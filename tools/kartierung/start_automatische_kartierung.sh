#!/usr/bin/env bash
# Startet die fail-closed LiDAR-Kartierung mit Nav2-Frontier-Exploration.
# Der Launch sendet selbst KEIN Explore-Goal. Erst nach dem Live-Preflight
# darf genau ein Auftrag ueber /mission_manager/command_json folgen.

set -o pipefail

source /opt/ros/humble/setup.bash
source "$HOME/amadeus_slam_toolbox_ws/install/setup.bash"
source "$HOME/amadeus_lidar_ws/install/local_setup.bash"
source "$HOME/roboter_ws/install/local_setup.bash"

if ! python3 "$HOME/roboter_ws/tools/kartierung/roboterknoten.py" --still; then
    echo "ABBRUCH: Es laeuft bereits ein Robotik-Stack."
    exit 1
fi

ARGS=("$@")
ACTIVE=false
AUTO=false
for arg in "${ARGS[@]}"; do
    [ "$arg" = "active_drive:=true" ] && ACTIVE=true
    [ "$arg" = "enable_auto_explore:=true" ] && AUTO=true
done

if [ "$ACTIVE" = true ] && [ "${AMADEUS_FAHRFREIGABE:-NEIN}" != "JA" ]; then
    echo "ABBRUCH: active_drive braucht AMADEUS_FAHRFREIGABE=JA."
    exit 1
fi

if [ "$ACTIVE" = true ] && [ "$AUTO" != true ]; then
    echo "HINWEIS: Basis wird bestromt, aber Explore-Fahrtor bleibt gesperrt."
fi

exec ros2 launch robot_navigation nav_mapping.launch.py "${ARGS[@]}"
