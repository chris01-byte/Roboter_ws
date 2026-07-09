# base_hardware

Erster echter Unterbau fuer den Hauptantrieb der mobilen Plattform.

## Warum zuerst trocken?
Der Node startet im **Dry-run**. Er sendet keine RS485-Kommandos. Das ist Absicht: Wir pruefen erst Mathematik, Vorzeichen, Watchdog, `/cmd_vel`-Kette und Odometrie, ohne echte NEMA23-Motoren zu bewegen.

## Funktionen v1
- Subscribed `/cmd_vel` (`geometry_msgs/Twist`)
- Berechnet linke/rechte Radgeschwindigkeit und RPM
- Publiziert simulierte `/odom`
- Publiziert `/base_hardware/state_json`
- Watchdog: stoppt nach `cmd_timeout_s`, wenn keine neuen Kommandos kommen
- Optional: schreibt Velocity-/Stop-Kommandos per RS485/Modbus (nur wenn bewusst freigeschaltet)

## Start
```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch base_hardware base_hardware.launch.py
```

## Testkommando
```bash
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.10}, angular: {z: 0.0}}" -r 2
```

Status ansehen:
```bash
ros2 topic echo /base_hardware/state_json
ros2 topic echo /odom
```

## RS485-Test auf Staendern
Vorher `config/base_hardware_params.yaml` pruefen:
- `rs485_port`
- `left_motor_id`, `right_motor_id`
- `invert_left`, `invert_right`
- Register: `rpm_register`, `direction_register`, `command_register`, `velocity_start_value`, `stop_value`

Abhaengigkeit auf dem Jetson:
```bash
python3 -m pip install pymodbus
```

Dann nur bei frei drehenden Raedern und bereitliegendem Not-Aus:
```yaml
dry_run: false
allow_rs485: true
```

Starten und mit sehr kleinem Kommando testen:
```bash
ros2 launch base_hardware base_hardware.launch.py
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.03}, angular: {z: 0.0}}" -r 2
```

Wenn die Raeder falsch herum laufen, zuerst `invert_left`/`invert_right` korrigieren, nicht die Verkabelung hektisch tauschen.

## Standalone-RViz-Test
Normalerweise publiziert spaeter `ekf_node` den TF `odom -> base_link`. Fuer einen isolierten Test kannst du voruebergehend TF aktivieren:
```bash
ros2 launch base_hardware base_hardware.launch.py publish_tf:=true
```

## Naechster Ausbau
Wenn der aufgebockte Radtest plausibel ist:
1. Status-/Alarmregister der Motoren lesen.
2. RS485-Port stabil per udev-Regel benennen.
3. Odometrie aus echten Motor-Istwerten statt Sollgeschwindigkeit berechnen.
4. Not-Aus-/Enable-Kette mit `safety_monitor` koppeln.
