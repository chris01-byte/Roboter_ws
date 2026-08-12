# SLAM-Toolbox: reine Drehungen unter ROS 2 Humble

**Stand:** 12.08.2026

**Zielsystem:** Amadeus, Jetson, Ubuntu 22.04, ROS 2 Humble

**Ausgangsbranch:** `feature/stl27l-integration`, Commit `7010058`

**Implementierungsbranch:** `agent/slam-toolbox-pure-rotation-fix`

Dieses Dokument ist die verbindliche Übergabe für den Agenten, der den Fix auf
dem Jetson installiert und abnimmt. Vorher auch `AGENTS.md`,
`docs/PROJECT_MEMORY.md`, `docs/INVENTORY.md` und
`docs/hardware/STL27L_INTEGRATION.md` vollständig lesen.

## 1. Ergebnis in einem Satz

Der STL-27L, sein USB-Treiber, die Totzonenmaske und der TF-Baum sind nicht die
Ursache dafür, dass eine Karte bei einer Drehung auf der Stelle unverändert
bleibt. Der Vorfilter von `slam_toolbox` im ROS-2-Humble-Zweig verwirft solche
Scans anhand der Translation, bevor Kartos vorhandene Winkelschwelle sie
annehmen kann.

Der Produktionsfix ist ein reproduzierbarer, gepinnter Backport des bereits
offiziell gemergten Upstream-Fixes. `minimum_travel_distance: 0.0` ist dagegen
nur ein Diagnosetrick und **keine** dauerhafte Lösung.

## 2. Zwei getrennte Fehlerbilder

### A. Versetzte oder doppelte Wände während längerer Fahrten

Dieses Fehlerbild war eine Odometrie-Kalibrierung und ist bereits weitgehend
behoben:

- vorher: Wände zwei- bis dreifach versetzt, Scan-Match-Mittelfehler 43 mm;
- kalibrierte Werte: `wheel_radius_m: 0.0612` und
  `wheel_separation_m: 0.3755`;
- nachher: Scan-Match-Mittelfehler 6 mm, Winkelfehler etwa 0,50° je voller
  Umdrehung und keine sichtbaren Wandüberlagerungen;
- zugehöriger Commit: `9e8c06f`.

Diese beiden Kalibrierwerte bei der Installation des vorliegenden Fixes **nicht
ändern**. Erst nach einem getrennten, korrigierten Odometrie-Versuch erneut
bewerten.

### B. Keine neuen Kartendaten bei reiner Drehung

Dieses Fehlerbild ist der Gegenstand des Backports und war auf Commit `7010058`
noch offen. Gemessen wurde innerhalb desselben SLAM-Laufs:

- 360° Drehung auf der Stelle: **0 von 29.640 Kartenzellen verändert**;
- anschließend 40 cm Translation: **2.410 Kartenzellen verändert**;
- TF `odom -> base_link` drehte während des Versuchs plausibel mit;
- `mode: mapping`, `use_scan_matching: true`,
  `minimum_travel_heading: 0.15` und `minimum_travel_distance: 0.01` waren am
  laufenden Knoten gesetzt;
- Totzonenfilter an oder aus änderte den Befund nicht;
- Scanrate, USB-Verbindung und LiDAR-Prozess blieben stabil.

Damit sind Sensorstillstand, falsches Mapping-Mode, fehlende Odometrie und die
Mastmaske als Ursache dieses **Null-Updates** ausgeschlossen.

## 3. Exakte Root Cause

Im Humble-Zweig führt `SlamToolbox::shouldProcessScan()` vor dem Karto-Mapper
einen eigenen Bewegungsfilter aus. `last_pose.SquaredDistance(pose)` verwendet
nur die kartesische Position; die Orientierung ist nicht Teil dieser Distanz.
Bei einer idealen Drehung auf der Stelle gilt daher immer:

```text
translation = 0
translation < minimum_travel_distance
=> Scan wird vor Karto verworfen
```

Karto selbst besitzt eine richtige Prüfung auf Mindeststrecke **oder**
Mindestwinkel. Sie wird für diesen Scan aber nie erreicht. Daher hilft auch
`minimum_travel_distance: 0.01` nicht: 1 cm ist klein, aber bei idealer reiner
Drehung bleibt die Translation kleiner als jede positive Schwelle.

Offizielle Nachweise:

- Fehlerbericht: [slam_toolbox Issue #807](https://github.com/SteveMacenski/slam_toolbox/issues/807)
- offizieller Fix: [slam_toolbox Pull Request #808](https://github.com/SteveMacenski/slam_toolbox/pull/808)
- gemergter Upstream-Commit:
  [`649a50eae698396c40352619c95cd20e2ea1790a`](https://github.com/SteveMacenski/slam_toolbox/commit/649a50eae698396c40352619c95cd20e2ea1790a)

Der Fix ergänzt:

1. den Schalter `check_min_dist_and_heading_precisely`;
2. einen Karto-Getter für `minimum_travel_heading` in Radiant;
3. eine normalisierte Winkeldifferenz, korrekt auch am Übergang `-pi/+pi`;
4. die beabsichtigte Annahme eines Scans, sobald **Distanz oder Winkel** die
   jeweilige Schwelle erreicht;
5. unverändert die Sperre der ersten Scans zur Initialstabilisierung.

Der Fix ist auf neueren Upstream-Zweigen vorhanden, jedoch nicht im für Amadeus
eingesetzten Humble-Zweig. Deshalb wird nicht ungepinnt `ros2` oder ein
beliebiger neuer Branch eingebaut.

## 4. Reproduzierbare Backport-Artefakte

| Datei | Aufgabe |
|---|---|
| `vendor_slam_toolbox_humble.repos` | pinnt den bekannten Humble-Quellstand |
| `patches/slam_toolbox_humble_pure_rotation.patch` | minimaler, prüfbarer Backport von Upstream `649a50e` |
| `tools/kartierung/build_slam_toolbox_humble_overlay.sh` | importiert, prüft und baut das separate Overlay |
| `src/amadeus_lidar_bringup/config/slam_toolbox_amadeus.yaml` | aktiviert den neuen Schalter ausdrücklich |
| `tools/kartierung/slam_knoten_beobachten.py` | zählt echte Posegraph-Knoten statt alle Marker |
| `tools/kartierung/slam_graph_marker.py` und `test_slam_knoten_beobachten.py` | ROS-unabhängiger Regressionstest für die Markerzählung |

Das Ziel des Buildskripts ist standardmäßig
`~/amadeus_slam_toolbox_ws`. Es verändert **nicht** die apt-Installation unter
`/opt/ros/humble` und darf keine Dateien des bestehenden
`~/roboter_ws` überschreiben.

Der gepinnte Humble-Basiscommit ist
`51a99767b3e2ed4076ae5763ff14b69343ffd884`. Das Buildskript muss vor dem Bau
den tatsächlich ausgecheckten Commit prüfen und
`git apply --unidiff-zero --check` ausführen.
Bei einer Abweichung oder einem Patch-Konflikt gilt: **abbrechen, nicht
improvisieren und nicht auf einen beliebigen Upstream-HEAD wechseln.**

## 5. Installation auf dem Jetson

### 5.1 Voraussetzungen und Git-Stand

Keine ROS- oder Fahrprozesse dürfen laufen. Motorstrom bleibt aus. Unbekannte
lokale Änderungen werden weder überschrieben noch automatisch gestasht.

```bash
cd ~/roboter_ws
git status --short --branch
git fetch origin
```

Wenn `git status --short` Änderungen zeigt, hier stoppen und deren Eigentümer
klären. Bei sauberem Stand den Implementierungsbranch auschecken:

```bash
git switch agent/slam-toolbox-pure-rotation-fix 2>/dev/null || \
  git switch --track -c agent/slam-toolbox-pure-rotation-fix \
  origin/agent/slam-toolbox-pure-rotation-fix
git pull --ff-only
git log -1 --oneline
```

Dieser Branch basiert auf `feature/stl27l-integration`. `main` enthielt beim
Erstellen dieser Übergabe noch **keine** STL-27L-Integration. Deshalb die
Änderung nicht isoliert direkt auf den alten `main`-Stand kopieren.

### 5.2 Projektpaket und Overlay bauen

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select amadeus_lidar_bringup
source ~/roboter_ws/install/setup.bash
bash tools/kartierung/build_slam_toolbox_humble_overlay.sh
```

Das Skript führt den Patch-Vorabtest und den Build von `slam_toolbox` aus. Einen
bestehenden Overlay-Ordner bei einem Fehler **nicht löschen**. Ausgabe sichern
und Ursache prüfen.

In jedem Terminal gilt anschließend genau diese Source-Reihenfolge:

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/roboter_ws/install/local_setup.bash
```

Das gepatchte Drittanbieter-Overlay liegt damit über der apt-Version; das
Amadeus-Workspace wird anschließend mit `local_setup.bash` darübergelegt,
ohne seine beim Bau gespeicherte Underlay-Kette erneut zu laden.

### 5.3 Herkunft nachweisen

```bash
ros2 pkg prefix slam_toolbox
git -C ~/amadeus_slam_toolbox_ws/src/slam_toolbox rev-parse HEAD
git -C ~/amadeus_slam_toolbox_ws/src/slam_toolbox diff --check
```

Erwartet:

- Paketpräfix liegt unter
  `~/amadeus_slam_toolbox_ws/install/slam_toolbox`, nicht unter
  `/opt/ros/humble`;
- `HEAD` ist der oben angegebene gepinnte Humble-Commit;
- `git diff --check` meldet keinen Whitespace-Fehler. Ein Quell-Diff durch den
  angewendeten Patch ist dagegen erwartet.

## 6. Abnahme – strikt in dieser Reihenfolge

### Phase 0: Kein konkurrierendes SLAM

RTAB-Map und `slam_toolbox` dürfen nie gleichzeitig `map -> odom` publizieren.

```bash
ros2 node list | sort
ps -ef | grep -E '[r]tabmap|[a]sync_slam_toolbox|[s]ync_slam_toolbox'
```

Vor dem Start darf kein alter SLAM-Prozess erscheinen. Einen unbekannten
Prozess nicht blind abschießen; Besitzer und Startweg klären.

### Phase 1: Build- und Softwareprüfung ohne Hardwarewirkung

Der Patch-Vorabtest (`git apply --unidiff-zero --check`) und `colcon build` im
Buildskript sind
die vorhandene reproduzierbare Softwareprüfung. Zusätzlich:

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
cd ~/amadeus_slam_toolbox_ws
colcon test --packages-select slam_toolbox
colcon test-result --verbose
cd ~/roboter_ws
python3 tools/kartierung/test_slam_knoten_beobachten.py
```

Fehlschläge vollständig protokollieren und unterscheiden: Ein bereits im
gepinnten Upstream vorhandener, umgebungsabhängiger Testfehler ist noch kein
Beweis gegen den Patch, darf aber auch nicht stillschweigend ignoriert werden.
Nicht in einen anderen Quellstand wechseln, um einen Test grün zu bekommen.

Ein vollständig synthetischer LaserScan/TF-Regressionstest ist noch **offen**.
Ein späterer Agent soll ihn ergänzen: festes `base_link`, danach nur Yaw ändern,
gültige synthetische Scans liefern und nachweisen, dass nach 0,15 rad ein neuer
Knoten akzeptiert wird, während Stillstand keine Knotenflut erzeugt. Dieser
offene Test ist kein Grund, vorzeitig Motoren zu aktivieren.

### Phase 2: Stillstandstest am Roboter – Motoren bleiben unscharf

Terminal 1:

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 launch amadeus_lidar_bringup slam_lidar.launch.py active_drive:=false
```

Terminal 2:

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 pkg prefix slam_toolbox
ros2 param get /base_hardware dry_run
ros2 param get /base_hardware allow_rs485
ros2 param get /slam_toolbox check_min_dist_and_heading_precisely
ros2 param get /slam_toolbox minimum_travel_distance
ros2 param get /slam_toolbox minimum_travel_heading
ros2 topic hz /scan
python3 ~/roboter_ws/tools/kartierung/slam_knoten_beobachten.py 30
```

`ros2 topic hz /scan` nach ungefähr 10 Sekunden mit `Ctrl-C` beenden, erst
danach den folgenden Beobachter starten.

Erwartet:

- `dry_run = true`, `allow_rs485 = false`;
- neuer Schalter `true`, Strecke `0.01`, Winkel `0.15`;
- stabiler `/scan` ungefähr bei 10 Hz;
- nach der Startstabilisierung keine fortlaufend wachsende Knotenzahl im
  bewegungslosen Zustand;
- keine TF-Fehlerflut und kein zweiter Publisher für `map -> odom`.

Dieser Test darf beliebig oft wiederholt werden, ohne die Motoren zu
bestromen.

### Phase 3: Begrenzte Drehung – nur nach ausdrücklicher Freigabe

Ab hier entsteht reale Bewegung. Vorbedingungen:

- anwesende Person hat ausdrücklich zugestimmt;
- Not-Aus ist in der Hand und getestet erreichbar;
- niemand befindet sich im Bewegungsbereich;
- der Roboter steht auf freier, ebener Fläche; mindestens Körperradius plus
  Sicherheitsabstand ist rundum frei;
- eine zweite Person beobachtet Kabel, Mast und seitliches Wandern;
- Phase 1 und 2 sind vollständig bestanden.

Terminal 1 neu starten:

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 launch amadeus_lidar_bringup slam_lidar.launch.py active_drive:=true
```

Vorher-Karte sichern:

```bash
mkdir -p ~/.local/share/amadeus/slam_rotation_acceptance
ros2 run nav2_map_server map_saver_cli \
  -f ~/.local/share/amadeus/slam_rotation_acceptance/vor_drehung
```

Terminal 2 beobachtet echte Posegraph-Knoten:

```bash
python3 ~/roboter_ws/tools/kartierung/slam_knoten_beobachten.py 120
```

Erst wenn der Beobachter läuft, in Terminal 3 den vorhandenen, befristeten
Drehtest starten:

```bash
python3 ~/roboter_ws/tools/kartierung/odometrie_drehtest.py 1
```

Das Skript dreht mit 0,30 rad/s, besitzt eine Frist und sendet anschließend
Stoppkommandos. Bei Abweichung, Kabelzug oder ungewöhnlichem Geräusch sofort
Not-Aus betätigen. Die vom Skript ausgegebene automatische Empfehlung für
`wheel_separation_m` **nicht übernehmen**; siehe Nebenbefund unten.

Nachher-Karte sichern und vergleichen:

```bash
ros2 run nav2_map_server map_saver_cli \
  -f ~/.local/share/amadeus/slam_rotation_acceptance/nach_drehung
sha256sum ~/.local/share/amadeus/slam_rotation_acceptance/*.pgm
python3 ~/roboter_ws/tools/kartierung/karten_vergleichen.py \
  ~/.local/share/amadeus/slam_rotation_acceptance/vor_drehung.pgm \
  ~/.local/share/amadeus/slam_rotation_acceptance/nach_drehung.pgm
```

Akzeptanzkriterien:

- Beobachter meldet bei deutlicher Drehung **mehr als null neue Knoten**;
- die beiden PGM-Dateien sind nicht identisch;
- zuvor vom 68°-Mastsektor verdeckte Bereiche werden aus anderen
  Roboterorientierungen ergänzt;
- keine versetzt duplizierten Wände;
- kein TF-, USB- oder Treiberabbruch.

Richtwert, nicht starre Forderung: Bei `minimum_travel_heading: 0.15` sind über
360° theoretisch ungefähr 42 winkelgetriggerte Annahmen möglich. Zeitfilter,
Scanmatching und Initialisierung können die sichtbare Knotenzahl reduzieren.

### Phase 4: Translation und längere Runde – gesonderte Freigabe

Erst wenn Phase 3 bestanden ist, eine kurze Gerade von 0,40 m und danach eine
geschlossene, langsame Runde ausführen. Die existierenden Fahrwerkwerte bleiben
unverändert. Für die kurze, befristete Gerade kann nach erneuter Freigabe
verwendet werden:

```bash
python3 ~/roboter_ws/tools/kartierung/odometrie_streckentest.py 0.40
```

Nur ausführen, wenn mindestens 1 m freie Strecke vor dem Roboter besteht und
der rückwärtige Bereich ebenfalls frei ist. Während der längeren Runde:

```bash
python3 ~/roboter_ws/tools/kartierung/kartenwacht.py 600
```

Danach die Karte speichern und mit einer bekannten guten Karte über
`karten_vergleichen.py` prüfen. Erwartet werden weiterhin einzelne dünne
Wandlinien; der nach der Odometrie-Kalibrierung gemessene Wand/frei-Richtwert
lag etwa bei `0.052`, gegenüber `0.091` vor der Kalibrierung. Der Wert ist ein
Regressionsindikator, keine universelle Grenznorm.

## 7. Rollback

Der Backport verändert `/opt/ros/humble` nicht. Der schnellste, vollständig
reversible Rückfall ist eine neue Shell, in der das Overlay nicht gesourct
wird:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 pkg prefix slam_toolbox
```

Erwartet ist dann `/opt/ros/humble`. Keine laufenden ROS-Prozesse übernehmen
den geänderten Suchpfad nachträglich; laufenden Launch zuerst sauber mit einmal
`Ctrl-C` beenden und den Neustart aus der frischen Shell durchführen.

Für den vollständigen Projektrollback auf den letzten dokumentierten
LiDAR-Stand:

```bash
cd ~/roboter_ws
git status --short --branch
git switch feature/stl27l-integration 2>/dev/null || \
  git switch --track -c feature/stl27l-integration \
  origin/feature/stl27l-integration
git pull --ff-only
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select amadeus_lidar_bringup
```

Nur bei sauberem Worktree wechseln. Das Overlay-Verzeichnis nicht löschen; es
kann durch Weglassen der Source-Zeile deaktiviert und später untersucht werden.

## 8. Offene Nebenbefunde – nicht mit diesem Fix vermischen

### Scanzeitstempel und fehlendes Deskew

Der gepinnte LDROBOT-Treiber versieht einen abgeschlossenen Scan mit
`node->now()` und liefert bei ungefähr 10 Hz einen rund 100 ms langen Scan.
`slam_toolbox` ordnet den kompletten Scan im Wesentlichen einer Roboterpose zu;
eine beamweise Bewegungsentzerrung ist in diesem Pfad nicht nachgewiesen.

Während 100 ms dreht Amadeus bei 0,30 rad/s um etwa 1,72°, bei 0,20 rad/s um
etwa 1,15°. Das kann Wände bei schnellen Drehungen verbreitern, erklärt aber
**nicht** die gemessenen null Kartenupdates. Später getrennt untersuchen:

1. Semantik des Treiber-Zeitstempels gegen das Sensordatenblatt prüfen;
2. Beginn/Mitte/Ende des Scans eindeutig definieren;
3. Deskew oder langsamere Kartierdrehung A/B-testen;
4. für reguläre Kartierung zunächst höchstens etwa 0,20–0,25 rad/s verwenden.

### Odometrie-Drehtest: Korrekturformel und Vorzeichen

`tools/kartierung/odometrie_drehtest.py` schlägt derzeit sinngemäß

```text
wheel_separation_neu = wheel_separation_alt * echt / odometrie
```

vor. Für das übliche Differentialantriebsmodell
`omega = (v_rechts - v_links) / wheel_separation` ist die nötige Korrektur für
denselben Radhub invers. Außerdem muss das Vorzeichen der zyklischen
LiDAR-Verschiebung für beide Drehrichtungen geprüft werden. Deshalb:

- automatische Kalibrierempfehlung vorerst nicht anwenden;
- vorhandene, praktisch erfolgreiche Werte `0.0612` und `0.3755` beibehalten;
- später CW und CCW separat fahren, Bodenmarke/externes Maß gegenprüfen und
  Formel mit einem Unit-Test absichern.

Dieser Nebenbefund kann die Kartenqualität beeinflussen, ist aber nicht die
Ursache dafür, dass reine Drehungen bisher vollständig verworfen wurden.

## 9. Was in Git gehört – und was nicht

In Git gehören Patch, Manifest, Buildskript, Konfiguration, Tests und dieses
Protokoll. Nicht in Git gehören:

- echte Wohnungs-PGM/YAML-Dateien;
- ROS-Bags mit Wohnungs- oder Kameradaten;
- Logs mit Netzwerkdaten;
- GitHub-Token, WLAN-Daten oder andere Geheimnisse;
- der gebaute Overlay-Workspace.

Erst nach bestandener Phase 1 bis 4 darf der Implementierungsbranch in den
LiDAR-Integrationsbranch übernommen werden. Ein Merge nach `main` muss die
gesamte STL-27L-Integrationshistorie einschließen, nicht nur diesen Patch.
