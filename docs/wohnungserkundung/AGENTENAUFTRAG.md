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

## 3. Aktueller Folgeauftrag: Integrationsbasis und Auditbestand konsolidieren

Erst nach ausdrücklicher Übergabe dieses Auftrags ausführen. Keine alten
Fahrtest-Prompts zusätzlich oder automatisch ausführen.

```text
PROJEKT: Amadeus / chris01-byte/Roboter_ws
REFERENZ: docs/wohnungserkundung/MASTERPLAN.md, Version 1.0 vom 27.09.2026
AUFTRAG: AKTUELLEN INTEGRATIONSSTAND SICHERN UND AUDITBESTAND KONSOLIDIEREN

ZIEL
Eine nachvollziehbare, reproduzierbare WE-/Parity-Basis herstellen und
exakt das erste begrenzte Recovery-Änderungspaket daraus ableiten.
Kein Neustart des gesamten Projekts und keine neue Roadmap.

A. BESTAND SICHERN
Lies Pflichtkontext und aktuellen STATUS. Prüfe nach git fetch origin
Remote-Refs, Arbeitsbaum, lokale Änderungen, Worktrees und bekannte Builds.
Sichere die zuletzt tatsächlich verwendete Parity-/VL53-Recovery-Arbeit.
Nicht aus PR #101 oder dessen Beschreibung auf den lokalen Install schließen.

Erhalte historische Referenzen und bereits bestandene Nachweise.
Keine laufende Roboter-Arbeitskopie umschalten, kein reset --hard,
kein Force-Push, kein Löschen fremder Branches und kein Blind-Merge.
Fehlenden lokalen Zugriff ausdrücklich nennen; keine Runtime erfinden.

B. EINEN KANDIDATEN FESTLEGEN
Ordne Code, externe Treiber/Submodule, Versionen, Kalibrierungen, Profile,
Overlay-Reihenfolge und tatsächlich aufgelöste Pakete einander zu.
Vergleiche nur relevante Unterschiede mit dem historisch bewährten
HWT601-/Türpfad bei 1d91229; nicht pauschal auf diesen zurücksetzen.

Stelle die bereits beabsichtigte Zusammensetzung in einer isolierten
Integrationslinie reproduzierbar zusammen. Erhalte heutige nachgewiesene
VL53-/HWT-/Antriebs-/Cancel-/Shutdown-Korrekturen. Keine funktionale
Neuentwicklung oder Sicherheitslockerung als Teil des Zusammenbaus.
Ungeklärte Integrationsentscheidungen sichtbar zur Entscheidung vorlegen.

Nutze einen frischen isolierten Build und weise Abhängigkeiten/Paketauflösung
nach. Ein Besitzer je Motorbus, produktivem TF und Navigationskind;
kein neuer aktiver WE-Navigator neben der bestehenden Ausführung.
Gerätefreie Tests in isolierter Umgebung. Kein aktiver Installwechsel.

C. AUDITBESTAND ZUSAMMENFÜHREN
Suche vorhandene Abort-/Latch-Audits auch in der gesicherten lokalen Arbeit.
Vorhandenes fortschreiben, nicht dieselbe Inventur erneut erfinden.
Erfasse im real relevanten Pfad Trigger, Datenquelle, Grenzwert, aktuelle
Stop-/Cancel-/Abort-/Latch-Wirkung, Verantwortlichen, Recovery und Evidenz.
Unterscheide vorübergehenden Halt, eingeschränkten Betrieb, terminalen
Hilfebedarf, echten Schutzstopp und Shutdownbefund. Keine Klassifikation
allein aus einem Sammelfehler oder aufgrund des Wunsches, weiterzufahren.

Beim letzten HWT-Abbruch zuerst die tatsächliche Einzelbedingung und den
Originalwert aus bestehenden Logs/Code bestimmen. Falls nicht vorhanden:
als Nachweislücke ausweisen und eng begrenzte Erstfehler-Diagnose vorschlagen.
Keine erfundene HWT-Ursache und keine Timeout-Erhöhung auf Verdacht.

D. ERGEBNIS LIEFERN
Liefergegenstand ist die konsolidierte Basis mit Build-/Testnachweisen,
aktualisierter Audit-Inventur und einem ersten begrenzten Umsetzungspaket:
Halt -> Auftrag bleibt erhalten -> betroffene Funktion wiederherstellen ->
Quellen/Pose/Pfad neu prüfen -> denselben Auftrag fortsetzen.

Benenne dafür die vorhandenen Komponenten, exakt nötigen Änderungen,
Erfolgs-/Gegenfälle und Rückfall. Noch nicht alle Latches umbauen und keinen
zusätzlichen großen Supervisor schreiben. Keine automatische Rechnerreboot-
Kette und kein Start von WE-M4/M5/M6.

STATUS aktualisieren: exakte Basis, echte Nachweise, verbliebene Konflikte
und genau ein nächster Auftrag. Reale Karten, Koordinaten, Bags und
Zugangsdaten bleiben lokal. Eigene Änderung auf Themenbranch veröffentlichen;
kein automatischer Merge, keine Geräteaktivierung, kein Deployment und
keine Fahrt in diesem Auftrag.

ABSCHLUSS
Getrennt ausweisen: Runtime identifiziert / Build reproduziert /
Auditbestand vollständig / erstes Recoverypaket entscheidungsreif.
DOKUMENTIERT, BESTANDEN, OFFEN oder BLOCKIERT nur für den jeweiligen Umfang.
Ein grüner Build ist weder eine neue Fahrfreigabe noch Stufe 3 grün.
```

## 4. Übergabe und Fortschreibung

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
