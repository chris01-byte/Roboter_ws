# robot_bringup — Onboard/Offboard-Deployment (WP-5, Baustein D)

Organisiert, **was auf dem Roboter** und **was auf dem KI-Server** läuft, und wie beide
über **ROS 2 DDS im WLAN** zusammenfinden. Enthält den `link_monitor`, der die
Server-Erreichbarkeit überwacht (WLAN-Ausfall-Fallback).

## Aufteilung

| Läuft auf | Nodes | Start |
|---|---|---|
| **Roboter (onboard)** | base_hardware, vl53_near_field, explore, mission_manager, link_monitor, (Nav2/SLAM/OAK/MoveIt folgen) | `robot.launch.py` |
| **Server (offboard)** | llm_planner, semantic_perception | `server.launch.py` |

**Grundregel:** Sicherheit, Navigation und Exploration laufen **immer onboard**. Fällt der
Server/das WLAN aus, entfallen nur die KI-Funktionen — der Roboter bleibt sicher.

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
```

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

- Platzhalter in `robot.launch.py` für SLAM (RTAB-Map), Nav2, OAK-Kamera und MoveIt2
  aktivieren, sobald diese Stacks integriert sind (bis dahin via `mock_servers`).
- Optional: `ros2 launch`-Argument, um einzelne Onboard-Gruppen selektiv zu starten.
