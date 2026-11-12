# arm_bringup — Messdaten statt Vorgabewinkel

Dieses erste Paket installiert ausschließlich zwei JSON-Inventare, keine
Launchdatei und keinen automatischen Hardwarestart.

- [arm_inventory.json](config/arm_inventory.json): sechs noch nicht zugeordnete
  Gelenke. Typ, Busadresse, Firmware, Messwerte und Referenzdaten bleiben null.
  joint1 bis joint6 sind Erfassungsplätze, keine bestätigte URDF-Zuordnung.
- [synthetic_arm.json](config/synthetic_arm.json): ausdrücklich erfundene
  Testgeräte und Adressen, nur für --mode fake. Keine Hardwarekonfiguration.

Bekannt sind fünf ESS17-RS07 und ein NEMA23 mit noch offenem genauem Modell.
Welche Gelenke welche Motoren und Busadressen haben, ist noch nicht bestätigt.
Daher wird selbst dem ersten Gelenk kein NEMA23 und keinem Gelenk eine reale
Adresse voreingestellt.

JSON wurde gewählt, damit Konfigurationsprüfung/Fake ohne zusätzliche YAML-
oder ROS-Abhängigkeiten laufen. Das strikte Schema steht in
[config.py](../arm_hardware/arm_hardware/config.py). Unbekannte Schlüssel und
NaN/Infinity werden abgewiesen. Nicht bekannte Werte immer null lassen.
Ein gemessener Homing-Offset ist eine Konfigurationsgröße; die aktuelle
Referenzgültigkeit muss der spätere Laufzeitcontroller gesondert verwalten.

Die drei Pakete können gezielt mit folgendem Befehl gebaut werden:

~~~bash
colcon build --packages-select arm_hardware arm_tools arm_bringup
~~~

Keinen bestehenden Roboterstart erweitern, bis die Arm-Abnahmestufen erfüllt sind.
Details und Bedienung: [arm_tools](../arm_tools/README.md).
