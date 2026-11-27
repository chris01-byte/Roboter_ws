# Archiv: Auftrag KI-F8 „dreimal selbst durch die Tür, in einem Ablauf“ – ausgeführt am 23.11.2026: drei von drei

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`d61453c`; die spätere Ergänzung um die Seite des
Türblatts in `f70151d` war beim Lauf nicht dabei). Er ist **nicht mehr
aktuell**.

Jetson, mit Christopher, **zweiter vollständiger Durchgang** auf seine
Anweisung („einmal komplett neu“), 21:38 bis 22:24. Der erste Durchgang
(Release `kif8-20261123_2053`) blieb unvollständig; sein Bericht liegt nur
auf dem Jetson. Darin stand Amadeus einmal auf der Seite, zu der das
Türblatt aufgeht, und der Laser sah die Öffnung nicht richtig (Anlass für
`f70151d`). Die Berichte liegen nicht im Repository.

## Was lief (zweiter Durchgang)

- Release `kif8-20261123_2138`, Build 170 s, alle Prüfzeilen wie erwartet
  (nur `explore_node.py` und `stage_drive.py` anders als `kif7`), Tests 370
  und 271. Ein erster Testaufruf lief ohne frisches `source` und endete mit
  `ModuleNotFoundError`; mit `source` wie im Auftrag bestanden.
- **Eine Frage vorab (F0), „ja“.** Vorlauf ohne Motorfreigabe wie erwartet.
- Kein Radsensor gesperrt, keine Motorregler-Ausnahme, keine Wiederholung.

| Lauf | Aufstellung (erste Messung) | Ablauf | Ergebnis |
|---|---|---|---|
| 1 | 2,29 m vor der Türlinie, 0,05 m rechts | Durchfahrt direkt, 7 Etappen, 2,48 m | „Durchfahrt abgeschlossen.“; Christopher: „alles erfolgreich, bereit für lauf 2“ |
| 2 | 2,31 m vor der Türlinie, 0,80 m rechts | Anfahrt 1,23 m (78,5° und 87,4° gedreht), neu gemessen, wiedergefunden, 0,05 m rechts, Durchfahrt; zusammen 8 Etappen, 3,21 m | „Durchfahrt abgeschlossen.“; „ja alles erfolgreich, bereit für den letzten probelauf.“ |
| 3 | 3,36 m vor der Türlinie, 0,77 m rechts | Anfahrt 1,81 m, neu gemessen, wiedergefunden, Durchfahrt; zusammen 10 Etappen, 3,73 m | „Durchfahrt abgeschlossen.“; „erfolgreich“ |

Je Lauf ein Missionsstart und ein Aufruf des Werkzeugs, kein Nav2-Ziel,
höchstens 0,050 m/s und 0,080 rad/s, Rest nach dem Ausrichten höchstens
1,0°, seitlich höchstens 5 mm, alle Zähler der Kette 0. Neben der Fahrlinie
je 0,38 bis 0,39 m frei (nötig 0,26 m).

**G-1: drei von drei Läufen erfüllen alle Kriterien.** Vermerk: In Lauf 1
nahm die Messung im Stand (Schritt 3) die Türachse nur aus den Kanten, die
Messung im Ablauf aus der Wand; beide entschieden „Durchfahrt“.

## Was daraus folgt

- Anfahrt und Durchfahrt in einem Ablauf tragen am Roboter. Nächster
  Schritt der Linie: Die KI wählt die Tür (Konzept KI-2/KI-3), zuerst mit
  Einspruchsmöglichkeit von Christopher.
- Beobachtet: Die Etappen eines Auftrags zählen über alle Fahrziele einer
  Mission (Lauf 3: 10). Der Erkunder begrenzt sie je Mission auf 16; für
  Aufträge mit mehr Zielen gehört die Grenze je Fahrziel.
