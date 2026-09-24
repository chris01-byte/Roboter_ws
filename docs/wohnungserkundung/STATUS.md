# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus / `chris01-byte/Roboter_ws` · STUFE 1: GRÜN BESTÄTIGT · STUFE 2: gerätefrei GRÜN BESTÄTIGT · STUFE 3: TEILWEISE / NACHWEIS FEHLT · kein neuer realer Fahrversuch · 2026-09-24**

Dies ist der einzige laufende WE-Status. [Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md),
[Meilensteine](MEILENSTEINE.md) und die Sicherheits-/Abnahmereihenfolge bleiben
unverändert. Der vorherige M3/U-Stand ist im
[Archiv](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md) erhalten.

## Stufe 3 – Folgeprüfung Sensorvertrag, Stopp und Shutdown (24.09.2026)

**Gerätefreie Softwareabnahme bestanden; keine Freigabe zum Roboter-Install
oder zur Fahrt.** Auf PR #99
(`feature/we1-stufe3-local-recovery`, Ausgangs-HEAD `2914279`) wurde ein
separates, gerätefreies Kandidatenpräfix
`/home/p/.local/share/amadeus/releases/we1-stage3-complete-1kI6en/install`
gebaut. Die Softwareänderungen liegen in `785b825` (Messvertrag),
`e3d7352` (Navigation/Integration) und `aa699b0` (Shutdown); der
anschließende Dokumentationscommit enthält nur Nachweise. Die Overlayfolge
ist Humble → slam_toolbox → LiDAR-Shutdown →
`we1-10e1858074e7-r1` → Stufe 1 → Stufe 2 → Stage-3-Bypass → Kandidat.
`robot_interfaces`, `vl53_near_field`, `robot_navigation`, `explore`,
`robot_map_manager`, `safety_monitor`, `mission_manager`, `bt_orchestrator`
und `base_hardware` lösen alle aus diesem Kandidaten auf. Für den
`bt_orchestrator`-Build war der vorhandene lokale `behaviortree_cpp`-CMake-
Underlay nötig; die erste Buildrunde ohne ihn scheiterte sichtbar. Es wurde
kein aktives Roboterpräfix überschrieben, kein Gerät geöffnet und kein Motor
angesprochen. `explore` und `robot_navigation` sind in diesem Kandidaten
als Egg-Link auf den isolierten Build eingebunden; Source- und Build-Dateien
wurden per SHA-256 verglichen. Der Kandidat ist deshalb erst nach dem
nachstehenden Commit als Quellstand eindeutig festgehalten, nicht als
unabhängig kopiertes Produktions-Image zu betrachten.

**Sensorursache softwareseitig geschlossen, reale Verfügbarkeit offen:** Die
erweiterte `NearFieldStatus`-Nachricht unterscheidet je Seite unbekannt,
gültig nah, gültig fern, teilgültig und ungültig. Der VL53-Produzent bewertet
Status 5, Zielanzahl, Sigma, plausible Distanz und 8×8-Abdeckung **vor** dem
0,50-m-Nahfilter; beide Originalwolken tragen denselben Stempel wie der
Status. Eine leere Nahwolke mit positivem Fernstatus ist zulässig, ein leerer
oder defekter Frame ohne ihn nicht. Der Costmap-Strahl endet am gemessenen
Ziel (höchstens 0,60 m); unbeobachtete Spalten räumen nichts. Explorer und
Fahrtor benötigen einen frischen passenden Status/Wolken-Verbund; ein kurzes
Status-vor-Wolken-Interleaving wartet im Explorer begrenzt statt sofort den
Elternauftrag als Systemfehler abzubrechen. Der optionale Safety-Nahstopp
bleibt bei fehlender, ungültiger oder veralteter VL53-Quelle gesetzt. Alte
Status-Publisher mit Qualitätswert 0 bleiben im Kandidaten fail-closed.
Die vollständige 64/64-Zonen-Forderung ist sicherheitskonservativ; ob beide
realen Sensoren sie im vorgesehenen Raum liefern, ist **nicht motorlos am
Zielgerät gemessen** und kann die Verfügbarkeit begrenzen.

**Controllerbefund:** Im alten `stopped_bypass` fand NavFn einen sicheren
Polygon-Umweg, während RPP mit 0,80-m-Carrot trotz bereits abknickendem
Pfad vorwärts in eine lokale tödliche Costmap-Zelle steuern wollte; der
Controller stoppte korrekt. Ein Gegenversuch mit 0,10-rad-Drehschwelle ließ
die virtuelle gepaddete Kontur in die feste Barriere schneiden und wurde
**verworfen** (`/tmp/we-stage3-bypass-1vroikvh`). Der aktuelle Kandidat
behält Footprint, Padding, Collision Monitor, Sensor-/Frischegrenzen und
0,35-rad-Drehschwelle, verfolgt aber den nahen 0,40-m-Abschnitt des bereits
vorhandenen NavFn-Pfads. Der getrennte späte Fall (gleiche Barriere,
Einblendung bei Basis-x=1,50 m, gepaddete Geradeausfront x=1,83 m,
Hindernis ab x=2,00 m) zeigte einen **notwendigen Controller-Stopp und
anschließende sichere autonome Umfahrung bis Ziel A**. Ein früher Lauf
erreichte A, brach B jedoch vor Erfolg ab (`/tmp/we-stage3-bypass-9hs81pya`).
Die Diagnose fand zwei Races: Ein Odometrie-Callback aktualisierte seinen
Empfangszeitpunkt **nach** der Uhrzeitaufnahme der Sicherheitsprüfung;
die neue Nachricht wurde fälschlich als künftig verworfen (`age_s=-0.029`,
`/tmp/we-stage3-bypass-5eo3h5ys`). Außerdem konnte nach positiver
Revalidation einer geänderten Karte ein inhaltlich identisches Folgeupdate
wegen ausstehendem Policy-Takt das Ziel stornieren
(`/tmp/we-stage3-bypass-hkj066g9`). Der Zeitvergleich wird nun nach dem
Quell-Snapshot vorgenommen; der Fingerprint der letzten positiv validierten
Geometrie hält exakt identische Folgebeobachtungen aktuell. Wirklich neue
Inhalte erfordern weiterhin volle Rohkarten-/Scope-Revalidation. Der finale
späte Lauf bestand mit unveränderter Barriere: Controller-Stopp, sichere
Wiederanfahrt, automatisch gewählte Ziele A und B erfolgreich, 0 m rückwärts,
höchstens ein Nav2-Kind, kein Polygonverstoß, Elternmission weiter aktiv
(`/tmp/we-stage3-bypass-z86sal9u`). Keine Ziel- oder Scope-Ausweitung.

**Gerätefreie Gegenproben auf dem zuletzt gebauten Kandidaten:**
`explorer_bypass` mit dauerhafter Barriere bestand mit automatisch gewählten
Zielen A und B, 3,304 m Gesamtweg, 0,400 m zu B, 0 m rückwärts, höchstens
einem Nav2-Kind und sicherem geplantem/gefahrenem Footprint
(`/tmp/we-stage3-bypass-vwu6_1uk`). `disappear` belegte Stopp und sichere
Fortsetzung nach Wegfall eines vorübergehenden Hindernisses
(`/tmp/we-stage3-nav2-j0dmiqjx`). `local_blocked` belegte A-Abbruch → B
erfolgreich → A nach neuer zulässiger Route wieder auswählbar, obwohl der
Direktkorridor blockiert blieb. `no_exit` endete ohne Nav2-Kind/Bewegung
mit erklärtem Teilstand (`/tmp/we-stage3-bypass-m693swi7`).
`frontier_replan` belegte A-Cancel → B-Erfolg und weiterlaufende Elternmission,
ohne A-Fehlerbudget. Der Prüfer liefert nun die für den aktiven
Sicherheitsvertrag nötige periodische Sensor-/Odometrie-Telemetrie und
zerstört seinen Action-Client erst nach Executor-Drain. Ein erster
Wiederholungslauf war funktional korrekt, hatte aber eine asynchrone
`Destroyable`-Aufräummeldung; die nächste Wiederholung war sauber.
`frontier_no_source` scheiterte zunächst nur im Prüfer: Anders als
`frontier_replan` startete dieses Szenario gar keinen periodischen
Safety-Telemetrietimer, sodass schon A nicht laufen konnte. Nach dessen
Ergänzung: genau ein Kind, ein Cancel, keine Fahrbefehle oder Wiederanfahrt,
bounded Partial am Gesamtmissionsbudget (ROS-Domain 217).
1 018 Python-Tests der fünf betroffenen Pakete bestanden. Der Kartenmanager
beendet unter Einzel-PID-SIGINT zweimal einen laufenden Save-Callback ohne
Traceback, verlorenen Save oder hängenden Prozess
(`/tmp/we-mapmanager-shutdown-71iqo7b5`). Der Humble-Fehler entstand durch
Kontextinvalidierung des globalen Signalhandlers während
`SingleThreadedExecutor.take_message()`; jetzt setzt der eigene Handler nur
ein Stop-Ereignis, der Executor wird vor Knoten und ROS-Kontext beendet.
Unerwartete `RuntimeError` werden nicht mehr als Shutdown-Fall abgefangen.
Der Smoke trifft den Save-Callback, nicht deterministisch exakt den
historischen `take_message()`-Zeitpunkt.

**Harte Fehler:** Ein gültig empfangenes, aber rechts ungültiges VL53-Telegramm
führt während Fahrt zu Gate-Stopp und terminalem Kind ohne Recovery
(`/tmp/we-stage3-nav2-v97h6vxb`). Das Software-Not-Aus wurde direkt im
Fahrtor fail-closed angebunden. Ein Lauf mit 0,0263 m virtuellem Nachlauf
überschritt die anfängliche, willkürliche 0,025-m-Prüfergrenze
(`/tmp/we-stage3-nav2-9kf1y732`) und bleibt als Fehlversuch dokumentiert.
Die Spur zeigte unverzügliche Nullausgabe des Gates und anschließendes
Abbremsen im unveränderten Velocity-Smoother. Die gerätefreie
Diagnosegrenze wurde deshalb **offen als Testkorrektur** auf 0,04 m aus
0,10 m/s Anfahrt, 0,30 m/s² konfigurierter Verzögerung, 0,10-s-
Publikationsphase und einem 0,10-s-Prüfertakt hergeleitet. Zusätzlich
müssen Gate binnen 0,15 s und `/cmd_vel` binnen 0,45 s Null melden; die
Grenze für ungültige Sensorik bleibt 0,025 m. Der Wiederholungslauf
erreichte 0,0220 m / 0,108 s / 0,415 s
(`/tmp/we-stage3-nav2-ll4ojc90`). Das ist ein Nachweis der **Software-
Befehlskette**, nicht des hardwired Not-Aus oder einer realen Bremsstrecke.
Unterbrochenes `odom→base_link`-TF ließ
zuvor 0,172 m Nachlauf zu (`/tmp/we-stage3-nav2-0v9hl3d3`). Der neue
Gate-Nachweis verlangt Basis-TF jünger als 0,2 s und zusammengesetztes
`map→base_link` jünger als 0,8 s; danach betrug der virtuelle Nachlauf
0,0366 m und die Mission brach hart ab (`/tmp/we-stage3-nav2-10icbsbf`).
Die 5-cm-Diagnosegrenze für erst nach einem Timeout erkennbaren TF-Ausfall
ist von den Grenzen für explizites Software-Not-Aus bzw. Sensorfehler
getrennt; keine Produkt-Sicherheitsgrenze wurde gelockert. Reale TF-Raten sind
motorlos zu prüfen. Software-Not-Aus ersetzt den hardwired Not-Aus nicht.

**Rest und Abnahmegrenzen:** Gerätefreie Softwareabnahme **BESTANDEN**;
motorlose Zielsystemprüfung **OFFEN**, reale Stufe-3-Abnahme **OFFEN**.
Weder ein aktiver Roboter-Install noch reale Sensorqualität/TF-Frequenz noch
eine reale Fahrt sind mit diesem Kandidaten geprüft. Vor jeder Übernahme den
Quell-/Install-Hash und die tatsächliche Overlaykette am Zielgerät messen,
dann motorlos Lifecycle, Sensorfrische, Karten-/TF-Quellen, Safety und
zweimaligen kontrollierten Shutdown prüfen. Für die spätere getrennt
freigegebene Realabnahme vor Ort messen: Startpose, feste
Hinderniskontur, lichte Alternativbreiten, vollständigen Schwenkbereich,
Auslauf, aktuellen Kartenframe/Scope sowie erreichbaren Hardware-Not-Aus.
Die frühere linke VL53-Auffälligkeit und die fehlende Frontier im engen
realen Scope dürfen nicht durch synthetische Daten überdeckt werden.
Rückfall: Kandidatenpräfix nicht sourcen; vorhandene Installationen bleiben
unverändert. Die folgenden Abschnitte dokumentieren den historischen
Ausgangsstand und sind durch diesen neuen Softwarestand nur insoweit ersetzt,
wie oben ausdrücklich belegt.

## Stufe 3 – begrenzte lokale Blockadebehandlung, 2026-09-23

**Aktuelles Ergebnis des Umfahr-Folgeauftrags:** Frühzeitige Umfahrung einer
dauerhaft stehenden, geometrisch umfahrbaren Barriere ist **gerätefrei mit
echtem Nav2 und automatischer Explorerwahl nachgewiesen**. Anschließend wurde
auch ein zweites automatisch gewähltes Ziel erfolgreich verarbeitet; derselbe
Elternauftrag blieb aktiv. Der getrennte Fall „notwendiger Stopp und danach
Befreiung“ scheitert weiterhin kontrolliert. **Stufe 3 insgesamt bleibt GELB.**
Keine Hardware wurde geöffnet, kein realer Fahrversuch oder Deployment ausgeführt.

**Codebefunde A/B, beide bestätigt:** Bei `a8710db` meldete die aktuelle
Costmap eine alternative Verbindung zum Ziel, während der Nahkorridor ein
Hindernis enthielt; `_wohnungserkundung_local_blocked_rechecked()` gab dennoch
`false` zurück. Der neue Produktionsstand `90379d9` (Funktionsänderung
`4a20dea`) verlangt eine frische, nach der Blockade empfangene Costmap mit
derselben Rastergeometrie wie die exakt korrelierte Rohkarte. Die bestehende
geodätische Evidenz wird auf der **Schnittmenge** aus Rohkarten-/Scope-Maske
und nicht tödlichen, bekannten Costmap-Zellen berechnet. Start und Ziel dürfen
nicht projiziert werden. Ein Umweg darf damit die Aufgabe freigeben, auch
wenn der Direktkorridor weiterhin blockiert ist. Der Beleg liefert keine
Fahrkommandos; Nav2 und seine Polygonprüfung bleiben verbindlich.

Der reale VL53-Produzent erzeugt sowohl bei gültigen Fernmessungen außerhalb
des 0,50-m-Nahfensters als auch bei vollständig ungültigen Messungen dieselbe
leere Originalwolke. Das wurde mit seinen beiden reinen Produktionsmethoden
ohne Treiberimport ausgeführt: Punktzahlen **0 / 0 / 64** für gültig fern /
ungültig nah / gültig nah. Der alte Test-Nullpunkt verdeckte diese Mehrdeutigkeit.
Empfangszeit, Sensorstempel, Punktzahl und Messgültigkeit sind jetzt getrennt:
leer = frisch empfangen, Messgültigkeit **unbekannt**; Nullvektor/NaN/fehlerhaftes
Layout = ungültig. Der unveränderte 0,8-s-Vertrag gilt bis zur Entscheidung
auch für das tatsächliche Quellalter. Unbekannte, fehlende, zukünftige oder
veraltete Quellen geben keine lokale Recovery frei. Leere Wolken sind kein
Freiraum- oder Sensorgesundheitsbeleg.

| Gezielter Nachweis | Ergebnis und Grenze |
|---|---|
| Festes Diagnoseziel, Barriere von Beginn an vorhanden | NavFn 119 Pfadpunkte, kein ungültiger Polygon-Sweep; unveränderter Controller erreicht das Ziel nach 2,69 m. Keine Aussage über autonome Auswahl. |
| `explorer_bypass`, neues installiertes `explore` | Automatische Wahl `(3,475; 1,525)` → dauerhafte Barriere umfahren → A erfolgreich → neue Rohkarte bestätigt A-Aufgabe abgeschlossen → anderes Ziel automatisch gewählt **und erfolgreich** → Elternauftrag weiterhin aktiv. 3,253 m Gesamtweg, davon 0,453 m zum Folgeziel; maximal ein Kind, 0 m rückwärts. Alle geplanten und dicht abgetasteten gefahrenen Footprints kollisionsfrei/im Scope. Tatsächlicher gepaddeter Live-Footprint vor Fahrt abgeglichen. |
| `stopped_bypass`, unveränderte Geometrie und Parameter | Neuer NavFn-Umweg vorhanden, dessen 111 Posen ohne Polygonverletzung; Controller verwirft später seine vorausberechnete Bewegung mit `detected collision ahead` und endet nach 1,5 s Fehlertoleranz. Raw-/Gate-/Smoother-/Monitor-Ausgang werden null; keine nachgeschaltete Sperre eines fortbestehenden Fahrwunsches. Linke Seite an der Endpose zwei Nahpunkte, rechte leer/unbekannt: Explorer bricht sicher ab. **Befreiung nicht bestanden.** |
| `no_exit`, Barriere über gesamte Raumbreite | NavFn `ABORTED`, kein Pfad; Explorer sendet 0 Kindziele, 0 m Bewegung, Elternaktion endet am 10-s-Testbudget mit erklärtem Teilstand, nicht mit Vollabschluss. |
| `blocked`, linke Blockade plus leere rechte Originalwolke | Genau ein terminales Kind, Elternabbruch statt ungeprüfter Recovery, 0 m weitere Bewegung nach dem Stopp. Der historische Nullpunkt-basierte „gesund“-Nachweis ist damit ausdrücklich ersetzt. |
| Bestehender Prozessprüfer `local_blocked` / `local_no_exit`, Fake-Nav2 | A-Abbruch → B automatisch erfolgreich → B-Aufgabe durch Rohkarte abgeschlossen → A trotz **weiter belegtem Direktkorridor** über frische alternative Route wieder gewählt; maximal ein Kind. Ohne Alternative begrenzter Teilstand. Das ist Policy-, kein Fahrnachweis. |

**Erstes Scheitern präzisiert:** Der beibehaltene `legacy_probe` reproduzierte
den alten Controllerstopp bei synthetischer Pose `(1,126; 1,532)`, nur etwa
0,09 m vor der gepaddeten Vorderkante zur Barriere. Das Ziel selbst hatte
einen freien Footprint; im ersten Stoppfenster lag noch der ursprüngliche
gerade Pfad vor. Der neue späte Stoppfall trennt dies weiter: Es gibt bereits
einen zulässigen globalen Umweg, aber der Regler kann seine lokale Bewegung
aus der erreichten Pose nicht kollisionsfrei ausführen. Die genaue nötige
Reglerabstimmung ist damit **nicht** bewiesen; weder Lookahead noch Kollisions-
oder Geduldsgrenzen wurden versuchsweise gelockert. Die frühe Umfahrung
funktioniert mit der vorhandenen Nav2-Konfiguration.

Zwei Fehler des erweiterten Prüfers wurden vor der Abnahme korrigiert:
Plananfragen warten jetzt auf aktive Lifecycles statt bloße Serverexistenz;
unveränderte Karten erhöhen nur `observed_maps`, nicht `accepted_maps`.
Das erste zusätzliche Informationsfenster lag im alten Abschlussfenster;
die endgültige Fixture besitzt von Anfang an zwei getrennte Fenster (unten).
Hindernis, Footprint, Sicherheitsparameter und Erfolgskriterien wurden dabei
nicht verändert. LiDAR und acht VL53-Strahlen verwenden dieselbe synthetische
Wand-/Barrierengeometrie; die Nahsensorframes entsprechen der URDF.
Ein Abschlusslauf meldete außerdem `cannot use Destroyable because destruction
was requested`: Der Prüfer zerstörte seinen ROS-Knoten vor dem Ende des
Executor-Threads. Im Prüfer wird der Executor jetzt vor der Knotenzerstörung
beendet. Das behebt nicht den separat offenen Kartenmanager-Shutdown-Befund.
Die anschließenden Läufe `fixed_bypass` und `no_exit` endeten ohne diese
Ausnahme und ohne verbliebene eigene Nav2-/Explorerprozesse.

**Build und Evidenzbindung:** 917 direkte Explorer-Tests und 917 registrierte
`colcon test`-Tests bestanden, ebenso `git diff --check`; keine erneute
Stufe-1/2-Gesamtprüfung. Produktionsquelle `90379d9`, finaler Prozessprüfer
`d13a6c9`. Neues isoliertes Install:
`/home/p/.local/share/amadeus/releases/we1-stage3-bypass-s8QMY8/install`.
Kette: ROS Humble → bestätigte Stufe-1-Kette → Stufe 2 → dieses `explore`.
Quelle/Install SHA-256 von `explore_node.py` jeweils
`485435a0effe6c32efd74da4995a92584d6b01dff255f2010c6e003327fb8fe0`;
Nav2- und Collision-Konfiguration bytegleich mit dem Stufe-1-Install.
Der automatische Umfahrfall und die beiden gezielten bestehenden Prozessfälle
bestanden auch gegen dieses Install. Lokale synthetische Evidenz:
`/tmp/we-stage3-bypass-ywt3wj0n` (vollständiger automatischer Erfolg),
`/tmp/we-stage3-bypass-yi9lljh7` (festes Ziel, finales Install/Prüfer),
`/tmp/we-stage3-bypass-h5d1wnip` (unlösbarer Gegenfall, finales Install/Prüfer),
`/tmp/we-stage3-bypass-3kjd16r6` (Stoppfehler inklusive Reglerbögen),
`/tmp/we-stage3-nav2-itr_s561` (historische Diagnose),
`/tmp/we-stage3-nav2-yehnnsum` (leere rechte Quelle).
Rückfall: neues Präfix weglassen; vorhandene Installationen wurden nicht ersetzt.

Reproduktion nur gerätefrei, aus diesem Themenworktree und ohne parallelen
Prüfer in Domain 219 (jede Mode einzeln starten):

```bash
source /opt/ros/humble/setup.bash
source /home/p/amadeus_slam_toolbox_ws/install/setup.bash
source /home/p/.local/share/amadeus/releases/we1-ldlidar-shutdown-overlay/install/local_setup.bash
source /home/p/.local/share/amadeus/releases/we1-10e1858074e7-r1/install/local_setup.bash
source /home/p/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923/install/local_setup.bash
source /home/p/.local/share/amadeus/releases/we1-stage2-6fd36d5-20260923/install/local_setup.bash
source /home/p/.local/share/amadeus/releases/we1-stage3-bypass-s8QMY8/install/local_setup.bash
python3 tools/kartierung/wohnungserkundung_nav2_stage3_smoke.py --mode fixed_bypass
python3 tools/kartierung/wohnungserkundung_nav2_stage3_smoke.py --mode explorer_bypass
python3 tools/kartierung/wohnungserkundung_nav2_stage3_smoke.py --mode no_exit
# Erwarteter offener Abnahmefehler, kein Gruen-Nachweis:
python3 tools/kartierung/wohnungserkundung_nav2_stage3_smoke.py --mode stopped_bypass
```

**Noch nötige getrennte Arbeiten:** Für sichere Wiederfreigabe mit gesunder,
aber leerer Originalwolke fehlt positive Produzentenevidenz. Betroffen wären
`vl53_near_field_node.py`, sein öffentlicher Statusvertrag
`robot_interfaces/msg/NearFieldStatus.msg` und die Verbraucher Explorer/Fahrtor.
Die Gültigkeit müsste **vor** dem Nahbereichsfilter je Sensor mit demselben
Messstempel ausgewiesen und für gültige Fernmessung, fehlende Messung und
ungültige Qualität getrennt geprüft werden. Eine solche additive
Sensorvertragserweiterung benötigt ein separat abgegrenztes und freigegebenes
Schnittstellenpaket gemäß AGENTS; die heutigen Flags/-1-Distanzen belegen sie
nicht. Der bestehende Fahrtor-Heartbeat allein belegt ebenfalls keine
Messqualität. Für die Stoppbefreiung bleibt außerdem der vorhandene
`robot_navigation`-Reglerpfad gezielt zu prüfen; keine zweite Navigation oder
ungeprüfte Parameteränderung. Reale Abnahme bleibt bis Shutdownklärung,
aktueller Platz-/Scope-Messung und neuem Vor-Ort-Auftrag gesperrt.

**Folgeauftrag Umfahrung – vorab festgelegter Gerätefrei-Vergleich:** Basis
PR #99 / `a8710db`, unverändert nach erneutem Fetch; eigener vorhandener
Themenbranch, kein Hardwarezugriff. Die Diagnose verwendet den bestehenden
Echt-Nav2-Prüfer in Domain 219. Synthetischer Freiraum:
`x=0,15..4,85 m`, `y=0,25..2,75 m`; Scope `0..5 × 0..3 m`;
Start `(0,85; 1,525; 0)`, festes **Diagnoseziel** `(3,30; 1,525; 0)`.
Das unbewegliche Rechteck `x=2,00..2,30`, `y=1,325..1,725 m` bleibt
während des gesamten Umfahrnachweises bestehen. Beidseits bleiben 1,075 m
lichte Breite. Die reale gepaddete Kontur ist
`x=-0,13..0,33`, `y=±0,25 m` (Umkreisradius 0,414 m); die Geometrie
enthält damit Platz für einen Umweg und eine freie Drehkontur vor der Barriere.
Die VL53-Testframes entsprechen der URDF-Montage `(0,290; ±0,095; 0,215)`.
Nav2-, Footprint-, Collision- und Frischeparameter bleiben unverändert.

Vorher festgelegte Abnahme: NavFn liefert einen Pfad um das bleibende
Hindernis; jeder geplante und tatsächlich gefahrene Footprint bleibt im Scope
und kollisionsfrei; der echte Controller führt über Fahrtor, Smoother und
Collision Monitor zum Ziel (höchstens 120 s, 6 m Fahrweg, kein Rückwärtsgang).
Pfad, Raw-/Gate-/Smoother-/Monitor-Ausgang und virtuelle Pose werden getrennt
erfasst. Erst nach diesem isolierten Nachweis folgt automatische Explorerwahl
mit demselben Hindernis und belegtem Fortschritt derselben Mission.
Frühzeitige Umfahrung, notwendiger Stopp mit Befreiung und unlösbare Blockade
sind getrennte Ergebnisse. Das feste Ziel belegt keine autonome Zielwahl.
Der anschließende Explorerfall verwendet zwei von Beginn an vorhandene,
getrennte unbekannte Informationsfenster bei `x=2,90..3,20` und
`x=4,20..4,50`, jeweils `y=1,30..1,70 m`; nach dem ersten Ziel wird nur
das erste Fenster beobachtet. Weder Zielposition noch Folgeaufgabe werden
an den Explorer vorgegeben. Im separaten Stoppfall erscheint dieselbe
Barriere bei `Basis-x >= 1,20 m`; sie bleibt danach dauerhaft stehen. Nach
dem sensorisch ausgelösten Reglerstopp wird sie zusätzlich in der Rohkarte
beobachtet. Für den unlösbaren Gegenfall versperrt dieselbe Wandstärke
den gesamten Freiraum quer (`y=0,25..2,75`). Keine Parameteranpassung
zwischen diesen Fällen.

### Historische Ausgangsnachweise bis a8710db

**Produktionsnaher, aber gerätefreier Nav2-Prozessprüfer (23.09.):** Der neue
Prüfer `tools/kartierung/wohnungserkundung_nav2_stage3_smoke.py` verwendet
in der festen privaten DDS-Domain 219 den echten Stage-1/2/3-Explorer, den
unveränderten realen Nav2-Controller/Planner/BT, das Missionsfahrtor, den
Velocity Smoother und den unveränderten WE-Collision-Monitor. Nur Rohkarte,
Kartenmanagerstatus, LiDAR/VL53, TF/Odometrie und die differentielle Basis
sind synthetisch. Der Prüfer startet **keinen** Hardware- oder Sensortreiber.
Der bestehende Acht-Szenarien-Prozessprüfer mit Fake-Nav2 bleibt als
Missionsregression bestehen; er ist nicht der Beleg für reale Controllerfahrt.

Im zweimal bestandenen vollständigen Fall `disappear` fuhr das virtuelle
Ziel A zunächst an, ein eingespeistes VL53-/Costmap-Hindernis löste den
echten Regler-Kollisionsstopp aus (nur 2,2–2,5 mm Posedifferenz im
Beobachtungsfenster), und nach Freigabe der Sensorstrecke fuhr die virtuelle
Basis weitere 0,534–0,536 m. Nav2 erreichte A; eine neue Rohkarte belegte
den Abschluss der A-Frontier; ein **anderes** Frontierziel wurde automatisch
gestartet, während der Elternauftrag weiterlief. Maximal ein Nav2-Kindziel
war aktiv. Der vorhandene BT hatte keinen Spin-/BackUp-Fahrpfad. Dies erfüllt
den gerätefreien A-Fall mit echter Navigationskette, ist aber **keine reale
Probefahrt** und kein Nachweis einer dauerhaften Umfahrung.

Der erste produktionsnahe Fall mit dauerhaftem Hindernis zeigte einen
zusätzlichen Integrationsfehler: Nach A-Blockade wurde B gesendet, aber das
Hindernis lag auf Bs Route, nicht auf dem metrischen Ziel B. Nav2 stoppte
und brach auch B ab; die frühere Klassifikation deutete diesen terminalen
Abbruch als `SYSTEM_FAILURE`, der Elternauftrag endete. Die Stage-3-Änderung
klassifiziert einen solchen **bereits terminalen** Abbruch zusätzlich als
`LOCAL_BLOCKED`, nur wenn eine frische globale Costmap eine tödlich belegte
Zelle im nahen zielwärtigen Korridor nachweist, die Basis stillsteht und
Not-Aus, LiDAR, beide VL53, TF und Odometrie frisch/gültig sind. Ohne diesen
positiven Beleg bleibt es `SYSTEM_FAILURE`. Mit dem neuen isolierten
`explore`-Install
`/home/p/.local/share/amadeus/releases/we1-stage3-routeblock-20260923/install`
blieb der Elternauftrag nach zwei echten Nav2-Abbrüchen
aktiv, ohne weitere Bewegung oder konkurrierende Kindziele. Dieser Fix
ändert nur die begrenzte Aufgabenentscheidung, nicht den Fahrpfad oder eine
Sicherheitsgrenze.
Eine als lokal blockiert zurückgestellte Aufgabe wird auch bei freiem
metrischem Ziel erst wieder freigegeben, wenn eine **neuere** Costmap den
nahen Zielkorridor ohne tödlich belegte Zelle zeigt. Im produktionsnahen
Fall mit bleibendem Hindernis blieb die Basis nach insgesamt drei durch
das Profil begrenzten Nav2-Kindzielen stehen und die Mission wartete auf
eine sichere Alternative; maximal ein Kindziel war gleichzeitig aktiv.

**Damals offen; frühe Umfahrung inzwischen oben geschlossen:** Der produktionsnahe `bypass`-Fall mit zwei unbelebten
synthetischen Hindernispositionen stoppte sicher, fand aus der nahen Pose
aber keinen ausführbaren Umweg zum ursprünglichen Ziel; der Controller
meldete `Controller patience exceeded`. Deshalb sind Umfahrung bei dauerhaft
vorhandenem, tatsächlich umfahrbarem Hindernis und spätere sichere Bewegung
nach Zurückstellung weiterhin nicht nachgewiesen. Auf dem realen Roboter
fand der letzte motorlose WE-Lauf zudem keinen gültigen Frontierkandidaten
im bestätigten engen Scope; die aktuelle linke Barriere bewirkte nur 30-%-
Verlangsamung. Der einmalige Humble-Shutdown-Race des Kartenmanagers ist
weiter ungeklärt. Keine Motoren wurden für diese neuen Prüfungen aktiviert;
kein Sicherheitsparameter oder WE-Profil wurde gelockert.
Das neue Install löst nur `explore` auf; Kartenmanager, Mission Manager,
Navigation, Safety, VL53, LiDAR und Basis kommen weiterhin aus der
bestätigten Stufe-1-Kette, nach Stufe 2 gesourct. Quelle und neues
`explore_node.py`-Install haben denselben SHA-256
`be6c8f7da787fa51a57a9bebf87cf0ee1e440a049be57f3eef7af897b6c9c6ef`.
`colcon test` bestand mit **904 Explorer-Tests**; der bestehende
Gesamtprozessprüfer bestand mit **allen acht Szenarien** auch gegen dieses
neue Install. Der offene PR #99 bleibt ungemergt. Rückfallweg: neues
Stage-3-Präfix weglassen und zum vorigen isolierten Kandidaten zurückkehren;
am aktiven Roboter-Install wurde nichts umgestellt.

**Neues linkes Testhindernis, ausschließlich motorlos (23.09. abends):** Die
anwesende Person bestätigte einen unbelebten Gegenstand links vor dem Roboter,
personen-/tierfreien Bereich und erreichbaren hardwired Not-Aus. Der Stack
startete ohne Auftrag mit `active_drive:=false`, `enable_auto_explore:=false`;
die Basis meldete `dry_run=true`, `allow_rs485=false`. Der linke VL53 meldete
frisch und wiederholt etwa 0,24–0,25 m, der rechte keinen Nahpunkt. Im
unveränderten WE-Mapping-Profil verwendet der Collision Monitor den
bewegungsabhängigen `FootprintApproach` plus `SlowZone`, **keine** feste
0,26-m-StopZone. Ein 2-s-Testwunsch von 0,08 m/s auf dessen Eingang ergab am
Ausgang höchstens 0,024 m/s (30-%-SlowZone), nicht einen Vollstopp. Die
Platzierung belegt damit Erkennung und Verlangsamung, **nicht** den verlangten
Hindernisstopp oder autonome Fortsetzung. Das trockene Odometriesignal aus
diesem Test darf nicht als reale Bewegung oder neue Karten-/Scope-Freigabe
interpretiert werden. Es gab keine Motorbestromung und keine reale Fahrt.

Beim einzigen SIGINT-Stop dieses Vorlaufs beendeten 23 Kinder sauber, aber
`robot_map_manager` starb mit `RuntimeError: Unable to convert call argument
to Python object` im ROS-2-Humble-`take_message()`-Pfad. Quell- und
Install-Datei des vorhandenen Shutdown-Guards sind bytegleich; dieser Guard
reicht für den beobachteten Race nicht aus. Danach liefen keine Roboterknoten
mehr, und LiDAR-, Basis- und sichtbare I²C-Gerätepfade hatten keinen Handle.
Der Shutdown zählt **nicht** als sauber; dieser Integrationsfehler bleibt vor
einem weiteren Realversuch zu reproduzieren/klären. Keine Sicherheitsgrenze
wurde verändert, kein Stage-3-Recovery-Nachweis erbracht.
Ein zweiter vollständiger motorloser Start-/Stopp-Zyklus ohne synthetischen
Fahrwunsch sah denselben linken Nahpunkt (~0,245 m), blieb bei
`dry_run=true`/`allow_rs485=false` und beendete alle 24 Kinder mit einem
Einzel-SIGINT sauber. Keine Tracebacks oder Gerätehandles blieben zurück.
Der erste Shutdown-Race ist damit nicht reproduziert, aber nicht erklärt;
der saubere Wiederholungslauf ersetzt ihn nicht rückwirkend.

**Erneuter Vor-Ort-Vorlauf nach Nutzerfreigabe (23.09.):** Die anwesende Person
bestätigte erreichbaren hardwired Not-Aus, personen-/tierfreien Bereich und
physisch geklärten R9-Nahbereichsbefund. Auf dem Jetson wurde die unten
festgelegte Stufe-1/2/3-Overlaykette mit dem unveränderten lokalen WE-Profil
in der isolierten Domain 217 erneut geprüft. Der vollständige App-Stack lief
mit `active_drive:=false`, `enable_auto_explore:=true` und ohne Auftrag.
`explore` löste aus dem Stufe-3-Install auf, die übrigen WE-Pakete aus dem
Stufe-1-Install. Collision Monitor und alle fünf Nav2-Lifecycle-Knoten waren
aktiv; normierter LiDAR, Rohkarte und beide VL53 publizierten mit etwa 10, 1
und je 3,9 Hz. TF zu Basis, LiDAR und beiden VL53 war verfügbar; Kartenmanager
meldete `ok=true`, Safety `false`, Explorer `idle`, und die Basis blieb bei
`dry_run=true`, `allow_rs485=false` und null Sollwerten. Der einzelne SIGINT
beendete alle 24 Launch-Kinder sauber; danach waren LiDAR-, Basis- und
sichtbare I²C-Gerätepfade ohne Handle. Das Launchlog enthält keinen Traceback
oder Prozessabbruch. **Es gab keinen Fahrbefehl und keine Motoraktivierung.**
Dies ist nur ein erneuter passiver Preflight, noch kein produktionsnaher
Hindernisstopp und kein Stufe-3-Abnahmenachweis. Für einen begrenzten
Hindernisversuch fehlen noch die konkrete freie Startpose, unbelebte Barriere
und der sichere Auslauf. Die anschließend gewünschte freie Kurzfahrt ohne
Barriere benötigt stattdessen eine neue Scope-Bindung und enge Bewegungsgrenze;
die Fahrfreigabe allein ersetzt diese Testdefinition nicht.

**Zusätzliche Fahrblocksperre beim geplanten freien Kurztest:** Das verwendete
lokale R9-Profil bindet seine physisch bestätigte Scope-Geometrie ausdrücklich
nur an den damaligen R9-SLAM-Kontext und verbietet die Wiederverwendung nach
einem weiteren SLAM-Neustart. Der passive Vorlauf oben startete SLAM neu.
Deshalb ist diese Scope-Freigabe für eine jetzt startende reale WE-Mission
ungültig, obwohl Profil-Hash und Paketversionen unverändert sind. Die
anwesende Person bestätigte einen freien Raum, aber noch keine erneut an den
aktuellen Kartenframe gebundene Fahrgrenze. Es erfolgte keine Motorbestromung
und kein Fahrbefehl. Weder Scope- noch Sensor- oder Collision-Grenzen wurden
gelockert; vor Bewegung muss ein eng begrenzter Fahrbereich im neuen
Kartenframe gemessen und vor Ort bestätigt werden. Ein freier Kurztest ohne
Hindernis kann Stufe 3 ohnehin nicht auf GRÜN setzen.

**Enger freier Kurztest nur motorlos (23.09.):** Nach Bestätigung, dass nur der
aktuelle freie Raum freigegeben und dessen Ausgänge geschlossen sind, wurde
ein neues, ausschließlich lokales Einmalprofil
`~/.local/share/amadeus/profiles/we1-stage3-free-short-20260923.yaml` angelegt
(SHA-256 `8380e87b764693ae2965d7d890c5af4fd91da3b8ed2a7fb673c96b646feb9dfe`).
Sein achtseitiger kleiner Scope wurde aus der *neuen* stationären LiDAR-/TF-
Messung im aktuellen Kartenframe begrenzt; keine Wohnungsgeometrie wurde ins
Repository übernommen. Das Profil begrenzt auf ein Frontierziel, einen Fehler,
75 s Gesamtzeit und einen engen Vorwärtskegel; es deaktiviert Coverage,
Portalbeobachtung, Persistenz und den initialen Rundblick, ohne Sensor-,
Footprint-, Collision- oder Frischegrenzen zu verändern. Im erneuten
motorlosen Gesamtstart lag die Kartenpose am erwarteten Ursprung, der kleinste
gültige LiDAR-Abstand bei etwa 1,02 m, beide VL53 und Safety waren frei,
Kartenmanager `ok=true`, Nav2/Collision aktiv und Basis `dry_run=true`,
`allow_rs485=false`. Die echte Mission blieb während des Budgets bei
`we_waiting_for_goal`: kein gültiger Frontierkandidat, kein Nav2-Fahrkommando,
null Odometriebewegung. Sie endete mit Teilstand am Gesamtbudget, der
Missions-BT mit Failure. Ein einzelner SIGINT beendete alle 24 Kinder sauber;
Gerätehandles waren danach frei, im Launchlog kein Traceback oder Prozessabbruch.
**Keine Motorbestromung und keine reale Probefahrt:** Ein scharfer Start aus
demselben Profil hätte kein kontrolliertes Ziel. Nächster Schritt ist eine
erneut physisch bestätigte, gemessene sichere Kurzroute innerhalb des Raums
und ihr motorloser Nav2-/Scope-Nachweis; weder das alte R9-Profil noch ein
größerer Scope dürfen bloß zur Erzeugung eines Ziels verwendet werden.

**Basis:** ausschließlich der bestätigte Stufe-2-Branch
`feature/we1-stufe2-replan-fortsetzung` bei `3fa3ce6`, auf dem eigenen
Themenbranch `feature/we1-stufe3-local-recovery` mit Produktionscommit
`d6c6fa9`; der gestapelte Review steht als PR #99 gegen den Stufe-2-Branch.
Stufe 1/2 sowie alle
Hardware-, Footprint-, Collision-, Scope- und Sensorgrenzen bleiben
unverändert. Es wurde kein reales WE-Profil gestartet und keine Fahrt
freigegeben.

**Fehlerkette:** Die VL53-Punktwolken gehen unverändert in lokale/globale Nav2-
Costmaps und den `collision_monitor`; dessen Ausgang bleibt die letzte
reaktive Instanz vor `/cmd_vel`. Der Explorer verwendet bereits den bestehenden
Nav2-Baum mit `IsPathValid`/`ComputePathToPose` (1 Hz) und `FollowPath`; Spin
und BackUp sind absichtlich nicht an die Fahrkette angebunden. Bei
`Controller patience exceeded` liefert Humble `NavigateToPose` nur den
terminalen Zustand `ABORTED`, keinen Ursachencode. Bisher wurde daraus ein
allgemeiner `RETRYABLE_FAILURE` mit Revisions-Retry; nach erschöpftem Ziel-,
Retry- oder Gesamtbudget endet `ExploreArea` als Teilstand bzw. Fehler und
der Missions-BT als Failure. Ein unsicherer Cancel-/Transportfehler bleibt
sofortiger Systemabbruch. Ein einzelner Hindernisstopp beendet den Auftrag
also **nicht zwangsläufig sofort**, kann ihn aber mangels eigener
Lokalblockade-Entscheidung faktisch beenden.

**Begrenzte Änderung:** Der terminale Abbruch eines Frontier-Kindziels wird
nur bei frischem, positivem globalem Costmap-Hindernisbeleg, gültigem
Stillstand aus Odometrie, frischem map-TF, LiDAR, beiden nichtleeren VL53-
Wolken und frischem freiem Software-Not-Aus als `LOCAL_BLOCKED` eingestuft.
Fehlt einer dieser Belege, wird der Abbruch als `SYSTEM_FAILURE` behandelt;
`SOURCE_INVALIDATED` und `USER_CANCELED` behalten ihre eigenen Pfade.
`LOCAL_BLOCKED` beendet erst das einzelne Nav2-Ziel, stellt die Aufgabe für
mindestens zwei Kartenrevisionen zurück und lässt die bestehende Policy ein
anderes zugelassenes Ziel wählen. Die bisher zulässige Projektion desselben
Frontierziels auf eine benachbarte Costmap-Zelle bleibt nach dieser Blockade
gesperrt, bis eine **neuere** Costmap den ursprünglichen Kandidaten wieder
ohne Projektion freigibt. Das vorhandene Retrylimit, Zielbudget und
Gesamtzeitbudget begrenzen die Versuche. Es wurden weder eigene Fahrbefehle
noch Rückwärts- oder Dreh-Recovery ergänzt.

**Gerätefreie Evidenz:** **902 Explorer-Pytests** bestanden; die
Vertragstests prüfen auch fehlende/frische Sicherheitsbelege. Der bestehende
Gesamtprozessprüfer prüft die begrenzte Zurückstellung, das Verbot paralleler
Nav2-Kindziele und die Elternfortsetzung. Der neue Prozessfall zeigt
synthetisch A-`ABORTED` bei Costmap-Blockade → B automatisch ausgewählt → B
erfolgreich → B-Frontier auf neuer Rohkarte abgeschlossen → A nach freier
neuer Costmap erneut auswählbar. Ein Fall ohne Alternative wartet kontrolliert
bis zum Gesamtbudget, ohne zweites Ziel oder Fahrbefehl. Der Prüfer verwendet
einen eigenen DDS-Bereich (`ROS_DOMAIN_ID=217` voreingestellt) und
synthetische Topics. Beide neuen Szenarien bestanden isoliert aus dem
Quellbaum und gegen das isolierte Stage-3-Install
`~/.local/share/amadeus/releases/we1-stage3-candidate-20260923/install`,
das in der Test-Shell **nach** dem Stage-2-`explore` gesourct wurde.
`ros2 pkg prefix explore` und Python-Import zeigten auf dieses Präfix; die
installierten Laufzeitdateien und das Profil waren bytegleich zur Quelle.
Der Gesamtprozessprüfer bestand nach Prüferstabilisierung sowohl aus dem
Quellbaum als auch gegen das tatsächliche Stage-3-Install mit **acht
Szenarien** (Portal-Erfolg/-Fehler, Mehrraum, Wiederaufnahme,
Karten-Replan, fehlende Folgequelle, lokale Blockade mit B-Fortsetzung und
Blockade ohne Ausweg). Maximal ein Fake-Nav2-Kindziel war gleichzeitig aktiv;
synthetische Fahrbefehlsthemen erhielten null Nachrichten. Frühere lange
Läufe hatten zeitabhängige Fehler des älteren Portal-Positivfalls
(`pose_step_exceeds_jump_limit`) und einmal ein Shutdown-Race des neu
eingeführten Prüfer-Timers. Der Positivfall bestand isoliert; kleinere
synthetische Pose-Schritte bei unverändertem Traversal-Limit und ein
vor Knotenshutdown gestoppter, nur für neue Fälle aktiver Timer und länger
frische synthetische Karten für das unveränderte Drei-Beobachtungen-Fenster
beseitigten die beobachteten Prüferfehler in den beiden achtteiligen
Wiederholungsläufen. Die früheren Flakes bleiben als Teststabilitätsrisiko
dokumentiert, nicht als Produktnachweis umgedeutet.

**Rest / Abnahme:** Diese Evidenz verwendet eine Fake-Nav2-Aktion; weder ein
echter Controller-/Collision-Monitor-Stop noch eine sichere autonome
Ausweichbewegung wurde demonstriert. Insbesondere sind Wiederanfahrt zum
gleichen Ziel nach verschwindendem Hindernis und Umfahrung auf einem neuen
realen Nav2-Pfad noch nicht als Gesamtprozess nachgewiesen. Ein lokaler
Pfadstau bei weiterhin erreichbar erscheinendem Ziel wird derzeit
konservativ als Systemfehler behandelt und noch nicht als `LOCAL_BLOCKED`.
Nach vollständiger Erschöpfung des bestehenden Retrylimits erfolgt auch bei
später freier Costmap noch keine gesonderte `TaskReactivation`; der geprüfte
Reaktivierungsfall hatte einen lokalen Fehlversuch. Der aktive
Sensorfehler-/Lokalisierungsverlust während eines laufenden Kindziels braucht
eine eigene vollständige Fail-closed-Prozessprüfung. Der frühere R9-Befund
links ~0,24 m wurde von der anwesenden Person inzwischen als physisch geklärt
bestätigt; der erneute passive Preflight ergab beidseits keinen Nahpunkt.
**Stufe 3 ist nicht GRÜN; keine Stufe 4 und noch keine reale Fahrt.** Nächster
erlaubter Schritt: zuerst den gewünschten freien Kurztest nur nach neuer
Scope-Bindung und enger Bewegungsgrenze motorlos prüfen, danach beaufsichtigt
fahren. Für die spätere Stufe-3-Abnahme zusätzlich eine unbelebte Barriere,
freien Auslauf und Abbruchgrenze festlegen und die komplette Fortsetzung prüfen.

**Rückfall:** Stufe-3-Overlay nicht sourcen bzw. aus einer neuen Shell nur die
bestätigte Stufe-1/2-Kette laden. Es wurden keine aktiven Roboterinstallationen
oder Geräte verändert. Auf dem älteren Stufe-2-Stand ist lokale
Hindernisfortsetzung weiterhin nicht abgenommen.

## Stufe 2 – Frontierfortsetzung bei Kartenänderungen, 2026-09-23

Die Stufe-2-Arbeit zweigt mit `feature/we1-stufe2-replan-fortsetzung` direkt
vom bestätigten Stufe-1-Branch bei `93f8522` ab. Dessen produktiver
Quellstand ist `5e3fe0a`; die einzige Produktionsänderung liegt in `explore`
bei `6fd36d5`. Das zusätzliche isolierte Install
`~/.local/share/amadeus/releases/we1-stage2-6fd36d5-20260923/install`
enthält ausschließlich dieses neu gebaute Paket. Die Overlaykette ist die
unten für Stufe 1 dokumentierte Reihenfolge mit diesem Stufe-2-Install **als
letztem Präfix**. `ros2 pkg prefix explore` und der Python-Import lösen dort
auf; Quell- und Install-Datei `explore_node.py` haben denselben SHA-256-Wert
`b7d2853d3f56c53ec4d6cf2a4328fea5ea3658a75b76a2937e2ce3e8247d47ae`.
Alle anderen Pakete, Profile und Sicherheitsparameter bleiben auf Stufe 1.

Der bestehende M3/U-Gesamtprozessprüfer wurde um zwei gerätefreie
Frontierfälle erweitert. Im Fortsetzungsfall hält Ziel A eine inhaltlich neue,
aber sichere Kartenrevision und danach eine bytegleiche Karte mit neuem
Zeitstempel ohne Cancel aus. Erst ein belegtes Hindernis am festen Ziel A
bewirkt genau einen bestätigten Nav2-Cancel. Die vorhandene Policy wählt
automatisch das andere Ziel B; B endet erfolgreich und wird erst durch eine
nachfolgende Rohkarte als abgeschlossene Frontieraufgabe bestätigt. Der
Elternauftrag bleibt danach aktiv. Der Fall begrenzt `max_frontier_goals` auf
eins: B könnte nicht starten, wenn `SOURCE_INVALIDATED` dieses Zielbudget
verbrauchen würde. Für A blieben `attempt_count=0` und
`retryable_failure_count=0`. Zwei Kindziele waren nie gleichzeitig aktiv; die
synthetischen Fahrbefehlsthemen blieben bei null Nachrichten.

Ein zweiter Fall entzieht nach sicherem A-Cancel die gültige Kartenquelle.
Es wird kein zweites Kindziel gesendet; die Quelle wird als unfrisch markiert
und der Elternauftrag endet erst am Gesamtzeitbudget als Teilstand. Die
Testfrist für diese absichtlich ausbleibende Quelle ist strenger als die
Produktionsfrist; Produktionsfrische-, Scope-, Footprint- und
Collision-Grenzen wurden nicht verändert. In der ersten Prozessprüfung wurde
außerdem eine unnötige Wiedervergabe desselben *bereits erreichten*
metrischen B-Ziels sichtbar. Der kleine Integrationsfix sperrt nur dieses
identische Ziel, solange sein Frontierabschluss auf eine neue Rohkarte wartet;
ein anders belegtes metrisches Ziel derselben Aufgabe bleibt zulässig.

Die vollständige Explorer-Testsuite bestand mit **893 Tests**. Der erweiterte
Gesamtprozessprüfer bestand aus dem Quellbaum und im Wiederholungslauf auch
gegen den tatsächlich installierten Explorer mit **sechs Szenarien**:
Portal-Erfolg, Portal-Fault, Mehrraum-/Rückweg, Wiederaufnahme, Frontier-Replan
mit Fortschritt und fehlende Folgequelle mit Gesamtbudget. Ein erster
Install-Gesamtlauf hatte im älteren Wiederaufnahmefall einmal einen Timeout
beim Traversal-Status; der isolierte Wiederaufnahmefall und der komplette
erneute Install-Gesamtlauf bestanden. Die Ursache dieser einmaligen
Prüfer-Zeitstreuung ist nicht belegt; sie bleibt als Teststabilitätsrisiko
dokumentiert, nicht als bestandene Wiederholung verschwiegen. Es wurde weder ein
Roboter-Launchprofil gestartet noch ein Gerät geöffnet oder ein echter
Fahrbefehl gesendet. Das lokale Wohnungsprofil und reale Karten/Bags wurden
nicht verwendet; die frühere R9-Nahbereichsbeobachtung bleibt offen.

**Ergebnis Stufe 2:** Die gerätefreie Softwareabnahme ist erfüllt. Der nächste
erlaubte Schritt ist Review des gestapelten Stufe-2-PRs; keine Fahrt und keine
Stufe 3 folgen daraus. Eine reale Fahrt erfordert eine neue ausdrückliche
Freigabe der anwesenden Person und die zuvor dokumentierte physische
Nahbereichs-/Scope-Prüfung.

**Rückfall:** Neue Shell ohne das Stufe-2-Präfix öffnen. Das Stufe-1-Install
und der bisherige Roboterstand bleiben unverändert. Nach Rückfall ist der
erneute Versand eines bereits erreichten identischen Frontierziels wieder als
offener Fehler zu behandeln; für eine spätere Fahrt keine WE-Navigation aus
diesem alten Stand freigeben.

## Stufe 1 – eindeutiger motorloser Laufzeitstand, 2026-09-23

Stufe 1 wurde ausschließlich als Laufzeitinventur und motorloser
Integrationsnachweis ausgeführt. Es gab keine Fahrt, keinen Auftrag an Explorer
oder Nav2, keine Änderung an Footprints, Collision-, Frische- oder
Sensorgrenzen und keine Vorarbeit an einer folgenden Stufe.

### Git-, PR- und Abstammungsstand

Nach `git fetch --prune origin` war `origin/main` bei
`05439c7a13d7a92e69b9eb4663e3a2a1b44626a1`. Die aktuelle gestapelte
WE-Spitze ist PR #96, `fix/we1-target-check-blockers` gegen
`docs/we1-target-check-20260921`, bei
`5e3fe0a084b9b46809e25715d8bdca4c7bd408a4`; sie enthält dessen Basis
`e8b048e59651bcdb37b5c5c19e752dd9b1decace` und den früheren vollständigen
Release-Stand `10e1858074e738df739077aea27078d6bbef7156` als echte Vorfahren.
Der Zielstand liegt 98 Commits vor `origin/main` und nicht auf einer
abweichenden Seitenlinie. Die unmittelbar relevanten offenen PRs sind #94,
#95 und #96 in dieser gestapelten Kette.

Die Prüfung lief auf dem eigenen Branch `fix/we1-stufe1-runtimeinventur`, der
direkt von PR #96 abzweigt und als PR #97 zur Review steht. Die lokal geänderte
Hauptarbeitskopie `/home/p/roboter_ws` blieb auf
`feature/modulare-sensorfusion` bei `00f6e521`
vollständig unangetastet. Ein Commit oder Branchname allein wurde nicht als
Laufzeitnachweis verwendet.

Alle bestätigten funktionalen Korrekturen `bbb5da8`, `5f821b8`, `f74007e`,
`49e8067`, `6f9e8d1`, `ad3a04f`, `28780b1`, `402741d`, `27be777` sowie die
Shutdownkorrektur `5e3fe0a` sind Vorfahren des geprüften Zielstands. Der
Vergleich `10e1858..5e3fe0a` ändert unter `src/` genau die zehn unten
aufgeführten Pakete; genau diese zehn wurden neu gebaut. Damit fehlt keine
seit dem alten Vollrelease geänderte Paketversion im aktiven Overlay.

### Tatsächliche Installations- und Overlaykette

Der isolierte Merge-Install liegt unter
`~/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923/install`.
Die Test-Shell sourcte in dieser Reihenfolge:

1. `/opt/ros/humble/setup.bash`,
2. `/home/p/amadeus_slam_toolbox_ws/install/setup.bash`,
3. `~/.local/share/amadeus/releases/we1-ldlidar-shutdown-overlay/install/local_setup.bash`,
4. `~/.local/share/amadeus/releases/we1-10e1858074e7-r1/install/local_setup.bash`,
5. `~/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923/install/local_setup.bash`.

`ros2 pkg prefix` ordnete alle zehn geänderten Projektpakete dem neuen
Stufe-1-Install zu. Unveränderte Abhängigkeiten wie `robot_interfaces`,
`amadeus_map_identity` und `bt_orchestrator` kamen eindeutig aus dem
Vollrelease `10e1858`. `slam_toolbox` kam aus dem externen, gepatchten Stand
`51a99767`, der STL-27L-Treiber aus dem separaten Overlay mit Vendor-Commit
`bf668a89` und dem bereits dokumentierten Close-after-join-Patch. Ein
Dateivergleich zwischen Quellbaum und Install ergab für sämtliche
Laufzeit-Python-, Launch-, Konfigurations- und Behavior-Dateien der zehn Pakete
keine Abweichung. Nur die bewusst nicht installierte Entwicklerbeispieldatei
`ch34x_dkms.conf.example` hat kein Install-Gegenstück.

| Komponente | Quellbaum / letzter Paketcommit | Tatsächlich verwendeter Präfix | Maßgebliche Konfiguration |
|---|---|---|---|
| `explore` | `5e3fe0a` / `27be777` | Stufe-1-Install | `explore/config/explore_params.yaml` plus lokales WE-Profil |
| `robot_map_manager` | `5e3fe0a` / `5f821b8` | Stufe-1-Install | `robot_map_manager/config/robot_map_manager.yaml` |
| `mission_manager` | `5e3fe0a` / `5e3fe0a` | Stufe-1-Install | `mission_manager/config/mission_catalog.yaml` und `app_mapping.launch.py` |
| `robot_navigation` | `5e3fe0a` / `bbb5da8` | Stufe-1-Install | `robot_navigation/config/nav2_params_real.yaml`, `nav_mapping.launch.py` |
| `safety_monitor` | `5e3fe0a` / `5e3fe0a` | Stufe-1-Install | `safety_monitor/config/safety_monitor_params.yaml` |
| VL53-Nahbereich | `5e3fe0a` / `5e3fe0a` | Stufe-1-Install | `vl53_params.yaml`, `collision_monitor_mapping_params.yaml` |
| LiDAR-Bring-up | `5e3fe0a` / `5e3fe0a` | Stufe-1-Install | `stl27l.yaml`, `slam_toolbox_amadeus.yaml`, `slam_lidar.launch.py` |
| STL-27L-Treiber | Vendor `bf668a89` plus Close-after-join-Patch | `we1-ldlidar-shutdown-overlay` | serieller Port `/dev/amadeus_lidar`, Parameter aus `stl27l.yaml` |
| `base_hardware` | `5e3fe0a` / `5e3fe0a` | Stufe-1-Install | `base_hardware/config/base_hardware_params.yaml`; Start mit `active_drive:=false` |
| gemeinsamer Start | `robot_bringup` bei `5e3fe0a` | Stufe-1-Install | `app_mapping.launch.py`, OAK und Web-GUI für diese Prüfung aus |

Verwendet wurde ausschließlich das lokale Profil
`~/.local/share/amadeus/profiles/we1-two-rooms-hall-r9-20260922.yaml` mit
SHA-256 `e03495cebfc22dc7d9858cb8893660b83134cf4b6121db64ee49673d0688083f`.
Seine reale Geometrie bleibt außerhalb des Repositorys. Das Profil war als
WE-Profil aktiv, erzeugte im motorlosen Lauf aber keinen Auftrag. Die DDS-
Prüfung lief in Domain 217 ausschließlich über die lokale Loopback-
CycloneDDS-Konfiguration des Vollreleases.

Der historische R9-Pfad `we1-r8-scope-overlay` ist ausdrücklich **nicht** der
neue Teststand: Er war ein nicht commitmanifestierter Neun-Paket-Mischstand,
ließ `robot_navigation` aus dem älteren Vollrelease auflösen und enthielt vor
dem damaligen Nachbau den Kartenmanager-Fix `5f821b8` nicht. Genau diese
Mehrdeutigkeit ist mit dem neuen Zehn-Paket-Overlay beseitigt.

### Motorlose Abnahme

Der Build der zehn geänderten Pakete bestand. `colcon test` registrierte in
den Paketen mit registrierten Tests **1.002 bestandene Tests**; der direkte
gemeinsame Pytest-Lauf über die vorhandenen Testverzeichnisse bestand mit
**1.155 Tests**. Die abweichenden Zahlen überlappen und werden nicht addiert.

Zwei vollständige Starts von `app_mapping.launch.py` mit
`active_drive:=false`, aktiviertem WE-Profil und realen Sensoren ergaben
reproduzierbar:

- `collision_monitor`, Controller, Planner, Behavior Server, BT Navigator und
  Velocity Smoother jeweils Lifecycle `active`;
- vollständige TF-Ketten `map -> base_link`, `odom -> base_link`,
  `base_link -> laser_frame` und beide VL53-Frames;
- normierten LiDAR mit etwa 10 Hz, Rohkarte mit etwa 1 Hz und gültigem
  Kartenmanagerstatus `ok=true`, Kartenalter praktisch null, Pose verfügbar;
- beide VL53 mit etwa 3,6 bis 3,9 Hz; in der unbewegten freien Prüfsituation
  publizierten beide frische, leere Punktwolken;
- Safety frisch und durchgehend `false`, Explorer `idle`, Backend bereit,
  Rohkartenquelle bereit und ohne veraltete Quellen;
- `base_hardware` durchgehend `dry_run=true`, `allow_rs485=false`,
  `rs485_ready=false`, Sollgeschwindigkeit und beide Motor-Sollwerte null;
- in 15 s beziehungsweise 10 s Beobachtung null aktive Nav2-Ziele und auf
  allen beobachteten Fahrkanälen null nichtnullige Befehle.

Beide Gesamtstarts wurden jeweils mit genau einem SIGINT an den Elternprozess
beendet. Sämtliche Kindprozesse endeten sauber; danach waren LiDAR, RS485 und
beide sichtbaren I²C-Gerätepfade ohne Handle. Die vollständigen Zykluslogs
enthalten weder Traceback, Prozessabbruch, SIGABRT noch Fehlermeldung. Zwei
vorherige, nicht als Abnahme gezählte Vorläufe scheiterten noch vor der
Node-Laufzeit an doppelter Loopback-Auswahl beziehungsweise einer für
CycloneDDS zu hohen Domain-ID; beide Ursachen sind bestimmt, danach waren alle
Handles frei, und die korrigierten Wiederholungen in Domain 217 bestanden.

Die wiederholten Warnungen zu absichtlich nicht freigegebener Semantik und zum
fehlenden softwareseitigen GPIO-Not-Aus sind bekannte Zustandsmeldungen; sie
wurden nicht durch Abschwächung einer Grenze beseitigt. Die hardwired
Not-Aus-Kette bleibt vor jeder späteren Fahrt Pflicht. Der frühere physische
R9-Nahbereichsbefund bleibt ebenfalls für jede spätere Bewegung offen, ist
aber kein fehlender Laufzeit- oder Frischenachweis dieser motorlosen Stufe.

**Ergebnis Stufe 1:** Der geplante Stand ist eindeutig, alle geänderten Pakete
sind ihrem tatsächlichen Install zugeordnet, sämtliche bestätigten Fixes sind
aktiv, und der Stack startet und stoppt zweimal reproduzierbar ohne
Fahrwirkung. Der nächste erlaubte Schritt ist ausschließlich Review dieses
Themenbranches/PRs. Keine Stufe 2 und keine Fahrt wurden begonnen.

## R9 – Live-Quellenkette, sicherer Replan und Nahbereichsstop, 2026-09-22

Die Prüfung erfolgte in der isolierten Arbeitskopie
`fix/we1-target-check-blockers`, ausgehend von PR #95 / `10e1858074e7` und den
gestapelten WE-Korrekturen bis `be7de12`. Der Produktionslauf verwendete nur
das lokale Overlay unter `~/.local/share/amadeus/releases/we1-r8-scope-overlay`
über dem unveränderten Release `we1-10e1858074e7-r1`; reales Kartenmaterial,
das lokale Zwei-Zimmer-/Flurprofil und der Bag bleiben außerhalb des
Repositorys.

Der erste R9-Vorlauf hielt korrekt bei `we_waiting_for_goal`: Im zunächst
verwendeten Overlay fehlte der bereits im Quellstand vorhandene
Kartenmanager-Fix `5f821b8`, der bei gleicher Geometrie die letzte frische
Rohkartenbeobachtung erhält. Nach dem isolierten Build dieses Pakets bestanden
seine direkten Kernprüfungen (53 Fälle). Der laufende Kartenmanager meldete
anschließend frische `map_observed`-Ereignisse, und der Regionsgraph korrelierte
46 Rohkartenbeobachtungen (`matched`) mit Quelle, Portalgedächtnis und Graph.
Das ist ein Befund zur lokalen Release-Zusammensetzung, keine Änderung an
Karten-, Portal- oder Sicherheitsverträgen.

Nach aktivem Lifecycle-, TF-/Quellen-, Safety-, Encoder- und Bus-Preflight
wurde genau ein produktiver Erkundungsauftrag über den Missionsmanager
gesendet. Der verpflichtende Rundblick lief zunächst ohne Translation. Danach
bildete die Produktionskette Frontieraufgaben und wählte nacheinander mehrere
Ziele; die wachsende Rohkarte löste dabei revisionsgebundene Zielstopps aus.
Ein echter retrybarer Nav2-Abbruch wurde als solcher gezählt. Für die sicheren
Quellenstopps bestätigte das Kindziel dagegen `SOURCE_INVALIDATED` mit der
Action-Rückmeldung `canceled`. Der Elternlauf behandelte dieses `canceled`
bisher fälschlich als generischen Systemfehler statt auf eine frisch belegte
Auswahl zu warten.

Die eng begrenzte Korrektur behandelt ausschließlich diesen bestätigten Pfad:
`SOURCE_INVALIDATED` veröffentlicht `we_replanning_after_source_invalidation`,
wartet die vorhandene Replan-Periode ab und verbraucht weder Zielbudget noch
einen Nav2-Fehlversuch. Danach ist weiterhin ausschließlich ein neu gegen die
aktuelle Rohkarte belegter Kandidat zulässig. Der neue Vertragsfall sowie die
vollständige Explorer-Suite bestanden mit **892 Tests**; das geänderte
`explore`-Paket wurde im selben isolierten Overlay gebaut. Footprint,
Frische-, Scope-, Collision-Monitor- und Safety-Schwellen wurden nicht
verändert. Der Rückfall ist die vollständige Rücknahme dieses kleinen Commits;
dann gilt wieder der dokumentierte Abbruchfehler und der Stand ist nicht als
fahrender Kandidat zu verwenden.

Der R9-Lauf ist trotzdem **kein erfolgreicher Wohnungsabschluss**: Zum Ende
meldete der linke VL53-Nahbereich dauerhaft ein reales Objekt oder eine reale
Begrenzung in etwa 0,236–0,243 m. Not-Aus war frei; Encoderfeedback und Modbus
blieben fehlerfrei. Nach dem gezielten Einzel-PID-Stopp wurden Sollgeschwindigkeiten
null, der Bag sauber geschlossen und weder `/dev/ttyUSB_BASE` noch
`/dev/amadeus_lidar` offen gehalten. Der lokale Nachweis liegt unter
`~/.local/share/amadeus/bags/we1-real-two-rooms-hall-r9-retry-20260922`.
Die Beobachtung wird nicht durch Kartenlogik, eine Scope-Ausweitung oder
gelockerte Kollisionsgrenzen überstimmt.

**Nächster abgegrenzter Schritt:** Eine anwesende Person muss den linken
Nahbereich an der Endpose sichtbar prüfen und die Begrenzung beseitigen oder
den unbestromten Roboter in eine nachweislich freie, vermessene Ausgangspose
setzen. Danach: frischer vollständiger Preflight, neue gültige Quellen und ein
neuer ausdrücklicher Missionsauftrag. Erst dann darf der reale Mehrraumlauf
mit diesem Replan-Fix wiederholt werden. Es gibt daraus weder eine
Hardwareabnahme noch eine Freigabe für eine automatische Fortsetzung.

## R7 – Scope-Gate vor weiterer realer Erkundung, 2026-09-22

Der reale, auf `402741d` getestete R7-Lauf begann erst nach vollständigem
Preflight mit genau einem ausdrücklichen Erkundungsauftrag. Der neue
odometrisch überwachte Rundblick lief ohne Translation; Safety, Encoder und
Modbus blieben dabei unauffällig. Die Frontierzuführung blieb bis zu dessen
Erfolg geschlossen. Danach wurde ein reines Nahziel als erreichter
Beobachtungspunkt bewertet und erst durch eine neuere Rohkarte als
informationsaufgelöst abgeschlossen. Das ist kein Fahrfortschritt in einen
weiteren Bereich.

Die anschließende exakte Statusbewertung hatte 15 offene Frontieraufgaben. Für
14 aktuelle Aufgaben gab es im vorhandenen Profil keine sichere Rohkartenroute;
eine weitere war auf der aktuellen Revision nicht beobachtet. Die offline aus
dem lokalen R7-Bag reproduzierte Bewertung mit unveränderten realen
Clearance-Werten fand ohne Scope fünf grundsätzlich erreichbare Aufgaben, im
lokal bestätigten Scope jedoch keine. Damit ist weder eine gelockerte
Clearance noch eine aus dem Kartenfreiraum geschätzte Scope-Erweiterung
zulässig. Der Scope ist nach seinem dokumentierten Zweck nur für Startraum,
bekannte Tür und den ersten Flurabschnitt vermessen; er ist kein Nachweis für
den nun gewünschten Zwei-Zimmer-/Flur-Umfang.

Die Mission wurde über den Missionsmanager abgebrochen. Vor dem Stopp waren
Soll- und Messgeschwindigkeiten null, der Not-Aus frei sowie Encoder und Bus
fehlerfrei; danach hielten kein Amadeus-Prozess und kein Nutzer `/dev/ttyUSB_BASE`
offen. Die mit einer Terminal-Unterbrechung beendete Prozessgruppe ist
ausdrücklich kein Ersatz für den vorgeschriebenen Einzel-PID-Shutdownnachweis
und wird nicht als sauberer Shutdowntest gewertet. Reale Karte, Scope-Geometrie,
Bag und Diagnosebilder bleiben ausschließlich lokal.

**Nächster blockierter Schritt:** Vor einer weiteren Fahrt muss eine anwesende
Person den zuvor rechts vor der Front beobachteten Nahbereich als frei
bestätigen (oder Amadeus auf die markierte Ausgangspose zurücksetzen) **und**
einen vor Ort vermessenen, zusammenhängenden lokalen Scope für exakt die zwei
Zimmer und den Flur bestätigen. Treppen, Außenbereiche und alle übrigen
Flächen müssen darin weiterhin ausgeschlossen sein. Erst dann darf dieser
Scope mit unveränderten Footprint-, Frische- und Safetywerten motorlos geprüft
und mit neuem ausdrücklichen Auftrag verwendet werden. Die Software darf
diese physische Grenze nicht selbst erweitern.

## Fortgesetzter freigegebener WE-Realversuch, 2026-09-21

Nach der bestaetigten Freigabe fuer zwei Zimmer und den Flur wurde der zuletzt
belegte Softwareblocker eng begrenzt bearbeitet. Die Produktionskette prueft
jetzt vor dem Versand zusaetzlich, ob ein Frontierziel auf der aktuellen
Nav2-Costmap erreichbar ist. Ein dort nur projizierbares Zwischenziel muss
anschliessend erneut auf derselben Rohkarte, im freigegebenen Scope und mit dem
unveraenderten realen Abstand belegt sein. Waehrend ein Kindziel laeuft, wird
seine feste metrische Position auf jeder Rohkartenrevision vor der teureren
Gesamtbewertung separat mit demselben fail-closed Vertrag revalidiert. Dadurch
kann eine gueltige Fahrt nicht mehr allein wegen der Rechenzeit der
Frontier-Gesamtbewertung in die fruehere feste Cancel-/Retry-Schleife geraten.
Frische-, Scope-, Hindernis- und Sicherheitsgrenzen wurden nicht gelockert.

Der isolierte Explorer-Test bestand danach mit **886 Tests**. Im motorlosen
Produktionslauf blieb ein Kindziel nach zwei fruehen, durch die noch wachsende
Karte veranlassten Neuwahlen ueber 87 Sekunden und viele Kartenrevisionen
stabil; `base_hardware` blieb dabei `dry_run=true`, `allow_rs485=false`. Erst
danach wurde ein neuer scharfer Stack gestartet. Vor dem Auftrag waren RS485
und Encoder bereit, beide gemessenen Motordrehzahlen null, Safety frei, LiDAR
bei etwa 10 Hz und beide VL53 bei etwa 4 Hz. Es wurde genau ein
Erkundungsauftrag gesendet.

Amadeus fuhr encoderbasiert von `(0,0,0)` auf etwa
`(0,487 m, 0,034 m, 0,172 rad)`. Es gab keine Encoder-, Modbus- oder
Safety-Stoerung. Danach stoppte der Regler reproduzierbar mit
`RegulatedPurePursuitController detected collision ahead` und schliesslich
`Controller patience exceeded`. Die Ursache ist kein Karten-/Policy-Race:
Der linke VL53 meldete in allen acht Costmap-Strahlen 0,60 m frei, der rechte
VL53 dagegen eine zusammenhaengende reale Punktreihe 0,12 bis 0,23 m vor dem
Sensor. Im Basisrahmen lag sie etwa 0,40 bis 0,51 m vor der Antriebsachse und
rechts der Mitte. Damit liegt ein moegliches Hindernis nur rund 7 cm vor der
gepaddeten Vorderkante; Nav2 muss die Weiterfahrt und eine Drehung dort
fail-closed verweigern. Die globale Karte oder ein bestandener Pfadplan duerfen
diesen aktuellen Nahbereichsnachweis nicht ueberstimmen.

Der Auftrag wurde bei nachgewiesenem Stillstand abgebrochen. Der Bag
`~/.local/share/amadeus/bags/we1-real-fast-revalidation-20260921-2319`
enthaelt 631,2 s und 123.884 Nachrichten; reale Geometrie bleibt lokal. Danach
wurden Recorder und Gesamtstack sauber beendet. `/dev/ttyUSB_BASE`,
`/dev/amadeus_lidar` und `/dev/i2c-9` sind frei.

**Konkreter Restblocker:** Vor der naechsten Fahrt muss eine anwesende Person
den Gegenstand beziehungsweise die Tuerkante rechts vor dem Roboter sichtbar
pruefen. Ohne Veraenderung der Umgebung ist der sichere Rueckfall, den
unbestromten Roboter auf dem bereits gefahrenen, freien Weg mindestens 0,20 m
zurueckzusetzen und rechts vor der Front mindestens den gepaddeten
Footprint-Abstand wiederherzustellen. Erst nach dieser physischen Bestaetigung
darf derselbe begrenzte Auftrag neu gestartet werden. Eine kleinere Footprint-,
Inflations- oder Kollisionsgrenze ist ausdrücklich **kein** zulaessiger
Software-Fix.

## Erster freigegebener WE-Realversuch, 2026-09-21

Christopher bestätigte vor Ort erreichbaren Not-Aus, freie bekannte Türen und
den befahrbaren Umfang aus zwei Zimmern und Flur; Treppen, Außenbereiche,
Personen und Tiere waren ausgeschlossen. Der aktive Versuch verwendete nur das
lokale Profil und den isolierten WE-Installationsstand. Er bewegte Amadeus etwa
0,466 m, ohne Safety-, Encoder- oder Busfehler. Alle beobachteten Fahrkanäle
waren beim Ende null, der Bag wurde geschlossen und der Gesamtstart anschließend
mit genau einem SIGINT sauber beendet; `/dev/ttyUSB_BASE` war danach frei.

Der Versuch ist **kein erfolgreicher WE-M4-/WE-M6-Abschluss**. Während sich die
reale Karte entwickelte, ersetzte die Zielbildung denselben Frontierpunkt durch
jeweils neu bevorzugte Punkte. Die revisionssichere Quellenprüfung stornierte
dadurch jedes aktive Kindziel; nach zwölf solchen Sicherheits-Replans endete der
Elternauftrag mit dem belegten Teilstand statt natürlich. Der lokale Bag liegt
unter `~/.local/share/amadeus/bags/we1-real-full-20260921-2101`; reale Geometrie
bleibt außerhalb des Repositorys.

Die eng begrenzte Korrektur hält das einmal gesendete Frontierziel fest und
validiert es auf jeder neueren, exakt korrelierten Rohkarte erneut gegen
Kartenidentität, Pose, Hindernisabstand, freigegebenen Scope und geodätische
Erreichbarkeit. Nur ein weiterhin sicheres Ziel läuft weiter; ein blockiertes,
unerreichbares oder aus dem Scope gefallenes Ziel wird weiterhin fail-closed
storniert. Solche Quellen-Replans verbrauchen nicht mehr das endliche
Nav2-Ergebnisbudget; der Gesamt-Timeout begrenzt sie weiterhin. Der motorlose
Produktionslauf hielt dasselbe aktive Ziel von Kartenrevision 55 bis 119 bei
jeweils aktuellem Nachweis. Dabei blieben Basis im Dry-run, RS485 gesperrt und
alle Fahrbefehle null.

Vor einer zweiten Fahrt wurde aus der tatsächlich aufgezeichneten Endpose ein
neues lokales Profil abgeleitet. Der anschließende motorlose Exaktkartentest
fand ohne Scope sechs erreichbare Frontiers, innerhalb des freigegebenen
Polygons jedoch **null**. Zwei Frontierpunkte lagen zwar geometrisch im Polygon,
ihre sicher aufgeweitete Route war darin aber nicht mit der Roboterzelle
verbunden. Deshalb wurde beim zweiten aktiven Vorlauf trotz frischer Sensoren,
Odometrie und Safety **kein Auftrag gesendet**; der Start wurde wieder sauber
beendet.

Konkreter Restblocker: Der Roboter muss entweder zur markierten ursprünglichen
Startpose einschließlich Orientierung zurückgestellt werden, oder ein vor Ort
neu vermessener, zusammenhängender Scope muss die sichere Route ab der jetzigen
Pose einschließen und Treppen/Außenbereiche weiterhin nachweislich ausschließen.
Die Software darf diese reale Grenze nicht aus Kartenfreiraum erraten oder
automatisch erweitern. Bis dahin keine weitere Fahrt und keine Hardwareabnahme.

## Motorloser Zielsystemcheck auf dem Jetson, 2026-09-21

**MOTORLOSER WE-1-ZIELSYSTEMCHECK: BESTANDEN.** Daraus folgt ausdrücklich
keine Hardware- oder Fahrfreigabe. Motorstrom und RS485 blieben gesperrt, es
wurde kein Navigations- oder Erkundungsauftrag gesendet und keine Fahrt
ausgelöst.

Geprüfte Basis ist PR #95 bei
`10e1858074e738df739077aea27078d6bbef7156` plus ausschließlich die hier
dokumentierten Footprint-Test- und Shutdownkorrekturen auf
`fix/we1-target-check-blockers`. Die laufende Arbeitskopie
`/home/p/roboter_ws` und ihr Install blieben unverändert. Der vollständige
23-Paket-Build liegt isoliert unter
`~/.local/share/amadeus/releases/we1-target-blockers-20260921/main`; der
gepatchte, weiterhin auf `bf668a89baf722a787dadc442860dcbf33a82f5a`
gepinnte LiDAR-Treiber liegt in einem getrennten Overlay daneben.

### Geschlossene Blocker und Gesamtnachweis

- Der historische Kreis-Vertrag kam nur noch im VL53-Test vor. Der Test prüft
  jetzt wie die seit 18.08. real abgenommene Produktionskonfiguration das
  Polygon über `/local_costmap/published_footprint`; Produktionsparameter und
  Footprint-Architektur wurden nicht geändert. Direkt bestanden **1.206 Tests**,
  registriert **1.016 Tests**, jeweils 0 Fehler, 0 Fehlschläge, 0 Skips.
- Die LiDAR-Ursache war eine konkrete Close-Race im gepinnten Vendor-Treiber:
  der Empfangsthread konnte nach `IsOpened()` noch `FD_SET(-1)` erreichen,
  während `Close()` den Deskriptor vor dem Thread-Join schloss. Der eng
  getrennte Patch initialisiert die beteiligten Atomics und schließt erst nach
  dem Join. VL53 und Basis vermeiden doppeltes `rclpy.shutdown()`;
  Fahrtor und Kartenmanager unterdrücken ausschließlich den von Humble beim
  bereits beendeten Kontext gelieferten `take_message`-`RuntimeError`.
  Echte RuntimeErrors bei gültigem Kontext werden weiter ausgelöst.
- Nach dem diagnostischen Erstlauf wurden zwei weitere vollständige
  Start-/SIGINT-Zyklen mit LiDAR, beiden VL53, SLAM, Nav2, Explorer,
  Kartenmanager, `collision_monitor` und Safety sauber beendet. Alle Prozesse
  meldeten reguläres Ende; kein Buffer-Overflow, SIGABRT, doppeltes Shutdown
  oder Konvertierungs-Traceback trat auf. Danach waren `/dev/ttyUSB_BASE`,
  `/dev/amadeus_lidar` und `/dev/i2c-9` frei.
- Alle Nav2-Lifecycle-Knoten und `collision_monitor` waren aktiv. Der
  Laufzeit-Footprint war exakt `x=-0,13..+0,33 m`, `y=+/-0,25 m`. Gemessen
  wurden 9,9 Hz LiDAR/Normalisierung, je 4,0 Hz VL53, 1,0 Hz Karte, 49,8 Hz
  Odometrie und 99,6 Hz TF mit frischen Stamps. In 30 Sekunden entstanden 0
  Nav2-Ziele und auf allen beobachteten Fahrkanälen 0 Nichtnull-Befehle;
  `base_hardware` blieb `dry_run=true`, `allow_rs485=false`.
- Der reale Kartenmanager speicherte
  `we1_target_recheck_20260921` atomar ohne Durability-Warnung; der Explorer
  schrieb die exakt daran gebundene WE-Revision lokal. Der vorhandene
  Produktionsprozessprüfer bestand erneut `positive`, `fault`, `multiroom`
  und `resume`, einschließlich natürlichem Abschluss und passivem Laden ohne
  Autostart, jeweils mit `command_message_count: 0`.
- Das lokale, nicht versionierte Profil
  `~/.local/share/amadeus/profiles/we1-first-realtest-20260921.yaml` begrenzt
  auf Startraum, bekannte offene Tür und den ersten Flurabschnitt. Sein Scope
  stammt aus dem lokalen HWT-Bag; Chassis-, Footprint-, Portal-, LiDAR- und
  Frischewerte stammen aus den realen Produktionsabnahmen. Der vorgesehene
  Umfang endet vor späteren Flurabschnitten und nimmt Treppen, Außen- und
  sonstige nicht bestätigte Flächen nicht auf. Bis Christopher diesen
  Ausschluss vor Ort bestätigt, bleiben WE-Navigation, Scope-Freigabe und
  Portalmonitor ausdrücklich `false`.

Nächster Schritt ist kein weiterer Softwareumbau, sondern ausschließlich die
persönliche Bestätigung dieses begrenzten Scopes und eine neue Fahrfreigabe.
Rückfall: das isolierte Release und LiDAR-Overlay nicht sourcen beziehungsweise
die eng begrenzten Korrekturen zurücknehmen; kein Live-Install wurde ersetzt.

## 0. Abschlusskorrektur PR95-R1, 2026-09-16

Nach `git fetch origin` war der geprüfte Ausgangshead
`feature/we-transit-return` bei
`b1c44c61c065726fc6d943db985329b988960fa5`, inklusive Funktionscommit
`5e7ba9ea2dca25a0f51676bf78e884f59e966678`, gegen die unmittelbare Basis
`fix/we-release-candidate-review` bei
`05d28f0a2ce5e7a6d100f3b52064d8399955102d`. Die gezielte Korrektur und ihre
Nachweise entstehen ausschließlich im separaten Worktree; die laufende
Roboter-Arbeitskopie blieb unangetastet. PR #95 bleibt offen und wird mit diesem
Commit aktualisiert, nicht gemergt.

### PR95-R1 behoben: Transit nur mit aktuellem Arbeitszweck

Der frühere Gegenbeleg ist erhalten: Mit einer bekannten Tür und zwei jeweils
offenen, aber aktuell nicht beobachteten Frontieraufgaben wählte die damalige
Kette bei Revision 6 B → A, 8 A → B und 10 B → A. Ursache war, dass jede offene
Nicht-Transitaufgabe die nächste Rückfahrt legitimierte, obwohl keine von ihnen
auf der Zielseite konkret ausführbar war.

`TRANSIT` bleibt eine ereignisgebundene Rückkehraufgabe, ist aber jetzt nur
verfügbar, wenn seine vorhandene exakte Portalroute **und** eine frische,
konkrete Aufgabe nach dem Übertritt belegt sind. Die neue Evidenz bewertet vom
exakten Routenendpunkt aus ausschließlich lokale Frontierarbeit oder die
Einstiegsseite der nächsten bestätigten Portalaufgabe. `OPEN` allein, andere
Transitaufgaben und ein Transit als eigener Zweck reichen nicht. Der
Regionsgraph berücksichtigt Portalaufgaben nur auf ihrer tatsächlichen
Einstiegsseite, damit ein Raum → Flur → nächstes Zimmer möglich bleibt, ohne
Transitpendeln zu erzeugen. Nach jeder neuen Rohkartenrevision erfolgt die
vollständige Neubewertung; es gibt keinen Cooldown und keine gelockerte
Frische-, Scope-, Routen- oder Durchfahrtsprüfung.

Die Statusprojektion zeigt für eine wählbare Transitaufgabe die gebundene
Zielaufgabe, deren Region und gegebenenfalls das nächste Portal. Remote
Frontiers können keine direkte Kindnavigation am Portalmonitor vorbei
veranlassen; sie sind ausschließlich Zwecknachweis bis zum tatsächlichen
Übertritt. Dort entscheidet die bestehende Produktionskette erneut anhand
aktueller Quellen. Wird der Zweck ungültig, wird auch der Transit nicht mehr
angeboten beziehungsweise die vorhandene Quellprüfung beendet das Kindziel.

### Durchgeführte Prüfungen

- Der frühere `xfail` ist nun der reguläre Test
  `test_transit_does_not_repeat_direction_without_work_progress`: vier frische
  Revisionen mit weiterhin nicht beobachteter Arbeit wählen keinen Transit und
  ändern die aktuelle Region nicht.
- `test_three_hall_doors_hold_a_blocked_door_and_resume_in_order` bestätigt
  drei bekannte Flurtüren: eine blockierte Tür bleibt sichtbar, aber
  nicht wählbar; die andere wird zuerst gewählt; der Rücktransit erhält erst
  nach frischem Nachweis der verbleibenden Tür einen Zweck und danach wird
  genau diese Tür gewählt. Jede Policyentscheidung besitzt genau eine Absicht.
- Bestehende Tests belegen weiterhin den Rücktransit zu einer aktuellen
  Frontier sowie den Zweck „nächstes bestätigtes Portal“.
- Isolierter Build: `amadeus_map_identity`, `robot_interfaces` und `explore`
  bestanden. `pytest src/explore/test`: **868 bestanden**. Isoliertes
  `colcon test --packages-select explore`: **868 bestanden**.
- Kartenidentität, Kartenmanager, Semantikmanager, Missionsmanager und Explore:
  **1.051 bestanden**. Der Kartenmanager lief dabei aus seinem Quellpfad, weil
  sein Paket-Setup die nicht gebauten Zielsystem-Launch-Abhängigkeiten erwartet;
  das ist kein ersatzweiser Installationsnachweis.
- Der Produktionsprozessprüfer lief in `ROS_DOMAIN_ID=216`,
  `ROS_LOCALHOST_ONLY=1` und ohne `CYCLONEDDS_URI` mit Exit 0. `positive`,
  `fault`, `multiroom` und `resume` bestanden mit jeweils 0 Command-Nachrichten.
  Der Mehrraumfall erreicht Startraum → Flur → Zimmer → Unterbrechung →
  Speichern → Neustart ohne Autostart → frische Pose/Quellen → neuer
  ausdrücklicher Auftrag → derselbe Flur → Frontierabschluss → natürlichen
  Elternabschluss. Portal-/Regions-IDs bleiben erhalten, die Transitaufgabe
  bleibt über den Neustart offen und wird erst nach dem zweckgebundenen
  Rückübertritt abgeschlossen.
- `git diff --check`, `compileall` und `ament_flake8` für alle geänderten
  Dateien außer `explore_node.py` bestehen. Die 34 Befunde in
  `explore_node.py` entsprechen dem bekannten historischen Bestand; keine
  fachfremde Stilbereinigung.

Der Prozessprüfer simuliert Sensoren, Fake-Nav2 sowie den erfolgreichen
Kartenmanager-`save_result`; er schreibt und lädt die WE-Metadaten, aber startet
keinen realen Kartenmanager-Speicherprozess. Das belegt keine Zielsystem- oder
Hardwareabnahme. Es wurden keine Geräte aktiviert, keine Fahrt ausgelöst und
keine reale Wohnungsgeometrie gespeichert.

## 0.1. Historischer Gerätefrei-Check vor PR95-R1

Der Check und die Korrektur liefen ausschließlich im separaten Worktree
`feature/we-transit-return`, ausgehend vom Reviewstand
`05d28f0a2ce5e7a6d100f3b52064d8399955102d` (PR #94, gestapelt auf PR #93).
Die Behebung liegt in `5e7ba9ea2dca25a0f51676bf78e884f59e966678`; die laufende
Roboter-Arbeitskopie blieb unverändert. `git fetch origin` hatte keinen neueren
abgestimmten WE-Stand ergeben. Es gab keinen Merge.

Der bisherige Mehrraumblocker ist behoben. Nach einer bestätigten Durchfahrt
schließt der Regionsgraph nur die offene, zur Zielregion passende Portalaufgabe.
Bleibt in der verlassenen Region echte Arbeit offen, erzeugt er eine einmalige
revisionsgebundene `TRANSIT`-Aufgabe für dieselbe Portal-ID. Die Ankunft über
diese Aufgabe schließt genau sie. Der Ausschluss reiner Transitaufgaben als
Bedarfsgrund verhindert jedoch nicht PR95-R1 bei beidseitig offener Arbeit.
Mehrdeutige Transitzuordnungen werden nicht eindeutig abgeschlossen. Der vorhandene
Portal-Evidenz- und Traversalpfad ist ihr konkreter Verbraucher: `ExploreNode`
akzeptiert sie nur mit frischer Karten-, Scope-, Portal- und Routen-Evidenz.
Eine Aufgabe kann nicht auf der Revision gewählt werden, auf der sie entstand;
ohne eine neuere Quelle bleibt sie gesperrt. Die Statusprojektion verwendet
außerdem die neueste Portal-/Graphrevision, statt einen frisch fortgeschriebenen
Traversalstand fälschlich als veraltet zu melden.

Der vorhandene isolierte ROS-Prozessprüfer bestand in ROS-Domain 215 mit
synthetischer Karte, TF/Scan und Fake-Nav2. Er belegt die Produktionskette
Startraum → Flur → weiteres Zimmer → Unterbrechung → synthetisches Kartenmanager-
Save-Ergebnis und atomarer WE-Save → Neustart → passives Laden ohne Ziel → neue Pose/Quelle → neuer
ausdrücklicher Auftrag → derselbe Flur → Frontierabschluss → natürlicher
erklärter Elternabschluss. Die Rückkehraufgabe wurde automatisch gewählt,
behielt ihre ID über den Neustart und wurde erst durch den vorhandenen
Durchfahrtsmonitor bestätigt. Der Prüfer gab keine Fahrbefehle aus
(`command_message_count: 0`). Der bisherige Positiv-, Fehler- und
Einportal-Wiederanlauffall bestehen ebenfalls.

Der damalige positive Prozessnachweis galt nur für sein Szenario. Die
Korrektur und die zusätzlichen Gegenregressionen in Abschnitt 0 schließen
PR95-R1 gerätefrei; auch das ist weder eine Main-Integration noch ein
Installations-, Zielsystem- oder Hardwareabnahmenachweis.

## 1. Geprüfte Basis und Reviewbefund

Der Auftrag lief ausschließlich im separaten Worktree auf
`feature/we-softwareabschluss`, ausgehend von Dokumentationscommit
`56da2e3d93e2050b6178a2db5f770b746cab3512` und dessen funktionalem M3/U-Elternstand
`047455134894f700a115f6cea422479b99c702f6`. `origin/main` stand nach
`git fetch origin` auf `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1`; der getrennte HWT-Nachweis bleibt
`1d91229dc10ff4bb791938d49aae8e9808a5dfff`. Es wurde nichts gemerged.

Die laufende Roboter-Arbeitskopie `/home/p/roboter_ws` blieb auf
`feature/modulare-sensorfusion` (`00f6e521085b6cb0e38a62a029638d28195a544c`)
mit ihren vorhandenen lokalen Änderungen unangetastet. Ihr `install/` enthält
unter anderem Explorer, Kartenmanager und Semantikmanager, besitzt aber keinen
commitgebundenen Installationsnachweis; daraus wird keine Gleichheit mit diesem
WE-Stand behauptet.

Reviewt wurde die gesamte gestapelte WE-Reihe gegen `origin/main`, nicht nur
PR #92. Die Explorer-, Portal-, Regionsgraph-, Kartenmanager-, Semantik- und
Testverträge wurden reproduziert. Zwei funktionskritische Befunde wurden behoben:

- Eine neue Karte stornierte jedes aktive Ziel allein wegen ihrer Revisionsnummer.
  Jetzt darf nur ein auf der neuen exakten Produktionsquelle identitäts- und
  metrisch gleich bestätigtes Ziel weiterlaufen; geänderte, fehlende oder zu lange
  ungeprüfte Evidenz storniert weiterhin.
- Der natürliche Abschluss war nach bestätigter Durchfahrt durch dauerhaft
  `unknown` bleibende Portalseiten blockiert. Ausschließlich eine vollständig
  validierte Chassisdurchfahrt setzt beide Seiten auf `open`; ein Nav2-Erfolg allein
  reicht weiterhin nicht.

Ein kompletter `--packages-up-to`-Build bleibt auf diesem Review-PC durch die von
`/opt/ros/humble` exportierte, lokal fehlende `behaviortree_cpp`-Bibliothek im
Paket `bt_orchestrator` blockiert. Das ist ein Installations-/Underlaybefund,
kein bestandener oder fehlgeschlagener WE-Pakettest. Das geänderte Paket `explore`
wurde im isolierten Präfix erfolgreich gebaut und getestet.

## 2. Meilensteinstand

| Stufe | Nachgewiesener Stand | Verbleibende Grenze |
|---|---|---|
| WE-D0 / WE-M0/A | Strategie, Basisvergleich und Schnittstellenreview abgeschlossen. | Keine Wiederholung ohne neuen Befund. |
| WE-M0/B | **Stufe 1 grün:** Zielstand `5e3fe0a`, alle zehn seit Vollrelease `10e1858` geänderten Pakete und die tatsächliche Overlaykette sind eindeutig inventarisiert. Build, 1.155 direkte Tests, gemeinsame motorlose Zielsystemlast und zwei wiederholte saubere Gesamtstopps bestanden. | Das ist ein motorloser Zielsystemnachweis, keine Fahr- oder Hardwareabnahme. |
| WE-M1 | Portalgedächtnis und In-Memory-Verträge softwaregeprüft. | Keine Hardwareaussage. |
| WE-M2 | Automatische Rohkarten-, Portal-, Frontier-, Graph- und Aufgabenbildung softwaregeprüft. | Automatische Regionskorrektur bleibt konservativ; reale Karten offen. |
| WE-M3 | Automatische Zielwahl, revisionssichere Kindziele, zweckgebundene Transite und Mehrraum-Rückweg sind gerätefrei geprüft. Der Stufe-3-Folgeauftrag belegt zusätzlich echte Nav2-Umfahrung einer bleibenden Barriere mit automatischem erfolgreichem Folgeauftrag und frische Umweg-Reaktivierung; 917 Explorer-Tests. | Befreiung aus notwendigem Stopp und eindeutige VL53-Messgültigkeit bei leerer Originalwolke fehlen; keine reale Stufe-3-Abnahme. |
| WE-M4 | Der R9-Preflight, Rundblick, die reale Aufgaben-/Zielbildung und sichere Zielstopps sind nachgewiesen. | Aktuell blockiert ein persistenter linker Nahbereichsbefund an der Endpose. Erst physisch klären oder unbestromt auf eine vermessene freie Pose zurücksetzen; keine Mehrraumabnahme. |
| WE-M5 | Versionsgebundener, atomarer WE-Metadatenspeicher und passive Wiederaufnahme über Kartenmanagerstatus sind im Mehrraum-Rückweg geprüft. Auf dem Jetson bestanden echter Kartenmanager-Save, gebundener WE-Save, Falschkartensperre und passives Laden derselben Karte ohne Ziel. | Reale Wiederaufnahme nach Lokalisierung und Portal-/Transit-ID-Nachweis mit echter Mehrraumkarte bleiben offen. |
| WE-M6 | Der vereinbarte gerätefreie Mehrraum-/Unterbrechungs-/Fortsetzungsabschluss besteht einschließlich zweckgebundenem Rücktransit. | Reale Mehrraumkette, Unterbrechung/Wiederaufnahme und wiederholbarer Abschluss bleiben offen; der R9-Lauf endete vor diesem Nachweis sicher am Nahbereichsblocker. |
| WE-M7 | Nicht begonnen; kein Kernblocker. | App-Transparenz/manuelle Benennung später, ohne Geometrie zu überschreiben. |

## 3. Gerätefreie Gesamtnachweise

Der Prozessprüfer startet den produktiven `ExploreNode` in einer isolierten
ROS-Domain mit synthetischer Karte, TF/Scan und Fake-Nav2. Er publiziert auf den
beobachteten Command-Topics keine Befehle.

| Nachweis | Ergebnis |
|---|---|
| Positiver Portalprozess | Ein automatisch gewähltes Nav2-Ziel, bestätigte Durchfahrt, atomarer Region-/Aufgabenfortschritt und **natürlicher erfolgreicher Elternabschluss**, kein Prüfer-Cancel. |
| Fehlendes passendes TF | Kindziel wird storniert; kein Eintritt, Portalaufgabe offen, erklärter Fehlerabschluss. |
| Unterbrechung/Wiederaufnahme | Expliziter Cancel → erfolgreicher Kartenmanager-Save → atomarer WE-Save → Prozessneustart → passives Laden ohne Ziel → neue Pose/Kartenrevision → neuer ausdrücklicher Auftrag → natürliche erfolgreiche Beendigung. Aufgaben-ID bleibt identisch. |
| Mehrraum/Flurrückkehr/Wiederanlauf | Der produktive `ExploreNode` bildet Startraum → Flur → weiteres Zimmer. Danach: expliziter Cancel, atomarer Save, Prozessneustart ohne Autostart, neue Pose/Karte und neuer Auftrag. Die automatisch gewählte erhaltene Transitaufgabe führt durch dieselbe Portal-ID in den Flur zurück; Eintrittszähler 3, Transit- und Frontieraufgabe abgeschlossen, natürlicher Elternabschluss. |
| Frontierkette | Eine sich entwickelnde Rohkarte erzeugt automatisch einen Frontiercluster, stabile Aufgabe, Policyauswahl und metrischen Kandidaten; Fake-Nav2-Erfolg plus neuere vollständige Karte löst die Aufgabe über den Produktionsresolver. |

Die direkte Paketregression und `colcon test` für `explore` bestanden jeweils mit
**868 Tests, 0 Fehlern, 0 Fehlschlägen, 0 Skips**. Der Prozessprüfer bestand mit
`positive`, `fault`, `multiroom` und `resume`; alle vier Szenarien meldeten
`command_message_count: 0`. Die erweiterten reinen Module, Tests und der Prüfer
bestehen `ament_flake8` ohne Befund. Bestehende historische Stilbefunde im großen
`explore_node.py` wurden nicht als fachliche Änderung vermischt.

## 4. WE-M5-Vertrag und Pflichtfälle

WE-Metadaten liegen separat von unveränderlichen Kartenbytes und getrennt von
`semantic_map_manager`-Raumdaten. Jede Revision bindet Kartenname, Version,
Fingerprint, Breite, Höhe, Auflösung und Frame. Nur ein frischer, exakt zur
aktuellen Karte passender Kartenmanagerstatus wird akzeptiert; Speichern verlangt
zusätzlich ein erfolgreiches `save_result`.

Bestanden sind: Save/Load mit identischen Portal-/Regions-/Aufgaben-IDs,
Fingerprint- und Geometriewiderspruch, veralteter Managerstatus, fremde Karte,
beschädigte/abgebrochene Datei, unbekannte Schemaversion, Rückfall auf eine ältere
gültige Revision, idempotentes doppeltes Save-Ereignis, Neustart ohne Pose,
erhaltene blockierte Portalseite und unveränderte manuelle Semantikdatei. Laden
erzeugt weder Absicht noch Navigationsziel. Fortsetzung erfolgt erst mit neuer
gültiger Pose/Quelle und einem neuen ausdrücklichen `ExploreArea`-Auftrag.

## 5. Verbleibende konkrete Blocker und nächste Abnahme

Aktuell maßgeblich ist der Stufe-3-Umfahr-Folgeauftrag oben. Die historischen
Stufe-1/2-Nachweise werden erhalten und nicht erneut vollständig durchlaufen.

1. Den offenen PR #99 reviewen; kein automatischer Merge. Die frühe sichere
   Umfahrung ist softwaregeprüft, der gesonderte Stopp-/Befreiungsfall nicht.
2. Die fehlende positive Messgültigkeit bei leerer VL53-Originalwolke über
   einen expliziten Produzenten-/Verbrauchervertrag schließen. Bis dahin
   keine Recovery auf Grundlage eines Nullpunkts, Heartbeats oder `-1`-Abstands.
3. Vor Hardwarezugriff den wieder aufgetretenen `robot_map_manager`-
   `take_message()`-Shutdown-Race klären. Der aktuelle Auftrag erlaubt keinen
   Gerätezugriff; ein sauberer gerätefreier Nav2-Stopp ersetzt diesen Befund nicht.
4. Für eine spätere reale Abnahme fehlen Messwerte im aktuellen Kartenframe:
   Startposition **und Orientierung**, Barrierenkontur, lichte Breite beider
   Alternativkorridore, freier Footprint-Schwenkbereich und freier Auslauf sowie
   ein daran gebundenes Scope-Polygon mit ausgeschlossenen Gefahrenbereichen.
   Die synthetischen Koordinaten sind keine reale Scope-Freigabe. Erst nach
   geeignetem motorlosem Aufbau und aktueller ausdrücklicher Vor-Ort-Freigabe
   einen begrenzten Auftrag über den Missionsmanager ausführen. Keine Stufe 4.

Automatische Regions-Split-/Merge-Entscheidungen bleiben absichtlich konservativ;
ungeklärte Korrekturen dürfen keinen erfundenen Raumabschluss erzeugen. Manuelle
Raumnamen/-daten bleiben Eigentum des Semantikvertrags und werden durch WE-M5 nie
überschrieben.

## 6. Rückfall und Nachweisgrenze

Rückfall: `wohnungserkundung_persistence_enabled: false` lässt den neuen
Dateipfad vollständig unbenutzt; `wohnungserkundung_navigation_enabled: false`
belässt die WE-Kette passiv. Der R1-Korrekturcommit kann als Ganzes
zurückgenommen werden, ohne Karten- oder Semantikdateien zu löschen; dann gilt
der historische Pendelblocker wieder und der Branch darf nicht als
gerätefreier Releasekandidat bewertet werden. Sichtbare gültige
WE-Zustandsrevisionen werden nicht automatisch rotiert oder überschrieben.

Die Prozessprüfergebnisse sind Softwarebelege mit simulierten Sensoren/Fake-Nav2.
Der erste Realversuch aktivierte den vorhandenen isolierten Stand nach
persönlicher Freigabe und erzeugte ausschließlich den oben beschriebenen
Teilnachweis. Die laufende Roboter-Arbeitskopie wurde nicht gewechselt, ihr
Install nicht ersetzt und keine vollständige Fahr- oder Hardwareabnahme
behauptet.
