# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus · Stand 27.09.2026 · Stufe 3 weiterhin OFFEN/GELB**

**Aktuelle Entscheidung:** Konsolidierung statt Komplettneubau. Maßgeblich sind
[MASTERPLAN.md v1.0](MASTERPLAN.md), die unveränderte
[WE-Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) und
[MEILENSTEINE.md](MEILENSTEINE.md). Dies ist der einzige laufende WE-Iststand.

## 1. Sofortiger Arbeitsfokus

**Nächster Auftrag:** Die konkrete Rohstatus-Prüfung hinter
`raw_driver_not_ready` im HWT-Readinesspfad sichtbar machen. Die vorhandenen
Logs und das Bag enthalten nur den zusammengefassten Fehler, keinen
HWT-Rohstatus. Deshalb zuerst eng begrenzte, rein diagnostische
Feldbeobachtung und einen motorlosen Vorlauf vorbereiten; keine
HWT-Wiederanfahrlogik implementieren, keine Frischegrenze ändern.
Arbeitsvertrag: [AGENTENAUFTRAG.md](AGENTENAUFTRAG.md).

Keine neue Wohnungsfahrt, kein kompletter Rewrite, kein OS-Neuaufbau, kein
automatischer Merge und kein aktiver Installwechsel. Die vorhandene
HWT-/VL53-Schutzwirkung bleibt fail-closed. Erst nach identifizierter
Einzelbedingung wird das erste Recoverypaket umgesetzt.

## 2. Konsolidierte Quell- und Buildbasis

| Bereich | Festgestellter Stand | Grenze |
|---|---|---|
| Verbindliche Dokumentreferenz | `docs/we1-masterplan-20260927`, Commit `26360001f65e05a5b88a58581771c241291fa0e5`; separat in einem Bare-Repository geholt | Der Root-Checkout blieb auf `main` (`23928d92…`); `git fetch` darin scheiterte an einer defekten lokalen Checkpoint-Ref. Der Dokumentbranch ist keine Roboter-Runtime. |
| Historischer HWT-/Türvergleich | `1d91229dc10ff4bb791938d49aae8e9808a5dfff` | Vergleichsbeleg und Rückfallreferenz, kein pauschaler Rollback. |
| Letzter veröffentlichter WE-Quellstand | PR #101 / `codex/we1-hwt601-fusion` bei `40b5b49c9a92600484a0dc85c466930bc1680c60` | Kein Beleg für ausgeführte Pakete oder lokalen Install. Der Masterplan-Commit hat dieselbe Quellbasis; sein Diff zu `40b5b49` betrifft nur Dokumentation. |
| Zuletzt verwendeter lokaler Parity-Bestand | `/home/p/roboter_ws-parity-reset`, Branch `feature/parity-reset`, HEAD `40b5b49…`; sieben veränderte getrackte Dateien plus `docs/WE_PARITY_RESET.md` und `src/explore/config/hwt601_parity_params.yaml` | Änderungen und Buildartefakte blieben unangetastet. Die Quelländerungen wurden in den neuen Integrationsworktree übernommen; im Ursprungsworktree waren sie uncommittet. |
| Neue Integrationslinie | `docs/we1-integrationsbasis-audit`, Worktree `/home/p/roboter_worktrees/we1-integrationsbasis-audit`, Start-Commit `2636000…`; Quelländerungen aus dem Parity-Worktree | Dokumentationsbasis plus festgehaltene lokale Kandidatenänderungen. Kein Deployment und keine Aussage, dass dieser Baum bereits auf dem Roboter lief. |
| Letzter dokumentierter Installkandidat | `~/roboter_ws-parity-reset/install_parity_real`; projektseitig als separates Overlay des 27.09.-Laufs beschrieben | Die gespeicherte Buildauswahl vom 27.09. 08:53 enthält nur `vl53_near_field`. Die tatsächlich gesourcte Präfixreihenfolge und Package-SHAs des aktiven Laufs sind nicht unabhängig protokolliert. `/home/p/roboter_ws/install` blieb laut Übergabe unverändert. |
| Host des frischen Builds | Ubuntu 22.04.5, `aarch64`, ROS 2 Humble, `/opt/ros/humble`, Python 3.10.12, GCC 11.4 | Host-/Buildumgebung, kein Beleg der Runtime-Auflösung des Realtests. |
| BT-Submodul | Gitlink `6c6aa078ee7bc52fec98984bed4964556abf5beb`; im neuen Worktree genau auf diesen SHA ausgecheckt | Im ursprünglichen Parity-Worktree war das Submodul nicht initialisiert. |
| Externer CH341A-Treiber | `vendor_ch34x_mphsi.repos` pinnt `f33863fbbf322a85f960b1701e7148db0b7b2d85` | Quell-/DKMS-Installationsstand auf dem Robotersystem wurde nicht geprüft. |
| Parity-Profil | `explore/config/hwt601_parity_params.yaml`; laut Kandidatenbericht 900 s, höchstens ein Portal und sechs Abdeckungsziele; aktive WE-Navigation bleibt aus | Profil-/Launchzuordnung des Realtests ist nicht im Bag enthalten; sie bleibt durch die Übergabedokumentation berichtet. |
| Motorbus / TF / Auftrag | Bestehender Bringup startet `base_hardware` einmal. Im Mappingprofil publiziert EKF `odom→base_link`, SLAM `map→odom`; Mission Manager/BT besitzen den äußeren Auftrag, Explorer sendet Nav2-Unterziele. | Quell-/Launchvertrag gelesen, aber Live-Knoten, TF-Publisher und Ziel-Handles wurden nicht gezählt. Keine zweite aktive WE-Navigation ergänzt. |

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
| Vollständiger frischer Colcon-Build, Standardumgebung | **BLOCKIERT** | `behaviortree_ros2` bricht im `behaviortree_cpp`-CMake-Export ab: das ROS-Paket sucht `libbehaviortree_cpp.so` unter `/opt/ros/humble/lib`, die installierte Datei liegt unter `/opt/ros/humble/lib/aarch64-linux-gnu/`. Ein explizites `CMAKE_LIBRARY_PATH` ändert den hardcodierten `NO_DEFAULT_PATH`-Suchpfad nicht. Folgepakete wurden nicht gebaut. Das ist ein Umgebungs-/Exportkonflikt, kein erfolgreicher Vollbuild. |
| Frischer isolierter Teilbuild | **BESTANDEN** | `colcon build --packages-up-to explore vl53_near_field`; sechs Pakete einschließlich `robot_interfaces`, `base_hardware`, `robot_state_estimation`, `vl53_near_field` und `explore`; Präfixe unter `/tmp/we1-target-install`. Kein lokales Install gesourct. |
| `explore`-Tests | **BESTANDEN** | 925/925; `/tmp/we1-target-build/explore/pytest.xml`. |
| Direkte gerätefreie Vertragstests | **BESTANDEN** | 86 Tests aus VL53, HWT-Health, Mission-Gate/Nav-Vertrag und Safety Monitor bestanden. Direkter Aufruf mit ROS-Humble-Python, getrennt vom Colcon-Testlauf. |
| Colcon-Testregistrierung `vl53_near_field` | **KEIN NACHWEIS** | `colcon test` meldete 0 Tests in diesem Paket. Die 86 obigen direkten Tests sind der Softwarebeleg für den ausgewählten Umfang. |
| Gesamtprozess, Bringup-/BT-Auflösung | **OFFEN** | Vollbuild stoppte vor Bringup. Kein isolierter Vollstackstart oder integrierter Missionsablauf ausgeführt. |
| Aktive Installation, Zielsystem und Hardware | **NICHT GEPRÜFT** | Neuer Installpräfix nicht aktiviert. Keine Roboterknoten, Aktoren, Geräte, Deployment- oder Fahrtests gestartet. |

Buildlogs: `/tmp/we1-integrationsbasis-log` (Vollbuild),
`/tmp/we1-target-log` und `/tmp/we1-target-test-log`; erfolgreiches
Teilbuildpräfix `/tmp/we1-target-install`. Diese temporären Artefakte sind keine
Runtime-Abhängigkeit.

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
Wiederherstellungsfunktion ist **OFFEN**, bis Originalfeld und tatsächlich
recoverbare Ursache belegt sind.

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

Genau ein nächster Schritt: die sechs HWT-Rohstatusprüfungen diagnostisch
einzeln sichtbar machen und vorhandene Tests dafür vorbereiten. Kein aktiver
Motorlauf und keine Wohnungsfahrt in diesem Diagnoseauftrag. Erst nach dem
Ergebnis wird über ursachenspezifische Recovery entschieden.

Der vollständige Vorgängerstatus ist byteidentisch unter
[STATUS-Snapshot bei 40b5b49](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_40b5b49.md)
erhalten (Git-Blob `6d4092f11880f19f2f0052be940910ced526bb15`, 145845 Bytes).
Der ältere [M3/U-Snapshot](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md)
bleibt ebenfalls erhalten. Historische Aufträge sind keine aktuellen
Freigaben. Der Masterplan ändert sich nur mit expliziter Grundentscheidung.
