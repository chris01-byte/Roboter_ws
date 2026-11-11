# Integrations- und Stufenplan: Amadeus-Arm, Greifer und OAK

**Stand: 10.10.2026 — aus dem Gespräch rekonstruiert und mit dem gesicherten
Repo-Stand abgeglichen; ergänzt am 08.11.2026 um Nutzerangaben zu Aufbau,
Maßen, Not-Aus und Rolle der OAK, am 11.11.2026 um den neu konstruierten Arm.** Dies ist eine inhaltliche Neufassung,
keine behauptete Wiederherstellung des ursprünglichen Wortlauts. Sie ersetzt
die bisherige Planfassung mit falschen Angaben zu sechs ESS17 und externem
Foxy-Code.

Einstieg: [Arm-Kontext](ARM_KONTEXT.md).
Versuche: [Inbetriebnahme-Messblatt](ARM_INBETRIEBNAHME_MESSBLATT.md).
Umgesetzte Änderungen: [Build-Protokoll](ARM_BUILDPROTOKOLL.md).

## 1. Ziel, Arbeitsweise und aktueller Stand

Langfristig erkennt die OAK ein Objekt, beispielsweise eine Colaflasche.
Der Roboter lokalisiert einen erreichbaren Greifbereich, greift kontrolliert,
prüft den Griff und kann das Objekt später mit der mobilen Basis transportieren.

**Das jetzt vereinbarte erste Ziel ist ausschließlich Arm-Inbetriebnahme.**
Flaschengröße, Füllung und Tischversuch sind noch nicht als erste Abnahme festgelegt.

Der Nutzer übernimmt Aufbau und reale Erprobung; der Softwareagent entwickelt
Werkzeuge, prüfbare Änderungen und Versuchsanweisungen und wertet Rückmeldungen
aus. Jeder Versuch hat vorher festgelegte Grenzen, Abbruchbedingungen und ein
Messprotokoll. Fehlende Daten bleiben offen. Nach einem Fehlschlag wird zuerst
die Ursache eingegrenzt, nicht gleichzeitig an mehreren Parametern gedreht.

Kennzeichnungen in diesem Plan:

- **Bestätigt:** Nutzerangabe oder ausdrücklich referenzierter Repo-Nachweis.
- **Implementiert:** Code vorhanden; der Testumfang wird gesondert genannt.
- **Vorgeschlagen:** Entwurfsentscheidung, vor dem betroffenen Build zu prüfen.
- **Offen:** Noch zu messen oder zu entscheiden, keine Freigabe.

### Bestätigte Hardwareangaben

| Komponente | Stand |
|---|---|
| Arm | Vorn am Kameramast: vertikale Hubachse (400 mm) plus sechs Drehgelenke J1–J6; Zuordnung in [ARM_KONTEXT](ARM_KONTEXT.md) |
| Antriebe | Alle Schrittmotoren ESS-RS; J1 NEMA23 mit 55,25:1, J2–J5 mit 72:1; Antrieb von Hubachse und J6 offen |
| Maße | Gemessen 10.11.2026: LiDAR-Scheibenmitte 705 mm, OAK-Mitte 1350 mm, Hubschlitten-Unterkante 1140 mm (CAD 1150 mm). Reichweite gestreckt ca. 746 mm ab Schlittenvorderfläche ohne Greifer, Greifer bis ca. 150 mm; Nutzlast höchstens 1 kg. Kinematik aus dem korrigierten CAD in [ARM_KONTEXT](ARM_KONTEXT.md) |
| Montage | Arm in Einzelteilen; maßstäbliches Fusion-360-Modell vorhanden |
| Halten | Keine Bremsen; Selbsthemmung von Gelenken und Hubspindel ist unter Last praktisch nachzuweisen |
| Not-Aus | Trennt die komplette Stromversorgung des Roboters |
| Bus | Eigener RS485-Adapter für den Arm verbaut |
| Referenzgeber | TLE4905L vorgesehen; Stückzahl, Montage und Eingang je Gelenk aufnehmen |
| Armcode außerhalb des Repos | Laut Nutzer keiner |
| Greifer | Noch nicht konstruiert; Parallelgreifer mit XL330 und M6- oder ähnlich großer Trapezspindel |
| Griffmessung | Zwei ohmsche Drucksensoren; Typen, Kennlinien und Auswerteelektronik offen |
| Kamera | OAK-D-S2 am Mast nur für Objekterkennung und Anfahrdistanz; Nahbereichssensor für den Griff offen |
| Fahrpose | Arm am 11.11.2026 neu konstruiert; Homing-/Parkposition als STEP ausgewertet: hinter dem Mast, im maskierten LiDAR-Sektor, außerhalb des OAK-Bildes; Abstützung, Kabel und Last offen |
| Achsrichtung J2 | Seit der Neukonstruktion vom 11.11.2026 senkrecht bei waagerechtem Arm; J2 schwenkt seitlich |

### Softwarebestand nach Build A

[arm_hardware](../src/arm_hardware/README.md),
[arm_tools](../src/arm_tools/README.md) und
[arm_bringup](../src/arm_bringup/README.md) enthalten Inventarprüfung,
synthetische Testdaten, Fake-Transport und eine eng begrenzte ESS17-Rohdiagnose.
32 Tests sowie Paketinstallation und Humble-Build sind auf Commit 9e65e4f
bestanden; [CI-Nachweis](https://github.com/chris01-byte/Roboter_ws/actions/runs/38070478719).

**Nicht abgenommen:** Jetson-Installation dieser Pakete, realer Arm-Bus,
Homing, Motorbewegung, Gelenkskalierung, Grenzen, Trajektorien und Greifer.
Noch kein ros2_control-SystemInterface, MoveIt-Armmodell oder realer Arm-Actionserver.
JSON-Diagnose ist kein implementierter ROS-ArmStatus.

## 2. Architektur als Einheit im Roboter

~~~text
ESS-Achsen -- dedizierter RS485-Bus -- ein Bus-Eigentümer
                                       |
                              arm_hardware / Armzustand
                                       |
                         vermessener Bewegungscontroller
                                       |
                           ros2_control / MoveIt (Ziel)
                                       |
                            öffentliche Arm-Actions
                                       |
                                Missionssteuerung
                                       |
                          gemeinsame Basis-/Armsperren

XL330 -- eigener TTL-Bus -- Greifercontroller + lokale Sensor-/Endlagen-I/O
OAK -- vorhandene RGB-D-Pipeline -- Feinpose -- Greifplanung
~~~

Ein Bus wird von genau einem Prozess kontrolliert. Diagnosewerkzeug und
späterer Treiber dürfen ihn nicht gleichzeitig öffnen. Der Arm erhält einen
eigenen bestätigten Adapterpfad; der Fahrbasisport wird nicht übernommen.

| Baustein | Verantwortung und Ausbau |
|---|---|
| arm_hardware | Heute Python-Diagnose; später echte Rückmeldung, Referenzzustand, Fehler und begrenzte Befehle |
| arm_tools | Heute Validierung/Fake/RO-Probe; später getrenntes Einzelachs-Commissioning |
| arm_bringup | Heute Inventare; später geprüfte Controllerparameter, Betriebsarten und gezieltes Starten |
| robot_description | Reale Gelenkachsen, Gliedermaße, Kollisionskörper und Werkzeug-TCP |
| robot_moveit_config, geplant | Planungsgruppe, geprüfte Limits und benannte Posen |
| arm_action_server, geplant | Vorbedingungen, Ausführung, Abbruch und verifiziertes Ergebnis |
| Greifercontroller, geplant | XL330, Öffnungsbezug, Kontakt-/Kraftzustand und Fehlerreaktion |
| handeye_calibration | Vorhandenen Recorder/Löser prüfen und an reale Frames anpassen |
| semantic_perception | Vorhandene Wahrnehmung um aktuelle, greiftaugliche Feinpose ergänzen |
| Basis-/Arm-Interlock, geplant | Gegenseitige Bewegungsfreigabe unabhängig vom einzelnen Missionsbaum |

Die heutigen Python-Bibliotheken sind nicht automatisch ein
ros2_control-Plugin. Ob dessen Buszugriff später in C++ entsteht oder über
einen klaren, zeitlich geprüften Backend-Vertrag erfolgt, wird nach M3 entschieden.
Dabei bleibt der Bus-Eigentümer eindeutig.

Vorhandene Außenverträge beibehalten:
[MoveArmToNamed](../src/robot_interfaces/action/MoveArmToNamed.action),
[MoveArmToPose](../src/robot_interfaces/action/MoveArmToPose.action),
[ComputeGrasp](../src/robot_interfaces/srv/ComputeGrasp.srv) und
[RefineObjectPose](../src/robot_interfaces/srv/RefineObjectPose.srv).
Die Greifer-Action heißt im bisherigen Ablauf
/gripper_controller/gripper_cmd. Schnittstellendefinitionen beweisen keine
realen Server. map-Kommentare in den Greif-/Feinpose-Services sind vor M7/M8
mit dem beabsichtigten base_link-Vertrag abzugleichen; nicht still umdeuten.

## 3. Datenvertrag: Nullpunkt, Homing und Grenzen

Das aktuelle, strikte JSON-Schema liegt in
[config.py](../src/arm_hardware/arm_hardware/config.py), das ungemessene Inventar in
[arm_inventory.json](../src/arm_bringup/config/arm_inventory.json).
Neue Messfelder zuerst im Messblatt aufnehmen; das Schema lehnt unbekannte
JSON-Schlüssel ab. Eine spätere Erweiterung braucht einen eigenen Code-Build.

Je Achse getrennt bestimmen:

- Physischer Motor, Modell, Firmware, Gelenk, bestätigte Adresse und Leseprofil.
- Getriebeübersetzung, Gelenkachse und positive ROS-Drehrichtung.
- Feedback-Counts und Befehls-Counts je Motorumdrehung, Wortfolge,
  Vorzeichen, Überlauf und Verhalten nach Neustart.
- Lage der Home-Schaltkante, Anfahrrichtung und gemessene Streuung.
- Abstand von dieser Kante zum geometrischen Nullwinkel: **Home-Offset**.
- Mechanische Endlagen, daraus abgeleitete engere Softwaregrenzen sowie
  Geschwindigkeits-/Beschleunigungsgrenzen und Nachlauf.
- Homing-Suchweg und -Zeit: Diese begrenzen die Referenzfahrt und sind
  etwas anderes als Home-Offset oder regulärer Arbeitsbereich.

Nicht gleichsetzen: Encoder-PPR, Motor-Schritte, Mikrosteps, Befehlszählung,
Feedbackzählung und Gelenkwinkel. Die am Fahrantrieb gefundenen ESS23-Werte
sind keine Armkalibrierung.

Eindeutige spätere Rechenkonvention, erst nach Messung verwenden:

~~~text
q = s * 2*pi * (C_feedback - C_home) / (N_feedback * G) + q_home
~~~

Dabei ist G = Motorumdrehungen/Gelenkumdrehung, s das gemessene Vorzeichen,
C_home die Rückmeldung an der reproduzierten Referenzkante und q_home deren
Winkel im geometrischen Gelenkkoordinatensystem. Ein Befehlspfad bekommt seine
eigene gemessene Skalierung und einen passenden Befehlsbezug.
home_offset_rad ist vor Umsetzung eindeutig auf diese Konvention abzubilden;
nicht zwei Nullpunktkorrekturen gleichzeitig anwenden.

Die Laufzeitaussage „referenziert“ wird nicht aus einer gespeicherten Nullzahl
oder einer vorhandenen Konfigurationsdatei abgeleitet. Nach unklarer Lage,
Versorgungsverlust, relevantem Encoderfehler oder mechanischem Umbau ist sie
ungültig, bis eine definierte Wiederherstellung erfolgt.

## 4. Lokale Zustände und Bewegungssperren

Vorgeschlagene Laufzeitzustände: OFFLINE, READ_ONLY, UNREFERENCED, HOMING,
READY, EXECUTING, HOLDING, FAULT und ESTOP. Dazu je Achse Referenzgültigkeit,
Messwertalter, Fehlerursache und Konfigurations-ID. Sie sind noch nicht implementiert.

Vor dem ersten Einzelachs-Jog müssen lokale Versuchssperren wirksam sein.
Vor koordinierter Bewegung müssen zusätzlich die Plattform-Interlocks geprüft sein:

- Armbewegung nur bei nachgewiesen stillstehender, gegen Fahrt gesperrter Basis.
  Ein gesendetes cmd_vel=0 allein ist kein Stillstandsnachweis.
- Basisfahrt nur mit frischer, verifizierter Transportpose und gültiger
  Referenz, passendem Lastzustand und gültigem Sensor-/Sicherheitszustand.
- Fehlende, veraltete oder widersprüchliche Rückmeldung sperrt neue Bewegungen.
- Stop, Action-Cancel, Fehler, Not-Aus und Wiederanlauf haben explizite,
  getestete Übergänge; kein automatisches Weiterfahren nach Reconnect.
- Bei einem Fehler laufende Bewegungen über den geprüften Stopweg beenden.
  „Torque off“ ist bei einem ungebremsten Arm nicht automatisch sicher:
  Halten, Abstützen und Energieabschaltung müssen mechanisch zusammenpassen.

Der [safety_monitor](../src/safety_monitor/safety_monitor/safety_monitor_node.py)
hat eine GPIO-Platzhalteranbindung und initial_estop=false als Code-Default.
Ein empfangenes false ist daher kein belegter physischer Not-Aus-Zustand.
Für den Arm werden gültige Herkunft, Frische und tatsächliche Verdrahtung
gefordert. Die hardwired Kette bleibt unabhängig von ROS.

### Not-Aus trennt die gesamte Versorgung (Nutzerangabe 08.11.2026)

Damit werden alle Armachsen, die Hubachse und der Greifer gleichzeitig
stromlos. Ohne Bremsen hält dann nur Selbsthemmung. Daraus folgen
Prüfpflichten vor dem ersten belasteten oder angehobenen Betrieb:

- Haltevermögen je Gelenk und der Hubspindel stromlos unter definierter
  Last messen. Nicht jede Spindelsteigung ist selbsthemmend; fällt die
  Hubachse durch, sinkt der Arm um bis zu 400 mm.
- Nach jedem Not-Aus gilt die Referenz als verloren, bis gemessen ist, ob
  die ESS-Antriebe ihren Positionszähler über einen Stromausfall halten.
  Die Wiederherstellung muss aus jeder zulässigen Stellung kollisionsfrei
  referenzieren, auch mit Objekt im Greifer.
- Ein stromlos selbsthemmender Arm hält auch eine eingeklemmte Hand fest.
  Eine manuelle Entlastung gehört in die Konstruktion.
- Offen ist, ob der Not-Aus auch den Jetson abschaltet; davon hängen
  Neustartablauf und Datensicherheit laufender Dienste ab.
- Vorgeschlagen: Transportpose mechanisch abstützen, damit Fahrt und
  Not-Aus nicht vom Haltemoment der Antriebe abhängen. In der Parkpose vom
  11.11.2026 zieht die Schwerkraft J1 zur gesperrten Seite; ein Anschlag
  oder eine Auflage dort hält den Arm stromlos in definierter Lage.

## 5. TLE4905L: Wohin gehört das Homing-Signal?

**Vorgeschlagen: an einen als Referenzeingang konfigurierten digitalen Eingang
des zugehörigen ESS-Antriebs.** Der Antrieb erfasst die Schaltkante lokal;
der Jetson startet später die begrenzte Referenzfahrt und überwacht Status.
Die präzise Kante soll nicht erst durch ROS-Polling und einen USB-Umweg entstehen.

ESS17 besitzt X0–X3 und XCOM. Beispielplanung: X0 als Home-Sensor, weitere
Eingänge bei Bedarf für positive/negative Endlagen. Das ist eine Belegungsidee,
keine bereits bestätigte Verdrahtung. „Home-Sensor“ und „Homing starten“
sind unterschiedliche Eingangsfunktionen. Beim NEMA23 in J1 (ESS-RS-Reihe,
genauer Typ offen) ist die entsprechende Belegung separat zu klären.

Der TLE4905L ist ein Hall-Schalter mit Open-Collector-Ausgang Q. Er liefert
kein fertiges 3,3-V-GPIO-Signal. Empfohlener Aufbau zur Auslegung:

~~~text
TLE: VS -> geregelte Sensorversorgung (z. B. 5 V), GND -> Sensorbezug
     Q  -> geeignete Signalaufbereitung / NPN-Sink-Ausgang
                         |
                         +-> ESS X0 (oder bestätigter anderer Eingang)

ESS-NPN-Eingangsseite: XCOM -> +24 V I/O
                      Sink-Ausgang schaltet Xi gegen I/O-0 V
~~~

Bei nicht isolierter Signalaufbereitung brauchen Sensor und I/O eine definierte
gemeinsame Referenz; bei isolierter Kopplung bleibt die Trennung bestehen.
Versorgung, Pinansicht, Pull-up, Ausgangsspannung und Strom sind vor dem Bau
anhand der konkreten Schaltung zu prüfen. Kein paralleler direkter Anschluss
der 24-V-Eingangsleitung an Jetson-/MCU-GPIO.

Das ESS17-Handbuch nennt mindestens 10 mA Ansteuerung und eine Signaldauer
über 10 ms. Daher Kopplung und Magnetbreite zur maximalen Suchgeschwindigkeit
auslegen. Ein direkter Q-Xi-Anschluss kommt nur nach bestätigter elektrischer
Kompatibilität in Frage; die Pufferstufe ist die vorgeschlagene robuste Variante.
Handbuch: [ESS17, Abschnitte 4.2/4.3](https://files.omc-stepperonline.com/ESS17-RS0407_Series_Bus_Integrated_Motor_Hardware_Manual.pdf).
Sensorreferenz: [Infineon TLE49x5L](https://www.infineon.com/assets/row/public/documents/24/49/infineon-tle49x5l-datasheet-en.pdf).
Der Hersteller-Direktlink war beim aktuellen Abruf nicht erreichbar;
Originaldatenblatt und konkrete Pinansicht vor Verdrahtung beschaffen.

Vor Bewegung: Magnet von Hand an/weg, Signalzustand elektrisch und über
Eingangsstatus prüfen; danach Kabelbruch, Kurzschluss und Neustart betrachten.
Eine einfache Open-Collector-Leitung erkennt Drahtbruch nicht automatisch.
Eingangsfunktion und Polarität nach Power-Cycle erneut prüfen. Die heutige
RO-Probe schreibt diese Konfiguration ausdrücklich nicht.

Home ist nicht automatisch ein Endschalter oder eine sichere Endlagenbegrenzung.
Mechanische Anschläge, unabhängige Endlagen und begrenzte Suchwege gesondert
auslegen. Ein fehlendes Home-Signal darf keine endlose Suche auslösen.

Die Hubachse ist linear und braucht neben der Referenz Endlagen an beiden
Hubenden. Ihr Weg wird in Metern geführt, die Spindelsteigung ersetzt die
Getriebeübersetzung. Das heutige Inventarschema kennt nur Winkelachsen und
muss dafür erweitert werden.

### Sensorlage und Referenzfahrt aus der Parkpose (Konzept 11.11.2026)

**Vorschlag, Bestätigung durch den Nutzer offen.** Grundlage ist die
Parkpose aus dem CAD vom 11.11.2026 mit ihren freien und gesperrten
Richtungen ([ARM_KONTEXT](ARM_KONTEXT.md#park--und-homing-pose-aus-dem-cad-vom-11112026)).

Warum überhaupt Homing: Die ESS-Motorgeber zählen inkrementell. Der Motor
dreht je Gelenkumdrehung 72-mal (J1: 55,25-mal); ein Motorwinkel ist also
kein Gelenkwinkel. Ob der Zähler einen Stromausfall übersteht, ist offen,
und ohne Bremsen kann sich der Arm stromlos bewegen. Bis zum Gegenbeweis
sind nach jedem Einschalten alle Achsen UNREFERENCED.

1. **Sensor am Gelenkausgang.** Der TLE4905L sitzt fest an dem Glied, das
   den Antrieb der Achse trägt; seine Leitung führt dann ohne
   Gelenkdurchgang zum ESS-Eingang. Die Magnetspur sitzt auf dem Abtrieb,
   möglichst weit außen: Der Winkelfehler ist die Streuung des Schaltwegs
   geteilt durch den Radius.
2. **Sektor statt Punkt.** Die Spur ist so lang, dass der Sensor in der
   Parkpose sicher aktiv ist, auch mit Spiel, Durchhängen oder an einer
   Parkauflage. Sie überdeckt die gesperrte Seite und endet wenige Grad
   neben der Parkpose auf der freien Seite. Dieses Ende ist die
   Referenzkante. Die Parkpose selbst taugt nicht als Referenzpunkt: Sie
   streut, und ein Sensor, der genau dort schaltet, wäre beim Einschalten
   mehrdeutig.
3. **Aktiv bedeutet Magnet erkannt.** Ein Drahtbruch erscheint dann als
   „nicht in Parkpose“ und sperrt die automatische Referenzfahrt. Die Spur
   muss lückenlos schalten; zwischen Einzelmagneten darf das Signal nicht
   abfallen.
4. **Referenzfahrt je Achse.** Start nur bei aktivem Sensor. Begrenzte
   Relativbewegung in die freie Richtung, langsam, bis zur Flanke von aktiv
   nach inaktiv; bei Bedarf zurück in den Sektor und ein zweites Mal
   langsamer anfahren. Der Suchweg ist kleiner als der freie Korridor;
   endet er ohne Flanke, folgt FAULT. Kein Drehzahlbefehl ohne Weggrenze,
   damit auch ein Busausfall die Achse innerhalb des Korridors stoppt.
5. **Reihenfolge.** Hubachse, J1, J2, J3, J4, J5, J6; jede Achse einzeln
   aus der Parkpose und referenziert zurück, bevor die nächste startet. So
   bleibt der Überstand hinten klein (J1 um 5°: 51 mm über die
   Chassishinterkante). Fahren J1–J5 ohne Rückkehr je 10° aus, sind es
   239 mm. Hinter dem Roboter muss für die Referenzfahrt Platz sein.
6. **Startlogik.** Sind alle Sensoren aktiv und ist die Sichtprüfung
   bestätigt, ist die automatische Referenzfahrt erlaubt. Ist mindestens ein
   Sensor inaktiv, steht der Arm nicht in der Parkpose, etwa nach einem
   Not-Aus mitten in einer Bewegung. Dann gibt es keine automatische
   Bewegung, sondern eine beaufsichtigte Rückführung im Tippbetrieb mit
   reduzierter Geschwindigkeit, bis alle Sensoren aktiv sind. Die zuletzt
   geloggte Gelenkstellung darf dabei als Hinweis dienen, nie als Referenz.
7. **Laufende Plausibilisierung.** Nach dem Referenzieren muss der Sensor
   bei jeder Überfahrt an der gespeicherten Kante schalten. Eine Abweichung
   über der gemessenen Streuung bedeutet Referenzverlust oder Rutschen im
   Antriebsstrang und führt zu FAULT.
8. **Ausführung.** Ob der ESS die Referenzfahrt mit Home-Eingang selbst
   ausführt, ist offen; der Abruf des Modbus-Handbuchs war am 11.11.2026
   gesperrt. Rückfallweg: Der Jetson fährt die begrenzte Schleichfahrt und
   liest Eingänge und Position aus dem Block 0x0006, den die Read-only-Probe
   schon liest. Der zufällige Kantenfehler beträgt dann höchstens
   Schleichgeschwindigkeit mal Abfrageabstand; die feste Verzögerung des
   Eingangsfilters geht in den Home-Offset ein. Beides wird in M2 gemessen.

Achsbezogen nach CAD: Die freie Richtung führt für die Hubachse nach unten,
für J1–J5 bewegt sie Handgelenk und Greifer nach hinten oder oben. J1 ist
die kritische Achse: In der gesperrten Richtung setzt das Handgelenk nach 8°
auf der Deckschräge auf, und dorthin zieht auch die Schwerkraft. J4 und J6
brauchen wegen der Leitungen durch die Gelenke zusätzlich eine mechanische
Drehbegrenzung; ihr Sektor gibt die Richtung zur Kante an.

**Alternative, Entscheidung beim Nutzer:** Absolutwertgeber am
Gelenkausgang kennen die Stellung sofort nach dem Einschalten. Dann könnte
der Arm nach einem Not-Aus aus jeder Stellung selbst einen kollisionsfreien
Rückweg planen. Das kostet eigene Elektronik, Leitungen durch die Gelenke
und eine eigene Kalibrierung; entschieden werden muss vor der Konstruktion
der Gelenkabtriebe.

## 6. Greifer: Konzept vor dem Bau prüfen

**Das XL330-Spindelprinzip ist als Entwurf plausibel; die endgültige Auslegung
ist noch offen.** Vor Fertigung sind Öffnungsweite, Last, Zielkraft,
Schließzeit, Spindelsteigung und genaue XL330-Variante gemeinsam festzulegen.

### Mechanik

Vorgeschlagen sind eigenständige Linearführungen für die Backen, abgestützte
Spindel-Axiallager und eine Kupplung, die den Servo nicht als Schub-/Führungslager
missbraucht. Austauschbare, nachgiebige Fingerauflagen sollen beide Sensoren
definiert belasten. Seitliche Lasten dürfen die Sensoren nicht unkontrolliert biegen.

Symmetrische Backenbewegung hält den Greifmittelpunkt beim Schließen stabil.
Bei einer festen und einer bewegten Backe wandert er; das ist möglich, muss aber
im TCP-/Greifmodell berücksichtigt werden. Zwei gegenläufige Gewinde bzw.
geeignete Koppelmechanik sind erst nach Zeichnung festzulegen.

M6-Regelgewinde hat typischerweise 1 mm Steigung; die reale Spindel kann davon
abweichen. Trapezgewinde nicht allein nach Nenndurchmesser auswählen:
Steigung/Leitweg, Reibung, Spiel, Verschleiß und Selbsthemmung sind entscheidend.

Für einen direkt angetriebenen Entwurf gilt näherungsweise:

~~~text
Öffnungsänderung pro Spindelumdrehung = k * L
Schließzeit [s] = 60 * Öffnungsänderung [mm] / (k * L [mm/U] * n [U/min])
~~~

k=1 bei einer bewegten Backe, k=2 bei gleich schneller symmetrischer Bewegung.
n ist die belastete Spindeldrehzahl, nicht die Leerlaufdrehzahl im Datenblatt.
Kraft aus Drehmoment/Reibung nur abschätzen und anschließend messen.
Kleine Steigung kann sehr langsam sein und trotzdem hohe Quetschkräfte erzeugen.

### Endlagen und Neustart

Vor dem Bau Platz für einen eindeutigen Öffnungs-Referenzsensor und eine zweite
Endlagenbegrenzung vorsehen; mechanische Anschläge bleiben letzte Begrenzung.
Endschalter gehören an eine lokale I/O-/MCU-Auswertung, nicht an einen
angenommenen Homing-Pin des XL330. Der genaue Stop-/Leistungsweg wird mit
der Greiferelektronik ausgelegt.

XL330 nutzt TTL-Halbduplex und eine andere Versorgung als die ESS-Achsen.
Die dokumentierte M288-Variante arbeitet mit 3,7–6 V, empfohlen 5 V.
Mehrumdrehungszählung kann bei Neustart oder Moduswechsel ihren Bezug verlieren;
Homing Offset ersetzt keine absolute Öffnungsreferenz. Quellen:
[XL330-M288](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/),
[XL330-M077](https://emanual.robotis.com/docs/en/dxl/x/xl330-m077/).
Die tatsächliche Variante bleibt offen.

Nach unbekanntem Neustart nicht blind öffnen oder gegen einen Anschlag fahren,
wenn möglicherweise ein Objekt gehalten wird. Definierter Recovery-Zustand mit
Abstützen/Ablegen bzw. beaufsichtigter Wiederreferenzierung erforderlich.
Lokale Grenzen und Kommunikations-Watchdog vorsehen; ein Motorstromwert allein
ist wegen Spindelreibung keine direkte Griffkraftmessung.

### Zwei Widerstandssensoren

Vorgeschlagene Kette: je Sensor definierter Spannungsteiler oder andere passende
Erregerschaltung, geschützter/gefilterter ADC-Eingang und lokale MCU.
Bauteilwerte erst nach Sensortyp, unbelastetem Widerstand und belastetem Bereich.
Beide Kanäle einzeln mit eingebauter Fingerauflage kalibrieren.

Zu prüfen: Hysterese, Kriechen, Temperatur, Sättigung, Leitungsbruch/Kurzschluss,
Offset und asymmetrischer Kontakt. Zunächst relative Kontaktwerte ausgeben;
Newton erst mit nachvollziehbarer Kalibrierung. Griffbestätigung kombiniert
beide Kontakte, Öffnung, zeitliche Stabilität, Kraftgrenze und einen kleinen
beaufsichtigten Hebe-/Halteversuch. Zwei hohe ADC-Werte beweisen allein keinen
rutschfesten Griff.

Beim Spindelantrieb kann Kraft trotz Motorstop bestehen bleiben. Fehlerreaktion
muss übermäßige Kraft begrenzen, ohne ein gehaltenes Objekt unkontrolliert
fallen zu lassen. Diese Fälle gehören in die reale Greiferabnahme.

### Bauraum für einen Nahbereichssensor

Der Greifer ist noch nicht konstruiert und wird voraussichtlich bis etwa
150 mm lang. Weil die OAK den Greifraum kaum einsieht (Abschnitt 8), jetzt
Bauraum, Masse und Kabelweg für eine Kamera am Greifer oder Handgelenk mit
einplanen, auch wenn die Entscheidung noch offen ist. Alle Greiferleitungen
laufen durch J4 und J6; deren Drehbereich wird dadurch begrenzt.

## 7. Neutrale Transportpose und freie Sensorsicht

Die vorhandene Action kennt bereits stowed und ready:
[MoveArmToNamed.action](../src/robot_interfaces/action/MoveArmToNamed.action).
[pick_and_place.xml](../src/bt_orchestrator/bt_xml/pick_and_place.xml) fordert
stowed vor GoToObject/GoToPlace. Aber FindTarget kann vorher Explore auslösen;
[explore.xml](../src/bt_orchestrator/bt_xml/explore.xml) hat selbst keinen
Arm-Transportcheck. Auch Handsteuerung und Recovery müssen erfasst werden.
Ein einzelner BT-Schritt ersetzt deshalb keine zentrale Fahrfreigabe.

Repo-Montagereferenzen, vor Ort gegenprüfen:

| Sensor | Referenz | Bedeutung für den Arm |
|---|---|---|
| OAK | Konfiguration 1,34 m, gemessen 10.11.2026 1,35 m; Neigung 18,94°; [oak.launch.py](../src/robot_bringup/launch/oak.launch.py) | Arm, Finger und gehaltenes Objekt dürfen benötigte RGB-/Tiefensicht nicht verdecken |
| LiDAR | Konfiguration 0,75 m Sichtscheibenmitte (z=0,660 m relativ zu base_link), gemessen 10.11.2026 0,705 m; [stl27l.yaml](../src/amadeus_lidar_bringup/config/stl27l.yaml) | Bestehende Mastmaske umfasst 68°; Arm darf keine ungeprüfte zusätzliche Totzone erzeugen |
| VL53 | Nahbereichsabdeckung; [Konfiguration](../src/vl53_near_field/config/vl53_params.yaml) | Überhang und gehaltenes Objekt dürfen Schutzfelder nicht blind machen |

Die Höhen von LiDAR und OAK in der laufenden Konfiguration weichen von der
Messung vom 10.11.2026 ab. Das ist ein eigener, getesteter Sensor-Frame-
Schritt außerhalb der Arm-Integration. Die Mastmaske macht den Sektor
unbekannt, nicht frei. Neue Armreflexionen nicht einfach durch eine größere
Maske verbergen.

**Stand 11.11.2026:** Der Arm wurde neu konstruiert; die Zahlen zur alten
Transportpose (rund 4 cm über der LiDAR-Ebene, 136 mm Überstand) sind
überholt. Die vom Nutzer konstruierte Homing-/Parkposition ist ausgewertet
([ARM_KONTEXT](ARM_KONTEXT.md#park--und-homing-pose-aus-dem-cad-vom-11112026)):
Der Arm hängt hinter dem Mast. Sein tiefster Punkt liegt real 7 mm unter
der gemessenen LiDAR-Scheibenmitte von 705 mm, aber im bereits maskierten
Sektor. Die OAK sieht ihn bei 16:9 bis etwa 19° Neigung nicht, vorn und
hinten ragt er rund 2 cm über das Chassis. Rohscan- und Bildvergleich am
Roboter stehen aus. In Arbeitsposen gilt weiter:
J2 sitzt fest 130 mm vor J1; solange J1 den Arm waagerecht hält, ragt
allein das J2-Gehäuse rund 160 mm vor die Chassisfront. In Armhöhe erfasst
vorn kein Hindernissensor etwas: Die VL53 decken direkt vor dem Roboter nur etwa
0,4 m Höhe ab, und die OAK ist seit dem 04.11.2026 nicht zur
Hinderniserkennung vorgesehen. Überhänge wie Arbeitsplatten, Fensterbänke
oder Regalböden träfen zuerst den Arm. Der lokale Nav2-Footprint reicht bis
x = +0,31 m plus 0,02 m Polster und kennt keinen Überstand; auch der
Drehkreis wächst. Footprint und Kollisionsmonitor sind sicherheitsrelevant
und werden in einem eigenen, mit der Erkundungslinie abgestimmten Schritt
angepasst. Jede Transportpose ist mit Greifer und gegriffenem Objekt zu
prüfen. Sie braucht eine feste Hubhöhe, und die Fahrfreigabe muss sie
prüfen.

Vorgehen: kompakte, tiefe mechanische Pose suchen, dann vermessen und in
Kollisionsmodell sowie Posenkonfiguration übernehmen. Leerer Greifer und
definiertes Transportobjekt separat prüfen; gegebenenfalls eigene Pose
stowed_loaded vorschlagen. Keine Winkel raten. Auch der Weg in die Pose muss
kollisionsfrei sein, Kabel schonen und mit Last erreichbar sein.

Abnahme: Vergleich von RGB, Tiefe und ungefiltertem LiDAR-Scan vor/nach Einbau,
bekannte Hindernisse in allen weiterhin beanspruchten Sichtbereichen,
VL53-Abdeckung, Footprint und Überstand prüfen. Rohscan-Vergleich bei stehender
Basis, nicht als Änderung des laufenden Navigationsschutzes.
Danach kleine beaufsichtigte Fahrversuche mit Beschleunigen/Bremsen.

Fahrfreigabe später nur, wenn Istwinkel innerhalb gemessener Toleranzen liegen,
Gelenke stillstehen, Daten frisch sind und Last-/Greiferzustand zum freigegebenen
Transportprofil passen. Ein erfolgreich beantwortetes Mock-Ziel reicht nicht.

## 8. Kamera, Kalibrierung und Greifplanung

### OAK für Erkennung und Anfahrt, Nahbereichssensor für den Griff

**Nutzerentscheidung 08.11.2026:** Die OAK dient beim Greifen nur der
Objekterkennung und der Entfernung, damit die Basis weiß, wie weit sie zum
Zielobjekt fahren muss.

Überschlag für die heutige Ausrichtung (gemessen 1,35 m, 18,94° Neigung,
etwa 42° vertikal laut `oak_params.yaml`, passend zur gemessenen
Boden-Totzone von etwa 1,5 m): Eine waagerechte Fläche ist erst ab dieser
Entfernung vor der Chassisfront im Bild.

| Fläche | im Bild ab ca. |
|---|---|
| Arbeitsplatte, 0,90 m | 0,41 m |
| Tischplatte, 0,75 m | 0,59 m |
| Couchtisch, 0,45 m | 0,95 m |
| Boden | 1,48 m |

Laut CAD vom 11.11.2026 reicht der gestreckte Arm rund 0,66 m ohne und
0,81 m mit Greifer über die Chassisfront. Auf Tischhöhe sieht die OAK damit nur den
äußersten, gestreckten Rand des Arbeitsraums; Verdeckung durch Arm und
Objekt kommt hinzu.

Wie viel der Arm vom OAK-Bild verdeckt, hängt von seiner Stellung ab.
Gestreckt und mit dem Hub ganz oben sind es bei der heutigen Neigung rund
24 %, mit dem Hub ganz unten rund 4 %. Die Studie vom 10.11.2026 galt für
die alte Transportpose und ist überholt. In der Parkpose vom 11.11.2026
verdeckt der Arm bei 16:9 bis etwa 19° Neigung nichts; die Parkpose
schränkt die Neigungswahl also nicht ein. Tabellen stehen in
[ARM_KONTEXT](ARM_KONTEXT.md); die Entscheidung zur Neigung liegt beim
Nutzer, die Umsetzung ist ein eigener Sensor-Frame-Schritt.

**Vorgeschlagen, Entscheidung beim Nutzer:** ein Nahbereichssensor am Greifer
oder Handgelenk für die Feinlokalisierung (Eye-in-Hand). Er misst relativ zum
Greifer, sodass Mastbiegung, Kippeln der Basis und Spiel in Hubachse, J1 und
J2 im letzten Anfahrschritt kaum noch wirken. Er bringt Masse, Kabel durch J4
und J6, Kalibrierung und Zeitstempelfragen mit. Eine kleine RGB-Kamera liefert
nicht automatisch Tiefe; Nähegrenze, Tiefenausfälle an transparenten oder
glänzenden Flaschen und Licht sind bei der Auswahl zu prüfen.

Erkennung liefert zunächst eine Klasse und eine Beobachtung, keine sichere
Greifpose. Objektgröße/-achse, Greifbereich, Tisch, Hindernisse, Erreichbarkeit
und Werkzeugorientierung müssen separat bestimmt werden.

### Transformations- und Messvertrag

Für die feste OAK gilt Eye-to-Hand; eine Handkamera braucht eine
Eye-in-Hand-Kalibrierung (Kamera relativ zum Flansch, Board fest im Raum).
Für die OAK genügt bei der neuen Rollenverteilung eine Montagegenauigkeit im
Zentimeterbereich für die Anfahrt; die Millimeterkette trägt die Handkamera.
Die vorhandenen Werkzeuge sind für Eye-to-Hand gebaut; der Löser braucht für
die Handkamera einen eigenen Modus. Basis-/Armgeometrie und TCP zuerst
vermessen, dann Kameraextrinsik. Kamera-Intrinsik, Fokuszustand,
Bildauflösung und registrierte Tiefe müssen zum tatsächlichen Stream passen.
Die verbaute OAK-D-S2 hat Autofokus; die aktuelle OAK-Konfiguration legt keinen
festen Fokus fest.

Notation: A_T_B transformiert Koordinaten aus B nach A. Für ein starr am
Flansch befestigtes Board muss je Messpaar gelten:

~~~text
base_T_tool(i) * tool_T_board = base_T_camera * camera_T_board(i)
~~~

Vor echter Verwendung den bestehenden Löser mit synthetischen bekannten
Transformationen prüfen: Richtung/Inversion, Einheiten, Quaternionen und
Residuen. Unabhängige Validierungspunkte verwenden. Die feste optische Rotation
im alten Löser darf nicht ungeprüft auf die OAK-Treiberkette übertragen werden.
Jeder TF hat genau einen Eigentümer; keine zweite Kamerakette daneben publizieren.

Richtwert als Versuchsvorschlag: 15–25 gut verteilte, statische Posen mit
unterschiedlichen Rotationen und Distanzen, danach separate Prüfpunkte.
Abnahmetoleranzen vorher aus Greifergeometrie und gemessenem Fehlerbudget
ableiten. Alte Millimeterwerte im Juli-Konzept sind keine nachgewiesene Genauigkeit.
Armmodellfehler, Spiel, Durchbiegung, TCP, Kameramontage, Tiefe und Bildzeit
getrennt betrachten; ein kleiner Fit-Fehler allein reicht nicht.

Grobe Suche darf map nutzen. Für den letzten Griff braucht es eine neue,
zeitlich passende Pose in base_link, ohne unnötigen Kartenfehler.
Die vorhandene Semantik-YAML verwendet global_frame=map und ein Objektgedächtnis;
ein gespeicherter alter Treffer darf nicht als aktuelle Feinpose gelten.
Fehlender TF, veraltete Bilder, unpassende Tiefe oder verdecktes Ziel sperren
den Griff. Die bisherige 2-Hz-/2-s-Wahrnehmungskonfiguration ist für schnelle
visuelle Nachregelung nicht automatisch geeignet.

## 9. Stufenplan mit Software, Realtest und Freigabekriterium

Toleranzen und Lasten vor jedem Versuch im Messblatt festlegen. Unausgefüllte
Grenzen sind kein bestandenes Gate. Die folgenden Stufen sind Abhängigkeiten,
keine zugesagten Termine.

### M0 — Bestand und prüfbare Softwaregrundlage

**Software:** Inventarschema, getrennte Fake-Daten, Status/Rohdatenbericht,
enge Leseprofile und Negativtests. Build A ist hierfür vorhanden. Offen ist
die Erweiterung des Schemas um die lineare Hubachse als siebte Achse.

**Realität:** Motoren zu Gelenken zuordnen, NEMA23-Typ, Getriebe, Lasten,
Montage, Versorgungen, Adapter, E-Stop und Haltekonzept aufnehmen.
Gewichte von Arm, Greifer und Basis wiegen und daraus Gelenkmomente,
Kippsicherheit und Mastbelastung rechnen. Kinematik aus dem Fusion-360-Modell
übernehmen, am besten als URDF-Export mit Gelenkachsen, Ursprüngen und Netzen.
Eine gesicherte Prüfvorrichtung planen; den ungebremsten Arm nicht fallen lassen.

**Gate:** Reiner Softwarepfad läuft ohne Portöffnung. Daten und Grenzen
des nächsten ausgewählten Versuchs sind bekannt. Selbsthemmung ist noch
keine Annahme, sondern vor belasteter Bewegung zu prüfende Eigenschaft.

### M1A — Nur lesen, zuerst eine eindeutig zugeordnete ESS17-Achse

**Software:** Vorhandene CLI nach [Bedienung](../src/arm_tools/README.md).
FC03 nur 0x0000/4 und 0x0006/7; keine Konfigurations-, Reset- oder Motorbefehle.
Physische Identität, Busparameter und Auswahl explizit. Fehlende Kinematik
oder Firmware dürfen eine sichere Rohdaten-Erstinventur nicht unnötig blockieren.
Unbekannte NEMA23-Variante bleibt gesperrt.

**Realtest:** Einen Snapshot, anschließend begrenzte Wiederholung; Modell-/Firmware-
Rohwörter, Adresse, Eingänge, Fehler und Position dokumentieren.
Weitere Achsen erst nach Zuordnung. Doppelte IDs gegebenenfalls bei getrennten
Antrieben feststellen; niemals durch unkontrolliertes Bus-Umprogrammieren lösen.

**Gate:** Reproduzierbare Antworten mit gemessener Latenz, korrekter
physischer Zuordnung und nachvollziehbaren Eingängen. Verbindungsfehler beenden
die Probe ohne erfundene Rückmeldung. Bestanden bedeutet keine Bewegungsfreigabe.

### M1B — Begrenzter Einzelachs-Jog und Stopwege

**Software, noch zu bauen:** Separates Commissioning-Werkzeug mit expliziter
Achse, begrenztem Weg/Zeit/Geschwindigkeit, Bedienfreigabe und überprüftem
Stop-/Fehlerpfad. Basis sperren. Keine automatische Referenzfahrt.

**Realtest:** Gesichert und möglichst lastarm kleinste zulässige Bewegungen
in beide Richtungen. Drehsinn und unabhängigen Winkelweg messen; Befehls-/
Feedbackskalierung getrennt prüfen. Stop, Cancel, Busverlust und Neustart
nur mit vorher definierter mechanischer Absicherung erproben.
Selbsthemmung/Halten unter schrittweise erhöhter bekannter Last untersuchen.

**Gate:** Nachlauf und Stoplatenz innerhalb vorab festgelegter Grenzen,
keine unerklärte Bewegung, keine automatische Fortsetzung und keine
unbeherrschte Lageänderung. Bei unzureichendem Halten mechanisch nacharbeiten.

### M2 — Homing, Arbeitsgrenzen und reales Armmodell

**Software:** Verifizierte Eingangszuordnung, Referenzzustand je Gelenk,
begrenzte Suche, Freifahren und langsames erneutes Anfahren der Kante,
Home-Offset, Softlimits und echte JointStates. Homingreihenfolge auf
kollisionsfreie Suchräume abstimmen, auch aus zulässigen Startlagen.
Vorgeschlagenes Konzept mit Magnetsektor, Referenzkante auf der freien
Seite und Einzelachsfolge aus der Parkpose: Abschnitt 5.

**Realtest:** Wiederholte Referenzierung, Magnet schon aktiv, fehlendes/
daueraktives Signal, falsche Richtung, Drahtfehler und Restart.
Mechanische Grenzen ohne gewaltsames Anschlagfahren erfassen; Softlimits
mit Reserve für Nachlauf, Fehler und elastische Verformung festlegen.
FK/TCP an unabhängigen Punkten vergleichen. Die Hubachse mit Referenz und
beiden Endlagen gehört dazu. Weil der Not-Aus alle Achsen stromlos macht,
auch die Wiederherstellung nach Not-Aus aus ausgefahrener Stellung prüfen.

**Gate:** Dokumentierte Wiederholgenauigkeit, korrekt ungültige Referenz nach
relevantem Ausfall, plausibles Istmodell und wirksame Grenzen in beiden Richtungen.
Mehr als ein Achsbezug oder ein großer Home-Offset darf nicht stillschweigend
als „alle Gelenke null“ gespeichert werden.

### M3 — Koordinierte Bewegung und Busnachweis

**Voraussetzung:** Lokale Stopwege sowie gegenseitige Basis-/Armsperren
vor Bewegung wirksam; alle benötigten Achsen haben M2 bestanden.

**Software:** Gemeinsamer Trajektorienvertrag, aktuelles Feedback, zeitliche
Auswertung und Abbruch aller beteiligten Achsen bei Teilfehler.
RS485-Zykluszeiten, Startversatz und zulässige Reglerfrequenz messen.
Nacheinander gestartete interne Einzelachs-Trapezprofile garantieren
keine kartesisch sichere Bahn. Erst danach Controller-/ros2_control-Wahl abschließen.
Vorgeschlagen: Die Hubachse zunächst als Einstellachse behandeln, die vor
einer Armbewegung angefahren wird und währenddessen steht. Das hält die
Planung bei sechs Drehgelenken; die Redundanz der siebten Achse kann später
dazukommen.

**Realtest:** Langsame, freie Mehrachswege ohne Objekt; Istbahn, Folgefehler,
Jitter, Teilausfall und Stop vergleichen. Last und Geschwindigkeit getrennt steigern.

**Gate:** Bahnabweichung, Start-/Stopversatz und Feedbackalter im festgelegten
Budget. Falls der Bus/Antrieb das nicht erfüllt, Controllerarchitektur anpassen,
statt MoveIt auf unbewiesene Synchronität aufzusetzen.

### M4 — Plattform-Actions und geprüfte Transportpose

**Software:** Echte Arm-Actions, Planung, Kollisionsmodell, begrenzter
Ausführungszustand und benannte Posen. Einheitliche Sperren auch in Explore,
Teleop und Recovery. Kein Erfolg vor bestätigtem Istzustand.

**Realtest:** ready/stowed und Übergangswege, abgebrochene Action, unerreichbares
Ziel, Restart und veralteter Armstatus. Sensorfreie leere Transportpose nach
Abschnitt 7 prüfen. Geladene Transportpose spätestens vor M9 separat abnehmen.

**Gate:** Keine Basisfahrt bei unbekannter/ausgefahrener Armhaltung; keine
Armfahrt bei freigegebener Basisbewegung. Sichtbereiche und tatsächlicher
Roboterumriss passen zur Fahrtkonfiguration.

### M5 — Greifer als eigene Einheit

**Software:** Lokale ADC-/Endlagen-Auswertung, XL330-Anbindung, Öffnungsreferenz,
Kontakt-/Kraftstatus, Timeout/Watchdog und später Standard-GripperCommand-Action.
Öffnungsweite in Metern definieren; Servo-Strom nicht als Newton ausgeben.

**Realtest:** Zunächst Greiferprüfstand ohne Armbewegung; Öffnungsweg, Strom,
Temperatur, Blockieren, beiden Sensoren einzeln, Halten und Neustart mit/ohne
Objekt. Verschiedene Auflagen und Lasten messen.

**Gate:** Reproduzierbare Öffnung, kontrollierte Kraftbegrenzung, erkannte
Sensorausfälle und definierte Recovery ohne ungewolltes Fallenlassen.

### M6 — Greifen an bekannter Position

**Software:** Kollisionsgeprüfte Vorpose, Annäherung, Schließen,
Kontaktprüfung, kleiner Hub, Halten und kontrolliertes Ablegen.

**Realtest:** Basis steht; stabiles, unkritisches Referenzobjekt an markierter,
bekannter Position. Objekt und Last erst hier gemeinsam festlegen.
Zunächst manuell bestätigte Zielpose, keine Vision als zusätzliche Fehlerquelle.

**Gate:** Vorab definierte Wiederholungszahl, Erfolgsquote, Kraft-/Lagegrenzen
und Fehlerfälle bestanden. Fehlgriff wird erkannt, nicht als Erfolg gemeldet.

### M7 — Kamera-Arm-Kalibrierung

**Software:** Vorhandene Kalibrierwerkzeuge mit überprüfter Mathematik,
realen Frames, frischen Daten und versioniertem Ergebnis; Abschnitt 8.
Für die OAK reicht die Genauigkeit der Anfahrt; ein Nahbereichssensor am
Greifer braucht einen Eye-in-Hand-Modus im Löser.

**Realtest:** Boardmaße, Kamera-Intrinsik/Tiefe, statische Messpaare,
unabhängiger Zeigetest im Greifraum; Montage und Lastzustand festhalten.

**Gate:** Vorher begründetes Fehlerbudget an unabhängigen Punkten erfüllt.
Montage-/TCP-/Fokus-/Auflösungsänderung macht die betroffene Kalibrierung prüfpflichtig.

### M8 — Statisches Vision-Greifen

**Software:** Objektidentität, aktuelle Feinpose in base_link,
Geometrie-/Griffhypothese, Kollisionsprüfung, Ausführung und Griffverifikation.

**Realtest:** Stillstehende Basis; zuerst feste Beleuchtung und Objektlage,
dann Position/Orientierung/Material einzeln variieren. Colaflasche einschließlich
Füllzustand erst jetzt als dokumentierten Referenzfall festlegen.

**Gate:** Erfolgsquote und Fehlerbudget erreicht; kein Griff bei altem Treffer,
fehlender Tiefe, Verdeckung oder falschem Frame. Über den Nahbereichssensor
wird vor der Greiferkonstruktion entschieden (Abschnitt 8); M8 weist nach,
dass der Griff mit frischer Nahbeobachtung gelingt.

### M9 — Mobiles Gesamtsystem

**Software:** Suche, stowed, Navigation, verifizierter Stillstand, erneute
Feindetektion, Griff, abgenommene Transportpose mit Last, Fahrt und Ablage.

**Realtest:** Kurze kontrollierte Strecke, Last-/Kippstabilität,
Beschleunigen/Bremsen, Sichtfelder, Kabel und durchgehende Statusüberwachung.

**Gate:** Wechsel zwischen Fahrt und Manipulation bleibt bei Abbruch,
Kommunikationsverlust und Wiederanlauf gesperrt, bis Bedingungen wieder geprüft sind.
Greifpose wird nach jeder relevanten Basisbewegung neu bestimmt.

### M10 — Robustheit und Betriebsfreigabe

**Software/Tests:** Dauerlauf, Temperatur, Versorgung, USB-/Busabbrüche,
Prozessneustart, Sensorfehler und sichere Wiederherstellung.
Versionierte Konfiguration, Diagnose und Rückfallverfahren.

**Gate:** Dokumentierte Betriebsgrenzen für Last, Reichweite, Tempo und
Umgebung; vollständige Abnahme statt nur erfolgreichem Einzelversuch.

## 10. Nächste Arbeitspakete und Rückmeldung

| Paket | Ergebnis | Status |
|---|---|---|
| A | Inventarprüfung, Fake, reine ESS17-Rohdiagnose und Offline-/Humble-Tests | Implementiert, reale M1A-Abnahme offen |
| B | Inventarschema um die Hubachse erweitern, Kinematik aus dem CAD übernehmen, Messdaten vervollständigen, M1A-Protokoll; eigenes NEMA23-Profil erst nach Typnachweis | Nächster Schritt |
| C | Begrenzter Einzelachs-Jog, Stop-/Haltversuche | Noch zu bauen, braucht B und mechanische Versuchssicherung |
| D | Homing, Skalen, Limits, echtes Armmodell | Nach Einzelachsabnahme |
| E | Koordination, Plattform-Actions und Transportpose | Nach Timing-/Bahn-/Interlock-Nachweis |
| F | Greifer mit Bauraum für einen Nahbereichssensor, bekannte Griffe, Kalibrierung und Vision | Später, stufenweise; Sensorentscheidung vor der Greiferkonstruktion |

Seit 08.11.2026 bekannt: Gelenkzuordnung, Untersetzungen von J1–J5, Lage des
NEMA23 in J1, Hub, Reichweite, Transportpose, Nutzlast, Not-Aus-Wirkung und
eigener RS485-Adapter. Seit 10.11.2026: gemessene Höhen von LiDAR, OAK und
Hubschlitten. Seit 11.11.2026: Achslagen und Abstände des neu konstruierten
Arms sowie die Park-/Homing-Pose mit freien Richtungen je Achse aus dem CAD
(siehe [ARM_KONTEXT](ARM_KONTEXT.md)).

Jetzt benötigte Entscheidungen und Angaben: Bestätigung des Homing-Konzepts
aus Abschnitt 5 (Kantenlage je Achse, Anschlag oder Auflage für J1,
Absolutwertgeber ja oder nein), Homing-Funktion des ESS laut Handbuch,
Neigung und Montage der OAK, Antrieb und Spindel der Hubachse, Antrieb und Untersetzung
von J6, Typenschilder und Busadressen, Gewichte, Wirkung des Not-Aus auf den
Jetson, Montagezustand der Hubachse, vorhandene TLE/Magnete/Endlagen und
Busparameter, Grenzwinkel je Gelenk. Für die spätere Greiferauslegung
zusätzlich XL330-Variante, gewünschte Öffnung, Backenkinematik,
Spindel-Leitweg, Sensortyp, Referenzlast und die Entscheidung zum
Nahbereichssensor.

Jede Rückmeldung enthält Build-/Config-ID, Achse, Versuch, Soll/Ist,
Zeit-/Winkel-/Lastmessung, Abbruchgrund und lokalen Logpfad. Reale Bilder,
Raumkarten und Bags bleiben lokal. Pro neuem Build im
[Build-Protokoll](ARM_BUILDPROTOKOLL.md) höchstens 200 Wörter.

Rückfall aktuell: Diagnose beenden, isoliertes Overlay nicht sourcen.
Spätere Bewegungsbuilds brauchen zusätzlich einen vorab geprüften mechanischen
und elektrischen Stop-/Halteweg. Dieser Dokumentationsstand löst keinen
Hardwarestart und keine Änderung an laufenden Roboterparametern aus.
