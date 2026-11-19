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
| `lotse/` | Der „Kopf“: reines Python ohne ROS. Vermessene Vorschläge, Nummern im Bild, Frage an die KI, Prüfung der Antwort, Auswertung |
| `werkzeuge/blickrunde_aufnehmen.py` | Auf dem Jetson: hört während einer Drehung mit und speichert Bilder, Tiefenbilder und Scans als Blickrunde. Nur lesend; legt außerhalb des Repositorys ab |
| `werkzeuge/trockenlauf.py` | Auf dem KI-Rechner: Blickrunden aufbereiten (Drehwinkel, acht Bilder, Öffnungen, Nummern, Skizze) und die KI befragen |
| `werkzeuge/trockenlauf_auswerten.py` | Antworten gegen die Angaben des Menschen halten; Bericht zu den Kriterien K0-1 bis K0-6 |
| `werkzeuge/beispielrunde_erzeugen.py` | Künstliche Blickrunde (ausgedachtes Zimmer) zum Ausprobieren und Testen |
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
   aus oder antwortet unbrauchbar, entscheidet die vorhandene Regel.
6. **Bilder bleiben im Haus.** Kamerabilder, Tiefenbilder und Scans der
   Wohnung liegen nur auf dem Jetson und dem KI-Rechner, nie im Repository
   und nie bei einem Cloud-Dienst (AGENTS §2.5; Entscheidung 19.11.2026).
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

Vor Arbeit an dieser Linie lesen: `AGENTS.md`, [KONZEPT.md](KONZEPT.md),
[STATUS.md](STATUS.md). Für den **Jetson-Agenten gibt es hier derzeit keinen
Auftrag**; sein aktueller Auftrag steht unverändert in
`docs/wohnungserkundung/AGENTENAUFTRAG.md`.
