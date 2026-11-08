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
Basis, OAK und VL53 tragen inzwischen gemessene Werte (`[GEMESSEN ...]`). Alle mit `[ANPASSEN]` markierten Werte sind weiterhin Platzhalter.

Der Arm-Teil ist seit dem 08.11.2026 als `[UEBERHOLT]` markiert: Der reale Arm sitzt vorn am Kameramast auf einer Hubachse und hat eine andere Gelenkfolge als dieses Dummy. Fuer Planung, Kollision, Kalibrierung und Fahrpose nicht verwenden; Stand siehe [`docs/ARM_KONTEXT.md`](../../docs/ARM_KONTEXT.md).

Die Dummy-URDF ist nicht als fertige mechanische Konstruktion gedacht. Sie ist ein technischer TF-/RViz-Prototyp.
