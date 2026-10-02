#!/usr/bin/env bash
# Shared SO-101 connection settings.
#
# Subproject 1 should provide its connection-layer values through these
# environment variables.  The scripts in this directory deliberately do not
# know about a particular serial-discovery implementation.

SO101_ROBOT_TYPE="${SO101_ROBOT_TYPE:-so101_follower}"
SO101_ROBOT_PORT="${SO101_ROBOT_PORT:-/dev/ttyACM1}"
SO101_ROBOT_ID="${SO101_ROBOT_ID:-so101_follower_1}"
SO101_TELEOP_TYPE="${SO101_TELEOP_TYPE:-so101_leader}"
SO101_TELEOP_PORT="${SO101_TELEOP_PORT:-/dev/ttyACM0}"
SO101_TELEOP_ID="${SO101_TELEOP_ID:-so101_leader_1}"
SO101_CAMERAS="${SO101_CAMERAS:-{top: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 30, fourcc: MJPG}, wrist: {type: opencv, index_or_path: /dev/video4, width: 640, height: 480, fps: 30, fourcc: MJPG}}}"
SO101_DISPLAY_DATA="${SO101_DISPLAY_DATA:-true}"
SO101_DISPLAY_IP="${SO101_DISPLAY_IP:-127.0.0.1}"
SO101_DISPLAY_PORT="${SO101_DISPLAY_PORT:-9876}"

so101_print_command() {
    printf 'Dry run (no device, dataset, or network access):\n  '
    printf '%q ' "$@"
    printf '\n'
}

so101_execute() {
    if [[ "${SO101_DRY_RUN:-false}" == "true" ]]; then
        so101_print_command "$@"
        return 0
    fi
    command "$@"
}

so101_usage() {
    cat <<'EOF'
Usage: script [--dry-run]

--dry-run  Validate the wrapper's argument construction without accessing a
            robot, cameras, local dataset, Hugging Face, or the network.
EOF
}
