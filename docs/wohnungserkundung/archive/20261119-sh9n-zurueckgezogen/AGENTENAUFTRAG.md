# Aktueller Agentenauftrag: SH-9N – nur lesen: die Fahrten vom 08.11., 15.11. und 19.11. nebeneinander

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 19.11.2026 nach
der Auswertung von SH-9
([Archiv](archive/20261119-sh9-ausgewertet/README.md), STATUS Abschnitt
19.11.2026 abends).

**Anlass.** SH-9 erreichte kein einziges Ziel (16 Anläufe) und kam nicht
durch die Labortür. Am 08.11. (SH-7) erreichte Amadeus mit dem damaligen
Stand 5, 12 und 7 Ziele und fuhr in zwei von drei Fahrten durch dieselbe
Tür. Der Projektinhaber stellt fest: Das ist ein Rückschritt. Bevor wieder
etwas geändert oder gefahren wird, sollen die gespeicherten Fahrten mit
denselben heutigen Werkzeugen nebeneinander stehen (MASTERPLAN §9.1,
Regel 4: Scheitern führt zuerst zu Daten).

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nachträgen, §9 |
| WE-Bezug | WE-M3 (Hauptlinie `self_healing`) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, Klon `~/roboter_worktrees/selbstheilung-v2`; Releases unter `~/.local/share/amadeus/releases/` unverändert |
| Erwartetes Ergebnis | Je gespeicherter Fahrt dieselben Kennzahlen (Anläufe, erreichte Ziele, Anteil Drehen, Drehrate, Tempo, Zähler) und ein Vergleich der Einstellungen der drei Releases |
| Nicht-Ziele | Keine Fahrt, kein Stackstart, kein Build, keine Änderung an Releases, Profilen oder Code; keine Deutung der Ursache |
| Rückfall | Entfällt (nur lesend); der Ausgabeordner `~/selbstheilung_sh9n` kann gelöscht werden |

## Regeln für diesen Auftrag

- **Nur lesen.** Kein `ros2 launch`, kein Knoten, kein Motor, kein Schreiben
  in ein Release oder in `~/roboter_ws`. Alle Ausgaben nach
  `~/selbstheilung_sh9n` (außerhalb des Repositorys).
- **Keine Wohnungsdaten in den Bericht:** keine Kartenkoordinaten, keine
  Bilder. Abstände, Zeiten, Zähler und Einstellungen sind in Ordnung.
- **Nichts reparieren.** Läuft ein Werkzeug mit einer alten Datei nicht,
  die Fehlermeldung wörtlich berichten und beim nächsten Schritt weitermachen.
- Christopher wird für diesen Auftrag nicht gebraucht.

## Schritt 0 – Stand holen

```bash
date -Iseconds
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short | head -5 && \
  git pull --ff-only && git rev-parse HEAD
mkdir -p ~/selbstheilung_sh9n
```

## Schritt 1 – gespeicherte Fahrten finden

```bash
OUT=~/selbstheilung_sh9n; R=~/.local/share/amadeus/releases
for d in "$R"/selbstheilung-sh7-20261108_1617/pruefung/*/ \
         "$R"/selbstheilung-w1-20261115_1801/pruefung/*/ \
         "$R"/selbstheilung-sh9-20261119_1932/pruefung/*/; do
  [ -f "$d/launch.log" ] || continue
  printf '%s  Zeilen=%s  Anlaeufe=%s  Protokoll=%s\n' "$d" \
    "$(wc -l < "$d/launch.log")" "$(grep -c 'Begin navigating' "$d/launch.log")" \
    "$([ -f "$d/protokoll.json" ] && echo ja || echo nein)"
done | tee "$OUT/fahrten.txt"
```

Daraus sechs Fahrten wählen und im Bericht die Zuordnung nennen:

- `s7_1`, `s7_2`, `s7_3`: die drei Fahrten von SH-7 am 08.11. (erwartet
  `sh7_run1` bis `sh7_run3`).
- `w1_1`, `w1_2`: die zwei Wohnungsfahrten von W-1 am 15.11. (nicht die
  Stellproben; erkennbar an den meisten Anläufen).
- `s9_1`: die Fahrt von SH-9 (`sh9_runf1c`).

Fehlt ein Ordner oder heißt er anders: mit
`find "$R" -maxdepth 4 -name launch.log -newermt 2026-11-04` suchen, die
Fundstellen berichten und die passenden nehmen. Fehlt eine Fahrt ganz, das
berichten und mit den übrigen weitermachen.

## Schritt 2 – jede Fahrt mit denselben Werkzeugen auswerten

Für jede der sechs Fahrten einmal ausführen (`NAME` und `DIR` setzen):

```bash
cd ~/roboter_worktrees/selbstheilung-v2; OUT=~/selbstheilung_sh9n
NAME=s7_1; DIR=<Ordner der Fahrt>

python3 tools/kartierung/selbstheilung_anlaeufe.py --json "$OUT/${NAME}_anlaeufe.json" \
  "$DIR/launch.log" > "$OUT/${NAME}_anlaeufe.txt" 2>&1; echo "anlaeufe exit=$?"

if [ -f "$DIR/protokoll.json" ]; then
  python3 tools/kartierung/selbstheilung_ablauf.py --log "$DIR/launch.log" \
    --protokoll "$DIR/protokoll.json" --json "$OUT/${NAME}_ablauf.json" \
    > "$OUT/${NAME}_ablauf.txt" 2>&1; echo "ablauf exit=$?"
fi
# Ohne Protokoll, oder wenn der Aufruf oben mit einem alten Protokoll scheitert:
python3 tools/kartierung/selbstheilung_ablauf.py --log "$DIR/launch.log" \
  --json "$OUT/${NAME}_ablauf_nurlog.json" > "$OUT/${NAME}_ablauf_nurlog.txt" 2>&1; echo "ablauf nur Log exit=$?"

for muster in 'Begin navigating' 'Goal succeeded' 'Goal failed' 'Goal canceled' \
    'Controller patience exceeded' 'detected collision ahead' 'failed to create plan' \
    'Running backup' 'backup completed successfully' 'slowdown for' 'Robot to approach' \
    'harte Quellenstoerung' 'extrapolation into the future' 'process has died'; do
  printf '%s: %s\n' "$muster" "$(grep -c "$muster" "$DIR/launch.log")"
done > "$OUT/${NAME}_zaehler.txt"
grep -m1 -n 'Anfahrverhalten bestaetigt' "$DIR/launch.log" >> "$OUT/${NAME}_zaehler.txt"
cat "$OUT/${NAME}_zaehler.txt"
```

Dazu, unabhängig von den Werkzeugen, die Fahrbefehle an der Basis zählen
(die Zeile `CMD:` schreibt `base_hardware` etwa einmal je Sekunde):

```bash
python3 - "$DIR/launch.log" > "$OUT/${NAME}_cmd.txt" <<'PY'
import re, statistics, sys
vor = dreh = steh = 0
w, v = [], []
for zeile in open(sys.argv[1], errors='ignore'):
    m = re.search(r'CMD: v=([+-][0-9.]+) m/s w=([+-][0-9.]+) rad/s', zeile)
    if not m:
        continue
    a, b = float(m.group(1)), float(m.group(2))
    if abs(a) > 0.005:
        vor += 1; v.append(abs(a))
    elif abs(b) > 0.005:
        dreh += 1; w.append(abs(b))
    else:
        steh += 1
print('CMD-Zeilen: vorwaerts/rueckwaerts', vor, 'drehen', dreh, 'stehen', steh)
print('Median |w| beim Drehen rad/s:', round(statistics.median(w), 3) if w else None)
print('Median |v| beim Fahren m/s:', round(statistics.median(v), 3) if v else None)
PY
cat "$OUT/${NAME}_cmd.txt"
```

## Schritt 3 – Einstellungen der drei Releases nebeneinander

```bash
OUT=~/selbstheilung_sh9n; R=~/.local/share/amadeus/releases
for rel in selbstheilung-sh7-20261108_1617 selbstheilung-w1-20261115_1801 \
           selbstheilung-sh9-20261119_1932; do
  echo "== $rel"
  grep -rn -E "footprint_clearing_enabled|inflation_radius|cost_scaling_factor|desired_linear_vel|rotate_to_heading_angular_vel|rotate_to_heading_min_angle|max_angular_accel|max_allowed_time_to_collision|failure_tolerance|slowdown_ratio|time_before_collision|self_healing_attempt_stall_s|self_healing_scan_rad|self_healing_gap_depth_m|self_healing_goal_timeout|robot_radius" \
    "$R/$rel/product-install"/robot_navigation/share/robot_navigation/config/*.yaml \
    "$R/$rel/product-install"/explore/share/explore/config/*.yaml 2>/dev/null \
    | sed "s|$R/$rel/product-install/||"
done > "$OUT/konfig_vergleich.txt"; wc -l "$OUT/konfig_vergleich.txt"
```

Dazu je Fahrt die Zeile „Anfahrverhalten bestaetigt“ aus Schritt 2 (welche
Anfahrzeit der Antrieb hatte). Fehlt sie in einem alten Log, das berichten.

## Bericht

Datei `~/selbstheilung_jetson_bericht_sh9n.md`:

1. Stand (HEAD), Zuordnung der sechs Fahrten zu ihren Ordnern, was fehlte.
2. Eine Tabelle, eine Zeile je Fahrt: Datum, Release, Dauer, Anläufe,
   erreicht, gescheitert, abgebrochen; aus `fahrbefehle`: Sekunden vorwärts,
   drehen, stehen, ohne Befehl, die Anteile, `w_drehen_median_radps`,
   `v_vorwaerts_median_mps`, `befohlener_weg_vorwaerts_m`; aus den Zählern:
   „detected collision ahead“, „Controller patience exceeded“, „failed to
   create plan“, „Running backup“; die Anfahrzeit.
3. Je Fahrt wörtlich: die Zusammenfassung (JSON-Block) aus
   `*_anlaeufe.txt`, `*_zaehler.txt`, `*_cmd.txt`, und aus `*_ablauf*.txt` die
   Kopfzeilen bis einschließlich der Tabelle „Ziel Vers. erreicht …“.
4. `konfig_vergleich.txt` wörtlich.
5. Alles, was nicht lief, mit Fehlermeldung. Keine Deutung der Ursache.

## Ende

Kein Commit, kein Push, nichts gestartet. Den Bericht an Christopher geben.
