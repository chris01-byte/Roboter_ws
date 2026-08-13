# Ziel: Der Roboter kartiert selbst und findet sich zurecht

**Stand:** 13.08.2026 · Branch `fix/encoder-position-odometry`

Dieses Dokument ordnet ein, was für das eigentliche Ziel erreicht ist, was noch
fehlt, und welche Nebenschauplätze bewusst liegen bleiben.

---

## 1. Das Ziel in einem Satz

Der Roboter soll **eine Wohnung selbständig abfahren, dabei eine Karte
aufbauen** und sich **später in dieser Karte wiederfinden**.

Daraus folgen vier Fähigkeiten, die zusammenspielen müssen:

| | Fähigkeit | Stand |
|---|---|---|
| A | Aus Scans eine brauchbare Karte bauen | **erreicht** |
| B | Sich selbst durch den Raum bewegen | teilweise — nur ferngesteuert |
| C | Nicht anecken | **Lücke im LiDAR-Stack** |
| D | Sich in einer fertigen Karte lokalisieren | ungeprüft mit dem LiDAR |

---

## 2. Was jetzt funktioniert

Die Kartenqualität war das eigentliche Problem, und sie ist gelöst. Zwei
unabhängige Fehler standen im Weg; beide sind behoben und mit A/B-Messungen
belegt.

**Reine Drehungen wurden verworfen.** Der Vorfilter von `slam_toolbox` im
Humble-Zweig prüfte nur die Translation. Bei einer Drehung auf der Stelle ist
die null, also flog jeder Scan raus, bevor Kartos Winkelschwelle greifen konnte.
Der gepinnte Backport des offiziellen Upstream-Fixes stellt die
„Strecke **oder** Winkel"-Logik her. Synthetisch belegt: **37 gegen 0** neue
Knoten bei identischen Eingangsdaten.

**Karto verwarf drei Viertel aller Scans.** Der STL-27L liefert je Umdrehung
unterschiedlich viele Strahlen — 19 verschiedene Werte zwischen 2145 und 2176,
der häufigste deckt nur 25,7 % ab. Karto merkt sich die Strahlenzahl des ersten
Scans und bricht bei jedem abweichenden ab, **ohne Meldung im ROS-Log** (sie
geht auf stdout). Der neue Knoten `scan_vereinheitlichen` setzt jeden Scan auf
ein festes Winkelgitter um.

Ergebnis am Roboter, gleiche Drehung, nur der Schalter umgelegt:

| | verworfene Scans | neue Knoten | Nebenachse (real 3,80 m) |
|---|---|---|---|
| ohne Normalisierer | 31 | 10 | 5,39 m |
| mit Normalisierer | 0 | **41** | **3,83 m** |

Aus mehrfach versetzten Wandfragmenten wurde eine geschlossene Wandkontur.

**Odometrie kalibriert.** `wheel_radius_m: 0.0624`, `wheel_separation_m: 0.3845`
(vorher 0.0612 / 0.3755), aus acht Fahrten mit dem Lasermessgerät. Winkelfehler
−1,45° je Umdrehung, über 283 Messpunkte je Drehrichtung mit R² = 0,997.

---

## 3. Der Odometrieversatz — und warum er das Ziel nicht blockiert

Es bleibt ein Fehler: **Je Fahrt fehlen der Odometrie rund 28–35 mm**, nahezu
unabhängig von Streckenlänge und Geschwindigkeit. Nachgewiesen ohne äußeres
Messmittel, indem dieselbe Gesamtstrecke einmal am Stück und einmal in Etappen
gefahren wird — 1× 0,80 m ergab +28,6 mm, 4× 0,20 m ergab +80,5 mm.

**Drei Hypothesen dazu sind an Messungen gescheitert:**

1. *Unterabtastung der Rückmeldung* — die Leserate von 10 auf 50 Hz erhöht,
   Versatz blieb bei 17,9 statt 17,3 mm.
2. *Der Antrieb gibt die Welle beim Stoppen frei* — widerlegt: die Räder ließen
   sich von Hand nicht drehen, der Antrieb hält also.
3. *Kinetisches Rutschen* — müsste quadratisch mit der Geschwindigkeit wachsen.
   Gemessen: 28,0 mm bei 0,10 m/s, 28,5 bei 0,20, 34,6 bei 0,30. Nahezu
   konstant.

Der Mechanismus ist damit **offen**.

**Aber er steht dem Ziel nicht im Weg.** SLAM verwendet die Odometrie nur als
Startschätzung für den Scanabgleich; der Suchraum dafür ist mit
`correlation_search_space_dimension: 0.5` einen halben Meter groß. Ein Fehler
von 30 mm liegt weit darin und wird bei jedem Scan wegkorrigiert. Genau deshalb
ist die Karte trotz dieses Fehlers sauber geworden.

Relevant wird der Versatz erst dort, wo Odometrie **unkorrigiert** benutzt wird:
beim Andocken, bei Feinpositionierung, und in Nav2 zwischen zwei
Lokalisierungsupdates. Für „Karte bauen und sich zurechtfinden" ist er
zweitrangig.

> **Ehrliche Einordnung:** Die Suche nach diesem Versatz hat am 13.08.2026 einen
> großen Teil des Tages gekostet, ohne das Ziel voranzubringen. Der Befund ist
> korrekt und gut vermessen — aber er war nicht auf dem kritischen Pfad. Wer
> hier weitermacht, sollte das bewusst als eigenes Vorhaben tun.

---

## 4. Was zum Ziel noch fehlt

In der Reihenfolge, in der es sinnvoll ist.

### 4.1 Nahbereichsschutz im LiDAR-Stack — **zuerst**

`slam_lidar.launch.py` startet LiDAR, Antrieb, Scan-Vereinheitlicher und
`slam_toolbox`. Sonst nichts. Es läuft **kein `collision_monitor`** und keine
Nav2-Kostenkarte. Der bewährte Kamera-Stack (`robot_bringup/slam.launch.py`)
hat das über `vl53_near_field` — der LiDAR-Stack hat es noch nicht.

Solange das fehlt, darf niemand autonom fahren lassen. Zwei blinde Flecken
kommen dazu, die auch ein Monitor nicht behebt:

- Der **Mastsektor 236–304°** ist maskiert. Nach hinten hat der Roboter mit
  diesem Sensor **keinerlei** Wahrnehmung. Rückwärtsfahrten sind blind.
- Die Scanebene liegt auf **75 cm**. Alles darunter ist unsichtbar —
  Tischplatten, Kisten, Schwellen, Kabel. Die VL53-Sensoren decken das nur
  teilweise ab; ihr Kegel trifft den Boden erst bei ~0,53 m, jenseits ihrer
  Reichweite.

### 4.2 Kartierfahrt abschließen (Phase 4)

Offen ist die langsame geschlossene Runde. Es ist **kein Joystick angeschlossen**
(`/dev/input/js*` fehlt), also braucht es entweder einen Joystick, die
Weboberfläche (`smartphone_gui`) oder ein Fahrskript. Danach: Karte speichern
und mit `karten_vergleichen.py` und `karte_ansehen.py` bewerten.

Die kurze Gerade über 0,40 m ist bereits bestanden — 20 neue Knoten, Karte
blieb einwandig.

### 4.3 Lokalisierung in der LiDAR-Karte nachweisen

`slam_toolbox` kann Lokalisierung, ist damit aber am STL-27L noch nie geprüft
worden. Für den Kamera-Stack existiert ein belastbares Verfahren:
`tools/kartierung/lokalisierung_kidnapped.py`, dazu die harte Lehre aus
`docs/PROJECT_MEMORY.md` (28.07.2026):

> Zwei naheliegende Prüfungen beweisen **nichts** — dass `map→odom` nicht die
> Identität ist, und dass `/localization_pose` publiziert wird. Belastbar ist
> nur: ohne Vorwissen starten und von mehreren Standorten prüfen, ob der
> gemeldete Positionsunterschied dem echten entspricht.

Das gilt für den LiDAR genauso.

### 4.4 Selbständig erkunden

Das Paket `explore` steht in `docs/INVENTORY.md` als **Entwurf**, ebenso
`tools/kartierung/erkundungsfahrt.py`. Das ist der letzte Baustein und setzt
4.1 bis 4.3 voraus. Vorher autonom fahren zu lassen wäre fahrlässig.

---

## 5. Fallen, die real Zeit gekostet haben

**Kennzahlen können in die Irre führen.** „Dicke Wände" stieg bei der
*besseren* Karte von 3,2 auf 24,0 %. Die Kennzahl misst Erosionsüberleben und
belohnt dünne Linien; konsistent eingetragene Wände sind bei 3-cm-Zellen eben
dick. Erst das Rendern entschied. Das deckt sich mit der älteren Projektlehre,
dass eine einzelne Kennzahl nichts beweist.

**Der LiDAR-Wandvergleich ist keine Referenz für Kalibrierung.** Bei einer
Verifikationsfahrt lag er 24 mm daneben, bei sonst ±5 mm Streuung. Für
Kalibrierentscheidungen zählt das Lasermessgerät.

**Fehler werden lautlos verschluckt.** Kartos Meldung über verworfene Scans geht
auf stdout, nicht ins ROS-Log. Drei Viertel aller Scans verschwanden, ohne dass
ein Werkzeug es angezeigt hätte.

**`ros2 launch` beenden reicht nicht.** SIGINT an die Launch-PID beendet den
Elternprozess; die Knoten können weiterlaufen. So liefen zeitweise **zwei
vollständige Stapel gleichzeitig**, mit zwei `map→odom`-Publishern und zwei
scharfen `base_hardware`-Knoten auf demselben RS485-Bus. Vor jedem Start prüfen:

```bash
python3 tools/kartierung/roboterknoten.py
```

**Not-Aus:** Die Motorzuleitung wird **manuell über ein Relais** geschaltet, ist
also vom Kommandoregister unabhängig. Ein Software-Stopp ersetzt ihn nicht.

---

## 6. Konkret als Nächstes

1. `collision_monitor` beziehungsweise `vl53_near_field` in
   `slam_lidar.launch.py` aufnehmen und im Stillstand prüfen.
2. Fahrweg für die Kartierrunde klären — Joystick, Weboberfläche oder Skript.
3. Geschlossene Runde fahren, Karte speichern und bewerten.
4. Lokalisierung ohne Vorwissen von mehreren Standorten nachweisen.
5. Erst danach `explore` in Betrieb nehmen.

Der Odometrieversatz ist softwareseitig durch absolute Encoderpositionen adressiert.
Die Hardware-Abnahme (Counts/Umdrehung und A/B-Fahrt) ist noch offen; bis dahin
blockiert die Konfiguration den echten Encoderbetrieb absichtlich.

---

## 7. Startbefehle

```bash
# Vorbedingung: es darf nichts laufen
python3 tools/kartierung/roboterknoten.py

# Kartierung, Motoren stromlos (Vorgabe)
bash tools/kartierung/start_lidar_slam.sh /tmp/slam.log

# Noch keine pauschale Fahrfreigabe: Counts und beide erwarteten Treiberwerte
# sind 0 und blockieren den Encoderbetrieb. Erst nach H2-Bestätigung aller drei
# Werte, bestandenem H3 und neuer ausdrücklicher Freigabe darf die folgende
# Zeile ohne Kommentar ausgeführt werden:
# bash tools/kartierung/start_lidar_slam.sh /tmp/slam.log active_drive:=true
```

Die vollständige Source-Reihenfolge über **vier** Workspaces steckt im
Startskript. Die aktuelle Encoder-Abnahme und ihr Rückfallweg stehen in
`docs/ENCODER_ODOMETRIE_FIX.md`; der integrierte SLAM-Vorläufer ist in
`docs/SLAM_TOOLBOX_ROTATION_FIX.md` dokumentiert.
