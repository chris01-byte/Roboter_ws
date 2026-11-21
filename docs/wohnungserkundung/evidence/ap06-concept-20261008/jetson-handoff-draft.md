## Jetson-Uebergabe: vorhandene Bausteine und noch fehlende Integration

Lesende Bestandspruefung vom 08.10.2026; keine Jetson-Ausfuehrung. Die folgenden
Befehle sind eine aus den vorhandenen Werkzeugen abgeleitete Vorlage, kein
bereits gebauter oder gestarteter Zielsystemkandidat. Das Paket muss zuerst
mit einem eingefrorenen Commit und einem tatsaechlich geprueften lokalen
Laufprofil vervollstaendigt werden. Eine neue allgemeine Laborfreigabe fehlt
nicht.

### Konkrete Unterschiede zwischen Modell und vorhandenem Produktstart

| Punkt | AP-06-Gesamtmodell | Vorhandener echter Start | Praktische Folge / Quelle |
|---|---|---|---|
| Explorerstrategie | `metric_frontier` | Default `existing`; metrisches Basisprofil nur explizit | Ohne lokales Overlay wird nicht die neue Strategie getestet. `src/explore/explore/metric_frontier_runtime.py:57`, `tools/simulation/ap06_closed_product.py:798`. |
| Metrischer Pfadpruefer | `rpp_rollout` | Node-Default `conservative`; `metric_frontier_params.yaml` aendert ihn nicht | Das Modell laedt zusaetzlich `metric_frontier_simulation_params.yaml`. Diese Datei kennzeichnet 20 mm / 0,05 rad ausdruecklich nur als Modellnachweis; nicht ungeprueft zum Hardwareprofil umbenennen. |
| Vorausrichtungsuebergabe | 0,02 rad | 0,17 rad | Rolloutinitialisierung fordert aktivierte Vorausrichtung mit hoechstens 0,02 rad. `src/explore/config/metric_frontier_simulation_params.yaml:8`, `src/explore/config/explore_params.yaml:213`, Runtime `:88`. |
| Vorausrichtungs-Stoppmarge | 0,01 rad | 0,10 rad | Echte Rampe/Encoder- und TF-Latenz muessen diese engere Grenze tragen; eine reine YAML-Uebernahme prueft das nicht. Gleiche Profile. |
| Minimale Ausrichtungsverbesserung | 0,005 rad | 0,04 rad | Der Timeout-/Impulsablauf ist deshalb ebenfalls eine andere konfigurierte Bedingung. Gleiche Profile. |
| Missionsbudget / Fahrfehlerlimit | 900 s / 3 | 1200 s / 6 aus Basisprofil | Der echte Vergleich braucht explizit deklarierte Grenzen; der normale Launch uebernimmt die Modell-CLI-Overrides nicht. `ap06_closed_product.py:805`, `explore_params.yaml:101`. |
| SLAM-Ausfuehrung | `sync_slam_toolbox_node` | `async_slam_toolbox_node` | Gleicher Quellpin bedeutet nicht gleichen Ablauf/Last. `ap06_closed_product.py:772`, `src/amadeus_lidar_bringup/launch/slam_lidar_hwt601.launch.py:143`. |
| OAK-Daten | Endliche modellierte Punktwolke `/oak/points` | `nav_mapping.launch.py` sagt ausdruecklich OAK deaktiviert; beide Nav2-Costmaps nennen OAK weiterhin als Quelle | Der reale Sensorvertrag ist nicht identisch. Im Experiment reale OAK-Einbindung oder ausdruecklich VL53/LiDAR-only-Variante entscheiden und pruefen; keine gesunde Ersatzwolke erzeugen. |
| Mastabschattung | Konzeptprofil `finite-unmasked` entfernt nur die Modellmaske | `crop:=true`; echte Mastgeometrie bleibt | Nicht `crop:=false` auf echter Hardware als Ersatz verwenden. Originalprofil oder gesondert vermessener Sensoraufbau. |
| Antrieb | Zeitkonstante 0,05 s im Weltmodell | Produktregistrierung 2000-ms-Anfahr-/400-ms-Bremsrampe | Seitlicher/Heading-Trackingfehler und Nachlauf sind lokal zu messen; dies ist keine identische Strecke-Zeit-Dynamik. `tools/simulation/ap06_world.py:87`, `src/base_hardware/config/base_hardware_params.yaml`. |
| Scope-/Kartenbindung | Harness liest erste Karte, berechnet Fingerprint und setzt Scope vor Explorerstart | Metrische Beispielwerte leer; `app_mapping` startet Explorer ohne vorgelagerte Kartenbindung | Noch kein direkt kopierbarer metrischer Kaltstart. Fehlender Scope wirft bereits beim Node-Start einen Fehler, nicht erst beim Missionsauftrag. Runtime `:69`, `:96`. |
| Native Plugins | Gepinntes/gepatchtes NavFn, SLAM und gebundene native Artefakte | Alte `start_app_erkundung.sh`-Kette laedt fest `~/roboter_ws/install` sowie aeltere externe Overlays | Neues Release in sauberer Shell explizit aufloesen; sonst kann neuer Pythoncode mit altem Planner kombiniert werden. |

RPP selbst ist auch im echten `nav2_params_real.yaml` konfiguriert: 0,10 m/s,
0,4-m-Lookahead, 0,35-rad-Drehschwelle, `general_goal_checker.stateful=false`.
Der Unterschied betrifft insbesondere den Explorer-Beweis-/Ausrichtungspfad,
nicht das Vorhandensein eines RPP-Controllers.

### Gefundener echter LAB-Pfad

Vorhanden sind `app_mapping.launch.py` -> `nav_mapping.launch.py` ->
`slam_lidar_hwt601.launch.py`, der vorhandene Mission-Manager-Eingang
`/mission_manager/command_json` und die private historische Profilreferenz
`~/.local/share/amadeus/profiles/stage3-real-20260925-after-r2-scope.yaml`.
Spaetere private gebundene Messungen stehen laut STATUS unter
`~/.local/share/amadeus/tests/metric-adaptive-start-20261001/` beziehungsweise
`metric-egress-hwt-20261001/`. Deren Karten/Scopewerte und Hilfsskripte sind im
Repository nicht enthalten; der Offlineauswerter
`metric_start_geometrie_pruefen.py` liest nur bereits erzeugte Snapshots.

**Nicht gefunden:** ein versioniertes echtes RPP-Rollout-LAB-Profil samt
aktueller Scopebindung und ein reproduzierbarer Startpfad, der diese Bindung
vor dem einzigen Explorerstart aus dem tatsaechlich laufenden SLAM erzeugt.
Die genannten realen Messungen sind aelter als das AP-03-Modellprofil und
belegen dessen engere Parameter nicht. Die vorhandenen Process-Smokes und
`metric_frontier_product_graph.py` sind synthetische Pruefstaende, kein
Hardwarebootstrap.

Die kleine benoetigte Startintegration gehoert in den bestehenden Launch:
SLAM/Kartenmanager zuerst, erste tatsaechliche Karte/Pose und lokal festgelegtes
Scope binden, dann genau denselben Explorer mit dem eingefrorenen Profil
starten. Kein zweiter Navigator/Supervisor. Bei Neustart nicht den frueheren
Fingerprint blind wiederverwenden. Der Umfang der lokal erlaubten Flaeche
kommt vom echten LAB-Bereich; die Karte liefert keinen automatischen
Berechtigungsnachweis fuer den ganzen sichtbaren Rasterrand.

### Isolierter Zielsystembuild: passend zu diesem Repository

Vor der Uebergabe wird ein vollstaendiger getesteter Commit als Git-Bundle oder
verfuegbarer Remote-Commit bereitgestellt, inklusive SHA-256 und Quellmanifest.
Ein nicht gepushter Cloud-Branch ist auf dem Jetson nicht automatisch vorhanden.
`AP06_SOURCE` bezeichnet anschliessend den separaten sauberen Checkout dieses
Commits, `AP06_RELEASE` ein neues Verzeichnis unter
`~/.local/share/amadeus/releases/`. Keine alte Installation ueberschreiben.

In einer Shell ohne `.bashrc` und ohne geerbte ROS-/Python-Overlaypfade beginnen,
z.B. `env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin LANG=C.UTF-8 bash --noprofile --norc`.
Dort die konkreten beiden Pfade setzen und den Checkout gegen die gelieferte
vollstaendige Commit-ID vergleichen. Folgende Schritte benoetigen keine Geraete:

```bash
source /opt/ros/humble/setup.bash
cd "$AP06_SOURCE"
python3 tools/simulation/prepare_ap06_sources.py \
  --cache "$AP06_RELEASE/downloads" --destination "$AP06_RELEASE/native-src"
mapfile -t AP06_NATIVE_PATHS < <(python3 -c \
  'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["base_paths"]))' \
  "$AP06_RELEASE/native-src/prepared.json")
AP06_PRODUCT_PATHS=(
  src/amadeus_map_identity src/base_hardware src/robot_interfaces
  src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore
  src/robot_navigation src/robot_map_manager src/vl53_near_field
  src/safety_monitor src/amadeus_lidar_bringup
  src/robot_bringup src/semantic_map_manager
)
rosdep check --from-paths "${AP06_NATIVE_PATHS[@]}" "${AP06_PRODUCT_PATHS[@]}" \
  --ignore-src --rosdistro humble
export MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
colcon --log-base "$AP06_RELEASE/native-log" build --executor sequential \
  --base-paths "${AP06_NATIVE_PATHS[@]}" \
  --build-base "$AP06_RELEASE/native-build" --install-base "$AP06_RELEASE/native-install" \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
  -DBTCPP_UNIT_TESTS=OFF -DBTCPP_EXAMPLES=OFF -DBTCPP_BUILD_TOOLS=OFF
source "$AP06_RELEASE/native-install/local_setup.bash"
colcon --log-base "$AP06_RELEASE/product-log" build --executor sequential \
  --base-paths "${AP06_PRODUCT_PATHS[@]}" \
  --build-base "$AP06_RELEASE/product-build" --install-base "$AP06_RELEASE/product-install" \
  --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON
source "$AP06_RELEASE/product-install/local_setup.bash"
colcon --log-base "$AP06_RELEASE/test-log" test --executor sequential \
  --base-paths "${AP06_PRODUCT_PATHS[@]}" \
  --build-base "$AP06_RELEASE/product-build" --install-base "$AP06_RELEASE/product-install" \
  --return-code-on-test-failure
colcon test-result --test-result-base "$AP06_RELEASE/product-build" --all --verbose
```

Vor diesen Builds sind die von `rosdep check` konkret als fehlend gemeldeten
Abhaengigkeiten auf dem Jetson zu installieren. Die vier Python-Pins aus
`ap06_dependencies.json`, insbesondere Shapely 2.0.7, muessen aus einer
separaten dokumentierten Python-Zielinstallation aufgeloest werden; keine
unbemerkte Uebernahme beliebiger User-Site-Pakete. Native C-Extension und
externe Plugins werden auf aarch64 neu gebaut. Die x86-Manifestdatei benennt
keinen erfolgreichen ARM-Build.

Die zwei zusaetzlichen Produktpakete gegenueber dem zwoelfteiligen
Simulationsbuild sind fuer `app_mapping` noetig. `start_web_gui:=false` vermeidet
hier einen Start von `smartphone_gui`; der Launch braucht weiterhin
`rosbridge_server`. `robot_bringup/package.xml` nennt weitere optionale
Gesamtproduktabhaengigkeiten, die ein pauschaler `rosdep install` mitziehen
wuerde. Genau deshalb zuerst die konkrete Aufloesung protokollieren.
`nav_mapping` startet ausserdem `nav2_behaviors`, das die AP-06-Nativliste nicht
selbst baut; die tatsaechlich aufgeloeste Humble-Version ist gesondert zu
binden oder zum passenden gepinnten Nativbuild hinzuzunehmen.

Fuer den echten LiDAR steht bereits das isolierte Buildwerkzeug bereit:

```bash
bash tools/kartierung/build_ldlidar_stl27l_overlay.sh "$AP06_RELEASE/lidar"
source "$AP06_RELEASE/lidar/install/local_setup.bash"
```

Es verwendet den gepinnten Treiber samt Shutdownpatch. Der oben vorbereitete
SLAM ist bereits gepinnt/gepatcht; nicht zusaetzlich ein unbekanntes altes
`~/amadeus_slam_toolbox_ws/install` darueber sourcen. Alle Build-/Setupbefehle
und ihre Ausgaben werden im Release aufgezeichnet. Die Laufzeitumgebung
sourct danach ausschliesslich Humble, dieses native Overlay, diesen LiDAR
und zuletzt dieses Produktoverlay, jeweils mit `local_setup.bash`.

### Identitaet vor einem passiven Start

`hwt_diagnose_manifest.py` ist nuetzlich, aber allein unvollstaendig: sein
`MODULES`-Register bindet einige HWT-/Gate-/VL53-Dateien; es bindet weder alle
Explorerdateien noch `_reserved_sweep` oder alle Nav2-/SLAM-Artefakte.
Erforderlich ist deshalb die gleiche Quell-/Installpaarpruefung wie im
Softwareversuch, angepasst auf die tatsaechlichen aarch64-Pfade:

- Alle gebauten eigenen Pakete muessen aus `product-install/<paket>` aufloesen;
  `explore.metric_frontier_runtime.__file__`, `explore.explore_node.__file__`
  und `explore._reserved_sweep.__file__` explizit protokollieren.
- Quell-Pythondateien und installierte Pythondateien byteweise vergleichen;
  Konfigurationen, Launchdateien, XML-Baeume, native Erweiterung, NavFn-, RPP-,
  Goalchecker-, SLAM-, EKF- und BT-Artefakte hashen. Native ARM-Hashes duerfen
  von x86 abweichen; die gebundenen Quellen und ausgefuehrten ARM-Tests zaehlen.
- `ldd` auf dem tatsaechlichen `bt_orchestrator` sowie den relevanten Plugins:
  keine fehlenden Bibliotheken und keine alten Releasepfade. Der vorhandene
  NavFn-Zellmitten-Regressionstest laeuft gegen das tatsaechliche Plugin.
- Neues vollstaendiges Zielsystemmanifest neben Build-/Testergebnissen und
  dem noch nicht gestarteten lokalen Profil speichern; nicht nur SHA des
  Cloud-HEAD plus ein altes Installpraefix angeben.

### Passiver erster Realversuch und spaetere Mission

Der erste Passivstart kann das normale Basisprofil verwenden und nur echte
Startdaten aufnehmen. Damit laeuft noch keine metrische Mission; man vermeidet
bewusst den unvollstaendigen metrischen Beispielscope. In der oben gebundenen
Releaseumgebung, nach tatsaechlich festgestelltem Stillstand und vorhandener
LAB-1-Technikpruefung, ist der existierende Start:

```bash
python3 "$AP06_SOURCE/tools/kartierung/roboterknoten.py" --still
ros2 launch robot_bringup app_mapping.launch.py \
  active_drive:=false enable_auto_explore:=false start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true \
  operator_stationary_confirmed:=true normalize_scan:=true crop:=true
```

Der erste Befehl ist nur die vorhandene Prozesswache; zusaetzlich tatsaechliche
ROS-Knoten und USB-Besitzer erfassen. Kein `start_app_erkundung.sh`, da dieses
Skript alte Installpfade nachlaedt. Der Recorder aus dem Konzeptdokument
sichert Karte/Costmap/Scans/TF/Quellen und vier Befehlsstufen. Fuer Zeitkorrelation
zusaetzlich rohe HWT-/korrigierte Gierrate und unabhaengige LiDAR-Odometrie samt
Status aufnehmen. Nur ausgeschriebene Bag-Metadaten nach sauberem Recorderende
auswerten.

Vor dem konkreten metrischen Bewegungsprofil fehlen diese realen Messgroessen:
aktuelle Startpose und Kartenreferenz, tatsaechlich erlaubtes Scopepolygon,
beobachtete unbekannte Rand-/Heckflaeche einschliesslich Reserven, echte
Quellen-/Verarbeitungs-/TF-Zeitversatze, Trackingfehler und Nachlauf bei realen
Anfahr-/Bremsrampen. Daraus ergibt sich die Entscheidung zwischen einem
nachgewiesenen realen Rolloutvertrag und weiter konservativer Ausfuehrung.
Ein Punkt- oder Encodervergleich allein misst keine tatsaechliche laterale
Spurabweichung; dazu ist eine unabhaengige lokale Beobachtung erforderlich.

Nach dieser Bindung bleibt der vorhandene Produktweg gueltig: gleicher Launch
mit `active_drive:=true`, `enable_auto_explore:=true` und dem fertig geprueften
lokalen `explore_params_overlay`, genau ein Mission-Manager-Auftrag, begrenzte
Fristen, aktuelle Quellen-/Kontur-/Stoppruefungen. Auftrag und Cancel erfolgen
ueber die bereits verwendete Schnittstelle, nicht durch direkte Nav2-Ziele:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
  '{data: "{\"type\":\"explore\"}"}'
# Bei beabsichtigtem Ende/Abbruch desselben Versuchs:
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
  '{data: "{\"type\":\"cancel\"}"}'
```

Diese zwei Schnittstellenbefehle sind noch kein fertiger Ablauf: das konkrete
Profil muss den Messergebnissen entsprechen, der Explorer erst nach aktueller
Bindung starten, der Recorder vor Mission bereit sein und das Resultat samt
terminalen Actions/Nullbefehlen gesichert werden. Testgrenzen werden vor dem
Lauf eingefroren. Ein kurzer Konzeptversuch hat ein eigenes Ergebnis und ist
weder eine urspruengliche 900-s-Gesamtmission noch eine Kundenabnahme.
