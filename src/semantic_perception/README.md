# semantic_perception — Open-Vocabulary-Wahrnehmung (WP-5, Baustein B)

Erkennt Objekte per **Text-Anfrage** ("finde die Tasse") **ohne Neutraining** und liefert
ihre 3D-Pose über den **bestehenden** Service `GetObjectPose`. Dadurch bleibt der
Behavior-Tree **unverändert**. Optional publiziert der Node ausschließlich einen
getrennten Wahrnehmungs-Diagnosekatalog; er füllt den Missionskatalog nicht.

> Läuft **offboard** (RTX-3090-Server) oder perspektivisch auf der **OAK-NPU**.
> Ersetzt/ergänzt das `object_world_model` aus der Gesamtdoku.

## Schnittstellen

| Rolle | Name | Typ |
|---|---|---|
| Service | `<service_name>` (`/world_model/get_object_pose`) | `robot_interfaces/GetObjectPose` |
| Subscribe | `/oak/semantic/rgb/compressed` | `sensor_msgs/CompressedImage` (JPEG) |
| Subscribe | `/oak/semantic/depth/compressed` | `sensor_msgs/CompressedImage` (verlustfreies 16UC1-PNG) |
| Subscribe | `/oak/semantic/camera_info` | `sensor_msgs/CameraInfo` |
| Publish (opt) | `<catalog_topic>` (`/semantic/perception_catalog_json`) | `std_msgs/String` |
| TF | `<camera_frame>` → `<global_frame>` | für 3D-Projektion |

## Modell-Backend

| `model_backend` | Verhalten |
|---|---|
| `stub` (Standard) | Simulierte Erkennung – feste Pose für bekannte `class_queries`. Für den Trockentest. |
| `yoloworld` | **Implementiert**: YOLO-World (open-vocabulary) via `ultralytics` + 3D-Projektion aus Tiefe. |
| `owlvit` | Platzhalter (OWL-ViT / NanoOWL) – in `_detect_with_model()` analog einhängen. |

### YOLO-World aktivieren
```bash
pip install ultralytics          # auf dem Server (RTX 3090)
```
Dann in `config/semantic_perception_params.yaml`:
```yaml
model_backend: "yoloworld"
model_path: "yolov8s-worldv2.pt"   # wird beim ersten Lauf geladen
compressed_input: true
rgb_topic: "/oak/semantic/rgb/compressed"
depth_topic: "/oak/semantic/depth/compressed"
camera_info_topic: "/oak/semantic/camera_info"
```
Ablauf: RGB-Bild → YOLO-World mit dem Text-Query → beste 2D-Box → Tiefe an der Box-Mitte
+ Kamera-Intrinsics → 3D-Punkt → TF in den `map`-Frame. Fehlt eine Voraussetzung
(Bibliothek/Bild/Tiefe/Intrinsics/TF), meldet der Node fail-closed `found: false`.
Eine simulierte Pose wird ausschließlich mit dem ausdrücklich konfigurierten
`model_backend: "stub"` erzeugt; ein reales Backend fällt niemals auf den Stub zurück.
Die App- und Servicebegriffe aus `class_queries` bleiben deutsch. Die parallel
konfigurierten `model_class_prompts` bilden sie positionsgleich auf robuste
englische YOLO-World-/CLIP-Prompts ab, zum Beispiel `Tasse` auf `cup`. Dieses
Modellvokabular wird vor dem ersten CUDA-Lauf einmalig gesetzt. Antworten werden
danach anhand des zugeordneten tatsächlichen Modell-Prompts gefiltert; unbekannte
Serviceanfragen oder eine mehrdeutige Prompt-Konfiguration liefern keinen Treffer
beziehungsweise verhindern den Node-Start.

## OAK-Transport zum KI-Server

`robot_bringup/oak.launch.py` startet auf dem Jetson standardmaessig den
`semantic_stream_relay`. Er liest die OAK-Rohbilder ausschliesslich lokal mit
Best-Effort/KEEP_LAST(1), gleicht RGB und Tiefe in einem kleinen begrenzten
Zeitstempelpuffer ab und sendet nur 2 Hz komprimiert zum Server. Das Tiefen-PNG
bleibt 16 Bit und damit fuer die 3D-Projektion verlustfrei. Der Server darf
`/oak/rgb/image_raw`, `/oak/rgb/image_rect` oder `/oak/stereo/image_raw` nicht
direkt abonnieren; solche Offboard-Abonnenten erzeugten im A/B-Test Rueckstau
bis in `image_proc` und liessen RGB unter 1 Hz fallen.

DepthAIs geraeteinterne Pipeline-Synchronisierung bleibt bewusst aus: Sie
reduzierte den Mittelwert zwar, erzeugte im Realtest aber wiederholt bis zu
10 s lange RGB-Luecken. Stattdessen haelt der Relay hoechstens 80 lokale
Frames beziehungsweise 2 s vor und ordnet die spaeter eintreffende Tiefe ueber
den originalen Quellzeitstempel dem passenden RGB-Bild zu.

Die RGB-Entzerrung laeuft als eigener `robot_bringup/oak_rectifier`-Prozess.
Der DepthAI-Unterlaunch bekommt absichtlich `rectify_rgb=false`, damit kein
Rectifier im single-threaded OAK-Komponentencontainer laeuft. Der Standard-
`image_proc`-CameraSubscriber verlor im A/B-Dauertest spaeter ebenfalls nur
seine RGB-Zustellung, waehrend dasselbe Rohbild-Topic weiter 10,0 Hz lieferte.
Der eigene Node liest Bild und CameraInfo deshalb unabhaengig mit
Best-Effort/KEEP_LAST(1) und verwendet die jeweils letzte gueltige Kalibrierung.
Er verweigert abweichende Bild-/Kalibrierungsaufloesungen fail-closed.
`/oak/rgb/image_rect` bleibt fuer RTAB-Map unveraendert erhalten; sein Zustand
steht zusaetzlich unter `/oak/rgb/rectifier_status_json`. Ein ueber 3 s stiller
lokaler Bildeingang wird wie beim Relay durch einen begrenzten, im Status
gezaehlten Neuaufbau genau dieser Subscription geheilt.

Der Status ist unter `/oak/semantic/stream_status_json` sichtbar. Fuer einen
bewussten lokalen Kameratest ohne Relay:

Bleibt trotz laufendem OAK-Publisher nur ein lokaler RGB- oder Tiefen-Endpunkt
laenger als 3 s still, baut der Relay ausschliesslich diese Best-Effort-
Subscription neu auf. Alte Bilder bleiben durch die 2-s-Frischegrenze gesperrt;
`subscription_restarts` im Status macht jede Selbstheilung sichtbar.

```bash
ros2 launch robot_bringup oak.launch.py semantic_relay:=false
```

## Start & Test

```bash
ros2 launch semantic_perception semantic_perception.launch.py
```
Objekt abfragen (Stub liefert eine Pose für bekannte Objekte):
```bash
ros2 service call /world_model/get_object_pose robot_interfaces/srv/GetObjectPose \
  "{class_name: 'Tasse'}"
```
Dynamischen Wahrnehmungskatalog beobachten:
```bash
ros2 topic echo /semantic/perception_catalog_json
```

Der kanonische Raumkatalog `/semantic/catalog_json` wird vom
`semantic_map_manager` publiziert. `semantic_perception` verwendet bewusst ein
eigenes Diagnose-Topic, damit fluechtige beziehungsweise simulierte
Objekterkennung keine manuell bestaetigten Raeume ueberschreibt.

## Parameter

Alle in [config/semantic_perception_params.yaml](config/semantic_perception_params.yaml)
(mit Index). `class_queries`/`known_rooms` betreffen nur Wahrnehmung und das getrennte
Diagnose-Topic; `service_name` entspricht dem, was der Behavior-Tree aufruft
(`bt_params.yaml`).

## Grenzen / offen

- Die positive OAK-3D-Projektion ist mit einem motorlosen Test-TF abgenommen.
  Eine positive Pose im echten `map`-Frame bleibt an die separat bestaetigte
  Roboterlokalisierung gebunden. Ohne diesen TF antwortet das reale Backend
  absichtlich `found: false`.
- `cv_bridge`, OpenCV und `ultralytics` müssen installiert sein;
  Tiefe/CameraInfo müssen zur Kamera passen.
- Die Abnahme lief mit 640 x 360. Ein dauerhaftes hochaufloesendes
  Semantikprofil braucht eine eigene Messung von WLAN-Datenrate, Latenz und
  GPU-Last; das 320-x-180-Navigationsprofil bleibt davon getrennt.
- Für `owlvit`/NanoOWL analog `_detect_with_model()` erweitern.
- Der Transport bleibt auf 640 x 360 und 2 Hz begrenzt. Das ist das volle
  Kamerabild, nicht ein asymmetrischer Ausschnitt; hoehere Pixelaufloesung ist
  eine getrennte, noch nicht freigegebene Lastmessung.
