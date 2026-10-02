"""Tests for the hardware-independent experiment orchestration boundary."""

import json

import pytest

from lerobot.experiments.mock import make_mock_trial
from lerobot.experiments.orchestrator import ExperimentConfig, TrialOutcome, run_experiment
from lerobot.experiments.report import generate_report


def test_run_experiment_writes_jsonl_and_report(tmp_path):
    log_path = tmp_path / "trials.jsonl"

    result = run_experiment(
        make_mock_trial((True, False, True)), ExperimentConfig(max_trials=3), log_path
    )

    assert result.stop_reason == "max_trials_reached"
    records = [json.loads(line) for line in log_path.read_text().splitlines()]
    assert [record["success"] for record in records] == [True, False, True]
    assert records[1]["failure_reason"] == "mock_grasp_miss"
    report = generate_report(log_path)
    assert report.success_rate == pytest.approx(2 / 3)
    assert report.failure_patterns == {"mock_grasp_miss": 1}


def test_safety_check_stops_before_a_new_trial(tmp_path):
    calls = []

    def trial(index):
        calls.append(index)
        return TrialOutcome(True)

    result = run_experiment(
        trial, ExperimentConfig(max_trials=3), tmp_path / "trials.jsonl", safety_check=lambda: "e_stop"
    )

    assert result.stop_reason == "safety_stop:e_stop"
    assert calls == []
    assert result.records == ()


def test_anomaly_and_consecutive_failures_stop_loop(tmp_path):
    anomaly_result = run_experiment(
        make_mock_trial((True,)),
        ExperimentConfig(max_trials=3),
        tmp_path / "anomaly.jsonl",
        anomaly_detector=lambda record: "camera_lost" if record.trial_index == 1 else None,
    )
    failures_result = run_experiment(
        make_mock_trial((False,)),
        ExperimentConfig(max_trials=5, max_consecutive_failures=2),
        tmp_path / "failures.jsonl",
    )

    assert anomaly_result.stop_reason == "anomaly_detected:camera_lost"
    assert len(anomaly_result.records) == 1
    assert failures_result.stop_reason == "max_consecutive_failures_reached"
    assert len(failures_result.records) == 2


def test_duration_bound_stops_before_a_new_trial(tmp_path):
    clock_values = iter((0.0, 1.0, 1.0))
    calls = []

    def trial(index):
        calls.append(index)
        return TrialOutcome(True)

    result = run_experiment(
        trial,
        ExperimentConfig(max_duration_s=0.5),
        tmp_path / "trials.jsonl",
        clock=lambda: next(clock_values),
    )

    assert result.stop_reason == "max_duration_reached"
    assert calls == []


def test_trial_exceptions_are_recorded_as_failures(tmp_path):
    def broken_trial(index):
        raise RuntimeError("motor disconnected")

    result = run_experiment(
        broken_trial, ExperimentConfig(max_trials=1), tmp_path / "trials.jsonl"
    )

    assert result.records[0].failure_reason == "trial_exception:RuntimeError"


def test_config_requires_a_bound():
    with pytest.raises(ValueError, match="max_trials"):
        ExperimentConfig()


def test_config_rejects_zero_consecutive_failures():
    with pytest.raises(ValueError, match="max_consecutive_failures"):
        ExperimentConfig(max_trials=1, max_consecutive_failures=0)


def test_safety_check_exception_stops_before_a_trial(tmp_path):
    result = run_experiment(
        lambda index: TrialOutcome(True),
        ExperimentConfig(max_trials=1),
        tmp_path / "trials.jsonl",
        safety_check=lambda: (_ for _ in ()).throw(RuntimeError("e-stop unavailable")),
    )

    assert result.stop_reason == "safety_check_exception:RuntimeError"
    assert result.records == ()


def test_anomaly_detector_exception_stops_after_persisting_trial(tmp_path):
    result = run_experiment(
        lambda index: TrialOutcome(True),
        ExperimentConfig(max_trials=2),
        tmp_path / "trials.jsonl",
        anomaly_detector=lambda record: (_ for _ in ()).throw(RuntimeError("camera offline")),
    )

    assert result.stop_reason == "anomaly_detector_exception:RuntimeError"
    assert len(result.records) == 1


def test_invalid_clock_is_rejected_before_a_trial(tmp_path):
    with pytest.raises(ValueError, match="clock"):
        run_experiment(
            lambda index: TrialOutcome(True),
            ExperimentConfig(max_trials=1),
            tmp_path / "trials.jsonl",
            clock=lambda: float("nan"),
        )


def test_non_outcome_trial_result_is_recorded_as_failure(tmp_path):
    result = run_experiment(
        lambda index: "not-an-outcome", ExperimentConfig(max_trials=1), tmp_path / "trials.jsonl"
    )

    assert result.records[0].failure_reason == "trial_exception:TypeError"


def test_report_handles_empty_and_interrupted_logs(tmp_path):
    empty_log = tmp_path / "empty.jsonl"
    empty_log.touch()
    assert generate_report(empty_log).total_trials == 0

    interrupted_log = tmp_path / "interrupted.jsonl"
    interrupted_log.write_text('{"success": true, "duration_s": 1}\n{"success":')
    report = generate_report(interrupted_log)
    assert report.total_trials == 1
    assert report.success_rate == 1.0


def test_report_rejects_complete_invalid_json_and_normalizes_failure_reason(tmp_path):
    invalid_log = tmp_path / "invalid.jsonl"
    invalid_log.write_text("not-json\n")
    with pytest.raises(ValueError, match="Invalid JSON at line 1"):
        generate_report(invalid_log)

    failure_log = tmp_path / "failures.jsonl"
    failure_log.write_text('{"success": false, "duration_s": 1, "failure_reason": 42}\n')
    assert generate_report(failure_log).failure_patterns == {"42": 1}
