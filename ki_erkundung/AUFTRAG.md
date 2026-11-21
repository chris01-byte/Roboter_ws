# Aktueller Auftrag der KI-Linie: KI-0N – Nachmessen (im Stand, ohne Bewegung)

**Erteilt am 21.11.2026.** Er wird aktiv, sobald der Projektinhaber ihn
übergibt. Zwei Teile: zuerst auf dem **KI-Rechner** das Lotsen-Fenster
einrichten (Abschnitt „KI-Rechner“ weiter unten, etwa 15 Minuten), dann der
eigentliche Auftrag auf dem **Jetson**. Der Jetson-Teil geht auch ohne das
Fenster, solange der Lotsen-Dienst vom 21.11. noch läuft.

Der vorige Auftrag KI-0 „Erstes Sehen“ ist ausgeführt und liegt mit seinem
Ergebnis unter [archiv/20261121-ki0-erstes-sehen/](archiv/20261121-ki0-erstes-sehen/).

**Frage dieses Auftrags:** Bietet die nachgebesserte Vermessung an den
sieben Aufnahmen vom 21.11.2026 die Labortür richtig an (Breite, Lage der
Nummer, auch aus 4–5 m), und wählt die KI dann richtig? Nichts fährt.

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md` v1.2, Stufe KI-0 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält |
| Erwartetes Ergebnis | Prüftext der Vermessung zu den gespeicherten Aufnahmen; neue Antworten der KI; Christophers Urteil je Blatt; Auswertung nach K0-1 bis K0-6 |
| Nicht-Ziele | Keine Fahrt, keine Drehung, kein Motor; kein Eingriff in vorhandene Dienste, Pakete, Profile oder `~/roboter_ws`; keine Änderung an den Werkzeugen (nur ausführen und berichten) |
| Rückfall | Kamera und LiDAR beenden, falls in Teil 2 gestartet; `~/ki_trockenlauf_ki0n/` darf gelöscht werden; die Aufnahmen vom 21.11. und ihre früheren Angaben bleiben erhalten |

## Vorab festgelegte Erwartungen

Sie stehen hier, bevor gemessen wird. Trifft eine nicht zu, ist das ein
Befund und wird berichtet, nicht nachgebessert.

| Aufnahme | Am 21.11. vermessen | Erwartung jetzt |
|---|---|---|
| `labor_tuer_vorn`, `labor_tuer_vorn_2` | Tür 0,74 und 0,73 m | unverändert etwa 0,75 m, eine Nummer auf der Schwelle |
| `labor_tuer_seite_nah_b` | Tür als 1,22 m breite Lücke, Nummer neben der Tür | Tür zwischen 0,70 und 0,95 m, zweite Kante „blatt“ oder „lot“, Nummer auf der Schwelle |
| `labor_tuer_weit_seite` | Tür als 1,76 m breite Lücke, Nummer auf dem Türblatt | Tür zwischen 0,70 und 0,95 m, Nummer links vom Türblatt auf der Schwelle |
| `labor_tuer_weit` | Tür in 4–5 m ohne Nummer; nur eine 2,25 m breite Möbellücke | die Tür hat eine Nummer |
| `labor_ecke` | Ausgang als 1,74 m breite Lücke | Ausgang zwischen 0,70 und 0,95 m |
| alle | sieben von zwölf Vorschlägen waren Lücken an Möbeln | weniger Vorschläge seitlich und hinter dem Roboter als am 21.11. |

Ob das zutrifft, ist offen: Die Korrekturen sind nur im künstlichen Zimmer
geprüft.

## Regeln

- **Kein Motor, kein Fahr-Stack.** Teil 1 startet nichts außer den
  Werkzeugen dieser Linie. Teil 2 startet, nur wenn neue Ansichten
  aufgenommen werden, Kamera und LiDAR.
- **Bilder bleiben im Haus.** Aufnahmen, Blätter und Ergebnisdateien liegen
  nur auf dem Jetson (`~/.local/share/amadeus/ki_erkundung/`,
  `~/ki_trockenlauf_ki0n/`). Nichts davon in ein Repository. In den Bericht
  kommen nur Zahlen, Antworttexte und der Prüftext der Vermessung (er
  enthält Maße einzelner Lücken, keine Bilder, keine Scans, keine Karte).
  **Kein Bild und keine Scan-Datei in den Chat laden.** Die Blätter sieht
  Christopher am Bildschirm des Jetson.
- **Nichts Vorhandenes ändern, nichts reparieren.** Läuft ein Schritt nicht,
  die Meldung wörtlich berichten und beim nächsten sinnvollen Schritt
  weitermachen.
- **Prozesse einzeln beenden:** genau ein SIGINT an die jeweilige PID, nie
  an eine Prozessgruppe (AGENTS §3).

---

## Teil 1 – ohne Christopher möglich

### N0 – Bestand und Umgebung

Wie am 21.11.2026 entschieden, gilt für alles mit ROS die Umgebung der
WE-1-Release (`~/ki_trockenlauf_ki0/umgebung_we1.bash`, damals angelegt).
`~/roboter_ws/install` und die SH-9-Release sind für diese Linie nicht
brauchbar (Befund 21.11.2026).

```bash
date -Iseconds; MY=$$; pgrep -af "ros2 launch|ldlidar|depthai|base_hardware|slam_toolbox" | grep -v "^$MY " || echo "keine Amadeus-Prozesse"
KI=~/ki_trockenlauf_ki0n; mkdir -p "$KI"
R=~/.local/share/amadeus/ki_erkundung/blickrunden; ls "$R"
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
timeout 15 ros2 topic echo --once /ki_erkundung/lotse_status_json
```

`MY=$$;` steht mit Semikolon in derselben Zeile wie `pgrep`. Läuft ein Stack
oder ein fremder Test: Christopher einmal fragen, nichts selbst beenden.

Kommt kein Status des Lotsen-Dienstes: Teil 1 trotzdem bis N2 ausführen.
Christopher bitten, den KI-Rechner einzuschalten und dort das Programm
„Amadeus Lotse“ zu öffnen (Abschnitt „KI-Rechner“ unten).

### N1 – Stand holen und Tests

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short | head -5 && \
  git pull --ff-only && git rev-parse HEAD
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -5 )
```

Erwartung: `187 passed`.

### N2 – Vermessung der gespeicherten Aufnahmen prüfen (ohne ROS, ohne KI)

```bash
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$R" --bericht "$KI/pruefung.md"
```

Der ganze Text von `$KI/pruefung.md` gehört in den Bericht. Er nennt je
Aufnahme die angebotenen Öffnungen und die verworfenen Lücken mit Grund.

### N3 – die KI zu allen gespeicherten Aufnahmen fragen (ohne Denken)

Nur wenn Christopher in Teil 2 **keine** neuen Ansichten aufnimmt; sonst
erst nach den Aufnahmen (Schritt C3), damit alle Blätter aus einem Lauf
stammen.

```bash
python3 ki_erkundung/werkzeuge/trockenlauf.py --runden "$R" --ausgabe "$KI/alle" \
  --ueber-ros --denken aus | tee "$KI/alle.txt"
```

Mit Denken wird nicht mehr gefragt (am 21.11. langsamer, einmal 64,6 s ohne
brauchbare Antwort, in der Wahl nicht besser).

---

## Teil 2 – mit Christopher

### C1 bis C3 – neue Ansichten (wenn Christopher Zeit hat; sonst weiter bei C4)

Für ein Urteil nach den Kriterien fehlen: mehr Ansichten mit Tür (zehn sind
nötig, fünf gibt es), eine Glasfläche oder ein Spiegel im Blick, eine
Ansicht zweimal an genau derselben Stelle. Amadeus wird von Hand hingestellt
und steht bei jeder Aufnahme still.

**C1 – Kamera und LiDAR starten (keine Motoren):**

```bash
nohup env --default-signal=INT ros2 launch robot_bringup oak.launch.py pointcloud:=false \
  > "$KI/oak.log" 2>&1 < /dev/null & echo $! > "$KI/oak.pid"
nohup env --default-signal=INT ros2 launch amadeus_lidar_bringup stl27l.launch.py publish_static_tf:=true \
  > "$KI/lidar.log" 2>&1 < /dev/null & echo $! > "$KI/lidar.pid"
sleep 20
timeout -s INT 30 ros2 topic hz /oak/semantic/rgb/compressed 2>&1 | tail -2
timeout -s INT 30 ros2 topic hz /scan 2>&1 | tail -2
```

Erwartung: Bilder etwa 2 Hz, Scans etwa 10 Hz.

**C2 – je Ansicht 8 Sekunden aufnehmen:**

```bash
NAME=labor_blatt_90
python3 ki_erkundung/werkzeuge/blickrunde_aufnehmen.py --name "$NAME" --dauer 8 | tee "$KI/${NAME}_aufnahme.txt"
```

Gewünschte Ansichten, so viele wie möglich, in dieser Reihenfolge der
Wichtigkeit (Namen kurz, ohne Leerzeichen):

1. Labortür offen, Türblatt etwa im rechten Winkel, Amadeus steht auf der
   Scharnierseite und schaut an der Blattspitze vorbei in die Tür.
2. Labortür geschlossen, von vorn.
3. Ein Fenster, eine Balkon- oder Glastür im Blick.
4. Ein Spiegel im Blick, falls es einen gibt.
5. Flur mit mehreren Türen.
6. Ein anderes Zimmer mit offener Tür im Blick.
7. Eine der Ansichten mit Tür zweimal an **genau derselben Stelle**: Räder
   vorher mit Klebeband am Boden markieren, Amadeus wegstellen, wieder
   hinstellen, zweite Aufnahme mit demselben Namen und dem Zusatz `_2`.

Zu jeder Ansicht in einem Satz notieren, was Christopher über die Stelle
sagt (zum Beispiel „Tür offen, Blatt 90 Grad, 2 m“).

**C3 – beenden und alle Aufnahmen fragen:**

```bash
kill -INT "$(cat "$KI/oak.pid")"; kill -INT "$(cat "$KI/lidar.pid")"; sleep 5; MY=$$; pgrep -af "ros2 launch|ldlidar|depthai" | grep -v "^$MY " || echo "keine Amadeus-Prozesse"
python3 ki_erkundung/werkzeuge/vermessung_pruefen.py --runden "$R" --bericht "$KI/pruefung.md"
python3 ki_erkundung/werkzeuge/trockenlauf.py --runden "$R" --ausgabe "$KI/alle" \
  --ueber-ros --denken aus | tee "$KI/alle.txt"
```

Meldet der LiDAR-Treiber beim Beenden wieder `buffer overflow detected`
(21.11.2026), die Zeile berichten; das ist bekannt und kein Abbruchgrund.

### C4 – Christopher sieht jedes Blatt

Für jede Aufnahme (auch die sieben vom 21.11., ihre Nummern haben sich
geändert) das Blatt `$KI/alle/<Name>/uebersicht.jpg` im Vollbild auf dem
Bildschirm des Jetson zeigen, die Antwort der KI aus `$KI/alle.txt` nennen
und fragen, je einzeln, Antworten wörtlich notieren:

1. Welche Nummern sind echte, offene Ausgänge, durch die Amadeus fahren könnte?
2. Was ist jede Nummer wirklich (offene Tür, geschlossene Tür, Durchgang, Glas, Spiegel, Lücke an Möbeln, Nische)?
3. Gibt es von hier einen offenen Ausgang, der keine Nummer bekommen hat?
4. Steht die Nummer der Tür im Foto auf der Türschwelle, oder daneben (wo)?
5. In welchem Raum steht Amadeus?

Die Angaben eintragen (frühere Angaben bleiben als `wahrheit_vorher_1.json`
erhalten):

```bash
python3 ki_erkundung/werkzeuge/wahrheit_eintragen.py --ergebnis "$KI/alle/ergebnis.json" --runden "$R" \
  --name labor_tuer_vorn --ausgaenge 1 --arten 1=tuer_offen --raum Labor \
  --ausgang-ohne-nummer nein --bemerkung "Nummer auf der Schwelle"
```

Erlaubte Arten: `tuer_offen`, `tuer_geschlossen`, `durchgang`, `glas`,
`spiegel`, `moebelspalt`, `nische`, `unklar`. Ohne echten Ausgang unter den
Nummern bleibt `--ausgaenge` leer. Die Aufnahme `labor_tuer_seite_nah` (Tür
fast zu) wird diesmal mitgewertet, so wie Christopher sie beurteilt.

### C5 – auswerten

```bash
python3 ki_erkundung/werkzeuge/trockenlauf_auswerten.py --ergebnis "$KI/alle/ergebnis.json" \
  --runden "$R" --bericht "$KI/auswertung.md" --json "$KI/auswertung.json"
```

---

## KI-Rechner – Lotsen-Fenster einrichten (vor dem Teil auf dem Jetson)

Wunsch des Projektinhabers (21.11.2026): Auf dem KI-Rechner soll es ein
Programm mit Symbol auf dem Desktop geben, das den Lotsen-Dienst startet und
zeigt, ob alles läuft und verbunden ist, mit Log. Das ist
`werkzeuge/lotse_fenster.py`: Es startet den Dienst und zeigt seine Anzeige
im Browser. Die Anzeige ist nur von diesem Rechner aus erreichbar
(127.0.0.1); die Bilder der letzten Frage liegen nur auf diesem Rechner.

Nicht ändern: `amadeus-ki.service`, seine Einstellungen, Netz und Firewall
des Rechners, `~/roboter_ws`. Nichts reparieren; Meldungen wörtlich
berichten. Kein Bild in den Chat laden.

**F0 – Bestand:**

```bash
date -Iseconds; ps -ef | grep lotse_dienst.py | grep -v grep
ls -l ~/ki_trockenlauf_ki0/cyclonedds_lotse.xml ~/.config/amadeus/ 2>&1 | head
```

Die Umgebung `umg` ist dieselbe wie im archivierten Auftrag (A0). Notieren,
mit welcher DDS-Datei der laufende Dienst gestartet wurde (Pfad, keine
Adressen).

**F1 – neuen Stand holen und Tests:**

```bash
git -C ~/ki_erkundung_ws fetch origin claude/blissful-pasteur-s1eivj
git -C ~/ki_erkundung_ws checkout --detach FETCH_HEAD; git -C ~/ki_erkundung_ws rev-parse HEAD
umg 'cd ~/ki_erkundung_ws && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 env -u CYCLONEDDS_URI \
     ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3'
```

Erwartung: `187 passed`.

**F2 – DDS-Einstellung des Lotsen an einen dauerhaften Ort kopieren**
(der Ordner `~/ki_trockenlauf_ki0/` darf später gelöscht werden):

```bash
mkdir -p ~/.config/amadeus && cp -n ~/ki_trockenlauf_ki0/cyclonedds_lotse.xml ~/.config/amadeus/cyclonedds_lotse.xml
```

**F3 – Startskript anlegen** (liegt nur auf diesem Rechner, nicht im
Repository). Es setzt genau die Umgebung von `umg`; Pfad der Pixi-Datei,
Domain und Middleware an `umg` angleichen:

```bash
mkdir -p ~/.local/share/amadeus/ki_erkundung
cat > ~/.local/share/amadeus/ki_erkundung/lotse_fenster_start.sh <<'ENDE'
#!/bin/bash
# Startet das Lotsen-Fenster (Lotsen-Dienst mit Anzeige) für Amadeus.
export ROS_DOMAIN_ID=42 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI="file://$HOME/.config/amadeus/cyclonedds_lotse.xml"
exec pixi run --manifest-path "$HOME/roboter_ws/src/robot_bringup/config/offboard_pixi.toml" \
     python3 "$HOME/ki_erkundung_ws/ki_erkundung/werkzeuge/lotse_fenster.py" --modell qwen3.5:9b
ENDE
chmod +x ~/.local/share/amadeus/ki_erkundung/lotse_fenster_start.sh
```

Findet die Desktop-Umgebung `pixi` nicht (anderer Suchpfad als im Terminal),
im Skript den vollen Pfad aus `command -v pixi` einsetzen.

**F4 – Symbol auf dem Desktop und im Programmmenü:**

```bash
D="$(xdg-user-dir DESKTOP)/Amadeus-Lotse.desktop"
cat > "$D" <<ENDE
[Desktop Entry]
Type=Application
Name=Amadeus Lotse
Comment=Lotsen-Dienst für Amadeus starten und anzeigen
Exec=$HOME/.local/share/amadeus/ki_erkundung/lotse_fenster_start.sh
Icon=applications-science
Terminal=false
Categories=Utility;
ENDE
chmod +x "$D"; gio set "$D" metadata::trusted true 2>&1 | tail -1
mkdir -p ~/.local/share/applications && cp "$D" ~/.local/share/applications/amadeus-lotse.desktop
```

**F5 – den alten Hintergrunddienst beenden und das Programm starten.**
Den am 21.11. von Hand gestarteten Dienst mit genau einem SIGINT an seine
PID beenden (die PID aus F0). Dann bittet der Agent Christopher, das Symbol
„Amadeus Lotse“ doppelt anzuklicken. Es öffnet sich ein Fenster des Browsers.
Danach prüfen und die Ausgabe berichten (sie enthält keine Adressen):

```bash
kill -INT <PID aus F0>; sleep 3; ps -ef | grep lotse_dienst.py | grep -v grep
# nach dem Doppelklick:
curl -s --noproxy '*' http://127.0.0.1:8765/api/zustand | python3 -c "import json,sys; z=json.load(sys.stdin); print(json.dumps({k: z[k] for k in ('modell','ollama','dienst','roboter','fremde_dienste')}, ensure_ascii=False, indent=1))"
tail -5 ~/.local/share/amadeus/ki_erkundung/lotse/lotse_dienst.log
```

Erwartung: `ollama.erreichbar` und `modell_vorhanden` wahr, `dienst.laeuft`
und `bereit` wahr, `fremde_dienste` leer. `roboter.im_netz` ist wahr, wenn
der Jetson eingeschaltet ist.

Christopher fragen und wörtlich notieren: Öffnet sich das Fenster? Zeigt es
oben „Bereit“? Ist etwas unklar oder fehlt etwas?

**Bedienung für Christopher:** Rechner einschalten, Symbol „Amadeus Lotse“
doppelt anklicken, fertig. Das Fenster zu schließen beendet nichts; ein
neuer Doppelklick öffnet es wieder. Beendet wird über „Programm beenden“
unten auf der Seite oder mit dem Herunterfahren des Rechners. **Nach KI-0N
bleibt das Programm einfach offen oder wird dort beendet;** der frühere
Schritt A6 entfällt damit.

**Rückfall:** die beiden `.desktop`-Dateien, das Startskript,
`~/.config/amadeus/cyclonedds_lotse.xml` und den Ordner
`~/.local/share/amadeus/ki_erkundung/lotse` löschen. Der Dienst lässt sich
weiter wie am 21.11. von Hand starten (archivierter Auftrag, Abschnitt N3).

**Bericht des KI-Rechners:** Datei `~/ki_erkundung_bericht_fenster.md` mit
HEAD, Testergebnis, den angelegten Dateien (Inhalt des Startskripts ohne
Adressen), der Ausgabe aus F5, Christophers Antworten und allem, was nicht
lief.

---

## Bericht

Datei `~/ki_erkundung_bericht_ki0n.md`, ohne Bilder und ohne Scans:

1. Stand (HEAD), Testergebnis, Status des Lotsen-Dienstes.
2. Der ganze Text aus `$KI/pruefung.md`.
3. Die Tabelle „Vorab festgelegte Erwartungen“ von oben, je Zeile mit dem,
   was gemessen wurde, und „trifft zu“ oder „trifft nicht zu“.
4. Je Aufnahme: aus `$KI/alle.txt` die Zeile der KI; aus `ergebnis.json` die
   vermessenen Öffnungen (Nummer, Breite, Entfernung, Richtung, zweite
   Kante); Christophers Antworten wörtlich; der eingetragene Befehl.
5. Der Text aus `$KI/auswertung.md`.
6. Bei neuen Ansichten: Bildrate, Scanrate, die Zeilen des
   Aufnahmewerkzeugs, Christophers Satz zur Stelle.
7. Alles, was nicht lief, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
