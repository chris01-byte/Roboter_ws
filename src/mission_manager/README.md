# mission_manager (WP-4)

Sichere Zwischenschicht zwischen Smartphone-GUI und Robotik-Logik.

## Aktueller Stand
Der Node nimmt JSON-Auftraege auf `/mission_manager/command_json` entgegen und publiziert Status auf `/mission_manager/status_json`.

`pick_and_place` und `explore` werden als echte `RunMission`-Action an den
`bt_orchestrator` weitergegeben. `go_to_room` und `pick_object` simulieren ihre
Phasen noch, bis eigene Behavior Trees existieren. Ein Abbruch waehrend der
asynchronen Goal-Annahme wird vorgemerkt und nach Annahme sofort
serverseitig weitergegeben. Die Cancel-Antwort wird fuer genau diese Goal-ID
geprueft; erst der terminale Action-Status `SUCCEEDED`, `CANCELED` oder
`ABORTED` beendet die Mission. Bis dahin wird kein neuer Auftrag angenommen.

## Topic-Vertrag

### Eingang
`/mission_manager/command_json` (`std_msgs/String`)

Beispiele:
```json
{"type":"go_to_room","room":"Wohnzimmer"}
{"type":"pick_object","object":"Tasse"}
{"type":"pick_and_place","object":"Tasse","room":"Kueche","target":"Tisch"}
{"type":"explore"}
{"type":"cancel"}
```

### Ausgang
`/mission_manager/status_json` (`std_msgs/String`)

Enthaelt Zustand, Phase, Meldung, Raum-/Objektlisten, aktiven Auftrag und das
additive Bool-Feld `cancel_pending`.

## Lokale Tests

Ohne laufendes ROS:

```bash
cd /Volumes/64GB/roboter_ws
PYTHONPATH=src/mission_manager \
  python3 -m unittest discover -s src/mission_manager/test -v
```
