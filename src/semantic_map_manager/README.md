# semantic_map_manager

ROS-2-Humble-Paket für manuell in der Amadeus-App deklarierte Räume. Das
Paket legt ein versioniertes semantisches Overlay über eine bereits
gespeicherte metrische Karte. Es verändert weder die OccupancyGrid-Karte noch
RTAB-Map-Datenbanken.

Der Node besitzt **keinen** `cmd_vel`-Publisher, keine Nav2-Action und keine
Motor-/Missionsschnittstelle. Ein `navigation_goal` ist in dieser Stufe nur
gespeicherte, geometrisch geprüfte Metadaten und löst niemals eine Fahrt aus.

## Warum die Kartenbindung fail-closed ist

Jede metrische Karte des `robot_map_manager` besitzt einen SHA-256-
Fingerabdruck. Ein Overlay wird ausschließlich unter diesem Fingerabdruck
gespeichert. Die erste Bindung ist nur erlaubt, wenn derselbe aktuelle
`map.summary.fingerprint` zusätzlich durch mindestens einen gespeicherten
Eintrag bestätigt wird:

- `storage.last_saved` in einem normalen Status/Save-Status oder
- `maps[]` in einem `list_result`.

Der fremde Status muss `ok: true` melden. Ein alter Snapshot in einem
Fehlerstatus kann daher keine Bindung oder Bearbeitung freigeben. Nach der
ersten bestätigten Bindung darf der persistierte Datensatz bei einem Neustart
anhand identischen Fingerabdrucks und identischer Geometrie wieder aktiviert
werden, auch wenn der neue `robot_map_manager` noch `last_saved: null` meldet.

Ändert sich der Fingerabdruck, widerspricht die Geometrie, fällt der
Kartenmanager aus oder bleibt sein Status standardmäßig länger als sechs
Sekunden aus, wird `editable` sofort `false`. Schreibkommandos scheitern dann,
bis ein neuer gültiger Status eintrifft. Das gilt ebenso für Retries mit einer
bereits bekannten `request_id`: Der Node publiziert niemals eine alte gecachte
Antwort, sondern prüft Frische und Fingerabdruck neu und antwortet mit dem
aktuellen Snapshot. Auch `bind_map` verlangt unmittelbar vor der persistenten
Bindung einen frischen Kartenmanager-Status.

## ROS-Schnittstellen

| Richtung | Topic | Typ | QoS |
|---|---|---|---|
| Eingang | `/robot_map_manager/status_json` | `std_msgs/msg/String` | reliable, transient-local |
| Eingang | `/semantic_map/command_json` | `std_msgs/msg/String` | reliable, volatile |
| Ausgang | `/semantic_map/status_json` | `std_msgs/msg/String` | reliable, transient-local |
| Ausgang | `/semantic/catalog_json` | `std_msgs/msg/String` | reliable, transient-local |

Statusantworten besitzen immer diesen Umschlag:

```json
{
  "schema_version": 1,
  "event": "get_result",
  "ok": true,
  "request_id": "ios:42",
  "message": "Aktueller semantischer Kartenstand.",
  "semantic_map": {
    "map_ref": {
      "name": "wohnung",
      "version": "20260814T120000000000Z-abcdef123456",
      "fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "frame_id": "map",
      "width": 100,
      "height": 80,
      "resolution": 0.1,
      "origin": {
        "position": {"x": 0.0, "y": 0.0, "z": 0.0},
        "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0},
        "yaw": 0.0
      }
    },
    "revision": 3,
    "rooms": [],
    "editable": true,
    "edit_block_reason": null,
    "updated_at": "2026-08-14T12:34:56.123456Z"
  }
}
```

Der kompatible Katalog liefert `rooms` bewusst als Liste von Raumnamen. Neue
Verbraucher erhalten strukturierte Daten zusätzlich unter `room_entities`:

```json
{
  "schema_version": 1,
  "ok": true,
  "source": "semantic_map_manager",
  "rooms": ["Wohnzimmer"],
  "room_entities": [
    {
      "id": "wohnzimmer",
      "name": "Wohnzimmer",
      "navigation_goal": {"x": 2.0, "y": 2.0, "yaw": 0.5}
    }
  ],
  "map_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "revision": 3,
  "editable": true
}
```

Bei gesperrter Bindung meldet der Katalog `ok: false` und keine Räume. So
werden alte Räume nicht versehentlich als Ziele einer anderen Karte verwendet.

## JSON-Kommandos

Alle Kommandos sind strikt schemavalidiert; unbekannte Felder werden
verworfen. Das Größenlimit beträgt 64 KiB. Schreibkommandos benötigen eine
sichere `request_id`, den aktuellen `map_fingerprint` und `base_revision`.

### Zustand lesen

```json
{"command":"get","request_id":"ios:get:42"}
{"command":"status","request_id":"ios:status:42"}
```

### Bestätigte Version explizit binden

Normalerweise geschieht dies nach `save`/`list` automatisch. Die explizite
Variante kann nur exakt eine im aktuellen Kartenmanager-Status bestätigte
Version auswählen:

```json
{
  "command": "bind_map",
  "request_id": "ios:bind:1",
  "map_ref": {
    "name": "wohnung",
    "version": "20260814T120000000000Z-abcdef123456",
    "fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
}
```

### Raum anlegen oder aktualisieren

```json
{
  "command": "upsert_room",
  "request_id": "ios:room:wohnzimmer:7",
  "map_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "base_revision": 3,
  "room": {
    "id": "wohnzimmer",
    "name": "Wohnzimmer",
    "color": "#31A8FF",
    "polygon": [
      {"x": 1.0, "y": 1.0},
      {"x": 4.0, "y": 1.0},
      {"x": 4.0, "y": 3.0},
      {"x": 1.0, "y": 3.0}
    ],
    "navigation_goal": {"x": 2.0, "y": 2.0, "yaw": 0.5}
  }
}
```

Validiert werden unter anderem:

- ID: 1–64 Zeichen aus `a-z`, `0-9`, `_`, `-`;
- Name: NFC-normalisiert, nichtleer, höchstens 80 Zeichen, keine
  Steuerzeichen;
- optionale Farbe exakt als `#RRGGBB`;
- 3–64 endliche Kartenpunkte je Raum innerhalb des metrischen
  Kartenrechtecks;
- höchstens 4.096 Polygonpunkte im gesamten Dokument; dieses Gesamtlimit wird
  bei einer Mutation bereits vor der quadratischen Selbstschnittprüfung des
  neuen Polygons geprüft;
- keine doppelten Punkte, Nullfläche oder Selbstschneidung/-berührung;
- endliches `navigation_goal`, `yaw` zwischen −π und +π und der Punkt strikt
  innerhalb des Polygons (nicht auf dessen Kante);
- eindeutige Raum-IDs und Namen.

Das Kartenrechteck berücksichtigt auch einen gedrehten OccupancyGrid-Ursprung.

### Raum löschen

```json
{
  "command": "delete_room",
  "request_id": "ios:delete:wohnzimmer:8",
  "map_fingerprint": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "base_revision": 4,
  "room_id": "wohnzimmer"
}
```

## Konkurrenz und Wiederholungen

`base_revision` implementiert optimistic concurrency. Stimmen App-Revision und
aktuelle Revision nicht überein, wird nichts geschrieben; die App muss zuerst
`get` ausführen und den Konflikt bewusst auflösen.

Die letzten 256 erfolgreichen Schreib-`request_id`s werden zusammen mit der
kanonischen Kommandosignatur persistiert. Ein Retry derselben Anfrage erzeugt
keine weitere Revision – auch nach einem Node-Neustart. Dieselbe ID mit
anderem Inhalt ist ein Konflikt. Nach Verdrängung aus dem begrenzten Log gilt
eine alte ID wieder als neu; Clients sollen daher dauerhaft eindeutige IDs
verwenden. Der zusätzliche Laufzeitcache speichert nur ID und SHA-256-Signatur,
keine JSON-Antwort. Standardmäßig begrenzen ihn gleichzeitig 128 Einträge und
64 KiB; dadurch kann ein großer Kartenstatus den RAM nicht vervielfachen.

## Speicherung

Wohnungsdaten bleiben außerhalb des Repositories:

```text
~/.local/share/amadeus/semantic_maps/<fingerprint>/
├── current.json
└── revisions/
    ├── 00000000000000000000.json
    ├── 00000000000000000001.json
    └── ...
```

Jede Revision ist unveränderlich. Unter einem prozessübergreifenden `flock`
wird sie zuerst unter einem zufälligen Namen vollständig geschrieben und per
`fsync` gesichert. Erst danach veröffentlicht ein atomarer Hardlink den
endgültigen Revisionsnamen ohne Überschreibemöglichkeit. Ein ENOSPC oder
Abbruch kann daher nur eine entfernte Tempdatei, niemals eine sichtbare
Teilrevision hinterlassen. Anschließend wird `current.json` per atomarem Rename
ersetzt und das Verzeichnis synchronisiert. Bleibt nach einem Stromausfall eine
vollständig geschriebene Revision ohne `current.json` zurück, wird die jüngste
gültige Revision beim nächsten Start fail-safe wiederhergestellt. Existiert
noch ein älteres `current.json`, wird ausschließlich der exakt nächste,
geometrisch identische und request-log-konsistente Commit übernommen. Ein
Revisionssprung oder widersprüchlicher Nachfolger bleibt fail-closed. Dadurch
verwendet ein Retry auch das ursprüngliche `updated_at` und erzeugt keine
kollidierende Variante derselben unveränderlichen Revision.
Symlink-Ablagen, beschädigte Dateien, falsche Fingerabdrücke oder
widersprüchliche Geometrien werden verworfen.

Standardmäßig gelten zusätzlich harte Verfügbarkeitsgrenzen:

- höchstens 2.048 unveränderliche Revisionen je Kartenfingerabdruck;
- höchstens 1 GiB logische Dateidaten im gesamten Semantik-Repository;
- nach einem Commit müssen mindestens 512 MiB Dateisystemspeicher frei bleiben;
- einzelne Dokumente einschließlich Abschluss-Newline höchstens 4 MiB.
- höchstens 64 Polygonpunkte je Raum und 4.096 Polygonpunkte insgesamt, damit
  die O(P²)-Selbstschnittprüfung eine harte Laufzeitobergrenze besitzt.

Wird eine Grenze erreicht, bleibt die letzte gültige Revision lesbar und der
neue Commit scheitert vor dem Publizieren einer Revisionsdatei. Die Grenzen
sind über `max_revisions_per_map`, `max_storage_bytes` und
`min_free_space_bytes` konfigurierbar; der ROS-Node akzeptiert dennoch nur
endliche, defensiv begrenzte Werte. Vor einer bewussten Erhöhung muss die alte
Historie außerhalb des laufenden Repositorys archiviert werden.

Es gibt absichtlich kein automatisches Löschen oder Überschreiben alter
Revisionen. Erreichen der Grenze ist sichtbar und fail-closed, nicht Anlass
für einen stillen Datenverlust.

## Build und Start

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select semantic_map_manager
source install/setup.bash
ros2 launch semantic_map_manager semantic_map_manager.launch.py
```

Status und Kommandobeispiel:

```bash
ros2 topic echo /semantic_map/status_json
ros2 topic pub --once /semantic_map/command_json std_msgs/msg/String \
  "{data: '{\"command\":\"get\",\"request_id\":\"shell:get:1\"}'}"
```

Dieser Start enthält keine Aktoren und benötigt keine Fahrfreigabe.

## ROS-unabhängige Tests

```bash
cd ~/roboter_ws
PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH=src/semantic_map_manager \
python3 -m unittest discover -s src/semantic_map_manager/test -v
```

Die Tests decken Kartenstatus/echtes Versionsformat, strikte JSON- und
Geometrievalidierung, gedrehte Kartenursprünge, Selbstschnitt, Kartenmismatch,
Revisionen, parallele Autoren, persistente Idempotenz, frische Replay-
Snapshots, Rekursionstiefen-Angriffe, Speicher-/Revisionslimits, partielle
ENOSPC-Schreibvorgänge, Recovery bei älterem `current.json`, abgewiesene
Revisionssprünge, Polygon-Komplexitätsgrenzen, Korruption, Symlinks und
Stromausfall-Recovery ab.

## Bewusste Grenzen dieser ersten Stufe

- Räume werden ausschließlich vom Menschen in der App deklariert; es gibt
  noch keine automatische Raumsegmentierung.
- Das `navigation_goal` liegt geometrisch im Polygon. Ob die Zelle frei,
  ausreichend weit von Hindernissen und für Nav2 erreichbar ist, muss vor
  einer späteren Fahrt zusätzlich gegen Costmap/Planner geprüft werden.
- Überlappende Polygone verschiedener Räume werden noch nicht verboten. Das
  ermöglicht zunächst Korrekturen, verlangt aber eine eindeutige Regel vor
  automatischer Punkt-zu-Raum-Zuordnung.
- Es gibt noch keine Migration von Semantik zwischen unterschiedlichen
  Kartenfingerabdrücken.
- Objekte und Möbel sind nicht Teil dieses Paketschritts. Der bestehende
  Objektkatalog wird nicht überschrieben.
