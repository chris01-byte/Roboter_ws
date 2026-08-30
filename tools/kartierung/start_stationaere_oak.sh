#!/usr/bin/env bash
# Startet die OAK fuer den Stillstandsmodus im selben lokalen DDS-Raum wie
# LiDAR, Odometrie, Scan-Gate und die Diagnose-/Save-Helfer.

set -o pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/amadeus"
LOCAL_OVERLAY="$DATA_ROOT/overlays/stationary-scan-gate-current/install/local_setup.bash"

source /opt/ros/humble/setup.bash
source "$HOME/roboter_ws/install/local_setup.bash"
if [ -f "$LOCAL_OVERLAY" ]; then
    source "$LOCAL_OVERLAY"
fi
source "$SCRIPT_DIR/stationaere_ros_umgebung.sh"

EXISTING_NODES="$(ros2 node list --no-daemon 2>/dev/null || true)"
if printf '%s\n' "$EXISTING_NODES" | rg -F -x -q /oak; then
    echo "ABBRUCH: /oak laeuft im lokalen Stillstands-DDS bereits."
    exit 1
fi

echo ">>> OAK startet rein lokal ueber Loopback; App/KI-Server sehen diesen Lauf nicht."
exec ros2 launch robot_bringup oak.launch.py pointcloud:=false "$@"
