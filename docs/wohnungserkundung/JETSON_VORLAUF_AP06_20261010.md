# AP-06 – separater Jetson-Build und passiver Vorlauf, 10.10.2026

**Letzter Stand, erste reale Fahrt vorbereitet:** Neue ausdrückliche Laborfreigabe
erhalten; aktive Basis zweimal im Stillstand geprüft. Kein Bewegungsauftrag
gesendet, alle gemessenen Encoderpositionen/RPM und aufgezeichneten Kommandos
null. Bereichswerkzeug und Startreihenfolge separat verbessert, 181 Tests grün.
Aktive Encoderkontinuität bleibt verletzt; keine positive Fahrabnahme. Details
im letzten Nachtrag dieses Berichts.

**Aktueller Nachtrag:** Historischer VL53-Health-Vertrag bestätigt; gezielter
Encoder-Publikationspatch separat gebaut und zweimal drei Minuten passiv
gemessen. Zweiter Lauf ohne Leserfehler, Endzustand Quellen bereit; erster
Patchlauf mit realem Paarzeitverstoß. Recorder-Zustellspitzen bleiben offen.
Details und Gegenbelege im Nachtrag unten; keine Gesamtfreigabe.

**Ursprünglicher Vorlauf:** ARM-Build ausgeführt, zwei passive Aufnahmen von jeweils drei
Minuten abgeschlossen. Quellen-/Scopebereitschaft **nicht bestanden**:
Encoderkontinuität verriegelt, erster HWT-Lauf mit Transportfehler,
Scopevorbereitung in beiden Läufen an TF-Zeitprüfung abgebrochen.
Nahbereich liefert gesunde PARTIAL-Frames ohne Nahhindernispunkte; dies ist
gemäß dem Vertrag vom 25.09. kein eigenständiger Sensorfehler. Keine Mission/Fahrt,
kein Aktorschreibprozess, kein dauerhafter Installwechsel. Die ursprüngliche
AP-06-Gesamtqualifikation bleibt 0/3; kein Kundenrelease.

## Auftrag und tatsächlich geprüfter Stand

MASTERPLAN v1.3 / AP-06 im bestehenden WE-Rahmen und LAB-1. Auftrag war der
separate Build und passive Quellen-/Sichtnachweis nach
[JETSON_KONZEPTTEST_AP06](JETSON_KONZEPTTEST_AP06.md), keine Produktkorrektur
und kein bewegter Versuch. Der spätere ausdrückliche Reparaturauftrag anhand
der historischen Encoder-/VL53-Erkenntnisse ist im Nachtrag getrennt erfasst.
AGENTS, LAB-1, Inventar, Projektgedächtnis,
aktueller WE-Auftrag/Status und Kartierungsanleitung wurden berücksichtigt.

- Remote `chris01-byte/Roboter_ws`, Branch `feature/ap06-closed-product-validation`.
- Exakter getesteter Commit: `e14ca31276b26be2d88397b310301dad3c4e9600`.
- Neuer unabhängiger Clone: `/home/p/roboter_worktrees/ap06-e14ca312-validation`.
- Release: `/home/p/.local/share/amadeus/releases/ap06-20261010T070231Z`.
- Private Rohbelege: `/home/p/.local/share/amadeus/diagnostics/ap06-20261010T070231Z`.
- Jetson AArch64, Ubuntu 22.04 / ROS 2 Humble, Kernel `5.15.199-tegra`.
- Quellbaum bei Build und Messungen sauber am genannten Commit. Erst danach
  Dokumentationsbranch `docs/ap06-jetson-passive-20261010`; keine Produktdatei geändert.

Der Betreiber bestätigte eingeschaltete Elektronik, Stillstand und den aktuell
geprüften robotrelativen LAB-Bereich. Die Erklärung und das Polygon bleiben
privat. Kartenbezug/Pose wurden für jeden Start neu gemessen; keine alte
Kartenbindung übernommen. Elektrische Motorsperre wurde nicht behauptet.

## Build und Abweichungen der lokalen Ausführung

Saubere Shell ohne `.bashrc`, Humble sowie getrennte native-, LiDAR- und
Produktpräfixe. `MAKEFLAGS=-j2`, sequenzieller Colcon-Executor und zwei
CMake-Buildthreads. **31 native Pakete und 14 Produktpakete gebaut**, native
Tests gemäß Anleitung aus, Produkttests an. Hinzu kommen gepinnter
STL-27L-Treiber und natives TF-Ownership-Prüfwerkzeug.

Alle zehn Quellenarchive entsprechen den SHA-256-Werten von
`tools/simulation/ap06_dependencies.json`; vorgesehene SLAM-/NavFn-Patches
wurden per Reverse-Check bestätigt. LiDAR: Commit
`bf668a89baf722a787dadc442860dcbf33a82f5a`, vorgesehener Shutdownpatch bestätigt.
Kein x86-Binärstand übernommen.

Nachvollziehbare lokale Anpassungen, ausschließlich im Release:

1. Der vorhandene Python-3.10-Tarfilter verwarf interne relative
   `CHANGELOG.rst`-Symlinks. Reguläre Mitglieder wurden sicher gefiltert,
   Linkziele relativ zum Archivmitglied geprüft und interne Links erhalten.
   Archivprüfsummen bleiben unverändert; Hilfsskripte/Fehlversuche gespeichert.
2. Zwei Manifest-Basispfade lagen tatsächlich unter
   `navigation2/nav2_dwb_controller/{nav_2d_msgs,nav_2d_utils}`.
   `native-src/prepared.json` enthält die korrigierten lokalen Pfade.
3. Pip zog zusätzlich NumPy 2.2.6 ein. Diese Kopie liegt außerhalb des
   aktiven Pythonpfades; tatsächlich genutzt wird System-NumPy 1.21.5.
   Gepinnte Pakete liegen nur in `Release/python`: Jinja2 3.1.6,
   MarkupSafe 2.1.5, typeguard 2.13.3, Shapely 2.0.7,
   pymodbus 3.14.0 und pyserial 3.5.
4. Konkrete Rosdep-Ausnahmen sind in `dependency-exceptions.txt` begründet:
   vorhandenes Buildwerkzeug, separat gebauter LiDAR, isolierte Pythonpins,
   nicht gestartete optionale GUI-/LLM-/Perzeptionspakete und deaktivierte
   native Test-/Dokumentationsabhängigkeiten. Restlicher Rosdep-Check bestanden.
   Keine Systempakete installiert oder verändert.
5. Der erste native Build fand einen defekten Systemexport von BT.CPP.
   Explizite Release-CMake-Pfade und gezielte Nachbauten korrigierten zusätzlich
   `rsl`, `tcb_span`, `tl_expected` sowie beim BT-Orchestrator
   `control_msgs` und `nav2_msgs`. Endgültiger Audit: keine ausgewählte
   native/Produktabhängigkeit im CMake-Cache außerhalb des Release.
6. `vcs` 0.3.0 war nur unter `~/.local/bin` vorhanden. Ein Verweis im
   Release-Binverzeichnis machte genau dieses Werkzeug für den LiDAR-Build
   verfügbar; keine Änderung am globalen Suchpfad.

Aufgelöste Zusatzruntime: `nav2_behaviors` **1.1.20-1jammy.20260804.230121**,
`rosbridge_server` **2.0.7-1jammy.20260804.204022**, beide aus Humble.
VL53 verwendet `smbus2` **0.6.1** und `vl53l5cx` **1.0.1** aus
`/home/p/.local/lib/python3.10/site-packages`; kein `vl53l7cx`-Modul.
Modulpfade und Prüfsummen sind aufgezeichnet. BT.CPP 4 kommt aus dem Release;
die Nav2/Humble-Kette lädt daneben ihre vorhandene BT.CPP-v3-Bibliothek.

### Tests: kein Gesamt-Grün

Erster vollständiger Produktlauf: **2.456 registrierte Tests, 38 Fehlerfälle,
0 Errors, 0 Skips**; Explorer allein 1.783 bestanden / 25 fehlgeschlagen.
13 weitere Fehler betrafen `robot_navigation`.
33 Fälle verlangten explizit `ROS_LOCALHOST_ONLY=1` und eine Testdomain
200–230, die der dokumentierte Aufruf nicht setzt. Eine gezielte Wiederprüfung
aller 38 Fälle mit Domain 216, ohne parallelen Compiler, ergab **30 bestanden,
8 fehlgeschlagen**. Diese Ergebnisse werden nicht als zusätzliche Tests addiert.

Verbleibend:

- Drei `test_action_client_registration`-Fälle (`original-goal`,
  `serialized-goal`, `serialized-cancel`): Executor nimmt erwartete echte
  Antwort nicht innerhalb der 3-s-Prüfung auf.
- Zwei `test_metric_near_start_priority`-Fälle (`cooldown`, `capped`):
  `frontier_candidate_processing_budget_exhausted`.
- Drei `test_metric_public_observation`-Fälle: A54-Kurzsicht und private
  Ledgerfälle A54/A55; statt der erwarteten nahen Beobachtung tritt fernere
  Auswahl auf (ca. 2,09/2,12 m gegenüber Testgrenze 0,60 m, synthetische Daten).

BT-Orchestrator nach finaler Bindung erneut gebaut/getestet. Keine
Produktkorrektur, keine gelockerten Budgets, keine weitere Wiederholung zum
Erzwingen eines grünen Ergebnisses. Initial- und Wiederprüfungs-XML bleiben erhalten.

## Passiver Ablauf und Quellenbindung

Gleicher regulärer Start in beiden Läufen:

```text
ros2 launch robot_bringup app_mapping.launch.py
  use_hwt601_odometry:=true active_drive:=false enable_auto_explore:=false
  hwt_development_contract:=true operator_stationary_confirmed:=true
  start_web_gui:=false start_explorer:=false
```

Runtime in lokaler Domain 166, `ROS_LOCALHOST_ONLY=1`, Fast DDS. Nur temporäre
Prozessumgebung, keine dauerhafte Netzwerkkonfiguration. Das Runtime-Manifest
bindet Commit, Launchargumente, vier Setup-Dateien, Module, Profile, Binärhashes
und Bibliotheken. Audit von 48 Paket-/CMake-Präfixen; keine alte
`/home/p/roboter_ws/install`-Bibliothek in den erfassten Prozessabbildungen.

| Nachweis | Ergebnis |
|---|---|
| `/map` | alleiniger Publisher `/slam_toolbox` |
| `/robot_map_manager/status_json` | eigener MapManager, exakte Kartenfingerprint-/Quellstempelpaare aufgezeichnet |
| `map -> odom` | nativer TF-Probe ordnet Transform-GID SLAM Toolbox zu |
| `odom -> base_link`, `/odom` | EKF `/hwt601_mapping_ekf` |
| Radrohquelle | `/hwt601_encoder_shadow_reader`, FC03, `read_only=true`, keine TF-/Aktorausgabe |
| HWT-Rohquelle | `/hwt601_shadow_reader`, `/dev/ttyUSB_HWT601`, keine Sensor-Schreibkommandos/Aktorausgabe |
| Scope | beide Vorbereitungen brechen mit `TF pose/reference missing/stale/future` ab |
| Explorer | kein Profil erzeugt, keine Instanz gestartet, keine Mission |

Graphpräfixe und Transform-GIDs belegen Eigentümer, **nicht** automatisch eine
frische konsistente Pose. In Lauf A passen 266 von 268 MapManager-Meldungen
zu einem im Bag vorhandenen Fingerprint-/Zeitstempelpaar; in B 220 von 235
(enthält Anlauf-/Aufnahmegrenzen). Pro Lauf ein aufgezeichneter
Kartenfingerprint. Die privaten Scope-Eingaben sind daher noch keine gültigen
Scopeprofile. Der konkrete TF-Ablehnungsgrund wurde nicht durch ein
künstliches Restamping oder eine weiter gefasste Frist umgangen.

| Aufnahme | UTC / lokale Zeit jeweils +2 h | Recorderlauf |
|---|---|---:|
| A, nach Quellenstart/Scopeversuch | 08:10:04.555 bis 08:13:05.188 | 180,014 s bis SIGINT |
| B, einmalige Anlaufdiagnose | 08:14:35.591 bis 08:17:36.162 | 180,002 s bis SIGINT |

Beide Recorder Exit 0, abgeschlossene Metadaten. B startet den Recorder vor
dem identischen Stack, weil A die bereits ausgefallenen Rohquellen nicht mehr
als Zeitreihe erfasste. Keine weitere Wiederholung. Auswertung ausschließlich
nach Abschluss der jeweiligen Bag, keine Offline-Auswertung parallel zur
zweiten Aufnahme. Bags enthalten die vorgegebenen Topics, ergänzt um
IMU-Roh-/Gierdaten, lokalen Costmap und vier Nahbereichswolken.

## Sensorzeiten und fehlende Messungen

Die folgende Differenz ist **Bag-Empfang minus Header-Quellzeitstempel**, keine
physische Sensorlatenz. Sie enthält Producer-, Transport-, Scheduling- und
Recorderanteile. HWT stempelt am Hostempfang; keine behauptete synchronisierte
Geräteuhr. Tabelle B enthält Anlauf und laufenden Betrieb.

| Topic / Lauf B | Anzahl | Quellabstand p50 / Maximum (ms) | Empfang minus Stempel p50 / p95 / Maximum (ms) |
|---|---:|---:|---:|
| HWT raw | 16.518 | 10,00 / 357,68 | 1,38 / 4,68 / 358,33 |
| HWT korrigierte Gier | 13.932 | 9,98 / 519,57 | 3,52 / 8,93 / 353,41 |
| normalisierter Scan | 1.740 | 100,00 / 297,45 | 3,99 / 7,43 / 319,70 |
| VL53 links | 613 | 251,96 / 429,15 | 2,52 / 8,19 / 27,50 |
| VL53 rechts | 613 | 251,96 / 429,15 | 4,15 / 11,40 / 110,79 |
| EKF Odometrie | 4.298 | 31,64 / 369,47 | 10,05 / 19,43 / 223,01 |
| Karte | 147 | 1.000,00 / 1.500,01 | 107,37 / 115,14 / 622,72 |

Lauf A: Scanempfang maximal 364,04 ms auseinander; Nahbereich links/rechts
maximal ca. **2,315 s**. In A fehlen HWT-/Radrohzeitreihen nach den Ausfällen.
B liefert die HWT-Anlaufzeitreihe, aber ebenfalls **keine Radroh-Odometrie im
Bag**: der Reader meldet 32 Publikationen vor Verriegelung; der Recorder
abonniert die Quelle erst gegen Ende dieser kurzen Phase. Keine vollständige
Radlatenzverteilung aus diesen Bags ableitbar. Die Readerstatus-/FC03-Belege
bleiben verfügbar.

Encoder A: erste unüberbrückbare Samplelücke **333,969 ms**, B **370,945 ms**,
Grenze **180 ms**. Dazu Paarlesezeiten 28,535 bzw. 65,766 ms; maximal versuchte
Paare 59,246 bzw. 65,766 ms, jeweils unter der separaten 120-ms-Paargrenze.
Damit ist hier die Zeitkontinuität verletzt; ein zu langes einzelnes
Modbuspaar ist nicht belegt. Begrenzte Wiederaufnahme scheitert,
`encoder_timing_continuity_unproven` bleibt verriegelt. Ursache der
Scheduling-/Publikationslücke noch nicht nachgewiesen.

HWT A: 3.934 akzeptierte Rohwerte vor terminalem
`Sende-/Empfangsfehler: Write timeout`; dies ist das Senden der FC03-Leseanfrage,
kein Aktorbefehl. Fusion bleibt `raw_terminal_fault`. HWT B am Ende bereit,
Bias stabil mit 998 Kalibriersamples; trotzdem keine vollständige
Quellenbereitschaft wegen Radquelle. Vereinzelt zusätzliche Roh-/Gierlücken
sind in B sichtbar. EKF-Ausgaben werden nicht als Ersatz für fehlende echte
Radmessungen gewertet.

TF B: `map -> odom` wird gegenüber Bagempfang teils vorausdatiert
(p50 −130,02 ms; Spanne −180,64 bis +469,91 ms). Das allein beweist nicht,
welche einzelne gemeinsame Poseabfrage den Scopeabbruch auslöste.
`odom -> base_link` p95 Empfangsalter 19,46 ms, Maximum 223,05 ms.
Statische TF werden nicht anhand ihres alten Zeitstempels als stale bewertet.

## Sichtlücken

- In beiden Läufen mindestens 99 % nichtendliche Werte für **406 von 2.160
  Scanstrahlen**, Indizes 337–742, Sensorwinkel **56,19–123,72°**.
  Mit tatsächlich publiziertem LiDAR-Yaw 1,5708 rad liegt dies bei ungefähr
  **146,19–213,72° relativ zur Basis**, also im Hecksektor. Die aktive
  Crop-/Mastmaske erklärt diesen ausgesparten Sektor; der Versuch trennt
  Softwaremaske und physische Mastabschattung nicht experimentell.
- LiDAR-TF: 0,660 m über `base_link`; nach dokumentierter Basishöhe etwa
  0,750 m über Boden. Eine horizontale Scanebene belegt keine Boden-/niedrige
  Hindernisabdeckung.
- **Alle vier Nahbereichswolken in beiden Läufen sind leer**, A je 688,
  B je 613 Meldungen. Technische Framegesundheit beidseitig true,
  Qualität durchgehend `QUALITY_PARTIAL=3`, `observed_columns=0`.
  Eine gesetzte Spalte würde gültige Rückgaben in allen acht Höhenzonen
  verlangen. Leere Wolken und null vollständige Spalten sind kein Freiraumbeleg,
  **aber auch kein Sensorfehler und keine Forderung nach 64/64 Targets**. Der
  finale Health-Vertrag vom 25.09. verlangt gesunde, frische und zeitlich
  gepaarte Frames/Wolken. Unbeobachtete Zonen bleiben unbekannt; gültige
  Teilframe-Hindernisse bleiben marking-only wirksam. Die reale 2,315-s-Lücke
  in A ist davon getrennt ein Frischeproblem.
- Status/Wolken tragen gleiche Stempel: B 613 von 613 pro Wolke,
  A 685 gemeinsame Statusstempel bei 688 Wolken. Kein Ersatzpunkt eingespeist.
- Nahbereichs-TF 0,215 m über Basis, entsprechend etwa 0,305 m über Boden;
  Filter bis 0,50 m. Zusammen mit fehlenden Punkten ergibt sich hier keine
  nachgewiesene Schließung der Boden-/Hecklücken. OAK bleibt im Mappinglaunch aus.
- `/safety/estop` war im Bag false. Dieser Einzelstatus belegt weder gültige
  Quellen noch vollständige Hindernisabdeckung.

## Abschluss, Bestandsschutz und Rückfall

Die anfänglich ausgeschaltete Encoder-Elektronik antwortete nicht; nach
Betreiberbestätigung der Versorgung war die Leseprobe erfolgreich.
Vorher, unmittelbar vor Start und nach Abschluss je 20 rein lesende
Encoderproben pro Motor: Position 0, Delta 0, Geschwindigkeit 0 rpm.
Bei laufendem Stack kein `base_hardware`-Aktorprozess, kein Motorverbraucher
von `/cmd_vel`; vorhandene Aufzeichnungen aller empfangenen Geschwindigkeits-
kommandos sind null. In A hat `/cmd_vel` selbst keine aufgezeichnete Nachricht;
B enthält Nullnachrichten. Keine Explore-/Navigate-Mission gesendet. Das
belegt diesen passiven Versuch, keine Anhaltewirkung unter Fahrt.

Recorder jeweils direkt per SIGINT, danach nur direkter Launch-PID signalisiert,
keine Prozessgruppe. Beide Launches beendet, Geräteports wieder frei,
Roboterknotenprüfung leer. **1.048 Bestandsinstall-Dateien vorher/nachher
SHA-256-identisch**, keine hinzugefügt/entfernt. `/home/p/roboter_ws` bleibt
sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`.

Rückfall: frische Shell ohne dieses Release verwenden; Bestandsinstallation
wurde nie ersetzt. Kein Autostart, kein Shellprofil, kein Systempaket verändert.
Keine Realraumkarte, Bag oder private Bindungsdatei im Git-Checkout.

## Belegindex

Im Release: `build-ap06.bash`, `build-transcript.log`, Build-/Test-Colconlogs,
`prepare-compat.py`, `prepare-symlink-compat.py`, `source-proof.json`,
`lidar-proof.json`, `native-src/prepared.json`, `dependency-exceptions.txt`,
`python-resolution.json`, `test-results-initial.txt`, initiale Pytest-XML,
`failed-cases-retest.xml`/`.log`, Rebind-Skripte/-Logs, `runtime-env.bash`,
Aufnahme- und Auswerteskripte. Hilfsskripte sind Messwerkzeuge, kein Produktpatch.

Privat: `runtime-manifest.json`, `resolution-audit.json`,
`loaded-library-audit.json`, `stack-processes.json`, Graphsnapshots,
`tf-ownership.jsonl`, Encoderproben, `scope-binding.log`,
`lab-scope.json` mit Messbeleg, `recording.json`, `bag/`, `analysis/`,
`preservation.json`; zweite Aufnahme vollständig unter `startup-repeat/`.
Ein abschließendes `evidence-sha256.json` bindet die lokalen Messdateien.

Der einzige nächste WE-Schritt steht im [STATUS](STATUS.md).

## Nachtrag: historische Encoder-/VL53-Erkenntnisse angewandt

Der Nutzer beauftragte anschließend ausdrücklich die Problemlösung anhand der
älteren Unterlagen zur autonomen Wohnungskartierung. Dafür neuer Branch
`fix/ap06-passive-sensor-timing` auf demselben Commit im separaten Checkout;
Änderungen noch uncommitted. Zusätzlicher, ausschließlich sitzungsbezogener
Release `/home/p/.local/share/amadeus/releases/ap06-sensor-fix-20261010`.
Private Belege entsprechend unter
`/home/p/.local/share/amadeus/diagnostics/ap06-sensor-fix-20261010`.

### Historische Verträge und VL53-Korrektur

Maßgeblich ist der Eintrag **25.09.2026 – finaler VL53-Health-Vertrag** in
[archiviertem Projektgedächtnis](archive/20260930-v1.1/PROJECT_MEMORY.md).
VL53 ist Nahhindernis-/Reaktionssensor, keine globale 64/64-Freiraumbescheinigung.
Die damaligen Zieltafel-/Freiszene-Aufnahmen erklären gesunde PARTIAL-Frames
mit wenigen Fernreturns und leeren gefilterten Nahwolken. Der Übergabecode
enthält diesen Vertrag bereits. **Kein VL53-Treiber-/Filterpatch erforderlich.**
Die frühere Einordnung leerer Wolken als eigenständiger Sensorblocker war falsch.
Ein Sichtnachweis für unbekannte Zonen entsteht daraus weiterhin nicht.

Aktueller zweiter Patchlauf: **615 gesunde PARTIAL-Frames**, 615 identische
Status-/Links-/Rechts-Stempel, beide Nahwolken jeweils 615-mal leer. Offline
mit den unveränderten Gate-Callbacks bei originalen Bag-Empfangs-/Quellzeiten
nachgespielt: nach den ersten zwei noch unvollständigen Callback-Eingängen
**1.843 positive Health-Prüfungen**, keine weitere Ablehnung an diesen
Callbackzeitpunkten. Ohne Folgedaten nach einer Sekunde korrekt negativ.
Das ist eine Offline-Vertragsprüfung, keine gefälschte Live-Freigabe und keine
Bewegungsabnahme (`phases/near-contract.json`, `near-contract.py`).

Historischer Encodervertrag vom 26.09. und laufendes Projektgedächtnis vom
01.10.: 120 ms Paargrenze, 180 ms Kontinuität, USB-Suchpfadcache mit weiterhin
vollständiger Identitäts-/Generationskontrolle, 15-s-Anlauf und begrenzte
Wiederaufnahme nach echten frischen Paaren sind schon vorhanden. Frühere
Versuche mit längerem Anlauf und CPU-Pinning waren erfolglos. Kein erneutes
Lockern der Fristen, kein Ersatz durch synthetische Radwerte.

### Gemessene Publikationsblockade und abgegrenzter Patch

Private Instrumentierung maß unveränderte `_poll`, Status- und DDS-Publikation:

| Versuch | Befund | Konsequenz |
|---|---|---|
| Originalstack, ohne Recorder | Odometrie-`publish` 297,516 ms; Poll 313,948 ms; 23 Publikationen | DDS-Aufruf blockiert den Lese-Callback |
| Nur Odometrie in separatem Thread | Status-`publish` 345,225 ms; Poll 358,23 ms; 48 Publikationen | verworfen, Produktcode zurückgenommen |
| Originalcode, nur Reader mit Fast-DDS-ASYNCHRONOUS | Status-`publish` 254,534 ms; Poll 268,271 ms | verworfen, nicht Bestandteil des Kandidaten |
| Alle drei Ausgaben in separatem Prozess | zwei vollständige passive 180-s-Aufnahmen, unten | Kandidat, noch keine robuste Gesamtlösung |

Thread-/ASYNCHRONOUS-Aufnahmen wurden nach dem Fehler vorzeitig beendet und
zählen ausdrücklich nicht als Dreiminutennachweis. Rohbelege/verworfener
Threadpatch bleiben privat. Aus der Messung folgt die Blockade im Aufruf,
keine bewiesene Aussage über deren interne DDS-/GIL-Ursache.

`encoder_publication.py` startet einen eigenen DDS-Ausgabeprozess per `spawn`.
Eine begrenzte Queue je bestehendem Topic; der Leser wartet nicht auf einen
vollen Ausgabepuffer. Originale Nachrichtenstempel bleiben erhalten, überalte
Queueeinträge werden verworfen. Der Ausgabeprozess besitzt keinen Geräteport,
keinen TF-Publisher und keinen Aktorpfad. Sein Ausfall verriegelt den Leser.
FC03-Whitelist, exklusive Portbindung, Identitätsprüfungen und 120/180-ms-Grenzen
bleiben unverändert. Effektive Launch-Remaps werden vor Prozessstart aufgelöst.
`rosidl_runtime_py` ist als Laufzeitabhängigkeit deklariert.

**170 gezielte Tests bestanden**, separat `base_hardware` gebaut. Eingeschlossen:
Encoder/Hardware, volle VL53-Suite, Nahbereichs-Safety, Nav-Vertrag/Costmapquellen,
metrische Beobachtungsquellen; neue Fälle für blockierten Prozesskanal mit
unverändertem Originalstempel sowie Ausfall des Ausgabeprozesses. Keine erneute
vollständige AP-06-Regression; die acht ursprünglichen Negativfälle bleiben offen.
Belege: `build-manifest-final.log`, `tests.xml`, `code-proof-final.json`.

### Zwei passive Patchläufe und verbleibende Grenzen

Beide mit ursprünglichen passiven Launchargumenten, ohne Explorer/Mission,
ohne geänderte Grenzwerte und ohne Aktorschreibprozess. Instrumentierung im
zweiten Lauf zusätzlich mit Thread-CPU-Zeit; keine Graphabfrage während dieser
zweiten Aufnahme. CPU-/Wartezeiten sind Diagnosewerte, keine Ursachenfreigabe.

| Messung | Erster Patchlauf `process` | Zweiter Patchlauf `phases` |
|---|---:|---:|
| Aufnahme UTC | 08:51:25–08:54:25 | 08:58:37–09:01:38 |
| Aufnahmezeit vor Stop | 180,020 s | 180,066 s |
| Reader-Publikationen laut letztem Status | 664 | 3.200 |
| Radnachrichten im Bag | 660 | 3.186 |
| Maximale versuchte Paarzeit | 169,812 ms | 66,264 ms |
| Readerende | Kontinuität verriegelt | bereit, 0 Ablehnungen/0 FC03-Fehler |
| Quellenstatus am Ende | Radquelle ungültig | `sources_ready=true`, passiver Vertrag |

Erster Lauf: Erstfehler `encoderpaar_zeitfenster_ueberschritten`, Samplelücke
136,469 ms, Alter am Leseende 221,374 ms. Einzelreads 84,284/78,436 ms;
darin Alias-/USB-Prüfungen zusammen 86,986 ms, eigentliche Modbus-Aufrufe
54,439 ms. Diese Phasen enthalten auch Unterbrechungs-/Wartezeit; reine
Übertragungsdauer ist daraus nicht ableitbar. Begrenzte Wiederaufnahme endet
korrekt mit `encoder_timing_continuity_unproven`. Erster abgelehnter Status
und sein Vorgänger erhalten in `process/first-rejection.json`.

Zweiter Lauf: keine Reader-Ablehnung/Wiederaufnahme nötig, Positionen/RPM null.
Maximaler instrumentierter USB-Identitätsaufruf dennoch 54,057 ms Wandzeit
bei 34,256 ms Thread-CPU-Zeit; langsamster Aliasaufruf 11,409 ms bei 0,169 ms
CPU-Zeit. Das zeigt unterschiedliche Verzögerungsanteile, erklärt aber nicht
rückwirkend den ersten Paarverstoß. Keine weitere identische Fehlstartserie.

Sensorzeiten zweiter Lauf, Millisekunden; Empfangsalter = Bagempfang minus
Originalstempel, keine physische Abtastlatenz:

| Quelle | Anzahl | Quellabstand p50 / max | Empfangsalter p50 / p95 / max |
|---|---:|---:|---:|
| Encoder roh | 3.186 | 50,01 / 299,66 | 12,57 / 17,39 / 329,10 |
| HWT roh | 17.010 | 9,99 / 165,38 | 1,35 / 4,91 / 85,76 |
| normalisierter Scan | 1.746 | 100,00 / 200,16 | 3,66 / 7,34 / 150,73 |
| VL53 Status | 615 | 252,32 / 282,54 | 1,08 / 4,69 / 15,28 |
| EKF Odometrie | 4.664 | 32,21 / 369,10 | 11,58 / 21,57 / 71,88 |

**Gesunder Reader ist kein durchgängiger Zustellnachweis.** Die Radquelle hat
im Recorder weiterhin 299,66-ms-Stempellücken und bis 329,10 ms Empfangsalter.
Queueverwerfen/Transport/Recorder können die Differenz zwischen Readerzählung
und Bag erklären; deren Anteile sind nicht getrennt bewiesen. Der Gate-Status
meldet nach dem HWT-Warmup 645-mal `readonly_preflight_no_motion`, keine
aufgezeichnete spätere Radablehnung. Daraus folgt weder, dass jede einzelne
Nachricht rechtzeitig beim Gate ankam, noch dass der Recorder dessen Alter misst.

Quellenbindung: ausschließlich R0 plus neues `base_hardware`-Präfix; beide
installierten Pythonmodule SHA-256-identisch mit dem Kandidaten. Im ersten
Patchlauf ist `/hwt601_encoder_shadow_output` der einzige gemessene Publisher
von `/fusion/hwt601/wheel_odom_raw`, Empfänger sind EKF, Gate und Recorder.
Der Graphsnapshot erfolgte nach der Verriegelung; der Basisport war dann schon
geschlossen. Im zweiten Lauf kein eigener Live-Graphsnapshot; gleiche
Launch-/Installbindung und reale FC03-Statusfolge, keine erfundene Portmomentaufnahme.
Alle aufgezeichneten Geschwindigkeitskomponenten null. Kein Scopeversuch in
diesen Encoderdiagnosen; frühere TF-/Scopebefunde und Sichtgrenzen bleiben offen.

Abschluss: Recorder und direkte Launch-PIDs geordnet beendet, Endgraph nur
mit dem temporären Prüfnode, Geräteports frei. Abschlussprobe je Motor 20
FC03-Messungen, Position 0/Delta 0/0 rpm. Erneut **1.048/1.048 bestehende
Install-Dateien SHA-256-identisch**, keine hinzugefügt/entfernt; ursprünglicher
Checkout sauber. Rückfall: neues Overlay nicht sourcen; kein Autostart/Profil
oder Bestandsinstall geändert. Aktuelle Arbeit ist ein separat überprüfbarer
Entwicklungskandidat, keine Freigabe für Fahrt oder Kundenbetrieb.

## Vorbereitung der ersten realen Testfahrt, 10.10.2026, 11:38–11:55 MESZ

### Auftrag, tatsächlicher Umfang und Grenzen

Der Nutzer autorisierte ausdrücklich Vorbereitung und Durchführung der ersten
realen Laborfahrt. Diese organisatorische Freigabe liegt vor; es wurde keine
weitere allgemeine Bestätigung verlangt. Der bestätigte LAB-Bereich blieb
maßgeblich. Das gewünschte positive Ergebnis wurde nicht als Messbefund
übernommen. Die zuletzt dokumentierten technischen Quellenprobleme blieben
prüfpflichtig. Der Jetson war inzwischen neu gestartet, alle Geräteports frei.

Geplant war genau ein begrenzter Auftrag über Mission Manager → BT → Explorer
→ Nav2 → vorhandenes Gate/Collision Monitor → Basis, maximal 90 s, mit Cancel
bei 0,5 m kumulierter Encoderstrecke oder 0,6 rad kumulierter Drehung, bestätigtem
Halt und aktuellem privatem Scope. Kein manuelles Navigationsziel, keine direkte
Geschwindigkeit an der Schutzkette vorbei. Das private `trial-manifest.json`
und der vorbereitete `bounded-mission.py` halten dies fest. **Dieser
Missionsprüfer wurde nicht gestartet, kein Explore-/Navigate-Auftrag gesendet.**
Seine Syntax wurde geprüft, seine bewegte Laufzeit nicht validiert.

Belege außerhalb Git:
`/home/p/.local/share/amadeus/diagnostics/ap06-first-drive-20261010`.
Zusätzlicher sitzungsbezogener Release:
`/home/p/.local/share/amadeus/releases/ap06-first-drive-20261010`.
Basis weiter `e14ca312` plus dokumentierte lokale Änderungen auf
`fix/ap06-passive-sensor-timing`, noch uncommitted. Kein Bestandsinstallwechsel.

### Bereichsvorbereitung: aktuelle TF unabhängig empfangen

Der ursprüngliche Collector verarbeitet pro Hauptschleife einen ROS-Callback
und mehrere Karten-/Graphprüfungen; derselbe Executor musste auch TF zustellen.
Bei der ersten aktuellen Bindung lagen Pose und Referenz **1,382 s** zurück.
Das Werkzeug lehnte an der unveränderten 0,8-s-Grenze ab.

`ScopeTfListener` empfängt TF nun über einen eigenen lesenden Node/Executor-
Thread. Die Karten-/Grapharbeit blockiert dessen Callback-Verarbeitung nicht
mehr unmittelbar. Originalstempel, gemeinsame Pose-/Referenzzeit, Eigentümer-
und Frischeprüfungen bleiben erhalten; kein Umstempeln und keine erhöhte Frist.
Ein echter lokaler DDS-Gegenfall hält die Hauptschleife eine Sekunde beschäftigt:
alter Ablauf rot, neuer Ablauf aktuell; nach Ende der echten Quelle altern die
Stempel unverändert und werden wieder stale. **25 Bereichstests bestanden.**
CI nimmt den neuen Prozessfall ausdrücklich auf.

Im anschließenden passiven Lauf und ersten aktiven Stillstandslauf wurde das
aktuelle private Profil erfolgreich erzeugt. Im späteren aktiven Lauf scheiterte
eine weitere Bindung dennoch an TF-Frische; die Korrektur ist keine Garantie
gegen tatsächlich ausfallende Quellen. Ein Diagnoseversuch nach einem beendeten
Explorerstart sah vorübergehend noch einen Explorer im DDS-Graph und verweigerte
korrekt einen zweiten Besitzer. Kein alter Scope wurde als aktuell ausgegeben.

### Aktive Basis: Startlast vor der ersten Encoder-Messbasis abwarten

Der aktive Pfad verwendet `base_hardware` als einzigen RS485-Besitzer; der
passive Zusatzleser läuft dann nicht. Der erste aktive Start bestätigte Stop,
Rampen und Feedback, verriegelte aber nach nur acht gültigen Publikationen an
einem **239,018-ms-Paar** (Grenze 120 ms).

Der vorhandene 15-s-Startversatz wird deshalb nun auf den jeweils gewählten
Encoderbesitzer angewandt, auch auf die aktive Basis. Der alte Argumentname
`encoder_shadow_start_delay_s` bleibt kompatibel bestehen. Dies ist Wartezeit
**vor** Herstellung der ersten Messbasis; weder 120-ms-Paargrenze noch
180-ms-Kontinuität, Watchdog, Stopp- oder Wiederaufnahmebedingungen werden erhöht.
Bis echte gültige Quellen vorliegen, bleibt das Gate geschlossen. Aktorbefehle,
Geometrie, Kalibrierung und Motorparameter wurden nicht verändert.

Die Launch-Auflösung prüft beide Modi: genau ein Gerätebesitzer, kein vorzeitig
gestarteter Basisnode, unveränderte TF-Eigentümer und Opt-ins. Alter aktiver
Ablauf am neuen Test rot, passiver Fall grün; danach **181 betroffene Tests
bestanden**, einschließlich Basis-, Launch-, Nav-Vertrag und Bereichstests.
`amadeus_lidar_bringup` separat gebaut; installierte Launchdatei SHA-256-identisch
mit dem Kandidaten (`source-proof.json`). Keine vollständige neue AP-06-Abnahme.

### Tatsächliche Ergebnisse

| Lauf | Aufnahme | Befund |
|---|---:|---|
| Passiver frischer Vorlauf | 180,077 s | 344 Publikationen, 180,353-ms-Samplelücke; Kontinuität verriegelt |
| Passiv nach TF-Entkopplung | Status-/Profilbelege, kein vollständiges Bag | Scopebindung erfolgreich; Reader später Paarzeitfehler bis 165,519 ms |
| Aktive Basis, ursprünglicher Sofortstart | 73,760 s, nach Fehler beendet | acht Publikationen, Paarzeit 239,018 ms; kein Auftrag |
| Aktive Basis, 15-s-Startversatz | vollständige 180-s-Aufnahme | 2.438 Publikationen, zeitweise Quellen bereit; später 181,212-ms-Samplelücke |

Im letzten Lauf blieb die maximale versuchte Paarlesezeit mit **96,596 ms**
unter 120 ms. Der erste Kontinuitätsverstoß hatte 46,104 ms Paarzeit,
181,212 ms Sampleabstand und 204,264 ms Alter am Leseende. Zwei spätere gültige
Paare beweisen keine überbrückte alte Lücke; `encoder_timing_continuity_unproven`
blieb korrekt verriegelt. Die nur 1,212 ms Überschreitung rechtfertigt für sich
keine neue Bewegungs-/Stoppfreigabe und erklärt die Ursache nicht. Aktive
Veröffentlichungs-/Callbackzeit ist als nächstes zu korrelieren.

HWT lieferte im letzten Live-Snapshot gültige Rohdaten ohne terminalen Fehler;
im Gate waren zwischenzeitlich Rohquellen-Frischeablehnungen aufgezeichnet.
Das ist kein Nachweis eines defekten Sensors. Die Herkunft von Mess-/Prozess-
und Zustellverzögerung bleibt getrennt zu untersuchen.

Ein eigener Aufruffehler ist ebenfalls erhalten: Nach einer fehlgeschlagenen
Profilerzeugung lief ein Shellaufruf ohne Fehlerabbruch bis zum Explorerstart
weiter. ROS meldete die fehlende Profildatei; der Explorer startete mit seinem
Basisprofil im Leerlauf und wurde direkt per SIGINT beendet. Keine Mission oder
Bewegung. Der vorbereitete Aufruf `start-bound-explorer.bash` bricht nun bei
fehlendem/ungültigem explizitem Profil **vor** dem Launch ab; keine Weiterfahrt
mit Standardprofil. Dieser Startversuch zählt nicht als erfolgreicher Test.

### Abschluss und Rückfall

Alle drei Bags enthalten ausschließlich Nullkommandos. Sämtliche aufgezeichneten
Encoderpositionen und gemessenen Motor-RPM null; Mission Manager durchgehend
`idle`. Abschließend 20 unabhängige FC03-Proben je Motor: Position/Delta/RPM null.
Direkte Launch-/Recorder-PIDs geordnet beendet, Endgraph nur mit temporärem
Prüfnode, Geräteports frei. **Keine reale Fahrt ausgeführt.**

Erneut 1.048/1.048 Bestandsinstall-Dateien SHA-256-identisch, keine hinzugefügt
oder entfernt; `/home/p/roboter_ws` sauber auf `23928d9`. Rückfall: die neuen
Release-Overlays verlassen. Kein Autostart, Profil oder Systempaket geändert.
Belegindex: `trial-summaries.json`, Aufnahmen/Logs pro Lauf, Scopebelege,
`tf-regression-before.log`, `tf-regression-after.log`, Startregression,
Release-Build-/Testlogs, `source-proof.json`, `preservation.json`,
`final-graph.json`, `postflight.jsonl`. Reale Karten/Geometrie bleiben privat.


## Nachtrag 10.10.2026 – Encoder stabilisiert, erster echter Missionsauftrag ohne Bewegung

**Ergebnis:** Eine reale `explore`-Mission über Mission Manager → BT → Explorer
wurde gestartet. Sie endete vor einem Nav2-Fahrbefehl mit Geometriefehler.
Encoderweg, Drehung und sämtliche aufgezeichneten Geschwindigkeitsbefehle: null.
Frischer Stillstand bestätigt. **Keine reale Fahrt, keine AP-06-Abnahme (0/3).**
Die bestehenden Labor-/Bereichserklärungen wurden übernommen; keine neue
allgemeine Freigabe war nötig.

### Messungen und gezielte Korrekturen

Die aktive Zeitmessung hat die Vermutung eines ausschließlich blockierenden
DDS-Publishers nicht bestätigt: im Baselineversuch DDS maximal 33,211 ms,
ein FC03-Paar aber 123,721 ms. Die langsamste Pollfunktion brauchte 124,109 ms
Wandzeit bei 4,443 ms Thread-CPU; darin FC03 65,648 und 55,414 ms. CPU-Zuteilung
allein blieb negativ (134,303-ms-Paar). Eine ergänzende GC-Messung fand
42,304 ms vollständige Speicherbereinigung, jedoch **nicht** am späteren
Fehlerzeitpunkt. Daraus keinen exklusiven GC- oder Hardwaredefekt ableiten.

Im begrenzten Prozessaufbau wurden Encodererfassung/Basis auf CPU 5,
HWT-Erfassung und -Drehratenverarbeitung auf CPU 4 und die übrigen neu gestarteten
ROS-/Recorderprozesse auf CPUs 0–3 gelegt. Vor der ersten Encodererfassung wird
im jeweiligen Prozess einmal GC ausgeführt und der vorhandene Objektbestand
mit `gc.freeze()` aus späteren Vollscans genommen; neue Objekte unterliegen
weiter der normalen Speicherbereinigung. Keine globale CPU-, Prioritäts-,
Leistungs-, Autostart- oder Systemkonfiguration verändert. Diese Kombination
ist ein protokollierter Laufzeitkandidat, kein allgemeiner Echtzeitnachweis.

Damit blieb der aktive Encoderpfad gesund. Weitere Standläufe zeigten dagegen
HWT-Drehraten beim Gate mit 369–374 ms Alter. Ein eigener Produzententrace maß
nur 23,790 ms maximalen HWT-Callback und 14,723 ms Publisherzeit. Die bestehende
Radodometrie-Lösung wurde deshalb auf IMU-Rohdaten und Drehraten übertragen:
getrennte exklusive Callbackgruppen, Puffergröße eins und ein nicht blockierendes
DDS-Take vor der Entscheidung. Bereits laufende Callbackgruppen werden nicht
abgewartet; echte Stempel und Inhaltsprüfung bleiben erhalten. Empfangsfehler
invalidieren die betroffene Quelle. Passive und metrische aktive Verbraucher
nutzen dies; der bisherige nichtmetrische aktive Modus bleibt unverändert.

**Unverändert:** Encoderpaar 120 ms, Kontinuität/Encoderfrische 180 ms,
HWT-Rohdaten im Entwicklungsvertrag 300 ms, Drehrate 350 ms, Statusfrische,
Recoverybudgets, Watchdog, Not-Aus, Kollisionserkennung und Geometriegrenzen.

Der private Versuchsmonitor hatte zusätzlich einen eigenen Fehler: Er verlangte
auch im Leerlauf fortlaufende Nullnachrichten auf `/cmd_vel`. Laut vorhandenem
`teleop_joy.launch.py` schweigt der Collision Monitor nach dem Halt absichtlich.
Korrektur: Stillstand aus frischer Basis-/Encoder-Rückmeldung und Null-Sollwerten
bestätigen; ein frischer Nichtnullbefehl verhindert weiterhin die Bestätigung.
Sechs gerätefreie Monitorfälle bestanden. Produktions-Guards bleiben aktiv.

### Build, Regressionen und Quellenbindung

Separates Overlay `~/.local/share/amadeus/releases/ap06-current-imu-20261010`
über den bisherigen drei privaten Releases; ausschließlich Paket
`robot_state_estimation` gebaut (2,88 s Gesamtzeit). **351 betroffene Tests
bestanden** (23,53 s). Neue echte DDS-Regressionen prüfen aktuelle IMU-Werte
bei nicht bedientem Executor und weiter alternde Originalwerte nach Sendestopp.
Eine länger als die bestehende Statusfrist blockierte Statusquelle verriegelt
weiter. Frühere Negativbefunde und die ursprünglichen Gesamtregressionen sind
hierdurch nicht rückwirkend bestanden.

Checkout bleibt `fix/ap06-passive-sensor-timing` auf Basis `e14ca312…`, Änderungen
uncommitted. Quell- und Installhash des neuen Guards stimmen überein; Build-/Testlogs
und der Laufzeitpräfixpfad sind im privaten Belegindex erhalten. Gate **und**
separater Explorer beziehen das neue Overlay. Scope erneut an aktuelle Session,
Kartenfingerprint, Original-TF-Stempel und tatsächliche DDS-TF-Besitzer gebunden.
Keine alten Kartenkoordinaten übernommen. Ein zwischenzeitlicher TF-Frischefehler
beim Binden ist als Negativbeleg erhalten; nur eine später frisch validierte
Bindung wurde verwendet.

### Abschließende Aufzeichnungen und Sensorzeiten

Der letzte passive Vorlauf lief **180,089 s**, ohne Motorsteuerungsprozess.
Im Bag: **3.266** gültige Encoderpublikationen, maximal **50,396 ms** Paarzeit,
keine Paarablehnung, keine Kontinuitätsverriegelung. Der spätere Endstatus zeigte
3.626 Publikationen. Alle Quellen waren nach dem Einlauf bereit.

Der aktive Bag lief **300,052 s**: **4.731** Encoderpublikationen, maximal
**40,041 ms** Paarzeit, keine Ablehnung, keine Encoder- oder HWT-Verriegelung.
Nur die normale HWT-Einlaufphase vor Bereitschaft erscheint als Quellenmangel.

Die folgende Tabelle misst **Bag-Empfang minus Originalstempel**, nicht die
interne Laufzeit jedes sicherheitsentscheidenden Empfängers. Maxima werden
nicht durch den guten Endzustand ersetzt.

| Lauf / Quelle | Anzahl | Empfangsalter p99 / max (ms) | maximale Stempellücke (ms) |
|---|---:|---:|---:|
| passiv / LiDAR | 1750 | 10.186 / 140.612 | 200.897 |
| passiv / HWT roh | 17088 | 11.833 / 105.019 | 42.590 |
| passiv / HWT Drehrate | 14868 | 10.030 / 41.556 | 36.306 |
| passiv / Encoder | 3266 | 21.740 / 88.800 | 89.788 |
| passiv / VL53-Status | 603 | 11.608 / 16.453 | 306.576 |
| aktiv / HWT Drehrate | 25986 | 14.257 / 134.928 | 76.744 |
| aktiv / LiDAR | 2941 | 12.859 / 65.146 | 203.534 |
| aktiv / HWT roh | 28216 | 15.474 / 119.216 | 68.196 |
| aktiv / Encoder | 4731 | 20.431 / 112.185 | 91.971 |
| aktiv / VL53-Status | 1051 | 19.620 / 92.334 | 450.153 |

VL53-Status: 603/603 passive und 1.051/1.051 aktive Nachrichten mit beiden
Frames gesund. Das ist Frische-/Framegesundheit, **kein** Nachweis freier Flächen
bei leeren Returns und keine lückenlose Bodenabdeckung. Der historisch belegte
PARTIAL-Vertrag bleibt maßgeblich; keine künstlichen Punkte eingespeist.

### Tatsächlich gesendeter Auftrag und neuer konkreter Fehler

Der korrigierte Monitor bestätigte die frischen Quellen und den Stillstand,
sendete einmal `{"type":"explore"}` und nach BT-Fehlschlag `{"type":"cancel"}`.
Die Mission scheiterte nach rund 4,93 s; kein Fahrbefehl wurde freigegeben.
Im maßgeblichen Explorersnapshot: `safe=true`, HWT `HEALTHY`, Encoder gesund,
keine Paarablehnung. Begrenzung: 90 s, kumulativ 0,5 m bzw. 0,6 rad; keine Grenze
musste durch eine Bewegung ausgeschöpft werden.

Der endgültige Ablehnungsbeleg lautet `self_body_scan_stale_after_processing`:
Ausgewählter Scan bereits 93,509 ms alt, Geometriearbeit 677,016 ms, danach
770,524 ms gegenüber unveränderter 500-ms-Grenze. Der vorhandene zweisekündige
Neuversuchsrahmen für noch nicht zugeordnete Geometrie wurde bereits benutzt.
Zusätzlich beide Startreferenzen `valid=false`, Grund
`start_egress_obstacle_or_scope`, keine privaten Freiraumzellen freigegeben.
Die genaue Trennung Hindernis/Scope/Rasterrand ist damit noch nicht bewiesen.
Keinen generellen Hardwarefehler oder eine erfolgreiche Fahrt daraus ableiten.

Private Kartenansicht `latest-active/start-geometry.png`: Rohkarte zeigt einen
unbekannten Keil durch den Roboter-/Rückbereich, der Costmapausschnitt andere
Eigenkörperbehandlung; der bestätigte hintere Bereichsrand liegt am Footprintrand.
Die Darstellung nutzt die letzten Bag-Karten **vor** der Auswahl, nicht behauptete
bytegleiche Explorer-Zwischenarrays. Weitere strahlenförmige unbekannte Bereiche,
Mastabschattung, die begrenzte VL53-Sicht und die fehlende OAK-Abdeckung bleiben
reale Sicht-/Nachweisgrenzen. Unbekannt bleibt unbekannt.

**Genau nächster Schritt:** Den verworfenen Geometriesnapshot privat zeitlich
profilieren (Scope-Rasterisierung, Eigenkörper- und Startreferenzprüfung) und
`start_egress_obstacle_or_scope` an der exakten Footprint-/Scope-Rasterkante
auftrennen. Nur äquivalente Beschleunigung bzw. ein belegter Geometriefehlerfix;
keine alten Scans freigeben, keine unbestätigte Bereichserweiterung, keine
Wiederholung derselben Fahrt in Hoffnung auf einen grünen Moment.

### Abschluss und Rückfall

Alle eigenen Explorer-/Stack-Launchprozesse direkt per SIGINT beendet; keine
Prozessgruppe signalisiert. Je Motor anschließend 20 direkte FC03-Proben:
Position, Positionsänderung und Drehzahl durchgehend null. Geräteports frei.
Bestehendes `/home/p/roboter_ws` weiterhin sauber auf `23928d9…`; **1.048/1.048
Install-Dateien identisch**, keine hinzugefügt/entfernt. Kein Push/Merge,
keine Änderung der Bestandsinstallation. Rückfall: private Prozesse beenden
und neue Overlay-/Instrumentierungspräfixe weglassen; keine Systemänderung
zurückzunehmen. Keine Kartendaten oder Bags ins Repository aufgenommen.

Private Belege unter `~/.local/share/amadeus/diagnostics/ap06-active-output-20261010/`:
`trial-summaries.json`, `sensor-times-final.json`, `imu-source-proof-final.json`,
`quiet-stop-test.json`, `preservation.json`, `postflight-encoder.json`,
Lauf-Bags/Logs, Scopeprofile, tatsächliche Prozesszuordnungen sowie
`latest-active/trial-result.json` und `start-geometry-render.json`.


## Nachtrag 10.10.2026 – Geometriezeit korrigiert, konkrete hintere Bereichsgrenze offen

Erneuter ausdrücklicher Auftrag zur realen Probefahrt. Allgemeine LAB-1-Freigabe
besteht fort. In diesem Nachtrag wurde **keine neue Mission und keine Bewegung**
ausgelöst: die vorhandene Startfläche ist weiterhin geometrisch unzulässig.

### Messung und eng begrenzte Korrektur

Privater Nachweisordner: `~/.local/share/amadeus/diagnostics/ap06-geometry-20261010`.
Offline auf den letzten aufgezeichneten Karten vor der abgelehnten Auswahl:
108 von 2.700 reservierten Footprint-Zellen je Raster liegen hinter der
bestätigten hinteren Bereichsgrenze. Der unaufgepolsterte Roboter endet dort;
Rasterhalbdiagonale plus bestehende 10-mm-Reserve benötigen zusätzlichen Raum.
Das reproduziert `start_egress_obstacle_or_scope` ohne Encoderbeteiligung.
Die Bag-Proben sind benachbarte Empfangsstände, keine behaupteten identischen
internen Explorer-Snapshots. Reale Karten und Zellkoordinaten bleiben privat.

Vollständige isolierte Geometrieprofilierung: 8 Scope-Rasterisierungen benötigen
384 von insgesamt 642 ms über vier Aufrufe, rund 60 %. `rasterize_scope` nutzt
nun einen LRU-Cache mit vier Einträgen nur für das unveränderliche Polygon und
seine exakte Rastergeometrie. Kontext-, Kapazitäts- und Typprüfung bleiben vor
jedem Lookup; jeder Aufrufer erhält eine eigene beschreibbare Kopie. Keine
Belegung, Pose, Sensorzeit, Freigabe oder private Fahrberechtigung wird gecacht.
Vorher im Mittel 160,5 ms/Aufruf, danach 69,7 ms in derselben Offline-Auswertung.
Keine Frische-/Scope-/Footprint-/Fahrgrenze geändert.

Separates Overlay `~/.local/share/amadeus/releases/ap06-geometry-20261010`:
`explore` gebaut (4,64 s Gesamtlauf), identisches `amadeus_map_identity` zusätzlich
für geschlossene Quellenbindung gebaut. Runtime lädt die vorherigen AP-06-
Overlays und dieses neue Overlay, keine Bestandsinstallation. Installierte
Scope-Datei und Quelle sind SHA256-identisch; sechs tatsächlich aufgelöste
Module in `runtime-binding.json` gebunden.

234 gezielte Regressionen bestanden (25,63 s): Scope einschließlich
Cache-Invalidierung/Kopien/Kapazität, Quellenzustellung, Kartenwechsel,
Startinventar, öffentliche/private Berechtigung, Bewegungsfrische und Neuprüfung.
Zusätzlich sechs zeitabhängige Boundary-Tangent-Tests ohne laufenden Stack
bestanden (2,37 s). Keine neue vollständige AP-06-Gesamtqualifikation.
Ein zu breiter erster Testlauf wurde nach 267 bestandenen/11 abgelehnten Fällen
beendet: geerbtes `CYCLONEDDS_URI` verletzte die explizite Testumgebung.
Bereinigter breiter Lauf unter gleichzeitigem Sensor-/Profilerbetrieb nach
40 bestandenen/2 Zeitfensterfehlern beendet. Diese beiden Fälle gehören zu den
anschließend allein ausgeführten sechs grünen Fällen. Alle Logs/XML erhalten;
keine geänderten Erwartungen oder verlängerten Prüfzeiten.

### Realer passiver Vorlauf und Frische

180,057 s Bag, 11:31:27–11:34:28 UTC. `active_drive=false`,
`enable_auto_explore=false`; Bus nur durch FC03-Reader belegt. Vorheriges
prozesslokales CPU-/GC-Profil erhalten. Eigener passiver Explorer nach neuer
Karten-/TF-/Quellenbindung, ohne Mission. Privater Profilierungshook ruft die
bestehende Geometrieprüfung sechsmal auf, keine Action und kein Fahrbefehl.
Alle sechs Prüfungen bestehen die unveränderten Frischegrenzen: 434,074 / 230,667 / 169,285 / 185,881 / 265,504 / 286,585 ms Gesamtlaufzeit.
Beide Startreferenzen bleiben in allen sechs Aufrufen ungültig wegen
`start_egress_obstacle_or_scope`. Gültige Eingangsfrische ist keine Fahrfreigabe.

Letzter Bag-Readerstatus: 3.450 Publikationen, längstes Encoderpaar 34,159 ms,
kein Timing-Reject/Fault. Späterer Liveabschluss: 3.729 Publikationen, bereit.
Fusion nach Einlauf `readonly_preflight_no_motion`; 620/620 Nahbereichsstatus
mit beiden Frames gesund. PARTIAL/leere Wolken bleiben kein Freiraumbeweis.
Alle aufgezeichneten Kommandos, Encoderpositionen und Drehzahlen null;
MissionManager ausschließlich idle.

| Quelle | Bag-Proben | Empfangsalter p99 / max. | größter Headerabstand |
|---|---:|---:|---:|
| Encoder-Odometrie | 3.415 | 32,69 / 235,00 ms | 205,33 ms |
| HWT-Rohdaten | 16.133 | 22,20 / 207,16 ms | 264,70 ms |
| HWT-Drehrate | 14.968 | 17,73 / 212,47 ms | 231,17 ms |
| Laser | 1.731 | 18,17 / 278,33 ms | 200,65 ms |
| VL53-Status | 620 | 22,15 / 59,42 ms | 454,05 ms |

Diese Zeiten sind Recorderempfang minus Originalstempel, keine Behauptung
identischer Verbraucherlatenz. Der Recorder erhält weniger Encoderproben als
der Reader publiziert; seine 235-ms-Spitze bleibt als Gegenbeleg erhalten.
Keine Zeitstempel erneuert. Sechs bestandene Geometrieprüfungen und fehlerfreier
Reader belegen keine garantierte Echtzeit oder reale Controllerqualifikation.

### Abschluss und konkret fehlende Information

Alle eigenen Launch-PIDs direkt mit SIGINT beendet, keine Prozessgruppe.
Anschließend je Motor 20 exklusive FC03-Proben: Position, Delta und Drehzahl
null. Geräte frei, finaler Graph ohne eigenen Roboterstack. 1.048 vorhandene
Install-Dateien SHA256-identisch, keine hinzugefügt; ursprünglicher Checkout
sauber bei `23928d92f411473ed2644692a04aebdff0ffe803`.

An den Nutzer ist ausschließlich die konkrete hintere Flächengrenze gefragt:
ob mindestens 50 cm hinter der Antriebsachse tatsächlich hindernisfrei,
tragfähig und geprüft sind. Die bisherige Bestätigung betrifft nur 13 cm.
Keine neue allgemeine Laborfreigabe angefordert. Bis zur Antwort keinen größeren
Scope annehmen. Danach frische Quellen-/TF-/Scopebindung und begrenzte Fahrt
über die vorhandene Schutzkette; keine identische ungeklärte Fehlstartserie.
Sichtlücken der Rohkarte/Nahsensorik bleiben separat zu prüfen. AP-06 weiter 0/3.

Rückfall: neuen Cache-Diff und zugehörige Tests getrennt zurücknehmen bzw. das
vorherige Runtime-Overlay laden; keine historischen Änderungen, Daten oder
Bestandsinstallation überschreiben. Rückfall hebt die Bereichsprüfung nicht auf.


## Nutzerpräzisierung 10.10.2026 – keine weitere Bereichs-/Freigabeschleife

Der Nutzer weist erneut auf den durchgängigen Labormodus hin. Die pauschale
Nachfrage nach 50 cm hinter der Achse wird zurückgezogen; sie war nicht als
allgemeine notwendige Vorbedingung einer Vorwärtsfahrt nachgewiesen. Es fehlt
keine weitere allgemeine Freigabe. Daraus wird keine tatsächliche Beobachtung
oder numerische Vergrößerung des freien Bodens abgeleitet.

Neue ausschließlich lesende Auswertung `forward-start-diagnosis.py/.json` im
privaten Geometrieordner trennt Polygonkante und Belegung auf den erhaltenen
Realproben: Am Ausgangspunkt sind 108 reservierte Rasterzellen außerhalb des
Polygons; Rohkarte davon 105 unbekannt und drei frei, Kostenkarte elf unbekannt
und 97 frei. Keine belegten Zellen im ausgewerteten reservierten Umriss.
Die größeren Freiflächen der Kostenkarte sind kein Ersatz für Rohbeobachtung.
Bei idealer Vorfahrt 1 cm verbleiben 54 Außenzellen, ab idealen 2 cm keine.
Das ist eine Offline-Diagnose hypothetischer Posen, kein aktueller Fahrnachweis:
Anfangsstrecke, Kurven-/Trackingreserve und feste Startinventare bleiben bindend.
Unbekannt ist kein belegtes Hindernis, aber auch kein gemessener Freiraum.

Kein Stack oder Aktor gestartet, keine Action, kein Fahrbefehl. Geräte weiterhin
frei. Keine Quellcode-/Grenzwertänderung in dieser Präzisierung. Technischer
nächster Schritt ist gültige Startabdeckung bzw. ein vollständig nachgewiesener
zulässiger Ausfahrpfad; die alte pauschale 50-cm-Antwort ist kein wartender
Arbeitsauftrag mehr. Keine Behauptung einer bereits ausgeführten Probefahrt.


## 10.10.2026 – angeforderte Softwarekorrektur: Rundungsfehler unabhängig ausgeschlossen

Auf erneuten Auftrag, die Startsperre softwareseitig zu beheben, unabhängige
kontinuierliche Polygonprüfung der erhaltenen Realproben ausgeführt. Sie benutzt
Shapely-Flächenschnitt, nicht die Zellmittelpunktentscheidung des Fahrprüfers.
Physischer und gepaddeter Körper liegen vollständig im gespeicherten Polygon.
Bereits der gepaddete Körper plus bestehender 10-mm-Interpolationsreserve,
**ohne** Rasterhalbdiagonale, überdeckt 0,0052 m² außerhalb. Davon sind in den
zugrunde liegenden Rohproben 0,00509928 m² unbekannt (102 geschnittene Zellen).
Damit ist die Ablehnung nicht allein ein Rundungsartefakt der Rasterzellen.
Die zusätzliche Reserve darf nicht ohne eigenen Bewegungs-/Reglernachweis als
überflüssig entfernt werden. Die vorhandene Hardwareabweichung ist weiterhin
nicht als ausreichender Ersatz qualifiziert.

Vier bestehende gezielte Schutz-/Ausfahrtests bestanden (1,23 s): gültige
Vorwärtsausfahrt trotz anfänglichen Heckschattens, Abweisung unbekannter neuer
Fläche/Rückeintritt, Hindernis-/Drehprüfung und fehlende Scopeberechtigung.
Keine neue Softwarekorrektur am Bewegungspfad aus diesen Messungen abgeleitet;
keine erfundene freie Fläche, keine verkleinerte Kontur/Reserve, keine Fahrt.
Die zuvor geäußerte Vermutung einer bloß unnötigen Softwaresperre ist damit
für diesen konkreten Randbefund nicht belegt. Gültige Startabdeckung bzw.
beobachtbare Ausgangslage bleibt erforderlich; keine neue Laborfreigabe fehlt.

Private Nachweise: `exact-start-reserve.py/.json`, `start-guard-regression.xml`
im Geometrieordner. Ausschließlich gespeicherte Daten und gerätefreie Tests;
kein Roboterprozess gestartet. Der erste langsame vollständige Polygonlauf
wurde beendet und durch geometrisch begrenzte Kandidatenprüfung ersetzt;
keine Messdaten oder Kriterien geändert. Reale Raster/Koordinaten bleiben privat.

## 10.10.2026 – exakte Gerade und Abweichung getrennt geprüft

Erneuter konkreter Auftrag: Softwarekorrektur und anschließender Realtest.
URDF, Nav2-Footprint und Scope verwenden übereinstimmend die Antriebsachse;
kein belegter Bezugspunktfehler. Ein zusätzlicher gerätefreier Polygonvergleich
der gespeicherten Realproben zeigt eine wichtige Einschränkung des vorigen
Befunds: Die ideale kontinuierliche gerade Vorfahrt der gepaddeten Kontur bis
25 cm überdeckt keine neue unbekannte Fläche und verlässt das Polygon nicht.
Eine präzisere kontinuierliche Prüfung ist daher grundsätzlich untersuchbar;
der vorhandene Reservebefund beweist nicht, dass jede Softwarelösung unmöglich
ist. Diese Idealprüfung enthält jedoch keine Reglerabweichung.

Unabhängige Gegenbeispiele mit hypothetischen abweichenden Posen: Bei 1 mm
Vorfahrt und 1 mm Linksversatz entstehen rund 0,197 cm² zusätzliche unbekannte
Fläche; bei 1 mm Vorfahrt und −0,001 rad Winkelabweichung rund 0,0283 cm².
Keine dieser Proben enthält ein belegtes Hindernis. Es handelt sich ausdrücklich
um geometrische Gegenbeispiele, nicht um gemessene Fahrbewegungen oder eine
qualifizierte Hardware-Trackinghülle. Sie widerlegen die Verwendung der idealen
Geraden allein als Beweis für alle benachbarten möglichen Fahrbahnen.

Der vorhandene Stage-3-Diagnosepfad wurde ebenfalls gelesen. Seine feste Folge
enthält 25 cm Vorfahrt und zwei 15°-Drehungen; seine vollständige Umfangsprüfung
passt nicht zur gebundenen Ausgangsfläche. Kein gültiger alternativer Realtest
aus diesem Pfad abgeleitet und keine Schutzprüfung zum Erzwingen eines Starts
entfernt. Ein historisch gerader Realabschnitt qualifiziert weder diese aktuelle
Quelle noch eine garantierte obere Abweichungsgrenze.

Ergebnis dieses Arbeitsgangs: keine neue Produktkorrektur oder Installation,
kein Stackstart, keine Action, kein Fahrbefehl und kein ausgeführter Realtest.
Der Auftrag zur tatsächlichen Fahrt bleibt unerfüllt. Keine neue allgemeine
Laborfreigabe fehlt. Ein Ersatz der konservativen Rasterprüfung benötigt einen
vollständigen kontinuierlichen Bewegungsnachweis einschließlich realer
Abweichungen oder zusätzliche echte Beobachtung der betroffenen Außenfläche.
Eine größere Zeitgrenze behebt diesen räumlichen Befund nicht.

Private reproduzierbare Nachweise: `exact-forward-sweep.py/.json` und
`exact-forward-deviation.py/.json` im bisherigen Geometrieordner. Originaldaten
und Koordinaten bleiben dort; die bestehenden Schutzregressionen wurden in
diesem Arbeitsgang ohne Produktänderung nicht erneut ausgeführt.

## 10.10.2026 – beauftragter Ersatz: kontinuierlicher Geradenprüfer

Der Nutzer beauftragt nun ausdrücklich einen funktionierenden Ersatz. Neuer
lesender Geometriekandidat `src/explore/explore/metric_start_sweep.py`, integriert
in `tools/kartierung/metric_start_geometrie_pruefen.py`. Der aktive Explorer
nutzt weiterhin die bestehende Startprüfung. Keine versteckte Aktivierung
oder Umdeutung des neuen Kandidaten in eine fertige Fahrfreigabe.

Der Kandidat prüft die ganze überstrichene Fläche einer geraden Vorfahrt bis
0,5 m. Für die gepaddete rechteckige Kontur werden die Extrema sämtlicher
Ecken über das gesamte deklarierte Winkelintervall analytisch berechnet;
Positionsabweichung wird zusätzlich eingeschlossen. Der vollständige
Translationskorridor folgt geometrisch daraus. Rasterzellen werden mit ihren
ganzen Polygonen geschnitten. Deshalb benötigt diese spezielle Rechnung keine
Halbzelldiagonale oder 10-mm-Reserve für ausgelassene Wegzwischenpunkte.
Sie ersetzt diese Näherungen durch eine kontinuierliche Überdeckung, nicht
durch eine punktweise kleinere Kontur. Die Winkel-/Positionshülle ist weiter
konservativ. Keine Aussage für Kurven, Rückwärtsfahrt oder Enddrehungen.

Eine anfänglich unbekannte Zelle entschuldigt ausschließlich ihren exakten
Schnitt mit der initialen gepaddeten Körperkontur; keine ganze Randzelle,
zusätzliche Trackingfläche oder Belegung. Neue Belegung/Unbekanntheit wird
bei jedem Aufruf gelesen, nichts als frei gecacht oder in Karten geschrieben.
Das Werkzeug arbeitet auf einer gespeicherten Momentaufnahme. Die feste
Live-Anker-/Historienbindung, tatsächliche Quellenfrische, Reglergrenzen,
Bremsbahn und Live-Wiederprüfung sind **nicht** durch diesen Baustein
qualifiziert. Jedes Ergebnis enthält `motion_authorized=false` und
`qualification=offline_geometry_only`.

Qualifikation: 38 neue Geometriefälle und neun ausgewählte bestehende
Start-Egress-/Schutzfälle bestanden, insgesamt 47 in 1,89 s, 52 nicht
ausgewählte bestehende Fälle. Darunter positiver fester Heckbestand,
Hindernis/Unbekanntheit zwischen freien Endpunkten, Belegung einer ursprünglichen
unbekannten Zelle, subzellige neue Fläche, Trackingseitenkontakt, konkaver
Scope, Rastergrenze, Koordinatendrehung und unabhängige Eck-/Trajektorienproben.
Ungültige Eingaben werden verworfen. Die neue Diagnose darf keinen Fahrbefehl
oder positiven Hardwarequalifikationswert erzeugen.

Separater Build von `explore` und unverändertem `amadeus_map_identity` in
`~/.local/share/amadeus/releases/ap06-start-sweep-20261010`, beide erfolgreich
in insgesamt 6,09 s. Die Überlagerungswarnung betrifft die ausdrücklich
separaten Entwicklungsoverlays. Keine API des vorhandenen Fahrprüfers geändert;
Bestandsinstallation unberührt. Tests und Realprobenvergleich importieren den
tatsächlich gebauten Kandidaten, dessen Pfad/SHA im privaten Ergebnis stehen.

Auf denselben gespeicherten Realproben ist die ideale 25-cm-Gerade auf beiden
Rastern positiv. Mit dem explizit nur als Geometrieversuch deklarierten Band
20 mm/0,05 rad bleiben 0,018506 m² außerhalb des bisherigen Polygons;
zusätzliche unbekannte Fläche: Rohkarte 0,017601 m², Kostenkarte 0,002572 m².
Keine Belegung im Prüfkorridor. Beide Varianten zusammen benötigten rund
29,6 ms (Rohkarte) und 9,1 ms (Kostenkarte) in diesem einzelnen Offline-Aufruf;
kein Last-/Echtzeitnachweis. Original-CDR-Hashes und Originalzeitstempel bleiben
erhalten, keine Behauptung aktueller Sensorbereitschaft aus diesen Altproben.

Ergebnis: getesteter Ersatzkandidat für die Geometrie, **noch kein funktionierender
aktiver Ersatz**. Kein neuer passiver Hardwarelauf oder Realfahrversuch, weil
bereits der gerätefreie Nachweis mit Abweichung negativ bleibt. Keine
Kundenfreigabe oder vollständige AP-06-Abnahme. Private Originalergebnisse,
Test-XML und reproduzierbarer Aufruf unter
`~/.local/share/amadeus/diagnostics/ap06-start-sweep-20261010`.

Rückfall: ausschließlich neuen Kandidatenimport/-ausgabe im Diagnosewerkzeug
und die beiden neuen Modul-/Testdateien zurücknehmen bzw. das neue temporäre
Overlay nicht laden. Alle vorherigen Encoder-/HWT-/Cachekorrekturen, alten
Belege und die aktive Startprüfung bleiben erhalten. Kein dauerhafter
Installations-, Autostart-, Git-Remote- oder Motorsteuerungswechsel.

## 10.10.2026 – Vorbereitung des begrenzten realen Fahrablaufs

Nutzer beauftragt die vollständige Vorbereitung. Private Skripte unter
`~/.local/share/amadeus/diagnostics/ap06-drive-preparation-20261010T1308Z`:
`start-stack.bash`, `bind-scope.bash`, `start-explorer.bash`, `run-mission.bash`
und `stop-run.py`; Ablauf in `FAHRABLAUF.md`, Kandidat/Hashes/Grenzen im
`prepared-manifest.json`, aktueller Befund in `preparation-result.json`.
Die aktive Variante ist vorbereitet, in diesem Arbeitsgang nicht gestartet.
Genau ein Missionsauftrag über bestehenden Mission Manager, vorhandene
Explorer/Nav2/Smoother/Collision/Base-Kette. Abbruch bei 90 s Missionszeit,
0,5 m aufsummiertem Encoderweg, 0,6 rad aufsummiertem Winkel oder erforderlichem
Quellen-/Haltfehler. Danach Cancel und höchstens acht Sekunden für frischen
Stillstand. Cancel-Schwellen sind keine Behauptung eines nachlauffreien Halts.

Vorprüfung: exklusiv rein lesend 20 FC03-Proben je Motor, konstante Positionen
und 0 RPM. Anschließend passiver Stack mit Recorder, `active_drive=false`,
`enable_auto_explore=false`, kein aktiver Basisprozess. Recorder vom
13:11:31 bis 13:14:32 UTC, 180,070 s vor regulärem Stopp. Letzter Bag-Encoderstatus
4.045 Publikationen, max. versuchte Paarzeit 98,551 ms, keine Verriegelung oder
erste Timingablehnung; späterer Live-Status 5.279 Publikationen ohne Fehler.
Alle aufgezeichneten Kommandos, gemessenen RPM und Encoderpositionen null;
Mission Manager im gesamten Bag idle. 675/675 Nahstatus beidseits gesund.

Recorder-Empfangszeiten, ausdrücklich nicht Verbraucher-/Quellenlatenzen:

| Quelle | Proben | p99 Empfangsalter | max. Empfangsalter | max. Stempelabstand |
|---|---:|---:|---:|---:|
| Wheel-Odom | 3.485 | 43,816 ms | 111,403 ms | 136,503 ms |
| HWT raw | 16.495 | 15,352 ms | 125,706 ms | 119,496 ms |
| HWT yaw | 16.425 | 14,473 ms | 127,910 ms | 160,486 ms |
| Scan | 1.741 | 19,010 ms | 119,834 ms | 202,476 ms |
| Nahstatus | 675 | 17,834 ms | 66,541 ms | 461,874 ms |

Erste Scopebindung mit `TF pose/reference missing/stale/future` nach ursprünglicher
Frist beendet. Dieser Fehler bleibt im privaten Original-Log. Neue aktuelle
Scope-/Posemessung und eine weitere begrenzte Bindung bestanden ohne angehobene
Fristen; `metric-bound-2.yaml` enthält aktuelle Session, Karte, Quellenbesitzer,
native TF-Herkunft und R5-Installationsbindung. Keine ursprüngliche Anfrage
überschrieben oder größere Fläche angenommen.

Nach Ende des 180-s-Bags zusätzlich genau sechs passive Explorerproben:
ursprüngliche `_metric_inputs(active=False)` jedes Mal gültig, aktive
Startinventare jedes Mal ungültig. Geradenkandidat auf aktueller Roh-/Kostenkarte
mit deklarierter 20-mm-/0,05-rad-Hülle ebenfalls negativ; letzte Probe Rohkarte
0,0175425 m² neue unbekannte Fläche, Kostenkarte 0,0024893 m². Keine Belegung
in dieser Prüfhülle. Geometrieproben nach dem Bag besitzen eigene Original-CDRs,
Stempel und Statusdaten; sie werden nicht dem vorher beendeten Bag zugerechnet.
Die Gesamtmessung einschließlich zusätzlicher Kandidatenrechnung dauerte
362–560 ms je Aufruf. Der Kandidat erteilt keine Bewegung und beansprucht
keine Hardwaretracking- oder Live-Frischequalifikation.

Beim Audit des vorhandenen privaten Missionsmonitors belegter Fehler gefunden:
`rpm_left/right` in `base_hardware/state_json` sind Sollwerte. Die neue private
Monitorversion verwendet `meas_motor_rpm_left/right`, verlangt tatsächlich
null RPM, endliche gemessene Geschwindigkeiten und Encoderfeedbackalter
höchstens unverändert 180 ms. Alte Monitor-/Nachweisdateien unangetastet.
Zwölf gerätefreie Gegenproben bestanden: Nullkommando mit noch drehendem Motor,
fehlende/NaN-RPM und veraltete Rückmeldung werden nicht als Stillstand anerkannt.
Bash-Syntax, Python-Kompilation und absolute Laufpfade geprüft. Kein aktiver
Missionsversuch aus der Monitorprüfung.

Explorer und Stack ausschließlich über ihre direkten, diesem Lauf zugeordneten
Launch-PIDs geordnet gestoppt; keine Prozessgruppe signalisiert. Recorder war
bereits beendet. Abschließend erneut 20 FC03-Proben je Motor: alle Positionen
unverändert und RPM null. Finaler Graph nur noch eigener temporärer
Snapshotknoten, serielle Geräte frei. Bestehende 1.048 Install-Dateien bytegleich,
keine hinzugefügt/entfernt, Originalcheckout sauber. Kein Push/Merge/Autostart.

Ergebnis: Vorbereitung ausführbar und dokumentiert, `prepared=true`, aber
`drive_ready=false`. Kein Fahrbefehl, kein aktiver Basisstart, keine Realfahrt.
Räumlicher Start-/Abdeckungsnachweis und reale Trackingqualifikation bleiben
vor Bewegung erforderlich; keine erneute pauschale Laborfreigabe ausstehend.
Rückfall: private Vorbereitung nicht aufrufen, temporäres R5-Overlay abwählen;
vorige eigene Korrekturen und Belege erhalten.


## Nachtrag: begrenzte LAB-Diagnose und reale Startzustände

Im separaten Checkout bleibt der bisherige feste Stage-3-Komponententest hinter
Fahrtor, Smoother, Collision Monitor und Base-Watchdog: 0,25 m vorwärts mit
0,08 m/s, +15° und −15° mit 0,10 rad/s; Stillstand zwischen den Phasen. Keine
Explorer-Mission und kein Nav2-Ziel als Ersatz für den negativen autonomen
Startnachweis. Die ausdrückliche LAB-1-Freigabe liegt vor.

Die Scope-Prüfung nutzte zuvor eine 0,414-m-Körperscheibe, obwohl der vorhandene
gepaddete Körper rechteckig ist. Für diese feste Diagnosesequenz wird nun dessen
vollständige kontinuierliche Winkel-/Translationshülle einschließlich einer
1,6-s-Anhaltehülle geprüft. Konvexe und konkave Polygongrenzen, Innenextrema,
seitliche Abweichung und unzulässige Bewegungen sind getestet. Drehung unmittelbar
am Start bleibt unzulässig. Kein unbekanntes Kartenfeld wird als frei markiert,
und die autonome Startprüfung bleibt unverändert. Der LAB-Bereich wird mit
aktueller Karte/TF gebunden; sein physischer Bezug bleibt während des Tests über
aktuelle absolute Encoder-Odometrie und den einmal gemessenen Anfangsbezug fest.
SLAM-Korrekturen dürfen den vom Menschen geprüften Bereich nicht verschieben.

Das Vorbereitungswerkzeug wartet bei einem einzelnen zu alten TF-Sample weiter
innerhalb seiner ursprünglichen Deadline; es akzeptiert keine alte Messung.
Ein Humble-Executor-Abbaurennen wurde durch Stop/Wake/Join vor Shutdown behoben.
26 gezielte Scope- und reale DDS-TF-Tests bestanden.

Private Belege: `~/.local/share/amadeus/diagnostics/ap06-lab-contour-20261010`.
Erster neuer passiver Recorder: 180,047 s, keine Bewegung, keine Encoder-
Verriegelung, maximale Paarzeit 81,371 ms. Erstes aktives R6-Preflight: keine
Fahrt, alter Quellenempfang im Diagnosemodus. R7-Preflight: keine Fahrt, falsche
Behandlung des leeren Missionsobjekts. Der Jetson startete unabhängig vom Agenten
neu; frühere Bindungen wurden verworfen. Danach 40 reine FC03-Proben: beide
Motor-RPM und Positionen null. R8 passiv positiv; R8 aktiv latschte die gemessene
319,610-ms-Abfragelücke trotz 17,386-ms-Paarzeit. Kein Start-Trigger.

R9-Build Base/LiDAR-Bringup erfolgreich (5,44 s). 125 Basistests sowie fünf
motorlose Ausgabe-/Ausfalltests bestanden; echte DDS-Ausgabe besitzt genau einen
Publisher und erhält originale Stempel. R9 passiver und aktiver Null-Vorlauf
positiv; dennoch später 211,452-ms-Quellenalter im Tor und Terminal-HOLD vor der
Diagnose. Der aktive Recorder endete nach 151,290 s geordnet, nicht nach 180 s.
Kein Start-Trigger, Encoderweg/-winkel null. Die Fehlerhistorie wird nicht
überschrieben. R10 enthält zusätzlich den korrigierten Abfrage-/Health-Mutex-
Ablauf; Build von Base, LiDAR-Bringup und Navigation erfolgreich (7,84 s),
177 gezielte Tests bestanden, vier passive DDS-Fälle in diesem Lauf abgewählt.
Ein ROS-Graph-Discovery-Rennen im neuen motorlosen Ownership-Test wurde durch
Warten auf die echte Namenszuordnung innerhalb derselben Deadline korrigiert.

Die Sichtlücken aus dem ersten Vorlauf bestehen weiter: Nahbereichs-Frame-
Gesundheit ist keine globale 64/64-Freiraumbescheinigung, LiDAR sieht nur seine
Ebene, Mastabschattung und fehlende OAK-Abdeckung werden nicht erfunden.
AP-06 bleibt bis zu den erforderlichen realen autonomen Nachweisen 0/3.

## Abschluss: reale feste LAB-Sequenz vollständig gefahren

R17 (`ap06-lab-current-sources-20261010`) startete am 10.10.2026 um
18:42:39 UTC, Abschluss um 18:43:25 UTC. Bestehender Diagnose-Trigger nahm den
Start an; `state=complete`, feste Sequenz und drei gemessene Stillstände
bestätigt. Vorwärtsphase einschließlich Nachlauf etwa 26,5 cm, gesamter
Encoderweg 0,275685 m einschließlich kleiner Dreh-/Quantisierungsanteile.
Gemessene Drehungen einschließlich Nachlauf etwa +16,45° und −16,24° bei
15° Soll je Phase. Abschließende Richtungsabweichung gegenüber diesem
Versuchsanfang etwa 0,10°. Kein externer Positionsmessstab als unabhängiger
Trackingnachweis; die Werte stammen aus tatsächlicher Positions-Encoderodometrie.
Keine Modbus-Lesefehler, keine Encoder-/Ausgabeprozessverriegelung, beide
Motor-RPM am Ende null und Rückmeldung frisch. Gesamtaufzeichnung 180,067 s,
Recorder geordnet beendet. Kein Explorerauftrag oder Nav2-Ziel ausgeführt.

Vorherige Bewegungen bleiben getrennte Belege: R12 fuhr 0,784 mm und stoppte
an seiner konservativen Anhaltehülle; R13 weitere etwa 20,015 mm und stoppte
an TF-Frische. R15 sendete wegen falschem Kartenepochenvergleich keinen Start.
R16 absolvierte Vorwärtsfahrt und erste Drehung, wurde beim Rückdrehen vom
privaten Rohwinkelvariationsbudget gestoppt (0,286212 m Encoderweg).
R16b fuhr 0,269274 m und stoppte nach gemeinsamer 1,3–1,4-s-Verarbeitungslücke
von Diagnose und Monitor. Im unabhängigen Bag liefen reale Quellen weiter;
im betroffenen Fenster maximal 72,502 ms Wheel-Headerlücke, 54,589 ms IMU und
306,612 ms Nahstatus. Keine dieser Teilsequenzen wird als Gesamtpositivlauf
gezählt. Die erfolgreiche R17-Wiederholung verwendet denselben ursprünglichen
physischen LAB-Scope-/Radanker, keinen nach Bewegung verschobenen Bereich.

### Korrekturen und tatsächliche Quellenbindung

R11–R16 beheben unbenutzte Portal-/Regionabhängigkeit der festen Diagnose,
scheinbare Aktivierung beim Idle-Stop, notwendige explizite Recoveryquittierung,
verzögerten Original-TF-Empfang, Nullimpulse aus Idle-Missionsstatus und den
Vergleich einer wachsenden Karte mit der festen Sessionepoche. Gemessene
vorzeichenbehaftete Restgeschwindigkeit wird mit vollständiger Anhaltehülle
geprüft; Diagnosekommandos bleiben strikt vorwärts bis 0,08 m/s und
|w| bis 0,10 rad/s. R17 verarbeitet die jüngste queued Originalprobe jeder
vorhandenen Quelle vor der Entscheidung, maximal zehn je Quelle, ohne Warten
oder neue Stempel. Keine eingegangene Probe bedeutet keine Altersauffrischung.
TF-Listener verarbeitet weiterhin alle tatsächlichen Kanten. Der private
Monitor bewahrt rohe Winkelvariation (R17 0,711438 rad), begrenzt aber die
Summe vollständiger Phasenwinkelspannen (0,574391 rad); Weg 0,5 m, Spannen
0,6 rad und Zeit 90 s je Versuch bleiben begrenzt. Vier Monitorgegenproben
einschließlich Originalabbruchwiedergabe bestanden.

R17-Navigationsbuild erfolgreich in 6,58 s. 87 verschiedene gezielte Fälle
bestanden, darunter zwei echte DDS-Frischeprüfungen; die zuerst fehlgeschlagene
neue Probe hatte einen Typfehler im Testsender, danach nachgeprüft. Private
XML-Dateien und `focused-test-final-summary.json` halten die Fallherkunft fest.
R14 wurde nur gebaut; R15/R16 enthalten dessen TF-Korrektur. Tatsächlich aktiv:
Base aus R10, Fahrtor aus R15, Diagnose aus R17. Installierte relevante
Pythonquellen sind bytegleich mit dem separaten Checkout. Torwechsel bewahrte
die tatsächliche begonnene Diagnosehistorie, Recoveryzählung und Journal;
keine Proben, Gesundheitswerte oder Befehle wurden wiederhergestellt. Neue
Quellen und explizite Quittierung qualifizierten die neue Instanz im Stillstand.

Aktueller Graph: ein Encoderpublisher `/base_hardware_feedback_output`, ein
RS485-Besitzer `/base_hardware`, HWT-Rohleser aus R3; `/odom` und
`odom → base_link` vom bestehenden HWT-EKF, Karten-TF vom bestehenden
SLAM-Toolbox-Stack. `/cmd_vel` ausschließlich vom Collision Monitor. Tatsächliche
DDS-GIDs, Installpfade und Gerätebesitzer im privaten Graphsnapshot, ursprüngliche
native TF-Herkunft in der unveränderten Scopebindung. Kein zweiter Navigator,
kein direkter ungegateter Fahrpublisher, kein synthetischer Sensorersatz.
Frühere R12/R13/R15-Bags verwendeten einen nicht publizierten Rohdiagnosetopic-
Namen; die tatsächlichen Kommandos liegen in Node-/Monitorlogs und der
Schutzkettenaufzeichnung. Ab R16 wird auch der korrekte Rohdiagnoseeingang
aufgezeichnet; alte Aufzeichnungsbefehle bleiben unverändert.

### Sensorzeiten des abschließenden 180-s-Bags

Die Alterswerte sind Header bis **Recorderempfang**, keine Behauptung über das
jeweilige entscheidungsinterne Alter im Fahrtor. Insbesondere eine verzögert
protokollierte Wheel-Probe wird nicht auf jung gestempelt oder als aktuelle
Bewegungsfreigabe benutzt. Ursprüngliche Frischegrenzen bleiben maßgeblich.

| Quelle | Proben | Headerlücke p99 / max | Recorderalter p99 / max |
|---|---:|---:|---:|
| Positions-Wheel-Odometrie | 2.902 | 64,0 / 90,4 ms | 39,2 / 327,9 ms |
| HWT-Roh-IMU | 16.276 | 21,6 / 242,1 ms | 21,3 / 200,3 ms |
| HWT-Gierrate | 16.243 | 21,6 / 242,1 ms | 17,7 / 122,7 ms |
| LiDAR | 1.717 | 105,3 / 201,9 ms | 30,9 / 307,4 ms |
| Nahbereichsstatus | 645 | 331,8 / 526,9 ms | 21,4 / 49,1 ms |

645/645 Nahstatusmeldungen beidseits framegesund. Dies bestätigt keine globale
64/64-Freiraumabdeckung: LiDAR-Ebene, Mastabschattung, nicht beobachtete Raumteile
und im Mapping deaktivierte OAK bleiben reale Sichtlücken. Kein Raum-/Portal-
oder kompletter autonomer Wohnungsnachweis. AP-06 weiterhin **0/3**.

### Geordneter Abschluss und Rückfall

Diagnose, einzelnes Tor, Explorer und Stack über belegte direkte PIDs geordnet
gestoppt; keine Prozessgruppe signalisiert. Finaler Graph nur eigener temporärer
Beobachter, alle seriellen Geräte ohne Besitzer. Danach 20 FC03-Proben je Motor:
40/40 null RPM, unveränderte tatsächliche Positionen, maximal 5,977 ms je FC03.
Alle 1.048 Bestandsinstall-Dateien einschließlich vorhandener Pythoncachedateien
bytegleich; keine hinzugefügt/entfernt, Originalcheckout sauber und bei
`23928d92f411473ed2644692a04aebdff0ffe803`. Separater Checkout weiterhin auf Basis
`e14ca31276b26be2d88397b310301dad3c4e9600`, lokale Korrekturen getrennt erhalten.
Kein Autostart, Push, Merge oder dauerhafter Bestandsinstallwechsel.

Private Rohbelege unter `~/.local/share/amadeus/diagnostics/ap06-lab-contour-20261010`:
`active-5/diagnostic-r17/trial-result.json`, `trial-events.jsonl`, `bag`,
`runtime-manifest.json`, `graph-during-trial.json`; zusammengeführte Auswertung
`real-trials-final.json`, `sensor-times-all-final.json`, `postflight-final.json`,
`graph-final.json` und `preservation-after-stop.json`. Reale Maps, Bilder,
Polygone und Bags bleiben außerhalb Git. Rückfall: eigene Prozesse stoppen und
separate Releaseumgebung verlassen; die bestehende Installation bleibt erhalten.

## Bewertung und nächste Schritte nach R17

Die feste LAB-Sequenz bestätigt echte Fahrt und Stillstand mit gültigen
Quellen. Sie prüft den expliziten Diagnoseeingang; regulärer Nav2-Auftrag,
selbst gewählte Explorerbeobachtung und autonome Gesamtmission bleiben eigene
Nachweise. Ursprüngliche A/B/C-Qualifikation 0/3; keine neue Kundenabnahme.

Die Vorwärtsphase zwischen Startbindung und erstem Nullwunsch dauerte
21,377 s. Diagnose-Callbacks zeigen nach der Anfangsglättung kontinuierliche
0,08 m/s. Im unabhängigen vollständigen Bag war `/cmd_vel` etwa 99,7 % dieser
Phase ungleich null; das zeitintegrierte Kommando beträgt ungefähr 1,680 m
und ist ausdrücklich keine tatsächliche Strecke. Positionsencoder melden bis
zum Umschaltpunkt etwa 0,251 m, Kartenpose etwa 0,248 m. Beide können Quellen
teilen; dies ersetzt keine unabhängige Distanzmessung. Die gemessene
Encoder-Geschwindigkeit steigt in 3-s-Abschnitten von etwa 0,003 bis 0,020 m/s,
am Ende etwa 0,022 m/s. Drehphasen jeweils 10,200/10,300 s statt eines bereits
qualifizierten Sollgeschwindigkeitsverlaufs. Keine periodischen Nullimpulse
der Schutzkette im vollständigen Bag als Erklärung dieser Langsamkeit.

Das Zusatzregister `0x000C` meldet dabei lange 122 RPM links, während die
Positionsdeltas langsam anwachsen. Nach dem vorhandenen Encoder-H2-Vertrag
ist dieses Register zusätzliche Beobachtung und kein Counts-Akzeptanzkriterium.
Eine Ursache oder neue Skalierung folgt daraus nicht. Die frühere wiederholte
Startimpuls-Ausgabe ist im aktuellen Quellpfad bereits korrigiert; tatsächlich
gesendete Motortransaktionen wurden in R17 nicht separat aufgezeichnet.
Rampenprofil 2000/400 ms ist keine unabhängige Messung seines realen Verlaufs.

Priorität ist deshalb eine begrenzte Qualifikation der Soll-/Antriebsübertragung:
wirkliche Register-/Starttransaktionen und wirksame Rampen zu frischen
Positionsdaten sowie unabhängig gemessener Strecke/Winkel korrelieren.
Nachlauf (R17 etwa 13 mm nach dem Umschaltpunkt), Richtung und Trackingreserve
unter tatsächlicher Last messen. Erst eine belegte Ursache korrigieren und
gezielt nachprüfen; keine pauschale Erhöhung von Fristen, Änderung bestätigter
Counts/Geometrie oder Vergrößerung des Scopes. Der physische LAB-Bereich bleibt
derselbe und muss beim nächsten Stackstart mit dem gefahrenen Versatz gebunden
werden. Keine automatische Rückfahrt oder neuer relativer Flächengewinn.

Danach den erfolgreichen Quellstand als eindeutigen separaten Kandidaten
zusammenführen: bisherige reale Kombination Base R10, Tor R15 und Diagnose R17
bleibt Referenz, Originalinstall erhalten. Geschlossene A/B/C-Gesamtfälle und
betroffene Regressionen auf genau diesem Kandidaten prüfen. Reproduzierbare
Kaltstarts und begrenzte reale Trackingprüfung ergänzen den einmaligen Erfolg.
Anschließend regulärer autonomer Auftrag mit erster selbst gewählter nützlicher
Beobachtung, gefolgt von drei Beobachtungsaufgaben und den bestehenden Passage-/
Rundweg-/Hindernis-/Halt-/Persistenzabnahmen. Kein manuelles Ziel als Ersatz
der autonomen Auswahl. Native App-Prüfung bleibt unter WE-M7 separat.

Private neue Auswertungen `next-step-command-analysis.json` und
`next-step-bag-command-analysis.json` unter dem bestehenden LAB-Diagnosepfad.
Die Kommandozeiten sind Callback- beziehungsweise Recorderempfang, keine
behaupteten Motorstartzeitpunkte. Diese Bewertung ist rein lesend hinsichtlich
der Hardware; kein neuer Stack oder Fahrversuch, keine Parameteränderung.
Der einzige aktuelle nächste technische Auftrag steht im [STATUS](STATUS.md).
