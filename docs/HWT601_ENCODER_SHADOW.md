# HWT601 und ESS23-Encoder: direkte Schattenabnahme

**Stand:** 09.09.2026

**Branch:** `codex/hwt601-encoder-shadow`

**Status:** Software vorbereitet und offline getestet; beide seriellen Quellen
in dieser Stufe noch nicht gemeinsam am realen Roboter gestartet.

Diese Stufe beantwortet vor jeder EKF-Bewertung eine einfachere Frage: Bleiben
der korrigierte HWT-Gierwinkel und die aus den echten absoluten
Motorencoderzaehlern berechnete Bewegung im nachgewiesenen Stillstand
uebereinstimmend bei null? Synthetische Odometrie und `cmd_vel` sind dafuer
ausdruecklich unzulaessig.

```text
HWT601 /dev/ttyUSB_HWT601 -- nur FC03 --> Gyro-Z-Shadow ---+
                                                            +--> passiver
ESS23 /dev/ttyUSB_BASE ---- nur FC03 --> Encoder-Odometrie --+    Beobachter

erst nach bestandener direkter Abnahme:
beide Schatten-Topics --> getrenntes EKF, publish_tf=false
```

## Warum ein eigener Encoderleser noetig ist

Der produktive `base_hardware`-Knoten ist fuer diesen Nachweis ungeeignet:

- `dry_run=true` erzeugt Odometrie aus Befehlen statt aus den Motorencodern;
- `allow_rs485=false` oeffnet den Bus nicht;
- der echte Modus initialisiert und stoppt die Motoren mit FC06 und besitzt
  einen Fahrbefehlspfad.

Der neue `encoder_shadow_reader` besitzt dagegen keine Subscription und keine
Modbus-Schreibmethode. Er erlaubt ausschliesslich FC03 fuer:

| Bereich | Bedeutung |
|---|---|
| `0x000A`, 3 Worte | Position high/low und Ist-Drehzahl |
| `0x0011`, 1 Wort | Segmentierung, erwartet `1000` |
| `0x0019`, 1 Wort | Wortfolge, erwartet `0` (high/low) |
| `0x0101`, 1 Wort | Encoderaufloesung, erwartet `4000` |

Beide Motoren muessen dieselbe Konfiguration melden. Die bestaetigte
Positionsskala ist `1000` Counts je Motorumdrehung, das Getriebe `10:1`, der
wirksame Radradius `0,0624 m` und die wirksame Spurweite `0,3845 m`. Rechts
wird invertiert, links nicht. Ein unvollstaendiges Paar, eine Luecke, ein
unplausibles Delta, ein Aliaswechsel oder ein Verbindungsverlust verriegelt
den Leser bis zum Neustart. Pymodbus darf insbesondere keinen stillen
Reconnect ausfuehren.

Der Node akzeptiert nur `/dev/ttyUSB_BASE`, prueft dessen Linux-sysfs-Identitaet
auf FTDI `0403:6001` mit Seriennummer `BG03R8RZ`, verlangt gleichzeitig einen
getrennten aufloesbaren `/dev/ttyUSB_HWT601` und prueft den exklusiv offenen
seriellen Socket. Diese Kontrollen liegen im Leser selbst; der Startwrapper
wiederholt sie ueber udev und `fuser`.

## Isolierte Topics

| Topic | Quelle | Inhalt |
|---|---|---|
| `/shadow/hwt601/imu/yaw_rate` | HWT-Shadow | korrigierte Gierrate in `base_link` |
| `/shadow/hwt601/wheel_odom_raw` | Encoderleser | echte FC03-Pose und Twist |
| `/shadow/hwt601/status_json` | HWT-Shadow | fester Bias-/Sicherheitsvertrag |
| `/shadow/hwt601/raw_status_json` | HWT-Leser | Port-, Rate- und Verbindungsstatus |
| `/shadow/hwt601/wheel_status_json` | Encoderleser | Quelle, Geometrie, Paare und Fehler |

Es gibt kein `/odom`, kein TF, keine Karte, keine OAK, keinen LiDAR, kein SLAM,
keine Navigation und keinen Fahrbefehl. Das Quellen-Launch startet absichtlich
auch noch kein EKF.

## Reale Abnahme: Reihenfolge ist verbindlich

Dieser Abschnitt dokumentiert den spaeteren Lauf; er ist am 09.09.2026 noch
nicht ausgefuehrt. Das Oeffnen des Motorbusses erfolgt erst nach einer neuen
ausdruecklichen Freigabe der anwesenden Person. Der Roboter muss stillstehen,
der regulaere Basisstack muss sauber beendet sein und der Not-Aus bleibt in
Reichweite. Auch ohne Schreibzugriff koennen bereits versorgte Controller
Haltemoment erzeugen.

Zuerst wird in Terminal A der rein abonnierende Beobachter gestartet. Er
oeffnet kein Geraet und verlangt eine zuvor leere, auf Loopback isolierte
ROS-Domain. Der absolute Zielordner muss neu sein und ausserhalb des
Repositories liegen:

```bash
cd /home/p/roboter_worktrees/hwt601-usb-commissioning
bash tools/sensorfusion/start_hwt601_encoder_shadow_observer.sh \
  ~/.local/share/amadeus/hwt601/encoder-shadow-YYYYMMDD-HHMMSS
```

Erst wenn dessen Node sichtbar ist und die neue Freigabe vorliegt, startet
Terminal B die beiden strikt lesenden Quellen:

```bash
cd /home/p/roboter_worktrees/hwt601-usb-commissioning
AMADEUS_HWT601_ENCODER_STILLSTAND=JA \
AMADEUS_BASE_STACK_GESTOPPT=JA \
  bash tools/sensorfusion/start_hwt601_encoder_shadow.sh
```

Der zweite Wrapper akzeptiert als vorher vorhandenen Graphen exakt den
Beobachter. Ein leerer Graph oder irgendein weiterer Node bricht ab. Dadurch
kann der Beobachter nicht erst nach der HWT-Startkalibrierung angehaengt
werden. Er muss mindestens 24 s der 15-s-Einlauf- plus 10-s-Biasphase mit
echten Encoderwerten sehen; Bewegung, spaetes Anhaengen oder ein
Zaehler-Neustart verriegeln die Aufnahme.

Nach dem Lauf den Quellen-Launch genau einmal mit Strg-C an seinem
Elternprozess beenden, niemals die Prozessgruppe signalisieren. Danach beide
Ports mit `fuser` und Domain 145 mit `ros2 node list --no-daemon` auf Freiheit
pruefen.

## Fester 600-s-Akzeptanzvertrag

`summary.json` darf nur mit `passed: true` angenommen werden. Der Beobachter
verlangt unter anderem:

- mindestens 600 s sowohl nach monotoner Empfangszeit als auch nach
  ROS-Headerzeit; Abweichung hoechstens 0,5 s;
- HWT mindestens 80 Hz, Encoder mindestens 10 Hz und Datenluecken jeweils
  hoechstens 0,10 s; der isolierte HWT-Ausgang und der Beobachter verwenden
  dafuer lokal `RELIABLE` mit 200 Nachrichten Puffer, der Encoder-Ausgang
  `RELIABLE` mit 10; Motorpaarspanne hoechstens 0,05 s;
- HWT-, Encoder- und Differenzwinkel, jeweils Endwert und absoluter
  Zwischenpeak, strikt unter 1 Grad;
- Encodertranslation relativ zum Messstart und zur echten Startbaseline
  strikt unter 1 mm, `|v| < 0,005 m/s` und `|omega| < 0,005 rad/s`;
- null Rejects, Reconnects und Rebases; genau ein Verbindungsaufbau je Bus;
- alle drei Statusquellen und die erste gueltige Graphpruefung bereits vor den
  ausgewaehlten Messproben, danach monotone Statuszaehler und keine
  Statusluecke ueber 1 s;
- einen unveraenderten festen HWT-Bias ohne Adaptionsproben und von allen drei
  Quellen je einen fehlerfreien Status innerhalb von 2 s nach der letzten
  ausgewerteten Messprobe;
- bei den hoechstens 1 s auseinanderliegenden Graphpruefungen exakt die vier
  erwarteten Nodes und je genau einen unveraenderten Publisher-GID pro
  Quellentopic; null Publisher auf
  Produktiv-Odometrie, Karte, TF, Fusion oder Fahrbefehlen;
- CSV-Hash in der Zusammenfassung; reale CSV/JSON-Dateien bleiben lokal.

## EKF ist erst die nachgeordnete Beobachtungsstufe

`hwt601_encoder_shadow_ekf.launch.py` ist vorbereitet, aber noch nicht real
abgenommen. Es nutzt nur Encoder-`vx`/`wz` und HWT-`wz`, publiziert nur
`/shadow/hwt601/odom`, setzt `publish_tf=false` und `use_control=false` und
startet keine Hardware.

Der aktuelle HWT-Wert `5e-7 (rad/s)^2` gegen die vorlaeufige Encoder-
Winkelgeschwindigkeitsvarianz `0,03 (rad/s)^2` bedeutet ungefaehr 60.000:1
Gewichtung zugunsten des HWT. Beide Quellen liefern zudem nur Drehrate, keinen
absoluten Heading-Anker. Ein optisch plausibler EKF-Winkel waere deshalb noch
kein Nachweis, dass das Kartenproblem geloest ist.

Vor einer Kartierungsintegration fehlen weiterhin:

1. diese reale gemeinsame Stillstandsabnahme;
2. ein separat freigegebener dynamischer HWT-/Encodervergleich in beiden
   Drehrichtungen, einschliesslich Bewertung des zeitversetzten linken/rechten
   FC03-Paars;
3. reale Encoder-`wz`-Kovarianz und Innovationsauswertung;
4. eine Heading-Korrekturstrategie sowie Kaltstart-, Temperatur- und
   Motorvibrationspruefungen;
5. erst danach ein kontrollierter Karten-A/B-Test.

Rueckfall: beide Shadow-Prozesse beenden oder gar nicht starten. Kein
Produktivlaunch, Motorregister, Sensorregister, TF oder Kartenprofil wird von
dieser Stufe veraendert.
