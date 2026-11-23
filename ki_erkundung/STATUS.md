# KI-Erkundung – aktueller Status

**Stand 23.11.2026 (nachts): Die KI wählt die Tür – gebaut, in der
Simulation erprobt, Auftrag KI-F9 erteilt.** Entscheidung des
Projektinhabers nach KI-F8 („Ja“): Die KI wählt nach dem Rundblick die Tür;
zuerst sieht Christopher ihre Wahl und sagt vor der Fahrt ja oder nein. Die
Wahl geht über eine Wahl-Datei mit dem Ort der Öffnung in der Karte an das
Werkzeug (`ki_tuer_waehlen.py`, `fahrziel_senden.py --wahl`, `--ende`).
In der Simulation lief die ganze Kette: Rundblick, Aufnahme mit Lage in der
Karte, gespielte KI wählt, Neumessung findet die gewählte Tür wieder,
Anfahrt und Durchfahrt in einer Mission (unten). Dabei gefunden und
behoben: Die Aufnahme schrieb unter der neueren ROS-Fassung nach `kill
-INT` keine Runde. **Als Nächstes:** Auftrag KI-F9
([AUFTRAG.md](AUFTRAG.md)), wartet auf die Übergabe.

**Davor, 23.11.2026 (nach KI-F8): Drei von drei Läufen sind in einem Ablauf
durch die Labortür gefahren.** Von drei Plätzen: einmal gleich hindurch,
zweimal erst selbst vor die Tür (1,23 und 1,81 m), neu gemessen und
hindurch; je eine Mission und ein Aufruf des Werkzeugs, eine Frage vorab,
kein Nav2-Ziel, nichts berührt. Christopher: „erfolgreich“. Seit `f70151d`
findet das Werkzeug die Tür auch von der Seite des Türblatts (nur in der
Simulation erprobt). **Als Nächstes:** Die KI wählt die Tür; zuerst mit
Christophers Einspruch vor der Fahrt. Es gibt keinen offenen Auftrag.

**Davor, 23.11.2026 (abends): Auftrag KI-F8 erteilt, wartet auf die
Übergabe.** Entscheidungen des Projektinhabers nach der ersten Durchfahrt:
Grenzen des Werkzeugs 0,26 m neben der Fahrlinie und 0,37 m zum Drehen
(vorher 0,30 und 0,45 m); **ein Ablauf statt zwei Aufträge** (Anfahrt und
Durchfahrt in einer Mission); dreimal wiederholen; im Auftrag nur noch
**eine** Frage vorab. Gebaut, getestet und simuliert (unten); danach soll
die KI die Tür wählen, zuerst mit Christophers Einspruchsmöglichkeit.

**Davor, 23.11.2026 (nach KI-F7): Amadeus ist zum ersten Mal in dieser Linie
selbst durch die Tür gefahren.** Er stellte sich selbst vor die Labortür
(1,65 m, zwei Drehungen), richtete sich aus und fuhr gerade hindurch in den
Flur (1,90 m, fünf Etappen), ohne Nav2, ohne Nahsensoren, nichts berührt.
Christopher: „ja alles geklappt“; danach: „Jedoch waren die seitlichen
Abstandsgrenzen zu hoch, die können deutlich herunter genommen werden.“
Gelungen im zweiten Durchgang; im ersten lag etwas auf dem Roboter, und die
Tür war nicht ganz offen. **Als Nächstes:** Der Projektinhaber will das
weitere Vorgehen zuerst besprechen; es gibt keinen offenen Auftrag.

**Davor, 23.11.2026 (nach KI-F6): Amadeus hat sich zum ersten Mal selbst
vor die Tür gestellt.** Eine Messung, kein Umstellen: Das Werkzeug fand die
Labortür und entschied „Anfahrt“; Amadeus drehte sich, fuhr 1,42 m, drehte
sich zur Tür, und danach passten Aufstellung, Weg und Kostenkarte, ohne
dass ihn jemand anfasste. Christopher: „ja er hat die Tür gefunden ist zu
ihr gefahren und hat sich ausgerichtet“. **Die Durchfahrt brach nach 0,67 m
ab, wegen zweier Programmfehler im Erkunder, nicht wegen der Räder:** Die
gerade Etappe las erst die Uhr, dann die Odometrie (ein Wert dazwischen
galt als „aus der Zukunft“ → `odom_stale`; für das Drehen seit 29.09.
behoben, für die gerade Etappe nicht), und die Schlussmeldung warf beim
Wechsel von Erfolg zu Fehler einen ROS-Fehler. Beides ist behoben, mit Tests
und Simulation. **Als Nächstes:** Auftrag KI-F7, derselbe Ablauf mit neuem
Build. Christopher hat mit der Übergabe von KI-F6 entschieden, zuerst ohne
Nav2 weiterzumachen ([Bewertung](BEWERTUNG_TUERDURCHFAHRT.md), Nachtrag).

**Davor, 23.11.2026 (mittags): Konzept des Fahrteils überdacht.**
Christopher nach KI-F5: „So kommen wir nicht weiter. […] Ich glaube, ohne
NAV2 schafft er das nicht. Bitte überdenke unser Konzept“. Rückblick,
Möglichkeiten und Empfehlung stehen in
[BEWERTUNG_TUERDURCHFAHRT.md](BEWERTUNG_TUERDURCHFAHRT.md). Kern: Kein
Fehlschlag lag an der Fahrgenauigkeit. Alle realen Durchfahrten fuhr Nav2,
aber Nav2 erreicht seit 15./19.11. kaum ein Ziel, und ohne Nahsensoren
sperrt das Fahrtor Nav2 ganz. Zielbild: der Hybrid (Nav2 grob vor die Tür,
Laser-Etappen mit frischer Messung hindurch).

**Davor, 23.11.2026 (nach KI-F5):** KI-F5 fuhr nicht. Amadeus stand mittig
vor der Tür, aber das Werkzeug meldete fünfmal „30 cm nach links
versetzen“; es nahm die Türrichtung aus zwei Punkten, und eine Kante war
7 cm zu nah gemessen. Christopher: „ich mach mich doch hier nicht zum
clown, der roboter muss die tür finden, sich selber ausrichten und hindurch
fahren“. **Nachgebessert:** Türrichtung aus der Wand neben der Tür, und
Amadeus entscheidet selbst, ob er gleich durchfährt oder sich zuerst vor die
Tür stellt (`--zur-tuer`). Niemand stellt ihn mehr nach Hinweisen um.
**Als Nächstes:** Auftrag KI-F6, weiter ohne Nahsensoren.

Zu KI-F3b neu: Christopher bestätigte (in KI-F4), dass damals etwas vor der
Tür auf dem Boden lag, und der rechte Nahsensor sah an der Haltestelle etwas
in 10 bis 52 cm Höhe. Der Nahbereichs-Halt hat dort also wahrscheinlich
richtig angehalten.

**Davor, 22.11.2026 (nachts), Laborprobe ohne Nahsensoren:** Der
Projektinhaber hat entschieden, das Konzept einmal **ohne die beiden
Nahsensoren** zu prüfen: „Die Nahbereichssensoren machen gerade Probleme.
Deswegen schreibe jetzt einen Testlauf, wo diese komplett deaktiviert
werden.“ Dafür gibt es den Laborschalter `nahsensoren:=false` und den Auftrag
KI-F5 (mit neuem Build). Ohne Nahsensoren erkennt nichts niedrige Dinge
unter etwa 75 cm, und der Kollisionsmonitor sieht nichts; Christopher räumt
den Weg vorher frei. KI-F4 (Messung an der Haltestelle) entfällt.

**Davor (KI-F3b):** Amadeus ist zum ersten Mal in
dieser Linie geradeaus auf die Tür zugefahren: drei Etappen, 1,03 m, nie mehr
als 5 mm neben der Linie. **0,26 m vor der Türlinie hielt er an**, weil in
der Kostenkarte mitten im Durchgang etwas belegt war (0,25 m vor seiner
Vorderkante, 9 cm links der Mitte). Das Türblatt war es nicht. Welche
Quelle die Stelle meldete, war nicht festzustellen; das Werkzeug kann das
jetzt (unten). Im ersten Anlauf am selben Abend hatte sich der Radsensor
beim Start gesperrt (KI-F3).

Die gerade Etappe von 0,5 m ist
am Roboter gelungen (KI-F1). **Durch die Labortür ist Amadeus noch nicht
gekommen.** Im ersten Anlauf wurde die Tür aus der schrägen Lage falsch
vermessen und die Fahrt gar nicht gestartet (KI-F1). Im zweiten passte die
Aufstellung, aber der geplante Weg führte erst schräg zu einem Punkt auf
der Türachse und damit an die Spitze des offenen Türblatts; der
Nahbereichs-Halt hielt Amadeus nach 0,35 m an (KI-F2). Der Halt war
richtig, der Weg war falsch geplant. **Als Nächstes:** Auftrag KI-F5
([AUFTRAG.md](AUFTRAG.md)) ohne Nahsensoren, in zwei Stufen: erst von vorn auf gerader Linie
durch die Türmitte, dann von einem Platz im Raum, von dem Amadeus **selbst
vor die Tür fährt**. Beides wird vor dem Senden gegen das Laserbild geprüft.

**Einwand des Projektinhabers (22.11., spät):** Das Davorstellen von Hand
ist gegenüber den früheren Durchfahrten ein Rückschritt. Das trifft zu;
deshalb gibt es jetzt die Anfahrt (Abschnitt unten) und Stufe 2 im Auftrag.

Davor (21.11.): eine Drehung am Roboter mit Blickrunde, aus der die KI in
4,9 Sekunden die richtige Tür wählte (KI-1). Ein Urteil nach den Kriterien
K0-1 bis K0-6 gibt es weiter nicht (eine Blickrunde, kein Glas, kein
Spiegel).

Diese Linie ist seit 19.11.2026 (spät) die aktive Arbeit; die Hauptlinie ist
geparkt. Dies ist der einzige Iststand dieser Linie. Der Stand der
Hauptlinie steht ausschließlich in `docs/wohnungserkundung/STATUS.md`.

## Wo wir stehen und wohin es geht

**Ziel:** Amadeus erkundet eine Wohnung Raum für Raum selbst und fährt
danach auf Zuruf in einen benannten Raum oder zu einem Gegenstand. Die KI
auf dem KI-Rechner entscheidet, wohin es geht; der Roboter misst nach und
fährt mit seiner Schutzkette.

| Schritt | Was Amadeus dann kann | Stufe im Konzept | Stand |
|---|---|---|---|
| Erstes Sehen | im Stand Bild und Laser aufnehmen, die KI fragen, die Antwort prüfen | KI-0 | **erledigt** (21.11.) |
| Blickrunde | sich selbst einmal herumdrehen; aus acht Bildern nennt die KI den Ausgang | KI-1 | **am Roboter gelungen** (21.11., eine Runde im Labor); für die Kriterien fehlen weitere Runden |
| Die KI wählt, Amadeus fährt | zur gewählten Tür und hindurch, im nächsten Raum neu umsehen; zuerst in der Simulation, dann im Labor | KI-2, KI-3 | **in Arbeit:** Fahrteil gebaut (Etappenfahrt ohne Nav2); am Roboter gelungen: gerade Etappe (KI-F1), Ausrichten (KI-F2), drei Etappen genau auf der Linie bis kurz vor die Tür (KI-F3b); **selbst vor die Tür gestellt und hindurchgefahren (KI-F7; KI-F8: drei von drei in einem Ablauf)**; die Tür bestimmte dabei der Mensch. **Übergabe der KI-Wahl gebaut, in der Simulation gelaufen; am Roboter: Auftrag KI-F9** |
| Raum für Raum | weiter, bis kein Ausgang mehr offen ist (Laborraum, Flur, Schlafzimmer) | KI-3 | offen |
| Räume benennen, um Hilfe rufen | Raumnamen als Vorschlag in der App; Hilferuf mit Grund und Bild | KI-4 | offen |
| Auf Zuruf | „fahr in die Küche“, „such die Tasse“ | KI-5 | offen |

Die Stufen und ihre Kriterien stehen verbindlich im
[Konzept](KONZEPT.md), Abschnitt 8.

## Arbeitsliste

**Offener Auftrag: KI-F9 – die KI wählt die Tür** ([AUFTRAG.md](AUFTRAG.md)),
zweimal von zwei Plätzen, je mit Christophers Ja oder Nein vor der Fahrt;
kein Build.

**Danach, je nach Ergebnis:**
- Zweimal gelungen: Christophers Ja entfällt (die KI wählt, die Vermessung
  prüft, die Schutzkette fährt); dann weiter in den Flur mit neuem
  Rundblick (KI-3). Vorher entscheiden, was nach der Tür kommt (wohin im
  nächsten Raum, wann ein Raum fertig ist).
- Die KI wählt falsch (Christophers Nein): Antworten und Bilder auf dem
  KI-Rechner ansehen (Lotsen-Fenster), Frage oder Vermessung nachbessern;
  keine Fahrt ohne Einspruch, solange das vorkommt.
- Durchfahrt angehalten oder misslungen: zuerst die Ursache aus den
  Meldungen des Erkunders eingrenzen; keine neue Funktion darauf setzen.
- Mit dem nächsten Build des Erkunders: die Grenze der Etappen je Ziel statt
  je Mission (KI-F8, Lauf 3: 10 von 16).
- **Die Vermessung von der Seite des Türblatts** richtig stellen (Ursache
  weiter offen, siehe unten). Für eine KI, die Türen von beliebigen Plätzen
  aus wählt, ist das nötig; bis dahin fährt Amadeus nur aus einer
  Aufstellung vor der Tür.
- Mit dem nächsten Build des Erkunders prüfen, ob das Nachstellen der
  Richtung auf dem letzten halben Meter vor dem Zielpunkt entfallen soll
  (heute ab 0,35 m Restweg; in der Simulation einmal mitten in der Tür).
- Daneben, unabhängig: dieselbe Drehung im Flur für weitere Blickrunden
  (braucht die Freigabe für diesen Raum).

**Offen an der Vermessung (aus KI-0R, KI-1, KI-F1 und KI-F2):**
- **Tür von der Seite viel zu breit:** in KI-F1 1,23 m und 1,25 m statt
  0,85 m (Tür 24° und 32° seitlich), in KI-0R 1,30 m. Vermutung: Von der
  Seite des offenen Türblatts sieht der Laser die Lücke zwischen
  Blattspitze und gegenüberliegendem Pfosten. **Weder bestätigt noch
  widerlegt:** In KI-F2 stand Amadeus bei der Nachmessung nicht in der Lage
  vom Vormittag (Tür bei −2° und 2,58 m statt −32° und 1,59 m) und maß
  0,75 m. Belegt ist seither: Das Blatt geht in den Laborraum auf, steht
  etwa 85° zur Türöffnung und war von Amadeus aus links. Solange das offen
  ist, fährt Amadeus nur aus einer Aufstellung vor der Tür, und das
  Werkzeug nimmt nur 0,65 bis 0,95 m breit vermessene Öffnungen.
- Nach der Drehung bot die Vermessung hinter dem Roboter ein Regal als
  0,81 m breite Öffnung an (0,77 m frei dahinter). Die KI hat es als „wand“
  eingeordnet und nicht gewählt.
- `labor_tuer_seite_nah_b` (KI-0R): derselbe Fall. Am 21.11. stand hier,
  die Vermutung „Türblatt“ sei widerlegt. Widerlegt war nur, dass die dafür
  gebaute Regel an der echten Tür greift; die Ursache selbst war damit
  nicht ausgeschlossen.
- Flur: Der Laser sieht vom Standpunkt aus keine Öffnung, obwohl es dort
  zwei Türen gibt. Wird mit der Blickrunde im Flur neu angesehen.
- Türen werden 8 bis 13 cm zu schmal vermessen (vorsichtige Seite); in KI-1
  die 0,85 m breite Labortür mit 0,73 m nach der Drehung und 0,77 m im
  Stand vom selben Platz. Für die Etappenfahrt zählt die Lage der Türmitte:
  Liegt der Fehler an einem Pfosten, verschiebt sie sich um die Hälfte.

**Vorgemerkt:** Für ein Urteil nach den Kriterien fehlen Ansichten mit Glas
oder Fenster, mit Spiegel, in einem anderen Zimmer und eine Ansicht zweimal
an derselben Stelle. Der zweite Weg, bei dem die KI die Tür im Foto selbst
zeigt und der Laser nur dort misst, bleibt eine Möglichkeit, falls die
Vermessung weiter Türen verfehlt.

**Vor einem Einsatz ohne Aufsicht:** Der Schalter „nur Rundblick“ prüft
nicht, ob der Drehkreis in der Karte frei ist (der Rundblick des
Selbstheilungswegs tut das); dasselbe gilt für das Ausrichten in der
Etappenfahrt.

**Geparkt:** Raumnamen in
der App; Gegenstände finden; größere Kamerabilder für die KI (geliefert
werden 320 × 180).

**Erledigt:** Konzept und Trennregeln · Werkzeuge für den Trockenlauf ·
HomeMy-Konzept ausgewertet · Verbindung zum KI-Rechner · KI-0 Teil A
(19.11.) und Teil B, KI-0N, KI-0R (alle 21.11.) · Lotsen-Fenster gebaut und
auf dem KI-Rechner in Gebrauch · Sucher · Schalter „nur Rundblick“ im
Erkunder (21.11., `6956252`) · Bestand der Türdurchfahrten · Etappenfahrt
gebaut und simuliert (21.11., nachts) · KI-1: erste Drehung und Blickrunde
am Roboter (21.11., nachts).

## KI-F3b – drei Etappen auf der Linie, Halt kurz vor der Tür (Jetson, 22.11.2026, 22:25 bis 22:37)

Zahlen, Nachrechnung und Simulation stehen im
[Archiv](archiv/20261122-kif3-tuer-gerade/). Kein Build; 256 Tests
bestanden. Der Bericht liegt nicht im Repository.

**Was lief:** Messen beim ersten Mal passend (0,77 m, 1,87 m, 0,07 m rechts
der Türmitte, frei 0,38 / 0,39 m); Vorprüfung im scharfen Stack beim ersten
Mal bestanden (Radsensor nicht gesperrt). Drei Etappen geradeaus, LiDAR
0,350 + 0,280 + 0,400 m, seitlich höchstens 5 mm, Richtung höchstens 0,3°
daneben; nachgestellt werden musste nichts. So gerade ist Amadeus in dieser
Linie noch nie gefahren.

**Was nicht lief:** Zu Beginn der vierten Etappe, nach 7 mm, hielt der
Nahbereichs-Halt an. Das Werkzeug danach: belegt „im Fahrstreifen 0.25 m vor
der Vorderkante, 0.09 m links der Mitte“. Christopher: „nein er hat vor der
tür gestoppt“, nichts berührt, „keine nachstellung beobachtet“.

**Nachgerechnet:** Die Stelle lag 0,26 m vor der Türlinie, etwa 6 cm links
der Türmitte, mitten im Durchgang. Das Türblatt liegt in der Kostenkarte
0,37 bis 0,44 m links der Mitte, also daneben. In diese Kostenkarte
schreiben nur die Karte des SLAM (Laser, 0,75 m hoch) und die beiden
Nahsensoren (ab etwa 8 cm über dem Boden). Der Laser sah den Weg frei.
Offen bleibt: ein Gegenstand mindestens 8 cm hoch, eine Fehlmessung der
Nahsensoren oder ein Eintrag der Karte. Markierungen der Nahsensoren
näher als 0,45 m am Sensor werden nie geräumt; eine einzelne Fehlmessung
bliebe liegen.

**Fehler im Werkzeug:** Die Zeile zur Kostenkarte vor dem Senden reichte nur
1,5 m voraus, die Stelle lag 1,61 m voraus. Ob sie schon vor der Fahrt da
war, ist unbekannt. Woher eine belegte Stelle stammt, konnte das Werkzeug
nicht sagen.

**Nachgebessert (nur Werkzeug der KI-Linie):** Die Kostenkarte wird vor dem
Senden auf dem **ganzen Weg** so geprüft, wie der Nahbereichs-Halt sie
liest („Kostenkarte passt.“ ist nötig, sonst wird nichts gesendet). Für
eine belegte Stelle nennt das Werkzeug vor dem Senden, im reinen Messen und
nach einem Halt die Quelle: Karte des SLAM, Nahsensor links oder rechts mit
Höhe über dem Boden, Laser. Dazu eine Zeile, was die Nahsensoren gerade im
Fahrstreifen sehen, mit dem Abstand vom Gehäuse für ein Maßband.

**Simulation** (Laborraum mit 85° offenem Türblatt, Aufstellung wie
KI-F3b):

| Fall | Ergebnis |
|---|---|
| 20 cm hoher Gegenstand 0,26 m vor der Türlinie, 6 cm links | Halt nach 0,96 m (am Roboter 1,03 m), Stelle 0,25 m vor der Vorderkante, 0,12 m links (am Roboter 0,09 m); Herkunft: „Karte (SLAM) frei; Nahsensor links 12 Punkt(e), 16 bis 20 cm über dem Boden; Nahsensor rechts 6 Punkt(e), 13 bis 18 cm“ |
| Messung im Stand an der Haltestelle, mit Gegenstand | „Kostenkarte passt nicht“, Herkunft: beide Nahsensoren, 14 bis 20 cm; Laser sieht dort nichts |
| Messung im Stand an der Haltestelle, ohne Gegenstand | „Kostenkarte passt“, Nahsensoren sehen nichts; keine Fehlalarme von Türblatt oder Pfosten |
| ohne Gegenstand, ganze Fahrt mit dem neuen Werkzeug | „Kostenkarte passt“, durch die Tür, im Flur nach 53 s; die nächste belegte Stelle danach (Flurwand) richtig als „Karte (SLAM) belegt; Laser sieht dort etwas“ benannt |

Das Muster am Roboter gleicht dem mit Gegenstand. Ob dort wirklich etwas
stand, belegt das nicht; eine Fehlmessung sähe genauso aus.

## KI-F3, erster Anlauf – nicht gefahren, Radsensor beim Start gesperrt (Jetson, 22.11.2026, 22:03 bis 22:12)

Kein Build; 253 Tests bestanden. Nur Stufe 1 begonnen; Stufe 2 nicht, weil
Stufe 1 nicht bestanden war. Der Bericht liegt nicht im Repository.

**Was lief:** Aufstellen und Messen passten bei der ersten Messung: Öffnung
0,77 m, 1,87 m entfernt, 0,07 m rechts der Türmitte; „Aufstellung passt“
und „Weg passt“ mit 0,38 m links und 0,39 m rechts neben der Fahrlinie.
Christopher bestätigte die Labortür. Die Messung im scharfen Stack ergab
dasselbe.

**Was nicht lief:** Die Vorprüfung im scharfen Stack fiel durch, nur im
Bereich „D Quellen“: Encoder nicht frisch (letzte Messung 73 s alt),
Encoder-Zeitwache `fault_latched` mit Grund
`encoder_timing_continuity_unproven`, HWT-Fusion nicht bereit
(`wheel_missing_stale_or_invalid`). Motorregler antworteten
(Anfahrzeit bestätigt, „Modbus-Fehler“ 0). Keine Mission, keine Bewegung.

**Was das bedeutet:** Der Motortreiber liest die Radstellungen etwa alle
50 ms. Lagen zwischen zwei gültigen Lesungen mehr als 0,18 s, kann er nicht
belegen, dass sich die Räder in der Lücke nicht gedreht haben. Er versucht
zwei Sekunden lang, die Lücke zu überbrücken, und sperrt die Radmessung
sonst bis zum nächsten Start. Ohne Radmessung lässt die Schutzkette keine
Fahrt zu. Nach den Zeitangaben geschah das etwa 30 s nach dem Start des
Stacks, während der Jetson noch alles hochfuhr. Gemessen ist die Lücke
nicht; der Bericht enthält dazu keine Zahlen.

**Die Selbstheilung** war eingeschaltet (`self_healing:=true`), konnte hier
aber nichts tun: Sie wirkt erst in einer laufenden Mission, und die
Mission wurde nach der durchgefallenen Vorprüfung zu Recht nicht gestartet.
Auch in einer Mission löst sie diese Sperre nicht; das ist so gebaut
(Encodervertrag in `docs/wohnungserkundung/STATUS.md`: keine Rücksetzung
durch die Selbstheilung). Belegt am 04.11. (SH-4, Fahrt 3, erster Versuch):
derselbe Startfehler, 690 s Mission, sieben Heilungen, **nie gefahren**; die
Wiederholung nach einem Neustart fuhr normal.

**Wie oft:** In dieser Linie einer von fünf scharfen Starts mit freien
Motoren (KI-1: 1, KI-F1: 2, KI-F2: 1 ohne Sperre). In der Hauptlinie
dokumentiert seit Oktober (AP06-Vorlauf, SH-4).

**Fehler im Auftrag:** Der Fall war bekannt und steht in der Hauptlinie;
der Auftrag kannte nur die Ausnahme „Motorregler antworten nicht“. Der
Agent hat richtig gehandelt (keine Mission, nicht eigenmächtig neu
gestartet, berichtet).

**Nachgebessert:** Ausnahme „Radsensor beim Start gesperrt“ im Auftrag:
nur lesend sichern, was die Zeitwache meldet (neues Werkzeug
`werkzeuge/radsensor_zustand.py`: Größe und Zeitpunkt der ersten Lücke,
Dauer der Lesepaare), dazu die Last; dann genau ein neuer scharfer Start.
Am Motortreiber wird nichts geändert (Motorsteuerung, AGENTS §2.7).

## Die KI wählt die Tür (gebaut 23.11.2026, nachts)

Entscheidung des Projektinhabers nach KI-F8, auf die Frage „Soll ich das so
bauen, mit deinem Ja oder Nein zur Wahl der KI vor der Fahrt?“: „Ja“.

**Gebaut (nur KI-Linie, kein Build des Erkunders):**
- `blickrunde_aufnehmen.py` hält fest, wo Amadeus am Ende des Rundblicks in
  der Karte steht (TF `map` → `base_link`, nur lesend). Mit dem aus den Scans
  gemessenen Drehwinkel der Runde liegt jede Nummer an einem Ort in der
  Karte (`lotse/wahl.py`).
- `ki_tuer_waehlen.py`: die neueste Blickrunde (höchstens 10 Minuten alt
  und mit Lage in der Karte, sonst wird die KI gar nicht gefragt)
  aufbereiten, die KI über den Lotsen-Dienst fragen (120 s, höchstens zwei
  Versuche bis zu einer gültigen Antwort), prüfen und gegen die Vermessung
  halten. Eine gültige Wahl kommt mit ihrem Ort in eine Wahl-Datei (gilt
  15 Minuten), dazu ein Protokoll ohne Bilder. Für den Menschen: ein Satz
  mit Art, Breite, Entfernung und Richtung von Amadeus aus, je Nummer die
  Einordnung der KI, ihre Begründung; ist die Wahl nicht türbreit, sagt
  der Satz, dass der Fahrteil dort nicht hindurchfährt. Rückgabe 0 (Wahl),
  2 (kein Ausgang oder Vermessung dagegen), 3 (keine gültige Antwort),
  4 (Runde oder Lage fehlt), 5 (KI-Rechner nicht erreichbar).
- `fahrziel_senden.py --zur-tuer --wahl DATEI`: prüft die Wahl (Art,
  Rahmen, Alter), misst neu und nimmt die türbreite Öffnung, deren Mitte
  höchstens 0,40 m neben dem gewählten Ort liegt; liegt eine zweite kaum
  weiter weg, ist das nicht eindeutig, und es fährt nicht. Eine nicht
  türbreite Öffnung an der Stelle nennt es mit ihrem Maß; die Schätzung
  hinter einem Türblatt gilt nur, wenn sie höchstens 0,50 m daneben liegt.
  Danach der Ablauf aus KI-F8; Quelle in allen Meldungen `ki`. `--ende`
  sagt dem wartenden Erkunder, dass kein Fahrziel kommt.
- **Behoben:** Unter der neueren ROS-Fassung beendet `kill -INT` rclpy
  selbst (`ExternalShutdownException`) statt eines `KeyboardInterrupt`; die
  Aufnahme schrieb dann keine Runde (erster Simulationslauf). Aufnahme und
  Lotsen-Dienst fangen jetzt beides ab. Am Roboter (Humble) hatte `kill
  -INT` in KI-1 die Runde geschrieben.
- Tests: KI-Linie 328 ohne ROS (2 übersprungen), 340 mit ROS. Neu u. a.
  `test_wahl.py` (34) und `test_ki_tuer_waehlen.py` (11, gespielte KI:
  richtig, kein Ausgang, zweimal falsch, Unsinn dann richtig, stumm, Runde
  ohne Lage, alte Runde, KI-Rechner fehlt, Ablage in einer Arbeitskopie);
  über echte ROS-Themen das Werkzeug über den Lotsen-Dienst und die
  Aufnahme mit Lage aus TF.

**Simulation** (Laborraum mit Möbeln und 85° offenem Türblatt, ohne
Nahsensoren; Rundblick, Ersatzkamera ohne Bildinhalt, die echte Aufnahme,
eine gespielte KI, die die Welt der Simulation kennt, dann das Werkzeug mit
`--wahl`; ein Lauf, eine Mission). Die Simulation prüft die Kopplung, nicht
das Sehen.

| Fall | Ergebnis |
|---|---|
| mitten im Raum, richtige Wahl | Rundblick 361,5°, 223 Aufnahmen, keine verworfen, Lage festgehalten; Drehwinkel der Runde aus den Scans 351,2° (passend zur Karte; die Odometrie mit 3 % Fehler sagte 362°); gewählte Tür 7 cm neben der wahren Mitte; beim Neumessen wiedergefunden (Mitten 5 cm auseinander); Anfahrt 1,31 m, neu gemessen, Durchfahrt; „Durchfahrt abgeschlossen.“, Quelle ki, 8 Etappen, 3,27 m; im Flur nach 181 s, keine Berührung, engste Stelle 6,0 cm (an der Spitze des Türblatts) |
| anderer Platz, Tür 49° rechts, richtige Wahl | In der Runde drei Öffnungen, darunter eine 0,90 m breite Lücke zwischen Möbeln; die KI wählt die Tür (in der Runde 0,74 m), 3 cm neben der wahren Mitte. Im Stand vier Öffnungen mit neuen Nummern; die gewählte wiedergefunden (2 cm). Anfahrt mit 38° und 88° Drehung (Rest +1,6° und −1,7°), Durchfahrt; „Durchfahrt abgeschlossen.“, 9 Etappen, 3,40 m; im Flur nach 200 s, keine Berührung, engste Stelle 6,6 cm (ebenso) |
| KI wählt falsch (eine 1,12 m breite Lücke) | Satz der Wahl mit „So breit fährt der Fahrteil nicht hindurch“; das Werkzeug: „an der gewählten Stelle ist Öffnung 2 vermessen, 1.19 m breit – nicht türbreit“, „Nichts gesendet“, `ende`; der Erkunder: „beendet ohne Fahrziel (Quelle ki); nichts gefahren“. Keine Bewegung außer dem Rundblick |
| erster Lauf, Aufnahme ohne Runde (Fehler oben) | Der Ablauf schickte `--ende --quelle ki`; der Erkunder schloss sofort: „beendet ohne Fahrziel (Quelle ki); nichts gefahren“ |

Grenze: Wählt die KI eine türbreite Öffnung, die keine Tür ist (etwa die
0,90 m breite Lücke im zweiten Fall), hält das Werkzeug sie nicht auf; dann
fährt Amadeus davor und hindurch, soweit der Weg frei ist. Deshalb zuerst
Christophers Ja vor jeder Fahrt.

## KI-F8 – drei von drei in einem Ablauf (Jetson, 23.11.2026, 21:38 bis 22:24)

Zweiter vollständiger Durchgang auf Christophers Anweisung; der erste
(Release `kif8-20261123_2053`) blieb unvollständig, darin stand Amadeus
einmal auf der Blattseite (Anlass für die Ergänzung unten). Release
`kif8-20261123_2138`, Stand `d61453c`, Tests 370 und 271. Archiv:
[archiv/20261123-kif8-dreimal-durch/](archiv/20261123-kif8-dreimal-durch/).

| Lauf | Start | Ablauf | Ergebnis |
|---|---|---|---|
| 1 | 2,29 m vor der Tür, 0,05 m rechts | gleich hindurch, 7 Etappen, 2,48 m | „Durchfahrt abgeschlossen.“ |
| 2 | 2,31 m vor der Tür, 0,80 m rechts | Anfahrt 1,23 m, neu gemessen (0,05 m rechts), hindurch; 8 Etappen, 3,21 m | „Durchfahrt abgeschlossen.“ |
| 3 | 3,36 m vor der Tür, 0,77 m rechts | Anfahrt 1,81 m, neu gemessen, hindurch; 10 Etappen, 3,73 m | „Durchfahrt abgeschlossen.“ |

Eine Frage vorab; kein Radsensor gesperrt; Rest nach dem Ausrichten
höchstens 1,0°, seitlich höchstens 5 mm, höchstens 0,050 m/s; alle Zähler
der Kette 0; neben der Fahrlinie je 0,38 bis 0,39 m frei. **G-1 trifft
zu.** Beobachtet: Die Etappen zählen über alle Ziele einer Mission (bis 16
erlaubt, Lauf 3: 10); für Aufträge mit mehr Zielen gehört die Grenze je
Ziel.

## Von der Seite des Türblatts (gebaut 23.11.2026, spät)

Anlass: In KI-F8 stellte Christopher Amadeus seitlich vor die Tür, auf die
Seite, zu der das Türblatt aufgeht. Der Laser sah die Öffnung nicht richtig,
weil das Blatt sie verdeckt. Christopher: „Was passiert in solchen Fällen?“
Bisher: keine türbreite Öffnung, keine Fahrt, ein Mensch stellt um. Das
reicht nicht, sobald die KI Türen von beliebigen Plätzen wählt.

**Gebaut (nur Werkzeug, kein Build):**
- `gerade_stuecke`: gerade Stücke im Laserbild, robust gegen Rauschen (teilt
  erst ab 4 cm Abweichung, fügt gleich gerichtete Nachbarn wieder
  zusammen), Laserbild als geschlossener Kreis; je Ende, ob der Laser dort
  weiter sieht („frei“) oder etwas Näheres das Stück verdeckt.
- `tuer_hinter_blatt`: Ein 0,60 bis 0,95 m langes gerades Stück, das an
  einer geraden Wand ansetzt, 55 bis 125° zu ihr steht, mit freier Spitze
  in den Raum ragt, und die Wand auf der Seite des Roboters: das Blatt. Das
  Scharnier liegt, wo es die Wand trifft; die Tür in der Wand auf der
  anderen Seite des Blatts, so breit wie das Blatt lang ist.
- Im Werkzeug nur als Ersatz: wenn keine türbreite Öffnung in der
  gewünschten Richtung liegt oder ihre Entscheidung „keine Fahrt“ wäre.
  Zur geschätzten Tür wird **nur die Anfahrt** gesendet, nie gleich die
  Durchfahrt. Danach misst der Ablauf von vorn neu und findet die Tür
  wieder; sonst „Ende“.

**Nachgerechnet** an nachgebildeten Laserbildern des Laborraums der
Simulation (1 cm Rauschen): von fünf Plätzen auf der Blattseite jedes Mal
die richtige Tür (Scharnier auf 3 cm, Mitte auf 6 cm, 84 bis 85° gemessen);
von sechs Plätzen ohne Blick auf die Blattrückseite und ohne Türblatt kein
Fund. Gegen Fehlfunde: Raumecke hinter einer verdeckenden Werkbank (Ende
nicht frei) und ein 1 m tiefer Schrank an der Wand (zu lang) werden nicht
als Blatt genommen. **Grenze:** Ein Möbel von 0,60 bis 0,95 m Tiefe an einer
Wand kann von der Seite wie ein Blatt aussehen; dann führt die Anfahrt
umsonst vor das Möbel, und die Neumessung findet keine Tür (Ende, keine
Durchfahrt). Die Richtung muss zur gewünschten passen; später sagt die KI am
Bild, ob dort eine Tür ist.

**Simulation** (ohne Nahsensoren, ein Aufruf, eine Mission):

| Start auf der Blattseite | Ergebnis |
|---|---|
| neben einer Stuhllehne (0,31 m) | Tür richtig geschätzt; „keine Fahrt“: zum Drehen nur 0,31 m frei, nötig 0,37 m – richtig, die Ecken hätten die Lehne gestreift |
| Ecke zwischen Wand und Blatt, 1,0 m vor der Türlinie, Blick weg von der Tür | eine vermessene Öffnung mit „keine Fahrt“ (zu nah), dann „Türblatt gesehen: 0.89 m, 85° … Tür geschätzt“; Anfahrt 2,37 m mit zwei Drehungen; neu gemessen „Wiedergefunden … 0.79 m“, „0.00 m rechts, Aufstellung passt“, Weg 0,32/0,40 m; „Durchfahrt abgeschlossen.“; im Flur nach 159 s, keine Berührung, engste Stelle 3,7 cm (im Stand in der Tür neben dem 5° schräg ragenden Blatt) |
| 0,9 m vor der Türlinie, 1,2 m neben der Mitte auf der Blattseite | keine türbreite Öffnung, Tür geschätzt (0,90 m, 85°); Anfahrt 2,07 m; wiedergefunden, 0,01 m rechts; „Durchfahrt abgeschlossen.“; im Flur nach 159 s, keine Berührung, engste Stelle 3,8 cm (ebenso) |
| schräg, 1,55 m vor der Türlinie, 0,93 m neben der Mitte | Tür geschätzt (0,85 m, 89°); Anfahrt; wiedergefunden, 0,00 m; „Durchfahrt abgeschlossen.“; im Flur nach 141 s, keine Berührung, engste Stelle 6,3 cm (beim ersten Drehen neben einer Stuhllehne). Derselbe Start mit dem alten Zeitbudget der Vorlage (60 s) brach mitten in der Anfahrt ab; das war die Simulation, nicht der Ablauf |

## Ein Ablauf und neue Grenzen (gebaut 23.11.2026, abends)

Entscheidungen des Projektinhabers nach KI-F7: „Wir nehmen 0,25 Meter neben
der Fahrlinie und 0,35 Meter zum Drehen“, nach der Rechnung übernommen als
**0,26 m** (der Erkunder prüft selbst 0,25 m; sonst könnte er mitten in der
Tür halten) und **0,37 m** (die Gehäuseecken kreisen 0,355 m um die
Antriebsmitte; bei 0,35 m streiften sie eine Wand); „Diesmal aber ein
Ablauf statt zwei Aufträge“; „noch dreimal“; im Auftrag nur eine Frage
vorab.

**Gebaut:**
- Erkunder (nur mit `stage_drive_only`, sonst unverändert): Fahrziel mit
  `weiter` → danach stehend bis zu 120 s auf das Folgeziel warten, höchstens
  drei Ziele je Mission; Nachricht `ende` → Mission schließt sofort (nach
  einem Ziel erfolgreich, ohne Ziel „beendet ohne Fahrziel“). 14 neue Tests
  (98 in `test_stage_drive.py`).
- Werkzeug: `--zur-tuer` in einem Aufruf: Anfahrt mit `weiter`, nach
  „Fahrziel 1 erreicht“ im Stand neu messen, die gemerkte Tür in der Karte
  wiederfinden (höchstens 0,35 m daneben), Türachse aus der ersten Messung,
  wenn der Laser die Wand jetzt nicht lang genug sieht, dann die
  Durchfahrt. Passt etwas nicht, sendet es `ende`. Grenzen 0,26 m und
  0,37 m. KI-Linie 261 Tests ohne ROS, 271 mit.

**Simulation** (ohne Nahsensoren, ein Aufruf, eine Mission):

| Fall | Ergebnis |
|---|---|
| schräger Start, 1,01 m rechts, Tür 58° rechts | Anfahrt 1,42 m, „Fahrziel 1 erreicht“, neu gemessen, wiedergefunden (0,01 m rechts, Achse aus der Wand), Durchfahrt; „Durchfahrt abgeschlossen.“, 9 Etappen, 3,37 m; im Flur nach 117 s, keine Berührung, engste Stelle 8,0 cm |
| mittig vor der Tür, Stange vor dem rechten Rahmen | Entscheidung Durchfahrt, ein Ziel ohne Folgeziel, 6 Etappen, 2,18 m, „Durchfahrt abgeschlossen.“; im Flur nach 50 s, keine Berührung, engste Stelle 7,5 cm |
| keine passende Öffnung (künstlich: nur 0,95 bis 0,99 m zugelassen) | „Nichts gesendet“, Werkzeug schickt `ende`; Erkunder sofort „beendet ohne Fahrziel; nichts gefahren“, keine Bewegung |

## KI-F7 – erste Türdurchfahrt der KI-Linie (Jetson, 23.11.2026, 12:58 bis 14:54)

Neuer Release `kif7-20261123_1258` (nur `explore_node.py` geändert, wie
erwartet), Tests 356 und 268. Archiv mit Auftrag und beiden Durchgängen:
[archiv/20261123-kif7-erste-durchfahrt/](archiv/20261123-kif7-erste-durchfahrt/).

**Durchgang 2 (gelungen):** einmal umgestellt, weil am ersten Platz zum
Drehen nur 0,39 m frei waren (nötig 0,45 m). Anfahrt 1,65 m (Rest nach dem
Ausrichten −0,1° und −1,0°), danach ohne Anfassen „Aufstellung passt“
(0,03 m rechts), „Weg passt“ (je 0,39 m), „Kostenkarte passt“. Durchfahrt
fünf Etappen, 1,90 m, „Durchfahrt abgeschlossen.“ Seitlich höchstens 5 mm,
höchstens 0,050 m/s, alle Zähler der Kette 0. Christopher: ganz im Flur
„ja“, Platz „genug“, nichts berührt, „ja alles geklappt“. N-1, T-1, A-1,
T-2 bis T-6 treffen zu.

**Durchgang 1:** Radsensor beim ersten scharfen Start gesperrt (Ausnahme,
ein Neustart); erste Anfahrt hielt, weil etwas auf dem Roboter lag; nach
Wiederholung auf Anordnung gelungen; Durchfahrt nicht gesendet, weil links
nur 0,24 m frei waren (Tür nicht ganz offen; Gehäuse 0,23 m: 1 cm Luft).

**Beobachtet:** Nach der Anfahrt kam die Türachse aus den zwei Kanten (aus
1,6 m sieht der Laser die Wand neben der Tür nicht lang genug); es ging
gut, ist aber der Fall, der in KI-F5 täuschte. Der Radsensor sperrte sich
zum zweiten Mal in dieser Linie beim Hochfahren.

## KI-F6 – Anfahrt gelungen, Durchfahrt an zwei Programmfehlern abgebrochen (Jetson, 23.11.2026, 11:07 bis 11:21)

Kein Build (Release `kif5-20261123_0950`), Stand `8717fd9`, 268 Tests
bestanden, ohne Nahsensoren wie verlangt. Archiv mit Auftrag:
[archiv/20261123-kif6-anfahrt-gelungen/](archiv/20261123-kif6-anfahrt-gelungen/).

**Was lief:** eine Messung, kein Umstellen. Amadeus 2,33 m vor der Türlinie,
1,01 m rechts der Türmitte; Labortür 0,88 m, 2,54 m, 18° links, Türachse aus
der Wand; Entscheidung „Anfahrt“, Christopher bestätigte die Tür. **Anfahrt
(erste Mission) gelungen:** 69,8° gedreht (Rest −0,4°), drei Etappen, 82,2°
gedreht (Rest +0,7°), eine Etappe; 1,42 m, seitlich höchstens 5 mm, Winkel
höchstens 0,3° daneben; „Anfahrt abgeschlossen.“ Danach ohne Anfassen:
„0.06 m rechts, Tür 8° links – Aufstellung passt“, „Weg passt“ (je 0,38 m
frei), „Kostenkarte passt“. Durchfahrt (zweite Mission): 10,4° gedreht,
Etappe 1 mit 0,365 m bestanden.

**Was nicht lief:** In Etappe 2 nach 0,305 m „Encoder-Odometrie kurzzeitig
nicht frisch“, Etappe `odom_stale`, dann „Logger severity cannot be changed
between calls.“ (Mission `FAILURE`). 0,67 m von 2,38 m, nichts berührt, kein
Eingriff. Christopher: „Warum ist er jetzt im letzten Schritt nicht hindurch
gefahren“.

| Kennung | Ergebnis |
|---|---|
| N-1 ohne Nahsensoren | trifft zu |
| T-1 Vermessung | trifft zu (0,88 m; nicht umgestellt) |
| A-1 selbst ausgerichtet | **trifft zu** |
| T-2 Abschluss | trifft nicht zu |
| T-3 Ausrichten | trifft zu (Rest höchstens 0,7°) |
| T-4 durch die Tür | trifft nicht zu |
| T-5 Abstand | ohne Urteil |
| T-6 Kette | trifft nicht zu („Odometrie kurzzeitig nicht frisch“ 1) |
| H-1 Herkunft | trifft nicht zu (kein Halt an einer belegten Stelle; die Zeile entfiel) |

**Ursache, zwei Programmfehler im Erkunder:**
1. `_drive_forward_lidar` las erst die Uhr, dann die Odometrie. Der
   Odometrie-Rückruf läuft in einem anderen Faden; kommt er dazwischen, ist
   das „Alter“ negativ, und die Prüfung wertet das als Zeitfehler: sofort
   `odom_stale`. Für `_rotate_in_place` war genau das seit `f746b1c`
   (29.09.2026) behoben. Indizien: 1,27 s zwischen Warnung und Ende der
   Etappe (die Frist für echte Ausfälle ist 5 s), danach bestätigte dieselbe
   Odometrie den Stillstand, das Fahrtor meldete keinen Ausfall. Der innere
   Alterswert ist nicht protokolliert; sehr wahrscheinlich, nicht bewiesen.
2. `ende()` rief dieselbe Programmstelle erst mit `info`, dann mit `error`
   auf; rclpy wirft dann. Nur im zweiten Auftrag eines Stacklaufs nach einem
   gelungenen; in den Simulationen gelangen immer beide.

**Behoben (nur Etappenfahrt):** `_drive_forward_lidar(...,
snapshot_before_clock=True)` liest Odometrie und Scan vor der Uhr (Vorgabe
aus, für die Hauptlinie unverändert); die Schlussmeldung in zwei Aufrufen.
Sechs neue Tests stellen beide Fehler am alten Stand nach (`odom_stale`,
ValueError) und bestehen am neuen; Erkunder-Tests sonst unverändert
(dieselben 26 Tests mit echtem ROS-Knoten scheitern hier vorher wie
nachher). Simulation ohne Nahsensoren, schräger Start 1,01 m rechts:
Anfahrt 1,41 m, Durchfahrt 1,97 m, „Durchfahrt abgeschlossen.“, im Flur nach
116 s, keine Berührung, engste Stelle 7,3 cm.

Für die geparkte Hauptlinie festgehalten: `_drive_forward_localized` und
`_drive_forward_supervised` lesen ebenfalls erst die Uhr.

## KI-F5 – nicht gefahren: Amadeus stand mittig, das Werkzeug kippte die Tür (Jetson, 23.11.2026, 09:50 bis 10:18)

Zahlen und Nachrechnung stehen im
[Archiv](archiv/20261123-kif5-ohne-nahsensoren/). Der Bericht liegt nicht im
Repository.

**Was lief:** Build des Release `kif5-20261123_0950` (177 s, alle Prüfzeilen
wie erwartet, Profile gleich `kif1`), Tests 350 und 264 bestanden. Ohne
Nahsensoren im Stand: kein VL53-Knoten, Fahrtor `require_near_field`
`False`, beide VL53-Quellen des Kollisionsmonitors aus (diese Version kennt
das Abschalten einzelner Quellen), Logzeile zweimal. N-1 trifft im Stand zu.

**Was nicht lief:** Fünf Messungen meldeten „steht 0.30 bis 0.33 m rechts
neben der Türmitte“, Tür 7 bis 8° gedreht; die ersten zwei dazu „Weg passt
nicht“ (etwas lag auf dem Roboter im Blick des Lasers, von Christopher
entfernt). Keine Fahrt; Christopher beendete den Durchgang.

**Ursache, nachgerechnet:** Die linke Türkante lag wie am 22.11. auf 2 cm
an derselben Stelle, Amadeus stand also am selben Platz und mittig. Die
rechte Kante lag 7 cm näher (der Laser traf dort etwas Schmales vor dem
rechten Rahmen). Aus den zwei Kanten gerechnet kippte die Tür um 7,3°, auf
1,8 m wurden daraus 0,30 m „daneben“. Für die Anfahrt gab es die Achse aus
der Wand schon, für die Aufstellung nicht.

**Fehler der Planung:** Eine Prüfung, nach der ein Mensch den Roboter
umstellt, stützte sich auf zwei einzelne Punkte; der Auftrag erlaubte bis zu
acht Messungen mit Umstellen; und die Selbstausrichtung (Stufe 2) war an die
Stufe 1 gebunden.

**Nachgebessert (nur Werkzeug der KI-Linie):**
- `tuerachse`: Die Türachse kommt in allen Betrieben aus der geraden Wand
  neben der Tür; nur ohne Wand aus den Kanten. Mit den Zahlen aus KI-F5:
  aus den Kanten 0,296 m und 7,3° (wie gemeldet), aus der Wand mittig.
- `--zur-tuer`: misst, entscheidet „Durchfahrt“ (passend, Weg und
  Kostenkarte frei) oder „Anfahrt“ (sonst, wenn geprüft möglich) und
  sendet; nach der Anfahrt eine zweite Mission mit `--tuer`. Am Ende steht
  „Anfahrt abgeschlossen.“ oder „Durchfahrt abgeschlossen.“ (auch bei
  `--tuer`).
- Mehrere türbreite Öffnungen: Vorschlag ist die mit dem meisten freien Raum
  dahinter.

**Simulation** (ohne Nahsensoren, 85° offenes Blatt):

| Fall | Ergebnis |
|---|---|
| Stange 6 bis 10 cm vor dem rechten Türrahmen, Amadeus mittig (wie KI-F5) | „Türachse aus der Wand (60 Laserpunkte über 1,12 m)“, „0.03 m rechts, Tür 0°, Aufstellung passt“; Entscheidung Durchfahrt; „Durchfahrt abgeschlossen.“ (6 Etappen, 2,20 m); im Flur nach 52 s, keine Berührung, engste Stelle 7,6 cm |
| Amadeus schräg im Raum, 1,00 m rechts der Türmitte, Tür 58° rechts | „Aufstellung passt nicht“; Entscheidung Anfahrt: 28° links drehen, 1,01 m, 86° rechts drehen, 0,45 m; „Anfahrt abgeschlossen.“ (1,40 m, 114° gedreht). Zweite Mission mit `--tuer`: „0.00 m rechts, Tür 1°, Aufstellung passt“, 5 Etappen 2,01 m, einmal 7° nachgerichtet; im Flur nach 116 s, keine Berührung, engste Stelle 5,7 cm. Wiederholt nach der Nachbesserung der Schlusszeile: gleiche Entscheidung, „Durchfahrt abgeschlossen.“ auch nach `--tuer`, im Flur nach 117 s, keine Berührung, engste Stelle 6,7 cm |

## Laborprobe ohne Nahsensoren (Entscheidung des Projektinhabers, gebaut 22.11.2026, nachts)

**Entscheidung:** „Die Nahbereichssensoren machen gerade Probleme.
Deswegen schreibe jetzt einen Testlauf, wo diese komplett deaktiviert
werden. Wir wollen jetzt einmal das Konzept überprüfen, ohne die
Nahbereichssensoren zu nutzen. Diese machen immer wieder Probleme.“

**Was dafür nötig war (gemessen am Code, nicht vermutet):** Die Nahsensoren
hängen an drei Stellen. (1) Der VL53-Knoten speist beide Kostenkarten.
(2) Der **Kollisionsmonitor** hat im Kartierbetrieb **nur** die beiden VL53
als Quelle. (3) Das **Fahrtor** gibt im Erkundungsbetrieb nur Befehle frei,
wenn beide VL53 frisch und gesund melden; ohne sie sperrt es jede Bewegung.
Abschalten allein hätte Amadeus also stillgelegt.

**Was gebaut ist** (dritte Anschlussstelle, MASTERPLAN §10.3; Vorgabe
überall unverändert):
- `app_mapping.launch.py` und `nav_mapping.launch.py`: Startargument
  `nahsensoren` (Vorgabe `true`).
- `vl53_near_field.launch.py`: `start_vl53` (Vorgabe `true`); mit `false`
  startet der VL53-Knoten nicht. TF und Kollisionsmonitor laufen weiter (er
  liegt im Fahrbefehlspfad).
- `collision_monitor_ohne_nahsensoren.yaml`: schaltet beide VL53-Quellen
  ab, damit eine Quelle ohne Daten keinen Halt erzwingt. Der
  Kollisionsmonitor sieht dann nichts und reicht die Befehle durch.
- Fahrtor `require_near_field` (Vorgabe `true`): mit `false` gilt die
  Ausnahme **nur** für die beiden begrenzten Kanäle des Erkunders (Drehen
  bis 0,15 rad/s, geradeaus bis 0,08 m/s). Nav2- und Raumfahrten bleiben
  ohne VL53 gesperrt; LiDAR, Karte, Odometrie und Not-Aus bleiben Pflicht.
- Simulation: Experiment `etappenfahrt_ohne_nahsensoren.yaml`.

**Was in diesem Betrieb fehlt:** Niedrige Dinge unter der LiDAR-Höhe sieht
nichts; der Kollisionsmonitor bremst und hält nicht. Es bleiben: die
Prüfungen des Werkzeugs (Laserbild, Kostenkarte aus der Laserkarte), der
Streifen vor jeder Etappe (Laser), der Nahbereichs-Halt auf der Laserkarte,
5 cm/s, der Not-Aus und Christopher, der den Weg vorher freiräumt.

**Simulation** (Laborraum, 85° offenes Blatt, Aufstellung wie KI-F3b):

| Fall | Ergebnis |
|---|---|
| ohne Nahsensoren, ohne Gegenstand | „Kostenkarte passt“, durch die Tür, im Flur nach 50 s, keine Berührung, engste Stelle 10,2 cm; das Werkzeug meldet „Nahsensoren … nicht empfangen“ |
| ohne Nahsensoren, 20 cm hoher Gegenstand 0,26 m vor der Türlinie | **Berührung** bei 42 s mit vollen 0,05 m/s, ohne Bremsen (mit Nahsensoren hielt Amadeus davor an) |
| ohne Nahsensoren, Anfahrt von rechts schräg und Durchfahrt | beide Wege „Kostenkarte passt“, selbst vor die Tür und hindurch, im Flur nach 117 s, keine Berührung, engste Stelle 8,2 cm |
| Gegenprobe **mit** Nahsensoren (Vorgabe), derselbe Stand | wie vorher: durch die Tür, im Flur nach 53 s, keine Berührung; Fahrtor im Normalbetrieb („beide VL53 müssen fortlaufend frisch bleiben“) |

## Anfahrt: Amadeus stellt sich selbst vor die Tür (gebaut 22.11.2026, spät)

**Warum:** Der Projektinhaber: „Der Roboter ist aber schon mal durch die Tür
gefahren, in den Flur hinein. Das ist schon dreimal passiert. […] Warum
soll er sich auf einmal nur vor die Tür stellen? Das ist ja ein
Rückschritt.“ Die früheren Durchfahrten fanden den Weg zur Tür selbst, über
Nav2 (Bestand unten); die Etappenfahrt fährt nur gerade Stücke. Die Anfahrt
gibt Amadeus das Hinfahren zurück, weiter ohne Nav2.

**Was gebaut ist** (nur Werkzeug der KI-Linie, kein Paket unter `src/`):
- `lotse/fahrziel.py`, `anfahrt`: vom Standplatz zu einem Vorpunkt auf der
  Türachse, dort zur Tür drehen, 0,45 m auf sie zu; danach steht er 1,6 bis
  2,1 m mittig vor der Tür. Unter den möglichen Wegen nimmt er den mit dem
  wenigsten Drehen; steht er schon auf der Achse, entfällt der Vorpunkt.
- Geprüft am Laserbild: neben jeder Strecke 0,30 m frei, an jeder
  Drehstelle ein freier Kreis von 0,45 m, freie Sicht des Lasers auf die
  Punkte und auf den Drehkreis vor der Tür.
- `wandrichtung`: Die Türachse steht senkrecht auf der geraden Wand neben
  der Tür (Linie mit den meisten Laserpunkten, höchstens 3 cm daneben,
  mindestens 0,40 m lang). Nur ohne solche Wand gilt die Verbindung der
  Türkanten; das Werkzeug sagt, woraus die Achse stammt.
- `werkzeuge/fahrziel_senden.py --vor-die-tuer` (mit `--nur-messen` ohne
  Senden). Danach `--tuer` wie bisher, mit neuer Messung.

**Simulation** (Laborraum mit 85° offenem Türblatt, je ein Stacklauf mit
zwei Missionen; der zweite Missionsstart ohne Neustart ging jedes Mal):

| Startplatz | Anfahrt | Danach vor der Tür | Durchfahrt |
|---|---|---|---|
| rechts schräg (2,05 m vor der Tür, 1,15 m rechts, Tür 62° rechts) | 28° links, 1,01 m, 86° rechts, 0,45 m | 1,60 m, 0,01 m neben der Mitte; „Aufstellung passt“, „Weg passt“ (links 0,32 m, rechts 0,40 m) | im Flur nach 114 s; keine Berührung, engste Stelle 8,4 cm (gepolsterte Kontur) |
| Raummitte (2,71 m vor der Tür, 0,57 m links) | 29° rechts, 0,88 m, 41° links, 0,45 m | 1,62 m, 0,08 m links; passt (0,32 m / 0,40 m) | im Flur nach 104 s; keine Berührung, 8,4 cm |
| Seite des Türblatts, nah | keine: Tür 1,33 m breit vermessen, „keine Öffnung ist türbreit vermessen“ | – | – |
| weit weg (3,30 m vor der Tür, 0,11 m rechts, Tür 12° rechts) | 1,29 m, 18° rechts, 0,45 m | 1,64 m, 0,09 m links; passt (0,33 m / 0,40 m) | im Flur nach 103 s; keine Berührung, 6,1 cm |

**Ein Fehler, den die Simulation gezeigt hat:** Im ersten Lauf stand Amadeus
nach der Anfahrt 0,17 m neben der Türmitte, und die Durchfahrt wurde zu
Recht abgelehnt (links nur 0,26 m frei). Ursache: Aus zwei schräg gesehenen
Türkanten war die Türachse 6° verdreht. Mit der Achse aus der Wand neben
der Tür: 0,01, 0,08 und 0,09 m.

**Grenzen:** Am Roboter ist nichts davon gelaufen. Von der Seite des
offenen Türblatts gibt es keine Anfahrt (dort wird die Tür falsch
vermessen; in der Simulation tritt derselbe Fehler auf, 1,33 m). Neben der
Fahrlinie bleiben am Türblatt in der Simulation 0,32 m bei nötigen 0,30 m:
Landet die Anfahrt einige Zentimeter zur Blattseite hin, lehnt die
Durchfahrt ab. Der Laser sieht nichts unter 0,75 m.

## KI-F2 – erste Fahrt auf die Tür zu, am Türblatt angehalten (Jetson, 22.11.2026, 16:47 bis 17:23)

Zahlen, Nachrechnung und Simulation stehen im
[Archiv](archiv/20261122-kif2-tuerdurchfahrt/). Kein Build; 233 Tests
bestanden.

**Was lief:** Aufstellen und Messen passte beim ersten Mal (Tür 0,77 m,
1,90 m entfernt, Amadeus 0,18 m rechts der Türmitte). Das Ausrichten am
Roboter gelang in einem Durchgang (9,4° gedreht, Restfehler 0,8°); das war
am Roboter noch nie gelaufen.

**Was nicht lief:** Die Fahrt hielt in der ersten Etappe nach 0,345 m mit
„Nahbereich vor dem Roboter nicht frei (0,25 m vor der Vorderkante)“.
Nichts berührt. Der Projektinhaber: „Der Roboter ist nur gerade aus gefahren
und wäre gegen das Türblatt gefahren. Der Roboter hat sich überhaupt nicht
der Tür ausgerichtet und nachkorrigiert!“

**Ursache (nachgerechnet aus den Maßen des Berichts):** Der Weg ging nicht
zur Tür, sondern zuerst schräg nach links zu einem Punkt auf der Türachse
1,1 m vor der Tür; erst dort hätte sich Amadeus zur Tür gedreht. Mit dem
Türblatt links, 85° zur Türöffnung, führt diese Strecke 0,245 m an der
Blattspitze vorbei (Gehäuse halb 0,23 m, Streifen des Halts 0,255 m), und
am Wendepunkt hätte die vordere linke Ecke 1,6 cm vor der Spitze gestanden.
Die gerade Linie vom Standplatz durch die Türmitte hält dort 0,386 m. In
der Simulation mit einem solchen Blatt kam der alte Weg bis auf 4,7 cm an
die Spitze heran.

**Fehler der Planung, festgehalten:** (1) Der Weg wurde nur aus den zwei
Türkanten gerechnet und nicht gegen das geprüft, was der Laser sieht.
(2) Die Annahme zum Türblatt (rechter Winkel, 0,40 m neben der Achse) war
ungeprüft. (3) Der Umweg über die Türachse war bei fast mittiger
Aufstellung unnötig und für den Menschen am Roboter nicht zu verstehen.
(4) Nicht geklärt: Der Halt meldete das Hindernis 0,58 m voraus, die
Rechnung sieht die Blattspitze bei 0,78 m.

**Nachgebessert (nur Werkzeug der KI-Linie):** gerade Linie vom Standplatz
durch die Türmitte; Prüfung, dass am Laserbild links und rechts der Linie
0,30 m frei sind, mit Hinweis, wohin zu versetzen ist; eine Zeile dazu, was
in der Kostenkarte vor dem Roboter belegt ist (vor dem Senden und nach
einem Halt). Simulation mit 85° offenem Blatt: aus der Lage von KI-F2 im
Flur nach 51 s, keine Berührung; von der Seite des Blatts lehnt das
Werkzeug ab („links … nur 0,23 m frei …: bitte etwa 15 cm nach rechts
versetzen“).

## KI-F1 – die erste Etappe am Roboter (Jetson, 22.11.2026, 15:15 bis 16:15)

Zahlen und Abweichungen stehen im
[Archiv](archiv/20261122-kif1-erste-etappen/). Release `kif1-20261122_1515`
auf `baa16b7`; 345 und 228 Tests bestanden.

**Stufe 1, gerade Etappe von 0,5 m: alle sechs Kriterien erfüllt.** Laser
0,505 m, Maßband „ca. 550mm“, seitlich 0,000 m, Winkel 0,0°, 12,8 s, an der
Basis höchstens 0,050 m/s, kein Nav2-Ziel, der Kollisionsmonitor hat nicht
gebremst, nichts berührt. Christopher: „die fahrt war super“. Die Simulation
hatte 0,505 m vorhergesagt.

**Stufe 2, Tür: nicht gefahren.** Das Werkzeug vermaß vor dem Missionsstart
eine einzige Öffnung, 1,25 m breit, 32° rechts, 1,59 m entfernt; Christopher
bestätigte, dass dort die Labortür liegt. Verlangt waren 0,70 bis 0,90 m,
also keine Mission. Im Stand hatte dieselbe Messung von einem anderen Platz
1,23 m ergeben.

**Fehler der Planung, festgehalten:** (1) Der Messfehler war seit KI-0R
bekannt und offen; der Auftrag schickte den Roboter trotzdem vor die Tür.
(2) Die Aufstellanweisung „Blick ungefähr zur Tür“ ließ eine Lage zu, in der
die Tür 32° seitlich lag. (3) Bei falscher Breite kannte der Auftrag nur das
Ende; neu aufstellen und erneut messen wäre gefahrlos gewesen, und der
Projektinhaber hatte alles aufgebaut. (4) Die Frage „Welche Nummer ist die
Labortür?“ war ohne Bild nicht zu beantworten.

**Nachgebessert (nur Werkzeug der KI-Linie, kein Paket der Hauptlinie):**
Eine Öffnung gilt für die Durchfahrt nur zwischen 0,65 und 0,95 m als Tür;
das Werkzeug bewertet die Aufstellung (Abstand zur Türlinie 1,5 bis 2,6 m,
höchstens 0,25 m neben der Türmitte, Tür höchstens 25° neben der
Blickrichtung) und sagt in Worten, was zu ändern ist; `--nur-messen` zeigt
das Protokoll der Vermessung mit beiden Kanten jeder Lücke. Der Vorpunkt
liegt jetzt 1,1 m vor der Türlinie statt 0,7 m: Ein in den Raum offenes
Türblatt (bis 0,9 m) endet davor, und beim Ausrichten schwenken die Ecken
des Gehäuses nicht bis ans Blatt. In der Simulation mit einem solchen Blatt
kam Amadeus von vorn durch (sechs Etappen, im Flur nach 59 s).

## KI-1 – die erste Blickrunde aus eigener Kraft (Jetson, 21.11.2026, 20:43 bis 21:30)

Zahlen, Abweichungen und Lehren stehen im
[Archiv](archiv/20261121-ki1-blickrunde/). Gelaufen auf `a0ad82b`, also ohne
den Code der Etappenfahrt.

**Ergebnis nach den vorab festgelegten Kriterien: R1 bis R6 erfüllt.**

- **Drehung:** 363,2° in 81,3 s (Simulation: 361,7° in 77 s), acht
  Abschnitte, höchstens 0,10 rad/s, kein Fahrbefehl voraus, kein Nav2-Ziel.
  Endpunkt 8 mm neben dem Start. Christopher: nichts berührt, nicht
  gewandert, „genau richtig“.
- **Kamera neben dem Stack:** Bilder 2,00 Hz, Scans mindestens 9,43 Hz, auch
  in der Drehung; keine Fehlerzeile. Rechenlast im Stand: Last 11, 29 %
  Leerlauf.
- **Blickrunde:** 286 Paare, acht Bilder höchstens 4,3° neben dem Soll.
- **Vermessung:** Labortür als Nr. 1 angeboten (0,73 m, wahr 0,85 m); dazu
  als Nr. 2 ein Regal hinter dem Roboter.
- **KI:** gültige Antwort in 4,87 s (davon 2,69 s Laden), Wahl Nr. 1 („Tür
  offen“), Nr. 2 als „wand“. Christopher bestätigt Nr. 1 als einzigen
  Ausgang, die Nummer steht mittig auf der Schwelle. Raumname falsch
  („Wohnzimmer“).

**Abweichungen, die auf den Auftrag zurückgehen:** Der erste scharfe Start
fiel in der Vorprüfung durch, weil die Motoren noch gesperrt waren; der
Auftrag fragte nicht danach und sah keinen zweiten Start vor. Der Agent hat
nach Christophers „motoren sind jetzt wieder frei“ einmal neu gestartet und
das als Abweichung berichtet. Ein Suchmuster des Auftrags für den Status
traf nichts. Im Auftrag KI-F1 gibt es kein Suchmuster mehr; antworten die
Motorregler nicht, meldet der Agent das als Befund und darf nach
Christophers „frei“ einmal neu starten. Eine Vorabfrage nach der
Motorsperre gibt es auf Wunsch des Projektinhabers nicht.

**Beobachtung zur Hauptlinie (nicht geändert):** Das Prüfskript ohne
`--aktiv` meldet „Encoder-Shadow sichtbar“, auch wenn die Motorregler nicht
antworten. Im Stand ist das unschädlich.

## Zwei Festlegungen des Projektinhabers (21.11.2026, nachts)

1. **Die KI bekommt Zeit, und es gibt keinen stillen Rückfall.** Amadeus
   steht, während die KI überlegt. Antwortet sie nicht, fragt er erneut und
   bleibt sonst stehen und meldet es; er fährt nicht unbemerkt nach der
   alten Regel weiter. Steht im [Konzept](KONZEPT.md) v1.5, Abschnitt 6.
   Für KI-1 heißt das: Der alte Explorer fährt dort gar nicht mit (der
   Schalter lässt nur die Drehung zu), und die KI hat 120 s für ihre
   Antwort.
2. **Der Fahrteil soll aus Code entstehen, der schon real funktioniert
   hat.** Dazu der Bestand und ein Vorschlag im nächsten Abschnitt.

## Fahrteil: was es schon gibt (Bestand vom 21.11.2026)

Durchsucht: die Historie dieses Branches, der Branch
`codex/hwt601-encoder-shadow` und die Dokumente. Nichts gefahren, nichts
geändert.

**Türdurchfahrten, die real gelungen sind:**

| Wann | Was | Wie gefahren | Wo der Stand liegt |
|---|---|---|---|
| 18.08.2026 | erster Raumwechsel, vom Beobachter bestätigt (68-cm-Tür mit Schwelle), ein Lauf | Ziel 1,05 m hinter der Tür über Nav2 | `bf25594`, in der Historie dieses Branches |
| 11.09.2026 | einzelne Türdurchfahrt: im vierten Lauf stand das ganze Chassis im Nachbarraum (vom Nutzer bestätigt; die Software wertete den Wechsel in diesem Lauf noch nicht als Erfolg) | Rundblick, Türhals in der Karte erkennen, Vorpunkt vor der Tür über Nav2, ausrichten, Auslaufpunkt hinter der Tür über Nav2 | Branch `codex/hwt601-encoder-shadow`, `1d91229` |
| 11.09.2026 | Arbeitszimmer → Flur: im dritten Lauf bestanden (`portal_crossings=1/1`, vom Nutzer bestätigt), danach weiter im Flur | derselbe Ablauf | derselbe Stand |
| 08.11.2026 | SH-7: zwei von drei Fahrten durch die 80-cm-Labortür, einmal auch zurück | gewöhnliche Erkundungsziele über Nav2 im Selbstheilungsbetrieb | Release `selbstheilung-sh7-20261108_1617`, unverändert auf dem Jetson (HEAD `4c25fb3`) |

Am 26./27.09. scheiterten zwei Wiederholungen des Ablaufs vom 11.09. schon
vor der Tür (VL53-Treiber, HWT-Status). Am 15.11. und 19.11. kam Amadeus
nicht mehr durch die Tür; am 19.11. erreichte er kein einziges Ziel
(Hauptlinie, SH-9). **Alle gelungenen Durchfahrten fuhren über Nav2; genau
dieses Fahren über Nav2 trägt auf dem heutigen Stand nicht, und die Ursache
ist nicht eingegrenzt.**

**Einzelne Bausteine, die am 10./11.09. real bestanden haben** (derselbe
Branch, je eigener begrenzter Test):

| Baustein | Ergebnis real | Fährt über |
|---|---|---|
| Rundblick 360° in acht Abschnitten | 10.09. und 11.09. bestanden (360,7° bis 361,7°) | Drehkanal des Erkunders |
| Auf einen Punkt ausrichten | Teil der Türläufe vom 11.09. | Drehkanal |
| **Eine gerade Etappe von 0,50 m, vom Laser gemessen**, höchstens 0,05 m/s | 11.09. bestanden: 0,500 m, seitlich −15 mm, Richtung −2,5° | Direktkanal des Erkunders, ohne Nav2 |
| Prüfung „Streifen in Fahrzeugbreite frei“ vor der Etappe | Teil derselben Läufe | – |

**Was davon im heutigen Explorer steckt** (Vergleich Funktion für Funktion
zwischen `1d91229` und heute):

- Der Türablauf (`_portal_plans`, `_matching_portal_plan`,
  `_execute_portal_plan`, `_navigate_connected_portal_exit`): **keine Zeile
  geändert.** `portal_planning.py` drei Zeilen, `lidar_motion.py` gleich.
- Die gerade Etappe (`_drive_forward_lidar`, 339 Zeilen): vier Zeilen
  geändert. Ausrichten (`_prealign_to_goal`): zwei Zeilen. Drehen
  (`_rotate_in_place`): zwölf Zeilen.
- Das Fahrtor lässt vom Erkunder weiter genau diese zwei direkten Bewegungen
  zu: Drehen bis 0,15 rad/s und Geradeaus bis 0,08 m/s mit kleiner
  Lenkkorrektur.
- **Nicht mehr im heutigen Stand:** die fünf Testprofile
  (`hwt601_scan_only`, `_translation_only`, `_room_only`, `_door_only`,
  `_office_hall`) und ihre Startskripte; sie liegen nur auf dem Branch.
- Erreichbar ist das alles nur im alten Weg des Erkunders (ohne
  `self_healing`). Im Stack vom 19.11. kommt der Erkunder dort nicht hin;
  deshalb war schon „nur Rundblick“ ein eigener Schalter.

**Entschieden (Projektinhaber, 21.11.2026 nachts: „bau das so, zuerst die
Simulation; erst ohne Nav2, und wenn das nicht reicht, binden wir Nav2
ein“):** Der Fahrteil entsteht aus den einzeln bestandenen Bausteinen ohne
Nav2:
ausrichten, gerade Etappe bis vor die Tür, auf die Türachse ausrichten,
gerade Etappen durch die Tür bis etwa einen halben Meter dahinter, stehen
bleiben, neue Blickrunde. Zwischen den Etappen wird die Öffnung neu
vermessen. Gründe: Jeder Baustein hat real bestanden und ist praktisch
unverändert; er meidet das Fahren über Nav2, das am 19.11. kein Ziel
erreichte; das Fahrtor erlaubt genau diese Bewegungen schon. Grenze: Das
geht nur, wenn der Weg zur Tür in geraden Stücken frei ist. Um Möbel herum
braucht es später wieder Nav2; dafür liegt der Türablauf vom 11.09.
unverändert bereit.

Gebaut ist das als zweite Anschlussstelle im Erkunder; siehe den nächsten
Abschnitt.

## Etappenfahrt: der Fahrteil ohne Nav2 (gebaut 21.11.2026, nachts)

**Was gebaut ist:**

- Im Erkunder das Startargument `stage_drive_only` (Vorgabe aus), durch
  dieselben drei Startdateien gereicht wie `initial_scan_only`. Eingeschaltet
  wartet ein Auftrag stehend auf genau ein Fahrziel und fährt es an:
  ausrichten, gerade, vom Laser gemessene Etappen bis 0,5 m bei 0,05 m/s,
  nach jeder Etappe bestätigter Halt. Mit beiden Schaltern kommt zuerst der
  Rundblick. Ohne gültiges Ziel bewegt sich nichts (Wartezeit 420 s, dann
  Meldung). Am Erkunder kamen nur Zeilen hinzu (506, keine geändert), dazu
  das Modul `stage_drive.py`.
- In dieser Linie `lotse/fahrziel.py` (Vorpunkt 0,7 m vor und Auslaufpunkt
  0,6 m hinter der Türlinie, beide auf der Türachse) und
  `werkzeuge/fahrziel_senden.py` (misst die Öffnungen im Stand neu, wählt
  nach Nummer oder Richtung, sendet das Ziel und zeigt die Meldungen des
  Erkunders). Jedes Ziel nennt, wer gewählt hat (`ki`, `mensch`, `test`);
  der Erkunder schreibt das in seine Meldungen.
- Zwei Prüfungen vor und in jeder Etappe: der Streifen in Fahrzeugbreite im
  Laser (frei und sein Ende gesehen, 15 cm Reserve) und der
  **Nahbereichs-Halt** an der Kostenkarte mit den Treffern der VL53 (25 cm
  vor der Vorderkante).

**Simulation** (ganzer Stack wie am 19.11., möbliertes Labor mit 80-cm-Tür
und Flur, Laser mit 1 cm Rauschen; das Ziel wählt eine gespielte KI, die die
richtige Tür nennt; keine Kamera):

| Lauf | Start | Ergebnis | Kontrolle an der Welt |
|---|---|---|---|
| Gerade Etappe 0,5 m | freier Raum | bestanden: Laser 0,505 m, Radweg 0,496 m, seitlich 0,000 m | gefahren 0,52 m, keine Berührung |
| Tür aus der Nähe | 1,9 m vor der Tür, 25° daneben | bestanden: Rundblick 361,6°, Tür 0,79 m vermessen, 6 Etappen, 2,47 m | im Flur nach 164 s; keine Berührung; Türlinie 2 cm neben der Mitte gekreuzt; engster Abstand der gepolsterten Kontur 12 cm |
| Tür schräg | 1,8 m entfernt, Tür 36° links, am Vorpunkt 65° Drehung | bestanden: 6 Etappen, 2,61 m | im Flur nach 235 s; keine Berührung an der Tür |
| Tür quer durch den Raum | 2,9 m entfernt, zwei niedrige Mülleimer auf der Linie | **angehalten nach 0,49 m**, Meldung „Nahbereich vor dem Roboter nicht frei“ | keine Berührung, 24 cm Abstand; Tür nicht erreicht |

In keinem Lauf gab es ein Nav2-Ziel; das Fahrtor hat nichts verworfen. Die
Türläufe wurden nach dem Einbau des Nahbereichs-Halts wiederholt und kamen
wieder durch (dieselben Zahlen bis auf Zentimeter).

**Was die Simulation gezeigt hat (zwei Befunde, beide behoben):**

1. **Berührung im Kriechtempo.** Im ersten Lauf quer durch den Raum fuhr der
   Roboter mit 1,5 cm/s an einen niedrigen Mülleimer. Der Laser sieht ihn
   nicht, und der Kollisionsmonitor bremst nach Zeit bis zum Aufprall: bei
   so kleinem Tempo erst wenige Zentimeter davor. Beim Fahren über Nav2
   hält vorher der Regler an der Kostenkarte an; der direkten Etappe fehlte
   das. Daher der Nahbereichs-Halt.
2. **Abbruch mit „Odometrie veraltet“.** Die gerade Etappe liest die Uhr und
   fragt danach „anhalten?“. Rechnet diese Frage auch nur Millisekunden,
   hält die Etappe einen inzwischen eingetroffenen Odometriewert für einen
   aus der Zukunft und bricht ab. Die Nahbereichsprüfung läuft deshalb in
   einem eigenen Faden daneben. Die Stelle im vorhandenen Code ist
   unverändert und bleibt als Empfindlichkeit vermerkt.

**Beobachtung nebenbei:** Am Startplatz des schrägen Laufs kam die
gepolsterte Kontur beim Rundblick auf 3,6 cm an ein Möbel (das Gehäuse
selbst blieb über 3 cm entfernt). Das ist die bekannte Lücke des Schalters
„nur Rundblick“: Er prüft den Drehkreis nicht.

**Grenzen:**

- Die Etappenfahrt weicht nichts aus. Ist der gerade Weg nicht frei, bleibt
  Amadeus stehen und meldet es. Dort käme später Nav2 dazu.
- Strecken: je Stück höchstens 2,5 m, zusammen höchstens 4 m.
- Die Simulation hat keine Kamera, und sie hat am 19.11. das reale
  Fahrverhalten nicht gezeigt. Sie belegt die Kopplung und die Geometrie,
  nicht, dass Amadeus real so fährt.

## KI-0R – Nachrechnen an den elf Aufnahmen (Jetson, 21.11.2026, abends)

Zahlen stehen im [Archiv](archiv/20261121-ki0r-nachrechnen/).

**Erwartungen:** Zwei von fünf trafen zu (geschlossene Tür nicht angeboten;
Wandlinien werden jetzt gefunden). Nicht zugetroffen: die Tür von der
Scharnierseite (weiter 1,30 m), die Türbreiten (0,72 bis 0,78 m statt
mindestens 0,78 m bei wahren 0,85 m).

**Verschlechterung durch die eigene Änderung:** Bei `labor_tuer_vorn` stand
die Nummer auf der Türzarge. Eine 0,90 m breite Lücke 0,5 m vor der Tür
hatte die Tür verdrängt, weil seit dem Vormittag von zwei türgroßen Lücken
die nähere zählte. Die Regel stammte aus einem Gedankenfall und ist wieder
entfernt (`b3a1acf`).

**Die KI mit der geänderten Frage:** keine falsche Wahl in elf Ansichten.
Nummer auf der Schwelle: Tür gewählt, vier von vier. Nummer auf Zarge, Wand
oder Mauerwerk: „wand“ genannt und nichts gewählt, dreimal. K0-1 richtig
8 von 11 (73 %), kein Urteil; K0-6 Ausgang angeboten in 7 von 8 (88 %).

**Lehre:** Der Fehler von der Scharnierseite ließ sich im künstlichen Zimmer
mit derselben Zahl nachstellen (1,22 m) und dort beheben; an der echten Tür
änderte das nichts. Eine passende Zahl ist kein Beleg für die Ursache.

## Schalter „nur Rundblick“ (21.11.2026, Commit `6956252`)

Freigegeben vom Projektinhaber am 21.11.2026. Neues Startargument
`initial_scan_only` (Vorgabe aus) in `app_mapping.launch.py`,
`nav_mapping.launch.py` und `explore.launch.py`. Eingeschaltet dreht der
Erkunder einmal mit dem vorhandenen Rundblick (acht Abschnitte von 45°, je
mit bestätigtem Stillstand) und beendet den Auftrag, ohne ein Ziel
anzufahren. Das gilt in jedem Betrieb, auch im Selbstheilungsbetrieb, dem
Stack vom 19.11. Standardweg, Selbstheilungsweg, Profile, Fahrtor und
Kollisionsmonitor sind nicht geändert.

Geprüft in der Entwicklungsumgebung: 2285 Tests des Erkunders (18 neue),
267 in der gezielten Liste, ein Lauf des ganzen Stacks in der Simulation
(361,7° in 77 s, kein Nav2-Ziel, Mission erfolgreich). **Am Roboter
gelaufen am 21.11.2026 in KI-1:** 363,2° in 81,3 s, kein Nav2-Ziel.

## KI-0N – zweiter Durchgang an echten Aufnahmen (Jetson, 21.11.2026)

Zahlen je Ansicht stehen im [Archiv](archiv/20261121-ki0n-nachmessen/).

**Was besser wurde.** Vier der fünf vorab notierten Erwartungen trafen zu:
Die Tür aus 4–5 m hat jetzt eine Nummer; von der Seite aus der Ferne wird
sie 0,77 m breit vermessen statt 1,76 m, in der Ecke 0,72 statt 1,74 m; an
den sieben alten Aufnahmen gibt es 9 statt 12 Vorschläge, davon 2 statt 7 an
Möbeln. Eine geschlossene Tür wird nicht angeboten.

**Was nicht stimmte.**
- **Tür von der Scharnierseite** (`labor_tuer_seite_nah_b`): weiter 1,24 m
  breit, Nummer rechts neben der Tür auf der Wand. Der Prüftext zeigte den
  Grund: An diesem und den meisten anderen Türpfosten wurde keine gerade
  Wand erkannt; die Regeln für Türblatt und schräge Türen griffen deshalb
  nicht.
- **Flur:** Angeboten wurde eine 0,98 m breite „Öffnung“ in 0,56 m, die
  laut Christopher die Wand zwischen zwei Türen ist. Die beiden Türen hatten
  keine Nummer. Die KI wählte die Nummer als „Durchgang in die Küche“.
- **Halb geschlossene Tür:** Die Nummer stand auf dem Mauerwerk neben der
  Tür. Die KI wählte nichts.
- Türen von vorn werden 0,71 bis 0,77 m breit vermessen bei wahren 0,85 m.

**Was die KI tat.** Tür mit Nummer im Foto: sechs von sechs gewählt. Kein
Ausgang angeboten: dreimal richtig nichts gewählt, einmal falsch (Flur).
Ausgang nur in der Skizze: nichts gewählt. Raumname in 1 von 11 richtig.
K0-1 richtig 9 von 11 (82 %), K0-6 Ausgang angeboten in 7 von 8 (88 %);
beides ohne Urteil oder unter der Schwelle.

**Vorfall.** Zum Hinstellen wollte Christopher das Kamerabild sehen; im
Auftrag gab es dafür nichts. Der Agent schrieb ein eigenes Anzeigeprogramm.
Dessen Vollbild ließ sich nicht schließen, **Christopher musste den Jetson
herunterfahren**; Kamera und LiDAR endeten ohne SIGINT. Daten gingen nicht
verloren. Der Fehler lag im Auftrag: Er hätte das Live-Bild vorsehen müssen.
Folgen: Es gibt jetzt den Sucher (gewöhnliches Browserfenster, speichert
nichts, endet von selbst), und die Aufträge verbieten eigene
Anzeigeprogramme.

## Nachbesserung nach KI-0N (21.11.2026, Commit `70b0a5d`)

| Befund | Ursache | Änderung |
|---|---|---|
| Tür von der Scharnierseite 1,24 m, „keine Wandlinie“; Türen von vorn 10 cm zu schmal | Die Scans wurden über ein Raster mit 4 cm Zellen gelegt. Mit dem Rauschen des echten LiDAR (nachgestellt mit 2 cm und 2160 Strahlen) verschiebt das jeden Wandpunkt um einige Zentimeter; gerade Wände gelten dann als krumm. Das künstliche Zimmer ergab so denselben Fehler: 1,22 m, Mitte 0,4 m vor der Tür | Im Stand wird nicht mehr gerastert: je Richtung der Median aller Messungen. Im künstlichen Zimmer mit 1 bis 3 cm Rauschen: Tür 0,80 bis 0,82 m (wahr 0,80), mit Türblatt von vier Standpunkten 0,80 bis 0,82 m |
| Warum keine Wandlinie entstand, stand nicht im Prüftext | fehlte | Der Prüftext nennt den Grund mit Maß |
| Flur: KI wählt eine Nummer auf einer Wand | Die Nummer stand am unteren Bildrand (Öffnung näher als das Bild reicht); die KI nahm den Durchgang, den sie im Foto sah. „Wand“ konnte sie nicht sagen | Neue Einordnung „wand“; Nummern am unteren Bildrand werden erklärt |
| KI ordnet Nummern ein, die in keinem Foto stehen | Im Stand gibt es nur ein Foto | Wählbar sind nur Nummern, die in einem Foto stehen; die anderen gelten als nicht beurteilbar |
| Jede Änderung der Vermessung verlangte neue Angaben von Christopher | Die Angaben hingen an Nummern | Sie gelten jetzt für die Lage; die Auswertung überträgt sie und meldet, was neu zu beurteilen ist |

**Nicht geklärt:** warum im Flur die beiden Türen keine Nummer bekamen und
was die „Öffnung“ dort war. KI-0R liefert dazu den vollen Prüftext.
**Bekannte Grenzen:** Nach einer Drehung wird weiter gerastert; dort ist mit
denselben Schwächen zu rechnen, bis auch das geändert ist. Ein Türblatt, das
genau von der Kante gesehen wird, ist nicht zu verfolgen; die Tür wird dann
bis zu 15 cm zu breit vermessen.

## Frühere Durchgänge

**KI-0 Teil B (21.11.2026, vormittags):** erster echter Lauf, sieben
Standbilder; Kette läuft, Antwort in 1,5 bis 4 s, Tür mit Nummer im Foto vier
von vier gewählt; Vermessung von der Seite 1,22 und 1,76 m, Tür aus 4–5 m
ohne Nummer. Mit Denken langsamer und einmal ohne brauchbare Antwort:
**Denken bleibt aus.** Kamera liefert 320 × 180. Einzelheiten im
[Archiv](archiv/20261121-ki0-erstes-sehen/).

**Nachbesserung nach Teil B (Commit `5319b7f`):**

Im künstlichen Zimmer nachgestellt, dann geändert:

| Befund | Ursache im Nachstellen | Änderung |
|---|---|---|
| Tür von der Seite 1,22 m breit, Nummer daneben | Von der Scharnierseite endet die sichtbare Lücke an der Spitze des offenen Türblatts. Rechnerisch bei 85 cm und 90°: 1,20 m | Das Blatt wird bis zur Wand verfolgt; zweiter Pfosten ist das Scharnier. Die Nummer steht auf dem sichtbaren Stück der Schwelle. Ist das Blatt nicht zu verfolgen, zählt das Lot seiner Spitze auf die Wand |
| Tür in 4–5 m nicht angeboten | Kanten innerhalb einer gefundenen Lücke wurden übersprungen; die Tür lag hinter einer breiten Möbellücke | Hinter breiten Lücken wird weitergesucht; türgroß geht vor breit |
| (beim Nachstellen gefunden) Tür durch eine Tür gesehen: die fernere gewinnt | Von einer Kante aus zählte die erste zulässige Lücke | Es zählt die schmalste zulässige |
| Viele Vorschläge seitlich und hinten | Im Stand wurde von der Antriebsmitte aus gerechnet, das LiDAR sitzt 24,5 cm weiter vorn. Hinter jeder nahen Kante lag ein nie gesehener Keil, der als frei galt | Im Stand wird vom Ort des LiDAR aus vermessen |
| Wahl einer Möbellücke fehlte in K0-1; K0-2 „bestanden“ ohne Glas | Zählweise der Auswertung | K0-1 zählt alle Ansichten; K0-2 urteilt nur mit Glas oder Spiegel unter den Vorschlägen; K0-5 vergleicht getrennte Aufnahmen |

Neu sind `vermessung_pruefen.py` (nennt je Aufnahme angebotene und
verworfene Lücken mit Grund; nur Maße, keine Bilder oder Scans) und
`wahrheit_eintragen.py`.

Die 1,76 m (`labor_tuer_weit_seite`) und die 1,74 m (`labor_ecke`) waren
nicht nachgestellt; in KI-0N wurden beide Türen richtig angeboten (0,77 und
0,72 m).
**Bekannte Grenze:** Ein Türblatt, das genau von der Kante gesehen wird,
ist nicht zu verfolgen; die Tür wird dann bis zu 15 cm zu breit vermessen.
Steht das Blatt weniger als 90° offen und sieht man es von der Türseite,
wird die volle Türbreite gemeldet, nicht die engere lichte Breite.

## Klarstellungen des Projektinhabers (19.11.2026, abends)

1. **Kein Joystick.** Amadeus dreht sich für die Blickrunde selbst.
2. **Der KI-Rechner wird nur eingeschaltet;** die Verbindung baut sich von
   selbst auf, wie bei der Objekterkennung. Sie läuft über ROS 2 DDS im
   WLAN (auch im August, Christopher am 19.11.); rosbridge verbindet nur
   die App mit dem Roboter.

Dazu sein Konzept „HomeMy“ als Quelle ([quellen/](quellen/)); ausgewertet in
KONZEPT §13.

## Was gebaut ist

| Baustein | Aufgabe |
|---|---|
| `lotse/geometrie.py` | Montage von Kamera und LiDAR, Projektion ins Bild |
| `lotse/blickrunde.py` | Aufnahmeformat; Drehwinkel aus den Scans; Auswahl der acht Bilder; Profil des Standpunkts (im Stand der Median der Messungen vom Ort des LiDAR aus, nach einer Drehung über ein Raster); Ruhe des Echos je Richtung |
| `lotse/kandidaten.py` | Öffnungen vermessen (Breite, Lage, freie Tiefe), auch mit offenem Türblatt; Protokoll jeder geprüften Lücke mit Grund |
| `lotse/markierung.py` | Nummern ins Foto, Kartenskizze, Übersichtsblatt |
| `lotse/frage.py`, `lotse/antwort.py` | Frage an die KI (ganze Runde, Teilrunde, Einzelbild); Prüfung der Antwort |
| `lotse/ki_rechner.py` | Verbindung zu Ollama ohne Proxy; Denkschalter; Fassung und Kennung des Modells |
| `lotse/botschaft.py` | Frage und Antwort für die Übertragung packen und begrenzen |
| `lotse/auswertung.py`, `lotse/ablauf.py` | Kennzahlen K0-1 bis K0-6 mit Median und 95-%-Wert, Vergleich getrennter Aufnahmen, Übertragung der Angaben des Menschen nach Lage; Ablauf einer Runde |
| `werkzeuge/lotse_dienst.py` | KI-Rechner: nimmt Fragen über ROS an, fragt Ollama lokal, eine Frage zur Zeit; legt mit `--zustand` seinen Zustand und die letzte Frage für das Fenster ab |
| `werkzeuge/ki_verbindung_ros.py` | Roboter: stellt die Frage über ROS; keine Antwort ist ein Ergebnis, kein Fehler |
| `werkzeuge/lotse_fenster.py`, `lotse_fenster_seite.html` | KI-Rechner: Programm für den Bildschirm. Startet den Lotsen-Dienst und zeigt KI-Programm, Dienst, Roboter im Netz, die letzten Fragen mit Bildern und Antwort und das Log. Nur von diesem Rechner aus erreichbar |
| `werkzeuge/blickrunde_aufnehmen.py`, `trockenlauf.py`, `trockenlauf_auswerten.py`, `beispielrunde_erzeugen.py` | Aufnahme, Trockenlauf (direkt oder `--ueber-ros`), Auswertung, künstliche Beispielrunde (auf Wunsch mit Türblatt) |
| `werkzeuge/vermessung_pruefen.py`, `wahrheit_eintragen.py` | Prüftext der Vermessung zu gespeicherten Aufnahmen; Angaben des Menschen mit Lage der Nummern eintragen |
| `lotse/fahrziel.py`, `werkzeuge/fahrziel_senden.py` | Roboter: aus der gewählten, neu vermessenen Öffnung das Fahrziel für die Etappenfahrt (Anfahrt, Durchfahrt, in einem Ablauf); mit `--wahl` die Öffnung, die die KI gewählt hat; mit `--ende` keine Fahrt |
| `lotse/wahl.py`, `werkzeuge/ki_tuer_waehlen.py` | Roboter, nach dem Rundblick: die KI fragen und die geprüfte Wahl mit dem Ort der Öffnung in der Karte in eine Wahl-Datei schreiben (bleibt auf dem Roboter); fährt nicht |
| `werkzeuge/sucher.py` | Jetson: das Kamerabild live in einem gewöhnlichen Browserfenster, zum Hinstellen für eine Ansicht. Liest nur mit, speichert nichts, endet von selbst |

## Nachweise

| Datum | Was | Wo geprüft | Ergebnis |
|---|---|---|---|
| 19.11.2026 | Ordner, Konzept, Verankerung | Repository | angelegt (`907a2b0`) |
| 19.11.2026 | Werkzeuge für den Trockenlauf | Entwicklungsumgebung | `cb75e55` |
| 19.11.2026 | Tests dieser Linie | Python 3.13, numpy 2.5, Pillow 12.3, ohne ROS | 149 bestanden, 2 übersprungen (die ROS-Tests) |
| 19.11.2026 | Tests dieser Linie | Python 3.12, numpy 1.26, Pillow 10.2, ROS 2 Jazzy, abgeschottet | 157 bestanden; darunter Aufnahme über echte ROS-Themen und die Strecke Roboter → Lotsen-Dienst → gespieltes Ollama (Antwort, „beschäftigt“, Zeitgrenze, unbrauchbare Frage, fehlender Dienst) |
| 19.11.2026 | Quelltext auf Python 3.10 lesbar | Syntaxprüfung aller Python-Dateien | bestanden |
| 19.11.2026 | Hauptlinie unberührt | 249 gezielte Tests aus dem SH-9-Auftrag; `git diff` außerhalb dieses Ordners | 249 bestanden; keine bestehende Datei geändert außer den Verweisen |
| 19.11.2026 | KI-0 Teil A bis A5 | KI-Rechner, echtes Ollama | Tests 157 bestanden (mit abgeschaltetem Plugin); `qwen3.5:9b` antwortet gültig nach Schema, wählt im Beispielzimmer dreimal die Glastür; mit Denken keine Antwort in 60 s; Lotsen-Dienst wegen fehlender Netzverbindung nicht gestartet |
| 19.11.2026 | Werkzeuge nach Teil A korrigiert | Entwicklungsumgebung | kein stiller Ersatzversuch mehr, Fehlertext des Dienstes, Ausgabe mit Einordnung und Raum; Tests 150 bestanden, 2 übersprungen (ohne ROS) und 158 bestanden (mit ROS) |
| 19.11.2026 | Angaben des HomeMy-Konzepts | Ollama-Bibliothek, arXiv | `qwen3.5:9b` und `qwen3-vl:8b` vorhanden, beide mit Bildeingabe; Mobility VLA setzt eine vorab aufgenommene Führung voraus; LocalNav: 26 % / 37 % / 42 % Erfolg (lokal ohne und mit Nachtraining, Cloud) |
| 21.11.2026 | KI-0 Teil B | Jetson, Kamera, LiDAR, KI-Rechner über WLAN | 158 Tests bestanden; sieben Standbilder, 14 Fragen beantwortet; Tür von vorn richtig vermessen und gewählt, von der Seite zu breit, aus 4–5 m nicht angeboten; Einzelheiten im Archiv |
| 21.11.2026 | Vermessung und Auswertung nachgebessert, zwei Werkzeuge neu | Entwicklungsumgebung | `5319b7f`; 170 Tests bestanden, 2 übersprungen (ohne ROS); 178 bestanden (ROS 2 Jazzy, abgeschottet); Syntax für Python 3.10 geprüft |
| 21.11.2026 | Lotsen-Fenster und Zustandsablage des Dienstes | Entwicklungsumgebung | 178 Tests bestanden, 2 übersprungen (ohne ROS); 187 bestanden (ROS 2 Jazzy, abgeschottet); Strecke Trockenlauf → Dienst → gespieltes Ollama → Anzeige einmal ganz durchlaufen |
| 21.11.2026 | Befunde nachgestellt | künstliches Zimmer mit Türblatt | 0,80-m-Tür mit Blatt bei 90° von der Scharnierseite: vorher 1,14 m breit und 0,4 m vor der Tür (bei tieferem Flur; sonst gar nicht angeboten), jetzt 0,79 bis 0,84 m an der Tür. Blatt bei 75°, 90°, 100° und 110° von vier Standpunkten (16 Fälle): in 15 Fällen Tür 0,73 bis 0,89 m an der Tür, in einem Fall nicht angeboten (75°, von der Öffnung waren 6 cm zu sehen). Bei 100° und 110° erscheint in vier Fällen zusätzlich die Tasche zwischen Blatt und Schrank als eigene Öffnung. Tür hinter einer breiten Möbellücke: vorher nicht angeboten, jetzt 0,71 und 0,72 m |
| 21.11.2026 | KI-0N | Jetson, vier neue Ansichten mit Kamera und LiDAR, KI-Rechner über WLAN | 187 Tests bestanden; elf Standbilder; vier von fünf Erwartungen erfüllt; Tür mit Nummer im Foto sechs von sechs gewählt; Tür von der Scharnierseite weiter 1,24 m; im Flur eine Wand als Öffnung; Einzelheiten im Archiv |
| 21.11.2026 | Nachbesserung nach KI-0N, Sucher | Entwicklungsumgebung | `70b0a5d`; 192 Tests bestanden, 2 übersprungen (ohne ROS); 202 bestanden (ROS 2 Jazzy, abgeschottet); Fehler mit echtem Rauschen nachgestellt (Raster 1,22 m, Median 0,81 m) |
| 21.11.2026 | Vorhandener Rundblick der Hauptlinie | Code und Dokumente gelesen | 8 × 45° bei 0,08 rad/s mit Pause steht in `explore_params.yaml`; im Selbstheilungsbetrieb ersetzt `nav_mapping.launch.py` jedes eigene Profil; „nur Rundblick“ gibt es nicht; nichts gebaut |
| 21.11.2026 | KI-0R | Jetson, elf gespeicherte Aufnahmen, KI-Rechner über WLAN | 205 Tests bestanden; zwei von fünf Erwartungen erfüllt; eine Verschlechterung gefunden und behoben (`b3a1acf`); keine falsche Wahl der KI; Einzelheiten im Archiv |
| 21.11.2026 | Schalter „nur Rundblick“ | Entwicklungsumgebung, Simulation des ganzen Stacks | `6956252`; 2285 Tests des Erkunders, 267 gezielt; in der Simulation 361,7° in 77 s ohne Nav2-Ziel |
| 21.11.2026 | Tests dieser Linie nach KI-0R | Entwicklungsumgebung | 196 bestanden, 2 übersprungen (ohne ROS); 206 bestanden (ROS 2 Jazzy, abgeschottet) |
| 21.11.2026 | Bestand Türdurchfahrt | Historie, Branch `codex/hwt601-encoder-shadow`, Dokumente; Funktionsvergleich `1d91229` gegen heute | vier belegte Durchfahrten (18.08., 11.09. zweimal, 08.11.); Türablauf im heutigen Erkunder zeilengleich; gerade Etappe 0,50 m am 11.09. real bestanden |
| 21.11.2026 | Etappenfahrt, Tests | Entwicklungsumgebung | 2363 Tests des Erkunders (78 neue), 267 in der gezielten Liste von KI-1 unverändert; KI-Linie 216 bestanden, 2 übersprungen (ohne ROS), 226 (mit ROS) |
| 21.11.2026 | Etappenfahrt, Simulation | ganzer Stack, Labor mit Tür und Flur | gerade Etappe 0,5 m bestanden; zwei Türdurchfahrten bestanden (ohne Berührung, kein Nav2-Ziel); quer durch den Raum vor niedrigen Mülleimern angehalten; zwei Befunde gefunden und behoben |
| 21.11.2026 | Rundblick nach der Änderung am Erkunder | Simulation | unverändert: 361,7° in 77 s, kein Nav2-Ziel |
| 21.11.2026 | **KI-1** | Jetson, Laborraum, mit Christopher; KI-Rechner über WLAN | Release `ki1-20261121_2043` auf `a0ad82b`; 267 und 206 Tests bestanden; R1 bis R6 erfüllt: 363,2° in 81,3 s ohne Nav2-Ziel, 286 Paare, Antwort der KI in 4,87 s, richtige Tür gewählt; ein scharfer Start vorher an gesperrten Motoren abgebrochen |
| 21.11.2026 | Tests dieser Linie nach KI-1 | Entwicklungsumgebung | 218 bestanden, 2 übersprungen (ohne ROS); 228 bestanden (ROS 2 Jazzy, abgeschottet); gezielte Liste für KI-F1 345 bestanden |
| 22.11.2026 | **KI-F1** | Jetson, Laborraum, mit Christopher | Release `kif1-20261122_1515` auf `baa16b7`; 345 und 228 Tests bestanden; gerade Etappe 0,5 m: F1-1 bis F1-6 erfüllt (Laser 0,505 m, seitlich 0,000 m, 12,8 s); Tür nicht gefahren, weil 1,25 m breit vermessen |
| 22.11.2026 | Türblatt nachgestellt | Simulation, Labor mit 90° offenem Blatt | 0,6 m seitlich: Tür 0,84 m über die Blatt-Regel, daneben die Lücke Blattspitze–Pfosten 1,20 m verworfen, Werkzeug meldet „61 cm nach rechts versetzen“; von vorn: Durchfahrt neben dem Blatt gelungen |
| 22.11.2026 | Tests dieser Linie nach KI-F1 | Entwicklungsumgebung | 223 bestanden, 2 übersprungen (ohne ROS); 233 bestanden (ROS 2 Jazzy, abgeschottet) |
| 22.11.2026 | **KI-F2** | Jetson, Laborraum, mit Christopher | kein Build; 233 Tests bestanden; Aufstellung beim ersten Messen passend (0,77 m); Ausrichten 9,4° mit 0,8° Rest; Fahrt nach 0,345 m am Nahbereichs-Halt angehalten, nichts berührt; T-2 und T-4 nicht erfüllt |
| 22.11.2026 | Weg von KI-F2 nachgerechnet und nachgestellt | Maße des Berichts; Simulation mit 85° offenem Blatt | alte Linie 0,245 m neben der Blattspitze, Ecke am Wendepunkt 1,6 cm davor; gerade Linie 0,386 m; Simulation alter Weg: bis 4,7 cm an die Spitze; neuer Weg: im Flur nach 51 s; von der Blattseite: Werkzeug lehnt ab |
| 22.11.2026 | Tests dieser Linie nach KI-F2 | Entwicklungsumgebung | 232 bestanden, 2 übersprungen (ohne ROS); 242 bestanden (ROS 2 Jazzy, abgeschottet) |
| 22.11.2026 | Anfahrt und Durchfahrt als zwei Missionen in einem Stacklauf | Simulation, Laborraum mit 85° offenem Blatt, vier Startplätze | drei Plätze: selbst vor die Tür (0,01 bis 0,09 m neben der Mitte), dann im Flur nach 103 bis 114 s, keine Berührung (engste Stelle 6,1 bis 8,4 cm); Blattseite: abgelehnt (Tür 1,33 m vermessen); zweiter Missionsstart ohne Neustart ging jedes Mal |
| 22.11.2026 | Türachse aus den Türkanten gegen Türachse aus der Wand | Simulation, Start rechts schräg | Kanten: 6° verdreht, nach der Anfahrt 0,17 m neben der Mitte, Durchfahrt abgelehnt; Wand: 0,01 m, Durchfahrt gelungen |
| 22.11.2026 | Tests dieser Linie mit der Anfahrt | Entwicklungsumgebung | 243 bestanden, 2 übersprungen (ohne ROS); 253 bestanden (ROS 2 Jazzy, abgeschottet) |
| 22.11.2026 | **KI-F3, erster Anlauf** | Jetson, Laborraum, mit Christopher | kein Build; 253 Tests bestanden; T-1 erfüllt (0,77 m, frei 0,38 / 0,39 m, beim ersten Messen); Vorprüfung im scharfen Stack nicht bestanden (Encoder-Zeitwache `fault_latched`, `encoder_timing_continuity_unproven`); keine Mission, keine Bewegung; Stufe 2 nicht gelaufen |
| 22.11.2026 | Werkzeug zum Zustand des Radsensors | Entwicklungsumgebung | 3 Tests; KI-Linie 246 bestanden, 2 übersprungen (ohne ROS); 256 bestanden (ROS 2 Jazzy, abgeschottet) |
| 22.11.2026 | **KI-F3b** | Jetson, Laborraum, mit Christopher | kein Build; 256 Tests bestanden; T-1 erfüllt; Vorprüfung bestanden; drei Etappen 1,03 m (seitlich ≤ 5 mm, ≤ 0,3°); Halt am Nahbereich 0,26 m vor der Türlinie, Stelle 0,25 m vor der Vorderkante, 0,09 m links; nichts berührt; T-2 und T-4 nicht erfüllt |
| 22.11.2026 | Halt von KI-F3b nachgestellt | Simulation, 20 cm hoher Gegenstand an der Stelle | Halt nach 0,96 m, Stelle 0,25 m / 0,12 m links; Herkunft „Nahsensor links und rechts, 13 bis 20 cm“, Karte frei |
| 22.11.2026 | Messung an der Haltestelle im Stand | Simulation, mit und ohne Gegenstand | mit: Quelle beide Nahsensoren, 14 bis 20 cm, Laser nichts; ohne: Kostenkarte frei, keine Punkte |
| 22.11.2026 | Ganze Fahrten mit der Prüfung der Kostenkarte auf dem ganzen Weg | Simulation, 85° offenes Blatt | von vorn (Aufstellung KI-F3b): „Kostenkarte passt“, im Flur nach 53 s, keine Berührung, engste Stelle 11 cm; Anfahrt von rechts schräg und Durchfahrt: beide Wege „Kostenkarte passt“, im Flur nach 117 s, keine Berührung, 7,1 cm; keine falsche Ablehnung |
| 22.11.2026 | Tests dieser Linie mit Herkunftsprüfung | Entwicklungsumgebung | 254 bestanden, 2 übersprungen (ohne ROS); 264 bestanden (ROS 2 Jazzy, abgeschottet) |
| 22.11.2026 | Laborschalter ohne Nahsensoren | Entwicklungsumgebung (ROS 2 Jazzy) | Fahrtor und Startdateien: 55 Tests der betroffenen Dateien, Paket `robot_navigation` mit Erkunderprüfungen 254 bestanden; neu: ohne Schalter ohne VL53 keine Freigabe, mit Schalter nur Dreh- und Direktkanal, Nav2 und Raumfahrt gesperrt |
| 22.11.2026 | Fahrten ohne Nahsensoren | Simulation | siehe Abschnitt „Laborprobe ohne Nahsensoren“: Durchfahrt gelungen; gegen einen 20 cm hohen Gegenstand ungebremst gefahren |
| 23.11.2026 | **KI-F5** | Jetson, Laborraum, mit Christopher | Build `kif5-20261123_0950`, Tests 350 und 264; ohne Nahsensoren im Stand wie vorgesehen; fünf Messungen „Aufstellung passt nicht“ (0,30 bis 0,33 m) bei mittig stehendem Roboter, Ursache das Werkzeug; keine Fahrt |
| 23.11.2026 | Türachse aus der Wand, `--zur-tuer` | Entwicklungsumgebung, Simulation | Test mit den Zahlen aus KI-F5 (Kanten: 0,296 m, 7,3°; Wand: mittig); KI-Linie 258 bestanden, 2 übersprungen; 268 mit ROS; Simulation siehe Abschnitt KI-F5 |

**Gemessen an der künstlichen Beispielwelt** (ausgedachtes Zimmer mit
80-cm-Tür, 90-cm-Glastür zum Balkon, Schränken, Kiste; LiDAR-Rauschen 1 cm):

- Drehwinkel aus den Scans: Fehler höchstens 0,5° über eine volle Drehung
  (vier Standpunkte), in beiden Drehrichtungen, auch bei Schritten von 12°
  und mit einer um 15 % falschen Odometrie als Startwert. Die Tests
  verlangen unter 1°.
- Von drei Standpunkten werden genau Tür und Glastür als Öffnung vermessen,
  die 50 cm tiefe Schranknische nicht. Breiten: Tür 0,73–0,77 m (wahr 0,80),
  Glastür 0,84–0,88 m (wahr 0,90). Die Vermessung misst also 3–7 cm zu
  schmal.
- Von einem vierten Standpunkt 0,7 m vor der Wand mit der Glastür wird die
  Glastür nicht angeboten (Blick zu flach), dafür eine 2,2 m breite Bucht
  zwischen Kiste und Schrank.
- Im Stand, mit Blick zur Tür (ein Bild statt acht): Die Tür wird vermessen
  und im Foto markiert; die Frage sagt, dass nicht gedreht wurde.
- Die Nummern stehen in den Beispielbildern an der Türschwelle (angesehen),
  bei naher Öffnung am unteren Bildrand.
- Diese Werte stammen aus Runden mit Drehung und sind vom Stand 19.11.;
  nach der Nachbesserung vom 21.11. gelten sie weiter (die Tests dazu
  laufen unverändert).
- Im Stand dicht am Schrank: Von der Antriebsmitte aus gerechnet erscheint
  die 50 cm tiefe Schranknische als Öffnung, vom Ort des LiDAR aus nicht.

## Lotsen-Fenster (21.11.2026)

Geprüft in der Entwicklungsumgebung mit ROS 2 Jazzy, gespieltem Ollama und
dem künstlichen Zimmer: Programm starten, Dienst startet mit; eine Frage vom
Trockenlauf über ROS erscheint mit ihren neun Bildern, Wahl, Einordnung,
Raum und Dauer; Anhalten, Starten und Beenden über die Seite; ein außerhalb
gestarteter Dienst wird erkannt und kein zweiter gestartet; die Seite
antwortet nur dem eigenen Rechner, Schalter nur der eigenen Seite. Die
Anzeige wurde im Browser angesehen (hell, dunkel, schmal), ohne Fehler in
der Konsole.

Nicht geprüft: der Start über das Desktop-Symbol in der Pixi-Umgebung des
KI-Rechners, die Anzeige „Roboter im WLAN erreichbar“ gegen den echten
Jetson, echte Bilder.

## Was nicht geprüft ist

- **Die Etappenfahrt am Roboter durch eine Tür.** Am Roboter gelaufen sind
  die gerade Etappe (KI-F1), ein Ausrichten um 9,4° (KI-F2) und ein Halt am
  Nahbereich (KI-F2). Offen: die Fahrt an Türblatt und Pfosten vorbei; ob
  der Nahbereichs-Halt dort bei 13 cm Abstand zum Streifen ruhig bleibt;
  wie sich der Kollisionsmonitor dort verhält; ein Nachstellen der Richtung
  kurz vor oder in der Tür (in der Simulation einmal 5,6° in der Tür, dabei
  9,6 cm Abstand der gepolsterten Kontur zum Pfosten).
- **Die Prüfung des Freiraums und die Zeile zur Kostenkarte** an echten
  Messungen.
- **Was in KI-F3b vor der Tür stand:** Nach Christophers „ja“ (KI-F4, M1)
  lag dort etwas; an der Haltestelle sah der rechte Nahsensor etwas in 10
  bis 52 cm Höhe. Was es war, ist nicht festgestellt.
- **Die Selbstausrichtung am Roboter** (`--zur-tuer`, Achse aus der Wand,
  zwei Missionen in einem Stacklauf): bisher nur in Tests und Simulation.
- **Der Laborschalter am Roboter:** ob der Kollisionsmonitor der
  Humble-Version das Abschalten einzelner Quellen kennt (ohne VL53-Daten
  sieht er so oder so nichts), und ob das Fahrtor ohne VL53 wie in der
  Simulation nur die beiden Kanäle des Erkunders freigibt.
- **Die Herkunftsprüfung des Werkzeugs am Roboter:** Lesen der echten
  Nahsensor-Wolken, der Karte und der Höhenangaben; bisher nur in der
  Simulation und mit Tests.
- **Warum sich der Radsensor beim Hochfahren sperrt:** Größe und Zeitpunkt
  der Lücke sind am 22.11. nicht gemessen; das Werkzeug dafür kommt mit
  KI-F3b zum ersten Mal zum Einsatz. Ob ein Neustart verlässlich hilft, ist
  nur aus SH-4 (einmal) belegt.
- **Die Anfahrt am Roboter:** Drehen um große Winkel in der Etappenfahrt
  (am Roboter bisher 9,4°), die Türachse aus der Wand an echten Messungen
  (Türzarge, Möbel an der Wand), zwei Missionen in einem Stacklauf, und wie
  genau Amadeus danach vor der Tür steht. In der Simulation bleibt am
  Türblatt wenig Luft (0,32 m bei nötigen 0,30 m).
- **Die Wahl der KI am Roboter** (KI-F9): ob die Lage am Ende des
  Rundblicks (SLAM) und der Drehwinkel aus den Scans am Roboter so gut
  zusammenpassen wie in der Simulation (dort 5 bis 7 cm), wie lange das
  Aufbereiten der Runde auf dem Jetson neben dem Stack dauert, und ob die
  KI aus der echten Runde die Labortür wählt. Die Fälle falsch, langsam,
  stumm, Unsinn und „kein Ausgang“ sind für die Frage mit einer gespielten
  KI getestet; in der Simulation lief die ganze Kette mit einer gespielten
  KI, die die Welt kennt (sie prüft die Kopplung, nicht das Sehen).
- **Die Blickrunde in anderen Lagen:** Bisher eine Runde von einem Platz im
  Labor. Andere Standorte, der Flur und Räume mit Glas oder Spiegel fehlen.
- **Kamera neben dem Stack während einer Fahrt.** Gemessen ist sie im Stand
  und in der Drehung.
- **Der Stand nach `b3a1acf` an den echten Aufnahmen** (die zurückgenommene
  Regel).
- **Glas, Spiegel, anderes Zimmer; `qwen3-vl:8b`; Personen** in Scan und
  Bild (in KI-1 war Christopher auf einem Foto und bekam keine Nummer; ein
  einzelner Befund).
- **Der Sucher** auf dem Jetson.

## Genau ein nächster Schritt

Auftrag KI-F9 übergeben und am Roboter ausführen lassen (die KI wählt die
Tür, Christopher sagt vor jeder Fahrt ja oder nein), danach den Bericht
auswerten.
