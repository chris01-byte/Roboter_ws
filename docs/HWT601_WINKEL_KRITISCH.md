# Kritischer Winkelwiderspruch — Faktor-zwei-Verdacht abgeschlossen

Stand 09.09.2026. Der Nutzer bestaetigte nachtraeglich ausdruecklich den
visuell beobachteten 180-Grad-Haltpunkt. Damit ist ein Faktor-zwei-Fehler der
HWT-/LiDAR-Winkelskala verworfen. Es gibt keine Skalenhalbierung. Die genaue
Ursache der aelteren 45-Grad-Wahrnehmung ist nicht rekonstruierbar; jene beiden
Laeufe bleiben historisch zurueckgezogen. Freigegeben ist nur der passive,
isolierte Gyro-Z-Schattenpfad, keine autonome Bewegung oder Kartenintegration.

## Extern gestoppte 180-Grad-Gegenprobe

Der Nutzer verlangte nach der Sperre ausdruecklich eine beaufsichtigte
180-Grad-Drehung und wollte den physischen Endpunkt selbst beobachten. Fuer
diesen einzelnen Test bestimmte deshalb **kein Sensor** den Stopp: langsames
Linkskommando +0,10 rad/s, Nutzer betaetigte Motor-Halt/Not-Aus am beobachteten
Rueckwaertspunkt; automatische zweite Grenze 35 s. Eine lokale, nur ueber
Loopback erreichbare ROS-Domain 143 wurde verwendet. Vorher waren genau je ein
lokaler Publisher fuer LiDAR, HWT, LiDAR-Odometrie und Basiszustand, null
Befehlspublisher, ein Befehlssubscriber, gesunde Encoder und Stillstand
bestaetigt. OAK, SLAM, Navigation und collision_monitor liefen nicht.

Motor-Halt wurde nach 32,60936 s positivem Kommando als RS485-/Encoderverlust
erkannt. Aufzeichnung bis zu diesem externen Ereignis:

| Auswertung | Drehwinkel |
|---|---:|
| HWT-Gyro, Bias aus 1.400 Vorlaufproben | +178,16378 Grad |
| lokale rad-/IMU-unabhaengige LiDAR-Odometrie | +178,25000 Grad |
| Encoderpositions-Odometrie | +175,61648 Grad |
| separater Anfangs-/Endscan-Fit, freie Suche -180..180 | +178,12888 Grad |

IMU: 3.333 Bewegungsproben, 99,97166 Hz, maximale Luecke 25,239 ms.
Der freie Raw-Scan-Fit nutzt weder Online-Matcher noch IMU/Encoder; beste 70 %
der Punkte liegen im Mittel 23,96 mm auseinander. Die 0,475-m-Translation des
LiDAR-Ursprungs ist bei dessen 0,245-m-Hebelarm und einer Drehung nahe 180 Grad
erwartbar und keine Chassisfahrt von einem halben Meter.

Dieser Lauf und die spaetere ausdrueckliche Nutzerbestaetigung verwerfen einen
Faktor-zwei-Fehler in HWT- oder LiDAR-Winkelskala: doppelte Befehlsdauer
gegenueber den frueheren Laeufen ergibt doppelte Sensorwinkel, und der
physische Endpunkt kam vom anwesenden Nutzer. Die Werkzeugsperre bleibt als
Schutz vor einer unnoetigen Wiederholung bestehen. Keine Skalenwerte wurden
geaendert.

Lokales Bag:
`/home/p/.local/share/amadeus/hwt601/external-180-20260909/`, SHA-256 der DB3
`0ac4a4c73d80627704c4c38919b3282dfca7f3bbd26cd114f451072072aa3a51`.
Alle Prozesse einzeln per SIGINT beendet, serielle Ports frei. Der Motor-Halt
blieb die physische Rueckfallebene; Basis beendete danach mit dem bekannten
Shutdown-Doppelfehler, erst nach bereits gesendetem Stopp und erkannter
Hardwareunterbrechung.

Der anwesende Nutzer bestaetigt anhand vorher gesetzter Bodenmarkierungen
und der Chassisausrichtung jeweils etwa 45 Grad links und rechts. Dagegen
meldeten die aufgezeichneten IMU-/LiDAR-/Encoderwerte etwa 90 Grad.
Die physische Referenz darf nicht durch die Uebereinstimmung der Softwarewerte
ueberstimmt werden. Die frueheren `passed=true`-Ergebnisse sind als
Hardwareabnahme zurueckgezogen. Originaldateien bleiben als Evidenz unveraendert.

## Sofortmassnahme

Branch `fix/hwt601-angle-discrepancy-lock`: motorisches Testwerkzeug verweigert
`--execute` vor ROS-Initialisierung, auch bei gesetzter Fahrfreigabe und fuer
beide Richtungen. Kein Freigabeschalter umgeht die Sperre. 107 Softwaretests
bestanden, darunter beide Sperrfaelle. Keine Antriebe/Sensoren gestartet,
keine Motor-/Sensorkonfiguration geschrieben. Die Sperre gilt fuer dieses
Werkzeug in diesem Worktree, nicht fuer alte Branches oder andere Startwege.
Kein autonomer Prozess lief; alle drei seriellen Ports waren frei.
Die Motorversorgung wurde nicht physisch ausgeschaltet.

## Nachgeprueft, ohne Bewegung

- Die Stoppschwelle war 88 Grad **LiDAR-Schätzung**, nicht ein aus Laufzeit
  erzeugter Ergebniswert. IMU wurde mit festem Bias unabhaengig integriert.
- ROS-Zeitdauer/monotone Empfangsdauer im Bewegungsfenster: links 0,99994,
  rechts 1,00001. Keine beobachtete Verdopplung der Zeitbasis.
- LiDAR-SDK dekodiert Hundertstelgrad mit `/100`, ROS-Umrechnung ist
  pi/180; Scanmetadaten spannen rund 360 Grad auf. Quaternion verwendet
  sin(yaw/2), cos(yaw/2), Rueckrechnung atan2 korrekt. In diesen gelesenen
  Codepfaden keine Faktor-zwei-Stelle identifiziert. SDK-Arbeitskopie sauber,
  Commit `bf668a89baf722a787dadc442860dcbf33a82f5a`; ausgefuehrtes Binary ist
  das Build-Overlay. Historische Binary-/Hardwareidentitaet nicht lueckenlos
  attestiert.
- Encoderformel ist (rechter Weg - linker Weg)/Spurweite, Counts=1000,
  Getriebe=10. Rohzaehleraenderungen links (-7688,-7690), rechts (7684,7687).
  Formelkorrektheit beweist nicht die physisch richtige Parametrierung.
- IMU nutzt Z-Skala 400/32768 Grad/s je Rohwert. Herstellerangabe stuetzt
  diesen Wert, aber beweist nicht die gelieferte Firmwarekonfiguration.
- Separater Offline-Scanvergleich mit KD-Baum und freier SE(2)-Suche ueber
  -180..180 Grad, ohne Online-Matcher, IMU oder Encoder: links +91,3765,
  rechts -91,1585 Grad. Beste 70 % der Punkte im Mittel 11,8/13,9 mm
  auseinander. Suche um +/-45 Grad passte deutlich schlechter. Das belegt
  Konsistenz der **gespeicherten ROS-Scans**, nicht die physische Winkelreferenz
  oder deren fehlerfreie Entstehung.

## Konkrete Luecke im Pruefaufbau

Nur der Befehlskanal wurde auf Publisher-/Subscriberanzahl geprueft, nicht
die Sensorquellen. Verwendet wurde die normale netzwerkfaehige ROS-Domain 42,
nicht eine rein lokale Testdomain. Bags enthalten keine Sender-GIDs je
Nachricht und keine originalen UART-Frames beider Sensoren. Eine moegliche
Fremdquelle/Ersetzung vor dem Recording laesst sich daher rueckwirkend nicht
lueckenlos ausschliessen. **Keine Fremdquelle nachgewiesen:** aktuelle
achtsekündige Graphabfrage bei gestoppten Testprozessen fand auf allen fuenf
Test-/Sensortopics null Publisher. Das ist kein historischer Nachweis.

## Historische native Zielmessungen

**Zweite native Zielmessung 09.09.2026:** Nach vom Nutzer bestaetigtem
seitlichem Versetzen gemaess Anleitung erneute rein passive UART-Aufnahme:
9.063 gueltige Pakete, null CRC-Fehler. Altes nahes Ziel in CW-Bins 87..90
verschwindet (wieder Hintergrund ~3,05 m); neues Ziel in Bins 48..50 erscheint
bei 829..834 mm. Aus einzelnen Zielpunkten: Medianwinkel vorher 88,98409 Grad
(1.406 Treffer, 607 mm), nachher 49,50182 Grad (1.120 Treffer, 831 mm).
Differenz 39,48227 Grad. Auswahl: vorher 500..700 mm/nachher 750..1000 mm,
jeweils native Winkel 0..110 Grad und Intensitaet >0. Lokale Zweitaufnahme:
`/home/p/.local/share/amadeus/hwt601/lidar-native-20260909-175250/`.
Nur die beiden Zielsektoren aendern ihren 1-Grad-Distanzmedian um >300 mm.
Das stuetzt die Identitaet des bewegten Ziels. Der Test zeigt keine Meldung
von ~90 Grad fuer die angeleitete Zielverschiebung, ist aber wegen 39,48
statt nominell 45 Grad KEINE bestandene Winkelskalierungsabnahme. Tatsaechliche
Zielkoordinaten/Seitwaertsverschiebung muessen nachgemessen werden; weder
Aufstellfehler noch LiDAR-Skalenfehler damit bereits bewiesen. Motorsperre bleibt.

**Erste native Stillstandsmessung 09.09.2026:** Nutzer bestaetigt Motorstrom
aus, 40 mm breites Ziel frontal in 600 mm Entfernung ab LiDAR und in dessen
Scanebene. `lidar_uart_probe.py --capture` liest ausschliesslich den
seriennummerngeprueften LiDAR-USB-Port, ohne Sendebytes/ROS/SDK-Scanmatcher.
47-Byte-Pakete mit CRC-8 geprueft und native Hundertstelgrad dekodiert.
9.062 gueltige Pakete, null CRC-Fehler. Schmales Ziel in nativen CW-Bins
87..90 Grad mit Medianentfernungen 604..610 mm; passt zum Hefter, Identitaet
noch durch gezieltes Versetzen zu bestaetigen. Dies ist keine Winkelabnahme.
Originalbytes und Histogramm lokal unter
`/home/p/.local/share/amadeus/hwt601/lidar-native-20260909-173937/`.
Port danach geschlossen; Motor-/IMU-Port unangetastet. Parser-Tests fuer
Winkel, Entfernungen, Wrap, CRC-Verwerfung und fehlenden Sendeaufruf ergaenzt.

Diese Zielmessungen bleiben als Nachweis des damaligen Diagnosewegs erhalten.
Der ungenaue manuelle Aufbau ist nach der bestaetigten 180-Grad-Gegenprobe
nicht mehr Grundlage einer Skalenentscheidung. Nicht automatisch erneut
fahren und keine Skala pauschal halbieren. Der motorlose Schattenpfad aus
`docs/HWT601_SHADOW.md` hat seinen warmen 600-s-Stillstand bestanden; eine
spaetere echte Encodergegenprobe bleibt eine getrennte Stufe mit eigener
Freigabe fuer jeden Hardwarezugriff oder Fahrtest.

## Integritaet der lokalen Evidenz

Alle Pfade relativ zu `/home/p/.local/share/amadeus/hwt601/`:

| Datei | SHA-256 |
|---|---|
| powered-20260909-162248/samples.jsonl | d78c69d3b29e7ff71a36825cfb09b19120ed70a189baf49cd60ebb32bd29c650 |
| powered-20260909-164111/samples.jsonl | 623b3415fc7b3889de0751b8d9b2909f589a6bba675525cbbf84807cfa955d10 |
| powered-scans-20260909-162330/powered-scans-20260909-162330_0.db3 | 6f290ba19df4e7da2d350754b5a22dc5cfde57cca8082774156924f87ee4a2c7 |
| right-scans-20260909-164100/right-scans-20260909-164100_0.db3 | 08caba8e2adc4c3504493460163fad5e6c74b28647177c3db108645a91dbfd9f |

Rohdaten enthalten Wohnungsgeometrie und bleiben ausschliesslich lokal.
Rueckfall der Aenderung darf nicht als Fahrfreigabe verwendet werden:
vorherige Branches enthalten ungesperrte Testwerkzeuge und bleiben fuer
Bewegung ebenfalls nicht freigegeben.
