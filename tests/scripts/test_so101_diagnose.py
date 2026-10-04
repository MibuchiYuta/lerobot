"""Offline contract tests for the read-only SO-101 diagnostic."""

import importlib.util
import json
import sys
import types
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "so101_diagnose.py"


def load_diagnose_module(monkeypatch):
    motors_module = types.ModuleType("lerobot.motors")

    class Motor:
        def __init__(self, *args):
            self.args = args

    class MotorNormMode:
        RANGE_M100_100 = object()

    motors_module.Motor = Motor
    motors_module.MotorNormMode = MotorNormMode
    feetech_module = types.ModuleType("lerobot.motors.feetech")
    feetech_module.FeetechMotorsBus = object
    monkeypatch.setitem(sys.modules, "lerobot.motors", motors_module)
    monkeypatch.setitem(sys.modules, "lerobot.motors.feetech", feetech_module)

    spec = importlib.util.spec_from_file_location("so101_diagnose", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_diagnose_reads_raw_positions_without_changing_torque(monkeypatch, capsys):
    module = load_diagnose_module(monkeypatch)
    instances = []

    class FakeBus:
        is_connected = True

        def __init__(self, *, port, motors):
            self.port = port
            self.motors = motors
            self.calls = []
            instances.append(self)

        def connect(self):
            self.calls.append(("connect",))

        def sync_read(self, data_name, *, normalize):
            self.calls.append(("sync_read", data_name, normalize))
            return {str(index): index * 100 for index in range(1, 7)}

        def disconnect(self, *, disable_torque):
            self.calls.append(("disconnect", disable_torque))
            self.is_connected = False

    monkeypatch.setattr(module, "FeetechMotorsBus", FakeBus)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT_PATH), "/dev/ttyACM0"])

    assert module.main() == 0

    assert instances[0].calls == [
        ("connect",),
        ("sync_read", "Present_Position", False),
        ("disconnect", False),
    ]
    assert json.loads(capsys.readouterr().out) == {
        "raw_encoder_positions": {str(index): index * 100 for index in range(1, 7)}
    }
