#!/usr/bin/env bash
# Speichert Karte und editierbaren slam_toolbox-Posegraph ausschliesslich
# lokal. Echte Wohnungsgeometrie darf nicht in das Repository gelangen.

set -o pipefail

source /opt/ros/humble/setup.bash
source "$HOME/amadeus_slam_toolbox_ws/install/setup.bash"
source "$HOME/roboter_ws/install/local_setup.bash"

DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/amadeus"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_DIR="${1:-$DATA_ROOT/lidar_maps/stationary_$STAMP}"
PREFIX="$OUTPUT_DIR/map"

if [[ "$OUTPUT_DIR" != /* ]] || [[ "$OUTPUT_DIR" == *"'"* ]]; then
    echo "ABBRUCH: Ausgabe muss ein absoluter Pfad ohne Apostroph sein."
    exit 1
fi

for suffix in .yaml .pgm .posegraph .data; do
    if [ -e "$PREFIX$suffix" ]; then
        echo "ABBRUCH: Ausgabe existiert bereits: $PREFIX$suffix"
        exit 1
    fi
done

if ! ros2 service list | rg -F -x -q /slam_toolbox/save_map; then
    echo "ABBRUCH: /slam_toolbox/save_map ist nicht bereit."
    exit 1
fi
if ! ros2 service list | rg -F -x -q /slam_toolbox/serialize_map; then
    echo "ABBRUCH: /slam_toolbox/serialize_map ist nicht bereit."
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

echo "Speichere lokale Rasterkarte unter $PREFIX ..."
MAP_RESULT="$(ros2 service call /slam_toolbox/save_map \
    slam_toolbox/srv/SaveMap "{name: {data: '$PREFIX'}}")"
printf '%s\n' "$MAP_RESULT"
if ! printf '%s\n' "$MAP_RESULT" | rg -q 'result=(0|slam_toolbox\.srv\.SaveMap_Response\.RESULT_SUCCESS)'; then
    echo "ABBRUCH: Rasterkarte wurde nicht bestaetigt."
    exit 1
fi

echo "Speichere fortsetzbaren Posegraphen unter $PREFIX ..."
GRAPH_RESULT="$(ros2 service call /slam_toolbox/serialize_map \
    slam_toolbox/srv/SerializePoseGraph "{filename: '$PREFIX'}")"
printf '%s\n' "$GRAPH_RESULT"
if ! printf '%s\n' "$GRAPH_RESULT" | rg -q 'result=(0|slam_toolbox\.srv\.SerializePoseGraph_Response\.RESULT_SUCCESS)'; then
    echo "ABBRUCH: Posegraph wurde nicht bestaetigt."
    exit 1
fi

for suffix in .yaml .pgm .posegraph .data; do
    if [ ! -s "$PREFIX$suffix" ]; then
        echo "ABBRUCH: Erwartete Datei fehlt oder ist leer: $PREFIX$suffix"
        exit 1
    fi
done

echo "OK: Rasterkarte und Posegraph lokal gespeichert: $OUTPUT_DIR"
