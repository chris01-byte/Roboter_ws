# handeye_calibration — Hand-Auge-Kalibrierung Arm <-> OAK (Eye-to-Hand)

> **Stand 12.11.2026, zuerst lesen:** Dieses Paket stammt aus dem
> Juli-Konzept, das inzwischen nur noch historisch ist. Maßgeblich ist das
> [Kalibrierkonzept](../../docs/ARM_KALIBRIERKONZEPT.md) (Stufen K1–K7) mit
> dem [Integrationsplan](../../docs/INTEGRATIONSPLAN_ARM_SOFTWARE.md) (Stufe M7).
> Die OAK dient beim Greifen nur der Erkennung und Anfahrdistanz; den Griff
> führt eine Orbbec Gemini 305 zwischen J5 und J6. Der Recorder ist dafür mit
> anderen Topics und dem Frame des Handgelenkglieds verwendbar, der Löser
> braucht einen Eye-in-Hand-Modus. Die Frame-Namen weichen vom
> laufenden System ab: Das Werkzeug rechnet mit `camera_rgb_optical_frame`
> aus der Dummy-URDF, der OAK-Treiber liefert `oak_rgb_camera_optical_frame`,
> und die OAK-Lage kommt heute aus `oak.launch.py`, nicht aus der URDF. Das
> Armmodell der Dummy-URDF ist überholt, der Flansch-Frame `tool0` noch offen.
> Die Toleranzen unten sind Zielwerte des alten Konzepts, keine Zusage. Code
> und Parameter sind unverändert; ihre Anpassung ist ein eigener, getesteter
> Kalibrierschritt.

Werkzeuge zu den Stufen **D/E/F** aus [`KONZEPT_KALIBRIERUNG_OAK_ARM.md`](../../KONZEPT_KALIBRIERUNG_OAK_ARM.md)
(Workspace-Root). Erst Konzept lesen — die Stufen A–C (echtes Armmodell,
Intrinsik-Check, Board am Flansch) sind Voraussetzung.

| Werkzeug | Zweck | Stufe |
|---|---|---|
| `handeye_recorder` | ROS-Node: sammelt Messpaare (Armpose aus TF + Boardpose aus Kamerabild) | D |
| `handeye_solve` | Offline-Skript (ohne ROS lauffähig): rechnet die Lösung, filtert Ausreißer, gibt fertige URDF-Werte aus | E + F |

## Abhängigkeiten (Jetson)

```bash
sudo apt install ros-humble-cv-bridge python3-opencv python3-numpy
```
Ziel-OpenCV ist 4.5.x (Ubuntu-22.04-Paket); für OpenCV >= 4.7 sind
Kompatibilitätspfade eingebaut.

## 1) Messpaare sammeln (Stufe D)

Voraussetzungen laufen: Armtreiber (`/joint_states` + `robot_state_publisher`)
und OAK-Treiber (Bild + CameraInfo). Dann im Vordergrund-Terminal:

```bash
ros2 launch handeye_calibration handeye_recorder.launch.py
```

Bedienung (Eingaben mit ENTER bestätigen):

| Taste | Wirkung |
|---|---|
| ENTER / `s` | Paar aufnehmen — mittelt 8 Frames, prüft Stillstand von Board **und** Arm-TF |
| `u` | letztes Paar verwerfen |
| `d` | Vielfalts-/Qualitätsbericht (Rotations-Spannweite, RMS) |
| `q` | Bericht anzeigen und beenden |

Kontrollbild ohne Monitor am Roboter: `/handeye/debug_image` z. B. mit
`rqt_image_view` ansehen (zeigt erkannte Marker, Achsen, Zähler).

Regeln aus dem Konzept: **15–25 Posen**, Board um **>= 30°** um zwei Achsen
kippen, Abstand 0,4–0,9 m, jede Pose aus derselben Richtung anfahren, Basis
blockiert. Der Node warnt bei zu ähnlichen Posen und verwirft verwackelte
Aufnahmen automatisch. Ergebnisdatei (fortlaufend gespeichert):
`~/handeye_data/handeye_pairs_<Zeitstempel>.yaml`

## 2) Lösung rechnen (Stufe E)

```bash
handeye_solve ~/handeye_data/handeye_pairs_XXXX.yaml
# Methodenvergleich (Sanity-Check der Datenqualität):
handeye_solve ~/handeye_data/handeye_pairs_XXXX.yaml --method all
```

Ausgabe: `T(base_link -> camera_rgb_optical_frame)` mit Residuen
(Abnahme Stufe E: RMS <= 5 mm / <= 0,5°), Ausreißer werden automatisch
markiert und entfernt. Nebenprodukt `T(tool0 -> board)` dient als
Plausibilitätscheck der Halterung.

## 3) Ergebnis einpflegen (Stufe F)

`handeye_solve` druckt fertige Xacro-Zeilen (`oak_x` … `oak_yaw`) für den
Kamera-Joint — vorher den Joint in
`robot_description/urdf/mobile_manipulator_dummy.urdf.xacro` von nur-`yaw`
auf volle `rpy` erweitern. **Die URDF ist die einzige TF-Quelle** — der mit
ausgegebene `static_transform_publisher`-Befehl ist nur für den Schnelltest
gedacht. Danach: Zeigetest nach Stufe G des Konzepts.

## Grenzen / offen

- Wie die übrigen Pakete noch nicht in einer ROS-Umgebung kompiliert/getestet;
  `py_compile` bestanden. Board-Erkennung gegen OpenCV-4.5-API geschrieben,
  4.7+-Pfade vorhanden, aber auf dem Zielsystem zu verifizieren.
- Der Recorder fährt den Arm nicht selbst — Posen per Hand/Teach anfahren
  (bewusst: funktioniert vor MoveIt-Integration, Konzept Stufe D Variante 1).
