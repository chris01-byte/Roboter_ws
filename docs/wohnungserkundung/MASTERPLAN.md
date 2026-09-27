# WE-1 – verbindlicher Masterplan für Konsolidierung und robuste Wohnungserkundung

**Version 1.0 · 27.09.2026 · Amadeus / `chris01-byte/Roboter_ws`**

**Entscheidungsgrundlage:** Im Projektgespräch mit Christopher abgestimmter
Masterplan; zur dauerhaften Referenz für alle beteiligten Agenten abgelegt.
Dies ist eine Ziel- und Arbeitsentscheidung, keine behauptete Implementierung,
Hardwareabnahme, Auslieferungsfreigabe oder Erlaubnis zum Start einer Fahrt.

> Vorhandene Fähigkeiten erhalten. Einen reproduzierbaren Betriebsstand
> konsolidieren. Fehlerbehandlung gezielt ordnen. Danach denselben Kandidaten
> schrittweise bis zur zugänglichen Wohnung abnehmen.

## 1. Geltung und eindeutige Dokumentzuständigkeit

Dieser Masterplan konkretisiert das Vorgehen **innerhalb von WE-1**. Er ersetzt
weder das Produktziel der [Gesamtstrategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md)
noch die fachlichen Abnahmen in [MEILENSTEINE.md](MEILENSTEINE.md).
Es entsteht keine zweite Roadmap und kein WE-M8.

| Dokument | Verbindliche Rolle |
|---|---|
| [AGENTS.md](../../AGENTS.md) und einschlägige Unteranweisungen | Allgemeine Arbeits-, Sicherheits- und Repositoryregeln |
| `MASTERPLAN.md` | Stabile Entscheidungen, Arbeitsreihenfolge und Änderungsgrenzen |
| [STATUS.md](STATUS.md) | Einziger aktueller WE-Iststand: geprüfte Basis, Nachweise, offene Punkte und nächster Auftrag |
| [AGENTENAUFTRAG.md](AGENTENAUFTRAG.md) | Arbeitsvertrag und ausführbarer, begrenzter Folgeauftrag |
| [MEILENSTEINE.md](MEILENSTEINE.md) | Bestehende WE-D0/WE-M0 bis WE-M7 und ihre Abnahmen |
| [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) | Datiertes Projektgedächtnis, nicht automatisch heutiger Arbeitsauftrag |
| [ROBOT_TRANSFER.md](../ROBOT_TRANSFER.md) | Tatsächliche Installations-/Betriebsübergabe und Rückfallweg |

Frühere P1–P5-Prompts sind historische Arbeitspakete, keine parallele aktuelle
Meilensteinfolge. Frühere Einzelaufforderungen zu weiteren Fahrversuchen oder
pauschalem Zurückspielen werden durch den aktuellen Auftrag eingeordnet.
Keine ältere Chatantwort oder Archivdatei ohne Standprüfung ausführen.
Bei Widersprüchen den konkreten Konflikt benennen; keine bequemere Aussage wählen.
Sicherheitsregeln werden durch diesen Plan nicht außer Kraft gesetzt.

## 2. Entscheidungen, die nicht bei jedem Fehler neu verhandelt werden

- **Kein Komplettneubau der Software, keine pauschale Neuinstallation des Jetson.**
  Eine defekte Umgebung rechtfertigt nur den nachgewiesenermaßen nötigen Eingriff.
- **Kein blinder Rücksprung auf einen historischen Branch.** Historisch erprobte
  Tür-/Frontier-/Rundblickfunktionen sind Vergleichsreferenz und werden gezielt
  wiederverwendet; neuere belegte Korrekturen bleiben erhalten.
- **Eine Integrationslinie, ein aktiver Kandidat, ein aktueller Arbeitsauftrag.**
  Alte Builds bleiben als Rückfall erhalten, nicht als undokumentierte Laufzeitmischung.
- **Keine neue Navigation und kein vorsorglicher zusätzlicher Supervisor.**
  Bestehenden Mission Manager, Behavior Tree, Explorer, Nav2 und vorhandene
  Prozess-/Lifecycle-Funktionen zuerst verwenden. Fehlende Verantwortung explizit
  zuordnen, nicht einen zweiten Befehlsgeber hinzufügen.
- **Keine vollständige Audit-Inventur bei jedem Einzelbefund wiederholen.**
  Den einmaligen Audit fortschreiben; danach begrenzte Änderungspakete bearbeiten.

Behalten werden die vorhandenen Sensor-/Antriebspfade, Encoder plus HWT601,
SLAM, Nav2, VL53-Nahbereichserkennung, Portalgedächtnis und Kartenverwaltung,
soweit für den jeweiligen Kandidaten nachgewiesen. Eine aktuelle Einbindung
oder Abnahme darf nicht allein aus der Existenz einer Datei abgeleitet werden.
Amadeus und HomeMy bleiben getrennte Projekte.

## 3. Arbeitsreihenfolge innerhalb der bestehenden Roadmap

Die folgenden Schritte sind Arbeitspakete, **keine neuen Meilenstein-IDs**.
Erledigte WE-Nachweise werden wiederverwendet und nur bei betroffener Regression
gezielt erneut geprüft. Die umgangssprachliche „Stufe 3“ ist nicht mit jedem
Detail des ursprünglichen WE-M3 gleichzusetzen; STATUS ordnet beide Begriffe zu.

### Schritt 1 – aktuellen Integrationsstand sichern und reproduzierbar bauen

**Zuordnung:** Aktualisierung der Betriebsbasis aus WE-M0/A, kein Neustart aller
früheren WE-M0-Arbeiten.

Den tatsächlich zuletzt verwendeten lokalen Parity-/WE-Kandidaten erfassen:
Quell-SHAs, lokale Änderungen, externe Treiber/Submodule, Versionen, Profile,
Buildpräfixe und Paketauflösung. Remote-PR, lokaler Quellstand und ausgeführtes
Install getrennt dokumentieren. Lokale Änderungen sichern, nicht überschreiben.

Eine eindeutige Integrationsbasis und einen wiederholbaren Build/Startweg
herstellen. Maschinenbezogene Dateien und private Karten bleiben lokal;
Versionen, Hashes und datensparsame Nachweise ins Repository. Fachlich passende
heutige Korrekturen erhalten. Der alte HWT-Türstand ist Referenz, nicht Default.

**Ergebnis:** Ein frischer isolierter Build erzeugt die festgelegte Zusammenstellung.
Genau ein Besitzer je Motorbus, produktivem Odometrie-TF und Navigationsauftrag;
keine versteckte Abhängigkeit von zufällig gesourcten Alt-Overlays.
Quellstand, Abhängigkeiten, Konfiguration, Startweg, Nachweise und Restfehler
sind eindeutig zugeordnet. Noch keine neue Wohnungsfahrt.

### Schritt 2 – Audit abschließen und einen Wiederaufnahmefall durchgängig schließen

**Zuordnung:** Robustheits-/Integrationsrest der bestehenden WE-Kette,
insbesondere WE-M3 und der aktuellen Stufe-3-Arbeit.

Alle tatsächlich bewegungswirksamen Stop-/Abort-/Latch-Bedingungen einmal
inventarisieren: Auslöser, Datenquelle, Grenzwert, Reaktion, Verantwortlicher,
Wiederanlaufbedingung und Evidenz. Nicht nur Fehlertexte sammeln.

Danach zuerst **einen vollständigen vertikalen Fall** umsetzen:
Störung -> sicherer Halt -> Auftrag bleibt erhalten -> betroffene Funktion
wiederherstellen -> aktuelle Quellen/Pose/Pfad prüfen -> denselben Auftrag
fortsetzen. Der berichtete HWT-Rohstatusabbruch ist der erste Kandidat;
seine tatsächliche Einzelursache muss vorher belegt werden.

Vorhandene VL53-Recovery und sonstige lokale Arbeit zunächst lesen und zuordnen.
Nicht parallel dieselbe Funktion neu bauen. Weitere passende Fehler übernehmen
danach dasselbe begründete Muster in kleinen, überprüfbaren Änderungen.

**Ergebnis:** Gerätefreier integrierter Nachweis von Wiederaufnahme und
Gegenfällen; echte Schutzfehler verhindern weiterhin die Wiederanfahrt.
Keine pauschale Erhöhung von Frische-/Kollisionsgrenzen.

### Schritt 3 – konsolidierten Kern real abnehmen

**Zuordnung:** Betroffene WE-M0/B-/WE-M3-Zielsystemnachweise und vollständiger
realer Abschluss der aktuell offenen Stufe 3.

Auf demselben festgehaltenen Kandidaten die bestehenden Pflichtfälle prüfen:
autonomer Start, Rundblick, selbst gewähltes Ziel, frühe Umfahrung, notwendiger
Nahbereichsstopp mit sicherer Befreiung, geometrisch lösbare Wand-/Ecksituation,
Mission fortsetzen sowie Tür vollständig passieren und dahinter weiterarbeiten.
Die Fälle dürfen in getrennten begrenzten Aufbauten stattfinden.

Zusätzlich einen definierten vorübergehenden Fehler erst gerätefrei, dann im
kontrollierten Realaufbau prüfen: Halt, erfolgreiche Wiederherstellung und
Fortsetzung desselben Auftrags. Dauerhafte und gefährliche Gegenfälle prüfen.
Kein manuelles Nav2-Ziel oder Entfernen der Barriere als Autonomieerfolg.

Kriterien und Zahl der Wiederholungen **vor** der Abnahme festlegen. Drei
vollständige Wiederholungen sind ein vorgeschlagener Einstieg, kein schon
beschlossener Zuverlässigkeits- oder Auslieferungsnachweis. Rohdaten und
äußere Beobachtung von bloßen Sollbefehlen/Odometrieanzeigen unterscheiden.

**Ergebnis:** Aktuelle reale Kernabnahme einschließlich Schutz- und
Fortsetzungsfällen. Ein bestandener Rundblick allein macht Stufe 3 nicht grün.
Danach unmittelbar WE-M4, keine erneute allgemeine Optimierungsrunde.

### Schritt 4 – bestehende WE-M4, WE-M5 und WE-M6 abarbeiten

| Meilenstein | Ergebnis nach bestehender Roadmap |
|---|---|
| WE-M4 | Arbeitszimmer -> Flur -> weiteres Zimmer -> zurück in denselben Flur; stabile Portal-/Regionsidentität und real bestätigte Durchfahrten |
| WE-M5 | Karte und Erkundungswissen konsistent speichern; Neustart, gültige Wiederlokalisierung und kontrollierte Fortsetzung offener Aufgaben |
| WE-M6 | Zugängliche Wohnung wiederholt erkunden; vollständigen Abschluss von blockiertem Teilstand unterscheiden |

Bereits vorhandene M1/M2-/Mehrraum-/Persistenzsoftware prüfen und integrieren,
nicht neu erfinden. Bekannte Türen bleiben zulässige Rückwege; eine besuchte Tür
ist nicht für Transit gesperrt. Kein falscher Vollabschluss bei unerreichbaren
Restaufgaben oder mangels Sensordaten. WE-M7 bleibt nachgelagerte App-Transparenz.

### Schritt 5 – Kundentauglichkeit gesondert nachweisen

Keine Auslieferung allein aufgrund einer erfolgreichen Wohnungsfahrt erklären.
Längere Einsätze, wechselnde Umgebungen/Startpositionen, Wiederanläufe und
kontrollierte Sensor-/Prozess-/Kommunikationsausfälle gesondert abnehmen.
Vorab Zielgrößen für Missionsabschluss ohne Eingriff, Eingriffshäufigkeit,
Recoverydauer/-häufigkeit und sichere Fehlerreaktion festlegen.

Häufiges erfolgreiches Neustarten ist noch keine Zuverlässigkeit. Offene
Speicherfehler wie `buffer overflow` müssen eingegrenzt und vor Produktfreigabe
bewertet/behandelt sein. Testfortschritt und Produktsicherheitsnachweis getrennt
führen. Kein erfundenes WE-M8 und keine Produktzertifizierung behaupten.

## 4. Verbindliches Fehler- und Wiederaufnahmeprinzip

> Bewegung bei Gefahr oder unzureichendem Zustandsnachweis rechtzeitig stoppen;
> eine sicher wiederherstellbare Störung darf nicht unnötig den Auftrag vernichten.

Drei Zuständigkeiten: **Schutzkette** entscheidet über momentane Bewegung;
**Subsystemverantwortlicher** über dessen begrenzte Wiederherstellung;
**bestehende Missionssteuerung** über Auftragserhalt, Neuplanung und Hilfebedarf.

| Situation | Zielverhalten; Umsetzung und Freigabe müssen nachgewiesen werden |
|---|---|
| Recoverbare Daten-/Statuslücke | Bewegung soweit erforderlich sperren, Mission halten, begrenzt wiederherstellen und neu prüfen |
| Teilweise eingeschränkte Wahrnehmung | Nur nachgewiesen sichere eingeschränkte Bewegung zulassen; sonst Halt. Unbekannt ist nicht frei |
| Hindernis oder unzugängliches Ziel | Gefährliche Bewegung verhindern, sicheren Alternativweg/andere Aufgabe prüfen; Tür und Aufgabe nicht vergessen |
| Nicht wiederherstellbarer Zustand | Sicherer Stillstand, Teilstand/Auftrag sichern und klaren Hilfebedarf melden; auch bei Software- oder Lokalisierungsfehlern möglich |
| Expliziter Not-Aus, Nutzerabbruch, kritischer Aktuatorfehler | Keine automatische Rücksetzung oder Wiederanfahrt; Ursache und ausdrückliche Wiederfreigabe erforderlich |
| Ausschließlich beim Shutdown beobachteter Fehler | Vom Fahrergebnis getrennt dokumentieren; nicht allein wegen des Auftretens nach SIGINT als harmlos einstufen |

Sofortige Stoppschwelle, Warte-/Recoverybudget und terminale Eskalation sind
getrennte Entscheidungen. Keine willkürlichen Universalzeiten, keine
Endlos-Restartschleifen. Sicheren Stillstand nicht durch bloßes Nullkommando
behaupten. Safety-Reaktion hat Vorrang vor Protokollierung und Speicherung.

Wiederaufnahme verlangt neue gültige Messungen, geeignete stabile Beobachtungsfolge,
notwendige Kalibrierung, konsistente Pose/TF/Kartenbindung, freien aktuellen Pfad
und weiterhin gültigen Auftrag. Alte Goals/Commands dürfen nicht wieder aufleben;
maximal ein aktives Navigationskind. Ein neuer EKF-Ausgabestempel ersetzt keine
frischen Eingänge. HWT-Bias nicht während Bewegung neu kalibrieren.

Ein einzelnes verworfenes Sample ist nicht automatisch ein Hardwaredefekt.
Umgekehrt darf ohne sichere Fortsetzbarkeit nicht bis zum Nachweis eines
Kabelbruchs weitergefahren werden. Hardware-/Software-Not-Aus nicht umgehen,
keine Freiraumbehauptung aus fehlenden VL53-Daten, keine blinde Dreh-/Rückfahrt.

Automatische Stack-/Rechnerneustarts sind **kein aktueller Implementierungsauftrag**.
Sie benötigen vorher eigene Nachweise für Persistenz, Wiederlokalisierung und
unabhängige Antriebssperre. Laden gespeicherter Daten allein startet keine Fahrt.

## 5. Regeln gegen Verzetteln und unbemerkte Regressionen

Ein Integrationsverantwortlicher führt den Kandidaten. Weitere Agenten dürfen
parallel analysieren/reviewen/testen, aber nicht gleichzeitig unkoordiniert
Betriebsprofile, Quellstände oder aktive Hardware verändern.

Vor jedem Auftrag knapp festhalten: Planversion, WE-Bezug, Istbasis, genau ein
Ergebnis, erlaubte Änderungen, bewusst ausgeschlossene Themen, Tests und Rückfall.
Nur den in STATUS aktuellen Auftrag ausführen; kein automatisches Weiterlaufen
aller Schritte dieses Dokuments. Bereits belegte Ergebnisse nicht grundlos neu
öffnen. Betroffene Integration nach Änderungen trotzdem gezielt prüfen.

Jede Abweichung braucht Fehlerbeleg oder vereinbarte Anforderung. Änderungen an
Ziel, Architektur, Reihenfolge, Akzeptanz- oder Sicherheitsgrenzen erfordern eine
explizite Nutzerentscheidung und einen versionierten Planeintrag. Nebenbefunde
priorisieren und im STATUS parken statt sofort neue Arbeitspakete zu starten.

Ein gültiger begrenzter Sitzungsspielraum vermeidet wiederholte identische
Rückfragen; er ersetzt keine aktuellen Betriebsbedingungen. Nach Not-Aus,
relevantem Umbau, unklarem Zustand oder Umfangswechsel Freigabe neu klären.
Dokumentation/Commit/Push/Merge allein sind niemals Geräte- oder Fahrfreigabe.

## 6. Nachweise und Abschluss eines Auftrags

Getrennt führen: `dokumentiert`, `software_geprüft`, `zielsystem_geprüft`,
`physisch_abgenommen`; daneben `offen`, `blockiert` oder begründet nicht nötig.
„Nicht ausgeführt“ ist weder bestanden noch der Nachweis eines Fahrfehlers.
Tests mit synthetischen Eingängen und echte Fahrten nicht gleichsetzen.

Jeder Abschluss nennt Ausgangs-/Ergebnis-SHA, Profil-/Abhängigkeitsbezug,
wirklich ausgeführte Tests, Evidenzpfade, unveränderte Grenzen, Restfehler und
**genau den nächsten Schritt**. Keine unbelegten Prozentsätze oder Zusage
„nur noch dieser letzte Fix“. Grün gilt nur für den ausdrücklich geprüften Umfang.

## 7. Pflege und sofortiger Einstieg

Nur STATUS enthält den laufenden Iststand. Bei neuem Befund zuerst diesen
fortschreiben; MASTERPLAN nur bei einer geänderten Grundentscheidung versionieren.
Den aktuellen ausführbaren Auftrag in AGENTENAUFTRAG aktualisieren, überholte
Aufträge eindeutig historisch kennzeichnen. Archive behalten ihre Originalbytes.

**Jetzt:** Schritt 1 und die zugehörige Audit-Bestandsaufnahme gemäß
[AGENTENAUFTRAG.md](AGENTENAUFTRAG.md). Keine weitere Wohnungsfahrt und kein
vollständiger Rewrite aus diesem Dokument ableiten.

**Änderungsprotokoll:** 27.09.2026 – v1.0: Konsolidierung statt Komplettneubau;
ein dokumentierter Kandidat, begrenzter Recovery-Umbau, reale Kernabnahme,
danach WE-M4/M5/M6 und separate Produktreifeprüfung. Frühere Parallelpläne
werden nicht als zusätzliche Roadmap fortgeführt.
