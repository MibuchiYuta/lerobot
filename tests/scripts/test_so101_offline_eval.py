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
