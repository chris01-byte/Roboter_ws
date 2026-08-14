# robot_bringup — Onboard/Offboard-Deployment (WP-5, Baustein D)

Organisiert, **was auf dem Roboter** und **was auf dem KI-Server** läuft, und wie beide
über **ROS 2 DDS im WLAN** zusammenfinden. Enthält den `link_monitor`, der die
Server-Erreichbarkeit überwacht (WLAN-Ausfall-Fallback).

## Aufteilung

| Läuft auf | Nodes | Start |
|---|---|---|
| **Roboter (onboard)** | base_hardware, robot_map_manager, semantic_map_manager, vl53_near_field, explore, mission_manager, bt_orchestrator (Missions-Server), safety_monitor, robot_face, link_monitor — (SLAM/OAK/MoveIt folgen) | `robot.launch.py` |
| **Server (offboard)** | llm_planner (qwen2.5/Ollama), semantic_perception (YOLO-World + Objektgedächtnis) | `server.launch.py` |

**Grundregel:** Sicherheit, Navigation und Exploration laufen **immer onboard**. Fällt der
Server/das WLAN aus, entfallen nur die KI-Funktionen — der Roboter bleibt sicher
(der BT erkundet dann auch nicht ungewollt: `IsOffboardAvailable`-Guard).

## Server einmalig einrichten (Ersteinrichtung)

Zielsystem: Ubuntu 22.04 x86 (GPU empfohlen für YOLO-World, z. B. RTX 3090).

```bash
# 1) ROS 2 Humble (Desktop) + Build-Werkzeuge — Installation nach docs.ros.org, dann:
sudo apt install ros-humble-desktop python3-colcon-common-extensions \
                 ros-humble-behaviortree-cpp
echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc && source ~/.bashrc
# Hinweis: behaviortree_ros2 liegt als SOURCE in src/ — nichts extra klonen.

# 2) Workspace vom Stick kopieren und bauen (ext4 -> Symlinks ok):
cp -r /media/$USER/64GB/roboter_ws ~/roboter_ws
cd ~/roboter_ws && ./pruefplan_jetson.sh --stage B0     # baut + prüft
source install/setup.bash

# 3) KI-Modelle:
curl -fsSL https://ollama.com/install.sh | sh           # Ollama
ollama pull qwen2.5                                      # LLM des Planers
pip install ultralytics                                  # YOLO-World
# dann in src/semantic_perception/config/semantic_perception_params.yaml:
#   model_backend: "yoloworld"   (ohne Kamerabild: automatischer Stub-Rückfall)

# 4) Netzwerk einrichten (Abschnitt unten), Server starten:
ros2 launch robot_bringup server.launch.py

# 5) Funktionsprobe ohne Roboter (zweites Terminal):
ros2 topic pub --once /llm_planner/instruction std_msgs/msg/String "{data: 'Erkunde die Wohnung'}"
ros2 topic echo /mission_manager/command_json            # -> {"type": "explore"}
ros2 service call /world_model/get_object_pose robot_interfaces/srv/GetObjectPose "{class_name: 'Tasse'}"
```

Nicht nötig auf dem Server: `navigation2`, `rosbridge` (laufen auf dem Jetson).

## Netzwerk-Setup (einmalig)

1. **Roboter und Server im selben WLAN.**
2. **Gleiche `ROS_DOMAIN_ID`** auf beiden Rechnern (Beispiel 42):
   ```bash
   export ROS_DOMAIN_ID=42
   ```
3. **Empfohlen (WLAN):** CycloneDDS mit dem mitgelieferten Profil verwenden, damit die
   Kommunikation auch ohne Multicast funktioniert:
   ```bash
   export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
   export CYCLONEDDS_URI=file://$(ros2 pkg prefix robot_bringup)/share/robot_bringup/config/cyclonedds_profile.xml
   ```
   In der Profildatei die **echten IPs** von Roboter und Server als `<Peer .../>` eintragen.

> Tipp: Diese `export`-Zeilen in die `~/.bashrc` beider Rechner schreiben, dann gelten sie
> in jedem Terminal.

## Starten

**Auf dem Roboter:**
```bash
ros2 launch robot_bringup robot.launch.py
# optional den Behavior-Tree gleich mitstarten:
ros2 launch robot_bringup robot.launch.py start_bt:=true
# Kartenmanager nur zur Fehlersuche auslassen:
ros2 launch robot_bringup robot.launch.py start_map_manager:=false
# Semantische Raumverwaltung nur zur Fehlersuche auslassen:
ros2 launch robot_bringup robot.launch.py start_semantic_map_manager:=false
```

## Kartenintegration für die Amadeus-App

`robot.launch.py` startet standardmäßig den fahrbewegungsfreien
`robot_map_manager`. Der Node beobachtet `/map`, veröffentlicht den aus TF
ermittelten Stand von `base_link` im Kartenframe und speichert die letzte
gültige Karte ausschließlich auf expliziten Befehl. Er publiziert selbst
keine Karte und startet weder SLAM noch Nav2.

```text
/map                                  nav_msgs/OccupancyGrid (Eingang)
/robot_map_manager/robot_pose         geometry_msgs/PoseStamped
/robot_map_manager/status_json        std_msgs/String, transient-local
/robot_map_manager/command_json       std_msgs/String
/robot_map_manager/save_map           std_srvs/Trigger
```

Die native iPhone-App liest weiterhin das Standardtopic `/map` direkt über
rosbridge. Gespeicherte Karten liegen versioniert außerhalb des Workspace
unter `~/.local/share/amadeus/maps`; ein Software-Update darf diesen
Laufzeitdatenpfad niemals überschreiben oder löschen. Bedienung, Dateiformat
und Prüfkommandos stehen im README des Pakets `robot_map_manager`.

Wichtig: Der Kartenmanager ersetzt keinen SLAM-Publisher und keine
Lokalisierung. Solange RTAB-Map beziehungsweise ein `map_server` nicht läuft,
wartet die App korrekt auf `/map`.

## Semantische Raumverwaltung

`robot.launch.py` startet standardmaessig auch den
`semantic_map_manager`. Er ist eine persistente Beschriftungsschicht ueber der
metrischen Karte und in diesem Integrationsstand vollstaendig passiv:

- keine Action-Clients oder Nav2-Ziele;
- kein Publisher auf `cmd_vel`/`cmd_vel_smoothed`;
- keine Motor- oder Sensorparameteraenderung;
- Schreibzugriffe nur nach explizitem App-Kommando mit Kartenfingerprint und
  Basisrevision.

Der `mission_manager` liest dessen transient-local Status und Katalog. Er kann
ein manuell deklariertes Raumziel validieren und im eigenen Status anzeigen;
`go_to_room` bleibt jedoch `simulation_only_no_navigation`. Das Launch-Argument
`start_semantic_map_manager` ist standardmaessig `true`, weil dieser Node keine
Bewegungswirkung besitzt.

**Auf dem Server:**
```bash
ros2 launch robot_bringup server.launch.py
```

## Erreichbarkeit prüfen (`link_monitor`)

Der `link_monitor` läuft auf dem Roboter und meldet laufend, ob der Server da ist:

```bash
ros2 topic echo /offboard/available       # true/false
ros2 topic echo /offboard/status_json     # Details: welche Nodes fehlen
```

Parameter in [config/link_monitor_params.yaml](config/link_monitor_params.yaml)
(`watched_nodes`, `check_period_s`).

## Verbindung testen

Auf **beiden** Rechnern (gleiche Domain/Netz vorausgesetzt):
```bash
ros2 node list      # sollte Nodes vom jeweils anderen Rechner mit anzeigen
ros2 topic list     # Topics beider Seiten sichtbar
```
Sehen sich die Rechner nicht: Firewall prüfen, gleiche `ROS_DOMAIN_ID`, feste `<Peer>`-IPs
im DDS-Profil eintragen.

## Offen / später

- Platzhalter in `robot.launch.py` für SLAM (RTAB-Map), OAK-Kamera und MoveIt2 erst
  nach Prüfung der echten Sensor-, Odometrie-, TF- und Sicherheitsschnittstellen
  aktivieren (bis dahin via `mock_servers`). Nav2 ist bereits ohne Hardware nutzbar:
  `robot_navigation/nav_test.launch.py` (Testkarte + virtuelle Basis).
- Optional: `ros2 launch`-Argument, um einzelne Onboard-Gruppen selektiv zu starten.
