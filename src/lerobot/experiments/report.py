"""Summarize JSON Lines experiment records without hardware dependencies."""

from __future__ import annotations

import json
from argparse import ArgumentParser
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from ._jsonl import locked_log_file


@dataclass(frozen=True)
class ExperimentReport:
    """Aggregate statistics derived from a JSON Lines trial log."""

    total_trials: int
    successful_trials: int
    success_rate: float
    average_duration_s: float
    failure_patterns: dict[str, int]


def generate_report(log_path: Path | str) -> ExperimentReport:
    """Read trial records and return success, duration, and failure-pattern metrics."""
    records: list[dict[str, object]] = []
    with locked_log_file(Path(log_path), "r") as log_file:
        lines = log_file.readlines()
        for line_number, line in enumerate(lines, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                if line_number == len(lines) and not line.endswith("\n"):
                    # A crash may leave only the final record incomplete. Earlier
                    # records remain durable and are safe to summarize.
                    continue
                raise ValueError(f"Invalid JSON at line {line_number}") from error
            if not isinstance(record, dict):
                raise ValueError(f"Expected an object at line {line_number}")
            records.append(record)

    total_trials = len(records)
    successful_trials = sum(record.get("success") is True for record in records)
    durations = [float(record["duration_s"]) for record in records]
    failures = Counter(
        str(record.get("failure_reason") or "unspecified_failure")
        for record in records
        if record.get("success") is not True
    )
    return ExperimentReport(
        total_trials=total_trials,
        successful_trials=successful_trials,
        success_rate=successful_trials / total_trials if total_trials else 0.0,
        average_duration_s=sum(durations) / total_trials if total_trials else 0.0,
        failure_patterns=dict(sorted(failures.items())),
    )


def main() -> None:
    """Print a JSON report for a trial log."""
    parser = ArgumentParser(description="Summarize a LeRobot experiment JSON Lines log.")
    parser.add_argument("log_path", type=Path)
    args = parser.parse_args()
    print(json.dumps(asdict(generate_report(args.log_path)), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
