# KI-Erkundung – eigene Entwicklungslinie

**Angelegt am 19.11.2026 auf Entscheidung des Projektinhabers.**
Hier entsteht eine **zweite, vollständig getrennte Entwicklungslinie** für
Amadeus: Eine KI auf dem vorhandenen KI-Rechner (RTX 3090, im Haus) übernimmt
die **Ziel- und Suchwahl** der Wohnungserkundung. Sie sieht die Kamerabilder
einer Blickrunde, erkennt Türen und Durchgänge und entscheidet, wohin Amadeus
als Nächstes fährt. Der Roboter misst nach, fährt selbst und behält seine
ganze Schutzkette.

Kurzform des Prinzips: **Die KI wählt, die Vermessung prüft, die Schutzkette
fährt.**

## Was in diesem Ordner liegt

| Pfad | Inhalt |
|---|---|
| [KONZEPT.md](KONZEPT.md) | Das verbindliche Konzept dieser Linie: Rollen, Ablauf, Schnittstellen, Stufen mit vorab festgelegten Kriterien, Nicht-Ziele, Rückfall |
| [STATUS.md](STATUS.md) | **Einziger** Iststand dieser Linie: Arbeitsliste, Nachweise, genau ein nächster Schritt |
| [AUFTRAG.md](AUFTRAG.md) | Der aktuelle Auftrag dieser Linie für Jetson und KI-Rechner; aktiv erst nach Übergabe durch den Projektinhaber |
| [BEWERTUNG_TUERDURCHFAHRT.md](BEWERTUNG_TUERDURCHFAHRT.md) | Rückblick und Möglichkeiten für den Fahrteil vom 23.11.2026 (keine Entscheidung) |
| [BEWERTUNG_KIF9.md](BEWERTUNG_KIF9.md) | Ursachen der Probleme aus KI-F9, Modellfrage, Selbstheilung („Nachfassen“), Fahrplan, 24.11.2026 (keine Entscheidung) |
| `lotse/` | Der „Kopf“: reines Python ohne ROS. Vermessene Vorschläge, Nummern im Bild, Frage an die KI, Prüfung der Antwort, Auswertung |
| `werkzeuge/blickrunde_aufnehmen.py` | Auf dem Jetson: hört während einer Drehung mit und speichert Bilder, Tiefenbilder und Scans als Blickrunde. Nur lesend; legt außerhalb des Repositorys ab. Schreibt bei jedem Ende (auch nach Strg+C oder einem Fehler); mit `--bis-wartephase SEK` endet sie von selbst SEK s nach dem Rundblick des Erkunders; Zeilen `BEREIT …` und `ERGEBNIS …` für die Ablaufhilfe |
| `werkzeuge/trockenlauf.py` | Auf dem KI-Rechner: Blickrunden aufbereiten (Drehwinkel, acht Bilder, Öffnungen, Nummern, Skizze) und die KI befragen |
| `werkzeuge/trockenlauf_auswerten.py` | Antworten gegen die Angaben des Menschen halten; Bericht zu den Kriterien K0-1 bis K0-6 |
| `werkzeuge/vermessung_pruefen.py` | Zu gespeicherten Blickrunden nennen, welche Lücken der Laser angeboten und welche er verworfen hat, mit Grund. Nur Maße, keine Bilder oder Scans; ohne ROS und ohne KI-Rechner |
| `werkzeuge/wahrheit_eintragen.py` | Die Angaben des Menschen zu einem Blatt eintragen, mit der Lage jeder Nummer; frühere Angaben bleiben erhalten |
| `werkzeuge/sucher.py` | Auf dem Jetson: das Kamerabild live in einem gewöhnlichen Browserfenster, um Amadeus für eine Ansicht hinzustellen. Liest nur mit, speichert nichts, nur von diesem Rechner erreichbar |
| `werkzeuge/lotse_dienst.py` | Auf dem KI-Rechner: Lotsen-Dienst. Nimmt Fragen des Roboters über ROS an und fragt Ollama auf demselben Rechner |
| `werkzeuge/lotse_fenster.py` | Auf dem KI-Rechner: das Programm für den Bildschirm. Startet den Lotsen-Dienst und zeigt im Browser, ob KI-Programm, Dienst und Roboter da sind, die letzten Fragen mit Bildern und Antwort und das Log. Die Anzeige ist nur von diesem Rechner aus erreichbar |
| `werkzeuge/ki_verbindung_ros.py` | Gegenstück auf dem Roboter (`trockenlauf.py --ueber-ros`); vier eigene Themen `/ki_erkundung/…`, nur Text |
| `werkzeuge/radsensor_zustand.py` | Auf dem Roboter, nur lesend: hört einmal auf den Zustand des Motortreibers und schreibt in Klartext, ob und warum der Radsensor gesperrt ist (Größe und Zeitpunkt der ersten Lücke zwischen zwei Lesungen, Dauer der Lesepaare). Keine Lage des Roboters |
| `lotse/fahrziel.py`, `werkzeuge/fahrziel_senden.py` | Auf dem Roboter: aus der gewählten, vermessenen Öffnung einen Punkt vor und einen hinter der Tür berechnen und dem Erkunder als Fahrziel geben (Betrieb „Etappenfahrt“, `stage_drive_only`). Das Werkzeug fährt nicht selbst; gefahren wird vom Erkunder ohne Nav2, mit Fahrtor und Kollisionsmonitor. Mit `--zur-tuer` entscheidet der Roboter selbst, ob er gleich durch die Tür fährt oder sich zuerst davor stellt; die Türachse kommt in allen Betrieben aus der Wand neben der Tür. Mit `--vor-die-tuer` fährt der Roboter zuerst selbst von seinem Platz im Raum vor die Tür (Anfahrt über einen Punkt auf der Türachse; die Achse aus der Wand neben der Tür). Vor dem Senden prüft es die Kostenkarte auf dem ganzen Weg so, wie der Nahbereichs-Halt des Erkunders sie liest, und nennt für eine belegte Stelle (auch nach einem Halt) die Quelle: Karte des SLAM, Nahsensor links oder rechts mit Höhe über dem Boden, Laser. Mit `--tuer` legt es die Fahrpunkte auf die gerade Linie vom Standplatz durch die Türmitte und sendet nur, wenn die Öffnung türbreit vermessen ist, der Roboter passend davor steht und am Laserbild neben der Linie beidseits 0,30 m frei sind; `--tuer --nur-messen` zeigt Maße, Aufstellung, den Freiraum neben der Fahrlinie, was in der Kostenkarte vor dem Roboter belegt ist, und das Protokoll der Vermessung, ohne zu senden. Seit 24.11.2026: Die Herkunft einer belegten Stelle wird rings um sie geprüft und in Worten vom Roboter aus genannt (auch „hinter dem Ende der Strecke“); nach der Anfahrt nennt es, wie weit jede Öffnung neben der gemerkten Tür liegt; Belege jeder Entscheidung bleiben auf dem Jetson (`--belege`); nach Strg+C sendet es nichts mehr (Rückgabe 130) |
| `lotse/wahl.py`, `werkzeuge/ki_tuer_waehlen.py` | Auf dem Roboter, nach dem Rundblick: die neueste Blickrunde aufbereiten, die KI über den Lotsen-Dienst fragen und die geprüfte Wahl mit dem Ort der Öffnung in der Karte in eine Wahl-Datei schreiben (bleibt auf dem Roboter). Zeigt die Wahl in einem Satz mit Maßen vom Roboter aus. Fährt nicht und sendet nichts; zum Fahren gibt ein Mensch die Wahl frei, dann `fahrziel_senden.py --zur-tuer --wahl DATEI`, sonst `fahrziel_senden.py --ende`. Prüft mit `--ueber-ros` zuerst die ROS-Umgebung (Rückgabe 6) und nennt nach dem Schreiben die „Kennung der Wahl“ (Prüfsumme) |
| `werkzeuge/ki_lauf.py` | Auf dem Roboter: **Ablaufhilfe** für einen Lauf (seit 24.11.2026). `start` startet losgelöst Kamera und Aufnahme (sie endet von selbst 5 s nach dem Rundblick), danach fragt ein Begleiter die KI; `wahl` baut die Frage an den Menschen aus der Wahl-Datei selbst (Kennung geprüft), erst wenn keine Kamera mehr läuft (ohne gültige Wahl: „Ende“ an den Erkunder); `antwort` startet nur nach einem klaren „ja“ zu genau dieser Wahl (Kennung), ohne laufende Kamera oder andere Fahrt und einmal je Lauf `fahrziel_senden.py --zur-tuer --wahl …`, sonst „Ende“; `verfolgen`, `messen` (nur messen), `aufraeumen`. Ein vorhandener Laufordner wird nie wiederverwendet. Jeder Schritt lädt seine Umgebung selbst. Sendet selbst nichts an ROS, startet und stoppt keine Mission; Signale nur als genau ein SIGINT an geprüfte einzelne PIDs |
| `werkzeuge/ros_ende.py` | Gemeinsamer Baustein aller ROS-Werkzeuge dieser Linie: Strg+C, `kill -INT` und SIGTERM setzen nur eine Marke, rclpy läuft ohne eigenen Handler (Muster des Erkunders; Befund KI-F9, Lauf 2w) |
| `werkzeuge/beispielrunde_erzeugen.py` | Künstliche Blickrunde (ausgedachtes Zimmer) zum Ausprobieren und Testen; mit `--mit-karte` auch mit Lage am Ende der Runde |
| `quellen/` | Unverändert abgelegte Vorlagen (HomeMy-Konzept des Projektinhabers) |
| `archiv/` | Ausgeführte Aufträge dieser Linie in der Fassung, in der sie liefen, mit Ergebnis in Zahlen |
| `tests/` | Tests dieser Linie, darunter die Trennregeln als Tests (`test_trennung.py`) |

## Trennregeln (verbindlich, MASTERPLAN §10)

1. **Alles Neue dieser Linie liegt in diesem Ordner.** Konzept, Stand,
   Aufträge, Software und Tests.
2. **Diese Linie ändert nichts Bestehendes.** Keine Pakete unter `src/`,
   keine Profile, Startdateien oder Werkzeuge der Hauptlinie. Braucht sie
   später eine Anschlussstelle in bestehendem Code, ist das eine eigene,
   vom Projektinhaber freigegebene Änderung der Hauptlinie: standardmäßig
   aus, ausgeschaltet verhaltensgleich, getrennt getestet (AGENTS §2.7).
3. **Die Hauptlinie läuft unverändert weiter.** `self_healing` mit dem
   Fahrplan in MASTERPLAN §9, ihrem STATUS und ihrem Auftrag bleibt, wie sie
   ist. Dieser Ordner wird von ihrem Build und ihren Tests nicht erfasst
   (die nennen ihre Pfade einzeln).
4. **Am Roboter läuft immer nur ein Auftrag.** Ein Auftrag dieser Linie wird
   erst aktiv, wenn der Projektinhaber ihn ausdrücklich übergibt.
5. **Die KI fährt nicht.** Sie sendet nie Fahrbefehle, umgeht weder Fahrtor
   noch Kollisionsmonitor und ist nie die einzige Schutzmaßnahme. Fällt sie
   aus oder antwortet unbrauchbar, bleibt Amadeus stehen und meldet es; die
   vorhandene Regel entscheidet nur, wenn sie ausdrücklich eingeschaltet
   ist, und das ist dann sichtbar. Zwischen Roboter und KI-Rechner gehen nur
   Frage, Antwort und Status als Text auf den eigenen Themen
   `/ki_erkundung/…`. Das Fahrziel für den Erkunder (ein bis drei Punkte)
   rechnet und sendet nur der Roboter selbst aus der vermessenen, gewählten
   Öffnung; der KI-Rechner sendet es nie.
6. **Bilder bleiben im Haus.** Kamerabilder, Tiefenbilder und Scans der
   Wohnung liegen nur auf dem Jetson und dem KI-Rechner, nie im Repository
   und nie bei einem Cloud-Dienst (AGENTS §2.5; Entscheidung 19.11.2026).
   Das Lotsen-Fenster zeigt die Bilder der letzten Frage nur am Bildschirm
   des KI-Rechners, der Sucher das Live-Bild nur am Bildschirm des Jetson;
   beide Anzeigen sind von keinem anderen Rechner erreichbar.
7. **Dieselben Arbeitsregeln wie in der Hauptlinie.** Erst messen; Kriterien
   und Rückfall vorab; je Realtest genau eine Verhaltensänderung
   (MASTERPLAN §9.1).

**Rückfall der ganzen Linie:** diesen Ordner und die Verweise darauf
entfernen. Sonst ändert sich nichts.

## Ausprobieren ohne Roboter und ohne KI-Rechner

Voraussetzung: Python 3.10 oder neuer, `numpy`, `Pillow`.

```bash
# Tests dieser Linie (ohne ROS wird der eine ROS-Test übersprungen)
python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests

# mit ROS, abgeschottet von einem laufenden Roboter
env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
    python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests

# Eine künstliche Blickrunde erzeugen (kein echtes Bild, keine echte Wohnung)
python3 ki_erkundung/werkzeuge/beispielrunde_erzeugen.py --ausgabe /tmp/ki_beispiel

# Trockenlauf darauf: Vorschläge vermessen, Nummern einzeichnen, Skizze bauen
python3 ki_erkundung/werkzeuge/trockenlauf.py --runden /tmp/ki_beispiel \
    --ausgabe /tmp/ki_beispiel_aus --nur-markieren
```

Mit `--modell <Name>` statt `--nur-markieren` wird der KI-Rechner gefragt
(Ollama, Standardadresse `http://localhost:11434`). Das ist für den
KI-Rechner gedacht, nicht für diese Entwicklungsumgebung.

## Für Agenten

**Keine eigenen Anzeigeprogramme schreiben.** Braucht der Projektinhaber ein
Bild am Bildschirm, gibt es dafür den Sucher (Live-Bild) und den vorhandenen
Bildbetrachter in einem gewöhnlichen Fenster, nie im Vollbild. Am 21.11.2026
ließ sich ein behelfsmäßiges Vollbild nicht schließen; der Jetson musste
heruntergefahren werden.

Vor Arbeit an dieser Linie lesen: `AGENTS.md`, [KONZEPT.md](KONZEPT.md),
[STATUS.md](STATUS.md). Der aktuelle Auftrag dieser Linie steht in
[AUFTRAG.md](AUFTRAG.md) und gilt erst, wenn der Projektinhaber ihn übergibt.
Die Hauptlinie ist seit 19.11.2026 geparkt und hat keinen Auftrag
(`docs/wohnungserkundung/AGENTENAUFTRAG.md`).
