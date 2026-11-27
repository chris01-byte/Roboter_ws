# Archiv: Auftrag KI-F7 „noch einmal selbst ausrichten und durch die Tür“ – ausgeführt am 23.11.2026: erste Türdurchfahrt der KI-Linie

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`4ec1bcf`). Er ist **nicht mehr aktuell**.

Jetson, 12:58 bis 14:54, mit Christopher. Neuer Release
`kif7-20261123_1258` (Build 177 s, 14 Pakete; nur `explore_node.py`
gegenüber `kif5-20261123_0950` geändert, wie erwartet), Tests 356 und 268
bestanden. Jeder Start mit `stage_drive_only:=true nahsensoren:=false`. Ohne
Kamera, ohne KI. Der Bericht liegt nicht im Repository.

## Ergebnis: Durchgang 2 – selbst vor die Tür, ausgerichtet, hindurch

- Aufstellung von Christopher, einmal umgestellt (erste Messung: „keine
  Fahrt“, zum Drehen 0,39 m frei, nötig 0,45 m). Danach Labortür 0,75 m,
  3,28 m, +9°; Amadeus 3,21 m vor der Türlinie, 0,65 m rechts; Entscheidung
  „Anfahrt“.
- **Anfahrt:** 27,6° gedreht (Rest −0,1°), drei Etappen, 36,8° gedreht
  (Rest −1,0°), eine Etappe; 1,65 m; seitlich höchstens 5 mm, Winkel
  höchstens 0,5° daneben. Danach ohne Anfassen „0.03 m rechts, Tür 6° –
  Aufstellung passt“, „Weg passt“ (links und rechts je 0,39 m), „Kostenkarte
  passt“. Die Türachse kam dabei nur aus den zwei Kanten (neben der Tür
  keine gerade Wand gesehen).
- **Durchfahrt:** 7,8° gedreht (Rest −0,7°), fünf Etappen, 1,90 m,
  „Durchfahrt abgeschlossen.“ Kein Nav2-Ziel, höchstens 0,050 m/s und
  0,080 rad/s, alle Zähler der Kette 0.
- Christopher: steht ganz im Flur „ja“, Platz an Pfosten und Blatt „genug“,
  berührt oder eingegriffen „nein“, „ja alles geklappt“. Danach: „Jedoch
  waren die seitlichen Abstandsgrenzen zu hoch, die können deutlich herunter
  genommen werden.“
- Alle Kriterien N-1, T-1, A-1, T-2 bis T-6 treffen zu; H-1 nicht anwendbar
  (kein Halt).

## Durchgang 1 – keine Durchfahrt

- Erster scharfer Start: Radsensor beim Hochfahren gesperrt
  (`encoder_timing_continuity_unproven`, Last 8,1); Ausnahme, ein Neustart,
  danach frei. Zweites Mal in dieser Linie (KI-F3).
- Erste Anfahrt nach dem Ausrichten angehalten: „Streifen vor dem Roboter
  nicht frei (corridor_blocked, nächstes Hindernis 0.13 m)“; es lag etwas
  auf dem Roboter (Christopher). Auf seine Anordnung neu gemessen und neu
  angefahren: Anfahrt gelungen (1,85 m).
- Durchfahrt nicht gesendet: „links neben der Fahrlinie sind nur 0.24 m
  frei, nötig 0.30 m“; Christopher: „die tür war nicht ganz offen“. Bei
  0,24 m hätte zwischen Gehäuse (halbe Breite 0,23 m) und Türblatt 1 cm
  gelegen; die Prüfung hielt hier zu Recht.
- Beide Wiederholungen auf ausdrückliche Anordnung des Projektinhabers
  (Abweichung vom Auftrag, der jede Fahrt einmal vorsah).
