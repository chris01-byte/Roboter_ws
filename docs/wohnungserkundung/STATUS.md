# Wohnungserkundung – aktueller Status und nächster Auftrag

**WE-1 · 30.09.2026 · MASTERPLAN v1.2 · Stufe 3 weiterhin OFFEN**

Maßgeblich: [MASTERPLAN](MASTERPLAN.md), [AGENTENAUFTRAG](AGENTENAUFTRAG.md), [LAB-1](../LABORMODUS.md), [MEILENSTEINE](MEILENSTEINE.md). Dies ist der einzige aktuelle WE-Iststand. Die ausführliche bisherige Statusdatei ist [bytegleich archiviert](archive/20260930-v1.1/STATUS.md); alte Abschnittsnummern und „nächste Schritte“ dort sind historische Referenzen.

## 1. Aktuelle Nutzerentscheidung

Normale Erkundung wird metrisch organisiert: beobachten → erreichbare Frontier-/Beobachtungsposition wählen → navigieren → neue Beobachtung und Ergebnis bewerten → nächste Aufgabe. Portal-/Raumsemantik ist keine Pflicht für normale metrisch sichere Ziele. Geometrie, Karte/Pose, Scope, Sensor-/Antriebsgesundheit und Schutzkette bleiben verbindlich.

**GRÜN: METRISCHER ERKUNDUNGSKERN – GERÄTEFREI INTEGRIERT BESTANDEN.** Implementiert als explizites `metric_frontier`-Backend im bestehenden Explorer. Default bleibt `existing`. Beim anschließend beauftragten Realnachweis wurden reale Sensor-/ROS-Prozesse im rein lesenden Vorlauf gestartet; dieser blieb blockiert, keine aktive Fahrt oder Mission, kein dauerhafter Installwechsel. Stufe 3 bleibt **OFFEN**. Konservative Geometrieprüfung bleibt verbindlich; reale Zielerreichung, Türpassage und Robustheit sind nicht aus den Softwaretests abgeleitet.

## 2. Belegter Ausgangspunkt

| Stand | Beleg / Grenze |
|---|---|
| Remote-Dokumentbasis vor v1.2 | PR #105, feature/hwt-hold-recovery-resume, `99d21c012dfe4c28d8263f7cd5e16505b07736d6`; keine Aussage über aktuelle lokale Runtime |
| Letzter ausgewerteter realer Kandidat | `492ef20`, Ergebnis `d480243`; vollständiger zweiter Lauf stage3-map-handoff-20260929/real-repeat |
| Historischer Funktionsvergleich | `1d91229dc10ff4bb791938d49aae8e9808a5dfff`; [WE_PARITY_RESET](../WE_PARITY_RESET.md) dokumentiert Frontierfahrten, verbundenen Türübergang und weitere Frontiers danach |
| Erster HWT-Recoveryfall | Gerätefreier aktiver Kindzielvertrag und reale Rundblick-HOLD/Recovery/Fortsetzung im dokumentierten Umfang akzeptiert; kein umfassender Robustheitsnachweis |
| Aktueller Erkundungserfolg | Kein bestandener zusammenhängender A/B/C-/Mehrraumlauf; kein Ziel- oder Türerfolg des letzten Laufs |
| Neues metrisches Backend | Isolierter Build, Regression und synthetischer Produktgraph bestanden; realer lesender Vorlauf auf `deb075e` blockiert, kein Fahrnachweis |

Aktuelle und historische Modul-/Installpräfixe aus ROBOT_TRANSFER und den erhaltenen Manifesten ermitteln, nicht aus Branch-Namen ableiten. Bestehende Builds und unbekannte lokale Änderungen nicht überschreiben. Die Abnahme eines neu kombinierten Kandidaten wird nicht aus historischen Einzeltests zusammengesetzt.

## 3. Offene Befunde bleiben erhalten

Der letzte vollständige Lauf hielt ein autonomes Frontierkind bis zum Kindtimeout; kein SOURCE_INVALIDATED und kein HWT-first_fault. Keine erledigte Aufgabe, keine Portalquerung, kein Regionwechsel. SlowZone gab 30 % aus; kleine Bewegungen reichten im Offline-Progress-Checker-Replay, nicht für Zielerreichung. Nicht mit externer Bewegungsvermessung gleichsetzen.

Softwareseitig blieb der Portalbestand in 327 Statusmeldungen leer; 296 Gegenproben fanden ebenfalls keinen Kandidaten. Der aktive Analysepfad verwendete 0,20 m statt der separaten historischen Analyse bis 0,40 m. Das ist ein Vergleichsbefund, kein bewiesener alleiniger Auslöser und kein Auftrag, Grenzen blind anzugleichen. Die konkrete physische Tür ist dem Datensatz weiterhin nicht eindeutig zugeordnet.

Die SlowZone-Punkte lagen räumlich auch in den Costmaps. Ein sicherer physischer Ausweg ist damit nicht bewiesen. Warum der reale Timeout zu SYSTEM_FAILURE statt möglicher lokaler Aufgabenrückstellung führte, ist mangels interner Erstentscheidung nicht abschließend rekonstruiert. Positive Offline-Snapshots ersetzen nicht den damaligen Callbackzustand. Abweichungen von Drehsoll/-rückmeldung, Objektidentität und Shutdownfehler bleiben offen, nicht als harmlose Nebeneffekte wegdefiniert.

Originalwerte, Szenarien, Tests und Messgrenzen: [voriger STATUS, Abschnitt 7](archive/20260930-v1.1/STATUS.md#7-nächster-schritt-und-historie). Vollständige lokale Auswertung: `~/.local/share/amadeus/tests/stage3-door-obstacle-offline-20260930/`. Private Rohdaten bleiben lokal.

## 4. Softwareabschluss und Nachweise

Basis: veröffentlichter `1dbbdaa`, unabhängiger Checkout der bestehenden Integrationslinie; kein privater lokaler Bericht als Vorfahr. Änderungen: `explore_node.py`, neue `metric_frontier.py` und `metric_frontier_runtime.py`, explizites Overlay `metric_frontier_params.yaml`, Regression `test_metric_frontier.py` und verbundener Graph `tools/sensorfusion/metric_frontier_product_graph.py`. Modus-/Schnittstellen-/Wiederverwendungszuordnung: [Explore-README](../../src/explore/README.md#explizite-metrische-strategie-masterplan-v12).

Wiederverwendet: tatsächliche Frontiercluster, sichere Annäherungsziele, geodätische Distanz, freie Rastersegmentprüfung und vorhandene Bewertungsgewichte; aktuelle Kartenidentität/Scope, Quellenbeobachter, Nav2-Einzelkind, Scan/Vorausrichtung, HOLD/Stillstand/Gate-ACK. Kein zweiter Navigator und kein semantischer Aufgabenbesitzer im metrischen Modus. Der gepaddete asymmetrische Fahrzeugumriss wird einschließlich Drehungen auf Rohkarte **und** Costmap geprüft. Unbekannte Zellen bleiben gesperrt.

**Build:** sechs Pakete (`explore`, `robot_navigation`, `robot_state_estimation`, `mission_manager`, `robot_map_manager`, `amadeus_map_identity`) isoliert unter `~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/install`, ROS Humble plus dokumentiertem Vollunderlay. BT läuft aus `hwt-child-scope-20260928-retry/install`; Graph protokolliert alle aufgelösten Präfixe. Kein Install in der laufenden Arbeitskopie.

**Regression:** 1.342 pytest-Tests bestanden; zusätzlich registrierte colcon-Tests: 1.242, null Fehler/Failures/Skips. Neue metrische Regression: 21 Tests, unter anderem räumliche Retries, unbekannte/enge Wege, asymmetrischer Footprint, Scope-/Owner-/Budget-Ablehnung, verspätete Actionannahme und alte Karten. Reale ROS-Node-Tests erzwingen localhost und Domain 200–230 vor Initialisierung. Ausführung hier Domain 226, Graph Domain 224; konfigurierte DDS-Peers entfernt.

Ein Neustart der Ausführungsumgebung verlor die temporären `/tmp`-Artefakte und unterbrach den Abschlusslauf. Der Kandidat wurde am dauerhaften lokalen Testpfad erneut gebaut; maßgeblich sind dessen abschließende Logs, nicht verlorene Zwischenläufe.

Ein erster wiederholter HOLD-Reiz vor frischer wiederhergestellter Yaw-Messung endete korrekt an zusätzlicher ungültiger Quelle. Die Fixture wartet jetzt auf gemessene Wiederherstellung vor dem zweiten Rohdatenreiz; Originallauf bleibt unter `graph-hold-before-stable-fixture` erhalten. Produktgrenzen wurden dafür nicht geändert.

Der zusätzliche Rundblickfall legte einen vorzeitigen Abbruch am gemessenen `vl53_triplet_unmatched`-Publikationsfenster offen (`graph-scan-first` und `graph-scan-diagnostic`). Dieses Fenster wird jetzt wie in der Navigation vom echten Gate gesperrt, ohne das gesamte Scanverfahren sofort als Fehler zu beenden; tatsächlich stale/ungültige Quellen bleiben terminal. `scan_route` prüft eine echte Rohkartensperre während des Scans ohne Nav2-Kind.

Der erste korrigierte Scan lief mit einem festen 10-ms-Synthesetakt und 12-s-Testbudget in Timeout (`graph-scan-fixed-tick-model`). Die Fixture integriert jetzt tatsächliche verstrichene Zeit aus den gegateten synthetischen Ausgängen; 0,3-rad-Scanbudget 28 s ausschließlich im Test. Produktprofil weiterhin 360°/280 s. Das ist synthetische Modellbewegung, keine externe Vermessung des Roboters.

**Verbundener Produktgraph (16 Fälle bestanden):** Mission Manager → tatsächlicher BT → Explorer → Nav2-Testgegenstelle; tatsächlicher Kartenmanager, HWT-Shadow und Mission-Gate. Synthetisch sind Raster, physische Eingangsmeldungen und Nav2-Gegenstelle. Kein Zielkandidat, Portal, Region oder Taskgesundheitsadapter wird eingespeist. Lokale Belege `~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/graph-<Fall>/result.json` und Prozesslogs; Szenen sind gerätefrei.

| Pflichtfall aus AGENTENAUFTRAG §4 | Ausgeführter Beleg |
|---|---|
| 1 Ohne Semantik | `chain`: autonome Auswahl ohne Pflichtfeeds; widersprüchlicher optionaler Shadowstatus wirkungslos |
| 2 Beobachtungsschleife/offene Verbindung | `chain`: drei erreichte Aufgaben aus veränderten Rastern im selben Elternauftrag; maximal ein Kind, Verbindung ohne Türlabel |
| 3 Unerreichte Aufgabe/Alternative | `blocked`: tatsächliche erste Policywahl abortiert; terminales Kind, frischer Stillstand und Betriebssnapshot, danach anderes Rasterziel |
| 4 Kriechen/Budget | `budget`: kleine synthetische Drehbewegungen mit tatsächlich publizierten Gyro-/Odomeldungen setzen absolute Aufgabenfrist nicht zurück; gesunder Zustand erlaubt begrenzte Alternative |
| 5 Laufende Karte | `chain` erhält gültiges Kind trotz Updates; `route` storniert bei ungültigem Weg, `scan_route` beendet unzulässigen Scan; Unit-Regression verhindert Übernahme alter Raster/anderer Karte |
| 6 HOLD/Cancel | `hold`: wiederholte kurze Quellenausfälle, unveränderte HOLD-Frist, Bewegung sperrt Resume, Stillstand/Gate-ACK erlauben neues Kind derselben Aufgabe; `late`, `cancel_failed` |
| 7 Harte Gegenfälle | `estop`, `sensor`, `actuator`, `pose`, `map`, Nutzerabbruch, nicht terminales Kind; Scope/Footprint/Budget zusätzlich Regression und `empty`/`filtered` |
| 8 Abschluss/Migration | `empty`: vollständig bekannt nur metrischer Abschlusskandidat/Teilstand; `filtered`: unbekannter Rest ohne Abschlusskandidat; überall keine Speicherfreigabe und kein Gesamt-/Semantikerfolg |

Der abschließende `chain`-Lauf erreichte die ersten drei Aufgaben und nahm vor dem kontrollierten Testende noch ein viertes Kind an; dieses wurde terminal gecancelt. Beispiel der ersten drei Aufgaben (ausschließlich synthetische Koordinaten): `(1.05, 0.05)` → gemessene Zielerreichung/neue Karte → `(2.55, 0.05)` durch rastergeprüfte offene Verbindung → neue Karte → `(4.05, 0.05)`. In `blocked` lautet die erste Entscheidung `task_unreached_cause_unproven`, **kein** erfundenes Hindernis und kein pauschaler Hardwaredefekt; erst nach gesundem terminalem Zustand folgt die andere Aufgabe. Budget über HOLD/Kindwechsel erhalten; Retry erst nach Cooldown, geänderter Kartenevidenz und verbleibenden Versuchen. `scan` prüft begrenzten Initialscan und anschließende Vorausrichtung im verbundenen Pfad; Scan/Vorausrichtung bleiben vorhandene Verfahren mit laufender Konturprüfung.

**Offline-Grenze:** Historischer Erfolgsdatensatz und aktueller Fehllauf wurden lokal nur lesend anhand je drei Raster-/Pose-Snapshots verglichen. Historisch: alte Kandidaten 15/7/11, neue konservativ zulässige 0/4/11; aktueller Fehllauf: 10/13/12 gegenüber 0/0/0. Häufig liegt bereits die tatsächliche Fahrzeugkontur nicht vollständig im bekannten freien Rohkartenraum; zusätzlich Route/Costmap. Der Vergleich verwendet für die reine Kandidatenanalyse einen Rastergrenzen-Scope und beweist weder aktuellen Betreiber-Scope noch Live-Quellengesundheit. Diese Grenze wurde nicht durch Lockerung behoben. Positive Synthetik ist kein Nachweis realer Befahrbarkeit. Private Bags/Karten und Analyseergebnisse bleiben außerhalb Git.

### Realnachweis am 30.09.2026: Vorlauf blockiert, keine Mission

Exakter Kandidat `deb075e3f1a51a46bc00c2235a3068cfbe45d769`, derselbe isolierte Sechspaketinstall, Produktbasisprofil plus lokal vervollständigtes metrisches Overlay über `explore_params_overlay`. Reale Domain 42; kein Aktorschreibprozess. Live-Parameter und 324 Explorer-Statusmeldungen belegen `metric_frontier`; alte WE-Policy/Navigation false. Session/Startkarten-Fingerprint und LAB-1-Scope aus aktueller Karte/Pose zugeordnet; keine historischen Raumkoordinaten oder Dummy-Feeds. Bootstrap-Explorer endete zunächst erwartungsgemäß am ungebundenen Scope; nach Bindung alleiniger metrischer Explorer idle.

**Quellen:** direkte FC03-Startmessung im Stillstand; später passives Gate mit 189,166 ms Radsamplealter > 180 ms. Einmaliger passiver Gate-Neustart nach Sensorstart, tatsächliche kurze Rohquellen-Recovery separat beobachtet. Danach realer Encoderreader terminal verriegelt: `encoderpaar_zeitfenster_ueberschritten`, FC03-Paar 125,870 ms > 120 ms (Einzelreads 91,760/33,809 ms). Ursache der Zeitüberschreitung nicht bewiesen; kein pauschaler Hardwaredefekt. Keine Grenze gelockert und kein Quellenstatus gefälscht.

**Geometrie:** aktuelle Startzelle unbekannt (`-1`); volle gepaddete Kontur in Rohkarte und Costmap unzulässig, bereits erste Scanorientierung verworfen. Snapshotanalyse mit installiertem Kandidaten: 25 reale Frontiercluster, alle `no_known_free_route`, 0 akzeptiert. Kein pauschaler Tür-/Freigabebefund. Darstellung mit Kontur/Scope lokal; keine Fahrspur/Ziel-/Passageereignisse erfunden. Bekannter LAB-1-Rahmen, aktuelles beobachtetes Rasterenvelope; unbekannte Zellen bleiben gesperrt.

| Realnachweiskriterium | Ergebnis und Grenze |
|---|---|
| A: drei autonome Beobachtungen und räumlicher Kartenfortschritt | **nicht bestanden**: 0 Missionen/0 Aufgaben; 1.603 Kartenmanager-Meldungen mit unverändertem Fingerprint |
| B: Zielmisserfolg und sichere Folgeaufgabe | **nicht aufgetreten**: kein Nav2-Kind; passive Quellen-Recovery ist kein Aufgabenfortsetzungsbeleg |
| C: vollständige Passage und Aufgabe dahinter | **nicht bestanden**: keine Fahrt, kein Passagebeleg oder Beobachterzuordnung |

Kein regulärer aktiver Wechsel, weil Vorlauf nicht bestanden; kein zweiter Fahrversuch. Budgets live geladen: 900 s gesamt, 150 s Aufgabe, 6 Versuche/3 Fehler, Initialscan 280 s/0,08 rad/s. Keine Mission begonnen, daher keine Budget-/Timeoutabnahme. Recorder bis Ende aktiv; SQLite erst nach Ende ausgewertet: keine running-Mission, keine Navigate-Statuseinträge, alle aufgezeichneten Befehle null. Geordnete SIGINTs ausschließlich an Launchwurzeln; alle manifestierten Prozesse beendet und Gerätehandles frei. Nach Stackende zwölf frische FC03-Paare, beide Motorpositionen unverändert und 0 rpm. Keine Shutdownfehler im Abschlusslog; Bootstrap-Exit und Laufverriegelung getrennt geführt.

Private Belege ausschließlich `~/.local/share/amadeus/tests/metric-frontier-real-20260930/`: Runtime-Manifest mit Präfixen/Profil-/Modulhashes, Liveparameter/-status, Quellen-/Geometriesnapshots, lokale Darstellung, geschlossene Bag-Auswertung, FC03-Endmessung und Shutdownprüfung. Keine privaten Karten/Bags/Berichts-Vorfahren veröffentlicht. Softwareerfolg bleibt erhalten; kein Stufe-3-Gesamtgrün.

**Genau nächster Schritt:** ein gezielter Vorlauf-Korrekturauftrag für die belegten Startkarten-/Kontur- und FC03-Paarzeitblocker, mit getrennten Nachweisen und unveränderten Schutzgrenzen; keine automatische neue Fahrt.

## 5. Erhaltener Umfang und nächste Meilensteine

Schritt 1/2 nicht neu beginnen; betroffene Wiederverwendung gezielt regressieren. Stufe 3: Softwareabschluss des metrischen Kerns erreicht; reale autonome Beobachtungsfolge, Hindernis-/Befreiungsfälle und vollständige Passage mit Weitererkundung weiterhin offen. Normale Fahrten benötigen keine Portal-ID mehr; physische Durchfahrt und freier Fahrweg bleiben nachzuweisen.

Danach metrischer WE-M4-Rundweg, WE-M5-Persistenz/Wiederaufnahme und WE-M6-Abschluss gemäß v1.2. Semantische Portal-/Regionskriterien werden separat geführt, nicht gelöscht oder rückwirkend erfüllt. Geparkter HWT-Kindziel-Injektionstest, optionale OAK-Türerkennung und zusätzliche Architekturvergleiche sind kein aktueller Parallelauftrag.

## 6. Git, Runtime und Rückfall

Ein Integrationsverantwortlicher, bestehender Branch/PR #105. Kein automatischer Merge, kein permanenter Installwechsel. LAB-1 ohne erneute Standardfreigabeschleifen anwenden. Gerätefreier Auftrag ist keine unbegrenzte Fahrerlaubnis.

Ein lokaler nicht veröffentlichter Berichtscommit mit Raumdaten wurde im Gespräch genannt. Die ausgehende Linie basiert direkt auf dem veröffentlichten Remote-Stand; private Berichtscommits sind keine Vorfahren. Auch bei späteren Pushes Vorfahren prüfen. Lokale Arbeit sichern und getrennt halten, keinen Force-Push oder destruktiven Reset ausführen. Der Funktionscommit basiert ausschließlich auf dem veröffentlichten Remote-Stand.

Rückfall: metrisches Overlay nicht aktivieren, `exploration_strategy: existing` beim geordneten Start ohne Mission; sicherer Betriebsrückfall `enable_auto_explore:=false`, `active_drive:=false`. Kein Branch-Rollback und keine bekannten offenen Befunde ausblenden. Bei Code-Revert auch die gemeinsame Absicherung verspäteter Nav2-Annahme berücksichtigen.

## 7. Historie und Nachweisregister

[Original-STATUS bis 99d21c0](archive/20260930-v1.1/STATUS.md), [Original-Agentenauftrag](archive/20260930-v1.1/AGENTENAUFTRAG.md), [Archivzuordnung und Originalpfade](archive/20260930-v1.1/README.md). Die Dateien sind unverändert erhalten. Maßgeblich für den jetzigen Auftrag sind Abschnitte 1–6 dieser Datei und der aktuelle AGENTENAUFTRAG, nicht ältere Aufträge aus dem Archiv.
