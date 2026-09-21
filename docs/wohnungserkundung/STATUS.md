# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus / `chris01-byte/Roboter_ws` · Motorloser Zielsystemcheck: BESTANDEN · Realversuch: SICHER GESTOPPT, Nahbereichsblocker · PR #95-R1 plus eng begrenzte Zielsystemkorrekturen · 2026-09-21**

Dies ist der einzige laufende WE-Status. [Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md),
[Meilensteine](MEILENSTEINE.md) und die Sicherheits-/Abnahmereihenfolge bleiben
unverändert. Der vorherige M3/U-Stand ist im
[Archiv](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md) erhalten.

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
| WE-M0/B | Isolierter Jetson-Build, vollständige Tests, gemeinsame motorlose Zielsystemlast und zwei wiederholte saubere Gesamtstopps bestanden. Ein freigegebener Realversuch fuhr ca. 0,466 m ohne Safety-, Encoder- oder Busfehler und endete sicher. | Das ist nur ein Teilnachweis, keine vollständige Fahrabnahme. |
| WE-M1 | Portalgedächtnis und In-Memory-Verträge softwaregeprüft. | Keine Hardwareaussage. |
| WE-M2 | Automatische Rohkarten-, Portal-, Frontier-, Graph- und Aufgabenbildung softwaregeprüft. | Automatische Regionskorrektur bleibt konservativ; reale Karten offen. |
| WE-M3 | Automatische Zielwahl, revisionssichere Kindziele, zweckgebundene Transite und der Mehrraum-Rückweg sind gerätefrei geprüft. Aktive Frontierziele werden auf jeder neueren Rohkarte am festen Ziel erneut geprüft; motorlos blieb ein Ziel über Revision 55 bis 119 stabil. | Der korrigierte Pfad ist noch nicht fahrend über mehrere Kartenrevisionen abgenommen. |
| WE-M4 | Scope und Fahrt waren vor Ort freigegeben; der erste Realversuch lieferte einen sicheren Teilnachweis. Der zweite aktive Vorlauf sendete wegen null sicher erreichbarer Ziele bewusst keinen Auftrag. | Aktuelle Pose und lokaler Scope bilden keinen zusammenhängenden sicheren Pfad; Rückstellung oder neu vermessener Scope erforderlich. Keine Drei-Regionen-Abnahme. |
| WE-M5 | Versionsgebundener, atomarer WE-Metadatenspeicher und passive Wiederaufnahme über Kartenmanagerstatus sind im Mehrraum-Rückweg geprüft. Auf dem Jetson bestanden echter Kartenmanager-Save, gebundener WE-Save, Falschkartensperre und passives Laden derselben Karte ohne Ziel. | Reale Wiederaufnahme nach Lokalisierung und Portal-/Transit-ID-Nachweis mit echter Mehrraumkarte bleiben offen. |
| WE-M6 | Der vereinbarte gerätefreie Mehrraum-/Unterbrechungs-/Fortsetzungsabschluss besteht einschließlich zweckgebundenem Rücktransit. | Reale Mehrraumkette, Unterbrechung/Wiederaufnahme und wiederholbarer Abschluss bleiben offen. |
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

Im vereinbarten **gerätefreien Software- und motorlosen Zielsystemumfang ist
kein Blocker bekannt**. Der erste Realversuch hat darüber hinaus einen
Softwareblocker der aktiven Frontierfortsetzung offengelegt; die eng begrenzte
Korrektur ist motorlos auf dem Produktionspfad belegt. Für die nächste reale
Fahrt besteht nun ein physischer Scope-Blocker, kein Anlass zu einer neuen
WE-Architektur:

1. Den Branch reviewen und nach ausdrücklicher Freigabe nach `main` integrieren;
   kein automatischer Merge.
2. Amadeus zur ursprünglichen markierten Startpose und Orientierung
   zurückstellen oder den zusammenhängenden sicheren Scope ab der aktuellen
   Pose neu vermessen; reale Geometrie bleibt außerhalb des Repositorys.
3. Chassis-/Portalprofil, Kreis-/Polygon-Nahbereichsvertrag und
   Kollisionsüberwachung bei der Fahrt weiter beobachten; Softwaretests sind
   keine Hardwarefreigabe.
4. Erst nach Auflösung dieses Scope-Blockers und erneuter Vorprüfung den bereits
   freigegebenen Umfang fahren; anschließend WE-M6 einschließlich realer
   Unterbrechung/Wiederaufnahme wiederholt abnehmen.

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
