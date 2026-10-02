"""Hardware-agnostic utilities for repeatable robotics experiments."""

from .orchestrator import (
    ExperimentConfig,
    ExperimentResult,
    TrialOutcome,
    TrialRecord,
    run_experiment,
)

__all__ = [
    "ExperimentConfig",
    "ExperimentResult",
    "TrialOutcome",
    "TrialRecord",
    "run_experiment",
]
