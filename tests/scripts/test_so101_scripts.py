"""Offline contract tests for the SO-101 workflow wrappers."""

import os
import subprocess
from pathlib import Path

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def run_script(name: str, *, environment: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPTS_DIR / name), "--dry-run"],
        check=False,
        capture_output=True,
        env={**os.environ, **environment},
        text=True,
    )


@pytest.mark.parametrize(
    ("name", "environment", "expected"),
    [
        ("record_so101.sh", {"TASK_DESCRIPTION": "Pick up a cube"}, "lerobot-record"),
        (
            "train_so101.sh",
            {"DATASET_REPO_ID": "example/so101_train", "POLICY": "diffusion"},
            "--policy.type=diffusion",
        ),
        (
            "eval_so101.sh",
            {
                "POLICY_PATH": "outputs/train/checkpoint",
                "DATASET_REPO_ID": "example/eval_so101",
                "TASK_DESCRIPTION": "Pick up a cube",
            },
            "--policy.path=outputs/train/checkpoint",
        ),
        ("replay_so101.sh", {"DATASET_REPO_ID": "example/so101_train"}, "lerobot-replay"),
        ("teleoperate_so101.sh", {}, "lerobot-teleoperate"),
    ],
)
def test_dry_run_does_not_access_a_device(
    name: str, environment: dict[str, str], expected: str
) -> None:
    result = run_script(name, environment=environment)

    assert result.returncode == 0, result.stderr
    assert "Dry run (no device, dataset, or network access):" in result.stdout
    assert expected in result.stdout


def test_eval_rejects_non_evaluation_dataset_name() -> None:
    result = run_script(
        "eval_so101.sh",
        environment={
            "POLICY_PATH": "outputs/train/checkpoint",
            "DATASET_REPO_ID": "example/so101_train",
            "TASK_DESCRIPTION": "Pick up a cube",
        },
    )

    assert result.returncode == 2
    assert "beginning eval_" in result.stderr


def test_train_rejects_unknown_policy() -> None:
    result = run_script(
        "train_so101.sh",
        environment={"DATASET_REPO_ID": "example/so101_train", "POLICY": "unsupported"},
    )

    assert result.returncode == 2
    assert "POLICY must be act or diffusion" in result.stderr
