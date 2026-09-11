#!/usr/bin/env bash
# Startet genau eine begrenzte, LiDAR-bestaetigte HWT601-Tueretappe.
# Die Mission wird nach bestandenem Live-Preflight weiterhin separat gesendet.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="$HOME/roboter_ws/install/explore/share/explore/config/hwt601_door_only_params.yaml"

if [ ! -f "$PROFILE" ]; then
    echo "ABBRUCH: installiertes HWT601-Tuerprofil fehlt: $PROFILE"
    echo "Paket explore zuerst bauen und installieren."
    exit 1
fi

if [ "${AMADEUS_TUER_OFFEN:-NEIN}" != "JA" ]; then
    echo "ABBRUCH: vollstaendig offene und gesicherte Tuer nicht bestaetigt."
    echo "AMADEUS_TUER_OFFEN=JA erst nach physischer Pruefung setzen."
    exit 1
fi

if [ "${AMADEUS_TUER_VORNE:-NEIN}" != "JA" ]; then
    echo "ABBRUCH: offene Tuer im vorderen Suchsektor nicht bestaetigt."
    echo "Tuer muss vor dem Roboter liegen; AMADEUS_TUER_VORNE=JA setzen."
    exit 1
fi

if [ "${AMADEUS_TUERZIEL_FREI:-NEIN}" != "JA" ]; then
    echo "ABBRUCH: freier Fahr- und Bremsraum hinter der Tuer nicht bestaetigt."
    echo "AMADEUS_TUERZIEL_FREI=JA erst nach physischer Pruefung setzen."
    exit 1
fi

for arg in "$@"; do
    case "$arg" in
        active_drive:=*|enable_auto_explore:=*|explore_params_overlay:=*)
            echo "ABBRUCH: Tuer-Sicherheitsargumente nicht selbst angeben."
            exit 1
            ;;
    esac
done

echo "HWT601-Tuerabnahme: selbst scannen, ausrichten und einmal navigieren."
exec bash "$SCRIPT_DIR/start_app_erkundung_hwt601.sh" \
    active_drive:=true \
    enable_auto_explore:=true \
    explore_params_overlay:="$PROFILE" \
    "$@"
