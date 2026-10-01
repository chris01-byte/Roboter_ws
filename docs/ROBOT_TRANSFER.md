# Übertragung auf den realen Roboter

## 30.09.2026 – metrischer Realnachweis: lesender Vorlauf blockiert

Exakter Softwarekandidat `deb075e3f1a51a46bc00c2235a3068cfbe45d769`,
Branch `feature/hwt-hold-recovery-resume` / PR #105, LAB-1. Reale Domain 42.
Isoliertes Sechspaketpräfix `metric-frontier-20260930/software-final/install`
über vorhandener Runtime-Kette/Vollunderlay `hwt-child-scope-20260928-retry/install`;
LD-LiDAR-Shutdownoverlay und vorhandener SLAM-Toolbox-Install aufgelöst.
Tatsächliche Prozess-/Profil-/Modulhashes im privaten Runtime-Manifest.
`~/roboter_ws` bleibt auf `23928d9`, kein dauerhafter Installwechsel/Merge.

Passiver regulärer `app_mapping`-Start: `active_drive=false`, HWT-Odometrie,
`enable_auto_explore=false`; kein Aktorschreibprozess. Anfänglich ungebundener
Explorer erwartungsgemäß fail-closed; anschließend reale Karte/Pose und
LAB-1-Scope lokal gebunden und alleiniger Explorer über bestehenden Overlay-
Launch gestartet. Parameter und 324 Statusmeldungen: `metric_frontier`,
alte WE-Policy/Navigation false. Keine Pflicht-Portale/Regionen.

Erster Quellenblocker: Radsample 189,166 ms > passive 180-ms-Grenze.
Einmaliger passiver Gate-Neustart nach Quellenstart; kurze Rohquellen-HOLD/
Recovery separat. Später Encoderreader terminal: FC03-Paar 125,870 ms >
120 ms, Einzelreads 91,760/33,809 ms. Keine Grenze gelockert; konkrete
zeitliche Ursache nicht bewiesen, kein Hardwaredefekt behauptet.
Unabhängiger Geometriesnapshot: Startzelle unbekannt, volle gepaddete Kontur
in Rohkarte/Costmap unzulässig; Scan bereits erste Orientierung ungültig.
25 Frontiercluster, 25 `no_known_free_route`, kein zulässiger Kandidat.

Kein aktiver Wechsel und keine Mission/Fahrt; Realnachweis damit nicht
erreicht. A/C nicht bestanden, B nicht aufgetreten, Stufe 3 weiterhin offen.
Grenzen im Liveprofil 900 s/150 s/6 Versuche/3 Fehler, Scan 280 s/0,08 rad/s;
keine Mission begann diese Budgets. Keine direkten Explore-/Nav2-Ziele.

Recorder bis zum geordneten Ende aktiv; Datenbank erst nach Recorderende
analysiert. Keine running-Mission/kein Nav2-Statuseintrag; alle erfassten
Ausgangsbefehle null. Einzelne Launchwurzeln SIGINT, keine Prozessgruppe.
Alle manifestierten Prozesse beendet, ttyUSB-Handles frei, keine Shutdown-
fehler im Abschlusslog. Zwölf frische FC03-Paare nach Stackende: unveränderte
Motorpositionen, 0 rpm. Keine elektrische Sperrstellung behauptet.

Private Belege `~/.local/share/amadeus/tests/metric-frontier-real-20260930/`:
`REPORT.md`, Manifest, Liveparameter/-status, Rohkarten-/Costmapsnapshot,
Konturdarstellung, geschlossene Bag-Auswertung, FC03-Start/Endmessungen und
Shutdownprüfung. Nur datensparsame Dokumentation veröffentlicht.
Rückfall bereits wirksam: gestartete Prozesse beendet, keine Mission,
permanenter Install unverändert. MASTERPLAN v1.2 unverändert.
Genau nächster Schritt steht im STATUS: gezielter Vorlauf-Korrekturauftrag
für Startkarten-/Kontur- und FC03-Paarzeitblocker mit getrennten Nachweisen,
keine automatische neue Fahrt.

## 30.09.2026 – metrischer Softwarekandidat, keine Roboterübertragung

Separater Checkout: `/home/p/roboter_worktrees/metric-exploration-20260930`,
Basis `1dbbdaacc18550f1c1912a9a36a765bda397b19f`, vereinbarter Branch
`feature/hwt-hold-recovery-resume` / PR #105. Die laufende Arbeitskopie
`~/roboter_ws` bleibt auf ihrem bisherigen Stand; kein dauerhafter Install,
kein Merge, keine Hardware-/Sensorprozesse und keine reale Fahrt.

Sechs Pakete gerätefrei gebaut unter
`~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/install`:
explore, robot_navigation, robot_state_estimation, mission_manager,
robot_map_manager, amadeus_map_identity. Source-Reihenfolge der Tests:
ROS Humble → `hwt-child-scope-20260928-retry/install` → Kandidatenpräfix.
BT stammt weiterhin aus dem Vollunderlay, kein neuer BT-Stack. Paketpfade
stehen in jedem Graphlog; diese Auflösung ist ein lokaler Softwarebeleg,
kein Jetson-Laufmanifest. Nach Umgebungsneustart verloren gegangene `/tmp`-
Zwischenbuilds nicht als verwendbaren Install voraussetzen.

Neuer Modus ausschließlich `exploration_strategy=metric_frontier` mit
`src/explore/config/metric_frontier_params.yaml`, nach dem Basisprofil und
vor Missionstart. Ausgeliefertes Overlay ist nicht fahrfertig: aktuelle
Session, gemessener Startkarten-Fingerprint und explizit verifiziertes
Scopepolygon fehlen absichtlich. Default bleibt `existing`. Metrischer
Modus hat denselben Nav2-Client/Gate; keine Pflicht-Portal-/Regionsdaten.
Keine Geschwindigkeits-, Hardware-, Sensorframe-, EKF- oder Collision-
Monitor-Konfiguration geändert. Bei bewusstem späterem Einsatz können
mehrere normale Nav2-Aufgaben aus aktuellen Rastern folgen; physische
Wirkung daher erst nach realem technischen Vorlauf bewerten.

Gerätefrei: 1.342 pytest-Regressionen, registrierte colcon-Tests und verbundene
synthetische Produktfälle laut STATUS §4. localhost/Domain 224 bzw. 226,
keine konfigurierten DDS-Peers und kein Gerätebus. Reale Domain 42 hat keine
Testpublisher erhalten. Ergebnisse/Karten/Bags bleiben lokal außerhalb Git.

Rückfall: Overlay nicht laden und ohne Mission geordnet `existing` starten;
Betriebsrückfall `active_drive=false`, `enable_auto_explore=false`. Ein
nicht nachgewiesen terminales Nav2-Kind sperrt auch neue Elternaufträge;
bei unklarem Cancel kein Neustart zur ungeprüften Wiederanfahrt.
Genau ein begrenzter Realnachweis ist in AGENTENAUFTRAG §7 vorbereitet,
noch nicht ausgeführt. Stufe 3 und reale Durchfahrt bleiben offen.


## 29.09.2026 – isolierter HOLD-Auftragserhalt-Kandidat

Der aktive Produktlauf mit `08127c8` ist nach terminalem Recoveryabbruch
geordnet beendet. Neues Explore-Paket separat unter
`~/.local/share/amadeus/tests/stage3-core-20260929/hold-task-install`, nach
`idle-gate-install` (Navigation) und `hwt-callback-order-install` (HWT) sourcen.
Der Vollunderlay bleibt `hwt-child-scope-20260928-retry/install`. Kein
dauerhafter Installwechsel. Gerätefreier Graph läuft ausschließlich localhost
in Domain 200–230; reale Domain 42 übernimmt keine Testpublisher.
Real aufgelöst und bytegleich geprüft im lokalen Lauf
`stage3-core-20260929/autonomous-goal-after-hold-task-fix/`: aktiver Start,
vollständiger Scan, sieben autonome Kinder, aber keine abgeschlossene Aufgabe.
Nach 459,860 s kontrolliert beendet; alle Roboterprozesse und seriellen Handles
frei. Kein HWT-first_fault, neuer Kartenquellennachweis-Blocker. Einzelwerte,
Grenzen und genau nächster Auftrag ausschließlich im STATUS §7.


## 28.09.2026 – gezielte Portal-/Explorer-Reparatur, noch keine neue Fahrt

Explore und robot_state_estimation wurden unter
`~/.local/share/amadeus/tests/hwt-portal-repair-20260928/install` isoliert gebaut.
Underlay bleibt der vollständige `hwt-child-scope-20260928-retry/install` mit
den dokumentierten SLAM-/LiDAR-Overlays. Aktiver Install und Hauptarbeitskopie
bleiben unverändert. Das neue lokale No-Scan-Profil aktiviert den erforderlichen
Portalfeed; Portalquerung, Initialscan, Coverage und Rückkehr bleiben aus.
Vor Ort wurden Motorsperre, Stillstand und FC03-Erreichbarkeit ausdrücklich
bestätigt; damit ist die unten noch historisch offene Sperrenrückmeldung geklärt.
Die reale Karten-/Scopebindung muss im motorlosen Vorlauf neu gemessen werden.
Aktueller verbindlicher Nachweisstand: STATUS Abschnitt 7.

Der anschließende passive Start auf `e5b221b` ist beendet: Quellen, Karte/TF,
VL53 und Stillstand waren gültig. Die echte Policy lieferte autonome Ziele,
aber alle beobachteten Routen überschritten 0,45 m (Minimum 0,959117 m).
Daher kein aktiver Start und keine Mission/Injektion. Neues Scope lokal aus
Live-Pose erzeugt und dokumentiert, noch nicht als neues Laufprofil geladen.
28/28 Launch-Kinder sauber beendet, Recorder beendet und Ports frei. Lokale
Belege: `hwt-portal-repair-20260928/result.json`, Runtime-Manifest, Bag und
Scopebindung. Nach Shutdown Bindung nicht mehr live; aktiver Install unverändert.


## HWT-Kindziel, aktiver Einzelversuch ohne Ziel — 28.09.2026

Der unveränderte PR-#105-Build unter
`~/.local/share/amadeus/tests/hwt-child-scope-20260928-retry/install`
wurde über `app_mapping.launch.py` mit `active_drive=true`,
`use_hwt601_odometry=true`, `enable_auto_explore=true` und dem lokalen
Einmalprofil ohne Initialscan (SHA256 `a5e6b1d0…`) gestartet. Das lokale
`runtime-manifest-active-v2.json` unter
`~/.local/share/amadeus/tests/hwt-child-active-20260928-once/` hält die
aufgelösten Paketpfade fest; ein dauerhafter Installwechsel fand nicht statt.
Nach SLAM-Neustart wurde Scope-ID `we1-hwt-child-noscan-20260928-once` an
die neue Live-Karte `fb26a819…` und die Startpose gebunden (maximal
0,0009 m Eckenversatz). Bei stillstehender Basis waren HWT-Fusion,
Encoderfeedback und Sicherheitsstatus gesund. `base_hardware` besaß
`/dev/ttyUSB_BASE` allein, der HWT-Leser `/dev/ttyUSB_HWT601` allein;
kein paralleler Encoderleser. Die Vor-Ort-Bestätigung bezog sich auf den
kontrolliert gelösten unabhängigen Motorhalt, anwesenden Beobachter und
weiterhin freien Korridor.

Recorder und 340-s-Cancel-Wächter liefen vor dem einzigen Explore-Auftrag
über Mission Manager → BT → Explorer. In 247,97 s erzeugte der aktive
Produktpfad kein Kindziel: 249/249 Statusbilder meldeten
`stale_source:portal_memory`, kein Zielkandidat, keine Nav2-UUID und
kein Plan. Der Explorer endete vor der 300-s-Suchgrenze unerwartet mit
`hwt601_raw_missing_stale_or_invalid`. Es gab keine geplante HWT-Pause,
keinen HOLD und keine Nichtnull-Fahrkommandos; `/odom` maß 0,000 m Weg.
Der exakte Explorer-interne Erstwert ist nicht belegt; der getrennte
Fusion-Wächter blieb um den Abbruch gesund. Der Recorder erfasste
`/near_field/status` wegen fehlendem `robot_interfaces`-Overlay nicht.
Stack und Bag sind sauber beendet, 28/28 Launch-Kinder beendet, Ports frei.
Vor-Ort-Rückmeldung zur nach dem Lauf wieder wirksamen Motorsperre steht
noch aus. Kein zweiter Versuch, keine Produktänderung und keine
Kindziel-Recovery-Abnahme aus diesem Lauf.

## HWT-Kindziel ohne erneuten Initialscan — motorlos nicht ausgelöst (28.09.2026)

Das lokale Einmalprofil `hwt-child-no-initial-scan.yaml` unter
`~/.local/share/amadeus/tests/hwt-child-noscan-20260928/` hat SHA256
`a5e6b1d08041b3f63bb1fcd2b7730b709194fbe210426770f1ff759d2e70dcd6`.
Es schaltet nur den bereits real bestandenen Initialscan aus, hält
WE-Navigation an und begrenzt den Versuch auf ein Frontier-/Fehlziel ohne
Portalquerung, Coverage oder Rückkehr. Produktcode und aktiver Install
blieben unangetastet. Der korrigierte motorlose Start verwendete dieses
Profil tatsächlich; FC03, HWT/Yaw, Karte/TF und VL53-Frames waren gesund.
Der echte Mission-Manager-/BT-Auftrag scheiterte vor Kindziel-Dispatch an
`hwt601_readonly_preflight_no_motion` (`active_drive=false`). 20 offene,
zuletzt 5 geeignete Frontier-Aufgaben sind kein Nav2-Kind; Action-Status
und -Feedback blieben leer. Kein Fahrkommando, keine Fahrt und keine
HWT-Pause. Lokale Bag-/Statusnachweise unter demselben Testverzeichnis.
Recorder und Stack sind beendet, 28/28 Kinder im zweiten Start sauber,
Ports frei. Eine künftige Fahrt ist aus diesem Read-only-Ergebnis nicht
freigegeben; die Reihenfolge zur Beobachtung eines echten Kindes muss
ausdrücklich geklärt werden, ohne die Schutzsperre zu umgehen.

## HWT-Kindziel-Abnahme — zweiter motorloser Vorlauf, keine Fahrt (28.09.2026)

Der Nutzer bestätigte nach dem ersten fehlgeschlagenen Vorlauf nun eine
FC03-erreichbare Controllerelektronik bei weiterhin unabhängig gesperrter
Motorendstufe, Stillstand und Beobachtung vor Ort. Der funktional unveränderte
PR-#105-Stand wurde isoliert unter
`~/.local/share/amadeus/tests/hwt-child-scope-20260928-retry/install`
neu gebaut und über das lokale `runtime-manifest-passive.json` aufgelöst.
`app_mapping.launch.py` lief ausschließlich mit `active_drive=false`,
`enable_auto_explore=false`; kein Motorprozess, keine Mission und kein
Fahrkommando. FC03-Paare trafen ohne Latch ein, HWT-Roh-/Yaw und Fusion-
Quellen waren gesund, Karte/TF frisch. Das neue lokale Einmal-Scope samt
Fingerprint, Startpose, Polygon und Profilhash liegt nur im Testverzeichnis;
das historische Scope wurde nicht verwendet. Eine motorlose Nav2-
Planungsprobe blieb im Polygon, überschritt mit 0,494 m aber die für den
späteren Test festgelegte 0,45-m-Routenobergrenze und ist kein autonomes
Frontier-Kind. Der nötige rückwärtige Schwenkraum für den 360°-Initialscan
ist vor Ort noch nicht bestätigt. Daher keine Fahrt oder HWT-Injektion.
Der passive Stack endete mit 28/28 sauberen Kindern und freien Ports.
Der aktive Install blieb unverändert; das Profil aus der beendeten
SLAM-Session darf ohne erneute Kartenbindung nicht gefahren werden.

## HWT-Roh-/Yaw-Recovery — ein begrenzter neuer Real-Teilnachweis

Am 27.09.2026 wurde der PR-#105-Stand `6b666d97d7e11326c9f75dccbc4253112e99b578`
einmal im ausdrücklich freigegebenen 40-s-/3-rad-Initialscan geprüft.
Das Manifest unter
`~/.local/share/amadeus/tests/hwt-recovery-real-20260927-fxU0To/`
belegt das unveränderte Abnahmeprofil `hwt601_recovery_acceptance_params.yaml`
(SHA256 `ee3b42eef682a830892e93f84093baf1547a84f76d6baa3e480a81dc1de393c4`),
die Overlay-Reihenfolge und `robot_state_estimation` aus
`/tmp/we1-hwt-yaw-install`. Schattennode, Core und Health sind bytegleich
mit den Quellen. Der aktive Install wurde nicht gewechselt.

Nach bestandenem motorlosem Preflight lief der Recorder vor dem aktiven
Stack. Eine einmalige 0,251-s-Leserpause erzeugte 0,260533 s Rohdatenlücke.
Gate-HOLD sperrte die Fahrt; das Encoderfeedback meldete während HOLD
0/0 gemessene Motor-RPM. Der eingefrorene Bias blieb unverändert, frische
Yaw-Daten kehrten zurück, Health/Gate bestätigten Sequenz 1, und derselbe
Explore-Auftrag setzte den Rundblick fort. Der Controller cancelte nach
14,928 s und 0,136 rad; es gab keine Translation und kein Nav2-Kindziel.
Stack und Recorder wurden geordnet beendet; HWT- und Motorport sind frei.
Bag, Zeitfolge und Analyse liegen ausschließlich lokal. Die anwesende Person
bestätigte am 28.09.2026 für **diesen neuen Versuch** nachträglich den
tatsächlichen physischen Halt beim HOLD, Stillstand nach Cancel und die
danach wieder wirksame unabhängige Motorsperre. Damit ist der begrenzte
Rundblick-Umfang real bestanden; es wurde kein zweiter Versuch gefahren.
Ein aktives Nav2-Kindziel, eine Zielroute, Tür- oder Frontier-Recovery waren
nicht Gegenstand dieses Laufs. Keine neue Fahrt aus diesem Befund;
Stufe 3 bleibt offen.

## HWT-Roh-/Yaw-Korrektur — ausschließlich isolierter Softwarestand

Auf demselben PR-#105-Branch wurde nur `robot_state_estimation` für die
reine postkalibrierte Rohdatenlücke geändert und isoliert unter
`/tmp/we1-hwt-yaw-install` über dem bisherigen Recovery-Overlay gebaut.
Das installierte Abnahmeprofil bleibt SHA256 `ee3b42eef…`. Der
gerätefreie Produktgraph verwendete den echten Yaw-Schatten und bestand
mit 0,260675 s gemessener Rohdatenlücke; Bias unverändert, HOLD und
Fortsetzung nach Stillstands-/Pose-/Wegprüfung und Gate-ACK. Keine
produktive Roboter-Runtime, kein Gerät oder Aktor wurde dafür gestartet;
der aktive Install blieb unverändert. Details und Gegenfälle stehen in
STATUS Abschnitt 5.

Für einen später gesondert freizugebenden Einzeltest die Setup-Kette
`/opt/ros/humble`, `amadeus_slam_toolbox_ws`,
`we1-ldlidar-shutdown-overlay`, `we1-full-shim-install`,
`we1-hwt-recovery-install` und **danach**
`/tmp/we1-hwt-yaw-install` in einem frischen Prozess auflösen und mit dem
Runtime-Manifest tatsächlich nachweisen. Der aktuelle Roboter-Install
enthält diese Änderung nicht. Rückfall bleibt der gesicherte
PR-#104-Latchkandidat. Der nächste Schritt ist nur die begrenzte
Realtestvorlage in AGENTENAUFTRAG Abschnitt 5; keine Fahrt aus dieser
Übergabe.

## HWT-Recovery-Realversuch — HOLD ja, RESUME nein

Am 27.09.2026 lief genau ein von der anwesenden Person freigegebener,
begrenzter Initialscan auf dem isolierten Recovery-Overlay (Quell-HEAD
`25ac0481ad8c79ffcaa34d22ee4082fa5d39a45b`, PR #105). Der Recorder
startete vor dem Stack. Runtime-Manifest, Bag und Logs bleiben lokal unter
`~/.local/share/amadeus/tests/hwt-recovery-real-20260927-3wLELq/`.
Profil, Hash und Underlay-Reihenfolge entsprechen dem folgenden motorlosen
Abschnitt; `active_drive=true`, `enable_auto_explore=true`,
`use_hwt601_odometry=true`. Der Motorbus hatte nur `base_hardware` als
Besitzer, der HWT-Port nur den HWT-Leser. Der aktive Install blieb unverändert.

Eine einmalige 0,251-s-Pause des HWT-Lesers löste eine 0,261-s-Rohdatenlücke
aus. Das Gate erkannte `raw_missing_stale_or_invalid` bei 0,220622 s
Rohmessalter gegen 0,20 s, sperrte die Bewegung und der Explore-Auftrag
blieb zunächst im HOLD. Der Yaw-Schatten verriegelte dieselbe Lücke wegen
seiner bestehenden 0,10-s-Grenze als `imu_datenluecke_neustart_noetig`;
danach folgte `yaw_missing_stale_or_invalid` als terminaler Fusion-Fehler.
**Kein RESUME:** Der Testcontroller cancelte die Mission; das frische
Encoderfeedback meldete danach 0/0 Motor-RPM. Die gemessene Drehung war
höchstens 0,081 rad, ohne Translation. Die separate Bestätigung des
Beobachters über physischen Halt und wieder wirksame Motorsperre wurde
inzwischen für **diesen früheren** Versuch erteilt. Der Stack und Recorder
sind aus, HWT-/Motorports frei. Beim
SIGINT-Shutdown starb `slam_toolbox` mit Exit -6; kein Zusammenhang mit
dem HWT-Fehler ist belegt. Keine Wiederholung und keine Fahrfreigabe.

Rückfall: Das damals gefahrene Recovery-Overlay nicht als bestanden
übernehmen; der gesicherte PR-#104-Kandidat behält den fail-closed
Latch. Die spätere gerätefreie Korrektur steht oben und ersetzt keinen
zweiten Realnachweis.

## HWT-HOLD-/Recovery-Branch — motorloser Zielsystemcheck

`feature/hwt-hold-recovery-resume` baut die vier Pakete
`robot_state_estimation`, `robot_navigation`, `explore` und `mission_manager`
isoliert in `/tmp/we1-hwt-recovery-install` über
`/tmp/we1-full-shim-install`. Der aktive Roboter-Install und der
PR-#104-Kandidat blieben unberührt. Am 27.09.2026 wurde dieser Kandidat nach
aktueller motorloser Bestätigung **mit echten Sensoren, ohne Motoren und ohne
Mission** gestartet: HWT-Bias/Rohdaten/Gierrate, read-only Encoder, LiDAR,
VL53, TF und Gate-Nullausgabe wurden geprüft. Der erste Launch brach vor
Knotenstart ab, weil der externe LiDAR-Underlay fehlte. Für den erfolgreichen
Lauf wurden `/opt/ros/humble`,
`/home/p/amadeus_slam_toolbox_ws/install`,
`/home/p/.local/share/amadeus/releases/we1-ldlidar-shutdown-overlay/install`,
`/tmp/we1-full-shim-install` und `/tmp/we1-hwt-recovery-install` in dieser
Reihenfolge gesourct. Das installierte Abnahmeprofil hatte SHA256
`ee3b42eef682a830892e93f84093baf1547a84f76d6baa3e480a81dc1de393c4`.
Der motorlose Stack ist sauber beendet, HWT-/Motorports sind frei. Lokale
Manifeste und Beobachtungen liegen unter
`~/.local/share/amadeus/tests/hwt-recovery-real-20260927-3wLELq/`.
Dieser motorlose Teilnachweis erteilte keine Fahrfreigabe; der später
gesondert freigegebene begrenzte Realversuch steht oben.


## HWT-TOR-1-Diagnosekandidat — vollständiger motorloser Lauf

Auf der Integrationslinie PR #103 enthält `f1f6b74a5e5aea1ba43c50beb75f5f954218fb78`
die additive Erstfehlerdiagnose. Sie wurde nur in
`/tmp/we1-hwt-f1f6b74-install` gebaut, mit dem gesicherten Vollbuild
`/tmp/we1-full-shim-install` als Underlay. Der aktive Roboter-Install wurde
**nicht** gewechselt. Der Standard-BT-Build brauchte auf diesem Host den rein
temporären Pfad `/tmp/we1-btcpp-compat`; die Laufzeitbibliothek des gebauten
BT-Orchestrators löst nach
`/opt/ros/humble/lib/aarch64-linux-gnu/libbehaviortree_cpp.so` auf.
Der komplette Kandidaten- und Testnachweis steht im aktuellen
`docs/wohnungserkundung/STATUS.md`.

**Ausgeführt am 27.09.2026, aber nicht vollständig aufgezeichnet:** Die
anwesende Person bestätigte unabhängige Motorsperre, Stillstand und den
konkreten motorlosen Lauf. Quell-HEAD `fc6ac5e56f78898666d7c9e8b3785bdab74ab0f2`,
ein HWT-Leser, ein passiver Encoderleser, `active_drive=false`, keine
Explore-Mission und kein `base_hardware`-Antriebsknoten. Das vorab bestimmte
120-s-Fenster nach Bias-Readiness wurde nicht erreicht: `ros2 bag record`
brach nach 23,9 s wegen `SQLite error (5): database is locked` ab. Die
gespeicherten Daten enden während `gyro_bias_warmup`; kein `first_fault`.
Nach SIGINT endeten alle Launch-Kinder sauber. Der aktive Install blieb
unverändert. Einzelheiten und lokale Evidenzpfade stehen im aktuellen STATUS.
Eine Kopie des abgebrochenen Bags unter dem lokalen `recovered-copy/` wurde
nach Recorderende mit `ros2 bag reindex` um Metadaten ergänzt; sie enthält
weiterhin nur 23,91 s und 3755 Nachrichten.

`tools/kartierung/hwt_diagnose_record.py` wurde anschließend ohne Geräte auf
separaten ROS-Domains mit künstlichen Publishern geprüft: vollständige sieben
Themen über ein begrenztes Fenster, sauberes Recorderende und lesbare Metadaten;
ohne Readiness endet es begrenzt als unvollständig. Das Werkzeug verwendet
rosbag2 `--storage-preset-profile resilient` (SQLite-WAL) und liest die aktive
SQLite-Datei nicht. Ein dritter Laborlauf mit parallel offenem SQLite-Leser
endete ebenfalls vollständig. In dieser Laborphase wurde kein HWT-Gerät
gestartet. Die
konkrete Ursache der früheren SQLite-Sperre ist nicht belegt.

**Erneuter Lauf am 27.09.2026: Ergebnis B.** Nach ausdrücklicher Bestätigung
von unabhängiger Motorsperre, Stillstand und genau diesem motorlosen Lauf
startete der reparierte Recorder vor dem Stack. Quellstand
`c4295fcdacf817b33b53f17e38ac106bf01ae9e2`, Diagnosepakete aus
`/tmp/we1-hwt-f1f6b74-install` über dem dokumentierten Vollbuild, externes
LiDAR-Overlay und ROS Humble. Das lokale Manifest unter
`~/.local/share/amadeus/tests/hwt-tor1-20260927-run-nDR2Re/` belegt
Setup-Reihenfolge, Paketpräfixe, Modul-/Executable-Hashes, Profil-SHA und
Launchargumente. `active_drive=false`, `enable_auto_explore=false`, keine
Mission, kein Antriebsknoten; nur der FC03-Encoderleser am Motorbus.
Bias-Readiness um 14:24:09,788 UTC, danach 120 s vollständig mit sieben
Themen aufgezeichnet. Roh-HWT, Yaw, Encoder und Wächter blieben bereit,
`first_fault=null`, kein Latch; 0 RPM und keine Aktorausgabe. Der Recorder
endete mit Exit 0 und gültigen Metadaten, der Stack danach per einmaligem
SIGINT; alle Kinder endeten sauber und beide Ports sind frei. **Unter diesen
Bedingungen nicht reproduziert.** Der alte Fahrfehler bleibt ohne
Rohstatus-Originalwert; kein TOR 2 oder Fahrnachweis. Der aktive Install
blieb unverändert. Einzelheiten und Themenzähler stehen im STATUS.

Jeder weitere Lauf braucht eine neue aktuelle Freigabe der anwesenden Person.
Vor Ort unabhängige Motorsperre und Stillstand erneut bestätigen, vorhandene
Prozesse und Portbesitzer prüfen, dann genau einen Stack verwenden. Keine
zweite HWT- oder Motorbusverbindung öffnen. Die echte Stationärbestätigung
für die HWT-Biasphase darf erst danach als Launchargument gesetzt werden.
Keine Explore-Mission, kein `active_drive=true`.
Sind die `/tmp`-Präfixe nicht mehr vorhanden, zuerst aus dem festgelegten
Quellcommit isoliert neu bauen und ihre Auflösung prüfen; keine ältere
Installation stillschweigend substituieren.

Für den späteren Lauf das **tatsächlich gesourcte** Setup in jeder beteiligten
Shell in dieser Reihenfolge festhalten: `/opt/ros/humble/setup.bash`,
`/home/p/.local/share/amadeus/releases/we1-ldlidar-shutdown-overlay/install/local_setup.bash`,
`/tmp/we1-full-shim-install/local_setup.bash`,
`/tmp/we1-hwt-f1f6b74-install/local_setup.bash`. Das rein lesende Werkzeug
`tools/kartierung/hwt_diagnose_manifest.py` vor dem Start mit lokalem
`--output`, `--profile src/explore/config/hwt601_parity_params.yaml`,
`--launch-file robot_bringup/app_mapping.launch.py`, den tatsächlich
gewählten `--launch-arg KEY=VALUE` und den vier `--sourced-setup`-Argumenten
aufrufen. Es hält Paketpräfixe, installierte Dateihashes, BT-Linkpfad,
HWT-Serial-/VL53-/DKMS-Versionen, Profil-SHA und die effektive
`AMENT_PREFIX_PATH`-Reihenfolge lokal fest. Das Manifest ist kein Ersatz für
den abgeglichenen Startbefehl und beweist allein keinen laufenden Knoten.

Die gerätefreie Recorderprüfung ist für den unveränderten Werkzeugstand
erledigt. Für einen später gesondert beauftragten Lauf vor dem Stackstart
das Werkzeug auf ein **neues** lokales
Bag-Verzeichnis unter `~/.local/share/amadeus/tests/` starten, mit
`--warmup-limit-s 120 --window-s 120`; es erfasst nur diese Topics:
`/shadow/hwt601/imu/data_raw`, `/shadow/hwt601/imu/yaw_rate`,
`/shadow/hwt601/raw_status_json`, `/shadow/hwt601/status_json`,
`/fusion/hwt601/wheel_odom_raw`, `/shadow/hwt601/wheel_status_json` und
`/fusion/hwt601/status_json`. Es wartet höchstens 120 s auf kalibrierte
Readiness, zeichnet danach höchstens 120 s auf und beendet nur seinen eigenen
Recorderprozess mit SIGINT. Die laufende SQLite-Datei nicht anderweitig
öffnen; `*-summary.json`, Metadaten und `*-info.txt` erst nach Recorderende
auswerten. Bei `incomplete` den Stack sauber beenden und nicht erneut starten.
Startprofil: `active_drive:=false`, `use_hwt601_odometry:=true`,
`enable_auto_explore:=false`, `start_web_gui:=false`,
`explore_params_overlay:=<absoluter Pfad zum Parity-Profil>`;
`operator_stationary_confirmed:=true` nur nach echter Bestätigung.
Ergebnis einschließlich Lastbedingungen, Laufdauer, Nullbewegung und
`first_fault` oder „nicht reproduziert“ im STATUS berichten. Die alte
Fahrtursache wird dadurch nicht rückwirkend festgestellt. Kein Tor 2,
kein Deployment und keine Fahrt aus diesem Erfassungslauf ableiten.

## Integrationsbasis 27.09.2026 — keine Aktivierung

Der dokumentierte WE-Integrationsbranch `docs/we1-integrationsbasis-audit`
enthält die aus dem letzten lokalen Parity-Kandidaten gesicherten
Quelländerungen, das Profil `src/explore/config/hwt601_parity_params.yaml`
und die Dokumentation auf Masterplan v1.0. Ein neuer isolierter Build liegt
ausschließlich unter `/tmp/we1-*`; er wurde weder als Underlay noch als
Overlay des Roboterprozesses aktiviert. Der zuletzt berichtete Realtest nutzte
`~/roboter_ws-parity-reset/install_parity_real`; seine vollständige
Paket-SHA-/Präfixauflösung ist nicht protokolliert. Die Integrationsbasis ist
daher eine reproduzierbare Softwarezusammenstellung, noch kein bestätigter
aktiver Roboter-Install. Startparameter, Rückfall und Nachweise stehen im
aktuellen `docs/wohnungserkundung/STATUS.md`. Keine weitere Fahrt aus dieser
Zuordnung ableiten.

## Parity-Kandidat: VL53-Recovery und Realtest 27.09.2026

Nur das isolierte Overlay `~/roboter_ws-parity-reset/install_parity_real`
enthält die neue kanalgetrennte, begrenzte VL53-Runtime-Recovery. Das aktive
`~/roboter_ws/install` blieb unverändert. Der motorlose VL53-Lauf war über
125,1 s mit 508 beidseitig gesunden Statusmeldungen stabil; 989 betroffene
Softwaretests und der Paketbuild bestanden. Rückfall: die Änderungen in den
beiden Dateien unter `src/vl53_near_field/` im isolierten Branch zurücknehmen
und das VL53-Paket neu bauen.

Der einmalig aktive Parity-Lauf startete über Mission-Manager/BT und erreichte
einen autonomen Rundblick von 361,7°. Danach verriegelte die HWT-Rohquellen-
Prüfung `raw_driver_not_ready` (1790492567,566); das Fahrtor stoppte und die
Frontier-Vorausrichtungen scheiterten. Keine Türdurchfahrt. Beide VL53 und
LiDAR blieben frisch. Das Bag liegt ausschließlich lokal unter
`~/.local/share/amadeus/tests/parity-real-20260927-vl53-recovery`.
Der konkrete HWT-Rohstatuswert hinter der Verriegelung wurde nicht
aufgezeichnet. Vor weiterer Fahrt muss dieser Fehler getrennt geklärt werden.
Der STL-27L-Overflow trat nur nach SIGINT beim Shutdown auf.

## Motorloser HWT/Encoder-Preflight 26.09.2026: zweimal bestanden

Der Nutzer gab zwei motorlose Vollstack-Zyklen frei und bestätigte unabhängig
gesperrte Motor-Endstufen. Isolierter Kandidat aus PR #101 in ROS-Domain 217,
`active_drive=false`, HWT-Opt-in und ohne automatische Erkundungsmission;
der aktive `~/roboter_ws/install` blieb unverändert. Motorbusbesitzer war
ausschließlich der read-only FC03-Shadow-Knoten. Kein Nichtnull-Fahrwert.

Im Shadow-Profil sind Paar- und Sample-Grenze 0,12/0,18 s. Ein einzelnes
verspätetes, aber gültiges Paar vor der Baseline wird verworfen und neu
gelesen. Eine zweite aufeinanderfolgende Überschreitung und jede nach der
Baseline verriegeln; Antwort- und Konfigurationsfehler bleiben sofort
fail-closed. Aktive Base-Hardware-Encodergrenze 0,30 s, Motorparameter,
Modbus-Timeout, HWT/VL53/LiDAR, Scope, Footprint, Collision Monitor und
Navigation wurden nicht geändert.

Je 180 s nach Biasphase: 3.604 akzeptierte Paare und keine Fehler oder
Reconnects pro Fenster. Zyklus 1 Paarzeiten min/Median/p95/max
9,95/13,57/20,26/44,66 ms; Zyklus 2 10,08/13,77/20,74/45,32 ms.
Einzelread-Statistik pro Motor und Quellenalter stehen in
`/home/p/.local/share/amadeus/tests/stage3-hwt-cycle{1,2}.json`. HWT-Bias,
Fusion, VL53, LiDAR, Map/TF und sechs Nav2-Lifecycles waren frisch. Im zweiten
SIGINT-Shutdown wurde eine laufende Probe mit 124,547 ms fail-closed verworfen
und nicht publiziert. Alle Kinder beendeten sauber mit Exit 0, sämtliche
seriellen Handles wurden frei; keine SIGTERM-Eskalation.

Für die anschließende Freigabevorlage ist das lokale Profil
`stage3-real-20260925-after-r2-scope.yaml` mit Scope-ID
`stage3-local-scope-20260925-after-r2` und Session
`stage3-20260925-after-r2` bestimmt. Aktuelle Live-Karte in Frame `map`:
Fingerprint beginnt `c6c949`; beim Neustart erzeugt der bestehende
Map-Status-Korrelator eine neue Bindung zum aktuellen Fingerprint. Vor einer
Fahrt müssen aktuelle Startpose und Scope sichtbar abgeglichen werden. Es gab
keine Fahrt. Der begrenzte 0,25-m-/±15°-Test wird separat zur ausdrücklichen
Fahrfreigabe vorgelegt; Stufe 3 insgesamt bleibt bis zum Umfahrnachweis GELB.

## Aktuell: isolierter HWT601-WE-Kandidat, Geräteprüfung noch offen (26.09.2026)

**Softwareintegration lokal BESTANDEN; motorlose Prüfung OFFEN; reale
Bewegungsprüfung OFFEN.** Dieser Auftrag hat keine Geräte angesprochen und
keinen Roboter-Stack gestartet. Die alten Hardwarefreigaben werden nicht auf
die neue Integration übertragen. Keine Umstellung von `~/roboter_ws/install`.

### Exakter Quell- und Installstand

Branch `codex/we1-hwt601-fusion`, Basis PR #100 / `113014e`, HWT-Referenz
`1d91229`; Wiederverwendung `b3b6370`, funktionale Integration `f61e3e7`.
Arbeitskopie `/home/p/roboter_worktrees/we1-hwt601-fusion`; fremde Änderungen
in `/home/p/roboter_ws` nicht übernommen oder verändert. Nichtsymlink-Build:
`/home/p/.local/share/amadeus/releases/we1-hwt601-IC2SLr/{build,install,log}`.

Alle folgenden Pakete lösen nach Sourcen dieses Isolats tatsächlich aus
`we1-hwt601-IC2SLr/install/<paket>` auf:
`robot_state_estimation`, `base_hardware`, `amadeus_lidar_bringup`,
`robot_bringup`, `robot_navigation`, `explore`, `robot_map_manager`,
`mission_manager`, `bt_orchestrator`, `safety_monitor`, `vl53_near_field`,
`robot_interfaces`, `semantic_map_manager`, `amadeus_map_identity`.
Nav2 und `robot_localization` kommen aus `/opt/ros/humble`, `slam_toolbox`
aus `/home/p/amadeus_slam_toolbox_ws/install/slam_toolbox`, der korrigierte
LiDAR-Treiber aus `we1-ldlidar-shutdown-overlay/install/ldlidar_stl_ros2`.

Die gespeicherte Setup-Kette (unten nach oben; Release-Namen jeweils unter
`/home/p/.local/share/amadeus/releases/`, jeweils mit `/install`) ist:

```text
/opt/ros/humble
/home/p/amadeus_slam_toolbox_ws/install
we1-ldlidar-shutdown-overlay
we1-10e1858074e7-r1
we1-stage1-5e3fe0a-20260923
we1-stage2-6fd36d5-20260923
we1-stage3-bypass-s8QMY8
we1-stage3-complete-1kI6en
we1-stage3-vl53-mark-bwVxEL
we1-stage3-explorer-shutdown-dnrGyH
we1-stage3-health-CVhWvH
we1-stage3-frame-gap-r2
we1-stage3-cancel-latch-r1
we1-stage3-vl53-boot-r1
we1-hwt601-IC2SLr
```

Nicht neu gebaute App-Pakete bleiben in den alten Unterlagen. Der neue
Kandidat überlagert dagegen sämtliche oben genannten 14 WE-Pakete.
Quelle/Install paarweise SHA-256-identisch: `hwt601_fusion_health.py`
`9297699e...`, `hwt601_fusion_guard.py` `f144f6cc...`,
`cmd_vel_mission_gate.py` `fa5a6b60...`, HWT-SLAM-Launch `d11b6418...`,
VL53-Knoten `98d2b42e...`, Nav-Runtime `715b2a41...`.
Letztere und VL53/Interfaces/Nav-Sicherheitskonfiguration/Basisparameter
sind gegenüber PR #100 unverändert.

Buildbesonderheit: Der systemweite BehaviorTree-CMake-Export sucht eine
nicht vorhandene nicht-multiarch Bibliothek. Wie im bestehenden WE-Build
wurde **nur beim Bauen** der vorhandene Export unter
`we1-10e1858074e7-r1/underlay/behaviortree_cpp/share/behaviortree_cpp/cmake`
per `-Dbehaviortree_cpp_DIR` verwendet. Keine Systembibliothek verändert.
Runtime löst `libbehaviortree_cpp.so` aus
`/opt/ros/humble/lib/aarch64-linux-gnu/` auf; SHA-256
`c87409e5c2853a723537bbfc3d05be055c649ce3823e8027962a477eb97a7b15`
identisch zum vorhandenen Unterlagenartefakt. Keine fehlende Laufzeitbibliothek.

### Motorloser nächster Vorlauf — vorbereitet, NICHT ausgeführt

Vorher einmal gebündelt aktuell bestätigen lassen: Gerätezugriff auf HWT,
FC03-Encoder, VL53/LiDAR und ROS; kein paralleler Stack; Roboter ab Start
mindestens 30 s tatsächlich unbewegt; unabhängig deaktivierte Motorendstufe
bei weiterhin FC03-antwortender Controllerelektronik; Hardware-Halt erreichbar.
Bekannten dedizierten HWT-Adapter/Montage nur auf zwischenzeitliche Änderung
prüfen, nicht neu kalibrieren. Falls die getrennte Versorgung nicht möglich
ist, ist dieser FC03-Aufbau **nicht motorlos prüfbar**; keine Dry-run-Werte
unterschieben und keine Motoren für den Vorlauf aktivieren.

Danach in einer frischen Shell ausschließlich obigen Kandidaten sourcen.
Bestehendes begrenzendes WE-Profil aus
`/home/p/.local/share/amadeus/profiles/stage3-real-20260925-after-r2-scope.yaml`
vor Verwendung auf Kartenidentität und aktuelle Pose prüfen; nicht als
erneute physische Bereichsfreigabe behandeln oder automatisch ausweiten.
Bestehende `app_mapping.launch.py` mit `use_hwt601_odometry:=true`,
`operator_stationary_confirmed:=true` **erst nach der Bestätigung**,
`active_drive:=false`, `enable_auto_explore:=false`, `start_web_gui:=false`
und genau diesem lokal verifizierten `explore_params_overlay` verwenden.

In zwei getrennten Start-/Stopp-Zyklen protokollieren:

1. Ausschließlich `hwt601_encoder_shadow_reader` am Motorbus, kein
   `base_hardware`-Prozess; FC03-only, echte Zähler, kein Command-Abonnent.
   HWT eigener `/dev/ttyUSB_HWT601`, keine Sensorregister-Schreibbefehle.
2. Roh-HWT frisch, reale Stillstandswerte/Achsen plausibel, Bias nach
   unverändertem 15+10-s-Fenster stabil/kalibriert/eingefroren; Encoder-vx
   im tatsächlichen Stillstand plausibel. Kein künstliches Stillstandsflag
   aus Encoder-Dry-run. Keine Grenzwertänderung bei Fehlschlag.
3. Genau ein `/odom`-Publisher und dynamisches `odom->base_link` vom EKF,
   genau ein `/map`/`map->odom` vom SLAM; TF-Frische und Rohquellen gesondert.
4. Beide VL53 nach aktuellem Frame/Target/UNKNOWN-Vertrag, LiDAR,
   Kartenmanager-Frische, Karten-/Scope-Bindung, Safety und Nav2 prüfen.
   `/fusion/hwt601/status_json`: `sources_ready=true`, aber
   `hwt_motion_ready=false` / `readonly_preflight_no_motion`.
   Das ist keine vollständige Fahrtfreigabe; alle bisherigen Tore bleiben.
   Keine Mission senden, keine Nichtnull-Fahrbefehle, keine Motoraktivierung.
5. SIGINT nur an die protokollierte Launch-PID, nie an die Prozessgruppe.
   Alle Kinder, Logs und Gerätehandles prüfen. Zwei saubere reale Shutdowns
   erforderlich; gerätefreie Prozess-Shutdowns ersetzen diese nicht.

### Danach separat freizugebende Bewegungsdiagnose

#### Diagnosepfad lokal implementiert, Zielsystem noch nicht aktualisiert

Auf Branch `codex/we1-hwt601-fusion` ist der Diagnosemodus jetzt standardmäßig
deaktiviert (`enable_stage3_motion_diagnostic:=false`). Bei explizitem Opt-in
startet ein einzelner `/stage3_motion_test/start`-Trigger genau diese Sequenz:
0,25 m vorwärts, bestätigter Stillstand, +15°, Stillstand, −15° relativ zur
gemessenen Pose nach der positiven Drehung, Endstillstand. Es gibt keine
anderen Ziele, keine Wiederholung, Rückwärtsfahrt oder Recovery. Der
Diagnoseknoten publiziert ausschließlich `/cmd_vel_stage3_diagnostic_raw`;
`cmd_vel_mission_gate` gibt nur bei frischen normalen Sicherheitsquellen,
aktivem Diagnose-Opt-in, nicht laufender Mission, E-Stop-Freigabe, HWT und TF
nach `/cmd_vel_nav` frei. Danach bleiben Velocity Smoother, Collision Monitor,
`/cmd_vel` und `base_hardware` die vorhandene Kette. Produktgrenzen und
Parameter sind unverändert. Gate-Ausgang, Smoother, Collision Monitor,
Basis-Soll-/Ist-RPM und Encoderzähler, Encoder-/HWT-/fusions-Odom, LiDAR,
TF, Safety und beide VL53 werden mit Empfangs- und Nachrichtenzeit privat als
JSONL protokolliert.

Vor Triggern verlangt der Knoten das bereits bestimmte Scope-Profil und die
exakte Scope-ID `stage3-local-scope-20260925-after-r2`, einen frischen
Map-Fingerprint im bestehenden SLAM-Session-Kontext, Map-Frame-Pose und den
unveränderten gepaddeten Footprint vollständig innerhalb des Polygons. Die
Startkarte wird gebunden; nachfolgende Kartenrevisionen derselben SLAM-Session
werden toleriert, aber veraltete oder verlorene Bindung stoppt den Lauf. Jeder
Phasentick stoppt fail-closed bei fehlender/veralteter HWT-/Encoder-, VL53-,
LiDAR-, TF-, Karten-, Scope- oder Safety-Quelle. Nullkommando und deaktiviertes
Diagnose-Active folgen bei Ende oder Abbruch.

Gerätefreie Verifikation: alle 46 Tests aus `robot_navigation` bestanden;
`robot_navigation` und `robot_bringup` erfolgreich in einen separaten
temporären Build/Install unter `/tmp/amadeus-stage3-motion-build.N6Ninf`
gebaut. Der frühere 180-s-Motorlosnachweis wurde nicht wiederholt. Der
temporäre Overlay-Build wurde einmal für einen Live-Stackstart gesourct; der
Diagnosemodus blieb aus, es wurde kein Missionsauftrag gesendet. `base_hardware`
meldete währenddessen nur Nullsollwerte und 0 RPM; keine Bewegung. Der
Safety-Monitor meldete `use_gpio_estop=false` und „Kein Hardware-Not-Aus
angebunden“. Der Nutzer hat klargestellt und manuell bestätigt, dass der
unabhängige Hardware-Halt außerhalb GPIO/ROS verdrahtet und erreichbar ist;
diese Warnung ist nur die fehlende Jetson-GPIO-Rückmeldung. Der erste Lauf
wurde wegen einer Fehlinterpretation beendet, nicht wegen eines gemessenen
Sensor-/Safety-Fehlers. Für den einmaligen Diagnoselauf ist jetzt
`lab_external_hardware_halt_attested:=true` als standardmäßig falsches Opt-in
implementiert und im Diagnosestatus sichtbar; `/safety/estop`, Collision Monitor, Quellen-, TF- und
Scope-Prüfungen bleiben aktiv.
Der erste Triggerlauf scheiterte vor jeder Bewegung mit `veraltete Quellen:
near_status`. `ros2 node info` belegte, dass der Prüfknoten
`/near_field/status` fälschlich als `std_msgs/String` abonniert hatte; der
aktive `/vl53_near_field`-Knoten publiziert
`robot_interfaces/msg/NearFieldStatus`. Die Subscription wurde im Kandidaten
korrigiert und die Regression ergänzt. Erneut bestanden 46 Tests, isolierter
Build und `git diff --check`.

Mit dem korrigierten Kandidaten wurde der gebundene Bewegungstest einmal
vollständig ausgeführt. Ergebnis `complete`, mit drei bestätigten Stillständen;
`/odom` meldete 0,270 m Translation, Motor-Ist-RPM erreichten maximal ±122,
HWT-Gyro/Encoder/LiDAR/TF/Safety und 140 VL53-Statusframes wurden synchron
aufgezeichnet. Modbusfehler, verworfene Encoderupdates und Reconnects: 0.
Private Evidenz liegt unter
`/home/p/.local/share/amadeus/tests/stage3-hwt601-motion-20260926T105410Z.jsonl`.

Direkt danach schlug die automatisch gestartete Explore-Mission während ihres
Initialscans mit `initial_scan_no_progress` fehl. Status: 0/3 qualifizierende
Beobachtungen, 0 Frontierziele, `navigation_dispatched=false`; daher kein
Nav2-Ziel, keine Hindernisinteraktion und kein Umfahrnachweis. Ein vorheriger
Versuch war während desselben Initialscans kontrolliert storniert worden.
Stack wurde mit SIGINT am Launch-PID beendet; Motoren standen auf 0 RPM und
keine Roboterprozesse/seriellen Handles blieben zurück. Der Diagnoseprozess
warf beim Shutdown einen `RuntimeError` im rclpy-Nachrichten-Decoding. Dieser
Shutdown-Befund ist ungeklärt und muss vor einem weiteren Hardwarelauf
untersucht werden. Aktiver `~/roboter_ws/install` unverändert; kein Merge.
Stufe 3 bleibt GELB.

**Rückfall:** Vollständig stoppen, Shutdown/Handles bestätigen, neue Shell
mit bisheriger PR-#100-Installkette bis `we1-stage3-vl53-boot-r1`,
`use_hwt601_odometry=false`. Vor Neustart genau einen Topic-/TF-Eigentümer
sicherstellen. Kein Live-Umschalten, kein automatischer Merge. Softwaretests
und offene Altbefunde sind im [WE-STATUS](wohnungserkundung/STATUS.md) belegt.

## Historisch: isolierter Korrekturstand, reale Umfahrung noch offen (25.09.2026)

PR #100, Branch `fix/we1-stage3-vl53-regression`. Aktiver
`~/roboter_ws/install` unveraendert. Fuer motorlose Verifikation:
`/opt/ros/humble`, bestehende WE-Overlays,
`we1-stage3-frame-gap-r2/install` (VL53),
`we1-stage3-cancel-latch-r1/install` (Explorer); `robot_navigation`
weiter aus `we1-stage3-health-CVhWvH/install`. Das lokale, nach dem letzten
Odometrie-Endpunkt transformierte Scope-Profil ist
`/home/p/.local/share/amadeus/profiles/stage3-real-20260925-after-r2-scope.yaml`.
Nicht als neue physische Bereichsfreigabe oder als produktiven Install
uebernehmen.

Veraendert wurden nur Frame-Read-/Raster-Plausibilitaet und die
asynchrone Cancel-Ursachenbindung. 971 Tests bestanden; motorlos 44/44
gesunde Sensortripel, TF maximal 0,053 s, null Fahrbefehle, danach
korrekter Einzel-PID-Shutdown 24/24 sauber. Der vorangegangene
Terminal-Gruppenabbruch hatte KeyboardInterrupt-Tracebacks und zaehlt
nicht. Reale Testspur: sechs Quellen-Cancels, nur 0,1445 m Bewegung,
kein Vorbeifahren an der Barriere. `child_navigation_canceled`-Race ist
softwareseitig korrigiert, nicht real belegt. Bei `w=-0,12 rad/s` meldete
die Encoder-Odometrie zeitweise nur `-0,005...-0,04 rad/s` trotz etwa 34
Motor-rpm: Antrieb/Encoder/Schlupf vor weiterer Fahrt gezielt pruefen.
Keine Kalibrier- oder Sicherheitswerte auf Verdacht aendern. Stack aus,
keine offenen Geraetehandles. Evidenz im [WE-STATUS](wohnungserkundung/STATUS.md).
Nach einem rein formatierenden Rebuild des Explorer-Overlays versagte ein
weiterer voller motorloser Start durch VL53-Exit 1 vor ersten Topics;
Ursache nicht gesichert. Zwei isolierte VL53-Starts und ein weiterer voller
Start gelangen, aber kein vollstaendiger Preflight des letzten Builds.
Der genaue Fehler wurde danach im vollen Stack erfasst: rechter
VL53-MCU-Boot-Poll, `VL53L5CXException: 0`. Separates oberstes Overlay
`we1-stage3-vl53-boot-r1/install` wiederholt ausschliesslich diesen
Initialisierungsversuch einmalig und raeumt bei erneutem Fehlschlag auf.
974 Tests; zwei vollstaendige motorlose Preflights des exakten neuen
Installstands (58/58 und 57/57 gesunde Tripel, null Fahrbefehle) und je
24/24 saubere Shutdowns. Die Retry-Verzweigung wurde real nicht getroffen.
Finaler geraetefreier Prozesspruefer: `frontier_replan`, `local_blocked`,
echter Nav2-`explorer_bypass` und `stopped_bypass` bestanden, mit
fortgesetzter Elternmission und maximal einem aktiven Nav2-Kind.
**Keine Fahrt**, bis die im vorherigen Realversuch gemessene deutliche
Motor-RPM-/Encoder-Odometrie-Abweichung geklaert und die A/B-Geometrie
erneut passend vorbereitet ist; die Startkorrektur allein ist kein
Umfahrnachweis.

## Aktuell: realer Rundblick wegen VL53-Frame-Health beendet (25.09.2026)

Der Nutzer korrigierte die folgende historische Aussage und bestätigte
Abschaltung und Prüfung vor Ort sowie die Fahrfreigabe. Diese Auskunft ist
kein ferntechnischer Hardwarebeweis. Exakt derselbe isolierte Health-Install
und dasselbe Scope-Profil wurden verwendet; kein aktiver Install und keine
Produktparameter geändert (Repository `3913079`, PR #100).

Vorlauf bestanden: 57 gesunde VL53-Tripel je Seite, TF frisch, alle sechs
Lifecycles aktiv, gemessene RPM null. Ein autonomer Explorerauftrag startete.
Nach 13,267 s im Rundblick beide `frame_healthy=false`, Fahrtor `blocked`,
Wächter-Cancel. Bei 16,082 s gemessene RPM mindestens zwei Sekunden null;
Shutdown 24/24 sauber. Keine Umfahrung und keine Tests C/D. Ursache des
beidseitigen Health-Abfalls noch offen; nicht durch gelockerte Grenzwerte
oder wiederholte Fahrversuche umgehen. Stack bleibt aus. Details/Evidenz:
[WE-STATUS](wohnungserkundung/STATUS.md).

## Historisch: Sicherheitsstopp nach gegenteiliger Nutzeraussage (25.09.2026)

**Keine weitere reale Fahrt oder Motoraktivierung.** Der Nutzer erklärte
nach dem unten dokumentierten Teilversuch, am Roboter existiere überhaupt
kein hardwired Not-Aus und die Motorversorgung könne nicht ausgeschaltet
werden. Die frühere Vor-Ort-Bestätigung eines erreichbaren Not-Aus ist
damit widersprüchlich und darf nicht mehr als Sicherheitsnachweis gelten.
Die 0,18-m-Kurzfahrt bleibt eine technische Beobachtung, **keine gültige
reale Sicherheitsabnahme**. Software-Cancel und ROS-Shutdown sind kein
Ersatz für eine unabhängige Abschaltmöglichkeit. Der Stack ist gestoppt;
kein RS485-Handle ist offen.

Nach dieser Offenlegung nur passive Starts mit `dry_run=true`, RS485 aus,
null Motorsollwerten. Eine neue 0,75 m hohe, 0,55 m breite Barriere etwa
0,55 m vor dem Roboter wurde vom LiDAR frontal ab ca. 0,81 m Achsabstand
gesehen; Nav2 berechnete im geladenen Scope rechts einen Diagnosepfad mit
106 Posen. 59 gesunde VL53-Teilframes je Seite im Preflight, frische
TF-/Karten-/LiDAR-Daten und aktive Safety/Nav2. Das ist **keine** reale
Umfahrung und kein autonomes Explorerziel. Beide Starts endeten mit
24/24 sauberen Kindern. Keine Produkt-/Sicherheitsparameter und kein
aktiver Install wurden geändert. Weitere Fahrt erst nach Herstellung
und Vor-Ort-Nachweis einer unabhängig wirksamen Hardware-Not-Aus- oder
Motorstromtrennung; neue ausdrückliche Freigabe erst danach relevant.
Siehe [WE-STATUS](wohnungserkundung/STATUS.md).

## WE-1 Stufe 3: reale Kurzfahrt A, B ohne Route beendet (25.09.2026)

PR #100, Quellstand `a710fe3`, ausschließlich isolierter Install
`we1-stage3-health-CVhWvH/install`; der aktive Install blieb unverändert.
Vor Ort wurden Not-Aus, menschen-/tierfreier Bereich und Motorstrom
bestätigt. Ein lokales Scope-Profil band die frische Startkarte
(`map`-Pose `(0,0,0)`) an `x=[-0,5;2,6]`, `y=[-0,8;0,8]`. Der
motorisierte Vorlauf hatte 59 frische gesunde VL53-Tripel je Seite,
frische LiDAR-/Karten-/TF-/Odom-Quellen, Nav2 und Collision Monitor aktiv,
Safety frei, RS485 bereit und vor Auftrag 0 Fahr-/Motorwerte.

Test A: Nach autonomer Zielwahl fuhr der Roboter 0,18 m laut Odometrie;
Test-Cancel, Mission `canceled`, beide Motor-RPM 0 für mindestens 2 s.
Test B: 0 m Translation, kein Nav2-Pfad. Die Explorer-Policy hatte nach
Rundblick 10 offene, aber 0 zulässige Aufgaben (`no_current_raw_map_route`
oder auf aktueller Revision nicht beobachtet). Der separate Wächter
meldete später `guard_lost`; der Einzelgrund ist nicht gemessen.
Die reale Barriere war nur 0,40 m hoch und 0,38 m breit, etwa 1 m leicht
links vor der Ausgangspose: unter der 0,66-m-LiDAR-Ebene und damit kein
gültiger Aufbau für den vorgesehenen frühen LiDAR-/Nav2-Umfahrnachweis.
Keine Umfahrung oder Missionsfortsetzung nach Hindernis behaupten.
C/D nicht gestartet. Kein Produktparameter und keine Sicherheitsgrenze
geändert, kein Merge. Logs/Wächterbericht lokal unter
`~/.local/share/amadeus/tests/stage3-real-*`, Scope-Profil unter
`~/.local/share/amadeus/profiles/stage3-real-20260925-scope.yaml`.

Der Stack ist mit SIGINT **nur an Launch-PID** beendet: 24/24 Kinder
sauber, kein Traceback, Prozessrest oder offener I²C-/LiDAR-/RS485-Handle.
**Motorversorgung wird nicht softwareseitig getrennt; nach der späteren
Nutzeraussage ist physisches Ausschalten derzeit nicht möglich.** Erst die
oben genannte Hardware-Sicherheitslücke schließen; danach Route/Policy und Wächtergrund
motorlos diagnostizieren sowie eine mindestens 0,80 m hohe matte
bleibende Barriere mit gemessenen Passagen vorbereiten. Danach erneuter
motorloser Check und separate aktuelle Fahrfreigabe; B vor C/D.
Stufe 3 bleibt GELB. Details im [WE-STATUS](wohnungserkundung/STATUS.md).

## WE-1 Stufe 3: finaler Health-Kandidat motorlos bestanden (25.09.2026)

PR #100, Produktcommit `e18a267`, finaler Gerätefrei-Prüfstand `b692c28`.
Die aktuelle Produktvorgabe trennt technische Framegesundheit von
Target-/Spaltenabdeckung. Die unten beschriebenen früheren
Fahrvertragsblocker sind Historie, nicht der aktuelle Health-Vertrag.
Gesunde vollständige Teilframes sperren nicht global; unbekannte Zonen
bleiben ohne Clearingstrahlen. Reale gültige Nahpunkte, Juli-Filter,
FLIPX, Sensorfrische und sämtliche Fahr-/Kollisionsgrenzen unverändert.

**Ausschließlich isolierter Install, kein aktiver Install überschrieben:**
`/home/p/.local/share/amadeus/releases/we1-stage3-health-CVhWvH/install`.
Enthält gemeinsam neu gebaut `robot_interfaces`, `vl53_near_field`,
`robot_navigation`, `explore`, `safety_monitor`; Quell-/Install-SHA und
VL53-/Nav2-Konfiguration stimmen überein. Statusformat enthält nun
`left_frame_healthy`/`right_frame_healthy`; keine alten Consumer mischen.
Die reale Prozessauflösung bestätigte diese fünf Pakete, Stage-3-complete
für Basis/Manager und Stufe 1 für Bring-up. Vollständige Overlaykette im
maßgeblichen [WE-STATUS](wohnungserkundung/STATUS.md).

Mit unverändert physisch getrennter Motorversorgung zweimal gestartet:

```bash
source /home/p/.local/share/amadeus/releases/we1-stage3-health-CVhWvH/install/setup.bash
export ROS_DOMAIN_ID=217
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/p/.local/share/amadeus/releases/we1-10e1858074e7-r1/cyclonedds-local.xml
unset ROS_LOCALHOST_ONLY
ros2 launch robot_bringup app_mapping.launch.py active_drive:=false enable_auto_explore:=false start_web_gui:=false
```

Keine Action gesendet, kein Nichtnull-Fahrbefehl. Je ca. 15 s: 59/56
stempelgleiche frische VL53-Tripel, beide Health true/PARTIAL/Maske 0;
installierte Health-Prüfung auf realen Daten positiv. Kartenmanager ok,
LiDAR/Karte/Odom/TF frisch (maximales TF-Alter 0,034 s), alle fünf
Nav2-Lifecycles und Collision Monitor active, Safety false. Basis
`dry_run=true`, `allow_rs485=false`, `rs485_ready=false`, alle Sollwerte 0.
Jeweils 24/24 Kinder sauber nach SIGINT **nur an Launch-PID**, kein
Traceback/Restprozess/offener Gerätehandle. Prüfberichte nur lokal unter
`~/.local/share/amadeus/tests/stage3-health-hardware-cycle{1,2}.{json,log}`.

Dieser passive Test ließ Explore-Opt-in und Scope-Verifikation bewusst
aus; der alte R9-Scope ist nach Kartenneustart nicht gültig. Vor Fahrt
vermessenen markierten Bereich/Startpose an aktuelle Karte binden und
gesonderte aktuelle Fahrfreigabe einholen. Konkreter Vorschlag im
WE-STATUS: 4,70 × 2,50 m, hohe unbelebte bleibende Barriere, separate
Stopp-/Wand-/Eckaufstellung, begrenzte Mission und klare Abbruchbedingungen.
Noch **keine reale Umfahr-/Stoppbefreiungsabnahme**, Stufe 3 insgesamt GELB.
Motorloser Check bestanden; weitere Softwareentwicklung hier beendet.
Rückfall: komplettes neues Overlay nicht sourcen; vorheriger Stand sperrt
weiter streng. Das verworfene `we1-stage3-vl53-partial-PiRlgn` nicht nutzen.

## Historie: realer VL53-A/B-Test, passive Zielsystemwiederholung (25.09.2026)

Die echte matte Platte (~1 × 1 m, ~0,40 m vor beiden VL53) ergab links und
rechts je 30/30 vollständige Rohframes mit 64/64 gültigen Targets,
`target_status=5`, `nb_target_detected=1`, kleinen Sigma-Werten und je
64 Original- sowie 8 Costmap-Punkten. Nach Entfernen der Platte lieferten
dieselben Sensoren/Konfigurationen je 30 vollständige Frames, aber nur
2–6 gültige Fernreturns pro Frame in der untersten Sensorzeile, 0 volle
Spalten, `QUALITY_PARTIAL` und leere Nahwolken. Die Hardware ist damit
plausibel; die neue globale 64/64-Forderung ist für freie Szenen nicht
praktikabel und nicht real fahrabgenommen. Einzelne fehlende Targets
bleiben **unbekannt**, niemals pauschal 0,60 m frei. Rohframes und
Auswertung sind nur lokal unter
`/home/p/.local/share/amadeus/tests/we-stage3-vl53-ab-20260925.json`.

Das ausschließlich isolierte Präfix
`/home/p/.local/share/amadeus/releases/we1-stage3-vl53-partial-PiRlgn/install`
enthält eine **verworfene** pauschale `PARTIAL`-Freigabe im Explorer/Fahrtor.
Sie bestand gerätefreie Prozessfälle, besitzt aber keinen positiven
Bewegungsraumbeleg; **nicht für Fahrt oder künftige Freigabe sourcen**.
Der Quellbranch/PR #100 enthält diese Änderung nicht. Sein marking-only-
ObstacleLayer-Fix ist davon unabhängig. Der aktive Roboter-Install und alle
Fahr-/Sensorgrenzen blieben unangetastet.

Mit physisch getrennter Motorversorgung wurden zwei vollständige passive
Starts über das isolierte Präfix geprüft: beide VL53, LiDAR, TF, Rohkarte,
Kartenmanager, Safety, Collision Monitor und Nav2 waren frisch/aktiv;
`active_drive=false`, Explore-Opt-in aus, `dry_run=true`, RS485 aus,
alle Fahr- und Motorsollwerte null. Je Start 24/24 saubere Kinder beim
Einzel-PID-SIGINT, keine Tracebacks, Restprozesse oder Gerätehandles.
Danach bestanden auch **zwei Starts ohne das verworfene Präfix** auf dem
strengen PR-#100-Stand mit Explorer-Shutdown- und marking-only-Overlay:
beide VL53 `PARTIAL`/Maske 0, Safety aus, Collision Monitor/Nav2 aktiv,
acht Fahrbefehlskanäle ohne Nichtnullwert, Basis Dry-run/RS485 aus und
jeweils 24/24 saubere Kinder ohne Rest-Handle. Der normale freie Raum
bleibt mit diesem Stand am Fahrtor gesperrt, wie beabsichtigt.
Der vorhandene R9-Scope ist nach SLAM-Neustart nicht mehr gültig und wurde
deshalb nicht geladen; der Explorer meldete `scope_verified=false`.
Der vollständige motorlose *Fahrbereitschafts*-Nachweis bleibt offen:
Vor Fahrplanung sind aktueller Kartenframe/Startpose/enger Scope und ein
positiver Beleg für den tatsächlich nötigen niedrigen und seitlichen
Fahrraum erforderlich. LiDAR bei 0,66 m und im WE-Launch deaktivierte OAK
ersetzen die unbekannten VL53-Zonen nicht. Keine reale Fahrt ohne gesonderte
Vor-Ort-Fahrfreigabe. Rückfall für das Testpräfix: nicht sourcen.

## WE-1 Stufe 3: VL53-Regression, Teilframe-Markierung (24.09.2026)

Der neue, ausschließlich motorlose Direktlauf las je 20 vollständige
Rohframes aus beiden echten VL53. Derselbe lokale Frame-Satz ergab mit dem
historischen Nahfilter 0 Hindernispunkte im freien Nahbereich; die heutige
Qualitätsauswertung fand je 220 gültige Fern-Zonen, aber 0 volle Spalten.
Eine komplette Rohdatennachricht ist somit nicht gleich 64 gültigen
Target-Returns. Die überwiegend unbeobachteten Zonen dürfen nicht als frei
gelten. Eine große, matte unbelebte Testfläche im Sichtfeld beider Sensoren
wurde noch nicht vermessen; die Hindernis-A/B-Prüfung fehlt.

Ein separater Kandidatenbranch ergänzt die bestehende VL53-Originalwolke
als **marking-only**-Quelle in beiden Nav2-ObstacleLayern. Dadurch kann ein
gültiger Nahpunkt aus einem Teilframe ein Hindernis markieren; er kann keine
unbekannten Zellen räumen. `robot_navigation` liegt nur im isolierten Overlay
`/home/p/.local/share/amadeus/releases/we1-stage3-vl53-mark-bwVxEL/install`;
der aktive Roboter-Install blieb unberührt. 969 Vertragstests und vier
gerätefreie echte Nav2-Stage-3-Prozessfälle bestanden, darunter dauerhafte
Umfahrung mit Explorer-Folgefortschritt und Stopp/Befreiung. Das Fahrtor
bleibt wegen der nicht belegten Bewegungsraumabdeckung gesperrt. Rückfall:
dieses letzte Overlay nicht sourcen. Keine reale Fahrt freigeben, bevor
Sensorabdeckung, aktueller Scope und vollständiger motorloser Preflight
positiv nachgewiesen sind.

## WE-1 Stufe 3: motorloser Zielsystembefund, Fahrt gesperrt (24.09.2026)

Nach ausdrücklicher Vor-Ort-Freigabe wurde der vorhandene Stufe-3-Kandidat
mit realen Sensoren, aber `active_drive=false`, `enable_auto_explore=false`
und physisch getrennter Motorversorgung gestartet. Die Stufe-3-Pakete lösten
aus `we1-stage3-complete-1kI6en` auf, LiDAR-Bring-up und `robot_bringup` aus
Stufe 1. Nach einem nachgewiesenen Explorer-SIGINT-Race wurde **nur** das
separate `explore`-Overlay
`/home/p/.local/share/amadeus/releases/we1-stage3-explorer-shutdown-dnrGyH/install`
zuletzt gesourct (Quellcommit `0fe9245`, gleiche Quell-/Install-SHA). Zwei
vollständige Wiederholungsstarts endeten mit je 24/24 sauberen Kindern,
ohne Restprozess oder Gerätehandle. Der aktive Robot-Install blieb unberührt.

**Fahrblocker:** Beide realen VL53 sind zwar frisch (~3,6 Hz), aber im
aktuellen freien Raum in sämtlichen Stichproben nur `QUALITY_PARTIAL` mit
Spaltenmaske `0/255`. Der separate Rohdatenlauf ergab links 223/1280 und
rechts 233/1280 gültige Zonen, beidseits 0/160 volle Spalten, vorwiegend
Status 255/kein Ziel. Der 64/64-Vertrag und damit das Fahrtor sind nicht
erfüllt; das ist keine Erlaubnis, ihn oder andere Sicherheitsgrenzen zu
lockern. LiDAR, Karte, TF, Kartenmanager und Nav2 waren passiv frisch,
Fahrkanäle und Motor-Sollwerte null. Das geladene R9-Profil trägt noch das
alte `scope_verified=true`, hat aber keine neue physische Bindung an den
aktuellen SLAM-Frame. Kein Realversuch und keine Fahrfreigabe. Für eine
erneute Prüfung eine motorlose, vor Ort kontrollierte VL53-Szene mit
nachgewiesenen Rückgaben beider 8×8-Raster sowie die aktuelle Startpose und
Scope-Grenze im neuen Kartenframe messen; erst danach einen eng begrenzten
Umfahr-/Stoppbefreiungsaufbau festlegen und gesondert zur Fahrt freigeben
lassen. Keine reale Wohnungsgeometrie ins Repository übernehmen.

**Rückfall:** Das neue `explore`-Overlay weglassen, aber das ältere
Kandidatenpräfix wegen seines Egg-Links nicht als eingefrorenen Rollback
ansehen. Der vor `0fe9245` geprüfte Quellstand hatte den dokumentierten
Shutdown-Race; die reale Sensorqualität sperrt beide Varianten für Fahrten.

## WE-1 Stufe 3: neuer isolierter Softwarekandidat, nicht deployt (24.09.2026)

Ausgangsstand PR #99, Branch `feature/we1-stufe3-local-recovery`,
`2914279`; Softwarecommits `785b825`, `e3d7352`, `aa699b0`.
Der neu gebaute Kandidat liegt nur unter
`/home/p/.local/share/amadeus/releases/we1-stage3-complete-1kI6en/install`.
Reihenfolge: `/opt/ros/humble` →
`/home/p/amadeus_slam_toolbox_ws/install` →
`we1-ldlidar-shutdown-overlay` → `we1-10e1858074e7-r1` →
`we1-stage1-5e3fe0a-20260923` → `we1-stage2-6fd36d5-20260923` →
`we1-stage3-bypass-s8QMY8` → diesen Kandidaten. Die neun Pakete
`robot_interfaces`, `vl53_near_field`, `robot_navigation`, `explore`,
`robot_map_manager`, `safety_monitor`, `mission_manager`, `bt_orchestrator`
und `base_hardware` wurden neu gebaut und lösen aus diesem Präfix auf.
Die Python-Pakete `explore` und `robot_navigation` sind in diesem isolierten
Kandidaten per Egg-Link auf den zugehörigen Build gebunden; Source-/Build-
Hashes stimmen überein. Dieses Entwicklungspräfix nicht blind als
unabhängig kopierbares Deployment-Image behandeln.
`bt_orchestrator` benötigte für den Build den vorhandenen separaten
`behaviortree_cpp`-CMake-Underlay unter
`we1-10e1858074e7-r1/underlay/behaviortree_cpp`; der erste Lauf ohne
diesen Pfad scheiterte. Das ist kein Robot-Deployment.

**Jetson-Wirkung bei einer künftigen bewussten Übernahme:** Die additive
`NearFieldStatus`-Schnittstelle verlangt kohärenten Neubau/Start von
Produzent und sämtlichen Verbrauchern. Ein alter Publisher meldet Qualität
0 und sperrt Fahrtor/Explorer; bei aktiviertem optionalem VL53-Safety-Notstopp
bleibt auch dieser gesetzt. Gültige Fernmessung kann eine leere Originalwolke
haben, aber nur mit gemessenem Status 5, Zielanzahl, Sigma, plausiblem
Messwert, Vollabdeckung und gleichem Stempel. Die Costmap bekommt keine
Räumstrahlen aus unbeobachteten Spalten. Safety-Timeout 0,8 s ist neu
streng, nicht gelockert. Nav2 `nav2_params_real.yaml` verfolgt im Kandidaten
0,40 m statt 0,80 m voraus und dreht ab 0,35 rad statt des RPP-Defaults;
Footprint, Padding, Collision Monitor und Geschwindigkeiten sind unverändert.
Das Fahrtor verlangt nun zusätzlich `/safety/estop=false` mit Empfangsalter
höchstens 1,0 s und frisches Basis-/Karten-TF (0,2/0,8 s). Ein allein
gestartetes `nav_real.launch.py` ohne Safety-Publisher bleibt daher bewusst
gesperrt. Der normale `robot.launch.py`- und WE-Mapping-Start enthält den
Safety-Monitor; trotzdem sind tatsächliche TF- und Statusfrequenzen motorlos
zu messen, bevor dieser Kandidat die aktive Hardwarekette ersetzen dürfte.

Der gerätefreie frühe **und** späte dauerhafte Umfahrfall A→B bestanden
auf dem finalen Kandidaten mit echter Nav2-Kette, automatischer Explorerwahl,
nachgewiesenem Kartenfortschritt und weiterlaufender Elternmission. Im
späten Fall wurde ein notwendiger Controller-Stopp vor der unverändert
stehenden Barriere gemessen; die frühere B-Stornierung wurde als Folge von
Frische-/Karten-Duplikat-Races getrennt behoben. Sensor-, Software-Not-Aus-
und TF-Ausfälle endeten gerätefrei hart ohne Wiederanfahrt. Ein Software-
Not-Aus-Diagnoselauf überschritt die anfängliche 25-mm-Prüfergrenze mit
26,3 mm; die nachgelagerte unveränderte Velocity-Smoother-Rampe erklärte
den Restweg. Der korrigierte gerätefreie Prüfer misst Gate-/Ausgangs-
Nullzeit und einen aus der bestehenden Verzögerung abgeleiteten 40-mm-
Diagnoserahmen; er ist **kein** Hardware-Not-Aus- oder Bremswegbeleg.
Die ungeprüfte
reale Sensor-/TF-Verfügbarkeit hält Stufe 3 **insgesamt** offen. Zwei
Einzel-PID-SIGINTs während eines Karten-Saves endeten sauber mit erhaltenen
Dateien; der historische `take_message()`-Zeitpunkt wurde nicht gezielt
getroffen. Kein Zielgerät, kein Gerät, kein Motor und keine echte Karte wurden
hierfür berührt. Details/Evidenzpfade stehen im maßgeblichen WE-STATUS.

**Vor Ort noch erforderlich:** Startpose und aktueller Kartenframe/Scope,
Hinderniskontur, lichte Umfahrbreiten, freier Schwenkraum, Auslauf,
Hardware-Not-Aus, passive VL53-Qualitätsverteilung beider Seiten,
motorloser Gesamtstart/-stopp. Insbesondere die reale VL53-64/64-Qualität
und die `map→odom`-/`odom→base_link`-Publikationsrate gegen die neuen
Gate-Grenzen prüfen. Erst danach und mit neuer konkreter
Vor-Ort-Freigabe ein begrenzter Realversuch. Der frühere enge Scope ohne
Frontierziel darf nicht zum Umfahrtest erweitert oder geraten werden.

**Rückfall:** Dieses Präfix in einer frischen Shell weglassen. Aktiver
Jetson-Install, bisherige Overlays und Wohnungsdaten bleiben unverändert.

## WE-1 Stufe 3: permanente Umfahrung softwaregeprüft, reale Übernahme offen (23.09.2026)

Produktionsquellstand `90379d9`, Prozessprüfer `d13a6c9` auf
`feature/we1-stufe3-local-recovery`, PR #99 weiterhin
offen. Das neue **nur gerätefrei verwendete** Install liegt unter
`/home/p/.local/share/amadeus/releases/we1-stage3-bypass-s8QMY8/install`.
Sourcereihenfolge: ROS Humble → bestätigte Stufe-1-Kette → Stufe 2 → dieses
Präfix. `ros2 pkg prefix explore` und Dateivergleich belegen das neue Paket;
Quell-/Install-SHA von `explore_node.py` jeweils
`485435a0effe6c32efd74da4995a92584d6b01dff255f2010c6e003327fb8fe0`.
Alle übrigen Pakete kommen aus den bisherigen Underlays; Nav2- und
Collision-Monitor-Konfiguration wurden bytegleich mit Stufe 1 verglichen.
Keine Roboterinstallation, kein reales Profil und kein Gerät wurden geändert.

Die echte Nav2-Kette in DDS 219 umfuhr eine stehenbleibende synthetische
Barriere mit automatisch gewähltem Explorerziel. Danach bestätigte eine neue
Rohkarte den Frontierabschluss, ein anderer automatisch gewählter Auftrag
wurde erfolgreich abgearbeitet und dieselbe Elternmission blieb aktiv.
Live-Footprint, geplante/virtuell gefahrene Kontur, Ausgänge der Schutzkette,
maximal ein Kindziel und 0 m Rückwärtsfahrt wurden überprüft. Das ist ein
Softwarebeleg, keine physische Probefahrt. Der unlösbare Gegenfall blieb ohne
Kindziel/Bewegung und endete mit erklärtem Teilstand.

**Vor realer Übernahme weiterhin offen:**

- Notwendiger Stopp mit anschließender Befreiung: frischer NavFn-Umweg
  vorhanden, Regler stoppt aber wegen vorausberechneter Costmap-Kollision.
  Keine Regler-/Sicherheitsgrenze versuchsweise ändern.
- Leere VL53-Originalwolken belegen Empfang, aber keine Messgesundheit.
  Gültige Fernmessung und ungültige Messung sind im heutigen Statusvertrag
  ununterscheidbar. Der Explorer sperrt dann lokale Recovery. Ein eindeutiger
  Sensorstempel-/Gültigkeitsvertrag mit den Verbrauchern ist gesondert nötig;
  insbesondere ist der bisherige Fahrtor-Heartbeat kein Qualitätsnachweis.
- Den bekannten Kartenmanager-SIGINT-Race klären und anschließend einen
  geeigneten motorlosen Gesamtstart/-stopp nachweisen. Dieser Folgeauftrag
  enthält keine Erlaubnis für Hardwarezugriff.
- Aktuelle Startpose/Orientierung, Barrierenkontur, lichte Alternativbreiten,
  freier Schwenkbereich und Auslauf vor Ort messen und an den aktuellen
  Kartenframe/Scope binden. Keine synthetischen Maße als reale Freigabe nutzen.
  Eine reale Fahrt braucht danach die aktuelle ausdrückliche Vor-Ort-Freigabe.

Details, feste Diagnosegeometrie und konkrete Testgrenzen stehen ausschließlich
im laufenden WE-STATUS. **Rückfall:** Neues Präfix weglassen; das vorherige
isolierte Install und der aktive Roboterstand sind unverändert vorhanden.

## WE-1 Stufe 3: neues gerätefreies Nav2-Overlay, nicht auf Antrieb übernehmen (23.09.2026)

Das zusätzliche Stage-3-`explore`-Install
`/home/p/.local/share/amadeus/releases/we1-stage3-routeblock-20260923/install`
liegt **nur isoliert** vor und wurde nicht in den aktiven Roboterstart
übernommen. Quell- und Installdatei `explore_node.py` wurden per SHA-256
verglichen (beide
`be6c8f7da787fa51a57a9bebf87cf0ee1e440a049be57f3eef7af897b6c9c6ef`).
Die Reihenfolge ist ROS Humble → bestätigte Stufe-1-Kette →
Stufe 2 → dieses Stage-3-Overlay; die Nav2-/Collision-Konfiguration kommt
unverändert aus Stufe 1. Der neue Prüfer in DDS-Domain 219 startet keinen
Hardwaretreiber und sendet keine Motorregister. Er belegte zweimal mit
echtem Nav2, Fahrtor und Collision Monitor: Hindernis → Stopp → freie
Sensorstrecke → weitere virtuelle Fahrt → Zielerfolg → Rohkartenfortschritt
→ nächstes Frontierziel. Bei dauerhaftem Hindernis verhinderte die neue
enge Nahkorridor-Klassifikation den zuvor beobachteten sofortigen
`SYSTEM_FAILURE` nach einem zweiten Nav2-Abbruch. Ein echter sicherer
Umweg blieb in zwei synthetischen Positionen aus. Eine zurückgestellte
Aufgabe bleibt bei weiter belegtem Zielkorridor auch nach neuer Costmap
gesperrt; der gerätefreie Gegenlauf blieb nach drei begrenzten Kindzielen
ohne Bewegung stehen und wartete auf eine sichere Alternative.

**Keine reale Fahrt daraus ableiten:** Der letzte motorlose reale WE-Vorlauf
hatte kein gültiges Ziel im engen Scope; das links stehende Hindernis löste
nur Slowdown, keinen Stopp aus. Der einmal beobachtete Kartenmanager-
Shutdown-Race ist weiterhin offen. Vor einem Fahrversuch müssen diese drei
Punkte motorlos geklärt sein; das Fahrtor und die Sicherheitsgrenzen bleiben
unverändert. Rückfallweg: neues Stage-3-Präfix nicht sourcen, stattdessen
das vorherige isolierte Stage-3-Kandidatenpräfix verwenden; kein automatischer
Merge oder Deploy.

## WE-1 Stufe 3: lokale Hindernisbehandlung nur teilweise belegt (23.09.2026)

**Neues physisches Hindernis links (23.09. abends), nur motorlos:** Der linke
VL53 erkannte wiederholt ~0,24–0,25 m, der rechte keinen Nahpunkt. Bei
`dry_run=true`/`allow_rs485=false` ließ der bestehende WE-Collision-Monitor
einen synthetischen Vorwärtswunsch von 0,08 m/s nur mit höchstens 0,024 m/s
durch (SlowZone), nicht mit null. Das Mapping-Profil besitzt eine
bewegungsabhängige Footprint-Approach-Zone; die ältere starre StopZone darf
hier nicht unterstellt werden. Kein Motorstrom, keine reale Bewegung und kein
Recovery-Nachweis. Den aus Dry-run resultierenden Odometrie-/Kartenstand nicht
für eine Fahrt weiterverwenden.

Der anschließende Einzel-SIGINT erzeugte bei `robot_map_manager` einen
`take_message()`-RuntimeError und Exit 1; alle anderen Kinder stoppten sauber,
alle Gerätehandles waren danach frei. Dieser Shutdown ist **nicht** als
Stufe-1-artig sauber abzunehmen. Vor einer realen Fahrt den Race klären,
frischen motorlosen Preflight mit überprüftem Fahrziel durchführen und das
Hindernis nur in einer nachweislich sicheren Testanordnung verwenden. Keine
Schwellen, Footprints oder Fahrtore abschwächen.
Ein unmittelbar folgender motorloser Wiederholungslauf ohne synthetischen
Fahrwunsch sah denselben linken Nahpunkt und stoppte alle 24 Kinder sauber,
ohne Traceback oder offene Gerätehandles. Der erste Race bleibt ungeklärt;
der zweite Lauf beweist nur, dass er nicht bei jedem Stopp auftritt.

**Nachtrag nach Vor-Ort-Freigabe (23.09.):** Auf dem Jetson bestand ein erneuter
passiver WE-Preflight mit Stufe-3-Explorer aus dem isolierten Präfix und allen
anderen WE-Paketen aus der bestätigten Stufe-1/2-Kette. Der Stack lief mit
`active_drive:=false`, realen LiDAR-/VL53-Daten, aktivem Collision Monitor und
Nav2, frischer Rohkarte/TF/Safety und Basiswerten durchgehend null. Ein
einziger SIGINT beendete 24 Kinder sauber; Gerätehandles waren danach frei.
Es wurde kein Fahrbefehl gesendet. Für einen Hindernisversuch sind Startpose,
unbelebte Barriere und sicherer Auslauf noch nicht benannt. Eine gewünschte
freie Kurzfahrt ohne Barriere ist nur ein Basis-/Fahrkettencheck, kein
Stufe-3-Nachweis und braucht eine eigene enge Bewegungsgrenze.
Für den später gewünschten freien Kurztest kam ein weiterer Blocker hinzu:
Das lokale R9-WE-Profil untersagt selbst die Wiederverwendung seiner
Scope-Koordinaten nach SLAM-Neustart. Der passive Vorlauf startete SLAM neu;
Profil-Hashgleichheit ist daher keine gültige physische Scope-Bindung. Vor
einer WE-Fahrt den begrenzten Raum im aktuellen Kartenframe neu messen und
von der anwesenden Person bestätigen lassen. Bis dahin Motoren auslassen;
keine Sicherheitsschwelle ändern oder das Fahrtor umgehen.

Nach Vor-Ort-Bestätigung des einzelnen Raums und geschlossener Ausgänge wurde
ein neues lokales Einmalprofil für einen eng begrenzten, vorwärtsgerichteten
Ein-Ziel-Test im neuen Kartenframe erstellt (Profilpfad und Hash stehen im
WE-Status). Der echte WE-/Nav2-Gesamtprozess wurde damit **nur motorlos**
gestartet: Karte/TF/LiDAR/VL53/Safety waren frisch, Basis `dry_run=true`,
`allow_rs485=false`; der Explorer fand bis zum 75-s-Gesamtbudget kein gültiges
Ziel. Kein Nav2-Fahrkommando, keine Odometriebewegung, danach sauberer Stopp
und freie Gerätehandles. Der Versuch darf nicht scharf wiederholt werden, nur
um ein Ziel zu erzwingen. Erst eine neu vor Ort vermessene Kurzroute und ihr
motorloser Scope-/Nav2-Nachweis erlauben eine reale Probefahrt.

**Ausgangsstand:** bestätigter Stufe-2-Branch bei `3fa3ce6` auf der
Stufe-1-Overlaykette mit Stufe-2-`explore` als letztem Präfix. Der neue
Themenbranch `feature/we1-stufe3-local-recovery` bei Produktionscommit
`d6c6fa9` (Review-PR #99, nicht gemergt) ändert nur Explorer-Code, sein
Profil, Tests und den vorhandenen Prozessprüfer. Der produktive
Roboterstand und die lokale Standardinstallation wurden nicht verändert.
Der einzige neue Build ist das isolierte Präfix
`~/.local/share/amadeus/releases/we1-stage3-candidate-20260923/install`;
es wurde testweise **nach** dem Stage-2-Präfix gesourct.
`ros2 pkg prefix explore`, Python-Import und Quell-/Install-Hash ordneten den
Explorer diesem Präfix zu.

Der Explorer stuft ein terminales Frontier-`ABORTED` nur bei frischer
Costmap-Hindernisevidenz, gestoppter Odometrie, frischem map-TF, LiDAR, beiden
VL53-Streams und freiem Not-Aus als `LOCAL_BLOCKED` ein. Andernfalls bleibt
es ein Systemfehler. Eine blockierte Aufgabe wird begrenzt zurückgestellt;
ein anderes geprüftes Ziel kann übernommen werden, das erste erst nach
frischer, unprojiziert freier Costmap erneut. Nav2-/Collision-Monitor-
Parameter, Footprint, Padding und Scope wurden nicht geändert; Spin und
BackUp bleiben vom Fahrpfad getrennt.

902 Explorer-Pytests und der achtteilige gerätefreie Gesamtprozessprüfer aus
dem Quellbaum sowie gegen das isolierte Install bestanden. Der Prüfer mit
Fake-Nav2 belegt Elternfortsetzung nach lokalem Kindabbruch und kontrolliertes
Warten ohne Ausweg, **nicht** die
sichere Bewegung des realen Controllers. Sein DDS-Bereich ist vom Roboterdomain
getrennt; alle synthetischen Sensoren haben eigene Testtopics. Beim damaligen
Prüflauf war der R9-Befund links (~0,24 m) noch offen; eine Motorfreigabe,
Gerätezugriff oder Fahrbefehl fand dabei nicht statt. Die inzwischen
vorliegende Vor-Ort-Bestätigung und der passive Vorlauf oben ersetzen keinen
produktionsnahen Hindernis-/Collision-Monitor-Nachweis. Bis der begrenzte
Testaufbau festgelegt und motorlos überprüft ist, darf die Stage-3-Installation
nicht als Fahrprofil verwendet werden.

**Rückfall:** Stufe-3-Präfix in einer neuen Shell auslassen; die bestätigte
Stufe-1/2-Kette bleibt unverändert. Es ist nichts auf dem Jetson zu entfernen
oder zurückzukopieren.

---

## WE-1 Stufe 2: gerätefreie Frontierfortsetzung (23.09.2026)

**Basis:** bestätigter Stufe-1-Stand `5e3fe0a` mit dessen unveränderter
Overlaykette. Der Stufe-2-Branch `feature/we1-stufe2-replan-fortsetzung`
ergänzt nur `explore` aus Produktionscommit `6fd36d5`. Isoliertes Install:
`~/.local/share/amadeus/releases/we1-stage2-6fd36d5-20260923/install`.
Es wird **nach** dem Stufe-1-Präfix gesourct; alle anderen Pakete bleiben auf
ihrem in Stufe 1 bestimmten Präfix. `ros2 pkg prefix explore`, Python-Import
und Dateihash bestätigten genau dieses neue Install. Weder die Standardkopie
`/home/p/roboter_ws/install` noch ein aktiver Roboterdienst wurden ersetzt.

Die neue gerätefreie Prozessprüfung hält Ziel A auf einer sicheren neuen
Kartenrevision und auf einem reinen Zeitstempelduplikat aktiv. Wenn A durch
eine echte belegte Zelle ungültig wird, folgt auf bestätigten Kindziel-Cancel
automatisch Ziel B. B wird erfolgreich verarbeitet und seine Frontieraufgabe
auf einer folgenden Karte abgeschlossen. Maximal ein Nav2-Kindziel war aktiv;
`max_frontier_goals=1` im Test beweist, dass der A-Quellenstopp das
Navigationsbudget nicht verbraucht. Ohne neue gültige Quelle erfolgt kein
zweiter Versand und das Elternzeitbudget beendet den Auftrag kontrolliert.
Der bestehende Sechs-Szenarien-Gesamtprozessprüfer bestand sowohl aus der
Quelle als auch gegen das installierte Overlay; 893 Explorer-Pytests bestanden
ebenfalls. Ein erster Install-Gesamtlauf hatte einen einmaligen Timeout im
älteren Wiederaufnahmefall, der isoliert und im vollständigen Wiederholungslauf
bestand. Die Ursache dieser Test-Zeitstreuung ist offen. Alle Prüfungen liefen
ohne Gerätezugriff, Motorfreigabe oder Fahrbefehl.

**Keine Fahrfreigabe:** Das ist kein realer Sensor-, Nav2- oder
Hindernis-Recovery-Test. Der linke VL53-Nahbereichsbefund aus R9 bleibt
ungeklärt. Vor einer neuen Fahrt sind Sichtprüfung oder unbestromtes
Zurücksetzen auf eine vermessene freie Pose, erreichbarer hardwired Not-Aus,
vollständiger neuer Preflight und eine neue ausdrückliche Freigabe nötig.
Weder Scope noch Collision-, Footprint-, Frische- oder Sensorgrenzen wurden
gelockert. Stufe 3 wurde nicht begonnen.

**Rückfall:** Frische Shell öffnen und das Stufe-2-Präfix nicht sourcen.
Stufe 1 bleibt unverändert; keine Geräte- oder Installationsdatei muss
zurückkopiert werden. Den älteren Explorer wegen der dokumentierten
Wiedervergabe eines erreichten Frontierziels nicht als Fahrkandidaten nutzen.

---

## WE-1 Stufe 1: reproduzierbarer motorloser Zielstand (23.09.2026)

**Geprüfter Runtime-Code:**
`5e3fe0a084b9b46809e25715d8bdca4c7bd408a4` aus PR #96 auf dem
Stufe-1-Themenbranch `fix/we1-stufe1-runtimeinventur`; dessen Dokumentation
steht als PR #97 zur Review. Der neue isolierte
Merge-Install liegt unter
`~/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923/install`.
Weder `/home/p/roboter_ws/install` noch die dortige schmutzige Arbeitskopie
wurden verändert oder als gleichwertig behauptet.

Die geprüfte Shell-Reihenfolge ist:

```bash
source /opt/ros/humble/setup.bash
source /home/p/amadeus_slam_toolbox_ws/install/setup.bash
source ~/.local/share/amadeus/releases/we1-ldlidar-shutdown-overlay/install/local_setup.bash
source ~/.local/share/amadeus/releases/we1-10e1858074e7-r1/install/local_setup.bash
source ~/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923/install/local_setup.bash
```

Danach lösen `amadeus_lidar_bringup`, `base_hardware`, `explore`,
`mission_manager`, `robot_bringup`, `robot_map_manager`, `robot_navigation`,
`safety_monitor`, `semantic_map_manager` und `vl53_near_field` aus dem neuen
Stufe-1-Präfix auf. Das sind genau alle unter `src/` seit dem Vollrelease
`10e1858` geänderten Pakete. Unveränderte Projektabhängigkeiten kommen aus dem
commitgebundenen Vollrelease; der LiDAR-Treiber kommt aus dem gepatchten
Close-after-join-Overlay, `slam_toolbox` aus seinem vorhandenen gepatchten
Arbeitspräfix. Das alte `we1-r8-scope-overlay` nicht für Stufe 1 sourcen: Es ist
ein historischer Mischstand und enthält insbesondere kein neu gebautes
`robot_navigation`.

Das verwendete lokale Profil ist
`~/.local/share/amadeus/profiles/we1-two-rooms-hall-r9-20260922.yaml`, SHA-256
`e03495cebfc22dc7d9858cb8893660b83134cf4b6121db64ee49673d0688083f`.
Seine reale Geometrie bleibt lokal. Die beiden Abnahmezyklen wurden mit
`active_drive:=false`, Domain 217 und der Loopback-CycloneDDS-Konfiguration des
Vollreleases gestartet. Keine Missions- oder Navigationsaction wurde gesendet.

Beide Zyklen bestätigten aktive Nav2- und Collision-Lifecycles, vollständige
TF-Ketten, etwa 10 Hz LiDAR, 1 Hz frische Rohkarte, je etwa 4 Hz für beide
VL53, frischen Kartenmanager- und Explorerstatus sowie Safety `false`.
`base_hardware` meldete durchgehend `dry_run=true`, `allow_rs485=false`,
`rs485_ready=false` und null Motorwerte. In den Beobachtungsfenstern gab es
null Nav2-Ziele und null nichtnullige Fahrbefehle. Beide Einzel-SIGINT-Stopps
beendeten alle Prozesse sauber; `/dev/amadeus_lidar`, `/dev/ttyUSB_BASE` und
die sichtbaren I²C-Gerätepfade blieben danach ohne Handle. Die Zykluslogs
enthalten keine Tracebacks oder Prozessabbrüche.

**Keine Fahrfreigabe:** Der frühere reale R9-Befund links vor der Endpose ist
durch diesen motorlosen Lauf weder widerlegt noch beseitigt. Vor jeder späteren
Bewegung sind Sichtprüfung oder unbestromtes Zurücksetzen auf eine vermessene
freie Pose, erreichbarer hardwired Not-Aus, kompletter neuer Preflight und eine
neue ausdrückliche Freigabe erforderlich. Sicherheits- und Frischegrenzen
bleiben unverändert. Nächster erlaubter Schritt ist nur Review des
Stufe-1-PRs; Stufe 2 wurde nicht gestartet.

**Rückfall:** Neue Shell öffnen und das Stufe-1-Präfix nicht sourcen. Es wurde
nichts in die Standardinstallation deployt, daher ist keine Roboterdatei
zurückzukopieren.

---

## WE-1: erster Realversuch sicher beendet, Scope-Fortsetzung gesperrt (21.09.2026)

Christopher bestätigte Not-Aus, freie Türen und zwei Zimmer plus Flur; Treppen,
Außenbereiche, Personen und Tiere waren ausgeschlossen. Der freigegebene Lauf
bewegte Amadeus etwa 0,466 m und endete ohne Safety-, Encoder- oder Busfehler,
aber nur mit einem Teilstand: Kartenrevisionen ersetzten fortlaufend den
Frontierkandidaten und lösten zwölf sichere Cancel/Replans aus. Es wurde kein
Portal überquert und kein natürlicher Mehrraumabschluss erreicht.

Der Explorer hält nun das gesendete Frontierziel fest und prüft genau dieses
Ziel auf jeder neuen Rohkarte erneut gegen Kartenidentität, Pose,
Hindernisabstand, Scope und Erreichbarkeit. Der motorlose Produktionslauf hielt
es von Revision 55 bis 119 aktuell; Basis blieb im Dry-run und alle
Fahrbefehle waren null. Diese Softwareevidenz ist noch keine fahrende Abnahme
der Korrektur.

Amadeus steht nach dem ersten Lauf nicht mehr an der ursprünglichen Startpose.
Ein aus der aufgezeichneten Endpose abgeleitetes lokales Profil lieferte im
motorlosen Exaktkartentest null sicher erreichbare Frontierziele innerhalb des
Scopes, obwohl sechs Ziele ohne Scope erreichbar wären. Beim zweiten aktiven
Vorlauf wurde deshalb kein Auftrag gesendet. Danach wurden alle Prozesse sauber
beendet; `/dev/ttyUSB_BASE` war frei. Der Fahrzustand war null, eine elektrische
Motorstromfreiheit wurde dabei nicht separat gemessen.

Vor dem nächsten Start ist genau eine der folgenden Vor-Ort-Aktionen nötig:

1. Roboter zur ursprünglichen markierten Startpose einschließlich Orientierung
   zurückstellen; oder
2. einen neuen zusammenhängenden Scope ab der aktuellen Pose vermessen und
   dessen Ausschluss von Treppen und Außenbereichen bestätigen.

Das Profil liegt ausschließlich unter
`~/.local/share/amadeus/profiles/we1-first-realtest-20260921.yaml`, der
vollständige Fahrbag unter
`~/.local/share/amadeus/bags/we1-real-full-20260921-2101`. Diese reale Geometrie
nicht committen. Bis zur Vor-Ort-Aktion keine weitere WE-Fahrt auslösen und den
Scope nicht aus bloßem Kartenfreiraum automatisch vergrößern. Der isolierte
Overlaystand ist nicht in die laufende Roboter-Arbeitskopie deployt.

---

## WE-1: motorloser Zielsystemcheck bestanden (21.09.2026)

**Geprüfter Stand:** PR #95, Commit
`10e1858074e738df739077aea27078d6bbef7156`, plus ausschließlich die
Footprint-Test- und Shutdownkorrekturen auf `fix/we1-target-check-blockers`.

Der WE-Releasekandidat wurde auf diesem Jetson ohne Motorfreigabe in getrennten
Installationspräfixen unter
`~/.local/share/amadeus/releases/we1-target-blockers-20260921` gebaut und
geprüft. Die
laufende, lokal geänderte Arbeitskopie `/home/p/roboter_ws` und ihr Install
wurden weder gewechselt noch ersetzt. Das LiDAR-Overlay baut den gepinnten
Vendor-Commit mit der engen seriellen Shutdownkorrektur; der Roboter-Workspace
verwendet weiterhin ein lokales BehaviorTree.CPP-Kompatibilitätspräfix für die
vorhandene ARM64-apt-Bibliothek. Rückfall: eine frische Shell verwenden und die
isolierten Overlays nicht sourcen.

Der gemeinsame Lauf mit LiDAR, beiden VL53, SLAM, Nav2, Explorer,
Kartenmanager, `collision_monitor` und Safety war unter Last stabil. Typische
Raten waren etwa 10 Hz LiDAR, je 4 Hz VL53, 1 Hz Karte, 50 Hz Odometrie und
100 Hz TF. Nav2 und `collision_monitor` waren aktiv, das Laufzeit-Footprint war
das vermessene Polygon über `/local_costmap/published_footprint`.
`base_hardware` lief ausschließlich mit `dry_run=true`; `/dev/ttyUSB_BASE`
blieb frei, Drehzahlen und Geschwindigkeiten blieben null.

Der veraltete VL53-Test prüft nun ausschließlich den bereits real abgenommenen
Polygonvertrag; Produktionskonfiguration und Footprint-Architektur blieben
unverändert. Der gepinnte LiDAR-Treiber schließt seinen seriellen Deskriptor
erst nach dem Empfangsthread-Join. VL53 und Basis behandeln einen bereits durch
SIGINT beendeten rclpy-Kontext idempotent; Fahrtor und Kartenmanager lassen
echte RuntimeErrors weiter sichtbar und ignorieren nur den Humble-
`take_message`-Fehler bei bereits beendetem Kontext.

Der vollständige Build umfasste 23 Pakete. Direkt bestanden 1.206 Tests und
registriert 1.016 Tests, jeweils ohne Fehler, Fehlschlag oder Skip. Der
Produktionsprozessprüfer bestand positiv, Fehlerpfad, Mehrraum-Rückkehr und
Speichern/Neustart/Fortsetzung mit natürlichem Abschluss und jeweils null
Fahrbefehlen.

Der echte Kartenmanager-Save unter `we1_target_recheck_20260921` sowie der
daran gebundene WE-Save bestanden ohne Durability-Warnung. Während 30 Sekunden
gemeinsamer Last entstanden null Nav2-Ziele und null Nichtnull-Befehle. Zwei
aufeinanderfolgende vollständige SIGINT-Stopps endeten danach ohne Traceback
oder Prozessabbruch; LiDAR, beide VL53, Basis und Kartenmanager wurden sauber
freigegeben. `/dev/ttyUSB_BASE`, `/dev/amadeus_lidar` und `/dev/i2c-9` waren
frei.

**MOTORLOSER WE-1-ZIELSYSTEMCHECK: BESTANDEN.** Das lokale Profil
`~/.local/share/amadeus/profiles/we1-first-realtest-20260921.yaml` ist auf
Startraum, bekannte offene Tür und einen begrenzten ersten Flurabschnitt
zugeschnitten. Reale Wohnungsgeometrie und Zustände bleiben ausschließlich
lokal. WE-Navigation, Scope-Freigabe und Portalmonitor stehen weiter auf
`false`, bis Christopher den Ausschluss von Treppen, Außenbereichen und anderen
Gefahren vor Ort bestätigt und ausdrücklich die Fahrt freigibt.

Es wurde kein Deployment vorgenommen. Keine Hardware- oder Fahrfreigabe aus
diesem Abschnitt ableiten; die nächste Aktion ist ausschließlich Christophers
Scope- und Fahrbestätigung bei erreichbarem Not-Aus.

---

## OAK-RGB-D-Transport dauerstabil und selbstheilend (26.08.2026)

**Branch:** `codex/fix-oak-semantic-stream`

Die OAK-Konfiguration liefert nun tatsaechlich 640 x 360 bei 10 Hz
(ISP-Faktor 1/3). `oak.launch.py` startet standardmaessig zwei lokale,
motorunabhaengige Prozesse:

- `oak_rectifier` publiziert `/oak/rgb/image_rect` fuer RTAB-Map ohne
  Exact-Sync zwischen Bild und der stabilen CameraInfo;
- `semantic_stream_relay` publiziert nur 2 Hz JPEG-RGB, verlustfreies
  16UC1-PNG und CameraInfo unter `/oak/semantic/...`.

Der KI-Server muss `compressed_input: true` und ausschliesslich diese drei
Semantiktopics verwenden. Direkte Serverabonnements von
`/oak/rgb/image_raw`, `/oak/rgb/image_rect` oder `/oak/stereo/image_raw` sind
nicht zulaessig. Status:

```bash
ros2 topic echo /oak/rgb/rectifier_status_json --once
ros2 topic echo /oak/semantic/stream_status_json --once
```

`ready` muss wahr sein, Bildformen muessen 640 x 360 zeigen und
`codec_errors`, `stale_rgb`, `stale_depth` muessen null bleiben. Ein Wert in
`subscription_restarts` dokumentiert einen automatisch geheilten lokalen
DDS-Endpunktstillstand und darf nicht verschwiegen werden.

Motorlose Abnahme im isolierten Overlay: OAK 33 min 49 s ohne spaeten USB-
oder Geraetefehler; Relay 17 min 31 s mit 2.068 Paaren und null Codec-/
Altersfehlern; 24 Semantik- und 7 Bring-up-Tests bestanden. Je ein gezielter
2,5-s-Ausfall von Tiefe und RGB wurde durch genau einen Endpoint-Neuaufbau
geheilt. Nach leerem RTX-Objektgedaechtnis lieferte die sichtbare Tasse eine
echte positive 3D-Pose mit Konfidenz 0,694. Keine Motor-, Nav2-, VL53- oder
Missionskomponente lief.

**Produktionsdeployment:** Commit `a2d8ccc` ist auf dem Jetson als normal
kopiertes, nicht vom temporaeren Worktree abhaengiges Colcon-Install aktiv.
Ersetzt wurden ausschliesslich `install/robot_bringup` und
`install/semantic_perception`. Der vorherige vollstaendige Paketstand liegt
lokal unter
`~/.local/share/amadeus/deploy-backups/oak-stream-a2d8ccc-predeploy/`.
Die schmutzige Haupt-Arbeitskopie wurde nicht veraendert.

Auf dem KI-Server wurde derselbe Commit normal unter Python 3.12 gebaut; dort
bestanden 24/24 Tests. Die externe Produktions-YAML nutzt jetzt nur die
komprimierten Semantiktopics. Ihr Vorgänger liegt als
`~/.config/amadeus-server/semantic_perception.yaml.pre-a2d8ccc-20260826` vor.
`amadeus-ki.service` ist aktiv und startet genau einen `llm_planner` sowie
einen `semantic_perception` aus dem Produktions-Install.

Der anschliessende Produktionsstart aus `/home/p/roboter_ws/install` meldete
nach 190 Paaren weiterhin `ready=true`, 0,052 s Publikationsalter, null stale
Frames und null Codecfehler. Der Entzerrer meldete 957/957 Bilder, null Drops
und 640 x 360. Genau ein RTX-Subscriber hing am komprimierten RGB-Topic. Eine
Tassenabfrage blieb ohne laufende Kartenlokalisierung korrekt fail-closed im
`map`-Frame. Aktiv blieben nur OAK, Entzerrer, Relay und beide KI-Server-Nodes;
Motoren, Nav2, VL53 und Missionsausfuehrung waren aus.

Rueckfall: OAK und KI-Dienst stoppen, auf dem Jetson die beiden gesicherten
Paketverzeichnisse zurueckkopieren und auf dem Server die gesicherte YAML
wiederherstellen; alternativ `semantic_relay:=false` oder Commit revertieren.

---

## OAK-Objektpose mit deutschem Servicevertrag — motorlos bestanden (25.08.2026)

**Branch:** `fix/semantic-object-prompts`

Die externe Klasse bleibt deutsch. `GetObjectPose(Tasse)` und spaeter die App
muessen nicht auf englische Begriffe umgestellt werden. Intern setzt
YOLO-World einmalig das validierte Vokabular `cup`, `bottle`,
`remote control`, `tool`, `key`. Eine unvollstaendige, leere oder doppelte
Zuordnung verhindert den Node-Start statt eine falsche Klasse zu liefern.

Die A/B-Messung auf demselben lokalen OAK-Bild ergab fuer die sichtbare Tasse
`cup=0,396`, aber fuer `Tasse=0,029` mit falscher Box. Mit dem Fix erkannte der
Server die Tasse fortlaufend und erreichte ihre gueltige Tiefe. Ohne
Lokalisierung endete die Verarbeitung korrekt am fehlenden `map`-TF. Ein
kurzzeitiger, kuenstlicher Identitaets-TF pruefte ausschliesslich die restliche
3D-Kette und lieferte `found=true`, Konfidenz 0,4048 und
`(1,621; -0,308; 0,555) m` im Testframe. Dabei liefen nur OAK, Bildanzeige,
KI-Server und der Test-TF; keine Motor-, Nav2- oder Missionsknoten. Der TF
wurde danach entfernt und der KI-Dienst neu gestartet. Die Testpose ist nicht
mehr im Gedaechtnis; ohne echten Karten-TF antwortet der Service wieder
`found=false`.

Auf Jetson/Python 3.10 und KI-Server/Python 3.12 bestehen je neun direkte
Tests, Python-Kompilierung und normaler Colcon-Build. Auf dem KI-Server keinen
`--symlink-install`-Wechsel verwenden: Die dortige Setuptools-Version lehnt
die dazu verwendeten Optionen ab. Der normale, isolierte Colcon-Install ist
der bestaetigte Deploymentpfad.

Die Live-Abnahme nutzte 640 x 360. Das bisherige 320-x-180-Nav2-Profil war
fuer Sichtkontrolle und kleine Gegenstaende unnoetig knapp; eine dauerhafte
1920-x-1080-Uebertragung ist aber noch nicht freigegeben. Hochaufloesendes RGB
und ausgerichtete Tiefe erzeugen roh eine hohe WLAN- und GPU-Last. Ein
separates Semantikprofil soll deshalb komprimierte oder bedarfsgesteuerte
Schluesselbilder messen, ohne das schlanke Navigationsprofil zu veraendern.

Wichtig fuer diesen Folgeschritt: Auch der 640-x-360-Lauf war noch kein
Dauertest. Nach 17 min 18 s meldete der Treiber erstmals `No Data` und danach
etwa alle fuenf Sekunden erneut. Am Fehlerbeginn gab es keinen Kernel-USB-
Reset oder Disconnect. Beim Beenden hing der Komponentencontainer ueber
SIGINT und SIGTERM hinaus und wurde erst durch die normale Launch-Eskalation
per SIGKILL beendet; der USB-Disconnect folgte erst dabei. Die Ursache darf
nicht geraten werden. Vor 1080p deshalb mindestens drei motorlose A/B-Laeufe:
Kamera nur lokal, Kamera plus Offboard-Subscriber ohne Inferenz und Kamera plus
Inferenz. Je Lauf Bildrate, Datenluecken, DDS-Transport, Serverlatenz und
Shutdown protokollieren. Erst danach Transport/Kompression oder Aufloesung
festlegen.

Rueckfall: Prompt-Commit revertieren, `semantic_perception` normal neu bauen
und den KI-Dienst neu starten. Ohne reale Lokalisierung keinen statischen
`map -> base_link` stehen lassen; ein solcher TF war nur fuer diesen
motorlosen Projektionstest zulaessig.

---

## Mehrraum-Uebergang — sensorisch und extern bestaetigt (18.08.2026)

**Branch:** `fix/polygon-footprint-wohnung`

Der Explorer besitzt jetzt neben normaler Frontier-Navigation eine
fail-closed Portalbehandlung fuer den real gemessenen Sonderfall, dass Nav2
eine offene Tuer wegen Inflation in zwei freie Costmap-Komponenten trennt.
Normale erreichbare Frontiers bleiben vorrangig. Eine direkte Portalbruecke
ist nur nach frischer vollbreiter LiDAR-Korridorpruefung zulaessig und wird
ueber eingefrorene LiDAR-Geometrie statt ausschliesslich ueber Radencoder
beendet. Wenn neue Scans beide Komponenten waehrend der Anfahrt verbinden,
wechselt der Explorer nun zur regulaeren Nav2-Fahrt hinter die Tuer, statt
faelschlich `portal_geometry_changed` zu melden.

Gemessener Ablauf der Realabnahme:

- erster scharfer Lauf: Portal 0,887 m2, Luecke 0,488 m, Anfahrt 0,454 m;
- nach 0,347 m Anfahrt verschmolzen beide Gebiete zu einer regulaer
  befahrbaren 2,251-m2-Costmap-Komponente; alter Zielpunkt weiterhin Kosten 90;
- nach dem Softwarefix plante Nav2 aus der neuen Startlage ein normales Ziel
  bei `(1,05, 0,05) m` deutlich hinter der Tuer;
- Nav2 meldete Erfolg, Explorer meldete `frontiers_visited=1`;
- Endwerte: Encoderpose `x=1,018 m`, `y=-0,102 m`, `yaw=0,398 rad`, beide
  Motoren 0 rpm, RS485 und Encoder ohne Fehler;
- die Live-Karte wuchs in Fahrtrichtung und die Fahrspurabdeckung erreichte
  23,70 % der aktuellen sicheren Komponente.

Der terminale Missionsstatus dieses begrenzten Laufs war danach absichtlich
`failed`: Ein nur temporaer fuer die Abnahme gesetzter +/-20-Grad-Kegel
verwarf drei seitliche Folgefrontiers. Er kam erst nach dem erfolgreich
erreichten 1,05-m-Ziel zum Tragen und ist kein Tuerfahrfehler. Das normale
Wohnungsprofil bleibt richtungsfrei (`frontier_forward_cone_half_angle_rad:
0.0`). Die temporaere Begrenzung ist nicht Teil des installierten
Produktionsprofils.

Softwareabnahme: Explorer 58/58; gesamter registrierter Bestand 165 Tests,
0 Fehler, 0 Fehlschlaege, 0 Auslassungen. Vor der Fahrt liefen LiDAR mit
10,8 Hz und beide VL53 mit 3,8 Hz; Motoren standen bei 0 rpm. Nach der Fahrt
wurde der gesamte Stack mit genau einem Ctrl-C am Launch-Elternprozess beendet.
Es laufen derzeit keine fuer diese Abnahme absichtlich gestarteten
Amadeus-Knoten. Der anwesende Beobachter bestaetigte nach dem Stillstand, dass
der Roboter die Schwelle vollstaendig verlassen und den Folgeraum real erreicht
hatte. Die aeussere Sichtpruefung stimmt damit mit Sensorik und Nav2 ueberein.

**Naechster Schritt:** Kein weiterer Schwellen-Sondertest. Mit neuer
persoenlicher Fahrfreigabe das normale, richtungsfreie Wohnungsprofil starten
und aus dem Folgeraum mehrere Frontiers bedienen lassen. Erst dieser Lauf
prueft weitere Tueren und den globalen Abschlussvertrag. Echte Karten, Fotos
und ROS-Bags bleiben lokal.

Rueckfall: `portal_crossing_enabled: false` deaktiviert die Portalbruecke,
ohne normale Frontier-Navigation zu entfernen. Vollstaendig motorlos bleibt
`active_drive:=false`.

---

## Polygon-Footprint fuer Tuerdurchgaenge — motorlos verifiziert (18.08.2026)

**Branch:** `fix/polygon-footprint-wohnung`

Der reale lokale Nav2-Footprint ist jetzt die sichere Rechteckhuelle mit den
Rohpunkten `x=-0.11..+0.31 m`, `y=+/-0.23 m` relativ zur mittigen
Antriebsachse und `footprint_padding: 0.02`. Zur Laufzeit werden daraus
`x=-0.13..+0.33 m`, `y=+/-0.25 m`. Das Chassis selbst wurde am 18.08.2026 mit
270 mm vor, 110 mm hinter der Achse und maximal 460 mm Breite gemessen. Die
bekannte VL53-Montage verlaengert die sichere Kontur vorne auf 310 mm. Der
Kartierungs-`collision_monitor` abonniert dieses Polygon auf
`/local_costmap/published_footprint`, sodass lokaler Regler und reaktive
Approach-Pruefung dieselbe Kontur verwenden.

NavFn bleibt vorerst aktiv und plant global mit `robot_radius: 0.28`; die
Explorer-Ziel- und Abdeckungsrechnung verwendet dazu eine kreisfoermige
0,28-m-Maske.
Das ist absichtlich kein Smac-Umbau. Die Entscheidung und der gestufte
Wohnungsplan stehen in `docs/WOHNUNGSERKUNDUNG_STRATEGIE.md`.

Motorlos bestaetigt:

- 33 gezielte Footprint-/Explorer-Tests bestanden;
- registrierter Paketlauf: Explorer 19/19, Navigation 31/31 und Bring-up 3/3,
  insgesamt 53 Tests ohne Fehler/Fehlschlaege/uebersprungene Tests;
- `robot_description`, `explore`, `robot_navigation`, `vl53_near_field`
  gebaut und Xacro validiert;
- vermessener Nav2-Livefootprint exakt `x=-0,13..+0,33 m`, `y=+/-0,25 m`;
- `collision_mapping_approach` identisch im `base_link`-Frame;
- globaler Radius und beide Explorer-Abstaende live jeweils 0,28 m;
- realer NavFn-Stack plante auf einer temporaeren 3-cm-Synthetikkarte einen
  geraden 1,50-m-Pfad durch eine 0,69-m-Tuer (`SUCCEEDED`, ca. 0,7 ms);
- `dry_run=true`, `allow_rs485=false`, 0 rpm;
- nach dem Test keine Amadeus-Knoten aktiv.

Die schmalste Tuer ist mit 680 mm gemessen. Gegenueber der 500 mm breiten,
gepaddingten lokalen Kontur bleiben 90 mm je Seite bei exakt mittiger Fahrt;
das globale 560-mm-Modell laesst 60 mm je Seite. Laufzeit- und NavFn-Tuertest
sind motorlos abgeschlossen. Als naechstes folgt ein einzelner beaufsichtigter
Tuerdurchgang, nicht sofort eine volle Wohnungserkundung. Arm/Greifer muessen
in Transportpose sein. Hard-Not-Aus, freie Tuer und neue persoenliche
Fahrfreigabe bleiben Pflicht.

Begrenztes Profil fuer diese Einzelabnahme:

```bash
cd /home/p/roboter_ws
AMADEUS_FAHRFREIGABE=JA bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=true enable_auto_explore:=true start_web_gui:=false \
  explore_params_overlay:=/home/p/roboter_ws/install/explore/share/explore/config/door_test_params.yaml
```

Der Befehl ist **keine dauerhafte Fahrfreigabe** und darf erst nach neuer
persoenlicher Zustimmung ausgefuehrt werden. Das Profil laesst den Rundblick
und die sichere Vorausrichtung zu, aber hoechstens ein Frontier-Nav2-Ziel,
einen Fehlversuch, keine Coverage-Fahrt und maximal 300 s. Vor dem
Explore-Kommando muessen `max_frontier_goals=1`, `coverage_enabled=false`,
der Polygon-Footprint, beide VL53-Punktwolken und 0 rpm bestaetigt sein.

Ein motorloser Profilstart zeigte einmal einen transienten Fehler beim rechten
VL53 (`VL53L5CXException: 0`). Der sofortige isolierte Wiederholungstest war
erfolgreich; beide Seiten publizierten stabil rund 3,98 Hz. Bei Wiederholung
bleibt die Mission gesperrt und der Sensorstart wird nicht uebergangen.

### Erster begrenzter Realtest und TF-Korrektur (18.08.2026)

Der erste Motorstart blieb vor jedem Auftrag stehen, weil beide Regler bei
aktivem Motor-Halt nicht auf Modbus antworteten. Nach physischem Entriegeln
wurde RS485 vollstaendig bestaetigt. Ein transient fehlgeschlagener linker
VL53-Start wurde nicht uebergangen; der isolierte Neustart lieferte auf beiden
Seiten 3,78 Hz mit maximal 0,44 s Datenluecke bei 0,8 s Fahrtorgrenze.

Der scharfe Ein-Ziel-Lauf absolvierte den Rundblick mit 360,0 Grad und die
Frontier-Vorausrichtung mit 3,0 Grad Kartenrestfehler. Genau ein Nav2-Ziel wurde
angenommen. Es war mit 30,6 Grad zur Startfront jedoch bereits das falsche,
seitliche Ziel und fuehrte nicht zur Tuer; das bestaetigten Beobachter und Log.
Die bisherige `heading_scale` war nur eine weiche Praeferenz. Nach rund 0,28 m
Fahrt brach Nav2 zusaetzlich ab, obwohl Planer, Footprint, Encoder, RS485 und
VL53 fehlerfrei waren. Im Controllerlog steht diese zweite Ursache:
`map->odom` war unter Jetson-Last mindestens 0,95 s alt;
`controller_server.failure_tolerance` betrug nur 0,5 s. Das begrenzte Profil
endete korrekt nach dem ersten Fehlversuch, 0 rpm wurde bestaetigt und alle
Knoten wurden beendet. Dieser Lauf ist **noch kein bestandener Tuerdurchgang**.

Die installierte reale Nav2-Konfiguration verwendet jetzt
`failure_tolerance: 1.5`. `velocity_smoother.velocity_timeout` bleibt 0,5 s,
damit fehlende Reglerausgaben weiterhin frueher ein Nullkommando erzeugen.
Direkt bestanden 15 Vertragspruefungen; der registrierte Paketlauf bestand
31/31 Navigationstests. Ein anschliessender Dry-run bestaetigte live 1,5 s,
0,5 s, `dry_run=true` und 0 rpm. Vor einer Wiederholung Roboter erneut vor der
Tuer ausrichten, beide VL53 pruefen und eine neue persoenliche Fahrfreigabe
einholen.

Das begrenzte Tuerprofil akzeptiert nun zusaetzlich nur Frontier-Anfahrpunkte
innerhalb von +/-20 Grad zur aktuellen Front. Ein Ziel ausserhalb dieses
Korridors kann nicht mehr durch Groesse oder Naehe gewinnen. Fehlt ein sicherer
Kandidat vor der Front, bricht die Mission vor Vorausrichtung und Translation
mit einer eindeutigen Meldung ab. Die normale Wohnungserkundung bleibt mit
Kegelwert null unveraendert. 20/20 Explorer-Tests bestanden. Im installierten
Dry-run waren der Wert `0.3490658503988659`, ein Ziel/ein Fehlversuch,
deaktivierte Coverage, 300 s, `allow_rs485=false`, 0 rpm, beide VL53 mit rund
3,5--3,9 Hz und `/scan_normiert` mit rund 10 Hz aktiv. Danach liefen keine
Amadeus-Knoten mehr.

Rueckfall: lokales/globales `robot_radius: 0.40`, Mapping-Approach-Kreis
`radius: 0.40`, Explorer `coverage_clearance_m: 0.40`, oder ohne Bewegung
`active_drive:=false`. Die TF-Aenderung kann separat mit
`controller_server.failure_tolerance: 0.5` zurueckgenommen werden; nur der
Tuerkegel mit `frontier_forward_cone_half_angle_rad: 0.0`.

---

## Adaptive App-Raumkartierung — real abgenommen (17.08.2026)

**Branch:** `feature/hybrid-erkundung-app`

Die Erkundung hat jetzt drei Phasen:

1. odometrisch kontrollierter 360-Grad-LiDAR-Rundblick;
2. Frontier-Ziele fuer noch unbekannte Kartengrenzen;
3. adaptive Abdeckungsziele in der sicher befahrbaren bekannten Flaeche.

Phase 3 verwendet die gemessene Fahrspur. Standardabschluss sind 85 % der
zusammenhaengenden, radial um 0,28 m von Wand und unbekanntem Raum freigehaltenen
Flaeche innerhalb eines 0,65-m-Korridors um diese Spur. Maximal 14
Abdeckungsziele, 150 s pro Nav2-Ziel und 1200 s Gesamtzeit begrenzen den Lauf.
Eine SLAM-Korrektur ueber 0,35 m wird nicht als gefahrene Verbindung gezaehlt.
Unterhalb des Zielwerts melden Zeitlimit oder fehlendes sicheres Ziel einen
Fehler; die App zeigt dann nicht „Karte kann gespeichert werden".

Erfolgreich bediente Frontier-Anfahrbereiche werden innerhalb 0,60 m fuer den
Rest des Laufs gesperrt. Das verhindert die real beobachtete Folge sofortiger
Nav2-Erfolge ohne Bewegung. Ein zusaetzliches Limit von 20 Frontier-Zielen
bricht eine unerwartete Wiederholung fail-closed ab.

Fuer App, Kartierung und Raumeditor gibt es jetzt genau einen gemeinsamen
Startpfad. Motorlos:

```bash
cd ~/roboter_ws
bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=false enable_auto_explore:=true
```

Beaufsichtigter Realstart, erst nach freiem Raum, erreichtem Hard-Not-Aus und
neuer ausdruecklicher Fahrfreigabe:

```bash
cd ~/roboter_ws
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=true enable_auto_explore:=true
```

Der Launch sendet keinen Auftrag. Sobald die iOS- oder Web-App mit Port 9090
verbunden ist, wird **Erkundung starten** nur bei frischem Missions-,
Not-Aus- und Explorerstatus aktiv. `/explore/status_json` aktualisiert Phase
und reale Abdeckung mit 1 Hz. Erst `map_ready_to_save:true` bestaetigt den
Abschluss der Abdeckungsstrategie; die Karte danach weiterhin visuell
pruefen und bewusst speichern.

Der Starter bricht ab, wenn Einzelstarts von `robot_map_manager`,
`semantic_map_manager`, rosbridge, Missionsmanager oder Explorer noch laufen.
Diese Terminals zuerst sauber mit Strg-C beenden; niemals den neuen
Gesamtlaunch parallel zu `robot.launch.py`, `smartphone_gui.launch.py` oder
`nav_mapping.launch.py` starten. Der Check ist erforderlich, weil passive
Kartenmanager vom allgemeinen Stillstandshelfer absichtlich erlaubt werden.

Motorlos auf dem Jetson bestaetigt: je ein Besitzer aller zentralen Knoten,
`dry_run=True`, 0 rpm, Explorer-Heartbeat, echter rosbridge-Empfang und der
vollstaendige App-Pfad `explore -> running -> cancel -> canceled`.
`map_ready_to_save` blieb beim Abbruch korrekt falsch.

Reale Abnahme am 17.08.2026: Der erste 900-s-Akkulauf erreichte 82,72 % und
lief nur in das Gesamtzeitlimit. Ein Folgelauf deckte danach eine
Frontier-Wiederholung auf und wurde sicher abgebrochen. Mit der 0,60-m-Sperre
fuhr Amadeus den 360-Grad-Rundblick und fuenf verschiedene Frontier-Ziele in
732 s. Die adaptive Zielwahl wechselte bei neu entdeckten Grenzen korrekt
zurueck in die Frontier-Phase. Abschluss: 88,30 % von 5,0706 m2 sicher
erreichbarer Flaeche, 4,4775 m2 abgedeckt, keine Frontiers offen,
`map_ready_to_save=true`, Mission erfolgreich und danach 0 rpm. Beide VL53
und der Kollisionsmonitor waren aktiv. Die lokale Sichtkontrolle zeigte eine
zusammenhaengende 3-cm-Karte ohne offensichtliche Doppelwaende; sie wurde
nicht ins Repository uebernommen.

Rueckfall: `enable_auto_explore:=false`, `active_drive:=false` oder den neuen
App-Launch nicht verwenden. `coverage_enabled:false` in
`explore_params.yaml` stellt das alte Frontier-Ende wieder her.

---

## Automatische LiDAR-Raumkartierung — real abgenommen (16.08.2026)

**Branch:** `feature/automatische-lidar-kartierung`

Der neue Ablauf besitzt zwei klar getrennte Phasen. Zuerst dreht Amadeus mit
0,12 rad/s einmal vollstaendig auf der Stelle. Der erreichte Winkel wird aus
der Encoder-Odometrie ueber den +-Pi-Uebergang akkumuliert; ein Zeitlimit,
Mindestfortschritt, Drehrichtung und der anschliessende Stillstand werden
aktiv ueberwacht. Erst danach wertet der Explorer die neue 3-cm-SLAM-Karte aus
und faehrt sichere Punkte im bekannten Freiraum vor den Grenzen zu noch
unbekannten Bereichen an. Nach jedem Ziel wird neu geplant, bis keine
ausreichend grosse sicher erreichbare Frontier mehr vorhanden oder das
zehnminuetige Gesamtlimit erreicht ist. Nach bereits erzieltem Fortschritt
gilt der erste Fall als `safe_complete`, nicht als Fahrfehler.

Der komplette Ablauf ist motorlos und real getestet. Der Dry-run erreichte
360,4 Grad, bestaetigte den Stopp, fand drei sichere Frontier-Kandidaten und
uebergab genau ein Ziel an Nav2. Der anschliessende Cancel sperrte das Fahrtor,
stornierte das Nav2-Kindziel und endete bei Nullkommando.

Im beaufsichtigten Realtest drehte Amadeus 360,2 Grad, erreichte vier sichere,
jeweils neu geplante Frontier-Ziele und beendete danach wegen der einzigen
verbliebenen, nicht sicher anfahrbaren Frontier. Ein kurz veralteter
`map->odom`-Transform wurde fail-closed gestoppt und ohne Recovery-Bewegung
begrenzt neu versucht. Die Abschlusskarte war zusammenhaengend und frei von
doppelten Waenden oder getrennten Teilkarten (195 x 221 Zellen bei 3 cm,
5,85 x 6,63 m, 16,1 m2 freie Flaeche). Diese reale Karte bleibt lokal.

Voraussetzung fuer das korrekte Verhalten ist das verifizierte LiDAR-Paar
`laser_scan_dir: true` und `tf_yaw: +1.5708`. Vorher liefen Odometrie
(-96,9 Grad) und Kartenwinkel gegeneinander; danach stimmten sie in einem
echten Teilturn mit +99,10 und +98,10 Grad ueberein. Richtung und TF nie
einzeln aendern.

Der sichere Start ist absichtlich nicht automatisch:

```bash
cd ~/roboter_ws
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_automatische_kartierung.sh \
  active_drive:=true enable_auto_explore:=true
```

Erst nach Live-Pruefung von 0 rpm, LiDAR, beiden VL53, Odometrie, SLAM-Karte,
Kollisionsmonitor und freiem Dreh-/Fahrbereich darf genau ein Explore-Auftrag
gesendet werden. Der erste echte Rundblick ist gleichzeitig ein A/B-Test fuer
die Basis: Nach 15 Sekunden muessen im Mittel mindestens 0,01 rad/s erreicht
sein. Zusaetzlich gelten acht Sekunden ohne 0,03 rad Fortschritt, falsche
Drehrichtung, veraltete Odometrie oder 210 Sekunden Gesamtzeit als sicherer
Abbruch. Die niedrige Rate beruecksichtigt die reale 2-s-Motorrampe und die
30-Prozent-SlowZone des Kollisionsmonitors.

Abbruch eines laufenden Auftrags:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
  "{data: '{\"type\":\"cancel\"}'}"
```

Danach Nullkommando und 0 rpm bestaetigen und nur den Launch-Prozess einmal
mit Strg-C beenden. Keine Prozessgruppe signalisieren. Die reale Karte erst
nach Sichtkontrolle ueber den Kartenmanager speichern; Wohnungsdaten bleiben
lokal. Rueckfall: `enable_auto_explore:=false` oder `active_drive:=false`.
Ein flaches Stromkabel kann unterhalb der Sensor-Sicht liegen; auch bei
`left=false`, `right=false`, `middle=false` ersetzt das keine Sichtkontrolle.

---

## A* und Zielfahrt mit aktivem VL53-Schutz (16.08.2026)

**Branch:** `fix/nav2-astar-vl53-zieltest`

Der reale Navfn-Planer verwendet jetzt `use_astar: true`. Die Entscheidung ist
gemessen: Dijkstra brach auf der realen 3-cm-Karte trotz zusammenhaengender
begehbarer Zellen ab; A* plante denselben Weg bei unveraendert aktiven linken
und rechten VL53-Obstacle-Layern sofort. Ein Vertragstest verriegelt A*,
`allow_unknown:false` und den erwarteten Navfn-Plugin-Typ.

Der anschliessende beaufsichtigte Realtest bestand. Beide VL53-Datenstroeme,
`collision_monitor`, Lokalisierungs-Gate, Encoder und RS485 waren bereit. Der
Kollisionsmonitor war der einzige `/cmd_vel`-Publisher zur Hardware. Die
Mission `go_to_room Arbeitszimmer` endete mit `success/angekommen`, maximal
0,100 m/s; danach Soll/Ist und beide Motoren 0 rpm, Encoder frisch, keine
Modbus-Lesefehler. Der scharfe Stack ist anschliessend beendet worden.

OAK war bewusst aus: Ihre Live-Punktwolke markierte im A/B-Test den freien
Zielbereich als praktisch unpassierbar und trennte die Costmap. Bis der
Hoehen-/Bodenfilter korrigiert und motorlos abgenommen ist, gilt als
Hinderniskette: zwei VL53 in beiden Costmaps plus zwei VL53 im
`collision_monitor`. Ein absichtlicher Hindernis-Bremstest steht noch aus.

Naechster Meilenstein ist automatische LiDAR-Kartierung. Den vorhandenen
`explore`-Knoten nicht ungeprueft real starten: Er war bislang nicht unter ROS
abgenommen; das alte Python-Erkundungsskript publiziert teilweise direkt und
ist fuer die reale Kollisionskette nicht freigegeben. Erst SLAM, Nav2,
Fahrtor, VL53 und Explorer motorlos als eine fail-closed Kette testen.

---

## Aktueller Abnahmestand: selbst lokalisieren und Raumziel erreichen (16.08.2026)

**Branch:** `feature/globale-lokalisierung`

Der aktuelle Stand erreicht das eigentliche Meilensteinziel: Amadeus startet
ohne gespeicherte oder manuell gesetzte Pose, bestimmt seine Position und
Blickrichtung stationaer aus der gespeicherten LiDAR-Karte und erreicht danach
ein karten- und revisionsgebundenes semantisches Raumziel.

Der Kaltstart verwendet nicht mehr AMCLs nativen Globaldienst. Dieser Dienst
war auf Humble bereits erreichbar, bevor AMCL zwingend eine interne Karte
hatte, und verursachte real einen Segmentation Fault (`exit code -11`). Der
Guard startet stattdessen einen kartenfesten Vollscan-Zyklus. Erst zwei
unabhaengige Treffer innerhalb 0,20 m/8 Grad duerfen `/initialpose` setzen;
AMCL muss die Pose danach bestaetigen. Karte/Basis/LiDAR, AMCL und Guard werden
in 0-/4-/7-Sekunden-Stufen gestartet, weil ein gleichzeitiger Vollstart auf
dem Jetson ausserdem einen Fast-DDS-Lifecycle-Timeout erzeugt hatte.

Reale Abnahme am 16.08.2026:

- drei motorlose Kaltstarts an derselben extern bestaetigten Pose bestanden;
- maximale Streuung 3 cm/1 Grad, zwei konsistente Scans je Start;
- Score `0,9787..0,9789`, Wandtreffer `97,36..97,50 %`, Bestenabstand
  `1,155..1,168`;
- aktiver Start erneut eindeutig: Score `0,980`, 97,22 % Wandtreffer,
  Bestenabstand 1,180; AMCL-Standardabweichung bei Freigabe
  0,140/0,138 m und 4,70 Grad;
- Nav2-Pfad vorab read-only planbar, anschliessende reale Mission
  `go_to_room Arbeitszimmer` erfolgreich;
- Karten-Endfehler 0,133 m/6,28 Grad, damit innerhalb 0,15 m/0,40 rad;
- Encoderweg 1,024 m, Fahrbefehl hoechstens 0,100 m/s;
- terminal `success/angekommen`, danach wiederholt 0 rpm und keine
  Encoder-/Modbusfehler.

Vor dem aktiven Lauf waren RS485, beide Encoder, Motorstillstand, AMCL,
Lokalisierungs-Gate, beide VL53-Datenstroeme und `collision_monitor` korrekt.
VL53 und beide Costmap-Obstacle-Layer wurden auf ausdruecklichen Wunsch nur
fuer diese beaufsichtigte Fahrt zur Laufzeit deaktiviert; OAK war aus. Im
Repository bleibt die Hinderniskette aktiv. Nach der Abnahme wurden
Missions-, Nav2-, AMCL-, LiDAR- und Motorstack beendet. Karten, Raumgeometrie
und Diagnosen liegen weiterhin nur unter `~/.local/share/amadeus/`.

Fuer den naechsten Vorfuehrstart gilt weiterhin: zuerst freie Flaeche und
Not-Aus bestaetigen, motorlos lokalisieren, `/localization/ready=true` und
0 rpm pruefen, erst danach `active_drive:=true` und genau einen frischen
Missionsmanager mit `enable_real_go_to_room:=true` starten. Mehrdeutiger Scan,
falsche Kartenbindung oder fehlendes AMCL sperren fail-closed. Rueckfall:
`enable_real_go_to_room:=false` und den Lokalisierungs-/Real-Launch nicht
starten.

---

## Zwischenstand globaler Vollscan-Gate (16.08.2026)

**Branch:** `feature/globale-lokalisierung`

AMCL hatte eine rund 1,95 m falsche Pose trotz kleiner Kovarianz als
konvergiert gemeldet. Deshalb ist der alte Vertrag ersetzt: Vor der ersten
Freigabe muss jetzt `global_scan_localizer` einen stationaeren Vollscan
eindeutig gegen die Karte abgleichen. Der Treffer ist kryptographisch an den
Kartenfingerabdruck und ueber eine neue zufaellige 128-Bit-ID an genau einen
AMCL-Global-Reset gebunden. Veraltete Statusmeldungen koennen keinen spaeteren
Start freigeben. Danach muss AMCL den Treffer innerhalb 0,30 m/12 Grad
bestaetigen; erst dann prueft der Guard wie bisher Kovarianz und stabiles
`map -> odom`.

Live-A/B am unveraenderten Standort:

- falsches AMCL: `(0,704; 0,379; -123,6 Grad)`, nur 39,6 % Scanpunkte binnen
  15 cm zur Kartenwand, Median 0,190 m;
- globaler Vollscan: bei drei Kaltstarts `x=1,245..1,305 m`, `y=-1,135 m`,
  `yaw=38..39 Grad`, Score `0,970..0,973`, Wandtreffer `97,2..98,75 %`,
  Bestenabstand `1,245..1,267`;
- finale AMCL-Pose `(1,237; -1,147; 39,4 Grad)`, unabhaengig 98,27 % binnen
  15 cm, Median 0,030 m, 90-%-Quantil 0,060 m;
- alle Laeufe motorlos mit `dry_run=true` und 0 rpm.

Normale globale Lokalisierung benoetigt damit keine Drehung und keine
Vorwaertsfahrt mehr. Start weiterhin nur ueber
`tools/kartierung/start_lidar_lokalisierung.sh`; der Matcher setzt
`/initialpose` selbst. Seine Mindestgrenzen sind Score 0,85,
Wandtrefferquote 0,85 und Bestenabstand 1,15. Ein schlechter oder
mehrdeutiger Treffer sperrt fail-closed. Diagnose:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/setup.bash
python3 tools/kartierung/globale_scan_pose.py
python3 tools/kartierung/scan_karten_abgleich.py
ros2 topic echo --full-length /localization/status_json --once
```

22 Pakettests und der Colcon-Build bestehen. Echte Karten und alle Bilder
liegen nur unter `~/.local/share/amadeus/`. Noch offen sind die persoenliche
Bestaetigung der Blickrichtung, zwei weitere deutlich getrennte motorlose
Startpositionen und danach eine beaufsichtigte reale Zielfahrt. Aus diesem
motorlosen Ergebnis folgt noch keine Fahrfreigabe. Der alte
`amcl_lokalisierungsdrehung.py` bleibt nur als Diagnosewerkzeug und ist nicht
mehr der Normalstart.

---

## Übergabestand globale Lokalisierung (15.08.2026)

**Branch:** `feature/globale-lokalisierung`

Der Roboter wurde nach dem letzten Test manuell verschoben. Das war bei
beendeten Motor-/Navigations-Stacks sicher, macht aber jede vorherige globale
Pose ungueltig. Vor der naechsten autonomen Fahrt ist deshalb eine neue
Lokalisierung erforderlich; aus diesem Dokument folgt keine Fahrfreigabe.

### Implementierter Vertrag

- `nav_localized.launch.py` startet die lokale gespeicherte Karte, den
  normalisierten STL-27L-Scan, AMCL, den `localization_guard` und den realen
  Nav2-Pfad mit genau einem dynamischen `map -> odom`-Eigentuemer.
- Der Kartenpfad ist Pflicht. Metrische und semantische Karte muessen denselben
  SHA-256-Fingerabdruck besitzen; echte Karten und Raumdaten bleiben lokal.
- Der Starthelfer prueft PGM und YAML vor ROS. Er bricht ab, wenn
  `free_thresh` die von `map_saver` als 205 geschriebenen unbekannten Zellen
  verschlucken wuerde.
- `/localization/ready` wird erstmalig nur bei hoechstens 0,20 m
  Standardabweichung in x/y, 10 Grad in yaw und hoechstens 0,08 m/5 Grad
  Bewegung von `map -> odom` im Drei-Sekunden-Fenster wahr.
- Nach Freigabe halten getrennte Hysteresen bis 0,30 m/15 Grad Kovarianz und
  0,20 m/12 Grad TF-Bewegung. Die TF-Haltegrenzen stammen aus 640 realen
  Proben mit gemessenen Maxima 0,1601 m/8,32 Grad.
- Das `cmd_vel`-Gate stoppt bei jedem Verlust der Freigabe sofort. Der
  Mission Manager verwirft eine bereits laufende Raumfahrt erst nach 0,8 s
  ununterbrochenem Verlust. Die erste Zielannahme bleibt strikt fail-closed.
- Der Lokalisierungsstatus zeigt die aktuelle TF-Fensterbewegung, die aktive
  Acquire-/Maintain-Grenze und die Gruende eines Sperruebergangs. Der
  Missionsstatus zeigt Verlustalter und Abbruchnachfrist.

### Reale Evidenz und Grenze

Die Ursache der zuvor nicht wiederholbaren Suche wurde nachtraeglich in der
Kartendatei gefunden: Das PGM enthielt 20.543 freie, 3.561 belegte und 29.320
unbekannte Zellen, doch `free_thresh: 0.25` lud alle unbekannten Zellen als
frei. Der so gespeicherte Live-Grid hatte 44,88 m² freie Flaeche statt 18,49
m² und keine unbekannte Region; AMCL suchte damit ausserhalb des realen
Zimmers. Eine lokale, geometrisch identische Version mit
`free_thresh: 0.196` erhaelt die unbekannten Zellen und ist unter dem
Fingerabdruck `528a0b020fe89624da1c55925421aecba948a13f6f27f84087725d0ad79c701f`
gespeichert. Das Overlay `Arbeitszimmer` ist lokal explizit daran gebunden.

Nach freiem Versetzen konvergierte AMCL nach einer vollstaendigen Drehung
einmal auf 0,118/0,135 m und 8,65 Grad Standardabweichung. Die folgende
`go_to_room`-Fahrt erreichte einen Punkt rund 0,03 m vor dem semantischen Ziel.
Eine 0,59-s-TF-Korrektur blieb ohne Missionsverlust; eine spaetere
2,20-s-Instabilitaet brach die Mission korrekt ab und der Motorstillstand
wurde bestaetigt.

Die reine Suchbewegung hinterliess weiterhin mehrere Winkelhypothesen. Der
entscheidende, motorlose Schritt waren standardisierte stationaere
`/request_nomotion_update`-Messungen nach dem Stop: 20 Updates reduzierten die
Streuung auf 0,095/0,118 m und 7,83 Grad und setzten `/localization/ready=true`.
Der Helfer `amcl_lokalisierungsdrehung.py` fuehrt diese Nachmessung nun selbst
aus; die 10-Grad-Grenze bleibt unveraendert. Der reale Nachweis erfolgte nach
einem Stack-Neustart am zuvor um 0,243 m veraenderten Standort mit 180,2 Grad
Drehung. Die nun zusammengefuehrte Ein-Aufruf-Variante muss beim naechsten
versetzten Start noch wiederholt werden.

Der anschliessende reale End-to-End-Test ist bestanden. Die erste Raumfahrt
wurde bei 15,69 Grad Winkelunsicherheit fail-closed abgebrochen und alle
Motorwerte gingen auf null. Nach 20 weiteren stationaeren Messungen
(0,019/0,077 m, 4,50 Grad) erreichte der erneut gesendete Auftrag das
Arbeitszimmer. Missionstatus: `success`, Phase `angekommen`; Abschluss:
0,051/0,078 m, 6,08 Grad und 0 rpm. Der TF-Endpunkt lag rund 0,148 m und
21,7 Grad vom semantischen Ziel entfernt, innerhalb der Nav2-Toleranzen
0,15 m/0,40 rad. Mehrere unabhaengige versetzte Starts fehlen noch fuer eine
statistische Wiederholbarkeitsaussage; ein kompletter versetzter Lauf ist
jedoch real belegt.

### Zustand und naechster Start

- Die Motor-/Nav2-/AMCL-/Missions-Stacks wurden nach dem bestandenen Test beendet; der
  Roboter darf aus einer alten Pose nicht autonom gestartet werden.
- VL53-Zonen und Costmap-Obstacle-Layer waren nur waehrend der beaufsichtigten
  Testlaeufe zur Laufzeit deaktiviert. Keine dauerhafte Abschaltung wurde
  eingecheckt.
- Echte Karte, semantische Daten, Bags und Diagnoserenderings bleiben lokal.
- Vor einem neuen Realtest: freie Fahrbahn und Not-Aus neu bestaetigen,
  motorlosen Preflight ausfuehren, Kartenfingerabdruck pruefen, global neu
  lokalisieren und erst bei `/localization/ready:true` ein Ziel zulassen.
- Rueckfall: `enable_real_go_to_room:=false` verwenden und den
  Lokalisierungs-/Real-Launch nicht starten.

### Abnahmeplan naechste Sitzung: mehrere Startpositionen

Ziel ist nicht ein weiterer Einzel-Erfolg, sondern eine vergleichbare
Wiederholbarkeitsmessung ohne manuell gesetzte Startpose. Drei deutlich
getrennte Startpositionen mit unterschiedlichen Anfangsrichtungen verwenden.
Vor jedem Lauf den vorherigen Launch vollstaendig beenden, den Roboter nur im
Stillstand manuell versetzen und danach denselben korrigierten
Kartenfingerabdruck pruefen.

Je Startposition wird protokolliert:

1. Startbezeichnung und ungefaehre Anfangsrichtung, aber keine Wohnungsgeometrie
   oder Kartendaten im Repository;
2. Ergebnis des motorlosen Preflights und 0-rpm-Nachweis;
3. Ergebnis des zusammengefuehrten Suchlaufs mit `--degrees 360` und
   `--forward-meters 0.25`, Anzahl stationaerer AMCL-Updates und Zeit bis
   `/localization/ready=true`;
4. x-/y-/yaw-Standardabweichung bei Freigabe und Kartenfingerabdruck;
5. terminaler Status von `go_to_room Arbeitszimmer`, eventuelle
   fail-closed-Abbrueche und Zahl notwendiger Neuauftraege;
6. TF-Abstand und Winkelfehler zum Ziel sowie Motor-/Istgeschwindigkeit nach
   dem terminalen Status.

Die Wiederholbarkeitsabnahme besteht, wenn alle drei Starts ohne manuelle
Posevorgabe lokalisieren, alle drei Raumziele innerhalb 0,15 m/0,40 rad
erreichen und nach jedem terminalen Status 0 rpm anliegt. Fuer eine
vorfuehrfertige Ein-Klick-Kette darf kein manueller Stack-Neustart oder
Neuauftrag erforderlich sein. Ein Sicherheitsabbruch ist als korrektes
Fail-closed-Verhalten zu dokumentieren, zaehlt aber nicht als bestandener
Vorführlauf.

Der Vorwaertsteil darf nur an einer Startposition mit mindestens 0,40 m
freier Bahn ausgefuehrt werden. Hardware-/Encoderfehler, falscher
Kartenfingerabdruck, fehlender LiDAR oder eine nicht schliessende Fahrtor-Kette
beenden den jeweiligen Versuch. Eine beaufsichtigte VL53-Deaktivierung bleibt
rein laufzeitbezogen und darf nicht in die persistente Konfiguration gelangen.
ROS-Bags, Karten und Raumgeometrie bleiben lokal; ins Repository kommen nur
aggregierte Messwerte und die Entscheidung bestanden/nicht bestanden.

---

## Abnahmestand reale semantische Raumfahrt (15.08.2026)

**Branch:** `feature/reale-raumfahrt`

Dieser Abschnitt ersetzt fuer neuere Stände die Aussage vom 14.08.,
`go_to_room` sei immer simuliert. Der sichere Standard ist weiterhin
Simulation; nur `enable_real_go_to_room:=true` aktiviert den getrennten
Nav2-Pfad.

### Real bestandener Vertrag

- Ein Karten- und Revisions-gebundenes semantisches Raumziel wird als
  `NavigateToPose` gesendet.
- Der verpflichtende Behavior Tree enthält keine Recovery-Manöver: kein
  automatisches Rueckwaertsfahren und kein selbststaendiges Drehen nach einem
  Fehler.
- Nav2 publiziert auf `/cmd_vel_nav_raw`. Das fail-closed
  `cmd_vel_mission_gate` gibt nur eine frische, laufende `go_to_room`-Mission
  auf `/cmd_vel_nav` frei.
- Der `velocity_smoother` arbeitet `OPEN_LOOP`; danach folgt der
  `collision_monitor`, erst dann `/cmd_vel` und `base_hardware`.
- Der Nav2-Unterzieltimeout ist 2000 ms. Die reale Unterzielannahme benoetigte
  in einem Messlauf rund 590 ms; der alte 20-ms-Wert konnte einen Fehler
  melden, bevor das Unterziel angenommen war.
- Der Fortschrittspruefer ist auf 0,10 m in 20 s gesetzt. Die alte Schwelle
  0,30 m/15 s war mit der bestaetigten 2000-ms-Hardware-Rampe unvereinbar und
  brach freie Fahrt nach rund 0,19 m ab.

Der abschliessende beaufsichtigte Bodenlauf erreichte sein Ziel nach 1,084 m
Encoderweg. Der lange Geradeausabschnitt blieb innerhalb 0,14 Grad, das finale
Einlenken innerhalb 3,28 Grad. Alle vier Stufen der Befehlskette blieben bei
maximal 0,100 m/s und 0,149 rad/s. Nach Erfolg wurden Gate, reale
Istgeschwindigkeit und beide Motoren bei null bestaetigt; es blieb kein
verwaister Nav2-Rohbefehl. Beide VL53-Datenstroeme waren frisch, Encoder und
Modbus fehlerfrei.

### Pruefung vor jeder weiteren Realfahrt

1. Roboterpose nicht aus Kartenkoordinaten raten. Der bislang abgenommene Lauf
   verwendete einen bewusst gesetzten statischen `map -> odom`-Startbezug.
2. Freie Raeder/Fahrbahn und Not-Aus bestaetigen; keine Freigabe aus diesem
   Dokument ableiten.
3. Beide VL53-Punktwolken, aktiven `collision_monitor`, frische Odometrie,
   initialisierte Encoder, RS485-Bereitschaft und 0 rpm pruefen.
4. Laufzeitparameter pruefen: `OPEN_LOOP`, 2000-ms-Nav2-Timeout und
   Fortschrittspruefer 0,10 m/20 s.
5. Während des Laufs Mission, Gate-Ausgang, Encoder-/Modbusstatus und echten
   Motorstillstand auch nach einem Terminalstatus weiter beobachten.

### Offene Grenzen und Rückfall

Die allgemeine Selbstlokalisierung nach freiem Versetzen oder Neustart ist
noch nicht abgenommen. Bis dahin ist reale Raumfahrt nur vom kontrollierten
Startbezug aus zulaessig. Der Recovery-freie Baum bricht absichtlich ab, statt
ein Hindernis autonom zu umfahren. H5 der Encoder-Odometrie und ein echter
VL53-Hindernis-Abbruch in dieser Kette bleiben offen.

Rückfall: `enable_real_go_to_room:=false` verwenden oder weglassen und den
Real-Launch nicht starten. Dann bleibt die semantische Zielaufloesung
read-only/simuliert. Karten- und Raumdaten bleiben lokal ausserhalb des
Repositories.

---

## Auftrag: manuelle semantische Räume in der Amadeus-App (14.08.2026)

**Branch:** `feature/semantic-map-editor`

**Vollständiger Vertrag:** `docs/SEMANTIC_MAP_INTEGRATION.md`

Der neue `semantic_map_manager` ist passiv: Er liest den Status des
`robot_map_manager`, speichert Raum-Polygone außerhalb des Repositories und
publiziert Metadaten. Er besitzt weder Nav2-Action noch `cmd_vel`-Publisher.
Auch `mission_manager` bereitet `go_to_room` ausschließlich als Simulation vor.
Diese Übertragung ist daher **keine Fahrfreigabe**.

### Auf Entwicklungs-Mac und Jetson geprüft

- 51 Semantik-Backend-, 38 Mission-, 15 LLM-Planer-, 51 Kartenmanager-,
  2 Bring-up- und 5 rosbridge-Mocktests: **162/162 Python-Tests bestanden**;
- 39/39 Swift-Tests und vollständiger iOS-Simulator-Build bestanden;
- Python-Kompilierung, Mypy, Flake8 `F/E9`, YAML/XML, Packaging und
  Whitespaceprüfung bestanden;
- der identische Python-Testbestand sowie der Colcon-Build der sechs Pakete
  bestanden am 14.08.2026 auf dem realen Jetson;
- physisches iPhone: signierter Build, Installation, zwei rosbridge-Sockets,
  bewusstes Kartenspeichern, Raum-Upsert auf Revision 1 und App-Neustart
  bestanden;
- Semantikmanager-Neustart stellte Revision 1 identisch wieder her;
  kontrolliertes SIGINT endet nach der gefundenen Shutdown-Korrektur sauber;
- mehr als sechs Sekunden ohne Kartenmanager sperrten den Status mit
  `ok:false`/`editable:false`; der Wiederanlauf derselben Karte stellte
  Revision 1 und den Raum `Test` ohne Datenverlust wieder her;
- ein Update mit `base_revision:0` gegen Revision 1 wurde live abgelehnt und
  ließ `current.json` unverändert;
- `go_to_room` für `Test` ergab live ausschließlich
  `simulation_only_no_navigation`; `/cmd_vel` existierte davor und danach
  nicht;
- während der gesamten Abnahme existierten weder Motor-/Nav2-Knoten noch das
  Topic `/cmd_vel`.

Die Abnahme verwendete ausschließlich die statische `testwohnung`. Eine neue
reale Wohnungskarte und jede Fahrwirkung bleiben eigene spätere Prüfungen.

### Sichere Übernahmereihenfolge

1. Arbeitskopie und Branch prüfen; unbekannte lokale Änderungen nicht
   überschreiben. Den Branch erst übernehmen, nachdem er in das Remote
   veröffentlicht wurde.
2. `AGENTS.md`, dieses Dokument und `docs/SEMANTIC_MAP_INTEGRATION.md` lesen.
3. Ohne aktive Motor-/Navigationsknoten bauen und die Offline-Verträge prüfen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select \
  robot_map_manager semantic_map_manager mission_manager llm_planner \
  semantic_perception robot_bringup
source install/setup.bash

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/semantic_map_manager \
  python3 -m unittest discover -s src/semantic_map_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/mission_manager \
  python3 -m unittest discover -s src/mission_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/llm_planner \
  python3 -m unittest discover -s src/llm_planner/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/robot_map_manager \
  python3 -m unittest discover -s src/robot_map_manager/test -v
python3 -m unittest discover -s src/robot_bringup/test -v
python3 -m unittest discover -s ios/Robotersteuerung/Tools \
  -p 'test_mock_rosbridge.py' -v
```

4. Für den ersten ROS-Vertragstest nur die beiden passiven Manager starten;
   dafür sind keine Motoren und keine Fahrt nötig:

```bash
ros2 launch robot_map_manager map_manager.launch.py
ros2 launch semantic_map_manager semantic_map_manager.launch.py
ros2 topic echo /robot_map_manager/status_json
ros2 topic echo /semantic_map/status_json
ros2 topic echo /semantic/catalog_json
```

5. Erst wenn eine echte `/map` sichtbar ist, in der App bewusst **Karte für
   Räume speichern** wählen. Die Erstbindung ist nur nach einem bestätigten
   `save_result` mit identischem SHA-256-Fingerabdruck möglich. Danach einen
   kleinen Test-Raum zeichnen, Zielpunkt strikt innerhalb setzen, speichern,
   App neu verbinden und Persistenz/Revision prüfen.
6. Prüfen, dass die Daten ausschließlich hier liegen und nicht für Git
   vorgemerkt sind:

```text
~/.local/share/amadeus/semantic_maps/<fingerprint>/current.json
~/.local/share/amadeus/semantic_maps/<fingerprint>/revisions/
```

7. Negativtests ohne Fahrt: falsche `base_revision`, Kartenwechsel und mehr als
   sechs Sekunden ausbleibender Kartenmanagerstatus müssen `editable:false`
   ergeben. `go_to_room` darf nur `simulation_only_no_navigation` melden und
   weder Nav2 noch `cmd_vel` auslösen. Ein Replay derselben `request_id` muss
   dabei Karte, Speicher, Pose, Zeit und Zähler aus dem **aktuellen** Zustand
   zeigen und darf keinen historischen Vollstatus zurückspielen.
   Zusätzlich muss der Mission-Cache nach sechs Sekunden ohne neuen
   Semantikstatus verfallen. Ein manuell angelegter Raum, ein Objekt oder ein
   Ablageziel aus einer Topic-Nachricht darf die statischen realen
   `pick_and_place`-Allowlists nicht erweitern.
8. Persistenzgrenzen sichtbar prüfen: 2.048 Revisionen/Karte, 1 GiB
   Repository und 512 MiB Freispeicherreserve sind die defensiven Defaults.
   Eine erreichte Grenze muss die neue Revision ablehnen und die letzte
   gültige Revision unverändert lesbar lassen; nichts automatisch löschen.

### Rückfallweg

- `start_semantic_map_manager:=false` lässt das Paket im Gesamt-Bring-up aus.
- `use_dynamic_catalog:=false` in Missions- und LLM-Konfiguration nutzt wieder
  ausschließlich die statischen Listen.
- Das Verzeichnis `~/.local/share/amadeus/semantic_maps/` vor einer manuellen
  Änderung sichern; der Code löscht keine Revision automatisch.
- Reale Raumfahrt bleibt gesperrt, bis VL53-/Collision-Monitor, Lokalisierung,
  Costmap-Freiraum, Planbarkeit und Abbruchpfade separat abgenommen sind.

## Abnahmestand Encoder-Odometrie (13.08.2026)

**Branch:** `fix/encoder-position-odometry` · **H0 bis H4 bestanden**

- [x] **H0** keine Knoten aktiv, `/dev/ttyUSB_BASE` frei, Worktree sauber
- [x] **H1** beide Motoren stabil per FC03 (~5 ms); `0x0011=1000`, `0x0019=0`,
      `0x0101=4000` beidseitig identisch; Position im Stillstand bitgenau
      konstant über 40 Proben
- [x] **H2** `encoder_counts_per_motor_revolution = 1000`, unabhängig gemessen:
      vorwärts 1000,8/1000,9 und rückwärts 1000,2/1000,3; Richtungsunterschied
      unter 0,07 %; vom Nutzer in beiden Richtungen mit genau 5 Radumdrehungen
      bestätigt. Gegenrechnung über die Motordrehzahl: 999,4–999,5
- [x] **H3** aufgebockt: geradeaus 0,2442 m bei 0,01° Gierwinkel, Drehung auf
      der Stelle 93,33° bei 0,0001 m Translation; null Fehler, `/odom` 16,7 Hz,
      Watchdog greift
- [x] **H4** Bodenfahrt gegen das **Lasermessgerät**: je Fahrt **+0,5 mm**
      statt +17,3 bis +20,1 mm. Zusatzfehler dreier weiterer Start-Stopp-
      Vorgänge von **+51,9 auf +3,9 mm** gesunken (−92 %). Skalenfehler
      +0,23 %, Kursabweichung +0,04° bis +0,27°
- [ ] **H5** Fehler- und Wiederanlaufpfade — offen
- [ ] `odom_*_variance` aus wiederholten Fahrten kalibrieren — offen

### Was dabei zusätzlich gefunden wurde

**Die Anfahrrampe war bis 14.08.2026 nie wirksam.** Der Antrieb weist
`accel_ms: 2500` mit
`ExceptionResponse(function_code=134, exception_code=7)` zurück; die Obergrenze
beider Rampenregister liegt bei **2000**. Ausgelesen stand in `0x001E` auf
beiden Motoren **100**. Sichtbar wurde das erst, weil dieser Branch die
Rückgabewerte der Schreibvorgänge prüft — der alte Code verschluckte den
Fehlschlag.

Die getrennte Änderung ist inzwischen real bestanden: Eingetragen sind jetzt
**2000 ms Beschleunigen**, unverändert 400 ms Bremsen und 5 rpm
Startgeschwindigkeit. Beide Antriebe bestätigten alle drei Werte. Ein
1,0-s-Bodenimpuls mit 0,12 m/s ergab 0,0439 m Encoderweg und 0,000°
Kursänderung; der Nutzer bewertete das Anfahren als „gut sanft“. Die frühere
Annahme, die Rampenzeit werde proportional zu 3000 rpm verkürzt, ist damit
widerlegt. Die anschließende manuelle LiDAR-Runde zeigte keine Verschlechterung
der Wanddicke (37,0 % vorher, 36,7 % nachher). Die offene Zimmertür macht
Fläche und Kartenausdehnung zwischen den beiden Läufen nicht vergleichbar.

**Der Nahbereichsschutz ist funktionslos.** `vl53_near_field` stirbt mit
„Kein CH341/CH34x-I2C-Bus gefunden"; der Adapter `1a86:5512` steckt, das
Kernelmodul `ch34x` fehlt. Der `collision_monitor` aktiviert sich trotzdem und
reicht ohne Sensordaten alles durch. **Vor autonomem Fahren zwingend beheben.**

**Der LiDAR-Wandvergleich taugt nicht als Kalibrierreferenz.** Bei einer Fahrt
lag er 21,5 mm neben dem Laser, bei eigener Streuung von 1,7 mm.

### Fahren mit Nahbereichsschutz

`collision_monitor` hängt als `cmd_vel_smoothed` → `cmd_vel` dazwischen. Wer
direkt auf `/cmd_vel` publiziert, umgeht ihn. Messwerkzeuge nehmen dafür
`--cmd-topic /cmd_vel_smoothed`.

---

## Auftrag: Encoderpositions-Odometrie

**Branch:** `fix/encoder-position-odometry`
**Vollständige Anleitung:** `docs/ENCODER_ODOMETRIE_FIX.md`

Dieser Branch baut auf `agent/slam-toolbox-pure-rotation-fix` auf und enthält
damit den bereits geprüften Humble-Backport und den Scan-Vereinheitlicher. Für
diesen Auftrag später **nicht** auf den Basisbranch zurückschalten.

### Branch auf dem Jetson übernehmen

```bash
cd ~/roboter_ws
git status --short --branch
git fetch origin
git switch fix/encoder-position-odometry 2>/dev/null || \
  git switch --track -c fix/encoder-position-odometry \
  origin/fix/encoder-position-odometry
git pull --ff-only
```

Bei lokalen Änderungen, einem unerwarteten Commit oder einem nicht schnellen
Vorwärtsschritt stoppen und den Zustand klären. Keine unbekannten Jetson-Dateien
überschreiben.

Der Softwarefix ist offline geprüft, aber absichtlich noch nicht fahrbereit:
`encoder_counts_per_motor_revolution: 0.0` blockiert den echten Start. Auf dem
Jetson zuerst alle Roboterknoten beenden und ausschließlich read-only messen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
python3 tools/kartierung/encoder_position_pruefen.py --confirm-stack-stopped
```

Danach die markierte Motor- oder Radumdrehung gemäß Hilfe des Werkzeugs messen,
Wortfolge, Vorzeichen, `0x0011` und `0x0101` protokollieren und erst den
bestätigten Counts-Wert eintragen. Nach H2 müssen alle drei Schutzwerte gesetzt
sein:

```yaml
encoder_counts_per_motor_revolution: <bestätigter Wert>
encoder_expected_segment: <beidseitig bestätigter Wert aus 0x0011, > 0>
encoder_expected_resolution: <beidseitig bestätigter Wert aus 0x0101, > 0>
```

`0` bei einem dieser Werte ist ausschließlich der read-only
Inbetriebnahmezustand und verriegelt den realen `encoder_position`-Modus. Ein
neuer Modbus-Client liest `0x0011`/`0x0101` erneut und startet bewusst mit einer
neuen Baseline. Anschließend gelten H0 bis H5 aus der vollständigen Anleitung.
Keine Hardwarefreigabe aus diesem Dokument ableiten.

Im laufenden Encoderpositionsmodus behält eine einzelne normale FC03-Fehlprobe
Client und Baseline. An der Transportfehlerschwelle folgen bestmöglicher
Stopp, Busfehlerstatus, Reconnect und eine neue Baseline. Stale Rückmeldung
sperrt und stoppt immer, reconnectet aber nur bei zugrunde liegendem
Transportfehler;
Python-Ausnahmen beziehungsweise unbekannte Pymodbus-API-Fehler gehen sofort in
diesen Pfad. Ein Reconnect darf daher **nicht** als kurze Lücke mit nachzuholenden
Counts bewertet werden.

Ein semantisch ungültiges Encoderpaar oder eine abweichende Treiberkonfiguration
sperrt und stoppt dagegen sofort, ohne den bestehenden Client nutzlos neu zu
verbinden. Ein unplausibles Delta wird verworfen und im Tracker kontrolliert
rebased.

`/odom` wird nur zu einem neuen gültigen Encoderpaar publiziert, mit der
Zielperiode von 0,05 s ungefähr 20 Hz. `state_json` läuft unabhängig davon im
50-Hz-Node-Takt weiter.

Der Befehlsvertrag ist ebenfalls sicherheitsrelevant: `/cmd_vel` hat Queue-Tiefe
1, NaN/Inf werden verworfen und fordern Stopp an, und der Watchdog nutzt
monotone Echtzeit. `use_sim_time: true` ist bei scharfem RS485 verboten. Ein
Motorstart erfolgt nur, wenn nach Quantisierung mindestens ein tatsächlich
schreibbarer RPM-Wert ungleich null ist.

Die vier `odom_*_variance`-Werte sind konservative Startwerte und werden erst
in H4 aus wiederholten extern referenzierten Fahrten kalibriert.

Vor Build und Tests die gepinnten seriellen Abhängigkeiten installieren.
`requirements-modbus.txt` fixiert Pymodbus 3.14.0 und Pyserial 3.5:

```bash
python3 -m pip install -r src/base_hardware/requirements-modbus.txt
```

Lokal auf dem Entwicklungs-Mac bestanden 59 Base-Hardware- und 12
Werkzeugtests. Auf dem Jetson nach dem Checkout erneut ausführen und das dortige
Ergebnis getrennt protokollieren:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/base_hardware \
  python3 -m unittest discover -s src/base_hardware/test -v
python3 -m unittest discover -s tools/kartierung \
  -p "test_encoder_position_pruefen.py" -v
```

Der CI-Workflow `.github/workflows/encoder-odometry-offline.yml` kompiliert und
prüft dieselben Python-Komponenten zusätzlich unter Ubuntu 22.04/Python 3.10.
Mac- und CI-Ergebnisse ersetzen weder den Jetson-Lauf noch die gestufte
Hardwareabnahme.

---

Der folgende Abschnitt ist nur historischer Kontext des bereits integrierten
Vorläufers. Er ist **keine zweite aktive Übergabe**. Die vollständige alte
Diagnose steht in `docs/SLAM_TOOLBOX_ROTATION_FIX.md`.

## Integrierter Vorläufer: Humble-Fix für reine Drehungen

**Historischer Basisbranch:** `agent/slam-toolbox-pure-rotation-fix`

**Basis:** `feature/stl27l-integration`, Commit `7010058`

**Ziel:** gepinntes `slam_toolbox`-Overlay unter
`~/amadeus_slam_toolbox_ws`; `/opt/ros/humble` bleibt unverändert.

### Voraussetzungen

- [ ] `AGENTS.md`, `docs/PROJECT_MEMORY.md` und
      `docs/SLAM_TOOLBOX_ROTATION_FIX.md` vollständig gelesen
- [ ] Jetson-Arbeitskopie `~/roboter_ws` sauber; unbekannte Änderungen geklärt
- [ ] kein RTAB-Map- oder alter `slam_toolbox`-Prozess aktiv
- [ ] keine Geheimnisse, echten Karten oder ROS-Bags für einen Commit vorgemerkt
- [ ] Motorstrom aus; keine Fahrfreigabe vorausgesetzt

### Einordnung im aktuellen Branch

Der aktuelle Encoderbranch enthält diesen Stand bereits. Nicht auf
`agent/slam-toolbox-pure-rotation-fix` zurückschalten. Das gepinnte Overlay darf
weiterhin nicht ungepinnt aktualisiert und `/opt/ros/humble` nicht verändert
werden.

### Source-Reihenfolge in jedem Testterminal

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/amadeus_lidar_ws/install/local_setup.bash
source ~/roboter_ws/install/local_setup.bash
```

Kontrolle:

```bash
ros2 pkg prefix slam_toolbox
```

Muss auf `~/amadeus_slam_toolbox_ws/install/slam_toolbox` zeigen.

### Abnahmestatus

Stand 12.08.2026, abgenommen auf Commit `4fe5ee3`:

- [x] Patch-Preflight (`git apply --unidiff-zero --check`) bestanden
- [x] Overlay gebaut; `colcon test` liefert allerdings **0 Tests** und ist als
      Evidenz wertlos (Testblock im Upstream auskommentiert). Ersatz: Blob-Hashes,
      Release-Build und `strings`-Gegenprobe am Binärpaket
- [x] Paketpräfix und gepinnter Humble-Commit kontrolliert
- [x] Stillstand: `dry_run=true`, `allow_rs485=false`
- [x] Stillstand: neuer Parameter `true`, keine Knotenflut, `/scan` 9,99 Hz
- [x] Synthetischer Yaw-only-Regressionstest ergänzt:
      `tools/kartierung/test_reine_drehung_synthetisch.py`, A/B 37 gegen 0
- [x] ausdrückliche Fahrfreigabe der anwesenden Person erteilt
- [x] Not-Aus in Reichweite, Fläche frei, Beobachter anwesend
- [x] 360°: mehr als null neue Posegraph-Knoten (1 → 11), Karte sichtbar ergänzt
      (freie Fläche 10,8 → 23,2 m²)
- [x] **versetzt duplizierte Wände: Ursache gefunden und behoben.** Karto
      verwarf jeden Scan mit abweichender Strahlenzahl; der STL-27L schwankt
      über 19 Werte (2145–2176). Abhilfe ist der neue Knoten
      `scan_vereinheitlichen`. A/B bei identischem Ablauf: 31 → 0 verworfene
      Scans, 10 → 41 Knoten, Nebenachse 5,39 → 3,83 m bei real 3,80 m
- [x] 40 cm Translation: weiterhin Kartenupdate (20 neue Knoten), keine
      Doppelwände, Kursabweichung +0,18°
- [ ] langsame geschlossene Runde: **noch offen.** Es ist kein Joystick
      angeschlossen (`/dev/input/js*` fehlt) und weder `collision_monitor` noch
      Nav2 laufen in `slam_lidar.launch.py`. Eine Runde durch die Wohnung darf
      deshalb nicht ferngesteuert-blind gefahren werden — der LiDAR sieht
      Schwellen, Kabel und Tischplatten grundsätzlich nicht
- [x] Testergebnis mit Datum und Commit in `docs/PROJECT_MEMORY.md` ergänzt

Diese damalige Phase-4-Freigabe gilt nicht automatisch für die neue
Encoderänderung. Im aktuellen Branch sind zuerst H0 bis H3 aus
`docs/ENCODER_ODOMETRIE_FIX.md` abzuarbeiten; jede Bewegungsphase braucht eine
neue ausdrückliche Freigabe.

### Zwei Dinge, die beim Fahren beachtet werden müssen

**Vor jedem Versuch prüfen, dass nichts mehr läuft.** `kill -INT` auf die
`ros2 launch`-PID beendet den Elternprozess, die Knoten können weiterlaufen. Am
12.08.2026 liefen dadurch zeitweise **zwei vollständige Stapel gleichzeitig** —
zwei `map->odom`-Publisher und zwei scharfe `base_hardware`-Knoten auf demselben
RS485-Bus. Die betroffene Messung war Unsinn und wurde verworfen. Nach dem
Beenden immer nachsehen, die eigene PID dabei ausnehmen:

```bash
MY=$$
ps -eo pid=,cmd= | grep -E '[l]dlidar|[a]sync_slam_toolbox|[b]ase_hardware|[s]can_vereinheitlichen' \
  | awk -v my="$MY" '$1 != my'
```

**Korrektur vom 16.08.2026:** Die folgende Messung klaerte die
Betragsabweichung, nicht das Vorzeichen. Das Werkzeug spiegelte den
LiDAR-Zuwachs vor der Regression und verdeckte damit die falsche
Treiber-Handedness. Seit dem gekoppelten Paar `laser_scan_dir: true` und
`tf_yaw: +1.5708` stimmen Odometrie (+99,10 Grad) und Kartenwinkel
(+98,10 Grad) in einem echten Teilturn ueberein.

**Die Odometrie-Betragsabweichung liegt bei -1,45 Grad je Umdrehung.** Die früher
gemeldeten −6,3° bis −6,5° waren ein Artefakt von `odometrie_drehtest.py`.
Sauber gemessen mit `tools/kartierung/odometrie_winkel_messen.py` (283
Messpunkte je Richtung, R² = 0,997): Skalenfaktor 0,99628 gegen den und 0,99564
im Uhrzeigersinn — beide Richtungen stimmen überein, also ein echter
Skalenfehler. Kein Handlungsbedarf vor Phase 4.

**Der Radradius ist neu kalibriert:** `wheel_radius_m: 0.0624`,
`wheel_separation_m: 0.3845` (vorher 0.0612 / 0.3755), aus acht Fahrten mit dem
Lasermessgerät. Verifikationsfahrt über 2,00 m innerhalb der Ablesegenauigkeit
getroffen.

**Was dabei zu beachten ist, wenn jemand die Odometrie erneut vermisst:**

1. **Kurze und lange Fahrt kombinieren.** Fester Anfahrversatz und Skalenfehler
   sind nicht trennbar, solange alle Fahrten ähnlich lang sind. 0,30 m gegen
   2,50 m funktioniert; 0,4 bis 1,0 m reicht nicht und liefert je nach
   Auswertung Radien zwischen 0,0621 und 0,0631.
2. **Lasermessgerät, nicht den LiDAR-Wandvergleich.** Der LiDAR lag bei der
   Verifikationsfahrt 24 mm daneben, bei sonst ±5 mm Streuung.
3. **Eine Winkelmessung bestimmt nur r/W**, nie die Spurweite allein. Ein
   Streckenfehler bleibt darin unsichtbar.

**Historischer Befund:** Der feste Versatz war kein Radiusfehler. Die frühere
Vermutung eines verspätet einsetzenden Ist-Drehzahlwerts ist nicht belegt;
50-Hz-Polling widerlegte eine reine Unterabtastung. Der aktuelle Encoderbranch
adressiert den Softwarepfad mit absoluten Positionsdeltas. Ob der Versatz real
verschwindet, entscheidet erst die H4-A/B-Messung.

**Keine Aktoren aktivieren, bevor alle Stillstandsprüfungen oberhalb bestanden
sind.** Ein KI-Agent darf die Fahrfreigabe nicht selbst annehmen.

### Rollback

Launch einmal sauber mit `Ctrl-C` beenden. Dann eine frische Shell verwenden
und das Overlay nicht sourcen:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 pkg prefix slam_toolbox
```

Das Präfix muss wieder `/opt/ros/humble` sein. Der Overlay-Ordner bleibt zur
Analyse erhalten; keine Datenlöschung ist erforderlich.

## 2026-09-26 — Parity-Reset / WE-Realtest-Kandidat

Auf dem Jetson wurde in dieser Arbeit nichts gestartet und kein Aktor bestromt.
Es erfolgte kein Wohnungserkundungslauf. Die vorbereitete Software liegt in der
separaten Arbeitskopie `/home/p/roboter_ws-parity-reset`, Branch
`feature/parity-reset`; sie ist nicht automatisch der maßgebliche Baum
`~/roboter_ws` und wurde nicht übertragen.

Vor einem beaufsichtigten Test den vollständigen Diff und den tatsächlich
freigegebenen Arbeitsbaum prüfen. Danach die bestehenden Live-Prüfungen dieses
Protokolls ausführen: keine Altprozesse, Start bei 0 rpm, HWT-/Encoder- und
beide VL53-Daten frisch, Karten-/Scope-Bindung korrekt, Collision-Monitor-
Kette aktiv, Türbereich frei und Not-Aus erreichbar. Bewegung nur nach
separater ausdrücklicher Freigabe der anwesenden Person. Der Kandidat begrenzt
auf 900 s, höchstens einen Portalwechsel und sechs Abdeckungsziele; die aktive
WE-Ziel-/Cancel-/Fahrhierarchie bleibt gesperrt.

Rückfall: den vorherigen PR-#101-Head
`40b5b49c9a92600484a0dc85c466930bc1680c60` wiederherstellen. Nicht pauschal auf
`1d91229` zurückgehen, da dadurch spätere Hardware- und Sicherheitskorrekturen
verloren gehen könnten. Siehe `docs/WE_PARITY_RESET.md`.

## 2026-09-27 — Recovery-Abnahmeprofil nur im isolierten Software-Overlay

`hwt601_recovery_acceptance_params.yaml` liegt derzeit allein im temporären
Overlay `/tmp/we1-hwt-recovery-install/share/explore/config/`. Das aktive
Jetson-Install wurde nicht gewechselt. `hwt601_parity_params.yaml` bleibt
WE-Navigation-aus; erst das explizite Abnahmeprofil erreicht den neuen
HWT-HOLD-/Recovery-/Resume-Zweig. Ein isolierter Softwarestart über Mission
Manager, echten BT und Explorer gelang; dabei wurde weder ein Motor- noch
ein Hardware-Sensorprozess gestartet. Anschließend bestand ein isolierter
ROS-Graph-Test mit synthetischen Sensoren, TF, Costmap und Nav2-Gegenstelle:
HWT-HOLD, terminales Kind, Stillstand, Gate-ACK und neues Kind für denselben
Test-Task sowie getrennter Rundblick-HOLD ohne Kind. Die Karten-Task-Auswahl
war ein Testadapter; die gesonderte reale Abnahme fehlt. Keine Fahr- oder
Deploymentfreigabe.

Vor einem späteren Realtest Quell-Commit, installierte Paketpräfixe,
Profilpfad/Hash, Underlay-Reihenfolge und einzigen Hardwarebesitzer mit dem
Runtime-Manifest festhalten. Rückfall bleibt der fail-closed PR-#104-Kandidat;
kein aktiver Installwechsel folgt aus dieser Übergabe.


## 28.09.2026 – PR #105: lokaler WE-Vorwärtskandidat und beendete Vorläufe

Software `6429bd6`: ausschließlich Explore zusätzlich unter
`~/.local/share/amadeus/tests/hwt-child-route150-20260928/forward-install/`
gebaut. Temporäre Shellreihenfolge: bisheriges `hwt-portal-repair-20260928/`
`runtime-env.sh`, danach dieses `forward-install/local_setup.bash`.
Kein dauerhaftes Setup oder aktiver Install gewechselt. HWT-Schatten/Core/Health/
Guard weiter aus dem korrigierten `hwt-portal-repair-20260928/install`.
`forward-loaded-modules.json` und die Laufmanifeste dokumentieren Auflösung/Hashes.
Für den aktiven MM→BT→WE-Pfad sind `active_drive=true` UND
`enable_auto_explore=true` erforderlich; letzteres startet noch keine Mission.
Der motorlose Sensorpfad verwendet `active_drive=false`. Lokale Scope-/Profil-
Daten und alle Bags bleiben unter dem Testverzeichnis. Das Repo-Produktprofil
ist unverändert. Letzte motorlose Vorläufe nach separater Bestätigung gesperrter
Motorendstufe bei erreichbaren FC03-Encodern; aktueller Ergebnisstand und offene
Bedingungen stehen ausschließlich in WE-STATUS Abschnitt 7.

Recorder-Zusatz: `ros2 bag record --include-hidden-topics` ist für die explizit
aufgelisteten Nav2-Action-Themen notwendig (isolierte Gegenprobe 0 vs 73
Statusnachrichten). Vergangene Goal-UUID/Terminalfolge liegt im Controllerlog,
nicht im Real-Bag. Abschaltfaults und tatsächlichen Vorlauf-FC03-Zeitüberlauf
getrennt behandeln, siehe WE-STATUS. Zum Abschluss keine Roboterknoten oder
Portbesitzer mehr; alle sieben Aufzeichnungen ohne Fahrkommando/Translation.


## 29.09.2026 – Schritt-3-Produktprofil motorlos geprüft

Aktueller Auftrag gemäß WE-STATUS: normale A/B/C-Kernabnahme, keine
HWT-Fault-Injection und keine lokalen Kindziel-Sonderlimits. Dieselbe temporäre
Overlayreihenfolge wie am 28.09.; kein Installwechsel. Byteidentische lokale
Kopie des Repository-Recoveryprofils, SHA `ee3b42ee…`; Quellen-/Karten-/TF-
Vorlauf mit `active_drive=false` bestanden. Belege unter
`~/.local/share/amadeus/tests/stage3-core-20260929/`. Alle Prozesse danach
geordnet beendet; kein Fahrbefehl. Aktuelle Fahrt noch nicht durchgeführt.
Das Profil aktiviert WE und Portalwahl, aber nicht den separaten WE-
Portalmonitor; dessen Zuordnung und Live-Scope müssen für Phase C belegt sein.


## 29.09.2026 – reale Starts A1–A3 und temporärer korrigierter Explore-Install

Aktueller funktionaler Commit `872f6a8`: im betroffenen Drehpfad zuerst
Odometrie-Snapshot, dann Prüfzeit; abgelaufene Scan-/Prealignment-Pausen
auf null Restwartezeit begrenzt. Keine Parameter- oder Schutzlockerung.
Temporäre Shell: bisheriges `stage3-core-20260929/runtime-env.sh`, danach
`stage3-core-20260929/pause-install/local_setup.bash`. Bytegleichheit
Quelle/geladenes Modul und Runtime-Manifest geprüft. Kein aktiver Installwechsel.
161 gezielte Tests, Build und motorlose Vorläufe bestanden. A3 endete sicher
an `initial_scan_too_slow`, kein Nav2-Kind; alle Prozesse beendet. Letzte
explizite Motorsperrenstellung vor den Fahrten: vom Nutzer kontrolliert gelöst
(„erledigt“). Erneutes Sperren nach A3 angefordert, noch unbestätigt. Keine
Stellung aus Software-Nullkommando ableiten. Nächster Auftrag im WE-STATUS.


## 29.09.2026 – A-Produktlauf und temporäres HWT-Callback-Overlay

Nach bestätigter aktueller Motorsperrenstellung „kontrolliert frei“ bestanden
passiver und aktiver Preflight mit realen Quellen, Karte/TF und Stillstand.
Produktstart über Mission Manager → BT → WE → Nav2: Initialscan fertig,
autonome Kindziele angenommen, ca. 0,088 m zusätzliche kumulierte Odometrie-
Translation in der Kindzielphase. Vor Zielerreichung trat ein terminaler
HWT-Health-Erstfehler auf; Originalwerte und Auswertung im WE-STATUS Abschnitt 7
und lokal unter `stage3-core-20260929/autonomous-goal-run-resumed/`.
Nav2-Kinder wurden gecancelt, Endkommando null; Stack und Recorder beendet,
keine Roboterknoten mehr. A/B/C noch offen.

Fix `513af02`: überholten gültigen Callback nicht über eine bereits neuere
gültige Roh-/Yaw-/Radprobe schreiben. Später eintretende Zeitrückläufe und
ungültige Proben bleiben terminal. Keine Frische-, HWT-, Motor- oder
Kollisionsgrenzen verändert. 157 Pakettests bestanden; isolierter Install
`~/.local/share/amadeus/tests/stage3-core-20260929/hwt-callback-order-install/`
enthält den zur Quelle bytegleichen Health-Code, SHA-256 `8055fa44…`.
Für einen späteren Test nur als letztes Overlay nach
`autonomous-goal-run-resumed/runtime-env.sh` sourcen; aktiver Install nicht
gewechselt. Nach Codeänderung zuerst mit unabhängiger Motorsperre motorlos
prüfen. Die aktuelle Schalterstellung nach diesem Lauf wurde eigens angefragt
und darf nicht aus dem Endkommando abgeleitet werden.


### 29.09.2026 – gezielte aktive Kartenübergabe

PR #105: aktiver fester Frontierpunkt wird nach exaktem Rohkarten-/Statusjoin
unabhängig vom mehrsekündigen Aufgabenworker erneut geprüft. Fristen und
Schutzparameter unverändert. Vor/nach-Produktgraph bestätigt Bestandserhalt
des einen autonomen Kindes; 244 gezielte Tests und isolierter Explore-Build.
Neues temporäres Overlay lokal unter
`~/.local/share/amadeus/tests/stage3-map-handoff-20260929/install`.
Kein Wechsel von `~/roboter_ws/install`; Rückfall durch Weglassen dieses
letzten Overlays. Reale Quellen-, Profil- und Scopebindung vor Fahrt erforderlich.
Laufender Ergebnisstand ausschließlich im WE-STATUS Abschnitt 7.


29.09.2026, tatsächlicher Folgelauf `492ef20`: temporäres `join-install`
als letztes Overlay, aktive Installation unverändert. Quellen-/Profilmanifest
und geladene Modulhashes unter `stage3-map-handoff-20260929/real-repeat`.
Ein autonomes Kind ohne Kartenquellen-/HWT-Abbruch, aber Zieltimeout bei
belegter SlowZone-Verlangsamung. Kein Raumübergang. Abschließend RPM null,
Odometrie still, Kind terminal, alle Prozesse und seriellen Ports frei.
SLAM-Shutdown Exit -6 gesondert dokumentiert, Bag vollständig. Nächster
begrenzter Befundabgleich in WE-STATUS §7; keine weitere Fahrt gestartet.


## 01.10.2026 – temporärer Mast-/Encoder-Kandidat, gemeinsamer Vorlauf negativ

Unabhängiger Checkout `~/roboter_worktrees/metric-exploration-20260930`, bestehender
Branch/PR #105. Funktionaler Kandidat `8be0709`; Hauptkopie `~/roboter_ws`
unverändert sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`.
Kein dauerhafter Install-/Autostartwechsel. Privates temporäres Achtpaketpräfix:
`~/.local/share/amadeus/tests/metric-start-encoder-20260930/install`.
Runtime sourced ausschließlich über dortiges `runtime-env.sh`: dokumentierte
bisherige HWT-/Nav-/SLAM-/LiDAR-Unterlage, danach dieses lokale Overlay.
Module und tatsächliche Parameter-/Launchdateien gehasht und bytegleich geprüft.
Aktiver Basistreiber/Encoderodometrie unverändert zur Unterlage; kein aktiver
Busbesitzer im Vorlauf. Passiver Reader allein auf Basisbus; native Mastmaske
und Montage-TF erhalten. Reader startet im passiven HWT-Launch 15 s später,
Gate verarbeitet passive Quellen in eigener Callbackgruppe mit zweitem Thread.

Letzter Launch: `app_mapping.launch.py active_drive:=false
use_hwt601_odometry:=true operator_stationary_confirmed:=true
enable_auto_explore:=false start_web_gui:=false` mit zunächst ungebundenem
metrischem Bootstrapprofil. Nach aktueller LAB-1-Karten-/Posebindung eigener
metrischer Explorer, keine Mission. Kein elektrischer Motorstromzustand aus
Software behauptet. Reale Scans/TF belegen bestehende Mastmaske; tatsächlicher
SLAM-Präfix gepatchtes `~/amadeus_slam_toolbox_ws/install/slam_toolbox`,
`check_min_dist_and_heading_precisely=true` live. Historische Buildanweisungen
wurden nicht zur Installation ausgeführt.

Gemeinsamer Vorlauf weiterhin negativ: rohe/gepaddete Start-/Drehkontur
unzulässig und Gate später `wheel_missing_stale_or_invalid` terminal, obwohl
Reader ready/fehlerfrei. Keine Grenzlockerung oder Fault-Löschung. 0 Missionen,
0 Nav2-Kinder, Befehle null. Alle manifestierten Prozesse geordnet durch
SIGINT ausschließlich an Launchwurzeln beendet; Gerätebesitzer frei,
anschließend 12 frische FC03-Paare je 0 rpm / Position 0. Keine Shutdownfehler;
Bootstrap-Scope-Exit separat. Privat: `metric-start-encoder-20260930/common-gatefix`
mit geschlossener Bag, Manifest/Modulhashes/Scan- und Zellklassennachweis,
Zeitverteilungen und Shutdownprüfung. Originalfehlerläufe bleiben erhalten.

Rückfall: ohne Mission geordnet stoppen und letztes temporäres Overlay weglassen;
`active_drive=false`, `enable_auto_explore=false`. Bei langer Kontinuitätslücke
neue belegte stationäre Initialisierung mit neuem Karten-/Odometriebezug statt
Latch-Reset. Reale Erkundung erst nach gleichzeitig gültigem gemeinsamen
Startnachweis laut einzigem WE-STATUS, keine automatische Wiederanfahrt.


## 01.10.2026 – temporärer Entscheider-/Startgeometriekandidat, keine reale Mission

Funktionsstand `8f5eeb4`, unabhängiger Checkout im bestehenden Branch/PR #105.
`~/roboter_ws` sauber/unverändert `23928d92f411473ed2644692a04aebdff0ffe803`.
Exakte finale Runtime über
`~/.local/share/amadeus/tests/metric-gate-start-20261001/final-runtime-env.sh`:
dokumentierte vorherige Unterlage, Vierpaketpräfix dort `install/`, danach
Zweipaketpräfix `decision-take-overlay/install/` nur für robot_navigation und
robot_state_estimation. Explore/base_hardware aus Vierpaketpräfix;
mission_manager/robot_map_manager/amadeus_lidar_bringup aus
`metric-start-encoder-20260930/install`, BT aus `hwt-child-scope-20260928-retry`,
SLAM aus `~/amadeus_slam_toolbox_ws/install/slam_toolbox`, LiDAR aus
`releases/we1-ldlidar-shutdown-overlay/install`. Aufgelöste Präfixe, geladene
Parameterdateien, Prozesse und Modulhashes im finalen `decision-take-common/`.
Alle geänderten Modulbytes mit tatsächlich aufgelöster Installation abgeglichen.
Kein permanenter Install-/Autostartwechsel, keine Montage-/Kalibrierungsänderung.

Real nur `app_mapping.launch.py active_drive=false use_hwt601_odometry=true
operator_stationary_confirmed=true enable_auto_explore=false start_web_gui=false`
mit metrischem Bootstrapprofil; im selben Start neue lokale LAB-1-Kartenbindung,
vorhandene `explore.launch.py` mit metrischem Produktprofil und passivem HWT.
Ein passiver Reader am Basisbus, kein aktiver Basistreiber, keine Mission.
Passive Quelle eigene Radgruppe/dritter Thread und geschützter echter DDS-Take
vor Entscheidung; Befehl/ESTOP seriell, aktive Quellenscheduling unverändert.
120-ms-Paar-/180-ms-Lückengrenze und Mast-NaN/CCW/TF erhalten; SLAM-Patch live true.

Finales 720-s-Fenster negativ: zwei echte HWT-Recoveries, dann echte
120,874-ms-Paarverletzung, Gate 212,127 ms alte letzte zulässige Radprobe.
Echte Stale-Sperre erhalten. Gleichzeitig voller initialerSweep 211 unbekannte
Zellen / 0,188420 m² außerhalb Körper, Costmap 139 Zellen vollständig darin. Keine
künstliche Freigabe, keine weiteren Starts/Fahrten. Software: 1.469 Regressionen
bestanden; voller synthetischer2π-Dauerlauf separat negativ, keine Abnahme.
Ende: alle manifestierten Wurzeln einzeln SIGINT, keine Prozessgruppensignale;
Gerätehandles frei,12 frische FC03-Endpaare je 0 rpm / Position 0. Elektrischen
Motorstromzustand nicht aus Software behaupten. Private ClosedBag-/Timing- und
Endzustandsnachweise lokal, keine privaten Berichts-Vorfahren veröffentlicht.

Rückfall: geordnet ohne Mission stoppen und Zweipaket-/Vierpaketoverlay weglassen,
`active_drive=false`, `enable_auto_explore=false`. Echter Kontinuitätsverlust
benötigt neue belegte stationäre Initialisierung/Karte-Posezuordnung, kein
Latch-Reset. Reale Startfähigkeit nicht vollständig geschlossen: vorhandenen
FC03-Pfad innerhalb 120/180 ms absichern und exakt fehlende Außenfläche durch
separat hergestellte stationäre LiDAR-Sicht belegen; notwendiges manuelles
Umsetzen bei deaktivierten Antrieben liegt außerhalb Softwarepakets. Kein Merge
oder automatische Weiterfahrt, Stufe 3 offen.

## 01.10.2026 – adaptiver/Encoder-Kandidat isoliert geprüft, System bleibt an

Ausgang `d9894d2`, funktional `fd883fd`, bestehende PR #105. Kein permanenter
Install-, Autostart- oder Kalibrierungswechsel. Hauptkopie sauber/unverändert
`23928d92f411473ed2644692a04aebdff0ffe803`. Gemeinsame Encoderlogik betrifft
passiven FC03-Reader und aktive Basis ausschließlich im HWT-Pfad; dessen
unveränderlicher Startparameter `encoder_timing_recovery_enabled=true`,
Stale-/Kontinuitätsgrenze 180 ms. Außerhalb HWT bleibt dieser Parameter false.
Messwertgrenze 120 ms, Readerdiagnose 2 s / zwei Versuche, Consumer-HOLD 5 s /
zwei Recoveries je Quellenklasse. Hardfault/ESTOP/Cancel unverändert hart.
Aktiven Basisadapter gerätefrei geprüft; im jetzigen Realfenster lief er nicht.

Finale temporäre Runtime:
`~/.local/share/amadeus/tests/metric-adaptive-start-20261001/runtime-env.sh`
sourct bisheriges `metric-gate-start-20261001/final-runtime-env.sh`, dann
neuen kopierten Fünfpaketinstall `metric-adaptive-start-20261001/install/`:
base_hardware, explore, robot_navigation, robot_state_estimation,
amadeus_lidar_bringup. Mission-/Kartenpakete weiterhin aus
`metric-start-encoder-20260930/install`, BT aus `hwt-child-scope-20260928-retry`,
SLAM aus `~/amadeus_slam_toolbox_ws/install/slam_toolbox`, LiDAR aus
`releases/we1-ldlidar-shutdown-overlay/install`. Zehn geänderte Laufzeitartefakte
bytegleich zu den tatsächlichen aufgelösten Präfixen (`build-identity.json`).
1.493 Regressionen und Fünfpaketbuild erfolgreich; vollständige synthetische
2π-Dauerprobe separat negativ, nicht aus positiven kurzen Fällen abgenommen.
Nachträglich ausschließlich Testsammlung für Offline-CI ohne ROS korrigiert:
118 Offlinefälle/63 Subtests und zwölf Werkzeugtests bestanden, zwei echte
ROS-Abhängigkeitsskips; drei betroffene Fälle unter ROS erneut bestanden.
Keine Produktbytes nach dem Realfenster geändert, kein erneuter Stackstart.

Realer Start ausschließlich `app_mapping.launch.py active_drive=false
use_hwt601_odometry=true operator_stationary_confirmed=true
enable_auto_explore=false start_web_gui=false` mit privatem metrischem
Bootstrapprofil; Scope-/Sessionbindung aus aktueller LAB-1-Karte/Pose, dann
alleiniger gebundener Explorer über vorhandenes `explore.launch.py` im selben
Stack. Produktprofil live `metric_frontier`/`adaptive`, Scan true, 900/150 s,
6 Versuche/3 Fehler. Nav2-RPP genau FollowPath mit Rotation 0,35 rad, festem
Lookahead 0,40 m, Interpolation/Kollisionsprüfung true und ohne Rückwärtsfahrt;
SimpleGoalChecker 0,15 m / 0,40 rad. Insgesamt 13 Typ-/Wert-/Pluginparameter
bestätigt. Native Bibliothek/aufgelöste Module/geladene Paramfiles und Prozesse
in `common/` manifestiert. Montage-TF/Mast-NaN unverändert, SLAM-Patch live true.

720,016-s-Messfenster negativ: zwei echte HWT-Recoveries, dritte Rawstörung
bei 583,261 s `hwt_recovery_attempt_limit`; Readerfehlertext
`Zeitueberschreitung nach 0/14 Bytes`, kein bewiesener Geräte-/Kabeldefekt.
Encoderreader zum Fensterende 13.921 gültige Paare, keine Timing-Recovery,
größtes Paar 108,118 ms, Baseline eins/Rebase null. Unabhängig davon 33
unbekannte Startkonturzellen / 0,021089 m² Außenanteil, null zulässige adaptive
Kandidaten. Keine unbenutzte Vollsweepfläche als Bewegungsbedingung und keine
manuelle Vorbereitung als Bootstrap. **Keine Mission/kein aktiver Buswechsel.**

Messprobe stoppt bei 720 s; rein lesende Sensorprozesse liefen für abschließenden
Snapshot/geordneten Stopp 185,994 s weiter. Kein zweiter Start; dieser Nachlauf
gehört nicht zum 720-s-Erfolgsnachweis. Geschlossene Bag erst nach Recorderende
analysiert: keine running-Mission, keine Navigate-Statuseinträge, alle Befehle
null. Wurzeln einzeln SIGINT, keine Prozessgruppe; sämtliche manifestierten
Kinder beendet, `/dev/ttyUSB_BASE` und `/dev/ttyUSB_HWT601` ohne Besitzer.
Anschließend zwölf frische FC03-Paare Position 0 / 0 RPM; elektrische
Motorstromstellung nicht aus diesen Werten behauptet. `end-state-proof.json`
mit Originalsourcen/Endzustand und `end-encoder.json` (JSONL) privat.

Rückfall: ohne Mission geordnet stoppen und neues Fünfpaketoverlay weglassen;
voriger Kandidat hat seine dokumentierten Quellen-/Geometriegrenzen weiterhin.
Sicherer Betriebsstart `active_drive=false`, `enable_auto_explore=false`.
Kein Latch-Reset/automatischer Rebase bei echter Kontinuitätslücke; neue echte
stationäre Initialisierung/Karte-Posezuordnung nötig. Keine weitere Startserie,
kein Merge/Force-Push/private Daten oder private Berichts-Vorfahren. Details
im einzigen aktuellen WE-STATUS und AGENTENAUFTRAG §10. **Stufe 3 offen;
System eingeschaltet, keine geplante Abschaltung.**
