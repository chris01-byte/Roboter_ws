# Aktueller Agentenauftrag: SH-8 – Stellprobe „Abstand halten und wegkommen“, bei Erfolg eine volle Zwei-Raum-Fahrt

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 10.11.2026
(ersetzt die Fassung mit drei 40-Minuten-Fahrten, die
[zurückgezogen](archive/20261110-sh8-langfahrten-zurueckgezogen/README.md)
wurde, bevor sie ausgeführt wurde).

**Warum eine Stellprobe** (Entscheidung des Projektinhabers 10.11.2026,
MASTERPLAN §9 Regel 6): Seit dem 04.11. scheitert es an einer Sache: Amadeus
sitzt dicht an Hindernissen fest (Mülleimer, Garderobe, Ecke). Geprüft wurde
das bisher mit langen Fahrten; ob er dabei in die Lage kommt, war Zufall.
Jetzt wird er **gezielt an drei bekannte Stellen gestellt**, die Erkundung
startet, und gemessen wird, ob er sich ohne Berührung befreit und
weiterfährt. Erst wenn das gelingt, folgt eine volle Fahrt durch zwei Räume.

Prüfling ist das Paket **AW-1 plus AW-1b** (`19c8cb9`, `d0d1431`), nur im
Selbstheilungsbetrieb:

1. Wege mit mehr Abstand (globale Kosten neben Hindernissen reichen weiter).
2. Der LiDAR räumt seine eigenen alten Einträge in der lokalen Karte.
3. Die Rückfahrt prüft nur den Bereich hinter dem Heck (Rückfahrkontur,
   Knoten `rueckfahr_kontur`), nicht, was vorn oder seitlich anliegt.
4. Rückfahrt auch ohne gerade eigene Spur: 0,3 m gerade zurück, wenn hinten
   frei ist; höchstens 0,4 m, 0,05 m/s, einmal je Stillstand.
5. Nach einer Rückfahrt ein anderes Ziel statt desselben.

**Erwartetes Verhalten an jeder Stelle:** Der erste Anlauf scheitert (er kann
nicht drehen oder nicht vorwärts), dann setzt Amadeus etwa 0,3 m gerade
zurück, wählt ein anderes Ziel und fährt weg. Das kann zwischen etwa 30 s und
3 min dauern.

Offen und nur **gemessen**, nicht geändert: Liegt ein Hindernis vorn schon
innerhalb der gepolsterten Kontur (etwa 2 cm), setzt der Kollisionsmonitor
jede Bewegung auf null, auch rückwärts (Simulation 09.11.2026). In der
Simulation berührte außerdem das Gehäuse beim langsamen Drehen dicht an einem
Hindernis; real gab es in 15 Laborfahrten keine Berührung. **Deshalb gilt:
jede Berührung beendet den ganzen Auftrag.**

Tempo, Budget (40 min), Heilungsleiter und Hilfe-Grenzen wie in SH-7.
Prototyp 1 (`selbstheilung-sh6-20261104_2140`) und der SH-7-Release bleiben
unverändert.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/MASTERPLAN.md` §9,
`docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md` §5, §9 und §11, im STATUS
die Arbeitsliste und die Abschnitte 10.11.2026, 09.11.2026 (AW-1, AW-1b),
08.11.2026 (SH-7N, SH-7). Frühere Aufträge sind archiviert
([SH-7N](archive/20261108-sh7n-ausgewertet/README.md),
[SH-7](archive/20261108-sh7-ausgewertet/README.md)).

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 10.11.2026; **Fahrplan §9, Schritt 1, Regel 6** |
| WE-Bezug | WE-M3, metrischer Kern im Zwei-Raum-Umfang; Vorstufe zu WE-M4, keine Abnahme von WE-M4; Vorbedingung Stufe 3 (Wohnung) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `2409529`; neuer Release `selbstheilung-sh8-<STAMP>`. SH-7 lief mit `selbstheilung-sh7-20261108_1617` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh8.md`: Build, 182 gezielte Tests, **Teil A** Stellprobe an drei Stellen (je zweimal) mit Urteil je Probe, **Teil B** nur bei bestandener Stellprobe eine volle Zwei-Raum-Fahrt mit C1–C5, G1, R1, R2 |
| Nicht-Ziele | keine eigene Code- oder Parameteränderung, kein dritter Raum, keine Wohnungsfahrt, keine Tür mit Schwelle, kein Arm, kein Vergleich mit älteren Releases |
| Rückfall | in der Umgebungsdatei `SH_REL` auf `…/selbstheilung-sh7-20261108_1617` (SH-7-Stand) oder `…/selbstheilung-sh6-20261104_2140` (Prototyp 1) zurückstellen; alle Releases bleiben |
| Laborrahmen | LAB-1: aktive Fahrt im beauftragten Umfang ohne erneute Standardfreigaben. Not-Aus-Erreichbarkeit und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden **nicht** erneut abgefragt. **Neu und ausdrücklich so entschieden (10.11.2026):** In Teil A steht Amadeus beim Start absichtlich 5 cm vor einem Hindernis |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3;
- schreibend nur: der Stackstart je Probe oder Fahrt, falls die App fehlt
  **genau ein** Missionsstart je Probe oder Fahrt, und in Teil A **genau ein**
  Missionsstopp je Probe (derselbe Befehl wie der Stopp der App, siehe A6);
  kein `param set`, `lifecycle set`, `service call`, kein weiteres
  `topic pub`, keine Nav2-Ziele;
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
- **Rückwärts (erweitert):** entlang der eigenen geraden Spur oder, wenn es
  keine gibt, 0,3 m gerade zurück, sofern hinten frei ist; höchstens 0,4 m,
  0,05 m/s, einmal je Stillstand. Fährt er sich irgendwo fest, soll er sich so
  selbst befreien.
- Er wählt seine Ziele selbst (Frontiers) und heilt Fehlschläge selbst:
  1. erneut versuchen;
  2. Ziel zurückstellen;
  3. umsehen;
  4. ein Stück zurück (kommt er in einem Anlauf nicht vom Fleck, sofort;
     seit SH-8 auch ohne gerade Spur, danach ein anderes Ziel);
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
  git rev-parse HEAD && git merge-base --is-ancestor 2409529 HEAD && echo "2409529 enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh8-$STAMP/pruefung
```

### Schritt 2 – Umgebungsdatei

In `~/roboter_worktrees/selbstheilung-v2.env` mit dem Datei-Werkzeug nur die
Zeile `export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/selbstheilung-sh8-<STAMP>`
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
  grep -nE "desired_linear_vel|rotate_to_heading_angular_vel|max_velocity|min_velocity|footprint_topic|plugins|lidar_layer|clearing|inflation_radius|cost_scaling_factor" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  ls "$SH_REL/product-install/robot_navigation/lib/robot_navigation/rueckfahr_kontur"; \
  grep -nE "self_healing_goal_shift_max_m|self_healing_track_lateral_tolerance_m|self_healing_blocked_track_backs|self_healing_stuck_move_m|overall_timeout_s|self_healing_unknown_speed_mps|initial_scan_angular_speed_radps|self_healing_free_back_m|self_healing_track_back_slow_factor" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"
```

Erwartet: Zähler `0`; Tempo `desired_linear_vel: 0.135`,
`rotate_to_heading_angular_vel: 0.25`, `max_velocity: [0.162, 0.0, 0.3125]`,
`min_velocity: [-0.05, 0.0, -0.3125]`; **neu (AW-1)**
`footprint_topic: rueckfahr_kontur`,
`plugins: ["obstacle_layer", "lidar_layer", "inflation_layer"]`, eine
`lidar_layer` mit `clearing: True`, `inflation_radius: 0.60` und
`cost_scaling_factor: 2.5`, das Programm `rueckfahr_kontur` vorhanden; im
Explorer-Profil **neu** `self_healing_free_back_m: 0.3` und
`self_healing_track_back_slow_factor: 0.3`, dazu wie bisher
`self_healing_unknown_speed_mps: 0.08`, `initial_scan_angular_speed_radps: 0.10`,
`self_healing_goal_shift_max_m: 0.5`,
`self_healing_track_lateral_tolerance_m: 0.03`,
`self_healing_stuck_move_m: 0.05` und `overall_timeout_s: 2400.0`;
**keine** Zeile `self_healing_blocked_track_backs`.
**EK-1 muss aus sein:** Ab `454a937` enthält der Code das nächste Paket
„Erkundung zielgerichtet“ (Fahrplan Schritt 2). Es ist nur über
Profilparameter einschaltbar und in SH-8 **nicht** Teil des Tests:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  grep -cE "self_healing_scan_rad|self_healing_scan_spacing_m|self_healing_saturation_|self_healing_attempt_stall_" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"
```

Erwartet: `0`. Jede andere Zahl: nicht fahren, berichten.
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

Erwartung: `182 passed` (Cloud, Stand `2409529`; darin sechs Tests für den ausgeschalteten EK-1-Code, siehe Schritt 3). Bei Fehlschlägen nicht fahren,
berichten.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern und die Antworten wörtlich
festhalten:

„Bitte für SH-8 aufbauen wie in SH-7:
1. Dieselbe Tür zwischen Laborraum und Flur ganz öffnen, Türblatt gesichert
   (80 cm, keine Schwelle).
2. Alle anderen Türen beider Räume schließen.
3. In beiden Räumen flache Gegenstände unter etwa 15 cm Höhe vom Boden
   räumen, auch im Türbereich. Die Garderobe im Flur bleibt, wie sie ist.
4. Zwei Mülleimer (wie in SH-5, etwa 38 cm hoch) und einen Abstandshalter
   von 5 cm bereitlegen (zum Beispiel ein Klötzchen oder den Zollstock).“

Geht die Serie an einem anderen Tag weiter, den Aufbau dann einmal erneut
bestätigen lassen („unverändert“ genügt). Ohne geschlossene übrige Türen
keine Probe und keine Fahrt.

## Teil A – Stellprobe (sechs kurze Proben)

Reihenfolge und Kennung `P`: **s3a, s3b** (Mülleimer), **s2a, s2b** (Ecke),
**s1a, s1b** (Garderobe). Jede Probe ist ein Kaltstart mit neuer Karte und
dauert einschließlich Start etwa 6 bis 10 Minuten. `P` in jedem Befehlsblock
setzen, weil die Blöcke nicht zwingend in derselben Shell laufen.

| Stelle | Wo | Wie Amadeus hingestellt wird |
|---|---|---|
| S3 Mülleimer | Laborraum, freie Fläche | zwei Mülleimer nebeneinander, etwa 10 cm Lücke, quer vor Amadeus; seine Front mittig davor, **5 cm** Abstand; hinter ihm mindestens 1 m frei, seitlich je mindestens 0,5 m |
| S2 Ecke | Laborraum, freie Raumecke | gerade in die Ecke hinein: Front **5 cm** vor der Wand, linke Seite **5 cm** neben der Seitenwand; hinter ihm mindestens 1 m frei, rechts mindestens 0,5 m |
| S1 Garderobe | Flur | Front gerade auf die Jacken zu, **5 cm** davor; hinter ihm mindestens 0,5 m frei |

Abstände mit dem Abstandshalter einstellen (±2 cm), danach den Abstandshalter
wegnehmen.

### A1. Hinstellen und bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE
mkdir -p "$SH_PR/sh8_$P"
```

Fehlt ein Gerät: nicht fahren, berichten. Christopher einmal je Probe bitten
und die Antwort wörtlich festhalten: „Bitte stelle Amadeus für Probe <P> an
die Stelle <Stelle> wie in der Tabelle. Welche Abstände hast du eingestellt?
Steht er still und bleibt er während des Starts (etwa eine Minute)
unberührt? Ist der Motor-Stop-Schalter freigegeben, reicht der Akku?“ Nur
nach „ja“ weiter.

### A2. Stack scharf starten

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/sh8_$P/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8_$P/launch.pid"; cat "$SH_PR/sh8_$P/launch.pid"
date -Iseconds > "$SH_PR/sh8_$P/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s (HWT-Einmessung) `nodes.txt` und `lifecycle.txt` erfassen wie
in SH-7. Erwartet: `/base_hardware` und `/rueckfahr_kontur` vorhanden,
`/hwt601_encoder_shadow_reader` nicht.

### A3. Vorprüfung

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && P=s3a && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/sh8_$P/vorpruefung.json" 2>&1 | tee "$SH_PR/sh8_$P/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0 mit denselben Zeilen wie in Teil B Schritt 3 beschrieben
(Tempowerte, AW-1-Werte, „Rueckfahrkontur liegt am Behavior-Server an“, „D
Quellen“ OK, `/cmd_vel 3 s ohne Fahrbefehl`). Bei `FEHL` in „D Quellen“:
nicht fahren, Stack geordnet beenden, einmal neu starten. Jeder andere `FEHL`
(nach einer Wiederholung nach 30 s bei „erreichbar“, „nicht deklariert“ oder
„Graph unvollständig“): Stack geordnet beenden und berichten.

### A4. Protokoll mit Stellprobe starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh8_$P/protokoll.json" \
  --stellprobe-m 0.5 --stellprobe-fenster-s 360 --nachlauf-s 20 --max-s 900 \
  > "$SH_PR/sh8_$P/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8_$P/protokoll.pid"
```

Das Protokoll liest nur mit. Es merkt sich den Standort beim Missionsstart
und **beendet sich selbst**: 20 s nachdem Amadeus 0,5 m davon entfernt ist,
spätestens 6 min nach dem Missionsstart, oder wenn die Mission von selbst
endet. Das Urteil steht danach in `protokoll.json` unter `stellprobe`.

### A5. Mission starten und warten

Christopher drückt in der App „Erkunden“. Steht die App nicht zur Verfügung,
sendet der Agent **genau einmal**:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
```

Danach nur warten, bis der Protokollprozess endet (lesend prüfen, zum
Beispiel alle 10 s `kill -0 "$(cat "$SH_PR/sh8_$P/protokoll.pid")"`), höchstens
8 min. Der Agent greift nicht ein. Christopher beobachtet aus der Nähe mit
der Hand am Not-Aus; nähert sich eine Ecke von Amadeus sichtbar einem
Hindernis, drückt er (das zählt als Eingriff und beendet den Auftrag).

### A6. Probe beenden und sichern

Zuerst das Ergebnis lesen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
tail -40 "$SH_PR/sh8_$P/protokoll.txt"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print(r['protokoll_ende'], json.dumps(r['stellprobe'], ensure_ascii=False))" "$SH_PR/sh8_$P/protokoll.json"
```

Läuft die Mission noch (Protokoll-Ende `stellprobe_weg` oder
`stellprobe_fenster`), sendet der Agent **genau einmal** den Stopp, den auch
die App sendet, und wartet 5 s. Hat die Mission von selbst geendet
(`missionsende`), entfällt der Stopp:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
```

Danach, weiterhin nur lesend:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$SH_PR/sh8_$P/explore_status_ende.txt" 2>&1
grep -o 'last_track_back[^}]*}' "$SH_PR/sh8_$P/explore_status_ende.txt"
grep -nE "Begin navigating|Goal succeeded|Goal failed|Goal canceled|Controller patience exceeded|Failed to make progress|Running backup|backup completed successfully|backup failed|Collision Ahead|Exceeded time allowance|\[collision_monitor\].*Robot to" \
  "$SH_PR/sh8_$P/launch.log" > "$SH_PR/sh8_$P/ablauf.txt"; wc -l "$SH_PR/sh8_$P/ablauf.txt"
grep -c "detected collision ahead" "$SH_PR/sh8_$P/launch.log"
grep -c "process has died" "$SH_PR/sh8_$P/launch.log"
```

**Nur bei Urteil `nicht_befreit` oder „Hilfe benötigt“** zusätzlich wie in
SH-7N sichern (Amadeus steht):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$SH_PR/sh8_$P/tf_map_base_link.txt" 2>&1
timeout 8 ros2 run tf2_ros tf2_echo odom base_link > "$SH_PR/sh8_$P/tf_odom_base_link.txt" 2>&1
timeout 15 ros2 topic echo --once --full-length /local_costmap/costmap > "$SH_PR/sh8_$P/lokale_kostenkarte_ende_voll.txt" 2>&1
```

Christopher einmal fragen und wörtlich festhalten:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Was hast du gesehen: zurückgesetzt, gedreht, gestanden? In welcher
   Reihenfolge, und wie nah kam er dem Hindernis dabei?

Danach den Stack geordnet beenden (SIGINT nur an die Launch-PID,
`roboterknoten.py` danach leer). Läuft das Protokoll noch, es vorher per
SIGINT an `protokoll.pid` beenden.

### A7. Urteil je Probe und wie es weitergeht

| Urteil | Bedeutung | Weiter |
|---|---|---|
| `befreit` | mindestens eine Heilung, danach 0,5 m vom Standort weg, innerhalb von 6 min | nächste Probe |
| `nicht_blockiert` | ohne Heilung weggefahren: Die Stelle hat ihn nicht blockiert, die Probe sagt nichts aus | **einmal** wiederholen mit **3 cm** statt 5 cm (Kennung mit Zusatz `_nah`, zum Beispiel `s3a_nah`); bleibt es dabei, als „Stelle blockiert nicht“ berichten und weiter |
| `nicht_befreit` | nach 6 min nicht 0,5 m weg, oder „Hilfe benötigt“ | die zweite Probe **derselben** Stelle entfällt (kein identischer Fehlversuch); mit der nächsten Stelle weiter |
| Berührung, Eingriff, `outcome=error`, „process has died“ | | **Auftrag beenden**, nur berichten |

Höchstens zehn Starts mit Mission in Teil A, höchstens zwölf Starts
insgesamt (Starts, die „D Quellen“ vor der Mission abfängt, zählen nur zur
Gesamtzahl). Laden zwischen den Proben ist erlaubt.

**Stellprobe bestanden**, wenn keine Probe mit `nicht_befreit`, Berührung
oder Eingriff endete und jede der drei Stellen mindestens einmal `befreit`
ergab. **Nur dann folgt Teil B.** Sonst: Auftrag hier beenden und berichten.

## Teil B – eine volle Zwei-Raum-Fahrt (nur nach bestandener Stellprobe)

Eine Fahrt wie in SH-7, Kaltstart mit neuer Karte, bis zu 40 Minuten. Die
Mülleimer stehen dabei im Laborraum wie in SH-5, die Garderobe bleibt. In
jedem Befehlsblock `RUN=voll` setzen.

### 1. Bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=voll
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE
mkdir -p "$SH_PR/sh8_run$RUN"
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
RUN=voll
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/sh8_run$RUN/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8_run$RUN/launch.pid"; cat "$SH_PR/sh8_run$RUN/launch.pid"
date -Iseconds > "$SH_PR/sh8_run$RUN/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s (HWT-Einmessung) wie in SH-2 `nodes.txt`, 10 s später
`nodes_2.txt` und `lifecycle.txt` erfassen. Erwartet: `/base_hardware`
vorhanden, `/hwt601_encoder_shadow_reader` **nicht** (mit `active_drive`
startet der Launch nur den Motortreiber), **neu** `/rueckfahr_kontur`
vorhanden (ein Knoten mehr als in SH-7, dort 39).

### 3. Vorprüfung direkt vor der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && RUN=voll && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/sh8_run$RUN/vorpruefung.json" 2>&1 | tee "$SH_PR/sh8_run$RUN/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0, Bereiche A–C wie in SH-3, aber `B SLAM-Overlay` mit
**sechs** Zeilen: zusätzlich `minimum_travel_distance` 0.25 und
`minimum_travel_heading` 0.35. **Neu** genau zwei `B Nav2-Overlay`-Zeilen zu
`/controller_server`: `FollowPath.desired_linear_vel` 0.135 und
`FollowPath.rotate_to_heading_angular_vel` 0.25; zu `/velocity_smoother`
`max_velocity` [0.162, 0.0, 0.3125] und `min_velocity` [-0.05, 0.0, -0.3125];
in A `self_healing_unknown_speed_mps` 0.08 und
`initial_scan_angular_speed_radps` 0.10. **Neu (AW-1):** `B Nav2-Overlay`
zu `/behavior_server` `footprint_topic` 'rueckfahr_kontur', zu
`/local_costmap/local_costmap` `plugins` und die `lidar_layer.*`-Werte, zu
`/global_costmap/global_costmap` die beiden `inflation_layer`-Werte; in C
die Zeile `Rueckfahrkontur liegt am Behavior-Server an` OK; in A die
Sammelzeile mit `self_healing_free_back_m` und
`self_healing_track_back_slow_factor`. In D
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
RUN=voll
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh8_run$RUN/protokoll.json" --max-s 3600 \
  > "$SH_PR/sh8_run$RUN/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8_run$RUN/protokoll.pid"
```

`--max-s 3600`: Das Protokoll beendet sich sonst nach 30 min, die Fahrt
dauert bis zu 40 min. Es zeichnet seit `609d389` zusätzlich die
Abdeckungskurve auf (liest `/map`, publiziert nichts). Nur lesend, nebenher die Rechenlast von `slam_toolbox` alle 10 s mitschreiben
(SH-3: sie stieg in 20 min auf 85–95 % eines Kerns, mit SL-1 in SH-6 auf
10–15 %; Kriterium C2). `-x` vergleicht den Prozessnamen exakt und
trifft daher nicht die eigene Shell:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=voll
SLAM_PID=$(pgrep -x async_slam_tool | head -1); echo "SLAM_PID=$SLAM_PID"
echo "$SLAM_PID" > "$SH_PR/sh8_run$RUN/slam.pid"
nohup top -b -d 10 -p "$SLAM_PID" > "$SH_PR/sh8_run$RUN/slam_cpu.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8_run$RUN/slam_cpu.pid"
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
RUN=voll
cat "$SH_PR/sh8_run$RUN/protokoll.txt" | tail -60
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$SH_PR/sh8_run$RUN/explore_status_ende.txt" 2>&1
grep -o 'last_track_back[^}]*}' "$SH_PR/sh8_run$RUN/explore_status_ende.txt"
grep -cE "Collision Ahead|backup completed successfully|backup failed|Exceeded time allowance" "$SH_PR/sh8_run$RUN/launch.log"
grep -nE "Running backup|backup completed successfully|backup failed|Collision Ahead|Exceeded time allowance|\[collision_monitor\].*Robot to" "$SH_PR/sh8_run$RUN/launch.log" > "$SH_PR/sh8_run$RUN/rueckfahrten_kollisionsmonitor.txt"
for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
  echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$SH_PR/sh8_run$RUN/lifecycle_nach.txt"
grep -c "process has died" "$SH_PR/sh8_run$RUN/launch.log"
grep -nE "Ignoring the source|TERMINAL_FAULT|ERROR|FATAL" "$SH_PR/sh8_run$RUN/launch.log" | head -40
for m in "extrapolation into the future" "Unable to transform robot pose" "missed its desired rate" "detected collision ahead" "queue is full"; do \
  echo "$m: $(grep -c "$m" "$SH_PR/sh8_run$RUN/launch.log")"; done | tee "$SH_PR/sh8_run$RUN/zeitfehler.txt"
kill -TERM "$(cat "$SH_PR/sh8_run$RUN/slam_cpu.pid")"
grep -E "^ *$(cat "$SH_PR/sh8_run$RUN/slam.pid") " "$SH_PR/sh8_run$RUN/slam_cpu.txt" | awk '{print $9}' | tr '\n' ' ' | tee "$SH_PR/sh8_run$RUN/slam_cpu_reihe.txt"
ros2 run nav2_map_server map_saver_cli -f "$SH_PR/sh8_run$RUN/karte"
```

**Nur wenn die Fahrt mit „Hilfe benötigt“ endete**, vor dem Stoppen lesend
wie in SH-7 sichern (Amadeus steht dann still):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=voll
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$SH_PR/sh8_run$RUN/tf_map_base_link.txt" 2>&1
timeout 8 ros2 run tf2_ros tf2_echo odom base_link > "$SH_PR/sh8_run$RUN/tf_odom_base_link.txt" 2>&1
timeout 15 ros2 topic echo --once --full-length /local_costmap/costmap > "$SH_PR/sh8_run$RUN/lokale_kostenkarte_ende_voll.txt" 2>&1
```

Danach mit dem SH-7N-Werkzeug lesend auswerten (vorher nach
`$SH_PR/werkzeug/` kopieren, Pfade anpassen):
`/home/p/.local/share/amadeus/releases/selbstheilung-sh7-20261108_1617/pruefung/werkzeug/sh7n_auswertung.py`.

Christopher dann einmal fragen und die Antworten wörtlich festhalten:

1. Hat Amadeus etwas berührt, auch Türrahmen, Türblatt oder Garderobe?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Sieht die Karte sauber aus, ohne doppelte oder verdrehte Wände?
4. Auch dort, wo sich Amadeus auf der Stelle gedreht hat, und an der Tür:
   Passen beide Räume aneinander, liegt die Türöffnung an der richtigen
   Stelle?
5. Ist Amadeus selbst durch die Tür in den Flur gefahren? Wann ungefähr zum
   ersten Mal, und wie oft insgesamt hindurch?
6. Ist der Flur in der Karte zu erkennen: ganz, größtenteils, nur teilweise
   oder gar nicht?
7. Nur wenn die Fahrt mit „Hilfe benötigt“ endete: Wo stand er (welcher
   Raum, in der Tür?), was stand daneben, und hätte er nach deiner
   Einschätzung ausweichen können, wohin?
8. Hast du gesehen, dass er sich an einer engen Stelle rückwärts befreit
   hat? Wo, und kam er danach weiter?
9. Fuhr er an Möbeln und Türrahmen mit sichtbarem Abstand vorbei, oder eher
   dicht daran entlang?

Ist die App nicht verfügbar, die gespeicherte Karte (`karte.pgm`) als Bild
zeigen, wie in SH-3.

Danach den Stack geordnet beenden (wie SH-2 Schritt 9: SIGINT nur an die
Launch-PID, `roboterknoten.py` danach leer). Läuft das Protokoll noch, sein
Prozess vorher per SIGINT an `protokoll.pid` beenden.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei:
  - Berührung, auch leicht, auch an Mülleimer, Jacke, Türrahmen oder Türblatt;
  - Fahrt oder Drehung auf ein Hindernis ohne rechtzeitiges Abbremsen;
  - Fahrt in einen dritten Raum oder durch eine Tür, die zu sein sollte;
  - Türblatt bewegt sich oder Tür fällt zu, während Amadeus in der Nähe ist
    (Probe oder Fahrt ungültig, darf nach erneutem Sichern einmal wiederholt
    werden);
  - ungewöhnlichem Geräusch;
  - Rauch.

  Danach keine weitere Probe und keine Fahrt in dieser Sitzung; nur berichten.
- **Endet eine Probe oder Fahrt mit `outcome=error`:** anhalten und berichten.
- **Ungültige Probe oder Fahrt** aus einem äußeren Grund (zum Beispiel kommt
  jemand in den Raum): darf einmal wiederholt werden.
- Keine Parameter ändern, um eine Probe oder Fahrt „durchzubringen“.

## Bewertung

Die Kriterien stehen vor der ersten Probe fest.

**Teil A, je Probe:**

| Nr | Kriterium | Quelle |
|---|---|---|
| P1 | Urteil `befreit` | `protokoll.json`, Block `stellprobe` |
| P2 | keine Berührung, kein Eingriff | Christophers Antworten 1 und 2 |
| P3 | kein „Hilfe benötigt“, kein `outcome=error`, kein „process has died“ | Protokoll, `launch.log` |

Stellprobe bestanden: siehe A7. Gemessen, aber kein Kriterium: Zeit bis
0,5 m weg, Zahl und Art der Rückfahrten, Zustand des Kollisionsmonitors
während jeder Rückfahrt.

**Teil B, die volle Fahrt** (Kriterien wie in SH-7, damit der Vergleich gilt):

| Nr | Kriterium | Quelle |
|---|---|---|
| C1 | Stufe 1 wie in SH-3: `automatisch_erfuellt: true`, kein Kontakt (auch nicht mit Türrahmen oder Türblatt), kein Eingriff, Nav2 danach klar, kein „process has died“ vor dem Stopp | Protokoll, Christopher, Schritt 7 |
| C2 | `slam_toolbox` im Mittel der letzten sechs Werte (letzte Minute) ≤ 50 % eines Kerns | `slam_cpu_reihe.txt` |
| C3 | höchstens 20× „queue is full“ | `zeitfehler.txt` |
| C4 | höchstens 80× „extrapolation into the future“ | `zeitfehler.txt` |
| C5 | Karte sauber, auch an Drehstellen und an der Tür (beide Räume passen aneinander) | Christophers Antworten 3 und 4 |
| G1 | kein Ende mit „Hilfe benötigt“ an einer Stelle, an der Christopher Platz zum Ausweichen sieht | Christophers Antwort 7 |
| R1 | Amadeus fährt selbstständig durch die offene Tür in den Flur | Christophers Antwort 5 |
| R2 | Der Flur ist in der Karte ganz oder größtenteils zu erkennen | Christophers Antwort 6 |

Eine einzelne Fahrt bestätigt den Raumwechsel noch nicht; nach MASTERPLAN §9
braucht es drei. Erfüllt diese Fahrt alle Kriterien, folgen die zwei
weiteren als eigener kurzer Auftrag.

## Bericht: `~/selbstheilung_jetson_bericht_sh8.md`

1. Kopf: Datum, Release, HEAD, Ergebnis der Schritte 0–4 (Build-Dauer,
   Präfixe, Overlay-Zeilen, Testergebnis), Aufbau mit Christophers Antworten
   wörtlich.
2. **Teil A, Tabelle über alle Proben:** Kennung, Stelle, eingestellte
   Abstände (Christopher), Urteil, Zeit bis 0,5 m weg, Heilungen und
   Rückfahrten bis dahin, größte Entfernung, Christophers drei Antworten
   wörtlich.
3. **Teil A, je Probe der Ablauf** aus `ablauf.txt` (wörtlich, gleiche
   aufeinanderfolgende Zeilen zusammenfassen), dazu: Vorprüfung (Exit, Zahl
   OK/FEHL), `heilungsverlauf`, `last_track_back`, Zahl „detected collision
   ahead“, und **für jede Rückfahrt**: Art (`mode`: `spur` oder `frei`),
   Ergebnis des `behavior_server` (erfolgreich, Zeitgrenze, „Collision
   Ahead“), Zustand des Kollisionsmonitors davor und währenddessen (letzte
   Zeile „Robot to …“ vor „Running backup“ und alle bis zu ihrem Ende;
   besonders, ob „approach“ dabei war), welches Ziel danach kam.
4. **Urteil Teil A:** Stellprobe bestanden / nicht bestanden, mit Grund. Für
   jede Probe `nicht_befreit` die Daten wie in SH-7N (`map→odom`, Zellen
   ≥ 99 und = 100 im Umkreis von 1,5 m, Zellen an der Kontur; Werkzeug
   `…/selbstheilung-sh7-20261108_1617/pruefung/werkzeug/sh7n_auswertung.py`
   nach `$SH_PR/werkzeug/` kopieren und Pfade anpassen).
5. **Teil B**, falls gefahren: wie in SH-7 (Startplatz, Knotenlisten,
   Vorprüfung, Fahrtprotokoll, Ereignisse, Heilungsverlauf, Lifecycle danach,
   Warnungen, `zeitfehler.txt`, `slam_cpu_reihe.txt`, Christophers neun
   Antworten wörtlich), Tabelle C1–C5, G1, R1, R2 mit Wert und erfüllt/nicht
   erfüllt neben den SH-7-Werten, erste Durchfahrt, alle Rückfahrten wie in
   Punkt 3, und die **Abdeckungskurve** (Block `abdeckung` wörtlich,
   `abdeckungskurve` als Tabelle). Bei „Hilfe benötigt“ die Daten wie in
   SH-7N.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad; je Probe Kennung,
Urteil und Zeit bis 0,5 m weg; Stellprobe bestanden oder nicht; falls
gefahren C1–C5, G1, R1, R2 der vollen Fahrt und die Fahrzeit bis 90 % der
freien Endfläche; Kontakte oder Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Besteht die Stellprobe nicht, folgt nach
MASTERPLAN §9 Regel 4 eine gezielte Korrektur (Kandidat: lokale Karte löscht
nichts unter der Kontur, KM-1 B) und dieselbe Stellprobe erneut.
