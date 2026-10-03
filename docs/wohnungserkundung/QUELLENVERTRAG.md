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
| Rohkarte/Status noch nicht passend | Neue Aufgaben warten. Aktive Arbeit darf höchstens im bisherigen 1,25-s-Fenster den letzten **exakten** Join nutzen, wenn beide aktuellen Inhalte identisch zu ihm sind; dessen ursprüngliche Zeitstempel/Fristen bleiben maßgeblich |
| Neue Zellen oder Geometrie ohne passenden Status | Kein aktiver Ersatzjoin mit alter Revision; notwendige Quelle fehlt, laufendes Kind stoppen |
| Rasterwachstum, Ursprungs-/Quaternion-/Frame-/Auflösungswechsel | Alte Egress-Evidenz bereits beim Callback vor jeder Arrayverknüpfung dauerhaft invalidieren; bei Rohkartenwechsel auch vorhandenen Body-Anker invalidieren |
| Frame-/Auflösungswechsel eines Rasters | Arbeitsgeneration erhöhen; auch ein zwischen zwei Auswertungen beobachteter Wechsel und Rückwechsel macht alte Arbeit ungültig |
| Neuer Session-/Mapkontext, Zähler-/Zeitreset oder verschwundener initialisierter Kartenstatus | Bestehender Adapter verweigert implizite Neubindung; Explorerfehler bleibt hart, Kind stoppen, alte Plan-/Erfolgsresultate unwirksam. Neuer Kontext erfordert ausdrücklich neue Sitzung und passende Scope-Bindung |
| Verspätete ältere Rohkarte/Costmap/Status | Nicht überschreiben, kein neuer Empfangszeitpunkt; Produzent verwirft ältere positive Quellstempel ohne neue Revision/Frische |
| Widersprüchliche Inhalte bei gleichem positivem Stempel | Kartenmanager verwirft; metrischer Verbraucher sperrt hart. Kein Reihenfolge-Raten |

Normales Wachstum invalidiert räumliche **Ausnahmen**, nicht automatisch ein
noch gültiges Weltziel. Ohne die alte Ausnahme muss die vollständige bestehende
Routen-/Konturprüfung weiterhin bestehen. Unbekannte neue Zellen bleiben
unbekannt; kein Re-Ankern, keine verschobene Maske und keine freie Startschneise.
Der direkte `StartEgressEvidence.check_trajectory` schützt zusätzlich gegen
inkompatible Arrayformen. Bestehende monoton schrumpfende Inventare bleiben
bei passenden Geometrien erhalten; beobachtete Zellen werden nicht erneut exempt.

Rohkarte, Status, Costmap und Evidenzmutation werden unter dem vorhandenen
metrischen `RLock` zusammen ausgewertet. Kein Service/Action-Warten unter diesem
Lock. Die Auswertung prüft Frische erneut nach der Verarbeitung. HWT-/Gate-
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

Aktiver Guard: bestehende Sensor-QoS und serielle Quellengruppe bleiben erhalten;
kein Übertragen des passiven DDS-/Callbacknachweises auf aktive Vollstacklast.
Der aktive Basisowner liest echte Encoderpaare und steuert den vorhandenen
Stopppfad. Diese Umgebung startet diesen Owner nicht an einem Gerät.

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
