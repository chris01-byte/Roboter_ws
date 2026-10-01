# explore – Frontier- und adaptive Flaechenexploration

Lässt den Roboter die Wohnung **selbstständig und zielgerichtet** erkunden –
**kein Zufallsgenerator**. Nach einem kontrollierten 360-Grad-Rundblick sucht
der Node zuerst Grenzen zwischen bekannt-freiem und unbekanntem Raum. Sind
keine sicheren Frontiers mehr vorhanden, misst er die Abdeckung aus der realen
Fahrspur und waehlt den geodaetisch am weitesten entfernten, noch nicht
abgedeckten sicheren Punkt. Ein grosser Raum erzeugt dadurch automatisch mehr
Ziele als ein kleiner.

**CPU-only, kein CUDA/LLM nötig.**

## Einordnung (Schichten-Architektur)

```
mission_manager / Behavior-Tree  --Action ExploreArea-->  explore_node
explore_node                     --Action navigate_to_pose-->  Nav2
Reaktive Sicherheit (collision_monitor, VL53) bleibt autonom aktiv.
```

## Schnittstellen

| Rolle | Name | Typ |
|---|---|---|
| Action-Server | `/explore_area` | `robot_interfaces/ExploreArea` |
| Action-Client | `navigate_to_pose` | `nav2_msgs/NavigateToPose` |
| Subscribe | `<map_topic>` (`/map`) | `nav_msgs/OccupancyGrid` |
| TF | `<global_frame>` → `<robot_base_frame>` | Roboterpose |
| Publish (optional) | `<marker_topic>` (`/explore/frontiers`) | `visualization_msgs/MarkerArray` |
| Publish | `/explore/status_json` | `std_msgs/String`, 1-Hz-Heartbeat |

## Start

```bash
ros2 launch explore explore.launch.py
```

Voraussetzung: SLAM publiziert eine Karte auf `map_topic` **und** Nav2 läuft
(Action `navigate_to_pose`).

## Schnelltest ohne Behavior-Tree

```bash
ros2 action send_goal /explore_area robot_interfaces/action/ExploreArea \
  "{timeout_s: 0.0, min_frontier_size_m: 0.0, return_to_start: false}"
```

## Parameter

Alle Werte in [config/explore_params.yaml](config/explore_params.yaml)
(mit Parameter-Index im Kopf). Wichtige Stellhebel:

- `min_frontier_size_m` – kleinste beachtete Frontier (Rauschfilter)
- `potential_scale` / `gain_scale` – Kosten/Nutzen-Gewichtung (nah vs. groß)
- `goal_timeout_s` – max. Fahrzeit pro Frontier
- `blacklist_radius_m` – sperrt gescheiterte Ziele (Selbstbefreiung)
- `frontier_revisit_radius_m` – sperrt erfolgreich bediente Frontier-Umfelder
- `max_frontier_goals` – harte Obergrenze gegen Zielwiederholungen
- `coverage_target_ratio` – erforderlicher Anteil der sicher befahrbaren Flaeche
- `coverage_visit_radius_m` – Korridor um die gemessene Fahrspur
- `coverage_clearance_m` – Kartenabstand der Abdeckungsziele
- `coverage_max_goals` – harte Grenze der dritten Phase
- `return_to_start` – nach Fertigstellung zur Startpose zurück

## Abnahmestand und Grenzen

Der komplette Ablauf ist auf dem echten Roboter gefahren. Der beaufsichtigte
Akku-Lauf vom 17.08.2026 beendete Rundblick, adaptive Frontier-/Abdeckungswahl
und Mission nach 732 s mit 88,30 % Abdeckung, fuenf verschiedenen
Frontier-Zielen und `map_ready_to_save=true`. Beide VL53 und der
Kollisionsmonitor waren aktiv; danach standen Odometrie und Basis bei null.
Der Standardwert 85 % bezieht sich auf den erodierten, zusammenhaengenden
Freiraum innerhalb von 0,65 m zur Fahrspur und ersetzt keine visuelle
Kartenpruefung. Gedrehte Karten-Origin wird beruecksichtigt.

## Explizite metrische Strategie (MASTERPLAN v1.2)

**Startpräzisierung 01.10.2026:** `metric_start_strategy` ist beim Start
unveränderlich, Default und metrisches Profil wählen `adaptive`.
`initial_scan_enabled` stellt den Rundblick bereit; seine unbenutzte 360°-Fläche
ist keine Voraussetzung einer anderen ersten Bewegung. Die Auswahl prüft
Startkontur, Beobachtungsnutzen und tatsächliche Bewegungsgeometrie: zulässiger
nützlicher voller Scan, sonst autonomes Frontier-/Beobachtungsziel, sonst
konkreter Warte-/Teilstand. `configured_scan` erhält den bisherigen Scanablauf.
`existing` und dessen Defaultauswahl bleiben erhalten. Anfangs bestätigter
Encoderstillstand, aktuelle Quellen und Scope gelten für beide Bewegungsarten.

Der vorhandene Explorer liest vor Bewegung den tatsächlichen Nav2-Pfad über
`ComputePathToPose`; `NavigateToPose` bleibt alleiniger Fahrbesitzer. Aktuelle
`/plan`-Änderungen, Vorausrichtung, RPP-Headingkorrekturen/Lookahead und
Zielorientierung werden auf beiden Rastern geprüft. Die live abgefragten Controller-/Goalcheckerparameter sowie Geometrie-/Körperbelegdetails stehen im
[Kartierungs-README](../../tools/kartierung/README.md#adaptiver-metrischer-start-und-timing-hold-01102026).
Ein abgebrochener optionaler Scan ist ein begrenzter fehlgeschlagener Versuch,
kein erfüllter Vollrundblick; erst bestätigter Stillstand und gültige Quellen
erlauben eine andere geprüfte Beobachtungsposition. Gesamt-/Aufgabenfristen
werden dabei nicht neu gestartet.

`exploration_strategy` hat den unveränderten Default `existing`. Für das neue
Backend nach dem Basisprofil ein bewusst ausgewähltes, lokal vervollständigtes
`config/metric_frontier_params.yaml` über `explore_params_overlay` laden. Das
Beispiel ist absichtlich **nicht fahrfertig**: `metric_session_id`,
`metric_scope_map_fingerprint`, `wohnungserkundung_scope_id`, Polygon und
`wohnungserkundung_accessible_scope_verified` müssen zum beobachteten
Startkartenstand gehören. Die gemeinsamen Scope-Parameter sind metrisch;
keine Region oder Portal-ID wird daraus erzeugt. Moduswechsel erfordern einen
geordneten Neustart ohne aktive Mission; der Strategieparameter ist read-only.
Der bestehende Mission-Manager → BT → ExploreArea → Nav2-Ausführungspfad bleibt.

`metric_frontier.py` enthält räumliche Versuchshistorie, bekannte freie
Routen und Fahrzeugkonturprüfung. `metric_frontier_runtime.py` bindet diese
Strategie an denselben Explorer/Action-Server und Nav2-Client. Wiederverwendet
werden `_detect_frontiers`, `_frontier_approach_goal`, `grid_line_is_clear`, die
bestehenden Kosten-/Headinggewichte und die geodätische Distanzberechnung.
Sicherheitsprüfung geht der Rangfolge voraus. Reicht am historischen
Annäherungspunkt die kreisförmige Mittelpunktprüfung, aber nicht die gedrehte
Frontkontur, werden zurückliegende Punkte innerhalb des vorhandenen
`goal_search_radius_m` gesucht und jeweils mitsamt vollständiger Route geprüft. Das Rasterstufenprofil wird zu
freien geraden Segmenten vereinfacht und anschließend mit dem vollständigen
Footprint einschließlich Drehungen geprüft; es fordert keine Drehung an jeder
Rasterzelle. Unbekannt, außerhalb des Scopes oder unerreichbar bleibt gesperrt.

Erforderlich sind Rohkarte **und** deren exakte Kartenmanager-Korrelation,
aktueller Kartenframe/Pose, globale Costmap, tatsächlicher gepaddeter Footprint,
Not-Aus, LiDAR, beide VL53 samt passenden Qualitäts-/Cloudstempeln und
Encoder-/Aktuatorzustand. Wenn HWT-Fusion ausgewählt ist, bleiben deren
bestehende Quellen-/HOLD-/ACK-Verträge aktiv. `PortalMapContext` wird nur als
bestehender Sitzung/Karte/Frame-Datentyp wiederverwendet. Es gibt weder
Dummy-Portale noch Raum-IDs. Optionale Shadowfeeds dürfen passiv laufen;
`wohnungserkundung_policy_enabled` und `wohnungserkundung_navigation_enabled`
müssen für diesen Modus beide false sein. Direkte Portalbrücken, Coverage und
Rückkehr sind in diesem ersten Backend ausgeschlossen.

Ein gültiges Kind bleibt bei Karten- oder Rangfolgeänderungen erhalten. Seine
Route wird unabhängig von optionaler Semantik auf den **aktuellsten Rastern**
revalidiert; auch die ursprünglich an Nav2 übergebene Zielorientierung wird
bei verändertem Anfahrweg auf den aktuellen Rastern geprüft. Die vorhandene 1,25-s-Grenze für eine ausstehende Kartenübergabe
wird nicht durch weitere Updates verlängert; neue Kinder brauchen eine exakte
Korrelation. Verspätete ältere Rohkarten/Costmaps dürfen neuere Ablehnungen
nicht überschreiben. Ein Frame-/Epochenfehler bleibt gelatcht.

Nach terminalem Kind und mindestens 0,5 s frischem Encoderstillstand bewertet
die Strategie einen aktuellen Betriebssnapshot. Gesunder Zustand erlaubt
begrenzte Rückstellung eines unerreichten Ziels, ohne dessen unbekannte Ursache
als Hardwarefehler oder bewiesenes Hindernis auszugeben. `route_invalidated` wird
nur bei tatsächlich ungültiger Route verwendet; sonst
`task_unreached_cause_unproven`. Das nächste Ziel entsteht erneut aus den
Rastern. Wiederholung benötigt Ablauf von `metric_retry_cooldown_s` (30 s),
geänderte Kartenevidenz und verbleibende Versuche
(`metric_task_retry_limit`: 2); räumliche Zuordnung verhindert neue IDs als
Retry-Umgehung. Erfolgreich bediente Umfelder bleiben für dieselbe Mission
gesperrt. Die Historie ist auf 512 Aufgaben begrenzt.

`goal_timeout_s` ist das absolute Aufgabenbudget einschließlich Vorausrichtung,
Kindwechsel und HOLD. Kleine Drehungen oder Odometriesummen setzen es nicht
zurück. `overall_timeout_s`, `max_frontier_goals` und `max_failed_goals` bleiben
Gesamtgrenzen. Der ausgewählte HWT-Vertrag prüft kurze Störungen unabhängig
von Routenarbeit alle 50 ms und verwendet weiterhin Stillstand, aktuellen Weg
und Gate-ACK zur Fortsetzung. Ein nicht nachgewiesen terminales Nav2-Kind
verhindert neue Elternaufträge; spät angenommene alte Goals werden storniert.

Der unveränderte Schema-1-Status ergänzt `strategy: metric_frontier` und
`metric_exploration` mit aktivem Ziel, Kosten/Route, Versuch, Filtergründen,
Entscheidungssnapshot und begrenzter Ziel-Ergebnis-Folgezielkette. Feedback zeigt
das aktive Ziel. Drei bestätigte leere Beobachtungen **ohne** unbekannte
Scopezellen oder unerledigte Fehlversuche ergeben höchstens
`metric_completion_candidate`, Zustand `partial`. Filter, Blockaden und
fehlende Daten ergeben keinen Abschluss; Budgetende bleibt `partial`, harte
Fehler `failed`, Nutzerabbruch `canceled`. ExploreArea meldet keinen
Gesamterfolg; der bisherige boolesche Actionvertrag führt einen metrischen
Teilstand im Mission Manager/BT daher als fehlgeschlagen, während der neue
Explorerstatus ausdrücklich `partial` meldet. `map_ready_to_save` bleibt false,
Semantik- und Bodenabdeckung
bleiben ausdrücklich ungeprüft. Bestehende App-/Speicherkonsumenten erhalten
somit keine unberechtigte Speicherfreigabe. Manuelles Speichern einer geprüften
Teilkarte über den bestehenden Kartenmanager bleibt eine eigene Handlung.

Gerätefreier verbundener Nachweis:
`tools/sensorfusion/metric_frontier_product_graph.py` nach Sourcen des
isolierten Builds ausführen; das Skript erzwingt localhost und Domain 200–230.
Synthetische Quellen/Nav2 ersetzen ausschließlich Sensoren und Gegenstelle,
keine Karten-/Task-/Policylogik. Fallauswahl über `METRIC_GRAPH_CASE`; Ergebnisse
bleiben unter `HWT_GRAPH_LOGDIR` lokal. Die Softwarebelege sind keine reale
Durchfahrt oder Stufe-3-Gesamtabnahme. Rückfall: Overlay nicht wählen,
`exploration_strategy: existing` beim nächsten geordneten Start; sicherster
Betriebsrückfall bleibt `enable_auto_explore:=false`, `active_drive:=false`.
