#!/usr/bin/env bash
set -euo pipefail

# SO-101 teleoperation data collection in LeRobotDataset format.
# Camera/port notes: video2 is excluded and "wrist" is gripper-mounted.
# play_sounds is forced off: this container has no speech-dispatcher daemon running, so the
# default vocal announcements (spd-say) crash and abort the whole process on cleanup.
# Run scripts/start_rerun_viewer.sh first and open http://localhost:9090 to see the camera feed --
# this connects to that server instead of spawning a native viewer (no working GPU/X11 in this container).

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

DATASET_REPO_ID="${DATASET_REPO_ID:-${HF_USER:-local}/so101_test}"
TASK_DESCRIPTION="${TASK_DESCRIPTION:?Set TASK_DESCRIPTION, e.g. TASK_DESCRIPTION=\"Grab the black cube\"}"
NUM_EPISODES="${NUM_EPISODES:-5}"
EPISODE_TIME_S="${EPISODE_TIME_S:-60}"
RESET_TIME_S="${RESET_TIME_S:-60}"
PUSH_TO_HUB="${PUSH_TO_HUB:-true}"
RESUME="${RESUME:-false}"

# NUM_EPISODES is how many MORE episodes to record with RESUME=true.
so101_execute lerobot-record \
    --robot.type="${SO101_ROBOT_TYPE}" --robot.port="${SO101_ROBOT_PORT}" \
    --robot.id="${SO101_ROBOT_ID}" --robot.cameras="${SO101_CAMERAS}" \
    --teleop.type="${SO101_TELEOP_TYPE}" --teleop.port="${SO101_TELEOP_PORT}" \
    --teleop.id="${SO101_TELEOP_ID}" --display_data="${SO101_DISPLAY_DATA}" \
    --display_ip="${SO101_DISPLAY_IP}" --display_port="${SO101_DISPLAY_PORT}" \
    --dataset.repo_id="${DATASET_REPO_ID}" --dataset.num_episodes="${NUM_EPISODES}" \
    --dataset.single_task="${TASK_DESCRIPTION}" --dataset.episode_time_s="${EPISODE_TIME_S}" \
    --dataset.reset_time_s="${RESET_TIME_S}" --dataset.push_to_hub="${PUSH_TO_HUB}" \
    --play_sounds=false --resume="${RESUME}"
