# Projektgedächtnis

Fortlaufendes Protokoll getroffener Entscheidungen. Jeder Eintrag nennt die
**beobachtete Evidenz**, nicht nur die Entscheidung. Neue Einträge oben anfügen.

Format:

```text
Datum:
Entscheidung:
Grund / beobachtete Evidenz:
Betroffene Dateien und Hardware:
Teststatus:
Offene Risiken:
Rückfallweg:
```

---

## 2026-08-16 — Globaler Kaltstart und autonome Raumfahrt reproduzierbar abgenommen

**Entscheidung:** Der native Humble-Dienst
`/reinitialize_global_localization` wird im Normalstart nicht mehr aufgerufen.
Stattdessen eroeffnet der `localization_guard` einen eindeutig an Karte,
Generation und 128-Bit-ID gebundenen Vollscan-Zyklus. Zwei separat berechnete
Scans muessen innerhalb 0,20 m und 8 Grad dieselbe Pose liefern; erst dann
setzt `global_scan_localizer` `/initialpose`. AMCL muss diesen Treffer
rueckbestaetigen, bevor das Fahrtor oeffnet. AMCL startet vier Sekunden nach
Karte/Basis/LiDAR, Guard und Matcher nach sieben Sekunden, um den Jetson beim
Lifecycle-Start zu entlasten.

**Grund / beobachtete Evidenz:** Bei einem realen Kaltstart war der AMCL-Dienst
bereits erreichbar, obwohl AMCL intern noch keine Karte verarbeitet hatte.
Der Humble-Callback reicht in diesem Zustand einen Null-Kartenzeiger an
`pf_init_model` weiter; direkt nach dem Dienstaufruf starb AMCL mit
`exit code -11`. Ein weiterer gleichzeitiger Vollstart verlor zudem eine
Fast-DDS-Antwort auf `/amcl/change_state` und liess AMCL inaktiv. Der
kartenfeste Initialpose-Pfad und die zeitliche Staffelung beseitigen beide
beobachteten Startfehler, ohne einen Grenzwert zu lockern.

Drei anschliessende motorlose Kaltstarts an der unveraenderten, vom
Beobachter bestaetigten Pose bestanden. Die Treffer streuten hoechstens
3 cm und 1 Grad; Score `0,9787..0,9789`, Wandtrefferquote
`97,36..97,50 %` und Bestenabstand `1,155..1,168`. Jeder Start benoetigte
genau zwei konsistente Scans, AMCL wurde `active`, `/localization/ready` wurde
`true`, und `base_hardware` blieb `dry_run=true` bei 0 rpm.

Der danach ausdruecklich freigegebene End-to-End-Lauf lokalisierte erneut
motorlos im Stand und fuhr anschliessend das karten- und revisionsgebundene
Ziel `Arbeitszimmer` an. Nav2 meldete `success`, der Missionsmanager
`angekommen`. Der Karten-Endfehler betrug 0,133 m und 6,28 Grad und lag damit
innerhalb der Abnahmegrenzen 0,15 m/0,40 rad. Der Encoderweg betrug 1,024 m;
der Fahrbefehl blieb bei hoechstens 0,100 m/s. Nach dem terminalen Status
wurden wiederholt Soll- und Istgeschwindigkeit sowie beide Motoren mit 0 rpm
bestaetigt. Lokalisierung, Encoder und Modbus blieben fehlerfrei.

**Betroffene Dateien und Hardware:** `robot_navigation` (Startstaffelung,
Guard, Initialisierungsvertrag, Zwei-Scan-Konsens, Tests), STL-27L, Nav2/AMCL
und beide ESS23-RS-Antriebe. Die beiden VL53-Datenstroeme und der aktive
`collision_monitor` wurden vor der Fahrt geprueft, danach auf ausdruecklichen
Wunsch nur fuer diesen beaufsichtigten Lauf zur Laufzeit deaktiviert. Diese
Deaktivierung ist nicht persistent. Echte Karten, Raumgeometrie und
Diagnosebilder bleiben lokal.

**Teststatus:** 30 gezielte Python-Tests, Python-Kompilierung,
`git diff --check`, Colcon-Build und Colcon-Test des Pakets bestanden. Dazu
bestanden drei vollstaendige motorlose Kaltstarts, eine read-only
Nav2-Pfadplanung und die reale semantische Zielfahrt. Vor und nach der Fahrt
gab es genau einen Karten-, Semantik-, Missions-, AMCL- und `cmd_vel`-Pfad;
alle scharfen Knoten wurden anschliessend beendet.

**Offene Risiken:** Die heutige Wiederholung belegt drei Neustarts an einer
extern bestaetigten Position und einen vollstaendigen Ziellauf. Fuer eine
breitere statistische Aussage bleiben weitere deutlich getrennte
Startpositionen und Raumkonfigurationen sinnvoll. VL53 und OAK waren waehrend
des eigentlichen Ziellaufs deaktiviert; Hinderniserkennung ist damit fuer
diesen Lauf nicht abgenommen. Die bekannten Shutdown-Meldungen des
STL-27L-Treibers sowie die doppelte `rclpy.shutdown()`-Exception von
`base_hardware` und `vl53_near_field` bleiben getrennte Aufraeumfehler nach
bestaetigtem Stillstand.

**Rückfallweg:** `nav_localized.launch.py` nicht starten und
`enable_real_go_to_room:=false` verwenden. Dadurch bleiben globale
Lokalisierung und reale semantische Raumfahrt ohne Fahrwirkung. Der alte
AMCL-Globaldienst darf wegen des belegten Null-Kartenfensters nicht wieder in
den automatischen Kaltstart aufgenommen werden.

---

## 2026-08-16 — Selbstsichere AMCL-Fehlpose durch globalen Vollscan-Gate behoben

**Entscheidung:** Eine kleine AMCL-Kovarianz reicht nicht mehr zur ersten
Fahrfreigabe. Der neue `global_scan_localizer` sucht motorlos mit einem
stationaeren Vollscan ueber alle freien Kartenpositionen und Blickrichtungen.
Er bewertet Wandendpunkte und freie Strahlwege und akzeptiert nur einen
absolut guten sowie gegen die zweitbeste getrennte Hypothese eindeutigen
Treffer. Jeder AMCL-Global-Reset erhaelt eine zufaellige 128-Bit-ID. Der
`localization_guard` verlangt einen frischen Treffer fuer exakt
Kartenfingerabdruck, Generation und Reset-ID und prueft anschliessend, dass
AMCL hoechstens 0,30 m/12 Grad von diesem Startwert abweicht. Erst danach
gelten die bisherigen Kovarianz- und TF-Stabilitaetsgrenzen.

**Grund / beobachtete Evidenz:** AMCL meldete nach einer beaufsichtigten
Suchdrehung die Pose `(0,704; 0,379; -123,6 Grad)` mit nur
`0,122/0,123 m` und `9,54 Grad` Standardabweichung. Die vom Beobachter in der
Karte markierte reale Position lag jedoch rund 1,95 m entfernt. Ein
unabhaengiger Scan/Karten-Abgleich widerlegte die scheinbar sichere Pose: nur
39,6 % der Endpunkte lagen innerhalb 15 cm einer Kartenwand, Medianabstand
0,190 m.

Die globale Vollscansuche fand ohne Bewegung konsistent den Bereich
`x=1,245..1,305 m`, `y=-1,135 m`, `yaw=38..39 Grad`. Im ersten Diagnoselauf
erreichte der beste Treffer Score 0,980, 99,17 % Wandtreffer und Faktor 1,283
zur zweitbesten getrennten Hypothese. Drei vollstaendige motorlose Starts
lieferten erneut denselben Bereich. Der finale Kaltstart erreichte Score
0,973, 98,75 % Wandtreffer, Faktor 1,245 und wurde von AMCL bei
`(1,237; -1,147; 39,4 Grad)` bestaetigt. Die unabhaengige Nachpruefung legte
98,27 % der aktuellen Scanpunkte innerhalb 15 cm an Kartenwaende; Median
0,030 m, 90-%-Quantil 0,060 m. Das ist die gemessene A/B-Trennung gegen die
falsche AMCL-Pose, nicht nur eine kleinere Kovarianz.

**Betroffene Dateien und Hardware:** `robot_navigation` (Matcher-Kern,
ROS-Knoten, Launch, Guard und Vertrag), `tools/kartierung` (rein lesende
Diagnose) und STL-27L. Beide ESS23-RS-Antriebe blieben durchgehend im
`dry_run`; keine reale Karte und kein Diagnosebild wird eingecheckt.

**Teststatus:** 22 gezielte `robot_navigation`-Tests, Python-Kompilierung,
`git diff --check` und Colcon-Build bestanden. Der synthetische Test trennt
eine korrekte von einer falschen Pose ueber Wand- und Freistrahlscore. Live
wurden bei drei Neustarts jeweils eine neue Reset-ID, ein Treffer im selben
Positionsbereich, Guard-Verifikation, `ready=true`, `dry_run=true` und
Motorwerte 0 rpm bestaetigt. Ein erwartbarer AMCL-Loghinweis zur wenige
Millisekunden juengeren Initialpose erscheint unmittelbar vor dem dennoch
erfolgreichen `Setting pose`; Rueckdatieren und Nullstempel veraenderten ihn
nicht und wurden deshalb nicht als Scheinloesung uebernommen.

**Offene Risiken:** Die reale Blickrichtung muss noch vom anwesenden
Beobachter bestaetigt werden; die eingezeichnete gruene Pfeilrichtung koennte
auch nur ein Positionszeiger sein. Vorfuehrreife verlangt danach mindestens
zwei weitere motorlose, deutlich getrennte Startpositionen und erst dann eine
beaufsichtigte reale Zielfahrt. Die festen Qualitaetsgrenzen sind mit der
aktuellen Zimmerkarte klar bestanden, aber noch nicht statistisch ueber viele
Raumkonfigurationen validiert. Bei offener Tuer oder starker dynamischer
Verdeckung darf der Matcher korrekt ablehnen; das Fahrtor bleibt dann zu.

**Rückfallweg:** `nav_localized.launch.py` nur motorlos mit
`require_global_scan_match:=false` starten oder auf den vorherigen Commit
zurueckgehen. Eine reale Fahrt ohne den Vollscan-Gate ist nach dem belegten
1,95-m-Fehler nicht freigegeben.

---

## 2026-08-15 — Ursache der nicht wiederholbaren AMCL-Lokalisierung gefunden

**Entscheidung:** Vor jedem LiDAR-/AMCL-Start prueft
`karte_fuer_nav2_pruefen.py` die tatsaechliche Nav2-Trinary-Interpretation von
PGM und YAML. Der Start bricht ab, wenn die von ROS `map_saver` als Grauwert
205 gespeicherten unbekannten Zellen durch den Schwellwert vollstaendig zu
freiem oder belegtem Raum werden. Die echte Karte wurde lokal, verlustfrei
mit `free_thresh: 0.196` neu versioniert; Original und alte Version bleiben
unveraendert. Das semantische Overlay wurde nur wegen identischer
PGM-Geometrie explizit an den neuen Fingerabdruck gebunden.

**Grund / beobachtete Evidenz:** Die bislang verwendete PGM-Datei besitzt
20.543 freie, 3.561 belegte und 29.320 unbekannte Zellen. Ihr altes YAML mit
`free_thresh: 0.25` klassifizierte den Unbekannt-Wert 205 jedoch als frei.
Der live geladene und anschliessend korrekt gespeicherte OccupancyGrid besass
deshalb 49.863 freie Zellen, keine unbekannte Zelle und 44,88 m² scheinbare
Freiflaeche statt 18,49 m². AMCL musste damit in physisch unmoeglichen
Aussenbereichen suchen. Die korrigierte Live-Karte enthaelt wieder exakt
20.543/3.561/29.320 Zellen und den Fingerabdruck
`528a0b020fe89624da1c55925421aecba948a13f6f27f84087725d0ad79c701f`.
Schon im Stillstand sank die globale AMCL-Streuung gegenueber der
verfaelschten Karte von etwa 1,73/2,06 m auf 1,36/1,43 m; eine physische
Beobachtungsfahrt ist fuer die Konvergenz weiterhin erforderlich.

Dabei wurde ein zweiter Vertragsfehler korrigiert: `/amcl_pose` wird im
Stillstand nicht periodisch publiziert. Ein pauschaler Nachrichten-Timeout
haette eine einmal korrekt lokalisierte, stehende Pose wieder gesperrt. Der
Guard verlangt stattdessen eine Pose nach dem kartenbezogenen Global-Reset
und sichert deren Fortbestand ueber den frischen dynamischen `map -> odom`-TF.

**Betroffene Dateien und Hardware:** `tools/kartierung`,
`robot_navigation/localization_guard.py`, STL-27L und lokale Kartenablage.
Keine echte Karte oder semantische Raumgeometrie liegt im Repository.

**Teststatus:** Die Pruefung lehnt die alte reale YAML/PGM-Kombination mit
29.320 verlorenen Zellen ab und akzeptiert die korrigierte Version mit
18,49 m² frei und 26,39 m² unbekannt. Vier synthetische Positiv-/Negativtests
bestehen. Der korrigierte ROS-OccupancyGrid und die neue semantische Bindung
wurden motorlos live bestaetigt.

Der reale End-to-End-Lauf nach freiem Versetzen bestand am selben Tag. Ein
erster Global-Reset mit 360,3 Grad Suchdrehung und 0,243 m begrenzter
Vorwaertsfahrt verbesserte die Streuung auf 0,111/0,152 m und 20,88 Grad. Das
0,35-m-Fahrtorlimit schloss 7 mm vor dem angeforderten Weg. Nach dem deshalb
erforderlichen Stack-Neustart wurde AMCL am veraenderten Standort erneut
global verteilt. Auf 180,2 Grad Beobachtungsdrehung folgten 20 standardisierte
stationaere `/request_nomotion_update`-Messungen; sie trennten die
verbliebenen Winkelhypothesen. Die Freigabe erfolgte bei 0,095/0,118 m und
7,83 Grad Standardabweichung. Die erste
Raumfahrt wurde bei erneut auf 15,69 Grad gestiegener Winkelunsicherheit
korrekt abgebrochen; Fahrtor und Motoren gingen auf null. Nach 20 weiteren
stationaeren Messungen lag AMCL bei 0,019/0,077 m und 4,50 Grad. Der erneute
`go_to_room`-Auftrag meldete `success/angekommen`; Abschlusswerte waren
0,051/0,078 m und 6,08 Grad, korrekter Kartenfingerabdruck und 0 rpm. Die
TF-Zielabweichung betrug rund 0,148 m und 21,7 Grad und lag damit innerhalb
der konfigurierten Nav2-Toleranzen 0,15 m/0,40 rad.

Der Lokalisierungshelfer fordert die stationaeren AMCL-Nachmessungen nun nach
garantiertem Stop selbst an. Dadurch wird nicht die 10-Grad-Grenze gelockert,
sondern es werden im Stillstand weitere LiDAR-Beobachtungen ausgewertet. Die
Einzelschritte sind real belegt; die nun zusammengefuehrte Ein-Aufruf-Variante
bedarf beim naechsten versetzten Start noch eines Wiederholungslaufs.

**Offene Risiken:** Ein realer, frei versetzter End-to-End-Lauf ist bestanden;
mehrere unabhaengige Startpositionen fehlen noch fuer eine statistische
Wiederholbarkeitsaussage. Eine Raumfahrt kann bei voruebergehend steigender
Winkelunsicherheit weiterhin sicher abbrechen und muss erst nach erneuter
Lokalisierungsfreigabe neu beauftragt werden. Die konkrete Schwelle 0.196 gilt
fuer diese map_saver-PGM; andere Karten muessen durch die Pruefung bewertet
und duerfen nicht automatisch umgeschrieben werden.

**Rückfallweg:** Den korrigierten lokalen Kartenstand nicht verwenden und den
Lokalisierungs-Launch motorlos lassen. Das Original ist unveraendert vorhanden;
die Startpruefung kann separat rueckgaengig gemacht werden, ohne Kartendaten
oder Motorparameter anzufassen.

---

## 2026-08-15 — Globale AMCL-Lokalisierung: Sicherheitskette real bewiesen, Wiederholbarkeit noch offen

**Entscheidung:** Reale semantische Raumfahrt wird an eine explizite globale
AMCL-Freigabe gebunden. Der `localization_guard` prueft Kartenfingerabdruck,
Publisher-Eindeutigkeit, eine Pose nach dem Global-Reset, Scan-/TF-Frische,
AMCL-Kovarianz und die Stabilitaet von `map -> odom`. Die erstmalige Freigabe bleibt streng bei
0,20 m Standardabweichung in x/y, 10 Grad in yaw sowie 0,08 m/5 Grad
TF-Bewegung im Drei-Sekunden-Fenster. Nach einer bestaetigten Freigabe gelten
Hysteresen von 0,30 m/15 Grad fuer die Kovarianz und 0,20 m/12 Grad fuer die
TF-Bewegung.

Ein Verlust von `/localization/ready` sperrt das `cmd_vel`-Gate weiterhin
sofort. Nur der irreversible Missionsabbruch hat eine Nachfrist von 0,8 s:
Kurze AMCL-Korrekturen stoppen den Roboter, lassen die laufende Nav2-Action
aber bestehen; anhaltender Verlust bricht sie ab. Die erste Zielannahme hat
keine Nachfrist.

**Grund / beobachtete Evidenz:** Nach freiem Versetzen gelang eine globale
AMCL-Lokalisierung nach einer vollstaendigen Drehung einmal mit
0,118/0,135 m und 8,65 Grad Standardabweichung. Die anschliessende reale
`go_to_room`-Fahrt kam bis auf rund 0,03 m an das semantische Ziel. Eine
0,59 s lange `map -> odom`-Korrektur wurde durch die neue Missionsnachfrist
korrekt ueberstanden. Eine zweite Instabilitaet dauerte 2,20 s; der
Mission Manager brach deshalb wie vorgesehen ab und beide Motoren wurden bei
null bestaetigt. Nav2 selbst meldete dabei keinen Planer- oder Reglerfehler.

Die alte TF-Haltegrenze 0,08 m/5 Grad war fuer normale AMCL-Korrekturen zu
eng. Eine begrenzte langsame Kurvenfahrt mit 0,04 m/s und 0,15 rad/s lieferte
640 TF-Proben; im Drei-Sekunden-Fenster traten maximal 0,1601 m und 8,32 Grad
auf. Daraus wurden die Haltegrenzen 0,20 m/12 Grad mit Messreserve abgeleitet,
waehrend die strengeren Erstfreigabegrenzen unveraendert bleiben.

Nach einem weiteren Neustart und erneutem Versetzen war die globale Pose trotz
vollstaendiger Drehung und begrenzter Suchboegen nicht wieder eindeutig. Der
beste spaetere AMCL-Stand lag unter anderem bei 0,146/0,117 m, aber 11,33 Grad
und bestand den Vertrag absichtlich nicht. Ein Laufzeitversuch mit
2.000 bis 10.000 Partikeln endete bei 0,141/0,113 m und 13,39 Grad; diese
Parameter wurden deshalb nicht uebernommen. Einzelscan-Hypothesen waren wegen
der unvollstaendigen/offenen Karte und Raumsymmetrien mehrdeutig. Eine
zunaechst scheinbar gute Hypothese lag bei korrekter Nav2-Geometrie
(0,40 m Roboterradius) sogar in einer unzulaessigen Zelle. Deshalb wird weder
die 10-Grad-Grenze gelockert noch eine einzelne Scan-Uebereinstimmung als
globale Pose akzeptiert.

**Betroffene Dateien und Hardware:** `robot_navigation` (AMCL-Launch,
Lokalisierungsvertrag und -Guard, Missions-Gate, Realprofil und Starthelfer),
`mission_manager` (Freigabepruefung und 0,8-s-Abbruchnachfrist),
`robot_bringup` (Joystick-Konfliktvermeidung), STL-27L und beide ESS23-RS-
Antriebe. Die echte Karte, semantische Raumdaten, Diagnoserenderings und
Messprotokolle bleiben lokal ausserhalb des Repositories. Die VL53-Zonen und
beide Costmap-Obstacle-Layer wurden auf ausdruecklichen Wunsch nur fuer die
beaufsichtigten Testlaeufe zur Laufzeit deaktiviert; daraus folgt keine
persistente Konfigurationsaenderung.

**Teststatus:** Colcon-Build von `robot_navigation` und `mission_manager`, 60
gemeinsame Tests ohne Fehler, Python-Kompilierung und Whitespacepruefung
bestanden. Der motorlose Preflight bestaetigte `dry_run:true`, gesperrtes
RS485, 0 rpm und die aktiven Acquire-/Maintain-Grenzen. Real bestanden sind
der unmittelbare Gate-Stopp, das Ueberstehen des 0,59-s-Aussetzers, der sichere
Abbruch nach 2,20 s und die lokale Nav2-Annaeherung bis 0,03 m. Nicht bestanden
und damit offen ist eine nach beliebigem Versetzen wiederholbar eindeutige
globale Selbstlokalisierung mit anschliessender vollstaendiger Zielerreichung.

**Offene Risiken:** Die aktuelle Zimmerkarte ist bei offener Tuer und in
symmetrischen Bereichen fuer eine einzelne LiDAR-Beobachtung mehrdeutig.
AMCLs globaler Reset plus einfache Dreh-/Bogensuche garantiert noch keine
Konvergenz zur richtigen Hypothese. Als naechster Schritt ist ein
Mehrbeobachtungs-Initialisierer mit zeitlich getrennter Scanbewertung oder eine
messgestuetzte AMCL-Suchstrategie erforderlich. Vor jeder weiteren Fahrt nach
manuellem Verschieben muss die Pose neu ermittelt werden; eine alte Pose darf
nicht fortgeschrieben werden.

**Rückfallweg:** `nav_localized.launch.py` beziehungsweise den
Lokalisierungshelfer nicht starten und `enable_real_go_to_room:=false`
verwenden. Dann bleibt semantische Raumfahrt ohne reale Fahrwirkung. Fuer den
vorherigen kontrollierten statischen Testbezug kann `nav_real.launch.py` nur
unter den dort dokumentierten engen Testbedingungen verwendet werden; er ist
kein Ersatz fuer globale Lokalisierung.

---

## 2026-08-15 — Reale semantische Raumfahrt fail-closed abgenommen

**Entscheidung:** `go_to_room` darf ein echtes Nav2-Ziel nur nach dem separaten
Opt-in `enable_real_go_to_room:=true` senden. Der Standard bleibt Simulation.
Der reale Pfad verwendet einen Recovery-freien Behavior Tree und diese Kette:

```text
Nav2 -> cmd_vel_mission_gate -> velocity_smoother -> collision_monitor
     -> base_hardware
```

Das Gate gibt nur einen frischen `running`-Status derselben `go_to_room`-
Mission frei. Terminaler, fehlender, veralteter oder ungueltiger Status
erzwingt null. Der Glätter arbeitet `OPEN_LOOP`; die Encoder-Odometrie bleibt
unveraendert die Nav2-Rueckmeldung. Der Fortschrittspruefer verlangt 0,10 m in
20 s.

**Grund / beobachtete Evidenz:** Die Antriebsvorzeichen wurden mit einer
begrenzten Rechtsdrehung isoliert bestaetigt. Der erste Reglerlauf bog trotzdem
ab, weil `CLOSED_LOOP` die bereits vorhandene 2000-ms-Motorrampe ein zweites
Mal nachregelte: Nach drei Sekunden lagen nur 3,5 mm Encoderweg und etwa
0,007 m/s Sollgeschwindigkeit an. `OPEN_LOOP` beseitigte diese Doppelkopplung.

Ein zweiter, sicherheitsrelevanter Befund war Nav2s bisheriger
`default_server_timeout` von 20 ms. Die Unterzielannahme kam real erst nach
rund 590 ms; der Behavior Tree meldete vorher Fehler, waehrend der Controller
das verspaetet angenommene Unterziel weiterfuhr. Der Timeout steht nun auf
2000 ms, und das zusaetzliche Missions-Gate blockiert einen solchen verwaisten
Befehl unabhaengig vom Nav2-Actionzustand. Eine nach erfolgreichem Trockenlauf
absichtlich injizierte Rohgeschwindigkeit bewirkte hinter dem Gate exakt
0,000 m virtuelle Bewegung.

Der erste reale Lauf mit der neuen Kette wurde nach 15 s als festgefahren
abgebrochen: Die sanfte Hardware-Rampe hatte zu diesem Zeitpunkt rund 0,19 m
statt der damals geforderten 0,30 m erreicht. Das war kein Schlupf und kein
Encoderfehler. Mit der daraus gemessenen Schwelle 0,10 m/20 s erreichte der
abschliessende beaufsichtigte Lauf sein semantisches Ziel. Gemessen wurden
1,084 m Encoderweg, maximal 0,14 Grad Abweichung im langen Geradeausabschnitt
und 3,28 Grad beim finalen Einlenken. Roh-, Gate-, Glätter- und Sicherheits-
Ausgang blieben bei hoechstens 0,100 m/s und 0,149 rad/s. Nach dem
Terminalstatus war der maximale verwaiste Rohbefehl 0,000; Gate und beide
Motoren wurden bei null bestaetigt. Beide VL53-Datenstroeme blieben frisch,
Encoder und Modbus meldeten keinen Fehler.

**Betroffene Dateien und Hardware:** `mission_manager` (expliziter Nav2-Pfad,
Recovery-freier Baum, Action-Abbruch), `robot_navigation` (Realprofil,
Missions-Gate, Open-Loop-Glättung, Fortschrittspruefer), beide ESS23-RS-
Antriebe und beide VL53L7CX. Keine Karte, Raumgeometrie oder Zielkoordinate
wurde ins Repository aufgenommen.

**Teststatus:** Colcon-Build von `mission_manager` und `robot_navigation`, 44
gemeinsame Python-Tests, Python-Kompilierung, XML-/YAML-Pruefung und
`git diff --check` bestanden. Gate-Fehlerinjektion bestand fehlenden,
laufenden, terminalen und veralteten Status. Der vollstaendige Trockenlauf und
die verwaiste-Rohbefehl-Injektion bestanden. Der abschliessende reale Lauf
bestand Zielerreichung, Geschwindigkeitsgrenzen, Sensorfrische und gemessenen
Stillstand.

**Offene Risiken:** Dies ist noch keine allgemeine Selbstlokalisierung. Der
abgenommene Lauf verwendete einen bewusst gesetzten statischen `map -> odom`-
Startbezug; nach freiem Versetzen oder Neustart muss die Pose weiterhin
zuverlaessig lokalisiert werden. Der Recovery-freie Baum bricht bei Planungs-
oder Regelfehlern absichtlich ab und umfährt nichts selbstständig. H5 der
Encoder-Odometrie und ein realer VL53-Hindernis-Abbruch waehrend dieser
Raumfahrt bleiben offen. `base_hardware` und `vl53_near_field` melden beim
gemeinsamen SIGINT weiterhin eine bereits bekannte doppelte
`rclpy.shutdown()`-Exception, nachdem der Stillstand erreicht ist; das neue
Gate endet dagegen sauber.

**Rückfallweg:** `enable_real_go_to_room:=false` verwenden oder weglassen;
dann bleibt `go_to_room` ohne Fahrwirkung in der bisherigen Simulation. Den
Real-Launch nicht starten. Motorparameter, Encodergeometrie und semantische
Kartendaten werden durch diesen Rückfall nicht verändert.

---

## 2026-08-14 — Beschleunigungsrampe 2000 ms real abgenommen

**Entscheidung:** `accel_ms` wird von 100 auf **2000** erhöht. Bremsen bleibt
bewusst bei 400 ms, die Startdrehzahl bei 5 rpm. Damit wird normales Anfahren
sanfter, ohne den Bremsweg des Nahbereichs- und Notstopps zu verlängern.

**Grund / Evidenz:** Bei der ersten vollständigen manuellen LiDAR-Runde
wackelte der hohe Aufbau beim Anfahren stark. Die 100-ms-Einstellung war der
Wert, den die Hardware zuvor ohnehin fuhr; sie war ausdrücklich nur der
unveränderte H2/H3-Ausgangspunkt. Beide realen Antriebe akzeptieren und
bestätigen 2000, während 2500 weiterhin mit Modbus Exception 7 abgelehnt wird.
Der Knoten prüft jeden Schreibzugriff und verweigert bei Ablehnung die
Fahrfreigabe.

Ein begrenzter Bodenversuch mit 1,0 s bei 0,12 m/s ergab **0,0439 m** absoluten
Encoderweg und **0,000°** Kursänderung. Der Nutzer bewertete das Anfahren als
„gut sanft“. Das widerlegt die bisherige Dokumentationsannahme, die
Rampenzeit werde gegen 3000 rpm skaliert und wirke bei Kartiergeschwindigkeit
nur rund 0,12 s: Sie wirkt real wesentlich stärker und offenbar weitgehend
direkt auf die Sollwertänderung.

Die anschließende geschlossene manuelle LiDAR-Runde hatte eine offene
Zimmertür und ist deshalb in Fläche und Ausdehnung nicht A/B-vergleichbar. Der
geometrieunabhängigere Wanddickenanteil blieb praktisch gleich (**37,0 % →
36,7 %**); die weichere Rampe verschlechterte die Karte also nicht, ein
messbarer Kartenqualitätsgewinn ist mit diesem einen Lauf aber nicht belegt.
Der Scan-Normalisierer setzte 4467/4467 Scans auf 2160 Strahlen um; keine
Verwerfung wegen wechselnder Strahlenzahl und kein RS485-/Encoderfehler während
der Fahrt. Karte, Posegraph und Laufprotokoll bleiben ausschließlich lokal.

**Betroffene Dateien und Hardware:** `base_hardware_params.yaml`, Defaultwert
im Basis-Node, Vertragsprüfung und Dokumentation; beide ESS23-RS-Antriebe.

**Teststatus:** 60/60 Base-Hardware-Tests, Build, Python-Kompilierung, Flake8
F/E9 und Diff-Check bestanden. Registerprüfung ohne Bewegung, begrenzter
Bodentest und vollständige manuelle Kartenrunde real bestanden. Nach dem
Joystick-Stopp bestätigte der Watchdog fortlaufend 0 rpm. Eine einzelne
Modbus-Fehlermeldung trat erst beim gemeinsamen SIGINT-Herunterfahren auf,
nachdem der Roboter bereits rund eine Minute stillstand.

**Offene Risiken:** Die exakte Rampenfunktion des ESS23-RS ist noch nicht aus
mehreren Impulsdauern identifiziert. Bremsen bleibt absichtlich ruppiger; ein
Komfort-Smoother muss später vor dem `collision_monitor` liegen, damit dessen
Sicherheitsstopp nicht verzögert wird. Ein erneuter externer H4-Laservergleich
war für diese reine Beschleunigungsänderung nicht Teil des Laufs.

**Rückfallweg:** `accel_ms: 100` wiederherstellen und `base_hardware` neu
bauen. Encoderwerte, Geometrie und Bremsrampe sind von diesem Rückfall
unberührt.

---

## 2026-08-14 — DKMS-Aufraeumen: ein "rm" ohne --force haette den Treiber beim naechsten Boot gekillt

**Entscheidung:** Festgehalten als Warnung. Beim Bereinigen der
DKMS-Dopplung entstand kurzzeitig ein Zustand, in dem der Treiber nach dem
naechsten Neustart nicht mehr geladen haette.

**Grund / Evidenz:** `dkms status` meldete
`installed (WARNING! Diff between built and installed module!)` — in
`/lib/modules` lag noch ein handgebautes Modul, DKMS hatte ein eigenes gebaut.
Der Versuch, das mit `rm` der alten Datei plus `dkms install` zu loesen, ging
schief: **DKMS haelt sich laut eigenem Status fuer installiert und ueberspringt
den Einbau.** Ergebnis:

```text
Modul im Speicher : laeuft weiter  -> alles schien in Ordnung
Datei in /lib/modules : FEHLT
modules.dep       : 0 Eintraege
modules.alias     : kein Alias
```

Im laufenden Betrieb war nichts zu merken. Erst ein Neustart haette den
Nahbereichsschutz stillschweigend getoetet — dieselbe Klasse von Fehler, die
den ganzen Tag gekostet hat.

**Behebung:** `dkms uninstall --all` bringt die Buchfuehrung mit der Realitaet
in Einklang, danach installiert `dkms install` wirklich. Ein reines
`dkms install` nach einem `rm` reicht **nicht**.

**Endzustand geprueft:** `installed` ohne Warnung; Modul unter
`/lib/modules/5.15.199-tegra/updates/dkms/` (DKMS-eigenes Verzeichnis, hat
Vorrang); `modules.dep` 1 Eintrag; Alias `usb:v1A86p5512… → ch34x_mphsi_master`
wieder da; installierte Datei identisch mit dem DKMS-Build; Startpruefung
vollstaendig gruen.

**Lehre:** Beim Hantieren an Kernelmodulen sagt der laufende Betrieb **nichts**
ueber die Bootfaehigkeit. Nach jedem Eingriff sind drei Dinge zu pruefen, nicht
nur `lsmod`: die **Datei** in `/lib/modules`, der Eintrag in **`modules.dep`**
und der **Alias** in `modules.alias`. Genau das prueft
`tools/kartierung/nahbereich_pruefen.py` inzwischen mit ab.

**Betroffen:** kein Projektcode.

**Rueckfallweg:** Modul neu bauen ueber
`tools/kartierung/setup_ch34x_treiber.sh`, dann DKMS wie oben.

---

## 2026-08-14 — CH341-Treiberquelle gepinnt und DKMS eingerichtet

**Entscheidung:** Der WCH-Treiber wird wie der STL-27L-Treiber und
`slam_toolbox` als **gepinntes Vendor-Manifest** gefuehrt:
`vendor_ch34x_mphsi.repos`, Commit `f33863f` von
`WCHSoftGroup/ch34x_mphsi_master_linux`. Aufbau ueber
`tools/kartierung/setup_ch34x_treiber.sh`.

**Grund / Evidenz:** Die Quellen lagen unversioniert in `~/`. Waeren sie
verschwunden, haette niemand mehr gewusst, welcher Stand gebaut war — und nach
dem naechsten Kernel-Update waere der Nahbereichsschutz erneut lautlos
ausgefallen. Geprueft: Quellcode gegenueber `f33863f` **unveraendert**, einzige
Ergaenzung ist die `dkms.conf`.

DKMS ist eingerichtet und greift ueber `/etc/kernel/postinst.d/dkms` bei jeder
Kernel-Installation; `AUTOINSTALL="yes"` meldet unser Modul dafuer an. Damit
baut es sich kuenftig selbst neu.

**Betroffen:** `vendor_ch34x_mphsi.repos` (neu),
`tools/kartierung/setup_ch34x_treiber.sh` (neu).

**Teststatus:** Skript erkennt den vorhandenen gepinnten Stand, baut fehlerfrei
gegen 5.15.199-tegra und prueft das `vermagic` gegen den laufenden Kernel. Die
root-Schritte werden bewusst nur ausgegeben, nicht ausgefuehrt.

**Offene Risiken:** `/usr/src/ch34x-mphsi-1.0` ist ein Symlink ins
Home-Verzeichnis. Wird es verschoben, kann DKMS nach einem Kernel-Update nicht
mehr bauen. Das Manifest erlaubt dann aber, den Stand wiederherzustellen.

**Rueckfallweg:** `sudo dkms remove -m ch34x-mphsi -v 1.0 --all`; das Modul fuer
5.15.185 liegt weiterhin unter `/lib/modules/5.15.185-tegra/`.

---

## 2026-08-14 — Startpruefung: der Nahbereichsschutz kann nicht mehr lautlos fehlen

**Entscheidung:** `tools/kartierung/nahbereich_pruefen.py` prueft den
Nahbereichsschutz, und `start_lidar_slam.sh` verweigert den Start mit
`active_drive:=true`, wenn die Pruefung durchfaellt. Bewusst **nicht** in
`base_hardware` eingebaut — dessen Motorcode hat gerade die H0-bis-H4-Abnahme
bestanden, dort kommt jetzt keine neue Abhaengigkeit hinein.

**Grund / Evidenz:** Der Ausfall vom 14.08.2026 war lautlos. `vl53_near_field`
starb beim Start, der `collision_monitor` aktivierte sich trotzdem sauber und
reichte **jeden** Fahrbefehl durch. Kein Fehler beim Booten, keine Warnung —
nur ein Sicherheitssystem, das zur Attrappe geworden war. Aufgefallen ist es
allein, weil zufaellig jemand hinsah.

Die Pruefung prueft vier Dinge, und Punkt 3 ist der entscheidende:

1. Kernelmodul `ch34x_mphsi_master` geladen;
2. CH341-I2C-Bus vorhanden;
3. **beide Punktwolken-Topics veroeffentlichen tatsaechlich** — ein laufender
   Knoten beweist nichts, ein laufender Monitor erst recht nicht;
4. `collision_monitor` laeuft.

**Teststatus:** Alle vier Faelle am Geraet geprueft. Fehlerfall meldet
namentlich, was fehlt, und gibt 1 zurueck. Gutfall gibt 0 zurueck. Der
Startversuch mit `active_drive:=true` bei abgeschaltetem Schutz brach ab, ohne
einen einzigen Knoten zu starten. Ohne `active_drive` greift das Tor nicht —
`dry_run=True, allow_rs485=False` wie zuvor.

**Bewusster Ausweg:** `AMADEUS_OHNE_NAHBEREICH=1` schaltet den Start ohne Schutz
frei — fuer beaufsichtigte Fahrten mit Not-Aus in der Hand, wie sie den ganzen
13. und 14.08. gefahren wurden. Der Weg ist absichtlich umstaendlich und muss
je Aufruf gesetzt werden.

**Was die Pruefung NICHT leistet:** Sie sagt nicht, ob der Monitor auch bremst —
dafuer braucht es ein Hindernis in der Zone. Und leere Wolken sind kein Fehler:
Der Schutz wirkt nur innerhalb von 50 cm.

**Betroffen:** `tools/kartierung/nahbereich_pruefen.py` (neu),
`tools/kartierung/start_lidar_slam.sh`,
`src/vl53_near_field/config/ch34x_dkms.conf.example` (neu). Keine Motoren
bestromt.

**Offene Risiken:** Die Pruefung laeuft beim Start, nicht dauerhaft. Faellt der
Sensor waehrend der Fahrt aus, faengt sie das nicht. Ein laufender Waechter
waere der naechste Schritt.

**Rueckfallweg:** Das Tor greift nur bei `active_drive:=true`; entfernen liesse
es sich durch Loeschen des Blocks in `start_lidar_slam.sh`.

---

## 2026-08-14 — Nahbereichsschutz wieder in Betrieb: Kernel-Update hatte den Treiber verwaist

**Entscheidung:** Das Out-of-Tree-Modul `ch34x_mphsi_master` wurde gegen den
laufenden Kernel neu gebaut und bootfest installiert. Der Nahbereichsschutz ist
wieder nachweislich funktionsfähig.

**Grund / Evidenz:** Am 13.08.2026 war hier notiert, der Schutz sei
„funktionslos" und der WCH-Treiber müsse erst gebaut werden. **Das war eine
Fehldiagnose.** Der Hinweis des Nutzers auf die früheren VL53-Abnahmen
(`1f48b2c`, `6ee8c62`, `6a6b397`) führte zur wahren Ursache:

```text
Modul gebaut fuer : 5.15.185-tegra
laeuft gerade     : 5.15.199-tegra
DKMS              : nicht installiert
```

Ein **Kernel-Update** hat das Modul verwaist. Ohne DKMS wird es nicht neu
gebaut, deshalb lud es seit dem Update nicht mehr. Der Projektcode war nie
kaputt.

Nach `make` gegen die Header von 5.15.199 und `sudo make install`: `i2c-10 —
ch34x-mphsi-i2c` erscheint, der Multiplexer `0x70` antwortet, der Knoten findet
den Bus selbst. Mit einem Objekt in ~20 cm melden **beide Sensoren 64 von 64
Zonen** bei 0,18–0,26 m, `target_status` 5 durchgehend, alle vier Filter
passiert.

**Bremsnachweis ohne Motorstrom** — `collision_monitor` ohne `base_hardware`
betrieben, Fahrbefehl hinein, Ausgang beobachtet:

| Zustand | Ergebnis |
|---|---|
| Objekt in der Zone | **2914 von 2914** auf null gebremst |
| freie Bahn | **133 von 165** unverändert mit 0,100 m/s durchgereicht |

**Drei Fallen, damit sie niemanden erneut kosten:**

1. `z_min`/`z_max` heißen so, sind aber **Distanzgrenzen**. Der Schutz wirkt nur
   innerhalb von 50 cm; „0 Punkte" im freien Raum ist korrekt. Der Boden
   erscheint bei 0,60–0,72 m und wird bewusst weggefiltert.
2. `stop_pub_timeout: 2.0` — nach einem Stopp publiziert der Monitor noch zwei
   Sekunden Nullen und schweigt dann. Ausbleibende Nachrichten heißen „Stopp
   hält an", nicht „Monitor tot".
3. Eigene Diagnosewerkzeuge brauchen zwei Dinge, die der ROS-Knoten schon tut:
   `VL53L5CX_COMMS_CHUNK_SIZE = 32` (sonst `OSError(5)` beim Firmware-Upload,
   der CH341A schafft nur ~32 Byte je Transaktion) und `set_resolution(64)`
   (sonst bleibt der Sensor im 4×4-Modus und nur 16 der 64 Zellen tragen Daten —
   das sah kurz wie ein Projektfehler aus, war aber einer im Prüfwerkzeug).

**Betroffen:** kein Projektcode; `~/ch34x_mphsi_master_linux/driver` neu gebaut
und installiert. Keine Motoren bestromt, keine Bewegung.

**Teststatus:** Treiber geladen, Bus erkannt, beide Sensoren geprüft, Bremsen
und Durchreichen je einzeln nachgewiesen.

**Offene Risiken:** **Ohne DKMS bricht das beim nächsten Kernel-Update erneut.**
Unverändert bestehen die beiden physischen blinden Flecken: maskierter
Mastsektor nach hinten, LiDAR-Scanebene auf 75 cm.

**Rückfallweg:** `sudo make uninstall` im Treiberverzeichnis; das für 5.15.185
gebaute Modul liegt als Sicherung unter
`/tmp/ch34x_mphsi_master_5.15.185.ko.bak`.

---

## 2026-08-14 — Semantische Räume auf Jetson und echtem iPhone abgenommen

**Entscheidung:** Der passive semantische Kartenpfad ist auf dem realen Jetson
und einem physischen iPhone für die nächste Stufe freigegeben. Diese Freigabe
umfasst Kartenanzeige, manuelles Speichern, Raum-Overlay, Revisionen und
Persistenz, aber ausdrücklich keine Raumfahrt.

**Grund / beobachtete Evidenz:** Vor dem Start waren auf dem Jetson keine ROS-,
Motor- oder Navigationsknoten aktiv und der Workspace war sauber. Der Branch
`feature/semantic-map-editor` wurde ohne Überschreiben lokaler Änderungen
übernommen. Der ROS-2-Humble-Build der sechs Pakete `robot_map_manager`,
`semantic_map_manager`, `mission_manager`, `llm_planner`,
`semantic_perception` und `robot_bringup` bestand. Anschließend bestanden alle
**162/162 Python-Vertragstests** auf dem Jetson.

Für den fahrbewegungsfreien End-to-End-Test liefen ausschließlich die statische
`testwohnung`, eine statische TF, `robot_map_manager`, `semantic_map_manager`
und rosbridge. `/cmd_vel` existierte nicht. Die nativ signierte Amadeus-App
wurde auf dem echten iPhone installiert und verband sich über WLAN. Der Nutzer
speicherte die Karte bewusst in der App und zeichnete den Raum `Test` mit vier
Eckpunkten und einem inneren Zielpunkt. Kartenmanager, App und Semantikmanager
verwendeten denselben Fingerabdruck; das Overlay wechselte von Revision 0 auf
1 und erschien im Katalog. Nach einem echten Neustart des Semantikmanagers
wurde Revision 1 aus `~/.local/share/amadeus/semantic_maps/` wiederhergestellt.
Nach Neustart der App verband sie sich ohne erneute URL-Übergabe, womit die
gespeicherte rosbridge-Adresse ebenfalls bestätigt ist.

Die passiven Negativtests wurden anschließend ebenfalls auf dem echten Jetson
ausgeführt. Nach Abschalten von `robot_map_manager` und rosbridge sperrte der
Semantikmanager den unverändert gespeicherten Raum nach mehr als sechs
Sekunden mit `ok:false` und `editable:false`. Nach Wiederanlauf derselben Karte
wurde Revision 1 ohne Datenverlust wieder editierbar. Ein absichtlich mit
`base_revision:0` gesendetes Update gegen Revision 1 wurde als veraltet
abgelehnt; `current.json` blieb auf Revision 1. Ein temporär allein ergänzter
`mission_manager` löste `go_to_room` für `Test` ausschließlich als
`simulation_only_no_navigation` auf. Vor und nach diesem Versuch existierte
kein `/cmd_vel`-Topic.

Der erste Geräte-Start zeigte außerdem, dass der bisherige App-Standard
`roboter.local` im realen WLAN nicht auflösbar war. Der vorhandene Jetson-
Hostname `p-desktop.local` löste dagegen stabil auf und wurde für den Test
einmalig übergeben. Die App verwendet ihn nun als Standard für frische
Installationen; eine bereits vom Nutzer gespeicherte Adresse behält Vorrang.

Beim Neustarttest wurde ein doppelter `rclpy.shutdown()` nach SIGINT sichtbar:
Der Node war bereits beendet, meldete aber fälschlich Exitcode 1. Der Einstieg
fängt `KeyboardInterrupt` nun ab und ruft Shutdown nur bei `rclpy.ok()` auf;
ein Quellvertragstest schützt diesen Pfad.

**Betroffene Dateien und Hardware:**
`semantic_map_manager_node.py`, sein Vertragstest und diese Übergabedokumente;
`RobotController.swift` und das iOS-Gedächtnisprotokoll; Jetson `p-desktop` und
physisches iPhone. Die Testkarte und der Raum liegen nur im lokalen Amadeus-
Datenspeicher und nicht im Repository.

**Teststatus:** Jetson: sechs Pakete gebaut, **162/162 Python-Tests** grün,
ROS-Topics und Persistenz live geprüft. iPhone: Gerätebuild, Installation,
App-/Karten-WebSocket, manuelles Save, Raum-Upsert und App-Neustart bestanden.
Der SIGINT-Fix wurde zusätzlich durch erneuten Build, Test und kontrolliertes
Beenden auf dem Jetson geprüft. Stale-Sperre, Wiederanlauf, veraltete Revision
und simulierte Raumzielauflösung bestanden als reale, fahrbewegungsfreie
Negativtests.

**Offene Risiken:** Getestet wurde bewusst die statische Testkarte, nicht eine
neue reale Wohnungskarte. Ein tatsächlicher Kartenwechsel auf eine andere
Geometrie und der vollständige Editorlauf auf dieser Wohnungskarte bleiben
offen. Rosbridge bleibt im lokalen WLAN unverschlüsselt und unauthentifiziert.
Reale Navigation sowie VL53-/Collision-Schutz sind weiterhin gesperrt.

**Rückfallweg:** Die passiven Testprozesse beenden;
`start_semantic_map_manager:=false` oder `use_dynamic_catalog:=false` setzen.
Die versionierten lokalen Overlay-Dateien nicht löschen; sie sind unabhängig
vom Git-Workspace.

## 2026-08-14 — Manuelle semantische Räume vollständig implementiert

**Entscheidung:** Die erste semantische Ausbaustufe besteht ausschließlich aus
vom Nutzer in der nativen Amadeus-App gezeichneten Räumen. Jeder Raum wird als
Polygon mit ID, Name, Farbe und einem inneren Navigationspunkt gespeichert und
unveränderlich an den SHA-256-Fingerabdruck einer gespeicherten metrischen
Karte gebunden. Gegenstände und automatische Raumsegmentierung bleiben eine
spätere, getrennte Ausbaustufe. `go_to_room` löst den Punkt nur auf und bleibt
hart im Simulationsmodus; es existiert in diesem Stand kein Nav2-/`cmd_vel`-
Pfad für Raumziele.

**Grund / beobachtete Evidenz:** Die vorhandene OccupancyGrid-Karte besitzt
Geometrie, aber keine stabilen Raumnamen. Ein separates Overlay lässt die SLAM-
Karte unverändert und verhindert über Fingerabdruck, Geometrie und Revision,
dass Räume nach einem Kartenwechsel still auf die falsche Wohnung angewendet
werden. App, Backend und Kartenmanager berechnen denselben Fingerabdruck. Ein
Erst-Overlay ist erst nach einem bestätigten manuellen Kartenspeichern erlaubt;
ein vorhandenes Overlay darf bei identischem Fingerabdruck nach Neustart wieder
aktiv werden. Stale Statusdaten, verlorene ACKs, Revisionskonflikte und fremde
Karten sperren Bearbeitung fail-closed.

Während des Cross-Contract-Reviews wurde zusätzlich ein alter Replaypfad im
`robot_map_manager` gefunden: Eine idempotente Wiederholung konnte einen
historischen Vollstatus erneut auf dem globalen Statustopic publizieren. Der
Cache enthält nun nur noch unveränderliche Kommandoergebnisfelder; Karte,
Speicher, Pose, Zeit und Zähler werden bei jedem Replay aus dem aktuellen
Zustand aufgebaut. Dasselbe Prinzip gilt im `semantic_map_manager`.

Das Cross-Contract-Review trennte außerdem manuelle Räume von den bereits
realen Missions-Allowlists: Der dynamische Katalog darf ausschließlich Räume
liefern. Objekte, Ablageziele und `pick_and_place`-Räume bleiben statisch;
ein gezeichnetes Polygon kann deshalb keine reale Behavior-Tree-Mission
freischalten. Semantikstatus müssen `editable:true` sein und verfallen im
Missionsmanager nach sechs monotonic gemessenen Sekunden. Alle JSON-Eingänge
sind gegen Größe, Rekursion und ungültiges Unicode begrenzt.
Da die Prüfung einfacher Polygone Kantenpaare vergleicht, begrenzen Backend,
Mission, App und Mock zusätzlich jeden Raum auf 64 und das Gesamtdokument auf
4.096 Polygonpunkte. So kann ein formal gültiger Extremstatus keine ROS-
Callbackverarbeitung über viele Sekunden blockieren.
Die App verlangt für Save, Overlay, Mutation und ACK zusätzlich einen aktuellen
Kartenmanagerstatus mit `ok:true`; ein Fehlerstatus mit noch passender Summary
kann die Bearbeitung nicht kurzzeitig offenhalten.

**Betroffene Dateien und Hardware:** neues Paket `src/semantic_map_manager/`;
iOS-Raumeditor in `ios/Robotersteuerung/`; read-only Semantikkonsumenten in
`mission_manager` und `llm_planner`; passiver Bring-up-Include; getrennter
Wahrnehmungskatalog; Replay-Härtung im `robot_map_manager`; vollständiger
Vertrag in `docs/SEMANTIC_MAP_INTEGRATION.md`. Keine Hardware wurde bewegt und
keine echten Wohnungsdaten liegen im Repository.

**Teststatus:** Auf dem Entwicklungs-Mac bestanden **162 Python-Vertragstests**
(51 Semantik-Backend, 38 Mission, 15 LLM-Planer, 51 Kartenmanager, 2 Bring-up,
5 zustandsbehafteter rosbridge-Mock) und **39 Swift-Tests**. Mypy, Flake8
`F/E9`, Python-Kompilierung, YAML/XML, fünf isolierte Python-Wheels und
`git diff --check` waren grün. Der vollständige unsigned iOS-Simulator-Build
für arm64/x86_64 bestand mit Swift-/Clang-Warnungen als Fehler; App und Mock
starteten im iPhone-17-Pro-Simulator. Der nachfolgende Jetson-/iPhone-Test ist
im unmittelbar darüberstehenden Eintrag protokolliert.

**Offene Risiken:** Reale Raumfahrt bleibt gesperrt, bis Kartenladen,
Lokalisierung, Costmap-Freiraum, Planbarkeit, Abbruchpfade und insbesondere der
derzeit fehlende VL53-/CH341-Nahbereichsschutz separat bestanden sind. Die
erste Stufe prüft den Zielpunkt geometrisch im Polygon, aber noch nicht gegen
belegte/unbekannte Zellen oder Erreichbarkeit. Polygonüberlappungen sind
erlaubt; Objekte und automatische Segmentierung fehlen bewusst. Rosbridge ist
im aktuellen lokalen Netz weder authentifiziert noch verschlüsselt.

**Rückfallweg:** `start_semantic_map_manager:=false` lässt den passiven Node
beim Bring-up aus. `use_dynamic_catalog:=false` stellt die statischen
Kataloglisten wieder her. Ohne passenden Semantikstatus bleibt der bestehende
Karten-Tab reine Anzeige und sendet keine Raumänderung. Diese Rückfälle
aktivieren keine Fahrt.

## 2026-08-13 — H4 bestanden: der feste Versatz je Fahrt ist weg

**Entscheidung:** Der Encoderpfad (`odometry_source: encoder_position`) bleibt
scharf. Der über Wochen reproduzierte feste Odometrieversatz je Fahrt ist
beseitigt.

**Grund / Evidenz:** Fahrtest mit dem **Lasermessgerät** als externer Referenz,
Positionen auf dem Maßband abgelesen (0,395 → 1,219 → 1,443 → 1,674 → 1,907 m):

| Fahrt | Laser | Odometrie | Abweichung |
|---|---|---|---|
| 1× 0,80 m | 824,0 mm | 825,9 mm | **−1,9 mm** |
| Etappe 1 | 224,0 mm | 223,6 mm | +0,4 mm |
| Etappe 2 | 231,0 mm | 231,7 mm | −0,7 mm |
| Etappe 3 | 233,0 mm | 231,1 mm | +1,9 mm |
| Etappe 4 | 227,0 mm | 226,6 mm | +0,4 mm |
| **4× 0,20 m gesamt** | **915,0 mm** | **913,0 mm** | **+2,0 mm** |

**Das Abnahmekriterium der Übergabe ist damit erfüllt.** Der Zusatzfehler der
drei weiteren Start-Stopp-Vorgänge sank von **+51,9 mm auf +3,9 mm**, also um
92 %. Der Skalenfehler beträgt +0,23 % und die Kursabweichung +0,04° bis
+0,27° — beides unverschlechtert.

**Je Fahrt +0,5 mm statt der bisherigen +17,3 bis +20,1 mm.** Jede einzelne
Fahrt stimmt auf unter 2 mm. Der Skalenfehler beträgt −0,23 % auf 0,824 m, die
Kursabweichung lag bei +0,04° und +0,27° — beides unverschlechtert.

Der Mechanismus ist im Detail sichtbar: Eine kommandierte 0,20-m-Etappe meldet
über den Encoder 0,224 bis 0,233 m, und der Laser bestätigt genau diese Werte.
Der Roboter fährt also tatsächlich weiter als kommandiert, weil er ausrollt —
der Drehzahlpfad verschluckte exakt diesen Weg.

**WICHTIG für künftige Kalibrierungen: Der LiDAR-Wandvergleich taugt dafür
nicht.** Bei Lauf 1 meldete er 0,8025 m gegen 0,8240 m laut Laser, also
**21,5 mm daneben** — bei einer eigenen Streuung von nur 1,7 mm. Über alle
Encoder-Läufe streute er zwischen −23,4 und +5,6 mm, während der Laser
durchweg unter 2 mm blieb. Seine geringe Streuung täuscht eine Genauigkeit vor,
die er nicht hat.

**Betroffene Dateien und Hardware:** keine Codeänderung in diesem Schritt; beide
Motoren, fünf Fahrten von zusammen rund 1,7 m auf dem Boden.

**Teststatus:** H0 bis H4 bestanden. Vier unabhängige Fahrt-für-Fahrt-Vergleiche
gegen das Lasermessgerät.

**Offene Risiken:** Die vier `odom_*_variance`-Werte sind weiterhin konservative
Startwerte; ihre Kalibrierung verlangt laut Übergabe mehr Wiederholungen als
hier gefahren. H5 (Fehler- und Wiederanlaufpfade) steht aus.

**Der Nahbereichsschutz ist derzeit funktionslos.** Der `collision_monitor`
startet und aktiviert sich sauber, aber `vl53_near_field` stirbt beim Start mit
„Kein CH341/CH34x-I2C-Bus gefunden (WCH-Treiber geladen?)". Der USB-Adapter
`1a86:5512` steckt, das Kernelmodul `ch34x` ist nicht geladen. Ein Monitor ohne
Sensordaten reicht alles durch. Für autonomes Fahren muss das zuerst in Ordnung
sein; bei diesem Fahrtest ersetzte die Aufsicht der anwesenden Person ihn.

**Rückfallweg:** `odometry_source: speed` stellt den alten Pfad her — mitsamt
seinem Versatz von rund 18 mm je Fahrt.

---

## 2026-08-13 — H2 und H3 bestanden; Encoderpfad ist scharf

**Entscheidung:** `encoder_counts_per_motor_revolution: 1000.0`,
`encoder_expected_segment: 1000`, `encoder_expected_resolution: 4000`. Der
Encoderpfad ist damit entriegelt und läuft. Zusätzlich `accel_ms: 2500 -> 100`,
weil der Antrieb 2500 zurückweist (siehe unten).

**H2, gemessen am aufgebockten Roboter mit freien Rädern.** Verfahren ohne
Abweichung von der Übergabe: Encoderstand strikt lesend vor und nach einem
befristeten Motorlauf; Lesewerkzeug und `base_hardware` liefen **nie**
gleichzeitig. Bodenreferenz war eine Radmarkierung, vom Nutzer in **beiden**
Richtungen mit genau 5 Radumdrehungen bestätigt.

| Lauf | M1 | M2 | Counts/Motorumdrehung |
|---|---|---|---|
| vorwärts 65,3 s | +50040 | −50045 | 1000,8 / 1000,9 |
| rückwärts 65,3 s | −50009 | +50017 | 1000,2 / 1000,3 |

Richtungsunterschied 0,062 % (M1) und 0,056 % (M2). Ein dritter Lauf über
65,0 s ergab konsistent +49804/−49810. Die Gegenrechnung über die kommandierte
Motordrehzahl (46 rpm) ergab 999,4 bis 999,5 — ein völlig anderer Weg, dasselbe
Ergebnis. Der Wert deckt sich mit `0x0011`, wurde aber **nicht** von dort
übernommen.

**H3, aufgebockt:** `/odom` +0,2442 m bei 8 s × 0,03 m/s (erwartet 0,240) und
dabei nur 0,01° Gierwinkel; rückwärts symmetrisch 0,2443 m; Drehung auf der
Stelle 93,33° bei **0,0001 m** Translation (erwartet 91,7°). Null Fehler, null
verworfene Updates, `/odom` mit 16,7 Hz, Watchdog greift. Vorzeichen und
Montageinvertierung stimmen.

**BEFUND MIT EIGENSTÄNDIGEM GEWICHT — die Anfahrrampe war nie wirksam.** Der
neue Branch verweigerte zunächst jede Fahrt: `Anfahrparameter Motor 1, Reg
0x001E nicht bestaetigt`, danach Dauerreconnect ohne einen einzigen Fahrbefehl.
Ursache: Der Antrieb weist `2500` mit
`ExceptionResponse(function_code=134, exception_code=7)` zurück. Abgetastet
liegt die Obergrenze beider Rampenregister bei **2000**.

Ausgelesen standen in `0x001E` auf beiden Motoren **100** — weder die früher
eingetragenen 800 noch die 2500. `0x001F` (400) und `0x0020` (5) stimmten
dagegen. Schreibzugriffe funktionieren also, nur dieser Wert wurde nie
angenommen.

Sichtbar wurde das erst, weil der Encoder-Branch die **Rückgabewerte** der
Schreibvorgänge prüft. Der vorherige Code rief `_write_register` dreimal ohne
jede Auswertung auf. Das erklärt rückwirkend den Eintrag vom 28.07.2026, die
Solldrehzahl sei „nach ~110 ms zu 90 % erreicht, trotz 800-ms-Rampe" — die
Rampe stand nie auf 800.

Eingetragen sind jetzt 100, also exakt der Wert, den die Hardware ohnehin fährt:
Der Schreibvorgang gelingt, der Knoten startet, das Fahrverhalten ändert sich
nicht. Eine wirklich weichere Rampe wäre mit bis zu 2000 möglich und entspräche
der ursprünglichen Absicht — das ist aber eine echte Verhaltensänderung am
Antrieb und gehört nach AGENTS.md 7 in einen eigenen Schritt.

**Betroffene Dateien und Hardware:** `base_hardware_params.yaml`,
`test_base_hardware_node_contract.py`; ESS23-RS IDs 1/2. Beim Messen drei
Motorläufe zu je 65 s und drei zu je 8 s, Roboter aufgebockt, Räder frei.

**Teststatus:** 59 base_hardware-Tests und 12 Werkzeugtests grün. Der Test
`test_unknown_counts_fail_closed` prüfte wörtlich die Inbetriebnahme-Nullen;
er nagelt jetzt das H2-Ergebnis fest. Die fail-closed-Logik im Node blieb
unverändert — wer wieder 0 einträgt, verriegelt den Pfad erneut.

**Offene Risiken:** Einzelne Räder ließen sich nicht getrennt ansteuern, weil
`cmd_vel` immer beide bedient; H3 deckt diesen Punkt daher nur gemeinsam ab.
Fehler- und Wiederanlaufpfade (H5) wurden nicht provoziert. H4, also die
Bodenfahrt mit A/B gegen die alten 51,9 mm, steht aus. Ob der Encoder
Handschieben erfasst, ist weiterhin unbeantwortet — die Antriebe halten die
Welle auch ohne jeden Master am Bus, ein Handversuch ist damit ausgeschlossen.

**Rückfallweg:** `odometry_source: speed`, oder die drei Encoderwerte wieder
auf 0. `accel_ms` zurück auf 2500 würde den Startfehler erneut auslösen.

---

## 2026-08-13 — Encoder-Fix auf dem Jetson geprüft: Offline-Tests und H1 bestanden

**Entscheidung:** Der Branch `fix/encoder-position-odometry` (`9f7d339`) ist auf
dem Jetson gebaut, offline geprüft und die read-only Registerprobe H1 ist
bestanden. `encoder_counts_per_motor_revolution` bleibt bei `0` — der reale
Positionsmodus ist damit weiterhin verriegelt.

**Grund / Evidenz:** Der geforderte eigene Jetson-Lauf (Mac- und CI-Ergebnisse
zählen dafür ausdrücklich nicht):

- `colcon build --packages-select base_hardware` fehlerfrei;
- 59 base_hardware-Tests bestanden;
- 12 Tests des read-only Inbetriebnahmewerkzeugs bestanden;
- `colcon test-result --verbose`: 59 Tests, 0 Fehler, 0 Fehlschläge.

Die gepinnten Abhängigkeiten waren bereits erfüllt: Pymodbus **3.14.0** und
Pyserial **3.5** sind installiert, exakt wie in `requirements-modbus.txt`
gefordert. Es musste nichts nachinstalliert werden, der laufende Antrieb blieb
also unberührt.

**H0:** keine Amadeus-Knoten aktiv, `/dev/ttyUSB_BASE` von keinem Prozess
gehalten, Arbeitskopie sauber auf `9f7d339`.

**H1, ausschließlich lesend:** Beide Motoren antworten stabil per FC03 mit rund
5 ms je Zugriff. Beidseitig identisch gelesen:

```text
Motor 1: 0x0011=1000, 0x0019=0 (high/low), 0x0101=4000
Motor 2: 0x0011=1000, 0x0019=0 (high/low), 0x0101=4000
```

Ausgangspositionen M1 `+48955`, M2 `−49028`; die gegenläufigen Vorzeichen passen
zur spiegelbildlichen Montage. Über 40 Proben je Motor blieb das Delta **exakt
null** — die Position ist im Stillstand nicht nur „innerhalb erklärbarer
Grenzen" stabil, sondern bitgenau konstant.

**Betroffene Dateien und Hardware:** keine Codeänderung; ESS23-RS IDs 1/2 auf
`/dev/ttyUSB_BASE`, ausschließlich lesend.

**Teststatus:** H0 und H1 bestanden. H2 bis H5 offen.

**Offene Risiken:** `0x0011=1000` und `0x0101=4000` sind exakt die
Handbuchvorgaben. Sie dürfen laut Übergabe **nicht** als Positionseinheit je
Motorumdrehung übernommen werden — das ist genau die Messung, die H2 leistet.

**Praktisches Hindernis für H2:** Die Antriebe halten die Welle mit Moment. Am
13.08.2026 konnte der Nutzer die Räder von Hand nicht drehen, weder nach dem
Stoppbefehl noch bei Solldrehzahl 0. Für eine Handmessung muss der Motor
elektrisch freigegeben werden; ohne Versorgung antwortet er aber nicht mehr auf
Modbus. Wie freigegeben wird, entscheidet laut Übergabe ausdrücklich die
anwesende Person — ein Agent sendet kein Freigabekommando.

**Rückfallweg:** `odometry_source: speed`; für vollständigen Rollback den
Commit `9f7d339` revertieren.

---

## 2026-08-13 — Absolute Encoderposition statt Drehzahlintegration

**Entscheidung:** Die reale Odometrie wird auf die kumulierten ESS-RS-Positionen
`0x000A/0x000B` umgestellt. `0x000C` bleibt Diagnose; bei Lesefehlern wird im
realen Betrieb niemals mehr der Sollwert integriert.

**Grund / Evidenz:** Der reproduzierte feste Fehler betrug 17,3 mm pro
zusätzlichem Stop/Start. 50-Hz-Speed-Polling änderte ihn nicht. Beim Bremsen
meldete `0x000C` zeitweise 0 rpm und später wieder 16 rpm. Die neue Software
erhält jede in `0x000A/0x000B` tatsächlich registrierte Bewegung. Ob diese
Register Handschieben im vorgesehenen Betriebszustand erfassen, ist H2-offen.
Ein einzelner normaler FC03-Fehler behält Client und Baseline; die
Transportfehlerschwelle führt zu Stopp und Reconnect, Ausnahmen/API-Fehler
sofort. Stale Rückmeldung sperrt und stoppt immer, reconnectet aber nur bei
einem zugrunde liegenden Transportfehler.
Ein semantisch ungültiges Paar oder eine Konfigurationsabweichung sperrt und
stoppt dagegen sofort ohne Reconnect. Ein unplausibles Delta wird verworfen und
im Tracker kontrolliert rebased.
Jeder tatsächlich neue Client verwirft die alte Baseline bewusst. Im
Encoderpositionsmodus entsteht `/odom` nur zu einem neuen gültigen Paar
(Ziel etwa 20 Hz), während `state_json` im 50-Hz-Node-Takt weiterläuft.
Der Watchdog nutzt monotone Echtzeit; scharfes RS485 mit `use_sim_time` ist
verboten. `/cmd_vel` hat Queue-Tiefe 1, nicht-endliche Werte fordern Stopp an,
und nur ein nach RPM-Quantisierung darstellbarer Befehl darf starten.

Pymodbus 3.14.0 und Pyserial 3.5 sind in
`src/base_hardware/requirements-modbus.txt` fest gepinnt; interne Modbus-Retries
sind null. Die vier Odometrie-Kovarianzen sind konservative Startwerte und erst
in H4 durch wiederholte externe Referenzmessungen zu kalibrieren.

**Betroffene Dateien/Hardware:** `base_hardware_node.py`,
`encoder_odometry.py`, Parameter, ESS23-RS IDs 1/2 auf `/dev/ttyUSB_BASE`.

**Teststatus:** Auf dem Entwicklungs-Mac bestanden 59
Base-Hardware-Regressionstests und 12 Tests des strikt read-only
Inbetriebnahmewerkzeugs; Syntax geprüft. Keine Motoren aktiviert. Der erneute
Build-/Testlauf auf dem Jetson sowie reale Counts pro Motorumdrehung,
Wortfolge/Vorzeichen und A/B-Fahrt sind offen.
Der Workflow `.github/workflows/encoder-odometry-offline.yml` kompiliert und
testet dieselben Python-Komponenten zusätzlich auf Ubuntu 22.04/Python 3.10;
CI und Mac-Lauf ersetzen die Jetson- und Hardwareabnahme nicht.

**Offene Risiken:** `0x0011` meldet standardmäßig 1000 Unterteilungen,
`0x0101` standardmäßig 4000 Encoder-Counts. Die Einheit der Positionsregister
darf nicht geraten werden. Deshalb blockieren `counts=0` sowie
`encoder_expected_segment=0` oder `encoder_expected_resolution=0` den realen
Positionsmodus. Nach H2 müssen die erwarteten Werte mit den beidseitig
bestätigten read-only Werten aus `0x0011`/`0x0101` verriegelt werden.

**Rückfallweg:** `odometry_source: speed`; auch dort kein Sollwertfallback.
Für vollständigen Code-Rollback diesen Commit revertieren.

---

## 2026-08-12 — Root Cause für fehlende LiDAR-Kartenupdates bei reiner Drehung

**Entscheidung:** Der offizielle `slam_toolbox`-Fix aus PR #808 wird als
minimaler Patch auf einen fest gepinnten Humble-Commit zurückportiert und in
einem separaten Overlay unter `~/amadeus_slam_toolbox_ws` gebaut. Aktiviert wird
er projektspezifisch mit `check_min_dist_and_heading_precisely: true`. Die
apt-Installation unter `/opt/ros/humble` bleibt unverändert.

**Grund / beobachtete Evidenz:** Im selben Lauf veränderte eine 360°-Drehung
**0 von 29.640** Kartenzellen, eine anschließende 40-cm-Translation dagegen
**2.410**. Odometrie/TF drehten korrekt, Mapping-Parameter waren aktiv und
LiDAR, USB sowie Totzonenfilter blieben stabil. Die Humble-Implementierung von
`SlamToolbox::shouldProcessScan()` prüft vor Karto nur
`Pose2::SquaredDistance`, also x/y-Translation. Dadurch erreicht eine reine
Drehung Kartos korrekte Distanz-oder-Winkel-Prüfung nicht. Das entspricht
[Issue #807](https://github.com/SteveMacenski/slam_toolbox/issues/807); der
offizielle Fix wurde in [PR #808](https://github.com/SteveMacenski/slam_toolbox/pull/808)
als Commit `649a50eae698396c40352619c95cd20e2ea1790a` gemergt, fehlt aber im
Humble-Zweig.

**Betroffene Dateien und Hardware:**
`vendor_slam_toolbox_humble.repos`,
`patches/slam_toolbox_humble_pure_rotation.patch`,
`tools/kartierung/build_slam_toolbox_humble_overlay.sh`,
`tools/kartierung/slam_knoten_beobachten.py`,
`tools/kartierung/slam_graph_marker.py`,
`tools/kartierung/test_slam_knoten_beobachten.py`,
`src/amadeus_lidar_bringup/config/slam_toolbox_amadeus.yaml`; Jetson und
STL-27L. Die bestehende Fahrwerkskalibrierung wird nicht verändert.

**Teststatus:** Root Cause durch Quellcode und Messung bestätigt. Backport und
Build-/Stillstandsverfahren sind in `docs/SLAM_TOOLBOX_ROTATION_FIX.md`
dokumentiert. Test am echten Jetson, reine Drehung, Translation und geschlossene
Runde stehen noch aus; keine Aktoren ohne ausdrückliche Freigabe.

**Offene Risiken:** Der LiDAR-Zeitstempel liegt am Ende eines ungefähr 100-ms-
Scans und für diesen Pfad ist kein beamweises Deskew nachgewiesen; schnelle
Drehung kann daher Wände verschmieren, erklärt aber nicht das Null-Update. Im
Odometrie-Drehtest sind Korrekturformel und Korrelationsvorzeichen vor einer
weiteren Kalibrierung für CW und CCW zu verifizieren. Ein synthetischer
Yaw-only-Regressionstest fehlt noch.

**Rückfallweg:** Launch beenden und in einer frischen Shell nur
`/opt/ros/humble/setup.bash` sowie `~/roboter_ws/install/local_setup.bash`
sourcen.
Das separate Overlay wird dadurch ohne Löschung deaktiviert.

---

## 2026-08-13 — Fester Versatz je Fahrt bestätigt, Ursache eingegrenzt

**Entscheidung:** Noch keine. Der Befund wird festgehalten, die Ursache ist
eingegrenzt, aber nicht bewiesen. Es wurde nichts an `base_hardware` geändert.

**Grund / Evidenz:** Der feste Versatz je Fahrt lässt sich **ohne äußeres
Messmittel** nachweisen, indem dieselbe Gesamtstrecke einmal am Stück und
einmal in Etappen gefahren wird — der Skalenanteil ist dann in beiden Fällen
gleich, der feste Anteil fällt einmal beziehungsweise N-mal an:

| | Odometrie | LiDAR | Abweichung |
|---|---|---|---|
| 1× 0,80 m | 0,8019 m | 0,8305 m | +28,6 mm |
| 4× 0,20 m | 0,8215 m | 0,9020 m | +80,5 mm |

Drei zusätzliche Fahrten kosten 51,9 mm, also **17,3 mm je Fahrt**. Die
Wandabstände wurden über 15 Scans gemittelt; ihre Streuung lag bei 1,0 bis
3,4 mm, der Effekt ist also weit außerhalb des Messrauschens.

**Was die Ursache NICHT ist:** Die Odometrie integriert sehr wohl die gemessene
Ist-Drehzahl, nicht den Sollwert — 153 Motor-rpm ergeben rechnerisch
0,09999 m/s, was in der Anzeige als 0,1000 erscheint und einen zunächst in die
Irre führt. Quantisierung (0,65 %) wäre ein Skalenfehler und steckt bereits im
Radradius. Ein reiner Zeitverzug hebt sich über eine Fahrt aus dem Stillstand
mathematisch exakt auf.

**Was auffällt:** Während der Bremsphase ist die Rückmeldung unbrauchbar. Nach
einem Stoppbefehl bei t=3,04 s meldete das Register bei t=3,12 s **null**, bei
t=3,47 s dann wieder **16 rpm** — die Räder drehten also noch. Dazu passt, dass
`feedback_period_s: 0.1` nur 10 Stützstellen je Sekunde liefert, während mit
50 Hz integriert wird; über eine Bremsung bleiben vier Werte.

**Zusätzlicher Codebefund, unabhängig davon:** Schlägt eine Modbus-Leseanfrage
fehl, setzt `_poll_speed_feedback` `feedback_ok = False`, und `_update` fällt
**stillschweigend auf den KOMMANDIERTEN Wert zurück**. Während eines Stopps ist
das Kommando null — ein Lesefehler genau dort lässt die Odometrie also exakt den
Weg verlieren, den der Roboter noch ausrollt, ohne jede Warnung. Das ist
unabhängig vom Hauptbefund ein Mangel.

**Betroffen:** noch nichts geändert. Neue Werkzeuge:
`tools/kartierung/odometrie_versatz_messen.py` und
`tools/kartierung/start_lidar_slam.sh`.

**Teststatus:** Der Versatz ist reproduziert und quantifiziert, die Ursache
nicht bewiesen.

**Nächster Schritt:** `feedback_period_s` von 0.1 auf 0.02 setzen und dieselbe
A/B-Messung wiederholen. Schrumpft der Versatz deutlich, war die Unterabtastung
die Ursache. Dafür muss der Roboter zuvor umgesetzt werden — vor ihm sind nur
noch rund 0,9 m frei, und rückwärts ist er blind.

**Offene Risiken:** Der Versatz wirkt sich bei vielen kurzen Fahrten stärker aus
als bei wenigen langen. Für Nav2 mit häufigen Stopps ist das relevant.

---

## 2026-08-12 — Odometrie neu kalibriert; ein Teil des Fehlers ist kein Radiusfehler

**Entscheidung:** `wheel_radius_m: 0.0624` und `wheel_separation_m: 0.3845`
(vorher 0.0612 / 0.3755). Der verbleibende Fehler von rund 15 mm je Fahrt ist
**kein Kalibrierproblem** und wird nicht über die Radgeometrie ausgeglichen.

**Grund / Evidenz:** Acht Fahrten mit dem Lasermessgerät, jede in Radumdrehung
umgerechnet, weil zwischendurch der Radius verstellt wurde:

```text
echte Strecke = 15 mm + 0.0625 m * Radumdrehung [rad]
                ^^^^^   ^^^^^^^^
                je FAHRT konstant, unabhaengig von der Laenge
```

Ausgleich über alle acht Fahrten (Hebel 5,1 bis 40,4 rad): wirksamer Radius
0,06252 m, fester Versatz 15,1 mm, größte Restabweichung 8,2 mm. Der gesetzte
Wert 0,0624 liegt 0,2 % darunter — unter dem Messrauschen, deshalb belassen.

**Der Weg dorthin ist die eigentliche Lehre.** Aus den ersten vier Fahrten
(alle zwischen 0,41 und 1,01 m) kamen je nach Auswertung Radien zwischen 0,0621
und 0,0631 heraus; eine daraus abgeleitete Vorhersage wurde anschließend
widerlegt. Fester Versatz und Skalenfaktor sind stark korreliert, solange alle
Fahrten ähnlich lang sind. Erst der Hebel aus einer **kurzen und einer langen**
Fahrt (0,30 m gegen 2,50 m) trennt beide: bei 0,30 m macht ein 15-mm-Versatz
5 % aus, bei 2,50 m nur 0,6 %. Zwei unabhängige Auswertungen — der Gesamtausgleich
und der Hebel allein — lagen danach 0,13 % auseinander.

Dass der Versatz **je Fahrt** anfällt, wurde getrennt belegt: zweimal 0,50 m
einzeln gefahren ergab zusammen 1,068 m bei 1,021 m gemeldet, dieselbe Strecke
am Stück nur 1,044 m bei 1,012 m. Vorhergesagt waren 1,072 m für „Versatz je
Fahrt" gegen 1,053 m für „nur einmal". Die abschließende Verifikationsfahrt über
2,00 m sagte 2,021 m voraus, gemessen wurden 2,030 m.

**Historischer Verdacht zum damaligen Messzeitpunkt, nicht bestätigt:** Beim
Anfahren könnten sich die Räder vor einer brauchbaren Ist-Drehzahl-Rückmeldung
drehen. Der spätere 50-Hz-Test widerlegte reine Unterabtastung; der interne
Mechanismus von `0x000C` blieb offen. Der aktuelle, getrennte Encoderpfad steht
im Eintrag vom 13.08.2026 am Dokumentanfang.

**Warum das früher niemand fand:** Eine Winkelmessung bestimmt nur das
Verhältnis r/W, nie die Spurweite allein. Radius und Spurweite waren beide rund
2 % zu klein, aber im fast gleichen Verhältnis — die Drehung stimmte auf 0,4 %,
die Strecke lag 2,5 % daneben. Nur eine Streckenmessung kann das aufdecken.

**Der LiDAR-Wandvergleich taugt nicht als alleinige Referenz.** Bei der
Verifikationsfahrt meldete er 2,006 m gegen 2,030 m per Laser — 24 mm daneben,
bei einer sonstigen Streuung von ±5 mm. Der Roboter endete dort 0,94 m vor der
Wand, deutlich näher als sonst. Für Kalibrierentscheidungen immer das
Lasermessgerät heranziehen.

**Betroffen:** `src/base_hardware/config/base_hardware_params.yaml`. Beim Messen
beide Motoren, acht Fahrten zwischen 0,30 und 2,50 m.

**Teststatus:** Verifikationsfahrt über 2,00 m innerhalb der Ablesegenauigkeit
getroffen. Kursabweichung über alle Fahrten zwischen −0,51° und +0,28°.

**Offene Risiken:** Der feste Versatz von 15 mm je Fahrt bleibt bestehen und
wirkt sich bei vielen kurzen Fahrten stärker aus als bei wenigen langen. Die
wirksame Spurweite liegt 6,5 mm über der abgemessenen — plausibel durch
Aufstandspunkt und Reifenradieren, aber nicht unabhängig bestätigt.

**Rückfallweg:** `wheel_radius_m: 0.0612` und `wheel_separation_m: 0.3755` in
`base_hardware_params.yaml`, dann `colcon build --packages-select base_hardware`.

---

## 2026-08-12 — Winkelfehler war ein Messartefakt; Phase 4a bestanden

**Entscheidung:** Der Winkelfehler der Odometrie wird künftig mit
`tools/kartierung/odometrie_winkel_messen.py` bestimmt, nicht mehr mit
`odometrie_drehtest.py`. Die Kalibrierwerte bleiben unverändert.

**Grund / Evidenz:** Die zuvor über vier Läufe reproduzierten −4,98° bis −6,50°
je Umdrehung waren ein Artefakt des Messverfahrens. `odometrie_drehtest.py`
vergleicht nur Anfangs- und Endscan, liest `/scan` mit schwankender
Strahlenzahl und summiert die Odometrie nicht über die Bremsphase. Der zweite
Punkt wiegt am schwersten: da nur gleich lange Scans vergleichbar sind, blieben
im Versuch **22 von rund 250 Messpunkten** übrig, bei einer Vergleichsgüte von
0,70 m statt 0,03 m — die Verfolgung verlor zwischen den Scans die Spur und
lieferte einen Skalenfaktor von 0,80, also 20 % Fehler. Offensichtlich Unsinn.

Kontinuierlich gemessen auf `/scan_normiert`, je eine volle Umdrehung bei
0,25 rad/s:

| Richtung | Messpunkte | Skalenfaktor | R² |
|---|---|---|---|
| gegen den Uhrzeigersinn | 283 | 0,99628 | 0,9973 |
| im Uhrzeigersinn | 283 | 0,99564 | 0,9974 |

Beide Richtungen stimmen auf 0,00064 überein — das Verhalten eines echten
Skalenfehlers, kein richtungsabhängiger Effekt. **−1,45° je Umdrehung**, also
0,4 %. Der Widerspruch zu den 0,50° aus `9e8c06f` ist damit aufgelöst.

Wichtig für spätere Kalibrierungen: Die Winkelmessung bestimmt nur das
**Verhältnis** von Radradius zu Spurweite, nicht die Spurweite selbst. Der
Streckentest über 0,40 m ergab 0,411 m gemeldet gegen 0,427 m per LiDAR
(+3,9 %). Zusammen mit dem Winkelfaktor folgt daraus eine um 4,3 % größere
Spurweite — nicht die 0,4 %, die der Winkel allein nahelegt. Beide Werte
gehören gemeinsam gesetzt und gemeinsam geprüft.

**Phase 4a bestanden:** 0,40 m Translation erzeugte 20 neue Knoten, die Karte
blieb einwandig, Kursabweichung +0,18°, Nebenachse 3,85 m gegen real 3,80 m.

**Betroffen:** `tools/kartierung/odometrie_winkel_messen.py` (neu),
Dokumentation. Beim Messen beide Motoren, drei volle Umdrehungen und 0,40 m
Fahrt.

**Teststatus:** Zwei Messläufe je Richtung, seitlicher Versatz 0,0–0,1 cm.

**Offene Risiken:** Der Radradius ist ungeprüft; die +3,9 % beruhen auf einer
einzigen LiDAR-Wandmessung und brauchen eine Gegenmessung mit dem
Lasermessgerät. Ein Deskew fehlt weiterhin.

**Nicht gefahren:** die geschlossene Runde aus Phase 4. Es ist kein Joystick
angeschlossen, und weder `collision_monitor` noch Nav2 laufen in dieser
Startdatei. Ohne Hindernisabsicherung und mit einem Sensor, der Schwellen und
Kabel grundsätzlich nicht sieht, wird nicht blind durch die Wohnung gefahren.

**Rückfallweg:** Es wurde nichts an der Kalibrierung geändert; der Stand ist
unverändert fahrbereit.

---

## 2026-08-12 — Duplizierte Wände: Karto verwarf drei Viertel aller Scans

**Entscheidung:** Zwischen Treiber und `slam_toolbox` läuft ab sofort der Knoten
`amadeus_lidar_bringup/scan_vereinheitlichen`. Er setzt jeden Scan auf ein
festes Winkelgitter (2160 Strahlen) um und veröffentlicht ihn als
`/scan_normiert`. Der Launch-Schalter `normalize_scan` steht auf `true`.

**Grund / Evidenz:** Die versetzt duplizierten Wände kamen weder vom fehlenden
Deskew noch vom Odometrie-Winkelfehler — beide Vermutungen waren falsch. Karto
merkt sich die Strahlenzahl des **ersten** verarbeiteten Scans und bricht bei
jedem abweichenden Scan sofort ab: `LaserRangeFinder::Validate` gibt false
zurück, `Mapper::Process` kehrt daraufhin ohne Knoten und ohne Kartenbeitrag
zurück (`lib/karto_sdk/src/Karto.cpp` Zeile 213 ff., `Mapper.cpp` Zeile 2722).
Die Meldung geht auf **stdout**, nicht ins ROS-Log — deshalb war sie so lange
unsichtbar.

Der STL-27L liefert keine feste Strahlenzahl: über 424 Scans am stehenden
Roboter **19 verschiedene Werte zwischen 2145 und 2176**, der häufigste deckt
nur 25,7 % ab. Die Winkel sind dabei korrekt, der Treiber zieht
`angle_increment` mit, sodass `(N-1)·increment` immer 360° ergibt.

Die Rechnung geht auf: etwa 42 winkelgetriggerte Annahmen je Umdrehung mal
25,7 % sind knapp 11 — gemessen wurden 10.

A/B am realen Roboter, identischer Ablauf, nur der Schalter umgelegt:

| | verworfene Scans | neue Knoten | Wand/frei | Nebenachse (real 3,80 m) |
|---|---|---|---|---|
| ohne | 31 | 10 | 0,125 | 5,39 m |
| mit | 0 | 41 | 0,098 | 3,83 m |

**Kennzahlenfalle, die fast zur falschen Entscheidung geführt hätte:** „dicke
Wände" stieg von 3,2 % auf 24,0 % — bei der *besseren* Karte. Die Kennzahl misst
Erosionsüberleben und belohnt dünne Linien. Konsistent aus 41 Richtungen
eingetragene Wände sind bei 3-cm-Zellen zwei bis drei Zellen dick; verschmierte
Karten bestehen aus dünnen Fragmenten an vielen Versätzen und schneiden
scheinbar besser ab. Erst das Rendern entschied.

Zwei weitere Korrekturen: Die Mastmaske funktioniert — der Treiber maskiert mit
**NaN**, nicht mit 0 wie in `stl27l.yaml` behauptet. Eine Prüfung auf `== 0.0`
findet sie nicht; genau das führte kurzzeitig zu der falschen Vermutung, der
Mast sei unmaskiert. Und `amadeus_lidar_bringup` brauchte eine `setup.cfg`, die
console_scripts nach `lib/<paket>` umleitet, sonst findet launch sie nicht.

**Betroffen:** `src/amadeus_lidar_bringup/` (neuer Knoten, `scan_gitter.py`,
Test, `setup.cfg`, `setup.py`, Launch, `stl27l.yaml`), Dokumentation. Beim
Fahrtest beide Motoren.

**Teststatus:** Zwei saubere Durchläufe mit Vorbedingungsprüfung und
verifiziertem Abschalten. Ohne Normalisierer exakt reproduziert (31 Verwürfe,
10 Knoten), mit Normalisierer 0 und 41. Sechs Unittests der Winkelabbildung.

**Offene Risiken:** Der Odometrie-Winkelfehler von −6,3° bis −6,5° je Umdrehung
bleibt ungeklärt und widerspricht den 0,50° aus `9e8c06f`. Ein Deskew fehlt
weiterhin. Beide sind vom Normalisierer unabhängig.

**Betriebsfalle, die real Schaden anrichten kann:** `kill -INT` auf die
`ros2 launch`-PID beendet nur den Elternprozess; die Knoten können weiterlaufen.
Dadurch liefen zeitweise **zwei vollständige Stapel gleichzeitig**, mit zwei
`map->odom`-Publishern und zwei scharfen `base_hardware`-Knoten auf demselben
RS485-Bus. Die betroffene Messung war unbrauchbar und wurde verworfen. Nach dem
Beenden immer die Knotenprozesse nachzählen, die eigene PID ausnehmen.

**Rückfallweg:** `normalize_scan:=false` startet wieder ohne den Knoten; der
Treiberpfad bleibt unverändert. Die Karte ist dann wieder verschmiert, der
Roboter aber fahrbereit.

---

## 2026-08-12 — Backport abgenommen; er legt einen zweiten Fehler frei

**Entscheidung:** Der gepinnte `slam_toolbox`-Backport (Upstream `649a50e`,
PR #808) wird auf dem Jetson als Overlay `~/amadeus_slam_toolbox_ws`
betrieben. Phase 1 bis 3 der Abnahme sind bestanden, **Phase 4 bleibt
gesperrt**, bis die neu sichtbare Wandverschmierung eingegrenzt ist.

**Grund / Evidenz:** Der Kern ist doppelt belegt. Synthetisch, ganz ohne
Hardware (`tools/kartierung/test_reine_drehung_synthetisch.py`): dieselben
Eingangsdaten, nur der Schalter umgelegt, ergaben **37 gegen 0** neue Knoten bei
einer 360°-Drehung — die `false`-Variante reproduziert das Fehlerbild aus #807
exakt, nicht ungefähr. Am realen Roboter: 1 → 11 Knoten, freie Fläche 10,8 →
23,2 m². Vorher waren es null.

Dass wirklich der gepatchte Code läuft, ist über das Binärpaket belegt, nicht
über einen Pfad: `check_min_dist_and_heading_precisely` kommt im Overlay-`.so`
genau einmal vor, im apt-Paket gar nicht — und der Parameter ist am laufenden
Knoten abfragbar.

**Der wichtigere Befund ist der zweite:** Die Nachher-Karte zeigt versetzt
mehrfach eingetragene Wände. Wand/frei stieg von 0,041 auf 0,115 (Richtwerte
0,091 vor und 0,052 nach der Odometrie-Kalibrierung), dicke Wandzellen von
0,0 % auf 3,1 %. Solange reine Drehungen verworfen wurden, konnte eine Drehung
die Karte auch nicht verschmieren — der Backport hat das Problem nicht erzeugt,
sondern sichtbar gemacht. Zwei Kandidaten, **keiner gemessen bestätigt**:
fehlendes Deskew (bei 0,30 rad/s dreht der Roboter je 100-ms-Scan um 1,72°) und
ein Winkelfehler der Odometrie (gemessen −4,98° je Umdrehung gegen die in
`9e8c06f` dokumentierten 0,50°, bei nur 0,1 cm seitlichem Versatz).

Zwei Prüfungen des Übergabeprotokolls erwiesen sich als untauglich:
`colcon test` meldet Rückgabewert 0 bei **0 Tests**, weil der Testblock im
gepinnten Upstream auskommentiert ist. Und `slam_knoten_beobachten.py` las seine
Grundlinie über 30 `spin_once`-Aufrufe ein — die kehren aber zurück, sobald
irgendein Callback lief, und der TransformListener liefert ~50 TF/s. Die
Schleife war nach Sekundenbruchteilen durch, während der Graph nur alle 1 s
publiziert; der Initialknoten wurde dadurch der Bewegung zugerechnet und ein
reiner Stillstandslauf meldete „Die Drehung erzeugt Knoten".

**Betroffen:** `docs/SLAM_TOOLBOX_ROTATION_FIX.md`, `docs/ROBOT_TRANSFER.md`,
`tools/kartierung/slam_knoten_beobachten.py`,
`tools/kartierung/test_reine_drehung_synthetisch.py`; Overlay
`~/amadeus_slam_toolbox_ws`; beim Fahrtest beide Motoren.

**Teststatus:** Phase 0–3 bestanden bis auf das Kriterium „keine versetzt
duplizierten Wände". `/scan` stabil 9,99 Hz, genau ein Publisher für
`map -> odom`, `slam_toolbox` beendet sauber.

**Offene Risiken:** Wandverschmierung ungeklärt. Die Drehung erzeugte nur 10
statt der theoretisch möglichen ~42 Knoten, synthetisch waren es 37 — Ursache
nicht gemessen. Karto verwarf 31 von rund 2100 Scans wegen schwankender
Strahlenzahl (2146–2174 statt fest 2172); klein, aber unerklärt. Der
LiDAR-Treiber stirbt beim Herunterfahren mit Exit −6, `base_hardware` mit
Exit 1 (`rcl_shutdown already called`) — beides auf dem Weg nach unten und
unabhängig vom Backport.

**Nächster Schritt, bewusst eine Messung und keine Parameteränderung:** dieselbe
Drehung bei 0,20 rad/s wiederholen und die Kartenkennzahlen vergleichen. Das
trennt Deskew von Odometrie, ohne eine Hypothese vorwegzunehmen.

**Rückfallweg:** Neue Shell öffnen und das Overlay nicht sourcen; dann gilt
wieder das unveränderte apt-Paket unter `/opt/ros/humble`. Gegengeprüft. Es
werden keine Dateien verändert und nichts gelöscht.

---

## 2026-08-10 — Import in ein privates GitHub-Repository

**Entscheidung:** Der getestete Jetson-Stand wird nach
`github.com/chris01-byte/Roboter_ws` (privat) übertragen; `ios/` und
`integration/` werden vom USB-Stick ergänzt.

**Grund / Evidenz:** Jetson und Stick waren divergent — der Jetson trug 27
Commits mit der getesteten Robotersoftware, der Stick 4 Commits mit der iOS-App
und den Transferwerkzeugen. `git merge-base --is-ancestor` bestätigte, dass
keiner den anderen enthält. Vor dem Push geprüft: keine Treffer auf Schlüssel-,
Token- oder Passwortmuster; größte Datei 836 KB; keine Provisioning-Profile.
`testwohnung.pgm` ist synthetisch (240×200 Zellen, **null** unbekannte
Bereiche) und damit unbedenklich — eine echte SLAM-Karte hat immer unbekannte
Zonen.

**Betroffen:** gesamtes Repository, `.gitignore`

**Teststatus:** Push erfolgreich, Inhalt auf GitHub gegengeprüft (privat, keine
Token-Funde).

**Offene Risiken:** Ein leeres Repository `amadeus-robot-ws` ist bei der
Einrichtung entstanden und konnte nicht automatisch entfernt werden.

**Rückfallweg:** Repository ist privat und kann gelöscht werden; der lokale
Stand auf dem Jetson bleibt unabhängig davon bestehen.

---

## 2026-07-28 — Anfahrverhalten geglättet (Commit `f3a9094`)

**Entscheidung:** `base_hardware` schreibt Startdrehzahl und Rampen bei jedem
Verbindungsaufbau: `0x0020` = 5 rpm, `0x001E` = 800 ms, `0x001F` = 400 ms.

**Grund / Evidenz:** Der Roboter nickte beim Anfahren sichtbar. Bei einer Kamera
auf 1,34 m verschieben schon 2° Nicken den gemessenen Boden auf 3 m Entfernung
um rund 10 cm — Boden wird dann als Wand kartiert. Auslesen der Register ergab
**Startdrehzahl 30 rpm**, ein Rest aus dem Richtungstest vom 24.07., der
persistent im Motor gespeichert war. Bei Fahrdrehzahlen um 46 rpm setzte der
Antrieb damit sofort mit 65 % der Zielgeschwindigkeit ein. Messung bestätigte:
Solldrehzahl nach ~110 ms zu 90 % erreicht, **trotz** 800-ms-Rampe — die Rampe
war nie das Problem.

**Betroffen:** `base_hardware_node.py`, `base_hardware_params.yaml`; beide
Motoren.

**Teststatus:** Vom Nutzer am Gerät bestätigt („alles passt"). Bremswert von 250
auf 400 ms nachjustiert, weil 250 ms zu ruppig und 800 ms zu weich war
(Nachlaufen).

**Offene Risiken:** 5 rpm Startdrehzahl könnte bei höherer Last zu wenig
Anlaufmoment bieten. Register `0x0021` steht auf 100, Bedeutung unbekannt.

**Rückfallweg:** Werte in `base_hardware_params.yaml` zurücksetzen; der Antrieb
läuft mit jedem Wert, nur weniger sanft.

---

## 2026-07-28 — Lokalisierung ohne Vorwissen nachgewiesen (Commit `e136871`)

**Entscheidung:** Neues Launch-Argument `start_at_origin` und der Test
`lokalisierung_kidnapped.py` als verbindliches Prüfverfahren.

**Grund / Evidenz:** Zwei naheliegende Prüfungen beweisen **nichts**:
(1) „`map→odom` ist nicht die Identität" — RTAB-Map lädt beim Start die zuletzt
gespeicherte Pose, der Roboter steht dann sofort „richtig" da.
(2) „`/localization_pose` wird publiziert" — im Lokalisierungsmodus kommen
Meldungen in **jedem** Verarbeitungstakt (71 Stück bei ~120 s und 1 Hz),
unabhängig vom Erfolg. Belastbar ist nur: ohne Vorwissen starten **und** von
mehreren Standorten prüfen, ob der gemeldete Positionsunterschied dem echten
entspricht.

**Betroffen:** `slam.launch.py`, `tools/kartierung/`

**Teststatus:** Zwei Läufe: 1,25 m ermittelter Abstand gegen 1,4 m von Hand
gemessen (11 % Abweichung). Gegenprobe mit einer schlechteren Karte fiel
korrekt durch (0,000 m Versatz).

**Offene Risiken:** Geometrische Genauigkeit nur handgemessen.

**Rückfallweg:** `start_at_origin:=false` stellt das alte Verhalten her.

---

## 2026-07-28 — Wörterbuch-Verlust: Ursache korrigiert (Commit `390fcec`)

**Entscheidung:** SIGINT geht **nur an den ros2-launch-Prozess**, nie an die
Prozessgruppe; beim Start `sigterm_timeout:=120 sigkill_timeout:=180`.

**Grund / Evidenz:** Die bisherige Projekterklärung lautete, nur `kill -9`
zerstöre das visuelle Wörterbuch. Gemessen: Auch ein SIGINT an die
**Prozessgruppe** tut es — rtabmap bekommt das Signal doppelt (direkt vom Kernel
und weitergereicht von launch), das zweite bricht das Speichern ab. Ergebnis
war eine Datenbank mit 831 Knoten und **0 Wörtern**, rtabmap starb mit
`exit code -2`. Zusätzlich eskaliert launch nach 5 s selbsttätig auf
SIGTERM/SIGKILL, was für große Karten zu knapp ist.

**Betroffen:** `slam.launch.py` (Dokumentation), `tools/kartierung/stop_slam.sh`

**Teststatus:** Mehrfach bestätigt — seither wird das Wörterbuch zuverlässig
geschrieben (bis 271.805 Wörter).

**Rückfallweg:** Entfällt; ohne den Fix ist die Karte unbrauchbar.

---

## 2026-07-28 — RS485-Selbstheilung repariert (Commit `390fcec`)

**Entscheidung:** Der alte Modbus-Client wird vor einem Neuaufbau geschlossen.

**Grund / Evidenz:** Ein einziger Timeout im Startgewitter (OAK, VL53, RTAB-Map
am USB-Bus) legte die Motoren dauerhaft still. Die Selbstheilung legte einen
neuen Client an, ohne den alten zu schließen; dessen exklusives Port-Lock ließ
jeden weiteren Versuch an `[Errno 11] Could not exclusively lock port`
scheitern.

**Betroffen:** `base_hardware_node.py`; RS485-Bus

**Teststatus:** 0 RS485-Fehler über alle folgenden Fahrten.

**Rückfallweg:** Vorheriger Commit; dann ist ein Neustart des Knotens nach
jedem Timeout nötig.

---

## Grundsätzliches (übernommen aus früheren Sitzungen)

- Amadeus nutzt eine **OAK-D-S2** auf hohem Mast; ein Wechsel auf OAK 4 D Pro
  Wide FF ist vorgesehen. Der Treiber erkennt das Modell selbst.
- Für robuste 2D-Navigation ist ein **separater 2D-Lidar** vorgesehen. Kamera
  und Lidar haben unterschiedliche Aufgaben: die Kamera liefert visuelle
  Lokalisierung und Semantik, der Lidar die horizontale Navigationskarte.
- **Maststeifigkeit, Sensor-Frames und Odometrie** sind für die Kartenqualität
  genauso wichtig wie der Sensor selbst — belegt durch den Nick-Befund oben.
- **Spiegel und Glas** erzeugen optische Ausreißer und werden softwareseitig
  gefiltert, nicht als reale Wände interpretiert. Offener Punkt: Die
  Strahlartefakte vom 28.07. (74,6 % der scheinbaren Freifläche) sind
  vermutlich darauf zurückzuführen; `tools/kartierung/karte_bereinigen.py`
  entfernt die Folge, die Ursache ist ungeklärt.
- Die **VL53-Sensoren decken flache Bodenobjekte nicht ab**: Sie sitzen auf
  0,305 m und schauen waagerecht; ihr Kegel trifft den Boden erst bei ~0,53 m,
  jenseits ihrer Reichweite. Kabel und Schwellen sieht kein Sensor.
