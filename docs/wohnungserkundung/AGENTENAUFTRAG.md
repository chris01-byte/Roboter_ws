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

## 4. Aktueller Folgeauftrag: ein begrenztes HWT-Recoverypaket

```text
PROJEKT: Amadeus / chris01-byte/Roboter_ws
REFERENZ: docs/wohnungserkundung/MASTERPLAN.md, Version 1.0 vom 27.09.2026
BASIS: STATUS.md, Integrationslinie docs/we1-integrationsbasis-audit
ERGEBNIS: Für einen nachgewiesenen transienten HWT-Rohstatusfehler den
Bewegungshalt, Erhalt desselben Explore-Auftrags, begrenzte
Quellwiederherstellung und geprüfte Wiederaufnahme als EIN Paket umsetzen.
Das erste Tor ist die Einzelursachen-Diagnose. Ist die Ursache nicht
recoverbar belegt, endet dieser Auftrag mit dem Diagnosebefund und ohne
funktionale Recoveryänderung.

TOR 1: URSACHE UND ORIGINALWERT
- Bestehende HWT-Statusquelle, Hwt601FusionHealth und Statusveröffentlichung
  im Mission-Gate nachvollziehen.
- Für die sechs bestehenden Rohstatusbedingungen (`ready`, `raw_data_ready`,
  Port, Sensor-Schreibmodus, `consecutive_errors`, `age_s`) maschinenlesbare
  Fehlernamen und die tatsächlich empfangenen Werte additiv ausgeben.
- Den bisherigen Sammelgrund `raw_driver_not_ready`, die Grenzwerte, das
  fail-closed Latch und die Nullausgabe des Gates unverändert lassen.
- Gerätefreie Tests für jedes Einzelprädikat, mehrere gleichzeitige Fehler,
  fehlende Statusnachricht und den unveränderten Gate-Stopp ausführen.
- Nur nach gesonderter Freigabe für Gerätezugriff die Rohstatusfolge bei
  motorlosem Vorlauf vollständig und ohne Wohnungsdaten erfassen. Den ersten
  verletzten Einzelwert und die Quellzeit mit dem Gate-Latch korrelieren.
  Ein synthetischer Test ersetzt diesen Beleg nicht.

TOR 2: BEGRENZTE FUNKTIONALE ÄNDERUNG NUR BEI TRANSIENTER URSACHE
- Die tatsächlich betroffene HWT-Lesefunktion/Verbindung in der vorhandenen
  Komponente begrenzt wiederherstellen; Anzahl und Frist der Versuche aus
  dem belegten Fehlerbild festlegen, nicht aus vermuteten Timeouts.
- Währenddessen im bestehenden Mission Manager/BT/Explorer den identischen
  Explore-Auftrag samt Goal-ID erhalten. Bewegungstor geschlossen halten,
  das einzige Nav2-Kind terminal canceln und verspätete Antworten abweisen.
- Vor Fortsetzung Roh-/Yaw-/Encoderstatus, VL53-Paar, Scan, TF/Pose,
  Kartenbindung und aktuellen freien Weg neu belegen. Erst danach genau
  ein Kindziel für denselben Auftrag zulassen. Keine alte Geschwindigkeits-
  nachricht und kein altes Nav2-Goal wiederverwenden.

NICHT-ZIELE
- Keine pauschale Frische-/Timeout-Lockerung und keine gleichzeitige
  Überarbeitung weiterer Latches. Kein neuer Supervisor, Rechnerreboot,
  zweiter Navigator oder neues Missionsmodell.
- Keine aktive Installation oder Fahrt aus diesem Auftrag. Ein motorloser
  Quelllauf erfordert getrennte Gerätefreigabe.

ERFOLG / GEGENFÄLLE
- Jede einzeln verletzte Bedingung ist mit Originalwert und Quellenalter
  eindeutig; fehlende, zukünftige, nicht endliche und widersprüchliche Werte
  bleiben fail-closed. Mehrfachfehler werden nicht verschleiert.
- Der bestätigte Einzelfehler stoppt sofort; die Auftrags-ID bleibt gleich;
  Wiederherstellung ist begrenzt; erst frische Quellen, Pose und aktueller
  Weg erlauben ein einziges neues Nav2-Kind.
- Dauerhafter Ausfall, falscher Port/Schreibmodus, fehlerhafte Kalibrierung,
  Nutzerabbruch und Not-Aus führen zu sicherem terminalem Zustand oder
  manueller Freigabe, niemals zu automatischer Wiederanfahrt.
- Gerätefreie Einzelfehler-, Stale-/Race-, Cancel- und Gegenfalltests sowie
  isolierter Build; reale Fortsetzung bleibt einer späteren Abnahme vorbehalten.

RÜCKFALL
- Diagnostik und die begrenzte Recovery-/Missionserhaltänderung getrennt
  revertierbar halten. Das heutige fail-closed Gate bleibt der Rückfall.

ABSCHLUSS
- Ursache des alten Laufs bleibt offen, bis der vollständige Rohstatus
  tatsächlich erfasst ist. Ohne Transienzbeleg kein Tor 2; den konkreten
  Nachweisfehlbetrag dokumentieren. Danach STATUS mit Ergebnis und genau
  einem nächsten Auftrag fortschreiben.
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
