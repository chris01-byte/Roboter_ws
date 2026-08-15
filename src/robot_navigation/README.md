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

Der `PoseProgressChecker` akzeptiert innerhalb von 20 s entweder 0,10 m
Translation oder 0,05 rad Encoder-Drehung. Das ist auf die gemessene
2000-ms-Hardware-Rampe abgestimmt: Der reine Positionspruefer brach eine real
laufende Drehung nach 20 s faelschlich als festgefahren ab. Die
Winkelbeschleunigung des Reglers liegt bewusst ueber der Komfortgrenze; der
nachgeschaltete `velocity_smoother` begrenzt weiterhin verbindlich auf
0,30 rad/s², danach folgt die Motor-Hardwarerampe. So wird die
Encoder-Rueckmeldung nicht durch eine zweite gleich niedrige Regler-Rampe
erneut ausgebremst. Ein echter Stillstand wird weiterhin zeitlich begrenzt
erkannt.

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

## Globale Lokalisierung auf einer gespeicherten LiDAR-Karte

`nav_localized.launch.py` verbindet die aktuelle gespeicherte OccupancyGrid-
Karte mit dem normalisierten STL-27L-Scan und AMCL. Es übernimmt absichtlich
weder die letzte Pose noch einen geratenen Ursprung. Nach identischer
Fingerprint-Bindung von metrischer und semantischer Karte ruft der
`localization_guard` den globalen AMCL-Reset auf.

Die Freigabe `/localization/ready` bleibt `false`, bis alle Bedingungen
gleichzeitig gelten:

- genau ein `/map`- und ein `/amcl_pose`-Publisher;
- metrische und semantische Karte haben denselben SHA-256-Fingerprint;
- frischer normalisierter LiDAR-Scan;
- AMCL-Standardabweichung zum erstmaligen Freigeben höchstens 0,20 m in x/y
  und 10 Grad in yaw;
- dynamisches `map -> odom` bleibt über mindestens rund 2,4 s innerhalb
  0,08 m und 5 Grad stabil.

Nach einer bestaetigten Freigabe verhindern zwei Hysteresen Flattern waehrend
normaler Bewegung: Die Kovarianz darf beim Halten der Freigabe bis 0,30 m oder
15 Grad steigen, und die Bewegung des dynamischen `map -> odom` im
Messfenster darf bis 0,20 m oder 12 Grad betragen. Die strengeren
Erstfreigabegrenzen bleiben unveraendert 0,20 m/10 Grad fuer die Kovarianz und
0,08 m/5 Grad fuer `map -> odom`. Die Haltegrenzen wurden aus 640 realen
TF-Proben einer langsamen Kurvenfahrt abgeleitet; dabei wurden im
Drei-Sekunden-Fenster maximal 0,1601 m und 8,32 Grad gemessen. Der Status nennt
unter `map_to_odom_window` die aktuelle Messung und unter
`transform_stability_limits` die gerade aktive Acquire- oder Maintain-Grenze.

Diese Hysteresen gelten nicht fuer andere Fehler. Falsche Kartenbindung,
fehlende oder veraltete Scans/TF/Pose oder eine falsche Publisherzahl sperren
weiterhin sofort; danach gelten zur erneuten Freigabe wieder die strengeren
Acquire-Grenzen. Die Kovarianz-Erstfreigabe von 10 Grad wird nicht gelockert:
Mehrdeutige globale Hypothesen in der realen, teilweise offenen Raumkarte
duerfen nicht durch eine groessere Schwelle als lokalisiert gelten.

Mission Manager und `cmd_vel_mission_gate` prüfen diese Freigabe unabhängig.
Ein fehlendes, falsches oder älter als eine Sekunde gewordenes Signal sperrt
den Geschwindigkeitsausgang sofort. Eine bereits aktive `go_to_room`-Mission
wird erst verworfen, wenn die Lokalisierung 0,8 s durchgehend fehlt; eine
kurze AMCL-Korrektur stoppt dadurch den Roboter, zerstoert aber nicht sofort
den Action-Zustand. Die erste Zielannahme verlangt weiterhin ohne Nachfrist
eine gueltige Freigabe. `loss_age_seconds` und
`mission_cancel_grace_seconds` machen diesen Zustand im Missionsstatus
sichtbar.

Der Kartenpfad ist Pflicht und bleibt lokal; eine Test-/Leerkarte wird nie als
Default angenommen. Der Starthelfer sourct auch den getrennten gepinnten
STL-27L-Treiber:

```bash
bash tools/kartierung/start_lidar_lokalisierung.sh /absolut/map.yaml \
  oak:=false

ros2 topic echo --once --full-length --qos-durability transient_local \
  /localization/status_json --field data
```

Der erste Befehl ist motorlos (`active_drive:=false`). Eine scharfe
Lokalisierungsdrehung ist ein eigener beaufsichtigter Hardwaretest; der Helfer
verlangt dafür zusätzlich `AMADEUS_FAHRFREIGABE=JA` und einen expliziten
Launch-Wert `active_drive:=true`.
