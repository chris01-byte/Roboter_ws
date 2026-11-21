# KI-Erkundung – aktueller Status

**Stand 21.11.2026:** Der erste echte Lauf ist gemacht (Auftrag KI-0
„Erstes Sehen“, [Archiv](archiv/20261121-ki0-erstes-sehen/)): Amadeus stand
im Labor, Kamera und LiDAR liefen, der KI-Rechner hat über WLAN zu sieben
Standbildern geantwortet. **Die Kette läuft an echten Geräten. Ein Urteil
nach den Kriterien gibt es noch nicht.** Das schwache Glied ist die
Vermessung der Öffnungen, nicht die KI. Die Vermessung ist nachgebessert,
aber nur im künstlichen Zimmer geprüft; ob sie an den echten Aufnahmen
stimmt, klärt der Auftrag KI-0N ([AUFTRAG.md](AUFTRAG.md)).

Diese Linie ist seit 19.11.2026 (spät) die aktive Arbeit; die Hauptlinie ist
geparkt. Dies ist der einzige Iststand dieser Linie. Der Stand der
Hauptlinie steht ausschließlich in `docs/wohnungserkundung/STATUS.md`.

## Arbeitsliste

**Aktiv: Auftrag KI-0N „Nachmessen“** ([AUFTRAG.md](AUFTRAG.md)), im Stand,
ohne Bewegung, auf dem Jetson. Zuerst an den sieben gespeicherten Aufnahmen
vom 21.11. (kein Sensor nötig), dann, wenn Christopher Zeit hat, weitere
Ansichten: Tür mit offenem Blatt von der Scharnierseite, geschlossene Tür,
Glas, Spiegel, Flur, eine Ansicht zweimal an derselben Stelle. Christopher
beurteilt alle Blätter neu, weil sich die Nummern geändert haben.

**Danach, je nach Ergebnis:**
- Stimmt die Vermessung an den echten Aufnahmen: Fahrteil vorbereiten
  (unten).
- Stimmt sie nicht: mit dem Prüftext aus KI-0N gezielt nachbessern. Als
  zweiter Weg ist vorgemerkt, dass die KI die Tür im Foto selbst zeigt und
  der Laser nur an dieser Stelle misst; dann hängt das Erkennen nicht mehr
  an den vermessenen Vorschlägen.

**Fahrteil (in der Entwicklung, ohne Roboter).** Vorgabe des
Projektinhabers: nichts Neues erfinden, sondern an den Türdurchfahrten
orientieren, die funktioniert haben. Im Repository belegt:
- 11.09.2026 (Stand `1d91229`, Protokoll `WE_PARITY_RESET.md`): Rundblick in
  8 × 45° mit 0,08 rad/s und 1 s Pause, danach Ziele, eine Tür als
  „verbunden“ erkannt und über die Navigation durchfahren, mit Aufstellen in
  begrenzten Etappen davor und Bestätigen des Auslaufs dahinter.
- 08.11.2026 (Release `selbstheilung-sh7-20261108_1617`): zwei Durchfahrten
  durch die 80-cm-Tür in drei Fahrten, über gewöhnliche Ziele der Navigation.
- Dazu ein begrenztes Türprofil (`door_test_params.yaml`): gerade Fahrt mit
  Mittenführung durch den LiDAR, höchstens 0,08 m/s, Abbruch ab 6 cm
  seitlicher Abweichung. Dieser Code ist vorhanden, in der geparkten Linie
  abgeschaltet und seit September nicht mehr real gelaufen.
Offen ist, wie Amadeus einem gefundenen Weg im Raum folgt (wie am 08.11.
oder in geraden Stücken mit Drehen auf der Stelle); wird mit dem
Projektinhaber besprochen.

**Danach: KI-1 „Blickrunden aus eigener Kraft“.** Dafür fehlen zwei Dinge,
die diese Linie nicht allein herstellen kann:
- **Volle Drehung am Start.** Der Rundblick der Hauptlinie dreht 90°; der
  Wert steht fest im Profil und lässt sich im Selbstheilungsbetrieb beim
  Start nicht von außen setzen (`nav_mapping.launch.py` gibt dem Erkunder
  dort immer `self_healing_params.yaml`). Nötig ist eine kleine
  Anschlussstelle in der Hauptlinie; ohne Freigabe des Projektinhabers wird
  dort nichts geändert.
- **Kamera neben der Kartierung.** Sie ist dort bewusst abgeschaltet; ihre
  Last wird zuerst im Stand gemessen.

**Geparkt:** Anschluss der KI-Wahl an die vorhandene Erkundung (Entscheidung
vor KI-2); Raumnamen in der App (KI-4); Gegenstände finden (KI-5);
Lotsen-Dienst als Systemdienst, damit Einschalten genügt; größere
Kamerabilder für die KI (geliefert werden 320 × 180).

**Erledigt:** Konzept und Trennregeln · Werkzeuge für den Trockenlauf ·
HomeMy-Konzept ausgewertet · Verbindung zum KI-Rechner · KI-0 Teil A
(19.11.) und Teil B (21.11.) · Vermessung und Auswertung nach Teil B
nachgebessert (21.11.).

## KI-0 Teil B – erster echter Lauf (Jetson, 21.11.2026)

Zahlen und Antworten je Ansicht stehen im
[Archiv](archiv/20261121-ki0-erstes-sehen/). Kurz:

**Was lief.** 158 Tests am Jetson (Python 3.10, ROS 2 Humble). 14 Fragen
über WLAN an den Lotsen-Dienst, alle beantwortet. Bild und Scan passen
zeitlich zusammen (je Aufnahme 16 Paare, keines verworfen). Ohne Denken
kommt die Antwort in 1,5 bis 2,7 s (die erste 4,0 s, davon 2,4 s Laden).

**Was die KI kann und was nicht.**
- Hatte die Tür eine Nummer und war sie im Foto zu sehen, hat die KI sie
  gewählt: vier von vier Ansichten.
- War kein Ausgang im Foto (er lag nur in der Skizze), hat sie nichts
  gewählt. Das ist vorsichtig, aber zu wenig: Ein Bild allein reicht nicht,
  es braucht die Blickrunde.
- War nur eine Möbellücke angeboten, hat sie diese als „Durchgang“ gewählt
  (Sicherheit 0,95). Die KI nimmt also, was man ihr anbietet. Eine fast
  geschlossene Tür nannte sie „offen“.
- Raumnamen: in allen Ansichten falsch (Schlafzimmer, Flur, Wohnzimmer; es
  war das Labor). Für Raumnamen ist ein einzelnes kleines Bild keine Basis.
- Mit Denken: 8 bis 16 s statt 2 s, einmal 64,6 s ohne brauchbare Antwort,
  in der Wahl nicht besser. **Denken bleibt aus.**
- Glas und Spiegel waren nicht dabei. K0-2 ist ungeprüft.

**Was an der Vermessung nicht stimmte.**
- Von vorn: Tür 0,74 und 0,73 m bei wahren 0,85 m. Zu schmal, vorsichtige
  Seite.
- Von der Seite: Tür 1,22 m und 1,76 m breit, die Nummer stand neben der
  Tür oder auf dem Türblatt.
- Aus 4–5 m: Tür nicht angeboten, nur eine 2,25 m breite Möbellücke davor.
- Sieben von zwölf Vorschlägen waren Lücken an Möbeln, die meisten seitlich
  oder hinter dem Roboter.

**Nach den Kriterien (nachgerechnet mit der korrigierten Auswertung, ohne
Denken):** K0-1 richtig 4 von 6 (67 %), nötig 90 % bei mindestens zehn
Ansichten mit angebotenem Ausgang (es waren fünf): kein Urteil. K0-2: kein
Urteil. K0-3: 0 von 6 verworfen, bestanden. K0-4: Median 1,9 s, bestanden.
K0-5: ein Paar, gleiche Wahl; der Standort war nur ungefähr derselbe. K0-6:
Ausgang angeboten in 5 von 6 (83 %), nötig 90 %: nicht bestanden.

**Was dabei auffiel und offen bleibt.**
- Die Kamera liefert 320 × 180, nicht 640 × 360 wie für August im
  ROBOT_TRANSFER vermerkt (`i_isp_den: 6` in den Releases).
- `~/roboter_ws/install` (Stand 27.07.) startet weder das Kamera-Relay noch
  das LiDAR; der SH-9-Release fehlt `semantic_perception`. Benutzt wurde auf
  Christophers Entscheidung die WE-1-Release `we1-10e1858074e7-r1`.
- Der LiDAR-Treiber endete beim Beenden mit `buffer overflow detected`.
- Während der Messung lief `update-manager` mit etwa 94 % eines Kerns.
- Der Lotsen-Dienst auf dem KI-Rechner lief nach Teil B weiter (A6 offen;
  KI-0N benutzt ihn und beendet ihn danach).

## Nachbesserung nach Teil B (21.11.2026, Commit `5319b7f`)

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

**Nicht nachgestellt:** die 1,76 m (`labor_tuer_weit_seite`) und die 1,74 m
(`labor_ecke`). Ob die Blattregel sie trifft, ist offen.
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
| `lotse/blickrunde.py` | Aufnahmeformat; Drehwinkel aus den Scans; Auswahl der acht Bilder; Rundum-Profil (im Stand vom Ort des LiDAR aus); Ruhe des Echos je Richtung |
| `lotse/kandidaten.py` | Öffnungen vermessen (Breite, Lage, freie Tiefe), auch mit offenem Türblatt; Protokoll jeder geprüften Lücke mit Grund |
| `lotse/markierung.py` | Nummern ins Foto, Kartenskizze, Übersichtsblatt |
| `lotse/frage.py`, `lotse/antwort.py` | Frage an die KI (ganze Runde, Teilrunde, Einzelbild); Prüfung der Antwort |
| `lotse/ki_rechner.py` | Verbindung zu Ollama ohne Proxy; Denkschalter; Fassung und Kennung des Modells |
| `lotse/botschaft.py` | Frage und Antwort für die Übertragung packen und begrenzen |
| `lotse/auswertung.py`, `lotse/ablauf.py` | Kennzahlen K0-1 bis K0-6 mit Median und 95-%-Wert, Vergleich getrennter Aufnahmen; Ablauf einer Runde |
| `werkzeuge/lotse_dienst.py` | KI-Rechner: nimmt Fragen über ROS an, fragt Ollama lokal, eine Frage zur Zeit |
| `werkzeuge/ki_verbindung_ros.py` | Roboter: stellt die Frage über ROS; keine Antwort ist ein Ergebnis, kein Fehler |
| `werkzeuge/blickrunde_aufnehmen.py`, `trockenlauf.py`, `trockenlauf_auswerten.py`, `beispielrunde_erzeugen.py` | Aufnahme, Trockenlauf (direkt oder `--ueber-ros`), Auswertung, künstliche Beispielrunde (auf Wunsch mit Türblatt) |
| `werkzeuge/vermessung_pruefen.py`, `wahrheit_eintragen.py` | Prüftext der Vermessung zu gespeicherten Aufnahmen; Angaben des Menschen mit Lage der Nummern eintragen |

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
| 21.11.2026 | Befunde nachgestellt | künstliches Zimmer mit Türblatt | 0,80-m-Tür mit Blatt bei 90° von der Scharnierseite: vorher 1,14 m breit und 0,4 m vor der Tür (bei tieferem Flur; sonst gar nicht angeboten), jetzt 0,79 bis 0,84 m an der Tür. Blatt bei 75°, 90°, 100° und 110° von vier Standpunkten (16 Fälle): in 15 Fällen Tür 0,73 bis 0,89 m an der Tür, in einem Fall nicht angeboten (75°, von der Öffnung waren 6 cm zu sehen). Bei 100° und 110° erscheint in vier Fällen zusätzlich die Tasche zwischen Blatt und Schrank als eigene Öffnung. Tür hinter einer breiten Möbellücke: vorher nicht angeboten, jetzt 0,71 und 0,72 m |

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

## Was nicht geprüft ist

- **Die nachgebesserte Vermessung an echten Aufnahmen.** Sie ist nur im
  künstlichen Zimmer geprüft. Das künstliche Zimmer hat die Fehler vom
  21.11. vorher nicht gezeigt, weil es kein Türblatt und kaum Möbel hatte.
- **Glas, Spiegel, geschlossene Tür, Flur mit mehreren Türen** an echten
  Bildern.
- **Die ganze Blickrunde** (acht Bilder nach einer Drehung) an echten
  Bildern; bisher nur Standbilder mit einem Foto.
- **`qwen3-vl:8b`** an echten Bildern; gefragt wurde nur `qwen3.5:9b`.
- **Personen** in Scan und Bild.
- **Größere Kamerabilder.** Ob 320 × 180 der KI auf Dauer genügt, ist offen.

## Genau ein nächster Schritt

Auftrag KI-0N auf dem Jetson ([AUFTRAG.md](AUFTRAG.md)): die sieben
gespeicherten Aufnahmen neu vermessen und fragen, Christopher beurteilt die
Blätter; wenn Zeit ist, weitere Ansichten dazu.
