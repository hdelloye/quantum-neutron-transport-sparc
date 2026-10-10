"""ProblemSpec: the SPARC first-wall slab, defined once (PHYS-01).

Every geometry number and every macroscopic cross section used anywhere in the project
comes from `sparc_first_wall()`; the microscopic data behind it live in
`neutron_qae.nuclear_data` with their ENDF/B-VIII.0 citations.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass

import numpy as np

from neutron_qae import nuclear_data as nd

MODELS = ("transport_corrected", "isotropic_raw")
DEFAULT_MODEL = "transport_corrected"


@dataclass(frozen=True)
class Material:
    """One-group 14.1 MeV material, macroscopic cross sections in 1/cm.

    sigma_t is the model total cross section and sigma_s the model (isotropic) scattering
    cross section; under `transport_corrected` both carry the transport correction.
    """

    name: str
    sigma_t: float   # model total cross section, 1/cm
    sigma_s: float   # model isotropic scattering cross section, 1/cm

    def __post_init__(self):
        if not (math.isfinite(self.sigma_t) and math.isfinite(self.sigma_s)):
            raise ValueError(f"non-finite cross sections for {self.name}")
        if not (self.sigma_t > 0 and 0 <= self.sigma_s <= self.sigma_t):
            raise ValueError(f"bad cross sections for {self.name}: need sigma_t > 0 and 0 <= sigma_s <= sigma_t")

    @property
    def scatter_ratio(self) -> float:
        """P(scatter | collision) = sigma_s / sigma_t."""
        return self.sigma_s / self.sigma_t

    @property
    def sigma_a(self) -> float:
        """Removal from the 14 MeV group, sigma_t - sigma_s, 1/cm (PD-03).

        Covers every non-elastic channel, (n,2n) included and counted once. It is the same
        number under both models, because the transport correction subtracts the same
        mubar * Sigma_el from sigma_t and sigma_s.
        """
        return self.sigma_t - self.sigma_s


def atom_densities(rho: float, wfrac: dict[str, float]) -> dict[str, float]:
    """Atoms per barn-cm: N = rho * w * N_A / M * 1e-24, in the composition's insertion order."""
    if not (math.isfinite(rho) and rho > 0):
        raise ValueError(f"density must be a positive finite number, got {rho!r}")
    if not wfrac:
        raise ValueError("empty composition")
    for el, w in wfrac.items():
        if el not in nd.MICRO_14MEV or el not in nd.ATOMIC_WEIGHT:
            raise ValueError(f"element {el!r} has no entry in nuclear_data.MICRO_14MEV / ATOMIC_WEIGHT")
        if not (math.isfinite(w) and w >= 0):
            raise ValueError(f"weight fraction of {el} must be finite and non-negative, got {w!r}")
    total = math.fsum(wfrac.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"weight fractions sum to {total!r}, not 1 (tolerance 1e-6)")
    return {el: rho * w * nd.AVOGADRO / nd.ATOMIC_WEIGHT[el] * nd.BARN_CM2 for el, w in wfrac.items()}


def one_group(name: str, rho: float, wfrac: dict[str, float], model: str = DEFAULT_MODEL) -> Material:
    """Macroscopic one-group Material from a density and weight-fraction composition.

    model "transport_corrected" (default, PD-01): Sigma_tr = Sigma_t - mubar * Sigma_el,
    Sigma_s,tr = (1 - mubar) * Sigma_el. model "isotropic_raw": Sigma_t and Sigma_el as
    evaluated, elastic scattered isotropically. Sums run in the composition's insertion
    order, so repeated calls give bit-identical floats.
    """
    if model not in MODELS:
        raise ValueError(f"unknown model {model!r}; allowed models are {MODELS}")
    n = atom_densities(rho, wfrac)
    sig_t = sum(n[e] * nd.MICRO_14MEV[e][0] for e in n)
    sig_el = sum(n[e] * nd.MICRO_14MEV[e][1] for e in n)
    mu_sig_el = sum(n[e] * nd.MICRO_14MEV[e][1] * nd.MICRO_14MEV[e][2] for e in n)
    if model == "transport_corrected":          # Sigma_tr = Sigma_t - mubar*Sigma_el ; Sigma_s,tr = (1-mubar)*Sigma_el
        return Material(name, sig_t - mu_sig_el, sig_el - mu_sig_el)
    return Material(name, sig_t, sig_el)        # isotropic_raw: elastic kept at full size, scattered isotropically


def _is_count(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


@dataclass(frozen=True)
class ProblemSpec:
    """The 2D SPARC first-wall slab (PD-05 conventions, used by every engine).

    - x is depth through the wall (x = 0 is the plasma face, x = width_x the back face);
      y is lateral (0 <= y <= height_y).
    - 0-based column j spans [j * dx, (j + 1) * dx) with dx = width_x / nx (0.625 cm, exact
      in binary, so column edges j * dx are exact).
    - The front material (WHA) fills 0 <= x < boundary_x and the back material (SS316)
      boundary_x <= x <= width_x; `material_at` is half-open, so x = boundary_x is SS316.
      The 2.0 cm interface lies inside 0-based column index 3 = the ROADMAP's 1-based
      column 4; that column is integrated exactly over its two sub-segments, never snapped.
    - Exit row of a back-face crossing at height y is `row_of(y)` = floor(y / dy) clipped
      to [0, ny - 1] (floor, never round).
    - Direction bin b covers phi in [2 pi b / n_dir, 2 pi (b + 1) / n_dir), phi measured from
      +x toward +y.
    - Source: pencil beam entering at (x = 0, y = beam_y), normal incidence (+x).
    """

    front: Material                 # plasma side, 0 <= x < boundary_x
    back: Material                  # boundary_x <= x <= width_x
    width_x: float = 10.0           # depth through the wall, cm
    height_y: float = 10.0          # lateral extent, cm
    nx: int = 16                    # columns along x (column j spans [j*dx, (j+1)*dx), 0-based)
    ny: int = 16                    # rows along y
    boundary_x: float = 2.0         # W|SS interface, cm (inside 0-based column 3 = "column 4")
    beam_y: float = 5.0             # pencil beam, normal incidence at x=0
    n_dir: int = 16                 # direction bins, bin b = [2*pi*b/n_dir, 2*pi*(b+1)/n_dir), phi from +x toward +y

    def __post_init__(self):
        for name in ("width_x", "height_y", "boundary_x", "beam_y"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(f"{name} must be a finite number, got {v!r}")
        if not (self.width_x > 0 and self.height_y > 0):
            raise ValueError("width_x and height_y must be positive")
        for name in ("nx", "ny", "n_dir"):
            if not _is_count(getattr(self, name)):
                raise ValueError(f"{name} must be an int >= 1, got {getattr(self, name)!r}")
        if not (0 < self.boundary_x < self.width_x):
            raise ValueError(f"boundary_x must lie strictly inside (0, width_x), got {self.boundary_x!r}")
        if not (0 < self.beam_y < self.height_y):
            raise ValueError(f"beam_y must lie strictly inside (0, height_y), got {self.beam_y!r}")

    @property
    def dx(self) -> float:
        return self.width_x / self.nx

    @property
    def dy(self) -> float:
        return self.height_y / self.ny

    def material_at(self, x: float) -> Material:
        """Material at depth x; half-open interface, so x < boundary_x is front."""
        return self.front if x < self.boundary_x else self.back

    def tau_x(self, x):
        """Optical depth along +x from the front face to depth x (scalar or numpy array)."""
        x = np.asarray(x, dtype=float)
        a = np.minimum(x, self.boundary_x)
        b = np.maximum(x - self.boundary_x, 0.0)
        return self.front.sigma_t * a + self.back.sigma_t * b

    def column_segments(self, j: int) -> list[tuple[float, float, Material]]:
        """Single-material sub-segments (a, b, material) of 0-based column j; the interface column returns two."""
        x0, x1 = j * self.dx, (j + 1) * self.dx
        if x1 <= self.boundary_x:
            return [(x0, x1, self.front)]
        if x0 >= self.boundary_x:
            return [(x0, x1, self.back)]
        return [(x0, self.boundary_x, self.front), (self.boundary_x, x1, self.back)]

    def row_of(self, y):
        """Exit row: floor(y / dy) clipped to [0, ny - 1]; int for a scalar, int array otherwise."""
        r = np.clip(np.floor(np.asarray(y, dtype=float) / self.dy).astype(int), 0, self.ny - 1)
        return int(r) if np.ndim(y) == 0 else r


def sparc_first_wall(model: str = DEFAULT_MODEL, **overrides) -> ProblemSpec:
    """The SPARC first wall: 2.0 cm WHA 97W-2Ni-1Fe on 8.0 cm SS316, 10 x 10 cm, 16 x 16 lattice."""
    return ProblemSpec(front=one_group("WHA 97W-2Ni-1Fe", *nd.WHA_97W, model=model),
                       back=one_group("SS316", *nd.SS316, model=model), **overrides)


def spec_fingerprint(spec: ProblemSpec) -> str:
    """sha256 hex digest of the ProblemSpec inputs (json.dumps(asdict(spec), sort_keys=True)).

    Hashes inputs only; output floats are never byte-hashed (PD-06).
    """
    return hashlib.sha256(json.dumps(asdict(spec), sort_keys=True).encode("utf-8")).hexdigest()
