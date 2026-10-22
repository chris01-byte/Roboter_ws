# Aktueller Agentenauftrag: SH-2 – motorlose Nachmessung (VL53-Grenze, HWT601-Weg)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 16.10.2026 nach
Entscheidung 7 des Projektinhabers: Im Selbstheilungsbetrieb zählt jetzt jeder
gültige VL53-Treffer. Die Grenze in beiden Kostenkarten und im
`collision_monitor` liegt bei −0,02 m über `base_link` (0,07 m über Boden)
statt 0,05 m (0,14 m über Boden). Umgesetzt in Commit `5c285c0`. Das Prüfskript
zählt seit `ae780e7` zusätzlich belegte Kostenkartenzellen vor dem Roboter.

**Ergänzt am 22.10.2026 (Entscheidung 8):** Die Laborfahrten laufen mit
HWT601-Odometrie, wie die abgenommenen HWT-Fahrten vom 10./11.09.2026 auf den
Fliesen des Labors. SH-1 hat nur den Standardweg geprüft. SH-2 startet deshalb
den **HWT-Weg** (`use_hwt601_odometry:=true`) und prüft ihn motorlos mit
(`--odometrie hwt601`, seit `06b8a6c`). Der HWT-Start verlangt eine bestätigte
reale Stillstandsbeobachtung (Schritt 6).

SH-2 wiederholt den bestandenen Ablauf SH-1 v3 mit dem neuen Stand. Der
SH-1-Auftrag ist [archiviert](archive/20261016-sh1-bestanden/README.md); dort
stehen alle Einzelheiten, die hier nur verkürzt wiederholt werden. Vorher
lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md`
§6 und §9.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen vom 15./16.10.2026 |
| WE-Bezug | WE-M0 und WE-M3; Vorbedingung für Abnahmestufe 1 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `06b8a6c`. SH-1 v3 bestanden mit `f295a85` (Release `selbstheilung-sh1-20261015_2326`, Standardweg) |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh2.md`: Build, 149 gezielte Tests, App-Stack im HWT-Weg, Prüfskript A–D mit den neuen Overlays und `--odometrie hwt601`, dieselbe VL53-Messreihe wie SH-1 v3 mit Kostenkartenzählung |
| Nicht-Ziele | wie SH-1: keine Fahrt, keine Korrektur, keine eigene Parameteränderung |
| Rückfall | neuen Release nicht sourcen; SH-1-Release, `~/roboter_ws` und alle bisherigen Releases bleiben unverändert |
| Laborrahmen | LAB-1, motorloser Pfad nach §3 (`active_drive=false`); keine Standardfreigabefragen |

## Verboten

Unverändert aus SH-1:
- keine Fahrfreigabe, Missionen, Ziele oder `operator_stationary_confirmed`;
- nur lesende `ros2`-Befehle;
- nichts in `~/roboter_ws` und an der defekten Codex-Referenz;
- bestehende Releases und der v1-Ordner bleiben, wie sie sind;
- keine Code- oder Parameteränderungen, kein Commit oder Push;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht.

## Ablauf

Jeder ROS-Befehl beginnt mit `source ~/roboter_worktrees/selbstheilung-v2.env`.

### Schritt 1 – Bestand

```bash
date -Iseconds
git -C ~/roboter_ws rev-parse HEAD; git -C ~/roboter_ws status --short | head -5
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
printenv ROS_DOMAIN_ID RMW_IMPLEMENTATION CYCLONEDDS_URI
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.

### Schritt 2 – Klon aktualisieren, neuer Release-Ordner

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor 06b8a6c HEAD && echo "06b8a6c enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh2-$STAMP/pruefung
```

### Schritt 3 – Umgebungsdatei

In `~/roboter_worktrees/selbstheilung-v2.env` mit dem Datei-Werkzeug nur die
Zeile `export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/selbstheilung-sh2-<STAMP>`
ändern. Die Unterbauzeilen bleiben wie in SH-1 v3. Prüfen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "rc=$?"; echo "$SH_SRC $SH_REL"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
```

Erwartung: `rc=0`, Zähler `0`.

### Schritt 4 – Build (wie SH-1 v3)

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && cd "$SH_SRC" && \
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

Danach wie in SH-1 v3 prüfen: `Found behaviortree_cpp` unter native-install,
alle 14 Präfixe unter `$SH_REL/product-install` (`prefixes.txt`). Zusätzlich:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  ls "$SH_REL/product-install/vl53_near_field/share/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml" && \
  grep -n "min_obstacle_height" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"
```

Bei Build-Fehler oder fehlendem Präfix entfallen die Schritte 5–8.

### Schritt 5 – gezielte Tests

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && cd "$SH_SRC" && \
env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider \
  src/explore/test/test_self_healing.py \
  src/explore/test/test_self_healing_runtime.py \
  src/explore/test/test_metric_float32_lattice.py \
  src/explore/test/test_metric_selection_retry.py \
  src/explore/test/test_metric_map_lifecycle.py \
  src/robot_navigation/test/test_nav_real_contract.py \
  src/robot_bringup/test/test_semantic_map_launch_contract.py \
  src/vl53_near_field/test/test_mapping_collision_contract.py \
  tools/kartierung/test_selbstheilung_stillstand_pruefen.py \
  2>&1 | tee "$SH_PR/tests.log" | tail -40
```

Erwartung: `149 passed` (Cloud). Fehlschläge berichten, nicht beheben.

### Schritt 6 – App-Stack motorlos im HWT-Weg starten

`source` steht in einer eigenen Zeile (SH-1-Befund):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE
```

Beide Geräte müssen vorhanden sein. Fehlt `/dev/ttyUSB_HWT601`: abbrechen und
berichten; nicht auf den Standardweg ausweichen.

Der HWT misst sich beim Start im Stillstand ein. Deshalb Christopher genau
einmal fragen: „Steht Amadeus still, und kann er während des Starts (etwa eine
Minute) unberührt bleiben?“ Nur nach einem „ja“ starten. Die Antwort ist eine
Beobachtung von Christopher und wird im Bericht so gekennzeichnet.

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  > "$SH_PR/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/launch.pid"; cat "$SH_PR/launch.pid"; date -Iseconds > "$SH_PR/launch_start.txt"
```

`active_drive` und `enable_auto_explore` bleiben auf ihrem Standard `false`.
Die PID muss die des `ros2 launch`-Prozesses sein (mit `ps -o pid,cmd -p <PID>`
kontrollieren). Nach etwa 60 s (HWT-Einmessung) wie in SH-1 v3 `nodes.txt`,
`lifecycle.txt` und die `grep`-Zeilen aus `launch.log` erfassen, zusätzlich:

```bash
grep -niE "hwt|bias|ekf|encoder_shadow" "$SH_PR/launch.log" | head -60
```

### Schritt 7 – Prüfskript A–D

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 \
  --json "$SH_PR/pruefung_AD.json" 2>&1 | tee "$SH_PR/pruefung_AD.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartung: Exit 0. Neu in Bereich C: `Explorer erwartet hwt601` und
`genau ein /odom-Publisher (/hwt601_mapping_ekf)`. Neu in Bereich B: vier Zeilen
`…costmap obstacle_layer.vl53_*_mark.min_obstacle_height` mit −0.02 und zwei
Zeilen `B Kollisionswaechter … min_height` mit −0.02. Bei `FEHL` mit
„erreichbar“ oder „nicht deklariert“ einmal nach 30 s wiederholen.

### Schritt 8 – VL53-Messreihe (braucht Christopher)

**Dieselben Objekte wie in SH-1 v3**, damit die Läufe vergleichbar sind.
Christopher legt, der Agent sagt je Lage einmal an und wartet auf „liegt“.
Danach steht niemand vor dem Roboter. Objekte mittig, Abstand von der
Fahrzeugfront bis zur Vorderkante.

| Nr | Objekt (wie SH-1 v3) | Abstand ab Front |
|---|---|---|
| 0 | kein Objekt, mindestens 1 m frei | – |
| 1 | 3 cm | 0,30 m |
| 2 | 5,5 cm | 0,30 m |
| 3 | 10 cm | 0,30 m |
| 4 | 15 cm | 0,30 m |
| 5 | 3 cm | 0,38 m |
| 6 | 6,5 cm | 0,38 m |
| 7 | 10 cm | 0,38 m |
| 8 | 15,5 cm | 0,38 m |

Je Messung:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 \
  --beobachten-s 1 --vl53-s 10 --notiz "Nr 2: 5,5 cm, 0,30 m" \
  --json "$SH_PR/vl53_02.json" 2>&1 | tee "$SH_PR/vl53_02.txt"
```

Erwartung (zu prüfen, nicht vorwegnehmen): ähnliche Trefferzahlen wie in
SH-1 v3; `filter_ueber_boden_m` 0,07; `verworfen` 0, weil kein gültiger Punkt
unter 0,084 m liegen kann; 3 cm weiterhin 0 Treffer.

Die neue Zeile „lokale Kostenkarte: N belegte Zellen vor dem Roboter“ zeigt,
ob die Treffer als Hindernis eingetragen werden. Ohne Räumstrahl bleiben
Markierungen früherer Lagen bestehen; die Zahl kann also von Lage zu Lage nur
wachsen. Entscheidend ist der Sprung von Nr 1 (0 erwartet) zu Nr 2.

### Schritt 9 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
PID=$(cat "$SH_PR/launch.pid"); kill -INT "$PID"; for i in $(seq 1 30); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done
kill -0 "$PID" 2>/dev/null && echo "LAUNCH LAEUFT NOCH" || echo "Launch beendet nach ${i}s"
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

SIGINT nur an die Launch-PID. Nach 30 s noch aktiv: einmal `kill -TERM`, 15 s
warten, übrige eigene Knoten einzeln per PID mit SIGINT beenden und auflisten.

### Abbruchregeln

Sofort Schritt 9 und dann Bericht bei:
- Rad- oder Motorbewegung;
- `FEHL` in „D Stillstand“;
- Not-Aus oder einem „Stopp“ von Christopher;
- einem zweiten Robotik-Stack;
- einem HWT-Endfehler im Log (`TERMINAL_FAULT`) oder fehlendem HWT-Gerät.
  Nicht auf den Standardweg ausweichen; berichten.

## Bericht: `~/selbstheilung_jetson_bericht_sh2.md`

Gliederung wie SH-1 v3. Kopf, Bestand, Umgebungsdatei, Build mit
`prefixes.txt` und den zwei Overlay-Zeilen aus Schritt 4, Tests,
Stackstart im HWT-Weg (Geräte, Christophers Stillstandsantwort, Wartezeit,
HWT-/EKF-Logzeilen), Prüfung A–D vollständig mit Exitcode. Dann die VL53-Tabelle mit
einer **zusätzlichen Spalte „Kostenkarte belegt vorn“** und dem `vl53`-Teil
jeder JSON-Datei wörtlich. Danach Beenden, Auffälligkeiten (insbesondere
`collision_monitor`-Warnungen „Ignoring the source“ mit Zeitraum) und nicht
Ausgeführtes. Am Ende im Chat nur: Pfad, Ergebnis A–D, Testfehlschläge, ob der
HWT-Weg lief, ob die Reihe vollständig ist und ob die Kostenkarte ab Nr 2
Zellen einträgt.

## Danach

Auswertung in der Cloud-Sitzung. Bei bestandenem SH-2 folgt Abnahmestufe 1
(drei begrenzte Laborfahrten nach LAB-1) als eigener Auftrag.
