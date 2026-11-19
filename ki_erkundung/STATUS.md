# KI-Erkundung – aktueller Status

**Stand 19.11.2026:** Die Linie ist angelegt (Entscheidung des
Projektinhabers vom 19.11.2026, MASTERPLAN §10). [Konzept v1.0](KONZEPT.md)
steht. **Am Roboter und am KI-Rechner ist für diese Linie noch nichts
gelaufen.** In der Hauptlinie läuft parallel der Realtest SH-9; dieser Ordner
berührt ihn nicht.

Dies ist der einzige Iststand dieser Linie. Der Stand der Hauptlinie steht
ausschließlich in `docs/wohnungserkundung/STATUS.md`.

## Arbeitsliste

**Aktiv (Entwicklung, ohne Roboter): Stufe KI-0 vorbereiten.** Werkzeuge für
den Trockenlauf bauen und in der Entwicklungsumgebung prüfen: Aufnahmeformat
der Blickrunde, vermessene Vorschläge aus dem LiDAR, Nummern im Bild und
Kartenskizze, Frage an den KI-Rechner, Prüfung der Antwort, Auswertung.

**Danach:** Auftrag KI-0 (Blickrunden aufnehmen, am KI-Rechner auswerten).
Er wird erst geschrieben und übergeben, wenn SH-9 ausgewertet ist und der
Projektinhaber ihn anfordert. Am Roboter läuft immer nur ein Auftrag.

**Offen, vom Projektinhaber zu klären (erst für den Auftrag KI-0 nötig):**

1. Wie wird Amadeus für die Blickrunden gedreht: mit dem Joystick oder von
   Hand bei gesperrten Motoren?
2. Wer bedient den KI-Rechner beim Trockenlauf (ein Agent dort oder der
   Projektinhaber selbst), und wie kommen die Aufnahmen vom Jetson dorthin?

**Geparkt:** Anschluss der KI-Wahl an die vorhandene Erkundung (Entscheidung
vor KI-2); Raumnamen in der App (KI-4).

**Erledigt:** Konzept v1.0 und Trennregeln (19.11.2026).

## Nachweise

| Datum | Was | Wo geprüft | Ergebnis |
|---|---|---|---|
| 19.11.2026 | Ordner, Konzept, Verankerung | Repository | angelegt; kein bestehendes Paket, Profil oder Werkzeug geändert |

## Genau ein nächster Schritt

Werkzeuge für KI-0 fertigstellen und hier prüfen.
