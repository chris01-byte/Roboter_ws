# AP-06 Gesamtprüfung

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
Der Quellbaum erhält den bestehenden Pure-Rotation-Patch; es wird kein Git-HEAD
für extrahierte Archive erfunden. Lizenzen bleiben in den Quellarchiven erhalten.

Die zugehörigen System-/ROS-Entwicklungsabhängigkeiten vor dem Build mit
`rosdep` für genau die in `prepared.json` aufgeführten Paketpfade und die zwölf
Produktpakete auflösen. Dazu gehören BehaviorTree.CPP v3 für Nav2, Boost, Qt,
Ceres/SuiteSparse, GeographicLib, SQLite, ZeroMQ/Fmt, TF-/Nachrichtenpakete
und die deklarierten Python-Pins. `rosdep --ignore-src` muss auch alle vorbereiteten
Quellpakete sehen; kein Fremdprodukt als Navigator verwenden.

```bash
source /opt/ros/humble/setup.bash
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

`commands.jsonl`, `events.jsonl`, Prozesslogs, `plant.jsonl`, Manifestkopie und
`result.json` bewahren Eingang, tatsächlich aufgelöste Präfixe, Quellenzustände
und Ergebnis. Die echte SLAM-Karte wird samt Geometrie separat gespeichert.
Unabhängige Referenzprüfung misst die ganze gepaddete Kontur, Heckfreigabe,
beobachteten Anteil tatsächlicher Referenzzellen und Wandfehler. Eine steigende
freie Zellzahl allein reicht nicht. Erfolg verlangt zusätzlich tatsächlichen
Missionsabschluss, mindestens drei autonome Aufgaben, weitere Karte/Beobachtung
und eindeutig beobachtete TF-Besitzer. Gestoppte/partielle/abgelehnte Läufe
bleiben negativ; sie erfüllen keinen Positivfall.

Der korrigierte Startadapter prüft im bestehenden RPP-/Boundary-/Egress-Opt-in
zusätzlich aktuelle Vorwärtspositionen bis Mindestzielabstand plus vorhandenem
lokalem Suchradius. Nur volle Geometrie und Sicht tatsächlicher Frontieranker
ergeben einen Vorschlag; vor Fahrt bleibt der wirkliche Nav2-Plan verbindlich.
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
