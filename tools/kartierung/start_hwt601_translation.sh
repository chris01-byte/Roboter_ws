#!/usr/bin/env bash
# Startet ausschliesslich den begrenzten HWT601-Translationsstack.
# Die Mission wird nach bestandenem Live-Preflight weiterhin separat gesendet.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="$HOME/roboter_ws/install/explore/share/explore/config/hwt601_translation_only_params.yaml"

if [ ! -f "$PROFILE" ]; then
    echo "ABBRUCH: installiertes HWT601-Translationsprofil fehlt: $PROFILE"
    echo "Paket explore zuerst bauen und installieren."
    exit 1
fi

for arg in "$@"; do
    case "$arg" in
        active_drive:=*|enable_auto_explore:=*|explore_params_overlay:=*)
            echo "ABBRUCH: Translations-Sicherheitsargumente nicht selbst angeben."
            exit 1
            ;;
    esac
done

echo "HWT601-Translation: 0,50 m LiDAR-bestaetigt; keine Frontier-Fahrt."
exec bash "$SCRIPT_DIR/start_app_erkundung_hwt601.sh" \
    active_drive:=true \
    enable_auto_explore:=true \
    explore_params_overlay:="$PROFILE" \
    "$@"
