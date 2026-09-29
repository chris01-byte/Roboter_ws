# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus · Stand 29.09.2026 · Stufe 3 weiterhin OFFEN/GELB**

**Aktuelle Entscheidung:** Konsolidierung statt Komplettneubau. Maßgeblich sind
[MASTERPLAN.md v1.1](MASTERPLAN.md), die unveränderte
[WE-Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) und
[MEILENSTEINE.md](MEILENSTEINE.md). Dies ist der einzige laufende WE-Iststand.

## 1. Sofortiger Arbeitsfokus

**Entscheidung vom 29.09.2026, Basis PR #105 / `5c6ff0e`:**
Masterplan Schritt 2 ist für den ersten HWT-Wiederaufnahmefall abgeschlossen:
gerätefreier aktiver Nav2-Kind-Recoveryvertrag bestanden; realer HWT-Halt,
Recovery und Fortsetzung desselben Initialscans bestanden. Die reale
HWT-Injektion bei aktivem Nav2-Kind bleibt ein späterer Robustheitsnachweis,
ist kein aktuelles Gate und kein fehlgeschlagener Produktnachweis.

Aktueller Auftrag ist **Schritt 3: konsolidierten Kern real abnehmen**.
Eine durchgängige beobachtete Folge A (autonomes Ziel und reale Navigation),
B (Hindernis/Befreiung bei erhaltener Mission), C (vollständiger Portalübergang
und Weitererkundung) wird geprüft. Das ist eine erste Kernabnahme, kein
Wiederholungs- oder Zuverlässigkeitsnachweis. Noch kein Stufe-3-Gesamtgrün.
Details und laufender Ergebnisstand in Abschnitt 7.

Die früheren HWT-Sonderlimits 0,45/1,50 m Zielroute, 0,60 m Translation,
Vorwärtskegel, enger erzwungener Testkorridor und HWT-Leserpause sind für diesen
Auftrag aufgehoben. Produktive Footprint-, Costmap-, Kollisions-, VL53-,
Frische-, Pose-/TF- und Geschwindigkeitsgrenzen bleiben unverändert.
Kein Merge, kein dauerhafter Installwechsel, keine vorsorgliche Produktänderung.

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
| Motorlose Erfassung | **B – vollständiges Fenster, unter diesen Bedingungen nicht reproduziert.** Der einmalig neu freigegebene Lauf auf `c4295fc…` erfasste nach Bias-Readiness 120 s mit allen sieben Themen und ohne `first_fault` oder Latch. Der erste Lauf auf `fc6ac5e…` bleibt als 23,9-s-Teilmessung erhalten. Der alte Fahrabbruch ist dadurch nicht erklärt; Einzelheiten unten. |

Das Manifestwerkzeug `tools/kartierung/hwt_diagnose_manifest.py` schreibt erst
bei ausdrücklich übergebenem lokalem Ausgabepfad eine neue JSON-Datei außerhalb
des Repositories. Es startet keine Geräte oder ROS-Prozesse. Für eine spätere
Messung werden die tatsächlich gesourcten Setup-Dateien, das Profil mit SHA256,
Launchargumente, `AMENT_PREFIX_PATH`, Paketpräfixe und installierte Modul- und
Executable-Hashes **vor Ort erneut** erfasst. Der `/tmp`-Probeausdruck ist
kein Nachweis eines Roboterstarts.

### Motorloser HWT-Lauf vom 27.09.2026: begrenzter Teilnachweis

Die anwesende Person bestätigte für **diesen** Lauf die unabhängige
Motorsperre, Stillstand und Freigabe eines motorlosen Geräte-/Sensorlaufs.
Vor dem Start waren HWT-/Motorport frei und kein zweiter Stack aktiv. Das
Messfenster war vorab auf höchstens **120 s nach HWT-Bias-Readiness** gesetzt.
Eine erste Launchprobe endete vor Sensorstart wegen des fehlenden externen
Pakets `ldlidar_stl_ros2`; ihr Bag enthält null Nachrichten. Der anschließend
gestartete, unveränderte Diagnosekandidat nutzte in dieser Reihenfolge
`/opt/ros/humble`, das bekannte LiDAR-Overlay
`we1-ldlidar-shutdown-overlay/install`, `/tmp/we1-full-shim-install` und
`/tmp/we1-hwt-f1f6b74-install`. Quell-HEAD war `fc6ac5e56f78898666d7c9e8b3785bdab74ab0f2`
(sauber); das Parity-Profil hatte SHA256 `6097dae5aaee6bb6964d78b474f13768e70af298915fd986920c20a6cf2e3506`.
Das Manifest enthält die effektiv aufgelösten Paketpräfixe, installierten
Modul-/Executable-Hashes, Treiberversionen und alle Launchargumente.
Der Start erfolgte mit `active_drive=false`, `use_hwt601_odometry=true`,
`operator_stationary_confirmed=true`, `enable_auto_explore=false`,
`enable_stage3_motion_diagnostic=false`, `start_web_gui=false`, `normalize_scan=true`
und `crop=true`, ROS-Domain 217 über eine reine Loopback-DDS-Konfiguration.
Keine Mission wurde gesendet. Es lief nur der lesende
`encoder_shadow_reader` am Motorbus, kein `base_hardware`-Antriebsknoten.

Der gestartete Stack lief vom Sensorstart um 13:09:54 UTC bis zum geordneten
SIGINT um etwa 13:12:40 UTC. Der Recorder speicherte jedoch nur
13:09:54,988–13:10:18,898 UTC, **23,91 s Roh-IMU**; dann endete er mit
`rosbag2_storage_plugins::SqliteException`, `SQLite error (5): database is locked`.
Die konkrete Ursache der Dateisperre ist nicht belegt. Das geschlossene Bag
ist lesbar, aber ohne Metadatendatei. Aufgezeichnet wurden 2328 Roh-IMU,
48 Rohstatus, 48 Bias-/Yawstatus, 469 Encoder-Odometrien, 470 Encoderstatus
und 392 Wächterstatus. Die korrigierte Drehrate hatte null Nachrichten.
Im erfassten Zeitraum war der Rohstatus stets `ready=true`,
`raw_data_ready=true`, `consecutive_errors=0`, `reconnects=0` und
`age_s=0,00017–0,00146 s`; der Encoderstatus war stets `ready=true`,
`read_only=true`, ohne Latch oder FC03-Paarfehler. Beide Statusquellen meldeten
`actuator_output=false` und keine Sensor-Schreibbefehle; die gemessenen
Radgeschwindigkeiten waren 0 RPM. Der letzte Biasstatus hatte 883 Samples,
`calibrated=false`, `stable=false`, Grund `gyro_bias_warmup`; der Wächter
meldete durchgehend `yaw_missing_stale_or_invalid`, `sources_ready=false`,
`latched_fault=null`, `first_fault=null`. Diese Zustände während der
Startkalibrierung sind **kein** nachgewiesener HWT-Fehler nach Readiness.
Messalter, Status-Empfangsalter und `age_s` eines Erstfehlers sind mangels
Erstfehler nicht verfügbar. Eine spätere natürliche Erholung oder Störung
innerhalb der nicht aufgezeichneten Zeit ist nicht beurteilbar.

Die lokalen, nicht ins Repository übernommenen Belege liegen unter
`~/.local/share/amadeus/tests/hwt-tor1-20260927-M97XodUP/`:
`runtime-manifest-v2.json`, `runtime-addendum.json`, `run-conditions.json`,
`capture-analysis.json`, `hwt-bag-v2/`, `recorder-v2.log` und `launch-v2.log`.
Alle Launch-Kinder endeten nach SIGINT sauber. Kein aktiver Install wurde
gewechselt. Der historische HWT-Rohwert des alten Fahr-Bags bleibt offen;
TOR 2 und jede Fahrfreigabe bleiben aus.

**Recorder-Reparatur im Labor:** Eine unveränderte Kopie der abgestürzten
SQLite-Datei wurde unter `recovered-copy/` mit `ros2 bag reindex` um Metadaten
ergänzt; `ros2 bag info` bestätigt 3755 Nachrichten über 23,91 s. Dies fügt
keine späteren Messwerte hinzu. Das neue Werkzeug
`tools/kartierung/hwt_diagnose_record.py` startet nur einen Recorder und
beobachtet Bias-Readiness über ROS-Status, ohne die laufende SQLite-Datei zu
öffnen. Es verwendet das installierte rosbag2-SQLite-Profil `resilient`
(WAL-Journal statt des optimierten MEMORY-Journals), begrenzt Vorlaufzeit
und Fenster nach Readiness, signalisiert nur den eigenen Recorderprozess mit
SIGINT und prüft Metadaten, die Liste
aller sieben Themen, Statuszähler sowie `ros2 bag info` erst nach dessen Ende.
Ein gerätefreier Probelauf auf ROS-Domain 219 mit sieben künstlichen Publishern
lieferte 31–32
Nachrichten je Thema, Recorder-Exit 0 und Ergebnis `complete` nach einem
3-s-Fenster. Ohne Publisher auf Domain 220 endete ein 2-s-Vorlauf mit Ergebnis
`incomplete` und Exit 2. Ein weiterer gerätefreier Lauf auf Domain 221 hielt
parallel eine SQLite-Lesetransaktion 2 s offen; der WAL-Recorder endete nach
4 s mit Exit 0 und 41 Nachrichten je Thema. Das abgeschlossene Bag meldet
`journal_mode=wal`. Ein vierter Laborlauf auf Domain 222 hielt die korrigierte
Gierrate bei 0 Nachrichten und beendete dennoch die vollständige
Aufzeichnung: Ein fehlender Messwert wird nicht als Recorderabbruch verdeckt.
Belege: `/tmp/hwt-recorder-preflight-20260927-1*`,
`/tmp/hwt-recorder-preflight-20260927-timeout*` und
`/tmp/hwt-recorder-preflight-20260927-wal*` sowie
`/tmp/hwt-recorder-preflight-20260927-zero-yaw*`. Diese Laborprüfung
belegte zunächst nur den Aufzeichnungspfad. Die konkrete
Ursache der vorherigen SQLite-Sperre bleibt unbewiesen; während eines neuen
Laufs darf kein anderer Prozess die Bag-Datenbank öffnen.

### Vollständiger motorloser HWT-Lauf vom 27.09.2026: Ergebnis B

Die anwesende Person bestätigte für **genau diesen Lauf** unabhängige
Motorsperre, Stillstand und den motorlosen Geräte-/Sensorzugriff. Vor dem
Start waren HWT-/Motorport frei; es lief kein zweiter Stack. Auf sauberem
Quellstand `c4295fcdacf817b33b53f17e38ac106bf01ae9e2` (PR #104,
Recorderwerkzeug) wurden unverändert die Diagnosepakete aus
`/tmp/we1-hwt-f1f6b74-install` über dem Vollbuild
`/tmp/we1-full-shim-install`, dem bekannten LiDAR-Overlay und ROS Humble
verwendet. Das Profil `hwt601_parity_params.yaml` hatte SHA256
`6097dae5aaee6bb6964d78b474f13768e70af298915fd986920c20a6cf2e3506`.
`runtime-manifest.json` enthält die tatsächliche Setup-Reihenfolge,
Paketpräfixe, installierten Modul-/Executable-Hashes, Versionen und
Launchargumente; der externe LiDAR-Executable-Hash steht in
`run-conditions.json`. ROS lief auf der lokalen Loopback-Domain 217.
Launchargumente: `active_drive=false`, `use_hwt601_odometry=true`,
`operator_stationary_confirmed=true`, `enable_auto_explore=false`,
`enable_stage3_motion_diagnostic=false`, `start_web_gui=false`,
`normalize_scan=true`, `crop=true` und das genannte Parity-Overlay.
Keine Mission wurde gesendet. Nur `encoder_shadow_reader` besaß den Motorbus,
kein `base_hardware`-Antriebsknoten. Keine Parameteränderung oder Recovery.

Der reparierte Recorder startete **vor** dem Stack um 14:23:24 UTC.
HWT-Bias-Readiness wurde um 14:24:09,788 UTC erkannt; das vorab auf höchstens
120 s begrenzte Fenster endete um 14:26:09,789 UTC. Der Recorder beendete
mit Exit 0, Metadaten und `ros2 bag info`; das gesamte Bag enthält
35 555 Nachrichten über 145,502 s einschließlich Vorlauf. Themenzähler:
14 375 Roh-IMU, 11 965 korrigierte Drehraten, 290 Rohstatus,
292 Bias-/Yawstatus, 2 905 Encoder-Odometrien, 2 906 Encoderstatus und
2 822 Wächterstatus. Nach Readiness waren 240/240 Rohstatus `ready=true`
und `raw_data_ready=true` mit `age_s=0,00023–0,00661 s`,
`consecutive_errors=0` und `reconnects=0`. 241/241 Yawstatus waren bereit;
der letzte Biasstatus war `calibrated=true`, `stable=true`, 999 Samples.
Der Encoder war stets `read_only=true`, ohne FC03-Paarfehler oder Latch;
beide Radgeschwindigkeiten blieben 0 RPM. Alle 2 400 Wächterstatus im
Messfenster hatten `sources_ready=true`, `first_fault=null`,
`latched_fault=null`, `active_drive=false` und den Grund
`readonly_preflight_no_motion`. Kein HWT-Erstfehler oder späterer
Erholungswechsel wurde beobachtet. Statusquellen meldeten keine Aktorausgabe
oder Sensor-Schreibbefehle. Nach dem Recorder wurde der Stack per einmaligem
SIGINT beendet; alle Kinder endeten sauber und beide seriellen Ports sind frei.

**B – vollständiges Fenster ohne Fehler: unter diesen Bedingungen nicht
reproduziert.** Der Befund gilt für den motorlosen Stillstand mit diesem
Kandidaten und dieser Last. Er bestimmt weder rückwirkend das verletzte
Rohstatusfeld des alten Fahr-Bags noch belegt er Recoverbarkeit. Für einen
nicht aufgetretenen Erstfehler gibt es keinen Originalwert, Grenzwert oder
Erstfehler-Zeitfolge aus diesem Lauf. TOR 2 und Fahrfreigabe bleiben aus.
Lokale Belege (keine Bags im Repository):
`~/.local/share/amadeus/tests/hwt-tor1-20260927-run-nDR2Re/` mit Manifest,
`run-conditions.json`, `hwt-bag/`, `hwt-bag-summary.json`,
`capture-analysis.json`, Recorder- und Launchlogs. Das Bag hat SHA256
`d15868030208421599626477ce473fa27f23ec130949f52cb117c1242b09aee9`.

### Offline-Vergleich: Fahrabbruch gegen stabiles Stillstandsfenster

**🟡 OFFLINE-VERGLEICH ABGESCHLOSSEN – MIT VORHANDENEN DATEN NICHT
ENTSCHEIDBAR.** Nur das alte lokale Fahr-Bag
`parity-real-20260927-vl53-recovery`, sein ROS-Launchlog vom 27.09. um
08:57:59 Ortszeit, vorhandene HWT-/Gate-Knotenlogs, der Parity-Bericht und
das neue lokale Bag samt Manifest wurden gelesen. Keine ROS-Runtime und
keine Geräte wurden gestartet.

**Engste alte Zeitfolge:** Der fusionierte Wächter meldete um
`1790492567.5165083` noch `raw_sources_ready`, `sources_ready=true`,
`hwt_motion_ready=true`. Um `1790492567.5659919` wechselte er auf
`raw_driver_not_ready`, `sources_ready=false` und den gleichnamigen Latch.
Das Mission Gate protokollierte `blocked` um `1790492567.5672408`; `/cmd_vel`
war spätestens um `1790492567.5942700` null. Die korrigierte Gierrate lag
im Bag unmittelbar vor/nach dem Latch bei `1790492567.565142` und
`1790492567.572654` mit etwa `0,0623 rad/s`; in den nächsten fünf Sekunden
folgten 500 weitere Nachrichten ohne Lücke über 0,019 s. Der letzte
Yawstatus vor dem Latch traf um `1790492567.540613` ein, meldete
`ready=true`, kalibrierten stabilen Bias und **internes** `age_s=0,000838 s`.
Sein Bag-Empfang lag 0,025379 s vor dem Latch; der nächste Yawstatus um
`1790492568.035000` war ebenfalls bereit. Bag-Empfangsabstand, internes
`age_s` und Guard-Empfangszeit sind verschiedene Größen. Die Header-Zeiten
der korrigierten Gierrate waren `1790492567.560314` und
`1790492567.570187`; aus Bag- und Header-Zeit allein folgt kein exaktes
HWT-Rohmessalter im Wächter.

Unmittelbar vor dem Latch meldete `base_hardware/state_json` um
`1790492567.558667` frisches Encoderfeedback
(`encoder_feedback_age_s=0,046478 s`, `encoder_feedback_ok=true`,
`encoder_stale=false`, keine Modbus-Lesefehler) und je `-24 RPM` gemessene
Motordrehzahl. Nach dem Latch lag um `1790492567.585372` weiterhin
Encoderfeedback vor, nun `-15 RPM`. Mission Manager und Explorer waren in
`Explore`/`initial_scan`. LiDAR und VL53 liefen laut Bag und vorhandenem
Bericht weiter. Das alte Bag hat **keinen**
`/shadow/hwt601/raw_status_json`-Topic; Rohstatus-Empfangszeit,
`consecutive_errors`, `reconnects` und internes `age_s` am ersten Fehler
sind historisch nicht vorhanden. Das HWT-Knotenlog enthält Verbindung und
Start, keinen Rohstatuswert zum Übergang. Im dokumentierten
`Hwt601FusionHealth`-Prüfpfad folgt `raw_driver_not_ready` erst nach den
Sample-/Statusfrischeprüfungen und umfasst sechs Rohstatusprädikate; die
exakte installierte Modul-SHA des alten Prozesses wurde nicht erfasst.

**Neuer Vergleichsausschnitt:** Um die Mitte des stabilen Fensters
(`1790519109.788339`) war der letzte aufgezeichnete Rohstatus 0,381508 s
alt, mit eigenem `age_s=0,005302 s`, `ready=true`,
`raw_data_ready=true`, `consecutive_errors=0`, `reconnects=0`; der nächste
Rohstatus folgte 0,117938 s später. Yawstatus war bereit mit eigenem
`age_s=0,004908 s`, Encoderfeedback `0,007348 s` alt, Wächter
`sources_ready=true`, `first_fault=null`, `latched_fault=null`.
Im ganzen 120-s-Fenster waren 2 400/2 400 Wächterstatus quellenbereit.
Der neue Lauf hatte `active_drive=false`, keinen Explore-Auftrag und 0 RPM.

| Unterschied | Bewertung aus den vorhandenen Daten |
|---|---|
| Aktiver `base_hardware`-Antrieb und tatsächliche Drehung alt; nur `encoder_shadow_reader`, gesperrte Motoren/0 RPM neu | **Möglich, aber unbelegt** als Bedingung des Rohstatusfehlers. Schon in den 60 s vor dem Latch zeigten 2 763 von 2 997 Basisstatusmeldungen Bewegung, während der Wächter zuvor bereit blieb. Bewegung allein ist kein deterministischer Auslöser. |
| Explore-/BT-Auftrag und Initialscan alt; kein Auftrag neu | **Möglich, aber unbelegt.** Alt war `active_command.type=explore`, Nav2/Controller liefen; neu waren Nav2/Controller ebenfalls gestartet, aber keine Mission wurde gesendet. Ein Zusammenhang mit einem der sechs Rohstatusprädikate ist nicht aufgezeichnet. |
| Längerer Betrieb bis zum Fehler und andere Paket-/Overlayauflösung | **Nicht bewertbar** als Ursache. Alt lag der Latch etwa 288 s nach Launch, neu endete das Messfenster etwa 149 s nach Launch. Alt ist `install_parity_real` nur teilweise dokumentiert; die ausgeführten HWT-Paket-SHAs und vollständige Präfixreihenfolge fehlen. Neu sind sie im Manifest erfasst. |
| HWT, Encoder, LiDAR, VL53, SLAM und Nav2 als gestartete Komponenten | Ein unterschiedlicher gestarteter **Sensorsatz ist durch Daten ausgeschlossen**: beide Launchlogs enthalten HWT, LiDAR und VL53. Alt starteten 25, neu 28 Prozesse; die zusätzliche neue Karten-/Semantik-/Rosbridge-Gruppe und fehlende Mission machen Prozesszahlen zu keinem CPU-/I/O-Lastmaß. CPU-, Speicher- und Buslast um den alten Latch sind **nicht bewertbar**. |
| Längerer Ausfall der korrigierten Gierrate, Yaw-Bias oder Encoderfeedback als unmittelbare Erklärung | **Durch Daten ausgeschlossen** für den beobachteten Übergang: Gierrate publizierte ohne relevante Lücke weiter, Yawstatus blieb bereit und Encoderfeedback frisch. Ein kurzer Fehler in einem anderen Rohstatusprädikat ist dadurch nicht ausgeschlossen. |

**Entscheidung:** Keine der belegten Betriebsdifferenzen bestimmt, welches
der sechs Rohstatusprädikate zuerst scheiterte. Aktiver Motorbetrieb,
Missionslast, längere Laufzeit und nicht vollständig belegte alte Runtime
lassen sich aus einem einzigen Fehlerereignis nicht gegeneinander priorisieren.
Die **eine fehlende Information** ist der vollständige HWT-Rohstatus-Snapshot
zum ersten alten Latch, einschließlich Originalfeldwerten und Empfangszeit.
Er ist aus den vorhandenen Artefakten nicht rekonstruierbar. Daher wird
**keine einzelne Auslösebedingung priorisiert** und TOR 2 nicht begonnen.

## 4. Abort-, Stop- und Latch-Inventur des Bewegungspfads

Die folgende Inventur hält den konsolidierten **Vorgängerstand vor dem
Recovery-Branch** und den alten Fahrprozess fest. Nur die HWT-Zeilen werden
durch den gerätefreien Implementierungsstand in Abschnitt 5 ergänzt; reale
Schutzwirkung und aktiver Install sind damit nicht umgestellt.

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
Missionsabbruch. Auftragserhalt und Wiederaufnahme fehlten beim HWT-Latch im
Vorgängerstand. Dauerhafte Quell- und Konfigurationsfehler, Nutzerabbruch
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

**Gerätefreier Ergebnisstand:** Auf Branch `feature/hwt-hold-recovery-resume`
wird ein ausdrücklich synthetischer transienter HWT-Fall in der bestehenden
Kette behandelt. Die alte reale Ursache ist weiterhin **unbekannt**. Es gab
keinen Gerätezugriff, keinen Roboterprozess, keinen Installwechsel und keine
Fahrt. Die unveränderten Bewegungsfristen sind Rohmessung 0,20 s,
korrigierte Gierrate 0,35 s, Encoder 0,30 s im Fahrprofil und 0,18 s im
Lesemodus sowie 1,0 s Statusherz. VL53-, TF- und Kollisionsgrenzen wurden
nicht gelockert.

**Klassifikation:** `Hwt601FusionHealth` behandelt eine einzelne fehlende
oder kurz stale Roh- beziehungsweise Yaw-Messung sowie
`raw_data_ready=false`/`ready=false` im weiterhin verbundenen Zustand
`degradiert` und ein bis zwei Lesefehler ohne Reconnect als transient.
Gleicher Port, unveränderter Reconnectzähler, deaktivierte Sensor-Schreibbefehle,
endliche konsistente Zeitwerte und gültiger Bias/Encoder bleiben nötig.
Falscher Port, Schreibmodus, Disconnect/Reconnect, drei Lesefehler,
ungültige Kalibrierung, Encoder-/Konfigurationsfehler, widersprüchliche oder
nicht endliche Werte und unbekannte Statuslage sind Hard Faults. Ein Fehler
nach erster Readiness behält seinen unveränderlichen `first_fault`-Snapshot;
HOLD-/Recovery-Ereignisse werden zusätzlich protokolliert. Ein Hard Fault
bleibt gelatcht.

**HOLD und Resume:** `motion_failure` bleibt während `HOLD` und
`RECOVERY_VALIDATION` ungleich `None`; das bestehende
`cmd_vel_mission_gate` sendet Null und hält eine eigene Resume-Sperre. Der
Explore-Action- und Mission-Manager-Auftrag bleiben aktiv. Ein laufendes
Nav2-Kind wird über den vorhandenen Client gecancelt; nur ein bestätigter
terminaler Kindzustand lässt die Kindziel-Session frei. Ein nicht bestätigter
Cancel endet im terminalen Hilfebedarf. Nach HWT-Heilung verlangt die
Quellwache mindestens 1,0 s durchgehend gültige Werte, 20 neue
Rohmessungen und zwei neue Rohstatusmeldungen. Der gesamte HWT-Recoveryversuch
ist auf 5,0 s ab Erstfehler begrenzt. Diese Werte leiten sich aus 100 Hz
Rohdaten, 2 Hz Rohstatus, 1 s Statusherz und der bestehenden 3-s-Nav2-Cancelfrist
ab; eine einzelne gute Meldung reicht nicht. Wiederholter Fehler setzt das
Zeitbudget nicht zurück. Zusätzlich sind höchstens zwei transiente HOLDs pro
Health-Lauf erlaubt; beim dritten wird wie beim dritten aufeinanderfolgenden
Treiber-Lesefehler ein terminaler Hilfebedarf gesetzt, statt endlos zu
stoppen und wieder anzufahren.

Erst nach terminalem Kind und erneuter Prüfung von Not-Aus, HWT/Encoder,
VL53, LiDAR, aktueller TF/Pose, Kartenquelle und unprojiziert erreichbarem
Weg signalisiert der Explorer `we_hwt_resumed`. Das Gate verlangt die neue
HOLD→RESUME-Folge und einen **nach** dieser Freigabe empfangenen Befehl.
Der Explorer wartet auf die passende `resume_sequence`-Bestätigung des
Gates, bevor er ein neues Kindziel versendet.
Der vorherige Nav2-Goal-Handle wird nicht wiederverwendet; eine neue
Kindziel-Session plant denselben noch offenen Task vom aktuellen Zustand.
Ein anderer Task, stale Quelle, fehlender Pfad oder zweites Kind autorisiert
keine Wiederanfahrt. Not-Aus und Nutzerabbruch setzen sich nicht selbst
zurück; dauerhafter Fehler endet stehend im terminalen Hilfebedarf mit
erhaltenem Auftrag/Teilstand.

**Nachweise:** Frischer isolierter Build von `robot_state_estimation`,
`robot_navigation`, `explore` und `mission_manager` unter
`/tmp/we1-hwt-recovery-install` über dem gesicherten
`/tmp/we1-full-shim-install`; Paketpräfixe der vier neuen Pakete zeigen auf
das Recovery-Overlay, BT, Motor und VL53 auf das Underlay.
`colcon test-result` meldet für HWT, Gate und Explorer 1 124 Tests ohne
Fehler/Fehlschlag; die vom Mission-Manager-Paketsetup nicht registrierten
47 direkten `pytest`-Tests bestanden separat. Synthetisch geprüft sind Rohdatenlücke, degradiertes
`raw_data_ready`, kurzer Lesefehler, bleibender/wiederholter Fehler,
Port-/Schreibmodus-/Reconnect-/Zeit-/Bias-Hard-Fault, Gate-Halt und
Resume-Handschlag einschließlich Gate-Bestätigung, bestätigter/fehlgeschlagener Kindziel-Cancel,
Ein-Kind-Semantik, Nutzerabbruch, Not-Aus sowie Sperre bei ungültigem
TF-/Karten-/Pfadbeleg. Diese Tests belegen die Softwareverträge, keine
physische Haltstrecke, reale Transienzrate oder Fahrtauglichkeit.

Auf Stand `f426a12` waren die vier installierten Hauptmodule bytegleich mit
den Quellen: SHA256 `0336686e…` (`hwt601_fusion_health.py`), `f964f170…`
(`cmd_vel_mission_gate.py`), `b668a0c0…` (`explore_node.py`) und
`9e12a6a0…` (`mission_manager_node.py`). Der nachfolgende isolierte Neubuild
in diesem Abschnitt hat für den geänderten Explorer-Code `11c63dc3…` und
für das neue installierte Profil `ee3b42ee…` ergeben, jeweils bytegleich zur
Quelle. ROS-Paketauflösung wurde im temporären Overlay geprüft; diese Pfade
sind **kein aktiver Roboter-Install**.

### Produktpfad und zusätzliche Absicherung auf PR #105

Das bisherige `hwt601_parity_params.yaml` bleibt mit
`wohnungserkundung_navigation_enabled=false` unverändert. Damit erreicht es
die neue Recovery im WE-Loop **nicht**. Für die Abnahme existiert das explizite
`hwt601_recovery_acceptance_params.yaml`; es übernimmt die Parity-Werte und
setzt ausschließlich dieses WE-Navigations-Opt-in auf `true`. Der bisherige
pauschale Startabbruch bei aktivem WE-Zweig wurde entfernt; alle bestehenden
Voraussetzungen für Schatten, Rohkarte, Frontierfeed, Policy und Safety
bleiben aktiv. Ein Start ohne explizit gewähltes Abnahmeprofil bleibt auf dem
Legacy-/Parity-Pfad.

Vorgesehener Startvertrag ist `robot_bringup/app_mapping.launch.py` mit
`use_hwt601_odometry=true`, `enable_auto_explore=true`,
`explore_params_overlay` auf dem **installierten** Abnahmeprofil und dem
gesondert freizugebenden `active_drive`. `app_mapping` bindet
`robot_navigation/nav_mapping.launch.py` ein; dieser startet den einzigen
Explorer, das `cmd_vel_mission_gate`, `bt_orchestrator` und `mission_manager`.
Ein `explore`-Kommando läuft als `RunMission` über den echten BT-Baum
`explore.xml` zur `/explore_area`-Action. `ExploreNode._execute_reserved`
verzweigt bei diesem Profil in `_execute_wohnungserkundung_navigation`;
dort führen `_wohnungserkundung_hwt_hold` und
`_wohnungserkundung_wait_for_hwt_resume` HOLD, Auftragserhalt, Neuprüfung und
Resume aus. Initialscan und aktives Nav2-Kind sind getrennte Fälle.

Vor `we_hwt_resumed` verlangt der WE-Loop jetzt **tatsächlichen Stillstand**
aus frischer Encoder-Odometrie: Betrag der linearen Geschwindigkeit höchstens
`door_stop_linear_tolerance_mps=0,01`, Betrag der Drehrate höchstens
`scan_stop_angular_tolerance_radps=0,02`, mindestens 0,5 s stabil und eine
neuere Odometrieprobe innerhalb dieses Fensters. Die vorhandene
`scan_odom_timeout_s=0,8` bleibt maßgeblich. Bei Bewegung oder veralteter
Rückmeldung bleibt das Gate im HOLD; fällt eine bereits signalisierte
Validierung erneut zurück, schließt das Gate wieder und fordert eine neue
Resume-Nachricht plus frischen Befehl. Nullkommando und terminales Kind allein
reichen nicht. Die Route verlangt zusätzlich einen frischen TF-Pose-Stempel
innerhalb der bereits vorhandenen `door_localization_timeout_s=0,8` und eine
aktuelle, unprojizierte Costmap-Verbindung. Der neu gebaute Gate-Code ist mit
der Quelle bytegleich (SHA256 `58712ff5…`).

Isolierter Neubuild der vier Recovery-Pakete bestand; das neue Profil wurde
unter `/tmp/we1-hwt-recovery-install/share/explore/config/` installiert.
`colcon test-result`: **1127 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**;
`mission_manager` separat **47 pytest-Tests bestanden**. Der neue verbundene
Prozess-Test injiziert eine Rohdatenlücke während eines synthetischen
Kindziels, prüft Gate-Nullausgabe, erhaltene Auftrag-/Action-Identität,
terminales altes Kind, bewegte Odometrie als Resume-Sperre, stabile
Stillstandsfolge, aktuelle Task-/Karten-/Routenprüfung, Gate-Sequenzbestätigung,
neuen Befehl und genau ein neues Kind für denselben Task. Dies ist ein
verbundener Prozess-Test; der nachfolgende ROS-Graph-Test ist der maßgebliche
gerätefreie Integrationsnachweis. Separate Paket-Gegenfälle decken
Dauerfehler, verspäteten Cancel, falschen Port, Schreibmodus, ungültigen Bias,
Nutzerabbruch und ungültigen TF-/Pfadbeleg ab.

**Zusammenhängender ROS-Graph-Nachweis:**
`tools/sensorfusion/hwt_recovery_product_graph.py` lief in isolierter,
localhost-begrenzter ROS-Domain mit dem installierten Abnahmeprofil. Echte
Mission-Manager- und BT-Prozesse führten `explore` über `RunMission` und
`explore.xml` zur realen Explorer-Action. Explorer, HWT-Guard und Gate liefen
aus dem Recovery-Overlay; HWT-/Encoder-, VL53-, LiDAR-, TF- und Costmap-
Nachrichten sowie ein Nav2-Action-Server waren synthetische ROS-Gegenstellen.
Die WE-Karten-/Task-Policy erhielt einen Testadapter mit genau einem offenen
Task; dies ist **keine** reale Karten-, Frontier- oder Türabnahme.

Nach einer Rohmessungslücke jenseits der unveränderten 0,20-s-Grenze
beobachtete der Lauf `we_hwt_hold`, Gate-Nullausgabe und einen bestätigten
terminalen Cancel von Kind 1. Der Mission-Manager-Auftrag blieb `explore`.
Obwohl HWT wieder gesund war, blieb bei 0,03 m/s Encoder-Rückmeldung
`we_hwt_recovery_validation` aktiv. Nach stabiler Nullbewegung blieb die
synthetisch blockierte Costmap-Route zunächst gesperrt; erst mit frischem TF,
freien Costmap-Zellen und passenden Gate-ACK folgte `we_hwt_resumed` und ein
**neues** Kind 2 für denselben Task. Höchstens ein Kind war aktiv; alte
Bewegungsbefehle passierten vor dem neuen Ziel nicht. Nutzerabbruch cancelte
Kind 2 und beendete den Auftrag. Im getrennten Rundblickfall entstand kein
Nav2-Kind; HOLD und erneuter Eintritt in `we_initial_scan` wurden beobachtet.
Ein danach gesetzter synthetischer Not-Aus stoppte die Gate-Ausgabe und
beendete den Auftrag ohne automatischen Neustart. Der Rundblick wurde im
Test **nicht** zu 360° vollendet; verspätete Action-Antworten und der
dauerhafte HWT-Ausfall sind separat in Pakettests geprüft.

Der reproduzierbare Skriptlauf meldete `PASS` mit `max_active_children=1`,
`new_child_count=1`, `gate_ack_sequence=2` und
`scan_nav2_child_count=0`; Graph-, BT- und Manager-Logs sowie die
synthetischen Laufbedingungen und Dateihashes liegen lokal unter
`~/.local/share/amadeus/tests/hwt-recovery-product-graph-20260927-run-226/`.
Kein Motor- oder Hardware-Sensorprozess und
kein aktiver Roboter-Install wurde gestartet oder geändert. Physischer Halt,
reale Transienzrate und Fortsetzung auf echter Karte sind **nicht** belegt.

**Motorloser Zielsystemcheck am 27.09.2026 (PR #105, `91bc6bf`):**
Die anwesende Person bestätigte für diesen Lauf Stillstand, unabhängige
Motorsperre und motorlosen Sensorzugriff. Das auf dem Jetson mit
`hwt_diagnose_manifest.py` erfasste, saubere Quell-HEAD ist
`91bc6bf64e29110d72773d20ebcf6be77c333e72`; das installierte
`hwt601_recovery_acceptance_params.yaml` hat SHA256 `ee3b42ee…`. Der erste
Launch brach vor jedem Knoten ab, weil der isolierten Setup-Kette der externe
`ldlidar_stl_ros2`-Treiber fehlte. Der dokumentierte korrigierte Treiber aus
`we1-ldlidar-shutdown-overlay/install`, das bestehende
`amadeus_slam_toolbox_ws/install`, `/tmp/we1-full-shim-install` und das
Recovery-Overlay wurden daraufhin in dieser Reihenfolge gesourct; kein
Paket und kein aktiver Install wurden verändert. Das zweite Manifest belegt
die wirksame Präfixreihenfolge und das Motorlos-Profil
(`active_drive=false`, `enable_auto_explore=false`,
`use_hwt601_odometry=true`, `operator_stationary_confirmed=true`).

Im echten, motorlosen App-Mapping-Stack waren HWT-Roh- und korrigierte
IMU mit je etwa 100 Hz frisch, Bias kalibriert/stabil, Rohstatus bereit mit
`reconnects=0` und `consecutive_errors=0`, Encoder-Status bereit mit
0 m/s und 0 rad/s, Fusion `sources_ready=true` ohne `first_fault`.
LiDAR-Scan kam mit etwa 10 Hz; beide VL53-Frames meldeten Gesundheit,
ohne Hindernispunkte in diesem Stillstandsausschnitt. `map→odom` und
`odom→base_link` waren frisch, Not-Aus-Topic war frei. Das Gate publizierte
167 Nullkommandos auf `/cmd_vel_nav` in 6 s; Mission und Explorer blieben
`idle`. Die Scope-Felder des Profils blieben ausdrücklich
`accessible_scope_verified=false` und leer; daraus folgt keine
Frontier-Fahrfreigabe. Der Stack wurde per SIGINT an genau den
Launch-Prozess sauber beendet; die beiden seriellen Ports sind frei.
Manifeste, Logs und motorlose Beobachtungen liegen nur lokal unter
`~/.local/share/amadeus/tests/hwt-recovery-real-20260927-3wLELq/`.
Dieser motorlose Teilnachweis allein ist kein Recovery- oder Fahrnachweis.

**Einziger begrenzter Realversuch am 27.09.2026 (PR #105, Quell-HEAD
`25ac0481ad8c79ffcaa34d22ee4082fa5d39a45b`):** Für genau den
40-s-/3-rad-Rundblick bestätigte die anwesende Person freien Schwenkraum,
Beobachtung, erreichbaren unabhängigen Halt/Not-Aus, Stillstand und die
bewusst gelöste Motorsperre. Vor dem Stack startete ein Recorder für 26
Topics. Das Runtime-Manifest liegt lokal unter
`~/.local/share/amadeus/tests/hwt-recovery-real-20260927-3wLELq/runtime-manifest-drive-25ac048.json`;
es belegt das explizite installierte Profil
`/tmp/we1-hwt-recovery-install/share/explore/config/hwt601_recovery_acceptance_params.yaml`
(SHA256 `ee3b42eef682a830892e93f84093baf1547a84f76d6baa3e480a81dc1de393c4`)
und die Setup-Reihenfolge ROS Humble, `amadeus_slam_toolbox_ws`,
`we1-ldlidar-shutdown-overlay`, `we1-full-shim-install`,
`we1-hwt-recovery-install`. `active_drive=true`,
`enable_auto_explore=true`, `use_hwt601_odometry=true`; Scope-Verifikation
blieb falsch und die Scope-ID leer. `base_hardware` besaß allein den Motorbus,
der HWT-Leser allein seinen Port. Das Manifestwerkzeug trägt im Feld
`purpose` noch den älteren Text „motorless HWT first-fault diagnosis“;
maßgeblich für diesen Lauf sind seine expliziten `launch_arguments` und der
aufgezeichnete aktive Preflight. Der aktive Install wurde nicht gewechselt.

Nach gesundem motorlosen/aktiven Preflight ging genau ein Explore-Auftrag über
Mission Manager und BT in `we_initial_scan`. Der gemessene Encoderwert zeigte
vor der Störung etwa 0,0202 rad/s, kein lineares Kommando. Der HWT-Leser wurde
einmal von 1790536677,855 bis 1790536678,106 (0,251 s) pausiert und per
unabhängigem Watchdog gegen Hängenbleiben abgesichert. Das Bag zeigt eine
Roh-IMU-Publikationslücke von 0,261 s. Der **erste Fehler** um
1790536678,0736856 war `raw_missing_stale_or_invalid`: Alter der letzten
gültigen Rohmessung **0,220622 s > 0,20 s**. Rohstatus und sein eigenes
`age_s=0,000645 s` waren dagegen gültig; dessen Empfangsalter betrug
0,577996 s < 1,0 s, `reconnects=0`, `consecutive_errors=0`. Das ist nicht
der historische `raw_driver_not_ready`-Fall.

Das Gate setzte `/cmd_vel_nav` um 1790536678,0766 auf null, der Explorer
ging um 1790536678,0918 auf `we_hwt_hold`; der übergeordnete Explore-Auftrag
blieb dabei `running`/`HWT_HOLD`. Das nachgeschaltete `/cmd_vel` erreichte
nach Smoother-Abbremsung um 1790536678,1883 null. Der Rohleser lieferte ab
1790536678,1145 wieder Daten. **Danach scheiterte die Wiederaufnahme:** Der
Yaw-Schatten veröffentlichte zuletzt um 1790536677,8561 korrigierte Drehrate
und meldete um 1790536678,232 `ready=false`,
`latched_fault=imu_datenluecke_neustart_noetig`, `age_s=0,373865 s`.
Sein vorhandener Code verriegelt eine kalibrierte IMU nach einer
Samplelücke >0,10 s; die gemessene Roh-Lücke war 0,261 s. Gate/Fusion gingen
um 1790536678,2254 erneut auf HOLD und um 1790536678,2758 auf
`TERMINAL_FAULT: yaw_missing_stale_or_invalid`. Die erreichte
`RECOVERY_VALIDATION` um 1790536678,1279 führte zu keinem RESUME.
Der Testcontroller forderte deshalb um 1790536678,2797 Cancel an; Mission
und Explorer waren bis 1790536678,6365 `canceled`. Ab etwa
1790536679,13 meldete das frische Encoderfeedback 0,0/0,0 Motor-RPM und
0 m/s sowie 0 rad/s; die gemessene Drehung betrug höchstens 0,081 rad.
Der Beobachter hat den physischen Halt und die danach wieder wirksame
unabhängige Motorsperre dieses **früheren** Versuchs inzwischen bestätigt;
das ist kein Nachweis für den neuen Lauf. Kein zweiter Versuch, keine
Frontierfahrt, keine Parametrierung und kein RESUME.

Bag, Controller-Zeitfolge und Stack-/Recorderlogs bleiben lokal unter
`~/.local/share/amadeus/tests/hwt-recovery-real-20260927-3wLELq/`.
Mission, Launch und Recorder wurden beendet; beide seriellen Ports sind frei.
Beim SIGINT-Shutdown starb allein `slam_toolbox` mit `RCLError`/Exit -6;
das liegt nach dem Versuch und ist getrennt vom HWT-Fehler. Dieser Versuch
belegt den fail-closed Halt, **nicht** eine bestandene Real-Recovery.

### Roh-/Yaw-Lücke auf demselben Branch gerätefrei geschlossen

Die bisherige ROS-Graphprobe erzeugte `/shadow/hwt601/imu/yaw_rate` und
`/shadow/hwt601/status_json` unabhängig von der Roh-IMU dauerhaft gesund.
Dadurch konnte sie den real beobachteten Yaw-Latch nicht erkennen. Nach
Anbindung des echten `Hwt601ShadowNode` mit Bias-Schätzer und installiertem
`hwt601_shadow.yaml` reproduzierte der **Vorher-Lauf** denselben Ablauf:
kalibriert → etwa 0,261 s Rohdatenlücke → HOLD/Kindziel-Cancel →
`imu_datenluecke_neustart_noetig` → `yaw_missing_stale_or_invalid` als
`TERMINAL_FAULT`, Manager/BT-Failure; die Probe endete erwartungsgemäß mit
`source not recovered`. Kein Rohstatuswert des historischen Fahrfehlers
wurde ergänzt oder behauptet.

Die kleinste Änderung behandelt nur eine reine Samplelücke nach gültiger
Startkalibrierung: Der Yaw-Schatten verwirft den ersten zurückkehrenden
Messwert als Kontinuitätsgrenze, behält den eingefrorenen Bias und gibt erst
ab einem neuen zeitlich zusammenhängenden, gültigen Messwert wieder eine
**aktuelle** korrigierte Gierrate aus. Es wird weder ein Zwischenwert noch
eine rückwirkende Orientierung für die Lücke erzeugt. Ein Status
`data_continuity_pending` trennt vorübergehend gesperrte Yaw-Ausgabe von
echtem Bias-/Identitätsfehler. Health darf diesen engen Zustand nur während
HOLD/Validierung annehmen; ungültige IMU, rückläufiger Zeitstempel,
Kalibrierfehler, andere Yaw-Latches sowie falscher Port oder Reconnect
bleiben terminal. Nach einer erneuten Lücke in der Validierung beginnen
Rohmessungs- und Rohstatuszähler erneut bei null. Die Grenzen 0,10 s
(Kontinuität), 0,20 s (Rohfrische) und 0,35 s (Yaw-Frische) blieben
unverändert; die 5-s-/Zwei-Versuche-Grenzen ebenfalls. Bewegungsfreigabe
bleibt separat bei Health, Gate und Explorer.

**Nachher-Lauf:** Derselbe isolierte Produktgraph mit synthetischer Roh-IMU,
echtem Yaw-Schatten, beiden echten HWT-Guards, Gate, Explorer,
Mission Manager, BT und Nav2-Testgegenstelle bestand mit **0,260675 s
tatsächlicher Rohdatenlücke**. Der gespeicherte Bias
`[0,001, -0,002, 0,0001]` rad/s und `adaptation_samples=0` blieben
unverändert. Gate-HOLD sperrte alte Kommandos, das alte Kind wurde terminal,
der Elternauftrag blieb erhalten. Eine zweite Lücke während der Validierung
kehrte zu HOLD zurück. Trotz später gesunder Quellen wurde bei gemeldeter
Restbewegung, blockierter Route und anschließend absichtlich veralteter
Kartenpose kein Kind freigegeben. Erst nach Encoder-Stillstand, frischer
Kartenpose, freier Route und Gate-ACK startete **ein** neues Kind für
`task-1`; höchstens ein Kind war gleichzeitig aktiv. Getrennter Rundblick
ohne Kind hielt ebenfalls und setzte fort; Not-Aus beendete ihn ohne
automatischen Neustart. Die Karten-Task-Auswahl blieb wie zuvor ein
Testadapter. Der echte Roboter und seine Lokalisierungsqualität nach einer
realen Lücke sind damit noch nicht abgenommen.

**Gegenfälle und Build:** Direkte HWT-/Gate-/Explorer-/Manager-Tests
`109 passed`; isolierter Neubuild nur von `robot_state_estimation` nach
`/tmp/we1-hwt-yaw-install` und `colcon test-result` dafür
`149 tests, 0 errors/failures/skips`. Die Läufe überlappen und werden
nicht addiert. Dauerlücke blieb nach späterem Yaw-Wiederempfang terminal;
ungültige Daten und rückläufige Zeitstempel blieben verriegelt.
Bestehende Health-Tests decken Port-/Reconnect-/Biasfehler und begrenztes
Budget; der Produktgraph deckt erneute Lücke, Not-Aus und Nutzer-Cancel.
Ein Zwischenlauf der Probe scheiterte vor der Injektion an kurz stale
synthetischem Encoderfeed (`wheel_missing_stale_or_invalid`) und zählt
nicht als HWT-Erfolg. Der letzte vollständige Nachher-Lauf steht unter
`/tmp/we1-hwt-yaw-final3-graph.log`.

Die tatsächlich aufgelösten Präfixe waren
`robot_state_estimation=/tmp/we1-hwt-yaw-install/robot_state_estimation`,
`explore`, `robot_navigation`, `mission_manager` aus
`/tmp/we1-hwt-recovery-install` und `bt_orchestrator` aus
`/tmp/we1-full-shim-install/bt_orchestrator`; das Abnahmeprofil blieb
SHA256 `ee3b42eef682a830892e93f84093baf1547a84f76d6baa3e480a81dc1de393c4`.
Die drei installierten geänderten Pythonmodule sind bytegleich mit den
Quellen (SHA256 `907aba5f…`, `d9d824fd…`, `884a5ed9…`). Weder
Produktprofil noch aktiver Install wurden gewechselt. Dieser Stand ist ein
**bestandener gerätefreier Recovery-Nachweis**, kein Real-Rundblicknachweis,
keine Tür-/Nav2-Realabnahme und kein Stufe-3-Gesamtgrün.

**Rückfall:** Den funktionalen Branch nicht in den aktiven Install übernehmen;
bei einer späteren Regression auf den gesicherten PR-#104-Kandidaten
zurückkehren. Das bisherige fail-closed Latch bleibt dort erhalten. Vor
einem Realtest sind Runtime-Manifest, unabhängige Motorsperre, Stillstand,
anwesende Person und ein eigener begrenzter Fahrfreigabeentscheid nötig.

### Ein begrenzter Roh-/Yaw-Recovery-Realversuch auf `6b666d9`

Der Nutzer bestätigte vor dem motorlosen Start Stillstand, unabhängige
Motorsperre, Beobachter, erreichbaren Not-Aus und Sensorlauf. Der neue lokale
Lauf liegt unter
`~/.local/share/amadeus/tests/hwt-recovery-real-20260927-fxU0To/`.
`runtime_manifest.json` hält den sauberen Quell-HEAD
`6b666d97d7e11326c9f75dccbc4253112e99b578`, die expliziten Launch-Argumente
und das Abnahmeprofil mit SHA256 `ee3b42eef682a830892e93f84093baf1547a84f76d6baa3e480a81dc1de393c4`
fest. Die Setup-Reihenfolge endet nach ROS, Slam-, LiDAR-, Vollbuild- und
Recovery-Overlay beim isolierten Yaw-Overlay. `module_resolution.json` belegt,
dass `hwt601_shadow_node.py`, `hwt601_shadow_core.py` und
`hwt601_fusion_health.py` aus
`/tmp/we1-hwt-yaw-install/robot_state_estimation` geladen werden und bytegleich
mit den Quellen sind. Im echten Prozess starteten HWT-Leser und Yaw-Schatten
aus genau diesem Präfix. Der aktive Install blieb unverändert.

Der motorlose App-Mapping-Preflight auf demselben Profil (`active_drive=false`,
`enable_auto_explore=false`) zeigte 786 Roh-IMU- und 788 korrigierte
Yaw-Nachrichten in 8 s, kalibrierten stabilen Bias, `reconnects=0`,
Encoder-Stillstand, `sources_ready=true`, `first_fault=null` und 217
Gate-Nullkommandos. Scan, beide gesunden VL53-Frames und frisches
`map→odom→base_link` waren vorhanden; Mission und Explorer blieben `idle`.
Der Stack wurde sauber beendet und beide seriellen Ports waren frei. Danach
gab der Nutzer **genau einen** beaufsichtigten 40-s-/3-rad-Rundblick mit
0,08 rad/s, ohne Translation und mit einer etwa 0,25-s-Pause ausschließlich
des HWT-Lesers ausdrücklich frei. Der Recorder lief vor dem aktiven Stack;
alle 26 vorgesehenen Topics wurden synchron erfasst. Motorbus und HWT-Port
hatten je einen Besitzer. Scope-Verifikation blieb falsch und die ID leer.

Der Explore-Auftrag begann um `1790541890,927`. Der HWT-Leser wurde einmal
von `1790541897,798` bis `1790541898,048` (0,251 s) angehalten und mit
unabhängigem SIGCONT-Watchdog abgesichert. Das Bag misst eine Roh-IMU-Lücke
von **0,260533 s**. `first_fault` um `1790541898,017` lautet
`raw_missing_stale_or_invalid`: die letzte gültige Rohmessung war
**0,221942 s** alt bei **0,20 s** Grenze. Rohstatus-Empfangsalter
`0,609694 s < 1,0 s` und internes `age_s=0,000326 s` sind andere Größen;
`ready=true`, `raw_data_ready=true`, `reconnects=0`,
`consecutive_errors=0`. Dies ist kein rückwirkender Beweis für den
historischen `raw_driver_not_ready`-Fall.

Das Gate wechselte um `1790541898,022` auf HOLD und setzte
`/cmd_vel_nav` auf null. Explorer-HOLD folgte um `1790541898,042` bei
unverändert `running` bleibendem Explore-Elternauftrag. Das nachgeschaltete
`/cmd_vel` war um `1790541898,169` null; das reale Encoderfeedback zeigte
spätestens um `1790541898,623` beide gemessenen Motor-RPM null. Die
HWT-Health erreichte `RECOVERY_VALIDATION` um `1790541898,071` und
`HEALTHY` mit `resume_sequence=1` um `1790541899,076`. Der Yaw-Schatten
lieferte wieder aktuelle Werte ohne Latch. Alle 18 im Ereignisfenster
aufgezeichneten Yaw-Statusmeldungen trugen denselben eingefrorenen Bias
`[0,0015726155, 0,0055953393, 0,0000581250]` rad/s.

Während der Validierung kamen frische Karte, Costmap, Scan, beide gesunden
VL53-Status und beide dynamischen TF-Strecken an. Der Produktpfad prüfte
frische Quellen, Kartenpose und stabilen Encoder-Stillstand von mindestens
0,5 s vor Wiederaufnahme; für den Initialscan gab es **kein** Nav2-Kindziel
und keine Zielroute zu prüfen. Der Explorer meldete `we_hwt_resumed` um
`1790541900,379`, ging um `1790541900,483` in **denselben** Initialscan
zurück, und das Gate gab erst danach wieder Drehkommandos bis höchstens
0,08 rad/s aus. Der Controller beobachtete erneute gemessene Drehung und
forderte um `1790541905,855` Cancel an, 14,928 s nach Explore-Start;
die Gesamtdrehung aus `/odom` war 0,136 rad und jedes lineare Kommando
null. Manager und Explorer waren bis `1790541906,720` beziehungsweise
`1790541906,707` `canceled`; Encoder-Stillstand nach Cancel ist um
`1790541907,228` protokolliert. Kein Frontierziel und keine Translation.
Stack und Recorder endeten geordnet; beide Ports sind frei. `real-bag/`,
`control-events.jsonl`, `run-analysis.json` und Logs bleiben lokal.

**HWT-RECOVERY IM BEGRENZTEN RUNDBLICK – REAL BESTANDEN.** Der anwesende
Beobachter bestätigte am 28.09.2026 für **diesen neuen Lauf** ausdrücklich:
Der Roboter hielt beim HOLD tatsächlich physisch an, stand nach Cancel
still und die unabhängige Motorsperre war danach wieder wirksam. Diese
nachträgliche Außenbeobachtung ist getrennt von Bag und Encoderbeleg; sie
ändert deren Messwerte nicht. Eine Wiederholung zur Erzielung einer grünen
Wertung wurde nicht durchgeführt. Der Initialscan belegt weder
Nav2-Kind-Cancel noch Tür- oder Frontier-Recovery; Stufe 3 bleibt offen.
Kein TOR 2, Merge, Installwechsel oder weiterer Fahrtest folgt automatisch.

## 6. Erhaltene Nachweise und Roadmapgrenzen

| Umfang | Stand |
|---|---|
| Bisherige „Stufe 1“ | Historisch GRÜN für die dort bezeichnete Basis; erhalten |
| Bisherige „Stufe 2“ | Historisch gerätefrei GRÜN; keine Abnahme der späteren Runtime |
| HWT-/Encoder-Preflight vom 26.09. | Zwei bestandene motorlose Zyklen im Vorgängerstatus berichtet |
| Begrenzter Bewegungstest | `complete` und 0,270 m aus `/odom` berichtet; kein unabhängiger metrischer Gesamtfahrnachweis |
| Historischer Rundblick 27.09. vor PR #105 | 361,7° und korrektes Missions-/BT-/Gate-Startverhalten berichtet; kein Frontierziel erreicht |
| VL53-Recovery | Im Kandidaten softwaregeprüft; im Realtest nicht ausgelöst, da keine neue VL53-Störung auftrat |
| Aktuelle HWT-Störung | Sammelursache und Latch-Zeitpunkt belegt; verletztes Rohstatusfeld fehlt im Bag |
| Raumwechsel, Hindernisbewältigung und Missionsfortsetzung | Auf konsolidiertem Gesamtkandidaten nicht vollständig real nachgewiesen |
| WE-M4 / WE-M5 / WE-M6 | Reale Abnahmen weiter offen; vorhandene Bausteine nicht neu entwickeln |

„Stufe 1/2/3“ sind bisherige Arbeitsbezeichnungen. Die Roadmap bleibt WE-D0
und WE-M0 bis WE-M7; keine neue Meilensteinfolge.

## 7. Nächster Schritt und Historie

### Aktueller Auftrag vom 29.09.2026: reale Kernabnahme A → B → C

Verbindlicher Nutzerentscheid auf `5c6ff0e`: Schritt 2 wie in Abschnitt 1
abgeschlossen; reale HWT-Kindinjektion geparkt. Keine Fault Injection hier.
Kandidat bleibt Software `6429bd6` mit korrigiertem HWT-/Portalpfad `e5b221b`.
Das Repositoryprofil `hwt601_recovery_acceptance_params.yaml` ist die Basis:
WE-Navigation, Initialscan, Portal und Coverage aktiv; Rückfahrt aus.
Die speziellen lokalen Kindziel-Testprofile und Controllergrenzen gelten nicht.
Vorhandene 900-s-Gesamtfrist, 120-s-Kindfrist und produktive Schutzgrenzen bleiben.

Reihenfolge: motorloser Quellen-/Karten-/TF-Vorlauf mit tatsächlichem Manifest,
danach reguläre Mission ausschließlich über Mission Manager → BT → WE-Explorer
→ Nav2 → Schutzkette → Basis. Recorder vor Stack, Action-Themen mit
`--include-hidden-topics`. Kein manuelles Ziel, kein synthetischer Task.
Nach A direkt B, dann C im selben beaufsichtigten Laborauftrag. Eine geeignete
reale Hindernis-/Türsituation muss tatsächlich beobachtet werden; fehlende
Belege werden nicht durch Simulation oder bloße Sensorbereitschaft ersetzt.

Aktueller Ausführungsstand: **motorloser Quellen-/Karten-/TF-Vorlauf bestanden**.
Lokale Belege unter `~/.local/share/amadeus/tests/stage3-core-20260929/`:
`passive-manifest.json`, `passive-source-preflight.json`, `passive-summary.json`,
`passive-bag/`. Produktprofil SHA256
`ee3b42eef682a830892e93f84093baf1547a84f76d6baa3e480a81dc1de393c4`.
60,244 s Aufzeichnung, null Nichtnull-Kommandos auf `/cmd_vel`. Reale Quellen,
Bias-Readiness, Encoder-FC03, VL53-Frames, Stillstand, Karte und Map-TF geprüft;
Mission/Explorer idle. Recorder vor Stack; beide sauber beendet.
Noch keine neue Mission oder Fahrt gestartet. Der Portalmonitor ist im
Recoveryprofil noch aus; für C fehlen dessen explizite Profilzuordnung und
eine aktuelle verifizierte Labor-Scopebindung. Alte Polygone werden nicht
übernommen. Quellen-Preflight allein ist keine A/B/C-Abnahme.
Die unabhängige Motorsperre ist zuletzt als geschlossen bei erreichbaren
Encodern bestätigt. Die Labor-Sitzungsfreigabe gilt; eine notwendige tatsächliche
Schalterstellung ist von erneuter Freigabe zu unterscheiden.
Konkrete Softwarefehler werden gemessen, minimal korrigiert und gezielt erneut
geprüft. Hard-Faults beenden den Lauf; Shutdownbefunde getrennt ausweisen.
**Genau nächster Auftrag:** Diese reale A/B/C-Kernabnahme durchführen; erst bei
vollständigem Erfolg WE-M4 vorbereiten. Masterplan v1.1 bleibt unverändert.

### Historische Kindziel-Sondertests bis 28.09.2026

Die folgenden Befunde bleiben erhalten. Ihre damaligen Folgeaufträge und
künstlichen HWT-Testgrenzen sind durch den vorstehenden Nutzerentscheid abgelöst.


### Aktueller Ergebnisstand 28.09.2026: Produktpfad korrigiert, Fahrfall offen

**Software `6429bd6` im selben PR #105; kein Merge, kein aktiver Installwechsel.**
Der Nutzer hat die begrenzte Laborsitzung bis zum erfolgreichen Missionsnachweis
freigegeben. Die festgelegten Grenzen (autonome Route ≤1,50 m, kumulierte
Translation ≤0,60 m einschließlich Nachlauf, 35/340 s, unveränderte HWT-/Encoder-/
Collision-/Geschwindigkeitsgrenzen) werden dadurch nicht aufgehoben.

**Tatsächlich behoben:**

- Der lokale aktive Teststart hatte `enable_auto_explore=false` aus dem passiven
  Aufruf übernommen. Damit war `explore_execution=simulation_only_no_navigation`;
  ein gemeldetes `success` war nur Simulation. Korrigierter Realaufruf:
  `active_drive=true`, `enable_auto_explore=true`, Mission ausschließlich per
  Mission Manager → BT → WE → Nav2. Beide lokalen Preflights verlangen nun
  `bt_explicit_opt_in`; der Opt-in allein sendet keinen Missionsauftrag.
- Der wiederverwendete aktive Prüfhelfer verwies noch auf eine historische
  Profil-Datei. Er prüft jetzt die konkrete lokale Profilkopie am eigenen Pfad.
  Geladene Scope-ID und Polygon wurden zusätzlich über ROS-Parameter gelesen.
- Die Startgrenze lag exakt auf dem gepolsterten hinteren Footprint. Die
  tatsächliche kleine Poseabweichung verursachte 0,114 mm Überschreitung und
  sofortigen Cancel ohne Kind/Bewegung. Der Nutzer bestätigte danach **5 cm
  freien Raum hinter der hintersten Roboterkante** und ausdrücklich dessen
  Aufnahme als Startreserve. Nur diese Reserve wurde lokal ergänzt; kein
  Rückwärtsfahren. Die Start-Footprint-Prüfung liegt nun vor dem Missionskommando.
- Der lokale Controller prüft den gepolsterten Footprint entlang des Plans und
  bei Schwenkbewegungen im konvexen Scope, nicht nur Punkte in dessen Boundingbox.
  Eine neu angenommene, noch planende Action darf bei Stillstand auf ihren Plan
  warten; Bewegung ohne aktuellen Plan wird abgebrochen. Produktprüfungen für
  Belegung, Pose und tatsächliche Nachführung bleiben erforderlich.
- Der bestehende optionale `frontier_forward_cone_half_angle_rad` wirkte nur
  im älteren Explorerpfad. `6429bd6` bindet ihn vor WE-Frontier-Dispatch an den
  tatsächlich gestagten metrischen Kandidaten. Seitliche Kandidaten werden mit
  `frontier_outside_forward_cone` zurückgehalten; Ziel, Task und Route werden
  nicht erzeugt, verschoben oder abgeschnitten. **Produktstandard 0 bleibt
  unverändert**, alle übrigen Schutz- und Recoveryprüfungen bleiben erhalten.

**Begrenzte Ergebnisse, ohne Fahr- oder Recovery-Grün:**

1. Motorloser Ausgangsvorlauf: Quellen/Karte/TF/Stillstand bereit, 100,272 s
   Aufzeichnung, kein Nichtnullkommando, 0,000 m Translation, kein HWT-first_fault.
2. Erster Stoppmess-Anlauf: Start-Footprint-Grenze, Cancel ohne Nav2-Kind und
   ohne Bewegung. Zweiter Anlauf: Simulation statt Realpfad, ebenfalls keine
   Bewegung. Beide bleiben ausdrücklich **nicht ausgelöst**, keine Stoppbelege.
3. Nach korrigiertem Real-Opt-in entstand ein echtes autonomes Nav2-Kind mit
   aufgezeichneter Goal-UUID und einem **0,449705 m** langen Plan. Die erste
   Planrichtung lag etwa **93,8° rechts**; der geplante gepolsterte Schwenk passte
   nicht in das Scope. Der lokale Controller cancelte ohne Fahrkommando; das
   Kind erreichte Status 5 (`CANCELED`), Mission canceled und Encoder-Stillstand.
   **0,000 m Translation, keine HWT-Injektion.** Das belegt Dispatch/Cancel im
   Produktpfad, aber weder physisches Bremsen noch Kindziel-Recovery.
4. Software: **1.199 gerätefreie Regressionen bestanden** (Explore,
   robot_state_estimation, robot_navigation, Mission Manager). Der echte
   WE-Statuscallback wurde mit deaktivierter Begrenzung, seitlichem blockiertem
   und vorderem freigegebenem Kandidaten geprüft. **30 lokale Controllerprüfungen**
   bestehen; sie ersetzen keinen vollständigen Realnachweis. Explore wurde
   isoliert neu gebaut; HWT-Yaw/Core/Health/Guard bleiben aus dem bisherigen
   korrigierten Overlay. Kein erneuter Build anderer Produktpakete.
5. Neue Software motorlos: Quellen und Scopebindung zunächst bestanden. Eine
   lokale Probe mit 0,17 rad war unnötig an die Vororientierung gekoppelt; sie
   bleibt als konservativer Zwischenstand erhalten. Die aktuelle lokale
   Kandidatenbegrenzung beträgt **0,2529368168 rad (14,49°)**, rein aus dem
   bestätigten seitlichen Freiraum, gepolstertem Footprint und 1,50 m maximaler
   Route hergeleitet: `(L + front) sin(theta) + halfwidth cos(theta) ≤ min(left,right)`.
   Das ist nur eine Richtungs-Vorauswahl; die vollständige echte Route, Kurven,
   Belegung und der Scope müssen weiterhin unabhängig bestehen.
6. Ein motorloser Start verriegelte den Encoderleser mit
   `encoderpaar_zeitfenster_ueberschritten`: **0,121539587 s > 0,120000000 s**.
   Kein Grenzwert geändert, kein Live-Reset, keine HWT-Ursache daraus abgeleitet.
   Der Stack wurde geordnet beendet; ein weiterer unveränderter motorloser
   Start ohne parallele Softwaretests bestand den Quellen-/Pose-/Scopecheck.
   Das beweist keine behobene Ursache des einmaligen FC03-Zeitüberlaufs.
7. Im anschließenden begrenzten 15-s-Beobachtungsfenster lagen die tatsächlich
   angebotenen Kandidaten rund **17,4° bis 38,4° rechts**, Routen 0,712 bis 1,165 m.
   Sie wurden korrekt zurückgehalten; weitere Statusbilder meldeten
   `withheld_by_current_policy`. Kein aktueller passender autonomer
   Vorwärtskandidat belegt. Keine weitere aktive Mission angehängt.

**Nach vollständiger Bag-Auswertung ergänzte Grenzen:**
Die Goal-UUID und Statusfolge des echten Kindes sind im zeitgestempelten
`control-events.jsonl` enthalten, **nicht im Bag**. Der verwendete native Recorder
hat versteckte Action-Themen trotz expliziter Topicliste ohne
`--include-hidden-topics` nicht aufgenommen. Isolierte gerätefreie Gegenprobe
(Domain 225, ausschließlich ein Test-Statuspublisher, keine Roboterthemen):
ohne Option 0, mit Option **73 Statusnachrichten**. Der nächste vorhandene
Recorderaufruf muss diese Option enthalten; keine neue Recorderarchitektur.
`recorder-command-contract.json` und `recorder-hidden-probe-result.json`
sichern die Korrektur. Keine rückwirkend vollständige synchrone Action-Aufzeichnung
für den vergangenen Lauf behaupten.

Die Bag-Gesamtsummen enthalten zusätzliche Meldungen **nach** eingeleitetem
SIGINT: im Simulationsanlauf Rohmessalter 0,211282 s > 0,20 s, im ersten
Forward-Vorlauf FC03-Paar 0,132546 s und im letzten Vorlauf zunächst
Wheel-Messalter 0,181569 s > 0,18 s, dann FC03-Paar 0,126837 s. Diese
Abschaltbefunde bleiben erhalten (`late-fault-analysis.json`) und werden weder
als störungsfreier Gesamtbag noch als Fehler während des freigegebenen Fensters
ausgegeben. Der FC03-Befund 0,121539587 s im fehlgeschlagenen Vorlauf lag dagegen
**vor** dem Shutdown und bleibt offen. Alle sieben Bags belegen 0 Nichtnull-
Fahrkommandos und 0,000 m Translation. Alle Stacks/Recorder sind geordnet beendet,
Roboterknotenprüfung leer und beide seriellen Ports ohne Besitzer.

**Aktueller Abschluss:** TESTFALL NICHT AUSGELÖST / TEILNACHWEIS.
Die allgemeine Laborfreigabe liegt vor; es fehlt aktuell ein autonomer Kandidat,
welcher die begrenzten räumlichen Testbedingungen erfüllt. Ein manuelles Ziel,
eine synthetische Aufgabe, zufälliges Wiederholen oder Lockerung von Schutzwerten
wird daraus nicht abgeleitet. Der reale Nachlauf der Cancel-Kette ist weiterhin
unbelegt; `stopping_evidence=null` sperrt die Recoveryausführung. Eine Simulation
oder ein Cancel bei 0 m/s erfüllt diese Voraussetzung nicht. Der zuvor bestandene
Rundblick bleibt erhalten, Stufe 3 bleibt OFFEN/GELB.

**Genau nächster Schritt:** Den realen Startaufbau so vor Ort ausrichten, dass
innerhalb des erneut bestätigten Geradeauskorridors eine echte autonome
Frontieraufgabe in zulässiger Richtung erreichbar ist; danach neue Live-
Scopebindung und Quellen prüfen und denselben vorbereiteten begrenzten
Stopp-/Kindzielnachweis fortsetzen. Keine künstliche Zielbereitstellung und
keine automatische Fahrt allein aus dieser Dokumentation. Die Stellung der
Motorsperre wurde zuletzt vor dem korrigierten motorlosen Vorlauf als wirksam
bei erreichbaren Encodern und Stillstand bestätigt.

**Lokale Belege, keine Wohnungsdaten im Repository:**
`~/.local/share/amadeus/tests/hwt-child-route150-20260928/` enthält Manifeste,
Profilstände/Hashes, `stop-attempt-01/`, `stop-attempt-02/`, `control-events.jsonl`,
`stop-03-plans.json`, `forward-cone-regression.log`, `forward-build-log/`,
`forward-loaded-modules.json`, die unverändert erhaltenen Einzelbags,
`geometric-passive-encoder-fault.json`, `geometric-passive-02-candidates.json`,
`forward-cone-geometric-decision.json` und `run-summary.json`. Karten-/Scope-
Fingerprints, Koordinaten und Bags bleiben lokal. Nach Stackende sind diese
Bindungen historische Laufbelege und keine laufende Karte.

**Die nachfolgenden früheren Testentscheide/Berichte bleiben historisch erhalten;
der vorstehende Ergebnisstand bestimmt den aktuellen nächsten Schritt.**

### Testentscheid 28.09.2026: Zielroute und gefahrenes Budget getrennt

**Nutzerentscheid vor einem neuen Versuch:** Vollständige autonom erzeugte
Route höchstens **1,50 m** statt 0,45 m; tatsächlich gefahrene Translation
weiterhin höchstens **0,60 m kumuliert einschließlich Reaktions-/Bremsnachlauf**.
Route vollständig im aktuell bestätigten, live gebundenen Scope, einschließlich
Footprint, Kurven und Abständen; kein unbekannter Bereich wird als frei behandelt.
Keine Scope-Ausweitung. Kein Budgetreset bei HOLD, Resume oder neuem Kind.
Nach beobachteter kurzer Wiederaufnahme beenden, nicht das Frontierziels erreichen.
35 s ab erstem aktiven Kind und 340 s Gesamtzeit bleiben einschließlich Beendigung
bestehen; Geschwindigkeiten/Schutzgrenzen bleiben unverändert. Initialscan,
Portalquerung, Coverage, Rückfahrt und manuelle/synthetische Zielvorgabe bleiben aus.
Genau eine abgesicherte HWT-Leserpause erst bei autonomem aktivem Kind, erfasster
Task-ID/UUID und gemessener Vorwärtsfahrt. Keine zusätzlichen Fahrversuche.

**Umgesetzt, ausschließlich lokal:** Vorhandener Testcontroller und
SIGCONT-/Cancel-Verfahren unter `hwt-child-route150-20260928/` wiederverwendet.
`test-limits.json` trennt 1,50 m Routenobergrenze, 0,60 m Bewegungsobergrenze und
35/340 s Zeitobergrenzen. Die unveränderte Produktprofilkopie enthält keine
Lockerung von Sensor-, HWT-, Collision- oder Geschwindigkeitsparametern.
Der Controller fordert vor ROS-/Missionsstart einen belegten, an Kandidat und
Geschwindigkeit gebundenen Stoppnachweis. Daraus werden Distanz- und Zeitreserve
vor den harten Grenzen abgezogen. Der bisherige Cancel erst bei 0,60 m wäre zu
spät und wird nicht verwendet. Wegmessung läuft während HOLD, nach neuem Kind
und während der Stopbestätigung weiter; große Odometrieschritte werden nicht
mehr aus der Wegsumme herausgelassen. Kein realer Reservewert erfunden:
`stopping_evidence=null` sperrt den Start. Eine neue Live-Scopebindung ist noch
nicht aktiviert; der bisherige statische Scope ist keine aktuelle Fahrfreigabe.

**Gerätefreier Nachweis:** `budget-tests.log`: **15 bestanden**. Getestet sind
weit entfernte Ziele bis 1,50 m bei gleichbleibender früher Distanzschwelle,
HOLD/Resume/UUID-Wechsel ohne Wegreset, Mitrechnung nach Cancel, reservierte
Beendigungszeit und Sperre bei fehlenden/ungültigen/nicht passenden Nachweisen.
Synthetische Reserven in den Tests dienen ausschließlich der Softwareprüfung
und werden vom Realstart explizit abgewiesen. Kein neuer Produktbuild nötig:
`runtime-resolution.json` und `module-match.json` bestätigen die fünf
aufgelösten Explore-/HWT-Module bytegleich mit dem isolierten `e5b221b`-Kandidaten.
Die übernommenen 1.187 Regressionen und der Produktgraph wurden nicht wiederholt.

**Konkrete Grenze: Realtest nicht gestartet.** Die vorhandene reale
Bewegungsdiagnose `stage3-hwt601-motion-20260926T105410Z.jsonl` ergibt beim
Vorwärtsstopp 0,0212497 m Odometrieweg vom letzten Sample vor Stoppbeginn bis
zur folgenden Phase; Geschwindigkeit vor dem Stopp etwa 0,0301300 m/s.
Sie verwendete ein Diagnose-Nullkommando (Soll 0,08 m/s), nicht die aktuelle
Mission-Manager → BT → Nav2-Cancel-Kette bis zum erlaubten Ausgang 0,12 m/s.
Die bisherigen Parity-Bags enthalten keine entsprechende translatorische
Fahrt mit diesem Stoppnachweis. Die dokumentierten Nav2-Nachlaufwerte
0,022/0,037 m sind virtuelle Prozessnachweise, keine physische Bremsmessung.
Daraus lässt sich keine belastbare aktuelle Reserve ableiten.
Lokale Auswertung: `historical-stop-evidence.json`,
`available-motion-evidence.json`, SHA256-Verzeichnis der Prüfarbeitsdateien.
Keine neue HWT-Ursachenanalyse; kein Gerät, Stack oder Aktor gestartet und
keine Mission/Injektion/Fahrt. Vorhandene Laborfreigabe wird nicht erneut
abgefragt; es fehlt ein Nachweis, keine identische Zustimmung.

**Genau nächster Auftrag:** Einen separat freigegebenen, begrenzten realen
Nachlaufnachweis der aktuellen Stop-/Cancel-Kette bei den vorgesehenen
Geschwindigkeiten erbringen oder einen tatsächlich übertragbaren vorhandenen
Nachweis bereitstellen. Daraus die Stoppreserve für denselben einzelnen
Kindziel-Recoverytest festlegen. Erst danach aktueller motorloser Quellen-/
Karten-/Scope-/Routenvorlauf und der bereits beauftragte Test. Kein zusätzlicher
Fahrversuch aus diesem Dokument gestartet, keine Produktreparatur oder
Grenzlockerung. Ergebnis bleibt ein Software-Teilnachweis, **keine reale
Kindziel-Recovery-Abnahme**, Zielerreichung/Wohnungserkundung separat offen.

### Historischer Abschluss vor der Änderung der Routengrenze


### Übernommener Teilnachweis: gezielte Portal-/Explorer-Reparatur vom 28.09.2026

Arbeitsbasis `7e27082a8074a1ad2e5abd69778ea9725cf7c3f4`, gleicher
Branch `feature/hwt-hold-recovery-resume` / PR #105, Masterplan v1.1 Schritt 2.
Der reale Rundblicknachweis bleibt bestanden; der reale Kindzielnachweis ist
weiter offen. Kein Merge, kein Wechsel des aktiven Installs.

**Konkrete Portalursache:** Im tatsächlich aufgelösten lokalen No-Scan-Profil
war `region_graph_shadow_connected_portals_enabled=false`. Deshalb kehrte
`_try_observe_connected_raw_map_portals` vor jeder Verarbeitung zurück;
es gab keinen ausgewerteten Bestand, auch keinen nachgewiesen leeren.
Die unveränderte Aufgabenpolicy sperrte folgerichtig `portal_memory`.
Das lokale korrigierte Profil aktiviert ausschließlich diesen benötigten Feed;
Portalquerung bleibt aus. Die WE-Startvalidierung weist die widersprüchliche
Konfiguration jetzt sofort zurück, statt minutenlang auf sie zu warten.

**Unveränderte Karte:** Der reale Kartenmanager zählt validierte Beobachtungen
in `observed_maps`, auch bei unverändertem Fingerprint. Der Exaktjoin führt
jede neue Beobachtung durch den echten Portal-/Frontierdetektor. Ein erfolgreich
leerer Bestand erhält dadurch eine belegte Revision und Verarbeitungszeit.
Bloße identische Replays erneuern weiterhin keine Frische; fehlende Verarbeitung,
überalterte Quellen und fremde Karten bleiben gesperrt. Keine Portale erfunden,
keine Revision künstlich erhöht und keine Policy-Frische entfernt.

**Explorer/HWT:** Eine Guard-Entscheidung liefert Fehlergrund und Zustand unter
dem vorhandenen Health-Lock gemeinsam. Die WE-Schleife benutzt dieses eine
Ergebnis für HOLD bzw. terminalen Abbruch. Der Regressionstest reproduzierte
zuvor gesund → recoverbarer Fehler bei der zweiten Prüfung → Sofort-Abbruch;
danach erreicht er HOLD mit erhaltenem Auftrag. Der Explorer veröffentlicht
seinen eigenen `hwt_first_fault` und `hwt_recovery_state` im bestehenden
`/explore/status_json`; der Guard protokolliert den Originalsnapshot einmal.
Die Ursache des historischen Explorer-Abbruchs wird dadurch nicht nachträglich
bewiesen. Klassifikation, Fristen, Recoverybudget und Latches bleiben unverändert.

**Zwei im geforderten Integrationsnachweis reproduzierte Übergabefehler:**
Überlappende Policy-Timer konnten einen älteren Snapshot nach einer neueren
Revision abschließen. Nur dieser Timer nutzt jetzt eine eigene gegenseitig
ausschließende Callbackgruppe; Sensorempfang bleibt parallel. Bei einem vom
Kartenadapter abgewiesenen fremden Frame blieb außerdem ein alter Kandidat
abrufbar. Der vorhandene Schattenfehler sperrt jetzt sowohl Kandidatenabruf
als auch Quellenfreigabe eines laufenden Kindes. Der Fremdkarten-Gegenfall
scheiterte vorher an genau dieser Abrufbarkeit und besteht danach.

**Gerätefreie Belege:** 1.187 Tests aus Explore, State Estimation, Navigation
und Mission Manager bestanden. Zwei geänderte Pakete wurden isoliert gebaut.
Lokale Logs/Build/Profil unter
`~/.local/share/amadeus/tests/hwt-portal-repair-20260928/`.
Der erweiterte bestehende Graph verwendet echte Yaw-/Biasverarbeitung,
Kartenmanager, Exaktkorrelation, Portal-/Frontierfeed, Aufgabenpolicy, Explorer,
Mission Manager, BT und Gate. Nur Sensoren und Nav2-Gegenstelle sind synthetisch;
keine eingesetzte Aufgabe, kein fest eingesetzter Kandidat, kein Frischestempel-
Adapter. Testkarte: 40 × 30 Zellen à 0,10 m, 1 Hz; kein Lastabnahmenachweis.
`graph-recovery-final.log`: autonome Aufgabe `task-frontier_000001`, gemessene
Rohdatenlücke 0,270301 s, HOLD, altes Kind terminal, Bias unverändert,
Bewegung/ungültige Route/fehlende Pose sperren, Stillstand und Quellen-/Routenprüfung,
Gate-ACK 1, genau ein neues Kind und neue Bewegungsausgabe. Maximal ein aktives
Kind; Nutzerabbruch beendet das neue Kind. Fehlender Portalfeed und ungültige
Route sperren die echte Zielauswahl; unveränderte Kartenbeobachtungen blockieren
sie nicht. Separater Fremdkarten-Nachweis: `graph-foreign-after.log`.
Getrennte Läufe `graph-permanent-final.log` und `graph-estop-final.log`
beenden das aktive Kind und die Mission ohne Neustart. Im Not-Aus-Lauf erfolgte
der belegte Cancel wegen `estop_missing_stale_or_active`; 0,89 s später trat
zusätzlich eine synthetische Encoder-Frischeverletzung auf. Der frühere saubere
Not-Aus-Lauf `graph-estop-2.log` enthält diese Zusatzstörung nicht. Der
Fremdkartenlauf belegt den gesperrten Kandidaten direkt vor Missionsstart;
eine später zusätzliche Yaw-Störung ist kein Karten-Nachweis.
Fehlgeschlagene Vorläufe bleiben lokal erhalten, einschließlich einer
zusätzlichen synthetischen Encoder-Frischeverletzung im ersten Not-Aus-Lauf;
sie werden nicht als erfolgreicher gezielter Nachweis gezählt.

**Vor Ort bestätigt:** unabhängige Motorsperre wirksam, Roboter steht still,
Controllerelektronik für FC03 erreichbar. Dies schließt die zuvor offene
Sperrenrückmeldung. Daraus wird kein bereits gelöster Motorhalt abgeleitet.

**Realer motorloser Vorlauf auf Ergebniscommit
`e5b221be5e9e54296319c96640efbdef6cb63969`: TESTFALL NICHT AUSGELÖST.**
Recorder mit vollständigem Interface-Overlay vor dem passiven
`app_mapping.launch.py` gestartet (`active_drive=false`,
`enable_auto_explore=false`). Das Manifest und `loaded-modules.json` belegen
Explore, HWT-Schattennode, Schattenkern, Health und Guard aus dem neuen
isolierten Kandidaten; alle fünf aufgelösten Module sind bytegleich mit den
Quellen. Das tatsächlich geladene lokale Profil hat SHA256
`89d966b79d79699a3d53c73ab2c75752c67a57b1158b23caf90c7ca9ec6efd07`;
`passive-launch-profile.yaml` erhält diese unveränderten Startbytes.

Reale HWT-/Encoderquellen gesund, FC03 ausschließlich lesend, beide VL53-Frames
gesund, frische Karte und `map→base_link`, gemessener Stillstand. Der erste
lokale Prüfskriptlauf lief wegen fälschlich erwarteter aktiver Encoderfeldnamen
aus; mit dem tatsächlichen Read-only-Schema bestand dieselbe laufende passive
Session. Keine Produktänderung oder Stackwiederholung dafür.

Die neue lokale Scopevorlage wurde aus der gemessenen Startpose und dem
bestätigten Geradeauskorridor erzeugt und an die Live-Karte gebunden;
Koordinaten/Fingerprint bleiben ausschließlich in `passive-live-binding.json`.
Profil-SHA256 danach
`9c55a328ff50671662f4ba4f5d42d9735f999c83bc08e575fc325207d7651f41`.
Diese neue Profilfassung wurde **nicht** im laufenden Node nachgeladen oder
aktiv gestartet. Der Quellen-/Kartencheck ist bestanden; eine vollständig
aktivierte Abnahme mit dieser neuen Scopefassung wird nicht behauptet.

Die Portalblockade ist im realen passiven Produktpfad behoben:
`ready_with_tasks`, keine stale Quellen und autonome Frontierauswahl.
Alle **195** aufgezeichneten aktuellen Kandidaten hatten jedoch
**0,959117–1,461838 m** Routenlänge. Die letzten vier Vorschauen lagen bei
1,176396 / 1,461838 / 1,176396 / 1,176396 m. Damit fehlt konkret ein autonom
gewähltes Produktziel innerhalb der unveränderten **0,45-m-Routengrenze**.
Die vorhandene Freigabe wurde weder erweitert noch durch ein manuelles Ziel
ersetzt. Kein aktiver Start, keine Mission, keine HWT-Pause und keine Fahrt.

`passive-bag` umfasst 203,65 s; alle aufgezeichneten `/cmd_vel_nav`,
`/cmd_vel_smoothed` und `/cmd_vel` sind null, Odometrieweg 0,000 m,
keine Nav2-UUID und kein laufender Explore-Auftrag. Vor der letzten
Kandidatenerfassung kein Fusion-Erstfehler. `/near_field/status` ist diesmal
mit aufgezeichnet. Launch geordnet nur über den Elternprozess beendet,
28/28 Kinder sauber, anschließend Recorder beendet, Ports frei.
`result.json` enthält Zählwerte und beide Profilhashes. Die beendete
SLAM-Session ist keine weiterhin gültige Live-Bindung.

**Damals nächster Auftrag (abgelöst):** Den fehlenden realen Ausgangspunkt für genau
denselben begrenzten Kindzieltest herstellen: Im bestätigten freien Bereich
muss der unveränderte Produktpfad selbst ein gültiges Ziel mit Route ≤ 0,45 m
liefern. Nach tatsächlicher Vor-Ort-Zuordnung und erneuter Live-Scopebindung
nur diesen einen Test mit den bereits festgelegten Grenzen durchführen.
Keine manuelle Zielvorgabe, Scope-Ausweitung, neue HWT-Untersuchung oder
vorsorgliche Softwareänderung. Ein gelöster Motorhalt ist vor dem aktiven
Start weiterhin tatsächlich vor Ort zu bestätigen. Kein automatischer
Folgeversuch, kein Gesamt-Grün für Stufe 3.

### Historisch: aktiver Einzelversuch vor dieser Reparatur


**Historischer aktiver Einzelversuch vom 28.09.: TESTFALL NICHT AUSGELÖST.**
Der korrigierte Ablauf wurde **einmal** über
`app_mapping.launch.py` mit `active_drive=true`, HWT-Odometrie,
`enable_auto_explore=true` und dem lokalen Profil ohne Initialscan
(SHA256 `a5e6b1d0…`) gestartet. Manifest
`~/.local/share/amadeus/tests/hwt-child-active-20260928-once/runtime-manifest-active-v2.json`
ordnet die installierten Pakete dem isolierten PR-#105-Build und
Quell-HEAD `b870c969…` zu. Das Profil war in `/explore_node` tatsächlich
aufgelöst: WE-Navigation und Scope an, Initialscan/Portal/Coverage/Rückkehr
aus, 340/35 s und je ein Frontier-/Fehlziel. Nach SLAM-Neustart wurde
Scope-ID `we1-hwt-child-noscan-20260928-once` an die neue Live-Karte
`fb26a819…` und aktuelle Pose gebunden; der maximale Polygon-Eckenversatz
zum bestätigten Geradeauskorridor betrug 0,0009 m. Ohne Mission waren HWT-
Fusion, Encoderfeedback, `map`/TF, Not-Aus-Status und Nullsollwerte gesund;
`base_hardware` war alleiniger Motorbusbesitzer, der HWT-Leser allein auf
seinem Port. Der Nutzer bestätigte den kontrolliert gelösten unabhängigen
Halt und den weiterhin beaufsichtigten freien Korridor vor dem aktiven Start.

Recorder und unabhängiger 340-s-Cancel-Wächter liefen vor dem **einzigen**
Mission-Manager→BT→WE-Explorer-Auftrag. Während der 247,97 s bis zum
terminalen Produktfehler blieben alle 249 auswertbaren Explorer-Statusbilder
in `waiting_for_fresh_sources` mit genau `stale_source:portal_memory`.
Zuletzt waren 22 Aufgaben offen und fünf als geeignet geführt, aber
`selection.task_id=null`, `goal_candidate=unavailable` und
`navigation_dispatched=false`. Der Bag enthält null Nav2-Action-Status,
null Feedback und null `/plan`. Ohne Kindziel und Vorwärtsfahrt wurde
**keine** HWT-Leserpause ausgelöst. Alle 8841 `/cmd_vel_nav`-, 7820
`/cmd_vel_smoothed`- und 41 `/cmd_vel`-Nachrichten waren null; `/odom`
weist 0,000 m Translation aus. Der aktive Produktlauf ist damit kein
Kindziel-Recovery-Nachweis und keine Stufe-3-Freigabe.

Um `1790618944,0016` protokollierte der Explorer unerwartet
`HWT-Recovery TERMINAL_FAULT: raw_missing_stale_or_invalid` und endete
mit entsprechendem Missionsfehler, **ohne** vorherigen HOLD und ohne
Fault Injection. Der unabhängige Fusion-Status blieb um dieses Ereignis
`HEALTHY`, `first_fault=null`; aufgezeichnete Roh-IMU-Empfangsabstände
erreichten zwischen `1790618939` und `1790618945` höchstens 0,043 s,
und die 2-Hz-Rohstatusbilder vor/
nach dem Ereignis waren `ready=true`, `reconnects=0`. Diese Bagdaten
belegen nicht den exakten internen Erstwert des Explorer-eigenen HWT-
Wächters; aus ihnen wird keine neue HWT-Ursache erfunden. Der Controller
forderte nach terminalem Missionsstatus Cancel an und protokollierte
Encoder-Stillstand. Stack und Recorder wurden geordnet beendet, 28/28
Launch-Kinder sauber, beide seriellen Ports frei. Die vor Ort erbetene
Bestätigung der physischen Ruhe und wieder wirksamen unabhängigen
Motorsperre wird getrennt nachgetragen. Recorder-Einschränkung:
`/near_field/status` fehlt im Bag, weil der Recorder ohne
`robot_interfaces`-Overlay gestartet wurde; es gab keinen aktiven
Kindzielteil, für den dieser Topic einen Fahrnachweis liefern müsste.
Lokale Belege: `active-bag/`, `control-events.jsonl`,
`active-live-binding.json`, `resolved-explore-params.yaml` und
`run-analysis.json` im genannten Testverzeichnis.

**Genau nächster Auftrag:** Gerätefrei und eng begrenzt den aktiven
No-Scan-Produktpfad aus diesem einen Bag darauf prüfen, warum
`portal_memory` in allen 249 Statusbildern stale bleibt, und den
gleichzeitigen Explorer-eigenen HWT-Terminalbefund gegen die vorhandenen
Roh-/Fusion-Zeitreihen abgrenzen. Erst nach einer nachweisbaren Auflösung
beider Startblocker einen erneuten begrenzten Kindzielversuch entscheiden;
aus diesem Lauf keine automatische Wiederholung. Keine neue allgemeine
Inventur und keine Änderung von Frische- oder Sicherheitsgrenzen.

**Historisch: motorloser Kindziel-Vorlauf ohne Initialscan am 28.09. —
TESTFALL NICHT AUSGELÖST.** Der bereits real bestandene HWT-Initialscan
wurde nicht wiederholt. Ausschließlich lokal liegt unter
`~/.local/share/amadeus/tests/hwt-child-noscan-20260928/` das vom
unveränderten Recovery-Profil abgeleitete Einmalprofil
`hwt-child-no-initial-scan.yaml` (SHA256
`a5e6b1d08041b3f63bb1fcd2b7730b709194fbe210426770f1ff759d2e70dcd6`).
Tatsächlich geladene Parameter: `initial_scan_enabled=false`,
`wohnungserkundung_navigation_enabled=true`, Portal/Coverage/Rückkehr
aus, `max_frontier_goals=1`, `max_failed_goals=1`; HWT-, Encoder-, TF-,
VL53-, Collision-, Geschwindigkeits-, Stillstands- und Recoveryparameter
unverändert. Das erste lokale Profil setzte einen inaktiven Portalzähler
auf null; der Explorer lehnte diesen Wert schon beim Start als nicht
positiv ab. Nur im lokalen Profil wurde der ursprüngliche positive
Zähler wiederhergestellt, Portalquerung blieb deaktiviert. Kein
Produktcode und kein Repository-Profil geändert.

Beim korrigierten zweiten Start über `app_mapping.launch.py` mit
`active_drive=false`, `enable_auto_explore=true` waren FC03, HWT/Yaw,
Fusion-Quellen, Karte/TF und beide VL53-Frames motorlos gesund. Das
Scope war in der Runtime aktiv; sein lokaler Bindungsbeleg
`live-binding-v2.json` nennt Map-Fingerprint `c36de5da…` und aktuelle
Startpose. Der maximale Abstand der vier Profil-Ecken vom aus dieser
Live-Pose erneut berechneten Bereich betrug 0,0028 m. Der Produktauftrag
ging durch Mission Manager und BT, aber der Explorer endete in rund
1,3 s sicher mit `hwt601_readonly_preflight_no_motion`. Die Policy
meldete zuletzt 20 offene und 5 geeignete Frontier-Aufgaben, jedoch
`goal_candidate=unavailable` / `navigation_dispatched=false`. Das Bag
`motorless-product-bag-v2` enthält null Nav2-Status-/Feedbacknachrichten,
null Nichtnull-`/cmd_vel_nav` und keine `/cmd_vel`-Nachricht. Damit
ist **nicht** belegt, dass der Produktpfad ohne Initialscan kein Ziel
finden könnte; die frühere Read-only-Bewegungssperre verhinderte bereits
die Kindziel-Freigabe. Kein manuelles Ziel, keine HWT-Injektion, keine
Fahrt. `verification-summary.json` hält den Befund lokal fest.
Recorder und Stack wurden beendet, der zweite Start mit 28/28
sauber abgeschlossenen Kindern, Geräteports frei; aktiver Install
unverändert. Die Kartenbindung ist nach Shutdown nicht mehr live.

**Historischer Folgeschluss:** Die Forderung „aktives autonomes Kind bereits
im motorlosen `active_drive=false`-Vorlauf“ ist mit dem unveränderten
HWT-Produktgate nicht erfüllbar. Der neue Auftrag korrigiert genau diese
Reihenfolge. Der Read-only-Stopp ist kein HWT-Fehler und wird nicht durch
eine weitere identische motorlose Explore-Mission wiederholt.

**Historischer zweiter motorloser Vorlauf am 28.09.: Quellen BESTANDEN, Scope lokal
gebunden, Fahrtest NICHT gestartet.** Nach aktueller Bestätigung, dass die
Controller für FC03 erreichbar und die Motorendstufe weiterhin unabhängig
gesperrt ist, wurde derselbe unveränderte PR-#105-Quellstand isoliert in
`~/.local/share/amadeus/tests/hwt-child-scope-20260928-retry/install`
neu gebaut (24 Pakete, keine Produktdatei geändert). Das lokale
`runtime-manifest-passive.json` zeigt das Recovery-Profil bytegleich zum
früheren Realstand und die korrigierten HWT-/Gate-Module mit denselben
Hashes. `active_drive=false`, `enable_auto_explore=false`, keine Mission:
FC03-Encoder bereit und ohne Latch, HWT-Rohdaten/Yaw bereit,
Fusion `sources_ready=true` bei `readonly_preflight_no_motion`, Karte/TF
frisch, beide VL53-Frames technisch gesund, Safety-E-Stop false.

Ein **neues**, nur lokal gespeichertes Einmalprofil
`hwt-child-scope-map-52d498d9.yaml` (SHA256 `f26c1e67…`) verwendet
Scope-ID `we1-hwt-child-20260928-retry-52d498d90043` und die aktuelle
Map-Identität `52d498d9…`. Pose und Polygonkoordinaten bleiben in
`scope-binding.json` lokal; das alte Polygon wurde nicht verwendet. Die
bestätigte Geradeausfläche wurde konservativ relativ zum Start mit
Vorwärtsgrenze 2,0 m, rechter Grenze 0,9 m, linker Grenze 0,7 m und
gepadderter hinterer Footprintkante −0,13 m abgebildet; 0,5 m Auslauf
bleiben außerhalb des Fahr-Scope reserviert. Der gerade 0,45-m-Korridor
liegt geometrisch vollständig mit gepaddertem Footprint im Polygon.
Eine **nur planende** Nav2-`ComputePathToPose`-Probe erzeugte 30 Posen
innerhalb des Scope, aber 0,494 m Pfadlänge und damit mehr als die
festgelegten 0,45 m; sie ist kein autonomes Frontier-Kind und kein
zulässiges Testziel. In der aktuellen Rohkarte waren nahe der Startpose
noch unbekannte Zellen, ab etwa 0,30 m die gerade Rasterspur frei.

Die Produktparameter verlangen vor einem autonomen Kind einen 360°-
Initialscan. Die bisherige Vor-Ort-Freigabe beschreibt Vorwärts- und
Seitenraum, nicht den für den dabei geschwenkten Footprint nötigen freien
Bereich hinter der Startpose. Dafür wurde eine aktuelle Bestätigung
angefragt, aber noch nicht erhalten. Deshalb kein Fahrstart und keine
HWT-Injektion. Das Profil war im passiven Stack nicht aktiv; nach dessen
Stopp ist die Kartenbindung historisch und muss in einer künftigen
Runtime vor Bewegung neu geprüft werden. Der Shutdown endete mit 28/28
Kindern sauber; Ports frei, aktiver Install unverändert.

**Damals nächster Auftrag:** Den rückwärtigen freien Schwenkraum für den
vorgesehenen Initialscan vor Ort bestätigen. Danach denselben begrenzten
Kindzielversuch erst bei frischer Karten-/Scope-Bindung und einem vom
Produktpfad selbst erzeugten Ziel mit höchstens 0,45 m Route ausführen;
sonst ohne Störung beenden.

**Historischer erster passiver Scope-Vorlauf am 28.09.: nicht bestanden, keine Fahrt.**
Auf Quellstand `247ed49` wurden 24 Pakete isoliert unter
`/tmp/we1-pr105-20260928-install` gebaut; das festgelegte BT-Submodul und
das unveränderte Recovery-Abnahmeprofil wurden aufgelöst. Das lokale
Runtime-Manifest liegt unter
`~/.local/share/amadeus/tests/hwt-child-scope-20260928/runtime-manifest-passive.json`.
Motorendstufe unabhängig gesperrt, Stillstand und Beobachter waren vor dem
Start bestätigt. Der Produktstack lief ausschließlich mit
`active_drive=false`, `enable_auto_explore=false`, ohne Mission oder
Motorbefehl. Karte und `map→base_link` erschienen frisch; lokaler
Map-Fingerprint `a363c30a…`, Startpose und neues, allein aus der aktuellen
Vor-Ort-Freigabe abgeleitetes Polygon stehen **nur lokal** in
`scope-geometry-candidate.json`. Das Profil
`hwt-child-scope-pending.yaml` verwendet eine neue Scope-ID und kein altes
Polygon, bleibt aber `accessible_scope_verified=false`: Der FC03-Encoderleser
verriegelte `encoderkonfiguration_ungueltig` nach ausbleibender Antwort,
Fusion meldete `wheel_missing_stale_or_invalid` / `sources_ready=false`.
Der Beobachter bestätigte anschließend, dass die unabhängige Motorsperre
hier auch die Controllerelektronik trennt; eine FC03-Prüfung unter dieser
Sperre ist im aktuellen Aufbau daher nicht möglich. Die fehlende Antwort
ist damit vereinbar, beweist aber allein keinen Software- oder
Encoderdefekt. Zudem waren im ersten 0,45-m-Vorwärtskorridor 32 von 272 geprüften
Kartenpunkten unbekannt; eine vollständig freie digitale Route ist nicht
belegt. Das ist kein bestandener motorloser Fahr-Preflight und aktiviert
die vorab genannte Fahrfreigabe nicht. Der Stack ist beendet, alle
protokollierten Kinder und seriellen Handles sind frei; aktiver Install
unverändert. Ein erneuter Stackstart erzeugt eine neue Kartenbindung, daher
ist dieses Einmalprofil dafür nicht unverändert verwendbar.

**Damals nächster Auftrag:** Eine vor Ort überprüfbare Trennung von
gesperrter Motorendstufe und erreichbarer Controllerelektronik für den
FC03-Encoder-Vorlauf herstellen. Erst damit
den neuen motorlosen Karten-/Scope-/Routennachweis auf einer frischen
Kartenbindung ausführen. Keine Fahrt, solange diese Voraussetzung und
der digital freie Zielkorridor fehlen.

**Entscheidungsfähige Kindziel-Abnahmevorlage:** AGENTENAUFTRAG Abschnitt 5
legt Produktpfad, Zielidentität, genau eine 0,25-s-HWT-Leserpause,
Aufzeichnung, Erfolg und Gegenfälle sowie 340 s Gesamtdauer, 35 s ab
aktivem Kind, 0,60 m gemessene Translation und die vorhandenen
0,10-/0,12-m/s- und 0,25-rad/s-Geschwindigkeitsgrenzen fest. Kein
manuelles Nav2-Ziel und kein synthetischer Task zählen. Nach vollständigem
Initialscan muss die Produktpolicy ein **eigenes** offenes Frontier-Task,
einen aktuellen Zielkandidaten und eine Route von höchstens 0,45 m in der
bestätigten freien Kurzstrecke liefern. Altes Kind terminal, Elternauftrag
und Task erhalten, Quellen/Stillstand/Pose/Route erneut geprüft, Gate-ACK
und höchstens ein neues Kind sind die Erfolgskriterien.

**Historischer Freigabeentscheid vor dem passiven Vorlauf am 28.09.:
NO-GO für einen sofortigen Fahrstart.**
Der bisherige Lauf endete vor dem vollständigen Initialscan:
`open_tasks=0`, `goal_candidate=unavailable`, `navigation_dispatched=false`.
Das letzte Abnahmeprofil (SHA256 `ee3b42ee…`) hat
`accessible_scope_verified=false` und eine leere Scope-ID. Damit entsteht
im Frontierpfad `scope=None`; die unveränderte Produktlogik kann dennoch
einen Kandidaten bilden. Das ist **kein** Beleg für eine autorisierte
Fahrstrecke. Der Nutzer bestätigte am 28.09. eine aktuell freie
Geradeausstrecke, kennt aber deren Dokumentpfad nicht. Die lokale Suche
fand als jüngsten passenden historischen Scope das Profil
`~/.local/share/amadeus/profiles/stage3-real-20260925-after-r2-scope.yaml`
(SHA256 `74c14c2d5a37a7ebc6f7e84206deba2ff6d7197135a4ab31b4772530917451a5`),
Scope-ID `stage3-local-scope-20260925-after-r2`, Session
`stage3-20260925-after-r2`, vier Polygonecken und
`accessible_scope_verified=true`. Der Diagnoselauf
`stage3-hwt601-motion-20260926T105410Z.jsonl` band ihn an den
Map-Fingerprint `4f17785f…`. Der jüngere HWT-Lauf
`hwt-recovery-real-20260927-fxU0To/motorless-observation.json` (27.09.,
22:42 Uhr) meldet dagegen Session `hwt601-parity-20260926` und Map-ID
`map-90b3fcce…`; sein installiertes Abnahmeprofil hat Scope-Verifikation
aus und eine leere ID. Das alte Profil enthält selbst keinen Map-Fingerprint.
Somit ist der historische Polygonbeleg vorhanden, aber seine Bindung an die
aktuelle Karte und die bestätigte Geradeausstrecke fehlt. Weder Profil-Hash
noch Aussage über freie Vorwärtsfahrt übertragen die alten Koordinaten in
den heutigen Kartenframe. Reale Koordinaten bleiben lokal.

Auch die beim bestandenen Rundblick tatsächlich aufgelösten temporären
Präfixe `/tmp/we1-full-shim-install`, `/tmp/we1-hwt-recovery-install` und
`/tmp/we1-hwt-yaw-install` existieren aktuell nicht mehr. Der damals
installierte Profilpfad ist heute nicht vorhanden. Die Quellbasis
`6b666d97…` bleibt nachvollziehbar (seitdem nur Dokumentänderungen),
aber ein **heute installierter** Kindziel-Testkandidat ist nicht
manifestiert. Weder Root-Arbeitskopie noch aktiver Install wurden
umgeschaltet. Diese beiden konkret fehlenden Belege — aktuelle
Karten-/Scope-/Zielbindung und erneut aufgelöste Runtime — verhindern
eine positive Freigabe. Ein früherer Rundblick oder ein manuell gesetztes
Nav2-Ziel ersetzt sie nicht.

**Damals nächster Auftrag:** Die aktuell freie Geradeausstrecke ab der
aktuellen Startpose mit Endpunkt und seitlicher Begrenzung im beim Versuch
laufenden Kartenframe vor Ort markieren/bestätigen und als neues lokales,
kartenidentitätsgebundenes Einmalprofil dokumentieren; den PR-#105-Kandidaten isoliert erneut
manifestieren und das Profil mit Sicherheitsquellen motorlos prüfen. Erst
danach den in Abschnitt 5 bereits festgelegten Einzelversuch separat zur
konkreten Fahrfreigabe vorlegen. Ein autonomes Kindziel kann nach dem
echten Initialscan **im später freigegebenen Lauf** entstehen; ohne ein
gültiges Ziel wird vor der Injektion abgebrochen. Dieser Dokumentationsauftrag
startet weder Geräte noch Fahrt, TOR 2, Merge oder Installwechsel.

Der vollständige Vorgängerstatus ist byteidentisch unter
[STATUS-Snapshot bei 40b5b49](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_40b5b49.md)
erhalten (Git-Blob `6d4092f11880f19f2f0052be940910ced526bb15`, 145845 Bytes).
Der ältere [M3/U-Snapshot](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md)
bleibt ebenfalls erhalten. Historische Aufträge sind keine aktuellen
Freigaben. Der Masterplan ändert sich nur mit expliziter Grundentscheidung.
