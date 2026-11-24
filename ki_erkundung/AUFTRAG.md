# Aktueller Auftrag der KI-Linie: KI-F9R – Nachrechnen nach der Reparatur des Sehens (nur Jetson, ohne Sensoren, ohne Motoren)

**Erteilt am 24.11.2026** (Christopher zur Reihenfolge nach KI-F9N: „Ja
beginne“). Er wird aktiv, sobald der Projektinhaber ihn übergibt. Er läuft
auf dem **Jetson** an gespeicherten Daten; auf dem **KI-Rechner** muss das
Lotsen-Fenster („Amadeus Lotse“) laufen. **Kein Stack, keine Kamera, kein
Laser, kein Motor.** Christopher wird nur in Schritt 5 gebraucht (etwa zehn
Minuten, Fotos ansehen) und falls der Lotse nicht bereit ist.

**Warum es ihn gibt:** Das Sehen ist ohne Roboter repariert (Schritt 3 der
Reihenfolge, Abschnitt „Sehen repariert“ im [STATUS](STATUS.md)):
1. **Vermessung:** keine Lücke über 180° und keine Lot-Schätzung mit
   vertauschten Kanten mehr (die Ursache von Lauf 2 in KI-F9); hinter einer
   breiten, nahen Lücke (über 1,0 m und über 60°) werden Kanten nicht mehr
   übersprungen; zwei Lücken mit fast derselben Mitte (unter 0,30 m)
   bekommen für die KI nur eine Nummer.
2. **Darstellung:** Nummern, die sich im Foto verdecken würden, werden
   auseinandergeschoben und mit einer Linie mit ihrer Stelle verbunden.
3. **Frage an die KI (Fassung 2):** kein Beispiel mehr zum Abschreiben, erst
   jede Nummer einordnen, dann wählen; neue Arten „fenster“ und „moebel“;
   „lieber keine Wahl als eine falsche“.
4. **Fahrteil:** Durch eine Öffnung, deren zweiter Pfosten nur aus dem Lot
   geschätzt ist, fährt er nie direkt (in diesem Auftrag nicht berührt).

Geprüft ist das bisher an Zufallszimmern, in Tests und in der Simulation,
**nicht an echten Aufnahmen**. Dieser Auftrag rechnet alt gegen neu an allen
gespeicherten Blickrunden nach.

Der vorige Auftrag liegt mit Ergebnis im Archiv:
[KI-F9N](archiv/20261124-kif9n-im-stand/) (dort auch die Liste aller
früheren).

**Frage dieses Auftrags:** Bietet die neue Vermessung an den echten Runden
die Labortür in Lauf 2 an, ohne anderswo eine Öffnung zu verlieren? Wählt
die KI mit der neuen Frage nie mehr Fenster oder Regal, ohne die echte Tür
seltener zu wählen? Und nebenbei: Endet `cmd_vel_mission_gate` bei jedem
Beenden des Stacks mit „exit code -11“?

| | |
|---|---|
| Plan | [Bewertung nach KI-F9](BEWERTUNG_KIF9.md) §10, Schritt 3, mit Christophers Zustimmung vom 24.11.2026; [Konzept](KONZEPT.md) v1.17 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. Alter Stand zum Vergleich: `282ae29` (= Stand von KI-F9N; Vermessung und Frage wie in KI-F9), nur ausgelesen mit `git archive`. Unter `src/` hat sich seit `d61453c` nichts geändert |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif9r.md`: Tests unter Humble, Vermessung alt gegen neu an allen Runden, die KI alt gegen neu an den Runden mit Christophers Angaben und an den KI-F9-Runden, Christophers Angaben zu den KI-F9-Runden, Auswertung K0, die Enden von `cmd_vel_mission_gate` in den alten Logs |
| Nicht-Ziele | Kein Stack, kein Sensor, keine Kamera, kein Motor, keine Mission, kein Fahrziel, kein Build, keine Code- oder Parameteränderung; an den Blickrunden nur das Eintragen von Christophers Angaben (`wahrheit.json`, Schritt 5); auf dem KI-Rechner nichts löschen |
| Rückfall | `~/ki_trockenlauf_kif9r/` darf gelöscht werden. Die in Schritt 5 neu angelegten `wahrheit.json` der KI-F9-Runden dürfen gelöscht werden; frühere Angaben anderer Runden bleiben unberührt (das Werkzeug überschreibt sie nicht) |
| Bereich und Freigabe | Nur Rechnen an gespeicherten Daten; kein Aktor, keine Freigabe nötig. Fragen an Christopher nur in Schritt 3 (Ausnahme) und Schritt 5 |

## Regeln

- **Nichts starten außer den Werkzeugen unten.** Kein `ros2 launch`, kein
  `topic pub`, kein `param set`, `lifecycle set` oder `service call`.
- Keine eigene Code- oder Parameteränderung, kein Commit oder Push, kein
  Build; nichts in `~/roboter_ws`, an Umgebungsdateien oder Releases.
- Signale nur als **genau ein** SIGINT an eine einzelne, geprüfte PID (zum
  Beispiel den Bildbetrachter); keine Prozessgruppen-Signale, kein
  `pkill -f`, kein `killall`, kein `kill -9`.
- **Bilder bleiben im Haus.** Keine Bilder, Scans, Karten, Koordinaten oder
  Adressen im Chat oder im Bericht; Wahl-Dateien nie anzeigen. Erlaubt sind
  die Texte der Werkzeuge mit Maßen vom Roboter aus (Tabellen von
  `vermessung_pruefen.py`, Zeilen von `trockenlauf.py`, die Auswertung).
- Fotos für Christopher nur mit dem vorhandenen Bildbetrachter in einem
  gewöhnlichen Fenster, nie im Vollbild: `env --default-signal=INT eog DATEI &`;
  geschlossen mit dem Kreuz oder genau einem SIGINT an seine PID. **Kein
  eigenes Anzeigeprogramm schreiben.**
- Der Lotse zeigt nur die letzten zehn Fragen. Dieser Auftrag stellt viele;
  die Fragen aus KI-F9 sind seit KI-F9N auf dem KI-Rechner gesichert
  (`~/ki_erkundung_kif9_fragen`). Die Antworten dieses Auftrags stehen ganz
  in `ergebnis.json` auf dem Jetson.

## Vorab festgelegte Erwartungen

Sie stehen hier, bevor gerechnet wird. Trifft eine nicht zu, ist das ein
Befund und wird berichtet, nicht nachgebessert.

**Lauf 2** ist die KI-F9-Runde, für die `vermessung_alt.md` genau zwei
Öffnungen anbietet: 0,82 m bei etwa −174° und 0,83 m bei etwa −171°, beide
mit zweiter Kante „lot“ (so in KI-F9N gefunden).

| Kennung | Erwartung |
|---|---|
| T-1 Tests | Tests der KI-Linie unter Humble: `0 failed` (hier unter ROS 2 Jazzy: 426 bestanden) |
| V-1 Tür in Lauf 2 | `vermessung_neu.md`, Lauf 2: angeboten ist eine Öffnung 0,78 bis 0,92 m breit bei +25° bis +40° (die Labortür) |
| V-2 Scheinlücke weg | `vermessung_neu.md`, Lauf 2: keine angebotene Öffnung mehr 0,82 m bei −174° (±3°); in `vermessung_neu_alle.md`, Lauf 2, steht dort der Vermerk `lot_verkehrt` oder der Grund „Kanten verkehrt herum“ |
| V-3 nichts verloren | Jede Öffnung, die `vermessung_alt.md` in einer Runde anbietet und `vermessung_neu.md` in derselben Runde nicht (gleiche Öffnung heißt: Richtung ±3°, Breite ±0,10 m), ist entweder (a) die Scheinlücke aus V-2 oder (b) eine zweite Nummer an fast derselben Stelle (in `vermessung_neu.md` gibt es eine Öffnung mit Richtung ±5° und Entfernung ±0,3 m). Jede andere verschwundene Öffnung ist ein Befund. Neu hinzugekommene Öffnungen werden nur aufgezählt |
| K-1 KI in Lauf 2 | `ki_nummern.txt`, „neu“, Lauf 2: Die KI wählt die Nummer der Labortür (0,78 bis 0,92 m bei +25° bis +40°) oder keine; nie eine Nummer, deren Richtung mehr als 150° von vorn abweicht (Fenster) |
| K-2 keine falsche Wahl | `auswertung_neu.md`: K0-1 „falsch“ ist 0 und K0-2 hat keine gefährliche Wahl |
| K-3 nicht vorsichtiger als nötig | `auswertung_neu.md`: K0-1 „richtig“ ist höchstens um 1 kleiner als in `auswertung_alt.md` |
| K-4 nichts abgeschrieben | in `ki_neu/ergebnis.json` keine Antwort mit den Platzhaltern SATZ oder RAUM aus dem Muster (Prüfzeile in Schritt 4); Antworten mit einer Nummer, die nicht angeboten war (etwa der 0 aus dem Muster), werden nur gezählt |
| K-5 Form und Zeit | `auswertung_neu.md`: K0-3 (verworfene Antworten) höchstens 10 %; K0-4 wird nur berichtet |
| E-1 Torwächter | keine Erwartung: gezählt wird je altem Log, wie `cmd_vel_mission_gate` endete |

Gesamt: **G-1: T-1, V-1, V-2, V-3, K-1, K-2 und K-4 treffen zu.** K-3 und
K-5 sind Hinweise für die nächste Entscheidung, keine Bedingung.

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls -d ~/ki_trockenlauf_ki0/umgebung_we1.bash ~/roboter_worktrees/kif8.env
ls -d ~/ki_trockenlauf_kif9r 2>/dev/null && echo "KIF9R-ORDNER GIBT ES SCHON"
```

Läuft ein Robotik-Stack: nichts beenden, nichts starten, berichten, Ende.
Fehlt eine der beiden Dateien: berichten, Ende. Gibt es
`~/ki_trockenlauf_kif9r` schon: nicht löschen, berichten, Ende.

## Schritt 1 – Stand holen (kein Build) und Tests

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
echo "src-Aenderungen: $(git diff --name-only d61453c HEAD -- src/ | wc -l)"
KI=~/ki_trockenlauf_kif9r; mkdir -p "$KI/alt"
git archive 282ae29 ki_erkundung | tar -x -C "$KI/alt"; ls "$KI/alt/ki_erkundung/werkzeuge/trockenlauf.py"
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3 ) | tee "$KI/tests.txt"
```

Erwartet: `src-Aenderungen: 0`. Sonst: nichts weiter, berichten.

## Schritt 2 – Vermessung alt gegen neu (ohne ROS, ohne KI)

```bash
cd ~/roboter_worktrees/selbstheilung-v2; KI=~/ki_trockenlauf_kif9r
R=~/.local/share/amadeus/ki_erkundung/blickrunden; ls "$R" | wc -l | tee "$KI/runden_anzahl.txt"
python3 "$KI/alt/ki_erkundung/werkzeuge/vermessung_pruefen.py" --runden "$R" --bericht "$KI/vermessung_alt.md" > /dev/null
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$R" --bericht "$KI/vermessung_neu.md" > /dev/null
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$R" --alle --bericht "$KI/vermessung_neu_alle.md" > /dev/null
diff -u "$KI/vermessung_alt.md" "$KI/vermessung_neu.md" > "$KI/vermessung_diff.txt"; echo "diff_rc=$?"
grep -c "^## " "$KI/vermessung_alt.md" "$KI/vermessung_neu.md"; wc -l "$KI/vermessung_diff.txt"
```

Dann von Hand, nur lesend: Lauf 2 bestimmen (siehe oben), V-1 und V-2
prüfen; für V-3 jede Runde, deren Abschnitt sich im `diff` ändert, mit
beiden Tabellen „Angeboten“ vergleichen.

## Schritt 3 – Lotse bereit?

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash; KI=~/ki_trockenlauf_kif9r
timeout 15 ros2 topic echo --once --full-length /ki_erkundung/lotse_status_json > "$KI/lotse_status.txt" 2>&1
grep -o '"bereit": [a-z]*' "$KI/lotse_status.txt"
```

Nur wenn nicht `"bereit": true`: Christopher genau einmal bitten, auf dem
KI-Rechner „Amadeus Lotse“ zu öffnen, und auf seine Antwort warten; dann die
Zeilen noch einmal. Ist der Lotse dann weiter nicht bereit: Schritt 4 und 5
entfallen, Schritt 6 trotzdem, berichten.

## Schritt 4 – die KI fragen: alt und neu (zweimal dieselben Runden)

Gefragt werden die Runden mit Christophers Angaben (`wahrheit.json`) und
alle Runden aus KI-F9. Die KI antwortet bei gleicher Frage gleich
(Temperatur 0); eine Wiederholung bringt nichts.

```bash
cd ~/roboter_worktrees/selbstheilung-v2; source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_kif9r; R=~/.local/share/amadeus/ki_erkundung/blickrunden
mkdir -p "$KI/auswahl"
for r in "$R"/*/; do r=${r%/}; n=$(basename "$r")
  if [ -f "$r/wahrheit.json" ] || [[ "$n" == kif9_* ]]; then ln -s "$r" "$KI/auswahl/$n"; fi
done; ls "$KI/auswahl" | tee "$KI/auswahl.txt" | wc -l
python3 "$KI/alt/ki_erkundung/werkzeuge/trockenlauf.py" --runden "$KI/auswahl" --ausgabe "$KI/ki_alt" \
  --ueber-ros --denken aus > "$KI/ki_alt.txt" 2>&1; echo "rc=$?" >> "$KI/ki_alt.txt"
python3 ki_erkundung/werkzeuge/trockenlauf.py --runden "$KI/auswahl" --ausgabe "$KI/ki_neu" \
  --ueber-ros --denken aus > "$KI/ki_neu.txt" 2>&1; echo "rc=$?" >> "$KI/ki_neu.txt"
tail -n 2 "$KI/ki_alt.txt" "$KI/ki_neu.txt"
```

Dauert je Runde und Fassung etwa 5 bis 20 s. Danach die Prüfzeile zu K-4:

```bash
KI=~/ki_trockenlauf_kif9r
python3 - "$KI/ki_neu/ergebnis.json" <<'PY' | tee "$KI/muster_pruefung.txt"
import json, sys
e = json.load(open(sys.argv[1], encoding='utf-8'))
n = abgeschrieben = fremd = 0
for r in e['runden']:
    for a in r.get('antworten', []):
        n += 1
        p = a.get('pruefung') or {}
        if p.get('begruendung') == 'SATZ' or p.get('raum') == 'RAUM':
            abgeschrieben += 1
            print('Platzhalter SATZ oder RAUM:', r['name'])
        # eine Nummer, die nicht angeboten war (etwa die 0 aus dem Muster)
        if 'fremde_nummer_eingeordnet' in (p.get('toleriert') or []):
            fremd += 1
            print('Nummer eingeordnet, die nicht angeboten war:', r['name'])
print(f'{n} Antworten, {abgeschrieben} mit SATZ oder RAUM, {fremd} mit fremder Nummer')
PY
```

Und je KI-F9-Runde die Nummern mit Maßen vom Roboter aus und was die KI
dazu sagt, alt und neu (für V-3, K-1 und den Bericht):

```bash
KI=~/ki_trockenlauf_kif9r
python3 - "$KI/ki_alt/ergebnis.json" "$KI/ki_neu/ergebnis.json" <<'PY' | tee "$KI/ki_nummern.txt"
import json, sys
for pfad, fassung in zip(sys.argv[1:], ('alt', 'neu')):
    e = json.load(open(pfad, encoding='utf-8'))
    for r in e['runden']:
        if not r['name'].startswith('kif9_'):
            continue
        print(f"## {fassung} {r['name']}")
        im_foto = r.get('sichtbar_in') or {}
        for o in r.get('oeffnungen', []):
            print(f"  Nr. {o['nr']}: {o['breite_m']:.2f} m, {o['richtung_grad']:+.1f}°, "
                  f"{o['entfernung_m']:.2f} m, {o.get('schluss')}, "
                  f"im Foto: {'ja' if im_foto.get(str(o['nr'])) else 'nein'}")
        for a in r.get('antworten', []):
            p = a.get('pruefung') or {}
            print(f"  KI: Wahl {p.get('wahl')}, Einordnung {p.get('arten')}, "
                  f"gültig {p.get('gueltig')}, Fehler {a.get('fehler') or p.get('fehler') or '-'}")
PY
```

## Schritt 5 – Christophers Angaben zu den KI-F9-Runden (neue Nummern)

Für jede Runde in `auswahl.txt`, die mit `kif9_` beginnt und noch keine
`wahrheit.json` hat: das Blatt `$KI/ki_neu/<Runde>/uebersicht.jpg` in einem
gewöhnlichen Fenster zeigen (siehe Regeln), dazu die Zeilen dieser Runde aus
`ki_neu.txt` **ohne** die Wahl der KI. Dann fragen, je einzeln, als Text,
Antworten wörtlich notieren:

1. „Welche Nummern auf diesem Blatt sind echte, offene Ausgänge aus dem
   Raum? (Keine ist auch eine Antwort.)“
2. „Was ist jede Nummer wirklich: offene Tür, geschlossene Tür, Durchgang,
   Fenster, Glas, Spiegel, Möbel, Lücke an Möbeln, Nische, Wand oder
   unklar?“
3. „Gibt es von diesem Platz aus einen offenen Ausgang, der keine Nummer
   hat?“

Dann eintragen (Arten in den Wörtern des Werkzeugs: `tuer_offen`,
`tuer_geschlossen`, `durchgang`, `fenster`, `glas`, `spiegel`, `moebel`,
`moebelspalt`, `nische`, `wand`, `unklar`):

```bash
cd ~/roboter_worktrees/selbstheilung-v2; KI=~/ki_trockenlauf_kif9r; R=~/.local/share/amadeus/ki_erkundung/blickrunden
python3 ki_erkundung/werkzeuge/wahrheit_eintragen.py --ergebnis "$KI/ki_neu/ergebnis.json" --runden "$R" \
  --name RUNDE --ausgaenge NR … --arten NR=ART … --ausgang-ohne-nummer JA_ODER_NEIN --bemerkung "WÖRTLICH"
```

Die Großbuchstaben sind Platzhalter: `RUNDE` der Name der Runde, `NR` die
Nummern (bei keinem Ausgang `--ausgaenge` ohne Nummer), `JA_ODER_NEIN`
entweder `ja` oder `nein`, `WÖRTLICH` Christophers Antworten im Wortlaut.

Das Blatt danach schließen. Hat Christopher keine Zeit, entfällt dieser
Schritt; die Auswertung beruht dann nur auf den älteren Angaben (berichten).

Danach auswerten (die Angaben werden nach der Lage der Öffnungen auf die
alten Nummern übertragen):

```bash
cd ~/roboter_worktrees/selbstheilung-v2; KI=~/ki_trockenlauf_kif9r; R=~/.local/share/amadeus/ki_erkundung/blickrunden
for art in alt neu; do
  python3 ki_erkundung/werkzeuge/trockenlauf_auswerten.py --ergebnis "$KI/ki_$art/ergebnis.json" \
    --runden "$R" --bericht "$KI/auswertung_$art.md" --json "$KI/auswertung_$art.json" > /dev/null
done; cat "$KI/auswertung_alt.md" "$KI/auswertung_neu.md"
```

## Schritt 6 – Wie endete `cmd_vel_mission_gate` in den alten Logs? (nur lesen)

```bash
source ~/roboter_worktrees/kif8.env; KI=~/ki_trockenlauf_kif9r
{ find "$SH_PR" -name launch.log; find ~/.ros/log -maxdepth 2 -name launch.log -newermt 2026-11-01; } 2>/dev/null \
  | sort -u > "$KI/logs.txt"; wc -l < "$KI/logs.txt"
while read -r f; do
  sauber=$(grep -cE "cmd_vel_mission_gate[^]]*\]: process has finished cleanly" "$f")
  m11=$(grep -cE "cmd_vel_mission_gate[^]]*\]: process has died .*exit code -11" "$f")
  tot=$(grep -cE "cmd_vel_mission_gate[^]]*\]: process has died" "$f")
  [ $((sauber + tot)) -gt 0 ] && echo "$(date -r "$f" '+%F %T') sauber=$sauber exit-11=$m11 anders=$((tot - m11)) ${f#$HOME/}"
done < "$KI/logs.txt" | sort | tee "$KI/gate_ende.txt"
xargs -r -d '\n' grep -ohE "\[[A-Za-z0-9_]+-[0-9]+\]: process has died \[pid [0-9]+, exit code -?[0-9]+" < "$KI/logs.txt" 2>/dev/null \
  | sed -E 's/^\[([A-Za-z0-9_]+)-[0-9]+\].*exit code (-?[0-9]+)$/\1 exit=\2/' | sort | uniq -c | sort -rn | tee "$KI/gestorben.txt"
```

Nur zählen, nichts deuten, nichts ändern.

## Abbruch

- Bewegt sich Amadeus wider Erwarten oder klingt etwas ungewöhnlich:
  Christopher drückt den Not-Aus; der Agent startet nichts mehr und
  berichtet. Den Not-Aus setzt nur Christopher zurück (LAB-1 §4).
- Hängt ein Werkzeug (keine neue Zeile über 5 Minuten): genau ein SIGINT an
  seine PID, kein zweites; berichten, mit dem nächsten Schritt weiter.
- Keine Parameter ändern, um einen Schritt „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif9r.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen, ohne den Inhalt der Wahl-Dateien:

1. Stand (HEAD), die Zeile `src-Aenderungen`, `tests.txt`,
   `runden_anzahl.txt`.
2. `vermessung_diff.txt` ganz. Der Name von Lauf 2; aus
   `vermessung_alt.md` und `vermessung_neu.md` je der ganze Abschnitt von
   Lauf 2; aus `vermessung_neu_alle.md` die Zeilen von Lauf 2 mit
   `verkehrt`. Für V-3 je geänderter Runde: verschwundene und neue
   Öffnungen mit Breite, Richtung, Entfernung, zweiter Kante.
3. `lotse_status.txt` (Zeile „bereit“), `auswahl.txt`, `ki_alt.txt` und
   `ki_neu.txt` ganz (ohne Zeilen `[WARN]` und ohne Pfade),
   `muster_pruefung.txt`, `ki_nummern.txt` ganz.
4. Schritt 5: je Runde Christophers Antworten wörtlich und der Befehl.
5. `auswertung_alt.md` und `auswertung_neu.md` ganz.
6. `gate_ende.txt` und `gestorben.txt` ganz.
7. Die Tabelle T-1, V-1, V-2, V-3, K-1 bis K-5, E-1 mit dem Gemessenen und
   „trifft zu“ oder „trifft nicht zu“, dazu G-1.
8. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
