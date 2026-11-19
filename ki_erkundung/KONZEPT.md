# Konzept „KI-Erkundung“ – eine KI übernimmt Ziel- und Suchwahl

**Version 1.0 · 19.11.2026 · Entscheidung des Projektinhabers**

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
| Fahren, Abstand, Bremsen | Nav2, Fahrtor, Kollisionsmonitor, VL53, Not-Aus | **unverändert dieselben** |

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
| **Regel-Rückfall** | Roboter | entscheiden, wenn die KI fehlt, zu langsam ist oder Unbrauchbares antwortet | – |

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
- **Ohne KI bleibt Amadeus fahrfähig.** Raumsemantik ist Zusatznutzen, keine
  versteckte Pflicht.
- **Bilder bleiben im Haus** (README, Regel 6).

## 4. Ablauf im Betrieb (Zielzustand ab Stufe KI-3)

```
 Raum betreten ─► Blickrunde ─► Vorschläge vermessen ─► Frage an den Lotsen
                                                              │
        ┌─────────────────────────────────────────────────────┘
        ▼
   Antwort prüfen ──unbrauchbar/zu spät──► Regel-Rückfall entscheidet
        │ gültig
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

**Wann gefragt wird** (damit die Bildrunde nicht nach jedem Ziel läuft):

- beim Betreten eines Raums (einmal je Raum eine volle Blickrunde),
- wenn ein gewähltes Ziel nicht erreicht wurde,
- wenn ohne Fortschritt gesucht wird (das Signal dafür gibt es schon: EK-1 D),
- vor dem Ende der Erkundung („gibt es noch einen Ausgang, der fehlt?“).

**Zeitbedarf (Rechnung, noch nicht gemessen):** Eine volle Drehung dauert
beim heutigen Drehtempo des Rundblicks (0,10 rad/s) gut eine Minute. Die
Antwort der KI soll im Mittel unter 20 Sekunden kommen (Kriterium in KI-0).

## 5. Die Blickrunde und die vermessenen Vorschläge

**Bilder.** Acht Bilder im Abstand von 45°. Vier Bilder reichen nicht: Die
Kamera sieht nach Datenblatt rund 69° breit, zwischen vier Bildern blieben
Lücken von gut 20°. Mit acht Bildern ist jede Richtung in zwei Bildern zu
sehen.

**Was die Kamera sieht (Rechnung aus Montage und Datenblatt, in KI-0
nachzumessen).** Die OAK-D-S2 sitzt 1,34 m hoch, 0,15 m vor der Antriebsmitte
und ist 18,94° nach unten geneigt. Der Bildstrom zum KI-Rechner hat 640 × 360
Punkte. Daraus folgt: Der Boden ist ab etwa 1,6 m vor der Kamera im Bild; nach
oben reicht das Bild nur knapp über die Waagerechte (in 3 m Entfernung bis
etwa 1,45 m Höhe). Türstürze und Zimmerdecken sind also nicht zu sehen,
Türpfosten, Schwellen, Türblätter und der Boden dahinter schon. Ob das der
KI genügt, ist die erste Frage an den Trockenlauf.

**Vorschläge.** Das LiDAR (0,75 m hoch, 292° Sichtfeld, 0,245 m vor der
Antriebsmitte) liefert während der Drehung Scans. Aus ihnen wird zuerst der
Drehwinkel jeder Aufnahme bestimmt (deshalb ist es gleich, ob Amadeus mit dem
Joystick oder von Hand gedreht wird), dann ein Rundum-Profil des Standpunkts.
Eine **Öffnung** ist eine Lücke von 0,55 bis 2,5 m zwischen zwei Kanten,
hinter der es frei weitergeht: quer zur Lücke gemessen im Mittel mindestens
0,6 m, damit das 0,42 m lange Gehäuse hineinpasst. Eine flache Schranknische
zählt nicht. Jede Öffnung bekommt eine Nummer und ihre Maße: Breite,
Entfernung, Richtung, freie Tiefe. Unter 0,60 m Breite wird sie gezeigt,
aber als zu schmal vermerkt.

**Nummern im Bild.** Jede Nummer wird an der vermessenen Stelle in die Fotos
gezeichnet (am Boden der Öffnung) und in eine Kartenskizze von oben. Grund:
Bild-Sprach-Modelle sind unzuverlässig bei Meterangaben, aber gut darin,
zwischen markierten Stellen zu wählen.

**Später (ab KI-1)** kommen als Vorschläge die Ziele hinzu, die die
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
`art` ist eines von: `tuer_offen`, `tuer_geschlossen`, `durchgang`, `glas`,
`spiegel`, `moebelspalt`, `nische`, `unklar`.

**Prüfung der Antwort** (auf dem Roboter; im Trockenlauf dieselbe Prüfung):

| Fall | Folge |
|---|---|
| kein lesbares JSON | verworfen |
| `wahl` ist keine angebotene Nummer | verworfen |
| die KI ordnet ihre eigene Wahl als nicht befahrbar ein (geschlossene Tür, Glas, Spiegel, Möbelspalt, Nische) | verworfen |
| unbekannte `art` | wird zu `unklar`, Antwort bleibt gültig |
| `wahl` als Text statt Zahl („2“) | toleriert und gezählt |
| Antwort später als die Zeitgrenze | verworfen |

Danach misst die Vermessung die gültige Wahl nach: Öffnung breit genug
(Vorgabe 0,60 m bei 0,46 m Gehäusebreite), erreichbar, im freigegebenen
Fahrbereich. Erst dann wird gefahren.

## 7. Der KI-Rechner

Vorhanden und am 25.08.2026 abgenommen: Rechner mit RTX 3090 (24 GB),
Ubuntu 22.04, ROS 2 Humble. Dort laufen bereits ein lokales Sprachmodell
über Ollama (`qwen2.5`, für Sprachaufträge im `llm_planner`) und die
Objekterkennung (`semantic_perception`, YOLO-World). Der Roboter schickt
dafür einen gedrosselten, komprimierten Kamerastrom (2 Bilder je Sekunde mit
Tiefenbild); dieser Weg ist erprobt.

Diese Linie braucht dort zusätzlich ein **Bild-Sprach-Modell** in demselben
Ollama. Welches, entscheidet der Trockenlauf an denselben Bildern. Nach
heutigem Kenntnisstand kommen Modelle aus den Familien Qwen-VL und Gemma 3
in Frage, die auf 24 GB passen; Namen und Größen werden vor KI-0 am
KI-Rechner geprüft, nicht aus dem Gedächtnis übernommen.

Zu beachten: Die vorhandenen Dienste (`amadeus-ki.service`) dürfen nicht
gestört werden. Lädt Ollama ein großes Bildmodell, kann das Sprachmodell
aus dem Speicher fallen; die erste Antwort danach dauert länger. Das wird
in KI-0 mitgemessen.

## 8. Stufen, Kriterien, Rückfall

Jede Stufe hat vorab festgelegte Kriterien. Eine Stufe beginnt erst, wenn
die vorige bestanden ist. Auf den Roboter kommt je Realtest genau eine
Verhaltensänderung.

### KI-0 – Trockenlauf (keine Fahrentscheidung, kein Eingriff ins Fahren)

An mindestens sechs Standpunkten in Laborraum, Flur und Schlafzimmer werden
Blickrunden aufgenommen, zusammen mindestens zwölf (auch bei anderem Licht
oder anders stehender Tür). Ausgewertet wird am KI-Rechner. Der
Projektinhaber gibt je Runde an, welche Nummern echte Ausgänge sind.

| Kennung | Kriterium (vorab festgelegt) |
|---|---|
| K0-1 Ausgang | In mindestens 90 % der Runden mit angebotenem echtem Ausgang wählt die KI einen echten, offenen Ausgang |
| K0-2 Keine gefährliche Wahl | Nie wählt die KI eine Nummer, die in Wahrheit Glas oder Spiegel ist |
| K0-3 Form | Höchstens 10 % der Antworten werden von der Prüfung verworfen |
| K0-4 Zeit | Antwortzeit im Mittel (Median) höchstens 20 s, längste höchstens 45 s, bei geladenem Modell |
| K0-5 Wiederholbarkeit | Dreimal dieselbe Frage: in mindestens 90 % der Runden dieselbe Wahl |
| K0-6 Vorschläge | In mindestens 90 % der Runden, in denen ein Ausgang zu sehen ist, ist er unter den vermessenen Vorschlägen (misst die Vermessung, nicht die KI) |
| K0-7 Kamera | Sichtfeld aus den Kameradaten bestimmt; Rechenlast der Kamera auf dem Jetson im Stand gemessen (nur Messung) |

Besteht K0-6 nicht, wird zuerst die Vermessung verbessert. Besteht K0-1 mit
keinem Modell, das auf den KI-Rechner passt, ist das der Blocker dieser
Linie; dann wird nichts in Richtung Fahren gebaut.

### KI-1 – Mitlauf ohne Wirkung

Die Kamera läuft bei Erkundungsfahrten der Hauptlinie mit; die KI beantwortet
im Hintergrund dieselben Entscheidungen, steuert aber nichts. Die Kamera ist
in der automatischen Kartierung heute bewusst abgeschaltet. Deshalb zuerst im
Stand messen, dass Ortung und Rechenlast des Jetson mit Kamera nicht leiden.
Kriterien: keine messbare Verschlechterung der Hauptlinie; Antworten in
mindestens 90 % rechtzeitig; Vergleich „Wahl der KI gegen Wahl der Regel“ an
den echten Entscheidungspunkten.

### KI-2 – Kopplung in der Simulation

Im vorhandenen Simulationsaufbau wählt eine gespielte KI: richtig, falsch,
langsam, stumm, Unsinn. Kriterien: keine zusätzlichen Berührungen gegenüber
dem Vergleichslauf; der Regel-Rückfall übernimmt innerhalb der Zeitgrenze;
dasselbe gescheiterte Ziel wird nicht beliebig oft wiederholt; die Fahrt
endet ordentlich. Die Simulation hat keine Kamera; sie prüft die Kopplung,
nicht das Sehen.

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
| Rechenlast der Kamera auf dem Jetson neben der Kartierung | offen; KI-1 misst zuerst im Stand |
| Eine volle Blickrunde dauert gut eine Minute und belastet die Ortung (viele Drehschritte) | bekannt; nur einmal je Raum und im Zweifel |
| Auswahl des Bild-Sprach-Modells | offen; KI-0 vergleicht zwei bis drei |
| Personen im Bild und im Scan (Begleitung mit Not-Aus) | können als falsche Öffnung erscheinen; in KI-0 beobachten |
| Breite der Öffnungen | in der künstlichen Beispielwelt 3–7 cm zu schmal gemessen (vorsichtige Seite); in KI-0 an der bekannten 78-cm-Tür prüfen |
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
