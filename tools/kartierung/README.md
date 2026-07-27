# Werkzeuge für Kartierung und Lokalisierung

Am 27.07.2026 auf dem echten Roboter benutzt und dort verifiziert. Die Skripte
setzen voraus, dass `~/roboter_ws/install/setup.bash` existiert.

## Reihenfolge einer kompletten Kartenaufnahme

```bash
# 1) SLAM starten - Motoren werden SCHARF, Not-Aus bereithalten
./start_slam.sh /pfad/zum/slam.log

# 2) Kartierfahrt (Zeitbudget in Sekunden)
python3 kartierfahrt.py 900

# 3) Karte sichern, SOLANGE SLAM noch läuft
ros2 service call /robot_map_manager/save_map std_srvs/srv/Trigger

# 4) sauber beenden - prüft selbst, ob das Wörterbuch geschrieben wurde
./stop_slam.sh
```

## Lokalisierung prüfen

```bash
./start_lokalisierung.sh /pfad/zum/lok.log     # delete_db:=false, localization:=true
python3 lokalisierung_test2.py                 # dreht 360° und zählt Lokalisierungen
./stop_slam.sh
```

## Auswertung

```bash
python3 karte_ansehen.py ~/.local/share/amadeus/maps/amadeus/<version>/
python3 merkmale_messen.py                     # Bildmerkmale + Tiefenabdeckung
```

---

## Drei Fallen, die hier real zugeschlagen haben

**1. Das visuelle Wörterbuch geht beim Beenden verloren.** Dann ist die Karte
geometrisch intakt, aber Lokalisierung unmöglich. Ursache ist *nicht* nur
`kill -9`: Ein `kill -INT -<PGID>` an die Prozessgruppe trifft rtabmap doppelt
(direkt vom Kernel und weitergereicht von launch) und bricht das Speichern
genauso ab — der Prozess stirbt mit `exit code -2`. Deshalb schickt
`stop_slam.sh` SIGINT **nur an den Launch-Prozess** und wartet, bis rtabmap von
selbst verschwunden ist. Zusätzlich setzt `start_slam.sh`
`sigterm_timeout:=120 sigkill_timeout:=180`, weil launch sonst nach 5 s
nachtritt. Kontrolle:

```bash
sqlite3 ~/.local/share/amadeus/rtabmap.db "SELECT COUNT(*) FROM Word;"   # muss > 0 sein
```

**2. Der collision_monitor kennt keine Fluchtbewegung.** Seine StopZone-Aktion
nullt *jede* Twist, auch reine Drehungen. Ein Roboter, der einmal in der
StopZone steht, kommt aus eigener Kraft nicht mehr heraus. `kartierfahrt.py`
hält deshalb selbst schon bei 0,35 m an (StopZone beginnt bei 0,26 m vor dem
Sensor), hat für jede Bewegung eine Frist und fährt zur Not rückwärts frei —
höchstens so weit, wie es gerade vorwärts kam, weil dort eben noch freier Raum
war. Rückwärts geht nur direkt auf `/cmd_vel`, weil der Monitor im
Stoppzustand auch das sperren würde.

**3. „map→odom ist nicht die Identität" beweist keine Lokalisierung.**
RTAB-Map lädt beim Start die zuletzt gespeicherte Pose aus der Datenbank und
setzt map→odom danach — ganz ohne Wiedererkennung. Belastbar ist allein
`/localization_pose`: darauf wird nur nach bestätigter Lokalisierung
publiziert. Und der Roboter muss sich bewegen, sonst verarbeitet RTAB-Map wegen
`RGBD/AngularUpdate` überhaupt keine Bilder.

## Was das Log nicht verrät

Erfolgreiche Wiedererkennungen stehen dort nicht in derselben Form wie die
Ablehnungen — `grep "Loop closure"` findet fast nur `... rejected!`. Die
Wahrheit steht in der Datenbank:

```bash
rtabmap-info ~/.local/share/amadeus/rtabmap.db | sed -n '/^Info:/,$p'
```
