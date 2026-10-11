# AP-06: Korrekturprüfung F7/F8 vom 11.10.2026

## Urteil

**Vier begrenzte Korrekturen liegen vor; F7 und F8 sind insgesamt noch offen.**
Der finale Softwarelauf besteht mit **3.136 Tests, 0 Fehlern und 0 Skips**.
Auf demselben Produktstand scheiterte zuvor jedoch einer der beauftragten
Quellenfälle. Eine grüne Wiederholung beseitigt diesen negativen Nachweis nicht.
Gesamtmissionen und Hardwareabnahme werden getrennt ausgewiesen.

Belegt korrigiert sind der begrenzte TF-Queue-Empfang, die Zeitabhängigkeit eines
reinen Auswahlentscheidungstests und ein tatsächlich blockierender
Warteschlangenaufruf im Sensorproduzenten. Zusätzlich wurde die nachgewiesene
CPU-Vererbung vorhandener Ausgabearbeiter im Simulationsprüfstand korrigiert.
Diese Korrektur beseitigt die Ressourcenkopplung; sie belegt noch keine
zuverlässige Sensor-/TF-/Kartenbereitschaft des gesamten Verbunds.

## 1. Auftrag und unveränderte Verträge

Ausdrücklich beauftragt sind ausschließlich F7/F8 des
[Audits](AP06_EXTERNER_AUDIT_20261011.md), unter MASTERPLAN v1.5,
WE-M0/M3/M4/M5/M6; WE-M7 bleibt gesondert. Gerätefreie Entwicklung und
Softwareprüfung, keine Jetsoninstallation, kein Autostartwechsel und keine
reale Aktorbewegung. LAB-1 autorisiert hier keine Ausweitung des Auftrags.

Erhalten: Mission → BT → Explorer → Nav2 → Schutzkette, ein Navigationsbesitzer,
F1–F5, F6-CI-Auswahl und die vorhandene Slot-Strategie. Keine neue
Explorerarchitektur oder zusätzliche Prozessschicht. Rohkarte, Sensorstempel,
Frische-/Kontinuitätsgrenzen, Faultflags, Versuchshistorie, Budgets, Prüfwelten und
Abnahmekriterien bleiben unverändert. Die tatsächlichen Quelle-/Install-Dateien
und Konfigurationen sind gebunden; `preserved-contracts.json` weist die
unveränderten zentralen Laufzeiten, F6, Welten, Manifest und Nav2-Konfiguration
mit SHA256 nach.

## 2. Versionen, Build und Quellenbindung

| Gegenstand | Stand |
|---|---|
| Beauftragte Produktbasis | `900ce5d8a3f56dd5f59f6b16462d3a9cb1cc8a53` |
| Ausgangs-HEAD mit Dokumentation/CI | `1b3bc987913d518776f495fdc5b2e0cbabec383c`, `fix/ap06-slot-audit` |
| Korrekturbranch | `fix/ap06-source-startup`, eigener Worktree |
| Final gebautes/getestetes Produkt | `cf010a03c96ad981516b52d96f5c21dda78c4369` |
| Zwischenprodukt des ersten neuen Gesamtlaufs | `6bbec19fe7506880efb22ba69f48be09c5ccd42e` |
| Plattform | Ubuntu 22.04, ROS 2 Humble, Python 3.10.12, x86_64, `rmw_fastrtps_cpp` |

Originalworktree und Originalinstall bleiben erhalten. Vor den Produktprüfungen
war der Korrekturworktree sauber. Submodulzeiger `src/behaviortree_ros2`:
`6c6aa078ee7bc52fec98984bed4964556abf5beb`, im Worktree nicht ausgecheckt.
Der bereits gepinnt gebaute native 37-Pakete-Unterbau wurde wiederverwendet:
36 ament-Präfixe plus der separate CMake-Install `rsl`. Die Unterbauten wurden
erneut gehasht und gebunden, nicht auf einer zweiten Maschine neu gebaut.

Alle **15 Produktpakete** und die echte C++-TF-Prüfsonde wurden in getrennten
Build-/Install-/Logverzeichnissen gebaut; nach der Warteschlangenkorrektur
`base_hardware` erneut. Bindung: **15 private Produktpräfixe, 163 bytegleiche
Quelle-/Install-Dateien und 18 tatsächlich geladene Module**, einschließlich
TF-Empfang, Encoderpublikation und nativer C-Sweep-Erweiterung.
Da das Host-Gitverzeichnis im Container nicht sichtbar ist, wurden Commit und
sauberer Zustand auf dem Host erfasst und alle erfassten versionierten Dateien
im Container gegen ihre SHA256 geprüft. Alle Produkt-/Unterbau-Install-Dateien
sind zusätzlich in `installed-files-sha256.json` gehasht; System-ROS/Compiler
und Python-Pakete sind mit Versionen erfasst. Dokumentation folgt als separater
Commit hinter dem getesteten Produkt; der Lieferstand steht im Artefaktmanifest.

Der isolierte Container hatte fünf CPUs; keine cgroup-CPU-Drosselung wurde
beobachtet. Es gab erhebliche virtuelle CPU-Steal-Zeiten. Das ist ein
gemessener Störfaktor, aber kein Beweis, dass alle Zeitfehler allein vom
Hostscheduler stammen. Prozesskontrollen fanden nach Bereinigung keine
lebenden zurückgelassenen ROS-Prüfprozesse; verbliebene Zombies können keine
DDS-Daten veröffentlichen. ROS-Domänen und geladene Module sind in den Belegen
erfasst. Eine Reihenfolgeabhängigkeit durch einen konkreten Vorgängertest wurde
nicht bewiesen.

## 3. F7: Quellen- und Startpfad

### 3.1 Vorherige Belege erhalten

Die ursprünglichen A/C-Läufe auf `12de37e` scheiterten an
`SLAM initial actual map`, B an `real scope and HWT readiness`;
Cancel/HOLD ebenfalls vor Bewegung und Fehlerinjektion. Encoderlücken bis
0,82659 s und Paarlesungen bis 0,32713 s überschreiten die unveränderten
Grenzen 0,18 s beziehungsweise 0,12 s. Diese alten Zahlen identifizieren für
sich allein keinen langsamen Verarbeitungsschritt.

Die alten Audit-Logs/JUnit-Dateien sind mit ursprünglichen SHA256 gesichert.
Zusätzlich liegen Originalrohzustände der Gerätefälle vor. Negative Diagnose-
und Zwischenläufe bleiben erhalten; sie werden nicht durch spätere grüne
Resultate ersetzt.

### 3.2 Gemessene Zeitkette bei Nullkommandos

Die zusätzlichen Diagnosen verwenden die echten Basis-/HWT-Verarbeitungen
am vorhandenen simulierten FC03-Endpunkt, echte DDS-Ausgaben, Fusion/EKF,
TF, Scan-Normalisierung und SLAM. Erfasst: Beginn/Ende von Encoderbaseline,
Encoderpoll, FC03-Lesungen, Basisupdate, HWT-Poll und Queue-Übergabe;
ursprüngliche Headerstempel, DDS-Publikationsbeginn/-ende sowie Empfang von
Basisstatus, Roh-HWT, Shadowstatus, Radodom, `/odom`, `/tf`, `/tf_static`,
`/scan`, `/scan_normiert` und `/map`. Späte Diagnosen enthalten zusätzlich
Wallclock-/Monotonic-Zuordnung und tatsächlich geladene Modulpfade.

Der Diagnosewrapper unterbindet die erste Explore-Anforderung, wenn die
Bereitschaft erreicht wird. Er ist deshalb **kein Gesamtmissionsnachweis**.
Native-/Stack-/Scheduling-Instrumentierung kann den Lauf zusätzlich belasten;
die uninstrumentierten Originalgesamtfälle werden separat ausgeführt.

Konkrete Ereignisketten:

- Ein reiner Quellenlauf ohne den vollständigen Graphen war 25 s gesund;
  größter empfangener Radquellstempelabstand 0,150561 s, darunter 0,18 s.
  Dies belegt lediglich diesen Lauf, nicht stabile Gesamtbereitschaft.
- Im ursprünglichen vollständigen Startgraphen wird eine Lücke von
  **0,963837 s** verworfen; die Paarlesung selbst dauert nur **0,000360 s**.
  Die drei Quellenexecutoren stocken gemeinsam vor dem nächsten Callback.
  Der erste Kontinuitätsbruch liegt bereits in der **Produktion der Radprobe**,
  vor deren Queue-Übergabe/DDS-Empfang. Gesunde Roh-HWT-Daten schließen den
  ungültigen Radpfad nicht; der Shadowzustand erhält keine gültige Fusion.
- Ein weiterer Nullkommandolauf verwirft eine Paarlesung von **0,287166 s**.
  Der betroffene Speicherbuszugriff benötigt nur etwa **0,000725 s Thread-CPU**
  und wartet im Pflanzensimulations-/Lockpfad. Hier liegt der erste Bruch im
  **Erfassungsschritt**, nicht erst beim Empfänger. Schedulerdaten zeigen
  gleichzeitig hohe Steal-Zeiten. Lockbesitzer, native/GIL-Wartezeit und
  Descheduling sind damit noch nicht eindeutig gegeneinander getrennt.

Der letzte Nullkommandogegenfall bindet ausdrücklich Produkt `cf010a0`, alle
installierten Module und die gehashten Messskripte. Er verwirft **0,212766 s
Quellabstand** bei nur **0,000313 s Paarlesung**. Die letzte gültige Originalprobe
durchläuft Queue, DDS und Empfang in **14,467 ms**. Die nächste Erfassung beginnt
erst zu spät; dies ordnet den ersten Kontinuitätsbruch in diesem Lauf dem
Produzenten zu. Die instrumentierten Quellen verändern weder Stamp noch Frist.

| Übergang der letzten gültigen Radprobe | Monotonic-Zeit in Sekunden |
|---|---|
| FC03-Poll Beginn / Ende | 45541,120485 / 45541,120891 |
| Queueübergabe Beginn / Ende | 45541,121030 / 45541,121286 |
| Tatsächliche DDS-Publikation Beginn / Ende | 45541,123912 / 45541,124160 |
| Empfang des ursprünglichen Radodomheaders | 45541,135105 |
| Nächster verworfener FC03-Poll Beginn / Ende | 45541,333235 / 45541,333695 |

Originalheader `[1791755692, 904525181]`; erster Verwerfungsgrund
`encoder_luecke_nicht_ueberbrueckbar`. Das äußere `encoder_sample_dt_s` steht
dabei noch auf 0,057832 s, die verschachtelte erste Verwerfung auf 0,212766 s.
Nach Ablauf der unveränderten Wiederprüffrist latcht
`encoder_timing_continuity_unproven`. Die vollständige Kette und alle 14
empfangenen Topicgruppen stehen in `final-time-chain.json` und dem Rohjournal.
Alle aufgezeichneten Pflanzenkommandowirkungen dieses Diagnosefalls sind null.

Der bisher nicht vollständig instrumentierte Executorabschnitt der Erfassungs-
TID 47557 liegt zwischen 45541,138023 und 45541,318543. Die benannten
WaitSet-Aufrufe der anderen Quellen und Schedulerwerte sind erfasst; eine
eindeutige Erklärung dieses Abschnitts fehlt. Der Scheduler-Monitor stempelt
eine ganze Leseiteration, nicht jeden einzelnen TID-Zugriff. Aus seiner groben
Korrelation keinen alleinigen nativen/GIL-/Host-Verursacher ableiten.

**Wichtig für die Auswertung:** Nicht nur `encoder_sample_dt_s` lesen.
`encoder_timing_recovery.first_timing_rejection` bewahrt in Recoverypfaden den
ursprünglichen Auslöser. In einem direkten terminalen Lückenpfad kann aber auch
dieses Feld `null` bleiben: dann `fault_latched`, `fault_reason`,
`current_reason`, `last_attempt_gap_s`, `published_count` und äußere
Feedbackflags mitprüfen. Ein `null`-Feld ist kein Gesundheitsnachweis.

### 3.3 Bestätigter Publikationsfehler: vermeintlich nicht blockierender Empfang

**Stelle:** `src/base_hardware/base_hardware/encoder_publication.py`,
`_Publisher.publish`, Überlauf einer `multiprocessing.Queue(maxsize=1)`.

**Ursache:** Bei voller Queue entnahm der Sensorproduzent mit `get_nowait()`
das alte Element, um das neue einzusetzen. Eine lesbare Pipe kann jedoch erst
den vier Byte langen Nachrichtenkopf enthalten. `get_nowait()` wartet dann
auf den verbleibenden gerahmten Inhalt und blockiert den Produzenten.
Der Name garantiert keinen zeitlich beschränkten Empfang eines Teilrahmens.

**Reproduktion:** Echte Multiprocessing-Pipe, native ROS-String-Serialisierung
vorbereitet, 20.033 Byte serialisierte ROS-Nutzdaten, Header tatsächlich geschrieben,
Restpayload 0,35 s verzögert. Gegen die alte installierte Klasse blockiert
der Aufruf **0,410999 s**, obwohl die Kontinuitätsgrenze 0,18 s beträgt.
Es handelt sich um synthetische Testdaten; daraus folgt nicht, dass dieser
Mechanismus jede historische Sensorlücke verursacht hat.

**Änderung:** Der Sensorproduzent empfängt niemals mehr aus der Outputqueue.
Bei voller Queue wird die **neue Einreichung verworfen**, das bestehende
begrenzte Original bleibt für den vorhandenen Ausgabebesitzer erhalten.
Dies ist keine Garantie, stets die neueste Probe zu senden. Die unveränderte
Queue-Altersprüfung verwirft zu spät ausgelieferte Originale; weder Header-
noch Queuezeit wird aufgefrischt. Verbraucher-Frische und Faultflags bleiben.

**Abschlussnachweis:** Derselbe Teilrahmengegenfall besteht nach der Korrektur;
gezielt 0,0000575 s, im finalen Gesamtlauf 0,0000490 s. Zusätzlich wird geprüft,
dass Nutzdaten unverändert und die Queuezeit die der ersten Einreichung ist.
Der vorhandene Outputbesitzer und die separate Stale-Verwerfung bleiben erhalten.
Dieser Unterbefund ist softwareseitig geschlossen, **F7 insgesamt nicht**.

### 3.4 Nachgewiesene Ressourcenvererbung im Prüfstand

**Stelle:** `tools/simulation/ap06_closed_product.py::device_process`.
Frühes Pinning des Elternprozesses auf die Erfassungs-CPU wurde an die bereits
vorhandenen DDS-Ausgabeprozesse und nativen DDS-Threads vererbt. Die Rohbelege
zeigen Ausgabe und Erfassung gemeinsam auf CPU 4. Eine Diagnose mit den
bestehenden Ausgaben auf anderer CPU erreichte Bereitschaft; weitere Versuche
mit geänderter Verteilung scheiterten wieder. Kein statistischer Abschluss.

**Änderung:** Bestehende Arbeiter während der Initialisierung auf den anderen
verfügbaren Graph-/Sensor-CPUs erzeugen; den Besitzer und seine folgenden
Erfassungsthreads erst vor Timerbetrieb auf die Erfassungs-CPU pinnen.
Tatsächliche Affinitäten werden aufgezeichnet und in den Isolationsprüfungen
kontrolliert. Es entstehen keine zusätzlichen Prozesse. Im aktuellen
Fünf-CPU-Prüfstand: Erfassung `[4]`, bestehende DDS-Ausgaben `[0,1,2,3]`.
Diese Änderung betrifft die Simulation, keine ungeprüfte reale CPU-Konfiguration.

**Abschluss:** Die gemessene Vererbungskopplung ist beseitigt. Verbleibende
Quellenlücken trotz korrekter Affinitäten zeigen, dass dies keine vollständige
F7-Lösung ist. Auch ein versuchsweiser gemeinsamer Executor löste den Fehler
nicht und wurde nicht übernommen.

### 3.5 Offener Rest und überprüfbares Abschlusskriterium

Auf dem finalen Produkt scheitert der gezielte Supervisorfall `[False]` bereits
vor seiner Pauseninjektion: nur drei Radproben; Core-Fault
`encoder_luecke_nicht_ueberbrueckbar`, `last_attempt_gap_s=0,383609 s`,
`first_timing_rejection=null`, `published_count=3`. Der langsamste gleichzeitige
Pflanzensimulationsaufruf liegt im HWT-Thread; die vorliegenden Zeiten
identifizieren den blockierenden einzelnen nativen Aufruf noch nicht eindeutig.
Der finale breite Lauf besteht denselben Fall mit gesundem Quellenzustand und
maximalem empfangenem Quellstempelabstand 0,060561 s. Beide Resultate zählen.

Fehlender Nachweis: Welcher konkrete native Aufruf/Lockbesitzer oder
Schedulingentzug verhindert unter dem vollen Startgraphen die nächste gültige
Radprobe? Für einen weiteren beobachteten Fall mit gesunder Produktion, aber
0,302590 s empfangenem Radstempelabstand fehlt die eindeutige Zuordnung zu
Queue/DDS-Publikation oder Empfang. Keine Ursache aus einem anderen Lauf
auf diesen Fall übertragen.

Die nächste unterscheidende Messung erfasst im gleichen Nullkommando-Start
gleichzeitig native Aufrufgrenzen/Stacks, GIL-/Lockbesitzer und OS-
Schedulingzustand der Quellen-TIDs, korreliert sie mit FC03-Beginn/Ende,
Originalstempel, Queueübergabe, DDS-Publikation und Empfang bis zum ersten
Fehler. Das trennt Produzentenstillstand, tatsächliche Rechenarbeit,
Blockierung und spätere Auslieferung. Erforderlich für F7-Abschluss sind danach
reproduzierbare Vorher-/Nachherbelege unter der identifizierten Fehlerbedingung,
gesunde Quellen innerhalb 0,18/0,12 s und ursprüngliche Gesamtfälle; keine
neue Warteschleife darf den Fehler lediglich verdecken.

## 4. F8: die fünf beauftragten Regressionen

| Fall | Ursache und Korrektur | Abschluss |
|---|---|---|
| `test_public_view_does_not_require_private_ledger_epoch_expiry[ap06_a55_selection]` | Der reine Geometrie-/Historientest verbraucht abhängig von realer Rechen-/Wartezeit die optionale 2-s-Auswahlzeit. Kontrollierte Monotonic-Zeit ausschließlich in diesem Entscheidungstest; alle Geometrie-/Historienaussagen erhalten. | Reproduzierbarer Gegenfall und positiver Nachweis; separate echte Zeitprüfung bestanden. Unterbefund geschlossen. |
| `test_current_tf_received_without_executor_and_missing_tf_never_restamped` | Erstpublikation nicht synchronisiert; DDS-Discovery garantiert noch keine aktuelle veröffentlichte Probe. Zusätzlich liest der Helper nur 32 von tatsächlich 100 gepufferten TF-Nachrichten. Live-Source-Event vor der 350-ms-Prüfphase; Helper liest höchstens echte QoS-Tiefe. | Verzögerte echte Erstpublikation und echte stale/fresh-Queue vor/nach geprüft; alte Stempel werden später weiter abgelehnt. Unterbefund geschlossen. |
| `test_original_imu_writer_pause_is_isolated_from_encoder_acquisition[True]` | Reale Quellenlücke auch mit isolierter IMU-Ausgabe; in einem Lauf 0,304702 s bei Paarlesung 0,000362 s. CPU-Vererbung korrigiert, weitere Ursache nicht vollständig belegt. | Im finalen Gesamtlauf bestanden, nach früher negativem Lauf kein Stabilitätsabschluss. Offen. |
| `test_real_encoder_source_survives_supervisor_interpreter_pause[False]` | Reale Encoderlücken, zuletzt bereits vor Injektion 0,383609 s und terminaler Core-Fault. | Final gezielt negativ, danach breit positiv. Offen. |
| Derselbe Test `[True]` | Reproduzierter Empfangsstempelabstand 0,302590 s trotz durchgehend gesund empfangenem Basiszustand; anderer Lauf gesund. Erster Übergang noch nicht eindeutig bestimmt. | Final gezielt und breit positiv; der negative Auslieferungsbeleg ist nicht ursächlich geschlossen. Offen. |

### 4.1 A55: Entscheidung und tatsächliches Zeitbudget trennen

Die Tracefolge des ursprünglichen Tests erreicht die öffentliche Auswahlgrenze
nach etwa 2,00153 s; vorherige Verfeinerung etwa 1,39997 s, 57 Routenprüfungen.
Eine **wirkliche Pause von 2,05 s im ersten Routenaufruf** reproduziert den
Fehlschlag: öffentliche Auswahl nach 2,09503 s, keine begrenzt bewiesene
öffentliche Beobachtung, ursprüngliches Gesamtbudget unverändert 5 s.

Die Testkorrektur ersetzt nur die `time`-Referenz des Laufzeitmoduls während
der reinen Geometrie-/Historienentscheidung; `thread_time` bleibt echt.
Produktion und globale ROS-/Sensorzeit werden nicht verändert.
Ein zusätzlicher Test berechnet dieselbe A55-Grenzsituation mit wirklicher
2,05-s-Pause: optionales Budget genau 2 s, Rest null, keine erfundene
Beobachtungsfreigabe; verbleibende Kandidaten benötigen einen nativen Plan.
Die tatsächliche Verarbeitung muss weiterhin im unveränderten 5-s-Budget
liegen. Gegenfalltrace und reale Zeitprüfung sind separate Nachweise.

### 4.2 TF: wartende aktuelle Originale auch erreichen

Der Queuegegenfall stellt 40 echte TF-Nachrichten bereit, lässt ihre
Originalstempel 0,3 s altern und sendet fünf frische Paare. Ohne Consumer-
Executor bleibt die alte 32er-Prüfung im veralteten Präfix und verweigert
Freigabe. Die Korrektur erreicht die tatsächlich gepufferten frischen
Originale; 0,25 s später sind dieselben Stempel wieder unzulässig.

Ein zweiter Gegenfall verzögert nur die wirkliche erste Publikation um
0,5 s. Der bisherige Test begann seine 0,35-s-Phase trotzdem sofort und
scheitert; der korrigierte Test wartet mit ursprünglichem 3-s-Setupbudget
auf eine tatsächlich veröffentlichte aktuelle Probe. Danach gelten dieselben
0,35 s ohne Consumer-Executor und dieselbe 0,2-s-Frische. Kein Sensorstempel
wird aktualisiert, keine Missionsfrist verlängert.

Der Helper wird von Bewegungsdiagnostik **und** Missionsgeschwindigkeitsgate
verwendet. Die Änderung ist deshalb produktwirksam und wurde im separaten
Install sowie mit echten ROS-/TF-Nachrichten geprüft.

## 5. Gesamte Softwareprüfung, einschließlich negativer Läufe

| Lauf | Produkt / Umfang | Ergebnis |
|---|---|---|
| Ausgangsaudit | `900ce5d`, bisheriger voller Umfang | 3.128 bestanden, 5 fehlgeschlagen |
| Audit-Wiederholung ohne Produktänderung | dieselben fünf Fälle | 5 bestanden; kein Fixnachweis |
| Früher Diagnose-Testlauf | Altes Install `900ce5d`, geänderte Test-/Prüftreiberquellen; 15 Auswahl-/Gerätefälle | 14 bestanden, 1 fehlgeschlagen (`[True]`, Radstempelabstand 0,302590 s); kein finaler Produktlauf |
| Erster neu gebauter gezielter Lauf | `6bbec19`, 91 Fälle | 89 bestanden, 2 fehlgeschlagen (IMU isoliert, Supervisor `[False]`) |
| Erster neuer voller Lauf | `6bbec19`, 3.135 Fälle | 3.134 bestanden, 1 fehlgeschlagen; die fünf F8-Fälle bestanden |
| Final gezielt | `cf010a0`, 99 Fälle | 98 bestanden, 1 fehlgeschlagen (Supervisor `[False]`), 79,38 s |
| Final voller bisheriger Umfang mit neuen Gegenfällen | `cf010a0`, 13 Produkt-Testverzeichnisse und `tools/simulation` | **3.136 bestanden, 0 Fehler, 0 Skips**, 409,49 s |

Teilumfänge überlappen; Zahlen nicht addieren. Die fünf F8-Fälle bestanden im
finalen vollen Lauf, doch das schließt die drei Gerätezeitbefunde nicht.
Rohzustände, Radquellstempel, Executorzeiten und tatsächlich vererbte
Ausgabeaffinitäten wurden gesichert. Assertions der drei Gerätefälle bleiben
unverändert; keine zusätzlichen Setupfristen, Domain-Ausweichstrategie,
Testdeaktivierung oder Testskip.

Der erste Zwischen-Gesamtlauf behält stdout und JUnit, sein temporäres
Geräteverzeichnis wurde beim finalen Lauf wiederverwendet. Ein vollständiger
eigener Rohquellenbeleg dieses Zwischenlaufs ist deshalb nicht verfügbar.
Die finalen gezielten und breiten Läufe haben getrennte erhaltene Rohverzeichnisse.
Bei frühen Diagnosevarianten fehlen zudem vollständige Snapshots aller damaligen
externen Messskripte. Sie sind Ursachenhinweise; der letzte Nullkommandobeleg
bindet dagegen Produkt, Install und vollständige Messskripthashes ausdrücklich.

**Neuer unabhängiger Fehlschlag außerhalb F7/F8:**
`test_metric_selection_components.py::test_recorded_public_selection_keeps_capped_history_and_finds_native_query`,
auf gespeicherter B207-Auswahlsituation im ersten neuen Gesamtlauf:
`ValueError` am unveränderten 5-s-Verarbeitungsbudget. Test und Laufzeitquelle
wurden nicht geändert. Im finalen Lauf besteht er. Ursache, Zusammenhang mit
F7/F8 und stabile Budgeterfüllung sind damit nicht bewiesen; gesonderter Befund,
keine stillschweigende weitere Explorerkorrektur.

Ein anfänglicher Testproxy ohne `thread_time` verursachte drei Setup-
Fehlschläge; die Schnittstelle wurde ergänzt, Zwischenlog/JUnit bleiben
erhalten. Das war ein eigener Testimplementierungsfehler, kein Sensorbefund.
Der erste Gesamtfall-Aufruf scheiterte wegen vorher angelegter Zielverzeichnisse;
auch dieser Skriptfehler ist gesichert und zählt nicht als Gesamtmission.

## 6. Unveränderte ursprüngliche Gesamtfälle

**A/B/C: 0/3 qualifiziert; Cancel/HOLD: 0/2 qualifiziert.** Ergebnisdateien
ausgewertet, alle fünf `passed=false`. Alle ursprünglichen Driverläufe haben
Exitcode 1; der äußere Serienwrapper beendet sich nach dem Sichern aller Fälle
mit 0. Der Wrappercode ist ausdrücklich kein Missionserfolg.

| Ursprünglicher Fall | Tatsächlicher Verlauf | Ergebnis / fehlendes Kriterium |
|---|---|---|
| A, `door68_start_a` | Initiale echte SLAM-Karte vorhanden; keine Missionsfreigabe | `real scope and HWT readiness`; erste Encoderlücke 0,584591 s |
| B, `door68_start_b` | Startscan 2,646683 rad / 151,64°; null Ankünfte/Beobachtungen | `hwt_terminal`; Radlücke 0,553592 s; Referenzbeobachtung 61,52 % statt 95 % |
| C, `door80_start_c` | Startscan 0,769563 rad / 44,09°; null Ankünfte/Beobachtungen | `hwt_terminal`; Radlücke 0,407647 s und rohe HWT-Probe 0,349895 s alt |
| `cancel` | Scan 0,458544 rad / 26,27°; Cancel-Injektion noch nicht erreicht | `hwt_terminal`; Paarlesung 0,563209 s; keine Cancel-Stoppqualifikation |
| `gyro_hold` | Initiale Karte vorhanden; keine Missionsfreigabe oder Injektion | `real scope and HWT readiness`; erste Encoderlücke 0,575237 s; keine HOLD-Stoppqualifikation |

B/C/Cancel kommen tatsächlich bis zur Drehung, im Modell aber jeweils weniger
als 0,3 mm translatorische Strecke; kein autonomes Fahrziel und keine
Türpassage. Das unveränderte Injektionskriterium verlangt über 0,02 m Fahrt und
lineare Geschwindigkeit über 0,005 m/s. Es wurde nicht um eine reine Drehung
erweitert. Ein natürlicher HOLD infolge fehlerhafter Daten ersetzt diese
gezielte Injektion nicht. A/HOLD bleiben bei Nullkommandos.

Bei B weist die Fusion als ersten Grund `wheel_missing_stale_or_invalid` aus;
bei C/Cancel zunächst `raw_missing_stale_or_invalid`, mit zusätzlichem ungültigem
Radpfad. F1–F5 erhalten Scanabbruch, ursprünglichen HOLD und terminalen Grund
getrennt. B/C/Cancel beenden Kinder und alle vier Kommandokanäle mit null.
Kartenwachstum und korrekte TF-Besitzer sind Teilbelege; die Gesamtkriterien
bleiben dennoch negativ. Vollständige Kriterienauswertung und Original-
Kompressionshashprüfung stehen in `evaluated-results.json`.

Originalmanifest und Welten sind bytegleich. Start 60 s, Mission 900 s,
Ziel 150 s, Cancel 3 s, Halt 1 s; native Mastmaske mit 2.160 Strahlen und
endliche VL53/OAK-Modelle. Kein Ideal-LiDAR, keine Profilierungs-/Geometrie-
Ausnahme und kein manuelles Nav2-Ziel. Quell-/Installbindung wird vor dem
Serienlauf erneut geprüft; Ergebnisdateien, Ereignisse und Kriterien zählen.

Erforderlich für A/B/C bleiben tatsächlicher Missionserfolg, mindestens drei
autonome Ankünfte und Beobachtungen, beide Türen mit freiem Heck, beobachteter
rechter Raum, Kartenwachstum nach Bewegung, mindestens 95 % Referenzbeobachtung,
maximal 0,1 m Wandfehler, keine Kollision/offene Aufgabe, korrekte TF-Besitzer,
maximal ein Navigationskind und abschließend null Kommandos.

**HOLD-Stopp und Wiederaufnahme sind getrennt.** `gyro_hold` qualifiziert nur
die Haltreaktion; `hold_resume_qualified` bleibt im ursprünglichen Driver
`false`. Weder ein Stoppfall noch Softwaretests der Beobachtungsfortsetzung
beweisen vollständige Wiederaufnahme der ganzen Mission oder einen realen
Hardwarelauf.

## 7. Korrekturcommits und Rückfall

| Commit | Grund / Umfang | Rückfall im separaten Kandidaten |
|---|---|---|
| `4ea2486305ef303fb4877068a11a0bd2a65444b1` | Echte TF-Queuetiefe statt 32er-Präfix; Live-Source-Test synchronisieren | Diesen Commit revertieren und `robot_navigation` separat neu bauen; dokumentierter TF-Empfangsfehler kehrt zurück. |
| `6233bb5bcd1eaab7bcd9d8c39ea1e115759e115d` | A55-Entscheidung mit kontrollierter Zeit, echter Budgetgegenfall daneben | Testcommit revertieren; zeitabhängige Entscheidungsaussage kehrt zurück, Produktionsruntime unverändert. |
| `6bbec19fe7506880efb22ba69f48be09c5ccd42e` | Bestehende passive Arbeiter von Erfassungs-CPU entkoppeln und Affinitäten/Rohzustände belegen | Diesen Prüfstandcommit revertieren; frühere CPU-Kopplung kehrt zurück. |
| `cf010a03c96ad981516b52d96f5c21dda78c4369` | Kein Teilrahmenempfang im Sensorproduzenten; echte Pipe-/Originalzeitprüfung | Commit revertieren und `base_hardware` separat neu bauen; bekannte Blockierungsgefahr kehrt zurück. |

Rückfall verändert weder F1–F6 noch den erhaltenen Bestandsinstall.
Keine Live-Installumschaltung; vor einem späteren Zielsystemwechsel bestätigter
Halt und Ende eigener Kandidatenprozesse. Kein neuer Push/Merge oder
Jetsontransfer erfolgt. Commitnachrichten enthalten Gründe und Rückfallwege.
Frühere nur um Rückfalltexte ergänzte Commitidentitäten sind mit identischen
Bäumen in `commit-message-lineage.json` dokumentiert.

## 8. Nachweise und Reproduktion

[Maschinenlesbarer Ergebnisbeleg](evidence/ap06-f7-f8-20261011.json).
Die vollständigen lokalen Rohbelege liegen außerhalb Git unter
`/workspace/ap06-audit-results/f7-f8-evidence/`; Lieferung unter
`/workspace/f7-f8-results/` mit Bundle, Reviewpatch, Bericht, Roharchiv,
Build-/Install-/Konfigurationsbindung und SHA256SUMS. Nur synthetische
Prüfwelten, keine realen Wohnungskarten/Bilder/Bags eingecheckt.

Wesentliche Einstiege im Roharchiv:

- `baseline-source.json`, `baseline-artifacts.json`, `original-audit-files/`,
  `original-test-artifacts/`, `original-whole-12de37e/` und deren Bindungsdatei
  sichern Originalstand, Audit-Logs/JUnit und die fünf alten Gesamtrohbelege.
- `source-identity.json`, `product-source-binding-final-regressions.json`,
  `native-prefix-bindings.json`, `python-packages.json`, `preserved-contracts.json`
  binden Produkt, tatsächlich geladene Module, Unterbau und unveränderte Verträge.
- `installed-files-sha256.json`, `system-packages.tsv` und `container-binding.txt`
  erfassen alle 897 Produkt- und 4.746 Unterbau-Install-Dateien einschließlich
  vorhandener Bytecodes, die Systempaketversionen und das Containerimage.
- `build.sh`/`build.log`, `rebuild-base.sh`/`rebuild-base.log` sowie separate
  Build-/Install-/Logverzeichnisse dokumentieren den Build.
- `tf-backlog-baseline.*`, `tf-delay-baseline.xml`, `tf-delay-candidate.xml`,
  `tf_startup_pause.py` belegen echte TF-Gegenfälle.
- `selection-route-preempted-baseline.json`,
  `selection-route-preempted-candidate.json`, `selection_probe.py` belegen die
  gleiche A55-Fehlerbedingung mit wirklicher Pause vor/nach Testkorrektur.
- `partial-write-baseline.*`,
  `focused-final-device-raw/test_full_queue_with_partial_f0/partial-write.json`
  und derselbe Fall in `full-device-raw/` belegen die Teilrahmenblockierung.
- `focused-final.log`/`.xml`, `focused-final-device-raw/`,
  `full-regressions.log`/`.xml`, `full-device-raw/` enthalten sämtliche finalen
  Regressionsergebnisse; frühere Läufe sind mit eigenen Namen erhalten.
- `startup-*/`, jeweilige Shellskripte und `*-scheduling.jsonl` enthalten
  Nullkommandodiagnosen. Nicht übernommene Diagnosen sind ausdrücklich solche.
- `whole-cases.sh`, `whole-cases.log`, `whole/*/result.json`, native Parameter,
  gestartete Befehle, Quellen-/Executorlogs und vollständige Ereignisjournale
  enthalten die ursprünglichen Gesamtfälle. `events.jsonl.gz` ist verlustfreie
  Rohkompression mit Originalhash in `.meta.json`.

Reproduktion erfolgt im isolierten Humble-Prüfstand mit `/audit`-Mount,
gepinntem nativen Unterbau und separat gebautem Produktinstall. Vor jeder
Auswertung Sourcebinder ausführen; nach Dokumentationsänderungen den getesteten
Produktcommit in einem sauberen Worktree verwenden. Die Shellskripte nennen
die exakten Pfade, Optionen und Domänen. `full-regressions.sh` bildet den
vollständigen bisherigen Umfang ab, `whole-cases.sh` die fünf ursprünglichen
Gesamtfälle. Ein Driver-Exitcode allein reicht für keine Abnahme.

## 9. Grenzen vor dem Jetson

Softwareteilbelege ersetzen keinen zuverlässigen Nullkommando-Start und keine
Gesamtfahrt. Die offenen Quellen-/Auslieferungsursachen müssen gerätefrei
weiter eingegrenzt werden. Ein späterer ARM64-Build ist eine eigene
Portierungsprüfung; reale Sensorzeiten, USB/RS485/I2C, TF-Frames, Brems-
und Sichtwirkung, Recorderempfang vor Bewegung und Aufzeichnung bis zum
bestätigten Halt bleiben vollständig offen.

Das Simulationsprofil `rpp_rollout` und dessen CPU-Zuordnung werden nicht auf
den realen Standard `conservative` übertragen. Keine elektrische Sperrstellung
oder neue reale Fahrfreigabe wird aus diesen Ergebnissen abgeleitet. Genau
ein aktueller nächster Schritt steht ausschließlich im [STATUS](STATUS.md).
