#!/usr/bin/env python3
"""SO-101 leader/follower teleoperation with a fail-closed software watchdog.

Use only after the hardware safety checklist in docs/source/so101_safe_setup.md.
This program deliberately requires --arm: it is never appropriate for unattended
operation without a tested physical E-stop and power isolation.
"""

from __future__ import annotations

import argparse
import logging
import time

from lerobot.robots.so_follower import SO101Follower, SO101FollowerConfig
from lerobot.robots.so_follower.safety import SO101SafetyMonitor, SafetyFault, SafetyLimits
from lerobot.teleoperators.so_leader import SO101Leader, SO101LeaderConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--follower-port", required=True)
    parser.add_argument("--leader-port", required=True)
    parser.add_argument("--follower-id", default="so101_follower")
    parser.add_argument("--leader-id", default="so101_leader")
    parser.add_argument("--fps", type=float, default=30.0)
    parser.add_argument("--max-cycle-s", type=float, default=0.25)
    parser.add_argument("--max-position-step", type=float, default=35.0)
    parser.add_argument(
        "--max-present-current",
        type=float,
        help="enable collision detection at a measured, device-specific current limit",
    )
    parser.add_argument("--arm", action="store_true", help="acknowledge physical E-stop has been tested")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.arm:
        raise SystemExit("Refusing to move motors without --arm and a tested physical E-stop.")
    if args.fps <= 0:
        raise SystemExit("--fps must be positive")

    follower = SO101Follower(SO101FollowerConfig(port=args.follower_port, id=args.follower_id))
    leader = SO101Leader(SO101LeaderConfig(port=args.leader_port, id=args.leader_id))
    monitor: SO101SafetyMonitor | None = None
    try:
        leader.connect()
        follower.connect()
        monitor = SO101SafetyMonitor(
            follower.bus, SafetyLimits(max_cycle_s=args.max_cycle_s, max_position_step=args.max_position_step)
        )
        while True:
            cycle_start = time.monotonic()
            action = leader.get_action()
            monitor.check_action(action)
            if args.max_present_current is not None:
                monitor.check_present_current(
                    follower.bus.sync_read("Present_Current"), args.max_present_current
                )
            follower.send_action(action)
            time.sleep(max(0.0, 1.0 / args.fps - (time.monotonic() - cycle_start)))
    except (KeyboardInterrupt, Exception) as exc:
        # Any unexpected communication / processing error is a safety fault.
        if monitor is not None and not monitor.is_latched:
            try:
                monitor.trip(f"teleoperation failure: {type(exc).__name__}: {exc}")
            except SafetyFault:
                pass
        logging.exception("SO-101 teleoperation stopped", exc_info=not isinstance(exc, KeyboardInterrupt))
        return 130 if isinstance(exc, KeyboardInterrupt) else 1
    finally:
        # Both devices must be attempted independently; leader cleanup cannot leave follower powered.
        for device in (follower, leader):
            try:
                if device.is_connected:
                    device.disconnect()
            except Exception:
                logging.exception("device disconnect failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
