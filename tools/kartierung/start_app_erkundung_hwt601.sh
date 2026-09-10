#!/usr/bin/env bash
# Sicherer Opt-in-Wrapper fuer den HWT601-Karten-A/B-Test.
# Der bestehende Encoderstart bleibt start_app_erkundung.sh unveraendert.

set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${AMADEUS_HWT601_STILLSTAND:-NEIN}" != "JA" ]; then
    echo "ABBRUCH: HWT-Startkalibrierung braucht AMADEUS_HWT601_STILLSTAND=JA."
    echo "Roboter waehrend Start und Kalibrierung mindestens 30 s nicht bewegen."
    exit 1
fi

if [ ! -e /dev/ttyUSB_HWT601 ]; then
    echo "ABBRUCH: /dev/ttyUSB_HWT601 fehlt."
    exit 1
fi

if command -v fuser >/dev/null 2>&1 \
        && fuser /dev/ttyUSB_HWT601 >/dev/null 2>&1; then
    echo "ABBRUCH: /dev/ttyUSB_HWT601 ist bereits geoeffnet."
    exit 1
fi

for arg in "$@"; do
    case "$arg" in
        use_hwt601_odometry:=false|operator_stationary_confirmed:=false)
            echo "ABBRUCH: Der HWT-Wrapper erlaubt keine Deaktivierung seiner Sicherheitsargumente."
            exit 1
            ;;
        use_hwt601_odometry:=true|operator_stationary_confirmed:=true)
            echo "ABBRUCH: HWT-Argumente nicht selbst angeben; der Wrapper setzt sie eindeutig."
            exit 1
            ;;
    esac
done

echo "HWT601-Karten-A/B startet. Chassis fuer die ersten 30 s absolut stillhalten."
exec bash "$SCRIPT_DIR/start_app_erkundung.sh" \
    use_hwt601_odometry:=true \
    operator_stationary_confirmed:=true \
    "$@"
