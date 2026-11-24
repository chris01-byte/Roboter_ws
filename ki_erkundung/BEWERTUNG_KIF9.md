# Bewertung nach KI-F9: Was robuster werden muss und wie es weitergeht (24.11.2026)

Anlass: Christopher nach KI-F9: „Das Grundkonzept funktioniert. Wir hatten
einige erfolgreiche Durchfahrten. Jedoch sind mir 3 Sachen aufgefallen.“
Erstens hielt die KI ein Fensterrollo für eine Tür (Frage: „ein robusteres
Modell, zum Beispiel SRM3 oder YOLO-26 oder Qwen 3.8 27b?“). Zweitens war
die Kostenkarte belegt, „obwohl nichts im Raum sich verändert hat“, und im
nächsten Lauf vom selben Platz frei. Drittens brach Amadeus kurz vor der
Tür ab, weil er sie „nicht mehr gefunden“ hat, „die Tür war ja direkt vor
ihm. […] In dem Fall muss die Kamera nochmal gucken oder es muss nochmal
der Lidar scannen.“ Auftrag: „evaluiere jetzt ausführlich, wie wir diese
kleinen Problemchen beheben können, den Stack insgesamt robuster machen
können (Selbstheilung). Und schaue […] auf das ganzheitliche Konzept, sind
wir auf dem richtigen Weg und wie gehen wir weiter.“

Diese Bewertung ist **keine Entscheidung**. Sie hält Ursachen, Möglichkeiten
und Empfehlung fest. Was der Projektinhaber entscheidet, kommt in den
[STATUS](STATUS.md); ändert es den Rahmen, auch in den
[Masterplan](../docs/wohnungserkundung/MASTERPLAN.md) §10.

**Vorgehen:** sechs getrennte Untersuchungen: Wiederfinden der Tür (2w3),
Kostenkarte (2w2), Absturz der Aufnahme und Ablauf, Fehlwahl der KI
(Lauf 2), Modelle (mit Websuche), Gesamtkonzept. Vier davon hat je ein
zweiter, skeptischer Prüfer gegen Bericht, Code und eigene Nachrechnung
geprüft; seine Korrekturen sind eingearbeitet. Die tragenden Aussagen sind
zusätzlich von Hand nachgesehen. Nur gelesen und nachgerechnet, nichts
gefahren; im Repository wurde dafür nichts geändert. Alle Maße sind vom
Roboter aus angegeben, ohne Bilder und ohne Lage in der Wohnung.

## 0. Kurz

- **Das Grundkonzept trägt.** Seit KI-F7 wurde jedes gesendete Fahrziel wie
  geplant gefahren; die einzige Ausnahme war ein berechtigter Halt in
  KI-F7. In KI-F9 standen alle Zähler der Schutzkette auf 0, nichts wurde
  berührt, Christophers Nein hat gewirkt. **Alle Fehlschläge lagen vor dem
  Fahren**: beim Sehen, beim Prüfen und im Ablauf.
- **Jedes der drei Probleme hat eine benennbare Ursache.** Keine liegt am
  Fahren oder an der Schutzkette:
  1. **Fensterrollo:** vor allem *nicht* das Modell. In Lauf 2 hatte die
     Labortür gar keine Nummer, zwei Nummern lagen im Foto übereinander, und
     die Antwort der KI gleicht in Wahl, Arten und Zahlen genau dem Beispiel
     aus unserer Frage.
     Wo die Tür eine Nummer hatte, hat die KI sie bisher immer gewählt.
  2. **Kostenkarte:** Sie war wirklich belegt. Etwas in Hüfthöhe, etwa 1,9 m
     links von Amadeus, lag knapp hinter dem Punkt, an dem er sich gedreht
     hätte. Ohne Nahsensoren ist die Kostenkarte die Laserkarte vom
     Rundblick; was dabei in der Nähe stand, auch ein Mensch, bleibt bis zum
     Ende des Laufs darin. Unsere Zeile „Karte (SLAM) frei“ war ein Fehler
     im Werkzeug.
  3. **Tür nicht wiedergefunden:** Der Laser *hat* nach der Anfahrt neu
     gescannt und die Tür richtig gesehen. Die erste, schräge Messung hatte
     sie aber rund 0,35 m zu nah gelegt, vermutlich wegen etwas, das rechts
     neben dem Türrahmen vor der Wand steht. Die starre Regel „höchstens
     0,35 m daneben“ hat dann die echte Tür abgelehnt.
  4. **Dazu der Absturz der Aufnahme:** ein bekanntes Verhalten von ROS
     Humble beim Beenden mit Strg+C. Die Hauptlinie hat es im September
     gelöst, die KI-Linie hatte die Lösung nicht übernommen.
- **Modellfrage:** Qwen3.8-27B gibt es und ist einen Versuch wert,
  SAM 3 („SRM3“) und YOLO26 taugen als zweite Meinung. Ein größeres Modell
  allein hätte Lauf 2 aber wohl nicht verhindert. Zuerst kommen Vermessung,
  Darstellung und Frage, dann der Modellvergleich an den gespeicherten
  Runden, dann eine zweite Meinung als Veto.
- **Selbstheilung** heißt hier „Nachfassen“: die Heilungsleiter der
  Hauptlinie (warten, neu messen, andere Wege prüfen, Sicht gewinnen,
  gezielt fragen), zuerst nur im Werkzeug, während Amadeus steht. Erkunder
  und Schutzkette bleiben unverändert.
- **Richtiger Weg?** Für das Prinzip „die KI wählt, die Vermessung prüft,
  die Schutzkette fährt“: ja. Für „Raum für Raum“: noch nicht; dafür fehlen
  Nahsensoren, Seitentüren im schmalen Flur und ein zweiter Rundblick in
  derselben Mission.
- **Wie weiter:** (1) Werkzeugfehler hier beheben, (2) ein reiner
  Auswerteauftrag KI-F9N am Jetson, ohne Fahrt, (3) das Sehen ohne Roboter an
  den gespeicherten Runden verbessern, (4) ein Realtest „Nachfassen im
  Stand“. Christophers Ja vor jeder Fahrt bleibt.
- **Zwei Sicherheitshinweise** (Abschnitt 8): Öffnungen mit nur geschätztem
  zweitem Pfosten („lot“) sind heute nicht von der direkten Durchfahrt
  ausgenommen. Und ohne Nahsensoren sieht Amadeus *während* einer Etappe
  nichts Neues rechtzeitig, auch nicht in Hüfthöhe.

## 1. Was KI-F9 gezeigt hat

Fünf Missionen, eine durch die Tür (Archiv:
[archiv/20261124-kif9-ki-waehlt/](archiv/20261124-kif9-ki-waehlt/)):

| Lauf | Was geschah | Woran es lag (Abschnitt) |
|---|---|---|
| 1 | KI wählt die Labortür, Ja, Anfahrt 1,61 m, Tür wiedergefunden (nachgerechnet 0,03 bis 0,09 m daneben), Durchfahrt, 3,49 m | gelungen |
| 2 | KI wählt ein Fensterrollo als „offene Tür“ (90 %), Nein, nichts gefahren | Vermessung, Darstellung, Frage (2) |
| 2w | Aufnahme stürzt beim Beenden ab, keine Blickrunde, nichts gefahren | Signalbehandlung (5) |
| 2w2 | KI wählt die Labortür, Ja, Kostenkarte auf der Anfahrt belegt, nicht gesendet | echte Stelle knapp hinter dem Wendepunkt, Werkzeugzeile falsch (3) |
| 2w3 | KI wählt die Labortür, Ja, Anfahrt 1,57 m, danach „nicht wiederzufinden“ | schräge erste Messung, starre Regel (4) |

Anfahrt und Wiederfinden gelangen bisher von Plätzen bis etwa 1,0 m
seitlich und 17 bis 18° schräg zur Tür (KI-F6 bis KI-F9 Lauf 1). Beide Fehlschläge nach einem Ja kamen
von weiter seitlich und schräger (1,16 bis 1,27 m, 29 bis 32°). Lauf 2 lief
viermal, 38 Minuten ohne Durchfahrt.

## 2. Problem 1: Das Fensterrollo (Lauf 2)

**Was geschah:** Die Vermessung bot genau zwei Nummern an, beide hinter
Amadeus am Fenster und praktisch an derselben Stelle: Nr. 1 0,82 m breit,
2,6 m entfernt, 176° rechts; Nr. 2 0,83 m, 2,5 m, 174° rechts. Die Mitten
liegen etwa 0,13 m auseinander. Die KI nannte Nr. 1 „Lücke an Möbeln“ (80 %),
Nr. 2 „offene Tür“ (90 %) und wählte Nr. 2. Die Labortür hatte in dieser
Runde **keine Nummer**, obwohl sie in 2w2 und 2w3 vom etwa selben Platz
angeboten wurde. Richtig wäre also „keine Wahl“ gewesen.

**Warum: drei Ursachen kamen zusammen.**

1. **Die Vermessung.** Ein echter Fehler ist gefunden und von zwei Prüfern
   unabhängig nachgestellt: Steht ein Möbel schräg gesehen vor der Wand neben
   einer Lücke, kann die Lot-Regel eine Scheinlücke mit vertauschten Kanten
   erzeugen. Sie gilt dann als fast 360° breit und verdrängt jede breitere
   Öffnung im ganzen Rundblick als „überdeckt“, auch eine Tür auf der
   anderen Seite. Ob genau das in Lauf 2 geschah, zeigt erst das gespeicherte
   Protokoll der Runde am Jetson. Die Doppelnummer kann auch anders
   entstanden sein: Zwei schräg gesehene Lücken überdecken sich nur im
   Winkel, und die Prüfung kennt keine Lage.
2. **Die Darstellung.** Die beiden Nummernscheiben lagen im Foto fast
   übereinander: Die Mitten waren 4 bis 23 Bildpunkte auseinander, eine
   Scheibe ist 22 Bildpunkte breit, und Nr. 2 war über Nr. 1 gemalt.
3. **Die Frage.** Die Antwort gleicht in Wahl, Arten und Zahlen genau dem
   Antwortmuster in unserer Frage. Dort steht als Beispiel: Wahl 2, Nr. 1 „moebelspalt“
   mit 0,8, Nr. 2 „tuer_offen“ mit 0,9 (`lotse/frage.py`, Antwortmuster).
   Bei unklarem Bild hat das Modell offenbar das Beispiel übernommen. Dazu
   kommt: Das Schema verlangt die Wahl als erstes Feld, vor der Einordnung.
   Es gibt keine Art „Fenster“ oder „Rollo“, nur „Glas“. Die Angabe „sicher
   zu … %“ ist nirgends erklärt; die falsche Wahl hatte 90 %, die richtigen
   90 bis 95 %.

**Das Muster über alle Runden:** Hatte die Tür eine Nummer, wählte die KI
sie jedes Mal (KI-0, KI-0N, KI-0R, KI-1 und alle Wahlen in KI-F9). Alle drei
bekannten Fehlwahlen fielen in Runden, in denen kein echter Ausgang eine
Nummer hatte: in KI-0 eine Möbellücke, in KI-0N die Wand zwischen zwei
Flurtüren, in KI-F9 das Rollo. Die Schwäche ist weniger das Erkennen der
Tür als das Nein-Sagen: Die KI wählt lieber irgendetwas als „keine Wahl“.
Auch in Lauf 1 nannte sie eine zweite Nummer „offene Tür“ (85 %, 152°
links, 1,5 m); was dort war, hat noch niemand eingetragen.

**Was hilft (alles zuerst ohne Roboter an den gespeicherten Runden
prüfbar):**

1. **Daten lesen:** das Protokoll der Runde Lauf 2 (warum die Tür fehlte,
   ob Nr. 1 und Nr. 2 dieselbe Stelle sind). Auf dem KI-Rechner den Rohtext
   der Antwort. Christopher trägt ein, was jede Nummer war.
2. **Vermessung nachbessern** (vier Regeln zusammen): ein Lot vor dem
   sichtbaren Pfosten verwerfen; die Winkelspanne immer als kürzeren Bogen
   rechnen; Kanten nur nach Lücken bis 60° überspringen; zwei Lücken mit
   Mitten unter 0,30 m als eine Öffnung zählen. Nachgerechnet in 9000
   künstlichen Zimmern: keine Scheinlücken und keine Doppelnummern mehr;
   die Tür wird 31-mal öfter und nie seltener angeboten. Die letzte Regel
   gilt nur für die Angebotsliste an die KI. Im Fahrwerkzeug bleibt die
   Sperre „zwei Öffnungen fast gleich nah: nicht eindeutig“. Die Änderung
   betrifft alle Stellen, die denselben Baustein benutzen.
3. **Nie zwei Nummern zeichnen, deren Scheiben sich decken.**
4. **Die Frage neu fassen:**
   - ein neutrales Muster ohne echte Nummern und Arten;
   - erst jede Nummer einordnen, dann wählen: Reicht sie bis zum Boden? Was
     ist dahinter: Raum, draußen, Glas, Rollo, Möbel?
   - eine eigene Art „Fenster“, auch mit Rollo, Jalousie oder Vorhang;
   - „lieber keine Wahl als eine falsche“.
   Die Prozentangabe kommt aus der Nachricht an Christopher heraus, solange
   sie nichts bedeutet.
5. **Widerspruchsregel:** Liegen zwei Nummern an derselben Stelle (Mitten
   unter 0,30 m) und ist die eine als Ausgang, die andere als etwas anderes
   eingeordnet, gibt es keine Wahl. Das hätte Lauf 2 gestoppt und keine der
   richtigen Wahlen. Die Regel gehört dorthin, wo Lage und Antwort zusammen
   vorliegen, damit auch Trockenlauf und Auswertung sie zählen.
6. **Laser-Merkmale gegen Glas und draußen:**
   - Wie viele Strahlen enden auf der Türlinie? Bei Glas oder Rollo gibt es
     dort Echos.
   - Wie viele kommen gar nicht zurück? Heute zählt kein Echo als „8 m
     frei“, ein Fenster nach draußen sieht damit wie die tiefste Öffnung
     aus.
   Erst messen und an der Tür gegen das Fenster eichen, dann als harte
   Prüfung.
7. **Erst danach** der Modellvergleich und eine zweite Meinung
   (Abschnitt 6).

## 3. Problem 2: Die belegte Kostenkarte (Lauf 2w2)

**Was geschah:** Nach Christophers Ja plante das Werkzeug die Anfahrt: 101°
links drehen, 1,35 m fahren, 110° rechts drehen, 0,45 m. Es sendete nicht:
„Kostenkarte passt nicht: belegt 1.87 m voraus (Strecke 1)“. Herkunft:
„Karte (SLAM) frei; Laser sieht dort etwas“. Christopher: „da war aber
nichts“. Im nächsten Lauf, vom praktisch selben Platz, war alles frei.

**Was es war (auf Zentimeter nachgerechnet):**
- Die Stelle lag **etwa 1,9 m links von Amadeus, ungefähr auf Höhe seines
  Hecks**. Sie lag nicht auf dem Weg, sondern 0,52 m hinter dem Ende der
  ersten Strecke, dort, wo er sich zur Tür gedreht hätte. Berührt hätte er
  sie nicht (Drehkreis 0,36 m, Abstand 0,54 m).
- Der Nahbereichs-Halt des Erkunders schaut auch auf den letzten
  Zentimetern einer Strecke 0,25 m über die gepolsterte Vorderkante hinaus.
  Das Werkzeug bildet das absichtlich nach. Ob der Erkunder dort wirklich
  angehalten hätte, entscheiden ±2 cm. Ein Halt hätte die ganze Mission
  beendet.
- **Dort stand wirklich etwas in Laserhöhe (0,75 m, Hüfthöhe).** Der Laser
  sah es beim Ja im Mittel über 21 Scans, 3,5 bis 3,9 Minuten nach dem
  Rundblick, also kein kurzer Ausreißer. Was es war, ist offen: eine Person,
  eine Stuhllehne, eine Tisch- oder Regalkante. Eine Person passt genauso,
  auch Christopher selbst, der laut Auftrag seitlich mit der Hand am Not-Aus
  stand.
- **„Karte (SLAM) frei“ war ein Fehler unseres Werkzeugs.** Es sah nur in
  einem Streifen vor dem Roboter nach; die Stelle lag seitlich. In Wahrheit
  stand sie in der Karte.

**Warum „auf einmal frei“:** Amadeus stand in 2w3 rund 12 cm anders, die
Tür wurde etwas anders vermessen, und der geplante Weg lief 4,5 cm an der
Stelle vorbei. Das ist die wahrscheinlichste Erklärung, aber nicht sicher:
Mit der unsicheren Türachse in 2w3 läge die Stelle in 8 bis 16 % der Fälle
doch im geprüften Streifen.

**Was man wissen muss:** Ohne Nahsensoren besteht die Kostenkarte nur aus
der Laserkarte des SLAM. Was beim Rundblick in Hüfthöhe in der Nähe stand,
auch ein Mensch, bleibt darin **bis zum Ende des Laufs** belegt.
Weggehen hilft in diesem Lauf nicht mehr, Warten auch nicht. Erst ein neuer
Stackstart räumt es.

**Was hilft:**
1. **Herkunft richtig prüfen:** rings um die Stelle statt nur voraus.
   Sieht keine Quelle etwas, heißt es „Prüfung widersprüchlich“ statt
   „frei“; mit Nahsensoren bleibt deren heutige Erklärung.
2. **Meldung in Worten, die man versteht**, beide Kanten richtig benannt.
   Beispiel: „Etwas in Hüfthöhe, 1,9 m links von ihm auf Höhe seines Hecks.
   Es liegt nicht auf dem Weg, aber 0,5 m hinter dem Punkt, an dem er sich
   dreht. Am Drehpunkt läge es 0,25 m vor seinem Gehäuse und 0,19 m vor
   der gepolsterten Vorderkante; der Nahbereichs-Halt könnte dort
   anhalten.“
3. **Wegvarianten statt Aufgeben:** alle Anfahrten prüfen (1,6 bis 2,1 m vor
   der Tür, letzte Strecke 0,45 oder 0,60 m) gegen Laser und Kostenkarte,
   mit 3 cm Rand, und die erste freie nehmen. Eine letzte Strecke von
   0,40 m geht nicht: Mit der Ankunftstoleranz von 0,10 m blieben 0,30 m,
   und darunter richtet sich der Erkunder nicht mehr aus. In 2w2 wären
   freie Varianten da gewesen, gerechnet gegen die eine bekannte Stelle.
4. **Den Weg vor der Frage ansagen:** Das Werkzeug plant schon vor der Frage
   F-Wahl, ohne zu senden (`--nur-messen` gibt es schon). Christopher hört
   dann, wohin Amadeus fahren wird.
5. **Standort des Menschen:** Während des Rundblicks und der Fahrt an einer
   Stelle stehen, die vom möglichen Weg weg liegt, also hinter Amadeus oder
   auf der Seite weg von der Tür, mindestens 1 m entfernt. Beim Drehen nicht
   herumgehen.
6. **Gleich weit schauen wie der Erkunder:** Die Laserprüfung des Werkzeugs
   reicht heute 0,33 m über das Streckenende, die des Erkunders 0,48 m.
   Etwas Neues 0,37 bis 0,48 m hinter einem Punkt lässt das Werkzeug durch,
   und der Erkunder bricht dann mitten in der Anfahrt ab. Das Werkzeug
   prüft künftig ebenfalls bis 0,48 m.
7. **Warten nur, wo es wirkt:** wenn der Laser etwas sieht, das nicht in der
   Karte steht. Dann kam es nach dem Rundblick dazu, meist ein Mensch. Das
   kommt als eigener Test nach den Varianten.
8. **Belege sichern:** Das Werkzeug speichert bei jeder Entscheidung seine
   Scans und die Zellen um eine sperrende Stelle in der Ablage des Laufs auf
   dem Jetson. Für 2w2 fehlt genau dieser Beleg.

**Nicht empfohlen:** den Nahbereichs-Halt des Erkunders am Streckenende
verkürzen. Das hätte 2w2 gelöst. Es lockert aber die Schutzkette des
einzigen Navigationsbesitzers: Bei spät ankommenden Einträgen schrumpft die
Reserve um 5 bis 10 cm. Die Varianten lösen 2w2 ohne Lockerung.

## 4. Problem 3: Die Tür nach der Anfahrt „nicht wiederzufinden“ (Lauf 2w3)

**Was geschah:** Die erste Messung vom Startplatz ergab 0,87 m Breite, 2,36 m
Entfernung, 21° links. Amadeus sah die Tür dabei 29° schräg, und die zweite
Kante wurde aus der Wandlinie gefolgert (Schluss „linie“). Die Anfahrt lief
genau wie geplant: 87° links, 1,16 m, 102° rechts, 0,50 m, Rest 0,05 m und
1°. Die neue Messung ergab eine Öffnung von 0,77 m in 2,01 m, 9° links,
beide Kanten gemessen (Schluss „sprung“). Dann kam „Die Tür von vorhin ist
nach der Anfahrt nicht wiederzufinden“.

**Was es war:** Christophers Eindruck stimmt. Amadeus stand etwa 2,0 m vor
der echten Tür, 0,07 bis 0,21 m neben ihrer Mitte, mit Blick 3 bis 7° neben
der Achse. Aus dieser Aufstellung hätte er hindurch gedurft. **Falsch war
die erste, schräge Messung:** Sie hatte die Türmitte rund 0,35 m vor die
echte Tür gelegt. Das zeigt die Rechnung ohne Karte, nur aus gefahrenen
Wegen und Drehwinkeln: Die neu gesehene Öffnung lag 0,33 bis 0,39 m tiefer
als die gemerkte. In Lauf 1 waren es zum Vergleich 0,03 bis 0,09 m. Mit der
Lage laut Karte kamen 0,21 m seitlich dazu, etwa zur Hälfte aus einer
Drehung der Karte um rund 3°; zusammen 0,42 m. Die Regel „höchstens 0,35 m
in jede Richtung“ lehnte die echte Tür ab.

**Wahrscheinlicher Grund für die falsche erste Messung:** Rechts neben dem
Türrahmen steht vermutlich etwas, rund 0,35 m tief vor der Wand: ein Möbel,
ein Mauervorsprung, ein Stuhl oder eine Person. Aus dem schrägen Blick
hielt die Vermessung dessen Vorderkante für die Wand neben der Tür. Dafür
spricht:
- Eine Kante im Protokoll des Vorlaufs liegt genau 0,34 m vor der
  Türebene.
- Schon KI-0R (21.11.) sah eine Möbellücke 0,5 m vor dieser Tür.
- Eine künstliche Welt mit einem solchen Kasten ergibt ohne weitere
  Anpassung die Zahlen aus 2w3 und auch die aus 2w2.

Bestätigt ist das erst, wenn jemand nachsieht.

**Was hilft: nicht mehr Hinsehen, sondern eine bessere Regel.** Der Laser
hat nach der Anfahrt richtig nachgesehen; nur der Vergleich mit der alten
Messung war zu starr.
1. **Das Wiederfinden nennt immer den Abstand:** wie viel tiefer, wie viel
   seitlich, wie viel breiter. Heute muss man das nachrechnen.
2. **Wiederfinden in Stufen:**
   - seitlich streng, höchstens 0,30 m;
   - in der Tiefe so großzügig, wie unsicher die erste Messung war: nach
     einem Blick schräger als 20° oder einem Schluss ohne zweite gemessene
     Kante bis 0,60 m tiefer;
   - nur, wenn die Zuordnung eindeutig ist und die neue Messung frontal
     beide Kanten hat.
   Durchgefahren wird dann nach der neuen, frontalen Messung, nie nach der
   alten.
3. **Nur nach einem Blickwechsel.** Für die Zuordnung der KI-Wahl im Stand
   bleibt die enge Regel (0,40 m, eindeutig): Dort messen beide vom selben
   Platz, und die Bindung an Christophers Ja muss eng bleiben.
4. **Korrektur-Anfahrt:** Passt die Aufstellung nach der Anfahrt nicht,
   folgt eine kurze zweite Anfahrt als weiteres Ziel derselben Mission
   (höchstens 3 Ziele je Mission).
5. **Später:** Sieht Amadeus eine Tür sehr schräg, fährt er zuerst an einen
   Sichtpunkt, von dem aus er sie frontal misst.
6. **Grenzwerte vorher prüfen:** an allen gespeicherten Anfahrten (KI-F6
   bis KI-F9) und an Gegenfällen (Möbellücke vor der Tür, Tür hinter der
   Tür) nachrechnen, nicht nur an 2w3.

**Kamera nach der Anfahrt?** Für diesen Fall nicht nötig. Später ist eine
Rückfrage im Zweifel denkbar, dann aber nur als zusätzliches Nein. Nach dem
Fensterrollo darf ein Ja der KI keine Messgrenze aufweichen. Das braucht
eine Entscheidung, weil die Kamera heute nur während des Rundblicks läuft.

## 5. Dazu: Absturz der Aufnahme und der Ablauf mit zwei Shells

**Absturz (2w):** Bei `kill -INT` löst ROS einen `KeyboardInterrupt` aus.
Fällt der genau in das Umwandeln einer gerade empfangenen Nachricht, macht
die Bibliothek unter Humble daraus einen `RuntimeError` („Unable to
convert call argument …“). Die Aufnahme fing nur zwei andere Arten ab.
Deshalb schrieb sie nichts, und über 200 Aufnahmen gingen verloren.
- Nachgestellt: Mit dem heutigen Code ging bei 4 von 73 Signalen die Runde
  verloren, mit Korrektur bei 0 von 70.
- Es gibt einen zweiten, selteneren Weg („context is not valid“), den die
  Aufnahme heute ebenfalls nicht fängt.
- Die Hauptlinie hat dasselbe im September gelöst: Ein eigener Handler
  setzt nur eine Marke, und rclpy läuft ohne eigenen Handler.
- Unser Nachtrag vom 23.11. hat den Grund falsch zugeordnet. Es hängt nicht
  an der ROS-Fassung, sondern daran, ob SIGINT beim Start ignoriert war.

**Ablauf (2w3):** `ki_tuer_waehlen.py` lief einmal ohne ROS-Umgebung und
meldete das erst nach 7 s Aufbereitung. Der Auftrag bestand aus zehn
Handschritten in zwei Shells mit zwei Umgebungen, und ein Suchmuster passte
nicht auf die Statusmeldung.

**Was hilft (keine Änderung am Fahren):**
1. Ein gemeinsamer Baustein für alle ROS-Werkzeuge der KI-Linie: Ein Signal
   setzt nur eine Marke. Die Aufnahme schreibt in jedem Fall, was sie hat.
2. Die Aufnahme endet von selbst 5 s nach Beginn der Wartephase des
   Erkunders. Im Normalfall gibt es dann kein `kill -INT` mehr, und die
   Frage an Christopher kommt 30 bis 40 s früher.
3. `ki_tuer_waehlen.py` prüft die Umgebung zuerst, in unter 1 s, und nimmt
   genau die Runde dieser Aufnahme statt „der neuesten“.
4. **Eine Ablaufhilfe auf dem Jetson** ersetzt die Handschritte:
   - Sie sourct jede Umgebung selbst.
   - Sie startet und stoppt keine Mission und sendet nichts an ROS.
   - Nur Christophers „ja“, an genau diese Wahl gebunden, startet das
     Werkzeug zum Fahren.
   Sie ist ein Zielgeber wie bisher der Agent, kein Aufseher.
5. Am Jetson im Stand messen: alte gegen neue Aufnahme, je 30-mal mit einem
   Signal.

## 6. Die Modellfrage

| Genannt | Was es ist | Taugt es für uns? |
|---|---|---|
| „SRM3“ | Vermutlich **SAM 3** von Meta; ein Modell „SRM3“ gibt es nicht. Es findet zu einem Wort („door“, „window“, „window blind“) alle passenden Flächen im Bild. | Nur als zweite Meinung, nicht als Entscheider, denn es wählt keinen Ausgang. Ohne Training stark, aber groß. Die Lizenz hat eigene Bedingungen, der Download gibt es erst nach Freischaltung. Die Zeit auf der RTX 3090 ist unbekannt. **Dritte Wahl.** |
| „YOLO-26“ | **YOLO26** von Ultralytics (Januar 2026), sehr schnell. | Die normale Fassung kennt weder Tür noch Fenster. Die Fassung **YOLO26-sem-ade20k** ordnet jedem Bildpunkt eine von 150 Klassen zu, darunter Tür, Fensterscheibe, Rollo, Vorhang und Spiegel. Sie braucht 4 bis 10 ms je Bild auf einer RTX 3090 und unter 1 GB. **Gute unabhängige zweite Meinung (Veto).** Die Klasse „glass“ ist dort ein Trinkglas. |
| „Qwen 3.8 27b“ | **Qwen3.8-27B** (August 2026, Apache-2.0), ein Bild-Sprach-Modell wie das heutige, dreimal so groß. In Ollama 18 GB, unterstützt ab Ollama 0.32.12; der KI-Rechner hat 0.32.15. | Ohne Codeänderung tauschbar (`--modell`). Unabhängig gemessen insgesamt deutlich besser (69,5 gegen 56,0 %), beim Erkennen von Dingen aber kaum (85,4 gegen 83,3 %, innerhalb der Streuung). Gleich gebauter Bildteil, dieselben Fotos mit 320 × 180 Bildpunkten: Eine Tür in 2,5 m sind rund 3 × 4 Bildbausteine. Passt nicht zusammen mit dem Planer der Hauptlinie in die 24 GB, neben YOLO-World nur knapp oder mit Auslagern. **Offline-Versuch wert.** |

**Warum nicht zuerst das Modell:**
1. In Lauf 2 hatte die Tür keine Nummer.
2. Die Nummern lagen übereinander.
3. Die Antwort war das Beispiel aus unserer Frage.

Das sind Fehler in Vermessung, Darstellung und Frage. Sie lassen sich ohne
neues Modell beheben und am heutigen Modell prüfen. Wo die Tür eine Nummer
hatte, hat das heutige Modell sie immer gewählt.

**Empfohlene Reihenfolge**, alles zuerst ohne Roboter an den gespeicherten
Runden:
1. Vermessung, Darstellung und Frage nachbessern (Abschnitt 2). Dann
   Lauf 2 mit dem heutigen Modell neu fragen.
2. **Heutiges Modell gegen Qwen3.8-27B:**
   - je Modell ein eigener Lauf über alle Runden mit eingetragener
     Wahrheit, Denken aus;
   - die anderen Modelle vorher entladen;
   - Speicher, Ladezeit und Antwortzeit festhalten;
   - bewertet nach K0-1 bis K0-5 (Konzept §8).
3. **Eine zweite Meinung mit Vetorecht** aus einer anderen Modellfamilie:
   YOLO26-sem-ade20k. Dafür sprechen Tür und Gittertür, dagegen
   Fensterscheibe, Rollo, Vorhang und Spiegel. YOLOv8 mit der Klasse
   „Window blind“ (Open Images) läuft in derselben Sitzung mit. SAM 3 nur,
   wenn beides nicht reicht.
4. **Mittelfristig der größte belegte Hebel:** ein eigener kleiner Erkenner
   für Tür, Fenster und Rollo, nachtrainiert mit 80 bis 200 Bildern aus den
   eigenen Blickrunden. Eine Studie zu Türerkennern auf Robotern fand ohne
   eigene Bilder nur mAP 12 bis 37, mit rund 80 eigenen Bildern 41 bis 76.
   Die Bilder bleiben im Haus.
5. **Statt größerer Kamerabilder** (Sensorbereich der Hauptlinie): einen
   vergrößerten Ausschnitt des vorhandenen Fotos um die gewählte Nummer
   mitschicken. Er prüft direkt, ob die Bildgröße die Grenze ist.

**Regeln für jede zweite Meinung:**
- Sie kann nur sperren, nie eine Fahrt erzwingen.
- Der Laser bleibt harte Bedingung, es gibt keine Mehrheitsentscheidung.
- Je Realtest kommt nur eine solche Änderung dazu, und Christophers Ja
  bleibt.
- Sie bräuchte auf dem KI-Rechner einen eigenen Dienst mit eigener
  Python-Umgebung, damit die Objekterkennung der Hauptlinie unberührt
  bleibt. Heute gehen Bilder nur an Ollama; das wäre eine freizugebende
  Ausnahme.

## 7. Selbstheilung: „Nachfassen“ statt Abbrechen

Selbstheilung heißt hier: Ein Problem führt nicht gleich zum Abbruch,
sondern zu einem begrenzten, sicheren nächsten Versuch. Erst wenn der nicht
hilft, kommt eine klare Frage an Christopher. **Nicht** gemeint ist, Schutz
wegzulassen. Vorbild ist die Heilungsleiter der Hauptlinie
(`docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md`, Logik in
`src/explore/explore/self_healing.py`, nur lesend wiederverwendet): „Ein
Stopp ist ein Pausieren, kein Missionsende.“ Damit es nicht mit
`self_healing:=true` verwechselt wird, heißt es in der KI-Linie
„Nachfassen“.

| Stufe | Was Amadeus tut | Wo | Fall aus KI-F9 | Grenze |
|---|---|---|---|---|
| Grundlage | Werkzeugfehler beheben, nicht durch Wiederholen wegheilen | Werkzeuge | 2w, 2w3 (Umgebung), 2w2 (Herkunftszeile) | – |
| Neu messen, andere Wege prüfen | bis zu drei Messungen; alle Anfahrten gegen Laser und Kostenkarte; Wiederfinden in Stufen; Abstand immer ausgeben | Werkzeug, im Stand | 2w2, 2w3 | höchstens 3 Messungen; durch die Tür nur nach frischer frontaler Messung mit zwei Kanten |
| Warten | Sieht der Laser etwas Neues, das nicht in der Karte steht: warten, neu messen | erst Werkzeug im Stand; später Erkunder („Pause statt Ende“) | Mensch im Weg | höchstens 3-mal 10 s innerhalb der Wartezeit des Erkunders; Einträge der Karte heilt Warten nicht |
| Sicht gewinnen | Korrektur-Anfahrt; bei sehr schrägem Blick erst ein Sichtpunkt | Werkzeug, als Fahrziele | 2w3 | höchstens 3 Ziele je Mission |
| Zurückstellen, merken | Tür „später“; ein vom Menschen benanntes Fenster nicht wieder anbieten; Rückweg kennen | Werkzeug, Gedächtnis auf dem Roboter | Lauf 2 | höchstens dreimal je Tür; keine Koordinaten verlassen den Roboter |
| Zweite Meinung | bei Widerspruch oder Verdacht auf Glas keine Wahl, dafür eine Rückfrage | KI-Rechner | Lauf 2 | nur sperren |
| Gezielt fragen | Frage mit Ursache in Worten („Stehst du 1,9 m links von ihm?“) | Ablauf, später App | 2w2 | keine Antwort heißt keine Fahrt |
| Sicher stoppen, fortsetzbar bleiben | Schutzkette unverändert; Karte, Runde, Wahl und Gedächtnis bleiben erhalten | Erkunder, Schutzkette | alle | nie wegheilen: Not-Aus, Kollision, Aktor- und Encoderfehler, Radsensor-Sperre beim Start |

**Wo Nachfassen wohnt, und nur dort:**
- **(a) Das Werkzeug der KI-Linie** heilt beim Messen, Wählen und Fragen.
  Es handelt nur, während Amadeus steht und der Erkunder auf ein Ziel
  wartet, und sendet nur Ziele oder „ende“.
- **(b) Der Erkunder** heilt Bewegung, und das erst später, als eigene,
  freigegebene Anschlussstelle mit Vorgabe aus.

Kein dritter Prozess beobachtet oder übersteuert den Erkunder. Es gibt kein
blindes Löschen der Kostenkarte, keine erfundenen gesunden Quellen und
keine unbegrenzten Wiederholungen (MASTERPLAN §4, §10).

## 8. Sicherheitshinweise aus der Prüfung

1. **„lot“-Öffnungen:** Durch eine nur geschätzte Tür wird heute nicht
   gefahren, aber diese Ausnahme gilt nur für die Schätzung hinter einem
   Türblatt. Öffnungen, deren zweiter Pfosten über die Lot-Regel geschätzt
   ist, sind nicht ausgenommen. Genau das ist der Fall der Scheinlücke aus
   Abschnitt 2. Laserprüfung der Fahrlinie und Kostenkarte würden eine Wand
   dahinter weiter sehen, die Regel „nie durch eine Schätzung“ soll aber
   auch hier gelten: erst Anfahrt, dann Durchfahrt nach neuer Messung mit
   zwei gemessenen Kanten. Das gehört in den nächsten Umbau des Werkzeugs.
2. **Was Amadeus ohne Nahsensoren während der Fahrt sieht:** Der Laser
   prüft den Weg *vor* jeder Etappe. *Während* einer Etappe liest der
   Nahbereichs-Halt nur die Kostenkarte, und in die Laserkarte kommt Neues
   erst nach etwa 0,25 m Fahrt. Eine Etappe ist 0,28 bis 0,50 m lang. Tritt
   jemand während einer Etappe vor Amadeus, hält ihn praktisch nur der
   Not-Aus, auch in Hüfthöhe. Die Vorabfrage F0 sagte bisher nur, dass er
   nichts unter 75 cm sieht. Das muss im nächsten Auftrag deutlich drinstehen.
3. **Keine Regel lockert eine bestehende Sperre.** Das Zusammenfassen naher
   Lücken gilt nur für das Angebot an die KI, nicht für die
   Eindeutigkeitsprüfung beim Fahren. Ein Ja der KI hebt keine Messgrenze
   an.

## 9. Sind wir auf dem richtigen Weg?

**Für das Prinzip ja.** Die Rollen tragen: Die KI wählt nur angebotene
Nummern, der Roboter misst nach, der Erkunder fährt allein.
- Die Fahrbausteine sind am Roboter belegt: je Etappe höchstens 5 mm
  seitlich und 0,5° daneben, nach dem Ausrichten höchstens 1,0° Rest.
- Die Übergabe der Wahl über die Karte fand die gewählte Öffnung jedes Mal
  wieder (0,00 bis 0,04 m).
- Jede Unsicherheit endete im Stillstand, keine in einer Fahrt.
- Das Sehen lässt sich ohne Fahren verbessern, weil jede Runde mit Protokoll
  gespeichert ist.

**Für „Raum für Raum“ noch nicht.** Die Belege sind schmal: eine Tür, eine
Seite, ein großer Raum, keine Nahsensoren, und Christopher räumt den Weg
frei. Was die Labortür nicht prüft:
- **Seitentüren im 1,3 m breiten Flur:** Die Anfahrt braucht heute 2,05 bis
  2,55 m vor der Tür, das ist dort unmöglich. Es braucht ein eigenes Profil
  für kurze Abstände oder doch Nav2. Nav2 ist heute ohne Nahsensoren am
  Fahrtor gesperrt und erreichte zuletzt kein Ziel.
- **Ohne Nahsensoren ist die Wohnung kein Einsatzort:** Niedriges sieht
  niemand, und während einer Etappe sieht er nichts Neues (Abschnitt 8).
- **Ein zweiter Rundblick in derselben Mission**, mit Prüfung des
  Drehkreises vorher, ohne dass ein Mensch ihn freiräumt.
- **Wartezeit:** Auf ein Folgeziel wartet der Erkunder 120 s, Christophers
  Antworten kamen nach 101 bis 211 s.
- **Etappen je Ziel statt je Mission**, ein Gedächtnis der Türen und eine
  Regel, wann ein Raum fertig ist.

**Folgerung:** weitermachen, aber nicht mit weiteren Wiederholungen an der
Labortür. Nach einem Fehlschlag erst auswerten, dann gezielt nachbessern.

## 10. Fahrplan

Je Realtest genau eine Verhaltensänderung, Christophers Ja vor jeder Fahrt.

| Schritt | Wo | Was | Änderung am Fahren | Bestanden, wenn |
|---|---|---|---|---|
| 1 Werkzeuge robust | hier (Tests, Simulation) | Signal-Baustein; Aufnahme endet selbst und schreibt immer; Umgebung zuerst prüfen; Ablaufhilfe; Herkunft und Meldungen in Worten; Abstand beim Wiederfinden ausgeben; Belege speichern | keine | 10 von 10 Rundblicken ergeben eine Runde, auch mit Signal mitten im Lesen; alle Tests grün |
| 2 **KI-F9N** Auswerten | Jetson und KI-Rechner, mit Christopher; nur lesen, Stand ohne Motorfreigabe | Protokolle von Lauf 2, 2w2 und 2w3; vor Ort nachsehen (rechts neben dem Rahmen, Fenster, Standorte); je Nummer eintragen, was sie war; Rohtext der Antworten; Signalmessung alt gegen neu; Ablaufhilfe im Vorlauf | keine | je Problem ein Befund mit Zahlen |
| 3 Sehen ohne Roboter | KI-Rechner, gespeicherte Runden; neue Rundblicke nur mit Freigabe des Ortes | Vermessung, Darstellung, Frage, Widerspruchsregel; dann heutiges Modell gegen Qwen3.8-27B; dann zweite Meinung | keine | Lauf 2 ergibt keine Wahl oder die Tür; jede bestätigte Tür wird weiter gewählt; K0-Zählung beginnt |
| 4 **KI-F10** Nachfassen im Stand | Labor | die Regeln des Werkzeugs vor dem Senden: Wiederfinden in Stufen, Wegvarianten mit Ansage, Laserprüfung bis 0,48 m, durch die Tür nur nach frontaler Messung mit zwei Kanten | genau eine: Regeln des Werkzeugs; Erkunder und Schutzkette unverändert, kein Build | 3 von 3 schräge Starts (1,1 bis 1,3 m seitlich, etwa 30°) ohne Umstellen hindurch; Abstand in jedem Lauf ausgegeben |
| 5 **KI-F11** Sehen am Roboter | Labor und Fensterstelle | das in Schritt 3 gewählte Sehen | genau eine | Fenster nie zur Fahrt vorgeschlagen; Tür 3 von 3 |
| 6 Nahsensoren | eigener Auftrag im Sicherheitsbereich | Kette reparieren, wieder an | genau eine | in der Simulation Halt vor einem 20 cm hohen Gegenstand; real 3 von 3 durch die Tür |
| 7 Pause statt Ende | Anschlussstelle im Erkunder, Vorgabe aus | Halt → stehen, bis 30 s warten → dieselbe Etappe weiter | genau eine | tritt jemand kurz davor: hält, fährt danach weiter |
| 8 Flur | Anschlussstellen | Rundblick nach der Durchfahrt (Rückweg bekannt), dann Seitentür mit Nahanfahrt | je eine | erst Simulation mit 1,3-m-Flur, dann 3 von 3 |
| 9 Ja nur noch im Zweifel | – | erst Schattenbetrieb (er sagt, was er ohne Ja täte), dann ohne Ja bei Einigkeit | je Stufe eine | nach Zahlen (Entscheidung 2) |
| 10 KI-3 Wohnung | – | Raum für Raum durch die freigegebenen Räume | – | Kriterien vorab vom Projektinhaber |

Schritte 1 und 3 laufen ohne Roboter und können parallel zu 2 vorbereitet
werden. Schneller fahren (0,08 statt 0,05 m/s) kommt erst danach. In Lauf 1
kosteten Rundblick und Warten auf das Ja mehr Zeit als die Fahrt.

## 11. Entscheidungen für Christopher

1. **Den Weg bestätigen:** zuerst Schritt 1 hier, dann KI-F9N (nichts
   fahren), dann Schritt 3 ohne Roboter, dann KI-F10.
2. **Dein Ja bleibt**, bis Zahlen erfüllt sind. Das ersetzt die Regel
   „zweimal gelungen: Ja entfällt“ in der Arbeitsliste. Vorschlag:
   - K0-1, K0-2, K0-5 und K0-6 bestanden an mindestens 12 Runden, davon
     mindestens 3 mit Fenster, Glas oder Spiegel und 2 ohne echten Ausgang;
   - danach ein Schattenbetrieb ohne Widerspruch;
   - jede gefährliche Wahl führt sofort zurück zum Ja.
   Wie streng, entscheidest du: Null Fehler in 12 Runden begrenzen die
   Fehlerrate (95 % sicher) nur auf unter 22 %, in 60 Runden auf unter 5 %.
3. **Nachfassen** als Selbstheilung der KI-Linie, zuerst nur im Werkzeug im
   Stand. Grenzen: höchstens 3 Messungen, höchstens 3-mal 10 s Warten, eine
   Korrektur-Anfahrt als weiteres Ziel.
4. **Erkunder und Schutzkette jetzt nicht ändern.** Kein kürzeres Fenster am
   Streckenende. „Pause statt Ende“ kommt später als eigene Anschlussstelle,
   nach den Nahsensoren.
5. **Modellversuch auf dem KI-Rechner:** Qwen3.8-27B herunterladen (18 GB)
   und offline vergleichen. Während der Messung wird der Planer der
   Hauptlinie mit `ollama stop` entladen, nur für die Messung. Über eine
   zweite Meinung (eigener Dienst neben Ollama) erst nach den Zahlen
   entscheiden.
6. **Orte für Rundblicke ohne Fahrt:** die Fensterstelle als feste
   Prüfstelle (Rollo oben, halb, unten, bei Tag und bei Nacht), später Flur
   und ein zweites Zimmer.
7. **Nahsensoren reparieren** als eigener Auftrag im Sicherheitsbereich,
   bevor es in die Wohnung geht.
8. **Flur:** zuerst eine Nahanfahrt für Seitentüren ohne Nav2, erst in der
   Simulation. Nav2 erst nach einer lesenden Auswertung, warum es seit
   Mitte November kein Ziel mehr erreicht.
9. **Kleinigkeiten:**
   - MASTERPLAN §10, Regel 5 („entscheidet die vorhandene Regel“) an deine
     Festlegung vom 21.11. angleichen: kein stiller Rückfall.
   - Die Prozentangabe der KI aus der Nachricht an dich nehmen.
   - Den F0-Text zur Sicht ohne Nahsensoren berichtigen (Abschnitt 8).

**Was nur du vor Ort klären kannst** (Teil von KI-F9N):
- Was steht vom Labor aus rechts neben dem Rahmen der Labortür? Wie tief
  ab der Wand, wie weit vom Rahmen, höher als 75 cm?
- Wo standest du in 2w2 und 2w3 beim Rundblick und beim „ja“? Etwa 1,9 m
  links von Amadeus, auf Höhe seines Hecks? Hast du ihn zwischen den
  beiden Läufen versetzt? Gemessen sind rund 12 cm.
- Wie hoch liegen am Fenster die Unterkante der Scheibe und die des Rollos?
  Steht davor etwas, ein Regal zum Beispiel?
- Wo sitzt der Not-Aus: am Gehäuse, an einem Kabel oder als Funktaster?
- Was war jede Nummer der KI-F9-Runden? Besonders Nr. 2 in Lauf 1 („offene
  Tür“, 152° links).

## 12. Was diese Bewertung nicht belegt

- Den Gegenstand rechts neben dem Rahmen hat niemand gesehen; auch ein
  beweglicher (Stuhl, Person) passt.
- Ob in 2w2 ein Mensch oder ein festes Ding an der Stelle stand.
- Welche der zwei Erklärungen für die Doppelnummer in Lauf 2 zutrifft; das
  Protokoll ist noch nicht gelesen.
- Ob Qwen3.8-27B die Fehlwahl vermeidet und ob es neben den Diensten der
  Hauptlinie ganz in den Grafikspeicher passt.
- Ob die zweiten Meinungen auf den eigenen kleinen Nachtbildern taugen; Werte
  je Klasse gibt es nur von fremden Modellen.
- Der Absturz unter Humble ist aus Quelltext, Fehlermeldung und einer
  Nachstellung unter der neueren ROS-Fassung belegt, am Jetson selbst noch
  nicht nachgestellt.
- Warum der Weg laut Karte je Etappe 8 bis 20 % länger ist als laut Laser.
  Das war nicht die Ursache, kostet aber Spielraum.
- Die vorgeschlagenen Grenzwerte (0,30 m seitlich, bis 0,60 m Tiefe) stammen
  aus einem Fall und werden vor dem Realtest an allen gespeicherten
  Anfahrten nachgerechnet.
