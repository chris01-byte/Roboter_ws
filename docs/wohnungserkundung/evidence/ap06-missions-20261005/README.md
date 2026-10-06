# AP-06 – Reparatur der vollständigen Missionen, Zwischenstand

Nutzerauftrag: Ursachen der drei negativen Gesamtmissionen beheben und dieselben
fünf Produktmanifestfälle erneut prüfen. MASTERPLAN v1.3, Welt, Quellenfristen,
Scope, Kontur, unbekannter Außenraum, Aufgaben-/Gesamtbudgets und Abnahmekriterien
bleiben erhalten. **Noch keine drei positiven Gesamtmissionen und kein
vollständiger AP-06-Abschluss.** Die Arbeit wird fortgesetzt.

## Nachgewiesene zusätzliche Reparaturen

* Quellen und physisches Modell laufen im eigenen Interpreter: langsame
  Supervisor-/Geometriearbeit blockiert nicht deren GIL. Originalquellen und
  echte Stempel bleiben erhalten; keine nachträglich gefüllten Messungen.
* Ein echter eigener DDS-Test reproduziert das ausbleibende `/plan` bei
  wartenden Geometriecallbacks; Callbackgruppen lassen den tatsächlichen Plan
  zustellen. Frische endet weiterhin bei tatsächlichem Producerstopp.
* Physische Encoderbindung wird nur für private Anfangsabfahrt benötigt.
  Bei vollständig gewöhnlicher bekannter aktueller Kontur bleibt die reguläre
  Live-Quellenprüfung maßgeblich. Echte Rückfahrt/Unknown bleiben gesperrt.
* Gate und Explorer beziehen die tatsächliche jüngste Radprobe aus ihrem
  eigenen DDS-Leser. Unabhängiges Gate-HOLD löst auch bei gesundem Explorer
  dessen ursprünglichen HOLD-/Abbruch-/ACK-Ablauf aus.
* Eine alte verworfene Eigenroute verhindert keinen noch ausstehenden echten
  ComputePath-Versuch. Vor Bewegung bleibt der volle tatsächliche Nav2-Pfad
  verpflichtend. Der Vollscan behält auch die 2-cm-Trackingreserve.
* Native `SimpleGoalChecker`-Gegenprobe: `stateful: true` akzeptiert nach
  erfüllter Position und anschließender Drehung 16 cm Abstand. `false` lehnt
  diesen Zustand ab und akzeptiert 14 cm mit passender Orientierung.
  **15 cm / 0,4 rad unverändert**; der qualifizierte Controllervertrag prüft
  zusätzlich den tatsächlichen Boolparameter.
* Am stehenden terminalen Kind darf ein kurzzeitig unpassendes VL53-Triplet
  innerhalb des ursprünglichen Beobachtungsfensters zusammenkommen.
  Tatsächliche passende Stempel sind weiterhin für Beobachtung erforderlich.
  Dauerhaft unpassendes Triplet liefert keinen Gewinn, defekter Encoder
  bleibt terminal. Ein ablehnender Snapshot wird zusätzlich erhalten.
* Am tatsächlichen C32-Restbestand scheitert die nächstgelegene Anfahrpose an
  ihrer Ausrichtung. Der gleiche lokale Suchbereich enthält eine sichere
  alternative Zielpose mit Sicht. Diese wird ausschließlich als
  **Nav2-Planungsvorschlag** behandelt: die unsichere Eigenverbindung bleibt
  verworfen, der echte Native-Pfad muss vor Bewegung vollständig bestehen.

* Das einmalige Anfangsinventar erhält jetzt auch ursprüngliche unbekannte
  Zellen, die die stationäre Eigenkörpermaske vorübergehend erlaubte. Deren
  Entzug erzeugt keine neue Anfangserfassung. Tatsächlicher TF-Bezug projiziert
  den körpergebundenen Bestand auch bei stabilem Kartenraster; reine TF-
  Korrektur ist keine Beobachtung. Echte beobachtete Teilfläche bleibt entzogen.
* Native Vorwärtsweiterfahrt wird vor regulären Beobachtungszielen rein lesend
  geprüft; tatsächliche RPP-Endorientierung statt idealem Wunschheading.
  Begrenzte erste Beobachtung behält ihren bisherigen vollständigen Egress-
  Beweis. Lokale Zielsuche bevorzugt bekannte Wendebereiche, falls vollständig
  beweisbar; ursprünglicher Radius und Native-Freigabe unverändert.
* Rein lesende Vorschlagsablehnung vor jedem Dispatch verbraucht weiterhin
  Aufgaben-/Gesamtversuch, aber keinen Fahrfehler. Ein tatsächlich gestartetes
  Kind behält seine Fahrversuchsbindung über Kartenjoin und erneute Planung.
  Raw-erreichbare Restarbeit verhindert weiterhin false-positive Completion.

## Prüfnachweise und ihre Grenzen

Native Goalchecker: Rot/Grün mit dem wirklich installierten C++-Plugin.
VL53-Beobachtung: zwei tatsächliche alte Produktfehler, danach 70 betroffene
Tests grün. Alternative Zielpose: alter Produktstand ohne Kandidat, danach
73 betroffene Tests grün, einschließlich Ablehnung der unsicheren Verbindung.
Zwölfpaketbuild des Kandidaten `3e151fa`: 6,99 s. Neun native Bewegungsfälle des früheren Kandidaten in `native-components/`
grün; diese sind Komponentenfälle, keine ganzen autonomen Missionen.

Die vollständige direkte Prüfung des Kandidaten besteht **1.932 Tests**;
reguläre colcon-Prüfung: **1.922 Tests, 0 Fehler, 0 Fehlschläge, 0 Skipped**.
Native vollständige Kommandos/Logs: `native-final-v7-*`. Testmengen überlappen.
Ubuntu 22.04 / Humble / amd64 / Python 3.10 / rclpy 3.3.17; keine ARM-Abnahme.
`installed-identity-3e151fa.json` bindet die tatsächlich importierbaren Module
an den geprüften Ausführungscopy; `source-identity-3e151fa.json` an den Gitstand.

Die roten Zwischenstände bleiben erhalten: v4 enthält eine fehlende Costmap-
Variablenbindung und einen der korrigierten Inventarführung widersprechenden
Alt-Test. v5/v6 sowie zwei Gate-Testisolationen reproduzieren Rad-DDS-Alter über
180 ms. Der passive Gate-Executor gibt nun nach begrenztem `spin_once` 1 ms
CPU frei; aktiver serieller Pfad und Quellenfristen unverändert. Echte Gate-
DDS-Regressionen verwenden frische Prozesse und einen unabhängigen synthetischen
Messproduzenten. Positivfall und absichtlicher echter Producerstopp bestehen in
vollständiger direkter UND colcon-Prüfung. Ein früherer stateless-Geometrietest
überschritt unter paralleler Diagnostik sein Fixturebudget; dessen 30-s-
Testbudget betrifft keine produktive 5-s-Live-Auswahl.

Der erste native Sammelversuch im Container `ap03-current` konnte wegen
fehlender `libmap_msgs__rosidl_typesupport_cpp.so` nicht starten und wurde
beendet. Die neun Originalfälle wurden im vollständig eingerichteten
`ap03-nav2` geprüft. Daraus folgt keine Zielsystem-/ARM-/Applequalifikation.

## Echte Gesamtläufe bleiben getrennt negativ

| Lauf | Ankünfte / Beobachtungen | Originaler Abschluss |
| --- | --- | --- |
| C29 | 3 / 3 | Budget erschöpft; natives viertes SUCCESS außerhalb Positionsgrenze |
| C30 | 4 / 3 | Stationäre Beobachtung abgebrochen; Goalchecker nun innerhalb Grenze |
| C31 | 0 / 0 | Aktueller Kontur-/Anfangsflächenbeweis verworfen; ursprüngliches Fehlerbudget erschöpft |
| C32 Diagnose | 5 / 5 | 4,61 m, ganze Passage, 96,37 % Boden; Restfrontier bleibt offen |
| C33 | 4 / 3 | 900-s-Grenze; Ankunft in engem Bereich ohne ausführbare Vorwärtsweiterfahrt |
| C34 | 0 / 0 | Vor Missionsbeginn: 386,6-ms-Encodergap; parallele Diagnostik aufgezeichnet, keine bewiesene alleinige Ursache |
| C35 | 1 / 1 | Weiterfahrtsbeweis am Start zu früh gefordert; nachfolgende Auswahl überschreitet 5-s-Grenze |
| C36 | 4 / 4 | 3,69 m, beide Folgebereiche, 96,92 % Boden; drei Vorschlagsablehnungen wurden als Fahrfehler gezählt |
| C37 | 0 / 0 | 900-s-Grenze; nach 21,5 cm fehlender ursprünglicher Eigenkörperbestand. Nach echtem Dispatch erneute Planung fälschlich ohne Fahrfehler gezählt |
| C38 | 4 / 3 | 3,28 m, 93,20 % Boden, ganze erste Passage; weitere Auswahl >5 s. Nominaler Rückweg am vierten Ziel ignoriert π-Drehrichtungswechsel innerhalb ±0,05 rad |

C32 verwendet den ausdrücklich als Diagnose markierten passiven
Geometrie-Hook und ist **nicht manifestkompatibel**. Auch ein erfolgreicher
C32-Abschluss wäre kein Gesamtpositivnachweis. Sein finaler Originalraster,
die tatsächlich akzeptierte letzte Pose und die gespeicherte Policy bilden
den Regressionseingang `ap06_remaining_frontier.*`; sie sind kein gleichzeitig
aufgenommener Fehlersnapshot. Die finite Winkelabdeckung im Geometrietest
stammt vom echten synthetischen C27-Scan und ist kein C32-Beobachtungsreceipt.

Die Originalereignisse und alle vorherigen Negativläufe bleiben lokal unter
`/workspace/scratch/ap06-missions-20261005` erhalten. Fertige große JSONL-Dateien
sind verlustfrei gzip-komprimiert; `compressed-events.jsonl` dokumentiert
ursprüngliche SHA-256, Größen und geprüfte Dekompression. Kein laufendes
Ereignisfile wird komprimiert. Diese Daten enthalten ausschließlich die
deklarierte synthetische Welt, keine realen Wohnungsdaten.

Kopierte Logs/Originalresultate und `copied-evidence-sha256.json` gehören zu
diesem Zwischenstand. `source-identity-intermediate.json` bleibt ein historischer Zwischenstand;
neue Identitätsdateien überschreiben ihn nicht. Keine Identitätsdatei ist
allein ein Gesamtpositivnachweis.
Die nächste Arbeit bleibt der volle Produktnachweis A/B/C plus Cancel/HOLD
und die abschließende Regression, ohne Hardwarefahrt oder Deployment.


## Kandidat ec96479 vor C39 – zusätzlicher Rot/Grün-Nachweis

`c38-heading-branch-before.log`: tatsächlich installierter alter Stand akzeptiert
auf aufgezeichneten C38-Nav2-Pfaden einen zukünftigen Rückweg, der schon bei
−0,05 rad Orientierung innerhalb der zugesagten Bandbreite scheitert. Aktuelle
Ankunft liegt innerhalb der Bandbreite. Endraster sind später aufgezeichnet,
keine gleichzeitig erfassten Fehlereingaben. Neuer voller öffentlicher
RPP-Beweis beider Bandränder verwirft ihn; keine neue Unknown-/Konturreserve.

`c36-query-budget-before-v6.log` / `c38-bounded-regressions-v3.log`: Original-
Kandidatenentscheidung aus `3e151fa` auf echten C36-Endrastern und ihrer späteren
Standpose, finite Winkelabdeckung aus C38 als ausdrücklicher geometrischer
Komponenteneingang (kein C36-Beobachtungsreceipt). Tatsächlicher Detektor liefert
alle unveränderten Kandidaten, für den Test in umgekehrter Eingangsreihenfolge;
synthetischer Verarbeitungsclock macht unnötige Arbeit nach der ersten zulässigen
Planungsanfrage sichtbar. Alter Stand überschreitet 5 s, neuer bleibt bei 4,9 s
und verlangt weiter die reale Native-Freigabe vor jeder Bewegung. Kein Fake-
Nav2-/Wholemission-Positivnachweis. Zwei zusätzliche Policytests sichern neue
räumliche Planungsanfrage nach ursprünglichem Cooldown, unveränderte ID und drei
Versuche; reale Fahrfehler und erledigte Aufgaben bleiben gesperrt.

Gezielte neue Gruppe: 9 bestanden; betroffene Policy/Fortschrittsgruppe: 128
bestanden (Überlappung). Vollständige neue direkte Suite: 1.936 bestanden. Neue
colcon- und Gesamtmissionen laufen; `source-identity-ec96479.json` erhält ihre
Quellbindung. V7 bleibt historischer vollständiger 1.932/1.922-Testnachweis.

## Weiterer belegter Stand: Kandidat ec96479

Zwölfpaketbuild erfolgreich, **1.936 direkte Tests bestanden (55,56 s)**;
reguläre **1.926 colcon-Tests: null Fehler, Fehlschläge oder Skips**. Prüfmengen
überlappen. Originale `native-final-v8-*` liegen hier. Diese Komponentenprüfung
ist keine positive Gesamtmission.

C39 ist manifestkonform und scheitert **vor dem Missionsstart** an der echten
Scope-/HWT-Bereitschaft. Im unabhängigen Quellenprozess sind drei zeitgleiche
Executorpausen von etwa 330 ms gemessen; der tatsächliche Encoderabstand beträgt
326,55 ms. Die ursprüngliche Kontinuitätsprüfung sperrt korrekt. Weder längere
CPU-Rechenarbeit noch ein aufgezeichneter GC erklären die Pause. Eine konkrete
Scheduler-/DDS-/SDK-Ursache ist damit noch nicht bewiesen. Originalresultat und
Quellenlatenzen unter `mission-c-v39/`.

Die neuere vorhandene ROS-Prüfumgebung (rclpy 3.3.22 / rclcpp 16.0.21) wird
separat für native Komponenten qualifiziert. Fehlende Map-Interfaces wurden
aus unverändertem upstream map_msgs 2.1.0 gebaut; ausschließlich fehlende
Laufzeitbibliotheken werden aus der vorhandenen Ubuntu-22.04-Prüfumgebung
wiederverwendet. Bestehende Nav2-/Support-Overlays sind gegen den älteren SDK
gebaut. Kein neuer Zielsystembuild oder erfolgreicher Gesamtlauf daraus abgeleitet.
Die ersten beiden Versuche scheiterten an fehlenden dynamischen Bibliotheken;
diese negativen Originale bleiben lokal erhalten. Gesamtwiederholung erst
nach erfolgreicher nativer Prüfung. **Weiterhin 0/3 Gesamtpositivnachweise.**

Die anschließende neuere native Komponentenprüfung besteht **alle neun** originalen Bewegungs-/Schutzfälle (`current-native-components-v3-ec96479-results.json`). Die importierbaren installierten Kernmodule sind zum Softwarecommit bytegleich (`installed-identity-ec96479.json`). Der erste vollständige Lauf dort ist C40; sein Ergebnis ist noch offen.

## C40: native Umwege statt direkter Rückverbindung

C40 beginnt in der neueren Prüfumgebung tatsächlich, erreicht drei Ankünfte/
Beobachtungen und beide Türen mit dem ganzen Körper. 79,53 % Referenzboden;
0 tatsächliche Fahrzielfehler, sechs verworfene Planungsvorschläge, abschließend
5-s-Kandidatenbudget erschöpft. **Negativ**, Original unter `mission-c-v40/`.

Im späteren tatsächlichen Roh-/Costmap-Raster besteht der native Anfahrtsweg
zur Südaufgabe. Die ursprüngliche Zukunftsprüfung verwirft dennoch: eine
direkte Rückverbindung schneidet Hindernis/Unknown. Mit drei echten CPP-NavFn-
Abfragen (Rückversuch, Vorwärtsrefugium, Umweg-Rückkehr) bestehen beide wirklichen
Pfade einschließlich nominaler/±0,05-rad-Anfangsorientierung vollständig die
unveränderte öffentliche Konturprüfung. Zweite Originalgeometrie C33 bestätigt
den Befund. C33s früheres negatives Süd-Komponentenergebnis war somit eine
falsche Sackgassenklassifikation durch denselben Direktfilter; dessen alte
Originale bleiben erhalten. C33-/C38-Nord-Sackgassen bleiben negativ.

**Reparatur c2e9c00:** der Direkt-Rückweg ist keine Vorbedingung mehr. Echte
Native-Vorwärts-/Rückwege, Kontur, Unknown, Quellen, zukünftige Heading-Band-
Prüfung, 5 s und tatsächliche neue Navigation vor Bewegung bleiben notwendig.
Rotbeleg gegen ec96479: `c40-native-detour-before.log`; Grün nach Reparatur:
69 gezielte Tests in `c40-detour-after-v3.log`. Zwei vorherige Regressionversuche
zeigen noch unvollständigen alten Actionfixturebestand bzw. fehlenden Test-
Defaultwert; erhalten, mit tatsächlich neu aufgenommenen Native-Pfaden/
produktidentischem Default korrigiert. Diese Raster-/Pfadfälle sind geometrische
Komponenten, keine gleichzeitigen Fehlerinputs, gemessene Beobachtung oder
Gesamtpositivabnahme. Volle neuere Build-/Tests laufen vor C41.

Kandidat c2e9c00 in neuerer Umgebung: **Zwölfpaketbuild 45,4 s**, einschließlich erneut kompiliertem Produkt-BT; **1.937 direkte Tests (56,54 s)** und **1.927 colcon-Tests (null Fehler/Skips, 1 min)**. Originale `current-final-v3-*` und Modulidentität hier; Native-/Support-Bibliotheken bleiben als ältere wiederverwendete Overlays ausgewiesen. C41 ist gestarteter, noch offener Gesamtlauf.

## C41: gebundener Geometrieprüfstand verfällt während Bearbeitung

C41 negativ nach 14,5 cm: `start_motion_wheel_stale_after_processing`; null
Ankünfte/Beobachtungen. Keine entsprechende >100-ms-Quellenexecutorpause
aufgezeichnet; letzter Betriebssnapshot sicher/HEALTHY. Das beweist keine
allgemeine Scheduler-/DDS-Ursache, sondern den konkreten verfallenen gebundenen
Input. Terminal alle Handles weg und vier Befehlsstufen null; Original erhalten.

**e152228:** Dieser spezifische Bearbeitungsablauf bleibt ein ablehnender Input.
Nach terminalem Kind/echtem bestätigtem Halt darf innerhalb des bestehenden
2-s-Neuprüfungsfensters ein vollständig neu gelesener, frischer Input den
weiterbestehenden Task neu planen. Echte fehlende/alte/ungültige Radquellen
sowie HOLD/Context/Cancel/Fristen bleiben hart. Bestehende Aufgabe, laufende
Task-/Gesamtfristen, Originalversuchslimit und Zähler unverändert; keine Stempel
aktualisiert, alte Kontur weiterverwendet oder Parent neu gestartet. Journal
unterscheidet `geometry_snapshot_revalidate` vom Kartenjoin.

Sechs Parent-Regressionen mit tatsächlicher Policy/Korrelator-/Pfadlogik und
injektierter spezifischer Inputablehnung: frische Wiederprüfung, echte
Quellenlücke, dauerhafter Bearbeitungsablauf, begrenzte Tasktries, Cancel und
Gesamtfrist. Drei relevante Fälle rot gegen c2e9c00; anschließend **28** gezielte
Tests grün. Actionpeers/Fehlerinjektion sind Komponenten, keine Gesamtabnahme.
Volle Build-/Tests vor neuer Gesamtmission laufen.

## Vollprüfung v4: zusätzliche Quellen-GIL-Gegenprobe

V4-Build erfolgreich (7,05 s), direkte Prüfung **1 fehlgeschlagen / 1.942 grün**
(67,67 s). Kein colcon nach der negativen direkten Prüfung gestartet. Originaler
Pytestfehler erhalten. Der reale Encoder-Isolationstest erhält nach absichtlichem
400-ms-Supervisor-GIL-Halt keine weiteren 30 Radproben innerhalb 10 s. Seine
Quellen-Timer zeigen 179,31 ms Sensorexecutor mit 174,94 ms eigenem CPU-Verbrauch;
Rad-/Gyrothreads im selben Interpreter bekommen nahezu keine CPU. Das ist ein
anderer konkret gemessener Verlauf als C39s Pause mit wenig CPU. Die inzwischen
von Pytest automatisch gelöschten temporären JSONs wurden zuvor per Tool gelesen;
`current-final-v4-source-negative/captured-timer-output.txt` ist ausdrücklich eine
Transkription dieses Befunds, kein archiviertes Original oder SHA-Nachweis.

**16cbe5c:** finite Laser-/VL53-/OAK-Berechnung eigener gespawnter Prozess;
100-Hz-Pflanze und originale Register-/HWT-Proben bleiben im Quellenprozess.
Atomare Modellpose mit tatsächlichem Erfassungszeitpunkt; jedes ausgegebene
Sensortriplet hält diesen Stempel auch bei verzögerter Berechnung. Keine neue
Frame-/Heartbeatausgabe aus >30 ms altem Modellsnapshot. Welt, endliche Strahlen,
Originalquellen/Takt/Fristen/Body/Scope/Abnahme bleiben erhalten.

Echter DDS-Test nun auch mit separatem 250-ms-Sensor-GIL-Halt: **zwei Fälle grün**
(5,23 s). Weitere DDS-Gegenprobe prüft tatsächliche Originalstempel, Ausbleiben
bei eingefrorener Modellquelle und Wiederkehr erst mit frischen Originalinputs:
**drei Fälle grün** (6,85 s). 11 Modell-/Lifecycle-/Quellenprüfungen grün vor
der zusätzlichen Gegenprobe. Ganze Missionen laufen erst nach finaler V5-Prüfung.

Finaler Kandidat **16cbe5c** vor C42: tatsächlicher Zwölfpaketbuild **6,57 s**, **1.945 direkte Tests / 61,77 s**, **1.933 colcon-Tests / 1 min 1 s**, null Fehler oder Skips. Die Mengen überlappen. Neue Timing-/Sensor-DDS-Regressionen sind enthalten; früherer V4-Fehler bleibt dokumentiert. C42 läuft jetzt als unveränderter vollständiger Manifestfall.

## C42: tatsächlicher Planstart und konsistenter TF-Gegenlauf

C42 (`16cbe5c`, neuerer Core mit älterer Native-Unterlage) bleibt negativ: drei
Ankünfte und Beobachtungen, 90,164 % Referenzboden, 2,577 m Fahrt, mindestens
102 mm unabhängiger gepaddeter Abstand. Finite Sensoren eigener Prozess,
Quellen stabil, Kind terminal und Quellenprozess beendet. Der tatsächliche
implizite ComputePath-/BT-Plan beginnt in allen aufgezeichneten Abfragen bei
(0,0), auch bei aktueller Roboterpose (2,581; 0,064). Explizite hypothetische
Startabfragen beginnen korrekt. Der zweite südliche Controller-Versuch meldet
Transformzeit 1791232115,502 bei Pfadzeit 1791232136,331. Das ist kein
Gesamtpositivnachweis und noch kein bewiesener ABI-/SDK-Ursachennachweis.

`c42-recorded-plans.json` enthält alle 23 tatsächlich empfangenen Native-Pfade.
Die isolierte echte C++-Gegenprobe `c42-current-native-start-pose` verwendet
einen konstanten TF und impliziten Start: Beginn (2,55; 0,06) bei erwarteter
Pose (2,558; 0,066), daher korrekt; keine Bewegung und kein Gesamtlauf.
Kandidat `ee7e21b` ergänzt ausschließlich passive Planheader, empfangenen
Controller-Plan und unabhängige TF-Snapshots. Zehn betroffene Prüferfälle grün.

`native-final-v9-*` baut alle zwölf Produktpakete frisch gegen die mit der
Native-Unterlage konsistenten älteren ROS-Pakete in einen separaten Präfix:
47,0 s, 1.945 direkte Tests (62,56 s), 1.933 colcon-Tests, keine Fehler/Skips.
Ein früherer Buildpräfix wird nicht überschrieben. C43 prüft dieses konsistente
Gesamtsystem mit dem ursprünglichen vollständigen Manifest; bleibt negativ.
Drei Ankünfte/Beobachtungen, 79,536 % Referenzboden, mindestens 120 mm
unabhängiger gepaddeter Abstand. Die dynamischen impliziten Planstarts sind
korrekt (0,93; 0) bzw. (1,89; 0), während die aktuelle unabhängige TF-Pose
fortschreitet. Kein konkreter ABI-Grund aus dem Vergleich erfunden.

Der tatsächliche NavFn-Server bricht anschließend einen nicht extrahierbaren
Pfad ab. Das Produkt beendet darauf bisher die Mission mit `nav2_plan_failed`.
Kandidat `4def089` unterscheidet tatsächlichen terminalen Actionstatus ABORTED
von CANCELED/Kommunikationsfehler. Nur dieser rein lesende Vorschlag wird nach
bestätigtem Halt und frischen gültigen Eingaben verworfen; eine bereits
erfasste Schutzursache hat Vorrang. Aufgaben-/Gesamtversuch zählt weiter,
kein Fahrfehler ohne Dispatch, keine Erledigung und keine Budgetverlängerung.
Drei rote Originalfälle in `c43-planner-abort-before-v2.log`, danach 25
betroffene Eltern-/Join-/Frischefälle grün (9,15 s). Frühe Prüferfassungen mit
nur einem Frontiercluster bzw. unpassendem Beobachtungszähler sind erhalten;
sie werden nicht als Produktfehler ausgegeben. C44 läuft unverändert.

## C44: Bodenprüfung erfüllt, Kandidatenbudget noch negativ

`4def089` erreicht sechs Ankünfte/fünf Beobachtungen; 96,850 % Referenzboden,
45 mm maximaler Wandfehler, mindestens 100 mm unabhängiger gepaddeter Abstand.
Ein angekommenes Ziel hat keinen gültigen neuen Beobachtungsreceipt und bleibt
offen. Die nächste Auswahl überschreitet fünf Sekunden: Gesamtresultat negativ.
Exaktes natives Karten-/Checkpointpaar erfolgreich gespeichert; keine Resume-
oder Wholemission-Abnahme daraus abgeleitet. Originalresultat unter C44.

Offline-Profil auf den späteren tatsächlichen terminalen Rastern, endlicher
letzter Scanwinkelabdeckung und gespeichertem Originalpolicybestand (nicht
gleichzeitig erfasste Fehlereingaben): 121 Sichtabfragen 2,67 s, 65 lokale
Evidenzdigests 1,61 s, Gesamtbudget nach 5,01 s überschritten. Original
Profiltext erhalten; die ursprüngliche Binärprofildatei wurde beim erneuten
Probeaufruf überschrieben. `selection-local-cache.prof` ist ausdrücklich der
spätere Cache-Zwischenstand, kein ursprüngliches Binärprofil.

`0f0fa42` wiederverwendet Inhaltsdigests nur innerhalb derselben vollständig
evidenzgebundenen Suchrunde; mutierte Arrays, Masken/Raster und neue Suchrunde
verwerfen sie. Vier rote Originalfälle, nach Korrektur 101 betroffene Tests grün.
Zusätzlich werden alle unveränderten Halbzell-Strahlpunkte in Blöcken berechnet,
aber nach dem originalen ersten Stop nicht weiter. Ein vorausgehender Punkt
erhält die diagonale Verdeckung über Blockgrenzen; Unknown, Mindestreichweite,
Mastmasken, Scope und Kapazität unverändert. Sechs rote Arbeitskapazitätsfälle,
17 ursprüngliche Paritätsfälle schon am alten Stand grün; danach alle 124
betroffenen Fälle grün (10,75 s). Gefrorene eigene erste-Treffer-Referenz aus
4def089, rotierte Raster/Scope-Verdeckung und tatsächliche C44-Winkel/Raster
liefern exakt dieselben Treffermengen. Kein Beobachtungsgewinn daraus erfunden.

Die gleiche komplette offline Suchrunde beendet nun auch unter Profiler in
4,776 s ohne Kandidaten. Das beweist keine erfolgreiche Gesamtmission; C45
wiederholt das ursprüngliche vollständige Manifest. Zehn weitere relevante
Regressionsdateien in bestehender CI-Auswahl ergänzt; Remote-CI nicht gestartet.


## C45/C46 und unveränderte Wiederholung A47

C45 scheitert vor Bewegung am Quellenvorlauf: 359,8 ms tatsächliche
Radkontinuitätslücke; drei Quellenexecutor-Threads pausieren ungefähr 330 ms
bei zusammen nur 6–9 ms Prozess-CPU. Der ursprüngliche Fehler bleibt
verriegelt, Budgets und Kriterien unverändert. Source-/Sensorresultate und
Latenzprotokoll unter C45. Ursache der Pause noch nicht bewiesen.

C46 ist ausdrücklich kein Manifest-Abnahmelauf: periodische Python-Stack-
Aufzeichnung und passive Publisher-Laufzeitmessung. Startup ohne gültigen
Fusionstatus, keine lange Veröffentlichung oder entsprechende Quellen-
executor-Pause aufgezeichnet. Beim Aufräumen hängt der Supervisor; eigene
Source-/Supervisorprozesse nach bestätigter Stillstandsausgabe einzeln
mit SIGINT beendet. Kein finales result.json, daher keinerlei positive
Abnahme aus C46. Originale Diagnosefiles bleiben im lokalen Scratch-Verzeichnis.
A47 wiederholt das ursprüngliche Szenario A mit unveränderten Kriterien.


## A47: negative Auswahlmessung, robotseitige Beobachtungspositionen

A47 erzielt eine Ankunft/Beobachtung und 62,375 % Boden, keine ganze Passage.
Nach drei rein lesenden Vorschlagsablehnungen und einem durch die ursprüngliche
150-s-Aufgabenfrist begrenzten Rundblick steht der Explorer mit 177 zugänglichen
Rohgrenzzellen ohne zulässige Aufgabe. Tatsächliche spätere Karten/Scans/Pose
und Originalcheckpoint durch zusätzliche passive Aufnahme und echten Map-
Manager-Save gesichert. Anschließend ausdrücklich durch Analyse-Cancel beendet
(`analysis-interruption.json`), deshalb kein positiver Abnahmenachweis und keine
Behauptung eines ursprünglichen 900-s-Endtimeouts. Originalereignisse verlustlos
komprimiert, Original-SHA/Decompressionsprüfung im lokalen Kompressionsindex.

Die Kartenansicht zeigt eine zu spät eingedrehte native Türanfahrt. Alle zuerst
geprüften alternativen Normal-Anfahrpositionen bleiben konturungültig. Derselbe
ursprüngliche Abstand und lokale Suchraum auf der aktuellen Roboterseite liefern
dagegen nützliche Beobachtungspositionen vor dem Eingang. Echte native Hinweg-
und anschließende Abfahrtsprüfungen sind für (0,855; −0,105; 2,061) positiv;
keine Bewegung/Wholemission aus dieser separaten Komponentenprobe behauptet.

Kandidat **1de7c9b** bevorzugt einen so gewonnenen vollständig eigenen
Routenbeweis vor einer bloßen Native-Planungsanfrage. Endliche aktuelle
Frontiersicht, tatsächlicher späterer Native-Plan, Kontur/Scope, gleiche
Nachbarschafts-/Trylimits und ursprüngliche Budgets bleiben verpflichtend.
Optionale Suche höchstens 0,5 s innerhalb der ursprünglichen 5-s-Auswahlfrist;
eine bereits zulässige Anfrage wird bei wenig Restbudget sofort behalten.
Zwei rote Produktfälle am alten Kandidaten, danach 200 betroffene Fälle grün;
sieben zusätzliche Einzelregressionen einschließlich tatsächlicher nativer
Gut-/Schlechtpfade und erhaltener abgeschlossener Nachbarschaft grün.
Erster Testlauf hatte wegen fehlgeschlagener Dateikopie zwei zusätzliche
Fixture-KeyErrors; korrigierter Rotbeleg ist ausdrücklich before-v2.
Erster Korrekturstand verbrauchte noch Auswahlbudget (zwei alte Regressionen
rot); begrenzte optionale Suche erhält beide Fälle. A48 läuft unverändert.


## A48: getrennte Beobachtungsflächen statt pauschaler Positionssperre

A48 bestätigt zwei Ankünfte mit 8/21 tatsächlich gewonnenen Zellen, danach
drei rein lesende Türvorschläge abgelehnt und Rundblick durch das ursprüngliche
150-s-Budget beendet. Mit 188 Rohgrenzzellen bleibt die Mission stehen. Der
zusätzliche passive Save erfasst Originalpolicy/Karten/Scan/Pose, danach
Analyse-Cancel. Der anschließende Harness-Endsave fällt noch in den globalen
Speichercooldown (1,243 s verbleibend), deshalb enthält result.json keine
finalen Kartenmetriken. Dieser durch den zusätzlichen Diagnose-Save verursachte
Fehler ist kein Produktmissions-/Map-Manager-Defekt und kein Abnahmenachweis.
Originale Eingaben/Checkpoint und Ereignisse erhalten; kein Budgetreset.

Die beiden erledigten Aufgaben betreffen entfernte Frontiers, sperren aber
pauschal nahe Beobachterpositionen für eine andere unbekannte Frontier.
Kandidat **b85a376** erlaubt deren spätere Auswahl ausschließlich mit aktuellen
endlichen unbekannten Frontierpunkten außerhalb der alten lokalen 0,8-m-
Beobachtungsfläche zuzüglich unveränderter 0,6-m-Wiederbesuchsmarge. Das
verwendet vorhandene aktuelle Sicht-/Kartenbeweise; potenzielle Sicht erledigt
keine Aufgabe. Ohne Sichtpunkte/lokalen Inhaltsbezug oder bei Überlappung
bleibt die alte Alias-Sperre bestehen. Alle alten/neuen Nachbarzähler, Cooldown,
Try-/Failurecaps bleiben verpflichtend; keine neue ID löscht einen Versuch.
Eine rote ursprüngliche Policyentscheidung, zehn geschützte Originalfälle
grün; anschließend 213 betroffene Regressionen grün, inklusive tatsächlicher
A48-Daten mit ausdrücklich modelliertem früherem Einzelablehnungszähler.
Der tatsächlich gespeicherte Drei-Versuche-Stand bleibt weiterhin gesperrt.
A49 wiederholt das unveränderte vollständige Szenario A.


## A49 und folgende Korrekturen

A49 bleibt negativ: zwei Ankünfte/Beobachtungen, 62,446 % Referenzboden,
kein Heckdurchgang. Drei Tür-Planungsanfragen verbrauchen ihre ursprünglichen
Versuche vor einem nützlichen Rundblick. Der tatsächliche HWT-Terminalfehler
entsteht vor bzw. während des angeforderten Analyse-Cancels; dieser Lauf ist
nicht lediglich ein Cancel. Der Rohgyroexecutor braucht 202,171 ms Wandzeit
und 192,199 ms eigene Thread-CPU; keine GC-Pause protokolliert. Die genaue
Ursache dieser CPU-Spitze ist noch nicht bewiesen. Ereignisse verlustfrei
komprimiert und vollständig über ihren Original-SHA rückgeprüft.

**c90b2d7** nutzt den bereits sicherheitsgeprüften noch offenen Rundblick vor
einer Auswahl, die ausschließlich unbewiesene native Planungsanfragen enthält.
Ein vollständig eigener Routenbeweis bleibt bevorzugt. Tatsächliche A48-Raster
in vier Regressionen: ein ursprünglicher Rotfall/drei geschützte Grünfälle,
anschließend 162 betroffene Tests grün. Originale Budgets/Zähler/Guards bleiben.

**95e82db** vermeidet wiederholte Kollisionsgeometrie bei exakt gleicher Pose
in der statischen deklarierten Modellwelt. Nichtnull-Geschwindigkeit, Encoder,
Integration, Clearance und jede Poseänderungsprüfung bleiben erhalten. Ein
roter Denormalrest-Fall, anschließend 15 Modell-/Isolations-/Lebenszyklusfälle
grün. 500 profiliert ausgeführte Denormalrest-Schritte: zuvor 128,600 ms, danach
11,927 ms. Dies beweist vermeidbaren Modellaufwand, nicht die Ursache der
192-ms-Gyrospitze. Passive Slow-Advance-Diagnose ergänzt; keine Erfassungszeit
oder Schutzfrist verändert. Ein erster zusammengefasster Testaufruf benannte
eine nicht vorhandene Testdatei, führte keine Tests aus und wurde mit dem
wirklichen Lebenszyklustest korrigiert. A50 läuft mit dem Originalmanifest.


## A50: Quellen stabil, scan-relevanter Join-Abbruch

Originaler ganzer A50-Lauf endet ohne Quellenpause mit task_attempts_exhausted:
zwei Ankünfte/Beobachtungen; die zusätzlich robotseitig bewiesene native Anfahrt
wird tatsächlich gefahren, später durch die frische Ganzkonturprüfung gestoppt.
62,150 % Referenzboden, 1,449 m Fahrt, minimale gepaddete Clearance 118,893 mm,
kein Heckdurchgang. Der anschließende sichere Rundblick wird durch einen
tatsächlichen Karten-/Statusjoin unterbrochen und endgültig verbraucht; weitere
reine Planungsanfragen sind konturungültig. Keine volle Abnahme.

**4f500d0** erhält den bereits gemessenen Winkel desselben Scanversuchs über
diesen Join hinweg. Erst bestätigter Stillstand, danach wirkliches frisches
exaktes Paar und erneut ganze Rotationsgeometrie; Restwinkel innerhalb der
ursprünglichen 150-s-Aufgabenfrist, genau ein gezählter Versuch. Kartenwechsel,
Cancel, Rawfrische und Konturblocker bleiben wirksam. Drei rote Gegenfälle bei
den beiden originalen Methoden aus 95e82db, danach 257 betroffene Tests grün.
Frühe Testfixtures hatten vollständig bekannte Karten ohne nützlichen Scan
sowie eine falsche erwartete Endursache nach tatsächlich veraltetem Rawstamp;
die Originalfehlprotokolle bleiben erhalten, korrekter Rotbeleg before-v3.
A51 wiederholt das ursprüngliche vollständige Szenario, kein Hardwarebeleg.


## A51 und entkoppelte robotseitige Beobachtungswahl

A51 bleibt ein explizit diagnostisch abgebrochener Negativlauf: erste Ankunft
mit acht gewonnenen Zellen, eine reale Folgeaufgabe konturbedingt abgebrochen,
weitere reine Native-Anfragen abgelehnt; 257 erreichbare Rohgrenzzellen.
65,278 % Boden, 0,694 m Fahrt, kein Heckdurchgang. Passive spätere
Karten/Costmap/Scan/TF/Persistenz erfasst. Erste kurzlebige Cancel-Publikation
wurde nicht vom Manager empfangen; neuer Publisher wartet auf entdeckten
Empfänger und echten Managerstatus, danach Cancellation tatsächlich bestätigt.
Mehr als zehn Sekunden zum diagnostischen Save, Endsaveschutz eingehalten.
Kompressions-/Decompressions-SHA erhalten; keine Deadline- oder Positivabnahme.

Die spätere Komponentenprobe findet bei (0,855; 0,255; 1,249) vor dem Eingang
einen nützlichen eigenen Routenbeweis und echten nativen Hin-/Abfahrtsbeweis.
Dabei wird nur die tatsächlich erledigte erste Aufgabe in einer ausdrücklich
modellierten früheren Historie auf den späteren Rastern behalten. Dies ist
kein historischer Missionserfolg und erlaubt keinen Reset des ausgeschöpften
Originals. Ein alter A47-Textlabel im nativen Diagnoseprotokoll wurde von der
Vorlage übernommen; Dateien/Eingaben/Posen sind explizit A51, Fixturemetadaten
benennen den tatsächlichen getrennten nativen Komponentenaufbau.

**7778771** hält die ursprüngliche normale Anfahrposition gesperrt, prüft aber
die bestehende lokale robotseitige Beobachtungsalternative auch dann, wenn
diese normale Position gar keinen Routenbeweis oder keine Policyzulassung
hat. Dieselben endlichen aktuellen Sichtpunkte/Policyzähler, frische öffentliche
Startkontur, Scope, ganze Route, 0,5-s-Teilbudget innerhalb ursprünglicher 5 s
und späterer tatsächlicher Native-Plan bleiben verpflichtend. Zwei rote
ursprüngliche Auswahlfälle, Originalhistory weiterhin gesperrt; 130 betroffene
Tests und vier zusätzliche tatsächliche Native-Pfadregressionen grün. Erstes
Testbatch nannte eine nicht vorhandene Datei (keine Tests ausgeführt); korrekter
Beleg affected-v2. A52 läuft mit den ursprünglichen Manifestgrenzen.


## A52 und Arbeit vor nutzloser Sichtberechnung begrenzen

A52 ebenfalls diagnostisch abgebrochen nach einem tatsächlichen ersten
Beobachtungsziel; Folgefahrt konturbedingt gestoppt, reine Türanfragen
ausgeschöpft. Spätere passive Eingaben erfasst; Abbruch auf entdecktem
Managerempfänger tatsächlich bestätigt, Endsaverate eingehalten. Keine ganze
Passage oder Positivabnahme. Ereignisse verlustfrei komprimiert/Original-SHA
rückgeprüft. Eine ungebremste separate Geometriediagnose findet eine zulässige
Position im ursprünglichen Suchraum und sogar ursprünglichen Suchrichtung;
es war keine Richtungs- oder Radiusänderung notwendig.

Der begrenzte alte Helper verbraucht 50 Sichtprüfungen/358,121 ms und findet
innerhalb 0,5 s keine Position. **df0c7c0** prüft dieselbe Route vor den teuren
endlichen Sichtstrahlen. Im tatsächlichen owning selection pass mit exakt
gebundenem Memo wird (0,825; 0,135; pi/2) nach 0,358 s gewählt; dessen echte
native Hin-/Abfahrtsproben grün. Standalone-Helper ohne den bestehenden
Auswahlmemo weiterhin zu langsam, ausdrücklich separate Messung. Frühere
Testfixture ließ diesen Memo ebenfalls aus; korrekter Rotbeleg before-v2
führt nur die alte Helpermethode aus 7778771 im identischen owning Memo aus.
Zwei Rotfälle, danach 134 betroffene Fälle grün, einschließlich A51/A52 der
tatsächlich aufgezeichneten nativen Hin-/Abfahrtspläne. Die spätere Geometrie
mit ausdrücklich modellierter nur erster erledigter Historie beweist keinen
historischen oder aktuellen Whole-Abschluss; tatsächliche erschöpfte History
bleibt gesperrt. Ursprüngliche Strahlen/Route/Kontur/Scope/Policy/Fristen gleich.
A53 wiederholt das ganze Originalmanifest.


A53 bestätigt diagnostisch abgebrochen, zwei qualifizierte Ankünfte/Beobachtungen,
73,268 % Boden, kein Heckdurchgang. Gemessener voller Scan 6,300 rad mit
Join-Wiederprüfung erfolgreich; spätere reine Vorschläge erschöpft. Neue kurze
öffentliche Beobachtungswahl nutzt die vollständige originale A53-Policy ohne
Zählerreset: Ziel (0,603390; 1,022234; -0,431592), finite unbekannte Sichtpunkte,
Eigenroute und tatsächliche native Hin-/Abfahrt positiv (Fixture A53).
Ein roter Auswahlfall vor Änderung; sechs neue direkte Schutz-/Auswahlfälle
und 171 betroffene Fälle grün. Zwei ältere globale Leerlisten-Erwartungen
prüfen nun gezielt die weiterhin gesperrte ursprüngliche Aufgabe, unveränderte
Historie und vollständige Geometrie/Sicht anderer Kandidaten. Keine neue
Erledigung oder Gesamtpositivbehauptung. Frühere negative Testlogs erhalten.


A54 endet vor dem beabsichtigten Diagnose-Cancel regulär negativ am ursprünglichen
5-s-Auswahlbudget (zwei Ankünfte/Beobachtungen, 72,171 % Boden, 45 mm
maximaler Wandfehler, kein Heckdurchgang). Cancel hat danach keinen Subscriber
mehr und erteilt keinen Abnahmenachweis. Passiv gespeicherter tatsächlicher
Verlauf findet denselben kurzen öffentlichen Weg in 2,828 s im isolierten
Nachlauf. Die begrenzte öffentliche Auswahl wird vor unbewiesene entfernte
Approach-Arbeit gesetzt; erledigte identifizierte Aufgaben werden dabei
ausgeschlossen. Roter Reihenfolgefall auf tatsächlicher vollständiger A54-History
erhalten. Die bisherigen Seitenwegtests prüfen bei der neuen Wahl deren
gleichen begrenzten Abstand und vollständige Geometrie, bei Wiederverwendung
einer Position die bestehende endliche Sichtmarge außerhalb des erledigten
Beobachtungsbereichs. Alle ursprünglichen Historyzähler unverändert.

Separater Ankunftsfix für den in A47 gemessenen SUCCESS außerhalb 15 cm: nur
terminaler Child, bestätigter Halt, frische echte Eingaben, gleiche Aufgabe,
gleicher ursprünglicher Start und noch vorhandene Try-/Gesamtlimits erlauben
einen weiteren vollständig geprüften Nav2-Versuch. Kein Receipt für den
Außerhalbfall, keine .15-m/.4-rad-Lockerung. Acht direkte Fälle grün; drei rote
Verhaltensfälle vorher (zusätzlich ein ursprünglich ungültiger Retry-0-Test
im erhaltenen Beforelog, korrigiert auf echten per-task-Cap bei größerem
Gesamtlimit). Insgesamt 261 betroffene Fälle grün, keine Fehler/Skips.


A55 diagnostisch bestätigt abgebrochen: zwei Ankünfte/Beobachtungen,
72,256 % Boden, 45 mm Wandfehler, kein Heckdurchgang. Nachtest-Fixture bildet
un zusätzlich den produktiven <=90-Zentrumsfilter auf tatsächlicher Costmap
nach; die Körperprüfung verwendet unverändert <100. Korrigierter Filter
ändert den gefundenen Kandidaten nicht und erklärt diesen Stillstand nicht.
Auswahlfixtures bisher erzwungen private_epoch_expired=True; im Produkt kann
der private monotone Bestand ungültig sein, ohne dass seine Karten-/Sitzungs-
identität abläuft. Public-observation wartete trotzdem auf dieses andere
Ereignis. Drei rote neue Fälle auf A53/A54/A55 mit ungültigen privaten
Produkt-Evidenzobjekten, leerer aktueller Ausnahme und weiterhin gültiger
Identität. Neue öffentliche Auswahl erfordert ausschließlich aktuelle volle
öffentliche Geometrie und die ursprünglichen Quellen/Sicht/Policy/Fristen;
der ungültige private Bestand bleibt ungültig, keine Unknown-Ausnahme entsteht.
Neue Diagnose zeigt epoch_expired getrennt von valid. Alle Native-Körper-/
Hin-/Abfahrtsprüfungen bleiben zwingend. Kein Gesamtpositiv aus Nachtests.

Inkrementeller Explorerbuild und **271 betroffene Regressionen grün**, keine
Fehler/Skips; einschließlich aller bisherigen nativen Departure-Fixtures.


B56 regulär negativ: eine Ankunft/Beobachtung nach echtem Join-Retry,
60,105 % Boden, maximaler Wandfehler 25,495 mm, Auswahldeadline 5 s.
Originalstatus bestätigt private_epoch_expired=False und beide privaten
Inventare valid=False / projected=0. Die alten zwei Forward-Start-Suchen
durchlaufen dennoch die längeren privaten Anfangsdistanzen. Neue drei rote
Gegenfälle beweisen solche unnötigen langen Anfragen vor der existierenden
öffentlichen kurzen Wahl. Nur aktuell gültiger privater Bestand darf diese
Startsuche ausführen und ihr initiales Ranking erhalten; öffentliche Wege
behalten obligatorische native Abfahrtsprüfung. Erster breiter Regressionstest
hatte einen fehlenden optionalen Opt-in-Zustand in Standardfixtures; der
Zugriff wurde mit dem bestehenden Default geschützt (Negativlog erhalten).

270/271 im breiten Lauf grün; ein reiner Rankingkennzeichen-Fall erwartet
nun ebenfalls bounded_public_observation. Ganze Kontur und erledigte
Folgeaufgaben bleiben geprüft. Alle 19 Fälle der beiden anschließend
korrigiert ausgeführten Auswahl-Dateien grün. Keine offene betroffene
Regression; endgültige vollständige Gesamtsuite bleibt separat ausstehend.


### B57/B58 und gebundene öffentliche Anfahrt (06.10.2026)

B57 mit `c9a3117` bleibt regulär negativ am originalen 5-s-Auswahlbudget,
nach einer Ankunft/Beobachtung. B58 mit Auswahlprofilierung ist ausdrücklich
`manifest_compatible=False`: eine Ankunft/Beobachtung; danach wurde dieselbe
öffentliche Anfahrt dreimal wegen einer neuen Rohkarte vor ihrem passenden
Status abgebrochen. Terminal `map_status_join_retry_budget_exhausted`;
keine erfolgreiche zweite Beobachtung oder Gesamtmission.

`c9bea6a` erhält während genau eines bestehenden öffentlichen Nav2-Kinds
höchstens im ursprünglichen 1,25-s-Joinfenster das vorherige exakte Kartenpaar
mit seinen ursprünglichen Zeiten und Identitäten. Die frische neue Rohkarte
kann nur bisher bekannte freie Zellen entziehen: gleiche Auflösung/Frames/
Orientierung, ganzzellig ausgerichtete Projektion; unbekannte/belegte/fehlende
Zellen sperren. Keine neue Freifläche, private Anfangsfreigabe, Zielwahl oder
Ankunft/Beobachtungsquittung. Das echte passende neue Paar bleibt dafür nötig.
Kontur-/Routenprüfung, Quellenalter, Sitzung und ursprüngliche Fristen gelten.

Vier neue positive Bindungsgegenfälle zuerst rot; 21 neue Regressionen samt
bestehendem Parent mit einem Kind und drei aufeinanderfolgenden Joinfenstern.
Hindernis, Zeit-/Quellenverlust und Epochenwechsel stoppen weiterhin. Erster
betroffener Lauf 189/190 grün: öffentliche Parent-Fixture enthielt noch private
Startinventare, die korrekt ablehnten. Öffentliche Fixture korrigiert; danach
**190/190 betroffene Tests grün**, inkrementeller Explorerbuild erfolgreich.
Keine abgeschlossene Gesamtmission daraus; B59 wiederholt das originale B
mit unveränderten Manifestgrenzen und ohne Profilierungsoption.


### B59/B60, andere Grenze und ursprünglicher Cooldown (06.10.2026)

B59 regulär und B60 mit opt-in Profilierung bleiben negativ: jeweils eine
Ankunft/Beobachtung, anschließend `frontier_candidate_processing_budget_exhausted`.
B60 ist `manifest_compatible=False`, kein Abnahmenachweis. Exakter Einstieg in
dessen Auswahl wurde mit Roh-/Kostenraster, gemeinsamen Bezug, endlichem Scan,
wirklichen privaten invaliden Inventaren und Aufgabenhistorie gesichert.
Profil: 5,156 s, 376 Routenprüfungen; öffentlicher begrenzter Helper 0,532 s,
weitere unbewiesene Alternativen verbrauchen das ursprüngliche Budget.

Isoliertes Replay auf schnellerem ungestörtem Prozess findet teils auch ein
anderes zulässiges Ziel in 1,59 s; dieser Befund bleibt erhalten. Der Fehler
ist kein Beweis, dass überall jegliches Ziel fehlt. Bei nahen Beobachterposen
wurde eine andere tatsächliche Grenze durch Zielnähe einer erledigten Aufgabe
zugeordnet. Der ursprüngliche 30-s-Cooldown kann zusätzlich eine bereits ganz
geprüfte andere öffentliche Sicht vorübergehend sperren.

`d57c257`: nur endliche Sichtpunkte jenseits der bisherigen begrenzten
Beobachtungsfläche plus voller Revisit-Marge dürfen die Zielnähen-Aliasbildung
zu einer erledigten anderen Grenze vermeiden. Gleiche Frontier bleibt gleiche
ID; alle nahen Try-/Fehlergrenzen, lokale Evidenz und Cooldown bleiben.
Eine aktuell voll geometrisch/sichtgeprüfte öffentliche Möglichkeit, deren
**einziger** verbleibender Ausschluss der ursprüngliche Cooldown ist, erlaubt
Warten vor teurer unbewiesener Alternativarbeit. Kein Reset, kein Receipt,
kein behaupteter Abschluss: raw-erreichbare Restgrenze bleibt sichtbar und
Missionzeit läuft weiter; nächste Auswahl prüft neu, native Hin-/Abfahrt bleibt
Pflicht vor Dispatch.

Acht neue Policy-Fälle zuerst rot wegen noch fehlender expliziter Sichtbindung.
Zwei aufgezeichnete Geometrie-/Historyfälle grenzen den originalen 0,3-m-
Subkandidaten gesondert ein: damit allein Cooldown ursächlich; übrige originale
0,45-/0,6-m-Kandidaten bleiben in Gesamtmissionen unverändert. Zuerst Rot an
echten vorherigen Methoden `c9bea6a`; danach **127/127** betroffene Regressionen
grün und Explorerbuild erfolgreich. Erste unbeschränkte Gegenprobe konnte
berechtigtes anderes Ziel statt Wartezustand finden; Testanforderung wurde
auf den deklarierten strengeren Subkandidaten begrenzt (Logs erhalten).
Plain JSON/NPZ/CDR-Fixtures enthalten ausschließlich eigene synthetische Daten;
keine Live-Quellen-/Hardware-/Gesamtqualifikation durch Replay.
B61 ist anschließend der unveränderte reguläre Gesamtfall ohne Profilierung.


### B61 und begrenzter Rechenaufwand der Konturprüfung (06.10.2026)

B61 regulär mit der Sicht-/Cooldownkorrektur bleibt negativ nach einer
Ankunft/Beobachtung am originalen Auswahlbudget. Der isolierte Wartezustand
wurde im Produkt vor dem begrenzten Helperende nicht erreicht; kein
Gesamtpositiv aus den vorherigen Komponentenprüfungen.

`4722f32` reduziert identische Winkelfunktionsberechnungen in der bestehenden
Batchkonturprüfung auf einmal je Pose. Verbotene Zellzentren außerhalb des
nach außen gerundeten Umkreises der **unveränderten** reservierten Rechtecke
benötigen keine weitere Rechteckprüfung. Alle Posen, 15 Winkelschritte,
Chassis/Padding, Halbzelldiagonale, Interpolations-/Trackingreserven bleiben.
Kein Gesundheits-/Freiraumcache oder Timeoutanstieg. Dieselben 320 Prüfungen
über den 487-Posen-RPP-Verlauf auf echten eingefrorenen B60-Rastern: 4,771657 s
vorher, 3,383489 s nachher, jeweils alle 320 Ergebnisse identisch. Diese
Zeitmessung ist kein Nachweis einer eingehaltenen Live-Auswahlfrist.

Zwölf zusätzliche scalar-versus-batch-Fälle prüfen jeweils bis zu 40 einzeln
verbotene Originalkonturzellen, einschließlich gedrehter Origins, asymmetrischer
Ecken und Winkelschritte; keine zweite Sperrzelle verdeckt eine Fehlfreigabe.
**165/165** betroffene Geometrie-/Navigationstests grün. Anschließender voller
Zwölfpaketbuild `native-final-v10` erfolgreich in 6,25 s; vollständige direkte
und colcon-Suiten separat erfasst. Vollständige unveränderte Mission folgt,
kein vorgezogener Gesamtabschluss.
## B62: private Anfangsfreigabe war fälschlich öffentliche Rückfahrtfläche

Originaler vollständiger Lauf B62 auf `4722f32`: eine qualifizierte Ankunft/Beobachtung (12 neue Zellen), sieben Versuche, drei tatsächliche Bewegungsfehler, terminal `failure_budget_exhausted`. Nach der ersten Abfahrt folgen nur Drehungen; die Schutzprüfung verwirft Ziele mit `goal_orientation_invalid` bzw. `footprint_sweep_invalid`. Die dazwischen gemessene volle Drehung erreicht 6,287962 rad; sie ist kein weiterer Ankunfts-/Beobachtungsbeleg. Weg 0,902314 m, Referenzboden 69,1497 %, maximale Wandabweichung 35 mm, Fahrzeugheck nicht durch die Passage. B62 bleibt negativ.

Die gesicherten originalen B58/B60-Auswahleingaben enthalten 82 roh unbekannte Zellen innerhalb der virtuellen ersten Aufstellfreigabe. Das gewählte B60-Rückziel berührt 44 davon. Auch die alternativ geprüfte Ankunftsorientierung berührt unbekannte Zellen; eine bloße Orientierungsänderung löst den Fehler nicht. `known` enthielt private Anfangsprivilegien und war deshalb kein Beleg für öffentlich beobachteten Freiraum. Frühere öffentliche Komponentenprüfungen auf dieser Maske belegten die Historien-/Cooldownlogik, aber nicht die erforderliche strikte Rohfreiraumklassifikation.

Reparatur: ursprüngliche private Zellen monoton mit der aktuellen, tatsächlich vollständig überdeckten ungepaddeten Fahrzeugfläche schneiden; verlassene Zellen nie neu freigeben. Fester erster Anker, Referenz und historische Egress-Inventare bleiben erhalten. Öffentliche Suche und öffentliche Native-Abfahrtsprüfung entziehen alle privaten Roh-Unknown-Privilegien. Die gekoppelte private Egress-Prüfung greift bei tatsächlich unbekannten Zellen unter der aktuellen reservierten Kontur, auch wenn sie virtuell whitelisted sind. Bei vollständig roh beobachteter aktueller Kontur gibt es keine erste Abfahrtsausnahme und keine privaten Suchseeds.

Fünf neue Regressionen reproduzieren vor der jeweiligen Reparatur die Rückfreigabe bei gemessener Fahrt, die unerlaubte private Drehung, die konkrete B60-Rückroute und die falsche erste Abfahrtsphase bei vollständig beobachteter Fläche. Die beiden alten Tests trennten TF-Verfeinerung und wirkliche Bewegung nicht korrekt; ihre Erwartungen wurden auf unveränderte reine Verfeinerung und monotone Entziehung bei wirklicher Fahrt präzisiert. Keine Rasterbeobachtung, Quellenzeit, Scope, Fahrzeugreserve, Deadline oder Aufgabenhistorie zurückgesetzt. Betroffene **235 Tests grün (33,66 s)**, inkrementeller Explorerbuild grün. Gesamtbuild/volle Regression und die unveränderten Ganzmissionen folgen; dieser Komponentenabschluss ist kein 3/3-Nachweis.

## Vollständige Regression: alte unzutreffende öffentliche Testannahmen

Der erste vollständige Lauf v11 auf `7e470db` ergibt 2.086 grüne Fälle und zwei rote Startbeobachtungstests (110,71 s). Deren gespeicherte vermeintlich öffentliche Zwischenpose (0,174985 m, −0,000005 m) berührt tatsächlich **40 roh unbekannte Zellen** unter der aktuellen reservierten Kontur; die restaurierte ursprüngliche private Historie ist bereits ungültig und leer. Hier ist eine normale Fahrt nicht belegt. Testkorrektur `5d38f85` erhält den Raw-Stand und prüft die gebotene Ablehnung. Der positive Folgeaufgabenfall verwendet stattdessen die exakt gespeicherten B60-Eingaben, echte Rohfreiraumprüfung und die ursprüngliche 30-s-Pause (nur isolierte Komponentenuhr, kein Live-Quellenbeleg). Alle acht Startbeobachtungstests grün (5,17 s). Ursprünglicher roter Gesamtbericht bleibt erhalten; der frische vollständige v12-Lauf folgt unverändert.

Tatsächliche kohärente alte Humble-Präfixe (`ap06-old-product-install`): 136 installierte Produktdateien bytegleich zu Ausführungskopie und Repository, acht Native-Binär-SHAs, reale Importpfade und ROS-Versionen gesichert. Manifest SHA256 `54132aaaca7ccee8412d5a5078410f49cb2f388da08c8f18899e5493ab4021da`, MASTERPLAN SHA256 `030782dc0cce24d23ef730783703f91cac6957ceb4b7305a224342fba74a8a10` unverändert. Die älteren Identitätsberichte mit neuerem Produktpräfix bezeichnen ihre damaligen Zwischenstände, nicht diesen tatsächlichen Prüfstand.

## Frischer vollständiger Stand v12

Kandidat `5d38f85`, Produktcode `7e470db`: vollständiger Zwölfpaketbuild 6,42 s; 2.088 direkte Tests grün (111,39 s), regulär 2.074 colcon-Tests ohne Fehler/Fehlschläge/Skips. Mengen überlappen. Alle ursprünglichen zwölf Pakete und drei Simulationstools geprüft; alter roter v11-Lauf unverändert erhalten. Alle Produktdateien/Bindings/Native-SHAs auf tatsächlich ausgeführtem alten kohärenten Präfix gesichert. Originalaufrufe und vollständige Ergebnisse neben dieser Datei. B63 ist die anschließende unveränderte Gesamtmission auf diesem Produktstand; ohne Profiling/Geometrie-/Sichtdiagnoseoptionen, keine parallelen Builds/Tests. Noch kein positiver Gesamtmissionsnachweis.

## B63/B64: native Rasterkoordinaten und öffentliche Vorausrichtung

B63 auf `7e470db` erreicht zwei Ankünfte/Beobachtungen (12 und 2 Zellen), sechs Versuche, null Fahrfehler, aber drei verworfene echte Native-Pfade und anschließend ursprüngliches 5-s-Auswahlbudget. Weg 1,358430 m, Boden 74,1602 %, Wandabweichung 35 mm, Heck nicht durch die Passage. Negativ. Der publizierte letzte NavFn-Pfad reproduziert einen RPP-Sweep durch belegte Zelle (37,73), Kartenposition (1,455,−0,765), vorhergesagte Pose (1,141897,−0,464289,−0,304236). Raster sind spätere stationäre Terminalnachrichten, kein exakter synchroner Fehlersnapshot. Echte CPP-A*/Dijkstra-Gegenproben auf dieser Raw-Geometrie scheitern ebenfalls. Bloße Vorausrichtung oder pauschale Halbzellverschiebung alter Punkte reichen nicht.

`2074efa`: gepinnte NavFn-Indexumrechnung korrekt an enthaltende Zelle (`floor`) und Zellmitte (`+0,5`) gebunden; nicht endliche Punkte verworfen. Kein Raw-/Kosten-/Scope-/Weltraster verschoben oder resampelt. Die echten korrigierten CPP-Pfade plus vorhandene öffentliche Vorausrichtung bestehen gesamte Bewegung nominal/±0,02 rad Handoff. Radius **0,28 m** unverändert; die separat diagnostizierte strengere 0,325-m-Variante wird nicht übernommen. Bereits sichere native Rollouts bleiben zuerst. Eine zusätzliche ganze geprüfte öffentliche Drehung erlaubt nur der vorhandene Explorer vor einer sonst unzulässigen Abfahrt, nicht die private Anfangsausnahme oder ein aktives Nav2-Kind. Sechs neue Fälle, 190 betroffene Tests grün (39,77 s); ursprünglicher Prototyp änderte vier gespeicherte Endposen, seine rote Ausgabe bleibt erhalten. Native-first bewahrt die ursprünglichen Erwartungen.

Direkte gelinkte Native-Koordinaten: 388/492 vorher falsch, 492/492 danach grün, CTest grün. Gepinntes Originalarchiv/Quellenvorbereitung ergibt bytegleich denselben Patch. Native Zusatzsuite: 32 Einträge, keine Fehler/Failures, fünf ausdrückliche Upstream-cppcheck-2.7-Performance-Skips; Format- und Offline-Schema-Gegenfälle erhalten und behoben. Originalschema samt eingebundenem Schema aus offiziellem ROS-REP-Mirror per URL/SHA/lokalem XML-Katalog geprüft, kein Lint abgeschaltet.

V13-Zwölfpaketbuild 6,66 s, 2.094 direkte (116,40 s)/2.080 colcon-Tests grün, keine Produktfehler/Skips, Mengen überlappen. Neun Native-Bewegungsfälle grün; größte Spurabweichung 3,081 mm/0,004813 rad innerhalb unveränderter Reserve. Tatsächliche Plugin-/Quellhashes und 136 bytegleiche Produktdateien gesichert; ursprünglicher Masterplan und Szenariomanifest unverändert.

B64 bleibt ebenfalls **negativ**: eine qualifizierte Ankunft/Beobachtung, zuerst ein ehrlich als `arrival_revalidate` verworfener Native-SUCCESS außerhalb der Originaltoleranz; eine rein lesende lokale Folgeplanung mit `goal_stop_rotation_invalid`, danach ursprüngliches 5-s-Auswahlbudget. Keine Fahrfehler oder Passage. Der nachfolgende B65-Lauf ist ausdrücklich eine Profilingdiagnose mit `manifest_compatible=false`, kein Abnahmekandidat. Auswahlaufwand und mögliche Beschränkung der zusätzlichen öffentlichen Vorausrichtung auf tatsächlich gebundene Native-Pfade werden noch gemessen; keine weitere Reparatur/3/3 behauptet.

## 06.10.2026 – Beobachtung am tatsächlichen Stopp / Kandidat d9ade6e

B65 bleibt ausdrücklich Profilingdiagnose, B66 ein negativer Originallauf mit Analyse-Cancel; keine Gesamtpositivmission aus beiden. B66: drei Ankünfte, zwei Beobachtungen, kein Heckdurchgang; nach Analyse-Cancel beide Kindkanäle leer und alle vier Befehlsströme null. Originalarchive bleiben verlustfrei erhalten. B65-Auswahlobjekt 2 verspricht 24 endliche Grenzpunkte am idealen Ziel `(1.256245,-0.489332,2.549039)`; tatsächlicher Native-Rolloutstop `(1.171900,-0.367718,-3.334146)` sieht null davon. Beobachtungschance daher am Stoppprognosepunkt berechnen; nach tatsächlicher Native-Pfadbindung erneut mit ursprünglicher Auswahlkarte/Originalpunkten prüfen. Pure Chancenprüfung zählt niemals als beobachtete neue Zelle.

Neue öffentliche Nahsuche berücksichtigt seitliche Positionen und bevorzugt vollständig geprüfte Drehreserve innerhalb des bisherigen 0,5-s-Hilfs-/5-s-Auswahlbudgets. Zähler/Historie/Cooldowns gelten an der prognostizierten Beobachterposition. Exakte vollständige B65-Ledgerfixture bewahrt private Gültigkeit, erste Referenz, Weg und alle Aufgaben; die vereinfachte frühere Fixture ließ einen falschen Epoch-Ablauf entstehen und wurde deshalb nicht als genügender Originalnachweis verwendet. Fünf neue Stoppsicht-/Historien-/Quellenfälle plus gezielte Altregressionen grün; Workbudgettest korrigiert, weil Sicht bewusst am Stopppunkt statt am Idealziel stattfindet. Unverändert strikte Bedingung: unmögliche Wege dürfen keine Sichtarbeit verbrauchen. V15-Fehllog (2.099 grün/1 rot) erhalten, sieben gezielte Nachprüfungen grün. Vollprüfung v16 auf `b51fb0a` grün: **2.100 direkte Tests in 122,11 s / 2.086 colcon-Tests**, null Fehler/Skips; Zwölfpaketbuild 6,44 s. Mengen überlappen. Vollständige Originalbefehle in `native-final-v16-tests.sh`, unveränderte Vollprüfung; alle vier v16-Prüflogs erhalten.

Echte C++-Native-Probe `b65-refuge-native-plan-probe-unchanged-controller/result.json`: öffentliche Beobachtungspose `(0.903844,-0.596212,0.677019)` besteht vollständige Anfahrt, Abfahrt und Sicht am Native-Stopp `(0.942644,-0.453544,0.277019)` auf 18 ursprüngliche Punkte. Gefrorener Komponentenzustand benennt ausdrücklich hypothetisch 31 s vergangenen ursprünglichen Cooldown; keine Live-Historie, kein Reset und kein Gesamtabschluss. B66-Gegenproben zeigen Konturkontakt am Türpfosten auch mit größerem Radius, größerer Inflation oder kleinerem diagnostischem Lookahead. Keine dieser Parameteränderungen übernommen; Radius 0,28 m, Inflation 0,45 m/Skalierung 3 und Lookahead 0,4 m unverändert.

`source-identity-v16.json` und `native-identity-v16-bound.json`: 136 installierte Produktdateien/143 Quelldatensätze bytegleich; korrigierter Native-Pluginhash unverändert. MASTERPLAN/Manifest unverändert. **Weiterhin 0/3; frische Gesamtmission B67 ohne Profiling läuft auf diesem unveränderten Stand.**

## B67 – echte Callback-Dispatchreihenfolge / 7a2b09e

B67 ist regulär negativ, null qualifizierte Ankünfte, 0,761 m autonome Bewegung; danach terminale HWT-Störung im Explorer. Kein manuelles Diagnose-Cancel/Positivnachweis. Quellenprozess meldet keine >100-ms-Executorarbeit; tatsächliches Erstfault zeigt keine Frischeüberschreitung: neuere Rawprobe `1791256959.905483169` tritt bei `222910.632857649` ein, ältere bereits dispatchte Probe `1791256959.895403290` erst bei `222910.632974442`. Die Reentrant-Ausführung pausiert bereits vor Guard-Eintritt; deshalb kann der bisherige Health-Vergleich der Eintrittszeiten diese Überholung nicht erkennen und verwirft wegen Messreihenfolge. Echter ursprünglicher Erstfault in `b67-first-explorer-terminal.json`, unveränderte Resultate/Logs unter `mission-b-v67/`; alle vier Endbefehle null, beide Kinder beendet. Verlustfreies Eventarchiv im Kompressionsindex.

Korrektur `7a2b09e`: eigener MutuallyExclusiveCallbackGroup je Raw/Yaw/Wheel-Quelle, explizite vorhandene Wheelgruppe erhalten. Kein Zeitstempel-/Frist-/Health-/QoS-Wechsel, keine pauschale ältere Probenakzeptanz. Native DDS-Test pausiert den alten Callback vor `_sample`, publiziert die neuere Probe und zeigt auf altem Produkt drei tatsächlich vertauschte Dispatchfolgen (rot); drei echte publizierte Stempelrückläufe bleiben ungültig (grün). Nach Korrektur sechs native Fälle grün und andere Quelle während Pause unabhängig verarbeitet; originale Messstempel erhalten. 155 betroffene Clock-/Health-/Fahrtor-/Explorer-Recoverytests grün in 2,88 s. CI erfasst das vollständige robot_state_estimation-Testverzeichnis bereits. V17-Gesamtprüfung läuft; kein neuer Gesamtabschluss.

### Serielle Gate-Besitzer erhalten / b8189a9

V17-Vollprüfung: Build grün, 2.104 direkte Tests bestanden, zwei Gate-Callbackgegenfälle negativ. `7a2b09e` änderte auch bereits serielle Standard-/passive Gategruppen und damit deren nachgewiesene Status-/HOLD-Kopplung. `b8189a9` beschränkt zusätzliche Samplegruppen auf tatsächliche `ReentrantCallbackGroup`-Besitzer; vorhandene explizite Wheelgruppe und bereits serielle Gategruppen bleiben erhalten. Neue native Dispatchfälle und alle bisherigen Gate-Callbackfälle unverändert, 160 gezielte Quellen-/Clock-/Health-/Gate-/Recoverytests grün in 10,42 s. Negatives V17-Vollprotokoll bleibt erhalten. V18-Gesamtprüfung auf `b8189a9` grün: **2.106 direkte Tests in 121,57 s / 2.092 colcon-Tests**, null Fehler/Skips; Zwölfpaketbuild 6,33 s, Mengen überlappen. Vollbefehle in `native-final-v18-tests.sh`, alle vier vollständigen Prüflogs erhalten. Identitätsnachweise v18: 136 installierte Produktdateien/143 Quelldatensätze bytegleich, Native-Plugin unverändert. B68 ohne Profiling gestartet; weiterhin kein Gesamtpositiv behauptet.


### 06.10.2026 – frische Zustandsvalidierung v19 auf Nutzerwunsch

HEAD `b8189a9` plus vorhandene uncommittete Teilbeobachtungsänderungen, keine weitere Produktänderung während dieser Prüfung. `native-status-v19-tests.sh`: zwölf Pakete gebaut (6,52 s), direkte Gesamtauswahl **2.112 bestanden / 1 fehlgeschlagen**, keine Skips (129,98 s). Originalrotes Protokoll `native-status-v19-affected-tests.log`. Skriptabbruch mit Exit 1 vor colcon-Testphase; keine neuen registrierten Testzahlen behauptet. Historische v18-Zahlen beziehen sich ausschließlich auf deren früheren Kandidaten.

Der rote Fall `test_metric_proposal_alternatives.py::test_rejected_query_can_try_distinct_pose_without_new_scan_or_reset` belegt eine neue Sperre für einen anderen Planvorschlag nach ursprünglichem Cooldown: `valid_view` gilt jetzt auch für `proposal_rejected`, während bestehende Vorprüfungen keine Sichtpunkte liefern. Die neue Behandlung `partially_observed` ist noch nicht fertig qualifiziert. `native-status-v19-baseline.py` lädt in einem separaten Testprozess nur das originale HEAD-Policy-Modul aus `native-status-v19-head-metric_frontier.py`: beide vorhandenen Tests bestehen; installiertes Produkt nicht verändert. Gegenprobe ist ein Komponententest, kein vollständiger HEAD-Retest.

`native-status-v19-identity.json`: 136 installierte Dateien gegen ausführbare Quellkopie und Hauptworktree geprüft. `native-status-v19-source.json`: exakter HEAD, Dirty-Markierung und 432 Quell-/Test-/Konfigurationshashes. `native-status-v19-working.diff` enthält den geprüften getrackten Software-/Diagnosediff; neue ungetrackte B68-Tests und Fixtures liegen im Repository und sind in den Quellhashes enthalten. `status-before-v19.md` erhält den vorherigen Dokumentationsstand. MASTERPLAN und Szenariomanifest bytegleich.

Kleine Originalresultate von `mission-b-v68/` und `mission-b-v70-capture/` sowie Analyse-Cancel-Metadaten übernommen. B68: 2 Ankünfte/2 Beobachtungen, 229 erreichbare Grenzzellen, kein Heckdurchgang, expliziter Analyse-Cancel, erfolgreicher Save/Checkpoint. B70: diagnostisch (`manifest_compatible=false`), expliziter Analyse-Cancel; terminal beide Actions leer und alle vier Befehlsausgänge null; Save konkret unterhalb der 512-MiB-Mindestreserve verweigert. Seine beiden erfassten Abfahrtsprüfungen waren positiv; daraus ergibt sich keine vollständige Missionsfreigabe. Der frühere `b70-partial-affected.log` enthält nur einen ungültigen Testpfad und **keine ausgeführten Tests**; das wird durch v19 transparent ersetzt, nicht als grün gezählt. Große unveränderte synthetische Rohereignisse bleiben verlustfrei komprimiert im Scratch-Verzeichnis.

Gesamtabnahme weiterhin **0/3**. Nächster Schritt laut STATUS: Teilbeobachtungs-/Wiederholungslogik mit dem belegten Planalternativenfehler schließen und gezielt regressionsprüfen; erst danach unveränderte Gesamtfälle auf einem finalen Kandidaten wiederholen. Kein Hardware-/Deployment-/Shutdownnachweis.

## V20 / B71 – Restbeobachtung, 06.10.2026

Softwarekandidat `17fba88d256711d7e64b881ac8c6fa62c400bf65`. `b71-progress-probe.json` prüft alle ursprünglichen Beobachtungspunkte auf zeitlich passenden B70-Rohkarten. Erste Baseline komplett, zweite mit genau einem unbekannten Originalpunkt. `b71-before-tests.log` erhält die rote Verhaltensgegenprobe mit ursprünglichen Kandidaten-/Runtime-Modulen; `b71-retained-selection.log` und `b71-native-plan-probe-original` belegen die anschließend sichere begrenzte Folgeposition mit ursprünglicher Task-ID/Historia. Analytisch abgelaufener ursprünglicher Cooldown ist Komponenteninput, kein Gesamtlauf. JSON/NPZ-Fixtures unter `src/explore/test/data/ap06_b70_after_observation.*` sind die gesicherten synthetischen Originaldaten. Negative Zwischenprüfungen erhalten: `b71-targeted-tests.log` (unrealistisch manuell konstruierte leere Sicht), `b71-trace-final-tests.log` (fehlender isolierter Testdomain); finale Fixtures verwenden unveränderte echte Decoder-/Isolationsregeln.

`native-final-v20-*`: Zwölfpaketbuild, 2.134 direkte Tests und 2.116 registrierte Tests grün, keine Skips. `native-identity-v20-bound.json` und `source-identity-v20.json` binden 136 ausgeführte Installdateien und 448 Quell-/Test-/Werkzeug-/Konfigurationsdateien an diesen Commit. Native Pluginidentität unverändert. `native-components-v20` belegt 9/9 native Bewegungs-/Sperrkomponenten. B72 läuft regulär ohne Diagnoseoptionen; noch keine Gesamtpositive.

`b71-inactive-build-caches.tar.manifest.json` enthält die vor Entfernung einzeln geprüften SHA256 der ausschließlich eigenen inaktiven regenerierbaren Build-Caches; verlustfreies Archiv außerhalb Git. `b71-storage-reclamation.json` unterscheidet das entfernte unbenutzte Docker-Tag von tatsächlichem Layerplatz: kein Layerplatz freigegeben. Die etwa 496 MB kommen aus den geprüften Build-Cache-Archivierungen. Keine Originalereignisse, Karten oder Softwareinstallationen gelöscht.

## B72/B73/B74 und V23 – präzisere zulässige Sichtwahl

B72 bleibt regulär negativ auf `17fba88`: drei Ankünfte/zwei Beobachtungen, ursprüngliches 5-s-Auswahlbudget, keine Passage. Endsave und exakter Checkpoint erfolgreich. B73 ist ausschließlich begrenzte Originalinputdiagnose (`manifest_compatible=false`), nach vier Ankünften/zwei Beobachtungen explizit analytisch abgebrochen. Beide vollständigen Events bleiben original verlustfrei komprimiert im Scratch; die kleinen Metadaten enthalten die unabhängig geprüften vollständigen Eingangsbytezahlen/-Hashes. Kein Gesamtpositiv aus diesen Läufen.

B73-Proben erhalten auch widerlegte Hypothesen: ursprüngliche dritte Punkte teils unbekannt/occluded, vierte Sicht am originalen Supercover ungültig; Punktunion, reine Completed-Vorfilterentfernung, Identity-/Receipt-Varianten und lokaler kleiner Rand lösen den Originalfehler nicht. Echte C++-Native-Probe der kleinen lokalen Randalternative lehnt den Sweep ab. Keine solche Variante installiert. B73-Randtangentenalternative bietet dagegen sieben endliche Potentialpunkte statt einem und bestand echte Native-Anfahrt, Abfahrt und Drehrefuge. Dies ist ein Komponentenbeleg, kein beobachteter Gewinn. Originale B73-Entscheidungsobjekte bleiben außerhalb Git. Testfixture `ap06_b73_before_last_view` enthält den ursprünglichen synthetischen Zustand einschließlich vollständiger Task-/Privathistorie und aufgezeichneter echter Native-Pläne.

B74-Zwischenversionen und V21/V22-Logs ausdrücklich negativ: zu breite Suche eröffnet alte A51-Erschöpfung neu. V21 2.135 bestanden/zwei Fehler; V22 nach bekanntem alten Erschöpfungsfehler durch eigenes SIGINT unterbrochen, keine abgeschlossene Vollprüfung/colcon-Zahl behauptet. Finale Korrektur `ea63493a464c11504bef16832b09936b567ae099` verbessert ausschließlich eine zuvor original zulässige Zielwahl im verbleibenden ursprünglichen Helperfenster; Lookup legt keine IDs an. B74-targeted-v4: **31 grün**, alte A51/B70/B68-Gegenfälle und vier neue Fälle. V23: **2.138 direkte Tests** (144,06 s), **2.120 registrierte Tests**, keine Fehler/Skips, **Zwölfpaketbuild 6,60 s grün**. Mengen überlappen. Native Bewegungs-/Sperrmatrix **9/9 grün**; Ergebnisse unter `native-components-v23/`.

`native-identity-v23-bound.json`: 136 installierte Produktdateien und ausgeführte native Binär-/SDKpfade. `source-identity-v23.json`: 449 ausführbare Quell-/Test-/Konfigurationsdateien, alle bytegleich zur Ausführungskopie. Nativer NavFn-Pluginhash nochmals auf tatsächlichen Dateibytes geprüft; MASTERPLAN und originaler Gesamtmanifest unverändert. Regulärer B75 läuft auf exakt diesem Kandidaten ohne Diagnoseoptionen; Abschlussstatus ausschließlich im aktuellen STATUS.

B75 endete regulär negativ nach ursprünglichen 900 s: 2 Ankünfte/2 Beobachtungen, 8 Versuche/0 Bewegungsfehler, 228 erreichbare Randzellen, 72,101 % Boden, kein Heckdurchgang. Tatsächliche Folgeplanung `footprint_sweep_invalid`, keine HWT-/Quellenstörung. Save/exakter Checkpoint positiv, beide Actions terminal und alle vier Befehle null. Trace 769.062.555 Eingangsbytes / 98.546.057 Gzipbytes, vollständige unabhängige Dekompressionsidentität positiv. B75-Frühere-Datenprobe bestätigt B73-Originalindex13 weiterhin verbessert, aber Index5 bleibt ein unbewiesener nativer Vorschlag; keine neue Produktvariante daraus. Eigener inaktiver SLAM-Build ohne Install-Symlinkbezug lossless archiviert und alle regulären Dateihashes vor rootseitiger Entfernung geprüft; Hostentfernung zuvor durch Eigentümerrechte verweigert, keine Install-/Binärdateien entfernt. B76 ist ausdrücklich Originalinputdiagnose, nicht abnahmefähig; aktueller Stand weiterhin 0/3.

## B76–B79 – Originale Pfostenablehnung und orientierte Planung

B76 ausschließlich Originalinputdiagnose, nach drei Ankünften/zwei Beobachtungen explizit analytisch abgebrochen. Gewinne 11/1/0, keine Passage. Quelle gesund; Mapsave und exakter Checkpoint positiv, alle Actions terminal und vier Befehle null. 221.669.641 Eingangsbytes / 27.481.202 Gzipbytes unabhängig vollständig verifiziert. `b76-native-plans-passive` enthält tatsächliche nur lesend abonnierte /plan-Meldungen; kein zusätzlicher Planner/Navowner. Die Probe `b77-first-sweep` reproduziert am vollständigen kohärenten B73-Snapshot14 den Original-Native-Pfadfehler: nominal früheste RPP-Hülle bei (1,1023 / −0,5029 / −0,0429) an raw-100-Zellen des unteren Türpfostens; nach zulässiger öffentlicher Vorausrichtung bei (1,2150 / −0,4599 / 0,1037) am oberen Pfosten (1,545 / −0,105), noch vor der Tür. Keine gelockerte Kontur, Tracking- oder Rasterreserve.

B77 nur Diagnose: separates echtes C++-Plugin mit kanonisch normierten bilinearen Offsets gebaut (14,1 s), derselbe Gegenfall bleibt negativ. Auch stock-Native-Dijkstra und nach Nav2-Gewichten rein geometrisch geglättete Wege bleiben negativ. Nichts davon produktseitig übernommen; C++-Diagnosediff ist ausschließlich Evidenz. B78 sampelt zusätzliche Zielrichtungen derselben lokalen Beobachtungsaufgabe mit analytisch abgelaufenem ursprünglichem Cooldown; keine tatsächlichen Budgets/Quittungen geändert. Mehr Potentialpunkte reichen nicht als echter Fortschrittsbeleg, keine solche Änderung übernommen.

B79 untersucht den vorhandenen Nav2-Smac-Planer für orientierte Fahrzeuge im isolierten Komponentenprüfstand. MASTERPLAN §3 verlangt gleiche Kontur und ausführbare orientierte Planung; AP-03 wählt eine konkrete vorhandene Kombination anhand der Fälle. Quelle weiterhin vorhandener gepinnter Navigation2-Baum; kein neuer Navigator/Supervisor/Fremdstack. Fehlende OMPL-Entwicklungspakete aus signiertem Ubuntu-Jammy-Archiv separat hinzugefügt; signed InRelease und Paket-SHA verifiziert, keine ROS-/Controller-/Kontur-/Fristparameter dabei verändert. Vergleich/Integration noch offen, weiterhin 0/3.
