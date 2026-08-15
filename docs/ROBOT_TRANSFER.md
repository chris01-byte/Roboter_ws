# Übertragung auf den realen Roboter

## Abnahmestand reale semantische Raumfahrt (15.08.2026)

**Branch:** `feature/reale-raumfahrt`

Dieser Abschnitt ersetzt fuer neuere Stände die Aussage vom 14.08.,
`go_to_room` sei immer simuliert. Der sichere Standard ist weiterhin
Simulation; nur `enable_real_go_to_room:=true` aktiviert den getrennten
Nav2-Pfad.

### Real bestandener Vertrag

- Ein Karten- und Revisions-gebundenes semantisches Raumziel wird als
  `NavigateToPose` gesendet.
- Der verpflichtende Behavior Tree enthält keine Recovery-Manöver: kein
  automatisches Rueckwaertsfahren und kein selbststaendiges Drehen nach einem
  Fehler.
- Nav2 publiziert auf `/cmd_vel_nav_raw`. Das fail-closed
  `cmd_vel_mission_gate` gibt nur eine frische, laufende `go_to_room`-Mission
  auf `/cmd_vel_nav` frei.
- Der `velocity_smoother` arbeitet `OPEN_LOOP`; danach folgt der
  `collision_monitor`, erst dann `/cmd_vel` und `base_hardware`.
- Der Nav2-Unterzieltimeout ist 2000 ms. Die reale Unterzielannahme benoetigte
  in einem Messlauf rund 590 ms; der alte 20-ms-Wert konnte einen Fehler
  melden, bevor das Unterziel angenommen war.
- Der Fortschrittspruefer ist auf 0,10 m in 20 s gesetzt. Die alte Schwelle
  0,30 m/15 s war mit der bestaetigten 2000-ms-Hardware-Rampe unvereinbar und
  brach freie Fahrt nach rund 0,19 m ab.

Der abschliessende beaufsichtigte Bodenlauf erreichte sein Ziel nach 1,084 m
Encoderweg. Der lange Geradeausabschnitt blieb innerhalb 0,14 Grad, das finale
Einlenken innerhalb 3,28 Grad. Alle vier Stufen der Befehlskette blieben bei
maximal 0,100 m/s und 0,149 rad/s. Nach Erfolg wurden Gate, reale
Istgeschwindigkeit und beide Motoren bei null bestaetigt; es blieb kein
verwaister Nav2-Rohbefehl. Beide VL53-Datenstroeme waren frisch, Encoder und
Modbus fehlerfrei.

### Pruefung vor jeder weiteren Realfahrt

1. Roboterpose nicht aus Kartenkoordinaten raten. Der bislang abgenommene Lauf
   verwendete einen bewusst gesetzten statischen `map -> odom`-Startbezug.
2. Freie Raeder/Fahrbahn und Not-Aus bestaetigen; keine Freigabe aus diesem
   Dokument ableiten.
3. Beide VL53-Punktwolken, aktiven `collision_monitor`, frische Odometrie,
   initialisierte Encoder, RS485-Bereitschaft und 0 rpm pruefen.
4. Laufzeitparameter pruefen: `OPEN_LOOP`, 2000-ms-Nav2-Timeout und
   Fortschrittspruefer 0,10 m/20 s.
5. Während des Laufs Mission, Gate-Ausgang, Encoder-/Modbusstatus und echten
   Motorstillstand auch nach einem Terminalstatus weiter beobachten.

### Offene Grenzen und Rückfall

Die allgemeine Selbstlokalisierung nach freiem Versetzen oder Neustart ist
noch nicht abgenommen. Bis dahin ist reale Raumfahrt nur vom kontrollierten
Startbezug aus zulaessig. Der Recovery-freie Baum bricht absichtlich ab, statt
ein Hindernis autonom zu umfahren. H5 der Encoder-Odometrie und ein echter
VL53-Hindernis-Abbruch in dieser Kette bleiben offen.

Rückfall: `enable_real_go_to_room:=false` verwenden oder weglassen und den
Real-Launch nicht starten. Dann bleibt die semantische Zielaufloesung
read-only/simuliert. Karten- und Raumdaten bleiben lokal ausserhalb des
Repositories.

---

## Auftrag: manuelle semantische Räume in der Amadeus-App (14.08.2026)

**Branch:** `feature/semantic-map-editor`

**Vollständiger Vertrag:** `docs/SEMANTIC_MAP_INTEGRATION.md`

Der neue `semantic_map_manager` ist passiv: Er liest den Status des
`robot_map_manager`, speichert Raum-Polygone außerhalb des Repositories und
publiziert Metadaten. Er besitzt weder Nav2-Action noch `cmd_vel`-Publisher.
Auch `mission_manager` bereitet `go_to_room` ausschließlich als Simulation vor.
Diese Übertragung ist daher **keine Fahrfreigabe**.

### Auf Entwicklungs-Mac und Jetson geprüft

- 51 Semantik-Backend-, 38 Mission-, 15 LLM-Planer-, 51 Kartenmanager-,
  2 Bring-up- und 5 rosbridge-Mocktests: **162/162 Python-Tests bestanden**;
- 39/39 Swift-Tests und vollständiger iOS-Simulator-Build bestanden;
- Python-Kompilierung, Mypy, Flake8 `F/E9`, YAML/XML, Packaging und
  Whitespaceprüfung bestanden;
- der identische Python-Testbestand sowie der Colcon-Build der sechs Pakete
  bestanden am 14.08.2026 auf dem realen Jetson;
- physisches iPhone: signierter Build, Installation, zwei rosbridge-Sockets,
  bewusstes Kartenspeichern, Raum-Upsert auf Revision 1 und App-Neustart
  bestanden;
- Semantikmanager-Neustart stellte Revision 1 identisch wieder her;
  kontrolliertes SIGINT endet nach der gefundenen Shutdown-Korrektur sauber;
- mehr als sechs Sekunden ohne Kartenmanager sperrten den Status mit
  `ok:false`/`editable:false`; der Wiederanlauf derselben Karte stellte
  Revision 1 und den Raum `Test` ohne Datenverlust wieder her;
- ein Update mit `base_revision:0` gegen Revision 1 wurde live abgelehnt und
  ließ `current.json` unverändert;
- `go_to_room` für `Test` ergab live ausschließlich
  `simulation_only_no_navigation`; `/cmd_vel` existierte davor und danach
  nicht;
- während der gesamten Abnahme existierten weder Motor-/Nav2-Knoten noch das
  Topic `/cmd_vel`.

Die Abnahme verwendete ausschließlich die statische `testwohnung`. Eine neue
reale Wohnungskarte und jede Fahrwirkung bleiben eigene spätere Prüfungen.

### Sichere Übernahmereihenfolge

1. Arbeitskopie und Branch prüfen; unbekannte lokale Änderungen nicht
   überschreiben. Den Branch erst übernehmen, nachdem er in das Remote
   veröffentlicht wurde.
2. `AGENTS.md`, dieses Dokument und `docs/SEMANTIC_MAP_INTEGRATION.md` lesen.
3. Ohne aktive Motor-/Navigationsknoten bauen und die Offline-Verträge prüfen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select \
  robot_map_manager semantic_map_manager mission_manager llm_planner \
  semantic_perception robot_bringup
source install/setup.bash

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/semantic_map_manager \
  python3 -m unittest discover -s src/semantic_map_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/mission_manager \
  python3 -m unittest discover -s src/mission_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/llm_planner \
  python3 -m unittest discover -s src/llm_planner/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/robot_map_manager \
  python3 -m unittest discover -s src/robot_map_manager/test -v
python3 -m unittest discover -s src/robot_bringup/test -v
python3 -m unittest discover -s ios/Robotersteuerung/Tools \
  -p 'test_mock_rosbridge.py' -v
```

4. Für den ersten ROS-Vertragstest nur die beiden passiven Manager starten;
   dafür sind keine Motoren und keine Fahrt nötig:

```bash
ros2 launch robot_map_manager map_manager.launch.py
ros2 launch semantic_map_manager semantic_map_manager.launch.py
ros2 topic echo /robot_map_manager/status_json
ros2 topic echo /semantic_map/status_json
ros2 topic echo /semantic/catalog_json
```

5. Erst wenn eine echte `/map` sichtbar ist, in der App bewusst **Karte für
   Räume speichern** wählen. Die Erstbindung ist nur nach einem bestätigten
   `save_result` mit identischem SHA-256-Fingerabdruck möglich. Danach einen
   kleinen Test-Raum zeichnen, Zielpunkt strikt innerhalb setzen, speichern,
   App neu verbinden und Persistenz/Revision prüfen.
6. Prüfen, dass die Daten ausschließlich hier liegen und nicht für Git
   vorgemerkt sind:

```text
~/.local/share/amadeus/semantic_maps/<fingerprint>/current.json
~/.local/share/amadeus/semantic_maps/<fingerprint>/revisions/
```

7. Negativtests ohne Fahrt: falsche `base_revision`, Kartenwechsel und mehr als
   sechs Sekunden ausbleibender Kartenmanagerstatus müssen `editable:false`
   ergeben. `go_to_room` darf nur `simulation_only_no_navigation` melden und
   weder Nav2 noch `cmd_vel` auslösen. Ein Replay derselben `request_id` muss
   dabei Karte, Speicher, Pose, Zeit und Zähler aus dem **aktuellen** Zustand
   zeigen und darf keinen historischen Vollstatus zurückspielen.
   Zusätzlich muss der Mission-Cache nach sechs Sekunden ohne neuen
   Semantikstatus verfallen. Ein manuell angelegter Raum, ein Objekt oder ein
   Ablageziel aus einer Topic-Nachricht darf die statischen realen
   `pick_and_place`-Allowlists nicht erweitern.
8. Persistenzgrenzen sichtbar prüfen: 2.048 Revisionen/Karte, 1 GiB
   Repository und 512 MiB Freispeicherreserve sind die defensiven Defaults.
   Eine erreichte Grenze muss die neue Revision ablehnen und die letzte
   gültige Revision unverändert lesbar lassen; nichts automatisch löschen.

### Rückfallweg

- `start_semantic_map_manager:=false` lässt das Paket im Gesamt-Bring-up aus.
- `use_dynamic_catalog:=false` in Missions- und LLM-Konfiguration nutzt wieder
  ausschließlich die statischen Listen.
- Das Verzeichnis `~/.local/share/amadeus/semantic_maps/` vor einer manuellen
  Änderung sichern; der Code löscht keine Revision automatisch.
- Reale Raumfahrt bleibt gesperrt, bis VL53-/Collision-Monitor, Lokalisierung,
  Costmap-Freiraum, Planbarkeit und Abbruchpfade separat abgenommen sind.

## Abnahmestand Encoder-Odometrie (13.08.2026)

**Branch:** `fix/encoder-position-odometry` · **H0 bis H4 bestanden**

- [x] **H0** keine Knoten aktiv, `/dev/ttyUSB_BASE` frei, Worktree sauber
- [x] **H1** beide Motoren stabil per FC03 (~5 ms); `0x0011=1000`, `0x0019=0`,
      `0x0101=4000` beidseitig identisch; Position im Stillstand bitgenau
      konstant über 40 Proben
- [x] **H2** `encoder_counts_per_motor_revolution = 1000`, unabhängig gemessen:
      vorwärts 1000,8/1000,9 und rückwärts 1000,2/1000,3; Richtungsunterschied
      unter 0,07 %; vom Nutzer in beiden Richtungen mit genau 5 Radumdrehungen
      bestätigt. Gegenrechnung über die Motordrehzahl: 999,4–999,5
- [x] **H3** aufgebockt: geradeaus 0,2442 m bei 0,01° Gierwinkel, Drehung auf
      der Stelle 93,33° bei 0,0001 m Translation; null Fehler, `/odom` 16,7 Hz,
      Watchdog greift
- [x] **H4** Bodenfahrt gegen das **Lasermessgerät**: je Fahrt **+0,5 mm**
      statt +17,3 bis +20,1 mm. Zusatzfehler dreier weiterer Start-Stopp-
      Vorgänge von **+51,9 auf +3,9 mm** gesunken (−92 %). Skalenfehler
      +0,23 %, Kursabweichung +0,04° bis +0,27°
- [ ] **H5** Fehler- und Wiederanlaufpfade — offen
- [ ] `odom_*_variance` aus wiederholten Fahrten kalibrieren — offen

### Was dabei zusätzlich gefunden wurde

**Die Anfahrrampe war bis 14.08.2026 nie wirksam.** Der Antrieb weist
`accel_ms: 2500` mit
`ExceptionResponse(function_code=134, exception_code=7)` zurück; die Obergrenze
beider Rampenregister liegt bei **2000**. Ausgelesen stand in `0x001E` auf
beiden Motoren **100**. Sichtbar wurde das erst, weil dieser Branch die
Rückgabewerte der Schreibvorgänge prüft — der alte Code verschluckte den
Fehlschlag.

Die getrennte Änderung ist inzwischen real bestanden: Eingetragen sind jetzt
**2000 ms Beschleunigen**, unverändert 400 ms Bremsen und 5 rpm
Startgeschwindigkeit. Beide Antriebe bestätigten alle drei Werte. Ein
1,0-s-Bodenimpuls mit 0,12 m/s ergab 0,0439 m Encoderweg und 0,000°
Kursänderung; der Nutzer bewertete das Anfahren als „gut sanft“. Die frühere
Annahme, die Rampenzeit werde proportional zu 3000 rpm verkürzt, ist damit
widerlegt. Die anschließende manuelle LiDAR-Runde zeigte keine Verschlechterung
der Wanddicke (37,0 % vorher, 36,7 % nachher). Die offene Zimmertür macht
Fläche und Kartenausdehnung zwischen den beiden Läufen nicht vergleichbar.

**Der Nahbereichsschutz ist funktionslos.** `vl53_near_field` stirbt mit
„Kein CH341/CH34x-I2C-Bus gefunden"; der Adapter `1a86:5512` steckt, das
Kernelmodul `ch34x` fehlt. Der `collision_monitor` aktiviert sich trotzdem und
reicht ohne Sensordaten alles durch. **Vor autonomem Fahren zwingend beheben.**

**Der LiDAR-Wandvergleich taugt nicht als Kalibrierreferenz.** Bei einer Fahrt
lag er 21,5 mm neben dem Laser, bei eigener Streuung von 1,7 mm.

### Fahren mit Nahbereichsschutz

`collision_monitor` hängt als `cmd_vel_smoothed` → `cmd_vel` dazwischen. Wer
direkt auf `/cmd_vel` publiziert, umgeht ihn. Messwerkzeuge nehmen dafür
`--cmd-topic /cmd_vel_smoothed`.

---

## Auftrag: Encoderpositions-Odometrie

**Branch:** `fix/encoder-position-odometry`
**Vollständige Anleitung:** `docs/ENCODER_ODOMETRIE_FIX.md`

Dieser Branch baut auf `agent/slam-toolbox-pure-rotation-fix` auf und enthält
damit den bereits geprüften Humble-Backport und den Scan-Vereinheitlicher. Für
diesen Auftrag später **nicht** auf den Basisbranch zurückschalten.

### Branch auf dem Jetson übernehmen

```bash
cd ~/roboter_ws
git status --short --branch
git fetch origin
git switch fix/encoder-position-odometry 2>/dev/null || \
  git switch --track -c fix/encoder-position-odometry \
  origin/fix/encoder-position-odometry
git pull --ff-only
```

Bei lokalen Änderungen, einem unerwarteten Commit oder einem nicht schnellen
Vorwärtsschritt stoppen und den Zustand klären. Keine unbekannten Jetson-Dateien
überschreiben.

Der Softwarefix ist offline geprüft, aber absichtlich noch nicht fahrbereit:
`encoder_counts_per_motor_revolution: 0.0` blockiert den echten Start. Auf dem
Jetson zuerst alle Roboterknoten beenden und ausschließlich read-only messen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
python3 tools/kartierung/encoder_position_pruefen.py --confirm-stack-stopped
```

Danach die markierte Motor- oder Radumdrehung gemäß Hilfe des Werkzeugs messen,
Wortfolge, Vorzeichen, `0x0011` und `0x0101` protokollieren und erst den
bestätigten Counts-Wert eintragen. Nach H2 müssen alle drei Schutzwerte gesetzt
sein:

```yaml
encoder_counts_per_motor_revolution: <bestätigter Wert>
encoder_expected_segment: <beidseitig bestätigter Wert aus 0x0011, > 0>
encoder_expected_resolution: <beidseitig bestätigter Wert aus 0x0101, > 0>
```

`0` bei einem dieser Werte ist ausschließlich der read-only
Inbetriebnahmezustand und verriegelt den realen `encoder_position`-Modus. Ein
neuer Modbus-Client liest `0x0011`/`0x0101` erneut und startet bewusst mit einer
neuen Baseline. Anschließend gelten H0 bis H5 aus der vollständigen Anleitung.
Keine Hardwarefreigabe aus diesem Dokument ableiten.

Im laufenden Encoderpositionsmodus behält eine einzelne normale FC03-Fehlprobe
Client und Baseline. An der Transportfehlerschwelle folgen bestmöglicher
Stopp, Busfehlerstatus, Reconnect und eine neue Baseline. Stale Rückmeldung
sperrt und stoppt immer, reconnectet aber nur bei zugrunde liegendem
Transportfehler;
Python-Ausnahmen beziehungsweise unbekannte Pymodbus-API-Fehler gehen sofort in
diesen Pfad. Ein Reconnect darf daher **nicht** als kurze Lücke mit nachzuholenden
Counts bewertet werden.

Ein semantisch ungültiges Encoderpaar oder eine abweichende Treiberkonfiguration
sperrt und stoppt dagegen sofort, ohne den bestehenden Client nutzlos neu zu
verbinden. Ein unplausibles Delta wird verworfen und im Tracker kontrolliert
rebased.

`/odom` wird nur zu einem neuen gültigen Encoderpaar publiziert, mit der
Zielperiode von 0,05 s ungefähr 20 Hz. `state_json` läuft unabhängig davon im
50-Hz-Node-Takt weiter.

Der Befehlsvertrag ist ebenfalls sicherheitsrelevant: `/cmd_vel` hat Queue-Tiefe
1, NaN/Inf werden verworfen und fordern Stopp an, und der Watchdog nutzt
monotone Echtzeit. `use_sim_time: true` ist bei scharfem RS485 verboten. Ein
Motorstart erfolgt nur, wenn nach Quantisierung mindestens ein tatsächlich
schreibbarer RPM-Wert ungleich null ist.

Die vier `odom_*_variance`-Werte sind konservative Startwerte und werden erst
in H4 aus wiederholten extern referenzierten Fahrten kalibriert.

Vor Build und Tests die gepinnten seriellen Abhängigkeiten installieren.
`requirements-modbus.txt` fixiert Pymodbus 3.14.0 und Pyserial 3.5:

```bash
python3 -m pip install -r src/base_hardware/requirements-modbus.txt
```

Lokal auf dem Entwicklungs-Mac bestanden 59 Base-Hardware- und 12
Werkzeugtests. Auf dem Jetson nach dem Checkout erneut ausführen und das dortige
Ergebnis getrennt protokollieren:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/base_hardware \
  python3 -m unittest discover -s src/base_hardware/test -v
python3 -m unittest discover -s tools/kartierung \
  -p "test_encoder_position_pruefen.py" -v
```

Der CI-Workflow `.github/workflows/encoder-odometry-offline.yml` kompiliert und
prüft dieselben Python-Komponenten zusätzlich unter Ubuntu 22.04/Python 3.10.
Mac- und CI-Ergebnisse ersetzen weder den Jetson-Lauf noch die gestufte
Hardwareabnahme.

---

Der folgende Abschnitt ist nur historischer Kontext des bereits integrierten
Vorläufers. Er ist **keine zweite aktive Übergabe**. Die vollständige alte
Diagnose steht in `docs/SLAM_TOOLBOX_ROTATION_FIX.md`.

## Integrierter Vorläufer: Humble-Fix für reine Drehungen

**Historischer Basisbranch:** `agent/slam-toolbox-pure-rotation-fix`

**Basis:** `feature/stl27l-integration`, Commit `7010058`

**Ziel:** gepinntes `slam_toolbox`-Overlay unter
`~/amadeus_slam_toolbox_ws`; `/opt/ros/humble` bleibt unverändert.

### Voraussetzungen

- [ ] `AGENTS.md`, `docs/PROJECT_MEMORY.md` und
      `docs/SLAM_TOOLBOX_ROTATION_FIX.md` vollständig gelesen
- [ ] Jetson-Arbeitskopie `~/roboter_ws` sauber; unbekannte Änderungen geklärt
- [ ] kein RTAB-Map- oder alter `slam_toolbox`-Prozess aktiv
- [ ] keine Geheimnisse, echten Karten oder ROS-Bags für einen Commit vorgemerkt
- [ ] Motorstrom aus; keine Fahrfreigabe vorausgesetzt

### Einordnung im aktuellen Branch

Der aktuelle Encoderbranch enthält diesen Stand bereits. Nicht auf
`agent/slam-toolbox-pure-rotation-fix` zurückschalten. Das gepinnte Overlay darf
weiterhin nicht ungepinnt aktualisiert und `/opt/ros/humble` nicht verändert
werden.

### Source-Reihenfolge in jedem Testterminal

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/amadeus_lidar_ws/install/local_setup.bash
source ~/roboter_ws/install/local_setup.bash
```

Kontrolle:

```bash
ros2 pkg prefix slam_toolbox
```

Muss auf `~/amadeus_slam_toolbox_ws/install/slam_toolbox` zeigen.

### Abnahmestatus

Stand 12.08.2026, abgenommen auf Commit `4fe5ee3`:

- [x] Patch-Preflight (`git apply --unidiff-zero --check`) bestanden
- [x] Overlay gebaut; `colcon test` liefert allerdings **0 Tests** und ist als
      Evidenz wertlos (Testblock im Upstream auskommentiert). Ersatz: Blob-Hashes,
      Release-Build und `strings`-Gegenprobe am Binärpaket
- [x] Paketpräfix und gepinnter Humble-Commit kontrolliert
- [x] Stillstand: `dry_run=true`, `allow_rs485=false`
- [x] Stillstand: neuer Parameter `true`, keine Knotenflut, `/scan` 9,99 Hz
- [x] Synthetischer Yaw-only-Regressionstest ergänzt:
      `tools/kartierung/test_reine_drehung_synthetisch.py`, A/B 37 gegen 0
- [x] ausdrückliche Fahrfreigabe der anwesenden Person erteilt
- [x] Not-Aus in Reichweite, Fläche frei, Beobachter anwesend
- [x] 360°: mehr als null neue Posegraph-Knoten (1 → 11), Karte sichtbar ergänzt
      (freie Fläche 10,8 → 23,2 m²)
- [x] **versetzt duplizierte Wände: Ursache gefunden und behoben.** Karto
      verwarf jeden Scan mit abweichender Strahlenzahl; der STL-27L schwankt
      über 19 Werte (2145–2176). Abhilfe ist der neue Knoten
      `scan_vereinheitlichen`. A/B bei identischem Ablauf: 31 → 0 verworfene
      Scans, 10 → 41 Knoten, Nebenachse 5,39 → 3,83 m bei real 3,80 m
- [x] 40 cm Translation: weiterhin Kartenupdate (20 neue Knoten), keine
      Doppelwände, Kursabweichung +0,18°
- [ ] langsame geschlossene Runde: **noch offen.** Es ist kein Joystick
      angeschlossen (`/dev/input/js*` fehlt) und weder `collision_monitor` noch
      Nav2 laufen in `slam_lidar.launch.py`. Eine Runde durch die Wohnung darf
      deshalb nicht ferngesteuert-blind gefahren werden — der LiDAR sieht
      Schwellen, Kabel und Tischplatten grundsätzlich nicht
- [x] Testergebnis mit Datum und Commit in `docs/PROJECT_MEMORY.md` ergänzt

Diese damalige Phase-4-Freigabe gilt nicht automatisch für die neue
Encoderänderung. Im aktuellen Branch sind zuerst H0 bis H3 aus
`docs/ENCODER_ODOMETRIE_FIX.md` abzuarbeiten; jede Bewegungsphase braucht eine
neue ausdrückliche Freigabe.

### Zwei Dinge, die beim Fahren beachtet werden müssen

**Vor jedem Versuch prüfen, dass nichts mehr läuft.** `kill -INT` auf die
`ros2 launch`-PID beendet den Elternprozess, die Knoten können weiterlaufen. Am
12.08.2026 liefen dadurch zeitweise **zwei vollständige Stapel gleichzeitig** —
zwei `map->odom`-Publisher und zwei scharfe `base_hardware`-Knoten auf demselben
RS485-Bus. Die betroffene Messung war Unsinn und wurde verworfen. Nach dem
Beenden immer nachsehen, die eigene PID dabei ausnehmen:

```bash
MY=$$
ps -eo pid=,cmd= | grep -E '[l]dlidar|[a]sync_slam_toolbox|[b]ase_hardware|[s]can_vereinheitlichen' \
  | awk -v my="$MY" '$1 != my'
```

**Der Odometrie-Winkelfehler ist geklärt: −1,45° je Umdrehung.** Die früher
gemeldeten −6,3° bis −6,5° waren ein Artefakt von `odometrie_drehtest.py`.
Sauber gemessen mit `tools/kartierung/odometrie_winkel_messen.py` (283
Messpunkte je Richtung, R² = 0,997): Skalenfaktor 0,99628 gegen den und 0,99564
im Uhrzeigersinn — beide Richtungen stimmen überein, also ein echter
Skalenfehler. Kein Handlungsbedarf vor Phase 4.

**Der Radradius ist neu kalibriert:** `wheel_radius_m: 0.0624`,
`wheel_separation_m: 0.3845` (vorher 0.0612 / 0.3755), aus acht Fahrten mit dem
Lasermessgerät. Verifikationsfahrt über 2,00 m innerhalb der Ablesegenauigkeit
getroffen.

**Was dabei zu beachten ist, wenn jemand die Odometrie erneut vermisst:**

1. **Kurze und lange Fahrt kombinieren.** Fester Anfahrversatz und Skalenfehler
   sind nicht trennbar, solange alle Fahrten ähnlich lang sind. 0,30 m gegen
   2,50 m funktioniert; 0,4 bis 1,0 m reicht nicht und liefert je nach
   Auswertung Radien zwischen 0,0621 und 0,0631.
2. **Lasermessgerät, nicht den LiDAR-Wandvergleich.** Der LiDAR lag bei der
   Verifikationsfahrt 24 mm daneben, bei sonst ±5 mm Streuung.
3. **Eine Winkelmessung bestimmt nur r/W**, nie die Spurweite allein. Ein
   Streckenfehler bleibt darin unsichtbar.

**Historischer Befund:** Der feste Versatz war kein Radiusfehler. Die frühere
Vermutung eines verspätet einsetzenden Ist-Drehzahlwerts ist nicht belegt;
50-Hz-Polling widerlegte eine reine Unterabtastung. Der aktuelle Encoderbranch
adressiert den Softwarepfad mit absoluten Positionsdeltas. Ob der Versatz real
verschwindet, entscheidet erst die H4-A/B-Messung.

**Keine Aktoren aktivieren, bevor alle Stillstandsprüfungen oberhalb bestanden
sind.** Ein KI-Agent darf die Fahrfreigabe nicht selbst annehmen.

### Rollback

Launch einmal sauber mit `Ctrl-C` beenden. Dann eine frische Shell verwenden
und das Overlay nicht sourcen:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 pkg prefix slam_toolbox
```

Das Präfix muss wieder `/opt/ros/humble` sein. Der Overlay-Ordner bleibt zur
Analyse erhalten; keine Datenlöschung ist erforderlich.
