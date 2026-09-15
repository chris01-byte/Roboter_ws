# Agentenauftrag – Wohnungserkundung Amadeus

**WE-1 · Version 2026-09-15 · Repository `chris01-byte/Roboter_ws`**

Die [Gesamtstrategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) bleibt unverändert.
Dieses Vorhaben betrifft Amadeus, nicht HomeMy. Bereits erprobte Raumerkundung und
Türdurchfahrt sind Ausgangsbasis, nicht erneut zu entwickelnde Funktionen.
Aktuelle Priorität ist der zusammenhängende Softwareabschluss vor der erweiterten
Probefahrt. Dokumentation, Commit und Merge sind keine Geräte- oder Fahrfreigabe.

## 1. Pflichtkontext und Quellenrang

Vor Änderungen alle geltenden [AGENTS.md](../../AGENTS.md),
[Projektstatus](../../PROJEKT_STATUS.md), [Inventar](../INVENTORY.md) und einschlägige
Einträge im [Projektgedächtnis](../PROJECT_MEMORY.md) lesen. Dann den aktuellen
[WE-Status](STATUS.md), den betroffenen [Meilenstein](MEILENSTEINE.md), die Strategie
und den relevanten Code einschließlich Tests lesen. Bei Kartierung außerdem das
[Betriebswissen](../../tools/kartierung/README.md), vor freigegebenem Gerätezugriff
die passende [Hardwareübergabe](../ROBOT_TRANSFER.md) des tatsächlichen Git-Stands.

Strategie/Meilensteine definieren das Soll. Commitgebundener Code und datierte
Nachweise belegen das Ist. Der kompakte STATUS ist der laufende Einstieg; historische
Logs nur gezielt zu einem Befund nachladen. Bei Widersprüchen Datum, Commit,
Profil und Testart vergleichen und den Konflikt sichtbar zuordnen, nicht die
bequemere Aussage auswählen. Kein erneuter Start bei WE-M0/A, wenn sein Ergebnis
bereits belegt ist. Fehlende aktuelle Hardwareabnahme löscht keinen historischen
Fahrerfolg, gibt aber auch keinen geänderten Stand frei.

## 2. Git-Basis und Reviewgate

Der bei diesem Abgleich jüngste funktionale Stand ist M3/U, PR #91, Commit
`047455134894f700a115f6cea422479b99c702f6` auf
`feature/we-m3u-process-runtime-evidence`. Die ursprüngliche Dokumentation bei
`96cebee` ist nur die Planhistorie. Fortschritt nicht vom ursprünglichen
Dokumentationsbranch oder einem veralteten Main-Snapshot ableiten.

Nach `git fetch origin` Remote-Refs, HEAD, Arbeitsbaum und Worktrees prüfen.
Neuere Arbeit nicht überschreiben und bereits erledigte Schritte nicht wiederholen.
Der neueste PR allein bestimmt nicht die freigegebene Entwicklungsbasis;
Abstammung und vorhandene Zustimmung müssen passen. `main` bleibt reguläres
Integrationsziel. Die gestapelte WE-Basis wird für den explizit übergebenen
Folgeauftrag isoliert geprüft; sie ist weder Main noch Produktionsinstallation.

Vor weiterer funktionaler WE-Arbeit die bis M3/U vorhandene Kette reviewen,
relevante Prüfungen reproduzieren und den geprüften SHA samt Restbefunden benennen.
Gerätefreie Weiterarbeit darf auf dieser geprüften, isolierten Basis erfolgen,
wenn sie vom übergebenen Auftrag umfasst ist; dazu ist kein pauschaler Merge nötig.
Ungeklärte funktionskritische Reviewbefunde sperren die betroffene Weiterarbeit.
Main-Zusammenführung und zusätzliche funktionale HWT-Übernahmen bleiben gesondert
abzustimmen. Kein automatischer Merge, Force-Push, blindes Pull, `reset --hard`,
Löschen fremder Branches oder Wechsel einer laufenden Roboter-Arbeitskopie.

Die divergente HWT-Referenz `1d91229dc10ff4bb791938d49aae8e9808a5dfff` und der
lokal veränderte Jetson-Bestand werden nicht stillschweigend zur neuen Basis.
Installationspfade und Overlay-Reihenfolge müssen vor Zielsystembehauptungen
nachgewiesen werden; `git fetch` ist kein Installationsnachweis.

## 3. Ein abgegrenzter Auftrag ist ein funktionales Ergebnis

Bündele notwendige Schritte bis zu nutzbarem Verhalten statt bis zu einer einzelnen
Hilfsfunktion. Kleine Commits und gezielte Tests bleiben möglich. Vor dem Eingriff
Scope, vorhandene Anforderungen, Eingangs-SHA, betroffene Komponenten, erwartetes
Verhalten, Prüfplan und Rückfall kurz benennen. Keine neue Parallelroadmap.

Datenzuführung → automatische Ereignisse → Raum-/Aufgabenverwaltung → Zielwahl/
Abschluss → Speicherung/Wiederaufnahme sind die vorhandene Kette. Erledigte
Abschnitte wiederverwenden. Neue Module, Szenarien und Refaktorierungen benötigen
einen konkreten offenen Vertrag oder Fehlerbefund und einen benannten Verbraucher.
Kein ungenutztes Hilfsmodul als Abschluss einer Laufzeitintegration ausgeben.

Kein Nebenauftrag für Kalibrierung, Treiber, Motorregelung, OAK, Netzwerke, Arm,
KI-Raumnamen oder Komfortoberflächen. Keine neue Navigation und kein umfangreiches
zusätzliches Simulationsframework. Erweiterungen des genehmigten Umfangs einmal
als konkretes Paket abstimmen, nicht unbemerkt anwachsen lassen.

## 4. Sicherheits- und Integrationsregeln

WE-01 bis WE-12 sowie die bestehenden hardwired/softwareseitigen Schutzketten
gelten unverändert. Reine Berechnung, passive ROS-Anbindung und potenziell
bewegungswirksame Integration getrennt prüfen. Neue aktive Funktionen bleiben
standardmäßig deaktiviert oder benötigen ein explizites gültiges Profil.

Keine Geräteaktivierung, kein Deployment und keine Fahrt ohne gesonderte
Freigabe der anwesenden Person. Alte Fahrfreigaben nicht übertragen. Vor einem
„motorlosen“ Start Nodes und Gerätepfade prüfen; `dry_run` allein beweist nichts.
Gerätefreie ROS-Tests verwenden isolierte Domains und synthetische Gegenstellen;
keine reale Motor-/Sensorverbindung und keine Commands in die Produktionsdomain.

Tests nicht durch Abschalten von VL53, `collision_monitor`, Frische-/Lokalisierungs-
prüfung, Footprint-Padding oder Missions-Gates grün machen. Keine zusätzliche
Motorbusöffnung. Synthetische Geometrie-/Zeitwerte sind keine Hardwareparameter.
Nötige sicherheitsrelevante Änderungen separat begründen, freigeben und testen.

Bei Bewegung geht sicherer Stopp vor Logging/Speichern. Bestehende kontrollierte
Shutdown-Prozeduren verwenden, keine Prozessgruppen-Signale, endlosen Retries
oder blind wiederholten Navigationsziele. Dieser Dokumentationsauftrag selbst
startet weder Softwaretests mit Geräten noch irgendeine Bewegung.

## 5. Fertigkriterien und Statuspflege

„Softwareseitig fertig“ heißt: der vereinbarte Produktionspfad erzeugt seine
Entscheidungen aus den Eingabedaten und besteht die gerätefreie Gesamtkette.
Eine Testfixture darf Sensoren, Umgebung, Kartenmanager und Nav2 simulieren.
Sie darf aber nicht die gerade geprüfte Portalbestätigung, Durchfahrt,
Regionskorrektur oder Abschlussentscheidung als fertige Wahrheit einschleusen.
Solche Modultests bleiben gültig, sind jedoch kein Ersatz für den Gesamtnachweis.

Unterscheide Quell-/Modultest, integrierten Gerätefreitest, Zielsystemprüfung und
physische Abnahme. Null Commands im Fake-Nav2-Aufbau beweisen keine reale
Kollisions- oder Not-Aus-Funktion. Überlappende Testzahlen nicht addieren.
`MERGEABLE/CLEAN` ist kein funktionaler Review- oder Abnahmenachweis.

Aktualisiere STATUS-Kopf, Meilensteintabelle und Restliste gemeinsam. Überholte
Blocker datiert abschließen oder als historische Befunde kennzeichnen. Umfangreiche
abgeschlossene Logs bei Bedarf unverändert archivieren, mit klarer Geltungswarnung
und Quellenbezug. Keine zweite „aktuelle“ Statusdatei. Fachliche WE-Entscheidungen
bleiben im STATUS-Log, übergreifende Änderungen zusätzlich im PROJECT_MEMORY und
tatsächliche Jetson-Wirkung zusätzlich im ROBOT_TRANSFER.

## 6. Commit, Push und Übergabe

Vor Commit den eigenen Diff/Dateisatz prüfen, passende Tests und `git diff --check`
ausführen. Keine Tokens, Schlüssel, Zugangsdaten, echten Wohnungsgeometrien, Karten,
Bags, Kamerabilder, Build- oder Installationsartefakte einchecken.
Commitmuster: `typ: Grund der Änderung`; Hardwaregrenze und Rückfall dokumentieren.
Eigenen Themenbranch pushen, Remote-HEAD prüfen und PR gegen die passende
Reviewbasis erstellen. Keine funktionalen PRs automatisch mergen oder fremde
Änderungen löschen. Veröffentlichung ist kein Deployment.

Übergabe: geprüfte Basis/Scope; neu nutzbares Verhalten; geänderte Dateien;
tatsächlich ausgeführte und nicht ausführbare Tests getrennt; verbleibende
Blocker/Nachweise; Rückfall; Commit/Branch/PR; nächstes funktionales Ergebnis.
Fehlende Umgebung offen nennen. Kein grüner Softwaretest startet automatisch
Hardware und kein historisches Ergebnis wird nachträglich hochgestuft.

## 7. Folgeauftrag: Softwareabschluss ohne Geräte

Der folgende Auftrag wird erst nach ausdrücklicher Nutzerübergabe ausgeführt.
Er ersetzt alte Startaufforderungen zu WE-M0/A, aber keine Sicherheitsgrenzen.

```text
Projekt Amadeus / chris01-byte/Roboter_ws. Gesamtstrategie WE-1 unverändert.
Arbeite auf den zusammenhängenden gerätefreien Softwareabschluss hin,
nicht auf eine vorgezogene Probefahrt. Kein Neustart bei früheren Meilensteinen.

Lies die geltenden AGENTS.md, den aktuellen WE-STATUS, AGENTENAUFTRAG,
Strategie und betroffene Meilensteine. Prüfe nach git fetch origin die
abgestimmte neueste WE-Basis. Ausgangsreferenz dieses Auftrags ist M3/U,
PR #91, 047455134894f700a115f6cea422479b99c702f6, mit dem aktualisierten
Dokumentationsnachtrag. Neueren belegten Fortschritt erhalten.

A. Reviewgate vor funktionaler Weiterarbeit:
Prüfe die gestapelte WE-Kette, nicht nur den letzten PR. Reproduziere die
relevanten Pakettests und den vorhandenen echten Explorer-Prozessprüfer
in einem isolierten temporären Aufbau. Ordne bekannte Altbefunde gezielt
zu und benenne eine geprüfte commitgebundene Softwarebasis. Kein pauschaler
HWT-/Main-Merge, kein Löschen und keine Änderung der Roboterinstallation.
Bei funktionskritischen Reviewblockern erst diese begrenzt beheben oder
zur notwendigen Freigabe vorlegen. Keine weitere allgemeine Planungsrunde.

B. Danach innerhalb derselben geprüften WE-Linie das bestehende
Mehrraum-/Persistenzpaket schließen (WE-M3-Restnachweise, WE-M5 offline):
Verwende die vorhandene Produktionskette und vorhandenen Prüfer. Weise
Startraum -> Flur -> weiteres Zimmer -> derselbe Flur mit sich entwickelnder
Karte, Frontieraufgaben, automatischer Zielwahl und natürlichem erklärtem
Abschluss nach. Fortlaufende Kartenrevisionen während aktiver Ziele dürfen
nicht bloß eine endlose Cancel-/Retry-Schleife erzeugen. Sicherheits- und
Frischeprüfungen nicht zum Bestehen abschwächen.

Implementiere den minimalen WE-M5-Speicher-/Wiederaufnahmepfad über die
bestehenden Kartenmanager-Verträge: validiertes Schema, eindeutige
Kartenbindung, atomare Ablage, erhaltene Portal-/Regions-IDs und Restaufgaben.
Manuelle Raumdaten erhalten. Keine konkurrierende Kartenablage. Teste alle
bestehenden WE-M5-Pflichtfälle einschließlich beschädigter Daten, falscher
Karte, abgebrochenem Schreiben, Neustart ohne gültige Pose und doppelten Events.
Laden allein darf weder Navigationsziel noch Bewegung starten; nach erneut
gültigen Quellen benötigt Fortsetzung einen neuen expliziten Auftrag.

Verbinde Mehrraumtest und WE-M5 zu einem gerätefreien Gesamttest mit
Unterbrechung, Speichern, Neustart und expliziter Fortsetzung. Simulierte
Sensoren und Fake-Nav2 sind erlaubt; fertige Portal-/Durchfahrts-/Mergeurteile
als Ersatz der zu prüfenden Produktionsentscheidung nicht. Plane keine Route
heimlich für den Explorer vor. Füge Blockade, Datenfehler und Teilabschluss
gezielt hinzu, statt weitere beliebige Szenarien zu erfinden.

Kleine Commits sind möglich, Liefergegenstand bleibt das funktionierende Paket.
Neue Hilfsmodule nur bei benanntem Bedarf. Keine neue Navigation, KI-Modelle,
GUI-Erweiterung oder großes Simulationsframework. Notwendige zusätzliche
HWT-Übernahmen und sicherheitsrelevante Änderungen paketweise abstimmen.

Pflege STATUS-Kopf, Tabelle und Restliste konsistent. Berichte genau, welche
Gesamtkette selbständig bestanden hat und welche Zielsystem-/Hardwaregates
offen bleiben. Eigene Änderungen committen/pushen und zur Review stellen;
keine automatischen Merges, Geräteaktivierung, Deployments oder Fahrten.
```
