#!/bin/bash
# Startet den Stack im LOKALISIERUNGSMODUS auf der vorhandenen Karte.
#   delete_db:=false      -> Karte behalten (sonst waere sie sofort geloescht!)
#   localization:=true    -> Mem/IncrementalMemory=false, es wird nichts angebaut
#   start_at_origin:=true -> OHNE Vorwissen starten (siehe unten)
# Die grosszuegigen Signal-Fristen bleiben, damit auch hier sauber beendet wird.
#
# Zum Vorwissen: Normalerweise laedt RTAB-Map beim Start die zuletzt gespeicherte
# Pose. Der Roboter steht dann sofort "richtig" in der Karte, ohne irgendetwas
# wiedererkannt zu haben - ein Lokalisierungstest misst so nur das Gedaechtnis
# der Datenbank, nicht das Koennen des Roboters. Mit start_at_origin:=true
# beginnt er am Kartenursprung und muss sich seine Position selbst erarbeiten.
#
# Aufruf:  ./start_lokalisierung.sh <logdatei> [start_at_origin]
#          Vorgabe fuer start_at_origin ist true.
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/setup.bash
LOG="$1"
ORIGIN="${2:-true}"
exec ros2 launch robot_bringup slam.launch.py \
    sigterm_timeout:=120 sigkill_timeout:=180 \
    delete_db:=false localization:=true start_at_origin:="$ORIGIN" \
    active_drive:=true safety:=true map_manager:=true \
    > "$LOG" 2>&1
