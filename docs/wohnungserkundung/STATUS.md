# Wohnungserkundung – laufender Status und Entscheidungen

**Vorhaben WE-1 · Aktualisiert: 2026-09-14 (WE-M2/L)**

Dies ist der einzige laufende Fortschrittsstand des Vorhabens. Die
[Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) beschreibt das Soll,
die [Roadmap](MEILENSTEINE.md) die Abnahmen und der
[Agentenauftrag](AGENTENAUFTRAG.md) den Arbeitsablauf. Historische Logs bleiben
Quellen, aber ersetzen diesen statusbezogenen Einstieg nicht.

## 1. Aktueller nächster Schritt

**WE-M2/L – Kartenmanager-Status-JSON rein decodiert und softwaregeprüft, zur
Review.** Der tatsächliche Schema-1-Umschlag von
`/robot_map_manager/status_json` wird größen- und tiefenbegrenzt auf
`MapManagerStatusSample` abgebildet. Pflichtpfade und Typen werden nicht geraten
oder umgewandelt; zusätzliche reale Statusfelder bleiben innerhalb der Grenzen
zulässig. Es gibt weiterhin keine ROS-Subscription, Uhr-, Explorer- oder
Fahrwirkung.

**Nächster vorgeschlagener Umsetzungsschritt nach Review: WE-M2/M.** Eine neue
reine Lebenszyklusklasse soll genau einen `MapManagerStatusCorrelator` und nach
dem ersten gültigen decodierten Status genau eine `RegionGraphShadowSession`
besitzen. Sie erhält Sitzungs-ID, erwarteten Frame und Startbeobachtungs-ID
explizit, erzeugt den `RegionSeed` erst aus dem ersten Korrelationsresultat und
führt weitere Status-JSONs fail-closed fort. Nichtverfügbarkeit vor dem ersten
Snapshot bleibt wartend; Epochenwechsel, Kontextfehler und Neustart werden nicht
automatisch über alte Zustände hinweg geheilt. Nur neues reines Modul, dessen
Tests und diese STATUS.md; noch keine ROS-Subscription, Uhr, Portalzuführung,
Node-, Launch-, Parameter- oder Fahrsoftware.

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
| WE-M2/C `feature/we-m2c-task-references` | Gestapelte passive Aufgabenreferenzen mit aliasfestem Regionsbezug; nur Graphmodul, Tests und Status, kein Deployment. |
| WE-M2/D `feature/we-m2d-region-split` | Gestapelte, vollständig spezifizierte Regionsteilung; nur Graphmodul, Tests und Status, kein Deployment. |
| WE-M2/E `feature/we-m2e-shadow-status` | Gestapelte reine JSON-Schattenprojektion mit expliziter Revisionsfrische und harten Ausgabegrenzen; neues Modul, Tests und Status, kein Publisher oder Deployment. |
| WE-M2/F `docs/we-m2f-shadow-integration` | Gestapelte Integrationsentscheidung zu Eingängen, Zustandsbesitz, getrenntem Topic, QoS, Frische und Rückfall; nur Statusdokumentation. |
| WE-M2/G `feature/we-m2g-source-ages` | Gestapelte reine Zeitfrische für Kartenquelle, Portalgedächtnis und Regionsgraph; Statusmodul, Tests und Status, keine Runtime-Einbindung. |
| WE-M2/H `feature/we-m2h-portal-adapter` | Gestapelte fail-closed Normalisierung vorhandener Portalpläne zu ausschließlich unqualifizierten Beobachtungen; neues Modul, Tests und Status. |
| WE-M2/I `feature/we-m2i-shadow-session` | Gestapelte reine Sitzungsaggregation aus begrenztem Portalgedächtnis, Regionsgraph und Schattenstatus; neues Modul, Tests und Status. |
| WE-M2/J `feature/we-m2j-map-status-adapter` | Gestapelte reine Korrelation des vorhandenen Kartenmanagerstatus zu Kontext, sitzungsbezogener Revision und Quellalter; neues Modul, Tests und Status. |
| WE-M2/K `feature/we-m2k-map-shadow-handoff` | Gestapelte typisierte Übergabe von Kartenstatuskorrelation an die reine Schatten-Sitzung; Aggregatmodul, Vertragstests und Status. |
| WE-M2/L `feature/we-m2l-map-status-json` | Gestapelte reine, begrenzte Decodierung des tatsächlichen Kartenmanager-Status-JSON in den bestehenden Korrelationsvertrag; Adapter, Tests und Status. |

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
| WE-M2 | In Arbeit | WE-M2/A bis L decken reine Topologie, Korrekturen, Aufgabenbezug, Statusprojektion, Integrationsgrenze, Zeitfrische, unqualifizierte Portalplan-Normalisierung, Schattenaggregation, Kartenstatuskorrelation, deren typisierte Übergabe und die reine JSON-Decodierung ab. Lebenszyklus-/ROS-Eingang, qualifizierte Evidenz und passive ROS-Ausgabe offen. |
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
Regionsvereinigung und erhält alte IDs als Alias. WE-M2/C erhält offene und
erledigte Aufgabenreferenzen bei diesen Vereinigungen und löst ihren Regionsbezug
kanonisch auf. WE-M2/D teilt eine Region nur nach vollständiger externer
Zuordnung aller Portalenden und Aufgaben und erhält Replays. Eine neue bestätigte
Portal-ID erzeugt weiterhin zunächst eine vorläufige Gegenregion. Automatische
Merge-/Splitentscheidung und Geometriekorrekturen fehlen. WE-M2/E kann den
vorhandenen Stand passiv, revisionsgebunden und ohne metrische Geometrie
serialisieren. WE-M2/F legt getrenntes Topic, QoS und Zustandsbesitz fest, belegt
aber zugleich, dass Zeitfrische und zulässige Evidenzadapter vor der ROS-Ausgabe
fehlen. WE-M2/G ergänzt die Zeitfrische fail-closed; die Alterswerte selbst muss
der noch fehlende Runtime-Adapter aus einer monotonen Uhr liefern. WE-M2/H kann
vorhandene Portalpläne ohne ROS-Abhängigkeit normalisieren, stuft sie aber bewusst
nicht als bestätigte Struktur ein und verbindet sie daher noch nicht mit dem
Regionsgraphen. WE-M2/I besitzt diese Zustände nun in genau einer passiven
Sitzung; die tatsächliche Kartenepoche und monotone Quellzeit bleiben explizite,
noch nicht angebundene Eingaben. WE-M2/J kann diese Angaben aus einem konsistenten
Verlauf der explizit extrahierten Kartenmanagerfelder ableiten. WE-M2/K bindet
dieses Ergebnis typisiert und revisionsmonoton an die Sitzung. WE-M2/L decodiert
den tatsächlichen Statusumschlag rein und begrenzt; Lebenszyklusbesitz,
ROS-Subscription und echte Laufzeitalter fehlen weiterhin.

**Unabhängiger Testbasisbefund:** Ein zusätzlich ausgeführter, unveränderter
Nahbereichs-Vertragstest erwartet im Mapping-Profil einen kreisförmigen
`FootprintApproach`, während die bereits auf der WE-M2/B-Basis eingecheckte
Konfiguration ein Polygon enthält (268 bestanden, 1 fehlgeschlagen). WE-M2/C
ändert weder Test noch Konfiguration. Ursache und beabsichtigter Vertrag sind in
einem eigenen sicherheitsrelevanten Auftrag zu klären; dieser Befund ist keine
Freigabe, eine Kollisionsüberwachung zu ändern oder Hardware zu betreiben.

**Kartenintegration:** Manuelle Raum-Overlays, Fingerprints und Speicherverträge
existieren. Die Zuordnung automatischer Erkundungsregionen und laufender Karten-
revisionen muss diese erhalten; konkrete Schema-/API-Erweiterungen sind noch offen.

**Abnahmegrenzen:** Grenzwerte für Identitätszuordnung, Beobachtungsfenster,
Ressourcenbudgets und Wohnungsumfang müssen vor den jeweiligen Tests begründet
festgelegt werden. Die Dokumentation ist kein Ersatz für diese Messungen.

## 6. Entscheidungslog

### 2026-09-14 – WE-M2/L: realen Statusumschlag ohne ROS decodieren

**Quellbefund:** `robot_map_manager_node.py` erzeugt Schema 1 mit
`schema_version` und Unix-Statuszeit `time` auf der obersten Ebene. Unter `map`
liegen `available`, `snapshot_available`, `age_seconds` und `summary`; bei
verfügbarer Karte enthält `summary` unter anderem `fingerprint`, `frame_id` und
`source_stamp_ns`, andernfalls ist es `null`. `accepted_maps` liegt getrennt
unter `counters`. Ereignis, Meldung, Pose, Speicherstatus und weitere Zähler
gehören zum realen Umschlag, werden für WE-M2 aber nicht als Kartenidentität
umgedeutet.

**Entscheidung / Umfang:** `decode_map_manager_status_json()` in
`map_status_adapter.py` bildet ausschließlich diese Pflichtfelder auf den bereits
validierten `MapManagerStatusSample` ab. Der Decoder verlangt Text und ein
JSON-Objekt, übernimmt Werte ohne Typkonvertierung und lässt zusätzliche Felder
zu. Fehlende Pfade, falsche Zwischenobjekte, doppelte JSON-Schlüssel, nicht
endliche JSON-Konstanten, ungültiges Unicode/JSON und eine Teil-Summary schlagen
geschlossen fehl. Bei nicht verfügbarer Karte muss `summary` exakt `null` sein;
der bestehende Sample-Vertrag verlangt zusätzlich Zählerstand 0 und keine
Kartenalter-/Identitätswerte.

Der Eingangsumschlag ist auf **1.048.576 UTF-8-Bytes** und **32 Ebenen** begrenzt.
Beide Werte sind konservative synthetische Softwaregrenzen, keine gemessene
Jetson-Lastabnahme. Die Tiefenprüfung betrachtet auch irrelevante Zusatzfelder,
damit diese die Begrenzung nicht umgehen. Der Decoder liest keine Uhr, Datei,
Karte oder ROS-Schnittstelle und besitzt keinen Korrelations- oder
Sitzungszustand.

**Nachgewiesenes Verhalten:** Synthetische Umschläge in der tatsächlichen
Kartenmanagerstruktur werden für verfügbare und noch nicht verfügbare Karten
feldgleich decodiert. Begrenzte zusätzliche Status- und Summary-Felder werden
ignoriert, auch wenn `ok=false` ist; Kartenverfügbarkeit bleibt der getrennte
Vertrag. Jede Pflichtfeldlücke und alle geprüften Typ-/Strukturfehler werden
abgewiesen. Ein decodiertes Sample durchläuft den bestehenden Korrelator ohne
zusätzliche oder erfundene Werte.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2L-DECODER | Kartenstatusadapter-Suite einschließlich Decodergrenzen: **91 passed**. |
| WE-M2L-EXPLORE | Gesamte Explorer-Suite: **375 passed**. |
| WE-M2L-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **480 passed**. |
| WE-M2L-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **375 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2L-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden eine reale Topic-Nachricht, ROS-Subscription/QoS/Discovery,
Publisher, tatsächliche Statusrate oder Restartfolge, ROS-/Wall-/monotone
Zeitbezüge, Jetson-Laufzeit/Speicher, reale Karten, Portal-/LiDAR-Evidenz,
Sensorik, Footprint, Kollisionswirkung oder Hardware. Die JSON-Decodierung
bestätigt weder Karte, Portal, Durchfahrt noch Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/M:** Neu ausschließlich eine reine
Lebenszyklusklasse, deren Test und diese STATUS.md. Die Klasse besitzt einen
explizit konfigurierten `MapManagerStatusCorrelator`, decodiert über die neue
Funktion und erzeugt beim ersten gültigen Kartenresultat genau eine
`RegionGraphShadowSession` samt revisionsgleichem `RegionSeed`. Weitere
Statusumschläge werden nur in diese Sitzung fortgeführt. Vor erster Karte bleibt
Nichtverfügbarkeit sichtbar, Epochenwechsel und widersprüchliche Folgen verlangen
einen neuen Besitzer statt stiller Wiederverwendung. Noch keine ROS-Subscription,
Uhr, Portalzuführung, Ausgabe, Node-, Launch-, Parameter-, Ziel- oder Fahrsoftware.

**Rückfallweg:** Decoderfunktion und Decoder-Testfälle sowie diesen
WE-M2/L-Statusabschnitt entfernen beziehungsweise den gestapelten PR schließen.
WE-M2/A bis K bleiben separat reviewbar; kein Runtime-, Installations- oder
Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/K: Kartenrevision und Kartenalter nur noch gemeinsam

**Entscheidung / Umfang:** `RegionGraphShadowSession` verlangt beim Erzeugen nun
ein `MapStatusCorrelationResult` aus WE-M2/J statt eines frei übergebenen
`PortalMapContext`. Nur das erste neue Ergebnis (`map_changed=true`, kein Replay)
darf eine Sitzung eröffnen. Der explizite `RegionSeed` muss sowohl denselben
Kontext als auch exakt dessen Kartenrevision tragen. Damit können Startregion,
Sitzung und Kartenstatus nicht mehr aus unabhängig zusammengesetzten Werten
entstehen.

`status_source()` und `build_status_json()` nehmen ebenfalls ein typisiertes
Korrelationsresultat entgegen. Sie übernehmen `map_revision` und
`source_map_age_seconds` gemeinsam und unverändert. Portalgedächtnis- und
Regionsgraphalter bleiben getrennte, explizite Aufrufwerte, weil WE-M2/J sie
nicht messen kann. Normaler Kartenfortschritt, ausgelassene Revisionen,
periodischer Gleichstand und exaktes Replay bleiben im selben Kontext zulässig.
Ein anderer `PortalMapContext` oder eine Revision hinter dem zuletzt angenommenen
Kartenstatus schlägt vor jeder Änderung des Sitzungsstands geschlossen fehl.
Auch ein Fehler in Snapshotbildung oder Serialisierung übernimmt den neuen
Kartenstatus nicht.

Die bisherige manuelle Kartenrevision und das separat behauptete Kartenalter
wurden aus der öffentlichen Aggregat-API entfernt. Der bestehende
Kartenadapter-Übergabetest wurde ausschließlich an diesen neuen Vertrag angepasst;
Korrelation, JSON-Eingang und Kartenmanager selbst ändern sich nicht. Das Modul
bleibt reine In-Memory-Logik ohne ROS-, Uhr-, Datei-, Karten-, Ziel- oder
Aktorschnittstelle.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2K-HANDOFF | Kartenadapter- und Schatten-Sitzungssuiten gemeinsam: **79 passed**. |
| WE-M2K-EXPLORE | Gesamte Explorer-Suite: **333 passed**. |
| WE-M2K-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **438 passed**. |
| WE-M2K-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **333 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2K-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden JSON-Decodierung, ROS-Subscription/QoS/Discovery, reale
monotone oder ROS-/Wall-Zeitbezüge, Kartenmanager-Neustart im Prozessverbund,
Jetson-Laufzeit/Speicher, reale Karten, qualifizierende Portal-/LiDAR-Evidenz,
Sensorik, Footprint, Kollisionswirkung oder Hardware. Die reine Übergabe bestätigt
weder Kartenqualität, Portal, Durchfahrt noch Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/L:** Im bestehenden
`map_status_adapter.py` eine reine Decoderfunktion für den tatsächlichen
Schema-1-JSON-Umschlag des Kartenmanagers ergänzen und synthetisch gegen exakte
Feldabbildung, Nichtverfügbarkeit, fehlende oder falsch geformte
Zwischenstrukturen, zusätzliche irrelevante Felder, ungültiges Unicode/JSON,
falsche Typen, Rekursion und eine feste Eingangsgrenze prüfen. Die Funktion
erzeugt nur `MapManagerStatusSample`; sie liest keine Uhr und besitzt weder
Subscription noch Sitzung. Nur Adapter, dessen Test und diese STATUS.md; keine
Node-, Explorer-, Launch-, Parameter-, Ziel- oder Fahrsoftware.

**Rückfallweg:** Die Kartenstatusargumente von `RegionGraphShadowSession` auf den
WE-M2/I-Vertrag zurücksetzen, die WE-M2/K-Testfälle und diesen Statusabschnitt
entfernen beziehungsweise den gestapelten PR schließen. WE-M2/A bis J bleiben
separat reviewbar; kein Runtime-, Installations- oder Gerätezustand ist
zurückzusetzen.

### 2026-09-14 – WE-M2/J: Kartenfortschritt und Kartenepoche bleiben getrennt

**Quellkorrektur:** Die erneute Prüfung des tatsächlichen Kartenmanagers zeigt:
`accepted_maps` steigt nur, wenn ein neuer `MapSnapshot` einen anderen
Inhaltsfingerprint besitzt. Ein Fingerprintwechsel zusammen mit höherem Zähler
ist daher normaler Kartenfortschritt innerhalb derselben Sitzung, nicht pauschal
eine neue Kartenepoche. Duplikate behalten Fingerprint, Quellstempel und Zähler;
lediglich das Empfangsalter kann durch erneuten Empfang sinken. Der in WE-M2/I
vorgeschlagene pauschale Epochenwechsel bei jedem Fingerprintwechsel wird damit
quellenbasiert berichtigt.

**Entscheidung / Umfang:** Neu `map_status_adapter.py`. Ein unveränderlicher
`MapManagerStatusSample` bildet ausschließlich die relevanten bereits geparsten
Schema-1-Felder ab: Statuszeit, beide Verfügbarkeitsflags, `accepted_maps`,
SHA-256-Fingerprint, Frame, Quellstempel und Empfangsalter. Vollständigkeit,
Datentypen, sichere Kennungen sowie nichtnegative endliche Zeiten werden vor der
Korrelation geprüft. Nicht verfügbare Karten dürfen keine Teilfelder oder einen
Zähler tragen.

`MapManagerStatusCorrelator` verlangt eine externe Sitzungs-ID und einen
erwarteten Frame. Der erste vollständige Status verankert die Kartenepoche am
ersten beobachteten Fingerprint; `accepted_maps` bleibt unverändert die
prozesslokale Revision. Spätere Fingerprint- und Zähleränderung müssen gemeinsam
erfolgen, Zählersprünge wegen ausgelassener Statusmeldungen bleiben zulässig.
Gleicher Kartenstand behält Revision und Kontext, darf aber ein aktualisiertes
Empfangsalter liefern. Quellstempel null bleibt als explizit unbekannte ROS-Zeit
zulässig.

Zählerrücklauf, Framewechsel, erneute Nichtverfügbarkeit oder rückläufiger
Quellstempel verlangen `MapEpochChangeRequired`; der Aufrufer muss dann eine neue
Sitzungs-ID und neue Zustandsbesitzer anlegen. Rückläufige Statuszeit,
Fingerprint/Zähler-Widerspruch oder Quellstempelwechsel ohne neue akzeptierte
Karte wird als ungültig abgewiesen. Ein Quellstempel mehr als **0,5 s** vor der
mitgelieferten Statuszeit wird ebenfalls verworfen. Diese Toleranz ist nur ein
synthetischer Softwarestartwert und keine gemessene ROS-/Jetson-Zeitgrenze. Das
Modul liest selbst keine Uhr, kein JSON, keine Karte und keine Datei.

**Nachgewiesenes Verhalten:** Periodischer Status und exaktes Replay erhöhen die
Revision nicht. Normaler Kartenfortschritt sowie ein Sprung über ausgelassene
Zwischenmeldungen behalten denselben Kontext. Neustart mit zurückgesetztem Zähler
wird im alten Korrelator abgewiesen; eine ausdrücklich neue Sitzungs-ID ergibt
auch bei gleichem Anfangsfingerprint einen anderen `PortalMapContext`.
Unvollständige, falsche oder nicht endliche Felder und alle beschriebenen
Widerspruchsfolgen schlagen ohne Änderung des letzten gültigen Kontexts
geschlossen fehl. Ein Korrelationsresultat kann bereits manuell und rein logisch
eine `RegionGraphShadowSession` initialisieren; diese Übergabe ist aber noch
nicht als eigene öffentliche Aggregat-API gekapselt.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2J-MAP | Neue Kartenstatusadapter-Suite: **49 passed**. |
| WE-M2J-EXPLORE | Gesamte Explorer-Suite: **323 passed**. |
| WE-M2J-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **428 passed**. |
| WE-M2J-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut und neues Modul installiert; Pakettest: **323 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2J-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden das Extrahieren aus realem Status-JSON, ROS-Subscription und
QoS, tatsächlicher Kartenmanager-Neustart, ROS-/Wall-Zeitbezug, Jetson-
Laufzeit/Speicher, reale Karten, qualifizierende Portal- oder LiDAR-Evidenz,
Sensorik, Footprint, Kollisionswirkung oder Hardware. Der Korrelator bestätigt
weder Kartenqualität, Portal, Durchfahrt noch Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/K:** `RegionGraphShadowSession` nur über
ein geprüftes erstes `MapStatusCorrelationResult` erzeugbar machen und eine
Statusmethode ergänzen, die weitere Resultate ausschließlich bei exakt gleichem
`PortalMapContext` und nicht rückläufiger `map_revision` annimmt. Das vom
Kartenadapter gelieferte `source_map_age_seconds` wird unverändert übernommen;
Portal-/Graphalter bleiben explizite Aufrufwerte. Kontextwechsel und alte
Resultate müssen ohne Zustandsänderung scheitern. Nur Aggregatmodul, dessen Test
und diese STATUS.md; keine JSON-/ROS-/Explorer-/Launch-/Parameteränderung,
Qualifikation, Navigation oder Fahrwirkung.

**Rückfallweg:** `map_status_adapter.py`, dessen Test und diesen
WE-M2/J-Statusabschnitt entfernen beziehungsweise den gestapelten PR schließen.
WE-M2/A bis I bleiben separat reviewbar; kein Runtime-, Installations- oder
Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/I: ein Besitzer, weiterhin keine Fahr- oder Strukturbefugnis

**Entscheidung / Umfang:** Neu `region_graph_shadow.py` mit
`RegionGraphShadowSession`. Die reine Klasse verlangt einen vollständigen
`PortalMapContext` und einen expliziten `RegionSeed`, startet genau eine bekannte
Region und besitzt intern je ein `PortalMemory`, einen `RegionGraph` sowie eine
`ShadowStatusPolicy`. Portal-, Graph- und Ausgabekapazitäten bleiben die bereits
getrennt getesteten Policies; das Aggregat ersetzt oder lockert sie nicht.

Der einzige Beobachtungseingang akzeptiert `PortalPlanCandidate`, verwendet den
fail-closed Adapter aus WE-M2/H und übergibt dessen festes `INSUFFICIENT` nur an
das Portalgedächtnis. Es gibt absichtlich keinen öffentlichen Zugriff auf die
internen Besitzer und keine Methode für Qualifikation, Portalverbindung,
Erreichbarkeit, Traversal oder Zielerzeugung. Die Startregion ist explizit
betreten; ein Kandidat kann weder eine zweite Region noch einen bestätigten
Eintritt erzeugen.

`status_source()` erzeugt unveränderliche Snapshots und übernimmt aktuelle
Kartenrevision sowie alle drei Alterswerte ausschließlich vom Aufrufer.
`build_status_json()` validiert und serialisiert sie mit der sitzungseigenen
Statuspolicy. Das Modul liest keine Uhr und erzeugt keine fehlenden Werte. Eine
Portalbeobachtung vor der Graph-Startrevision wird zusätzlich abgewiesen; damit
kann ein frisch angelegtes Portalgedächtnis keine ältere, zur Sitzung
widersprüchliche Zeitlinie eröffnen.

**Nachgewiesenes Verhalten:** Der Start erzeugt genau eine Region ohne Verbindung
oder bestätigten Eintritt. Ein normalisierter Kandidat erscheint als ungelöstes
Portal, während Regionszahl, Verbindungen und Eintrittszähler unverändert
bleiben. Exaktes Replay ist idempotent und ergibt bei gleichen Alterswerten
bytegleichen Status. Fremder Sitzungs-/Karten-/Frame-Kontext, Revision vor
Sitzungsstart, neue Revision hinter dem Portalgedächtnis und eine aktuelle
Kartenrevision hinter internem Zustand schlagen ohne Teiländerung geschlossen
fehl. Fehlende Alterswerte bleiben für alle drei Quellen sichtbar `missing`.

Ein Portal-Beobachtungslimit von eins und eine enge Status-Bytegrenze werden vom
Aggregat durchgesetzt. Ein Regionslimit von eins bleibt trotz Portalplan
eingehalten, weil unqualifizierte Beobachtungen keine Gegenregion anlegen.
Zurückgegebene `ShadowStatusSource`-Objekte sind Snapshots und ändern sich bei
späteren Beobachtungen nicht.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2I-SESSION | Neue Aggregat-Suite: **20 passed**. |
| WE-M2I-DIRECT | Aggregat-, Portaladapter- und Statussuiten gemeinsam: **85 passed**. |
| WE-M2I-EXPLORE | Gesamte Explorer-Suite: **274 passed**. |
| WE-M2I-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **379 passed**. |
| WE-M2I-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut und neues Modul installiert; Pakettest: **274 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2I-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden Kartenmanager-Statuskorrelation, echte monotone Uhr und
Quellalter, qualifizierende Struktur-/LiDAR-Evidenz, ROS-QoS/Discovery, Publisher,
Explorer-Lebenszyklus, Jetson-Laufzeit/Speicher, Sensorik, Footprint,
Kollisionswirkung oder Hardware. Reine Sitzungsaggregation bestätigt keine reale
Tür, Durchfahrt oder Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/J:** Ein neues reines Adaptermodul soll ein
explizites Abbild des vorhandenen Kartenmanagerstatus validieren. SHA-256-
Fingerprint, Kartenframe, Quellstempel, nichtnegatives endliches Empfangsalter
und sitzungsbezogenes `accepted_maps` sind getrennt zu führen. Gleicher
Fingerprint darf die Revision nicht erhöhen; Zählerrücklauf, Fingerprintwechsel,
fehlender Status oder Quellstempel aus der Zukunft erzwingt Fehler beziehungsweise
eine explizit neue Kartenepoche, niemals stilles Weiterführen. Synthetische
Statusfolgen einschließlich Replay und Managerneustart prüfen. Keine JSON-/ROS-
Subscription, Datei, Uhr, Explorer-/Launch-/Parameteränderung oder Fahrwirkung.

**Rückfallweg:** `region_graph_shadow.py`, dessen Test und diesen
WE-M2/I-Statusabschnitt entfernen beziehungsweise den gestapelten PR schließen.
WE-M2/A bis H bleiben separat reviewbar; kein Runtime-, Installations- oder
Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/H: Costmap-Portalplan bleibt unqualifizierter Kandidat

**Entscheidung / Umfang:** Neu `portal_plan_adapter.py` als reine
Normalisierungsgrenze. `PortalPlanCandidate` verlangt explizit eine stabile
Beobachtungs-ID, den vollständigen `PortalMapContext`, eine nichtnegative
Kartenrevision, unveränderliche metrische Nah-/Fernseiten sowie eine endliche
nichtnegative Unsicherheit. Die vorhandene `PortalPlan`-Klasse im ROS-Explorer
wird nicht importiert oder verändert; ein späterer Runtime-Aufrufer muss diese
fehlenden Angaben nach belegtem Vertrag liefern und darf sie nicht aus einem
flüchtigen Listenindex ableiten.

`normalize_portal_plan_candidate()` erhält die Richtung `staging_xy` →
`target_xy`, prüft den erwarteten Sitzungs-/Karten-/Frame-Kontext und erzeugt
ausschließlich `PortalStructuralEvidence.INSUFFICIENT`. Die öffentliche Eingabe
besitzt kein Feld, mit dem ein Aufrufer `QUALIFIED` oder `CONTRADICTORY` setzen
könnte. Das Modul führt keinen Zustand und bietet weder Bestätigungs-,
Erreichbarkeits-, Graph-, Ziel- noch Durchfahrtsfunktion.

**Nachgewiesenes Verhalten:** Gleicher Eingang ergibt dieselbe unveränderliche
Beobachtung; ein Replay im `PortalMemory` wird genau einmal gezählt. Zwei passende
Beobachtungen verschiedener Revisionen bleiben trotz geometrischer Zuordnung ein
unbestätigter Kandidat mit null qualifizierten Evidenzen und null bestätigten
Durchfahrten. Die Gegenrichtung bleibt erhalten. Abweichende Sitzung, Karte oder
Frame, fehlende/negative/boolsche Revision, unsichere Kennung, veränderliche oder
falsch dimensionierte XY-Eingabe, `NaN`, Unendlich, negative Unsicherheit und
degenerierte Achse schlagen vor jeder Zustandsänderung geschlossen fehl.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2H-ADAPTER | Neue Adapter-Suite: **23 passed**. |
| WE-M2H-MEMORY | Adapter- und Portalgedächtnis-Suiten gemeinsam: **74 passed**. |
| WE-M2H-EXPLORE | Gesamte Explorer-Suite: **254 passed**. |
| WE-M2H-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **359 passed**. |
| WE-M2H-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut und neues Modul installiert; Pakettest: **254 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2H-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden ein realer `PortalPlan`-Aufrufer, die Herkunft und Güte der
Unsicherheit, qualifizierende Wand-/Rand- oder LiDAR-Evidenz, monotone Quellalter,
ROS-QoS/Discovery, Publisher, Jetson-Laufzeit/Speicher, Sensorik, Footprint,
Kollisionswirkung oder Hardware. Bestandene Tests bestätigen weder eine Tür noch
eine Durchfahrt oder Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/I:** Ein neues reines Aggregatmodul soll
genau einen expliziten Kartenkontext besitzen, normalisierte Beobachtungen an ein
begrenztes `PortalMemory` übergeben, einen getrennten `RegionGraph` halten und
einen `ShadowStatusSource` erzeugen. Unqualifizierte Kandidaten dürfen keine
Graphverbindung und keinen Eintritt erzeugen. Kontextwechsel, Replay, veraltete
Revision, fehlende Alterswerte und feste Kapazitätsgrenzen synthetisch prüfen.
Keine Uhr lesen, keine automatische Strukturqualifikation, keine
ROS-/Explorer-/Launch-/Parameteränderung, kein Publisher, Ziel oder Fahrbefehl.

**Rückfallweg:** `portal_plan_adapter.py`, dessen Test und diesen
WE-M2/H-Statusabschnitt entfernen beziehungsweise den gestapelten PR schließen.
WE-M2/A bis G bleiben separat reviewbar; kein Runtime-, Installations- oder
Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/G: gleiche Revision belegt keine zeitliche Frische

**Entscheidung / Umfang:** `ShadowStatusSource` trägt zusätzlich optionale
Alterswerte in Sekunden für Kartenquelle, Portalgedächtnis und Regionsgraph. Der
Aufrufer muss sie aus derselben monotonen Zeitbasis bilden; die Projektion liest
weiterhin weder Uhr noch ROS-Zeit. `ShadowStatusPolicy` führt für alle drei
Quellen getrennte Obergrenzen. Die Standardwerte von jeweils **2,0 s** sind nur
synthetische Softwarestartwerte für den noch nicht vorhandenen Adapter, keine
gemessenen Jetson-, Sensor- oder Sicherheitsgrenzen.

Der JSON-Quellstatus enthält nun auch `source_map` und für jede Quelle
`age_seconds`. Eine vorhandene Revision ohne Alter ergibt sichtbar `missing`;
Revisions- oder Altersgrenze überschritten ergibt `stale`. Ein Alter ohne
zugehörige Komponentenrevision ist widersprüchlich und wird abgewiesen. Boolean,
negative Werte – einschließlich eines aus der Zukunft stammenden Quellstempels –,
`NaN` und Unendlich schlagen geschlossen fehl. Grenzwerte dürfen null, aber weder
negativ noch nicht endlich sein. Gleichheit mit der Grenze gilt als frisch.

**Nachgewiesenes Verhalten:** Ein synthetischer Stand mit identischen
Karten-, Portal- und Graphrevisionen, aber jeweils 10,0 s Alter wird bei einer
1,0-s-Policy für alle drei Quellen als `stale` ausgewiesen. Fehlende Alterswerte
werden trotz aktueller Revision nicht als frisch ausgegeben. Die drei Grenzen
wirken unabhängig; Revisionsfrische bleibt zusätzlich erforderlich. Kanonisches
JSON, Ausgabegrenzen und die bisherigen Bestands-/Referenzvalidierungen bleiben
erhalten. Außer Tests existiert weiterhin kein Import oder Verbraucher dieses
Moduls.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2G-AGE | Schattenstatus-Suite: **42 passed**, davon 11 neue Alters-/Grenzfälle gegenüber WE-M2/E. |
| WE-M2G-EXPLORE | Gesamte Explorer-Suite: **231 passed**. |
| WE-M2G-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **336 passed**. |
| WE-M2G-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **231 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2G-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Zwei vorangehende reine Testsammlungen ohne vollständig eingeblendete Umgebung
brachen erwartungsgemäß zuerst wegen fehlendem `nav_msgs`, dann wegen fehlendem
`robot_interfaces` ab. Nach explizitem Einblenden von ROS Humble und vorhandenem
Underlay liefen die oben berichteten Suiten grün. Das belegt die weiterhin
bestehende Build-Abhängigkeit, aber keine Runtime- oder Zielsystemabnahme.

Nicht geprüft wurden monotone Uhr und tatsächliche Quellalter im Explorer,
ROS-QoS/Discovery, Publisherrate, Jetson-Laufzeit/Speicher, Sensorik, Footprint,
Kollisionswirkung oder Hardware. Die Softwarestartwerte dürfen nicht als
Messgrenzen in ein Fahrprofil übernommen werden.

**Nächster abgegrenzter Schritt WE-M2/H:** Ein neues reines Adaptermodul soll
einen expliziten, unveränderlichen Portalplan-Eingang mit Kontext, Kartenrevision,
Beobachtungs-ID und Nah-/Fernseite in eine `PortalObservation` überführen. Solange
kein separat belegter frischer Strukturvertrag existiert, muss die Evidenz fest
`INSUFFICIENT` bleiben. Fehlende/ungültige Revision, degenerierte Geometrie,
Replay und fremder Kontext sind synthetisch zu prüfen. Kein Import von
`explore_node`, keine ROS-/Node-/Launch-/Parameteränderung, keine Bestätigung,
kein Durchfahrtsereignis und keine Fahrwirkung.

**Rückfallweg:** Änderungen an `region_graph_status.py`, dessen Test und diesen
WE-M2/G-Statusabschnitt zurücknehmen beziehungsweise den gestapelten PR schließen.
WE-M2/A bis F bleiben separat reviewbar; kein Runtime-, Installations- oder
Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/F: Schattenintegration bleibt getrennt und fail-closed

**Verglichener Stand:** Nach erneutem `git fetch origin` blieb Main auf
`05439c7a13d7a92e69b9eb4663e3a2a1b44626a1`, HWT auf
`1d91229dc10ff4bb791938d49aae8e9808a5dfff`; beide sind ab `9822962` weiterhin
mit 16 nur auf Main und 46 nur auf HWT vorhandenen Commits divergent. Der lokale
Primärbaum blieb auf `feature/modulare-sensorfusion`/`00f6e52` mit den bereits
dokumentierten Änderungen und der nicht eingecheckten Konturstrategie. Er wurde
weder gewechselt noch beschrieben.

**Eingangsentscheidung:** Main liefert `PortalPlan` aus getrennten
Costmap-Komponenten und frischer LiDAR-Prüfung, aber keine stabile Portal-ID,
Strukturevidenz oder Kartenrevision. HWT ergänzt verbundene Engstellen,
Portalpriorität, begrenztes Nachrücken und einen expliziten Übergangszähler,
jedoch ebenfalls keinen WE-M1-Evidenzvertrag. Der lokale Konturstand führt nur
einen flüchtigen `room_index`; er ist weder stabiler Regionsgraph noch
reproduzierbare Integrationsbasis.

Darum gilt fail-closed: Vorhandene Main-/HWT-Portalangebote dürfen ein passives
Gedächtnis zunächst höchstens mit `INSUFFICIENT` speisen. `QUALIFIED` benötigt
einen separat getesteten Adapter mit benannter frischer Geometrie-/LiDAR-Evidenz.
Eine bestätigte Durchfahrt benötigt den getrennten vollständigen
Chassis-/Auslauf-, Pose-, Sensor- und Plausibilitätsvertrag; Nav2-Erfolg,
Portalzähler oder `room_index` allein genügen nicht. WE-M2 erweitert damit keine
Fahrbefugnis und verändert weder Costmap noch Rohkarte.

**Karten- und Frischeentscheidung:** `robot_map_manager` akzeptiert `/map`,
unterdrückt inhaltsgleiche Snapshots anhand SHA-256-Fingerprint und stellt
Fingerprint, Quellstempel, Empfangsalter sowie den sitzungsbezogenen Zähler
`accepted_maps` im Status bereit. Dieser Zähler kann nach Prozessneustart nicht
als dauerhafte Kartenidentität dienen; innerhalb einer expliziten
Schatten-Sitzung ist er aber die kleinste wiederverwendbare Revisionsquelle.
Fingerprint und Quellstempel müssen zur Korrelation sichtbar bleiben. Rücklauf,
fehlender Fingerprint oder Kartenmanager-Neustart erzwingt einen neuen Kontext
beziehungsweise `stale`, niemals stilles Weiterzählen.

WE-M2/E bewertet bisher nur Revisionsabstand. Bleiben Karte und beide abgeleiteten
Stände gemeinsam eingefroren, bleibt dieser Abstand null und würde fälschlich
frisch aussehen. Vor einem Publisher muss der reine Vertrag deshalb zusätzlich
extern gemessene monotone Alterswerte führen; die Projektionsfunktion liest auch
dann selbst keine Uhr.

**Ausgabe- und Besitzerentscheidung:** `/explore/status_json` bleibt unverändert.
iOS verlangt dort ein vollständiges Schema 1 und verwendet Frische sowie
`backend_ready` zur Startfreigabe; Web prüft dieselben Felder und zeigt
`map_ready_to_save`. Ein Schattenstatus auf diesem Topic könnte abgelehnt oder
mit Fahrbereitschaft verwechselt werden. Mission, Navigation, LLM und Gesicht
haben laut Quellsuche keinen direkten Verbraucher dieses Explorerstatus; die
bestehenden App-Verbraucher sind dennoch verbindlich.

Die spätere Ausgabe erhält daher ausschließlich
`/explore/region_graph/status_json` als `std_msgs/msg/String`, QoS Keep-last 1,
reliable und transient-local, maximal 1 Hz sowie bei relevanter Zustandsänderung
zusammengefasst. Sie bleibt mit `region_graph_shadow_enabled: false`
standardmäßig aus. Der Schattenzustand soll nach geklärter Runtime-Basis im
bestehenden Explorerprozess leben: Dort liegen Detektor- und
Durchfahrtsentscheidungen bereits vor, ohne zweiten Karten-, Nav2- oder
Motorbesitzer. Marker, App-Abonnement und Abschlusslogik bleiben getrennte
Folgeschritte.

**Ausgeführte Prüfungen:** Ausschließlich Quell-/Konfigurationsvergleich und
Python-Tests, ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2F-STACK | Gestapelter WE-M2/E-Explorerstand: **220 passed**. |
| WE-M2F-HWT | Sauberer HWT-Explorerstand `1d91229`: **80 passed**. |
| WE-M2F-LOCAL | Lokal veränderter Primär-Explorerstand: **67 passed**. |
| WE-M2F-APP-MOCK | Python-Tests des iOS-rosbridge-Mocks: **7 passed**. |
| WE-M2F-STATIC | `git diff --check`: bestanden. |

Swift-/Xcode-Tests, Browser-Lauf, ROS-QoS/Discovery, Publisherrate,
Kartenmanager-Neustart, Jetson-Ressourcen, Sensorik, Footprint und Hardware
wurden nicht ausgeführt. Grüne Quelltests belegen keine zulässige
Strukturevidenz, reale Durchfahrt oder Hardwareabnahme.

**Offene Abhängigkeiten:** Die funktionale Runtime-Basis bleibt zwischen Main,
HWT und lokalem Konturstand ungeklärt; kein Gesamtmerge ist freigegeben. Der
Kartenmanagerstatus ist asynchron zum Explorer-Map-Callback und braucht einen
expliziten Korrelations-/Neustartvertrag. Schwellen für monotones Alter,
Publisherbudget und `QUALIFIED`-Evidenz sind noch nicht gemessen. Ohne diese
Punkte darf der Schattenstatus weder `fresh` noch einen Eintritt erfinden.

**Nächster abgegrenzter Schritt WE-M2/G:** Nur
`region_graph_status.py`, `test_region_graph_status.py` und diese STATUS.md.
Nichtnegative endliche, vom späteren Adapter gelieferte monotone Alterswerte für
Kartenquelle, Portalgedächtnis und Regionsgraph in die Frischeentscheidung
aufnehmen. Fehlend, zu alt, inkonsistent oder zeitlich zurücklaufend muss sichtbar
`missing`/`stale` oder fail-closed werden; eine eingefrorene Karte bei
Revisionsgleichstand synthetisch testen. Grenzwerte ausdrücklich als
Softwarestartwerte kennzeichnen. Noch kein ROS-, Node-, Launch-, Parameter-,
Ziel- oder Fahrsoftwareeingriff.

**Rückfallweg:** Nur diesen WE-M2/F-Statusabschnitt beziehungsweise den
Dokumentations-PR zurücknehmen. WE-M2/A bis E bleiben separat reviewbar; es gibt
keine Runtime-, Installations- oder Geräteänderung zurückzusetzen.

### 2026-09-14 – WE-M2/E: begrenzter Schattenstatus ohne Publisher

**Entscheidung / Umfang:** Neu `region_graph_status.py` als reine
Standardbibliotheks-Projektion. Ein `ShadowStatusSource` übernimmt den expliziten
Portal-/Kartenkontext, die aktuelle externe Kartenrevision, die letzte
Portalgedächtnisrevision sowie unveränderliche Portal-, seitenspezifische
Erreichbarkeits- und Regionsgraph-Snapshots. `build_shadow_status_json()` erzeugt
kanonisches kompaktes JSON mit `schema_version: 1`, `mode: shadow` und
`passive: true`. Das Modul liest keine Karte, Uhr, Datei oder ROS-Schnittstelle
und publiziert nichts.

**Nachgewiesenes Verhalten:** Gleicher Inhalt ergibt unabhängig von der
Eingabereihenfolge bytegleiches JSON. Portalgeometrie (`x`, `y`, metrische Seiten)
wird nicht ausgegeben. Enthalten sind Kontext, aktuelle Kartenrevision, getrennte
Portal-/Graphrevision samt Abstand in Revisionen und `fresh`/`stale`/`missing`,
aktuelle Region, Regionen, Portalverbindungen, Aliasbezug, vollständiger
Aufgabenbestand, Bestätigungs-/Eintrittszähler sowie unbekannte oder vorübergehend
blockierte Portalseiten. Fehlende Quellen gelten nicht als frisch.

Der Projektor prüft vor Ausgabe Kontextgleichheit, aktuelle und nicht zukünftige
Revisionen, eindeutige IDs, beide Erreichbarkeitsseiten jedes Portals,
Verbindungs-/Regions-/Aufgabenreferenzen und die zugehörigen Zähler. Harte Grenzen
für alle Bestände und die serialisierte Bytezahl verhindern unbeschränkte
Ausgabe. Widerspruch, Lücke oder Grenzüberschreitung bricht geschlossen ab.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Umgebung,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2E-STATUS | Neue Schattenstatus-Suite: **31 passed**. |
| WE-M2E-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **325 passed**. |
| WE-M2E-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **220 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2E-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Der zusätzliche Lauf einschließlich des bereits in Abschnitt 5 abgegrenzten
VL53-Vertragstests ergab **327 bestanden, 1 fehlgeschlagen**; Fehlerbild und
betroffene unveränderte Dateien entsprechen WE-M2/C und werden hier nicht
angepasst. Der Colcon-Aufbau überschreibt keine Arbeitsinstallation und nutzt
`robot_interfaces` aus dem vorhandenen Underlay. Nicht geprüft wurden ROS-QoS,
Publisher, Statusverbraucher, echte Datenfrische, Laufzeit/Speicher auf dem
Jetson, Sensorik, Footprint, Kollisionswirkung oder Hardware.

**Offene Risiken / Integrationsabhängigkeiten:** `PortalSnapshot` selbst trägt
keinen Kontext; der Aufrufer muss deshalb belegen, dass die zusammen übergebenen
Portal- und Erreichbarkeitssnapshots zum deklarierten Kontext gehören. Die
Revisionsabstandsgrenze `1` ist nur ein synthetischer Softwarestartwert, keine
gemessene Laufzeit-Frische. Eingangsadapter, Zustandsbesitzer, Aktualisierungsrate,
Topic/QoS, vorhandene `/explore/status_json`-Verbraucher und Jetson-Budget sind
noch nicht festgelegt. Das JSON ist weder Abschlussurteil noch Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/F:** Nur Bestands- und
Integrationsentscheidung in dieser STATUS.md. Aktuellen Main-, HWT- und lokalen
Explorerstand sowie iOS/Web-/Missionsverbraucher prüfen. Festlegen, welche
bestehenden Detektorausgaben ohne erfundene Strukturevidenz als normalisierte
Eingänge dienen dürfen, wo der sitzungsgebundene Schattenzustand lebt, wie ein
neues Topic benannt und mit welchem QoS/Rate-/Speicherbudget standardmäßig
deaktiviert vorbereitet wird. Noch keine Node-, Launch-, Parameter-, Ziel- oder
Fahrsoftware ändern. Erst der danach eindeutig abgegrenzte PR darf die passive
Publisher-Hülle umsetzen.

**Rückfallweg:** Die zwei neuen WE-M2/E-Dateien und diesen Statusabschnitt
entfernen beziehungsweise den gestapelten Review-PR zurücknehmen. WE-M2/A bis D
und WE-M1 bleiben separat reviewbar. Da kein Runtime-Pfad das neue Modul importiert,
gibt es keine Runtime- oder Geräteänderung zurückzusetzen.

### 2026-09-14 – WE-M2/D: Regionsteilung ordnet alle Referenzen explizit zu

**Entscheidung / Umfang:** `region_graph.py` ausschließlich um einen begrenzten,
idempotenten `RegionSplit`-Vertrag ergänzt. Die kanonische Ausgangs-ID bleibt als
eine Ergebnisregion erhalten, genau eine neue ID wird deterministisch erzeugt.
Der Auftrag nennt für jede Seite A/B jeder betroffenen Portalverbindung und jede
Aufgaben-ID eindeutig `retained` oder `created`. Er leitet keine Teilung aus
Karte, Sensorik oder Geometrie ab.

Gesehen, betreten und Eintrittszähler werden als unteilbarer historischer Zustand
konservativ genau dem explizit gewählten `state_target` zugewiesen; dadurch werden
Belege und Zähler weder erfunden noch verdoppelt. War die Ausgangsregion aktuell,
folgt die aktuelle Region demselben Ziel. Historische Alias-IDs bleiben bei der
beibehaltenen ID, weil eine einzelne alte ID nicht mehrdeutig auf zwei Regionen
auflösbar sein darf.

**Nachgewiesenes Verhalten:** Portalenden – einschließlich beider Seiten einer
internen Verbindung – und Aufgaben werden ohne Verlust auf beide Ergebnisse
verteilt. Alte Portalbeobachtungs-, Durchfahrts- und Aufgaben-Replays liefern die
nach der Teilung aktuelle Zuordnung, ohne Zustand erneut zu verändern. Ein
anschließender expliziter Merge vereinigt beide Ergebnisse wieder ohne verlorene
Portale oder Aufgaben. Exakte Split-Replays sind idempotent und normalisieren
später vereinigte IDs.

Unvollständige, doppelte oder fremde Portal-/Aufgabenzuordnungen,
widersprüchliche Split-IDs, fremder Kontext, unbekannte Ausgangsregion,
veraltete Revision sowie feste Regions- und Verlaufsgrenzen schlagen vor der
ersten Änderung geschlossen fehl. Die Eingabetupel werden kanonisch sortiert,
damit ihre Reihenfolge keine zweite Operation erzeugt.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Umgebung,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2D-GRAPH | Regionsgraph-Suite: **80 passed**, einschließlich 28 neuer Split-/Replay-/Negativfälle. |
| WE-M2D-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **294 passed**. |
| WE-M2D-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **189 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2D-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Der zusätzliche Lauf einschließlich des bereits in Abschnitt 5 abgegrenzten
VL53-Vertragstests ergab **296 bestanden, 1 fehlgeschlagen**; Fehlerbild und
betroffene unveränderte Dateien entsprechen WE-M2/C. Der Colcon-Aufbau
überschreibt keine Arbeitsinstallation und nutzt `robot_interfaces` aus dem
vorhandenen Underlay. Nicht geprüft wurden reale Segmentierung oder Korrekturen,
ROS-QoS/TF, Laufzeitlast, Sensorik, Footprint, Kollisionswirkung oder Hardware.

**Offene Risiken / Integrationsabhängigkeiten:** Teilungsgrund und komplette
Zuordnung sind externe Eingaben; ein Detektor oder geometrischer Beleg fehlt
bewusst. Der konservative unteilbare Zustand kann historische Eintritte nicht auf
beide Ergebnisse verteilen, weil der bisherige Graph keine ortsgebundenen
Eintrittsbelege besitzt. Eine falsche externe Zuordnung bleibt logisch konsistent,
ist aber keine belegte reale Raumkorrektur. Statusschema, Datenfrische,
Schattenausgabe, Kartenursprungs-/Rotationsadapter und Ressourcenmessung fehlen.

**Nächster abgegrenzter Schritt WE-M2/E:** Neu nur ein reines
Statusprojektionsmodul, dessen Tests und diese STATUS.md. Einen versionierten,
begrenzten und deterministischen Schattenstatus aus vorhandenen unveränderlichen
Portal-/Graphsnapshots bilden. Kontext, Quell-/Graphrevision, explizite
Frischebewertung, aktuelle Region, Verbindungs- und Aufgabenbestand sowie
ungelöste/unsichere Zustände ausweisen. Noch keine ROS-Node-Änderung,
Marker-Geometrie, Zielauswahl, Navigation oder Fahrwirkung; die spätere
Publisher-Einbindung bleibt ein eigener Schritt.

**Rückfallweg:** Den WE-M2/D-Commit beziehungsweise den gestapelten Review-PR
zurücknehmen. WE-M2/A bis C und WE-M1 bleiben separat reviewbar. Da kein
Runtime-Pfad den Regionsgraph importiert, gibt es keine Runtime- oder
Geräteänderung zurückzusetzen.

### 2026-09-14 – WE-M2/C: Aufgabenreferenzen bleiben bei Merge stabil

**Entscheidung / Umfang:** `region_graph.py` ausschließlich um einen begrenzten,
idempotenten Bestand passiver `RegionTaskUpdate`-Eingaben ergänzt. Jede stabile
Aufgaben-ID bindet genau einen opaken Gegenstand der Art `frontier`, `portal` oder
`observation` an eine kanonische Region und führt Erzeugungs- sowie letzte
Aktualisierungsrevision. Der Zustand unterscheidet nur `open` und `completed`.
Das Modul bewertet, priorisiert oder startet Aufgaben nicht und erzeugt keine
Ziele oder Bewegungsfreigaben.

**Nachgewiesenes Verhalten:** Erzeugung, zustandsunveränderte Aktualisierung und
Abschluss sind revisionsgebunden. Exakte Update-Replays bleiben idempotent;
widersprüchliche Update-IDs, Identitätswechsel, Umzug in eine nicht vereinigte
Region, veraltete Revisionen, unbekannte Regionen, fremde Kontexte,
Wiederöffnung abgeschlossener Aufgaben und feste Speichergrenzen schlagen vor
einer Teiländerung geschlossen fehl. Filter und Snapshots sind deterministisch.
Eine Regionsvereinigung übernimmt offene und abgeschlossene Aufgaben ohne
Verlust, schreibt deren Bezug auf die kanonische Region um und akzeptiert danach
sowohl alte Alias-IDs als auch das Replay eines vor dem Merge erzeugten Updates.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Umgebung,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2C-GRAPH | Regionsgraph-Suite: **52 passed**, einschließlich Aufgaben-/Merge-/Alias- und Negativfällen. |
| WE-M2C-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **266 passed**. |
| WE-M2C-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **161 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2C-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Der Colcon-Aufbau überschreibt keine Arbeitsinstallation und nutzt
`robot_interfaces` aus dem vorhandenen Underlay; er ist kein vollständiger
Workspace- oder Zielsystemnachweis. Der zusätzliche Nahbereichslauf mit einem
unabhängigen, geerbten Vertragsfehler ist in Abschnitt 5 getrennt dokumentiert.
Nicht geprüft wurden reale Aufgaben, Ausführungsreihenfolge, ROS-QoS/TF,
Laufzeitlast, Sensorik, Footprint, Kollisionswirkung oder Hardware.

**Offene Risiken / Integrationsabhängigkeiten:** Aufgaben-ID, Gegenstand,
Regionszuordnung und Abschlussurteil sind externe Eingaben; ihre Adapter und
Evidenzquellen fehlen bewusst. Abgeschlossene Aufgaben werden in diesem kleinen
Schritt nicht reaktiviert. Priorität, Retry-/Blacklistlogik, Zielkoordinaten,
Abhängigkeiten und Persistenz sind nicht Teil des Modells. Eine Region kann noch
nicht kontrolliert geteilt werden; dadurch ist noch nicht gezeigt, dass alle
Referenzen auch nach einer späteren Korrektur zu grober Segmentierung erhalten
bleiben. Keine grüne Prüfung belegt eine reale Aufgabe oder Region.

**Nächster abgegrenzter Schritt WE-M2/D:** Nur `region_graph.py`, dessen Tests
und diese STATUS.md ändern. Eine explizite Regionsteilung muss zwei stabile
Ergebnisregionen bilden und Portalenden sowie sämtliche Aufgabenreferenzen der
Ausgangsregion vollständig und eindeutig zuweisen. Gesehen/betreten,
Eintrittszähler, aktuelle Region, Verbindungen, IDs und Aliasauflösung müssen
deterministisch erhalten beziehungsweise nach dokumentierter Vorgabe verteilt
werden. Unvollständige, doppelte, veraltete oder widersprüchliche Aufträge
schlagen atomar fehl. Noch keine automatische Teilungsentscheidung,
Geometrieschwelle, Detektoranbindung, ROS-Ausgabe oder Navigation.

**Rückfallweg:** Den WE-M2/C-Commit beziehungsweise den gestapelten Review-PR
zurücknehmen. WE-M2/A und B sowie WE-M1 bleiben separat reviewbar. Da kein
Runtime-Pfad den Regionsgraph importiert, gibt es keine Runtime- oder
Geräteänderung zurückzusetzen.

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
