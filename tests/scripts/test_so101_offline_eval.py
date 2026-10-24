"""Unit tests for the hardware-free SO-101 offline evaluator."""

import fcntl
import importlib.util
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "so101_offline_eval.py"
SPEC = importlib.util.spec_from_file_location("so101_offline_eval", SCRIPT)
assert SPEC and SPEC.loader
offline_eval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(offline_eval)


def test_masked_error_sums_ignores_padded_actions() -> None:
    prediction = torch.tensor([[[2.0, 4.0], [50.0, 50.0]]])
    target = torch.tensor([[[1.0, 1.0], [0.0, 0.0]]])
    absolute, squared, count = offline_eval.masked_error_sums(
        prediction, target, torch.tensor([[False, True]])
    )
    assert (absolute, squared, count) == (4.0, 10.0, 2)


def test_masked_error_sums_rejects_mismatched_shapes() -> None:
    with pytest.raises(ValueError, match="prediction shape"):
        offline_eval.masked_error_sums(torch.ones(1, 2), torch.ones(1, 3))


def test_mean_action_uses_only_requested_batch_limit() -> None:
    class Dataset(torch.utils.data.Dataset):
        def __len__(self) -> int:
            return 2

        def __getitem__(self, index: int) -> dict[str, torch.Tensor]:
            return {offline_eval.ACTION: torch.tensor([[1.0] if index == 0 else [9.0]])}

    assert offline_eval._mean_action(Dataset(), batch_size=1, max_batches=1).item() == 1.0
    assert offline_eval._mean_action(Dataset(), batch_size=1, max_batches=None).item() == 5.0


def test_evaluator_has_no_hardware_imports() -> None:
    source = SCRIPT.read_text()
    forbidden_imports = (
        r"(?:from|import)\s+lerobot\.robots",
        r"(?:from|import)\s+lerobot\.teleoperators",
        r"(?:from|import)\s+serial",
        r"(?:from|import)\s+cv2",
    )
    for forbidden in forbidden_imports:
        assert not re.search(forbidden, source)


def test_write_metrics_rejects_existing_output_without_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "offline_eval.json"
    output.write_text("important existing result\n")

    with pytest.raises(FileExistsError, match="pass --overwrite"):
        offline_eval._write_metrics(output, {"new": "metrics"}, overwrite=False)

    assert output.read_text() == "important existing result\n"


def test_write_metrics_backs_up_and_replaces_existing_output_when_requested(tmp_path: Path) -> None:
    output = tmp_path / "offline_eval.json"
    output.write_text("old result\n")

    backup = offline_eval._write_metrics(output, {"new": "metrics"}, overwrite=True)

    assert output.read_text() == '{\n  "new": "metrics"\n}\n'
    assert backup is not None
    assert backup.read_text() == "old result\n"
    assert not list(tmp_path.glob(".*.tmp"))
    assert (tmp_path / ".offline_eval.json.lock").exists()


def test_write_metrics_rejects_concurrent_writer(tmp_path: Path) -> None:
    output = tmp_path / "offline_eval.json"
    lock = tmp_path / ".offline_eval.json.lock"
    with lock.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(FileExistsError, match="being written by another evaluator"):
            offline_eval._write_metrics(output, {"new": "metrics"}, overwrite=False)


def test_write_metrics_reuses_stale_lock_file(tmp_path: Path) -> None:
    output = tmp_path / "offline_eval.json"
    lock = tmp_path / ".offline_eval.json.lock"
    lock.write_text("left by a terminated evaluator\n")

    offline_eval._write_metrics(output, {"new": "metrics"}, overwrite=False)

    assert output.read_text() == '{\n  "new": "metrics"\n}\n'


def test_evaluate_uses_standard_delta_timestamp_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    config = SimpleNamespace(device="cpu")
    metadata = object()

    monkeypatch.setattr(offline_eval.PreTrainedConfig, "from_pretrained", lambda _: config)
    monkeypatch.setattr(offline_eval, "LeRobotDatasetMetadata", lambda _: metadata)

    class ResolutionReachedError(Exception):
        pass

    def resolve(received_config: object, received_metadata: object) -> None:
        assert received_config is config
        assert received_metadata is metadata
        raise ResolutionReachedError

    monkeypatch.setattr(offline_eval, "resolve_delta_timestamps", resolve)

    with pytest.raises(ResolutionReachedError):
        offline_eval.evaluate(
            checkpoint=checkpoint,
            dataset_repo_id="example/dataset",
            holdout_episodes=[8, 9],
            output=tmp_path / "metrics.json",
            batch_size=1,
            device="cpu",
            video_backend="pyav",
            max_batches=1,
        )


def test_cli_accepts_training_video_backend_spelling(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(offline_eval, "evaluate", lambda **kwargs: captured.update(kwargs) or {})
    monkeypatch.setattr(
        "sys.argv",
        [
            str(SCRIPT),
            "--checkpoint",
            "/tmp/checkpoint",
            "--dataset.repo_id",
            "example/dataset",
            "--holdout-episodes",
            "8,9",
            "--output",
            "/tmp/output.json",
            "--dataset.video_backend=pyav",
        ],
    )

    offline_eval.main()

    assert captured["video_backend"] == "pyav"
