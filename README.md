# roboter_ws — ROS 2 Workspace (Ubuntu 22.04 / ROS 2 Humble)

Code zum Projekt **Mobiler Pick-and-Place-Roboter** (Jetson onboard + KI-Server offboard).
Software-Stand am 08.07.2026 auf dem Jetson **komplett abgenommen** (alle Prüfstufen grün,
inkl. echter Missionskette und echtem Nav2 ohne Hardware).

## Zentrale Einstiegsdokumente
| Datei | Zweck |
|---|---|
| `README.md` | Überblick + Schnellstart (diese Datei) |
| `PROJEKT_STATUS.md` | **Aktueller Stand** — zuerst hier lesen |
| `Roboter_Pruefplan.md` | Der EINE finale Prüfplan (+ `pruefplan_jetson.sh`) |
| `KONZEPT_KALIBRIERUNG_OAK_ARM.md` | Hand-Auge-Kalibrierung (nächste Hardware-Phase) |
| `docs/SEMANTIC_MAP_INTEGRATION.md` | Manuelle Räume, Kartenbindung, App-Vertrag und sichere Ausbaufolge |
| `docs/PROJECT_MEMORY.md` | Fortlaufende, evidenzbasierte Entscheidungen und reale Abnahmen |

## Pakete
| Paket | Inhalt |
|---|---|
| `robot_interfaces` | Eigene `msg`/`srv`/`action` (GetObjectPose, RunMission, ExploreArea, …) |
| `bt_orchestrator` | Behavior-Tree als **Missions-Action-Server** (`run_mission`) |
| `mission_manager` | Bedien-Layer; löst manuelle Raumziele read-only auf, fährt sie aber noch nicht an |
| `mock_servers` | Gegenstellen für Trockentests (Arm/Greifer/Wahrnehmung; Nav/Not-Aus abschaltbar) |
| `robot_navigation` | Echter Nav2-Stack + Testkarte: Navigation ohne Hardware (virtuelle Basis) |
| `safety_monitor` | Onboard-Not-Aus-Wächter: publiziert `/safety/estop` (latched) |
| `smartphone_gui` | iPhone-Web-App/PWA: Aufträge, Erkunden, NOT-AUS, KI-Status (Port 8080) |
| `robot_face` | Cartoon-Gesicht fürs 7-Zoll-Display (Port 8081) |
| `base_hardware` | Basisantrieb: Dry-Run (`/cmd_vel` -> RPM + `/odom`) / später RS485 |
| `explore` | Autonome Frontier-Erkundung: `/explore_area` -> Nav2 |
| `vl53_near_field` | 2x VL53L7CX Nahbereich + collision_monitor-Konfiguration |
| `semantic_perception` | Open-Vocabulary-Erkennung (YOLO-World) **mit Objektgedächtnis** (offboard) |
| `semantic_map_manager` | Fingerprint-gebundene, revisionssichere manuelle Räume für App und Missionen |
| `llm_planner` | Sprache (qwen2.5/Ollama) -> mission_manager command_json (offboard) |
| `robot_bringup` | Onboard-/Offboard-Start, Netzwerk/DDS, link_monitor |
| `robot_description` | Dummy-URDF/TF-Baum für RViz (Arm-Maße folgen mit echtem Arm) |
| `handeye_calibration` | Messpaar-Recorder + Löser für die Hand-Auge-Kalibrierung |
| `behaviortree_ros2`* | Source-Abhängigkeit (BT.CPP-ROS2-Anbindung; nicht per apt verfügbar) |

## Bauen & Prüfen
```bash
cd ~/roboter_ws            # bzw. Stick-Pfad; exFAT: ohne --symlink-install (macht B0 automatisch)
./pruefplan_jetson.sh --software    # baut UND prüft alles (finaler Abnahmelauf, ~10 min)
```
Einmalige Voraussetzungen: `sudo apt install ros-humble-behaviortree-cpp ros-humble-navigation2 ros-humble-rosbridge-server`

## Schnellstart (nach dem Build)
```bash
# Roboter (onboard): Basis, Sicherheit, Gesicht, mission_manager, BT-Server
ros2 launch robot_bringup robot.launch.py
# KI-Server (offboard): LLM-Planer + Semantik   (beide: gleiche ROS_DOMAIN_ID!)
# Ersteinrichtung des Servers: src/robot_bringup/README.md
ros2 launch robot_bringup server.launch.py
# Bedienung: GUI + rosbridge
ros2 launch smartphone_gui smartphone_gui.launch.py    # iPhone: http://JETSON-IP:8080

# Trockentests einzeln (Details: Roboter_Pruefplan.md):
ros2 launch mock_servers dry_run.launch.py             # BT allein
ros2 launch mock_servers dry_run_mission.launch.py     # echte Auftragskette
ros2 launch mock_servers dry_run_safety.launch.py      # + echter Not-Aus-Wächter
ros2 launch mock_servers dry_run_nav_mission.launch.py # + echtes Nav2 (Testwohnung)
```

## Wo ändere ich was?
- **ROS-Namen/Timeouts/Testobjekt** -> `src/bt_orchestrator/config/bt_params.yaml` (Suchanker im Kopf)
- **Missionsablauf** -> `src/bt_orchestrator/bt_xml/pick_and_place.xml` (nach `[TUNE:...]` suchen)
- **Ablageorte/Katalog** -> `src/mission_manager/config/mission_catalog.yaml` (Pose-Katalog)
- **Gesichtsausdrücke** -> `src/robot_face/config/event_expression_map.yaml` (nur Daten, kein Code)
- **Neue BT-Aktion** -> Header unter `src/bt_orchestrator/include/.../nodes/` + in `bt_orchestrator_main.cpp` registrieren

**Konventionen:** XML-Kommentare mit `====` trennen (niemals `--`, bricht XML) · keine
Zeilennummern in Doku-Köpfen (Suchanker verwenden) · nach Änderungen an `smartphone_gui/web/`
den `CACHE_NAME` in `sw.js` hochzählen.

## Was noch Hardware braucht
Arm-Action-Server (MoveIt 2) und Greifer sind noch Mocks; SLAM (RTAB-Map) ersetzt die Testkarte,
sobald die OAK montiert ist; RS485-Antrieb erst nach aufgebocktem Test (`Roboter_Pruefplan.md`,
Teil 3). Erste Arm-Schritte: `KONZEPT_KALIBRIERUNG_OAK_ARM.md` (Stufe A).
