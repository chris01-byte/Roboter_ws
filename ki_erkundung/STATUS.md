# KI-Erkundung – aktueller Status

**Stand 19.11.2026 (abends):** Die Linie ist angelegt (Entscheidung des
Projektinhabers vom 19.11.2026, MASTERPLAN §10), [Konzept v1.0](KONZEPT.md)
steht, und die **Werkzeuge für den Trockenlauf KI-0 sind gebaut und in der
Entwicklungsumgebung geprüft**. **Am Roboter und am KI-Rechner ist für diese
Linie noch nichts gelaufen**; es wurde noch kein echtes Bild und keine echte
KI verwendet. In der Hauptlinie läuft parallel der Realtest SH-9; dieser
Ordner berührt ihn nicht (belegt unten).

Dies ist der einzige Iststand dieser Linie. Der Stand der Hauptlinie steht
ausschließlich in `docs/wohnungserkundung/STATUS.md`.

## Arbeitsliste

**Aktiv:** nichts am Roboter. Die Vorbereitung von KI-0 ist softwareseitig
abgeschlossen.

**Als Nächstes: Auftrag KI-0** (Blickrunden aufnehmen, am KI-Rechner
auswerten). Er wird geschrieben und übergeben, wenn SH-9 ausgewertet ist und
der Projektinhaber ihn anfordert. Am Roboter läuft immer nur ein Auftrag.

**Offen, vom Projektinhaber zu klären (für den Auftrag KI-0):**

1. Wie wird Amadeus für die Blickrunden gedreht: mit dem Joystick oder von
   Hand bei gesperrten Motoren? Dem Werkzeug ist es gleich.
2. Wer bedient den KI-Rechner beim Trockenlauf (ein Agent dort oder der
   Projektinhaber selbst), und wie kommen die Aufnahmen vom Jetson dorthin?

**Geparkt:** Anschluss der KI-Wahl an die vorhandene Erkundung (Entscheidung
vor KI-2); Vorschläge aus den Zielen der vorhandenen Erkundung (ab KI-1);
Raumnamen in der App (KI-4).

**Erledigt:** Konzept v1.0 und Trennregeln · Werkzeuge für KI-0 gebaut und
geprüft (beides 19.11.2026).

## KI-0 in Schritten (Entwurf, noch kein Auftrag)

1. Tests dieser Linie auf Jetson und KI-Rechner laufen lassen (ohne Hardware).
2. Jetson: Kamera mit Relay und LiDAR starten. Motoren sind dafür nicht
   nötig, wenn von Hand gedreht wird.
3. An mindestens sechs Standpunkten in Laborraum, Flur und Schlafzimmer je
   eine Blickrunde: `blickrunde_aufnehmen.py --name <standpunkt>` starten,
   Amadeus einmal langsam ganz herumdrehen, beenden. Zusammen mindestens
   zwölf Runden, auch bei anderem Licht oder anders stehender Tür.
4. Aufnahmen im Haus auf den KI-Rechner kopieren.
5. KI-Rechner: `trockenlauf.py --nur-markieren`. Der Projektinhaber sieht je
   Runde ein Übersichtsblatt mit den Nummern und gibt an, welche Nummern
   echte Ausgänge sind (`wahrheit.json`).
6. KI-Rechner: zwei bis drei Bild-Sprach-Modelle laden, `trockenlauf.py
   --modell … --wiederholungen 3`, dann `trockenlauf_auswerten.py`. Der
   Bericht nennt je Modell die Kriterien K0-1 bis K0-6.

## Was gebaut ist

| Baustein | Aufgabe |
|---|---|
| `lotse/geometrie.py` | Montage von Kamera und LiDAR, Projektion ins Bild |
| `lotse/blickrunde.py` | Aufnahmeformat; Drehwinkel aus den Scans; Auswahl der acht Bilder; Rundum-Profil |
| `lotse/kandidaten.py` | Öffnungen vermessen (Breite, Lage, freie Tiefe) |
| `lotse/markierung.py` | Nummern ins Foto, Kartenskizze, Übersichtsblatt |
| `lotse/frage.py`, `lotse/antwort.py` | Frage an die KI; Prüfung der Antwort (verstehen oder verwerfen) |
| `lotse/ki_rechner.py` | Verbindung zum KI-Rechner (Ollama), ohne Proxy, Fehler als Ergebnis |
| `lotse/auswertung.py`, `lotse/ablauf.py` | Kennzahlen K0-1 bis K0-6; Ablauf einer Runde |
| `werkzeuge/` | Aufnahme am Jetson, Trockenlauf und Auswertung am KI-Rechner, künstliche Beispielrunde |

## Nachweise

| Datum | Was | Wo geprüft | Ergebnis |
|---|---|---|---|
| 19.11.2026 | Ordner, Konzept, Verankerung | Repository | angelegt (`907a2b0`) |
| 19.11.2026 | Tests dieser Linie | Entwicklungsumgebung, Python 3.13, numpy 2.5, Pillow 12.3, ohne ROS | 122 bestanden, 1 übersprungen (der ROS-Test) |
| 19.11.2026 | Tests dieser Linie | Entwicklungsumgebung, Python 3.12, numpy 1.26, Pillow 10.2, ROS 2 Jazzy, abgeschottet | 123 bestanden, darunter die Aufnahme über echte ROS-Themen mit nachgestellter Kamera, LiDAR, Odometrie und TF |
| 19.11.2026 | Quelltext auf Python 3.10 lesbar | Syntaxprüfung aller 28 Python-Dateien | bestanden |
| 19.11.2026 | Hauptlinie unberührt | 249 gezielte Tests aus dem SH-9-Auftrag; `git diff` außerhalb dieses Ordners | 249 bestanden; keine bestehende Datei geändert (nur die Verweise aus `907a2b0`) |

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
- Die Nummern stehen in den Beispielbildern an der Türschwelle (angesehen),
  bei naher Öffnung am unteren Bildrand.
- Die Glastür ist die Gegenprobe für K0-2: Das LiDAR misst dort eine
  Öffnung; nur das Bild zeigt die Scheibe.

## Was nicht geprüft ist

- **Kein echtes Bild, kein echter Scan, keine echte KI.** Ob ein
  Bild-Sprach-Modell auf dem KI-Rechner an echten Bildern dieser Kamera Türen
  erkennt und richtig wählt, ist offen. Das ist die Frage von KI-0.
- **Zielsysteme.** Jetson und KI-Rechner haben Python 3.10 mit älterem numpy
  und Pillow; dort sind die Tests noch nicht gelaufen (Schritt 1 von KI-0).
- **Zeitstempel am echten Roboter.** Bild und Scan werden nach ihren
  Stempeln zugeordnet (höchstens 0,15 s Abstand). Ob Kamera und LiDAR
  dieselbe Zeitbasis liefern, zeigt erst die erste echte Aufnahme.
- **Personen** im Scan und im Bild.
- **Modellnamen.** Welche Bild-Sprach-Modelle auf 24 GB passen und mehrere
  Bilder je Frage annehmen, wird vor KI-0 am KI-Rechner geprüft.

## Genau ein nächster Schritt

Auftrag KI-0 schreiben, sobald SH-9 ausgewertet ist und die zwei offenen
Fragen oben beantwortet sind.
