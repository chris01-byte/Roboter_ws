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

## 5. Aktueller Folgeauftrag: HWT-Roh-/Yaw-Vertragskollision gerätefrei klären

Der **einzige** freigegebene Realversuch auf PR #105 ist beendet. Der
synthetisch ausgelöste Rohmessungs-Kurzfehler führte zum wirksamen HOLD,
aber der kalibrierte Yaw-Schatten verriegelte die dabei entstandene
0,261-s-IMU-Lücke dauerhaft als `imu_datenluecke_neustart_noetig`
(aktuelle Grenze 0,10 s). Dadurch entstand `yaw_missing_stale_or_invalid`
als `TERMINAL_FAULT`; es gab kein RESUME. Einzelwerte, Runtime-Manifest und
lokales Bag stehen in STATUS Abschnitt 5. Der alte Fahrfehler bleibt davon
unabhängig und unbekannt.

```text
PROJEKT: Amadeus / chris01-byte/Roboter_ws
REFERENZ: MASTERPLAN v1.1, STATUS Abschnitt 5, Schritt 2.
BASIS: PR #105 / feature/hwt-hold-recovery-resume, Realversuch auf 25ac048.
ZIEL: Genau die nachgewiesene Kollision zwischen Rohdaten-Kurzfehler,
kalibriertem Yaw-Schatten-Latch und HWT-HOLD/RESUME gerätefrei klären.

- Bag, Erstfehler, Yaw-Status und Codevertrag des einmaligen Realversuchs
  gemeinsam auswerten. Die 0,10-s-Lücke des Yaw-Schattens, die 0,20-s-
  Rohmessungsfrische und die 0,35-s-Yaw-Frische getrennt behandeln.
- Für diese eine Fehlerklasse entscheiden, ob Bias/Yaw nach der Lücke ohne
  unerkannte Drehung und ohne neue Stillstandskalibrierung sicher wieder
  gültig werden können. Bei fehlendem Beweis bleibt der terminale Latch
  bestehen; dann diesen Pause-Trigger ausdrücklich als nicht recoverbar
  einordnen und einen anderen belegbar recoverbaren Testfehler festlegen.
- Nur falls die Sicherheitsbedingung belegbar ist: kleinste Änderung an der
  bestehenden HWT-Schatten-/Recovery-Kette. Keine pauschale Latch- oder
  Timeoutlockerung. Fail-closed Stop, Auftragserhalt, tatsächlicher
  Stillstand, frische Quellen, aktuelle Pose/Wegprüfung und Gate-ACK bleiben
  notwendig.
- Den vorgesehenen Produktstart über Mission Manager, BT, Explorer und Gate
  mit synthetischen Sensoren gerätefrei auf HOLD und entweder begründeten
  RESUME oder terminalen Ausgang prüfen. Dauerfehler, ungültige IMU,
  Nutzerabbruch und Not-Aus dürfen keine Wiederanfahrt auslösen.
- STATUS, PROJECT_MEMORY bei einer übergreifenden Entscheidung und
  ROBOT_TRANSFER bei einer späteren Installwirkung fortschreiben. Build,
  Tests und Rückfall auf PR #104 dokumentieren.

GRENZEN
- Kein weiterer Geräte- oder Fahrversuch, keine Aktoren, kein aktiver
  Installwechsel, keine neue Recoveryarchitektur, kein automatischer Merge.
- Keine Frischegrenze auf Verdacht erhöhen, keine historische Ursache
  behaupten, TOR 2 oder Stufe 3 nicht pauschal grün setzen.
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
