# Semantische Wohnungskarte und manueller Raumeditor

**Stand:** 14.08.2026

**Branch:** `feature/semantic-map-editor`

**Hardwarewirkung:** keine; alle in diesem Dokument beschriebenen
Entwicklungs- und Offline-Tests bleiben ohne Fahrbefehle

## 1. Ziel und Abgrenzung

Die metrische `nav_msgs/OccupancyGrid`-Karte bleibt die einzige geometrische
Grundlage fuer SLAM und Nav2. Die semantische Karte ist eine getrennte,
versionierte Ebene darueber. In der ersten Ausbaustufe zeichnet der Benutzer
Raeume selbst in der iOS-App ein und gibt jedem Raum einen Namen sowie einen
Navigationspunkt.

Ein Raum-Polygon ist **keine Freigabe zum Fahren**. Vor einer spaeteren echten
Raumfahrt muss Nav2 den Zielpunkt noch gegen Karte, Kostenkarte, Roboterfreiraum
und Erreichbarkeit pruefen. `go_to_room` bleibt bis zu dieser Abnahme im
Simulationsmodus.

Nicht Bestandteil der ersten Stufe:

- automatische Raumsegmentierung;
- automatisches Eintragen oder Persistieren erkannter Gegenstaende;
- Aenderungen an Motor-, Odometrie-, LiDAR- oder Sicherheitsparametern;
- autonomer Fahrtest.

## 2. Quellen der Wahrheit

| Information | Verantwortliches Paket |
|---|---|
| belegte, freie und unbekannte Zellen | SLAM beziehungsweise Kartenserver |
| unveraenderliche Kartenversion und Fingerabdruck | `robot_map_manager` |
| Raum-Polygone, Namen, Navigationspunkte und Revision | `semantic_map_manager` |
| Darstellung und manuelle Bearbeitung | native iOS-App `Amadeus` |
| Missionsvalidierung und vorbereitete Raumziel-Aufloesung | `mission_manager` |
| Sprache zu Missionsauftrag | `llm_planner` |
| fluechtige Kameraerkennungen | `semantic_perception` |

Der Wahrnehmungsknoten darf den manuellen Raumkatalog nicht ueberschreiben.
Deshalb ist `/semantic/catalog_json` allein dem `semantic_map_manager`
zugeordnet. `semantic_perception` publiziert seinen Diagnosekatalog getrennt
auf `/semantic/perception_catalog_json`.

## 3. Bindung an eine Kartenversion

`robot_map_manager` bildet aus Dimensionen, Aufloesung, Frame, Ursprung und
allen Occupancy-Zellen einen SHA-256-Fingerabdruck. Jede semantische Karte
enthaelt eine vollstaendige `map_ref` mit mindestens:

```json
{
  "name": "wohnung",
  "version": "20260814T120000000000Z-0123456789ab",
  "fingerprint": "64-kleinbuchstabige-hexzeichen",
  "frame_id": "map",
  "width": 800,
  "height": 600,
  "resolution": 0.03,
  "origin": {
    "position": {"x": -5.0, "y": -4.0, "z": 0.0},
    "orientation": {"x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0}
  }
}
```

Eine erstmalige Bindung ist nur erlaubt, wenn `robot_map_manager` dieselbe
Karte als erfolgreich gespeicherte Version bestaetigt. Nach einem Neustart
darf eine bereits bestehende semantische Karte anhand desselben Fingerabdrucks
und derselben Geometrie wieder aktiviert werden. Ein anderer Fingerabdruck
sperrt Bearbeitung und Overlay fail-closed; es gibt keine stille Migration.
Dasselbe gilt bei `ok:false` oder wenn der Kartenmanager länger als sechs
Sekunden keinen neuen Status liefert.

Echte Wohnungsgeometrie bleibt gemaess `AGENTS.md` ausserhalb des Repositories:

```text
~/.local/share/amadeus/semantic_maps/<fingerprint>/
  current.json
  revisions/<20-stellige-revision>.json
```

## 4. Raummodell

Ein Raum besitzt:

```json
{
  "id": "room-550e8400-e29b-41d4-a716-446655440000",
  "name": "Wohnzimmer",
  "color": "#4A90E2",
  "polygon": [
    {"x": 0.40, "y": 0.30},
    {"x": 4.80, "y": 0.30},
    {"x": 4.80, "y": 3.90},
    {"x": 0.40, "y": 3.90}
  ],
  "navigation_goal": {"x": 2.10, "y": 1.80, "yaw": 1.57}
}
```

Der Core prueft unter anderem:

- sichere, begrenzte ID und begrenzten Namen;
- ausschliesslich endliche Koordinaten;
- mindestens drei unterschiedliche Polygonpunkte und eine Mindestflaeche;
- keine Selbstueberschneidung des Polygons;
- Navigationspunkt strikt innerhalb des Polygons, nicht auf dessen Kante;
- eindeutige Raum-ID und eindeutigen Raumnamen;
- passenden Kartenfingerabdruck und exakte Basisrevision.

Der Navigationspunkt ist absichtlich getrennt vom geometrischen Mittelpunkt.
Ein Mittelpunkt kann auf einem Tisch, in einer Wandnische oder in einer fuer
Amadeus zu engen Stelle liegen.

## 5. Revisions- und Schreibvertrag

Jede erfolgreiche Aenderung erhoeht `revision` genau einmal. Die App sendet
ihren zuletzt bestaetigten Stand als `base_revision`. Ist inzwischen eine
andere Aenderung gespeichert, wird der Schreibzugriff als Konflikt abgelehnt
und die App muss erst den neuen Stand anzeigen.

Jedes Kommando besitzt eine `request_id`. Innerhalb des begrenzten
Idempotenz-Caches fuehrt ein erneut zugestelltes identisches Kommando nicht zu
einer zweiten Revision. Dieselbe ID mit anderem Inhalt ist ein Fehler.

ROS-Topics:

```text
/semantic_map/command_json       std_msgs/msg/String
/semantic_map/status_json        std_msgs/msg/String, transient-local
/semantic/catalog_json           std_msgs/msg/String, transient-local
/robot_map_manager/status_json   bestehende Kartenquelle
```

Wesentliche Kommandos:

```json
{"command":"status","request_id":"ios-status-..."}
{"command":"get","request_id":"ios-get-..."}
{"command":"upsert_room","map_fingerprint":"...","base_revision":3,
 "request_id":"ios-room-...","room":{}}
{"command":"delete_room","map_fingerprint":"...","base_revision":4,
 "request_id":"ios-delete-...","room_id":"room-..."}
```

Der Status besitzt ein stabiles Top-Level und den Snapshot unter
`semantic_map`:

```json
{
  "schema_version": 1,
  "event": "status",
  "ok": true,
  "request_id": null,
  "message": "bereit",
  "semantic_map": {
    "map_ref": {},
    "revision": 5,
    "rooms": [],
    "editable": true
  }
}
```

## 6. Bedienablauf in der iOS-App

1. Die Kartenansicht empfaengt `/map`, den Kartenmanagerstatus und den
   semantischen Status ueber ihre eigene WebSocket-Verbindung.
2. Ist die Live-Karte noch nicht gespeichert, bietet die App bewusst den
   manuellen Befehl **Karte fuer Raeume speichern** an. Er publiziert genau
   einen idempotenten `save`-Befehl fuer den Namen `wohnung`.
3. Bearbeiten wird erst freigegeben, wenn Live-Karte, Kartenmanager und
   semantische `map_ref` denselben Fingerabdruck und dieselbe Geometrie melden
   und der aktuelle Kartenmanagerstatus `ok:true` ist. Ein `ok:false` sperrt
   Speichern, Overlay und Bearbeitung unmittelbar fail-closed.
4. **Raum hinzufuegen** schaltet den Canvas vom Verschieben in den
   Polygonmodus. Taps erzeugen Eckpunkte; Rueckgaengig und Abbrechen veraendern
   noch keine Serverdaten.
5. Nach mindestens drei gueltigen Punkten werden Name und Navigationspunkt
   festgelegt. Erst **Speichern** sendet `upsert_room`.
6. Die lokale Entwurfsanzeige wird erst nach bestaetigtem Serverstatus zum
   gespeicherten Raum. Bei Revisionskonflikt bleibt sie gesperrt, bis der neue
   Snapshot vorliegt.
7. Loeschen verlangt eine bestaetigte Auswahl und sendet `delete_room` mit der
   aktuellen Revision.

Die Umrechnung Bildschirm ↔ Karte beruecksichtigt Aspect-Fit, Kartenzoom,
Pan-Versatz, die vertikal gespiegelte OccupancyGrid-Darstellung, Aufloesung
sowie Translation und Yaw des Kartenursprungs. Beide Richtungen werden mit
bekannten Punkten und Roundtrips getestet.

## 7. Missions- und Sprachintegration

Der `semantic_map_manager` publiziert kompatibel:

```json
{
  "ok": true,
  "rooms": ["Wohnzimmer", "Flur"],
  "room_entities": [],
  "source": "semantic_map_manager",
  "map_fingerprint": "...",
  "revision": 5,
  "editable": true
}
```

`mission_manager` und `llm_planner` behalten ihre statischen Listen als
Fallback. Ein leerer, ungueltiger oder uebergrosser Katalog darf diese Listen
nicht leeren. Ein gueltiger Katalog ersetzt die Raumliste, nicht jedoch
Objekte und Ablageziele. Konsumenten verlangen `schema_version:1`,
`source:"semantic_map_manager"`, höchstens 256 Räume, Namen bis 80 Zeichen
und höchstens 512 KiB Katalogdaten.
Eine gültige leere Raumliste setzt die Auswahl auf den statischen Fallback
zurück; sie lässt keine zuvor gelöschten dynamischen Namen zurück.

Die bestehende reale `pick_and_place`-Mission besitzt bewusst eine getrennte,
statische Raum-Allowlist. Ein neu gezeichneter Raum kann dadurch weder diesen
Behavior-Tree noch ein neues Objekt oder Ablageziel freischalten. Die App zeigt
für `pick_and_place` genau diese separate Liste als `pick_and_place_rooms` an.

`mission_manager` nimmt einen Raumzielpunkt nur in seinen vorbereiteten Status
auf, wenn Status, Kartenfingerabdruck, Frame, Revision, Raumname und alle
Posewerte gueltig sind, `editable:true` gilt und der Status nicht älter als
sechs monotonic gemessene Sekunden ist. In diesem Branch bleibt `go_to_room`
standardmaessig simuliert und sendet kein Nav2-Ziel. Auch eingehende
Missionskommandos sind auf 64 KiB begrenzt; tief verschachteltes oder
ungültiges Unicode-JSON wird fail-closed abgelehnt.

## 8. Spaetere Freigabe einer echten Raumfahrt

Vor dem Umschalten auf eine echte Nav2-Action sind mindestens erforderlich:

1. VL53-/`collision_monitor`-Kette wieder funktionsfaehig und fail-closed;
2. gespeicherte Karte wird nach Neustart kontrolliert geladen;
3. aktuelle Lokalisierung ist bestaetigt;
4. Zielzelle ist frei, nicht unbekannt und besitzt Roboterfreiraum;
5. Nav2 kann einen Pfad zum Ziel planen;
6. Abbruch, Timeout und unerreichbares Ziel sind getestet;
7. erster Fahrtest aufgebockt beziehungsweise ohne Translation, danach langsam
   mit Not-Aus und anwesender Aufsicht.

Die App ist niemals Teil der Sicherheitskette.

## 9. Gegenstaende als naechste Ausbaustufe

Feste Orte und bewegliche Gegenstaende werden spaeter getrennt modelliert.
Ein Tisch oder eine Ladestation ist eine bestaetigte Landmarke mit eigener
Anfahrpose. Eine Tasse ist eine zeitgestempelte Beobachtung mit Confidence,
Quelle und `last_seen`; sie darf nicht dauerhaft wie ein Moebel behandelt
werden. Der Stub der aktuellen `semantic_perception` darf niemals Daten in die
reale semantische Karte persistieren.

## 10. Rueckfallweg

- `start_semantic_map_manager:=false` laesst den neuen passiven Node beim
  Bring-up aus.
- `use_dynamic_catalog:=false` aktiviert in Missions- und Sprachplaner wieder
  ausschliesslich die statischen Listen.
- Die bestehende reine Kartenanzeige bleibt erhalten; ohne passenden
  semantischen Snapshot zeigt sie keine Overlays und sendet keine Aenderung.
- Kein Rueckfallweg dieses Dokuments aktiviert oder veraendert Motoren.

## 11. Umgesetzte Softwarebausteine

Der Branch enthält die vollständige erste Stufe:

- `src/semantic_map_manager/`: ROS-Node, ROS-freier Validierungs-/Persistenz-
  Core, Launch, Konfiguration, Packaging und Regressionstests;
- `ios/Robotersteuerung/`: nativer Editor, Karten-/Semantik-Protokoll,
  Fingerprintberechnung, Konflikt-/Timeoutlogik und zustandsbehafteter Mock;
- `mission_manager`: validierter Semantikstatus-Cache und eindeutige Auflösung
  von Raum-ID beziehungsweise Raumname auf ein gebundenes Ziel;
- `llm_planner`: begrenzter dynamischer Raumkatalog mit statischem Fallback;
- `robot_bringup`: bedingter, standardmäßig aktiver Include des rein passiven
  Semantikmanagers;
- `semantic_perception`: eigener Diagnosekatalog unter
  `/semantic/perception_catalog_json`, damit es nur einen kanonischen Publisher
  für manuell bestätigte Räume gibt;
- `robot_map_manager`: idempotente Replays bauen globale Statusfelder immer aus
  dem aktuellen Zustand neu auf und können keine alte Karte reaktivieren.

Die App speichert keine fertige Raumänderung optimistisch. Ein Entwurf wird
erst nach einer passenden Antwort mit identischer `request_id`, Karte und
erhöhter Revision als gespeichert übernommen. Nach zwölf Sekunden ohne
eindeutige Antwort ist das Ergebnis **unbekannt**; es gibt keinen automatischen
Retry.

## 12. Persistenz- und Ressourcenvertrag

Revisionen werden zunächst als vollständig geschriebene und `fsync`-gesicherte
Tempdatei erzeugt und anschließend ohne Überschreiben atomar als unveränderliche
Revisionsdatei veröffentlicht. Erst danach wird `current.json` atomar ersetzt.
Ein Schreibabbruch oder ENOSPC hinterlässt daher keine sichtbare Teilrevision.
Beim Neustart kann eine vollständige verwaiste Revision kontrolliert
wiederhergestellt werden.

Standardgrenzen:

- höchstens 2.048 Revisionen pro Kartenfingerabdruck;
- höchstens 1 GiB logische Daten im gesamten Semantik-Repository;
- mindestens 512 MiB freie Dateisystemreserve nach jedem Commit;
- höchstens 4 MiB pro Dokument einschließlich Abschluss-Newline;
- höchstens 256 Räume, 64 Polygonpunkte pro Raum und 4.096 Polygonpunkte im
  gesamten Dokument. Diese kombinierte Grenze hält die Prüfung auf
  Selbstüberschneidungen auch bei maximaler Eingabe responsiv;
- Laufzeitcache standardmäßig 128 Signaturen beziehungsweise 64 KiB, ohne
  vollständige Statusantworten.

Die Grenzen führen zu einem sichtbaren Fehler und löschen keine Historie
automatisch. Echte Karten- und Raumdaten bleiben unter
`~/.local/share/amadeus/` und dürfen nicht in Git aufgenommen werden.

## 13. Verifikation und verbleibende Abnahme

Auf dem Entwicklungs-Mac bestanden am 14.08.2026:

| Bereich | Ergebnis |
|---|---:|
| `semantic_map_manager` | 51/51 |
| `mission_manager` | 38/38 |
| `llm_planner` | 15/15 |
| `robot_map_manager` | 51/51 |
| `robot_bringup`-Vertrag | 2/2 |
| rosbridge-Semantikmock | 5/5 |
| Swift-Protokoll/Geometrie/Clientpolicy | 39/39 |

Zusätzlich bestanden Python-Kompilierung, Mypy, Flake8 `F/E9`, YAML/XML,
fünf isolierte Python-Wheels und ein vollständiger unsigned iOS-Simulator-Build
für arm64/x86_64 mit Warnungen als Fehler. App und Mock starteten im
iPhone-17-Pro-Simulator; das Dashboard verband sich stabil mit dem Mock.

Auf dem realen Jetson bestanden anschließend der Colcon-Build der sechs
betroffenen Pakete und **162/162 Python-Tests**. Die signierte App lief auf dem
physischen iPhone im Roboter-WLAN. Mit der statischen `testwohnung` wurden das
bewusste Kartenspeichern, ein Raum `Test` mit vier Polygonpunkten, Revision
0→1, App- und Backend-Neustart sowie persistente Wiederherstellung geprüft.
Fahrbewegungsfreie Live-Negativtests bestätigten außerdem die Stale-Sperre nach
sechs Sekunden, Wiederfreigabe nur für dieselbe Karte, Ablehnung einer
veralteten `base_revision` und `go_to_room` ausschließlich als
`simulation_only_no_navigation`. Zu keinem Zeitpunkt existierte `/cmd_vel`.

Noch verbindlich offen:

1. visueller End-to-End-Editorlauf mit einer neu erzeugten, gespeicherten
   Wohnungskarte statt der statischen `testwohnung`;
2. echter Kartenwechsel auf einen anderen Fingerabdruck und Rückkehr;
3. erst in einem späteren Auftrag: Occupancy-/Costmap-/Erreichbarkeitsprüfung
   und kontrollierte Nav2-Integration.

Der Branch `feature/semantic-map-editor` ist veröffentlicht. Die
fahrbewegungsfreie Übernahme auf den Jetson ist abgeschlossen; eine spätere
Fahrfreigabe ist davon ausdrücklich nicht umfasst.
