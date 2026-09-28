# Agentenauftrag – Wohnungserkundung Amadeus

**WE-1 · Version 27.09.2026 · Repository `chris01-byte/Roboter_ws`**

Verbindlicher Einstieg ist [MASTERPLAN.md v1.1](MASTERPLAN.md).
Der laufende Iststand und der nächste Auftrag stehen in [STATUS.md](STATUS.md).
Die [Gesamtstrategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) und die
[WE-Meilensteine](MEILENSTEINE.md) bleiben erhalten. Kein paralleler P1–P5-Plan.
Dieser Text ist eine Arbeitsreferenz, keine automatische Geräte-/Fahrfreigabe.

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

## 5. Abnahmevorlage: ein HWT-Fall mit aktivem Nav2-Kindziel

**Aktueller Torstand vom 28.09., zweiter passiver Vorlauf:** Der Nutzer
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
**keine Fahrt**. **Einziger nächster Schritt:** Rückwärtigen Schwenkraum
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
Diese Vorlage ist der konkrete **Freigabeentscheid: derzeit NO-GO**. Sie
ist kein Auftrag, eine weitere Vorlage zu schreiben oder Geräte zu starten.

### Kandidat und derzeitige Sperren

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

### Feste Annahmebedingungen für genau einen künftigen Versuch

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
3. **Autonomes Kind:** Der unveränderte Produktpfad muss nach seinem
   vollständigen Initialscan selbst eine offene Frontieraufgabe und einen
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
   Initialscan, HOLD und RESUME; höchstens **35 s ab erster aktiver
   Kindziel-UUID**; höchstens **0,60 m kumulierte gemessene Translation**.
   Zuerst erreichte Grenze löst Mission-Manager-Cancel aus. Scan-Sollwert
   bleibt 0,08 rad/s und dessen 280-s-Produkttimeout unverändert. Im
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

**Damals nächster einzelner Schritt:** Den freien Geradeauskorridor ab aktueller
Startpose mit Endpunkt und seitlicher Begrenzung im dann laufenden Kartenframe
vor Ort markieren/bestätigen und lokal neu binden. Danach das
Karten-/Scope-/Runtime-Tor anhand des isoliert wiederhergestellten
Produktkandidaten schließen und motorlos prüfen. Erst dann kann eine
gesonderte Freigabe für den gesamten begrenzten Einzelversuch eingeholt
werden. Das autonome Kindziel darf erst **im freigegebenen Produktlauf nach
dem echten Initialscan** entstehen; es ist eine harte Bedingung **vor**
Fault Injection und vor jeder Kindziel-Fortsetzung. Fehlt es, Cancel ohne
Injektion und Ergebnis `TESTFALL NICHT AUSGELÖST`. Die konkrete
Fahrfreigabe lautet derzeit **NEIN**. Keine Geräte oder Fahrt aus dieser
Vorlage, kein Merge, kein TOR 2 und kein Stufe-3-Gesamtgrün.

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
