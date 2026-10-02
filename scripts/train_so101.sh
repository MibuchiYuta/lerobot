#!/usr/bin/env bash
set -euo pipefail

# Train an ACT or Diffusion Policy from a LeRobotDataset created by record_so101.sh.
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

POLICY="${POLICY:-act}"
case "${POLICY}" in act|diffusion) ;; *) printf 'POLICY must be act or diffusion, got: %s\n' "${POLICY}" >&2; exit 2 ;; esac
DATASET_REPO_ID="${DATASET_REPO_ID:?Set DATASET_REPO_ID to a recorded LeRobotDataset repo id}"
OUTPUT_DIR="${OUTPUT_DIR:-outputs/train/${POLICY}_so101}"
JOB_NAME="${JOB_NAME:-${POLICY}_so101}"
POLICY_DEVICE="${POLICY_DEVICE:-cuda}"
PUSH_TO_HUB="${PUSH_TO_HUB:-false}"
POLICY_REPO_ID="${POLICY_REPO_ID:-}"
EXTRA_TRAIN_ARGS="${EXTRA_TRAIN_ARGS:-}"

if [[ "${PUSH_TO_HUB}" == "true" && -z "${POLICY_REPO_ID}" ]]; then
    printf 'Set POLICY_REPO_ID when PUSH_TO_HUB=true.\n' >&2
    exit 2
fi

command=(lerobot-train --dataset.repo_id="${DATASET_REPO_ID}" --policy.type="${POLICY}"
    --output_dir="${OUTPUT_DIR}" --job_name="${JOB_NAME}" --policy.device="${POLICY_DEVICE}"
    --policy.push_to_hub="${PUSH_TO_HUB}")
if [[ -n "${POLICY_REPO_ID}" ]]; then command+=(--policy.repo_id="${POLICY_REPO_ID}"); fi
# EXTRA_TRAIN_ARGS is intentionally split by the shell for simple CLI overrides.
if [[ -n "${EXTRA_TRAIN_ARGS}" ]]; then read -r -a extra_args <<<"${EXTRA_TRAIN_ARGS}"; command+=("${extra_args[@]}"); fi
so101_execute "${command[@]}"
