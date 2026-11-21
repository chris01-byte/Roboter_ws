# Archiv: Auftrag KI-1 „Blickrunde aus eigener Kraft“ – ausgeführt am 21.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der letzten Fassung. Er ist
**nicht mehr aktuell**; der aktuelle Auftrag der KI-Linie steht in
`ki_erkundung/AUFTRAG.md`.

Ausgeführt wurde er auf dem Stand `a0ad82b` (Fassung des Auftrags aus
`a8aee99`), also **ohne** die zweite Anschlussstelle „Etappenfahrt“: Die hier
archivierte Fassung nennt schon die Zähler und Testzahlen des späteren Stands
(`2caae94`: 11 und 226); am Jetson galten und stimmten 8 und 206.

Jetson, 20:43 bis 21:30, mit Christopher, nur im Laborraum. Release
`ki1-20261121_2043`, Umgebungsdatei `~/roboter_worktrees/ki1.env`. **Zum
ersten Mal in dieser Linie hat sich Amadeus bewegt:** eine Drehung auf der
Stelle. Der Bericht selbst liegt nicht im Repository.

## Vorab festgelegte Kriterien und was gemessen wurde

| Kennung | Kriterium | Gemessen | Urteil |
|---|---|---|---|
| R1 Drehung | 350° bis 370° und „Nur Rundblick abgeschlossen“ | 363,2° gedreht; Meldung wie erwartet | trifft zu |
| R2 Kein Fahren | kein Nav2-Ziel; höchstens 10 cm neben dem Start | kein Nav2-Ziel; 0,008 m; an der Basis höchstens 0,000 m/s; Christopher: nicht gewandert | trifft zu |
| R3 Dauer | höchstens 150 s | 81,3 s (Simulation: 77 s) | trifft zu |
| R4 Blickrunde | mindestens 100 Paare; 350° bis 370° aus den Scans; acht Bilder je höchstens 12° neben dem Soll | 286 Paare (163 in der Drehung); 363,3°; acht Bilder, 0,0° bis 4,3° daneben | trifft zu |
| R5 Kamera neben dem Stack | Bilder mindestens 1,8 Hz, Scans mindestens 9 Hz, auch in der Drehung; keine Fehlerzeile | Stand 2,00 / 9,93 Hz; Drehung 2,00 Hz und mindestens 9,43 Hz; keine Fehlerzeile | trifft zu |
| R6 Antwort | gültig auf neun Bilder, höchstens 45 s | gültig, 4,87 s (davon 2,69 s Laden des Modells) | trifft zu |

## Die Blickrunde und die Antwort der KI

- **Vermessung** (nach der Drehung, über das Raster von der Antriebsmitte):
  zwei Öffnungen angeboten. Nr. 1 ist die Labortür, 0,73 m breit vermessen
  (wahr 0,85 m; im Stand vom selben Platz 0,77 m), 2,40 m entfernt. Nr. 2
  liegt hinter dem Roboter, 0,81 m breit, 0,77 m frei dahinter; laut
  Christopher ein Regal.
- **KI:** wählte Nr. 1 („tuer_offen“, Sicherheit 0,95) und ordnete Nr. 2 als
  „wand“ ein. Christopher: Nr. 1 ist die offene Tür, die Nummer steht mittig
  auf der Schwelle; einen Ausgang ohne Nummer gibt es nicht. Raumname der KI
  „Wohnzimmer“, tatsächlich Labor.
- **Christopher im Bild:** Er war auf einem Foto zu sehen, bekam aber keine
  Nummer in der Skizze.
- **Auswertung:** K0-1 richtig 1 von 1, K0-6 Ausgang angeboten 1 von 1; für
  ein Urteil zu wenige Runden.

## Rechenlast (Stack ohne Motorfreigabe und Kamera, im Stand)

Last 11,1 (eine Minute), 29 % Leerlauf, 3,1 GB Speicher verfügbar. Größte
Verbraucher: Erkunder 63 %, Fahrtor 58 %, LiDAR-Odometrie 37 %; die Kamera
11 %. Raten blieben im Soll, auch in der Drehung; keine „Transform data too
old“, keine „Odometrie kurzzeitig nicht frisch“.

## Was nicht lief oder abwich

- **Erster scharfer Start ohne Motorregler.** Die Regler antworteten nicht
  (Motoren waren gesperrt); die Vorprüfung fiel mit drei `FEHL` durch, es
  gab keine Mission, der Stack wurde beendet. Christopher: „sorry mein
  fehler motoren sind hetzt wieder frei“. Der Agent fragte die
  Startbedingung neu ab und startete ein zweites Mal scharf. Der Auftrag sah
  das nicht vor; der Agent hat es als Abweichung berichtet. Es blieb bei
  genau einem Missionsstart. **Der Fehler lag im Auftrag:** Er fragte vor
  dem scharfen Start nicht nach der Motorsperre und kannte diesen Fall
  nicht.
- **Im Stand lief die Prüfung trotz stummer Regler durch.** Der
  Encoder-Leser meldete „Encoder-Shadow dauerhaft gesperrt … No response“,
  das Prüfskript ohne `--aktiv` trotzdem „Encoder-Shadow sichtbar“. Für den
  Stand ist das unschädlich; als Auskunft über die Regler taugt die Zeile
  nicht.
- **Ein Muster im Auftrag traf nichts:** Der Status des Erkunders steht ohne
  Leerzeichen nach dem Doppelpunkt; der Agent las mit angepasstem Muster.
- Der Erkunder meldet nach dem Rundblick `partial`, der Missionsbaum
  `SUCCESS` (ein Auftrag ohne Flächenziel heißt im Erkunder so).
- Das Aufnahmewerkzeug schrieb seine Zwischenzeilen ohne Terminal erst am
  Ende; die Scanrate in der Drehung hat der Agent deshalb zusätzlich nur
  lesend mitgeschnitten.
- Christopher wurde zu den Fragen nach der Drehung erst nach dem Beenden des
  Stacks befragt; die Frage nach seinem Standort blieb ohne Angabe.
- Beim Beenden brauchten `ekf_node` und einmal `lifecycle_manager` ein
  SIGTERM.

## Was daraus folgte

- Der Schalter „nur Rundblick“ arbeitet am Roboter wie in der Simulation.
- Nachgebessert: Das Aufnahmewerkzeug schreibt zeilenweise; der nächste
  Auftrag fragt vor dem scharfen Start nach der Motorsperre, erlaubt bei
  stummen Reglern nach Christophers „frei“ genau einen neuen Start und
  enthält kein Suchmuster für den Status mehr.
- Nächster Auftrag: die ersten Etappen des Fahrteils (KI-F1).
