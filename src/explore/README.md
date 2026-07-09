# explore – Autonome Frontier-Exploration (WP-5, Ebene 1)

Lässt den Roboter die Wohnung **selbstständig und zielgerichtet** erkunden –
**kein Zufallsgenerator**. Grundlage ist die bewährte *Frontier*-Methode:
Der Node sucht in der SLAM-Karte die Grenzen zwischen bekannt-freiem und
unbekanntem Raum, bewertet sie nach Kosten/Nutzen und schickt die beste als
Fahrziel an Nav2 – bis keine Frontier mehr übrig ist (Wohnung vollständig).

**CPU-only, kein CUDA/LLM nötig.**

## Einordnung (Schichten-Architektur)

```
mission_manager / Behavior-Tree  --Action ExploreArea-->  explore_node
explore_node                     --Action navigate_to_pose-->  Nav2
Reaktive Sicherheit (collision_monitor, VL53) bleibt autonom aktiv.
```

## Schnittstellen

| Rolle | Name | Typ |
|---|---|---|
| Action-Server | `/explore_area` | `robot_interfaces/ExploreArea` |
| Action-Client | `navigate_to_pose` | `nav2_msgs/NavigateToPose` |
| Subscribe | `<map_topic>` (`/map`) | `nav_msgs/OccupancyGrid` |
| TF | `<global_frame>` → `<robot_base_frame>` | Roboterpose |
| Publish (optional) | `<marker_topic>` (`/explore/frontiers`) | `visualization_msgs/MarkerArray` |

## Start

```bash
ros2 launch explore explore.launch.py
```

Voraussetzung: SLAM publiziert eine Karte auf `map_topic` **und** Nav2 läuft
(Action `navigate_to_pose`).

## Schnelltest ohne Behavior-Tree

```bash
ros2 action send_goal /explore_area robot_interfaces/action/ExploreArea \
  "{timeout_s: 0.0, min_frontier_size_m: 0.0, return_to_start: false}"
```

## Parameter

Alle Werte in [config/explore_params.yaml](config/explore_params.yaml)
(mit Parameter-Index im Kopf). Wichtige Stellhebel:

- `min_frontier_size_m` – kleinste beachtete Frontier (Rauschfilter)
- `potential_scale` / `gain_scale` – Kosten/Nutzen-Gewichtung (nah vs. groß)
- `goal_timeout_s` – max. Fahrzeit pro Frontier
- `blacklist_radius_m` – sperrt gescheiterte Ziele (Selbstbefreiung)
- `return_to_start` – nach Fertigstellung zur Startpose zurück

## Grenzen / offen

- In ROS noch nicht kompiliert/getestet (wie die übrigen Pakete).
- Karten-Origin wird ohne Rotation angenommen (bei 2D-SLAM üblich).
- Später optional: Ersatz durch `explore_lite`/`nav2 wavefront`, falls gewünscht.
