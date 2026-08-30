# Modulare Sensor-Fusion fuer Amadeus und Nachfolger

**Stand:** 30.08.2026

**Paket:** `src/robot_state_estimation`

**Status:** motorlos mit echten Jetson-, Encoder- und OAK-IMU-Daten abgenommen;
Fahr- und Bodenstoerungstests stehen noch aus

Dieses Dokument beschreibt nicht nur die aktuelle Konfiguration. Es ist der
Schnittstellenvertrag fuer den naechsten Roboter und fuer spaetere Sensoren.
Roboterspezifische Treiber und Messwerte bleiben an den Raendern; die
Vertrauenslogik und der eigentliche Zustandsschaetzer bleiben austauschbar.

## 1. Ziel und klare Grenzen

Die lokale Fusion soll kontinuierlich die Bewegung des Fahrwerks im
`odom`-Bezug liefern. Sie soll insbesondere verhindern, dass eine einzelne
unzuverlaessige Quelle unbemerkt die Karte verzieht.

Sie soll:

- Radencoder und IMU kombinieren;
- fehlende, alte oder ungueltige Daten sichtbar machen;
- den beim Start gemessenen Gyro-Nullfehler korrigieren;
- Radschlupf nur mit einer **radunabhaengigen** Quelle erkennen;
- gekippte 2D-LiDAR-Scans waehrend Fugen- und Schwellenereignissen sperren;
- neue lokale Bewegungssensoren ohne Umbau des Kerns aufnehmen koennen;
- genau einen Besitzer fuer jeden dynamischen TF-Uebergang erzwingen.

Sie soll bewusst nicht:

- `cmd_vel` als angeblich gemessene Bewegung verwenden;
- aus einem Fahrbefehl Bewegung erfinden, wenn der Roboter festhaengt;
- SLAM oder Schleifenschluesse ersetzen;
- `map->odom` publizieren;
- Motoren, Hub oder andere Aktoren ansteuern;
- unsichere Messungen durch frei erfundene Ersatzwerte kaschieren.

## 2. Datenfluss und TF-Zustaendigkeit

```text
hardware-/roboterspezifisch              stabile, portable Schnittstellen

Motorencoder -> /wheel/odom_raw ----+
                                      +-> sensor_adapter -> /fusion/wheel_odom --+
OAK/andere IMU -> /oak/imu/data ------+                                        |
                                             +-------> /fusion/imu --------------+--> lokaler EKF
                                                                                       |
LiDAR/VIO/Bodenfluss -> /fusion/reference_odom -> Konsistenzpruefung ------------------+--> /odom
                                                                                             + odom->base_link

/scan_normiert + /fusion/imu -> scan_quality_gate -> /scan_qualitaet -> SLAM/Lokalisierung
                                                                        |
                                                                        +--> map->odom
```

Verbindlicher TF-Vertrag:

| Uebergang | Einziger Besitzer | Begruendung |
|---|---|---|
| `base_link -> sensor_frame` | URDF / statischer Publisher | vermessene Montage |
| `odom -> base_link` | lokaler EKF | kontinuierliche lokale Bewegung |
| `map -> odom` | SLAM oder Kartenlokalisierung | globale Korrektur und Wiedererkennung |

Der Encoder-Treiber publiziert im Fusionsbetrieb deshalb auf
`/wheel/odom_raw` und mit `publish_tf=false`. Zwei Publisher fuer
`odom->base_link` oder `map->odom` sind ein harter Konfigurationsfehler.

## 3. Vier getrennte Schichten

### 3.1 Treiber

Treiber lesen Hardware. Sie duerfen herstellerspezifisch sein, sollen aber
Zeitstempel, Frame und Rohmessung unveraendert und nachvollziehbar liefern.
Ein Treiber entscheidet nicht selbst, wie stark der EKF ihm vertraut.

### 3.2 Sensoradapter

Adapter sind die einzige roboterspezifische Grenze der Fusion. Sie:

- pruefen Zeitstempel, endliche Werte und erwartete Frames;
- wandeln auf ROS-Standardnachrichten um;
- tragen gemessene oder konservative Kovarianzen ein;
- korrigieren nur explizit kalibrierte, nachvollziehbare Fehler;
- publizieren weder TF noch Aktorkommandos.

Der aktuelle `sensor_adapter` behandelt Encoder und IMU. Ein neuer Sensor
muss diesen Knoten nicht erweitern, wenn sein Treiber bereits den unten
beschriebenen Standardvertrag erfuellt.

### 3.3 Qualitaet und Vertrauen

Qualitaetslogik bleibt ausserhalb des EKF. Dadurch ist sichtbar, **warum**
eine Quelle gerade weniger Gewicht erhaelt.

- `GyroBiasEstimator` wartet beim Start den ersten thermischen Uebergang ab
  und misst danach den IMU-Nullfehler. Ein langsamer Tiefpass fuehrt den Bias
  nur weiter, wenn frische Encoderdaten Stillstand bestaetigen. Bei Bewegung
  bleibt der letzte gute Wert eingefroren. Bis zur Anfangskalibrierung sowie
  bei einem geglaetteten Restoffset ueber der Profilgrenze wird keine
  korrigierte IMU publiziert; der Status degradiert sichtbar.
- `MotionConsistencyMonitor` vergleicht Radgeschwindigkeit und eine
  radunabhaengige Bewegung. Zwei schlechte Proben markieren Schlupf; gute
  Proben loesen ihn erst mit Hysterese. Das Radgewicht wird ueber die
  Kovarianz reduziert, nicht durch eine erfundene Bewegung ersetzt.
- `scan_quality_gate` lernt die lokale Schwerkraftrichtung unabhaengig von
  der geneigten Kameramontage. Es laesst ebene Translation und Gierbewegung
  zu, sperrt aber kurzzeitig Roll-/Nick-, Stoss- und Beruhigungsphasen.
- Die optionale LiDAR-Odometrie verwendet keine Radvorhersage, keinen TF und
  keine Befehle. Bei zu wenig Geometrie oder Mehrdeutigkeit publiziert sie
  nichts.

Status steht maschinenlesbar auf:

| Topic | Inhalt |
|---|---|
| `/sensor_fusion/status_json` | Frische, Zaehler, IMU-Bias, Schlupfzustand, Radgewicht |
| `/sensor_fusion/scan_quality_json` | stabil/gesperrt, Ursache, Scan-Zaehler |
| `/sensor_fusion/lidar_odometry_json` | Guete und Zaehler der optionalen Referenz |
| `/diagnostics` | standardisierte ROS-Diagnose fuer Betriebsueberwachung |

### 3.4 Zustandsschaetzung

Der Filter ist `robot_localization`, nicht ein projektspezifischer Eigenbau.
Damit bleiben Filtermathematik, Zeitbehandlung und TF-Verhalten gepflegte
ROS-Komponenten.

Das erste Amadeus-Profil fusioniert:

- Encoder: Vorwaertsgeschwindigkeit, Giergeschwindigkeit und die
  Nicht-Seitwaerts-Bedingung des Differentialantriebs;
- OAK-IMU: kalibrierte Giergeschwindigkeit.

Encoderpose und Encodergeschwindigkeit stammen aus denselben Zaehlimpulsen.
Sie werden nicht gleichzeitig fusioniert, weil das dieselbe Messung doppelt
zaehlen wuerde. OAK-Orientierung und -Beschleunigung bleiben aus, bis Bias,
Rauschen und Temperaturverhalten real vermessen sind. Das Magnetfeld wird in
Innenraeumen nicht als verlaessliche absolute Richtung vorausgesetzt.

## 4. Standardvertrag fuer neue Sensoren

### Lokale Bewegung: `nav_msgs/Odometry`

Geeignet fuer Radencoder, visuelle Odometrie, LiDAR-Odometrie, Radar oder
optischen Bodenfluss.

- `header.stamp`: Messzeit, monoton und nicht null;
- `header.frame_id`: lokaler Ursprung der Quelle, niemals `map` vortaeuschen;
- `child_frame_id`: `base_link` oder ein dokumentierter Fahrwerksframe;
- Twist muss im Child-Frame gelten;
- nur wirklich gemessene Achsen mit endlicher, positiver Kovarianz belegen;
- unbekannte Achsen im EKF-Profil deaktivieren;
- kein `odom->base_link`-TF aus dem Adapter.

Eine Quelle fuer Schlupferkennung muss physikalisch unabhaengig von den
Antriebsraedern sein. Aus Encoderwerten abgeleitete Zweit-Odometrie ist keine
unabhaengige Referenz.

### Inertialsensor: `sensor_msgs/Imu`

- Nachricht bleibt im physischen IMU-Frame;
- statischer TF zum `base_link` ist Pflicht;
- unbekannte Orientierung wird mit `orientation_covariance[0] = -1` markiert;
- Null-Kovarianz darf nicht versehentlich „perfekt“ bedeuten;
- Achsrichtung und Einheit werden vor jeder Fusion mit einem manuellen
  Links-/Rechts-Drehtest bestaetigt.

### Globale Positionsquelle

UWB, GNSS, Marker oder Kartenwiedererkennung gehoeren nicht ungeprueft in den
kontinuierlichen lokalen Filter. Sie korrigieren eine getrennte globale
Schicht beziehungsweise `map->odom`. So verursacht ein globaler Sprung keinen
Sprung in der lokalen Regelschleife.

### Abstandssensoren

VL53, Ultraschall und einzelne ToF-Strahlen sind primaer Sicherheits- und
Hindernissensoren. Ohne belastbares Bewegungsmodell sind sie keine
Odometriequelle. Sie bleiben deshalb ausserhalb des Pose-EKF.

## 5. Profile statt Umbau

Roboterspezifisch sind nur:

1. Topicnamen und erwartete Frames in einem Adapterprofil wie
   `config/amadeus.yaml`;
2. die statischen Sensor-TFs im URDF;
3. gemessene Kovarianzen und Qualitaetsgrenzen;
4. die aktivierten Achsen im EKF-Profil;
5. die Launch-Datei, die Treiber startet und TF-Besitz eindeutig setzt.

Der portable Kern liegt in `quality_core.py` und `planar_scan_matcher.py` und
kennt weder ROS-Nachrichten noch Amadeus-Hardware. Fuer Roboter 2 wird das
Paket kopiert oder als eigenes Repository eingebunden; anschliessend wird ein
neues Profil neben `amadeus.yaml` angelegt. Eine Sensorerweiterung wird zuerst
auf einem neuen Topic im Beobachtungsmodus betrieben.

Empfohlene Stufen fuer jede neue Bewegungsquelle:

1. **observe:** Daten, Zeit, Frame, Kovarianz und Ausfaelle nur protokollieren;
2. **monitor:** gegen die bestehende Schaetzung vergleichen, aber nicht
   fusionieren;
3. **deweight:** bei bestaetigtem Widerspruch nur das Vertrauen der
   abhaengigen Quelle senken;
4. **fuse:** erst nach allen Akzeptanztests als eigenes EKF-Input aktivieren;
5. **required:** erst nach bewiesenem Ausfallverhalten zum Missionskriterium
   machen.

Diese Reihenfolge verhindert, dass ein neuer Sensor durch scheinbar gute
Momentanwerte sofort die einzige produktive Odometrie beschaedigt.

## 6. Konfigurationsprofile

| Datei | Zweck | Freigabestatus |
|---|---|---|
| `config/amadeus.yaml` | Topics, Frames, Bias- und Qualitaetsgrenzen | motorlos abgenommen |
| `config/hwt601_driver.yaml` | read-only HWT601-RS485-Treiber | synthetisch getestet, Hardware ausstehend |
| `config/amadeus_hwt601.yaml` | alternative HWT601-Quelle und vorlaeufige Biasgrenzen | nur Entwurf bis Realmessung |
| `config/ekf_encoder_imu.yaml` | Encoder + OAK-Gierrate | motorlos abgenommen |
| `config/ekf_encoder_imu_reference.yaml` | zusaetzlich radunabhaengige Geschwindigkeit | erst nach Realabnahme |

Der optionale lokale LiDAR-Matcher ist standardmaessig aus. Er ist keine
zweite SLAM-Instanz: Er haelt nur einen kleinen lokalen Referenzscan und dient
als unabhaengiger Kurzzeit-Bewegungsmesser. Spaeter kann OAK-VIO oder ein
optischer Bodensensor dasselbe `/fusion/reference_odom` liefern.

Der geplante `HWT601-AGV-485` folgt derselben Reihenfolge. Sein Treiber liest
nur Modbus-Funktion 0x03 auf einem eigenen USB-RS485-Adapter und publiziert
`/hwt601/imu/data_raw` im physischen Frame `hwt601_link`. HWT-Orientierung
wird nicht verwendet. Bis Skala, Achsen, statischer Montage-TF, Zeitverhalten
und Kovarianzen am gelieferten Sensor gemessen sind, bleiben Adapter, EKF und
Scan-Gate in seinem motorlosen Validierungslaunch standardmaessig aus. Die
OAK ist dort ebenfalls aus und wird nur fuer einen begrenzten Vergleich
zugeschaltet. Einbau- und Abnahmefolge: `docs/HWT601_INTEGRATION.md`.

## 7. Abnahme in sieben Stufen

Jede Stufe muss einzeln protokolliert werden. Eine bestandene spaetere Stufe
ersetzt keine fruehere.

| Stufe | Aufbau | Bestehenskriterium |
|---|---|---|
| A | rein synthetisch | Unit-, Vertrags- und Buildtests gruen |
| B | Jetson, Motorpfad hart gesperrt | Topics frisch, Bias kalibriert, genau ein lokaler TF-Besitzer |
| C | mindestens 5 min Stillstand | Position bleibt stehen; Gierdrift und Kovarianz innerhalb festgelegter Grenze |
| D | aufgebockte Raeder | Vorzeichen, Zeitverzug und Ausfall jeder Quelle stimmen |
| E | glatter Boden | Gerade, Drehung und kombinierter Weg gegen aeussere Referenz messen |
| F | Fuge/Schwelle/Teppich | Kipp-Scans werden gesperrt; radunabhaengige Quelle erkennt Schlupf |
| G | Kartierung und Lokalisierung | weniger Artefakte, kein TF-Konflikt, reproduzierbare Zielpose |

Fuer D bis G gelten die Hardware-Sicherheitsregeln aus `AGENTS.md`: frische
persoenliche Freigabe, freier Weg und erreichbarer Hard-Not-Aus. Dieses
Dokument ist keine Fahrfreigabe.

Vor dem Produktionswechsel muessen zusaetzlich Sensor- und Filterausfaelle
getestet werden: IMU abziehen, LiDAR abziehen, Zeitstempel stoeren,
Referenzquelle verlieren und Neustart im bewegten Zustand verweigern. Der
Filter darf dabei degradieren, aber nicht still falsche Sicherheit melden.

## 8. Aktuell gemessener Stand vom 30.08.2026

Der erste lange motorlose Lauf zeigte, dass eine einzelne 2-s-Biasmessung
nicht genuegt. Obwohl Encoderposition, Frames und Datenraten stabil waren,
verschob sich der OAK-Gyro-Nullpunkt nach der Kalibrierung weiter. Ueber
615,7 s integrierte das korrigierte Rohsignal zu `-49,24 Grad`; die EKF-Gierlage
wanderte um `-43,33 Grad`. Das formale 329,4-s-Fenster der Stufe C war bereits
mit `-23,91 Grad` klar durchgefallen.

Eine Wiedergabe der Rohdaten wurde fuer Zeitkonstanten von 0,5 bis 10 s
ausgewertet. Gewaehlt wurden konservative 5 s, weil die Nachfuehrung damit den
simulierten Fehler auf `-0,46 Grad` begrenzte, ohne eine echte langsame Drehung
so aggressiv wie kuerzere Konstanten zu absorbieren. Das Profil verwendet nun:

- 15 s zusammenhaengenden encoderbestaetigten Stillstand als Einlaufzeit;
- danach 5 s und mindestens 1.000 Proben fuer die Anfangskalibrierung;
- 5 s Zeitkonstante fuer Nachfuehrung nur bei Stillstand;
- 1 s Zeitkonstante fuer den Restfehler und `0,001 rad/s` als Sperrgrenze;
- 2 s unterhalb der Grenze vor der erneuten Freigabe.

Der reale Wiederholungslauf zeichnete 342,5 s auf, davon 330,8 s nach der
ersten Freigabe. `x` und `y` blieben exakt 0, die EKF-Gierlage aenderte sich um
`-0,090 Grad` und die korrigierte IMU integrierte zu `-0,058 Grad`. Der
Restoffset lag im Median bei `0,000145 rad/s`, im 95-%-Quantil bei
`0,000615 rad/s`. Eine einzelne Driftphase erreichte `0,001214 rad/s`; der
Adapter sperrte die IMU 3,5 s, wartete weitere 2,0 s zur Erholung und meldete
danach wieder bis Testende nominal. Der EKF ueberbrueckte diese Phase mit der
stillstehenden Radodometrie, ohne Positionsbewegung zu erzeugen.

Auf `/tf` gab es genau den dynamischen Uebergang `odom->base_link` sowie die
statischen OAK-Sensorframes. Der Basisstart blieb hart auf `dry_run=true`,
`allow_rs485=false`, `publish_tf=false`, `rs485_ready=false`, 0 m/s und 0 rpm.
Damit ist Stufe C bestanden. Der Test beweist weiterhin keine korrekte
Biassperre waehrend realer Bewegung und keine Beherrschung von Bodenfugen;
dafuer fehlen Stufen D bis F.

## 9. Start und Rueckfall

Der sichere Validierungsstart kann ueber kein Launchargument scharf gestellt
werden:

```bash
ros2 launch robot_bringup state_estimation_validation.launch.py
```

Die reine Fusionsschicht startet selbst keine Hardware:

```bash
ros2 launch robot_state_estimation fusion.launch.py
```

Produktionsumschaltung erfolgt erst nach der Fahrabnahme:

- Basis-Odometrie auf `/wheel/odom_raw`;
- `base_hardware.publish_tf=false`;
- EKF-Ausgabe auf `/odom`, `publish_tf=true`;
- SLAM-Eingang auf `/odom` und `/scan_qualitaet`;
- Missionsstart nur bei frischem, bereitem Fusionsstatus.

Rueckfall ohne Motorregister- oder Kalibrierwertaenderung:

1. Fusionslaunch beenden;
2. bisherigen Basisstart mit `/odom` und `publish_tf=true` verwenden;
3. SLAM wieder direkt auf `/scan_normiert` setzen;
4. pruefen, dass nur Basis und SLAM ihre bisherigen TF-Uebergaenge besitzen.

Das Paket schreibt keine Motorkonfiguration, keine Karte und keine
Kalibrierdatei ausserhalb des Workspace. Das installierte Systempaket
`ros-humble-robot-localization` ist die einzige neue Laufzeitabhaengigkeit.

## 10. Offene Arbeit

- Bias-Einfrierung und Achsvorzeichen zuerst mit aufgebockten Raedern pruefen;
- weiteren Temperaturbereich und Neustart nach bereits warmer OAK messen;
- realer Geradeaus- und Drehtest des Defaultprofils;
- Fugenfahrt mit Roh-IMU, Encoder, LiDAR-Gate und externer Beobachtung;
- reale Abnahme und Kovarianzkalibrierung der unabhaengigen LiDAR-Odometrie;
- danach erst Umschaltung der Kartierungs- und Navigationsstarts;
- fuer Roboter 2 bevorzugt eine tiefer und steifer montierte IMU nahe dem
  Chassisschwerpunkt sowie eine radunabhaengige Bewegungssicht nach unten oder
  per VIO vorsehen.
- gelieferten HWT601 zuerst nur lesen und gegen
  `docs/HWT601_INTEGRATION.md` abnehmen; vor vermessenem TF und Kovarianzen
  weder EKF noch Scan-Gate darauf umschalten.
