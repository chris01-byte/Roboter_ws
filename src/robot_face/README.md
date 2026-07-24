# robot_face — Reaktives Cartoon-Gesicht für das Roboter-Display

Rundes Cartoon-Gesicht (Augen, Augenbrauen, Nase, Mund, Wangen) für das
**7-Zoll-HDMI-Display am Jetson**. Reagiert auf System-Ereignisse — ohne dass
ein bestehender Node angepasst werden muss (gleiches Vorschalt-Muster wie
`llm_planner`).

## Architektur

```
mission_manager/status_json  ─┐
/safety/estop                ─┤
/offboard/available          ─┼─> [face_controller] ─> /face/state_json ─> web/face.js (SVG)
llm_planner/status+instruction┤        ^
/face/event  (generischer Bus)┘        └── config/event_expression_map.yaml
```

- **`face_controller`**: sammelt Ereignisse, waehlt per Prioritaet den aktiven
  Ausdruck (Not-Aus = 100, ueberstimmt immer alles) und publiziert
  `/face/state_json`. Kurz-Ereignisse haben eine Anzeigedauer (`ttl_s`),
  Zustaende (E-Stop, Mission laeuft, Offboard weg) bleiben bis zur Aufloesung.
  Ohne Aktivitaet schlaeft das Gesicht ein (`sleep_timeout_s`).
- **Design:** humanoides Android-Gesicht (weisse Hochglanz-Schale, Panel-Fugen, technische blaue
  Iris, mechanischer Hals mit blauer Leuchte) nach Referenzbildern. Die Ausdrucks-Engine ist davon
  unabhaengig - ein Redesign tauscht nur die SVG-Artwork, IDs/Parameter bleiben gleich.
- **`web/index.html`**: SVG-Gesicht, weiches Morphing zwischen 9 Ausdruecken
  (`neutral, listening, thinking, happy, sad, surprised, alarm, confused,
  sleeping`) plus Idle-Leben (Blinzeln, Blickwandern, Atmen). Verbindung wie
  die Smartphone-GUI per rosbridge (`ws://<host>:9090`).
  **Bewusst eine einzige Datei** (CSS + JS inline): rendert dadurch auch bei
  Datei-Doppelklick, in Vorschau-Panels und unvollstaendigen Kopien korrekt —
  ohne Stylesheet wuerde das Gesicht sonst als schwarzer Kreis erscheinen
  (SVG-Fallback-Farbe, genau so einmal passiert).

## Neue Ausloeser ergaenzen (ohne Code!)

Kuenftige Sensorik (Personenerkennung, Beruehrung, Mikrofon, ...) publiziert
einfach auf `/face/event`:

```bash
ros2 topic pub --once /face/event std_msgs/msg/String \
  "{data: '{\"event\": \"person_detected\"}'}"
```

und bekommt ihren Eintrag in
[config/event_expression_map.yaml](config/event_expression_map.yaml)
(`expression`, `prio`, `ttl_s`) — Beispiele stehen schon drin. Alternativ ohne
Map-Eintrag direkt: `{"expression": "happy", "prio": 50, "ttl_s": 3}`.

## Starten

```bash
ros2 launch robot_face robot_face.launch.py
# falls rosbridge NICHT schon laeuft (smartphone_gui.launch.py startet ihn sonst):
ros2 launch robot_face robot_face.launch.py with_rosbridge:=true
```

Anzeige: `http://<JETSON-IP>:8081` (Port 8081, damit die Smartphone-GUI auf
8080 parallel laufen kann).

## Kiosk-Modus auf dem 7-Zoll-Display (Jetson)

Einmalig einrichten, damit das Gesicht nach dem Booten vollbild erscheint:

```bash
sudo apt install chromium-browser unclutter
```

Autostart-Eintrag (`~/.config/autostart/robot-face.desktop`):

```ini
[Desktop Entry]
Type=Application
Name=Robot Face
Exec=chromium-browser --kiosk --noerrdialogs --disable-infobars \
     --check-for-update-interval=31536000 http://localhost:8081
```

`unclutter` blendet den Mauszeiger aus (die Seite tut das zusaetzlich per CSS).
Displayaufloesung ist egal — das SVG skaliert (getestetes Seitenverhaeltnis
1000x620, passend fuer 1024x600-Panels).

## Testen ohne ROS / ohne Roboter

`web/index.html` direkt im Browser oeffnen (oder den Webserver starten):
Tasten **1–9** schalten die Ausdruecke direkt um, **Tippen/Klicken** geht der
Reihe nach durch. Der rosbridge-Punkt unten rechts bleibt dann rot — normal.
Vom Terminal aus testen (mit ROS):

```bash
ros2 topic pub --once /face/event std_msgs/msg/String \
  "{data: '{\"expression\": \"surprised\", \"ttl_s\": 3}'}"
```

## Grenzen / offen

- Wie die uebrigen Pakete noch nicht in einer ROS-Umgebung kompiliert
  (`py_compile` bestanden; Web-App im Browser getestet).
- Stimme/Ton ist bewusst ausgeklammert (Projektentscheidung); Kandidat fuer
  spaeter: Piper TTS lokal auf dem Jetson + kurze Klang-Cues bei
  Ausdruckswechseln.
- `mission_canceled -> sad` u. Ae. sind Startwerte — Feintuning ist reiner
  YAML-Eingriff.
