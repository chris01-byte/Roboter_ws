# base_hardware

Erster echter Unterbau fuer den Hauptantrieb der mobilen Plattform.

## Warum zuerst trocken?
Der Node startet im **Dry-run**. Er sendet keine RS485-Kommandos. Das ist Absicht: Wir pruefen erst Mathematik, Vorzeichen, Watchdog, `/cmd_vel`-Kette und Odometrie, ohne echte NEMA23-Motoren zu bewegen.

## Geometrie & Getriebe (Odometrie kalibriert 12.08.2026)
| Wert | Größe | Wirkung |
|---|---|---|
| wirksamer Rollradius | 0,0624 m | Umfang 0,3921 m — skaliert Tempo **und** Odometrie |
| wirksame Spurweite | 0,3845 m | kalibrierter Odometriewert für Drehung/Kursstabilität |
| `gear_ratio` | **10:1** | Rad-rpm × 10 = Motor-rpm (sonst 10× zu langsam!) |

Richtwerte: 0,03 m/s ≈ 46 rpm Motor · 0,05 m/s ≈ 76 rpm · 0,30 m/s ≈ 458 rpm ·
Vollgas + Drehung ≈ 689 rpm (Grenze `max_motor_rpm: 700`, **gegen Motor-Datenblatt prüfen**).

Odometrie und URDF verwenden absichtlich unterschiedliche Arten von Geometrie:

- `config/base_hardware_params.yaml` enthält die **wirksamen, unter Last
  kalibrierten** Werte 0,0624 m und 0,3845 m;
- die URDF enthält die **physisch gemessenen** Werte 0,0625 m und 0,378 m für
  Form und Gelenkpositionen.

Diese Werte nicht blind angleichen. Eine erneute Kalibrierung braucht getrennte
Strecken- und Winkelmessungen gemäß `docs/PROJECT_MEMORY.md`.

## Encoderpositions-Odometrie

Im realen Zielmodus nutzt der Node absolute Positionszähler
(`0x000A/0x000B`). Die Software kann jede dort tatsächlich registrierte
Positionsänderung einschließlich Bremsweg und einer kurzen Buslücke erhalten.
Ob die Register auch Handschieben im vorgesehenen elektrischen Zustand erfassen,
muss H2 am realen Motor erst bestätigen. Der Standardwert
`encoder_counts_per_motor_revolution: 0.0` blockiert den echten Positionsmodus
absichtlich, bis `tools/kartierung/encoder_position_pruefen.py` die Einheit
bestimmt hat. Details: `docs/ENCODER_ODOMETRIE_FIX.md`.

Nach H2 müssen außerdem die auf beiden Motoren identisch gelesenen Werte aus
`0x0011` und `0x0101` als `encoder_expected_segment` und
`encoder_expected_resolution` größer null eingetragen werden. `0` ist bei den
drei Schutzparametern nur für die read-only Inbetriebnahme vorgesehen und
verriegelt den realen `encoder_position`-Modus.

Ein einzelner normaler FC03-Fehler behält Client und Baseline, sodass das
nächste gültige Paar die kumulierten Counts noch übernehmen kann. Sobald
`encoder_failure_stop_count` normale FC03-Transportfehler in Folge auftreten,
erfolgen Stopp, Busfehlerstatus und Reconnect. Eine stale Rückmeldung
sperrt und stoppt immer; nur ein zugrunde liegender Transportfehler löst den
Reconnect aus. Ausnahmen/API-Fehler gehen sofort in diesen Pfad. Jeder neue Modbus-Client
verwirft die alte
Baseline bewusst, damit ein Controllerreset keinen Posesprung erzeugt.

Ein semantisch ungültiges, etwa unplausibles Delta wird dagegen sofort
verworfen und kontrolliert rebased; Fahrt und Motor werden gesperrt/gestoppt,
der bestehende Client bleibt erhalten. Eine Abweichung der in H2 verriegelten
Treiberwerte sperrt ebenfalls sofort und wird nicht durch Reconnects kaschiert.

Encoder-`/odom` wird nur zu einem neuen gültigen Positionspaar publiziert
(Ziel etwa 20 Hz); `/base_hardware/state_json` bleibt beim 50-Hz-Node-Takt.

`/cmd_vel` verwendet Queue-Tiefe 1. NaN/Inf werden verworfen und fordern Stopp
an; der Watchdog misst mit monotoner Echtzeit. Deshalb ist
`use_sim_time: true` bei `dry_run: false` plus `allow_rs485: true` verboten.
Eine Bewegung gilt erst dann als angefordert, wenn mindestens ein auf den
signed-RPM-Registerwert quantisierter Motorsollwert ungleich null ist. Kleinere
nicht darstellbare Befehle halten den Antrieb gestoppt.

Die vier Parameter `odom_pose_xy_variance`, `odom_yaw_variance`,
`odom_twist_linear_variance` und `odom_twist_angular_variance` sind
konservative Startwerte. Sie stehen nicht für bereits gemessene Genauigkeit
und werden erst in H4 aus wiederholten Fahrten gegen eine externe Referenz
kalibriert.

## Funktionen v1
- Subscribed `/cmd_vel` (`geometry_msgs/Twist`)
- Berechnet linke/rechte Radgeschwindigkeit und RPM
- Publiziert simulierte `/odom` im Dry-run und messsynchronisierte Encoder-`/odom` im realen Modus
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
Vorher H0 bis H2 aus `docs/ENCODER_ODOMETRIE_FIX.md` abarbeiten und prüfen:
- `rs485_port`
- `left_motor_id`, `right_motor_id`
- `invert_left`, `invert_right`
- `odometry_source: encoder_position`
- bestätigte `encoder_counts_per_motor_revolution` größer als null
- bestätigte `encoder_expected_segment` und `encoder_expected_resolution`
  aus `0x0011`/`0x0101`, beide größer als null
- verwendete Register: `rpm_register`, `command_register`, `velocity_start_value`, `stop_value`

Abhaengigkeit auf dem Jetson:
```bash
python3 -m pip install -r src/base_hardware/requirements-modbus.txt
```

Die Runtime ist damit auf Pymodbus 3.14.0 und Pyserial 3.5 festgelegt. `modbus_retries: 0`
verhindert versteckte Wiederholungen im zeitkritischen Fehlerpfad; kontrollierte
Wiederanläufe führt der Node selbst aus.

Ein echter Motorlauf ist mit `counts=0` oder einem der beiden erwarteten
Treiberwerte auf `0` nicht startfähig. H3 beginnt erst nach bestätigten Counts
und Treiberwerten, frei drehenden Rädern,
geprüftem und erreichbarem Not-Aus sowie einer neuen ausdrücklichen
Fahrfreigabe. Erst dann dürfen für genau diesen aufgebockten Test gesetzt
werden:
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

## Nächste Schritte
Nach bestandenem aufgebocktem H3-Test:
1. H4-A/B-Streckenmessung mit externer Referenz durchführen.
2. H5-Fehler- und Wiederanlauftests kontrolliert abnehmen.
3. Status-/Alarmregister der Motoren ergänzen.
4. Not-Aus-/Enable-Kette mit `safety_monitor` koppeln.
