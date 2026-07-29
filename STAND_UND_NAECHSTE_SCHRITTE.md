# Stand der Inbetriebnahme und nächste Schritte

**Letzte Aktualisierung: 27.07.2026 · Jetson `p-desktop` · Arbeitskopie `~/roboter_ws`**

Dieses Dokument hält fest, wo die Inbetriebnahme steht, was heute geprüft wurde und
womit beim nächsten Mal weitergemacht wird. Es ergänzt `Roboter_Pruefplan.md`
(dort steht das Verfahren, hier der Ist-Stand).

---

## 1. Kurzfassung

**Teil A der Inbetriebnahme ist abgeschlossen.** Alle acht Schritte sind gefahren,
Schritt 8 (Zusammenspiel mit dem KI-Server) fehlt nur noch auf der **Server**-Seite –
der Roboter selbst ist dafür bereit.

**Heute zuletzt geprüft: Stufe B3 – Onboard-Gesamtstart. Ergebnis: bestanden.**

Die Kartierung (SLAM) läuft technisch, wird aber **bewusst pausiert**, bis die neue
Kamera **OAK 4 D Pro** eintrifft – Kartieren und Objekterkennung hängen beide an ihr.

---

## 2. Ergebnis der Stufe B3 (Onboard-Gesamtstart)

`ros2 launch robot_bringup robot.launch.py` startet elf Komponenten. Alle laufen:

| Komponente | Status |
|---|---|
| `safety_monitor` | ✅ `/safety/estop = false` (frei) |
| `base_hardware` | ✅ Dry-Run (keine Motoren) |
| `vl53_near_field` + `collision_monitor` | ✅ Sensoren angebunden, Lifecycle aktiv |
| `robot_map_manager` | ✅ |
| `mission_manager`, `bt_orchestrator`, `explore_node` | ✅ |
| `rosbridge_websocket` (9090) | ✅ Port offen |
| `smartphone_gui` (8080), `robot_face` (8081) | ✅ Ports offen |
| `link_monitor` | ✅ |

Verfügbare Schnittstellen (Grundlage für Schritt 8):

- Actions: `/run_mission`, `/explore_area`, `/navigate_to_pose`
- Topics: `/mission_manager/command_json`, `/mission_manager/status_json`,
  `/safety/estop`, `/safety/estop_request`
- **0 Fehlerzeilen** im Startlog.

### 2.1 Zwei Vorbehalte zum Prüfskript

1. **`./pruefplan_jetson.sh --stage B3` meldet fälschlich „Fehlende Kern-Nodes:
   safety_monitor".** Die Stufe wartet nur **8 s** und fragt dann `ros2 node list` ab.
   Auf diesem Jetson ist die DDS-Discovery unter Last unzuverlässig – der Node läuft
   nachweislich (Logzeile „safety_monitor bereit"), erscheint aber noch nicht in der
   Liste. Nach **45 s** sind alle Nodes sichtbar.
   → *Verbesserungsvorschlag: Wartezeit in `stage_B3()` auf 30–45 s erhöhen.*
2. **Das Skript braucht eine gesourcte ROS-Umgebung.** Ohne
   `source /opt/ros/humble/setup.bash && source install/setup.bash` bricht es mit
   „ros2 nicht gefunden" ab.

### 2.2 Sicherheitsrelevanter Befund

```
[safety_monitor] WARN: Kein Hardware-Not-Aus angebunden (use_gpio_estop=false).
```

Der **Software**-Not-Aus (`/safety/estop`) ist derzeit **nicht** mit dem physischen
Not-Aus-Taster verdrahtet. Beide wirken unabhängig voneinander. Das ist für den
Betrieb wichtig zu wissen: Der Hardware-Taster trennt den Motorstrom, löst aber
keinen Software-Stopp aus – und umgekehrt.
→ *Offener Punkt: GPIO-Anbindung nach Ruhestromprinzip (`use_gpio_estop`).*

---

## 3. Nächster Schritt: Schritt 8 – Zusammenspiel mit dem KI-Server

Der Roboter ist bereit. Zu tun ist die **zweite Maschine**:

1. Server ins **gleiche WLAN**, gleiche `ROS_DOMAIN_ID` (auf dem Jetson: **42**).
2. Auf dem Server `ros2 launch robot_bringup server.launch.py` – startet
   `llm_planner` und `semantic_perception`.
3. Prüfstufen der Reihe nach:
   ```bash
   ./pruefplan_jetson.sh --stage C1   # Server sichtbar
   ./pruefplan_jetson.sh --stage C2   # Sprache -> Auftrag
   ./pruefplan_jetson.sh --stage C3   # iPhone -> Mission
   ```
   (vorher ROS sourcen, s. 2.1)

**Gute Nachricht:** Schritt 8 braucht die Kamera **nicht**. `semantic_perception`
läuft standardmäßig im Stub-Modus (`model_backend: "stub"`), der Rest ist Sprache,
Missionslogik und Bedienoberfläche.

---

## 4. Warum die Kartierung pausiert

SLAM funktioniert (RTAB-Map 0.23.7, Karten bis 6,7 × 6,2 m aufgenommen und
versioniert gespeichert). Pausiert wird trotzdem, weil die **OAK 4 D Pro** kommt:
Sowohl die Kartenqualität als auch die Objekterkennung hängen unmittelbar an der
Kamera, und die Montagepose muss nach dem Tausch ohnehin neu vermessen werden.

**Beim Kamerawechsel zu tun:**

1. Neue Kamera anstecken – das Modell erkennt der Treiber automatisch.
2. **Montagepose neu vermessen** und in `robot_bringup/launch/oak.launch.py`
   (einziger markierter Block oben) **und** in der URDF eintragen.
   Aktuell: x = 0,150 · y = 0 · z = 1,250 über `base_link` · pitch 0,3306 rad (18,94°).
3. Ggf. Auflösungsnamen anpassen – Vorlage:
   `/opt/ros/humble/share/depthai_ros_driver/config/oak_d_pro_w.yaml`
   (dort `rgb.i_resolution: '720'` – **ohne** „P"!).
4. Karte **neu aufnehmen** (andere Optik = andere Merkmale).

**Offen aus der Kartierung** (Details in der Sitzungshistorie):

- **Lokalisierung ist unbewiesen.** Der Nachweis, dass sich der Roboter visuell in
  einer gespeicherten Karte wiederfindet, steht aus. Ein Versuch scheiterte an einer
  beschädigten Datenbank; nach Neuaufnahme war das Ergebnis mehrdeutig.
- **Befahrbare Fläche klein**: von 7,5 m² Freifläche bleiben bei `robot_radius 0.40`
  nur 3,05 m² (3,10 × 1,85 m). Begrenzender Faktor ist der vollgestellte Raum.

---

## 5. Betriebswissen – bitte beachten

Diese Punkte haben real Zeit gekostet:

1. **`rtabmap` NIE mit `kill -9` beenden.** Es schreibt das visuelle Wörterbuch erst
   beim Herunterfahren (~5 s nach `SIGINT`). Ein SIGKILL macht die Karte für die
   Lokalisierung unbrauchbar und **nicht reparierbar**.
2. **`base_hardware` immer mit `SIGINT` beenden.** Der ESS23-RS läuft im Speed-Modus
   ohne motorseitigen Watchdog – bei hartem Abschuss **fährt der Motor weiter**.
   `destroy_node()` sendet den Stopp.
3. **`/map` wird `TRANSIENT_LOCAL` publiziert** – Abonnenten mit Standard-QoS sehen
   nichts. Und `ros2 node list` / `topic list` liefern auf diesem Jetson sporadisch
   leere Ergebnisse; das ist **kein** Beweis für Abwesenheit.
4. **`pgrep -f "…base_hardware…"` trifft die eigene Shell.** Immer `MY=$$` setzen und
   `[ "$p" = "$MY" ] || kill …`, sonst schießt sich der Aufräumbefehl selbst ab.
5. **Kaltstart-Race:** Der erste Start größerer Launches scheitert gelegentlich
   („Failed to change state for node …"). Ein erneuter Start ist zuverlässig grün.
6. **Nie direkt auf `/cmd_vel` publizieren** – immer auf `cmd_vel_smoothed`, sonst
   wird der `collision_monitor` (Notbremse) umgangen.
7. **PGM-Semantik:** `0` = belegt, **`205` = unbekannt**, `254` = frei.

---

## 6. Sicherheitsregeln

- Motortests zuerst **aufgebockt**, dann langsam am Boden.
- **Hardware-Not-Aus** bei jeder Fahrt in Reichweite – er ersetzt den Software-Stopp
  nicht und wird von ihm nicht ersetzt (s. 2.2).
- Standard bleibt `dry_run: true` / `allow_rs485: false`; scharf nur bewusst per
  Launch-Argument `active_drive:=true`.
- Nie allein am fahrenden Roboter arbeiten.
