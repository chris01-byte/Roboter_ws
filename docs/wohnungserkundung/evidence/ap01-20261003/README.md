# AP-01 – originale gerätefreie Softwarebelege

03.10.2026, Basis `08a4b9a`, Dokumentübernahme `84abfc6`, Software `c797442b37994f774df40b6b27d54c27efa3bdc3`. Auswertung und einziger aktueller Status: [STATUS](../../STATUS.md). Keine Zielsystem-/Fahrabnahme. `SHA256SUMS` belegt die gespeicherten Dateien.

`ap01-original-method-proof.json` liest per Python-Trace nur lokale Variablen aus dem unveränderten Original-`_poll()`; Poll-/Fehlerentscheidung wurde nicht nachgebaut/ersetzt. `ap01-before.log` ist der gewünschte Regressionstest vor Reparatur (erwartet rot); `ap01-repaired-method-proof.json` protokolliert echte reparierte Methoden aus dem Installpräfix. Clock/Transport/Serial sind synthetisch.

`ap01-run-final.sh` enthält den vollständigen abschließenden Build-/Testaufruf. ROS: `ros:humble-ros-base` Image-Digest `sha256:860e53793ccf575e5369b5e9a19939de2bfcfb46a299954d06f54f2af54fed19`, Ubuntu 22.04/x86_64, Python 3.10.12, pytest 6.2.5. Zusatzbindungen nav2_msgs/nav2_common stammen aus `ros-navigation/navigation2`, humble, SHA `3c3db59d6969d8ecee8e68468693d006397f4a0c`; nur diese Nachrichten-/Buildpakete, kein Navigator. SciPy/Serial/Pip aus Ubuntuquellen, Modbusrequirements aus Repository.

Containerpfade: `/repo` = `/workspace/Roboter_ws-ap01`, `/evidence` = `/workspace/scratch`. Unter `/evidence/ap01-{build,install,...}` liegen getrennte Artefakte; `/opt/ros/humble` liefert echte Standardnachrichten/rclpy. Container `ap01-ros`: keine Robotergeräte eingebunden, keine Verbindung zum Roboternetz; localhost, Domain 226. CI-/colcon-/pytest-Zahlen überlappen und werden nicht addiert.

Die JSON-Tiefenlogs stammen separat vom Host Python 3.12.14: 4 Tests, je 1 Fehler, vor und nach AP-01. Baselineprodukte/-test aus `git show 08a4b9a`, nachher unverändert bytegleich. Unter Humble/Python 3.10 besteht derselbe Test innerhalb der 443. Nicht gelöscht/übersprungen oder als Python-3.12-Erfolg gewertet.

Nicht maßgebliche Umgebungsanläufe wurden erhalten unter `/workspace/scratch`: zuerst fehlende ROS-Python-/Interfacepfade, dann unvollständige Zusatzpaketauswahl; abschließender Achtpaketbuild und vollständige Testauswahl sind hier separat gesichert. Kein ROS-EKF-/Gesamtrobotergraf gestartet; der erforderliche Zeitvertrag ist direkt mit echten Raw-/Transport-/Guard-/Health-Komponenten verbunden geprüft.
