# Aktueller Auftrag der KI-Linie: KI-0R – Nachrechnen (nur Jetson, ohne Sensoren)

**Erteilt am 21.11.2026 (abends).** Er wird aktiv, sobald der Projektinhaber
ihn übergibt. Er läuft auf dem **Jetson**, dauert etwa zehn Minuten und
braucht Christopher nur, falls am Ende einzelne Blätter neu zu beurteilen
sind. Auf dem KI-Rechner muss der Lotsen-Dienst laufen (Programm „Amadeus
Lotse“ oder der Dienst vom 21.11.).

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](archiv/20261121-ki0-erstes-sehen/),
[KI-0N](archiv/20261121-ki0n-nachmessen/).

**Frage dieses Auftrags:** Vermisst der neue Stand an den elf gespeicherten
Aufnahmen die Labortür jetzt auch von der Scharnierseite richtig, und was
bietet er im Flur an? Nichts fährt, kein Sensor wird gestartet.

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md` v1.3, Stufe KI-0 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält |
| Erwartetes Ergebnis | Prüftext der Vermessung zu den elf Aufnahmen; neue Antworten der KI auf die geänderte Frage; Auswertung, bei der die Angaben vom 21.11. nach Lage übertragen sind |
| Nicht-Ziele | Kein Motor, kein Fahr-Stack, keine Kamera, kein LiDAR; kein Eingriff in vorhandene Dienste, Pakete, Profile oder `~/roboter_ws`; keine Änderung an den Werkzeugen; **kein eigenes Anzeigeprogramm schreiben** |
| Rückfall | `~/ki_trockenlauf_ki0r/` darf gelöscht werden; die Aufnahmen und ihre Angaben bleiben unberührt |

## Was sich geändert hat

1. **Im Stand wird direkt gemessen, nicht mehr gerastert.** Nachgestellt mit
   dem Rauschen des echten LiDAR: Das Raster ergab im künstlichen Zimmer
   denselben Fehler wie an der echten Tür (1,22 m, Nummer neben der Tür) und
   zu schmale Türen; der Median der Messungen je Richtung nicht.
2. Der Prüftext nennt, warum an einem Pfosten keine Wandlinie entstand.
3. Die Frage an die KI kennt die Einordnung „wand“, lässt nur Nummern
   wählen, die in einem Foto stehen, und erklärt Nummern am unteren Bildrand.
4. Die Auswertung überträgt Christophers Angaben nach der Lage der
   Öffnungen. Öffnungen an neuer Stelle sind „nicht beurteilt“.

## Vorab festgelegte Erwartungen

Sie stehen hier, bevor gemessen wird. Trifft eine nicht zu, ist das ein
Befund und wird berichtet, nicht nachgebessert.

| Aufnahme | In KI-0N vermessen | Erwartung jetzt |
|---|---|---|
| `labor_tuer_vorn`, `labor_tuer_vorn_2`, `labor_blatt_90` | Tür 0,75, 0,72 und 0,71 m bei wahren 0,85 m | Tür zwischen 0,78 und 0,90 m |
| `labor_tuer_seite_nah_b` | Tür als 1,24 m breite Lücke, „sprung“, Vermerk „keine_wandlinie“ | Tür zwischen 0,75 und 0,95 m, zweite Kante „blatt“ oder „lot“; die Auswertung meldet sie als Öffnung an neuer Stelle, 0,3 bis 0,6 m von der früheren Nr. 2 und links davon |
| `labor_tuer_weit`, `labor_tuer_weit_seite`, `labor_ecke` | Tür 0,70, 0,77 und 0,72 m in 3,5 bis 4 m | Tür weiter angeboten, zwischen 0,75 und 0,90 m |
| `labor_tuer_zu` | nichts angeboten | weiter nichts angeboten |
| alle | an den meisten Türpfosten Vermerk „keine_wandlinie“ | an Türpfosten überwiegend kein Vermerk „wand_…“ mehr |
| `flur` | Nr. 1 auf der Wand zwischen zwei Türen; die Türen ohne Nummer | keine Erwartung; der Prüftext mit `--alle` soll zeigen, was dort geprüft und verworfen wird |

Zur KI gibt es keine Erwartung; die Frage hat sich geändert, das Ergebnis
wird berichtet.

## Regeln

- **Kein Motor, kein Fahr-Stack, keine Sensoren.** Gestartet werden nur die
  drei Werkzeuge unten.
- **Bilder bleiben im Haus.** Kein Bild und keine Scan-Datei in den Chat. In
  den Bericht kommen nur Zahlen, Antworttexte und die Texte der Werkzeuge.
- **Nichts ändern, nichts reparieren, kein eigenes Programm für die
  Anzeige.** Braucht Christopher ein Blatt, wird es mit dem vorhandenen
  Bildbetrachter in einem gewöhnlichen Fenster geöffnet, nie im Vollbild:
  `env --default-signal=INT eog DATEI &`. Geschlossen wird es mit dem Kreuz
  oder einem SIGINT an seine PID.

## Schritte

### R0 – Bestand und Umgebung

```bash
date -Iseconds; pgrep -af "[r]os2 launch|[l]dlidar|[d]epthai|[b]ase_hardware|[s]lam_toolbox" || echo "keine Amadeus-Prozesse"
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_ki0r; mkdir -p "$KI"          # nach dem source: die Datei setzt KI selbst
R=~/.local/share/amadeus/ki_erkundung/blickrunden; ls "$R" | wc -l
timeout 15 ros2 topic echo --once --full-length /ki_erkundung/lotse_status_json > "$KI/lotse_status.txt" 2>&1; cat "$KI/lotse_status.txt"
```

Die eckigen Klammern im Muster sorgen dafür, dass `pgrep` die eigene Shell
nicht trifft. Kommt kein Status des Lotsen-Dienstes: R1 und R2 trotzdem
ausführen, Christopher bitten, auf dem KI-Rechner „Amadeus Lotse“ zu öffnen,
dann R3.

### R1 – Stand holen und Tests

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short | head -5 && \
  git pull --ff-only && git rev-parse HEAD
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -5 )
```

Erwartung: `202 passed`.

### R2 – Vermessung prüfen (ohne ROS, ohne KI)

```bash
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$R" --bericht "$KI/pruefung.md" > /dev/null
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$R" --alle --bericht "$KI/pruefung_alle.md" > /dev/null
wc -l "$KI/pruefung.md" "$KI/pruefung_alle.md"
```

In den Bericht: der ganze Text von `pruefung.md`; aus `pruefung_alle.md`
nur der Abschnitt `flur`.

### R3 – die KI zu allen elf Aufnahmen fragen (ohne Denken) und auswerten

```bash
python3 ki_erkundung/werkzeuge/trockenlauf.py --runden "$R" --ausgabe "$KI/alle" \
  --ueber-ros --denken aus > "$KI/alle.txt" 2>&1; cat "$KI/alle.txt"
python3 ki_erkundung/werkzeuge/trockenlauf_auswerten.py --ergebnis "$KI/alle/ergebnis.json" \
  --runden "$R" --bericht "$KI/auswertung.md" --json "$KI/auswertung.json" > /dev/null; cat "$KI/auswertung.md"
```

Die Angaben in den `wahrheit.json` werden dabei **nicht** verändert.

### R4 – nur wenn die Auswertung „nicht beurteilt“ meldet und Christopher Zeit hat

Für jede Aufnahme, bei der eine Öffnung „an neuer Stelle“ liegt, das Blatt
`$KI/alle/<Name>/uebersicht.jpg` in einem gewöhnlichen Fenster zeigen und
fragen, je einzeln, Antworten wörtlich notieren:

1. Welche Nummern sind echte, offene Ausgänge?
2. Was ist jede Nummer wirklich (offene Tür, geschlossene Tür, Durchgang, Glas, Spiegel, Lücke an Möbeln, Nische, Wand)?
3. Steht die Nummer der Tür im Foto auf der Türschwelle, oder daneben (wo)?

Dann mit `wahrheit_eintragen.py` eintragen wie in KI-0N (`--ergebnis
"$KI/alle/ergebnis.json"`; erlaubte Arten jetzt auch `wand`) und R3, zweite
Zeile, noch einmal ausführen. Hat Christopher keine Zeit, entfällt R4; das
berichten.

## KI-Rechner – Lotsen-Fenster einrichten (falls noch nicht geschehen)

Der Abschnitt steht unverändert im archivierten Auftrag
[KI-0N](archiv/20261121-ki0n-nachmessen/AUFTRAG.md), Schritte F0 bis F5, und
gilt weiter. Einzige Änderung: Die Tests melden jetzt `202 passed`. Ein
Bericht dazu liegt noch nicht vor.

## Bericht

Datei `~/ki_erkundung_bericht_ki0r.md`, ohne Bilder und ohne Scans:

1. Stand (HEAD), Testergebnis, Status des Lotsen-Dienstes.
2. Der ganze Text aus `$KI/pruefung.md`; aus `$KI/pruefung_alle.md` der
   Abschnitt `flur`.
3. Die Tabelle „Vorab festgelegte Erwartungen“, je Zeile mit dem Gemessenen
   und „trifft zu“ oder „trifft nicht zu“.
4. Der Inhalt von `$KI/alle.txt` und je Aufnahme die Begründung der KI aus
   `ergebnis.json`.
5. Der Text aus `$KI/auswertung.md`.
6. Falls R4 lief: Christophers Antworten wörtlich und die Befehle.
7. Alles, was nicht lief, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
