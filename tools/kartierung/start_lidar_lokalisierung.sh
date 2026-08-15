#!/usr/bin/env bash
# Startet AMCL + Nav2 mit einer explizit gewaehlten, lokal gespeicherten Karte.
#
# Motorlos:
#   bash tools/kartierung/start_lidar_lokalisierung.sh /absolut/map.yaml \
#     oak:=false
#
# Scharf erst nach der Hardware-Startpruefung und persoenlicher Freigabe:
#   AMADEUS_FAHRFREIGABE=JA bash \
#     tools/kartierung/start_lidar_lokalisierung.sh /absolut/map.yaml \
#     active_drive:=true oak:=false
#
# Beenden: genau einmal Ctrl-C an diesen Launch, nie an die Prozessgruppe.

set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROBOT_WORKSPACE="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
LIDAR_WORKSPACE="${AMADEUS_LIDAR_WORKSPACE:-${HOME}/amadeus_lidar_ws}"

if [ "$#" -lt 1 ]; then
    echo "Fehler: absoluter Pfad zur gespeicherten map.yaml fehlt." >&2
    echo "Aufruf: $0 /absolut/map.yaml [launch-argumente...]" >&2
    exit 2
fi

MAP_INPUT="$1"
shift
if [ "${MAP_INPUT#/}" = "$MAP_INPUT" ] || [ ! -f "$MAP_INPUT" ]; then
    echo "Fehler: Karte muss als vorhandener absoluter Pfad angegeben werden." >&2
    exit 2
fi
case "$MAP_INPUT" in
    *.yaml) ;;
    *)
        echo "Fehler: Kartenpfad muss auf .yaml enden." >&2
        exit 2
        ;;
esac
MAP_YAML="$(realpath -e -- "$MAP_INPUT")"

if [ ! -f "$LIDAR_WORKSPACE/install/local_setup.bash" ]; then
    echo "Fehler: gepinnter STL-27L-Treiber fehlt unter $LIDAR_WORKSPACE." >&2
    exit 2
fi

if ! python3 "$SCRIPT_DIR/roboterknoten.py" --still; then
    echo "Fehler: Ein alter LiDAR-/SLAM-/Basis-Stack laeuft bereits." >&2
    python3 "$SCRIPT_DIR/roboterknoten.py"
    exit 1
fi

ACTIVE_DRIVE=false
for argument in "$@"; do
    if [ "$argument" = "active_drive:=true" ]; then
        ACTIVE_DRIVE=true
    fi
done
if [ "$ACTIVE_DRIVE" = true ] && [ "${AMADEUS_FAHRFREIGABE:-NEIN}" != "JA" ]; then
    echo "ABBRUCH: active_drive:=true verlangt AMADEUS_FAHRFREIGABE=JA." >&2
    echo "Nur nach freier Fahrflaeche und erreichbarem Not-Aus setzen." >&2
    exit 1
fi

# Kein "set -u": ROS-Setup-Skripte lesen ungesetzte Variablen.
source /opt/ros/humble/setup.bash
source "$LIDAR_WORKSPACE/install/local_setup.bash"
source "$ROBOT_WORKSPACE/install/local_setup.bash"

exec ros2 launch robot_navigation nav_localized.launch.py \
    map:="$MAP_YAML" "$@"
