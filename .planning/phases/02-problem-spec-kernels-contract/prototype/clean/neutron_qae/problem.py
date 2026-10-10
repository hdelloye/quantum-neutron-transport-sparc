"""ProblemSpec: the SPARC first-wall slab, defined once (PHYS-01)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from neutron_qae import nuclear_data as nd


@dataclass(frozen=True)
class Material:
    name: str
    sigma_t: float   # model total cross section, 1/cm
    sigma_s: float   # model isotropic scattering cross section, 1/cm

    def __post_init__(self):
        if not (self.sigma_t > 0 and 0 <= self.sigma_s <= self.sigma_t):
            raise ValueError(f"bad cross sections for {self.name}")

    @property
    def scatter_ratio(self) -> float:
        return self.sigma_s / self.sigma_t


def atom_densities(rho: float, wfrac: dict[str, float]) -> dict[str, float]:
    """Atoms per barn-cm: N = rho * w * N_A / M * 1e-24."""
    return {el: rho * w * nd.AVOGADRO / nd.ATOMIC_WEIGHT[el] * nd.BARN_CM2 for el, w in wfrac.items()}


def one_group(name: str, rho: float, wfrac: dict[str, float], model: str = "transport_corrected") -> Material:
    n = atom_densities(rho, wfrac)
    sig_t = sum(n[e] * nd.MICRO_14MEV[e][0] for e in n)
    sig_el = sum(n[e] * nd.MICRO_14MEV[e][1] for e in n)
    mu_sig_el = sum(n[e] * nd.MICRO_14MEV[e][1] * nd.MICRO_14MEV[e][2] for e in n)
    if model == "transport_corrected":          # Sigma_tr = Sigma_t - mubar*Sigma_el ; Sigma_s,tr = (1-mubar)*Sigma_el
        return Material(name, sig_t - mu_sig_el, sig_el - mu_sig_el)
    if model == "isotropic_raw":                # elastic kept at full size but scattered isotropically
        return Material(name, sig_t, sig_el)
    raise ValueError(model)


@dataclass(frozen=True)
class ProblemSpec:
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
        if not (0 < self.boundary_x < self.width_x and 0 < self.beam_y < self.height_y):
            raise ValueError("geometry")

    @property
    def dx(self) -> float:
        return self.width_x / self.nx

    @property
    def dy(self) -> float:
        return self.height_y / self.ny

    def material_at(self, x: float) -> Material:
        return self.front if x < self.boundary_x else self.back

    def tau_x(self, x):
        """Optical depth along +x from the front face to depth x (scalar or numpy array)."""
        import numpy as np
        x = np.asarray(x, dtype=float)
        a = np.minimum(x, self.boundary_x)
        b = np.maximum(x - self.boundary_x, 0.0)
        return self.front.sigma_t * a + self.back.sigma_t * b

    def column_segments(self, j: int) -> list[tuple[float, float, Material]]:
        """Single-material sub-segments of column j; the interface column returns two."""
        x0, x1 = j * self.dx, (j + 1) * self.dx
        if x1 <= self.boundary_x:
            return [(x0, x1, self.front)]
        if x0 >= self.boundary_x:
            return [(x0, x1, self.back)]
        return [(x0, self.boundary_x, self.front), (self.boundary_x, x1, self.back)]


def sparc_first_wall(model: str = "transport_corrected", **overrides) -> ProblemSpec:
    return ProblemSpec(front=one_group("WHA 97W-2Ni-1Fe", *nd.WHA_97W, model=model),
                       back=one_group("SS316", *nd.SS316, model=model), **overrides)
