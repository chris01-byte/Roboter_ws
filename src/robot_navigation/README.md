# robot_navigation — Nav2 real, zuerst ohne Hardware

Echter Nav2-Stack (Planer, Regler, Recovery, BT-Navigator) für den Roboter.
Der Clou: **läuft komplett ohne Hardware** — die Dry-Run-Basis (`base_hardware`)
integriert `cmd_vel` zu `/odom` + TF, dazu eine statische Testkarte. Nav2 plant
wirklich, die virtuelle Basis „fährt", das Ziel wird erreicht.

```
Nav2 (planner/controller/behaviors/bt_navigator)
   -> /cmd_vel -> base_hardware (dry_run, publish_tf) -> /odom + TF -> Nav2
Karte: maps/testwohnung (12x10 m) | map->odom: statische Identitaet
```

## Testwohnung (map-Frame)

| Bereich | Koordinaten | Ablageorte (Pose-Katalog) |
|---|---|---|
| Wohnzimmer | x < 3 | Tisch (1.5, 2.0) · Regal (0, 6.5) · Start (0,0) |
| Flur (rechts unten) | x 3..10, y < 4 | Benutzer (4.5, 0.5) |
| Küche (rechts oben) | x 3..10, y > 4 | Arbeitsplatte (5.0, 6.0) |

Türen: Wohnzimmer→Flur bei y≈2, Flur→Küche bei x≈7. Karte neu erzeugen/ändern:
Generator-Aufruf steht in der Git-/Chat-Historie; einfacher: PGM direkt malen.

## Nutzung

```bash
sudo apt install ros-humble-navigation2        # einmalig

# Nav2 allein (Prüfstufe N1):
ros2 launch robot_navigation nav_test.launch.py
ros2 action send_goal /navigate_to_pose nav2_msgs/action/NavigateToPose \
  "{pose: {header: {frame_id: map}, pose: {position: {x: 1.5}, orientation: {w: 1.0}}}}"

# Komplette Mission mit echtem Nav2 (Prüfstufe N2):
ros2 launch mock_servers dry_run_nav_mission.launch.py
```

## Weg zur echten Navigation (wenn Hardware da ist)

1. **SLAM** (RTAB-Map mit OAK bzw. Lidar): liefert `/map` + `map->odom` —
   ersetzt `map_server` + statische TF in `nav_test.launch.py`. Die
   Nav2-Parameter hier bleiben gültig.
2. **Sensor-Layer**: VL53-Wolken in die Costmaps (Vorlage liegt in
   `vl53_near_field/config/costmap_vl53_obstacle_layer.snippet.yaml`),
   `use_collision_detection` im Regler aktivieren.
3. **cmd_vel-Kette scharf**: Nav2 -> collision_monitor -> base_hardware
   (Prüfplan C4), `dry_run: false` erst nach aufgebocktem Test.
4. Pose-Katalog (`mission_manager`) mit der echten SLAM-Karte neu einmessen.
