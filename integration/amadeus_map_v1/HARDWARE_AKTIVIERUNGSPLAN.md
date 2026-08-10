# Hardware-Aktivierungsplan – Karten, SLAM und Navigation

> **Nicht mehr als Erstinstallation auf dem aktuellen Jetson ausführen.**
> Laut Hardwarebericht vom 27.07.2026 besitzt der Jetson bereits einen neueren,
> nur dort vorhandenen Stand auf Commit `390fcec`, reales RTAB-Map-Mapping und
> eine funktionierende Wiederlokalisierung. Vor jedem weiteren Apply zuerst
> `integration/amadeus_slam_localization_20260727/UEBERNAHMEPLAN.md` ausführen
> und den Jetson-Stand hashgesichert übernehmen. Abweichung bedeutet weiterhin
> Abbruch, niemals Überschreiben.

Dieser Plan ist für den Agenten bestimmt, der das vorbereitete Kartenpaket
später auf den echten Jetson überträgt. Alle Prüfungen in Abschnitt 1 sind
lesend und bewegen den Roboter nicht.

## 0. Archiv prüfen und Ziel-Drift ausschließen

Auf dem Mac beziehungsweise vom USB-Datenträger:

```bash
RELEASE_ID='amadeus-map-v1-20260726T194942Z'

python3 /Volumes/64GB/roboter_ws/tools/robot_transfer/pack_release.py verify \
  --archive /Volumes/64GB/robot_transfers/"$RELEASE_ID.tar.gz"
```

Archiv, `.sha256`, `pack_release.py` und `common.py` auf den Jetson
übertragen. Dort ausschließlich mit dem Prüfer entpacken:

```bash
mkdir -p ~/amadeus-transfer-tools ~/incoming ~/robot_transfers

python3 ~/amadeus-transfer-tools/pack_release.py verify \
  --archive ~/incoming/"$RELEASE_ID.tar.gz" \
  --extract-to ~/robot_transfers

python3 ~/robot_transfers/"$RELEASE_ID"/tools/apply.py \
  --release ~/robot_transfers/"$RELEASE_ID" \
  --target ~/roboter_ws
```

Der letzte Befehl ist nur ein Dry-run. Jede Hash-, Modus-, Marker- oder
Pfadabweichung bedeutet Abbruch und Analyse. In diesem Zustand nichts mit
`rsync`, `cp` oder `chmod` passend machen.

## 1. Zielsystem und ROS-Graph inventarisieren

```bash
uname -a
cat /etc/os-release
echo "$ROS_DISTRO"
ros2 doctor --report

ros2 pkg list | grep -E 'rtabmap|depthai|navigation2|nav2|robot_localization'
ros2 node list
ros2 topic list -t
ros2 action list -t

ros2 topic info /map --verbose
timeout 15 ros2 topic echo /map --once \
  --qos-durability transient_local --qos-reliability reliable

ros2 topic info /odom --verbose
ros2 topic info /cmd_vel --verbose
ros2 topic info /cmd_vel_smoothed --verbose
timeout 10 ros2 run tf2_ros tf2_echo map base_link
timeout 10 ros2 run tf2_ros tf2_echo odom base_footprint
ros2 run tf2_tools view_frames
```

Zusätzlich alle Kamera-, Tiefenbild-, Punktwolken-, IMU-, Scan- und
Radencoder-Topics samt Typ und QoS notieren. Topics dürfen erst nach diesem
Befund in eine RTAB-Map-Konfiguration eingetragen werden.

## 2. Eindeutige Besitzer festlegen

Vor jeder Fahrt muss die Kette genau so eindeutig sein:

```text
RTAB-Map Mapping oder Lokalisierung
  ├── /map
  └── TF map -> odom

reale Odometrie / EKF
  ├── /odom
  └── TF odom -> base_footprint

robot_state_publisher
  └── TF base_footprint -> base_link -> Sensorframes

Nav2 Controller
  -> /cmd_vel_nav
  -> collision_monitor
  -> /cmd_vel
  -> base_hardware
```

Unzulässig sind insbesondere:

- statisches `map -> odom` parallel zu SLAM oder Lokalisierung,
- zwei Publisher für denselben TF,
- Nav2 direkt auf dem finalen `/cmd_vel`,
- Sollgeschwindigkeitsintegration als ungeprüfte reale Odometrie,
- doppelte feste Sensor-TFs aus URDF und separaten
  `static_transform_publisher`-Nodes.

## 3. SLAM zuerst ohne Motorfreigabe

1. Erst nach grüner Inventur das Software-Release mit
   `--apply --confirm-safe-state` anwenden.
2. `colcon build`, Pakettests und den bewegungsfreien Smoke-Launch aus
   `TESTPLAN.md` ausführen.
3. Roboter standsicher abstellen; Hardwareantrieb deaktiviert lassen.
4. OAK-/Sensorsystem und kalibrierte feste TFs starten.
5. Ausgewählte reale Odometrie starten.
6. RTAB-Map im Mappingmodus starten.
7. `/map`, Zeitstempel und die vollständige TF-Kette prüfen.
8. Die iPhone-App verbinden und ausschließlich die Kartenanzeige testen.
9. Einen Snapshot über den Map-Manager speichern und Dateien/Hashes prüfen.
10. RTAB-Datenbank separat nach dem vorgesehenen RTAB-Verfahren sichern.

Ein PGM/YAML-Snapshot ersetzt nicht die RTAB-Datenbank und stellt allein
keine Wiederlokalisierung bereit.

## 4. Produktives Nav2 erst nach Sicherheitsabnahme

Vor Aktivierung:

- realen Footprint beziehungsweise Plattformradius eintragen,
- echte Hindernisquellen in lokale und globale Costmap integrieren,
- Collision Detection im Controller einschalten,
- Nav2-Ausgabe auf `/cmd_vel_nav` remappen,
- Collision Monitor als einzigen Publisher von `/cmd_vel` bestätigen,
- Watchdog-Stopp bei Ausfall jeder vorgeschalteten Komponente testen,
- Explore um endliche Preflight-Timeouts und unmittelbare
  Nav2-Goal-Cancellation ergänzen,
- alle Testwohnungskoordinaten im Missionskatalog sperren und danach mit der
  echten Karte neu einmessen.

Die erste Fahrprüfung erfolgt aufgebockt und mit harter
Hardware-NOT-AUS-Möglichkeit. Erst danach folgt eine langsame Bodenfahrt.

## 5. Abnahmekriterien der Kartenintegration

- Genau ein gültiger `/map`-Publisher ist sichtbar.
- Die App erhält auch bei später Verbindung eine Karte.
- Kartenbreite, -höhe, Auflösung und Frame-ID stimmen in App und ROS überein.
- Der Map-Manager meldet einen gültigen Snapshot.
- `map -> ... -> base_link` ist zusammenhängend und zeitlich aktuell.
- Eine gespeicherte Version enthält PGM, YAML und Metadaten mit gültigen
  Prüfsummen.
- Ein erneutes Speichern erzeugt eine neue Version und überschreibt keine
  ältere Karte.
- Software-Apply und Rollback verändern keine gespeicherten Wohnungskarten.
