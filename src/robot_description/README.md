# robot_description (WP-0 Dummy)

Dieses Paket enthaelt ein erstes Dummy-Robotermodell fuer den mobilen Pick-and-Place-Roboter.

## Zweck
- TF-Baum sichtbar machen, bevor echte Hardware eingebunden wird.
- VL53-, OAK-, Basis- und Arm-Frames frueh pruefen.
- Grundlage fuer spaetere MoveIt-/Nav2-Konfiguration.

## Start
```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch robot_description display_dummy.launch.py use_rviz:=true
```

## Wichtig
Alle Masse im Xacro sind Platzhalter und mit `[ANPASSEN]` markiert. Bitte spaeter durch echte Messwerte ersetzen.

Die Dummy-URDF ist nicht als fertige mechanische Konstruktion gedacht. Sie ist ein technischer TF-/RViz-Prototyp.
