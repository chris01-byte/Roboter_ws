# Roboter-Projekt — PRÜFPLAN & INBETRIEBNAHME (FINAL)

Version 2.1 · Stand: 13.07.2026
**Das EINZIGE gültige Prüfdokument.** Ausführendes Werkzeug: `pruefplan_jetson.sh`
(gleicher Ordner). Ergebnisse landen automatisch in `~/pruefplan_ergebnisse.md`.

- **Zum ersten Mal am fertigen Roboter?** → Teil A (einmalig, Schritt für Schritt).
- **Nur schnell prüfen, ob die Software noch stimmt?** → Teil B (ein Befehl).

---

## Teil A — ERSTE INBETRIEBNAHME am aufgebauten Roboter

Einmalig, in genau dieser Reihenfolge. **Motoren bleiben bis Schritt 6 stromlos/dry_run.**
Stand: Arm noch nicht montiert → Arm/Greifer bleiben Mocks, Kalibrierung folgt später.

**1. Software auf den Jetson bringen** (Stick steckt):
```bash
STICK="$(findmnt -rno TARGET LABEL=64GB 2>/dev/null || ls -d /media/*/64GB | head -1)"
find "$STICK/roboter_ws" ~/roboter_ws/src \( -name '._*' -o -name '.DS_Store' \) -delete 2>/dev/null
rsync -a --exclude build --exclude install --exclude log --exclude '._*' \
      "$STICK/roboter_ws/" ~/roboter_ws/          # ADDITIV, KEIN --delete!
chmod +x ~/roboter_ws/pruefplan_jetson.sh
```
> `--delete` würde die aus Source gebauten `behaviortree_*`-Pakete löschen.

**2. Hardware-Pakete installieren** (einmalig):
```bash
sudo apt install ros-humble-navigation2 ros-humble-rosbridge-server \
                 ros-humble-joint-state-publisher-gui ros-humble-depthai-ros
python3 -m pip install pymodbus                    # RS485-Antrieb
sudo usermod -aG dialout $USER                     # Zugriff auf /dev/ttyUSB*  (danach neu anmelden!)
```

**3. Software-Abnahme auf DIESER Maschine** (kein Hardware-Risiko, ~10 min):
```bash
cd ~/roboter_ws && ./pruefplan_jetson.sh --software
```
Erst wenn alles `OK` ist, weiter. Das ist das Sicherheitsnetz vor dem ersten Motorlauf.

**4. Anzeigen + NOT-AUS prüfen** (noch immer kein Motorstrom):
```bash
./pruefplan_jetson.sh --stage D1      # Gesicht auf dem 7-Zoll-Display
./pruefplan_jetson.sh --stage B4      # iPhone-GUI verbinden
./pruefplan_jetson.sh --stage B1-RViz # URDF/TF-Baum (Arm noch Dummy)
```
Am iPhone **NOT-AUS drücken und wieder freigeben** — das Gesicht muss auf `alarm` springen
und danach zurück. Diesen Knopf brauchst du gleich als Rückfallebene.

**5. Sensoren real** (rechnet nur, dreht nichts):
```bash
./pruefplan_jetson.sh --stage B1-VL53   # Hand vor die Sensoren halten
./pruefplan_jetson.sh --stage B2-OAK    # Kamera-Topics
./pruefplan_jetson.sh --stage B1-Basis  # Basis im DRY-RUN: /odom rechnet, Motoren still
```

**6. ERSTER MOTORLAUF — nur aufgebockt!** Vorher prüfen:
`ls -l /dev/ttyUSB*` (Port = `rs485_port`?) · Motor-IDs/Register gegen das NEMA23-Manual ·
Not-Aus in Reichweite · **Räder frei in der Luft**.
```bash
./pruefplan_jetson.sh --stage B2-RS485   # verlangt wörtliche Sicherheitsphrase
```
Läuft ein Rad falsch herum: `invert_left`/`invert_right` in `base_hardware_params.yaml`
korrigieren — **nicht** die Verkabelung tauschen. Danach `dry_run: true` /
`allow_rs485: false` zurücksetzen, bis du bewusst wieder fährst.

**7. Erste Fahrt am Boden** (nach bestandenem Rollentest, freie Fläche, Hand am Not-Aus):
```bash
ros2 launch robot_bringup robot.launch.py            # kompletter Onboard-Stack
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.05}}" -r 10   # sehr langsam
```
Der `collision_monitor` bremst über die VL53-Sensoren automatisch ab.

**8. Zusammenspiel** (KI-Server im selben WLAN, gleiche `ROS_DOMAIN_ID`):
```bash
./pruefplan_jetson.sh --stage B3   # Onboard-Gesamtstart
./pruefplan_jetson.sh --stage C1   # Server sichtbar
./pruefplan_jetson.sh --stage C2   # Sprache -> Auftrag
./pruefplan_jetson.sh --stage C3   # iPhone -> Mission
```

> **Sicherheit:** Not-Aus erreichbar UND getestet · Motortests zuerst nur aufgebockt ·
> immer erst `dry_run: true` · Software-Not-Aus ersetzt NICHT den Hardware-Not-Aus ·
> nie allein am fahrenden Roboter arbeiten.

**Noch NICHT möglich (fehlt Hardware/Integration):** autonome Missionsfahrten brauchen SLAM
(RTAB-Map mit der OAK) — bis dahin fährt Nav2 nur virtuell (N1/N2, Testkarte). Arm/Greifer
bleiben Mocks bis Montage + Kalibrierung (`KONZEPT_KALIBRIERUNG_OAK_ARM.md`).
Stufe C4 erst nach SLAM sinnvoll.

---

## Teil B — SOFTWARE-ABNAHME (Routine, ohne Hardware, ~10 min)

Nach jeder Software-Änderung. Ein Befehl, keine Rückfragen:
```bash
cd ~/roboter_ws && ./pruefplan_jetson.sh --software
```

| Stufe | Beweist |
|---|---|
| B0 | Clean-Build aller Pakete (räumt vorher macOS-Reste weg) |
| B0b | Alle Pakete + AMENT-Hooks korrekt installiert |
| A1 | Pick&Place-Trockenlauf (Mocks) endet mit SUCCESS |
| K1 | Missionsbrücke: Auftrag → mission_manager → BT → success (echt) |
| K2 | Objektgedächtnis: get_object_pose antwortet aus dem Weltmodell |
| K4 | Not-Aus-Wächter: `/safety/estop` frei by default + reagiert auf Anforderung |
| K5 | Offboard-Guard: Serverausfall löst KEINE ungewollte Erkundung aus |
| N1 | Echtes Nav2 erreicht ein Ziel in der Testwohnung (virtuelle Basis) |
| N2 | KÖNIGSTEST: kompletter Auftrag mit echter Nav2-Fahrt bis zur Katalog-Ablage |
| D2 | handeye_calibration-Paket bereit (Kalibrierlauf folgt mit echtem Arm) |

**Bestanden = alle Zeilen im Protokoll `OK`.**

## Teil C — Einzelstufen

`./pruefplan_jetson.sh --stage <ID>` · Liste: `--hilfe` · Menü: ohne Argument ·
`--alle` inkl. Hardware-Stufen (B2-RS485 bleibt durch die Sicherheitsphrase geschützt).

## Wenn etwas fehlschlägt

1. Stufe einzeln wiederholen: `./pruefplan_jetson.sh --stage <KÜRZEL>`
2. Log ansehen: `/tmp/pruefplan_logs/` + `~/pruefplan_ergebnisse.md`
3. Häufigste Ursachen: `source install/setup.bash` vergessen · `--` in XML-Kommentaren ·
   navigation2/rosbridge/depthai nicht installiert · `/dev/ttyUSB*`-Rechte (dialout-Gruppe) ·
   macOS-`._*`-Dateien (räumt B0 automatisch weg).

---
*Änderungsstand des Projekts: `PROJEKT_STATUS.md` · Ersteinrichtung KI-Server:
`src/robot_bringup/README.md`.*
