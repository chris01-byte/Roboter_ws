# Aktueller Auftrag der KI-Linie: KI-F9N – Auswerten und Erproben im Stand, ohne Fahrt

**Erteilt am 24.11.2026** (Christopher: „ja“ zum Vorschlag KI-F9N). Er wird
aktiv, sobald der Projektinhaber ihn übergibt. Er läuft auf dem **Jetson**,
mit Christopher vor Ort; auf dem **KI-Rechner** muss das Lotsen-Fenster
(„Amadeus Lotse“) laufen. **Amadeus fährt in diesem Auftrag nicht:** keine
Motorfreigabe, kein Missionsstart, kein Fahrziel, keine Drehung.

**Warum es ihn gibt:** In KI-F9 sind drei von vier Wiederholungen vor dem
Fahren gescheitert (Fensterrollo, belegte Kostenkarte, Tür nicht
wiedergefunden), dazu ein Absturz der Aufnahme. Die
[Bewertung](BEWERTUNG_KIF9.md) hat Ursachen gefunden. Danach sind die
Werkzeuge robust gemacht worden (Schritt 1, Abschnitt „Werkzeuge robust
gemacht“ im [STATUS](STATUS.md)); in Tests und Simulation geprüft, **am
Jetson noch nie**. Dieser Auftrag ist Schritt 2 aus Bewertung §10:
1. **Erproben im Stand:** die neuen Werkzeuge am echten Roboter unter ROS 2
   Humble, mit echter Kamera und echtem Laser, ohne dass etwas fährt;
2. **Auswerten:** was in KI-F9 hinter Lauf 2, 2w2 und 2w3 steckte, aus den
   gespeicherten Daten und mit Christophers Antworten vor Ort.

Der vorige Auftrag liegt mit Ergebnis im Archiv:
[KI-F9](archiv/20261124-kif9-ki-waehlt/) (dort auch die Liste aller
früheren).

**Frage dieses Auftrags:** Halten die neuen Werkzeuge am stehenden Roboter
(Aufnahme trotz Signal, Ablaufhilfe von der Kamera bis zum Messen), und was
war in KI-F9 an der Tür, am Fenster und an den Nummern der KI wirklich da?

| | |
|---|---|
| Plan | [Bewertung nach KI-F9](BEWERTUNG_KIF9.md) §10, Schritt 2 (vom Projektinhaber bestätigt am 24.11.2026) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. **Kein Build:** Release `kif8-20261123_2138` mit `~/roboter_worktrees/kif8.env`, beide unverändert. Unter `src/` hat sich seit `d61453c` nichts geändert; neu sind nur Werkzeuge der KI-Linie (Python, direkt aus der Arbeitskopie) |
| Was neu ist | Aufnahme mit Signal-Baustein (endet geordnet bei Strg+C/SIGINT/SIGTERM, schreibt immer); Ablaufhilfe `ki_erkundung/werkzeuge/ki_lauf.py`; Meldungen und Belege im Fahrwerkzeug |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif9n.md`: Tests unter Humble, Signalprobe alt gegen neu (je 30), Vorlauf der Ablaufhilfe im Stand, die Vermessung und die Wahlen der KI-F9-Runden, Christophers Antworten wörtlich |
| Nicht-Ziele | Keine Fahrt, keine Motorfreigabe (kein `active_drive:=true`), kein Missionsstart, kein Fahrziel (`fahrziel_senden.py` nur über `ki_lauf.py messen`, das nur misst), keine Drehung, kein Build, keine Code- oder Parameteränderung, auf dem KI-Rechner nichts löschen |
| Rückfall | `~/ki_trockenlauf_kif9n/` und `$SH_PR/kif9n/` dürfen gelöscht werden, ebenso die heute entstandenen Belege unter `~/.local/share/amadeus/ki_erkundung/belege/` und die Wahl des Vorlaufs. Die Daten von KI-F9 bleiben unberührt. Release und `kif8.env` bleiben unverändert |
| Bereich und Freigabe | Laborraum; Amadeus steht. Rein lesender Vorlauf ohne Motorsteuerung nach LAB-1 §3. Eine Vorabfrage (F0), danach die Fragen O-1 bis O-6 zur Auswertung, einzeln |

## Fragen an Christopher – nur diese

Gefragt wird als Text, einzeln, ohne Auswahlfeld; Antworten wörtlich in den
Bericht.

1. **Vorab, genau einmal (F0)**, in Schritt 3, wörtlich:

   > „Heute fährt Amadeus nicht: Die Motoren werden nicht freigegeben, es
   > gibt keine Mission, er dreht sich auch nicht. Ich prüfe am stehenden
   > Roboter die neuen Werkzeuge (Kamera, Aufnahme, die KI fragen, nur
   > messen) und werte KI-F9 aus. Am Ende stelle ich dir einzeln ein paar
   > kurze Fragen zu KI-F9 (was neben der Tür steht, wo du standest, was
   > die Nummern der KI waren). Ist alles so: Amadeus steht still im
   > Laborraum, nichts auf ihm, der Arm in Transportstellung, und auf dem
   > KI-Rechner ist ‚Amadeus Lotse' geöffnet? Wenn du ‚ja' schreibst,
   > starte ich.“

   Nur nach „ja“ weiter. Das „ja“ gilt auch als Bestätigung, dass Amadeus
   stillsteht (`operator_stationary_confirmed:=true`).
2. **O-1 bis O-6** in Schritt 9.
3. **Nur in der Ausnahme** „Lotsen-Dienst nicht bereit“ (Schritt 4).

Keine weitere Frage, keine Frage nach freien Motoren, keine Bestätigung
unveränderter Laborbedingungen.

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push, **kein
  Build**;
- **kein Start mit `active_drive:=true`**, kein Missionsstart, kein
  `topic pub`, kein `param set`, `lifecycle set` oder `service call`;
- `fahrziel_senden.py` nur über `ki_lauf.py messen` (das ruft es mit
  `--nur-messen` auf und sendet nichts); `ki_lauf.py antwort` nur einmal in
  Schritt 6 mit dem Wortlaut „nein“ (zur Probe, dass es im Vorlauf ablehnt),
  **nie mit „ja“**;
- die Kamera läuft nur in Schritt 5 und 6;
- Signale nur als **genau ein** SIGINT an eine einzelne, geprüfte PID; keine
  Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- nichts in `~/roboter_ws`, nichts an Umgebungsdateien und Releases;
- auf dem KI-Rechner nichts löschen (dort liegen die Antworten der KI aus
  KI-F9; der Lotse behält nur die letzten zehn Fragen, dieser Auftrag stellt
  genau eine neue);
- **keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht; Wahl-Dateien nie anzeigen** (sie enthalten Koordinaten der
  Karte). Erlaubt sind die Zeilen der Werkzeuge mit Maßen vom Roboter aus:
  `wahl.txt` ohne Pfade, die Tabellen von `vermessung_pruefen.py`, die
  Ausgaben von `ki_lauf.py`.

## Vorab festgelegte Kriterien

| Kennung | Kriterium |
|---|---|
| T-1 Tests | Tests der KI-Linie unter Humble: `0 failed` (hier unter ROS 2 Jazzy: 409 bestanden) |
| U-1 Umgebungen | `ki_lauf.py pruefe-umgebung`: „Umgebungen passen.“ |
| S-1 Aufnahme neu | 30 von 30 Aufnahmen schreiben trotz SIGINT mitten im Lesen eine Runde („Blickrunde geschrieben“), 0-mal `Traceback`, jede mit `rc=0` |
| S-2 Aufnahme alt | wird nur gezählt (Gegenprobe): wie oft die Fassung aus KI-F9 nach demselben Signal keine Runde schreibt oder mit `Unable to convert call argument` abbricht. 0-mal heißt: Das Problem ließ sich im Stand nicht nachstellen |
| V-1 Ablaufhilfe im Stand | `start --nur-stand`: Zeile `BEREIT` mit `bilder_hz` mindestens 1,8 und „Aufnahme im Stand läuft“; `wahl`: „Vorlauf im Stand: Wahl der KI mit Kennung …“ oder „Keine Wahl der KI (rc=2)“ bzw. „(rc=4)“, aber nicht „Lage in der Karte fehlt“, „keine Runde“, rc 3, 5 oder 6; `messen` (nur nach einer Wahl): „Nur gemessen, nichts gesendet“; `antwort … nein`: „keine Wahl, zu der eine Antwort passen könnte“; `aufraeumen`: „Alles beendet.“; in `signale.json` genau eine PID; Amadeus hat sich nicht bewegt |
| B-1 Belege | nach `messen`: ein neuer Ordner unter `~/.local/share/amadeus/ki_erkundung/belege/` mit mindestens einer `messung_N.json` |
| A-1 Vermessung KI-F9 | für jede KI-F9-Runde die Tabellen „Angeboten“ und „Verworfen“; für Lauf 2: ob die Labortür verworfen wurde, mit Grund, und welche Lücke sie verdrängt hat |
| A-2 Wahlen KI-F9 | je KI-F9-Frage die Uhrzeit, die Nummern mit Maßen und die Einordnung der KI (aus `wahl.txt`) |
| O-1 bis O-6 | Christophers Antworten wörtlich |

Gesamt: **G-1: T-1, U-1, S-1, V-1 und B-1 treffen zu, A-1, A-2 und O-1 bis
O-6 sind festgehalten.**

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls -d ~/.local/share/amadeus/releases/kif8-20261123_2138 ~/roboter_worktrees/kif8.env ~/ki_trockenlauf_ki0/umgebung_we1.bash
ls -d ~/ki_trockenlauf_kif9n 2>/dev/null && echo "KIF9N-ORDNER GIBT ES SCHON"
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.
Fehlt eines der drei Dinge der `ls`-Zeile: berichten, Ende. Gibt es
`~/ki_trockenlauf_kif9n` schon: nicht löschen, berichten, Ende.

## Schritt 1 – Stand holen (kein Build)

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
echo "src-Aenderungen: $(git diff --name-only d61453c HEAD -- src/ | wc -l)"
source ~/roboter_worktrees/kif8.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
mkdir -p "$SH_PR/kif9n" ~/ki_trockenlauf_kif9n
```

Erwartet: `src-Aenderungen: 0`, `rc=0`, `SH_REL` endet auf
`kif8-20261123_2138`. Sonst: nichts starten, berichten. **Jeder ROS-Befehl
der ersten Shell beginnt mit `source ~/roboter_worktrees/kif8.env`, jeder
der zweiten mit `source ~/ki_trockenlauf_ki0/umgebung_we1.bash`.**

## Schritt 2 – Tests der KI-Linie (unter Humble)

```bash
cd ~/roboter_worktrees/selbstheilung-v2; source ~/roboter_worktrees/kif8.env
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3 ) | tee "$SH_PR/kif9n/tests.txt"
```

Dauert einige Minuten. Darin steckt schon eine Signalprobe unter Humble
(zehnmal mit nachgestellten Sensoren). Erwartung T-1. Bei Fehlschlägen:
nichts starten, die Namen der fehlgeschlagenen Tests berichten, Ende.

## Schritt 3 – die eine Frage (F0)

Christopher F0 stellen (Wortlaut oben). Nur nach „ja“ weiter.

## Schritt 4 – Stack ohne Motorfreigabe starten (erste Shell)

Wie der Vorlauf in KI-F9 (LAB-1 §3). Amadeus bewegt sich nicht.

```bash
source ~/roboter_worktrees/kif8.env
D="$SH_PR/kif9n"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  initial_scan_only:=true stage_drive_only:=true nahsensoren:=false \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9n"; L="$D/launch.log"
{ ros2 param get /explore_node initial_scan_only 2>&1
  ros2 param get /explore_node stage_drive_only 2>&1
  echo "Traceback: $(grep -c Traceback "$L")"; } | tee "$D/pruefung.txt"
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
timeout 15 ros2 topic echo --once --full-length /ki_erkundung/lotse_status_json > ~/ki_trockenlauf_kif9n/lotse_status.txt 2>&1
grep -o '"bereit": [a-z]*' ~/ki_trockenlauf_kif9n/lotse_status.txt
```

Erwartet: `True`, `True`, `Traceback: 0`, `"bereit": true`. Weicht eine
Prüfzeile ab: Stack beenden (Schritt 7), berichten, Ende.

**Lotsen-Dienst nicht bereit (Ausnahme):** Christopher einmal bitten: „Bitte
öffne auf dem KI-Rechner ‚Amadeus Lotse' und schreib ‚fertig'.“ Danach die
beiden letzten Zeilen wiederholen; ist er dann nicht bereit: Stack beenden,
berichten, Ende.

## Schritt 5 – Signalprobe: Aufnahme alt gegen neu (zweite Shell)

Die Aufnahme bekommt 4 bis 8 s nach dem Start, mitten im Lesen, **genau ein**
SIGINT, je 30-mal: zuerst die Fassung aus KI-F9 (`30e72a4`), dann die neue.
Die alte Fassung wird dafür nur ausgelesen (`git archive`), nicht
ausgecheckt; die Runden landen in eigenen Ordnern, nicht bei den
Blickrunden.

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_kif9n; cd ~/roboter_worktrees/selbstheilung-v2
mkdir -p "$KI/alt" && git archive 30e72a4 ki_erkundung | tar -x -C "$KI/alt"
ls "$KI/alt/ki_erkundung/werkzeuge/blickrunde_aufnehmen.py"
nohup env --default-signal=INT ros2 launch robot_bringup oak.launch.py pointcloud:=false \
  > "$KI/oak_probe.log" 2>&1 < /dev/null & echo $! > "$KI/oak.pid"
sleep 25
timeout -s INT 15 ros2 topic hz /oak/semantic/rgb/compressed > "$KI/rate_probe.txt" 2>&1; tail -2 "$KI/rate_probe.txt"
```

Ist die Rate unter 1,8 Hz: Kamera beenden (letzter Block dieses Schritts),
Stack beenden, berichten, Ende. Sonst:

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_kif9n; cd ~/roboter_worktrees/selbstheilung-v2
for art in alt neu; do
  if [ "$art" = alt ]; then SKRIPT="$KI/alt/ki_erkundung/werkzeuge/blickrunde_aufnehmen.py"; MEHR=""
  else SKRIPT="ki_erkundung/werkzeuge/blickrunde_aufnehmen.py"; MEHR="--bereit-nach 2"; fi
  mkdir -p "$KI/probe_$art"
  for i in $(seq 1 30); do
    env --default-signal=INT python3 "$SKRIPT" --name "kif9n_${art}_$i" --dauer 60 \
      --ausgabe "$KI/probe_${art}_runden" $MEHR > "$KI/probe_$art/$i.txt" 2>&1 < /dev/null &
    P=$!; sleep $(( 4 + RANDOM % 5 )); kill -INT "$P"
    for t in $(seq 1 30); do kill -0 "$P" 2>/dev/null || break; sleep 1; done
    if kill -0 "$P" 2>/dev/null; then echo "HAENGT nach SIGINT (PID $P)" | tee -a "$KI/probe_$art/$i.txt"; break 2; fi
    wait "$P"; echo "rc=$?" >> "$KI/probe_$art/$i.txt"
  done
done
for art in alt neu; do
  echo "$art: Runden geschrieben $(grep -l 'Blickrunde geschrieben' "$KI"/probe_$art/*.txt | wc -l) von $(ls "$KI"/probe_$art/*.txt | wc -l)," \
    "Traceback $(grep -l Traceback "$KI"/probe_$art/*.txt | wc -l)," \
    "Unable-to-convert $(grep -l 'Unable to convert' "$KI"/probe_$art/*.txt | wc -l)," \
    "rc ungleich 0: $(grep -L '^rc=0$' "$KI"/probe_$art/*.txt | wc -l)"
done | tee "$KI/probe_ergebnis.txt"
```

Dauert etwa zehn Minuten. **Hängt eine Aufnahme** nach dem Signal länger als
30 s („HAENGT“): kein zweites Signal; die Probe endet dort; PID und letzte
Zeilen in den Bericht; weiter mit dem nächsten Block.

Dann die Kamera beenden (genau ein SIGINT) und nachsehen, dass nichts mehr
liest:

```bash
KI=~/ki_trockenlauf_kif9n; cd ~/roboter_worktrees/selbstheilung-v2
kill -INT "$(cat "$KI/oak.pid")"; sleep 10
python3 -c "import sys; sys.path.insert(0, 'ki_erkundung/werkzeuge'); import ki_lauf; \
print(ki_lauf.laufende('oak.launch.py', 'blickrunde_aufnehmen.py') or 'Kamera und Aufnahmen beendet')"
```

(Kein `pgrep -f`: Es träfe auch die eigene Shell, AGENTS.md §3. Die Prüfung
der Ablaufhilfe vergleicht ganze Argumente und nimmt die eigenen Vorfahren
aus.)

Steht da noch ein Prozess: kein weiteres Signal, berichten, Schritt 6
auslassen, weiter mit Schritt 7.

## Schritt 6 – Vorlauf der Ablaufhilfe im Stand (eine Shell genügt)

Die Ablaufhilfe lädt ihre Umgebungen selbst. Sie startet Kamera und
Aufnahme (10 s im Stand), beendet die Kamera, fragt die KI **genau einmal**
und misst nur. Es gibt keine Mission, und sie sendet nichts.

```bash
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif9n
$H pruefe-umgebung 2>&1 | tee "$O/umgebung.txt"
```

Erwartet U-1 („Umgebungen passen.“). Sonst: nichts weiter in diesem
Schritt, weiter mit Schritt 7.

```bash
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif9n
$H start --auftrag kif9n --lauf v1 --nur-stand 2>&1 | tee "$O/v1_start.txt"; echo "rc=${PIPESTATUS[0]}"
$H wahl --auftrag kif9n --lauf v1 2>&1 | grep -v "^Wahl-Datei" | tee "$O/v1_wahl.txt"; echo "rc=${PIPESTATUS[0]}"
```

Gibt `wahl` `rc=10` („Läuft noch“): dieselbe Zeile noch einmal (höchstens
dreimal). Hat `wahl` eine Wahl mit Kennung gemeldet (`rc=0`):

```bash
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif9n
$H messen --auftrag kif9n --lauf v1 2>&1 | tee "$O/v1_messen.txt"; echo "rc=${PIPESTATUS[0]}"
ls -t ~/.local/share/amadeus/ki_erkundung/belege/ | head -2; ls "$(ls -td ~/.local/share/amadeus/ki_erkundung/belege/*/ | head -1)"
```

In jedem Fall danach:

```bash
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif9n
K=$(python3 -c "import json; print((json.load(open('$O/laufv1/zustand.json')).get('wahl') or {}).get('kennung') or 'abcdef')")
$H antwort --auftrag kif9n --lauf v1 --kennung "$K" --wortlaut "nein" 2>&1 | tee "$O/v1_antwort.txt"; echo "rc=${PIPESTATUS[0]}"
$H aufraeumen --auftrag kif9n --lauf v1 2>&1 | tee "$O/v1_aufraeumen.txt"
cat "$O/laufv1/signale.json"; tail -5 "$O/laufv1/ablauf.log"
```

Erwartet V-1 und (nach `messen`) B-1. `antwort` muss ablehnen, weil ein
Vorlauf keine Frage hat; es ruft dabei nichts auf.

## Schritt 7 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif8.env; kill -INT "$(cat "$SH_PR/kif9n/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

## Schritt 8 – KI-F9 auswerten (nur lesen, kein Sensor)

```bash
cd ~/roboter_worktrees/selbstheilung-v2; O=~/ki_trockenlauf_kif9n
B=~/.local/share/amadeus/ki_erkundung
ls -d "$B"/blickrunden/kif9_* | tee "$O/kif9_runden.txt"
ls "$B"/wahl/ | grep '^kif9_.*_protokoll.json$' | tee "$O/kif9_fragen.txt"
for r in "$B"/blickrunden/kif9_*; do
  python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$r" --alle
done > "$O/kif9_vermessung.md" 2>&1; grep -c "^## " "$O/kif9_vermessung.md"
for f in ~/ki_trockenlauf_kif9/*wahl*.txt ~/ki_trockenlauf_kif9/*/wahl.txt; do
  echo "== $f"; grep -v "^Wahl-Datei\|^Protokoll" "$f"
done > "$O/kif9_wahlen.txt" 2>&1; cat "$O/kif9_wahlen.txt"
```

Die Namen der Protokolle enthalten Datum und Uhrzeit der Frage
(`…_JJJJMMTT_HHMMSS_protokoll.json`); damit findet Christopher die Fragen im
Lotsen-Fenster (O-5). `kif9_vermessung.md` enthält nur Maße vom Roboter aus
und kommt ganz in den Bericht. Für Lauf 2 dort nachsehen: Steht unter
„Verworfen“ eine Lücke von etwa der Türbreite, und mit welchem Grund? Welche
Lücke hat sie überdeckt (Breite, Richtung, zweite Kante)?

## Schritt 9 – Fragen an Christopher (O-1 bis O-6, einzeln)

Jede Frage einzeln als Text, auf die Antwort warten, wörtlich festhalten.

- **O-1:** „Was steht vom Laborraum aus gesehen rechts neben dem Rahmen der
  Labortür? Bitte grob: was es ist, wie weit es von der Wand absteht, wie
  weit es vom Türrahmen entfernt ist, und ob es höher als 75 cm ist.“
- **O-2:** „In den Wiederholungen 2w2 und 2w3: Wo standest du beim Rundblick
  und beim ‚ja'? Und hast du Amadeus zwischen diesen beiden Läufen versetzt?
  (Gemessen ist eine belegte Stelle in Hüfthöhe etwa 1,9 m links von ihm,
  ungefähr auf Höhe seines Hecks.)“
- **O-3:** „Am Fenster mit dem Rollo: Wie hoch über dem Boden liegen die
  Unterkante der Scheibe und die Unterkante des Rollos, so wie es in Lauf 2
  stand? Steht davor etwas, zum Beispiel ein Regal?“
- **O-4:** „Wo sitzt der Not-Aus: am Gehäuse, an einem Kabel oder als
  Funktaster?“
- **O-5:** „Bitte öffne im Lotsen-Fenster nacheinander die Fragen aus KI-F9
  von <Uhrzeiten aus `kif9_fragen.txt`, mit Lauf> und schreib mir je
  Nummer kurz, was dort wirklich ist (zum Beispiel ‚Lauf 1: Nr. 1 Labortür,
  Nr. 2 Regal'). Besonders: Was ist Nr. 2 in Lauf 1?“ Dazu die Zeilen
  „Nr. …“ aus `kif9_wahlen.txt` je Lauf mitschicken (ohne Pfade).
- **O-6:** „Damit die Antworten der KI aus KI-F9 erhalten bleiben (der Lotse
  behält nur die letzten zehn Fragen): Kopierst du bitte auf dem KI-Rechner
  den Ordner `~/.local/share/amadeus/ki_erkundung/lotse/fragen` nach
  `~/ki_erkundung_kif9_fragen` und schreibst ‚fertig'?“

Fehlen im Lotsen-Fenster Fragen aus KI-F9: festhalten, welche; nicht
nachfragen.

## Abbruch

- **Bewegt sich Amadeus** (Räder, Drehung) oder klingt etwas ungewöhnlich:
  Christopher drückt den Not-Aus; Agent beendet Aufnahme, Kamera und Stack
  mit je einem SIGINT, startet nichts mehr und berichtet.
- Hängt ein Werkzeug (keine neue Zeile über 5 Minuten): kein zweites
  Signal, Stack beenden (Schritt 7), berichten.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um einen Schritt „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif9n.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen, ohne den Inhalt der Wahl-Dateien:

1. Stand (HEAD), die Zeile `src-Aenderungen`, `tests.txt`.
2. F0 und Christophers Antwort wörtlich; `pruefung.txt`, ob der Lotse bereit
   war.
3. Signalprobe: `rate_probe.txt` (letzte Zeilen), `probe_ergebnis.txt`; bei
   jeder Aufnahme ohne Runde oder mit `rc` ungleich 0 deren Datei ganz; bei
   „HAENGT“ PID und letzte Zeilen.
4. Ablaufhilfe: `umgebung.txt`, `v1_start.txt`, `v1_wahl.txt`,
   `v1_messen.txt` (falls vorhanden), `v1_antwort.txt`,
   `v1_aufraeumen.txt`, `signale.json`, die letzten Zeilen von `ablauf.log`,
   die Zeilen zu den Belegen. Hat sich Amadeus bewegt? (Christophers
   Beobachtung, falls er etwas gesagt hat.)
5. KI-F9: `kif9_runden.txt`, `kif9_fragen.txt`, **`kif9_vermessung.md`
   ganz**, `kif9_wahlen.txt` ganz (ohne Pfade); für Lauf 2 der Befund aus
   Schritt 8 mit Zahlen.
6. O-1 bis O-6: Frage und Antwort wörtlich.
7. Die Tabelle T-1, U-1, S-1, S-2, V-1, B-1, A-1, A-2 mit dem Gemessenen und
   „trifft zu“ oder „trifft nicht zu“, dazu G-1.
8. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
