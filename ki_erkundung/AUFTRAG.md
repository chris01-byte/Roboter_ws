# Aktueller Auftrag der KI-Linie: KI-F8 – dreimal selbst durch die Tür, in einem Ablauf

**Erteilt am 23.11.2026.** Er wird aktiv, sobald der Projektinhaber ihn
übergibt. Er läuft auf dem **Jetson**, mit Christopher. Der KI-Rechner wird
nicht gebraucht; Kamera und KI laufen in diesem Auftrag nicht.

**Warum es ihn gibt:** In KI-F7 ist Amadeus zum ersten Mal in dieser Linie
selbst vor die Labortür gefahren, hat sich ausgerichtet und ist hindurch in
den Flur gefahren. Danach hat der Projektinhaber entschieden (23.11.2026):

- **Grenzen des Werkzeugs gesenkt:** neben der Fahrlinie 0,26 m statt
  0,30 m (Gehäuse 0,23 m je Seite; der Erkunder prüft selbst 0,25 m), zum
  Drehen 0,37 m statt 0,45 m (Gehäuseecken 0,355 m).
- **Ein Ablauf statt zwei Aufträge:** Ein einziger Aufruf des Werkzeugs
  macht Anfahrt, Neumessung und Durchfahrt in **einer** Mission. Die
  Türrichtung aus der ersten Messung wird mitgenommen, wenn der Laser nach
  der Anfahrt die Wand neben der Tür nicht mehr lang genug sieht.
- **Dreimal**, von drei verschiedenen Plätzen, um Sicherheit zu gewinnen.
- **Kaum Fragen:** Vorab fragt der Agent Christopher **genau einmal**, ob
  alles aufgebaut ist. Danach läuft alles ohne weitere Vorabfragen; nach
  jedem Lauf gibt es genau eine kurze Nachricht. Der Laborbetrieb (LAB-1)
  ist darauf abgestimmt.

**Ohne Nahsensoren**, wie vom Projektinhaber am 22.11.2026 entschieden
(`nahsensoren:=false`): Amadeus sieht nichts unter etwa 75 cm Höhe, und der
Kollisionsmonitor bremst nicht. Christopher räumt den Weg frei und hat die
Hand am Not-Aus.

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
[KI-F6](archiv/20261123-kif6-anfahrt-gelungen/),
[KI-F7](archiv/20261123-kif7-erste-durchfahrt/).

**Frage dieses Auftrags:** Kommt Amadeus von drei verschiedenen Plätzen im
Laborraum jedes Mal in einem Ablauf selbst durch die Tür?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md`, Abschnitt 6a |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. **Neuer Build** in einen neuen Release-Ordner `kif8-<STAMP>` mit eigener Umgebungsdatei `~/roboter_worktrees/kif8.env` (Kopie von `kif7.env`). Gegenüber dem Release `kif7-20261123_1258` sind nur `explore_node.py` und `stage_drive.py` des Erkunders geändert |
| Was neu ist | Erkunder (nur mit `stage_drive_only:=true`): Ein Fahrziel kann den Vermerk „es folgt ein Folgeziel“ tragen; dann wartet er danach stehend bis zu 120 s auf das nächste, höchstens drei je Mission. Eine Nachricht „Ende“ schließt die Mission sofort. Ohne Vermerk ist alles wie bisher. Werkzeug: `--zur-tuer` in einem Aufruf; neue Grenzen 0,26 m und 0,37 m |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif8.md`: Build, Tests, je Lauf die Ausgabe des Werkzeugs, die Meldungen des Erkunders, die Kriterien und Christophers Antworten wörtlich |
| Nicht-Ziele | Keine KI, keine Kamera, kein Rundblick, kein Nav2-Ziel; kein Build außer Schritt 3; keine eigene Code- oder Parameteränderung; kein Umstellen nach Hinweisen des Werkzeugs |
| Rückfall | Neu sind nur der Release-Ordner `kif8-<STAMP>` und `~/roboter_worktrees/kif8.env`; `kif7-20261123_1258` und `kif7.env` bleiben unverändert und sind der Rückweg |
| Bereich und Freigabe | Laborraum und, für die Durchfahrt, der Flur unmittelbar hinter der Labortür (vom Projektinhaber am 21.11.2026 verlangt). Ohne Nahsensoren auf Entscheidung des Projektinhabers vom 22.11.2026. Höchstens eine Vorabfrage auf Wunsch des Projektinhabers vom 23.11.2026 (LAB-1). Christopher ist dabei, die Hand am Not-Aus. 100 ms Anfahrzeit wie seit dem 15.11. |

## Fragen an Christopher – nur diese

Gefragt wird als Text, einzeln, ohne Auswahlfeld; Antworten wörtlich in den
Bericht.

1. **Vorab, genau einmal (F0)**, nach Schritt 4, wörtlich:

   > „Gleich fährt Amadeus dreimal selbst durch die Labortür, jedes Mal in
   > einem Ablauf: erst stellt er sich vor die Tür, dann fährt er hindurch
   > und bleibt knapp einen halben Meter dahinter im Flur stehen. Er fährt
   > **ohne Nahsensoren**: Was niedriger als etwa 75 cm ist (Kisten,
   > Taschen, Kabel, Schuhe, Türstopper), sieht er nicht, und der
   > Kollisionsmonitor bremst nicht. Ist alles aufgebaut: die Labortür ganz
   > offen, im Laborraum, in der Tür und im Flur bis gut einen Meter dahinter
   > nichts Niedriges am Boden, nichts auf Amadeus, der Arm in
   > Transportstellung, Amadeus 1,5 bis 3 m vor der Tür auf der Seite ohne
   > Türblatt, und du stehst seitlich, nicht zwischen ihm und der Tür, mit der
   > Hand am Not-Aus? Wenn du ‚ja' schreibst, starte ich ohne weitere Fragen;
   > du fasst ihn dann nur zwischen den Läufen an, wenn ich dich darum bitte.“

   Nur nach „ja“ weiter. Das „ja“ gilt auch als Bestätigung, dass Amadeus
   beim ersten Start stillsteht (`operator_stationary_confirmed:=true`).
2. **Nach jedem Lauf genau eine Nachricht (F-Lauf)**, siehe „Lauf k“,
   Schritt 7. Christophers „weiter“ darin gilt als Bestätigung, dass Amadeus
   für den nächsten Start stillsteht.
3. **Nur in den Ausnahmen**, die unten ausdrücklich stehen (mehrere
   türbreite Öffnungen, „keine Fahrt“, Motorregler antworten nicht).

Keine weitere Frage, keine Frage nach freien Motoren, keine Bestätigung
unveränderter Laborbedingungen.

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push, kein
  Build außer dem einen in Schritt 3;
- **jeder Stackstart dieses Auftrags mit `stage_drive_only:=true
  nahsensoren:=false`**, keiner ohne;
- schreibend nur: die Stackstarts dieses Auftrags, **je Lauf genau ein**
  Missionsstart und das Werkzeug `fahrziel_senden.py` genau so, wie es hier
  steht (es sendet die Fahrziele und, wenn nichts passt, das „Ende“); kein
  `param set`, `lifecycle set`, `service call`, kein weiteres `topic pub`,
  keine Nav2-Ziele, kein Missionsstopp von Hand außer unter „Abbruch“;
- **kein Missionsstart, wenn `stage_drive_only` nicht nachweislich `True`
  ist**;
- Christopher stellt Amadeus je Lauf **höchstens einmal** um, und nur, wenn
  das Werkzeug „keine Fahrt“ entscheidet; nie nach den Zentimetern eines
  Hinweises;
- das Werkzeug nie mit `--aufstellung-egal`, `--breite-min`, `--breite-max`
  oder `--vor` aufrufen;
- `initial_scan_only` wird nie gesetzt und muss `False` melden;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an bestehenden Umgebungsdateien und
  Releases; neu entstehen nur `~/roboter_worktrees/kif8.env` und der
  Release-Ordner `kif8-<STAMP>`;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- kein eigenes Anzeigeprogramm, nichts im Vollbild;
- keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht.

## Vorab festgelegte Kriterien

„Kette“ heißt: `Begin navigating` 0-mal, „Direkter Explore-Befehl verworfen“
0-mal, „Odometrie kurzzeitig nicht frisch“ 0-mal, „process has died“ 0-mal,
„Interner Explorer-Fehler“ 0-mal, „Logger severity“ 0-mal.

Je Lauf:

| Kennung | Kriterium |
|---|---|
| N-1 Ohne Nahsensoren | kein Knoten `vl53_near_field`; `require_near_field` `False`; „TESTBETRIEB OHNE NAHSENSOREN“ im Log; „Robot to slowdown“ und „Robot to approach“ je 0 |
| T-1 Vermessung | eine türbreit vermessene Öffnung (0,65 bis 0,95 m); „Türachse aus der Wand neben der Tür“ in der ersten Messung; Entscheidung „Durchfahrt“ oder „Anfahrt“; höchstens einmal umgestellt |
| L-1 Ein Ablauf | genau ein Missionsstart und genau ein Aufruf des Werkzeugs; bei Anfahrt: „Anfahrt abgeschlossen. Jetzt misst er neu …“, „Wiedergefunden: …“, danach „Aufstellung passt.“ und „Weg passt.“ ohne Anfassen |
| T-2 Abschluss | „Durchfahrt abgeschlossen.“ und „Etappenfahrt abgeschlossen: … Quelle mensch; kein Nav2-Ziel“; Werkzeug `rc=0` |
| T-3 Ausrichten | je Punkt höchstens drei Zeilen „ausgerichtet um …“; der jeweils letzte „Restfehler“ höchstens 3,5 Grad |
| T-4 Durch die Tür | Christopher: steht ganz im Flur, nichts berührt, kein Eingriff |
| T-6 Kette | wie oben |

Gesamt: **G-1: drei von drei Läufen erfüllen alle Kriterien.**

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls ~/.local/share/amadeus/releases/ | tail -5; ls -d ~/.local/share/amadeus/releases/kif7-20261123_1258 ~/roboter_worktrees/kif7.env
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.
Fehlt der Release `kif7-20261123_1258` oder `kif7.env`: berichten, Ende.

## Schritt 1 – Stand holen, neuer Release-Ordner

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
git diff --stat 4ec1bcf HEAD -- src/ | tail -5
mkdir -p ~/.local/share/amadeus/releases/kif8-$STAMP/pruefung
```

Erwartet: Seit dem Build von KI-F7 (`4ec1bcf`) sind unter `src/` genau drei
Dateien geändert: `src/explore/explore/explore_node.py`,
`src/explore/explore/stage_drive.py` und
`src/explore/test/test_stage_drive.py`. Sonst: nichts bauen, berichten.

## Schritt 2 – eigene Umgebungsdatei

```bash
cp ~/roboter_worktrees/kif7.env ~/roboter_worktrees/kif8.env
```

In `~/roboter_worktrees/kif8.env` mit dem Datei-Werkzeug nur die Zeile
`export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/kif8-<STAMP>`
ändern. Prüfen:

```bash
source ~/roboter_worktrees/kif8.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
diff ~/roboter_worktrees/kif7.env ~/roboter_worktrees/kif8.env
mkdir -p "$SH_PR/kif8"
```

Erwartung: `rc=0`, Zähler `0`, `diff` zeigt genau die eine Zeile. **Jeder
ROS-Befehl dieses Auftrags beginnt mit `source ~/roboter_worktrees/kif8.env`.**

## Schritt 3 – Build (wie in KI-F7)

```bash
source ~/roboter_worktrees/kif8.env && cd "$SH_SRC" && \
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

Danach prüfen, dass genau die Änderung im Erkunder steckt und sonst alles
dem Release von KI-F7 gleicht:

```bash
source ~/roboter_worktrees/kif8.env; I="$SH_REL/product-install"; ALT=~/.local/share/amadeus/releases/kif7-20261123_1258/product-install
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
N="$(find "$I/explore" -name explore_node.py | head -1)"; SD="$(find "$I/explore" -name stage_drive.py | head -1)"
echo "$(grep -c snapshot_before_clock "$N") snapshot_before_clock"
echo "$(grep -c parse_stage_message "$N") parse_stage_message"
echo "$(grep -c stage_drive_followup_wait_s "$N") stage_drive_followup_wait_s"
echo "$(grep -c 'class StageEnd' "$SD") StageEnd"
```

Erwartet: `25`; elfmal `gleich: …` und `gleich: cmd_vel_mission_gate.py`;
`6 snapshot_before_clock`; `2 parse_stage_message`; `1
stage_drive_followup_wait_s`; `1 StageEnd`. Jede Abweichung, Build-Fehler
oder fehlendes Paket: nichts starten, berichten.

## Schritt 4 – gezielte Tests

```bash
source ~/roboter_worktrees/kif8.env && cd "$SH_SRC" && \
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

Erwartung: `370 passed` (die 356 aus KI-F7 und 14 neue zum Folgeziel) und
für die KI-Linie `285 passed` (271 und 14 neue zur Seite des Türblatts; der
Stand vor dieser Ergänzung hatte 271). Bei Fehlschlägen nichts starten,
berichten.

## Schritt 5 – die eine Frage (F0)

Christopher F0 stellen (Wortlaut oben). Nur nach „ja“ weiter.

## Schritt 6 – Vorlauf ohne Motorfreigabe (einmal, ohne Frage)

Prüft im Stand, ohne Motorsteuerung, ob der neue Stand richtig hochkommt
(LAB-1 §3). Amadeus bewegt sich nicht.

```bash
source ~/roboter_worktrees/kif8.env
D="$SH_PR/kif8/vorlauf"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  stage_drive_only:=true nahsensoren:=false \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif8/vorlauf"; L="$D/launch.log"
{ ros2 param get /explore_node stage_drive_only 2>&1
  ros2 param get /explore_node initial_scan_only 2>&1
  ros2 param get /explore_node stage_drive_followup_wait_s 2>&1
  ros2 param get /explore_node stage_drive_max_targets 2>&1
  echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"
  echo "Traceback: $(grep -c Traceback "$L")"; } | tee "$D/pruefung.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen.txt"
kill -INT "$(cat "$D/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Erwartet: `True`, `False`, `120.0`, `3`, `vl53_near_field-Knoten: 0`,
`False`, `Testbetrieb im Log:` mindestens `2`, `Traceback: 0`; in
`messen.txt` die Labortür unter „Türbreit vermessen“ mit „Entscheidung:
Durchfahrt“ oder „Entscheidung: Anfahrt“. Weicht etwas ab: nichts weiter
starten, berichten. Meldet das Werkzeug hier „keine Fahrt“: weiter mit
Lauf 1; die Ausnahme in dessen Schritt 3 regelt es.

---

## Lauf k (k = 1, 2, 3)

Für jeden Lauf dieselben Schritte; Dateien unter `$SH_PR/kif8/lauf$k`.
Vor Lauf 2 und 3 hat Christopher „weiter“ geschrieben (Schritt 7 des
vorigen Laufs).

### 1 – scharfer Start

```bash
source ~/roboter_worktrees/kif8.env; k=1        # 2, 3 in den folgenden Läufen
D="$SH_PR/kif8/lauf$k"; mkdir -p "$D"
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

### 2 – Prüfungen (nach etwa 70 s, ohne Frage)

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif8/lauf$k"; L="$D/launch.log"
grep -n "Anfahrverhalten bestaetigt" "$L" | tee "$D/anfahrzeit.txt"
{ ros2 param get /explore_node stage_drive_only 2>&1
  ros2 param get /explore_node initial_scan_only 2>&1
  echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"; } | tee "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung.txt"
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`;
`True`, `False`, `vl53_near_field-Knoten: 0`, `False`, `Testbetrieb im
Log:` mindestens `2`; Prüfskript Exit 0 (die Prüfung der Eigenechos
entfällt, sie gilt den Nahsensoren). **Trifft etwas nicht zu (nach einer
Wiederholung bei „erreichbar“, „nicht deklariert“, „Graph unvollständig“):
keine Mission, Stack geordnet beenden (Schritt 6), berichten, Ende.**

**Radsensor beim Start gesperrt (Ausnahme, ohne Frage):** Die Zeile zur
Anfahrzeit ist da, „Modbus-Fehler“ steht 0-mal im Log, und die Vorprüfung
fällt **nur** im Bereich „D Quellen“ durch („Encoder liefern frisch“,
„Encoder-Zeitwache bereit“ mit `state='fault_latched'`, gegebenenfalls
„HWT-Fusion Quellen bereit“). Dann:

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif8/lauf$k"
uptime | tee "$D/last_bei_sperre.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/radsensor_zustand.py" 2>&1 | tee "$D/radsensor.txt"
kill -INT "$(cat "$D/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
for f in launch.log launch.pid launch_start.txt anfahrzeit.txt schalter.txt vorpruefung.json vorpruefung.txt; do \
  [ -e "$D/$f" ] && mv "$D/$f" "$D/erster_start_$f"; done
```

Christopher dazu nur sagen (keine Frage): „Der Radsensor hat sich beim
Hochfahren gesperrt; ich starte einmal neu, Amadeus fährt dabei nicht.“
Mindestens 30 s nach „alles beendet“ **genau ein** weiterer Start (Schritt
1, dann 2). Sperrt er sich wieder: Stack beenden, berichten, Ende.

**Motorregler antworten nicht (Ausnahme):** Fehlt die Zeile zur Anfahrzeit
und steht im Log „Modbus-Fehler Motor … No response received“: Stack
beenden und Christopher sagen: „Die Motorregler antworten nicht; so kann ich
nicht starten.“ Sagt er, die Motoren seien frei, ist **genau ein** weiterer
Start erlaubt.

### 3 – messen (nichts fährt)

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif8/lauf$k"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen.txt"
```

- **Genau eine türbreite Öffnung mit „Entscheidung: Durchfahrt …“ oder
  „Entscheidung: Anfahrt …“:** ihre Richtung aus der Tabelle (Zahl mit
  Vorzeichen) ist `R`. Weiter mit 4, **ohne Frage**.
- **Keine passende türbreite Öffnung, aber „Tür hinter dem Türblatt
  geschätzt: Nr. …, Richtung … (für --richtung)“** mit „Entscheidung:
  Anfahrt …“ darunter: Amadeus steht auf der Seite, zu der das Blatt
  aufgeht. `R` ist diese Richtung. Weiter mit 4, **ohne Frage**; das
  Werkzeug fährt zuerst frontal vor die Tür, misst neu und fährt erst dann
  hindurch.
- **Mehrere türbreite Öffnungen (Ausnahme):** Christopher einmal fragen:
  „Ich messe mehrere türbreite Öffnungen: … (je Breite, Entfernung,
  Richtung). Welche ist die Labortür?“ Seine Antwort bestimmt `R`.
- **„Entscheidung: keine Fahrt“ oder keine türbreite Öffnung (Ausnahme):**
  Christopher den Grund aus der Ausgabe wörtlich nennen und bitten: „Bitte
  stelle ihn etwa einen Meter weiter in den Raum, die Tür vor ihm, mit einer
  Armlänge Platz um ihn herum, und schreib ‚fertig'.“ Nach „fertig“ den
  Stack beenden (Schritt 6), dann Schritt 1 bis 3 dieses Laufs noch einmal
  (`lauf${k}b`). Ist es wieder „keine Fahrt“: Lauf beenden, berichten, keine
  weiteren Läufe.

Hinweise wie „bitte etwa 30 cm nach links versetzen“ werden Christopher
nicht vorgelesen; das Werkzeug richtet ihn selbst aus.

### 4 – ein Ablauf: Mission starten, das Werkzeug macht den Rest

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif8/lauf$k"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --richtung R --richtung-toleranz 10 --hinter 0.45 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/werkzeug.txt"; echo "rc=${PIPESTATUS[0]}"
```

(`--hinter 0.45`, weil im Flur laut Christopher 1,20 m bis zum ersten
Hindernis frei sind.) Das Werkzeug sendet bei „Anfahrt“ zuerst die Anfahrt,
misst danach im Stand neu und sendet in derselben Mission die Durchfahrt.
Passt etwas nicht, sendet es dem Erkunder „Ende“; die Mission schließt dann
von selbst. **Kein zweiter Missionsstart, kein Stopp von Hand.**

**Christopher drückt den Not-Aus (oder den Stopp in der App), bevor etwas
berührt wird,** und sofort, wenn doch etwas Niedriges in den Weg gerät oder
jemand den Weg kreuzt; ohne Nahsensoren hält Amadeus davor nicht von selbst
an. Drehen auf der Stelle, kurzes Stehenbleiben zwischen den Etappen und
vor der Durchfahrt (Neumessung), kleines Nachstellen der Richtung und
langsames Kriechen neben dem Türblatt sind gewollt.

### 5 – sichern (Amadeus bleibt stehen, der Stack läuft noch)

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif8/lauf$k"
date -Iseconds > "$D/ende.txt"
grep -n "Etappenfahrt\|Fahrziel\|Mission beendet" "$D/launch.log" | tee "$D/etappen.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died" \
  "Interner Explorer-Fehler" "Logger severity"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
```

Dazu aus den Sekundenzeilen von `base_hardware` zwischen Missionsstart und
Ende: größtes |v| und |w|.

### 6 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif8.env; kill -INT "$(cat "$SH_PR/kif8/lauf$k/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

### 7 – eine Nachricht an Christopher (F-Lauf)

Ein Satz zum Ergebnis aus `werkzeug.txt` (zum Beispiel „Lauf 1: Anfahrt
1,6 m, dann Durchfahrt 1,9 m, ‚Durchfahrt abgeschlossen'.“), dann:

- nach Lauf 1 und 2: „Steht er ganz im Flur, und hat er nichts berührt?
  Dann stell ihn bitte für den nächsten Lauf an einen **anderen** Platz im
  Laborraum, 1,5 bis 3 m vor der Tür, Tür ganz offen, nichts auf ihm, und
  schreib ‚weiter', wenn er still steht.“
- nach Lauf 3: „Steht er ganz im Flur, und hat er nichts berührt?“

**Danach:**
- Antwort mit „weiter“ und ohne Berührung oder Eingriff: nächster Lauf.
- **Berührung oder Eingriff:** keine weiteren Läufe, berichten.
- **Lauf ohne Durchfahrt** (Werkzeug `rc` ≠ 0 oder kein „Durchfahrt
  abgeschlossen.“): Nennt Christopher einen Grund bei sich (etwas lag auf
  dem Roboter, die Tür war nicht ganz offen, jemand im Weg) oder bittet er
  ausdrücklich darum, wird **dieser Lauf genau einmal** wiederholt
  (`lauf${k}w`). Sonst: keine weiteren Läufe, berichten.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei Berührung, bei einer anderen Bewegung als
  angekündigt, bei ungewöhnlichem Geräusch, starkem Schwanken oder Rauch.
  Danach nichts mehr starten; nur berichten.
- Hängt das Werkzeug (keine neue Zeile über 5 Minuten, Amadeus steht):
  einmal `ros2 topic pub --once /mission_manager/command_json
  std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"`, dann Schritt 5 und
  6, berichten, keine weiteren Läufe.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif8.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen:

1. Stand (HEAD), `git diff --stat` aus Schritt 1, Build (`rc`, Dauer, die
   Prüfzeilen), Tests.
2. F0 und Christophers Antwort wörtlich; der Vorlauf (`pruefung.txt`,
   `messen.txt` ganz).
3. **Je Lauf:** Start, Prüfungen (bei der Ausnahme „Radsensor“ der ganze
   Inhalt von `radsensor.txt` und `last_bei_sperre.txt`), `messen.txt` ganz,
   **`werkzeug.txt` ganz**, `etappen.txt`, `zaehler.txt`, größtes |v| und
   |w|, die Nachricht F-Lauf und Christophers Antwort wörtlich, ob und wie er
   umgestellt hat.
4. Die Tabelle N-1, T-1, L-1, T-2, T-3, T-4, T-6 je Lauf mit dem Gemessenen
   und „trifft zu“ oder „trifft nicht zu“, und G-1.
5. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
