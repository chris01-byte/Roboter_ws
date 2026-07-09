# semantic_perception — Open-Vocabulary-Wahrnehmung (WP-5, Baustein B)

Erkennt Objekte per **Text-Anfrage** ("finde die Tasse") **ohne Neutraining** und liefert
ihre 3D-Pose über den **bestehenden** Service `GetObjectPose`. Dadurch bleibt der
Behavior-Tree **unverändert**. Optional füllt der Node den Missionskatalog dynamisch.

> Läuft **offboard** (RTX-3090-Server) oder perspektivisch auf der **OAK-NPU**.
> Ersetzt/ergänzt das `object_world_model` aus der Gesamtdoku.

## Schnittstellen

| Rolle | Name | Typ |
|---|---|---|
| Service | `<service_name>` (`/world_model/get_object_pose`) | `robot_interfaces/GetObjectPose` |
| Subscribe | `<rgb_topic>` (`/oak/rgb`) | `sensor_msgs/Image` *(für echte Modelle)* |
| Publish (opt) | `<catalog_topic>` (`/semantic/catalog_json`) | `std_msgs/String` |
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
depth_topic: "/oak/stereo/depth"   # + camera_info_topic passend zur Kamera
```
Ablauf: RGB-Bild → YOLO-World mit dem Text-Query → beste 2D-Box → Tiefe an der Box-Mitte
+ Kamera-Intrinsics → 3D-Punkt → TF in den `map`-Frame. Fehlt eine Voraussetzung
(Bibliothek/Bild/Tiefe/Intrinsics), fällt der Node automatisch auf den Stub zurück.

## Start & Test

```bash
ros2 launch semantic_perception semantic_perception.launch.py
```
Objekt abfragen (Stub liefert eine Pose für bekannte Objekte):
```bash
ros2 service call /world_model/get_object_pose robot_interfaces/srv/GetObjectPose \
  "{class_name: 'Tasse'}"
```
Dynamischen Katalog beobachten:
```bash
ros2 topic echo /semantic/catalog_json
```

## Parameter

Alle in [config/semantic_perception_params.yaml](config/semantic_perception_params.yaml)
(mit Index). Wichtig: `class_queries`/`known_rooms` konsistent zum Missionskatalog halten;
`service_name` entspricht dem, was der Behavior-Tree aufruft (`bt_params.yaml`).

## Grenzen / offen

- `yoloworld` ist eingebaut, aber **in ROS/GPU noch nicht getestet** (API-Stand ultralytics).
  `cv_bridge` + `ultralytics` müssen installiert sein; Tiefe/CameraInfo müssen zur Kamera passen.
- Für `owlvit`/NanoOWL analog `_detect_with_model()` erweitern.
- `py_compile` bestanden.
