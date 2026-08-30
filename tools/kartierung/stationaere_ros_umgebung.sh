#!/usr/bin/env bash
# Gemeinsame ROS-/DDS-Umgebung fuer den rein lokalen Stillstandsmodus.
# Dieses Skript wird von Start-, Save- und Diagnosehelfern gesourct.

STATIONAERE_ROS_SCRIPT_DIR="$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd
)"
STATIONAERE_DDS_PROFIL="$STATIONAERE_ROS_SCRIPT_DIR/cyclonedds_stationaer_lokal.xml"

if [ ! -r "$STATIONAERE_DDS_PROFIL" ]; then
    echo "ABBRUCH: Lokales DDS-Profil fehlt: $STATIONAERE_DDS_PROFIL" >&2
    return 1 2>/dev/null || exit 1
fi

# Das globale WLAN-Profil kann feste KI-Server-Peers enthalten. Fuer diesen
# Workflow wird es bewusst und nur im aktuellen Prozess ersetzt.
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_LOCALHOST_ONLY=0
export CYCLONEDDS_URI="file://$STATIONAERE_DDS_PROFIL"

unset STATIONAERE_ROS_SCRIPT_DIR
unset STATIONAERE_DDS_PROFIL
