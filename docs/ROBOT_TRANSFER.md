# Übertragung auf den realen Roboter

## Automatische LiDAR-Raumkartierung — real abgenommen (16.08.2026)

**Branch:** `feature/automatische-lidar-kartierung`

Der neue Ablauf besitzt zwei klar getrennte Phasen. Zuerst dreht Amadeus mit
0,12 rad/s einmal vollstaendig auf der Stelle. Der erreichte Winkel wird aus
der Encoder-Odometrie ueber den +-Pi-Uebergang akkumuliert; ein Zeitlimit,
Mindestfortschritt, Drehrichtung und der anschliessende Stillstand werden
aktiv ueberwacht. Erst danach wertet der Explorer die neue 3-cm-SLAM-Karte aus
und faehrt sichere Punkte im bekannten Freiraum vor den Grenzen zu noch
unbekannten Bereichen an. Nach jedem Ziel wird neu geplant, bis keine
ausreichend grosse sicher erreichbare Frontier mehr vorhanden oder das
zehnminuetige Gesamtlimit erreicht ist. Nach bereits erzieltem Fortschritt
gilt der erste Fall als `safe_complete`, nicht als Fahrfehler.

Der komplette Ablauf ist motorlos und real getestet. Der Dry-run erreichte
360,4 Grad, bestaetigte den Stopp, fand drei sichere Frontier-Kandidaten und
uebergab genau ein Ziel an Nav2. Der anschliessende Cancel sperrte das Fahrtor,
stornierte das Nav2-Kindziel und endete bei Nullkommando.

Im beaufsichtigten Realtest drehte Amadeus 360,2 Grad, erreichte vier sichere,
jeweils neu geplante Frontier-Ziele und beendete danach wegen der einzigen
verbliebenen, nicht sicher anfahrbaren Frontier. Ein kurz veralteter
`map->odom`-Transform wurde fail-closed gestoppt und ohne Recovery-Bewegung
begrenzt neu versucht. Die Abschlusskarte war zusammenhaengend und frei von
doppelten Waenden oder getrennten Teilkarten (195 x 221 Zellen bei 3 cm,
5,85 x 6,63 m, 16,1 m2 freie Flaeche). Diese reale Karte bleibt lokal.

Voraussetzung fuer das korrekte Verhalten ist das verifizierte LiDAR-Paar
`laser_scan_dir: true` und `tf_yaw: +1.5708`. Vorher liefen Odometrie
(-96,9 Grad) und Kartenwinkel gegeneinander; danach stimmten sie in einem
echten Teilturn mit +99,10 und +98,10 Grad ueberein. Richtung und TF nie
einzeln aendern.

Der sichere Start ist absichtlich nicht automatisch:

```bash
cd ~/roboter_ws
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_automatische_kartierung.sh \
  active_drive:=true enable_auto_explore:=true
```

Erst nach Live-Pruefung von 0 rpm, LiDAR, beiden VL53, Odometrie, SLAM-Karte,
Kollisionsmonitor und freiem Dreh-/Fahrbereich darf genau ein Explore-Auftrag
gesendet werden. Der erste echte Rundblick ist gleichzeitig ein A/B-Test fuer
die Basis: Nach 15 Sekunden muessen im Mittel mindestens 0,01 rad/s erreicht
sein. Zusaetzlich gelten acht Sekunden ohne 0,03 rad Fortschritt, falsche
Drehrichtung, veraltete Odometrie oder 210 Sekunden Gesamtzeit als sicherer
Abbruch. Die niedrige Rate beruecksichtigt die reale 2-s-Motorrampe und die
30-Prozent-SlowZone des Kollisionsmonitors.

Abbruch eines laufenden Auftrags:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
  "{data: '{\"type\":\"cancel\"}'}"
```

Danach Nullkommando und 0 rpm bestaetigen und nur den Launch-Prozess einmal
mit Strg-C beenden. Keine Prozessgruppe signalisieren. Die reale Karte erst
nach Sichtkontrolle ueber den Kartenmanager speichern; Wohnungsdaten bleiben
lokal. Rueckfall: `enable_auto_explore:=false` oder `active_drive:=false`.
Ein flaches Stromkabel kann unterhalb der Sensor-Sicht liegen; auch bei
`left=false`, `right=false`, `middle=false` ersetzt das keine Sichtkontrolle.

---

## A* und Zielfahrt mit aktivem VL53-Schutz (16.08.2026)

**Branch:** `fix/nav2-astar-vl53-zieltest`

Der reale Navfn-Planer verwendet jetzt `use_astar: true`. Die Entscheidung ist
gemessen: Dijkstra brach auf der realen 3-cm-Karte trotz zusammenhaengender
begehbarer Zellen ab; A* plante denselben Weg bei unveraendert aktiven linken
und rechten VL53-Obstacle-Layern sofort. Ein Vertragstest verriegelt A*,
`allow_unknown:false` und den erwarteten Navfn-Plugin-Typ.

Der anschliessende beaufsichtigte Realtest bestand. Beide VL53-Datenstroeme,
`collision_monitor`, Lokalisierungs-Gate, Encoder und RS485 waren bereit. Der
Kollisionsmonitor war der einzige `/cmd_vel`-Publisher zur Hardware. Die
Mission `go_to_room Arbeitszimmer` endete mit `success/angekommen`, maximal
0,100 m/s; danach Soll/Ist und beide Motoren 0 rpm, Encoder frisch, keine
Modbus-Lesefehler. Der scharfe Stack ist anschliessend beendet worden.

OAK war bewusst aus: Ihre Live-Punktwolke markierte im A/B-Test den freien
Zielbereich als praktisch unpassierbar und trennte die Costmap. Bis der
Hoehen-/Bodenfilter korrigiert und motorlos abgenommen ist, gilt als
Hinderniskette: zwei VL53 in beiden Costmaps plus zwei VL53 im
`collision_monitor`. Ein absichtlicher Hindernis-Bremstest steht noch aus.

Naechster Meilenstein ist automatische LiDAR-Kartierung. Den vorhandenen
`explore`-Knoten nicht ungeprueft real starten: Er war bislang nicht unter ROS
abgenommen; das alte Python-Erkundungsskript publiziert teilweise direkt und
ist fuer die reale Kollisionskette nicht freigegeben. Erst SLAM, Nav2,
Fahrtor, VL53 und Explorer motorlos als eine fail-closed Kette testen.

---

## Aktueller Abnahmestand: selbst lokalisieren und Raumziel erreichen (16.08.2026)

**Branch:** `feature/globale-lokalisierung`

Der aktuelle Stand erreicht das eigentliche Meilensteinziel: Amadeus startet
ohne gespeicherte oder manuell gesetzte Pose, bestimmt seine Position und
Blickrichtung stationaer aus der gespeicherten LiDAR-Karte und erreicht danach
ein karten- und revisionsgebundenes semantisches Raumziel.

Der Kaltstart verwendet nicht mehr AMCLs nativen Globaldienst. Dieser Dienst
war auf Humble bereits erreichbar, bevor AMCL zwingend eine interne Karte
hatte, und verursachte real einen Segmentation Fault (`exit code -11`). Der
Guard startet stattdessen einen kartenfesten Vollscan-Zyklus. Erst zwei
unabhaengige Treffer innerhalb 0,20 m/8 Grad duerfen `/initialpose` setzen;
AMCL muss die Pose danach bestaetigen. Karte/Basis/LiDAR, AMCL und Guard werden
in 0-/4-/7-Sekunden-Stufen gestartet, weil ein gleichzeitiger Vollstart auf
dem Jetson ausserdem einen Fast-DDS-Lifecycle-Timeout erzeugt hatte.

Reale Abnahme am 16.08.2026:

- drei motorlose Kaltstarts an derselben extern bestaetigten Pose bestanden;
- maximale Streuung 3 cm/1 Grad, zwei konsistente Scans je Start;
- Score `0,9787..0,9789`, Wandtreffer `97,36..97,50 %`, Bestenabstand
  `1,155..1,168`;
- aktiver Start erneut eindeutig: Score `0,980`, 97,22 % Wandtreffer,
  Bestenabstand 1,180; AMCL-Standardabweichung bei Freigabe
  0,140/0,138 m und 4,70 Grad;
- Nav2-Pfad vorab read-only planbar, anschliessende reale Mission
  `go_to_room Arbeitszimmer` erfolgreich;
- Karten-Endfehler 0,133 m/6,28 Grad, damit innerhalb 0,15 m/0,40 rad;
- Encoderweg 1,024 m, Fahrbefehl hoechstens 0,100 m/s;
- terminal `success/angekommen`, danach wiederholt 0 rpm und keine
  Encoder-/Modbusfehler.

Vor dem aktiven Lauf waren RS485, beide Encoder, Motorstillstand, AMCL,
Lokalisierungs-Gate, beide VL53-Datenstroeme und `collision_monitor` korrekt.
VL53 und beide Costmap-Obstacle-Layer wurden auf ausdruecklichen Wunsch nur
fuer diese beaufsichtigte Fahrt zur Laufzeit deaktiviert; OAK war aus. Im
Repository bleibt die Hinderniskette aktiv. Nach der Abnahme wurden
Missions-, Nav2-, AMCL-, LiDAR- und Motorstack beendet. Karten, Raumgeometrie
und Diagnosen liegen weiterhin nur unter `~/.local/share/amadeus/`.

Fuer den naechsten Vorfuehrstart gilt weiterhin: zuerst freie Flaeche und
Not-Aus bestaetigen, motorlos lokalisieren, `/localization/ready=true` und
0 rpm pruefen, erst danach `active_drive:=true` und genau einen frischen
Missionsmanager mit `enable_real_go_to_room:=true` starten. Mehrdeutiger Scan,
falsche Kartenbindung oder fehlendes AMCL sperren fail-closed. Rueckfall:
`enable_real_go_to_room:=false` und den Lokalisierungs-/Real-Launch nicht
starten.

---

## Zwischenstand globaler Vollscan-Gate (16.08.2026)

**Branch:** `feature/globale-lokalisierung`

AMCL hatte eine rund 1,95 m falsche Pose trotz kleiner Kovarianz als
konvergiert gemeldet. Deshalb ist der alte Vertrag ersetzt: Vor der ersten
Freigabe muss jetzt `global_scan_localizer` einen stationaeren Vollscan
eindeutig gegen die Karte abgleichen. Der Treffer ist kryptographisch an den
Kartenfingerabdruck und ueber eine neue zufaellige 128-Bit-ID an genau einen
AMCL-Global-Reset gebunden. Veraltete Statusmeldungen koennen keinen spaeteren
Start freigeben. Danach muss AMCL den Treffer innerhalb 0,30 m/12 Grad
bestaetigen; erst dann prueft der Guard wie bisher Kovarianz und stabiles
`map -> odom`.

Live-A/B am unveraenderten Standort:

- falsches AMCL: `(0,704; 0,379; -123,6 Grad)`, nur 39,6 % Scanpunkte binnen
  15 cm zur Kartenwand, Median 0,190 m;
- globaler Vollscan: bei drei Kaltstarts `x=1,245..1,305 m`, `y=-1,135 m`,
  `yaw=38..39 Grad`, Score `0,970..0,973`, Wandtreffer `97,2..98,75 %`,
  Bestenabstand `1,245..1,267`;
- finale AMCL-Pose `(1,237; -1,147; 39,4 Grad)`, unabhaengig 98,27 % binnen
  15 cm, Median 0,030 m, 90-%-Quantil 0,060 m;
- alle Laeufe motorlos mit `dry_run=true` und 0 rpm.

Normale globale Lokalisierung benoetigt damit keine Drehung und keine
Vorwaertsfahrt mehr. Start weiterhin nur ueber
`tools/kartierung/start_lidar_lokalisierung.sh`; der Matcher setzt
`/initialpose` selbst. Seine Mindestgrenzen sind Score 0,85,
Wandtrefferquote 0,85 und Bestenabstand 1,15. Ein schlechter oder
mehrdeutiger Treffer sperrt fail-closed. Diagnose:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/setup.bash
python3 tools/kartierung/globale_scan_pose.py
python3 tools/kartierung/scan_karten_abgleich.py
ros2 topic echo --full-length /localization/status_json --once
```

22 Pakettests und der Colcon-Build bestehen. Echte Karten und alle Bilder
liegen nur unter `~/.local/share/amadeus/`. Noch offen sind die persoenliche
Bestaetigung der Blickrichtung, zwei weitere deutlich getrennte motorlose
Startpositionen und danach eine beaufsichtigte reale Zielfahrt. Aus diesem
motorlosen Ergebnis folgt noch keine Fahrfreigabe. Der alte
`amcl_lokalisierungsdrehung.py` bleibt nur als Diagnosewerkzeug und ist nicht
mehr der Normalstart.

---

## Übergabestand globale Lokalisierung (15.08.2026)

**Branch:** `feature/globale-lokalisierung`

Der Roboter wurde nach dem letzten Test manuell verschoben. Das war bei
beendeten Motor-/Navigations-Stacks sicher, macht aber jede vorherige globale
Pose ungueltig. Vor der naechsten autonomen Fahrt ist deshalb eine neue
Lokalisierung erforderlich; aus diesem Dokument folgt keine Fahrfreigabe.

### Implementierter Vertrag

- `nav_localized.launch.py` startet die lokale gespeicherte Karte, den
  normalisierten STL-27L-Scan, AMCL, den `localization_guard` und den realen
  Nav2-Pfad mit genau einem dynamischen `map -> odom`-Eigentuemer.
- Der Kartenpfad ist Pflicht. Metrische und semantische Karte muessen denselben
  SHA-256-Fingerabdruck besitzen; echte Karten und Raumdaten bleiben lokal.
- Der Starthelfer prueft PGM und YAML vor ROS. Er bricht ab, wenn
  `free_thresh` die von `map_saver` als 205 geschriebenen unbekannten Zellen
  verschlucken wuerde.
- `/localization/ready` wird erstmalig nur bei hoechstens 0,20 m
  Standardabweichung in x/y, 10 Grad in yaw und hoechstens 0,08 m/5 Grad
  Bewegung von `map -> odom` im Drei-Sekunden-Fenster wahr.
- Nach Freigabe halten getrennte Hysteresen bis 0,30 m/15 Grad Kovarianz und
  0,20 m/12 Grad TF-Bewegung. Die TF-Haltegrenzen stammen aus 640 realen
  Proben mit gemessenen Maxima 0,1601 m/8,32 Grad.
- Das `cmd_vel`-Gate stoppt bei jedem Verlust der Freigabe sofort. Der
  Mission Manager verwirft eine bereits laufende Raumfahrt erst nach 0,8 s
  ununterbrochenem Verlust. Die erste Zielannahme bleibt strikt fail-closed.
- Der Lokalisierungsstatus zeigt die aktuelle TF-Fensterbewegung, die aktive
  Acquire-/Maintain-Grenze und die Gruende eines Sperruebergangs. Der
  Missionsstatus zeigt Verlustalter und Abbruchnachfrist.

### Reale Evidenz und Grenze

Die Ursache der zuvor nicht wiederholbaren Suche wurde nachtraeglich in der
Kartendatei gefunden: Das PGM enthielt 20.543 freie, 3.561 belegte und 29.320
unbekannte Zellen, doch `free_thresh: 0.25` lud alle unbekannten Zellen als
frei. Der so gespeicherte Live-Grid hatte 44,88 m² freie Flaeche statt 18,49
m² und keine unbekannte Region; AMCL suchte damit ausserhalb des realen
Zimmers. Eine lokale, geometrisch identische Version mit
`free_thresh: 0.196` erhaelt die unbekannten Zellen und ist unter dem
Fingerabdruck `528a0b020fe89624da1c55925421aecba948a13f6f27f84087725d0ad79c701f`
gespeichert. Das Overlay `Arbeitszimmer` ist lokal explizit daran gebunden.

Nach freiem Versetzen konvergierte AMCL nach einer vollstaendigen Drehung
einmal auf 0,118/0,135 m und 8,65 Grad Standardabweichung. Die folgende
`go_to_room`-Fahrt erreichte einen Punkt rund 0,03 m vor dem semantischen Ziel.
Eine 0,59-s-TF-Korrektur blieb ohne Missionsverlust; eine spaetere
2,20-s-Instabilitaet brach die Mission korrekt ab und der Motorstillstand
wurde bestaetigt.

Die reine Suchbewegung hinterliess weiterhin mehrere Winkelhypothesen. Der
entscheidende, motorlose Schritt waren standardisierte stationaere
`/request_nomotion_update`-Messungen nach dem Stop: 20 Updates reduzierten die
Streuung auf 0,095/0,118 m und 7,83 Grad und setzten `/localization/ready=true`.
Der Helfer `amcl_lokalisierungsdrehung.py` fuehrt diese Nachmessung nun selbst
aus; die 10-Grad-Grenze bleibt unveraendert. Der reale Nachweis erfolgte nach
einem Stack-Neustart am zuvor um 0,243 m veraenderten Standort mit 180,2 Grad
Drehung. Die nun zusammengefuehrte Ein-Aufruf-Variante muss beim naechsten
versetzten Start noch wiederholt werden.

Der anschliessende reale End-to-End-Test ist bestanden. Die erste Raumfahrt
wurde bei 15,69 Grad Winkelunsicherheit fail-closed abgebrochen und alle
Motorwerte gingen auf null. Nach 20 weiteren stationaeren Messungen
(0,019/0,077 m, 4,50 Grad) erreichte der erneut gesendete Auftrag das
Arbeitszimmer. Missionstatus: `success`, Phase `angekommen`; Abschluss:
0,051/0,078 m, 6,08 Grad und 0 rpm. Der TF-Endpunkt lag rund 0,148 m und
21,7 Grad vom semantischen Ziel entfernt, innerhalb der Nav2-Toleranzen
0,15 m/0,40 rad. Mehrere unabhaengige versetzte Starts fehlen noch fuer eine
statistische Wiederholbarkeitsaussage; ein kompletter versetzter Lauf ist
jedoch real belegt.

### Zustand und naechster Start

- Die Motor-/Nav2-/AMCL-/Missions-Stacks wurden nach dem bestandenen Test beendet; der
  Roboter darf aus einer alten Pose nicht autonom gestartet werden.
- VL53-Zonen und Costmap-Obstacle-Layer waren nur waehrend der beaufsichtigten
  Testlaeufe zur Laufzeit deaktiviert. Keine dauerhafte Abschaltung wurde
  eingecheckt.
- Echte Karte, semantische Daten, Bags und Diagnoserenderings bleiben lokal.
- Vor einem neuen Realtest: freie Fahrbahn und Not-Aus neu bestaetigen,
  motorlosen Preflight ausfuehren, Kartenfingerabdruck pruefen, global neu
  lokalisieren und erst bei `/localization/ready:true` ein Ziel zulassen.
- Rueckfall: `enable_real_go_to_room:=false` verwenden und den
  Lokalisierungs-/Real-Launch nicht starten.

### Abnahmeplan naechste Sitzung: mehrere Startpositionen

Ziel ist nicht ein weiterer Einzel-Erfolg, sondern eine vergleichbare
Wiederholbarkeitsmessung ohne manuell gesetzte Startpose. Drei deutlich
getrennte Startpositionen mit unterschiedlichen Anfangsrichtungen verwenden.
Vor jedem Lauf den vorherigen Launch vollstaendig beenden, den Roboter nur im
Stillstand manuell versetzen und danach denselben korrigierten
Kartenfingerabdruck pruefen.

Je Startposition wird protokolliert:

1. Startbezeichnung und ungefaehre Anfangsrichtung, aber keine Wohnungsgeometrie
   oder Kartendaten im Repository;
2. Ergebnis des motorlosen Preflights und 0-rpm-Nachweis;
3. Ergebnis des zusammengefuehrten Suchlaufs mit `--degrees 360` und
   `--forward-meters 0.25`, Anzahl stationaerer AMCL-Updates und Zeit bis
   `/localization/ready=true`;
4. x-/y-/yaw-Standardabweichung bei Freigabe und Kartenfingerabdruck;
5. terminaler Status von `go_to_room Arbeitszimmer`, eventuelle
   fail-closed-Abbrueche und Zahl notwendiger Neuauftraege;
6. TF-Abstand und Winkelfehler zum Ziel sowie Motor-/Istgeschwindigkeit nach
   dem terminalen Status.

Die Wiederholbarkeitsabnahme besteht, wenn alle drei Starts ohne manuelle
Posevorgabe lokalisieren, alle drei Raumziele innerhalb 0,15 m/0,40 rad
erreichen und nach jedem terminalen Status 0 rpm anliegt. Fuer eine
vorfuehrfertige Ein-Klick-Kette darf kein manueller Stack-Neustart oder
Neuauftrag erforderlich sein. Ein Sicherheitsabbruch ist als korrektes
Fail-closed-Verhalten zu dokumentieren, zaehlt aber nicht als bestandener
Vorführlauf.

Der Vorwaertsteil darf nur an einer Startposition mit mindestens 0,40 m
freier Bahn ausgefuehrt werden. Hardware-/Encoderfehler, falscher
Kartenfingerabdruck, fehlender LiDAR oder eine nicht schliessende Fahrtor-Kette
beenden den jeweiligen Versuch. Eine beaufsichtigte VL53-Deaktivierung bleibt
rein laufzeitbezogen und darf nicht in die persistente Konfiguration gelangen.
ROS-Bags, Karten und Raumgeometrie bleiben lokal; ins Repository kommen nur
aggregierte Messwerte und die Entscheidung bestanden/nicht bestanden.

---

## Abnahmestand reale semantische Raumfahrt (15.08.2026)

**Branch:** `feature/reale-raumfahrt`

Dieser Abschnitt ersetzt fuer neuere Stände die Aussage vom 14.08.,
`go_to_room` sei immer simuliert. Der sichere Standard ist weiterhin
Simulation; nur `enable_real_go_to_room:=true` aktiviert den getrennten
Nav2-Pfad.

### Real bestandener Vertrag

- Ein Karten- und Revisions-gebundenes semantisches Raumziel wird als
  `NavigateToPose` gesendet.
- Der verpflichtende Behavior Tree enthält keine Recovery-Manöver: kein
  automatisches Rueckwaertsfahren und kein selbststaendiges Drehen nach einem
  Fehler.
- Nav2 publiziert auf `/cmd_vel_nav_raw`. Das fail-closed
  `cmd_vel_mission_gate` gibt nur eine frische, laufende `go_to_room`-Mission
  auf `/cmd_vel_nav` frei.
- Der `velocity_smoother` arbeitet `OPEN_LOOP`; danach folgt der
  `collision_monitor`, erst dann `/cmd_vel` und `base_hardware`.
- Der Nav2-Unterzieltimeout ist 2000 ms. Die reale Unterzielannahme benoetigte
  in einem Messlauf rund 590 ms; der alte 20-ms-Wert konnte einen Fehler
  melden, bevor das Unterziel angenommen war.
- Der Fortschrittspruefer ist auf 0,10 m in 20 s gesetzt. Die alte Schwelle
  0,30 m/15 s war mit der bestaetigten 2000-ms-Hardware-Rampe unvereinbar und
  brach freie Fahrt nach rund 0,19 m ab.

Der abschliessende beaufsichtigte Bodenlauf erreichte sein Ziel nach 1,084 m
Encoderweg. Der lange Geradeausabschnitt blieb innerhalb 0,14 Grad, das finale
Einlenken innerhalb 3,28 Grad. Alle vier Stufen der Befehlskette blieben bei
maximal 0,100 m/s und 0,149 rad/s. Nach Erfolg wurden Gate, reale
Istgeschwindigkeit und beide Motoren bei null bestaetigt; es blieb kein
verwaister Nav2-Rohbefehl. Beide VL53-Datenstroeme waren frisch, Encoder und
Modbus fehlerfrei.

### Pruefung vor jeder weiteren Realfahrt

1. Roboterpose nicht aus Kartenkoordinaten raten. Der bislang abgenommene Lauf
   verwendete einen bewusst gesetzten statischen `map -> odom`-Startbezug.
2. Freie Raeder/Fahrbahn und Not-Aus bestaetigen; keine Freigabe aus diesem
   Dokument ableiten.
3. Beide VL53-Punktwolken, aktiven `collision_monitor`, frische Odometrie,
   initialisierte Encoder, RS485-Bereitschaft und 0 rpm pruefen.
4. Laufzeitparameter pruefen: `OPEN_LOOP`, 2000-ms-Nav2-Timeout und
   Fortschrittspruefer 0,10 m/20 s.
5. Während des Laufs Mission, Gate-Ausgang, Encoder-/Modbusstatus und echten
   Motorstillstand auch nach einem Terminalstatus weiter beobachten.

### Offene Grenzen und Rückfall

Die allgemeine Selbstlokalisierung nach freiem Versetzen oder Neustart ist
noch nicht abgenommen. Bis dahin ist reale Raumfahrt nur vom kontrollierten
Startbezug aus zulaessig. Der Recovery-freie Baum bricht absichtlich ab, statt
ein Hindernis autonom zu umfahren. H5 der Encoder-Odometrie und ein echter
VL53-Hindernis-Abbruch in dieser Kette bleiben offen.

Rückfall: `enable_real_go_to_room:=false` verwenden oder weglassen und den
Real-Launch nicht starten. Dann bleibt die semantische Zielaufloesung
read-only/simuliert. Karten- und Raumdaten bleiben lokal ausserhalb des
Repositories.

---

## Auftrag: manuelle semantische Räume in der Amadeus-App (14.08.2026)

**Branch:** `feature/semantic-map-editor`

**Vollständiger Vertrag:** `docs/SEMANTIC_MAP_INTEGRATION.md`

Der neue `semantic_map_manager` ist passiv: Er liest den Status des
`robot_map_manager`, speichert Raum-Polygone außerhalb des Repositories und
publiziert Metadaten. Er besitzt weder Nav2-Action noch `cmd_vel`-Publisher.
Auch `mission_manager` bereitet `go_to_room` ausschließlich als Simulation vor.
Diese Übertragung ist daher **keine Fahrfreigabe**.

### Auf Entwicklungs-Mac und Jetson geprüft

- 51 Semantik-Backend-, 38 Mission-, 15 LLM-Planer-, 51 Kartenmanager-,
  2 Bring-up- und 5 rosbridge-Mocktests: **162/162 Python-Tests bestanden**;
- 39/39 Swift-Tests und vollständiger iOS-Simulator-Build bestanden;
- Python-Kompilierung, Mypy, Flake8 `F/E9`, YAML/XML, Packaging und
  Whitespaceprüfung bestanden;
- der identische Python-Testbestand sowie der Colcon-Build der sechs Pakete
  bestanden am 14.08.2026 auf dem realen Jetson;
- physisches iPhone: signierter Build, Installation, zwei rosbridge-Sockets,
  bewusstes Kartenspeichern, Raum-Upsert auf Revision 1 und App-Neustart
  bestanden;
- Semantikmanager-Neustart stellte Revision 1 identisch wieder her;
  kontrolliertes SIGINT endet nach der gefundenen Shutdown-Korrektur sauber;
- mehr als sechs Sekunden ohne Kartenmanager sperrten den Status mit
  `ok:false`/`editable:false`; der Wiederanlauf derselben Karte stellte
  Revision 1 und den Raum `Test` ohne Datenverlust wieder her;
- ein Update mit `base_revision:0` gegen Revision 1 wurde live abgelehnt und
  ließ `current.json` unverändert;
- `go_to_room` für `Test` ergab live ausschließlich
  `simulation_only_no_navigation`; `/cmd_vel` existierte davor und danach
  nicht;
- während der gesamten Abnahme existierten weder Motor-/Nav2-Knoten noch das
  Topic `/cmd_vel`.

Die Abnahme verwendete ausschließlich die statische `testwohnung`. Eine neue
reale Wohnungskarte und jede Fahrwirkung bleiben eigene spätere Prüfungen.

### Sichere Übernahmereihenfolge

1. Arbeitskopie und Branch prüfen; unbekannte lokale Änderungen nicht
   überschreiben. Den Branch erst übernehmen, nachdem er in das Remote
   veröffentlicht wurde.
2. `AGENTS.md`, dieses Dokument und `docs/SEMANTIC_MAP_INTEGRATION.md` lesen.
3. Ohne aktive Motor-/Navigationsknoten bauen und die Offline-Verträge prüfen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select \
  robot_map_manager semantic_map_manager mission_manager llm_planner \
  semantic_perception robot_bringup
source install/setup.bash

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/semantic_map_manager \
  python3 -m unittest discover -s src/semantic_map_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/mission_manager \
  python3 -m unittest discover -s src/mission_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/llm_planner \
  python3 -m unittest discover -s src/llm_planner/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/robot_map_manager \
  python3 -m unittest discover -s src/robot_map_manager/test -v
python3 -m unittest discover -s src/robot_bringup/test -v
python3 -m unittest discover -s ios/Robotersteuerung/Tools \
  -p 'test_mock_rosbridge.py' -v
```

4. Für den ersten ROS-Vertragstest nur die beiden passiven Manager starten;
   dafür sind keine Motoren und keine Fahrt nötig:

```bash
ros2 launch robot_map_manager map_manager.launch.py
ros2 launch semantic_map_manager semantic_map_manager.launch.py
ros2 topic echo /robot_map_manager/status_json
ros2 topic echo /semantic_map/status_json
ros2 topic echo /semantic/catalog_json
```

5. Erst wenn eine echte `/map` sichtbar ist, in der App bewusst **Karte für
   Räume speichern** wählen. Die Erstbindung ist nur nach einem bestätigten
   `save_result` mit identischem SHA-256-Fingerabdruck möglich. Danach einen
   kleinen Test-Raum zeichnen, Zielpunkt strikt innerhalb setzen, speichern,
   App neu verbinden und Persistenz/Revision prüfen.
6. Prüfen, dass die Daten ausschließlich hier liegen und nicht für Git
   vorgemerkt sind:

```text
~/.local/share/amadeus/semantic_maps/<fingerprint>/current.json
~/.local/share/amadeus/semantic_maps/<fingerprint>/revisions/
```

7. Negativtests ohne Fahrt: falsche `base_revision`, Kartenwechsel und mehr als
   sechs Sekunden ausbleibender Kartenmanagerstatus müssen `editable:false`
   ergeben. `go_to_room` darf nur `simulation_only_no_navigation` melden und
   weder Nav2 noch `cmd_vel` auslösen. Ein Replay derselben `request_id` muss
   dabei Karte, Speicher, Pose, Zeit und Zähler aus dem **aktuellen** Zustand
   zeigen und darf keinen historischen Vollstatus zurückspielen.
   Zusätzlich muss der Mission-Cache nach sechs Sekunden ohne neuen
   Semantikstatus verfallen. Ein manuell angelegter Raum, ein Objekt oder ein
   Ablageziel aus einer Topic-Nachricht darf die statischen realen
   `pick_and_place`-Allowlists nicht erweitern.
8. Persistenzgrenzen sichtbar prüfen: 2.048 Revisionen/Karte, 1 GiB
   Repository und 512 MiB Freispeicherreserve sind die defensiven Defaults.
   Eine erreichte Grenze muss die neue Revision ablehnen und die letzte
   gültige Revision unverändert lesbar lassen; nichts automatisch löschen.

### Rückfallweg

- `start_semantic_map_manager:=false` lässt das Paket im Gesamt-Bring-up aus.
- `use_dynamic_catalog:=false` in Missions- und LLM-Konfiguration nutzt wieder
  ausschließlich die statischen Listen.
- Das Verzeichnis `~/.local/share/amadeus/semantic_maps/` vor einer manuellen
  Änderung sichern; der Code löscht keine Revision automatisch.
- Reale Raumfahrt bleibt gesperrt, bis VL53-/Collision-Monitor, Lokalisierung,
  Costmap-Freiraum, Planbarkeit und Abbruchpfade separat abgenommen sind.

## Abnahmestand Encoder-Odometrie (13.08.2026)

**Branch:** `fix/encoder-position-odometry` · **H0 bis H4 bestanden**

- [x] **H0** keine Knoten aktiv, `/dev/ttyUSB_BASE` frei, Worktree sauber
- [x] **H1** beide Motoren stabil per FC03 (~5 ms); `0x0011=1000`, `0x0019=0`,
      `0x0101=4000` beidseitig identisch; Position im Stillstand bitgenau
      konstant über 40 Proben
- [x] **H2** `encoder_counts_per_motor_revolution = 1000`, unabhängig gemessen:
      vorwärts 1000,8/1000,9 und rückwärts 1000,2/1000,3; Richtungsunterschied
      unter 0,07 %; vom Nutzer in beiden Richtungen mit genau 5 Radumdrehungen
      bestätigt. Gegenrechnung über die Motordrehzahl: 999,4–999,5
- [x] **H3** aufgebockt: geradeaus 0,2442 m bei 0,01° Gierwinkel, Drehung auf
      der Stelle 93,33° bei 0,0001 m Translation; null Fehler, `/odom` 16,7 Hz,
      Watchdog greift
- [x] **H4** Bodenfahrt gegen das **Lasermessgerät**: je Fahrt **+0,5 mm**
      statt +17,3 bis +20,1 mm. Zusatzfehler dreier weiterer Start-Stopp-
      Vorgänge von **+51,9 auf +3,9 mm** gesunken (−92 %). Skalenfehler
      +0,23 %, Kursabweichung +0,04° bis +0,27°
- [ ] **H5** Fehler- und Wiederanlaufpfade — offen
- [ ] `odom_*_variance` aus wiederholten Fahrten kalibrieren — offen

### Was dabei zusätzlich gefunden wurde

**Die Anfahrrampe war bis 14.08.2026 nie wirksam.** Der Antrieb weist
`accel_ms: 2500` mit
`ExceptionResponse(function_code=134, exception_code=7)` zurück; die Obergrenze
beider Rampenregister liegt bei **2000**. Ausgelesen stand in `0x001E` auf
beiden Motoren **100**. Sichtbar wurde das erst, weil dieser Branch die
Rückgabewerte der Schreibvorgänge prüft — der alte Code verschluckte den
Fehlschlag.

Die getrennte Änderung ist inzwischen real bestanden: Eingetragen sind jetzt
**2000 ms Beschleunigen**, unverändert 400 ms Bremsen und 5 rpm
Startgeschwindigkeit. Beide Antriebe bestätigten alle drei Werte. Ein
1,0-s-Bodenimpuls mit 0,12 m/s ergab 0,0439 m Encoderweg und 0,000°
Kursänderung; der Nutzer bewertete das Anfahren als „gut sanft“. Die frühere
Annahme, die Rampenzeit werde proportional zu 3000 rpm verkürzt, ist damit
widerlegt. Die anschließende manuelle LiDAR-Runde zeigte keine Verschlechterung
der Wanddicke (37,0 % vorher, 36,7 % nachher). Die offene Zimmertür macht
Fläche und Kartenausdehnung zwischen den beiden Läufen nicht vergleichbar.

**Der Nahbereichsschutz ist funktionslos.** `vl53_near_field` stirbt mit
„Kein CH341/CH34x-I2C-Bus gefunden"; der Adapter `1a86:5512` steckt, das
Kernelmodul `ch34x` fehlt. Der `collision_monitor` aktiviert sich trotzdem und
reicht ohne Sensordaten alles durch. **Vor autonomem Fahren zwingend beheben.**

**Der LiDAR-Wandvergleich taugt nicht als Kalibrierreferenz.** Bei einer Fahrt
lag er 21,5 mm neben dem Laser, bei eigener Streuung von 1,7 mm.

### Fahren mit Nahbereichsschutz

`collision_monitor` hängt als `cmd_vel_smoothed` → `cmd_vel` dazwischen. Wer
direkt auf `/cmd_vel` publiziert, umgeht ihn. Messwerkzeuge nehmen dafür
`--cmd-topic /cmd_vel_smoothed`.

---

## Auftrag: Encoderpositions-Odometrie

**Branch:** `fix/encoder-position-odometry`
**Vollständige Anleitung:** `docs/ENCODER_ODOMETRIE_FIX.md`

Dieser Branch baut auf `agent/slam-toolbox-pure-rotation-fix` auf und enthält
damit den bereits geprüften Humble-Backport und den Scan-Vereinheitlicher. Für
diesen Auftrag später **nicht** auf den Basisbranch zurückschalten.

### Branch auf dem Jetson übernehmen

```bash
cd ~/roboter_ws
git status --short --branch
git fetch origin
git switch fix/encoder-position-odometry 2>/dev/null || \
  git switch --track -c fix/encoder-position-odometry \
  origin/fix/encoder-position-odometry
git pull --ff-only
```

Bei lokalen Änderungen, einem unerwarteten Commit oder einem nicht schnellen
Vorwärtsschritt stoppen und den Zustand klären. Keine unbekannten Jetson-Dateien
überschreiben.

Der Softwarefix ist offline geprüft, aber absichtlich noch nicht fahrbereit:
`encoder_counts_per_motor_revolution: 0.0` blockiert den echten Start. Auf dem
Jetson zuerst alle Roboterknoten beenden und ausschließlich read-only messen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
python3 tools/kartierung/encoder_position_pruefen.py --confirm-stack-stopped
```

Danach die markierte Motor- oder Radumdrehung gemäß Hilfe des Werkzeugs messen,
Wortfolge, Vorzeichen, `0x0011` und `0x0101` protokollieren und erst den
bestätigten Counts-Wert eintragen. Nach H2 müssen alle drei Schutzwerte gesetzt
sein:

```yaml
encoder_counts_per_motor_revolution: <bestätigter Wert>
encoder_expected_segment: <beidseitig bestätigter Wert aus 0x0011, > 0>
encoder_expected_resolution: <beidseitig bestätigter Wert aus 0x0101, > 0>
```

`0` bei einem dieser Werte ist ausschließlich der read-only
Inbetriebnahmezustand und verriegelt den realen `encoder_position`-Modus. Ein
neuer Modbus-Client liest `0x0011`/`0x0101` erneut und startet bewusst mit einer
neuen Baseline. Anschließend gelten H0 bis H5 aus der vollständigen Anleitung.
Keine Hardwarefreigabe aus diesem Dokument ableiten.

Im laufenden Encoderpositionsmodus behält eine einzelne normale FC03-Fehlprobe
Client und Baseline. An der Transportfehlerschwelle folgen bestmöglicher
Stopp, Busfehlerstatus, Reconnect und eine neue Baseline. Stale Rückmeldung
sperrt und stoppt immer, reconnectet aber nur bei zugrunde liegendem
Transportfehler;
Python-Ausnahmen beziehungsweise unbekannte Pymodbus-API-Fehler gehen sofort in
diesen Pfad. Ein Reconnect darf daher **nicht** als kurze Lücke mit nachzuholenden
Counts bewertet werden.

Ein semantisch ungültiges Encoderpaar oder eine abweichende Treiberkonfiguration
sperrt und stoppt dagegen sofort, ohne den bestehenden Client nutzlos neu zu
verbinden. Ein unplausibles Delta wird verworfen und im Tracker kontrolliert
rebased.

`/odom` wird nur zu einem neuen gültigen Encoderpaar publiziert, mit der
Zielperiode von 0,05 s ungefähr 20 Hz. `state_json` läuft unabhängig davon im
50-Hz-Node-Takt weiter.

Der Befehlsvertrag ist ebenfalls sicherheitsrelevant: `/cmd_vel` hat Queue-Tiefe
1, NaN/Inf werden verworfen und fordern Stopp an, und der Watchdog nutzt
monotone Echtzeit. `use_sim_time: true` ist bei scharfem RS485 verboten. Ein
Motorstart erfolgt nur, wenn nach Quantisierung mindestens ein tatsächlich
schreibbarer RPM-Wert ungleich null ist.

Die vier `odom_*_variance`-Werte sind konservative Startwerte und werden erst
in H4 aus wiederholten extern referenzierten Fahrten kalibriert.

Vor Build und Tests die gepinnten seriellen Abhängigkeiten installieren.
`requirements-modbus.txt` fixiert Pymodbus 3.14.0 und Pyserial 3.5:

```bash
python3 -m pip install -r src/base_hardware/requirements-modbus.txt
```

Lokal auf dem Entwicklungs-Mac bestanden 59 Base-Hardware- und 12
Werkzeugtests. Auf dem Jetson nach dem Checkout erneut ausführen und das dortige
Ergebnis getrennt protokollieren:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/base_hardware \
  python3 -m unittest discover -s src/base_hardware/test -v
python3 -m unittest discover -s tools/kartierung \
  -p "test_encoder_position_pruefen.py" -v
```

Der CI-Workflow `.github/workflows/encoder-odometry-offline.yml` kompiliert und
prüft dieselben Python-Komponenten zusätzlich unter Ubuntu 22.04/Python 3.10.
Mac- und CI-Ergebnisse ersetzen weder den Jetson-Lauf noch die gestufte
Hardwareabnahme.

---

Der folgende Abschnitt ist nur historischer Kontext des bereits integrierten
Vorläufers. Er ist **keine zweite aktive Übergabe**. Die vollständige alte
Diagnose steht in `docs/SLAM_TOOLBOX_ROTATION_FIX.md`.

## Integrierter Vorläufer: Humble-Fix für reine Drehungen

**Historischer Basisbranch:** `agent/slam-toolbox-pure-rotation-fix`

**Basis:** `feature/stl27l-integration`, Commit `7010058`

**Ziel:** gepinntes `slam_toolbox`-Overlay unter
`~/amadeus_slam_toolbox_ws`; `/opt/ros/humble` bleibt unverändert.

### Voraussetzungen

- [ ] `AGENTS.md`, `docs/PROJECT_MEMORY.md` und
      `docs/SLAM_TOOLBOX_ROTATION_FIX.md` vollständig gelesen
- [ ] Jetson-Arbeitskopie `~/roboter_ws` sauber; unbekannte Änderungen geklärt
- [ ] kein RTAB-Map- oder alter `slam_toolbox`-Prozess aktiv
- [ ] keine Geheimnisse, echten Karten oder ROS-Bags für einen Commit vorgemerkt
- [ ] Motorstrom aus; keine Fahrfreigabe vorausgesetzt

### Einordnung im aktuellen Branch

Der aktuelle Encoderbranch enthält diesen Stand bereits. Nicht auf
`agent/slam-toolbox-pure-rotation-fix` zurückschalten. Das gepinnte Overlay darf
weiterhin nicht ungepinnt aktualisiert und `/opt/ros/humble` nicht verändert
werden.

### Source-Reihenfolge in jedem Testterminal

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/amadeus_lidar_ws/install/local_setup.bash
source ~/roboter_ws/install/local_setup.bash
```

Kontrolle:

```bash
ros2 pkg prefix slam_toolbox
```

Muss auf `~/amadeus_slam_toolbox_ws/install/slam_toolbox` zeigen.

### Abnahmestatus

Stand 12.08.2026, abgenommen auf Commit `4fe5ee3`:

- [x] Patch-Preflight (`git apply --unidiff-zero --check`) bestanden
- [x] Overlay gebaut; `colcon test` liefert allerdings **0 Tests** und ist als
      Evidenz wertlos (Testblock im Upstream auskommentiert). Ersatz: Blob-Hashes,
      Release-Build und `strings`-Gegenprobe am Binärpaket
- [x] Paketpräfix und gepinnter Humble-Commit kontrolliert
- [x] Stillstand: `dry_run=true`, `allow_rs485=false`
- [x] Stillstand: neuer Parameter `true`, keine Knotenflut, `/scan` 9,99 Hz
- [x] Synthetischer Yaw-only-Regressionstest ergänzt:
      `tools/kartierung/test_reine_drehung_synthetisch.py`, A/B 37 gegen 0
- [x] ausdrückliche Fahrfreigabe der anwesenden Person erteilt
- [x] Not-Aus in Reichweite, Fläche frei, Beobachter anwesend
- [x] 360°: mehr als null neue Posegraph-Knoten (1 → 11), Karte sichtbar ergänzt
      (freie Fläche 10,8 → 23,2 m²)
- [x] **versetzt duplizierte Wände: Ursache gefunden und behoben.** Karto
      verwarf jeden Scan mit abweichender Strahlenzahl; der STL-27L schwankt
      über 19 Werte (2145–2176). Abhilfe ist der neue Knoten
      `scan_vereinheitlichen`. A/B bei identischem Ablauf: 31 → 0 verworfene
      Scans, 10 → 41 Knoten, Nebenachse 5,39 → 3,83 m bei real 3,80 m
- [x] 40 cm Translation: weiterhin Kartenupdate (20 neue Knoten), keine
      Doppelwände, Kursabweichung +0,18°
- [ ] langsame geschlossene Runde: **noch offen.** Es ist kein Joystick
      angeschlossen (`/dev/input/js*` fehlt) und weder `collision_monitor` noch
      Nav2 laufen in `slam_lidar.launch.py`. Eine Runde durch die Wohnung darf
      deshalb nicht ferngesteuert-blind gefahren werden — der LiDAR sieht
      Schwellen, Kabel und Tischplatten grundsätzlich nicht
- [x] Testergebnis mit Datum und Commit in `docs/PROJECT_MEMORY.md` ergänzt

Diese damalige Phase-4-Freigabe gilt nicht automatisch für die neue
Encoderänderung. Im aktuellen Branch sind zuerst H0 bis H3 aus
`docs/ENCODER_ODOMETRIE_FIX.md` abzuarbeiten; jede Bewegungsphase braucht eine
neue ausdrückliche Freigabe.

### Zwei Dinge, die beim Fahren beachtet werden müssen

**Vor jedem Versuch prüfen, dass nichts mehr läuft.** `kill -INT` auf die
`ros2 launch`-PID beendet den Elternprozess, die Knoten können weiterlaufen. Am
12.08.2026 liefen dadurch zeitweise **zwei vollständige Stapel gleichzeitig** —
zwei `map->odom`-Publisher und zwei scharfe `base_hardware`-Knoten auf demselben
RS485-Bus. Die betroffene Messung war Unsinn und wurde verworfen. Nach dem
Beenden immer nachsehen, die eigene PID dabei ausnehmen:

```bash
MY=$$
ps -eo pid=,cmd= | grep -E '[l]dlidar|[a]sync_slam_toolbox|[b]ase_hardware|[s]can_vereinheitlichen' \
  | awk -v my="$MY" '$1 != my'
```

**Korrektur vom 16.08.2026:** Die folgende Messung klaerte die
Betragsabweichung, nicht das Vorzeichen. Das Werkzeug spiegelte den
LiDAR-Zuwachs vor der Regression und verdeckte damit die falsche
Treiber-Handedness. Seit dem gekoppelten Paar `laser_scan_dir: true` und
`tf_yaw: +1.5708` stimmen Odometrie (+99,10 Grad) und Kartenwinkel
(+98,10 Grad) in einem echten Teilturn ueberein.

**Die Odometrie-Betragsabweichung liegt bei -1,45 Grad je Umdrehung.** Die früher
gemeldeten −6,3° bis −6,5° waren ein Artefakt von `odometrie_drehtest.py`.
Sauber gemessen mit `tools/kartierung/odometrie_winkel_messen.py` (283
Messpunkte je Richtung, R² = 0,997): Skalenfaktor 0,99628 gegen den und 0,99564
im Uhrzeigersinn — beide Richtungen stimmen überein, also ein echter
Skalenfehler. Kein Handlungsbedarf vor Phase 4.

**Der Radradius ist neu kalibriert:** `wheel_radius_m: 0.0624`,
`wheel_separation_m: 0.3845` (vorher 0.0612 / 0.3755), aus acht Fahrten mit dem
Lasermessgerät. Verifikationsfahrt über 2,00 m innerhalb der Ablesegenauigkeit
getroffen.

**Was dabei zu beachten ist, wenn jemand die Odometrie erneut vermisst:**

1. **Kurze und lange Fahrt kombinieren.** Fester Anfahrversatz und Skalenfehler
   sind nicht trennbar, solange alle Fahrten ähnlich lang sind. 0,30 m gegen
   2,50 m funktioniert; 0,4 bis 1,0 m reicht nicht und liefert je nach
   Auswertung Radien zwischen 0,0621 und 0,0631.
2. **Lasermessgerät, nicht den LiDAR-Wandvergleich.** Der LiDAR lag bei der
   Verifikationsfahrt 24 mm daneben, bei sonst ±5 mm Streuung.
3. **Eine Winkelmessung bestimmt nur r/W**, nie die Spurweite allein. Ein
   Streckenfehler bleibt darin unsichtbar.

**Historischer Befund:** Der feste Versatz war kein Radiusfehler. Die frühere
Vermutung eines verspätet einsetzenden Ist-Drehzahlwerts ist nicht belegt;
50-Hz-Polling widerlegte eine reine Unterabtastung. Der aktuelle Encoderbranch
adressiert den Softwarepfad mit absoluten Positionsdeltas. Ob der Versatz real
verschwindet, entscheidet erst die H4-A/B-Messung.

**Keine Aktoren aktivieren, bevor alle Stillstandsprüfungen oberhalb bestanden
sind.** Ein KI-Agent darf die Fahrfreigabe nicht selbst annehmen.

### Rollback

Launch einmal sauber mit `Ctrl-C` beenden. Dann eine frische Shell verwenden
und das Overlay nicht sourcen:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 pkg prefix slam_toolbox
```

Das Präfix muss wieder `/opt/ros/humble` sein. Der Overlay-Ordner bleibt zur
Analyse erhalten; keine Datenlöschung ist erforderlich.
