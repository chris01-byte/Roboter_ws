# Parity-Reset: Mehrraum-Fahrpfad

Verglichen wurden der real bestandene Stand `1d91229` und der nach
Remote-Abfrage aktuelle PR-#101-Head `40b5b49`. Der Git-Fetch scheiterte an
einer defekten lokalen Checkpoint-Ref; `git ls-remote` und `gh pr view` gaben
den Head `40b5b49` unabhaengig bestaetigt zurueck.

| Funktion | `1d91229` real bewährt | PR #101 vor Reset | Änderung | Parity nötig |
|---|---|---|---|---|
| Initialscan | 8 × 45°; 0,08 rad/s; 1 s Pause; 280 s Gesamtlimit | kontinuierlich; 0,12 rad/s; 210 s; keine Segmentpause | Segmentierung, Messwerte und Nachbremsmessung wiederhergestellt | ja |
| Scan-Fortschritt | 15 s ohne 0,03 rad; Odometrie bei Lücke sofort Null, höchstens 5 s Erholung | 8 s ohne Fortschritt | gemessene 15-s-Grenze zurück; Odometrie-/Stopp-Gates unverändert | ja |
| Geschwindigkeitskette | Explore → Gate → Smoother → Collision Monitor → Basis; 0,08 rad/s erreichte HWT/Odom | 0,12 rad/s führte im 26.09.-Bag nur zu kurzen 0,015/0,004-Ausgaben und keiner Drehung | nur Explore-Scanprofil geändert | ja |
| Frontier-Auswahl | etablierte Frontier-Rangfolge und Nav2-Ziele | alte Rangfolge vorhanden, aber neue WE-Navigation konnte sie ersetzen | WE-Navigationsopt-in im Parity-Kandidaten wird beim Start abgewiesen | ja |
| Portalwahl | verbundene Tür bei Analyseabstand 0,40 m; optional vor lokalen Frontiers | nur Costmap-getrennte Portale aktiv; Priorisierung entfernt | verbundene Erkennung und explizite Profilpriorität wiederhergestellt | ja |
| Staging | begrenzte Nav2-Vorstufen; Geometrie nach jeder Fahrt neu prüfen | nur eine Staging-Etappe | begrenzte, erneut validierte Nav2-Stagingfolge wiederhergestellt | ja |
| Türübergang | verbundene Tuer über Nav2; getrennte Lücke nur nach frischer Vollbreiten-LiDAR-Prüfung und mit eingefrorener Scanbewegung | LiDAR-Brücke erhalten, verbundene Türerkennung fehlte | beide bewährten Fälle wieder aktiv | ja |
| Nach dem Portal | Nav2-Auslauf bestätigen, danach neue Frontier-Ziele | normale Frontier-Folge vorhanden, aber Begrenzungen für verbundenen Auslauf fehlten | Auslauf-Retry begrenzt wiederhergestellt; Frontier-Erkundung läuft weiter | ja |
| HWT/Odom/Nav2/Sicherheit | HWT601-Gier, Encoder-vx, EKF und bestehende Fahrtore | aktuelle PR-#101-HWT-/VL53-/Cancel-/Shutdown-Korrekturen | aktuelle Treiber, Fusion, Nav2, Footprint, Collision Monitor und Gates unverändert behalten | nein |
| Neue WE-Hierarchie | nicht vorhanden | optional aktive Hierarchie plus Shadow-Komponenten | Shadow darf beobachten; aktive Ziele, Cancel und Fahrt sind im Kandidaten gesperrt | ja |

## Replay-Befund

Der erfolgreiche lokale Bag
`hwt601-office-hall-connected-retest-20260911-190824` wurde ausschließlich
lesend ausgewertet. Er enthält einen abgeschlossenen Initialscan, danach
Frontierziele, einen als verbunden erkannten Türübergang und zwei anschließend
besuchte Frontiers. Der Scan-Topic zeigt wiederholte 0,08-rad/s-Abschnitte mit
Nullkommandos dazwischen. `/cmd_vel_smoothed`, `/cmd_vel`, `/odom`, HWT-
Gierrate und Basisstatus zeigen dazu reale Drehung. Die größte `/map` im Bag
hat 58.280 Zellen bei 0,03-m-Auflösung.

Der lokale Gegenbag vom 26.09.2026 (`stage3-initialscan-20260926T1321`) endet
fail-closed mit `initial_scan_no_progress`: 0 von 3 Fortschrittsbelegen, keine
Frontierziele und kein Nav2-Ziel. Der Rohscan sendete 0,12 rad/s, doch die
aufgezeichnete Smoother-/Monitor-Ausgabe blieb bei kurzen 0,015-/0,004-rad/s-
Impulsen; Encoder-Odometrie und HWT-Gyro blieben praktisch bei null. Das
begründet das Zurücksetzen auf den real gefahrenen 0,08-rad/s-Segmentscan,
nicht eine Änderung an Smoother, Collision Monitor oder Hardware.

## Kandidatenprofil und Grenze

`src/explore/config/hwt601_parity_params.yaml` begrenzt den Lauf auf 900 s,
einen Portalwechsel und sechs Abdeckungsziele. Nach der einen Tür bleibt die
Frontier-Erkundung aktiv. Das Profil aktiviert Regionsgraph/WE-Beobachtung mit
100.000 Zellen harter Rohkartenobergrenze; der neue Navigationspfad bleibt
aus. Wird er dennoch per Override eingeschaltet, startet der Explorer nicht.
Die Standarddatei laesst den Shadow weiterhin deaktiviert.

Der motorlose Vorstart ist bestanden. Beim aktiven Stackstart am 26.09.2026
waren Karte/TF, Sensorik, HWT-Bias, Encoder/EKF, Nav2 und Schutzkette bereit.
Der erste ExploreArea-Aufruf umging den Mission-Manager, sodass das Fahrtor
keine reale Bewegung autorisierte; dieser Versuch war kein Parity-Fahrtest.
Der anschließende, korrekt über den Mission-Manager gestartete Versuch ist im
aktuellen Protokoll festgehalten. Diese Datei erteilt keine Motorfreigabe.

## Erster Direktaufruf am 26.09.2026 — kein Parity-Fahrtest

**Status: PARITY-REALTEST NICHT AUSGEFÜHRT.** Der motorlose Vorstart bleibt
bestanden. Im direkt gestarteten aktiven Stack waren LiDAR, HWT601-Bias,
Encoder/EKF, beide VL53-Frames, TF, Karte, Nav2 und Collision Monitor bereit;
vor Missionsstart meldete die Basis 0 RPM. Karte, Startpose und der begrenzte
Scope (Startraum, ein Portal, ein Ziel im Folgeraum) wurden an die lokale
Aufzeichnung
`~/.local/share/amadeus/tests/parity-real-20260926T143000-run2` gebunden.

Der ExploreArea-Aufruf ging direkt an `/explore_area` und umging dadurch den
vorgesehenen `mission_manager`/Behavior-Tree-Auftragsweg. Das aktive Fahrtor
verlangt einen laufenden Mission-Manager-Auftrag vom Typ `explore`; ohne ihn
blieb es geschlossen. Der Explorer gab auf `/cmd_vel_explore_scan_raw` zwar
293 ungleich-null Rundblickkommandos mit bis zu 0,08 rad/s aus, aber
`/cmd_vel_smoothed`, `/cmd_vel_nav` und `/cmd_vel` blieben null; Encoderpose
und Motoren blieben still. Der Explorer meldete danach
`no_progress; erreicht 0.0 Grad`. Das war kein physischer Fahr-/Türtest und
entwertet den bestandenen Vorstart nicht. Es gab keine Frontier-, Portal- oder
Raumwechselprüfung. Der korrigierte Status lautet **PARITY-REALTEST NICHT
AUSGEFÜHRT**, nicht bestanden oder gescheitert.

Der bekannte STL-27L-Fehler `buffer overflow detected` / Exit `-6` trat nur
nach SIGINT beim Shutdown auf. Danach waren keine Amadeus-Knoten aktiv; FC03-
Lesungen zeigten beide Motoren bei 0 RPM und unveränderte Encoderpositionen.
Dieser Befund ist separat als Cleanup-/Shutdown-Defekt zu führen. Während
dieses Auftrags gab es keinen Neustart und keine Parameter- oder
LiDAR-Änderung.

## Korrekt gestarteter Produktpfad am 26.09.2026

**Status: PARITY REAL GESCHEITERT.** Der unveränderte Kandidat
`40b5b49c9a92600484a0dc85c466930bc1680c60` wurde mit demselben aktiven Stack
gestartet. Nach stabilem HWT601-Startbias und 0 RPM vor Missionsbeginn wurde
genau `{"type":"explore"}` über `/mission_manager/command_json` gesendet.
Der Manager meldete `state=running`, `active_command.type=explore` und
`phase=Explore`; der BT-Orchestrator startete `explore.xml`. Das Fahrtor wechselte
auf `mission`, bevor der erste Rundblickbefehl die Basis erreichte. Die Basis
führte den autonomen 0,08-rad/s-Rundblick aus; Odometrie bestätigte bis zum
Abbruch etwa 2,45 rad Gierbewegung. Es gab keinen manuellen Nav2-Befehl.

**Erster sicherheitsrelevanter Laufzeitfehler:** Das vollständige Knotenlog
meldete zuerst einen `IndexError` auf `ch1` (1790436850,681), danach 21
Warnungen auf `ch0` über 9,42 s ab 1790436858,753, darunter wiederholte
Ranging-Neustarts. Der Fehlertext passt zum `get_ranging_data()`-Pfad des
installierten Treibers; ein Stacktrace zur exakten Zeile liegt nicht vor.
Der alte Code fragte den rechten Kanal weiter ab, aber während der Lücke
fehlt wegen der gepaarten Publikation ein Einzelkanalnachweis. Der
VL53-Treiber meldete wiederholt `ch0: IndexError: list assignment index out of range` und
`Ranging neu starten`. Daraufhin verwarf der Collision Monitor beide Quellen
`vl53_left` und `vl53_right` als veraltet (Zeitstempelabweichung über 3 s).
Wegen des Ausfalls der Nahbereichs-Schutzdaten wurde der Auftrag über den
Mission-Manager abgebrochen. Der Initialscan blieb unvollständig; es gab kein
Frontierziel, keine Tür-/Portalwahl und keinen Raumwechsel. Missionmanager,
BT und Fahrtor arbeiteten korrekt; der Fehler lag am VL53-Datenpfad während
des aktiven Laufs.

Das lokale Bag liegt unter
`~/.local/share/amadeus/tests/parity-real-20260926T153200Z-product`. Nach dem
kontrollierten Mission-Manager-Abbruch standen die Motoren bei 0 RPM; FC03
bestätigte stabile Encoderpositionen. Der STL-27L-`buffer overflow detected`-
Fehler / Exit `-6` trat separat erst nach SIGINT auf. Keine Software- oder
Parameteränderung wurde vorgenommen.

## VL53-Runtime-Recovery und erneuter Realtest am 27.09.2026

Im isolierten Parity-Kandidaten erhielt nur `vl53_near_field` eine begrenzte
Recovery je Kanal: einzelne Fehlprobe verwerfen, nach drei Fehlern einmal
Ranging neu starten, bei erneutem Fehler höchstens zweimal ein neues
Treiberobjekt für den betroffenen Mux-Kanal initialisieren. Erst zwei
vollständige Rohframes beenden einen Recovery-Zustand. Bis dahin werden keine
alten Status- oder Cloud-Daten als frisch publiziert; nach erneutem Fehler
bleibt die betroffene Quelle endgültig gesperrt. Read-Fehler, gesunde Frames,
Ranging-Neustarts, Reinitialisierungen, erfolgreiche Recovery und Endfehler
werden kanalgetrennt gezählt und bei Recovery/Endfehler geloggt. Der gesunde
Kanal wird intern weiter gelesen; die Bewegungsfreigabe verlangt weiterhin
das vollständige Paar. Sicherheitsfristen und andere Fahrkomponenten blieben
unverändert. Die 989 VL53-, Navigations- und Explorer-Tests bestanden.

Der motorlose Echtlauf lieferte in 125,1 s 508 gepaarte Statusmeldungen,
alle mit beiden Frames gesund; beide Sensorwolken hatten höchstens 0,28 s
Abstand. Danach startete der freigegebene aktive Stack einmalig mit dem
unveränderten Parity-Profil. Vor Missionsbeginn waren LiDAR, HWT/Encoder/EKF,
VL53, Karte/TF und Nav2 frisch, beide Motoren bei 0 RPM. Der Auftrag lief
über `/mission_manager/command_json` mit `{"type":"explore"}`; Manager,
BT und Fahrtor nahmen ihn an. Der autonome Initialscan erreichte 361,7°.

**Ergebnis: PARITY REAL GESCHEITERT.** Die erste Sperre trat um
1790492567,566 auf: `/fusion/hwt601/status_json` wechselte von
`raw_sources_ready` auf den verriegelten Fehler `raw_driver_not_ready`, und
das Fahrtor wechselte sofort auf `blocked`. Welche konkrete Bedingung im
HWT-Rohstatus ausfiel, ist nicht aufgezeichnet; hierzu wird keine Ursache
behauptet. Der Explorer schloss den Rundblick noch ab, verwarf dann drei
Frontier-Vorausrichtungen (`too_slow`, zweimal `no_progress`) und endete mit
`Zu viele nicht ausrichtbare Erkundungsziele`. Es gab kein angefahrenes
Frontierziel, keinen Portaldurchgang und keinen Raumwechsel. LiDAR und beide
VL53 publizierten weiter: im Bag maximal 0,20 s LiDAR- und 0,35 s
VL53-Statuslücke, kein neuer VL53-IndexError im Knotenlog. Der Stack wurde
im Stillstand sauber beendet. Der bekannte STL-27L-Overflow erschien erst
beim SIGINT-Shutdown und bleibt separat. Bag:
`~/.local/share/amadeus/tests/parity-real-20260927-vl53-recovery`.

Keine HWT-, Nav2-, Explorer-, Gate- oder Sicherheitsparameter wurden geändert.
Rückfall der VL53-Software: nur die beiden Änderungen unter
`src/vl53_near_field/` im isolierten Parity-Branch zurücknehmen und das
Paket neu bauen. Vor einem weiteren Realtest ist der HWT-Rohstatusfehler
getrennt zu klären; dieser Lauf wird nicht als Parity-Nachweis gewertet.

## Software-Nachweis und Rückfall

Auf dem isolierten PR-#101-Head wurden `explore` gebaut und 925 Tests bestanden.
Die ausgewählten Regressionen für `base_hardware` (103),
`robot_state_estimation` (99), `amadeus_lidar_bringup` (7),
`robot_navigation` (46) sowie direkte VL53-/`safety_monitor`-Tests (17)
bestanden ebenfalls: insgesamt 1.197 gezählte Tests. Gezielte Builds der
betroffenen Pakete gelangen. Ein zusätzlicher Build bis `robot_bringup` blieb
an fehlender `behaviortree_ros2`-CMake-Konfiguration in der lokalen Umgebung
stehen; das ist kein bestandener Buildnachweis für diesen Launchpfad.

Der Rückfall ist ein Wechsel auf den bisherigen PR-#101-Head
`40b5b49c9a92600484a0dc85c466930bc1680c60`; der real bewährte Referenzcommit
`1d91229` ist Vergleichsgrundlage, aber wegen späterer Sensor-/Sicherheitsfixes
nicht als vollständiger Rollback vorgesehen. Änderungen dieses Kandidaten
bleiben auf `feature/parity-reset` in der isolierten Arbeitskopie. Kein Commit,
Merge oder Hardwarelauf wurde ausgeführt.
