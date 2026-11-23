# Archiv: Auftrag KI-F6 „Amadeus richtet sich selbst aus und fährt durch die Tür“ – ausgeführt am 23.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`8717fd9`). Er ist **nicht mehr aktuell**; der aktuelle
Auftrag der KI-Linie steht in `ki_erkundung/AUFTRAG.md`.

Jetson, 11:07 bis 11:21, mit Christopher. Kein Build (Release
`kif5-20261123_0950`), jeder Start mit `stage_drive_only:=true
nahsensoren:=false`. Ohne Kamera, ohne KI. Der Bericht liegt nicht im
Repository.

## Was lief

- Stand `8717fd9`, `zeilen=0`, 268 Tests bestanden; beide Stacks ohne
  Nahsensoren wie verlangt (kein VL53-Knoten, Fahrtor und Kollisionsmonitor
  `False`).
- **Eine Messung, kein Umstellen.** Amadeus stand 2,33 m vor der Türlinie,
  1,01 m rechts der Türmitte. Das Werkzeug fand die Labortür (0,88 m breit,
  2,54 m, 18° links; Türachse aus der Wand, 19 Laserpunkte über 1,25 m) und
  entschied „Anfahrt“. Christopher bestätigte die Tür.
- **Die Anfahrt gelang** (erste Mission): 69,8° gedreht (Rest −0,4°), drei
  Etappen 0,36/0,32/0,26 m, 82,2° gedreht (Rest +0,7°), eine Etappe 0,48 m;
  seitlich höchstens 5 mm, Winkel höchstens 0,3° daneben; „Anfahrt
  abgeschlossen.“ Danach, ohne dass jemand Amadeus anfasste: „0.06 m rechts
  neben der Türmitte, Tür 8° links – Aufstellung passt“, Türachse aus der
  Wand (68 Punkte über 1,33 m), „Weg passt“ (links und rechts je 0,38 m
  frei), „Kostenkarte passt“. Christopher: „ja er hat die Tür gefunden ist
  zu ihr gefahren und hat sich ausgerichtet“.
- Zweite Mission, Durchfahrt: 10,4° gedreht (Rest −0,4°), Etappe 1 mit
  0,365 m bestanden.

## Was nicht lief

In Etappe 2 (nach 0,305 m) meldete der Erkunder „Encoder-Odometrie
kurzzeitig nicht frisch; LiDAR-Tueretappe bleibt null.“ und beendete die
Etappe mit `odom_stale`. Die Schlussmeldung scheiterte dann mit
„Logger severity cannot be changed between calls.“ (Mission `FAILURE`).
Gefahren 0,67 m von 2,38 m, nichts berührt, kein Eingriff, keine Bremsung
des Kollisionsmonitors. Nicht wiederholt. Christopher: „Warum ist er jetzt
im letzten Schritt nicht hindurch gefahren“.

## Ursache: zwei Programmfehler im Erkunder, nicht die Räder

1. **Lesereihenfolge.** Die gerade Laser-Etappe (`_drive_forward_lidar`)
   las erst die Uhr, dann den Odometriewert. Der Odometrie-Rückruf läuft in
   einem anderen Faden; kommt er dazwischen, ist der Wert jünger als die
   gelesene Uhrzeit, sein „Alter“ negativ, und die Prüfung wertet das als
   Zeitfehler: sofort `expired`, Etappe `odom_stale`. Für das Drehen
   (`_rotate_in_place`) war genau das seit dem 29.09.2026 behoben (`f746b1c`,
   damals nach einem realen Abbruch des Rundblicks), für die gerade Etappe
   nicht.
   Indizien, dass es so war: Zwischen der Warnung und dem Ende der Etappe
   lagen 1,27 s, die Frist für echte Odometrieausfälle beträgt 5 s; danach
   bestätigte dieselbe Odometrie innerhalb dieser Zeit den Stillstand (sonst
   hätte die Etappe `stop_unconfirmed` gemeldet); das Fahrtor meldete keinen
   Odometrieausfall. Ein ungültiger (nicht endlicher) Odometriewert hätte
   dasselbe Bild ergeben; dafür gibt es keinen Hinweis, aufgezeichnet ist er
   nicht. Der innere Alterswert wurde nicht protokolliert; die Zuordnung ist
   deshalb sehr wahrscheinlich, nicht bewiesen.
2. **Schlussmeldung.** `ende()` rief für Erfolg und Fehler dieselbe
   Programmstelle mit verschiedener Stufe auf (`info`, dann `error`). rclpy
   merkt sich je Aufrufstelle die Stufe und wirft beim Wechsel. Das trat nur
   auf, weil im selben Stacklauf erst ein Auftrag gelang (Anfahrt) und dann
   einer scheiterte; in allen Simulationen gelangen beide.

## Was daraus folgte

- Korrektur nur für die Etappenfahrt (`snapshot_before_clock=True`, Vorgabe
  aus): erst Odometrie und Scan lesen, dann die Uhr. Fristen und die Sperre
  echter Zeitfehler unverändert. Die Schlussmeldung in zwei getrennten
  Aufrufen.
- Sechs neue Tests; sie stellen beide Fehler am alten Stand nach
  (`odom_stale` bei einem Rückruf zwischen Uhr und Lesen; ValueError beim
  zweiten Auftrag) und bestehen am neuen.
- Folgeauftrag KI-F7 mit neuem Build; sonst wie KI-F6.
- Für die geparkte Hauptlinie festgehalten: `_drive_forward_localized` und
  `_drive_forward_supervised` lesen ebenfalls erst die Uhr; sie fährt die
  Etappenfahrt nicht und bleiben unverändert.
