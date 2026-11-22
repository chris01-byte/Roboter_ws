# KI-Erkundung – aktueller Status

**Stand 22.11.2026 (nach KI-F1):** Amadeus ist am Roboter zum ersten Mal in
dieser Linie gefahren: eine gerade Etappe von 0,5 m, alle sechs Kriterien
erfüllt (0,505 m laut Laser, keine Abweichung zur Seite, nichts berührt).
**Die Fahrt durch die Labortür wurde nicht gestartet:** Von Amadeus' Platz
aus wurde die Tür 1,25 m breit vermessen statt 0,85 m, und der Auftrag
sperrte die Fahrt dann. Die Sperre war richtig; dass es dazu kam, lag an
einem bekannten, nicht behobenen Messfehler und an einer zu ungenauen
Aufstellanweisung. **Als Nächstes:** Folgeauftrag KI-F2
([AUFTRAG.md](AUFTRAG.md)), in dem im Stand so lange neu aufgestellt und
gemessen wird, bis es passt, und dann einmal gefahren wird.

Davor (21.11.): eine Drehung am Roboter mit Blickrunde, aus der die KI in
4,9 Sekunden die richtige Tür wählte (KI-1). Ein Urteil nach den Kriterien
K0-1 bis K0-6 gibt es weiter nicht (eine Blickrunde, kein Glas, kein
Spiegel). Die Vermessung misst Türen von vorn etwas zu schmal und von der
Seite des offenen Türblatts viel zu breit.

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
| Die KI wählt, Amadeus fährt | zur gewählten Tür und hindurch, im nächsten Raum neu umsehen; zuerst in der Simulation, dann im Labor | KI-2, KI-3 | **als Nächstes:** Fahrteil gebaut (Etappenfahrt ohne Nav2), in der Simulation durch die Tür gefahren; Auftrag KI-F1 bringt ihn in zwei Stufen auf den Roboter |
| Raum für Raum | weiter, bis kein Ausgang mehr offen ist (Laborraum, Flur, Schlafzimmer) | KI-3 | offen |
| Räume benennen, um Hilfe rufen | Raumnamen als Vorschlag in der App; Hilferuf mit Grund und Bild | KI-4 | offen |
| Auf Zuruf | „fahr in die Küche“, „such die Tasse“ | KI-5 | offen |

Die Stufen und ihre Kriterien stehen verbindlich im
[Konzept](KONZEPT.md), Abschnitt 8.

## Arbeitsliste

**Erteilt, wartet auf die Übergabe durch den Projektinhaber: Auftrag KI-F2
„Türdurchfahrt“** ([AUFTRAG.md](AUFTRAG.md)).
Auf dem Jetson, mit Christopher; ohne Kamera und ohne KI-Rechner; **ohne
neuen Build** (derselbe Release wie bei der gelungenen Etappe). Zuerst im
Stand, ohne Motorfreigabe: eine Messung aus der schrägen Lage vom 22.11.
(für die Ursache), dann mittig vor die Tür stellen und messen, bis das
Werkzeug „Aufstellung passt“ meldet. Danach genau eine Fahrt: bis 1,1 m vor
die Tür, ausrichten, hindurch, 0,45 m dahinter stehen bleiben.

**Danach, je nach Ergebnis:**
- Durchfahrt gelungen: Rundblick, Frage an die KI und Etappenfahrt in einem
  Zug (die Übergabe der gewählten Öffnung an das Fahrziel ist noch zu
  bauen); dazu die gespielte KI in der Simulation mit falscher, langsamer,
  stummer und unsinniger Antwort (Konzept, KI-2).
- Durchfahrt angehalten oder misslungen: zuerst die Ursache aus den
  Meldungen des Erkunders eingrenzen; keine neue Funktion darauf setzen.
- **Die Vermessung von der Seite des Türblatts** nach der Messung in KI-F2
  richtig stellen. Für eine KI, die Türen von beliebigen Plätzen aus wählt,
  ist das nötig; bis dahin fährt Amadeus nur aus einer Aufstellung vor der
  Tür.
- Daneben, unabhängig: dieselbe Drehung im Flur für weitere Blickrunden
  (braucht die Freigabe für diesen Raum).

**Offen an der Vermessung (aus KI-0R, KI-1 und KI-F1):**
- **Tür von der Seite viel zu breit:** in KI-F1 1,23 m und 1,25 m statt
  0,85 m (Tür 24° und 32° seitlich), in KI-0R 1,30 m. Vermutung, nicht
  belegt: Das Türblatt steht in den Raum hinein offen, und von seiner Seite
  aus sieht der Laser die Lücke zwischen Blattspitze und gegenüberliegendem
  Pfosten (bei 0,85 m Blatt im rechten Winkel 1,20 m). In der Simulation
  mit einem solchen Blatt erscheint genau diese Lücke (1,20 m, „sprung“,
  Kanten bei 1,18 m und 2,29 m); dort erkennt die vorhandene Blatt-Regel
  die Tür trotzdem richtig (0,84 m), am Roboter offenbar nicht. KI-F2 misst
  nach, mit vorab notierter Erwartung.
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

- **Die Etappenfahrt am Roboter über eine gerade Etappe hinaus.** Die
  gerade Etappe ist am 22.11. gelaufen. Offen: wie genau sich Amadeus auf
  wenige Grad ausrichten lässt (am Roboter noch nie gelaufen); ob der
  Nahbereichs-Halt mit den echten VL53 rechtzeitig anspricht und an Tür und
  Türblatt nicht fälschlich; wie sich der Kollisionsmonitor dort verhält.
- **Die neue Bewertung der Aufstellung und das Türfenster des Werkzeugs** an
  echten Messungen.
- **Die gespielte KI in der Simulation wählt bisher nur richtig.** Die Fälle
  falsch, langsam, stumm und Unsinn (Konzept, KI-2) stehen aus.
- **Der Weg von der Antwort der KI zum Fahrziel in einem Zug.** Heute nennt
  ein Mensch dem Werkzeug Nummer oder Richtung; die Übergabe der gewählten
  Öffnung aus der Blickrunde ist nicht gebaut.
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

Auftrag KI-F2 auf dem Jetson ([AUFTRAG.md](AUFTRAG.md)): im Stand aufstellen
und messen, bis es passt, dann einmal durch die offene Labortür.
