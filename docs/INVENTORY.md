# Inventar

**Hardwarestand:** 17.08.2026 · Erfasst auf dem Jetson (`~/roboter_ws`)
**Softwaredelta:** 17.08.2026 · Branch
`feature/hybrid-erkundung-app`; dreistufige App-Erkundung real bis 88,30 %
abgenommen, erfolgreich bediente Frontier-Umfelder gegen Wiederholung gesperrt

**Sensorfusionsdelta:** 30.08.2026 · Ausgangscommit `00f6e52` auf
`feature/modulare-sensorfusion`, Driftkorrektur auf
`fix/sensorfusion-imu-bias`; modulare Encoder-/OAK-IMU-Fusion,
stillstandsgebundene thermische Biasnachfuehrung, Kipp-Scanfilter und optionale
radunabhaengige LiDAR-Bewegungsreferenz; Langzeitstillstand motorlos bestanden

**HWT601-Delta:** 30.08.2026 · Branch `feature/hwt601-integration`;
read-only Modbus-Treiber, eigener USB-RS485-Pfad, Diagnose und motorloser
Stufenstart vorbereitet; Hardware, Montage-TF, Skala und Kovarianzen noch nicht
real abgenommen

**HWT601-USB-Delta:** 08.09.2026 · `fix/hwt601-usb-commissioning`;
CH340 `1a86:7523` physisch erkannt. Fehlender CH341-Kerneltreiber gebaut,
gezielte USB-Regeln/Installer/Rueckfall und Messwerkzeug getestet vorbereitet.
Systeminstallation inzwischen vom Nutzer ausgefuehrt. 60-s-Rohdatenlauf:
6.000 Antworten ohne Fehler bei rund 100 Hz; ROS-Ausgabe bestanden.
Montage-TF, Gyroskala, Bias/Langzeitverhalten und Fusionsfreigabe noch offen.

**HWT-Montagereferenz:** `feature/hwt601-mount-frame`; Nutzerangaben als
separater nominaler Fussplattenframe `hwt601_mount` hinterlegt und motorlos
per TF geprueft. -90 Grad Yaw, x=0,084/y=0/z=-0,056 m zu bestehendem
`base_link`. Kein erfundener Chipursprung; keine automatische Fusionsfreigabe.

Reifegrade: **produktiv** = am echten Roboter getestet · **erprobt** = läuft,
aber nicht abschließend abgenommen · **Entwurf** = vorhanden, ungetestet

**HWT-Biasdelta:** `feature/hwt601-stationary-bias`, 08.09.2026:
zehn Minuten echte IMU mit bestehender Biasnachfuehrung bestanden;
maximaler absoluter korrigierter Z-Winkel 0,03985 Grad. Nur abgesprochener
Stillstand des bereits eingeschalteten Sensors, keine Bewegungsfreigabe.

---

## 1. Umgebung

| | |
|---|---|
| Rechner | Jetson (`p-desktop`), Kernel 5.15.199-tegra |
| Betriebssystem | Ubuntu 22.04.5 LTS |
| ROS | 2 Humble |
| Arbeitskopie | `~/roboter_ws` — **maßgeblich** |
| Zweitkopie | `/media/p/64GB/roboter_ws` (USB-Stick, älterer Stand) |
| Freier Speicher | ~91 GB |

---

## 2. ROS-2-Pakete

| Paket | Zweck | Reifegrad |
|---|---|---|
| `base_hardware` | Antrieb über RS485/Modbus; Encoderpositions-Odometrie H0–H4 real bestanden, H5 offen | **erprobt (Encoder)** |
| `vl53_near_field` | 2× VL53L7CX über CH341A (Treiber gepinnt in `vendor_ch34x_mphsi.repos`, per DKMS kernelupdate-fest), Nahbereichsschutz, `collision_monitor` | **produktiv** (15.08.2026 in realer Nav2-Kette mit frischen Daten überwacht) |
| `robot_bringup` | Startdateien für Roboter, SLAM, Kamera, Handsteuerung und einzelner App-Kartierungsstack | **produktiv** (App-Erkundungsstack real abgenommen) |
| `robot_map_manager` | versionierte Kartenablage, Schnittstelle zur App | **produktiv** |
| `semantic_map_manager` | manuelle Raum-Overlays, fest an gespeicherte Kartenfingerprints gebunden | **produktiv** (App-/Jetson-Persistenz und reales Raumziel abgenommen) |
| `robot_description` | URDF/Xacro, Sensor-Frames | erprobt |
| `robot_state_estimation` | portable Sensoradapter, Qualitaets-/Schlupfueberwachung, IMU-Scanfilter und lokaler `robot_localization`-EKF | **erprobt (motorlos)** |
| `robot_navigation` | Nav2-Realprofil mit globalem Zwei-Scan-Lokalisierer, fail-closed Missions-Gate, Glättung und VL53-Kollisionskette | **erprobt** (drei Kaltstarts an bestaetigter Pose und anschliessendes Raumziel real bestanden) |
| `robot_interfaces` | eigene Nachrichten (u. a. `NearFieldStatus`) | **produktiv** |
| `safety_monitor` | Sicherheitsüberwachung | erprobt |
| `semantic_perception` | Objekterkennung auf OAK-Bildern | Entwurf |
| `mission_manager` | Auftragsverwaltung; Raumziel standardmäßig simuliert, reale Nav2-Fahrt nur per explizitem Opt-in | **erprobt** (ein beaufsichtigtes Raumziel real erreicht) |
| `bt_orchestrator` | Behavior-Tree-Ablaufsteuerung mit reaktiver Not-Aus-Bedingung und sicherem Subscription-Vorlauf | **erprobt** (in realer Explore-Kette abgenommen) |
| `llm_planner` | Sprachgestützte Auftragsplanung | Entwurf |
| `smartphone_gui` | Weboberfläche | erprobt |
| `robot_face` | Gesichtsanzeige | erprobt |
| `explore` | Dreistufige Erkundung: Rundblick, sichere Frontier-Ziele und adaptive Abdeckung aus realer Fahrspur | **produktiv** (88,30 % im beaufsichtigten Akku-Realtest) |
| `handeye_calibration` | Kamera-Arm-Kalibrierung | Entwurf |
| `mock_servers` | Testgegenstellen ohne Hardware | erprobt |
| `behaviortree_ros2` | **Submodul** → github.com/BehaviorTree/BehaviorTree.ROS2 (humble) | extern |

---

## 3. Startbefehle

| Zweck | Befehl | Hardware aktiv? |
|---|---|---|
| Kamera allein | `ros2 launch robot_bringup oak.launch.py` | nein |
| Sensor-Fusion, harter Motorlos-Test | `ros2 launch robot_bringup state_estimation_validation.launch.py` | nein (`dry_run=true`, RS485 gesperrt) |
| Nur passive Fusionsknoten | `ros2 launch robot_state_estimation fusion.launch.py` | nein; startet keine Treiber |
| Nur HWT601-Rohdaten | `ros2 launch robot_state_estimation hwt601.launch.py` | nein; liest nur die IMU, keine OAK/Motoren |
| HWT601-Stufentest | `ros2 launch robot_bringup state_estimation_hwt601_validation.launch.py` | nein (`dry_run=true`, Motor-RS485 gesperrt; OAK/Fusion aus) |
| SLAM/Kartierung | `ros2 launch robot_bringup slam.launch.py active_drive:=true` | **ja, Motoren bestromt** |
| SLAM ohne Nahbereichsschutz | zusätzlich `safety:=false` | **ja, ohne Notbremse** |
| Lokalisierung | `slam.launch.py delete_db:=false localization:=true start_at_origin:=true` | **ja** |
| Globale LiDAR-Lokalisierung, Preflight | `bash tools/kartierung/start_lidar_lokalisierung.sh /absolut/map.yaml oak:=false` | nein (`dry_run`) |
| Globale LiDAR-Lokalisierung, scharf | `AMADEUS_FAHRFREIGABE=JA bash tools/kartierung/start_lidar_lokalisierung.sh /absolut/map.yaml active_drive:=true oak:=false` | **ja, Motoren bestromt** |
| Automatische LiDAR-Kartierung, Preflight | `bash tools/kartierung/start_automatische_kartierung.sh active_drive:=false enable_auto_explore:=true` | nein (`dry_run`) |
| Automatische LiDAR-Kartierung, scharf | `AMADEUS_FAHRFREIGABE=JA bash tools/kartierung/start_automatische_kartierung.sh active_drive:=true enable_auto_explore:=true` | **ja, autonom fahrend** |
| App-Kartierung, Preflight | `bash tools/kartierung/start_app_erkundung.sh active_drive:=false enable_auto_explore:=true` | nein (`dry_run`) |
| App-Kartierung, scharf | `AMADEUS_FAHRFREIGABE=JA bash tools/kartierung/start_app_erkundung.sh active_drive:=true enable_auto_explore:=true` | **ja, autonom fahrend** |
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
| `tools/kartierung/start_automatische_kartierung.sh` | dreistufige SLAM-/Nav2-/Explore-Kette ohne App-Dienste; scharf nur mit zwei Opt-ins |
| `tools/kartierung/start_app_erkundung.sh` | einzelner dreistufiger Kartierungs-, App-, rosbridge- und Kartenmanager-Stack; Doppelstartschutz |
| `tools/kartierung/start_lokalisierung.sh` | Lokalisierungsmodus, wahlweise ohne Vorwissen |
| `tools/kartierung/kartierfahrt.py` | autonome Fahrt, hält selbst vor Hindernissen |
| `tools/kartierung/erkundungsfahrt.py` | Ziele an der Grenze bekannt/unbekannt |
| `tools/kartierung/lokalisierung_kidnapped.py` | **belastbarer** Lokalisierungstest |
| `tools/kartierung/karte_bereinigen.py` | entfernt Strahlartefakte |
| `tools/kartierung/karte_ansehen.py` | rendert Karte mit Maßstabsraster |
| `tools/kartierung/merkmale_messen.py` | Bildmerkmale und Tiefenabdeckung |
| `tools/kartierung/encoder_position_pruefen.py` | strikt read-only: Position, Wortfolge und Counts/Umdrehung bestimmen |
| `docs/82-ftdi-latency.rules` | udev-Regel, senkt FTDI-Latenz 16 ms → 1 ms |
| `tools/sensorfusion/hwt601_usb_pruefen.py` | liest USB-Merkmale und erzeugt nur bei eindeutiger Seriennummer einen udev-Vorschlag |
| `tools/sensorfusion/hwt601_usb_setup.py` | Jetson-CH340-Treiber vorbereiten/installieren, gezielte udev-Ausnahme, recoverbarer Rueckfall |
| `tools/sensorfusion/hwt601_messen.py` | begrenzter, ROS-/motorloser HWT-Rohdatentest; default nur lauschen |
| `docs/83-hwt601.rules.example` | nicht installierbare Vorlage fuer den getrennten HWT-USB-RS485-Alias |

---

## 5. Hardware und Gerätepfade

| Gerät | Pfad / Kennung | Bemerkung |
|---|---|---|
| Antrieb RS485 | `/dev/ttyUSB_BASE` → ttyUSB0 | FTDI FT232, udev-Alias, `latency_timer=1` |
| VL53L7CX (2×) | I²C über CH341A | Busnummer **wechselt**, Node sucht sie selbst |
| OAK-D-S2 | USB, 03e7:2485 | udev-Regel `80-movidius.rules` |
| HWT601 (Nutzerangabe) | `/dev/ttyUSB_HWT601` → ttyUSB0 | CH340 `1a86:7523`, fester USB-Port `1-2.4.4.4`; Rohdaten/ROS geprueft; Montage, Gyroskala, Langzeitverhalten/Isolation offen |
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
| `0x001E` / `0x001F` | Beschleunigen / Bremsen [ms] | 2000 / 400 |
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
| Manuelle Raumkarten | `~/.local/share/amadeus/semantic_maps/<fingerprint>/` |
| Protokoll der Lokalisierungsläufe | `~/.local/share/amadeus/lokalisierungstests.log` |

Im Repository liegen nur **synthetische** Testkarten
(`src/robot_navigation/maps/`) — erkennbar daran, dass sie keine unbekannten
Bereiche enthalten.

---

## 7. Weitere Komponenten

| Komponente | Pfad | Reifegrad |
|---|---|---|
| iOS-App „Amadeus" | `ios/Robotersteuerung/` | Raumeditor und Raumwahl am realen ROS-System abgenommen |
| Übergabeprotokolle | `integration/` | Dokumentation |
| Prüfplan | `Roboter_Pruefplan.md`, `pruefplan_jetson.sh` | produktiv genutzt |
