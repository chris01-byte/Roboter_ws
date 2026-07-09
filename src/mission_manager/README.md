# mission_manager (WP-4)

Sichere Zwischenschicht zwischen Smartphone-GUI und Robotik-Logik.

## Aktueller Stand
Der Node nimmt JSON-Auftraege auf `/mission_manager/command_json` entgegen und publiziert Status auf `/mission_manager/status_json`.

Er simuliert die Missionsphasen noch ohne echte Hardware. Spaeter ersetzt diese Stelle die Simulation durch das Starten/Parametrisieren des Behavior Trees.

## Topic-Vertrag

### Eingang
`/mission_manager/command_json` (`std_msgs/String`)

Beispiele:
```json
{"type":"go_to_room","room":"Wohnzimmer"}
{"type":"pick_object","object":"Tasse"}
{"type":"pick_and_place","object":"Tasse","room":"Kueche","target":"Tisch"}
{"type":"cancel"}
```

### Ausgang
`/mission_manager/status_json` (`std_msgs/String`)

Enthaelt Zustand, Phase, Meldung, Raum-/Objektlisten und aktiven Auftrag.
