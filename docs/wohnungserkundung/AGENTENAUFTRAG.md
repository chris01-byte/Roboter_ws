# Agentenauftrag – Wohnungserkundung Amadeus

**WE-1 · Version 27.09.2026 · Repository `chris01-byte/Roboter_ws`**

Verbindlicher Einstieg ist [MASTERPLAN.md v1.0](MASTERPLAN.md).
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
Quellzuordnung, frischer Teilbuild, Tests, fehlgeschlagener Vollbuild,
Abort-/Latch-Inventur und abgegrenztes Recoverypaket stehen ausschließlich im
[STATUS.md](STATUS.md). Die Arbeitskopie `~/roboter_ws` wurde nicht umgeschaltet;
keine Runtime aktiviert, kein Merge und keine Fahrt.

Der letzte HWT-Fehler ist im lokalen Bag auf den Wechsel
`raw_sources_ready` → `raw_driver_not_ready` bei `1790492567.5659919`
eingegrenzt. Das Bag enthält keinen `/shadow/hwt601/raw_status_json`-Topic;
die verletzte Einzelbedingung und ihr Originalwert fehlen. Der Vollbuild ist
wegen des `behaviortree_cpp`-CMake-Exportpfads blockiert; Teilbuild und
gerätefreie Tests sind getrennt im STATUS bewertet.

## 4. Aktueller Folgeauftrag: HWT-Rohstatus-Erstfehler sichtbar machen

```text
PROJEKT: Amadeus / chris01-byte/Roboter_ws
REFERENZ: docs/wohnungserkundung/MASTERPLAN.md, Version 1.0 vom 27.09.2026
BASIS: STATUS.md, Integrationslinie docs/we1-integrationsbasis-audit
ERGEBNIS: Den konkreten HWT-Rohstatus-Prädikatfehler ohne Änderung der
Bewegungs-/Schutzwirkung diagnostisch sichtbar machen.

UMFANG
- Bestehende HWT-Statusquelle, Hwt601FusionHealth und Statusveröffentlichung
  im Mission-Gate nachvollziehen.
- Für die sechs bestehenden Rohstatusbedingungen (`ready`, `raw_data_ready`,
  Port, Sensor-Schreibmodus, `consecutive_errors`, `age_s`) maschinenlesbare
  Fehlernamen und die tatsächlich empfangenen Werte additiv ausgeben.
- Den bisherigen Sammelgrund `raw_driver_not_ready`, die Grenzwerte, das
  fail-closed Latch und die Nullausgabe des Gates unverändert lassen.
- Gerätefreie Tests für jedes Einzelprädikat, mehrere gleichzeitige Fehler,
  fehlende Statusnachricht und den unveränderten Gate-Stopp ausführen.

NICHT-ZIELE
- Keine Frische-/Timeout-Änderung, kein Auto-Reconnect/Restart und keine
  Wiederanfahrt.
- Keine neue Navigation, kein Supervisor, kein Auftragserhalt-Umbau.
- Keine aktive Installation, kein Roboterstart, keine Fahrt. Ein späterer
  motorloser HWT-Quelllauf zur Feldwertaufnahme ist ein eigener Schritt und
  wird nicht automatisch aus diesem Codeauftrag abgeleitet.

ERFOLG / GEGENFÄLLE
- Jede einzeln verletzte Bedingung ist im Status eindeutig; Originalwerte und
  Quellenalter sind lesbar, ohne Rohdaten anderer Sensoren auszugeben.
- Gate bleibt bei jedem ungültigen oder stale HWT-Status blockiert.
- Fehlender, zukünftiger, nicht endlicher oder widersprüchlicher Wert bleibt
  fail-closed. Mehrfachfehler dürfen keinen Fehlergrund verschleiern.

RÜCKFALL
- Diagnostische Felder entfernen; altes Statusschema und das unveränderte
  fail-closed Verhalten bleiben als Referenz erhalten.

ABSCHLUSS
- Ursache des alten Laufs bleibt offen, bis ein vollständiger HWT-Rohstatus
  tatsächlich erfasst ist. Keine einzelne Ursache aus einem synthetischen Test
  ableiten. STATUS danach mit Ergebnis und genau einem nächsten Auftrag
  fortschreiben.
```

## 5. Übergabe und Fortschreibung


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
