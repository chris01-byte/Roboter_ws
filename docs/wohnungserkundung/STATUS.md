# Wohnungserkundung – laufender Status und Entscheidungen

**Vorhaben WE-1 · Aktualisiert: 2026-09-14 (WE-M3/F)**

Dies ist der einzige laufende Fortschrittsstand des Vorhabens. Die
[Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) beschreibt das Soll,
die [Roadmap](MEILENSTEINE.md) die Abnahmen und der
[Agentenauftrag](AGENTENAUFTRAG.md) den Arbeitsablauf. Historische Logs bleiben
Quellen, aber ersetzen diesen statusbezogenen Einstieg nicht.

## 1. Aktueller nächster Schritt

**WE-M3/F – Der erste passive Runtimeadapter ist standardmäßig deaktiviert,
gerätefrei durchgängig geprüft und zur Review.** Bei explizitem Opt-in bewertet
er atomar genau den typisierten Snapshot des vorhandenen Regionsgraph-Schatten
und hängt eine begrenzte, versionierte `wohnungserkundung`-Diagnose an den
Legacy-Status. Ohne Opt-in bleibt dessen Payload unverändert. Mangels
Aufgabenverfügbarkeitsbelegen bleibt jede offene Aufgabe unbekannt und der
Abschluss immer gesperrt; Zielwahl und Fahrpfade lesen den neuen Zustand nicht.

WE-M2 bleibt formal offen: Sein gerätefreier Softwareumfang einschließlich
wachsenden Langlaufs ist umgesetzt und lokal geprüft. Ein Durchfahrtsurteil
kann atomar Portalgedächtnis, aktuelle Region und Portalaufgabe fortschreiben,
wird aber absichtlich nur als bereits extern validierter Eingang akzeptiert.
Der vorhandene Fahrpfad liefert noch keinen vollständigen Chassis-/Auslaufbeleg
und ist nicht angebunden. Reale Parallel-/SLAM-Last, Jetson-Nachtest und
Hardwareabnahme fehlen; der Offline-Langlauf ersetzt diese Nachweise nicht.
WE-M3 bleibt ebenfalls offen: M3/A bis F umfassen Logik, Migrationsvertrag und
die erste rein diagnostische Runtimeprojektion. Echte revisionsgebundene
Verfügbarkeits-/Wegkostenbelege, zustandsbehaftete Auswahl, Zielbildung und
-übergabe, Abschluss-/Actionintegration, eingefrorenes begrenztes Profil sowie
die motorlose Zielsystemabnahme fehlen.

**Nächster abgegrenzter Schritt WE-M3/G:** Die fehlende Belegnaht ohne
Zielübergabe ergänzen: aus exakt derselben korrelierten Rohkarte, dem vollständigen
Frontierbestand und einem expliziten Roboterbezug revisionsgebundene
Aufgabenverfügbarkeit, geodätische Weglänge und Informationsgewinn ableiten.
Fehlende Karte/Pose, nicht auflösbare Aufgaben, Planungsfehler und veraltete
Revisionen müssen als unbekannt beziehungsweise blockiert sichtbar bleiben.
Zunächst nur reine Adapter-/Szenariotests und passive Statusdiagnose; keine
Action-, Nav2-Ziel-, Command- oder Twist-Wirkung.

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
| WE-M2/M `feature/we-m2m-shadow-lifecycle` | Gestapelter reiner Lebenszyklusbesitzer für Decoder, Kartenkorrelator und genau eine Schatten-Sitzung; neues Modul, Tests und Status. |
| WE-M2/N `feature/we-m2n-shadow-monotonic-age` | Gestapelte explizite monotone Eingangszeit und daraus abgeleitetes Graphalter im reinen Lebenszyklus; Modul, Tests und Status. |
| WE-M2/O `feature/we-m2o-shadow-portal-feed` | Gestapelte unqualifizierte Portalplan-Zuführung mit replayfestem Portalalter im reinen Lebenszyklus; Modul, Tests und Status. |
| WE-M2/P `docs/we-m2p-shadow-runtime-seam` | Gestapelte quellenbasierte Festlegung der ersten passiven ROS-Naht einschließlich gesperrter Portal-Provenienz; nur diese STATUS.md. |
| WE-M2/Q `feature/we-m2q-shadow-map-runtime` | Gestapelte, standardmäßig deaktivierte und kartenstatusbasierte ROS-Schattenhülle; Explorer-Node, Standardparameter, Vertragstests und Status. |
| WE-M2/R `feature/we-m2r-shadow-map-age` | Gestapelte reine monotone Fortführung des Kartenquellalters mit replayfestem Empfangsanker; Lebenszyklus, Tests und Status. |
| WE-M2/S `docs/we-m2s-acceptance-matrix` | Gestapelte vollständige Zuordnung der WE-M2-Lieferung, Pflichttests und Abnahme zu konkreten Nachweisen oder Lücken; nur diese STATUS.md. |
| WE-M2/T `feature/we-m2t-region-exploration-state` | Gestapelter expliziter Regions-Erkundungsstatus mit konservativer Merge-/Split-Behandlung und passiver Statusprojektion; Graph, Tests und Status, kein Deployment. |
| WE-M2/U `docs/we-m2u-portal-provenance` | Gestapelte Quellenentscheidung zur fehlenden Rohkartenlinie der Nav2-Master-Costmap und zum fail-closed Korrelationsvertrag; nur diese STATUS.md. |
| WE-M2/V `feature/we-m2v-raw-map-source` | Gestapelter reiner Exaktabgleich von Rohkartenfingerprint, -stempel und Frame gegen den aktuellen Kartenmanagerstand; neues Modul, Tests und Status, kein Deployment. |
| WE-M2/W `docs/we-m2w-map-identity-dependency` | Gestapelte Abhängigkeitsentscheidung gegen den zyklischen Direktimport des Kartenmanagers und für eine neutrale Fingerprintquelle; nur diese STATUS.md. |
| WE-M2/X `feature/we-m2x-shared-map-identity` | Gestapelte gemeinsame ROS-freie Fingerprintquelle für Kartenmanager und Explorer mit bytegleichen Vektoren und azyklischem Paketgraphen; kein Deployment. |
| WE-M2/Y `docs/we-m2y-raw-map-runtime-seam` | Gestapelte Quellen- und Nebenläufigkeitsentscheidung zur passiven Rohkartennaht mit lokaler synthetischer Typ-/Kostenmessung; nur diese STATUS.md, kein Deployment. |
| WE-M2/Z `feature/we-m2z-shared-cell-normalization` | Gestapelte gemeinsame ROS-freie, begrenzte Zellnormalisierung für Kartenmanager und Explorer; reine Module, Tests, Inventar und Status, kein Deployment. |
| WE-M2/AA `feature/we-m2aa-raw-map-status-join` | Gestapelter reiner, explizit begrenzter und beidseitig anstoßbarer Exaktjoin von Rohkartenidentität und Kartenmanagerstatus; Adapter, Tests und Status, kein Deployment. |
| WE-M2/AB `docs/we-m2ab-raw-map-runtime-owner` | Gestapelte Besitzer-, Opt-in-, Diagnose- und Messentscheidung für die spätere passive Runtime; nur diese STATUS.md, kein Deployment. |
| WE-M2/AC `feature/we-m2ac-lifecycle-raw-map-owner` | Gestapelter optionaler Joiner-Besitz im reinen Schattenlebenszyklus mit begrenzten Diagnosezählern und beidseitigen Übergaben; reine Module, Tests und Status, kein Deployment. |
| WE-M2/AD `feature/we-m2ad-raw-map-status-diagnostics` | Gestapelte optionale, begrenzte Rohkarten-Korrelationsdiagnose im getrennten reinen Schattenstatus; reine Module, Tests und Status, kein Deployment. |
| WE-M2/AE `feature/we-m2ae-passive-raw-map-runtime` | Gestapelter doppelt opt-in passiver Rohkartenadapter im Explorer mit gemeinsamer Identität, isoliertem Schattenfehler und getrennten Diagnosen; Node, Standardparameter, Tests und Status, kein Deployment. |
| WE-M2/AF `docs/we-m2af-raw-map-load-probe-plan` | Gestapelte Quellen-, Sicherheits-, Mess- und Schnittstellenentscheidung für genau einen gerätefreien synthetischen Rohkarten-Lastprüfer; nur diese STATUS.md. |
| WE-M2/AG `chore/we-m2ag-raw-map-load-probe` | Gestapelter gerätefreier synthetischer DDS-Prüfer für Wire-Digest, Exaktjoin, begrenzte Kapazität/Laufzeit/Ausgabe und Explorer-RSS samt reinen Tests und Status; kein Deployment. |
| WE-M2/AH `docs/we-m2ah-region-scenario-fixtures` | Gestapelte Abdeckungs- und Nahtinventur der WE-M2-Szenarien mit exakt abgegrenzter reiner HWT-Detektorabhängigkeit; nur diese STATUS.md. |
| WE-M2/AI `feature/we-m2ai-connected-portal-detector` | Gestapelte, ausdrücklich freigegebene Übernahme nur des reinen HWT-Detektors für Türen in verbundenem Freiraum samt vier Tests; kein Runtime-Aufrufer oder Deployment. |
| WE-M2/AJ `feature/we-m2aj-room-hall-scenario` | Gestapeltes reines Kombinationsszenario von Rastergeometrie bis Regionsgraph für Startraum–Flur–Zimmer, Wahrheitsgrenzen, Aufgabenbezug und identische Flurrückkehr; nur Tests und Status. |
| WE-M2/AK `feature/we-m2ak-negative-region-scenarios` | Gestapelte reine Kombinations-Negativfälle für offenen Wohnbereich und Möbelunterteilung; Kandidat/Strukturwahrheit, Graph und Aufgaben bleiben getrennt, nur Tests und Status. |
| WE-M2/AL `feature/we-m2al-l-hall-loop-scenario` | Gestapeltes reines L-Flur-/Schleifenszenario mit Detektorportalen und ausdrücklich separater Merge-Wahrheit; nur Tests und Status. |
| WE-M2/AM `feature/we-m2am-map-change-scenario` | Gestapeltes reines Kartenänderungsszenario für Wachstum, Origin-/Rasterrotation und explizite Merge-/Split-Korrektur ohne Identitäts- oder Aufgabenverlust; nur Tests und Status. |
| WE-M2/AN `docs/we-m2an-runtime-feed-seam` | Gestapelte erneute Runtime-Nahtinventur nach Abschluss der kombinierten Szenarien; legt den fehlenden reinen Rohkarten-Kandidatenadapter als nächste Voraussetzung fest, nur diese STATUS.md. |
| WE-M2/AO `feature/we-m2ao-correlated-raw-map-portals` | Gestapelter ROS-freier Adapter von exakt korrelierten Rohkartenzellen zu stabilen unqualifizierten verbundenen Portalkandidaten samt reinen Verträgen; kein Runtime-Aufrufer. |
| WE-M2/AP `docs/we-m2ap-passive-portal-feed-owner` | Gestapelter Besitzer-, Cache-, Retry-, Sperr- und Fehlervertrag für die spätere dritte Opt-in-Portalzuführung; nur diese STATUS.md. |
| WE-M2/AQ `feature/we-m2aq-passive-connected-portal-feed` | Gestapelte dritt-opt-in passive Node-Zuführung exakt korrelierter Rohkarten-Portalkandidaten mit begrenztem Pose-Retry, Sperrdisziplin, Fehlerisolation und gerätefreiem ROS-Smoke; keine Qualifikation, Graphverbindung oder Fahrwirkung. |
| WE-M2/AR `feature/we-m2ar-automatic-shadow-events` | Gestapelte dritt-opt-in Kette von exakt korrelierter Rohkarte über topologischen Strukturbeleg und revisionsgebundene Portalbestätigung bis zu vorläufiger Region, Verbindung und passiven Beobachtungs-/Portalaufgaben; validierte Traversalschnittstelle ohne Fahrpfadanbindung. |
| WE-M2/AS `feature/we-m2as-passive-frontier-tasks` | Gestapelte unabhängige Opt-in-Zuführung aller ungefilterten Rohkarten-Frontiers in sitzungsstabile offene Graphaufgaben; eindeutige Assoziation, mehrdeutige Zusatzaufgabe, Replay-/Kapazitätsgrenzen und kein Abschluss durch Verschwinden oder Filter. |
| WE-M2/AT `chore/we-m2at-passive-chain-load-probe` | Gestapelter gerätefreier Offline-Langläufer für Exaktjoin, Frontier-/Portalereignisse, Regionen und Aufgaben über wachsende synthetische Karten; bytegleiche Eingangsprüfung, Zeit-/Prozess-RSS-Messung und atomarer Kapazitätsfall. |
| WE-M3/A `feature/we-m3a-policy-contract` | Gestapelter ROS-freier Policyvertrag auf vollständigen passiven Snapshots; revisionsgebundene Aufgabenverfügbarkeit, Quellen-/Erreichbarkeitsblocker, Regionskontinuität und ausschließlich nichtterminale Ergebnisse ohne Ziel- oder Fahrwirkung. |
| WE-M3/B `feature/we-m3b-task-history` | Gestapelter begrenzter, revisionsgetriebener Aufgabenverlauf mit Alter, Auswahl-/Versuchshistorie, Retryverzögerung/-budget, expliziter Reaktivierung, Regionshaltezeit und Anti-Verhungerungsrotation; nur Aufgaben-ID, keine Fahrwirkung. |
| WE-M3/C `feature/we-m3c-task-scoring` | Gestapelte revisionsgebundene skalare Bewertung geeigneter Aufgaben-IDs aus geodätischer Weglänge in Metern und Informationsgewinn in Quadratmetern; explizite Normierung/Gewichte, vollständige Belege und deterministische Gleichstände ohne Pfad-/Zielausgabe. |
| WE-M3/D `feature/we-m3d-completion-contract` | Gestapelter reiner Abschlussautomat mit drei frischen qualifizierten Revisionen, Reset bei Blockade, getrennten Voll-/Teil-/System-/Nutzerzuständen und unabhängigen Speicher-/Rückkehrergebnissen; keine Runtime- oder Fahrwirkung. |
| WE-M3/E `feature/we-m3e-consumer-migration` | Gestapelte quellenbasierte Verbraucher-/ABI-Inventur und reine additive Abbildung von WE-Ergebnissen auf unveränderte Legacy-Action-/Statuszustände; versionierte verschachtelte Statuserweiterung, keine Runtimewirkung. |
| WE-M3/F `feature/we-m3f-passive-runtime-status` | Gestapelter standardmäßig deaktivierter Runtimeadapter vom atomaren typisierten Schattensnapshot zur begrenzten versionierten `wohnungserkundung`-Diagnose im Legacy-Status; ohne Verfügbarkeitsbeleg kein geeignetes Ziel und stets gesperrter Abschluss. |

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
| WE-M2 | Softwareumfang lokal geprüft; formale Abnahme offen | WE-M2/A bis AT decken reine Topologie, Korrekturen, Aufgabenbezug, Statusprojektion, Integrationsgrenzen und -adapter, Zeitfrische, Sitzungslebenszyklus, passive Kartenstatus-/Rohkarten-ROS-Hüllen, sämtliche Geometrieszenarien, automatisch korrelierte Struktur-/Frontierereignisse und den wachsenden Kettenlanglauf ab. Vollständige Bewegungsbelegquelle, reale Parallel-/SLAM-Last, Zielsystem- und Hardwareabnahme bleiben offen. |
| WE-M3 | Begonnen; M3/A bis F softwaregeprüft | Vertrag, Aufgabenverlauf, skalare Bewertung, Abschlussautomat, additive Migration und passiver Status-Runtimepfad liegen vor. Belegzuführung, Auswahl-/Zielintegration, Abschlussruntime, begrenztes Profil und motorlose Zielsystemabnahme fehlen. |
| WE-M4 | Geplant | Arbeitszimmer → Flur → weiteres Zimmer → derselbe Flur. |
| WE-M5 | Geplant | Versionsgebundene Persistenz und sichere Wiederaufnahme. |
| WE-M6 | Geplant | Wiederholbarer Abschluss des zugänglichen Wohnungsumfangs. |
| WE-M7 | Geplant, ergänzend | App-Transparenz und manuelle Benennung. |

## 5. Bekannte offene Punkte

**Codebasis:** Main und HWT-Erprobungszweig bleiben divergent. Der HWT-Zweig
ändert unter `src/explore/` elf Dateien gegenüber Main (unter anderem 670
Zeilen im Node), der lokale Primärbaum nochmals drei Explorerdateien und eine
nicht eingecheckte strukturierte Strategie. Die gestapelte WE-Reihe verändert
den bestehenden `explore_node.py` dagegen nicht und bleibt deshalb die einzige
reproduzierbare Reviewbasis für die passive Hülle; sie ist weder Deployment-
noch HWT-Integrationsfreigabe. Vor einer späteren funktionalen Einbindung sind
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
den tatsächlichen Statusumschlag rein und begrenzt. WE-M2/M besitzt daraus genau
eine Sitzung und verweigert automatische Epochenübernahme. WE-M2/N leitet das
Graphalter aus expliziten monotonen Zeitpunkten ab. WE-M2/O führt unqualifizierte
Portalpläne mit replayfestem Portalalter zu. WE-M2/P legt die erste passive
ROS-Naht fest, weist aber zugleich nach, dass `PortalPlan` aus der
Nav2-Global-Costmap nicht belastbar einer Kartenmanagerrevision zugeordnet
werden kann. WE-M2/Q bindet ausschließlich den Kartenstatus passiv und
standardmäßig deaktiviert an; Portalzuführung und qualifizierte Evidenz bleiben
offen. WE-M2/R führt das Kartenquellalter monoton fort. Die Matrix aus WE-M2/S
weist außerdem den fehlenden eigenen Regions-Erkundungsstatus, noch nicht
kombinierte Geometrieszenarien und fehlende Runtime-/Belastungsnachweise aus.

**Statusfrische:** Der Kartenmanager publiziert seinen Status standardmäßig
alle 2,0 s, während der reine Schattenvertrag Kartenquellen nach mehr als 2,0 s
als veraltet bewertet. Gleichheit der Grenzwerte lässt keinen Spielraum für
Scheduling und Transport. Der WE-M2/Q-Smoke-Test belegt Discovery und Ausgabe,
nicht diese Frischegrenze. WE-M2/R schreibt das vom letzten neuen
Kartenmanagerumschlag übernommene Kartenalter nun zwischen den Eingängen monoton
fort; ein exaktes Replay verjüngt es nicht. Der echte 2,0-s-Grenzfall unter
Managerperiodik und Scheduling bleibt dennoch ungemessen.

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

### 2026-09-14 – WE-M3/F: passiver Runtime- und Statusadapter

**Arbeitsbasis und Umfang:** `feature/we-m3f-passive-runtime-status` baut direkt
auf M3/E `d7dbcd1` auf. `RegionGraphShadowLifecycle.build_status()` liefert nun
atomar den unveränderlichen typisierten Snapshot und dessen weiterhin
bytebegrenzte kanonische Schattenprojektion; die bestehende
`build_status_json()`-Schnittstelle bleibt kompatibel. Erst der neue Parameter
`wohnungserkundung_policy_enabled`, standardmäßig `false`, lässt den Explorer
diesen Snapshot mit dem M3/A-Vertrag bewerten. Die Policyarbeit läuft nach
Freigabe der Schatten-Sperre.

**Status- und Sicherheitsvertrag:** Vor dem ersten vollständigen Snapshot ist
die verschachtelte Diagnose ausdrücklich `unavailable`. Danach enthält sie
Schema, passiven Modus, Kontext/Revision, Quellenfrische, aktuelle Region,
begrenzte Blockercodes und ausschließlich Zähler. `result_state` bleibt
`in_progress`, `terminal` und `completion_allowed` bleiben `false`. Maximal 128
Blockercodes werden ausgegeben; Gesamtzahl und Abschneidung bleiben sichtbar.
Fehler im Policyadapter sperren nur dessen Diagnose und unterdrücken den
separaten Schattenstatus nicht. Der Adapter erhält bewusst keine
Aufgabenverfügbarkeit: vorhandene offene Aufgaben werden deshalb
`unknown`, nicht auswählbar. Bei deaktiviertem Opt-in besitzt der Legacystatus
kein `wohnungserkundung`-Feld und bleibt in allen bisherigen Feldern gleich.

Geändert wurden ausschließlich der Lebenszyklus-/Migrationsadapter, der passive
Abschnitt des bestehenden Explorer-Nodes, ein Standardparameter, zugehörige
Vertragstests und diese Statusdatei. `ExploreArea`, Nav2-Action, Zielbildung,
Frontier-/Portalwahl, Coverageabschluss, Command-/Twist-Publisher, Karten- und
Semantikmanager sowie Apps wurden nicht funktional geändert.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble und
frischem temporären Overlay; keine Geräte, realen Karten, Bags, Actions oder
Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M3F-FOCUS | Lebenszyklus-, Migration- und Nodevertrag gemeinsam: **155 passed**; darunter atomarer Snapshot, Pflicht-Opt-in, gesperrter Abschluss, Ausgabegrenze, Sperrfreigabe sowie identischer Legacy-OFF-Pfad. |
| WE-M3F-EXPLORER | Vollständige Explorer-Suite: **648 passed**. |
| WE-M3F-ADJACENT | Explorer plus Fingerprint-, Karten-, Semantik-, Mission- und Launch-Verträge: **811 passed**. |
| WE-M3F-COLCON | Frischer Build von `amadeus_map_identity`, `robot_interfaces` und `explore`; **36 + 648 = 684 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M3F-ROS | Isolierte lokale DDS-Domain, direkter Explorer ohne Action: synthetischer Kartenmanagerstatus ergab Revision **1**, Policyzustand `waiting_for_fresh_sources`, `completion_allowed=false` und **0** Nachrichten auf beiden Explorer-Command-Topics. |
| WE-M3F-STATIC | `compileall`, auf geänderte Zeilen begrenztes `flake8` mit E501/W503-Ausnahmen und `git diff --check`: bestanden. |

Der erste ROS-Probelauf verwendete versehentlich einen volatilen
Kartenstatus-Publisher und wurde von der korrekt transient-lokalen Subscription
wegen inkompatibler QoS abgewiesen; nach Korrektur auf Reliable/Transient Local
bestand derselbe gerätefreie Test. Das ist Testaufbau-Evidenz, kein Produktfehler
und keine Hardwareaussage.

**Offene Grenzen:** Der Adapter belegt die passive Runtimeverkabelung, liefert
aber noch keine echte Verfügbarkeit, Weglänge, Informationsfläche, Auswahl,
Attempt-/Retryfortschreibung, Kindzielkorrelation oder Abschlussbeobachtung. Die
fehlende Portalgedächtnisrevision im bewusst minimalen ROS-Smoke macht die Quelle
korrekt veraltet. Reale Managerperiodik, Plannerverfügbarkeit, Jetsonlast,
HWT-/lokale Mischstandintegration, Sicherheitskette, Sensorik und Hardware sind
nicht geprüft. Softwaretests bedeuten keine Fahr- oder Hardwareabnahme.

**Nächster abgegrenzter Schritt WE-M3/G:** Eine reine und anschließend nur
passiv diagnostische Belegnaht auf der exakt korrelierten Rohkarte festlegen und
implementieren. Sie ordnet Frontieraufgaben ihrer stabilen Geometrie zu und
liefert revisionsgebundene Verfügbarkeit, geodätische Weglänge und
Informationsgewinn; fehlende Pose/Karte, veraltete Identität, nicht auflösbare
Portal-/Beobachtungsaufgaben und Berechnungsfehler bleiben explizit unbekannt.
Noch keine zustandsbehaftete Auswahl, kein Ziel und kein Nav2-Aufruf.

**Rückfall:** `wohnungserkundung_policy_enabled: false` entfernt die neue
Bewertung und das verschachtelte Statusfeld, ohne den vorhandenen Schatten zu
deaktivieren. Vollständiger Rückfall ist der einzelne M3/F-Revert; bestehender
Schatten-, Legacy-, Action-, Navigations- und Fahrzustand bleibt unverändert.
Es wurde nichts deployed oder an Hardware aktiviert.

### 2026-09-14 – WE-M3/E: Verbraucher- und Migrationsvertrag

**Arbeitsbasis und Inventur:** `feature/we-m3e-consumer-migration` baut direkt
auf M3/D `55ed9d4` auf. Die Suche über Quellcode, Actions, BT-XML,
Konfigurationen, iOS/Web und Mocks ergab:

- `ExploreArea.action` wird vom Explorer produziert. Einziger produktiver
  direkter Resultatverbraucher ist `exploration_nodes.hpp`; er akzeptiert nur
  ROS-Status `SUCCEEDED` zusammen mit `result.success=true`. Die beiden BT-Bäume
  `explore.xml` und `pick_and_place.xml` verwenden diesen Knoten. Der
  Missionmanager startet den jeweiligen Baum und sieht danach nur das
  zusammengefasste `RunMission`-Ergebnis. `mock_servers_node.py` ist
  Testproduzent, kein zusätzlicher Produktionsverbraucher.
- `/explore/status_json` wird allein in `explore_node.py` erzeugt. Direkte
  Laufzeitverbraucher sind `src/smartphone_gui/web/app.js` und die iOS-Kette
  `RosbridgeProtocol.swift` → `RobotController.swift` → `DashboardView.swift`.
  Der Python-Rosbridge-Mock erzeugt/transportiert Teststatus. iOS verlangt einen
  vollständigen Schema-1-Kernsatz und bekannte Top-Level-Zustände, ignoriert
  aber wie der Webdecoder zusätzliche JSON-Schlüssel.
- Coverage wird in Web/iOS ausschließlich als Fahrspurfortschritt angezeigt.
  `map_ready_to_save` steuert dort nur den Hinweis, dass gespeichert werden
  kann. Kein produktiver Kartenmanager-, Mission- oder BT-Code abonniert dieses
  Feld oder löst dadurch automatisch eine Speicherung aus. Dokumentations- und
  Prüfskriptfundstellen sind Bedien-/Historienquellen, keine Runtimeverbraucher.

**Additive Migration:** Die `ExploreArea`-ABI und der vorhandene Top-Level-
Status Schema 1 bleiben zunächst byte-/feldseitig unverändert. Der neue reine
Adapter `exploration_migration.py` legt die spätere Abbildung fest:
`complete_accessible` → Legacy `success`/Action-Success true; `partial` →
Legacy `partial` bei terminal `SUCCEEDED`, aber Action-Success false;
`aborted` → Legacy `failed`/`ABORTED`; `canceled` → Legacy
`canceled`/`CANCELED`. Damit kann der bestehende BT nur beim starken neuen
Vollabschluss erfolgreich werden. Die detaillierten WE-Felder werden additiv
unter `wohnungserkundung` mit eigenem `schema_version: 1` vorgesehen. Darin
bleiben Ergebnisgrund, Fensterzähler, Blocker, `map_saved` und Rückkehrergebnis
getrennt. Altes Coverage und `map_ready_to_save` werden nicht in eine
Wohnungsvollständigkeitsgarantie umgedeutet.

**Ausgeführte Prüfungen:** Keine ROS-Knoten oder Geräte gestartet:

| Test-ID | Ergebnis |
|---|---|
| WE-M3E-FOCUS | **9 neue** Fälle für alle konservativen Ergebnisabbildungen, versionierte Erweiterung, unveränderte Action-ABI, einzigen produktiven Resultatverbraucher und unveränderte iOS-/Web-Legacyfelder: bestanden. |
| WE-M3E-EXPLORER | Vollständige Explorer-Suite: **638 passed**. |
| WE-M3E-ADJACENT | Explorer plus Fingerprint-, Karten-, Semantik-, Mission- und Launch-Verträge: **801 passed**. |
| WE-M3E-COLCON | Frischer Build von `amadeus_map_identity`, `robot_interfaces` und `explore`; **36 + 638 = 674 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M3E-STATIC | `compileall`, `flake8` mit E501/W503-Ausnahmen und `git diff --check`: bestanden. |

**Nachweisgrenze:** Die Inventur und reine Abbildung belegen noch keine
veröffentlichte WE-Erweiterung, keinen aktualisierten App-Verbraucher, keine
Actionausführung, Speicherung, Rückkehr, Zielbildung, Jetsonintegration, Fahrt
oder Hardwareabnahme. Dass unbekannte JSON-Schlüssel kompatibel sind, erlaubt
die additive Form; es ersetzt keine spätere Ende-zu-Ende-Prüfung.

**Nächster abgegrenzter Schritt WE-M3/F:** Einen unabhängig und standardmäßig
deaktivierten passiven Runtimeadapter im Explorer ergänzen. Er darf nur den
vorhandenen vollständigen Schatten-Snapshot bewerten und das verschachtelte
`wohnungserkundung`-Objekt an den Legacy-Status anhängen. Mangels echter
Verfügbarkeits-/Wegkostenzuführung müssen offene Aufgaben unbekannt und der
Abschluss gesperrt bleiben. Keine Action-, Zielwahl-, Nav2-, Command- oder
Twist-Änderung.

**Rückfall:** Den einzelnen M3/E-Commit zurücknehmen oder den noch unbenutzten
reinen Adapter nicht aufrufen. Action, Legacy-Status, Apps und Runtime bleiben
unverändert; kein Prozess-, Fahr- oder Hardwarezustand ist zurückzusetzen.

### 2026-09-14 – WE-M3/D: reiner Abschlussautomat

**Arbeitsbasis und Umfang:** `feature/we-m3d-completion-contract` baut direkt
auf M3/C `d758a29` auf. Neu sind `exploration_completion.py`, reine Tests sowie
die explizite Kontext-/Revisionsangabe im bestehenden Policyergebnis und diese
STATUS.md. Node, Profile, Actions, Statuspublisher und Fahrpfade bleiben
unverändert.

**Abschlussvertrag:** Eine `CompletionObservation` korreliert exakt einen
M3-Policyentscheid mit Kartenkontext und -revision, explizit geprüftem
zugänglichem Auftragsscope und Kindnavigationszustand. Der begrenzte Automat
akzeptiert nur streng steigende inhaltlich neue Revisionen; exaktes ID-Replay
ist idempotent, widersprüchliche IDs oder Revisionen scheitern fail-closed.
Standardmäßig sind drei aufeinanderfolgende qualifizierte Neubewertungen nötig.
Nur `completion_window_required`, verifizierter Scope, sicher `idle` gemeldete
Kindnavigation und das Fehlen von Retryblockern zählen. Jede offene/gefilterte
Aufgabe oder sonstige Policyblockade, aktives/unklares Kindziel oder ungeklärter
Scope setzt die Folge auf null.

**Getrennte Ergebnisse:** Erst das vollständige Fenster erzeugt terminal
`complete_accessible`. Explizites Budget-/Zeit-/Energieende ergibt `partial`,
System-/Sensorfehler `aborted`, Nutzerabbruch `canceled`; diese Gründe werden
nicht ineinander oder in Erfolg umgedeutet. `map_saved` und das getrennte
Rückkehrergebnis bleiben unabhängige Felder und verändern den
Erkundungszustand nicht. Ein terminaler Zustand ist unveränderlich. Der Automat
liest keine Uhr und besitzt keine ROS-, Action-, Planner-, Ziel-, Command-,
Dateisystem- oder Geräteabhängigkeit. Drei Revisionen sind ein synthetischer
Softwarestartwert und vor späterer Abnahme zu begründen und einzufrieren.

**Ausgeführte Prüfungen:** Nur lokale Software-/Buildumgebung, keine ROS-Knoten
oder Geräte gestartet:

| Test-ID | Ergebnis |
|---|---|
| WE-M3D-FOCUS | **13 neue** Fälle für Drei-Revisionen-Fenster, Scope-/Kindzielblockade, Reset, offene/gefilterte Aufgaben, getrennte Terminalgründe, unabhängige Speicherung/Rückkehr, Replay/Terminalität, Korrelation/Kapazität und Importgrenze; gesamte Policy-/Abschlusssuite: **50 passed**. |
| WE-M3D-EXPLORER | Vollständige Explorer-Suite: **629 passed**. |
| WE-M3D-ADJACENT | Explorer plus Fingerprint-, Karten-, Semantik-, Mission- und Launch-Verträge: **792 passed**. |
| WE-M3D-COLCON | Frischer Build von `amadeus_map_identity`, `robot_interfaces` und `explore`; **36 + 629 = 665 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M3D-STATIC | `compileall`, `flake8` mit E501/W503-Ausnahmen und `git diff --check`: bestanden. |

**Nachweisgrenze:** Belegt ist ausschließlich der reine deterministische
Softwarevertrag. Nicht belegt sind reale Quellenfrequenz, Planner, laufende
Kindnavigation, Aktionsabbruch, Speicherung, Rückfahrt, Jetsonlast, Sensorik,
Fahrt oder Hardwareabnahme. Die neuen Resultate sind noch an keinen bestehenden
Verbraucher veröffentlicht.

**Nächster abgegrenzter Schritt WE-M3/E:** Verbraucher von `ExploreArea`,
`/explore/status_json`, Coverage und `map_ready_to_save` vollständig im aktuellen
Stack inventarisieren. Darauf eine versionierte oder additive
Kompatibilitätsnaht mit exakten Dateien, Tests und Rückfall festlegen; noch keine
Action-/Runtime-/Fahränderung.

**Rückfall:** Den einzelnen M3/D-Commit zurücknehmen. M3/C und alle Runtimepfade
bleiben unverändert; es gibt keinen Prozess-, Fahr- oder Hardwarezustand
zurückzusetzen.

### 2026-09-14 – WE-M3/C: revisionsgebundene skalare Aufgabenbewertung

**Arbeitsbasis und Umfang:** Der isolierte Branch
`feature/we-m3c-task-scoring` baut direkt auf dem M3/B-Reviewcommit `9b26d3e`
auf. Geändert werden nur `explore/exploration_policy.py`, seine reinen Tests und
diese STATUS.md. Kein Node, Profil, Actionvertrag oder Fahrpfad wird verändert.

**Bewertungsvertrag:** `TaskUtilityEvidence` bindet eine stabile Aufgaben-ID,
den Kartenkontext und exakt die aktuelle Kartenrevision an zwei skalare Größen:
`geodesic_path_length_m` in Metern und `information_gain_square_m` in
Quadratmetern. Der Vertrag enthält absichtlich weder Pfadpunkte noch Pose oder
Ziel. `score_task_utilities()` verlangt eine vollständige, duplikatfreie
Evidenzmenge für genau den auswählbaren Bestand. Fremde Kontexte, fehlende,
zusätzliche, doppelte, alte/zukünftige oder nichtendliche Werte werden
fail-closed abgewiesen; die Evidenzkapazität ist hart begrenzt.

**Normierung und Auswahl:** Die sichtbare `TaskScoringPolicy` kappt standardmäßig
Weglänge bei 20 m und Informationsfläche bei 10 m², normiert beide auf `[0,1]`
und bildet `0,4 * (1 - Wegkosten) + 0,6 * Informationsgewinn`. Gewichte werden
auf ihre Summe normiert, sodass auch bewusst einseitige Profile eindeutig sind.
Diese Zahlen sind synthetische Softwarestartwerte, keine Mess-, Wohnungs- oder
Freigabeschwellen; vor Abnahmeläufen sind sie zu begründen und einzufrieren.
Die M3/B-Sitzung verwendet den Score nur innerhalb der bereits zulässigen
hierarchischen Kandidatenmenge. Regionshaltezeit und Anti-Verhungerung bleiben
vorrangige Verlaufsgates; innerhalb derselben Stufe gewinnen höherer Score,
ältere Sichtung und schließlich die sichere Aufgaben-ID. Ohne
Bewertungsevidenz bleibt das M3/B-Verhalten unverändert.

**Ausgeführte Prüfungen:** Lokaler Entwicklungsrechner mit ROS Humble nur als
Build-/Testumgebung; keine ROS-Knoten oder Geräte wurden gestartet:

| Test-ID | Ergebnis |
|---|---|
| WE-M3C-FOCUS | **7 neue** reine Fälle für Einheiten/Normierung/Kappung, scorebasierte ID-Wahl, stabilen Gleichstand, sichtbare Gewichtswirkung, exakte Bestands-/Revisionsdeckung, fremde/duplizierte/nichtendliche Eingaben und Kapazitäts-/Konfigurationsgrenzen; gesamte Policysuite: **37 passed**. |
| WE-M3C-EXPLORER | Vollständige Explorer-Suite: **616 passed**. |
| WE-M3C-ADJACENT | Explorer plus gemeinsame Fingerprintquelle, Kartenmanager, Semantikmanager sowie semantische Mission-/Launch-Verträge: **779 passed**. |
| WE-M3C-COLCON | Frischer temporärer Build von `amadeus_map_identity`, `robot_interfaces` und `explore`; **36 + 616 = 652 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M3C-STATIC | `compileall`, `flake8` unter den Projekt-Ausnahmen E501/W503 und `git diff --check`: bestanden. |

**Nachweisgrenze:** Die Tests belegen reine Arithmetik, Vertragsvalidierung und
deterministische Auswahl mit synthetisch vorgegebenen Skalaren. Sie belegen
weder, dass ein realer Planner diese Weglänge liefert, noch die Güte eines
Informationsmaßes, Pfadgültigkeit, Zielpose, Lokalisierung, Jetsonlast,
Sicherheitsfreigabe, Bewegung oder Hardwareabnahme. Eine hoch bewertete ID ist
kein sicherer Pfad und kein Fahrbefehl; `completion_allowed` bleibt `false`.

**Nächster abgegrenzter Schritt WE-M3/D:** Einen reinen, revisionsgetriebenen
Abschlussautomaten ergänzen, der mehrere frische, inhaltlich neue
Neubewertungen verlangt und laufende Kindnavigation sowie expliziten
zugänglichen Auftragsscope als zusätzliche Eingänge führt. Vollabschluss bleibt
bei jedem M3/A-/B-Blocker gesperrt; Budgetende wird `partial`, Sensor-/Systemfehler
`aborted` und Nutzerabbruch `canceled`. Bestehende Action- und JSON-Verträge
werden erst nach diesem reinen Vertrag inventarisiert und kompatibel migriert.

**Rückfall:** Den einzelnen WE-M3/C-Commit zurücknehmen oder keine
`TaskUtilityEvidence` übergeben. Dann bleibt der reine M3/B-Verlauf unverändert.
Es gibt keinen Prozess-, Fahr- oder Hardwarezustand zurückzusetzen.

### 2026-09-14 – WE-M3/B: begrenzter Aufgabenverlauf und Regionshysterese

**Arbeitsbasis und Umfang:** Der isolierte Branch
`feature/we-m3b-task-history` baut direkt auf dem M3/A-Reviewcommit `66f9efb`
auf. Geändert werden nur `explore/exploration_policy.py`, seine reinen Tests und
diese STATUS.md. Die laufende Roboter-Arbeitskopie, Explorer-Node,
Konfigurationen, Actions und Fahrpfade bleiben unverändert.

**Verlaufsvertrag:** `ExplorationTaskPolicySession` besitzt genau einen
`PortalMapContext` und übernimmt nur streng steigende Snapshotrevisionen;
identisches Replay liefert dasselbe Ergebnis, abweichender Inhalt auf derselben
Revision wird abgewiesen. Pro stabiler Aufgaben-ID hält die begrenzte Sitzung
erste/letzte Sichtung, Alter in Revisionen, letzte Auswahl und Auswahlzahl,
letzten Versuch, Versuchszahl, Retryfehler, früheste Retryrevision, letzten
Versuchsgrund, Reaktivierungsrevision und den aus dem Graph übernommenen
Erledigtzustand. Vollständige Graphaufgaben werden beobachtet; erledigte
Aufgaben bleiben im Verlauf sichtbar und sind nicht mehr auswählbar.

`TaskAttempt` übernimmt ausschließlich ein extern bereits festgestelltes
`progressed` oder `retryable_failure`. Ein Retryfehler ist bis zu einer explizit
späteren Kartenrevision zurückgestellt. Nach dem konfigurierten Fehlversuchsbudget
bleibt die Aufgabe gesperrt, bis ein eigenes idempotentes
`TaskReactivation`-Ereignis auf neuer Evidenz die Sperre löscht. Kein
Nav2-Status, keine Pose und kein Motorbeleg wird in diesem Modul als Versuch,
Fortschritt oder Abschluss interpretiert. Fremde Kontexte, unbekannte oder
erledigte Aufgaben, alte Ereignisse, widersprüchlich wiederverwendete IDs und
Kapazitätsüberschreitungen scheitern fail-closed vor der Fortschreibung.

**Hierarchische ID-Auswahl:** Aus den von M3/A lediglich als geeignet
ausgewiesenen Aufgaben wird deterministisch höchstens eine Aufgaben-ID gewählt.
Zunächst bleibt eine bereits gewählte Region für mindestens zwei
Snapshotrevisionen stabil, sofern sie weiter geeignete Aufgaben besitzt. Danach
erhält eine seit acht Revisionen nicht gewählte Aufgabe Vorrang; bei Gleichstand
entscheiden ältere Sichtung und sichere Aufgaben-ID. Ohne überfällige Aufgabe
hat die aktuelle Graphregion Vorrang. Auswahlrevision und -zahl werden erst bei
einer neuen Revision fortgeschrieben, sodass Replay keine künstliche Alterung
oder Rotation auslöst. Zwei und acht sind ausdrücklich synthetische
Softwarestartwerte, keine nachgewiesenen Wohnungs-, Zeit- oder
Hardwaregrenzwerte; sie müssen vor einer späteren Abnahme begründet und
eingefroren werden.

**Ausgeführte Prüfungen:** Lokaler Entwicklungsrechner mit ROS Humble nur als
Build-/Testumgebung; keine ROS-Knoten oder Geräte wurden gestartet:

| Test-ID | Ergebnis |
|---|---|
| WE-M3B-FOCUS | **12 neue** reine Verlaufsfälle für ID-Auswahl, Alter, Replay/Konflikt, Regionshaltezeit, Anti-Verhungerung bei erhaltener Haltezeit, Retryverzögerung, Budgeterschöpfung, Reaktivierung, Ereignisreplay, Fortschritt, erledigte Historie, Kapazität und ungültige Ereignisse; gesamte Policysuite: **30 passed**. |
| WE-M3B-EXPLORER | Vollständige Explorer-Suite: **609 passed**. |
| WE-M3B-ADJACENT | Explorer plus gemeinsame Fingerprintquelle, Kartenmanager, Semantikmanager sowie semantische Mission-/Launch-Verträge: **772 passed**. |
| WE-M3B-COLCON | Frischer temporärer Build von `amadeus_map_identity`, `robot_interfaces` und `explore`; **36 + 609 = 645 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M3B-STATIC | `compileall`, `flake8` unter den Projekt-Ausnahmen E501/W503 und `git diff --check`: bestanden. |

**Nachweisgrenze:** Die Softwaretests belegen deterministische, begrenzte
Zustandsfortschreibung und Auswahl von Aufgaben-IDs in synthetischen
Revisionen. Sie belegen weder reale Zeit, Route, Informationsgewinn, Planbarkeit,
Lokalisierung, TF-/DDS-Last, Jetsonverhalten, sichere Erreichbarkeit,
Durchfahrt noch Hardwareabnahme. Eine ausgewählte ID ist ausdrücklich kein
Navigationsziel oder Bewegungsauftrag; `completion_allowed` bleibt immer
`false`.

**Nächster abgegrenzter Schritt WE-M3/C:** In
`explore/exploration_policy.py` einen vollständigen, revisionsgebundenen
Bewertungsbeleg pro geeigneter Aufgaben-ID für geodätische Wegkosten und
Informationsgewinn ergänzen. Einheiten, harte Grenzen, Normierung, Gewichtung
und deterministische Gleichstände sind explizit zu testen. Die Session darf
damit nur zwischen IDs entscheiden; Planneraufruf, Zielpose, Runtime und
Fahrschnittstellen bleiben unverändert außen vor.

**Rückfall:** Den einzelnen WE-M3/B-Commit zurücknehmen. Dann bleibt der reine,
zustandslose M3/A-Vertrag vollständig erhalten. Da B weder importiert noch an
Runtime oder Geräte angebunden ist, gibt es keinen Prozess-, Fahr- oder
Hardwarezustand zurückzusetzen.

### 2026-09-14 – WE-M3/A: passiver Policy-Eingangs- und Ergebnisvertrag

**Arbeitsbasis und Umfang:** Nach `git fetch origin --prune` blieb
`ff4e42a1793fe66202f820dd081c1a1c5cd7049e` auf
`chore/we-m2at-passive-chain-load-probe` der neueste belegte WE-Status. Der
isolierte Branch `feature/we-m3a-policy-contract` baut direkt darauf auf; die
laufende, lokal veränderte Roboter-Arbeitskopie wurde weder gewechselt noch
beschrieben. Betroffen sind ausschließlich
`explore/exploration_policy.py`, die formatunabhängig öffentlich gemachte
Snapshotvalidierung in `region_graph_status.py`, deren Tests und diese
STATUS.md.

**Eingangsvertrag:** `assess_exploration_policy()` akzeptiert genau einen
vollständig konsistenten `ShadowStatusSource` und optional je offener Aufgabe
einen expliziten `TaskAvailability`-Beleg aus demselben Kartenkontext. Die
Zustände `available`, `filtered`, `temporarily_blocked`, `unknown` und
`excluded` sind revisionsgebunden und enthalten Grund sowie erneute
Prüfbedingung. Fehlender oder zu alter Beleg wird nicht als Wegfall behandelt,
sondern als unbekannt beziehungsweise `stale_evidence`. Fremde Kontexte,
zukünftige Revisionen, doppelte oder unbekannte Aufgaben-IDs, Belege für bereits
erledigte Aufgaben und Kapazitätsüberschreitungen werden fail-closed abgewiesen.
Die vorhandenen Grenzen und Frischewerte der Schattenprojektion werden
wiederverwendet; es wurden keine nachträglichen Hardware- oder Abnahmewerte
erfunden.

**Ergebnisvertrag:** Das unveränderliche Ergebnis enthält den vollständigen
offenen Aufgabenbestand vor jeder Verfügbarkeitsfilterung, getrennte Aufgaben
der aktuellen und anderer Regionen, eine deterministisch nach aktueller Region
gruppierte Liste lediglich geeigneter Aufgaben-IDs sowie den Einzelzustand jeder
Aufgabe. Außerdem weist es veraltete Quellen, unbestätigte Portale, unbekannte,
blockierte und ausgeschlossene Portalseiten, nicht betretene beziehungsweise
nicht fertig bewertete Regionen und maschinenlesbare Blocker aus. Eine
verfügbare Aufgabe ergibt `ready_with_tasks`; ausschließlich fehlende oder
veraltete Aufgabenevidenz wartet auf Neubewertung; nur gefilterte, blockierte
oder ausgeschlossene Restaufgaben ergeben einen erklärten
`partial_candidate`. Veraltete Quellen haben Vorrang vor jeder positiven
Aufgabenbewertung.

Selbst frische, vollständig als Kandidat bewertete Regionen ohne offene Aufgabe
ergeben nur `completion_window_required`. Das Ergebnis setzt
`completion_allowed` ausnahmslos auf `false` und nennt dann zusätzlich das noch
fehlende frische Mehrfachbeobachtungsfenster, den zugänglichen Auftragsscope und
den Kindnavigationsstatus. M3/A kann daher weder `complete_accessible` noch ein
Fahrziel behaupten. Es besitzt keine Uhr, ROS-, Action-, Nav2-, Planner-,
Prozess-, Geräte-, Command- oder Twist-Abhängigkeit und ist an keinen
Produktionspfad angebunden.

**Ausgeführte Prüfungen:** Lokaler Entwicklungsrechner mit ROS Humble nur als
Build-/Testumgebung; keine ROS-Knoten oder Geräte wurden gestartet:

| Test-ID | Ergebnis |
|---|---|
| WE-M3A-FOCUS | Neue reine Policyfälle für Regionskontinuität, vollständigen Bestand, Determinismus/Unveränderlichkeit, alle Verfügbarkeitszustände, fehlende/veraltete Evidenz, Quellenfrische, Abschlussblockade, Struktur-/Erreichbarkeitsblocker, Eingabefehler, Kapazität und Importgrenze: **18 passed**. Zusammen mit der Statusprojektion: **68 passed**. |
| WE-M3A-EXPLORER | Vollständige Explorer-Suite: **597 passed**. |
| WE-M3A-ADJACENT | Explorer plus gemeinsame Fingerprintquelle, Kartenmanager, Semantikmanager sowie semantische Mission-/Launch-Verträge: **760 passed**. |
| WE-M3A-COLCON | Frischer temporärer Build von `amadeus_map_identity`, `robot_interfaces` und `explore`; **36 + 597 = 633 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M3A-STATIC | `compileall`, `flake8` unter den Projekt-Ausnahmen E501/W503 und `git diff --check`: bestanden. |

**Nachweisgrenze:** Diese Prüfungen belegen den reinen Softwarevertrag und seine
konservative Abschlussblockade. Sie belegen keine Güte eines Planers, keine
tatsächliche/geodätische Weglänge, keinen Informationsgewinn, keine
Lokalisierung, Sicherheitsfreigabe, Durchfahrt, Jetsonlast oder
Hardwareabnahme. Insbesondere ist `available` keine Aussage über einen aktuell
sicheren Pfad und `partial_candidate` noch kein endgültiges Action-Ergebnis.

**Nächster abgegrenzter Schritt WE-M3/B:** In
`explore/exploration_policy.py` einen begrenzten, nur durch explizite Revisionen
fortgeschriebenen Verlauf für Aufgabenalter, letzten Versuch, Fehlversuche,
Retrybudget und Reaktivierungsbedingung ergänzen. Die zugehörigen reinen Tests
müssen Replay, spätere Freigabe blockierter Aufgaben, deterministische
Regionshysterese sowie ausbleibendes Pendeln und Verhungern abdecken. Ausgabe
bleibt eine Aufgaben-ID, niemals Pose oder Fahrziel; Node, Action, Nav2 und
bestehende Zielwahl bleiben in diesem Schritt unverändert.

**Rückfall:** Den einzelnen WE-M3/A-Commit zurücknehmen oder das neue Modul
nicht importieren. Da kein Runtime-Aufrufer, Publisher, Ziel oder Gerätezugriff
hinzukam, gibt es keinen Prozess-, Fahr- oder Hardwarezustand zurückzusetzen;
WE-M2/AT bleibt unverändert nutzbar.

### 2026-09-14 – WE-M2/AT: wachsender Langlauf der passiven Gesamtkette

**Werkzeug und Sicherheitsgrenze:**
`tools/kartierung/passive_kette_lasttest.py` ist ein eigenständiger
Offline-Prüfer. Er startet keine ROS-Knoten oder Kindprozesse, liest keine
realen Karten/Bags und besitzt keine Publisher-, Action-, Nav2-, Twist- oder
Geräteschnittstelle. Seine synthetischen OccupancyGrids durchlaufen die
tatsächlichen reinen Produktionsmodule für Rohkartenidentität, Exaktjoin,
Frontierdetektion, Portalbeobachtung, Schattenlebenszyklus, Regionsgraph und
Aufgaben. Der separate ROS-Smoke aus AS bleibt Nachweis der Nodeverkabelung.

**Deterministische Folge:** Der längere belegte Lauf umfasst 240 verschiedene
Kartenrevisionen. Eine verbundene Raum–Tür–Raum-Geometrie wechselt die
Engstellenkante geringfügig; alle zehn Revisionen wächst das Raster symmetrisch,
bis maximal 24 Polsterzellen pro Seite erreicht sind. Der Kartenursprung wird
gegenläufig verschoben, sodass die metrische Wohnungsgeometrie stabil bleibt.
Ein belegter Marker außerhalb der Nutzgeometrie erzwingt pro Revision einen
neuen exakten Fingerprint. Maximal wurden 15.984 Zellen pro Snapshot und
insgesamt 2.496.160 Eingangsbytes verarbeitet.

Vor und nach jeder Kette vergleicht der Prüfer Metadaten und Zellbytes. Alle 240
Vergleiche blieben bytegleich. Jede Revision erzeugte genau eine qualifizierte
Portalbeobachtung. Nach der zweiten Revision blieben ein bestätigtes Portal,
zwei Regionen und eine Verbindung stabil. Der vollständige ungefilterte
Frontierbestand blieb bei genau einer sitzungsstabilen Frontieraufgabe. Zusammen
mit erledigter Beobachtungs- und offener Portalaufgabe betrug der Bestand
durchgehend höchstens und am Ende genau drei Aufgaben. Ein separater Track mit
Kapazität eins wies eine zweite neue Frontier zurück und blieb zustandsgleich auf
dem vorherigen Snapshot; die integrierte Graphatomizität ist zusätzlich in AS
getestet.

**Gemessene lokale Ressourcen:** Auf dem aktuellen Entwicklungsrechner wurden
pro vollständiger Revision Median 40.597.590 ns, p95 75.043.337 ns und maximal
111.125.872 ns gemessen. Prozess-RSS Start/Spitze/Ende waren
63.651.840/66.592.768/66.592.768 Byte, also 2.940.928 Byte beobachteter
Spitzenanstieg. Das sind reproduzierbare Beobachtungswerte, keine eingefrorenen
Grenzwerte und keine Jetson-Prognose; Hintergrundlast und Pythonallocator sind
enthalten.

**Ausgeführte Prüfungen:** Der 240-Revisionen-Lauf bestand mit Actions/Commands
`0` und `hardware_access=false`. Die fünf neuen Offline-Vertragstests prüfen
Kurzlauf, Wachstum/Ursprung, Kapazitätsatomizität, Argument-/Ausgabegrenzen und
das Fehlen von Prozess-/Fahrschnittstellen. Gemeinsam mit dem vorhandenen
Rohkartenlastprüfer bestanden **14 Tests**; zusammen mit der unveränderten
Explorer-Suite **593 Tests**. `compileall`, geänderte Pythonzeilen mit `flake8`
unter den Projekt-Ausnahmen E501/W503 und `git diff --check` bestanden. Da nur
ein Werkzeug, dessen Tests, README und diese STATUS.md hinzukommen, ist der
unveränderte frische AS-Paketbuild mit **615 Tests** weiterhin die Codebasis;
AT benötigt und verändert kein installierbares ROS-Paket.

**Abnahmegrenze:** Der Lauf belegt lokal, dass der vereinbarte passive
Softwarepfad bei diesem synthetischen Wachstum keine Aufgaben-/Identitätsdrift,
Rastermutation oder ungebremstes RSS-Wachstum zeigte. Er belegt keine reale
Kartenrate, DDS-/TF-Parallelität, SLAM-Korrekturverteilung, Jetsonlast,
Lokalisierung, Erreichbarkeit, Durchfahrt oder Hardwareabnahme. Mangels vorab
eingefrorener Zeit-/RSS-Schwelle werden die Messwerte nicht nachträglich als
Zielsystemfreigabe deklariert.

**Nächster abgegrenzter Schritt WE-M3/A:** Einen ROS-freien, deterministischen
Policyvertrag auf den vorhandenen passiven Snapshots aufbauen. Er muss offene
Frontier-/Portal-/Beobachtungsaufgaben, Quellenfrische, Regionskontinuität,
Blockade-/Unklarzustände und erklärbare Teilstände bewerten, aber noch kein
Fahrziel erzeugen und keinen bestehenden Explorerpfad verändern.

**Rückfall:** Den einzelnen WE-M2/AT-Commit zurücknehmen oder das neue
Offline-Werkzeug nicht aufrufen. Es gibt keinen laufenden Prozess, Geräte- oder
Fahrzustand zurückzusetzen; AS und alle Produktionsmodule bleiben unverändert.

### 2026-09-14 – WE-M2/AS: ungefilterte Frontiers bleiben offene Aufgaben

**Quellen- und Aktivierungsentscheidung:** Ein neuer unabhängiger Opt-in
`region_graph_shadow_frontiers_enabled` ist standardmäßig `false` und nur mit
aktivem Regionsgraph-Schatten, aktiver Rohkartenkorrelation und positiver
Join-Kapazität zulässig. Er nutzt dieselbe exakt korrelierte Rohkartennachricht
wie der Portalpfad. Auf ihr läuft ausschließlich die bereits vorhandene
`_detect_frontiers()`-Erkennung mit der bestehenden Mindestgröße. Das Ergebnis
wird vollständig vor `_rank_frontiers()`, Anfahrprojektion, Besuchsfilter,
Blacklist und Planner in einen typisierten Inventarvertrag überführt. Damit
kann keiner dieser ausführungsbezogenen Filter den passiven Bestand verkleinern.

**Identität und Aufgabenverwaltung:** Der reine, begrenzte
`FrontierTaskTracker` sortiert das vollständige Inventar deterministisch und
hält höchstens 4096 sitzungsbezogene Tracks sowie genau das letzte Inventar für
Replay. Eine neue Beobachtung übernimmt eine bestehende ID nur bei eindeutig
gegenseitig nächster Zuordnung innerhalb des bereits konfigurierten
`frontier_revisit_radius_m`. Bei Distanzgleichstand, Split-/Merge-Mehrdeutigkeit
oder größerer Verschiebung entsteht eine zusätzliche offene Frontier-ID; alte
IDs werden nicht stillschweigend verschmolzen oder gelöscht. Eine Folgesicht
trifft diese neue ID wieder und erzeugt dadurch kein ungebremstes Duplikat.

Neue IDs erzeugen transaktional genau eine `frontier`-Aufgabe in der zum
Beobachtungszeitpunkt aktuellen vorläufigen Region. Die unsegmentierte globale
Sicht bleibt über die ungefilterte Gesamtausgabe `tasks` erhalten. Wiedererkanntes
oder exaktes Replay erzeugt keine zweite Graphaufgabe. Ein leeres oder später
kleineres Inventar schließt ausdrücklich keine Aufgabe ab; Abschluss,
Fehlversuch, Sperrgrund und Reaktivierung gehören zur späteren WE-M3-Policy.
Kartenepochenwechsel bleiben wie zuvor ein fail-closed Neustartgrund.

**Runtimewirkung:** Karten-/Statusjoin, Detektion und Inventarbildung laufen
außerhalb der Schattensperre; vor der transaktionalen Mutation wird dasselbe
Korrelationspaar erneut geprüft. Portal- und Frontierinventar besitzen getrennte
Replayanker. Der Frontierpfad benötigt keine Pose. Er fügt keine ROS-Schnittstelle
hinzu und wird weder von Explorerstatus, Actionserver, Zielwahl, Nav2-Client,
Costmap-Portalplanung noch Twist-Publishern gelesen. Rohkarte und Costmap werden
nicht verändert.

**Ausgeführte Prüfungen:** Lokaler Arbeitsplatz mit ROS Humble, ausschließlich
synthetische Raster und statischer Test-TF:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AS-FOCUS | Inventar-/Tracker-, Sitzung/Lifecycle- und Nodeverträge einschließlich Replay, Wachstum, Verschwinden, Mehrdeutigkeit, Kapazitätsatomizität, Cachewechsel und ungefilterter Übergabe: **180 passed**. |
| WE-M2AS-EXPLORER | Vollständige Explorer-Suite: **579 passed**. |
| WE-M2AS-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **720 passed**. |
| WE-M2AS-COLCON | Frischer temporärer Build von drei Paketen; **36 + 579 = 615 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AS-ROS | Isolierte Domain 229, direkter Explorer und statischer TF über zwei Exaktkorrelationen: **1 stabile Frontieraufgabe**, 1 bestätigtes Portal, 2 Regionen, 1 Verbindung, insgesamt 2 offene/1 erledigte Aufgaben; Actions/Commands **0**, Hardwarezugriff **false**. |
| WE-M2AS-STATIC | `compileall`, auf geänderte Zeilen begrenztes `flake8` mit E501/W503-Ausnahmen und `git diff --check`: bestanden. |

Das ist ein gerätefreier Software- und ROS-Integrationsnachweis. Er belegt keine
reale Frontier, Lokalisierung, Erreichbarkeit, Fahrt, Jetsonlast oder
Hardwareabnahme. Insbesondere ist eine offene Aufgabe weder ein freigegebenes
Ziel noch eine Aussage, dass der Bereich aktuell sicher erreichbar ist.

**Offene Grenzen:** Frontier-IDs sind bewusst nur innerhalb der Kartenepoche und
Prozesssitzung stabil; dauerhafte Wiederaufnahme gehört zu WE-M5. Die räumliche
Zuordnung ist konservative Datenassoziation, keine Raumsegmentierung. Weil AS
keine Aufgaben abschließt, kann der Bestand wachsen; genau dieses Wachstum und
die kombinierte Portal-/Frontier-Rasterlast müssen im nächsten gerätefreien
Langlauf gegen die vorhandenen Grenzen gemessen werden.

**Nächster abgegrenzter Schritt WE-M2/AT:** Einen reproduzierbaren synthetischen
Langlauf der gesamten passiven Kette mit Kartenwachstum, Origin-/Geometrieänderung,
stabilen und verschwindenden Frontiers sowie Portalereignissen ausführen. Laufzeit,
RSS, Aufgaben-/Identitätszuwachs, harte Kapazitätsreaktion und bytegleich
unveränderte Eingangsraster protokollieren. Keine Geräte-, Ziel- oder Fahrwirkung.

**Rückfall:** Den einzelnen WE-M2/AS-Commit zurücknehmen oder
`region_graph_shadow_frontiers_enabled: false` belassen. Dann bleiben ARs
Portal-/Regions-/Aufgabenkette und alle Betriebswege unverändert; es gibt keinen
Geräte- oder Fahrzustand zurückzusetzen.

### 2026-09-14 – WE-M2/AR: automatische Strukturereignisse bis Region und Aufgabe

**Quellenentscheidung:** Der vorhandene verbundene Clearance-Detektor belegt
eine gemessene freie Engstelle, aber noch keine Raumgrenze. WE-M2/AR ergänzt
deshalb genau einen konservativen topologischen Beleg auf demselben exakt
korrelierten Rohkartensnapshot: Eine clearance-große Scheibe um den erkannten
Hals wird nur für die Analyse entfernt. Sind die aktuelle Roboterseite und eine
mindestens der vorhandenen Zielmindestfläche entsprechende Gegenseite danach
verschiedene Freiraumkomponenten, lautet die detectorseitige Strukturevidenz
`qualified`, andernfalls `insufficient`. Rohkarte und Nav2-Costmap bleiben
unverändert. Material oder reale lichte Türbreite werden daraus nicht behauptet.

Ein einzelner qualifizierter Snapshot bestätigt weiterhin kein Portal. Das
vorhandene Portalgedächtnis verlangt zwei unterschiedliche Kartenrevisionen;
identische Status-/Rohkartenreplays zählen nicht erneut. Die synthetische
Möbelinsel mit einem zweiten freien Weg bleibt trotz erkannter Engstelle
`insufficient`, weil der lokale Schnitt die Bereiche nicht trennt.

**Automatische Verwaltung:** Die reine `RegionGraphShadowSession` verarbeitet
eine solche `PortalObservation` transaktional auf tief kopiertem, begrenztem
Portal- und Graphzustand. Ein unbestätigtes Portal öffnet genau eine stabile
`observation`-Aufgabe in der aktuellen Region. Nach der zweiten qualifizierten
Revision wird diese Aufgabe erledigt, das bestätigte Portal an die aktuelle
Region gebunden, eine vorläufige gesehene/nicht betretene Gegenregion angelegt
und dort genau eine `portal`-Aufgabe geöffnet. Replays sind idempotent;
Fehler vor Abschluss übernehmen weder Teilzustände noch verlorene Aufgaben.

Eine separate transaktionale Methode kann ein bereits extern vollständig
validiertes `TraversalEvent` in Portalgedächtnis und Graph verbuchen und bei
bestätigtem Eintritt die Portalaufgabe erledigen. Sie liest keine Pose,
Footprint-, Encoder-, LiDAR-, Nav2- oder Actiondaten und bildet selbst kein
Durchfahrtsurteil. Insbesondere ist der bestehende Explorer-Fahrerfolg nicht
angebunden, weil weder Nav2-Erfolg noch Kartenpose allein den in der Strategie
verlangten vollständigen Chassis-Auslauf belegen.

**Runtimewirkung:** Der WE-M2/AQ-Nodepfad verwendet nun die reichere
Rohkartenbeobachtung und lässt die reine Sitzung Region und Aufgaben bilden.
Er läuft weiterhin nur bei denselben drei Opt-ins. Es gibt keine neue
Subscription, keinen Publisher, kein Launchprofil und keinen Verbraucher im
Action-, Zielwahl-, Costmap-, Navigations- oder Twist-Pfad.

**Ausgeführte Prüfungen:** Lokaler Arbeitsplatz mit ROS Humble als
Build-/Testumgebung; nur synthetische Raster und statischer Test-TF:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AR-FOCUS | Rohkartenbeleg, atomare Sitzung/Lifecycle und Nodevertrag einschließlich Tür-/Möbelnegativfall, zwei Revisionen, Aufgaben, Traversal-Replay-/Fehlergrenze: **177 passed**. |
| WE-M2AR-EXPLORER | Vollständige Explorer-Suite: **562 passed**. |
| WE-M2AR-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **703 passed**. |
| WE-M2AR-COLCON | Frischer temporärer Build von Abhängigkeiten und `explore`; **36 + 562 = 598 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AR-ROS | Isolierte Domain 230, direkter Explorer und statischer TF: zwei verschiedene Exaktkorrelationen, **1 bestätigtes Portal, 2 Regionen, 1 Verbindung, 1 offene und 1 erledigte Aufgabe**, Actions/Commands **0**, Hardwarezugriff **false**. |
| WE-M2AR-STATIC | `compileall`, auf geänderte Zeilen begrenztes `flake8` mit E501/W503-Ausnahmen und `git diff --check`: bestanden. |

Dies ist ein gerätefreier Software- und ROS-Integrationsnachweis. Er bestätigt
weder reale Wände/Türen noch Lokalisierung, Chassisauslauf, Jetsonlast,
Durchfahrt oder Hardware. Die neue Gegenregion ist ausdrücklich vorläufig und
`entered=false`.

**Offene Grenzen:** Ein topologischer Engpass in einer OccupancyGrid kann ohne
zusätzliche Sensor-/Semantikquelle nicht sicher zwischen Baukörper und einem
einzigen alternativen Weg versperrendem Möbelstück unterscheiden. Zwei
unabhängige Revisionen und der Trennnachweis reduzieren Fehlereignisse, sind
aber keine physische Türklassifikation. Die Durchfahrtsquelle bleibt offen,
bis gesamte transformierte Kontur, Seitenfolge, Frische und Auslauf mit
abgenommenen Konfigurationsdaten belegt werden können.

**Nächster abgegrenzter Schritt WE-M2/AS:** Den bereits berechneten
Frontierbestand passiv und revisionsgebunden in stabile Aufgaben überführen.
Globale/unsegmentierte Sichtbarkeit, Replay, Verschwinden ohne Abschluss,
Blacklist und Kartenwechsel fail-closed testen. Keine Policy, Zielauswahl,
Action, Navigation, Commands oder Fahrt ändern.

**Rückfall:** Den einzelnen WE-M2/AR-Commit zurücknehmen. Dann liefert der
dritte Opt-in wieder ausschließlich unqualifizierte Portalkandidaten wie in
WE-M2/AQ; keine automatische Region oder Aufgabe entsteht. Alternativ den
dritten Opt-in auf `false` belassen. Es gibt keinen Geräte- oder Fahrzustand
zurückzusetzen.

### 2026-09-14 – WE-M2/AQ: passive korrelierte Portalzuführung

**Umfang und Aktivierung:** `ExploreNode` übernimmt die in WE-M2/AO
implementierte reine Detektion nur bei dem neuen dritten Opt-in
`region_graph_shadow_connected_portals_enabled`. Der bestehende Schatten, die
Rohkartenkorrelation und eine positive Join-Kapazität müssen gleichzeitig
aktiv sein; ungültige Kombinationen werden beim Start abgelehnt. Die
Standardkonfiguration bleibt vollständig deaktiviert. Eigene, validierte
Schattenparameter begrenzen Analyse-Clearance, Kandidatenunsicherheit und
Pose-Retry. Es entstehen keine neuen ROS-Endpunkte.

**Nachgewiesene Datenkette:** Der Rohkarten-Callback hält unter der bestehenden
Schatten-Sperre höchstens die letzte Nachricht zusammen mit ihrer daraus
berechneten Identität. Beide bereits vorhandenen Join-Reihenfolgen können die
letzte exakte Korrelation bereitstellen. Der 1-Hz-Schatten-Timer verarbeitet
nur ein Paar, bei dem Fingerprint, Quellstempel und Frame übereinstimmen.
Pose-Lesen, erneuter Fingerprint und verbundene Clearance-Detektion laufen
außerhalb der Sperre; vor der Mutation wird dasselbe Paar erneut verglichen.
Ein zwischenzeitlicher Cachewechsel verwirft das alte Ergebnis. Exaktes Replay
wird nicht erneut detektiert. Fehlende Pose verbraucht einen begrenzten Retry;
danach oder bei ungültigem passendem Raster wird ausschließlich der Schatten
fail-closed gesetzt.

Die Kandidaten gelangen über das bestehende
`RegionGraphShadowLifecycle.observe_portal_plan()` in das Portalgedächtnis.
Sie behalten absichtlich `PortalStructuralEvidence.INSUFFICIENT`; deshalb
erzeugt diese Zuführung weder Portalbestätigung noch Graphverbindung,
Gegenregion oder Aufgabe. Explorerstatus, Actionserver, Nav2-Client,
Costmap-Portalplanung, Frontierauswahl und beide Twist-Publisher konsumieren
keinen neuen Zustand.

**Ausgeführte Prüfungen:** Lokaler Arbeitsplatz mit ROS Humble als
Build-/Testumgebung; ausschließlich synthetische Raster und eine statische
Testtransformation, keine Geräte, realen Karten, Bags, Actions oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AQ-CONTRACT | Node-/Parameter-/Callback-Verträge einschließlich OFF-Pfad, Aktivierung, beide Join-Reihenfolgen, Sperrgrenzen, Retry, Replay, Cachewechsel und Fehlerisolation: **64 passed**. |
| WE-M2AQ-FOCUS | Vertrag gemeinsam mit Rohkarten-Kandidatenadapter und Schattenlebenszyklus: **140 passed**. |
| WE-M2AQ-EXPLORER | Vollständige Explorer-Suite: **555 passed**. |
| WE-M2AQ-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **696 passed**. |
| WE-M2AQ-COLCON | Frischer temporärer Build von Abhängigkeiten und `explore`; Paketprüfungen: **36 + 555 = 591 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AQ-ROS | Isolierte Domain 231, direkter Explorer und statischer TF: exakte Korrelation **1**, Portal **1 unbestätigt**, Regionen **1**, Verbindungen/Aufgaben **0**, Actions/Commands **0**, Hardwarezugriff **false**. |
| WE-M2AQ-STATIC | `compileall`, auf geänderte Zeilen begrenztes `flake8` mit E501/W503-Ausnahmen und `git diff --check`: bestanden. |

Der ROS-Smoke bestätigt die Softwareverkabelung und den bewusst
unqualifizierten Zustand, nicht die reale Türgeometrie, Lokalisierung,
Parallel-/SLAM-Last, Jetson-Eignung oder eine Hardwareabnahme.

**Offene Grenze:** Der aktuelle Rohkartendetektor liefert geometrische
Kandidaten, aber keine qualifizierte Strukturevidenz. Die Runtime besitzt auch
keine unabhängige, vollständige Bewegungsquelle, die beide Portalseiten und den
Chassisauslauf revisionsgebunden belegt. Ohne diese Ereignisse darf die bereits
vorhandene Raum-/Aufgabenverwaltung nicht automatisch fortgeschrieben werden.

**Nächster abgegrenzter Schritt WE-M2/AR:** Vorhandene Quellen für genau diese
beiden Belegarten inventarisieren und nur eine belegbare, fail-closed
Ereignisbildung an den vorhandenen Schattenlebenszyklus anbinden. Der
funktionale Softwarepfad soll anschließend synthetisch von Eingangsdaten bis
zu Region und Aufgabe laufen. Wiederholung allein qualifiziert keine Struktur,
Nav2-Erfolg allein bestätigt keine Durchfahrt. Keine Action, kein Command,
keine Zielwahl und kein Fahrpfad werden verändert.

**Rückfall:** Den einzelnen WE-M2/AQ-Commit zurücknehmen oder den neuen dritten
Opt-in auf `false` belassen. Dann existieren weder Portalfeed-Cache noch dessen
TF-/Digest-/Detektorarbeit; der vorherige Schatten und sämtliche Betriebswege
bleiben unverändert.

### 2026-09-14 – WE-M2/AP: Besitzervertrag des passiven Portalfeeds

**Bestandsbefund:** `ExploreNode` besitzt bereits genau einen optionalen
Schattenlebenszyklus, dessen Sperre, Kartenstatus-Subscription,
Rohkartenidentitätszuführung und 1-Hz-Statustimer. Beide Eingangsreihenfolgen
werden im reinen `RawMapStatusJoiner` unterstützt; der Callback verwirft das in
`ShadowLifecycleUpdate.raw_map_correlation` zurückgegebene Exaktergebnis aber
noch. Der Node hält zwar die jeweils letzte `/map`-Nachricht, doch ein späterer
Kartenmanagerstatus kann zu einem älteren wartenden Identitätswert gehören.
Deshalb darf weder der letzte Cachewert noch eine bloß gleiche Frame-/Zeitnähe
ungeprüft verwendet werden. `observe_portal_plan()` ist vorhanden, akzeptiert
aber absichtlich nur `INSUFFICIENT`-Kandidaten und verändert den Regionsgraphen
nicht.

**Aktivierung und Parameter:** WE-M2/AQ ergänzt
`region_graph_shadow_connected_portals_enabled: false`. `true` ist nur zusammen
mit aktivem Schatten, aktivierter Rohkartenkorrelation und positiver Kapazität
zulässig. Zusätzlich sind ausschließlich Analyse-Clearance,
Kandidatenunsicherheit und ein positiver Retry-Grenzwert eigene
Schattenparameter. Flächen-, Lücken-, Auslauf- und Seed-Grenzen werden aus den
bereits validierten reinen Portalgeometriegrenzen gelesen; dies erteilt keine
Fahrerlaubnis und ändert deren Werte nicht. Ohne den dritten Opt-in werden
weder Cache-/Korrelationsbesitz noch TF, Detektor, Digest oder Portalfeed
ausgeführt.

**Cache und Reihenfolge:** Unter der vorhandenen Schatten-Sperre hält der Node
höchstens ein Paar aus unveränderlich referenzierter letzter Raw-Map-Nachricht
und genau der außerhalb der Sperre berechneten `RawMapPortalSource`, außerdem
höchstens eine letzte emittierte `PortalSourceCorrelation`, ihren Retryzähler
und den zuletzt abgeschlossenen Korrelationsschlüssel. Beide vorhandenen
Callbacks übernehmen eine nichtleere Korrelation aus dem Lebenszyklus. Ein
Kandidat darf erst berechnet werden, wenn Cache-Identität und Korrelation in
Fingerprint, Quellstempel und Frame exakt übereinstimmen. Ein erwartetes
asynchrones Nichtpassen wartet auf das nächste Paar und ist kein Schattenfehler.

**Sperr- und Retryregel:** Der 1-Hz-Schatten-Timer stößt vor seiner
Statusprojektion höchstens einen Versuch an. Er kopiert das passende Paar unter
der Sperre, gibt sie frei und liest erst dann Roboterpose, Rasterzellen und den
WE-M2/AO-Adapter. Fehlende Pose verbraucht genau einen der konfiguriert
begrenzten Versuche; bis dahin bleibt die Quelle sichtbar `missing`. Nach
Erschöpfung wird nur der Schattenpfad dauerhaft fail-closed gesetzt. Digest,
NumPy/SciPy-Detektion und TF laufen nie unter der Sperre. Vor
`observe_portal_plan()` wird unter der Sperre geprüft, dass Korrelation und
Cachepaar noch exakt dieselben Objekte/Identitäten sind; ein inzwischen neueres
Paar verwirft das berechnete Ergebnis ohne Mutation. Alle Kandidaten eines
Snapshots erhalten denselben danach gelesenen monotonen Zeitpunkt. Exaktes
Replay wird vom Lebenszyklus idempotent behandelt, ein abgeschlossenes Paar
nicht erneut detektiert.

**Fehlergrenze:** Ungültige exakt passende Kartendaten, Adapterfehler,
Zeitkonflikt oder Lebenszyklusfehler sperren ausschließlich den Schatten bis
zum Neustart. Erwartete Reihenfolgeabweichung, noch fehlender Kartenstatus und
ein während der Berechnung fortgeschriebener Cache sind Wartesituationen. Der
bestehende Explorerstatus, Actionserver, Nav2-Client, Twist-Publisher,
Costmap-Portalplan und Frontierstrategie lesen keinen neuen Zustand.

**Geänderte Dateien / Prüfplan für WE-M2/AQ:** Nur `explore_node.py`,
`explore_params.yaml`, `test_explore_contract.py` und STATUS.md. Zu prüfen sind
OFF-Nullkostenpfad, ungültige Aktivierung, beide Join-Reihenfolgen, exakt
gepaartes Cacheobjekt, Digest/Detektor außerhalb der Sperre, Pose-Retry und
-Erschöpfung, Cachewechsel während Berechnung, idempotentes Replay,
Schattenfehlerisolation, unveränderte ROS-Schnittstellen sowie ein synthetischer
ROS-Smoke ohne Action. Danach vollständige Suiten, temporärer Build und
statische Prüfungen. Keine Geräte, realen Karten, Navigation oder Bewegung.

**Rückfall:** WE-M2/AP ändert ausschließlich diese STATUS.md. Für WE-M2/AQ ist
der sofortige Rückfall der neue dritte Parameter `false`; vollständig werden
die vier Dateien des einzelnen Commits zurückgenommen. Bestehender Schatten,
Explorer und Fahrpfad bleiben dabei erhalten.

**Eigene Prüfung:** Die bestehenden Callback-, Rohkarten-, Adapter- und
Lebenszyklusverträge wurden quellenbasiert gelesen; ihre vier relevanten
Testdateien bestanden gemeinsam mit **192 passed**, `git diff --check` bestand.
Keine ROS-Nodes, Geräte, Karten, Bags, Actions oder Bewegung wurden gestartet.
Dies ist keine Runtime-, Zielsystem- oder Hardwareabnahme.

**Nächster abgegrenzter Schritt WE-M2/AQ:** Nur diesen dritten Opt-in-Feed samt
Vertragstests umsetzen. Keine Frontier-, Qualifikations-, Graph-, Ziel- oder
Fahrintegration.

### 2026-09-14 – WE-M2/AO: korrelierte Rohkarten-Portalkandidaten

**Umfang:** Neu sind `explore/raw_map_portal_adapter.py`, sein reiner Test und
dieser Statusnachtrag. Das Modul hat keine ROS-, Node-, Uhr-, Dateisystem-,
Planner-, Navigations- oder Aktorabhängigkeit. Explorer-Node, Parameter,
Launch, Actionloop, Costmap-Portalpfad, Frontierlogik, Statusschema und
Fahrsoftware bleiben unverändert.

**Vertrag:** `correlated_connected_portal_candidates()` erhält eine bereits
belegte `PortalSourceCorrelation` sowie vollständige explizite Felder und
Zellen genau des verwendeten Rohkartensnapshots. Die gemeinsame
Zellnormalisierung und Fingerprintimplementierung werden erneut auf diesen
Zellen ausgeführt. Nur bei exakter Übereinstimmung von Fingerprint,
Quellstempel und Frame geht die Verarbeitung weiter. Der Ursprung muss eine
endliche, normierte planare Pose sein; Roboter-Weltposition und Raster werden
damit gegenseitig transformiert. Eingaben bleiben unverändert.

Der verbundene Clearance-Detektor erzeugt weiterhin nur Geometrie. Für jede
Brücke entsteht eine stabile ASCII-ID als SHA-256 über die versionierte
Detektorart, exakte Quellenidentität und vier Rasterendpunkte. Empfangszeit und
Listenposition gehen nicht ein. Kontext und Revision stammen ausschließlich
aus der Korrelation; Unsicherheit ist ein expliziter Eingang. Ausgegeben wird
ein unveränderliches Tupel bestehender `PortalPlanCandidate`s. Deren bestehende
Normalisierung setzt ausnahmslos
`PortalStructuralEvidence.INSUFFICIENT`: keine Bestätigung, Durchfahrt,
Graphverbindung, Zielwahl oder Bewegung.

**Nachweise:** Exaktes Replay liefert bytegleiche Kandidaten-IDs. Gepolstertes
Kartenwachstum und eine um 90 Grad gedrehte Rasterdarstellung erzeugen mit
ihren eigenen Identitäten/Revisionen unterschiedliche Beobachtungs-IDs, aber
metrisch gleiche Portalachsen und deshalb dieselbe Portalgedächtnis-ID.
Stempel-, Frame-, Zell- oder Korrelationsfingerprintabweichung, nichtplanare
oder nichtnormierte Orientierung sowie ungültige Unsicherheit/Detektorgrenzen
schlagen vor Ausgabe geschlossen fehl. Eine Roboterposition außerhalb des
exakten Rasters liefert ausdrücklich ein leeres Tupel.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble nur als
Build-/Test-Underlay; keine ROS-Nodes, Geräte, realen Karten, Bags, Actions oder
Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AO-FOCUS | Exaktkorrelation, Replay, Wachstum/Rotation, Identität und Negativgrenzen: **12 passed**. |
| WE-M2AO-EXPLORER | Vollständige Explorer-Suite: **550 passed**. |
| WE-M2AO-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **691 passed**. |
| WE-M2AO-COLCON | Frischer temporärer Build von `amadeus_map_identity` und `explore`; **36 + 550 = 586 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AO-STATIC | `compileall`, `flake8` mit den projektüblichen Ausnahmen E501/W503 sowie `git diff --check`: bestanden. |

Dies ist reine synthetische Softwareevidenz, keine Runtime-, Jetson- oder
Hardwareabnahme und keine Fahrfreigabe.

**Rückfall:** Den einzelnen WE-M2/AO-Commit zurücknehmen oder seinen PR
schließen. Das neue Modul besitzt keinen Produktionsaufrufer; frühere Schritte
und der Betriebszustand bleiben unverändert.

**Nächster abgegrenzter Schritt WE-M2/AP:** Nur Cache-, Korrelation-, Pose-,
Retry- und Sperrbesitz für eine spätere doppelt opt-in Node-Zuführung festlegen.
Noch keine Node-, Parameter-, Frontier-, Ziel- oder Fahränderung.

### 2026-09-14 – WE-M2/AN: Runtime-Zuführungsnaht nach Szenarioabschluss

**Geprüfter Bestand:** Erneut gelesen wurden `ExploreNode` einschließlich
Karten-/Costmap-Callbacks, `_detect_frontiers()`, `_portal_plans()` und
Actionloop, die Parameter-/Node-Verträge, `portal_planning`,
`portal_plan_adapter`, `portal_source_adapter`,
`RegionGraphShadowLifecycle` und deren Tests. Die früheren
Provenienzentscheidungen WE-M2/U bis AE bleiben gültig.

| Pfad | Vorhandene Funktion | Fehlende Runtime-Voraussetzung |
|---|---|---|
| Rohkarte `/map` | Der normale Explorer hält Nachricht und monotone Empfangszeit. Der doppelt opt-in Schattenpfad berechnet außerhalb seiner Sperre die gemeinsame Identität und joint Fingerprint, Quellstempel und Frame beidseitig gegen den Kartenmanagerstatus. | Der Node verwirft den optional zurückgegebenen `PortalSourceCorrelation`; der Lebenszyklus speichert weder korreliertes Raster noch eine für Detektoren abrufbare Korrelation. Ein späterer „letzter“ Snapshot dürfte deshalb nicht nachträglich der letzten Revision zugeschrieben werden. |
| Verbundener Rohkartendetektor | `find_connected_clearance_portals()` ist rein, synthetisch geprüft und verändert die Karte nicht. | Kein Node-Aufrufer, keine erneute Bindung der tatsächlich verwendeten Zellen an die exakte Korrelation, keine stabile Beobachtungs-ID und keine metrische Origin-/Yaw-Umrechnung für den Runtimekandidaten. |
| Bestehender Costmap-Portalplan | `_portal_plans()` erzeugt im Actionloop begrenzte `PortalPlan`s aus genau einer frischen Nav2-Master-Costmap und verwendet sie weiterhin für die vorhandene Fahrstrategie. | Master-Costmap und `PortalPlan` tragen weiterhin keine Rohkartenidentität/Managerrevision. Dieser Pfad bleibt gemäß WE-M2/U für den Schatten gesperrt und darf nicht durch „zuletzt gesehen“ korreliert werden. |
| Schattenlebenszyklus | `observe_portal_plan()` akzeptiert nach Sitzungsstart einen expliziten `PortalPlanCandidate`, hält ihn immer `insufficient` und führt Portalalter replayfest. | Der Node importiert/ruft diese API absichtlich nicht auf. Es gibt deshalb noch keine passive Portalzuführung, aber auch keinen Einfluss auf Graph, Ziele oder Fahrt. |
| Frontiers | `_detect_frontiers()` liefert globale Zentren/Größen aus der aktuellen Rohkarte; `_rank_frontiers()` und Besuchslisten dienen ausschließlich der Action-Strategie. | Frontier besitzt keine stabile ID, Kartenrevision oder Schatten-Task-API. Nur Kandidaten oder gerankte Teilmengen einzuspeisen würde die globale Sicht verlieren. Diese Naht bleibt nach dem Portalkandidaten separat zu entwerfen. |

**Entscheidung für den kleinsten nächsten Schritt:** Noch keine Node-Anbindung.
Zuerst wird ein einziges ROS-freies Adaptermodul benötigt. Es erhält die
vollständigen Rohkartenfelder und Zellen, die Roboterposition im Kartenframe,
explizite Detektorgrenzen/Unsicherheit und genau die zuvor vom Exaktjoin
gelieferte `PortalSourceCorrelation`. Das Modul bildet mit der gemeinsamen
Fingerprintquelle erneut die Identität genau der verwendeten Zellen und muss
Fingerprint, Stempel sowie Frame gegen die Korrelation prüfen, bevor es den
verbundenen Detektor aufruft. Dadurch kann kein zwischenzeitlich neuer Cachewert
einer alten/neuen Revision zugeschrieben werden.

Rasterendpunkte werden unter validiertem planarem Ursprung/Yaw metrisch
normalisiert. Eine stabile Beobachtungs-ID wird deterministisch aus einer
versionierten Detektorart, exakter Quellenidentität und kanonischer
Portalgeometrie gehasht; Listenpositionen und Empfangszeit sind verboten. Die
Ausgabe ist ein unveränderliches Tupel bestehender `PortalPlanCandidate`s mit
Kontext/Revision aus der Korrelation und expliziter Unsicherheit. Der bestehende
Adapter stuft sie weiterhin ausschließlich `INSUFFICIENT` ein. Keine
Costmap-Erreichbarkeit, Strukturqualifikation, Durchfahrt, Graphverbindung,
Navigation oder Bewegung gehört in diesen Schritt.

**Betroffene Dateien für WE-M2/AO:** Ein neues Modul unter
`src/explore/explore/`, seine neue reine Testdatei und diese STATUS.md. Explorer-
Node, Parameter, Launch, bestehende Portalplanung, Actionloop, Kartenmanager,
Frontierlogik, Statusschema und Fahrsoftware bleiben unverändert.

**Prüfplan WE-M2/AO:** Identischer Snapshot/Detektoroutput liefert bytegleiche
IDs; Kartenwachstum und 90°-Rasterrotation liefern metrisch passende Kandidaten
mit jeweils korrekter Revision; Fingerprint-/Stempel-/Frame-/Zellabweichung,
ungültige Geometrie, nichtplanare oder nichtnormierte Orientierung,
Roboterposition außerhalb der Karte und Grenzwertfehler schlagen vor jeder
Ausgabe geschlossen fehl oder liefern den ausdrücklich spezifizierten leeren
Detektorbefund. Danach fokussierte Adapter-/Portal-/Quelltests, komplette
Explorer-/angrenzende Suiten, temporärer Build und statische Prüfungen. Keine
ROS- oder Geräteprüfung.

**Ausgeführte Bestandsprüfung:** Die sechs relevanten unveränderten Testdateien
für Explorervertrag, Portalplanung, Plan-/Quelladapter, Schattenlebenszyklus und
kombinierte Szenarien bestanden gemeinsam mit **220 passed**. `git diff --check`
bestand. Keine ROS-Nodes, Geräte, Karten, Bags, Actions oder Bewegung wurden
gestartet; dies ist keine Runtime-, Zielsystem- oder Hardwareabnahme.

**Rückfall:** WE-M2/AN ändert nur diese STATUS.md. Den einzelnen
Dokumentationscommit zurücknehmen oder den PR schließen; kein Betriebszustand
ist zurückzusetzen.

**Nächster abgegrenzter Schritt WE-M2/AO:** Genau den beschriebenen reinen
Rohkarten-Kandidatenadapter samt Tests implementieren. Keine Node-, Parameter-,
Frontier-, Ziel- oder Fahränderung.

### 2026-09-14 – WE-M2/AM: kombiniertes Kartenänderungsszenario

**Abgrenzung:** Nur `src/explore/test/test_region_scenarios.py` und diese
STATUS.md wurden ergänzt. Produktionsmodule, Runtime, Parameter, Launch,
Navigation, Zielwahl, Fahrsoftware und Sicherheitskonfiguration bleiben
unverändert.

**Nachgewiesener Ablauf:** Derselbe synthetische Raum–Flur-Kartenausschnitt
wird zunächst im Basisraster detektiert, dann oben/links mit unbekannten Zellen
vergrößert und schließlich um 90 Grad gedreht. Die Fixture deklariert für jede
Darstellung Auflösung, Ursprung und Yaw und transformiert ausschließlich die
jeweiligen Detektorendpunkte in den gemeinsamen metrischen Kartenframe. Die
resultierenden vier Koordinaten stimmen bis auf Rundungsgenauigkeit überein.
Drei qualifizierte Revisionen werden deshalb deterministisch demselben
`portal_000001` zugeordnet; Startregion `region_000001`, gesehener Flur
`region_000002` und `task-map-change` bleiben vor der Korrektur stabil.

Die anschließende simulierte Kartenkorrektur ist kein Detektorschluss: Ein
expliziter Fixture-Merge vereinigt die beiden vorläufigen Regionen, danach
partitioniert ein expliziter Fixture-Split die beiden Portalenden erneut. Der
neue Korrekturstand ist `region_000003`; der historische Flur bleibt Alias der
Startregion. Portal-ID, offene Aufgaben-ID, Aufgabenstatus und bestätigter
Eintritt bleiben erhalten, die Aufgabe folgt vollständig der deklarierten
Splitpartition. Bytegleiche Vergleiche belegen außerdem, dass Detektor und
Fixture Basis-, Wachstums- und Rotationsraster nicht verändern.

Mit WE-M2/AJ bis AM sind damit alle in WE-M2 verlangten kombinierten
Geometriefälle lokal abgedeckt: Startraum–Flur–Zimmer, derselbe Flur bei
Rückkehr, verbundene Türen, L-Flur/Schleife, offener Wohnbereich,
Möbelunterteilung, Kartenwachstum/Origin-Rotation/Korrektur, gesehen ohne
Eintritt sowie Split/Merge ohne Aufgabenverlust. Dies ersetzt nicht die noch
fehlende passive Runtimezuführung oder Zielsystemabnahme.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble nur als
Build-/Test-Underlay; keine ROS-Nodes, Geräte, realen Karten, Bags, Actions oder
Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AM-SCENARIOS | Alle fünf kombinierten Szenarien: **5 passed**. |
| WE-M2AM-EXPLORER | Vollständige Explorer-Suite: **538 passed**. |
| WE-M2AM-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **679 passed**. |
| WE-M2AM-COLCON | Frischer temporärer Build von `amadeus_map_identity` und `explore`; **36 + 538 = 574 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AM-STATIC | `compileall`, `flake8` mit den projektüblichen Ausnahmen E501/W503 sowie `git diff --check`: bestanden. |

Diese synthetischen Softwaretests sind keine Jetson-, Runtime- oder
Hardwareabnahme und keine Fahrfreigabe.

**Rückfall:** Den einzelnen WE-M2/AM-Commit zurücknehmen oder seinen PR
schließen. Dadurch entfallen nur ein Test und der Statusnachtrag; frühere
Schritte und Produktionsverhalten bleiben unverändert.

**Nächster abgegrenzter Schritt WE-M2/AN:** Nur die inzwischen erreichte
Abdeckung gegen die tatsächlichen Explorer-Runtime-Nähte auditieren und den
kleinsten passiven Frontier-/Portal-Zuführungsschritt festlegen. Noch keine
Funktionsänderung, kein Deployment und keine Geräteprüfung.

### 2026-09-14 – WE-M2/AL: kombiniertes L-Flur-/Schleifenszenario

**Abgrenzung:** Nur `src/explore/test/test_region_scenarios.py` und diese
STATUS.md wurden ergänzt. Produktionsmodule, ROS-/Runtimepfade, Parameter,
Navigation, Zielwahl, Fahrsoftware und Sicherheitskonfiguration sind
unverändert.

**Nachgewiesener Ablauf:** Die synthetische Belegungskarte enthält einen
horizontalen und einen vertikalen Arm desselben L-förmigen Flurs sowie je eine
schmale Tür am Anfang und Ende. Der verbundene Detektor liefert beide
Portalgeometrien. Je zwei ausdrücklich qualifizierte Strukturrevisionen und
separat bestätigte Durchfahrtsereignisse erzeugen zunächst deterministisch
`portal_000001`/`portal_000002` und drei vorläufige Regionen. Das ist noch kein
Schleifenbeweis.

Erst `explicit-loop-truth` vereinigt als ausdrücklich externer
Fixture-Wahrheitseingang `region_000003` mit `region_000001`. Der Endstand hat
genau zwei Regionen, beide Portalverbindungen zwischen Startregion und
`region_000002`, genau einen Alias und drei bestätigte Eintritte. Der
anschließende Rückweg über das zweite Portal endet wieder in `region_000002`
mit Eintrittszähler zwei. Keine vierte Region und keine neue Fluridentität
entsteht. Der Merge wird ausdrücklich nicht aus Detektor- oder Plannererfolg
abgeleitet.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble nur als
Build-/Test-Underlay; keine ROS-Nodes, Geräte, Karten, Bags, Actions oder
Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AL-SCENARIOS | Raum–Flur–Raum, Negativfälle und L-Flur/Schleife: **4 passed**. |
| WE-M2AL-EXPLORER | Vollständige Explorer-Suite: **537 passed**. |
| WE-M2AL-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **678 passed**. |
| WE-M2AL-COLCON | Frischer temporärer Build von `amadeus_map_identity` und `explore`; **36 + 537 = 573 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AL-STATIC | `compileall`, `flake8` mit den projektüblichen Ausnahmen E501/W503 sowie `git diff --check`: bestanden. |

Diese synthetischen Softwaretests sind keine Jetson-, Runtime- oder
Hardwareabnahme und keine Fahrfreigabe.

**Rückfall:** Den einzelnen WE-M2/AL-Commit zurücknehmen oder seinen PR
schließen. Dadurch entfallen nur ein Test und der Statusnachtrag; frühere
Schritte und Produktionsverhalten bleiben unverändert.

**Nächster abgegrenzter Schritt WE-M2/AM:** Nur ein kombiniertes
Kartenänderungsszenario ergänzen. Metrische Portalwahrheit, Rastertransformation
und Split-/Merge-Wahrheit bleiben getrennte Fixture-Eingaben; Produktionscode
und Runtime sind ausgeschlossen.

### 2026-09-14 – WE-M2/AK: kombinierte Negativszenarien

**Abgrenzung:** Nur `src/explore/test/test_region_scenarios.py` und diese
STATUS.md wurden ergänzt. Sämtliche Produktionsmodule, ROS-/Runtimepfade,
Parameter, Navigation, Zielwahl, Fahrsoftware und Sicherheitskonfiguration
bleiben unverändert.

**Nachgewiesene Fälle:** Ein zusammenhängender rechteckiger Freiraum liefert
keinen verbundenen Portalkandidaten; Portalgedächtnis, einzelne Startregion,
Verbindungen, Aufgaben und Eintrittszähler bleiben unverändert. Im zweiten Fall
liegt eine große synthetische Möbelinsel innerhalb desselben freien Raums. Die
Analyseerosion liefert an einem verbleibenden Weg eine geometrische Engstelle.
Die Fixture setzt dafür ausdrücklich widersprüchliche Strukturwahrheit. Das
Portalgedächtnis hält deshalb genau einen unbestätigten `uncertain`-Kandidaten,
der Graph stellt ihn zurück und erzeugt weder Verbindung noch zusätzliche
Region, Aufgabe oder Eintritt. Damit wird ein Kandidat nicht fälschlich als
Raumgrenze behandelt; seine Beobachtung wird zugleich nicht verschwiegen.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble nur als
Build-/Test-Underlay; keine ROS-Nodes, Geräte, Karten, Bags, Actions oder
Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AK-SCENARIOS | Raum–Flur–Raum plus zwei neue Negativszenarien: **3 passed**. |
| WE-M2AK-EXPLORER | Vollständige Explorer-Suite: **536 passed**. |
| WE-M2AK-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **677 passed**. |
| WE-M2AK-COLCON | Frischer temporärer Build von `amadeus_map_identity` und `explore`; **36 + 536 = 572 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AK-STATIC | `compileall`, `flake8` mit den projektüblichen Ausnahmen E501/W503 sowie `git diff --check`: bestanden. |

Dies ist nur synthetische Softwareevidenz, keine Jetson-, Runtime- oder
Hardwareabnahme und keine Fahrfreigabe.

**Rückfall:** Den einzelnen WE-M2/AK-Commit zurücknehmen oder seinen PR
schließen. Dadurch entfallen nur zwei Tests und der Statusnachtrag;
Produktionsverhalten und frühere Schritte bleiben unverändert.

**Nächster abgegrenzter Schritt WE-M2/AL:** Nur ein kombiniertes L-Flur- und
Schleifenszenario ergänzen. Ein Schleifen-Merge bleibt ein ausdrücklich
gesetzter Fixture-Wahrheitseingang und darf nicht aus Geometrie abgeleitet
werden; Produktionscode und Runtime sind ausgeschlossen.

### 2026-09-14 – WE-M2/AJ: kombiniertes Raum–Flur–Raum-Szenario

**Abgrenzung:** Ergänzt wurde ausschließlich
`src/explore/test/test_region_scenarios.py` sowie dieser Statusnachtrag.
Produktionsmodule, Explorer-Node, Parameter, Launch, Navigation, Zielwahl,
Actions, Fahrsoftware und Sicherheitskonfiguration bleiben unverändert.

**Nachgewiesener Ablauf:** Eine vollständig synthetische Rasterkarte enthält
zwei große Räume, einen schmaleren Flur und zwei gemessene Türen. Der reine
verbundene Detektor liefert die erste Tür aus dem Startraum und beide
Richtungen der zweiten Tür. Seine Rasterendpunkte werden nur in metrische
Testpunkte umgerechnet. Die Fixture setzt Strukturwahrheit ausdrücklich:
Unzureichende Geometrieevidenz bleibt Kandidat und wird vom Graphen
zurückgestellt; erst zwei separat qualifizierte Revisionen bestätigen jedes
Portal. Ebenso bleibt ein ausdrücklich unbestätigtes Durchfahrtsereignis ohne
Regionseintritt. Bestätigte Fixture-Ereignisse führen anschließend über
`region_000001` nach `region_000002` und `region_000003` und über dasselbe
zweite Portal zurück in exakt `region_000002`.

Der Endstand hält genau `portal_000001`/`portal_000002`, drei Regionen, zwei
Verbindungen, keine Aliase, drei bestätigte Eintritte und die abgeschlossene
Aufgabe `task-portal-000002`. Der zunächst nur gesehene Zielraum bleibt bis zum
expliziten Eintritt `entered=false`. Damit verbindet der Test vorhandene APIs,
ohne Struktur- oder Durchfahrtswahrheit aus Detektor- oder Plannererfolg zu
erfinden.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble nur als
Build-/Test-Underlay; keine ROS-Nodes, Geräte, Karten, Bags, Actions oder
Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AJ-SCENARIO | Kombiniertes Raum–Flur–Raum-Szenario: **1 passed**. |
| WE-M2AJ-EXPLORER | Vollständige Explorer-Suite: **534 passed**. |
| WE-M2AJ-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **675 passed**. |
| WE-M2AJ-COLCON | Frischer temporärer Build von `amadeus_map_identity` und `explore`; **36 + 534 = 570 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AJ-STATIC | `compileall`, `flake8` mit den projektüblichen Ausnahmen E501/W503 sowie `git diff --check`: bestanden. |

Diese Ergebnisse sind ein synthetischer Softwarebeleg, keine Jetson-, Runtime-
oder Hardwareabnahme und keine Fahrfreigabe.

**Rückfall:** Den einzelnen WE-M2/AJ-Commit zurücknehmen oder seinen PR
schließen. Dadurch entfallen nur Test und Statusnachtrag; Produktionsverhalten
und der separat reviewbare Detektor bleiben unverändert.

**Nächster abgegrenzter Schritt WE-M2/AK:** In derselben reinen Testdatei nur
offenen Wohnbereich und Möbelunterteilung als kombinierte Negativfälle
ergänzen. Portalgedächtnis, Graph und Aufgaben müssen darin unverändert bleiben;
Produktionscode und Runtime sind ausgeschlossen.

### 2026-09-14 – WE-M2/AI: reiner Detektor für verbundene Türen

**Freigabe und Abgrenzung:** Der Nutzer hat die in WE-M2/AH verlangte gezielte
HWT-Teilübernahme ausdrücklich bestätigt. Aus Commit `1d91229` wurden nur
`find_connected_clearance_portals()`, dessen privater Bresenham-Linienprüfer
und genau vier synthetische Tests übernommen. Explorer-Node, Parameter,
Launchdateien, Zielwahl, Actions, Geschwindigkeitsausgabe, Fahrprofile und alle
übrigen HWT-Änderungen bleiben ausgeschlossen.

**Nachgewiesene Funktion:** Der reine Detektor betrachtet ausschließlich als
frei gemessene Zellen einer zusammenhängenden Belegungskartenkomponente. Eine
nur zur Analyse erodierte Maske trennt mögliche Raumseiten; der bestehende
begrenzte Brückendetektor liefert Kandidaten. Eine Kandidatenlinie muss in der
ursprünglichen freien Komponente vollständig frei bleiben. Der Positivfall
findet eine schmale gemessene Tür zwischen zwei großen Bereichen. Negativfälle
verwerfen einen offenen Einzelraum, eine zu kleine Nische und eine trennende
Wand trotz anderweitiger Verbindung. `rg` weist als einzige Python-Verwendungen
die Funktionsdefinition und ihre Testdatei aus: Es gibt keinen Runtime-Aufrufer.

**Geänderte Dateien:** `src/explore/explore/portal_planning.py`,
`src/explore/test/test_portal_planning.py` und diese STATUS.md. Keine
Fahrsoftware, Navigation, Sicherheitsparameter, Installation oder Geräte.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble nur als
Build-/Test-Underlay; keine ROS-Nodes, Geräte, Karten, Bags, Actions oder
Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AI-FOCUS | Vollständige Portalplanung einschließlich vier neuer Fälle: **12 passed**. |
| WE-M2AI-EXPLORER | Vollständige Explorer-Suite: **533 passed**. |
| WE-M2AI-ADJACENT | Zusätzlich gemeinsames Fingerprintpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **674 passed**. |
| WE-M2AI-COLCON | Frischer temporärer Build von `amadeus_map_identity` und `explore`; **36 + 533 = 569 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AI-STATIC | `compileall`, `flake8` mit den projektüblichen Ausnahmen E501/W503 sowie `git diff --check`: bestanden. |

Die Softwaretests belegen nur die reine Geometriefunktion auf synthetischen
Rasterdaten. Sie sind weder Jetson-/Runtime-Nachweis noch Hardwareabnahme und
erteilen keine Fahrfreigabe.

**Rückfall:** Den einzelnen WE-M2/AI-Commit zurücknehmen oder seinen PR
schließen. Da die neue Funktion keinen Produktionsaufrufer hat, entsteht ohne
spätere gesonderte Integration keine Runtimewirkung.

**Nächster abgegrenzter Schritt WE-M2/AJ:** Nur eine kombinierte synthetische
Testszenario-Datei für Startraum–Flur–Zimmer und Rückkehr ergänzen. Geometrie,
Strukturqualifikation und Durchfahrtswahrheit bleiben darin sichtbar getrennte
Fixture-Eingaben; Produktions-APIs und Runtime werden nicht geändert.

### 2026-09-14 – WE-M2/AH: kombinierte Szenarien und HWT-Naht inventarisiert

**Bestandsabgleich:** Geprüft wurden die aktuellen reinen Schnittstellen und
Tests von `portal_planning`, `portal_memory`, `portal_plan_adapter`,
`portal_source_adapter`, `region_graph`, `region_graph_shadow` und
`region_graph_shadow_lifecycle` sowie der HWT-Stand `1d91229`. Die heutige
Abdeckung gegenüber den WE-M2-Pflichttests ist:

| WE-M2-Szenario | Bereits belegte Teilfunktion | Fehlender kombinierter Nachweis |
|---|---|---|
| Startraum–Flur–Zimmer und Flurrückkehr | `test_start_room_hall_room_and_return_reuse_the_same_hall_region` führt zwei bestätigte Portale, drei Regionen und die Rückkehr in exakt denselben Flur. | Portale sind direkt als qualifizierte Wahrheit erzeugt; keine synthetische Kartengeometrie oder Detektorausgabe fließt ein. |
| Verbundener Freiraum mit offenen Türen | HWT `find_connected_clearance_portals()` erkennt eine gemessene schmale Tür und verwirft offenen Einraum, kleine Nische und Wand mit Umweg. | Funktion und vier Tests fehlen auf der aktuellen gestapelten Basis; keine Verbindung zu Portalgedächtnis/Graph. |
| L-Flur und Schleife | Graph-Merge rewritet Topologie, Traversals und Aliase deterministisch; Rückweg über eine umgeschriebene Verbindung ist getestet. | Keine L-förmige Rasterfixture, keine Detektorfolge und kein geometrisch geschlossener Portalring. |
| Offener Wohnbereich | `test_open_area_without_confirmed_portal_remains_one_region` verhindert eine erfundene zweite Region; Merge kann Teilregionen wieder vereinigen. | Kein Detektor-Negativfall auf dieser Basis und keine gemeinsame Geometrie-/Graphfixture. |
| Möbelunterteilung | Portalgedächtnis bestätigt wiederholte Möbelengstellen ohne qualifizierte Strukturevidenz niemals. HWT verwirft eine kleine Nische. | HWT-Negativdetektor fehlt; keine kombinierte Prüfung, dass Graph und Aufgabenbestand unverändert bleiben. |
| Kartenwachstum, Ursprungsrotation und Korrektur | Kartenstatus korreliert Wachstum; Portalgedächtnis prüft metrische Normalisierung und Achsrotation; Graph prüft Merge/Split. | Kein einziger Ablauf bindet dieselben Wahrheitsportale und Aufgaben über geänderten Wire-Snapshot, Ursprung und Korrektur hinweg. |
| Raum gesehen, nicht betreten | Eine bestätigte Portalverbindung erzeugt die Gegenseite `seen=true`, `entered=false`; eine unbestätigte Durchfahrt ändert weder Region noch Eintritt. | Noch nicht gemeinsam aus einer Detektorfixture und expliziter Traversalwahrheit geprüft. |
| Split/Merge ohne verlorene Aufgaben | Expliziter Split partitioniert Portalenden, Zustände und Aufgaben atomar; anschließender Merge stellt eine Region ohne Referenzverlust her. | Kein vorgeschalteter geometrischer Korrekturfall; Split-/Merge-Entscheidung bleibt wie vorgesehen externer Wahrheitseingang. |

Die Einzelnachweise sind belastbare Modultests, aber kein Ersatz für die
geforderte kombinierte Szenariomatrix. Besonders wichtig: `PortalBridge`
enthält Rasterendpunkte und Kosten-/Flächengrößen, aber keine Kartenidentität,
Strukturevidenz oder stabile Portal-ID. `PortalPlanCandidate` trägt metrische
Endpunkte und Revision, wird jedoch absichtlich nur als
`PortalStructuralEvidence.INSUFFICIENT` normalisiert. Der Schattenbesitzer
besitzt ausdrücklich keine API zum Qualifizieren, zum Bestätigen einer
Durchfahrt oder zum Anwenden von Split, Merge und Aufgaben. Deshalb können
Portalpläne heute keine Graphverbindung erzeugen; dies fail-closed zu umgehen
wäre eine neue Gesamtlösung, nicht eine Testfixture.

**HWT-Abhängigkeit:** Auf `origin/codex/hwt601-encoder-shadow` ergänzt Commit
`1d91229` den reinen `find_connected_clearance_portals()` in
`src/explore/explore/portal_planning.py` und vier zugehörige Fälle in
`src/explore/test/test_portal_planning.py`. Gegen Main umfasst die reine
Zweidateien-Teilmenge 112 hinzugefügte/geänderte Quell- und 54 Testzeilen
(insgesamt 162 Diff-Zeilen einschließlich kleiner Modultextänderungen) und
verwendet nur bereits vorhandene NumPy-/SciPy-Funktionen. Sie erodiert nur eine
Analysemaske, lässt die reale Karte/Costmap unverändert und gibt ausschließlich
`PortalBridge`-Geometrie zurück.

Der vollständige HWT-Commit verändert dagegen 12 Dateien mit 1.875
Einfügungen, darunter Explorer-Node, Fahrprofile, Portalpriorität und
Türdurchfahrt. Diese funktionale Gesamtheit ist weder nötig noch als Teil von
WE-M2/AH zulässig. Eine gezielte Übernahme darf daher ausschließlich die reine
Funktion und ihre vier Tests betreffen. Auch diese Übernahme ist gemäß
Agentenauftrag vorab ausdrücklich abzustimmen, weil sie aus dem divergenten
HWT-Zweig stammt.

**Kleinste Fixture-Naht danach:** Erst nach dem reinen Detektorschritt soll
eine einzelne neue Testdatei synthetische Wahrheitsfälle komponieren. Sie darf
Detektorresultate in metrische Testpunkte umrechnen, muss
Strukturqualifikation und Traversalentscheidung aber ausdrücklich als getrennte
Fixture-Wahrheit markieren. Sie darf diese Belege weder aus Geometrie noch aus
einem Nav2-Ergebnis erfinden. Erwartete Portal-, Regions-, Alias-, Aufgaben- und
Eintritts-IDs werden pro Revision vollständig festgehalten. Produktionsmodule
erhalten dafür zunächst keine neue API.

**Geänderte Dateien / Prüfung:** Nur diese STATUS.md. Verglichen wurden die
oben genannten aktuellen Tests und APIs, der reine HWT-Diff sowie dessen
Einbettung im Gesamtcommit. Die sieben betroffenen reinen Testdateien bestanden
gemeinsam mit **324 passed**; `git diff --check` bestand. Es wurden keine
ROS-Nodes, Geräte, Karten, Bags, Aktoren oder Fahrpfade gestartet; dies ist
keine Softwareübernahme, Lastmessung, Jetson- oder Hardwareabnahme.

**Rückfall:** Den einzelnen WE-M2/AH-Dokumentationscommit zurücknehmen. Keine
Runtime-, Installations- oder Gerätewirkung.

**Nächster abgegrenzter Schritt WE-M2/AI, nur nach ausdrücklicher Zustimmung:**
Aus HWT `1d91229` ausschließlich `find_connected_clearance_portals()` samt
privatem Bresenham-Helfer und genau den vier Positiv-/Negativtests in die
aktuelle gestapelte Basis übertragen. Prüfplan: vier fokussierte Fälle,
vollständige Portalplanung, gesamte Explorer-Suite, angrenzende Pakete,
temporärer Build und statische Prüfungen. Rückfall: dieser eine reine Commit;
die Funktion bleibt ohne Node-Aufruf ohnehin ohne Runtimewirkung. Keine
Explorer-Node-, Konfigurations-, Launch-, Ziel-, Command- oder Fahränderung.

### 2026-09-14 – WE-M2/AG: gerätefreier Rohkarten-Lastprüfer

**Entscheidung / Umfang:** Der eigenständige Helfer
`tools/kartierung/rohkarten_schatten_lasttest.py` führt ausschließlich einen
synthetischen Publisher/Beobachter und je Matrixfall einen frischen Explorer
aus. Er setzt die gewählte `ROS_DOMAIN_ID` vor `rclpy`, akzeptiert nur Domains
0 bis 232 und beobachtet die Domain vor jedem Kindstart zwei Sekunden lang
durchgehend. Jeder fremde Node bricht den Lauf ab. Der Explorer wird wie beim
vorhandenen synthetischen SLAM-Test als direkt aufgelöstes installiertes
Programm gestartet, nicht über `ros2 run`; so erreicht SIGINT genau das Kind.
Die installierte Parameterdatei muss zuvor beide WE-M2/AE-Sperrdefaults
enthalten, sonst wird ein veraltetes Overlay abgelehnt.

Karte, Kartenmanager- und Schattenstatus sowie alle unbenutzten Odometrie-,
Scan-, Command-, Nav-Action-, Explore-Action- und Visualisierungsschnittstellen
sind je Fall auf einen privaten Testpräfix gelegt. Der Helfer startet keinen
Kartenmanager, SLAM-, Nav2-, Missions-, Sensor- oder Hardwareknoten, sendet
keine Action und publiziert keinen Twist. Kartenwerte und Ursprungsdaten werden
deterministisch im Speicher erzeugt; reale Karten, Bags und Wohnungsgeometrie
werden nicht gelesen oder geschrieben.

Der passende synthetische Managerstatus entsteht erst aus der eigenen, über DDS
zurückempfangenen `OccupancyGrid`-Nachricht. Damit wird insbesondere die
float32-Wire-Auflösung statt des Python-Ausgangsliterals gehasht. Je Fall wird
zuerst ein Exaktjoin erzeugt, danach werden Kapazität plus zwei eindeutige
unpassende Quellen sowie explizite Duplikate angeboten. Die erwartete
Zählererhaltung, volle Warteschlange und genau zwei Verdrängungen sind harte
Erfolgskriterien.

CLI-Grenzen beschränken Zellzahl auf 4.000.000, Kapazität auf 32,
Wiederholungen auf 20, Matrix auf 12 Fälle, Intervall und Fall-/Gesamtdauer
sowie das Ergebnis-JSON auf 65.536 Byte. Ausgegeben werden nur Aggregate,
keine Rohzellen, Fingerprints oder Geometrie. Factoryzeiten stammen aus dem
zurückempfangenen Wire-Snapshot. Die externe Joinstatuslatenz enthält den
1-Hz-Schattenstatus-Timer und ist weiterhin keine interne Callbackzeit. RSS
wird ohne neue Abhängigkeit aus `/proc/<explorer-pid>/status` abgetastet und ist
Prozess-RSS, nicht exklusiver Python-Heap.

**Geänderte Dateien:** Der neue Helfer, sein reiner Vertragstest unter
`tools/kartierung/` und diese STATUS.md. Explorer, gemeinsames
Fingerprintpaket, Kartenmanager, Launchdateien, installierte Standards,
Detektoren, Graphlogik, Navigation, Fahrsoftware und Sicherheitsparameter sind
unverändert.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble,
maßgeblicher Installationsstand nur als Underlay gelesen und WE-M2/X plus
WE-M2/AE in `/tmp/we-m2ag-colcon.gORVLq` gebaut. Keine Geräte, realen Karten,
Bags, Actions oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AG-TOOL | Domain-, CLI-/Matrix-, Wire-Roundtrip-, Digeststatus-, Zähler-, Topic-, Ausgabe- und Einzelsignalverträge: **9 passed**. |
| WE-M2AG-SOURCE | Helfertests plus gemeinsames Fingerprintpaket und vollständige Explorer-Suite: **574 passed**. |
| WE-M2AG-ADJACENT | Zusätzlich Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **679 passed**. |
| WE-M2AG-BUILD | Temporärer isolierter Build von `amadeus_map_identity` und `explore`: **2 Pakete gebaut**. |
| WE-M2AG-STATIC | `compileall`, `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |
| WE-M2AG-MATRIX | Endstand in Domain 214; Kanten 64/256/512, Kapazitäten 1/4, je drei Duplikate: **6/6 Fälle bestanden**, 65,88 s gesamt einschließlich je 2 s Isolationsprüfung. Jeder Fall: ein Exaktjoin, Wartespitze gleich Kapazität, genau zwei Verdrängungen und drei Duplikate. |
| WE-M2AG-MAX | Endstand in Domain 213; 2000×2000 = **4.000.000 Zellen**, Kapazität 1, ein Duplikat: bestanden in 11,05 s gesamt einschließlich Isolationsprüfung; ein Exaktjoin, Wartespitze 1, zwei Verdrängungen. |

In der finalen Sechs-Fall-Matrix lagen die Wire-Factory-Mediane zwischen 0,233
und 2,632 ms; über alle Fälle reichten die Einzelwerte von 0,216 bis 7,049 ms.
Die externe Joinstatuslatenz lag erwartungsgemäß zwischen 998,1 und 1000,3 ms.
Der höchste beobachtete Explorer-RSS betrug 73.596.928 Byte; der größte Anstieg
von Start zu Spitze 5.181.440 Byte. Im finalen Vier-Millionen-Zellen-Fall
betrugen Factory-Minimum/Median/Maximum 19,59/25,49/30,70 ms, die
Joinstatuslatenz 997,1 ms und der RSS Start/Spitze/Ende
69.132.288/104.996.864/98.209.792 Byte. Das sind lokale Messwerte, keine
eingefrorenen Produktionsgrenzen und keine Jetson- oder Hardwareabnahme.

Ein erster Buildaufruf endete vor jedem ROS-Start wegen der lokal erforderlichen
Position von `--log-base` vor dem `build`-Unterbefehl. Der erste Explorerstart
danach fand ohne vollständig gesourctes Workspace-Underlay die generierten
`robot_interfaces` nicht. Nach dem rein lesenden Sourcen des vorhandenen
Underlays wurde als zweite fehlende Voraussetzung der absichtlich verpflichtende
Recovery-freie Behavior Tree sichtbar. Der Helfer übergibt ihn nun explizit.
Ein erfolgreicher Einzelfall zeigte anschließend, dass `ros2 run` SIGINT nicht
an sein Kind weitergibt; entsprechend der bereits dokumentierten
Kartierungsfalle wird nun das aufgelöste Explorerprogramm direkt gestartet.
Nach jedem Versuch wurden die konkreten Kindprozesse beendet; es blieb kein
Testnode zurück.

**Rückfall:** Den einzelnen WE-M2/AG-Commit zurücknehmen. Der Helfer ist nicht in
Launch, Installation oder CI eingebunden und verändert keine Runtime. Temporäre
Buildartefakte liegen ausschließlich unter `/tmp`; Geräte-, Karten- und
Installationszustand blieben unverändert.

**Nächster abgegrenzter Schritt WE-M2/AH:** Die verbleibenden WE-M2-Pflichttests
Startraum–Flur–Zimmer, verbundener Freiraum mit offenen Türen, L-Flur/Schleife,
offener Wohnbereich, Möbelunterteilung, Kartenwachstum/-rotation/-korrektur,
Betrachten ohne Eintritt, Flurrückkehr sowie Split/Merge mit Aufgaben anhand der
heutigen reinen Detektor-, Portalgedächtnis- und Graphtests inventarisieren.
Nur fehlende kombinierte Wahrheitsfixtures und ihre kleinste API-Naht
spezifizieren; noch keine Implementierung, Runtime, Zielwahl oder Fahrt.

### 2026-09-14 – WE-M2/AF: synthetischen Rohkarten-Lastprüfer abgegrenzt

**Quellen- und Werkzeugbefund:** Die WE-M2-Abnahme fordert begrenzte Laufzeit
und begrenzten Speicher bei wachsender synthetischer Karte. Die Strategie
fordert relevante Kartenereignisse, begrenzte Puffer und kontrollierte
Ausführung statt Vollanalyse in jedem LiDAR-Callback. Der bestehende
`tools/kartierung/test_reine_drehung_synthetisch.py` setzt seine eigene
`ROS_DOMAIN_ID` vor dem ersten `rclpy`-Import, nennt den Hardwareausschluss,
begrenzt Dauer und Eingaben, schreibt Kindprozessausgabe in eine temporäre Datei
und beendet nur den konkreten Prozess per SIGINT. Die lesenden Kartenwerkzeuge
geben begrenzte, sortierte JSON-Metriken aus. Diese Konventionen sind für den
neuen Prüfer zu übernehmen.

Kein vorhandenes Werkzeug misst die passive Rohkartennaht, Digestkosten,
Joinlatenz oder den RSS des Explorerprozesses. Im Repository wird weder
`psutil` noch `tracemalloc` oder `resource.getrusage()` für vergleichbare
Prozessmessungen verwendet. Der Prüfer benötigt deshalb keine neue Abhängigkeit:
Zeitmessung erfolgt mit `time.perf_counter_ns()`, der Linux-RSS wird während des
begrenzten Laufs aus genau `/proc/<explorer-pid>/status` abgetastet. Der Wert ist
als Prozess-RSS und nicht als exklusiver Python-Heap zu bezeichnen.

**Festgelegter Helfervertrag:** Der nächste Schritt ergänzt genau
`tools/kartierung/rohkarten_schatten_lasttest.py` und
`tools/kartierung/test_rohkarten_schatten_lasttest.py`. Das Programm setzt eine
vom Aufrufer wählbare, gültige und standardmäßig reservierte Testdomain vor
`rclpy`, startet ausschließlich das direkt aufgelöste installierte
Explorerprogramm mit beiden Schatten-Opt-ins, expliziter Joinerkapazität und
privaten Karten-, Managerstatus- und Schattenstatustopics. Es startet weder
Kartenmanager, SLAM, Nav2,
Missionsmanager, Sensor- noch Hardwareknoten und sendet keinen Actionauftrag
oder Twist. Vor dem Lastlauf muss die Domain außer dem Prüfer und dem von ihm
gestarteten Explorer leer sein; fremde Knoten führen fail-closed zum Abbruch.

Ein kombinierter Publisher/Beobachter publiziert ausschließlich synthetische
`OccupancyGrid`-Nachrichten. Entscheidend ist der WE-M2/AE-Befund: Er berechnet
den dazugehörigen Schema-1-Managerstatus nicht aus dem ursprünglichen Python-
Literal, sondern erst in einer eigenen Subscription aus der über DDS
zurückempfangenen Nachricht. Damit entsprechen insbesondere `resolution` und
Ursprungsfelder ihren ROS-Wire-Typen. Inhalt und Dimensionen sind deterministisch;
Wohnungsgeometrie, Zufallsdaten, Bags oder lokale Karten werden nicht gelesen.

Die CLI verlangt beziehungsweise begrenzt Domain, Rastergrößen, Kapazitäten,
Wiederholungen, Publikationsrate und Gesamtfrist. Vorgesehen sind kleine,
mittlere und bis zum bestehenden Vier-Millionen-Zellen-Vertrag wachsende
quadratische Raster sowie mindestens zwei explizite Kapazitäten. Jeder
Kapazitätsfall läuft in einem frischen Explorerprozess, damit Parameter und
Zähler nicht vermischt werden. Der Ablauf erzeugt Duplikate, mehr eindeutige
noch unkorrelierte Quellen als die jeweilige Kapazität und danach einen exakten
Status für die jüngste Quelle. Dadurch müssen Wartespitze, Verdrängung,
Duplikatzählung und abschließender Exaktjoin beobachtbar sein.

**Metriken und Wahrheitsgrenzen:** Pro Größen-/Kapazitätsfall werden nur
Aggregate ausgegeben: Zellenzahl, Wiederholungen, Digest-/Factoryzeit aus dem
zurückempfangenen Wire-Snapshot (Minimum, Median, p95, Maximum), Zeit vom
Publizieren des passenden Managerstatus bis zum ersten beobachteten
`matched`-Schattenstatus, maximale wartende Quellen, Verdrängungen,
Duplikate, ausgegebene Korrelationen, Start-/Spitzen-/End-RSS und Laufdauer.
Rohzellen, Fingerprints, Frames, Geometrie und Einzelereignislisten werden
nicht ausgegeben. Die externe Joinlatenz enthält bewusst die bis zu einsekündige
Schattenstatusperiode; sie ist keine direkte interne Callbackdauer. Die lokal
gemessene Factoryzeit deckt denselben Kopie-/Digestpfad ab, beweist aber nicht
die gesamte Explorer-Callbackzeit.

Der Prüfer schlägt fehl bei Timeout, fremdem Knoten, Prozessabbruch,
unvollständiger Matrix, fehlendem Exaktjoin, falschen Zählererhaltungen,
überschrittener Kapazität, ungültigen RSS-Werten oder Überschreitung der festen
Ausgabegrenze. Er berichtet zunächst Messwerte und codiert noch keine erfundenen
Jetson-Grenzwerte als Erfolgsschwellen. Erst ein späterer eigener Zielsystemlauf
ohne Aktoren darf auf derselben Matrix belastbare Grenzwerte begründen.

**Geänderte Dateien und Prüfung:** Nur diese STATUS.md. Geprüft wurden die
WE-M2-Anforderungen, der bestehende synthetische ROS-Prüfer, lesende
JSON-Diagnosewerkzeuge, Explorerparameter/-callback, gemeinsamer
Fingerprintvertrag, Joinerdiagnose und Kartenmanagerstatusquelle.
`git diff --check` muss vor Übergabe bestehen. Es wurden keine ROS-Nodes,
Geräte, Karten,
Bags, Aktoren oder Fahrpfade gestartet; dies ist eine dokumentierte
Schnittstellenentscheidung, keine Last-, Jetson- oder Hardwareabnahme.

**Rückfall:** Den einzelnen WE-M2/AF-Dokumentationscommit zurücknehmen. Es gibt
keine Runtime-, Installations- oder Gerätewirkung.

**Nächster abgegrenzter Schritt WE-M2/AG:** Ausschließlich den beschriebenen
Helfer und seine reinen Parser-, Grenz-, Wire-Normalisierungs-, Aggregations-
und Prozessbereinigungstests ergänzen. Danach auf dem lokalen x86_64-System eine
kleine vollständige Matrix in einer leeren isolierten Domain ausführen und die
tatsächlichen Messwerte dokumentieren. Keine Produktionsnode-, Launch-,
Parameter-, Detektor-, Navigations- oder Hardwareänderung.

### 2026-09-14 – WE-M2/AE: doppelt opt-in passive Rohkarten-Runtime

**Entscheidung / Umfang:** `ExploreNode` deklariert zusätzlich
`region_graph_shadow_raw_map_enabled` mit Standard `false` und
`region_graph_shadow_raw_map_capacity` mit Sperrwert `0`. Die reine Validierung
akzeptiert den Rohkartenpfad nur, wenn zugleich der übergeordnete
`region_graph_shadow_enabled` gesetzt und eine positive Kapazität ausdrücklich
angegeben ist. Bei deaktiviertem Rohkartenpfad muss die Kapazität null bleiben;
ein wirkungsloser positiver Wert wird als Konfigurationswiderspruch verworfen.
Es gibt weiterhin keinen geratenen Runtime- oder Produktionsdefault.

Nur beim doppelten Opt-in übergibt `_initialize_region_graph_shadow()` die
Kapazität an genau einen `RegionGraphShadowLifecycle`. Es entsteht keine neue
Subscription: Der bestehende `/map`-Callback wird wiederverwendet. Im
deaktivierten Standard kehrt er nach seinen zwei bisherigen Zuweisungen zurück
und ruft die Factory nicht auf; damit entstehen weder zusätzliche Rasterkopie
noch Digest.

Im Opt-in setzt `_on_map()` zuerst unverändert `self._map` und die monotone
Explorer-Empfangszeit. Nach einer kurzen Fehlerprüfung wird außerhalb von
`_region_graph_shadow_lock` aus Breite, Höhe, wire-genauer Auflösung,
getrimmtem Frame, vollständigem Ursprung, Quellstempel und `data` über den
gemeinsamen WE-M2/Z-Vertrag ein `RawMapPortalSource` gebildet. Erst danach wird
unter dem Lock eine neue monotone Übergabezeit erfasst und die kleine Identität
an den Lebenszyklus gegeben. Dadurch blockiert die Millionen-Zellen-Kopie nicht
den Kartenstatus-/Ausgabe-Lock. Factory- oder Übergabefehler werden einmal nur
im vorhandenen Schattenfehler festgehalten; Karte und Empfangszeit des
bestehenden Explorers bleiben gesetzt. Nach dem Fehler werden weitere Digests
vermieden.

**Geänderte Dateien:** `src/explore/explore/explore_node.py`,
`src/explore/config/explore_params.yaml`, Explorer-Vertragstests und diese
STATUS.md. Kein Launch, Kartenmanager, Detektor, Portalplan, Actionvertrag,
Navigationsziel, Geschwindigkeitskommando oder Sicherheitsparameter wurde
geändert.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble und
vorhandenen generierten Schnittstellen; keine Robotergeräte, realen Karten/Bags,
Nav-Action oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AE-CONTRACT | Explorer-Node-/Parametervertrag einschließlich Doppel-Opt-in, Nullkostenpfad, Wire-Felder, Lockgrenze, echter reiner Lifecycle und isolierter Fehler: **59 passed**. |
| WE-M2AE-EXPLORER | Vollständige Explorer-Suite: **529 passed**. |
| WE-M2AE-ADJACENT | Zusätzlich Blattpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **670 passed**. |
| WE-M2AE-COLCON | Temporärer isolierter Build von Blattpaket und Explorer: 2 Pakete gebaut; **36 + 529 = 565 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AE-STATIC | `git diff --check`, `flake8 --diff` (E501/W503 ausgenommen) und `compileall`: bestanden. |
| WE-M2AE-ROS | Frischer Explorer in isolierter DDS-Domain 228, beide Opt-ins und Kapazität 2; synthetische 2×2-Rohkarte plus exakt gleicher Schema-1-Managerstatus ergaben `mode=shadow`, `passive=true`, eine Region und `raw_map_correlation.state=matched`, `emitted_correlations=1`, `evicted_sources=0`. Prozess per SIGINT beendet. |

Der erste synthetische Statusversuch verwendete für `MapMetaData.resolution`
den Python-Doublewert `0.05` statt des nach DDS-Serialisierung empfangenen
float32-Werts. Der Exaktjoin blieb korrekt `waiting`. Ein danach im selben
Lebenszyklus widersprüchlich fortgeschriebener Teststatus löste wie vorgesehen
den Schattenfehler aus. Der erfolgreiche Wiederholungslauf verwendete eine
frische Domain und die wire-normalisierte Auflösung. Dieser Befund ist zugleich
ein Testharness-Hinweis: synthetische Fingerprints müssen aus den tatsächlich
empfangenen Feldtypen entstehen, nicht aus Vorserialisierungs-Literalen.

In der isolierten Domain wurden keine Motor-, Sensor- oder Missions-Nodes
gestartet und kein Action-Auftrag gesendet. Der Explorer legt seine bestehenden
Geschwindigkeitspublisher zwar an, veröffentlichte im Test aber keinen
Fahrbefehl. Dies ist ein lokaler Software-/DDS-Nachweis, keine Jetson-, Last-,
Hardware- oder Fahrabnahme.

**Rückfall:** Beide neuen Standardparameter bleiben `false`/`0`; dadurch ist
der gesamte neue Callbackteil bereits inaktiv. Vollständiger Rückfall ist das
Zurücknehmen des einzelnen WE-M2/AE-Commits. Kein Installations-, Karten- oder
Gerätezustand wurde verändert.

**Nächster abgegrenzter Schritt WE-M2/AF:** Erst Quellen und vorhandene
Werkzeugkonventionen prüfen und einen eigenständigen synthetischen Prüfer für
dieselbe passive DDS-Naht spezifizieren. Er erzeugt den Fingerprint erst aus
wire-normalisierten beziehungsweise zurückempfangenen Feldern, variiert eine
explizite Kapazitätsmatrix und protokolliert nur begrenzte Aggregate für
Digest-/Callbackzeit, Joinlatenz, Wartespitze, Verdrängungen und RSS. Noch keine
Jetson-Ausführung, reale Map, Bag, Geräte- oder Fahraktivierung.

### 2026-09-14 – WE-M2/AD: optionale Diagnose im getrennten Schattenstatus

**Entscheidung / Umfang:** `RawMapCorrelationDiagnostics` liegt nun bei der
reinen Joiner-Schnittstelle und ist damit ohne zyklischen Import für Joiner,
Lebenszyklus, Schatten-Sitzung und Statusprojektion nutzbar. Der unveränderliche
Typ prüft nichtnegative Ganzzahlzähler und die Erhaltung
`eindeutig = wartend + verdrängt + ausgegeben`. Deaktiviert sind Kapazität und
alle Zähler null. Aktiviert ist die Kapazität positiv, die wartende Anzahl liegt
nicht darüber und eine letzte Revision existiert genau dann, wenn mindestens
eine Korrelation ausgegeben wurde.

Der abgeleitete Zustand ist `waiting`, solange weder Join noch Verdrängung
belegt ist, `matched` nach mindestens einem Join und `evicted` als absichtlich
haftender Warnzustand nach jeder Verdrängung. Die Einzelzähler bleiben daneben
sichtbar; ein späterer Treffer verdeckt eine zu kleine Kapazität deshalb nicht.
`RawMapStatusJoiner.diagnostics` erzeugt diesen validierten Snapshot, und der
Lebenszyklus delegiert seine Eigenschaft an genau denselben Besitzer.

`ShadowStatusSource` akzeptiert die Diagnose optional. `None` fügt dem
kanonischen Schema-1-Dokument kein Feld hinzu; die vorhandenen deaktivierten
Statusverträge bleiben damit strukturell unverändert. Ein aktiver Snapshot wird
als Top-Level-Block `raw_map_correlation` mit `enabled`, Zustand, Kapazität,
Quellen-/Dubletten-/Warte-/Verdrängungs-/Joinzählern und letzter Revision
serialisiert. Deaktivierte oder typfremde Diagnoseobjekte werden verworfen.
Fingerprint, Frame, Quellstempel, Zellen und Wohnungsgeometrie fehlen bewusst.
Die vorhandene `max_serialized_bytes`-Prüfung läuft erst über das vollständige
erweiterte Dokument.

**Geänderte Dateien:** Reine Adapter-, Lebenszyklus-, Sitzungs- und
Statusmodule unter `src/explore/explore/`, deren vier Testsuiten und diese
STATUS.md. Keine Änderung an Node, Launch, Parametern, Topics, Kartenmanager,
Detektor, Portalfeed, Navigation oder Fahrsoftware.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz, für die vollständige
Explorer-Suite ROS-Humble-Underlay und vorhandene generierte Schnittstellen;
keine Nodes, Geräte, Karten, Bags oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AD-FOCUSED | Joiner-, Status-, Schatten-Sitzungs- und Lebenszyklusverträge gemeinsam: **201 passed**. |
| WE-M2AD-EXPLORER | Vollständige Explorer-Suite: **522 passed**. |
| WE-M2AD-ADJACENT | Zusätzlich Blattpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **663 passed**. |
| WE-M2AD-COLCON | Temporärer isolierter Build von Blattpaket und Explorer: 2 Pakete gebaut; **36 + 522 = 558 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AD-STATIC | `git diff --check`, `flake8 --diff` (E501/W503 ausgenommen) und `compileall`: bestanden. |

**Offene Grenzen / Rückfall:** Der Block zeigt bisher ausschließlich reine
synthetische Zustände; ohne ROS-Adapter entstehen keine realen Runtimezähler.
Schema 1 bleibt wegen des ausschließlich additiven optionalen Feldes erhalten;
vor einer externen Nutzung muss ein Verbraucher unbekannte optionale Felder wie
vereinbart tolerieren. Es gibt keinen Jetson-, DDS-, Last- oder
Hardware-Nachweis. Rückfall ist das Zurücknehmen des einzelnen WE-M2/AD-Commits;
bei `None` ist der Block ohnehin abwesend.

**Nächster abgegrenzter Schritt WE-M2/AE:** Im Explorer zwei Parameter mit den
Sperrdefaults `region_graph_shadow_raw_map_enabled: false` und
`region_graph_shadow_raw_map_capacity: 0` deklarieren und ihre Kombination
streng validieren. Nur bei doppeltem Opt-in erzeugt der Lebenszyklus seinen
Joiner. `_on_map()` übernimmt zuerst unverändert Karte und monotone Empfangszeit,
bildet dann außerhalb des Schatten-Locks über den gemeinsamen Factoryvertrag
die Identität und übergibt sie unter dem Lock. Tests belegen deaktivierte
Nullkosten, Feldnormalisierung, Lockgrenze, beide Callbackreihenfolgen und
isolierten Schattenfehler. Ein isolierter DDS-Smoke darf nur ohne Motor-/Sensor-
Nodes und ohne Action-Auftrag laufen.

### 2026-09-14 – WE-M2/AC: optionaler Joiner-Besitz im reinen Lebenszyklus

**Entscheidung / Umfang:** `RegionGraphShadowLifecycle` nimmt optional
`raw_map_capacity` entgegen. Nur ein positiver, nichtboolescher Ganzzahlwert
erzeugt genau einen `RawMapStatusJoiner`; `None` lässt ihn vollständig abwesend.
Null und ungültige Werte werden am reinen Konstruktionsrand verworfen. Der
bisherige Konstruktor bleibt durch den optionalen Standardwert kompatibel.

Der neue reine Eingang `accept_raw_map_source()` übernimmt ausschließlich ein
bereits unveränderliches `RawMapPortalSource` plus explizite monotone
Empfangszeit. Bei deaktiviertem Joiner oder falschem Typ entsteht ein
`RegionGraphShadowLifecycleError`, ohne Zeit, Sitzung oder Diagnosezähler zu
verändern. Bei gültigem Eingang gibt die bestehende `ShadowLifecycleUpdate`
neben Zustand und aktuellem Kartenstatus optional die exakte
`PortalSourceCorrelation` zurück. Dasselbe optionale Feld wird nach jedem
gültigen Kartenstatus gefüllt, falls bereits eine passende Rohkarte wartet.
Somit bleiben Status-vor-Karte und Karte-vor-Status gleichwertig.

Die unveränderliche Eigenschaft `raw_map_diagnostics` projiziert nur feste
Skalare: aktiviert, Kapazität, alle Quellenaufrufe, innerhalb des begrenzten
Fensters eindeutige Quellen und Dubletten, aktuell wartend, verdrängt,
ausgegebene Korrelationen und letzte korrelierte Revision. Keine Rasterbytes,
Fingerprints, Frames oder Geometrien werden dupliziert. Der zugrunde liegende
Joiner zählt eine Wiederholung der zuletzt ausgegebenen Identität als Dublette,
nicht als neue wartende Quelle.

**Geänderte Dateien:** `src/explore/explore/portal_source_adapter.py`,
`src/explore/explore/region_graph_shadow_lifecycle.py`, deren zwei reine
Testsuiten und diese STATUS.md. Keine Änderung an Status-JSON, Node, Launch,
Parametern, Topics, Kartenmanager, Portalfeed, Navigation oder Fahrsoftware.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz, für die vollständige
Explorer-Suite ROS-Humble-Underlay und vorhandene generierte Schnittstellen;
keine Nodes, Geräte, Karten, Bags oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AC-FOCUSED | Portalquellenjoin und Schattenlebenszyklus gemeinsam: **111 passed**. |
| WE-M2AC-EXPLORER | Vollständige Explorer-Suite: **509 passed**. |
| WE-M2AC-ADJACENT | Zusätzlich Blattpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **650 passed**. |
| WE-M2AC-COLCON | Temporärer isolierter Build von Blattpaket und Explorer: 2 Pakete gebaut; **36 + 509 = 545 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AC-STATIC | `git diff --check`, `flake8 --diff` (E501/W503 ausgenommen) und `compileall`: bestanden. |

**Offene Grenzen / Rückfall:** Diagnosezähler liegen nur als reine
Lebenszykluseigenschaft vor und werden noch nicht serialisiert. Es gibt weiterhin
keinen Runtime-Default und keine ROS-Zuführung. Die Tests messen weder Jetson-
Kosten noch echte Karten-/Statuslatenz und sind keine Zielsystem- oder
Hardwareabnahme. Rückfall ist das Zurücknehmen des einzelnen WE-M2/AC-Commits;
ohne `raw_map_capacity` entspricht der Lebenszyklus bereits dem vorherigen
Verhalten.

**Nächster abgegrenzter Schritt WE-M2/AD:** Den Diagnosetyp in eine von Joiner,
Lebenszyklus und Statusprojektion gemeinsam nutzbare reine Modulgrenze legen und
`ShadowStatusSource` optional darum ergänzen. Der bestehende kanonische JSON-Text
muss bei `None` bytegleich bleiben; andernfalls kommt ein kleiner Block mit
Kapazität, Zählern, letzter Revision und abgeleitetem Zustand hinzu. Grenzen,
Konsistenz, Serialisierungsgröße und deaktivierte Rückwärtskompatibilität werden
rein getestet. Noch keine ROS- oder Fahrwirkung.

### 2026-09-14 – WE-M2/AB: Besitzer-, Opt-in- und Messvertrag der Runtime

**Entscheidung / Umfang:** Dieser Schritt ändert nur diese STATUS.md. Die
Quellen von `ExploreNode`, `RegionGraphShadowLifecycle`, Statusprojektion,
Standardparametern und Vertragstests wurden auf der gestapelten WE-M2/AA-Basis
`6ba1e25` geprüft. Es wurden keine Nodes gestartet, keine Geräte oder lokalen
Kartendaten geöffnet und keine Fahrsoftware verändert.

**Besitz und Übergaben:** `RegionGraphShadowLifecycle` besitzt bereits genau
einen `MapManagerStatusCorrelator`, die daraus erzeugte Kartenepoch, die
Schatten-Sitzung und die monotonen Eingangszeiten. Er wird deshalb auch einziger
Besitzer des optionalen `RawMapStatusJoiner`; ein zweiter Joiner im Node oder in
der Statusprojektion würde Sequenzprüfung und Zähler aufteilen. Der Lebenszyklus
erhält später einen reinen Rohkarteneingang und führt nach jedem gültigen
Kartenstatus beide Seiten dem Joiner zu. Ein optionales Korrelationsresultat
wird in der jeweiligen Lebenszyklusantwort zurückgegeben. Ohne konfigurierte
Kapazität existiert kein Joiner und alle bisherigen Antworten bleiben gleich.

Der ROS-Node bleibt nur Adapter. `_on_map()` muss zuerst wie bisher `self._map`
und `self._map_received_at` setzen. Nur beim späteren separaten Rohkarten-Opt-in
liest er danach Dimensionen, Auflösung, normalisierten Frame, Ursprung,
Quellstempel und Zellen. Bytekopie, Werteprüfung und Digest geschehen außerhalb
von `_region_graph_shadow_lock`. Unter dem Lock wird ausschließlich das fertige
kleine `RawMapPortalSource` übergeben. Eine ungültige Quelle faultet nur den
optionalen Schatten; ein gültiger Nichttreffer bleibt wartend. Der
Kartenstatuscallback bleibt unter demselben Lock, sodass Lebenszyklus und Joiner
trotz `ReentrantCallbackGroup` serialisiert werden. Weder Rasterkopie noch
Memoryview werden im Besitzer gehalten.

**Opt-in-Vertrag:** Für die spätere Node-Stufe sind zwei getrennte Parameter
vorgesehen:

- `region_graph_shadow_raw_map_enabled: false` aktiviert ausschließlich Bildung
  und Join der Rohkartenidentität; der übergeordnete Schatten muss zugleich
  aktiviert sein.
- `region_graph_shadow_raw_map_capacity: 0` ist im deaktivierten Stand ein
  Sperrwert, kein gemessener Default. Bei aktiviertem Rohkartenpfad muss der
  Nutzer einen positiven Wert explizit setzen. Ein gesetzter Wert bei
  deaktiviertem Pfad wird als widersprüchliche Konfiguration abgelehnt, damit
  keine scheinbare Aktivierung entsteht.

Die bestehende `/map`-Subscription mit Tiefe eins wird wiederverwendet; es
entsteht kein zweiter Kartenabonnent. Der Opt-in ändert weder
`/explore/status_json` noch Action, Nav2-Ziele oder `cmd_vel`. Ohne beide
Aktivierungen darf `_on_map()` keine zusätzliche Kopie und keinen Digest bilden.

**Diagnosevertrag:** Die spätere additive Diagnose gehört ausschließlich in den
getrennten `/explore/region_graph/status_json`-Schattenstatus und wird nur beim
Rohkarten-Opt-in ausgegeben. Schema 1 bleibt nur dann zulässig, wenn der neue
Block optional ist und der deaktivierte JSON-Text bytegleich bleibt. Der Block
benennt mindestens: konfigurierte Kapazität, beobachtete eindeutige Quellen,
aktuelle wartende Quellen, Verdrängungen, erfolgreiche Joins, letzte korrelierte
Kartenrevision und Zustand `waiting`, `matched` oder `evicted`. Er enthält weder
Rasterdaten noch Wohnungsgeometrie. Callback-/Digestzeiten und Prozessspeicher
gehören in den Messbericht, nicht als unbeschränkt wachsende Zeitreihe in das
Statusdokument.

**Motorloser Messplan:** Zuerst wird auf dem Jetson in einer isolierten DDS-
Domain eine synthetische `OccupancyGrid`-/Statusfolge an einen alleinstehenden
passiven Explorer gespeist. Vorher ist anhand der tatsächlich laufenden Prozesse
zu belegen, dass weder `base_hardware`, Bewegungscontroller, Missionsausführung
noch reale Sensorstarts beteiligt sind; bloßes `dry_run` genügt nicht. Gemessen
werden Rastergröße, Publikationsrate, Digest- und gesamte Callbackzeit
(Median/p95/Maximum), Join-Wartezeit, wartende Spitze, Verdrängungen sowie
Prozess-RSS vor/während/nach der Folge. Kapazitäten werden als explizite
Testmatrix gesetzt, nicht als Produktionsdefault.

Eine reale Kartenrate und Managerverzögerung kann dieser synthetische Lauf nicht
beweisen. Dafür ist anschließend entweder eine vorhandene geeignete lokale Bag
in isolierter Wiedergabe oder eine ausdrücklich freigegebene passive Beobachtung
eines bereits laufenden Kartenstacks nötig. Ohne Bag beziehungsweise Freigabe
bleibt die Produktionskapazität offen; Kamera/SLAM werden nicht allein für diese
Messung aktiviert. Keine dieser Messungen erteilt eine Fahr- oder
Hardwareabnahme.

**Ausgeführte Prüfungen / Rückfall:** Quellenvergleich und `git diff --check`;
keine Funktions-, ROS-, Zielsystem- oder Hardwaretests, weil nur die fachliche
Entscheidung geändert wird. Rückfall ist das Zurücknehmen dieses
Dokumentationscommits; WE-M2/AA bleibt reine, nicht eingebundene Logik.

**Nächster abgegrenzter Schritt WE-M2/AC:** Nur den reinen Lebenszyklus um einen
optionalen, ausschließlich bei explizit positiver Kapazität erzeugten Joiner,
einen Rohkarteneingang und feste Zählerzustände erweitern. Kartenstatus-vor-
Rohkarte, Rohkarte-vor-Status, Replay, Nichttreffer, Verdrängung, ungültige
Quelle, Kartenepochwechsel und vollständig deaktiviertes Legacyverhalten werden
ohne ROS getestet. JSON, Node, Parameter und Runtime bleiben unverändert.

### 2026-09-14 – WE-M2/AA: begrenzter beidseitiger Rohkarten-/Statusjoin

**Entscheidung / Umfang:** Neu ist ausschließlich der reine
`RawMapStatusJoiner` im bestehenden `portal_source_adapter.py`. Seine Kapazität
ist ein obligatorisches positives Konstruktorargument; dieser Schritt erfindet
weder Messwert noch Runtime-Default. Er hält eine einfügungsgeordnete Abbildung
aus exakter Rohkartenidentität und unveränderlichem `RawMapPortalSource`, nicht
die Rasterzellen. Beim Überschreiten entfernt er genau die älteste noch
wartende Identität und zählt die Verdrängung sichtbar.

Sowohl `observe_source()` als auch `observe_status()` versuchen den Join erneut.
Dadurch sind Status-vor-Karte und Karte-vor-Status gleichwertig. Nur identischer
SHA-256-Fingerprint, identischer Quellstempel einschließlich null und identischer
Frame führen über den Exaktvertrag aus WE-M2/V zu einer
`PortalSourceCorrelation`. Ein fehlender Treffer liefert `None`, verändert den
gültigen Status nicht und löst keinen Fehler aus. Wiederholte Quellen werden
nicht mehrfach gepuffert; dieselbe bereits ausgegebene Identität/Revision wird
nicht erneut ausgegeben.

Der Joiner prüft außerdem die Folge bereits normalisierter Kartenstatusobjekte:
Kontext- oder Revisionsrücksprung, Identitätswechsel ohne neue Revision, neue
Revision ohne Identitätswechsel sowie widersprüchliche Änderungs-/Replayflags
werden fail-closed verworfen, ohne den zuletzt gültigen Status zu überschreiben.
Die vorgelagerte `MapManagerStatusCorrelator` bleibt Eigentümer von JSON,
Kartenepoch und Zeitprüfung; der neue Joiner ersetzt ihn nicht.

**Geänderte Dateien:** Nur
`src/explore/explore/portal_source_adapter.py`, dessen reine Unit-Tests und diese
STATUS.md. Keine Änderung an Node, Lebenszyklus, Launch, Parametern, Topics,
Kartenmanager, Detektor, Navigation oder Fahrsoftware.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz, für die vollständige
Explorer-Suite ROS-Humble-Underlay und vorhandene generierte Schnittstellen;
keine Nodes, Geräte, Karten, Bags oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2AA-FOCUSED | Vollständiger Portalquellenadapter einschließlich beider Eingangsreihenfolgen, Wachstum/Nichttreffer, Replay, Kapazitätsverdrängung und gefälschter Folgen: **48 passed**. |
| WE-M2AA-EXPLORER | Vollständige Explorer-Suite: **499 passed**. |
| WE-M2AA-ADJACENT | Zusätzlich Blattpaket, Kartenmanager, Semantikmanager und Semantik-Launch-Verträge: **640 passed**. |
| WE-M2AA-COLCON | Temporärer isolierter Build von Blattpaket und Explorer: 2 Pakete gebaut; **36 + 499 = 535 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2AA-STATIC | `git diff --check`, `flake8 --diff` (E501/W503 ausgenommen) und `compileall`: bestanden. |

**Offene Grenzen / Rückfall:** Die explizite Kapazität beweist Begrenztheit der
reinen Struktur, aber noch keinen ausreichenden Wert für die reale Kartenrate
und Callbackverzögerung. Ohne Runtime-Besitzer existieren keine Messwerte für
Nichttreffer oder Verdrängungen auf dem Jetson. Der Joiner gibt noch keinen
Portalplan an den Schattenlebenszyklus und beeinflusst keine Navigation. Die
Tests sind keine Zielsystem- oder Hardwareabnahme. Rückfall ist das
Nichtverwenden des neuen Typs beziehungsweise das Zurücknehmen des einzelnen
WE-M2/AA-Commits; der stateless Exaktabgleich aus WE-M2/V bleibt erhalten.

**Nächster abgegrenzter Schritt WE-M2/AB:** Dokumentarisch festlegen, welcher
bestehende Schattenbesitzer den Joiner hält, wie ein separater standardmäßig
deaktivierter Opt-in und eine nur explizit gesetzte Kapazität validiert werden,
welche Zähler/Frischeangaben ohne Änderung von `/explore/status_json` sichtbar
werden und wie der motorlose Jetson-Lauf Kartenrate, Join-Latenz, Verdrängung,
Digestzeit, Callbackzeit und Speicher misst. Erst danach darf ein passiver
ROS-Integrationsschritt abgegrenzt werden.

### 2026-09-14 – WE-M2/Z: eine gemeinsame begrenzte Zellnormalisierung

**Entscheidung / Umfang:** `amadeus_map_identity.compact_occupancy_cells()`
ist nun die einzige Umwandlung von ROS-signierten Belegungszellen in die
kanonische unveränderliche Bytefolge. Werte 0 bis 100 bleiben gleich, `-1` wird
zum Bitmuster 255. Eindimensionale, zusammenhängende Buffer mit Elementgröße
eins und Format `b`, `B` oder `c` nutzen Memoryview, eine C-seitige Bytekopie
und C-seitige Werteprüfung. Andere Iterables werden streng elementweise geprüft.
Länge, Ganzzahltyp, `bool`, Wertebereich und Lesefehler werden fail-closed
behandelt.

Die bestehende Kartenmanagergrenze von 4.000.000 Zellen ist als gemeinsame
Konstante in das Blattpaket verschoben. Eine größere angegebene Länge wird vor
Iteration verworfen. `robot_map_manager` behält den Namen
`MAXIMUM_CELL_COUNT` und übersetzt einen `MapIdentityError` weiterhin in seinen
vorhandenen `MapValidationError`; gespeicherte Bytes, bekannte SHA-256-Werte,
Statusschema und Dateiformat ändern sich nicht. Der reine Explorer-Factory-
Vertrag nimmt nun rohe `cells` entgegen, validiert positive 32-Bit-Dimensionen,
normalisiert über dieselbe Funktion und bildet erst dann den gemeinsamen
Fingerprint. Er ist weiterhin in keinen Node eingebunden.

**Geänderte Dateien:** Implementierung, Export, Metadaten und Tests unter
`src/amadeus_map_identity/`; Delegation in
`src/robot_map_manager/robot_map_manager/map_core.py`; reiner Factory-Vertrag
und Tests in `src/explore/explore/portal_source_adapter.py` beziehungsweise
`src/explore/test/test_portal_source_adapter.py`; Paketbeschreibung in
`docs/INVENTORY.md` und dieser Status. Keine Node-, Launch-, Parameter-,
Navigations-, Sensor- oder Fahränderung.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz, ROS-Humble-Underlay und
für generierte Schnittstellen die vorhandene lokale Installation; keine Nodes,
Geräte, Karten, Bags oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2Z-FOCUSED | Blatt-, Portalquellen- und Kartenmanager-Core-Verträge gemeinsam: **119 passed**. |
| WE-M2Z-COMPONENTS | Blattpaket **36**, vollständiger Explorer **483**, Kartenmanager **51** Tests; zusammen **570 passed**. |
| WE-M2Z-ADJACENT | Zusätzlich Semantikmanager- und Semantik-Launch-Verträge: **624 passed**. |
| WE-M2Z-COLCON | Temporärer isolierter Build der drei Pakete: 3 Pakete gebaut; Blattpaket **36** und Explorer **483** Pakettests bestanden, Kartenmanager-Colcon-Hook führt historisch 0 Tests. Gesamt `colcon test-result`: **519 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**; die **51** Kartenmanager-Quelltests sind in WE-M2Z-COMPONENTS enthalten. |
| WE-M2Z-STATIC | `git diff --check`, `flake8 --diff` (E501/W503 ausgenommen) und `compileall`: bestanden. |
| WE-M2Z-REMOTE-CI | PR #50 ist laut GitHub mergebar, aber nicht grün. Der unveränderte `python-contracts`-Workflow brach wie bei WE-M2/X im Bring-up-Vertrag bereits beim Import von `test_oak_rectifier.py` ab, weil dem Ubuntu-Runner `cv2` fehlt. Der Kartenmanagerschritt wurde dadurch nicht erreicht; Blattpaket und Explorer gehören weiterhin nicht zu den Pfaden beziehungsweise Tests dieses Workflows. Dies ist kein entfernter Nachweis für WE-M2/Z. |

Eine erste kombinierte Testanweisung enthielt einen falschen
Semantik-Launch-Dateinamen; die korrigierte Anweisung lief vollständig. Ein
zweiter Vorlauf ohne die lokal installierten generierten `robot_interfaces`
brach bei der Sammlung ab; nach explizitem Read-only-Underlay lief die oben
ausgewiesene vollständige Suite. Beides waren Testaufbaufehler vor Ausführung
der Produkttests, keine bestandenen oder fehlgeschlagenen Produktnachweise.

**Offene Grenzen / Rückfall:** Der Schritt beweist Byte- und Vertragsgleichheit
auf dem lokalen Rechner, nicht Kosten oder Scheduling auf dem Jetson. Er hält
noch keine Identität über Callbacks, ordnet keinen Kartenstatus zu, beobachtet
kein Portal und beeinflusst keine Navigation. Rückfall ist das Zurücknehmen des
einzelnen WE-M2/Z-Commits; WE-M2/Y bleibt als Dokumentationsvertrag bestehen,
und WE-M2/X kann wieder die vorherige private Kartenmanagernormalisierung nutzen.
Keine physische Abnahme ist erfolgt.

**Nächster abgegrenzter Schritt WE-M2/AA:** Als reine Logik einen beidseitig
anstoßbaren Korrelator ergänzen. Er hält nur eine vom Aufrufer explizit begrenzte
Folge unveränderlicher `RawMapPortalSource`-Objekte und den aktuellen validierten
Kartenstatus, gibt ausschließlich bei exakter Fingerprint-/Stempel-/Frame-
Gleichheit eine Revision frei, dedupliziert Replays und unterscheidet erwarteten
Nichttreffer von ungültigem Eingang. Tests decken Status-vor-Karte,
Karte-vor-Status, Kartenwachstum, Replay, Verdrängung und Fälschungen ab. Noch
kein Defaultwert, ROS-Callback, Portalfeed oder Fahrpfad. Rückfall: das neue
reine Modul nicht einbinden beziehungsweise den einzelnen Commit zurücknehmen.

### 2026-09-14 – WE-M2/Y: Vertrag der passiven Rohkartennaht

**Entscheidung / Umfang:** Dieser Schritt ändert ausschließlich diese
STATUS.md. Er schließt noch keinen ROS-Callback an. Geprüft wurden der lokal
installierte ROS-Humble-Nachrichtentyp, der Kartenmanager-Quellpfad und der
standardmäßig deaktivierte Explorer-Schattenpfad auf der gestapelten
WE-M2/X-Basis `340d6c5`. Es wurden keine Nodes gestartet, keine Geräte geöffnet,
keine Karten oder Bags gelesen und keine Fahrsoftware verändert.

**Nachgewiesener Datentyp und Kopiergrenze:** Die lokal installierte, von
`rosidl_generator_py` erzeugte Klasse `nav_msgs.msg.OccupancyGrid` speichert
`data` als `array.array('b')`. Auch zugewiesene Python-Sequenzen werden nach der
int8-Prüfung in diesen Typ überführt. Ein tatsächliches Testobjekt lieferte einen
eindimensionalen, C-zusammenhängenden Memoryview mit Format `b` und Elementgröße
1. `[-1]` besitzt darin das Bitmuster `0xff`; die Testfolge
`[0, 100, -1, 42]` wurde bytegleich zu `00 64 ff 2a` kopiert. Damit ist der
vorhandene Kartenmanager-Schnellpfad `memoryview(...).cast("B").tobytes()` für
den lokalen Humble-Stand anwendbar und vermeidet die Python-Schleife über jede
Zelle. Die unveränderliche Bytekopie ist zugleich die Besitzgrenze: Der
Explorer darf nach Rückkehr aus dem Callback keinen geliehenen ROS-Puffer für
eine spätere Digestberechnung behalten.

Die Normalisierung ist heute jedoch privat in
`robot_map_manager.map_core._validated_compact_cells()` implementiert. Der
Explorer darf weder diesen Import und damit den in WE-M2/W nachgewiesenen
Paketzyklus einführen noch die Werteprüfung duplizieren. Deshalb bleibt die
Runtime-Anbindung gesperrt, bis der exakt gleiche Schnell- und Fallbackpfad im
neutralen Blattpaket liegt.

**Callback- und Fehlervertrag:** `ExploreNode` verwendet eine
`ReentrantCallbackGroup`; Karten-, Kartenmanagerstatus- und Statustimer-Callbacks
können sich daher überlappen. `_on_map()` setzt bislang nur die bestehende
Explorerkarte und deren monotone Empfangszeit. Diese beiden Zuweisungen müssen
bei einer späteren Erweiterung zuerst und unverändert erfolgen. Nur wenn der
Schattenmodus aktiviert ist, darf danach aus den Nachrichtenfeldern eine
unveränderliche Rohkartenidentität gebildet werden. Digest und Bytekopie erfolgen
außerhalb von `_region_graph_shadow_lock`; unter dem Lock werden nur kleine
Identitäts-/Statusobjekte korreliert und der Schattenzustand verändert.

Eine ungültige Rohkarte darf ausschließlich den optionalen Schattenpfad in
seinen bestehenden fail-closed-Fehlerzustand versetzen; die Exception darf den
vorhandenen Explorer-Kartenpfad nicht verlassen. Ein gültiger, aber aktuell
nicht passender Kartenfingerprint ist dagegen beim Kartenwachstum und durch die
asynchronen Callbacks erwartbar und **kein** dauerhafter Fehler. Rohkarten- und
Kartenstatus-Callback müssen denselben Exaktabgleich aus WE-M2/V jeweils erneut
auslösen können. Erlaubt ist nur Gleichheit von Fingerprint, Quellstempel und
Frame; Zeitnähe, Framegleichheit allein oder eine Nav2-Costmap-Zeit bilden keine
Provenienz.

Bis zur Messung wird keine Puffergröße erfunden. Eine spätere Implementierung
darf nur eine feste Anzahl kleiner `RawMapPortalSource`-Identitäten und den
aktuellen validierten Kartenstatus halten, niemals mehrere Rasterkopien. Zu
messen sind auf dem Jetson vor Aktivierung: Kartenrate, Abstand zwischen
Rohkartenempfang und passendem Managerstatus, Zahl dazwischen empfangener
verschiedener Identitäten, Nichttreffer/Verdrängungen, Callback-Gesamtzeit,
Digestzeit sowie RSS-/Spitzenspeicher. Aus beobachteter Verzögerung und Rate ist
anschließend eine harte Kapazität mit Reserve festzulegen; Überschreitung bleibt
sichtbar nicht bereit und erzeugt keine erfundene Revision.

**Lokale synthetische Kostenprobe:** Auf dem x86_64-Arbeitsplatz wurde ohne ROS-
Node ein Raster mit der bestehenden Höchstgrenze von 4.000.000 Zellen fünfmal
kopiert und durch den WE-M2/X-Explorer-Factory-/Digestpfad geführt. Median:
1,976 ms Bytekopie, 11,856 ms Digest/Validierung und 13,832 ms gesamt. Ein
separater `tracemalloc`-Durchlauf meldete 4.000.129 Byte verbleibend und
8.000.198 Byte Spitze bei 12,706 ms Gesamtzeit. Das belegt nur die Größenordnung
dieses lokalen CPython-/x86-Laufs; es ist weder ein Jetson-Budget noch ein
Runtime-, Last-, Zielsystem- oder Hardware-Nachweis.

**Ausgeführte Prüfungen:** Quellprüfung der installierten generierten
`OccupancyGrid`-Klasse, der Kartenmanager-Konvertierung/-Callbackfolge, der
Explorer-`ReentrantCallbackGroup` und des Schatten-Locks; tatsächlicher
`array('b')`-/Memoryview-Test sowie die vorstehende synthetische Kostenprobe;
`git diff --check`. Nicht ausgeführt wurden ROS-Start, DDS-Zuordnung,
Callback-Lasttest, Jetson-Messung, Karten-/Bag-Auswertung und jede physische
Abnahme.

**Nächster abgegrenzter Schritt WE-M2/Z:** Im Blattpaket eine öffentliche reine
Zellnormalisierung mit unveränderlichen Bytes, vollständiger Längen-/Werteprüfung,
Memoryview-Schnellpfad und generischem Fallback ergänzen. Der Kartenmanager
delegiert seinen bisherigen privaten Pfad dorthin; der reine Explorer-Factory-
Vertrag nutzt dieselbe Funktion. Betroffen sind ausschließlich
`src/amadeus_map_identity/`, `src/robot_map_manager/robot_map_manager/map_core.py`,
die reinen `portal_source_adapter`-Dateien und diese STATUS.md. Prüfplan:
bekannte Byte-/Fingerprintvektoren, `array('b')`, `bytes`, ungültige Formate,
Länge/Werte, Generator-Fallback, vollständige gemeinsame Unit-Suiten,
isolierter Drei-Paket-Colcon-Test und statische Prüfungen. Rückfall: den einen
WE-M2/Z-Commit zurücknehmen; WE-M2/X bleibt funktionsfähig, weil keine Runtime-
Schnittstelle und kein Format geändert werden.

### 2026-09-14 – WE-M2/X: eine gemeinsame bytegleiche Kartenidentität

**Entscheidung / Umfang:** Neu ist das ament-Python-Blattpaket
`amadeus_map_identity` ohne ROS- oder Projektpaketabhängigkeit. Seine einzige
fachliche Funktion bildet den bisherigen Kartenmanager-SHA-256 aus positiver
Breite/Höhe, positiver Auflösung, normalisiertem Frame, sieben endlichen
Ursprungswerten und bereits kompakten Kartenzellen. Die Byteordnung und
Feldreihenfolge sind unverändert. Erlaubt sind Zellbytes 0 bis 100 und 255 für
ROS-Unknown; der Quellstempel gehört weiterhin nicht zum Inhaltsfingerprint.

`robot_map_manager.MapSnapshot` validiert und normalisiert weiterhin seinen
vollständigen Kartenvertrag, delegiert danach aber die eine Digestberechnung an
das Blattpaket. Ein bekannter Fingerprintvektor wurde im Kartenmanagertest
festgeschrieben. Dadurch ändern sich weder Statusschema, gespeicherte
Fingerprintwerte noch Dateiformat. `explore` deklariert ebenfalls nur die
Abhängigkeit zum Blattpaket. Sein reiner Quellenadapter kann aus expliziten,
bereits normalisierten Kartenfeldern eine `RawMapPortalSource` bilden und nutzt
dabei denselben bekannten Digestvektor.

Der Paketgraph bleibt azyklisch:

```text
amadeus_map_identity --> explore --> robot_navigation --> robot_map_manager
                    \--------------------------------------->|
```

Das neue Blatt kennt keinen seiner Verbraucher. Der bereits vorhandene Pfad
zwischen Explorer, Navigation und Kartenmanager bleibt unverändert. Ein
isolierter Drei-Paket-Build ordnete deshalb zuerst `amadeus_map_identity`, dann
`explore` und zuletzt `robot_map_manager` an.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS-Humble-Underlay,
ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2X-FOCUSED | Gemeinsame Fingerprint-, Kartenmanager-Core- und Portalquellen-Suiten: **100 passed**. |
| WE-M2X-CORE | Neues Blattpaket, vollständige Explorer- und Kartenmanager-Suiten gemeinsam: **551 passed**. |
| WE-M2X-ADJACENT | Zusätzlich Semantikmanager- und Semantik-Launch-Verträge: **605 passed**. |
| WE-M2X-COLCON | Temporärer isolierter Build der drei Pakete: 3 Pakete gebaut; Blattpaket **18** und Explorer **482** Pakettests bestanden, Kartenmanager-Colcon-Hook führt historisch 0 Tests; seine **51** Quelltests sind separat in WE-M2X-CORE enthalten. Gesamt `colcon test-result`: **500 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2X-STATIC | `git diff --check`, `flake8 --diff` (E501/W503 ausgenommen) und `compileall`: bestanden. |
| WE-M2X-REMOTE-CI | PR #48 ist laut GitHub mergebar, aber nicht grün: Beide `python-contracts`-Läufe brachen im unveränderten `src/robot_bringup/test/test_oak_rectifier.py` bereits beim Import ab, weil dem Ubuntu-Runner `cv2` fehlt. Der nachfolgende Kartenmanagertest lief dadurch nicht. Der Workflow überwacht und testet außerdem weder `src/amadeus_map_identity/**` noch `src/explore/**`; dies ist deshalb ausdrücklich **kein** entfernter Testnachweis für WE-M2/X. Ein Swift-Lauf war erfolgreich, der zweite beim Abruf noch aktiv. |

**Offene Grenzen / Integrationsabhängigkeiten:** Der neue Explorer-Factory-
Vertrag akzeptiert absichtlich nur bereits normalisierte kompakte Bytes. Noch
ist nicht festgelegt, wie der reale rclpy-`OccupancyGrid.data`-Puffer ohne
unnötige Millionen-Zellen-Python-Schleife in genau diesen unveränderlichen
Snapshot überführt wird. Explorer und Kartenmanager empfangen `/map` weiterhin
in getrennten Callbacks; erst der spätere exakte Abgleich aus WE-M2/V darf eine
Revision freigeben. Keine HWT-Detektorfunktion wurde übernommen, kein Portal
beobachtet und keine Runtime aktiviert. Die Testläufe sind keine Zielsystem-
oder Hardwareabnahme. Der bestehende, außerhalb dieses Schritts liegende
CI-Umgebungs-/Abdeckungsbefund wird nicht durch eine fachfremde Workflow- oder
OpenCV-Änderung in WE-M2/X verdeckt; er muss separat abgegrenzt werden.

**Nächster abgegrenzter Schritt WE-M2/Y:** Nur quellenbasiert den tatsächlichen
rclpy-Datentyp, die vorhandenen schnellen Kartenmanagerpfade und die
Reentrant-Callback-Nebenläufigkeit prüfen. Einen begrenzten Snapshotvertrag,
Fehlerisolation und Messplan für Digestzeit sowie Spitzenspeicher festlegen,
bevor der standardmäßig deaktivierte Schattenpfad eine Rohkarte verarbeitet.
Zunächst nur diese STATUS.md; keine Funktions- oder Runtimeänderung.

**Rückfallweg:** Den WE-M2/X-Commit beziehungsweise gestapelten Review-PR
zurücknehmen. `MapSnapshot` verwendet danach wieder seinen vorherigen internen,
bytegleichen Digest; Karten-IDs und gespeicherte Karten brauchen keine
Migration. Explorer-Quellenadapter WE-M2/V bleibt ohne Erzeuger bestehen. Kein
Installations- oder Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/W: `MapSnapshot`-Direktimport würde Paketzyklus erzeugen

**Geprüfte Abhängigkeit:** Der WE-M2/V-Adapter benötigt langfristig exakt
denselben Fingerprint wie der Kartenmanager. Ein direkter Laufzeitimport von
`robot_map_manager.map_core.MapSnapshot` wäre technisch naheliegend, ist im
vorhandenen Paketgraphen aber nicht zulässig:

```text
robot_map_manager --exec--> robot_navigation --exec--> explore
       ^                                             |
       +---------------- geplanter Import -----------+
```

`robot_map_manager/package.xml` benötigt `robot_navigation` für seinen
vorhandenen Smoke-Launch; `robot_navigation/package.xml` benötigt `explore` für
den Mapping-/Erkundungslaunch. `colcon list --topological-order --packages-up-to
explore robot_map_manager` bestätigt heute die azyklische Reihenfolge
`explore → robot_navigation → robot_map_manager`. Eine neue
`explore → robot_map_manager`-Kante würde diese Reihenfolge unmöglich machen.

**Entscheidung:** Weder ein nicht deklarierter Python-Import noch ein zweiter,
nur durch ähnliche Tests synchron gehaltener SHA-256-Algorithmus wird
eingeführt. `robot_interfaces` bleibt auf ROS-IDL beschränkt und wird nicht mit
einer fachfremden Python-Hilfsbibliothek erweitert. Stattdessen wird nur die
kanonische Fingerprintberechnung aus `MapSnapshot.__post_init__` in ein kleines
ROS-freies Blattpaket extrahiert. Dieses Blatt kennt weder Kartenmanager,
Navigation noch Explorer; Kartenmanager und Explorer dürfen von ihm abhängen.
Die Validierung und Speicherung des `MapSnapshot` bleiben Eigentum des
Kartenmanagers.

Die Extraktion muss byteidentisch bleiben: Breite/Höhe/Auflösung in der
vorhandenen Network-Byte-Order, Länge und Bytes des UTF-8-Frames, sieben
Ursprungswerte und die bereits validierten kompakten Zellbytes. Der
`source_stamp_ns` bleibt wie bisher absichtlich außerhalb des Inhaltsfingerprints.
Bekannte Vektoren und bestehende Kartenmanager-Fingerprinttests müssen vor und
nach der Extraktion identisch sein. Damit wird keine Karten-ID migriert.

**Ausgeführte Prüfungen:** Paketmetadaten, Launchverwendungen und der einzige
vollständige MapSnapshot-Fingerprintpfad wurden quellenbasiert geprüft; der
aktuelle Paketgraph wurde mit Colcon aufgelistet. Die unveränderte vollständige
Explorer-Suite bestand erneut mit **476 passed**, `git diff --check` bestand.
Keine ROS-Nodes, Kartendaten, Geräte oder Aktoren wurden gestartet. Dies ist
eine Architekturentscheidung, keine Runtime-, Zielsystem- oder Hardwareabnahme.

**Nächster abgegrenzter Schritt WE-M2/X:** Neues Blattpaket
`src/amadeus_map_identity` mit genau einer reinen Fingerprintfunktion und
bekannten Testvektoren. `robot_map_manager.MapSnapshot` darauf umstellen und
den Explorer-Adapter aus expliziten, bereits normalisierten Rohkartenfeldern
dieselbe Funktion verwenden lassen. Paketmetadaten, Inventar,
Kartenmanager-/Explorer-Cross-Contracts und Gesamtgraph prüfen. Keine ROS-
Callbacks, Detektoren, Parameter, Launches, Portalzuführung oder Fahrsoftware
ändern.

**Rückfallweg:** WE-M2/W ändert nur diese STATUS.md. Den
Dokumentationscommit beziehungsweise Review-PR zurücknehmen; WE-M2/V bleibt
funktionsfähig, aber weiterhin ohne Erzeuger für seinen Fingerprint. Kein
Betriebs- oder Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/V: Revision nur bei exakter Rohkartenidentität

**Entscheidung / Umfang:** Neu ist das reine Standardbibliotheksmodul
`portal_source_adapter.py`. `RawMapPortalSource` trägt ausschließlich den
bereits berechneten SHA-256-Fingerprint, `source_stamp_ns` und Frame der exakt
vom passiven Detektor verwendeten Rohkartenmomentaufnahme. Der zustandslose
`correlate_raw_map_portal_source()`-Vertrag vergleicht alle drei Werte mit einem
aktuellen `MapStatusCorrelationResult`. Erst bei exakter Übereinstimmung gibt er
dessen unveränderten Portal-/Kartenkontext und positive Prozessrevision frei.

Jede Fingerprint-, Stempel- oder Frameabweichung wird verworfen; dadurch kann
eine ältere Detektormomentaufnahme nicht die inzwischen neueste
Kartenmanagerrevision erhalten. Ein Nullstempel bleibt als expliziter Wert
zulässig, muss aber auf beiden Seiten null sein und ersetzt den Fingerprint
nicht. Der Adapter validiert auch direkt konstruierte Statusobjekte und lehnt
ungültige Revisionen, Fingerprints, Stempel, Alterswerte sowie nicht boolesche
Änderungs-/Replaykennzeichen ab. Eingaben und Ergebnis sind unveränderlich.

Das Modul akzeptiert keine `OccupancyGrid`, Costmap, Portalgeometrie oder
Empfangszeit. Es berechnet noch keinen Fingerprint, ruft keinen Detektor auf,
erzeugt keine Beobachtungs-ID und verändert weder Portalgedächtnis noch Graph.
Damit kann insbesondere ein bestehender Costmap-only-`PortalPlan` die
Provenienzsperre aus WE-M2/U nicht umgehen.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und vorhandenem `robot_interfaces`-Underlay, ohne
ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2V-SOURCE | Quellenadapter-, Kartenstatus- und Portalplanadapter-Suiten gemeinsam: **139 passed**, davon 25 neue Quellenfälle. |
| WE-M2V-EXPLORE | Vollständige Explorer-Suite: **476 passed**. |
| WE-M2V-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **581 passed**. |
| WE-M2V-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **476 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2V-STATIC | `git diff --check` und `flake8 --diff` (E501/W503 ausgenommen): bestanden. |

**Offene Grenzen / Integrationsabhängigkeiten:** Der Adapter vertraut bewusst
noch auf einen bereits kanonisch berechneten Fingerprint. Der Explorer erzeugt
keine `RawMapPortalSource`, und es existiert weiterhin weder Detektor- noch
Lifecycle-Zuführung. Eine unabhängige zweite Implementierung des
Kartenmanager-Digests könnte auseinanderlaufen; deshalb muss der nächste Schritt
die vorhandene `MapSnapshot`-Implementierung direkt wiederverwenden. Die
HWT-Rohkartenerkennung ist nicht übernommen. Costmap-Provenienz,
Strukturevidenz, Beobachtungs-ID und Unsicherheitsquelle bleiben offen.

**Nächster abgegrenzter Schritt WE-M2/W:** Nur
`portal_source_adapter.py`, dessen Tests, `explore/package.xml` und diese
STATUS.md. Aus einem bereits validierten
`robot_map_manager.map_core.MapSnapshot` eine `RawMapPortalSource` ableiten,
damit Fingerprint, Quellstempel und Frame aus exakt derselben kanonischen
Implementierung stammen. Die azyklische Laufzeitabhängigkeit deklarieren und
positive/negative Cross-Package-Verträge prüfen. Keine ROS-Nachricht dekodieren,
keinen Node, Detektor, Parameter, Launch oder Portalfeed ändern.

**Rückfallweg:** Den WE-M2/V-Commit beziehungsweise gestapelten Review-PR
zurücknehmen. WE-M2/U und die standardmäßig deaktivierte Schattenhülle bleiben
separat reviewbar. Das neue Modul wird von keinem Runtime-Pfad importiert; es
gibt keinen Installations- oder Gerätezustand zurückzusetzen.

### 2026-09-14 – WE-M2/U: Costmap-Zeit ist keine Rohkarten-Provenienz

**Geprüfte Quellen:** Auf der gestapelten Spitze `eec8c5e` wurden
`ExploreNode.PortalPlan`, Karten-/Costmap-Callbacks und `_portal_plans()`, der
Kartenmanager-Eingang samt `MapSnapshot`/Status, beide Nav2-Konfigurationen sowie
die Portalpfade von Main, HWT `1d91229` und der unveränderten lokalen
Primärarbeitskopie gelesen. Lokal installiert ist Nav2
`nav2_costmap_2d` 1.1.20. Dessen zum Paketstand passender Upstream-Quelltext setzt
beim Erzeugen der publizierten `OccupancyGrid`-Master-Costmap
`header.stamp = clock_->now()`; er übernimmt dort weder den Quellstempel noch
einen Fingerprint der statischen `/map`-Eingabe. Keine ROS-Nodes, Topics,
Kartendaten oder Geräte wurden dafür geöffnet.

**Nachgewiesene Datenwege:**

| Quelle / Ergebnis | Tatsächlich vorhandener Bezug | Fehlender Beleg |
|---|---|---|
| Explorer `/map` | Vollständiges `OccupancyGrid` mit Frame, Quellstempel, Raster, Ursprung und Zellen; gespeichert werden Nachricht und monotone Empfangszeit. | Explorer bildet oder speichert keinen Kartenmanager-Fingerprint und keine angenommene Revision. |
| `robot_map_manager` `/map` | Validiert dieselben Rohfelder, bildet SHA-256 über Raster, Frame, Ursprung und Zellen und veröffentlicht Fingerprint, `source_stamp_ns`, Frame sowie `accepted_maps`. | Sein Status kennzeichnet nicht, welche spätere Nav2-Master-Costmap diese Rohkarte bereits verarbeitet hat. |
| Nav2 `/global_costmap/costmap` | Neuer Frame-/Publikationsstempel, Masterraster und -zellen. Im Realprofil kombiniert der Master statische Karte, OAK-/VL53-Hindernisse und Inflation; `always_send_full_costmap` ist aktiv. | Kein Rohkartenstempel, Rohkartenfingerprint oder statischer Layerstand wird mitpubliziert; `map_load_time` wird beim publizierten Grid nicht als Herkunft gesetzt. |
| Main-`PortalPlan` | Geometrie und Ziele werden ausschließlich aus genau einer frischen Master-Costmap berechnet. | Plan enthält weder Costmap-Header/Fingerprint noch Rohkartenidentität, Detektor-ID, Beobachtungs-ID, Revision oder Unsicherheit. |
| HWT-Portalplan | Getrennte Costmap-Brücken wie Main; zusätzlich verbundene Engstellen aus einer rohen Karte mit anschließender Erreichbarkeitsprüfung in der Costmap. Beide Eingänge müssen einzeln höchstens fünf Sekunden alt sein. | Die beiden neuesten Cachewerte werden nicht als zusammengehöriges Paar belegt; auch `connected_traversable` trägt keine Rohkarten- oder Costmapidentität. |
| Lokaler Primärstand | Portalplan und Portalplanungsmodul entsprechen hinsichtlich Provenienz dem Main-Pfad; lokale Konturarbeit ergänzt keine Kartenidentität. | Der lokale Mischstand löst die Korrelation nicht und bleibt keine Integrationsbasis. |

**Entscheidung:** Die Kartenmanagerrevision darf einem Portalplan weder als
„zuletzt gesehen“, anhand gleicher Frames/Metadaten noch über ein Zeitfenster
zugewiesen werden. Die Costmap-Headerzeit ist bei Nav2 1.1.20 nur deren
Publikationszeit. Ein Costmap-Fingerprint wäre wegen statischem,
dynamischem und Inflationsinhalt nicht mit dem Rohkartenfingerprint
gleichzusetzen. Auch zwei jeweils frische Nachrichten können aus
unterschiedlichen Rohkartenständen stammen. Deshalb bleiben Main- und
HWT-Costmap-only-Pläne für den WE-M2-Schatten fail-closed gesperrt.

Der kleinste belastbare Pfad beginnt stattdessen bei genau der rohen
Kartenmomentaufnahme, auf der eine rein passive Erkennung läuft. Ein Adapter
darf den Kartenmanagerkontext und `accepted_maps` nur übernehmen, wenn der
vollständige Rohkartenfingerprint, `source_stamp_ns` und Frame exakt mit dem
aktuellen `MapStatusCorrelationResult` übereinstimmen. Ein Nullstempel wird
nicht durch Ankunftszeit ersetzt; er muss auf beiden Seiten identisch sein und
der Inhaltsfingerprint bleibt maßgeblich. Abweichung, inzwischen weitergelaufener
Managerstatus oder fehlende Identität verwirft den Kandidaten. Beobachtungs-IDs
dürfen nicht aus einer Listenposition entstehen, sondern müssen später aus
Detektorart, korrelierter Quellenidentität und kanonischer Geometrie stabil
gebildet werden. Strukturevidenz bleibt zunächst `insufficient`.

Diese Entscheidung verändert weder Nav2 noch die reale Costmap. Die vorhandene
HWT-Rohkartenerkennung ist eine mögliche spätere Detektorquelle, aber ihre
funktionale Übernahme ist damit weder beschlossen noch gemerged. Eine
Costmap-basierte Erreichbarkeitsprüfung darf später zusätzliche passive
Diagnose sein; ohne explizite Upstream-Linie darf sie die Rohkartenrevision
nicht bestätigen oder ersetzen.

**Ausgeführte Prüfungen:** Die unveränderte vollständige Explorer-Suite auf
`eec8c5e` bestand mit **451 passed**. `git diff --check` bestand. Zusätzlich
wurden das installierte Nav2-Paket als Version **1.1.20** und dessen passende
Publisherimplementierung quellenbasiert geprüft. Das sind Quell- und
Softwarebefunde, keine ROS-, Zielsystem-, Karten-, Fahr- oder Hardwareabnahme.

**Nächster abgegrenzter Schritt WE-M2/V:** Neues reines Modul
`src/explore/explore/portal_source_adapter.py`, neue zugehörige Unit-Tests und
diese STATUS.md. Ein begrenzter Rohkarten-Identitätswert und ein Korrelator
akzeptieren ausschließlich die exakte Übereinstimmung mit einem
`MapStatusCorrelationResult` und liefern dann dessen Kontext/Revision;
Fingerprint-, Stempel-, Frame-, Typ- und Epochenfehler schlagen atomar fehl.
Noch keine Fingerprintberechnung aus ROS-Nachrichten, kein Detektoraufruf, keine
Node-/Parameter-/Launchänderung und keine Portalzuführung.

**Rückfallweg:** WE-M2/U ändert ausschließlich diese STATUS.md. Den
Dokumentationscommit beziehungsweise gestapelten Review-PR zurücknehmen;
WE-M2/T und die standardmäßig deaktivierte Schattenhülle bleiben unverändert.
Kein Betriebs- oder Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/T: regionaler Fortschritt ist kein Wohnungsabschluss

**Entscheidung / Umfang:** `RegionSnapshot` führt zusätzlich zu Seen, Entered
und Eintrittszähler einen eigenen `RegionExplorationState`. Er beginnt mit
`unassessed` und kann durch einen expliziten `RegionExplorationUpdate` nur über
`in_progress` nach `complete_candidate` fortschreiten. Das Update trägt eine
eindeutige Update-ID, Portal-/Kartenkontext, Kartenrevision, Regions-ID und einen
begründenden Text. Identisches Replay ist wirkungslos; widersprüchliche IDs,
fremde Kontexte, unbekannte Regionen, veraltete Revisionen, Sprünge und
Rückstufungen schlagen geschlossen fehl. Eine eigene harte Verlaufsgrenze
verhindert unbegrenztes Wachstum.

Der Zustand besitzt ausdrücklich keine Abschlussautorität: `complete_candidate`
besagt nur, dass ein späterer WE-M3-Vertrag diese Region erneut bewerten darf.
Das Graphmodul liest weder Frontiers noch Karten, Zeit, ROS oder Planer und
erzeugt keine Ziele. Bei einer Regionsvereinigung gewinnt bei abweichenden
Zuständen der konservativere Wert samt Merge-Grund und -Revision. Eine
Geometrieteilung setzt beide resultierenden Umfänge explizit auf `unassessed`,
weil keiner stillschweigend den Kandidatenstatus der alten Gesamtfläche erben
darf. Aufgaben, Portalenden, Aliase und der aktuelle Regionsbezug folgen dabei
weiter den bereits geprüften Merge-/Split-Verträgen.

Die reine Schattenprojektion validiert Zustand und zusammengehörige
Grund-/Revisionsmetadaten und veröffentlicht sie geometriefrei je Region. Der
vorhandene standardmäßig deaktivierte ROS-Schattenpfad übernimmt diese additive
Ausgabe erst bei einer späteren Aufnahme des gestapelten Branches; in WE-M2/T
wurden Node, Parameter, Launches, Detektoren und Navigation nicht geändert.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und vorhandenem `robot_interfaces`-Underlay, ohne
ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2T-GRAPH-STATUS | Graph-, Status-, Schatten- und Lebenszyklusverträge gemeinsam: **221 passed**. |
| WE-M2T-EXPLORE | Vollständige Explorer-Suite einschließlich 16 neuer Fälle: **451 passed**. |
| WE-M2T-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **556 passed**. |
| WE-M2T-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **451 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2T-STATIC | `git diff --check` und `flake8 --diff` (E501/W503 ausgenommen): bestanden. |

**Offene Grenzen / Integrationsabhängigkeiten:** Kein Runtime-Eingang setzt den
neuen Regionsstatus. Kriterien und Frischefenster für `in_progress` oder
`complete_candidate` gehören in WE-M3 und dürfen nicht aus einer einzelnen
Coverage-Zahl entstehen. Die in WE-M2/S aufgeführten kombinierten
Geometrieszenarien, reale Frontierzuführung, revisionssichere Portalzuführung
und wachsende Laufzeit-/Speichermessung bleiben offen. Softwaretests belegen
weder einen realen Raumabschluss noch Zielsystem- oder Hardwareabnahme.

**Nächster abgegrenzter Schritt WE-M2/U:** Nur die vorhandenen Quellpfade von
Explorer-Karte, Nav2-Global-Costmap, Portalplan und Kartenmanagerstatus prüfen
und den kleinstmöglichen revisionssicheren Provenienzvertrag dokumentieren.
Insbesondere darf die zuletzt empfangene Kartenmanagerrevision keinem
asynchron entstandenen Portalplan nachträglich zugeschrieben werden. Falls die
vorhandenen Header-/Zeit-/Inhaltsdaten keine eindeutige Korrelation erlauben,
bleibt die Portalzuführung gesperrt und der fehlende Adaptereingang wird exakt
benannt. Betroffen zunächst nur diese STATUS.md; keine Runtimeänderung.

**Rückfallweg:** Den WE-M2/T-Commit beziehungsweise den gestapelten Review-PR
zurücknehmen. Der vorherige WE-M2/S-Stand bleibt separat reviewbar. Da weder
Runtime, Installation, Parameter noch Geräte geändert wurden, ist kein
Betriebszustand zurückzusetzen.

### 2026-09-14 – WE-M2/S: grüne Einzeltests ersetzen keine M2-Abnahmematrix

**Bewertungsregel:** „Belegt“ bedeutet, dass ein vorhandener Test den genannten
Vertrag direkt prüft. „Teilbelegt“ bedeutet, dass reine Einzelverträge vorhanden
sind, aber die im Meilenstein verlangte Kombination oder Runtime-Zuführung
fehlt. „Offen“ darf nicht aus ähnlichen Tests als bestanden abgeleitet werden.

**Lieferumfang:**

| WE-M2-Lieferung | Nachweis | Bewertung |
|---|---|---|
| Vorläufige IDs, Regionszuordnung, Verbindungen und Revisionen | `test_start_room_hall_room_and_return_reuse_the_same_hall_region`, Gegenansicht- und Revisions-Negativtests in `test_region_graph.py` | Belegt für explizite reine Eingänge. |
| Seen und Entered getrennt | `test_unconfirmed_traversal_changes_neither_entry_nor_current_region`, Split-Zustandstests | Belegt. |
| Eigener Erkundungsstatus je Region | `RegionSnapshot` enthält nur `seen`, `entered`, `entry_count` und Referenzen. | Offen; weder Zustand noch Update-/Replayvertrag vorhanden. |
| Aufgabenbezug und Erhalt bei Korrekturen | Task-, Merge- und Split-Tests, insbesondere `test_merge_preserves_open_and_completed_tasks_without_loss` und `test_explicit_split_partitions_portal_ends_tasks_and_whole_state` | Belegt als passive Referenzlogik; keine Runtime-Frontierzuführung. |
| Bestehende Portaldetektoren, Analyse-Erosion getrennt von realer Costmap | Explorer-/Portalplanungstests prüfen Main-Geometrie; HWT besitzt zusätzliche verbundene Engstellen. Die Shadow-Runtime ruft keinen Detektor auf. | Teilbelegt; HWT/Main-Integration und revisionssichere Detektorzuführung offen. |
| Kartenkorrektur, Merge und Split | Explizite atomare Merge-/Split-Suiten einschließlich Replays und Aliasen | Teilbelegt; Entscheidung wird bewusst extern geliefert, kein Geometrieadapter. |
| Frühe passive Status-/Marker-Ausgabe | Versionierter begrenzter JSON-Status, WE-M2/Q-ROS-Smoke und Standard `false` | Status belegt; kein eigener Marker nötig. Runtime enthält bisher nur die Startregion aus Kartenstatus. |

**Pflichttests:**

| Gefordertes Szenario | Konkrete vorhandene Evidenz | Bewertung |
|---|---|---|
| Startraum–Flur–Zimmer | Gleichnamiger Drei-Regions-Test mit zwei Portalen und drei bestätigten Eintritten | Belegt als reines Graphszenario. |
| Verbundener Freiraum mit offenen Türen | Offener Bereich bleibt eine Region; unqualifizierte Kandidaten erzeugen keine Region. HWT-Detektortests liegen außerhalb der WE-Basis. | Teilbelegt; kein kombinierter Detektor–Portalgedächtnis–Graph-Test. |
| L-Flur und Schleife | Schleifen-Merge, Alias- und interner-Verbindungs-Tests | Teilbelegt; L-Geometrie und Detektorzuführung fehlen. |
| Offener Wohnbereich | `test_open_area_without_confirmed_portal_remains_one_region` und Merge nach synthetischer Fehlteilung | Teilbelegt; keine synthetische Flächengeometrie. |
| Möbelunterteilung | `test_repeated_furniture_bottleneck_evidence_never_confirms_a_portal` | Teilbelegt; kein kombinierter Graph-/Korrekturverlauf. |
| Kartenwachstum, Ursprungsrotation, simulierte Korrektur | Kartenstatuswachstum, metrische Portalnormalisierung nach Ursprung/Auflösung sowie Merge-/Split-Suiten | Teilbelegt; kein durchgängiges Szenario mit rotierter/korrigierter Geometrie. |
| Betrachten ohne Eintritt | Unqualifizierter Kandidat ändert nur Gedächtnis; unbestätigte Durchfahrt ändert weder Eintritt noch aktuelle Region. | Belegt als reine Zustandsgrenze. |
| Rückkehr in denselben Flur | Drei-Regions-Test kehrt über dasselbe zweite Portal in exakt dieselbe Flur-ID zurück. | Belegt als reine Graphlogik. |
| Merge/Split ohne verlorene Aufgaben | Vollständige Zuordnung aller Portalenden/Aufgaben, atomare Negativfälle und Merge nach Split | Belegt. |

**Abnahmekriterien:**

| WE-M2-Abnahme | Nachweis | Bewertung |
|---|---|---|
| Derselbe Flur erhält keine neue ID | Rückkehr- und Gegenansichttests | Belegt als reine Logik. |
| Unsegmentierte Frontiers bleiben global sichtbar | `test_task_filters_do_not_change_inventory` erhält eine Frontier-Referenz trotz Filterung. Der Explorer speist seine realen Frontiers aber nicht in den Graphen. | Teilbelegt; Runtime-Vertrag offen. |
| Rohkarte und Nav2-Kosten unverändert | Shadow-Callback verarbeitet nur Kartenmanager-`String`; kein Karten-/Costmap-Objekt oder Planer wird übergeben. | Quellenbasiert belegt, aber kein gezielter Mutations-/ROS-Vertragstest. |
| Keine Navigationsziele oder Fahrbefehle | Node-Vertrag sperrt Portaladapter; Shadow-Callbacks besitzen nur Lebenszyklus und String-Publisher. Deaktivierter/aktivierter ROS-Smoke ohne Action. | Softwarebelegt; keine Hardwareaussage. |
| Veraltete Daten werden gemeldet | Revisions-, Alters-, Missing- und monotone Lebenszyklustests einschließlich WE-M2/R | Belegt als Softwarevertrag; echter 2,0-s-Zielsystemgrenzfall offen. |
| Laufzeit/Speicher bei wachsender synthetischer Karte begrenzt | Harte Kapazitäten für Portale, Beobachtungen, Regionen, Verbindungen, Aufgaben, Historien und 1-MiB-JSON; atomare Grenztests | Teilbelegt; kein wachsender Szenario-/Zeit-/Speichermesslauf. |
| Rückfall | `region_graph_shadow_enabled: false`; ROS-OFF-Inventar ohne Shadow-Topic | Belegt für die gestapelte Main-Basis, nicht für HWT/lokalen Mischstand. |

**Gesamtergebnis:** WE-M2 ist nicht abgenommen. Die Matrix verhindert
insbesondere, dass Kapazitätstests als Laufzeitmessung, getrennte Geometrietests
als durchgängige Wohnungsgrundrisse oder die kartenbasierte Ein-Regions-Ausgabe
als Portal-/Frontierintegration ausgegeben werden.

**Ausgeführte Prüfungen:** Alle Testnamen und Behauptungen wurden gegen die
gestapelte Spitze `8bdb8f4` und die verbindlichen Abschnitte in Strategie und
MEILENSTEINEN gelesen. Die unveränderte Explorer-Suite wurde erneut ausgeführt:
**435 passed**. `git diff --check` bestand. Keine ROS-Nodes, Geräte, Karten oder
Aktoren wurden gestartet.

**Nächster abgegrenzter Schritt WE-M2/T:** Zuerst die kleinste unabhängige
Lieferlücke schließen: ein passiver, explizit revisionsgebundener
Regions-Erkundungsstatus, getrennt von Seen und Entered. Mindestens
`unassessed`, `in_progress` und `complete_candidate` unterscheiden; letzterer
ist ausdrücklich kein WE-M3-Wohnungsabschluss. Updates benötigen stabile IDs,
Grund und Revision, sind replayfest und dürfen abgeschlossene Kandidaten in
WE-M2 nicht stillschweigend wieder öffnen. Merge/Split müssen den konservativeren
Status erhalten beziehungsweise explizit zuordnen. Betroffen sind nur
`region_graph.py`, `test_region_graph.py`, `region_graph_status.py`, dessen Test
und diese STATUS.md. Keine Runtime-, ROS-, Detektor-, Ziel- oder Fahrwirkung.

**Rückfallweg:** WE-M2/S ändert nur diese STATUS.md; der Abschnitt kann
entfernt oder der Dokumentations-PR geschlossen werden. Kein Funktions-,
Installations- oder Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/R: Kartenalter folgt der monotonen Empfangszeit

**Entscheidung / Umfang:** `RegionGraphShadowLifecycle` speichert neben dem
letzten gültigen Kartenstatus dessen monotonen Empfangszeitpunkt. Bei jeder
späteren `build_status_json()`-Ausgabe wird
`source_map_age_seconds` als vom Kartenmanager gemeldetes Alter plus monotone
Differenz seit diesem Empfang projiziert. Der unveränderliche korrelierte
Status wird dafür nur per `dataclasses.replace()` als Ausgabewert kopiert; weder
Kartenrevision, Fingerprint, Kontext noch Korrelatorzustand werden umgeschrieben.

Ein neuer, nicht als Replay erkannter periodischer Kartenmanagerstatus setzt
den Empfangsanker auf seinen expliziten monotonen Eingangszeitpunkt und bringt
sein eigenes gemessenes Kartenalter mit. Ein byte-/feldgleich decodiertes Replay
nimmt weiterhin an der globalen monotonen Reihenfolge teil, setzt den Anker aber
nicht neu. Wartestatus vor Sitzungsbeginn, Decoder-/Epochenfehler, ungültige oder
rückläufige Zeit und fehlgeschlagene Ausgabe verändern den Kartenanker nicht.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und vorhandenem `robot_interfaces`-Underlay, ohne
ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2R-AGE | Erweiterte Lebenszyklus-Suite mit Fortschreibung, Replay und neuer periodischer Verankerung: **53 passed**. |
| WE-M2R-EXPLORE | Vollständige Explorer-Suite: **435 passed**. |
| WE-M2R-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **540 passed**. |
| WE-M2R-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **435 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2R-STATIC | `git diff --check` und `flake8 --diff` (E501/W503 ausgenommen): bestanden. |

**Nächster abgegrenzter Schritt WE-M2/S:** Ausschließlich in dieser STATUS.md
eine nachprüfbare Matrix aller WE-M2-Pflichttests und Abnahmekriterien gegen
konkrete Testnamen beziehungsweise fehlende Nachweise erstellen. Insbesondere
dürfen reine Einzelverträge nicht ohne kombiniertes Szenario als Nachweis für
Startraum–Flur–Zimmer, L-Flur/Schleife, offenen Wohnbereich,
Möbelunterteilung, Betrachten ohne Eintritt, Flurrückkehr oder begrenzte
Laufzeit/Speicher gelten. Danach genau eine kleinste Lücke auswählen; keine
Funktions-, ROS-, Fahr- oder Hardwareänderung in WE-M2/S.

**Rückfallweg:** Den zusätzlichen Karten-Empfangsanker und die
Ausgabe-Fortschreibung aus Lebenszyklus und Tests entfernen sowie diesen
Statusabschnitt zurücknehmen beziehungsweise den gestapelten PR schließen.
WE-M2/Q bleibt standardmäßig deaktiviert; kein Runtime-, Installations- oder
Gerätezustand ist zurückzusetzen.

**Abnahmegrenze:** Die Tests belegen deterministische monotone Algebra, keine
reale Kartenmanagerperiode, DDS-Latenz, Jetson-Uhr, Zielsystemlast, Portal-,
Navigations- oder Hardwarefunktion. Insbesondere ist der 2,0-s-Grenzfall nicht
allein durch bestandene Softwaretests freigegeben.

### 2026-09-14 – WE-M2/Q: ROS-Hülle sieht nur Kartenstatus und bleibt opt-in

**Entscheidung / Umfang:** `ExploreNode` deklariert fünf neue Parameter. Mit
`region_graph_shadow_enabled: false` kehrt die Initialisierung vor Erzeugung
jedes Schattenzustands, Publishers, Subscribers oder Timers zurück. Bei
Aktivierung sind nichtleere explizite Werte für
`region_graph_shadow_session_id` und
`region_graph_shadow_start_observation_id` Pflicht; Kartenstatus-Eingang und
Schattenausgang müssen nichtleer und voneinander sowie vom bestehenden
Explorerstatus getrennt sein.

Der opt-in Pfad besitzt genau einen `RegionGraphShadowLifecycle` und eine eigene
Sperre, weil der Explorer eine `ReentrantCallbackGroup` verwendet. Subscription
und Publisher sind `std_msgs/String` mit KeepLast 1, Reliable und Transient
Local. Der eigene 1,0-s-Timer begrenzt die Ausgabe auf höchstens 1 Hz und
publiziert vor einem vollständigen Kartenstatus nichts. Callback und Timer lesen
je Aufruf genau einmal `time.monotonic()`. Unerwartetes JSON, Zeitrücklauf,
Epochenwechsel oder Serialisierungsfehler werden einmal protokolliert und sperren
nur den Schattenpfad bis zum Prozessneustart; sie werden nicht in Action,
Navigation oder bestehende Statusausgabe weitergereicht.

Es gibt keinen Import und keinen Aufruf von `PortalPlanCandidate` oder
`observe_portal_plan()` im Node. Weder bestehendes `/explore/status_json` noch
Portalplanung, Geschwindigkeits-Publisher, Nav2-Client, Actionserver oder
Launchdatei wurden für den Schattenpfad verändert. Die drei funktional
betroffenen Dateien sind `explore_node.py`, `explore_params.yaml` und der
Explorer-Vertragstest.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit ROS Humble und
vorhandenem `robot_interfaces`-Underlay, ohne Sensor-, Karten- oder
Gerätezugriff und ohne Nav-Action oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2Q-CONTRACT | Explorer-Vertrag und Lebenszyklus gezielt: **102 passed**. |
| WE-M2Q-EXPLORE | Vollständige Explorer-Suite: **432 passed**. |
| WE-M2Q-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **537 passed**. |
| WE-M2Q-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **432 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2Q-STATIC | `compileall`, `git diff --check` und `flake8 --diff` (E501/W503 ausgenommen): bestanden. |
| WE-M2Q-ROS-GATE | Aktivierung ohne die beiden Pflicht-IDs: Node bricht vor seinen Explorer-ROS-Schnittstellen mit dem erwarteten `ValueError` ab. |
| WE-M2Q-ROS-OFF | Separater Explorer in DDS-Domain 231: Topicliste enthielt `/explore/status_json`, aber kein `/explore/region_graph/status_json`. |
| WE-M2Q-ROS-ON | Separater Explorer in DDS-Domain 232 mit expliziten Test-IDs: synthetischer gültiger Kartenmanagerstatus erzeugte einen passiven Ein-Regions-JSON-Status auf dem getrennten Shadow-Topic. |

Die ROS-Prozesse wurden mit SIGINT beendet. Die lokale CycloneDDS-Konfiguration
versuchte auch in den separaten Domains erfolglos bekannte Peer-Adressen zu
erreichen (`ddsi_udp_conn_write ... retcode -3`); im Topic-Inventar erschienen
keine fremden Roboter-Nodes. Das ist ein Umgebungsbefund und keine Aussage über
Zielsystem-Discovery oder Netzwerkfreigabe.

**Neu belegte Grenze / nächster Schritt WE-M2/R:** Der Kartenmanagerumschlag
liefert `map.age_seconds` nur für seinen Erzeugungszeitpunkt. Der Lebenszyklus
übernimmt diesen Wert derzeit unverändert in jede spätere 1-Hz-Projektion.
Damit ist zwar der gesamte Schattenstatus nach Ablauf des monoton geführten
Graphalters fail-closed, das einzelne Feld `source_map.age_seconds` altert aber
zwischen zwei Managerstatus-Nachrichten nicht. WE-M2/R ergänzt im reinen
Lebenszyklus den monotonen Empfangszeitpunkt zur ausgegebenen Kartenquellzeit.
Exakter Replay darf den ursprünglichen Kartenstand dabei nicht verjüngen; die
genaue Regel ist durch Negativtests festzulegen. Keine ROS- oder Parameteränderung.

**Rückfallweg:** `region_graph_shadow_enabled: false` erzeugt bereits keine
zusätzliche Schnittstelle. Vollständiger Rückfall ist Revert der drei
Funktions-/Testdateien und dieses Statusabschnitts beziehungsweise Schließen des
gestapelten PR. Kein Karten-, Installations- oder Gerätezustand muss
zurückgesetzt werden.

**Abnahmegrenze:** Die Tests belegen Softwarevertrag und synthetischen
ROS-Nachrichtenfluss. Nicht geprüft wurden Jetson-Last, echtes
Kartenmanager-Timing, der 2,0-s-Grenzfall, HWT-/lokale Codeintegration,
Portalprovenienz, qualifizierte Evidenz, reale Karten, TF, Sensorik, Navigation,
Aktorik oder Hardware.

### 2026-09-14 – WE-M2/P: erster ROS-Schritt bleibt kartenbasiert und passiv

**Verglichene Stände:** Nach erfolgreichem `git fetch origin` wurden Main
`05439c7`, HWT `1d91229`, der unverändert belassene lokale Primärbaum und die
gestapelte WE-Spitze `1d27c94` quellenbasiert verglichen. Main und die WE-Spitze
besitzen denselben bestehenden Explorer-Laufzeitcode. HWT ergänzt insbesondere
Engstellen in verbundenem Freiraum und weitere Portalabläufe; der lokale Baum
enthält abweichende, teilweise nicht eingecheckte strukturierte Erkundung.
Keiner der beiden letztgenannten Stände ist eine saubere Basis für diesen kleinen
Integrationsschritt. Die laufende Arbeitskopie wurde weder gewechselt noch
verändert.

**Besitz und Einfügepunkte für WE-M2/Q:** Der bestehende `ExploreNode` bleibt
einziger Prozessbesitzer. In `__init__` werden neben den vorhandenen Parametern
nur `region_graph_shadow_enabled` (Standard `false`), explizite nichtleere
Sitzungs- und Startbeobachtungs-ID, Kartenstatus-Topic mit Standard
`/robot_map_manager/status_json` sowie das getrennte Ausgabe-Topic
`/explore/region_graph/status_json` deklariert. Nur bei Aktivierung werden genau
ein `RegionGraphShadowLifecycle`, eine eigene Sperre, eine String-Subscription,
ein String-Publisher und ein eigener 1,0-s-Timer erzeugt. Die Subscription und
der Publisher verwenden KeepLast 1, Reliable und Transient Local passend zum
Kartenmanagerstatus und zur Entscheidung aus WE-M2/F. `explore.launch.py`
benötigt keine Änderung, weil es das vorhandene YAML-Profil bereits lädt.

Der Kartenstatus-Callback erfasst `time.monotonic()` genau einmal pro Nachricht
und übergibt Text und Zeitpunkt an den reinen Lebenszyklus. Der getrennte Timer
erfasst die monotone Zeit genau einmal, publiziert erst nach aktivem
Sitzungsstart und niemals häufiger als 1 Hz. Eine eigene Sperre ist wegen der
vorhandenen `ReentrantCallbackGroup` erforderlich. Ausnahmen des Schattenpfads
dürfen weder den bestehenden 1-Hz-Status noch Action, Nav2-Client,
Geschwindigkeitspublisher oder Zielwahl erreichen. Ein Decoder-, Zeitfolge-
oder Kartenepochenfehler setzt den Schattenpfad für diesen Prozessstart
fail-closed; insbesondere wird keine Sitzung automatisch zur neuen Epoche
umgebogen. Ein Neustart mit neuer expliziter Sitzungs-ID bleibt der
Wiederanlaufweg.

**Bewusst fehlende Portalzuführung:** Main erstellt `PortalPlan` aus der
Nav2-Global-Costmap; HWT ergänzt zwar einen zweiten, teilweise auf `/map`
gestützten Detektor, erzeugt am Ende aber denselben laufzeitnahen Plan ohne
stabile Beobachtungs-ID, Kartenrevision und Unsicherheit. Es gibt keinen
belegten Vertrag, der den Erstellungsstand der asynchronen Global-Costmap mit
dem Fingerprint und der Revision des Kartenmanagerstatus verbindet. WE-M2/Q
darf daher keinen `PortalPlanCandidate` erzeugen. Das erfordert zuerst einen
separaten, reviewbaren Costmap-/Karten-Korrelations- und Identitätsvertrag.

**Betroffene Dateien des nächsten Schritts:** ausschließlich
`src/explore/explore/explore_node.py`,
`src/explore/config/explore_params.yaml`,
`src/explore/test/test_explore_contract.py` und diese STATUS.md. Keine Änderung
an Portalplanung, Action-/Statusschema, Navigation, Bring-up, Kartenmanager,
Semantik, Launches oder Gerätekonfiguration.

**Prüfplan für WE-M2/Q:** Quellvertragstests müssen belegen, dass der Standard
deaktiviert ist, dann keine Schatten-ROS-Schnittstelle entsteht und der
bestehende Status unverändert bleibt. Aktivierte Tests prüfen Pflicht-IDs,
exaktes Topic/QoS, getrennten Timer, genau einen monotonen Zeitwert je Callback,
Warten auf unvollständigen Kartenstatus, Ausgabe erst nach gültiger Karte sowie
dauerhaftes Fail-closed bei ungültigem JSON, Zeitrücklauf und Epochenwechsel.
Danach vollständige Explorer-Suite, isolierter `colcon build/test` und ein
motorloser ROS-Topic-Test mit deaktiviertem und aktiviertem Pfad. Der
2,0-s-Frischegrenzfall ist als Messwert zu protokollieren, nicht stillschweigend
umzukonfigurieren. Keine Nav-Action, keine Aktoren und keine Hardwareabnahme.

**Rückfallweg:** Da WE-M2/P nur diese STATUS.md ändert, kann der Abschnitt
entfernt oder der Dokumentations-PR geschlossen werden. Für WE-M2/Q ist der
Rückfall `region_graph_shadow_enabled: false`; vollständig werden die drei
Runtime-/Parameter-/Teständerungen revertiert. Der bestehende
`/explore/status_json` und alle Fahrpfade dürfen dabei keinen Zustand verlieren.

**Grenzen der Aussage:** Keine ROS-Nodes, Karten, Geräte oder Aktoren wurden
gestartet; kein Zielsystem, Timing, Discovery, QoS-Replay, Speicherbedarf,
Portal, Durchfahrt oder Hardwareverhalten ist damit abgenommen.

### 2026-09-14 – WE-M2/O: Portal-Replay verjüngt die Quelle nicht

**Entscheidung / Umfang:** `RegionGraphShadowLifecycle.observe_portal_plan()`
nimmt nach dem ersten vollständigen Kartenstatus genau den bestehenden
`PortalPlanCandidate` aus WE-M2/H und einen expliziten monotonen
Beobachtungszeitpunkt entgegen. Vor Mutation werden aktiver Sitzungsbesitz,
exakter `PortalMapContext` und eine Revision geprüft, die weder vor dem
Graphstart noch nach dem letzten korrelierten Kartenstatus liegt. Die vorhandene
Sitzung normalisiert den Kandidaten weiterhin ausschließlich zu unqualifizierter
`INSUFFICIENT`-Evidenz.

Jede erfolgreich gespeicherte neue Beobachtung setzt den Portal-
Änderungszeitpunkt, auch wenn ihre Zuordnung mehrdeutig bleibt und deshalb kein
Portal verändert wird. Ein exaktes Beobachtungs-ID-Replay wird zwar idempotent
angenommen und nimmt an der globalen monotonen Reihenfolge teil, setzt diesen
Zeitpunkt aber nicht neu. Damit kann wiederholtes Abspielen derselben Beobachtung
keine Portalfrische vortäuschen. Die Statusausgabe berechnet das Portalalter nun
intern; ohne Beobachtung bleibt die Quelle `missing`. Der Graphzeitpunkt bleibt
von Portalplänen unverändert.

Fremder Kontext, Zukunfts- oder Alt-Revision, ungültiger Kandidat, Zeitrücklauf
und Kapazitäts-/Adapterfehler verändern weder Portalgedächtnis noch den letzten
gültigen Zeitstand. Die öffentliche Lebenszyklus-API besitzt weiterhin keine
Qualifikation, Durchfahrt, Graphverbindung, Zielwahl oder Resetfunktion.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2O-PORTAL | Erweiterte Lebenszyklus-Suite: **50 passed**. |
| WE-M2O-EXPLORE | Gesamte Explorer-Suite: **425 passed**. |
| WE-M2O-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **530 passed**. |
| WE-M2O-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **425 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2O-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden eine echte monotone Uhr, ein realer Explorer-Portalplan,
qualifizierende Struktur-/LiDAR-Evidenz, eine reale Topic-Nachricht,
ROS-Subscription/QoS/Discovery, Publisher, Jetson-Laufzeit/Speicher, reale Karten,
Sensorik, Footprint, Kollisionswirkung oder Hardware. Eine gespeicherte
unqualifizierte Beobachtung bestätigt weder Tür, Durchfahrt noch Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/P:** Ausschließlich diese STATUS.md anhand
des nach `git fetch origin` belegten Main-, HWT-, lokalen und gestapelten
WE-Stands fortschreiben. Exakte Einfügepunkte und Besitzverhältnisse im Explorer,
Quelle der `PortalPlanCandidate`-Felder, Erzeugung/Validierung der Sitzungs-ID,
Verwendung einer monotonen Uhr, Kartenstatus-Subscription, getrenntes
`/explore/region_graph/status_json`, QoS, maximal 1 Hz, standardmäßig deaktivierte
Parameter und Fehler-/Epochenverhalten festlegen. Noch kein funktionaler
Branchmerge und keine Node-, Launch-, Parameter-, Ziel- oder Fahrsoftware.

**Rückfallweg:** Portalzuführung und Portalzeitpunkt aus Lebenszyklus und Test
entfernen sowie diesen WE-M2/O-Statusabschnitt zurücknehmen beziehungsweise den
gestapelten PR schließen. WE-M2/A bis N bleiben separat reviewbar; kein Runtime-,
Installations- oder Gerätezustand ist zurückzusetzen.

### 2026-09-14 – WE-M2/N: Graphfrische beginnt bei der tatsächlichen Erzeugung

**Entscheidung / Umfang:** `RegionGraphShadowLifecycle.accept_map_status_json()`
verlangt nun für jeden formal gültigen Eingang einen expliziten nichtnegativen,
endlichen `received_monotonic_seconds`-Wert. Auch ein gültiger wartender
Nichtverfügbarkeitsstatus nimmt an dieser Reihenfolge teil. Der erste erfolgreiche
Kartensnapshot setzt neben der Sitzung genau einmal den Graph-Änderungszeitpunkt.
Periodischer Status, Replay und normales Kartenwachstum ändern diesen Zeitpunkt
nicht, weil sie den Regionsgraphen nicht verändern.

`build_status_json()` erhält nur noch einen expliziten monotonen Jetztwert. Das
Graphalter ist dessen Differenz zum Sitzungsstart; das Portalgedächtnis bleibt
ohne Portalzuführung korrekt `missing`. Jede erfolgreiche Ausgabe nimmt ebenfalls
an derselben monotonen Reihenfolge teil. Rücklauf, boolesche Werte, NaN, Unendlich
oder negative Zeiten scheitern vor Zustandsänderung. Decoder-, Epochen- oder
Serialisierungsfehler übernehmen den zugehörigen Zeitwert nicht. Die Klasse liest
selbst keine Uhr und vermischt die monotone Prozesszeit nicht mit der Unix-/ROS-
Zeit im Kartenmanagerstatus.

**Nachgewiesenes Verhalten:** Das Graphalter ist beim Start null und wächst über
periodischen Kartenstatus sowie Fingerprint-/Revisionsfortschritt hinweg weiter.
Fehlender Portalstand bleibt unabhängig davon `missing`. Wartestatus, Karteninput
und Statusausgabe bilden eine gemeinsame nicht rückläufige Reihenfolge. Ein nach
einem Fehler liegender, aber gegenüber dem letzten erfolgreichen Eingang gültiger
Zeitpunkt bleibt annehmbar; damit ist die Fortschreibung atomar belegt.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2N-MONOTONIC | Erweiterte Lebenszyklus-Suite: **36 passed**. |
| WE-M2N-EXPLORE | Gesamte Explorer-Suite: **411 passed**. |
| WE-M2N-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **516 passed**. |
| WE-M2N-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut; Pakettest: **411 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2N-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden eine reale monotone Uhr, Prozessneustart, Portalzuführung,
eine reale Topic-Nachricht, ROS-Subscription/QoS/Discovery, Publisher,
Jetson-Laufzeit/Speicher, reale Karten, Portal-/LiDAR-Evidenz, Sensorik,
Footprint, Kollisionswirkung oder Hardware. Synthetische Zeitfortschreibung ist
keine Zielsystem- oder Hardwareabnahme.

**Nächster abgegrenzter Schritt WE-M2/O:** Nur
`region_graph_shadow_lifecycle.py`, dessen Test und diese STATUS.md. Eine
`observe_portal_plan()`-Methode übernimmt nach aktivem Sitzungsstart einen
`PortalPlanCandidate` und dessen expliziten monotonen Beobachtungszeitpunkt.
Kontext und Revision müssen vor Mutation gegen Sitzung, Graphstart und aktuellen
Kartenstatus geprüft werden. Neue einschließlich mehrdeutiger Beobachtungen setzen
den Portal-Änderungszeitpunkt; exaktes Replay tut dies nicht. Die Statusausgabe
berechnet daraus intern Portalalter. Keine qualifizierte Evidenz, Graphverbindung,
Durchfahrt, echte Uhr, ROS-, Node-, Launch-, Parameter-, Ziel- oder Fahrsoftware.

**Rückfallweg:** Die monotonen Zeitargumente und die interne Graphalterführung
aus Lebenszyklus und Test entfernen sowie diesen WE-M2/N-Statusabschnitt
zurücknehmen beziehungsweise den gestapelten PR schließen. WE-M2/A bis M bleiben
separat reviewbar; kein Runtime-, Installations- oder Gerätezustand ist
zurückzusetzen.

### 2026-09-14 – WE-M2/M: ein Besitzer über Decoder, Korrelator und Sitzung

**Entscheidung / Umfang:** Neu `region_graph_shadow_lifecycle.py` mit
`RegionGraphShadowLifecycle`. Die reine Klasse erhält Sitzungs-ID, erwarteten
Kartenframe und Startbeobachtungs-ID explizit und besitzt genau einen
`MapManagerStatusCorrelator`. Sie decodiert jeden übergebenen Status über den
WE-M2/L-Vertrag. Vor dem ersten vollständigen Kartensnapshot ist ihr Zustand
`waiting_for_map`; ein formal gültiger Nichtverfügbarkeitsstatus erzeugt weder
Kontext noch Region oder Schattenstatus.

Das erste gültige Korrelationsresultat erzeugt intern einen revisionsgleichen
`RegionSeed` und genau eine `RegionGraphShadowSession`. Periodischer Kartenstatus,
Kartenwachstum und Replay werden in denselben Besitzer fortgeführt. Der
Lebenszyklus liefert erst danach einen passiven Status und übernimmt weiterhin
das Kartenalter aus dem Korrelationsresultat. Konfigurationsfehler werden vor
jedem Eingang abgewiesen. Decoder-/Korrelationsfehler, Zählerrücklauf,
Framewechsel und erneute Nichtverfügbarkeit verändern den letzten gültigen
Sitzungsstand nicht.

Es gibt absichtlich keine Resetmethode: Nach einer erkannten Epochengrenze muss
der spätere Runtime-Besitzer eine neue explizite Sitzungs-ID und eine neue
`RegionGraphShadowLifecycle` anlegen. Ebenso gibt es in diesem Schritt keine
Portal-, Qualifikations-, Durchfahrts-, Ziel-, Uhr-, Datei- oder ROS-API. Die
bestehenden begrenzten Karten-, Portal-, Graph- und Statusrichtlinien werden
unverändert an die jeweiligen Besitzer weitergereicht.

**Ausgeführte Prüfungen:** Lokaler x86_64-Arbeitsplatz mit eingeblendeter
ROS-Humble-Python-Umgebung und `robot_interfaces` aus dem vorhandenen Underlay,
aber ohne ROS-Start, Gerätezugriff, Kartendaten oder Bewegung:

| Test-ID | Ergebnis |
|---|---|
| WE-M2M-LIFECYCLE | Neue Lebenszyklus-Suite: **22 passed**. |
| WE-M2M-EXPLORE | Gesamte Explorer-Suite: **397 passed**. |
| WE-M2M-ADJACENT | Explorer-, Kartenmanager-, Semantikmanager- und Semantik-Launch-Vertragssuiten gemeinsam: **502 passed**. |
| WE-M2M-COLCON | Temporärer isolierter `colcon build --packages-select explore`: 1 Paket gebaut und neues Modul installiert; Pakettest: **397 Tests, 0 Fehler, 0 Fehlschläge, 0 Skips**. |
| WE-M2M-STATIC | `flake8` (E501/W503 ausgenommen) und `git diff --check`: bestanden. |

Nicht geprüft wurden monotone Laufzeitwerte, Portalzuführung, eine reale
Topic-Nachricht, ROS-Subscription/QoS/Discovery, Publisher, Restart im
Prozessverbund, Jetson-Laufzeit/Speicher, reale Karten, Portal-/LiDAR-Evidenz,
Sensorik, Footprint, Kollisionswirkung oder Hardware. Der reine Lebenszyklus
bestätigt weder Karte, Portal, Durchfahrt noch Fahrfreigabe.

**Nächster abgegrenzter Schritt WE-M2/N:** Nur
`region_graph_shadow_lifecycle.py`, dessen Test und diese STATUS.md. Beim
Kartenstatuseingang einen expliziten, nichtnegativen endlichen monotonen
Empfangszeitpunkt verlangen. Der erste erfolgreiche Sitzungsstart setzt daraus
den Graph-Änderungszeitpunkt; spätere reine Kartenupdates verändern ihn nicht.
Die Statusausgabe erhält ebenfalls einen expliziten monotonen Jetztwert und
berechnet das Graphalter intern, während Portalalter bis zu einer späteren
Portalzuführung `missing` bleibt. Zeitrücklauf und ungültige Werte scheitern
atomar. Keine Uhr lesen und keine ROS-, Portal-, Node-, Launch-, Parameter-,
Ziel- oder Fahrsoftware.

**Rückfallweg:** Das neue Lebenszyklusmodul, dessen Test und diesen
WE-M2/M-Statusabschnitt entfernen beziehungsweise den gestapelten PR schließen.
WE-M2/A bis L bleiben separat reviewbar; kein Runtime-, Installations- oder
Gerätezustand ist zurückzusetzen.

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
