#!/usr/bin/env bash
# Startet die begrenzte HWT601-Erkundung eines physisch geschlossenen Raums.
# Die Mission wird nach bestandenem Live-Preflight weiterhin separat gesendet.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="$HOME/roboter_ws/install/explore/share/explore/config/hwt601_room_only_params.yaml"

if [ ! -f "$PROFILE" ]; then
    echo "ABBRUCH: installiertes HWT601-Raumprofil fehlt: $PROFILE"
    echo "Paket explore zuerst bauen und installieren."
    exit 1
fi

if [ "${AMADEUS_RAUM_GESCHLOSSEN:-NEIN}" != "JA" ]; then
    echo "ABBRUCH: Raumgrenze nicht bestaetigt."
    echo "Alle Ausgaenge schliessen und AMADEUS_RAUM_GESCHLOSSEN=JA setzen."
    exit 1
fi

for arg in "$@"; do
    case "$arg" in
        active_drive:=*|enable_auto_explore:=*|explore_params_overlay:=*)
            echo "ABBRUCH: Raum-Sicherheitsargumente nicht selbst angeben."
            exit 1
            ;;
    esac
done

echo "HWT601-Raumerkundung: geschlossener Raum, keine Portal-/Tuerfahrt."
exec bash "$SCRIPT_DIR/start_app_erkundung_hwt601.sh" \
    active_drive:=true \
    enable_auto_explore:=true \
    explore_params_overlay:="$PROFILE" \
    "$@"
