#!/usr/bin/env bash
set -euo pipefail

# Replay one recorded LeRobotDataset episode on the physical SO-101.
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

DATASET_REPO_ID="${DATASET_REPO_ID:?Set DATASET_REPO_ID to a LeRobotDataset repo id}"
EPISODE="${EPISODE:-0}"
FPS="${FPS:-30}"

so101_execute lerobot-replay --robot.type="${SO101_ROBOT_TYPE}" \
    --robot.port="${SO101_ROBOT_PORT}" --robot.id="${SO101_ROBOT_ID}" \
    --dataset.repo_id="${DATASET_REPO_ID}" --dataset.episode="${EPISODE}" \
    --dataset.fps="${FPS}" --play_sounds=false
