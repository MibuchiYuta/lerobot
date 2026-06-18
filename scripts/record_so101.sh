#!/usr/bin/env bash
set -euo pipefail

# SO-101 dataset recording with cameras integrated.
# Camera/port notes: see scripts/teleoperate_so101.sh (video2 excluded, "wrist" is gripper-mounted).
# Requires `hf auth login` first so dataset push-to-hub works and ${HF_USER} resolves below.

HF_USER="${HF_USER:-$(hf auth whoami 2>/dev/null | head -n 1)}"
DATASET_REPO_ID="${DATASET_REPO_ID:-${HF_USER}/so101_test}"
TASK_DESCRIPTION="${TASK_DESCRIPTION:?Set TASK_DESCRIPTION, e.g. TASK_DESCRIPTION=\"Grab the black cube\"}"
NUM_EPISODES="${NUM_EPISODES:-5}"
EPISODE_TIME_S="${EPISODE_TIME_S:-60}"
RESET_TIME_S="${RESET_TIME_S:-60}"
PUSH_TO_HUB="${PUSH_TO_HUB:-true}"

lerobot-record \
    --robot.type=so101_follower \
    --robot.port=/dev/ttyACM1 \
    --robot.id=so101_follower_1 \
    --robot.cameras="{top: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 30, fourcc: MJPG}, wrist: {type: opencv, index_or_path: /dev/video4, width: 640, height: 480, fps: 30, fourcc: MJPG}}" \
    --teleop.type=so101_leader \
    --teleop.port=/dev/ttyACM0 \
    --teleop.id=so101_leader_1 \
    --display_data=true \
    --dataset.repo_id="${DATASET_REPO_ID}" \
    --dataset.num_episodes="${NUM_EPISODES}" \
    --dataset.single_task="${TASK_DESCRIPTION}" \
    --dataset.episode_time_s="${EPISODE_TIME_S}" \
    --dataset.reset_time_s="${RESET_TIME_S}" \
    --dataset.push_to_hub="${PUSH_TO_HUB}"
