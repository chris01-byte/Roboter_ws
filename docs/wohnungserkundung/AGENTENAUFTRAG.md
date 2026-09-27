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

## 5. Aktueller Folgeauftrag: denselben begrenzten Realtest zur Freigabe vorlegen

Der auf PR #105 ergänzte gerätefreie Produktgraph enthält nun die echte
HWT-Yaw-Schattenverarbeitung einschließlich Bias-Schätzer. Vor der Korrektur
reproduzierte er den terminalen Latch, danach bestand er mit 0,260675 s
Rohdatenlücke, erneutem HOLD, Stillstands-/Pose-/Wegprüfung und Gate-ACK
(STATUS Abschnitt 5). Dies ist **kein** realer Recovery-Nachweis. Der erste
Realversuch auf `25ac048` blieb ohne RESUME; der historische
`raw_driver_not_ready`-Originalwert bleibt unbekannt. Sein ausstehender
Beobachterbericht über physischen Halt und wieder wirksame Motorsperre ist
separat einzuholen und nicht aus Encoderwerten abzuleiten.

```text
PROJEKT: Amadeus / chris01-byte/Roboter_ws
REFERENZ: MASTERPLAN v1.1, STATUS Abschnitt 5, Schritt 2.
BASIS: PR #105 / feature/hwt-hold-recovery-resume nach dem dokumentierten
      gerätefreien Roh-/Yaw-Nachweis.
ZIEL: Genau den bereits definierten WE-Initialscan als nächsten begrenzten
      HWT-Recovery-Realtest zur gesonderten Entscheidung vorlegen.

VORLAGE, NOCH KEIN START
- Den neuen Branch-HEAD, die auf dem Zielsystem tatsächlich gesourcten
  Paketpräfixe und Modul-/Profil-Hashes mit dem bestehenden Manifestwerkzeug
  sichern. Nach ROS, Slam-/LiDAR-Underlays, Vollbuild und Recovery-Overlay
  muss das isolierte Yaw-Overlay mit dem geänderten
  robot_state_estimation-Paket tatsächlich Vorrang haben. Der aktive Install
  bleibt unverändert. Das Profil bleibt
  hwt601_recovery_acceptance_params.yaml; Parity-Profil erreicht den
  Recoverypfad nicht. Scope-Verifikation bleibt falsch/leer.
- Den exakt gleichen Einzelumfang vorlegen: höchstens 40 s ab Explore-Start,
  höchstens 3 rad gemessene Drehung, Soll-Drehrate 0,08 rad/s, keine
  Translation, eine etwa 0,25-s-Pause ausschließlich des bestehenden
  HWT-Lesers mit garantiertem SIGCONT-Watchdog. Mission-Manager-Cancel vor
  Ende des Initialscans, bei Abweichung sofort. Keine Frontierfahrt.
- Vor Gerätezugriff die aktuelle Bestätigung für unabhängige Motorsperre,
  Stillstand, anwesende Person, erreichbaren Not-Aus und motorlosen
  Sensorlauf einholen. Motorlos Roh-/Yaw-/Biasstatus, Encoder, Wächter,
  Gate-Nullausgabe, Pose/TF, Scan/VL53 und Portbesitzer prüfen. Vor Bewegung
  freien Schwenkraum, Beobachter, unabhängigen Halt und eigene konkrete
  Fahrfreigabe für genau diesen Umfang klären; alte Freigaben gelten nicht.
- Recorder vor dem Stack starten. Roh-IMU, korrigierte Gierrate, Roh-/Yaw-/
  Encoder-/Wächterstatus, Gate-Ein-/Ausgabe, gemessene Bewegung, Pose/TF,
  Karten-/Wegstand, Mission-/Task-ID und Kindzielstatus gemeinsam mit
  Originalzeiten sichern. Rohmessalter, Statusalter und internes age_s
  getrennt berichten.
- Erfolg nur bei realem Bewegungshalt mit Beobachterbeleg, erhaltenem
  Auftrag, frischem Encoder-Stillstand, unverändertem Bias, neuen gültigen
  Yaw-Daten, stabilen Quellen, aktueller Pose/Kartenbindung, Gate-ACK und
  Fortsetzung desselben Rundblickauftrags ohne altes Kommando. Der
  Initialscan belegt keinen Nav2-Kind-Cancel oder Türpfad.
- Dauerfehler, Reconnect, falsche Sensoridentität, ungültige IMU, Zeitfehler,
  Not-Aus, Nutzerabbruch oder fehlende Pose/Stillstand verlangen Abbruch
  ohne automatische Wiederanfahrt. Danach Stack und Recorder sauber beenden,
  Ports freigeben und Rückfall auf den gesicherten PR-#104-Latchkandidaten
  bereithalten.

GRENZEN
- Diese Vorlage ist keine Geräte- oder Fahrfreigabe. Keinen Realtest,
  Installwechsel, Merge oder neue Wohnungsfahrt automatisch ausführen.
- Keine Parameterlockerung, kein Gesamtgrün für Stufe 3 und keine Arbeit an
  WE-M4/M5/M6.
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
