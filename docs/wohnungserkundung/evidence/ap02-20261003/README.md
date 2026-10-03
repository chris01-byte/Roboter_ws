# AP-02 – gerätefreie Softwareevidenz, 03.10.2026

Basis `45f268a` (AP-01-Abschluss); Softwarecommit
`96bbd4d8ed6d0b7a3ca6816d7c5fae14c27f45d4`, Branch
`fix/map-lifecycle-source-contract`, isolierter Worktree
`/workspace/Roboter_ws-ap02`. Originalcheckout und AP-01-Worktree unverändert.
Plan weiterhin bytegleich MASTERPLAN v1.3. Kein Push/Merge, Deployment,
Hardwarezugriff oder automatischer AP-03-Übergang.

## Ergebnis und Belege

| Prüfung | Ergebnis | Originalausgabe |
|---|---|---|
| Gezielt isolierter Humble-Build | 10 Pakete erfolgreich | [Build](ap02-final-build.log) |
| Echte installierte Module / Paketpräfixe / Actions | Neues AP-02-Präfix; echte Humble-Bindungen | [Auflösung](ap02-installed-bindings.log) |
| Neue Lifecycle-Regressionsdatei plus bestehende metrische Regressionen gegen Installation | 116 bestanden, davon 55 neue AP-02-Fälle | [Installtests](ap02-installed-regressions.log) |
| Alle Explorer-, Fingerprint-, Map-Core-, State-/Base-Tests; betroffene reale Gate-/DDS-, Mission-/Commandtests | 1.587 bestanden | [Betroffene Tests](ap02-affected-tests.log) |
| Registrierte colcon-Tests für explore, map identity, map manager, state estimation und base hardware | 1.555 Tests, 0 Fehler/Fehlschläge/Skipped | [Ergebnis](ap02-colcon-results.log), [Lauf](ap02-colcon-tests.log) |
| Gegenprobe auf unverändertem AP-01-Stand mit neuer Testdatei | 30 erwartete Fehlschläge, 1 bestandener Fall, 24 abgewählte Fälle | [Baseline](ap02-baseline-regressions.log) |

Die Testmengen überlappen und dürfen nicht summiert werden. `colcon` führte
beim Kartenmanager nach Registrierung tatsächlich 53 Map-Core-Tests aus;
vorher lief dort nur ein leerer unittest-Aufruf. Die verbundene reale
Kartenmanager-/Explorer-Regressionsprüfung steht in der neuen Lifecycle-Datei.

Die Baselinegegenprobe verwendet Originalmodule aus `45f268a` und dieselben
realen ROS-Nachrichten; nur die Testdatei wurde hinzugefügt. Sie belegt u.a.
Broadcast-/Shapeausnahmen bei Wachstum, falsch gültige alte Evidenz,
Überschreiben des generischen Explorer-Kartenstands durch alte Callbacks,
aktive Ersatzjoins mit alter Revision, ignorierte Verarbeitungsfrische sowie
inkonsistente Produzentenzähler nach exakten Duplikaten. Ein erwarteter
Baselinefehlschlag hat Exitcode 1; die reparierte Fassung besteht alle 55 Fälle.

## Umgebung / Reproduktion

Ubuntu 22.04, ROS 2 Humble, Python 3.10.12, x86_64, lokale Dockerumgebung.
Versionen: [environment.txt](environment.txt). Offizieller ROS-Basisstand aus
AP-01: `ros:humble-ros-base`, Image-ID
`sha256:860e53793ccf575e5369b5e9a19939de2bfcfb46a299954d06f54f2af54fed19`.
Der lokale AP-02-Container übernimmt die in AP-01 installierten Testbibliotheken
und bekommt ausschließlich neue Repo-/Evidenzmounts. Lauf mit `--network none`,
`--init`, `ROS_LOCALHOST_ONLY=1`, `ROS_DOMAIN_ID=227`, ohne Geräte-Mounts.
Das Mounten der öffentlichen kombinierten CA aus der Cloudumgebung autorisiert
keinen Roboternetzkontakt; keine Netzwerkoperation im Prüflauf.

Benötigte echte Testbibliotheken: numpy/scipy/yaml/pytest/pyserial und
`src/base_hardware/requirements-modbus.txt`; Humble rclpy, Standardmessages,
tf2_ros, tf2_geometry_msgs, sensor_msgs_py und colcon. Keine Fake-ROS-Module.
Für die echten Nav2-Actions wurden `nav2_common` und `nav2_msgs` aus
`ros-navigation/navigation2`, Commit
`3c3db59d6969d8ecee8e68468693d006397f4a0c` (Humble), verwendet.
`robot_interfaces` entsteht aus dem aktuellen Repository.

Der vollständige ausgeführte Ablauf ist [ap02-verify.sh](ap02-verify.sh):
Repo unter `/repo`, Nav2-Quellen und getrennte Build-/Install-/Logpfade unter
`/evidence`; vor dem Build ausschließlich `/opt/ros/humble/setup.bash`, danach
das neue `/evidence/ap02-install/setup.bash`. Keine AP-01-Overlay-Sourcingzeile.
Die Importprüfung verlangt für alle betroffenen installierten Produktmodule
und Actions explizit das AP-02-Präfix. [Installed-Codevergleich](installed-code-sha256.txt)
bindet die installierten Implementierungen an die geprüften Quellen.

Gebaut werden diese acht Repositorypakete plus die beiden echten Nav2-
Interfacepakete: `amadeus_map_identity`, `robot_map_manager`, `explore`,
`mission_manager`, `robot_state_estimation`, `robot_interfaces`, `base_hardware`,
`robot_navigation`, `nav2_common`, `nav2_msgs`. Die expliziten `--base-paths`
bilden den betroffenen Softwareausschnitt ab. Es ist kein vollständiger
Nav2-/BT-/Hardwarelaunchbuild und keine Zielsysteminstallation.

Der anfängliche Build mit Discovery über das gesamte `src` scheiterte beim
Kartenmanager an nicht gebauten transitiven Launchpaketen (`bt_orchestrator`,
`safety_monitor`, `vl53_near_field`, `amadeus_lidar_bringup`, `robot_navigation`):
[ursprüngliche Ausgabe](ap02-build.log). Anschließend wurde der relevante
Python-/Interfaceausschnitt explizit entdeckt und wirklich gebaut, einschließlich
`robot_navigation`; keine Dummy-Pakete oder leeren Abhängigkeitspräfixe.
Externe Nav2-/BT-Ausführung wird hier nicht behauptet.

Die Baseline lässt sich im gleichen isolierten Container mit Originalquellen
aus `git archive 45f268a src/explore src/robot_map_manager`, der aktuellen neuen
Testdatei und entsprechend vorrangigem Original-`PYTHONPATH` reproduzieren:

```bash
python3 -m pytest -q --tb=short src/explore/test/test_metric_map_lifecycle.py \
  -k 'raster_transition or delayed_callback or same_stamp or new_content_requires or identical_content_pending or direct_egress or actual_map_producer or processing_time or final_mask_work or stamp_age_expires'
```

Das passende bestehende CI-Workflow `hwt601-we.yml` ergänzt die fehlenden
Identity-/Kartenmanager-/Interface-/Mission-Trigger, echte Nav2-Testbindings,
den gezielten Paketausschnitt und den Pytest-Aufruf. Das lokale Rezept ist
geprüft; ein GitHub-Actions-Lauf wurde nicht ausgelöst. Die bestehende
unittest-only Semantic-Workflowauswahl wird nicht als Nachweis der neuen
Pytest-Funktionen verwendet.

## Grenzen und Rückfall

Karten-/Quellenvertrag: [QUELLENVERTRAG](../../QUELLENVERTRAG.md).
Aktive/passive Budgets und Beobachter getrennt; AP-01 unverändert. Keine neue
Freiraumannahme, kein vergrößerter Timeout, keine Geometrie-/Controller-/Frontier-
Integration aus AP-03/AP-04. Der bereits in AP-01 belegte Python-3.12-JSON-
Baselinefehler liegt außerhalb dieser Humble/Python-3.10-Abnahme und bleibt
unverändert dokumentiert; kein pauschaler Hosttest-Gesamterfolg.

Aktive Jetson-Worst-Case-Zeiten, wirkliche Sensor-/TF-/Stopppfade, Startgeometrie
und Hardwareabnahme bleiben offen, insbesondere AP-06. Revert ausschließlich
Softwarecommit `96bbd4d` und die dazugehörige AP-02-Abschlussdokumentation;
AP-01 erhalten, keine fremde Arbeit oder Main/Jetson rücksetzen.

Originaldateien (einschließlich erwarteter Baselinefehler): [SHA256SUMS](SHA256SUMS).
