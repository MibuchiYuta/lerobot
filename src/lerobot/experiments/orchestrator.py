"""Run bounded trials and write an append-only JSON Lines experiment log.

The module intentionally depends only on callable protocols.  Hardware, perception,
rule-engine, and policy integrations can each adapt their own public API at the
application boundary without this package importing any of those components.
"""

from __future__ import annotations

import json
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ._jsonl import append_json_line


@dataclass(frozen=True)
class TrialOutcome:
    """The domain result returned by a trial callable."""

    success: bool
    failure_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TrialRecord:
    """A persisted trial result, including orchestration-owned timing."""

    trial_index: int
    success: bool
    duration_s: float
    failure_reason: str | None
    metadata: Mapping[str, Any]
    timestamp_utc: str


@dataclass(frozen=True)
class ExperimentConfig:
    """Bounds and safety thresholds for one experiment loop."""

    max_trials: int | None = None
    max_duration_s: float | None = None
    max_consecutive_failures: int = 3

    def __post_init__(self) -> None:
        if self.max_trials is None and self.max_duration_s is None:
            raise ValueError("At least one of max_trials or max_duration_s must be set.")
        if self.max_trials is not None and self.max_trials < 1:
            raise ValueError("max_trials must be at least 1.")
        if self.max_duration_s is not None and self.max_duration_s <= 0:
            raise ValueError("max_duration_s must be positive.")
        if self.max_consecutive_failures < 1:
            raise ValueError("max_consecutive_failures must be at least 1.")


@dataclass(frozen=True)
class ExperimentResult:
    """The in-memory completion state of an experiment loop."""

    records: tuple[TrialRecord, ...]
    stop_reason: str
    elapsed_s: float


TrialCallable = Callable[[int], TrialOutcome]
SafetyCheck = Callable[[], str | None]
AnomalyDetector = Callable[[TrialRecord], str | None]


def _utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _write_record(log_path: Path, record: TrialRecord) -> None:
    append_json_line(
        log_path, json.dumps(asdict(record), ensure_ascii=False, sort_keys=True, default=str)
    )


def _read_clock(clock: Callable[[], float], previous: float | None = None) -> float:
    """Return a finite, non-decreasing monotonic-clock reading."""
    try:
        value = float(clock())
    except (TypeError, ValueError) as error:
        raise ValueError("clock must return a finite float") from error
    if not math.isfinite(value) or (previous is not None and value < previous):
        raise ValueError("clock must return finite, non-decreasing values")
    return value


def run_experiment(
    trial: TrialCallable,
    config: ExperimentConfig,
    log_path: Path | str,
    *,
    safety_check: SafetyCheck | None = None,
    anomaly_detector: AnomalyDetector | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> ExperimentResult:
    """Execute trials until an explicit bound or safety condition stops the loop.

    ``safety_check`` is called before each trial so an external emergency-stop
    adapter can prevent a new motion. ``anomaly_detector`` is called after a
    record is created, allowing perception or rules adapters to stop after the
    trial that exposed an anomaly. Any trial exception is safely persisted as a
    failed trial rather than escaping and leaving the run unaccounted for.
    """

    path = Path(log_path)
    started_at = _read_clock(clock)
    last_clock_value = started_at
    records: list[TrialRecord] = []
    consecutive_failures = 0
    stop_reason = "unknown"

    for trial_index in range(1, (config.max_trials or 2**63 - 1) + 1):
        last_clock_value = _read_clock(clock, last_clock_value)
        elapsed_s = last_clock_value - started_at
        if config.max_duration_s is not None and elapsed_s >= config.max_duration_s:
            stop_reason = "max_duration_reached"
            break
        if safety_check is not None:
            try:
                reason = safety_check()
            except Exception as error:
                stop_reason = f"safety_check_exception:{type(error).__name__}"
                break
            if reason:
                stop_reason = f"safety_stop:{reason}"
                break

        trial_started_at = _read_clock(clock, last_clock_value)
        last_clock_value = trial_started_at
        try:
            outcome = trial(trial_index)
            if not isinstance(outcome, TrialOutcome):
                raise TypeError("trial must return TrialOutcome")
        except Exception as error:  # Preserve the exception as a structured failed trial.
            outcome = TrialOutcome(False, f"trial_exception:{type(error).__name__}")

        record = TrialRecord(
            trial_index=trial_index,
            success=outcome.success,
            duration_s=_read_clock(clock, last_clock_value) - trial_started_at,
            failure_reason=None if outcome.success else outcome.failure_reason or "unspecified_failure",
            metadata=dict(outcome.metadata),
            timestamp_utc=_utc_timestamp(),
        )
        last_clock_value = trial_started_at + record.duration_s
        _write_record(path, record)
        records.append(record)

        consecutive_failures = 0 if record.success else consecutive_failures + 1
        if anomaly_detector is not None:
            try:
                reason = anomaly_detector(record)
            except Exception as error:
                stop_reason = f"anomaly_detector_exception:{type(error).__name__}"
                break
            if reason:
                stop_reason = f"anomaly_detected:{reason}"
                break
        if consecutive_failures >= config.max_consecutive_failures:
            stop_reason = "max_consecutive_failures_reached"
            break
    else:
        stop_reason = "max_trials_reached"

    elapsed_s = _read_clock(clock, last_clock_value) - started_at
    return ExperimentResult(tuple(records), stop_reason, elapsed_s)
