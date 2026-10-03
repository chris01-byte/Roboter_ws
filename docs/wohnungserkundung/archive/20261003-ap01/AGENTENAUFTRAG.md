# Erster Software-Agentenauftrag: AP-01 – HWT-Zeitkorrelation

**Verbindlich: MASTERPLAN v1.3 vom 02.10.2026 · WE-D0/WE-M0 und betroffener Recoveryanteil WE-M3.**

Du arbeitest am GitHub-Projekt `chris01-byte/Roboter_ws` für den Roboter Amadeus. Setze den beigefügten MASTERPLAN v1.3 als kanonischen Plan ein und bearbeite ausschließlich AP-01 bis zu einem geprüften Softwareabschluss. Erwartet werden eine konkrete Codekorrektur, aussagekräftige Regressionen und eine saubere Übergabe. Ein weiterer Diagnosebericht allein erfüllt den Auftrag nicht.

Der Nutzer hat diesen schrittweisen Integrationsweg auf Grundlage einer unabhängigen Repositoryanalyse beauftragt. Die Architekturentscheidung lautet: bestehende Hardware-/ROS-Basis erhalten, Erkundung vereinfachen und später einen abgegrenzten externen Frontier-Kern vergleichen und integrieren. Dieser erste Auftrag repariert eine gemeinsame Voraussetzung dafür.

## 1. Umfang und Arbeitsregeln

Arbeite selbstständig innerhalb dieses begrenzten Softwareauftrags. Keine erneuten allgemeinen Bestätigungsfragen für Lesen, isolierten Branch/Build, Implementierung und Tests. Kläre nur eine tatsächlich fehlende Information oder einen echten Umfangskonflikt; bearbeite unabhängige Teile weiter.

Dieser Auftrag ist ausschließlich gerätefrei: keine Roboternetzverbindung, keine seriellen Geräte, keine Motor-/Aktorprozesse, keine Fahrt, kein Deployment, kein dauerhafter Installwechsel. Lokale ROS-Tests dürfen nur isoliert und ohne Gerätezugriff laufen. Die allgemeine LAB-1-Regel bleibt für spätere konkret beauftragte Laborarbeit bestehen; historische Fahrtaufträge werden hier nicht wieder aufgenommen.

Zulässige Produktänderungen: HWT-Rawdriver, gegebenenfalls ein kleiner privater Zeitkorrelationshelfer und unmittelbar erforderliche Diagnosefelder. Den Transport nur anfassen, falls dessen bestehender Empfangszeitbeleg technisch erforderlich ergänzt werden muss. Tests und notwendige Vertrags-/Planübernahme-Dokumentation gehören dazu.

Nicht Teil dieses Auftrags: Frontierimport, Kartenmasken-/Geometrieumbau, Nav2-/Controllerwechsel, neue Recovery-State-Machine, Gate-/DDS-/Executorumbau, Encoder-/EKF-/Biasänderung, neue Sensorkonfiguration, App-Umbau oder pauschale Lockerung von Fristen. Entdeckte unabhängige Fehler mit Beleg in den STATUS aufnehmen.

## 2. Tatsächliche Basis ermitteln und Plan übernehmen

Lies zuerst `AGENTS.md`, `docs/PROJECT_MEMORY.md`, `docs/INVENTORY.md`, `docs/LABORMODUS.md` und die aktuellen WE-Dokumente. Alte Aufträge sind Quellen, keine zusätzlichen Arbeitsaufträge. Lies bei betroffenen Karten-/Prozessfragen zusätzlich `tools/kartierung/README.md`.

Die Gegenprüfung bezog sich auf `feature/hwt-hold-recovery-resume` bei `08a4b9ac0b7a128ced2199f20976f3aa92ea55fe`. Das untersuchte ältere main `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1` ist keine geeignete Ersatzbasis. Prüfe den tatsächlich vorhandenen Branch, HEAD, Remote-Stand und lokale Änderungen. Wenn die Integrationslinie inzwischen weitergelaufen ist, prüfe gezielt den Diff in betroffenen Pfaden und arbeite auf ihrem geeigneten Nachfolger. Kein blindes Zurücksetzen und kein Überschreiben unbekannter Arbeit. Wenn die Linie nicht eindeutig ermittelbar ist, benenne genau diese Basisfrage.

Verwende einen isolierten Arbeitsbranch, beispielsweise `fix/hwt-clock-correlation`, auf der geprüften Integrationsbasis. Keine laufende Roboter-Arbeitskopie umschalten. Lokale Build-/Install-/Testpräfixe getrennt halten. Dokumentiere, aus welchen Präfixen die tatsächlich importierten ROS-Nachrichten und Produktmodule stammen; alte main-Bindungen dürfen keinen aktuellen Test vortäuschen.

Übernimm den beigefügten MASTERPLAN v1.3 nach `docs/wohnungserkundung/MASTERPLAN.md`. Archiviere zuvor die bestehenden Fassungen von MASTERPLAN, STATUS, AGENTENAUFTRAG und MEILENSTEINE bytegleich unter `docs/wohnungserkundung/archive/20261002-v1.2/`, mit Herkunftscommit/Blob und einem README. Falls dort schon ein Archiv existiert, verifiziere es; nicht überschreiben. Bestehende lokale Abweichungen separat erhalten und kennzeichnen.

Setze diesen Text als einzigen aktuellen `docs/wohnungserkundung/AGENTENAUFTRAG.md` ein. Füge dem STATUS vorn einen eindeutig datierten aktuellen Abschnitt hinzu: Plan v1.3, tatsächliche Basis, AP-01 in Arbeit, weiterhin offene reale Sensor-/Start-/Geometrieabnahme. Historische Nachweise bleiben erhalten und als historische Stände erkennbar. Erfinde keine aktuell installierte Jetson-Version aus einem Branch-Namen.

Synchronisiere gezielt Verweise und widersprüchliche aktuelle Aussagen in AGENTS, MEILENSTEINE und `docs/WOHNUNGSERKUNDUNG_STRATEGIE.md`; keine globale Umbenennung historischer v1.2-Belege. Die bisherige Einschränkung „Fremdcode nur Offline-Vergleich“ wird ausdrücklich durch die begrenzte AP-04-Erlaubnis ersetzt. Ergänze die Entscheidung im PROJECT_MEMORY. ROBOT_TRANSFER nicht als neues Deployment fortschreiben: Es findet keines statt. Dokumentübernahme und Codekorrektur sollen als getrennte, nachvollziehbare Diffs beziehungsweise lokale Commits prüfbar sein.

## 3. Nachgewiesener Fehler

Prüfe `src/robot_state_estimation/robot_state_estimation/hwt601_imu_node.py`, insbesondere `_poll()` und `_record_error()`, sowie den Zeitbeleg in `hwt601_transport.py` und die zugehörigen bestehenden Tests.

Im analysierten Stand liest `_poll()` zuerst ROS-Zeit, danach monotonic. Die Berechnung lautet sinngemäß `stamp_ns = clock_ns - round((bracket - received_at) * 1e9)`. Dabei werden zeitversetzte Uhrabfragen wie gleichzeitig behandelt.

Deterministisches Gegenbeispiel: Beide Uhren laufen vorwärts; ROS entspricht monotonic plus 1.000 s. Erster echter Antwortempfang bei monotonic 10,000 s ergibt ROS 1010,000 s. Zweiter Empfang erfolgt bei 10,010 s. Nach der zweiten ROS-Uhrabfrage, aber vor der zugeordneten monotonic-Abfrage wird eine Schedulingpause von 20 ms eingefügt. Der bisherige Code berechnet 1009,990 s und meldet `HWT-Messzeit nicht monoton`. Im Entwicklungsvertrag wird der Transport geschlossen; ein späterer gesunder Poll findet nicht mehr statt. Der Fehler ist mit den tatsächlichen Methoden reproduziert, nicht nur mathematisch vermutet.

Reproduziere dies zunächst mit synthetischen Uhren/Transport und den echten Produktmethoden. Testobjekte dürfen den Geräteaufbau ersetzen. Die zu prüfende Poll-/Zeit-/Fehlerlogik darf nicht im Test nachgebaut oder ersetzt werden. Die alte Implementierung muss am neuen gewünschten Verhalten scheitern; die reparierte muss bestehen. Keine Hardware und keine Änderung der Systemuhr.

## 4. Geforderter Zeitvertrag

Der maßgebliche Zeitpunkt ist der vom Transport erfasste vollständige Hostempfang `last_reply_received_monotonic_s`. Er ist kein belegter interner Sensorabtastzeitpunkt. Bewahre den Empfangsbezug auch bei verzögerter Verarbeitung.

Getrennte Uhrenabfragen haben eine Unsicherheit. Wähle eine kleine nachvollziehbare Lösung, die diese erfasst und akzeptierte Stempel aus einer konsistent gültigen Korrelation ableitet. Beispielsweise kann die ROS-Abfrage durch monotonic davor/danach eingerahmt und eine Offsetspanne geprüft werden. Dies ist eine mögliche Lösung, keine vorgeschriebene neue Architektur. Ein wechselnder Mittelpunkt großer Abfrageintervalle allein beseitigt den Fehler nicht zuverlässig.

Dokumentiere Unsicherheitsgrenze, Begründung, Clockquellenvertrag und Behandlung erkannter Sprünge. Erkennung beliebig kleiner Sprünge unterhalb der Messunsicherheit ist keine erfüllbare Forderung; benenne diese Grenze. Eine bereits erkannte tatsächliche Änderung der Zeitbasis darf nicht durch stilles Neubasieren verschwinden. Falls simulierte ROS-Zeit nicht unterstützt wird, muss deren Aktivierung/Quellenwechsel ausdrücklich entsprechend behandelt werden.

Eine ungenaue Zeitpaarung darf innerhalb der unveränderten Gesamtablaufzeit begrenzt erneut erfasst werden. Bleibt sie ungeeignet, veröffentliche diese Probe nicht und ändere weder letzten gültigen Empfang noch letzten gültigen Stempel. Der Unsicherheitsfall muss diagnostisch von einem erkannten harten Zeitbasisfehler unterscheidbar sein. Das erlaubt eine lokale Behandlung im Rawdriver; es beauftragt keinen umfassenden Health-/Recoveryumbau.

Kein `max(last+1, candidate)`, keine monotonisierende Korrektur falscher Messzeiten, keine Veröffentlichung als „jetzt“, kein künstliches Auffrischen alter Daten und kein Abschalten der Zeitprüfung. Fehlende/ungültige Empfangsbelege dürfen nicht ungeprüft durch Veröffentlichungszeit ersetzt werden. Ein bewusst geänderter bisheriger Fallback ist eng zu dokumentieren und im tatsächlichen Produkt-Transportcode mit synthetischer serieller Gegenstelle zu prüfen; kein Gerätezugriff.

Nach einer verworfenen unsicheren Probe muss eine spätere echte gültige Probe wieder verarbeitbar sein, soweit die bestehenden Verträge dies zulassen. Bei wiederholtem Verwerfen altern die letzten gültigen Daten; bestehende Frische-/Health-Regeln bleiben wirksam. Keine Baseline-, Bias-, Faultflag- oder Budgetresets zur Verschleierung.

Unverändert bleiben: Entwicklungsprofil 50 ms Antwort-/Gesamtablaufprüfung und 300 ms Rohdatenfrische, Legacy 30/200 ms, Encoder 120/180 ms sowie vorhandene HOLD-/Recoverygrenzen. Erkannte harte Zeit-/Identitäts-/Protokoll-/Datenfehler bleiben im Entwicklungsvertrag terminal. Die abweichende bestehende Legacy-Fehlerbehandlung wird nicht nebenbei vereinheitlicht.

## 5. Pflichtprüfungen

Implementiere deterministische Tests für die folgenden Verhaltensklassen. Nutze Parametrisierung, wo sie sinnvoll ist; keine Tests nur zur Erhöhung der Anzahl.

| Fall | Gefordertes Ergebnis |
|---|---|
| Präzise konstante Uhrenbeziehung, zwei Empfänge +10 ms | Korrekter Empfangsbezug und steigende veröffentlichte Stempel |
| Kleine wechselnde, nicht null breite Uhrbrackets unterhalb der begründeten Unsicherheitsgrenze | Kontinuierlicher gültiger Probenstrom; pauschales Verwerfen erfüllt den Auftrag nicht |
| Originalgegenbeispiel: +10 ms, danach 20-ms-Abfragepause | Kein falscher terminaler Rücklauf; korrekte Veröffentlichung nach zulässiger Paarung oder begründet verworfene unsichere Probe |
| Verzögerung vor, innerhalb und nach Uhrpaarung; wechselnder und konstant großer Versatz | Richtige Unsicherheit/Zuordnung oder Verwerfen, kein bloß monotoner aber falsch datierter Strom |
| Unbrauchbare Paarung, danach präzise Paarung | Nächste echte gültige Probe verarbeitet; kein erfundener Zwischenwert und keine terminale Schedulingfehlklassifikation |
| Wiederholt unbrauchbare Paarungen | Keine Auffrischung; vorhandene Frischeprüfung wird nach Ablauf unbereit |
| Überschrittene Transaktions-/Verarbeitungsfrist | Keine Veröffentlichung trotz eventuell gültiger Zeitkorrelation |
| Fehlender, nichtendlicher, zukünftiger oder rückläufiger Empfangsbeleg | Keine gültige Veröffentlichung mit erfundenem Ersatzzeitpunkt |
| Monotonic steigt, ROS springt separat zurück oder vor | Erkannter Sprung außerhalb Unsicherheit bleibt harter Zeitfehler |
| ROS-Rücksprung kleiner als Probenabstand, aber größer als Unsicherheit | Nicht übersehen, nur weil Nachrichtenstempel insgesamt noch steigen |
| Wechsel der Clockquelle bzw. ROS-Time-Aktivierung/Deaktivierung | Dokumentierter konservativer Quellenvertrag, kein stiller Epochenwechsel |
| Vorhandene CRC-/Portidentitäts-/Sättigungs-/Timeoutfälle | Bisherige Schutzwirkung bleibt erhalten |

Die zentralen neuen Fälle führen echte `_poll()`-/Fehlerbehandlung aus. Der synthetische Transport führt realistische Start-/Deadlinebelege in `last_transaction`, damit zusätzliche Uhrpaarungsversuche die 30-/50-ms-Gesamtfrist nicht durch leere Testdiagnostik umgehen. Zusätzlich mindestens ein gerätefreier Test mit echter `rclpy.clock.ROSClock`-/TimeSource-Funktionalität oder dokumentiert gleichwertiger tatsächlicher Clock-API für unabhängige Zeitänderung. Der vorhandene Test, der monotonic und ROS gemeinsam verstellt, ersetzt diesen Nachweis nicht.

Zeige außerdem verbundene Verbraucherfälle: Frische korrekt erzeugte Header bestehen die echte bestehende Guard-/Health-Zeitprüfung auch bei kurzer Zustellverzögerung; eine leicht zukünftige Marke darf nicht unbemerkt zum nächsten Terminalfehler führen. Wiederholt verworfene unsichere Proben werden dagegen nicht als frisch behandelt; die echte bestehende Guard-/Health-Logik reagiert auf das Alter der letzten gültigen Probe. Eine lokale direkte Kopplung echter Komponenten mit sonst gültigen Eingängen genügt; kein kompletter Robotergraf und keine vollständige Biasstart-Kalibrierung für diesen Zeitvertragsnachweis erforderlich.

Führe die unmittelbar betroffenen bestehenden Raw-/Transport-/Clock-/Health-Regressionen aus; passende HWT-/HOLD-/Kind-/Gate-Regressionen soweit durch den Diff betroffen. Bei lokalen DDS-Tests localhost und die vom jeweiligen Test geforderte isolierte ROS-Domain verwenden. Baue das geänderte Paket und erforderliche echte Abhängigkeiten in einem separaten Präfix. Ein Test mit alten Produktimporten ist ungültig.

Prüfe, ob die entscheidenden neuen Tests durch die vorhandene CI tatsächlich ausgeführt werden. Falls nötig, ergänze eng den passenden Aufruf/Trigger. Keine allgemeine CI-Neugestaltung. Ein unabhängiger bekannter Baselinefehler wird mit Vorher-/Nachherbeleg separat ausgewiesen; er darf nicht gelöscht, verdeckt übersprungen oder als bestanden gezählt werden.

## 6. Abnahme und Lieferung

AP-01 ist softwareseitig bestanden, wenn der reproduzierte Projektionsfehler im aktuellen Rawdriver beseitigt ist, Unsicherheit und erkannte echte Zeitbasisfehler getrennt behandelt werden, nach bloßer Unsicherheitsverwerfung gültige Folgeproben wieder verarbeitet werden und bestehende Schutzfristen unverändert wirksam bleiben. Ein bereits nach bestehendem Vertrag terminaler harter Fehler wird dadurch nicht aufgehoben. Betroffene Regressionen und Paketbuild müssen bestehen. Die neue Testabdeckung muss im normalen Projektprüfpfad erreichbar sein.

Liefere den konkreten Code-/Testdiff, kurze Erklärung der Zeitkorrelation und Unsicherheitsgrenze, Vorher-/Nachherbeleg des Gegenbeispiels, tatsächliche Test-/Buildbefehle und Ergebnisse, Quell-/Import-/Profilauflösung sowie Grenzen und Rückfall. Wenn eine Entwicklungsumgebung einen Nachweis verhindert, arbeite alle unabhängigen Teile ab und kennzeichne die verbleibende Abnahme offen; kein erfundenes BESTANDEN.

Erstelle auf dem Arbeitsbranch lokal überprüfbare Commits, soweit die Repositoryumgebung dies erlaubt. Prüfe vor jeder später autorisierten Veröffentlichung die ausgehende Historie auf private Daten. Dieser Auftrag enthält keinen Push, Merge oder Deployment; ein sauberer lokaler Diff mit Commit-IDs genügt als Lieferung. Kein destruktiver Reset.

Aktualisiere STATUS und diesen kanonischen Auftrag am Ende mit Ergebnis und Verweisen. Bewahre den Auftrag als abgeschlossenen Text; überschreibe ihn nicht mit unklaren neuen Imperativen. Kennzeichne ausschließlich den tatsächlich erreichten Status, beispielsweise **AP-01 software_geprüft; Zielsystem und reale Erkundung weiterhin offen**. Behaupte nicht, den historischen Roboterabbruch abschließend erklärt oder die Wohnungserkundung repariert zu haben.

**Genau nächster Schritt nach Erfolg:** AP-02 als begrenzten Folgeauftrag gemäß MASTERPLAN vorbereiten, mit konkreten betroffenen Pfaden und Abnahmekriterien für Kartenlebenszyklus und Quellenvertrag. Die Vorbereitung ist Übergabe, keine automatische Ausführung von AP-02. Bei Nichtbestehen stattdessen den kleinsten nötigen AP-01-Rest benennen. Keine Fahrt aus diesem Auftrag ableiten.

## 7. Abschluss am 03.10.2026 – AP-01 software_geprüft

Dieser AP-01-Auftrag ist abgeschlossen; der Originalauftrag oben bleibt erhalten und ist kein erneut auszuführender Auftrag. MASTERPLAN v1.3 bytegleich übernommen, vier WE-Vorgänger bytegleich mit Herkunfts-SHA archiviert. Verifizierte Basis `08a4b9a`, Dokumentcommit `84abfc6`, Softwarecommit `c797442b37994f774df40b6b27d54c27efa3bdc3`, Branch `fix/hwt-clock-correlation`, isolierter Worktree `/workspace/Roboter_ws-ap01`.

Ergebnis: HWT-Empfangszeit wird aus konsistenter Offsetspanne (≤1 ms, drei Versuche innerhalb echter 30/50-ms-Gesamtfrist) konservativ projiziert. Unsichere Proben werden ohne Reconnect/Frischeauffrischung verworfen, tatsächliche harte Zeit-/Quellenfehler bleiben hart. Originalgegenbeispiel vorher terminal `1009,990 s`, nachher korrekter Header `1010,010 s` und gültige Folgeprobe. 52 neue Fälle, 58 Installimporttests, 443 betroffene Regressionen, 381 registrierte colcon-Tests ohne Fehler/Skips; Achtpaketbuild erfolgreich. Zahlen überlappen. Details, Originalbefehle/Logs, Clockquellenvertrag, Plattform/Baselinefehler und Rückfall ausschließlich im [aktuellen STATUS](STATUS.md#03102026--masterplan-v13--ap-01-software_geprüft) und [Evidenzregister](evidence/ap01-20261003/README.md).

Keine Geräte, Roboternetzverbindung, Fahrt, Deployment, Push oder Merge. Zielsystem und reale Sensor-/Start-/Geometrieabnahme bleiben offen; historischer Roboterabbruch nicht abschließend erklärt. Python-3.12-JSON-Tiefenfehler unverändert separat nachgewiesen. ROBOT_TRANSFER unverändert.

### AP-02-Übergabe – vorbereitet, nicht ausgeführt

Genau nächstes begrenztes Paket gemäß MASTERPLAN v1.3/WE-M0 und WE-M3: konsistente Übergänge für Kartenidentität/Sitzung/Frame/Geometrie/Revision sowie gemeinsamen Quellenzeitvertrag. Diese Vorbereitung aktiviert keine Umsetzung und ersetzt den abgeschlossenen AP-01-Auftrag nicht durch neue Imperative.

**Betroffene Pfade für den Folgeauftrag:**

- `src/explore/explore/metric_frontier_runtime.py`: `_on_metric_map`, `_on_metric_map_status`, `_metric_inputs`, `_metric_prepare_egress`; Rasterwechsel vor allen Kombinationen von gespeicherten Masken und neuer Belegung behandeln. Im aktuellen Code läuft `evidence.unknown &= occupancy < 0` auch nach erkannter Geometrieänderung – alte/neue Form darf nicht kombiniert werden.
- `src/explore/explore/metric_frontier.py`: `StartEgressEvidence` und Geometrie-/Quellenbindungen; gespeicherte Evidenz bei normalen Updates korrekt revalidieren, bei tatsächlichem Kontextwechsel invalidieren.
- `src/explore/explore/explore_node.py`: `_on_map`, `_on_global_costmap`, ausstehende Kartenarbeit/Kindbindung. Harmlose Revision nicht allein als Cancelgrund verwenden; verspätete Arbeit darf aktuellen Stand nicht überschreiben.
- `src/amadeus_map_identity/amadeus_map_identity/fingerprint.py` und `src/robot_map_manager/robot_map_manager/`: bestehende Fingerprint-/Session-/Geometrieverträge prüfen und nur bei nötiger Konsistenzkorrektur ändern.
- Für die getrennte Quellenbudgetzuordnung: `src/robot_state_estimation/robot_state_estimation/hwt601_fusion_guard.py`, `hwt601_fusion_health.py`, `src/base_hardware/base_hardware/encoder_odometry.py`, aktiver `base_hardware_node.py`, passive `src/base_hardware/base_hardware/encoder_shadow_reader.py`/`encoder_shadow_node.py`, `src/robot_navigation/robot_navigation/cmd_vel_mission_gate.py` und bestehende TF-/Gate-/Explorerquellenadapter. AP-01-Headervertrag erhalten, kein allgemeiner Health-/DDS-/Executorumbau.
- Zugehörige Tests in explore/state/base/navigation/map-identity/map-manager und passende bestehende CI-Aufrufe/Trigger; nur betroffene Auswahl ergänzen. Paketauflösung vor Folgeänderung nochmals prüfen.

**Abnahme des begrenzten Folgeauftrags:** 100×100 → 100×101 und Wachstum mit verschobenem Ursprung ohne Arrayausnahme/alte falsch gültige Egress-Maske; Auflösungs-/Sitzungs-/Framewechsel invalidieren betroffene Evidenz; normale inhaltliche Updates erhalten noch gültige Ziele; verspätete Kartenarbeit bleibt unwirksam; Verlust notwendiger Quelle stoppt, tatsächlich gültige Folgeupdates werden verarbeitet. Keine neue Freiraumannahme oder mitwandernde Ausnahme.

Zeit-/Gültigkeitsbudget aus bestehenden Verträgen für HWT, Encoder, TF, Gate und Explorer offenlegen: Empfang, IO, Verarbeitung, DDS-Verbrauch, Frische, Kontinuität; aktiven/passiven Pfad unterscheiden. Gerätefreie verbundene Gegenfälle, echte aktuelle Nachrichtenbindungen, isolierter Paket-/Overlaybuild und betroffene Regressionen. Fristen/HOLD-/Kontinuitätsbudgets unverändert, keine Timeouterhöhung als Reparatur. Belastbare aktive Jetsonlast bleibt ausdrücklich AP-06-Nachweis. Keine Sensor-/Geometrie-/Planer-/Frontierintegration aus AP-03/AP-04 vorziehen. Keine Hardware/Fahrt aus dieser Übergabe.
