"""Unit tests for the hardware-free SO-101 offline evaluator."""

import importlib.util
import re
from pathlib import Path

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


def test_write_metrics_replaces_existing_output_atomically_when_requested(tmp_path: Path) -> None:
    output = tmp_path / "offline_eval.json"
    output.write_text("old result\n")

    offline_eval._write_metrics(output, {"new": "metrics"}, overwrite=True)

    assert output.read_text() == '{\n  "new": "metrics"\n}\n'
    assert not list(tmp_path.glob(".*.tmp"))
    assert not list(tmp_path.glob(".*.lock"))


def test_write_metrics_rejects_concurrent_writer(tmp_path: Path) -> None:
    output = tmp_path / "offline_eval.json"
    lock = tmp_path / ".offline_eval.json.lock"
    lock.touch()

    with pytest.raises(FileExistsError, match="being written by another evaluator"):
        offline_eval._write_metrics(output, {"new": "metrics"}, overwrite=False)


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
