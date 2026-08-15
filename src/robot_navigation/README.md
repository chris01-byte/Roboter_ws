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

## Reale Nav2-Fahrt

Die reale Startdatei verwendet eine bewusst gestufte Befehlskette:

```text
Nav2 -> /cmd_vel_nav_raw -> mission_cmd_vel_gate -> /cmd_vel_nav
     -> velocity_smoother -> /cmd_vel_smoothed -> collision_monitor
     -> /cmd_vel -> base_hardware
```

Der Geschwindigkeitsglätter begrenzt die Regleränderungen passend zur real
gemessenen 2000-ms-Anfahrtsrampe. Er liegt vor dem `collision_monitor`, damit
ein VL53-Sicherheitsstopp nicht weichgezeichnet oder verzögert wird. Encoder-
Odometrie, Motorvorzeichen und Motorregister bleiben dabei unverändert.
Der Glätter arbeitet bewusst `OPEN_LOOP`: Im Realtest koppelte `CLOSED_LOOP`
die Encoder-Rückmeldung mit der bereits vorhandenen Motorrampe doppelt und
reduzierte den Sollwert nach drei Sekunden noch auf etwa 0,007 m/s. Die
Encoder-Odometrie bleibt davon unberührt und wird weiterhin von Nav2 genutzt.

Der Fortschrittspruefer akzeptiert 0,10 m innerhalb von 20 s. Das ist auf die
gemessene 2000-ms-Hardware-Rampe abgestimmt: Mit der frueheren Schwelle von
0,30 m in 15 s wurde eine freie, gerade Fahrt nach rund 0,19 m faelschlich als
festgefahren abgebrochen. Ein echter Stillstand wird weiterhin zeitlich
begrenzt erkannt.

Das `mission_cmd_vel_gate` arbeitet fail-closed. Es gibt Nav2-Befehle nur bei
einem frischen Missionsstatus `running` für `go_to_room` frei. Ein fehlender,
veralteter oder terminaler Status erzwingt null. Damit kann auch ein von Nav2
verspätet angenommenes Unterziel nach einem Missionsfehler nicht weiterfahren.

Ohne Motorstrom prüfen:

```bash
ros2 launch robot_navigation nav_real.launch.py oak:=false \
  static_map_odom_x:=0.045 static_map_odom_y:=0.005
```

`active_drive:=true` aktiviert RS485 und darf nur nach der Hardware-
Startprüfung, mit freier Fahrfläche und erreichbarem Not-Aus verwendet werden.
Die drei `static_map_odom_*`-Werte sind ausschließlich eine vermessene
Startpose für kurze Tests ohne Lokalisierung. Sobald RTAB-Map oder AMCL läuft,
muss `static_map_odom:=false` gesetzt werden.
