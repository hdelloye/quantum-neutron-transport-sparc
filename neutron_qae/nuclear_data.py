"""Cited one-group nuclear data at 14.1 MeV for the SPARC first wall (PHYS-02, code half).

Constants only: this module performs no I/O and is never read from a file or the network.

Source library: ENDF/B-VIII.0 neutron sublibrary (CSEWG release 2018-02-02;
D. A. Brown et al., Nucl. Data Sheets 148, 1 (2018)). For every element, the per-isotope
MF3 MT1 (total) and MT2 (elastic) cross sections are interpolated at ENERGY_EV = 14.1 MeV
with each file's own interpolation law and weighted by natural isotopic abundance. The
elastic mean lab-frame scattering cosine mubar_lab comes from MF4/MT2 with the exact
CM-to-lab transform and is weighted by sigma_el across isotopes.

Removal definition (PD-03): the model has one energy group, "14 MeV neutrons". Elastic
scattering keeps a neutron in the group; every non-elastic channel (inelastic, (n,2n),
(n,3n), (n,p), (n,alpha), capture) removes it, so sigma_a = sigma_t - sigma_el. (n,2n) is
counted once, as a removal: its secondaries are born far below the group.

Constants:
- ENERGY_EV, BARN_CM2, AVOGADRO: group energy (eV), barn in cm^2, Avogadro constant (SI exact).
- LIBRARY: citation of the evaluated library, its download URL and the reduction method.
- MICRO_14MEV[element] = (sigma_t [barn], sigma_el [barn], mubar_lab elastic) at 14.1 MeV.
- SIGMA_N2N_14MEV[element]: sigma(n,2n) [barn], part of the removal sigma_t - sigma_el;
  documentation of the removal split only, never used as scattering (PD-03).
- ATOMIC_WEIGHT, ATOMIC_NUMBER: standard atomic weights (IUPAC/NIST) and Z per element.
- ABUNDANCE[element] = {mass number: NIST natural mole fraction}.
- PROVENANCE[element] = rows (isotope, ENDF MAT, verbatim evaluation header string,
  evaluation date YYYY-MM[-DD]), one row per isotope in ABUNDANCE (36 rows).
- WHA_97W, SS316: (density g/cm3, {element: weight fraction}); MATERIAL_SOURCES cites them.
"""
ENERGY_EV = 14.1e6
BARN_CM2 = 1.0e-24
AVOGADRO = 6.02214076e23

LIBRARY = {
    "name": "ENDF/B-VIII.0",
    "sublibrary": "neutrons",
    "release_date": "2018-02-02",
    "reference": "D. A. Brown et al., Nucl. Data Sheets 148, 1 (2018)",
    "source": "https://www.nndc.bnl.gov/endf-b8.0/zips/ENDF-B-VIII.0_neutrons.zip",
    "method": ("MF3 MT1/MT2/MT16 interpolated at 14.1 MeV with each file's interpolation law; "
               "mubar_lab from MF4/MT2 with the exact CM-to-lab transform; natural-abundance weighting; "
               "mubar weighted by sigma_el"),
}
MICRO_14MEV = {
    "C": (1.32159, 0.832494, 0.622879),
    "Si": (1.8079, 0.717912, 0.752766),
    "P": (1.87835, 0.96125, 0.728879),
    "S": (1.73681, 0.761595, 0.649242),
    "Cr": (2.41505, 1.05993, 0.829759),
    "Mn": (2.47933, 1.14606, 0.814957),
    "Fe": (2.57208, 1.16978, 0.821381),
    "Ni": (2.70486, 1.24823, 0.82251),
    "Mo": (4.07235, 2.28007, 0.851513),
    "W": (5.367, 2.84245, 0.920464),
}
ATOMIC_WEIGHT = {"C": 12.011, "Si": 28.085, "P": 30.973761998, "S": 32.06, "Cr": 51.9961,
                 "Mn": 54.938044, "Fe": 55.845, "Ni": 58.6934, "Mo": 95.95, "W": 183.84}
ATOMIC_NUMBER = {"C": 6, "Si": 14, "P": 15, "S": 16, "Cr": 24, "Mn": 25, "Fe": 26, "Ni": 28, "Mo": 42, "W": 74}

# sigma(n,2n) at 14.1 MeV, barn: a removal channel inside sigma_t - sigma_el (PD-03), never scattering.
SIGMA_N2N_14MEV = {"C": 0.0, "Si": 0.0255, "P": 0.0108, "S": 0.0121, "Cr": 0.3426, "Mn": 0.6868,
                   "Fe": 0.4191, "Ni": 0.1619, "Mo": 1.1701, "W": 2.0727}

# NIST natural isotopic mole fractions {mass number: fraction}.
ABUNDANCE = {
    "C": {12: 0.9893, 13: 0.0107},
    "Si": {28: 0.92223, 29: 0.04685, 30: 0.03092},
    "P": {31: 1.0},
    "S": {32: 0.9499, 33: 0.0075, 34: 0.0425, 36: 0.0001},
    "Cr": {50: 0.04345, 52: 0.83789, 53: 0.09501, 54: 0.02365},
    "Mn": {55: 1.0},
    "Fe": {54: 0.05845, 56: 0.91754, 57: 0.02119, 58: 0.00282},
    "Ni": {58: 0.68077, 60: 0.26223, 61: 0.011399, 62: 0.036346, 64: 0.009255},
    "Mo": {92: 0.1453, 94: 0.0915, 95: 0.1584, 96: 0.1667, 97: 0.0960, 98: 0.2439, 100: 0.0982},
    "W": {180: 0.0012, 182: 0.2650, 183: 0.1431, 184: 0.3064, 186: 0.2843},
}

# ENDF/B-VIII.0 isotopic evaluations behind MICRO_14MEV: (isotope, MAT, evaluation header string, date).
_W_IAEA = ("IAEA Eval090806; NDS 148, 1 (2018) DIST-FEB18", "2009-08-06")
_FE_CIELO17 = ("CIELO EVAL-DEC17; NDS 148, 214 (2018)", "2017-12")
_FE_CIELO16 = ("CIELO EVAL-Oct16", "2016-10")
_NI_OCT12 = ("EVAL-Oct12", "2012-10")
_CR = ("LANL,ORNL EVAL-OCT97", "1997-10")
_MO_FEB05 = ("JNDC,BNL EVAL-FEB05", "2005-02")
_MO_AUG89 = ("JNDC EVAL-AUG89", "1989-08")
_SI_JUN97 = ("EVAL-JUN97", "1997-06")
_C = ("EVAL-AUG15", "2015-08")
_S = ("FUJI E.C. EVAL-MAY87", "1987-05")
PROVENANCE = {
    "C": (("C-12", 625, *_C), ("C-13", 628, *_C)),
    "Si": (("Si-28", 1425, "EVAL-DEC02", "2002-12"), ("Si-29", 1428, *_SI_JUN97), ("Si-30", 1431, *_SI_JUN97)),
    "P": (("P-31", 1525, "LANL,LLNL EVAL-DEC97", "1997-12"),),
    "S": (("S-32", 1625, *_S), ("S-33", 1628, *_S), ("S-34", 1631, *_S), ("S-36", 1637, *_S)),
    "Cr": (("Cr-50", 2425, *_CR), ("Cr-52", 2431, *_CR), ("Cr-53", 2434, *_CR), ("Cr-54", 2437, *_CR)),
    "Mn": (("Mn-55", 2525, "IAEA Eval-Feb11", "2011-02"),),
    "Fe": (("Fe-54", 2625, *_FE_CIELO17), ("Fe-56", 2631, *_FE_CIELO17),
           ("Fe-57", 2634, *_FE_CIELO16), ("Fe-58", 2637, *_FE_CIELO16)),
    "Ni": (("Ni-58", 2825, "LANL,ORNL EVAL-Aug12", "2012-08"), ("Ni-60", 2831, *_NI_OCT12),
           ("Ni-61", 2834, *_NI_OCT12), ("Ni-62", 2837, *_NI_OCT12), ("Ni-64", 2843, *_NI_OCT12)),
    "Mo": (("Mo-92", 4225, "EVAL-MAY 2011", "2011-05"), ("Mo-94", 4231, *_MO_FEB05),
           ("Mo-95", 4234, "BNL,KAERI EVAL-DEC10", "2010-12"), ("Mo-96", 4237, *_MO_AUG89),
           ("Mo-97", 4240, *_MO_FEB05), ("Mo-98", 4243, *_MO_AUG89), ("Mo-100", 4249, "CNDC EVAL-AUG00", "2000-08")),
    "W": (("W-180", 7425, *_W_IAEA), ("W-182", 7431, *_W_IAEA), ("W-183", 7434, "IAEA EVAL-AUG14", "2014-08"),
          ("W-184", 7437, *_W_IAEA), ("W-186", 7443, *_W_IAEA)),
}

MATERIAL_SOURCES = {
    "WHA_97W": ("Rizzi et al., arXiv:2603.03893: SPARC first-wall W heavy alloy (WHA), 97% W, 2% Ni, 1% Fe, "
                "room-temperature density 18.5 g/cm3; consistent with ASTM B777 Class 4"),
    "SS316": 'PNNL-15870 Rev. 2 (April 2021), entry 333 "Steel, Stainless 316", p. 227, 8.00 g/cm3',
    "ABUNDANCE": "NIST Atomic Weights and Isotopic Compositions, physics.nist.gov",
    "ATOMIC_WEIGHT": "IUPAC/NIST standard atomic weights",
}

# (density g/cm3, weight fractions)
WHA_97W = (18.5, {"W": 0.97, "Ni": 0.02, "Fe": 0.01})
SS316 = (8.00, {"C": 0.0008, "Mn": 0.02, "P": 0.00045, "S": 0.0003, "Si": 0.01, "Cr": 0.17,
                "Ni": 0.12, "Mo": 0.025, "Fe": 0.65345})
