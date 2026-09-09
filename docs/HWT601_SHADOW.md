# HWT601: isolierter Gyro-Z-Schattenpfad

**Stand:** 09.09.2026

Der extern beobachtete 180-Grad-Lauf ist nach ausdruecklicher Bestaetigung des
Nutzers als Skalen- und Vorzeichenpruefung akzeptiert. HWT, unabhaengige
LiDAR-Auswertungen und die visuelle Chassisausrichtung stimmen mit rund
178 Grad ueberein. Es gibt deshalb keine Skalenhalbierung. Die frueheren
45-Grad-Beobachtungen bleiben als nicht reproduzierbarer Widerspruch
dokumentiert; ihr genauer Aufbaufehler ist rueckwirkend nicht bestimmbar.

Diese Stufe schaltet die IMU noch nicht in Kartierung oder Navigation. Sie
erzeugt einen strikt getrennten Beobachtungspfad:

```text
HWT601, nur Modbus FC03
  /shadow/hwt601/imu/data_raw        [hwt601_link]
                    |
                    v
  einmaliger Startbias, danach fest eingefroren
  bekannte Montage Rz(-90 Grad), nur Gyro-Z
                    |
                    v
  /shadow/hwt601/imu/yaw_rate       [base_link]
```

Der Sensor sitzt mit X nach rechts, Y nach vorne und Z nach oben. Daher gilt
`x_base=y_sensor`, `y_base=-x_sensor`, `z_base=z_sensor`. Fuer die reine
Giergeschwindigkeit ist der um etwa 84 mm versetzte, im Gehaeuse nicht exakt
bekannte Chipursprung ohne Einfluss. Es wird deshalb kein falscher
`base_link -> hwt601_link`-TF erfunden. Orientierung, Beschleunigung sowie
Gyro X/Y werden im abgeleiteten Signal nicht als nutzbare Messungen angeboten.

## Gemessene Ruhekovarianz

Ausgewertet wurde die bestehende 600-s-Datei
`bias-20260908-230201/samples.csv` mit 59.993 Proben bei 99,987 Hz. SHA-256:
`350c52407752dea2594bf91bdb02e8ced465a15008250dc60d50f8e7e3627269`.
Die Datei bleibt lokal und wird nicht ins Repository aufgenommen.

Empirische Gyro-Kovarianz im Sensorframe in `(rad/s)^2`:

```text
[ 1.80894e-7   3.849e-10  -5.177e-10 ]
[ 3.849e-10    1.99662e-7  3.958e-9  ]
[-5.177e-10    3.958e-9   1.15382e-8 ]
```

Z ist quantisiert und zeitlich korreliert (`rho(1)=0,628`). Der effektive
100-Hz-Weissrauschersatz steigt bei Blocklaengen bis 100 s auf
`4,179e-7 (rad/s)^2`. Der erste Schattenwert wird deshalb auf
`5,0e-7 (rad/s)^2` aufgerundet. Er liegt oberhalb aller beobachteten
Punktschaetzer und ist absichtlich konservativer als die reine
Z-Stichprobenvarianz. Weil fuer 100 s nur fuenf nicht ueberlappende Bloecke
vorliegen, ist er kein statistisches Konfidenzlimit und noch kein
Produktionswert: Kaltstart, Temperatur und Motorvibration wurden nicht erfasst.

Reproduzierbare Offline-Auswertung:

```bash
python3 tools/sensorfusion/hwt601_ruherauschen_auswerten.py \
  ~/.local/share/amadeus/hwt601/bias-20260908-230201/samples.csv
```

## Fail-closed-Start

Der Launch hat fuer die Stillstandsangabe absichtlich keinen Standardwert.
Vor dem Aufruf muss der Roboter tatsaechlich ruhig stehen. Der Start oeffnet
keinen Motorport und besitzt weder Fahrbefehlssubscriber noch Aktorausgabe:

```bash
AMADEUS_HWT601_STILLSTAND=JA \
  bash tools/sensorfusion/start_hwt601_shadow.sh
```

Der Wrapper prueft beide getrennten seriellen Aliase, verlangt freie HWT- und
Motorports, eine leere ROS-Domain und ersetzt das WLAN-DDS-Profil fuer seinen
gesamten Prozessbaum durch explizite Loopback-Unicast-Kommunikation. Der
Launchparameter allein bleibt fuer gezielte Entwicklertests verfuegbar.

Die ersten 15 s sind Einlaufzeit, danach werden mindestens 10 s und 800
Proben fuer den Bias gesammelt. Vor erfolgreicher Kalibrierung gibt es keine
Nachricht auf dem abgeleiteten Topic. Anschliessend wird der Bias fest
eingefroren; Bewegung kann ihn nicht nachfuehren.

Kontrolle in einem zweiten Terminal mit derselben Domain:

```bash
export ROS_DOMAIN_ID=144 ROS_LOCALHOST_ONLY=0
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI='<CycloneDDS xmlns="https://cdds.io/config"><Domain id="any"><General><Interfaces><NetworkInterface name="lo" multicast="false"/></Interfaces><AllowMulticast>false</AllowMulticast></General><Discovery><Peers><Peer address="localhost"/></Peers><ParticipantIndex>auto</ParticipantIndex><MaxAutoParticipantIndex>20</MaxAutoParticipantIndex></Discovery></Domain></CycloneDDS>'
ros2 topic echo --once /shadow/hwt601/raw_status_json
ros2 topic echo --once /shadow/hwt601/status_json
ros2 topic hz /shadow/hwt601/imu/yaw_rate
ros2 topic echo --once /shadow/hwt601/imu/yaw_rate
```

Erwartet werden mindestens 80 Hz, keine Datenluecke ueber 0,10 s, keine
Verwerfungen oder Reconnects, `bias.adaptation_samples=0`, Outputframe
`base_link`, Z-Kovarianz `5e-7`, Orientierung und Beschleunigung jeweils mit
`covariance[0]=-1`. Der Schattenstatus bleibt trotz gesunder Daten
`fusion_ready=false`, weil weder Encoderfusion noch Kartenintegration Teil
dieser Stufe sind. Eine ungueltige oder nicht monotone Probe sowie eine
Datenluecke ueber 0,10 s verriegelt den bereits kalibrierten Pfad dauerhaft;
danach sind Neustart und neue Stillstandsbestätigung erforderlich. Ein alter
Bias wird nie ueber einen vermuteten Sensorneustart hinweg weiterverwendet.

## Harte Grenzen und naechste Stufe

- kein `/odom`, `/tf`, `/map`, `/fusion/*` oder `cmd_vel`;
- kein Basis-, OAK-, LiDAR-, Scan-, SLAM- oder Navigationsstart;
- der gesperrte motorische Winkeltest bleibt gesperrt und wird nicht gebraucht;
- Stopp per einmaligem SIGINT am Launchprozess, nicht an der Prozessgruppe;
- Produktionsstarts und bestehende Kartenprofile bleiben unveraendert.

Der zehnminuetige Schattenstillstand ist inzwischen bestanden. Als naechste
getrennte Stufe wird ein eigener `publish_tf=false`-EKF gegen **echte**
Encoderodometrie vorbereitet. Der vorhandene 180-Grad-Bag enthaelt nur
Encoderstatus als JSON, kein `nav_msgs/Odometry`; synthetische Nullodometrie
darf nicht als Messung eingesetzt werden. Jede neue reale Bewegung braucht
weiterhin eine eigene Freigabe.

## Reale kurze Abnahme am 09.09.2026

Der Wrapper bestand die Alias-/Port- und leere-Domain-Pruefung. In der
Loopback-Domain 144 liefen exakt `/hwt601_shadow_reader` und
`/hwt601_shadow`. Je ein Publisher lieferte Rohdaten und abgeleitete
Giergeschwindigkeit; der Rohdatenstrom hatte exakt einen Subscriber. Auf
`/odom`, `/map`, `/tf`, `/tf_static`, `/fusion/imu`,
`/fusion/wheel_odom`, `/cmd_vel` und `/cmd_vel_smoothed` gab es jeweils null
Publisher.

Nach 2.500 absichtlich blockierten Startproben war der Bias mit 1.001 Proben
kalibriert. Kontrollstand nach 7.899 Rohproben: 5.399 publiziert, null
verworfen, `adaptation_samples=0`, ein Verbindungsaufbau und null Reconnects.
Der Rohstatus meldete rund 100,01 Hz; eine getrennte 20-s-Aufnahme enthielt
2.001 Schattenproben bei 99,9997 Hz und maximal 12,13 ms Luecke. Die mittlere
korrigierte Z-Rate betrug `0,0000404 rad/s`, das direkte Integral `+0,0463
Grad`. Die Nachricht hatte `frame_id=base_link`, X/Y-Varianz je `1e6`,
Z-Varianz `5e-7` sowie Orientierung/Beschleunigung explizit nicht vorhanden.

Der allgemeine Rohstatus bleibt bewusst bei `scale_validation_pending=true`,
weil weder Gyro X/Y noch die Beschleunigung als vollstaendige 6-Achs-Quelle
abgenommen sind. Nur der Shadow-Status bezeichnet die extern bestaetigte
Gyro-Z-Skala. Beide Prozesse wurden mit einem SIGINT am Launch-Elternprozess
sauber beendet; HWT- und Motorport sowie die lokale Domain waren danach frei.
Dies besteht den kurzen Smoke-Test. Kaltstart, Temperatur und Motorvibration
bleiben davon unberuehrt.

## Reale Zehn-Minuten-Abnahme am 09.09.2026

Der separat protokollierte Schattenlauf bestand 600,009 s mit 59.991 gueltigen
Proben bei 99,982 Hz. Die groesste Datenluecke betrug 30,744 ms; weder der
Rohleser noch der Schattenknoten verwarfen eine Probe, und es gab genau einen
Verbindungsaufbau sowie null Reconnects. Der nach der Startkalibrierung feste
Bias blieb bei `adaptation_samples=0`.

Die mittlere korrigierte Z-Rate war `3,777e-7 rad/s`, die
Standardabweichung `1,084e-4 rad/s`. Das direkte Integral endete bei
`+0,01323 Grad`; der groesste absolute Zwischenwert im gesamten Lauf war nur
`0,08574 Grad` gegen die Abnahmegrenze von 1 Grad. Der Status blieb gesund,
aber absichtlich `fusion_ready=false`.

Waehrend der Messung waren exakt Rohleser, Schattenknoten und der lokale
Beobachter sichtbar. Publisher-Provenienz und Topiczaehlung bestaetigten einen
Roh- und einen abgeleiteten HWT-Publisher sowie keine Publisher auf `/odom`,
`/map`, `/tf`, `/tf_static`, `/fusion/imu`, `/fusion/wheel_odom`, `/cmd_vel`
oder `/cmd_vel_smoothed`. OAK, Basis, SLAM und RTAB-Map waren aus; der
Motorport blieb frei. Nach einem einzelnen SIGINT endeten beide Prozesse
sauber, beide seriellen Ports und die isolierte Domain waren frei. Die
Groessen-/Mtime-Signatur aller lokalen Karten blieb vor und nach dem Lauf
identisch.

Lokale Evidenz, nicht im Repository:

```text
~/.local/share/amadeus/hwt601/shadow-20260909-192400/
samples.csv  cb66a7a772bfa191bd01ef3e1b31a98c1ae33ef633c6272cfcae043c89bfb7b9
summary.json 8465fa18ab19554b725699ab7f33381a4d4792de70dd0bbf4884e4587d2219c2
```

Damit ist der warme motorlose Gyro-Z-Schatten bestanden. Das ist noch keine
Freigabe fuer Kaltstart, thermische Aenderung, Motorvibration, Encoderfusion,
Kartierung oder Navigation.
