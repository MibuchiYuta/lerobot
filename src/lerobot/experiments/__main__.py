"""Run a mock experiment and print its report."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from pathlib import Path

from .mock import make_mock_trial
from .orchestrator import ExperimentConfig, run_experiment
from .report import generate_report


def main() -> None:
    """Provide a no-hardware smoke-test command for the experiment loop."""
    parser = argparse.ArgumentParser(description="Run a hardware-free LeRobot experiment mock.")
    parser.add_argument("--log-path", type=Path, required=True, help="Destination JSON Lines log path.")
    parser.add_argument("--max-trials", type=int, default=5)
    parser.add_argument(
        "--outcomes", default="success,failure", help="Comma-separated mock outcomes: success or failure."
    )
    args = parser.parse_args()
    outcomes = tuple(value.strip() == "success" for value in args.outcomes.split(","))
    if any(value.strip() not in {"success", "failure"} for value in args.outcomes.split(",")):
        parser.error("--outcomes accepts only success and failure")

    result = run_experiment(
        make_mock_trial(outcomes), ExperimentConfig(max_trials=args.max_trials), args.log_path
    )
    print(asdict(result))
    print(asdict(generate_report(args.log_path)))


if __name__ == "__main__":
    main()
