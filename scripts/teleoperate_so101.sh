#!/usr/bin/env bash
set -euo pipefail

# SO-101 teleoperate with cameras integrated.
# video2 (Anker webcam) is excluded: it's used for video conferencing, not workspace capture.
# "wrist" (video4) is mounted on the gripper itself -- confirmed by rotating wrist_roll and seeing
# the frame rotate in sync, so its view follows the arm rather than needing a fixed repositioning.
# Run scripts/start_rerun_viewer.sh first and open http://localhost:9090 to see the camera feed --
# this connects to that server instead of spawning a native viewer (no working GPU/X11 in this container).
# Defaults match docs/source/so101_safe_setup.md calibration examples: follower ACM0, leader ACM1.
# If USB enumeration differs, recalibrate and update every SO-101 command consistently.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091 # Runtime path is derived from this script's directory.
source "${SCRIPT_DIR}/so101_env.sh"

while (($#)); do
    case "$1" in
        --dry-run) export SO101_DRY_RUN=true ;;
        --help|-h) so101_usage; exit 0 ;;
        *) printf 'Unknown argument: %s\n' "$1" >&2; so101_usage >&2; exit 2 ;;
    esac
    shift
done

so101_execute lerobot-teleoperate \
    --robot.type="${SO101_ROBOT_TYPE}" --robot.port="${SO101_ROBOT_PORT}" \
    --robot.id="${SO101_ROBOT_ID}" --robot.cameras="${SO101_CAMERAS}" \
    --teleop.type="${SO101_TELEOP_TYPE}" --teleop.port="${SO101_TELEOP_PORT}" \
    --teleop.id="${SO101_TELEOP_ID}" --display_data="${SO101_DISPLAY_DATA}" \
    --display_ip="${SO101_DISPLAY_IP}" --display_port="${SO101_DISPLAY_PORT}"
