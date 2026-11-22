# Aktueller Auftrag der KI-Linie: KI-F1 – Erste Etappen (Fahrteil ohne Nav2)

**Erteilt am 21.11.2026 (nachts).** Er wird aktiv, sobald der Projektinhaber
ihn übergibt. Er läuft auf dem **Jetson**, mit Christopher. Der KI-Rechner
wird nicht gebraucht; Kamera und KI laufen in diesem Auftrag nicht.

**Zum ersten Mal in dieser Linie fährt Amadeus:** in kurzen geraden Etappen
von höchstens 0,5 m mit 5 cm/s, vom Einfachen zum Schwierigen.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](../20261121-ki0-erstes-sehen/),
[KI-0N](../20261121-ki0n-nachmessen/),
[KI-0R](../20261121-ki0r-nachrechnen/),
[KI-1](../20261121-ki1-blickrunde/).

**Frage dieses Auftrags:** Fährt Amadeus am echten Roboter mit dem neuen
Schalter „Etappenfahrt“ eine gerade Etappe so wie am 11.09.2026 und in der
Simulation, und kommt er damit in einem Zug durch die offene Labortür
(anfahren, ausrichten, hindurch)?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md`, Abschnitt 6a |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält; neuer Release `kif1-<STAMP>`. Der letzte real gelaufene Release ist `ki1-20261121_2043` (ohne Etappenfahrt) |
| Was neu ist | Genau eine Verhaltensänderung: Startargument `stage_drive_only:=true` (der Erkunder wartet auf ein Fahrziel und fährt es ohne Nav2 in geraden Etappen an). Das Fahrziel sendet `ki_erkundung/werkzeuge/fahrziel_senden.py` |
| Stufen | **1** eine gerade Etappe von 0,5 m · **2** durch die offene Labortür, in einem Zug. Stufe 2 nur, wenn Stufe 1 ihre Kriterien erfüllt hat. Eine eigene Stufe „ausrichten und eine Etappe“ entfällt auf Wunsch des Projektinhabers: Das Ausrichten gehört zur Türdurchfahrt und geschieht dort mindestens 0,7 m vor der Türlinie |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif1.md`: Build, Tests, Prüfung im Stand, je Stufe die Meldungen des Erkunders, die Kriterien und Christophers Antworten wörtlich |
| Nicht-Ziele | Keine KI, keine Kamera, kein Rundblick, kein Nav2-Ziel; keine eigene Code- oder Parameteränderung; keine Wiederholung einer misslungenen Stufe |
| Rückfall | `~/roboter_worktrees/kif1.env` und den Release-Ordner `kif1-<STAMP>` löschen; alle bisherigen Releases und Umgebungsdateien bleiben unberührt. Ohne das Startargument verhält sich der Stack wie am 19.11. |
| Bereich und Freigabe | Stufe 1: **nur der Laborraum** (LAB-1). **Stufe 2 führt durch die Labortür in den Flur.** Der Projektinhaber hat die Türdurchfahrt am 21.11.2026 ausdrücklich verlangt; mit der Übergabe dieses Auftrags gibt er den Flur unmittelbar hinter der Labortür für diese eine Durchfahrt frei. Christopher ist dabei, die Hand am Not-Aus. 100 ms Anfahrzeit wie seit dem 15.11. |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3;
- schreibend nur: die Stackstarts dieses Auftrags, je scharfem Start **genau
  ein** Missionsstart, höchstens **ein** Missionsstopp und das Werkzeug
  `fahrziel_senden.py` genau so, wie es hier steht; kein `param set`,
  `lifecycle set`, `service call`, kein weiteres `topic pub`, keine
  Nav2-Ziele;
- **kein Missionsstart, wenn `stage_drive_only` nicht nachweislich `True`
  ist.** Ohne den Schalter würde Amadeus nach der alten Erkundung losfahren;
- `initial_scan_only` wird in diesem Auftrag nie gesetzt und muss `False`
  melden;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`; `operator_stationary_confirmed:=true` nur nach
  Christophers „ja“;
- **keine Stufe zweimal.** Misslingt eine Stufe, wird sie nicht wiederholt
  und die nächste nicht begonnen. Einzige Ausnahme steht unter „Motorregler
  antworten nicht“;
- **keine Frage vorab, ob die Motoren frei sind**, und keine Fragerunde zu
  unveränderten Laborbedingungen (LAB-1). Gefragt wird nur, was in diesem
  Auftrag wörtlich als Frage steht;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an `~/roboter_worktrees/selbstheilung-v2.env`,
  an `ki1.env` und an bestehenden Releases;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- kein eigenes Anzeigeprogramm, nichts im Vollbild;
- Fragen an Christopher als Text, einzeln, ohne Auswahlfeld; Antworten
  wörtlich;
- keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht.

## Vorab festgelegte Kriterien

Gemessen wird an den Zeilen des Erkunders im `launch.log` und an
Christophers Angaben. „Kette“ heißt in jeder Stufe: `Begin navigating`
0-mal, „Direkter Explore-Befehl verworfen“ 0-mal, „Odometrie kurzzeitig
nicht frisch“ 0-mal, „process has died“ 0-mal.

| Kennung | Kriterium |
|---|---|
| **Stufe 1** | |
| F1-1 Abschluss | Meldung „Etappenfahrt abgeschlossen: 1 Etappe(n), … Quelle test; kein Nav2-Ziel“ |
| F1-2 Weg | „realer LiDAR-Weg“ 0,49 bis 0,55 m; Christophers Maßband 0,45 bis 0,60 m |
| F1-3 Spur | „seitlich“ höchstens 0,03 m, „Winkelfehler“ höchstens 3 Grad |
| F1-4 Dauer | von „Fahrziel angenommen“ bis „Etappe 1 beendet“ höchstens 30 s (Simulation 11,5 s) |
| F1-5 Kette | wie oben |
| F1-6 Mensch | gerade gefahren, von selbst angehalten, nichts berührt, kein Eingriff |
| **Stufe 2** | |
| F2-1 Vermessung | die von Christopher benannte Öffnung ist „befahrbar ja“ und 0,70 bis 0,90 m breit |
| F2-2 Abschluss | Meldung „Etappenfahrt abgeschlossen: … Quelle mensch; kein Nav2-Ziel“ mit höchstens 10 Etappen |
| F2-3 Ausrichten | je Punkt höchstens drei Zeilen „ausgerichtet um …“; der jeweils letzte „Restfehler“ höchstens 3,5 Grad |
| F2-4 Durch die Tür | Christopher: Amadeus steht ganz im Flur, auch die Hinterkante ist durch; nichts berührt, kein Eingriff |
| F2-5 Abstand | Christopher: an beiden Türpfosten blieb mindestens eine Handbreit |
| F2-6 Kette | wie oben |

Keine Erwartung gibt es zu „Robot to slowdown“ und „Robot to approach“ (der
Kollisionsmonitor darf an der Tür bremsen); beides wird gezählt und
berichtet. Hält der Erkunder mit „Nahbereich vor dem Roboter nicht frei“
oder „Streifen vor dem Roboter nicht frei“ an, ist das ein Befund: berichten,
nicht wiederholen. Trifft ein Kriterium nicht zu, endet der Auftrag mit dem
Bericht.

---

## Einmal je Sitzung

### Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls ~/.local/share/amadeus/releases/ | tail -5
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.

### Schritt 1 – Stand holen, neuer Release-Ordner

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
mkdir -p ~/.local/share/amadeus/releases/kif1-$STAMP/pruefung
```

### Schritt 2 – eigene Umgebungsdatei

```bash
cp ~/roboter_worktrees/selbstheilung-v2.env ~/roboter_worktrees/kif1.env
```

In `~/roboter_worktrees/kif1.env` mit dem Datei-Werkzeug nur die Zeile
`export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/kif1-<STAMP>`
ändern. Prüfen:

```bash
source ~/roboter_worktrees/kif1.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
diff ~/roboter_worktrees/selbstheilung-v2.env ~/roboter_worktrees/kif1.env
```

Erwartung: `rc=0`, Zähler `0`, `diff` zeigt genau die eine Zeile. **Jeder
ROS-Befehl dieses Auftrags beginnt mit `source ~/roboter_worktrees/kif1.env`.**

### Schritt 3 – Build (wie am 19.11. und in KI-1)

```bash
source ~/roboter_worktrees/kif1.env && cd "$SH_SRC" && \
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

Danach prüfen, dass beide Schalter eingebaut sind und sich an den Profilen
nichts geändert hat:

```bash
source ~/roboter_worktrees/kif1.env; I="$SH_REL/product-install"; ALT=~/.local/share/amadeus/releases/selbstheilung-sh9-20261119_1932/product-install
ls "$I" | wc -l
for f in "$(find "$I/explore" -name explore_node.py | head -1)" \
  "$I/explore/share/explore/launch/explore.launch.py" \
  "$I/robot_navigation/share/robot_navigation/launch/nav_mapping.launch.py" \
  "$I/robot_bringup/share/robot_bringup/launch/app_mapping.launch.py"; do \
  echo "$(grep -c stage_drive_only "$f") $(grep -c initial_scan_only "$f") $(basename "$f")"; done
find "$I/explore" -name stage_drive.py | wc -l
for f in explore/share/explore/config/self_healing_params.yaml explore/share/explore/config/explore_params.yaml \
  robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml \
  vl53_near_field/share/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml \
  amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml; do \
  diff -q "$I/$f" "$ALT/$f" && echo "gleich: $f"; done
```

Erwartet: `25`; die vier Zeilen `5 11 explore_node.py`, `3 3 explore.launch.py`,
`2 3 nav_mapping.launch.py`, `2 2 app_mapping.launch.py`; `1`; fünfmal
`gleich: …`. Jede Abweichung, Build-Fehler oder fehlendes Paket: nichts
starten, berichten.

### Schritt 4 – gezielte Tests

```bash
source ~/roboter_worktrees/kif1.env && cd "$SH_SRC" && \
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

Erwartung: `345 passed` (die 267 aus KI-1 und 78 neue) und für die KI-Linie
`228 passed`. Bei Fehlschlägen nichts starten, berichten.

---

## Teil A – Prüfung im Stand (ohne Motorfreigabe)

Der Stack startet **ohne** `active_drive` und ohne `enable_auto_explore`;
die Basis wird nicht bestromt, es kann nichts fahren (LAB-1 §3). Die Motoren
dürfen dabei gesperrt bleiben. In Teil A wird keine Mission gesendet.

Christopher einmal fragen: „Steht Amadeus im Laborraum still, und bleibt er
während des Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif1.env
D="$SH_PR/stand"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  stage_drive_only:=true \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/stand"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter.txt"
ros2 topic info /ki_erkundung/fahrziel_json 2>&1 | tee -a "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 \
  --json "$D/pruefung.json" > "$D/pruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/pruefung.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen 2>&1 | tee "$D/messen.txt"; echo "rc=${PIPESTATUS[0]}"
grep -c "Traceback" "$D/launch.log"
```

Erwartet: `Boolean value is: True` (Etappenfahrt), `Boolean value is: False`
(Rundblick), `Subscription count: 1`, Prüfskript Exit 0 wie in KI-1 ohne
`--aktiv`, vom Werkzeug eine Tabelle der Öffnungen (auch eine leere Tabelle
ist in Ordnung) mit `rc=0`, und `0` Zeilen „Traceback“. Bei `FEHL` mit
„erreichbar“, „nicht deklariert“ oder „Graph unvollständig“ einmal nach 30 s
wiederholen.

**Weiter mit Teil B nur, wenn alles zutrifft.** Sonst: Stack beenden,
berichten, Ende. Den Stack in jedem Fall geordnet beenden:

```bash
source ~/roboter_worktrees/kif1.env; kill -INT "$(cat "$SH_PR/stand/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

---

## Teil B – die Etappen

### Ablauf je Stufe (für N = 1 und 2 gleich)

In allen Blöcken dieses Abschnitts steht `N=1`; für Stufe 2 dort `N=2`
einsetzen. Jede Stufe hat ihren eigenen scharfen Stackstart und ihren
eigenen Ordner `stufeN`.

**B-a, Aufbau:** die Anweisung der Stufe stellen (unten), Antworten wörtlich
festhalten. Nach der Motorsperre wird nicht gefragt.

**B-b, Stack scharf starten** (`N` in der ersten Zeile setzen; `source` steht
in einer eigenen Zeile):

```bash
source ~/roboter_worktrees/kif1.env
N=1; D="$SH_PR/stufe$N"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  stage_drive_only:=true \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif1.env; N=1; D="$SH_PR/stufe$N"
grep -n "Anfahrverhalten bestaetigt" "$D/launch.log" | tee "$D/anfahrzeit.txt"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung.txt"
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`;
`Boolean value is: True` (Etappenfahrt) und `False` (Rundblick); Prüfskript
Exit 0 wie in KI-1. **Trifft etwas davon nicht zu (nach einer Wiederholung
bei „erreichbar“, „nicht deklariert“, „Graph unvollständig“): keine Mission,
Stack geordnet beenden, berichten.**

**Motorregler antworten nicht (einzige Ausnahme):** Fehlt die Zeile zur
Anfahrzeit und steht im Log „Modbus-Fehler Motor … No response received“,
den Stack geordnet beenden und Christopher den Befund in einem Satz melden:
„Die Motorregler antworten nicht; so kann ich nicht starten.“ Sagt er
daraufhin, die Motoren seien frei, ist **genau ein** weiterer scharfer Start
dieser Stufe erlaubt. Den Not-Aus löst nur Christopher.

**B-c, Mission starten und Fahrziel senden.** Genau einmal die Mission, dann
das Werkzeug der Stufe; es wartet, bis der Erkunder wartet, sendet das Ziel
und zeigt dessen Meldungen bis zum Ende:

```bash
source ~/roboter_worktrees/kif1.env; N=1; D="$SH_PR/stufe$N"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
<Werkzeugzeile der Stufe> 2>&1 | tee "$D/werkzeug.txt"; echo "rc=${PIPESTATUS[0]}"
```

Meldet das Werkzeug „Nichts gesendet“ oder „Der Erkunder wartet nicht“:
genau einmal den Stopp senden, dann weiter mit B-e und berichten:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
```

**Christopher drückt den Not-Aus (oder den Stopp in der App), bevor etwas
berührt wird:** wenn eine Ecke näher als zwei Finger breit an etwas
herankommt, wenn Amadeus anders fährt als angekündigt (rückwärts, im Bogen,
deutlich schneller als eine Handbreit in der Sekunde), bei ungewöhnlichem
Geräusch oder starkem Schwanken. Kurzes Stehenbleiben zwischen den Etappen ist gewollt.

**B-d, sichern** (Amadeus bleibt stehen, der Stack läuft noch):

```bash
source ~/roboter_worktrees/kif1.env; N=1; D="$SH_PR/stufe$N"
date -Iseconds > "$D/ende.txt"
grep -n "Etappenfahrt\|Fahrziel" "$D/launch.log" | tee "$D/etappen.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
```

Dazu aus den Sekundenzeilen von `base_hardware` im `launch.log`, wie im
Bericht zu KI-1: größtes |v| und größtes |w| zwischen Missionsstart und
Ende. Dann **die Fragen der Stufe** an Christopher (als Text, einzeln).

**B-e, Stack geordnet beenden:**

```bash
source ~/roboter_worktrees/kif1.env; N=1; kill -INT "$(cat "$SH_PR/stufe$N/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Danach die Kriterien der Stufe gegen `etappen.txt`, `zaehler.txt` und
Christophers Antworten halten. **Stufe 2 folgt nur, wenn alle Kriterien von
Stufe 1 zutreffen.**

### Stufe 1 – eine gerade Etappe von 0,5 m (N=1)

Anweisung an Christopher: „Bitte stelle Amadeus im Laborraum so hin, dass
**geradeaus vor ihm mindestens 1,5 m frei** sind (bis zur nächsten Wand
höchstens 6 m) und seitlich je 0,5 m; nichts Loses am Boden. Klebe ein Stück
Klebeband an den Boden, genau unter die Vorderkante. Gleich fährt er
**einmal einen halben Meter geradeaus, langsam (5 cm in der Sekunde), und
bleibt stehen.** Du stehst seitlich oder hinter ihm, nie vor ihm, mit der
Hand am Not-Aus.“ Frage: „Steht Amadeus so, und bleibt er während des Starts
(etwa eine Minute) unberührt?“

Werkzeugzeile:

```bash
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --geradeaus 0.5 --quelle test --warten 120 --beobachten 300
```

Fragen danach:

1. Ist Amadeus gerade gefahren und von selbst stehen geblieben?
2. Wie weit ist die Vorderkante jetzt vom Klebeband entfernt (Maßband, in cm)?
3. Hat er etwas berührt, oder musstest du eingreifen?
4. Wie wirkte die Fahrt: ruhig, ruckelig, zu langsam, zu schnell?

### Stufe 2 – durch die offene Labortür, in einem Zug (N=2)

Eine Mission: Amadeus fährt bis vor die Tür, richtet sich dort auf die
Türachse aus, fährt hindurch und bleibt im Flur stehen.

Anweisung: „Bitte stelle Amadeus **1,5 bis 2 m vor die offene Labortür**,
den Blick ungefähr zur Tür; die Tür steht ganz offen und ist gesichert, das
Türblatt ragt nicht in den Durchgang. Auf der geraden Linie zur Tür, im
Umkreis von einem Meter vor der Tür und in der Tür liegt und steht nichts.
Gleich fährt er in kurzen Etappen bis vor die Tür, richtet sich aus, fährt
hindurch und bleibt etwa einen halben Meter dahinter im Flur stehen; das
dauert etwa zwei Minuten. Du stehst seitlich im Laborraum, nicht in der Tür
und nicht im Flur vor ihm.“ Fragen, je einzeln:

1. Steht Amadeus so, und bleibt er während des Starts unberührt?
2. Wie weit ist es von der Türschwelle geradeaus bis zum ersten Hindernis im
   Flur (Wand, Regal, Schuhe), in cm?

**Sind es weniger als 115 cm, entfällt Stufe 2** (der Auslauf braucht Platz);
berichten.

Nach B-b (Stack scharf, Vorprüfung bestanden) und **vor** dem Missionsstart
messen:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/stufe2"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen 2>&1 | tee "$D/messen.txt"
```

Christopher die Zeilen der Tabelle in Worten nennen (Nummer, Breite,
Richtung links oder rechts, Entfernung) und fragen: „Welche Nummer ist die
Labortür?“ Ist keine Zeile die Tür, ist die genannte nicht „befahrbar ja“
oder nicht 0,70 bis 0,90 m breit: **keine Mission**, weiter mit B-e,
berichten. Sonst die Richtung dieser Zeile (Zahl mit Vorzeichen, ohne
Gradzeichen) als `R` einsetzen.

Werkzeugzeile:

```bash
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --richtung R --richtung-toleranz 10 --hinter 0.50 --quelle mensch --warten 120 --beobachten 600
```

Fragen danach:

1. Steht Amadeus ganz im Flur, auch mit der Hinterkante?
2. Wie viel Platz blieb an den Türpfosten, links und rechts (etwa in cm)?
3. Hat er etwas berührt, oder musstest du eingreifen?
4. Ist er zwischendurch länger stehen geblieben, und wo?

Nach B-e stellt Christopher Amadeus von Hand zurück.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei Berührung, bei einer anderen Bewegung als
  angekündigt, bei ungewöhnlichem Geräusch, starkem Schwanken oder Rauch.
  Danach nichts mehr starten; nur berichten.
- Endet eine Etappenfahrt mit einer Fehlermeldung („Etappenfahrt: …
  fehlgeschlagen“, „… angehalten“, „… nicht frei“, „kein gueltiges
  Fahrziel“): nicht wiederholen, B-d und B-e, berichten.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um eine Stufe „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif1.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen:

1. Stand (HEAD), Build (rc, Dauer, die Zähler und die fünf Vergleiche),
   Tests.
2. Teil A: die Zeilen aus `schalter.txt`, die `FEHL`-Zeilen des Prüfskripts
   oder der Satz „keine“, der Inhalt von `messen.txt`.
3. Je Stufe: Christophers Antworten zum Aufbau wörtlich; Anfahrzeit,
   Schalter, Vorprüfung; der Inhalt von `werkzeug.txt`, `etappen.txt` und
   `zaehler.txt`; größtes |v| und |w| an der Basis; Christophers Antworten
   nach der Fahrt wörtlich; in Stufe 2 zusätzlich `messen.txt` und die
   benannte Nummer.
4. Die Tabelle der Kriterien mit dem Gemessenen und „trifft zu“ oder „trifft
   nicht zu“; ist Stufe 2 nicht gefahren, „nicht gefahren“ mit Grund.
5. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
