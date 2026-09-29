# Agentenauftrag – Wohnungserkundung Amadeus

**WE-1 · Arbeitsregelstand 28.09.2026 · Repository `chris01-byte/Roboter_ws`**

Verbindlicher Einstieg ist [MASTERPLAN.md v1.1](MASTERPLAN.md) mit der
[Arbeitsregel LAB-1 v1.0](../LABORMODUS.md).
Der laufende Iststand und der nächste Auftrag stehen in [STATUS.md](STATUS.md).
Die [Gesamtstrategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) und die
[WE-Meilensteine](MEILENSTEINE.md) bleiben erhalten. Kein paralleler P1–P5-Plan.
Dieser Text ist eine Arbeitsreferenz; die ausdrücklich hinterlegte Laborfreigabe
LAB-1 gilt innerhalb des beauftragten Laborumfangs, nicht als pauschale
Freigabe neuer Bewegungen oder ungeprüfter Hardwarezustände.

## 1. Pflichtkontext vor jeder Bearbeitung

Alle geltenden [AGENTS.md](../../AGENTS.md), dann MASTERPLAN, STATUS und diesen
Auftrag lesen. Betroffene Meilensteine, [Inventar](../INVENTORY.md), einschlägige
[Projektgedächtnis-Einträge](../PROJECT_MEMORY.md) und vorhandenen Code samt Tests
gezielt hinzunehmen. Vor Gerätezugriff den tatsächlichen Stand in
[ROBOT_TRANSFER.md](../ROBOT_TRANSFER.md), bei Kartierung das
[Betriebswissen](../../tools/kartierung/README.md) prüfen.

Nicht aus historischen Hardwareübersichten, Branch-Namen oder einem PR-Text
auf aktuelle Runtime schließen. Bei Konflikten Datum, Commit, Profil und Art
des Nachweises nennen. Abgeschlossene Arbeiten nicht grundlos wieder beginnen.

## 2. Arbeitsvertrag für alle folgenden Aufträge

Ein Auftrag liefert genau ein abgegrenztes funktionales Ergebnis. Vor Änderungen
kurz benennen: Planversion, WE-Bezug, Istbasis, Ergebnis, erlaubte Dateien/
Komponenten, Nicht-Ziele, Nachweise und Rückfall. Einen Integrationsverantwortlichen
und einen aktiven Kandidaten führen; Parallelagenten nicht unkoordiniert an
Launchprofilen, Runtime oder Hardware schreiben lassen.

Bestehende Implementierungen verwenden. Keine neue Navigation, vorsorgliche
Supervisor-Neuentwicklung, neue OAK-Pipeline, Arm-, GUI- oder Komfortbaustelle.
Sicherheits- oder Akzeptanzgrenzen nicht allein für einen grünen Test ändern.
Nötige Umfangsänderungen mit konkretem Befund als ein Paket vorlegen.

Bewegung bei notwendigem Halt rechtzeitig stoppen. Auftragserhalt, begrenzte
Wiederherstellung und sichere Wiederaufnahme getrennt betrachten. Nicht jeden
Kommunikationsausreißer als permanenten Hardwaredefekt klassifizieren; aber auch
nicht ohne sichere Fortsetzbarkeit auf den Nachweis eines Kabelbruchs warten.
Not-Aus/Nutzerabbruch nicht automatisch zurücksetzen. Keine unbeobachteten
Bereiche freigeben, keine alten Daten frisch stempeln, kein direkter ungegateter
Motorbefehl. Die Detailregeln stehen im Masterplan; sie sind noch kein Nachweis
bereits implementierter Recovery.

### 2a. Laborumfang ohne erneute Standardfreigaben durcharbeiten

Die [Laborfreigabe LAB-1](../LABORMODUS.md) vom 28.09.2026 gilt auch für einen
neuen Agenten. Die beauftragte Kette aus Analyse, isoliertem Build, technischen
Preflights, Recorder/Stack, Karten-/Scope-Abgleich, begrenztem Produktlauf und
Auswertung ohne wiederholte identische Erlaubnisfragen bearbeiten.

Stale Topics, fehlende Ziele, Profile, Builds oder Scope-Neubindung sind
technische Aufgaben: innerhalb des Auftrags selbst lösen, nicht den Benutzer
erneut nach sämtlichen Laborbedingungen fragen. Notwendige Bewegungssperren
und reale Fehlermeldungen bleiben bestehen. Aktive Kindziele erst im regulären
aktiven Produktmodus erwarten, nicht im Read-only-Preflight.

Keine physische Motorsperre oder Bedienhandlung aus der Laborfreigabe ableiten.
Vorhandene verlässliche Zustandsinformationen verwenden; nur tatsächlich nötige,
nicht selbst ausführbare Bedienhandlungen konkret anfordern. Ein konkreter
Widerspruch, Not-Aus/Widerruf oder eine Umfangsänderung wird gezielt geklärt.
Kein automatisches Zurücksetzen echter Stopps und keine unbegrenzten Wiederholungen.

LAB-1 ersetzt ältere Forderungen nach einer neuen Zustimmung für jeden bereits
beauftragten unveränderten Teilschritt. Es verändert keine fachlichen Testgrenzen,
Messnachweise oder hier dokumentierten Ergebnisse. Die folgende Historie ist
keine Quelle für neue pauschale Freigabeschleifen.

## 3. Abgeschlossen: Integrationsbasis und Auditbestand konsolidieren

Der Auftrag aus der Referenz `26360001f65e05a5b88a58581771c241291fa0e5`
wurde auf Themenbranch `docs/we1-integrationsbasis-audit` bearbeitet. Ergebnis,
Quellzuordnung, frischer Voll- und Teilbuild, Tests, ROS-Exportpfadgrenze,
Abort-/Latch-Inventur und abgegrenztes Recoverypaket stehen ausschließlich im
[STATUS.md](STATUS.md). Die Arbeitskopie `~/roboter_ws` wurde nicht umgeschaltet;
keine Runtime aktiviert, kein Merge und keine Fahrt.

Der letzte HWT-Fehler ist im lokalen Bag auf den Wechsel
`raw_sources_ready` → `raw_driver_not_ready` bei `1790492567.5659919`
eingegrenzt. Das Bag enthält keinen `/shadow/hwt601/raw_status_json`-Topic;
die verletzte Einzelbedingung und ihr Originalwert fehlen. Der Standard-Vollbuild
ist wegen des `behaviortree_cpp`-CMake-Exportpfads blockiert; mit einem
temporären externen Bibliothekspfad wurden 24 Pakete isoliert gebaut.
Gerätefreie Tests und Grenzen sind getrennt im STATUS bewertet.

## 4. TOR 1 softwareseitig abgeschlossen: HWT-Erstfehlerdiagnose

Dieser Abschnitt beschreibt den damaligen TOR-1-Stand; die aktuelle
Recovery-Implementierung und ihre Grenzen stehen in STATUS Abschnitt 5.

Auf PR #103, Basis `3ed63f278b668fe9be64ce02568911e1b99f7fe8`,
implementiert Commit `f1f6b74a5e5aea1ba43c50beb75f5f954218fb78`
die einmalige Erstfehleraufnahme im `Hwt601FusionHealth`. Der Gate-Status
veröffentlicht sie additiv. Die vorhandene Fehlerentscheidung, Fristen,
Kalibrierung, Latches und Bewegungsblockierung wurden nicht geändert.
Zwei Pakete wurden auf dem bestehenden isolierten Vollbuild neu gebaut;
177 registrierte Tests bestanden. Der genaue Kandidat steht im STATUS.

Die alte Bag-Aufzeichnung enthält weder das verletzte HWT-Rohstatusfeld noch
dessen Originalwert. Ihre ausgeführte Paket-/Präfixreihenfolge ist ebenfalls
nicht vollständig protokolliert. Diese historischen Werte bleiben offen;
ein neuer Lauf beweist die alte Ursache nicht rückwirkend. Zum damaligen
TOR-1-Abschluss war TOR 2 noch nicht zur Umsetzung freigegeben; die spätere
Nutzerentscheidung ist in Masterplan v1.1 und STATUS Abschnitt 5 festgehalten.

## 5. Aktueller Folgeauftrag und historische Kindziel-Abnahmevorlage

### Aktueller Auftrag vom 29.09.2026: Schritt 3 real abnehmen

**Ergänzter ausführbarer Auftrag:** Regulären A→B→C-Produktlauf bis zur
vollständigen Türdurchfahrt und Weitererkundung im angrenzenden Bereich führen.
HWT-Fix `513af02` ist im bestehenden Overlay bytegleich aufgelöst; keine
erneute Implementierung. Gemäß Nutzerpräzisierung vom 29.09.2026 und LAB-1 §3
keine manuelle Motorsperre als Standardvoraussetzung verlangen: rein lesenden
Vorlauf ohne Motorsteuerungs-/Aktor-Schreibprozess technisch prüfen und starten;
Encoder-Erreichbarkeit und Stillstand selbst messen. Der Betreiberbeleg
für zwei Zimmer plus Flur ist im lokalen R9-Profil und ROBOT_TRANSFER vorhanden.
Seine alte SLAM-Geometrie nicht wiederverwenden; aktuellen Kartenbezug und
benötigte Portalmonitorparameter vor Fahrt tatsächlich binden. Keine allgemeine
Freigaberunde. A verlangt Aufgabenfortschritt, B getrennte Pflichtfälle
(Umfahrung, Nahbereichshalt/Wiederaufnahme, lösbare Wand/Ecke), C vollständige
Heckpassage und Fortsetzung derselben Mission im angrenzenden Bereich. Aktuelle
Vorbereitungsbefunde und der konkrete Blocker stehen im STATUS Abschnitt 7.

**Aktuellster Stand nach Fortsetzung:** Commit `513af02` auf PR #105 korrigiert
einen im neuen realen A-Lauf konkret nachgewiesenen HWT-Callback-Überholer.
Scan, autonome Nav2-Kinder, Vorwärtsfahrt und Neuplanung waren zu sehen; vor
Zielerreichung verriegelte der Explorer fälschlich die frisch eingetroffene
Rohprobe als ungültig, worauf das Kind terminal gecancelt wurde. Die echten
Erstwerte und die Grenze stehen im STATUS Abschnitt 7. Gerätefreie Vorher/
Nachher-Regression, 157 Pakettests und isolierter `robot_state_estimation`-
Build bestanden; der reparierte Realfall ist noch offen. **Genau nächster
Schritt:** Nach bestätigter physischer Motorsperre motorloser Vorlauf mit
diesem Overlay, anschließend reguläre autonome A-Zielanfahrt in demselben
LAB-1-Umfang. Nur bei A-Nachweis B und C fortsetzen; keine künstliche HWT-
Störung, keine Grenzlockerung und keine Wiederholung des A4-Schlupfvergleichs.

**Historischer Zwischenstand nach A4:** Kandidat `872f6a8`.
Vollständiger Scan ohne erneuten Fehler; autonomes Frontier-Kind erzeugt,
angenommen und bewusst via Mission Manager terminal gecancelt. Keine lineare
Endkommandierung im Kindfenster, keine Zielerreichungsabnahme. Rad-/Roh-IMU-/Yaw-/
EKF-Raten stimmen im Vergleichsfenster 5,0–5,7 rad weitgehend überein; die alte
Abweichung wurde dort nicht reproduziert. Stack/Recorder/Wächter beendet.
**Pausenstand 29.09.2026:** Nutzer setzt später fort. A4 ist abgeschlossen; Stack und Recorder sind aus. Beim Fortsetzen mit der regulären autonomen Zielanfahrt weitermachen, ohne den Schlupf-Sondertest zu wiederholen. Motorsperre zuletzt vor A4 als „frei“ gemeldet; danach angefordertes erneutes Sperren blieb unbestätigt und muss vor Bewegung aktuell geprüft werden.

**Beobachterabgleich abgeschlossen:** Der Nutzer meldet „alles inordnung
nichts auffälliged“; das passt zu den neuen Rad-/IMU-Messwerten. Keine
rückwirkende Ursachenbehauptung für A3. **Genau nächster Schritt:** Offene
reguläre A/B/C-Kernabnahme fortsetzen, zunächst autonome Zielanfahrt und
Zielerreichung bzw. sinnvolle Neuplanung. Keine weitere Schlupf-Sonderprüfung
oder vorsorgliche Softwareänderung. Die erneut
angeforderte Motorsperre ist noch unbestätigt. Details und Originalzeiten im
STATUS; keine historische physische Ursache aus dem neuen Lauf erfinden.

**Historische Zwischenstände A1–A3 (durch A4 ergänzt):**

**Laufender Ergebnisstand:** Software `872f6a8` behebt die reproduzierte
Odometrie-Lesereihenfolge-Race und negative Restwartezeiten; 161 gezielte Tests,
isolierter Build und motorlose Vorläufe bestanden. Drei reale Starts: A1
`initial_scan_odom_stale`, A2 vollständige Drehung, dann negative Wartezeit,
A3 `initial_scan_too_slow` ohne Wiederkehr beider Softwarefehler. A/B/C noch
nicht bestanden. Radbasierte Rate war höher als die übereinstimmenden Roh-IMU-,
Yaw- und EKF-Raten. Keine physische Ursache erfinden; kein Parameterlockern.
**Unmittelbar nächster Schritt:** Angefragte Vor-Ort-Beobachtung zu
Kontakt/Schlupf/Bewegung und Motorsperre mit den A3-Messdaten abgleichen,
konkreten Befund beheben und den regulären Kernablauf fortsetzen. Keine blinde
weitere Wiederholung bei ungeklärtem Bewegungsbefund. STATUS Abschnitt 7 enthält
die Originalzeiten, rekonstruierten Werte und Grenzen.


Basis PR #105 / `5c6ff0e`, funktionaler Kandidat `6429bd6`; Masterplan v1.1
unverändert. Schritt 2 ist für den ersten HWT-Fall abgeschlossen: gerätefreier
Nav2-Kind-Recoveryvertrag und reale Initialscan-Recovery bestanden. Reale
Kindziel-HWT-Injektion bleibt geparkter Robustheitsrest, kein Gate, kein
fehlgeschlagener Produktnachweis.

Genau ein durchgängiger Auftrag: **A → B → C** gemäß STATUS Abschnitt 7.
A: gesunde Quellen, aktuelle Karte/TF, regulärer Explore-Auftrag, autonomes
Frontierziel, akzeptiertes Nav2-Kind, reale Bewegung und Zielerreichung oder
sinnvolle Neuplanung bei aktiver Mission. B: realer Hindernis-/lösbarer
Wand-/Eckfall, Schutzwirkung, zulässiger Alternativweg/Befreiung und Fortsetzung
desselben Auftrags. C: autonom erkanntes Portal, vollständige Durchfahrt,
Roboter im nächsten Bereich und dort weitere Karten-/Frontierarbeit derselben
Mission. Ein bekannter Durchgang bleibt Transitweg.

Das Recovery-Produktprofil mit Initialscan, WE-Navigation, Portal und Coverage
verwenden; keine lokalen HWT-Sondergrenzen (.45/1.50-m-Route, .60-m-Translation,
Vorwärtskegel, enger erzwungener Korridor), keine HWT-Leserpause. Alle produktiven
Schutz-, Footprint-, Costmap-, VL53-, Frische-, TF-/Pose- und Geschwindigkeitsregeln
unverändert. 900 s Gesamtfrist und 120 s Kindfrist des Profils beibehalten.

Motorloser Vorlauf nach Änderungen; vorhandenen Build, Manifest und synchronen
Recorder einschließlich versteckter Action-Themen verwenden. Mission nur über
Mission Manager → BT → WE-Explorer → Nav2. Keine manuellen Ziele oder Testtasks.
Bestehende Laborfreigabe gilt durchgängig für technische Zwischenschritte,
Mission und A→B→C; keine wiederholten Freigabefragen. Tatsächliche
Hardwarestellungen/Beobachtungen nicht erfinden. Konkrete Softwarefehler minimal
korrigieren, gezielte Regression, betroffenen Fall erneut prüfen und fortsetzen.
Bei Hard-Fault sicher beenden; Shutdownbefunde separat. Kein Merge oder
permanenter Installwechsel, keine allgemeine Optimierungsrunde.

Erfolg erst bei realem A/B/C-Nachweis, danach WE-M4 vorbereiten. Ansonsten genau
den konkreten Produktblocker mit Originalbeleg dokumentieren und beheben.

### Historischer Auftrag nach dem Ergebnis vom 28.09.2026 (abgelöst)


**Basis:** `6429bd6`, gleicher PR #105 / `feature/hwt-hold-recovery-resume`,
fachlicher Masterplan v1.1 unverändert; Laborarbeitsregel LAB-1 v1.0 gilt.
Aktueller vollständiger Befund ausschließlich
[STATUS Abschnitt 7](STATUS.md#7-nächster-schritt-und-historie).

Real-Opt-in und lokale Scope-Prüfung sind korrigiert; die vorhandene optionale
Vorwärtsbegrenzung wirkt nun auch im WE-Pfad, ohne Ziel-/Task-/Routenänderung.
1.199 Regressionen und isolierter Explore-Build bestanden. Ein autonomes
Nav2-Kind wurde vor Bewegung wegen der unzulässigen Schwenkroute terminal
gecancelt. Kein realer Brems-/Recoverynachweis, keine HWT-Injektion. Der spätere
motorlose Vorlauf bestand; angebotene Kandidaten lagen außerhalb der aus dem
bestätigten Korridor abgeleiteten lokalen Richtungsbegrenzung. Ein einmaliger
FC03-Paarzeitüberlauf bleibt dokumentiert; kein Grenzwert wurde erhöht.

**Genau nächster Schritt:** Den realen Startaufbau vor Ort so ausrichten,
dass eine echte autonome Frontieraufgabe im erneut bestätigten begrenzten
Vorwärtskorridor erreichbar ist. Dann aktuellen Quellen-/Pose-/Kartenbezug
prüfen, neues lokales Scope binden und denselben vorbereiteten begrenzten
Stopp-/Kindzielnachweis fortsetzen. Kein manuelles Nav2-Ziel und keine
synthetische Aufgabe. Fehlenden Kandidaten nicht durch weitere beliebige
Fahrversuche ersetzen. Die allgemeine Laborfreigabe bleibt übernommen;
aktuelle Hardwarestellung nicht aus einer Softwarefreigabe ableiten.

Route ≤1,50 m, Translation ≤0,60 m kumuliert einschließlich Nachlauf, 35/340 s
und Produkt-Schutzgrenzen bleiben unverändert. Die zusätzlich bestätigten
5 cm hinter der Roboterkante sind nur eine Startreserve, keine Rückwärtsfreigabe.
Der vorhandene Recorder muss mit `--include-hidden-topics` laufen; die
gerätefreie Gegenprobe dieser Option ist bestanden. Vergangene Action-Statusfolge
liegt nur im Controllerlog, nicht vollständig im Bag. Der Stoppmessmodus
verwendet keinen HWT-Eingriff. Erst mit übertragbarem realem
Nachlaufbeleg und gültigem vollständigem autonomem Plan darf der bestehende
Recovery-Einzelfall folgen. Aktuell `stopping_evidence=null`; reale Stoppreserve
nicht erfinden. Keine weitere vorsorgliche Produktreparatur, kein Merge,
kein dauerhafter Installwechsel, keine Wohnungsfahrt und kein Stufe-3-Grün.

**Folgende frühere Berichte bleiben historisch erhalten; ihre damaligen
Folgeaufträge sind durch den vorstehenden Ergebnisstand abgelöst.**

**Datierter Testentscheid vom 28.09.2026, vor erneutem Realversuch:**
Software `e5b221be5e9e54296319c96640efbdef6cb63969`, dokumentierter vorheriger
Abschluss `e5821f2`, gleicher PR #105. Softwaretests und bestandenes
Rundblick-Recovery werden übernommen. Keine erneute Ursachenanalyse.

Für genau den einen Kindzieltest wird die vollständige autonome Routengrenze
von 0,45 m auf **1,50 m** ersetzt. Die tatsächliche Translation bleibt
**≤ 0,60 m kumuliert einschließlich Nachlauf**, ohne Reset bei HOLD, Resume
oder neuem Kind. 35 s ab erstem Kind / 340 s insgesamt, vorhandene
Geschwindigkeits- und Schutzgrenzen unverändert. Beendigung nach kurzer
nachgewiesener Wiederaufnahme; Zielerreichung ist kein Testziel.
Ganze Route, Kurven und Footprint müssen im aktuellen Live-Scope freigegeben
sein. Keine Scope-Ausweitung oder unbekannten Flächen. Produktpfad ausschließlich
Mission Manager → BT → WE-Explorer → Nav2, autonomes Ziel, keine direkte
Explore-Action. Kein Initialscan, Portal, Coverage, Rückfahrt oder Ersatzweg.
Eine abgesicherte HWT-Leserpause von ungefähr 0,25 s erst nach aktivem Kind,
Task-ID/UUID und Vorwärtsbewegung. Keine zusätzlichen Fahrversuche.

**Aktueller Ausführungsstand:** Lokaler Controller trennt die Grenzen und
zieht belegte Stoppreserven von Distanz- und Zeitlimits ab. 15 gerätefreie
Prüfungen bestanden. Ohne an den aktuellen Pfad gebundenen realen Nachlaufbeleg
sperrt er vor ROS-/Missionsstart. Der vorhandene Messwert 0,02125 m stammt aus
einem Diagnose-Nullkommando bei etwa 0,03013 m/s; er belegt die aktuelle
Cancel-Kette bis 0,12 m/s nicht. Keine tatsächliche Reserve daraus erfunden.
Keine Geräte/Prozesse/Mission/Injektion gestartet. Neue Live-Scopebindung und
motorloser Vorlauf noch ausstehend; keine bisherige Karte als aktuell ausgegeben.

**Genau nächster Auftrag:** Einen separat freigegebenen begrenzten realen
Nachlaufnachweis der aktuellen Stop-/Cancel-Kette bei den vorgesehenen
Geschwindigkeiten erbringen oder einen übertragbaren bestehenden Nachweis
bereitstellen. Daraus die Reserve festlegen, dann denselben Kindzieltest nach
aktuellem motorlosen Quellen-/Pose-/Scope-/Routencheck durchführen. Bestehende
Laborfreigabe für technische Zwischenschritte beibehalten; keine identischen
Freigabefragen. Keine Nachlaufannahmen, keine automatische zusätzliche Fahrt
und keine vorsorgliche Produktreparatur. Verbindliche Belege: STATUS Abschnitt 7.

**Die nachfolgenden Berichte sind historisch; ihre damaligen Folgeaufträge
sind durch den vorstehenden aktuellen Umfang abgelöst.**


**Historischer Ergebnisstand vom 28.09.: aktiver Kindziel-Testfall nicht
ausgelöst.** Der korrigierte Ablauf wurde im bestehenden PR-#105-Produktpfad
einmal aktiv gestartet. Das lokale Profil ohne Initialscan und die neu
gemessene Scopebindung waren geladen, reale HWT-/Encoderquellen und Stillstand
vor Mission gesund. Recorder und unabhängiger Cancel-Wächter liefen vor dem
Mission-Manager-Auftrag. In 247,97 s entstand kein Nav2-Kind: alle 249
Explorer-Statusbilder nannten `stale_source:portal_memory`, trotz zuletzt
fünf geeigneter Frontier-Aufgaben. Es gab keine Goal-UUID, keinen Nav2-Plan,
keine HWT-Injektion und keinen Nichtnull-Fahrbefehl; `/odom` blieb bei
0,000 m Translation. Danach meldete der Explorer ohne vorherigen HOLD den
ungeplanten terminalen Grund `hwt601_raw_missing_stale_or_invalid`. Der
unabhängige Fusion-Status und die gespeicherten Rohdaten belegen den
Explorer-internen Erstwert nicht. Der Produktlauf wurde beendet, 28/28
Kinder sauber, Ports frei. Details und lokale Belege: STATUS Abschnitt 7.

**Historischer Folgeauftrag (abgelöst):** Ausschließlich gerätefrei den vorhandenen Bag,
die Statusfolge und die konkreten Quell-/Policy-Stellen des aktiven No-Scan-
Pfads abgleichen: Warum bleibt `portal_memory` durchgehend stale, und was
ist für den Explorer-eigenen terminalen HWT-Befund tatsächlich belegt?
Eine eng begrenzte Korrektur oder ein neuer Realversuch wird erst aus diesem
Befund entschieden; keine erneute allgemeine Inventur, keine vorsorgliche
Parameteränderung und kein automatisch angehängter Geräteversuch. Der real
bestandene HWT-Initialscan bleibt erhalten. Die unabhängige Motorsperre
und Vor-Ort-Beobachtung werden getrennt bestätigt.

**Historische Testreihenfolge, nun korrekt eingeordnet:** Der motorlose
Vorlauf endete erwartungsgemäß an `hwt601_readonly_preflight_no_motion`.
Ein aktives Kind gehört erst in den aktiven Produktlauf und ist Bedingung
vor der HWT-Injektion, nicht vor dem Ende des motorlosen Preflights.
HWT-, Gate-, Recovery- und Sicherheitscode blieben unverändert.

**Historisches Ergebnis des motorlosen Vorlaufs vom 28.09.: TESTFALL NICHT AUSGELÖST.** Das
Einmalprofil ohne Initialscan wurde ausschließlich lokal erstellt und
im zweiten motorlosen Produktstart tatsächlich geladen (SHA256
`a5e6b1d08041b3f63bb1fcd2b7730b709194fbe210426770f1ff759d2e70dcd6`).
Die neue Live-Karte und Pose wurden mit dem Scope verglichen; FC03,
HWT/Yaw, Fusion-Quellen und VL53-Frames waren gesund. Ein echter
Mission-Manager-Auftrag erreichte BT/Explorer. Wegen
`hwt601_readonly_preflight_no_motion` bei `active_drive=false` gab der
Explorer trotz offener Frontier-Aufgaben kein Nav2-Kind frei. Bag:
null Action-Status/Feedback, null Nichtnull-Fahrbefehl. Kein manuelles
Nav2-Ziel, keine Fault Injection und keine Fahrt. Der Stack ist beendet.

**Historisch ausgeführte korrigierte Reihenfolge:** Der Produktstart für den Einzelversuch verwendet
`active_drive=true`, `use_hwt601_odometry=true` und das gehashte lokale
Einmalprofil ohne Initialscan. Nach dem aktiven Nullkommando-Preflight startet
Explore ausschließlich via Mission Manager → BT → WE-Explorer. Die vorhandenen
Produktprüfungen begrenzen Scope, Footprint und Route vor Bewegung. Erst ein
belegtes aktives autonomes Nav2-Kind mit Task-ID, Goal-UUID, Route ≤0,45 m
im Scope und gemessener Vorwärtsfahrt erlaubt **eine** vorbereitete HWT-
Leserpause. Ohne solches Ziel: kontrollierter Cancel ohne Injektion und
`TESTFALL NICHT AUSGELÖST`. Gesamtlimit 340 s, kein Kind nach 300 s,
35 s ab erstem Kind und 0,60 m kumulierte Translation bleiben harte
Grenzen. Keine direkte Explorer-Action und kein manuelles Nav2-Ziel.

**Historischer Torstand vom 28.09., zweiter passiver Vorlauf:** Der Nutzer
bestätigte FC03-erreichbare Controller bei weiterhin unabhängig gesperrter
Motorendstufe, Stillstand und Beobachtung. Der unveränderte Produktstand
wurde isoliert neu gebaut und manifestiert; FC03, HWT/Yaw, Fusion-Quellen,
Karte/TF und VL53-Framezustand waren motorlos gesund. Das neue lokale
Einmal-Scope ist an die Live-Karte des Vorlaufs gebunden, ohne altes
Polygon. Ein 0,45-m-gerader Zielkorridor liegt mit Footprint im Scope.
Die manuelle **Planungsprobe** ergab allerdings 0,494 m Pfad und zählt
weder als zulässiges ≤0,45-m-Ziel noch als autonomes Kind. Der passiv
gestartete Stack ist bereits sauber beendet; seine Scope-Bindung darf
nicht ungeprüft auf einen neuen SLAM-Start übertragen werden. Vor allem
fehlt noch die aktuelle Bestätigung des freien Bereichs **hinter** dem
Roboter für den im Produktprofil aktiven 360°-Initialscan. Bis dahin
**keine Fahrt**. **Damals einziger nächster Schritt:** Rückwärtigen Schwenkraum
vor Ort bestätigen, dann die bereits festgelegte Einzelabnahme nur mit
erneut gebundener Live-Karte und einem wirklich autonomen Kindziel nach
den unveränderten Grenzen durchführen.

**Historischer erster Torstand vom 28.09.: motorloser Scope-Vorlauf fehlgeschlagen,
Fahrt gesperrt.** Das isolierte PR-#105-Produktpräfix wurde neu gebaut und
manifestiert. Ein frischer Map-/TF-Kontext und ein neues Polygon wurden aus
der bestätigten freien Geradeausfläche nur lokal erfasst; das Einmalprofil
bleibt `accessible_scope_verified=false`. Die FC03-Encoderquelle verriegelte
nach ausbleibender Antwort, und die digitale Karte enthält im kurzen
Vorwärtskorridor noch unbekannte Zellen. Der Beobachter bestätigte, dass
die unabhängige Motorsperre hier auch die Controllerelektronik trennt;
FC03 unter dieser Sperre ist damit derzeit unmöglich. Die fehlende Antwort
beweist allein keinen Encoderdefekt. Details und lokale Artefaktpfade
stehen in STATUS Abschnitt 7. **Damals einziger nächster Schritt:** Eine
vor Ort überprüfbare Trennung von gesperrter Motorendstufe und erreichbarer
Controllerelektronik herstellen, danach den Karten-/Scope-/Routennachweis
auf einer neuen Live-Kartenbindung wiederholen.
Vorher kein aktiver Kindzielversuch; die vorab erteilte Fahrfreigabe ist
nicht durch einen bestandenen Preflight wirksam geworden.

Der reale Roh-/Yaw-Rundblick auf PR #105 ist **für den Initialscan bestanden**
(STATUS Abschnitt 5). Er hatte kein Nav2-Kind und belegt keine Kindziel-
Fortsetzung. Der nächste Test verwendet dieselbe definierte transiente
Rohfrischeklasse, keine neue HWT-Hypothese und keine manuelle Zielvorgabe.
Die frühere Vorlage endete mit dem **damaligen NO-GO** wegen der inzwischen
korrigierten Reihenfolge. Sie ist kein neuer Freigabeentscheid.

### Historische Kandidaten- und Sperrenlage vor dem neuen motorlosen Vorlauf

- Quellbasis: funktionaler Commit
  `6b666d97d7e11326c9f75dccbc4253112e99b578` auf
  `feature/hwt-hold-recovery-resume`; spätere Commits bis zum dokumentierten
  `31358a980aaf6d237fcc7bf78c03e96f96e69d25` änderten nur Dokumente.
  Der bewiesene Produktstart ist `robot_bringup/app_mapping.launch.py` über
  Mission Manager → BT → WE-Explorer → Nav2 `NavigateToPose`.
- Letztmals **ausgeführt**: Profil
  `hwt601_recovery_acceptance_params.yaml`, SHA256
  `ee3b42eef682a830892e93f84093baf1547a84f76d6baa3e480a81dc1de393c4`;
  ROS Humble → Slam- → LiDAR- → Vollbuild- → Recovery- → Yaw-Overlay.
  Das Manifest `~/.local/share/amadeus/tests/hwt-recovery-real-20260927-fxU0To/runtime_manifest.json`
  und `module_resolution.json` beweisen diese frühere Laufzeit. Die
  temporären `/tmp/we1-full-shim-install`, `/tmp/we1-hwt-recovery-install`
  und `/tmp/we1-hwt-yaw-install` existieren am 28.09. **nicht mehr**.
  Damit ist heute weder ein installiertes Abnahmeprofil noch der korrigierte
  HWT-/WE-Paketpfad erneut auflösbar. Kein aktiver Install wurde gewechselt.
- Das damalige Profil hat `wohnungserkundung_accessible_scope_verified=false`
  und eine leere Scope-ID. Im Frontierpfad wird damit `scope=None` erzeugt;
  ein Frontierkandidat kann trotzdem entstehen. Dieses Profil allein
  begrenzt also keine reale Fahrstrecke. Der bisherige Real-Bag endete vor
  dem vollständigen Initialscan mit `open_tasks=0`,
  `goal_candidate=unavailable`, `navigation_dispatched=false`. Ein gültiges
  autonomes Kindziel im aktuellen Kartenframe ist **nicht belegt**. Der
  Nutzer bestätigte eine aktuell freie Geradeausstrecke, kennt deren
  Dokumentpfad jedoch nicht. Die lokale Suche fand als jüngsten passenden
  historischen Scope
  `~/.local/share/amadeus/profiles/stage3-real-20260925-after-r2-scope.yaml`
  (SHA256 `74c14c2d5a37a7ebc6f7e84206deba2ff6d7197135a4ab31b4772530917451a5`),
  Scope-ID `stage3-local-scope-20260925-after-r2`, Session
  `stage3-20260925-after-r2`. Dessen gebundener Diagnoselauf hatte den
  Map-Fingerprint `4f17785f…`; der jüngere HWT-Lauf vom 27.09. meldet
  Session `hwt601-parity-20260926`, Map-ID `map-90b3fcce…`. Das alte
  Polygon hat keine belegte Transformation/physische Bindung zur aktuellen
  Karte. Die vor Ort bestätigte Geradeausstrecke ersetzt diese technische
  Zuordnung nicht; keine Wohnungskoordinaten ins Repository übernehmen.

### Historische Annahmebedingungen des ausgeführten Einzelversuchs

1. **Zielsystem:** Den unveränderten funktionalen Stand isoliert wieder
   aufbauen; in einer frischen Shell mit `hwt_diagnose_manifest.py` Quell-SHA,
   sämtliche tatsächlich aufgelösten Paketpräfixe, Yaw-Node/Core/Health-
   Hashes, Nav2-Realprofil, exaktes lokales Testprofil samt SHA und Launch-
   Argumente vor dem Start sichern. Keine Testadapter, synthetischen
   Sensorpublisher oder Änderung am aktiven Install. Bei fehlender
   Bytegleichheit: NO-GO.
2. **Karte und Scope:** Die anwesende Person muss eine kurze freie Strecke
   einschließlich Footprint, Auslauf und unabhängigem Halt **im aktuellen
   Kartenframe** vor Ort bestätigen. Das lokale Einmalprofil muss eine
   nichtleere Scope-ID, ein an diese Kartenidentität gebundenes Polygon und
   `wohnungserkundung_accessible_scope_verified=true` enthalten. Reale
   Koordinaten und Karten bleiben lokal. Ein altes Polygon nach SLAM-Neustart,
   ein bloßer Profil-Hash oder `scope=None` sind NO-GO. Portalquerung,
   Coverage und Rückfahrt sind im Einmalprofil aus
   (`portal_crossing_enabled=false`, `coverage_enabled=false`,
   `return_to_start=false`); `max_frontier_goals=1`,
   `max_failed_goals=1`, `overall_timeout_s=340`, `goal_timeout_s=35`.
   Dieses nur lokal gespeicherte Einmalprofil ist vor dem Start zu hashen
   und mit dem installierten Explorer zuzuordnen. Kein Produktprofil im
   Repository wird beiläufig geändert.
3. **Autonomes Kind:** Der unveränderte Produktpfad muss im aktiven Lauf
   ohne erneuten Initialscan selbst eine offene Frontieraufgabe und einen
   aktuellen, eindeutigen Zielkandidaten aus Karte, Policy und Costmap
   erzeugen. Vor der Fault Injection müssen Task-ID, Karten-/Scope-Kontext,
   aktuell freie Route und die aktive Nav2-Goal-UUID im Recorder vorliegen.
   Die Route darf höchstens 0,45 m lang sein und muss vollständig in der
   bestätigten freien Strecke liegen; `min_goal_distance_m=0,30` bleibt
   unverändert. Kein gültiges Ziel oder nur ein manuelles/synthetisches Ziel:
   **TESTFALL NICHT AUSGELÖST**, Cancel ohne HWT-Pause. Wenn bis 300 s nach
   Explore-Start kein solches Kind aktiv ist, ebenfalls Cancel ohne
   Injektion; keine verlängerte Zielsuche.
4. **Harte Einzelgrenzen:** Maximal **340 s ab Explore-Start** einschließlich
   HOLD und RESUME; höchstens **35 s ab erster aktiver
   Kindziel-UUID**; höchstens **0,60 m kumulierte gemessene Translation**.
   Zuerst erreichte Grenze löst Mission-Manager-Cancel aus. Der Scan-Sollwert
   und sein Produkttimeout bleiben unverändert; der Initialscan ist im
   lokalen Einmalprofil für diesen Versuch abgeschaltet. Im
   Kindzielteil gelten die vorhandenen Realprofilgrenzen
   `desired_linear_vel=0,10 m/s`, Smoother-Maxima 0,12 m/s und
   0,25 rad/s; Überschreitung, Rückwärtsfahrt oder Verlassen von Scope/
   freier Strecke: sofortiger Abbruch. Ein unabhängiger zeitlicher
   Cancel-Watchdog und der physische Halt bleiben verfügbar. Diese
   Versuchslimits sind **keine** Lockerung von Produkt- oder Frischegrenzen.
5. **Ein Eingriff:** Erst bei tatsächlich aktivem autonomem Kind und
   gemessener Vorwärtsfahrt genau eine etwa 0,25-s-SIGSTOP-Pause ausschließlich
   des identifizierten HWT-Lesers, mit unabhängigem SIGCONT-Watchdog.
   Erwartete Klasse `raw_missing_stale_or_invalid` wegen Rohmessalter
   >0,20 s ohne Disconnect/Reconnect. Kein Kabelzug, kein Motor-/Safety-
   Prozessstopp, kein zweiter Fehlerreiz. Andere Fehlerklasse oder nicht
   ausgelöste Lücke: Cancel, keine Nachinjektion.
6. **Gemeinsamer Nachweis:** Den bestehenden Recorder **vor dem Stack**
   starten und seine Roh-/Yaw-/Bias-, Encoder-, Wächter-, Gate-, cmd_vel-,
   Odom-, TF-, Karten-, Costmap-, VL53-, Mission- und Explorer-Themen um
   `/navigate_to_pose/_action/status`, Action-Feedback und geplante Route
   ergänzen. Originalzeiten und die in der echten Action-Statusfolge
   enthaltenen Goal-UUIDs bewahren. Erfolg nur bei beobachtetem physischem
   Halt und gemessenem Encoder-Stillstand; terminalem alten Kind;
   unveränderter Explore-Elternaktion und derselben offenen Task-ID;
   stabilem Bias und neuen gültigen Yaw-Daten; frischen Quellen, aktueller
   Kartenpose/Scopebindung und erneut freier Route; Gate-ACK; **höchstens
   einem neuen Kind** mit neuer UUID für denselben Task; und tatsächlicher
   begrenzter Fahrt nach RESUME ohne alte Kommandos. Späte Antworten des
   alten Kindes dürfen nichts erneut aktivieren.
7. **Gegenfälle und Abschluss:** Dauer-/Hard-Fault, fehlendes terminales
   altes Kind, veraltete/gesprungene Pose, unsichere Route, fehlender
   Stillstand, Not-Aus oder Nutzerabbruch beenden ohne automatische
   Wiederanfahrt. Bei jeder Abweichung Mission-Manager-Cancel, Stillstand
   vor Ort bestätigen, Stack/Recorder geordnet beenden, Ports prüfen und
   unabhängige Motorsperre wieder wirksam bestätigen. Ein sicherer Abbruch
   ist Schutzbeleg, kein bestandener Kindziel-Recovery-Nachweis.

**Historisch vorgesehener nächster Schritt:** Den freien Geradeauskorridor ab aktueller
Startpose mit Endpunkt und seitlicher Begrenzung im dann laufenden Kartenframe
vor Ort markieren/bestätigen und lokal neu binden. Danach das
Karten-/Scope-/Runtime-Tor anhand des isoliert wiederhergestellten
Produktkandidaten schließen und motorlos prüfen. Erst dann kann eine
gesonderte Freigabe für den gesamten begrenzten Einzelversuch eingeholt
werden. Das autonome Kindziel sollte erst **im freigegebenen Produktlauf nach
dem echten Initialscan** entstehen; es ist eine harte Bedingung **vor**
Fault Injection und vor jeder Kindziel-Fortsetzung. Fehlt es, Cancel ohne
Injektion und Ergebnis `TESTFALL NICHT AUSGELÖST`. Die konkrete
Fahrfreigabe lautete damals **NEIN**. Der inzwischen ausgeführte Einzelauftrag
ersetzte diese Reihenfolge und nutzte das lokale Profil ohne Initialscan.
Der nun aktuelle Folgeauftrag ist ausschließlich gerätefrei. Kein Merge,
kein TOR 2 und kein Stufe-3-Gesamtgrün.

## 6. Übergabe und Fortschreibung


Geprüfte Basis und Ergebnis-SHA, betroffene Dateien, wirklich ausgeführte Tests,
Evidenzpfade, Grenzen, Restbefunde und Rückfall nennen. Build, Modulprüfung,
gerätefreier Gesamtprozess, Zielsystem und physische Abnahme getrennt halten.
Doppelte Testzählungen und `mergeable` nicht als Funktionsnachweis verwenden.

STATUS ist der aktuelle fachliche Bericht. PROJECT_MEMORY enthält übergreifende
Entscheidungen; ROBOT_TRANSFER wird bei tatsächlicher Betriebs-/Installationswirkung
fortgeschrieben. Masterplan nur mit expliziter Grundentscheidung versionieren.
Keine weitere parallele aktuelle Statusdatei und keine grüne Gesamtstufe ohne
vollständigen vereinbarten Nachweis.

Der Vorgängerauftrag zu M3/U ist
[byteidentisch archiviert](../archive/2026-09/WOHNUNGSERKUNDUNG_AGENTENAUFTRAG_40b5b49.md).
Seine damalige Basis PR #91 und sein Abschnitt 7 sind **kein aktueller Auftrag**.
Historische fachliche Nachweise bleiben erhalten; Archive nicht automatisch ausführen.
