# AP-06 Gesamtprüfung

## Sensorüberwachten Start mit denselben Kriterien vergleichen

Der Produktkandidat vom 11.10.2026 wird beim ursprünglichen Testdriver mit
`--unknown-space-policy sensor_guarded` ausgewählt. Standard bleibt hier
`observed_only`, damit bisherige Vergleichsläufe identisch konfiguriert bleiben.
Die Auswahl lädt zusammen die Bewegungsregel im vorhandenen Explorer,
Nav2-`allow_unknown`, eine separate LiDAR-Hindernisebene und den LiDAR/VL53-
Collision-Monitor. Session-/Karten-/Scopebindung bleiben die tatsächlichen
Werte des Laufs. Keine ideale Rundumsicht oder Wahrheitskarte hinzufügen.

Alle ursprünglichen Szenarien, Sensoren, Weltgeometrien, Gesamtbudgets und
Abnahmekriterien bleiben unverändert. `result.json` benennt die gewählte
`unknown_space_policy`; Erfolg wird weiterhin anhand des Missions-/Karten-
Ergebnisses geprüft. Die neuen Parameter-/Starttests sind keine ganzen
A/B/C-Läufe und kein realer Fahrnachweis.

`ap06_closed_product.py` startet die vorhandene Mission-Manager-/C++-BT-/
Explorer-Kette, echtes Nav2 NavigateToPose mit NavFn/RPP, Fahrtor, nativen
Velocity Smoother und Collision Monitor. Ein echter `robot_localization`-EKF
besitzt `odom→base_link`, der gepinnte/gepatchte `slam_toolbox` `map→odom`.
Originale Scan-Normalisierung und Safety-Monitor verarbeiten die
modellierten Eingänge selbst. Der native DDS-Prüfer protokolliert die GIDs je TF-Kante. Kein Wahrheits-TF,
Wahrheitskarten-Publisher oder manuell gesendetes Navigationsziel.

**Diese Prüfung ersetzt keine Jetson- oder physische Abnahme.** Die tatsächliche
Abnahme und alle offenen Kriterien stehen allein im
[STATUS](../../docs/wohnungserkundung/STATUS.md).

## Vorab festgelegte Welt

`ap06_scenarios.json` wurde in `741e7cc` vor dem ersten Missionslauf festgelegt;
`f61ee85` benennt den vorhandenen Spiegelungsschritt getrennt. Zwei Räume,
Verbindung, 68-/80-cm-Türen, Umweginsel und blockierte Alternative. Drei
geometrisch freie Startposen, 60 s Startvorlauf, 900 s Gesamtmission und 150 s
je Aufgabe. Kein nachträgliches Verschieben von Startpunkten oder Wänden.

Das Original bleibt bytegleich als 720-Strahl-Belastungsprofil erhalten.
`ap06_native_scenarios.json` wird vor seinem ersten Lauf getrennt versioniert:
2160 Strahlen entsprechend dem vorhandenen `scan_vereinheitlichen`-Produktpfad.
Alle drei Startposen, Welt, Mastmaske, Konturen, Fristen und Abnahmekriterien
sind unverändert. Der Unterschied ist offen ausgewiesen: das erste SLAM-Raster
verlangt mehr als zwei Strahldurchgänge pro Zelle; die niedrigere Dichte erzeugt
mehr unbekannte Zellen. Kein ursprünglicher Negativlauf wird dadurch positiv.
Das Werkzeug nutzt standardmäßig das separat vorab in `0f95424` deklarierte
`ap06_product_scenarios.json`: gleiche Welt/Posen/Budgets/Abnahme, ursprüngliche
Nav2-Obstacle-/Static-/Inflation-Layer und endliche Nah-/Tiefensensoren.
Das Dichteprofil `342af24` hatte nur Static-/Inflation-Layer; seine Ergebnisse
bleiben getrennt erhalten. `--manifest` erlaubt
die ausdrückliche Wiederholung des ursprünglichen Profils.

Sensoren entstehen aus tatsächlicher simulierter Bewegung: endliche, verdeckende
Laserstrahlen, absolute ganzzahlige Motorzähler und HWT-FC03-Rohregister.
Vorhandene HWT-Transport-/CRC-/Messzeit-/Bias-, Encoder-/Watchdog- und
Gesundheitsprüfungen berechnen ihren Status selbst. Ausschließlich die
Geräteendpunkte sind Speichertransporte; USB-Identitäten und Buslatenzen sind
damit **nicht** geprüft. Etwaige Produktionsfelder `synthetic:false` im
Originalstatus sind keine Hardwarebehauptung dieses ausdrücklich simulierten
Prüfstands. Keine künstlichen Healthy-Publisher.

Das Modell integriert zeitlich geordnete Registeränderungen und reale verstrichene
Zeit in höchstens 10-ms-Schritten. Verzögerte Timer bleiben protokolliert;
Sensorproben werden weder aufgefüllt noch rückdatiert. Die 50-ms-Antwortzeit
qualifiziert ausschließlich dieses Modell, nicht die echten 2000-/400-ms-Rampen.
Nahbereichsrohdaten entstehen aus endlichen 8×8-Strahlkegeln. Die unveränderten
Produktmethoden für Qualitätsprüfung, Matrix, Status und Wolken verarbeiten diese
Rohdaten; nur der I2C-Endpunkt wird ersetzt. Ein endliches 8×16-Tiefenmodell
mit Boden-/Wandverdeckung speist den ursprünglichen Kamera-Obstacle-Layer.
Montage/Qualität sind deklarierte idealisierte Modellbedingungen; optische
Hardware, USB-Betrieb, Störungen und echte Last sind damit nicht geprüft.

Die Mastmaske bleibt im Standard aktiv: native 236–304° → ROS 56–124° mit
vorhandener +90°-Montage. `--ideal-lidar` ist eine getrennt gekennzeichnete
Diagnose ohne Mastmaske, niemals Ersatz der Standardabnahme.
Nav2 nutzt die tatsächliche SLAM-Karte und unveränderte Produkt-Costmaps mit
Static-/Obstacle-/Inflation-Layern sowie rollender lokaler Odom-Costmap; die
unabhängige VL53-Kollisionsinstanz bleibt im Befehlsweg. Dies qualifiziert nicht
den realen OAK-/VL53-Obstacle-Layer unter Hardwarelast.

## Reproduktion ohne Geräte

Auf einem ARM-Laborhost ohne Docker kann der gleiche Gesamtfall über
`ap06_namespace_runtime.py` in tatsächlichen separaten User-, Mount-, PID-,
Netz-, IPC- und UTS-Namespaces laufen. Der Launcher benötigt Bubblewrap;
er reicht keine Geräte durch, mountet nur ausdrücklich gewählte Quell-/
Bibliotheks-/Kandidatenpfade lesend und das private Ausgabeverzeichnis schreibend.
Die Hostinstallation, `/sys` und Host-IPC sind nicht sichtbar. Er vergleicht
die echten Namespace-IDs mit den zuvor erfassten Host-IDs; kein künstliches
Docker-Markerfile. Hardwareidentität oder gemeinsame Namespace-Grenze lehnt
den Lauf weiterhin ab. Plattform und verwendeter Unterbau bleiben im Manifest
auszuweisen. Welt, Startposen, Sensorprofil, Budgets und Abnahme ändern sich nicht.

```bash
python3 tools/simulation/ap06_namespace_runtime.py --repo "$AP06_SOURCE" \
  --runtime "$AP06_CANDIDATE/runtime.bash" --underlay "$AP06_UNDERLAY" \
  --output "$AP06_OUTPUT/isolation-only" --verify-only
python3 tools/simulation/ap06_namespace_runtime.py --repo "$AP06_SOURCE" \
  --runtime "$AP06_CANDIDATE/runtime.bash" --underlay "$AP06_UNDERLAY" \
  --output "$AP06_OUTPUT/door68_start_a" --case door68_start_a
```

Ubuntu 22.04/Humble/amd64/Python 3.10 in einem eigenen Docker-Container;
keine Geräte durchreichen. Build und Auflösung fremder Bibliotheken bleiben in
diesem Container. `ap06_dependencies.json` enthält zehn öffentliche Archive
mit Revision und SHA256, 31 ausgewählte native Pakete sowie Python-Pins.
Quell-/Build-/Installverzeichnisse und Originalausgaben außerhalb des Repositorys
halten. Das Vorbereitungswerkzeug überschreibt keine vorhandenen Quellbäume:

```bash
python3 tools/simulation/prepare_ap06_sources.py \
  --cache /tmp/ap06/downloads --destination /tmp/ap06/sources
```

Für Offlineprüfung vorhandener Archive zusätzlich `--offline --verify-only`.
Der Quellbaum erhält den bestehenden Pure-Rotation-Patch, den deklarierten festen Karto-Rasterpatch und die gebundene NavFn-Zellmittenkorrektur; es wird kein Git-HEAD
für extrahierte Archive erfunden. Lizenzen bleiben in den Quellarchiven erhalten.

Die zugehörigen System-/ROS-Entwicklungsabhängigkeiten vor dem Build mit
`rosdep` für genau die in `prepared.json` aufgeführten Paketpfade und die zwölf
Produktpakete auflösen. Dazu gehören BehaviorTree.CPP v3 für Nav2, Boost, Qt,
Ceres/SuiteSparse, GeographicLib, SQLite, ZeroMQ/Fmt, TF-/Nachrichtenpakete
und die deklarierten Python-Pins. `rosdep --ignore-src` muss auch alle vorbereiteten
Quellpakete sehen; kein Fremdprodukt als Navigator verwenden.

Die Nav2-Paketpfade `nav_2d_msgs` und `nav_2d_utils` liegen im gepinnten
Quellarchiv unter `nav2_dwb_controller/`. Der Quellenlock enthält jetzt diese
tatsächlichen Pfade; die Vorbereitung lehnt fehlende `package.xml` ab.
Ein unvollständiger Underlay darf diese Pakete nicht unbemerkt aus einem anderen
Install ergänzen. Versions-/Archivpins und Szenario-Abnahmekriterien bleiben gleich.

Für den LAB-Slotkandidaten beim bestehenden Testdriver ausdrücklich
`--unknown-space-policy sensor_guarded --execution-mode lab_slots` angeben.
Das lädt die vorhandenen sensorüberwachten Profile und danach den Slotablauf.
`continuous` bleibt der bisherige Ablauf. Ein bestandenes Cancel-/HOLD-Stopp-
Szenario bedeutet keinen erfolgreichen Kartierungsauftrag und keine vollständige
Wiederaufnahme. Der aktuelle Umfang steht ausschließlich im WE-STATUS.

```bash
source /opt/ros/humble/setup.bash
python3 -m pip install -r src/explore/requirements-geometry.txt
mapfile -t AP06_NATIVE_PATHS < <(python3 -c \
  'import json; print("\n".join(json.load(open("/tmp/ap06/sources/prepared.json"))["base_paths"]))')
export MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
colcon --log-base /tmp/ap06/native-log build --executor sequential \
  --base-paths "${AP06_NATIVE_PATHS[@]}" \
  --build-base /tmp/ap06/native-build --install-base /tmp/ap06/native-install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DBTCPP_UNIT_TESTS=OFF -DBTCPP_EXAMPLES=OFF -DBTCPP_BUILD_TOOLS=OFF
source /tmp/ap06/native-install/setup.bash
colcon --log-base /tmp/ap06/product-log build --executor sequential \
  --base-paths src/amadeus_map_identity src/base_hardware src/robot_interfaces \
  src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore \
  src/robot_navigation src/robot_map_manager src/vl53_near_field \
  src/safety_monitor src/amadeus_lidar_bringup \
  --build-base /tmp/ap06/product-build --install-base /tmp/ap06/product-install \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
source /tmp/ap06/product-install/setup.bash
cmake -S tools/simulation/tf_ownership_probe -B /tmp/ap06/tf-probe-build
cmake --build /tmp/ap06/tf-probe-build -j2
```

Für den Lauf den Container ohne externe Netzwerkverbindung betreiben. Das
Werkzeug verlangt zusätzlich explizites `AP06_SIMULATION=1`, einen eigenen
Domainbereich und fehlende Jetson-/Gerätealiases:

```bash
export AP06_SIMULATION=1 ROS_DOMAIN_ID=176 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
python3 tools/simulation/ap06_closed_product.py --repo "$PWD" \
  --tf-probe /tmp/ap06/tf-probe-build/tf_ownership_probe \
  --case door68_start_a --output /tmp/ap06/runs/door68_start_a
```

Jeder Lauf benötigt ein neues Ausgabeverzeichnis. Weitere Manifestfälle
`door68_start_b`, `door80_start_c`, `cancel`, `gyro_hold` einzeln starten.
`--profile-selection` bewahrt Originalentscheidungen/Budgets, erzeugt zusätzlich
`selection-*.prof` und gilt wegen Messaufwand nur als Diagnose.
`--capture-geometry` sichert höchstens 16 tatsächliche Start-/Fehlerinputs
einschließlich Raster, TF-Bezug und privatem Bestand. Es ändert keine Entscheidung,
gilt wegen Messaufwand ebenfalls nur als Diagnose und setzt
`manifest_compatible=false`. Solche Läufe zählen nicht als Gesamtpositive.
`--diagnostic-beams` weicht ausdrücklich vom geladenen Manifest ab und ist
ebenfalls keine Manifestabnahme. `--save-partial` prüft nach dem terminalen
Missionsresultat das echte Speichern der synthetischen SLAM-Karte und meldet
den zugehörigen Explorer-Checkpoint getrennt.

Der ergänzende Fall `gyro_hold` unterbricht den Speichertransport für 450 ms,
prüft ausschließlich nach der Injektion beobachtetes HOLD und gemessenen Halt
innerhalb 1 s. Er beweist kein ACK/Resume; `hold_resume_qualified` bleibt falsch.
Ohne tatsächlich erste Bewegung gilt keine der beiden Injektionen als geprüft.

## Native Nahbereichsregression

`ap06_nearfield_costmap_probe.py` startet ausschließlich den echten Nav2-Planer
mit seiner nativen Costmap und verarbeitet unveränderte VL53-Produktmethoden.
Eine deklarierte freie synthetische Karte/statische TF sind hier Komponenten-
Eingänge, kein Gesamtstacknachweis. Vier Costmap-Updates pro Phase: Fernziele
dürfen aus begrenzten Räumendpunkten keine Hindernisse erzeugen; anschließend
muss eine tatsächlich im Kegel platzierte nahe Wand weiterhin markiert werden.
Keine Action und kein Motorknoten. Gleiche Container-/Domainisolierung wie oben.

```bash
python3 tools/simulation/ap06_nearfield_costmap_probe.py --repo "$PWD" \
  --output /tmp/ap06/costmap-regression
```

## Nachweise und Grenzen

`commands.jsonl`, verlustfrei komprimierte `events.jsonl.gz`, Prozesslogs, `plant.jsonl`, Manifestkopie und
`result.json` bewahren Eingang, tatsächlich aufgelöste Präfixe, Quellenzustände
und Ergebnis. Die echte SLAM-Karte wird samt Geometrie separat gespeichert.
Unabhängige Referenzprüfung misst die ganze gepaddete Kontur, Heckfreigabe,
beobachteten Anteil tatsächlicher Referenzzellen und Wandfehler. Eine steigende
freie Zellzahl allein reicht nicht. Erfolg verlangt zusätzlich tatsächlichen
Missionsabschluss, mindestens drei autonome Aufgaben, weitere Karte/Beobachtung
und eindeutig beobachtete TF-Besitzer. Gestoppte/partielle/abgelehnte Läufe
bleiben negativ; sie erfüllen keinen Positivfall.

Der korrigierte Startadapter prüft im bestehenden RPP-/Boundary-/Egress-Opt-in
zusätzlich aktuelle Vorwärtspositionen. Ihr Mindestabstand berücksichtigt die
unveränderte besuchte Nachbarschaft, die 15-cm-Ankunftstoleranz und eine Rasterzelle;
der vorhandene lokale Suchradius begrenzt die zusätzlichen Offsets. Erledigte
Aufgaben werden an die frisch gemessene Ankunft gebunden. Nur volle Geometrie
und Sicht tatsächlicher Frontieranker ergeben einen Vorschlag; vor Fahrt bleibt
der wirkliche Nav2-Plan verbindlich.
Auch diese Suche verbraucht das unveränderte 5-s-Kandidatenbudget.

Die vorhandenen Geräte-, Frische-, HOLD-, Cancel- und Konturgrenzen werden nicht
gelockert. Bei Prozess-/Quellenfehler oder geometrischer Kollision endet der Lauf.
Direkte Kinder werden einzeln beendet, nie ihre Prozessgruppe. Testausgaben sind
rein synthetisch; reale Raumdaten gehören weiterhin ausschließlich außerhalb Git.

## AP-06-Referenzregression, 05.10.2026

`test_metric_egress_reference.py` prüft echte Produktmethoden mit der gesicherten
synthetischen C-Startkarte: gemeinsame TF-Zeit, verschobene/gedrehte Raster,
Wachstum, feste monotone Abfahrt, Wiederbetretung, neue Unknown-/Obstaclezellen,
beobachtet→unbekannt, fehlender Bezug und Kontextwechsel. Der ursprüngliche
Gegenfall ist vor der Änderung rot. Der Beleg wird einmal erfasst und in der
ersten Odometriefläche erhalten; aktuelle unbekannte Rasterzellen brauchen
vollständige Deckung durch den Restbestand und frischen ganzen Fahrzeugbeweis.
Bei subzelliger Rasterung verfällt Autorität konservativ, statt Teilzellen
durch Kopieren oder Interpolation freizugeben. Geometrische Memoisierung enthält
keine Quellenentscheidung, Frist oder Bewegungsfreigabe. Die bestehenden fünf
Manifestfälle werden unverändert wiederholt; Restfehler zählen weiter negativ.

## Zusätzliche Reparaturnachweise, 05.10.2026

`slam_grid_regression.cpp` prüft die tatsächlich gepatchten Karto-Funktionen
bei Wachstum, negativen Grenzen und exakten Endpunkten. GEOS/Shapely 2.0.7
ist für die exakte dauerhafte Teilflächenentnahme gepinnt; keine Pufferung oder
Aufweitung der privaten Zellautorität. `test_metric_partial_reference.py` und
die gesicherten Originalraster prüfen Lokalisierungskorrektur ohne neue
Beobachtung, wirkliche Zellbeobachtung/Regrowth und ganzzahliges Body-Wachstum.
`test_metric_join_replan.py` prüft den echten Elternpfad einschließlich
Kindcancellation, unveränderter Aufgaben-ID/Budgets und erneutem exakten Join.

Physische Welt und originale simulierte Encoder-/HWT-/Nahbereichsquellen
laufen in einem separat gestarteten Prozess. Prüfsteuerung und passive
Beobachter sind davon getrennt. Kein verlorenes Sensorsample wird nachgebaut.
`test_ap06_device_isolation.py` hält den Interpreter der Prüfsteuerung tatsächlich
400 ms in einem nativen Aufruf fest; die ursprünglichen Messungsstempel und
Encoderprüfungen im anderen Prozess müssen innerhalb 180 ms fortlaufen.
`device_result.json` und die Originalstatusmeldungen enthalten echte Probezeiten.
`test_ap06_lifecycle.py` verwirft gezielt nur eine Antwort der tatsächlich
ausgeführten Lifecycle-Transition; der Prüfleiter muss den Originalserverzustand
lesen und darf den nicht-idempotenten Zustandswechsel nicht erneut senden.

Die gesicherte native Abfahrtskurve `ap06_native_departure_path.json` und
`test_metric_start_observation.py` zeigen den Unterschied zwischen zusätzlicher
Drehung im Stand und tatsächlicher RPP-Kurvenfahrt. Nur der simulativ
qualifizierte Rollout-Modus überlässt diese bewiesene Abfahrt dem ursprünglichen
Controller. Die bisherigen 17 Controllerparameter und das zusätzliche
`general_goal_checker.stateful=false`, die 0,35-rad-Drehschwelle, vollständige
Kontur und 20-mm-/0,05-rad-Trackingreserve bleiben verbindlich. Vor dem nativen
Plan wird der ausgewählte Vorschlag frisch geprüft; danach zählt ausschließlich
der volle Beweis des tatsächlich zurückgegebenen Nav2-Pfads.

Der Prüfleiter weist bei mindestens vier verfügbaren CPUs einer CPU nur den
Geräteprozess und bis zu drei weiteren CPUs dem ROS-Graph zu. Diese begrenzte
Zuordnung trennt die Quellausführung von bis zu drei Graph-CPUs in der
Prüfumgebung mit übergeordneter Vier-CPU-Quote. Sie
ändert weder Frequenzen noch Fristen und ist keine Echtzeitgarantie.
`cpu_allocation`, `device_result.actual_cpu_affinity` und
`device_executor_latency.jsonl` halten die tatsächliche Zuordnung und
Executorlaufzeiten fest. Messlücken bleiben unverändert harte Gegenfälle.

Der Quellprozess importiert keine unbenutzte Explorer-/Geometrie-Runtime.
Latenzdiagnosen halten Wand-, Prozess- und Thread-CPU-Zeit getrennt fest;
eine Wandzeitlücke allein beweist weder CPU-Drosselung noch Garbage Collection.
Der metrische Guard und das Mapping-Fahrtor empfangen vor ihrer Entscheidung
die aktuell vorhandene originale Wheel-DDS-Probe ohne neuen Stempel. Der
gesonderte HOLD-Test verwendet auch getrennte Gesundheitsobjekte: ein nur vom
Tor beobachteter Ausfall muss das Kind beenden und den bestehenden validierten
HOLD-/RESUME-Ablauf auslösen. Die Gesamtmission erhält keinen gesunden Ersatz.

## NavFn-Zellmitten und öffentliche Vorausrichtung

Die AP-06-Vorbereitung wendet `patches/nav2_navfn_humble_cell_centers.patch` auf den unveränderten Nav2-Pin an. Der reale Kostenrasterindex wird in die Zellmitte übersetzt; Weltpunkte verwenden die tatsächlich enthaltende Zelle. Originalradius, Kontur und alle Fristen bleiben erhalten. Direkter Test gegen das tatsächlich gelinkte Plugin ohne Node-/Aktorstart:

```bash
source /tmp/ap06/native-install/setup.bash
cmake -S tools/simulation/navfn_cell_regression -B /tmp/ap06/navfn-cell-regression
cmake --build /tmp/ap06/navfn-cell-regression -j2
ctest --test-dir /tmp/ap06/navfn-cell-regression --output-on-failure
```

Der Explorer nutzt vor einer Fahrt die bestehende öffentliche Vorausrichtung nur als vollständig geprüfte Abhilfe für einen sonst unzulässigen nativen Sweep. Die erste private Abfahrt und die Liveprüfung eines aktiven Kindes bleiben native; keine fiktive erneute Drehung. Native Komponentenwerkzeuge übergeben dafür ihre tatsächlichen Eingaben an denselben vorhandenen Alignmentpfad. Alle Resultate bleiben Software-/Komponentenbelege, keine Hardwarequalifikation.

## Teilbeobachtung und verlustfreie Nachweise, 06.10.2026

Ein tatsächlicher Kartenfortschritt schließt eine Aufgabe erst ab, wenn ihre
ursprünglichen Beobachtungszellen alle auf der neueren, geometrisch passenden
Karte bekannt sind. Teilbeobachtete Aufgaben behalten ihren bisherigen
Versuchszähler und Cooldown. Ihre noch wirklich vorhandenen kleinen Frontier-
Komponenten bleiben innerhalb des bestehenden lokalen Radius sichtbar;
zusätzliche Tangentialblicke werden durch dieselben Sicht-, Kontur-, Pfad-
und Zeitprüfungen geprüft. Vollständig bewiesener Scope-Abschluss kann solche
Teilaufgaben innerhalb des bisherigen Abschlussfensters auflösen; daraus
entstehen keine zusätzlichen Beobachtungs- oder Ankunftszähler.

Der passive Beobachter schreibt alle ursprünglichen Ereignisbytes in einen
Gzip-Stream. `events.jsonl.gz.meta.json` hält die unkomprimierte Länge und SHA256;
`ap06_trace.verify_trace` prüft den abgeschlossenen Stream anschließend offline.
`progress.json` ist eine alle fünf Sekunden aktualisierte lesende Statuskopie.
Die Diagnoseoption `--capture-decisions` zeichnet tatsächliche Auswahleingaben
auf und setzt ebenfalls `manifest_compatible=false`; reguläre Abnahmen nutzen
keine Diagnoseoption. Der Vorlauf verlangt mindestens 1184 MiB freien Platz:
512 MiB Tracebudget, 64 MiB Zusatzlogs, 32 MiB temporäre Karte, den unveränderten
512-MiB-Kartenspeicher-Mindestplatz und 64 MiB Reserve. Dies ist eine
Kapazitätsplanung; tatsächliche Ressourcenfehler bleiben negativ.

Eine bereits nach den ursprünglichen Regeln zulässige öffentliche Beobachtung
kann im Rest ihres unveränderten 0,5-s-Hilfsfensters entlang der gemessenen
Randnormalen/Tangenten verfeinert werden. Die zusätzliche Position muss mehr
endliche ursprüngliche First-hit-Punkte, niedrigere ursprüngliche Kosten und
vollständige öffentliche Drehreserve bieten. Lookup ohne Neuanlage bindet
vorhergesagten Stopp und Idealziel an dieselbe vorhandene Aufgaben-ID;
Cooldown/Versuche/Fehler werden erneut geprüft. Der Native-Plan bleibt vor jeder
Fahrt erforderlich. Der tatsächliche Beobachtungszähler verwendet weiterhin
nur den unveränderten Messgewinn, keine Prognose.
