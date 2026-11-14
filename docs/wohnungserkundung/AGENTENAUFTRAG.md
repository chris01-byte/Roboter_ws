# Aktueller Agentenauftrag: SH-8b – dieselbe Stellprobe mit KM-1 B, bei Erfolg eine volle Zwei-Raum-Fahrt

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 13.11.2026 nach
der Auswertung von SH-8 ([archiviert](archive/20261113-sh8-ausgewertet/README.md)).

**Warum:** In SH-8 kam Amadeus an Ecke und Garderobe ohne Berührung frei
(AW-1 wirkt: kein „Collision Ahead“ mehr). **An den Mülleimern nicht:** Er
fuhr bis an den Eimer heran, dann meldete der Kollisionsmonitor „approach“
und setzte jede Bewegung auf null, auch beide Rückfahrten (an der Basis kam
kein einziger Fahrbefehl an). Der Grund: Die lokale Karte löschte alles
unter der gepolsterten Kontur. Was vom Eimer in das 2-cm-Polsterband rückte,
verschwand aus der Karte, und der Regler fuhr weiter hinein.

**Prüfling ist genau eine Änderung, KM-1 B** (`1f8ecf9`, Messwerkzeuge `e7d38d0`, nur im
Selbstheilungsbetrieb): Beide Hindernisebenen der lokalen Karte löschen
nichts mehr unter der Kontur (`footprint_clearing_enabled: False`). Das
Hindernis bleibt eingetragen, der Regler hält vorher an, weg geht es über
die Rückfahrkontur aus AW-1. Kollisionsmonitor, globale Karte, Tempo,
Rückfahrt, Budget und Heilungsleiter bleiben wie in SH-8.

**Dazu zwei reine Messungen, keine Verhaltensänderung:**

1. **Eigenechos (Vorprüfung, neuer Bereich F):** Weil die lokale Karte
   unter der Kontur nichts mehr löscht, bliebe ein Messpunkt auf dem Roboter
   selbst (Mast, Halter) als Hindernis stehen. Vor jeder Probe prüft die
   Vorprüfung deshalb 10 s lang, ob ein LiDAR- oder VL53-Punkt im Gehäuse
   liegt und ob die lokale Karte darunter eine tödliche Zelle hat.
2. **Rückfahrstrecke (Fahrtprotokoll):** Jede Rückwärtsfahrt wird mit Dauer,
   kleinster Geschwindigkeit und der laut Odometrie zurückgelegten Strecke
   aufgezeichnet. In SH-8 endeten 7 von 8 Rückfahrten an der 30-s-Grenze;
   wie weit Amadeus dabei kam, war nur ungefähr bekannt.

**Erwartetes Verhalten an jeder Stelle:** Amadeus fährt nicht mehr bis an den
Eimer heran. Der Regler hält vorher an (im Log häufiger „detected collision
ahead“, das ist jetzt normal). Dann setzt er etwa 0,3 m gerade zurück,
wählt ein anderes Ziel und fährt weg. Ein „approach“ des Kollisionsmonitors
sollte nicht mehr vorkommen; falls doch, wird es festgehalten. Die
Rückfahrt ist mit etwas vor ihm langsam (0,015 m/s) und kann an der
30-s-Grenze enden; das ist bekannt und nicht Teil dieses Tests. Eine
Befreiung kann deshalb bis zu etwa 4 Minuten dauern.

**Jede Berührung beendet den ganzen Auftrag.** Prototyp 1
(`selbstheilung-sh6-20261104_2140`), der SH-7- und der SH-8-Release bleiben
unverändert.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/MASTERPLAN.md` §9,
`docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md` §5, §9 und §11, im STATUS
die Arbeitsliste und die Abschnitte 13.11.2026 (SH-8, Simulation KM-1 B)
und 10.11.2026. Der SH-8-Auftrag ist
[archiviert](archive/20261113-sh8-ausgewertet/README.md); Teil A und Teil B
laufen hier genauso ab.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 13.11.2026; **Fahrplan §9, Schritt 1, Regeln 4 und 6** (Korrektur für dasselbe Problem, dieselbe Stellprobe) |
| WE-Bezug | WE-M3, metrischer Kern im Zwei-Raum-Umfang; Vorstufe zu WE-M4, keine Abnahme von WE-M4; Vorbedingung Stufe 3 (Wohnung) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `e7d38d0`; neuer Release `selbstheilung-sh8b-<STAMP>`. SH-8 lief mit `selbstheilung-sh8-20261113_2153` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh8b.md`: Build, 197 gezielte Tests, **Teil A** Stellprobe an drei Stellen (je zweimal) mit Urteil je Probe, Eigenecho-Zeilen und Rückfahrstrecken, **Teil B** nur bei bestandener Stellprobe eine volle Zwei-Raum-Fahrt mit C1–C5, G1, R1, R2 |
| Nicht-Ziele | keine eigene Code- oder Parameteränderung, kein dritter Raum, keine Wohnungsfahrt, keine Tür mit Schwelle, kein Arm, kein Vergleich mit älteren Releases, keine Änderung an Rückfahrtempo oder Langsam-Zone |
| Rückfall | in der Umgebungsdatei `SH_REL` auf `…/selbstheilung-sh8-20261113_2153` (SH-8-Stand ohne KM-1 B), `…/selbstheilung-sh7-20261108_1617` oder `…/selbstheilung-sh6-20261104_2140` (Prototyp 1) zurückstellen; alle Releases bleiben |
| Laborrahmen | LAB-1: aktive Fahrt im beauftragten Umfang ohne erneute Standardfreigaben. Not-Aus-Erreichbarkeit und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden **nicht** erneut abgefragt. Wie in SH-8 entschieden (10.11.2026): In Teil A steht Amadeus beim Start absichtlich 5 cm vor einem Hindernis |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3;
- schreibend nur: der Stackstart je Probe oder Fahrt, falls die App fehlt
  **genau ein** Missionsstart je Probe oder Fahrt, und in Teil A **genau ein**
  Missionsstopp je Probe (derselbe Befehl wie der Stopp der App, siehe A5);
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
- **Vorwärts:** Regler 0,135 m/s, höchstens 0,162 m/s; 0,08 m/s, solange vor
  ihm nicht kartiert ist (also auch beim ersten Durchfahren der Tür).
- **Drehen:** Regler 0,25 rad/s, höchstens 0,3125 rad/s.
- **Rückwärts:** entlang der eigenen geraden Spur oder, wenn es keine gibt,
  0,3 m gerade zurück, sofern hinten frei ist; höchstens 0,4 m, 0,05 m/s
  (mit etwas vor ihm 0,015 m/s), einmal je Stillstand.
- **Neu (KM-1 B):** Hindernisse dicht an ihm bleiben in seiner lokalen Karte
  stehen. Er fährt und dreht nicht mehr in sie hinein, sondern meldet einen
  Fehlschlag und setzt zurück.
- Er wählt seine Ziele selbst (Frontiers) und heilt Fehlschläge selbst:
  1. erneut versuchen;
  2. Ziel zurückstellen;
  3. umsehen;
  4. ein Stück zurück (kommt er in einem Anlauf nicht vom Fleck, sofort;
     auch ohne gerade Spur, danach ein anderes Ziel);
  5. „Hilfe benötigt“.
- Eine Fahrt endet von selbst mit „vollständig“, „Teilkarte“ oder „Hilfe
  benötigt“, spätestens nach **40 Minuten**.
- **Kurzes Stehenbleiben ist normal:** Setzen die VL53 einige Sekunden aus,
  sperrt das Fahrtor nach 0,8 s, und der Explorer wartet bis zu 30 s, bevor
  er Hilfe ruft. Das ist kein Eingriffsgrund. Auch Abbremsen oder kurzes
  Halten in der Tür ist normal (Kollisionsmonitor).

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
  git rev-parse HEAD && git merge-base --is-ancestor e7d38d0 HEAD && echo "e7d38d0 enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh8b-$STAMP/pruefung
```

### Schritt 2 – Umgebungsdatei

In `~/roboter_worktrees/selbstheilung-v2.env` mit dem Datei-Werkzeug nur die
Zeile `export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/selbstheilung-sh8b-<STAMP>`
ändern. Die Unterbauzeilen bleiben. Prüfen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "rc=$?"; echo "$SH_SRC $SH_REL"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
```

Erwartung: `rc=0`, Zähler `0`.

### Schritt 3 – Build (wie SH-8)

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

Danach wie in SH-8 prüfen: `Found behaviortree_cpp` unter native-install, alle
14 Präfixe unter `$SH_REL/product-install` (`prefixes.txt`). Dann die
Profilzeilen (dieselben wie in SH-8, dazu **neu** `footprint_clearing_enabled`):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  grep -n "minimum_travel" "$SH_REL/product-install/amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml"; \
  grep -cE "max_allowed_time_to_collision_up_to_carrot|xy_goal_tolerance" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  grep -nE "desired_linear_vel|rotate_to_heading_angular_vel|max_velocity|min_velocity|footprint_topic|plugins|lidar_layer|clearing|inflation_radius|cost_scaling_factor" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  ls "$SH_REL/product-install/robot_navigation/lib/robot_navigation/rueckfahr_kontur"; \
  grep -nE "self_healing_goal_shift_max_m|self_healing_track_lateral_tolerance_m|self_healing_blocked_track_backs|self_healing_stuck_move_m|overall_timeout_s|self_healing_unknown_speed_mps|initial_scan_angular_speed_radps|self_healing_free_back_m|self_healing_track_back_slow_factor" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"; \
  grep -cE "self_healing_scan_rad|self_healing_scan_spacing_m|self_healing_saturation_|self_healing_attempt_stall_" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"
```

Erwartet wie in SH-8: `minimum_travel_distance: 0.25`,
`minimum_travel_heading: 0.35`; DR-1-Zähler `0`; Tempo `0.135`, `0.25`,
`[0.162, 0.0, 0.3125]`, `[-0.05, 0.0, -0.3125]`;
`footprint_topic: rueckfahr_kontur`, `plugins` mit `lidar_layer`,
`clearing: True`, `0.60` / `2.5`; Programm `rueckfahr_kontur` vorhanden;
Explorer `0.3`, `0.3`, `0.08`, `0.10`, `0.5`, `0.03`, `0.05`, `2400.0`;
keine Zeile `self_healing_blocked_track_backs`; EK-1-Zähler `0`. **Neu
(KM-1 B):** genau **zwei** Zeilen `footprint_clearing_enabled: False`, eine
unter `obstacle_layer`, eine unter `lidar_layer` (beide im Block
`local_costmap`). Jede Abweichung: nicht fahren, berichten. Bei
Build-Fehler oder fehlendem Präfix: nicht fahren, berichten.

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
  tools/kartierung/test_selbstheilung_lauf_protokoll.py \
  2>&1 | tee "$SH_PR/tests.log" | tail -40
```

Erwartung: `197 passed` (Cloud, Stand `e7d38d0`; neu ist die letzte
Datei mit den Protokolltests). Bei Fehlschlägen nicht fahren, berichten.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern und die Antwort wörtlich
festhalten:

„Bitte für SH-8b aufbauen wie in SH-8:
1. Dieselbe Tür zwischen Laborraum und Flur ganz öffnen, Türblatt gesichert
   (80 cm, keine Schwelle).
2. Alle anderen Türen beider Räume schließen.
3. In beiden Räumen flache Gegenstände unter etwa 15 cm Höhe vom Boden
   räumen, auch im Türbereich. Die Garderobe im Flur bleibt, wie sie ist.
4. Dieselben zwei Mülleimer und den 5-cm-Abstandshalter bereitlegen.“

Geht die Serie an einem anderen Tag weiter, den Aufbau dann einmal erneut
bestätigen lassen („unverändert“ genügt). Ohne geschlossene übrige Türen
keine Probe und keine Fahrt.

## Teil A – Stellprobe (sechs kurze Proben)

Reihenfolge und Kennung `P`: **s3a, s3b** (Mülleimer, die Stelle, an der
SH-8 scheiterte), **s2a, s2b** (Ecke), **s1a, s1b** (Garderobe). Jede Probe
ist ein Kaltstart mit neuer Karte und dauert einschließlich Start etwa 6 bis
10 Minuten. `P` in jedem Befehlsblock setzen, weil die Blöcke nicht zwingend
in derselben Shell laufen.

| Stelle | Wo | Wie Amadeus hingestellt wird |
|---|---|---|
| S3 Mülleimer | Laborraum, freie Fläche | zwei Mülleimer nebeneinander, etwa 10 cm Lücke, quer vor Amadeus; seine Front mittig davor, **5 cm** Abstand; hinter ihm mindestens 1 m frei, seitlich je mindestens 0,5 m |
| S2 Ecke | Laborraum, freie Raumecke | gerade in die Ecke hinein: Front **5 cm** vor der Wand, linke Seite **5 cm** neben der Seitenwand; hinter ihm mindestens 1 m frei, rechts mindestens 0,5 m |
| S1 Garderobe | Flur | Front gerade auf die Jacken zu, **5 cm** davor; hinter ihm mindestens 0,5 m frei |

Abstände mit dem Abstandshalter einstellen (±2 cm), danach den Abstandshalter
wegnehmen. Möglichst dieselben Stellen wie in SH-8.

### A1. Hinstellen und bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
mkdir -p "$SH_PR/sh8b_$P"
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
  > "$SH_PR/sh8b_$P/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8b_$P/launch.pid"; cat "$SH_PR/sh8b_$P/launch.pid"
date -Iseconds > "$SH_PR/sh8b_$P/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s (HWT-Einmessung) `nodes.txt` und `lifecycle.txt` erfassen wie
in SH-8. Erwartet: `/base_hardware` und `/rueckfahr_kontur` vorhanden,
`/hwt601_encoder_shadow_reader` nicht. Meldet der LiDAR-Treiber
„communication is abnormal“ (in SH-8 dreimal beim Start): Stack geordnet
beenden, Christopher einmal bitten, den LiDAR-Stecker zu prüfen, dann einmal
neu starten (zählt zur Gesamtzahl der Starts).

### A3. Vorprüfung mit Eigenechos

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && P=s3a && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 \
  --json "$SH_PR/sh8b_$P/vorpruefung.json" 2>&1 | tee "$SH_PR/sh8b_$P/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0 mit denselben Zeilen wie in SH-8 (Tempowerte, AW-1-Werte,
„Rueckfahrkontur liegt am Behavior-Server an“, „D Quellen“ OK,
`/cmd_vel 3 s ohne Fahrbefehl`), dazu **neu**:

- Bereich `B Nav2-Overlay`: `/local_costmap/local_costmap
  obstacle_layer.footprint_clearing_enabled` und
  `… lidar_layer.footprint_clearing_enabled`, beide OK (`False`);
- Bereich `F Eigenechos`: eine INFO-Zeile „Loeschen unter der Kontur“ mit
  `obstacle_layer=False, lidar_layer=False`, dann **vier OK-Zeilen**:
  `LiDAR: … 0 Punkte im Gehaeuse`, `VL53 left: … 0 Punkte im Gehaeuse`,
  `VL53 right: … 0 Punkte im Gehaeuse` und
  `lokale Kostenkarte: 0 toedliche Zellen im Gehaeuse`.

Bei `FEHL` in „D Quellen“: nicht fahren, Stack geordnet beenden, einmal neu
starten. **Bei `FEHL` im Bereich F: nicht fahren, Stack geordnet beenden,
keine Wiederholung, Auftrag beenden und berichten** (die Detailzeile und den
Block `eigenechos` aus `vorpruefung.json` wörtlich). Ein Eigenecho würde mit
KM-1 B als Hindernis stehen bleiben. Jeder andere `FEHL` (nach einer
Wiederholung nach 30 s bei „erreichbar“, „nicht deklariert“ oder „Graph
unvollständig“): Stack geordnet beenden und berichten.

### A4. Protokoll mit Stellprobe starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh8b_$P/protokoll.json" \
  --stellprobe-m 0.5 --stellprobe-fenster-s 360 --nachlauf-s 5 --max-s 900 \
  > "$SH_PR/sh8b_$P/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8b_$P/protokoll.pid"
```

Das Protokoll liest nur mit und beendet sich selbst wie in SH-8, aber schon
**5 s** (statt 20 s) nachdem Amadeus 0,5 m weg ist. Neu steht im Ergebnis der
Block `rueckfahrten`: je Rückwärtsfahrt Beginn, Dauer, kleinste
Geschwindigkeit, Zahl der Befehle und die laut `/odom` zurückgelegte
Strecke.

### A5. Mission starten und warten

Christopher drückt in der App „Erkunden“. Steht die App nicht zur Verfügung,
sendet der Agent **genau einmal**:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
```

**Direkt nach dem Missionsstart** diesen Block starten. Er wartet, bis das
Protokoll endet (höchstens 8 min), und sendet dann **sofort genau einmal**
den Stopp, den auch die App sendet, sofern die Mission noch läuft
(Protokoll-Ende `stellprobe_weg` oder `stellprobe_fenster`). Hat die Mission
von selbst geendet (`missionsende`), entfällt der Stopp:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
PROT=$(cat "$SH_PR/sh8b_$P/protokoll.pid")
for i in $(seq 480); do kill -0 "$PROT" 2>/dev/null || break; sleep 1; done
kill -0 "$PROT" 2>/dev/null && { kill -INT "$PROT"; sleep 3; }
ENDE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['protokoll_ende'])" "$SH_PR/sh8b_$P/protokoll.json")
echo "protokoll_ende=$ENDE"
if [ "$ENDE" != "missionsende" ]; then
  ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
  date -Iseconds > "$SH_PR/sh8b_$P/missionsstopp.txt"
fi
```

**Warum sofort:** In der Simulation befreite sich Amadeus mit KM-1 B in 4
von 4 Läufen von den Mülleimern, berührte aber 25 s bis 5 min später beim
Vorbeifahren oder Drehen eine Eimerseite, die die VL53 nie gesehen hatten
(bekannte Grenze: Gegenstände unter 0,75 m sieht nur die VL53, und nur nach
vorn). Nach 0,5 m ist die Probe entschieden; jede weitere Fahrt an den
Eimern bringt nichts.

Der Agent greift sonst nicht ein. Christopher beobachtet aus der Nähe mit
der Hand am Not-Aus; nähert sich eine Ecke **oder eine Seite** von Amadeus
sichtbar einem Hindernis, besonders beim Vorbeifahren an einem Mülleimer,
drückt er (das zählt als Eingriff und beendet den Auftrag).

### A6. Probe sichern

Zuerst das Ergebnis lesen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
tail -40 "$SH_PR/sh8b_$P/protokoll.txt"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print(r['protokoll_ende'], json.dumps(r['stellprobe'], ensure_ascii=False)); print(json.dumps(r['rueckfahrten'], ensure_ascii=False))" "$SH_PR/sh8b_$P/protokoll.json"
```

Danach, weiterhin nur lesend:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$SH_PR/sh8b_$P/explore_status_ende.txt" 2>&1
grep -o 'last_track_back[^}]*}' "$SH_PR/sh8b_$P/explore_status_ende.txt"
grep -nE "Begin navigating|Goal succeeded|Goal failed|Goal canceled|Controller patience exceeded|Failed to make progress|Running backup|backup completed successfully|backup failed|Collision Ahead|Exceeded time allowance|\[collision_monitor\].*Robot to" \
  "$SH_PR/sh8b_$P/launch.log" > "$SH_PR/sh8b_$P/ablauf.txt"; wc -l "$SH_PR/sh8b_$P/ablauf.txt"
grep -c "detected collision ahead" "$SH_PR/sh8b_$P/launch.log"
grep -c "Robot to approach" "$SH_PR/sh8b_$P/launch.log"
grep -c "process has died" "$SH_PR/sh8b_$P/launch.log"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 --json "$SH_PR/sh8b_$P/nachpruefung.json" 2>&1 | grep -E "F Eigenechos|ERGEBNIS" | tee "$SH_PR/sh8b_$P/nachpruefung_f.txt"
timeout 15 ros2 topic echo --once --full-length /local_costmap/costmap > "$SH_PR/sh8b_$P/lokale_kostenkarte_ende_voll.txt" 2>&1
```

Die Nachprüfung zeigt, ob nach der Fahrt Punkte im Gehäuse liegen. Liegen
**LiDAR- oder VL53-Punkte** im Gehäuse (`FEHL` in einer dieser drei Zeilen):
Auftrag nach dieser Probe beenden und berichten. Tödliche Zellen der
Kostenkarte im Gehäuse nach der Fahrt nur berichten (sie können auch von
Odometriedrift stammen) und weitermachen.

**Nur bei Urteil `nicht_befreit` oder „Hilfe benötigt“** zusätzlich wie in
SH-8 sichern (Amadeus steht):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$SH_PR/sh8b_$P/tf_map_base_link.txt" 2>&1
timeout 8 ros2 run tf2_ros tf2_echo odom base_link > "$SH_PR/sh8b_$P/tf_odom_base_link.txt" 2>&1
```

Christopher einmal fragen und wörtlich festhalten:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Was hast du gesehen: zurückgesetzt, gedreht, gestanden? In welcher
   Reihenfolge, und wie nah kam er dem Hindernis dabei (sichtbare Lücke,
   etwa wie viele Zentimeter)?

Danach den Stack geordnet beenden (SIGINT nur an die Launch-PID,
`roboterknoten.py` danach leer). Läuft das Protokoll noch, es vorher per
SIGINT an `protokoll.pid` beenden.

### A7. Urteil je Probe und wie es weitergeht

| Urteil | Bedeutung | Weiter |
|---|---|---|
| `befreit` | mindestens eine Heilung, danach 0,5 m vom Standort weg, innerhalb von 6 min | nächste Probe |
| `nicht_blockiert` | ohne Heilung weggefahren: Die Stelle hat ihn nicht blockiert, die Probe sagt nichts aus | **einmal** wiederholen mit **3 cm** statt 5 cm (Kennung mit Zusatz `_nah`, zum Beispiel `s3a_nah`); bleibt es dabei, als „Stelle blockiert nicht“ berichten und weiter |
| `nicht_befreit` | nach 6 min nicht 0,5 m weg, oder „Hilfe benötigt“ | die zweite Probe **derselben** Stelle entfällt (kein identischer Fehlversuch); mit der nächsten Stelle weiter |
| Berührung, Eingriff, `outcome=error`, „process has died“, Eigenecho (A3 oder A6) | | **Auftrag beenden**, nur berichten |

Höchstens zehn Starts mit Mission in Teil A, höchstens zwölf Starts
insgesamt (Starts, die „D Quellen“ oder ein LiDAR-Startfehler vor der
Mission abfängt, zählen nur zur Gesamtzahl). Laden zwischen den Proben ist
erlaubt.

**Stellprobe bestanden**, wenn keine Probe mit `nicht_befreit`, Berührung,
Eingriff oder Eigenecho endete und jede der drei Stellen mindestens einmal
`befreit` ergab. **Nur dann folgt Teil B.** Sonst: Auftrag hier beenden und
berichten.

## Teil B – eine volle Zwei-Raum-Fahrt (nur nach bestandener Stellprobe)

Genau wie Teil B im
[SH-8-Auftrag](archive/20261113-sh8-ausgewertet/AGENTENAUFTRAG.md)
(Schritte 1–7, Fragen, Kriterien), mit diesen Unterschieden:

- Ordner `"$SH_PR/sh8b_run$RUN"` statt `sh8_run$RUN`, `RUN=voll`;
- in Schritt 3 die Vorprüfung **mit** `--eigenecho-s 10`; erwartet wie in A3
  (Amadeus steht am Startplatz mit etwa 0,5 m Platz rundherum);
- in Schritt 7 zusätzlich `grep -c "Robot to approach"` auf `launch.log` und
  den Block `rueckfahrten` aus `protokoll.json` sichern.

**Abweichung von SH-8:** In Teil B stehen **keine** Mülleimer in den beiden
Räumen (vorher hinausstellen; Christopher bestätigt das in Schritt 1). Die
Eimer prüft Teil A; seitlich an niedrigen Gegenständen vorbei ist eine
bekannte, getrennt geparkte Grenze. Die Garderobe bleibt.

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

Die Kriterien stehen vor der ersten Probe fest und sind dieselben wie in
SH-8, dazu P4.

**Teil A, je Probe:**

| Nr | Kriterium | Quelle |
|---|---|---|
| P1 | Urteil `befreit` | `protokoll.json`, Block `stellprobe` |
| P2 | keine Berührung, kein Eingriff | Christophers Antworten 1 und 2 |
| P3 | kein „Hilfe benötigt“, kein `outcome=error`, kein „process has died“ | Protokoll, `launch.log` |
| P4 | kein Eigenecho: Bereich F in A3 ohne `FEHL`, in A6 keine LiDAR- oder VL53-Punkte im Gehäuse | `vorpruefung.txt`, `nachpruefung_f.txt` |

Stellprobe bestanden: siehe A7. Gemessen, aber kein Kriterium: Zeit bis
0,5 m weg, Zahl, Art und Strecke der Rückfahrten, Zahl „approach“ und
„detected collision ahead“, Zustand des Kollisionsmonitors während jeder
Rückfahrt, wie nah Amadeus dem Hindernis kam (Christopher, Antwort 3).

**Teil B, die volle Fahrt:** C1–C5, G1, R1, R2 wie in SH-8. Eine einzelne
Fahrt bestätigt den Raumwechsel noch nicht; nach MASTERPLAN §9 braucht es
drei. Erfüllt diese Fahrt alle Kriterien, folgen die zwei weiteren als
eigener kurzer Auftrag.

## Bericht: `~/selbstheilung_jetson_bericht_sh8b.md`

1. Kopf: Datum, Release, HEAD, Ergebnis der Schritte 0–4 (Build-Dauer,
   Präfixe, Profilzeilen einschließlich der zwei
   `footprint_clearing_enabled`-Zeilen, Testergebnis), Aufbau mit
   Christophers Antwort wörtlich.
2. **Teil A, Tabelle über alle Proben:** Kennung, Stelle, eingestellte
   Abstände (Christopher), Urteil, Zeit bis 0,5 m weg, Heilungen und
   Rückfahrten bis dahin, größte Entfernung, Zahl „approach“, Zahl „detected
   collision ahead“, Christophers drei Antworten wörtlich.
3. **Teil A, je Probe der Ablauf** aus `ablauf.txt` (wörtlich, gleiche
   aufeinanderfolgende Zeilen zusammenfassen), dazu: Vorprüfung (Exit, Zahl
   OK/FEHL, die Zeilen des Bereichs F wörtlich), Nachprüfung (Zeilen F
   wörtlich), `heilungsverlauf`, `last_track_back`, der Block `rueckfahrten`
   wörtlich, und **für jede Rückfahrt**: Ergebnis des `behavior_server`
   (erfolgreich, Zeitgrenze, „Collision Ahead“), Strecke laut Protokoll,
   Zustand des Kollisionsmonitors davor und währenddessen (besonders, ob
   „approach“ dabei war), welches Ziel danach kam.
4. **Urteil Teil A:** Stellprobe bestanden / nicht bestanden, mit Grund. Für
   jede Probe `nicht_befreit` die Daten wie in SH-8 (`map→odom`, Zellen
   ≥ 99 und = 100 im Umkreis von 1,5 m, Zellen an der Kontur; Werkzeug
   `…/selbstheilung-sh8-20261113_2153/pruefung/werkzeug/sh8_stelle.py`
   nach `$SH_PR/werkzeug/` kopieren und Pfade anpassen).
5. **Teil B**, falls gefahren: wie in SH-8, dazu `rueckfahrten` und die Zahl
   „approach“.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad; je Probe Kennung,
Urteil, Zeit bis 0,5 m weg und Zahl „approach“; Eigenecho-Ergebnis; Stellprobe
bestanden oder nicht; falls gefahren C1–C5, G1, R1, R2 der vollen Fahrt und
die Fahrzeit bis 90 % der freien Endfläche; Kontakte oder Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Besteht die Stellprobe, gilt KM-1 B als
übernommen, und Teil B entscheidet über die zwei weiteren vollen Fahrten
(Prototyp 2). Besteht sie nicht, zuerst die Daten (MASTERPLAN §9 Regel 4);
kein weiterer Versuch ohne neue Auswertung.
