# Archiv: Auftrag KI-F3 „durch die Tür: erst von vorn, dann vom Platz im Raum“ – zwei Anläufe am 22.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung des zweiten
Anlaufs KI-F3b (`9ba30f1`). Er ist **nicht mehr aktuell**; der aktuelle
Auftrag der KI-Linie steht in `ki_erkundung/AUFTRAG.md`.

Jetson, mit Christopher, nur Stufe 1 (von vorn durch die Tür). Stufe 2 (vom
Platz im Raum) lief in keinem Anlauf, weil Stufe 1 nicht bestanden war.
Kein Build (Release `kif1-20261122_1515`). Ohne Kamera, ohne KI. Die
Berichte liegen nicht im Repository.

## Erster Anlauf KI-F3 (22:03 bis 22:12, Stand `6f7d496`)

- Aufstellen und Messen passten beim ersten Mal: Tür 0,77 m, 1,87 m
  entfernt, Amadeus 0,07 m rechts der Türmitte; neben der Fahrlinie links
  0,38 m und rechts 0,39 m frei.
- Im scharfen Stack hatte sich der Radsensor beim Hochfahren gesperrt
  (Encoder-Zeitwache `fault_latched`, `encoder_timing_continuity_unproven`).
  Die Vorprüfung fiel durch, keine Mission, keine Bewegung. Für diesen
  bekannten Fall kannte der Auftrag keinen Weg; nachgetragen als Ausnahme
  „Radsensor beim Start gesperrt“.

## Zweiter Anlauf KI-F3b (22:25 bis 22:37, Stand `9ba30f1`)

256 Tests bestanden. Messung wie im ersten Anlauf, beim ersten Mal passend;
Christopher bestätigte die Labortür. Die Vorprüfung im scharfen Stack bestand
beim ersten Mal (Radsensor nicht gesperrt, die neue Ausnahme kam nicht zum
Tragen).

**Die Fahrt:** drei Etappen geradeaus (LiDAR 0,350 m, 0,280 m, 0,400 m;
seitlich höchstens 5 mm, Richtung höchstens 0,3° daneben); nachgestellt
werden musste nichts. Zu Beginn der vierten Etappe hielt der Erkunder an,
nach 7 mm Radweg: „Nahbereich vor dem Roboter nicht frei (blocked, 0.25 m
vor der Vorderkante)“. Gefahren 1,03 m von 2,32 m, höchstens 0,050 m/s.
Der Kollisionsmonitor bremste zweimal kurz auf 30 %.

Das Werkzeug nach dem Halt: „im Fahrstreifen 0.25 m vor der Vorderkante,
0.09 m links der Mitte – so nah hält der Erkunder an“; daneben links und
rechts belegt ab der Vorderkante, 0,44 und 0,45 m neben der Mitte.

**Christopher:** „nein er hat vor der tür gestoppt“; Platz an Pfosten und
Türblatt „grob ca. 150mm“; nichts berührt, kein Eingriff; „keine
nachstellung beobachtet“.

| Kennung | Kriterium | Gemessen | Urteil |
|---|---|---|---|
| T-1 Vermessung | türbreit, „Aufstellung passt“, „Weg passt“ | 0,77 m; beides; frei 0,38 / 0,39 m | trifft zu |
| T-2 Abschluss | „Etappenfahrt abgeschlossen …“ | angehalten nach 1,03 m | trifft nicht zu |
| T-3 Ausrichten | höchstens drei Durchgänge, Rest höchstens 3,5° | nicht nötig (0 Grad) | trifft zu |
| T-4 Durch die Tür | ganz im Flur | „nein er hat vor der tür gestoppt“ | trifft nicht zu |
| T-5 Abstand | Handbreit an Pfosten und Blatt | nicht durch die Tür gefahren | ohne Urteil |
| T-6 Kette | je 0 | je 0 | trifft zu |

## Was die Stelle war – nachgerechnet

- Beim Halt stand die Antriebsmitte 0,84 m vor der Türlinie. Die belegte
  Zelle lag 0,58 m voraus: **0,26 m vor der Türlinie, etwa 6 cm links der
  Türmitte**, also mitten im Durchgang. Das Türblatt ist es nicht; das
  steht in der Kostenkarte 0,37 bis 0,44 m links der Mitte und lag neben
  dem Fahrstreifen.
- Belegte Zellen schreiben in diese Kostenkarte nur zwei Quellen: die Karte
  des SLAM (aus dem Laser in 0,75 m Höhe) und die beiden Nahsensoren (VL53).
  Der Laser sah die Fahrlinie vor der Fahrt frei. Die Nahsensoren sehen
  erst ab etwa 8 cm über dem Boden, aus 0,28 m Abstand erst ab 17 cm. Also
  bleibt: etwas mindestens 8 cm Hohes am Boden, eine Fehlmessung der
  Nahsensoren oder ein Eintrag in der Karte des SLAM. Eine Schwelle scheidet
  aus (die Tür hat keine; so tief sehen die Nahsensoren nicht).
- Markierungen der Nahsensoren, die näher als 0,45 m am Sensor liegen,
  werden nie wieder geräumt (gewollt, damit niedrige Dinge in der Karte
  bleiben, wenn der Sensor sie aus der Nähe nicht mehr sieht). Eine einzelne
  Fehlmessung bliebe so liegen.
- **Fehler im Werkzeug:** Seine Zeile zur Kostenkarte vor dem Senden reichte
  nur 1,5 m voraus; die Stelle lag 1,61 m voraus. Ob sie schon vor der Fahrt
  da war, ist deshalb unbekannt. Und es konnte nicht sagen, welche Quelle
  die Stelle meldet.
- Warum nichts nachgestellt wurde: Amadeus lag nach jeder Etappe höchstens
  5 mm und 0,3° neben der Linie. Das passt zu Christophers Beobachtung.

**Simulation dazu:** dieselbe Aufstellung und ein 20 cm hoher Gegenstand
0,26 m vor der Türlinie, 6 cm links. Halt nach 0,96 m, Stelle 0,25 m vor der
Vorderkante, 0,12 m links; das nachgebesserte Werkzeug meldet „Karte (SLAM)
frei; Nahsensor links 12 Punkt(e), 16 bis 20 cm über dem Boden; Nahsensor
rechts 6 Punkt(e), 13 bis 18 cm“. Das Muster gleicht dem am Roboter; ob dort
wirklich etwas stand, beweist es nicht. Eine Fehlmessung sähe gleich aus.

## Was daraus folgte

- Das Werkzeug prüft die Kostenkarte vor dem Senden auf dem **ganzen Weg**
  so, wie der Nahbereichs-Halt sie liest, und sendet nicht, wenn sie belegt
  ist („Kostenkarte passt.“ wird nötig). Für eine belegte Stelle nennt es
  die Quelle: Karte des SLAM, Nahsensor links oder rechts mit Höhe über dem
  Boden, Laser; dazu, was die Nahsensoren gerade im Fahrstreifen sehen.
- Folgeauftrag KI-F4: zuerst an der Haltestelle im Stand messen und
  Christopher fragen, dann die Fahrt mit dieser Auskunft.
