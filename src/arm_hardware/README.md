# arm_hardware — Inbetriebnahme-Grundlage

Stand: 10.10.2026. ROS 2 Humble / Python 3.10. Reine Python-Bibliothek,
noch kein ros2_control-SystemInterface und kein Bewegungscontroller.

- Striktes, teilweise ausfüllbares Inventar mit sechs Gelenken, getrennten
  Command-/Feedback-Counts, Übersetzung, Homing-Offset und späteren Limits.
- Fehlende Messungen bleiben null. Unbekannte Felder, doppelte Adressen,
  Broadcast, ungültige Zahlen und doppelte JSON-Schlüssel werden abgewiesen.
- Unveränderliche Lesepläne, deterministischer Fake und FC03-Adapter.
- Separater serieller Kontext mit explizitem Port, endlichem Timeout, null
  Wiederholungen und geprüftem exklusivem pyserial-Lock.
- Rohwörter, Konfigurationsfingerprint, UTC-Snapshotzeit und monotone
  Lesedauer. Keine abgeleiteten Gelenkwinkel oder Referenzbehauptungen.

Das exklusive Lock koordiniert kooperierende Linux-Programme. Es ersetzt nicht
die Prüfung, dass alle anderen Busmaster beendet und keine zweiten Adapter
angeschlossen sind. Ein gelesener Bewegungsstatus beweist ebenfalls keine
sichere mechanische Stillsetzung.

## Freigegebenes Leseprofil im Code

Profil-ID: ess17-rs07-fc03-v1. Ausschließlich für physisch zugeordnete
ESS17-RS07; keine Übernahme für den noch unbekannten NEMA23.

Quelle: STEPPERONLINE, [Modbus Series Bus Product Function Manual V1.0,
05.03.2025](https://files.omc-stepperonline.com/Modbus-Series-Bus-Product-Function-Manual-V1.0_1.pdf),
über die Downloads der [ESS17-RS07-Produktseite](https://www.omc-stepperonline.com/de/ess-serie-0-72nm-101-96oz-in-nema-17-integrierter-rs485-closed-loop-stepper-servomotor-24vdc-1000ppr-ess17-rs07).
Kapitel 3.2.1, gedruckte Seite 5: FC03, höchstens 16 Register.
Anhang 2, gedruckte Seiten 66–67 (PDF-Seiten 68–69): folgende Register sind RO.

| Start | Anzahl | Inhalt in Registerreihenfolge |
|---|---|---|
| 0x0000 | 4 | Modellcode, Firmware, Adresse, DIP |
| 0x0006 | 7 | Fehler, MotionStatus, Eingänge, Ausgänge, Position Wort 0/1, Drehzahl |

Die Lücke 0x0004/5 wird nicht gelesen. 0x0019, Kommandos, Konfiguration,
Reset und EEPROM sind nicht im Profil. Modellcodes werden roh ausgegeben;
ein Tabellen-Default ist kein Identitätsbeweis. Wortfolge, Einheiten und
Encoder-Nullpunkt werden nicht geraten. Die Leseprofilbestätigung vor Ort muss
Handbuch, Typenschild und vorhandenen Firmwarestand berücksichtigen.

## Tests ohne reale Hardware

Vom Repository-Root:

~~~bash
python3 -m pip install -r src/arm_hardware/requirements-modbus.txt
PYTHONPATH=src/arm_hardware:src/arm_tools python3 -m unittest discover -s src/arm_hardware/test -v
PYTHONPATH=src/arm_hardware:src/arm_tools python3 -m unittest discover -s src/arm_tools/test -v
~~~

Der Pseudo-Terminal-Test prüft den echten gepinnten Modbus-/Serialstack gegen
einen synthetischen FC03-Gegenpart, einschließlich CRC und exklusivem Lock.
Er öffnet kein physisches Gerät. CI baut zusätzlich die drei Pakete in ROS Humble.

Bedienung: [arm_tools](../arm_tools/README.md).
Inventar: [arm_bringup](../arm_bringup/README.md).
Kontext: [ARM_KONTEXT](../../docs/ARM_KONTEXT.md).
