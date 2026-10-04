# Projektgedächtnis

## Historie und aktueller Einstieg

Die vollständige bisherige Datei bis zum veröffentlichten Commit `99d21c012dfe4c28d8263f7cd5e16505b07736d6` ist [hier bytegleich erhalten](wohnungserkundung/archive/20260930-v1.1/PROJECT_MEMORY.md). Sie enthält auch alle anderen Projektbereiche; nichts daraus ist gelöscht. Für ältere Entscheidungen gezielt dort lesen. Relative Links beziehen sich auf den ursprünglichen Pfad docs/PROJECT_MEMORY.md; [Archivzuordnung](wohnungserkundung/archive/20260930-v1.1/README.md).

Aktuelle Wohnungserkundung ausschließlich aus [MASTERPLAN](wohnungserkundung/MASTERPLAN.md), [STATUS](wohnungserkundung/STATUS.md) und [AGENTENAUFTRAG](wohnungserkundung/AGENTENAUFTRAG.md) ableiten. Ältere „nächste Schritte“ sind keine parallelen Aufträge. Inventar und tatsächliche ROBOT_TRANSFER-Historie bleiben erhalten; dieser Eintrag ändert keine Runtime.

## 03.10.2026 – AP-05: belegter Beobachtungsfortschritt und konsistente Wiederaufnahme

**Nutzerentscheidung:** Nach AP-05-Übergabe ausdrücklich „gut mache weiter“. Saubere AP-04-Basis `2532f1b`, Branch `feature/metric-observation-persistence`, Software `090762d`; MASTERPLAN v1.3 unverändert, AP-04-Auftrag bytegleich archiviert.

**Entscheidung:** Im vorhandenen Explorer Ankunft, tatsächliche neue lokale Beobachtung und Erledigung trennen. Neue lokale Evidenz kann dieselbe räumliche Aufgaben-ID begrenzt wieder öffnen; keine Neustart-/Kartenstempel-/ID-Budgetresets. Gesamterfolg über vorab festes gültiges Restfreiheitsfenster, raw-erreichbare Aufgaben vor Filter/Blacklist. Vorhandenen Kartenmanager/Sidecar weiterverwenden, keinen neuen Speicher-/Missionsbesitzer. Resume verlangt zusätzlich zum expliziten neuen Auftrag die aktuelle vorhandene verifizierte Lokalisierungsfreigabe der gespeicherten Karte; TF allein beweist keine Relokalisierung. Additiver versionierter Ergebnisstatus, Action-Wire unverändert, vorhandene App konsistent angepasst.

**Nachweis und Grenzen:** Kern/Persistenz/ROS-Verträge software_geprüft; 65 neue Vertragsfälle, 225 installierte / 1.751 betroffene / 1.664 colcon-Tests bestanden (Überlappung), echter Zehnpaketbuild plus finaler Explorer-Neubuild. Rote Original-Ankunfts- und verspätete Beobachtungsverarbeitungs-Gegenproben, Source-/Installidentität und Originalbelege ausschließlich im [STATUS](wohnungserkundung/STATUS.md). Native iOS-Build/Laufzeit mangels Apple-Werkzeugen unter WE-M7 separat offen, wie MASTERPLAN ausdrücklich erlaubt. Keine Hardware, Deployment, Push/Merge, Jetson-Wirkung oder vollständige AP-06-Gesamtkette behauptet. Keine Reserve-/Fristlockerung. Eigene AP-05-Commits gezielt revertierbar; AP-01–04 und fremde Arbeit erhalten. AP-06 nur vorbereitet, nicht ausgeführt.

## 03.10.2026 – AP-04: tatsächliche Randpunkte und begründete Kernwahl

**Nutzerentscheidung:** AP-04 ausdrücklich „gut dann mach mit 04 weiter“. Saubere AP-03-Basis `495b538`, Branch `feature/frontier-candidate-core`, Software `5ee313b`. MASTERPLAN v1.3 unverändert; AP-03-Auftrag bytegleich archiviert.

**Entscheidung:** Exakten `mertgulerx/frontier_exploration_ros2`-Pin unverändert bauen/vergleichen, ohne dessen Missions-/Dispatchschicht. Gleiche Eingaben, endliche Sicht, Geometrie, Planer und Budgets. Seine einzelne Ringroute scheitert, langer Rand bleibt mit einer Sichtposition unzureichend erschlossen. Gemäß ausdrücklich erlaubter Planalternative die eigene Gewinnung begrenzt korrigieren: echte freie Randzellen in räumlichen Teilbereichen, bekannte Annäherungsseite, gültige reale Scan-/Montage-/Masken-/Reichweitensicht. Keine externe Runtimebibliothek, keine dritte Software; historische Schwerpunktquelle als read-only Prozessstart-Rückfall erhalten.

**Evidenz/Grenzen:** Alle sieben Pflichtfälle und elf Kartenstände; native volle Pfadprüfung belegt Ringalternativen und 5,9 m gegenüber 1,9 m sichtbaren Rasterrand. 27 neue Fälle, 1.636 betroffene / 165 installierte / 1.604 colcon-Tests (Überlappung), frische aktuelle/native Builds und bytegleiche Installation. Unzulässige native Zielgeometrien sowie korrigierte Prüferfehler sichtbar. Lizenz/Pin, Originalnachweise und exakter Umfang im [STATUS](wohnungserkundung/STATUS.md). Sichtmöglichkeit ist kein gemessener Fortschritt; missionseigene Erledigung/Wiederbeobachtung ausdrücklich AP-05. Keine Frist-/Kontur-/Unknown-Lockerung, Hardware, Deployment, Push/Merge oder Jetson-Installwechsel. AP-05 nur vorbereitet; physische und vollständige Kettenabnahme AP-06. Rückfall gezielt eigene AP-04-Commits revertieren, AP-01–03 und fremde Arbeit erhalten.

## 03.10.2026 – AP-03: tatsächlicher Bewegungspfad und autonomer Bootstrap

**Nutzerentscheidung:** AP-03 nach AP-02 ausdrücklich beauftragt; Basis `875c7c4`, Branch `fix/nav2-bootstrap-geometry`, Software `c3115ff`. MASTERPLAN v1.3 unverändert, abgeschlossener AP-02-Auftrag bytegleich archiviert.

**Entscheidung:** Ein verworfener kürzester Eigenpfad darf einen zulässigen längeren tatsächlichen Nav2-Pfad nicht blockieren. Vorschlag und Bewegungsfreigabe trennen, im vorhandenen Explorer bleiben und NavFn A*/RPP anhand echter geschlossener Messungen weiterverwenden. Rollout-Profil ausdrücklich simulationsqualifiziert, schreibgeschützt und mit enger geprüfter Vorausrichtungsübergabe; konservativer Default und sämtliche gemessenen Chassis-/Raster-/Goalreserven erhalten. Gemeinsamer [Bewegungsvertrag](wohnungserkundung/BEWEGUNGSVERTRAG.md); konkrete Sensorabdeckung separat nur vorbereitet.

**Evidenz/Grenzen:** Acht echte Nav2-Fälle einschließlich 68/80 cm, Umfahrung, autonomer erster Frontier-Beobachtung und sicher gesperrten Negativfällen. 22 neue Regressionen; aktuelle AP-02-Laufzeit besteht 1.609 betroffene, 138 installierte und 1.577 colcon-Tests (Überlappung), echte isolierte Builds. Ein enger unveränderter DDS-Test schwankte im älteren Nav2-Prüfimage; Originalfehler und Gegenproben erhalten. Ergebnis, Bedingungen und Rückfall ausschließlich im [STATUS](wohnungserkundung/STATUS.md). Keine Fristlockerung, Hardwarewirkung, Deployment oder Push/Merge. Reale Motor-/Sensor-/Stopplast bleibt offen; AP-04 nur durch eigenen nächsten Auftrag.

## 03.10.2026 – AP-02: Kartenarbeit und Quellenvertrag

**Nutzerentscheidung:** Nach abgeschlossenem AP-01 ausdrücklich AP-02 beauftragt.
Saubere Basis `45f268a`, Branch `fix/map-lifecycle-source-contract`, Software
`96bbd4d`. MASTERPLAN v1.3 bytegleich; früheren Auftrag bytegleich archiviert.

**Entscheidung:** Räumliche Startausnahmen an beobachtete Rasteridentität binden
und dauerhaft vor inkompatiblen Arrayoperationen invalidieren. Genau verbundene
Rohkarte/Status verwenden; Inhaltsrevision allein beendet gültige, erneut
geprüfte Weltziele nicht. Beobachtete Kontext-/Auflösungswechsel und Rückwechsel
machen alte Arbeit unwirksam. Produzent zählt exakte Duplikate nicht als neue
Beobachtung und ignoriert alte positive Quellstempel ohne Frischeerneuerung.
Verarbeitungszeit gehört in bestehende Frischebudgets.

**Evidenz/Grenzen:** Gemeinsame aktive/passive HWT-/Encoder-/TF-/Gate-/Explorer-
Budgetzuordnung [hier](wohnungserkundung/QUELLENVERTRAG.md), Softwareprüfung und
Originalbelege ausschließlich im [STATUS](wohnungserkundung/STATUS.md).
55 neue Fälle; 1.587 betroffene, 116 installierte und 1.555 colcon-Tests
bestanden (Überlappung); echte Zehnpaketauflösung. Keine Fristlockerung oder
neue Freiraumannahme. Keine Hardware, Jetson-Runtimeänderung, Deployment oder
Push/Merge. AP-03 getrennt vorbereiten, nicht automatisch implementieren;
aktive Jetsonlast bleibt AP-06. Rückfall nur eigene AP-02-Commits revertieren,
AP-01 und fremde Arbeit erhalten.

## 03.10.2026 – MASTERPLAN v1.3 und begrenzter AP-01-Softwareauftrag

**Entscheidung:** Nutzer hat die angehängten MASTERPLAN v1.3 und AGENTENAUFTRAG ausdrücklich beauftragt. Plan kanonisch übernommen; bisherige vier WE-Dateien bytegleich mit Commit-/Blobbeleg archiviert. AP-01 ausschließlich gerätefrei bis Softwareprüfung, keine Ausführung historischer Fahrt-/Deploymentaufträge. AP-04 hebt die reine Offline-Fremdcodegrenze gezielt für einen geprüften Frontier-Kandidatenkern auf; kein neuer Gesamtstack. Historischer Schwerpunktkern bleibt Vergleichsreferenz.

**Evidenz/Basis:** Remote `feature/hwt-hold-recovery-resume` am 03.10.2026 auf `08a4b9a` bestätigt; sauberer isolierter Worktree/Branch `fix/hwt-clock-correlation`. Älteres main `05439c7` wird nicht als Implementierungsbasis verwendet. Zeitkorrelationsfehler aus Gegenprüfung an Originalmethoden reproduziert und repariert; historischer Roboterabbruch damit nicht abschließend erklärt.

**Betroffene Dateien/Hardware:** WE-Dokumente, AGENTS und Gesamtstrategie; danach ausschließlich HWT-Rawpfad, Tests und notwendiger Clockvertrag. Keine Hardware/Roboternetzverbindung/Runtimeänderung; ROBOT_TRANSFER nicht fortgeschrieben. **Softwareabschluss:** `c797442` repariert den an Originalmethoden belegten Projektionsfehler durch ≤1-ms-Offsetspannen; unsichere Proben altern ohne Reconnect, erkannte Quellen-/Zeitbasisänderungen bleiben hart. 443 betroffene Regressionen, 58 Installimporttests und 381 registrierte colcon-Tests bestanden; Achtpaketbuild. Mengen überlappen. Originalbelege, Clockvertrag und Python-3.12-JSON-Baselinefehler ausschließlich im aktuellen STATUS. AP-01 software_geprüft, reale Abnahmen offen; AP-02 nur vorbereitet.

**Grenzen/Rückfall:** Sensor-/Start-/Geometrieabnahme offen, keine Fristlockerung. Eigene getrennte Dokument-/Softwarecommits gezielt revertieren, keine Rücksetzung unbekannter Arbeit. AP-02-Übergabe vorbereitet, nicht automatisch ausgeführt.

## 30.09.2026 – Metrische Erkundung vor verpflichtender Portal-/Raumsemantik

**Nutzerentscheidung:** Christopher beauftragt Masterplan v1.2 und den nächsten Softwareauftrag. Ziel ist die fortlaufende Schleife aus Beobachtung, erreichbarem Frontier-/Beobachtungsziel, realer Navigation, neuen Messungen und erneuter Aufgabenwahl. Keine dritte vollständige Robotersoftware.

**Wiederverwendung:** Historischer Frontier-/Annäherungskern um `1d91229` plus aktuelle Sensor-/HWT601-/Encoder-/EKF-, Mission-/BT-, Einzelkind-/Cancel-/HOLD- und metrische Validierungsbausteine. Ein Navigator, kein zusätzlicher Motor-/Goalbesitzer. Kein pauschaler Altbranch-Rollback.

**Architekturpräzisierung:** Metrische Ziele innerhalb des gültigen Scopes benötigen keine bestätigte Tür, Region oder Pflicht-PortalMemory. Semantik kann passiv beitragen. Geometrische Durchfahrtsprüfung, notwendige aktuelle Quellen/Pose, Schutzkette, bestätigter Stillstand vor Wiederanfahrt und Budgets bleiben verbindlich. Keine Dummy-Portale/Regionen und kein künstlich gesunder Status. Nicht erreichte Aufgabe ist nicht automatisch Hardwaredefekt; unbekannte sicherheitsrelevante Zustände bleiben bewegungssperrend.

**Bekannte Grenzen:** Der letzte ausgewertete reale Lauf auf `492ef20` endete ohne Ziel-/Türerfolg. SlowZone, fehlende Portalhypothese und unaufgeklärte Timeout-Erstentscheidung bleiben echte Befunde. Aus neuem Plan keine historische Ursache oder neue Abnahme ableiten. Der bisherige Diagnoseauftrag wird als eigenständiger nächster Auftrag abgelöst; benötigte Diagnose und Gegenfälle gehen in das funktionale Softwarepaket ein.

**Betroffene Dokumente:** AGENTS-Einstieg, MASTERPLAN, STATUS, AGENTENAUFTRAG, Gesamtstrategie, Meilensteinpräzisierung und dieses Journal. Frühere umfangreiche Plan-/Status-/Auftrags-/Strategie-/Meilenstein-/Journalfassungen wurden unter ihrer Original-Blobidentität archiviert, damit die aktiven Referenzen nur einen aktuellen Auftrag enthalten. Keine Code-, YAML-, Treiber- oder Hardwareänderung.

**Nachweise dieses Eintrags:** Dokumentationsabgleich; keine neuen Softwaretests oder Realversuche. Akzeptierte frühere HWT-Teilnachweise bleiben erhalten. Neues metrisches Backend erst beauftragt, nicht umgesetzt.

**Nächster Auftrag:** metrischen Kern gerätefrei implementieren und im verbundenen Produktgraph ohne Pflicht-Semantik prüfen: mehrere echte Folgeziele, blockierte Aufgabe mit zulässiger Alternative, HOLD/Cancel und harte Gegenfälle, ehrlicher Abschluss. Danach genau einen begrenzten Realnachweis vorbereiten, nicht automatisch starten.

**Git/Privatsphäre:** LAB-1 unverändert. Reale Karten/Bilder/Bags und private lokale Berichtscommits nicht mitpushen, auch nicht als Vorfahren. Nur Remote-Dokumentbasis veröffentlicht; keine lokale Jetson-Arbeitskopie umgeschaltet. Kein Merge und kein dauerhafter Installwechsel. Rückfall: gezieltes Revert der Dokumentationsänderung ohne Roboterruntime-Eingriff.

## 30.09.2026 – metrischer Kern implementiert, gerätefrei verbunden geprüft

**Entscheidung und Modulgrenze:** `exploration_strategy` ist read-only und standardmäßig `existing`; `metric_frontier` wird ausschließlich bewusst mit eigenem Overlay gewählt. Zwei kleine Module im vorhandenen Explore-Paket verbinden historische Cluster-/Annäherungs-/Bewertungshelfer mit aktuellen Kartenidentitäts-, Scope-, Quellen-, Nav2-Einzelkind-, Scan-/Vorausrichtungs- und HOLD-/ACK-Verträgen. Kein Pflicht-Portal-/Regionsfeed, keine künstliche Region, kein zweiter Navigator. Alte semantische Policy/Navigation, direkte Brücken, Coverage und Rückkehr sind in diesem Modus ausgeschlossen.

**Geometrieentscheidung mit Messgrund:** bekannte freie Rohkarte/Scope und aktuelle Costmap zuerst; anschließend vollständige gepaddete asymmetrische Fahrzeugkontur einschließlich Drehungen, danach Nutzen. Rastertreppen werden mit dem bestehenden freien Segmenthelfer vereinfacht; keine unnötige Drehung an jeder Zelle. Im synthetischen Blockadefall berührte die gedrehte Front am alten kreisgeprüften Annäherungspunkt unbekannte Zellen. Innerhalb des bereits bestehenden lokalen Suchradius werden nun zurückliegende Annäherungen und deren vollständige Routen geprüft. Gezielt getestet: beide zulässigen Alternativen entstehen, wirklich gesperrter Weg bleibt gesperrt. Keine Kontur-/Kollisions-/Frischegrenze gelockert. Initialscan prüft die Kontur auch während laufender Kartenänderungen. Ein im verbundenen Scan gemessenes kurzzeitiges `vl53_triplet_unmatched` wird wie in der Navigation durch das echte Gate gesperrt, ohne sofortigen terminalen Scanabbruch; tatsächlich ungültige/stale Quellen bleiben wirksam. Kartensperre während Scan separat als Gegenfall geprüft.

**Fortsetzungsvertrag:** Nav2-Terminalzustand plus frischer stabiler Encoderstillstand und konsistenter Betriebssnapshot vor anderer Aufgabe. Timeout/Abort bei sonst gesunden Quellen lautet `task_unreached_cause_unproven`, keine erfundene lokale Hindernisursache und kein pauschaler Hardwaredefekt. Räumliche Historie verhindert Retry über neue UUID/Revision; Cooldown, geänderte Kartenevidenz und Versuchsbudget nötig. Erfolgreiche Nachbarschaften bleiben für dieselbe Mission bedient. Absolute Aufgabenfrist umfasst Vorausrichtung, Kindwechsel und HOLD; kleine Drehungen setzen nichts zurück.

**Schutzkorrektur:** bestehender gemeinsamer Nav2-Client merkt ausstehende Annahme und fehlenden Terminalbeleg; neue Elternaufträge bleiben gesperrt. Eine nach Timeout verspätete Annahme wird automatisch gecancelt. Kurze HWT-Lücken werden unabhängig von teurer Routenarbeit mit dem bestehenden HOLD-Vertrag geprüft; wiederholte Störung verlängert die Frist nicht, Stillstand und Gate-ACK bleiben Pflicht.

**Statusmigration:** additive `strategy`/`metric_exploration`-Felder, aktive Auswahl, Route, Retry, Filter und Snapshot sowie begrenzte Ergebnis-/Folgezielkette. Kein ExploreArea-Gesamterfolg, keine automatische Speicherfreigabe; semantische Vollständigkeit/Bodenabdeckung/Wohnung ausdrücklich ungeprüft. Selbst vollständig bekannter Scope ergibt höchstens einen metrischen Abschlusskandidaten/Teilstand.

**Belege:** isolierter Sechspaketbuild; 1.342 pytest-Regressionen und registrierte colcon-Tests ohne Fehler. Verbundener echter Mission-Manager/BT/Explorer/Kartenmanager/HWT/Gate-Graph, synthetische Raster/physische Eingangsmeldungen/Nav2-Gegenstelle. Pflichtfallmatrix, drei autonom erreichte Rasterziele, Alternative nach unerreichter Aufgabe, offene Verbindung ohne Türlabel, HOLD/Cancel, harte Quellen-/Aktuator-/Posefälle und ehrlicher Teilstand in STATUS §4. Keine Geräte-/Sensorprozesse, keine reale Fahrt. Nach einem Umgebungsneustart verschwanden temporäre Tests; Abschlussbuild und Logs deshalb lokal dauerhaft unter `~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/`, außerhalb Git.

**Offline-Grenze:** je drei lokal gespeicherte historische/aktuelle Snapshots nur lesend verglichen. Alte/neue Kandidaten historisch 15/7/11 gegenüber 0/4/11, aktueller Fehllauf 10/13/12 gegenüber 0/0/0. Rastergrenzen-Scope nur zur Analyse, keine Live-Gesundheit oder reale Fahrabnahme. Unzulässige Rohkarten-/Footprint-/Routenlage bleibt ein Blocker; keine Kartenverbesserung oder behobene historische Ursache behauptet.

**Git, Runtime und Rückfall:** unabhängiger Checkout auf veröffentlichtem `1dbbdaa` in derselben PR-#105-Linie; laufendes `~/roboter_ws` unverändert, keine privaten Berichts-Vorfahren, keine Rohdaten in Git, kein Merge oder permanenter Installwechsel. Rückfall: metrisches Overlay abwählen, geordnet ohne Mission mit `existing` starten; sichere Betriebsgrenze weiterhin `active_drive=false`, `enable_auto_explore=false`. Genau ein begrenzter Realnachweis vorbereitet in AGENTENAUFTRAG §7, nicht gestartet. Stufe 3 bleibt offen.


## 01.10.2026 – Mast-Eigenkörpervertrag und begrenzte passive Encoderheilung

**Betreiberinformation:** Der rückwärtige graue Keil ist der OAK-Kameramast.
Die vorhandene native 236–304°-NaN-Maske, ROS-CCW und gemessener +90°-TF werden
weiterverwendet; aktuelles Install, Scanverbraucher und Laufdaten geprüft.
Keine neue Maskierung oder Außenraumfreigabe.

**Entscheidung:** Nur ganze unbekannte Zellen im ungepaddeten gemessenen Körper
werden privat auf erste korrelierte Pose/Fingerprint begrenzt behandelt.
Dieser Beleg folgt nicht der Bewegung und erlischt bei Fingerprintänderung.
Belegte Zellen, unbekannter Außenraum, Padding und Rasterreserve bleiben gesperrt;
voller Fahrzeug-/Drehsweep auf Rohkarte und Costmap erhalten. Positive Regression
mit versetztem LiDAR und tatsächlich belegtem Außenraum; die reale aktuelle
Geometrie bleibt trotz korrekter Eigenkörpertrennung unzulässig.

**Encodervertrag:** vorhandene gemeinsame FC03-Blöcke erhalten. USB-Pfadsuche
vermeiden, tatsächliche Identität/Exklusivität/CRC und Messzeitbezug erhalten.
Nach ≥20 gesunden Paaren ein isolierter vollständiger Timing-Ausreißer bei
belegter 180-ms-Kontinuität: ungültiges Paar zurückhalten, unbereit/HOLD,
zwei neue plausible vollständige Paare, alle Zähleränderungen erhalten.
120-/180-ms-Grenzen unverändert; harte Fehler erfordern neue belegte stationäre
Initialisierung und Karten-/Odometriezuordnung, kein Faultflag-Reset.
Passiver Readerstart 15 s staffeln. Passive Gate-Quellencallbacks unabhängig
vom normalen seriellen Callback verarbeiten; aktiven Pfad separat erhalten.

**Grenze/Nachweis:** 1.340 Regressionen und synthetischer `mast_start` bestanden;
Achtpaketinstall temporär. Letzter realer Reader 4.284 gültige Paare, keine
120-ms-Überschreitung; Gate nach echter HWT-Kurzstörung zunächst recovered,
später Radfrische terminal. Die Softwarekorrektur beweist keine vollständige
reale Verbraucherrobustheit. Keine Mission/Fahrt, A/B/C offen. Zahlen, Zellklassen,
Zeitverteilungen und einziger gemeinsamer Startnachweis im WE-STATUS; technische
Jetson-Wirkung im ROBOT_TRANSFER. Kein Masterplanwechsel, keine privaten Daten
oder Berichts-Vorfahren veröffentlicht, kein Merge/Hauptinstallwechsel.


## 01.10.2026 – Radentscheidung atomar, DDS-Übernahme und reale Geometrie präzisiert

Ausgang `cf55cea`, Funktionskandidat `8f5eeb4`, bestehende PR #105.
Jeder neue Fehlerübergang erhält seinen eigenen Originalzustand; first_fault
bleibt historische erste Störung, letzte Wheelentscheidung enthält vorherige
Recovery. Diagnose-JSON/DDS bounded außerhalb Stopptimer. Uhrbezug am tatsächlichen
ROS-/Monotonic-Bracket statt Callbackeintritt vermeidet doppeltes Präemptionsalter.

Zwei aktuelle Consumerfehler exakt reproduziert: 215,948 bzw. 186,344 ms alte
Wheelprobe trotz neueren Recorderreceipts. Recorderzeit nicht mit Gatecallback
gleichsetzen. Passive eigene Radgruppe allein reicht nicht. Nichtblockierender
Take derselben tatsächlichen Depth-1-Subscription direkt vor Gateentscheidung,
Callbackgruppenschutz, ursprüngliche Stempel und harte Gegenfälle erhalten.
Aktiver Basispfad bleibt seriell und separat regressiert; keine neue Quelle.
Aliaslinks/Gerätegenerationen und echte USB-Attribute weiterhin pro FC03 prüfen,
nur voller Pfadwalk an Bindung. 120-/180-ms-Verträge bleiben unverändert.

Ganze Körperzellen über exakte Projektion statt pauschalen Zellendiagonalradius:
bei erhaltenem aktuellem Start 14 echte Fehlablehnungen entfernt. Keine teilweise
überlappende Zelle, kein Außen-/Padding-/Reserveraum freigegeben. Scan während
Kartenarbeit gegen danach erfasste Zeit prüfen. Finale Geometrie 211 unbekannte
Rundblickzellen  / 0,188420 m² Außenanteil ; 139 Costmap-Zellen darin, keine Addition.
Das beweist erforderliche zusätzliche stationäre LiDAR-Außenbeobachtung, keinen
hardwarefreien Softwareweg zur Freigabe. Manuelles Umsetzen bei deaktivierten
Antrieben ist eine getrennte äußere Bedienhandlung.

1.469 Regressionen und isolierte Builds bestanden. Gerätefreier kurzer Scan/
Vorausrichtung / drei Folgeziele positiv, volle 2π-Dauerprobe mit Quellenpausen negativ
und erhalten. Vier begrenzte 720-s-Realfenster nach konkreten Korrekturen;
letztes nach zwei echten HWT-Recoveries erneut negativ, jetzt echte
120,874-ms-Readerpaarverletzung, Gate 212,127 ms stale, keine zulässige neue Probe.
Keine unbewiesene Encoder-/Kabel-/Kernelursache aus Phasenzeiten. Weitere
Transport-/Runtime-Latenzabsicherung separat begrenzen; keine automatische
Neustartserie.0 Missionen / 0 Nav2-Kinder, FC03-Endwerte null, Prozesse und Handles frei.
Private Einzelzellen/Bags/Manifeste lokal, Hauptkopie unverändert, kein Merge/
permanenter Installwechsel; Rückfall temporäre neue Overlays abwählen. Stufe 3 offen.

## 01.10.2026 – adaptiver Bootstrap und begrenzter Auftragserhalt bei Encoder-Timing

Nutzerpräzisierung im MASTERPLAN v1.2/AGENTENAUFTRAG §10; Ausgang `d9894d2`,
Funktionskandidat `fd883fd`, bestehender Branch/PR #105. `metric_frontier`
startet mit unveränderlichem `metric_start_strategy=adaptive`: zulässiger
nützlicher Rundblick, sonst berechnete Beobachtungsfahrt, sonst begründeter
Teilstand. `existing` bleibt Default; Scan bleibt verfügbar/eingeschaltet.
Kein manuelles Vorkartieren/Umsetzen als autonomer Nachweis. Unbenutzte 360°-
Fläche darf keine andere sichere Bewegung sperren; die tatsächlich beanspruchte
Anfangskontur, Vorausrichtung, Controllerkurve, Route und Zielrotation dagegen
vollständig prüfen. Tatsächlicher Nav2-Plan/13 RPP-/Goalcheckerparameter sind
Voraussetzung. Ein unbekanntes Padding wird nicht zum Eigenkörper erklärt.
Körperbeleg ist an Anfangsraum/Karten-Odometriebezug gebunden: normale Raster-
inhaltsupdates verkleinern ihn nur; neuer Kontext/Raster/Bezug lässt ihn
verfallen, niemals mitwandernde Blase. Dies präzisiert ältere pauschale
Fingerprint-/Vollrundblickanforderungen; historische Messungen bleiben erhalten.

Messvalidität 120 ms, Frische/Integration 180 ms und begrenzter Auftragserhalt
sind getrennt. Gemeinsamer Core in passivem Reader/aktiver HWT-Basis: 2 s
Diagnosefrist, zwei Versuche je Readerlebensdauer, keine verworfenen Odomdaten,
Rebase oder verlorenen Zählerdeltas. Verbraucher maximal 5 s / zwei Recoveries
je HWT-/Radquelle. Resume nur mit belegter Kontinuität, Originalstempeln,
Stillstand/Fusion/Route/Kindterminal/Gate-ACK. Alte 120,874265-ms-Paarverletzung
mit 212,127149-ms-alter Gateprobe exakt reproduziert: Erstgrund Readerzeitfenster,
danach Kontinuität unbewiesen. Spätere gute Paare/0 RPM heilen das nicht.

1.493 Regressionen, isolierter Fünfpaketbuild und verbundene A–H-Fälle im
dokumentierten Umfang bestanden. Mehrere autonome synthetische Folgeziele,
später nach neuer Karte zulässiger Scan, Timing-HOLD und getrennte HWT-/Rad-
ereignisse. Historische und neue vollständige 2π-Dauerprobe bleiben negativ:
neuer 259,27-s-Versuch mit bis 515,70 ms Rohquellenlücke/Budgeterschöpfung;
kurze positive Zulassungstests beweisen keinen abgeschlossenen Vollscan.

Genau ein neues reales 720-s-Messfenster mit gleichem installierten Kandidaten:
HWT-Recoveries bei 162,718/401,729 s, dritte Rawdriverstörung nach 583,261 s
terminal `hwt_recovery_attempt_limit` (`Zeitueberschreitung nach 0/14 Bytes`).
Radreader am Fensterende 13.921 Paare ohne Timingfehler, größtes Paar 108,118 ms;
kein realer Encoder-Recoveryfall. Geometrie separat negativ: 33 unbekannte
Startkonturzellen / 0,021089 m² Außenanteil, kein berechneter Startkandidat.
Die optionale Rundblickentscheidung löst diese beiden Grenzen nicht.
Kein aktiver Wechsel, 0 Missionen/Nav2-Kinder, ausschließlich Nullbefehle.
Messprobe beendet bei 720,016 s; rein lesender Abschluss-/Stoppnachlauf noch
185,994 s offen ausgewiesen. Danach alle manifestierten Prozesse/Handles frei,
zwölf frische FC03-Paare Position/RPM null. Kein weiterer Neustart/Fahrversuch,
keine unbewiesene Hardwareursache. Private Belege in
`~/.local/share/amadeus/tests/metric-adaptive-start-20261001/`, Hauptkopie
unverändert, Stufe 3 offen, **System eingeschaltet lassen**.

## 01.10.2026 – HWT-Pollzustand und feste Start-Egress-Geometrie getrennt

Nutzerauftrag auf `2a0e19d`, Funktionsstand `a6f31bf` im bestehenden PR #105.
Explizites Entwicklungsopt-in setzt 50-ms-Antwortfrist/300-ms-Rohfrische.
Frischer Originalwert bleibt bei transientem Pollfehler nutzbar; verspätete
Antwort verworfen, kein Restempeln. Zwei echte HWT-HOLDs im rollenden 60-s-
Fenster, jeder absolut 5 s; keine Task-ID-Rücksetzung. Noch frischer korrigierter
Originalwert kann nach verworfener Grenzmessung erhalten bleiben; kein
Integrieren der Lücke, keine Änderung der 100-ms-/800-Sample-Kalibrierung.
Legacy 30/200 ms, Encoder 120/180 ms und harte Fehler bleiben erhalten.

Start-Egress im bestehenden Explorer: fester unbekannter Ausgangsbestand
beider Raster, keine neue Beanspruchung/Annäherung/Wiederbetretung; ganzer
reservierter Körper entlang tatsächlicher RPP-Kurve und strenge Zieltoleranzen.
Anker-/Raster-/Kontextwechsel entzieht die Ausnahme endgültig. Nach nominalem
Verlassen bleibt der Bewegungsbeleg gekoppelt, solange eine Drehung noch den
Bestand berühren könnte. Keine globale 33-Zellen-Liste oder fahrende Blase.

1.564 Regressionen sowie gerätefreier Drei-Ziel- und HOLD/ACK/Resume-Graph
bestanden. Reale kurze Schlussmessung nach gemessener Portprüfungsoptimierung:
HEALTHY 36,379 s, terminale hostseitige Messzeitprüfung 54,880 s innerhalb
60,008-s-Fenster. Zwei vorherige Pollfehler nur degraded, null echte HOLDs.
Keine bewiesene Hardwareursache. Aktuelle Karte unabhängig: 22 Kandidaten
alle unzulässig; keine reale Mission oder Ziel-/Passagenabnahme. Historischer
720-s-/33-Zellen-/2π-Negativbefund bleibt separat erhalten.

Isolierter Build, 100 Bytevergleiche und native Parameter gesichert;
Live-Explorer-Abfrage während Initialisierung nicht verfügbar. Endzustand
ROS beendet, Gerätehandles frei, zwölf FC03-Paare Position/RPM null,
Hauptkopie unverändert. Private Daten ausschließlich lokal unter
`~/.local/share/amadeus/tests/metric-egress-hwt-20261001/`. Rückfall Overlay
weglassen/Opt-ins beim gestoppten Start deaktivieren; kein Installwechsel
oder automatischer weiterer Realversuch. Nutzerklärung ausdrücklich:
**ROS-Stack beenden, Rechner eingeschaltet lassen.** Details im aktuellen
[STATUS-Abschluss](wohnungserkundung/STATUS.md#aktueller-abschluss-hwt-entwicklungsvertrag-und-start-egress-01102026).

## 04.10.2026 – AP-06 native Integration und ehrliche Gesamtgrenze

MASTERPLAN v1.3 beibehalten. Originaler Mission-/C++-BT-/Explorer-/Nav2-/SLAM-/EKF-Pfad mit realen Scan-/Safety-Knoten auf einem ausdrücklich gerätefreien Modell geprüft. Gezielte Integrationskorrekturen: aktuelle statt zukünftiger SLAM-TF, passweise identische Geometrieprüfung, Ziel-/Startbeweis getrennt und Vororientierung am tatsächlichen RPP-Carrot, ursprünglicher Planabbruchgrund erhalten. Begrenzte VL53-Räumendpunkte markieren keine Hindernisse; unveränderte getrennte Messwolken behalten diese Rolle. Eine bloße numerische Reichweitenlücke war wegen nativer Rasterrundung kein sicherer Rollentrenner. Native Rot/Grün-Gegenprobe bewahrt nahe Hindernisse.

Bestehender Startadapter darf unter unverändertem Egress-/RPP-/Scope-/Sichtbeweis die erste nützliche nahe Vorwärtsposition prüfen, innerhalb vorhandener Suche/Frist und anschließend mit wirklichem Nav2-Plan. Keine feste Wegpunktliste, bewegte Weißblase oder neue Navigation. Die tatsächliche erste SLAM-Aktualisierung entzieht danach noch die feste Referenz; kein stilles Re-Ankern zur grünen Abnahme. Vollständiger Zustand und genau nächster AP-06-Schritt ausschließlich im [STATUS](wohnungserkundung/STATUS.md). Build/Regressionen sind grün, drei vollständige Gesamtmissionen negativ; Dokumentation/Komponentenprüfung bedeuten keine Realabnahme.

App-Projekt auf lokalem Jetson und tatsächlich erreichbarer Ausführungsbackend sind getrennt: diese Werkzeuge bleiben in x86-Cloud ohne Roboterzugang. Keine neue LAB-1-Standardfreigabe nötig, technische Voraussetzungen weiter maßgeblich. Keine Jetson-/Install-/Autostartwirkung, ROBOT_TRANSFER unverändert; AP-01–05/Main/fremde Arbeit erhalten.
