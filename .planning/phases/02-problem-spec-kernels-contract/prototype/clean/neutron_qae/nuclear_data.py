"""One-group 14.1 MeV microscopic data, ENDF/B-VIII.0 (released 2018-02-02, NDS 148 (2018) 1).
Per element: (sigma_total [b], sigma_elastic [b], mubar_lab elastic), natural-abundance weighted
over isotopic evaluations MF3 MT1/MT2 (lin-lin interpolated at 14.1 MeV) and MF4 MT2."""
ENERGY_EV = 14.1e6
BARN_CM2 = 1.0e-24
AVOGADRO = 6.02214076e23
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
# (density g/cm3, weight fractions)
WHA_97W = (18.5, {"W": 0.97, "Ni": 0.02, "Fe": 0.01})
SS316 = (8.00, {"C": 0.0008, "Mn": 0.02, "P": 0.00045, "S": 0.0003, "Si": 0.01, "Cr": 0.17,
                "Ni": 0.12, "Mo": 0.025, "Fe": 0.65345})
