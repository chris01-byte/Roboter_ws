# Aktueller Auftrag der KI-Linie: KI-F7 – noch einmal selbst ausrichten und durch die Tür

**Erteilt am 23.11.2026.** Er wird aktiv, sobald der Projektinhaber ihn
übergibt. Er läuft auf dem **Jetson**, mit Christopher. Der KI-Rechner wird
nicht gebraucht; Kamera und KI laufen in diesem Auftrag nicht.

**Warum es ihn gibt:** In KI-F6 hat Amadeus die Tür gefunden, ist selbst zu
ihr gefahren und hat sich ausgerichtet (Christopher: „ja er hat die Tür
gefunden ist zu ihr gefahren und hat sich ausgerichtet“). Die Durchfahrt
brach nach 0,67 m ab. Ursache waren **zwei Programmfehler im Erkunder**,
nicht die Räder: (1) Die gerade Etappe las erst die Uhr und dann die
Odometrie; kam dazwischen ein neuer Odometriewert, galt er als Wert „aus der
Zukunft“, und die Etappe endete sofort mit `odom_stale`. Für das Drehen war
genau das seit dem 29.09. behoben (`f746b1c`), für die gerade Etappe nicht.
(2) Die Schlussmeldung nutzte dieselbe Programmstelle erst für eine
Erfolgs-, dann für eine Fehlermeldung; das verbietet ROS und warf „Logger
severity cannot be changed between calls.“ Beides ist behoben und mit Tests
belegt, die den Fehler am alten Stand nachstellen. Weil sich der Erkunder
geändert hat, braucht es **einen neuen Build**. Sonst ist alles wie in
KI-F6: gleiche Profile, gleiche Startdateien, gleiches Fahrtor.

**Ohne Nahsensoren**, wie vom Projektinhaber am 22.11.2026 entschieden
(`nahsensoren:=false`): Amadeus sieht nichts unter etwa 75 cm Höhe, und der
Kollisionsmonitor bremst nicht. Vor der Fahrt räumt Christopher den Weg frei
und bestätigt das; seine Hand bleibt am Not-Aus.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](archiv/20261121-ki0-erstes-sehen/),
[KI-0N](archiv/20261121-ki0n-nachmessen/),
[KI-0R](archiv/20261121-ki0r-nachrechnen/),
[KI-1](archiv/20261121-ki1-blickrunde/),
[KI-F1](archiv/20261122-kif1-erste-etappen/),
[KI-F2](archiv/20261122-kif2-tuerdurchfahrt/),
[KI-F3 und KI-F3b](archiv/20261122-kif3-tuer-gerade/),
[KI-F4](archiv/20261122-kif4-ersetzt/),
[KI-F5](archiv/20261123-kif5-ohne-nahsensoren/),
[KI-F6](archiv/20261123-kif6-anfahrt-gelungen/).

**Frage dieses Auftrags:** Fährt Amadeus, nachdem er sich selbst vor die Tür
gestellt hat, jetzt auch ohne Hilfe hindurch?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md`, Abschnitt 6a |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. **Neuer Build** in einen neuen Release-Ordner `kif7-<STAMP>` mit eigener Umgebungsdatei `~/roboter_worktrees/kif7.env` (Kopie von `kif5.env`). Gegenüber dem Release `kif5-20261123_0950` ist nur `explore_node.py` geändert |
| Was neu ist | Erkunder, nur in der Etappenfahrt (`stage_drive_only:=true`): erst Odometrie und Scan lesen, dann die Uhr; die Schlussmeldung in zwei getrennten Aufrufen. Fristen, Grenzen und Sperren unverändert. Am Roboter wie in KI-F6: `stage_drive_only:=true nahsensoren:=false`, Werkzeug `--zur-tuer` |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif7.md`: Build, Tests, die Prüfungen „ohne Nahsensoren“, die Messungen wörtlich, die Fahrt mit den Meldungen des Erkunders und des Werkzeugs, die Kriterien und Christophers Antworten wörtlich |
| Nicht-Ziele | Keine KI, keine Kamera, kein Rundblick, kein Nav2-Ziel; kein Build außer Schritt 3; keine eigene Code- oder Parameteränderung; keine Wiederholung einer Fahrt; kein Umstellen nach Hinweisen des Werkzeugs |
| Rückfall | Neu sind nur der Release-Ordner `kif7-<STAMP>` und `~/roboter_worktrees/kif7.env`; `kif5-20261123_0950` und `kif5.env` bleiben unverändert und sind der Rückweg. Ohne `stage_drive_only` und `nahsensoren` verhält sich der Stack wie bisher |
| Bereich und Freigabe | Laborraum und, für die Durchfahrt, der Flur unmittelbar hinter der Labortür (vom Projektinhaber am 21.11.2026 verlangt). Ohne Nahsensoren auf Entscheidung des Projektinhabers vom 22.11.2026. Christopher ist dabei, die Hand am Not-Aus, und räumt vor der Fahrt den Weg frei. 100 ms Anfahrzeit wie seit dem 15.11. |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push, kein
  Build außer dem einen in Schritt 3;
- **jeder Stackstart dieses Auftrags mit `stage_drive_only:=true
  nahsensoren:=false`**, keiner ohne;
- schreibend nur: die Stackstarts dieses Auftrags, **höchstens zwei**
  Missionsstarts (der zweite nur nach „Anfahrt abgeschlossen“), höchstens
  **ein** Missionsstopp und das Werkzeug `fahrziel_senden.py` genau so, wie
  es hier steht; kein `param set`, `lifecycle set`, `service call`, kein
  weiteres `topic pub`, keine Nav2-Ziele;
- **kein Missionsstart, wenn `stage_drive_only` nicht nachweislich `True`
  ist**, und keiner ohne Christophers „ja“ zur Labortür und zum freien Weg;
- **Christopher stellt Amadeus höchstens einmal um** (nur in A2, nur wenn
  das Werkzeug „keine Fahrt“ entscheidet), und nie nach den Zentimetern
  eines Hinweises;
- das Werkzeug nie mit `--aufstellung-egal`, `--breite-min`, `--breite-max`
  oder `--vor` aufrufen;
- `initial_scan_only` wird nie gesetzt und muss `False` melden;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`; `operator_stationary_confirmed:=true` nur nach
  Christophers „ja“;
- **jede Fahrt gibt es genau einmal** (die Anfahrt, die Durchfahrt). Bricht
  eine ab oder hält sie an, wird sie nicht wiederholt, und es folgt keine
  weitere Fahrt. Einzige Ausnahmen stehen unter „Motorregler antworten
  nicht“ und „Radsensor beim Start gesperrt“;
- keine Frage vorab, ob die Motoren frei sind, und keine Fragerunde zu
  unveränderten Laborbedingungen (LAB-1). Gefragt wird nur, was in diesem
  Auftrag wörtlich als Frage steht;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an bestehenden Umgebungsdateien und
  Releases; neu entstehen nur `~/roboter_worktrees/kif7.env` und der
  Release-Ordner `kif7-<STAMP>`;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- kein eigenes Anzeigeprogramm, nichts im Vollbild;
- Fragen an Christopher als Text, einzeln, ohne Auswahlfeld; Antworten
  wörtlich;
- keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht.

## Vorab festgelegte Kriterien

„Kette“ heißt: `Begin navigating` 0-mal, „Direkter Explore-Befehl verworfen“
0-mal, „Odometrie kurzzeitig nicht frisch“ 0-mal, „process has died“ 0-mal,
„Interner Explorer-Fehler“ 0-mal, „Logger severity“ 0-mal.

| Kennung | Kriterium |
|---|---|
| N-1 Ohne Nahsensoren | In jedem Stack: kein Knoten `vl53_near_field`; `require_near_field` des Fahrtors `False`; im Log die Zeile „TESTBETRIEB OHNE NAHSENSOREN“; während der Fahrt „Robot to slowdown“ und „Robot to approach“ je 0 |
| T-1 Vermessung | Eine türbreit vermessene Öffnung (0,65 bis 0,95 m; erwartet 0,72 bis 0,80 m), von Christopher als Labortür bestätigt; „Türachse aus der Wand neben der Tür“; Entscheidung „Durchfahrt“ oder „Anfahrt“; höchstens einmal umgestellt |
| A-1 Selbst ausgerichtet | Nur wenn die Anfahrt gewählt wurde: „Anfahrt abgeschlossen“, danach meldet `--tuer` „Aufstellung passt.“, „Weg passt.“ und „Kostenkarte passt.“, ohne dass jemand Amadeus angefasst hat |
| T-2 Abschluss | „Durchfahrt abgeschlossen.“ und „Etappenfahrt abgeschlossen: … Quelle mensch; kein Nav2-Ziel“; je Etappenfahrt höchstens 10 Etappen |
| T-3 Ausrichten | je Punkt höchstens drei Zeilen „ausgerichtet um …“; der jeweils letzte „Restfehler“ höchstens 3,5 Grad |
| T-4 Durch die Tür | Christopher: Amadeus steht ganz im Flur, auch die Hinterkante ist durch; nichts berührt, kein Eingriff |
| T-5 Abstand | Christopher: an Türpfosten und Türblatt blieb mindestens eine Handbreit |
| T-6 Kette | wie oben |
| H-1 Herkunft | Hält der Erkunder an, enthält die Ausgabe des Werkzeugs die Zeilen „Herkunft der Stelle …“ und „Nahsensoren im Fahrstreifen …“ |

Der Kollisionsmonitor hat in diesem Betrieb keine Quelle; „Robot to
slowdown“ oder „Robot to approach“ wären ein Befund (N-1). Hält der Erkunder
mit „Nahbereich vor dem Roboter nicht frei“ oder „Streifen vor dem Roboter
nicht frei“ an, ist das ein Befund: berichten, nicht wiederholen.

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls ~/.local/share/amadeus/releases/ | tail -5; ls -d ~/.local/share/amadeus/releases/kif5-20261123_0950 ~/roboter_worktrees/kif5.env
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.
Fehlt der Release `kif5-20261123_0950` oder `kif5.env`: berichten, Ende.

## Schritt 1 – Stand holen, neuer Release-Ordner

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
git diff --stat 88efba4 HEAD -- src/ | tail -4
mkdir -p ~/.local/share/amadeus/releases/kif7-$STAMP/pruefung
```

Erwartet: Seit dem Build von KI-F5 (`88efba4`) sind unter `src/` genau
zwei Dateien geändert: `src/explore/explore/explore_node.py` und
`src/explore/test/test_stage_drive.py`. Sonst: nichts bauen, berichten.

## Schritt 2 – eigene Umgebungsdatei

```bash
cp ~/roboter_worktrees/kif5.env ~/roboter_worktrees/kif7.env
```

In `~/roboter_worktrees/kif7.env` mit dem Datei-Werkzeug nur die Zeile
`export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/kif7-<STAMP>`
ändern. Prüfen:

```bash
source ~/roboter_worktrees/kif7.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
diff ~/roboter_worktrees/kif5.env ~/roboter_worktrees/kif7.env
mkdir -p "$SH_PR/kif7"
```

Erwartung: `rc=0`, Zähler `0`, `diff` zeigt genau die eine Zeile. **Jeder
ROS-Befehl dieses Auftrags beginnt mit `source ~/roboter_worktrees/kif7.env`.**

## Schritt 3 – Build (wie in KI-F5)

```bash
source ~/roboter_worktrees/kif7.env && cd "$SH_SRC" && \
export MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 && \
SECONDS=0 && colcon --log-base "$SH_REL/product-log" build --executor sequential \
  --base-paths src/amadeus_map_identity src/base_hardware src/robot_interfaces \
    src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore \
    src/robot_navigation src/robot_map_manager src/vl53_near_field \
    src/safety_monitor src/amadeus_lidar_bringup src/robot_bringup src/semantic_map_manager \
  --build-base "$SH_REL/product-build" --install-base "$SH_REL/product-install" \
  --cmake-args \
    -Dbehaviortree_cpp_DIR=/home/p/.local/share/amadeus/releases/ap06-20261010T070231Z/native-install/behaviortree_cpp/share/behaviortree_cpp/cmake \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  2>&1 | tee "$SH_PR/build.log" | tail -25; echo "rc=${PIPESTATUS[0]} dauer_s=$SECONDS"
```

Danach prüfen, dass genau die Korrektur im Erkunder steckt und sonst alles
dem Release von KI-F5 gleicht:

```bash
source ~/roboter_worktrees/kif7.env; I="$SH_REL/product-install"; ALT=~/.local/share/amadeus/releases/kif5-20261123_0950/product-install
ls "$I" | wc -l
for f in explore/share/explore/config/self_healing_params.yaml explore/share/explore/config/explore_params.yaml \
  robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml \
  robot_navigation/share/robot_navigation/config/nav2_params_real.yaml \
  robot_navigation/share/robot_navigation/launch/nav_mapping.launch.py \
  robot_bringup/share/robot_bringup/launch/app_mapping.launch.py \
  vl53_near_field/share/vl53_near_field/launch/vl53_near_field.launch.py \
  vl53_near_field/share/vl53_near_field/config/collision_monitor_ohne_nahsensoren.yaml \
  vl53_near_field/share/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml \
  vl53_near_field/share/vl53_near_field/config/collision_monitor_mapping_params.yaml \
  amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml; do \
  diff -q "$I/$f" "$ALT/$f" && echo "gleich: $f"; done
G="$(find "$I/robot_navigation" -name cmd_vel_mission_gate.py | head -1)"; GA="$(find "$ALT/robot_navigation" -name cmd_vel_mission_gate.py | head -1)"
diff -q "$G" "$GA" && echo "gleich: cmd_vel_mission_gate.py"
N="$(find "$I/explore" -name explore_node.py | head -1)"; NA="$(find "$ALT/explore" -name explore_node.py | head -1)"
echo "geänderte Zeilen explore_node.py: $(diff "$NA" "$N" | grep -c '^[<>]')"
echo "$(grep -c snapshot_before_clock "$N") snapshot_before_clock"
echo "$(grep -c 'self.get_logger().error(text)' "$N") getrennte Schlussmeldung"
```

Erwartet: `25`; elfmal `gleich: …` und `gleich: cmd_vel_mission_gate.py`;
`geänderte Zeilen explore_node.py: 33`; `6 snapshot_before_clock`; `1
getrennte Schlussmeldung`. Jede Abweichung, Build-Fehler oder fehlendes
Paket: nichts starten, berichten.

## Schritt 4 – gezielte Tests

```bash
source ~/roboter_worktrees/kif7.env && cd "$SH_SRC" && \
env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider \
  src/explore/test/test_stage_drive.py \
  src/explore/test/test_initial_scan_only.py \
  src/explore/test/test_self_healing.py \
  src/explore/test/test_self_healing_runtime.py \
  src/explore/test/test_self_healing_gap_depth.py \
  src/explore/test/test_metric_float32_lattice.py \
  src/explore/test/test_metric_selection_retry.py \
  src/explore/test/test_metric_map_lifecycle.py \
  src/robot_navigation/test/test_nav_real_contract.py \
  src/robot_navigation/test/test_monitor_kontur.py \
  src/robot_bringup/test/test_semantic_map_launch_contract.py \
  src/vl53_near_field/test/test_mapping_collision_contract.py \
  tools/kartierung/test_selbstheilung_stillstand_pruefen.py \
  tools/kartierung/test_selbstheilung_lauf_protokoll.py \
  tools/kartierung/test_selbstheilung_ablauf.py \
  tools/kartierung/test_selbstheilung_anlaeufe.py \
  tools/kartierung/test_karte_engstelle.py \
  2>&1 | tee "$SH_PR/tests.log" | tail -8
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3 )
```

Erwartung: `356 passed` (die 350 aus KI-F5 und 6 neue zur Korrektur) und
für die KI-Linie `268 passed`. Bei Fehlschlägen nichts starten, berichten.

---

## Teil A – Aufstellen und einmal messen (ohne Motorfreigabe, nichts fährt)

Der Stack startet **ohne** `active_drive` und ohne `enable_auto_explore`;
die Basis wird nicht bestromt (LAB-1 §3). In Teil A wird keine Mission
gesendet.

### A1 – Aufstellen und Stack ohne Motorfreigabe

Anweisung: „Bitte stelle Amadeus **irgendwo in den Laborraum, 1,5 bis 3 m
von der offenen Labortür entfernt**, so dass die Tür nicht genau hinter ihm
liegt. Genau ausrichten musst du ihn nicht, das macht er selbst. Um ihn
herum sollte eine Armlänge frei sein. Bitte steh während der Messungen
nicht direkt am Türrahmen; der Laser misst die Tür an ihren Kanten.“ Frage: „Steht Amadeus so still, und bleibt er
während des Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif7.env
D="$SH_PR/kif7"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  stage_drive_only:=true nahsensoren:=false \
  > "$D/launch_stand.log" 2>&1 < /dev/null &
echo $! > "$D/launch_stand.pid"; cat "$D/launch_stand.pid"; date -Iseconds
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter_stand.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter_stand.txt"
grep -c "Traceback" "$D/launch_stand.log"
```

Erwartet: `True`, `False`, `0`.

Dann, ob die Nahsensoren wirklich aus sind:

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"; L="$D/launch_stand.log"
{ echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  ros2 param get /collision_monitor vl53_left.enabled 2>&1
  ros2 param get /collision_monitor vl53_right.enabled 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"; } | tee "$D/ohne_nahsensoren_stand.txt"
```

Erwartet: `vl53_near_field-Knoten: 0`, dreimal `Boolean value is: False`,
`Testbetrieb im Log:` mindestens `2`. Meldet einer der beiden Befehle zum
`collision_monitor`, der Parameter sei nicht gesetzt, kennt diese Version
das Abschalten einzelner Quellen nicht; er bekommt dann ohnehin keine
VL53-Daten. Das berichten, kein Abbruch. **Läuft ein Knoten
`vl53_near_field` oder meldet das Fahrtor `True`: keine Mission, Stack
geordnet beenden, berichten.**

### A2 – einmal messen, Tür bestätigen lassen

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"; K=1
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen_$K.txt"
```

Das Werkzeug nennt unter „Türbreit vermessen“ jede passende Öffnung: wie
Amadeus zu ihr steht, woraus die Türachse stammt, die Fahrlinie, und als
letzte Zeile „Entscheidung: Durchfahrt …“, „Entscheidung: Anfahrt …“ oder
„Entscheidung: keine Fahrt …“. Bei mehreren steht darunter „Vorschlag:
Nr. …“.

**Hinweise wie „bitte etwa 30 cm nach links versetzen“ werden Christopher
nicht vorgelesen;** ob Amadeus passend steht, entscheidet das Werkzeug, und
er korrigiert es selbst.

Christopher einmal fragen (B, E und R aus der Tabelle, für die einzige
türbreite Öffnung oder die unter „Vorschlag“): „Ich messe eine Öffnung,
**B** m breit und **E** m entfernt, **R** Grad **links** (oder **rechts**)
von seiner Blickrichtung. Ist das die Labortür?“

- **„ja“ und Entscheidung „Durchfahrt“ oder „Anfahrt“:** weiter mit A3.
- **„ja“ und Entscheidung „keine Fahrt“:** Christopher den Grund aus der
  Ausgabe wörtlich nennen und sagen: „Bitte stelle ihn etwa einen Meter
  weiter in den Raum, die Tür vor ihm, mit einer Armlänge Platz um ihn
  herum. Genau ausrichten musst du ihn nicht.“ Mit `K=2` noch einmal
  messen. Lautet die Entscheidung wieder „keine Fahrt“: A3, berichten, Ende.
- **„nein“:** Christopher fragen: „Wo liegt die Labortür von Amadeus aus
  gesehen: vorn, links, rechts oder hinten?“ und mit `K=2` noch einmal
  messen; die Öffnung in dieser Richtung ist dann die gemeinte. Findet das
  Werkzeug dort keine türbreite Öffnung: A3, berichten, Ende.

### A3 – Stack beenden

```bash
source ~/roboter_worktrees/kif7.env; kill -INT "$(cat "$SH_PR/kif7/launch_stand.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Amadeus bleibt danach genau so stehen.

---

## Teil B – selbst ausrichten und durch die Tür

### B1 – Ansage und scharfer Start

Zuerst Christopher sagen: „**Amadeus fährt gleich ohne Nahsensoren.** Er
sieht dann nichts, was niedriger als etwa 75 cm ist, zum Beispiel Kisten,
Taschen, Kabel, Schuhe oder einen Türstopper, und der Kollisionsmonitor
bremst nicht. Pfosten, Türblatt und Wände sieht er weiter mit dem Laser.
Bitte sieh nach, dass um Amadeus herum, zwischen ihm und der Tür, in der
Tür und im Flur bis gut einen Meter hinter der Tür nichts am Boden liegt
oder steht.“ Frage:
„Ist der Weg frei von niedrigen Dingen?“ Nur nach „ja“ weiter. Bei „nein“:
Christopher räumt es weg, dann noch einmal fragen.

Dann Christopher sagen: „Gleich richtet sich Amadeus **selbst** aus. Steht
er schon passend, fährt er in kurzen Etappen geradeaus durch die Türmitte.
Sonst stellt er sich zuerst vor die Tür: auf der Stelle drehen, ein oder
zwei kurze gerade Stücke, wieder drehen, kurz stehen. Dann fährt er gerade
hindurch und bleibt knapp einen halben Meter dahinter im Flur stehen. Das
dauert zwei bis vier Minuten. Du stehst seitlich im Laborraum auf der Seite
ohne Türblatt, nicht zwischen Amadeus und der Tür, nicht in der Tür, nicht
im Flur vor ihm und nicht direkt am Türrahmen, mit der Hand am Not-Aus.“ Frage: „Steht Amadeus unverändert, und bleibt er während des
Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif7.env
D="$SH_PR/kif7"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  stage_drive_only:=true nahsensoren:=false \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
grep -n "Anfahrverhalten bestaetigt" "$D/launch.log" | tee "$D/anfahrzeit.txt"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung.txt"
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`;
`True` (Etappenfahrt) und `False` (Rundblick); Prüfskript Exit 0 wie in
KI-F2. Die Prüfung der Eigenechos (`--eigenecho-s`) entfällt in diesem
Auftrag; sie gilt den Nahsensoren. **Trifft etwas davon nicht zu (nach einer
Wiederholung bei „erreichbar“, „nicht deklariert“, „Graph unvollständig“):
keine Mission, Stack geordnet beenden, berichten.**

Dann, ob die Nahsensoren wirklich aus sind:

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"; L="$D/launch.log"
{ echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  ros2 param get /collision_monitor vl53_left.enabled 2>&1
  ros2 param get /collision_monitor vl53_right.enabled 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"; } | tee "$D/ohne_nahsensoren.txt"
```

Erwartet: `vl53_near_field-Knoten: 0`, dreimal `Boolean value is: False`,
`Testbetrieb im Log:` mindestens `2`. Meldet einer der beiden Befehle zum
`collision_monitor`, der Parameter sei nicht gesetzt, kennt diese Version
das Abschalten einzelner Quellen nicht; er bekommt dann ohnehin keine
VL53-Daten. Das berichten, kein Abbruch. **Läuft ein Knoten
`vl53_near_field` oder meldet das Fahrtor `True`: keine Mission, Stack
geordnet beenden, berichten.**


**Motorregler antworten nicht (Ausnahme):** Fehlt die Zeile zur Anfahrzeit
und steht im Log „Modbus-Fehler Motor … No response received“, den Stack
geordnet beenden und Christopher den Befund in einem Satz melden: „Die
Motorregler antworten nicht; so kann ich nicht starten.“ Sagt er daraufhin,
die Motoren seien frei, ist **genau ein** weiterer scharfer Start erlaubt.

**Radsensor beim Start gesperrt (Ausnahme):** Die Zeile zur Anfahrzeit ist
da, „Modbus-Fehler“ steht 0-mal im `launch.log`, und die Vorprüfung fällt
**nur** im Bereich „D Quellen“ durch: „Encoder liefern frisch“ und
„Encoder-Zeitwache bereit“ mit `state='fault_latched'`, dazu
gegebenenfalls „HWT-Fusion Quellen bereit“. Dann hat sich der Radsensor
beim Hochfahren selbst gesperrt. Er gibt sich erst bei einem neuen Start
frei; die Selbstheilung löst das nicht (SH-4, 04.11.: 690 s Mission, nie
gefahren). Amadeus hat sich nicht bewegt.

1. Nur lesend sichern, was die Zeitwache meldet, und die Last:

   ```bash
   source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
   uptime | tee "$D/last_bei_sperre_1.txt"
   python3 "$SH_SRC/ki_erkundung/werkzeuge/radsensor_zustand.py" 2>&1 | tee "$D/radsensor_1.txt"
   ```

2. Stack geordnet beenden (wie B5) und Christopher in einem Satz sagen: „Der
   Radsensor hat sich beim Hochfahren selbst gesperrt; ich starte den Stack
   einmal neu, Amadeus fährt dabei nicht.“
3. Die Dateien des ersten Starts beiseitelegen, damit B1 bis B5 mit
   denselben Befehlen weiterlaufen:

   ```bash
   source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
   for f in launch.log launch.pid launch_start.txt anfahrzeit.txt schalter.txt vorpruefung.json vorpruefung.txt; do \
     [ -e "$D/$f" ] && mv "$D/$f" "$D/erster_start_$f"; done; ls "$D"
   ```

4. Mindestens 30 s nach „alles beendet“: **genau ein** weiterer scharfer
   Start, B1 von der Frage an, mit den Befehlen, wie sie dort stehen.
5. Sperrt sich der Radsensor auch beim zweiten Start: Schritt 1 mit
   `_2` statt `_1` in den Dateinamen, Stack beenden, berichten, Ende. Das
   ist dann ein Befund für die Motorsteuerung, nichts für diesen Auftrag.

Stimmt eine der Bedingungen nicht (zum Beispiel „Modbus-Fehler“ im Log oder
eine FEHL-Zeile außerhalb von „D Quellen“), gilt die Ausnahme nicht.

### B2 – noch einmal messen (nichts fährt)

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen_scharf.txt"
```

Die Labortür muss wieder dastehen (Breite und Richtung wie in A2, je auf
0,05 m und 10° genau), mit „Entscheidung: Durchfahrt …“ oder
„Entscheidung: Anfahrt …“. Ihre Richtung aus der Tabelle (Zahl mit
Vorzeichen, ohne Gradzeichen) ist `R`. Sonst: keine Mission; weiter wie
unter „Nichts gesendet“.

### B3 – erste Mission: Amadeus entscheidet selbst

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --richtung R --richtung-toleranz 10 --hinter 0.45 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/werkzeug.txt"; echo "rc=${PIPESTATUS[0]}"
```

(`--hinter 0.45`, weil im Flur laut Christopher 1,20 m bis zum ersten
Hindernis frei sind.)

- **Letzte Zeilen enthalten „Durchfahrt abgeschlossen.“:** fertig, weiter
  mit B4.
- **Letzte Zeilen enthalten „Anfahrt abgeschlossen.“:** Amadeus steht jetzt
  vor der Tür. Niemand fasst ihn an. Weiter mit B3b.
- **Der Erkunder hält an oder die Etappenfahrt scheitert:** nicht
  wiederholen; weiter mit B4.

### B3b – zweite Mission: die Durchfahrt (nur nach „Anfahrt abgeschlossen.“)

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart2.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --richtung 0 --richtung-toleranz 15 --hinter 0.45 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/werkzeug2.txt"; echo "rc=${PIPESTATUS[0]}"
```

Meldet das Werkzeug hier „Nichts gesendet: Die Aufstellung passt nicht.“
oder „… Neben der Fahrlinie ist nicht genug frei.“, steht Amadeus nach der
Anfahrt nicht passend: ein Befund zu A-1; einmal den Stopp senden (unten),
weiter mit B4. Nicht umstellen, nicht wiederholen.

**Nichts gesendet (Ausnahme):** Meldet das Werkzeug „Nichts gesendet“ oder
„Der Erkunder wartet nicht“, hat sich Amadeus nicht bewegt. Dann genau
einmal den Stopp senden, den Stack geordnet beenden (B5) und berichten, was
das Werkzeug gesagt hat. Kein weiterer Durchgang.

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
```

**Christopher drückt den Not-Aus (oder den Stopp in der App), bevor etwas
berührt wird, und sofort, wenn doch etwas Niedriges in den Weg gerät oder
jemand den Weg kreuzt; ohne Nahsensoren hält Amadeus davor nicht von selbst
an:** wenn eine Ecke näher als zwei Finger breit an Pfosten,
Türblatt oder sonst etwas herankommt, wenn Amadeus anders fährt als
angekündigt (rückwärts, im Bogen, deutlich zur Seite, deutlich schneller als
eine Handbreit in der Sekunde), bei ungewöhnlichem Geräusch oder starkem
Schwanken. Drehen auf der Stelle, kurzes Stehenbleiben zwischen den
Etappen, kleines Nachstellen der Richtung und langsames Kriechen neben dem
Türblatt sind gewollt.

### B4 – sichern (Amadeus bleibt stehen, der Stack läuft noch)

```bash
source ~/roboter_worktrees/kif7.env; D="$SH_PR/kif7"
date -Iseconds > "$D/ende.txt"
grep -n "Etappenfahrt\|Fahrziel\|Mission beendet" "$D/launch.log" | tee "$D/etappen.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died" \
  "Interner Explorer-Fehler" "Logger severity"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
```

Dazu aus den Sekundenzeilen von `base_hardware` im `launch.log`, wie im
Bericht zu KI-F2: größtes |v| und größtes |w| zwischen Missionsstart und
Ende. Dann Christopher fragen, je einzeln:

1. Steht Amadeus ganz im Flur, auch mit der Hinterkante?
   (Nur wenn er sich zuerst vor die Tür gestellt hat, vorher: „Hat er sich
   selbst vor die Tür gestellt, und stand er danach mittig davor?“)
2. Wie viel Platz blieb an den Türpfosten und am Türblatt (etwa in cm, je
   Seite)?
3. Hat er etwas berührt, oder musstest du eingreifen?
4. Ist er gerade auf die Tür zugefahren, und hat er die Richtung
   nachgestellt? Wo?
5. Nur wenn der Erkunder angehalten hat und `werkzeug.txt` (oder
   `werkzeug2.txt`) eine Zeile
   „Herkunft der Stelle …“ enthält: „Das Werkzeug meldet etwa **A** cm vor dem Gehäuse und **B** cm **links** (oder **rechts**) der Mitte etwas. Steht oder liegt dort etwas, und was?“ (A steht in der Zeile „Herkunft der Stelle …“, B ist der Wert „… m links/rechts der Mitte“ mal 100.)

### B5 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif7.env; kill -INT "$(cat "$SH_PR/kif7/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Danach stellt Christopher Amadeus von Hand zurück.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei Berührung, bei einer anderen Bewegung als
  angekündigt, bei ungewöhnlichem Geräusch, starkem Schwanken oder Rauch.
  Danach nichts mehr starten; nur berichten.
- Endet die Etappenfahrt mit einer Fehlermeldung („Etappenfahrt: …
  fehlgeschlagen“, „… angehalten“, „… nicht frei“, „kein gueltiges
  Fahrziel“): nicht wiederholen, B4 und B5, berichten.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um die Fahrt „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif7.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen:

1. Stand (HEAD), die Zeile `zeilen=…`, Tests.
2. Je Stack die Prüfung „ohne Nahsensoren“ (`ohne_nahsensoren*.txt`).
3. Teil A: `schalter_stand.txt`; der ganze Inhalt jeder Datei
   `messen_K.txt`; die Fragen an Christopher und seine Antworten wörtlich;
   ob und wie er Amadeus umgestellt hat.
4. Teil B: Christophers Antworten auf die Frage nach dem freien Weg und zum
   Start; Anfahrzeit, Schalter, Vorprüfung; bei der Ausnahme „Radsensor
   beim Start gesperrt“ der ganze Inhalt von `radsensor_K.txt` und
   `last_bei_sperre_K.txt` und was der zweite Start ergab;
   `messen_scharf.txt`; **der ganze Inhalt von `werkzeug.txt` und, falls
   vorhanden, `werkzeug2.txt`**; `etappen.txt` und `zaehler.txt`; größtes
   |v| und |w| an der Basis; Christophers Antworten nach der Fahrt wörtlich.
5. Die Tabelle N-1, T-1, A-1, T-2 bis T-6 und H-1 mit dem Gemessenen und
   „trifft zu“ oder „trifft nicht zu“.
6. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
