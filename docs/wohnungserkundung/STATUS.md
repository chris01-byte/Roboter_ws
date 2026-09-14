# Wohnungserkundung – laufender Status und Entscheidungen

**Vorhaben WE-1 · Aktualisiert: 2026-09-14 (WE-M2/B)**

Dies ist der einzige laufende Fortschrittsstand des Vorhabens. Die
[Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) beschreibt das Soll,
die [Roadmap](MEILENSTEINE.md) die Abnahmen und der
[Agentenauftrag](AGENTENAUFTRAG.md) den Arbeitsablauf. Historische Logs bleiben
Quellen, aber ersetzen diesen statusbezogenen Einstieg nicht.

## 1. Aktueller nächster Schritt

**WE-M2/B – kontrollierte Regionsvereinigung als reine Logik softwaregeprüft,
zur Review.** Explizite revisionsgebundene Merge-Aufträge vereinigen vorläufige
Regionen deterministisch. Historische IDs bleiben als Alias auflösbar;
Verbindungen, aktueller Ort, gesehen/betreten und Eintrittszähler werden ohne
Verlust umgeschrieben. Dies ist weiterhin nicht der gesamte WE-M2-Umfang und
keine Zielsystem- oder Hardwareabnahme.

**Nächster vorgeschlagener Umsetzungsschritt nach Review: WE-M2/C.** Im reinen
Graphmodul nur einen begrenzten Bestand stabiler, opaker Aufgabenreferenzen
(`frontier`, `portal`, `observation`) mit Regionsbezug und Revisionskontext führen
und bei Regionsvereinigung aliasfest erhalten. Keine Bewertung, Zielauswahl,
Retries, automatische Teilung, ROS-Ausgabe, Navigation oder Fahrwirkung.

WE-M0/A gibt weiterhin weder den HWT-Zweig noch den lokal veränderten
Jetson-Arbeitsbaum als Entwicklungsbasis frei. Deren funktionale Integration und
der Zielsystem-Nachtest bleiben eigene, später ausdrücklich abzugrenzende Schritte.

Eine Wiederholung des Arbeitszimmer-Flur-Laufs gehört zu WE-M0/B und benötigt
zusätzlich Zielsystemprüfung, sicheren Aufbau und eine neue ausdrückliche
Freigabe. Das Schreiben oder Veröffentlichen dieses Plans erteilt diese nicht.

## 2. Git- und Evidenzbasis

| Referenz am 14.09.2026 | Nachgewiesener Umfang |
|---|---|
| Dokumentation `96cebee986e55cde2d10da0f86e65294e6004a82` | Nach `git fetch origin` über `origin/docs/wohnungserkundung-agentenplan` gelesen. Nicht in `origin/main` enthalten; PR #20 ist offen und laut GitHub `MERGEABLE/CLEAN`. |
| Main `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1` | Aktueller Remote-Stand. Mit HWT ab gemeinsamem Vorfahren `9822962` divergent: 16 nur auf Main, 46 nur auf HWT. |
| HWT `1d91229dc10ff4bb791938d49aae8e9808a5dfff` auf `codex/hwt601-encoder-shadow` | Remote-Referenz sowie sauberer separater Worktree unter `/home/p/roboter_worktrees/hwt601-usb-commissioning` nachgewiesen; nicht pauschal nach Main übernommen. |
| Maßgebliche Arbeitskopie `/home/p/roboter_ws` | Branch `feature/modulare-sensorfusion`, HEAD `00f6e521085b6cb0e38a62a029638d28195a544c`, mit bestehenden lokalen Änderungen unter anderem in Explorer, LiDAR, Navigation und Dokumentation. Kein Branchwechsel und keine Änderung dieses Bestands. |
| Lokale Installationen | Primärinstallation und separates HWT-Overlay dateibasiert geprüft; Details unten. Keine Geräte, ROS-Nodes, Karten oder Bags geöffnet. |
| WE-M0/A-Fortschreibung `cf3a40bfe004a174eccae18b22cb3a17126bed3e` auf `docs/we-m0a-bestandspruefung` | Dokumentationsbasis von WE-M1/A; vereinigt die belegten lokalen und isolierten Gegenprüfungen, funktionaler Code darunter weiterhin Main `05439c7`. |
| WE-M1/A `feature/we-m1a-portal-memory` | Zwei neue, nicht eingebundene Python-Dateien plus dieser Statusnachtrag; Reviewstand, kein Deployment. |
| WE-M1/B `feature/we-m1b-portal-state` | Gestapelter reiner Logikschritt auf WE-M1/A; nur Portalmodul, dessen Tests und Status, kein Deployment. |
| WE-M1/C `feature/we-m1c-portal-evidence` | Gestapelter Abschluss der reinen WE-M1-Logik; qualifizierte Bestätigungsevidenz und verbleibende synthetische Negativfälle, kein Deployment. |
| WE-M2/A `feature/we-m2a-region-graph` | Gestapelter, nicht eingebundener Regions-/Verbindungskern auf WE-M1/C; zwei neue Python-Dateien und Status, kein Deployment. |
| WE-M2/B `feature/we-m2b-region-merge` | Gestapelte, explizit ausgelöste Regionsvereinigung mit Aliasauflösung; nur Graphmodul, Tests und Status, kein Deployment. |

Der [Bericht vom 11.09.2026](https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/docs/PROJECT_MEMORY.md)
dokumentiert den physischen Übergang vom Arbeitszimmer in den Flur mit
Nutzerbestätigung und anschließendem weiteren Umsehen. Er dokumentiert auch die
erneute Erkennung desselben Portals nach Geometrieänderung. Die abschließende
Softwarekorrektur ist dort mit 80 Explorer-Tests und Build-Erfolg angegeben,
aber ausdrücklich noch nicht erneut real gefahren.

Dies sind historische, im Repository berichtete Nachweise. Der neue Plan
setzt weder diese Tests noch den gesamten Wohnungslauf eigenständig auf bestanden.

## 3. Ergebnis WE-M0/A – Bestand und Integrationsentscheidung

### 3.1 Main, HWT und lokal verfügbarer Stand

**Main:** `origin/main` enthält den bisherigen Explorer mit Rundblick,
Frontier-Auswahl, Koordinaten-/Radius-Blacklist, getrennten Costmap-Portalen,
LiDAR-Korridorprüfung, Nav2-Auslaufprüfung, Fahrspurabdeckung und 1-Hz-Status.
`robot_state_estimation` und die HWT601-Profile sind dort nicht enthalten.
Die 16 nur auf Main vorhandenen Commits betreffen spätere OAK-/Offboard- und
Semantikarbeit. Ein Gesamtmerge des HWT-Zweigs wäre deshalb weder eine kleine
Portalübernahme noch eine zulässige Integrationsbasis.

**HWT:** `1d91229` ergänzt gegenüber der gemeinsamen Basis insbesondere die
modulare Sensorfusion/HWT601-Kette, begrenzte HWT-Startprofile, eine opt-in
Engstellenerkennung in bereits verbundenem Freiraum, Portalpriorität,
`required_portal_crossings`, begrenztes Nachrücken und genau einen zusätzlichen
Nav2-Auslaufversuch nach vorzeitigem Erfolg. Die Abschlusskorrektur ignoriert
weitere Portalangebote, wenn ein expliziter Ein-Übergang-Vertrag bereits 1/1
erfüllt ist. Diese Korrektur ist laut HWT-Protokoll softwaregeprüft, aber nach
dem realen Befund nicht erneut physisch gefahren.

**Primärinstallation:** `install/explore` ist eine Symlink-Installation auf den
lokal veränderten Quellbaum. Dessen `explore_node.py` und Parameter entsprechen
weder Main noch HWT; zusätzlich liegt die nicht eingecheckte
`structured_exploration.py` vor. `portal_planning.py` entspricht dagegen Main
und besitzt die HWT-Engstellenerkennung nicht. Dieser Mischstand ist keine
reproduzierbare Integrationsbasis. `robot_map_manager` ist installiert und sein
Core entspricht dem aktuellen Main-Quellstand. Die installierten Kopien von
`semantic_map_manager` sind dagegen älter als der Quellstand: `semantic_core.py`
entspricht dem Stand vor optionalen Räumen ohne Navigationsziel, der Node dem
Stand vor dem Ausschluss solcher reinen Raumgrenzen aus dem Zielkatalog.

**HWT-Overlay:** Der saubere HWT-Worktree besitzt gebaute Präfixe für sechs
Pakete einschließlich `explore`, `robot_state_estimation`, Navigation und
Bring-up. Er verwendet `robot_map_manager`, `semantic_map_manager`, Mission und
weitere Pakete aus `/home/p/roboter_ws/install` als Underlay. Mehrere HWT-Wrapper
erwarten ihre Explorerprofile außerdem hart unter
`/home/p/roboter_ws/install/explore`; dort fehlen die HWT-Profile im aktuellen
lokalen Zustand. Das vorhandene Overlay ist daher heute nicht als
selbstständiger, sauber reproduzierbarer Gesamtinstallationsstand belegt.

Zum Zeitpunkt der Prozessprüfung wurden keine laufenden Amadeus-/ROS-Prozesse
mit den geprüften Namen gefunden. Daraus folgt keine Aussage zu Versorgung,
Not-Aus, seriellen Geräten oder physischer Fahrbereitschaft; diese wurden
absichtlich nicht abgefragt oder aktiviert.

### 3.2 Vorhandene Explorer- und Portalfunktionen

- `ExploreArea` bleibt die einzige Explorer-Action. Ihr Resultat unterscheidet
  nur `success`, Klartext, Frontierzahl und Fläche. Der BT-Verbraucher reduziert
  dies auf Erfolg/Fehler. `complete_accessible`, `partial`, `aborted`,
  `canceled`, Speichern und Rückkehr sind noch kein expliziter Ergebnisvertrag.
- `/explore/status_json` enthält auf Main unter anderem Phase, Coverage,
  Frontier-/Portalzähler und `map_ready_to_save`. HWT ergänzt Pflichtübergänge
  und `room_transition_confirmed`. iOS und Web konsumieren den bestehenden
  Kernstatus, aber keine stabile Portal-/Regionsidentität oder vollständige
  Aufgabenliste.
- Main erkennt getrennte befahrbare Costmap-Komponenten und prüft eine
  Sonderbrücke mit frischem LiDAR. HWT kann zusätzlich eine Türengstelle in
  bereits verbundenem gemessenem Freiraum finden; die echte Costmap und der
  reale Footprint bleiben dabei unverändert.
- HWT gleicht einen während einer Etappe veränderten Portalplan anhand von Nah-,
  Fern- und Mittelpunkt sowie gleicher Richtung ab. Dauerhaft besucht bleibt
  ein Portal jedoch nur als Kartenkoordinate in `_visited_portals` mit
  Radiusvergleich. Es gibt weder Portal-ID noch kanonische Seiten, getrennte
  Beobachtungs-/Erreichbarkeitszustände, Evidenzrevision oder idempotentes
  Durchfahrtsereignis.
- Weder Main noch HWT enthalten `portal_memory.py`, `region_graph.py` oder
  `exploration_policy.py`. Der lokal vorhandene `room_index` der strukturierten
  Konturstrategie ist nur ein Laufzeitzähler und kein stabiler Regionsgraph.

### 3.3 Kartenmanager, Semantik und Integrationsgrenzen

- `robot_map_manager` liefert validierte Live-Snapshots, inhaltsbasierte
  SHA-256-Fingerprints, unveränderliche atomare Kartenversionen, Status/Listen
  und idempotente Speicherkommandos. Er lädt oder löscht absichtlich keine
  Karten und besitzt kein Schema für Erkundungssitzungen, Portal- oder
  Regionsdaten.
- `semantic_map_manager` bindet manuelle Raum-IDs, Polygone, optionale
  Navigationsziele und Revisionen fail-closed an eine gespeicherte
  Kartenidentität. `/semantic/catalog_json` ist bereits gemeinsamer Verbraucher
  für Mission und LLM-Planer. Automatische Regionen dürfen diese Raum-IDs nicht
  ersetzen; eine explizite Zuordnungsschnittstelle existiert noch nicht.
- Karten- und Semantikquellen sind zwischen aktuellem Main und HWT bytegleich.
  Für WE-M1 ist deshalb kein zweiter Speicher und keine Änderung dieser Pakete
  erforderlich. Der Bezug einer laufenden Portalbeobachtung auf Kartenrevision,
  Ursprung und spätere gespeicherte Identität bleibt bis WE-M2/WE-M5 offen.
- Der bestehende Semantik-Core erlaubt seit Main Räume ohne Navigationsziel;
  der Katalog filtert sie. Dafür existiert ein iOS-Serialisierungstest, aber
  kein gezielter Python-Backendtest. Vor einer späteren automatischen
  Regionszuordnung ist dieser Negativvertrag nachzutesten und die lokale
  Installation frisch aufzubauen.

### 3.4 Ausgeführte Prüfungen

Alle folgenden Läufe waren reine Python-/Quelltests ohne ROS-Launch oder
Gerätezugriff:

- exakter Main-/Dokumentationsbasisstand: 160 Tests bestanden
  (`explore` 58, `robot_map_manager` 51, `semantic_map_manager` 51);
- exakter HWT-Explorerstand `1d91229`: 80 Tests bestanden;
- lokal veränderter Primär-Explorerstand: 67 Tests bestanden.

Die bestehenden HWT-Tests decken unter anderem verbundene Engstellen,
Richtungsumkehr beim lokalen Portalabgleich, begrenztes Nachrücken, frühen
Nav2-Erfolg und den Ein-Übergang-Abschluss ab. Nicht abgedeckt sind die für
WE-M1 geforderten stabilen Identitäten über beide Portalansichten,
Ursprungs-/Rasteränderungen, zwei benachbarte ähnliche Türen, unabhängige
Beobachtungsevidenz, Ambiguität, blockiert → offen und idempotente
Durchfahrtsereignisse.

Nicht ausgeführt wurden Colcon-Neubuild, ROS-Smoke-/Zielsystemstart,
TF-/Controllerlastmessung, Geräte-/Portprüfung, Karten-/Bag-Auswertung und jede
Bewegung. Vorhandene Buildartefakte und historische Fahrberichte sind keine
heutige Zielsystem- oder Hardwareabnahme.

### 3.5 Integrationsbasis und kleinster nächster PR

**Integrationsbasis:** neuer Themenbranch vom dann aktuellen `main`, nachdem
PR #20 aufgenommen oder die vier Planunterlagen anderweitig eindeutig verfügbar
sind. Weder der lokale Mischstand noch der HWT-Gesamtzweig wird als Basis
verwendet. Das reine Identitätsmodul akzeptiert eine kleine normalisierte
Portalbeobachtung und bleibt dadurch von Main-/HWT-Detektordetails getrennt.

**WE-M1/A – betroffene Dateien:** neu
`src/explore/explore/portal_memory.py`, neu
`src/explore/test/test_portal_memory.py` und dieser Status. Keine Änderung an
`explore_node.py`, Launches, Parametern, Action/Status, Navigation,
Sensorfusion, Kartenmanagern oder Semantik.

**Prüfplan:** deterministische Unit-Tests für gleiche Tür von beiden Seiten,
kleines Kartenwachstum, verschobenen Ursprung/Rasterbezug, zwei nahe Türen,
identische wiederholte Kartenrevision und mehrdeutige Zuordnung. Ambiguität
darf keine ID verschmelzen oder Evidenz erhöhen. Danach bestehende
Explorer-Suite und `colcon build/test --packages-select explore`; keine Nodes
starten. Passageereignisse, ROS-Schattenintegration und Persistenz bleiben
bewusst Folgeschritte.

**Rückfallweg:** Das neue Modul wird in WE-M1/A nirgends importiert oder
gestartet. Rückfall besteht ausschließlich aus Entfernen der beiden neuen
Dateien beziehungsweise Revert des kleinen PR; bestehender Explorer und jede
Runtime bleiben unverändert.

### 3.6 Ergänzende Gegenprüfung aus isolierter Audit-Umgebung

**Fortgeschriebene Basis:** Während der Veröffentlichung einer separaten
Gegenprüfung wurde dieser Status mit Commit
`630c38cd3e563b564b4a0dd6bf35b128f80bd3cc` weitergeführt. Dessen Bestandsbericht,
Installationsbefunde, Tests und WE-M1/A-Abgrenzung bleiben vollständig erhalten.
Der vorher parallel entstandene Auditstand `c8d97cb88863513187dbea3dc74df48c084a1a5d`
ist damit nicht mehr der aktuelle Status. Dieser Zusatz setzt WE-M0/A nicht
zurück und beginnt keine Implementierung von WE-M1/A.

**Getrennte Nachweise:** Die Jetson-Dateiinventur und die in Abschnitt 3.4
berichteten 160/80/67 Testläufe stammen aus dem dortigen Prüfauftrag. Sie wurden
in der folgenden separaten Chat-Audit-Umgebung nicht selbst wiederholt.
Hier war kein Jetson-Installationsbaum verfügbar. `git fetch origin` wurde in
einem neu angelegten isolierten Audit-Repository versucht und scheiterte mit
Exit 128 (`Could not resolve host: github.com`). Referenzen und Quelldateien
wurden ersatzweise über den GitHub-Connector gelesen. Diese Einschränkung betrifft
nur die Gegenprüfung und widerruft nicht die oben dokumentierte Dateiinventur.
Keine laufende Roboter-Arbeitskopie wurde gewechselt oder verändert.

**Eigene ausgeführte Tests:** Linux x86_64, Python 3.13.5, NumPy 2.3.5,
SciPy 1.17.0 und pytest 9.0.2; ohne ROS oder Gerätezugriff. Je Referenz wurden
nur `portal_planning.py` und `test_portal_planning.py` isoliert bereitgestellt.
Vor Ausführung stimmten die vollständigen Git-Blob-Hashes mit den gepinnten
Repository-Dateien überein. Keine veränderten Tests, kein vollständiger Clone
und kein Installations- oder Hardwaretest.

| Referenz | Eigenes Ergebnis für `test_portal_planning.py` | Exit |
|---|---|---|
| Main `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1` | 8 bestanden; keine Fehler, Fehlschläge oder Skips. | 0 |
| HWT `1d91229dc10ff4bb791938d49aae8e9808a5dfff` | 12 bestanden; keine Fehler, Fehlschläge oder Skips. | 0 |

Die Suiten überlappen: nicht 20 unterschiedliche Testfälle und nicht zusätzlich
zu den anderen Läufen als neue Funktionsabdeckung zählen. Die Gegenprüfung betrifft
Portalgeometrie, Endpunktkosten, Größenlimits und LiDAR-Korridore, nicht stabile
Portalidentität, Durchfahrtsereignisse oder einen Wohnungsabschluss.

| Datei unter `src/explore/` | Main-Git-Blob | HWT-Git-Blob |
|---|---|---|
| `explore/portal_planning.py` | `f66717088d0fb552f0d63b5f586ecf78ef89b376` | `7cd85d19e433de708c27d98e0574a7b3449bf807` |
| `test/test_portal_planning.py` | `a30c03ce747558bb3838aa0ee3628f6b7bff560b` | `a8ee5de695aeb947db1a68f007febecfaf1ce77c` |

Reproduktion jeweils aus dem passenden isolierten Paketverzeichnis:

```bash
report_dir="$(mktemp -d /tmp/we-m0a-portal.XXXXXX)"
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -m pytest -q -p no:cacheprovider test/test_portal_planning.py \
  --junitxml="$report_dir/portal.xml"
```

Konsolenlogs, JUnit-Berichte, Exit-Codes und SHA-256-Werte sind im separaten
Audit-Prüfsatz enthalten. Die übrigen Explorer-/Manager-Verträge wurden hier
statisch anhand relevanter Quellen und ausgewählter Tests gelesen, nicht als
vollständige ROS-/Colcon-/Manager-Testläufe wiederholt.

**Zusätzlicher offener Vertragsbefund:** Die
[Kartenmanager-README auf Main](https://github.com/chris01-byte/Roboter_ws/blob/05439c7a13d7a92e69b9eb4663e3a2a1b44626a1/src/robot_map_manager/README.md)
verlangt bytegleiche wiederholte Antworten. Der
[zugehörige Node](https://github.com/chris01-byte/Roboter_ws/blob/05439c7a13d7a92e69b9eb4663e3a2a1b44626a1/src/robot_map_manager/robot_map_manager/robot_map_manager_node.py)
erzeugt beim Cache-Replay über `CachedCommandResponse.publish_kwargs` und
`_publish_status` jedoch den globalen Map-/Storage-/Pose-/Zeit-/Zählerstatus
frisch. Idempotentes Kommandoergebnis und bytegleicher gesamter Statusumschlag
sind daher getrennte Verträge. Vor einer späteren Adapterintegration mit einem
fokussierten Test und Dokumentationsabgleich klären; hier keine Funktionsänderung.
Eine frische Statuswiederholung ist zudem kein Beleg einer neuen unabhängigen
Portalbeobachtung. Der isolierte WE-M1/A-Schritt aus Abschnitt 3.5 benötigt diesen
Adapter noch nicht und bleibt unverändert.

**Änderungsumfang / Rückfall:** Nur diese Ergänzung in der fachlichen STATUS.md;
keine andere Repository-Datei, kein funktionaler Branchmerge und kein Deployment.
Den fortgeschriebenen Status aus `630c38c` bei der Dokumentationszusammenführung
erhalten. Rückfall dieser Gegenprüfung: ausschließlich Abschnitt 3.6 entfernen
oder den Ergänzungs-PR schließen, nicht den neueren Bestandsbericht zurücksetzen.

## 4. Meilensteinstand

| Stufe | Stand | Fehlender Nachweis / nächste Abgrenzung |
|---|---|---|
| WE-D0 | Dokumentiert; zur Review | Dokumentationszweig/PR ist nicht automatisch Main oder Jetson-Deployment. |
| WE-M0/A | Dokumentiert; Leseanalyse abgeschlossen | Keine Runtime-/Zielsystem-/Hardwareabnahme. Lokaler Mischstand und HWT-Gesamtmerge ausdrücklich nicht freigegeben. |
| WE-M0/B | Offen | Neue Baseline-/Lastprüfung und reale Wiederholung der Abschlusskorrektur. |
| WE-M1 | Softwaregeprüft; zur Review | WE-M1/A bis C decken den reinen In-Memory-Vertrag ab. Detektoradapter, ROS-/Zielsystemintegration und Hardwareabnahme sind ausdrücklich nicht enthalten. |
| WE-M2 | In Arbeit | WE-M2/A und B als reine Topologie samt Vereinigung softwaregeprüft; Aufgabenbezug, kontrollierte Teilung und passive Integration offen. |
| WE-M3 | Geplant | Hierarchische Policy, Abschlussvertrag und motorlose Abnahme. |
| WE-M4 | Geplant | Arbeitszimmer → Flur → weiteres Zimmer → derselbe Flur. |
| WE-M5 | Geplant | Versionsgebundene Persistenz und sichere Wiederaufnahme. |
| WE-M6 | Geplant | Wiederholbarer Abschluss des zugänglichen Wohnungsumfangs. |
| WE-M7 | Geplant, ergänzend | App-Transparenz und manuelle Benennung. |

## 5. Bekannte offene Punkte

**Codebasis:** Main und HWT-Erprobungszweig bleiben divergent. WE-M1/A benötigt
keine funktionale HWT-Übernahme. Vor einer späteren Explorer-Einbindung sind
Engstellendetektor, Auslaufkorrektur, strukturierte lokale Konturstrategie und
Sensorfusionsprofil gezielt gegeneinander zu integrieren; ein
Dokumentationsmerge nimmt diese Funktionen nicht mit.

**Installation:** Primärinstallation folgt teils einem lokal veränderten
Symlink-Quellbaum, teils älteren kopierten Semantikartefakten. Das HWT-Overlay
ist auf dieses Underlay angewiesen. Vor WE-M0/B oder jeder Zielsystembehauptung
ist ein isolierter, commitgebundener Neuaufbau mit nachgewiesener Overlay-
Reihenfolge erforderlich.

**Baseline:** Die nach dem letzten Realtest geänderte Abschlusslogik ist laut
Referenz noch nicht erneut physisch abgenommen.

**Ressourcen:** Der letzte Bericht nennt TF-Zukunftsextrapolationen und verpasste
Controllerzyklen unter SLAM-Last. Aktuellen Zustand messen, nicht aus alten Werten
als erledigt betrachten.

**Identität und Abschluss:** WE-M1/A bis C stellt Identität, qualifizierte
Bestätigung, Ereignishistorie und aktuelle Erreichbarkeit nur innerhalb eines
expliziten Sitzungs-/Karten-/Frame-Kontexts bereit. Struktur- und Bewegungsbelege
werden nicht selbst erzeugt oder physisch validiert. Dauerhafte Kartenbindung,
vollständiger Regionsgraph und Abschluss fehlen.

**Regionsgraph:** WE-M2/A kann einen Start–Flur–Raum-Pfad und die Rückkehr in
dieselbe Flur-ID führen. WE-M2/B schließt Schleifen durch explizite
Regionsvereinigung und erhält alte IDs als Alias. Eine neue bestätigte Portal-ID
erzeugt weiterhin zunächst eine vorläufige Gegenregion. Automatische
Mergeentscheidung, Teilung, Geometriekorrekturen, Aufgabenreferenzen und passive
Runtime-Ausgabe fehlen noch.

**Kartenintegration:** Manuelle Raum-Overlays, Fingerprints und Speicherverträge
existieren. Die Zuordnung automatischer Erkundungsregionen und laufender Karten-
revisionen muss diese erhalten; konkrete Schema-/API-Erweiterungen sind noch offen.

**Abnahmegrenzen:** Grenzwerte für Identitätszuordnung, Beobachtungsfenster,
Ressourcenbudgets und Wohnungsumfang müssen vor den jeweiligen Tests begründet
festgelegt werden. Die Dokumentation ist kein Ersatz für diese Messungen.

## 6. Entscheidungslog

### 2026-09-14 – WE-M2/B: Regionsvereinigung erhält Referenzen

**Entscheidung / Umfang:** `region_graph.py` ausschließlich um einen expliziten,
revisionsgebundenen `RegionMerge` ergänzt. Das Modul leitet keine Vereinigung aus
Sensordaten ab. Es wählt deterministisch die kleinere bestehende Regions-ID als
kanonisch, übernimmt Zustand und Portale der anderen Region und hält jede entfernte
ID dauerhaft als Alias auflösbar. Alle Portalenden und die aktuelle Region werden
auf die kanonische ID umgeschrieben. Replays alter Portal-/Durchfahrtsereignisse
geben normalisierte IDs zurück, ohne erneut Zustand zu verändern.

**Nachgewiesenes Verhalten:** Eine synthetische Schleifenschließung vereinigt das
erneut erreichte Startgebiet mit seiner vorläufigen Zweit-ID; die beiden
Flurverbindungen zeigen anschließend auf dieselben zwei kanonischen Regionen.
Gesehen/betreten, Portalbestand und Eintrittszähler bleiben erhalten. Mehrstufige
Merges flachen alle alten Aliaswege auf eine kanonische ID ab. Wird eine direkt
verbundene Gegenregion vereinigt, bleibt das Portal als interne Verbindung
referenzierbar, zählt aber keine neue Regionsbetretung. Neue Eingaben dürfen eine
historische Alias-ID verwenden.

Exakte Merge-Replays sind idempotent. Widersprüchliche Wiederverwendung,
Selbstmerge, bereits vereinigte Paare unter neuer ID, unbekannte Regionen,
fremder Kontext, veraltete Revision und feste Mergegrenzen schlagen vor jeder
Teilumschreibung geschlossen fehl.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Umgebung,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2B-GRAPH | Regionsgraph-Suite: **32 passed**, davon 15 neue Merge-/Aliasfälle. |
| WE-M2B-ADJACENT | Explorer-, Kartenmanager- und Semantikmanager-Suiten gemeinsam: **243 passed**. |
| WE-M2B-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **141 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2B-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Der Colcon-Aufbau überschreibt keine Arbeitsinstallation und nutzt
`robot_interfaces` aus dem vorhandenen Underlay; er ist kein vollständiger
Workspace- oder Zielsystemnachweis. Nicht geprüft wurden echte Schleifen,
automatische Gleichheitsentscheidung, ROS-QoS/TF, Laufzeitlast, Sensorik,
Footprint oder Hardware.

**Offene Risiken / Integrationsabhängigkeiten:** Ein Merge ist eine externe
Entscheidung; Quelle, Geometriebeleg und Schwellen fehlen bewusst. Eine falsche
Entscheidung würde Regionen zusammenlegen, auch wenn die Datenstrukturen selbst
konsistent bleiben. Direkte Portalverbindungen innerhalb einer vereinigten Region
bleiben als `internal` erhalten, bis ein späterer Vertrag ihre Behandlung festlegt.
Aufgaben besitzen noch keine stabilen Graphreferenzen, und eine Region kann noch
nicht kontrolliert geteilt werden. Keine grüne Prüfung belegt reale Raumgleichheit.

**Nächster abgegrenzter Schritt WE-M2/C:** Nur `region_graph.py`, dessen Tests und
diese STATUS.md ändern. Stabile Aufgaben-ID, Typ (`frontier`, `portal`,
`observation`), kanonischer Regionsbezug und Erzeugungs-/Aktualisierungsrevision
als begrenzte, idempotente Referenz führen. Bei Merge müssen offene und erledigte
Referenzen erhalten und auf die kanonische Region auflösbar bleiben; keine Aufgabe
darf durch Alias oder Replay verschwinden. Noch keine Priorität, Retrylogik,
Blacklist, Zielkoordinate, automatische Reaktivierung, Regionsteilung, ROS-Ausgabe
oder Navigation.

**Rückfallweg:** Den WE-M2/B-Commit beziehungsweise den gestapelten Review-PR
zurücknehmen. WE-M2/A und WE-M1 bleiben separat reviewbar. Da kein Runtime-Pfad
den Regionsgraph importiert, gibt es keine Runtime- oder Geräteänderung
zurückzusetzen.

### 2026-09-14 – WE-M2/A: vorläufige Topologie ohne Laufzeitwirkung

**Entscheidung / Umfang:** Neu `region_graph.py` als reines, begrenztes
In-Memory-Modul. Eine explizite Startbeobachtung erzeugt genau eine Startregion.
Nur ein konsistent als `confirmed` gelieferter Portalstand darf eine kanonische
Verbindung A/B und eine vorläufige Gegenregion erzeugen; Kandidaten oder unsichere
Portale werden sichtbar zurückgestellt. Ein bereits extern validiertes
Durchfahrtsereignis kann gesehen/betreten und die aktuelle Region fortschreiben.
Das Modul segmentiert keine Karte, validiert keine Bewegung und erzeugt keine
Navigationsziele oder Freigaben.

**Nachgewiesenes Verhalten:** Der synthetische Pfad Startzimmer → Flur → weiteres
Zimmer und zurück verwendet beim Rückweg wieder dieselbe Flur-ID. Dieselbe Tür
von der Gegenseite erzeugt weder neue Region noch Verbindung. Ein offener Bereich
ohne bestätigtes Portal bleibt eine Region. Unbestätigte Durchfahrten ändern weder
Eintritt noch aktuelle Region. Replays sind idempotent; widersprüchliche IDs,
unbekannte Regionen/Portale, falsche aktuelle Region, fremder Kontext, veraltete
Revision, zukünftiger Portalstand, inkonsistenter Bestätigungsstatus und feste
Kapazitätsgrenzen schlagen geschlossen fehl.

Eine über ein bestätigtes Portal erzeugte Gegenregion gilt topologisch als
`seen`, aber erst nach bestätigtem externen Durchfahrtsereignis als `entered`.
Der Start gilt als betreten, erhöht jedoch keinen Überquerungszähler. Diese
Definitionen sind reine Modellsemantik und kein physischer Raumbeleg.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Umgebung,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2A-GRAPH | Neue Regionsgraph-Suite: **17 passed**. |
| WE-M2A-ADJACENT | Explorer-, Kartenmanager- und Semantikmanager-Suiten gemeinsam: **228 passed**. |
| WE-M2A-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **126 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2A-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Der Colcon-Aufbau überschreibt keine Arbeitsinstallation und nutzt
`robot_interfaces` aus dem vorhandenen Underlay; er ist kein vollständiger
Workspace- oder Zielsystemnachweis. Nicht geprüft wurden ROS-QoS/TF, echte
Regionen, SLAM-Korrekturen, Laufzeitlast, Sensorik, Footprint oder Hardware.

**Offene Risiken / Integrationsabhängigkeiten:** `PortalSnapshot` und
`TraversalEvent` sind reine Eingaben; der Adapter zu Main-/HWT-Detektoren und zur
realen Bewegungsvalidierung fehlt. Der Graph nimmt keine automatische
Raumsegmentierung oder feste Zimmerzahl an, kann aber deshalb noch nicht erkennen,
dass zwei vorläufige IDs nach einem Schleifenschluss dieselbe Region meinen. Er
führt noch keine Aufgaben und verarbeitet weder Teilung noch Kartenursprungs-
oder Geometriekorrekturen. Keine der grünen Prüfungen belegt eine reale Region.

**Nächster abgegrenzter Schritt WE-M2/B:** Nur `region_graph.py`, dessen Tests und
diese STATUS.md ändern. Eine explizite, revisionsgebundene Merge-Operation muss
zwei vorläufige Regionen deterministisch auf eine kanonische ID vereinigen,
alte IDs als Alias lesbar halten und sämtliche Portalenden, gesehen/betreten,
Eintrittszähler sowie aktuelle Region verlustfrei umschreiben. Replays,
widersprüchliche/stale Merges, Selbstmerge, Kapazitätsgrenzen und eine L-Flur-
Schleife testen. Noch keine automatische Mergeentscheidung, Regionsteilung,
Aufgaben, ROS-Ausgabe oder Navigation.

**Rückfallweg:** Den WE-M2/A-Commit beziehungsweise den gestapelten Review-PR
zurücknehmen. WE-M1/A bis C bleiben separat reviewbar. Da keine Runtime-Datei den
Regionsgraph importiert, gibt es keine Runtime- oder Geräteänderung zurückzusetzen.

### 2026-09-14 – WE-M1/C: Bestätigung an qualifizierte Evidenz gebunden

**Entscheidung / Umfang:** `PortalObservation` führt nun eine explizite, vom
Detektor zu liefernde Strukturevidenz `qualified`, `insufficient` oder
`contradictory`. Fehlt sie, gilt fail-closed `insufficient`. Das Gedächtnis
implementiert keine Tür-/Möbelerkennung, sondern zählt qualifizierte Evidenz nur
einmal je Kartenrevision. Der öffentliche Zustand unterscheidet Kandidat,
bestätigt und unsicher. Bestehende Ereignis- und Erreichbarkeitsachsen bleiben
getrennt. Keine Runtime-Datei außerhalb des reinen Moduls und seiner Tests geändert.

**Nachgewiesenes Verhalten:** Wiederholte unzureichende Beobachtungen einer
synthetischen Möbelengstelle bestätigen kein Portal. Widersprüchliche Evidenz
setzt den Zustand auf `uncertain`; unzureichende Folgebeobachtungen heben dies
nicht stillschweigend auf, erst eine neuere qualifizierte Revision kann erneut
bestätigen. Mehrere qualifizierte Meldungen derselben Kartenrevision zählen nur
einmal. Verlorene Struktursicht löscht eine zuvor belastbare Identität nicht.
Verschobene Raumschwerpunkte sind kein Identitätsmerkmal. Zahl erkannter Portale,
Beobachtungen und bestätigter Überquerungen bleiben getrennte Kennzahlen.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Umgebung,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M1C-PORTAL | Portalgedächtnis-Suite: **51 passed**, davon 8 neue Evidenz-/Abgrenzungsfälle. |
| WE-M1C-ADJACENT | Explorer-, Kartenmanager- und Semantikmanager-Suiten gemeinsam: **211 passed**. |
| WE-M1C-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **109 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M1C-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Damit sind die synthetischen WE-M1-Pflichtfälle Gegenrichtung, Kartenwachstum,
bewegter Raumschwerpunkt, Ursprung/Raster, nahe Türen, Möbelengstelle, verlorene
Sicht, identische Kartenrevision, blockiert → offen, Ambiguität und Ereignisreplay
abgedeckt. Der temporäre Colcon-Aufbau überschreibt keine Arbeitsinstallation und
nutzt `robot_interfaces` aus dem vorhandenen Underlay; er ist kein vollständiger
Workspace- oder Zielsystemnachweis.

**Offene Risiken / Integrationsabhängigkeiten:** Die Evidenzklasse ist ein
Eingabevertrag, kein gemessener Nachweis. Welcher vorhandene Main-/HWT-Detektor
sie unter welchen begründeten Schwellen liefern darf, bleibt vor einer passiven
Integration zu klären. Große SLAM-Korrekturen werden weiterhin nicht über
Kartenkontexte hinweg vereinigt. Ebenso bleiben reale Pose-/Footprint-Prüfung,
Zeitquelle, Zielsystemlast, dauerhafte Speicherung und jede Fahrwirkung offen.
Deshalb bedeutet `softwaregeprüft` hier nur den isolierten WE-M1-Logikkern.

**Nächster abgegrenzter Schritt WE-M2/A:** Neu ausschließlich
`src/explore/explore/region_graph.py` und
`src/explore/test/test_region_graph.py` sowie diese STATUS.md. Vorläufige stabile
Regions-IDs, Verbindungen über bestätigte Portal-IDs, Seitenzuordnung und
gesehen/betreten mit Karten-/Revisionsbezug als reines In-Memory-Modell führen.
Synthetisch Startraum–Flur–Zimmer, Rückkehr in denselben Flur, offenen Wohnbereich,
unbekannte/unsichere Portale, Kontextfehler und harte Speichergrenzen prüfen.
Teilung/Vereinigung, Aufgabenbestand, Policy und passive ROS-Ausgabe bleiben
nachfolgende WE-M2-Teilschritte; das Graphmodell erzeugt keine Navigationsziele.

**Rückfallweg:** Den WE-M1/C-Commit beziehungsweise den gestapelten Review-PR
zurücknehmen. WE-M1/A und B bleiben separat reviewbar. Da kein bestehender
Runtime-Pfad das Portalmodul importiert, gibt es keine Runtime- oder
Geräteänderung zurückzusetzen.

### 2026-09-14 – WE-M1/B: Ereignis und Erreichbarkeit getrennt geführt

**Entscheidung / Umfang:** Das reine `portal_memory.py` ausschließlich um zwei
Zustandsachsen ergänzt. Ein `TraversalEvent` übernimmt ein bereits extern
validiertes Urteil mit Ereignis-ID, Portal-ID, Richtung, Zeit sowie Kartenkontext
und -revision. Eine `ReachabilityUpdate` beschreibt unabhängig davon den aktuellen
Zustand einer Portalseite als offen, vorübergehend blockiert, unklar oder bewusst
ausgeschlossen, jeweils mit Grund und erneuter Prüfbedingung. Das Modul liest
keine Pose, keinen Footprint, Encoder oder Sensoren und trifft keine Fahrentscheidung.

**Nachgewiesenes Verhalten:** Bestätigte Überquerungen werden genau einmal
gezählt; ein identisches Replay ändert weder Zähler noch Historie. Unbestätigte
Ereignisse bleiben sichtbar, zählen aber nicht als Überquerung. Hin- und Rückweg
sind getrennte Ereignisse derselben Portal-ID. Konfligierende IDs, unbekannte
Portale, fremde Kontexte, veraltete Revisionen, ungültige Felder und harte
Speichergrenzen werden abgelehnt. Ohne Bewertung ist jede Seite ausdrücklich
`unknown`, nicht stillschweigend offen. Verlorene Sicht löscht keine Identität;
ein neuerer externer Befund kann `temporarily_blocked` wieder auf `open` setzen.
Die Seitenzustände bleiben unabhängig, und ein historisch beobachteter Rückweg
wird nicht durch diese reine Buchhaltung unterdrückt.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Umgebung,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M1B-PORTAL | Portalgedächtnis-Suite: **43 passed**, davon 23 neue Ereignis-/Erreichbarkeitsfälle. |
| WE-M1B-ADJACENT | Explorer-, Kartenmanager- und Semantikmanager-Suiten gemeinsam: **203 passed**. |
| WE-M1B-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; anschließender Pakettest: **101 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M1B-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Geprüft sind Replay nach späterem Zählerstand, bestätigte/unbestätigte Ereignisse,
beide Richtungen, Kontext-/Revisionsfehler, verlorene Sicht, blockiert → offen,
seitenspezifische Zustände, unveränderte Historie sowie getrennte Kapazitätsgrenzen.
Der Colcon-Aufbau überschrieb das vorhandene `explore` nur in einem temporären
Ausgabeverzeichnis und nutzte `robot_interfaces` aus dem vorhandenen Underlay;
er ist kein sauberer Gesamtworkspace- oder Zielsystemaufbau. Nicht ausgeführt
wurden ROS-/Zielsystemstart, Jetson-, Sensor-, Footprint- oder Hardwaretests.
Softwaretests validieren keine reale Überquerung.

**Offene Risiken / Integrationsabhängigkeiten:** `crossing_confirmed` ist bewusst
ein externes Urteil; Quelle, Frische und vollständiger Chassis-/Auslaufnachweis
werden erst in einem späteren Integrationsschritt festgelegt und dürfen nicht aus
Nav2-Erfolg allein entstehen. Die aktuellen Zeitfelder definieren noch keine
ROS-Uhrquelle. Erreichbarkeit erzeugt weder Blacklists noch Navigationsfreigaben.
Vor allem genügt die bisherige Zahl unterschiedlicher Kartenrevisionen noch nicht,
um eine wiederholt sichtbare Möbelengstelle als Tür auszuschließen. Deshalb bleibt
WE-M1 trotz grüner Tests in Arbeit.

**Nächster abgegrenzter Schritt WE-M1/C:** Nur Portalmodul, synthetische Tests und
diese STATUS.md ändern. Die Bestätigung benötigt neben unabhängiger Revision eine
explizite, detectorseitig gelieferte qualifizierte Strukturevidenz; fehlende oder
widersprüchliche Evidenz bleibt Kandidat beziehungsweise unsicher. Tests für eine
wiederholt beobachtete Möbelengstelle, verlorene Sicht ohne Identitätsverlust,
bewegten Raumschwerpunkt und stabile Zählertrennung ergänzen. Keine neue
Bild-/Costmap-Erkennung implementieren und keine Schwellen als Hardwaremessung
ausgeben. Erst danach WE-M1 als reine Logik insgesamt bewerten.

**Rückfallweg:** Den WE-M1/B-Commit beziehungsweise dessen gestapelten Review-PR
zurücknehmen. WE-M1/A bleibt separat reviewbar. Da weiterhin kein bestehender
Runtime-Pfad das Modul importiert, gibt es keine Runtime- oder Geräteänderung
zurückzusetzen.

### 2026-09-14 – WE-M1/A: stabile Portalidentität ohne Laufzeitbindung

**Entscheidung / Umfang:** Den in WE-M0/A abgegrenzten kleinsten Schritt als
reines Standardbibliotheksmodul `portal_memory.py` umgesetzt. Das Modul übernimmt
ausschließlich bereits normalisierte metrische Beobachtungen; es erkennt oder
befährt selbst kein Portal. `explore_node.py`, bestehende Detektoren, Launches,
Actions, Profile, Karten-/Semantikmanager und Fahrpfade bleiben unverändert.

**Nachgewiesenes Verhalten:** Portal-IDs werden deterministisch vergeben und eine
Gegenrichtungsbeobachtung derselben lokalen Geometrie derselben ID mit vertauschter
Annäherungsseite A/B zugeordnet. Evidenz zählt unterschiedliche Kartenrevisionen,
nicht wiederholte Aufrufe; identische Beobachtungs-IDs sind idempotent, eine
widersprüchliche Wiederverwendung wird abgelehnt. Sitzung, Kartenepoche und Frame
sind eine harte Kontextgrenze. Nicht endliche Geometrie, zu hohe Unsicherheit,
unbekannte veraltete Revisionen und feste Speichergrenzen schlagen geschlossen
fehl. Bei nahezu gleichwertigen Kandidaten wird keine Portalidentität bestätigt
oder verändert.

Die Portalgeometrie bleibt absichtlich am ersten eindeutigen metrischen Anker;
Rasterursprung und Auflösung sind daher nur nach externer Normalisierung relevant.
Die voreingestellten Abstands-, Winkel- und Unsicherheitsgrenzen sind ausdrücklich
synthetische Softwarestartwerte, keine vermessenen Tür-, Lokalisierungs- oder
Hardwaretoleranzen.

**Ausgeführte Prüfungen:** Auf dem lokalen x86_64-Arbeitsplatz mit ROS-Humble-
Umgebung, aber ohne ROS-Start, Gerätezugriff oder Kartendaten:

| Test-ID | Ergebnis |
|---|---|
| WE-M1A-EXPLORE | Gesamte Explorer-Suite einschließlich 20 neuer Portalgedächtnis-Fälle: **78 passed**. |
| WE-M1A-ADJACENT | Explorer-, Kartenmanager- und Semantikmanager-Suiten gemeinsam: **180 passed**. |
| WE-M1A-STATIC | `flake8` (E501/W503 ausgenommen): bestanden; `git diff --check`: bestanden. |

Die neuen Fälle decken Gegenrichtung, getrennte Evidenzrevisionen, kleine
Geometrieabweichung, nahe parallele Türen, Mehrdeutigkeit, Kontextwechsel,
veraltete Daten, ungültige Zahlen, Unsicherheits- und Kapazitätsgrenzen sowie
metrische Äquivalenz bei geändertem Raster/Ursprung ab. Bestanden sind damit
Softwaretests, keine ROS-, Colcon-, Jetson- oder Hardwareabnahme.

**Offene Risiken / Integrationsabhängigkeiten:** Der Detektor-zu-Beobachtung-
Adapter und eine gültige Quelle für Sitzung, Kartenepoche, Revision und
Unsicherheit sind noch nicht festgelegt. Große SLAM-Korrekturen werden nicht über
Kontexte hinweg zugeordnet. Möbelengstellen bleiben Aufgabe vorhandener
Detektorevidenz. Verlorene Sicht, blockiert → erneut offen und tatsächliche
Überquerungen benötigen die getrennten Zustandsachsen aus WE-M1/B. Der weiterhin
offene Zielsystemabgleich aus WE-M0/B wird nicht durch diese Offline-Prüfung
ersetzt.

**Nächster abgegrenzter Schritt WE-M1/B:** Nur `portal_memory.py`, dessen neue
Tests und diese STATUS.md erweitern: Ereignis-ID, Portal-ID, Richtung und
Zeit-/Kartenbezug als validierten Durchfahrtsbeleg führen; unbestätigte und
bestätigte Überquerung unterscheiden und identische Ereignisse genau einmal
zählen. Daneben aktuelle Erreichbarkeit (`offen`, `vorübergehend blockiert`,
`unklar`, `bewusst ausgeschlossen`) mit Grund und erneuter Prüfbedingung getrennt
halten. Tests müssen insbesondere Replay, Gegenrichtung, unbekannte Portal-ID,
Kontext-/Revisionsfehler, verlorene Sicht und blockiert → erneut offen prüfen.
Keine Pose-/Footprint-Auswertung erfinden: WE-M1/B konsumiert nur bereits extern
validierte Bewegungsbelege und bleibt ohne ROS-/Fahrintegration.

**Rückfallweg:** Den WE-M1/A-Commit beziehungsweise Review-Branch zurücknehmen.
Da das neue Modul von keinem Runtime-Pfad importiert wird, bleibt das bisherige
Roboterverhalten unverändert; es gibt kein Deployment und keinen Gerätezustand
zurückzusetzen.

### 2026-09-14 – WE-M0/A auf Main-basierte reine Portalidentität begrenzt

**Entscheidung:** Der erste Funktionsschritt wird als WE-M1/A auf dem dann
aktuellen Main ausgeführt und liefert nur eine nicht eingebundene, reine
Portalidentitätslogik. HWT bleibt Referenz für Beobachtungsgeometrie und
historische Fahrt, wird aber weder insgesamt gemerged noch als installierte
Gesamtbasis behauptet.

**Grund / Evidenz:** Main, HWT und lokale Installation sind drei verschiedene
Stände. HWT besitzt wichtige Portal-/Auslaufkorrekturen, aber noch keine
stabilen IDs. Die lokale Primärinstallation ist ein nicht reproduzierbarer
Mischstand; zugleich sind Karten-/Semantikquellen auf Main und HWT identisch.
Damit kann der fehlende Identitätskern ohne Fahrwirkung und ohne Vorwegnahme
der späteren Drei-Wege-Integration isoliert getestet werden.

**Betroffene Dateien und Hardware:** Nur diese fachliche Statusdatei. Die
Bestandsprüfung las Git-Objekte, lokale Build-/Installationspfade und Quelltests.
Keine Fahrsoftware, ROS-Prozesse, Geräte, Karten, Bags oder Hardware geändert.

**Teststatus:** 160 Tests auf der Main-/Dokumentationsbasis, 80 HWT-Explorer-
Tests und 67 Tests des lokalen Explorer-Quellstands bestanden. Dies sind
Softwaretests ohne Zielsystem- oder Hardwareabnahme.

**Offene Risiken:** Drei-Wege-Integration von HWT, lokaler Konturstrategie und
aktuellem Main; stale Semantikinstallation; HWT-Underlay-/Profilpfade;
Last-/TF-Befunde sowie reale Wiederholung der HWT-Abschlusskorrektur.

**Rückfallweg:** Diese Statusergänzung revertieren. Es existiert keine
Runtime-Wirkung und keine funktionale Branchübernahme.

### 2026-09-14 – WE-1 als schrittweises Vorhaben festgelegt

**Entscheidung:** Bestehende Frontier-Erkundung um dauerhaftes Portalgedächtnis,
vorläufigen Raumgraphen und Flur-/Raumstrategie ergänzen; Nav2, Sensorfusion und
Sicherheitsausführung bleiben die Basis. Umsetzung in WE-M0 bis WE-M7 statt
Gesamt-Neuentwicklung in einem Agentenlauf.

**Grund / Evidenz:** Nutzer hat diese Strategie bestätigt. Die eingecheckte
HWT-Erprobung belegt einen Raumwechsel und eine spätere Portal-Doppelerkennung.
Das rechtfertigt die gezielte Identitäts-/Rückwegerweiterung, nicht eine bereits
bestandene Vollwohnungserkundung.

**Betroffene Dateien und Hardware:** Nur Strategie, Agentenkontext, Roadmap,
Status und Dokumenteinstiege; alter Strategiestand historisch erhalten.
Keine Geräte, ROS-Prozesse, Parameter, Treiber oder funktionalen Branches geändert.

**Teststatus:** Dieser Eintrag ist eine Planentscheidung. Neue Runtime-, ROS-,
Jetson- und Fahrtests wurden für die Dokumentation nicht ausgeführt. Tatsächliche
Dokumentations-/Remote-Prüfungen werden im zugehörigen PR dokumentiert.

**Offene Risiken:** Integrationsbasis, Baseline-Nachtest, Ressourcenlast und
geplante neue Logik wie oben. Kein universeller Vollständigkeits- oder
Sicherheitsnachweis allein durch diesen Plan.

**Rückfallweg:** Nur den Dokumentationscommit zurücknehmen. Der bisherige
Strategiestand liegt unverändert im Archiv; Roboterlaufzeit bleibt unberührt.

## 7. Pflege nach jedem Arbeitsschritt

Nächsten Schritt, betroffene Statuszeilen und neue Evidenz aktualisieren; keine
vorweggenommenen Gesamthäkchen. Planabweichungen und relevante Entscheidungen hier
mit Datum, Grund, Code-/Dokumentenstand, Tests, offenen Risiken und Rückfallweg
festhalten. Übergreifende Projektentscheidungen zusätzlich mit Verweis in
`docs/PROJECT_MEMORY.md`, echte Betriebsänderungen in `docs/ROBOT_TRANSFER.md`.

Nach Merge/Deployment den nachgewiesenen Stand ausdrücklich eintragen. Ein alter
Commit in dieser Tabelle ist eine Referenz und kein Auftrag, spätere Arbeit auf
diesen Stand zurückzusetzen. Keine privaten Wohnungsgeometrien oder Rohdaten
in diesen Status kopieren.
