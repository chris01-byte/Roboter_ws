#!/usr/bin/env bash
# Zeichnet ausschliesslich die fuer den Fugen-/Stillstandstest erforderlichen
# ROS-Daten lokal auf. Keine RGB-Bilder und keine Wohnungsdaten ins Git legen.

set -o pipefail

source /opt/ros/humble/setup.bash
source "$HOME/amadeus_slam_toolbox_ws/install/setup.bash"
source "$HOME/amadeus_lidar_ws/install/local_setup.bash"
source "$HOME/roboter_ws/install/local_setup.bash"

DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/amadeus"
STAMP="$(date +%Y%m%d_%H%M%S)"
DEFAULT_OUTPUT="$DATA_ROOT/diagnostics/stationary_mapping_$STAMP"
OUTPUT="${1:-$DEFAULT_OUTPUT}"
PARENT="$(dirname "$OUTPUT")"
mkdir -p "$PARENT"

if [ -e "$OUTPUT" ]; then
    echo "ABBRUCH: Ausgabe existiert bereits: $OUTPUT"
    exit 1
fi

echo "Lokale Diagnoseaufzeichnung: $OUTPUT"
echo "Beenden mit Ctrl-C; diesen Ordner niemals committen."
exec ros2 bag record --output "$OUTPUT" \
    /oak/imu/data \
    /odom \
    /scan \
    /scan_normiert \
    /scan_stillstand \
    /stationary_scan_gate/status_json \
    /tf \
    /tf_static \
    /map \
    /slam_toolbox/graph_visualization
