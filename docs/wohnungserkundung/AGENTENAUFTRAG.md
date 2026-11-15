# Aktueller Agentenauftrag: SH-8d – Stellprobe mit KM-2 (Rückzug aus der Sperre), bei Erfolg eine volle Zwei-Raum-Fahrt

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.11.2026 nach
der Auswertung von SH-8c
([Archiv](archive/20261115-sh8c-ausgewertet/README.md), STATUS Abschnitte
15.11.2026 abends).

**Warum:** In SH-8c befreite sich Amadeus an der Ecke zweimal in etwa 92 s
(Rückfahrt 0,31 m in 21 s). **An den Mülleimern nicht:** Er fuhr in der
Langsam-Zone 12 cm schräg an einen Eimer heran; danach lagen VL53-Punkte im
2-cm-Polsterband seiner Kontur. Der Kollisionsmonitor meldete „approach“
und setzte jede Bewegung auf null, **auch die gerade Rückfahrt vom Eimer
weg** (16 s bis zur Zeitgrenze). Danach scheiterte jeder Anlauf, bis „Hilfe
benötigt“ kam. Deine Hinweise zum HWT601-Topic und zur Tempo-Folge waren
richtig; beide Fehler lagen im Werkzeug der Cloud-Sitzung und sind behoben.

**Prüfling ist genau eine Änderung, KM-2** (`c8873c9`, nur im
Selbstheilungsbetrieb): Ein neuer Knoten `monitor_kontur` liefert dem
Kollisionsmonitor die Kontur für die „approach“-Prüfung. Sie ist die volle
gepolsterte Kontur wie bisher, **außer bei einem frischen Befehl „gerade
rückwärts“**; dann ist es die Rückfahrkontur aus AW-1. Vorwärtsfahrt und
Drehen bleiben gesperrt, solange etwas im Polsterband liegt. Die
Langsam-Zone gilt unverändert, auch rückwärts. KM-1 B, Tempo, Rückfahrt,
Budget und Heilungsleiter bleiben wie in SH-8c.

**Unverändert aus SH-8c:** Jeder Start mit `hwt601_accel_ms:=100` (Standard
für den selbstheilenden Betrieb seit 15.11.2026). Amadeus fährt wirklich
das befohlene Tempo (0,135 m/s) und setzt wirklich bis 0,4 m zurück.

**Dazu reine Messungen im Fahrtprotokoll (korrigiert):**

1. **Wackeln** aus dem HWT601, jetzt auf dem richtigen Topic
   (`/shadow/hwt601/imu/data_raw`). Das Protokoll meldet beim Start
   „Messquelle Wackeln: OK“ oder „FEHLT“.
2. **Tempo-Folge**: Weg und Drehung zählen jetzt in Schritten ab 5 mm bzw.
   0,02 rad; die rohe Summe steht zum Vergleich daneben.

**Erwartetes Verhalten an den Mülleimern:** Kommt Amadeus einem Eimer so
nah, dass der Kollisionsmonitor sperrt, bleibt er stehen (wie bisher). Die
folgende Rückfahrt läuft jetzt durch (in der Simulation 0,30 m in 20 s);
danach wählt er ein anderes Ziel und fährt weg. Im Log steht dann einmal
kurz „approach“ und gleich darauf „slowdown“.

**Jede Berührung beendet den ganzen Auftrag.** Alle bestehenden Releases
bleiben unverändert.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/MASTERPLAN.md` §9, im
STATUS die Arbeitsliste und die Abschnitte 15.11.2026, und den Kopf von
`src/robot_navigation/robot_navigation/monitor_kontur.py`. Die Aufträge
SH-8, SH-8b und SH-8c sind archiviert; Teil A und Teil B laufen hier
genauso ab, mit den unten genannten Unterschieden.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 15.11.2026; **Fahrplan §9, Schritt 1, Regeln 1, 4 und 6** (eine Änderung, Korrektur für dasselbe Problem, dieselbe Stellprobe); AGENTS §2.7 (Kollisionsmonitor getrennt ändern und prüfen) |
| WE-Bezug | WE-M3, metrischer Kern im Zwei-Raum-Umfang; Vorstufe zu WE-M4, keine Abnahme von WE-M4; Vorbedingung Stufe 3 (Wohnung) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `c8873c9`; neuer Release `selbstheilung-sh8d-<STAMP>`. SH-8b und SH-8c liefen mit `selbstheilung-sh8b-20261114_1643` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh8d.md`: Build, 209 gezielte Tests, **Teil A** Stellprobe (Mülleimer zweimal, Garderobe zweimal, Ecke einmal) mit Urteil je Probe, Rückfahrstrecken, Kontur-Umschaltungen, Tempo-Folge und Wackeln, **Teil B** nur bei bestandener Stellprobe eine volle Zwei-Raum-Fahrt mit C1–C5, G1, R1, R2 |
| Nicht-Ziele | keine eigene Code- oder Parameteränderung, kein dritter Raum, keine Wohnungsfahrt, keine Tür mit Schwelle, kein Arm, kein Vergleich mit älteren Releases, keine Änderung an Rückfahrtempo, Langsam-Zone oder Anfahrzeit |
| Rückfall | in der Umgebungsdatei `SH_REL` auf `…/selbstheilung-sh8b-20261114_1643` (Stand SH-8c ohne KM-2) zurückstellen; alle Releases bleiben |
| Laborrahmen | LAB-1: aktive Fahrt im beauftragten Umfang ohne erneute Standardfreigaben. Not-Aus-Erreichbarkeit und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden **nicht** erneut abgefragt. Wie in SH-8 entschieden (10.11.2026): In Teil A steht Amadeus beim Start absichtlich 5 cm vor einem Hindernis. Entscheidung des Projektinhabers vom 15.11.2026: 100 ms Anfahrzeit ist Standard |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3;
- schreibend nur: der Stackstart je Probe oder Fahrt, falls die App fehlt
  **genau ein** Missionsstart je Probe oder Fahrt, und in Teil A **genau ein**
  Missionsstopp je Probe (derselbe Befehl wie der Stopp der App, siehe A5);
  kein `param set`, `lifecycle set`, `service call`, kein weiteres
  `topic pub`, keine Nav2-Ziele;
- kein Start ohne `hwt601_accel_ms:=100`, kein Lauf von `antriebsprobe.py`;
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
  ihm nicht kartiert ist (also auch beim ersten Durchfahren der Tür). **Diese
  Werte werden seit SH-8c wirklich gefahren.**
- **Drehen:** Regler 0,25 rad/s, höchstens 0,3125 rad/s.
- **Rückwärts:** entlang der eigenen geraden Spur oder, wenn es keine gibt,
  0,3 m gerade zurück, sofern hinten frei ist; höchstens 0,4 m, 0,05 m/s
  (mit etwas vor ihm 0,015 m/s), einmal je Stillstand.
- **KM-1 B (wie SH-8b):** Hindernisse dicht an ihm bleiben in seiner lokalen
  Karte stehen. Er fährt und dreht nicht in sie hinein, sondern meldet einen
  Fehlschlag und setzt zurück.
- **Neu (KM-2):** Hält ihn der Kollisionsmonitor wegen eines Hindernisses im
  Polsterband fest, darf er trotzdem **gerade** zurücksetzen. Vorwärts und
  Drehen bleiben gesperrt. **Nach hinten sieht er nichts.**
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
  git rev-parse HEAD && git merge-base --is-ancestor c8873c9 HEAD && echo "c8873c9 enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh8d-$STAMP/pruefung
```

### Schritt 2 – Umgebungsdatei

In `~/roboter_worktrees/selbstheilung-v2.env` mit dem Datei-Werkzeug nur die
Zeile `export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/selbstheilung-sh8d-<STAMP>`
ändern. Die Unterbauzeilen bleiben. Prüfen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "rc=$?"; echo "$SH_SRC $SH_REL"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
```

Erwartung: `rc=0`, Zähler `0`.

### Schritt 3 – Build (wie SH-8b)

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

Danach wie in SH-8b prüfen: `Found behaviortree_cpp` unter native-install,
alle 14 Präfixe unter `$SH_REL/product-install` (`prefixes.txt`). Dann die
Profilzeilen (dieselben wie in SH-8b, dazu **neu** die drei KM-2-Zeilen am
Ende):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  grep -n "minimum_travel" "$SH_REL/product-install/amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml"; \
  grep -cE "max_allowed_time_to_collision_up_to_carrot|xy_goal_tolerance" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  grep -nE "desired_linear_vel|rotate_to_heading_angular_vel|max_velocity|min_velocity|footprint_topic|plugins|lidar_layer|clearing|inflation_radius|cost_scaling_factor" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  ls "$SH_REL/product-install/robot_navigation/lib/robot_navigation/rueckfahr_kontur"; \
  grep -nE "self_healing_goal_shift_max_m|self_healing_track_lateral_tolerance_m|self_healing_blocked_track_backs|self_healing_stuck_move_m|overall_timeout_s|self_healing_unknown_speed_mps|initial_scan_angular_speed_radps|self_healing_free_back_m|self_healing_track_back_slow_factor" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"; \
  grep -cE "self_healing_scan_rad|self_healing_scan_spacing_m|self_healing_saturation_|self_healing_attempt_stall_|self_healing_gap_depth_m" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml"; \
  grep -c "footprint_clearing_enabled: False" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  ls "$SH_REL/product-install/robot_navigation/lib/robot_navigation/monitor_kontur"; \
  grep -n "footprint_topic" "$SH_REL/product-install/vl53_near_field/share/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml" "$SH_REL/product-install/vl53_near_field/share/vl53_near_field/config/collision_monitor_mapping_params.yaml"; \
  grep -c "executable='monitor_kontur'" "$SH_REL/product-install/robot_navigation/share/robot_navigation/launch/nav_mapping.launch.py"
```

Erwartet wie in SH-8: `minimum_travel_distance: 0.25`,
`minimum_travel_heading: 0.35`; DR-1-Zähler `0`; Tempo `0.135`, `0.25`,
`[0.162, 0.0, 0.3125]`, `[-0.05, 0.0, -0.3125]`;
`footprint_topic: rueckfahr_kontur`, `plugins` mit `lidar_layer`,
`clearing: True`, `0.60` / `2.5`; Programm `rueckfahr_kontur` vorhanden;
Explorer `0.3`, `0.3`, `0.08`, `0.10`, `0.5`, `0.03`, `0.05`, `2400.0`;
keine Zeile `self_healing_blocked_track_backs`; EK-1-Zähler `0`; KM-1 B:
Zähler `2` (`footprint_clearing_enabled: False`). **Neu (KM-2):** Programm
`monitor_kontur` vorhanden; im Overlay
`footprint_topic: "kollisionsmonitor_kontur"`, im Mapping-Profil weiter
`footprint_topic: "/local_costmap/published_footprint"`; Zähler im Launch
`1`. Jede Abweichung: nicht fahren, berichten. Bei Build-Fehler oder
fehlendem Präfix: nicht fahren, berichten.

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
  src/robot_navigation/test/test_monitor_kontur.py \
  src/robot_bringup/test/test_semantic_map_launch_contract.py \
  src/vl53_near_field/test/test_mapping_collision_contract.py \
  tools/kartierung/test_selbstheilung_stillstand_pruefen.py \
  tools/kartierung/test_selbstheilung_lauf_protokoll.py \
  2>&1 | tee "$SH_PR/tests.log" | tail -40
```

Erwartung: `209 passed` (Cloud, Stand `c8873c9`; neu sind die Datei
`test_monitor_kontur.py` und Tests in den vorhandenen Dateien). Bei
Fehlschlägen nicht fahren, berichten.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern und die Antwort wörtlich
festhalten:

„Bitte für SH-8d aufbauen wie in SH-8c:
1. Dieselbe Tür zwischen Laborraum und Flur ganz öffnen, Türblatt gesichert
   (80 cm, keine Schwelle).
2. Alle anderen Türen beider Räume schließen.
3. In beiden Räumen flache Gegenstände unter etwa 15 cm Höhe vom Boden
   räumen, auch im Türbereich. Die Garderobe im Flur bleibt, wie sie ist.
4. Dieselben zwei Mülleimer und den 5-cm-Abstandshalter bereitlegen.

Amadeus fährt wie in SH-8c wirklich so schnell, wie er soll, und setzt bis
zu 40 cm zurück. Neu: Er darf jetzt auch dann gerade zurücksetzen, wenn er
ganz dicht vor etwas steht. Bitte bleib bei jeder Probe nah bei ihm mit der
Hand am Not-Aus und achte besonders auf sein Heck beim Zurücksetzen und auf
seine Ecken beim Drehen dicht an den Mülleimern.“

Geht die Serie an einem anderen Tag weiter, den Aufbau dann einmal erneut
bestätigen lassen („unverändert“ genügt). Ohne geschlossene übrige Türen
keine Probe und keine Fahrt.

## Teil A – Stellprobe (fünf kurze Proben)

Reihenfolge und Kennung `P`: **s3a, s3b** (Mülleimer, die Stelle, an der
SH-8c scheiterte), **s1a, s1b** (Garderobe), **s2a** (Ecke, einmal als
Gegenprobe; sie war in SH-8c zweimal `befreit`). Jede Probe ist ein
Kaltstart mit neuer Karte und dauert einschließlich Start etwa 5 bis 8
Minuten. `P` in jedem Befehlsblock setzen, weil die Blöcke nicht zwingend
in derselben Shell laufen.

| Stelle | Wo | Wie Amadeus hingestellt wird |
|---|---|---|
| S3 Mülleimer | Laborraum, freie Fläche | zwei Mülleimer nebeneinander, etwa 10 cm Lücke, quer vor Amadeus; seine Front mittig davor, **5 cm** Abstand; hinter ihm mindestens 1 m frei, seitlich je mindestens 0,5 m |
| S2 Ecke | Laborraum, freie Raumecke | gerade in die Ecke hinein: Front **5 cm** vor der Wand, linke Seite **5 cm** neben der Seitenwand; hinter ihm mindestens 1 m frei, rechts mindestens 0,5 m |
| S1 Garderobe | Flur | Front gerade auf die Jacken zu, **5 cm** davor, gemessen an dem Teil, der am weitesten vorsteht (auch oben); hinter ihm mindestens 0,7 m frei |

Abstände mit dem Abstandshalter einstellen (±2 cm), danach den Abstandshalter
wegnehmen. Möglichst dieselben Stellen wie in SH-8c.

### A1. Hinstellen und bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
mkdir -p "$SH_PR/sh8d_$P"
```

Fehlt ein Gerät: nicht fahren, berichten. Christopher einmal je Probe bitten
und die Antwort wörtlich festhalten: „Bitte stelle Amadeus für Probe <P> an
die Stelle <Stelle> wie in der Tabelle. Welche Abstände hast du eingestellt?
Steht er still und bleibt er während des Starts (etwa eine Minute)
unberührt? Ist der Motor-Stop-Schalter freigegeben, reicht der Akku? Stehst
du mit der Hand am Not-Aus daneben?“ Nur nach „ja“ weiter.

### A2. Stack scharf starten (mit 100 ms Anfahrzeit)

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  > "$SH_PR/sh8d_$P/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8d_$P/launch.pid"; cat "$SH_PR/sh8d_$P/launch.pid"
date -Iseconds > "$SH_PR/sh8d_$P/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s (HWT-Einmessung) `nodes.txt` und `lifecycle.txt` erfassen wie
in SH-8b. Erwartet: `/base_hardware`, `/rueckfahr_kontur` und **`/monitor_kontur`**
vorhanden, `/hwt601_encoder_shadow_reader` nicht. Dann:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
grep -n "Anfahrverhalten bestaetigt" "$SH_PR/sh8d_$P/launch.log" | tee "$SH_PR/sh8d_$P/anfahrzeit.txt"
grep -n "monitor_kontur" "$SH_PR/sh8d_$P/launch.log" | head -3
```

Erwartet: **`Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`** und
eine Zeile „Kollisionsmonitor-Kontur auf /kollisionsmonitor_kontur: voll …“.
Fehlt eine davon oder steht ein anderer Wert dort: **keine Mission**, Stack
geordnet beenden, berichten. Meldet der LiDAR-Treiber
„communication is abnormal“ (in SH-8 dreimal beim Start): Stack geordnet
beenden, Christopher einmal bitten, den LiDAR-Stecker zu prüfen, dann einmal
neu starten (zählt zur Gesamtzahl der Starts).

### A3. Vorprüfung mit Eigenechos

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && P=s3a && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 \
  --json "$SH_PR/sh8d_$P/vorpruefung.json" 2>&1 | tee "$SH_PR/sh8d_$P/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0 mit denselben Zeilen wie in SH-8c (Tempowerte, AW-1-Werte,
„Rueckfahrkontur liegt am Behavior-Server an“, „D Quellen“ OK,
`/cmd_vel 3 s ohne Fahrbefehl`, KM-1 B), dazu **neu (KM-2)** im Bereich
`C Verdrahtung`:

- „Kollisionsmonitor-Kontur liegt am Kollisionsmonitor an“: OK
  (`FootprintApproach.footprint_topic` `kollisionsmonitor_kontur`, Publisher
  nur `/monitor_kontur`, Leser `/collision_monitor`);
- „Kollisionsmonitor-Kontur im Stand ist die volle gepolsterte Kontur“: OK
  (Rahmen `base_link`, Ecken ±0,25 m, vorn 0,33 m, hinten −0,13 m);
- „Kollisionsmonitor benutzt diese Kontur (seine eigene Sicht)“: OK, oder
  eine INFO-Zeile „Sicht des Kollisionsmonitors … keine Nachricht“ (dann
  bitte im Bericht vermerken).

**Ein `FEHL` in einer dieser KM-2-Zeilen: nicht fahren, Stack geordnet
beenden, keine Wiederholung, Auftrag beenden und berichten** (die
Detailzeilen wörtlich). Wie bisher:

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
  --json "$SH_PR/sh8d_$P/protokoll.json" \
  --stellprobe-m 0.5 --stellprobe-fenster-s 360 --nachlauf-s 1 --max-s 900 \
  > "$SH_PR/sh8d_$P/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8d_$P/protokoll.pid"
```

Das Protokoll liest nur mit und beendet sich **1 s**, nachdem Amadeus 0,5 m
weg ist (wie in SH-8c). Nach etwa 5 s prüfen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
grep -n "Messquelle Wackeln" "$SH_PR/sh8d_$P/protokoll.txt"
```

Erwartet: `Messquelle Wackeln: OK (/shadow/hwt601/imu/data_raw, 1 Sender)`.
Steht dort `FEHLT`: trotzdem fahren (die Messung ist kein Kriterium), aber
mit `ros2 topic list | grep -i imu` den richtigen Namen festhalten und
berichten.

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
PROT=$(cat "$SH_PR/sh8d_$P/protokoll.pid")
for i in $(seq 480); do kill -0 "$PROT" 2>/dev/null || break; sleep 1; done
kill -0 "$PROT" 2>/dev/null && { kill -INT "$PROT"; sleep 3; }
ENDE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['protokoll_ende'])" "$SH_PR/sh8d_$P/protokoll.json")
echo "protokoll_ende=$ENDE"
if [ "$ENDE" != "missionsende" ]; then
  ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
  date -Iseconds > "$SH_PR/sh8d_$P/missionsstopp.txt"
fi
```

**Warum sofort:** In der Simulation befreite sich Amadeus mit KM-2 von den
Mülleimern, berührte aber 1 bis 3 min später beim Drehen eine Eimerseite,
die die VL53 nie gesehen hatten
(bekannte Grenze: Gegenstände unter 0,75 m sieht nur die VL53, und nur nach
vorn). Nach 0,5 m ist die Probe entschieden; jede weitere Fahrt an den
Eimern bringt nichts.

Der Agent greift sonst nicht ein. Christopher beobachtet aus der Nähe mit
der Hand am Not-Aus; nähert sich eine Ecke **oder eine Seite** von Amadeus
sichtbar einem Hindernis, besonders beim Vorbeifahren an einem Mülleimer,
drückt er (das zählt als Eingriff und beendet den Auftrag). **Besonders in
den Sekunden nach einer Rückfahrt:** Dreht Amadeus dicht neben einem
Mülleimer und kommt eine Ecke näher als etwa zwei Finger breit, drücken.

### A6. Probe sichern

Zuerst das Ergebnis lesen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
tail -40 "$SH_PR/sh8d_$P/protokoll.txt"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print(r['protokoll_ende'], json.dumps(r['stellprobe'], ensure_ascii=False)); [print(k, json.dumps(r[k], ensure_ascii=False)) for k in ('rueckfahrten','tempo_folge','wackeln','fahrbefehle')]" "$SH_PR/sh8d_$P/protokoll.json"
```

Danach, weiterhin nur lesend:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$SH_PR/sh8d_$P/explore_status_ende.txt" 2>&1
grep -o 'last_track_back[^}]*}' "$SH_PR/sh8d_$P/explore_status_ende.txt"
grep -nE "Begin navigating|Goal succeeded|Goal failed|Goal canceled|Controller patience exceeded|Failed to make progress|Running backup|backup completed successfully|backup failed|Collision Ahead|Exceeded time allowance|\[collision_monitor\].*Robot to" \
  "$SH_PR/sh8d_$P/launch.log" > "$SH_PR/sh8d_$P/ablauf.txt"; wc -l "$SH_PR/sh8d_$P/ablauf.txt"
grep -c "detected collision ahead" "$SH_PR/sh8d_$P/launch.log"
grep -c "Robot to approach" "$SH_PR/sh8d_$P/launch.log"
grep -c "process has died" "$SH_PR/sh8d_$P/launch.log"
grep -nE "\[monitor_kontur\].*Kontur: " "$SH_PR/sh8d_$P/launch.log" > "$SH_PR/sh8d_$P/kontur.txt"; wc -l "$SH_PR/sh8d_$P/kontur.txt"
grep -E "CMD: v=|TIMEOUT-STOP" "$SH_PR/sh8d_$P/launch.log" > "$SH_PR/sh8d_$P/basis.txt"; wc -l "$SH_PR/sh8d_$P/basis.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 --json "$SH_PR/sh8d_$P/nachpruefung.json" 2>&1 | grep -E "F Eigenechos|ERGEBNIS" | tee "$SH_PR/sh8d_$P/nachpruefung_f.txt"
timeout 15 ros2 topic echo --once --full-length /local_costmap/costmap > "$SH_PR/sh8d_$P/lokale_kostenkarte_ende_voll.txt" 2>&1
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
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$SH_PR/sh8d_$P/tf_map_base_link.txt" 2>&1
timeout 8 ros2 run tf2_ros tf2_echo odom base_link > "$SH_PR/sh8d_$P/tf_odom_base_link.txt" 2>&1
```

Christopher einmal fragen und wörtlich festhalten. Die Fragen **wörtlich
und ohne Hinweis auf Messwerte** stellen, jede als eigene Frage mit freiem
Text:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Was hast du gesehen: zurückgesetzt, gedreht, gestanden? In welcher
   Reihenfolge, und wie nah kam er dem Hindernis dabei (sichtbare Lücke,
   etwa wie viele Zentimeter)? Wie viel Platz blieb hinter ihm beim
   Zurücksetzen?
4. Hat der Aufbau (Mast, Kamera) sichtbar gewackelt oder geruckt? Wenn ja:
   beim Anfahren, beim Anhalten, beim Drehen oder mitten in der Fahrt?

Danach den Stack geordnet beenden (SIGINT nur an die Launch-PID,
`roboterknoten.py` danach leer). Läuft das Protokoll noch, es vorher per
SIGINT an `protokoll.pid` beenden.

### A7. Urteil je Probe und wie es weitergeht

| Urteil | Bedeutung | Weiter |
|---|---|---|
| `befreit` | mindestens eine Heilung, danach 0,5 m vom Standort weg, innerhalb von 6 min | nächste Probe |
| `nicht_blockiert` | ohne Heilung weggefahren: Die Stelle hat ihn nicht blockiert, die Probe sagt nichts aus | **Mülleimer und Ecke:** einmal wiederholen mit **3 cm** statt 5 cm (Kennung mit Zusatz `_nah`, zum Beispiel `s3a_nah`); bleibt es dabei, als „Stelle blockiert nicht“ berichten und weiter. **Garderobe: keine Wiederholung mit 3 cm** (in SH-8c ragten die Jacken dabei in die Kontur); als „Stelle blockiert nicht“ berichten und weiter |
| `nicht_befreit` | nach 6 min nicht 0,5 m weg, oder „Hilfe benötigt“ | die zweite Probe **derselben** Stelle entfällt (kein identischer Fehlversuch); mit der nächsten Stelle weiter |
| Berührung, Eingriff, `outcome=error`, „process has died“, Eigenecho (A3 oder A6), falsche Anfahrzeit oder fehlende Kontur (A2), `FEHL` in einer KM-2-Zeile (A3) | | **Auftrag beenden**, nur berichten |

Höchstens zehn Starts mit Mission in Teil A, höchstens zwölf Starts
insgesamt (Starts, die „D Quellen“ oder ein LiDAR-Startfehler vor der
Mission abfängt, zählen nur zur Gesamtzahl). Laden zwischen den Proben ist
erlaubt.

**Stellprobe bestanden**, wenn keine Probe mit `nicht_befreit`, Berührung,
Eingriff oder Eigenecho endete, die **Mülleimer mindestens einmal `befreit`**
ergaben und die Ecke `befreit` ergab. Die Garderobe darf `befreit` oder
„Stelle blockiert nicht“ sein. **Nur dann folgt Teil B.** Sonst: Auftrag
hier beenden und berichten.

## Teil B – eine volle Zwei-Raum-Fahrt (nur nach bestandener Stellprobe)

Genau wie Teil B im
[SH-8-Auftrag](archive/20261113-sh8-ausgewertet/AGENTENAUFTRAG.md)
(Schritte 1–7, Fragen, Kriterien), mit diesen Unterschieden:

- Ordner `"$SH_PR/sh8d_run$RUN"` statt `sh8_run$RUN`, `RUN=voll`;
- der Stackstart **mit `hwt601_accel_ms:=100`** (wie A2), danach dieselben
  zwei Prüfzeilen („Anfahrverhalten bestaetigt … 100 ms“, „monitor_kontur“);
- das Fahrtprotokoll ohne `--stellprobe-m` wie in SH-8, nach 5 s die Zeile
  „Messquelle Wackeln“ prüfen wie in A4;
- in Schritt 3 die Vorprüfung **mit** `--eigenecho-s 10`; erwartet wie in A3
  einschließlich der KM-2-Zeilen (Amadeus steht am Startplatz mit etwa 0,5 m
  Platz rundherum);
- in Schritt 7 zusätzlich `grep -c "Robot to approach"` auf `launch.log`,
  `kontur.txt` und `basis.txt` wie in A6 und die Blöcke `rueckfahrten`,
  `tempo_folge` und `wackeln` aus `protokoll.json` sichern;
- **Amadeus fährt jetzt wirklich 0,135 m/s.** Die Fahrt dürfte deutlich
  kürzer dauern als die bisherigen (Budget weiter 40 Minuten). Christopher
  geht mit und bleibt mit der Hand am Not-Aus in seiner Nähe, besonders an
  der Tür, an Möbeln und bei jeder Rückfahrt;
- **Hinweis vom 14.11.2026 (Simulation):** Nach einer Türdurchfahrt stieß
  Amadeus dort beim Zurücksetzen mit dem Heck an den Türpfosten; nach hinten
  sieht er nichts. Christopher vor der Fahrt einmal darauf hinweisen: Setzt
  Amadeus **in Türnähe oder dicht vor einer Wand hinter ihm zurück**, den
  Not-Aus drücken, bevor das Heck etwas erreicht (zählt als Eingriff).

**Abweichung von SH-8:** In Teil B stehen **keine** Mülleimer in den beiden
Räumen (vorher hinausstellen; Christopher bestätigt das in Schritt 1). Die
Eimer prüft Teil A; seitlich an niedrigen Gegenständen vorbei ist eine
bekannte, getrennt geparkte Grenze. Die Garderobe bleibt.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei:
  - Berührung, auch leicht, auch an Mülleimer, Jacke, Türrahmen oder Türblatt;
  - Fahrt oder Drehung auf ein Hindernis ohne rechtzeitiges Abbremsen;
  - Rückfahrt auf etwas zu, das hinter ihm steht;
  - starkem Schwanken des Aufbaus;
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
SH-8b und SH-8c.

**Teil A, je Probe:**

| Nr | Kriterium | Quelle |
|---|---|---|
| P1 | Urteil `befreit` | `protokoll.json`, Block `stellprobe` |
| P2 | keine Berührung, kein Eingriff | Christophers Antworten 1 und 2 |
| P3 | kein „Hilfe benötigt“, kein `outcome=error`, kein „process has died“ | Protokoll, `launch.log` |
| P4 | kein Eigenecho: Bereich F in A3 ohne `FEHL`, in A6 keine LiDAR- oder VL53-Punkte im Gehäuse | `vorpruefung.txt`, `nachpruefung_f.txt` |

Stellprobe bestanden: siehe A7. Gemessen, aber kein Kriterium: Zeit bis
0,5 m weg; Zahl, Art, Dauer und Strecke der Rückfahrten; **wie oft und wann
die Kontur auf „Rückzug“ und zurück auf „voll“ schaltete** (`kontur.txt`);
Zahl „approach“ und „detected collision ahead“; Zustand des
Kollisionsmonitors während jeder Rückfahrt; `tempo_folge` und `wackeln`;
wie nah Amadeus dem Hindernis kam und wie viel Platz hinten blieb
(Christopher).

**Teil B, die volle Fahrt:** C1–C5, G1, R1, R2 wie in SH-8. Eine einzelne
Fahrt bestätigt den Raumwechsel noch nicht; nach MASTERPLAN §9 braucht es
drei. Erfüllt diese Fahrt alle Kriterien, folgen die zwei weiteren als
eigener kurzer Auftrag.

## Bericht: `~/selbstheilung_jetson_bericht_sh8d.md`

1. Kopf: Datum, Release, HEAD, Ergebnis der Schritte 0–4 (Build-Dauer,
   Präfixe, Profilzeilen einschließlich der KM-2-Zeilen, Testergebnis),
   Aufbau mit Christophers Antwort wörtlich.
2. **Teil A, Tabelle über alle Proben:** Kennung, Stelle, eingestellte
   Abstände (Christopher), Urteil, Zeit bis 0,5 m weg, Heilungen und
   Rückfahrten bis dahin, größte Entfernung, Zahl „approach“, Zahl „detected
   collision ahead“, Zahl der Umschaltungen auf „Rückzug“,
   `weg_gefahren_zu_befohlen`, `drehung_gedreht_zu_befohlen`, größtes
   Wackeln (rad/s) mit Lage, Christophers vier Antworten wörtlich.
3. **Teil A, je Probe der Ablauf** aus `ablauf.txt` (wörtlich, gleiche
   aufeinanderfolgende Zeilen zusammenfassen), dazu: Vorprüfung (Exit, Zahl
   OK/FEHL, die Zeilen des Bereichs F wörtlich), Nachprüfung (Zeilen F
   wörtlich, die KM-2-Zeilen aus Bereich C wörtlich), `heilungsverlauf`,
   `last_track_back`, die Blöcke `rueckfahrten`, `tempo_folge` und `wackeln`
   wörtlich, `kontur.txt` wörtlich, und **für jede Rückfahrt**: Ergebnis des
   `behavior_server` (erfolgreich, Zeitgrenze, „Collision Ahead“), Strecke
   laut Protokoll, Zustand des Kollisionsmonitors davor und währenddessen
   (besonders, ob „approach“ dabei war und wie lange), die zugehörigen
   Zeilen aus `kontur.txt`, welches Ziel danach kam.
4. **Urteil Teil A:** Stellprobe bestanden / nicht bestanden, mit Grund. Für
   jede Probe `nicht_befreit` die Daten wie in SH-8 (`map→odom`, Zellen
   ≥ 99 und = 100 im Umkreis von 1,5 m, Zellen an der Kontur; Werkzeug
   `…/selbstheilung-sh8-20261113_2153/pruefung/werkzeug/sh8_stelle.py`
   nach `$SH_PR/werkzeug/` kopieren und Pfade anpassen).
5. **Teil B**, falls gefahren: wie in SH-8, dazu `rueckfahrten`,
   `tempo_folge`, `wackeln`, `kontur.txt` und die Zahl „approach“; die
   Fahrzeit bis 85, 90 und 95 % der freien Endfläche.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad; je Probe Kennung,
Urteil, Zeit bis 0,5 m weg, Zahl „approach“ und Zahl der Umschaltungen auf
„Rückzug“; Eigenecho-Ergebnis; größtes Wackeln; Stellprobe bestanden oder
nicht; falls gefahren C1–C5, G1, R1, R2 der vollen Fahrt und
die Fahrzeit bis 90 % der freien Endfläche; Kontakte oder Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Stellprobe bestanden und volle Fahrt mit
allen Kriterien: Das aktive Problem „sitzt fest“ gilt als gelöst, KM-1 B
und KM-2 als bestätigt; es folgen die zwei weiteren vollen Fahrten als
eigener kurzer Auftrag (MASTERPLAN §9). Sonst: zuerst die Daten (Regel 4),
kein weiterer Versuch ohne neue Auswertung.
