# Archiv: Auftrag KI-F9N „Auswerten und Erproben im Stand, ohne Fahrt“ – ausgeführt am 24.11.2026 (abends)

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`b5af3ee`). Er ist **nicht mehr aktuell**.

Jetson, mit Christopher, 20:56 bis 22:13. **Kein Build:** Release
`kif8-20261123_2138` mit `kif8.env`, beide unverändert; unter `src/` seit
`d61453c` nichts geändert. **Amadeus ist nicht gefahren:** keine
Motorfreigabe, keine Mission, keine Drehung; im Stack lief keine
Motorsteuerung. Die Übergabe nannte zuerst versehentlich KI-F9; der Agent hat
nachgefragt und nichts gestartet, bis Christopher KI-F9N bestätigt hatte.
Der Bericht liegt nicht im Repository.

## Was lief

| Kennung | Ergebnis |
|---|---|
| T-1 Tests unter Humble | 409 bestanden, 0 fehlgeschlagen – trifft zu |
| U-1 Umgebungen | „Umgebungen passen.“ (beide Domäne 42, Cyclone) – trifft zu |
| S-1 Aufnahme neu | 30 von 30 Runden trotz SIGINT mitten im Lesen, 0 Traceback, jedes Mal `rc=0` – trifft zu |
| S-2 Aufnahme alt (`30e72a4`) | ebenfalls 30 von 30: Der Absturz aus 2w ließ sich im Stand nicht nachstellen |
| V-1 Ablaufhilfe im Stand | `BEREIT bilder_hz=2.0`, Aufnahme geschrieben, Kamera mit genau einem SIGINT beendet (eine PID in `signale.json`); im Stand keine Öffnung vermessen, daher „Keine Wahl der KI (rc=4)“, die KI wurde nicht gefragt; `antwort … nein` lehnte ab; „Alles beendet.“ – trifft zu |
| B-1 Belege | nicht prüfbar: Ohne Wahl lief `messen` nicht (eine Lücke des Auftrags, der mit einer Öffnung im Blick rechnete) |
| A-1, A-2 | Vermessung und Wahlen aller KI-F9-Runden festgehalten |
| O-1 bis O-6 | rechts neben der Labortür ein Stuhl, etwa 1,2 m vom Rahmen, höher als 75 cm; wo er in 2w2/2w3 stand: „weiß ich nicht mehr“; Fensterscheibe ab 90 cm, nichts davor; Not-Aus im Gehäuse; Nummern siehe unten; die Fragen von KI-F9 sind auf dem KI-Rechner nach `~/ki_erkundung_kif9_fragen` kopiert |

**G-1 trifft nicht zu**, allein wegen B-1.

Was die Nummern in KI-F9 wirklich waren (Christopher, O-5): Vorlauf Nr. 1
Tür; Lauf 1 Nr. 1 Tür, Nr. 2 schmales Wandregal direkt neben dem Fenster
(die KI: „offene Tür“, 85 %); 2w3 Nr. 1 Tür, Nr. 2 Wand neben einem Regal,
Nr. 3 Regal und Stuhl; dazu „Lauf2w2 Nr.2 Fenster, die Nummer ist doppelt
identisch“ (vermutlich ist Lauf 2 gemeint, dort lagen zwei Nummern
übereinander; nicht nachgefragt).

Außerdem: Beim Beenden des Stacks (nach Strg+C) endete
`cmd_vel_mission_gate` mit „process has died … exit code -11“. Das ist ein
Baustein der Hauptlinie, kein Werkzeug der KI-Linie.

## Was daraus folgt

Die Ursache von Lauf 2 ist mit Zahlen belegt: Die Nummer 1 am Fenster hatte
ihre Kanten in umgekehrter Reihenfolge (−166° → −180°). Ihr Winkelbereich
galt deshalb als 346° statt 14°, und sie verdrängte jede breitere Lücke im
ganzen Rundblick, auch die Labortür. Auswertung und Vorschlag: [STATUS.md](../../STATUS.md).
