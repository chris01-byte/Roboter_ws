# smartphone_gui (WP-4)

Mobile Web-App/PWA fuer den Roboter — laeuft im Browser jedes Smartphones,
optimiert fuer iPhone (Home-Bildschirm-App, siehe unten).

## Funktionen

| Bereich | Was es tut |
|---|---|
| Raum / Greifen / Bringen | Auftraege an den `mission_manager` (Bringen laeuft seit K1 ECHT ueber den Behavior-Tree) |
| **Erkunden** | startet die autonome Wohnungs-Erkundung (`{"type": "explore"}`) |
| **NOT-AUS** | publiziert `/safety/estop_request` an den `safety_monitor` (K4); Knopf zeigt den Ist-Zustand von `/safety/estop` (aktiv = dunkelrot, pulsierend) und gibt wieder frei |
| KI-Pill | zeigt `offboard_available` (KI-Server erreichbar?) aus dem Status |
| Log | inkl. abgelehnter Auftraege (`last_rejection`) und Not-Aus-Ereignisse |

> Sicherheit: Die GUI sendet keine direkten Motorbefehle — nur Auftraege an den
> `mission_manager` und die Not-Aus-ANFORDERUNG an den `safety_monitor`. Der
> Software-Not-Aus ersetzt NICHT den Hardware-Not-Aus (Ruhestromprinzip, s. safety_monitor).

## Start auf dem Jetson
```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 launch smartphone_gui smartphone_gui.launch.py
```

Dann am Smartphone im gleichen WLAN oeffnen: `http://JETSON-IP:8080`
(die App verbindet sich per rosbridge mit `ws://JETSON-IP:9090`).

## Als App auf dem iPhone installieren (einmalig)

1. In **Safari** `http://JETSON-IP:8080` oeffnen.
2. **Teilen-Symbol** -> **"Zum Home-Bildschirm"** -> Hinzufuegen.
3. Es erscheint ein "Roboter"-Icon; die App startet im Vollbild (ohne Safari-Leiste).

Hinweis fuer Entwickler: Die PWA cached sich selbst (Service Worker, cache-first).
**Nach jeder Aenderung an `web/`-Dateien in `web/sw.js` den `CACHE_NAME` hochzaehlen**,
sonst zeigt das iPhone ewig die alte Version.
