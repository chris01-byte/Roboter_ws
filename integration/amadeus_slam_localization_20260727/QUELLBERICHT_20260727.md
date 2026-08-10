# Kartierung und Lokalisierung — Arbeitsbericht

**Datum:** 27.07.2026
**System:** Jetson `p-desktop`, Arbeitskopie `~/roboter_ws`
**Commit:** `390fcec` — *Lokalisierung in Betrieb nehmen: RS485-Selbstheilung und Woerterbuch-Rettung*
**Roboter:** Amadeus, OAK-D-S2 auf 1,34 m (18,94° geneigt), 2× VL53L7CX, ESS23-RS-Antrieb

---

## 1. Ergebnis in einem Satz

**Der Roboter findet sich in seiner selbst erstellten Karte wieder** — 76 bestätigte
Lokalisierungen über eine volle 360°-Drehung. Damit ist der Punkt überwunden, an dem
die Arbeit zuvor abgebrochen war.

| Kennzahl | vorher (26.07.) | jetzt (27.07.) |
|---|---:|---:|
| Fahrstrecke in der Karte | 1,34 m | **17,54 m** |
| Kartenknoten | 230 | **902** |
| Visuelles Wörterbuch | 34.716 Wörter | **271.805 Wörter** |
| Globale Wiedererkennungen | 35 | **100** |
| Lokale Wiedererkennungen | 1 | **67** |
| Bestätigte Lokalisierungen | 0 | **76** |

---

## 2. Ausgangslage

Eine frühere Sitzung hatte eine Karte aufgenommen, war aber beim nächsten Schritt
gescheitert: Der Roboter erkannte nicht, wo er sich befindet. Als Ursache war
festgehalten worden, die Datenbank sei durch ein `kill -9` ohne das visuelle
Wörterbuch zurückgeblieben und **nicht reparierbar**.

**Diese Erklärung hat sich als falsch herausgestellt.** Die vorgefundene Datenbank
enthielt sehr wohl ein Wörterbuch (34.716 Wörter, 35 Wiedererkennungen). Die
eigentliche Schwäche lag woanders: Die gesamte Aufnahme umfasste nur **1,34 m**
zurückgelegte Strecke in 4 Minuten — im Kern ein einziger Standpunkt mit Drehungen,
keine Raumkarte.

---

## 3. Zwei echte Fehler, gefunden und behoben

### 3.1 `base_hardware` kam von einem RS485-Aussetzer nie wieder hoch

**Symptom:** Nach dem Start meldete der Antriebsknoten im Sekundentakt
`RS485-Verbindung fehlgeschlagen: /dev/ttyUSB_BASE`. Die Motoren blieben tot, obwohl
der Port isoliert einwandfrei funktionierte (beide Motoren antworteten auf Anhieb,
Ist-Drehzahl 0).

**Ursachenkette, aus dem Log rekonstruiert:**

1. Der erste Verbindungsaufbau **gelang** (`RS485 AKTIV`).
2. Beim anschließenden Stopp-Kommando liefen beide Motoren in einen Modbus-Timeout —
   das Startgewitter aus OAK, VL53 und RTAB-Map belegte den USB-Bus.
3. Der Selbstheilungspfad `_ensure_rs485()` legte daraufhin einen **neuen**
   Modbus-Client an, **ohne den alten zu schließen**.
4. Der alte Client hielt das exklusive Port-Lock. Jeder weitere Versuch scheiterte an
   `[Errno 11] Could not exclusively lock port /dev/ttyUSB_BASE`.

Die Selbstheilung blockierte sich also selbst — ein einziger Timeout genügte, um die
Motoren dauerhaft stillzulegen.

**Behebung** (`src/base_hardware/base_hardware/base_hardware_node.py`): Der alte
Client wird vor dem Neuaufbau geschlossen. **Ergebnis: 0 RS485-Fehler über zwei
komplette Kartierfahrten.**

### 3.2 Das visuelle Wörterbuch ging beim Beenden verloren — aus einem anderen Grund als angenommen

RTAB-Map schreibt das Wörterbuch erst beim Herunterfahren in die Datenbank. Fehlt es,
bleibt die Karte geometrisch intakt, aber **Wiedererkennung und Lokalisierung sind
unmöglich**.

**Messung:** Nach einer Kartierfahrt wurde der Stack scheinbar sauber beendet — SIGINT,
20 Sekunden Wartezeit. Kontrolle der Datenbank: **831 Knoten, 0 Wörter.** Im Log stand

```
[ERROR] [rtabmap-8]: process has died [pid 6221, exit code -2, ...]
```

`exit code -2` bedeutet: gestorben **an SIGINT**, nicht geordnet beendet. Zum Vergleich
meldete der Kamera-Container daneben korrekt `process has finished cleanly`.

**Ursache:** Das Signal ging an die **Prozessgruppe** (`kill -INT -<PGID>`). Damit
erhielt rtabmap SIGINT doppelt — einmal direkt vom Kernel, einmal weitergereicht von
`ros2 launch`. Das erste Signal startet das Speichern, das zweite bricht es ab.

**Zweiter Stolperstein:** `ros2 launch` eskaliert nach SIGINT selbsttätig auf SIGTERM
und SIGKILL, nach jeweils 5 Sekunden Vorgabe. Für große Karten ist das zu knapp.

**Behebung:**

- SIGINT **nur an den Launch-Prozess**, dann warten, bis rtabmap von selbst verschwindet
- beim Start `sigterm_timeout:=120 sigkill_timeout:=180` mitgeben
  (das sind Launch-Konfigurationen, **keine** `ros2 launch`-Optionen — die kennt Humble nicht)

**Ergebnis:** `rtabmap nach 9s beendet. 902 Knoten, 271805 Woerter.`

Die Warnung in `slam.launch.py` wurde entsprechend korrigiert; sie hätte sonst weiter
in die falsche Richtung gewiesen.

---

## 4. Die Kartierfahrt

### 4.1 Erster Versuch — und was er über die Sicherheitskette lehrte

Der erste Anlauf endete nach 168 Sekunden damit, dass der Roboter **17 cm vor einem
Hindernis stand und sich nicht mehr befreien konnte**.

Der Grund liegt in der Bauart des `nav2_collision_monitor`: Seine StopZone-Aktion
setzt **jede** Bewegung auf null — auch eine reine Drehung. Wer einmal in der Zone
steht (1 bis 26 cm vor dem Sensor), kommt aus eigener Kraft nicht mehr heraus. Das
Fahrskript bemerkte das nicht und schickte zwei Minuten lang Drehbefehle ins Leere.

### 4.2 Das überarbeitete Fahrskript

`tools/kartierung/kartierfahrt.py` verlässt sich nicht mehr auf den collision_monitor
als Bremse, sondern arbeitet auf drei Ebenen:

| Ebene | Wirkung |
|---|---|
| **Vorausschauend** | hört selbst auf `/near_field/status` und hält bei **0,35 m** an — die StopZone beginnt erst bei 0,26 m |
| **Zeitlimit** | jede Fahrt und jede Drehung hat eine Frist; passiert nichts, gilt das als Blockade statt als Endlosschleife |
| **Flucht** | fährt rückwärts frei, **höchstens so weit, wie es gerade vorwärts kam** — dort war eben noch freier Raum. Nur direkt auf `/cmd_vel`, weil der Monitor im Stoppzustand auch das Rückwärtsfahren sperrt |

Zur Sicherheitseinordnung: Der Monitor bleibt als Notbremse in der Kette, er ist nur
nicht mehr der reguläre Bremsweg.

### 4.3 Verlauf der zweiten Fahrt (903 Sekunden)

| Ereignis | Anzahl |
|---|---:|
| Zyklen mit voller 1,00-m-Strecke | 8 |
| Zyklen mit vorzeitigem Halt („zu nah") | 2 |
| Blockaden ohne Erkennung | **0** |
| Fluchtmanöver | 2 — **beide erfolgreich** |

Beispiel eines Fluchtmanövers aus dem Protokoll:

```
Drehung blockiert
FLUCHT: 0.30 m rueckwaerts (vorne 0.30 m)
FLUCHT beendet: 0.30 m zurueck, vorne jetzt 9.90 m
```

Der Roboter hat sich in beiden Fällen selbst befreit und die Aufgabe fortgesetzt.

---

## 5. Der Lokalisierungstest

### 5.1 Warum der erste Testlauf wertlos war

Der erste Prüflauf meldete „bestanden": `map→odom` zeigte einen Versatz von 0,665 m,
also nicht die Identität. **Das beweist gar nichts.** Zwei Gegenbefunde:

1. `base_hardware` meldete durchgehend `TIMEOUT-STOP` — der Roboter **hatte sich nie
   gedreht**. Der Fahrbefehl per `ros2 topic pub` kam nicht an.
2. Im Log wurde **jede** Wiedererkennung abgelehnt (`Not enough inliers 0/20`).

Der Versatz stammte allein daraus, dass **RTAB-Map beim Start die zuletzt gespeicherte
Pose aus der Datenbank lädt** und `map→odom` entsprechend setzt — ganz ohne
Wiedererkennung. Genau dieser Trugschluss hatte auch den früheren Test unbrauchbar
gemacht.

### 5.2 Der belastbare Test

Zwei Korrekturen:

- **Hartes Kriterium:** `/localization_pose` — RTAB-Map publiziert dort **nur nach
  bestätigter Lokalisierung**.
- **Echte Bewegung:** Der Roboter dreht sich aus dem Skript heraus (rclpy statt CLI)
  einmal vollständig. Ohne Bewegung verarbeitet RTAB-Map wegen `RGBD/AngularUpdate`
  überhaupt keine Bilder.

**Ergebnis:**

```
tatsaechlich gedreht      : 357 Grad
Lokalisierungen gemeldet  : 76
ERGEBNIS: BESTANDEN - 76 bestaetigte Lokalisierungen.
```

Die gemeldete Karten-Pose blieb über die gesamte Umdrehung stabil bei
x = +0,62 / y = +0,23 m — der Roboter erkennt seine Umgebung aus jedem Blickwinkel
wieder.

---

## 6. Was bewusst offen bleibt

### 6.1 Die Karten-Pose ist plausibel, aber nicht unabhängig geprüft

Sie stimmt mit der beim Start geladenen Pose überein. Ob sie **metrisch** stimmt, zeigt
erst eine Gegenprobe: fahren und verfolgen, ob die Karten-Pose der tatsächlich
gefahrenen Strecke folgt.

### 6.2 Das Belegungsraster taugt noch nicht zum Navigieren

Das ist die wichtigere Einschränkung. Die beiden Fähigkeiten hängen an
**verschiedenen Daten**:

| Fähigkeit | Datengrundlage | Zustand |
|---|---|---|
| Sich orientieren („wo bin ich?") | visuelle Merkmale der Kamerabilder | **gut** — 271.805 Wörter, 167 Wiedererkennungen |
| Navigieren („wie komme ich hin?") | Belegungsraster | **noch nicht ausreichend** |

Gemessen: 17,7 % frei, 31,3 % belegt, 51 % unbekannt. Die freie Fläche wird stark
unterschätzt — die Karte zeigt rund 10,5 m², der Raum hat sichtbar mehr. Zwei Gründe:

- `Grid/RangeMax` steht auf **2,5 m**; weiter wird nichts eingetragen
- der Roboter kam kaum vom Fleck (Endpose 1,01 / −0,41 m trotz 17,5 m Fahrstrecke,
  das meiste waren Drehungen)

Daraus entsteht ein **runder „Sichthorizont"** statt der eckigen Raumwände. Für Nav2
wäre das schädlich: Ein zu dick eingetragener Möbelring blockiert Fläche, die in
Wirklichkeit befahrbar ist.

### 6.3 Kleinere Punkte

- Der OAK-Container wirft beim Herunterfahren einen Segfault (apport, Signal 11) —
  unkritisch, da beim Beenden, aber unschön.
- Der USB-Stick `/media/p/64GB/roboter_ws` hat diesen Stand **nicht**; Commit `390fcec`
  liegt nur auf dem Jetson.

---

## 7. Vier Fehldiagnosen — und was daraus folgt

Der Vollständigkeit halber, weil das Muster wichtiger ist als die einzelnen Irrtümer.
Im Laufe dieser Sitzung habe ich vier Mal etwas behauptet, das die Messung widerlegt hat:

| Behauptung | Wirklichkeit |
|---|---|
| „0 akzeptierte Wiedererkennungen" | 167 — im Log stehen nur die *Ablehnungen* im Klartext |
| „Den Merkmalen fehlt die Tiefe" | 97,8 % haben Tiefe, im Median 888 pro Knoten |
| „Die Tiefe endet bei 1,23 m" | das waren Möbel**höhen**: `Feature.depth_x/y/z` sind base_link-Koordinaten (x = Entfernung, z = Höhe); die echten Entfernungen liegen bei 1,8–2,7 m |
| „Lokalisierung bestanden" (erster Lauf) | der Roboter hatte sich nicht bewegt; der Versatz war die geladene Startpose |

**Schlussfolgerung:** Das Log allein führt bei diesem System systematisch in die Irre,
weil Erfolge dort anders (oder gar nicht) auftauchen als Misserfolge. Belastbar sind
nur die Rohdaten — die Datenbank via `rtabmap-info`, und für die Lokalisierung
ausschließlich `/localization_pose`.

Dieselbe Lehre steht bereits dreimal im Projektgedächtnis früherer Sitzungen. Sie gilt
weiterhin.

---

## 8. Nächste Schritte, in sinnvoller Reihenfolge

1. **Lokalisierung gegenprüfen:** kurze Fahrt, dabei verfolgen, ob die Karten-Pose der
   gefahrenen Strecke folgt. Erst damit ist die Pose metrisch bestätigt.
2. **Raster brauchbar machen:** `Grid/RangeMax` erhöhen (2,5 → 4,0 m) und den Raum
   großflächig abfahren, damit die echte freie Fläche eingetragen wird. Vorher die
   Höhenverteilung messen, nicht raten.
3. **Erst danach Nav2** auf der gespeicherten Karte, mit `static_map_odom:=false`
   (sonst zwei Publisher für `map→odom`).
4. **Stand auf den USB-Stick spiegeln.**

---

## 9. Befehle zum Nachvollziehen

Vollständig dokumentiert in `~/roboter_ws/tools/kartierung/README.md`.

```bash
# Karte aufnehmen (Motoren werden SCHARF)
cd ~/roboter_ws/tools/kartierung
./start_slam.sh /tmp/slam.log
python3 kartierfahrt.py 900
ros2 service call /robot_map_manager/save_map std_srvs/srv/Trigger
./stop_slam.sh          # prüft selbst, ob das Wörterbuch geschrieben wurde

# Lokalisierung prüfen
./start_lokalisierung.sh /tmp/lok.log
python3 lokalisierung_test2.py
./stop_slam.sh

# Auswerten
python3 karte_ansehen.py ~/.local/share/amadeus/maps/amadeus/<version>/
source /opt/ros/humble/setup.bash && rtabmap-info ~/.local/share/amadeus/rtabmap.db
sqlite3 ~/.local/share/amadeus/rtabmap.db "SELECT COUNT(*) FROM Word;"   # muss > 0 sein
```

---

## 10. Dateien

| Was | Wo |
|---|---|
| Karten-Datenbank | `~/.local/share/amadeus/rtabmap.db` (270 MB) |
| Sicherung der Vorgängerkarte | `~/.local/share/amadeus/rtabmap_20260727_backup.db` |
| Karten-Schnappschuss | `~/.local/share/amadeus/maps/amadeus/20260727T165329866919Z-dbdb0d131f39/` |
| Gerenderte Karte | ebenda, `karte_gross.png` — Kopie neben diesem Bericht |
| Werkzeuge und Fallenbeschreibung | `~/roboter_ws/tools/kartierung/` |
| Commit | `390fcec` in `~/roboter_ws` |
