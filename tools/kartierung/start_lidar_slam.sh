#!/usr/bin/env bash
# Startet den STL-27L-SLAM-Stack mit der vollstaendigen Source-Reihenfolge.
#
# Nicht zu verwechseln mit start_slam.sh - das startet den RTAB-Map-Stack aus
# robot_bringup. Beide duerfen NIE gleichzeitig laufen: zwei Publisher fuer
# map->odom ergeben einen springenden Roboter.
#
# VIER Workspaces, nicht drei. Der gepatchte slam_toolbox-Backport liegt in
# ~/amadeus_slam_toolbox_ws, der gepinnte LDROBOT-Treiber in
# ~/amadeus_lidar_ws. Fehlt Letzterer, bricht der Launch mit
# "package 'ldlidar_stl_ros2' not found" ab.
#
# Kein "set -u": die ROS-Setup-Skripte lesen ungesetzte Variablen.
#
# Aufruf:
#   bash tools/kartierung/start_lidar_slam.sh [LOGDATEI] [launch-argumente...]
#
#   bash tools/kartierung/start_lidar_slam.sh /tmp/slam.log
#   bash tools/kartierung/start_lidar_slam.sh /tmp/slam.log active_drive:=true
#
# active_drive:=true bestromt die Motoren. Vorgabe ist false.
# normalize_scan:=false schaltet den Scan-Vereinheitlicher ab; dann verwirft
# Karto rund drei Viertel aller Scans (siehe docs/SLAM_TOOLBOX_ROTATION_FIX.md).
#
# Vor dem Start pruefen, dass nichts laeuft:
#   python3 tools/kartierung/roboterknoten.py --still || echo "laeuft schon"
#
# Beenden: SIGINT NUR an die ros2-launch-PID, nie an die Prozessgruppe. Danach
# mit roboterknoten.py nachsehen, ob wirklich alle Kindprozesse weg sind - sie
# ueberleben den Elternprozess gelegentlich.

source /opt/ros/humble/setup.bash
source "$HOME/amadeus_slam_toolbox_ws/install/setup.bash"
source "$HOME/amadeus_lidar_ws/install/local_setup.bash"
source "$HOME/roboter_ws/install/local_setup.bash"

LOG="${1:-/dev/stdout}"
shift 2>/dev/null

exec ros2 launch amadeus_lidar_bringup slam_lidar.launch.py "$@" \
    > "$LOG" 2>&1
