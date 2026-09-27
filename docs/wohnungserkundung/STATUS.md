# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus · Stand 27.09.2026 · Stufe 3 weiterhin OFFEN/GELB**

**Aktuelle Entscheidung:** Konsolidierung statt Komplettneubau. Maßgeblich sind
[MASTERPLAN.md v1.0](MASTERPLAN.md), die unveränderte
[WE-Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) und
[MEILENSTEINE.md](MEILENSTEINE.md). Dies ist der einzige laufende WE-Iststand.

## 1. Sofortiger Arbeitsfokus

**Nächster Auftrag:** Genau einen begrenzten **motorlosen HWT-Erfassungslauf**
mit dem Diagnosekandidaten aus Abschnitt 3 nach aktueller Gerätefreigabe
durchführen und auswerten. TOR 1 ist softwareseitig umgesetzt; TOR 2 bleibt
gesperrt. Ein neuer Lauf kann nur heutiges Verhalten erklären und die fehlende
Einzelursache des alten Fahr-Bags nicht rückwirkend beweisen.
Arbeitsvertrag: [AGENTENAUFTRAG.md](AGENTENAUFTRAG.md).

Keine neue Wohnungsfahrt, kein kompletter Rewrite, kein OS-Neuaufbau, kein
automatischer Merge und kein aktiver Installwechsel. Die vorhandene
HWT-/VL53-Schutzwirkung bleibt fail-closed. Erst nach identifizierter und als
recoverbar belegter Einzelbedingung darf über eine funktionale Recoveryänderung
entschieden werden.

## 2. Konsolidierte Quell- und Buildbasis

| Bereich | Festgestellter Stand | Grenze |
|---|---|---|
| Verbindliche Dokumentreferenz | `docs/we1-masterplan-20260927`, Commit `26360001f65e05a5b88a58581771c241291fa0e5`; separat in einem Bare-Repository geholt | Der Root-Checkout blieb auf `main` (`23928d92…`); `git fetch` darin scheiterte an einer defekten lokalen Checkpoint-Ref. Der Dokumentbranch ist keine Roboter-Runtime. |
| Historischer HWT-/Türvergleich | `1d91229dc10ff4bb791938d49aae8e9808a5dfff` | Vergleichsbeleg und Rückfallreferenz, kein pauschaler Rollback. |
| Letzter vor der Integration veröffentlichter WE-Quellstand | PR #101 / `codex/we1-hwt601-fusion` bei `40b5b49c9a92600484a0dc85c466930bc1680c60` | Kein Beleg für ausgeführte Pakete oder lokalen Install. Der Masterplan-Commit hat dieselbe Quellbasis; sein Diff zu `40b5b49` betrifft nur Dokumentation. |
| Zuletzt verwendeter lokaler Parity-Bestand | `/home/p/roboter_ws-parity-reset`, Branch `feature/parity-reset`, HEAD `40b5b49…`; sieben veränderte getrackte Dateien plus `docs/WE_PARITY_RESET.md` und `src/explore/config/hwt601_parity_params.yaml` | Änderungen und Buildartefakte blieben unangetastet. Die Quelländerungen wurden in den neuen Integrationsworktree übernommen; im Ursprungsworktree waren sie uncommittet. |
| Neue Integrationslinie | `docs/we1-integrationsbasis-audit`, Worktree `/home/p/roboter_worktrees/we1-integrationsbasis-audit`, Start-Commit `2636000…`; Quelländerungen aus dem Parity-Worktree | Dokumentationsbasis plus festgehaltene lokale Kandidatenänderungen. Kein Deployment und keine Aussage, dass dieser Baum bereits auf dem Roboter lief. |
| Letzter dokumentierter Installkandidat | `~/roboter_ws-parity-reset/install_parity_real`; projektseitig als separates Overlay des 27.09.-Laufs beschrieben | Die gespeicherte Buildauswahl vom 27.09. 08:53 enthält nur `vl53_near_field`. Die tatsächlich gesourcte Präfixreihenfolge und Package-SHAs des aktiven Laufs sind nicht unabhängig protokolliert. `/home/p/roboter_ws/install` blieb laut Übergabe unverändert. |
| Host des frischen Builds | Ubuntu 22.04.5, `aarch64`, ROS 2 Humble, `/opt/ros/humble`, Python 3.10.12, GCC 11.4 | Host-/Buildumgebung, kein Beleg der Runtime-Auflösung des Realtests. |
| BT-Submodul | Gitlink `6c6aa078ee7bc52fec98984bed4964556abf5beb`; im neuen Worktree genau auf diesen SHA ausgecheckt | Im ursprünglichen Parity-Worktree war das Submodul nicht initialisiert. |
| Externer CH341A-Treiber | `vendor_ch34x_mphsi.repos` pinnt `f33863fbbf322a85f960b1701e7148db0b7b2d85` | Quell-/DKMS-Installationsstand auf dem Robotersystem wurde nicht geprüft. |
| Parity-Profil | `explore/config/hwt601_parity_params.yaml`; laut Kandidatenbericht 900 s, höchstens ein Portal und sechs Abdeckungsziele; aktive WE-Navigation bleibt aus | Profil-/Launchzuordnung des Realtests ist nicht im Bag enthalten; sie bleibt durch die Übergabedokumentation berichtet. |
| Motorbus / TF / Auftrag | Der HWT-Mappingpfad in `slam_lidar_hwt601.launch.py` wählt bei `active_drive=true` genau `base_hardware`, sonst ausschließlich den lesenden `encoder_shadow_reader`; nie beide. EKF publiziert `odom→base_link`, `slam_toolbox` `map→odom`. `nav_mapping.launch.py` wählt genau einen SLAM-Include, einen Explorer und eine Mission-Manager/BT-Kette; der Explorer sendet Nav2-Unterziele. | Statische Launch-Zuordnung, keine Live-Zählung von Knoten, TF-Publishern oder Ziel-Handles. Paralleler Fremdstart bleibt möglich und wurde nicht geprüft. Keine zweite aktive WE-Navigation ergänzt. |

Außerhalb dieser Linie waren der Root-Checkout `main` sauber, der lokale
Parity-Worktree mit den oben genannten uncommitteten Quell-/Dokumentenänderungen
und der HWT-Fusion-Worktree nur mit drei Dokumentänderungen. Letzterer ergänzt
den 26.09.-Befund: hinter dem Mission-Gate kamen bei 0,12 rad/s nur drei kurze
0,015-rad/s-Smootherimpulse an; der Collision Monitor gab 0,0045 rad/s weiter,
die Basis blieb mit maximal 1,32 RPM unter ihrer unveränderten 5-RPM-
Startdrehzahl. Die tatsächliche Smoother-Ursache blieb offen. Derselbe Messbefund
und die begründete 0,08-rad/s-Paritywahl stehen in
[`WE_PARITY_RESET.md`](../WE_PARITY_RESET.md); keine HWT- oder Smoother-
Parameteränderung wird daraus abgeleitet. Die übrigen geprüften Worktrees waren
sauber; mehrere enthalten alte Build-/Install-/Logordner, die nicht als aktuelle
Auflösung gewertet wurden.

Die Integration führt keine ältere HWT-Referenz über spätere Sensor-, Nav2-,
Cancel- oder Shutdownkorrekturen zurück. `PROJECT_MEMORY.md`,
`ROBOT_TRANSFER.md` und `docs/WE_PARITY_RESET.md` enthalten die vorherigen
Nachweise; dieser STATUS ordnet sie dem Kandidaten zu.

## 3. Frische Build- und Softwarebelege

Alle frischen Artefakte liegen außerhalb des Roboters und außerhalb des
Arbeitskopie-Installpräfixes unter `/tmp/we1-*`.

| Prüfung | Ergebnis | Evidenz / Grenze |
|---|---|---|
| Vollständiger frischer Colcon-Build, Standardumgebung | **BLOCKIERT** | `behaviortree_ros2` bricht im `behaviortree_cpp`-CMake-Export ab: das ROS-Paket sucht `libbehaviortree_cpp.so` unter `/opt/ros/humble/lib`, die installierte Datei liegt unter `/opt/ros/humble/lib/aarch64-linux-gnu/`. `CMAKE_LIBRARY_PATH` greift wegen `NO_DEFAULT_PATH` nicht. |
| Vollständiger isolierter Build mit temporärem BT-CMake-Pfad | **BESTANDEN** | 24/24 Pakete in 2 min 41 s; `/tmp/we1-full-shim-build`, `/tmp/we1-full-shim-install`, `/tmp/we1-full-shim-log2`. Nur im temporären Präfix liegt ein Symlink zum unveränderten ROS-CMake-Export und zur bereits installierten Bibliothek. Keine Quell- oder Systempaketänderung; der Shim ist lediglich eine Buildvoraussetzung dieses Hosts. |
| Frischer isolierter Teilbuild | **BESTANDEN** | `colcon build --packages-up-to explore vl53_near_field`; sechs Pakete einschließlich `robot_interfaces`, `base_hardware`, `robot_state_estimation`, `vl53_near_field` und `explore`; Präfixe unter `/tmp/we1-target-install`. Kein lokales Install gesourct. |
| `explore`-Tests | **BESTANDEN** | 925/925; `/tmp/we1-target-build/explore/pytest.xml`. |
| Direkte gerätefreie Vertragstests | **BESTANDEN** | 86 Tests aus VL53, HWT-Health, Mission-Gate/Nav-Vertrag und Safety Monitor bestanden. Direkter Aufruf mit ROS-Humble-Python, getrennt vom Colcon-Testlauf. |
| Regressionen auf dem vollständigen isolierten Build | **BESTANDEN** | `colcon test` für `base_hardware`, `robot_state_estimation`, `robot_navigation`, `mission_manager`, `bt_orchestrator`, `robot_bringup`; `colcon test-result`: 259 Tests, 0 Fehler, 0 Fehlschläge. `mission_manager` registriert dabei 0 Tests; seine 45 Quelltests bestanden zusätzlich direkt mit `python3 -m pytest -q src/mission_manager/test`. |
| Colcon-Testregistrierung `vl53_near_field` | **KEIN NACHWEIS** | `colcon test` meldete 0 Tests in diesem Paket. Die 86 obigen direkten Tests sind der Softwarebeleg für den ausgewählten Umfang. |
| Paketauflösung im frischen Overlay | **BESTANDEN** | Nach `/opt/ros/humble/setup.bash` plus `/tmp/we1-full-shim-install/local_setup.bash` zeigen `ros2 pkg prefix` für `behaviortree_ros2`, `bt_orchestrator`, `robot_bringup`, `robot_navigation`, `mission_manager`, `explore`, `vl53_near_field`, `base_hardware`, `robot_state_estimation` ausschließlich auf `/tmp/we1-full-shim-install/<Paket>`. BT-Submodul `6c6aa078…`, ROS `behaviortree_cpp` 4.9.1, Nav2 1.1.20 und RTAB-Map ROS 0.23.7. |
| Gesamtprozess und Runtime-Auflösung des Realtests | **OFFEN** | Kein isolierter Vollstackstart oder integrierter Missionsablauf ausgeführt. Quell- und Buildauflösung sind belegt, die tatsächlich gesourcte Präfixreihenfolge des alten Realtests nicht. |
| Aktive Installation, Zielsystem und Hardware | **NICHT GEPRÜFT** | Neuer Installpräfix nicht aktiviert. Keine Roboterknoten, Aktoren, Geräte, Deployment- oder Fahrtests gestartet. |

Buildlogs: `/tmp/we1-integrationsbasis-log` (erster Vollbuild),
`/tmp/we1-full-shim-log2` (erfolgreicher Vollbuild), `/tmp/we1-target-log` und
`/tmp/we1-target-test-log`; Präfixe `/tmp/we1-full-shim-install` und
`/tmp/we1-target-install`. Diese Artefakte sind keine Roboter-Runtime.

Der Vollbuild ist reproduzierbar mit ROS Humble als einzigem Underlay und
dem gepinnten BT-Submodul. Vor `colcon build` wird außerhalb des Repositories
ein temporäres Präfix mit `share/behaviortree_cpp/cmake` als Symlink auf
`/opt/ros/humble/share/behaviortree_cpp/cmake`, `include` auf
`/opt/ros/humble/include`, `lib/aarch64-linux-gnu` auf
`/opt/ros/humble/lib/aarch64-linux-gnu` und
`lib/libbehaviortree_cpp.so` auf die installierte gleichnamige Bibliothek
angelegt. Der Buildaufruf nutzt
`--cmake-args -Dbehaviortree_cpp_DIR=/tmp/we1-btcpp-compat/share/behaviortree_cpp/cmake`
und getrennte `--build-base`, `--install-base`, `--log-base` unter `/tmp`.
Der temporäre Pfad gleicht nur die falsche Bibliothekssuche im ROS-Export aus;
er ist **kein** zusätzliches Roboter-Underlay.

Auf diesem Host verwendeter gerätefreier Buildweg (neue temporäre Zielpfade
für einen erneuten Lauf wählen, falls Artefakte erhalten bleiben sollen):

```bash
mkdir -p /tmp/we1-btcpp-compat/share/behaviortree_cpp /tmp/we1-btcpp-compat/lib
ln -sfn /opt/ros/humble/share/behaviortree_cpp/cmake /tmp/we1-btcpp-compat/share/behaviortree_cpp/cmake
ln -sfn /opt/ros/humble/include /tmp/we1-btcpp-compat/include
ln -sfn /opt/ros/humble/lib/aarch64-linux-gnu /tmp/we1-btcpp-compat/lib/aarch64-linux-gnu
ln -sfn /opt/ros/humble/lib/aarch64-linux-gnu/libbehaviortree_cpp.so /tmp/we1-btcpp-compat/lib/libbehaviortree_cpp.so
source /opt/ros/humble/setup.bash
colcon --log-base /tmp/we1-full-shim-log2 build --base-paths src \
  --build-base /tmp/we1-full-shim-build --install-base /tmp/we1-full-shim-install \
  --parallel-workers 4 --event-handlers log+ \
  --cmake-args -Dbehaviortree_cpp_DIR=/tmp/we1-btcpp-compat/share/behaviortree_cpp/cmake
```

Quell- und Betriebszuordnung: Der dokumentierte Startpfad des letzten
Parity-Laufs ist `robot_bringup app_mapping.launch.py` →
`robot_navigation nav_mapping.launch.py` mit `active_drive`,
`use_hwt601_odometry`, `operator_stationary_confirmed`,
`enable_auto_explore` und `explore_params_overlay` als ausdrücklichen
Launch-Argumenten; der Explore-Auftrag kam danach als
`{"type":"explore"}` über `/mission_manager/command_json`.
`hwt601_parity_params.yaml` ist der beabsichtigte Overlay-Pfad und bleibt
standardmäßig **nicht** aktiv. Dies ist eine Zuordnung aus Launchcode und
Testbericht, kein erneuter Start oder unabhängiger Nachweis der tatsächlich
gesourcten Präfixe des 27.09.-Laufs. Python-Abhängigkeiten auf dem Buildhost:
`numpy 1.21.5`, `smbus2 0.6.1`, `vl53l5cx 1.0.1`; der externe CH341A-Treiber
ist auf `f33863f…` gepinnt, seine installierte DKMS-Version nicht geprüft.

### TOR-1-Diagnosekandidat auf dieser Integrationslinie

| Zuordnung | Nachweis und Grenze |
|---|---|
| Ausgang / Quellstand | PR #103, `docs/we1-integrationsbasis-audit` bei `3ed63f278b668fe9be64ce02568911e1b99f7fe8`; darauf Codecommit `f1f6b74a5e5aea1ba43c50beb75f5f954218fb78`. Die zuvor uncommitteten Parity-Änderungen sind bereits im Integrationscommit `21ff064…` gesichert; keine neue lokale Quellmischung. |
| Diagnoseänderung | `Hwt601FusionHealth` hält nach erster Readiness genau den ersten latched Fehler mit Wächtername, Sammelgrund, allen sechs Rohstatusprädikaten samt Wert/Typ/Grenze, vollständigem Rohstatus, Quell- und Statuszeiten, letzter gültiger Rohmessung und vorhandenen Treiberzählern im Speicher fest. Das bestehende `/fusion/hwt601/status_json` enthält additiv `first_fault`; gesunde spätere Meldungen überschreiben ihn nicht. Keine Dateioperation im Schutzpfad. |
| Frischer isolierter Build | ROS-Humble-Underlay `/opt/ros/humble` → gesicherter Vollbuild `/tmp/we1-full-shim-install/local_setup.bash` → nur zwei neu gebaute Python-Pakete `/tmp/we1-hwt-f1f6b74-install/local_setup.bash`. Build-/Logpfade `/tmp/we1-hwt-f1f6b74-build` und `/tmp/we1-hwt-f1f6b74-log`; `robot_state_estimation` und `robot_navigation` 2/2 gebaut. Bestehender BT-CMake-Symlinkpfad `/tmp/we1-btcpp-compat` war für den Vollbuild nötig, wurde nicht ins Zielsystem übernommen. |
| Effektive Paketauflösung | `robot_state_estimation` und `robot_navigation` aus `/tmp/we1-hwt-f1f6b74-install`; `vl53_near_field`, `base_hardware`, `explore`, `mission_manager`, `bt_orchestrator`, `robot_bringup` aus `/tmp/we1-full-shim-install`; `behaviortree_cpp`, `robot_localization`, `slam_toolbox` auf diesem Buildhost aus `/opt/ros/humble`. Die spätere Zielsystemauflösung wird vor einem Start neu erfasst. |
| Profile / Startvertrag | Beabsichtigter motorloser Pfad: `robot_bringup/app_mapping.launch.py`, `active_drive=false`, `use_hwt601_odometry=true`, `enable_auto_explore=false`, `start_web_gui=false`, `explore_params_overlay=src/explore/config/hwt601_parity_params.yaml`. `operator_stationary_confirmed=true` erst nach tatsächlicher Bestätigung vor Ort. Dies ist vorbereitet und wurde **nicht gestartet**. |
| Treiber / BT | Host: `pyserial 3.5` für den HWT-Serialtransport, `vl53l5cx 1.0.1`, `smbus2 0.6.1`, `numpy 1.21.5`; `ch34x-mphsi/1.0` für Kernel `5.15.199-tegra` via DKMS installiert; Quellpin `f33863f…`. `ros-humble-behaviortree-cpp` `4.9.1-1jammy.20260725.161519`; der BT-Orchestrator löst `libbehaviortree_cpp.so` tatsächlich nach `/opt/ros/humble/lib/aarch64-linux-gnu/` auf. Versions- und Linkbelege stammen vom Buildhost, nicht vom alten Fahrprozess. |
| Tests | 76 fokussierte HWT-/Gate-Tests direkt bestanden. Frischer 2-Paket-Build und `colcon test-result`: 177 Tests, 0 Fehler/Fehlschläge; diese Läufe überschneiden sich und werden nicht addiert. Manifestwerkzeug rein lesend unter `/tmp/we1-hwt-f1f6b74-manifest.json` ausgeführt; Quellcommit, saubere Arbeitskopie, installierte Dateihashes, Paketpräfixe, BT-Link und Treiberversionen geprüft. Kein ROS-Knoten, Port oder Aktor gestartet. |
| Motorlose Erfassung | **OFFEN / aktuelle Gerätefreigabe erforderlich.** Das neue `first_fault` enthält deshalb noch keinen real gemessenen Einzelwert. Keine Wiederholung der alten Fahrt und keine Annahme eines bestimmten HWT-Defekts. |

Das Manifestwerkzeug `tools/kartierung/hwt_diagnose_manifest.py` schreibt erst
bei ausdrücklich übergebenem lokalem Ausgabepfad eine neue JSON-Datei außerhalb
des Repositories. Es startet keine Geräte oder ROS-Prozesse. Für eine spätere
Messung werden die tatsächlich gesourcten Setup-Dateien, das Profil mit SHA256,
Launchargumente, `AMENT_PREFIX_PATH`, Paketpräfixe und installierte Modul- und
Executable-Hashes **vor Ort erneut** erfasst. Der `/tmp`-Probeausdruck ist
kein Nachweis eines Roboterstarts.

## 4. Abort-, Stop- und Latch-Inventur des Bewegungspfads

| Auslöser / Datenquelle / Grenze | Gegenwärtige Wirkung und Besitzer | Wiederherstellung / Einordnung | Evidenz |
|---|---|---|---|
| HWT-Rohdatenstatus: `ready`, `raw_data_ready`, Port `/dev/ttyUSB_HWT601`, keine Sensor-Schreibbefehle, `consecutive_errors == 0`, `age_s` 0–0,20 s; korrigierter HWT-Status max. 0,35 s; Encoderfeedback im Fahrmodus max. 0,30 s; Statusherzen max. 1,0 s | `Hwt601FusionHealth` macht nach erster Readiness den ersten Quellenfehler dauerhaft zum `latched_fault`. `cmd_vel_mission_gate` sperrt Bewegung. Ein frischer EKF-Ausgabestempel hebt die Rohquellenprüfung nicht auf. | Kein automatisches Entlatchen im selben Health-Objekt. Die äußere Explore-/BT-Mission endet bei terminalem Fehler; eine neu gesendete Mission wäre keine nachgewiesene Fortsetzung. | `hwt601_fusion_health.py`, Gate-Tests und lokales Bag; der Rohstatus-Topic fehlt im Bag. |
| Ungültige/stale VL53-Paarquelle; Mission-Gate `explore_sensor_timeout_s = 0.8 s`; Collision Monitor `source_timeout = 3.0 s` | Mission-Gate sperrt bei stale Scan, beiden VL53-Punktwolken oder Nahbereichsstatus. Collision Monitor verarbeitet die Zonen; sein eigener 3-s-Quelltimeout ist für sich allein kein Frischebeleg und wird nicht als fail-closed-Stopp klassifiziert. Kandidaten-Recovery: nach 3 Lesefehlern Ranging-Neustart, bei Folgefehlern höchstens 2 Reinitialisierungen des betroffenen Treibers, 2 vollständige Frames bis zur Wiederfreigabe; danach bleibt finaler Kanalfehler gesperrt. Besitzer: `vl53_near_field`, Mission-Gate und Collision Monitor. | Nur neue vollständige Paare können die Quelle erholen. Bewegung bleibt bis dahin gesperrt. Kein Fortsetzen der Mission nach Sensor-Recovery belegt. Optionaler Nahbereichs-E-Stop in `safety_monitor` ist standardmäßig aus und ersetzt die Schutzkette nicht. | Geänderte lokale VL53-Dateien, direkte Tests; 125,1 s / 508 gesunde motorlose Statusmeldungen berichtet. Im Lauf vom 27.09. trat kein neuer VL53-Fehler auf. |
| HWT-Yaw-/Bias-/Encoderstatus ungültig oder gelatcht | Fusion-Health sperrt `hwt_motion_ready`; Mission Gate gibt keine Bewegung frei. Encoder-Konfigurationsfehler bleibt eigener Latch. | Stillstand, frische Rohquellen, Bias-/Encoderstatus und Pose müssen neu geprüft werden; automatischer Neustart ist nicht belegt. | Fusion-Health-Tests, HWT-/Encoder-Preflight vom 26.09. berichtet. |
| Stale Scan/Odom beim Rundblick; `/odom` 0,8 s, begrenztes Recoveryfenster 5 s; 15 s ohne 0,03 rad Fortschritt; Rundblicklimit 280 s | Explorer stoppt das Rundblickkommando und prüft Quelle/Fortschritt; bei ausbleibender Erholung bricht er fail-closed ab. | Nur frische Eingänge und gemessener Fortschritt können fortsetzen; Nav2-Recovery ist nicht zuständig. | `explore_params.yaml` und Explore-Vertragstests. |
| Nav2-Unterziel abgebrochen/abgelehnt/timeout; Cancel-Frist 3 s; recoveryfreier BT | Explorer beendet/ordnet das Kindziel ein. Mission Manager/BT beenden bei terminalem Fehler die übergeordnete Mission. | Lokale Frontier-Retries/Neubewertung existieren. Auftragserhalt nach terminalem Missionsfehler ist nicht nachgewiesen. | `exploration_nav_runtime.py`, `mission_manager_node.py`, recoveryfreier BT. |
| Stale Map/TF/Sensorstatus oder ungültige Lokalisierung | Mission Gate, Localization Guard und Nav2 sperren/stoppen die Anfahrt. | Aktuelle Quellen, konsistente `map→odom→base_link`-Pose, Kartenbindung und freier Pfad neu prüfen; kein altes Goal reaktivieren. | `cmd_vel_mission_gate.py`, `localization_guard.py`, Tests und Profil-YAML. |
| E-Stop-Anforderung oder gefährliche Nahdistanz | `/safety/estop=true` ist Schutzstopp. Softwareanforderung ist eigener Eingang; Nahbereichs-E-Stop standardmäßig aus; GPIO ist Platzhalter. | Expliziter Not-Aus/Nutzerabbruch erfordert Ursache und lokale Wiederfreigabe. Softwaretopic ist kein Ersatz für Hardware-Not-Aus. | `safety_monitor_node.py`, 0,2-s-Publishzyklus, Near-Field-Tests und dokumentierte GPIO-Grenze. |
| STL-27L-`buffer overflow` / Exit `-6` nach SIGINT | Shutdown-/Cleanup-Fehler nach Missionsende; nicht mit vorherigem Fahrtorfehler zusammenlegen oder pauschal als harmlos einstufen. | Eigenständiger Shutdownfall. Im 27.09.-Bericht trat er erst beim SIGINT nach beendetem Lauf auf; keine Aussage über andere Phasen. | Lokaler Bericht, Bag und `ROBOT_TRANSFER.md`. |

**Konkrete Zuordnung im konsolidierten Quellbaum:**

| Schutzentscheidung | Code / wirksame Konfiguration | Auftrag und Nachweisgrenze |
|---|---|---|
| HWT-Rohstatus, Statusherz und Latch | `src/robot_state_estimation/robot_state_estimation/hwt601_fusion_health.py:46–65,98–115`; `config/hwt601_shadow.yaml:5–20,39–58`; Eingang `/shadow/hwt601/raw_status_json` in `hwt601_fusion_guard.py:28`; Veröffentlichung des Sammelgrunds in `src/robot_navigation/robot_navigation/cmd_vel_mission_gate.py:804–814` | Das Gate prüft `hwt_failure` in `cmd_vel_mission_gate.py:816–849`. Der erste Fehler nach `was_ready` bleibt verriegelt; weder Auftragserhalt noch Neustart folgen daraus. Bag belegt nur den Sammelgrund. |
| VL53-Paar und Bewegungstor | `src/vl53_near_field/vl53_near_field/vl53_near_field_node.py:328–405,492–555`; `src/robot_navigation/robot_navigation/cmd_vel_mission_gate.py:268,683–733`; `src/vl53_near_field/config/collision_monitor_mapping_params.yaml:31` | Kanal-Recovery ist begrenzt; Paarfrische 0,8 s am Gate. Der Collision-Monitor-Quelltimeout 3 s ist allein keine Stoppgarantie. Tests sind gerätefrei, keine Störung im jüngsten Realtest. |
| Rundblick und Kindziel | `src/explore/config/explore_params.yaml:102,133–143`; `src/explore/explore/explore_node.py:675,694–703,4404–4410`; `src/mission_manager/mission_manager/mission_manager_node.py:442–535,656–710` | Explorer verwaltet den Rundblick und seine Nav2-Kinder; der Mission Manager meldet terminale Resultate. Nach terminalem Fehler ist Fortsetzen desselben äußeren Auftrags nicht belegt. |
| Not-Aus und Lokalisierung | `src/safety_monitor/config/safety_monitor_params.yaml:15–34`; `src/safety_monitor/safety_monitor/safety_monitor_node.py:118–168`; `src/robot_navigation/robot_navigation/cmd_vel_mission_gate.py:781–849`; `src/mission_manager/mission_manager/mission_manager_node.py:917–986` | Software-E-Stop und Lokalisierungsverlust sind getrennte Quellen. Gate-Stopp, Kindziel-Cancel und terminaler Missionszustand sind unterschiedliche Wirkungen; ein automatisches Zurücksetzen ist nicht nachgewiesen. |

Die Einordnung nach Masterplan lautet: Quellverlust verlangt zunächst einen
Bewegungshalt; ein terminaler Kindzielabbruch ist nicht automatisch ein
Missionsabbruch. Auftragserhalt und Wiederaufnahme fehlen beim HWT-Latch als
getesteter Produktpfad. Dauerhafte Quell- und Konfigurationsfehler, Nutzerabbruch
und Not-Aus bleiben terminal bzw. manuell freizugeben.

`docs/INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md` ist ein älterer,
nicht umgesetzter Vorschlag. Seine zusätzlichen Health-Zustände und Supervisor-
Änderungen sind keine Bestandsbeobachtung und wurden nicht als implementiert
gezählt.

**HWT-Einzelursache vom 27.09.:** Im lokalen Bag
`~/.local/share/amadeus/tests/parity-real-20260927-vl53-recovery` wechselt
`/fusion/hwt601/status_json` bei `1790492567.5659919` von
`raw_sources_ready` zu `raw_driver_not_ready`; direkt davor ist um
`1790492567.5165083` noch `sources_ready=true`. Danach bleibt
`latched_fault=raw_driver_not_ready`. Das Bag enthält nur
`/fusion/hwt601/status_json`, `/fusion/hwt601/wheel_odom_raw`,
`/shadow/hwt601/imu/yaw_rate` und `/shadow/hwt601/status_json`; der rohe
`/shadow/hwt601/raw_status_json`-Topic fehlt. Der Originalwert der sechs
Rohstatusprüfungen ist daher **nicht vorhanden**. Keine Einzelursache
behaupten. LiDAR und VL53 blieben frisch; es gab kein Frontierziel und keinen
Portal-/Raumwechsel.

**Historische Nachweislücke abgeschlossen gekennzeichnet:** Weder dieses
Fahr-Bag noch die vorhandenen Logs enthalten das verletzte Rohstatusfeld mit
Originalwert. Auch die damalige vollständige `source`-Reihenfolge und die
Paket-SHAs des ausgeführten Install wurden nicht aufgezeichnet. Diese Werte
sind aus den vorhandenen Artefakten nicht rekonstruierbar; erneute Suche in
denselben Logs ersetzt keinen Messbeleg. Der neue Diagnosekandidat darf
ausschließlich einen **neuen** motorlosen Lauf erklären.

## 5. Erstes begrenztes Recoverypaket

**Zielbild:** Die Schutzkette stoppt; derselbe Explore-Auftrag bleibt erhalten;
ausschließlich die identifizierte Funktion wird begrenzt wiederhergestellt;
HWT-/Encoder-/VL53-/Scanquellen, TF/Pose und aktueller freier Pfad werden neu
bewertet; genau das ursprüngliche Goal wird fortgesetzt. Höchstens ein aktives
Nav2-Kind. Keine alte `cmd_vel`-Nachricht, kein altes Goal und kein frischer
EKF-Stempel allein dürfen eine Wiederanfahrt autorisieren.

**Komponenten und Grenze:**

1. Zuerst in `robot_state_estimation` den HWT-Rohstatus so beobachtbar machen,
   dass jedes bestehende Prädikat mit Originalfeldwert, Quellalter und Zeit
   markiert wird. Keine Grenzwerte lockern. Den Befund mit den sechs
   Bedingungen und dem latching `Hwt601FusionHealth` korrelieren.
2. Erst nach bestätigter transienter Ursache die konkrete vorhandene
   HWT-Funktion begrenzt wiederherstellen. Derzeit ist nicht entschieden, ob
   Datenlesen, Serialtransport, Treiberbereitschaft oder Konfiguration die
   Ursache war; Reopen-/Restart-Mechanismus bleibt offen.
3. In der bestehenden Kette `mission_manager` / BT / `explore` den Auftrag
   während eines recoverbaren Halts erhalten, `cmd_vel_mission_gate`
   geschlossen halten und nach terminalem Cancel des einzigen Nav2-Kindes
   aktuelle Quellen, Pose, Kartenbindung, Pfad und Goal-ID prüfen. Kein neuer
   Supervisor und keine neue Navigation.

**Erfolgskriterien:** Ein gerätefreier Einzelfehler der später bestätigten
transienten Bedingung stoppt unmittelbar; der Auftrag bleibt identisch; nur
die betroffene Funktion wird begrenzt wiederhergestellt; frische gültige
Eingänge erfüllen bestehende Quellverträge; TF/Pose, Kartenbindung und Pfad
stimmen; das vorige Goal ist terminal; genau dasselbe Goal wird einmal
fortgesetzt; verspätete oder widersprüchliche Daten und Befehle bleiben
gesperrt.

**Gegenfälle:** Rohdaten dauerhaft nicht bereit, falscher Port oder
Schreibmodus, wiederholter HWT-/Encoderfehler, stale oder widersprüchliche
Quellen, Bias-/Kalibrierfehler, Sensor-/TF-Ausfall, blockierter Pfad,
fehlendes/stales Goal, zweites aktives Nav2-Kind, Nutzerabbruch, expliziter
E-Stop und kritischer Aktuatorfehler. Sie bleiben gesperrt und eskalieren in
terminalen Hilfebedarf oder manuellen Reset; keine automatische Wiederanfahrt.

**Rückfall:** HWT-Wiederherstellung und Missionserhalt einzeln revertieren.
Das bestehende Mission Gate bleibt fail-closed; `enable_auto_explore` oder
`active_drive` bleiben aus. Keine Erhöhung von Frische-/Kollisionsgrenzen.
Vor physischer Fortsetzung ist eine neue ausdrückliche Freigabe nötig.

Das Paket ist hinsichtlich Komponenten und Gegenfällen abgegrenzt; seine
Wiederherstellungsfunktion ist **OFFEN**, bis für den neuen Kandidaten
Originalfeld und tatsächlich recoverbare Ursache belegt sind. TOR 2 wurde
in diesem Auftrag nicht umgesetzt oder freigegeben.

## 6. Erhaltene Nachweise und Roadmapgrenzen

| Umfang | Stand |
|---|---|
| Bisherige „Stufe 1“ | Historisch GRÜN für die dort bezeichnete Basis; erhalten |
| Bisherige „Stufe 2“ | Historisch gerätefrei GRÜN; keine Abnahme der späteren Runtime |
| HWT-/Encoder-Preflight vom 26.09. | Zwei bestandene motorlose Zyklen im Vorgängerstatus berichtet |
| Begrenzter Bewegungstest | `complete` und 0,270 m aus `/odom` berichtet; kein unabhängiger metrischer Gesamtfahrnachweis |
| Rundblick 27.09. | 361,7° und korrektes Missions-/BT-/Gate-Startverhalten berichtet; kein Frontierziel erreicht |
| VL53-Recovery | Im Kandidaten softwaregeprüft; im Realtest nicht ausgelöst, da keine neue VL53-Störung auftrat |
| Aktuelle HWT-Störung | Sammelursache und Latch-Zeitpunkt belegt; verletztes Rohstatusfeld fehlt im Bag |
| Raumwechsel, Hindernisbewältigung und Missionsfortsetzung | Auf konsolidiertem Gesamtkandidaten nicht vollständig real nachgewiesen |
| WE-M4 / WE-M5 / WE-M6 | Reale Abnahmen weiter offen; vorhandene Bausteine nicht neu entwickeln |

„Stufe 1/2/3“ sind bisherige Arbeitsbezeichnungen. Die Roadmap bleibt WE-D0
und WE-M0 bis WE-M7; keine neue Meilensteinfolge.

## 7. Nächster Schritt und Historie

Genau ein nächster Nachweis: den in `AGENTENAUFTRAG.md` beschriebenen,
zeitlich begrenzten **motorlosen HWT-Erfassungslauf** mit dem eindeutig
gesourcten Diagnosekandidaten nach aktueller Vor-Ort-Freigabe ausführen.
Roh-IMU, korrigierte Drehrate, Rohstatus, Biasstatus und Wächterstatus zusammen
aufzeichnen. Tritt kein Fehler auf, Dauer und Lastbedingungen mit Ergebnis
„nicht reproduziert“ festhalten und nicht unbegrenzt wiederholen. Erst nach
Auswertung wird TOR 2 ursachenspezifisch entschieden; keine Fahrfreigabe.

Der vollständige Vorgängerstatus ist byteidentisch unter
[STATUS-Snapshot bei 40b5b49](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_40b5b49.md)
erhalten (Git-Blob `6d4092f11880f19f2f0052be940910ced526bb15`, 145845 Bytes).
Der ältere [M3/U-Snapshot](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md)
bleibt ebenfalls erhalten. Historische Aufträge sind keine aktuellen
Freigaben. Der Masterplan ändert sich nur mit expliziter Grundentscheidung.
