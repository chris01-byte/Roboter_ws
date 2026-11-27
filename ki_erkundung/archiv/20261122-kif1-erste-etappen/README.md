# Archiv: Auftrag KI-F1 „Erste Etappen“ – ausgeführt am 22.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`baa16b7`). Er ist **nicht mehr aktuell**; der aktuelle
Auftrag der KI-Linie steht in `ki_erkundung/AUFTRAG.md`.

Jetson, 15:15 bis 16:15, mit Christopher. Release `kif1-20261122_1515`,
Umgebungsdatei `~/roboter_worktrees/kif1.env`; 345 und 228 Tests bestanden.
Ohne Kamera, ohne KI. **Zum ersten Mal in dieser Linie ist Amadeus
gefahren:** eine gerade Etappe von 0,5 m. Die Türdurchfahrt wurde nicht
gefahren. Der Bericht selbst liegt nicht im Repository.

## Stufe 1 – eine gerade Etappe von 0,5 m: alle Kriterien erfüllt

| Kennung | Kriterium | Gemessen | Urteil |
|---|---|---|---|
| F1-1 Abschluss | „Etappenfahrt abgeschlossen: 1 Etappe(n) …; Quelle test; kein Nav2-Ziel“ | so gemeldet | trifft zu |
| F1-2 Weg | Laser 0,49 bis 0,55 m; Maßband 0,45 bis 0,60 m | 0,505 m; „ca. 550mm“ | trifft zu |
| F1-3 Spur | seitlich höchstens 0,03 m, Winkel höchstens 3° | 0,000 m; 0,0° | trifft zu |
| F1-4 Dauer | höchstens 30 s | 12,8 s (Simulation 11,5 s) | trifft zu |
| F1-5 Kette | kein Nav2-Ziel, nichts verworfen, Odometrie frisch | je 0 | trifft zu |
| F1-6 Mensch | gerade, selbst angehalten, nichts berührt | „ja“, „nein“, „die fahrt war super“ | trifft zu |

An der Basis höchstens 0,050 m/s; Radweg laut Encoder 0,524 m bei 0,505 m
laut Laser. Der Kollisionsmonitor hat nicht gebremst. Die Simulation hatte
für dieselbe Etappe 0,505 m und 0,52 m Fahrweg vorhergesagt.

## Stufe 2 – durch die Labortür: nicht gefahren

Vor dem Missionsstart vermaß das Werkzeug genau eine Öffnung: **1,25 m
breit**, 32° rechts, 1,59 m entfernt, „sprung“. Christopher bestätigte, dass
dort die Labortür liegt (wahre Breite 0,85 m). Das Kriterium F2-1 verlangte
0,70 bis 0,90 m; der Agent sandte deshalb keine Mission und beendete den
Stack. Schon im Stand hatte dieselbe Messung von einem anderen Platz 1,23 m
ergeben.

**Die Sperre war richtig, die Ursache liegt im Auftrag und im Stand:**

- Der Fehler war bekannt (KI-0R: Tür von der Seite 1,30 m, Ursache offen)
  und nicht behoben; der Auftrag schickte den Roboter trotzdem vor die Tür.
- Die Aufstellanweisung „Blick ungefähr zur Tür“ war zu ungenau. Amadeus
  stand so, dass die Tür 32° seitlich lag.
- Der Auftrag kannte bei falscher Breite nur „keine Mission, Ende“. Messen
  bewegt nichts; Neuaufstellen und erneut Messen wäre gefahrlos gewesen.
- Die Messung im Stand (1,23 m) hat der Auftrag nicht als Warnung genutzt.

**Vermutung zur Ursache, nicht belegt:** Das Türblatt steht in den Raum
hinein offen. Von der Seite des Blatts aus sieht der Laser nicht die Tür,
sondern die Lücke zwischen der Spitze des Blatts und dem gegenüberliegenden
Pfosten: bei einem 0,85 m breiten Blatt im rechten Winkel 1,20 m, etwas
weiter offen 1,25 bis 1,30 m. Eine Nachstellung in der Simulation zeigt
genau diese Lücke (1,20 m, „sprung“, eine Kante bei 1,18 m, die andere bei
2,29 m). Am 21.11. galt dieselbe Vermutung als widerlegt; widerlegt war
aber nur, dass die dafür gebaute Regel an der echten Tür greift. Der
Folgeauftrag misst es nach.

## Was sonst abwich

- Auf „Welche Nummer ist die Labortür?“ antwortete Christopher „ich sehe
  kein bild“. Die Frage war ohne Blatt nicht zu beantworten; der Agent
  fragte mit Richtung und Entfernung nach (eine Frage mehr als im Auftrag).
- Der Erkunder meldet nach der gelungenen Etappe `partial` (wie in KI-1).

## Was daraus folgte

- Die gerade Etappe arbeitet am Roboter wie in der Simulation und wie am
  11.09.2026.
- Das Werkzeug prüft jetzt selbst: Eine Öffnung gilt nur zwischen 0,65 und
  0,95 m als Tür; es bewertet die Aufstellung (Abstand, Versatz neben der
  Türmitte, Blickwinkel) und sagt, was zu ändern ist. Der Vorpunkt liegt
  1,1 m vor der Tür, damit Amadeus sich nicht neben einem offenen Türblatt
  ausrichtet.
- Folgeauftrag KI-F2: im Stand so lange neu aufstellen und messen, bis es
  passt; dann die Türdurchfahrt.
