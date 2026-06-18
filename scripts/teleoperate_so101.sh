#!/usr/bin/env bash
set -euo pipefail

# SO-101 teleoperate with cameras integrated.
# video2 (Anker webcam) is excluded: it's used for video conferencing, not workspace capture.
# "wrist" (video4) is mounted on the gripper itself -- confirmed by rotating wrist_roll and seeing
# the frame rotate in sync, so its view follows the arm rather than needing a fixed repositioning.

lerobot-teleoperate \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.id=so101_follower_1 \
    --robot.cameras="{top: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 30, fourcc: MJPG}, wrist: {type: opencv, index_or_path: /dev/video4, width: 640, height: 480, fps: 30, fourcc: MJPG}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM0 \
    --teleop.id=so101_leader_1 \
    --display_data=true
