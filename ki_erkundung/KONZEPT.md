# Konzept „KI-Erkundung“ – eine KI übernimmt Ziel- und Suchwahl

**Version 1.11 · 22.11.2026 · Entscheidung des Projektinhabers vom 19.11.2026,
nachgeführt nach drei Durchgängen an echten Aufnahmen, der Freigabe der
Schalter „nur Rundblick“ und „Etappenfahrt“ und der Festlegung „die KI
bekommt Zeit, kein stiller Rückfall“**

Dieses Dokument ist die verbindliche Beschreibung der zweiten
Entwicklungslinie. Verankert in MASTERPLAN §10. Den aktuellen Stand führt nur
[STATUS.md](STATUS.md). Die Übernahme dieses Konzepts ist keine Software- oder
Realabnahme.

## 0. In Kürze

Amadeus dreht sich beim Betreten eines Raums einmal, nimmt dabei Bilder auf
und schickt sie an den KI-Rechner im Haus. Die KI erkennt Türen und
Durchgänge, ordnet ein, was sie sieht, und entscheidet, wohin Amadeus als
Nächstes fährt und wo er weitersucht. Der Roboter prüft die Wahl mit seinen
Messungen, fährt selbst und behält seine ganze Schutzkette.

**Die KI wählt, die Vermessung prüft, die Schutzkette fährt.**

| | Bisher (Hauptlinie) | Diese Linie |
|---|---|---|
| Wohin als Nächstes? | feste Regeln über Kartenränder und Lücken | die KI, anhand von Bildern und vermessenen Vorschlägen |
| Was ist eine Tür? | nur Geometrie (Lücke in der Karte) | die KI sieht es; das LiDAR misst Breite und Lage |
| Ist der Raum fertig? | Schwellen (Anteil, Zeit, Weggewinn) | die KI beurteilt es, die Karte bestätigt |
| Fahren, Abstand, Bremsen | Nav2, Fahrtor, Kollisionsmonitor, VL53, Not-Aus | Fahrtor, Kollisionsmonitor, VL53 und Not-Aus **unverändert dieselben**; gefahren wird zuerst ohne Nav2 in kurzen geraden Etappen (Abschnitt 6a) |

## 1. Anlass und Entscheidung

Am 18./19.11.2026 hat der Projektinhaber festgestellt, dass die Erkundung
bisher nur nach festen Regeln arbeitet, und entschieden:

- Eine KI soll die **Ziel- und Suchfunktion** übernehmen, auf Grundlage von
  Kamerabildern einer Blickrunde.
- Das wird eine **komplett neue Entwicklungslinie in einem eigenen Ordner**.
  Die bisherige Entwicklung darf dadurch weder verloren gehen noch
  beeinflusst werden.
- Ausgewertet wird auf dem **vorhandenen KI-Rechner** des Projektinhabers.
- Der Realtest SH-9 der Hauptlinie läuft parallel weiter.

Klarstellungen des Projektinhabers vom 19.11.2026 (abends), eingearbeitet in
Version 1.1:

- **Kein Joystick.** Amadeus dreht sich für die Blickrunde selbst.
- **Der KI-Rechner wird nur eingeschaltet.** Die Verbindung baut sich von
  selbst auf, wie bei der Objekterkennung; Aufnahmen werden nicht von Hand
  kopiert.
- Als Quelle liegt sein Konzept „HomeMy – lokale semantische
  Roboternavigation nach dem Mobility-VLA-Prinzip“ unter
  [quellen/](quellen/). Was daraus übernommen ist, steht in Abschnitt 13.

Ehrliche Einordnung, wie am 18.11. besprochen: Die letzten Fehlschläge der
Hauptlinie lagen nicht an falschen Zielen. In W-1 lagen 10 von 12 Anläufen an
der Tür; sie war gefunden, die Durchfahrt gelang nicht. In der zweiten Fahrt
hinkte die Ortung beim Drehen hinterher. Die KI löst diese beiden Punkte
nicht (Abschnitt 9). Sie ersetzt den Teil, der in den Wochen davor am meisten
Nachstellen gebraucht hat: die Regeln der Zielwahl.

## 2. Zielbild

Aus einer normalen Startposition in einer unbekannten Wohnung:

1. **Schauen.** Amadeus dreht sich und nimmt eine Blickrunde auf.
2. **Verstehen.** Die KI sagt, was für ein Raum das ist und was jede
   vermessene Öffnung ist: offene Tür, geschlossene Tür, Durchgang, Glas,
   Spiegel, Spalt neben einem Möbel.
3. **Entscheiden.** Die KI wählt das nächste Ziel: durch welche Öffnung
   weiter, wo in diesem Raum noch gesucht wird, oder dass der Raum erfasst
   ist.
4. **Prüfen und fahren.** Der Roboter misst die Wahl nach und fährt mit der
   vorhandenen Navigation und Schutzkette.
5. **Merken.** Was erreicht wurde und was nicht, geht in die nächste Frage
   ein. Besuchte Räume und ihre Namen bleiben erhalten.

Am Ende steht eine Karte mit benannten Räumen. Sie ist die Grundlage für das
spätere „fahr ins Schlafzimmer“.

Die Produktvorgabe der Hauptlinie gilt weiter: Ein Raum darf bei 80–85 % als
erfasst gelten; ohne Fortschritt wird dort nicht weitergesucht.

## 3. Rollen und feste Grenzen

| Teil | Wo | Aufgabe | Darf nicht |
|---|---|---|---|
| **Lotse** (die KI) | KI-Rechner | sehen, einordnen, wählen, begründen | Fahrbefehle senden; Sicherheitsgrenzen ändern; Daten nach außen geben |
| **Vermessung** | Roboter | Vorschläge mit echten Maßen liefern (LiDAR, Karte); die Wahl der KI nachmessen | eine Wahl ausführen, die nicht angeboten war oder nicht befahrbar ist |
| **Navigation und Schutzkette** | Roboter | fahren, Abstand halten, bremsen, stoppen | von der KI umgangen oder abgeschwächt werden |
| **Regel-Rückfall** | Roboter | entscheiden, wenn die KI fehlt oder Unbrauchbares antwortet; **nur, wenn er ausdrücklich eingeschaltet ist** (Vorgabe aus) | still übernehmen: Jede Entscheidung nennt sichtbar, wer sie getroffen hat |

Feste Grenzen (MUSS):

- Die KI ist **zustandslos**: Jede Frage enthält alles Nötige (Bilder,
  Vorschläge, bisheriger Verlauf). Das Gedächtnis liegt beim Roboter. So ist
  jede Entscheidung nachvollziehbar und mit gespeicherten Fragen
  wiederholbar.
- Die KI wählt **nur aus angebotenen Nummern**. Freie Koordinaten oder
  Fahranweisungen nimmt der Roboter nicht an.
- Jede Antwort wird **geprüft** (Abschnitt 6). Eine verworfene Antwort führt
  nie zu einer Fahrt.
- Die KI ist **nie die einzige Schutzmaßnahme**. Meldet sie eine Gefahr
  (Treppe, Kabel, Glas), ist das ein Hinweis zusätzlich zur Sensorik, kein
  Ersatz.
- **Kein zweiter Navigator, kein zweiter Supervisor** (MASTERPLAN §4). Es
  fährt weiter genau ein Besitzer der Navigation.
- **Ohne KI bleibt Amadeus fahrfähig**, aber nie unbemerkt: Die bisherige
  Erkundung bleibt erhalten und umschaltbar; sie übernimmt nur, wenn sie
  ausdrücklich eingeschaltet ist, und das ist dann sichtbar (Abschnitt 6).
  Raumsemantik ist Zusatznutzen, keine versteckte Pflicht.
- **Bilder bleiben im Haus** (README, Regel 6).

## 4. Ablauf im Betrieb (Zielzustand ab Stufe KI-3)

```
 Raum betreten ─► Blickrunde ─► Vorschläge vermessen ─► Frage an den Lotsen
                                                              │
        ┌─────────────────────────────────────────────────────┘
        ▼
   Antwort prüfen ──unbrauchbar/keine──► noch einmal fragen; bleibt es
        │ gültig                         dabei: stehen bleiben und melden
        │                                (Regel-Rückfall nur, wenn eingeschaltet)
        ▼
   Wahl nachmessen (Breite, Erreichbarkeit, Fahrbereich)
        │ in Ordnung                       │ nicht befahrbar
        ▼                                  ▼
   fahren mit Navigation            Ergebnis merken, nächste Frage
   und Schutzkette
        │
        ▼
   Ergebnis merken ─► neuer Raum: Blickrunde · sonst: nächste Frage
```

**Ankunft bestätigen.** Nach einer Durchfahrt prüft Amadeus vor Ort, ob er
dort ist, wo die KI ihn hinschicken wollte (neuer Raum, anderes Bild). Ein
Ziel gilt erst nach dieser Prüfung als erreicht; ohne Bestätigung bleibt es
eine Vermutung.

**Wann gefragt wird** (damit die Bildrunde nicht nach jedem Ziel läuft):

- beim Betreten eines Raums (einmal je Raum eine volle Blickrunde),
- wenn ein gewähltes Ziel nicht erreicht wurde,
- wenn ohne Fortschritt gesucht wird (das Signal dafür gibt es schon: EK-1 D),
- vor dem Ende der Erkundung („gibt es noch einen Ausgang, der fehlt?“).

**Zeitbedarf (Rechnung, noch nicht gemessen):** Eine volle Drehung dauert
beim heutigen Drehtempo des Rundblicks (0,10 rad/s) gut eine Minute. Die
Antwort der KI soll im Mittel unter 20 Sekunden kommen (Kriterium K0-4).

## 5. Die Blickrunde und die vermessenen Vorschläge

**Bilder.** Acht Bilder im Abstand von 45°. Vier Bilder reichen nicht: Die
Kamera sieht nach Datenblatt rund 69° breit, zwischen vier Bildern blieben
Lücken von gut 20°. Mit acht Bildern ist jede Richtung in zwei Bildern zu
sehen.

**Was die Kamera sieht (Rechnung aus Montage und Datenblatt, in KI-0
nachzumessen).** Die OAK-D-S2 sitzt 1,34 m hoch, 0,15 m vor der Antriebsmitte
und ist 18,94° nach unten geneigt. Der Bildstrom zum KI-Rechner hat 640 × 360
Punkte (gemessen am 21.11.2026: 320 × 180, waagerecht 63,9°, senkrecht
38,7°). Daraus folgt: Der Boden ist ab etwa 1,6 m vor der Kamera im Bild; nach
oben reicht das Bild nur knapp über die Waagerechte (in 3 m Entfernung bis
etwa 1,45 m Höhe). Türstürze und Zimmerdecken sind also nicht zu sehen,
Türpfosten, Schwellen, Türblätter und der Boden dahinter schon. Ob das der
KI genügt, ist die erste Frage an KI-0.

**Vorschläge.** Das LiDAR (0,75 m hoch, 292° Sichtfeld, 0,245 m vor der
Antriebsmitte) liefert während der Drehung Scans. Aus ihnen wird zuerst der
Drehwinkel jeder Aufnahme bestimmt (die Odometrie dient nur als Startwert),
dann ein Rundum-Profil des Standpunkts.
Eine **Öffnung** ist eine Lücke von 0,55 bis 2,5 m zwischen zwei Kanten,
hinter der es frei weitergeht: quer zur Lücke gemessen im Mittel mindestens
0,6 m, damit das 0,42 m lange Gehäuse hineinpasst. Eine flache Schranknische
zählt nicht. Jede Öffnung bekommt eine Nummer und ihre Maße: Breite,
Entfernung, Richtung, freie Tiefe. Unter 0,60 m Breite wird sie gezeigt,
aber als zu schmal vermerkt.

Seit dem ersten echten Lauf (21.11.2026) gilt dazu:
- **Offenes Türblatt.** Von der Scharnierseite endet die sichtbare Lücke an
  der Spitze des Türblatts, nicht am Türpfosten. Das Blatt wird deshalb bis
  zur Wand verfolgt; der zweite Pfosten ist das Scharnier, die lichte Breite
  der Abstand des sichtbaren Pfostens zum Blatt. Die Nummer steht auf dem
  Stück der Schwelle, das vom Standpunkt aus zu sehen ist.
- **Türgroß vor breit.** Lücken bis 1,3 m gelten als türgroß. Hinter einer
  breiteren Lücke (freier Raum zwischen Möbeln) wird weitergesucht; liegt
  dort eine türgroße, wird sie angeboten und die breite nicht.
- **Im Stand vom Ort des LiDAR aus.** Ohne Drehung wird das Profil vom Ort
  des LiDAR aus gebildet, nicht von der Antriebsmitte: Was das LiDAR nie
  gesehen hat, darf nicht als frei gelten.
- **Jede geprüfte Lücke wird vermerkt,** mit Maßen und dem Grund, aus dem
  sie angeboten oder verworfen wurde. Ohne das ist an echten Aufnahmen nicht
  zu sehen, warum eine Tür fehlt.
- **Im Stand wird direkt gemessen (seit KI-0N).** Je Richtung zählt der
  Median aller Messungen. Ein Raster verschiebt bei echtem Messrauschen die
  Wandpunkte um einige Zentimeter; gerade Wände gelten dann als krumm, und
  Türen werden zu schmal oder zu breit vermessen. Nach einer Drehung wird
  vorerst weiter gerastert.

**Nummern im Bild.** Jede Nummer wird an der vermessenen Stelle in die Fotos
gezeichnet (am Boden der Öffnung) und in eine Kartenskizze von oben. Grund:
Bild-Sprach-Modelle sind unzuverlässig bei Meterangaben, aber gut darin,
zwischen markierten Stellen zu wählen.

**Später** kommen als Vorschläge die Ziele hinzu, die die
vorhandene Erkundung ohnehin bildet (Ränder zum Unbekannten). Dann kann die
KI auch entscheiden, wo im Raum weitergesucht wird.

## 6. Frage, Antwort und Prüfung

**Frage an den Lotsen** (Fassung 1, für den Trockenlauf):

- die acht Fotos mit eingezeichneten Nummern, in Drehrichtung,
- die Kartenskizze,
- eine Tabelle der Vorschläge (Nummer, Breite, Entfernung, Richtung, in
  welchen Bildern zu sehen),
- der bisherige Verlauf an diesem Standpunkt (im Trockenlauf leer),
- die Aufgabe: Raum verlassen, um weitere Räume zu erkunden.

**Antwort** (JSON, Fassung 1):

```json
{
  "wahl": 2,
  "begruendung": "Nummer 2 ist eine offene Zimmertür, dahinter Flurboden.",
  "kandidaten": [
    {"nr": 1, "art": "moebelspalt", "sicherheit": 0.8},
    {"nr": 2, "art": "tuer_offen", "sicherheit": 0.9}
  ],
  "raum": "Arbeitszimmer",
  "gefahren": []
}
```

`wahl` ist eine angebotene Nummer oder `null` („kein geeigneter Ausgang“).
Wählbar sind nur Nummern, die in einem Foto stehen: Was nur der Laser kennt,
kann die KI nicht beurteilen (seit KI-0N).
`art` ist eines von: `tuer_offen`, `tuer_geschlossen`, `durchgang`, `glas`,
`spiegel`, `moebelspalt`, `nische`, `wand`, `unklar`. `wand` heißt: Die
Nummer steht auf einer Wand, dort ist keine Öffnung. Damit kann die KI einen
Fehler der Vermessung benennen.

**Prüfung der Antwort** (auf dem Roboter; im Trockenlauf dieselbe Prüfung):

| Fall | Folge |
|---|---|
| kein lesbares JSON | verworfen |
| `wahl` ist keine angebotene Nummer | verworfen |
| `wahl` ist eine Nummer, die in keinem Foto steht | verworfen |
| die KI ordnet ihre eigene Wahl als nicht befahrbar ein (geschlossene Tür, Glas, Spiegel, Möbelspalt, Nische) | verworfen |
| unbekannte `art` | wird zu `unklar`, Antwort bleibt gültig |
| `wahl` als Text statt Zahl („2“) | toleriert und gezählt |
| Antwort später als die Zeitgrenze | verworfen |

Danach misst die Vermessung die gültige Wahl nach: Öffnung breit genug
(Vorgabe 0,60 m bei 0,46 m Gehäusebreite), erreichbar, im freigegebenen
Fahrbereich. Erst dann wird gefahren.

**Die KI bekommt Zeit; es gibt keinen stillen Rückfall** (Festlegung des
Projektinhabers, 21.11.2026). Amadeus steht, während die KI überlegt; Warten
kostet nichts und ist ungefährlich. Deshalb gilt:

- Die Zeitgrenze je Frage ist großzügig: **120 s**. Gemessen wurden in KI-1
  für neun Bilder 4,9 s, davon 2,7 s für das erneute Laden des Modells; die
  Grenze liegt damit beim Mehr als Zwanzigfachen. Das Kriterium K0-4 (Median 20 s, längste 45 s)
  bewertet die KI und ist nicht die Grenze, nach der Amadeus aufgibt.
- Kommt keine oder keine brauchbare Antwort, wird dieselbe Frage bis zu
  zweimal erneut gestellt.
- Bleibt es dabei, **bleibt Amadeus stehen und meldet das** („die KI hat
  nicht geantwortet“ mit dem Grund). Er fährt dann nicht nach der alten
  Regel weiter.
- Der Regel-Rückfall ist ein eigener Schalter, Vorgabe aus. Ist er
  eingeschaltet, steht bei jeder Entscheidung dabei, wer sie getroffen hat
  (KI, Regel oder niemand): in der Statusmeldung, im Lotsen-Fenster und im
  Bericht. So kann eine Fahrt nie wie eine KI-Fahrt aussehen, die keine war.

## 6a. Der Fahrteil: Etappenfahrt ohne Nav2 (seit v1.6)

Entscheidung des Projektinhabers vom 21.11.2026: Der Fahrteil entsteht aus
Code, der schon real funktioniert hat, und zwar **zuerst ohne Nav2, vom
Einfachen zum Schwierigen**. Nav2 kommt nur dazu, wenn das nicht reicht.
Grund: Alle früher gelungenen Türdurchfahrten fuhren über Nav2, und genau
dieses Fahren erreichte am 19.11. kein Ziel; die einzelnen Bausteine
darunter (Drehen auf der Stelle, eine gerade, vom Laser gemessene Etappe)
haben am 10./11.09.2026 je für sich real bestanden und stehen fast
unverändert im heutigen Erkunder.

So läuft es:

1. Die KI nennt eine Nummer; die Antwort ist geprüft (Abschnitt 6).
2. **Anfahrt (seit v1.10):** Steht der Roboter nicht passend vor der
   gewählten Tür, fährt er selbst dorthin: zu einem Vorpunkt auf der
   Türachse gut zwei Meter vor der Tür, dreht sich dort zur Tür und fährt
   0,45 m auf sie zu (`anfahrt`, im Werkzeug `--vor-die-tuer`). Danach steht
   er 1,6 bis 2,1 m mittig davor, Blick zur Tür. Die Türachse nimmt er dafür
   aus der **geraden Wand neben der Tür**, nicht aus den zwei Türkanten:
   Schräg gesehen ist die Verbindung der Kanten verdreht (Simulation: 6°,
   das sind 17 cm neben der Türmitte). Geprüft wird am Laserbild: neben
   jeder Strecke 0,30 m frei, an jeder Drehstelle ein freier Kreis von
   0,45 m, freie Sicht auf die Punkte; was der Laser von dort nicht sieht,
   gilt nicht als frei. Die Anfahrt ist ein eigenes Fahrziel; die
   Durchfahrt danach wird neu vermessen.
3. **Durchfahrt:** Der Roboter misst die Öffnung im Stand neu und legt zwei
   Punkte auf die **gerade Linie von seinem Standplatz durch die
   Türmitte**: einen
   1,2 m vor der Türlinie (dort stellt der Erkunder die Richtung nach) und
   einen 0,6 m dahinter (`lotse/fahrziel.py`). Als Tür gilt dabei nur, was
   0,65 bis 0,95 m breit vermessen ist; der Roboter muss passend davor
   stehen (1,5 bis 2,6 m vor der Türlinie, höchstens 0,25 m neben der
   Türmitte, die Linie höchstens 10° schräg zur Türachse); und **neben der
   Fahrlinie müssen am selben Laserbild links und rechts 0,30 m frei sein**
   (Türblatt, Pfosten, alles, was im Weg steht). Sonst wird nichts gesendet
   und das Werkzeug sagt, was zu ändern ist. Ein Umweg über einen Punkt auf
   der Türachse ist verworfen: Er führte in KI-F2 an der Spitze des offenen
   Türblatts vorbei. (Die Anfahrt aus Schritt 2 fährt auch über einen
   Punkt auf der Türachse, aber gut zwei Meter vor der Tür und geprüft am
   Laserbild; gedreht wird dort, nicht neben dem Türblatt.)
   **Seit v1.11** prüft das Werkzeug vor dem Senden außerdem die
   Kostenkarte auf dem **ganzen Weg** so, wie der Nahbereichs-Halt sie liest
   (Streifen in Fahrzeugbreite, von der Vorderkante bis 0,25 m davor, über
   jede Strecke bis zu ihrem Ende). Ist sie dort belegt, hielte der Erkunder
   an; dann wird nichts gesendet.
4. Diese Punkte gehen als **Fahrziel** an den Erkunder
   (`/ki_erkundung/fahrziel_json`, nur auf dem Roboter). Darin steht, wer
   gewählt hat: `ki`, `mensch` oder `test`.
5. Der Erkunder (Startargument `stage_drive_only`, Vorgabe aus) nimmt genau
   ein Ziel je Auftrag an (Anfahrt und Durchfahrt sind zwei Aufträge
   nacheinander im selben Stacklauf), prüft es (Rahmen, Alter, höchstens drei Punkte,
   je Strecke höchstens 2,5 m, zusammen höchstens 4 m) und fährt selbst:
   auf den Punkt ausrichten, gerade Etappen von höchstens 0,5 m bei
   0,05 m/s, nach jeder Etappe bestätigter Halt und neue Lagemessung. Vor
   jeder Etappe muss der Streifen in Fahrzeugbreite im Laser frei und sein
   Ende gesehen sein, mit 15 cm Reserve vor der Vorderkante. Fahrtor,
   Glätter und Kollisionsmonitor bleiben davor.
6. **Nahbereichs-Halt:** Vor und während jeder Etappe wird die Kostenkarte
   gelesen, in der auch die Treffer der Nahsensoren (VL53) stehen. Liegt
   25 cm vor der Vorderkante etwas Belegtes im Streifen, hält die Etappe an.
   Grund (Simulation, 21.11.2026): Bei 0,05 m/s bremst der Kollisionsmonitor
   erst wenige Zentimeter vor einem Hindernis; einen niedrigen Mülleimer,
   den der Laser nicht sieht, berührte der Roboter ohne diesen Halt im
   Kriechtempo. Für jede belegte Stelle, an der er anhält oder anhalten
   würde, nennt das Werkzeug die Quelle (Karte des SLAM, Nahsensor links
   oder rechts mit Höhe über dem Boden, Laser). Bekannte Eigenschaft:
   Markierungen der Nahsensoren näher als 0,45 m am Sensor werden nicht
   wieder geräumt; das hält niedrige Dinge fest, die der Sensor aus der
   Nähe nicht mehr sieht, und hielte ebenso eine Fehlmessung fest.
7. Scheitert ein Schritt, bleibt Amadeus stehen und der Auftrag nennt den
   Grund. Ein zweiter Versuch ist ein neuer Auftrag.

Grenzen, die bekannt sind: Das geht nur, wenn die geraden Strecken der
Anfahrt und die gerade Linie durch die Tür frei sind; die Etappenfahrt
weicht nichts aus. Von einem Platz, von dem die Tür nicht türbreit
vermessen wird (bisher: von der Seite des offenen Türblatts), gibt es keine
Anfahrt. Niedrige Dinge unter 0,75 m sieht der Laser nicht; vor ihnen schützen
die VL53 über den Nahbereichs-Halt und der Kollisionsmonitor, beide erst
aus der Nähe (die VL53 tragen etwa einen halben Meter weit). Um Möbel herum
braucht es später einen geplanten Weg; dafür liegt der Türablauf vom
11.09.2026 (Vorpunkt und Auslauf über Nav2) unverändert im Erkunder bereit.

## 7. Der KI-Rechner und die Verbindung

**Vorhanden** (im Repository auf `main`, abgenommen am 25.08.2026): ein
Rechner mit RTX 3090 (24 GB) im Haus. Auf ihm laufen in einer eigenen
ROS-Umgebung (RoboStack Humble, Python 3.12) als Dienst `amadeus-ki.service`
bereits zwei KI-Knoten: der Sprachplaner (`llm_planner`, ein Textmodell
`qwen2.5` über Ollama) und die Objekterkennung (`semantic_perception`,
YOLO-World mit einfachem Objektgedächtnis). Der Roboter schickt dafür einen
gedrosselten, komprimierten Kamerastrom (2 Bilder je Sekunde mit Tiefenbild).

**So finden sich Roboter und KI-Rechner:** über ROS 2 DDS im WLAN (gleiche
`ROS_DOMAIN_ID`, CycloneDDS mit festen Gegenstellen), nicht über rosbridge.
rosbridge verbindet die App mit dem Roboter. Auf dem Roboter meldet der
`link_monitor`, ob der KI-Rechner erreichbar ist; die Sicherheit hängt
bewusst nicht davon ab.

**Der Lotse nutzt denselben Weg** (gebaut und in der Entwicklungsumgebung
getestet, `werkzeuge/lotse_dienst.py` und `werkzeuge/ki_verbindung_ros.py`):

- Auf dem KI-Rechner läuft der **Lotsen-Dienst** neben den vorhandenen
  Knoten. Er nimmt eine vorbereitete Frage an, fragt Ollama auf demselben
  Rechner und schickt die Rohantwort zurück. Er beantwortet eine Frage zur
  Zeit.
- Der Roboter bereitet die Frage vor (Fotos mit Nummern, Skizze, Text) und
  prüft die Antwort selbst.
- Zwischen Roboter und KI-Rechner gibt es nur drei eigene Themen mit Text:
  `/ki_erkundung/frage_json`, `/ki_erkundung/antwort_json`,
  `/ki_erkundung/lotse_status_json`. Keine Fahrbefehle, keine Dienste, keine
  Aktionen. Ein viertes Thema, `/ki_erkundung/fahrziel_json`, gibt es nur
  auf dem Roboter (Abschnitt 6a); der KI-Rechner sendet dort nie.
- Kommt keine Antwort (KI-Rechner aus, WLAN weg, Zeitgrenze), ist das ein
  gewöhnliches Ergebnis: Amadeus fragt erneut, bleibt sonst stehen und
  meldet es (Abschnitt 6). Die Regel entscheidet nur, wenn der Rückfall
  eingeschaltet ist.

**Modell.** Der Lotse braucht ein Modell, das Bilder versteht; das
vorhandene `qwen2.5` ist ein reines Textmodell. Kandidaten, geprüft am
19.11.2026 in der Ollama-Bibliothek:

| Modell | Größe | Bemerkung |
|---|---|---|
| `qwen3.5:9b` | 6,6–7,6 GB | Text und Bild; erste Wahl (Vorschlag des Projektinhabers) |
| `qwen3-vl:8b` | 6,2 GB | Text und Bild; Vergleich; braucht Ollama ab 0.12.7 |
| `qwen3.5:27b` | 17–20 GB | zum Vergleich, falls die kleineren nicht genügen; lässt wenig Platz für anderes |

Die Größe ist das Modell auf der Platte, nicht der ganze Bedarf an
Grafikspeicher; Bilder und Kontext kommen hinzu. Welches Modell genügt,
entscheidet die Messung an echten Bildern, nicht die Beschreibung.

**Denkschalter.** Qwen3.5 „denkt“ in der Vorgabe vor der Antwort; das kostet
Zeit. Die Werkzeuge können es ab- oder anschalten (`--denken aus`); beides
wird gemessen.

**Nachvollziehbar.** Jede Ergebnisdatei hält fest, womit geantwortet wurde:
Fassung von Ollama, Kennung (`digest`) und Quantisierung des Modells,
Kontextlänge, Denkschalter. Der Modellname allein genügt nicht.

**Zu beachten.** Die vorhandenen Dienste dürfen nicht gestört werden. Lädt
Ollama ein Bildmodell, kann das Sprachmodell aus dem Speicher fallen; die
erste Antwort danach dauert länger. Große Nachrichten über das WLAN
(eine Frage hat rund 0,5 MB) sind im Stand unkritisch; während der Fahrt
wird ihre Wirkung auf die übrige Verbindung gemessen, bevor sie dort
verwendet werden.

## 8. Stufen, Kriterien, Rückfall

Jede Stufe hat vorab festgelegte Kriterien. Eine Stufe beginnt erst, wenn
die vorige bestanden ist. Auf den Roboter kommt je Realtest genau eine
Verhaltensänderung. KI-0 und KI-1 bilden zusammen den **Trockenlauf**: Die KI
antwortet, aber nichts fährt nach ihrer Antwort.

### KI-0 – Erstes Sehen (im Stand, ohne Bewegung)

Die erste Frage dieser Linie ist: Erkennt das Modell auf dem KI-Rechner an
echten Bildern dieser Kamera überhaupt Türen, und wie lange braucht es?
Dafür muss nichts fahren. Amadeus steht dort, wo er ohnehin steht (zum
Beispiel am Start oder Ende einer Fahrt der Hauptlinie). Kamera und LiDAR
laufen, die Aufnahme dauert einige Sekunden, die Frage geht über die
Verbindung an den Lotsen-Dienst, die Antwort wird geprüft und gespeichert.
Das wird an einigen Stellen und Blickrichtungen wiederholt.

Gemessen wird (noch ohne Bestehen oder Durchfallen bei K0-1, dafür sind es
zu wenige Runden): Kommt eine gültige Antwort (K0-3)? Wie lange dauert sie
mit und ohne Denkschalter (K0-4)? Was sieht die Kamera wirklich (K0-7)?
Stimmt die vermessene Breite an der bekannten 78-cm-Tür? Passen die
Zeitstempel von Kamera und LiDAR zusammen? Dazu der erste Eindruck, ob die
KI die Tür benennt.

### KI-1 – Blickrunden aus eigener Kraft (Mitlauf ohne Wirkung)

Amadeus dreht sich bei einer Erkundungsfahrt der Hauptlinie selbst einmal
herum; die Blickrunde entsteht dabei von selbst und geht an den KI-Rechner.
Die KI beantwortet im Hintergrund dieselben Entscheidungen wie die Regel,
steuert aber nichts. So entstehen die Blickrunden für die Kriterien, ohne
Joystick und ohne Kopieren.

**Seit v1.4 (21.11.2026):** Die Hauptlinie ist geparkt; es gibt keine
Fahrten, bei denen die KI mitlaufen könnte. KI-1 beginnt deshalb mit einer
einzelnen Drehung auf der Stelle, ohne Fahrt (Auftrag KI-1; für die Drehung
gelten die Kriterien R1 bis R6 dort). Woher die zwölf Blickrunden für die
Kriterien unten kommen (weitere Drehungen an anderen Stellen und in anderen
Räumen, jeder neue Raum mit eigener Freigabe), legt der Projektinhaber nach
dem Ergebnis der ersten Drehung fest.

Dafür waren zwei Dinge nötig, die es bis zum 21.11.2026 nicht gab:

- **Die Kamera läuft bei der Erkundung mit.** Sie ist in der automatischen
  Kartierung bewusst abgeschaltet. Deshalb zuerst im Stand messen, dass
  Ortung und Rechenlast des Jetson mit Kamera nicht leiden.
- **Der Rundblick geht einmal ganz herum.** Heute dreht Amadeus am Start und
  an Suchpunkten um 90°; der Wert steht fest im Profil der Hauptlinie und
  lässt sich beim Start nicht von außen setzen. Eine volle Drehung braucht
  deshalb eine kleine Anschlussstelle in der Hauptlinie (ein Startwert, ohne
  den alles bleibt, wie es ist). Das ist eine eigene Änderung der Hauptlinie
  nach README, Regel 2. **Seit 21.11.2026 gibt es sie:** das Startargument
  `initial_scan_only` (Freigabe des Projektinhabers). Mit ihm dreht Amadeus
  einmal abschnittsweise um 360° und bleibt stehen, ohne zu fahren.

Kriterien dieser Stufe (vorab festgelegt), an zusammen mindestens zwölf
Blickrunden aus mindestens zwei Fahrten; der Projektinhaber gibt je Runde
an, welche Nummern echte Ausgänge sind:

| Kennung | Kriterium |
|---|---|
| K0-1 Ausgang | In mindestens 90 % der Runden wählt die KI richtig: einen echten, offenen Ausgang, wenn einer angeboten ist, und nichts, wenn keiner angeboten ist. Ein Urteil gibt es ab zehn Runden mit angebotenem Ausgang |
| K0-2 Keine gefährliche Wahl | Nie wählt die KI eine Nummer, die in Wahrheit Glas oder Spiegel ist. Bestanden ist das nur, wenn Glas oder Spiegel unter den Vorschlägen war |
| K0-3 Form | Höchstens 10 % der Antworten werden von der Prüfung verworfen |
| K0-4 Zeit | Antwortzeit im Mittel (Median) höchstens 20 s, längste höchstens 45 s, bei geladenem Modell; zusätzlich wird der Wert genannt, den 95 % der Antworten einhalten |
| K0-5 Wiederholbarkeit | Zwei getrennte Aufnahmen derselben Ansicht: in mindestens 90 % der Paare dieselbe Wahl |
| K0-6 Vorschläge | In mindestens 90 % der Runden, in denen ein Ausgang zu sehen ist, ist er unter den vermessenen Vorschlägen (misst die Vermessung, nicht die KI) |
| K0-7 Kamera | Sichtfeld aus den Kameradaten bestimmt; Rechenlast der Kamera auf dem Jetson gemessen (nur Messung) |

Dazu: keine messbare Verschlechterung der Hauptlinie durch Kamera und
Verbindung. Besteht K0-6 nicht, wird zuerst die Vermessung verbessert.
Besteht K0-1 mit keinem Modell, das auf den KI-Rechner passt, ist das der
Blocker dieser Linie; dann wird nichts in Richtung Fahren gebaut.

### KI-2 – Kopplung in der Simulation

Im vorhandenen Simulationsaufbau wählt eine gespielte KI: richtig, falsch,
langsam, stumm, Unsinn. Kriterien: keine zusätzlichen Berührungen gegenüber
dem Vergleichslauf; bei stummer oder unbrauchbarer KI bleibt Amadeus stehen
und meldet es, mit eingeschaltetem Rückfall übernimmt die Regel sichtbar;
dasselbe gescheiterte Ziel wird nicht beliebig oft wiederholt; die Fahrt
endet ordentlich. Die Simulation hat keine Kamera; sie prüft die Kopplung,
nicht das Sehen.

**Stand 21.11.2026:** Entschieden ist der Anschluss über die Etappenfahrt
(Abschnitt 6a). Sie ist gebaut und in der Simulation mit richtig gewähltem
Ziel gelaufen; die Fälle falsch, langsam, stumm und Unsinn stehen aus.

Vor KI-2 ist zu entscheiden, wie die Wahl an die vorhandene Erkundung
angeschlossen wird (README, Regel 2). Bis dahin wird kein bestehender Code
angefasst.

### KI-3 – Die KI wählt (Realtest, eine Verhaltensänderung)

Laborraum, Flur, Schlafzimmer, begleitet. Kriterien wie beim Vergleichslauf
der Hauptlinie (SH-9), dazu der Vergleich mit dessen Ergebnis. Fahrbereich
und Freigabe legt der Projektinhaber vorher fest.

### KI-4 – Raumnamen und Hilferuf

Raumnamen der KI erscheinen als Vorschlag im Raumeditor der App; der Mensch
bestätigt. Ein Hilferuf enthält Grund und Bild.

### KI-5 – Gegenstände finden („Fahre zur Tasse“)

Fernziel, erst nach einer verlässlichen Erkundung: Ein Auftrag in Worten
führt zu einem Gegenstand. Die Bausteine gibt es bei Amadeus schon
(Sprachplaner, Objekterkennung mit 3D-Lage aus dem Tiefenbild, einfaches
Objektgedächtnis, Raumziele); diese Stufe verbindet sie und übernimmt aus
dem HomeMy-Konzept: letzte Sichtung mit Zeit und Zustand (bestätigt,
veraltet, unbekannt), Prüfung vor Ort vor der Erfolgsmeldung, Tiefe über die
Fläche des Gegenstands statt nur an der Bildmitte, und „nicht gefunden“
statt einer erfundenen Lage.

**Rückfall je Stufe:** KI-0 bis KI-2 verändern das Fahrverhalten nicht; es
gibt nichts zurückzunehmen. Ab KI-3 ist die KI-Wahl ein Schalter, der
standardmäßig aus ist. Rückfall der ganzen Linie: README.

## 9. Was diese Linie nicht löst

- **Die Türdurchfahrt.** 78 cm Tür, 46 cm Gehäuse: rund 15 cm Luft je Seite.
  Das ist Regelung viele Male je Sekunde; die KI braucht Sekunden je Antwort.
  Die Korrektur der Durchfahrt bleibt Arbeit der Hauptlinie (MASTERPLAN §9.2)
  und ist Voraussetzung dafür, dass KI-3 mehrere Räume erreicht. Die KI hilft
  dabei mittelbar: Sie sagt, welche Öffnung die Tür ist.
- **Die blinde Rückseite** und **die nachhinkende Ortung beim Drehen.**
- **Irrtümer der KI.** Bild-Sprach-Modelle liegen gelegentlich mit voller
  Überzeugung falsch. Deshalb Prüfung und Nachmessen (Abschnitt 6).
- **Die Erkundung selbst.** Das Vorbild Mobility VLA erkundet nicht: Dort
  wird die Umgebung dem Roboter vorher in einer Führung gezeigt (ein
  aufgenommenes Video), die KI sucht danach nur das Ziel in diesem Video.
  Selbstständiges Finden in unbekannter Umgebung ist auch in der Forschung
  noch unsicher: Die im HomeMy-Konzept genannte Arbeit LocalNav berichtet
  für ein kleines lokales Modell ohne Nachtraining 26 % Erfolg bei der
  Suche nach Gegenständen in fremden Wohnungen, mit Nachtraining 37 %, für
  ein großes Cloud-Modell 42 %. Diese Linie stellt der KI deshalb eine
  engere Frage (eine Nummer aus vermessenen Öffnungen wählen) und misst
  das Ergebnis, bevor sie ihm folgt.

## 10. Nicht-Ziele

- Keine KI, die aus Bildern direkt die Motoren steuert.
- Kein Cloud-Dienst für Bilder der Wohnung.
- Keine dritte Gesamtsoftware, kein eigener Navigator oder Supervisor.
- Keine Änderung an Kalibrierung, Sensor-Frames, Motorsteuerung,
  Kollisionsmonitor oder Netzwerk durch diese Linie.
- Kein Ersatz der Hauptlinie: Sie bleibt erhalten und umschaltbar.

## 11. Bekannte Risiken und offene Punkte

| Punkt | Stand |
|---|---|
| Blick der Kamera nach unten (kein Türsturz im Bild) | Rechnung; wird in KI-0 gemessen |
| Rechenlast der Kamera auf dem Jetson neben der Kartierung | gemessen in KI-1 (21.11.): Last 11, 29 % Leerlauf, Kamera 11 % eines Kerns; Bilder 2,0 Hz und Scans über 9,4 Hz auch in der Drehung, keine veralteten Transformationen |
| Eine volle Blickrunde dauert gut eine Minute und belastet die Ortung (viele Drehschritte) | gemessen in KI-1: 81 s für 363°, Endpunkt 8 mm neben dem Start; nur einmal je Raum und im Zweifel |
| Auswahl des Bild-Sprach-Modells | Kandidaten in Abschnitt 7; KI-0 und KI-1 messen sie |
| Anschlussstelle für die volle Drehung am Start (KI-1) | gebaut am 21.11.2026 (`initial_scan_only`, Vorgabe aus); in Tests und Simulation gelaufen, am Roboter noch nicht |
| Große Nachrichten über das WLAN während der Fahrt | im Stand unkritisch; vor KI-1 messen |
| Personen im Bild und im Scan (Begleitung mit Not-Aus) | können als falsche Öffnung erscheinen; in KI-1 war Christopher auf einem Foto, bekam aber keine Nummer. Ein einzelner Befund |
| Breite der Öffnungen | in der künstlichen Beispielwelt 3–7 cm zu schmal gemessen (vorsichtige Seite); an der Labortür (850 mm laut Projektinhaber) am 21.11.2026 von vorn 0,74 und 0,73 m, von der Seite 1,22 und 1,76 m; Nachbesserung in §5, Prüfung an den Aufnahmen offen |
| Öffnung bei sehr flachem Blick (Standpunkt dicht an der Wand) | wird nicht angeboten, weil die freie Tiefe dahinter nicht zu sehen ist; zählt in K0-6 |
| Zeitstempel von Kamera und LiDAR am echten Roboter | Zuordnung Bild zu Scan nach Stempel (höchstens 0,15 s Abstand); erst in KI-0 prüfbar |
| Anschluss an die vorhandene Erkundung | offen; Entscheidung vor KI-2 |
| Späteres Kundengerät ohne eigenen KI-Rechner | Produktfrage, nicht Teil dieser Stufen |

## 12. Änderungsprotokoll

- 19.11.2026, v1.0: Erstfassung nach Entscheidung des Projektinhabers
  (eigene Linie, eigener Ordner, vorhandener KI-Rechner, SH-9 parallel).
- 19.11.2026, Nachtrag am selben Tag: Regel für Öffnungen in §5 nach den
  ersten Tests genauer gefasst; drei Punkte in §11 ergänzt. Keine Änderung
  an Rollen, Grenzen, Stufen oder Kriterien.
- 19.11.2026, v1.1 (Klarstellungen des Projektinhabers und sein
  HomeMy-Konzept): kein Joystick, Amadeus dreht sich selbst; Verbindung zum
  KI-Rechner wie bei der Objekterkennung, mit eigenem Lotsen-Dienst (§7);
  KI-0 ist jetzt „Erstes Sehen im Stand“, KI-1 „Blickrunden aus eigener
  Kraft“ mit den Kriterien K0-1 bis K0-7; neu KI-5 Gegenstände finden;
  Modellkandidaten, Denkschalter und nachvollziehbare Modellangaben; Ankunft
  bestätigen (§4); Einordnung von Mobility VLA und LocalNav (§9); §13.
  Rollen, Grenzen und Schwellen der Kriterien unverändert.

- 19.11.2026, Nachtrag nach dem ersten echten Lauf (Teil A von KI-0):
  K0-5 neu gefasst. Dieselbe Frage mehrfach zu stellen misst nichts: Bei
  Temperatur 0 und Zwischenspeicher des Dienstes kommt dieselbe Antwort in
  1,3 s statt 17 s. Gemessen wird jetzt an zwei getrennten Aufnahmen
  derselben Ansicht; die Schwelle bleibt 90 %. K0-4 zählt nur die erste
  Antwort je Frage.
- 21.11.2026, v1.2, nach dem ersten echten Lauf am Roboter (Teil B von
  KI-0): §5 um vier Regeln der Vermessung ergänzt (Türblatt, türgroß vor
  breit, im Stand vom Ort des LiDAR aus, Vermerk jeder geprüften Lücke).
  K0-1 strenger gefasst: Es zählen alle Runden; wo kein Ausgang angeboten
  ist, ist nur „keine Wahl“ richtig. Anlass: Die KI wählte eine Möbellücke
  als Durchgang, und die Zählung ließ das aus. K0-2 gibt nur ein Urteil,
  wenn Glas oder Spiegel unter den Vorschlägen war. Schwellen unverändert.
  Der Denkschalter bleibt aus (langsamer, einmal ohne brauchbare Antwort,
  in der Wahl nicht besser). Rollen, Grenzen und Stufen unverändert.
- 21.11.2026, v1.3, nach dem zweiten Durchgang (KI-0N): **Die Frage der
  Stufe KI-0 ist beantwortet.** Gültige Antworten: ja (0 von 11 verworfen).
  Zeit: Median 1,6 s ohne Denken. Kamera: 320 × 180, waagerecht 63,9°.
  Zeitstempel von Bild und Scan passen (kein Paar verworfen). Erster
  Eindruck: Hat die Tür eine Nummer und ist sie im Foto, wählt die KI sie
  (sechs von sechs). Breite der bekannten Tür: von vorn 0,71 bis 0,77 m
  bei wahren 0,85 m. Die Kriterien K0-1 bis K0-6 gehören zu KI-1 und sind
  nicht entschieden. Neu in §5: im Stand direkt messen. Neu in §6: Einordnung
  `wand`; wählbar sind nur Nummern im Foto. Die Angaben des Menschen gelten
  für die Lage der Öffnungen, nicht für ihre Nummern. KI-1 soll den
  vorhandenen Rundblick der Hauptlinie nutzen (8 × 45°); die dafür nötige
  Einstellung „nur Rundblick“ ist eine Änderung der Hauptlinie und wartet
  auf die Entscheidung des Projektinhabers.
- 21.11.2026, v1.4: **KI-1 beginnt mit einer Drehung ohne Fahrt.** Statt
  eines Mitlaufs bei Fahrten der Hauptlinie (die geparkt ist) dreht sich
  Amadeus mit dem neuen, vom Projektinhaber freigegebenen Startargument
  `initial_scan_only` einmal um sich selbst und bleibt stehen. Die Kamera
  läuft dabei getrennt neben dem Kartier-Stack; das wird zuerst im Stand
  gemessen. Die Kriterien K0-1 bis K0-7 bleiben; für die Drehung selbst
  gelten die Kriterien R1 bis R6 im Auftrag KI-1. Zurückgenommen: die Regel
  „von zwei türgroßen Lücken die nähere“ (§5 nannte sie nicht eigens). Die
  Stufen KI-2 bis KI-5 bleiben, wie sie in §8 stehen; wie der Fahrteil
  (KI-2, KI-3) im Einzelnen geschnitten wird, wird mit dem Projektinhaber
  besprochen, bevor dort etwas gebaut wird.
- 21.11.2026, v1.5 (Festlegung des Projektinhabers): **Die KI bekommt Zeit,
  kein stiller Rückfall.** Großzügige Zeitgrenze, erneutes Fragen, sonst
  stehen bleiben und melden; der Regel-Rückfall ist ein eigener Schalter
  (Vorgabe aus) und immer sichtbar (§3, §4, §6, §7, KI-2). Grund: Eine Fahrt
  darf nicht wie eine KI-Fahrt aussehen, wenn in Wahrheit die alte Regel
  entschieden hat. Der Fahrteil soll aus vorhandenem, real bewährtem Code
  entstehen; Bestand und Vorschlag stehen im STATUS, entschieden ist dazu
  noch nichts.
- 22.11.2026, v1.11, nach KI-F3b: Amadeus fuhr drei Etappen genau auf der
  Linie und hielt 0,26 m vor der Türlinie an einer belegten Stelle mitten
  im Durchgang; woher sie stammte, ließ sich nicht feststellen. In §6a
  nachgezogen: Prüfung der Kostenkarte auf dem ganzen Weg vor dem Senden
  und die Herkunft jeder belegten Stelle. Grundsatz, neu festgehalten:
  **Ein Halt muss seine Ursache benennen können**, sonst lässt sich aus
  ihm nichts lernen.
- 22.11.2026, v1.10 (Einwand des Projektinhabers: „Der Roboter ist schon
  dreimal durch die Tür gefahren. Warum soll er sich auf einmal nur vor die
  Tür stellen? Das ist ja ein Rückschritt.“): Das Davorstellen von Hand war
  als erste Stufe gedacht, weil die Etappenfahrt nur gerade Stücke fährt und
  die früheren Durchfahrten alle über Nav2 liefen, das seit dem 15.11. kein
  Ziel mehr erreicht. Neu in §6a: die **Anfahrt**, mit der sich der Roboter
  selbst vor die Tür stellt. Dabei gefunden und behoben: Die Türachse aus
  zwei schräg gesehenen Türkanten ist verdreht; sie kommt jetzt aus der Wand
  neben der Tür.
- 22.11.2026, v1.9, nach KI-F2: Die Fahrt hielt 0,35 m nach dem Start am
  Nahbereichs-Halt. Der Weg über einen Vorpunkt auf der Türachse führte
  rechnerisch so nah an die Spitze des 85° offenen Türblatts, dass die
  vordere Ecke am Wendepunkt 1,6 cm davor gestanden hätte. In §6a
  ersetzt durch die gerade Linie durch die Türmitte mit Prüfung des
  Freiraums am Laserbild. Grundsatz, neu festgehalten: **Ein Weg wird vor
  dem Senden gegen das geprüft, was der Laser sieht, nicht nur aus der
  gewählten Öffnung gerechnet.**
- 22.11.2026, v1.8, nach KI-F1: Die gerade Etappe ist am Roboter gelungen
  (0,505 m, keine Abweichung). Die Türdurchfahrt wurde nicht gestartet, weil
  die Tür aus der schrägen Lage 1,25 m breit vermessen wurde. In §6a
  nachgezogen: Türfenster 0,65 bis 0,95 m, Bewertung der Aufstellung,
  Vorpunkt 1,1 m statt 0,7 m vor der Tür. Festgehalten als Grenze des
  heutigen Stands: Aus einer Lage auf der Seite des offenen Türblatts ist
  die Tür nicht verlässlich vermessen; bis das geklärt ist, fährt Amadeus
  nur aus einer Aufstellung vor der Tür.
- 21.11.2026, v1.7, nach KI-1: Die erste Blickrunde aus eigener Kraft ist
  gelungen (Drehung 363°, acht Bilder, Antwort in 4,9 s, richtige Tür
  gewählt). Zeitgrenze auf 120 s festgelegt; Rechenlast, Dauer der Runde
  und der erste Befund zu Personen in §11 nachgetragen. Die Kriterien K0-1
  bis K0-6 haben weiter kein Urteil (eine Runde). Der nächste Auftrag
  (KI-F1) bringt den Fahrteil in zwei Stufen auf den Roboter: eine gerade
  Etappe, dann in einem Zug durch die Labortür.
- 21.11.2026, v1.6 (Entscheidung des Projektinhabers): **Der Fahrteil ist
  eine Etappenfahrt ohne Nav2** aus den am 10./11.09. real bestandenen
  Bausteinen (neuer Abschnitt 6a; zweite Anschlussstelle
  `stage_drive_only`; viertes Thema `/ki_erkundung/fahrziel_json` nur auf
  dem Roboter). Abweichung von §8, vom Projektinhaber so gewollt: Der
  Fahrteil wird schon jetzt gebaut und simuliert, obwohl die Kriterien von
  KI-1 noch kein Urteil haben. Auf den Roboter kommt er trotzdem nur
  Schritt für Schritt, je Realtest eine Verhaltensänderung, zuerst eine
  einzelne gerade Etappe.
- 21.11.2026, Nachtrag (Wunsch des Projektinhabers): Auf dem KI-Rechner
  gibt es ein Programm für den Bildschirm, das Lotsen-Fenster. Es startet
  den Lotsen-Dienst und zeigt seinen Zustand, die letzten Fragen mit Bildern
  und das Log. Es ersetzt den geplanten Systemdienst. An Rollen und Grenzen
  ändert es nichts: Es zeigt nur an und schaltet den Dienst ein und aus; die
  Anzeige ist nur vom KI-Rechner selbst erreichbar.

## 13. Übernommen aus dem HomeMy-Konzept des Projektinhabers

Quelle: [quellen/HomeMy_Mobility_VLA_Projektkonzept_2026-11-19.md](quellen/HomeMy_Mobility_VLA_Projektkonzept_2026-11-19.md)
(unverändert abgelegt). Das Dokument beschreibt für das Schwesterprojekt
HomeMy dieselbe Grundordnung wie diese Linie: Ein lokales Modell versteht
Sprache und Bild und schlägt ein Ziel vor, eine feste Schicht prüft es, die
Navigation fährt, die Sicherheit bleibt unabhängig.

| Aus dem Dokument | Hier |
|---|---|
| Kein direktes Motorinterface für das Modell; nur geprüfte Zielvorschläge | gilt schon (§3, §6) |
| Startmodell Qwen3.5-9B über Ollama, Vergleich Qwen3-VL-8B | übernommen (§7), an der Quelle geprüft |
| Erst an echten Wohnungsbildern messen, mit wiederholbarer Modellkonfiguration, Latenz als Median und 95-%-Wert | übernommen (KI-0, KI-1, Ergebnisdatei) |
| Ziel vor Ort erneut bestätigen | übernommen (§4) |
| Stationärer KI-Rechner, Roboter bleibt ohne ihn sicher | gilt schon (§3, §7) |
| Objektgedächtnis mit Zeit und Zustand, Tiefe über die Fläche, „nicht gefunden“ statt Erfindung | vorgemerkt für KI-5 |
| Selektierte Einzelbilder statt Dauer-Videostrom | gilt schon (Blickrunde) |

Nicht übernommen, weil es bei Amadeus schon entschieden oder vorhanden ist:
die offenen Punkte zu Kameratyp, ROS-Fassung, Odometrie, SLAM und LiDAR;
die Meilensteine M1 (3D-Lage aus RGB-D) und M2 (Nav2), die es hier als
`semantic_perception` und als Navigation der Hauptlinie gibt. Anders als im
Dokument angenommen ist die Navigation bei Amadeus nicht der erledigte Teil,
sondern der schwierige: die Türdurchfahrt (§9).
