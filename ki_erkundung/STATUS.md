# KI-Erkundung – aktueller Status

**Stand 21.11.2026 (spät):** Die erste Stufe (KI-0, Standbilder) ist
abgeschlossen: Die KI erkennt die Labortür an echten Bildern und antwortet
in etwa 1,5 Sekunden. **Als Nächstes dreht sich Amadeus zum ersten Mal
selbst** (Auftrag KI-1, [AUFTRAG.md](AUFTRAG.md)). Der dafür nötige Schalter
im Erkunder ist gebaut, getestet und in der Simulation gelaufen; am Roboter
noch nicht. **Gefahren ist in dieser Linie bisher nichts.**

Ein Urteil nach den Kriterien K0-1 bis K0-6 gibt es weiter nicht (zu wenige
Ansichten, kein Glas, kein Spiegel). Die Vermessung der Öffnungen ist in
zwei Fällen noch falsch, die Ursache ist dort nicht geklärt.

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
| Blickrunde | sich selbst einmal herumdrehen; aus acht Bildern nennt die KI den Ausgang | KI-1 | **als Nächstes**; Schalter gebaut, Auftrag geschrieben |
| Die KI wählt, Amadeus fährt | zur gewählten Tür und hindurch, im nächsten Raum neu umsehen; zuerst in der Simulation, dann im Labor | KI-2, KI-3 | offen; die Fahrweise wird vorher mit dem Projektinhaber besprochen. Vorbild sind die Türdurchfahrten vom 11.09. und 08.11. |
| Raum für Raum | weiter, bis kein Ausgang mehr offen ist (Laborraum, Flur, Schlafzimmer) | KI-3 | offen |
| Räume benennen, um Hilfe rufen | Raumnamen als Vorschlag in der App; Hilferuf mit Grund und Bild | KI-4 | offen |
| Auf Zuruf | „fahr in die Küche“, „such die Tasse“ | KI-5 | offen |

Die Stufen und ihre Kriterien stehen verbindlich im
[Konzept](KONZEPT.md), Abschnitt 8.

## Arbeitsliste

**Erteilt, wartet auf die Übergabe durch den Projektinhaber: Auftrag KI-1
„Blickrunde aus eigener Kraft“** ([AUFTRAG.md](AUFTRAG.md)).
Auf dem Jetson, mit Christopher, nur im Laborraum. Zuerst Prüfung im Stand
ohne Motoren (neuer Release, Kamera neben dem Kartier-Stack), dann **eine**
Drehung von 360° auf der Stelle, dabei Aufnahme der Blickrunde, danach die
Frage an die KI mit acht Fotos und der Skizze.

**Danach, je nach Ergebnis:**
- Blickrunde brauchbar: dieselbe Drehung im Flur (braucht die Freigabe für
  diesen Raum), dann der Fahrteil.
- Vermessung der Öffnungen nach der Drehung unbrauchbar: gezielt
  nachbessern. Die Blickrunde wird über ein Raster ausgewertet, das im Stand
  schon Schwächen zeigte.

**Offen an der Vermessung (aus KI-0R):**
- `labor_tuer_seite_nah_b`: Tür 1,30 m breit, Nummer neben der Tür; Ursache
  unbekannt (die Vermutung „Türblatt“ ist widerlegt). Der Prüftext nennt
  jetzt beide Kanten jeder Lücke und die Vermerke beider Suchrichtungen.
- Flur: Der Laser sieht vom Standpunkt aus keine Öffnung, obwohl es dort
  zwei Türen gibt. Wird mit der Blickrunde im Flur neu angesehen.
- Türen werden 8 bis 13 cm zu schmal vermessen (vorsichtige Seite).

**Vorgemerkt:** Für ein Urteil nach den Kriterien fehlen Ansichten mit Glas
oder Fenster, mit Spiegel, in einem anderen Zimmer und eine Ansicht zweimal
an derselben Stelle. Der zweite Weg, bei dem die KI die Tür im Foto selbst
zeigt und der Laser nur dort misst, bleibt eine Möglichkeit, falls die
Vermessung weiter Türen verfehlt.

**Vor einem Einsatz ohne Aufsicht:** Der Schalter „nur Rundblick“ prüft
nicht, ob der Drehkreis in der Karte frei ist (der Rundblick des
Selbstheilungswegs tut das).

**Geparkt:** Anschluss der KI-Wahl an die vorhandene Erkundung; Raumnamen in
der App; Gegenstände finden; größere Kamerabilder für die KI (geliefert
werden 320 × 180).

**Erledigt:** Konzept und Trennregeln · Werkzeuge für den Trockenlauf ·
HomeMy-Konzept ausgewertet · Verbindung zum KI-Rechner · KI-0 Teil A
(19.11.) und Teil B, KI-0N, KI-0R (alle 21.11.) · Lotsen-Fenster gebaut und
auf dem KI-Rechner in Gebrauch · Sucher · Schalter „nur Rundblick“ im
Erkunder (21.11., `6956252`).

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
(361,7° in 77 s, kein Nav2-Ziel, Mission erfolgreich). **Am Roboter nicht
gelaufen.**

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

- **Der Schalter „nur Rundblick“ am Roboter.** Nur Tests und Simulation.
- **Kamera neben dem Kartier-Stack:** Rechenlast, Bildrate und Ortung des
  Jetson, wenn beides läuft. Das misst Teil A von KI-1.
- **Die ganze Blickrunde** (acht Bilder nach einer Drehung) an echten
  Bildern: Drehwinkel aus den Scans, Auswahl der Bilder, Vermessung über das
  Raster, Antwort der KI auf neun Bilder über WLAN.
- **Der Stand nach `b3a1acf` an den echten Aufnahmen** (die zurückgenommene
  Regel).
- **Glas, Spiegel, anderes Zimmer; `qwen3-vl:8b`; Personen** in Scan und
  Bild. In KI-1 steht Christopher neben dem Roboter; das wird der erste
  Befund dazu.
- **Der Sucher** auf dem Jetson.

## Genau ein nächster Schritt

Auftrag KI-1 auf dem Jetson ([AUFTRAG.md](AUFTRAG.md)): Prüfung im Stand,
dann eine Drehung im Laborraum mit Aufnahme der Blickrunde.
