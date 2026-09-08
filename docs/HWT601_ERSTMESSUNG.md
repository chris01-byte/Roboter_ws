# HWT601: erste reale Rohdatenabnahme, 08.09.2026

Software: `2fcda93`, Branch `fix/hwt601-usb-commissioning`.
Der Nutzer hat den vorbereiteten USB-Installer lokal ausgefuehrt.
`/dev/ttyUSB_HWT601 -> ttyUSB0`, Treiber `ch341`, CH340 `1a86:7523` am
vermessenen Steckplatz bestaetigt. `brltty-udev.service` ist inaktiv; der
Desktop-Brailleprozess besteht weiter. Motor/OAK/EKF wurden nicht gestartet,
keine Sensor-Konfigurations- oder Kalibrierregister geschrieben.

## Messfolge und Ergebnis

1. Zwei Sekunden nur lauschen bei 115200 Baud: keine unaufgeforderten Bytes.
2. FC03, Adresse 80, AX..GZ ab Register 0x34, fuenf Sekunden: 500 gueltige
   Antworten, null Fehler, rund 100 Hz. Keine Baud-/Adresssuche notwendig.
3. Messskript mit 15 s Einlaufzeit und 60 s Auswertung: 6.000 gueltige
   Antworten, null Fehler, 99,99988 Hz, maximale Luecke 0,013850 s.
4. Separater ROS-Rohdatenstart: 822 IMU-Nachrichten empfangen, etwa
   100,17 Hz am Subscriber, maximale Empfangsluecke 0,01924 s.
   Letzter Treiberstatus: `ready=true`, `raw_data_ready=true`,
   `fusion_ready=false`, null verworfene Antworten, eine Verbindung.
   Nachrichten tragen `hwt601_link`, streng steigende Zeitstempel und
   `orientation_covariance[0]=-1`; alle Beschleunigungs-/Gyrowerte endlich.
   Launch mit einem SIGINT an den Elternprozess sauber beendet.

ROS-Pruefung ausschliesslich in prozesslokaler DDS-Domain 61 mit Localhost-
Peer. Keine System-Netzwerkkonfiguration geaendert. Statuszaehler und Anzahl
empfangener Nachrichten wurden zu unterschiedlichen Zeitpunkten erfasst.

## Statistik des 60-Sekunden-Laufs

Die Skalierung bleibt die bisherige Annahme: +/-4 g und 400 Grad/s Vollbereich.
Die Beschleunigungsnorm betraegt im Mittel **9,88344 m/s²**, Minimum
9,87494 und Maximum 9,89409 m/s². Damit ist die Beschleunigungsskala plausibel,
jedoch weder praezise kalibriert noch die separate Gyroskala bestaetigt.

| Groesse | Sensor-X | Sensor-Y | Sensor-Z |
|---|---:|---:|---:|
| Beschleunigung Mittel [m/s²] | 0,020424 | -0,026179 | 9,883380 |
| Beschleunigung Standardabweichung [m/s²] | 0,001896 | 0,001675 | 0,002531 |
| Gyro Mittel [rad/s] | 0,00144446 | 0,00671102 | 0,000112776 |
| Gyro Standardabweichung [rad/s] | 0,00042534 | 0,00044284 | 0,00010930 |
| Unkorrigiertes Gyrointegral ueber 60 s [Grad] | 4,9651 | 23,0669 | 0,38760 |

Dies sind **Rohdaten ohne Biasabzug**, keine gemessene Karten-/EKF-Drift.
Insbesondere die X/Y-Nullpunktabweichungen werden nicht als echte Bewegung
interpretiert oder verschwiegen. Die Konzentration der Beschleunigung auf
Sensor-Z deutet auf etwa waagerechte Montage hin, beweist aber keinen
vollstaendigen Montage-TF und keine Ausrichtung zur Roboterfront.
Der Lauf ist kein dokumentierter Kaltstart und kein 10-/30-Minuten-Drifttest.

## Noch offen, keine Fusionsfreigabe

- Foto/Angabe der aufgedruckten X/Y/Z-Achsen relativ zur Roboterfront und
  vermessene Lage relativ zu `base_link`; kein Identitaets-TF erfinden.
- Separater, abgesicherter +/-90-Grad-Test fuer Drehrichtung und Gyroskala.
- Biasabzug und laengerer Warm-/Kaltstarttest; keine automatischen Aenderungen
  an Sensorkalibrierung, Biasparametern oder Kovarianzen aus dieser Minute.
- USB-Abzieh-/Wiederansteck- und Neustarttest; moegliches Wiederanlaufen von
  brltty durch andere USB-Geraete bleibt gesondert zu pruefen.
- Motor-/LiDAR-USB-Pfade bleiben ausserhalb dieser IMU-Abnahme.

Alle gestarteten Mess-/ROS-Prozesse beendet. Rueckfall unveraendert:
HWT-Rohdatenstart nicht aktivieren; fuer die Systeminstallation der
manifestgebundene Rueckfall aus `HWT601_USB_INBETRIEBNAHME.md`.
