# Arm-Kontext für Agenten: Amadeus

**Stand: 08.11.2026.** Grundlage sind die am 10.10.2026 aus Gespräch und
Repository rekonstruierten Angaben sowie die Nutzerangaben vom 08.11.2026
(Gelenkzuordnung, Maße aus dem Fusion-360-Modell, Not-Aus, Rolle der OAK).
Der ursprüngliche lokale Wortlaut vom Oktober ist nicht zugänglich. Keine
Angabe in dieser Datei ist eine Messung am Roboter, sofern sie nicht
ausdrücklich so bezeichnet ist.

## Zuerst lesen

1. [AGENTS.md](../AGENTS.md), [Projektgedächtnis](PROJECT_MEMORY.md) und
   [Inventar](INVENTORY.md): projektweite Regeln und nachgewiesener Bestand.
2. [Integrations- und Stufenplan](INTEGRATIONSPLAN_ARM_SOFTWARE.md):
   maßgeblicher Armplan einschließlich Homing, Greifer, Fahrpose und Kalibrierung.
3. [Inbetriebnahme-Messblatt](ARM_INBETRIEBNAHME_MESSBLATT.md):
   offene Hardwaredaten, Versuche und Abnahmen.
4. [Build-Protokoll](ARM_BUILDPROTOKOLL.md): tatsächlich umgesetzte Änderungen;
   höchstens 200 Wörter pro neuem Eintrag einschließlich Überschrift.

**Aktuelles Ziel: ausschließlich Arm-Inbetriebnahme.** Kamerageführtes Greifen
einer Flasche bleibt das spätere Gesamtziel. Flaschenformat, Füllung und eine
erste Tischaufgabe sind noch nicht vereinbart. Der Arm liegt noch in
Einzelteilen vor (08.11.2026). Der Nutzer erprobt die Hardware; Agenten
entwickeln Software, Versuchsanweisungen und Auswertungen. Keine reale
Bewegung aus einer Planungsfreigabe ableiten.

## Aufbau laut Nutzer und CAD (08.11.2026)

Der Arm sitzt vorn am Kameramast auf einer vertikalen Hubachse. Er hat sechs
Drehgelenke; mit der Hubachse sind es sieben bewegte Achsen, dazu kommt der
Greifer. Die Farben beziehen sich auf das Fusion-360-Modell.

| Achse | Bauteil im CAD | Funktion | Antrieb, Untersetzung |
|---|---|---|---|
| Hubachse | vorhandene vertikale Linearführung mit Spindel | hebt und senkt den ganzen Arm, Hub 400 mm | Motor, Spindeltyp und Steigung offen |
| J1 Schulter heben | großes blaues Gelenk am Mast | schwenkt den Arm hoch und runter | NEMA23 der ESS-RS-Reihe, 55,25:1 |
| J2 Schulter seitlich | erstes silbernes Gelenk | seitliches Erreichen ohne Plattformbewegung | ESS-RS, 72:1 |
| J3 Ellenbogen | zweites blaues Gelenk | beugt und streckt zwischen Ober- und Unterarm | ESS-RS, 72:1 |
| J4 Unterarm drehen | grünes Gelenk, künftig hinter dem Ellenbogen | Drehung um die Unterarmlängsachse | ESS-RS, 72:1 |
| J5 Handgelenk kippen | letztes silbernes Gelenk | Querachse zum Unterarm; Greifer in Ausgangsstellung möglichst nach unten | ESS-RS, 72:1 |
| J6 Greifer drehen | neues Drehgelenk direkt vor dem Greifer | Drehung um die Greiferlängsachse | Antrieb und Untersetzung offen |

J4 wird gegenüber der bisherigen Konstruktion hinter den Ellenbogen verlegt,
J6 kommt neu hinzu. Ob der STEP-Export vom 08.11.2026 diesen Stand schon
zeigt, ist offen. Laut Angabe vom 10.10.2026 sind fünf ESS17-RS07 und ein
NEMA23 vorhanden; welche ESS17 Hubachse, J2–J5 und J6 antreiben, ist offen.
Frühere Angaben zu „iCL-Steppern“ sind überholt: Alle Schrittmotoren sind
ESS-RS (Nutzer, 08.11.2026).

**Maße (Nutzerangabe aus dem CAD):**

- Schulter in oberster Hubstellung 1106 mm über Boden; mit 400 mm Hub
  rechnerisch bis etwa 706 mm herunter.
- Reichweite gestreckt ab Mast etwa 746 mm ohne Greifer; der Greifer wird
  voraussichtlich bis etwa 150 mm lang.
- Transportpose wie im CAD: LiDAR-Ebene frei, der Arm ragt mindestens
  130 mm vor die Chassisfront. Mit gegriffenem Objekt ist die Pose neu zu
  prüfen; der Einfluss auf die OAK wird praktisch ermittelt.
- Nutzlast höchstens 1 kg. Arm, Greifer und Basis sind noch nicht gewogen.

**CAD:** maßstäbliches Fusion-360-Modell. Der STEP-Export
„Final P&C V3_Lang_lang_neu.1.step“ (44,7 MB, 08.11.2026) liegt nur lokal
beim Entwickler, nicht im Repository.

## Gesicherte Angaben und offene Punkte

| Thema | Gesichert | Noch offen |
|---|---|---|
| Achsen | Hubachse und J1–J6 wie oben; J1 mit NEMA23 (ESS-RS) | Antrieb von Hubachse und J6, Typenschilder, Firmware, Busadressen |
| Getriebe | J1 55,25:1; J2–J5 72:1 | Untersetzung J6, Spindelsteigung, Spiel, Grenzwinkel |
| Halten | Keine Bremsen; Selbsthemmung soll praktisch erprobt werden | Haltevermögen je Gelenk und Hubspindel unter Last, Rücktreiben |
| Not-Aus | Trennt die komplette Stromversorgung des Roboters | Ob auch der Jetson getrennt wird; Verhalten jeder Achse beim Abschalten |
| Bus | Eigener RS485-Adapter für den Arm ist verbaut | Chip, Gerätepfad, udev-Alias, Baudrate, Terminierung |
| Homing | TLE4905L als Referenzgeber vorgesehen | Stückzahl, Magnetlage, Verdrahtung; Referenz und Endlagen der Hubachse |
| Montage | Arm in Einzelteilen; maßstäbliches CAD vorhanden | Montagezustand der Hubachse am Roboter |
| Externer Armcode | Keiner | – |
| Greifer | Noch nicht konstruiert; XL330 mit M6- oder ähnlicher Trapezspindel | XL330-Variante, Steigung, Hub, Führung, Endlagen, Kamerabauraum |
| Kraftfeedback | Zwei Sensoren mit ohmschem Widerstandssignal | Typ, Kennlinie, Elektronik, ADC und Auswertung |
| Vision | OAK-D-S2 nur für Objekterkennung und Anfahrdistanz | Nahbereichssensor für den eigentlichen Griff |
| Transport | Transportpose laut CAD über der LiDAR-Ebene, mindestens 130 mm Überstand vorn | Gelenkwinkel, OAK-Sicht, Footprint, Abstützung, Pose mit Last |
| Last | Höchstens 1 kg | Ob inklusive Greifer; Massen und Schwerpunkte |

Die ESS23-Motoren der **Fahrbasis** sind kein Identitätsnachweis für den
NEMA23 im Arm, auch wenn beide zur ESS-RS-Reihe gehören. Modell, Register
und Skalierung erst an Typenschild und Gerät bestätigen. Encoderauflösung,
Befehlsauflösung und Gelenkwinkel sind verschiedene Größen; „1000 PPR“
allein legt keine Softwareumrechnung fest.

## Was bereits implementiert ist

Build A liegt auf dem Entwicklungsbranch
[feature/arm-commissioning-foundation](https://github.com/chris01-byte/Roboter_ws/tree/feature/arm-commissioning-foundation),
[PR #106](https://github.com/chris01-byte/Roboter_ws/pull/106).
Stand 08.11.2026: noch nicht nach main übernommen.

| Pfad | Inhalt |
|---|---|
| [arm_hardware](../src/arm_hardware/README.md) | Strikte Konfiguration, Fake-Transport, begrenzte Modbus-Leseprobe |
| [arm_tools](../src/arm_tools/README.md) | CLI für validate, ausdrücklich gewählte Fake- und Read-only-Betriebsart |
| [arm_bringup](../src/arm_bringup/README.md) | Unvollständiges reales Inventar und getrennte synthetische Beispieldaten |
| [Konfigurationsschema](../src/arm_hardware/arm_hardware/config.py) | Erlaubte Felder, Validierung, unbekannte Werte als null |
| [Inventar](../src/arm_bringup/config/arm_inventory.json) | Sechs noch nicht vermessene Gelenkeinträge; keine erfundene Motorzuordnung |
| [CI](../.github/workflows/arm-commissioning.yml) | Pakettests, Installation und isolierter ROS-Humble-Build |

Für ESS17-RS07 erlaubt die reale Probe ausschließlich FC03 mit Start/Länge
(0x0000, 4) und (0x0006, 7). Identität, Leseprofil, Gelenkauswahl,
Adapter und Busparameter müssen ausdrücklich bestätigt sein. Der NEMA23
bleibt gesperrt, bis sein Typ und Leseprofil bestätigt sind. Firmware darf
für die erste Inventur noch offen sein.

Es gibt keine Registerschreib-, Homing- oder Bewegungsbefehle.
Die Validierung öffnet keinen seriellen Port. Synthetische Daten ergeben
keine Hardwarefreigabe; auch eine erfolgreiche reale Leseprobe bedeutet
weder referenziert noch bewegungsbereit.

**Schemalücke:** [config.py](../src/arm_hardware/arm_hardware/config.py)
verlangt genau sechs Einträge mit Winkelgrößen in rad. Die Hubachse ist
linear (Weg in m, Spindelsteigung) und damit zusammen mit J1–J6 die siebte
Achse. Das Schema muss in einem eigenen Build erweitert werden; bis dahin
sind joint1 bis joint6 nur Erfassungsplätze ohne Zuordnung.

**Nachweis:** 32 Tests, Installation und Humble-Build auf Commit 9e65e4f
bestanden ([CI-Lauf](https://github.com/chris01-byte/Roboter_ws/actions/runs/38070478719)).
Keine reale Armverbindung oder Bewegung damit nachgewiesen. Der tatsächliche
Jetson-Installationsstand dieser neuen Pakete ist nicht geprüft.

## Angrenzende Systeme und Ablageorte

| System | Quelle | Bedeutung für die Integration |
|---|---|---|
| Öffentliche Armverträge | [robot_interfaces](../src/robot_interfaces/) | Actions/Services vorhanden, reale Umsetzung gesondert nachweisen |
| Greifmission | [pick_and_place.xml](../src/bt_orchestrator/bt_xml/pick_and_place.xml) | ready und stowed werden bereits verwendet |
| Erkundung | [explore.xml](../src/bt_orchestrator/bt_xml/explore.xml) | Kein vollständiger Arm-Fahrfreigabenachweis |
| Missions-Fahrgate | [cmd_vel_mission_gate.py](../src/robot_navigation/robot_navigation/cmd_vel_mission_gate.py) | Ansatzpunkt für einen systemweiten Basis-/Arm-Vertrag |
| Testgegenstellen | [mock_servers](../src/mock_servers/) | Erfolgreiche Abläufe können simuliert sein |
| Armmodell | [Dummy-URDF](../src/robot_description/urdf/mobile_manipulator_dummy.urdf.xacro) | Überholt: Arm hinten auf der Plattform mit senkrechter erster Achse; echtes Modell aus dem CAD ableiten |
| Ablageposen | [mission_catalog.yaml](../src/mission_manager/config/mission_catalog.yaml) | `place_arm.*` sind Platzhalter aus dem alten Plattformkonzept, Höhen unplausibel |
| OAK | [oak.launch.py](../src/robot_bringup/launch/oak.launch.py) | Aktuelle Montage- und Kamera-Frames |
| Wahrnehmung | [semantic_perception](../src/semantic_perception/) | Erkennung, Tiefe, TF und Objektgedächtnis |
| Hand-Auge-Werkzeug | [handeye_calibration](../src/handeye_calibration/) | Recorder/Löser für Eye-to-Hand; für eine Handkamera Eye-in-Hand ergänzen |
| LiDAR | [stl27l.yaml](../src/amadeus_lidar_bringup/config/stl27l.yaml) | Montage und bestehende Mastabschattung |
| Nahbereich | [vl53_params.yaml](../src/vl53_near_field/config/vl53_params.yaml) | Auch diese Sichtbereiche bei Fahrpose prüfen |
| Sicherheitsstatus | [safety_monitor_node.py](../src/safety_monitor/safety_monitor/safety_monitor_node.py) | GPIO-Platzhalter ist kein geprüfter Hardware-Not-Aus |
| Zielsystemübergabe | [ROBOT_TRANSFER.md](ROBOT_TRANSFER.md) | Installationsstand und reale Betriebsnachweise |

Der Bestand enthält passende Missionsschnittstellen und Kalibrierwerkzeuge.
Es fehlen weiterhin Bewegungsansteuerung, Homing, vermessene Kinematik,
belastbare Gelenkgrenzen, koordinierter Controller und realer Greifer.
Tests mit Mocks nicht als erfolgreiche reale Greifversuche ausgeben.

## Wichtige Entwurfsfragen

### TLE4905L

Das Referenzsignal soll bevorzugt an einen dafür konfigurierten Digitaleingang
des jeweiligen ESS-Antriebs gelangen. Der TLE4905L liefert einen
Open-Collector-Ausgang. Die ESS17-Eingangsbeschaltung arbeitet laut Handbuch
mit optisch getrennten 24-V-Eingängen; daraus folgt **keine ungeprüfte direkte
Verbindung**. Pegel, Strom, Polarität, Magnetlage und Eingangsfunktion vor Ort
prüfen. Eine passende Transistor-/Optokopplerstufe ist ein Entwurfsvorschlag.

Der Controller löst Homing aus und überwacht es; Linux-Polling soll die
Referenzflanke nicht zeitkritisch bestimmen. Home-Signal, Homing-Start,
Endlagen und mechanischer Anschlag haben unterschiedliche Aufgaben.
Details und Prüfablauf stehen im Integrationsplan. Für den NEMA23 in J1
ist die elektrische und funktionale Eignung separat zu prüfen. Die Hubachse
braucht zusätzlich eine eigene Referenz und Endlagen an beiden Hubenden.

### Not-Aus ohne Bremsen

Der Not-Aus trennt die komplette Stromversorgung. Damit werden alle Achsen
gleichzeitig momentlos. Bis Messungen etwas anderes zeigen, gilt:

- Gelenke und Hubspindel halten nur über Selbsthemmung. Nicht jede Spindel
  und nicht jedes Getriebe ist selbsthemmend; das ist je Achse unter Last
  zu prüfen, bevor der Arm angehoben oder ausgefahren betrieben wird.
- Ob die ESS-Antriebe ihren Positionszähler über einen Stromausfall halten,
  ist im Repo nicht belegt. Bis dahin ist nach jedem Not-Aus neu zu
  referenzieren, auch aus ausgefahrener Stellung und mit Objekt im Greifer.
  Die Homing-Reihenfolge muss dafür kollisionsfrei sein.
- Ein selbsthemmender, stromloser Arm hält auch eine eingeklemmte Hand fest.
  Eine manuelle Entlastung gehört in die Konstruktion.
- Die Greiferspindel hält ein gegriffenes Objekt nach dem Abschalten fest.
- Vorschlag: Transportpose mechanisch abstützen, damit Fahrt und Not-Aus
  nicht vom Haltemoment der Antriebe abhängen.

### Greifer

XL330 plus Spindel ist grundsätzlich plausibel, aber noch keine fertige
Konstruktionsfreigabe. Vor Bau klären: Linearführung, axiale Lagerung,
Öffnungsgeschwindigkeit, eindeutiger Öffnungsbezug und Endanschläge.
Empfohlen sind ein Öffnungs-Referenzschalter, eine zweite Endlagenüberwachung
und mechanische Anschläge. Eine lokale I/O-/ADC-Einheit liest Endlagen und
beide Widerstandssensoren; deren Signal gehört nicht auf den TTL-Datenbus.

Der XL330 benötigt seinen passenden Niederspannungsanschluss und eigenen
TTL-Bus. Seine Position liefert nach Neustart keinen ungeprüft gültigen
mehrgängigen Spindelweg. Motorstrom allein beweist keine Griffkraft.
Spindelselbsthemmung kann Druck auch nach einem Motorstopp aufrechterhalten.

Da der Greifer noch nicht konstruiert ist, jetzt Bauraum, Masse und
Kabelweg für einen möglichen Nahbereichssensor mit einplanen (siehe
Kamerastrategie). Alle Leitungen zum Greifer laufen durch J4 und J6; deren
Drehbereich wird dadurch begrenzt.

### Transportpose

stowed existiert als **Name**, noch nicht als vermessene Stellung.
Die Greifmission fährt diese Pose vor einigen Navigationsschritten an;
Erkundungswege sind nicht durchgehend abgesichert. Ein zentraler Fahrvertrag
muss später frische reale Gelenkwerte, Referenzstatus und Stillstand prüfen.

Laut CAD liegt die Transportpose oberhalb der LiDAR-Ebene und ragt mindestens
130 mm vor die Chassisfront, also bis mindestens x = 0,40 m statt 0,27 m vor
der Antriebsachse. Folgen:

- In dieser Höhe erfasst vorn kein Hindernissensor etwas. Der LiDAR scannt
  auf 0,75 m. Die VL53 sitzen auf 0,305 m, schauen geradeaus und decken
  direkt vor dem Roboter nur etwa 0,4 m Höhe ab. Die OAK ist seit dem
  04.11.2026 nicht zur Hinderniserkennung vorgesehen. Überhänge wie
  Arbeitsplatten, Fensterbänke oder Regalböden träfen zuerst den Arm.
- Der lokale Nav2-Footprint reicht bisher bis x = +0,31 m plus 0,02 m
  Polster und kennt den Überstand nicht; auch der Drehkreis wächst.
  Footprint und Kollisionsmonitor sind sicherheitsrelevant und werden in
  einem eigenen, mit der Erkundungslinie abgestimmten Schritt geändert.

Repo-Werte: OAK etwa 1,34 m über Boden, 18,94° nach unten; LiDAR laut
gemessener Konfiguration 0,75 m über Boden. Die bestehende LiDAR-Mastmaske
umfasst 68° im nativen Scan. Abgeschattete Bereiche bleiben unbekannt;
sie dürfen durch eine größere Maske nicht zu freiem Raum erklärt werden.
Pose und Übergangsweg mit leerem Greifer und vorgesehener Last erproben,
einschließlich VL53, Kabeln, Schwerpunkt und Bremsverhalten der Basis.

## Kalibrierung und Kamerastrategie

**Nutzerentscheidung 08.11.2026:** Die OAK-D-S2 dient beim Greifen nur der
Objekterkennung und der Entfernung, damit die Basis weiß, wie weit sie zum
Zielobjekt fahren muss. Ihr Bildwinkel reicht nach Einschätzung des Nutzers
nicht für den Arm-Arbeitsraum.

Überschlagsrechnung mit Repo-Werten (1,34 m Höhe, 18,94° Neigung, etwa 42°
vertikaler Bildwinkel laut `oak_params.yaml`; passt zur gemessenen toten
Zone am Boden von etwa 1,5 m). Eine waagerechte Fläche ist erst ab dieser
Entfernung vor der Chassisfront im Bild:

| Fläche | im Bild ab ca. |
|---|---|
| Arbeitsplatte, 0,90 m | 0,41 m |
| Tischplatte, 0,75 m | 0,58 m |
| Couchtisch, 0,45 m | 0,94 m |
| Boden | 1,5 m |

Mit dem Mast bei etwa x = 0,15 m reicht der gestreckte Arm grob 0,63 m
(ohne Greifer) bis 0,78 m (mit Greifer) über die Chassisfront. Auf
Tischhöhe liegt damit nur der äußerste, gestreckte Rand des Arbeitsraums im
Bild. Die Rechnung bestätigt die Einschätzung des Nutzers; die genaue Grenze
folgt aus dem CAD und einer Messung.

Folgerung, Entscheidung beim Nutzer: Für die Feinlokalisierung im Greifraum
liegt ein Nahbereichssensor am Greifer oder Handgelenk nahe (Eye-in-Hand).
Er misst das Objekt relativ zum Greifer; Mastbiegung, Kippeln der Basis und
Spiel in Hubachse, J1 und J2 wirken dann im letzten Anfahrschritt kaum noch.
Er bringt Masse, Kabel durch J4 und J6, eine eigene Kalibrierung und
Zeitstempelfragen mit.

Für die OAK genügt damit eine Montagegenauigkeit im Zentimeterbereich für
die Anfahrt. Die vorhandenen Werkzeuge in
[handeye_calibration](../src/handeye_calibration/) sind für Eye-to-Hand
gebaut; für eine Handkamera braucht der Löser einen Eye-in-Hand-Modus.
Aktueller optischer Frame der OAK ist oak_rgb_camera_optical_frame. Alte
Beispiel-Frames, Kamerahöhen und Genauigkeitszusagen aus dem
[historischen Kalibrierkonzept](../KONZEPT_KALIBRIERUNG_OAK_ARM.md)
nicht übernehmen.

Grobe Objektsuche darf map verwenden. Feinmanipulation soll mit frischen
Beobachtungen in base_link oder im Greiferframe arbeiten; bestehende
Service-Kommentare und Implementierungen müssen dafür ausdrücklich
abgeglichen werden.

## Nächster konkreter Schritt

1. Offene Hardwareangaben klären: Antrieb und Spindel der Hubachse,
   Antrieb von J6, Bezugspunkt der 746 mm, Not-Aus-Wirkung auf den Jetson.
2. Gewichte von Arm, Greifer und Basis wiegen; danach Momente je Gelenk,
   Kippsicherheit und Mastbelastung rechnen.
3. Kinematik aus dem CAD in den Workspace bringen: am besten als URDF-Export
   aus Fusion 360 mit Gelenkachsen, Ursprüngen und Netzen.
4. Inventarschema in einem eigenen Build um die Hubachse erweitern.
5. Messblatt M0 ausfüllen, danach beaufsichtigte M1A-Leseprobe mit
   bestätigten ESS17. Erst aus diesen Daten einen separaten, begrenzten
   Einzelachs-Bewegungsbuild erstellen.

Keine unbekannten Parameter mit Beispielwerten auffüllen. Reale Bilder,
Karten und Bags bleiben außerhalb des Repos; im Repo nur bereinigte
Messzusammenfassungen und Verweise auf lokale Ablagen.

## Herstellerquellen

- [ESS17-RS07 Produkt](https://www.omc-stepperonline.com/de/ess-serie-0-72nm-101-96oz-in-nema-17-integrierter-rs485-closed-loop-stepper-servomotor-24vdc-1000ppr-ess17-rs07)
- [ESS17 Hardware-Handbuch](https://files.omc-stepperonline.com/ESS17-RS0407_Series_Bus_Integrated_Motor_Hardware_Manual.pdf)
- [Modbus-Funktionshandbuch V1.0](https://files.omc-stepperonline.com/Modbus-Series-Bus-Product-Function-Manual-V1.0_1.pdf)
- [TLE49x5L Datenblatt](https://www.infineon.com/assets/row/public/documents/24/49/infineon-tle49x5l-datasheet-en.pdf):
  Hersteller-Direktlink beim aktuellen Abruf nicht erreichbar; genaue
  Bauteilvariante und aktuelle Originalunterlage vor Verdrahtung beschaffen.
- [XL330-M288](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/) und
  [XL330-M077](https://emanual.robotis.com/docs/en/dxl/x/xl330-m077/):
  tatsächliche Variante noch aufnehmen.
