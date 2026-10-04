#!/usr/bin/env python3
"""Read-only SO-101 serial-bus diagnostic; never enables torque or sends goals."""

from __future__ import annotations

import argparse
import json

from lerobot.motors import Motor, MotorNormMode
from lerobot.motors.feetech import FeetechMotorsBus


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port")
    args = parser.parse_args()
    motors = {str(index): Motor(index, "sts3215", MotorNormMode.RANGE_M100_100) for index in range(1, 7)}
    bus = FeetechMotorsBus(port=args.port, motors=motors)
    try:
        bus.connect()
        # Calibration is not available yet, so preserve the raw encoder readings.
        raw_encoder_positions = bus.sync_read("Present_Position", normalize=False)
        print(json.dumps({"raw_encoder_positions": raw_encoder_positions}, indent=2, sort_keys=True))
    finally:
        if bus.is_connected:
            # Diagnostic must not change torque state.
            bus.disconnect(disable_torque=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
