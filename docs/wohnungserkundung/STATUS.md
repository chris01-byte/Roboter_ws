# Wohnungserkundung – laufender Status und Entscheidungen

**Vorhaben WE-1 · Aktualisiert: 2026-09-14**

Dies ist der einzige laufende Fortschrittsstand des Vorhabens. Die
[Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) beschreibt das Soll,
die [Roadmap](MEILENSTEINE.md) die Abnahmen und der
[Agentenauftrag](AGENTENAUFTRAG.md) den Arbeitsablauf. Historische Logs bleiben
Quellen, aber ersetzen diesen statusbezogenen Einstieg nicht.

## 1. Aktueller nächster Schritt

**WE-M0/A – Repository-Bestandsprüfung dokumentiert, zur Review.** Der
Quellvergleich und die begrenzten Offline-Prüfungen stehen in Abschnitt 5.
Der tatsächliche Jetson-Installationsstand bleibt mangels Zugriff offen; WE-M0
ist damit weder insgesamt noch auf Hardware abgenommen.

**Nächster vorgeschlagener Umsetzungsschritt nach Review: WE-M1/A**, ein kleiner
Teilschnitt von WE-M1: reine Portalidentität mit synthetischen Tests, ohne
Einbindung in den Explorer. Dateien, Prüfplan und Rückfall stehen in Abschnitt 5.
Dieser Auftrag endet mit der Übergabe; WE-M1/A wurde nicht implementiert.
Keine neue Fahrsoftware, Geräteaktivierung oder funktionale Branchübernahme.

Eine Wiederholung des Arbeitszimmer-Flur-Laufs gehört zu WE-M0/B und benötigt
zusätzlich Zielsystemprüfung, sicheren Aufbau und eine neue ausdrückliche
Freigabe. Das Schreiben oder Veröffentlichen dieses Plans erteilt diese nicht.

## 2. Git- und Evidenzbasis

| Referenz am 14.09.2026 | Nachgewiesener Umfang |
|---|---|
| Main `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1` | Über GitHub gelesen; Quellbasis des Vergleichs und des vorgeschlagenen isolierten Logikschritts. |
| HWT `1d91229dc10ff4bb791938d49aae8e9808a5dfff` auf `codex/hwt601-encoder-shadow` | Referenz, relevante Quellen und Erprobungsbericht verglichen; keine Übernahme. |
| Dokumentation `96cebee986e55cde2d10da0f86e65294e6004a82` auf `docs/wohnungserkundung-agentenplan` | PR #20 bei Prüfung offen, nicht gemerged; Grundlage dieses reinen Statusnachtrags. |
| Jetson-Installation und lokale Rohdaten | Nicht zugänglich; Quell-HEAD, installierte Dateien, aktive Overlays, Profile und Messdaten nicht unabhängig verifiziert. |
| Lokale Audit-Umgebung | Isolierte Linux-x86_64-Umgebung ohne ROS/Jetson-Installation; vier hashgeprüfte Quellexporte für reine Portaltests, kein vollständiger Robotik-Clone. |

Der [Bericht vom 11.09.2026](https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/docs/PROJECT_MEMORY.md)
dokumentiert den physischen Übergang vom Arbeitszimmer in den Flur mit
Nutzerbestätigung und anschließendem weiteren Umsehen. Er dokumentiert auch die
erneute Erkennung desselben Portals nach Geometrieänderung. Die abschließende
Softwarekorrektur ist dort mit 80 Explorer-Tests und Build-Erfolg angegeben,
aber ausdrücklich noch nicht erneut real gefahren.

Dies sind historische, im Repository berichtete Nachweise. Der neue Plan
setzt weder diese Tests noch den gesamten Wohnungslauf eigenständig auf bestanden.

## 3. Meilensteinstand

| Stufe | Stand | Fehlender Nachweis / nächste Abgrenzung |
|---|---|---|
| WE-D0 | Dokumentiert; zur Review | Dokumentationszweig/PR ist nicht automatisch Main oder Jetson-Deployment. |
| WE-M0/A | Repository-Befund dokumentiert; zur Review | Zielsystemvergleich offen; keine Gesamt- oder Hardwareabnahme. Befunde und abgegrenzte Folgebasis in Abschnitt 5. |
| WE-M0/B | Offen | Neue Baseline-/Lastprüfung und reale Wiederholung der Abschlusskorrektur. |
| WE-M1 | Geplant | WE-M1/A als isolierter Identitätskern vorgeschlagen; noch keine Implementierung. |
| WE-M2 | Geplant | Regionsgraph und passive Integration. |
| WE-M3 | Geplant | Hierarchische Policy, Abschlussvertrag und motorlose Abnahme. |
| WE-M4 | Geplant | Arbeitszimmer → Flur → weiteres Zimmer → derselbe Flur. |
| WE-M5 | Geplant | Versionsgebundene Persistenz und sichere Wiederaufnahme. |
| WE-M6 | Geplant | Wiederholbarer Abschluss des zugänglichen Wohnungsumfangs. |
| WE-M7 | Geplant, ergänzend | App-Transparenz und manuelle Benennung. |

## 4. Bekannte offene Punkte

**Codebasis:** Main und HWT sind divergiert. Für den vorgeschlagenen reinen
WE-M1/A-Kern ist keine funktionale HWT-Übernahme erforderlich. Für spätere
Laufzeitintegration bleiben explizite Entscheidungen über Detektor, Explorer,
Sensorfusion, Fahrtor und Profile nötig; siehe Abschnitt 5. Ein Dokumentationsmerge
nimmt diese Funktionen nicht mit.

**Installation und Transport:** `git fetch origin` scheiterte in der isolierten
Audit-Umgebung mit Exit 128 an DNS. Remote-Referenzen wurden ersatzweise über den
GitHub-Connector gelesen, nicht lokal erfolgreich gefetcht. Jetson-Quellbaum und
`install/` sind unbekannt; Repository-HEAD beweist keine installierte Laufzeit.

**Baseline:** Die nach dem letzten Realtest geänderte Abschlusslogik ist laut
Referenz noch nicht erneut physisch abgenommen.

**Ressourcen:** Der letzte Bericht nennt TF-Zukunftsextrapolationen und verpasste
Controllerzyklen unter SLAM-Last. Aktuellen Zustand messen, nicht aus alten Werten
als erledigt betrachten.

**Identität und Abschluss:** Ein begrenzter Portalzähler ist noch kein stabiles
Raum-/Türgedächtnis. Die Roadmap legt den allgemeinen Vertrag fest; sie behauptet
nicht, dass das neue Datenmodell bereits im Code existiert.

**Kartenintegration:** Kartenmanager und manuelle Semantik sind zwischen Main und
HWT identisch. Live-Sitzung/Kartenrevision und gespeicherter Inhaltsfingerprint
sind zu trennen. Keine automatische Überschreibung manueller Raum-IDs und keine
Lockerung der Bindungsprüfung. Zusätzlich besteht ein Dokumentations-/Codewiderspruch
zum Replay-Umschlag des Kartenmanagers; Details in Abschnitt 5.

**Abnahmegrenzen:** Grenzwerte für Identitätszuordnung, Beobachtungsfenster,
Ressourcenbudgets und Wohnungsumfang müssen vor den jeweiligen Tests begründet
festgelegt werden. Die Dokumentation ist kein Ersatz für diese Messungen.

## 5. Entscheidungslog

### 2026-09-14 – WE-M0/A: Quellbestand geprüft, Zielsystem ausdrücklich offen

**Entscheidung / Umfang:** Nur diese fachliche STATUS.md ändern. Bestehende
Detektoren und Manager wiederverwenden; keine konkurrierende Gesamtarchitektur.
Den nächsten Logikschritt auf Portalidentität begrenzen. Diese Bestandsaufnahme
ist kein Integrationsmerge, kein Deployment und keine Freigabe für WE-M0/B.

#### Arbeitsgrundlage und Grenzen

Root-AGENTS.md einschließlich WE-1-Zusatz, alle vier WE-Dokumente, Inventar,
relevante Main-/HWT-Projektgedächtniseinträge und Kartierungsanweisungen gelesen.
Im bearbeiteten Pfad `docs/wohnungserkundung/STATUS.md` gibt es auf der
Dokumentationsbasis keine zusätzlichen AGENTS.md unter `docs/` oder
`docs/wohnungserkundung/`.

In der zugänglichen Umgebung wurde keine laufende Roboter-Arbeitskopie vorgefunden.
Ein eigenes leeres Audit-Repository mit passendem `origin` wurde angelegt und
zuerst `git fetch origin` versucht: **Exit 128, `Could not resolve host:
github.com`**. Keine Remote-Tracking-Referenzen konnten so aktualisiert werden.
Die nachfolgenden GitHub-API-Lesezugriffe liefern die oben gepinnten Referenzen;
sie sind kein erfolgreicher Fetch und kein Nachweis des lokalen Jetson-Stands.
Keine vorhandene Arbeitskopie gewechselt, keine lokalen Roboteränderungen
überschrieben, kein Gerät geöffnet, kein ROS-Prozess gestartet oder beendet.

Der Statusnachtrag erhält einen eigenen Dokumentationsbranch
`docs/we-m0a-bestandspruefung` auf der noch offenen Dokumentationsbasis. Reviewziel
ist zunächst `docs/wohnungserkundung-agentenplan`, damit nur dieser Nachtrag als
Diff erscheint. PR #20 und funktionale Branches werden nicht automatisch gemerged.
Neue **Implementierung** beginnt dagegen nach erneuter Referenzprüfung auf Main;
die Dokumentationsbasis ist kein Anlass, den HWT-Gesamtstack zu übernehmen.

#### Nachgewiesener Bestand und Integrationsabhängigkeiten

**Git-Divergenz:** Gemeinsame Basis ist
`982296231eae95b1a524ed07035af52720576482`. HWT hat gegenüber Main 46 eigene
Commits, Main gegenüber HWT 16. Das sind Abstammungszahlen, kein Nachweis einer
konfliktfrei möglichen Zusammenführung. Die beidseitigen Compare-Ergebnisse und
Paket-Trees wurden geprüft; ein funktionaler Merge wurde nicht versucht.

| Bereich | Nachweis am gepinnten Stand | Konsequenz für WE-1 |
|---|---|---|
| Explorer / Portalgeometrie | Main: `find_portal_bridges` und `front_lidar_corridor_check` in `src/explore/explore/portal_planning.py`. HWT ergänzt `find_connected_clearance_portals` für Engstellen innerhalb bereits verbundenen Freiraums. | Keine neue konkurrierende Türerkennung. HWT-Erkennung bleibt zunächst Referenz, nicht automatisch Main-Funktion. |
| Portalidentität | `PortalBridge` enthält Rasterendpunkte, Zielschwerpunkt, Abstände und Fläche, aber keine stabile ID oder Kartenepoche. HWT-`ExploreNode._is_visited_portal` prüft nur Abstand zu gespeicherten Mittelpunkten; Main hat ebenfalls `_visited_portals` mit Koordinaten. | Wiederbeobachtung, Gegenrichtung, benachbarte Türen und Geometriekorrekturen sind nicht als stabiles Identitätsgedächtnis abgesichert. WE-M1 ist weiterhin nötig. |
| HWT-Zwei-Bereich-Vertrag | `explore_node.py` enthält `_room_transition_requirement_met` und `_bounded_portal_scope_complete`. `hwt601_office_hall_params.yaml` fordert und begrenzt auf einen Übergang; entsprechende Profiltests sind vorhanden. | Ein erfülltes 1/1-Limit ist kein vollständiger Wohnungsgraph. Die nach dem Realtest geänderte Abschlusslogik bleibt physisch ungeprüft. |
| Laufzeit / Sensorfusion | HWT ändert unter anderem `base_hardware`, `amadeus_lidar_bringup`, `robot_bringup`, `robot_navigation` und ergänzt `robot_state_estimation`. `nav_mapping.launch.py` koppelt `use_hwt601_odometry` an den HWT-Launch und `require_hwt601_yaw` des Fahrtors. | Vor späterer Laufzeitintegration Paketabhängigkeiten, genau einen `/odom`- und TF-Eigentümer, Frische-/Stillstandsgates und tatsächlich installierte Profile gemeinsam prüfen. `active_drive=false` bedeutet hier nicht, dass keine Sensorgeräte gestartet werden. |
| Main-exklusive Arbeit | Main hat eigene OAK-/Rectifier-, Semantikstream- und LLM-Änderungen; insbesondere `robot_bringup` ist auf beiden Seiten geändert. | HWT-Verzeichnisse nicht pauschal über Main kopieren. OAK bleibt außerhalb dieses Auftrags; bestehende Main-Arbeit muss erhalten bleiben. |
| Metrische Karte | `robot_map_manager`: `/map`, `command_json`, `status_json`, explizites `save_map`; validierte Snapshots, versionierte Ablage und Inhaltsfingerprint. | Vorhandenen Speichervertrag nutzen. Ein laufender Snapshot oder Erkundungsabschluss ist noch keine erfolgreiche Speicherung. |
| Manuelle Semantik | `semantic_map_manager`: bestätigte gespeicherte Kartenreferenz, Fingerprint/Geometrie, frischer Managerstatus, `base_revision`, manuelle Raum-IDs und strikt validierte Kommandos. | Automatische Regionen nicht als manuelle Räume einschleusen. Keine Migration zwischen Fingerprints oder eindeutige automatische Zuordnung überlappender Raum-Polygone voraussetzen. |
| Abschluss / Verbraucher | `ExploreArea.action` liefert bisher `success`, Text und Zähler, keinen strukturierten WE-1-Abschluss. BT akzeptiert nur ROS-SUCCEEDED plus `result.success`. Web/iOS lesen unter anderem `map_ready_to_save`. | Spätere WE-M3-Änderung muss Action, BT/Mission, JSON und App-/Mock-Verträge bewusst kompatibel behandeln. Keine stillschweigende Umdeutung in diesem Auftrag. |

Die kompletten Paket-Trees einschließlich ihrer Tests sind für Main und HWT
identisch: `robot_map_manager` = `e7a1c0d81ede276be28e63903cb43c735a1fe744`,
`semantic_map_manager` = `e91dd75c22f6fc32587d93aad8b21fd473f8338e`,
`robot_interfaces` = `39c4a70a4e974e39b5525ca8f1d6a7b5eb48da81`.
Auch `mission_manager`, `bt_orchestrator` und die App-Verzeichnisse sind in den
verglichenen Trees unverändert. Das belegt Quellgleichheit, nicht Laufzeitabnahme.

**Konkreter Vertragswiderspruch:** Die README von `robot_map_manager` verlangt
bytegleiche wiederholte Antworten. Dagegen rekonstruiert
`robot_map_manager_node.py` im Cache-Replay mittels
`CachedCommandResponse.publish_kwargs` und `_publish_status` den globalen
Map-/Storage-/Pose-/Zeit-/Zählerstatus frisch. Idempotentes Kommandoergebnis und
bytegleicher kompletter Statusumschlag sind daher nicht gleichzusetzen. Vor einer
neuen Adapterintegration diesen Vertrag mit einem fokussierten Test und korrigierter
Dokumentation klären; hier weder Code noch README ändern. Frische periodische
Statusmeldungen allein dürfen außerdem nicht als neue unabhängige Portalbeobachtung
gezählt werden.

**Quellen:** Maßgeblich sind die obigen Commit-/Tree-Referenzen und die genannten
Pfade, nicht allein Paket-READMEs. Direkt prüfbare Stellen:
[HWT-Explorer](https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/src/explore/explore/explore_node.py),
[HWT-Portaltests](https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/src/explore/test/test_portal_planning.py),
[Main-Kartenmanager](https://github.com/chris01-byte/Roboter_ws/blob/05439c7a13d7a92e69b9eb4663e3a2a1b44626a1/src/robot_map_manager/robot_map_manager/robot_map_manager_node.py),
[Main-Semantikbindung](https://github.com/chris01-byte/Roboter_ws/blob/05439c7a13d7a92e69b9eb4663e3a2a1b44626a1/src/semantic_map_manager/semantic_map_manager/semantic_map_manager_node.py),
[Main-BT-Ergebnisvertrag](https://github.com/chris01-byte/Roboter_ws/blob/05439c7a13d7a92e69b9eb4663e3a2a1b44626a1/src/bt_orchestrator/include/bt_orchestrator/nodes/exploration_nodes.hpp).

#### Tatsächlich ausgeführte Prüfungen

**Umgebung:** isoliertes Linux x86_64, Python 3.13.5, NumPy 2.3.5, SciPy 1.17.0,
pytest 9.0.2; kein ROS 2 Humble und kein Jetson. Aus Connector-Inhalten wurden
nur Portalmodul und zugehörige Testdatei je Referenz als separate Quellexporte
bereitgestellt. Vor Ausführung stimmten die vollständigen Git-Blob-Hashes aller
vier Dateien mit den Repository-Blobs überein. Keine Änderung an den getesteten
Modulen oder Testfällen; keine vollständige Paket-/Installationskopie behauptet.

| Test-ID | Vorab erwartetes Ergebnis / tatsächliches Ergebnis | Exit |
|---|---|---|
| WE-M0A-P-MAIN | Vorhandene reine Portaltests unverändert bestehen / **8 passed**, keine Fehler, Fehlschläge oder Skips. | 0 |
| WE-M0A-P-HWT | Vorhandene reine Portaltests einschließlich Engstellenergänzung bestehen / **12 passed**, keine Fehler, Fehlschläge oder Skips. | 0 |

Die Suiten überlappen; dies sind nicht 20 unterschiedliche Testfälle.
Geprüft sind begrenzte Brücken, zulässige Endpunktkosten, Flächen-/Längenlimits,
beobachtete beziehungsweise blockierte LiDAR-Korridore sowie beim HWT-Stand
verbundene Engstellen und deren Negativfälle. Stabile IDs, Gegenrichtungszuordnung,
Kartenrevisionen, Durchfahrtsereignisse und Wohnungsabschluss sind damit **nicht**
abgenommen.

Reproduktion im jeweiligen separaten Export beziehungsweise passenden Quellstand,
aus dem Verzeichnis `src/explore` (im Export entsprechend `main/` oder `hwt/`):

```bash
report_dir="$(mktemp -d /tmp/we-m0a-portal.XXXXXX)"
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
python -m pytest -q -p no:cacheprovider test/test_portal_planning.py \
  --junitxml="$report_dir/portal.xml"
```

Je Stand einen eigenen Ausgabeort verwenden. Die hier erzeugten Konsolenlogs,
JUnit-Berichte, Exit-Codes und SHA-256-Werte bleiben im Audit-Prüfsatz; keine
Quellexporte, Caches oder privaten Wohnungsdaten werden eingecheckt.

| Referenz / Pfad unter `src/explore/` | Geprüfter Git-Blob |
|---|---|
| Main `explore/portal_planning.py` | `f66717088d0fb552f0d63b5f586ecf78ef89b376` |
| Main `test/test_portal_planning.py` | `a30c03ce747558bb3838aa0ee3628f6b7bff560b` |
| HWT `explore/portal_planning.py` | `7cd85d19e433de708c27d98e0574a7b3449bf807` |
| HWT `test/test_portal_planning.py` | `a8ee5de695aeb947db1a68f007febecfaf1ce77c` |

**Nur statisch geprüft, nicht neu ausgeführt:** ausgewählte Explorer-Vertrags-
und Profiltests in `src/explore/test/test_explore_contract.py`, Snapshot-/Fingerprint-
Validierung in `src/robot_map_manager/test/test_map_core.py` sowie Kartenreferenz-/
Geometrievalidierung in `src/semantic_map_manager/test/test_semantic_core.py`;
zugehörige Schnittstellenquellen und Manager-READMEs. Dies ist keine vollständige
Codeprüfung aller Testfälle. Die gesamte Explorer-Suite, beide Manager-Suiten,
ROS-Callbacks/QoS/TF, Colcon-Build, CI-Gesamtstand, aktive Parameter und reale
Sensor-/Fahrtests wurden hier nicht erneut geprüft. Fehlende Zielumgebung und der
bewusst auf ausgewählte Quellexporte begrenzte Umfang bleiben sichtbar.

#### Offene Gates und kleinster Folgeschritt

**Zielsystem-Gate bleibt offen:** Mit später tatsächlich verfügbarem Jetson-Zugriff
zuerst ausschließlich Quell-HEAD, Dirty-Status, installierte Modul-/Konfigurations-
hashes, Paketpfade und aktive Overlay-Auswahl erfassen. Ein Git-HEAD allein reicht
bei kopierten Colcon-Installationen nicht. Keine laufende Arbeitskopie wechseln und
keine Setup-/Startskripte ungeprüft ausführen. Erst ein eigener WE-M0/B-Auftrag darf
über diese Dateiinventur hinausgehen; Sensor-/Lastprüfung und Fahrt brauchen den
jeweils vorgesehenen sicheren Aufbau und die ausdrückliche Freigabe.

**Vorgeschlagen: WE-M1/A – reine Identität und Beobachtungsdeduplizierung.**
Nach Review und erneutem Fetch von Main einen separaten Implementierungsbranch
anlegen. Eingabe sind ausdrücklich normalisierte metrische Portalbeobachtungen mit
Beobachtungs-ID, Frame-/Sitzungs-/Revisionsbezug und Unsicherheitsangabe. Zunächst
nur im Speicher stabile Portal-IDs und kanonische Seiten A/B zuordnen; mehrdeutige
Zuordnung bleibt unbestätigt. Kein neues Detektionsverfahren und kein stiller
Koordinaten-/Epochentransfer. Für diesen rein synthetischen Kern ist weder ein
HWT-Merge noch ein Zugriff auf reale Wohnungskarten erforderlich.

| Geplante Datei | Genau begrenzte Änderung |
|---|---|
| `src/explore/explore/portal_memory.py` (neu) | ROS-unabhängiger Daten-/Identitätskern mit begrenztem Speicher, expliziter Kartenbezugsgültigkeit und deduplizierten Beobachtungen. Keine Fahr- oder Dateisystemwirkung. |
| `src/explore/test/test_portal_memory.py` (neu) | Synthetische Positiv-/Negativtests für genau diesen Identitätsteilschnitt. |
| `docs/wohnungserkundung/STATUS.md` | Tatsächlichen Nachweis und verbleibenden WE-M1-Umfang nachtragen. |

**Prüfplan:** Derselbe Übergang aus Gegenrichtung behält seine ID bei vertauschter
Annäherungsseite; kleine Geometrieänderungen im begründeten Gültigkeitsbereich
bleiben zuordenbar; zwei nahe Türen bleiben getrennt; mehrdeutige Matches werden
nicht automatisch vereinigt. Wiederholte Beobachtungs-IDs erhöhen keine Evidenz.
Fehlender oder widersprüchlicher Frame-/Sitzungsbezug, Kartenwechsel, nicht endliche
Werte und Speichergrenzen werden explizit getestet. Raster-/Ursprungsänderung nur
bei nachgewiesen äquivalenter metrischer Eingabe akzeptieren. Import und Tests
müssen ohne ROS, Nav2, Gerätezugriff oder Persistenz laufen; bestehende reine
Main-Portaltests zusätzlich unverändert ausführen. Testschwellen ausdrücklich als
synthetische Parameter kennzeichnen, nicht als gemessene Hardwaregrenzen.

**Ausgeschlossen:** Änderungen an `explore_node.py`, Launches, Fahrprofilen,
`ExploreArea.action`, Managern oder App; Integration in Zielwahl, Durchfahrtserkennung,
Regionsgraph, Rückkehrplanung oder Persistenz. Weitere WE-M1-Pflichten wie die
vollständige Ereignis-/Durchfahrtslogik bleiben separate Teilaufträge. WE-M2 bis
WE-M7 werden nicht vorgezogen.

**Rückfall:** Diesen Statusnachtrag allein zurücknehmen oder dessen PR schließen;
keine Runtime-Rücksetzung. Beim späteren WE-M1/A-Kern nur die neuen, noch ungebundenen
Modul-/Testdateien zurücknehmen. Solange keine Laufzeitintegration stattfindet,
bleibt das bisherige Roboterverhalten unverändert. Eine spätere HWT-Integration
braucht einen eigenen dateiweisen Prüf- und Rückfallplan, keinen pauschalen Merge.

**Übergabestatus:** Repository-Befund dokumentiert; Zielsystemvergleich offen;
keine neue physische Abnahme oder Fahrfreigabe. Geänderte Repository-Datei ist
allein diese STATUS.md. Veröffentlichungscommit, Remote-Verifikation und Review-PR
werden in der Auftragsübergabe beziehungsweise im PR nachgewiesen.

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

## 6. Pflege nach jedem Arbeitsschritt

Nächsten Schritt, betroffene Statuszeilen und neue Evidenz aktualisieren; keine
vorweggenommenen Gesamthäkchen. Planabweichungen und relevante Entscheidungen hier
mit Datum, Grund, Code-/Dokumentenstand, Tests, offenen Risiken und Rückfallweg
festhalten. Übergreifende Projektentscheidungen zusätzlich mit Verweis in
`docs/PROJECT_MEMORY.md`, echte Betriebsänderungen in `docs/ROBOT_TRANSFER.md`.

Nach Merge/Deployment den nachgewiesenen Stand ausdrücklich eintragen. Ein alter
Commit in dieser Tabelle ist eine Referenz und kein Auftrag, spätere Arbeit auf
diesen Stand zurückzusetzen. Keine privaten Wohnungsgeometrien oder Rohdaten
in diesen Status kopieren.
