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

## 5. Aktueller Folgeauftrag: ersten HWT-Recoveryfall begrenzt real abnehmen

Der motorlose Zielsystemcheck auf `91bc6bf` wurde mit echten Quellen
durchgeführt und danach sauber beendet (Details und lokaler Manifestpfad in
STATUS Abschnitt 5). Die wirksame Setup-Kette braucht den dokumentierten
LiDAR-Underlay und `amadeus_slam_toolbox_ws`. Das Abnahmeprofil bleibt mit
`wohnungserkundung_accessible_scope_verified=false` und leerem Scope-ID;
keine Scope-Freigabe setzen. **Die Fahrphase ist ein eigener, aktuell
freizugebender Teil desselben Auftrags.** Der dafür vorgelegte Einzelumfang
ist höchstens 40 s ab Explore-Start, höchstens 3 rad gemessene Drehung,
Soll-Drehrate 0,08 rad/s, keine Translation, eine etwa 0,25-s-Pause nur des
HWT-Lesers mit unabhängig abgesicherter Fortsetzung. Danach den bestehenden
Mission-Manager-Cancel vor Ende des 360°-Initialscans auslösen; bei
unerwartetem Zustand früher abbrechen. So darf aus diesem Versuch keine
Frontierfahrt entstehen.

```text
PROJEKT: Amadeus / chris01-byte/Roboter_ws
REFERENZ: MASTERPLAN v1.1 und aktueller STATUS, Schritt 2.
BASIS: PR #105 / feature/hwt-hold-recovery-resume mit dem in STATUS
beschriebenen gerätefreien ROS-Graph-Nachweis.
ZIEL: Genau einen definierten kurz stale HWT-Rohmessungsfall während eines
begrenzten WE-Initialscans real prüfen. Der historische
raw_driver_not_ready-Originalwert bleibt unbekannt.

VOR JEDEM GERÄTESTART
- Eine für genau diesen Lauf geltende lokale Bestätigung einholen:
  Roboter still, unabhängige Motorsperre wirksam, anwesende Person,
  Not-Aus in Reichweite und motorloser Sensorlauf freigegeben.
- Den tatsächlich verwendeten Quell-Commit, Paketpräfixe, Modul-/Profil-
  Hashes, Underlays, Treiber, Konfiguration und Startargumente mit
  tools/kartierung/hwt_diagnose_manifest.py auf dem Zielsystem erfassen.
  hwt601_recovery_acceptance_params.yaml muss als installiertes
  explore_params_overlay aufgelöst werden;
  hwt601_parity_params.yaml erreicht die WE-Recovery nicht. Keinen
  aktiven Install ungeprüft wechseln und keinen zweiten Motor-/Portbesitzer
  starten. Rückfall ist der gesicherte PR-#104-Latchkandidat.
- Motorlos bei active_drive=false, enable_auto_explore=false und
  use_hwt601_odometry=true Roh-IMU, Gierrate, Bias, Encoder, Wächter,
  Gate-Nullausgabe, TF/Pose, VL53, LiDAR und Not-Aus prüfen. Bei
  Widerspruch beenden; keine Parameteränderung und keine Fahrt.

FAHRTEIL NUR NACH NEUER KONKRETER FREIGABE
- Einen einzigen langsamen Initialscan, freien begrenzten Bewegungsraum,
  unabhängigen Halt, Beobachter, Messfenster und Abbruchregel vorab
  festlegen. Nur einen Stack mit active_drive=true,
  enable_auto_explore=true, use_hwt601_odometry=true und dem expliziten
  Recovery-Abnahmeprofil starten; der Motorbus hat einen Besitzer.
- Während der laufenden Explore-Action den bestehenden HWT-Leseprozess
  genau einmal etwa 0,25 s pausieren und auch bei Abbruch garantiert
  wieder fortsetzen. Nur eine kurz stale Rohmessung des weiterhin
  identischen Treibers zählt als geplanter Fehler. Disconnect/Reconnect,
  falscher Port oder Biasverlust sind kein Ersatz und verlangen Abbruch.
- Roh-IMU, korrigierte Gierrate, Roh-/Bias-/Encoder-/Wächterstatus,
  Gate-Ein-/Ausgabe, Odometriegeschwindigkeit, TF/Pose, Karten-/Wegstand,
  Mission-/Task-ID und Kindzielstatus synchron mit Originalzeiten erfassen.
  Messalter, Statusempfangsalter und internes age_s getrennt halten.
- Erfolg nur bei belegtem realem Bewegungshalt, erhaltenem Explore-Auftrag,
  bestätigtem Encoder-Stillstand, stabilen Quellen, aktueller Pose und
  gültigem Wegbeleg sowie Fortsetzung des Rundblicks. Ein Initialscan
  belegt keinen Nav2-Kind-Cancel, keine Türfahrt und keine vollständige
  Wohnungserkundung. Bleibt der definierte Fehler aus, als nicht
  reproduziert melden.
- Bei dauerhaftem Quellenfehler, Not-Aus, Nutzerabbruch, fehlendem
  Stillstand, ungültigem TF/Pfad oder anderer Fehlerklasse sicher beenden;
  keine automatische Wiederanfahrt. Rückfall und manuellen Halt bereithalten.

GRENZEN
- Dieser Dokumentauftrag ist keine Geräte-, Install- oder Fahrfreigabe.
- Kein automatischer Merge, keine Grenzlockerung, kein Stufe-3-Gesamtgrün
  und keine Arbeit an WE-M4/M5/M6.
```

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
