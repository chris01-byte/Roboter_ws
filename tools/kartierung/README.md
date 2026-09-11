# Werkzeuge für Kartierung und Lokalisierung

Am 27.07.2026 auf dem echten Roboter benutzt und dort verifiziert. Die Skripte
setzen voraus, dass `~/roboter_ws/install/setup.bash` existiert.

## Encoderposition strikt read-only prüfen

`encoder_position_pruefen.py` liest ausschließlich Holding-Register mit FC03.
Es sendet keine FC06/FC16-Schreibzugriffe, keine Motorbefehle und keine
ROS-Kommandos. Die Probe ist H1/H2-Diagnose und **keine Fahrfreigabe**.

Vor dem Aufruf den vollständigen Amadeus-Stack über dessen regulären
Stoppmechanismus beenden. Danach prüfen, dass keine Roboterknoten mehr laufen
und `/dev/ttyUSB_BASE` exklusiv frei ist; niemals parallel zu
`base_hardware` oder einem anderen seriellen Client öffnen:

```bash
cd ~/roboter_ws
python3 -m pip install -r src/base_hardware/requirements-modbus.txt
python3 tools/kartierung/roboterknoten.py --still
python3 tools/kartierung/encoder_position_pruefen.py \
  --confirm-stack-stopped --samples 20
```

`--confirm-stack-stopped` beendet selbst keinen Prozess. Das Werkzeug bricht
zusätzlich ab, wenn es bereits einen Besitzer des seriellen Ports findet.

Für eine markierte Radumdrehung eines einzelnen Motors, nur unter den
mechanischen und elektrischen Sicherheitsbedingungen aus H2:

```bash
python3 tools/kartierung/encoder_position_pruefen.py \
  --confirm-stack-stopped --measure-wheel 1 --turns 1 --gear-ratio 10
```

Die Messung in beiden Richtungen und für Motor 1 und 2 wiederholen. Der genaue
Akzeptanzvertrag, insbesondere Counts, `0x0011` und `0x0101`, steht in
`docs/ENCODER_ODOMETRIE_FIX.md`.

## Automatische LiDAR-Raumkartierung

Die automatische Kartierung arbeitet bewusst in drei Phasen:

1. kontrollierter 360-Grad-Rundblick mit 0,12 rad/s; der tatsaechliche Winkel,
   Fortschritt, Drehrichtung und anschliessende Stillstand kommen aus der
   Encoder-Odometrie;
2. Frontier-Exploration auf der laufend aktualisierten SLAM-Karte. Ziele
   liegen im bereits bekannten Freiraum vor den Grenzen zu unbekanntem Raum,
   besitzen Sicherheitsabstand und werden nach jedem Fahrabschnitt neu
   bewertet. Vor einem groesseren Richtungswechsel richtet sich der Roboter
   mit einem konstanten, encodergeprueften Drehkommando aus und bestaetigt den
   Stillstand; erst danach erhaelt Nav2 das eigentliche Fahrziel.
3. adaptive Flaechenabdeckung. Sobald keine sichere Frontier mehr uebrig ist,
   wird die tatsaechlich gemessene Fahrspur mit der zusammenhaengenden, um
   0,40 m erodierten Freiflaeche verglichen. Der geodaetisch am weitesten
   entfernte noch nicht abgedeckte sichere Punkt wird zum Folgeziel. Dadurch
   erzeugen groessere oder verwinkelte Raeume automatisch mehr Ziele.

Die Kartenaufloesung bleibt bei 3 cm. Das ist fuer den rund 18-m2-Raum ein
guter Kompromiss aus Wanddetail, stabiler Frontier-Erkennung und Rechenlast
auf dem Jetson. Eine feinere Zellgroesse behebt weder Odometriefehler noch
dynamische Hindernisse und wuerde die Navigation unnoetig verteuern.

Der verifizierte Sensorframe-Vertrag lautet `laser_scan_dir: true` und
`tf_yaw: +1.5708`. Der Treiber publiziert damit ROS-konform gegen den
Uhrzeigersinn; der Montage-TF bildet den physischen Vorwaertsstrahl korrekt
auf `base_link +X` ab. Beide Werte sind gekoppelt und duerfen nie einzeln
geaendert werden.

Motorloser Gesamttest:

```bash
cd ~/roboter_ws
bash tools/kartierung/start_automatische_kartierung.sh \
  active_drive:=false enable_auto_explore:=true
```

Fuer iOS-/Web-App, Live-Karte, Raumeditor und Erkundung stattdessen den
einzigen gemeinsamen App-Launch verwenden:

```bash
cd ~/roboter_ws
bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=false enable_auto_explore:=true
```

Dieser Starter nimmt Kartenmanager, Semantikmanager und rosbridge mit. Er
bricht ab, falls einer davon oder ein alter Missions-/Explorer-Stack bereits
laeuft. Den alten Einzelstart zuerst in seinem Terminal sauber mit Strg-C
beenden; nie `robot.launch.py`, `smartphone_gui.launch.py` oder
`nav_mapping.launch.py` parallel starten.

Scharfer Start nur nach persoenlicher Freigabe, freiem Raum und erreichbarem
Hard-Not-Aus:

```bash
cd ~/roboter_ws
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=true enable_auto_explore:=true
```

Fuer die erste HWT601-Kartenabnahme nicht das volle Explorerprofil verwenden,
sondern den begrenzten Rundblick. Er erzwingt acht langsame 45-Grad-Segmente
mit Pause, verbietet jede Translation und beendet die Mission danach:

```bash
cd ~/roboter_ws
AMADEUS_HWT601_STILLSTAND=JA \
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_hwt601_rundblick.sh
```

Auch dieser Start sendet noch keinen Auftrag. Den Roboter waehrend der
HWT-Biaskalibrierung mindestens 30 Sekunden stillhalten, alle unten genannten
Live-Signale pruefen und erst dann genau den einen Explore-Auftrag senden.
Jede Wiederholung benoetigt eine neue persoenliche Fahrfreigabe.

Nach bestandenem Rundblick prueft die erste HWT-Translation genau 0,50 m
geradeaus. Der lokale LiDAR-Abgleich bestaetigt den realen Chassisweg; die
Encoder begrenzen nur den maximalen Radweg auf 0,90 m. Das Profil deaktiviert
Rundblick, Frontiers, Portale und Abdeckung und beendet die Mission unmittelbar
nach bestaetigtem Stillstand:

```bash
cd ~/roboter_ws
AMADEUS_HWT601_STILLSTAND=JA \
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_hwt601_translation.sh
```

Vor dem Explore-Kommando muss der 0,50 m breite Korridor vor dem Roboter fuer
die Fahrt, die 0,31-m-Front und Bremsreserve frei sein. Der Start allein loest
keine Bewegung aus; der Auftrag bleibt separat und jede Wiederholung braucht
eine neue persoenliche Freigabe.

Fuer die anschliessende HWT-Erkundung genau eines physisch geschlossenen
Raums gilt das eigene Profil `hwt601_room_only_params.yaml`. Es deaktiviert
Tuer-/Portalbewegung und Rueckkehr, begrenzt auf acht Frontiers und sechs
Abdeckungsziele und endet spaetestens nach 15 Minuten. Der erste Echtlauf
zeigte, dass 10 Minuten nicht genuegen: Der langsame Rundblick benoetigte
146 s; nach drei erreichten Frontiers und 3,82 m EKF-Weg wurde das vierte Ziel
bei 50,3 % Abdeckung nur durch das Zeitlimit abgebrochen. Alle Ausgaenge
muessen geschlossen sein:

```bash
cd ~/roboter_ws
AMADEUS_RAUM_GESCHLOSSEN=JA \
AMADEUS_HWT601_STILLSTAND=JA \
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_hwt601_raumerkundung.sh
```

Der Start sendet weiterhin keinen Auftrag. Eine neue Ausfuehrung braucht eine
neue persoenliche Fahrfreigabe; das erhoehte Zeitbudget ist keine automatische
Fahrfreigabe.

Nach dem bestandenen HWT-Rundblick, der 0,50-m-Translation und einer
kohaerenten Raumerkundung darf genau eine Tuer mit dem getrennten Profil
`hwt601_door_only_params.yaml` abgenommen werden. Der Roboter fuehrt zuerst
den segmentierten 360-Grad-HWT-Rundblick aus, akzeptiert danach nur ein
Kartenziel innerhalb von +/-20 Grad zur wiederhergestellten Startfront,
richtet sich selbst darauf aus und navigiert mit Nav2 durch die Tuer. Trennt
die Inflation beide Raeume, darf genau eine LiDAR-gepruefte Portalbruecke
uebernehmen. Verschiebt neue Kartenevidenz dabei den sicheren Vorpunkt, darf
Nav2 hoechstens dreimal kontrolliert nachruecken; die direkte LiDAR-Bruecke
bleibt auf maximal 1,00 m begrenzt. Ein erreichter Vorpunkt allein ist kein
Erfolg: Erst der bestaetigte Portalwechsel beendet den Test und sperrt jede
weitere Fahrt. Coverage bleibt aus.

Vor dem Start die Tuer vollstaendig oeffnen und gegen Zuschlagen sichern. Den
Roboter so vor den Durchgang stellen, dass die offene Tuer innerhalb des
vorderen +/-20-Grad-Suchsektors liegt; manuelles Zentrieren oder paralleles
Ausrichten ist nicht Teil der Voraussetzung. Der Durchgang muss mindestens
0,68 m breit sein; Arm/Greifer bleiben in Transportpose. Hinter der Tuer
muessen Plattform, Zielweg und Bremsreserve frei sein.

Erst nach dieser physischen Pruefung und einer neuen persoenlichen
Fahrfreigabe starten:

```bash
cd ~/roboter_ws
AMADEUS_TUER_OFFEN=JA \
AMADEUS_TUER_VORNE=JA \
AMADEUS_TUERZIEL_FREI=JA \
AMADEUS_HWT601_STILLSTAND=JA \
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_hwt601_tuerdurchfahrt.sh
```

Auch dieser Start bewegt noch nichts. Nach mindestens 30 s absolutem
Stillstand werden HWT, LiDAR, Odometrie, beide VL53, Collision-Monitor und
Basis im Live-Preflight geprueft; erst danach wird genau ein Explore-Auftrag
gesendet. Der Auftrag darf zunaechst den notwendigen Rundblick und die
selbsttaetige Vorausrichtung ausfuehren. Jede Wiederholung benoetigt eine neue
Freigabe und erneute Aufstellungspruefung.

Erster Echtlauf am 11.09.2026: Rundblick 360,7 Grad, Tuerziel 4,24 m2 und
autonome Nav2-Anfahrt erkannt. Die Costmap verschob danach den Vorpunkt um
rund 0,30 m; die dadurch 1,21 m lange direkte Restfahrt wurde am unveraenderten
1,00-m-Limit korrekt verweigert. Die anschliessende Softwarekorrektur plant in
diesem Fall einen weiteren Nav2-Vorpunkt.

Der zweite Echtlauf stoppte vor jeder Translation bei 307,3 Grad Rundblick:
Der gemeinsame Dual-VL53-Prozess lieferte einmalig 10,924 s lang weder Status
noch Punktwolken. Das Fahrtor sperrte nach 0,8 s korrekt. HWT/EKF (307,4 Grad)
und Encoder (302,9 Grad) blieben kohaerent; HWT, LiDAR, Encoder und Not-Aus
zeigten keinen Fehler. In fuenf frueheren Bags ueber rund 32 Minuten betrug die
groesste VL53-Luecke 0,854 s. Deshalb wartet nur dieser rotationsreine
Rundblick jetzt hoechstens 15 s auf Wiederfreigabe. Fahrtor und die strengere
8-s-Abbruchgrenze waehrend Vorwaertsfahrt bleiben unveraendert. Eine reale
Wiederholung war ohne erneuten Aussetzer erfolgreich.

Im dritten Echtlauf gelangen 360,8 Grad Rundblick und eine autonome
0,34-m-Nav2-Anfahrt zum ersten Vorpunkt. Der getrennte Zielbereich wuchs dabei
von 1,758 auf 3,859 m2. Sein Flaechenschwerpunkt wanderte rund 0,85 m, obwohl
die lokale Tuergeometrie weniger als 0,15 m versetzt blieb. Die fruehere
Zuordnung ueber den Raumschwerpunkt meldete deshalb falsch
`portal_geometry_changed`; der Roboter stoppte sicher vor jeder direkten
Portalbewegung. Die Korrektur verfolgt nun Nah-/Fernpunkt, Portalmitte und
Durchfahrtsrichtung. Der aufgezeichnete Bag besteht damit alle fuenf
Costmap-Zeitpunkte; eine umgekehrte nahe Oeffnung bleibt fail-closed. Der
naechste Echtlauf verwendete diese Zuordnung erfolgreich.

Im vierten Echtlauf verband die Costmap die Tuer waehrend der Anfahrt und Nav2
meldete das Ziel `(1,53, -0,20) m` als erreicht. Die unabhaengige
Explorer-Pruefung stoppte trotzdem fail-closed: `map->base_link` lag erst bei
rund `(1,151, -0,146) m`, 0,383 m vor dem angeforderten Ziel und 0,138 m vor
dem festen Fernseitenpunkt. NavFns 0,30-m-Planertoleranz und die 0,15-m-
Zieltoleranz des Controllers koennen sich addieren. Darum bestaetigt allein
`NavigateToPose: SUCCEEDED` noch keinen Portalwechsel. Fehlt der gemessene
Pflichtauslauf, plant der Explorer jetzt hoechstens ein zweites, weiter
vorgeschobenes Nav2-Auslaufziel. Es muss frisch sicher und verbunden sein und
hoechstens 1,00 m von der aktuellen Pose entfernt liegen. Auf der echten
End-Costmap waeren das 0,725 m. Bleibt auch diese Etappe zu kurz, endet der
Auftrag weiterhin fail-closed. Der Nutzer bestaetigte nach diesem Lauf, dass
das gesamte Chassis in der Kueche stand; die physische Schwellenueberquerung
ist damit bestanden. Die strengere softwareseitige Abnahme und die reale
Wiederholung der neuen zweiten Auslaufetappe stehen noch aus.

Fuer einen anschliessenden beaufsichtigten Test aus genau einem Startraum in
den angrenzenden offenen Flur steht das getrennte Overlay
`hwt601_office_hall_params.yaml` bereit. Es erlaubt nach dem Rundblick bis zu
zehn normale Frontier-Ziele und hoechstens einen gesonderten Portalwechsel,
erkundet nach einer Tuer weiter, kehrt aber nicht automatisch zurueck. Das
Overlay ist keine allgemeine Wohnungsfreigabe:

```bash
cd ~/roboter_ws
AMADEUS_HWT601_STILLSTAND=JA AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_app_erkundung_hwt601.sh \
  active_drive:=true enable_auto_explore:=true \
  explore_params_overlay:="$(pwd)/src/explore/config/hwt601_office_hall_params.yaml"
```

Der erste Echtlauf am 11.09.2026 ist fehlgeschlagen: Der Roboter blieb nach
eindeutiger Beobachtung des anwesenden Nutzers im Arbeitszimmer. Durch die
offene Tuer sichtbare, zusammenhaengende LiDAR-Pixel sind kein Nachweis einer
Schwellenueberquerung. Der Bag zeigt nach 620 s einen sicheren Portalplan zum
1,569-m2-Zielbereich, gleichzeitig aber noch fuenf normale Zimmer-Frontiers.
Die Standardstrategie stellte den Portalplan deshalb zurueck. Nur dieses
begrenzte Overlay aktiviert nun `portal_priority_when_available: true`, damit
ein gemessener Portalplan Vorrang vor weiteren Zimmerzielen erhaelt. Der
Standard bleibt unveraendert. Diese erste Korrektur bestand den motorlosen
Test, loeste im zweiten Echtlauf aber noch nicht die unten beschriebene
verbundene Tuergeometrie. Der reale Erfolg verlangt immer die Beobachtung der
anwesenden Person.

Auch der zweite Echtlauf blieb im Arbeitszimmer. Diesmal gab es waehrend des
gesamten Auftrags keinen getrennten Portalplan: Die echte Costmap sah Tuer und
Flur bereits als eine zusammenhaengende Komponente. Das Overlay aktiviert
deshalb zusaetzlich `connected_portal_analysis_clearance_m: 0.40`. Nur die
Erkennung vergroessert ihren Abstand zellenweise bis zu diesem Maximum; beide
Endpunkte muessen in der unveraenderten Nav2-Costmap verbunden und unter
Zielkosten 90 sein. Der Uebergang wird dann regulaer von Nav2 gefahren. Mit
`required_portal_crossings: 1` bleibt jeder Abschluss ohne gemessenen Auslauf
ein Fehler. Build, 79 Explorer-Tests und motorloser Gesamt-Preflight sind
bestanden; die aktuelle Livekarte lieferte passiv einen passenden verbundenen
Plan mit 0,614 m2 Zielbereich und sicheren Endpunktkosten 82/70. Die reale
Wiederholung fuhr den Uebergang anschliessend mit Nav2 und bestaetigte
`portal_crossings=1/1`. Eine durch neue Kartengeometrie verschobene erneute
Erkennung desselben Tuerhalses loeste danach faelschlich das bereits erreichte
1/1-Limit aus. Fuer explizit begrenzte Profile werden weitere Portalangebote
nach erfuelltem Vertrag nun ignoriert, damit Frontier-/Coverage-Kartierung im
Zielbereich weiterlaeuft; allgemeine Profile bleiben am Limit fail-closed.
80 Explorer-Tests und Build sind gruen. Der anwesende Nutzer bestaetigte, dass
der Roboter vollstaendig in den Flur fuhr und sich dort noch etwas umsah. Der
Zwei-Bereich-Test ist damit bestanden; die nachgelagerte Abschlusskorrektur ist
real noch nicht wiederholt.

Der Launch startet absichtlich noch keine Mission. Erst wenn Basisstillstand,
LiDAR, beide VL53, Odometrie, SLAM-Karte, Kollisionsmonitor und Nav2 bereit
sind, genau einen Auftrag senden:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
  "{data: '{\"type\":\"explore\"}'}"
```

Ein laufender Auftrag wird fail-closed abgebrochen mit:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
  "{data: '{\"type\":\"cancel\"}'}"
```

Der Rundblick beendet sich ausserdem selbst, wenn nach 15 Sekunden im Mittel
weniger als 0,01 rad/s erreicht werden, die Odometrie ausfaellt, der Roboter in
die falsche Richtung dreht, 15 Sekunden keinen Fortschritt macht oder das
280-Sekunden-Limit erreicht. Das Zeitbudget beruecksichtigt, dass der aktive
Kollisionsmonitor die Drehung in seiner SlowZone auf 30 % reduziert. Die
gesamte Einzelabnahme endet spaetestens nach acht Minuten; ein Nav2-Ziel
nach 120 Sekunden. Erfolgreich bediente Frontier-Umfelder werden im Radius
von 0,60 m nicht erneut angefahren; 20 Frontier-Ziele sind die zusaetzliche
fail-closed Obergrenze. Recovery-Drehungen und -Rueckwaertsfahrten von Nav2
sind nicht mit der Hardware verbunden.

Ein beendeter Frontier-Abschnitt ist noch keine vollstaendige Raumabdeckung.
Standardmaessig meldet der Explorer erst Erfolg, wenn mindestens 85 % der
sicher befahrbaren Flaeche innerhalb von 0,65 m zur real gemessenen Fahrspur
liegen. Hoechstens 14 Abdeckungsziele begrenzen die dritte Phase. Zeitlimit
oder fehlendes sicheres Ziel unterhalb 85 % bleiben Fehler. Der 1-Hz-Status
auf `/explore/status_json` liefert `coverage_percent` und setzt
`map_ready_to_save:true` nur nach bestaetigtem Abschluss.

Seit dem Wohnungsbefund vom 18.08.2026 verwendet die lokale Costmap die
gemessene asymmetrische Rechteckhuelle `x=-0,11..+0,31 m`, `y=+/-0,23 m` plus
0,02 m Padding. Die Front schliesst die VL53-Montage ein. NavFn plant global
mit 0,28 m Radius; der lokale Regler und `collision_monitor` pruefen die volle
Kontur. Der Explorer erodiert Ziel- und Abdeckungsflaeche kreisfoermig um
0,28 m statt quadratisch um 0,40 m. Die schmalste gemessene Tuer ist 0,68 m
breit; fuer den lokal gepaddeten Footprint bleiben 0,09 m je Seite.
Ein motorloser NavFn-Test plante auf einer 3-cm-Synthetikkarte geradlinig
durch eine 0,69-m-Oeffnung (`ComputePathToPose: SUCCEEDED`).
Das alte `door_test_params.yaml` dokumentiert nur die historische 0,20-m-
Restwegetappe aus einer bereits begonnenen Tuerfahrt und darf nicht fuer einen
frischen HWT-Tuerstart verwendet werden. Dafuer ist ausschliesslich der oben
beschriebene `start_hwt601_tuerdurchfahrt.sh` vorgesehen. Vor dem
Explore-Kommando beide VL53-Punktwolken und die aktiven Parameter auslesen.
Die Mehrraumstrategie und Abnahmereihenfolge stehen in
`docs/WOHNUNGSERKUNDUNG_STRATEGIE.md`.

Die Karte zwischendurch rendern und ansehen. Erst eine plausible Karte ueber
den Kartenmanager speichern. Danach Auftrag abbrechen, Nullkommando und 0 rpm
pruefen und ausschliesslich den Launch-Prozess einmal mit Strg-C beenden.
Wohnungsgeometrie, Bags und Diagnosebilder bleiben lokal.

Bei einer parallelen Bag-Aufzeichnung darf der exakte Zielpfad vor
`ros2 bag record -o ZIELPFAD ...` **nicht** angelegt werden: rosbag2 bricht bei
einem bereits vorhandenen Ordner ab. Nur den Elternordner erzeugen, fuer `-o`
einen noch nicht existierenden Kindpfad verwenden und unmittelbar danach PID,
Prozessstatus sowie die entstehende `metadata.yaml`/Datenbank pruefen. Ein
gestarteter Karten-Stack ist noch kein Nachweis, dass der Recorder laeuft.

## Reihenfolge einer kompletten Kartenaufnahme

```bash
# 1) SLAM starten - Motoren werden SCHARF, Not-Aus bereithalten
./start_slam.sh /pfad/zum/slam.log

# 2) Kartierfahrt (Zeitbudget in Sekunden)
python3 kartierfahrt.py 900

# 3) Karte sichern, SOLANGE SLAM noch läuft
ros2 service call /robot_map_manager/save_map std_srvs/srv/Trigger

# 4) sauber beenden - prüft selbst, ob das Wörterbuch geschrieben wurde
./stop_slam.sh
```

## Manuelle Räume nach der Kartenaufnahme

Die Raumebene verändert weder RTAB-Map noch das OccupancyGrid. Sie darf erst
nach einem bestätigten Save derselben Karte bearbeitet werden und wird unter
deren SHA-256-Fingerabdruck separat gespeichert:

```text
~/.local/share/amadeus/semantic_maps/<fingerprint>/
```

Die sichere Reihenfolge ohne Fahrbefehl lautet:

1. `/robot_map_manager/status_json` zeigt die erwartete Live-Karte.
2. In der Amadeus-App **Karte für Räume speichern** bewusst auslösen.
3. Warten, bis `/semantic_map/status_json` denselben Fingerabdruck und
   `editable:true` meldet.
4. Raum als Polygon zeichnen, Zielpunkt strikt innerhalb setzen und speichern.

Ein Kartenwechsel sperrt das alte Overlay. Es wird nicht automatisch auf eine
neue Wohnungskarte übertragen. Details und Negativtests stehen in
`docs/SEMANTIC_MAP_INTEGRATION.md` und `docs/ROBOT_TRANSFER.md`.

## Lokalisierung prüfen

Fuer die LiDAR-/AMCL-Lokalisierung immer den Starthelfer verwenden. Er prueft
vor jedem Start, ob die PGM-Schwellwerte unbekannte Kartenzellen erhalten:

```bash
bash tools/kartierung/start_lidar_lokalisierung.sh \
  /absoluter/pfad/zur/map.yaml oak:=false
```

Der Aufruf ist ohne `active_drive:=true` motorlos. Ein scharfer Start verlangt
weiterhin die separate persoenliche Fahrfreigabe und
`AMADEUS_FAHRFREIGABE=JA`. Die Pruefung kann auch einzeln laufen:

```bash
python3 tools/kartierung/karte_fuer_nav2_pruefen.py /absoluter/pfad/map.yaml
```

Seit dem Vollscan-Fix vom 16.08.2026 ist keine Suchfahrt fuer den Normalstart
erforderlich: `global_scan_localizer` vergleicht den stationaeren kompletten
LiDAR-Scan mit allen freien Kartenpositionen und Blickrichtungen. Nur wenn

- Gesamtscore mindestens 0,85,
- mindestens 85 % der Endpunkte hoechstens 15 cm von einer Kartenwand liegen,
- der beste Treffer mindestens Faktor 1,15 vor der zweitbesten raeumlich oder
  winklig getrennten Hypothese liegt und
- AMCL genau diesen Treffer fuer die aktuelle Karte und einmalige
  Initialisierungs-ID
  uebernimmt,

wird `/localization/ready=true`. AMCL-Kovarianz allein ist kein
Wahrheitsnachweis. Der Matcher publiziert keine Fahrbefehle; bei einem
mehrdeutigen Scan bleibt das Fahrtor geschlossen.

Zwei rein lesende Diagnosewerkzeuge erzeugen Bilder ausschliesslich unter
`~/.local/share/amadeus/diagnostics/`:

```bash
python3 tools/kartierung/globale_scan_pose.py
python3 tools/kartierung/scan_karten_abgleich.py
```

Das erste zeigt die getrennten globalen Hypothesen, das zweite legt den Scan
ueber die aktuell von AMCL gemeldete Pose. Beide besitzen weder einen
`/initialpose`- noch einen `cmd_vel`-Publisher.

Der alte begrenzte Suchhelfer bleibt nur fuer beaufsichtigte Diagnose und
Vergleichsmessungen erhalten. Er fuehrt nach scharfem Start und persoenlicher
Freigabe eine volle Drehung, hoechstens 0,25 m Vorwaertsfahrt und danach im
garantierten Stillstand bis zu 20 AMCL-No-motion-Updates aus:

```bash
AMADEUS_FAHRFREIGABE=JA python3 \
  tools/kartierung/amcl_lokalisierungsdrehung.py \
  --degrees 360 --forward-meters 0.25
```

Die stationaeren Updates senden keine Fahrbefehle. Sie veranlassen AMCL nur,
weitere aktuelle LiDAR-Scans auszuwerten, bis die unveraenderte
Lokalisierungsgrenze erreicht ist. Der separate Fahrtor-Vertrag begrenzt die
Suche weiterhin auf 0,04 m/s, 0,15 rad/s, 0,35 m Odometrieweg und 110 s.

Sie lehnt insbesondere eine von ROS `map_saver` erzeugte Karte ab, wenn deren
Grauwert 205 durch einen zu hohen `free_thresh` beim Laden zu freiem Raum
wuerde. Reine binaere Testkarten ohne unbekannte Region sind weiterhin
zulaessig. Fuer die alte RTAB-Map-Lokalisierung gilt separat:

```bash
./start_lokalisierung.sh /pfad/zum/lok.log     # delete_db:=false, localization:=true
python3 lokalisierung_test2.py                 # dreht 360° und zählt Lokalisierungen
./stop_slam.sh
```

## Auswertung

```bash
python3 karte_ansehen.py ~/.local/share/amadeus/maps/amadeus/<version>/
python3 merkmale_messen.py                     # Bildmerkmale + Tiefenabdeckung
```

---

## Vier Fallen, die hier real zugeschlagen haben

**1. Das visuelle Wörterbuch geht beim Beenden verloren.** Dann ist die Karte
geometrisch intakt, aber Lokalisierung unmöglich. Ursache ist *nicht* nur
`kill -9`: Ein `kill -INT -<PGID>` an die Prozessgruppe trifft rtabmap doppelt
(direkt vom Kernel und weitergereicht von launch) und bricht das Speichern
genauso ab — der Prozess stirbt mit `exit code -2`. Deshalb schickt
`stop_slam.sh` SIGINT **nur an den Launch-Prozess** und wartet, bis rtabmap von
selbst verschwunden ist. Zusätzlich setzt `start_slam.sh`
`sigterm_timeout:=120 sigkill_timeout:=180`, weil launch sonst nach 5 s
nachtritt. Kontrolle:

```bash
sqlite3 ~/.local/share/amadeus/rtabmap.db "SELECT COUNT(*) FROM Word;"   # muss > 0 sein
```

**2. Der collision_monitor kennt keine Fluchtbewegung.** Seine StopZone-Aktion
nullt *jede* Twist, auch reine Drehungen. Ein Roboter, der einmal in der
StopZone steht, kommt aus eigener Kraft nicht mehr heraus. `kartierfahrt.py`
hält deshalb selbst schon bei 0,35 m an (StopZone beginnt bei 0,26 m vor dem
Sensor), hat für jede Bewegung eine Frist und fährt zur Not rückwärts frei —
höchstens so weit, wie es gerade vorwärts kam, weil dort eben noch freier Raum
war. Rückwärts geht nur direkt auf `/cmd_vel`, weil der Monitor im
Stoppzustand auch das sperren würde.

**3. „map→odom ist nicht die Identität" beweist keine Lokalisierung.**
RTAB-Map lädt beim Start die zuletzt gespeicherte Pose aus der Datenbank und
setzt map→odom danach — ganz ohne Wiedererkennung. Belastbar ist allein
`/localization_pose`: darauf wird nur nach bestätigter Lokalisierung
publiziert. Und der Roboter muss sich bewegen, sonst verarbeitet RTAB-Map wegen
`RGBD/AngularUpdate` überhaupt keine Bilder.

**4. Ein YAML-Schwellwert kann die Karte beim Laden zerstoeren.** Die
LiDAR-Karte vom 14.08. enthielt in der PGM-Datei 29.320 unbekannte Zellen mit
Grauwert 205. Mit `free_thresh: 0.25` interpretierte Nav2 alle davon als frei:
aus 18,49 m² bekannter Freiflaeche wurden 44,88 m² und AMCL suchte auch
ausserhalb des realen Raums. Fuer genau diese Datei erhaelt
`free_thresh: 0.196` die 26,39 m² unbekannte Region. Schwellenwerte nie blind
uebernehmen; vor AMCL immer `karte_fuer_nav2_pruefen.py` ausfuehren.

## Was das Log nicht verrät

Erfolgreiche Wiedererkennungen stehen dort nicht in derselben Form wie die
Ablehnungen — `grep "Loop closure"` findet fast nur `... rejected!`. Die
Wahrheit steht in der Datenbank:

```bash
rtabmap-info ~/.local/share/amadeus/rtabmap.db | sed -n '/^Info:/,$p'
```
