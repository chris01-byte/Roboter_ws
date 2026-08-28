#!/usr/bin/env bash
# Startet manuelle LiDAR-Kartierung, bei der slam_toolbox ausschliesslich
# kurze, per Odometrie und OAK-IMU bestaetigte Stillstandsfenster sieht.
#
# Motorloser Aufbau:
#   bash tools/kartierung/start_stationaere_kartierung.sh
#
# Reale, beaufsichtigte Handfahrt ohne VL53 erst nach persoenlicher Freigabe:
#   AMADEUS_FAHRFREIGABE=JA AMADEUS_OHNE_NAHBEREICH=1 \
#     bash tools/kartierung/start_stationaere_kartierung.sh \
#     active_drive:=true manual_teleop:=true

set -o pipefail

DATA_ROOT="${XDG_DATA_HOME:-$HOME/.local/share}/amadeus"
LOCAL_OVERLAY="$DATA_ROOT/overlays/stationary-scan-gate-current/install/local_setup.bash"

source /opt/ros/humble/setup.bash
source "$HOME/amadeus_slam_toolbox_ws/install/setup.bash"
source "$HOME/amadeus_lidar_ws/install/local_setup.bash"
source "$HOME/roboter_ws/install/local_setup.bash"
if [ -f "$LOCAL_OVERLAY" ]; then
    source "$LOCAL_OVERLAY"
fi

STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_DIR="$DATA_ROOT/logs"
LOG_PATH="$LOG_DIR/stationary_mapping_$STAMP.log"
mkdir -p "$LOG_DIR"

ACTIVE=false
for argument in "$@"; do
    [ "$argument" = "active_drive:=true" ] && ACTIVE=true
done

if [ "$ACTIVE" = true ]; then
    if [ "${AMADEUS_FAHRFREIGABE:-NEIN}" != "JA" ]; then
        echo "ABBRUCH: Motorstart braucht die frische Freigabe "
        echo "AMADEUS_FAHRFREIGABE=JA."
        exit 1
    fi
    if [ "${AMADEUS_OHNE_NAHBEREICH:-0}" != "1" ]; then
        echo "ABBRUCH: Dieser einfache Stop-and-go-Modus startet keine VL53-"
        echo "Notbremse. Die beaufsichtigte Ausnahme muss bewusst mit"
        echo "AMADEUS_OHNE_NAHBEREICH=1 bestaetigt werden."
        exit 1
    fi
fi

EXISTING_NODES="$(ros2 node list 2>/dev/null || true)"
for node in \
    /slam_toolbox \
    /base_hardware \
    /amadeus_stl27l \
    /scan_vereinheitlichen \
    /stationary_scan_gate; do
    if printf '%s\n' "$EXISTING_NODES" | rg -F -x -q "$node"; then
        echo "ABBRUCH: $node laeuft bereits; kein Doppelstart."
        exit 1
    fi
done

echo "Pruefe den realen OAK-IMU-Strom motorlos ..."
if ! ros2 run robot_bringup oak_imu_check --duration 3; then
    echo "ABBRUCH: OAK-IMU nicht abgenommen; Scan-Gate bleibt geschlossen."
    echo "Zuerst starten: ros2 launch robot_bringup oak.launch.py"
    exit 1
fi

echo "Stillstandskartierung startet. Log: $LOG_PATH"
echo "Status: ros2 topic echo --once --full-length \
/stationary_scan_gate/status_json"

if [ "$ACTIVE" = true ]; then
    echo ">>> Beaufsichtigter manueller Stop-and-go-Test OHNE VL53."
fi

exec ros2 launch amadeus_lidar_bringup \
    stationary_slam_lidar.launch.py "$@" > "$LOG_PATH" 2>&1
