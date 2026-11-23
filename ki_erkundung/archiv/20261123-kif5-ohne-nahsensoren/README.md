# Archiv: Auftrag KI-F5 „Türdurchfahrt ohne Nahsensoren (Laborprobe)“ – ausgeführt am 23.11.2026, keine Fahrt

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`88efba4`). Er ist **nicht mehr aktuell**; der aktuelle
Auftrag der KI-Linie steht in `ki_erkundung/AUFTRAG.md`.

Jetson, 09:50 bis 10:18, mit Christopher. Der Bericht selbst liegt nicht im
Repository.

## Was lief

- **Build** des neuen Release `kif5-20261123_0950` mit dem Laborschalter:
  `rc=0`, 177 s, 14 Pakete; alle Prüfzeilen wie erwartet, alle Profile gleich
  dem Release `kif1`. Tests 350 und 264 bestanden.
- **Ohne Nahsensoren** im Stack ohne Motorfreigabe: kein Knoten
  `vl53_near_field`, Fahrtor `require_near_field` `False`, beide
  VL53-Quellen des Kollisionsmonitors `False`, Logzeile zweimal. Der
  Kollisionsmonitor dieser Version kennt das Abschalten einzelner Quellen.

## Was nicht lief

Fünf Messungen im Stand meldeten „Aufstellung passt nicht: steht 0.30 bis
0.33 m rechts neben der Türmitte: bitte etwa 31 cm nach links versetzen“,
Tür 7 bis 8° gedreht. In den ersten zwei lag zusätzlich etwas auf dem
Roboter im Blick des Lasers („Weg passt nicht“, 0,11 m frei);
Christopher: „sorry da lag was auf dem roboter“. Christopher nach der
ersten Messung: „doch der roboter steht direkt mittig vor der tür, warum hat
der externe ki rechner das nicht bestädigt“; nach der fünften: „ich mach
mich doch hier nicht zum clown, der roboter muss die tür finden, sich
selber ausrichten und hindurch fahren“, dann „schick mir den bericht“.
Keine Fahrt, kein scharfer Start.

## Ursache: das Werkzeug, nicht die Aufstellung

Christopher hatte recht, Amadeus stand mittig:

| | rechte Türkante | linke Türkante | Tiefenunterschied | Werkzeug |
|---|---|---|---|---|
| 22.11. (KI-F3b) | 1,868 / −0,346 m | 1,883 / +0,424 m | 1,5 cm | 0,07 m rechts, Tür 1° gedreht, „passt“ |
| 23.11. (KI-F5) | 1,802 / −0,318 m | 1,899 / +0,442 m | 9,7 cm | 0,30 m rechts, Tür 7° gedreht, „passt nicht“ |

Die linke Kante liegt an beiden Tagen auf 2 cm an derselben Stelle, also
stand Amadeus am selben Platz und gleich gedreht. Nur die rechte Kante lag
heute 7 cm näher: Der Laser traf dort etwas vor dem rechten Türrahmen (einen
Grad daneben sah er schon 2,47 m in den Flur, es war also schmal; was es
war, ist nicht festgestellt). Das Werkzeug nahm die Richtung der Tür aus
genau diesen zwei Punkten. 7 cm an einer Kante kippen die Türachse um 7°,
und auf 1,8 m Abstand werden daraus 30 cm „daneben“.

**Fehler der Planung:** (1) Eine Prüfung, nach der ein Mensch den Roboter
umstellen soll, stützte sich auf zwei einzelne Punkte. Für die Anfahrt
gab es schon die robuste Achse aus der Wand neben der Tür, für die
Aufstellung nicht. (2) Der Auftrag ließ bis zu acht Messungen mit
Umstellen von Hand zu. Er hätte nach einer unplausiblen Meldung (Mensch sagt
„mittig“, Werkzeug sagt „30 cm daneben“) nicht weiter umstellen lassen
dürfen. (3) Stufe 2, in der Amadeus sich selbst vor die Tür stellt, war an
Stufe 1 gebunden; genau sie hätte hier geholfen.

## Was daraus folgte

- Die Türachse kommt jetzt in allen Betrieben aus der geraden Wand neben
  der Tür (`tuerachse`); mit den Zahlen von heute meldet das Werkzeug
  „mittig“.
- Neuer Betrieb `--zur-tuer`: Amadeus entscheidet selbst, ob er gleich
  durchfährt oder sich zuerst vor die Tür stellt; niemand stellt ihn um.
- Folgeauftrag KI-F6.
