"""Offline contract tests for the SO-101 workflow wrappers."""

import os
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml


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
    assert "prefixed with eval_" in result.stderr
    assert "org/eval_task" in result.stderr


def test_train_rejects_unknown_policy() -> None:
    result = run_script(
        "train_so101.sh",
        environment={"DATASET_REPO_ID": "example/so101_train", "POLICY": "unsupported"},
    )

    assert result.returncode == 2
    assert "Set POLICY=act or POLICY=diffusion" in result.stderr


def test_record_rejects_invalid_resume_value() -> None:
    result = run_script(
        "record_so101.sh",
        environment={"TASK_DESCRIPTION": "Pick up a cube", "RESUME": "invalid"},
    )

    assert result.returncode == 2
    assert "Set RESUME=true or RESUME=false" in result.stderr


def dry_run_camera_config(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    command = shlex.split(result.stdout.splitlines()[1].strip())
    camera_argument = next(argument for argument in command if argument.startswith("--robot.cameras="))
    return yaml.safe_load(camera_argument.removeprefix("--robot.cameras="))


def test_record_dry_run_camera_defaults_are_valid_yaml() -> None:
    result = run_script(
        "record_so101.sh",
        environment={"TASK_DESCRIPTION": "Pick up a cube", "SO101_CAMERAS": ""},
    )

    assert result.returncode == 0, result.stderr
    cameras = dry_run_camera_config(result)
    assert cameras["top"]["index_or_path"] == "/dev/video0"
    assert cameras["wrist"]["index_or_path"] == "/dev/video2"
    assert cameras["top"]["type"] == cameras["wrist"]["type"] == "opencv"


def test_record_dry_run_preserves_camera_override_as_yaml() -> None:
    override = "{top: {type: opencv, index_or_path: /dev/video9}, wrist: {type: opencv, index_or_path: /dev/video8}}"
    result = run_script(
        "record_so101.sh",
        environment={"TASK_DESCRIPTION": "Pick up a cube", "SO101_CAMERAS": override},
    )

    assert result.returncode == 0, result.stderr
    cameras = dry_run_camera_config(result)
    assert cameras["top"]["index_or_path"] == "/dev/video9"
    assert cameras["wrist"]["index_or_path"] == "/dev/video8"


def test_record_requires_display_and_xauthority_outside_dry_run() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPTS_DIR / "record_so101.sh")],
        check=False,
        capture_output=True,
        env={**os.environ, "TASK_DESCRIPTION": "Pick up a cube", "DISPLAY": "", "XAUTHORITY": ""},
        text=True,
    )

    assert result.returncode == 1
    assert "Cannot record with keyboard controls" in result.stderr
    assert "DISPLAY XAUTHORITY is unset" in result.stderr


def test_record_reports_an_unusable_lock_directory(tmp_path: Path) -> None:
    lock_file = tmp_path / "not-a-directory"
    lock_file.touch()
    result = subprocess.run(
        ["bash", str(SCRIPTS_DIR / "record_so101.sh")],
        check=False,
        capture_output=True,
        env={
            **os.environ,
            "TASK_DESCRIPTION": "Pick up a cube",
            "SO101_LOCK_DIR": str(lock_file),
            "DISPLAY": ":0",
            "XAUTHORITY": "/tmp/test-xauthority",
        },
        text=True,
    )

    assert result.returncode == 1
    assert "Unable to create SO101_LOCK_DIR" in result.stderr


def test_record_uses_a_per_dataset_local_lock() -> None:
    source = (SCRIPTS_DIR / "record_so101.sh").read_text()

    assert "SO101_LOCK_DIR" in source
    assert "flock -n" in source
