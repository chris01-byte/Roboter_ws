# Bewertung: Wie kommt Amadeus selbst durch die Tür? (23.11.2026)

Anlass: Christopher nach KI-F5: „So kommen wir nicht weiter. Der Roboter hat
es ja schon 3-mal geschafft, im Laufe seiner Bauphase eine Tür zu
durchqueren. Jetzt schafft er gar nichts und ich muss ihn ständig neu auf
einen Zentimeter genau vor der Tür ausrichten. […] Ich glaube, ohne NAV2
schafft er das nicht. Bitte überdenke unser Konzept, evaluiere und schaue,
welche Möglichkeiten wir jetzt haben.“

Diese Bewertung ist **keine Entscheidung**. Sie hält Rückblick, Möglichkeiten
und Empfehlung fest; was der Projektinhaber entscheidet, kommt in den
[STATUS](STATUS.md) und, wenn es den Rahmen ändert, in den
[Masterplan](../docs/wohnungserkundung/MASTERPLAN.md) §10.

Vorgehen: sechs unabhängige Leser (gelungene Nav2-Durchfahrten, Nav2-Rückschritt
seit Mitte November, alle KI-F-Fahrten, Nav2 im heutigen Code, Technik der
Etappenfahrt, öffentliche Quellen), daraus sechs Lösungswege, jeder von zwei
skeptischen Prüfern (Machbarkeit, Betrieb) gegen Code und Unterlagen geprüft,
dazu eine Vollständigkeitskritik. Die tragenden Aussagen unten sind zusätzlich
von Hand nachgeprüft. Nur gelesen, nichts gefahren.

## 1. Rückblick

**Was real funktioniert hat:**
- Die Türwahl der KI (KI-1, 21.11.: richtige Tür in 4,9 s).
- Die Fahrbausteine der Etappenfahrt: 0,505 m geradeaus ohne Seitenfehler
  (KI-F1), Ausrichten um 9,4° mit 0,8° Rest (KI-F2), drei Etappen über
  1,03 m mit höchstens 5 mm und 0,3° Abweichung (KI-F3b).
- Früher, alle über **Nav2**: 18.08. (erster Raumwechsel), 11.09. (zwei
  Durchfahrten), 08.11. (SH-7, zwei von drei Fahrten durch die Labortür).
  Von Hand zentriert wurde dabei nie: Am 11.09. reichte „Tür im vorderen
  ±20°-Sektor; manuelles Zentrieren oder paralleles Ausrichten ist nicht Teil
  der Voraussetzung“ (`origin/codex/hwt601-encoder-shadow:tools/kartierung/README.md:171-176`),
  am 08.11. ein Start irgendwo im Raum.

**Was nicht funktioniert hat:** In fünf Aufträgen (KI-F1 bis KI-F5, 22./23.11.,
zusammen etwa 156 Minuten) kam Amadeus nie durch die Tür; am nächsten war er
0,26 m vor der Türlinie (KI-F3b).

**Warum – kein Fehlschlag lag an der Fahrgenauigkeit:**

| Auftrag | Ursache | Klasse |
|---|---|---|
| KI-F1 | Tür aus der schrägen Lage 1,25 m breit vermessen, nicht gefahren | Werkzeug der KI-Linie |
| KI-F2 | Weg an die Spitze des Türblatts geplant, Nahbereichs-Halt nach 0,35 m | Werkzeug der KI-Linie (Halt richtig) |
| KI-F3 | Radsensor beim Start gesperrt | Hardware |
| KI-F3b | Halt 0,26 m vor der Türlinie; am Boden lag etwas, rechter Nahsensor sah es in 10 bis 52 cm Höhe | Schutzkette, wahrscheinlich zu Recht |
| KI-F5 | Türachse aus zwei Kantenpunkten, eine Kante 7 cm zu nah → „30 cm versetzen“, obwohl mittig | Werkzeug der KI-Linie |

**Fehler unserer Planung (KI-Linie):**
1. Die Etappenfahrt misst die Tür einmal im Stand und fährt dann feste
   Punkte ab, ohne nachzumessen. Am 21.11. war „zwischen den Etappen neu
   vermessen“ beschlossen (STATUS, Abschnitt „Fahrteil: was es schon gibt“);
   gebaut wurde das nicht.
2. Das Vorpositionieren von Hand kam aus der Auftragslogik, nicht aus der
   Physik: Stufe 1 „von vorn“ war Pflicht, die Selbst-Anfahrt (gebaut am
   22.11.) hing daran und lief real nie.
3. Die Ausgangsannahme vom 21.11. war zu optimistisch: Die „am 10./11.09.
   bestandenen Bausteine ohne Nav2“ waren eine gerade Etappe in der freien
   Küche. Durch Türen fuhr Amadeus immer mit Nav2.
4. Mit `nahsensoren:=false` (22.11.) sperrt das Fahrtor jede Nav2-Fahrt
   (`src/robot_navigation/robot_navigation/cmd_vel_mission_gate.py:126-128`,
   `914-935`: die Ausnahme gilt nur für `explore_scan` und `explore_direct`).
   „Wenn es nicht reicht, binden wir Nav2 ein“ ging damit nicht mehr ohne
   neue Entscheidung.

**Ist „ohne Nav2 schafft er das nicht“ berechtigt? Zur Hälfte.**
- Ja: Alle realen Durchfahrten fuhr Nav2, ohne Zentrieren von Hand. Aus
  beliebiger Lage und um Möbel herum vor die Tür kommen kann die
  Etappenfahrt nicht; sie braucht einen geraden freien Weg.
- Aber: Nav2 schaffte auch damals nur etwa ein Drittel der Läufe (bis 08.11.
  rund 15 Läufe, 5 Durchfahrten). Seit 15./19.11. erreicht es praktisch kein
  Ziel mehr: SH-9 (19.11.) 0 von 16 Anläufen, 616× „collision ahead“, 38×
  kein Plan bei freier Lage (`docs/wohnungserkundung/STATUS.md:95-103`);
  Ursache nicht eingegrenzt. Und gerade in der Tür ist sein Planer schwach:
  Mit 0,28 m Radius bleibt der Robotermitte in einer 0,78-m-Tür ein Streifen
  von 22 cm. In W-1 (15.11.) scheiterten alle 10 Anläufe mit Ziel hinter der
  Tür: Die Robotermitte lag 14 cm neben der Türmitte, außerhalb dieses
  Streifens, und in der globalen Kostenkarte lagen zusätzlich belegte Zellen
  unklarer Herkunft (`docs/wohnungserkundung/STATUS.md:174`, `434`,
  `441-455`).
- Geometrie: Der gepolsterte Umriss braucht zum Drehen einen Kreis von
  0,41 m Radius, die halbe Tür hat 0,385 m. **In der Tür kann Amadeus sich
  nicht drehen**; ausgerichtet werden muss davor. Bei 5° Winkelfehler bleiben
  in der Tür etwa ±11 cm Spielraum, bei 10° ±8 cm, bei 20° nur ±4 cm.

**Was die Literatur macht** (öffentliche Quellen): Türlage aus einer robusten
Geradenanpassung an die Wand, nicht aus zwei Punkten (Mitterhuber u. a., ARW
2022: Fehler 0,321 aus zwei Endpunkten gegen 0,031 mit RANSAC; laufendes
Nachschätzen während der Anfahrt senkt den Lagefehler von 0,249 auf 0,065).
Dann ein Vorpunkt auf der Türsenkrechten, 0,5 bis 1,5 m davor, und die
Durchfahrt als geregelte Fahrt senkrecht durch die Tür (Burhanpurkar u. a.,
ICORR 2017: Zielreihe senkrecht durch die Türmitte, 96 von 96 realen
Versuchen). Keine Quelle fährt die Tür mit geraden Etappen ohne laufende
Rückmeldung.
- https://robotik.informatik.uni-wuerzburg.de/telematics/download/ARW2022_Door_Detection_Final.pdf
- https://arxiv.org/abs/1707.05301

**Kern:** Es fehlt weniger „Nav2 an sich“ als **Fahren mit Rückmeldung**:
grob und selbst vor die Tür kommen (das kann Nav2), dann genau und mit
frischer Messung hindurch (das können die Laser-Etappen, wenn sie
nachmessen).

## 2. Die Möglichkeiten

Note: Mittel aus zwei Prüfungen (Machbarkeit, Betrieb), 0 bis 10.

| | Weg | Wie | Voraussetzung | Hauptrisiko | Aufwand | Note |
|---|---|---|---|---|---|---|
| A | Türregelung ohne Nav2 | Erkunder bekommt die Türlage statt fester Punkte und regelt laufend auf die Türachse | Tür vom Start aus im Laser, gerader Weg frei; neue Anschlussstelle | löst ein Problem, das real nicht auftrat; größter Neubau im Sicherheitsumfeld | groß | 3,5 |
| B | **Hybrid** | Nav2 fährt zu einem Sammelpunkt vor der Tür, dann misst das Werkzeug neu und die Etappen fahren hindurch | Nav2 erreicht wieder Ziele; Nahsensoren an oder eigene Fahrtor-Änderung | Nav2 erreicht heute nichts | mittel (mit E) | 3,8 |
| C | Nav2 direkt hinter die Tür | ein Nav2-Ziel im Flur | wie B | genau der Engpass, an dem Nav2 zuletzt scheiterte | klein, ohne E sinnlos | 2,8 |
| D | Türablauf vom 11.09. mit KI-Wahl | alter Ablauf (Türhals in der Karte, Nav2-Vorpunkt, Nav2-Auslauf) | Nahsensoren an, `self_healing:=false`, Profile vom Branch | Hauptschleife nicht mehr der Stand vom 11.09.; Wiederholungen am 26./27.09. 0 von 2 | mittel bis groß | 3,3 |
| E | Nav2 wieder fahrfähig machen | Endgrund jedes SH-9-Anlaufs aus den Daten lesen, Nahsensoren im Stand messen, Vergleichsfahrt mit dem Stand vom 08.11. | Auftrag für die geparkte Hauptlinie; Nahsensoren stabil | liefert selbst keine Tür | kein Code, mehrere kurze Termine | 4,5 |
| F | **KI-F6 fahren** | grob 1,5 bis 3 m vor die Tür stellen; Werkzeug entscheidet selbst: Durchfahrt oder erst Anfahrt | nur die Übergabe; Weg geräumt | kein Nachmessen während der Fahrt; von der Türblattseite keine Anfahrt; passt die Lage, aber nicht der Weg, heißt es „keine Fahrt“ | klein, 30 bis 60 min, kein Build | 5,5 |

A bis D tragen in der jetzigen Form nicht (Prüfer: blockierende Einwände),
E und F tragen.

Weitere Ideen, **nicht geprüft:**
- **G** Nav2-Regler ohne Planer: den Weg aus der Türgeometrie als
  `FollowPath` an den Regler geben (Regulated Pure Pursuit regelt laufend
  über die SLAM-Lage). Umgeht den 22-cm-Streifen des Planers; braucht wie
  jede Nav2-Fahrt die Nahsensoren im Fahrtor.
- **H** Die Nahsensorkette reparieren statt abschalten (USB-I2C-Adapter,
  Bus, Kabel). B, C, D, E und G hängen alle an ihr.
- **I** Nav2 ohne Nahsensoren nur als eigene, getrennt geprüfte
  Sicherheitsänderung (LiDAR-Quelle im Kollisionsmonitor, fester
  Tempodeckel im Fahrtor), nie „nebenbei“.
- **J** Die Tür beim Rundblick in der Karte merken, statt sie von jedem Platz
  neu zu vermessen (hilft gegen die Türblattseite).
- **L** Eine kurze gerade Rückfahrt erlauben, damit Amadeus nach einem Halt
  selbst neu ansetzt (Sicherheitsschalter).

## 3. Empfehlung

**Zielbild: Hybrid (B).** Nav2 bringt Amadeus selbst und grob vor die Tür,
auch um Möbel herum; die Laser-Etappen fahren mit frischer Messung hindurch.
Kein einzelnes Nav2-Ziel quer durch die Tür (C).

**Vorher zu klären:**
1. Warum Nav2 seit 15./19.11. kein Ziel mehr erreicht (E).
2. Ob die Nahsensoren stabil laufen (H). Ohne sie lässt das Fahrtor Nav2 gar
   nicht fahren; die Alternative ist eine eigene Sicherheitsänderung (I).

**Ablauf bis zur ersten realen Durchfahrt** (Simulation zuerst, je Realtest
genau eine neue Verhaltensänderung):
1. KI-F6 als **letzter Versuch ohne Nav2**: Amadeus nur grob 1,8 bis 2,5 m
   vor die Tür, auf der Seite ohne Türblatt, nie auf den Zentimeter.
   Gefahren wird nur mit „Türachse aus der Wand“. Ausstieg vorab: Scheitert
   KI-F6 an Platz oder Vermessung, war es der letzte Versuch ohne Nav2.
   Erfolgschance geschätzt, nicht gemessen: 25 bis 50 %.
2. Parallel, ohne Fahrt: die gespeicherten Daten von SH-9 lesend auswerten
   (Endgrund jedes der 16 Anläufe; Vorlage SH-9N liegt im Archiv der
   Hauptlinie); die Nahsensoren 10 bis 15 min im Stand messen, mit vorher
   festgelegtem Kriterium.
3. Vergleichsfahrt mit dem unveränderten Release vom 08.11. (kurze Türfahrten
   aus grober Lage, mindestens zwei Fahrten), dann eingrenzen, bis ein Stand
   ein freies Nav2-Ziel in 1,5 bis 2,5 m Entfernung sicher erreicht.
4. Hybrid-Schalter im Erkunder bauen (Standard aus): Nav2-Ziel zu einem
   Sammelpunkt 2,0 bis 2,3 m vor der Tür, danach `--zur-tuer`. Erst
   Simulation, dann Realtest „nur Sammelpunkt“, dann Sammelpunkt plus
   Durchfahrt.

Ehrlich: Über den Nav2-Weg sind das geschätzt 8 bis 12 Termine (nicht
gemessen).

## 4. Was wir nicht mehr tun

- Amadeus von Hand auf den Zentimeter hinstellen oder mehrmals nach Hinweisen
  des Werkzeugs umstellen. Verlangt das Werkzeug Zentimeter, ist das ein
  Werkzeugfehler; er wird berichtet, nicht durch Umstellen umgangen.
- Die Türachse aus nur zwei Kantenpunkten.
- Die Selbst-Anfahrt an eine vorher bestandene Fahrt „von vorn“ koppeln.
- Neue Funktionen auf einen Fehlschlag setzen, dessen Ursache noch nicht
  ausgewertet ist.
- Nav2 ohne Nahsensoren „nebenbei“ im Fahrtor freischalten.
- Mehrere Änderungen in einem Realtest; Simulationserfolge als Beleg für die
  reale Tür (in der Simulation gelangen rund 16 Türfahrten, real 0 von 5
  Aufträgen).
- Aufträge ohne vorher festgelegten Ausstieg.

## 5. Offene Entscheidung des Projektinhabers

KI-F6 noch einmal als letzten Versuch ohne Nav2 (grob hinstellen) und
parallel den Nav2-Weg vorbereiten, oder sofort auf den Nav2-Weg wechseln
(Nahsensoren wieder an, zuerst den Stand vom 08.11. nachfahren).
