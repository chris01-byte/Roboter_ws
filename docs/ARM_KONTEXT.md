# Arm-Kontext für Agenten: Amadeus

**Stand: 11.11.2026.** Grundlage sind die am 10.10.2026 aus Gespräch und
Repository rekonstruierten Angaben, die Nutzerangaben vom 08.11.2026
(Gelenkzuordnung, Not-Aus, Rolle der OAK), die Messungen des Nutzers vom
10.11.2026 und die Auswertung des neu konstruierten Arms (zwei STEP-Exporte
vom 11.11.2026: gestreckte Pose und mögliche Homing-/Parkposition). Die
Kinematik aus den Exporten vom 09.11.2026 ist überholt: Dort war J2 falsch
zusammengebaut.
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
Gespräch übergeben und ist noch nicht im Repository. Ein zweiter Export vom
selben Tag zeigt eine mögliche Homing-/Parkposition; auch er liegt nur
außerhalb des Repositorys vor (Auswertung unten). Die Dateien
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

## Park- und Homing-Pose aus dem CAD vom 11.11.2026

Ausgewertet wurde der zweite STEP-Export des Nutzers („mögliche Homing
Position“). Gegenüber der gestreckten Nullpose: Hub ganz oben, J1 −180°,
J2 −40°, J3 −90°, J4 0°, J5 +20°, J6 0°. Die Vorzeichen gelten
rechtshändig um die Achsrichtungen der Kinematiktabelle. Sie sind
Modellkonvention, keine Drehrichtung der Antriebe. Die Fusion-Gelenkwerte
aus den Bildern des Nutzers passen dazu (gleiche Beträge, Vorzeichen in
Fusion teils andersherum). Das Gelenkmodell
gibt den Export auf 0,4 mm genau wieder und ist damit auch abseits der
Nullpose geprüft.

Der Arm klappt über J1 nach hinten, läuft links am Mast vorbei und hängt
hinter dem Mast senkrecht nach unten. Das Handgelenk endet knapp über dem
hinteren Deck. Alle Werte sind aus dem CAD gerechnet, real liegt der Arm
rund 10 mm tiefer; Kabel und Greiferform sind nicht modelliert.

| Prüfgröße | Ergebnis |
|---|---|
| Tiefster Armpunkt | real 698 mm, 7 mm unter der LiDAR-Scheibenmitte; vom LiDAR aus bei 172°–186° hinter dem Mast, also im bereits maskierten Sektor |
| OAK-Bild | 0 % verdeckt bei 16:9 bis etwa 19° Neigung; ab 20° erscheint das J1-Gehäuse am unteren Bildrand, bei 4:3 schon bei 18,94° (rund 8 %) |
| Überstand | vorn 23 mm (J1-Gehäuse); hinten 22 mm über die Chassishinterkante in 0,8–1,2 m Höhe; seitlich innerhalb des Chassis; größter Radius um die Antriebsachsmitte 341 mm, innerhalb des Chassis-Drehkreises |
| Engste Abstände | J1-Gehäuse 7 mm vor dem Hubschlitten (bauartbedingt, in jeder Pose), J2-Gehäuse 23 mm neben dem Mast, Handgelenk 9 mm neben dem Unterarm und 69 mm hinter dem Mast |
| Greifer, 150 mm, nur Mittellinie | hängt fast senkrecht; Spitze real rund 73 mm über dem hinteren Deck |
| Hub nach unten | ohne Greifer rund 164 mm frei, mit 150-mm-Greifer rund 73 mm (real) |

**Freie Richtungen aus der Parkpose.** Jedes Gelenk einzeln gedreht, die
übrigen in Parkpose. Geprüft wurden die CAD-Flächen des Arms und die
Mittellinie eines 150 mm langen Greifers gegen Basis, Mast und die nicht
mitbewegten Armglieder:

| Achse | frei | gesperrt: Arm / Greifermittellinie berührt nach |
|---|---|---|
| Hub | nach unten, siehe oben | oben Hubende |
| J1 | Arm nach hinten-oben, 77° bis zur ersten Berührung | 8° / 8°, Deckschräge hinter dem Mast |
| J2 | vom Mast weg nach links-hinten, über 90° | 33° am Mast / 27° Deckschräge |
| J3 | Unterarm nach hinten-oben, über 90° | über 90° / 13° Deckschräge |
| J4 | über 90° | über 90° / 44° Deckschräge |
| J5 | Greifer nach hinten-oben, über 90° | über 90° / 23° Deckschräge |
| J6 | dreht nur um die Greiferachse | erst mit Greiferform prüfbar |

Für jede Achse bewegt die freie Richtung Handgelenk und Greifer nach hinten
oder oben, weg von Mast und Deck. Dabei wächst der Überstand nach hinten:
J1 allein um 5° ergibt 51 mm, um 10° 86 mm über die Chassishinterkante;
J3 um 10° 56 mm. Fahren J1–J5 nacheinander je 10° aus, ohne
zurückzukehren, sind es 239 mm.

**Schwerkraft in der Parkpose:** Alle Armglieder hinter J1 liegen hinter
und unter der J1-Achse. Ohne Selbsthemmung dreht J1 den Arm stromlos in die
gesperrte Richtung, Handgelenk und Greifer also zur Deckschräge. J2 steht
senkrecht und trägt kein Schwerkraftmoment; Unterarm und Handgelenk hängen
fast senkrecht. Mit dem Hub oben liegt der Armschwerpunkt hoch; Kippsicherheit
in Fahrt erst nach dem Wiegen rechnen.

Das daraus abgeleitete Homing-Konzept steht unter [TLE4905L](#tle4905l) und
ausführlich im [Integrationsplan](INTEGRATIONSPLAN_ARM_SOFTWARE.md#sensorlage-und-referenzfahrt-aus-der-parkpose-konzept-11112026).

## Gesicherte Angaben und offene Punkte

| Thema | Gesichert | Noch offen |
|---|---|---|
| Achsen | Hubachse und J1–J6 wie oben; J1 mit NEMA23 (ESS-RS); Lage und Abstände aus dem CAD vom 11.11.2026 | Antrieb von Hubachse und J6, Typenschilder, Firmware, Busadressen; Grenzwinkel |
| Getriebe | J1 55,25:1; J2–J5 72:1 | Untersetzung J6, Spindelsteigung, Spiel, Grenzwinkel |
| Halten | Keine Bremsen; Selbsthemmung soll praktisch erprobt werden | Haltevermögen je Gelenk und Hubspindel unter Last, Rücktreiben |
| Not-Aus | Trennt die komplette Stromversorgung des Roboters | Ob auch der Jetson getrennt wird; Verhalten jeder Achse beim Abschalten |
| Bus | Eigener RS485-Adapter für den Arm ist verbaut | Chip, Gerätepfad, udev-Alias, Baudrate, Terminierung |
| Homing | TLE4905L mit Einzelmagnet je Achse, in der Parkstellung aktiv; J1 mit mechanischem Anschlag; keine Absolutwertgeber (Nutzer, 11.11.2026); Referenz- und Grenzfunktionen des ESS aus dem Herstellerhandbuch belegt | Gelenkbereich je Achse (Kabel), Fensterbreite, Kantenlage, J1-Anschlagwinkel, Verdrahtung; Referenz und Endlagen der Hubachse; Antriebsfunktionen am Gerät bestätigen |
| Montage | Arm in Einzelteilen; maßstäbliches CAD vorhanden; Hubschlitten-Unterkante gemessen 1140 mm | Montagezustand der Hubachse am Roboter |
| Externer Armcode | Keiner | – |
| Greifer | Noch nicht konstruiert; XL330 mit M6- oder ähnlicher Trapezspindel | XL330-Variante, Steigung, Hub, Führung, Endlagen, Kamerabauraum |
| Kraftfeedback | Zwei Sensoren mit ohmschem Widerstandssignal | Typ, Kennlinie, Elektronik, ADC und Auswertung |
| Vision | OAK-D-S2 nur für Objekterkennung und Anfahrdistanz | Nahbereichssensor für den eigentlichen Griff |
| Transport | Homing-/Parkposition des Nutzers als STEP ausgewertet (11.11.2026): hinter dem Mast, außerhalb des OAK-Bildes, im maskierten LiDAR-Sektor | Abstützung, Pose mit Greifer und Last, Kabel, Footprint hinten, Kippsicherheit, praktische Prüfung |
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

**Festlegungen des Nutzers vom 11.11.2026:** ein Einzelmagnet je Achse,
kein Magnetbogen; J1 bekommt einen mechanischen Anschlag; Absolutwertgeber
sind konstruktiv nicht mehr möglich; die Parkposition steht fest.

**Konzept daraus (Einzelheiten und Register im
[Integrationsplan](INTEGRATIONSPLAN_ARM_SOFTWARE.md#sensorlage-und-referenzfahrt-aus-der-parkpose-konzept-11112026)):**

- Die Motorgeber der ESS zählen inkrementell, und der Motor dreht je
  Gelenkumdrehung 72-mal (J1: 55,25-mal). Nach jedem Einschalten wird daher
  jede Achse neu referenziert, solange nicht gemessen ist, dass Zähler und
  Stellung einen Stromausfall überstehen.
- Sensor am Gelenkausgang, nicht am Motor: fest an dem Teil, das den
  Antrieb trägt, Magnet auf dem Abtrieb. Am Motor würde er 72-mal je
  Gelenkumdrehung schalten.
- Sensorstellung: In der Parkstellung steht der Magnet dem Sensor
  gegenüber, der Sensor ist aktiv. Referenz ist das Ende des Schaltfensters
  auf der freien Seite, wenige Grad hinter der Parkstellung; der Rest des
  Fensters überdeckt Parkstellung, Spiel, Durchhängen und bei J1 den
  Anschlag.
- Ein Einzelmagnet zeigt außerhalb seines Fensters nicht, auf welcher Seite
  das Gelenk steht. Referenziert wird deshalb nur aus der Parkstellung bei
  aktivem Sensor; sonst folgt eine beaufsichtigte Rückführung.
- Überfahrschutz in Schichten: Suchfahrt als Positionsfahrt mit festem
  Höchstweg, begrenzter Strom und Schleppfehler, nach der Referenz
  Soft-Limits im Antrieb und im Jetson, zuletzt mechanische Anschläge.
- J1-Anschlag höchstens 1–2° hinter der Parkstellung (Richtung Deck). Laut
  CAD hat die Mittellinie eines 150-mm-Greifers dann noch rund 64–77 mm
  (CAD) bzw. 54–67 mm (real) Abstand zur Deckschräge, bei 4° nur noch rund
  29 mm (real).
- Hubachse ebenso: Parkpose oben, Kante wenige Millimeter darunter,
  Referenzfahrt nach unten.

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
  nicht vom Haltemoment der Antriebe abhängen. In der Parkpose vom
  11.11.2026 trägt nur J1 ein nennenswertes Schwerkraftmoment, und zwar zur
  gesperrten Seite: Ohne Selbsthemmung setzen Handgelenk oder Greifer nach
  höchstens 8° auf der Deckschräge auf. Der Nutzer baut dafür einen
  J1-Anschlag auf der Parkseite (11.11.2026); er hält den Arm stromlos in
  definierter Lage, das Schaltfenster von J1 überdeckt ihn.

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
Überstand) galten für den falsch zusammengebauten Arm und sind überholt.
Die vom Nutzer am 11.11.2026 konstruierte Homing-/Parkposition eignet sich
rechnerisch auch als Transportpose (Werte unter
[Park- und Homing-Pose](#park--und-homing-pose-aus-dem-cad-vom-11112026)):
Sie liegt hinter dem Mast, ihr tiefster Punkt im bereits maskierten
LiDAR-Sektor, außerhalb des OAK-Bildes und vorn wie hinten nur rund 2 cm
über dem Chassis. Offen bleiben:

- Pose mit Greifer und gegriffenem Objekt. Der hängende Greifer reicht unter
  die LiDAR-Ebene; er und ein gehaltenes Objekt müssen im maskierten Sektor
  bleiben.
- Kabel, mechanische Abstützung, Schwerpunkt mit Hub oben und Fahrverhalten.
- Der Nav2-Footprint kennt hinten keinen Überstand (siehe unten).
- Arbeitsposen mit waagerechtem Arm: J2 sitzt fest 130 mm vor J1 bei
  x = 366 mm; dann ragt allein das J2-Gehäuse rund 160 mm vor die
  Chassisfront (x = 271 mm).

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

Der gestreckte Arm liegt bei Hub oben nur rund 5 cm unter der Kameramitte
und links von ihr; je tiefer der Hub, desto freier das Bild. In der
Parkpose vom 11.11.2026 liegt der Arm bei 16:9 bis etwa 19° Neigung ganz
außerhalb des Bildes; erst ab 20° erscheint das J1-Gehäuse am unteren Rand.
Die Parkpose schränkt die Neigungswahl damit nicht ein. Die Neigung kann nach
der gewünschten Raumsicht (Tabelle oben) gewählt werden; Verdeckung entsteht
nur in Arbeitsposen. Jede neue Neigung oder
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

1. Sensor und Magnet je Achse einschließlich Hubachse so setzen, dass sie
   sich in der Parkstellung gegenüberstehen (im Fusion-Modell in der Pose der
   Homing-STEP); Fensterende auf der freien Seite; J1-Anschlag höchstens
   1–2° hinter der Parkstellung.
2. Gelenkbereich je Achse angeben (Kabel- und mechanische Grenzen); daraus
   Soft-Limits und Höchstwege der Suchfahrt ableiten. Antriebsfunktionen aus
   dem Handbuch (Integrationsplan, Abschnitt 5) am Gerät bestätigen.
3. Entscheidung zur OAK-Neigung nach der Raumsicht; die Parkpose schränkt
   sie nicht ein.
4. Offene Hardwareangaben klären: Antrieb und Spindel der Hubachse,
   Antrieb von J6, Not-Aus-Wirkung auf den Jetson.
5. Gewichte von Arm, Greifer und Basis wiegen; danach Momente je Gelenk,
   Kippsicherheit und Mastbelastung rechnen.
6. URDF des Arms aus den CAD-Achsen erstellen; Nullstellung, Drehrichtungen
   und Grenzwinkel bleiben bis zur Messung offen.
7. Inventarschema in einem eigenen Build um die Hubachse erweitern.
8. Messblatt M0 ausfüllen, danach beaufsichtigte M1A-Leseprobe mit
   bestätigten ESS17. Dabei ohne Bewegung prüfen: Eingangszustand beim
   Vorbeiführen des Magneten von Hand und Positionszähler vor und nach
   einem Aus- und Einschalten. Erst aus diesen Daten einen separaten,
   begrenzten Einzelachs-Bewegungsbuild erstellen.

Keine unbekannten Parameter mit Beispielwerten auffüllen. Reale Bilder,
Karten und Bags bleiben außerhalb des Repos; im Repo nur bereinigte
Messzusammenfassungen und Verweise auf lokale Ablagen.

## Herstellerquellen

- [ESS17-RS07 Produkt](https://www.omc-stepperonline.com/de/ess-serie-0-72nm-101-96oz-in-nema-17-integrierter-rs485-closed-loop-stepper-servomotor-24vdc-1000ppr-ess17-rs07)
- [ESS17 Hardware-Handbuch](https://files.omc-stepperonline.com/ESS17-RS0407_Series_Bus_Integrated_Motor_Hardware_Manual.pdf)
  (V1.0 vom 15.04.2025)
- [Modbus-Funktionshandbuch V1.0](https://files.omc-stepperonline.com/Modbus-Series-Bus-Product-Function-Manual-V1.0_1.pdf)
  (05.03.2025; gilt für ESS17-RSx1 und ESS23-RSx1). Der Herstellerserver
  lehnte am 11.11.2026 den automatischen Abruf ab; der Nutzer hat beide
  PDFs bereitgestellt, Seitenangaben im Integrationsplan beziehen sich auf
  diese Fassungen.
- [TLE49x5L Datenblatt](https://www.infineon.com/assets/row/public/documents/24/49/infineon-tle49x5l-datasheet-en.pdf):
  Hersteller-Direktlink beim aktuellen Abruf nicht erreichbar; genaue
  Bauteilvariante und aktuelle Originalunterlage vor Verdrahtung beschaffen.
- [XL330-M288](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/) und
  [XL330-M077](https://emanual.robotis.com/docs/en/dxl/x/xl330-m077/):
  tatsächliche Variante noch aufnehmen.
