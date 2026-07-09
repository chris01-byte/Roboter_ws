# Roboter-Projekt — PRÜFPLAN (FINAL)

Version 2.0 · Stand: 08.07.2026
**Dies ist der EINZIGE gültige Prüfplan.** Ausführendes Werkzeug: `pruefplan_jetson.sh`
(gleicher Ordner). Ältere Fassungen (HTML, „Server/Jetson/Smartphone"-Dokumente) sind
ersetzt. Ergebnisse landen automatisch in `~/pruefplan_ergebnisse.md`.

---

## Teil 1 — SOFTWARE-FINAL (ohne Hardware, vollautomatisch, ~10 min)

Ein einziger Befehl, keine Rückfragen:

```bash
cd ~/roboter_ws
./pruefplan_jetson.sh --software
```

Läuft der Reihe nach und beweist die komplette Software-Kette:

| Stufe | Beweist |
|---|---|
| B0 | Clean-Build aller Pakete (räumt vorher macOS-Reste weg) |
| B0b | Alle 16 Pakete + AMENT-Hooks korrekt installiert |
| A1 | Pick&Place-Trockenlauf (Mocks) endet mit SUCCESS |
| K1 | Missionsbrücke: Auftrag → mission_manager → BT → success (echt, keine Simulation) |
| K2 | Objektgedächtnis: get_object_pose antwortet aus dem Weltmodell |
| K4 | Not-Aus-Wächter: /safety/estop frei by default + reagiert auf Anforderung |
| K5 | Offboard-Guard: Serverausfall löst KEINE ungewollte Erkundung aus |
| N1 | Echtes Nav2 erreicht ein Ziel in der Testwohnung (virtuelle Basis) |
| N2 | KÖNIGSTEST: kompletter Auftrag mit echter Nav2-Fahrt bis zur Katalog-Ablage |
| D2 | handeye_calibration-Paket bereit (Kalibrierlauf folgt mit echtem Arm) |

Voraussetzungen (einmalig): `sudo apt install ros-humble-navigation2 ros-humble-rosbridge-server`
(+ `behaviortree_ros2` aus Source, liegt bereits im Jetson-Workspace).

**Bestanden = alle Zeilen im Protokoll `OK`.** Damit ist der Software-Stand abgenommen.

## Teil 2 — Bedienoberflächen (mit Mensch, je ~2 min)

```bash
./pruefplan_jetson.sh --stage D1    # Cartoon-Gesicht auf dem 7-Zoll-Display
./pruefplan_jetson.sh --stage B4    # Smartphone-GUI: iPhone verbinden, Auftrag senden
```
Am iPhone zusätzlich prüfen: Erkunden-Tab, NOT-AUS-Knopf (gegen K4), KI-Pill.

## Teil 3 — HARDWARE (erst wenn montiert; Sicherheitsregeln beachten!)

Reihenfolge einhalten, nichts überspringen:

```bash
./pruefplan_jetson.sh --stage B1-RViz     # URDF/TF-Baum sichtbar
./pruefplan_jetson.sh --stage B1-VL53     # Nahbereichssensoren (I2C)
./pruefplan_jetson.sh --stage B2-OAK      # Kamera-Topics
./pruefplan_jetson.sh --stage B2-RS485    # Motoren SCHARF - NUR AUFGEBOCKT,
                                          # Skript verlangt Sicherheitsphrase
./pruefplan_jetson.sh --stage B3          # Onboard-Gesamtstart
./pruefplan_jetson.sh --stage C1          # Netzwerk Jetson <-> KI-Server
./pruefplan_jetson.sh --stage C2          # Sprache -> Auftrag (qwen2.5)
./pruefplan_jetson.sh --stage C3          # Smartphone -> Mission
./pruefplan_jetson.sh --stage C4          # Nav2-Kette bis Basis (mit SLAM)
```

> **Sicherheit (Teil 3):** Not-Aus erreichbar UND getestet · Motortests nur aufgebockt ·
> immer erst `dry_run: true` · Software-Not-Aus ersetzt NICHT den Hardware-Not-Aus.

## Wenn etwas fehlschlägt

1. Stufe einzeln wiederholen: `./pruefplan_jetson.sh --stage <KÜRZEL>`
2. Log ansehen: `/tmp/pruefplan_logs/` + `~/pruefplan_ergebnisse.md`
3. Häufigste Ursachen: `source install/setup.bash` vergessen · `--` in XML-Kommentaren ·
   navigation2/rosbridge nicht installiert · macOS-`._*`-Dateien (macht B0 automatisch weg).

---
*Historie: v1.x-Checklisten (03.–05.07.) sind in dieser Fassung aufgegangen. Änderungs­stand
des Projekts: `PROJEKT_STATUS.md`.*
