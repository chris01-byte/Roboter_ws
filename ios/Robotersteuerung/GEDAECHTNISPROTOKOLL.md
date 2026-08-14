# Gedächtnisprotokoll – native iOS-Robotersteuerung

**Stand:** 14.08.2026
**Arbeitsbereich:** `/Volumes/64GB/roboter_ws`
**App:** `ios/Robotersteuerung`

Dieses Dokument ist der Einstiegspunkt für spätere Arbeit an der nativen
iPhone-App. Vor Änderungen zuerst dieses Dokument, danach
`src/smartphone_gui/web/app.js` und den betroffenen Swift-Code lesen.

## Ziel und aktueller Stand

Die bisherige Safari-/PWA-Oberfläche wurde nicht entfernt. Daneben existiert
eine eigenständige SwiftUI-App ab iOS 16, die direkt per
`URLSessionWebSocketTask` mit rosbridge kommuniziert. Der bestehende
ROS-Vertrag bleibt kompatibel; der Missionsstatus wurde additiv um
`cancel_pending` ergänzt.

Enthalten sind:

- Verbindungseingabe mit lokal gespeicherter, zuletzt erfolgreicher URL
- automatischer Start, Ping und Wiederverbindung mit Backoff
- Erkennung veralteter Missions- und Sicherheitsdaten
- Raumfahrt, Greifen, Bringen und autonome Erkundung
- manuell deklarierte Räume aus dem Semantikstatus; Objekte, Ablageziele und
  die reale `pick_and_place`-Raumliste bleiben statisch freigegeben
- Mission abbrechen, Statusanzeige und lokales Ereignislog
- feedback-gesteuerter Software-NOT-AUS mit bestätigter Freigabe
- eigener Tab für die Live-Wohnungskarte mit Zoom, Verschieben, Reset,
  Metadaten und Legende
- manuelle Raumdeklaration als farbiges Polygon mit Name, Navigationspunkt,
  Blickrichtung, Auswahl und Löschen
- fail-closed Kartenbindung über denselben SHA-256 wie `robot_map_manager`
  und optimistische Semantik-Revisionen
- separate, nur im Karten-Tab aktive WebSocket-Verbindung für `/map`, damit
  große Kartenframes Steuerung und NOT-AUS nicht verzögern
- klare Kennzeichnung der letzten gültigen Karte als **NICHT LIVE**, sobald
  ihre Verbindung abbricht
- lokale Netzwerkfreigabe, enge ATS-Ausnahme und Privacy Manifest
- lokaler, abhängigkeitfreier rosbridge-Mock einschließlich Testwohnung
- 39 Swift-Tests für Steuerungs-, Sicherheits-, Karten- und Semantikprotokoll

## Verbindungsvertrag

Standardadresse der App: `ws://roboter.local:9090/`. Falls der Jetson unter
diesem mDNS-Namen nicht erreichbar ist, in der App seine WLAN-IP eintragen:
`ws://<JETSON-IP>:9090/`.

Nach dem Öffnen des WebSockets werden diese Frames gesendet:

```json
{"op":"advertise","topic":"/mission_manager/command_json","type":"std_msgs/String"}
{"op":"advertise","topic":"/safety/estop_request","type":"std_msgs/Bool"}
{"op":"subscribe","topic":"/mission_manager/status_json","type":"std_msgs/String"}
{"op":"subscribe","topic":"/safety/estop","type":"std_msgs/Bool"}
```

Missionen sind absichtlich doppelt kodiert: `msg.data` von
`/mission_manager/command_json` ist ein JSON-String.

```json
{"type":"go_to_room","room":"Wohnzimmer"}
{"type":"pick_object","object":"Tasse"}
{"type":"pick_and_place","object":"Tasse","room":"Kueche","target":"Tisch"}
{"type":"explore"}
{"type":"cancel"}
```

NOT-AUS:

```json
{"op":"publish","topic":"/safety/estop_request","msg":{"data":true}}
```

`true` fordert NOT-AUS an, `false` fordert die Freigabe an. Nur die
Rückmeldung auf `/safety/estop` bestimmt den angezeigten Istzustand.

Statusfelder in dem JSON-String auf `/mission_manager/status_json`:

```text
state, phase, message, progress, active_command,
rooms, targets, objects, offboard_available, cancel_pending,
pick_and_place_rooms, last_rejection, time
```

Der Karten-Tab öffnet unabhängig davon eine zweite Verbindung zu derselben
Adresse. Nur solange er sichtbar ist, registriert er:

```json
{"op":"advertise","topic":"/robot_map_manager/command_json","type":"std_msgs/String"}
{"op":"advertise","topic":"/semantic_map/command_json","type":"std_msgs/String"}
{"op":"subscribe","id":"amadeus-map","topic":"/map","throttle_rate":1000,"queue_length":1}
{"op":"subscribe","id":"amadeus-map-manager-status","topic":"/robot_map_manager/status_json","type":"std_msgs/String","queue_length":1}
{"op":"subscribe","id":"amadeus-semantic-map-status","topic":"/semantic_map/status_json","type":"std_msgs/String","queue_length":1}
```

Beim Verlassen des Tabs werden alle drei Subscriptions beendet und beide
Command-Topics wieder unadvertised. Der erste Teardown-Frame lautet:

```json
{"op":"unsubscribe","id":"amadeus-map","topic":"/map"}
```

Der Nachrichtentyp wird beim Subscribe absichtlich nicht angegeben, damit
rosbridge sowohl die ROS-1-Schreibweise `nav_msgs/OccupancyGrid` als auch die
ROS-2-Schreibweise `nav_msgs/msg/OccupancyGrid` selbst auflösen kann. Erwartet
werden `header.frame_id`, `info.width`, `info.height`, `info.resolution`,
`info.origin` und `data`. Die App akzeptiert höchstens 4.000.000 Zellen sowie
nur Werte von `-1` bis `100`; ROS-Zeilen werden beim Rendern für
Bildkoordinaten vertikal gespiegelt.

Falls beim ersten Subscribe noch kein SLAM-Publisher existiert, kann rosbridge
den untypisierten Topicnamen nicht auflösen. Solange die Ansicht
`warte auf /map` zeigt, führt der Kartencontroller deshalb alle vier Sekunden
ein Unsubscribe/Subscribe aus. So erscheint die Karte auch dann automatisch,
wenn SLAM erst später gestartet wird.

## Vertrag der manuellen Raumdeklaration

Die App berechnet aus `/map` exakt denselben Inhaltsfingerabdruck wie
`robot_map_manager`: SHA-256 über Dimensionen, Auflösung, Frame-ID, die sieben
Origin-Werte und alle kompakten Zellen; ROS-Zeitstempel sind nicht enthalten.
Raumschreiben ist nur erlaubt, wenn

```text
/map-Fingerprint == map.summary.fingerprint == semantic_map.map_ref.fingerprint
```

und Geometrie, Frame-ID, Origin, `editable=true` sowie die aktuelle Revision
ebenfalls stimmen. Zusätzlich muss der aktuelle `robot_map_manager`-Status
`ok:true` melden; bei `ok:false` werden Save, Overlay und Bearbeitung gesperrt.
Ein persistiertes semantisches Dokument darf nach einem
Node-Neustart auch bei `storage.last_saved: null` wieder aktiv werden. Nur die
erste Anlage verlangt eine identisch gespeicherte metrische Version.
Gespeicherte Versionen folgen dem echten `robot_map_manager`-Format
`YYYYMMDDTHHMMSSffffffZ-<12 kleine Fingerprint-Hexzeichen>`; ein optionales
Suffix `-NN` kennzeichnet eine Kollision.

Hierfür bietet die App bewusst den Knopf **Karte für Räume speichern** an und
publiziert genau diesen JSON-String in `msg.data`:

```json
{"command":"save","name":"wohnung","request_id":"ios-map-<uuid>"}
```

Es gibt keine automatische Wiederholung. Nur ein `save_result` mit derselben
`request_id` ist eine Antwort. Der Save-Knopf erscheint nur, wenn weder eine
passende `semantic_map.map_ref` noch ein passendes `storage.last_saved`
existiert. Eine passende, aber wegen `editable=false` gesperrte Semantik führt
stattdessen zu einem sichtbaren Blockgrund und niemals zu einem unnötigen
zweiten Erst-Save.

Raum anlegen beziehungsweise löschen:

```json
{
  "command":"upsert_room",
  "request_id":"ios-room-<uuid>",
  "map_fingerprint":"<64 kleine Hexzeichen>",
  "base_revision":3,
  "room":{
    "id":"room-<uuid>",
    "name":"Wohnzimmer",
    "color":"#4FB3A5",
    "polygon":[{"x":1.0,"y":1.0},{"x":4.0,"y":1.0},{"x":4.0,"y":3.0}],
    "navigation_goal":{"x":2.0,"y":2.0,"yaw":0.0}
  }
}
```

```json
{
  "command":"delete_room",
  "request_id":"ios-room-<uuid>",
  "map_fingerprint":"<fingerprint>",
  "base_revision":4,
  "room_id":"room-<uuid>"
}
```

`/semantic_map/status_json` liefert `schema_version`, `event`, `ok`,
`request_id`, `message` und `semantic_map` mit `map_ref`, `revision`, `rooms`
und `editable`. Bei einem Revisionskonflikt sendet die App nichts erneut,
sperrt den Editor und verlangt ein bewusstes Neuladen.

Save, Upsert und Delete haben jeweils eine lokale Antwortfrist von zwölf
Sekunden. Geht ein ACK verloren, wird der Pending-Zustand beendet, aber das
Ergebnis als unbekannt markiert; es gibt keinen automatischen Retry. Auch ein
positives ACK gilt erst dann als Erfolg, wenn es weiterhin zur aktuellen
Live-/Manager-Karte gehört, `editable=true` meldet, eine höhere Revision als
`base_revision` enthält und den erwarteten Raum tatsächlich enthält
beziehungsweise nicht mehr enthält. Raum-IDs folgen exakt
`[a-z0-9][a-z0-9_-]{0,63}`; ein Snapshot enthält höchstens 256 Räume.

Die Bildschirm-/ROS-Transformation berücksichtigt Origin-Translation,
Origin-Yaw, vertikale OccupancyGrid-Spiegelung, aspect-fit, Zoom und Pan. Der
Navigationspunkt muss strikt innerhalb des einfachen Polygons liegen. Er ist
nur Metadatum und löst keinen Nav2-Auftrag aus.

Quellen des Vertrags:

- `src/smartphone_gui/web/app.js`
- `src/mission_manager/mission_manager/mission_manager_node.py`
- `src/safety_monitor/safety_monitor/safety_monitor_node.py`
- `src/semantic_map_manager/semantic_map_manager/semantic_map_manager_node.py`

## Sicherheitsinvarianten

Diese Regeln bei Änderungen nicht aufweichen:

1. Missionsbuttons bleiben gesperrt, bis beide Statusströme frisch sind und
   `/safety/estop == false` bestätigt ist.
2. Ein gesendeter WebSocket-Frame ist kein Command-ACK. Annahme, Ablehnung und
   Ausführung kommen nur über `status_json`.
3. Während `state == "running"` oder `cancel_pending == true` keinen neuen
   Auftrag senden. Ein Abbruch ist erst nach terminalem ROS-Action-Ergebnis
   abgeschlossen.
4. NOT-AUS nie optimistisch umschalten. Immer die Ist-Rückmeldung abwarten.
5. Ein unbekannter NOT-AUS-Zustand darf nur das Auslösen (`true`), nie eine
   Freigabe (`false`) zur Folge haben.
6. Die NOT-AUS-Freigabe verlangt eine bewusste Bestätigung. Beim tatsächlichen
   Senden muss der Controller erneut prüfen, dass der aktive Istzustand noch
   frisch ist; ein offen gebliebener Dialog darf diese Prüfung nicht umgehen.
7. Hintergrund/Sperrbildschirm macht Telemetrie unbekannt; bei Rückkehr neu
   verbinden.
8. Klar sichtbar lassen: Software-NOT-AUS ist kein Hardware-NOT-AUS.
9. Kartendaten bleiben reine Anzeige und laufen über einen eigenen Socket. Sie
   dürfen niemals Missionsfreigaben oder Sicherheitszustände beeinflussen.
10. Semantische Schreibvorgänge laufen auf diesem getrennten Karten-Socket,
    sind keine Sicherheitskette und lösen keine Bewegung aus. Ein gesendeter
    Frame ist auch hier niemals ein ACK.

## Architektur und wichtige Dateien

```text
Robotersteuerung/
├── Models/RobotModels.swift
├── Models/RobotMapModels.swift
├── Services/RosbridgeProtocol.swift
├── Services/MapRosbridgeProtocol.swift
├── Services/RobotController.swift
├── Services/RobotMapController.swift
├── Views/AmadeusRootView.swift
├── Views/Components.swift
├── Views/DashboardView.swift
├── Views/RobotMapView.swift
├── Tools/mock_rosbridge.py
├── Tools/test_mock_rosbridge.py
├── Assets.xcassets/
├── Info.plist
└── PrivacyInfo.xcprivacy
```

- `RosbridgeProtocol.swift` ist der testbare Codec und die einzige Stelle für
  Topicnamen sowie äußere rosbridge-Frames.
- `RobotController.swift` hält Verbindung, Reconnect, Telemetriefrische,
  Katalogauswahl und Log auf dem Main Actor.
- `RobotMapController.swift` besitzt den getrennten, nur bei sichtbarer Karte
  aktiven WebSocket. Decodierung und Pixelaufbau laufen außerhalb des
  Main Actors; veröffentlicht wird nur die fertige Karte. Bei schnellen
  Updates wird höchstens eine Karte verarbeitet und nur der neueste wartende
  Stand behalten, damit alte große Frames keine neueren überschreiben.
- `RobotMapModels.swift` validiert das OccupancyGrid, berechnet den
  Kartenfingerabdruck, prüft Polygone und enthält die testbare
  Bildschirm-/map-Transformation. `MapRosbridgeProtocol.swift` kapselt Karte,
  Kartenmanager, Semantikstatus und die Schreibbefehle.
- `AmadeusRootView.swift` stellt die Tabs **Steuerung** und **Karte** bereit.
  `RobotMapView.swift` enthält Bitmap, Gesten, Zoomtasten, Metadaten, Legende
  und den auch dort erreichbaren Software-NOT-AUS.
- `DashboardView.swift` enthält den Bedienfluss; wiederverwendbare visuelle
  Bausteine und die bestehende PWA-Farbpalette liegen in `Components.swift`.
- Keine externen Swift Packages. Das ist wegen des exFAT-Workspace und für
  reproduzierbare Builds beabsichtigt. `Package.swift` ist lediglich ein
  lokaler Test-Harness für Model und Codec und lädt keine Abhängigkeiten.
- `Tools/mock_rosbridge.py` stellt lokal WebSocket-Port 9090 und
  Steuer-/Ereignis-Port 9091 bereit. Er ist nur ein Testwerkzeug und kein
  Ersatz für rosbridge auf dem Jetson.

## Simulator-Abnahme vom 26.07.2026

Getestete Umgebung: Xcode 26.5, iOS-26.5-Runtime, simuliertes iPhone 17 Pro,
lokaler Mock unter `ws://127.0.0.1:9090/`.

Synthetisch erfolgreich bedient und anhand der empfangenen Frames geprüft:

- Verbindungsaufbau mit zwei `advertise`- und zwei `subscribe`-Frames
- Raumfahrt, Greifen, Bringen und Erkunden einschließlich Picker-Auswahl
- genau ein Missions-Publish bei schnellem Doppel-Tap
- laufende Erkundung, doppelter Abbruch-Tap und genau ein `cancel`
- NOT-AUS, Abbruch des Freigabedialogs und bestätigte Freigabe
- offener Freigabedialog bei inzwischen veraltetem Sicherheitsstatus:
  `false` wird blockiert und nicht publiziert
- unvollständiger, unbekannter und beschädigter Missionsstatus wird verworfen
- Stale-Sperre getrennt für Missions- und NOT-AUS-Telemetrie
- ungültiges URL-Schema, manuelles Trennen, Socket-Abbruch, Auto-Reconnect
  und erneute Topic-Registrierung
- Wechsel in den Hintergrund und zurück sowie Hochformat-Festlegung
- separater `/map`-Subscribe mit ID, Drosselung und Queue-Länge eins
- Darstellung der 48 × 36 großen synthetischen Testwohnung mit korrekter
  Achsrichtung, Größe, Auflösung und Frame-ID
- Vergrößern und Zurücksetzen über synthetische Klicks
- Live-Kartenupdate über `/map-update`
- erst fehlender, danach über `/map-enable` verfügbarer Publisher; die Karte
  erschien ohne Tabwechsel nach der automatischen Neuregistrierung
- Socket-Ausfall mit weiterhin sichtbarer, klar als **NICHT LIVE**
  gekennzeichneter letzter Karte
- manueller Wiederanlauf und `/map`-Unsubscribe beim Verlassen des Tabs

Während dieser Abnahme wurden drei Sicherheitslücken geschlossen:

1. Doppelte Abbruch-Taps konnten mehr als einen `cancel` senden.
2. Leere oder unbekannte Status-Snapshots konnten als frisch gelten.
3. Ein alter, offen gebliebener NOT-AUS-Freigabedialog konnte die
   Freshness-Prüfung umgehen.

Im Stand vom 14.08.2026 bestehen 39 Swift-Tests im macOS-Test-Harness und im
iPhone-17-Pro-Simulator,
darunter Fingerprint-, Status-, Kommando-, Polygon- und Transformtests. Fünf
Python-Tests prüfen zusätzlich den semantischen Mock-Flow. Der
Strict-Concurrency-Build mit Warnungen als Fehler ist erfolgreich. Eine
synthetische End-to-End-Bedienung des neuen Raumeditors und der Lauf gegen den
echten Jetson bleiben separate Abnahmeschritte.

## Installation auf echtem iPhone vom 26.07.2026

Die App wurde mit dem persönlichen Xcode-Team signiert, per USB auf einem
iPhone 16 Pro Max mit iOS 26.5.2 installiert und nach Bestätigung des
Entwicklerzertifikats erfolgreich gestartet. Installierter Anzeigename ist
`Amadeus`, die Bundle-ID bleibt `de.roboterws.Robotersteuerung`. Auch der
sichtbare Titel im Dashboard lautet `Amadeus`. Der laufende App-Prozess wurde
anschließend über CoreDevice bestätigt.

Für die kostenlose Sieben-Tage-Signierung liegt auf diesem Mac die
doppelklickbare Datei `~/Desktop/Amadeus-App-erneuern.command`. Sie prüft das
bekannte iPhone und dessen Entwicklermodus, erneuert Build und Provisioning,
installiert über die vorhandene App und startet sie. Der vollständige Ablauf
wurde am 26.07.2026 erfolgreich auf dem echten Gerät ausgeführt.

Nach Fertigstellung der Kartenfunktion wurde derselbe Ablauf erneut
erfolgreich ausgeführt. Der Build mit den Tabs **Steuerung** und **Karte** ist
auf dem iPhone installiert und der laufende Prozess wurde über CoreDevice
bestätigt. Der echte Karteninhalt konnte dabei noch nicht geprüft werden, weil
dafür als nächster Schritt der `/map`-Publisher auf dem Jetson untersucht
werden muss.

Nach den abschließenden Race- und Lifecycle-Korrekturen wurde der endgültige
Build nochmals erfolgreich signiert und über die vorhandene App installiert.
CoreDevice listet weiterhin `Amadeus 1.0 (1)` mit der erwarteten Bundle-ID.
Nur das automatische Öffnen dieses letzten Builds wurde vom gesperrten iPhone
abgewiesen; nach dem Entsperren genügt ein normales Antippen der App.

## Bekannte Grenzen und nächste sinnvolle Schritte

- Die iOS-Plattform und Simulator-Runtime sind installiert; Build, Tests und
  interaktive Simulator-Abnahme sowie Installation und Start auf dem echten
  iPhone sind bestanden. Offen bleibt der Integrationstest gegen den echten
  Jetson im gemeinsamen WLAN.
- Die App-Seite der Kartenanzeige ist fertig. Im Repository wird derzeit nur
  `src/robot_navigation/maps/testwohnung.yaml` samt PGM über
  `nav_test.launch.py` als `/map` veröffentlicht. Im zentralen
  `robot.launch.py` sind echtes RTAB-Map-SLAM und Nav2 noch Platzhalter.
- Vor dem echten Kartenlauf muss auf dem Jetson geprüft werden, welcher Prozess
  `/map` veröffentlicht, ob das Topic dauerhaft beziehungsweise transient
  local ausgeliefert wird und wie Karten gespeichert und wieder geladen
  werden. Mehrere benannte Karten sind noch nicht Teil des Protokolls.
- Eine Roboterpositionsmarkierung ist bewusst noch nicht verdrahtet. Dafür
  muss die Roboterseite zuerst ein eindeutiges Pose-Topic im `map`-Frame
  festlegen; alternativ müsste die App die TF-Kette auswerten.
- Das persönliche Signing-Team ist im Xcode-Projekt ausgewählt. Bei
  abgelaufenem kostenlosen Provisioning muss die App erneut aus Xcode auf das
  iPhone installiert werden.
- rosbridge bindet auf `0.0.0.0:9090` ohne TLS, Authentifizierung oder
  Topic-ACL. Für Betrieb außerhalb eines isolierten WLANs einen schmalen,
  authentifizierten `wss://`-Gateway davor setzen.
- Das gefundene frühe Cancel-Race im `mission_manager` wurde am 26.07.2026
  geschlossen: Ein Abbruch vor Erhalt des Goal-Handles wird vorgemerkt,
  `CancelGoal.Response` samt Goal-ID geprüft und ein neues Goal bis zum
  terminalen `WrappedResult.status` blockiert. Ein später Abbruch darf einen
  bereits erfolgreichen Lauf nicht in „abgebrochen“ umdeuten. Lokale
  Zustands-, Payload- und Outcome-Tests bestehen; der unmittelbare
  Start-und-Abbruch bleibt als Jetson-Integrationstest erforderlich.
- `go_to_room` und `pick_object` sind laut Backend derzeit Simulation;
  `pick_and_place` und `explore` laufen über den echten Behavior Tree.
- Es gibt im Repository noch keine Akkutelemetrie.

## Prüfbefehle

```bash
cd /Volumes/64GB/roboter_ws/ios/Robotersteuerung
swift test --scratch-path /tmp/robotersteuerung-swift-tests
python3 -m unittest discover -s Tools -p 'test_mock_rosbridge.py' -v
xcodebuild -list -project Robotersteuerung.xcodeproj
xcodebuild \
  -project Robotersteuerung.xcodeproj \
  -scheme Robotersteuerung \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
  test
xcodebuild \
  -project Robotersteuerung.xcodeproj \
  -scheme Robotersteuerung \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
  SWIFT_STRICT_CONCURRENCY=complete \
  SWIFT_TREAT_WARNINGS_AS_ERRORS=YES \
  build
```

Backend-Validierung und Cancel-Outcome-Logik ohne ROS-Laufzeit:

```bash
cd /Volumes/64GB/roboter_ws
PYTHONPATH=src/mission_manager \
  python3 -m unittest discover -s src/mission_manager/test -v
```

Lokaler Simulator-Mock:

```bash
cd /Volumes/64GB/roboter_ws/ios/Robotersteuerung
python3 Tools/mock_rosbridge.py
# In der App: ws://127.0.0.1:9090/
# Ereignisse: http://127.0.0.1:9091/events
# Karte ändern/zurücksetzen:
# http://127.0.0.1:9091/map-update
# http://127.0.0.1:9091/map-reset
# Späten SLAM-Start simulieren:
# http://127.0.0.1:9091/map-disable
# http://127.0.0.1:9091/map-enable
# Semantik zurücksetzen / konkurrierende Revision / stille Revision:
# http://127.0.0.1:9091/semantic-reset
# http://127.0.0.1:9091/semantic-bump
# http://127.0.0.1:9091/semantic-bump-silent
```

Nach jeder Protokolländerung mindestens die Tests in
`RobotersteuerungTests/RosbridgeProtocolTests.swift` beziehungsweise
`RobotMapProtocolTests.swift` anpassen und die alte PWA als Fallback auf
Kompatibilität prüfen.
