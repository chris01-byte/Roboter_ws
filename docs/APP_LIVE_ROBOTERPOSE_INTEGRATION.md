# Live-Roboterpose in der iOS-App

## Integrationsanweisung für den nächsten Agenten

**Planungsstand:** 16.08.2026

**Ziel:** Die iOS-App zeigt die aktuelle Position und Blickrichtung von
Amadeus auf der bereits dargestellten Karte an. Die Anzeige soll sich ungefähr
einmal pro Sekunde aktualisieren, ohne Navigation auszulösen oder Teil der
Sicherheitskette zu werden.

Diese Datei ist die verbindliche technische Übergabe für die Implementierung.
Vor Änderungen zusätzlich `AGENTS.md`, `docs/PROJECT_MEMORY.md`,
`docs/INVENTORY.md` und `tools/kartierung/README.md` vollständig lesen.

---

## 1. Ergebnis, das gebaut werden soll

Im Karten-Tab erscheint ein gut sichtbarer Robotermarker:

- sein Mittelpunkt liegt auf der aktuellen Position im ROS-Frame der
  angezeigten Karte;
- seine Spitze zeigt in die tatsächliche Vorwärtsrichtung des Roboters;
- Position und Richtung folgen Zoom, Pan, Kartenursprung und einer eventuell
  gedrehten Karte korrekt;
- neue Werte erscheinen ungefähr einmal pro Sekunde und werden für die
  Darstellung weich animiert;
- nur eine für genau diese Kartenversion bestätigte globale Lokalisierung wird
  als aktuelle Position dargestellt;
- bei verlorener oder veralteter Lokalisierung darf die letzte Pose nicht
  unbemerkt wie eine aktuelle Pose aussehen;
- die App sendet durch diese Funktion keinerlei ROS-Befehl.

Die Funktion ist ausschließlich eine Visualisierung. Sie darf weder eine
Mission freigeben noch einen Sicherheitsmechanismus ersetzen. Die vorhandenen
Freigaben in `mission_manager` und `cmd_vel_mission_gate` bleiben die alleinige
Wahrheit für Bewegung.

## 2. Bewusste Nicht-Ziele

In dieser Änderung nicht implementieren:

- keine Fahrt, Zielwahl oder automatische Kartenzentrierung;
- keine Berechnung von TF in der App;
- kein direktes Verwenden von `/odom`, `/amcl_pose` oder
  `/localization_pose` als Bildschirm-Pose;
- keine Positionshistorie, Fahrspur oder Cloud-Synchronisierung;
- keine Speicherung der letzten Roboterpose in `UserDefaults`, Dateien,
  Telemetrie oder Analytics;
- keine Backend-Parameteränderung und keine neue ROS-Publisherschnittstelle;
- keine reale Wohnungs- oder Positionsaufzeichnung im Repository.

Eine Fahrspur kann später als getrennte Funktion ergänzt werden. Für den
ersten belastbaren Stand ist eine ehrliche aktuelle Pose wichtiger als eine
optisch aufwendige Historie.

---

## 3. Bereits vorhandene und geprüfte Grundlagen

### 3.1 Posequelle

`robot_map_manager` veröffentlicht bereits:

| Eigenschaft | Vertrag |
|---|---|
| Topic | `/robot_map_manager/robot_pose` |
| ROS-Typ | `geometry_msgs/msg/PoseStamped` |
| Konfiguration | `src/robot_map_manager/config/robot_map_manager.yaml` |
| Backend-Rate | `pose_publish_rate_hz: 5.0` |
| Position | TF vom Frame der aktuellen Karte nach `base_link` |
| Frame | `header.frame_id` entspricht dem Frame der aktuellen `/map` |

Der Kartenmanager publiziert nur, nachdem Koordinaten, Quaternion und
TF-Zeitstempel geprüft wurden. Dynamische TFs dürfen standardmäßig höchstens
eine Sekunde alt sein. Die App soll diese geprüfte, appnahe Schnittstelle
verwenden und nicht selbst `map -> base_link` zusammensetzen.

### 3.2 Wahrheit über die Lokalisierung

Die Existenz einer Pose allein beweist keine korrekte globale Lokalisierung.
Die Freigabe liefert der bestehende `localization_guard`:

| Topic | Typ | Bedeutung |
|---|---|---|
| `/localization/status_json` | `std_msgs/msg/String` | Ausführlicher, kartenbezogener Zustand |
| `/localization/ready` | `std_msgs/msg/Bool` | Fail-closed Freigabe für andere ROS-Nodes |

Für die App wird `/localization/status_json` verwendet. Der JSON-Status enthält
mindestens:

- `schema_version`;
- `ready` und `state`;
- `reasons`;
- `map_fingerprint`;
- `global_initialization` und Angaben zum verifizierten Vollscan;
- `covariance`;
- `time` als Unix-Zeit des Jetsons.

Das Status-Topic wird mit 5 Hz und `TRANSIENT_LOCAL` veröffentlicht. Wegen
dieser Latch-Eigenschaft darf die erste Nachricht nach einem Reconnect nicht
sofort als Beweis für einen aktuell laufenden Publisher gelten. Die Behandlung
dazu steht in Abschnitt 8.

### 3.3 Kartenbindung

Die App empfängt schon `/map` als `nav_msgs/OccupancyGrid` und berechnet dafür
`RobotMapSnapshot.contentFingerprint`. Derselbe SHA-256-Fingerabdruck wird vom
Kartenmanager, der semantischen Karte und dem Lokalisierungswächter verwendet.

Ein Robotermarker ist nur **aktuell und bestätigt**, wenn gleichzeitig gilt:

1. eine live empfangene Karte ist vorhanden;
2. Kartenmanager-Summary und Live-Karte stimmen wie bisher überein;
3. `localization/status_json.ready == true`;
4. `localization.map_fingerprint == map.contentFingerprint`;
5. Kartenframe der Pose und `map.frameID` stimmen exakt überein;
6. Pose, Kartenmanagerstatus und Lokalisierungsstatus sind im aktuellen
   WebSocket-Zyklus frisch.

### 3.4 Bestehende Bildschirmtransformation

`RobotMapViewportTransform` in `RobotMapModels.swift` beherrscht bereits:

- Aspect-Fit der OccupancyGrid-Grafik;
- Kartenursprung mit Translation und Quaternion/Yaw;
- die vertikale Spiegelung von ROS-OccupancyGrid zu Bildkoordinaten;
- Zoom und Pan;
- Hin- und Rücktransformation zwischen Karte und Bildschirm.

Die Markerposition muss zwingend mit
`RobotMapViewportTransform.screenPoint(for:)` berechnet werden. Keine zweite,
ähnlich aussehende Formel im View oder Controller anlegen. Sonst driften
Raumpolygone, Navigationsziele und Roboterpose bei gedrehtem Ursprung oder Zoom
auseinander.

---

## 4. Festgelegter Datenfluss

```text
map -> base_link (TF)
        |
        v
robot_map_manager -- /robot_map_manager/robot_pose (PoseStamped, 5 Hz)
        |            /robot_map_manager/status_json
        |                         |
        +------------ rosbridge -+-------------------+
                                  |                   |
localization_guard -- /localization/status_json -----+
                                                      v
                                         RobotMapController
                                                      |
                                   Karten-/Frame-/Frischeprüfung
                                                      |
                                                      v
                                         RobotMapCanvas-Overlay
```

Alle drei zusätzlichen Eingänge laufen über die bereits für die Karte
vorhandene WebSocket-Verbindung. Keine dritte Verbindung eröffnen. Die große
Karte bleibt damit weiterhin von der Steuerungs-/Not-Aus-Verbindung getrennt,
während Pose und Kartenstatus konsistent in derselben Karten-Session liegen.

Die App drosselt nur die Pose auf ungefähr 1 Hz. Die Backend-Rate von 5 Hz
bleibt unverändert, weil andere lokale Verbraucher sie nutzen können und die
Validierung damit schnell auf einen ungültigen TF reagiert.

---

## 5. Rosbridge-Vertrag

### 5.1 Neue Konstanten

In `MapRosbridgeProtocol.swift` ergänzen:

```swift
static let robotPoseTopic = "/robot_map_manager/robot_pose"
static let robotPoseSubscriptionID = "amadeus-robot-map-pose"
static let localizationStatusTopic = "/localization/status_json"
static let localizationStatusSubscriptionID = "amadeus-localization-status"
```

### 5.2 Subscribe

Zu `connectionSetupFrames()` kommen zwei Subscriptions:

```json
{
  "op": "subscribe",
  "id": "amadeus-robot-map-pose",
  "topic": "/robot_map_manager/robot_pose",
  "type": "geometry_msgs/PoseStamped",
  "throttle_rate": 1000,
  "queue_length": 1
}
```

```json
{
  "op": "subscribe",
  "id": "amadeus-localization-status",
  "topic": "/localization/status_json",
  "type": "std_msgs/String",
  "queue_length": 1
}
```

`throttle_rate: 1000` begrenzt die an die App gesendete Pose auf höchstens
ungefähr eine Nachricht pro Sekunde. Für den kleinen Lokalisierungsstatus ist
keine Drosselung nötig; seine 5 Hz ermöglichen eine schnelle Stale-Erkennung.

Zu `connectionTeardownFrames()` gehören die spiegelbildlichen Unsubscribes mit
derselben ID und demselben Topic. Setup- und Teardown-Tests müssen die neuen
Frames in exakter Reihenfolge und mit exakten Feldern abdecken.

### 5.3 Erwartete Pose-Nachricht

Rosbridge liefert ROS-2-Zeitfelder in der hier bereits vom Mock verwendeten
Form `sec`/`nanosec`:

```json
{
  "op": "publish",
  "topic": "/robot_map_manager/robot_pose",
  "msg": {
    "header": {
      "stamp": {"sec": 123, "nanosec": 456000000},
      "frame_id": "map"
    },
    "pose": {
      "position": {"x": 1.2, "y": -0.4, "z": 0.0},
      "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
    }
  }
}
```

Die Zahlen sind rein synthetische Testwerte und keine reale Roboterposition.

### 5.4 Decoderregeln

`decodeRobotPose(from:)` muss:

- fremde Topics mit `nil` ignorieren;
- kaputtes äußeres JSON als `invalidTextFrame` melden;
- eine unvollständige Pose als neuen Fehler `invalidRobotPose` melden;
- alle sieben Positions-/Quaternionwerte auf `isFinite` prüfen;
- einen Quaternionbetrag nahe null ablehnen;
- nur normalisierte Quaternionen mit einer Toleranz von `1e-3` akzeptieren;
- `frame_id` trimmen und dieselben Zeichen-/Längenregeln wie die Karte
  anwenden;
- `sec >= 0` und `0 <= nanosec < 1_000_000_000` prüfen;
- die Umrechnung in Nanosekunden mit einer expliziten `Int64`-
  Überlaufprüfung absichern;
- den Zeitstempel zu Diagnosezwecken behalten, aber nicht allein zur
  App-Frischeprüfung verwenden. Ein gültiger TF kann nach der im Backend
  dokumentierten Static-TF-Konvention Stamp 0 besitzen.

Yaw wird nach erfolgreicher Quaternionprüfung berechnet:

```text
yaw = atan2(2 * (w*z + x*y), 1 - 2 * (y*y + z*z))
```

Das Ergebnis auf `[-pi, pi]` normalisieren.

### 5.5 Lokalisierungsstatus

`decodeLocalizationStatus(from:)` dekodiert die innere JSON-Zeichenkette eines
`std_msgs/String`. Für die Anzeige reichen als eigenes, streng validiertes
Modell zunächst:

```swift
struct LocalizationStatusEnvelope {
    let schemaVersion: Int
    let ready: Bool
    let state: String
    let reasons: [String]
    let mapFingerprint: String?
    let globalInitialization: String
    let time: Double
}
```

Regeln:

- nur `schema_version == 1` akzeptieren;
- `state` und `global_initialization` müssen nichtleer sein;
- höchstens 64 Gründe, jeder höchstens 512 Zeichen;
- `time` muss endlich und positiv sein;
- ein vorhandener Fingerabdruck muss exakt 64 kleine Hex-Zeichen haben;
- `ready == true` erfordert zusätzlich einen gültigen Fingerabdruck,
  `state == "localized"` und `global_initialization == "completed"`;
- unbekannte zusätzliche Backend-Felder werden zur Vorwärtskompatibilität
  ignoriert.

Die Gründe sind Diagnoseanzeige, niemals ungefiltert ein Log- oder
Telemetriekanal.

---

## 6. App-Datenmodelle

In `RobotMapModels.swift` reine, testbare Werte ergänzen. Namen dürfen an den
lokalen Stil angepasst werden, ihre Trennung soll erhalten bleiben.

```swift
struct RobotPoseSample: Equatable, Sendable {
    let point: MapPoint
    let yaw: Double
    let frameID: String
    let sourceStampNanoseconds: Int64
    let receivedAt: Date
    let socketGeneration: UInt64
}

enum RobotPoseDisplayState: Equatable, Sendable {
    case unavailable(message: String)
    case localizing(message: String)
    case live(RobotPoseSample)
    case lastKnown(RobotPoseSample, message: String)
}
```

Zusätzlich `RobotMapManagerStatusEnvelope` um das vorhandene Backendfeld
`pose` erweitern. Das Feld zunächst optional dekodieren, damit eine ältere
Mock- oder Backendversion als klarer Kompatibilitätszustand behandelt werden
kann, statt den gesamten Kartenstatus zu zerstören:

```swift
struct PoseState: Decodable, Equatable, Sendable {
    let available: Bool
    let topic: String
    let targetFrame: String?
    let snapshotFrame: String?
    let baseFrame: String
    let lastPublished: String?
    let zeroStampStaticAssumption: Bool?
    let tfStampNanoseconds: Int64?
    let tfAgeSeconds: Double?
    let maximumDynamicTFAgeSeconds: Double
    let error: String?
}
```

Die Coding Keys entsprechen den Backendnamen `target_frame`,
`snapshot_frame`, `base_frame`, `last_published`,
`zero_stamp_static_assumption`, `tf_stamp_ns`, `tf_age_seconds` und
`maximum_dynamic_tf_age_s`.

Eine grüne Live-Anzeige verlangt `pose.available == true`, das erwartete Topic
und übereinstimmende Ziel-/Snapshotframes. Fehlt das gesamte optionale Feld,
lautet der Zustand sinngemäß „Kartenmanager liefert noch keine Pose-Prüfung“;
er darf nicht stillschweigend grün werden.

---

## 7. Koordinaten und Blickrichtung

### 7.1 Position

Vor der Darstellung:

1. `sample.frameID == map.frameID` prüfen;
2. Pose in die lokalen Kartenkoordinaten zurückdrehen;
3. prüfen, dass lokale x/y innerhalb
   `0 ... width*resolution` und `0 ... height*resolution` liegen;
4. erst danach `RobotMapViewportTransform.screenPoint(for:)` aufrufen.

Eine außerhalb liegende Pose wird nicht am Kartenrand festgeklemmt. Sie ist
ein Diagnosefehler und wird nicht dargestellt.

### 7.2 Bildschirmwinkel

Der Marker wird so entworfen, dass seine Spitze bei Winkel 0 nach rechts,
also entlang der lokalen positiven Karten-x-Achse, zeigt. Dann gilt:

```text
screenHeading = -(robotYaw - map.origin.yaw)
```

Das Minuszeichen ist wegen der nach unten wachsenden Bildschirm-y-Achse
notwendig. `screenHeading` ebenfalls auf `[-pi, pi]` normalisieren.

Die Winkelberechnung gehört als reine Funktion zu den Modellen bzw. zur
Viewport-Transformation und muss mit den vier Hauptrichtungen getestet werden:

| ROS-Richtung bei origin-yaw 0 | Erwartete Bildschirmspitze |
|---|---|
| yaw 0° | rechts |
| yaw +90° | oben |
| yaw ±180° | links |
| yaw -90° | unten |

Ein zusätzlicher Test mit `map.origin.yaw = +90°` verhindert, dass die Formel
nur zufällig für die aktuelle Karte funktioniert.

---

## 8. Zustands-, Frische- und Reconnect-Regeln

Diese Regeln verhindern eine überzeugend aussehende, aber alte Position.

### 8.1 WebSocket-Generation

`RobotMapController` zählt bei jeder neu geöffneten Verbindung eine
`socketGeneration` hoch. Karte, Pose und Status werden ihrer Generation
zugeordnet. Werte verschiedener Generationen dürfen nie gemeinsam einen
Live-Zustand bilden.

Beim Start einer Verbindung, bei Socketfehler, `stop()`, App-Hintergrund oder
manuellem Retry sofort löschen:

- aktuelle Pose;
- Empfangszeiten;
- Lokalisierungsstatus und dessen Fortschrittszähler;
- Animationsstart/-ziel;
- letzte als live bestätigte Pose.

Die bereits vorhandene Karte darf wie heute als **NICHT LIVE** sichtbar
bleiben. Bei einem Socket-Lebenszykluswechsel wird der Robotermarker jedoch
sofort ausgeblendet. `lastKnown` ist nur für einen kurz veralteten oder
gesperrten Zustand innerhalb derselben noch verbundenen Socketgeneration
vorgesehen.

### 8.2 Schutz vor altem Transient-Local-Status

Nach einem Subscribe kann rosbridge zunächst den gelatchten letzten
Lokalisierungsstatus liefern. Für `live` daher innerhalb derselben
Socketgeneration mindestens **zwei** gültige Lokalisierungsstatus-Nachrichten
mit strikt steigendem `time` verlangen. Bei 5 Hz dauert das normalerweise
weniger als eine halbe Sekunde. Bleibt nur die gelatchte Nachricht, ist der
Zustand nicht live.

Ein rückwärts laufender oder unveränderter `time`-Wert wird nicht als neuer
Lebensnachweis gezählt. Nach einem Node-Neustart muss die neue Statusfolge
ebenfalls wieder zwei fortschreitende Werte liefern, bevor `live` möglich ist.

### 8.3 Zeitgrenzen der App

Als anfängliche, reine UI-Werte festlegen und als Konstanten testen:

| Signal | live bis | danach |
|---|---:|---|
| RobotPoseSample, lokal empfangen | 2,5 s | `lastKnown` |
| LocalizationStatus, lokal empfangen | 1,0 s | sofort nicht live |
| Kartenmanagerstatus, lokal empfangen | 4,5 s | sofort nicht live |
| letzte bestätigte Pose | weitere max. 5,0 s | Marker ausblenden |

Der Kartenmanager sendet seinen periodischen Status derzeit alle 2 Sekunden;
4,5 Sekunden lassen eine einzelne verzögerte Nachricht zu. Der
Lokalisierungsstatus kommt mit 5 Hz, deshalb ist eine Sekunde bereits eine
deutliche Störung. Frische wird mit lokalem monotonic/`Date`-Empfangsalter
bewertet, nicht nur durch Uhrenvergleich zwischen iPhone und Jetson.

Der Controller benötigt dafür einen kleinen, abbrechbaren Prüftask oder Timer
mit 250–500 ms Takt. Er prüft nur Zustand und sendet nichts. Der Task wird beim
Schließen des Sockets zuverlässig beendet.

### 8.4 Zustandsübergänge

- `unavailable`: keine Live-Karte, falsche Bindung, Protokollfehler oder noch
  nie eine Pose empfangen;
- `localizing`: Status vorhanden, aber `ready == false`, noch keine zwei
  fortschreitenden Statusmeldungen oder Kartenfingerabdruck fehlt;
- `live`: alle Verträge aus Abschnitt 3.3 und alle Fristen erfüllt;
- `lastKnown`: zuvor live, aber Pose/Status gerade veraltet oder
  Lokalisierung verloren; höchstens fünf Sekunden und klar grau markiert;
- danach `unavailable` und kein Marker.

Wenn `ready` auf `false` wechselt, ist der Marker sofort nicht mehr aktuell.
Die letzte Position darf kurz grau sichtbar bleiben, aber niemals mit der
Beschriftung „Aktuell“.

### 8.5 Kartenwechsel

Ändert sich `map.contentFingerprint` oder `map.frameID`, sofort Pose,
Statusfortschritt und Animation löschen. Erst eine neue Pose und eine
Lokalisierungsfreigabe für den neuen Fingerabdruck dürfen den Marker wieder
anzeigen. Ein bloß gleich benannter Frame `map` reicht nicht.

---

## 9. Darstellung in SwiftUI

### 9.1 Übergabe an den Canvas

`RobotMapView.mapCard` übergibt den geprüften `RobotPoseDisplayState` an
`RobotMapCanvas`. Der Canvas berechnet aus seinem bereits vorhandenen
`viewportTransform(in:)` Bildschirmposition und -winkel.

Den Marker im selben Overlay wie Räume und Navigationsziele oder in einem
direkt darüberliegenden, hit-test-freien Overlay zeichnen. Er muss:

- über Karte und Raumflächen liegen;
- unter Offline- und Fehlerhinweisen liegen;
- `.allowsHitTesting(false)` besitzen, damit der Raumeditor unverändert
  bedienbar bleibt;
- eine feste Bildschirmgröße von ungefähr 26–30 pt behalten; Zoom bewegt den
  Mittelpunkt, vergrößert aber nicht das Symbol;
- einen hellen Rand oder Schatten besitzen, damit er auf freien, belegten und
  farbigen Zellen erkennbar bleibt.

Empfohlene Zustände:

- `live`: kräftige Akzent-/Grünfarbe, gerichtete Spitze, kleiner Innenpunkt;
- `lastKnown`: grau, reduzierte Deckkraft, Beschriftung „LETZTE POSITION“;
- `localizing`: kein richtungsweisender Marker; stattdessen kompakter Hinweis
  „Position wird ermittelt …“;
- `unavailable`: kein Marker, verständlicher Statustext.

Die UI soll keine rohe Backend-Fehlerkette dauerhaft über die Karte legen.
Ein kurzer deutscher Status reicht; vollständige `reasons` können in einem
Diagnosebereich erscheinen.

### 9.2 Animation

Bei kleinen, aufeinanderfolgenden Live-Änderungen Position und Winkel mit
etwa 0,35–0,6 Sekunden `easeInOut` animieren. Nicht extrapolieren: Die App
kennt nur die zuletzt bestätigte Pose.

Eine globale AMCL-Korrektur darf nicht sichtbar quer durch Wände gleiten.
Deshalb ohne Animation auf die neue Pose springen, wenn mindestens eine
Bedingung gilt:

- Distanz zur letzten Pose größer als 0,50 m;
- kleinste Winkeldifferenz größer als 30°;
- Kartenfingerabdruck, Frame oder Socketgeneration hat sich geändert;
- der vorherige Zustand war nicht `live`.

Diese Schwellen steuern nur die Optik und haben keinerlei Einfluss auf
Navigation oder Sicherheit.

### 9.3 Bedienbarkeit und Accessibility

Der kombinierte Accessibility-Text soll zum Beispiel lauten:

```text
Roboterposition aktuell, x 1 Komma 20 Meter, y minus 0 Komma 40 Meter,
Blickrichtung 90 Grad.
```

Im Zustand `lastKnown` muss „letzte bekannte Position“ gesagt werden.
Zahlen auf eine sinnvolle Genauigkeit begrenzen; keine Zentimetergenauigkeit
versprechen, die die Lokalisierung nicht garantiert.

---

## 10. Änderungen nach Datei

### `ios/Robotersteuerung/Robotersteuerung/Services/MapRosbridgeProtocol.swift`

- Topics und Subscription-IDs ergänzen;
- Setup/Teardown erweitern;
- PoseStamped- und Localization-Status-Decoder ergänzen;
- neue, genaue Protokollfehler ergänzen;
- bestehende Befehls- und Kartenpfade nicht verändern.

### `ios/Robotersteuerung/Robotersteuerung/Models/RobotMapModels.swift`

- `RobotPoseSample`, `LocalizationStatusEnvelope` und
  `RobotPoseDisplayState` ergänzen;
- Kartenmanager-Posezustand abbilden;
- reine Validierungs-, Bounds-, Winkel- und Zustandsfunktionen ergänzen;
- vorhandenen `RobotMapViewportTransform` wiederverwenden.

### `ios/Robotersteuerung/Robotersteuerung/Services/RobotMapController.swift`

- neue `@Published private(set)`-Werte für Pose-/Lokalisierungsanzeige;
- eingehende Topics routen;
- Kartenversion, Frame, Backendstatus, `ready` und Frische zusammenführen;
- Socketgeneration und Fortschrittsprüfung verwalten;
- Stale-Prüftask starten/abbrechen;
- Zustände bei Reconnect, Stop, Hintergrund und Kartenwechsel löschen;
- keine Publish-, Mission- oder Fahrfunktion ergänzen.

### `ios/Robotersteuerung/Robotersteuerung/Views/RobotMapView.swift`

- Posezustand an `RobotMapCanvas` übergeben;
- Marker und kompakten Status darstellen;
- dieselbe Viewport-Transformation wie Räume/Ziele verwenden;
- Gesten und Raumeditor unverändert lassen.

### `ios/Robotersteuerung/RobotersteuerungTests/RobotMapProtocolTests.swift`

- exakte Subscribe-/Unsubscribe-Verträge aktualisieren;
- Decoder-, Validierungs-, Zustands-, Frische- und Geometrietests ergänzen;
- vorhandene Karten- und Raumtests unverändert grün halten.

### `ios/Robotersteuerung/Tools/mock_rosbridge.py`

- synthetische Pose und Lokalisierungsstatus ergänzen;
- Pose bei aktiver Subscription ungefähr mit Backendrate erzeugen; rosbridge-
  Drosselung entweder im Mock respektieren oder für den UI-Test mit 1 Hz
  senden;
- eine kleine, deterministische Route innerhalb der Testkarte anbieten;
- Endpunkte zum Pausieren, Verlieren der Lokalisierung, Pose-Sprung und
  Kartenwechsel ergänzen;
- keinerlei echte Karten- oder Messwerte verwenden.

### Dokumentation

- nach erfolgreicher Implementierung `ios/Robotersteuerung/README.md`
  aktualisieren;
- technische Entscheidung und Abnahme in `docs/PROJECT_MEMORY.md` festhalten;
- bei einer Änderung mit Wirkung auf Jetson-Start oder Backend zusätzlich
  `docs/ROBOT_TRANSFER.md` ergänzen. Für die geplante reine App-Subscription
  sollte keine Backendwirkung nötig sein.

---

## 11. Verbindliche Tests

### 11.1 Reine Swift-/Protokolltests

Mindestens folgende Fälle automatisieren:

1. gültige Pose mit yaw 0 wird dekodiert;
2. fremdes Topic liefert `nil`;
3. fehlendes Feld, nichtendliche Zahl und Nullquaternion werden abgelehnt;
4. nichtnormalisierte Quaternion wird abgelehnt;
5. ungültige ROS-Zeit wird abgelehnt;
6. falscher Frame verhindert `live`;
7. Pose außerhalb der gedrehten Kartengrenzen wird abgelehnt;
8. Lokalisierung `ready:false` zeigt keine aktuelle Pose;
9. falscher Kartenfingerabdruck zeigt keine aktuelle Pose;
10. erst die zweite Nachricht mit steigendem `time` bestätigt einen laufenden
    Lokalisierungsstatus;
11. Stale-Grenzen 1,0/2,5/4,5/5,0 Sekunden werden exakt geprüft;
12. Reconnect und Kartenwechsel löschen die alte Pose;
13. Hauptrichtungen sowie origin-yaw +90° zeigen korrekt;
14. Position stimmt bei Aspect-Fit, Spiegelung, Zoom und Pan mit einem über
    dieselbe `screenPoint(for:)`-Funktion gezeichneten Raumziel überein;
15. große AMCL-Korrektur springt, kleine Änderung darf animiert werden;
16. Setup und Teardown enthalten jede ID genau einmal.

Zeitlogik als reine Policy mit injizierter Uhr testen. Keine Tests mit echten
`sleep`-Aufrufen bauen.

### 11.2 Mock-Tests

`Tools/test_mock_rosbridge.py` erweitern:

- Pose- und Status-Subscribe/Unsubscribe werden registriert;
- nur abonnierte Clients erhalten Daten;
- Reset löscht Subscriptions und Zustände korrekt;
- Pause führt reproduzierbar zum Stale-Zustand;
- Kartenwechsel liefert einen anderen Fingerabdruck und verlangt eine neue
  bestätigte Lokalisierung;
- malformed pose/status wird vom Mock gezielt erzeugt.

Ausführen:

```bash
cd ios/Robotersteuerung
python3 -m unittest discover -s Tools -p 'test_mock_rosbridge.py' -v
```

Auf dem Entwicklungs-Mac zusätzlich die im App-README dokumentierten Befehle
für `swift test` und `xcodebuild ... test` ausführen. Der Jetson ersetzt keinen
iOS-Build.

### 11.3 Manueller Simulator-Test

1. `python3 Tools/mock_rosbridge.py` starten.
2. App mit `ws://127.0.0.1:9090/` verbinden.
3. Karten-Tab öffnen und prüfen, dass der Marker der synthetischen Route folgt.
4. Zoomen und verschieben: Marker, Räume und Ziele müssen deckungsgleich
   bleiben.
5. Alle vier Blickrichtungen auslösen.
6. Pose-Stream pausieren: spätestens nach 2,5 Sekunden nur noch klar als
   letzte Position, nach weiteren höchstens fünf Sekunden kein Marker.
7. Lokalisierung auf `ready:false`: sofort keine aktuelle Pose.
8. Verbindung schließen und neu öffnen: keine alte Pose darf kurz grün
   aufblitzen.
9. Mock-Karte wechseln: Marker bleibt aus, bis Status und Pose zur neuen
   Kartenversion gehören.

### 11.4 Motorloser Jetson-Test

Dieser Test aktiviert keine Aktoren. Vorher prüfen, welche Prozesse bereits
laufen; keine zweite Instanz starten.

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash

ros2 topic info /robot_map_manager/robot_pose --verbose
ros2 topic hz /robot_map_manager/robot_pose
ros2 topic echo --once --full-length /robot_map_manager/robot_pose
ros2 topic echo --once --full-length --qos-durability transient_local \
  /localization/status_json --field data
ros2 topic echo --once --full-length --qos-durability transient_local \
  /robot_map_manager/status_json --field data
```

Danach das iPhone verbinden und ohne Motorstrom verifizieren:

- Karte und Marker erscheinen;
- Kartenfingerabdruck und Frame stimmen;
- die beobachtete Blickrichtung passt innerhalb der praktisch erkennbaren
  Genauigkeit;
- bei Stoppen des Lokalisierungs-/Posepublishers wird die Anzeige fristgerecht
  grau und verschwindet;
- die App hat keinen Publisher auf Fahr- oder Initialpose-Topics angelegt.

Vor Prozessstopps die Hinweise in `tools/kartierung/README.md` beachten. Keine
Prozessgruppe pauschal signalisieren.

### 11.5 Beaufsichtigter Fahrtest

Erst nach bestandenen automatischen, Simulator- und motorlosen Tests. Wegen
der physischen Wirkung ist dafür unmittelbar vor dem Test erneut die nach
`AGENTS.md` erforderliche Fahrfreigabe einzuholen; freie Fläche und Hardware-
Not-Aus müssen bestätigt sein.

Der Roboter fährt eine kurze, begrenzte Strecke und dreht langsam. Ein äußerer
Beobachter vergleicht:

- Bewegungsrichtung auf dem Boden gegen Bewegung des Markers;
- tatsächliche Front gegen Markerspitze;
- Stillstand gegen stabilen Marker;
- gezielten Lokalisierungsverlust gegen sofortige Statusänderung.

Diese visuelle Abnahme ist wichtig, aber kein Zentimeter-Messnachweis. Die
softwareseitige Karten-/LiDAR-Verifikation bleibt die belastbarere Grundlage
für die globale Pose.

---

## 12. Abnahmekriterien

Die Integration ist erst abgeschlossen, wenn alle folgenden Punkte erfüllt
und dokumentiert sind:

- [ ] Marker nutzt `/robot_map_manager/robot_pose`, nicht `/odom` oder eine
      eigene TF-Berechnung.
- [ ] Eine gültige neue Pose wird unter normalen WLAN-Bedingungen innerhalb
      von höchstens 1,5 Sekunden sichtbar.
- [ ] Position bleibt bei Zoom, Pan, Aspect-Fit und gedrehtem Kartenursprung
      deckungsgleich.
- [ ] Blickrichtung besteht die vier Hauptrichtungs- und origin-yaw-Tests.
- [ ] Grün/„aktuell“ erscheint nur bei frischer, global bestätigter
      Lokalisierung für denselben Kartenfingerabdruck.
- [ ] Veraltete Pose wird spätestens nach 2,5 Sekunden als letzte Position
      kenntlich und nach weiteren höchstens fünf Sekunden ausgeblendet.
- [ ] `ready:false`, Framefehler, Fingerprintwechsel und Reconnect arbeiten
      fail-closed und zeigen nie unbemerkt eine alte aktuelle Pose.
- [ ] Raumeditor, Kartenspeichern, Navigation und Not-Aus-Verhalten zeigen
      keine Regression.
- [ ] Swift-Tests, Python-Mocktests und verfügbarer Xcode-Testlauf sind grün.
- [ ] Motorloser Jetson-Test ist protokolliert.
- [ ] Es wurden keine Geheimnisse, echten Karten, Bilder, Bags oder
      Positionsverläufe committed.
- [ ] Diff, Hardwarewirkung und Rückfallweg sind im Commit/PR beschrieben.

## 13. Rückfallweg

Die Änderung soll so geschnitten sein, dass der bestehende Karten-Tab ohne
Pose weiterhin funktioniert. Bei einem Fehler:

1. Pose- und Localization-Subscriptions aus Setup/Teardown entfernen;
2. Posezustand und Overlay entfernen;
3. vorhandene `/map`-, Kartenmanager- und Semantikpfade unverändert lassen;
4. App neu bauen.

Ein Backend-Rollback ist für diese reine Leserfunktion nicht erforderlich.
Fällt die neue Posequelle aus, muss die App lediglich „Position nicht
verfügbar“ anzeigen; Karte, Räume und bestehende Steuerung bleiben nutzbar.

## 14. Empfohlene Arbeitsreihenfolge für den implementierenden Agenten

1. Von einem getesteten Stand einen eigenen Branch
   `feature/app-live-roboterpose` anlegen.
2. Protokollmodelle und reine Policyfunktionen implementieren.
3. Alle Decoder-, Geometrie- und Zeitlogiktests hinzufügen.
4. Mock samt Fehlerendpunkten erweitern und Python-Tests ausführen.
5. Controllerzustand und Reconnect-Bereinigung integrieren.
6. Marker-Overlay und Accessibility ergänzen.
7. Swift-/Xcode- und Simulatorabnahme durchführen.
8. Erst danach motorlos auf dem Jetson prüfen.
9. Einen beaufsichtigten Fahrtest nur als getrennte letzte Abnahme durchführen.
10. Dokumentation aktualisieren, Geheimnis-/Datenschutzprüfung ausführen,
    gezielt committen und pushen.

Damit erhält die App eine Roborock-ähnliche Live-Anzeige, ohne die wichtigste
Eigenschaft des aktuellen Systems zu verlieren: Eine schön gezeichnete Pose
gilt erst dann als wahr, wenn die globale Lokalisierung sie für exakt die
angezeigte Karte bestätigt hat.
