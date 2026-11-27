# Archiv: Auftrag KI-F9R „Nachrechnen nach der Reparatur des Sehens“ – ausgeführt am 27.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`9e2cb17`). Er ist **nicht mehr aktuell**.

Jetson, 18:01 bis 18:29, an 19 gespeicherten Blickrunden. **Kein Stack, kein
Sensor, kein Motor, kein Build**; unter `src/` seit `d61453c` nichts
geändert. Auf dem KI-Rechner lief der Lotse mit `qwen3.5:9b`. Neu angelegt
wurden nur die fünf `wahrheit.json` der KI-F9-Runden (Christophers Angaben,
Schritt 5). Der Bericht liegt nicht im Repository.

## Was lief

| Kennung | Ergebnis |
|---|---|
| T-1 Tests unter Humble | 433 bestanden – trifft zu |
| V-1 Tür in Lauf 2 | angeboten: Labortür 0,84 m bei +33,8° in 2,33 m („linie“) – trifft zu |
| V-2 Scheinlücke weg | Die Scheinlücke (0,82 m bei −173,7°) ist nicht mehr angeboten. Erwartet war außerdem eine Zeile mit `lot_verkehrt` an ihrer Stelle; die gibt es nicht, weil eine verworfene Lot-Schätzung keine eigene Zeile bekommt (siehe unten) – **trifft nicht zu** (in der Sache erfüllt, die Erwartung war falsch gefasst) |
| V-3 nichts verloren | in keiner der 19 Runden eine angebotene Öffnung verloren; in Lauf 2 kamen die Tür und eine 1,75-m-Lücke (Pflanze) dazu – trifft zu |
| K-1 KI in Lauf 2 | neue Fassung: Wahl Nr. 1, die Labortür; die alte Fassung wählte wie in KI-F9 die Lücke am Fenster (Nr. 2, „tuer_offen“) – trifft zu |
| K-2 keine falsche Wahl | in den KI-F9-Runden immer die Tür. Aber `labor_tuer_seite_nah` (Tür halb zu, Nr. 1 laut Christopher am 21.11. „Mauerwerk neben der Tür“): neu „tuer_offen“ und gewählt, alt „wand“ – **trifft nicht zu** |
| K-3 | K0-1 richtig: alt 13, neu 14 von 16 (81 % → 88 %) – Hinweis |
| K-4 nichts abgeschrieben | 17 Antworten, keine mit SATZ oder RAUM – trifft zu |
| K-5 | 0 von 17 verworfen; Median 1,8 s, längste 2,7 s – Hinweis |
| E-1 Torwächter | 88 Stackläufe seit 02.11.: `cmd_vel_mission_gate` 86-mal sauber beendet, einmal `exit code -11` (KI-F9N, 24.11.), einmal `-9` (15.11.) – gezählt |

**G-1 trifft nicht zu** (V-2 und K-2).

Christophers Angaben zu den KI-F9-Runden (neue Nummern): Nr. 1 ist in allen
fünf die offene Labortür; sonst Möbel (Stuhl, Hängeregal, Pflanze, Stuhl und
Hängeschrank) und in Lauf 2 Nr. 3 das Fenster mit Rollo. Kein Ausgang ohne
Nummer.

## Was daraus folgt

- **Lauf 2 ist behoben, an echten Daten.** Mit dem alten Stand wiederholte
  sich der Fehler aus KI-F9 genau (Wahl der Fensterlücke). Mit dem neuen
  Stand hat die Tür eine Nummer, und die KI wählt sie. Die zweite
  Fensterlücke bleibt angeboten; die KI nennt sie „wand“ und wählt sie nicht.
- **V-2 war falsch gefasst:** Eine Lot-Schätzung mit verkehrten Kanten wird
  verworfen, bevor eine Lücke entsteht. Ihr Vermerk `lot_verkehrt` steht
  dann an einer anderen Lücke derselben Kante, falls diese anders geschlossen
  wird, sonst nirgends. Deshalb tragen jetzt 13 Zeilen `lot_verkehrt`
  (meist statt `tuer_…`), auch angebotene Türen. Das Netz „über 180°“ hat an
  echten Daten nie gegriffen.
- **Eine neue Fehlwahl:** In `labor_tuer_seite_nah` hält die KI mit der
  neuen Frage die Nummer auf dem Mauerwerk neben einer halb geschlossenen
  Tür für eine offene Tür. In der zweiten Aufnahme dieser Ansicht
  (`labor_tuer_seite_nah_b`) gilt dieselbe Wahl nach
  Christophers Angaben vom 21.11. als richtig („Nr. 2 Tür, Nummer zu weit
  rechts“). Ein Fall von 16; Christophers Ja bleibt vor jeder Fahrt.
- **Torwächter:** Der Speicherzugriffsfehler beim Beenden kam in 88 Läufen
  einmal vor. Er ist kein Muster; der Baustein gehört zur Hauptlinie und
  wird von der KI-Linie nicht geändert.
- Kleinere Beobachtungen: In Lauf 2 nennt die KI die 1,75-m-Lücke an einer
  Pflanze „durchgang“ (nicht gewählt; zum Fahren wäre sie zu breit). In
  Lauf 1 sagt Christopher zu Nr. 2: „kommt zwei mal vor einmal ein Stuhl
  und einmal ein Hängeregal“ (sie steht in zwei Fotos, offen ist, ob an
  derselben Stelle).
