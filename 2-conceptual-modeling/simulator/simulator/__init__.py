"""Wearable CPES simulator package."""

from .config import BASELINE_MODE, DETE4CPES_MODE, SimulationConfig
from .experiment_runner import ExperimentResult, run_experiment

__all__ = [
    "BASELINE_MODE",
    "DETE4CPES_MODE",
    "ExperimentResult",
    "SimulationConfig",
    "run_experiment",
]
