# Wohnungserkundung – aktueller Status

## 11.10.2026 – LAB-Slots umgesetzt; Gesamtprüfung läuft

Aktiver Kandidat `feature/ap06-lab-slots`, Basis `8d72876` (Produkt `51f8e862`).
Der ausdrückliche Umsetzungsauftrag steht in MASTERPLAN v1.5 und
[LAB_SLOTS](LAB_SLOTS.md): fester gemessener 360°-Start ohne Kartenpixel-/Frontier-
Vorauswahl, danach bestätigter Halt/Beobachtung/Planung, ein Nav2-Ziel und Halt.
Sensoren und Schutzkette laufen durchgehend. Quellenlücken erhalten dieselbe
Aufgabe mit ursprünglicher Frist; gewöhnliche Zielprobleme suchen geprüfte
Alternativen. Fehlerflags, Quellenalter, Fehlversuche und Budgets werden nicht
zurückgesetzt. Unbestätigte Kinder, Not-Aus und Vertragsfehler bleiben terminal.

Die drei ursprünglichen Blocker sind auf dem alten installierten Produktstand
reproduziert: kein Start vor Kartenjoin, Abbruch bei normalem Join während der
Fahrt und Ende am globalen Einzelzielfehlerlimit. Neue tatsächliche Elternabläufe
beheben diese Gegenfälle. Die gezielten Slot-, Parameter-, Launch- und Encoder-
Prüfungen bestehen. Vollständige Regression, separater Gesamtbuild und echte
Nav2-/SLAM-Missionen werden im gerätefreien Humble-x86_64-Prüfstand vervollständigt.
Ein erster breiter Lauf enthielt fehlende Dateien des unvollständigen Prüfbaums;
die 59 betroffenen Fälle bestehen nach Ergänzung separat. Noch kein vollständiger
einheitlicher neuer Prüf-/Buildabschluss und keine neue reale AP-06-Abnahme.

Kein Jetson-Zugang in dieser Arbeitsumgebung, kein Transfer/Autostartwechsel
und keine reale Aktorbewegung. Ursprüngliche A/B/C-/Cancel/HOLD-Kriterien bleiben
unverändert. Historische Zahlen unten gelten für ihre damaligen Quellstände.

**Genau nächster Schritt:** den separaten vollständigen Kandidatenbuild und
die zusammenhängende Regression abschließen; danach die unveränderten ganzen
Fälle mit `--unknown-space-policy sensor_guarded --execution-mode lab_slots`
ausführen und tatsächlichen Missionsabschluss, Kartenfortschritt, Kindende und
ersten Fehlergrund dokumentieren. LAB-1 erlaubt die beauftragte spätere Realprüfung
ohne neue Standardfreigaberunde; dafür ist tatsächlicher Zielsystemzugang nötig.

## Historischer sensorüberwachter Kandidat vor den LAB-Slots

## 11.10.2026 – sensorüberwachter Start als neuer Softwarekandidat

**Quellstand `51f8e862a92836a141b4fdc3a503c331671e6052`**, Branch
`feature/ap06-sensor-guarded-start`, Ausgangsbasis `22a4b76`.
Die ausdrücklich verlangte Nutzeränderung ist in [MASTERPLAN v1.4](MASTERPLAN.md)
und [Auftrag](AGENTENAUFTRAG.md) aufgenommen. Unbekannte Zellen werden im neuen
Modus zur Planung zugelassen, ohne die Rohkarte oder Beobachtungsnachweise zu
ändern. Private Startkörper-/Egress-Ausnahmen entfallen. Rundblick vor Zielsuche;
bei erkannter Drehblockade normale Beobachtungszielsuche. Gemeinsame Launch-
Auswahl bindet Explorer, Nav2 und LiDAR/VL53-Bremse. Rückfall über
`unknown_space_policy:=observed_only` nach bestätigtem Halt/Prozessende.

**395 gezielte Softwareprüfungen bestanden: 369 Regressionen einschließlich
25 neuer Bewegungs-/Konfigurationsfälle plus 26 Scope-Prüfungen.** Der tatsächliche
Elternablauf beginnt auf derselben zuvor blockierten unbekannten Startkarte mit
dem Scan vor jeder Zielsuche. Geprüft sind außerdem der vollständige Körperweg
aus unbekanntem Start, echte belegte Zellen, aktuelle LiDAR-Hindernispunkte,
veraltete Empfangs-/Quellzeiten, fehlende TF, ungültige Scans, Stop/Cancel und
ehrlicher Scanabbruchgrund. Testtransport und synthetische Sensordaten sind
kein realer Bewegungs- oder SLAM-Gewinnnachweis.

Vier betroffene Pakete separat unter Humble/Python 3.10 auf x86_64 gebaut;
10 geänderte installierte Dateien bytegleich, tatsächlich geladene Laufzeit,
Geometrie, Sensorprüfung und Nativkern aus dem neuen privaten Prefix.
Kein vollständiger neuer 14-Pakete-/Nav2-/SLAM-Build. Nachweis, Hashes und
zugängliche Rohlog-/JUnit-Pfade im
[Softwarebeleg](evidence/ap06-sensor-guarded-start-20261011.json).

**Offen:** ganze ursprüngliche A/B/C-Missionen und ganze Cancel/HOLD-Fortsetzung
mit dem neuen Modus, Jetson-Transfer und reale Schutz-/Fahrtabnahme. Kein realer
Roboterprozess oder Aktor gestartet; Bestandsinstallation nicht umgestellt.
Der letzte vollständige gemeinsame v17-Vergleich bleibt 2.976 Regressionen,
A/B/C 0/3 und Cancel/HOLD-Stopp 2/2. Diese Zahlen sind kein Ergebnis dieses
neuen Kandidaten. VL53 vorn und LiDAR-Mastmaske ergeben keine lückenlose
Rundum-/Bodenerfassung; tatsächliche Brems- und Sichtwirkung bleiben zu prüfen.

**Genau nächster Auftrag:** vollständigen Kandidaten separat bauen und die
unveränderten ursprünglichen A/B/C-/Cancel/HOLD-Fälle über den vorhandenen
Testdriver mit `--unknown-space-policy sensor_guarded` ausführen. Originale
Welt-/Sensor-/Abnahmekriterien behalten, tatsächliche Produktpräfixe binden,
Missionsabschluss/Karte/Kindende und ersten Fehlergrund auswerten. Danach den
exakt nachgewiesenen Kandidaten im bestehenden LAB-1-Umfang real prüfen;
Softwaretests allein erklären die Hardwareabnahme nicht für bestanden.

## Historischer vollständiger Vergleichsstand v17

**Neuester vollständig geprüfter gemeinsamer Stand: v17 / `60e894c`,
11.10.2026.** Separater ARM64-Build: 14 Pakete, 155 eindeutige bytegleiche
Quelle/Install-Dateien bei 157 Vergleichseinträgen. **2.976 Regressionen
bestanden; ursprüngliche ganze A/B/C-Missionen weiterhin 0/3.** Originale
Cancel-/HOLD-Stoppfälle 2/2; im HOLD-Fall nach Halt vier Ankünfte/drei
Beobachtungen, danach terminaler Kartenstatus-Joinfehler. Vollständige
Wiederaufnahme und reale Gesamtfahrt bleiben offen. Bestandsinstall und Main
unverändert. [Kritischer Buildreview](AP06_BUILD_REVIEW_20261011.md) und
[exakter v17-Beleg](evidence/ap06-correction-v17-20261011.json).

**Damals vorgesehene Ursachenprüfung zum v17-Stand:** A erste verworfene Rasterzelle samt Rastertyp und
Referenz; B/C tatsächlich späte Auswahl- und Callback-Arbeit; Joinfehler nach
HOLD-Fortsetzung getrennt zuordnen. Keine geänderten Grenzwerte oder neuen
gleichen Fehlversuche. Die nachstehenden Absätze bewahren die einzelnen
Korrekturen und früheren Vergleichsstände.

## 11.10.2026 – Wartefolge und wiederholte Zielidentität korrigiert; Gesamtprüfung offen

Getrennter Checkout, Fixbranch `fix/ap06-adaptive-cooldown-order`, Ausgangsbasis
`d2c6cfe`. Schritte 1/2: echte adaptive Auswahl vor Korrektur dreimal statt
einmal während derselben ursprünglichen Pause; danach 214 gezielte Fälle
positiv. Zeit-/Kontextpause liegt vor adaptiver Zielsuche, nach aktuellen
Schutzprüfungen. Neue echte Auswahl nach Pausenende, Cancel/HOLD/Quelle und
Kontext geprüft. [Gegenfall](evidence/ap06-adaptive-wait-order-20261011.json).

Instrumentierter geschlossener Vergleich aus `34fbad1`: negativ nach
0,191529 m, keine Ankunft/Beobachtung. Ereignisfolge: Encoderprobe nach
Verarbeitung veraltet, Route verworfen, anschließend getrennte VL53-Stempel
während Stillstand/Pause terminal behandelt. Kein harter Quellenfehler.
`9fb28f6` korrigiert das Veröffentlichungsfenster ohne künstlichen Match oder
Bewegungsrecht; zwei Gegenfälle zuvor negativ, danach 34 Wartefälle positiv.
[Nachweis](evidence/ap06-publication-wait-20261011.json).

Schritt 3: bei 53 live Eingangsprüfungen 135,763 ms Median/383,700 ms Maximum;
eine nach Verarbeitung erneut gebundene Encoderprobe war am Ende 201,456/
212,415 ms alt, über der unveränderten 180-ms-Grenze. Gemessene reine Arbeit
verkürzt: Körperzellen mit identischer Rechnung nur im konservativen lokalen
Fenster, genau eine inhalt-/geometrie-/Scope-/Kontext-/Körpermasken-gebundene
Known/Safe-Berechnung wiederverwendbar. Kein Gesundheits-, Routen- oder
Dispatchnachweis im Cache; tatsächliche Costmap und ganzer Egress weiter
geprüft. Auf eingefrorenen Eingaben mit tatsächlichem v10-Nativkern etwa
52,5 → 28 ms. 298 betroffene Fälle positiv; Körpermasken bitgleich, geänderte
Eingaben invalidieren, ursprüngliche Frischegrenzen auch bei Cachetreffern
wirksam. Kartenalter und Auswahl-Rechenbudget getrennt benannt mit identischem
bisherigem Grenzwert; aktuelle Alters-/Rechenzeitbelege im Produktstatus.
[Messung und Prüfung](evidence/ap06-input-geometry-20261011.json).

Geschlossener instrumentierter Vergleich aus `7c07641` regulär negativ:
0,526085 m, eine Ankunft/Beobachtung (176 Zellen), keine volle Passage. Bei
578 Eingangsprüfungen Median 85,357/p95 116,293 ms (zuvor 135,763/276,637),
aber weiter ein Frischeausreißer: erneute Probe vor 48,487 ms Maskenentzug
gebunden, anschließend 148,420 ms Egressprüfung; am Ende 200,735/209,135 ms
alt. Mehrere native Folgeziele ohne ursprüngliche Sicht am Haltepunkt, später
bewegte Folge wegen Kartenjoin unterbrochen; terminal 5-s-Auswahlbudget
überschritten. Kinder beendet, vier Kommandoströme null. Kein Stoppsignal
mehr gesendet: der Prozess war schon regulär beendet. Kein Gesamtpositivbeleg.

Die erneute tatsächliche Encoderbindung liegt jetzt nach reinem Maskenentzug,
weiter gegen dasselbe tatsächliche TF-Paar und die originalen 20-mm/0,05-rad-
Grenzen. Kein Stamp geändert, keine Pollschleife oder Frist verlängert. Echter
DDS-Gegenfall mit originaler vollständiger Methode zuvor negativ, danach
positiv; 149 betroffene Fälle sowie drei verstärkte aktuelle Paarfälle positiv.
[Zeitfolge/Gegenfall](evidence/ap06-late-wheel-binding-20261011.json).

Schritt 4: ursprünglicher Auslöser, begrenzte Folgereaktionen und terminaler
Grund werden jetzt unabhängig im Ergebnis erhalten; Scanwinkel/-dauer/-Sollrate
und erster Navigations-Stopgrund bleiben nachvollziehbar. 136 betroffene
Fälle positiv, einschließlich tatsächlicher Elternfolge mit verworfener nativer
Route und späterem Budgetende. Keine Entscheidungs- oder Budgetänderung.
Der ältere Zwei-Beobachtungs-Lauf zeigt 5,6421 rad in ungefähr 151 s,
etwa 18 s Stillstand und 0,03743 rad/s mittlere tatsächliche Drehung. Gemessene
Sollwerte 0,08/0,024 passen zum bestehenden SlowZone-Faktor 0,3; ohne volle
Monitor-Spur ist dessen Gesamtanteil nicht bewiesen. Drei aufeinanderfolgende
Beobachtungen fehlen weiter. [Kausalbeleg](evidence/ap06-causal-result-20261011.json).
Eine versuchte exakte Routenwiederverwendung brachte im Profil keine
Verbesserung (4,505 → 4,602 s) und wurde vollständig verworfen.

Gemeinsamer Kandidat v11 aus `b58b257` separat gebaut: 14 Pakete in etwa
173 s, 157 Quelle-Installgleichheiten, 756 Installhashes; sämtliche Produkt-
präfixe einschließlich Nativkern im neuen privaten Install. Vollregression:
**2.933 Fälle positiv**, keine Fehler/Skip. Ursprüngliche unveränderte A/B/C
weiter **0/3**: A 0,728097 m mit zwei Ankünften/Beobachtungen (176/4 Zellen),
B 0,311323 m ohne Ankunft/Beobachtung, C 0,712181 m mit einer Ankunft/Beobachtung.
A: Scan erreichte 6,29505 rad, meldete jedoch am ursprünglichen 150-s-Limit
unterbrochen; danach native Footprint-Verwerfungen, terminal 5,09361 s
Auswahlarbeit bei 2,02131 s Thread-CPU. B: erster Auslöser neue unbekannte
Fläche/Belegung im Egress, C: Scangeometrie nach 0,20730 rad ungültig; beide
terminal Auswahlbudget. Keine gemeinsame Ursache aller Schutztrigger bewiesen.
Alle Kinder terminal, vier Kommandoströme null. Keine reale autonome Fahrt.
[Gemeinsamer Build, Regression und Originale](evidence/ap06-correction-v11-20261011.json).
Alle 1.048 Bestandsinstallhashes gleich, Bestandsmain sauber/unverändert.

Weitere gemessene Schritt-3-Korrektur: echte adaptive Auswahl erneuerte
nach 2,0278 s optionaler öffentlicher Arbeit drei zusätzliche Helferfenster
von 0,5046/0,5029/0,5019 s. Der Gegenfall war vor Korrektur negativ. Die
bestehende 2-s-Zuteilung wird jetzt pro Auswahl gemeinsam verbraucht; das
ursprüngliche harte 5-s-Auswahlbudget und alle Frische-/Aufgaben-/Gesamtgrenzen
bleiben unverändert. Eingefrorene originale Auswahl 4,5049 → 2,9637 s,
identisches Ziel, 102 Punkte und vollständiger Evidenzhash. 180 betroffene
Fälle positiv. Kein Routen-/Quellen-/Fahrrecht zwischengespeichert.
[Budgetgegenfall](evidence/ap06-optional-geometry-budget-20261011.json).
Kopiervermeidung, Routenreuse und Rasterpaar-Zusammenfassung ohne klaren
Gesamtgewinn verworfen. Keine neue gemeinsame oder reale Abnahme daraus.

Gemeinsamer Kandidat v12 aus `f7138cf` separat gebaut: 14 Pakete, 157
Quelle-Installgleichheiten und 756 Installhashes. Vollregression: **2.936 Fälle
positiv**, keine Fehler/Skip. Ursprüngliche unveränderte A/B/C weiter **0/3**:
A 0,150076 m ohne Beobachtung; B 1,272521 m mit drei selbst gewählten
Beobachtungen; C 0,697345 m mit einer Beobachtung. B schloss den optionalen
Rundblick mit 6,29647 rad in 149,979 s ab, erreichte aber keine volle Passage.
A: erster Egress-Trigger neue unbekannte Fläche/Belegung, terminal 5,04335 s
Auswahlarbeit trotz nur 0,01316 s optionaler Helferarbeit. B: zuerst keine
ursprüngliche Sicht am nativen Haltepunkt, später Auswahlbudget. C: reale
simulierte Encoderprobe am Ende 172,373/180,795 ms alt, danach begrenzte
Revalidierung und eine Beobachtung, terminal 5,11247 s Auswahl. Keine harte
Quellenstörung und kein Gesamtpositivnachweis. Alle Kinder terminal, vier
Kommandoströme null. [V12-Build und Originale](evidence/ap06-correction-v12-20261011.json).
Bestandsmain unverändert/sauber, alle 1.048 Bestandsinstallhashes gleich.

**Veröffentlichung:** Implementierung und bisherige Belege wurden ohne Force
auf `feature/ap06-closed-product-validation` übertragen; Remote-HEAD
`f7138cfbd38d58462040174203a278d8231bb18e` am 11.10.2026 um 06:09:17 UTC
mit `ls-remote` bestätigt. 22 geänderte Dateien geprüft, keine Geheimnistreffer;
nur eigene synthetische binäre Gegenfallraster. Der V12-Nachtrag ist neu.

Weitere Schritt-4-Korrektur: das gemeinsame `/plan`-Topic konnte während
rein lesender ComputePath-Anfragen als aktiver Navigationspfad gebunden werden.
Drei Gegenfälle vor Korrektur negativ, einschließlich tatsächlicher adaptiver
Auswahl/Elternfolge. Jetzt nur Topic-Updates des gleichen aktuellen Nav2-Kindes;
Dispatch-Stempel schließt wartende alte Query-Veröffentlichungen aus. Der
explizite Query-Rückgabepfad bleibt vollständig geprüft. 174 betroffene Fälle
positiv, keine Grenzen verändert. Im älteren Original A war der verworfene
Task-4-Pfad allerdings gleich dem Query-Pfad: keine Behauptung, dieser Rollenfehler
erkläre jene Verwerfung oder alle Abbrüche.
[Gegenfall und Quellenbindung](evidence/ap06-plan-publication-owner-20261011.json).

Weitere Schritt-4-Korrektur: fünf identische rein lesende native Pfade bei
unveränderter Karte im instrumentierten Source-A-Diagnoselauf. Derselbe bereits
abgelehnte Zielpunkt wurde einem näheren unversuchten Frontier zugeordnet;
unterschiedliche Ortsfenster-Hashes erschienen fälschlich als neue Messung.
Zwei tatsächliche Gegenfälle zuvor negativ, einschließlich originaler adaptiver
Auswahl mit aufgezeichneten synthetischen Eingaben. Jetzt priorisiert ein exakt
bereits versuchter Zielpunkt seine ursprüngliche Historie/Messfenster; echte
andere Querypositionen und endliche neue abgeschlossene Sichten bleiben möglich.
110 und 104 betroffene Fälle positiv (getrennte Suiten mit Überschneidung),
originale Cooldowns/Zähler/Fristen unverändert. Keine Bewegungsfreigabe daraus.
Diagnoselauf nach ausreichender Aufzeichnung über seine eigene eindeutige PID
geordnet abgebrochen: eine Beobachtung/0,296201 m, kein Manifestnachweis;
unvollständiges Resultat und Reporting-KeyError getrennt erhalten. Zusätzlicher
Hashcache und größere Nativbatch ohne zuverlässigen Gesamtgewinn verworfen.
[Gegenfall und Grenzen](evidence/ap06-exact-query-identity-20261011.json).

Gemeinsamer Kandidat **v13 aus `a4b4e35`** separat gebaut: 14 Pakete in
170,906 s, 157 Quelle-Installgleichheiten und 756 Installhashes; ursprüngliche
Paket-/Nativpräfixe eindeutig im privaten Kandidaten erfasst. Vollregression:
**2.946 Fälle positiv**, keine Fehler/Skip. Originale unveränderte A/B/C
weiter **0/3**: A 1,201621 m/zwei Beobachtungen, B 0,353843 m/eine Beobachtung,
C 0,702971 m/eine Beobachtung. A/B zuerst keine ursprüngliche Sicht am nativen
Haltepunkt; C dort 108 von 128 Sichtpunkten, jedoch anschließende bekannte
Route unzulässig. B terminal 5,539640 s Auswahl bei 2,185857 s Thread-CPU,
C 5,000319 s bei 1,970833 s; kein gemeinsamer universeller Trigger bewiesen.
A: optionaler Scan nach 6,104092 rad/150,789 s unterbrochen; anschließend
frische Auswahl innerhalb des Budgets und zweite Beobachtung. Terminal
`hwt_terminal`: Fahrtor wählte eine 184,949 ms alte Encoderprobe bei 180-ms-
Grenze; Raw/Gyro am ersten Fehler frisch. Quellenprozess gleichzeitig über
208–215 ms verzögert, wenig eigene Thread-CPU; Ursache dieser Pause nicht
bewiesen. Keine Behauptung eines realen Encoder-/Modbusdefekts.

Originale geschlossene **Cancel und Gyro-HOLD 2/2 positiv** mit gleichem v13:
Cancel → Stillstand 0,354443 s, terminal 0,631966 s; HOLD → Stillstand
0,259884 s. Der HOLD-Fall qualifiziert ausdrücklich keine Wiederaufnahme;
betroffene Wiederaufnahme-/Speicher-/Schutzregressionen sind im gesammelten
2.946er-Lauf enthalten. Sämtliche Kinder terminal, vier Kommandoströme null.
Keine reale autonome Fahrt, kein dreiminütiger Realvorlauf aus diesem Stand.
[Gemeinsamer Build, Originale, Schutzfälle und Ursache](evidence/ap06-correction-v13-20261011.json).

Zusätzliche negative Budgetdiagnose ohne Manifestabnahme: tatsächlicher
gekappter Historienaufruf nach 5,390469 s/2,189939 s Thread-CPU gesichert;
38,231 ms zusätzliche Diagnosekopie transparent erhalten. Exakter privater
v13-Replay mit dessen Nativkern findet nach 3,594412 s einen reinen Nav2-
Vorschlag, 90 Punkte und gebundenen Hash, keine Bewegungsfreigabe. 2.254
Signaturprüfungen kumulativ etwa 0,754 s und acht Inhalts-Hashes etwa 0,704 s.
NumPy-Vollvergleich 5,187600 s/Budgetfehler und nativer Bytevergleich
3,738922 s mit gleichem Kandidaten ohne Gesamtgewinn; beide verworfen.
Zwei private Wrapperfehler vor Graphstart getrennt dokumentiert. Gesicherte
Inputs/Profile bleiben lokal; reale Karten/Bilder/Bags werden nicht hochgeladen.

**Veröffentlichung:** Produktfixes bis `a4b4e355d54f17b4195331faf0ad6be413f56a50`
am 11.10.2026 um 07:04 UTC auf AP-06-Featurebranch bestätigt. Dieser v13-
Ergebnisnachtrag enthält ausschließlich Dokumentation; gemeinsame Build-/
Testquelle bleibt `a4b4e35`. Bestandsmain sauber/unverändert, alle 1.048
Installhashes nach dem separaten Build identisch.

Weitere gemessene Schritt-3-Korrektur: Der echte adaptive Gegenfall mit
unbesuchtem Ziel und ausschließlich räumlich unbeteiligter Historie berechnete
elf lokale Hashes für eine Auswahl. Vor Korrektur negativ, danach nur der
endgültige ausgewählte Hash. Unbesuchte Preselection ohne versuchten Nachbarn
an **allen** geprüften Positionen benötigt keinen Historienvergleich; eigene
oder relevante Nachbarhistorie behält den tatsächlichen Hash. Jeder ausgewählte
Kandidat bekommt weiter seine vollständige aktuelle Kartenevidenz. 150 und
acht gezielte Fälle positiv, 151 eindeutige Prüfungen. Auf dem tatsächlich
aufgezeichneten terminalen B-Aufruf: acht → drei Hashberechnungen, etwa
3,594 → 3,032 s Profilzeit, identisches Ziel/90 Punkte/Evidenzschlüssel und
Ranking, gleicher v13-Nativkern. Einzelprofil ist keine Gesamtqualifikation.
[Gegenfall und Messung](evidence/ap06-relevant-history-digest-20261011.json).

Gemeinsamer Kandidat **v14 aus `a6d5bbd`** separat gebaut: 14 Pakete in
171,453 s, 157 Quelle-Installgleichheiten, 756 Installhashes. Vollregression:
**2.954 Prüfungen positiv**, keine Fehler/Skip. Ursprüngliche A/B/C weiter
**0/3**: A 0,715282 m/zwei Beobachtungen, B 1,282187 m/**vier** Beobachtungen,
C 0,714659 m/eine Beobachtung. A zuerst Scan nach 0,660620 rad/28,100 s wegen
Footprint ungültig; B zuerst `map_status_join_pending`; C zuerst keine Sicht
am nativen Haltepunkt. Drei getrennte Auslöser, terminal jeweils unverändertes
5-s-Auswahlbudget: 5,276156/5,000409/5,737415 s bei 1,997423/1,977971/2,230855 s
Thread-CPU. Kein ursprünglicher vollständiger Missionsabschluss daraus.
Originale Cancel/HOLD **2/2 positiv**: Halt nach Cancel-Injektion 0,347173 s,
nach HOLD 0,309861 s. HOLD setzte anschließend mit zwei Beobachtungen fort;
der unveränderte Fall bewertet ausdrücklich nur HOLD/Stopp und weist
`hold_resume_qualified=false` aus. Vollständige Wiederaufnahmeabnahme offen.
Vier Kommandoströme null, Kinder terminal; alle 1.048 Bestandsinstallhashes
identisch, Bestandsmain sauber. Keine reale autonome Fahrt.
[V14-Build, gesamte Regression und Originale](evidence/ap06-correction-v14-20261011.json).

Weitere gemessene Schritt-3-Korrektur: der echte eingefrorene Selector las
4.484 Raster für wiederholte Signaturen; Gegenfall vorher negativ. Eine reine
Routenberechnung teilt nun eine exakt erfasste Inhaltsbindung und prüft alle
Inhalte danach erneut, bevor eine Route zurückkommt. Geänderte Raster/Masken,
Pose-/physische Bewegungsbindung, Egress, Scope und Kontur-/Routenparameter
verwerfen die gesamte Auswahl. Keine Route, Quellenbewertung oder Bewegungserlaubnis
im Cache. 164 und elf gezielte Fälle positiv, 166 eindeutig (Überschneidung neun).
Drei gepaarte Profile mit demselben v14-Nativkern: 3,084/3,013/3,035 →
2,742/2,656/2,794 s; jeweils identisches Ziel/90 Punkte/Evidenzhash/Ranking.
Das sind reine eingefrorene Profile, keine aktuelle Quelle oder Mission.
[Gegenfall und Grenzen](evidence/ap06-route-proof-group-20261011.json).

Gemeinsamer **v15 aus `1d03a1f`**: 14 Pakete separat in 172,076 s gebaut,
157 Quelle-Installgleichheiten, 756 Installhashes. **2.965 Regressionstests positiv**,
keine Fehler/Skip. Unveränderte Originalmissionen weiterhin **0/3**: A 0,225799 m/
keine Beobachtung, B 0,363251 m/eine, C 0,715161 m/eine. A/B terminal Auswahlbudget
5,251736/5,953357 s bei 2,056967/2,224353 s Thread-CPU. C Auswahl 4,239189 s
innerhalb 5 s, danach terminal `nav2_plan_goal_stop_rotation_invalid`.
C zuvor eigener Scan nach 0,032602 rad/1,957792 s geometrisch abgelehnt, später
bekannte Abfahrt nicht verfügbar und zwei native Sweeps verworfen. Kein
vollständiger Rundblick oder ganzer Missionsabschluss. Cancel positiv, Halt
0,381296 s nach Einspeisung (exakter Wert im Beleg); **HOLD negativ**, ohne Bewegung
oder HOLD-Einspeisung: erster Eingang nach 479,330 ms Arbeit mit alter Körperscan-
Probe, anschließend Auswahlbudget 5,262765 s überschritten. Kein gemessener
HOLD-Stopp aus diesem Fall. Kinder terminal/vier Kommandoströme null. Alle
1.048 Bestandsinstallhashes unverändert, Main sauber. Keine reale autonome Fahrt.
[V15, exakte Quellen und Ergebnisse](evidence/ap06-correction-v15-20261011.json).

Die passive Prozess-CPU-Stichprobe in C umfasst 5,295 s mit 5,13 s Explorer-
Prozess-CPU, während die Auswahl selbst 4,239 s Wandzeit/1,675 s Thread-CPU
benötigt. Das Fenster beginnt 0,804 s davor und endet 0,251 s danach. Weitere
Threads verbrauchen messbar CPU; Ursache der Verzögerung, GIL-/Scheduleranteil
und alle anderen Fälle sind damit nicht bewiesen. Keine Sensorperioden oder
CPU-Zuordnungen verändert.

Schritt 2/4: ein konkreter Klassifizierungsfehler ist belegt. Die echte adaptive
Auswahl mit alternativem nativen Plan hat einen freien RPP-Translationssweep,
aber unzulässige Drehung am tatsächlichen Stop. Vor Korrektur terminal, ohne
Verbuchung als abgelehnter Vorschlag. Jetzt wird dieser geometrische Queryfehler
wie die vorhandenen Sweepfehler als `proposal_rejected` verbucht; ursprünglicher
Auslöser bleibt, aktueller Versuch zählt, kein Kind/Alignment oder Bewegung.
Reale Rotation bleibt abgelehnt. Falsche Frames und nicht endliche Planwerte
bleiben terminal. Gegenfall zuvor rot, danach grün; **281 betroffene Fälle positiv**.
[Gegenfall und Rückfall](evidence/ap06-native-stop-recovery-20261011.json).

Gemeinsamer **v16 aus `dc84753`**: 14 Pakete separat in 177,291 s gebaut,
157 Quelle-Installgleichheiten, 756 Installhashes; **2.969 Regressionen positiv**,
keine Fehler/Skip. Ursprüngliche vollständige A/B/C weiter **0/3**, je eine
Beobachtung und 0,293228/0,356163/0,713589 m. A zuerst kein Kandidatensichtpunkt
am nativen Stop, terminal unzulässige private Anfangsdrehung. B zuerst
Körperscan nach Verarbeitung 518,511 ms alt bei 345,784 ms Eingangsarbeit,
danach Auswahlbudget 5,239773 s/2,048424 s Thread-CPU. C zuerst Scan nach
0,070940 rad/2,337272 s geometrisch abgelehnt, danach Auswahlbudget
5,016257 s/2,016217 s CPU. Ursache aller Stopps weiterhin nicht gemeinsam
bewiesen. Originale Cancel/HOLD **2/2**, Cancel-Halt 0,401796 s; HOLD-Halt
0,311322 s nach HOLD, terminal `hwt_terminal`. Der ursprüngliche HOLD-Fall
qualifiziert ausdrücklich keine vollständige Wiederaufnahme. Alle vier
Kommandoströme null, Kinder terminal. Erster Testdriverstart scheiterte vor
Sammlung am bereits angelegten leeren Ergebnisordner; korrekt reparierter
Start, ursprünglicher Fehler und erfolgreiche Stufen separat erhalten.
Alle 1.048 Bestandsinstallhashes unverändert, Main sauber.
[V16-Build und Originalfälle](evidence/ap06-correction-v16-20261011.json).

Schritt 2/4: zweiter tatsächlicher Klassifizierungsgegenfall geschlossen.
Ein nativer read-only Plan kann eine unzulässige Anfangsdrehung im privaten
Startbestand enthalten. Die Drehung bleibt durch denselben vollständigen
Guard abgelehnt. Ihre Ablehnung wird jetzt innerhalb unveränderter Versuchs-
und Zeitlimits als verworfener Vorschlag verbucht, statt unmittelbar ohne
Folgeversuch terminal zu enden. Echte adaptive Elternauswahl/echter privater
Sweep vor Korrektur negativ, danach positiv; **193 betroffene Tests positiv**,
kein Alignment/Nav2-Kind oder Aktor aus dem Gegenfall. Harte Quellen-/Kontext-
fehler bleiben terminal. [Gegenfall](evidence/ap06-native-private-recovery-20261011.json).

Zusätzliche Timingdiagnosen sind keine Qualifikation: eine 1-ms-Pause zwischen
Executor-Dispatches spart CPU, verzögert aber während der Auswahl erzeugte
Nachrichten bis 243,039 ms; Ansatz verworfen. Null-Warte-Yield ohne Rechenzeit-
gewinn ebenfalls verworfen. Explorer-Hauptschleife unverändert. Gemessene
wiederholte reine Inhaltsprüfungen werden gezielt reduziert und auf echte
Änderungen an Raster/Referenz/Scope/Kontur geprüft. Originale Frischegrenzen,
CPU-Zuteilungen, 5-s-Auswahlbudget und Missionskriterien unverändert.

Schritt 3: tatsächliche adaptive Auswahl liest im aufgezeichneten synthetischen
B-Gegenfall noch 1.828-mal Rasterinhalte für wiederholte Bindung. Derselbe echte
Aufruf ist vor Korrektur am Arbeitszähler negativ. Jetzt teilen nur die reinen
Kandidaten desselben Threads/derselben Auswahl die vollständig geprüfte
Inhaltsbindung; vor Rückgabe vollständiger erneuter Audit ohne Cache. Raster,
Masken, Referenz, Bewegung, Egressgeneration/-gültigkeit, Kontur/Scope und
Geometrieparameter geändert: gesamte Auswahl verworfen. Bei Ausnahme Gruppe
und Memo freigegeben; nächste Auswahl frisch. Kein Gesundheits-, Routen- oder
Fahrrechtcache. **176 betroffene Prüfungen positiv**, zusätzlich erster
87-Fall-Vergleich positiv; Mengen überlappen. Drei native Vergleiche unter
unveränderter künstlicher 320-Hz-DDS-Last: 1.828 → 16 Inhaltsreads, median
3,908911 → 3,264769 s Wandzeit und 2,396170 → 1,997462 s Auswahl-CPU.
Ziel/90 Punkte/Evidenzhash gleich. Während Auswahl erzeugte Nachrichten p95
29,664–40,157 ms davor bzw. 34,209–42,881 ms danach, Maximum danach 104,589 ms.
Kein daraus abgeleiteter Produktquellen-, Missions- oder Realgesundheitsbeleg.
Executor, ursprüngliche Budgets und Schutzprüfungen unverändert.
[Gegenfall, exakte Vergleiche und Rückfall](evidence/ap06-candidate-pass-binding-20261011.json).

Gemeinsamer **v17 aus `60e894c`** abgeschlossen: 14 Pakete in 174,559 s,
157 Vergleichseinträge für 155 eindeutige Quelle/Install-Dateien, 756 Installhashes. **2.976 Regressionen positiv**,
keine Fehler/Skip. Beide Manifeste für 3.717 verfolgte Dateien identisch;
aktuelle erfasste Produktmodule/hashgebundener ARM64-Kern stimmen. Ursprüngliche
volle Missionen **0/3**, keine volle Passage/Heck und nur 0/1/1 Beobachtungen:

| Fall | Weg | Erster Auslöser | Terminaler Grund |
|---|---:|---|---|
| A | 0,203623 m | Egressroute: neue unbekannte Fläche/Belegung | `completion_raw_pose_not_observed_free` |
| B | 0,354768 m | Keine ursprüngliche Kandidatensicht am nativen Stop | Auswahlbudget 5,889749 s, CPU 2,257465 s |
| C | 0,707988 m | Scan-Footprint nach 0,192777 rad/4,083774 s ungültig | Auswahlbudget 5,707443 s, CPU 2,145290 s |

Keine gemeinsame Ursache aller Abbrüche bewiesen. A letzte Auswahl 3,361210 s
innerhalb Budget; sein Geometrie-/Abschlussfehler bleibt getrennt von B/C.
Die lokale Beschleunigung behebt die späteren Lastfälle noch nicht. Grenzen
oder Freiraum nicht erweitert. Cancel positiv, HOLD-Stopp positiv; gemessener Cancel-Halt
0,338385 s, HOLD-Halt ab HOLD
0,300974 s. Originaler HOLD-Fall ausdrücklich nur
Stopp, **keine vollständige Wiederaufnahme**. Nach tatsächlichem HOLD folgen
vier Ankünfte/drei Beobachtungen und 1,249039 m; terminal anschließend
`map_status_join_retry_budget_exhausted`. Dieser begrenzte positive Fortsetzungs-
verlauf ersetzt keine Original-Positivmission. Alle Kinder terminal, vier
Kommandoströme null. Bestandsmain `23928d9` sauber und alle 1.048 ursprünglichen
Installhashes unverändert. Kein realer Vorlauf oder autonome Realfahrt aus
dieser Umsetzung. Matrixdriver-Exit 0 bedeutet Ausführung, keine Missionsabnahme.
[Exakter v17-Build und Resultate](evidence/ap06-correction-v17-20261011.json).

Kritische Selbstprüfung samt Erkenntnisgrenzen und reparierter veralteter
Jetson-Kandidatenangabe:
[Buildreview](AP06_BUILD_REVIEW_20261011.md). Software `60e894c` bereits auf dem
Featurebranch bestätigt; dieser Audit ergänzt Dokumentation/Belege. Kein
Main-Merge oder dauerhafte Installation.

**Genau nächster Schritt:** A erste tatsächlich verworfene Rasterzelle samt
Rastertyp/Referenz messen; B/C tatsächlich späte Auswahlarbeit und Callback-
Verzögerung gezielt binden. Echte Gegenfälle vor weiterer Produktänderung,
keine unveränderten Fehlversuche oder pauschalen höheren Budgets. Danach ein
neuer gemeinsamer Kandidat mit ursprünglicher vollständiger Abnahme. Volle
Wiederaufnahme und reale Folge gemäß aktuellem Auftrag bleiben offen.
Rückfall begrenzte eigene Korrekturcommits revertieren/private Overlay-Abwahl.

## Historischer veröffentlichter Stand vor Umsetzung der Ablaufkorrektur

Der [aktive Auftrag](AGENTENAUFTRAG.md) enthält die aufeinanderfolgenden
Maßnahmen: Gegenfälle im tatsächlichen adaptiven Pfad, Warte-/Auswahlreihenfolge,
gemessene Zeitverarbeitung, Folgeplanung nach Beobachtung/Scan, gemeinsamer
Softwarekandidat und erst danach reale autonome Abnahme. MASTERPLAN v1.3 und
LAB-1 unverändert. Die Veröffentlichung behebt keine der offenen Ablaufprobleme.

V10 aus `2d93f2b`: 2.867 vollständige Produktfälle positiv, ursprüngliche
A/B/C weiterhin 0/3. Die danach entwickelte Wartekorrektur ist jetzt als
`09f866d` versioniert und bleibt unvollständig. 196 gezielte Fälle positiv; neuester
instrumentierter Source-A: 0,729335 m, zwei Ankünfte und Beobachtungen, negativ
am Auswahlbudget, kein Quellenfehler, keine Manifest-/Hardwareabnahme.
Zuvor optionalen Scan nach 5,6421 rad am Aufgabenbudget beendet und einen
Plan bei ungültigem Footprint-Sweep verworfen. Dies ist eine Ereignisfolge,
noch kein Beweis einer einzigen Ursache für alle Abbrüche.

Neuer **Codebefund**: Im adaptiven Pfad ruft `_metric_start_decision` bereits
die Zielsuche auf, bevor `_execute_metric_frontier` die neue Wartephase prüft.
Die neuen Eltern-Wartetests verwenden dagegen den Fixture-Default
`configured_scan`. Die behauptete Unterdrückung erneuter Suche ist somit für
den tatsächlich verwendeten Aufrufer nicht nachgewiesen. Ein ausführbarer
adaptiver Gegenfall und dessen Korrektur fehlen noch. **Messbefund**: Eine
Scanprobe alterte durch 425,467 ms Verarbeitung von 86,022 auf 511,489 ms,
oberhalb ihrer unveränderten 500-ms-Grenze. Das ist kein Beweis eines defekten
Sensors. Befunde/Hashes: [Audit](evidence/ap06-ablauf-audit-20261011.json).

**Veröffentlichung:** Der Nutzer hat nach der Planerstellung ausdrücklich die
Aktualisierung des Repositories beauftragt. Der vorhandene GitHub-Branch
`feature/ap06-closed-product-validation` wurde ohne Force-Push von `e14ca312`
auf `09f866d3a3e9bd7729ac4e052247b88fe43738ec` aktualisiert; `git ls-remote`
bestätigte den übertragenen Softwarestand. Enthalten sind die lokalen
Folgearbeiten sowie Plan/Analyse aus `79cd784`. Der vorliegende
Dokumentationsnachtrag ändert keine Produktdateien. Der ältere Auditbeleg
hält bewusst den Zustand vor Commit/Upload fest.

Vor Übertragung: 68 geänderte Dateien und 205 neue Blob-/Commitobjekte auf
gängige Geheimnismuster geprüft, keine Treffer; keine großen Objekte oder
erkannten privaten Aufzeichnungsdateien im Änderungssatz. Syntax und
Übereinstimmung der untersuchten Produktdateien mit den vorhandenen
Testnachweisen geprüft. Kein neuer Vollbuild oder neuer Gesamtmissionslauf
durch die Veröffentlichung, keine neue CI-Erfolgsbehauptung.
[Veröffentlichungsbeleg](evidence/ap06-publication-20261011.json).

Reale Schritte 3/4 weiter offen, keine neue Bewegung oder Installänderung.
Der begrenzte reale Punkt-1-Nachweis und dessen Rohdatenlücke bleiben bestehen.
Letzte Hardware-/Bestandsprüfung siehe unten; kein frischer Hardwarezustand
aus Simulationsresultaten abgeleitet.

**Genau nächster Schritt:** Schritt 1 des Korrekturplans: reproduzierbaren
Gegenfall mit echter adaptiver Startentscheidung hinzufügen, der vor der
Korrektur die zu frühe erneute Auswahl während der laufenden Pause zeigt.
Erst danach den Zustandsübergang korrigieren. Keine weitere Gesamtwiederholung
ohne gezielten neuen Befund. Rückfall: eigene kleine Diffs bzw. privates Overlay;
Bestandsinstall erhalten.

## Historischer v10-Prüfstand vor dem Ablauf-Audit

Punkt 1 bleibt begrenzt real positiv; Rohdatenlücke während Translation erhalten.
Punkt 2: gemeinsamer v10-Build `2d93f2b`, 14 Pakete in 172,54 s, 155
Quelle-Installgleichheiten/756 Installhashes. Vollständige 2.867 Produktfälle
positiv ohne Fehler/Skip. Ursprüngliche manifestgleiche A/B/C weiterhin 0/3:
0,293827/0,364219/0,710745 m, je eine Ankunft und Beobachtung (176/183/145
neue Zellen, C teilweise beobachtet). Alle enden am Auswahlbudget; keine volle
Passage samt Heck. C wieder mit mehr Fortschritt als v9, kein Gesamt-Grün.
Reale Schritte 3/4 nicht durchgeführt, kein Kunden-/Hardware-Abnahmebeleg.

v10 enthält getrennten Regionsfix `4f32555` und Wegfix `2d93f2b`. Unveränderte
physische Egress-Region bei vollständiger Extentdeckung ohne wirklichen Entzug
behalten; aktuelle Projektion/Historie weiter voll prüfen. 80 gezielte Fälle
und vier verstärkte Entzug-/Historienfälle positiv. Ungültiger subzelliger
Gegenfall bleibt identisch ungültig, Refresh 55,61 → 38,38 ms. Native Rückverfolgung
desselben Distanzfelds und bitgleiche Zellzentrenprojektion: 279 gezielte Fälle
positiv. Erste eigene Testdomain/Int8-Testannahmen korrigiert, Originalnegative
erhalten. Eingefrorene vollständige A-Auswahl 4,69 s, kein zulässiges Ziel;
Geometriediagnose ersetzt keine aktuelle Quelle oder geschlossene Mission.

Neue tatsächliche Ursachenprobe am aufgezeichneten A-Folgeinput: Privatabfahrt
weiter nötig; mehrere vollständige Vorwärtsrouten zwischen 0,30 und 0,55 m
zulässig. Aktuelle mögliche Sicht enthält 1/3/8 unbekannte Zellen. Bestehende
30-s-Nachbarschaftspause hält diese neuen Aufgaben noch zurück; nach originalem
Ablauf sind 5/8/9 Ansichten zulässig. Kein Timer erhöht oder vorgespult im Produkt.
Ohne korrekt behandelte Wartephase konsumieren ungeeignete Fernalternativen das
ursprüngliche 5-s-Auswahlbudget. Dies begründet den nächsten getrennten Fix,
keine aus dem eingefrorenen Input abgeleitete reale Bewegungsfreigabe.

Letzte tatsächliche rein lesende FC03 am 02:49:47 UTC: Zähler 35204/−35676
unverändert, Null-RPM, RAM 100/400/5, Lesungen 4,966/4,464 ms. Alle 1.048
Bestandsinstallhashes am 02:50:02 UTC gleich; Main sauber/unverändert. Keine
neue Hardwarebewegung, kein SDK-/OS-/Autostartwechsel. v10-Realstartskripte nur
vorbereitet. Bekannten festen LAB-Scope vor realem Start neu binden, nicht
umzentrieren. Passage-/Drei-Bereich-Aufbau und native Apple-Laufzeit nicht
erfinden. Bestehender LAB-1-Auftrag gilt ohne neue allgemeine Freigaberunde.

**Genau nächster Schritt:** bewiesene begrenzte Privatabfahrt, die nur auf die
ursprüngliche Nachbarschaftspause wartet, als wartende Arbeit behandeln statt
Auswahlbudget verbrauchen. Geometrie, echte Quellen, Cooldown, Versuchs- und
Gesamtfristen unverändert; keine gespeicherte Bewegungsfreigabe. Gezielt und mit
gleichen Originalmissionen prüfen, erst nach softwareseitigem Bestehen reale
3/4. Rückfall: nur eigenen Wartephasendiff revertieren oder eigene private PIDs
direkt geordnet stoppen und Bestandsinstall verwenden. Originalnegative und
reale Daten privat unter
`~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/`.

## Historischer v7-/TF-/Auswahlstand vom 11.10.2026

Punkt 1 bleibt begrenzt real positiv, mit erhaltener Rohdatenlücke während
Translation. Für Punkt 2 wird die nachgewiesene native IMU-Schreibpause im
vorhandenen Quellenpfad korrigiert: optionaler schreibgeschützter Startparameter
`isolate_sensor_output`, Default false. Wiederverwendung des vorhandenen
Encoder-Ausgabehelpers; Serializer/Spawn vor erster Erfassung, ein begrenzter
Ausgabeschlitz je bestehendem Topic, unveränderte Messbytes/Stempel und Sensor-
QoS (IMU best effort / Tiefe 5, Status/Diagnose reliable / Tiefe 10).
Genau ein DDS-Publisherbesitzer, eigenes Output-Kind ohne Bus oder Aktor.
Verlorenes Output-Kind verriegelt die passive Erfassung und schließt den
Transport; kein automatischer Neustart oder geheilter Quellenzustand.
Der gerätefreie Originalprüfstand wählt diesen vorhandenen Produktpfad explizit.
Reale Installation/Autostart und die Sensor-/Kontinuitätsfristen bleiben unverändert.

Tatsächlicher 350-ms-Schreibpausenvergleich mit gehaltenem GIL: direkter IMU-
Schreiber unterbricht Encoderkontinuität, isolierter Schreiber erhält gültige
Radproben und unveränderte Positionen. Alle 15 gezielten Helper-/IMU-/Quellen-
Isolationsfälle bestanden. Erste Testfassung enthielt zwei eigene Belegfehler:
kurzlebiges multiprocessing-Value vor Spawn verloren und native DDS-Graph-
Tiefenanzeige 0 statt lokaler Publisher-Konfiguration. Originalnegative erhalten;
Value-Lebensdauer korrigiert, tatsächliche im Kind erzeugten Publisher-QoS
separat ausgelesen, korrigierter Lauf 15/15. Keine Quellenwerte angepasst.
Vollständiger privater v7-Build `f8cedc1`: 14 Pakete in 2 min 51 s,
154 geprüfte Produktdateien Quelle/Install identisch, 755 Installhashes.
Voller Lauf 2.717 Fälle, ein Fehler im bestehenden DDS-Cancel-Gegenversuch:
Executor erreicht dessen Take-Barriere nicht. Originalnegativ erhalten;
unveränderte betroffene Datei erneut 4/4 bestanden. SDK-Befund:
`get_num_entities`/`add_to_wait_set` blockieren ebenfalls an seinem nativen
Registrierungslock, bevor `take_data` erreicht wird. Der korrigierte reine
Testnachtrag prüft tatsächlich nicht erwerbbaren Lock im Executor und hält
auch die echte spätere Cancel-Antwort / Goal-ID / Terminalität fest. Neuer
erzwungener Wait-Set-Gegenfall; betroffene Datei 5/5 bestanden. Alle 2.718
unterschiedlichen Produktfälle damit geprüft und positiv, kein behaupteter
erster vollständig grüner Volllauf und keine Fristverlängerung. Produktdateien
des Builds bleiben unverändert. Ursprüngliche A/B/C mit sauberer Quelle
`192ac68` nun beendet, alle manifestkompatibel und negativ: A 0,089590 m,
keine Ankunft/Beobachtung; B 0,365139 m, eine Ankunft/Beobachtung und 183 neue
Zellen; C 0,714527 m, eine Ankunft/Beobachtung und 145 neue Zellen. Alle
enden an `frontier_candidate_processing_budget_exhausted`, keine volle
Passage samt Heck. C erreicht zusätzlich nur 4,071 rad des zurückgestellten
Rundblicks vor `scan_task_budget_exhausted`. Keine neue reale Fahrt daraus.

Separater gemessener Empfangsfehler: trotz gültiger aktueller Encoderproben
lag die bereits gewählte TF-Pose in A/B/C 22,4–26,1 mm zurück. Tatsächlicher
DDS-Gegenversuch mit pausiertem Verbraucher: 29,9-mm-Abweisung vor Empfang,
identische Rad-/TF-Pose nach Übernahme wartender Originalnachrichten. Neuer
begrenzter Empfang über die bereits bestehenden TF-Subscriptions/Callbacks
vor gemeinsamer Pose/Referenzauswahl, keine neue Quelle oder Stempel.
Fehler beim Take sperrt ausdrücklich; fehlender Sender veraltet weiter.
25 gezielte Fälle bestanden, einschließlich echter DDS-Pause, Handleverlust
und paralleler Listenercallbacks. Privater nicht qualifizierender A-Vergleich
erreicht 0,284571 m / eine Beobachtung ohne Rad-TF-Abweisung; Empfang bis
1,535 ms, später weiterhin Auswahlbudget. Erste Diagnosekopie hatte ihren
Manifestpfad falsch auf das private Verzeichnis aufgelöst; Originalfehler
erhalten, expliziter Originalmanifestpfad korrigiert. Der neue TF-Fix ist
noch nicht gemeinsam gebaut oder als Originalgesamtmission qualifiziert.
Reale FC03 am 11.10. um 01:06:40 UTC: Positionen unverändert, beide RPM null,
RAM 100/400/5; alle 1.048 Bestandsinstallhashes um 01:06:34 UTC gleich.

Separate Auswahlkorrektur: exakte Kopien der beiden Egress-Ledger statt
wiederholtem Sortieren; geänderte Inhalte invalidieren weiterhin den Pass.
Startconnector-Suche auf umschließenden Rasterkasten des bestehenden Radius
beschränkt, mit zwei zusätzlichen Randzellen; ursprüngliche skalare
Projektion, Reihenfolge, Distanz-/Heading-/Linien- und volle Routenprüfung
bleiben. 121 gezielte Fälle positiv; finale Dictionary-Kopie zusätzlich
mit Pass-/In-place-/TF-Fällen nachgeprüft. Geometrischer Originalvergleich
A/C: 1,731→1,366 s und 1,769→1,199 s, Ziele/Beobachtungspunkte/Ranking/
Evidenzschlüssel exakt identisch. Frozenset-Zwischenfassung brachte keine
Gesamtbeschleunigung und wird nicht übernommen. Vergleiche sind reine
Geometrie, keine Quelle/Frische/Mission oder neue reale Bewegung.
Gemeinsamer neuer v8-Build und ursprüngliche A/B/C folgen.

Private Auslagerung von Egress-Geometrie ist nicht übernommen. Mehrkern-
Parentversuche enden mit nativer Explorer-Absturzaufzeichnung, darunter ein
Shutdown-Stack, der die ursprüngliche Ursache nicht beweist. Mit ursprünglichem
Ein-Kern-Explorer meldet die erste Transferfassung fehlende Kartenreferenz beim
Tuple-Deserialisieren; korrigierter ausdrücklich gebundener Transfer läuft,
bleibt aber negativ: 0 m, `start_motion_wheel_stale_after_processing`.
Eigene Rechenzeit 28–81 ms, gesamte gemessene Antwort 131–155 ms plus weitere
Parentprüfung. Keine Prozessauslagerung oder andere CPU-/Dispatcherdiagnose
als qualifiziert behaupten. Bestehender Scope-Cache ist bereits vorhanden.

Punkte 3/4 bleiben von bestandener ursprünglicher Softwaregesamtprüfung abhängig;
keine neue reale autonome Fahrt aus diesem Zwischenstand. Bekannte LAB-Kontur
nach gemessenem Fahrversatz fest neu binden. Weitere Passage-/Drei-Bereich-
Geometrie und native Apple-Laufzeit bleiben tatsächlich unbestätigt; bestehende
konkrete Rückfragen erhalten, keine erneute allgemeine Laborfreigabe.

**Genau nächster Schritt:** den separat geprüften gemeinsamen v8-Kandidaten
bauen, vollständige Regression und ursprüngliche A/B/C ausführen; nach
deren Bestehen die beauftragten realen Schritte 3/4.
Rückfall: eigenes privates Overlay direkt geordnet stoppen, Bestandsinstall
bewahren; IMU-Ausgabeopt-in zurücknehmen oder eigenen Fix gezielt revertieren.
Private Belege: `~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/simulation/`.

## Historischer v6-Quellen-/Dispatcherstand


Punkt 1 bleibt als begrenzte reale Anfahr-/Bremsqualifikation positiv beendet;
kein autonomer Realnachweis daraus. Punkt 2: vollständiger separater Build
`ap06-qualified-v6-20261011`, Produktquelle `cdf95b6`, 14 Pakete in 2 min 50 s,
154 geprüfte Produktdateien Quelle/Install identisch und 755 Installhashes.
Alle 2.715 Fälle der vollständigen Produktprüfung ohne Fehler/Skip bestanden.
Bestandsmain sauber, alle 1.048 geprüften Bestandsinstall-Dateien unverändert;
letzte zusätzliche FC03-Prüfung am 11.10. um 00:31:31 UTC ohne Positionsänderung,
beide RPM null, RAM 100/400/5. Kein Autostart-/OS-/SDK-Wechsel.

Der frühere v6-Vergleich vor der Prüfstand-Ausgabekorrektur bleibt erhalten.
Die drei ursprünglichen Gesamtmissionen mit unveränderter Welt, Startpose,
Sensorprofil und Budgets bleiben **0/3**: A 0,294290 m, eine Ankunft und eine
echte neue Beobachtung; B scheitert bereits an Scope-/HWT-Bereitschaft;
C 0,707064 m, eine Ankunft und eine neue Beobachtung. A und C enden später
an `frontier_candidate_processing_budget_exhausted`; C unterbricht vorher
zweimal wegen eines nach Verarbeitung veralteten Radsnapshots. Alle Strecken
dieses Absatzes sind gerätefreie Simulation, keine neue physische Fahrt.
Kein Fall räumt die Passage samt Heck; keine Gesamt- oder Kundenabnahme.

Zusätzliche, ausdrücklich nicht qualifizierende Diagnose: 307–314 ms lange
Quellenpause bei nur 24–31 ms Prozess-CPU. Drei aufeinanderfolgende native
Thread-Aufzeichnungen zeigen die Basis in `rclpy.publisher.publish` beim
Statusschreiben, gleichzeitig stehen IMU-/Plant-Verarbeitung. Mit dem bereits
real qualifizierten vorhandenen `isolate_feedback_output`-Pfad verschwindet
diese lange Erfassungspause und die Missionsphase wird erreicht; separate
Geometrie-/Auswahlfehler bleiben. Der Prüfstand verwendet diesen vorhandenen
Produktpfad nun ebenfalls, mit geerbter CPU-Affinität innerhalb seiner
gerätefreien Namespace-Grenze. Keine neue Transportimplementierung, keine
Stempel-/Frische-/Kontinuitätsänderung oder erfundene Zwischenprobe.

Gezielter tatsächlicher DDS-Schreibergegenfall: native 350-ms-Pause mit
gehaltenem Interpreterlock. Alter Prüfstand verwirft Encoderproben; korrigierter
Pfad erhält gültige Erfassung und unveränderte Positionen. Rot/Grün separat
erhalten, Grün 1/1; alle 28 betroffenen Quellen-/Isolation-/Welt-/Trace-/
Lifecycle-Fälle bestanden. Die gefrorenen Produktdateien des v6-Builds bleiben
unverändert. Neuer ursprünglicher Gesamtvergleich mit sauberer Quelle
`6c50cf5`, identischen 755 Installhashes / 154 Produktdateien, weiterhin **0/3**:
A scheitert an Scope-/HWT-Bereitschaft; B 0,354773 m, eine Ankunft / 183 neue
Zellen; C 0,704869 m, eine Ankunft / 144 neue Zellen. B/C enden später am
unveränderten Auswahlbudget; ein bzw. zwei vorangehende Geometrie-Neuprüfungen
wegen veraltetem Radsnapshot. Keine volle Passage samt Heck. Alle drei Läufe
manifestkompatibel, gerätefrei, ohne manuelle Nav-Ziele. Der Build bleibt
Produktquelle `cdf95b6`; `6c50cf5` ist der nachgeprüfte Prüfstand-/Test-/
Dokumentationsnachtrag, kein behaupteter neuer Produktbuild.

Weitere nicht qualifizierende Diagnose lokalisiert echte IMU-/Scan-
Publikationspausen von 323–343 / 329 ms. Ein ausdrücklicher nativer asynchroner
DDS-Vergleich verkürzt eine IMU-Pause auf 143 ms, hält den gemeinsam erfassten
Radpfad jedoch weiterhin 189 ms auf: nicht übernommen. Wiederverwendung des
vorhandenen Ausgabehelpers für die IMU mit ursprünglichem Sensor-QoS erhält
in einem privaten Vergleich 2.058 gültige Basiszustände ohne Verwerfung;
noch keine Produktintegration oder volle Lieferkontinuität daraus. Erster
CPU-Aufzeichnungsversuch scheitert an seiner eigenen nebenläufigen Deque-
Iteration; korrigierter Diagnoselauf und Originalnegativbeleg bleiben erhalten.

Korrigierte Messung: Auswahl 5,389 s Wandzeit / 2,053 s eigener Thread-CPU,
gleichzeitig 1,703 s Thread-CPU im ROS-Dispatcher. Eine gültige reine Radquelle
ersetzt keine rechtzeitige Geometrieentscheidung. Vier Explorer-Kerne,
begrenzter Neueste-Nachricht-Empfang, 1-ms-Dispatcherpause und drei statt sechs
Explorer-Worker ergeben keinen
vollständigen Positivlauf; keine dieser Diagnosevarianten wurde übernommen.
Frische, 20-mm-Abgleich, Kontur und Originalbudgets unverändert. Diagnosefahrten
zählen nicht als Positivfall und sind keine neue reale Fahrt.

Punkt 3 (regulärer autonomer Realstart) und Punkt 4 (erweiterte reale Abnahmen)
stehen weiter aus, bis Punkt 2 bestanden ist. Bekannte physische LAB-Kontur
nach gemessenem Fahrversatz neu binden, niemals umzentrieren. Weitere reale
Passage-/Drei-Bereich-Geometrie und natives Apple-Ziel sind noch nicht belegt;
einmalige konkrete Rückfragen stehen aus. LAB-1 und erneute Nutzerfreigabe
gelten weiterhin, keine neue allgemeine Freigaberunde.

**Genau nächster technischer Schritt:** gemessene Quellen-/Dispatcher-Konkurrenz
gezielt entkoppeln und die ursprüngliche Quellen-/Geometriebinding dabei
nachweisen, dann den
unveränderten ursprünglichen A/B/C-Vergleich bestehen und die beauftragten
realen Schritte 3/4 fortsetzen. Rückfall: eigenes privates Overlay geordnet
beenden; Bestandsinstallation erhalten. Prüfstanddelta gezielt rücknehmbar.
Private Originale und Rot/Grün: `~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/`.

## Historischer v5-Zwischenstand vom 11.10.2026

Punkt 1 bleibt als begrenzte reale Anfahr-/Bremsqualifikation beendet, mit
Positionsencodern, tatsächlichen FC03/FC06-Belegen und unabhängigem LiDAR-Vergleich.
Keine autonome Produktabnahme daraus. Der ursprüngliche Rohdatenrecorder verfehlte
insbesondere die Translation; diese Sichtlücke und die alten negativen Läufe bleiben
im Protokoll ausdrücklich erhalten. Letzte rein lesende Hardwareprüfung um
22:56:56 UTC: unveränderte Positionen, beide RPM null, RAM 100/400/5.
Alle bewegten Vergleichsfälle dieses Abschnitts sind gerätefreie Simulationen.

Punkt 2: Kandidat `ap06-qualified-v5-20261011` baute 14 Produktpakete in
2 min 50 s, 154 geprüfte Produktdateien Quelle/Install identisch, 755 Installhashes.
Produktbuild `205c2c4`, Testwrapper-Nachtrag `94ba58e`; unveränderte Produktdateien
nachgewiesen. Volllauf mit 2.714 Fällen enthielt zunächst zwölf Fehler eines
Wrappers ohne den neuen optionalen Parameter. Reparierte Datei: 62/62 bestanden;
alle zwölf negativen Fälle erneut geprüft, alle 2.714 eindeutigen Fälle bestanden.
Der ursprüngliche negative Volllauf wird nicht ersetzt. Einheitlicher privater
nativer ARM-Unterbau und tatsächliche SDK-/Pythonauflösung bleiben gebunden;
Bestandsmain sauber und alle 1.048 geprüften Bestandsinstall-Dateien unverändert.

Drei ursprüngliche Gesamtmissionen v5 weiterhin **0/3**, bei unveränderter Welt,
Startpose, 2-s-Beobachtungsfenster, 5-s-Auswahl-/Kartenfrist, Sensor- und Gesamtbudgets:
A 0,164762 m, 1 Ankunft/1 Beobachtung (174 echte neue Zellen); B 1,243869 m,
2 Ankünfte/2 Beobachtungen; C 0,259991 m, 0 Ankünfte/0 Beobachtungen. Alle endeten
später am Auswahl-Rechenbudget, kein Fall räumte die Passage samt Heck.
B-Rundumbeobachtung nur 5,00455 rad bis zum 150-s-Aufgabenbudget, kein voller
Positivscan. C verwarf während der Fahrt einen nach Verarbeitung veralteten
Radsnapshot und hielt an; danach eine Geometrieablehnung. Quellenfrische oder
Ankunftstoleranzen werden daraus nicht gelockert.

Die gebündelte identische Strahlprüfung beseitigt den bisherigen ersten Null-
Beobachtungsbefund in A. Ein zusätzlicher Diagnoselauf mit Entscheidungsaufzeichnung
scheiterte dagegen bereits an Radbereitschaft: echter 346-ms-Plant-/Quelle-Aussetzer,
kein Auswahl-Pickle und kein neuer Missionsbeleg. Eine Explorer-Verteilung auf
Kerne 3/4 brachte bei 11 bestandenen Isolationstests keinen Gesamterfolg
(A 0,169440 m, 1/1); Änderung nach Vergleich wieder zurückgenommen.

Neue konkrete Messung an gesicherten ursprünglichen Anfangsdaten: 40-cm-
Vorwärtsziel mit vollständiger Route und endlicher neuer Sicht zulässig,
45 cm bereits durch unveränderte Geometrie abgelehnt. Bisherige frühe Auswahl
30 cm, vorhergesagter echter RPP-Stop 15,25 cm wegen der unveränderten
15-cm-Ankunftsscheibe. Die kurze Suche bevorzugt nun ihr entferntestes tatsächlich
vollständig geprüftes Ziel im selben bestehenden lokalen Suchbereich; weder
Wegpunktvorgabe noch vergrößerter Scope, neue Freizellen oder höheres Budget.
Gezielte Regression: 30/30 bestanden, einschließlich zuvor negativem tatsächlichem RPP-Stopnachweis und ursprünglichen Route-/Sicht-/Cooldown-/Versuchskappen. Eingefrorene ursprüngliche ARM-Anfangsdaten wählen nun 43 cm / 177 endliche potenzielle Punkte in 1,246 s bei identischem vollständigem lokalen Evidenzhash; keine Livebeobachtung daraus. Neuer vollständiger Kandidatenvergleich erforderlich.

Punkt 3 (regulärer autonomer Realstart) und Punkt 4 (erweiterte reale Abnahmen)
sind damit weiter offen. Bekannte physische LAB-Kontur wird nach tatsächlichem
Fahrversatz neu an TF/Karte gebunden, niemals umzentriert. Neue reale Passage/
Drei-Bereich-Geometrie und verfügbares natives Apple-Ziel sind noch nicht belegt;
einmalige konkrete Rückfragen dazu sind gestellt. Keine weitere allgemeine
Freigaberunde: erneute Nutzerfreigabe und LAB-1 gelten weiterhin.

**Genau nächster technischer Schritt:** geänderte kurze Auswahl separat prüfen,
in einem neuen vollständigen privaten Kandidaten bauen und die ursprünglichen
A/B/C-Gesamtmissionen abnehmen; danach den bereits beauftragten autonomen LAB-
Start und die abhängigen realen Abnahmen fortsetzen. Bestehende Installation und
Autostart bewahren. Rückfall: eigenen Kandidaten geordnet beenden, vorhandenen
Bestandsinstall nutzen; die Auswahländerung lässt sich gezielt zurücknehmen.
Private Originalbelege: `~/.local/share/amadeus/diagnostics/ap06-drive-qualified-20261010/`.


## 10.10.2026 – beauftragte Folge 1–4 wird ausgeführt

Punkt 1 beendet als begrenzte Komponentenqualifikation: Register 100/400/5
tatsächlich zurückgelesen, RPM-Skalierung 1 beibehalten. Negative Drehung und
25-cm-Translation mit gemessenem Stop positiv. Translation einschließlich
Ausrollen 29,850 cm Encoder / 30,066 cm unabhängiger LiDAR; lokale ICP-Residuen
3,85 mm. Gerade Phase 4,185 s, gesamter Lauf 6,109 s, nach letztem Vor-Stop-
Sample 4,411 cm Ausrollen; bestehende 12,8-cm-Stopphülle genügt für diese Probe.
Steady-State tatsächlich etwa 0,079 m/s bei 0,08 m/s Soll, FC03 122 RPM;
kein belegter Faktor-zwei-Encoder-/RPM-Fehler. 46/46 FC06 bestätigt, genau zwei
Startimpulse. Danach je Motor 1.970 tatsächliche FC03-Proben mit identischer
Position und Null-RPM. Beide feste Komponenten sind keine selbstgewählten
Explorer-Ziele. Keine autonome Produkt-/Kundenabnahme daraus ableiten.

Sichtlücke im Rohdatenbeleg ausdrücklich: zweiter 90-s-Recorder endete knapp
vor Translationsbeginn. Originale Diagnose-/Tor-/Base-Ereignisse und tatsächliche
RAM-Bustransaktionen erfassen den Lauf; unabhängiger LiDAR-Wegvergleich nutzt
Originalscans vor Fahrt und zusätzliche späte Stillstandsaufzeichnung. Keine
vollständige bewegte Raw-Bag-Sensorabdeckung behaupten. Private Originale
bleiben erhalten, eigene Prozesse geordnet direkt beendet. Punkt 2 folgt:
einheitlicher Produktkandidat und ursprüngliche AP-06-Fälle A/B/C.

Unabhängige Auswertung der Original-LiDAR-Scans ohne Rad-/EKF-
Prior bestätigt R17: 26,84 cm, +16,69° / −16,37°, lokale Fitresiduen etwa
3–4 mm. Neuer R18-Vergleich startete real und durchlief Vorwärts- und beide
Drehphasen; beim Schlussstop kontrollierter Monitorabbruch bei 0,60957 rad
Phasenwinkelspanne gegen 0,6 rad Budget. Kein vollständiger Positivlauf daraus.
Encoder gültig, keine Modbus-Lesefehler, frischer Stillstand bestätigt.
90 reale FC06-Transaktionen alle bestätigt, genau sechs Startimpulse; ein
periodisches Neustarten der Rampe ist damit widerlegt. Register 2000/400/5
zurückgelesen. Positionsdaten zeigen etwa 1,48 Motor-RPM/s Beschleunigung.
Expliziter Vergleich mit Register 100 und getrennten begrenzten Komponenten-
proben vorbereitet; bisher noch keine Fahrt mit dieser Rampeneinstellung.

Zusätzliche lesende Nachprüfungen: einmal 130-ms-Paar gegen 120-ms-Grenze,
anschließend bei CPU-Trennung eine 199-ms-Lücke direkt nach der ersten
Odometrieausgabe. Beide negative Befunde bleiben erhalten. Kaltmessung der
ersten ROS-Serialisierung: String 79,6 ms, Odometry 195,9 ms; danach jeweils
unter 0,3 ms. Ausgabehelper lädt nun die tatsächlichen Serialisierer vor
Baseline/Timer, verwirft Initialisierungsbytes lokal und publiziert keine
Aufwärmprobe. 128 Tests mit expliziter Sourceauflösung bestanden; erste
versehentlich alte Overlayauflösung ist als negativer Testnachweis erhalten.
Separater Base-Build erfolgreich. Lesender Dreiminutenlauf 180,009 s beendet:
3.230 aufgezeichnete gültige Radproben, keine Paarverwerfung, längstes Paar
31,386 ms, größte Radheaderlücke 63,896 ms; 608/608 Nahstatusproben gesund.
HWT-Anlauf nicht als durchgehend fertige Fusion ausweisen. Aktiver Folgestart
noch ohne Bewegung: Tor verwendete bei frischen IMU-Messungen 1,196 s alte
Status-Callbacks und verriegelte; Start nicht gesendet, Weg/Kommandos null.
Originalbefund bleibt erhalten; Status-Empfangspfad wird separat korrigiert.
Keine Frische-, Kontinuitäts- oder Bremsgrenze angehoben.

Nutzerauftrag: Anfahr-/Bremsmessung, ein reproduzierbarer Kandidat samt drei
ursprünglichen AP-06-Gesamtfällen, regulärer autonomer LAB-Start, danach die
weiteren Gesamtprüfungen gemäß MASTERPLAN v1.3 / WE-M4–M7. LAB-1-Freigabe
wurde erneut ausdrücklich erteilt. Istbasis: separater Checkout e14ca312 mit
den dokumentierten eigenen Korrekturen R1–R17; Bestandsmain/-install bleiben
erhalten. Keine vorweggenommene Kunden- oder Gesamtqualifikation.

Zuerst tatsächliche FC03-/FC06-Transaktionen und Positions-/LiDAR-Referenz
prüfen. Erster bewegter Vergleich bleibt die feste 25-cm-/±15°-Sequenz,
90 s / 0,5 m / 0,6 rad, gleiche Schutzkette und physischer LAB-Bereich unter
Berücksichtigung des bereits gefahrenen Versatzes. Änderungen an Rampen erst
nach gemessener Ursache, separat testen. Anschließend ein eigener vollständiger
Produktbuild auf gepinntem nativen Unterbau; ursprüngliche Simulation A/B/C
bleibt gerätefrei und ohne Zielvorgaben. Reale Folgebudgets vor Ausführung
festlegen. Unverifizierte Passage, neue Bereiche oder native App-Ergebnisse
nicht aus dieser lokalen Fläche ableiten. Rückfall: eigene Prozesse geordnet
stoppen und den erhaltenen Bestandsinstall verwenden; kein Autostartwechsel.

## 10.10.2026 – Bewertung nach der erfolgreichen LAB-Sequenz

R17 bleibt ein vollständiger positiver fester Fahrtest mit gültigen Encodern,
bestätigten Zwischenstopps und erhaltenem Bestandsinstall. Die normale
Explorer-/Nav2-Mission wurde dabei noch nicht ausgeführt; ursprüngliche AP-06-
Gesamtqualifikation weiterhin 0/3. Ein einzelner positiver Lauf belegt noch
keine Reproduzierbarkeit nach Kaltstart oder unter Kundenlast.

Neue Auswertung der unveränderten Originaldaten: Vorwärtsphase 21,377 s bis
25 cm Sollfortschritt, während `/cmd_vel` zeitlich etwa 99,7 % ungleich null
war und nach der Glättung überwiegend 0,08 m/s verlangte. Beide Drehphasen
dauerten jeweils etwa 10,2/10,3 s. Während der Vorwärtsfahrt stieg die gemessene
Encoder-Geschwindigkeit langsam von etwa 0,003 auf 0,022 m/s. Zeit-/Kommandosummen
aus dem unabhängigen vollständigen Bag bestätigen die Auswertung der Diagnose-
Callbacks. Das beweist eine erhebliche Soll-/Bewegungsabweichung, aber noch
nicht deren Ursache. Kein belegter Encoderdefekt oder wiederholter Schutzstop.
Encoderweg etwa 25,1 cm und Kartenpose etwa 24,8 cm sind plausibel zueinander;
die Kartenpose ist wegen gemeinsamer Quellen keine unabhängige Bodenreferenz.

**Genau nächster begrenzter technischer Auftrag:** Antriebsübertragung,
Anfahr-/Bremsverhalten und reale Trackingreserve des bestehenden Kandidaten
qualifizieren: tatsächliche Register-/Starttransaktionen, wirksame Rampen,
Positionsfeedback und unabhängige Strecke/Winkel gemeinsam messen. Innerhalb
des bestehenden LAB-Bereichs, mit frischen Quellen und unveränderter Schutzkette;
keine blinde Fristerhöhung, Counts-/Geometrieänderung oder zusätzliche Fläche.
Vor einem neuen Stackstart den gefahrenen Versatz bei der Bindung desselben
physischen Laborbereichs berücksichtigen. Diese Bewertung startet keine Fahrt.

Danach Korrekturen in einem eindeutig versionierten separaten Kandidaten
zusammenführen und die ursprünglichen geschlossenen Fälle A/B/C nachprüfen;
dann den regulären autonomen Start mit nützlicher erster Beobachtung abnehmen.
Weitere Beobachtungsaufgaben, ganze Passage, Rundweg, Hindernis/Halt/Fortsetzung
und Speichern/Wiederaufnahme folgen gemäß MASTERPLAN/WE-M4–M6. Native App-
Abnahme bleibt unter WE-M7 getrennt. Kein dauerhafter Installwechsel aus der
Bewertung. [Messgrundlage und Folgeschritte](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – erste vollständige reale feste LAB-Fahrsequenz bestanden

Die Startablehnungen der ausdrücklich aktivierten Stage-3-Diagnose wurden im
separaten Checkout korrigiert. R17 startete um 18:42:39 UTC und beendete um
18:43:25 UTC regulär die feste 25-cm-/+15°-/−15°-Sequenz mit drei gemessenen
Stillständen. Vorwärtsphase einschließlich Ausrollen etwa 26,5 cm, gesamter
Encoderweg 27,568 cm; gemessene Drehungen einschließlich Nachlauf etwa +16,45°
und −16,24°. Abschließend beide Motor-RPM null, Encoderfeedback gültig und
frisch, keine Modbus-Lesefehler oder Encoder-/Ausgabeprozessverriegelung.

Korrigiert: feste physische LAB-Kontur statt übergroßer Körperscheibe,
leerer Idle-Missionsstatus, echte Quellenzustellung vor Entscheidungen,
unbegründete Nullimpulse im erlaubten Diagnosemodus und unveränderliche
Session-/Scopeepoche trotz wachsender Karte. Tatsächliche HOLD-Historie und
Recoverybudgets bleiben erhalten; explizite Quittierung nur nach geprüfter
Erholung und gemessenem Stillstand. Der private Monitor unterscheidet rohe
Encoder-Winkelvariation von vollständigen Winkelspannen der überwachten
Phasen. Keine Frist, Haltwirkung oder physische Schutzgrenze angehoben.

87 verschiedene gezielte Software-/DDS-Fälle und vier private Monitorfälle
bestanden. Separater Navigationsbuild R17 erfolgreich (6,58 s). Ausgeführt:
Base R10, Fahrtor R15, Diagnose R17 mit derselben tatsächlichen Sensor-/EKF-/
SLAM-Quelle und dem ursprünglichen physischen Scope-/Radanker. Abgebrochene
Vorversuche bleiben als solche dokumentiert; keine negative Historie gelöscht.
Eigene Prozesse geordnet über direkte PIDs beendet, serielle Geräte frei;
abschließend 20 rein lesende FC03-Proben je Motor: null RPM und stabile
Positionen. Bestandsinstallation mit 1.048 Dateien und Originalcheckout erhalten.

Dies ist ein vollständiger begrenzter LAB-Komponententest, keine autonome
Wohnungserkundung oder Kundenabnahme. AP-06 bleibt **0/3** Gesamtmissionen.
Der nächste fachliche Schritt ist der echte autonome Start-/Trackingnachweis
mit anschließendem AP-06-Gesamtlauf innerhalb eines passend geprüften Bereichs.
[Build, Fahr- und Quellenbelege, Sensorzeiten und Sichtlücken](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – realen Fahrablauf vorbereitet, aktueller Startnachweis negativ

Auf Auftrag „alles für die Fahrt vorbereiten“ ausführbare private Abläufe für
passiven/aktiven Stack, neue Scopebindung, Explorer, begrenzte Mission und
geordneten Stopp vorbereitet. Keine weitere allgemeine Freigabe erforderlich.
Abbruchschwellen: 90 s Missionszeit, 0,5 m Encoderweg, 0,6 rad Encoderwinkel;
Cancel über bestehenden Mission Manager, anschließend frischen Stillstand prüfen.

Neuer passiver Vorlauf 180,070 s, keine Encoderverriegelung, max. Paarzeit
98,551 ms, 675/675 Nahstatus beidseits gesund. Neue Karten-/TF-/Quellenbindung
gelungen; erste transient fehlgeschlagene TF-Bindung erhalten. Sechs anschließende
aktuelle passive Geometrieproben gültiger Eingänge bleiben negativ. Der neue
Geradenprüfer ist weiterhin nur Diagnose, kein aktiver Ersatz.

Konkreter Vorbereitungsfehler behoben: Stillstandsprüfung im privaten
Missionsmonitor nutzte Soll-RPM. Neue Version verlangt gemessene Motor-RPM=0
und frische Encoder-Rückmeldung; zwölf Gegenproben bestanden. Historischer
Monitor unverändert als Beleg erhalten. Keine Produktgrenze angehoben.

**Ablauf vorbereitet, noch keine Fahrbereitschaft oder Realfahrt.** Alle eigenen
Prozesse geordnet beendet, abschließend 20 FC03-Proben je Motor mit 0 RPM und
unveränderten Positionen, Geräte frei und Bestandsinstallation unverändert.
Private ausführbare Anleitung/Ergebnis unter
`~/.local/share/amadeus/diagnostics/ap06-drive-preparation-20261010T1308Z`.
Nächster technischer Schritt bleibt gültige reale Startabdeckung/Tracking und
anschließende Live-Qualifikation; keine identische Fehlstartserie. AP-06 0/3.

## 10.10.2026 – Ersatzprüfung implementiert, Realfreigabe weiterhin offen

Auf ausdrücklichen Auftrag, einen funktionierenden Ersatz der Startprüfung zu
entwickeln, kontinuierlichen Geradenprüfer `metric_start_sweep.py` erstellt und
in das vorhandene **lesende** Startdiagnosewerkzeug eingebunden. Vollständiger
Vorfahrtkorridor, analytische Winkelhülle, Positionsabweichung und exakte
Rasterzellpolygone ersetzen dort punktweise/rasterpauschale Näherungen.
Fester Anfangsbestand bleibt auf seine tatsächliche gepaddete Körperüberdeckung
begrenzt; belegte Zellen und neue unbekannte Außenfläche bleiben negativ.

Separater Zweipaketbuild erfolgreich, 47 gezielte neue/bestehende Prüfungen
bestanden. Auf unveränderten gespeicherten Roh-/Kostenrasterproben ist die
ideale 25-cm-Gerade positiv. Das deklarierte Versuchsband 20 mm/0,05 rad bleibt
negativ; auf der Rohkarte 0,017601 m² zusätzliche unbekannte Fläche. Das Band
ist keine qualifizierte reale Reglergarantie. Neue Rechnung ist kein Ersatz
für aktuelle Quellen-/TF-/Controller- und Stoppnachweise.

**Noch kein funktionierender aktiver Ersatz und keine Realfahrt.** Aktive
Startprüfung unverändert, keine Schutzprüfung gelöscht, keine Roboterprozesse
gestartet. Nächster erforderlicher Schritt: nachgewiesene reale Abdeckungs- und
Trackingbedingungen herstellen, anschließend denselben Geometriekern mit der
bestehenden festen Live-Referenz-/Historienbindung qualifizieren. Bis dahin
keine Aktivierung durch ein positives ideales Offline-Ergebnis. AP-06 weiter
0/3; kein Kundenauslieferungsnachweis. Details und Rückfall im
[Vorlaufbericht](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – unabhängiger Gegencheck: Startsperre ist kein Raster-Rundungsfehler

Softwarekorrektur erneut untersucht. Kontinuierlicher Polygonschnitt belegt:
Schon die vorhandene 10-mm-Reserve ohne Rasterhalbdiagonale liegt teilweise
außerhalb des gespeicherten Startpolygons und über unbekannter Rohfläche.
Vier gezielte Ausfahr-/Schutztests bestanden, darunter zulässige Vorwärtsausfahrt.
Keine belegte Korrektur, die diesen Realstart ohne neue Beobachtung oder
unqualifizierte Reservenreduzierung freigibt. Keine Bewegung, AP-06 weiter 0/3.
Es fehlt keine Laborfreigabe. Erforderlich bleibt gültige Startabdeckung bzw.
beobachtbare Ausgangslage; die frühere Vermutung einer reinen Rundungssperre
ist für diesen Befund widerlegt. Details im letzten Vorlaufnachtrag.

## 10.10.2026 – keine weitere Freigaberunde; technischer Startnachweis bleibt negativ

Nutzer stellt klar: im bestehenden Labormodus nicht auf eine erneute hintere
Bereichs-/Laborfreigabe warten. Die pauschale 50-cm-Nachfrage ist zurückgezogen;
sie ist weder eine allgemeine Voraussetzung für Vorfahrt noch ein Ersatz
für den technischen Geometrienachweis. Keine größere freie Fläche daraus
als gemessen oder geprüft behauptet.

Zusätzliche lesende Zerlegung der erhaltenen Realproben: Von 108 reservierten
Startzellen außerhalb des bisherigen Polygons sind 105 in der Rohkarte unbekannt,
drei beobachtet frei; keine dieser Proben belegt ein Hindernis. Eine ideale
Vorfahrt um 2 cm verlässt die Polygonkante, rechtfertigt aber nicht rückwirkend
die ungeprüfte Anfangsstrecke. Die bestehende Startprüfung bleibt negativ.
Keine neue Mission, keine Bewegung, keine Schutzgrenze geändert. Es wird nicht
auf eine zusätzliche allgemeine Freigabe gewartet. Nötig ist ein gültiger
technischer Start-/Abdeckungsnachweis; vorhandenes Abdeckungspaket und neue
Messdaten verwenden, keine unbekannten Zellen zu Freiraum erklären.
Details im letzten [Vorlauf-Nachtrag](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – Geometriefrische verbessert; hintere reale Bereichsgrenze muss geklärt werden

Erneuter Fahrstartauftrag bearbeitet, weiterhin **keine reale Bewegung, AP-06 0/3**.
Gemessene Mehrfachberechnung des unveränderten Scope-Rasters begrenzt gecacht;
keine Sensor-/Footprint-/Scopegrenzen gelockert. Separater Build und 240 gezielte
Tests bestanden. Neuer 180,057-s-Vorlauf: 3.450 Encoderpublikationen, längstes
Paar 34,159 ms, keine Ablehnung; 620/620 Nahstatus beidseits gesund. Sechs reale
passive Geometrieprüfungen halten die Frischegrenzen ein (169–434 ms).

Startreferenzen bleiben ungültig: 108 reservierte Zellen pro Raster hinter der
bisher bestätigten 13-cm-Grenze. Konkrete Frage nach tatsächlich geprüftem
hindernisfreiem Boden bis 50 cm hinten gestellt; Antwort noch ausstehend.
Allgemeine LAB-1-Freigabe gilt weiter. Ohne Antwort keinen größeren Bereich
annehmen. Nach Klärung neu binden und begrenzt über die Schutzkette fahren.
Alle eigenen Prozesse beendet, Stillstand per FC03 bestätigt, Installation
unverändert. Details und Recorder-Zeitspitzen im letzten
[Vorlauf-Nachtrag](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – Encoder/HWT im finalen Lauf gesund; Missionsauftrag ohne Fahrt abgebrochen

**Aktuell: reale Explore-Mission gesendet, aber 0 m / 0 rad Bewegung; AP-06 0/3.**
351 betroffene Tests und getrenntes `robot_state_estimation`-Overlay bestanden.
HWT-Rohdaten/Drehraten nutzen jetzt wie die vorhandene Radquelle einen aktuellen
DDS-Take mit Originalstempeln vor der Entscheidung. Prozesslokale CPU-Zuteilung
und Encoder-GC-Vorlauf stabilisierten die letzten Encoderläufe; keine Grenzwerte
angehoben. Letzter passiver Bag: 180,089 s, 3.266 Encoderpublikationen, max.
50,396 ms/Paar, keine Ablehnung. Aktiver Bag: 300,052 s, 4.731 Publikationen,
max. 40,041 ms/Paar, keine Encoder-/HWT-Verriegelung nach dem Einlauf.

Der Auftrag erreichte den Explorer, scheiterte jedoch **vor** einem Fahrbefehl:
`self_body_scan_stale_after_processing`, Geometriearbeit 677,016 ms und finales
Scanalter 770,524 ms gegenüber 500 ms. Vorhandener Neuversuchsrahmen bereits
benutzt. Zusätzlich `start_egress_obstacle_or_scope` bei beiden Startreferenzen.
Genau nächster Schritt: die konkrete Geometriearbeit profilieren und die
Footprint-/Scope-Rasterkante auftrennen; keine Fristerhöhung oder Bereichserfindung.

Roboter abschließend per 20 FC03-Proben je Motor still; Prozesse beendet,
Ports frei, 1.048 Bestandsinstall-Dateien unverändert. Keine reale Fahrabnahme.
Details, neue Quellen-/Sensorzeiten und Rückfall im letzten Nachtrag des
[Vorlaufberichts](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – erste reale Fahrt vorbereitet, aktive Stillstandsprüfung negativ

**Aktuell: ausdrückliche Labor-/Fahrfreigabe des Nutzers liegt vor; technische
Voraussetzung weiterhin nicht erfüllt. Keine Bewegung ausgeführt, AP-06 0/3.**
Nach Rechnerneustart aktuelle Sensoren/Scope neu geprüft. TF-Empfang des
Bereichswerkzeugs von Karten-/Grapharbeit entkoppelt; Originalstempel und
0,8-s-Grenze erhalten, zwei reale Scopebindungen gelungen. Ein späterer
TF-Frischefehler bleibt als Gegenbeleg erhalten.

Aktive Basis als alleiniger Busbesitzer zunächst nach acht Ausgaben mit
239,018-ms-Paar verriegelt. Gezielte Startkorrektur: erste Encoder-Messbasis
auch aktiv erst nach vorhandenem 15-s-Vorlauf. Danach 2.438 Publikationen,
Paarzeiten maximal 96,596 ms und zwischenzeitlich gültige Quellen, später aber
181,212-ms-Samplelücke gegenüber 180 ms. Keine Frische-/Stoppgrenze erhöht.
181 betroffene Tests bestanden und neues Launch-Overlay separat gebaut;
kein Software-Gesamtpositivnachweis und kein Bewegungsauftrag daraus abgeleitet.

Ein Explorer-Aufruf ohne vorhandenes Profil wurde im Leerlauf beendet; kein
Auftrag gesendet. Vorbereiteter Start bricht nun vor Launch ab, wenn das
explizite gebundene Profil fehlt. Alle realen Kommandos/Encoder/RPM null,
abschließend je Motor 20 FC03-Proben null, Prozesse beendet/Ports frei und
1.048 Bestandsinstall-Dateien unverändert.

**Genau nächster Schritt:** Im aktiven Basisprozess den belegten 181,212-ms-
Kontinuitätsverstoß mit FC03-, Callback- und DDS-Publikationszeiten korrelieren
und die Ursache beheben; erst danach den vorbereiteten begrenzten Fahrtest
mit frischen Quellen und neuer Scopebindung starten. Keine pauschale
Fristerhöhung, keine wiederholten identischen Starts. Vollständige Belege und
Rückfall im letzten Nachtrag des [Vorlaufberichts](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – historische Sensorverträge angewandt, Encoder teilweise korrigiert

**Aktuell: AP-06 weiterhin 0/3; keine Kunden-/Fahrtfreigabe.** Separater
Kandidat `fix/ap06-passive-sensor-timing`, Basis `e14ca312`, noch uncommitted.
Die historische VL53-Diagnose ist geklärt: gesunde, frische PARTIAL-Frames mit
leeren Nahwolken sind laut finalem Vertrag vom 25.09. kein eigener Sensorfehler.
615 aktuelle vollständige Tripel erfüllen die vorhandene Offline-Health-Prüfung;
unbekannte Sichtbereiche und die frühere reale Frischelücke bleiben getrennt.

Encoder-DDS-Publikation blockierte den Lese-Callback nachweislich bis 297,5 ms.
Gezielter Patch trennt alle drei Ausgaben in einen begrenzten Prozesskanal;
Originalstempel, exklusive FC03-Quelle und 120/180-ms-Grenzen unverändert.
170 betroffene Tests bestanden, separates Overlay gebaut. Zwei neue passive
Dreiminutenaufnahmen: erster Lauf nach 664 Publikationen mit 169,8-ms-Paar
verriegelt; zweiter Lauf 3.200 Publikationen, keine Ablehnung, maximal 66,3 ms,
am Ende Quellen bereit. Im Recorder dennoch bis 329,1 ms Rad-Empfangsalter.
Damit Teilkorrektur und ein positiver Leser-/Endstatusnachweis, keine robuste
Gesamtfreigabe. Kein Aktorprozess, keine Mission; Installation unverändert.

**Genau nächster Schritt:** Den getrennten Ausgabeweg bei Reader, DDS und
Gate-Empfang zeitlich korrelieren, um die verbleibende Zustellspitze und ihre
Wirkung auf Quellenfrische nachzuweisen; den erhaltenen Paarzeit-Gegenfall
dabei nicht verwerfen. Keine weiteren identischen Fehlstarts oder gelockerten
Fristen. TF-/Scopebindung, geometrische Sichtgrenzen und acht ursprüngliche
Regressionstestfehler bleiben offen. Messungen, Quellenbindung, verworfene
Ansätze und Rückfall im [Vorlaufbericht](JETSON_VORLAUF_AP06_20261010.md).

## 10.10.2026 – Jetson-Build erfolgt, passiver Quellen-/Sichtnachweis negativ

**Aktuell: ursprüngliche AP-06-Abnahme weiterhin 0/3; keine Kundenfreigabe.**
Exakter Übergabestand `e14ca31276b26be2d88397b310301dad3c4e9600` im neuen
Checkout `/home/p/roboter_worktrees/ap06-e14ca312-validation`, separater
AArch64-Release `ap06-20261010T070231Z`. 31 native und 14 Produktpakete,
LiDAR-Overlay und TF-Prüfwerkzeug gebaut; Quellen-/CMake-/Runtimepräfixe
gebunden. Bestehender Checkout und 1.048 Install-Dateien unverändert.

Vollständiger Produktlauf: 2.456 registrierte Tests, 38 fehlgeschlagen.
Gezielte Wiederprüfung der 38 Fälle mit korrekter isolierter Testumgebung:
30 bestanden, acht weiterhin negativ (DDS-Registrierung, Auswahlbudget,
öffentliche Beobachtung). Kein Produktcode/Grenzwert geändert, kein Gesamt-Grün.

Zwei abgeschlossene passive 180-s-Aufnahmen, zweite ausdrücklich zur Erfassung
des Anlaufs. Encoder in beiden Läufen wegen Kontinuitätslücken verriegelt
(334/371 ms gegenüber 180 ms). HWT im ersten Lauf terminaler serieller
Transportfehler, im zweiten Lauf grundsätzlich bereit mit gemessenen Lücken.
Beide aktuellen Scopevorbereitungen scheitern an TF-Zeitbindung; kein Explorer,
keine Mission, keine Fahrt. Eindeutige Karten-/TF-Eigentümer ersetzen diese
fehlende Zeitkonsistenz nicht. Vier Nahbereichswolken durchgehend leer,
Qualität PARTIAL, keine vollständig beobachteten Spalten; zusätzlicher
LiDAR-Hecksektor von etwa 68 Grad ausgespart. OAK bleibt aus.

Stacks/Recorder beendet, Ports frei, Abschlussencoder unverändert/0 rpm.
Reale Bags/Karten/Bindungen nur privat. Vollständige Messdefinitionen,
Buildabweichungen, Grenzen und Belegpfade im
[Jetson-Vorlaufbericht](JETSON_VORLAUF_AP06_20261010.md).

**Genau nächster Schritt:** Die im passiven Originalstack gemessene
Encoder-Kontinuitätslücke mit vorhandenen Reader-/Transport-/Callbackzeiten
ursächlich isolieren und eine etwaige gezielte Korrektur separat passiv prüfen.
Offene TF-/Nahbereichs- und Regressionstestbefunde bleiben dabei offen;
keinen aktiven oder Kundenpositivlauf daraus ableiten.

## 08.10.2026 – Konzeptvergleich und überprüfbare Jetson-Übergabe

**Aktuell: ursprüngliche AP-06-Abnahme 0/3; keine Kundenfreigabe.**
Geprüfter Produktkandidat `c5d2a9c00d146851799a907ba725ef0d0f30c815`,
gleicher AP-06-Branch. Folgende datierte Einträge bleiben als Historie erhalten.

Umgesetzt sind ein abgegrenzter Konzeptprüfstand, phasenbezogene Drehprüfung,
öffentliche Kartenfortsetzung bei vollständig leerem privaten Startbestand,
begrenzte Wiederprüfung während der Verarbeitung abgelaufener Scan-/Posedaten
und ein passiver Start mit aktueller Scope-/Quellenbindung. Quellengrenzen,
Stopbedingungen und ursprüngliche Aufgaben-/Missionsbudgets bleiben bestehen.

Letzter Explorer-Build und **1.808 registrierte Explorer-Tests bestanden**,
0 Fehler/0 Skips. Übrige 13 Produktpakete unverändert seit geprüftem
14-Paketbuild; native Szenarien zuletzt 9/9 am unveränderten nativen Stand.
Diese Prüfungen ersetzen keine Gesamtmissionen und werden nicht addiert.

Sechs abgeschlossene Konzeptläufe bleiben negativ. Letzter regulärer
Konzeptlauf: drei Ankünfte/drei Beobachtungen, dann 5-s-Auswahlbudget erschöpft.
Zusätzlicher Diagnoselauf: zwei Ankünfte/zwei Beobachtungen; eine tatsächliche
Frische-Wiederprüfung führt zur Folgeankunft, später verbraucht ein erneuter
Poseablauf das vorhandene Aufgabenversuchslimit. Ganze Passage fehlt.
23 aufgezeichnete Auswahlaufrufe reproduzieren den älteren Auswahlabbruch
nicht. Originaler Gyro-HOLD-Stoppfall bestanden; der erneute Cancel-Versuch
scheitert bereits vor Fahrt an einer Encoder-Zeitlücke und zählt nicht als
Cancelnachweis. Exakte Resultate, Zeiten und Gegenfälle im
[Belegbericht](evidence/ap06-concept-20261008/README.md).

**Nächster Schritt:** Nutzer übernimmt den separaten lokalen Build und
passiven dreiminütigen Quellen-/Sichtnachweis nach
[JETSON_KONZEPTTEST_AP06](JETSON_KONZEPTTEST_AP06.md). Das Paket enthält
prüfbare Quellen und Belege; ARM-Build und echte Sensorlatenzen wurden hier
nicht gemessen. Deren Auswertung muss die verbleibenden Zeit-/Sichtprobleme
klären. Vor Kundenfreigabe sind weiterhin drei vollständige Originalmissionen
auf demselben Kandidaten und die realen Abnahmen erforderlich. Keine weitere
Zugangsfrage, kein Deployment oder automatischer Übergang zu einem anderen AP.

## 07.10.2026 – AP-06 Reviewkorrekturen in Umsetzung

Nutzer beauftragt ausdrücklich die Behebung der festgestellten Probleme. Basis `7934a28` im bestehenden AP-06-Branch, MASTERPLAN v1.3 und ursprüngliche A/B/C-/Cancel-/Gyro-HOLD-Abnahme unverändert. Ziel bleibt 3/3 am gleichen finalen Softwarestand. Kein Hardwarezugriff, Deployment, Push/Merge oder nächstes AP. Frühere Reparaturen und Negativnachweise bleiben erhalten; Rückfall nur der neuen eigenen Änderungen.

V37 und V38: jeweils **9/9 native Komponenten bestanden**. Diagnose B186 lokalisiert die Eingabeverzögerung; `7fabf80` reduziert den allgemeinen exakten Egress-Pfad auf identischen Daten von 186–192 auf 50–51 ms. V38: Zwölfpaketbuild, **2242 direkte / 2224 registrierte Tests grün**, null Skips. Regulärer B193 dennoch negativ: eine Ankunft, null Beobachtungen, abgelaufene gebundene Encoderprobe während der Beobachtung.

B194 belegt eine bereits vorliegende echte frische Encoderprobe trotz verworfener alter Bindung und anschließend einen zweiten Fehler: Restarbeitsbewertung bricht im noch nicht roh-frei beobachteten Startzentrum ab. `4497d0c` bindet höchstens einmal eine tatsächlich neuere, weiterhin TF-konsistente Messung mit vollständigem neuen Egress-Beweis. Unbeweisbare lokale Konnektivität hält Arbeit offen; globale Abschlussprüfung und Fahrfreigaben unverändert. Gegenfälle des alten Frischecodes 2 rot/6 grün; korrigierte Nachbarprüfung 93 grün, Fortschritts-/Frischeprüfung 86 grün. **Gesamtstatus weiterhin 0/3**, bis vollständige Missionen am gleichen finalen Kandidaten nachgewiesen sind.

`8e6cbbe` beseitigt weitere gemessene Auswahlkosten: V40-Zwölfpaketbuild, **2282 direkte / 2264 registrierte Tests**, 9/9 native Komponenten grün. Regulärer B207 erreicht drei Ankünfte/drei Beobachtungen und vollständigen Rundblick, bleibt nach 1,4018 m / 74,62 % Referenzboden an späterem Auswahlbudget negativ. Native-Sichtablehnung eines Fernvorschlags bleibt korrekt aktiv. Save/exakter Checkpoint und terminale Nullbefehle bestätigt.

`972ef6c` ersetzt den mehrfachen Python-Konnektivitätsdurchlauf durch identische Vier-Nachbar-Komponenten und bündelt unveränderte Zielprojektionen. Seitenabfragen prüfen die bestehenden Zeit-/Versuchsgrenzen vor teurer Geometrie. Im erhaltenen B207-Endzustand sinkt die Auswahl von Budgetüberschreitung auf 2,657 s bei unveränderter Historie; keine frühere Live-Freigabe daraus. **336 betroffene Tests grün**; V41-Gesamtprüfung siehe folgenden Absatz.

V41 ebenfalls vollständig grün (**2306 direkte / 2288 registrierte Tests**, 9/9 native Fälle), regulärer B214 jedoch erneut vor dem noch ausstehenden Rundblick am Auswahlbudget beendet. Exakte Eintrittsdiagnose B216 bewahrt die privaten Inventare und ursprüngliche Historie; unter Live-Last 5,100 s, im isolierten Cooldown-Zweig 0,528 s. Damit ist eine reine Endkarten-/Mikrobenchmark-Zusage unzureichend.

`60e23a8` priorisiert den bereits vollständig auf öffentlichen Karten bewiesenen, noch ausstehenden einmaligen Rundblick nach einer tatsächlichen Startbeobachtung, bevor ein weiteres Fahrziel gesucht wird. Anfang ohne Beobachtung, virtuelle Freiheit und unzulässige Drehfläche bleiben gesperrt; Scan-/Missionsdeadline und jede tatsächliche Drehprüfung unverändert. Originalgegenfall 1 rot/6 grün, korrigiert 168 betroffene Fälle grün. V42-Zwölfpaketbuild, **2313 direkte / 2295 registrierte Tests** und 9/9 native Fälle grün. B221 scheitert nach drei Ankünften/drei Beobachtungen an einer echten Encoderlücke; A222/C223 am initialen Auswahlbudget. Cancel224 bestanden; Gyro225 bereits vor Injektion wegen Quellkontinuität negativ. Weiterhin **0/3**.

`a2180ed` und `3c66cbe` beschleunigen ausschließlich die exakt gleiche Zellabstands-/Clippingarithmetik. Vollständiger NumPy-Referenzpfad erhalten; Kontaktpunkte mit Fläche null und ursprüngliche Flächensummation unverändert. V43: zwölf Pakete gebaut, **2337 direkte / 2319 registrierte Tests** grün. Abstandskorrektur allein löst den A-Gegenfall noch nicht (5,078 s); beide Korrekturen zusammen finden auf denselben A227-Eingaben in **4,195 s** den geprüften Startbeobachtungskandidaten. **75 gezielte Fälle grün**. V44 ebenfalls vollständig grün (**2360 direkte / 2342 registrierte Tests**, 9/9 native Fälle, Cancel233 und Gyro-HOLD234); A230/B231/C232 jedoch erneut am Auswahlbudget negativ. Eigener nativer Kernel neu gebaut/gehasht, externe Plugins und ursprüngliches Manifest unverändert.

`5612878` zieht den bereits vorhandenen vollständig geprüften kurzen privaten Startschritt vor Fernabfragen. Originaler A227-Gegenfall rot; korrigiert dasselbe Ziel/dieselbe Task-ID in **0,964 s**, Karten/Inventare/Fristen unverändert. Vier Gegenfälle erhalten Route, Sicht, Cooldown und Versuchskappen. **30 betroffene / 2365 direkte / 2347 registrierte Tests grün**, V45-Zwölfpaketbuild und 9/9 native Fälle bestanden.

**Aktuelles Endergebnis:** Originalmatrix A238/B239/C240 weiterhin **0/3**; Cancel241 und Gyro-HOLD242 bestanden. A startet nun rechtzeitig, scheitert nach 2,1 cm an der festen unbekannten Anfangsfläche bei kleiner realer Kurve. B sperrt neu unbekannte Fläche beim Referenzwechsel. C erreicht drei Ankünfte/Beobachtungen und 4,394 m, scheitert aber an echter 213-ms-Encoderlücke. Alle Actions terminal/vier Nullketten. C245 mit zur Vier-CPU-Quote passender Zuteilung ohne Drosselung, aber Encoder-/TF-Poseabweichung; kein Gesamtfix daraus.

`2e5e1fd` ergänzt unabhängig davon die vorhandene gestoppte, begrenzte Geometrie-Neuprüfung auch für Encoder-/TF-Abweichung: gleicher Task, unveränderte 2 cm/0,05 rad, Fristen und Versuche; permanente Abweichung/Quelllücke bleiben negativ. Das tatsächlich abgelehnte Eingangspaar wird protokolliert. Original-Elterngegenfälle 3 rot/9 grün, korrigiert 48 betroffene Tests grün. V46: Zwölfpaketbuild, **2371 direkte / 2353 registrierte Tests**, 9/9 native Komponenten grün. C248 nutzt die gestoppte Neuprüfung desselben Tasks nach 27,0 mm Poseabweichung, bleibt danach geometrisch gesperrt und endet regulär nach ursprünglichen 900 s: neun Versuche/ein Fehler, null Ankünfte/Beobachtungen, 0,29878 m. **Cancel249 und Gyro-HOLD250 bestanden**. Alle Kinder terminal/vier Nullketten; volle Trace-Hashes geprüft. Keine erneute identische A/B-Fehlstartserie. [Nachweis](evidence/ap06-missions-20261005/README_C246_C250.md).

**Konkreter Blocker und getrennte Weiterarbeit:** Der vollständige unveränderte Trackingnachweis am A227-Start benötigt 138 unbeobachtete Rohkartenzellen außerhalb des Anfangsinventars. Nominal gerade Bewegung reicht nicht. [Separates Beobachtungs-/Abdeckungspaket vorbereitet](AP06_STARTBEOBACHTUNG_BLOCKER.md) gemäß MASTERPLAN AP-03; keine Hardwareänderung und keine neue Serie identischer Fehlstarts. Unabhängig: gestoppte Encoder-/TF-Neuprüfung und echte Ablehnungsdiagnostik implementiert und V46-validiert; genaue Ursache des langen Base-Executors bei C240 weiterhin offen. Grenzen, Inventar und Originalmanifest bleiben unverändert. **AP-06 nicht abgeschlossen; keine 3/3- oder Deploymentfreigabe.** Nachweise: [B185–B193](evidence/ap06-missions-20261005/README_B185_B193.md), [B194–B196](evidence/ap06-missions-20261005/README_B194_B196.md), [B197–B207](evidence/ap06-missions-20261005/README_B197_B207.md), [B208–B214](evidence/ap06-missions-20261005/README_B208_B214.md), [B215–B225](evidence/ap06-missions-20261005/README_B215_B225.md), [A227–A235](evidence/ap06-missions-20261005/README_B227_B235.md), [A236–B242](evidence/ap06-missions-20261005/README_B236_B242.md).

## 06.10.2026 – AP-06 Lösungskonzept in Umsetzung, Gesamtmissionen offen

**Auftrag:** Nutzer beauftragt die Umsetzung des dokumentierten Lösungskonzepts mit Ziel 3/3 erfolgreichen Gesamtmissionen. Basis `b8189a9` plus identifizierter v19-Arbeitsstand, gleicher isolierter Branch `feature/ap06-closed-product-validation`. MASTERPLAN v1.3 und ursprüngliches Szenariomanifest unverändert. Keine Hardware oder Deployment.

**Belegte Reparaturen:** Die v19-Regression für reine Planalternativen ist geschlossen; der bestehende rote Test besteht wieder. Originale B70-Daten zeigen: erste Beobachtungsbaseline aufgelöst, nach der zweiten noch ein ursprünglicher unbekannter Punkt von neun, trotzdem Aufgabe als erledigt markiert. Der verbleibende kleine aktuelle Rand wird zusätzlich durch den normalen Größenfilter entfernt. Teilbeobachtung bleibt jetzt offen; der ursprüngliche zugelassene Task erhält seinen gemessenen kleinen Rand mit vorhandener ID/Versuchs-/Cooldownbindung. Nur für diese Restarbeit ergänzt die begrenzte öffentliche Suche Richtungen entlang des tatsächlichen Randes. Sonstige Größenfilter, Kontur, Quellen, Scope, Fristen und Fehlerlimits erhalten. Spätere vollständige frische Scope-Beobachtung kann alte Teilaufgaben im ursprünglichen Abschlussfenster auflösen, ohne zusätzliche Ankunfts-/Gewinn-/Beobachtungszähler.

**Kausalnachweise:** B70-Auswahl nach analytisch abgelaufenem originalem Cooldown auf exakt erhaltenen Daten: vorher nur ferner unbewiesener Vorschlag, nachher nützliche vollständig eigene geprüfte Folgeposition in 0,12 s, vorhandene Task-ID 4 und unveränderte Zähler. Gegenprobe mit früheren Kandidaten-/Runtime-Modulen rot am Verhaltensassert. Tatsächliche C++-Nav2-Abfrage für diese Folgeposition: Anfahrt, Stopp/Drehhülle und gesicherte Abfahrt positiv. Dies sind Komponentenbelege; keine Mission daraus als positiv gezählt. 14 neue Retained-/Beobachtungs-/Persistenzfälle grün, drei zusätzliche echte Elternentscheidungsfälle für Teilbeobachtung und spätere Scope-Auflösung grün. Ganze direkte Regression v20: **2.134 bestanden**, keine Fehler/Skips, 138,31 s. Zwölfpaketbuild 6,67 s bestanden; registrierte colcon-Prüfung: **2.116 Tests, null Fehler/Failures/Skips**. **9/9 native Bewegungs-/Sperrkomponenten bestanden**. Kandidat `17fba88`, 136 Installdateien bytegleich, 448 Dateien an Quellstand gebunden.

**Prüfstand:** Eigene inaktive Build-Caches lossless archiviert und alle regulären Dateihashes vor Entfernung geprüft; etwa 496 MB zusätzlicher Platz. Die Observer-Ereignisse werden künftig beim Schreiben vollständig verlustfrei komprimiert, mit Eingangsbytezahl/-SHA und separater Dekompressionsprüfung nach Ende. Vier Trace-/Kapazitätsfälle grün, einschließlich echter Startverweigerung vor Runtime bei fehlendem Speicher. Produktmindestreserve weiterhin 512 MiB. Vor jedem Lauf explizites Trace-/Nebenlog-/Temporärkarte-/Reservebudget; aktuell etwa 1,5 GiB frei. Verlustfrei archivierte Negativevidenz bleibt erhalten.

**Grenzen:** Weiterhin **0/3 Gesamtpositivmissionen**; regulärer B72-Gesamtlauf auf Kandidat `17fba88` negativ: 3 Ankünfte/2 Beobachtungen, 7 Versuche/1 Bewegungsfehler, 261 erreichbare Randzellen, 72,42 % Referenzfläche; natürliche Beendigung am ursprünglichen 5-s-Auswahlbudget. Keine Passage. Alle Kinder terminal und vier Nullbefehle, echtes Map-Save und exakt gebundener Checkpoint positiv. Verlustfreie Dekompression aller 196.019.618 Ereignisbytes geprüft (23.993.578 Bytes Gzip). B73 zeichnet begrenzt Originalentscheidungen auf und ist ausschließlich Diagnose. Historische v18/v19-Resultate und rote Zwischenprüfungen bleiben erhalten. Zielsystem-, physische und Apple-Abnahme getrennt offen.

**B73-Diagnose / B74-Korrektur:** B73 bleibt nach explizitem Analyse-Cancel negativ (4 Ankünfte/2 Beobachtungen). Originale dritte Sichtpunkte teils noch unbekannt, teils von kürzeren realen Strahlen verdeckt (2,05/2,09 m Reichweite gegenüber 2,32/2,34 m Punktdistanz). Vierte Sicht scheitert am originalen Supercover, kein erfundener Gewinn. Größere Punktunion, reine Erledigungs-Vorfilterentfernung, IDs-/Receipt-Varianten verbessern die Originalauswahl nicht; nichts davon übernommen. Kleiner aktueller Korridorrand liefert einen weiteren Vorschlag, dessen echter Native-Pfad negativ bleibt. Eine vor dem vierten Ziel berechnete Randtangentenposition bietet sieben statt einem endlichen First-hit-Punkt und echte Native-An-/Abfahrt mit Drehrefuge. Zu breite erste Integration wird durch den alten A51-Erschöpfungsfall abgelehnt; Original-V21/-V22-/Zwischenlogs erhalten. Finale Umsetzung verfeinert ausschließlich eine zuvor original zulässige Zielwahl im Rest desselben 0,5-s-Fensters, bindet beide Positionen lesend an dieselbe ID und verlangt höhere Potentialpunktzahl/niedrigere Originalkosten/öffentliche Drehreserve. **31 gezielte Tests grün**, einschließlich alter Erschöpfung, B70-Rest, B68-Goalchecker und vier neuer B73-/Lookup-Fälle. Finaler Softwarecommit `ea63493`: V23-Zwölfpaketbuild **6,60 s grün**, **2.138 direkte Tests grün** (144,06 s), **2.120 registrierte Tests grün**, jeweils ohne Fehler/Skips. **9/9 native Bewegungs-/Sperrfälle grün**; 136 installierte Produktdateien bytegleich, 449 ausführbare Quell-/Test-/Konfigurationsdateien gebunden. B75 regulär **negativ** am originalen 900-s-Gesamtbudget: 2 Ankünfte/2 Beobachtungen, 8 Versuche/null Bewegungsfehler, 228 erreichbare Grenzzellen, 72,10 % Boden, keine Passage. Kein Quellenfehler; tatsächliche Folgepfade `footprint_sweep_invalid`. Map-Save/exakter Checkpoint positiv, beide Kinder terminal/vier Befehlsströme null. Alle 769.062.555 Ereignisbytes lossless geprüft (98.546.057 Gzipbytes); noch keine Gesamtpositive.

**Neue Kausalreparatur B89:** B79/B80–B86 bleiben reine native Komponentenvergleiche, kein Plannerwechsel. Die gespeicherte aktuelle B76-Auswahl zeigt eine günstigere öffentliche Randtangente: 9 statt 4 endliche Potentialpunkte, Originalkosten ca. 1,55 statt 2,86, dieselbe Task-ID und ursprüngliche Limits. Die ursprüngliche Richtungsreihenfolge verbraucht ihr festes 0,5-s-Fenster zuvor an der nach hinten gerichteten Normalen. Original-Gegenprobe rot; repariert wird ausschließlich die Reihenfolge der vier vorhandenen Richtungen anhand der bereits gewichteten absoluten Lenkkosten. Native B88-Anfahrt, tatsächlicher Goalchecker-Stopp (0,14973 m), volle öffentliche Drehreserve und originale Abfahrt positiv. Zwei neue Regressionen und 46 gezielte bestehende Fälle grün; umfassender aktueller Build-/Testlauf noch laufend. [Originalnachweise und verworfene Vergleiche](evidence/ap06-missions-20261005/README_B80_B89.md). Keine Reserve, Frist, Nachbarregel oder letzte Native-Freigabe gelockert; kein zusätzlicher Bewegungsowner.

**Genau nächster Schritt:** B89 auf dem vollständigen geprüften Kandidaten binden und die ursprüngliche A/B/C-/Cancel-/Gyro-HOLD-Matrix erneut ausführen. Vorher Kapazität aus eigenen inaktiven und überprüfbar gesicherten Prüfcaches schaffen. Bei neuem Fehler erste kausale Ablehnung erhalten und im selben AP-06-Auftrag beheben. Noch 0/3, keine Zählung unterschiedlicher Kandidaten. Shutdown ausschließlich tatsächlicher verifizierter Jetson nach Abschluss, kein Cloud-Host-Shutdown.

### Lösungskonzept vom 06.10.2026 – von 0/3 zur vollständigen Softwareabnahme

Auf Nutzerwunsch erarbeitet; Konzeptstand, noch keine umgesetzte oder bestandene Gesamtreparatur. Basis ist der oben identifizierte v19-Arbeitsstand. MASTERPLAN v1.3, WE-M0/M3/M4/M5/M6 und bestehende Mission/BT/Explorer/Nav2/SLAM-Kette bleiben maßgeblich. Dieses Konzept konkretisiert den laufenden AP-06-Auftrag innerhalb dieses STATUS; es eröffnet keine zweite Roadmap.

**Gesicherte Befunde und offene Ursachen**

| Befund | Konsequenz für die Reparatur |
|---|---|
| v19: neue `valid_view`-Pflicht sperrt reine alternative Planvorschläge; bestehender Test rot, HEAD-Gegenprobe grün. | Eigenständige, bereits bewiesene Regression beheben. Sie entstand nach B68/B70 und erklärt deren ursprünglichen Stillstand nicht. |
| B68: zwei Ankünfte/Beobachtungen, 229 erreichbare Grenzzellen, erschöpfte Planvorschläge. B70: zwei Ankünfte/Beobachtungen, 226 Grenzzellen, zwölf zurückgestellte/als bedient behandelte Kandidaten. | Zwischen lokalem Fortschritt, erledigter Aufgabe, Cooldown und ausgeschöpften Versuchen unterscheiden. Welche konkrete Sperre eine sichere Folgebeobachtung verhindert, am ursprünglichen Entscheidungszeitpunkt beweisen. |
| B70: geplante Sicht auf 13 bzw. 9 Punkte, gemessene Gewinne 12 bzw. 2 Zellen; beide erfassten Abfahrtsprüfungen positiv. | Teilbeobachtung ist ein begründeter Reparaturansatz. Die Zähldifferenz allein beweist aber keine unerledigte Aufgabe: Originalpunkte gegen die frische Karte und tatsächliche Sicht prüfen. |
| Frühere native Pfade wurden wegen `footprint_sweep_invalid` abgelehnt; auf späteren Endkarten sind einzelne lokale Wege gültig. | Endkarten nicht rückwirkend als Freigabe der früheren Fahrt verwenden. Tatsächlichen Pfad mit dessen damaligen Raster-/Pose-/Controllerdaten prüfen. |
| B70-Save scheitert an der 512-MiB-Mindestreserve. Ereignisdatei allein 450.301.562 Bytes vor Kompression. | Eigenständige Kapazitätsvorsorge vor jedem Gesamtlauf; Speicherbereinigung repariert keine Auswahlentscheidung. |

**1. Reproduzierbare Entscheidungsnachweise herstellen**

Den vorhandenen v19-Fehlertest erhalten und zuerst die unbeabsichtigte Kopplung von `proposal_rejected` an den neuen Teilbeobachtungsnachweis lösen. Die Vorprüfung eines anderen rein lesenden Planvorschlags muss nach ursprünglichem Cooldown und innerhalb derselben Versuchslimits wieder möglich sein. Vollständige Sicht- und Bewegungsfreigabe erfolgen weiterhin an den dafür vorgesehenen späteren Prüfstellen. Alle Aufrufer von `MetricTaskPolicy.eligible` prüfen, insbesondere Vorprüfungen vor der Sichtberechnung; fehlende Sichtpunkte dürfen weder eine verfrühte Bewegung erlauben noch die benötigte Kandidatenberechnung unbeabsichtigt verhindern.

Für B68/B70 einen zeitlich passenden Komponentenfall aus Rohkarte, Costmap, Pose/TF-Bezug, Scope, ursprünglicher Beobachtungsbaseline, endlichem Scan, Kandidat und vollständiger damaliger Aufgabenhistorie erstellen. Historisch erschöpfte Aufgaben bleiben erschöpft; eine Reparatur wird an einem Zustand vor dem Fehlentscheid und dessen nachvollziehbarer Folge geprüft. Keine bereinigte Historie oder nachträglich günstigere Endkarte als Kausalnachweis verwenden.

Falls vorhandene Aufzeichnungen die erste Ablehnung nicht enthalten, genau diese Stelle begrenzt erfassen: Auswahlstufe, Task-ID, Sperrgrund, Versuche/Cooldown, Originalsichtpunkte und bei Geometrieablehnung tatsächlicher Native-Pfad samt erstem verletztem Kontur-/Rasterkriterium. Bestehende Diagnostik erweitern, keine neue Steuerinstanz. Erfassung bleibt beschränkt und zählt zur ursprünglichen Laufzeit; instrumentierte Läufe bleiben Diagnose. Volles Profiling während einer Qualifikationsmission entfällt.

Ergebnis dieser Stufe: ein roter/verhaltensbezogener Gegenfall je bewiesener Ursache. Wenn alle ursprünglichen Beobachtungspunkte bereits aufgelöst waren, wird die Teilbeobachtungshypothese für diesen Fall verworfen; dann führt die tatsächlich aufgezeichnete Kandidaten-/Geometriesperre die Reparatur.

**2. Fortschritt, Restaufgabe und begrenzte Wiederbeobachtung schließen**

`metric_progress.py`, `metric_frontier.py` und deren Einbindung in `metric_frontier_runtime.py` gemeinsam bearbeiten. Die bloße Ankunft bleibt ohne Beobachtungsreceipt. Tatsächlich neu beobachtete Zellen zählen als Fortschritt. Bleibt belegte relevante Restarbeit derselben Aufgabe, bleibt sie als `partially_observed` offen, ohne daraus einen Fahrfehler zu machen. Die ursprüngliche Baseline bleibt während des Versuchs einschließlich HOLD/Retry unverändert.

Eine weitere Beobachtung verlangt nach unverändertem Cooldown eine tatsächlich nützliche aktuelle endliche Sicht auf die Restarbeit und eine zulässige Beobachtungsposition. Die Prüfung verwendet den prognostizierten tatsächlichen Stopp und anschließend die wirkliche Ankunft. Reine Planablehnung, Teilbeobachtung und echter Fahrfehler behalten unterschiedliche Wiederholungsbedingungen. Räumliche Aufgabenbindung, Nachbarschaftsschutz, höchstens drei Versuche je Aufgabe, ursprüngliche Fehlerlimits und Gesamtbudget bleiben wirksam. Eine neue ID, ein neuer Kartenstempel oder eine kleine Zielverschiebung setzen nichts zurück.

Offene Teilaufgaben müssen auch durch spätere gültige Beobachtungen anderer Ziele auflösbar bleiben. Umgekehrt darf eine sichtbare Restfrontier nicht durch ein pauschales `completed` verschwinden. Dazu die kleine ursprüngliche lokale Restverpflichtung nachvollziehbar mit aktueller kartengebundener Evidenz abgleichen. Eine bloß aktuell verdeckte Sicht ist kein Erledigungsnachweis. Nachweislich durch beobachtete Wände abgetrennte unbekannte Bereiche dürfen gemäß Masterplan den metrischen Abschluss nicht dauerhaft sperren. Diese Auflösung erhöht keinen Beobachtungszähler ohne neuen echten Gewinn.

Aufgabenstatus und gegebenenfalls benötigte begrenzte Restdaten im vorhandenen Checkpoint erhalten; keine zweite Persistenz. Zusätzliche Felder nur bei nachgewiesenem Bedarf, mit explizitem Schemakontrakt und konservativer Behandlung älterer Daten. Save/Load und Wiederaufnahme erhalten IDs, Versuche, Cooldowns und abgelaufene Missionszeit. Laden erteilt keine Fahrtfreigabe. Alte gültige Sicherungen bleiben erhalten.

Pflichtregressionen: Teilgewinn mit verbleibender zugänglicher Restarbeit; vollständige lokale Auflösung; neue Wand versus bloße Sichtverdeckung; spätere Auflösung durch anderes Ziel; kein Gewinn bei alter/fremder Karte, Rasterinkompatibilität oder maskiertem Scan; alternative reine Planung; verweigerte Wiederholung bei erschöpfter Historie; HOLD/Cancel während Beobachtung; unveränderter Zustand nach Persistenz-Rundlauf. Die neue Logik wird nur übernommen, wenn der ursprüngliche Fehlentscheid verschwindet und diese Gegenfälle bestehen.

**3. Eine geometrisch zulässige Folge von Beobachtungszielen nachweisen**

Mit derselben Historie und frischen Produktdaten prüfen, ob die Auswahl eine nützliche Folgeposition vor dem Eingang, die vollständige Durchfahrt und die Weiterarbeit im zweiten Raum erzeugen kann. Vorhandene begrenzte lokale Kandidatensuche und echten NavFn/RPP weiterverwenden. Anfahrt, Sicht am tatsächlichen Stopppunkt und gesicherte Abfahrt müssen zusammenpassen. Bekannte Originalkollisionen an Türpfosten/Hindernis bleiben abgelehnt; Radius, Padding, Toleranzen und Lookahead werden nicht als Ersatz für eine funktionierende Zielwahl verändert.

Falls der nächste sichere Kandidat noch fehlt: zuerst den konkreten Verlust in Kandidatenerzeugung, Historienfilter oder Native-Validierung lokalisieren und nur diese Stelle ändern. Keine fest codierten Weltkoordinaten, manuellen Zwischenziele oder neuen Navigatoren. Rein lesende Native-Planabfragen bleiben im bestehenden Budget; Fehlversuche behalten ihre ursprüngliche Zählung. Ein positiver Weg auf eingefrorenen Daten ist nur ein Komponentenbeleg. Erst neue Bewegung mit daraus entstehenden Sensordaten kann eine Beobachtungsfolge bestätigen.

Geometrie-/Native-Regressionen umfassen die bisherigen neun Bewegungsfälle und den neuen konkreten Folgefehler. Zusätzlich Auswahl einschließlich Sichtberechnung innerhalb der ursprünglichen 5 s, lokaler Helper innerhalb 0,5 s, unveränderte Quellenfrische unter Last. Bei identischer Eingabe ohne neue Evidenz keine Serie gleicher fehlgeschlagener Missionsläufe.

**4. Prüfstand und finalen Kandidaten festlegen**

Vor jedem Gesamtlauf den verfügbaren Speicher gegen ein aus bisherigen unkomprimierten Datenraten auf die vollen 900 s abgeleitetes Laufbudget prüfen: Ereignisse, weitere Logs, Karte/Checkpoint einschließlich temporärer Schreibdateien, 512 MiB Mindestreserve und zusätzlicher Sicherheitsabstand. Die zuletzt freien 1,2 GiB sind keine zugesicherte Laufkapazität. Beendete eigene Nachweise verlustfrei archivieren und per Hash prüfen; nur sicher zugeordnete entbehrliche eigene Build-/Temporärdaten entfernen. Reicht der Platz nicht, zuerst Ausführungsvolumen erweitern oder verifiziert archivieren. Die Mindestreserve bleibt unverändert.

Ein finaler Quellstand, ein reproduzierbarer Build und eindeutig zugeordnete Installpräfixe. Zwölfpaketbuild, vollständige direkte Regression, registrierte colcon-Tests und betroffene native Prüfungen bestehen ohne neue Fehler. Neue Tests müssen auch in der tatsächlichen CI-Auswahl stehen; insbesondere die bisher ungetrackten B68-Komponentenfälle sachlich einordnen und bei Übernahme registrieren. Produkt-/Konfigurations-/Pluginhashes gegen den finalen Stand prüfen. Während einer Gesamtmission keine konkurrierenden Builds, Regressionen, Profiler oder Archivierungsläufe.

**5. Gemeinsame Endabnahme ausführen**

Die unveränderten Manifestfälle auf diesem identischen Kandidaten ausführen. B beginnt als gezielte Gesamtprobe; ein regulärer bestandener B-Lauf kann bereits zur finalen Matrix zählen, wenn Code, Parameter, Manifest und Prüfmodus danach unverändert bleiben. Danach A, C, Cancel und Gyro-HOLD. Ändert sich Produktcode oder eine wirksame Konfiguration, sind vorherige Positivläufe für den neuen Stand erneut zu bestätigen. Keine Vermischung mehrerer Kandidaten zu 3/3.

| Fall | Unveränderter Start `(x, y, yaw)` | Nachweis |
|---|---|---|
| A – `door68_start_a` | `(-1,9; -0,45; 0)` | Vollständige autonome Mission bei 68-cm-Türen |
| B – `door68_start_b` | `(-2,1; 0,45; 0)` | Vollständige autonome Mission aus bisher blockierter Startlage |
| C – `door80_start_c` | `(-1,6; 0; 0)` | Vollständige autonome Mission bei 80-cm-Türen |
| Cancel / Gyro-HOLD | jeweils `(-1,9; -0,45; 0)`, 80 cm | Originale Injektionen und Stoppkriterien; HOLD-Stopp allein belegt keine ACK-/Resume-Abnahme |

Ein Positivlauf verlangt echten Erfolg von Mission-Manager und Explorer, mindestens drei autonome Ankünfte mit qualifizierten Beobachtungen, vollständige Passage beider Türen einschließlich Heck, Weitererkundung im zweiten Raum und beobachtungsbedingtes Kartenwachstum. Mindestens 95 % der Referenzbodenfläche, höchstens 0,1 m Wandfehler und keine Kollision; Referenzwissen ausschließlich im unabhängigen Prüfer. Vor Erfolg keine relevante erreichbare Restaufgabe oder ungeklärte zugängliche Verbindung im ursprünglichen gültigen Abschlussfenster. Ein Nav-Kind gleichzeitig, eindeutige SLAM-/EKF-TF-Besitzer, am Ende keine aktiven Actions und alle vier Befehlsstufen null. Karte und exakter Aufgabencheckpoint müssen konsistent gespeichert sein.

Startbudget 60 s, Mission 900 s, Aufgabe 150 s, Cancel höchstens 3 s und Halt höchstens 1 s bleiben unverändert. Für jedes fehlgeschlagene Kriterium Originalbeleg und ersten kausalen Fehler sichern. Diagnose-Cancel, Teilkarte, bloßer Kartenzuwachs oder erschöpftes Budget zählen nie als Erfolg. Erst die gemeinsam bestandene Matrix belegt den Softwareteil; Zielsystem, physische Abnahme und native Apple-Prüfung bleiben getrennte Nachweise.

**Rückfall und Lieferung:** Kleine auf eine gemessene Ursache begrenzte Änderungen mit passenden Tests; nur eigene Änderungen gezielt zurücknehmen. Bereits geprüfte Referenz-/HWT-/NavFn-Korrekturen erhalten. Lieferung umfasst finale SHA und Installhashes, Build-/Testprotokolle, fünf Originalresultate und Kriterienmatrix. Es wird kein Datum oder sicherer Erfolg versprochen, solange die neuen Gegenfälle und Gesamtläufe fehlen.

## Erhaltener Zwischenstand 05.10.2026 – AP-06 Gesamtmissionsreparatur

**Aktueller Auftrag:** Nutzer verlangt die Behebung der Ursachen für 0/3 Gesamtmissionen. Basis `1b93694`, gleicher isolierter AP-06-Branch/Worktree; MASTERPLAN v1.3 und die fünf vollständigen Produktfälle unverändert. Voriger Auftrag bytegleich archiviert. Keine Hardwarefahrt, Deployment oder weitere AP-Arbeit.

**Gemessene Ursachen / laufende Reparatur:** millimeterverschiebende Karto-Rastergrenzen; Explorer-Worker durch wartende Geometriecallbacks belegt; tausende skalare Konturprüfungen überschreiten Kandidatenbudget; Lokalisierungskorrektur fälschlich als neue Rasterbeobachtung bzw. Verlust des ersten Körpers behandelt; Goalchecker-Akzeptanzscheibe mit erreichbarer RPP-Stoppbewegung verwechselt; exakter Karten-/Statusjoin nach Kindankunft trifft einen asynchronen Zwischenstand. Native rote Producer-/DDS-Gegenproben und synthetische Originalraster erhalten. Guards/Fristen, Ganzkontur, echte Source-Zeit und Abnahmen bleiben erhalten; erster nativer zusätzlicher Stopp in einer 68-cm-Passage positiv, gezielte Komponentenfälle grün. Volle Regression und endgültige Gesamtfälle laufen noch; kein neuer Gesamtpositivabschluss behauptet.

**Genau nächster Schritt innerhalb dieses Auftrags:** verbleibende nachgewiesene Gesamtfehler beheben, finalen Kandidaten mit Build/Regressionen und allen fünf unveränderten Gesamtfällen belegen; Ziel drei vollständige autonome Positivmissionen. Reale AP-06-/Apple-Abnahme weiterhin separat offen. Shutdown nur tatsächlicher Jetson bei nachgewiesenem Zugang/Identität, kein Cloud-Host-Shutdown.

**Überprüfbarer laufender Zwischenstand:** [Originalresultate und Rot-/Grün-Belege](evidence/ap06-missions-20261005/README.md). Kandidat **`16cbe5c`**: echte Native-Abfahrtsprüfung bei nominaler und ±0,05-rad-Prognoseorientierung, frühe gültige Planungswahl im bestehenden 5-s-Budget, begrenzte neue Zielgeometrie nach reiner Vorschlagsablehnung, echte Native-Umwegrückwege statt Direkt-Rückfilter, vollständig frische Wiederprüfung nach bestätigtem Halt bei spezifischem gebundenem Bearbeitungsablauf. Zusätzlich finite Sensorberechnung eigener Prozess: ein realer Isolationstest misst sonst 175 ms Sensorexecutor-CPU bei kaum ausgeführten Rad-/Gyrothreads. Welt/Strahlen/Takte/Guards/Abnahmen unverändert; keine neuen Sensorframes/Heartbeats aus altem Pflanzensnapshot, ursprüngliche Erfassungsstempel erhalten. Neuerer Zwölfpaketbuild und **1.945 direkte / 1.933 colcon-Tests grün**, keine Fehler/Skips; alle neun nativen Bewegungskomponenten ebenfalls geprüft. C38/C40 drei bzw. vier Ankünfte bleiben negative Gesamtstände; C39 Quellenpause, C41 gebundener Bearbeitungsablauf erhalten. C42 ebenfalls negativ: drei Ankünfte/Beobachtungen, 90,164 % Referenzboden, Quellen stabil; implizite Native-Pfade starten fälschlich bei (0,0), Controller meldet veraltetes map→odom. Isolierte konstante TF-Gegenprobe beginnt korrekt an der gemessenen Pose; Ursache des Gesamt-TF-Problems noch nicht bewiesen. Vollständig konsistenter älterer ROS-Prüfstand frisch gebaut (47 s), dieselben 1.945/1.933 Tests grün. Kandidat `ee7e21b` ergänzt passive Plan-/TF-Zeitstempel; C43 beginnt seine dynamischen Folgepfade korrekt, bleibt aber nach drei Ankünften/Beobachtungen mit tatsächlichem NavFn-ABORT negativ. Kandidat `4def089` hält nach terminalem rein lesendem ABORT begrenzte Alternativen offen; CANCELED/RPC-Fehler und beobachtete Schutzursachen bleiben hart. Drei rote Originalfälle, 25 betroffene Eltern-/Join-/Frischefälle grün. C44 erreicht sechs Ankünfte/fünf Beobachtungen und 96,850 % Boden, bleibt wegen 5-s-Auswahlbudget negativ. Originale erhalten. Kandidat `0f0fa42`: gleiche lokalen Inhaltsdigests innerhalb exakt gebundener Suchrunde, identische Halbzell-Strahlen nur bis zum ersten Stop berechnet; 124 betroffene Fälle grün, tatsächliche spätere C44-Suchrunde mit Profiler 4,776 s. C45 endet vor Missionsstart negativ: tatsächliche Radkontinuitätslücke 359,8 ms, gleichzeitige Quellen-Executorpause rund 330 ms bei 6–9 ms Prozess-CPU. Keine Fristlockerung oder Quellenentriegelung. C46 ist ein separat markierter Diagnoseversuch ohne Abnahmenachweis; keine lange Publisher-Blockade gemessen, Cleanup manuell beendet. A47 mit 177 zugänglichen Rohgrenzzellen ohne Aufgabe gestoppt (expliziter Analyse-Cancel, kein Positivnachweis). Kandidat **1de7c9b** findet zusätzlich nützliche, vollständig geprüfte Positionen auf der Roboterseite der Frontier im bestehenden lokalen Suchraum. Tatsächliche native Hin-/Abfahrtsprobe positiv; 200 betroffene Regressionen und sieben direkte Zusatzfälle grün. Gleiche Kontur/Scope/Quellen/Fristen/Trylimits; optionale bessere Geometriesuche maximal 0,5 s innerhalb der ursprünglichen 5 s. A48 bestätigt zwei Ankünfte/Beobachtungen, bleibt vor der Passage ohne Ziel. Seine erledigten entfernten Beobachtungsflächen sperren die Position für eine andere aktuelle unbekannte Grenze. Diagnose-Save/Analyse-Cancel separat markiert; anschließender Endsaveschutz lehnt den zu frühen zweiten Save ab, kein Map-Manager-Produktdefekt. Kandidat **b85a376** erlaubt nur tatsächlich endliche unbekannte Sichtpunkte außerhalb der alten Beobachtungsfläche mit zusätzlicher Wiederbesuchsmarge; Potential beendet keine Aufgabe, Zähler/Cooldown/Fristen/Alias-Gegenfälle bleiben erhalten. 213 betroffene Regressionen grün. A49 bleibt negativ: zwei Ankünfte/Beobachtungen, 62,446 % Boden, kein Heckdurchgang; tatsächlicher HWT-Terminalfehler und 192,199 ms Gyrothread-CPU, genaue Ursache noch unbewiesen. **c90b2d7** nutzt den sicheren Rundblick vor ausschließlich unbewiesenen Planungsanfragen (162 betroffene Tests grün). **95e82db** spart identische statische Modellgeometrie bei exakt unveränderter Pose ohne Geschwindigkeits-/Zähler-/Schutzänderung; Rot/Grün und 15 Modell-/Isolations-/Lebenszyklustests belegt. A50 endet ohne Quellenpause negativ (zwei Ankünfte/Beobachtungen, 62,150 % Boden); frische Kontur sperrt Folgeanfahrt, Karten-/Statusjoin verbraucht optionalen Scan. **4f500d0** erhält gemessenen Restwinkel desselben Scans nach bestätigtem Halt und frischem exaktem Paar innerhalb ursprünglicher 150 s; drei rote Gegenfälle/257 betroffene Tests grün. A51 diagnostisch bestätigt abgebrochen, eine Ankunft/Beobachtung, 65,278 % Boden, kein Durchgang; ursprüngliche erschöpfte Historie bleibt gesperrt. **7778771** prüft die bestehende sichere lokale Beobachtungsalternative unabhängig von einer abgelehnten normalen Anfahrposition; zwei rote Auswahlfälle, 130 betroffene/vier Native-Pfadregressionen grün. A52 diagnostisch abgebrochen nach erster Beobachtung, keine Passage; begrenzter Helper findet existierende sichere Position wegen Sichtarbeitsaufwand nicht. **df0c7c0** prüft gleiche Route vor endlichen Sichtstrahlen, owning Suche 0,358 s; zwei rote Gegenfälle/134 betroffene Tests sowie native Hin-/Abfahrtsprobe grün. A53 diagnostisch bestätigt abgebrochen: zwei Ankünfte/Beobachtungen, 73,268 % Boden, kein Heckdurchgang; voller gemessener Scan 6,300 rad mit Join-Wiederprüfung erfolgreich, danach erschöpfte Vorschläge ohne Folgeziel. Neue begrenzte öffentliche Beobachtungswahl findet im unveränderten vollständigen A53-Verlauf ein anderes zulässiges Ziel: finite unbekannte Sichtpunkte, ganzer Eigenweg und native Hin-/Abfahrt positiv. Originalaufgaben bleiben erschöpft; kein Gesamtpositiv daraus. A54 endet vor Diagnose-Cancel negativ am ursprünglichen 5-s-Auswahlbudget: zwei Ankünfte/Beobachtungen, 72,171 % Boden, kein Heckdurchgang. Öffentliche kurze Auswahl jetzt vor unbewiesener ferner Arbeit; erledigte identifizierte Aufgaben ausgeschlossen. Separat gleiche echte Ankunft nach SUCCESS außerhalb 15 cm innerhalb originaler Task-/Try-/Gesamtlimits erneut prüfbar, kein Receipt für den Fehlstand. Kandidaten `d7a4c91` / `f61f209`, inkrementeller Explorerbuild und 261 betroffene Regressionen grün. A55 diagnostisch bestätigt abgebrochen, zwei Ankünfte/Beobachtungen, 72,256 % Boden, kein Durchgang. `9130ee7` trennt öffentliche Wege vom Ablauf privater Referenz, drei rote Gegenfälle/271 betroffene Tests grün. B56 regulär negativ nach einer Beobachtung am 5-s-Auswahlbudget; tatsächlicher Status bestätigt private_epoch_expired=False bei valid=False/projected=0. Weitere begrenzte Korrektur schließt die spezielle erste Forward-Suche bei ungültigem privatem Bestand aus. **Weiterhin 0/3 vollständige Gesamtpositivnachweise; Reparatur läuft.**

## Erhaltener Stand 05.10.2026 – AP-06 Referenzbindung software_geprüft; gemeinsame Gesamtprüfung weiter blockiert

**Aktueller Auftrag:** Nutzer „repariere die Referenzbindung und prüfe mit denselben Szenarien erneut“; Basis `4351b8bb2018aa959aa84d6d6e8aa03621913e41`, unveränderter AP-06-Branch/Worktree. Reparaturen `e54c954` und **`3f66d73`**; MASTERPLAN v1.3 bytegleich. [Auftrag vor Fortsetzung archiviert](archive/20261005-ap06-reference/README.md). [Neue vollständige Originalnachweise](evidence/ap06-reference-20261005/README.md); vorige AP-06-Negativläufe bleiben erhalten. Kein Push/Merge, Deployment, Realversuch oder automatischer weiterer AP.

**Reparatur:** Erstes Raster/Polygon und monotone Abfahrtsflächen/-abstände bleiben in der ersten Odometriefläche fest. Pose und `map→odom` stammen vom selben tatsächlichen gemeinsamen TF-Zeitpunkt; jeder Input erhält diesen Bezug selbst. Kompatibles Wachstum/Korrektur löst frische Projektion und vollständige aktuelle Konturprüfung auf Rohkarte/Costmap sowie ursprünglichen monotonen Egress-Beweis aus, keine erneute Anfangserfassung. Nur vollständig vom erhaltenen Bestand gedeckte aktuelle unbekannte Zellen sind privat zulässig. Beobachtete Teilfläche lässt konservativ die ganze alte Zelle entfallen; keine Wiederbetretung, neue Unknown-/Obstaclefreigabe, Schema-/Kontext-/Auflösungs-/Fristlockerung oder Budgetreset. Geometriecache enthält keine Gesundheit/Bewegungsfreigabe. Quellenalter wird nach der gesamten Projektion erneut geprüft; ungebundener AP-02-Fallback bleibt strikt invalidierend. [Bewegungs-/Referenzvertrag](BEWEGUNGSVERTRAG.md).

**Softwareprüfung abgeschlossen:** sechsmal rot am echten bisherigen Produkt; **16 zusätzliche Fälle**, darunter echte TF2-Zeitkorrelation, gesicherte synthetische C-Startkarte mit rigidem Raster-/Referenzwechsel, echte Rückkehr, subzellige ungeklärte Außenfläche, Wachstum, Quellenverlust und Bearbeitungsalter. **1.860 direkte Tests / 1.852 colcon-Tests grün**, 0 Fehler/Skipped; Prüfmengen überlappen. Echter isolierter inkrementeller **Zwölfpaketbuild 6,65 s**, **136** installierte Produktdateien bytegleich auf beiden Prüfplattformen, **466** ausführbare Quell-/Test-/Konfigurationsdateien bytegleich zum Softwarecommit. Native Gesamtläufe auf Ubuntu 22.04/Humble/Python 3.10/rclpy 3.3.17; volle Komponentenprüfung 3.3.22. CI-Auswahl ergänzt, Remote-CI nicht ausgeführt. Kein ARM-Zielbuild behauptet.

**Dieselben Manifestfälle erneut; Positivmissionen 0/3:** A/B/C fahren autonom **19,560 / 18,230 / 17,594 cm** statt zuvor 5–6 cm; keine Zielankunft/Beobachtungsaufgabe/ganze Passage. Im neuen Ereignisarchiv tritt `start_egress_reference_expired` nullmal auf. A/B terminal `post_child_state_or_standstill_unconfirmed`, C `hwt_terminal`. Konkrete Quellengegenfälle im Explorer: A Radprobe 2,539 s alt; B Roh-/Yawprobe 2,753 s und Radprobe 2,788 s alt; C Radprobe 298,965 ms, Raw-/Yawstatus 2,733/2,443 s alt. Notwendige Frische bleibt unverändert, kein Sensor-/Kabel-/Schedulinggrund daraus erfunden. Parallel meldet das echte Fahrtor beim ersten Quellenfehler in A/B/C weiterhin HEALTHY. Zusätzlich entziehen subzellige aktuelle Raster konservativ volle Anfangszell-Deckung (`start_egress_new_unknown_or_obstacle`); eine gültige Referenz ist kein Freiraumnachweis. Die rigiden positiven Komponentenfälle beweisen keine erfolgreiche nichtganzzahlige Rasterabfahrt oder Gesamtmission. Rohkarten wachsen/55,032–58,054 % Referenzboden beobachtet; das ist kein Abschluss.

**Schutzfälle:** Cancel terminal 0,602 s, gemessener Halt 0,301 s ab Injektion; Gyro-HOLD Halt 0,268 s nach HOLD / 0,594 s ab Injektion. Beides innerhalb ursprünglicher 3-/1-s-Grenzen; echte 450-ms-Transportlücke, kein HOLD/ACK-/Fortsetzungsnachweis. Im Cancel-Fenster tritt auch ein eigener Radfrischefehler auf; kein isolierter Kausalnachweis ausschließlich der Cancellation. Alle fünf Läufe höchstens ein echtes Nav-/Explorerkind, eindeutig allein SLAM/EKF als TF-Besitzer, terminal keine aktiven Handles und alle vier Befehlsstufen null; unabhängiger gepaddeter Körper kollisionsfrei. Alle fünf echten Rohkartensaves erfolgreich, aktueller exakter Checkpoint jeweils unavailable; kein gesichertes Resume-Paar behauptet. Frühere vier passive Paare bleiben historische Teilnachweise.

**Abschluss/Zielsystem:** Eigene native ROS-Kinder beendet; nur Container-Init/Idle vor geordnetem Containerstopp. Nutzer-Shutdown ausdrücklich autorisiert und ältere Sperre im aktuellen Auftrag ersetzt. Tatsächliches Befehlsbackend weiterhin x86_64/Cloud, kein Jetson-Releasepfad oder `/home/p/roboter_ws`; letzter neuer App-Terminal-Leseversuch ohne Antwort beendet. Kein technisch verifizierter lokaler Jetson-Ausführungskanal, deshalb **Jetson nicht heruntergefahren** und ROBOT_TRANSFER unverändert. Zielsystem-/Real-/native Apple-Abnahme weiterhin offen; negative Gesamtfälle sperren Realfahrt unabhängig vom Zugang.

**Genau nächster Schritt bleibt AP-06:** Ursachen der Quellen-Verbrauchslücken während der frischen Geometrie-/Referenzauswertung messen und im vorhandenen Explorer begrenzt beheben; die nichtganzzahligen Raster-/Egress-Gegenfälle und dieselben fünf Manifestläufe dabei erhalten. Erst drei positive ganze Missionen erlauben den bestehenden technisch bedingten LAB-1-Zielvorlauf. Keine Fristen-/Kontur-/Unknown-Lockerung als Ersatz. Rückfall: nur `3f66d73`/`e54c954` gezielt revertieren/isoliertes Overlay abwählen; Originalcheckouts/AP-01–05/Main und vorige Nachweise erhalten.

## Erhaltener Zwischenstand 04.10.2026 – MASTERPLAN v1.3 / AP-06 software_korrekturen_geprüft; Gesamt-/Realabnahme blockiert

**AP-06 ist nicht vollständig abgenommen.** Nutzer „gut dann mache ap-6 fertig“; Basis `6a4a7df51c3ed152edb82ffa8b7dce5f1020f8e4`, Branch `feature/ap06-closed-product-validation`, Worktree `/workspace/Roboter_ws-ap06`. Geprüfter Software-/Prüfstandcommit **`ecb2586`**; vollständige Nachweise/Dokumentation anschließend. [AP-05-Auftrag bytegleich archiviert](archive/20261003-ap05/README.md). MASTERPLAN v1.3 bytegleich. AP-01–05 und ursprüngliche Arbeitskopie erhalten; kein Push/Merge, dauerhafter Install-/Autostartwechsel oder Rechner-Shutdown.

**Konkrete Codekorrekturen:** aktuelle ROS-Zeit für SLAM-/Körper-TF statt zukünftigem Latest-TF; identische stationäre Egress-Prüfungen nur je Kandidatenpass mit vollständigem Eingabeschlüssel memoisiert. Endpoint-only prüft das wirkliche Ziel statt nochmals den unbekannten Start; Anfahrt/Ankunft getrennt, Vororientierung und Proof am tatsächlichen interpolierten 0,4-m-RPP-Carrot. Beobachteter Parent-Abbruchgrund beim Planen bleibt erhalten, auch nach Quellenheilung. Begrenzte VL53-Räumendpunkte markieren keine Hindernisse mehr, echte separate Messwolken bleiben unverändert aktiv: nativer Rot/Grün-Fall 452→0 falsche Zellen, nahe Wand weiterhin 394 markierte Zellen. Bestehender Startadapter sucht zusätzlich die erste vollständig sichere nahe Beobachtungsposition mit echter Frontiersicht innerhalb des vorhandenen Suchradius/5-s-Budgets. Keine feste Wegpunktliste, kein Whitening, keine gelockerte Kontur-/Quellen-/Fristgrenze oder zweite Navigation. Mission-/VL53-/Safety-Pytestregistrierung und explizite DDS-Testbarriere korrigiert.

**Geschlossener tatsächlicher Gesamtpfad:** vorhandener Mission-Manager → nativer C++-BT → Explorer → echtes NavigateToPose/NavFn/RPP → Fahrtor → Velocity Smoother → Collision Monitor → Bewegungsmodell; nativer EKF allein `odom→base_link`, gepatchter SLAM allein `map→odom`, originale Scan-Normalisierung und Safety-Monitor. Welt liefert nur endliche verdeckende Sensor-/Rohregistermodelle und Schalteranforderung; keine Wahrheitskarte/-TF oder manuellen Nav-Ziele im Produkt. Originalstatus `synthetic:false` bedeutet auf diesem ausdrücklich isolierten Modell keine Hardwarequalifikation. Vorab festgelegte zwei Räume/Verbindung/68-/80-cm-Türen/Umweg/blockierte Alternative und drei Startposen erhalten; ursprüngliches 720-Profil, separat vorab deklariertes 2160-Profil und vollständiges Wahrnehmungsprofil samt negativen Zwischenständen erhalten.

**Endgültige vollständige Positivfälle 0/3:** A/B/C fahren autonom **5,748 / 5,647 / 5,180 cm**, dann `start_egress_reference_expired`; jeweils echte Nav2-Cancellation und Stillstand, terminal `blocked_help_required` / `completion_raw_pose_not_observed_free`. **Null Zielankünfte, null bestätigte Beobachtungsaufgaben**, keine ganze Türpassage/Heckfreigabe/Weitererkundung. Tatsächliche Referenzfläche 54,877 / 56,859 / 57,437 %, max. Wandfehler jeweils <2,5 cm; Kartenwachstum allein kein Abschluss. In C verschiebt die tatsächliche SLAM-Aktualisierung den Rasterursprung um −1,985 / −0,066 mm; feste Egress-/Körperreferenz verfällt. Dieser Schutz wurde nicht durch stilles Re-Ankern oder neue Freiraumannahme umgangen. Das ist das erste offene Gesamtsoftwarekriterium.

**Getrennte Schutzfälle bestanden:** Cancel terminal 0,204 s, gemessener Stillstand 0,331 s ab Injektion (Grenzen 3/1 s). Tatsächliche 450-ms-Gyrolücke erzeugt beobachtetes HWT-HOLD, Halt 0,242 s nach HOLD / 0,561 s ab Injektion; Mission terminal `hwt_terminal`, kein HOLD/ACK-/Fortsetzungs-/Resume-Positivnachweis. Alle fünf Endläufe eindeutige wirkliche TF-Publisher-GIDs, höchstens ein NavigateToPose-Kind/ExploreArea-Elternziel, terminal keine aktiven Handles und alle vier Befehlsstufen null. Volle unabhängige gepaddete Kontur kollisionsfrei. Drei negative Erkundungsmissionen bleiben negativ.

**Build/Test:** 17 native Supportpakete frisch gebaut und 14 gepinnte AP-03-Nav2-Pakete wiederverwendet, ursprünglicher frischer Neunpaketbuild samt echter C++-BT-Kompilation; VL53/Safety/Scan ergänzt, abschließender isolierter **Zwölfpaketbuild 6,41 s**. **1.844 direkte Tests**, **1.836 reguläre colcon-Tests**, jeweils vollständig grün ohne Fehler/Skipped; Mengen überlappen. **8/8 native Bewegungsregressionen** und nativer Nahbereichs-Rot/Grün-Fall bestanden. **135** installierte Produktdateien bytegleich zu geprüften Quellen, tatsächliche AP-06-Nachrichtenbindings/Modulpräfixe/Binär-SHAs gesichert. Native Gesamt-/C++-Prüfungen auf Ubuntu 22.04/Humble/amd64/Python 3.10.12/rclpy 3.3.17; vollständige Python-/colcon-Regression auf 3.3.22. Alter passiver DDS-Timingfehler auf 3.3.17 mitsamt Original-JUnit erhalten, 180-ms-Radfrische nicht gelockert. Kein ARM-/aktueller Jetson-Gesamtbuild behauptet. Native Upstream-Unit-Tests/Remote-CI nicht ausgeführt; Workflow-Auswahl ergänzt. [Originalnachweise, Pflichtfallmatrix und Prüfsummen](evidence/ap06-20261003/README.md).

**Persistenz tatsächlich begrenzt geprüft:** alle fünf echten Kartenmanager-Saves erzeugen synthetische Rohkarten. Vier exakte Karte-/Checkpoint-Paare (A/B/C/Cancel) passiv über originale Schema-/Prüfsummen-/Fingerprintfunktionen geladen, ohne Fahrfreigabe. Gyro-HOLD meldet ehrlich `metric_checkpoint_exact_saved_snapshot_unavailable`; kein vollständiges Backup dieses Falls. Aktive Relokalisierung/Wiederaufnahme und reale WE-M5-Wiederaufnahme offen.

**Zielsystemgrenze:** Nutzer präzisiert, dass die App auf dem Jetson läuft; App-Projekt `/home/p/roboter_ws` bestätigt. Tatsächlicher Befehlswerkzeugkontext bleibt x86_64/Debian 13/`/workspace`, ohne Jetson-Modellpfad, Gerätealiases oder jenen lokalen Projektpfad. Terminal-Anbindungsversuch lieferte ebenfalls Cloud-Kontext; letzte Terminalabfrage keinen zugeordneten lokalen Ausführungskanal. Cloud ohne VPN/TCP-Ziel/Robotercredentials. Keine neue LAB-1-Freigabe fehlt. Kein tatsächlicher Geräte-/Consumerlast-/Besitzerwechseltest oder Realversuch; ROBOT_TRANSFER unverändert. Selbst bei verfügbarer lokaler Ausführung sperrt das negative Gesamtsoftwarekriterium eine Abnahmefahrt. Native Apple-/WE-M7-Prüfung separat offen. Eigene temporäre Docker-Prüfprozesse/Container nach Nachweissicherung geordnet gestoppt; Originalcheckouts erhalten.

**Genau nächster Schritt bleibt AP-06:** feste erste unbekannte Egress-Kontur und aktuelle SLAM-Raster-/Referenzänderung geometrisch konsistent verbinden, mit frischem ganzen Fahrzeugbeweis und neuer gültiger Pfadbindung, ohne erneute Freiraumannahme/Wiederbetretung oder Budgetreset. Gesicherten bewegungsabhängigen Gegenfall zuerst schließen, dieselben drei Gesamtmissionen wiederholen; anschließend technisch verifizierter Zielsystem-/LAB-1-Vorlauf und Realabnahme. Keine automatische AP-07-/Installarbeit. Rückfall nur eigene AP-06-Commits gezielt revertieren; Räumstrahl-Revert stellt den belegten alten Fehler wieder her.

## 03.10.2026 – MASTERPLAN v1.3 / AP-05 software_geprüft; WE-M7 nativ offen

**AP-05-Kern, Persistenz und ROS-Verbraucherverträge software_geprüft.** Nutzer „gut mache weiter“ beauftragt AP-05 nach dessen konkreter Übergabe. Saubere Basis `2532f1b`, Branch `feature/metric-observation-persistence`, Worktree `/workspace/Roboter_ws-ap05`; Softwarecommit **`090762d93dd4c270478cb31c01c05d07c1da0459`**, Auftragscommit `4a370c0`. MASTERPLAN v1.3 bytegleich; [AP-04-Auftrag archiviert](archive/20261003-ap04/README.md). Keine Hardware, Roboternetzverbindung, Deployment, Push/Merge oder automatische AP-06-Arbeit. Originalcheckout und AP-01–04 bleiben unverändert.

**Fortschritt und Abschluss:** Ankunft allein erledigt kein Ziel. Tatsächlicher Gewinn erfordert neue passende Karte und neuen endlichen Scan, belegte unbekannt→beobachtet-Weltzellen ohne Wand-/Masken-/Reichweiten-/Rasterwiderspruch; nach Verarbeitung Frische und Originaldeadline erneut prüfen. Stationäre Beobachtung höchstens 2 s innerhalb ursprünglicher Goal-/Gesamtfrist; bestehender HWT-HOLD/ACK ohne neues Kind oder Budgetreset. Neue lokale Evidenz erlaubt nach Cooldown dieselbe Aufgabe erneut, höchstens drei Gesamtversuche, keine neue ID durch entfernte Kartenänderung. Gesamterfolg erst nach vorab festem mindestens **3-s-Fenster**, mindestens drei verschiedenen gültigen Scans und kontinuierlich keiner raw-erreichbaren Restaufgabe/ungeklärten zugänglichen Verbindung. Prüfung erfolgt vor Größen-/Geometrie-/Historienfiltern; hinter Wänden unbekannte Zellen verhindern Erfolg nicht pauschal. Letzter Callback-Race wird erneut geprüft. Datenverlust, Filter, Blockade, Versuchs- und Budgetende ergeben keinen Erfolg.

**Ergebnisse und Verbraucher:** `metric_complete`, `usable_partial`, `blocked_help_required`, `error`, `user_canceled` getrennt im versionierten metrischen Statusobjekt. Bestehende ExploreArea-Wirefelder unverändert; nur wirklicher metrischer Abschluss endet SUCCEEDED/true, Cancel terminal CANCELED/false. Bestehender BT-Erfolgspfad bleibt maßgeblich; Missiontelemetrie kann ihn weder beenden noch entsperren. Bestehende App-Modell/UI/Testquelle zeigen die Zustände und Ankunft/Beobachtung/Gewinn getrennt, keine metrische Bodenabdeckungs-Prozentbehauptung. Rohkarte, kumulativer Sichtgewinn, Fahrspur und Semantik bleiben getrennt; weder semantischer Vollabschluss noch unbekannte geschlossene Räume behauptet.

**Bestehende Persistenz:** Schema-1-Checkpoint an exakte gespeicherte Kartenidentität/Fingerprint/Sitzung/Scope gebunden, einschließlich Aufgaben/IDs/Versuchen und Goal-/Fehler-/Gesamtbudgets. Kartenmanager und Sidecar behalten ihre vorhandenen atomaren Einzelverträge; Abbruch zwischen beiden hinterlässt eine Rohkarte ohne Resume-Aufgabenstand, kein vollständiges Backup. Letztes gültiges Paar und gültige ältere Sidecarrevision erhalten. Keine stille Bindung an fremde Karte; Snapshot-Race konkret gemeldet. Laden passiv. Resume nur über explizites Prozessstart-Opt-in, originale Map-ID, neuen gültigen Auftrag, aktuelle Pose/Quellen und **frischen vorhandenen verifizierten globalen Lokalisierungsstatus** derselben Karte. TF/Ready-Bool allein genügt nicht. Ausfallzeit verbraucht Gesamtbudget; keine Versuchs-/Limitreset. Fehlender/ungültiger Resume überschreibt letzte Sicherung nicht.

**Tests/Build/Nachweise:** **65 neue Fälle**, **225 installierte Metriktests**, **1.751 betroffene Tests**, **1.664 registrierte colcon-Tests**, alle bestanden, keine Fehler/Skipped; Mengen überlappen. Frischer echter **Zehnpaketbuild**, anschließend Explorer-Neubuild und vollständiger Wiederholungslauf für letzte Deadline-/HOLD-Korrekturen. Ubuntu 22.04/Humble/Python 3.10.12/rclpy 3.3.22; localhost/Domain 230, network none, keine Geräte. Tatsächliche installierte Produktmodule/Config/Action bytegleich zum Quellcopy/Softwarecommit. Zwei echte DDS-Actionfälle belegen Erfolgs- und Cancel-Wirezustand; synthetische Karten/Scans/Pose und einzelne Nav-Gegenstellen bleiben Komponentenprüfung. Alle ursprünglichen Quellen-/Gate-/Geometrie-/Lifecycleverträge erneut geprüft. [Originalnachweise](evidence/ap05-20261003/README.md) mit Pflichtfallmatrix, roten AP-04-Ankunfts-/AP-05-Deadline-Gegenproben, sämtlichen Zwischenständen, Original-JUnit/Buildkommandos, Install-/Quellhashes und SHA256SUMS. CI-Auswahl ergänzt, Remote-CI nicht ausgeführt.

**Konkreter offener Plattformnachweis WE-M7:** Linux-Workspace ohne `swift`, `xcodebuild`, `xcrun`/Apple-SDK/Simulator. Native iOS-Build/Laufzeit und ergänzte Swift-Tests **nicht ausgeführt**; Python-Rosbridge-/ROS-Verträge sind kein Ersatz. Gemäß MASTERPLAN AP-05 bleibt dies separat offen und sperrt den unabhängigen Kernabschluss nicht.

**Grenzen/Rückfall:** Vollständige Mission/BT/Explorer/Nav2/SLAM-/Sensorkette und physische Start-/Mast-/Tür-/Tracking-/Stopplast weiterhin offen. Historischer synthetischer Graphprüfer nur an neue Resultassertionen angepasst, in AP-05 nicht neu abgenommen. Keine neuen Freiraumannahmen, Geometrie-/Fristlockerung oder Jetson-Profil-/Installänderung; ROBOT_TRANSFER unverändert. Rückfall ausschließlich eigene AP-05-Commits gezielt revertieren; AP-01–04 und fremde Arbeit erhalten.

**Genau nächster vorbereiteter Schritt: AP-06** gemäß MASTERPLAN v1.3 – zunächst vollständige bewegungsabhängige geschlossene Gesamtsoftwareprüfung mit den vorab festgelegten Szenarien/Startposen, anschließend separat technisch begrenzte Zielsystem-/Realabnahme. AP-06 **nicht begonnen**; der AP-05-Auftrag startet keine Robotertests. WE-M7-Nativprüfung bei verfügbarer Apple-Plattform zusätzlich schließen.

## Erhaltene Paketabschlüsse


## 03.10.2026 – MASTERPLAN v1.3 / AP-04 software_geprüft

**AP-04 software_geprüft auf Kandidaten-/Adapterebene.** Nutzer ausdrücklich „gut dann mach mit 04 weiter“. Saubere Basis `495b538`, Branch `feature/frontier-candidate-core`, Worktree `/workspace/Roboter_ws-ap04`; Softwarecommit **`5ee313b47ea2ef7c98554e42a9cae224a8a7d0ca`**. Originalcheckout und AP-01–03 sauber/unverändert. MASTERPLAN v1.3 bytegleich. Keine Hardware, Deployment, Push/Merge oder automatische AP-05-Arbeit. [AP-03-Auftrag bytegleich archiviert](archive/20261003-ap03/README.md).

**Entscheidung nach MASTERPLAN-Alternative:** Gepinnter unveränderter Fremdkern `mertgulerx/frontier_exploration_ros2@418e9717564a895214275e088ea7075b8ac88f64` wirklich gebaut, 134 Unit-Tests bestanden. Sein einziger Ringvorschlag scheitert an der gleichen Fahrzeugprüfung; am langen Rand bietet er unzureichend verteilte Sicht. Deshalb eigene Gewinnung begrenzt korrigiert und erneut verglichen: tatsächliche freie Randpunkte statt Schwerpunkt, mehrere räumlich getrennte Positionen, Annäherung zur bekannten freien Seite, aktuelle echte Scan-/TF-/Scope-/Reichweiten-/Maskenprüfung. Keine externe Runtimeabhängigkeit oder zweiter Navigator. `existing` bleibt Gesamtdefault; read-only `metric_candidate_source` wählt im expliziten metrischen Modus die Korrektur oder `legacy_centroid` als Rückfall. Bestehende Kontur-/Regler-/Quellen-/HOLD-/Kindverträge und Budgets erhalten.

**Abnahmen:** Alle sieben Pflichtfälle auf Kandidatenebene; Wachstum und Wiederbeobachtung über je drei Kartenstände. Unverändertes installiertes Original: Ring → `approach_unavailable` → null Ziele; korrigierte Gewinnung → fünf mit echtem Nav2 zulässige Alternativen. Langer Rand nach tatsächlicher vollständiger Pfadprüfung: **5,9 m** potenziell sichtbarer Rasterrand aus mehreren Eigenpositionen gegenüber **1,9 m** Fremdkern. Gleiche deklarierte endliche synthetische Sicht, Raster, Planung und Schutzbedingungen; kein gemessener Beobachtungsgewinn. **110 echte ComputePathToPose-Pläne**, **74** nach Produktgeometrie zulässig, davon **63** Eigenkorrektur; **36** unzulässige Zielgeometrien ehrlich verworfen. Kein FollowPath oder Motorpublisher. Ursprungrotation korrekt transformiert; Fremdbrücke lehnt sie explizit ab. Neue lokale Kartenevidenz nahe früherem Ziel liefert wieder Vorschläge; missionseigene Erledigung bleibt AP-05.

**Regression/Build:** **27 neue Fälle**. **1.636 betroffene Tests**, **165 gegen installierte Module**, **1.604 registrierte colcon-Tests** bestanden, keine Fehler/Skipped; Mengen überlappen. Frischer aktueller **Zehnpaketbuild**, frischer nativer **Achtpaket-Produktbuild**, unveränderter Fremdkern und CPP-Vergleichsbrücke gebaut. Neue und native installierte Produktmodule bytegleich zum Worktree. Echte Ubuntu-22.04/Humble-/Python-3.10-Laufzeiten, rclpy 3.3.22 bzw. native 3.3.17; keine Nachrichten-/Planerattrappen. Vorhandene AP-03-Nav2-1.1.20-Binärunterlage wiederverwendet, nicht als neuer Nav2-Build gezählt. CI ruft neue pytest-Datei auf; Remote-CI nicht ausgelöst.

**Originalnachweise:** [AP-04-Evidenz](evidence/ap04-20261003/README.md) mit Pflichtfallmatrix, allen nativen Pfaden/Planerlogs, Originalkern-Gegenbeispiel, gemeinsamen Eingaben, konkreten Befehlen, Pin/Lizenz, Image-/Installidentität und SHA256SUMS. Ein korrigierter neuer Minimalreichweiten-Test und erster nativer Prüferabbruch bleiben als Originalbelege erhalten. Keine Frist-/Reserveänderung, um grün zu werden. Historische unabhängige Python-3.12-/DDS-Befunde bleiben in AP-01/AP-03 erhalten.

**Grenzen/Rückfall:** Nur Kandidaten-/Adapter-/Planungssoftware geprüft. Potenzielle Sicht ist keine tatsächlich gemessene Beobachtung; native Plan-SUCCESS ohne volle Geometrie wurde abgelehnt. Mission/BT/Explorer/Nav2/Sensorkette, physische Start-/Mast-/Tracking-/Türabnahme und aktive Jetson-/Stopplast bleiben AP-06; AP-03-Simulationsprofil nicht für Hardware aktiviert. Große Karten oberhalb expliziter Kandidaten-/Sichtkapazität werden konkret blockiert, nicht als abgeschlossen gewertet. Alte missionseigene Erfolgs-Nachbarschaftssperre bleibt für **AP-05** offen. Rückfall nur eigene Software-/Dokumentcommits gezielt revertieren oder `legacy_centroid` beim gestoppten Start auswählen; AP-01–03 und fremde Arbeit erhalten. Kein Jetson-Installwechsel; ROBOT_TRANSFER unverändert.

**Genau nächster vorbereiteter Auftrag: AP-05** – Ankunft/Beobachtung/Erledigung trennen, begrenzte Wiederbeobachtung, ehrlichen Erfolgs-/Teilstandszweig und vorhandene Persistenz-/Verbraucherschnittstellen schließen. Noch nicht begonnen; eigene ausdrückliche Nutzerbeauftragung erforderlich. Vollständige Softwarekette und Hardwarequalifikation bleiben danach AP-06.

## 03.10.2026 – MASTERPLAN v1.3 / AP-03 software_geprüft

**AP-03 software_geprüft für die geschlossene synthetische Komponenten-/Bootstrapprüfung.** Nutzer hat AP-03 ausdrücklich beauftragt. Basis `875c7c4`, Branch `fix/nav2-bootstrap-geometry`, Worktree `/workspace/Roboter_ws-ap03`; Softwarecommit `c3115ff8ecb28b0828e1de8b8e062c6f0866f55e`. Originalcheckout, AP-01-/AP-02-Worktree sauber und unverändert. MASTERPLAN v1.3 bytegleich. Keine Hardware, kein Deployment/Push/Merge oder automatischer AP-04-Übergang. [AP-02-Auftrag bytegleich archiviert](archive/20261003-ap02/README.md).

**Umsetzung:** Ein ungültiger kürzester Eigenpfad schließt ein verbundenes bekanntes Ziel im neuen Opt-in-Profil nicht mehr dauerhaft aus. Er bleibt gekennzeichneter Nav2-Planungsvorschlag; vor jeder Vorausrichtung/Fahrt ist der tatsächliche Nav2-Pfad vollständig zu prüfen. Live/HOLD-Prüfung verwendet diesen tatsächlichen Pfad statt ihn durch eine andere Eigenroute zu verwerfen. Vorhandene NavFn-A*/RPP-Kombination nach Messung erhalten; kein weiterer Navigator oder Frontier-Kern. Numerische Sub-Halbzell-Endstücke erfinden keine Enddrehung.

**Geometrie:** Asymmetrischer Achsbezug, vollständiges Chassis x=−0,11…+0,31/y=±0,23 m und 0,02-m-Padding unverändert; halbe Zelldiagonale, 0,01-m-Interpolationsreserve sowie 0,15-m/±0,40-rad-Goalhülle bleiben geprüft. Neues schreibgeschütztes `rpp_rollout`-Simulationsprofil prüft tatsächliche berechnete Bewegungen einschließlich Drehen mit zusätzlich 0,02-m/±0,05-rad-Trackingband und erfordert aktivierte Vorausrichtung auf das erste tatsächliche Pfadstück innerhalb 0,02 rad. 17 echte Controllerparameter müssen passen. Bestehendes konservatives Profil bleibt Default. [Gemeinsamer Bewegungsvertrag](BEWEGUNGSVERTRAG.md).

**Geschlossene echte Nav2-Abnahme:** Acht Fälle bestanden. 68-/80-cm-Durchfahrt jeweils beide echte Actions erfolgreich, maximal rund 2 mm Tracking und mindestens 80/140 mm Abstand des gepolsterten Footprints. Längere 3,682-m-Umfahrung trotz verworfener Eigenroute erfolgreich, maximal 3,485 mm Positions-/0,005011 rad Headingabweichung und 201 mm Abstand. Vorbestimmte Tür-/Umfahrungsziele sind Komponententests, keine autonome Wohnungserkundung. Unzulässige 56-cm-Durchfahrt und Rotation im 68-cm-Spalt trotz NavFn-Punktpfad vor FollowPath verworfen; unbekannter Außenraum vom tatsächlichen Planer abgelehnt. Keine Nichtnullkommandos in diesen Negativfällen. Rückwärtsanteil sämtlicher positiver Fälle null.

**Autonomer Bootstrap:** Tatsächlicher bestehender Frontierdetektor/Approach/Policy wählt selbst einen ersten Beobachtungspunkt; Vollscan bei unbeobachtetem hinterem Außenraum gesperrt. Echte Nav2-Regelbewegung gewinnt im endlichen verdeckungsgeprüften synthetischen Sichtmodell 0,454 m² neue beobachtete Fläche. Fehlende initiale Kontur ergibt `wait` mit 168 fehlenden Zellen je Quelle, keine identischen Start-/Scanwiederholungen. Eigenkörper-/Egress-Ausnahmen und AP-02-Invalidierung bleiben erhalten. Separates begründetes reales Sensorpositions-/Abdeckungspaket im Bewegungsvertrag nur vorbereitet.

**Tests/Build:** 22 neue aussagekräftige Regressionen; Gegenprobe auf Original-AP-02: 18 erwartete Fehlschläge, 4 negative Fälle bestanden. Aktuelle AP-02-basierte Humble-Laufzeit: 138 Installtests, **1.609 betroffene Tests** einschließlich aller fünf echten DDS-Callbackfälle und **1.577 colcon-Tests** fehlerfrei; echter Zehnpaketbuild mit neuen Repo-/Nav2-Aktionsbindings und geprüfter Install-/Quellenidentität. Zusätzlich echte native Nav2-Planer-/Controller-/Pluginbuilds (14 Pakete) und acht Repo-Pakete in getrennter Installation. Mengen überlappen. CI-Auswahl und echter Nav2-Prüfjob ergänzt; kein GitHub-Lauf. [Vollständige Originalbelege und Reproduktion](evidence/ap03-20261003/README.md).

**Beobachtete Grenze:** Zwei Sammelläufe und ein erster Einzelversuch eines unveränderten engen DDS-Timingtests schwankten im älteren Nav2-Prüfimage (u.a. rclpy 3.3.17). Vier spätere Einzelprozesse dort sowie alle fünf Fälle und der vollständige Abschlusslauf auf AP-02-Laufzeit (rclpy 3.3.22) bestanden. Fehllogs erhalten; keine Ursachengarantie, kein allgemeines Last-Grün und keine Frist-/Schutzlockerung. Aktive Jetson-/Worst-Case-Abnahme bleibt AP-06.

**Offen:** Physische Türen/Startabdeckung und echte Motor-/Tracking-/Stopplast. Simulationsantwort 50 ms und 25-ms-Schrittkappe sind kein Nachweis für die reale 2000-ms-Antriebsrampe, Smoother, Schlupf und Sensor-/TF-Latenzen. Gesamte ExploreArea-/BT-/Mission-/Sensor-/Gatekette und Wohnungsvollständigkeit nicht als abgenommen ausweisen. Das Simulationsprofil ist nicht am Jetson aktiviert.

**Rückfall:** Nur eigene AP-03-Software `c3115ff` und zugehörige Dokumentation gezielt revertieren; AP-01/AP-02, Main/Jetson und fremde Arbeit erhalten.

**Genau nächster Schritt:** AP-04 gemäß MASTERPLAN v1.3 als eigenen begrenzten Softwareauftrag beauftragen. Keine automatische Frontier-Integration, Profilaktivierung oder Fahrt aus diesem Abschluss.

---

## 03.10.2026 – MASTERPLAN v1.3 / AP-02 software_geprüft

**AP-02 software_geprüft.** Nutzer hat AP-02 nach AP-01 ausdrücklich beauftragt.
Keine Hardware, kein Deployment/Push/Merge und kein automatischer AP-03-Übergang.
MASTERPLAN v1.3 bleibt bytegleich; sein ursprünglicher AP-01-Einstieg ist durch
AP-01-Abschluss und den ausdrücklichen Folgeauftrag abgearbeitet.

**Basis/Lieferung:** AP-01-Abschluss `45f268a` auf der bestätigten Integrationsbasis
`08a4b9a`; sauberer eigener Worktree `/workspace/Roboter_ws-ap02`, Branch
`fix/map-lifecycle-source-contract`. Softwarecommit
`96bbd4d8ed6d0b7a3ca6816d7c5fae14c27f45d4`. Originalcheckout und AP-01-Worktree
unverändert. [Aktueller abgeschlossener Auftrag](AGENTENAUFTRAG.md),
[bytegleich archivierter AP-01-Auftrag](archive/20261003-ap01/README.md).

**Konkrete Reparatur:** Raster-/Ursprungs-/Quaternionwechsel verwerfen alte
Egress-/betroffene Body-Evidenz vor Arrayoperationen, ohne Re-Ankern. Normale
passend korrelierte Folgeupdates erhalten neu geprüfte Weltziele. Exakte
Rohkarten-/Statusjoins ersetzen den aktiven Ersatzjoin mit alter Revision;
identischer Inhalt darf eng begrenzt den letzten exakten Snapshot innerhalb
seiner ursprünglichen Fristen erhalten. Verspätete Rohkarten überschreiben
auch den generischen Explorerstand nicht. Sitzungs-/Frame-/Auflösungs- und
beobachtete Rückwechsel sperren alte Arbeit und verspätete Plan-/Kindresultate.
Quellen-, Pose- und Scanfrische wird nach Verarbeitung erneut geprüft.
Der echte Kartenmanager erhält konsistente Beobachtungsrevisionen bei
Duplikaten und verwirft alte positive Stempel ohne Frische-/Revisionserneuerung.

**Gemeinsamer Vertrag:** [Karten-/Quellenbudget](QUELLENVERTRAG.md) ordnet HWT,
Encoder, TF, Gate und Explorer über Empfang, IO, Verarbeitung, DDS, Frische
und Kontinuität zu. Aktiver/passiver Pfad getrennt; bestehende Fristen,
Timingkern und AP-01-Clockvertrag erhalten. Kein allgemeiner Health-/Executor-
Umbau und keine vorgezogene AP-03-/AP-04-Geometrie-/Controller-/Frontierintegration.

**Abnahme:** 55 neue echte Lifecycle-/Produzenten-/Elternschleifenfälle:
100×100 → 100×101, Wachstum mit verschobenem Ursprung, Rohkarte/Costmap,
Auflösungs-/Sitzungs-/Frame-/Quaternionwechsel und Rückwechsel, verspätete
Arbeit, notwendige Quellen verloren, gültige Folgeupdates. Keine Arrayausnahme,
keine falsch gültige alte Maske und keine neue Freiraumannahme. Nav2-`success`
nach Quellenausfall/Kontextwechsel zählt keinen Besuch; gültiges Ziel bei
harmlosem Wachstum bleibt ausführbar.

**Ausgeführte Prüfung:** 1.587 betroffene Pytesttests bestanden, 116 gezielte
Tests gegen das neue Installationspräfix bestanden (einschließlich 55 neuer
Fälle), 1.555 registrierte colcon-Tests ohne Fehler/Fehlschläge/Skipped.
Mengen überlappen. Zehn Pakete mit echten Humble-/Nav2-/robot_interfaces-
Bindungen gebaut; Modul-/Paketauflösung und installierter Code geprüft.
Der Kartenmanager registriert nun tatsächlich seine 53 Map-Core-Tests für
colcon. Gegenprobe auf unverändertem AP-01-Stand: 30 erwartete Fehlschläge,
1 bestandener Fall, 24 abgewählte Fälle. Passende bestehende CI-Trigger und
Pytestauswahl ergänzt; GitHub-Actions nicht gestartet.

**Originalbelege/Reproduktion:** [AP-02-Evidenz](evidence/ap02-20261003/README.md)
mit Build-, Import-, Codehash-, Test-, Baselineausgaben, exaktem Skript,
Umgebung und SHA-256-Manifest. Der anfängliche Voll-`src`-Discoverybuild
scheiterte an nicht gebauten transitiven Launchpaketen; der explizite betroffene
Zehnpaketausschnitt wurde anschließend vollständig gebaut, ohne Dummy-Präfixe.
Dies belegt keinen kompletten Nav2-/BT-/Hardwarelaunch. Der bekannte
Python-3.12-JSON-Baselinefehler aus AP-01 bleibt unverändert außerhalb der
Humble/Python-3.10-Abnahme. Keine pauschale Gesamt-Grünbehauptung.

**Grenzen/Rückfall:** WE-M0 und betroffener metrischer WE-M3-Softwareanteil;
keine vollständige Meilenstein-, Zielsystem-, Start-/Geometrie-, Semantik- oder
Hardwareabnahme. Belastbare aktive Jetson-/Vollstackzeit bleibt AP-06.
Keine Runtimeänderung auf Jetson, deshalb kein neuer ROBOT_TRANSFER-Eintrag.
Nur eigene AP-02-Software-/Dokumentcommits gezielt revertieren; AP-01 erhalten,
keine fremde Arbeit oder pauschalen Altbranch zurücksetzen.

**Genau nächster Schritt:** AP-03 „Bewegung und autonomer Start zusammenführen“ gemäß MASTERPLAN als
separaten Auftrag mit echtem Nav2-Planer-/Controllerpfad und geschlossenem
synthetischem Bootstrap-/Geometrieprüfstand vorbereiten. Hier nicht ausgeführt
oder automatisch aktiviert; keine weitere Code- oder Hardwarearbeit aus AP-02.

## Historie

## 03.10.2026 – MASTERPLAN v1.3 / AP-01 software_geprüft

**AP-01 software_geprüft; Zielsystem, reale Sensor-/Start-/Geometrieabnahme und Wohnungserkundung weiterhin offen.** Kein Hardwarezugriff, Deployment, Push oder Merge. AP-02 ist ausschließlich als Übergabe vorbereitet.

**Basis und Lieferung:** Remote `feature/hwt-hold-recovery-resume` am 03.10.2026 auf `08a4b9ac0b7a128ced2199f20976f3aa92ea55fe` bestätigt. Ursprünglicher lokaler Checkout `work`/main `05439c7` sauber und unverändert belassen; isolierter Worktree `/workspace/Roboter_ws-ap01`, Branch `fix/hwt-clock-correlation`. Keine unbekannten lokalen Änderungen auf der Integrationsbasis. Dokumentübernahme `84abfc6`, geprüfter Softwarecommit `c797442b37994f774df40b6b27d54c27efa3bdc3`. Keine aus einem Branch abgeleitete Jetson-Installationsbehauptung. WE-D0/WE-M0 und betroffener WE-M3-Recoveryanteil.

Kanonisch: [MASTERPLAN v1.3](MASTERPLAN.md), [abgeschlossener AP-01-Auftrag](archive/20261003-ap01/AGENTENAUFTRAG.md), [Meilensteine](MEILENSTEINE.md), [LAB-1](../LABORMODUS.md). Die vier Vorgängerdateien sind mit Commit-/Blob-/SHA-256-Beleg [bytegleich archiviert](archive/20261002-v1.2/README.md); MASTERPLAN entspricht dem Anhang bytegleich. AGENTS/Meilensteine/Gesamtstrategie und PROJECT_MEMORY gezielt synchronisiert, begrenzte AP-04-Erlaubnis ausdrücklich übernommen. ROBOT_TRANSFER unverändert.

### Reparatur und Zeitvertrag

Produktänderungen nur in `hwt601_imu_node.py` und dem privaten `_hwt601_clock.py`. Transport, Guard/Health, Encoder, EKF, Bias, Profile, Mission/Explorer und Recoverycode unverändert. Der echte Transport bleibt vollständiger Hostempfangsbeleg, nicht interner Sensorabtastzeitpunkt. Fehlender/ungültiger Empfangs- oder Transaktionsbeleg wird jetzt hart zurückgewiesen; kein Fallback auf Verarbeitung/Veröffentlichung.

Monotonic rahmt die ROS-Abfrage ein. Präzise Offsetspannen werden geschnitten; ein Bracket von höchstens **1 ms** und höchstens **drei** sofortige Versuche innerhalb derselben echten Transaktionsfrist. Unterer Offsetrand gibt konservativ höchstens 1 ms + 2 ns früheren Empfangsheader; kein Futurefehler durch wechselnden Mittelpunkt. Die Grenze entspricht 1/10 des nominellen Probenabstands und 1/100 der unveränderten Biaskontinuitätsgrenze. Größere Brackets werden verworfen, ohne letzten gültigen Empfang/Header/Samplehistorie zu ändern oder den Transport zu schließen. `clock_correlation` unterscheidet Unsicherheit und Zeitbasisänderung.

Disjunkte Belege bleiben harte Zeitfehler, auch wenn Header noch steigen; keine Neubasierung. Aktive ROS-Time/`use_sim_time`, Clockobjekt-/Typwechsel sowie zwischen Polls aktivierte/deaktivierte ROS-Time werden konservativ gesperrt. Unterstützt: unveränderte Host-SYSTEM_TIME oder inaktive ROSClock mit Hostzeit. Sprünge unter Messunsicherheit sind nicht garantiert erkennbar; der Hostvertrag verlangt denselben laufenden Taktbezug. Siehe [ausführlichen Clockvertrag](../../src/robot_state_estimation/README.md#ap-01-hostempfang-und-clockvertrag-masterplan-v13). Entwicklung bleibt bei harten Fehlern terminal; Legacy-Hard-/Reconnectbehandlung bleibt erhalten.

Unverändert: Entwicklung 50 ms Antwort/Gesamtablauf und 300 ms Rohfrische; Legacy 30/200 ms; Encoder 120/180 ms; Bias-/HOLD-/Recoverygrenzen. Messagebau/Paarungsversuche werden ebenfalls vor Veröffentlichung gegen die Gesamtdeadline geprüft. Wiederholte Unsicherheit führt durch das Alter der letzten echten Probe zur bestehenden Health-HOLD-Reaktion.

### Vorher/Nachher und Pflichtfälle

[Originalmethoden vor Reparatur](evidence/ap01-20261003/ap01-original-method-proof.json): erster Header `1010,000 s`, zweiter echter Empfang `1010,010 s`, nach ROS-Abfrage 20 ms Pause → berechnet `1009,990 s`, terminal `HWT-Messzeit nicht monoton`, Transport geschlossen, nur ein veröffentlichter Wert. [Gewünschter Regressionstest rot](evidence/ap01-20261003/ap01-before.log).

[Reparierte Methoden aus dem Install](evidence/ap01-20261003/ap01-repaired-method-proof.json): zweite Paarung bei monotonic `10,030 s` gültig, Header bleibt exakt Empfang `1010,010 s`; spätere Probe `1010,040 s` ebenfalls veröffentlicht. Drei akzeptierte Werte, null verworfene Werte, kein Terminalfehler, Transport offen. Keine Testnachbildung der Poll-/Fehlerentscheidung.

| Pflichtklasse | Tatsächlicher Nachweis in `test_hwt601_time_correlation.py` |
|---|---|
| Präzise +10 ms, wechselnde kleine Brackets | exakter Empfangsbezug; kontinuierlicher gültiger Strom, zwei konstante Offsets, Fehler ≤1 ms |
| Originalpause, Verzögerung vor/in/nach Paarung, konstant/wechselnd groß | korrekt datiert; erneute präzise Paarung statt Mittelpunktprojektion |
| Unbrauchbar → präzise, wiederholt unbrauchbar | kein Zwischenwert/Reset; letzte gültige Daten altern, nächste echte Probe verarbeitet |
| Transaktions-/Verarbeitungsfrist | 30-/50-ms-Gegenfälle für Verarbeitung, Retry, Dekodierung und Messagebau; keine Publikation |
| Fehlend/NaN/Inf/zukünftig/rückläufig/wiederholt | echte Poll-/Fehlerlogik weist Beleg zurück, kein Ersatzzeitpunkt |
| Unabhängige ROS-Sprünge, kleiner als Probenabstand | ±2/±20 ms bei steigender monotonic erkannt; selbst bei weiter steigenden Headern terminal |
| Tatsächliche Clock-API/Quellenwechsel | echte ROSClock/TimeSource und unabhängige Overrideänderung; Aktivierung/Deaktivierung auch zwischen Polls erkannt |
| Verbundene Verbraucher | echte Guard-/Health-Zeitprüfung akzeptiert erzeugte Header bei 0/0,05/2 ms Zustellung; Future-Gegenfall bleibt hart; echte Alterung bewirkt HOLD |
| Transport/Schutzwirkung | echter serieller Produkttransport + synthetische Gegenstelle, ganz/fragmentiert und verzögerte Dekodierung; CRC/Identität/Timeout bestehend, Sättigung zusätzlich |

### Befehle, Ergebnisse und Auflösung

Vollständige Aufrufe: [ap01-run-final.sh](evidence/ap01-20261003/ap01-run-final.sh). Plattform und Präfixmapping: [Evidenzregister](evidence/ap01-20261003/README.md). Ubuntu 22.04/x86_64, echtes ROS Humble, Python 3.10.12; localhost/Domain 226 für DDS-Tests. Keine Geräte eingebunden.

| Ausführung | Ergebnis | Originalbeleg |
|---|---|---|
| `colcon build --packages-select nav2_common nav2_msgs amadeus_map_identity explore mission_manager robot_state_estimation robot_interfaces base_hardware`, getrennte Build-/Installpräfixe | 8 Pakete bestanden | [Buildlog](evidence/ap01-20261003/ap01-verified-build.log) |
| `pytest` neue Clock-/Rawtests, nur Testpfad plus frisches Install | 58 bestanden, davon 52 neue AP-01-Fälle | [Installtests](evidence/ap01-20261003/ap01-regressions-installed.log) |
| `pytest` vollständige state/base-Tests, Gate-Integration/pending-wheel/source-callbacks, HWT-Recovery/Kindpolitik/Kindvertrag, Mission-HWT und JSON | **443 bestanden** | [Regressionen](evidence/ap01-20261003/ap01-regressions-final.log) |
| `colcon test` state/base und `colcon test-result --verbose` | **381 Tests, 0 Fehler/Failures/Skips** | [Registrierte Ergebnisse](evidence/ap01-20261003/ap01-colcon-results.log) |

Mengen überlappen; nicht addiert. Neue Tests laufen bereits in `.github/workflows/hwt601-we.yml`: PR-Pfadtrigger `src/robot_state_estimation/**` und `python3 -m pytest -q src/robot_state_estimation/test ...`. Kein unzureichender unittest-only-Aufruf; keine CI-Neugestaltung nötig. Colcon hat die neuen 52 Fälle tatsächlich gesammelt. Hosted CI wurde mangels Push nicht neu ausgelöst.

[Importauflösung](evidence/ap01-20261003/ap01-imports-installed.log): Raw/Clockhelper aus `/evidence/ap01-install/robot_state_estimation/lib/python3.10/site-packages`; `robot_interfaces` aus neu gebautem `/evidence/ap01-install/robot_interfaces/local/lib/python3.10/dist-packages`; Standardnachrichten/rclpy aus `/opt/ros/humble`. Weitere Verbraucherprüfungen nutzen aktuellen Worktreecode und diese echten Nachrichtenbindungen. Fünf relevante Quell-/Installmodule [bytegleich mit SHA-256 geprüft](evidence/ap01-20261003/ap01-byte-manifest.json). Container `/evidence` entspricht Host `/workspace/scratch`, `/repo` dem isolierten Worktree; kein alter main-Import. Entwicklungs-/Legacyparameter sind explizit in den Fixtures gesetzt; kein behauptetes geladenes Jetsonprofil.

**Unabhängiger Baselinefehler:** Python 3.12.14 / Missionmanager-JSON-Tiefentest nimmt 2.000 verschachtelte Arrays an. [Vorher](evidence/ap01-20261003/ap01-json-before-python312.log) und [nachher](evidence/ap01-20261003/ap01-json-after-python312.log): je 4 Tests / 1 Fehler, Produkt-/Testbytes unverändert. Unter Humble/Python 3.10 besteht derselbe Test in den 443. Nicht behoben, nicht gelöscht/übersprungen oder als Python-3.12-Erfolg gezählt; außerhalb AP-01 und kein Blocker dieses geprüften Zeitpfads.

### Grenzen, Rückfall und genau ein nächster Schritt

Keine Zielsystem-, aktive Last-, Sensor-/Start-/Geometrie- oder Fahrabnahme. Der historische Roboterabbruch ist nicht abschließend erklärt; nur das konkrete Projektionsgegenbeispiel ist behoben. Keine vollständige EKF-/Robotergrafabnahme behauptet; direkte echte Verbraucherkomponenten erfüllen den begrenzten Zeitvertrag. Keine private Wohnungsevidenz übernommen.

Rückfall: eigenen Softwarecommit `c797442` gezielt revertieren und Paket im getrennten Präfix neu bauen; der dokumentierte Originalfehler kehrt dabei zurück. Keine pauschale Branch-/Installrücksetzung. Dokumentübernahme ist unabhängig prüfbar. Laufende Roboterkopie und ROBOT_TRANSFER unverändert.

**Genau nächster Schritt:** den vorbereiteten begrenzten **AP-02-Auftrag** zu Kartenlebenszyklus/Quellenvertrag gemäß MASTERPLAN v1.3 beauftragen. Konkrete betroffene Pfade und Akzeptanzfälle stehen in der [AP-02-Übergabe am abgeschlossenen Auftrag](AGENTENAUFTRAG.md#ap-02-übergabe-vorbereitet-nicht-ausgeführt). Keine automatische Implementierung oder Fahrt.

Der folgende vollständige STATUS ist ausschließlich Historie bis `08a4b9a`; dortige „aktuelle“ Überschriften, Aufträge und Runtimeangaben gelten für den damaligen Stand.

---

# Wohnungserkundung – aktueller Status und nächster Auftrag

**WE-1 · Stand 01.10.2026 · MASTERPLAN v1.2 · Stufe 3 weiterhin OFFEN**

Maßgeblich: [MASTERPLAN](MASTERPLAN.md), [AGENTENAUFTRAG](AGENTENAUFTRAG.md), [LAB-1](../LABORMODUS.md), [MEILENSTEINE](MEILENSTEINE.md). Dies ist der einzige aktuelle WE-Iststand. Die ausführliche bisherige Statusdatei ist [bytegleich archiviert](archive/20260930-v1.1/STATUS.md); alte Abschnittsnummern und „nächste Schritte“ dort sind historische Referenzen.

**Aktueller Abschluss:** HWT-Entwicklungsvertrag und Start-Egress auf `a6f31bf`
implementiert; 1.564 Regressionen, gerätefreier Drei-Ziel- und HOLD-Produktgraph
bestanden. Kurzer Realstart: HEALTHY nach 36,379 s, terminale Messzeitprüfung
bei 54,880 s; aktuelle Geometrie verwirft alle 22 Kandidaten. Keine reale
Mission. Quellenzeit und konkrete Bewegungsgeometrie blockieren unabhängig.
ROS beendet, Rechner eingeschaltet; Einzelgrenzen im neuen Abschluss unter §4.

**Abschluss des vorigen Pakets 01.10.2026:** Adaptiver metrischer Bootstrap und begrenzte
Encoder-Timing-Recovery auf `fd883fd` softwareseitig geprüft. Gemeinsamer realer
Vorlauf negativ: dritte HWT-Störung erschöpft das Budget; unabhängig davon 33
unbekannte Startkonturzellen / 0,021089 m² Außenanteil, kein zulässiger Startkandidat.
Keine reale Mission. Einzelbelege, voller negativer Dauertest und Grenzen im
neuen Abschluss unter §4 sowie AGENTENAUFTRAG §10. **System bleibt eingeschaltet.**

## 1. Aktuelle Nutzerentscheidung

Normale Erkundung wird metrisch organisiert: beobachten → erreichbare Frontier-/Beobachtungsposition wählen → navigieren → neue Beobachtung und Ergebnis bewerten → nächste Aufgabe. Portal-/Raumsemantik ist keine Pflicht für normale metrisch sichere Ziele. Geometrie, Karte/Pose, Scope, Sensor-/Antriebsgesundheit und Schutzkette bleiben verbindlich.

**GRÜN: METRISCHER ERKUNDUNGSKERN – GERÄTEFREI INTEGRIERT BESTANDEN.** Implementiert als explizites `metric_frontier`-Backend im bestehenden Explorer. Default bleibt `existing`. Beim anschließend beauftragten Realnachweis wurden reale Sensor-/ROS-Prozesse im rein lesenden Vorlauf gestartet; dieser blieb blockiert, keine aktive Fahrt oder Mission, kein dauerhafter Installwechsel. Stufe 3 bleibt **OFFEN**. Konservative Geometrieprüfung bleibt verbindlich; reale Zielerreichung, Türpassage und Robustheit sind nicht aus den Softwaretests abgeleitet.

**Historischer Abschluss des vorigen Pakets (01.10.2026):** Ausgang `cf55cea`,
Funktionskandidat `8f5eeb4`, bestehender Branch/PR #105. 1.469 Regressionen
bestanden; Radübernahme, Uhrzuordnung und ganze Eigenkörperzellen gezielt
korrigiert. **Realer 720-s-Gesamtvorlauf negativ, keine Mission/Fahrt.**
Letzter Fehler nach zwei echten HWT-Recoveries: 120,874 ms verworfenes
Encoderpaar, anschließend 212,127 ms alte letzte zulässige Radprobe am Gate.
Unveränderte 120-/180-ms-Grenzen sperren richtig. Geometrie unabhängig davon:
211 unbekannte Rundblickzellen, 0,188420 m² Außenanteil; bereits Anfangskontur
unzulässig. Genaues Ergebnis und Restumfang im aktuellen Abschluss unter §4,
Auftragsabschluss in AGENTENAUFTRAG §9. Der folgende adaptive Auftrag hat diesen
Restumfang gezielt ersetzt; alte Messungen bleiben unverändert erhalten.

## 2. Belegter Ausgangspunkt

| Stand | Beleg / Grenze |
|---|---|
| Remote-Dokumentbasis vor v1.2 | PR #105, feature/hwt-hold-recovery-resume, `99d21c012dfe4c28d8263f7cd5e16505b07736d6`; keine Aussage über aktuelle lokale Runtime |
| Letzter ausgewerteter realer Kandidat | `492ef20`, Ergebnis `d480243`; vollständiger zweiter Lauf stage3-map-handoff-20260929/real-repeat |
| Historischer Funktionsvergleich | `1d91229dc10ff4bb791938d49aae8e9808a5dfff`; [WE_PARITY_RESET](../WE_PARITY_RESET.md) dokumentiert Frontierfahrten, verbundenen Türübergang und weitere Frontiers danach |
| Erster HWT-Recoveryfall | Gerätefreier aktiver Kindzielvertrag und reale Rundblick-HOLD/Recovery/Fortsetzung im dokumentierten Umfang akzeptiert; kein umfassender Robustheitsnachweis |
| Aktueller Erkundungserfolg | Kein bestandener zusammenhängender A/B/C-/Mehrraumlauf; kein Ziel- oder Türerfolg des letzten Laufs |
| Neues metrisches Backend | Software und Mast-/Encoderkorrekturen auf `8be0709` regressiert; gemeinsamer realer Vorlauf weiter negativ, kein Fahrnachweis |

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

**Damals nächster Schritt, im folgenden Abschnitt ausgeführt:** gezielter Vorlauf-Korrekturauftrag für Startkarten-/Kontur- und FC03-Paarzeitblocker mit getrennten Nachweisen und unveränderten Schutzgrenzen. Aktuelle Voraussetzung ausschließlich im Abschluss vom 01.10.2026.

### Historisch bis cf55cea: Mast-/Eigenkörpervertrag und Encoderzeitpfad

Auftrag vom 30.09. auf veröffentlichtem `0efb7e4`, funktionaler Abschluss
`8be0709` in derselben PR-#105-Linie. **Softwarekorrekturen regressiert;
gemeinsamer realer Vorlauf negativ. Keine Mission und kein Fahrnachweis.**

**Mast:** Betreiberzuordnung OAK-Kameramast verbindlich übernommen. Vorhandene
native Maske 236–304°, NaN-Ausgabe und ROS-CCW bleiben unverändert. Im letzten
Vorlauf: 2.325 Rohscans / 2.287 normierte Scans; im robusten Sektorinneren
57–123° sind sämtliche 924.632 / 905.652 Bins NaN. Die 1° Randreserve dient
nur dieser Auswertung unterschiedlich diskretisierter Scans, verändert keinen
Filter. Tatsächlicher statischer TF aus der Bag: x 0,245, y 0, z 0,660 m,
yaw +1,5708. Manifest belegt Crop=true und tatsächlich gestartete Parameterdatei.
Der native Treiber beantwortete den Parameterdump nicht; deshalb kein erfundener
Live-Parameterbeleg. `/scan` → vorhandene Vereinheitlichung → `/scan_normiert`
→ SLAM/Explorer/HWT-Beobachter/Gate; Costmaps nutzen Rohkarte und ihre vorhandenen
VL53/OAK-Quellen. SLAM-Präfix `~/amadeus_slam_toolbox_ws/install/slam_toolbox`,
Patchparameter live true; installierte `libtoolbox_common.so` enthält den Patch.
Keine neue Drehfahrt oder Kalibrierung daraus ableiten.

**Startkorrektur:** `metric_self_body_enabled` erlaubt privat nur ganze unbekannte
Zellen im ungepaddeten gemessenen Körper x −0,11..0,31 / y ±0,23 m, einschließlich
Zellenecken und Scopeprüfung. Erste korrelierte Pose und Rohkarten-Fingerprint
fixieren den Beleg; er folgt keiner Bewegung und erlischt bei geändertem
Fingerprint. Frische Pose/Scan und passender planarer Montage-TF bleiben Pflicht.
Belegte Zellen, Costmap-Unknown, Außenkeil, Padding und Rasterreserve werden nicht
freigegeben. Rohkarte bleibt bytegleich; volle Kontur x −0,13..0,33 / y ±0,25 m
und ihr Bewegungs-/Drehsweep bleiben geprüft. Keine Garantie für einen Rundblick
allein aus belegtem Eigenkörper.

Der alte Startsnapshot bleibt reproduziert: unbekannte Startzelle, unzulässige
Kontur und 25 `no_known_free_route`. Bei 325 berührten Zellen: 88 ganz im Körper
liegende unbekannte Zellen, 4 Randzellen mit Körperüberschneidung, 16 im Padding,
18 in Rasterreserve; 0 Rohkartenhindernisse. Alte Costmap: 1 unbekannte Zelle in
Rasterreserve, 143 Inflationszellen, 0 Zellen mit Wert ≥100. Rasterkosten beweisen
keine bestimmte physische Objektidentität. Der neue Startsnapshot zeigt 78 ganze
Körperzellen, 16 Körperrand-, 16 Padding- und 18 Reservezellen weiter unbekannt;
Costmap 2 unbekannte Reservezellen, keine Kosten >0 in der berührten Kontur.
Die ganzen Körperzellen werden korrekt getrennt; der unzulässige Außenanteil
bleibt wirksam. Startzentrum nach Clearanceprüfung false, volle Roh-/Costkontur
false, bereits erste Scanorientierung false. 15 reale Cluster, 15
`no_known_free_route`, 0 akzeptiert. Keine freie 360°-Drehung nachgewiesen.

**Encoderkorrektur:** gemeinsame FC03-Blöcke Position/RPM erhalten. Instrumentiert
sind Alias/USB vor/nach Zugriff, Modbus, Antwortprüfung, Paar, Motorversatz,
Pollstart und Publikationsalter. Nur USB-Attributpfadsuche gespeichert; tatsächliche
Identität/tty-Gerätegeneration, Alias und Exklusivität vor/nach jeder Probe sowie
CRC/Antwortprüfung bleiben aktiv. Paarzeit 120 ms und Datenlücke 180 ms unverändert.
Nach ≥20 gesunden Paaren darf ein einzelnes vollständiges Timingpaar bei belegter
Kontinuität verworfen werden: Quelle unbereit, Transport weiter lesend, zwei neue
vollständige plausible Paare. Erstes gültiges Paar integriert sämtliche Zähler
und publiziert weiter unbereit; zweites stellt Readerbereitschaft wieder her.
Passives HWT geht dabei in den vorhandenen HOLD/Validierungsvertrag. Keine
Faultflag-Löschung, Pose-/Baseline-Nullung oder unterschlagene Bewegung.
Anhaltende Verzögerung, lange Lücke, unvollständige Antwort, Portwechsel/-verlust,
unplausible Zähler, Zeitrücklauf und harte Schutzfälle bleiben gesperrt.

Erster Vollstackstart vor der dritten Probe: Pollstart 197,695 ms, Paarzeit
97,920 ms. Terminal, `rebases=0`; keine automatische Heilung einer langen Lücke.
Passiver Readerstart nun 15 s nach den übrigen Starts; vor echten Proben bleibt
Fusion unbereit. Nur Startstaffelung, keine Messzeit-/Grenzverschiebung. Spätere
Verbraucherbeobachtung: frische aufgezeichnete Radprobe vorhanden, während Gate
189,800 ms alte Probe auswertete. Passive HWT-Quellen erhalten aktuelle DDS-Proben
und im Gate eine eigene serielle Callbackgruppe/zweiten Thread; gewöhnliche
Gate-/Not-Aus-/Befehlscallbacks bleiben seriell. Aktiver Basistreiber und aktiver
Gate-Quellenpfad unverändert und separat regressiert.

**Zeitmessung, Millisekunden (Median / p95 / p99 / Maximum):**

| Größe | Allein, 1.200 Paare | Letzter Vollstack, 4.284 Paare |
|---|---:|---:|
| Paar | 13,361 / 15,172 / 16,143 / 18,277 | 18,488 / 37,703 / 52,857 / 87,120 |
| Motorzeitversatz | 6,646 / 7,510 / 8,028 / 9,113 | 9,151 / 18,769 / 25,753 / 43,865 |
| USB/Alias vor Zugriff, je Motor | 0,719 / 1,463 / 1,858 / 4,276 | 1,093 / 4,133 / 10,838 / 33,057 |
| USB/Alias nach Zugriff, je Motor | 0,737 / 1,166 / 1,420 / 3,209 | 1,129 / 4,519 / 10,273 / 45,216 |
| Modbus, je Motor | 4,820 / 5,371 / 5,743 / 9,018 | 6,103 / 13,849 / 20,972 / 36,871 |
| Antwortprüfung, je Motor | 0,019 / 0,034 / 0,046 / 0,365 | 0,035 / 0,047 / 0,203 / 12,365 |
| Pollstartabstand | Standalone-Steuerintervall 50 ms, kein ROS-Publikationsbeleg | 50,000 / 57,173 / 72,622 / 132,552 |
| Publikationsalter ab echtem Paarmittelpunkt | Standalone publiziert nicht | 12,501 / 28,419 / 38,209 / 61,293 |

Je-Motor-Verteilungen haben n=2.400 bzw. 8.568. Null Paarüberschreitungen >120 ms
in beiden Reihen; im letzten Reader null Mittelpunktlücken oder beobachtete
Publikationsalter >180 ms. Keine kausale Last-/Kabelbehauptung aus diesen Maxima.
Voroptimierung ebenfalls 1.200 Alleinpaare: Median 14,020 / p95 16,027 / p99
17,868 / max 21,798 ms. Kein kontrollierter alleiniger Ursachenbeweis.
Zwei erhaltene ältere Vollstackreihen: 12.003 bzw. 3.360 Paare, ebenfalls keine
120-ms-Überschreitung; ihre Gateverriegelungen sind keine Reader-Paarfehler.

**Regression/Build:** acht Projektpakete isoliert, zwei betroffene Pakete nach
Gatekorrektur erneut gebaut; Quelle/Install bytegleich, kein Hauptinstallwechsel.
1.340 abschließende pytest-Tests bestanden, einschließlich aktivem Basistreiber,
passivem Kontinuitäts-/Recoveryvertrag, Not-Aus/Bewegungs-/HOLD-Gegenfällen und
Launch-Besitzprüfung einschließlich verzögertem Reader. Neue echte DDS-Regression
blockiert normalen Callback 350 ms: frische Quellen laufen weiter; tatsächlich
fehlende Radquelle >180 ms bleibt terminal. Ohne eigene Quellengruppe scheitert
die positive Gegenkontrolle erwartungsgemäß an unverändertem Radstempel.
Versetzter LiDAR/Mast, zulässiger Start und Nachbarhindernis/unbekannter
Schwenkraum/falscher TF/ungültige Pose getrennt regressiert. Verbundener
`mast_start`: drei synthetische Aufgaben erreicht, viertes Kind terminal
gecancelt, maximal ein Kind. Das ersetzt keinen realen Bewegungsbeleg.

**Gemeinsames reales Ergebnis:** erster korrigierter Quellenvorlauf 20 s gesund,
später Gate terminal an Radquellenalter; nächste Messung ohne Rendering ebenfalls
nicht durchgängig gesund. Nach gezielter passiver Callbackkorrektur im letzten
Vorlauf reale HWT-Kurzstörung → HOLD → Validierung → HEALTHY, danach weiterhin
terminal `wheel_missing_stale_or_invalid`. Reader selbst bis Ende ready,
4.284 vollständige Paare, keine FC03-Fehler/Reconnects/Recoveryausreißer/Rebases.
Der erste Fehler-Snapshot bleibt die frühere HWT-Störung; er ist kein numerischer
Snapshot der späteren terminalen Radentscheidung. Deren exaktes Verbraucher-
alter/Ursache wird nicht aus dem Bag oder späteren guten Paaren erfunden.
Die Callbackkorrektur behebt den gezielt regressierten seriellen Stau, beweist
aber **keine vollständige Beseitigung realer Verbraucherfrischefehler**.
Geometrie unabhängig davon weiterhin unzulässig. Deshalb kein aktiver Wechsel,
0 Missionen/0 Nav2-Kinder; A/B/C unverändert offen. Budgets 900/150 s, 6/3 live
belegt, nicht als ausgeführte Missionsabnahme gewertet. Alle vier Befehlsströme
null; Encoderpositionen/RPM unverändert null, Odom-v null. Alle manifestierten
Prozesse und Gerätebesitzer beendet; anschließend 12 frische Paare beider Motoren
mit 0 rpm/Position 0. Bootstrap-Scope-Exit getrennt, keine Shutdownfehler.

**Historische Voraussetzung bis cf55cea; durch den folgenden Abschluss konkretisiert:** ein
**gleichzeitig gültiger gemeinsamer Startnachweis**: vollständige gepaddete
Start-/Schwenkgeometrie samt zulässigem Rasterweg sensorisch belegt und tatsächliche
Quellen bis zum Verbraucher innerhalb ihrer unveränderten Frischegrenzen, ohne
terminale Verriegelung. Dieser eine Startvertrag ist aktuell an beiden getrennt
benannten Prädikaten ungültig; die Befunde dürfen nicht zu einem einzigen
angeblich behobenen Fehler zusammengezogen werden. Keine identische Wiederholung
oder erzwungene Bewegung ohne neue Geometrie-/Zeitbezugsevidenz.

Private Messungen/Scans/Karten/Bags/Manifeste ausschließlich unter
`~/.local/share/amadeus/tests/metric-start-encoder-20260930/`, Abschluss in
`common-gatefix/`. Keine Raumdaten oder private Berichts-Vorfahren veröffentlicht.
Rückfall: ohne Mission geordnet beenden, temporäres letztes Overlay weglassen;
Eigenkörperoption abwählen. Bei Kontinuitätsverlust neue belegte stationäre
Initialisierung mit neuem Karten-/Odometriebezug, kein Latch-Reset. Kein Merge,
kein permanenter Installwechsel und kein Stufe-3-Gesamtgrün.

### 01.10.2026 – Entscheider und reale Anfangsgeometrie, begrenztes Paket beendet

**Radpfad:** Eigener atomarer Snapshot je STARTUP-/HOLD-/Terminalübergang mit
Ereigniskennung, Zustand vorher/nachher, Originalnachricht (Header sec/ns,
Frames, Pose/Quaternion, Twist und beide Kovarianzen), tatsächlichem
Consumer-/Callbackeintritt, ROS-/Monotonic-Bracket, Mess-/Empfangsalter,
Grenze, erstem Prädikat und vorheriger erfolgreicher Recovery. Historisches
`first_fault` bleibt erhalten. Fehlend, ungültig und stale getrennt;
ältere Callbackübernahme ersetzt keine neuere Probe. Gate entscheidet einmal
unter dem bestehenden Quellenlock; bounded/latest Diagnose-JSON und DDS-Ausgabe
laufen separat, Stopptimer weiterhin 20 Hz. Ein vor der ROS-Uhrabfrage
präemptierter Callback wird nicht zusätzlich als Messalter gezählt;
Integer-ns-Differenz und konservativer gepaarter Monotonic-Bezug statt alter
Eintrittszeit. Dieser kontrollierte Uhrtest ist kein rückwirkender Beweis
für sämtliche historischen Radfehler.

Zweiter aktueller Realvorlauf: gültige Probe, 215,948 ms Messalter >180 ms,
162,131 ms seit Callback, drei neuere Originalmessungen vor Entscheidung im
Recorder. Reader fehlerfrei, Paarmaximum 93,291 ms. Recorderempfang ist kein
Gatecallback. Separate passive Radgruppe/dritter Thread allein reicht real
nicht: dritter Vorlauf 186,344 ms, neuere Probe mit 69,822 ms Messalter bereits
21,973 ms vorher im Recorder. Danach zusätzlich echte 170,104-ms-Paarverletzung.
Die nachgewiesene Empfangs-/Schedulinglücke wird am vorhandenen Gate geschlossen:
vor passiver Entscheidung nichtblockierender Take aus derselben zuverlässigen
Depth-1-DDS-Subscription unter ihrem Callbackgruppenschutz. Kein zweiter
Subscriber, Quellenpublisher oder Busbesitzer; Originalstempel unverändert.
Eine bereits laufende Subscription wird nicht verdrängt. Receive-Exception
macht die alte Probe ungültig, statt sie gesund weiterzuverwenden. Normaler
Befehl/Not-Aus bleibt seriell; aktive Quellen weiterhin bestehender serieller
Executor/QoS und separat regressiert.

**Reader:** Im ersten aktuellen Start war eine reale 129,184-ms-Paarverletzung
überwiegend in Alias-/USB-Prüfung gemessen (106,350 ms). Voller `/dev`-Pfadwalk
nun nur zur Bindung; beide Aliaslinks, tatsächliche Gerätegenerationen und
alle USB-Identitätswerte weiter vor/nach jeder FC03-Probe prüfen. Weder
120-ms-Paargrenze noch 180-ms-Kontinuität oder Recoverybedingungen gelockert.
1.200 korrigierte Alleinpaare: Median 13,895 / p95 16,593 / p99 19,135 /
Maximum 23,420 ms. Unterschiedliche Lastbedingungen sind kein alleiniger
Kausalvergleich. Die Optimierung garantiert keine reale Echtzeitdeadline.

**Geometrie:** Zellprojektion auf den tatsächlichen Körper durch
res/2·(|cos Δyaw|+|sin Δyaw|) statt immer res/√2. Bei einem erhaltenen aktuellen
Start 78→92 ganze Körperzellen; alle vier Ecken der 14 zusätzlich zugelassenen
Zellen wirklich innerhalb des unveränderten ungepaddeten Körpers. Erste
Anfangsablehnung 50→36 und volle Rundblickablehnung 231→217; körperfremder
Flächenanteil unverändert. Vorheriger C3-Start 78→78, keine rückwirkende Heilung.
Kein Rohkartenwechsel, keine partielle Zellenfreigabe, kein mitbewegter Beleg.
Frischer Scan, der während Kartenarbeit ankommt, wird gegen danach erfasste
Zeit geprüft; echtes Stale/Future/fehlender Scan weiter abgewiesen.

Finale Karte/Pose im selben letzten Vollstack gebunden: 92 unbekannte ganze
Körperzellen privat korrekt behandelt. Anfangskontur weiterhin 36 unbekannte
Zellen: 18 teilweise Körperrand, 1 Padding, 17 Reserve; Außenanteil
0,030920 m². Voller 360°-Sweep: 211 abgewiesene Zellen (18 Rand, 1 Padding,
192 Reserve/zusätzlicher Schwenkraum), Außenanteil **0,188420 m²**.
Dies ist die konservativ benötigte Rasterbeobachtung abzüglich exakter
Körperüberlappung, nicht eine vermeintlich exakte feste Fahrzeug-Sweepfläche.
Costmap: Anfang 2 unbekannte Zellen; volle Drehung 139 unbekannte Zellen /
0,125100 m², vollständig in obiger Rohkartenzellmenge. Flächen nicht addieren.
Keine Rohhindernisse oder Inflationskosten in diesem Beleg. Zentrum nach
Clearance 0,120 m < erforderlichen 0,295 m unzulässig, 0 sichere Kandidaten;
erstes Produktprädikat `initial_scan_footprint_invalid`. Ganze 360°-Kontur,
Vorausrichtungs-/Routenwahl und Costmap werden nicht durch eine freigegebene
Mittelpunktzelle ersetzt. Volle reale Kontur/Padding/Reserve unverändert.

**Regressionen und Grenzen:** Isolierter ursprünglicher Vierpaketbuild plus
abschließendes Zweipaketoverlay bestanden und Quelldateien bytegleich geprüft.
1.469 pytest inklusive A–D, aktiv/passiv, Reihenfolge, wartende echte DDS-Probe,
Receive-Exception, Not-Aus/HOLD/Stillstand/Einzelkind. Gerätefreier verbundener
`mast_start_scan` besteht: versetzter LiDAR/Mast-NaN, volle 360°-Konturzulassung,
bestehender 0,3-rad-Testscan, Vorausrichtung, drei autonome Beobachtungen,
viertes Kind gecancelt, maximal ein Kind. Kein voller physischer Rundblick
behauptet. Zusätzliche vollständige 2π-Dauerprobe nicht bestanden:
`initial_scan_no_progress`, gemessene synthetische Quellengaps bis 460,796 ms.
Diese erhaltene negative Probe wird nicht in die positiven Softwarebelege
umbenannt. Keine entsprechende reale Bewegungsprobe ausgeführt.

**Gemeinsamer Realvorlauf:** Vier klar begrenzte, jeweils nach neuer Evidenz
korrigierte Fenster, jeweils 720 s ab Launchwurzel, kein Gate-/Reader-Neustart
oder Latch-Reset innerhalb eines Fensters. Letzter Kandidat `8f5eeb4`, Sources
zuerst nach 33,328 s bereit; zwei reale HWT-HOLDs mit erfolgreicher Validierung.
Danach etwa 197,9 s: Wheelmessalter 212,127 ms, tatsächlicher Consumerabstand
165,445 ms, gültiger Inhalt, `measurement_age_out_of_bounds`. Historische erste
HWT-Störung und letzte Wheelentscheidung haben eigene Originalsnapshots;
vorherige erfolgreiche Recovery steht im Wheelereignis. Beim Reader:
3.552 akzeptierte Paare (Maximum 99,431 ms); letztes 64,649 ms,
folgendes verworfenes Paar **120,874 ms**,
kein Rebase/Reconnect, keine aktuelle zulässige Ersatzprobe. Geschlossener Bag:
keine neuere Radnachricht um den Entscheid; erster verriegelter Readerstatus
bereits 7,975 ms vor dessen gepaartem ROS-Zeitbezug im Recorder. Das ist ein neuer
echter Transport-/Deadlinegegenfall; keine alte Probe frisch bewerten.
Der spätere Status `ready=false` bleibt erhalten. Gesamtes Fenster negativ,
geometrisch zugleich unzulässig. Kein aktiver Buswechsel, 0 Missionen,
0 Nav2-Kinder; 900/150 s und 6/3 live geladen, keine Budgets gestartet/reset.

**Damals konkreter Restumfang (durch den folgenden Auftrag präzisiert):** Der aktuelle FC03-Pfad muss unter echter Vollstacklast
wieder zulässige Paare innerhalb 120 ms und lückenlos innerhalb 180 ms liefern.
Im letzten Paar sind 71,797 ms Alias/USB-Nachprüfung und 46,840 ms Modbus
beobachtet; aus diesen wall-clock-Phasen allein keine Kabel-/Encoder-/Kernel-
Ursache erfinden. Weitergehende Transport-/Runtime-Latenzabsicherung ist ein
separat zu begrenzender Umsetzungsschritt; dieses Paket startet keine weitere
Reparatur-/Vorlaufserie. Geometrisch genau eine notwendige äußere Handlung:
die private Liste der 211 Außen-/Schwenkzellen mit dem vorhandenen LiDAR von
einer separat hergestellten stationären Beobachtungsposition aufnehmen und
Karte/Pose neu gültig zuordnen. Dafür nötiges manuelles Umsetzen bei deaktivierten
Antrieben durch die anwesende Person liegt außerhalb dieses Softwarepakets.
Stationärer Mast-NaN-Blick und vorhandene OAK/VL53-Vorwärtssicht belegen diesen
gesamten rückwärtigen Bereich nicht. Keine allgemeine Platzfrage, Karten-
freigabe oder autonome Bewegung zur Umgehung.

Alle zugehörigen Wurzeln geordnet einzeln per SIGINT beendet, Gerätehandles frei,
abschließend 12 frische FC03-Paare beider Motoren: Position/RPM null. Elektrische
Motorstromfreiheit wurde daraus nicht behauptet. Befehlsströme und Shutdown-
Details im geschlossenen lokalen Bericht. Ungebundener Bootstrap-Explorer
beendet sich erwartungsgemäß mit Scope-/Sitzungsfehler (Exit 1); anschließend
gebundener Explorer regulär, kein Fehler beim geordneten Shutdown.
Private Messdaten, Zellkoordinaten,
Karten, Bags und Manifeste unter `~/.local/share/amadeus/tests/metric-gate-start-20261001/`,
finaler Lauf `decision-take-common/`, Runtime `final-runtime-env.sh`,
`final-build-identity.json` und `end-state-proof.json`. Keine privaten
Berichts-Vorfahren, Merge, Force-Push oder permanenter Installwechsel.
Rückfall: ohne Mission geordnet stoppen, beide temporären Overlays weglassen,
`active_drive=false`, `enable_auto_explore=false`. **Stufe 3 bleibt offen.**

### Historischer Abschluss: adaptiver Start und begrenzte Encoder-Recovery (01.10.2026)

Ausgang `d9894d268262f7f8e965f2f92aef72021df3245e`, Funktionskandidat
`fd883fdf35e004dff6b209fffff9118c71161cd3`, derselbe Branch/PR #105.
Getrennte Funktionscommits: `a8aa3f3` Encoder/aktive Basis/Fusion/Gate,
`b36d412` adaptiver Start/Controllergeometrie, `fd883fd` typgerechte
Controllerklassen in der Graphfixture. Keine privaten Berichts-Vorfahren.

**Wirksamer Produktvertrag:** `exploration_strategy` bleibt standardmäßig
`existing`; metrisches Profil explizit `metric_frontier`, dessen unveränderlicher
Startparameter `metric_start_strategy=adaptive`. `initial_scan_enabled=true`
bleibt geladen. Ein zulässiger nützlicher Vollrundblick bleibt verfügbar; fehlt
seine Fläche, wird ein echtes Frontier-/Annäherungsziel gesucht. Fehlt schon
die sichere Anfangskontur oder jedes Ziel, folgt ein begründeter Teilstand.
Kein Pflichtscan für eine andere Bewegung, kein festes Fahrziel, kein neuer
Goal-Sender oder Supervisor. Bootstrap/HOLD zählen in 900/150 s und 6/3 hinein.

Vor vorhandener Nav2-Ausführung tatsächlichen `ComputePathToPose`-Plan und
13 Liveparameter von RPP/Goalchecker prüfen: genau `FollowPath`/RPP und
`general_goal_checker`/SimpleGoalChecker; Rotation true, Winkel 0,35 rad,
Lookahead 0,40 m, Geschwindigkeitsskalierung/Rückwärtsfahrt false,
Kollisionsprüfung/Interpolation true, XY-Toleranz 0,15 m/Yaw 0,40 rad.
Vorausrichtung, Controllerkorrektur, interpolierter Carrot/Kurvenraum, gesamte
Route und Zielrotation einschließlich XY-Toleranzdisk reservieren. Ungedeckter
weiter Carrot aus zu dünnem Plan wird verworfen; vorhandene Reserven bleiben.
Die zusätzliche Kurvenreserve ist abgeleitet, kein verkleinerter Footprint.
Startkörperbeleg bleibt im ursprünglichen Raum; harmlose Rasterupdates können
ihn nur verkleinern. Änderungen von Kontext/Raster/Karten-Odometriebezug lassen
ihn verfallen. Keine mitfahrende Freiraumblase, kein Überschreiben von Hindernissen.
Mastmaske, NaN-Semantik und Montage-TF erhalten.

**Encodervertrag:** gemeinsamer Core für passiven Reader und aktive HWT-Basis;
120 ms Paarvalidität und 180 ms Bewegungsfrische/Kontinuität unverändert.
Nach gesundem Vorlauf darf bei intakter Identität begrenzt diagnostisch weiter-
gelesen werden: maximal 2 s / zwei Versuche je Readerlebensdauer. Verworfenes
Paar bleibt unveröffentlicht, Stillstand/HOLD sofort. Neue gültige Paare können
nur bei belegter Kontinuität alle Zählerdifferenzen erhalten; keine Rebase,
Pose-Nullung oder Reconnect-Reparatur. Echte >180-ms-Lücke bleibt unbewiesen,
auch bei späteren 0 RPM/zwei guten Paaren. Verbraucher zusätzlich höchstens
5 s / zwei Wiederherstellungen je Quellenklasse HWT bzw. Rad, ohne Reset durch
Kindwechsel. Gültige Originalstempel, Stillstand, Fusion/Karte/Route, terminales
altes Kind und Gate-ACK vor Resume. Port/Identität/Zähler/Zeit/ESTOP/Cancel
und Aktuatorfehler bleiben hart. Details: [Encodervertrag](../ENCODER_ODOMETRIE_FIX.md)
und [Explore-README](../../src/explore/README.md).

**Alter echter Fehler exakt reproduziert:** native Paardauer 120,874265 ms,
letzte zulässige Radprobe am Gate 212,127149 ms. Erstgrund im ursprünglichen
Reader `encoderpaar_zeitfenster_ueberschritten`; keine wartende zulässige Probe.
Neuer Reader verwirft das Paar; danach >180 ms macht Kontinuität unbewiesen,
2-s-Endgrund `encoder_timing_continuity_unproven`. Historisch nicht aufgezeichnete
verworfene Zähler wurden im Replay mit null gegengetestet: sogar das heilt die
Zeitlücke nicht, beweist aber keinen historischen Stillstand. Kein rückwirkendes
Umdeuten der damaligen Sperre.

**Software und verbundene Nachweise:** 1.493 Regressionen bestanden, isolierter
Fünfpaketbuild erfolgreich. Zehn geänderte Laufzeitartefakte bytegleich mit dem
tatsächlich aufgelösten Install. MM, BT, Explorer, Kartenmanager, HWT-Shadow und
Gate tatsächlich ausgeführt; synthetisch sind Sensor-/Rastereingänge und
Nav2-Gegenstelle. Keine erfundenen Ziele/Gesundheitsadapter. Reale Zeitlücken
bleiben Zeitlücken, kein Fresh-Restamping. Unterschiedliche Graphfälle nicht
zu einer bestandenen durchgehenden Vollrundblickfahrt zusammensetzen.

| Pflichtfall | Ergebnis und Grenze |
|---|---|
| A adaptive Beobachtungsschleife | `adaptive_loop`: drei selbst berechnete Ziele, neue Rasterevidenz, offene Verbindung/weitere Ziele, 60,38 s im selben Elternauftrag, maximal ein Kind. Scanverfügbarkeit in diesem Loop-Test explizit false. Separater Fall unten prüft den tatsächlich eingeschalteten Scan. |
| A/B Scan optional, später zulässig | `adaptive_admission` mit `initial_scan_enabled=true` und voller 2π-Anforderung: rückwärtiger Schatten sperrt Scan; anderes berechnetes Ziel wird ausgeführt; erst neue Karte erlaubt Scan. Danach bewusster Testabbruch, **kein bestandener Vollscan**. Nach letzter Parametertypkorrektur erneut bestanden. |
| C keine sichere Erstbewegung | `adaptive_wait`: null Kinder und ausschließlich Nullbefehle bei unbekannter Startreserve; Vorausrichtung/seitliches Hindernis/Controller-/Zieltoleranz zusätzlich regressiert. |
| D/F Timing-HOLD und HWT davor | `encoder_hold`: tatsächlicher Core verwirft 120,874-ms-Paar bei noch belegter kurzer Kontinuität; HWT-Recovery zuvor separat; neuer gültiger Stillstand/Fusion/ACK, höchstens ein Kind; getrennte Originalereignisse am Explorer und Gate. |
| E echte Lücke | `encoder_gap` und Readerregression: >180 ms, spätere gute Paare/0 RPM ohne Rebase oder Weiterfahrt; begrenzte Diagnose endet gesperrt. |
| G harte Gegenfälle/Budget | `encoder_persistent`, `encoder_no_stop`, `encoder_estop`, `encoder_cancel`, `encoder_budget`, `cancel_failed`, `estop`: keine unerlaubte Fortsetzung; dritter Radfehler nach zwei Recoveries terminal. Aktiver Basisadapter/Identität/Uhrrücklauf/Zähler separat regressiert. |
| H Karten-/Körperbeleg | `route`, `mast_start`, `chain` sowie Körper-/Kontextregression: gültige Updates erhalten Aufgaben; neues Hindernis stoppt; alter Körperbeleg kann weder wandern noch neue Sperren freigeben. |

Sechs geometrie-/Controllerbetroffene Graphfälle nach finaler Kurven- und
Zielreserve erneut bestanden, zusätzlich typgerechte 13-Parameterprüfung und
Budgetfall. Lokales Nachweisregister `metric-adaptive-start-20261001/` mit
`regressions-publish-final.log`, `graph-controller-final-summary.json`,
`graph-suite-summary.json` und einzelnen `result.json`/Prozesslogs.

Nach Veröffentlichung erkannte Offline-CI einen ROS-Import im neuen aktiven
Adaptertest. Nur dessen Sammlung und die ROS-Uhrprüfung bei fehlendem `rclpy`
ausnehmen; vollständige Coretests bleiben offline aktiv. Nachweis in isolierter
Umgebung ohne ROS: 118 bestanden, zwei ROS-Abhängigkeitsskips, 63 Subtests;
zwölf Inbetriebnahmewerkzeugtests bestanden. Dieselben drei ROS-abhängigen
Adapter-/Uhrfälle mit echter ROS-Installation erneut bestanden. Produktbytes
des real geprüften Kandidaten bleiben unverändert, kein neuer Realstart.

**Volle Dauerprobe bleibt negativ:** historische 2π-Probe erhalten. Auch neuer
`graph-adaptive_start-final` nach 259,27 s negativ: Vollscan erst nach tatsächlich
erledigter erster Beobachtung zugelassen, dann Quellenpausen (größte rohe
Publikationslücke 515,70 ms), zwei HWT-Recoveries, absolute 150-s-Scanfrist
erschöpft; anschließend `post_child_state_or_standstill_unconfirmed` mit
`hwt_recovery_attempt_limit`. Gemessene synthetische Gesamt-Yaw 11,825 rad über
Unterbrechungen ist kein belegter abgeschlossener 2π-Scan. Diese Probe entstand
vor der zusätzlichen Kurven-/Zielreserve; die späteren positiven Kurzfälle
ersetzen ihre Laufzeit-/Quellengrenze nicht. Frühere negative Fixture-/Last-/
Geometrieversuche ebenfalls erhalten. Kein Vollrundblick-/Robustheitsgrün.

**Ein gemeinsamer realer Vorlauf:** derselbe isoliert kopiert gebaute Kandidat,
reale Domain 42, `active_drive=false`, passiver FC03-Reader als einziger
Basisbusbesitzer. Vorab FC03-Nullposition/-RPM und freie Handles geprüft.
Ungebundener Bootstrap endet erwartungsgemäß am Scope; im selben Stackfenster
Session/LAB-1-Scope an tatsächliche Karte/Pose gebunden und einziger gebundener
Explorer idle. Laufzeitpräfixe, Prozessbaum, geladene Parameterdateien, Modul-
und native RPP-Bibliothekshashes sowie alle 13 Controllerparameter manifestiert.
Tatsächliches metrisches/adaptives Profil, Scan weiterhin true, 900/150 s und
6/3 live; SLAM `check_min_dist_and_heading_precisely=true`.

Vorab festgelegtes Messfenster **720 s ab Launchwurzel**, gemessen 720,016 s.
Erstmals alle Vorlaufbedingungen außer Bewegungsgeometrie nach 35,858 s.
Am tatsächlichen Gate: HWT-HOLD nach 162,718 s → HEALTHY nach 164,263 s;
zweiter HOLD 401,729 s → HEALTHY 403,212 s. Dritte HWT-Störung nach 583,261 s
terminal `hwt_recovery_attempt_limit`. Eigener Originalzustand: Rawdriver
`ready=false`, `raw_data_ready=false`, `consecutive_errors=1`,
`Zeitueberschreitung nach 0/14 Bytes`; Rawalter dabei erst 37,327 ms.
Also echter Readiness-/Budgetgegenfall, keine erfundene stale-Wheelursache.
First-Fault und zweite erfolgreiche Recovery im späteren Fehler erhalten.
Keine bewiesene Hardware-/Kabel-/Kernelursache daraus ableiten.

Encoder am 720-s-Ende: **13.921 vollständige Paare**, null Timing-Recovery/
Rejects/Rebases/Reconnects, ursprünglicher Baselinezähler eins, Kontinuität
gültig. Größte diagnostizierte Paardauer 108,118 ms, unter 120 ms. Der aktuelle
Realfall ist **kein realer Encoder-Recovery-Nachweis**; dieser ist softwareseitig
verbunden geprüft. Gesundes Rad heilt keine terminale HWT-/Fusionquelle.

Aktuelle frühe und späte Geometrie unabhängig von Quellen negativ:
**33 unbekannte Startkonturzellen**, davon 16 teilweise Körperzellen und
17 Paddingzellen. Ganze Körperzellen privat 79; Außenanteil spät **0,021089 m²**
(früh 0,021069 m²). Eine unbekannte Costmap-Paddingzelle vollständig in dieser
Rohmenge; Flächen nicht addieren. Erster Produktgrund
`initial_contour_unknown_or_occupied`, **null adaptive Kandidaten**. Kein
unbenutzter Vollsweep als Gate: dennoch bleibt die beanspruchte Anfangskontur
unbelegt. Vollsweep nur Diagnose: 220 unbekannte Zellen / 0,189389 m²,
134 Costmap-Zellen vollständig darin. Letzter historischer Referenzfall bleibt
separat 36 Start-/211 Sweepzellen; weder manuelles Umsetzen noch Vorkartieren
wurde als positiver Bootstrap verwendet. Spätaufnahme nutzt aktuelle Daten
im selben laufenden Sensorstack, keine neue Karten-/Quellenfreigabe.

**Reale Mission nicht ausgeführt:** kein aktiver Buswechsel, kein MM-Auftrag,
kein Nav2-Kind. Quellenbudget UND Anfangskontur blockieren technisch; keine
fehlende allgemeine Nutzerfreigabe. Kein weiterer Vorlauf oder Fahrversuch.
Der 720-s-Probe endete automatisch; für abschließenden Snapshot und geordneten
Stopp liefen die rein lesenden Sensorprozesse anschließend noch **185,994 s**.
Dies ist Abschlussnachlauf außerhalb des Messfensters, kein zweites Fenster
und keine 900-s-Mission; eine exakte 720-s-Prozesslaufzeit wird nicht behauptet.
Geschlossene Bag erst nach Recorderende: 0 running-Missionen, 0 Navigate-
Statuseinträge, sämtliche vier aufgezeichneten Befehlsströme null. Radpositionen
durchgehend null; kleine gefilterte IMU-Winkelgeschwindigkeit ist kein Fahrbeleg.
Geschlossener Gesamtdatensatz einschließlich Nachlauf: 17.559 Readerpaare,
keine 120-ms-Verletzung, maximaler Messabstand 124,198 ms. Diese Statistik
nicht mit einem durchgehend gesunden Verbraucherzustand gleichsetzen.
Mast-NaN im robusten Sektorinneren 57–123° vollständig erhalten; Montage-TF
unverändert. Einzelne Raster-/Pose-/Zellbelege bleiben privat.

**Endzustand:** alle manifestierten Prozesse nach einzelnem SIGINT an ihren
Launchwurzeln beendet, beide Gerätealiases ohne Besitzer; anschließend zwölf
frische FC03-Paare je Position 0 / 0 RPM, keine elektrische Sperrstellung
behauptet. Hauptkopie sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`,
kein dauerhafter Install-/Autostartwechsel. System eingeschaltet, kein geplanter
Shutdown. Private Belege ausschließlich
`~/.local/share/amadeus/tests/metric-adaptive-start-20261001/`, insbesondere
`common/passive-window-final.json`, `common/closed-preflight-analysis.json`,
`common/late-geometry-report.json`, `common/fullstack-timing.json`,
`common/scan-mask-proof.json`, `end-state-proof.json` und `end-encoder.json`.

**Belegte Restgrenze:** autonome reale Erkundung erst mit gleichzeitig gültigen
Quellen am Verbraucher innerhalb des unveränderten Recoverybudgets und
sensorisch belegter Anfangskontur/einer zulässigen berechneten Erstbewegung.
Der optionale Rundblick löst weder drei HWT-Störungen noch die 33 Startzellen.
Kein manueller Bootstrap als Ersatz. Weitere gezielte Quellen-/Beobachtungs-
arbeit braucht einen neuen begrenzten Auftrag, keine automatische Neustartserie.
Rückfall: ohne Mission geordnet stoppen und dieses temporäre Fünfpaketoverlay
weglassen; sichere Betriebsparameter `active_drive=false`,
`enable_auto_explore=false`. **Stufe 3 offen.**

### Aktueller Abschluss: HWT-Entwicklungsvertrag und Start-Egress (01.10.2026)

Ausgang `2a0e19d`, bestehender Branch/PR #105. Getrennte Funktionscommits:
`689cba3` (HWT-Vertrag), `acdfbeb` (gebundene Portgeneration), `577013d`
(weiter frisches korrigiertes Original nach verworfener Grenzmessung),
`a6f31bf` (bewegungsgerichteter Egress). Explizites Entwicklungsopt-in:
Antwortfrist 50 ms, Rohoriginalfrische 300 ms, maximal zwei echte HWT-HOLDs
im rollenden 60-s-Fenster. Einzel-Recovery weiterhin absolut 5 s; keine
Rücksetzung durch Aufgaben-/Kind-IDs. Legacy 30/200 ms und Encoder 120/180 ms
erhalten. Kein Restempeln, keine verspätete Antwort nachträglich nutzbar.

**Software:** 1.462 Pflichtregressionen in sieben betroffenen Paketen bestanden
(28,97 s), zusätzlich 102 unveränderte Mission-/BT-/Kartenprüfungen (5,00 s):
zusammen 1.564 Tests in getrennten, nicht überlappenden Testsammlungen.
Pflichtfälle A–F: Polltimeout ohne Budgetverbrauch, wirkliche Rohdatenlücke,
begrenztes Heilen/ACK/Resume, drittes HOLD innerhalb 60 s, drei zeitlich
verteilte Recoveries und harte Port-/Protokoll-/Zeitfehler. G–J: autonome
Vorwärtsausfahrt aus unbekanntem Startbestand, unzulässige Drehung, neues
Hindernis und spätere normale Entscheidung nach echter Beobachtung.
Zusätzlich Wiederbetreten/Annäherung, Kontextentzug und verbleibende
Drehkopplung nach nominalem Verlassen, sowie Not-Aus/Cancel/Einzelkind/
Encoder/Kartenprovenienz regressiert. Verbundener gerätefreier Produktgraph:
drei autonome erreichte Ziele mit neuen Kartenbeobachtungen und Weiterarbeit
über die synthetische Verbindung; maximal ein Nav2-Kind. Separater HOLD-Graph:
150-ms-Lücke ohne HOLD, echte >300-ms-Lücke, Stop/Validierung/ACK innerhalb
5 s und Wiederaufnahme desselben Ziels. Keine reale Recovery daraus ableiten.
Historische negative vollständige 2π-Dauerprobe bleibt unverändert negativ.

**Runtime:** Sechspaket-Copybuild außerhalb Git erfolgreich, letzter Build
von state/explore 8,58 s. 100 Quell-/Install-Dateien bytegleich. Tatsächliche
Prozessargumente, Parameterdateien, Präfixe und Modulhashes privat gesichert;
live Rawreader 50/300 ms, Encoder 120/180 ms und 13 native Controller-/
Goalcheckerparameter gelesen. Die einzelne Live-Explorer-Parameterabfrage
war während dessen verzögerter Initialisierung nicht verfügbar; gebundenes
Launchprofil und vier spätere `metric_frontier`-Statusmeldungen sind erhalten.
Keine vollständige Live-Parameterantwort dieses Nodes behaupten.

**A. Start-Egress:** Fester Ausgangsbestand in beiden Rastern, nur monoton
wegführender voller reservierter RPP-Sweep; Suchmaske ist keine Freigabe.
Aktueller Real-Snapshot: 42 unbekannte Roh-Startkonturzellen (16 teilweise
Körperrand-, 17 Padding-, 9 Reservezellen), 79 ganze Körperzellen privat;
Außenanteil 0,026895 m². Costmap zwei unbekannte Konturzellen. Das ist ein
neuer Snapshot, kein Ersatz des historischen 33-Zellen-Befunds. 22 autonome
Kandidaten, keiner zulässig: zehn nötige Anfangsdrehungen, sieben fehlende
freie Routen, eine ungültige Zielorientierung, vier ungültige Footprint-
Sweeps. Produktgrund `start_egress_no_admissible_motion`; optionaler Vollscan
ebenfalls unzulässig. Alle Zell-/Pose-/Kartenbelege und gerenderte Grafik
privat. Frühere virtuelle Hindernisdiagnose nicht als aktuelle Fahrt ausgeben.

**B. Reale autonome Ziele:** Null; kein aktiver Buswechsel, keine MM-Mission,
kein Nav2-Kind. Keine fehlende allgemeine Nutzerfreigabe: der harte Zeitfehler
und der fehlende zulässige Startkandidat verhindern den konditionierten Start.

**C. Karte:** Aktuelle reale Karte/Pose/Scope gebunden und unverändert
ausgewertet. Kein durch Fahrt erzielter Kartierungsfortschritt und kein
Abdeckungs-/Wohnungsabschluss. Drei neue Beobachtungen nur im Softwaregraph.

**D. HWT:** Erster kurzer Start vor der gemessenen Portprüfung-Optimierung
verbleibt STARTUP: wiederholte >100-ms-Lücken unterbrechen die unveränderte
800-Sample-Kalibrierung. Optimierung gemessen: voller USB-Abgleich im Mittel
1,065 ms, gebundene Geräteprüfung 0,031 ms; voller Ausschluss vor exklusivem
Öffnen, danach Gerätegeneration vor und nach Antwort. Finaler kurzer Start:
60,008-s-Messfenster, HEALTHY bei 36,379 s, terminal bei 54,880 s wegen
`HWT-Messzeit nicht monoton`. Dies betrifft die hostseitige Zuordnung des
Empfangs zu ROS-Zeit; keine bewiesene Sensor-/USB-/Kernelursache. Davor
zwei tatsächliche verworfene Transaktionen: Header 3 Bytes erst nach Frist,
Payload 0; anschließend Header 3/Payload 14 rechtzeitig empfangen, Verarbeitung
nach Frist. Rawdriver meldet dabei `transport_degraded`, letzte gültige
Messung 75,693 bzw. 71,024 ms alt, kein HWT-HOLD. Harte Zeitprüfung umgeht das
Recoverybudget nicht: unmittelbare Sperre, null Recoveryversuche. Keine
natürliche reale HOLD→Resume-Folge in diesem Lauf. Frozen Bias mit 800 Samples
belegt, keine Grenze dafür gelockert. Recorder 3.280 Rohframes gegenüber
Driverzähler 3.287; nicht als verlustfreie Aufzeichnung darstellen.

Encoder am Messfensterende 824 Paare, im geschlossenen Gesamtdatensatz 1.133;
maximal 114,879 ms, null Reject/Timing-Recovery/Rebase/Reconnect, Baseline eins.
Er ist auch hier kein nachgewiesener Blocker. Messfenster und Prozessdauer
getrennt: gesamte Orchestrierung einschließlich Bindung/Manifest/geordnetem
Stopp 83,709 s, Bag-Spanne 76,646 s. Kein 720-s-Vorlauf oder 900-s-Fahrversuch.

**E. Zielmisserfolg/Folgeaufgabe:** Kein reales Ziel gesendet, daher kein
reales Misserfolgs-/Alternativzielereignis. Bestehender Softwarevertrag bleibt
regressiert; die Drei-Ziel-Folge meldet drei `success/observed`, null Fehler.

**F. Passage/Weitererkundung:** Nur synthetisch im Produktgraph belegt;
keine reale Durchfahrt, keine Portal-ID als Voraussetzung eingeführt.

**Endzustand/Rückfall:** Geschlossene Bag mit Integritätsprüfung, null laufende
Missionen/Nav2-Statuseinträge und alle vier Befehlsströme null. Eigene
Launchwurzeln einzeln SIGINT, Recorder danach; sämtliche manifestierten
Prozesse beendet, beide Gerätealiases ohne Handles. Zwölf frische FC03-Paare
Position/RPM null; keine elektrische Motorstromstellung daraus behauptet.
Hauptkopie sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`, kein permanenter
Install-/Autostartwechsel. Rückfall: isoliertes Overlay weglassen oder beide
Opt-ins beim gestoppten Neustart deaktivieren; ohne Mission
`active_drive=false`, `enable_auto_explore=false`. Private Nachweise ausschließlich
`~/.local/share/amadeus/tests/metric-egress-hwt-20261001/`, insbesondere
`runtime-byte-manifest-release.json`, `short-final/geometry-report.json`,
`short-final/passive-window-final.json`, `short-final/timing-analysis.json`,
`short-final/closed-preflight-analysis.json`, `end-state-proof.json` und
`end-encoder.json`. Kein automatischer weiterer Start. Konkrete offene
Grenzen: monotone originale Zeitzuordnung und eine tatsächlich zulässige
autonome erste Trajektorie. **Stufe 3 offen, ROS beendet, Rechner eingeschaltet.**

## 5. Erhaltener Umfang und nächste Meilensteine

Schritt 1/2 nicht neu beginnen; betroffene Wiederverwendung gezielt regressieren. Stufe 3: Softwareabschluss des metrischen Kerns erreicht; reale autonome Beobachtungsfolge, Hindernis-/Befreiungsfälle und vollständige Passage mit Weitererkundung weiterhin offen. Normale Fahrten benötigen keine Portal-ID mehr; physische Durchfahrt und freier Fahrweg bleiben nachzuweisen.

Danach metrischer WE-M4-Rundweg, WE-M5-Persistenz/Wiederaufnahme und WE-M6-Abschluss gemäß v1.2. Semantische Portal-/Regionskriterien werden separat geführt, nicht gelöscht oder rückwirkend erfüllt. Geparkter HWT-Kindziel-Injektionstest, optionale OAK-Türerkennung und zusätzliche Architekturvergleiche sind kein aktueller Parallelauftrag.

## 6. Git, Runtime und Rückfall

Ein Integrationsverantwortlicher, bestehender Branch/PR #105. Kein automatischer Merge, kein permanenter Installwechsel. LAB-1 ohne erneute Standardfreigabeschleifen anwenden. Gerätefreier Auftrag ist keine unbegrenzte Fahrerlaubnis.

Ein lokaler nicht veröffentlichter Berichtscommit mit Raumdaten wurde im Gespräch genannt. Die ausgehende Linie basiert direkt auf dem veröffentlichten Remote-Stand; private Berichtscommits sind keine Vorfahren. Auch bei späteren Pushes Vorfahren prüfen. Lokale Arbeit sichern und getrennt halten, keinen Force-Push oder destruktiven Reset ausführen. Der Funktionscommit basiert ausschließlich auf dem veröffentlichten Remote-Stand.

Rückfall: metrisches Overlay nicht aktivieren, `exploration_strategy: existing` beim geordneten Start ohne Mission; sicherer Betriebsrückfall `enable_auto_explore:=false`, `active_drive:=false`. Kein Branch-Rollback und keine bekannten offenen Befunde ausblenden. Bei Code-Revert auch die gemeinsame Absicherung verspäteter Nav2-Annahme berücksichtigen.

## 7. Historie und Nachweisregister

[Original-STATUS bis 99d21c0](archive/20260930-v1.1/STATUS.md), [Original-Agentenauftrag](archive/20260930-v1.1/AGENTENAUFTRAG.md), [Archivzuordnung und Originalpfade](archive/20260930-v1.1/README.md). Die Dateien sind unverändert erhalten. Maßgeblich für den jetzigen Auftrag sind Abschnitte 1–6 dieser Datei und der aktuelle AGENTENAUFTRAG, nicht ältere Aufträge aus dem Archiv.
