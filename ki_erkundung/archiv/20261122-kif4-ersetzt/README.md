# Archiv: Auftrag KI-F4 „was hält vor der Tür? Erst messen, dann fahren“ – bis Teil M3 ausgeführt, dann ersetzt

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung vom 22.11.2026
(nachts, `9934e6f`). Er ist **nicht mehr aktuell**.

**Richtigstellung (23.11.2026):** Hier stand zuerst, KI-F4 sei „nicht
übergeben und nicht ausgeführt“. Das war falsch. Laut Bericht zu KI-F5 hat
der Projektinhaber KI-F4 am 22.11.2026 übergeben; der Jetson-Agent hat ihn
von 23:25 bis 23:36 bis Teil M3 ausgeführt (Release `kif1-20261122_1515`,
ein Stackstart ohne Motorfreigabe, keine Fahrt, Prüfdateien unter
`pruefung/kif4/`). Danach kam KI-F5.

Er sollte zuerst im Stand an der Stelle messen, an der Amadeus in KI-F3b vor
der Tür angehalten hatte, und feststellen, welcher Sensor die belegte
Stelle meldete; danach die Durchfahrt wie in KI-F3b.

## Was gemessen wurde (Teil M, mit Nahsensoren)

- **M1, Christophers Antworten:** auf „Lag oder stand bei der letzten Fahrt
  in der Tür oder bis etwa einen halben Meter davor etwas auf dem Boden …?“
  – „ja“; auf „Womit und an welcher Stelle ist die Tür gesichert?“ – „die
  Tür ist in der Wand eingemauert“.
- **M3, an der Haltestelle** (Amadeus 0,77 m vor der Türlinie, mittig):
  „Kostenkarte passt nicht“; Herkunft der Stelle 38 cm vor dem Gehäuse,
  8 cm links der Mitte: „Karte (SLAM) frei; Nahsensor links sieht dort
  nichts; Nahsensor rechts 28 Punkt(e), 10 bis 52 cm über dem Boden; Laser
  sieht dort nichts“.
- **M4** blieb unbeantwortet: „Der Nahsensor sieht etwa 38 cm vor dem
  Gehäuse und 8 cm links der Mitte etwas in 10 bis 52 cm Höhe. Liegt oder
  steht dort etwas, und was?“

**Einordnung:** Nach Christophers „ja“ lag bei KI-F3b etwas vor der Tür,
und an der Haltestelle sah der rechte Nahsensor dort etwas zwischen 10 und
52 cm Höhe, das der Laser in 75 cm Höhe nicht sah. Das spricht dafür, dass
der Nahbereichs-Halt in KI-F3b **richtig** angehalten hat. Was es war, ist
nicht festgestellt.

## Warum ersetzt

Am 22.11.2026 (nachts) entschied der Projektinhaber: „Die
Nahbereichssensoren machen gerade Probleme. Deswegen schreibe jetzt einen
Testlauf, wo diese komplett deaktiviert werden. Wir wollen jetzt einmal das
Konzept überprüfen, ohne die Nahbereichssensoren zu nutzen.“ Daraus wurde
KI-F5.
