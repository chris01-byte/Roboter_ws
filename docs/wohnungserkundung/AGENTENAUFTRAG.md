# Aktueller Agentenauftrag: SH-5 – Bestätigung der einfachen Version (SH-3 plus SL-1, drei Laborfahrten)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 04.11.2026.
Entscheidung des Projektinhabers: zurück zur einfachen, in SH-3 bewährten
Software. Gegenüber SH-3 ändert sich nur eines, alles nur im
Selbstheilungsbetrieb:

- **SL-1 (`c20436a`, in SH-4 am Jetson abgenommen):** SLAM legt erst nach
  0,25 m Fahrt oder 0,35 rad Drehung einen neuen Graphknoten an (vorher
  0,01 m / 0,15 rad). Die SLAM-Last sank in SH-4 von 61–81 % auf 6–12 % eines
  Kerns.

Die in SH-4 gefahrenen DR-1-Änderungen am Fahrverhalten sind **zurückgenommen**
(`037c41a`): Mit ihnen verweigerte Amadeus jede Drehung, sobald etwas näher
als etwa 45 cm war, und rief zweimal Hilfe, obwohl Platz war. Neu ist nur in
der Vorprüfung: Sie meldet jetzt auch nicht bereite Fahrquellen (Encoder,
HWT-Fusion), wie im ersten Versuch von Fahrt 3 in SH-4.

SH-5 baut den Stand, prüft ihn und fährt dreimal im **selben Laborraum wie
SH-4, mit denselben Gegenständen** (Mülleimer, Bücherregal). Gemessen wird,
ob die einfache Version dort ohne Berührung und ohne unnötigen Hilferuf
durchkommt und die SLAM-Last niedrig bleibt.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md`
§5, §9 und §11, im STATUS die Abschnitte zu SH-3, SH-4 und zum Kurswechsel
vom 04.11.2026. SH-3 und SH-4 sind archiviert
([SH-3](archive/20261102-sh3-bestanden/README.md),
[SH-4](archive/20261104-sh4-ausgewertet/README.md)).

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 04.11.2026 |
| WE-Bezug | WE-M3, Bestätigung des Selbstheilungsbetriebs mit SL-1 (Vorbedingung Stufe 3) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `037c41a`; neuer Release `selbstheilung-sh5-<STAMP>`. SH-3 bestanden mit `selbstheilung-sh2-20261102_1107`, SH-4 mit `selbstheilung-sh4-20261103_1738` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh5.md`: Build, 171 gezielte Tests, drei Fahrten wie SH-3/SH-4, Kriterien C1–C5 und G1 |
| Nicht-Ziele | keine eigene Code- oder Parameteränderung, kein anderer Raum, keine Wohnungsfahrt, kein Arm |
| Rückfall | in der Umgebungsdatei `SH_REL` auf `…/selbstheilung-sh2-20261102_1107` zurückstellen; alle Releases bleiben |
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

- **Vorwärts:** höchstens 0,12 m/s; 0,06 m/s, solange vor ihm nicht kartiert ist.
- **Drehen:** höchstens 0,25 rad/s.
- **Rückwärts:** nur entlang der eigenen Spur, höchstens 0,4 m, 0,05 m/s.
- Er wählt seine Ziele selbst (Frontiers) und heilt Fehlschläge selbst:
  1. erneut versuchen;
  2. Ziel zurückstellen;
  3. umsehen;
  4. ein Stück zurück entlang der Spur;
  5. „Hilfe benötigt“.
- Eine Fahrt endet von selbst mit „vollständig“, „Teilkarte“ oder „Hilfe
  benötigt“, spätestens nach 20 Minuten (Explorer-Gesamtbudget).
- **Kurzes Stehenbleiben ist normal:** Setzen die VL53 einige Sekunden aus
  (in SH-1 und SH-2 je einmal 6–7 s), sperrt das Fahrtor nach 0,8 s, und der
  Explorer wartet bis zu 30 s, bevor er Hilfe ruft. Das ist kein Eingriffsgrund.

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
  git rev-parse HEAD && git merge-base --is-ancestor 037c41a HEAD && echo "037c41a enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh5-$STAMP/pruefung
```

### Schritt 2 – Umgebungsdatei

In `~/roboter_worktrees/selbstheilung-v2.env` mit dem Datei-Werkzeug nur die
Zeile `export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/selbstheilung-sh5-<STAMP>`
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
  grep -nE "self_healing_goal_shift_max_m|self_healing_track_lateral_tolerance_m|self_healing_blocked_track_backs" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"
```

Erwartet: Zähler `0`; `self_healing_goal_shift_max_m: 0.5` und
`self_healing_track_lateral_tolerance_m: 0.03`, **keine** Zeile
`self_healing_blocked_track_backs`.
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

Erwartung: `171 passed` (Cloud, Stand `037c41a`). Bei Fehlschlägen nicht fahren,
berichten.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern: „Bitte die Türen des Laborraums
schließen, sodass Amadeus den Raum nicht verlassen kann.“ Der Selbstheilungs-
betrieb kennt keinen Software-Fahrbereich; den Raum begrenzen Wände und
geschlossene Türen. Ohne geschlossenen Raum keine Fahrt.

Außerdem einmal: „Bitte flache Gegenstände unter etwa 15 cm Höhe (Kabel,
Kartons, Schuhe) vom Boden räumen. Die Mülleimer und das Bücherregal bleiben
bitte so stehen wie in SH-4.“ Grund: Unter etwa 6 cm sehen die VL53
nichts (SH-2), und von höheren niedrigen Gegenständen nur die Vorderkante;
liegt so ein Gegenstand neben dem Roboter, kann die Flanke ihn beim Drehen
berühren (bekannte Grenze, Entscheidung 22.10.2026). Höhere Möbel und Wände
sieht der LiDAR.

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
mkdir -p "$SH_PR/sh5_run$RUN"
```

Fehlt ein Gerät: nicht fahren, berichten. Christopher einmal fragen: „Steht
Amadeus an seinem Startplatz still, mit etwa 0,5 m Platz rundherum, und bleibt
er während des Starts (etwa eine Minute) unberührt?“ Nur nach „ja“ weiter. Der
Startplatz darf je Fahrt wechseln; ihn im Bericht beschreiben lassen.

### 2. Stack scharf starten

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/sh5_run$RUN/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh5_run$RUN/launch.pid"; cat "$SH_PR/sh5_run$RUN/launch.pid"
date -Iseconds > "$SH_PR/sh5_run$RUN/launch_start.txt"
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
  --json "$SH_PR/sh5_run$RUN/vorpruefung.json" 2>&1 | tee "$SH_PR/sh5_run$RUN/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0, Bereiche A–C wie in SH-3, aber `B SLAM-Overlay` mit
**sechs** Zeilen: zusätzlich `minimum_travel_distance` 0.25 und
`minimum_travel_heading` 0.35. **Keine** `B Nav2-Overlay`-Zeile zu
`/controller_server` (die DR-1-Werte sind zurückgenommen). In D
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
  --json "$SH_PR/sh5_run$RUN/protokoll.json" \
  > "$SH_PR/sh5_run$RUN/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh5_run$RUN/protokoll.pid"
```

Nur lesend, nebenher die Rechenlast von `slam_toolbox` alle 10 s mitschreiben
(SH-3: sie stieg in 20 min auf 85–95 % eines Kerns; Kriterium C2). `-x` vergleicht den Prozessnamen exakt und
trifft daher nicht die eigene Shell:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
SLAM_PID=$(pgrep -x async_slam_tool | head -1); echo "SLAM_PID=$SLAM_PID"
echo "$SLAM_PID" > "$SH_PR/sh5_run$RUN/slam.pid"
nohup top -b -d 10 -p "$SLAM_PID" > "$SH_PR/sh5_run$RUN/slam_cpu.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh5_run$RUN/slam_cpu.pid"
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
cat "$SH_PR/sh5_run$RUN/protokoll.txt" | tail -60
for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
  echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$SH_PR/sh5_run$RUN/lifecycle_nach.txt"
grep -c "process has died" "$SH_PR/sh5_run$RUN/launch.log"
grep -nE "Ignoring the source|TERMINAL_FAULT|ERROR|FATAL" "$SH_PR/sh5_run$RUN/launch.log" | head -40
for m in "extrapolation into the future" "Unable to transform robot pose" "missed its desired rate" "detected collision ahead" "queue is full"; do \
  echo "$m: $(grep -c "$m" "$SH_PR/sh5_run$RUN/launch.log")"; done | tee "$SH_PR/sh5_run$RUN/zeitfehler.txt"
kill -TERM "$(cat "$SH_PR/sh5_run$RUN/slam_cpu.pid")"
grep -E "^ *$(cat "$SH_PR/sh5_run$RUN/slam.pid") " "$SH_PR/sh5_run$RUN/slam_cpu.txt" | awk '{print $9}' | tr '\n' ' ' | tee "$SH_PR/sh5_run$RUN/slam_cpu_reihe.txt"
ros2 run nav2_map_server map_saver_cli -f "$SH_PR/sh5_run$RUN/karte"
```

Christopher dann einmal fragen und die Antworten wörtlich festhalten:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Sieht die Karte sauber aus, ohne doppelte oder verdrehte Wände?
4. Auch dort, wo sich Amadeus auf der Stelle gedreht hat?
5. Nur wenn die Fahrt mit „Hilfe benötigt“ endete: Wo stand er, was stand
   daneben, und hätte er nach deiner Einschätzung ausweichen können, wohin?

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
  - Verlassen des Laborraums;
  - ungewöhnlichem Geräusch;
  - Rauch.

  Danach keine weitere Fahrt in dieser Sitzung; nur berichten.
- **Endet eine Fahrt mit `outcome=error`:** die Serie anhalten und berichten.
  Keine identischen Fehlversuche aneinanderreihen.
- **Ungültige Fahrt:** Ist eine Fahrt aus einem äußeren Grund ungültig (zum
  Beispiel kommt jemand in den Raum) oder fuhr Amadeus wegen einer nicht
  bereiten Fahrquelle gar nicht los, darf sie einmal wiederholt werden.
  Höchstens vier Starts je Sitzung.
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bewertung (Bestätigung der einfachen Version)

Die Kriterien stehen vor der ersten Fahrt fest (STATUS, Abschnitt 04.11.2026,
Kurswechsel). Je Fahrt:

| Nr | Kriterium | Quelle |
|---|---|---|
| C1 | Stufe 1 wie in SH-3: `automatisch_erfuellt: true`, kein Kontakt, kein Eingriff, Nav2 danach klar, kein „process has died“ vor dem Stopp | Protokoll, Christopher, Schritt 7 |
| C2 | `slam_toolbox` im Mittel der letzten sechs Werte (letzte Minute) ≤ 50 % eines Kerns | `slam_cpu_reihe.txt` |
| C3 | höchstens 10× „queue is full“ | `zeitfehler.txt` |
| C4 | höchstens 40× „extrapolation into the future“ | `zeitfehler.txt` |
| C5 | Karte sauber, auch an Drehstellen | Christophers Antworten 3 und 4 |
| G1 | kein Ende mit „Hilfe benötigt“ an einer Stelle, an der Christopher Platz zum Ausweichen sieht | Christophers Antwort 5 |

Die einfache Version ist bestätigt, wenn alle drei Fahrten C1–C5 und G1
erfüllen. Die Fahrzeit wird gemessen, ist aber kein Kriterium.

## Bericht: `~/selbstheilung_jetson_bericht_sh5.md`

1. Kopf: Datum, Release, HEAD, Ergebnis der Schritte 0–4 (Build-Dauer,
   Präfixe, Overlay-Zeilen, Testergebnis), Raum und Türen (Christophers Angabe).
2. Je Fahrt wie in SH-3: Startplatz, Knotenlisten, Vorprüfung (Exit, B
   SLAM-Overlay, C/D), Fahrtprotokoll ohne `ereignisse` und die gekürzte
   Ereignisliste, Lifecycle danach, „process has died“, Warnungen,
   `zeitfehler.txt` und `slam_cpu_reihe.txt` vollständig, Christophers
   Antworten wörtlich.
3. Tabelle über alle Fahrten wie in SH-3, zusätzlich je Fahrt C1–C5 und G1
   mit Wert und erfüllt/nicht erfüllt, daneben die Werte aus SH-3 und SH-4
   zum Vergleich.
4. Gesamturteil: einfache Version bestätigt / nicht bestätigt, mit Grund.
   Bei „Hilfe benötigt“: Ort, was danebenstand, wohin Christopher ausweichen
   würde, und die letzten Heilungsaktionen.
5. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad, Zahl der Fahrten,
C1–C5 und G1 je Fahrt, Gesamturteil, Kontakte oder Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Erst mit bestätigter einfacher Version wird
über Stufe 3 (Wohnung) gesprochen; die Entscheidung trifft der Projektinhaber.
