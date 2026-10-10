# arm_tools — explizite Erstdiagnose

Das Werkzeug startet weder Motoren noch ROS-Nodes. Standard ist die reine
Konfigurationsprüfung; Fake und reale Rohdatenprobe sind ausdrücklich getrennt.
Es gibt keinen automatisch gewählten Gerätepfad und keinen Adressscan.

## Ohne Hardware beginnen

Vom Repository-Root, ohne ROS-Installation:

~~~bash
PYTHONPATH=src/arm_hardware:src/arm_tools python3 -m arm_tools.cli \
  --config src/arm_bringup/config/arm_inventory.json

PYTHONPATH=src/arm_hardware:src/arm_tools python3 -m arm_tools.cli \
  --config src/arm_bringup/config/synthetic_arm.json --mode fake
~~~

Nach isoliertem Colcon-Build funktioniert derselbe Aufruf als
ros2 run arm_tools arm_probe. Den installierten Konfigurationspfad liefert
ros2 pkg prefix arm_bringup, Unterverzeichnis share/arm_bringup/config.

Ausgabe: JSON, eine Zeile je Snapshot. source unterscheidet hardware/synthetic,
motion_permitted bleibt immer false. Exitcode 0 bedeutet erfolgreiche
Validierung/Abfrage, 1 einen Diagnosefehler, 2 fehlerhafte Konfiguration oder
Verbindung, 130 Abbruch. Syntax-/Hilfemeldungen stammen von argparse.
Ein Diagnosefehler stoppt den gesamten Lauf; bereits gelesene Rohwerte im
Bericht bleiben als einzelne erfolgreiche Transaktionen erkennbar.
Ein Snapshot ist keine zeitgleiche Aufnahme aller sechs Achsen.

## Spätere reale M1A-Probe — vor Ort vorbereiten

1. Motorlosen Softwaretest abschließen; Arm mechanisch sichern und
   Hardware-Not-Aus/Versorgung mit der anwesenden Person klären.
2. Eigenen Arm-Bus bestätigen. Alle anderen Master/Programme beenden;
   Fahrbasisadapter nicht verwenden. Keine parallele zweite Busverbindung.
3. Eine Kopie von arm_inventory.json außerhalb des Repos anlegen.
   Pro zuerst einzelner ESS17-Achse Typenschild, physische Zuordnung und
   Busadresse bestätigen. motor_model = ESS17-RS07,
   read_profile = ess17-rs07-fc03-v1, device_id = bestätigte Adresse.
   identity_evidence beschreibt die tatsächlich geprüfte Zuordnung.
   Die Firmware und alle noch ungemessenen Kalibrierwerte dürfen null bleiben.
4. Baudrate, Parität und Stopbits aus der Gerätekonfiguration bestätigen.
   Nur diese Werte verwenden. Die CLI kann keine Einstellungen umprogrammieren.
5. Hersteller-Leseprofil mit vorhandenem Modell/Firmware abgleichen;
   die beiden Bestätigungsflags dokumentieren diese Prüfungen, keine Bewegung.

Aufrufschema, Platzhalter vor Ausführung durch geprüfte Werte ersetzen:

~~~text
ros2 run arm_tools arm_probe \
  --config /absoluter/pfad/zum/geprueften-inventar.json \
  --mode readonly --joint BESTAETIGTER_GELENKNAME \
  --port /dev/BESTAETIGTER_ARM_ADAPTER \
  --baudrate BESTAETIGTE_BAUDRATE --parity BESTAETIGTE_PARITAET \
  --stopbits BESTAETIGTE_STOPBITS --samples 1 \
  --confirm-bus-exclusive --confirm-profile-reviewed
~~~

Kein kopierfertiger Livebefehl mit angenommenen Adressen/Busraten.
--joint darf wiederholt werden, nachdem jede ausgewählte Identität geprüft ist.
--samples ist auf 1–100 begrenzt; --timeout auf 0,05–2 Sekunden.
Für die Erstprobe eine einzelne Achse und einen Snapshot verwenden.
JSON-Ausgabe lokal speichern und anschließend gemeinsam auswerten.

Eine erfolgreiche FC03-Antwort beweist weder Homing, korrekte Übersetzung,
Selbsthemmung noch eine sichere Transportpose. Bei Kommunikationsausfall
schließt die Probe den Port; sie kann und darf keinen Motorhalt garantieren.
Bewegung, Homing und Stopsteuerung gehören in einen eigenen späteren Build.
