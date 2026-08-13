# Inventar

**Hardwarestand:** 10.08.2026 · Erfasst auf dem Jetson (`~/roboter_ws`, Commit `f1b2f23`)
**Softwaredelta:** 13.08.2026 · Branch `fix/encoder-position-odometry`, reale
Encoder-Abnahme noch offen

Reifegrade: **produktiv** = am echten Roboter getestet · **erprobt** = läuft,
aber nicht abschließend abgenommen · **Entwurf** = vorhanden, ungetestet

---

## 1. Umgebung

| | |
|---|---|
| Rechner | Jetson (`p-desktop`), Kernel 5.15.185-tegra |
| Betriebssystem | Ubuntu 22.04.5 LTS |
| ROS | 2 Humble |
| Arbeitskopie | `~/roboter_ws` — **maßgeblich** |
| Zweitkopie | `/media/p/64GB/roboter_ws` (USB-Stick, älterer Stand) |
| Freier Speicher | ~91 GB |

---

## 2. ROS-2-Pakete

| Paket | Zweck | Reifegrad |
|---|---|---|
| `base_hardware` | Antrieb über RS485/Modbus; Speed-Odometrie produktiv, Encoderposition softwareseitig umgesetzt und fail-closed bis H2/H3 | **produktiv (Speed)** / **Entwurf (Encoder)** |
| `vl53_near_field` | 2× VL53L7CX über CH341A, Nahbereichsschutz, `collision_monitor` | **produktiv** |
| `robot_bringup` | Startdateien für Roboter, SLAM, Kamera, Handsteuerung | **produktiv** |
| `robot_map_manager` | versionierte Kartenablage, Schnittstelle zur App | **produktiv** |
| `robot_description` | URDF/Xacro, Sensor-Frames | erprobt |
| `robot_navigation` | Nav2-Konfiguration, synthetische Testkarten | erprobt |
| `robot_interfaces` | eigene Nachrichten (u. a. `NearFieldStatus`) | **produktiv** |
| `safety_monitor` | Sicherheitsüberwachung | erprobt |
| `semantic_perception` | Objekterkennung auf OAK-Bildern | Entwurf |
| `mission_manager` | Auftragsverwaltung, Action-Lebenszyklus | erprobt |
| `bt_orchestrator` | Behavior-Tree-Ablaufsteuerung | Entwurf |
| `llm_planner` | Sprachgestützte Auftragsplanung | Entwurf |
| `smartphone_gui` | Weboberfläche | erprobt |
| `robot_face` | Gesichtsanzeige | erprobt |
| `explore` | Erkundungslogik | Entwurf |
| `handeye_calibration` | Kamera-Arm-Kalibrierung | Entwurf |
| `mock_servers` | Testgegenstellen ohne Hardware | erprobt |
| `behaviortree_ros2` | **Submodul** → github.com/BehaviorTree/BehaviorTree.ROS2 (humble) | extern |

---

## 3. Startbefehle

| Zweck | Befehl | Hardware aktiv? |
|---|---|---|
| Kamera allein | `ros2 launch robot_bringup oak.launch.py` | nein |
| SLAM/Kartierung | `ros2 launch robot_bringup slam.launch.py active_drive:=true` | **ja, Motoren bestromt** |
| SLAM ohne Nahbereichsschutz | zusätzlich `safety:=false` | **ja, ohne Notbremse** |
| Lokalisierung | `slam.launch.py delete_db:=false localization:=true start_at_origin:=true` | **ja** |
| Handsteuerung | `ros2 launch robot_bringup teleop_joy.launch.py` | fährt über `cmd_vel_smoothed` |
| Handsteuerung ohne Monitor | zusätzlich `cmd_topic:=/cmd_vel` | **ja, ohne Notbremse** |

Die Befehle mit `active_drive:=true` beschreiben die vorhandenen Launchpfade,
sind aber keine Fahrfreigabe. Im aktuellen Encoderbranch verhindern
`counts=0`, `encoder_expected_segment=0` oder
`encoder_expected_resolution=0` den echten Positionsmodus, bis H2/H3 aus
`docs/ENCODER_ODOMETRIE_FIX.md` bestanden, alle drei Werte bestätigt und die
konkrete Bewegungsphase ausdrücklich freigegeben ist.

Bequemer über die Skripte in `tools/kartierung/` — sie beenden RTAB-Map korrekt
und kontrollieren, ob das Wörterbuch geschrieben wurde.

---

## 4. Werkzeuge

| Datei | Zweck |
|---|---|
| `tools/kartierung/start_slam.sh` / `stop_slam.sh` | SLAM starten; **sauber** beenden mit Wörterbuch-Kontrolle |
| `tools/kartierung/start_lokalisierung.sh` | Lokalisierungsmodus, wahlweise ohne Vorwissen |
| `tools/kartierung/kartierfahrt.py` | autonome Fahrt, hält selbst vor Hindernissen |
| `tools/kartierung/erkundungsfahrt.py` | Ziele an der Grenze bekannt/unbekannt |
| `tools/kartierung/lokalisierung_kidnapped.py` | **belastbarer** Lokalisierungstest |
| `tools/kartierung/karte_bereinigen.py` | entfernt Strahlartefakte |
| `tools/kartierung/karte_ansehen.py` | rendert Karte mit Maßstabsraster |
| `tools/kartierung/merkmale_messen.py` | Bildmerkmale und Tiefenabdeckung |
| `tools/kartierung/encoder_position_pruefen.py` | strikt read-only: Position, Wortfolge und Counts/Umdrehung bestimmen |
| `docs/82-ftdi-latency.rules` | udev-Regel, senkt FTDI-Latenz 16 ms → 1 ms |

---

## 5. Hardware und Gerätepfade

| Gerät | Pfad / Kennung | Bemerkung |
|---|---|---|
| Antrieb RS485 | `/dev/ttyUSB_BASE` → ttyUSB0 | FTDI FT232, udev-Alias, `latency_timer=1` |
| VL53L7CX (2×) | I²C über CH341A | Busnummer **wechselt**, Node sucht sie selbst |
| OAK-D-S2 | USB, 03e7:2485 | udev-Regel `80-movidius.rules` |
| Controller | `/dev/input/js0` | DualShock über Bluetooth |

**Motorregister** (ESS23-RS, über Modbus FC03 lesen / FC06 schreiben; auf FC04
antwortet der Antrieb **nicht**):

| Register | Bedeutung | Wert |
|---|---|---|
| `0x000A` / `0x000B` | absolute Position high/low (nur lesen, signed 32 Bit) | Wortfolge über `0x0019` |
| `0x000C` | Ist-Drehzahl (nur lesen, signed) | Diagnose |
| `0x0011` | Segment/Subdivision | typ. 1000; nur als Kandidat lesen |
| `0x0019` | 32-Bit-Wortfolge | 0 high-low, 1 low-high |
| `0x0101` | Encoderauflösung, 4 x Linienzahl | typ. 4000; nur als Kandidat lesen |
| `0x001D` | Solldrehzahl, **Vorzeichen = Richtung** | ±3000 |
| `0x001E` / `0x001F` | Beschleunigen / Bremsen [ms] | 2500 / 400 |
| `0x0020` | **Startdrehzahl** | 5 rpm |
| `0x0027` | Kommando | `0x0002` Start, `0x0100` Stop |

---

## 6. Daten außerhalb des Repositories

Diese Daten liegen **bewusst nur lokal** — sie enthalten Wohnungsgeometrie:

| Was | Wo |
|---|---|
| RTAB-Map-Datenbank | `~/.local/share/amadeus/rtabmap.db` (~258 MB) |
| Geprüfte Sicherung | `~/.local/share/amadeus/rtabmap_20260728_lokalisierung_ok.db` |
| Karten-Schnappschüsse | `~/.local/share/amadeus/maps/amadeus/<version>/` |
| Protokoll der Lokalisierungsläufe | `~/.local/share/amadeus/lokalisierungstests.log` |

Im Repository liegen nur **synthetische** Testkarten
(`src/robot_navigation/maps/`) — erkennbar daran, dass sie keine unbekannten
Bereiche enthalten.

---

## 7. Weitere Komponenten

| Komponente | Pfad | Reifegrad |
|---|---|---|
| iOS-App „Robotersteuerung" | `ios/Robotersteuerung/` | Entwurf, 14 Swift-Dateien |
| Übergabeprotokolle | `integration/` | Dokumentation |
| Prüfplan | `Roboter_Pruefplan.md`, `pruefplan_jetson.sh` | produktiv genutzt |
