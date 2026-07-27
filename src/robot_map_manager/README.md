# robot_map_manager

Isolierter ROS-2-Humble-Kartenmanager für Amadeus. Er empfängt eine
`nav_msgs/OccupancyGrid` auf `/map`, hält ausschließlich die jüngste gültige
Karte im Speicher und legt sie nur auf einen expliziten Speicherbefehl
versioniert ab.

Der Node lädt und löscht keine Karten, sendet keine Fahrbefehle und greift
nicht auf Motor-, Navigations- oder Missionsaktionen zu.

## Schnittstellen

| Richtung | Name | Typ |
|---|---|---|
| Eingang | `/map` | `nav_msgs/msg/OccupancyGrid` |
| Eingang | `/robot_map_manager/command_json` | `std_msgs/msg/String` |
| Ausgang | `/robot_map_manager/status_json` | `std_msgs/msg/String` |
| Ausgang | `/robot_map_manager/robot_pose` | `geometry_msgs/msg/PoseStamped` |
| Service | `/robot_map_manager/save_map` | `std_srvs/srv/Trigger` |

Für `/map` existieren absichtlich zwei Subscriptions:

- `TRANSIENT_LOCAL + RELIABLE` für einen gelatchten Kartenserver,
- `VOLATILE + BEST_EFFORT` für laufende SLAM-Publisher.

Vor der teuren Zellkonvertierung wird für den vollständigen rohen
`int8`-Puffer plus alle Kartenmetadaten und ROS-Zeitstempel eine
SHA-256-Signatur gebildet. Eine zeitnahe, bytegenau identische
Cross-QoS-Zweitlieferung kann dadurch bereits vor der Python-Zelliteration
entfallen. Der übliche zusammenhängende ROS-Puffer wird dabei direkt über
`memoryview`/`hashlib` in C gelesen; es gibt keine Stichproben-Heuristik.
Erst eine vollständig validierte Erstlieferung darf eine Zweitlieferung
überspringen. Zusätzlich erkennt der Inhaltsfingerabdruck des fertigen
Snapshots gleiche Karteninhalte unabhängig vom ROS-Zeitstempel.

Die Zellen liegen intern kompakt als ein Byte pro Zelle vor (`255` kodiert
ROS `-1`). Auch die vollständige Werteprüfung des üblichen `int8`-Puffers
läuft im schnellen Bytepfad. So erzeugt selbst das erlaubte Maximum von vier
Millionen Zellen kein Python-Integer-Tupel mit hohem Speicherbedarf.

Die Pose ist die über TF abgefragte Transformation vom `frame_id` des
aktuell gültigen Kartensnapshots nach `base_link`; ein separat konfigurierter,
möglicherweise falscher Kartenframe wird nicht verwendet. Der TF-Lookup ist
nicht blockierend. Endliche Koordinaten, Quaternion und TF-Zeitstempel werden
geprüft. Dynamische TFs dürfen standardmäßig höchstens eine Sekunde alt sein;
ihr tatsächliches Alter steht im Status. Stamp `0` wird gemäß der üblichen
Static-TF-Konvention alterslos akzeptiert. Das ist ausdrücklich nur eine
Annahme: Der Zeitstempel beweist nicht, dass die Quelle wirklich
`/tf_static` war. Ein fehlerhafter dynamischer Publisher mit Stamp `0` muss im
Jetson-Audit erkannt werden.

## JSON-Kommandos

`msg.data` enthält jeweils genau ein JSON-Objekt:

```json
{"command":"save"}
{"command":"save","name":"wohnung"}
{"command":"list"}
{"command":"list","name":"wohnung","request_id":"app-42"}
{"command":"status","request_id":"app-43"}
```

Erlaubte Kartennamen bestehen aus 1 bis 64 Kleinbuchstaben, Ziffern,
Unterstrichen oder Bindestrichen. Punkte, Schrägstriche, Leerzeichen,
Großbuchstaben und Pfadsegmente wie `..` werden verworfen. `request_id` ist
optional und wird in der Antwort gespiegelt. Innerhalb eines begrenzten
Laufzeitcaches von standardmäßig 128 Einträgen ist sie idempotent: dasselbe
semantische Kommando erhält exakt die bereits publizierte Antwort und löst
insbesondere keinen zweiten Save aus. Dieselbe `request_id` mit einem anderen
Kommando wird als Konflikt verworfen. Nach Verdrängung aus dem Cache oder
einem Node-Neustart beginnt dieser Schutz erwartungsgemäß neu.

Antworten und periodischer Zustand erscheinen als JSON auf
`/robot_map_manager/status_json`. Das Feld `event` unterscheidet unter
anderem `status`, `map_received`, `map_rejected`, `save_result` und
`list_result`; `ok` und `message` geben das Ergebnis an.

Im Kartenstatus unterscheiden `snapshot_available` und `publisher_count`
bewusst zwischen einer bereits empfangenen gültigen Karte und aktuell im
ROS-Graph sichtbaren `/map`-Publishern. Eine statische, gelatchte Karte wird
nicht allein wegen ihres Empfangsalters als ungültig markiert. Nach einer
verworfen Karte bleibt `map.last_validation_error` zur Diagnose erhalten;
eine danach empfangene gültige Karte oder deren gültige QoS-Zweitlieferung
löscht dagegen den aktuellen `last_error`. Unter `pose` stehen
`target_frame`, `zero_stamp_static_assumption`, `tf_stamp_ns` und das
ehrliche `tf_age_seconds`.

Der Trigger-Service speichert unter dem konfigurierten Standardnamen
`amadeus`:

```bash
ros2 service call /robot_map_manager/save_map std_srvs/srv/Trigger "{}"
```

## Speicherung

Der Standardpfad liegt absichtlich außerhalb des Workspaces:

```text
~/.local/share/amadeus/maps/<name>/<version>/
├── map.pgm
├── map.yaml
├── occupancy.bin
└── metadata.json
```

Jeder Speichervorgang schreibt zuerst in ein zufälliges Staging-Verzeichnis
auf demselben Dateisystem. Alle Dateien und das Verzeichnis werden
synchronisiert; erst danach macht ein atomarer Verzeichnis-Rename die neue,
unveränderliche Version sichtbar. Bei Fehlern wird nur das eigene
Staging-Verzeichnis entfernt. Schlägt ausschließlich das abschließende
Verzeichnis-`fsync` nach einem erfolgreichen atomaren Rename fehl, bleibt der
Save wahrheitsgemäß erfolgreich; `durability_warning` weist dann auf die
reduzierte Crash-Dauerhaftigkeitsgarantie hin.

Ein prozessübergreifender exklusiver `flock` auf
`.repository.lock` umfasst Schutzprüfung und Commit. Damit können zwei
Manager mit derselben Ablage die globalen Intervalle und Limits nicht
gleichzeitig passieren. Nach jedem Commit wird nach dem Kartenverzeichnis
zusätzlich die Speicherwurzel synchronisiert. Damit ist insbesondere beim
ersten Save auch der neue Namens-Directory-Eintrag crash-dauerhaft. Ein Fehler
dieses post-commit-`fsync` ist ebenfalls eine Warnung und kein falscher
Save-Fehler.

Bei jedem Start synchronisiert der Konstruktor die Elternkette der
Speicherwurzel innerhalb desselben `st_dev` bis einschließlich der
Mountwurzel, aber niemals ein darüberliegendes Dateisystem. Dadurch kann auch
ein Retry nach einem fehlgeschlagenen Erstanlage-`fsync` die
Durability-Prüfung nicht umgehen, nur weil die Verzeichnisse noch sichtbar
sind. Scheitert einer dieser Schritte, startet der Manager mit einem klaren
Speicherfehler gar nicht erst; ein Save ist dann nicht möglich. Es wird
bewusst kein globales `os.sync()` verwendet.

- `map.pgm` und `map.yaml` bilden das übliche ROS-/Nav2-Kartenpaar.
- `occupancy.bin` bewahrt jeden ursprünglichen Wert verlustfrei als signed
  int8 in der ROS-Zellreihenfolge.
- `metadata.json` enthält Ursprung, vollständige Quaternion, Dimensionen,
  Fingerabdruck und Prüfsummen.

Es gibt bewusst kein Laden, Überschreiben oder Löschen sichtbarer Versionen.
Beim Start dürfen lediglich eindeutig eigene Verzeichnisse der Form
`.tmp-<32 hex>` entfernt werden, wenn sie älter als die konfigurierte
Mindestzeit sind und ausschließlich die bekannten Staging-Artefakte
enthalten. Die Bereinigung nutzt no-follow-Verzeichniszugriffe und ist auf
standardmäßig 32 Einträge begrenzt; Versionen, Symlinks und fremde Dateien
bleiben unangetastet.

Vor jedem Save gelten standardmäßig folgende Schutzgrenzen:

- global mindestens 5 Sekunden Abstand zwischen Speichervorgängen, auch bei
  wechselnden Kartennamen,
- mindestens 512 MiB verbleibender freier Speicher nach konservativer
  Größenabschätzung,
- höchstens 100 Versionen je Kartenname,
- höchstens 2 GiB logischer Gesamtumfang der Kartenablage,
- höchstens 16 unterschiedliche Kartennamen.

Eine überschrittene Grenze verwirft ausschließlich den neuen Save. Es werden
niemals alte Versionen automatisch gelöscht, rotiert oder überschrieben.

Der ROS-Parameter `storage_directory` besitzt genau diesen Standardwert. Für
isolierte Test- oder Containerumgebungen kann er auf einen anderen absoluten
Pfad gesetzt werden; relative Pfade werden abgelehnt.

`list` meldet eine Version nur dann, wenn die tatsächlichen Größen und
SHA-256-Summen von `map.pgm`, `map.yaml` und `occupancy.bin` mit den Metadaten
übereinstimmen. Beschädigte oder manipulierte Versionen werden nicht als
gültig aufgelistet. Um nicht durch eine große Alt-Sammlung blockiert zu
werden, werden die Verzeichnisnamen zunächst günstig sortiert und nur eine
begrenzte Zahl der jüngsten Kandidaten vollständig geöffnet und gehasht:
höchstens das Doppelte des angeforderten Limits und im Core niemals mehr als
1000. Der Node liefert standardmäßig höchstens 20 Einträge und akzeptiert
keine Konfiguration über 100.

Zusätzlich dürfen die Artefakt-Hashes einer einzelnen `list`-Ausführung
zusammen höchstens 128 MiB lesen. Die deklarierten, vorab validierten
Artefaktgrößen werden konservativ reserviert; passt der nächste Kandidat
nicht vollständig ins Restbudget, wird er gar nicht gehasht. `list_policy`
meldet unter anderem `truncated`, `truncation_reasons`,
`artifact_verification_bytes_reserved` und
`maximum_list_verify_bytes`, sodass ein gekürztes Ergebnis nie als
vollständige Liste erscheint.

Neue `list`-Ausführungen besitzen global über alle `request_id` hinweg eine
Abkühlzeit von standardmäßig 10 Sekunden. Rotierende IDs können das
Hashbudget dadurch nicht unmittelbar wiederholt auslösen. Ein identischer
`request_id`-Replay wird vorher aus dem begrenzten Antwortcache bedient und
verursacht weder neue Datei-I/O noch eine neue Abkühlzeit.

## Validierung

Vor der Übernahme werden unter anderem geprüft:

- positive Dimensionen und höchstens 4.000.000 Zellen,
- exakt `width * height` ganzzahlige Zellwerte im Bereich `-1 ... 100`,
- positive, endliche Auflösung,
- endliche Ursprungskoordinaten,
- endliche, nichtleere und auf Norm 1 geprüfte Quaternion,
- nichtleere Frame-ID ohne Steuerzeichen,
- strikt begrenzte JSON-Größe und erlaubte Kommandofelder.

Ungültige Karten ersetzen niemals die letzte gültige Karte.

## Build und Start

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select robot_map_manager
source install/setup.bash
ros2 launch robot_map_manager map_manager.launch.py
```

Parameter stehen in `config/robot_map_manager.yaml`.

## Fahrbewegungsfreier Smoke-Test

Der separate Smoke-Launch startet ausschließlich die statische
`testwohnung`, einen `map_server`, den Kartenmanager und eine unveränderliche
Test-TF `map -> base_link`. Er enthält kein Nav2, keine Odometrie, keinen
`cmd_vel`-Publisher und keine Motor-Hardware:

```bash
ros2 launch robot_map_manager map_manager_smoke.launch.py
ros2 topic echo /robot_map_manager/status_json
ros2 service call /robot_map_manager/save_map std_srvs/srv/Trigger "{}"
```

Optional kann rosbridge ausschließlich auf dem lokalen Loopback-Interface
mitgestartet werden:

```bash
ros2 launch robot_map_manager map_manager_smoke.launch.py start_rosbridge:=true
```

Für einen bewusst durchgeführten iPhone-End-to-End-Test darf rosbridge im
vertrauenswürdigen, isolierten WLAN geöffnet werden:

```bash
ros2 launch robot_map_manager map_manager_smoke.launch.py \
  start_rosbridge:=true rosbridge_address:=0.0.0.0
```

`0.0.0.0:9090` besitzt dabei weder TLS noch Authentifizierung und darf nicht
in einem ungeschützten oder fremden Netz exponiert werden.

## ROS-unabhängige Tests

Die Speicherlogik importiert kein ROS und läuft ausschließlich mit der
Python-Standardbibliothek:

```bash
cd ~/roboter_ws
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src/robot_map_manager \
python3 -m unittest discover -s src/robot_map_manager/test -v
```

Diese Tests decken unter anderem parallele Repository-Saves, alle
Speichergrenzen, Root-/Directory-`fsync`-Warnpfade, begrenztes Listing,
Staging-Bereinigung, vollständige Bufferprüfung, Request-Cache und
TF-Zeitstempelregeln ab. Echte rclpy-/TF-/QoS-Callbacks benötigen dagegen
eine ROS-2-Humble-Laufzeit und werden deshalb im Jetson-Smoke-Test geprüft.

## Jetson-Callback-Check

Nach Build und Start des fahrbewegungsfreien Smoke-Launches:

1. `pose.target_frame` muss dem `map.summary.frame_id` entsprechen,
   `pose.zero_stamp_static_assumption` muss für die Test-TF `true` sein und
   `pose.tf_age_seconds` muss `null` bleiben.
2. Derselbe `save`-Befehl mit derselben `request_id` wird zweimal publiziert.
   Beide Antworten müssen bytegleich sein, `idempotent_replays` muss steigen
   und auf dem Dateisystem darf genau eine neue Version entstehen.
3. Bei einer Karte, die beide QoS-Subscriptions erreicht, muss
   `early_qos_duplicates` steigen; die Zweitlieferung darf keine zweite
   Snapshot-Konvertierung oder Statusstörung erzeugen.
4. Nach einer absichtlich ungültigen und danach gültigen Karte bleibt
   `map.last_validation_error` als Diagnose erhalten, während `last_error`
   wieder `null` ist.
5. Bei einem Snapshot mit geändertem `frame_id` muss die Pose sofort
   `available: false` und den neuen `target_frame` melden, bis eine passende
   TF ohne blockierenden Timeout verfügbar ist.
6. Im ROS-Graph muss geprüft werden, dass jeder Publisher mit Stamp `0`
   tatsächlich die beabsichtigte statische TF liefert; der Stamp allein kann
   diese Herkunft nicht beweisen.
7. Zwei neue `list`-Kommandos mit unterschiedlichen IDs innerhalb von zehn
   Sekunden müssen den zweiten Aufruf mit `retry_after_seconds` abweisen.
   Derselbe bereits beantwortete `request_id` muss dagegen sofort bytegleich
   aus dem Cache kommen und darf
   `artifact_verification_bytes_reserved` nicht erneut erhöhen.
