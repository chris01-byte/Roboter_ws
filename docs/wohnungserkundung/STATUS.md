# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus / `chris01-byte/Roboter_ws` · STUFE 1: GRÜN BESTÄTIGT · commit- und präfixgebundener Zielstand `5e3fe0a` · zwei motorlose Gesamtstarts/-stopps bestanden · R9-Nahbereichsbefund bleibt ausschließlich für eine spätere Fahrt offen · 2026-09-23**

Dies ist der einzige laufende WE-Status. [Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md),
[Meilensteine](MEILENSTEINE.md) und die Sicherheits-/Abnahmereihenfolge bleiben
unverändert. Der vorherige M3/U-Stand ist im
[Archiv](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md) erhalten.

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
| WE-M3 | Automatische Zielwahl, revisionssichere Kindziele, zweckgebundene Transite und der Mehrraum-Rückweg sind gerätefrei geprüft. Der bestätigte Live-Pfad `SOURCE_INVALIDATED` → sicherer Stop → frische Auswahl ist zusätzlich mit einem Vertragsfall und 892 Explorer-Tests geprüft. | Der Replan-Fix ist noch nicht fahrend über mehrere Kartenrevisionen abgenommen. |
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

Im vereinbarten **gerätefreien Software- und motorlosen Stufe-1-Umfang ist nach
der commit- und präfixgebundenen Inventur kein weiterer Blocker bekannt**. Der
reale R9-Lauf hat den Fix jedoch noch nicht bis zum Abschluss abgenommen und
endete an einem konkreten physischen Nahbereichsbefund. Das ist kein Anlass zu
einer neuen WE-Architektur und kein Bestandteil dieser Stufe:

1. Den Stufe-1-Themenbranch und seinen PR reviewen; kein automatischer Merge
   und kein Beginn von Stufe 2 in diesem Auftrag.
2. Den linken Nahbereich an der R9-Endpose sichtbar prüfen, die Begrenzung
   entfernen oder Amadeus unbestromt auf eine nachweislich freie, vermessene
   Ausgangspose zurücksetzen; reale Geometrie bleibt außerhalb des Repositorys.
3. Nach frischem Lifecycle-, Quellen-, TF-, Encoder-, Bus- und Safety-Preflight
   erst mit neuem ausdrücklichem Auftrag über den Missionsmanager fortsetzen.
   Chassis-/Portalprofil, Polygon-Nahbereichsvertrag und
   Kollisionsüberwachung bleiben unverändert; Softwaretests sind keine
   Hardwarefreigabe.
4. Erst nach Auflösung dieses physischen Blockers den bereits freigegebenen
   Umfang fahren; anschließend WE-M6 einschließlich realer
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
