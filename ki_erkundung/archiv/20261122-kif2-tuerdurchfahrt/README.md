# Archiv: Auftrag KI-F2 „Türdurchfahrt“ – ausgeführt am 22.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`e0de4f0`). Er ist **nicht mehr aktuell**; der aktuelle
Auftrag der KI-Linie steht in `ki_erkundung/AUFTRAG.md`.

Jetson, 16:47 bis 17:23, mit Christopher. Kein Build (Release
`kif1-20261122_1515`); 233 Tests bestanden. Ohne Kamera, ohne KI. Der Bericht
selbst liegt nicht im Repository.

## Was geschah

- **Aufstellen und Messen** klappte beim ersten Mal: mittig vor der Tür
  0,77 m breit, 1,90 m entfernt, „Aufstellung passt“; Christopher bestätigte
  die Labortür. Amadeus stand 0,18 m rechts der Türmitte.
- **Die Fahrt:** Ausrichten um 9,4° nach links (Restfehler 0,8°), dann die
  erste Etappe. Nach 0,345 m hielt der Erkunder an: „Nahbereich vor dem
  Roboter nicht frei (blocked, 0.25 m vor der Vorderkante)“. Nichts berührt,
  kein Eingriff, kein Nav2-Ziel. Der Kollisionsmonitor hatte 5 s nach
  Etappenbeginn auf 30 % gebremst.
- **Christopher:** „Soweit ich es gesehen habe hat der Kollisionssensor
  ausgelöst. Der Roboter ist nur gerade aus gefahren und wäre gegen das
  Türblatt gefahren. Der Roboter hat sich überhaupt nicht der Tür
  ausgerichtet und nachkorrigiert!“ Das Türblatt geht in den Laborraum auf,
  steht „85 grad zur türöffnung“ und ist von Amadeus aus links.

| Kennung | Kriterium | Gemessen | Urteil |
|---|---|---|---|
| T-1 Vermessung | 0,65 bis 0,95 m, „Aufstellung passt“ | 0,77 m, passt | trifft zu |
| T-2 Abschluss | „Etappenfahrt abgeschlossen …“ | „angehalten, Nahbereich … nicht frei“ nach 0,35 m | trifft nicht zu |
| T-3 Ausrichten | höchstens drei Durchgänge, Restfehler höchstens 3,5° | Punkt 1: ein Durchgang, 0,8° | trifft zu (Punkt 2 nicht erreicht) |
| T-4 Durch die Tür | ganz im Flur | nein | trifft nicht zu |
| T-5 Abstand | Handbreit an Pfosten und Blatt | nicht bis an die Tür gekommen | ohne Urteil |
| T-6 Kette | je 0 | je 0 | trifft zu |

## Ursache: der geplante Weg, nicht der Halt

Der Auftrag ließ Amadeus nicht auf die Tür zu fahren, sondern zuerst schräg
zu einem Punkt auf der Türachse, 1,1 m vor der Tür, und sich erst dort zur
Tür drehen. Weil er 0,18 m rechts der Türmitte stand, ging diese Strecke
nach links, zur Seite des Türblatts.

Nachgerechnet aus den Maßen des Berichts (Türkanten bei −10,0°/1,90 m und
+12,7°/1,97 m, Blatt 0,85 m lang, 85° zur Türöffnung):

- Die gefahrene Linie führt 0,245 m an der Spitze des Türblatts vorbei. Das
  Gehäuse ist 0,23 m halb breit, der Streifen des Nahbereichs-Halts 0,255 m.
- Am Wendepunkt hätte die vordere linke Ecke 1,6 cm vor der Blattspitze
  gestanden.
- Auf der geraden Linie vom Standplatz durch die Türmitte bleiben 0,386 m.

Der Halt war also richtig. Offen bleibt eine Abweichung: Nach dieser
Rechnung lag die Blattspitze beim Halt 0,78 m voraus; gemeldet wurde ein
Hindernis 0,58 m voraus. Blattlänge, Winkel und die Darstellung des Blatts
in der Karte sind nicht gemessen.

**Simulation dazu:** Mit einem 85° offenen, 0,9 m langen Blatt und derselben
Aufstellung kam der alte Plan durch, aber die gepolsterte Kontur näherte
sich der Blattspitze am Wendepunkt auf 4,7 cm. Der Halt selbst wurde nicht
nachgestellt (in der Simulation lag die Spitze 5 cm weiter von der Linie).

**Fehler der Planung:** (1) Der Weg wurde nicht gegen das geprüft, was der
Laser sieht; er wurde nur aus zwei Türkanten gerechnet. (2) Die Annahme
„Blatt im rechten Winkel, 0,40 m neben der Achse“ war ungeprüft; ein Blatt
bei 85° lehnt 7 cm herein. (3) Ein Umweg über die Türachse ist unnötig, wenn
der Roboter fast mittig steht, und für den Menschen daneben nicht zu
verstehen.

## Messung aus der schrägen Lage (A2)

Erwartet war eine 1,15 bis 1,35 m breite Öffnung wie am Vormittag. Gemessen
wurde eine 0,75 m breite Öffnung bei −2,0° und 2,58 m: Amadeus stand nicht
so wie am Vormittag (damals −31,9° und 1,59 m). Die Vermutung „Lücke
zwischen Blattspitze und Pfosten“ ist damit **weder bestätigt noch
widerlegt**. Belegt ist nur: Das Blatt geht in den Laborraum auf.

## Was daraus folgte

- Das Werkzeug legt die Fahrpunkte jetzt auf die **gerade Linie vom
  Standplatz durch die Türmitte** und prüft vor dem Senden am Laserbild,
  dass links und rechts der Linie 0,30 m frei sind; sonst sendet es nicht
  und sagt, wohin zu versetzen ist.
- Es zeigt vor dem Senden und nach einem Halt, was in der Kostenkarte vor
  dem Roboter belegt ist (dieselbe Karte, an der der Erkunder anhält).
- Folgeauftrag KI-F3.
