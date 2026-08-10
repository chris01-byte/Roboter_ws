# Übernahmeplan – Jetson-Mappingstand vom 27.07.2026

Dieser Plan überträgt den einzigen aktuellen Jetson-Stand auf den
USB-Datenträger, ohne den Jetson oder den bestehenden USB-Workspace zu
überschreiben. Die Quellsicherung ist fahrbewegungsfrei. Befehle, die den
Roboter bewegen, sind ausdrücklich nicht Teil dieser Übernahme.

## 0. Verbindliche Sperren

- Das Release `amadeus-map-v1-20260726T194942Z` nicht auf den aktuellen Jetson
  anwenden.
- Weder `rsync --delete` noch einen pauschalen Workspace-Abgleich verwenden.
- Commit `390fcec` nicht anhand des Berichts nachbauen.
- Die vorhandene `rtabmap.db`, ihr Backup und den gespeicherten Snapshot nicht
  verändern, verschieben oder überschreiben.
- Keine Kartierfahrt und kein Nav2 während der Sicherung starten.

## 1. Jetson und Stillstand prüfen

Auf dem Jetson:

```bash
cd ~/roboter_ws
git rev-parse HEAD
git status --short
git log -5 --oneline --decorate

pgrep -af 'rtabmap|ros2 launch|kartierfahrt|lokalisierung'
ros2 topic info /cmd_vel --verbose
ros2 topic type /localization_pose
ros2 topic info /localization_pose --verbose
ros2 topic info /map --verbose
ros2 topic info /odom --verbose
ros2 topic info /cmd_vel_smoothed --verbose
ros2 node list
ros2 node info /rtabmap
ros2 param dump /rtabmap
ros2 param get /rtabmap Grid/RangeMax
ros2 run tf2_tools view_frames
```

Der erwartete Commit ist `390fcec`. Laufende Kartierung oder Lokalisierung
muss zuerst mit dem auf dem Jetson vorhandenen, geordneten Stoppskript beendet
werden. Kein Prozessgruppen-SIGINT und kein `kill -9` verwenden. Anschließend
prüfen:

```bash
pgrep -af 'rtabmap|ros2 launch|kartierfahrt|lokalisierung'
sqlite3 ~/.local/share/amadeus/rtabmap.db 'PRAGMA quick_check;'
sqlite3 ~/.local/share/amadeus/rtabmap.db 'SELECT COUNT(*) FROM Word;'
source /opt/ros/humble/setup.bash
rtabmap-info ~/.local/share/amadeus/rtabmap.db
```

`PRAGMA quick_check` muss `ok` liefern und die Wörterzahl muss größer als null
sein. Abweichung bedeutet Abbruch und Sicherung des unveränderten Istzustands
zur Analyse.

## 2. Quellstand verlustfrei exportieren

Ein neuer, leerer Zielordner auf dem USB-Datenträger wird verwendet:

```bash
EXPORT_DIR='/media/p/64GB/jetson_exports/amadeus-slam-localization-20260727'
test ! -e "$EXPORT_DIR"
mkdir -p "$EXPORT_DIR/code" "$EXPORT_DIR/runtime"

cd ~/roboter_ws
git rev-parse HEAD > "$EXPORT_DIR/code/HEAD.txt"
git status --porcelain=v1 --untracked-files=all > "$EXPORT_DIR/code/status.txt"
git log -20 --format=fuller > "$EXPORT_DIR/code/log.txt"
git show --stat --summary 390fcec > "$EXPORT_DIR/code/commit-stat.txt"
git diff --binary > "$EXPORT_DIR/code/worktree.patch"
git diff --cached --binary > "$EXPORT_DIR/code/index.patch"
git bundle create "$EXPORT_DIR/code/roboter_ws.bundle" --all
git ls-files --others --exclude-standard -z > "$EXPORT_DIR/code/untracked.zlist"
```

Die Null-Liste der unversionierten Dateien muss ein Agent prüfen, bevor er sie
in ein separates Archiv übernimmt. Build-, Install-, Log-, `.git`- und
Laufzeitkarten-Verzeichnisse dürfen nicht als Quellcode importiert werden.
Der Git-Bundle enthält nur commitete Git-Objekte; Patchdateien und die geprüfte
Untracked-Liste sichern mögliche Abweichungen getrennt.

Mindestens folgende gemeldete Pfade müssen anschließend im exportierten Commit
oder in der Untracked-Liste auffindbar sein:

```text
src/base_hardware/base_hardware/base_hardware_node.py
tools/kartierung/
slam.launch.py beziehungsweise dessen tatsächlicher Pfad
alle von den Startskripten referenzierten YAML- und Launch-Dateien
```

## 3. Laufzeitdaten getrennt sichern

Erst nach dem Integritätscheck und bei beendetem RTAB-Map:

```bash
rsync -a --checksum \
  ~/.local/share/amadeus/rtabmap.db \
  ~/.local/share/amadeus/rtabmap_20260727_backup.db \
  "$EXPORT_DIR/runtime/"

rsync -a --checksum \
  ~/.local/share/amadeus/maps/amadeus/20260727T165329866919Z-dbdb0d131f39/ \
  "$EXPORT_DIR/runtime/map-snapshot/"
```

Danach für Quell- und Laufzeitexport getrennte SHA-256-Listen erzeugen und
erneut vergleichen. Die Datenbankprüfung wird auf der Kopie wiederholt. Der
Agent protokolliert tatsächliche Dateigrößen, Hashes, Wörterzahl und
`rtabmap-info`-Kennzahlen; Schätzwerte aus dem Arbeitsbericht reichen nicht.

## 4. Vergleich auf dem Mac

Der USB-Workspace bleibt zunächst unangetastet. In einem temporären,
separaten Clone:

1. `git bundle verify` ausführen.
2. Jetson-Commit und vollständige Elternkette bestimmen.
3. Gemeinsamen Vorfahren mit USB-Commit
   `8d43cb07ef3ed4a19b61f39e462c6c286a8faaa3` ermitteln.
4. Commit-Diff, Worktree-Patch, Index-Patch und geprüfte unversionierte Dateien
   getrennt auswerten.
5. Berichtete Fixes gegen den tatsächlichen Code und Tests prüfen.
6. Erst dann eine neue `baseline.json`, `release-spec.json` und ein neues
   Release mit ausschließlich den erforderlichen Laufzeitdateien erzeugen.

Die alte V1-Release-Spezifikation wird nicht erweitert und ihr Archiv nicht
ersetzt.

## 5. Technische Freigabereihenfolge nach der Sicherung

1. Kurze Fahrt über eine bekannte Distanz aufzeichnen und
   `/localization_pose`, `/odom`, `/tf` und `/tf_static` vergleichen.
2. Den direkten `/cmd_vel`-Fluchtpfad vor weiterer autonomer Bodenfahrt
   sicherheitstechnisch korrigieren oder separat abnehmen.
3. Höhenverteilung der Tiefendaten messen.
4. Neue RTAB-Datenbank für `Grid/RangeMax=4.0` verwenden; die funktionierende
   Datenbank bleibt unverändert.
5. Raum großflächig abfahren und freie, belegte sowie unbekannte Fläche,
   Abmessungen und Wandverlauf prüfen.
6. Wiederlokalisierung erneut ausschließlich über `/localization_pose`
   bestätigen.
7. iPhone-App über Rosbridge end-to-end testen.
8. Nav2 erst danach und nur mit `static_map_odom:=false`, eindeutiger
   TF-Autorität, geprüftem Footprint, Costmaps und sicherer
   `/cmd_vel`-Kette aktivieren.

`src/robot_navigation/launch/nav_test.launch.py` ist ausschließlich ein
virtueller Teststand. Er darf nicht für diese Hardwareprüfung verwendet
werden, weil er selbst eine statische `map -> odom`-TF und virtuelle
Odometrie erzeugt.

## 6. Abschlusskriterien der Übernahme

- Git-Bundle ist verifiziert und enthält Commit `390fcec`.
- Dirty- und Untracked-Zustand des Jetson ist vollständig dokumentiert.
- Alle exportierten Dateien besitzen gespeicherte und nach dem Kopieren erneut
  geprüfte SHA-256-Werte.
- Original- und Kopierdatenbank bestehen `PRAGMA quick_check`.
- Beide Datenbanken enthalten eine positive Wörterzahl.
- Map-Snapshot enthält PGM, YAML, Rohdaten und Metadaten mit gültigen
  Prüfsummen.
- Kein bestehender USB-Code und keine Laufzeitkarte wurde überschrieben.
- Ein neues Release listet nur die tatsächlich geprüften Änderungen.
