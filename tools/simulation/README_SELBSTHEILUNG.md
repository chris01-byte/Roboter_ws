# Robustheitssimulation Selbstheilung (Abnahmestufe 2)

`sh_robustheit.py` prüft die Hauptlinie `self_healing` in einer geschlossenen
Simulation gegen die vorab festgelegten Störfälle aus
`sh_robustheit_szenarien_v4.json` (Konzept: `docs/wohnungserkundung/
KONZEPT_SELBSTHEILUNG.md` §11, Stufe 2).

**Diese Prüfung ersetzt keine Jetson- oder Realabnahme.** Sie zeigt, ob die
Produktsoftware bei Störungen heilt statt abzubrechen.

## Was echt ist und was simuliert

| Echt (Produktcode, Produktparameter) | Simuliert |
|---|---|
| Missionsmanager, `bt_orchestrator` mit `explore.xml`, Explorer mit `self_healing_params.yaml` und Selbstheilungs-BT | Fahrmodell (AP06-Welt, 50-ms-Antwort, 0,25-s-Watchdog) |
| Nav2: NavFn, RPP, Behavior-Server, BT-Navigator, Glätter; Produkt- und Selbstheilungsparameter | LiDAR-Strahlen mit Mastmaske, 2160 Strahlen, 10 Hz |
| Fahrtor, Kollisionswächter mit Selbstheilungs-Overlay, Safety-Monitor | VL53-Rohdaten (die Matrix-/Wolken-/Statusberechnung ist die unveränderte des VL53-Knotens) |
| Scan-Normalisierung, `slam_toolbox` mit Produktprofil | ideale Odometrie (Standardweg; HWT601/EKF nicht modelliert) |
| Missionsstart wie aus der App: `{"type":"explore"}` | Störungen nach Manifest |

Kein Wahrheits-TF, keine Wahrheitskarte, kein manuell gesendetes Navigationsziel.
Ein unabhängiger Prüfer (Welt) misst Kollisionen einschließlich niedriger
Hindernisse.

## Störfälle

| Szenario | Störung | Erwartet |
|---|---|---|
| `referenz` | keine | Vergleichslauf |
| `sensorluecke` | beide VL53 6 s ohne Daten, während der Fahrt | anhalten, warten (`waiting_for` vl53), weiterfahren |
| `kartenrennen` | LiDAR 8 s ohne Scan, danach einmal eine ältere Karte nach einer neueren | warten, weiterfahren |
| `rechenlast` | 90 s volle Last auf allen Kernen | verzögert, kein Abbruch |
| `hindernis_im_weg` | 10 cm hohes Hindernis 0,9 m vor dem fahrenden Roboter; nur die VL53 sehen es | ausweichen ohne Kontakt |
| `gesperrte_tuer` | rechte Tür schließt, sobald der Roboter in die Verbindung fährt | erreichbaren Teil fertig erkunden, sauberes Ende |

Bestanden nach Manifest v4 (Entscheidungen des Projektinhabers, 22.10.2026), wenn:
- die Mission von selbst endet, sauber mit `exploration_complete` oder
  `usable_partial` („Hilfe benötigt“ zählt in Stufe 2 nicht als Heilung);
- mindestens 95 % der vom Start aus erreichbaren Fläche frei kartiert sind
  (Fläche hinter einer geschlossenen Tür zählt nicht mit);
- keine belegte Kartenzelle weiter als 0,10 m von einer Wand der Welt liegt;
- die Störung ausgelöst und die erwartete Heilung beobachtet wurde;
- keine Kollision und kein Prozessabsturz auftraten.

Versionen (Welt, Budgets und Störungen gleich; Ergebnisse bleiben nach der
Version bewertet, mit der sie liefen):
- v1 `sh_robustheit_szenarien.json`: mindestens zwei erreichte Ziele und eines
  nach der Störung. Traf auch Läufe, deren Karte unterwegs vollständig wurde.
- v2 `sh_robustheit_szenarien_v2.json`: Abdeckung oder sauberes Teilende. Ließ
  einen Lauf mit verbogener Karte (3,3 m) über das Teilende bestehen.
- v3 `sh_robustheit_szenarien_v3.json`: Abnahme wie oben, symmetrische Welt.
- v4 `sh_robustheit_szenarien_v4.json`: Abnahme wie v3 in der Welt mit vier
  festen, unsymmetrischen Möbeln (`welt.zusatz_hindernisse`), unverändert aus
  `experimente/manifest_asymmetrisch.json`. Grund: In der symmetrischen Welt
  schloss `slam_toolbox` in 12 von 43 Läufen falsche Ringe, in der
  unsymmetrischen in 0 von 5 (Entscheidung C).

## Unterschiede zur Jetson-Umgebung (nur Simulation)

Die Simulation läuft in der Cloud mit ROS 2 Jazzy, der Jetson mit Humble.
Angepasst sind ausschließlich Formate und Startmechanik, keine Werte:

1. `sh_robustheit_jazzy.yaml`: Jazzy-Klassennamen der Nav2-Plugins (`::` statt `/`).
2. `jazzy_kompatibel()`: Polygonpunkte des Kollisionswächters als Text statt
   Zahlenliste (gleiche Punkte).
3. `slam_toolbox` ist unter Jazzy ein Lifecycle-Knoten; der Treiber führt
   configure/activate aus wie das Jazzy-Launchfile.
4. `patches/behaviortree_ros2_jazzy_abo_reihenfolge.patch` für BehaviorTree.ROS2
   `6c6aa07` (gleicher Stand wie das Submodul). Unter Jazzy erreichten die
   Not-Aus-Nachrichten den Missionsbaum sonst nie, und jede Mission scheiterte
   beim ersten Takt (`BT FAILURE`, Phase `start`), auch mit 5 s Vorlauf.
   Ursache: Die Callback-Gruppe wurde dem Executor vor dem Abonnement
   hinzugefügt. **Auf Humble (Jetson) tritt das nicht auf; für ein künftiges
   Jazzy-System (etwa HomeMy) ist es relevant.**
5. RMW CycloneDDS wie am Roboter, eigene Domain 231, nur lokal.

## Vorbereitung (Cloud, einmalig)

```bash
sudo apt-get install -y ros-jazzy-nav2-bt-navigator ros-jazzy-nav2-planner \
  ros-jazzy-nav2-navfn-planner ros-jazzy-nav2-behaviors ros-jazzy-nav2-velocity-smoother \
  ros-jazzy-nav2-collision-monitor ros-jazzy-nav2-lifecycle-manager ros-jazzy-nav2-map-server \
  ros-jazzy-slam-toolbox ros-jazzy-behaviortree-cpp ros-jazzy-generate-parameter-library \
  ros-jazzy-control-msgs ros-jazzy-rmw-cyclonedds-cpp
git clone https://github.com/BehaviorTree/BehaviorTree.ROS2.git ext/BehaviorTree.ROS2
git -C ext/BehaviorTree.ROS2 checkout 6c6aa078ee7bc52fec98984bed4964556abf5beb
git -C ext/BehaviorTree.ROS2 apply "$REPO/tools/simulation/patches/behaviortree_ros2_jazzy_abo_reihenfolge.patch"
colcon build --base-paths "$REPO/src" ext/BehaviorTree.ROS2 --packages-up-to \
  explore robot_navigation vl53_near_field safety_monitor amadeus_lidar_bringup \
  bt_orchestrator mission_manager --cmake-args -DBUILD_TESTING=OFF
```

## Lauf

```bash
python3 tools/simulation/sh_robustheit.py --szenario sensorluecke --ausgabe /pfad/zum/lauf
```

Immer nur ein Lauf gleichzeitig (gemeinsame ROS-Domain). `ergebnis.json` enthält:
- Kriterien;
- Fahrtprotokoll mit Ereignissen und Heilungsverlauf;
- Störungszeitpunkte;
- Kollisionsprüfer und minimalen Abstand;
- Kartenvergleich mit der Welt;
- Lifecycle-Zustände nach der Fahrt.

Exitcode 0 = bestanden.

### Diagnose (nur lesend, beeinflusst die Bewertung nicht)

| Feld | Bedeutung |
|---|---|
| `engste_stelle` | Pose, Geschwindigkeit und Zeit beim kleinsten Konturabstand. Unter 3 cm zusätzlich das Hindernis (Wand oder niedrig) und die Belegung der lokalen Kostenkarte darüber (`toedlich`, `eingeschrieben_oder_mehr`, `unbekannt`): Konnte der Regler es kennen? |
| `mitte_engste_stelle` | kleinster Abstand der Robotermitte; unter `robot_radius` (0,28 m) plant NavFn von dort nicht mehr |
| `plan_engste_stelle` | engste Stelle der globalen Pläne, ganz und nur bis 1 m um den Roboter (`nah_…`) |
| `timer_verspaetungen`, `rechnerlast` | Lücken der Anlage mit Zeitpunkt, 1-min-Last je 10 s |
| `kartenfehler_orte` | belegte Kartenzellen weiter als 0,10 m von jeder Wand, mit Weltkoordinaten (gleiche Rechnung wie das Kriterium `karte_plausibel`) |
| `endkarte.npz` | Endkarte der synthetischen Welt (`belegung`, `aufloesung`, `ursprung`) im Laufordner, zum Ansehen |

Kontur der Welt = gepolsterter Nav2-Footprint (x −0,13…0,33 m, y ±0,25 m).
Das echte Chassis liegt rundum etwa 2 cm innerhalb. „Kollision“ heißt hier
also Berührung der Polsterung.

### Experimente

```bash
python3 tools/simulation/sh_robustheit.py --szenario referenz --ausgabe /pfad \
  --experiment kandidat.yaml [--manifest anderes_manifest.json]
```

`--experiment` mischt eine Parameterdatei über das Produktprofil (wie ein
weiteres params-file). Das Ergebnis trägt dann `experiment_keine_abnahme`.
Experimente dienen Entscheidungen; die Abnahme gilt nur ohne `--experiment`
mit dem festgelegten Manifest.

Messexperimente 23.10.2026 zu den Reglerabbrüchen „extrapolation into the
future“ (`map`→`odom` zu alt), beide **widerlegt** und nicht übernommen:
`experimente/x11_tf_vorlauf_05.yaml` (`transform_timeout` 0,5 s; `slam_toolbox`
2.8.5 datiert `map`→`odom` damit nicht vor, Fehlerzahl unverändert) und
`experimente/x12_slam_raster_5cm.yaml` (SLAM-Karte 5 statt 1 cm; Last anfangs
niedriger, Spitzen und Fehlerzahl unverändert, Abdeckung schlechter).
