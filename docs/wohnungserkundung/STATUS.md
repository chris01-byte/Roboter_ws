# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus · Stand 27.09.2026 · Stufe 3 weiterhin OFFEN/GELB**

**Aktuelle Entscheidung:** Konsolidierung statt Komplettneubau. Maßgeblich sind
[MASTERPLAN.md v1.0](MASTERPLAN.md), die unveränderte
[WE-Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) und
[MEILENSTEINE.md](MEILENSTEINE.md). Dies ist der einzige laufende WE-Iststand.

## 1. Sofortiger Arbeitsfokus

**Nächster Auftrag:** Aktuellen lokalen Parity-/WE-Kandidaten sichern, seine
Runtime- und Buildzusammenstellung eindeutig bestimmen, reproduzierbar
konsolidieren und die vorhandene Abort-/Latch-Inventur zusammenführen.
Ausführung gemäß [AGENTENAUFTRAG.md](AGENTENAUFTRAG.md).

Noch kein neuer Ganzwohnungslauf, kein kompletter Rewrite, kein pauschaler
OS-Neuaufbau und kein automatischer Merge. Noch keine Freigabe zum Ändern aller
Stop-/Latch-Regeln. Zuerst die tatsächliche Basis und das begrenzte erste
Recovery-Änderungspaket belegen. Bereits erledigte Arbeit wiederverwenden.

## 2. Quellenstand – Remote, lokal und berichtet getrennt

| Quelle | Aussage und Grenze |
|---|---|
| PR #101 / `codex/we1-hwt601-fusion` bei `40b5b49c9a92600484a0dc85c466930bc1680c60` | Bei dieser Ablage abgerufene Remote-Dokumentationsbasis; nicht automatisch der letzte lokale Parity-Install |
| HWT-Referenz `1d91229dc10ff4bb791938d49aae8e9808a5dfff` | Historisch dokumentierter Arbeitszimmer-Flur-Erfolg; keine Aufforderung zum Blind-Rollback |
| Spätere lokale Parity-/VL53-Recovery-Arbeit | Im Projektchat berichtet; vollständige Quell-/Install-Zuordnung in dieser Dokumentationsarbeit nicht am Roboter geprüft |
| Letzter im Chat gezeigter Bericht | Rundblick 361,7°, 1.188 beidseitig gesunde VL53-Statusmeldungen, danach `raw_driver_not_ready`; berichteter Teilnachweis, keine unabhängige Reproduktion |

Die PR-Beschreibung enthält ältere Zustände. Weder der Text eines PR noch dessen
Head allein beweist den lokal ausgeführten Stand. Im nächsten Auftrag exakte
Dateien, Versionen, Konfigurationen und Nachweise abgleichen; nicht vorhandene
Rohlogs, Profile oder Gerätezugriffe ausdrücklich als fehlend kennzeichnen.

## 3. Erhaltene Nachweise und aktuelle Grenzen

| Umfang | Stand |
|---|---|
| Bisherige „Stufe 1“ | Historisch als GRÜN dokumentiert; nicht gelöscht, gilt für die dort bezeichnete Basis |
| Bisherige „Stufe 2“ | Historisch gerätefrei GRÜN; nicht automatisch Abnahme der späteren Runtime |
| HWT-/Encoder-Preflight vom 26.09. | Im Vorgängerstatus zwei bestandene motorlose Zyklen dokumentiert |
| Begrenzter Bewegungstest | Im Vorgängerstatus `complete` und 0,270 m aus `/odom` dokumentiert; kein unabhängiger metrischer Gesamtfahrnachweis |
| Rundblick und VL53 nach lokaler Parity-Arbeit | Späterer Erfolg berichtet; Commit-/Install-/Log-Zuordnung noch zu sichern |
| Aktuelle HWT-Störung | Auslösende Einzelbedingung von `raw_driver_not_ready` in der zuletzt vorgelegten Evidenz nicht identifiziert |
| Aktueller Raumwechsel, Hindernisbewältigung und Missionsfortsetzung | Auf einem konsolidierten Gesamtkandidaten nicht vollständig real nachgewiesen |
| WE-M4 / WE-M5 / WE-M6 | Reale Abnahmen weiterhin gesondert offen; vorhandene Softwarebausteine nicht erneut entwickeln |

„Stufe 1/2/3“ sind bisherige Arbeitsbezeichnungen. Die eigentliche Roadmap
bleibt WE-D0 und WE-M0 bis WE-M7; keine pauschale Gleichsetzung der beiden
Nummerierungen und kein neuer Meilensteinplan.

## 4. Begrenzter Restumfang und Reihenfolge

1. Betriebsbasis konsolidieren und Audit-Iststand feststellen (aktueller Auftrag).
2. HWT-Erstursache belegen; einen durchgängigen Halt-/Recovery-/Fortsetzungsfall
   in der bestehenden Kette schließen und passende Gegenfälle testen.
3. Aktuelle Stufe-3-/Kernnachweise real schließen, einschließlich autonomem Ziel,
   Hindernisbewältigung, sicherer Befreiung, Türdurchfahrt und Weitererkundung.
4. WE-M4-Rundweg, dann WE-M5-Wiederaufnahme und WE-M6-Wohnung abnehmen.
5. Zuverlässigkeit und Kundentauglichkeit separat nachweisen.

Jeder Übergang erfordert die im Masterplan und im betroffenen Meilenstein
festgelegten Nachweise. Kein automatisches Abarbeiten aller Schritte aufgrund
einer Freigabe des ersten. Neue Nebenbefunde hier priorisieren statt einen
weiteren parallelen Masterplan zu eröffnen.

## 5. Entscheidung und Nachweis dieser Dokumentationsablage

**27.09.2026:** Christopher beauftragt die dauerhafte Referenz des im Chat
abgestimmten Masterplans. Die Grundentscheidung lautet: Fähigkeiten erhalten,
Runtime konsolidieren, Fehlerverantwortlichkeiten gezielt ordnen und anschließend
WE-1 abnehmen. Automatische Wiederaufnahme ist ein nachzuweisendes Produktziel,
keine pauschale Außerkraftsetzung von Schutzfunktionen.

Dieser Stand ändert ausschließlich Dokumentation und Agenteneinstieg. Keine
Runtime, Parameter, Firmware, Geräte oder Roboterinstallation wurden hiermit
geändert; keine neuen ROS-/Fahr-/Hardwaretests wurden durch diese Ablage belegt.
Die Dokumentationsbasis `40b5b49` wird dadurch nicht zur freigegebenen Runtime.

## 6. Historie ohne konkurrierenden Arbeitsauftrag

Der vollständige Vorgängerstatus ist byteidentisch unter
[STATUS-Snapshot bei 40b5b49](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_40b5b49.md)
erhalten (Git-Blob `6d4092f11880f19f2f0052be940910ced526bb15`, 145845 Bytes).
Der ältere [M3/U-Snapshot](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md)
bleibt ebenfalls erhalten. Historische „nächste Schritte“ sind keine heutigen
Freigaben. Quellenbeschränkungen und ursprüngliche Links siehe
[Archivhinweise](../archive/2026-09/README.md).

Fortschreiben: aktuelles Ergebnis, exakten Kandidaten, erste Fehlerursache,
Evidenzart und genau einen nächsten Auftrag nennen. Widersprüchliche alte
Zustände nicht wieder ungekennzeichnet in den Kopf kopieren. Der Masterplan
ändert sich nur mit einer expliziten Grundentscheidung.
