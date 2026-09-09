# HWT601-AGV-485: Einbau und gestufte Inbetriebnahme

**Stand:** 09.09.2026

**Nachtrag:** USB-Installation, 600-s-Stillstand und die extern beobachtete,
vom Nutzer bestaetigte 180-Grad-Skalenpruefung sind erfolgt. Ein Faktor-zwei-
Fehler ist verworfen; keine Skalenhalbierung. Der isolierte Gyro-Z-
Schattenpfad ohne Odometrie, TF oder Aktoren hat inzwischen auch seinen warmen
600-s-Stillstand bestanden. Details: `HWT601_SHADOW.md`. Eine Produktions-
oder Kartenfreigabe ist das noch nicht.

**Vorheriger Softwarestatus:** vorbereitet und synthetisch getestet. Der Nutzer hat den
HWT601 montiert; sein CH340-USB-Adapter ist sichtbar, aber Kernel-Treiber und
gezielte udev-Korrektur sind noch systemweit zu installieren. Konkreter
Befund, Installationsbefehl und Rueckfall stehen in
[HWT601_USB_INBETRIEBNAHME.md](HWT601_USB_INBETRIEBNAHME.md).
Der HWT bleibt bis zur abgeschlossenen Abnahme eine
Beobachtungsquelle und ist in keinem Produktionsstart aktiv.

Diese Vorbereitung gilt fuer die **RS485-Variante HWT601-AGV-485**. Vor dem
Anschliessen muss das Typenschild genau diese Schnittstelle bestaetigen. Eine
TTL- oder RS232-Variante funktioniert nicht an dem vorbereiteten
USB-RS485-Pfad.

## 1. Warum ein eigener HWT-Pfad

Die OAK bleibt als Kamera und Vergleichssensor nutzbar. Ihre IMU sitzt jedoch
hoch, ist mit der Kamera 18,94 Grad nach unten geneigt und wird durch die OAK-
Elektronik thermisch beeinflusst. Software kann die bekannte Neigung per TF
korrekt behandeln; sie kann aber weder den hohen, mechanisch unguenstigeren
Messort noch jede temperatur- und vibrationsabhaengige Drift beseitigen.

Der HWT wird deshalb tief und steif am Chassis montiert. Fuer Stillstands-,
Temperatur- und Ausfalltests darf die OAK aus bleiben. Sie wird nur fuer einen
zeitlich begrenzten A/B-Vergleich eingeschaltet. Das reduziert Waermeeintrag
und trennt die Fehlerursachen, ohne die Kamera dauerhaft aufzugeben.

## 2. Elektrik und USB-RS485

Laut Herstellerseite hat der HWT601-AGV standardmaessig eine Versorgung von
9–36 V; einzelne Anschlussgrafiken nennen 5–36 V, waehrend 5-V-Ausfuehrungen
als kundenspezifisch beschrieben werden. Deshalb gilt verbindlich: **Spannung
vom Typenschild und dem mitgelieferten Datenblatt verwenden, niemals 5 V
annehmen.** Ein normaler USB-RS485-Adapter versorgt den Sensor nicht.

Die veröffentlichte Kabelfarbbelegung lautet:

| Farbe | Signal |
|---|---|
| Rot | VCC, Spannung erst nach Typenschildpruefung |
| Schwarz | GND |
| Gelb | RS485 A |
| Gruen | RS485 B |

Empfohlen ist ein **eigener galvanisch getrennter USB-RS485-Adapter** mit
eindeutiger Seriennummer. Der jetzt angeschlossene CH340 hat keine individuelle
Seriennummer; er wird deshalb an seinen vermessenen USB-Steckplatz gebunden.
Eine galvanische Trennung des gelieferten Adapters ist nicht bestaetigt.
Der HWT darf weder elektrisch noch softwareseitig
am Motorbus `/dev/ttyUSB_BASE` haengen. Die Versorgung wird passend zum
Sensortyp abgesichert; A/B oder Versorgung werden nur spannungsfrei
umgeklemmt. Schirmung, Signalbezug und Abschlusswiderstand richten sich nach
den Unterlagen des gelieferten Sensors und Adapters.

Nach dem Einstecken des noch unbeschalteten USB-Adapters werden seine Merkmale
nur lesend erfasst:

```bash
cd /home/p/roboter_ws
python3 tools/sensorfusion/hwt601_usb_pruefen.py /dev/ttyUSBX
```

Das Werkzeug verweigert den bekannten Motoradapter. Nur wenn VID, PID und eine
eindeutige Seriennummer vorliegen, gibt es eine konkrete udev-Regel aus. Die
Vorlage `docs/83-hwt601.rules.example` darf mit ihren Platzhaltern nicht
installiert werden. Nach manueller Installation muss der Sensor ausschliesslich
unter `/dev/ttyUSB_HWT601` erscheinen.

## 3. Mechanischer Einbau und Frame

- steif am Roboterboden, moeglichst nahe Antriebsachse/Chassismitte;
- nicht auf duennem, schwingendem Blech und nicht direkt neben Motor,
  Schrittmotortreiber oder DC/DC-Wandler;
- Kabel mit Zugentlastung, ohne Kraft auf Sensor oder Stecker;
- aufgedruckte Sensorachsen vor dem Verschrauben fotografieren und notieren;
- Position und Orientierung relativ zu `base_link` nach dem Einbau messen.

Der Treiber publiziert unveraendert im physischen Frame `hwt601_link`:
`x/y/z` sind also die Achsen des Sensors, nicht automatisch vorwaerts/links/
oben. Der statische TF `base_link -> hwt601_link` wird erst mit den gemessenen
Werten in die Roboterbeschreibung aufgenommen. Es existiert absichtlich kein
Identitaets-TF als Platzhalter. Ohne diesen TF bleiben EKF und Scan-Gate aus.

## 4. Vorbereitete Software

Der Treiber fragt per Modbus RTU ausschliesslich die sechs Register ab

```text
0x34..0x36  AX, AY, AZ
0x37..0x39  GX, GY, GZ
```

und implementiert nur Funktion `0x03` (Holding Register lesen). Er sendet
keine Schreib-, Kalibrier- oder Speicherbefehle. CRC, Adresse, Funktion,
Laenge und Saettigung werden streng geprueft; ungueltige Pakete erzeugen keine
IMU-Nachricht. Nach drei Fehlern wird die Schnittstelle geschlossen und
begrenzt neu verbunden.

| Schnittstelle | Bedeutung |
|---|---|
| `/hwt601/imu/data_raw` | `sensor_msgs/Imu`, SI-Einheiten, Sensorframe |
| `/hwt601/status_json` | Verbindung, Frische, Rate, Fehlerzaehler |
| `/diagnostics` | standardisierte Diagnose |

Die Orientierung ist immer explizit unbekannt
(`orientation_covariance[0] = -1`). Die Datenblattskalierung `+/-4 g` und
`400 Grad/s` Vollbereich ist konfigurierbar. Gravitation und Gyro-Skala sind
am gelieferten Sensor plausibilisiert; die bestaetigte externe 180-Grad-
Gegenprobe schliesst insbesondere den Faktor zwei aus. Nur das isolierte
Shadow-Profil verwendet `5,0e-7 (rad/s)^2` als Weissrauschersatz aus dem
warmen 600-s-Stillstand. Das allgemeine HWT-Profil bleibt bis zur
Produktionsabnahme bei `0.02`. Beschleunigungskovarianz, Kaltstart, Temperatur
und Motorvibration bleiben ungemessen.

## 5. Inbetriebnahme nach Lieferung

Alle Schritte bis einschliesslich 5.4 sind motorlos. Motorstrom bleibt aus,
der Roboter liegt ruhig und kann nicht rollen.

### 5.1 Sicht- und Verdrahtungspruefung

1. Modell, RS485-Suffix, Versorgungsspannung und Kabelfarben gegen die
   Lieferunterlagen pruefen.
2. Eigenen isolierten USB-RS485-Adapter identifizieren und den eindeutigen
   udev-Alias einrichten.
3. Mit ausgeschalteter Versorgung Durchgang, Polaritaet und A/B kontrollieren.
4. Erst dann Sensor versorgen; Motor-RS485 bleibt unverbunden.

### 5.2 Nur Rohdaten, ohne OAK und ohne Fusion

```bash
cd /home/p/roboter_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch robot_state_estimation hwt601.launch.py
```

In einem zweiten Terminal:

```bash
ros2 topic echo --once /hwt601/status_json
ros2 topic hz /hwt601/imu/data_raw
ros2 topic echo --once /hwt601/imu/data_raw
```

Bei keiner Antwort zuerst Adresse `80`, Baudrate `115200`, Versorgung und
Adapter pruefen. A/B nur spannungsfrei tauschen. Nicht mit Hersteller-
Konfigurationssoftware "auf Verdacht" schreiben; abweichende Adresse oder
Baudrate wird erst dokumentiert und dann im YAML-Profil angepasst.

### 5.3 Skala und Achsen

1. Ruhend muss der Betrag der Beschleunigung ungefaehr `9,81 m/s²` sein;
   vorlaeufiger Toleranzbereich `9,3..10,3 m/s²`.
2. Jede Achse einzeln nach oben halten. Vorzeichen und Betrag dokumentieren.
3. Positive Basis-Gier ist gegen den Uhrzeigersinn von oben. Die Skala wurde
   inzwischen mit einem vom Nutzer visuell bei etwa 180 Grad gestoppten Lauf
   gegen HWT und zwei unabhaengige LiDAR-Auswertungen geprueft.
4. Fuer Gyro-Z wird die bekannte Achsrotation direkt angewendet. Ein exakter
   Chipursprung wird weiterhin nicht als statischer TF erfunden.

Weicht die Beschleunigungsnorm ungefaehr um Faktor 2 oder 4 ab, wird nicht
"zurechtkalibriert": Zuerst Firmware/Registerkarte und Vollbereich des
gelieferten Modells klaeren. Die konfigurierbaren Skalen dienen der
nachvollziehbaren Anpassung, nicht dem Kaschieren eines falschen Protokolls.

### 5.4 Motorloser Langzeit- und Schattentest

```bash
AMADEUS_HWT601_STILLSTAND=JA \
  bash tools/sensorfusion/start_hwt601_shadow.sh
```

Dieser Start besitzt ueberhaupt keinen Basistreiber und damit auch keinen
synthetischen Null-Odom-Strom, der faelschlich als Encoderstillstand gelten
koennte. Er startet weder OAK, LiDAR, EKF noch TF und verwendet nur eigene
`/shadow/hwt601/*`-Topics. Der erforderliche Launchwert darf nur bei
tatsaechlichem Stillstand gesetzt werden. Nach 15 s Einlauf und 10 s
Kalibrierung wird der Bias fest eingefroren. Das bisherige motorlose
Bringup-Validierungslaunch bleibt fuer Architekturtests erhalten, ist aber
nicht mehr der Abnahmepfad fuer einen physisch bestaetigten HWT-Bias.

Abnahmedaten bleiben lokal. Aufzuzeichnen sind mindestens Kaltstart,
30 Minuten Warmbetrieb, Datenrate, groesste Luecke, Beschleunigungsnorm,
Gyro-Mittelwert/-Streuung und integrierte Gier. Vorlaeufig gelten bei 100-Hz-
Abfrage mindestens 80 Hz, keine Luecke ueber 0,10 s und weniger als 1 Grad
Gierdrift in 10 ruhigen Minuten nach dem Einlaufen. Grenzwerte und die noch
fehlenden Temperatur-/Vibrationsanteile werden anschliessend aus den echten
Daten festgelegt. Die erste Ruheauswertung und ihre reproduzierbare
Berechnung stehen in `HWT601_SHADOW.md`.

### 5.5 Erst spaeter: EKF und Bewegung

Ein eigener Schatten-EKF folgt erst mit echter Encoderodometrie und bleibt auf
`/shadow/hwt601/odom` sowie `publish_tf=false` begrenzt. Der produktive EKF und
`start_scan_gate:=true` bleiben bis zur vollstaendigen Abnahme aus. Der erste
weitere Bewegungstest folgt wieder den Stufen aus
`docs/SENSOR_FUSION_ARCHITEKTUR.md`: aufgebockte Raeder, dann glatter Boden,
erst danach Fugen/Schwellen. Jede Aktorpruefung braucht eine neue persoenliche
Freigabe, freien Weg und erreichbaren Not-Aus.

## 6. Quellen und offene Punkte

- Herstellerproduktseite: <https://wit-motion.com/index.php/AGV/74.html>
- Herstellerreferenz fuer das High-Precision-Modbus-Protokoll:
  <https://github.com/WITMOTION/WitHighModbus_HWT9073485>

Noch offen bis zur Produktionsabnahme: dokumentierte Typenschildspannung,
exakter Chipursprung (nur fuer Beschleunigung relevant), Kaltstart,
Temperaturdrift, Motor-/Bodenvibration, Beschleunigungskovarianz und die echte
Encoder-HWT-Schattenfusion. Modbus-Rohdaten, Achsen, Gravitation,
Gyro-Vorzeichen/-Skala sowie warmes Ruherauschen sind inzwischen gemessen.
