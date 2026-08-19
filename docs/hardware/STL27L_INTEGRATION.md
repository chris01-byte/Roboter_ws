# STL-27L — Integration in Amadeus

**Sensor:** LDROBOT/Waveshare STL-27L, 2D-dToF-LiDAR, 360°, 6–13 Hz
**Adapter:** Waveshare-Platine mit ESP8266 und CP2102 (USB-UART)
**Treiber:** `ldlidar_stl_ros2`, gepinnt auf `bf668a89baf722a787dadc442860dcbf33a82f5a`
**Grundlage:** `Amadeus_Lidar_Integrationsdatei.md` (05.08.2026)

---

## 1. Warum dieser Sensor

Die OAK-D-S2 liefert visuelle Merkmale und Semantik, aber ihre Tiefenmessung
versagt an Fenstern, Spiegeln und glatten hellen Wänden. Bei der Kartierung vom
28.07.2026 waren dadurch **74,6 % der scheinbaren Freifläche Artefakte**
(26,5 m² gemeldet in einem Raum von 18,6 m²). Der STL-27L soll die metrische
2D-Karte übernehmen, die Kamera bleibt für Wiedererkennung und Objekte
zuständig.

---

## 2. Sicherheitsgrenzen — vor dem ersten Betrieb lesen

**Der STL-27L auf ~75 cm Höhe ist kein Kollisionssensor.** Alles unterhalb
seiner Scanebene ist für ihn unsichtbar: Tischplatten auf 72–76 cm, Kisten,
Hocker, Betten, Schwellen. Bodennaher Schutz muss weiterhin über OAK-Tiefe und
die VL53-Sensoren kommen.

**Der maskierte Mastsektor ist unbekannter Raum, nicht freier Raum.** Solange
dort keine bestätigte Sensorabdeckung existiert, gilt:

- keine autonome Rückwärtsfahrt
- kein seitliches Ausschwenken in die Totzone allein auf LiDAR-Basis
- Drehungen langsam und unter Nutzung der übrigen Sensorik

**Eine alte Karte ersetzt keinen aktuellen Kollisionssensor.**

Vor jedem Test: Not-Aus erreichbar, Fahrantriebe deaktiviert, kein Autostart
von Navigation. Der rotierende Sensorkopf wird nicht berührt oder blockiert.

---

## 3. Was bereits vorbereitet ist

| Teil | Zustand |
|---|---|
| Herstellertreiber | gebaut in `~/amadeus_lidar_ws`, Commit gepinnt, **unverändert** |
| Bringup-Paket | `src/amadeus_lidar_bringup/` — baut, Launch löst auf |
| Sensorparameter | `config/stl27l.yaml`; ROS-CCW-Ausgabe (`laser_scan_dir: true`) |
| udev-Beispielregel | `config/udev/99-amadeus-stl27l.rules.example` |
| `slam_toolbox`, `rviz2` | bereits auf dem Jetson installiert |

**Aktueller, real verifizierter Montagevertrag:** Die Launch-Datei publiziert
`base_link→laser_frame` mit x = 0,245 m, y = 0,000 m, z = 0,660 m und
yaw = +1,5708 rad. Zusammen mit `laser_scan_dir: true` stimmen Karten- und
Odometrie-Drehrichtung ueberein. `base_hardware` sendet `odom→base_link`,
`slam_toolbox` waehrend der LiDAR-Kartierung `map→odom`.

---

## 4. Ablauf am Roboter

### Phase 0 — Gerät identifizieren

Lidar anschließen: graues Kabel an die schwarze Waveshare-Platine, USB-C dorthin,
USB-A an einen freien Jetson-Port. **Die rote USB-TTL-Platine bleibt weg.**

```bash
lsusb | grep 10c4                 # erwartet: 10c4:ea60 Silicon Labs CP210x
ls -l /dev/serial/by-id/
udevadm info --query=property --name=/dev/ttyUSBx | \
  egrep 'ID_VENDOR_ID|ID_MODEL_ID|ID_SERIAL_SHORT|ID_PATH'
```

Seriennummer in die udev-Regel eintragen, dann:

```bash
sudo cp src/amadeus_lidar_bringup/config/udev/99-amadeus-stl27l.rules.example \
        /etc/udev/rules.d/99-amadeus-stl27l.rules
# Seriennummer eintragen, dann:
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -l /dev/amadeus_lidar
```

Benutzer muss in der Gruppe `dialout` sein (`groups`), sonst `usermod -aG
dialout $USER` und neu anmelden.

### Phase 1 — Rohdaten und isolierter Sensortest

Nur ein Prozess darf den Port öffnen. Rohdatentest **vor** dem ROS-Treiber:

```bash
stty -F /dev/amadeus_lidar 921600 raw -echo
timeout 2 dd if=/dev/amadeus_lidar bs=47 count=5 2>/dev/null | hexdump -C
```

Erwartet: fortlaufende Binärdaten mit wiederkehrendem Header `54 2c`.

Dann der Treiber, zunächst **ohne** Winkelmaskierung:

```bash
ros2 launch amadeus_lidar_bringup stl27l.launch.py crop:=false
```

Prüfen:

```bash
ros2 topic hz /scan          # 9–11 Hz
ros2 topic echo /scan --once # frame_id = laser_frame, Werte 0,03–25 m
```

In RViz bei Fixed Frame **`laser_frame`** liegt die physische Roboterfront der
aktuellen Montage bei 270 Grad. Mit Fixed Frame **`base_link`** muss dieselbe
Wand auf +X erscheinen; ein Karton links darf nicht rechts auftauchen. Der
isolierte Test vom 16.08.2026 bestaetigte vorne/links/rechts sowie den
Mastbogen bei 56,0 bis 123,9 Grad im Sensorframe (Zentrum 90 Grad, im
Basisframe hinten).

### Phase 2 — Vermessen

**Winkelgrenzen** (Abschnitt 5.5 des Plans): Rohscan in RViz, Reflexionen des
eigenen Rumpfs identifizieren, Grenzen des offenen Sichtfelds bestimmen, je
3–5° Sicherheitszugabe. Werte in `config/stl27l.yaml` eintragen, dann mit
`crop:=true` gegenprüfen: Kein Teil des Rumpfs darf mehr in `/scan` erscheinen.

**Montagepose** (Abschnitt 5.6): von `base_link` bis zur optischen Mitte, nach
REP-103. Zur Orientierung: `base_link` liegt bei Amadeus **0,09 m über dem
Boden**, ein optisches Zentrum auf 80 cm Bodenhöhe ergäbe also z ≈ 0,71 m —
**dieser Wert ist zu messen, nicht zu übernehmen.** Am aktuellen Roboter sind
die oben genannten Werte gemessen und real gegen die Drehrichtung verifiziert.

Danach:

```bash
ros2 launch amadeus_lidar_bringup stl27l.launch.py publish_static_tf:=true \
  tf_x:=… tf_y:=… tf_z:=… tf_roll:=… tf_pitch:=… tf_yaw:=…
ros2 run tf2_ros tf2_echo base_link laser_frame
```

Besser als der statische Publisher: den Link fest in die URDF aufnehmen. Dann
`publish_static_tf` auf `false` lassen — **nie zwei Publisher für denselben
Transform**.

### Phase 3 — 2D-SLAM-Baseline

Erst nach bestandener Phase 2 und nur mit validierter Odometrie. `slam_toolbox`
ist installiert. Beim ersten Lauf **nicht** gleichzeitig RTAB-Map und
slam_toolbox betreiben — zuerst eine reproduzierbare LiDAR-Baseline erzeugen,
dann vergleichen.

---

## 5. Messprotokoll

```text
Datum/Uhrzeit:
Roboter-Commit vor Änderung:      21720b5 (main) / feature/stl27l-integration

--- Gerät ---
USB VID:PID:                      ZU_ERMITTELN   (erwartet 10c4:ea60)
ID_SERIAL_SHORT:                  ZU_ERMITTELN
ID_PATH:                          ZU_ERMITTELN
Stabiler Gerätepfad:              /dev/amadeus_lidar
USB-Port/Hub:                     ZU_ERMITTELN

--- Montage ---
Höhe optisches Zentrum über Boden: ZU_ERMITTELN mm
TF x / y / z:                      ZU_ERMITTELN m
TF roll / pitch / yaw:             ZU_ERMITTELN rad
Sensor-0° zeigt relativ base_link: ZU_ERMITTELN

--- Totzone ---
Mastbreite B auf Scanebene:        ZU_ERMITTELN mm
Abstand D Zentrum–Mastfläche:      ZU_ERMITTELN mm
Verdeckter Sektor von/bis:         ZU_ERMITTELN °
Sicherheitsrand links/rechts:      ZU_ERMITTELN °
Nutzbares Sichtfeld:               ZU_ERMITTELN °

--- Messung ---
Scanrate Mittel/Min/Max:           ZU_ERMITTELN Hz   (Soll 9–11)
Wand bei 1 m:                      ZU_ERMITTELN m    (Soll ±3 cm)
Wand bei 3 m:                      ZU_ERMITTELN m    (Soll ±3 cm)
USB-Resets in 15 min:              ZU_ERMITTELN      (Soll 0)
ROS-Warnungen/Fehler:              ZU_ERMITTELN

--- Abnahme Phase 1 ---
15 min ohne Treiberabbruch:        JA / NEIN
vorne/links/rechts korrekt:        JA / NEIN
Rumpf vollständig maskiert:        JA / NEIN
Totzone gilt als ungültig, nicht als frei: JA / NEIN
Motoren waren deaktiviert:         JA / NEIN
```

---

## 6. Rückfallweg

**Hardware:** Jetson herunterfahren, USB-A abziehen, Halterung entfernen — ohne
andere Sensoren zu berühren.

**Software:**

```text
Bekannter funktionierender Stand: Tag baseline-2026-08-10 (Zweig main)
Rückfallbedingung: USB-Resets, Motorbus gestört, /scan unbrauchbar
Rückfallaktion:
  1. LiDAR-Launch nicht mehr starten (er ist in keinem Gesamtstart eingebunden)
  2. /etc/udev/rules.d/99-amadeus-stl27l.rules entfernen, Regeln neu laden
  3. git switch main
Der Zweig feature/stl27l-integration bleibt erhalten - auch fehlgeschlagene
Ergebnisse gehören ins Protokoll.
```

Der Treiber liegt in `~/amadeus_lidar_ws` **außerhalb** des Roboter-Workspace.
Er beeinflusst den bestehenden Betrieb nicht, solange er nicht gesourct wird.

---

## 7. Bekannte Fallstricke

| Symptom | Ursache / Prüfung |
|---|---|
| Kein `/dev/ttyUSB*` | Ladekabel statt Datenkabel; rote Platine angeschlossen; `dmesg --follow` |
| Dreht, aber keine Daten | falscher Port; Baudrate ≠ 921600; anderer Prozess hält den Port (`lsof`) |
| `Permission denied` | nicht in `dialout`; nach `usermod` neu anmelden |
| USB-Resets mit OAK zusammen | `lsusb -t` prüfen, LiDAR und OAK auf getrennte Root-Hubs, aktiv versorgter Hub |
| Scan gespiegelt | Treiberrichtung und Montage-Yaw als gekoppelten Vertrag pruefen; aktuelles verifiziertes Paar: `laser_scan_dir: true` und `tf_yaw: +1.5708`. Nie nur einen Wert aendern |
| Karte verzogen | erst Montage, TF, Raddaten, Zeitstempel prüfen — nicht den Sensor tauschen |

**Projektspezifisch:** Am Jetson hängt bereits ein FTDI auf `/dev/ttyUSB0`
(Motor-RS485). Deshalb ist der udev-Alias Pflicht — ein vertauschter Port
ließe den LiDAR-Treiber auf den Motorbus sprechen.
