#!/bin/bash
# Beendet den SLAM-Stack SO, dass RTAB-Map sein Woerterbuch noch schreiben kann.
#
# DER ENTSCHEIDENDE PUNKT:
# SIGINT geht NUR an den ros2-launch-Prozess, NICHT an die Prozessgruppe.
# Ein "kill -INT -$PGID" trifft rtabmap doppelt (einmal direkt vom Kernel,
# einmal weitergereicht von launch). Das erste Signal startet das Speichern,
# das zweite bricht es ab -> Datenbank ohne Woerterbuch -> keine Lokalisierung.
# Gemessen am 27.07.2026: rtabmap starb mit "exit code -2" (= SIGINT), die
# Datenbank hatte 831 Knoten und 0 Woerter.
set -u
DB="${1:-$HOME/.local/share/amadeus/rtabmap.db}"

PID=$(pgrep -f "ros2 launch.*slam.launch.py" | head -1)
if [ -z "$PID" ]; then
    echo "Kein laufender slam.launch.py gefunden."
    exit 0
fi
echo "SIGINT an den Launch-Prozess $PID (NICHT an die Gruppe) ..."
kill -INT "$PID"

# Warten, bis rtabmap von selbst weg ist. Es schreibt dabei das Woerterbuch.
for i in $(seq 1 120); do
    if ! pgrep -x rtabmap > /dev/null 2>&1; then
        echo "rtabmap nach ${i}s beendet."
        break
    fi
    sleep 1
done
sleep 3

echo "=== Kontrolle: Woerterbuch in der Datenbank ==="
python3 - "$DB" <<'PYEOF'
import sqlite3, sys
try:
    c = sqlite3.connect(sys.argv[1]); cur = c.cursor()
    cur.execute('SELECT COUNT(*) FROM Node'); n = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Word'); w = cur.fetchone()[0]
    print(f'  {n} Knoten, {w} Woerter')
    print('  OK - Woerterbuch geschrieben, Lokalisierung moeglich.' if w > 0
          else '  FEHLER - Woerterbuch fehlt, Karte NICHT lokalisierbar.')
except Exception as exc:
    print('  Datenbank nicht lesbar:', exc)
PYEOF

echo "=== noch laufende Knoten ==="
ps -eo pid,cmd | grep -E "rtabmap_slam|base_hardware|depthai|vl53_near|collision_monitor|component_container" | grep -v grep
echo "(leer = alles beendet)"
