# Übertragung auf den realen Roboter

Verbindlicher Kurzstatus für Änderungen mit Jetson- oder Hardwarewirkung. Die
vollständige Diagnose und alle Befehle stehen in
`docs/SLAM_TOOLBOX_ROTATION_FIX.md`.

## Auftrag: Humble-Fix für reine Drehungen

**Branch:** `agent/slam-toolbox-pure-rotation-fix`

**Basis:** `feature/stl27l-integration`, Commit `7010058`

**Ziel:** gepinntes `slam_toolbox`-Overlay unter
`~/amadeus_slam_toolbox_ws`; `/opt/ros/humble` bleibt unverändert.

### Voraussetzungen

- [ ] `AGENTS.md`, `docs/PROJECT_MEMORY.md` und
      `docs/SLAM_TOOLBOX_ROTATION_FIX.md` vollständig gelesen
- [ ] Jetson-Arbeitskopie `~/roboter_ws` sauber; unbekannte Änderungen geklärt
- [ ] kein RTAB-Map- oder alter `slam_toolbox`-Prozess aktiv
- [ ] keine Geheimnisse, echten Karten oder ROS-Bags für einen Commit vorgemerkt
- [ ] Motorstrom aus; keine Fahrfreigabe vorausgesetzt

### Verbindliche Reihenfolge

```bash
cd ~/roboter_ws
git status --short --branch
git fetch origin
git switch agent/slam-toolbox-pure-rotation-fix 2>/dev/null || \
  git switch --track -c agent/slam-toolbox-pure-rotation-fix \
  origin/agent/slam-toolbox-pure-rotation-fix
git pull --ff-only

source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select amadeus_lidar_bringup
source ~/roboter_ws/install/setup.bash
bash tools/kartierung/build_slam_toolbox_humble_overlay.sh
```

Bei Patch-, Commit- oder Buildabweichung stoppen. Nicht ungepinnt aktualisieren,
nicht `/opt/ros/humble` bearbeiten und einen bestehenden Overlay-Ordner nicht
löschen.

### Source-Reihenfolge in jedem Testterminal

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/amadeus_lidar_ws/install/local_setup.bash
source ~/roboter_ws/install/local_setup.bash
```

Kontrolle:

```bash
ros2 pkg prefix slam_toolbox
```

Muss auf `~/amadeus_slam_toolbox_ws/install/slam_toolbox` zeigen.

### Abnahmestatus

Stand 12.08.2026, abgenommen auf Commit `4fe5ee3`:

- [x] Patch-Preflight (`git apply --unidiff-zero --check`) bestanden
- [x] Overlay gebaut; `colcon test` liefert allerdings **0 Tests** und ist als
      Evidenz wertlos (Testblock im Upstream auskommentiert). Ersatz: Blob-Hashes,
      Release-Build und `strings`-Gegenprobe am Binärpaket
- [x] Paketpräfix und gepinnter Humble-Commit kontrolliert
- [x] Stillstand: `dry_run=true`, `allow_rs485=false`
- [x] Stillstand: neuer Parameter `true`, keine Knotenflut, `/scan` 9,99 Hz
- [x] Synthetischer Yaw-only-Regressionstest ergänzt:
      `tools/kartierung/test_reine_drehung_synthetisch.py`, A/B 37 gegen 0
- [x] ausdrückliche Fahrfreigabe der anwesenden Person erteilt
- [x] Not-Aus in Reichweite, Fläche frei, Beobachter anwesend
- [x] 360°: mehr als null neue Posegraph-Knoten (1 → 11), Karte sichtbar ergänzt
      (freie Fläche 10,8 → 23,2 m²)
- [ ] **offen und vorrangig:** Wände der Nachher-Karte sind versetzt mehrfach
      eingetragen (Wand/frei 0,041 → 0,115). Nächster Schritt ist eine Messung,
      keine Parameteränderung: dieselbe Drehung bei 0,20 statt 0,30 rad/s
      wiederholen und vergleichen
- [ ] 40 cm Translation: weiterhin Kartenupdate, keine Doppelwände
- [ ] langsame geschlossene Runde: keine Odometrie-/TF-/USB-Regression
- [x] Testergebnis mit Datum und Commit in `docs/PROJECT_MEMORY.md` ergänzt

**Phase 4 ist nicht freigegeben**, solange die Wandverschmierung nicht
eingegrenzt ist. Der Backport selbst funktioniert nachweislich; die
Verschmierung ist ein zweiter, davon unabhängiger Befund, den der Backport erst
sichtbar gemacht hat.

**Keine Aktoren aktivieren, bevor alle Stillstandsprüfungen oberhalb bestanden
sind.** Ein KI-Agent darf die Fahrfreigabe nicht selbst annehmen.

### Rollback

Launch einmal sauber mit `Ctrl-C` beenden. Dann eine frische Shell verwenden
und das Overlay nicht sourcen:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 pkg prefix slam_toolbox
```

Das Präfix muss wieder `/opt/ros/humble` sein. Der Overlay-Ordner bleibt zur
Analyse erhalten; keine Datenlöschung ist erforderlich.
