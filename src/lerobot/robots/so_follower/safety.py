"""Fail-closed safety primitives for SO-101 follower teleoperation.

This module intentionally contains no policy for automatically resuming motion.
Once a fault is observed, :class:`SO101SafetyMonitor` stays latched until the
operator starts a new, explicitly armed process.
"""

from __future__ import annotations

import math
import numbers
import time
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol


class TorqueBus(Protocol):
    """Small interface required for an emergency torque-off attempt."""

    motors: Mapping[str, object]

    def disable_torque(self, motors: str | list[str] | None = None, num_retry: int = 0) -> None: ...


@dataclass(frozen=True)
class SafetyLimits:
    """Limits used to reject implausible commands before sending them."""

    max_cycle_s: float = 0.25
    max_position_step: float = 35.0


class SafetyFault(RuntimeError):
    """A latched condition which prohibits any further movement command."""


class SO101SafetyMonitor:
    """Validate command continuity and perform best-effort, per-motor torque-off.

    A torque-off command can itself fail after a USB loss.  Errors are retained
    and reported to the caller, but never cause a later motor to be skipped.
    Physical E-stop or power isolation remains mandatory for unattended use.
    """

    def __init__(
        self,
        bus: TorqueBus,
        limits: SafetyLimits = SafetyLimits(),
        clock: Callable[[], float] = time.monotonic,
    ):
        if limits.max_cycle_s <= 0 or limits.max_position_step <= 0:
            raise ValueError("Safety limits must be positive")
        self.bus = bus
        self.limits = limits
        self._clock = clock
        self._last_cycle: float | None = None
        self._last_action: dict[str, float] | None = None
        self.fault_reason: str | None = None
        self.stop_errors: dict[str, Exception] = {}

    @property
    def is_latched(self) -> bool:
        return self.fault_reason is not None

    def check_action(self, action: Mapping[str, float]) -> None:
        """Fail closed on stalled loop, missing joints, non-finite or jumping data."""
        if self.is_latched:
            raise SafetyFault(f"Safety stop is latched: {self.fault_reason}")
        now = self._clock()
        expected = {f"{name}.pos" for name in self.bus.motors}
        received = set(action)
        if received != expected:
            self.trip(f"incomplete action: expected {sorted(expected)}, got {sorted(received)}")
        if self._last_cycle is not None and now - self._last_cycle > self.limits.max_cycle_s:
            self.trip(f"control heartbeat exceeded {self.limits.max_cycle_s}s")
        for name, value in action.items():
            if not isinstance(value, numbers.Real) or not math.isfinite(value):
                self.trip(f"non-finite action for {name}")
            if self._last_action is not None and abs(value - self._last_action[name]) > self.limits.max_position_step:
                self.trip(f"unexpected position step for {name}")
        self._last_cycle = now
        self._last_action = dict(action)

    def check_present_current(self, currents: Mapping[str, float], max_abs_current: float) -> None:
        """Fail closed on incomplete/invalid telemetry or an excessive motor current.

        Callers must only enable this after establishing the unit and a safe
        measured threshold for their particular STS3215 installation.
        """
        if max_abs_current <= 0:
            raise ValueError("max_abs_current must be positive")
        if self.is_latched:
            raise SafetyFault(f"Safety stop is latched: {self.fault_reason}")
        expected = set(self.bus.motors)
        if set(currents) != expected:
            self.trip(f"incomplete current telemetry: expected {sorted(expected)}, got {sorted(currents)}")
        for motor, current in currents.items():
            if not isinstance(current, numbers.Real) or not math.isfinite(current):
                self.trip(f"non-finite current for {motor}")
            if abs(current) > max_abs_current:
                self.trip(f"over-current / possible collision for {motor}: {current}")

    def trip(self, reason: str) -> None:
        """Latch a fault and attempt torque-off separately for every motor."""
        if not self.is_latched:
            self.fault_reason = reason
            for motor in self.bus.motors:
                try:
                    self.bus.disable_torque(motor, num_retry=5)
                except Exception as exc:  # Safety cleanup must continue for other motors.
                    self.stop_errors[motor] = exc
        raise SafetyFault(reason)
