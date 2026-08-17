# explore – Frontier- und adaptive Flaechenexploration

Lässt den Roboter die Wohnung **selbstständig und zielgerichtet** erkunden –
**kein Zufallsgenerator**. Nach einem kontrollierten 360-Grad-Rundblick sucht
der Node zuerst Grenzen zwischen bekannt-freiem und unbekanntem Raum. Sind
keine sicheren Frontiers mehr vorhanden, misst er die Abdeckung aus der realen
Fahrspur und waehlt den geodaetisch am weitesten entfernten, noch nicht
abgedeckten sicheren Punkt. Ein grosser Raum erzeugt dadurch automatisch mehr
Ziele als ein kleiner.

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
| Publish | `/explore/status_json` | `std_msgs/String`, 1-Hz-Heartbeat |

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
- `frontier_revisit_radius_m` – sperrt erfolgreich bediente Frontier-Umfelder
- `max_frontier_goals` – harte Obergrenze gegen Zielwiederholungen
- `coverage_target_ratio` – erforderlicher Anteil der sicher befahrbaren Flaeche
- `coverage_visit_radius_m` – Korridor um die gemessene Fahrspur
- `coverage_clearance_m` – Kartenabstand der Abdeckungsziele
- `coverage_max_goals` – harte Grenze der dritten Phase
- `return_to_start` – nach Fertigstellung zur Startpose zurück

## Abnahmestand und Grenzen

Der komplette Ablauf ist auf dem echten Roboter gefahren. Der beaufsichtigte
Akku-Lauf vom 17.08.2026 beendete Rundblick, adaptive Frontier-/Abdeckungswahl
und Mission nach 732 s mit 88,30 % Abdeckung, fuenf verschiedenen
Frontier-Zielen und `map_ready_to_save=true`. Beide VL53 und der
Kollisionsmonitor waren aktiv; danach standen Odometrie und Basis bei null.
Der Standardwert 85 % bezieht sich auf den erodierten, zusammenhaengenden
Freiraum innerhalb von 0,65 m zur Fahrspur und ersetzt keine visuelle
Kartenpruefung. Gedrehte Karten-Origin wird beruecksichtigt.
