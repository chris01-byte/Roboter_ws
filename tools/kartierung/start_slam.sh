#!/bin/bash
# Startet den SLAM-Stack scharf (Motoren bestromt, aber OHNE Fahrbefehl).
#
# WICHTIG - Zeitgrenzen fuers Herunterfahren:
# ros2 launch eskaliert nach SIGINT von sich aus auf SIGTERM und dann SIGKILL.
# RTAB-Map schreibt beim Beenden das visuelle Woerterbuch in die Datenbank; je
# groesser die Karte, desto laenger dauert das. Mit den Vorgabewerten (5 s) wird
# es dabei abgeschossen -> Datenbank ohne Woerterbuch -> keine Lokalisierung.
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/setup.bash
LOG="$1"
shift
# sigterm_timeout/sigkill_timeout sind in Humble keine Kommandozeilenoptionen,
# sondern Launch-Konfigurationen, die ExecuteProcess selbst ausliest.
exec ros2 launch robot_bringup slam.launch.py \
    sigterm_timeout:=120 sigkill_timeout:=180 \
    active_drive:=true delete_db:=true safety:=true map_manager:=true "$@" \
    > "$LOG" 2>&1
