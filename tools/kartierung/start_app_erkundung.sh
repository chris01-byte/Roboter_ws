#!/usr/bin/env bash
# Startet genau einen vollstaendigen App-Kartierungsstack.
# Es wird kein Explore-Auftrag automatisch gesendet. Die App darf ihn erst
# nach frischem Missions-, Sicherheits- und Explorer-Preflight ausloesen.

set -o pipefail

source /opt/ros/humble/setup.bash
source "$HOME/amadeus_slam_toolbox_ws/install/setup.bash"
source "$HOME/amadeus_lidar_ws/install/local_setup.bash"
source "$HOME/roboter_ws/install/local_setup.bash"

if ! python3 "$HOME/roboter_ws/tools/kartierung/roboterknoten.py" --still; then
    echo "ABBRUCH: Es laeuft bereits ein Robotik-Stack."
    echo "Nicht parallel robot.launch.py, smartphone_gui.launch.py oder nav_mapping.launch.py starten."
    exit 1
fi

# roboterknoten.py erlaubt absichtlich passive Kartenwerkzeuge. Dieser
# Gesamtlaunch besitzt sie jedoch selbst und muss deshalb auch deren bereits
# laufende Instanzen vorab erkennen, sonst erscheinen doppelte ROS-Namen.
EXISTING_NODES="$(ros2 node list 2>/dev/null || true)"
for node in \
    /robot_map_manager \
    /semantic_map_manager \
    /rosbridge_websocket \
    /smartphone_gui_server \
    /mission_manager \
    /explore_node; do
    if printf '%s\n' "$EXISTING_NODES" | rg -F -x -q "$node"; then
        echo "ABBRUCH: $node laeuft bereits; App-Stack wuerde ihn doppeln."
        echo "Bestehenden Einzelstart zuerst sauber mit Ctrl-C beenden."
        exit 1
    fi
done

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
    echo "HINWEIS: Basis wird bestromt, App-Erkundung bleibt aber gesperrt."
fi

if [ "$AUTO" = true ] && [ "$ACTIVE" != true ]; then
    echo "HINWEIS: Explorer ist freigeschaltet, Basis bleibt im Dry-Run."
fi

echo "App-Kartierungsstack startet; die App sendet den Erkundungsauftrag separat."
exec ros2 launch robot_bringup app_mapping.launch.py "${ARGS[@]}"
