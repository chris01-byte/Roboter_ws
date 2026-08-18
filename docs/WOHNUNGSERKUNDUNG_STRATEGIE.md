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

### Stufe 1: Einen Tuerdurchgang beweisen

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
Coverage-Fahrt und ein hartes Gesamtlimit von 300 s. Die Zielpose wird vor der
Translation im Log geprueft. Erst danach wird die Mission freigegeben.

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

### Stufe 4: Raumgraph nur bei nachgewiesenem Bedarf

Falls reine Frontier-Auswahl zwar Tueren passieren kann, aber in komplexeren
Wohnungen ineffizient pendelt, wird die Karte hierarchisch gegliedert:

- enge Passagen werden als Portale/Tueren erkannt;
- grosse Freiraumkomponenten werden als vorlaeufige Raumregionen gefuehrt;
- der Graph speichert `Raum -- Tuer -- Raum`;
- zuerst wird eine offene Portal-Frontier gewaehlt, dann lokal der neue Raum
  kartiert und abgedeckt;
- die App kann daraus spaeter benennbare Raeume anbieten.

Das ist eine Erweiterung der Frontier-Methode, kein Ersatz. Sie wird erst
implementiert, wenn reale Logs zeigen, dass der flache Frontier-Ansatz nach
dem Footprint-Fix noch unzureichend ist.

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
4. Beaufsichtigten einzelnen Tuerdurchgang fahren.
5. Erst danach einen neuen Wohnungslauf starten und Log/Karte auswerten.
6. Nur bei erneutem Scheitern zwischen Frontier-Zielwahl, Portalgraph oder
   `SmacPlannerLattice` anhand der Messdaten entscheiden.
