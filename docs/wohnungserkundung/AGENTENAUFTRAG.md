# Agentenauftrag – Wohnungserkundung Amadeus

**Plan WE-1 · Version 2026-09-14 · Repository `chris01-byte/Roboter_ws`**

Arbeite an der schrittweisen Umsetzung des
[Gesamtplans](../WOHNUNGSERKUNDUNG_STRATEGIE.md). Dieses Vorhaben betrifft Amadeus,
nicht HomeMy. Eine dokumentierte Zielarchitektur ist keine implementierte Funktion
und keine Freigabe für Motoren oder eine unbeaufsichtigte Wohnungsfahrt.

## 1. Pflichtkontext bei jeder neuen Sitzung

Lies in dieser Reihenfolge:

1. Alle für die betroffenen Pfade geltenden `AGENTS.md`, beginnend mit
   [Root-AGENTS](../../AGENTS.md).
2. [Projektstatus](../../PROJEKT_STATUS.md), [Inventar](../INVENTORY.md) und die
   einschlägigen Entscheidungen in [Projektgedächtnis](../PROJECT_MEMORY.md).
3. [Status dieses Vorhabens](STATUS.md): tatsächlicher Stand, Blocker, letzter
   Nachweis und nächster zulässiger Schritt.
4. [Gesamtplan](../WOHNUNGSERKUNDUNG_STRATEGIE.md) und den betroffenen Eintrag in
   [Meilensteine](MEILENSTEINE.md).
5. Betroffene Implementierung, Tests und Konfiguration; bei Kartierung
   [Betriebswissen](../../tools/kartierung/README.md), vor Gerätezugriff die
   einschlägige [Hardwareübergabe](../ROBOT_TRANSFER.md) des richtigen Git-Stands.

Lade nicht routinemäßig alle historischen Logs und Fremdprojekte in den Kontext.
Erweitere gezielt um den konkret betroffenen Befund. Die Planunterlagen sind
verbindlich für das **Soll**; aktueller Code und datierte Messungen belegen das
**Ist**. Bei widersprüchlichen Quellen nicht die günstigere Behauptung auswählen,
sondern Commit, Profil und Evidenz vergleichen und den Konflikt offen eintragen.

## 2. Git-Basis zuerst klären

`main` ist die reguläre Entwicklungsbasis. Die Referenz der jüngsten besprochenen
Fahrt liegt dagegen bei `1d91229dc10ff4bb791938d49aae8e9808a5dfff` auf
`codex/hwt601-encoder-shadow`. Der Dokumentationszweig ist
`docs/wohnungserkundung-agentenplan`, ausgehend von Main-Commit
`05439c7a13d7a92e69b9eb4663e3a2a1b44626a1`.

Vor Änderungen Remote, Branch, HEAD, Arbeitsbaum und vorhandene Worktrees prüfen.
`git fetch origin` aktualisiert die Remote-Referenzen, ersetzt aber keine Prüfung
des tatsächlich auf dem Jetson gestarteten Installationsstands. Kein blindes
`git pull`, kein Wechsel einer laufenden Hardware-Arbeitskopie, kein automatischer
Merge des gesamten HWT-Zweigs, kein Force-Push, kein `reset --hard` oder Aufräumen
fremder Änderungen.

Neue Implementierung auf einem isolierten Themenbranch vom aktuellen `main`.
Fehlen notwendige HWT-/Portalvoraussetzungen dort, in WE-M0 einen gezielten
Integrationsvorschlag mit exakten Abhängigkeiten erstellen. Eine abweichende
Arbeitsbasis oder die Übernahme funktionaler Änderungen ausdrücklich abstimmen.
Reine Leseanalyse und synthetische Tests dürfen dadurch nicht mit einer angeblich
bestandenen Hardwarefreigabe verwechselt werden.

Ist diese Dokumentation noch nicht nach `main` gemerged, lies die vier Planunterlagen
über den Dokumentationsbranch, ohne deswegen die laufende Roboterinstallation
umzustellen. Nach Merge genügt der aktuelle Main-Stand. Halte fest, welchen
Dokumentationsstand du tatsächlich verwendet hast.

## 3. Umfang eines einzelnen Auftrags

Der erste Folgeauftrag ist **WE-M0/A: Bestands- und Integrationsprüfung ohne
Geräteaktivierung**, sofern der Status nicht bereits einen belegten neueren Stand
nennt. Erstelle keine vollständige neue Navigationslösung in einem Durchgang.

Bei jedem weiteren Auftrag:

- Benenne Meilenstein und abgegrenzten Teilschritt, Eingangsstand, betroffene
  Dateien, erwartete Wirkung, Tests und Rückfallweg vor dem Eingriff.
- Bearbeite ausschließlich diesen Schritt. Erweitere den Umfang nicht auf
  Kalibrierung, Treiber, Motorregelung, OAK, Netzwerke oder andere Projekte.
- Trenne reine Berechnung, passive ROS-Integration und bewegungswirksame Integration.
  Neue Funktion zunächst standardmäßig aus oder ausdrücklich passiv halten.
- Beende den Auftrag mit einem Ergebnis und einer eindeutigen nächsten Aufgabe.
  Ein bestandener Softwaretest startet niemals automatisch den nächsten Fahrtest.

Fehlende Geräte, ROS-Umgebung oder lokale Bags sachlich als nicht verfügbar
kennzeichnen. Keine synthetischen Daten als echte Fahrt ausgeben. Geeignete
synthetische Fixtures und Testpläne sind trotzdem zulässige Lieferobjekte.

## 4. Sicherheits- und Integrationsregeln

Der Gesamtplan WE-01 bis WE-12 und die bestehende hardwired/softwareseitige
Sicherheitskette gelten durchgehend. Diese Unterlagen autorisieren weder Bestromen
noch Fahrt. Vor realem Gerätezugriff beziehungsweise Bewegung sind die vorhandenen
Freigaberegeln der anwesenden Person und die jeweilige begrenzte Testabnahme
anzuwenden; alte Freigaben sind nicht dauerhaft übertragbar.

Keinen Test durch Deaktivieren von VL53, `collision_monitor`, Frischeprüfung,
Lokalisierungsprüfung oder Footprint-Padding zum Bestehen bringen. Keine zusätzliche
Motorbusöffnung und keine Umgehung des Missions-Gates. Ein "motorloser" Test ist
vorher anhand der tatsächlich gestarteten Nodes und Gerätepfade zu überprüfen;
ein bloßes `dry_run`-Label genügt nicht als Annahme über Hardwarezugriff.

Bei laufender Bewegung hat sicherer Stopp Vorrang vor Logging, Speichern oder
Reparieren. Bestehende Shutdown-Prozeduren verwenden; keine Prozessgruppen-Signale,
unbegrenzten Wiederanläufe oder blind wiederholten Navigationsziele.

## 5. Tests, Status und Nachweise

Verwende die [Statusstufen](MEILENSTEINE.md) getrennt für Software, Zielsystem und
physische Abnahme. Ein Gesamt-Häkchen ist erst zulässig, wenn alle für diesen
Meilenstein geforderten Nachweise vorliegen. Zahlen aus alten Protokollen sind
keine heute ausgeführten Tests.

Prüfe normales Verhalten und die relevanten Negativfälle: falsche Portalzuordnung,
verdeckte Sicht, Kartenkorrektur, fehlende Quellen, Abbruch, Blacklist, blockierter
Rückweg, veraltete Metadaten und Wiederanlauf. Tests sollen Verhalten prüfen, nicht
nur das Vorhandensein eines Parameternamens oder Quelltextfragments.

Pflege [STATUS.md](STATUS.md) bei jedem Ergebnis oder Blocker. Fachentscheidungen
dieses Vorhabens stehen dort im Entscheidungslog, ohne einen zweiten parallelen
Fortschrittsstand aufzubauen. Übergreifende Änderungen gehören zusätzlich mit
Verweis in `docs/PROJECT_MEMORY.md`; tatsächliche Jetson-Wirkung zusätzlich in
`docs/ROBOT_TRANSFER.md`. Bestehende historische Einträge nicht nachträglich
"grün" umschreiben.

## 6. Commit, Push und Übergabe

Vor einem Commit Diff und Dateiliste prüfen, passende Tests ausführen,
`git diff --check` verwenden sowie Geheimnisse und reale Wohnungsdaten ausschließen.
Keine Bags, realen Karten, Graphgeometrien, Kamerabilder oder Build-Verzeichnisse
mitnehmen. Nur den eigenen, thematisch abgegrenzten Dateisatz committen.

Commit-Nachricht: `typ: Grund der Änderung`; bei Hardwarewirkung Abnahmegrenze und
Rückfallweg nennen. Auf den eigenen Themenbranch pushen und Remote-HEAD prüfen.
Keinen fremden Branch löschen und keinen ungetesteten Funktionsmerge erzwingen.
Pull Request mit Zweck, Tests, offenen Gates, Hardwarewirkung und Rückfallweg.
Ein Push ist kein Deployment und ein Merge keine Fahrfreigabe.

Die Übergabe muss enthalten:

```text
Meilenstein / Teilschritt:
Dokumentationsstand und tatsächliche Codebasis:
Ergebnis und geänderte Dateien:
Ausgeführte Prüfungen mit Resultat:
Nicht ausgeführte Prüfungen und Grund:
Physische Abnahme / Freigabe: nicht erfolgt oder konkreter Nachweis
Offene Fehler, Risiken und Rückfallweg:
Commit, Remote-Branch und PR-Stand:
Nächster exakt begrenzter Schritt:
```

## 7. Startauftrag für die nächste Agentensitzung

> Lies zuerst alle geltenden AGENTS.md und die vier Unterlagen zur Wohnungserkundung:
> `docs/WOHNUNGSERKUNDUNG_STRATEGIE.md`,
> `docs/wohnungserkundung/AGENTENAUFTRAG.md`,
> `docs/wohnungserkundung/MEILENSTEINE.md` und
> `docs/wohnungserkundung/STATUS.md`.
> Sie liegen bis zum Merge auf `docs/wohnungserkundung-agentenplan`.
> Führe zunächst nur WE-M0/A aus, sofern kein neuerer belegter Status vorliegt:
> vergleiche aktuellen Main-, HWT-Referenz- und verfügbaren lokalen Stand,
> prüfe vorhandene Explorer-/Karten-/Semantikschnittstellen und liefere einen
> gezielten Integrations- und Prüfplan. Keine Fahrsoftware ändern, keine Geräte
> aktivieren, keine funktionalen Branches automatisch mergen und keine Fahrt
> auslösen. Aktualisiere den fachlichen Status mit nachgewiesenen Ergebnissen
> und dem nächsten abgegrenzten Schritt.
