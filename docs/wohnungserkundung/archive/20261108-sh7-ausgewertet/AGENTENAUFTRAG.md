# Aktueller Agentenauftrag: SH-7 – Raumwechsel: Laborraum plus Nachbarraum durch eine offene Tür (drei Fahrten)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 05.11.2026.
Grundlage ist der in SH-6 bestätigte Stand (SH-3-Software, SLAM-Korrektur
SL-1, Regel „kein Fortschritt → zurück“ `e8f00f6`); dieser Stand ist als
**Prototyp 1 eingefroren** (Release `selbstheilung-sh6-20261104_2140`, bleibt
unverändert). Neu sind zwei Einstellungen, nur im Selbstheilungsbetrieb:

- **`c444bca`, Entscheidung des Projektinhabers 04.11.2026:** Gesamtbudget je
  Mission **40 statt 20 Minuten**.
- **`adbb39f`, Entscheidung des Projektinhabers 05.11.2026:** **vorwärts
  35 % schneller, Drehen 25 % schneller** (Regler 0,10 → 0,135 m/s und
  0,20 → 0,25 rad/s, Obergrenzen 0,12 → 0,162 m/s und 0,25 → 0,3125 rad/s,
  vor Unbekanntem 0,06 → 0,08 m/s, Umsehen 0,08 → 0,10 rad/s).
  Kollisionsmonitor, Motorrampen, Antriebsgrenzen und Rückfahrt (0,05 m/s)
  bleiben unverändert.

Heilungsleiter und Hilfe-Grenzen bleiben unverändert.

Neu ist vor allem der **Aufbau**: Laborraum und ein Nachbarraum, verbunden
durch **genau eine offene Tür ohne Schwelle, lichte Breite mindestens
75 cm**; alle anderen Türen beider Räume sind zu. Amadeus kennt keine Räume.
Hinter der offenen Tür ist alles unbekannt, die Türöffnung ist für ihn eine
Lücke in der Karte wie jede andere. Er fährt hindurch, sobald sie das
günstigste Ziel ist, auch bevor der Laborraum fertig ist, und kann
zurückkommen. Gemessen wird, ob er selbstständig, ohne Berührung, durch die
Tür in den Nachbarraum fährt, ihn kartiert und beide Räume in der Karte
sauber zusammenpassen.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md`
§5, §9 und §11, im STATUS die Abschnitte 05.11.2026 (SH-6) und 04.11.2026
(spät) zum Weg zu mehreren Räumen. Frühere Aufträge sind archiviert
([SH-6](archive/20261105-sh6-ausgewertet/README.md),
[SH-5](archive/20261104-sh5-ausgewertet/README.md)).

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 04.11.2026 |
| WE-Bezug | WE-M3, metrischer Kern im Zwei-Raum-Umfang; Vorstufe zu WE-M4 (Drei-Bereich-Rundweg), keine Abnahme von WE-M4; Vorbedingung Stufe 3 (Wohnung) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `adbb39f`; neuer Release `selbstheilung-sh7-<STAMP>`. SH-6 lief mit `selbstheilung-sh6-20261104_2140` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh7.md`: Build, 172 gezielte Tests, drei Fahrten durch zwei Räume, Kriterien C1–C5, G1, R1 und R2 |
| Nicht-Ziele | keine eigene Code- oder Parameteränderung, kein dritter Raum, keine Wohnungsfahrt, keine Tür mit Schwelle, kein Arm |
| Rückfall | in der Umgebungsdatei `SH_REL` auf `…/selbstheilung-sh6-20261104_2140` zurückstellen; alle Releases bleiben |
| Laborrahmen | LAB-1: aktive Fahrt im beauftragten Umfang ohne erneute Standardfreigaben. Not-Aus-Erreichbarkeit, freier Fahrbereich und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden **nicht** erneut abgefragt |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3;
- schreibend nur: der Stackstart je Fahrt und, falls die App fehlt, **genau
  ein** Missionsstart je Fahrt; kein `param set`, `lifecycle set`,
  `service call`, kein weiteres `topic pub`, keine Nav2-Ziele;
- `operator_stationary_confirmed:=true` nur nach Christophers „ja“;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws` und an der defekten Codex-Referenz; bestehende
  Releases, der v1-Ordner und frühere Berichte bleiben, wie sie sind;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht.

## Was Amadeus in diesen Fahrten tut

- **Er kennt keine Räume.** Er wählt jeweils die günstigste Lücke in der Karte
  (nah und groß); die offene Tür ist eine davon.
- **Vorwärts (neu):** Regler 0,135 m/s, höchstens 0,162 m/s; 0,08 m/s,
  solange vor ihm nicht kartiert ist (also auch beim ersten Durchfahren der
  Tür).
- **Drehen (neu):** Regler 0,25 rad/s, höchstens 0,3125 rad/s.
- **Rückwärts:** nur entlang der eigenen Spur, höchstens 0,4 m, 0,05 m/s.
- Er wählt seine Ziele selbst (Frontiers) und heilt Fehlschläge selbst:
  1. erneut versuchen;
  2. Ziel zurückstellen;
  3. umsehen;
  4. ein Stück zurück entlang der Spur (seit SH-6: kommt er in einem Anlauf
     nicht vom Fleck, sofort, dann dasselbe Ziel erneut);
  5. „Hilfe benötigt“.
- Eine Fahrt endet von selbst mit „vollständig“, „Teilkarte“ oder „Hilfe
  benötigt“, spätestens nach **40 Minuten** (Explorer-Gesamtbudget, neu).
- **Kurzes Stehenbleiben ist normal:** Setzen die VL53 einige Sekunden aus
  (in SH-6 bis zu 11,7 s), sperrt das Fahrtor nach 0,8 s, und der
  Explorer wartet bis zu 30 s, bevor er Hilfe ruft. Das ist kein Eingriffsgrund.
  Auch Abbremsen oder kurzes Halten in der Tür ist normal (Kollisionsmonitor).

## Einmal je Sitzung

Jeder ROS-Befehl beginnt mit `source ~/roboter_worktrees/selbstheilung-v2.env`.

### Schritt 0 – Bestand

```bash
date -Iseconds
git -C ~/roboter_ws rev-parse HEAD; git -C ~/roboter_ws status --short | head -5
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.

### Schritt 1 – Klon aktualisieren, neuer Release-Ordner

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor adbb39f HEAD && echo "adbb39f enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh7-$STAMP/pruefung
```

### Schritt 2 – Umgebungsdatei

In `~/roboter_worktrees/selbstheilung-v2.env` mit dem Datei-Werkzeug nur die
Zeile `export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/selbstheilung-sh7-<STAMP>`
ändern. Die Unterbauzeilen bleiben. Prüfen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "rc=$?"; echo "$SH_SRC $SH_REL"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
```

Erwartung: `rc=0`, Zähler `0`.

### Schritt 3 – Build (wie SH-2)

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

Danach wie in SH-2 prüfen: `Found behaviortree_cpp` unter native-install, alle
14 Präfixe unter `$SH_REL/product-install` (`prefixes.txt`). Zusätzlich:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  grep -n "minimum_travel" "$SH_REL/product-install/amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml"
```

Erwartet: `minimum_travel_distance: 0.25` und `minimum_travel_heading: 0.35`.
Dass die DR-1-Änderungen wirklich zurückgenommen sind:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  grep -cE "max_allowed_time_to_collision_up_to_carrot|xy_goal_tolerance" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  grep -nE "desired_linear_vel|rotate_to_heading_angular_vel|max_velocity|min_velocity" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  grep -nE "self_healing_goal_shift_max_m|self_healing_track_lateral_tolerance_m|self_healing_blocked_track_backs|self_healing_stuck_move_m|overall_timeout_s|self_healing_unknown_speed_mps|initial_scan_angular_speed_radps" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"
```

Erwartet: Zähler `0`; Tempo `desired_linear_vel: 0.135`,
`rotate_to_heading_angular_vel: 0.25`, `max_velocity: [0.162, 0.0, 0.3125]`,
`min_velocity: [-0.05, 0.0, -0.3125]`; im Explorer-Profil
`self_healing_unknown_speed_mps: 0.08`, `initial_scan_angular_speed_radps: 0.10`,
`self_healing_goal_shift_max_m: 0.5`,
`self_healing_track_lateral_tolerance_m: 0.03`,
`self_healing_stuck_move_m: 0.05` und **neu** `overall_timeout_s: 2400.0`;
**keine** Zeile `self_healing_blocked_track_backs`.
Bei Build-Fehler oder fehlendem Präfix: nicht fahren, berichten.

### Schritt 4 – gezielte Tests

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

Erwartung: `172 passed` (Cloud, Stand `adbb39f`). Bei Fehlschlägen nicht fahren,
berichten.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern und die Antworten wörtlich
festhalten:

„Bitte für SH-7 aufbauen:
1. Genau **eine** Tür zwischen dem Laborraum und einem Nachbarraum ganz
   öffnen: Türblatt bis zum Anschlag und gegen Zufallen gesichert (zum
   Beispiel Türstopper), **keine Schwelle**. Bitte die lichte Breite messen
   und nennen (mindestens 75 cm).
2. Alle anderen Türen **beider** Räume schließen, sodass Amadeus nur diese
   zwei Räume erreichen kann.
3. In **beiden** Räumen flache Gegenstände unter etwa 15 cm Höhe (Kabel,
   Kartons, Schuhe) vom Boden räumen, auch im Türbereich. Mülleimer und
   Bücherregal im Laborraum dürfen stehen bleiben.
4. Kurz sagen, was der Nachbarraum ist (zum Beispiel Flur, Küche) und wie
   groß er ungefähr ist.“

Grund: Der Selbstheilungsbetrieb kennt keinen Software-Fahrbereich; den
Bereich begrenzen Wände und geschlossene Türen. Unter etwa 6 cm sehen die
VL53 nichts (SH-2), von höheren niedrigen Gegenständen nur die Vorderkante;
liegt so ein Gegenstand neben dem Roboter, kann die Flanke ihn beim Drehen
berühren (bekannte Grenze, Entscheidung 22.10.2026). Ein halb offenes
Türblatt ist für den LiDAR eine schmale Kante und für die Flanke ein Risiko.

Ist die offene Tür schmaler als 75 cm, hat sie eine Schwelle oder lässt sie
sich nicht feststellen: keine Fahrt, berichten. Ohne geschlossene übrige
Türen keine Fahrt.

Geht die Serie an einem anderen Tag weiter, den Aufbau dann einmal erneut
bestätigen lassen (Punkte 1–3, „unverändert“ genügt).

## Je Fahrt (Nr 1, 2, 3)

Jede Fahrt ist ein Kaltstart mit neuer Karte. `RUN` = 1, 2 oder 3; in jedem
Befehlsblock setzen (`RUN=1 …`), weil die Blöcke nicht zwingend in derselben
Shell laufen.

### 1. Bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE
mkdir -p "$SH_PR/sh7_run$RUN"
```

Fehlt ein Gerät: nicht fahren, berichten. Christopher einmal fragen: „Steht
Amadeus an seinem Startplatz im **Laborraum** still, mindestens 1 m von der
offenen Tür, mit etwa 0,5 m Platz rundherum, und bleibt er während des Starts
(etwa eine Minute) unberührt? Ist der Motor-Stop-Schalter freigegeben, und
reicht der Akku für etwa 45 Minuten Fahrt? Ist die Tür noch offen und
gesichert?“ Nur nach „ja“ weiter. Der Startplatz darf je Fahrt wechseln;
Christopher beschreibt ihn kurz (zum Beispiel „Raummitte, Blick zum
Fenster“). Laden zwischen den Fahrten ist erlaubt; eine Fahrt darf auf einen
anderen Tag fallen.

### 2. Stack scharf starten

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/sh7_run$RUN/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh7_run$RUN/launch.pid"; cat "$SH_PR/sh7_run$RUN/launch.pid"
date -Iseconds > "$SH_PR/sh7_run$RUN/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s (HWT-Einmessung) wie in SH-2 `nodes.txt`, 10 s später
`nodes_2.txt` und `lifecycle.txt` erfassen. Erwartet: `/base_hardware`
vorhanden, `/hwt601_encoder_shadow_reader` **nicht** (mit `active_drive`
startet der Launch nur den Motortreiber).

### 3. Vorprüfung direkt vor der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && RUN=1 && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/sh7_run$RUN/vorpruefung.json" 2>&1 | tee "$SH_PR/sh7_run$RUN/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0, Bereiche A–C wie in SH-3, aber `B SLAM-Overlay` mit
**sechs** Zeilen: zusätzlich `minimum_travel_distance` 0.25 und
`minimum_travel_heading` 0.35. **Neu** genau zwei `B Nav2-Overlay`-Zeilen zu
`/controller_server`: `FollowPath.desired_linear_vel` 0.135 und
`FollowPath.rotate_to_heading_angular_vel` 0.25; zu `/velocity_smoother`
`max_velocity` [0.162, 0.0, 0.3125] und `min_velocity` [-0.05, 0.0, -0.3125];
in A `self_healing_unknown_speed_mps` 0.08 und
`initial_scan_angular_speed_radps` 0.10. In D
`base_hardware scharf (aktiver Auftrag)` mit `dry_run=False, allow_rs485=True`
und `/cmd_vel 3 s ohne Fahrbefehl`. **Neu, Bereich „D Quellen“:** `Encoder
liefern frisch`, `Encoder-Zeitwache bereit` und `HWT-Fusion Quellen bereit`
müssen OK sein; ein `FEHL` dort heißt: Fahrquelle nicht bereit, nicht fahren
(wie im ersten Versuch von Fahrt 3 in SH-4). Dann Stack geordnet beenden und
einmal neu starten; das zählt als Wiederholung.

Bei `FEHL` mit „erreichbar“, „nicht deklariert“ oder „Graph unvollständig“ das
Skript einmal nach 30 s wiederholen; erst die Wiederholung zählt. Jeder andere
`FEHL` und ein `FEHL` nach der Wiederholung: Stack geordnet beenden (wie
SH-2 Schritt 9: SIGINT nur an die Launch-PID) und berichten; keine Fahrt.

### 4. Fahrtprotokoll starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh7_run$RUN/protokoll.json" --max-s 3600 \
  > "$SH_PR/sh7_run$RUN/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh7_run$RUN/protokoll.pid"
```

`--max-s 3600`: Das Protokoll beendet sich sonst nach 30 min, die Fahrt
dauert bis zu 40 min. Nur lesend, nebenher die Rechenlast von `slam_toolbox` alle 10 s mitschreiben
(SH-3: sie stieg in 20 min auf 85–95 % eines Kerns, mit SL-1 in SH-6 auf
10–15 %; Kriterium C2). `-x` vergleicht den Prozessnamen exakt und
trifft daher nicht die eigene Shell:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
SLAM_PID=$(pgrep -x async_slam_tool | head -1); echo "SLAM_PID=$SLAM_PID"
echo "$SLAM_PID" > "$SH_PR/sh7_run$RUN/slam.pid"
nohup top -b -d 10 -p "$SLAM_PID" > "$SH_PR/sh7_run$RUN/slam_cpu.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh7_run$RUN/slam_cpu.pid"
```

### 5. Mission starten

Christopher drückt in der App „Erkunden“. Das ist der Produktweg. Steht die App
nicht zur Verfügung, sendet der Agent **genau einmal** denselben Befehl wie die
App:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
```

### 6. Während der Fahrt

- Der Agent greift nicht ein und sendet keine weiteren Befehle.
- Christopher beobachtet und darf jederzeit über die App stoppen oder den
  Not-Aus drücken. Das gilt dann als **Eingriff**.
- Kurzes Stehenbleiben ist kein Eingriffsgrund (siehe oben).
- Die Fahrt endet von selbst; das Protokoll beendet sich wenige Sekunden danach.

### 7. Nach der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
cat "$SH_PR/sh7_run$RUN/protokoll.txt" | tail -60
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$SH_PR/sh7_run$RUN/explore_status_ende.txt" 2>&1
grep -o 'last_track_back[^}]*}' "$SH_PR/sh7_run$RUN/explore_status_ende.txt"
for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
  echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$SH_PR/sh7_run$RUN/lifecycle_nach.txt"
grep -c "process has died" "$SH_PR/sh7_run$RUN/launch.log"
grep -nE "Ignoring the source|TERMINAL_FAULT|ERROR|FATAL" "$SH_PR/sh7_run$RUN/launch.log" | head -40
for m in "extrapolation into the future" "Unable to transform robot pose" "missed its desired rate" "detected collision ahead" "queue is full"; do \
  echo "$m: $(grep -c "$m" "$SH_PR/sh7_run$RUN/launch.log")"; done | tee "$SH_PR/sh7_run$RUN/zeitfehler.txt"
kill -TERM "$(cat "$SH_PR/sh7_run$RUN/slam_cpu.pid")"
grep -E "^ *$(cat "$SH_PR/sh7_run$RUN/slam.pid") " "$SH_PR/sh7_run$RUN/slam_cpu.txt" | awk '{print $9}' | tr '\n' ' ' | tee "$SH_PR/sh7_run$RUN/slam_cpu_reihe.txt"
ros2 run nav2_map_server map_saver_cli -f "$SH_PR/sh7_run$RUN/karte"
```

Christopher dann einmal fragen und die Antworten wörtlich festhalten:

1. Hat Amadeus etwas berührt, auch Türrahmen oder Türblatt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Sieht die Karte sauber aus, ohne doppelte oder verdrehte Wände?
4. Auch dort, wo sich Amadeus auf der Stelle gedreht hat, und an der Tür:
   Passen beide Räume aneinander, liegt die Türöffnung an der richtigen
   Stelle?
5. Ist Amadeus selbst durch die Tür in den Nachbarraum gefahren? Wann
   ungefähr zum ersten Mal, und wie oft insgesamt hindurch?
6. Ist der Nachbarraum in der Karte zu erkennen: ganz, größtenteils, nur
   teilweise oder gar nicht?
7. Nur wenn die Fahrt mit „Hilfe benötigt“ endete: Wo stand er (welcher
   Raum, in der Tür?), was stand daneben, und hätte er nach deiner
   Einschätzung ausweichen können, wohin?
8. Zum neuen Tempo: Hat er vor Hindernissen rechtzeitig und ruhig
   gebremst, und wirkte das Tempo passend (zu langsam, passend, zu schnell)?

Ist die App nicht verfügbar, die gespeicherte Karte (`karte.pgm`) als Bild
zeigen, wie in SH-3.

Danach den Stack geordnet beenden (wie SH-2 Schritt 9: SIGINT nur an die
Launch-PID, `roboterknoten.py` danach leer). Läuft das Protokoll noch, sein
Prozess vorher per SIGINT an `protokoll.pid` beenden.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei:
  - Berührung;
  - Fahrt auf ein Hindernis ohne Abbremsen;
  - Fahrt in einen dritten Raum oder durch eine Tür, die zu sein sollte;
  - Türblatt bewegt sich oder Tür fällt zu, während Amadeus in der Nähe ist
    (Fahrt ungültig, darf nach erneutem Sichern einmal wiederholt werden);
  - ungewöhnlichem Geräusch;
  - Rauch.

  Danach keine weitere Fahrt in dieser Sitzung; nur berichten.
- **Endet eine Fahrt mit `outcome=error`:** die Serie anhalten und berichten.
  Keine identischen Fehlversuche aneinanderreihen.
- **Ungültige Fahrt:** Ist eine Fahrt aus einem äußeren Grund ungültig (zum
  Beispiel kommt jemand in den Raum), darf sie einmal wiederholt werden.
  Höchstens vier Starts mit Mission je Sitzung. Ein Start, den die
  Vorprüfung in „D Quellen“ vor der Mission abfängt (keine Bewegung), zählt
  nicht mit; höchstens sechs Starts insgesamt.
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bewertung (Raumwechsel)

Die Kriterien stehen vor der ersten Fahrt fest. C1–C5 und G1 wie in SH-6;
C3 und C4 sind für die doppelte Fahrzeit verdoppelt (gleiche Rate wie
bisher). Neu sind R1 und R2. Je Fahrt:

| Nr | Kriterium | Quelle |
|---|---|---|
| C1 | Stufe 1 wie in SH-3: `automatisch_erfuellt: true`, kein Kontakt (auch nicht mit Türrahmen oder Türblatt), kein Eingriff, Nav2 danach klar, kein „process has died“ vor dem Stopp | Protokoll, Christopher, Schritt 7 |
| C2 | `slam_toolbox` im Mittel der letzten sechs Werte (letzte Minute) ≤ 50 % eines Kerns | `slam_cpu_reihe.txt` |
| C3 | höchstens 20× „queue is full“ | `zeitfehler.txt` |
| C4 | höchstens 80× „extrapolation into the future“ | `zeitfehler.txt` |
| C5 | Karte sauber, auch an Drehstellen und an der Tür (beide Räume passen aneinander) | Christophers Antworten 3 und 4 |
| G1 | kein Ende mit „Hilfe benötigt“ an einer Stelle, an der Christopher Platz zum Ausweichen sieht | Christophers Antwort 7 |
| R1 | Amadeus fährt selbstständig durch die offene Tür in den Nachbarraum | Christophers Antwort 5 |
| R2 | Der Nachbarraum ist in der Karte ganz oder größtenteils zu erkennen | Christophers Antwort 6 |

Christophers Antwort 8 zum Tempo ist eine Beobachtung, kein Kriterium; ein
„zu spät gebremst“ ist dagegen ein Abbruchgrund (Fahrt auf ein Hindernis
ohne Abbremsen).

Der Raumwechsel ist bestätigt, wenn alle drei Fahrten C1–C5, G1, R1 und R2
erfüllen. Fahrzeit, Ende („vollständig“ oder „Teilkarte“) und Zahl der
Durchfahrten werden gemessen, sind aber keine Kriterien.

## Bericht: `~/selbstheilung_jetson_bericht_sh7.md`

1. Kopf: Datum, Release, HEAD, Ergebnis der Schritte 0–4 (Build-Dauer,
   Präfixe, Overlay-Zeilen, Testergebnis), Aufbau mit Christophers
   Antworten wörtlich: lichte Breite der offenen Tür, Art und ungefähre
   Größe des Nachbarraums, übrige Türen zu.
2. Je Fahrt wie in SH-3: Startplatz, Knotenlisten, Vorprüfung (Exit, B
   SLAM-Overlay, C/D), Fahrtprotokoll ohne `ereignisse` und die gekürzte
   Ereignisliste, Heilungsverlauf, Lifecycle danach, „process has died“, Warnungen,
   `zeitfehler.txt` und `slam_cpu_reihe.txt` vollständig, Christophers
   Antworten wörtlich.
3. Tabelle über alle Fahrten wie in SH-6, zusätzlich je Fahrt C1–C5, G1,
   R1 und R2 mit Wert und erfüllt/nicht erfüllt, daneben die Werte aus SH-6
   zum Vergleich (C1–C5, G1).
4. Gesamturteil: Raumwechsel bestätigt / nicht bestätigt, mit Grund.
   Bei „Hilfe benötigt“: Ort, was danebenstand, wohin Christopher ausweichen
   würde, und die letzten Heilungsaktionen.
   Je Fahrt: erste Durchfahrt (Christophers Zeitangabe) und Zahl der
   erreichten Ziele davor und danach (aus den `selbstheilung`-Ereignissen),
   Zahl der Durchfahrten. Ziele, die in der Tür oder direkt davor
   scheiterten, mit Heilungsaktion und Navigatorzeilen aus `launch.log`.
   Wie in SH-6 je Fahrt: Zahl der Spur-Rückfahrten und für jede: wann, wie weit
   (Zeitpunkte aus den `selbstheilung`-Ereignissen und dem `heilungsverlauf`
   im Protokoll, Weite der letzten aus `explore_status_ende.txt`,
   `last_track_back`), und ob Amadeus danach weiterkam; Christophers Beobachtung dazu, falls er eine
   Rückfahrt gesehen hat.
5. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad, Zahl der Fahrten,
C1–C5, G1, R1 und R2 je Fahrt, Gesamturteil, Kontakte oder Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Mit bestätigtem Raumwechsel folgt Stufe 3
(Wohnung); Umfang und Kriterien legt der Projektinhaber vorher fest.
