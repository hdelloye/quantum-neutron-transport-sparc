"""neutron_qae: flat package imported by main.py (Qollab puts the project root on sys.path).

Every function that needs a backend takes it as a parameter; nothing here creates or
reads a global backend. Later phases add the ProblemSpec, Kernels, classical Monte Carlo,
quantum circuits and MLAE modules here.
"""

__all__ = ["smoke"]
