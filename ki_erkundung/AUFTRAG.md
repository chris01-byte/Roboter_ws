# Aktueller Auftrag der KI-Linie: KI-1 – Blickrunde aus eigener Kraft

**Erteilt am 21.11.2026 (spät).** Er wird aktiv, sobald der Projektinhaber
ihn übergibt. Er läuft auf dem **Jetson**, mit Christopher. Auf dem
KI-Rechner muss das Programm „Amadeus Lotse“ offen sein.

**Zum ersten Mal in dieser Linie bewegt sich Amadeus:** Er dreht sich im
Laborraum einmal auf der Stelle um sich selbst (acht Schritte von 45° mit
kurzem Halt, etwa anderthalb Minuten) und bleibt stehen. Er fährt nicht.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](archiv/20261121-ki0-erstes-sehen/),
[KI-0N](archiv/20261121-ki0n-nachmessen/),
[KI-0R](archiv/20261121-ki0r-nachrechnen/).

**Frage dieses Auftrags:** Dreht sich Amadeus mit dem neuen Schalter „nur
Rundblick“ einmal ganz herum und bleibt stehen, läuft die Kamera dabei neben
dem Kartier-Stack, und entsteht daraus eine Blickrunde mit acht Bildern, zu
der die KI antwortet?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md` (v1.4 oder neuer), Stufe KI-1 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält; neuer Release `ki1-<STAMP>`. Der letzte real gelaufene Release ist `selbstheilung-sh9-20261119_1932` |
| Was neu ist | Genau eine Verhaltensänderung: Startargument `initial_scan_only:=true` (Erkunder dreht einmal abschnittsweise und endet, ohne ein Ziel anzufahren). Dazu als Mitläufer: Kamera und Aufnahmewerkzeug (lesen nur). Der Stand enthält seit dem 21.11. (nachts) außerdem die zweite Anschlussstelle `stage_drive_only` („Etappenfahrt“); sie bleibt in diesem Auftrag **aus** und wird nicht gesetzt |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_ki1.md`: Build, Tests, Prüfung im Stand, eine Drehung mit den Kriterien R1 bis R6, die Blickrunde mit Prüftext, die Antwort der KI, Christophers Antworten wörtlich |
| Nicht-Ziele | Keine Fahrt, kein Ziel, keine Tür; keine eigene Code- oder Parameteränderung; keine Drehung außerhalb des Laborraums; kein zweiter Versuch nach einer Berührung |
| Rückfall | `~/roboter_worktrees/ki1.env` und den Release-Ordner `ki1-<STAMP>` löschen; die Umgebungsdatei der Hauptlinie und alle bisherigen Releases bleiben unberührt. Ohne das Startargument verhält sich der Stack wie am 19.11. |
| Bereich und Freigabe | **Nur der Laborraum** (LAB-1). Der Projektinhaber hat die Änderung am Erkunder am 21.11.2026 freigegeben; mit der Übergabe dieses Auftrags gibt er die eine Drehung im Laborraum frei. Christopher ist dabei, die Hand am Not-Aus. 100 ms Anfahrzeit wie seit dem 15.11. |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3;
- schreibend nur: die zwei Stackstarts, **genau ein** Missionsstart und
  höchstens **ein** Missionsstopp; kein `param set`, `lifecycle set`,
  `service call`, kein weiteres `topic pub`, keine Nav2-Ziele;
- **kein Missionsstart, wenn `initial_scan_only` nicht nachweislich `True`
  ist** (B2). Ohne den Schalter würde Amadeus losfahren;
- `stage_drive_only` wird in diesem Auftrag nie gesetzt und muss `False`
  melden; `fahrziel_senden.py` wird nicht benutzt;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`; der Start im Stand (Teil A) hat keine
  Motorfreigabe und braucht das Argument nicht;
  `operator_stationary_confirmed:=true` nur nach Christophers „ja“;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an `~/roboter_worktrees/selbstheilung-v2.env`
  und an bestehenden Releases;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- **kein eigenes Anzeigeprogramm, nichts im Vollbild.** Blätter zeigt der
  vorhandene Bildbetrachter in einem gewöhnlichen Fenster
  (`nohup env --default-signal=INT eog DATEI &`); das Live-Bild zeigt
  `werkzeuge/sucher.py`;
- kein Bild, keine Scan-Datei und keine Karte in den Chat oder in den
  Bericht; keine IP-Adressen.

## Vorab festgelegte Kriterien

| Kennung | Kriterium | Woran gemessen |
|---|---|---|
| R1 Drehung | Der Erkunder meldet 350° bis 370° und „Nur Rundblick abgeschlossen“ | Statusmeldung, `launch.log` |
| R2 Kein Fahren | Kein Nav2-Ziel; Amadeus steht nach der Drehung höchstens 10 cm neben dem Startpunkt | `Begin navigating` 0-mal; `tf2_echo map base_link` vorher und nachher; Christopher |
| R3 Dauer | Von „Nur Rundblick: kontrollierter 360-Grad-Rundblick“ bis „Nur Rundblick abgeschlossen“ höchstens 150 s (in der Simulation 77 s) | Zeitstempel der beiden Zeilen in `launch.log` |
| R4 Blickrunde | Mindestens 100 Paare aus Bild und Scan; aus den Scans 350° bis 370° gedreht; acht Bilder gefunden, jedes höchstens 12° neben seinem Sollwinkel | Ausgabe von `trockenlauf.py`, `ergebnis.json` |
| R5 Kamera neben dem Stack | Bilder mindestens 1,8 Hz, Scans mindestens 9 Hz, auch während der Drehung; keine Fehlerzeilen im Kamera-Log | Raten, Logs |
| R6 Antwort | Die KI antwortet gültig auf die Frage mit neun Bildern, in höchstens 45 s | Ausgabe von `trockenlauf.py` |

Zur Wahl der KI und zur Vermessung der Öffnungen gibt es keine Erwartung;
beides wird berichtet. Trifft ein Kriterium nicht zu, ist das ein Befund und
wird berichtet, nicht nachgebessert.

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
mkdir -p ~/.local/share/amadeus/releases/ki1-$STAMP/pruefung
```

### Schritt 2 – eigene Umgebungsdatei (die der Hauptlinie bleibt unberührt)

```bash
cp ~/roboter_worktrees/selbstheilung-v2.env ~/roboter_worktrees/ki1.env
```

In `~/roboter_worktrees/ki1.env` mit dem Datei-Werkzeug nur die Zeile
`export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/ki1-<STAMP>`
ändern. Prüfen:

```bash
source ~/roboter_worktrees/ki1.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
diff ~/roboter_worktrees/selbstheilung-v2.env ~/roboter_worktrees/ki1.env
```

Erwartung: `rc=0`, Zähler `0`, `diff` zeigt genau die eine Zeile. **Jeder
ROS-Befehl für den Stack beginnt ab hier mit `source ~/roboter_worktrees/ki1.env`.**

### Schritt 3 – Build (wie am 19.11.)

```bash
source ~/roboter_worktrees/ki1.env && cd "$SH_SRC" && \
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

Danach prüfen, dass der Schalter eingebaut ist und sich sonst nichts
gegenüber dem Release vom 19.11. geändert hat:

```bash
source ~/roboter_worktrees/ki1.env; I="$SH_REL/product-install"; ALT=~/.local/share/amadeus/releases/selbstheilung-sh9-20261119_1932/product-install
ls "$I" | wc -l
grep -c initial_scan_only "$(find "$I/explore" -name explore_node.py | head -1)" \
  "$I/explore/share/explore/launch/explore.launch.py" \
  "$I/robot_navigation/share/robot_navigation/launch/nav_mapping.launch.py" \
  "$I/robot_bringup/share/robot_bringup/launch/app_mapping.launch.py"
for f in explore/share/explore/config/self_healing_params.yaml explore/share/explore/config/explore_params.yaml \
  robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml \
  vl53_near_field/share/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml \
  amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml; do \
  diff -q "$I/$f" "$ALT/$f" && echo "gleich: $f"; done
```

Erwartet: die Zähler `11`, `3`, `3`, `2`; fünfmal `gleich: …`. Jede
Abweichung, Build-Fehler oder fehlendes Paket: nichts starten, berichten.

### Schritt 4 – gezielte Tests

```bash
source ~/roboter_worktrees/ki1.env && cd "$SH_SRC" && \
env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider \
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

Erwartung: `267 passed` (die 249 vom 19.11. und 18 neue) und für die
KI-Linie `226 passed`. Bei Fehlschlägen nichts starten, berichten.

---

## Teil A – Prüfung im Stand (Motoren aus)

Der Stack startet **ohne** `active_drive` und ohne `enable_auto_explore`;
die Basis wird nicht bestromt, es kann nichts fahren (LAB-1 §3).

### A1 – Stack ohne Motorfreigabe starten

Christopher einmal fragen: „Steht Amadeus im Laborraum still, und bleibt er
während des Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/ki1.env
D="$SH_PR/stand"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  initial_scan_only:=true \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 70 s:

```bash
source ~/roboter_worktrees/ki1.env; D="$SH_PR/stand"
ros2 param get /explore_node initial_scan_only 2>&1 | tee "$D/schalter.txt"
ros2 param get /explore_node stage_drive_only 2>&1 | tee -a "$D/schalter.txt"
ros2 param get /explore_node exploration_strategy 2>&1 | tee -a "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 \
  --json "$D/pruefung.json" > "$D/pruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/pruefung.txt"
```

Erwartet: `Boolean value is: True` (Rundblick), `Boolean value is: False`
(Etappenfahrt), `String value is: self_healing`,
Prüfskript Exit 0 mit denselben Zeilen wie am 19.11. ohne `--aktiv`
(„kein Motorschreiber (HWT-Weg ohne active_drive)“). Bei `FEHL` mit
„erreichbar“, „nicht deklariert“ oder „Graph unvollständig“ einmal nach 30 s
wiederholen. **Ist `initial_scan_only` nicht `True`, ist `stage_drive_only`
nicht `False` oder bleibt ein `FEHL`: Stack geordnet beenden, berichten,
Teil B entfällt.**

### A2 – Kamera dazu, Last und Raten messen

In einer **zweiten Shell** (die Kamera kommt wie in KI-0 aus der
WE-1-Umgebung; das LiDAR startet der Stack selbst, es wird hier **nicht**
gestartet):

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_ki1; mkdir -p "$KI"          # nach dem source: die Datei setzt KI selbst
timeout 15 ros2 topic echo --once --full-length /ki_erkundung/lotse_status_json > "$KI/lotse_status.txt" 2>&1; cat "$KI/lotse_status.txt"
nohup env --default-signal=INT ros2 launch robot_bringup oak.launch.py pointcloud:=false \
  > "$KI/oak_stand.log" 2>&1 < /dev/null & echo $! > "$KI/oak.pid"
sleep 25
timeout -s INT 30 ros2 topic hz /oak/semantic/rgb/compressed > "$KI/rate_bild_stand.txt" 2>&1; tail -2 "$KI/rate_bild_stand.txt"
timeout -s INT 30 ros2 topic hz /scan > "$KI/rate_scan_stand.txt" 2>&1; tail -2 "$KI/rate_scan_stand.txt"
timeout -s INT 30 ros2 topic hz /odom > "$KI/rate_odom_stand.txt" 2>&1; tail -2 "$KI/rate_odom_stand.txt"
top -b -n 1 | head -18 > "$KI/top_stand.txt"; cat "$KI/top_stand.txt"
timeout 8 ros2 run tf2_ros tf2_echo base_link oak_rgb_camera_optical_frame > "$KI/tf_kamera.txt" 2>&1; tail -6 "$KI/tf_kamera.txt"
grep -ciE "error|TF_REPEATED|multiple authority" "$KI/oak_stand.log"
```

Dann in der ersten Shell noch einmal das Prüfskript aus A1 (Ausgabe nach
`pruefung_mit_kamera.txt`); es muss weiter Exit 0 liefern.

Kommt kein Status des Lotsen-Dienstes (`"bereit": true`): Christopher
bitten, auf dem KI-Rechner „Amadeus Lotse“ zu öffnen. Teil A und die Drehung
laufen auch ohne ihn; nur B7 braucht ihn. Der KI-Rechner darf auf dem Stand
vom 21.11. bleiben; sein Fenster zeigt die neue Einordnung „wand“ dann als
„unklar“, die Antwort an den Roboter ist davon nicht berührt.

### A3 – eine Aufnahme im Stand mit laufendem Stack

In der zweiten Shell:

```bash
cd ~/roboter_worktrees/selbstheilung-v2
python3 ki_erkundung/werkzeuge/blickrunde_aufnehmen.py --name ki1_stand --dauer 8 > "$KI/ki1_stand_aufnahme.txt" 2>&1; cat "$KI/ki1_stand_aufnahme.txt"
R=~/.local/share/amadeus/ki_erkundung/blickrunden
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$(ls -d $R/ki1_stand_* | tail -1)" --bericht "$KI/pruefung_stand.md" > /dev/null; head -20 "$KI/pruefung_stand.md"
```

Erwartet: etwa 16 Aufnahmen, „ohne Scan verworfen: 0“.

### A4 – Entscheidung

**Weiter mit Teil B nur, wenn alles zutrifft:** Schalter `True`; Prüfskript
zweimal Exit 0; Bilder mindestens 1,8 Hz, Scans mindestens 9 Hz; keine
Fehlerzeile im Kamera-Log; die Aufnahme im Stand ohne verworfene Paare.
Sonst: Kamera und Stack beenden (wie B6), berichten, Ende.

Kamera und Stack für Teil B geordnet beenden (der Stack muss mit
Motorfreigabe neu starten):

```bash
kill -INT "$(cat ~/ki_trockenlauf_ki1/oak.pid)"; sleep 5
source ~/roboter_worktrees/ki1.env; kill -INT "$(cat "$SH_PR/stand/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

---

## Teil B – die Drehung

### B1 – Aufbau (Christopher)

Nur diese Handlung einmal anfordern, Antworten wörtlich festhalten:

„Bitte stelle Amadeus im Laborraum so hin, dass **rundherum mindestens
0,5 m frei** sind und nichts Loses am Boden liegt. Die Labortür ist offen.
Niemand sonst ist im Raum. Gleich dreht er sich **auf der Stelle einmal
linksherum**, in acht Schritten mit kurzem Halt, etwa anderthalb Minuten,
und bleibt dann stehen. **Er soll nicht fahren.** Du stehst mit der Hand am
Not-Aus dabei, möglichst die ganze Zeit an derselben Stelle.“

1. Steht Amadeus so, ist rundherum 0,5 m frei, und bleibt er während des
   Starts (etwa eine Minute) unberührt?
2. Wo stehst du während der Drehung (zum Beispiel „rechts hinter ihm, 1 m“)?

Nur nach „ja“ auf Frage 1 weiter.

### B2 – Stack scharf starten

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/ki1.env
D="$SH_PR/drehung"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  initial_scan_only:=true \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/ki1.env; D="$SH_PR/drehung"
grep -n "Anfahrverhalten bestaetigt" "$D/launch.log" | tee "$D/anfahrzeit.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee "$D/schalter.txt"
ros2 param get /explore_node stage_drive_only 2>&1 | tee -a "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung.txt"
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`;
`Boolean value is: True` (Rundblick) und `Boolean value is: False`
(Etappenfahrt); Prüfskript Exit 0 wie am 19.11. **Ist `initial_scan_only`
nicht `True`, ist `stage_drive_only` nicht `False`, fehlt die Anfahrzeit-Zeile
oder bleibt ein `FEHL`
(nach einer Wiederholung bei „erreichbar“, „nicht deklariert“, „Graph
unvollständig“): keine Mission, Stack geordnet beenden, berichten.**

### B3 – Kamera und Aufnahme starten

Zweite Shell:

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_ki1; cd ~/roboter_worktrees/selbstheilung-v2
nohup env --default-signal=INT ros2 launch robot_bringup oak.launch.py pointcloud:=false \
  > "$KI/oak_drehung.log" 2>&1 < /dev/null & echo $! > "$KI/oak.pid"
sleep 25
timeout -s INT 15 ros2 topic hz /oak/semantic/rgb/compressed > "$KI/rate_bild_vor.txt" 2>&1; tail -2 "$KI/rate_bild_vor.txt"
nohup env --default-signal=INT python3 ki_erkundung/werkzeuge/blickrunde_aufnehmen.py \
  --name labor_rundblick_1 --dauer 240 > "$KI/labor_rundblick_1_aufnahme.txt" 2>&1 < /dev/null & echo $! > "$KI/aufnahme.pid"
sleep 3; cat "$KI/labor_rundblick_1_aufnahme.txt"
```

Kommen keine Bilder (Rate unter 1,8 Hz): keine Mission; Aufnahme, Kamera und
Stack beenden, berichten.

### B4 – Mission starten und beobachten

Erste Shell. Lage vorher festhalten, dann **genau einmal** senden:

```bash
source ~/roboter_worktrees/ki1.env; D="$SH_PR/drehung"
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$D/tf_vorher.txt" 2>&1; tail -5 "$D/tf_vorher.txt"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
```

Etwa alle 20 s (nur lesend):

```bash
source ~/roboter_worktrees/ki1.env; D="$SH_PR/drehung"
echo "seit Missionsstart: $(( $(date +%s) - $(date -d "$(cat "$D/missionsstart.txt")" +%s) )) s"
timeout 5 ros2 topic echo --once --full-length /explore/status_json 2>&1 | grep -oE '"(state|phase|message)": "[^"]*"' | head -3
```

Die Mission endet von selbst; die Meldung lautet dann „Nur Rundblick
abgeschlossen: … Grad gedreht; kein Ziel angefahren“. **Läuft sie nach
240 s noch**, sendet der Agent genau einmal den Stopp und hält ihn fest:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
date -Iseconds > "$D/missionsstopp.txt"
```

**Christopher drückt den Not-Aus (oder den Stopp in der App), bevor etwas
berührt wird:** wenn Amadeus **fährt** (vor oder zurück, auch nur ein
kurzes Stück), wenn eine Ecke beim Drehen näher als zwei Finger breit an
etwas herankommt, bei ungewöhnlichem Geräusch oder starkem Schwanken.
Kurzes Stehenbleiben zwischen den Schritten ist gewollt.

### B5 – nach der Drehung sichern (der Stack läuft noch)

```bash
source ~/roboter_worktrees/ki1.env; D="$SH_PR/drehung"
date -Iseconds > "$D/missionsende.txt"
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$D/tf_nachher.txt" 2>&1; tail -5 "$D/tf_nachher.txt"
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$D/explore_status_ende.txt" 2>&1
for m in "Nur Rundblick" "Begin navigating" "Goal succeeded" "detected collision ahead" "Robot to approach" "Transform data too old" "queue is full" "process has died" "Odometrie kurzzeitig nicht frisch"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
grep -n "Nur Rundblick" "$D/launch.log" | tail -4
```

Zweite Shell: Aufnahme beenden, Raten während der Drehung stehen im
Aufnahmeprotokoll:

```bash
KI=~/ki_trockenlauf_ki1
kill -INT "$(cat "$KI/aufnahme.pid")"; sleep 4; tail -5 "$KI/labor_rundblick_1_aufnahme.txt"
grep -ciE "error" "$KI/oak_drehung.log"
```

Christopher fragen, je einzeln, Antworten wörtlich:

1. Hat sich Amadeus einmal ganz herumgedreht? In wie vielen Schritten?
2. Ist er dabei von der Stelle gefahren oder gewandert? Wie weit etwa?
3. Hat er etwas berührt, oder musstest du eingreifen?
4. Wie wirkte die Drehung: ruhig, ruckelig, zu schnell, zu langsam? Hat der
   Aufbau geschwankt?

### B6 – Kamera und Stack geordnet beenden

```bash
kill -INT "$(cat ~/ki_trockenlauf_ki1/oak.pid)"; sleep 5
source ~/roboter_worktrees/ki1.env; kill -INT "$(cat "$SH_PR/drehung/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Meldet der LiDAR-Treiber beim Beenden `buffer overflow detected`, die Zeile
berichten; das ist bekannt.

### B7 – Blickrunde auswerten und die KI fragen

Zweite Shell (WE-1-Umgebung, `KI` gesetzt wie oben):

```bash
cd ~/roboter_worktrees/selbstheilung-v2; R=~/.local/share/amadeus/ki_erkundung/blickrunden
RUNDE=$(ls -d $R/labor_rundblick_1_* | tail -1); echo "$RUNDE"
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$RUNDE" --alle --bericht "$KI/pruefung_rundblick.md" > /dev/null; wc -l "$KI/pruefung_rundblick.md"
SECONDS=0; python3 ki_erkundung/werkzeuge/trockenlauf.py --runden "$RUNDE" --ausgabe "$KI/rundblick" \
  --ueber-ros --denken aus --zeitgrenze 120 > "$KI/rundblick.txt" 2>&1; echo "dauer_s=$SECONDS"; cat "$KI/rundblick.txt"
python3 -c "import json,sys; r=json.load(open(sys.argv[1]))['runden'][0]; print({k: r[k] for k in ('vollstaendig','gedreht_grad','drehsinn','guete_min','vermessen_von')}); [print(b) for b in r['bilder']]" "$KI/rundblick/ergebnis.json"
```

Dann Christopher das Blatt `$KI/rundblick/labor_rundblick_1/uebersicht.jpg`
in einem gewöhnlichen Fenster zeigen (acht Fotos und die Skizze) und die
Antwort der KI nennen. Fragen, je einzeln, Antworten wörtlich:

1. Welche Nummern sind echte, offene Ausgänge, durch die Amadeus fahren könnte?
2. Was ist jede Nummer wirklich (offene Tür, geschlossene Tür, Durchgang, Glas, Spiegel, Lücke an Möbeln, Nische, Wand)?
3. Gibt es von hier einen offenen Ausgang, der keine Nummer bekommen hat?
4. Steht die Nummer der Tür in den Fotos auf der Türschwelle, oder daneben (wo)?
5. Bist du selbst auf einem Foto oder als Nummer in der Skizze zu sehen? Wo?
6. In welchem Raum steht Amadeus?

Eintragen und auswerten:

```bash
python3 ki_erkundung/werkzeuge/wahrheit_eintragen.py --ergebnis "$KI/rundblick/ergebnis.json" --runden "$RUNDE" \
  --name labor_rundblick_1 --ausgaenge <Nummern> --arten <NR=ART …> --raum Labor \
  --ausgang-ohne-nummer <ja|nein> --bemerkung "<Christophers Worte zu Frage 4 und 5>"
python3 ki_erkundung/werkzeuge/trockenlauf_auswerten.py --ergebnis "$KI/rundblick/ergebnis.json" \
  --runden "$RUNDE" --bericht "$KI/auswertung_rundblick.md" > /dev/null; cat "$KI/auswertung_rundblick.md"
```

### B8 – Ende

Nach der einen Drehung ist der Auftrag beendet. **Keine zweite Drehung**,
auch wenn die erste abgebrochen wurde; berichten.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei Berührung, bei jeder Fahrt statt Drehung, bei
  ungewöhnlichem Geräusch, starkem Schwanken oder Rauch. Danach nichts mehr
  starten; nur berichten.
- Endet die Drehung mit einer Fehlermeldung („Nur Rundblick fehlgeschlagen:
  …“): nicht wiederholen, berichten.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um die Drehung „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_ki1.md`, ohne Bilder, Scans, Karten und
Adressen:

1. Stand (HEAD), Build (rc, Dauer, die Zähler und die fünf Vergleiche),
   Tests.
2. Teil A: Schalter, Ausgabe des Prüfskripts (die Zeilen mit `FEHL` oder
   der Satz „keine“), Raten, die `top`-Zeilen, TF der Kamera, Zeilen des
   Aufnahmewerkzeugs, der Prüftext der Aufnahme im Stand.
3. Teil B: Christophers Antworten zum Aufbau; Anfahrzeit, Schalter,
   Vorprüfung; Zeitstempel von Missionsstart und -ende; die Statuszeilen
   während der Drehung; die Zähler; die Zeilen „Nur Rundblick …“ aus dem
   Log; Lage vorher und nachher (nur der Abstand in Metern und der
   Drehwinkel, keine Koordinaten); Christophers Antworten zur Drehung.
4. Die Tabelle R1 bis R6 mit dem Gemessenen und „trifft zu“ oder „trifft
   nicht zu“.
5. Der ganze Text aus `pruefung_rundblick.md`, der Inhalt von
   `rundblick.txt`, die Zeile mit `vollstaendig`/`gedreht_grad` und die acht
   Bildzeilen, die Begründung der KI, Christophers Antworten zum Blatt, der
   Text aus `auswertung_rundblick.md`.
6. Alles, was nicht lief, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
