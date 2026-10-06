# Karten- und Quellenvertrag – AP-02 / MASTERPLAN v1.3

Diese Zuordnung beschreibt die vorhandenen Softwareverträge und die gezielte
AP-02-Korrektur. Ergebnis/Nachweisstufe ausschließlich im [STATUS](STATUS.md).
Die Zahlen sind Grenzwerte aus Code/Profilen, keine gemessenen Jetson-Latenzen.
Es gibt keine neue allgemeine Health-State-Machine und keine erhöhten Fristen.

## Kartenlebenszyklus

Fingerprint: kanonisches `amadeus_map_identity.map_snapshot_fingerprint` über
Frame, Auflösung, Ursprung einschließlich Quaternion, Breite/Höhe und Zellinhalt.
Der Quellstempel gehört zur Beobachtung, nicht zum Inhaltsfingerprint.
`MapManagerStatusCorrelator` bindet den explizit konfigurierten `metric_session_id`
und den ersten Fingerprint an einen stabilen Kartenkontext. Ein Inhaltswechsel
allein erzeugt keine neue Sitzung oder neues Aufgabengedächtnis.

| Eingang / Übergang | Softwarewirkung |
|---|---|
| Noch keine Karte oder kein gebundener Scope | Wartet; kein erfundener Kontext |
| Exakt gleiche Beobachtung, auch nach dem Duplikatfenster des Produzenten | `accepted_maps` und `observed_maps` bleiben stabil |
| Gleicher Inhalt mit neuem Stempel | `accepted_maps` stabil; `observed_maps` steigt; exakten Rohkarten-/Statusjoin erneuern |
| Neuer Inhalt mit neuem Stempel | Beide Zähler steigen; gültige Ziele behalten und auf aktuellen Rastern erneut prüfen |
| Rohkarte/Status noch nicht passend | Neue Aufgaben warten. Aktive Arbeit darf höchstens im bisherigen 1,25-s-Fenster den letzten **exakten** Join mit seinen ursprünglichen Zeitstempeln/Fristen nutzen. Identischer Inhalt bleibt der allgemeine Fall; ein bestehendes öffentliches RPP-Kind darf zusätzlich nur Freiraumentzug gemäß der folgenden Zeile verwenden |
| Neuer Inhalt ohne passenden Status | Ausschließlich bei schon aktivem öffentlichem RPP-Kind, ohne gültige private Egress-Bestände, gleichem Frame/Auflösung/Orientierung und ganzzellig ausgerichtetem Raster: frische neue Rohkarte entzieht alte Freizellen durch Unknown/Obstacle/fehlende Deckung. Alte exakte Karte/Revision/Stempel bleiben erhalten; ganze aktuelle Kontur/Route wird auf der verkleinerten Freifläche geprüft. Keine neue Freifläche, Zielwahl oder Receipt. Andernfalls Kind stoppen; originaler Join-/Quellen-/Epochenschutz bleibt |
| Rasterwachstum, Ursprungs-/Quaternionwechsel | Alten Rasterbeweis vor jeder Arrayverknüpfung entziehen; TF-gebundenen ersten Body-Zellbestand bei exakt ganzzahligem festem Rasterwachstum monoton übersetzen, sonst invalidieren. Ohne TF-Bindung Egress dauerhaft invalidieren. AP-06 mit gemeinsamer TF-Zeit: ersten physischen Bestand erhalten, exakte begrenzte Projektion und frischen ganzen Fahrzeugbeweis auf beiden aktuellen Rastern verlangen |
| Frame-/Auflösungswechsel | Auch TF-gebundenen Egress dauerhaft invalidieren; kein Wachstum-/Korrektur-Ersatzpfad |
| Frame-/Auflösungswechsel eines Rasters | Arbeitsgeneration erhöhen; auch ein zwischen zwei Auswertungen beobachteter Wechsel und Rückwechsel macht alte Arbeit ungültig |
| Neuer Session-/Mapkontext, Zähler-/Zeitreset oder verschwundener initialisierter Kartenstatus | Bestehender Adapter verweigert implizite Neubindung; Explorerfehler bleibt hart, Kind stoppen, alte Plan-/Erfolgsresultate unwirksam. Neuer Kontext erfordert ausdrücklich neue Sitzung und passende Scope-Bindung |
| Verspätete ältere Rohkarte/Costmap/Status | Nicht überschreiben, kein neuer Empfangszeitpunkt; Produzent verwirft ältere positive Quellstempel ohne neue Revision/Frische |
| Widersprüchliche Inhalte bei gleichem positivem Stempel | Kartenmanager verwirft; metrischer Verbraucher sperrt hart. Kein Reihenfolge-Raten |

Normales Wachstum entzieht den alten **Rasterbeweis**, nicht automatisch ein
noch gültiges Weltziel. Die AP-06-Präzisierung vom 05.10.2026 bindet den einmaligen
Bestand an die erste Odometriefläche und projiziert ausschließlich vollständig
gedeckte aktuelle unbekannte Zellen; ursprüngliches Polygon, Flächen-/Abstands-
historie und Budgets bleiben erhalten. Neue Routen-/Konturprüfung auf beiden
aktuellen Rastern ist nötig. Unbekannte neue Zellen bleiben unbekannt;
kein Re-Ankern, keine mitfahrende Maske und keine freie Startschneise.
Der direkte `StartEgressEvidence.check_trajectory` schützt zusätzlich gegen
inkompatible Arrayformen. Bestehende monoton schrumpfende Inventare bleiben
bei passenden Geometrien erhalten; beobachtete Zellen werden nicht erneut exempt.

Rohkarte, Status, Costmap und Evidenzmutation werden unter dem vorhandenen
metrischen `RLock` zusammen ausgewertet. Kein Service/Action-Warten unter diesem
Lock. Die Auswertung prüft Frische erneut nach der Verarbeitung. Die metrischen Rohkarten-/Costmap-/Status-/Wheel-/Lokalisierungs-/Planquellen teilen eine separate `MutuallyExclusiveCallbackGroup`: nur ein am Geometrielock wartender Callback belegt einen Executorworker; HWT-/Stop-/TF-Callbacks behalten ihre unabhängige Gruppe. HWT-/Gate-
Beobachter behalten ihre eigenen Locks/Gruppen. Die tatsächliche maximale
Callback-/Auswertungsdauer unter Jetsonlast bleibt AP-06 zu messen.

Planerarbeit bindet Sitzung/Kartenkontext, Frame, Auflösungen und Generation,
nicht jede Inhaltsrevision oder Rastergröße. Verspätete `/plan`-Callbacks werden
verworfen; selbst ein bereits fertiges Planner-Actionresultat wird bei inzwischen
ungültigem Kontext nicht verwendet. Die echte Elternschleife prüft aktuelle
Quellen/Route und Kontext vor Bewegung und vor Besuchszählung. Nav2-`success`
allein beweist weder Ankunft noch Beobachtung oder Wohnungsabschluss.

## Gemeinsames Zeitbudget

Alle Verbraucher prüfen ursprüngliches **Messungsalter und Empfangsalter**,
soweit der jeweilige Vertrag beide liefert. Verarbeitung und DDS-/Executorwartezeit
verbrauchen dasselbe Frischefenster. Statusherzschläge, EKF-Prädiktion und
erneute Publikation ersetzen keine notwendige neue Rohmessung.

Für einen auf das IO-Mittel bezogenen Encoderstempel gilt als Budgetzuordnung:
`Alter am Verbraucher = verbleibende IO-Hälfte + Produzentenverarbeitung + DDS/
Executorwartezeit + Verbraucherverarbeitung + Zeitkorrelationsunsicherheit`.
Bei 0,12 s Paar-IO sind davon bis 0,06 s bereits vor Publikation verbraucht.
Von 0,18 s bleiben dann höchstens 0,12 s für den übrigen Weg, **kein zusätzliches**
DDS-Budget. Für HWT zählt die tatsächliche Host-Empfangsmarke des Frames;
die gesamte Transaktion hat zusätzlich ihre eigene harte Deadline.

| Quelle / Entscheidung | Vorhandener Grenzwert und Gültigkeit | Zuständiger Code / Profil |
|---|---|---|
| HWT-Raw | 100-Hz-Poll; ganze FC03-Transaktion 0,03 s historisch bzw. 0,05 s nur explizites Entwicklungsprofil; Messungsfrische 0,20 bzw. 0,30 s | `hwt601_imu_node.py`, `hwt601_shadow.yaml`, `hwt601_metric_development.yaml` |
| HWT-Zeitkorrelation | AP-01: Offsetspannen mit höchstens 1 ms ROS-Lesebracket, höchstens drei Versuche innerhalb der ursprünglichen IO-Deadline; konservativer Empfangsstempel bis 1 ms + 2 ns früh, niemals neu auf Publikationszeit gestempelt | `_hwt601_clock.py`, Raw-Pfad; AP-01-Vertrag unverändert |
| Abgeleitete Yaw-Quelle | Frische 0,35 s; monoton neue Stempel; Kalibrierung verlangt u.a. höchstens 0,10 s Samplelücke | `hwt601_fusion_health.py`, `hwt601_shadow.yaml` |
| HWT-/Yaw-/Wheelstatus | Empfangsalter höchstens 1,0 s, zusätzlich passende Producerfelder und Messungsfrische; HWT-Rawstatus nominal 0,5 s | `Hwt601FusionGuard`, `Hwt601FusionHealth` |
| Passiver Encoder | Profil 20 Hz; Paar-IO höchstens 0,12 s; unveränderte Kontinuität/Messungsfrische 0,18 s; ROS-/monotoner Stempel am Paarmittel | `encoder_shadow_node.py`, `encoder_shadow_reader.py`, `encoder_shadow.yaml` |
| Aktiver Encoder mit Timingvertrag | 0,05-s-Feedbackperiode; gemeinsamer Timingkern mit 0,12-s-Paarlimit; Stale-/Recoverygap auf höchstens 0,18 s begrenzt; Quellenmittelstempel | `base_hardware_node.py`, insbesondere `_initialize_encoder_feedback`, `_accept_encoder_pair` und Timingkern |
| Historischer aktiver Encoder ohne Timingvertrag | Stale-/Healthlimit 0,30 s, Tracker-Recoverygap 2,0 s; keine Behauptung des 0,12-s-Vertrags für diesen Pfad. Dies ist kein zusätzlicher Fahrtspielraum des Timingprofils | `base_hardware_params.yaml`, aktiver Node, `Hwt601FusionHealth._wheel_limit` |
| Encoder-Timingrecovery | Eine isolierte Überziehung erst nach mindestens 20 gesunden Paaren; zwei tatsächlich neue vollständige Paare im selben 0,18-s-Kontinuitätsfenster; absoluter Recoverydeckel 2,0 s, keine Baseline-Neuinitialisierung | gemeinsamer `EncoderShadowCore`, aktive/passive Adapter |
| HWT-HOLD/Wiederaufnahme | Absolut 5,0 s einschließlich Cancel/Validierung; 1,0 s gesund, mindestens 20 Rawproben und zwei neue Rawstatusframes; historisch höchstens zwei Versuche, explizites Entwicklungsprofil höchstens zwei HOLDs/60 s | `Hwt601FusionHealth`; Frischeprüfungen bleiben während HOLD gleich |
| Gate | Nominal 20-Hz-Entscheidung; Command 0,25 s, Missionstatus/Not-Aus 1,0 s; Erkundung Karte 5,0 s, notwendige Sensoren und Odometrie 0,8 s; zusätzlich strengere echte HWT-/Wheelquelle | `cmd_vel_mission_gate.py` |
| Gate-TF | `map`-Relation höchstens 0,8 s, Basisrelation höchstens 0,2 s; Zukunft/ungültige Stempel sperren | `transform_motion_authorized`, reale TF-Abfrage im Gate |
| Explorer | Rohkarte/Status/Costmap jeweils 5,0 s, auch ROS-Quellstempel; Pose/Map-Odom-Anker 0,8 s, Lidar 0,5 s; Betriebssnapshot zusätzlich Encoderstatus/Feedbackalter 0,8 s und tatsächlicher Guardvertrag | `metric_frontier_runtime.py`, `explore_node.py`, `explore_params.yaml` |
| Explorer-Kind | Bestehende absolute Ziel-/Gesamtbudgets gelten über HOLD; Cancel 3,0 s; bestätigter Stillstand vor Wiederanlauf erforderlich | bestehender Einzelkind-/HOLD-/Cancelpfad; keine neue Goalinstanz für abgelaufene Arbeit |

Grenzen werden pro Entscheidung gemeinsam ausgewertet. Beispielsweise bleibt
ein Encoder im Timingprofil nach 0,18 s ungültig, obwohl der allgemeine Gate-
Odometriepfad 0,8 s zuließe. Fristen verschiedener Stufen werden nicht addiert.
Statische TF-Annahmen und Stempel-null-Karten anderer Modi werden durch AP-02
nicht zu gültigen dynamischen metrischen Quellen umgedeutet.

## Aktiv und passiv getrennt

Passiver Guard: Depth-one für aktuelle Raw/Yaw-Daten (Best Effort) und Wheel
(Reliable), bestehende unabhängige Callbackgruppen und nichtblockierender DDS-
`take` vor der Gateentscheidung. Er benötigt echte Empfangs-/Messungsfrische;
eine wartende neuere Probe kann gelesen werden, eine verlorene Quelle bleibt
verloren. Reale DDS-Gegenfälle laufen gerätefrei mit isoliertem ROS-Domain.

Aktiver Guard im bisherigen Standard: bestehende Sensor-QoS und serielle
Quellengruppe bleiben erhalten. Metrischer Explorer und ausdrücklich für
Erkundung freigegebenes Fahrtor wählen für Wheel eine eigene Callbackgruppe
und Best-Effort-Depth-one. Vor der Entscheidung dürfen sie dieselbe tatsächliche
DDS-Subscription nichtblockierend lesen. Ursprünglicher Messstempel, Inhalt und
Messungs-/Empfangsalter bleiben maßgeblich; kein Restamping, Warten oder
Ersatzpublisher. Fehlende, alte und ungültige Messungen sperren weiterhin.
Der aktive Basisowner liest echte Encoderpaare und steuert den vorhandenen
Stopppfad. Diese Umgebung startet diesen Owner nicht an einem Gerät.

Tor und Explorer sind unabhängige Beobachter. Ein frischer torseitiger HOLD
oder `awaiting_explore_resume` löst auch bei gesundem Explorer den bestehenden
HOLD-/Kindcancelpfad aus. Wiederaufnahme verlangt innerhalb des ursprünglichen
5-s-Deckels gesunde Quellen beider Beobachter, bestätigten Stillstand, einen
aktuellen Wegbeweis und die vorhandene Sequenzbestätigung des Tors. Ein
torseitiger Terminalfehler oder verlorener Status gibt keine Fahrt frei.

Für AP-06 vorhandene Diagnosen zusammenführen: HWT-IO-/Clockbrackets und
Empfangsmarken, Encoderpaar-/Einzelreadzeiten, Paarmittel/Skew, Pollstartgap,
Publikations-/Feedbackalter, Guard-`consumer_entry_monotonic_s`, ROS-Lesebracket,
Stempelalter, Callback oder Predecision-`take`, Quellen-/Statusalter sowie erste
verwerfende Gate-/Explorerentscheidung. Dazu tatsächliche gestartete Profile,
Installpräfixe, TF-Stempel und aktive Executorwartezeiten erfassen. AP-02 ergänzt
keinen pauschalen Trace-/Supervisorstack. Aktive Jetson-Worst-Case-Zeit und
Hardwarewirksamkeit sind hier ausdrücklich nicht nachgewiesen.

## Softwaregegenfälle

`test_metric_map_lifecycle.py` nutzt echte Explorer-/Kartenmanager-Methoden,
ROS-Nachrichten und den bestehenden Eltern-/Routenpfad; fehlende Actionpeers
sind klar begrenzte Testdoubles. Es prüft Wachstum, verschobenen Ursprung,
Auflösung/Quaternion, Kontextwechsel/Rückwechsel, Egress-Formschutz, beide
Joinreihenfolgen, Source-Loss/Folgeupdates, Fristverbrauch, verspätete Planer-
und Kindresultate sowie echte Produzentenzähler nach Duplikaten.

Zusätzlich laufen bestehende Clock-/Raw-/Health-/Encoder-, echte DDS-Gate-,
HOLD-/Cancel-/Recovery- und Map-Core/Fingerprintregressionen. Aktuelle Mengen,
Originalbelege und reproduzierbare Aufrufe: [AP-02-Evidenz](evidence/ap02-20261003/README.md).

## AP-06 Gesamtmissionsreparatur, 05.10.2026

Karto produziert beim gepinnten Overlay ein auf der exakten Float32-ROS-
Auflösung festes ganzzahliges Raster. Ursprungsänderung durch Wachstum
verschiebt keine bestehende Zelle um Millimeter. Rohstrahlen werden direkt
auf dieses Raster verarbeitet; keine Karte wird resampelt oder aufgehellt.

Ein neuer ungebundener Karteninhalt stoppt weiterhin das aktive Kind. Erst
dessen tatsächlicher terminaler Zustand und bestätigter Stillstand erlauben
das Warten auf den neuen exakten Join. Nach tatsächlichem Join und unverändertem
Kontext darf dieselbe Aufgabe mit erneutem Originalplan-/Konturbeweis begrenzt
wiederholt werden. Aufgaben-ID, Startzeit, bisherige Beobachtungen und gesamte
Ziel-/Missionsbudgets bleiben erhalten; der Wiederholungszähler steigt. Ein
Kontext-, Quellen- oder Fristfehler ist kein transienter Join. Der bisherige
zweissekündige stationäre Beobachtungsdeckel umfasst bereits die Joinwartezeit.

Der gerätefreie AP-06-Prüfstand führt seine ursprünglichen simulierten Geräte
und physische Welt in einem separaten Python-Prozess aus. Native ROS-Graph-/
Servicearbeit des Prüfleiters kann deren Interpreter nicht mehr blockieren.
FC03-Frames, tatsächliche Messzeitpunkte, Integrationsschritte, Frequenzen und
120-/180-ms-Encodergrenzen bleiben unverändert. Shared Memory enthält nur
passive Oracletelemetrie und die deklarierte Gyro-Fehlerinjektion; keine
Produktquelle erhält Groundtruth oder synthetischen Gesundheitsstatus.
Originaler Basisstatus wird zusätzlich unverändert protokolliert. Lifecycle-
Zustände werden am tatsächlichen Server gelesen; verlorene Antwortpakete
lösen keinen zweiten Zustandswechsel aus. Das bestehende 30-s-Stufenbudget
umfasst die Zustandsabfragen. Keine Jetson-/Hardwarezeitbehauptung.

Bei mindestens vier verfügbaren CPUs reserviert der isolierte Prüfstand eine
CPU für den originalen Geräteprozess und höchstens drei für den übrigen
Graph. Die tatsächliche Affinität und lange Executoraufrufe sind archivierte
Prüfumgebungsdaten; keine Frequenz-/Friständerung und kein Hardwarezeitnachweis.
Ein überlasteter Prüfstand gilt weiterhin als fehlgeschlagen, auch wenn sein
terminaler geometrischer Missionsfehler ansonsten behoben ist.


**05.10.2026 – passiver Gate-Executor:** Nur der bereits parallel laufende
passive Gate-Pfad verwendet begrenzte `spin_once`-Aufrufe und 1 ms CPU-Freigabe,
um bereite Quellen-Callbacks bei belegter Standardgruppe nicht durch
unbegrenztes Ready-Polling zu verdrängen. Aktiver serieller Gate-Pfad unverändert.
Keine neue Health-State-Machine, Quelle, Frische oder Deadline; dieselbe echte
DDS-Subscription, tatsächlicher Nachrichtenstempel, Verbrauchszeit und 180-ms-
Radgrenze bleiben maßgeblich. DDS-Regressionen starten ein echtes Gate und einen
separaten synthetischen Messproduzenten in frischen Prozessen; Prüfentscheidung,
Callbackgruppen, HOLD und Quellenverlust sind Produktfunktionen. Frühere rote
Läufe bleiben erhalten. Dies ist keine Zielsystem-Last- oder Hardwareabnahme.

### Verfall eines gebundenen Eingangs während Geometriebearbeitung

`start_motion_wheel_stale_after_processing` bleibt bei 180 ms ablehnend. Der
Parent darf erst nach terminalem Kind und echtem bestätigtem Halt im bestehenden
2-s-Fenster vollständig frische Eingaben lesen und dieselbe Aufgabe neu planen.
Das nutzt die vorhandenen Tasktries und erhält alle Start-/Gesamtfristen; kein
Stempelreset. Tatsächliches `start_motion_wheel_missing_stale_or_invalid`, HOLD,
Contextwechsel, Cancel und Fristfehler bleiben hart. Dauerhafter Inputverfall
scheitert am bestehenden Fenster; keine Endlosschleife oder Sourceheilung.

### Simulationsquellen: finite Sensorberechnung separat

175 ms Sensorexecutor-CPU im Quellen-Isolationstest blockieren die anderen
Pythonthreads trotz eigenem Quellenprozess. Deshalb rechnet ein eigener
Sensorprozess die unveränderten endlichen Laser-/VL53-/OAK-Rohmodelle. Die
100-Hz-Pflanze und tatsächlichen Originalregisterleser bleiben gemeinsam beim
Bewegungsbesitzer; Sensorworker schreibt keine Register und integriert nichts.
Atomarer Pflanzensnapshot enthält tatsächlichen Erfassungsstempel, den alle
Frames beibehalten. >30 ms alter Pflanzensnapshot erzeugt keine neuen Frames
oder gesunden Heartbeats. Keine echte Jetson-/Sensorlatenz daraus abgeleitet.

## Private virtuelle Zellen und öffentliche Quellenbeweise, 06.10.2026

Eine virtuelle erste Körperzelle ist keine beobachtete Rohfreizelle. Bei tatsächlicher Abfahrt darf ihre Freigabe nur monoton mit dem vollständig überdeckten aktuellen Körper schrumpfen. Öffentliche Suche und öffentliche Native-Abfahrt entziehen sämtliche Roh-Unknown-Privilegien, ohne Raw-Inhalt oder Korrelationsidentität zu ändern. Aktuelle Unknown-Berührung der reservierten Kontur erfordert den ursprünglichen gültigen gekoppelten Egress-Beweis; vollständig beobachteter Körper erhält keine erste Ausnahme. B60 enthält 82 alte private Unknown-Zellen, das Rückziel berührt 44; ein älterer angeblich öffentlicher Starttest enthält 40 aktuelle Unknown-Zellen und ungültige Historie. Diese Fälle sind keine öffentliche Quellenautorität.
