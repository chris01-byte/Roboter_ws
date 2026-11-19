# KI-Erkundung – aktueller Status

**Stand 19.11.2026 (spät):** [Konzept v1.1](KONZEPT.md) steht. Die Werkzeuge
für den Trockenlauf und die **Verbindung Roboter ↔ KI-Rechner für den
Lotsen** sind gebaut und in der Entwicklungsumgebung geprüft. **Am Roboter
und am KI-Rechner ist für diese Linie noch nichts gelaufen**; es wurde noch
kein echtes Bild und keine echte KI verwendet. In der Hauptlinie läuft
parallel der Realtest SH-9; dieser Ordner berührt ihn nicht.

**Seit 19.11.2026 (spät) ist dies die aktive Arbeit:** Der Projektinhaber
hat die Hauptlinie nach SH-9 geparkt (kein Ziel erreicht, Tür nicht
durchfahren) und entschieden, mit der KI-Erkundung zu beginnen. Folge: Diese
Linie kann sich nicht darauf stützen, dass die Hauptlinie fährt. Die Stufen
KI-1 („Mitlauf bei Fahrten der Hauptlinie“) und KI-3 („die vorhandene
Navigation fährt“) müssen deshalb neu gefasst werden; der Aufbau wird gerade
mit dem Projektinhaber abgestimmt.

Dies ist der einzige Iststand dieser Linie. Der Stand der Hauptlinie steht
ausschließlich in `docs/wohnungserkundung/STATUS.md`.

## Klarstellungen des Projektinhabers (19.11.2026, abends)

Sie beantworten die zwei Fragen, die hier offen standen:

1. **Kein Joystick.** Amadeus dreht sich für die Blickrunde selbst.
2. **Der KI-Rechner wird nur eingeschaltet;** die Verbindung baut sich von
   selbst auf, wie bei der Objekterkennung.

Dazu sein Konzept „HomeMy“ als Quelle ([quellen/](quellen/)); ausgewertet in
KONZEPT §13. Festgestellt dabei: Die Verbindung zum KI-Rechner liegt im
Repository auf `main` und läuft über ROS 2 DDS im WLAN; rosbridge verbindet
nur die App mit dem Roboter.

## Arbeitsliste

**Aktiv: Auftrag KI-0 „Erstes Sehen“** ([AUFTRAG.md](AUFTRAG.md)), im Stand,
ohne Bewegung. **Teil A (KI-Rechner) lief am 19.11.2026 bis A5** und steht
dort: Der Lotsen-Dienst kann nicht starten, weil die Netzwerkschnittstelle,
an die das DDS des KI-Dienstes gebunden ist (`enp4s0`), keine Verbindung
hat. Der Agent hat richtig nichts am Netz geändert. Christopher: Auch im
August lief alles über WLAN; der Lotsen-Dienst bekommt deshalb eine eigene
Kopie der DDS-Einstellung mit der WLAN-Schnittstelle, der vorhandene Dienst
bleibt unverändert. Fortsetzung über den
„A-Nachtrag“ im Auftrag, dann Teil B (Jetson). Reihenfolge laut
Projektinhaber: erst prüfen, ob die KI die Tür erkennt, dann die
Türdurchfahrt.

**Teil A, erster echter Lauf (19.11.2026, Bericht des Agenten auf dem
KI-Rechner):**
- Stand `8347f2b` frisch nach `~/ki_erkundung_ws` geklont (`~/roboter_ws`
  unberührt). Tests: 157 bestanden, nachdem das pytest-Plugin
  `launch_testing` abgeschaltet war (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`).
- Modelle: `qwen3.5:9b` (6,6 GB) und `qwen3-vl:8b` (6,2 GB) geladen;
  Grafikspeicher danach 7,7 von 24 GB belegt.
- Künstliches Beispielzimmer, `qwen3.5:9b` ohne Denken: dreimal **Wahl 1**,
  gültig nach Schema; 37,5 s (davon etwa 20 s Laden), dann 1,35 s und 1,32 s.
  **Nummer 1 ist dort die Glastür zum Balkon**, Nummer 2 die Tür zum Flur.
  Das Modell hat also dreimal die Glastür als Ausgang gewählt. Einschränkung:
  Die Glastür ist im gezeichneten Bild nur als heller Rahmen mit dem Balkon
  dahinter zu sehen; ein Urteil über echte Glastüren ist das nicht. Für K0-2
  ist es eine Warnung, die Teil B prüfen muss.
- Die 1,3 s der Wiederholungen kamen vermutlich aus dem Zwischenspeicher
  des Dienstes (gleiche Frage); eine neue Frage dauert eher um 17 s. Folge:
  K0-4 zählt nur die erste Antwort je Frage, K0-5 vergleicht zwei getrennte
  Aufnahmen derselben Ansicht (KONZEPT, Änderungsprotokoll).
- Mit Denken: zweimal keine Antwort nach 60 s. Die Werkzeuge hatten dabei
  still ohne Denkschalter und ohne Schema wiederholt und den Fehlertext des
  Dienstes verworfen. Behoben: genau eine Anfrage wie angegeben, der
  Fehlertext steht in der Ausgabe.

**Als Nächstes in der Entwicklung (ohne Roboter): der Fahrteil.** Vorgabe
des Projektinhabers: nichts Neues erfinden, sondern an den Türdurchfahrten
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
  Anschlussstelle in der Hauptlinie. Vorschlag folgt nach SH-9; ohne
  Freigabe des Projektinhabers wird dort nichts geändert.
- **Kamera neben der Kartierung.** Sie ist dort bewusst abgeschaltet; ihre
  Last wird zuerst im Stand gemessen.

**Geparkt:** Anschluss der KI-Wahl an die vorhandene Erkundung (Entscheidung
vor KI-2); Raumnamen in der App (KI-4); Gegenstände finden (KI-5);
Lotsen-Dienst als Systemdienst, damit Einschalten genügt (mit dem Auftrag
KI-0).

**Erledigt (alles 19.11.2026):** Konzept v1.0 und Trennregeln · Werkzeuge
für den Trockenlauf · HomeMy-Konzept ausgewertet, Konzept v1.1 · Verbindung
zum KI-Rechner (Lotsen-Dienst und Gegenstück).

## KI-0 in Schritten (Entwurf, noch kein Auftrag)

1. **KI-Rechner:** Tests dieser Linie; Bildmodell laden (`qwen3.5:9b`, zum
   Vergleich `qwen3-vl:8b`); Lotsen-Dienst starten
   (`werkzeuge/lotse_dienst.py --modell qwen3.5:9b`).
2. **Jetson:** Tests dieser Linie; Kamera mit Relay und LiDAR starten (keine
   Motoren); prüfen, dass der Status des Lotsen-Dienstes zu hören ist.
3. **Amadeus steht**, wo er ohnehin steht: einige Sekunden aufnehmen
   (`blickrunde_aufnehmen.py`), dann `trockenlauf.py --ueber-ros`, einmal mit
   `--denken aus` und einmal mit `--denken an`. An einigen Stellen und
   Blickrichtungen wiederholen.
4. Der Projektinhaber sieht die Übersichtsblätter mit den Nummern. Der
   Bericht nennt Antwortzeiten, verworfene Antworten, die vermessene Breite
   der bekannten Tür und das Sichtfeld der Kamera.

## Was gebaut ist

| Baustein | Aufgabe |
|---|---|
| `lotse/geometrie.py` | Montage von Kamera und LiDAR, Projektion ins Bild |
| `lotse/blickrunde.py` | Aufnahmeformat; Drehwinkel aus den Scans; Auswahl der acht Bilder; Rundum-Profil |
| `lotse/kandidaten.py` | Öffnungen vermessen (Breite, Lage, freie Tiefe) |
| `lotse/markierung.py` | Nummern ins Foto, Kartenskizze, Übersichtsblatt |
| `lotse/frage.py`, `lotse/antwort.py` | Frage an die KI (ganze Runde, Teilrunde, Einzelbild); Prüfung der Antwort |
| `lotse/ki_rechner.py` | Verbindung zu Ollama ohne Proxy; Denkschalter; Fassung und Kennung des Modells |
| `lotse/botschaft.py` | Frage und Antwort für die Übertragung packen und begrenzen |
| `lotse/auswertung.py`, `lotse/ablauf.py` | Kennzahlen K0-1 bis K0-6 mit Median und 95-%-Wert; Ablauf einer Runde |
| `werkzeuge/lotse_dienst.py` | KI-Rechner: nimmt Fragen über ROS an, fragt Ollama lokal, eine Frage zur Zeit |
| `werkzeuge/ki_verbindung_ros.py` | Roboter: stellt die Frage über ROS; keine Antwort ist ein Ergebnis, kein Fehler |
| `werkzeuge/blickrunde_aufnehmen.py`, `trockenlauf.py`, `trockenlauf_auswerten.py`, `beispielrunde_erzeugen.py` | Aufnahme, Trockenlauf (direkt oder `--ueber-ros`), Auswertung, künstliche Beispielrunde |

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

## Was nicht geprüft ist

- **Kein echtes Bild, kein echter Scan, keine echte KI.** Ob ein Modell auf
  dem KI-Rechner an echten Bildern dieser Kamera Türen erkennt und richtig
  wählt, ist offen. Das ist die Frage von KI-0 und KI-1.
- **Echtes Ollama:** Antwortschema und neun Bilder je Frage laufen mit
  `qwen3.5:9b` (Teil A). Offen: Denkschalter, `qwen3-vl:8b`, die Zeit einer
  neuen Frage ohne Zwischenspeicher.
- **Zielsysteme.** Jetson (Python 3.10, ROS 2 Humble) und KI-Rechner
  (RoboStack Humble, Python 3.12); die ROS-Tests liefen hier unter Jazzy.
- **Echtes WLAN.** Die Strecke lief nur innerhalb eines Rechners.
- **Zeitstempel am echten Roboter** (Bild zu Scan, höchstens 0,15 s Abstand)
  und **Personen** in Scan und Bild.

## Genau ein nächster Schritt

KI-0 fortsetzen: A-Nachtrag N1 bis N3 auf dem KI-Rechner (der Lotsen-Dienst
bekommt eine eigene DDS-Einstellung über WLAN; Christopher: auch im August
lief alles über WLAN), dann Teil B auf dem Jetson.
