# Arm-Kontext für Agenten: Amadeus

**Stand: 11.11.2026.** Grundlage sind die am 10.10.2026 aus Gespräch und
Repository rekonstruierten Angaben, die Nutzerangaben vom 08.11.2026
(Gelenkzuordnung, Not-Aus, Rolle der OAK), die Messungen des Nutzers vom
10.11.2026 und die Auswertung des neu konstruierten Arms (STEP-Export vom
11.11.2026, gestreckte Pose). Die Kinematik aus den Exporten vom 09.11.2026
ist überholt: Dort war J2 falsch zusammengebaut.
Der ursprüngliche lokale Wortlaut vom Oktober ist nicht zugänglich. Werte aus
dem CAD sind als solche gekennzeichnet; als „gemessen“ gelten nur ausdrücklich
so bezeichnete Angaben.

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

## Aufbau laut Nutzer und CAD (11.11.2026)

Der Arm sitzt vorn am Kameramast auf einer vertikalen Hubachse. Er hat sechs
Drehgelenke; mit der Hubachse sind es sieben bewegte Achsen, dazu kommt der
Greifer. Die Farben beziehen sich auf das Fusion-360-Modell.

| Achse | Bauteil im CAD | Funktion | Antrieb, Untersetzung |
|---|---|---|---|
| Hubachse | vorhandene vertikale Linearführung mit Spindel | hebt und senkt den ganzen Arm, Hub 400 mm | Motor, Spindeltyp und Steigung offen |
| J1 Schulter heben | große blaue Schulter am Hubschlitten | schwenkt den Arm hoch und runter | NEMA23 der ESS-RS-Reihe, 55,25:1 |
| J2 Schulter seitlich | weiße Schulter, 130 mm vor J1 | schwenkt den Arm seitlich; Achse senkrecht, wenn der Arm waagerecht steht | ESS-RS, 72:1 |
| J3 Ellenbogen | oranges Gelenk | beugt und streckt zwischen Ober- und Unterarm | ESS-RS, 72:1 |
| J4 Unterarm drehen | grünes Gelenk hinter dem Ellenbogen | Drehung um die Unterarmlängsachse | ESS-RS, 72:1 |
| J5 Handgelenk kippen | rotes Gelenk | Querachse zum Unterarm | ESS-RS, 72:1 |
| J6 Greifer drehen | schwarze Anschlussplatte für den Greifer | Drehung um die Greiferlängsachse | Antrieb und Untersetzung offen |

Der Arm wurde am 11.11.2026 neu konstruiert, weil J2 im alten Modell um 90°
falsch eingebaut war. Die Bauteile tragen im neuen STEP ihre Gelenknamen.
Das rote Verbindungsstück zwischen J1 und J2 ist fest. Laut Angabe vom
10.10.2026 sind fünf
ESS17-RS07 und ein NEMA23 vorhanden; welche ESS17 Hubachse, J2–J5 und J6
antreiben, ist offen. Frühere Angaben zu „iCL-Steppern“ sind überholt: Alle
Schrittmotoren sind ESS-RS (Nutzer, 08.11.2026).

**Gemessen am Roboter (Nutzer, 10.11.2026):**

- Mitte der LiDAR-Sichtscheibe 705 mm über Boden.
- Mitte der OAK 1350 mm über Boden.
- Unterkante des Hubschlittens 1140 mm über Boden; im CAD 1150 mm. Die
  Abweichung ist am Roboter nicht mehr änderbar. Mast, Kamera und Arm sitzen
  real damit rund 10 mm tiefer als im CAD.

**Weitere Nutzerangaben:** Reichweite gestreckt etwa 746 mm ohne Greifer,
gemessen ab der vorderen Fläche des Hubschlittens; Greifer bis etwa 150 mm;
Hub 400 mm; Nutzlast höchstens 1 kg. Arm, Greifer und Basis sind noch nicht
gewogen. Die Angabe „Schulter 1106 mm“ vom 08.11.2026 stammte aus dem
fehlerhaften ersten STEP-Export und ist überholt.

**CAD:** maßstäbliches Fusion-360-Modell. Maßgeblich ist der STEP-Export
„Roboter+Arm in komplett gestreckter Position“ vom 11.11.2026; er wurde im
Gespräch übergeben und ist noch nicht im Repository. Ein zweiter Export in
einer möglichen Homing-Position liegt bisher nur als Bild vor. Die Dateien
unter `CAD_usdz Datei/` (09.11.2026) zeigen den alten, falsch
zusammengebauten Arm und eine um 105 mm zu niedrige Basis; sie sind
überholt. Armmotoren, Hubspindel, Hubmotor und Greifer sind nicht
modelliert.

## Kinematik aus dem CAD vom 11.11.2026

Abgeleitet aus Lagerbohrungen und Bauteilnamen des STEP-Exports in
gestreckter Pose, Hub ganz oben. Roboterrahmen: x nach vorn ab
Antriebsachse, y nach links, Höhe über Boden. CAD-Werte; real sitzt der Arm
rund 10 mm tiefer. Die gestreckte Pose dient als Nullpose des Modells.

| Achse | Lage in der gestreckten Pose | Drehachse in der gestreckten Pose |
|---|---|---|
| Hubschlitten | Vorderfläche bei x = 172 mm, Unterkante 1152 mm | Führungsschienen senkrecht |
| J1 | x = 236 mm, 1211 mm hoch | quer (y) |
| J2 | x = 366 mm, y = +139 mm; 130 mm vor J1 | senkrecht (z), rechtwinklig zu J1 |
| J3 | x = 522 mm, 1305 mm hoch; 156 mm vor J2 | quer (y) |
| J4 | Unterarmachse bei y = +225 mm, 1305 mm hoch | Unterarmlängsachse (x) |
| J5 | x = 778 mm, 1306 mm hoch; 257 mm vor J3 | quer (y) |
| J6 | Werkzeugachse bei y = +139 mm, 1307 mm hoch; Flanschfläche bei x = 927 mm, 149 mm vor J5 | Werkzeuglängsachse (x) |

- Die Armachse liegt in der gestreckten Pose 94 mm über der J1-Achse.
- Oberarm und Werkzeug liegen bei y ≈ +139 mm, der Unterarm 86 mm weiter
  links bei y ≈ +225 mm. Der Arm sitzt damit links der Robotermitte; der
  gestreckte Unterarm ragt rund 45 mm über die linke Chassisseite hinaus.
- Gestreckt sind es ab der Schlittenvorderfläche 755 mm bis zur
  Flanschfläche (Nutzerangabe 746 mm) und 656 mm über die Chassisfront
  hinaus; mit 150 mm Greifer rund 806 mm über die Chassisfront.
- J1 und J2 schneiden sich nicht (130 mm Abstand). J3 schneidet J4, J4
  schneidet J5, J5 schneidet J6; J4 und J6 sind 86 mm versetzt. Das
  Handgelenk ist damit nicht kugelförmig, die Gelenkwinkel müssen numerisch
  berechnet werden.

**J2 schwenkt jetzt seitlich.** Die offene Frage vom 10.11.2026 ist damit
erledigt. Rechnerisch (Flanschfläche, Hub oben, übrige Gelenke gestreckt):

| J2 | Flansch x | Flansch y |
|---|---|---|
| 90° nach rechts | 366 mm | −422 mm |
| 30° nach rechts | 852 mm | −141 mm |
| 0° | 927 mm | +139 mm |
| 30° nach links | 852 mm | +420 mm |
| 90° nach links | 366 mm | +700 mm |

Die J2-Achse steht nur senkrecht, solange J1 den Arm waagerecht hält. Bei
anderen J1-Stellungen schwenkt J2 in einer geneigten Ebene.

**Höhenbereich der Flanschfläche (real, rechnerisch, ohne
Kollisionsprüfung):** gestreckt 1297 mm bei Hub oben und 897 mm bei Hub
unten; Unterarm senkrecht nach unten (J3) 890 mm bzw. 490 mm; ganzer Arm
nach unten (J1) 511 mm bzw. 111 mm. Mit 150 mm Greifer ist der Boden bei
Hub unten rechnerisch erreichbar; der Arm hängt dann dicht vor der
Chassisfront und im Sichtbereich von LiDAR und VL53. Grenzwinkel,
Kollisionen mit Mast, Basis und Kamera sowie Kabelwege sind nicht geprüft.

## Gesicherte Angaben und offene Punkte

| Thema | Gesichert | Noch offen |
|---|---|---|
| Achsen | Hubachse und J1–J6 wie oben; J1 mit NEMA23 (ESS-RS); Lage und Abstände aus dem CAD vom 11.11.2026 | Antrieb von Hubachse und J6, Typenschilder, Firmware, Busadressen; Grenzwinkel |
| Getriebe | J1 55,25:1; J2–J5 72:1 | Untersetzung J6, Spindelsteigung, Spiel, Grenzwinkel |
| Halten | Keine Bremsen; Selbsthemmung soll praktisch erprobt werden | Haltevermögen je Gelenk und Hubspindel unter Last, Rücktreiben |
| Not-Aus | Trennt die komplette Stromversorgung des Roboters | Ob auch der Jetson getrennt wird; Verhalten jeder Achse beim Abschalten |
| Bus | Eigener RS485-Adapter für den Arm ist verbaut | Chip, Gerätepfad, udev-Alias, Baudrate, Terminierung |
| Homing | TLE4905L als Referenzgeber vorgesehen | Stückzahl, Magnetlage, Verdrahtung; Referenz und Endlagen der Hubachse |
| Montage | Arm in Einzelteilen; maßstäbliches CAD vorhanden; Hubschlitten-Unterkante gemessen 1140 mm | Montagezustand der Hubachse am Roboter |
| Externer Armcode | Keiner | – |
| Greifer | Noch nicht konstruiert; XL330 mit M6- oder ähnlicher Trapezspindel | XL330-Variante, Steigung, Hub, Führung, Endlagen, Kamerabauraum |
| Kraftfeedback | Zwei Sensoren mit ohmschem Widerstandssignal | Typ, Kennlinie, Elektronik, ADC und Auswertung |
| Vision | OAK-D-S2 nur für Objekterkennung und Anfahrdistanz | Nahbereichssensor für den eigentlichen Griff |
| Transport | Mögliche Homing-Position vom Nutzer konstruiert, bisher nur als Bild | Gelenkwinkel und Geometrie der Pose, Abstand zur LiDAR-Ebene, Überstand, OAK-Sicht, Footprint, Abstützung, Pose mit Greifer und Last |
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

Die Zahlen zur alten Transportpose (rund 4 cm über der LiDAR-Ebene, 136 mm
Überstand) galten für den falsch zusammengebauten Arm und sind überholt. Der
Nutzer hat am 11.11.2026 eine mögliche Homing-Position konstruiert; sie
liegt bisher nur als Bild vor und ist noch nicht ausgewertet. Für jede
Transportpose bleibt zu prüfen:

- Abstand der tiefsten Armstelle zur LiDAR-Ebene (gemessen 705 mm), mit
  Greifer und gegriffenem Objekt, samt der dafür nötigen Hubhöhe.
- Überstand vor und neben dem Chassis. J2 sitzt fest 130 mm vor J1 bei
  x = 366 mm; solange J1 den Arm waagerecht hält, ragt allein das
  J2-Gehäuse rund 160 mm vor die Chassisfront (x = 271 mm).
- Sicht der OAK (siehe Kamerastrategie).

Unverändert gilt für jeden Überstand:

- In Armhöhe erfasst vorn kein Hindernissensor etwas. Der LiDAR scannt
  auf 0,705 m. Die VL53 sitzen auf 0,305 m, schauen geradeaus und decken
  direkt vor dem Roboter nur etwa 0,4 m Höhe ab. Die OAK ist seit dem
  04.11.2026 nicht zur Hinderniserkennung vorgesehen. Überhänge wie
  Arbeitsplatten, Fensterbänke oder Regalböden träfen zuerst den Arm.
- Der lokale Nav2-Footprint reicht bisher bis x = +0,31 m plus 0,02 m
  Polster und kennt keinen Überstand; auch der Drehkreis wächst.
  Footprint und Kollisionsmonitor sind sicherheitsrelevant und werden in
  einem eigenen, mit der Erkundungslinie abgestimmten Schritt geändert.

Die bestehende LiDAR-Mastmaske umfasst 68° im nativen Scan. Abgeschattete
Bereiche bleiben unbekannt; sie dürfen durch eine größere Maske nicht zu
freiem Raum erklärt werden. Pose und Übergangsweg mit leerem Greifer und
vorgesehener Last erproben, einschließlich VL53, Kabeln, Schwerpunkt und
Bremsverhalten der Basis.

## Kalibrierung und Kamerastrategie

**Nutzerentscheidung 08.11.2026:** Die OAK-D-S2 dient beim Greifen nur der
Objekterkennung und der Entfernung, damit die Basis weiß, wie weit sie zum
Zielobjekt fahren muss. Ihr Bildwinkel reicht nach Einschätzung des Nutzers
nicht für den Arm-Arbeitsraum.

Überschlagsrechnung für die heutige Ausrichtung (Kamera gemessen 1,35 m,
18,94° Neigung, etwa 42° vertikaler Bildwinkel laut `oak_params.yaml`; passt
zur gemessenen toten Zone am Boden von etwa 1,5 m). Eine waagerechte Fläche
ist erst ab dieser Entfernung vor der Chassisfront im Bild:

| Fläche | im Bild ab ca. |
|---|---|
| Arbeitsplatte, 0,90 m | 0,41 m |
| Tischplatte, 0,75 m | 0,59 m |
| Couchtisch, 0,45 m | 0,95 m |
| Boden | 1,48 m |

Laut CAD vom 11.11.2026 reicht der gestreckte Arm rund 0,66 m (ohne
Greifer) bis 0,81 m (mit Greifer) über die Chassisfront. Auf Tischhöhe
liegt damit nur der äußerste, gestreckte Rand des Arbeitsraums im Bild. Die
Rechnung bestätigt die Einschätzung des Nutzers.

### OAK-Neigung und Verdeckung durch den Arm

**Ziel des Nutzers:** Die OAK soll Raumgegenstände möglichst gut erkennen,
ohne dass der Arm viel vom Bild verdeckt. Was die Kamera vom Raum sieht,
hängt nur von ihrer Höhe und Neigung ab (16:9 mit etwa 42° vertikal,
gemessene Kamerahöhe 1,35 m, Entfernungen ab Chassisfront):

| Neigung | Tisch 0,75 m ab | Boden ab | Bildoberkante in 3 m |
|---|---|---|---|
| 0° | 1,43 m | 3,37 m | 2,56 m |
| 4° | 1,16 m | 2,76 m | 2,31 m |
| 10° | 0,87 m | 2,11 m | 1,96 m |
| 15° | 0,70 m | 1,73 m | 1,69 m |
| 18,94° (heute) | 0,59 m | 1,48 m | 1,47 m |

Wie viel der Arm verdeckt, hängt von seiner Stellung ab. Die Studie vom
10.11.2026 galt für die alte Transportpose und ist überholt. Simuliert aus
dem CAD vom 11.11.2026 für den gestreckten Arm (keine Messung):

| Hub | verdeckt bei 4° | bei 12° | bei 18,94° |
|---|---|---|---|
| oben | 16 % | 20 % | 24 % |
| 100 mm tiefer | 11 % | 16 % | 20 % |
| 200 mm tiefer | 4 % | 9 % | 14 % |
| unten (400 mm tiefer) | 0 % | 1 % | 4 % |

Der Arm liegt bei Hub oben nur rund 5 cm unter der Kameramitte und links
von ihr; je tiefer der Hub, desto freier das Bild. Für die Wahl der
OAK-Neigung zählt die Verdeckung in der Transport- bzw. Homing-Position;
sie wird berechnet, sobald deren Geometrie vorliegt. Jede neue Neigung oder
Montage muss am Roboter neu gemessen werden (Bodenebene wie am 27.07.2026)
und gehört als eigener, getesteter Sensor-Frame-Schritt in `oak.launch.py`.

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

## Abweichungen zu laufenden Sensor-Frames

Die Messungen vom 10.11.2026 weichen von der laufenden Konfiguration ab:

- LiDAR: `stl27l.yaml` rechnet mit 750 mm Scheibenmitte (z = 0,660 m über
  base_link); gemessen sind 705 mm (z = 0,615 m).
- OAK: `oak.launch.py` rechnet mit 1340 mm (z = 1,25 m über base_link);
  gemessen sind 1350 mm.

Beide Werte gehören zu sicherheitsrelevanten Sensor-Frames. Sie werden hier
nicht geändert, sondern in einem eigenen Schritt nachgemessen, korrigiert
und getestet.

## Nächster konkreter Schritt

1. Homing-Position als STEP-Export oder mit Gelenkwinkeln übergeben; danach
   LiDAR-Abstand, Überstand und OAK-Verdeckung dafür rechnen.
2. Entscheidung zur OAK-Neigung und -Montage anhand dieser Rechnung.
3. Offene Hardwareangaben klären: Antrieb und Spindel der Hubachse,
   Antrieb von J6, Not-Aus-Wirkung auf den Jetson.
4. Gewichte von Arm, Greifer und Basis wiegen; danach Momente je Gelenk,
   Kippsicherheit und Mastbelastung rechnen.
5. URDF des Arms aus den CAD-Achsen erstellen; Nullstellung, Drehrichtungen
   und Grenzwinkel bleiben bis zur Messung offen.
6. Inventarschema in einem eigenen Build um die Hubachse erweitern.
7. Messblatt M0 ausfüllen, danach beaufsichtigte M1A-Leseprobe mit
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
