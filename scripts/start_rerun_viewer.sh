#!/usr/bin/env bash
set -euo pipefail

# Hosts a browser-based Rerun viewer for SO-101 camera/state visualization.
# Run this once in its own terminal and leave it running, then open
# http://localhost:9090 in a browser (VS Code should auto-forward the port;
# check the "Ports" tab if it doesn't).
#
# Why this exists: this devcontainer has no working GPU/X11 path for native
# GUI rendering (confirmed: even after installing libxkbcommon-x11-0, the
# native viewer fails with "WGPU error: No suitable graphics adapter found").
# The web viewer renders client-side in the browser instead, so it sidesteps
# the problem entirely. teleoperate_so101.sh / record_so101.sh point at this
# server via --display_ip/--display_port instead of spawning their own
# (broken) native viewer.

rerun --serve-web --port 9876 --web-viewer-port 9090
