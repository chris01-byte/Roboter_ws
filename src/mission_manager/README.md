# mission_manager (WP-4)

Sichere Zwischenschicht zwischen Smartphone-GUI und Robotik-Logik.

## Aktueller Stand
Der Node nimmt JSON-Auftraege auf `/mission_manager/command_json` entgegen und publiziert Status auf `/mission_manager/status_json`.

`pick_and_place` und `explore` werden als echte `RunMission`-Action an den
`bt_orchestrator` weitergegeben. `pick_object` simuliert seine Phasen weiterhin.
`go_to_room` loest bereits ein konkretes Ziel aus der manuellen semantischen
Raumkarte auf, bleibt aber absichtlich eine reine Vorbereitungssimulation:
Es wird weder eine Action noch ein Nav2-Ziel oder ein Fahrbefehl gesendet.
Selbst ein versehentlicher Eintrag von `go_to_room` in `real_mission_types`
wird ignoriert. Ein Abbruch waehrend der
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
{"type":"go_to_room","room_id":"room-wohnzimmer","room":"Wohnzimmer"}
{"type":"pick_object","object":"Tasse"}
{"type":"pick_and_place","object":"Tasse","room":"Kueche","target":"Tisch"}
{"type":"explore"}
{"type":"cancel"}
```

### Ausgang
`/mission_manager/status_json` (`std_msgs/String`)

Enthaelt Zustand, Phase, Meldung, Raum-/Objektlisten, aktiven Auftrag und das
additive Bool-Feld `cancel_pending`. Fuer die Raumvorbereitung kommen additiv
hinzu:

- `semantic_map`: Verfuegbarkeit, Fehler, Fingerprint, Revision und Frame des
  zuletzt vollstaendig validierten Snapshots;
- `resolved_room_goal`: kanonische Raum-ID/-Name, Kartenbindung und endliche
  Pose `{x,y,yaw}` oder `null`;
- `go_to_room_execution`: immer `simulation_only_no_navigation`.
- `pick_and_place_rooms`: die unveränderte statische Raum-Allowlist der
  bestehenden realen Pick-and-Place-Mission;
- `semantic_map.status_age_seconds` und `stale_timeout_seconds`: Frische des
  ausschließlich vorbereitenden Raumziels.

## Read-only Vertrag zur semantischen Karte

Der Manager abonniert transient-local:

```text
/semantic_map/status_json   std_msgs/String
/semantic/catalog_json      std_msgs/String
```

Ein Raumziel wird nur aus einem Status dieser Form vorbereitet:

```json
{
  "schema_version": 1,
  "ok": true,
  "semantic_map": {
    "map_ref": {
      "fingerprint": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
      "frame_id": "map"
    },
    "revision": 7,
    "rooms": [{
      "id": "room-wohnzimmer",
      "name": "Wohnzimmer",
      "polygon": [
        {"x":0.0,"y":0.0},{"x":4.0,"y":0.0},
        {"x":4.0,"y":3.0},{"x":0.0,"y":3.0}
      ],
      "navigation_goal": {"x":2.0,"y":1.5,"yaw":1.57}
    }],
    "editable": true
  }
}
```

Fail-closed geprueft werden `ok`, Fingerprint, erwarteter Frame,
nichtnegative Revision, eindeutige Raum-ID/-Name, endliche Pose, gueltiges
Raumpolygon, `editable:true` und eine Zielposition strikt innerhalb dieses
Polygons. Ein neuer ungueltiger Status invalidiert den vorherigen Cache. Bleibt
der Status länger als `semantic_map_status_stale_timeout_s` (Standard sechs
Sekunden) aus, wird der Cache anhand einer monotonic clock ebenfalls verworfen;
eine laufende `go_to_room`-Vorbereitung endet ohne Fahrt als Fehler. Optional kann
`semantic_map_expected_fingerprint` in `config/mission_catalog.yaml` auf eine
bestimmte metrische Karte verriegelt werden.

Der dynamische Auswahlkatalog akzeptiert ausschließlich Räume vom Vertrag
`schema_version:1`, `source:"semantic_map_manager"`. Namenslisten und
Raumobjekte mit `name` sind kompatibel; Fehler, Leereinträge, mehr als 256
Räume oder mehr als 512 KiB ersetzen den statischen Fallback nicht. Objekte,
Ablageziele und die echte `pick_and_place`-Raum-Allowlist bleiben statisch und
können über dieses Topic nicht erweitert werden. `go_to_room` verlangt
unabhängig vom Auswahlkatalog das passende Ziel im frischen, gültigen Snapshot.
Eine gültige leere Raumliste stellt bewusst die konfigurierte Fallbackliste
wieder her, statt zuvor gelöschte dynamische Namen festzuhalten.

Das Missionskommando selbst ist auf 64 KiB begrenzt. Nicht-UTF-8-kompatible,
zu tief verschachtelte und übergroße JSON-Nachrichten werden abgefangen und
ändern weder Mission noch Freigabelisten.

Der kanonische Polygonvertrag verwendet Punktobjekte `{"x":...,"y":...}`.
Zweierlisten `[x,y]` bleiben nur fuer bereits erzeugte lokale Test-/Altdaten
read-only kompatibel.

## Lokale Tests

Ohne laufendes ROS:

```bash
cd /Volumes/64GB/roboter_ws
PYTHONPATH=src/mission_manager \
  python3 -m unittest discover -s src/mission_manager/test -v
```

Die Tests pruefen neben den vorhandenen Action-/JSON-Vertraegen insbesondere
Fingerprint-/Revisionsbindung, endliche und innerhalb des Raums liegende
Zielposen, Status-Frische, Katalog-Fallback, getrennte reale Allowlists und die
unverrueckbare Simulationsbarriere fuer `go_to_room`.
