#!/usr/bin/env bash
set -euo pipefail

# Run a trained policy on the physical SO-101 and store evaluation episodes.
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

POLICY_PATH="${POLICY_PATH:?Set POLICY_PATH to a local checkpoint or Hub policy id}"
DATASET_REPO_ID="${DATASET_REPO_ID:?Set DATASET_REPO_ID (its dataset name must begin eval_)}"
if [[ "${DATASET_REPO_ID##*/}" != eval_* ]]; then
    printf 'Evaluation DATASET_REPO_ID must use a dataset name prefixed with eval_ (for example, org/eval_task): %s\n' \
        "${DATASET_REPO_ID}" >&2
    exit 2
fi
TASK_DESCRIPTION="${TASK_DESCRIPTION:?Set TASK_DESCRIPTION for the evaluation task}"
NUM_EPISODES="${NUM_EPISODES:-10}"
EPISODE_TIME_S="${EPISODE_TIME_S:-60}"
RESET_TIME_S="${RESET_TIME_S:-60}"
PUSH_TO_HUB="${PUSH_TO_HUB:-false}"

so101_execute lerobot-record \
    --robot.type="${SO101_ROBOT_TYPE}" --robot.port="${SO101_ROBOT_PORT}" \
    --robot.id="${SO101_ROBOT_ID}" --robot.cameras="${SO101_CAMERAS}" \
    --display_data="${SO101_DISPLAY_DATA}" --display_ip="${SO101_DISPLAY_IP}" \
    --display_port="${SO101_DISPLAY_PORT}" --dataset.repo_id="${DATASET_REPO_ID}" \
    --dataset.num_episodes="${NUM_EPISODES}" --dataset.single_task="${TASK_DESCRIPTION}" \
    --dataset.episode_time_s="${EPISODE_TIME_S}" --dataset.reset_time_s="${RESET_TIME_S}" \
    --dataset.push_to_hub="${PUSH_TO_HUB}" --policy.path="${POLICY_PATH}" --play_sounds=false
