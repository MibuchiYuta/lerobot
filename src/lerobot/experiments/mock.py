"""Deterministic mock trial adapters for testing an experiment plan without hardware."""

from __future__ import annotations

from collections.abc import Sequence

from .orchestrator import TrialOutcome


def make_mock_trial(outcomes: Sequence[bool] = (True,)):
    """Return a deterministic trial callable cycling through ``outcomes``."""
    if not outcomes:
        raise ValueError("outcomes must not be empty")

    def trial(trial_index: int) -> TrialOutcome:
        success = outcomes[(trial_index - 1) % len(outcomes)]
        return TrialOutcome(
            success=success,
            failure_reason=None if success else "mock_grasp_miss",
            metadata={"adapter": "mock"},
        )

    return trial
