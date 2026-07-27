#!/bin/bash
# Startet den Stack im LOKALISIERUNGSMODUS auf der vorhandenen Karte.
#   delete_db:=false   -> Karte behalten (sonst waere sie sofort geloescht!)
#   localization:=true -> Mem/IncrementalMemory=false, es wird nichts angebaut
# Die grosszuegigen Signal-Fristen bleiben, damit auch hier sauber beendet wird.
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/setup.bash
LOG="$1"
exec ros2 launch robot_bringup slam.launch.py \
    sigterm_timeout:=120 sigkill_timeout:=180 \
    delete_db:=false localization:=true \
    active_drive:=true safety:=true map_manager:=true \
    > "$LOG" 2>&1
