"""Offline logging contract tests for the safe SO-101 teleoperation script."""

import argparse
import importlib.util
import logging
import sys
import types
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "so101_safe_teleop.py"


def load_teleop_module(monkeypatch):
    robots_module = types.ModuleType("lerobot.robots")
    follower_module = types.ModuleType("lerobot.robots.so_follower")
    follower_module.SO101Follower = object
    follower_module.SO101FollowerConfig = object
    safety_module = types.ModuleType("lerobot.robots.so_follower.safety")
    safety_module.SO101SafetyMonitor = object
    safety_module.SafetyFault = type("SafetyFault", (Exception,), {})
    safety_module.SafetyLimits = object
    teleoperators_module = types.ModuleType("lerobot.teleoperators")
    leader_module = types.ModuleType("lerobot.teleoperators.so_leader")
    leader_module.SO101Leader = object
    leader_module.SO101LeaderConfig = object

    monkeypatch.setitem(sys.modules, "lerobot.robots", robots_module)
    monkeypatch.setitem(sys.modules, "lerobot.robots.so_follower", follower_module)
    monkeypatch.setitem(sys.modules, "lerobot.robots.so_follower.safety", safety_module)
    monkeypatch.setitem(sys.modules, "lerobot.teleoperators", teleoperators_module)
    monkeypatch.setitem(sys.modules, "lerobot.teleoperators.so_leader", leader_module)

    spec = importlib.util.spec_from_file_location("so101_safe_teleop", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("failure", "monitor_failure", "expected_status", "expected_level", "has_exception"),
    [
        (KeyboardInterrupt(), None, 130, logging.INFO, False),
        (RuntimeError("communication lost"), None, 1, logging.ERROR, True),
        (None, "safety fault", 1, logging.ERROR, True),
    ],
)
def test_teleop_logs_normal_interrupts_at_info_and_failures_at_error(
    monkeypatch, caplog, failure, monitor_failure, expected_status, expected_level, has_exception
):
    module = load_teleop_module(monkeypatch)
    devices = []

    class Device:
        is_connected = True

        def __init__(self, *_args, **_kwargs):
            self.bus = object()
            self.disconnected = False
            devices.append(self)

        def connect(self):
            pass

        def disconnect(self):
            self.disconnected = True

    class Leader(Device):
        def get_action(self):
            if failure is not None:
                raise failure
            return {}

    class Monitor:
        is_latched = False

        def __init__(self, *_args, **_kwargs):
            pass

        def trip(self, _reason):
            self.is_latched = True
            raise module.SafetyFault()

        def check_action(self, _action):
            if monitor_failure is not None:
                self.is_latched = True
                raise module.SafetyFault(monitor_failure)

    monkeypatch.setattr(module, "SO101Follower", Device)
    monkeypatch.setattr(module, "SO101Leader", Leader)
    monkeypatch.setattr(module, "SO101FollowerConfig", lambda **kwargs: kwargs)
    monkeypatch.setattr(module, "SO101LeaderConfig", lambda **kwargs: kwargs)
    monkeypatch.setattr(module, "SO101SafetyMonitor", Monitor)
    monkeypatch.setattr(module, "SafetyLimits", lambda **kwargs: kwargs)
    monkeypatch.setattr(
        module,
        "parse_args",
        lambda: argparse.Namespace(
            arm=True,
            follower_port="/dev/follower",
            leader_port="/dev/leader",
            follower_id="follower",
            leader_id="leader",
            fps=30.0,
            max_cycle_s=0.25,
            max_position_step=35.0,
            max_present_current=None,
        ),
    )

    with caplog.at_level(logging.INFO):
        assert module.main() == expected_status

    stopped = [record for record in caplog.records if record.message == "SO-101 teleoperation stopped"]
    assert len(stopped) == 1
    assert stopped[0].levelno == expected_level
    assert bool(stopped[0].exc_info) is has_exception
    assert all(device.disconnected for device in devices)
