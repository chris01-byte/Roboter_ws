# Aktueller Auftrag der KI-Linie: KI-F5 – Türdurchfahrt ohne Nahsensoren (Laborprobe)

**Erteilt am 22.11.2026 (nachts).** Er wird aktiv, sobald der Projektinhaber
ihn übergibt. Er läuft auf dem **Jetson**, mit Christopher. Der KI-Rechner
wird nicht gebraucht; Kamera und KI laufen in diesem Auftrag nicht.

**Warum es ihn gibt:** Entscheidung des Projektinhabers vom 22.11.2026:
„Die Nahbereichssensoren machen gerade Probleme. Deswegen schreibe jetzt
einen Testlauf, wo diese komplett deaktiviert werden. Wir wollen jetzt
einmal das Konzept überprüfen, ohne die Nahbereichssensoren zu nutzen.“
In KI-F3b fuhr Amadeus genau auf der Linie und hielt kurz vor der Tür an
einer Stelle an, die nur die Nahsensoren gemeldet haben können. Dieser
Auftrag prüft die Durchfahrt (und danach die Anfahrt vom Platz im Raum)
**ohne die beiden Nahsensoren**.

**Was „ohne Nahsensoren“ bedeutet (Startargument `nahsensoren:=false`):**

- Der VL53-Knoten startet nicht; in keiner Kostenkarte stehen
  VL53-Treffer, der Nahbereichs-Halt sieht nur noch die Karte des Lasers.
- Der **Kollisionsmonitor** hat im Kartierbetrieb nur die beiden VL53 als
  Quelle. Ohne sie **sieht er nichts, bremst nicht und hält nicht an**; er
  reicht die Fahrbefehle nur durch.
- Das **Fahrtor** gibt ohne VL53 nur die beiden begrenzten Kanäle des
  Erkunders frei (Drehen bis 0,15 rad/s, geradeaus bis 0,08 m/s). Fahrten
  über Nav2 und Raumfahrten bleiben ohne VL53 gesperrt.
- **Niedrige Dinge unter etwa 75 cm sieht Amadeus nicht** (Kisten,
  Taschen, Kabel, Schuhe, Türstopper). In der Simulation fuhr er gegen einen
  20 cm hohen Gegenstand. Pfosten, Türblatt und Wände sieht er weiter mit dem
  Laser; die Prüfungen des Werkzeugs und der Streifen vor jeder Etappe
  bleiben.
- Deshalb gilt: **Vor jeder Fahrt sieht Christopher nach, dass der Weg frei
  von niedrigen Dingen ist**, und während der Fahrt bleibt seine Hand am
  Not-Aus. Tempo wie bisher 5 cm/s.

**Ablauf:** neuer Build mit dem Schalter, dann Stufe 1 wie in KI-F3b: von
vorn auf gerader Linie durch die Tür. Stufe 2 (vom Platz im Raum selbst vor
die Tür und hindurch) nur nach bestandener Stufe 1.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](archiv/20261121-ki0-erstes-sehen/),
[KI-0N](archiv/20261121-ki0n-nachmessen/),
[KI-0R](archiv/20261121-ki0r-nachrechnen/),
[KI-1](archiv/20261121-ki1-blickrunde/),
[KI-F1](archiv/20261122-kif1-erste-etappen/),
[KI-F2](archiv/20261122-kif2-tuerdurchfahrt/),
[KI-F3 und KI-F3b](archiv/20261122-kif3-tuer-gerade/),
[KI-F4 (nicht ausgeführt)](archiv/20261122-kif4-ersetzt/).

**Fragen dieses Auftrags:** (1) Kommt Amadeus ohne Nahsensoren, mittig vor
die offene Labortür gestellt, auf der geraden Linie durch die Türmitte in
einem Zug hindurch? (2) Findet er von einem Platz im Raum selbst vor die Tür
und kommt dann ohne Hilfe hindurch?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md`, Abschnitt 6a |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält; **neuer Release `kif5-<STAMP>`** mit eigener Umgebungsdatei `~/roboter_worktrees/kif5.env`. Der letzte real gelaufene Release ist `kif1-20261122_1515`; gegenüber ihm geändert sind nur die Startdateien (`nahsensoren`), das Fahrtor (`require_near_field`) und ein neues Profil des Kollisionsmonitors |
| Was neu ist | Das Startargument `nahsensoren:=false` (Vorgabe `true` = wie bisher): VL53-Knoten startet nicht, Kollisionsmonitor ohne VL53-Quellen, Fahrtor gibt nur die Dreh- und Direktbefehle des Erkunders ohne VL53 frei. Sonst wie in KI-F3b: `stage_drive_only:=true`, Werkzeug mit „Kostenkarte passt.“ und der Herkunft jeder belegten Stelle |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif5.md`: Build, Tests, die Prüfungen „ohne Nahsensoren“, die Messungen im Stand wörtlich, die Fahrt mit den Meldungen des Erkunders und des Werkzeugs, die Kriterien und Christophers Antworten wörtlich |
| Nicht-Ziele | Keine KI, keine Kamera, kein Rundblick, kein Nav2-Ziel; keine eigene Code- oder Parameteränderung; je Stufe keine Wiederholung der Fahrt; keine Fahrt außerhalb des Laborraums und des Flurs direkt hinter der Tür |
| Rückfall | `~/roboter_worktrees/kif5.env` und den Release-Ordner `kif5-<STAMP>` löschen; `kif1-20261122_1515`, `kif1.env` und alle früheren Releases bleiben unberührt. Ohne `nahsensoren:=false` verhält sich der neue Release wie der alte |
| Bereich und Freigabe | Laborraum und, für die Durchfahrt, der Flur unmittelbar hinter der Labortür (vom Projektinhaber am 21.11.2026 für die Durchfahrten verlangt). **Ohne Nahsensoren** auf ausdrückliche Entscheidung des Projektinhabers vom 22.11.2026; mit der Übergabe bestätigt er, dass ihm die Folgen oben bekannt sind. Christopher ist dabei, die Hand am Not-Aus, und sieht vor jeder Fahrt den Weg nach. 100 ms Anfahrzeit wie seit dem 15.11. |
| Stufe 2 | Läuft nur, wenn der Projektinhaber sie in der Übergabe nennt **und** Stufe 1 die Kriterien T-1 bis T-6 erfüllt hat |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3, genau wie dort beschrieben;
- **jeder Stackstart dieses Auftrags mit `nahsensoren:=false` und
  `stage_drive_only:=true`**, keiner ohne;
- **keine Fahrt ohne Christophers „ja“ auf die Frage, ob der Weg frei von
  niedrigen Dingen ist** (B1, D1);
- schreibend nur: die Stackstarts dieses Auftrags, die Missionsstarts, die
  hier stehen (Stufe 1: **genau einer**; Stufe 2: **genau zwei**, einer für
  die Anfahrt und einer für die Durchfahrt), je Stufe höchstens **ein**
  Missionsstopp und das Werkzeug `fahrziel_senden.py` genau so, wie es hier
  steht; kein `param set`, `lifecycle set`, `service call`, kein weiteres
  `topic pub`, keine Nav2-Ziele;
- **kein Missionsstart, wenn `stage_drive_only` nicht nachweislich `True`
  ist**; keiner für eine Durchfahrt, solange die letzte Messung nicht
  **alle drei** meldet: „Aufstellung passt.“, „Weg passt.“ und „Kostenkarte
  passt.“; keiner für die Anfahrt, solange sie nicht „Anfahrt passt.“ und
  „Kostenkarte passt.“ meldet;
- das Werkzeug nie mit `--aufstellung-egal`, `--breite-min`, `--breite-max`
  oder `--vor` aufrufen;
- `initial_scan_only` wird nie gesetzt und muss `False` melden;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`; `operator_stationary_confirmed:=true` nur nach
  Christophers „ja“;
- **jede Fahrt gibt es genau einmal** (Stufe 1: die Durchfahrt; Stufe 2:
  die Anfahrt und die Durchfahrt). Bricht eine ab oder hält sie an, wird
  sie nicht wiederholt, und es folgt keine weitere Fahrt. (Neu aufstellen
  und messen im Stand ist keine Fahrt und darf wiederholt werden.) Einzige
  Ausnahmen stehen unter „Motorregler antworten nicht“, „Radsensor beim
  Start gesperrt“ und „Nichts gesendet“;
- keine Frage vorab, ob die Motoren frei sind, und keine Fragerunde zu
  unveränderten Laborbedingungen (LAB-1). Gefragt wird nur, was in diesem
  Auftrag wörtlich als Frage steht;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an den Umgebungsdateien und an
  bestehenden Releases (außer neuen Prüfdateien unter `pruefung/kif5/`);
- Amadeus wird nur von Hand umgestellt, wenn kein Stack mit Motorfreigabe
  läuft;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- kein eigenes Anzeigeprogramm, nichts im Vollbild;
- Fragen an Christopher als Text, einzeln, ohne Auswahlfeld; Antworten
  wörtlich;
- keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht.

## Vorab festgelegte Kriterien

„Kette“ heißt: `Begin navigating` 0-mal, „Direkter Explore-Befehl verworfen“
0-mal, „Odometrie kurzzeitig nicht frisch“ 0-mal, „process has died“ 0-mal.

| Kennung | Kriterium |
|---|---|
| N-1 Ohne Nahsensoren | In jedem Stack: kein Knoten `vl53_near_field`; `require_near_field` des Fahrtors `False`; im Log die Zeile „TESTBETRIEB OHNE NAHSENSOREN“; während der Fahrt „Robot to slowdown“ und „Robot to approach“ je 0 |
| T-1 Vermessung | Mittig vor der Tür meldet das Werkzeug eine türbreit vermessene Öffnung (0,65 bis 0,95 m; erwartet 0,72 bis 0,80 m), „Aufstellung passt.“, „Weg passt.“ mit mindestens 0,30 m frei links und rechts der Fahrlinie und „Kostenkarte passt.“ |
| T-2 Abschluss | Meldung „Etappenfahrt abgeschlossen: … Quelle mensch; kein Nav2-Ziel“ mit höchstens 10 Etappen |
| T-3 Ausrichten | je Punkt höchstens drei Zeilen „ausgerichtet um …“; der jeweils letzte „Restfehler“ höchstens 3,5 Grad |
| T-4 Durch die Tür | Christopher: Amadeus steht ganz im Flur, auch die Hinterkante ist durch; nichts berührt, kein Eingriff |
| T-5 Abstand | Christopher: an Türpfosten und Türblatt blieb mindestens eine Handbreit |
| T-6 Kette | wie oben |
| H-1 Herkunft | Hält der Erkunder an, enthält `werkzeug.txt` die Zeilen „Herkunft der Stelle …“ und „Nahsensoren im Fahrstreifen …“ |

Für Stufe 2:

| Kennung | Kriterium |
|---|---|
| S-1 Anfahrt gemessen | Von einem Platz, an dem die Aufstellung von Hand nicht passt, meldet das Werkzeug eine türbreit vermessene Öffnung und „Anfahrt passt.“ |
| S-2 Anfahrt gefahren | Meldung „Etappenfahrt abgeschlossen: … Quelle mensch; kein Nav2-Ziel“; Christopher: Amadeus steht vor der Tür mit Blick zur Tür, nichts berührt, kein Eingriff |
| S-3 Danach passt es | Die Messung nach der Anfahrt meldet „Aufstellung passt.“ und „Weg passt.“, ohne dass jemand Amadeus angefasst hat |
| S-4 Durch die Tür | wie T-2 und T-4 |
| S-5 Abstand | wie T-5 |
| S-6 Kette | wie T-6, über den ganzen Stacklauf der Stufe 2 |

Der Kollisionsmonitor hat in diesem Betrieb keine Quelle; „Robot to
slowdown“ oder „Robot to approach“ wären ein Befund (N-1). Hält der Erkunder mit
„Nahbereich vor dem Roboter nicht frei“ oder „Streifen vor dem Roboter nicht
frei“ an, ist das ein Befund: berichten, nicht wiederholen. Das Werkzeug
schreibt dann in seine letzten Zeilen, was in der Kostenkarte vor dem
Roboter belegt ist und woher („Herkunft der Stelle …“, „Nahsensoren im
Fahrstreifen …“); diese Zeilen gehören in den Bericht.

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls ~/.local/share/amadeus/releases/ | tail -5; ls ~/roboter_worktrees/kif1.env
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.

## Schritt 1 – Stand holen, neuer Release-Ordner

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
mkdir -p ~/.local/share/amadeus/releases/kif5-$STAMP/pruefung
```

## Schritt 2 – eigene Umgebungsdatei

```bash
cp ~/roboter_worktrees/kif1.env ~/roboter_worktrees/kif5.env
```

In `~/roboter_worktrees/kif5.env` mit dem Datei-Werkzeug nur die Zeile
`export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/kif5-<STAMP>`
ändern. Prüfen:

```bash
source ~/roboter_worktrees/kif5.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
diff ~/roboter_worktrees/kif1.env ~/roboter_worktrees/kif5.env
mkdir -p "$SH_PR/kif5"
```

Erwartung: `rc=0`, Zähler `0`, `diff` zeigt genau die eine Zeile. **Jeder
ROS-Befehl dieses Auftrags beginnt mit `source ~/roboter_worktrees/kif5.env`.**

## Schritt 3 – Build (wie in KI-F1)

```bash
source ~/roboter_worktrees/kif5.env && cd "$SH_SRC" && \
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

Danach prüfen, dass der Schalter eingebaut ist und sich an den Profilen
nichts geändert hat:

```bash
source ~/roboter_worktrees/kif5.env; I="$SH_REL/product-install"; ALT=~/.local/share/amadeus/releases/kif1-20261122_1515/product-install
ls "$I" | wc -l
for f in "$I/robot_navigation/share/robot_navigation/launch/nav_mapping.launch.py" \
  "$I/robot_bringup/share/robot_bringup/launch/app_mapping.launch.py"; do \
  echo "$(grep -c nahsensoren "$f") $(grep -c stage_drive_only "$f") $(basename "$f")"; done
echo "$(grep -c start_vl53 "$I/vl53_near_field/share/vl53_near_field/launch/vl53_near_field.launch.py") vl53_near_field.launch.py"
echo "$(grep -c require_near_field "$(find "$I/robot_navigation" -name cmd_vel_mission_gate.py | head -1)") cmd_vel_mission_gate.py"
ls "$I/vl53_near_field/share/vl53_near_field/config/collision_monitor_ohne_nahsensoren.yaml"
for f in explore/share/explore/config/self_healing_params.yaml explore/share/explore/config/explore_params.yaml \
  robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml \
  robot_navigation/share/robot_navigation/config/nav2_params_real.yaml \
  vl53_near_field/share/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml \
  vl53_near_field/share/vl53_near_field/config/collision_monitor_mapping_params.yaml \
  amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml; do \
  diff -q "$I/$f" "$ALT/$f" && echo "gleich: $f"; done
diff -q "$(find "$I/explore" -name explore_node.py | head -1)" "$(find "$ALT/explore" -name explore_node.py | head -1)" && echo "gleich: explore_node.py"
```

Erwartet: `25`; die Zeilen `10 2 nav_mapping.launch.py`, `3 2
app_mapping.launch.py`, `3 vl53_near_field.launch.py`, `11
cmd_vel_mission_gate.py`; die Datei des neuen Profils; achtmal `gleich: …`.
Jede Abweichung, Build-Fehler oder fehlendes Paket: nichts starten,
berichten.

## Schritt 4 – gezielte Tests

```bash
source ~/roboter_worktrees/kif5.env && cd "$SH_SRC" && \
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

Erwartung: `350 passed` (die 345 aus KI-F1 und 5 neue zum Schalter) und
für die KI-Linie `264 passed`. Bei Fehlschlägen nichts starten,
berichten.

---

# Stufe 1 – von vorn durch die Tür

## Teil A – Aufstellen und Messen (ohne Motorfreigabe, nichts fährt)

Der Stack startet **ohne** `active_drive` und ohne `enable_auto_explore`;
die Basis wird nicht bestromt (LAB-1 §3). In Teil A wird keine Mission
gesendet. Christopher darf Amadeus zwischen den Messungen umstellen.

### A1 – Aufstellen und Stack ohne Motorfreigabe

Anweisung: „Bitte stelle Amadeus **mittig vor die offene Labortür, etwa 2 m
davor, den Blick gerade durch die Tür**. Die Tür steht so weit offen wie
möglich und ist gesichert. Zwischen Amadeus und der Tür und in der Tür
liegt und steht nichts.“ Frage: „Steht Amadeus so still, und bleibt er
während des Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif5.env
D="$SH_PR/kif5"; mkdir -p "$D"
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
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter_stand.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter_stand.txt"
grep -c "Traceback" "$D/launch_stand.log"
```

Erwartet: `True`, `False`, `0`.

Dann, ob die Nahsensoren wirklich aus sind:

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"; L="$D/launch_stand.log"
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

### A2 – messen, bis Aufstellung und Weg passen

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"; K=1
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen_$K.txt"
```

Das Werkzeug nennt unter „Türbreit vermessen“ jede passende Öffnung mit
drei Zeilen: die Lage („Aufstellung passt.“ oder was zu ändern ist), die
Fahrlinie („Weg passt.“ oder was zu ändern ist) und die Kostenkarte auf dem
ganzen Weg („Kostenkarte passt.“ oder wo sie belegt ist, dann mit einer
Zeile „Herkunft der Stelle …“).

- **„Aufstellung passt nicht: …“ oder „Weg passt nicht: …“:** Christopher den
  Hinweis wörtlich nennen (zum Beispiel „bitte etwa 15 cm nach rechts
  versetzen“), er stellt um, dann mit `K=2`, `K=3` … erneut messen.
- **„Kostenkarte passt nicht: …“:** Christopher die Zeile „Herkunft der
  Stelle …“ vorlesen und fragen: „Das Werkzeug meldet etwa **A** cm vor dem Gehäuse und **B** cm **links** (oder **rechts**) der Mitte etwas. Steht oder liegt dort etwas, und was?“ (A steht in der Zeile „Herkunft der Stelle …“, B ist der Wert „… m links/rechts der Mitte“ mal 100.) Liegt dort etwas und
  kann er es wegnehmen: wegnehmen lassen und erneut messen.
- **„Keine Öffnung ist türbreit vermessen“:** Christopher sagen: „Von hier
  wird die Tür nicht als Tür gemessen. Bitte stelle ihn genauer mittig vor
  die Tür.“ Dann erneut messen.
- Höchstens acht Messungen. Passt es dann nicht: Stack beenden, berichten,
  Ende.

Sobald eine Messung **alle drei** meldet, „Aufstellung passt.“, „Weg
passt.“ und „Kostenkarte passt.“, Christopher einmal fragen: „Ich messe geradeaus eine Öffnung,
**B** m breit und **E** m entfernt. Ist das die Labortür?“ (B und E aus der
Tabelle.) Bei „nein“: wie „passt nicht“ behandeln. Bei „ja“: **Amadeus
bleibt ab jetzt genau so stehen.**

### A3 – Stack beenden

```bash
source ~/roboter_worktrees/kif5.env; kill -INT "$(cat "$SH_PR/kif5/launch_stand.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

---

## Teil B – die Fahrt durch die Tür

### B1 – Ansage und scharfer Start

Zuerst Christopher sagen: „**Amadeus fährt gleich ohne Nahsensoren.** Er
sieht dann nichts, was niedriger als etwa 75 cm ist, zum Beispiel Kisten,
Taschen, Kabel, Schuhe oder einen Türstopper, und der Kollisionsmonitor
bremst nicht. Pfosten, Türblatt und Wände sieht er weiter mit dem Laser.
Bitte sieh nach, dass zwischen Amadeus und der Tür, in der Tür und im Flur bis gut
einen Meter hinter der Tür nichts am Boden liegt oder steht.“ Frage:
„Ist der Weg frei von niedrigen Dingen?“ Nur nach „ja“ weiter. Bei „nein“:
Christopher räumt es weg, dann noch einmal fragen.

Dann Christopher sagen: „Gleich fährt Amadeus in kurzen Etappen **geradeaus auf
die Türmitte zu**, ohne Umweg. Gut einen Meter vor der Tür stellt er die
Richtung nach, wenn nötig, fährt hindurch und bleibt knapp einen halben
Meter dahinter im Flur stehen; das dauert etwa zwei Minuten. Du stehst
seitlich im Laborraum auf der Seite ohne Türblatt, nicht zwischen Amadeus
und der Tür, nicht in der Tür und nicht im Flur vor ihm, mit der Hand am
Not-Aus.“ Frage: „Steht Amadeus unverändert, und bleibt er während des
Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif5.env
D="$SH_PR/kif5"
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
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
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
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"; L="$D/launch.log"
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
   source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
   uptime | tee "$D/last_bei_sperre_1.txt"
   python3 "$SH_SRC/ki_erkundung/werkzeuge/radsensor_zustand.py" 2>&1 | tee "$D/radsensor_1.txt"
   ```

2. Stack geordnet beenden (wie B5) und Christopher in einem Satz sagen: „Der
   Radsensor hat sich beim Hochfahren selbst gesperrt; ich starte den Stack
   einmal neu, Amadeus fährt dabei nicht.“
3. Die Dateien des ersten Starts beiseitelegen, damit B1 bis B5 mit
   denselben Befehlen weiterlaufen:

   ```bash
   source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
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
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen_scharf.txt"
```

Es muss wieder eine türbreit vermessene Öffnung mit „Aufstellung passt.“,
„Weg passt.“ und „Kostenkarte passt.“ dastehen. Deren Richtung aus der Tabelle (Zahl mit
Vorzeichen, ohne Gradzeichen) ist `R`. Passt es nicht: keine Mission;
weiter wie unter „Nichts gesendet“.

### B3 – Mission starten und Fahrziel senden

Genau einmal die Mission, dann das Werkzeug; es wartet, bis der Erkunder
wartet, misst, prüft, sendet das Ziel und zeigt dessen Meldungen bis zum
Ende:

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --richtung R --richtung-toleranz 10 --hinter 0.45 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/werkzeug.txt"; echo "rc=${PIPESTATUS[0]}"
```

(`--hinter 0.45`, weil im Flur laut Christopher 1,20 m bis zum ersten
Hindernis frei sind.)

**Nichts gesendet (Ausnahme):** Meldet das Werkzeug „Nichts gesendet“ oder
„Der Erkunder wartet nicht“, hat sich Amadeus nicht bewegt. Dann genau
einmal den Stopp senden, den Stack geordnet beenden (B5) und berichten, was
das Werkzeug gesagt hat. **Genau ein** weiterer Durchgang ab Teil A ist
erlaubt.

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
Schwanken. Kurzes Stehenbleiben zwischen den Etappen, kleines Nachstellen
der Richtung und langsames Kriechen neben dem Türblatt sind gewollt.

### B4 – sichern (Amadeus bleibt stehen, der Stack läuft noch)

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
date -Iseconds > "$D/ende.txt"
grep -n "Etappenfahrt\|Fahrziel" "$D/launch.log" | tee "$D/etappen.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
```

Dazu aus den Sekundenzeilen von `base_hardware` im `launch.log`, wie im
Bericht zu KI-F2: größtes |v| und größtes |w| zwischen Missionsstart und
Ende. Dann Christopher fragen, je einzeln:

1. Steht Amadeus ganz im Flur, auch mit der Hinterkante?
2. Wie viel Platz blieb an den Türpfosten und am Türblatt (etwa in cm, je
   Seite)?
3. Hat er etwas berührt, oder musstest du eingreifen?
4. Ist er gerade auf die Tür zugefahren, und hat er die Richtung
   nachgestellt? Wo?
5. Nur wenn der Erkunder angehalten hat und `werkzeug.txt` eine Zeile
   „Herkunft der Stelle …“ enthält: „Das Werkzeug meldet etwa **A** cm vor dem Gehäuse und **B** cm **links** (oder **rechts**) der Mitte etwas. Steht oder liegt dort etwas, und was?“ (A steht in der Zeile „Herkunft der Stelle …“, B ist der Wert „… m links/rechts der Mitte“ mal 100.)

### B5 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif5.env; kill -INT "$(cat "$SH_PR/kif5/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Danach stellt Christopher Amadeus von Hand zurück.

---

# Stufe 2 – vom Platz im Raum selbst vor die Tür und hindurch

Nur, wenn der Projektinhaber Stufe 2 in der Übergabe genannt hat und Stufe 1
T-1 bis T-6 erfüllt hat. Sonst: Bericht, Ende.

**Was Amadeus hier tut:** Er misst die Tür von seinem Platz, fährt zu einem
Punkt auf der Türachse gut zwei Meter vor der Tür, dreht sich dort zur Tür
und fährt knapp einen halben Meter auf sie zu. Dann steht er so, wie ihn in
Stufe 1 Christopher hingestellt hat. Von dort misst er neu und fährt wie in
Stufe 1 hindurch. Das sind zwei Missionen in einem Stacklauf.

**Was bekannt nicht geht:** Von der Seite des offenen Türblatts wird die Tür
bisher falsch vermessen (1,25 m statt 0,85 m). Von dort meldet das Werkzeug
„Keine Öffnung ist türbreit vermessen“; dann braucht es einen anderen
Platz. Das ist ein Befund für den Bericht, kein Fehler der Ausführung.

## Teil C – Platz wählen und messen (ohne Motorfreigabe, nichts fährt)

### C1 – Platz und Stack ohne Motorfreigabe

Anweisung: „Bitte stelle Amadeus an einen Platz im Laborraum, **nicht**
mittig vor die Tür: mindestens 2 m von der Tür entfernt und mindestens einen
halben Meter neben der Türmitte, auf der Seite **ohne** Türblatt. Die Tür
liegt vor ihm oder seitlich, nicht in seinem Rücken. Um ihn herum ist eine
Armlänge frei, und zwischen ihm und dem Platz vor der Tür steht nichts.“
Frage: „Steht Amadeus so still, und bleibt er während des Starts (etwa eine
Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif5.env
D="$SH_PR/kif5"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  stage_drive_only:=true nahsensoren:=false \
  > "$D/launch_stand2.log" 2>&1 < /dev/null &
echo $! > "$D/launch_stand2.pid"; cat "$D/launch_stand2.pid"; date -Iseconds
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter_stand2.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter_stand2.txt"
grep -c "Traceback" "$D/launch_stand2.log"
```

Erwartet: `True`, `False`, `0`.

Dann, ob die Nahsensoren wirklich aus sind:

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"; L="$D/launch_stand2.log"
{ echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  ros2 param get /collision_monitor vl53_left.enabled 2>&1
  ros2 param get /collision_monitor vl53_right.enabled 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"; } | tee "$D/ohne_nahsensoren_stand2.txt"
```

Erwartet: `vl53_near_field-Knoten: 0`, dreimal `Boolean value is: False`,
`Testbetrieb im Log:` mindestens `2`. Meldet einer der beiden Befehle zum
`collision_monitor`, der Parameter sei nicht gesetzt, kennt diese Version
das Abschalten einzelner Quellen nicht; er bekommt dann ohnehin keine
VL53-Daten. Das berichten, kein Abbruch. **Läuft ein Knoten
`vl53_near_field` oder meldet das Fahrtor `True`: keine Mission, Stack
geordnet beenden, berichten.**

### C2 – messen, bis die Anfahrt passt

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"; K=1
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --vor-die-tuer --nur-messen 2>&1 | tee "$D/anfahrt_messen_$K.txt"
```

Das Werkzeug nennt unter „Türbreit vermessen“ jede passende Öffnung mit
zwei Zeilen: wie Amadeus zu ihr steht, und die Anfahrt.

- **„Anfahrt: … – Anfahrt passt.“** und darunter **„Kostenkarte
  passt.“:** weiter unten bei der Frage.
- **„Anfahrt passt nicht: …“:** Christopher den Grund wörtlich nennen und
  sagen: „Bitte stelle ihn an einen anderen Platz.“ Dann mit `K=2`, `K=3` …
  erneut messen.
- **„Anfahrt: nicht nötig, er steht schon passend vor der Tür.“:**
  Christopher sagen: „Er steht schon passend. Bitte stelle ihn weiter zur
  Seite.“ Dann erneut messen.
- **„Keine Öffnung ist türbreit vermessen“:** Christopher sagen: „Von hier
  wird die Tür nicht als Tür gemessen. Bitte stelle ihn an einen anderen
  Platz, von dem er gerader auf die Tür sieht.“ Dann erneut messen.
- Höchstens sechs Messungen. Passt es dann nicht: Stack beenden (C3),
  berichten, Ende.

Sobald eine Messung „Anfahrt passt.“ und „Kostenkarte passt.“ meldet,
Christopher einmal fragen: „Ich
messe eine Öffnung, **B** m breit und **E** m entfernt, **R** Grad **links
oder rechts** von seiner Blickrichtung. Ist das die Labortür?“ (B, E und R
aus der Tabelle; positives R ist links.) Bei „nein“: wie „passt nicht“
behandeln. Bei „ja“: **Amadeus bleibt ab jetzt genau so stehen.**

### C3 – Stack beenden

```bash
source ~/roboter_worktrees/kif5.env; kill -INT "$(cat "$SH_PR/kif5/launch_stand2.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

## Teil D – Anfahrt und Durchfahrt

### D1 – Ansage und scharfer Start

Zuerst Christopher sagen: „**Amadeus fährt gleich ohne Nahsensoren.** Er
sieht dann nichts, was niedriger als etwa 75 cm ist, zum Beispiel Kisten,
Taschen, Kabel, Schuhe oder einen Türstopper, und der Kollisionsmonitor
bremst nicht. Pfosten, Türblatt und Wände sieht er weiter mit dem Laser.
Bitte sieh nach, dass zwischen Amadeus und dem Platz vor der Tür, in der Tür und im
Flur bis gut einen Meter hinter der Tür nichts am Boden liegt oder steht.“ Frage:
„Ist der Weg frei von niedrigen Dingen?“ Nur nach „ja“ weiter. Bei „nein“:
Christopher räumt es weg, dann noch einmal fragen.

Dann Christopher die Schritte aus der letzten Zeile „Anfahrt: …“ vorlesen (zum
Beispiel „30 Grad nach links drehen, 1,15 m fahren, 90 Grad nach rechts
drehen, 0,45 m fahren“) und dazu sagen: „Danach steht er etwa eine halbe
Minute, misst neu und fährt wie vorhin gerade durch die Tür. Du stehst so,
dass du weder auf diesem Weg noch zwischen Amadeus und der Tür stehst, nicht
in der Tür und nicht im Flur vor ihm, mit der Hand am Not-Aus.“ Frage:
„Steht Amadeus unverändert, und bleibt er während des Starts (etwa eine
Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif5.env
D="$SH_PR/kif5"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  stage_drive_only:=true nahsensoren:=false \
  > "$D/launch2.log" 2>&1 < /dev/null &
echo $! > "$D/launch2.pid"; cat "$D/launch2.pid"; date -Iseconds > "$D/launch2_start.txt"
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
grep -n "Anfahrverhalten bestaetigt" "$D/launch2.log" | tee "$D/anfahrzeit2.txt"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter2.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter2.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$D/vorpruefung2.json" > "$D/vorpruefung2.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung2.txt"
```

Dann, ob die Nahsensoren wirklich aus sind:

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"; L="$D/launch2.log"
{ echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  ros2 param get /collision_monitor vl53_left.enabled 2>&1
  ros2 param get /collision_monitor vl53_right.enabled 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"; } | tee "$D/ohne_nahsensoren2.txt"
```

Erwartet: `vl53_near_field-Knoten: 0`, dreimal `Boolean value is: False`,
`Testbetrieb im Log:` mindestens `2`. Meldet einer der beiden Befehle zum
`collision_monitor`, der Parameter sei nicht gesetzt, kennt diese Version
das Abschalten einzelner Quellen nicht; er bekommt dann ohnehin keine
VL53-Daten. Das berichten, kein Abbruch. **Läuft ein Knoten
`vl53_near_field` oder meldet das Fahrtor `True`: keine Mission, Stack
geordnet beenden, berichten.**

Erwartungen und die Ausnahmen „Motorregler antworten nicht“ und
„Radsensor beim Start gesperrt“ wie in B1; die Ausnahme gilt hier noch
einmal, unabhängig von Stufe 1. Dabei in Schritt 1 `_3` (beim zweiten Mal
`_4`) in den Dateinamen und in Schritt 3 statt der dortigen Zeile:

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
for f in launch2.log launch2.pid launch2_start.txt anfahrzeit2.txt schalter2.txt vorpruefung2.json vorpruefung2.txt; do \
  [ -e "$D/$f" ] && mv "$D/$f" "$D/erster_start_$f"; done; ls "$D"
```

Zum Beenden D7 statt B5; der neue Start ist D1 von der Frage an.

### D2 – Anfahrt noch einmal messen (nichts fährt)

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --vor-die-tuer --nur-messen 2>&1 | tee "$D/anfahrt_messen_scharf.txt"
```

Es muss wieder „Anfahrt passt.“ und „Kostenkarte passt.“ dastehen. Die Richtung dieser Öffnung aus
der Tabelle (Zahl mit Vorzeichen, ohne Gradzeichen) ist `R`. Passt es nicht:
keine Mission; Stack geordnet beenden (D7), berichten.

### D3 – erste Mission: die Anfahrt

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart_anfahrt.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --vor-die-tuer --richtung R --richtung-toleranz 10 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/anfahrt.txt"; echo "rc=${PIPESTATUS[0]}"
```

Erwartet: `rc=0` und „Etappenfahrt abgeschlossen: …“. Meldet das Werkzeug
„Nichts gesendet“ oder „Der Erkunder wartet nicht“: wie in B3 unter „Nichts
gesendet“ (Stopp, Stack beenden, berichten; genau ein weiterer Durchgang ab
Teil C ist erlaubt). Hält der Erkunder an oder scheitert die Anfahrt: keine
zweite Mission; weiter bei D6.

Christopher drückt den Not-Aus wie in B3 beschrieben. Drehen auf der Stelle
um große Winkel und kurzes Stehen zwischen den Schritten sind gewollt.

### D4 – Durchfahrt messen (nichts fährt, niemand fasst Amadeus an)

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/durchfahrt_messen.txt"
```

Es muss eine türbreit vermessene Öffnung mit „Aufstellung passt.“, „Weg
passt.“ und „Kostenkarte passt.“ dastehen; deren Richtung ist `R2`. **Passt es nicht: keine zweite
Mission.** Das Werkzeug nennt, was fehlt (zum Beispiel „bitte etwa 10 cm
nach rechts versetzen“); das ist der Befund zu S-3. Weiter bei D6.

### D5 – zweite Mission: die Durchfahrt

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart_durchfahrt.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --richtung R2 --richtung-toleranz 10 --hinter 0.45 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/werkzeug2.txt"; echo "rc=${PIPESTATUS[0]}"
```

Meldet das Werkzeug „Der Erkunder wartet nicht“ (der zweite Missionsstart
im selben Stacklauf ist am Roboter neu): nichts wiederholen; einmal den
Stopp senden wie in B3, weiter bei D6. Das ist ein Befund.

### D6 – sichern (Amadeus bleibt stehen, der Stack läuft noch)

```bash
source ~/roboter_worktrees/kif5.env; D="$SH_PR/kif5"
date -Iseconds > "$D/ende2.txt"
grep -n "Etappenfahrt\|Fahrziel\|Mission beendet" "$D/launch2.log" | tee "$D/etappen2.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died"; do \
  echo "$m: $(grep -c "$m" "$D/launch2.log")"; done | tee "$D/zaehler2.txt"
```

Dazu größtes |v| und größtes |w| an der Basis wie in B4. Dann Christopher
fragen, je einzeln:

1. Ist Amadeus selbst vor die Tür gefahren und hat sich zur Tür gedreht?
   Stand er danach mittig davor?
2. Steht er jetzt ganz im Flur, auch mit der Hinterkante?
3. Wie viel Platz blieb an den Türpfosten und am Türblatt (etwa in cm, je
   Seite)?
4. Hat er etwas berührt, oder musstest du eingreifen?

### D7 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif5.env; kill -INT "$(cat "$SH_PR/kif5/launch2.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Danach stellt Christopher Amadeus von Hand zurück.

---

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

Datei `~/ki_erkundung_bericht_kif5.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen:

1. Stand (HEAD) und `STAMP`.
2. Build (`rc`, Dauer, die Prüfzeilen aus Schritt 3), Tests (Schritt 4) und
   je Stack die Prüfung „ohne Nahsensoren“ (`ohne_nahsensoren*.txt`).
3. Teil A: `schalter_stand.txt`; der ganze Inhalt jeder Datei
   `messen_K.txt` mit dem Hinweis, den Christopher bekam, und was er
   geändert hat; seine Antwort auf die Frage nach der Labortür.
4. Teil B: Christophers Antwort auf die Frage nach dem freien Weg und zum
   Start; Anfahrzeit, Schalter, Vorprüfung; bei der
   Ausnahme „Radsensor beim Start gesperrt“ der ganze Inhalt von
   `radsensor_K.txt` und `last_bei_sperre_K.txt` und was der zweite Start
   ergab;
   `messen_scharf.txt`; **der ganze Inhalt von `werkzeug.txt`** (mit den
   Zeilen „Fahrlinie …“ und „Kostenkarte …“), `etappen.txt` und
   `zaehler.txt`; größtes |v| und |w| an der Basis; Christophers Antworten
   nach der Fahrt wörtlich.
5. Die Tabelle N-1, T-1 bis T-6 und H-1 mit dem Gemessenen und „trifft zu“
   oder „trifft nicht zu“.
6. Stufe 2, falls gelaufen: `schalter_stand2.txt`; der ganze Inhalt jeder
   Datei `anfahrt_messen_K.txt` mit dem, was Christopher gesagt bekam und
   geändert hat; seine Antworten auf die Fragen nach der Labortür und nach
   dem freien Weg; Anfahrzeit, Schalter und Vorprüfung des zweiten scharfen
   Starts;
   `anfahrt_messen_scharf.txt`; **der ganze Inhalt von `anfahrt.txt`,
   `durchfahrt_messen.txt` und `werkzeug2.txt`**; `etappen2.txt` und
   `zaehler2.txt`; größtes |v| und |w|; Christophers Antworten wörtlich; die
   Tabelle S-1 bis S-6. Falls nicht gelaufen: warum nicht.
7. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
