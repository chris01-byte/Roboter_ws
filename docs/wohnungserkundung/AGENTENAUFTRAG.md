# Aktueller Agentenauftrag: SH-1 v3 – motorlose Jetson-Prüfung `self_healing`

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.10.2026 vom
Projektinhaber („schreibe jetzt in die Datei, was der lokale KI-Agent auf dem
Jetson genau machen soll und was er reporten soll“). Der bisherige AP-06-Auftrag
ist [bytegleich archiviert](archive/20261015-ap06-eingefroren/README.md).

**v3 ersetzt SH-1 v2** (Commit `6d96202`). Der v2-Lauf vom 15.10.2026
23:05–23:07 war sauber: Unterbaukette eindeutig aus dem v17-`runtime.bash`,
Umgebung ohne `roboter_ws/install`, 4 von 14 Paketen gebaut. `bt_orchestrator`
scheiterte, weil CMake das System-`behaviortree_cpp` 4.9.1 wählte, dessen Export
eine nicht vorhandene Nicht-Multiarch-Bibliothek sucht. Diese Jetson-Eigenheit
ist bekannt (ROBOT_TRANSFER „Buildbesonderheit“). Der v17-Build übergibt deshalb
`-Dbehaviortree_cpp_DIR=…/native-install/…` und `-DBUILD_TESTING=ON`; v2 hatte
beides nicht. v3 übernimmt das v17-Buildskript wörtlich, nur Quell- und
Zielpfade sind getauscht. Quelle des Skripts:
`docs/wohnungserkundung/evidence/ap06-correction-v17-20261011.json`, Feld
`build_script`.

**v2 ersetzte SH-1 v1** (Commit `7493d9f`). Der v1-Lauf vom 15.10.2026 22:24–22:26
stoppte korrekt am Build. Ursachen, alle im Auftrag und nicht beim Agenten:

1. v1 baute auf `~/roboter_ws/install` auf. Das ist der August-Stand `23928d9`
   und enthält kein `amadeus_map_identity`. Die AP06-Kandidaten v11–v17 wurden
   dagegen als 14-Paket-Build in eigenen Release-Ordnern unter
   `~/.local/share/amadeus/releases/` gebaut, mit wiederverwendeten Unterbauten.
   v2 folgt genau diesem Muster.
2. `git fetch` in `~/roboter_ws` scheitert an einer defekten Codex-Referenz
   (`refs/codex/turn-diffs/…`). v2 arbeitet deshalb mit einem eigenen frischen
   Klon und fasst `~/roboter_ws` gar nicht an.
3. Die v1-Umgebungsdatei endete mit `[ -f … ] && source …` und lieferte Exit 1,
   solange nichts gebaut war. Die v2-Datei endet immer mit Exit 0.

Diese Datei auf dem Branch `claude/blissful-pasteur-s1eivj` lesen: über die
GitHub-Ansicht des Branches oder nach Schritt 2 im neuen Klon. Vorher lesen,
ebenfalls vom Branch: `AGENTS.md`, `docs/LABORMODUS.md` (LAB-1),
`docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md` §6, §10, §11.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen vom 15.10.2026 (`self_healing` Hauptlinie, AP06 eingefroren, Abnahmeleiter) |
| WE-Bezug | WE-M0 (Zielsystem-Vorlauf) und WE-M3 (metrischer Erkundungskern); Vorbedingung für Abnahmestufe 1 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens Commit `e123902`. Bisher nur in der Cloud geprüft (ROS 2 Jazzy, Python 3.12). Jetson-Bestand: `~/roboter_ws` `main` `23928d9` (August), AP06 v17 als Release `ap06-correction-v17-20261011` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_v3.md`: Unterbaukette, 14-Paket-Build, 142 gezielte Tests, Prüfskript A–D über den App-Start und die VL53-Messreihe |
| Nicht-Ziele | siehe „Verboten“; keine Fahrt, keine Korrektur, keine Filteränderung |
| Tests | 142 gezielte Tests (in der Cloud grün), Prüfskript `selbstheilung_stillstand_pruefen.py` |
| Rückfall | Release-Ordner und Klon nicht mehr sourcen; `~/roboter_ws`, dessen Installation und alle bisherigen Releases bleiben unverändert |
| Laborrahmen | LAB-1, motorloser Pfad nach §3 (`active_drive=false`); keine Standardfreigabefragen |

## Verboten in diesem Auftrag

- `active_drive:=true`, `enable_auto_explore:=true`, `AMADEUS_FAHRFREIGABE=JA`,
  Missionen, Navigationsziele, App-Erkundung, `operator_stationary_confirmed:=true`.
- `ros2 topic pub`, `ros2 service call`, `ros2 action send_goal`,
  `ros2 param set`, `ros2 lifecycle set`. Erlaubt sind nur lesende Befehle
  (`node list`, `topic list/info/hz`, `param get`, `lifecycle get`, `pkg prefix`).
- Irgendetwas in `~/roboter_ws` (auch kein `fetch`) und die defekte
  Codex-Referenz anfassen; bestehende Releases verändern; den v1-Ordner
  `~/roboter_worktrees/selbstheilung` löschen oder umbauen.
- Code-, Parameter- oder Filteränderungen, auch „nur zum Testen“. Fehler werden
  berichtet, nicht behoben.
- Commit, Push, Merge, Pull Request.
- Prozessgruppen signalisieren, `pkill -f`/`killall`, `kill -9` auf fremde Prozesse.
- In den Bericht: Geheimnisse, Tokens, WLAN-Daten, IP-Adressen, Karten,
  Kamerabilder, Bags.

## Ablauf

Shellzustand bleibt zwischen Agentenbefehlen nicht erhalten. Ab Schritt 4
beginnt deshalb jeder ROS-Befehl mit `source ~/roboter_worktrees/selbstheilung-v2.env`.

### Schritt 1 – Bestand und Unterbaukette nur lesen

```bash
date -Iseconds
python3 --version; printenv ROS_DISTRO ROS_DOMAIN_ID ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION CYCLONEDDS_URI
printenv AMENT_PREFIX_PATH | tr ':' '\n'
grep -nE "roboter_ws|setup\.bash|ROS_DOMAIN_ID|CYCLONEDDS|RMW" ~/.bashrc
git -C ~/roboter_ws rev-parse HEAD; git -C ~/roboter_ws status --short | head -10
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls -d ~/.local/share/amadeus/releases/*/
R17=$HOME/.local/share/amadeus/releases/ap06-correction-v17-20261011
ls -la "$R17"
find "$R17" -maxdepth 2 -type f \( -name "*.bash" -o -name "*.sh" -o -name "*.env" -o -name "*.json" \) | sort
grep -rhoE "$HOME/[^\"' :]*(native-install|lidar/install|install|/python)\b" "$R17" \
  --include=*.bash --include=*.sh --include=*.env --include=*.json --include=*.txt 2>/dev/null \
  | sort | uniq -c | sort -rn | head -30
```

**Unterbaukette festlegen:** genau die Präfixe, mit denen v17 gebaut und
gestartet wurde, **ohne** dessen eigenes `product-install`. Vorrang hat ein
Laufzeitskript im v17-Release (etwa `runtime.bash`). Seine `source`- und
`PYTHONPATH`-Zeilen in Originalreihenfolge übernehmen. Gibt es keins, gilt die
Reihenfolge aus `JETSON_KONZEPTTEST_AP06.md`: `/opt/ros/humble` → `PYTHONPATH`
mit `…/python` → `native-install` → `lidar/install`, jeweils mit den Pfaden,
die Manifest oder Skripte des v17-Releases nennen. `~/roboter_ws/install` gehört
nicht dazu.

Ist die Kette nicht eindeutig: hier stoppen und die Ausgaben oben berichten,
nicht raten. Läuft ein Robotik-Stack: nichts beenden und Christopher genau
einmal fragen, ob er geordnet beendet werden darf.

### Schritt 2 – Klon aktualisieren und neuer Release-Ordner

Der Klon `~/roboter_worktrees/selbstheilung-v2` aus dem v2-Lauf wird
weiterverwendet. Er ist ein eigenes Repository ohne die defekte Referenz:

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && \
  git pull --ff-only && git rev-parse HEAD && \
  git merge-base --is-ancestor e123902 HEAD && echo "e123902 enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh1-$STAMP/pruefung
```

`git status --short` muss leer sein. Fehlt der Klon oder scheitert
`pull --ff-only`: frisch klonen nach `~/roboter_worktrees/selbstheilung-v3`:

```bash
git clone --branch claude/blissful-pasteur-s1eivj --single-branch --depth 50 \
  https://github.com/chris01-byte/Roboter_ws.git ~/roboter_worktrees/selbstheilung-v3
```

Danach diesen Pfad in Schritt 3 als `SH_SRC` eintragen. Der v2-Release-Ordner
`selbstheilung-sh1-20261015_2305` bleibt unverändert liegen; neu wird in den
Ordner mit dem neuen `STAMP` gebaut, damit kein alter CMake-Cache mitwirkt.

### Schritt 3 – Umgebungsdatei

Die Datei `~/roboter_worktrees/selbstheilung-v2.env` aus dem v2-Lauf
weiterverwenden. Mit dem Datei-Werkzeug nur die Zeile `export SH_REL=…` auf den
neuen `STAMP` ändern, bei einem neuen Klon auch `SH_SRC`. Die Unterbauzeilen
bleiben wie im v2-Lauf (aus dem v17-`runtime.bash`, Zeilen 2–5). Sollform:

```bash
# SH-1 v2: nur diese Kette, kein ~/roboter_ws/install
for v in AMENT_PREFIX_PATH CMAKE_PREFIX_PATH COLCON_PREFIX_PATH ROS_PACKAGE_PATH PYTHONPATH; do unset "$v"; done
export LD_LIBRARY_PATH="$(printf '%s' "${LD_LIBRARY_PATH:-}" | tr ':' '\n' | grep -vE '/(roboter_ws|roboter_worktrees)/' | paste -sd: -)"
source /opt/ros/humble/setup.bash
# <Unterbauzeilen aus Schritt 1 in Originalreihenfolge, z. B. PYTHONPATH, native-install, lidar/install>
export SH_SRC="$HOME/roboter_worktrees/selbstheilung-v2"
export SH_REL="$HOME/.local/share/amadeus/releases/selbstheilung-sh1-<STAMP>"
export SH_PR="$SH_REL/pruefung"
if [ -f "$SH_REL/product-install/local_setup.bash" ]; then source "$SH_REL/product-install/local_setup.bash"; fi
true
```

Prüfen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "rc=$?"; echo "$SH_SRC $SH_REL"
printenv AMENT_PREFIX_PATH | tr ':' '\n'
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
```

Erwartung: `rc=0`, kein Eintrag mit `roboter_ws/install` (Zähler `0`).

### Schritt 4 – 14-Paket-Build in den Release-Ordner

Vorher das v17-Buildskript auf dem Jetson lesen und mit der Quelle im Repo
vergleichen:

```bash
cat -n ~/.local/share/amadeus/releases/ap06-correction-v17-20261011/build.bash
```

Es muss dieselben `--cmake-args` enthalten wie unten. Weicht es ab, gilt das
Skript auf dem Jetson: seine `--cmake-args` wörtlich übernehmen und die
Abweichung berichten. Build wie v17, nur mit eigenen Quell-, Log-, Build- und
Installpfaden:

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

Der explizite `behaviortree_cpp_DIR` gilt nur beim Bauen. Er umgeht den
bekannten fehlerhaften Systemexport; keine Systembibliothek wird verändert.
Danach prüfen, welche BT.CPP-Version gefunden wurde:

```bash
grep -h "Found behaviortree_cpp" "$SH_REL"/product-log/latest_build/bt_orchestrator/stdout*.log
```

Erwartung: Pfad unter `ap06-20261010T070231Z/native-install`, nicht `/opt/ros/humble`.

Danach (die Umgebungsdatei sourct jetzt das neue `product-install`):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && for p in amadeus_map_identity base_hardware \
  robot_interfaces bt_orchestrator mission_manager robot_state_estimation explore robot_navigation \
  robot_map_manager vl53_near_field safety_monitor amadeus_lidar_bringup robot_bringup \
  semantic_map_manager; do printf '%-24s %s\n' "$p" "$(ros2 pkg prefix "$p" 2>&1)"; done \
  | tee "$SH_PR/prefixes.txt"
```

Alle 14 Präfixe müssen unter `$SH_REL/product-install` liegen. Bei Build-Fehler
oder einem anderen Präfix entfallen die Schritte 5–8; weiter mit dem Bericht.
Keinen zweiten Build mit selbst erdachten Änderungen versuchen.

### Schritt 5 – gezielte Tests, isolierte ROS-Domain

Vor dem Stackstart. Die Tests erzeugen synthetische ROS-Daten, deshalb läuft
der Test in einer anderen Domain als der Roboter (Roboter: 42, Test: 227) und
nur lokal. Die Cyclone-Konfiguration des Roboters bleibt dabei außen vor:

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
  tools/kartierung/test_selbstheilung_stillstand_pruefen.py \
  2>&1 | tee "$SH_PR/tests.log" | tail -40
```

Erwartung: `142 passed` (Cloud). Fehlschläge nicht beheben; die vollständige
Fehlermeldung in den Bericht und mit Schritt 6 weitermachen (motorlos, ohne
Wirkung).

### Schritt 6 – App-Stack motorlos starten

Normale Roboterumgebung aus `~/.bashrc` (Domain 42, CycloneDDS mit
`CYCLONEDDS_URI`), also **ohne** die Testvariablen aus Schritt 5 und ohne die
v17-Testzeile `ROS_DOMAIN_ID=166 … rmw_fastrtps_cpp`. Gestartet
wird der App-Weg, den auch die spätere Laborfahrt nutzt, ohne Web-GUI:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
```

Nur wenn nichts läuft:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  > "$SH_PR/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/launch.pid"; cat "$SH_PR/launch.pid"
```

`env --default-signal=INT` ist nötig: Ein mit `&` gestarteter Prozess einer
nicht interaktiven Shell ignoriert sonst SIGINT, und der geordnete Stopp aus
Schritt 9 liefe ins Leere (gemessen 15.10.2026). Die gespeicherte PID ist die
des `ros2 launch`-Prozesses. `active_drive` und `enable_auto_explore` bleiben
auf ihrem Standard `false`.

Nach etwa 30 s lesend erfassen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && ros2 node list | sort | tee "$SH_PR/nodes.txt"
source ~/roboter_worktrees/selbstheilung-v2.env && \
  for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
    echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$SH_PR/lifecycle.txt"
grep -nE "ERROR|FATAL|Failed|Managed nodes are active|self_healing|Timed out" "$SH_PR/launch.log" | head -80
```

Ohne `active_drive` integriert die Basis nur Sollwerte (null); TF-Wartemeldungen
sind möglich. Berichten, nicht beheben.

### Schritt 7 – Prüfskript A–D

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" \
  --json "$SH_PR/pruefung_AD.json" 2>&1 | tee "$SH_PR/pruefung_AD.txt"; echo "exit=${PIPESTATUS[0]}"
```

Exit 0 = bestanden, 1 = mindestens ein `FEHL`, 2 = Explorer nicht erreichbar.
Bei Exit 2 oder `FEHL` mit „erreichbar“/„nicht deklariert“: einmal nach 30 s
wiederholen (langsamer Lifecycle-Start), beide Ausgaben berichten.

### Schritt 8 – VL53-Messreihe (braucht Christopher)

Christopher legt die Objekte; das ist die einzige Bedienhandlung, die der
Agent anfordert. Je Messung genau einmal ansagen, was wohin gelegt wird, und
auf „liegt“ warten. Danach steht niemand vor dem Roboter (seitlich oder
dahinter, mindestens 1 m Abstand zum Sichtbereich).

Objekt: matt, hell, nicht spiegelnd; mindestens 10 cm breit und 20 cm tief
(Karton, Bücherstapel). Mittig vor dem Roboter. Abstand = Fahrzeugfront bis
Vorderkante des Objekts.

| Nr | Höhe | Abstand ab Front |
|---|---|---|
| 0 | kein Objekt, mindestens 1 m frei | – |
| 1 | 3 cm | 0,30 m |
| 2 | 6 cm | 0,30 m |
| 3 | 10 cm | 0,30 m |
| 4 | 15 cm | 0,30 m |
| 5 | 3 cm | 0,38 m |
| 6 | 6 cm | 0,38 m |
| 7 | 10 cm | 0,38 m |
| 8 | 15 cm | 0,38 m |

Je Messung (Nummer und Notiz anpassen):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" \
  --beobachten-s 1 --vl53-s 10 --notiz "Nr 2: 6 cm, 0,30 m" \
  --json "$SH_PR/vl53_02.json" 2>&1 | tee "$SH_PR/vl53_02.txt"
```

Erwartung aus der Geometrie (zu prüfen, nicht vorwegnehmen): unterste
Sensorzeile bis −30°, Sensor 0,305 m über Boden, gültig nur bis 0,50 m
Messdistanz. Sehr flache Objekte erscheinen vermutlich gar nicht; Treffer
unter etwa 0,14 m über Boden zählt das Skript als `verworfen`. Ist
Christopher nicht verfügbar: Schritt 8 auslassen und das im Bericht vermerken.

### Schritt 9 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && PID=$(cat "$SH_PR/launch.pid") && \
  kill -INT "$PID" && for i in $(seq 1 30); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done; \
  kill -0 "$PID" 2>/dev/null && echo "LAUNCH LAEUFT NOCH" || echo "Launch beendet nach ${i}s"
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

SIGINT nur an die Launch-PID, nie an die Gruppe. Läuft der Launch nach 30 s
noch: einmal `kill -TERM` an dieselbe PID, 15 s warten. Danach übrige eigene
Knoten einzeln per PID mit SIGINT beenden und im Bericht auflisten.

### Abbruchregeln

Sofort Schritt 9 und dann Bericht, ohne Wiederholung, bei:

- sichtbarer oder hörbarer Rad-/Motorbewegung;
- `FEHL` in „D Stillstand“ (`dry_run`, `allow_rs485` oder `/cmd_vel` ungleich null);
- ausgelöstem Not-Aus oder einem „Stopp“ von Christopher;
- einem zweiten Robotik-Stack, der während der Prüfung auftaucht.

## Bericht: `~/selbstheilung_jetson_bericht_v3.md`

Markdown, Deutsch, Zahlen und Ausgaben wörtlich. Lange Logs auf die relevanten
Zeilen kürzen und das kenntlich machen. Rohdateien bleiben in `$SH_PR`.

1. **Kopf:** Datum/Uhrzeit Start und Ende, `SH_SRC`, `SH_REL`, HEAD des Klons,
   Ausgabe „e123902 enthalten“, ROS-Distribution, `python3 --version`.
2. **Bestand vorher:** HEAD und `git status --short` von `~/roboter_ws`;
   `roboterknoten.py`; die Umgebungsvariablen aus Schritt 1; die
   `~/.bashrc`-Treffer; `AMENT_PREFIX_PATH` vor dem Sourcen.
3. **Unterbaukette:** Quelle (Datei und Zeilen im v17-Release), übernommene
   Zeilen wörtlich, Inhalt von `selbstheilung-v2.env`, Ergebnis der Prüfung aus
   Schritt 3 (`rc`, Zähler `roboter_ws/install`).
4. **Build:** Ausgabe von `cat -n …/build.bash` und die tatsächlich
   verwendeten `--cmake-args`; `rc`, Dauer, die letzten 25 Zeilen; die
   `Found behaviortree_cpp`-Zeile; `prefixes.txt` vollständig; bei Fehler die
   letzten 60 Zeilen von `build.log` und das Log des fehlgeschlagenen Pakets.
5. **Tests:** Zusammenfassungszeile (`N passed, M failed …`), Laufzeit; bei
   Fehlern Testname und vollständige Fehlermeldung.
6. **Stackstart:** Startbefehl, Zahl der Knoten, `nodes.txt`, `lifecycle.txt`,
   die `grep`-Zeilen aus `launch.log`.
7. **Prüfung A–D:** vollständige Ausgabe von `pruefung_AD.txt` und Exitcode,
   bei Wiederholung beide.
8. **VL53:** Tabelle je Messung Nr | Notiz | links: Punkte/verworfen/behalten/
   Höhe min–max über Boden/getroffene Zeilen | rechts: dasselbe. Danach der
   `vl53`-Teil jeder JSON-Datei wörtlich. Fehlende Messungen mit Grund.
9. **Beenden:** wie beendet, Wartezeit, Ausgabe von `roboterknoten.py` danach.
10. **Auffälligkeiten:** alles Unerwartete, jede Abweichung von diesem Auftrag
    mit Grund, Beobachtungen von Christopher getrennt von Messwerten.
11. **Nicht ausgeführt:** Schritte, die entfallen sind, und warum.

Am Ende im Chat nur melden: Pfad des Berichts, Ergebnis A–D (bestanden/nicht
bestanden), Zahl der Testfehlschläge, ob die VL53-Reihe vollständig ist.
Christopher lädt den Bericht in die Cloud-Sitzung hoch.

## Danach

Auswertung in der Cloud-Sitzung. Erst bei bestandenem A–D folgt Abnahmestufe 1
(drei begrenzte Laborfahrten nach LAB-1) als eigener Auftrag; dort wird auch
der Odometriepfad (HWT601-Fusion wie v17 oder Standard) festgelegt. Eine
Änderung der VL53-Höhenfilter ist eine getrennte Sicherheitsänderung und nicht
Teil von SH-1. Die defekte Codex-Referenz in `~/roboter_ws` und der v1-Ordner
`~/roboter_worktrees/selbstheilung` bleiben bis zu Christophers Entscheidung
unverändert.
