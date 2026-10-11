# Prüfbericht zum LAB-Slotumbau vom 11.10.2026

Dieser Beleg gehört zum Produktquellstand
`12de37e89fed2a30d45fa3691919c2cc415560c9`, Branch
`feature/ap06-lab-slots`. Die spätere Dokumentation ist ein eigener Stand.
Den aktuellen Auftrag und genau nächsten Schritt ausschließlich im
[STATUS](STATUS.md) nachlesen. **Der Umbau ist implementiert und softwaregeprüft;
eine vollständige Erkundungsfahrt und die reale AP-06-Abnahme sind nicht belegt.**

## Umsetzung des Nutzerauftrags

Der vorhandene Explorer beginnt im LAB mit einer gemessenen vollen Drehung.
Die Entscheidung dafür wartet nicht auf freie Kartenpixel, Frontierauswahl,
Tür-/Raum-IDs oder den Abgleich einer neuen Karte mit dem Kartenmanager.
Antrieb, aktuelle Quellen, Pose, Schutzkette und die freigegebene Bereichsgrenze
werden weiter geprüft. Ein tatsächlicher Schutzstopp bleibt wirksam.

Anschließend gilt: bestätigter Halt → Beobachtung und Planung → ein Nav2-Ziel
→ terminales Kind und bestätigter Halt → nächste Beobachtung. Die teure
Rasterauswertung und Kandidatensuche laufen im Stillstand. Sensoren, SLAM,
Nav2 und LiDAR/VL53-Hindernisreaktion arbeiten während der Fahrt weiter.
Neue normale Kartenmeldungen lösen keine fortlaufende Explorer-Zielsuche und
keinen Kindabbruch allein wegen des ausstehenden Kartenstatusabgleichs aus.

Gewöhnliche Anfahrfehler beenden im LAB nicht mehr die Mission allein über
den globalen Einzelzielfehlerzähler. Der Explorer prüft andere Anfahrpunkte,
behält aber räumliche Versuchshistorie, ursprüngliche Fristen und Aufgabenlimits.
Kurze Quellenlücken halten dieselbe Aufgabe zur erneuten Prüfung offen.
Ein unabhängiger neuer Fehlername erneuert dabei keine laufende Wartefrist.
Erst tatsächlich gesunde Quellen und qualifizierter Stillstand beenden eine
zusammenhängende Quellenlücke.

Der Wiederprüfzeitraum beträgt standardmäßig 30 s, maximal 60 s und liegt
innerhalb der bisherigen Missions-/Aufgabenfrist. Nach einer unterbrochenen
Drehung bleibt der gemessene Restwinkel erhalten. Bei ausbleibendem Ziel kann
ein begrenzter Beobachtungsschwenk neue Sicht schaffen. Er ist kein erfundener
Kartengewinn. Gleich gebliebene Kartenpublikationen lösen keine erneute teure
Suche während der bestehenden Abkühlfrist aus.

„Reset“ verwirft hier Pläne. Not-Aus, gelatchte Encoder-/HWT-Fehler,
ungeklärte Kinder, Quellenstempel, Zähler und Budgets werden nicht gelöscht.
Die beiden vorderen VL53 begründen keine blinde Rückwärtsfahrt. Eine jederzeit
garantierte Befreiung aus jeder Geometrie ist damit nicht behauptet.
Der vollständige Ablauf steht in [LAB_SLOTS](LAB_SLOTS.md).

## Quellen und Architektur

Istbasis des Umbaus ist Dokumentation `8d72876`, sensorüberwachtes Produkt
`51f8e862`. Die Lieferung erhält Mission → C++-BT → Explorer → Nav2 → Schutzkette.
`lab_slots_runtime.py` wird innerhalb desselben ExploreArea-Besitzers aufgerufen;
es gibt keinen zweiten Navigator, Supervisor oder zusätzlichen Motorpfad.
Das bestehende Drehverfahren und die NavigateToPose-/Cancel-/Haltkette werden
weiterverwendet. Der bisherige kontinuierliche Ablauf bleibt auswählbar.

Die gemeinsame Mapping-Auswahl lautet
`unknown_space_policy:=sensor_guarded execution_mode:=lab_slots`.
Sie koppelt Explorer, Nav2-Unknown-Zulassung und LiDAR/VL53-Schutzparameter.
Der Modus ist im echten ROS-Knoten schreibgeschützt. Motor-Opt-ins und der
rein lesende Vorlauf bleiben getrennte technische Schritte.

## Build und Prüfaussage

| Prüfung | Ergebnis | Aussagegrenze |
|---|---|---|
| Unabhängiger Humble-/x86_64-Unterbau | 37 native Pakete gebaut | Kein ARM64-/Jetson-Build; keine Upstream-Unit-Testabnahme |
| Produkt | Bisherige 14 Pakete plus `robot_description`, insgesamt 15, gebaut | Keine reale Installation oder Autostartumstellung |
| Install-/Quellenbindung | 15 Produktpräfixe im getrennten Install; 163 Dateien bytegleich; 15 tatsächlich importierte Module einschließlich C-Erweiterung gebunden | Hardwaretreiber/I2C/USB und reale Optik nicht qualifiziert |
| Vollständige Regression des genannten Quellstands | **3.120 bestanden**, 0 Fehler/Skips: 3.033 Produktpaketfälle und 87 Simulationswerkzeugfälle | Softwaretests; keine ganzen Fahrmissionen |
| Gezielter Abschluss | **61 bestanden**, darunter 33 LAB-Fälle | Teilmenge der Regression; nicht addieren; Bewegungs-/Planertransporte in Elternablauftests ersetzt |
| Ursprüngliche Blocker vor Korrektur | Drei Gegenfälle am installierten `51f8e862` negativ | Keine Hardwaremessung |
| HOLD-Ursachenkette vor Korrektur | Ein neuer Gegenfall am Helper `084ac5c` negativ, danach positiv | Parent zum Vorstand bytegleich; kein vollständiger älterer Produktneubuild |

Die drei alten Blocker waren: kein Rundblick vor Kartenjoin, Kindabbruch allein
bei normalem Kartenjoin während der Fahrt und Missionsende am globalen
Einzelzielfehlerlimit. Zusätzlich zeigte ein realer geschlossener Diagnoseversuch,
dass eine spätere Pose-Lücke den vorherigen HOLD-Auslöser in der Metrik überdecken
konnte. Der neue Gegenfall reproduziert genau diese falsche Ursachenzuordnung.
Scan-/Kindresultat, erster Auslöser, Wiederprüfung und terminaler Grund bleiben
jetzt getrennt erhalten.

Der erste breite Zwischenlauf hatte 58 fehlende Prüfbaumdateien und eine
nicht bestandene DDS-Zeitprüfung. Die 59 betroffenen Fälle
bestanden separat nach Ergänzung des vollständigen Prüfbaums. Dieser
Zwischenlauf wird nicht als vollständiger grüner Abschluss gezählt. Maßgeblich
ist die abschließende einheitliche 3.120er-Regression. Originale Zwischenlogs
und JUnit-Dateien bleiben in den Rohbelegen erhalten.

Die zehn ursprünglichen Archivpins, SHA256 und Patches bleiben unverändert.
Zwei Nav2-Paketpfade waren im bisherigen Lock falsch: `nav_2d_msgs` und
`nav_2d_utils` liegen unter `nav2_dwb_controller/`. Diese Pfade sind korrigiert;
die Quellvorbereitung prüft jetzt jede deklarierte `package.xml` und wurde
offline erneut ausgeführt. Zusätzlich fehlende normale Distributionsstützen
(`bond`/`bondcpp`/`smclib`, `diagnostic_updater`, BT.CPP v3) wurden aus separat
gepinnter öffentlicher Quelle gebaut. `nav2_behaviors` verwendet denselben
Nav2-Pin. Einzelheiten, Versionen und Hashes stehen im
[maschinellen Beleg](evidence/ap06-lab-slots-20261011.json).

## Ursprüngliche geschlossene Gesamtfälle

Alle fünf Fälle wurden nacheinander gegen denselben finalen Quell-/Installstand
ausgeführt. Die Originalwelt, 2160-Strahl-Produktprofil, Mastmaske, Startposen,
endlichen Nah-/Tiefensensoren, Budgets und Abnahmekriterien bleiben bytegleich.
Echte Nav2-/SLAM-/EKF-/BT-Komponenten laufen; ausschließlich die Geräteendpunkte
sind modelliert. Kein Wahrheitskarten-/Wahrheits-TF-Publisher und kein manuell
gesendetes Navigationsziel.

| Fall | Tatsächliches Ergebnis | Was dadurch offen bleibt |
|---|---|---|
| `door68_start_a` | Timeout `SLAM initial actual map`, vor Missionsstart | Rundblick, Fahrt, 68-cm-Passage und Kartierungsabschluss |
| `door68_start_b` | Timeout `real scope and HWT readiness`, vor Missionsstart | Rundblick, Fahrt, 68-cm-Passage und Kartierungsabschluss |
| `door80_start_c` | Timeout `SLAM initial actual map`, vor Missionsstart | Rundblick, Fahrt, 80-cm-Passage und Kartierungsabschluss |
| `cancel` | Timeout `real scope and HWT readiness`, vor Bewegung/Injektion | Cancel-Halt nach begonnener Bewegung |
| `gyro_hold` | Timeout `real scope and HWT readiness`, vor Bewegung/Injektion | HOLD-Halt und vollständige Fortsetzung |

**0/3 positive Gesamtfälle qualifiziert; Cancel/HOLD 0/2 neue Qualifikationen,
beide ohne ausgeführte Injektion.** Das ist kein belegtes Versagen des Stopps
nach Bewegung, weil die Bewegung nicht begonnen hat. Die historischen v17-Werte
2.976 Regressionen / A–C 0/3 / Cancel-HOLD-Stopp 2/2 gehören weiterhin allein
zum damaligen ARM64-Stand. Sie werden nicht auf diesen Kandidaten übertragen.

Im finalen B-Lauf ist eine Encoder-Messlücke von **0,8266 s** dokumentiert;
im Cancel-Fall **0,1857 s**, im HOLD-Fall eine Paarlesung von **0,3271 s**.
Die ursprüngliche Radkontinuitätsgrenze ist 0,18 s. Die Quellen sperren deshalb
teilweise bereits vor dem Explorerauftrag. Einzelne Geräte-Executoraufrufe
dauerten 0,31–1,36 s. Diese Daten beweisen Zeitlücken in diesem Prüfstand;
sie beweisen noch nicht, welcher Produzent, Publikationsweg oder Scheduler
sie verursacht und ob derselbe Fehler am Jetson auftritt.

Ein vorheriger Diagnoseversuch am `084ac5c` erreichte den Slotstart und maß
0,005892 rad Drehung, bevor `hwt_terminal` beendete. Das ist weder eine volle
Drehung noch eine Erkundungsfahrt. Drei gemeinsam genutzte CPUs und eine
separate asynchrone ROS-Publikationskonfiguration lieferten ebenfalls keinen
Positivnachweis. Diese Versuche sind getrennte Diagnosen; die XML-Konfiguration
wurde nicht in den Produktstart übernommen. Quellen-/Frischegrenzen oder
Fehlerflags wurden für keinen dieser Versuche gelockert.

## Rohbelege und Übergabe

Der [maschinelle Beleg](evidence/ap06-lab-slots-20261011.json) bindet Commit,
Module, Quelldateien, Abhängigkeiten, Testzahlen, Ergebnisdateien und Grenzen.
Vollständige JUnit-/Buildlogs und alle Prozess-/Sensor-/Pflanzen-/Ereignislogs
liegen separat unter `/workspace/ap06-audit-results/lab-published-raw/`;
übersichtliche Abschlussbelege unter `/workspace/lab-slot-results/`.
Das vollständige lokale Roharchiv ist `amadeus-lab-slots-rohbelege.tar`.
Quellbundle und Patch heißen `amadeus-lab-slots.bundle` und
`amadeus-lab-slots.patch`. Beides umfasst die Änderungen ab dem veröffentlichten
Dokumentationsstand `22a4b76`, einschließlich des sensorüberwachten Vorgängers.
Prüfsummen und ein lesbarer Verzeichnisindex liegen daneben.

Es gab keinen Jetson-Zugang, reale Aktorbewegung oder Installwechsel.
Der Quellstand ist lokal committet; kein neuer Push/Merge wurde ausgeführt.
Ein x86_64-Binärinstall darf nicht auf den ARM64-Jetson übertragen werden.
Der [Transferbeleg](../ROBOT_TRANSFER.md) beschreibt den separaten Zielbuild,
Quellen-/Präfixbindung und Rückfall. Reale Karten/Bilder/Bags bleiben außerhalb
Git. Vollständige Fahr-, Tür-, Karten-, Stop-/Resume- und Kundenabnahmen bleiben
von dieser Softwareprüfung getrennt.
