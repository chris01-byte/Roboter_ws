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

## 4. TOR 1 softwareseitig abgeschlossen: HWT-Erstfehlerdiagnose

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
ein neuer Lauf beweist die alte Ursache nicht rückwirkend. TOR 2 ist **nicht**
zur funktionalen Umsetzung freigegeben.

## 5. Aktueller Folgeauftrag: HWT-Fahrabbruch und Stillstandsfenster vergleichen

```text
PROJEKT: Amadeus / chris01-byte/Roboter_ws
REFERENZ: MASTERPLAN v1.0 und aktueller STATUS
BASIS: Alter Fahrabbruch mit `raw_driver_not_ready` bei 1790492567.5659919;
vollständig aufgezeichneter motorloser Lauf vom 27.09.2026 auf
`c4295fcdacf817b33b53f17e38ac106bf01ae9e2`, Ergebnis B im STATUS.
ERGEBNIS: Aus ausschließlich vorhandenen Belegen die Betriebsunterschiede
und Zeitfolgen so eng vergleichen, dass genau eine priorisierte noch zu
messende Auslösebedingung benannt werden kann. Reichen die Daten dafür nicht,
die verbleibende Nachweislücke konkret feststellen.

EINGÄNGE
- Altes lokales Fahr-Bag und vorhandene zugehörige Logs unter
  `~/.local/share/amadeus/tests/parity-real-20260927-vl53-recovery`;
  dokumentierte Grenzen im STATUS beachten.
- Neues lokales Bag, Manifest, Bedingungen und Auswertung unter
  `~/.local/share/amadeus/tests/hwt-tor1-20260927-run-nDR2Re/`.

VERGLEICH
- Zeitachsen und die belegten HWT-/Encoder-/Wächterzustände unmittelbar vor
  und nach dem alten Latch mit dem neuen 120-s-Fenster nach Bias-Readiness
  vergleichen. Messalter, Status-Empfangsalter und `age_s` getrennt halten.
- Last- und Betriebsbedingungen nur aus tatsächlich belegten Startargumenten,
  Paketständen, Logs und Topics zuordnen. Das historische Bag enthält keinen
  HWT-Rohstatus; seinen Originalwert nicht aus gesunden neuen Meldungen
  ableiten. Keine zweite allgemeine Inventur und keine neue Hypothesenliste.
- Genau einen nächsten Nachweisfall oder die Unentscheidbarkeit aus den
  vorhandenen Daten in STATUS festhalten; AGENTENAUFTRAG entsprechend
  fortschreiben.

GRENZEN
- Nur lokale Dateien lesen und Dokumente fortschreiben. Kein Roboterprozess,
  Portzugriff, Aktor, Fahrtest, Parameter- oder Softwareänderung.
- TOR 2, Latch-Reset und automatische Recovery nicht beginnen. Eine spätere
  Geräteaktion erfordert einen eigenen abgegrenzten Auftrag und Freigabe.
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
