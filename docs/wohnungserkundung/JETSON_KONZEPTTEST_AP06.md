# AP-06: lokaler Konzepttest auf dem Jetson

Stand 11.10.2026. Der separate ARM64-Jetson-Build v17 aus
`60e894cd6638c2d977b0fca6e352fe7b5aedae44` ist ausgeführt: 14 Pakete,
155 eindeutige bytegleiche Quelle-/Install-Dateien (157 Vergleichseinträge)
und 2.976 Regressionen positiv. Ursprüngliche
vollständige Missionen weiterhin **0/3**. Exakte Quellen/Präfixe/Hashes und
kritische Erkenntnisgrenzen im [Buildreview](AP06_BUILD_REVIEW_20261011.md).
[STATUS](STATUS.md) bleibt der einzige aktuelle Iststand; der aktuelle
[Korrekturauftrag](AGENTENAUFTRAG.md) bestimmt die weitere Reihenfolge.

Die Anleitung beschreibt den separaten Aufbau. Der frühere Kandidat c5d2a9c
und sein Downloadbundle sind historische Belege. Vor den abhängigen realen
Schritten verlangt der aktuelle Auftrag vollständige Softwarequalifikation;
grüner Build/Regression allein erfüllt diese nicht. LAB-1 bleibt gültig,
aktuelle Quellen/Geometrie werden tatsächlich gemessen. Kein Kundenbeleg.

## Separater Quellen- und Installstand

Der Softwarestand mit Dokumentation und synthetischen Prüfberichten ist nach
ausdrücklichem Nutzerauftrag auf GitHub veröffentlicht:
`chris01-byte/Roboter_ws`, Branch `feature/ap06-closed-product-validation`.
In ein neues Verzeichnis klonen, niemals `~/roboter_ws/install` überschreiben.
Die vollständige veröffentlichte Commit-ID aus der Übergabemeldung prüfen.
Anschließend `AP06_SOURCE` auf diesen Checkout,
`AP06_RELEASE` auf ein neues Verzeichnis unter
`~/.local/share/amadeus/releases/` und `AP06_PRIVATE` auf ein privates
Diagnoseverzeichnis außerhalb jedes Git-Checkouts setzen.

Eine saubere Shell verwenden: keine alten ROS-/Python-/LiDAR-/SLAM-Overlays aus
`.bashrc` übernehmen. Der direkte Abruf vom Repository lautet:

```bash
env -i HOME="$HOME" USER="$USER" PATH=/usr/bin:/bin LANG=C.UTF-8 bash --noprofile --norc
export AP06_SOURCE="$HOME/amadeus-ap06-konzept"
export AP06_RELEASE="$HOME/.local/share/amadeus/releases/ap06-$(date -u +%Y%m%dT%H%M%SZ)"
export AP06_PRIVATE="$HOME/.local/share/amadeus/diagnostics/ap06-$(date -u +%Y%m%dT%H%M%SZ)"
git clone --branch feature/ap06-closed-product-validation \
  https://github.com/chris01-byte/Roboter_ws.git "$AP06_SOURCE"
git -C "$AP06_SOURCE" rev-parse HEAD
```

Die letzte Ausgabe mit der vollständigen veröffentlichten Commit-ID vergleichen.
Für den exakten v17-Nachbau den Produktcommit explizit auswählen; spätere
Dokumentationscommits sind kein neu qualifizierter Produktbuild:

```bash
git -C "$AP06_SOURCE" switch --detach 60e894cd6638c2d977b0fca6e352fe7b5aedae44
git -C "$AP06_SOURCE" rev-parse HEAD
git -C "$AP06_SOURCE" status --short
```

Der aktuell gebaute Produktstand ist `60e894cd6638c2d977b0fca6e352fe7b5aedae44`;
die nachfolgenden Übergabecommits ändern ausschließlich Dokumentation/Belege.
Der alte `start_app_erkundung.sh` lädt fest
`~/roboter_ws/install` und eignet sich deshalb nicht als Nachweis dieser
separaten Installation.

Nur für den historischen Stand kann beim Clone statt der GitHub-URL das heruntergeladene
`$HOME/Downloads/roboter-ap06-konzept.bundle` verwendet werden. Dessen eigener
Commit ist in `uebergabe.json` gebunden; die spätere Ergänzung zum GitHub-Abruf
ist darin noch nicht enthalten. Das Übergabeverzeichnis enthält
`uebergabe.json`, `SHA256SUMS`, das Git-Bundle
und ein separates Archiv synthetischer Rohbelege. Nach vollständigem Download
in diesem Verzeichnis `sha256sum -c SHA256SUMS` ausführen. Für den Build genügt
der historische Bundle-Checkout; das Rohbelegarchiv dient der unabhängigen
Auswertung. Dieses alte Bundle enthält v17 nicht; v17 aus Git abrufen.

Im Checkout gelten die gepinnten Quellen und Patches aus
`tools/simulation/ap06_dependencies.json`. Deren Vorbereitung steht in
[README_AP06](../../tools/simulation/README_AP06.md). Die dortige Zwölfpaketliste
für den Gesamtprüfstand für den echten `app_mapping`-Start um `robot_bringup`
und `semantic_map_manager` ergänzen:

```bash
source /opt/ros/humble/setup.bash
cd "$AP06_SOURCE"
mkdir -p "$AP06_RELEASE" "$AP06_PRIVATE"
python3 tools/simulation/prepare_ap06_sources.py \
  --cache "$AP06_RELEASE/downloads" --destination "$AP06_RELEASE/native-src"
mapfile -t AP06_NATIVE_PATHS < <(python3 -c \
  'import json,sys; print("\n".join(json.load(open(sys.argv[1]))["base_paths"]))' \
  "$AP06_RELEASE/native-src/prepared.json")
mapfile -t AP06_PYTHON_PINS < <(python3 -c \
  'import json; print("\n".join(json.load(open("tools/simulation/ap06_dependencies.json"))["python_requirements"]))')
python3 -m pip install --target "$AP06_RELEASE/python" "${AP06_PYTHON_PINS[@]}"
python3 -m pip install --target "$AP06_RELEASE/python" -r src/base_hardware/requirements-modbus.txt
export PYTHONPATH="$AP06_RELEASE/python${PYTHONPATH:+:$PYTHONPATH}"
AP06_PRODUCT_PATHS=(
  src/amadeus_map_identity src/base_hardware src/robot_interfaces
  src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore
  src/robot_navigation src/robot_map_manager src/vl53_near_field
  src/safety_monitor src/amadeus_lidar_bringup
  src/robot_bringup src/semantic_map_manager
)
rosdep check --from-paths "${AP06_NATIVE_PATHS[@]}" "${AP06_PRODUCT_PATHS[@]}" \
  --ignore-src --rosdistro humble
```

Konkret fehlende Systemabhängigkeiten vor dem Build auflösen und protokollieren.
`start_web_gui:=false` vermeidet die Smartphone-GUI; `rosbridge_server` bleibt
Bestandteil von `app_mapping`. `nav_mapping` verwendet zusätzlich
`nav2_behaviors`: dessen tatsächlich aufgelöste Humble-Version dokumentieren,
denn es gehört nicht zu den 31 ausgewählten nativen Quellenpaketen des Gesamtprüfstands.
Die pauschale Installation sämtlicher optionaler `robot_bringup`-Abhängigkeiten
ist kein Ersatz für diese Prüfung. Der echte Modbuspfad benötigt zusätzlich die
separat gepinnten `pymodbus==3.14.0` und `pyserial==3.5`; deshalb der zweite
Pip-Aufruf oben. Diese Abhängigkeit wird nicht von `rosdep` erfasst.
Auch für VL53 müssen die tatsächlich vorhandenen Treiber `smbus2` und
`vl53l5cx.vl53l5cx` beziehungsweise `vl53l7cx` mit Pfad und Version erfasst
werden. Fehlen sie, die konkrete zum lokalen Sensor passende Abhängigkeit
auflösen; diese Anleitung erfindet keine ungetestete Treiber-Pinversion.

```bash
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
bash tools/kartierung/build_ldlidar_stl27l_overlay.sh "$AP06_RELEASE/lidar"
source "$AP06_RELEASE/lidar/install/local_setup.bash"
cmake -S tools/simulation/tf_ownership_probe -B "$AP06_RELEASE/tf-probe-build"
cmake --build "$AP06_RELEASE/tf-probe-build" -j2
```

Alle Befehle und Ausgaben im Release sichern. Native Erweiterungen werden auf
AArch64 neu gebaut; die x86-Prüfsummen sind keine ARM-Binärqualifikation.
In jeder weiteren sauberen Shell dieselben konkreten Releasepfade setzen und
folgende Reihenfolge verwenden:

```bash
source /opt/ros/humble/setup.bash
export PYTHONPATH="$AP06_RELEASE/python${PYTHONPATH:+:$PYTHONPATH}"
source "$AP06_RELEASE/native-install/local_setup.bash"
source "$AP06_RELEASE/lidar/install/local_setup.bash"
source "$AP06_RELEASE/product-install/local_setup.bash"
```
 Die Paketpräfixe und tatsächlich
aufgelösten Module mitprotokollieren. `hwt_diagnose_manifest.py` unterstützt
Profil-/Installnachweise; das neue Scopewerkzeug ergänzt die tatsächlich
aufgelösten Explorer-/Kartenidentitätsmodule und beide Explorerprofile.

## Bestehenden Stack stufenweise starten

Der neue Schalter `start_explorer:=false` hält ausschließlich den Explorer
zurück. Er verändert keine Fahrfreigabe; der bisherige Standard bleibt `true`.
Der erste lokale Vorlauf erfolgt lesend nach LAB-1, mit passender echter
HWT-/Sensorverkabelung und ohne Aktor-Schreibprozess. Der Start verwendet
weiterhin die vorhandenen Launchdateien. `operator_stationary_confirmed`
nur nach tatsächlich beobachtetem Stillstand setzen; der HWT-Vorlauf braucht
diese technische Anfangsbedingung:

```bash
ros2 launch robot_bringup app_mapping.launch.py \
  use_hwt601_odometry:=true active_drive:=false enable_auto_explore:=false \
  hwt_development_contract:=true operator_stationary_confirmed:=true \
  start_web_gui:=false start_explorer:=false
```

Der lokale LAB-Bereich muss als tatsächlich geprüftes Polygon im aktuellen
Kartenframe vorliegen. Das neue Werkzeug erfindet weder diese Koordinaten noch
den Kartenbezug. Schema, aktueller Fingerprint, Fehlerfälle und genauer Aufruf
stehen unter [Scopevorbereitung](../../tools/kartierung/README.md#aktuellen-metrischen-lab-scope-lesend-vorbereiten):

```bash
python3 "$AP06_SOURCE/tools/kartierung/metric_scope_vorbereiten.py" \
  --scope "$AP06_PRIVATE/lab-scope.json" \
  --output "$AP06_PRIVATE/metric-current.yaml" \
  --install-root "$AP06_RELEASE/product-install" \
  --tf-probe "$AP06_RELEASE/tf-probe-build/tf_ownership_probe"
```

Das Werkzeug erzeugt ein neues privates Profil mit Modus `0600` und zeigt den
passiven Start des vorhandenen Explorers an. Diesen bei weiterlaufendem Stack
mit genau diesem Profil ausführen. Ein bereits vorhandener Explorer verhindert
die Vorbereitung; es wird keine zweite Instanz gestartet. Nach Karten- oder
Stackwechsel neu binden. Zwischen Ausgabe und Explorerstart kann sich die
Karte ändern; dann ist die alte Bindung ungültig und muss neu erzeugt werden.

Die Topics, TF, aktuellen Karten-/Kostenkarten, Encoder-/HWT-/Nahbereichszustände
zuerst wie im [Konzeptprotokoll](KONZEPTVERSUCH_AP06.md#übergang-zum-realen-roboter)
aufzeichnen. Das ist ein passiver Integrationsnachweis, noch keine bewegte
Abnahme. Er bestätigt auch noch nicht die Eignung enger Modelltoleranzen.

## Was vor dem bewegten Vergleich gemessen werden muss

| Unterschied | Tatsächliche Bedeutung |
|---|---|
| Modellprofil `rpp_rollout`, lokal zunächst `conservative` | Das neue Scopewerkzeug aktiviert absichtlich keine ungemessenen Hardware-Trackingreserven. RPP als Nav2-Controller ist bereits konfiguriert; dessen mathematischer Explorer-Nachweis ist ein eigener Vertrag. |
| Modell 20 mm / 0,05 rad Tracking, 0,02 rad Ausrichtungsübergabe | Reale Encoder-/TF-Zeitbindung, Nachlauf und Richtungsfehler messen. Das reale Basisprofil verwendet zunächst 0,17 rad Übergabe und 0,10 rad Stoppmarge. |
| Modellantrieb 50 ms Zeitkonstante, echte Rampen 2000/400 ms | Brems- und Drehverhalten nicht aus dem Modell ableiten. |
| Synchroner Modell-SLAM, asynchroner echter SLAM | Latenz und Karten-/Statusbindung unter tatsächlicher Last prüfen. |
| Modellierte endliche OAK-Punkte, OAK im echten Mappinglaunch deaktiviert | Die tatsächlich vorhandene Nahfeld-/Hindernisabdeckung messen und eine Sensorvariante ausdrücklich festlegen; keine Ersatzpunkte einspeisen. |
| Konzept ohne Mastmaske, echter Aufbau mit Mast | Den echten Abschattungsbereich messen; `crop:=false` entfernt den physischen Mast nicht. |

Die neue phasengetrennte Drehprüfung und öffentliche Kartenfortsetzung sind im
Rolloutpfad wirksam. Ein lokaler konservativer Test übt sie nicht automatisch
aus. Erst nach den tatsächlichen Tracking-/Stoppmessungen gehört ein ausdrücklich
als Experiment gekennzeichnetes Hardwareprofil in denselben bestehenden
Launch. Eine geänderte Bewegungswirkung folgt auf den lesenden Vorlauf; nach
einem dafür erforderlichen Stackneustart Scope neu binden, bevor genau ein
Explorer startet. Konkret: beim späteren aktiven Stack `active_drive:=true`,
`enable_auto_explore:=true` und weiterhin `start_explorer:=false` setzen;
anschließend aktuelle Session/Karte unter einem neuen privaten Ausgabepfad
binden und genau einen Explorer mit dazu passendem
`hwt601_active_drive:=true` starten. Der vom Vorbereitungstool ausgegebene
passive Befehl setzt diesen Wert bewusst auf `false` und ist kein aktiver
Startbefehl. Die vorhandenen beiden Fahrtor-Opt-ins bleiben maßgeblich.

Der begrenzte aktive Ablauf nutzt anschließend den bestehenden Mission Manager
(`/mission_manager/command_json`, Befehle `explore` und `cancel`) und dieselbe
Nav2-/Schutzkette. Zuerst selbst gewählten Beobachtungspunkt und Stoppen prüfen,
dann Folgebeobachtungen, ganze Türpassage mit Heck und Weiterarbeit. Daten
bleiben lokal außerhalb Git. Bedienereingriffe gehören ins Versuchsprotokoll;
sie ersetzen keinen autonomen Gesamtpositivlauf. Kundeneinsatzreife folgt erst
aus vollständigen Software- und realen Abnahmen auf einem festgelegten Profil.
