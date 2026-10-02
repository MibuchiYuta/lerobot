import pytest

from lerobot.robots.so_follower.safety import SO101SafetyMonitor, SafetyFault, SafetyLimits


class Bus:
    motors = {"shoulder_pan": object(), "gripper": object()}

    def __init__(self, failures=()):
        self.stopped = []
        self.failures = set(failures)

    def disable_torque(self, motors=None, num_retry=0):
        self.stopped.append((motors, num_retry))
        if motors in self.failures:
            raise OSError(motors)


def action(pan=0.0, gripper=0.0):
    return {"shoulder_pan.pos": pan, "gripper.pos": gripper}


def test_non_finite_command_stops_every_motor_and_latches():
    bus = Bus(failures={"shoulder_pan"})
    monitor = SO101SafetyMonitor(bus)

    with pytest.raises(SafetyFault, match="non-finite"):
        monitor.check_action(action(float("nan")))

    assert [motor for motor, _ in bus.stopped] == ["shoulder_pan", "gripper"]
    assert "shoulder_pan" in monitor.stop_errors
    with pytest.raises(SafetyFault, match="latched"):
        monitor.check_action(action())


def test_missing_joint_is_fail_closed():
    bus = Bus()
    monitor = SO101SafetyMonitor(bus)
    with pytest.raises(SafetyFault, match="incomplete"):
        monitor.check_action({"shoulder_pan.pos": 0.0})
    assert len(bus.stopped) == 2


def test_heartbeat_and_position_step_trip():
    values = iter((0.0, 0.3))
    bus = Bus()
    monitor = SO101SafetyMonitor(bus, SafetyLimits(max_cycle_s=0.2, max_position_step=10), clock=lambda: next(values))
    monitor.check_action(action())
    with pytest.raises(SafetyFault, match="heartbeat"):
        monitor.check_action(action())

    monitor = SO101SafetyMonitor(Bus(), SafetyLimits(max_position_step=10))
    monitor.check_action(action())
    with pytest.raises(SafetyFault, match="unexpected position step"):
        monitor.check_action(action(pan=11))


def test_current_telemetry_is_checked_fail_closed():
    bus = Bus()
    monitor = SO101SafetyMonitor(bus)
    with pytest.raises(SafetyFault, match="possible collision"):
        monitor.check_present_current({"shoulder_pan": 3, "gripper": 11}, max_abs_current=10)
    assert len(bus.stopped) == 2
