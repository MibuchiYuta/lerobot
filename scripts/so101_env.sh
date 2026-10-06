#!/usr/bin/env bash
# Shared SO-101 connection settings.
#
# Subproject 1 should provide its connection-layer values through these
# environment variables.  The scripts in this directory deliberately do not
# know about a particular serial-discovery implementation.

SO101_ROBOT_TYPE="${SO101_ROBOT_TYPE:-so101_follower}"
SO101_ROBOT_PORT="${SO101_ROBOT_PORT:-/dev/ttyACM0}"
SO101_ROBOT_ID="${SO101_ROBOT_ID:-so101_follower}"
SO101_TELEOP_TYPE="${SO101_TELEOP_TYPE:-so101_leader}"
SO101_TELEOP_PORT="${SO101_TELEOP_PORT:-/dev/ttyACM1}"
SO101_TELEOP_ID="${SO101_TELEOP_ID:-so101_leader}"
# Keep /dev/videoN paths: the cameras' by-id entries share a serial number and
# therefore cannot distinguish the devices. Override SO101_CAMERAS if USB
# enumeration changes these paths.
SO101_CAMERAS_DEFAULT='{top: {type: opencv, index_or_path: /dev/video0, width: 640, height: 480, fps: 30, fourcc: MJPG}, wrist: {type: opencv, index_or_path: /dev/video2, width: 640, height: 480, fps: 30, fourcc: MJPG}}'
SO101_CAMERAS="${SO101_CAMERAS:-${SO101_CAMERAS_DEFAULT}}"
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

so101_require_display() {
    local missing=()

    [[ -n "${DISPLAY:-}" ]] || missing+=(DISPLAY)
    [[ -n "${XAUTHORITY:-}" ]] || missing+=(XAUTHORITY)
    if ((${#missing[@]})); then
        printf 'Cannot record with keyboard controls: %s is unset. Set DISPLAY and XAUTHORITY for the graphical session, then retry.\n' \
            "${missing[*]}" >&2
        return 1
    fi
}

so101_usage() {
    cat <<'EOF'
Usage: script [--dry-run]

--dry-run  Validate the wrapper's argument construction without accessing a
            robot, cameras, local dataset, Hugging Face, or the network.
EOF
}
