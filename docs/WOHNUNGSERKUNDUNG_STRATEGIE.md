# Strategie fuer eine vollstaendige Wohnungserkundung

Stand: 18.08.2026. Dieses Dokument beschreibt die Zielarchitektur; es ist
kein Fahrfreigabe-Ersatz. Jede reale Bewegung braucht freien Boden, den
erreichbaren Hard-Not-Aus und eine neue persoenliche Freigabe.

## Kurzentscheidung

Amadeus braucht keinen zufaelligen Fahrgenerator und vorerst auch keinen
kompletten Austausch des Explorers. Die vorhandene Frontier-Methode ist das
etablierte Verfahren fuer unbekannte Innenraeume: Der Roboter faehrt Grenzen
zwischen bekannt-frei und unbekannt an, wodurch sich die Karte schrittweise
in Flure und weitere Zimmer erweitert.

Der gescheiterte Wohnungsversuch widerlegt die Methode nicht. Drei lokale
Geometrieentscheidungen trennten die Karte am Tuerbereich kuenstlich:

1. ein globaler 0,40-m-Kreis fuer die nachgemessen nur 0,46 m breite Plattform;
2. dieselbe Kreisannahme im reaktiven Kollisionsmonitor;
3. eine quadratische 0,40-m-Erosion in der Explorer-Abdeckungsrechnung.

Der erste Patch ersetzt diese Kombination durch:

- lokalen Nav2-Footprint: x=-0,11..+0,31 m und y=+/-0,23 m, um 0,02 m
  gepaddet; die Front umfasst dabei auch die VL53-Montage;
- globales NavFn-Modell: Radius 0,28 m (halbe Breite plus 0,05 m Reserve);
- `collision_monitor`: dynamisches Polygon aus
  `/local_costmap/published_footprint`;
- Explorer: kreisfoermige 0,28-m-Erreichbarkeitsmaske.

## Aktueller Realstand

Der erste Wechsel in einen Folgeraum ist am 18.08.2026 sensorisch und physisch
bestaetigt gelungen.
Nav2 erreichte nach der Tuerdiagnose ein regulaeres Frontier-Ziel bei
`(1,05, 0,05) m`; der Explorer zaehlte die Frontier als besucht und die Basis
stand danach mit beiden Motoren bei 0 rpm. Der anwesende Beobachter bestaetigte,
dass der Roboter die Schwelle vollstaendig verlassen und den Folgeraum erreicht
hatte. Zuvor hatte ein eigener Portallauf
den entscheidenden Zwischenzustand sichtbar gemacht: Nach 0,347 m Anfahrt
wuchsen zwei kuenstlich getrennte Costmap-Komponenten zu einer einzigen
2,251-m2-Komponente zusammen. Das alte Verhalten wertete diese Verbesserung
faelschlich als `portal_geometry_changed`.

Der Explorer kann jetzt beide Faelle auseinanderhalten:

1. Ist die Tuer bereits regulaer verbunden, bleibt die Fahrt vollstaendig bei
   Nav2, Polygon-Footprint und Kollisionsmonitor.
2. Bleibt sie kuenstlich getrennt, existiert eine begrenzte Portalbruecke. Sie
   braucht einen frisch beobachteten, footprintbreiten LiDAR-Korridor und
   misst die reale Bewegung aus eingefrorener LiDAR-Geometrie; Radencoder sind
   auf Schwellen nur ein hartes Wegbudget.
3. Waechst die Karte waehrend der Portal-Anfahrt zusammen, muss der
   urspruengliche Fernseitenpunkt nun in derselben Costmap-Komponente liegen.
   Dann uebernimmt wieder Nav2 bis zu einem Auslaufpunkt hinter der Tuer.

Der einzelne Lauf beweist noch keine vollstaendige Wohnung. Der naechste
Meilenstein ist deshalb nicht ein weiterer Schwellentest, sondern ein
richtungsfreier Lauf ueber mehrere Frontiers und mindestens einen weiteren
Raumwechsel.

Die Chassiskontur wurde am 18.08.2026 relativ zur mittigen Antriebsachse mit
270 mm vorne, 110 mm hinten und 230 mm je Seite gemessen. Die schmalste Tuer
misst 680 mm. Mit lokalem Padding ist die Kontur 500 mm breit, sodass bei
mittiger Fahrt 90 mm je Seite bleiben. Die abgeschraegten Vorderecken werden
ohne zusaetzliches Tiefenmass vorerst nicht ausgespart.

## Warum wir Frontier-Exploration behalten

Brian Yamauchis Frontier-Verfahren wurde fuer reale, unbekannte und auch
enge Innenraeume entwickelt. `m-explore-ros2` ist die verbreitete ROS-2-
Umsetzung derselben Grundidee. Unser Explorer erkennt und bewertet bereits
Frontiers nach Entfernung und Informationsgewinn, ist aber zusaetzlich in
Amadeus' Missions-Gate, Encoderpruefung, VL53-Kette, App-Status und begrenzte
Abdeckungsfahrt integriert. Ein Austausch gegen `m-explore-ros2` wuerde daher
keinen grundsaetzlich neuen Weg durch eine Tuer liefern, aber die vorhandenen
Sicherheitsvertraege erneut integrieren und abnehmen muessen.

Quellen:

- [Yamauchi: A Frontier-Based Approach for Autonomous Exploration](https://robotfrontier.com/papers/cira97.pdf)
- [m-explore-ros2 (ROS 2 Humble und neuer)](https://github.com/robo-friends/m-explore-ros2)
- [Nav2: Robot Footprint einrichten](https://docs.nav2.org/setup_guides/footprint/setup_footprint.html)
- [Nav2 Tuning Guide: Footprint statt Radius](https://docs.nav2.org/tuning/index.html#robot-footprint-vs-radius)

## Warum NavFn zunaechst bleibt

NavFn plant in einem zweidimensionalen Gitter und prueft keinen orientierten
Rechteck-Footprint. Nav2 weist deshalb darauf hin, dass NavFn fuer enge Wege
eines nicht kreisfoermigen Roboters keine kinematisch gueltige Route
garantiert. Als begrenzter Zwischenschritt bekommt NavFn ein 0,28-m-
Breitenmodell; der lokale Regler und der Kollisionsmonitor pruefen die volle
gepaddingte asymmetrische Kontur. Eine global unpassende Route wird damit
lokal gestoppt, nicht blind ausgefuehrt.

Wenn ein korrekt vermessener Roboter trotz ausreichend breiter Tuer einen
NavFn-Pfad erhaelt, den der lokale Polygonpruefer wiederholt verwirft, folgt
ein eigener A/B-Schritt mit `SmacPlannerLattice`. Nav2 stellt dafuer
Differentialantriebs-Primitiven und SE2-Polygonpruefung bereit. Dieser Wechsel
ist groesser als ein Parameterpatch und wird nicht ohne reproduzierbaren
NavFn-Befund vorgenommen.

Quellen:

- [Nav2: Auswahl des Planungsalgorithmus](https://docs.nav2.org/setup_guides/algorithm/select_algorithm.html)
- [Nav2 Smac Planner](https://github.com/ros-navigation/navigation2/tree/main/nav2_smac_planner)

## Empfohlener Ablauf

### Stufe 0: Geometrie verifizieren — abgeschlossen

Die Chassisabstaende und die schmalste Tuer sind gemessen. Der bekannte
VL53-Ueberstand ist in der sicheren Rechteckhuelle enthalten. Der dynamische
Footprint fuer ausgefahrenen Arm ist ein spaeterer Schritt; Erkundung ist bis
dahin nur in definierter Transportpose erlaubt.

### Stufe 1: Einen Tuerdurchgang beweisen — sensorisch abgeschlossen

Kein voller Wohnungslauf. Der Roboter startet etwa ein bis zwei Meter im
bekannten Zimmer, eine vollstaendig geoeffnete Tuer ist die einzige attraktive
groessere Frontier. Abnahmebedingungen:

- der Explorer waehlt ein Ziel hinter oder in Richtung der Tuer;
- die globale Route liegt mittig im Durchgang;
- der lokale Polygon-Footprint bleibt kollisionsfrei;
- beide VL53 und `collision_monitor` bleiben aktiv;
- der Roboter ueberquert die Tuerlinie und stoppt danach kontrolliert;
- Encoder-Odometrie und SLAM-Karte bleiben konsistent.

Dieser Test trennt Footprint/Planer von der spaeteren Wohnungsstrategie.
Er verwendet `door_test_params.yaml`: Rundblick und Vorausrichtung bleiben
aktiv, aber es gibt hoechstens ein Frontier-Ziel, einen Fehlversuch, keine
Coverage-Fahrt und ein hartes Gesamtlimit von 300 s. Nach dem ersten Realtest
ist ausserdem ein harter +/-20-Grad-Vorwaertskorridor aktiv: Das damalige,
30,6 Grad seitliche Ziel kann nicht erneut ausgewaehlt werden. Gibt es keine
sichere Frontier in Fahrtrichtung, endet der Test ohne Translation. Dieser
Korridor gilt bewusst nur fuer die Einzelabnahme; die spaetere
Wohnungserkundung muss Frontiers in allen Richtungen erreichen koennen.

Die Abnahme erreichte anschliessend ein normales Nav2-Frontier-Ziel 1,05 m
hinter der neuen Startpose. Der Explorer meldete eine besuchte Frontier, die
Basis stoppte fehlerfrei bei 0 rpm. Ein spaeterer Gesamtfehler im selben Lauf
kam ausschliesslich vom temporaeren 20-Grad-Kegel, der drei seitliche
Folgefrontiers verwarf; er ist fuer die Wohnungserkundung wieder deaktiviert.

### Stufe 2: Frontier-basierte Wohnungskartierung

Nach bestandenem Tuerbeweis laeuft die vorhandene Dreiphasenmission:

1. kontrollierter Rundblick;
2. Frontier-Ziele, solange neue unbekannte Bereiche erreichbar sind;
3. Abdeckungsziele in den bereits erschlossenen Bereichen.

Eine neu aufgedeckte Frontier unterbricht Phase 3 und hat wieder Vorrang.
Damit kann der Roboter aus einem Zimmer in Flur und Folgeraeume wachsen, ohne
vorher die Wohnungsstruktur zu kennen.

### Stufe 3: Abschlussvertrag fuer mehrere Raeume

Der heutige Wert „85 % der aktuellen sicheren Komponente“ darf allein keinen
Wohnungserfolg mehr bedeuten. Der zukuenftige Abschluss braucht gemeinsam:

- mehrere aufeinanderfolgende Neuplanungen ohne erreichbare Frontier;
- keine grosse offene, aber wegen Zielwahl/Blacklist ungelöste Frontier;
- stabile Kartenflaeche ueber ein Zeitfenster;
- mindestens 85 % Fahrspurabdeckung global und je erschlossener Region;
- keine gescheiterte Tuer-/Portalpassage;
- eine plausible, zusammenhaengende Karte in der Sichtpruefung.

Wenn eine offene Frontier existiert, aber kein sicherer Pfad dorthin gefunden
wird, lautet der Zustand `partial` beziehungsweise `failed`, niemals
`map_ready_to_save=true`.

### Stufe 4: Leichte Portalbruecke aktiv; voller Raumgraph nur bei Bedarf

Falls reine Frontier-Auswahl zwar Tueren passieren kann, aber in komplexeren
Wohnungen ineffizient pendelt, wird die Karte hierarchisch gegliedert:

- enge Passagen werden als Portale/Tueren erkannt;
- grosse Freiraumkomponenten werden als vorlaeufige Raumregionen gefuehrt;
- der Graph speichert `Raum -- Tuer -- Raum`;
- zuerst wird eine offene Portal-Frontier gewaehlt, dann lokal der neue Raum
  kartiert und abgedeckt;
- die App kann daraus spaeter benennbare Raeume anbieten.

Die reale Tuerdiagnose hat den kleinsten notwendigen Teil inzwischen
gerechtfertigt: Der Explorer erkennt grosse, getrennte Costmap-Komponenten
und kann genau eine begrenzte, unabhaengig mit LiDAR gepruefte Bruecke planen.
Das ist eine Erweiterung der Frontier-Methode, kein Ersatz. Ein persistenter
Raumgraph mit IDs, Rueckkehrlogik und App-Raumbenennung bleibt dagegen bewusst
offen, bis ein richtungsfreier Mehrraumlauf Pendeln oder falsche
Portalwiederholungen tatsaechlich nachweist.

## Was nicht empfohlen wird

- **Zufallsfahrt oder Wandfolgen allein:** keine Vollstaendigkeitsmetrik und
  unnoetig lange Wege.
- **Nur den 85-%-Wert erhoehen:** vergroessert nicht die als erreichbar
  betrachtete Flaeche und oeffnet keine Tuer.
- **`m-explore-ros2` sofort ersetzen:** gleiche Grundstrategie, aber Verlust
  der projektspezifischen Sicherheits- und App-Integration.
- **Coverage-Planer fuer die Entdeckung:** systematische Flaechenbahnen sind
  sinnvoll, nachdem die Region bekannt ist; sie ersetzen keine Exploration
  unbekannter Nachbarraeume.
- **Global sofort State Lattice aktivieren:** erst nach einem gemessenen
  NavFn-/Polygon-Widerspruch, dann separat motorlos und real abnehmen.

## Aufloesung

Die 3-cm-SLAM-Aufloesung bleibt richtig. Sie bildet Tuerbreiten und den
0,50-m-gepaddeten Plattformquerschnitt deutlich feiner ab als die 5-cm-
Costmaps und war in den bisherigen Karten stabil. Der aktuelle Fehler war
die Geometriemodellierung, nicht die Rasteraufloesung.

## Naechste reale Entscheidungspunkte

1. Vermessener Footprint im Nav2-/Kollisionsstack: abgeschlossen.
2. Synthetische 0,68-m-Tuer in der Explorer-Erreichbarkeit: abgeschlossen.
3. Motorloser NavFn-Plan durch eine 0,69-m-Synthetiktuer: abgeschlossen.
4. Beaufsichtigter Wechsel zum 1,05-m-Ziel im Folgeraum: sensorisch und durch
   aeussere Sichtpruefung abgeschlossen.
5. Richtungsfreien Mehrraumlauf mit normalem Wohnungsprofil starten und
   mehrere Frontiers, weitere Tueren, Log und lokale Karte auswerten.
6. Abschluss erst freigeben, wenn keine ungeloesten Frontiers/Portale bleiben
   und die globale sowie regionale Abdeckung stabil ist.
7. Nur bei erneutem Scheitern zwischen erweitertem Portalgraph oder
   `SmacPlannerLattice` anhand der Messdaten entscheiden.
