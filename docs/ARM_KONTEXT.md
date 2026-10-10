# Amadeus-Arm: Einstieg für Agenten

Stand: 10.10.2026. Diese Datei bündelt die im Gespräch bestätigten Fakten,
aktuellen Softwarepfade und offenen Messungen. Vor Änderungen zusätzlich
[AGENTS](../AGENTS.md), [Projektgedächtnis](PROJECT_MEMORY.md) und
[Inventar](INVENTORY.md) lesen. Entwicklung und reale Erprobung getrennt halten.

## Aktuelle Fakten

- Sechs Achsen: fünf ESS17-RS07 und ein NEMA23. NEMA23-Modell,
  Gelenkzuordnung, Busadressen und Busparameter sind noch nicht bestätigt.
- Keine Bremsen; Getriebeselbsthemmung ist vorgesehen, unter Last sowie bei
  Versorgungs-/Kommunikationsverlust aber noch zu prüfen.
- Kein zusätzlicher Armcode außerhalb dieses Repos.
- Homing mit TLE4905L vorgesehen. Elektrische Einbindung, Eingangsfunktion,
  Schaltposition, Wiederholgenauigkeit und Fehlerfälle müssen je Achse geprüft werden.
- Parallelgreifer noch nicht gebaut: DYNAMIXEL XL330, genaue Variante offen,
  M6- oder ähnlich große Trapezspindel noch nicht gewählt.
- Zwei ohmsche Drucksensoren vorgesehen, noch ohne Auswerteelektronik.
- OAK-D-S2 am Mast vorhanden. Eine Handkamera ist eine spätere,
  messungsabhängige Option.
- Erstes Ziel ist ausschließlich Arm-Inbetriebnahme. Flaschengreifen folgt
  nach Gelenk-, Greifer- und Kalibrierabnahme.
- Transportpose muss LiDAR, OAK und Nahbereichssensoren freihalten.
  stowed existiert als Missionsbegriff, aber noch ohne bestätigte reale Winkel.

## Aktuell gebaut

| Ablage | Bedeutung |
|---|---|
| [Build-Protokoll](ARM_BUILDPROTOKOLL.md) | Höchstens 200 Wörter je neuer Integration/Build |
| [arm_hardware](../src/arm_hardware/README.md) | Inventarschema, genaue FC03-Allowlist, Fake und serieller Leseadapter |
| [arm_tools](../src/arm_tools/README.md) | Explizite CLI, Prüfmodus/Fake/reale Rohdatenprobe |
| [arm_bringup](../src/arm_bringup/README.md) | Unbestätigtes Realinventar und klar getrennte Testkonfiguration |
| [Arm-CI](../.github/workflows/arm-commissioning.yml) | Offline-, Serial-Pseudo-Terminal-, Installations- und Humble-Prüfung |

Noch nicht implementiert: Aktorbefehle, Homingsteuerung, Referenzgültigkeit,
ros2_control, echtes Arm-URDF, Trajektorien, MoveIt, reale Arm-Actions,
Greifersteuerung und Fahrfreigabe über eine bestätigte Transportpose.
JSON-Diagnose ist kein ROS-ArmStatus und keine Bewegungsfreigabe.

## Verwandte Systeme

| Ablage | Bezug |
|---|---|
| [Integrationsplan](INTEGRATIONSPLAN_ARM_SOFTWARE.md) | Architektur und langfristige Schritte; siehe Gültigkeitshinweis unten |
| [robot_interfaces](../src/robot_interfaces) | MoveArmToNamed/MoveArmToPose; vorhandene öffentliche Verträge |
| [bt_orchestrator](../src/bt_orchestrator) | Missionsablauf, stowed/ready; keine physische Pose garantiert |
| [mock_servers](../src/mock_servers) | Simulierte Actions, niemals Nachweis realer Armbewegung |
| [robot_description](../src/robot_description) | TF-/Geometriebasis für späteres echtes Armmodell |
| [base_hardware](../src/base_hardware) | Fahrbasis mit ESS23; Register-/Countsergebnisse nicht pauschal auf Arm übertragen |
| [safety_monitor](../src/safety_monitor) | Plattformzustand; kein Ersatz für hardwired Not-Aus |
| [semantic_perception](../src/semantic_perception) | Reale OAK-Objektpose, RGB-D-Frische, Serveranbindung |
| [handeye_calibration](../src/handeye_calibration) | Bestehender Entwurf, erst nach echter Armgeometrie/Referenz prüfen |
| [OAK-Kalibrierkonzept](../KONZEPT_KALIBRIERUNG_OAK_ARM.md) | Historischer Konzeptstand, vor Ausführung TF/Montage/Mathematik prüfen |
| [Roboterübergabe](ROBOT_TRANSFER.md) | Isolierter Build, reale Abnahme und Rückfallweg |

## Stufen und nächste Messung

1. M0 / Build A: Messdatenschema, Offline-Tests, Fake und eng begrenzte
   ESS17-Leseprobe. Fehlende Werte bleiben null.
2. M1A: physische Motor-/Gelenk-/Adresszuordnung, Versorgung und Halteverhalten
   dokumentieren; danach einzelne beaufsichtigte Rohdatenabfrage.
3. M1B: getrennte Software für begrenzten Einzelachs-Jog, mit geprüften
   Stopwegen, lokaler Bewegungsfreigabe, gesperrter/stillstehender Basis
   und konkreter Vor-Ort-Freigabe. Diese Sperren gelten vor der ersten Bewegung.
4. M2: Homing, Drehrichtung, Übersetzung, getrennte Command-/Feedback-Counts,
   Nullpunkt, Winkelgrenzen und echte Gelenkrückmeldung.
5. M3/M4: Bustiming und koordinierte Trajektorien bei gesperrter Basis
   nachweisen; darauf aufbauend ros2_control/MoveIt und Arm-Actions.
   Plattform-Interlocks müssen vor Freigabe koordinierter Bewegung wirksam sein.
6. M5/M6: Greifermechanik, Endlagen, ADC/Signalaufbereitung, Kraft-/Kontakt-
   auswertung und Greifen an bekannter Position.
7. M7/M8: Kamera-Arm-Kalibrierung, Fehlerbudget, danach statisches Vision-Greifen.
8. M9/M10: geprüfte sensorfreie Transportpose, mobile Integration,
   Last-/Ausfall-/Dauertests.

Noch benötigte M1A-Daten: genauer NEMA23-Typ, Zuordnung aller Motoren zu Gelenken,
bestätigte IDs, dedizierter Adapter/Port, Baudrate/Parität/Stopbits sowie
Typenschild-/Verkabelungsnachweis. Nicht aus dem synthetischen Beispiel ableiten.

## Gültigkeit und Quellen

Der ältere Integrationsplan auf main nennt sechs ESS17 und alten externen
Foxy-Code. Diese Aussagen sind durch die obigen Nutzerangaben überholt.
Auch Beispielwerte wie Getriebe 50:1, IDs 1–6 oder vorgegebene Limits sind
keine gemessenen Hardwarefakten.

Die ausführlichen, im vorangehenden Planungsschritt lokal überarbeiteten
Plan-/Messblattdateien waren beim Beginn dieses Builds wegen des ausgefallenen
Arbeitsbereichs nicht erreichbar. Dieser GitHub-Branch enthält deshalb eine
eigenständige, aktuelle Kontextdatei. Bei Wiederherstellung die beiden
Dokumentstände vergleichen und zusammenführen; keine lokalen Änderungen verwerfen.

Hersteller-Leseprofil und genaue Fundstellen:
[arm_hardware README](../src/arm_hardware/README.md).
Homing-Elektrik vor Bau mit den Originaldatenblättern abgleichen:
[TLE4905L](https://www.infineon.com/assets/row/public/documents/24/49/infineon-tle49x5l-datasheet-en.pdf),
[ESS17-Hardwaremanual](https://files.omc-stepperonline.com/ESS17-RS0407_Series_Bus_Integrated_Motor_Hardware_Manual.pdf).
