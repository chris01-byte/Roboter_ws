# Projekt-Status roboter_ws (Stand: 09.07.2026)

**Single Source of Truth.** Zuerst hier lesen, nicht den `src/`-Baum scannen.
Nach jeder Änderung kurz aktualisieren.

## Meilenstein: SOFTWARE-ABNAHME BESTANDEN (08.07.2026, Jetson)
`./pruefplan_jetson.sh --software` — alle 10 Stufen grün: Build (16 eigene Pakete + BT-Source),
Trockenlauf, **K1** Missionsbrücke (Auftrag -> BT echt), **K2** Objektgedächtnis, **K4** Not-Aus-
Wächter, **K5** Offboard-Guard, **N1** echtes Nav2, **N2 Königstest** (Auftrag -> BT -> Nav2
fährt virtuell -> Ablage am Katalog-Ziel -> success), D2. Details: `pruefplan_ergebnisse.md`.
**Alle Software-Befunde des Prüfberichts sind damit geschlossen** (K1,K2,K4,K5,K6,K7,S1,S2,
Pose-Katalog, GUI-Ausbau, Nav2 virtuell). Rest ist hardwaregebunden.

## Betriebs-Fakten (nicht neu herleiten)
- **Eine Kopie:** dieser USB-Stick `/Volumes/64GB/roboter_ws` ist der gesamte Stand.
  Gebaut/getestet wird direkt hier auf dem Jetson (oder in `~/roboter_ws`-Kopie).
- **exFAT kann keine Symlinks** -> B0 erkennt das und baut ohne `--symlink-install`.
- macOS-Reste (`._*`, `.DS_Store`, `__pycache__`) räumt B0 vor jedem Build weg.
- `behaviortree_ros2` liegt als **Source in `src/`** (nicht per apt verfügbar) — nie löschen.
- Es entwickelt NUR Claude (Mac) am Code; „schon erledigt" wirkende Arbeit stammt aus
  eigenen früheren Sessions (5h-Limit). Erst diese Datei prüfen, dann implementieren.
- Nutzer-Feedback: sparsam mit Tokens; Doku aktuell halten statt Stick scannen.
- Konventionen: XML-Kommentare `====` statt `--` · Suchanker statt Zeilennummern ·
  `sw.js` CACHE_NAME bei GUI-Änderungen hochzählen.

## Nächste Schritte (alle hardwaregebunden)
1. **Arm-Integration:** echtes Arm-URDF + `/joint_states` (iCL-Stepper, Projektordner
   „Roboterarm" auf dem Mac) -> dann Hand-Auge-Kalibrierung nach
   `KONZEPT_KALIBRIERUNG_OAK_ARM.md` Stufe A–G (`handeye_recorder`/`handeye_solve` liegen bereit).
2. **OAK montieren -> SLAM (RTAB-Map):** ersetzt Testkarte + statische TF in
   `robot_navigation/nav_test.launch.py`; danach Pose-Katalog mit echter Karte einmessen.
3. **Hardware-Prüfstufen** B1–C4 (`Roboter_Pruefplan.md` Teil 3), inkl. abgesichertem
   RS485-Radtest; VL53-Montagepose einmalig in der URDF festlegen (Prüfbericht I7).
4. Optional/Feinschliff: Live-Detektion vor Gedächtnis bevorzugen, wenn Objekt sichtbar;
   TTS fürs Gesicht (Piper, lokal); `robot_radius` real ~0.43 prüfen (aktuell 0.30 für Testkarte).

## Testen
`./pruefplan_jetson.sh --software` (Abnahmelauf) · `--stage <ID>` einzeln · `--alle` inkl.
Hardware · Menü ohne Argument. Stufenliste: `--hilfe`. Ergebnisse: `~/pruefplan_ergebnisse.md`
(Kopie der Abnahme hier im Workspace).
