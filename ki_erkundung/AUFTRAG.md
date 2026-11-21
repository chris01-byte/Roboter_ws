# Aktueller Auftrag der KI-Linie: KI-0N – Nachmessen (im Stand, ohne Bewegung)

**Erteilt am 21.11.2026.** Er wird aktiv, sobald der Projektinhaber ihn
übergibt. Er läuft auf dem **Jetson**; der KI-Rechner muss nur eingeschaltet
sein und der Lotsen-Dienst dort laufen.

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
Christopher bitten, den KI-Rechner einzuschalten; dort startet der Agent den
Dienst wie am 21.11. (Befehl im Abschnitt „KI-Rechner“ unten).

### N1 – Stand holen und Tests

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short | head -5 && \
  git pull --ff-only && git rev-parse HEAD
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -5 )
```

Erwartung: `178 passed`.

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

## KI-Rechner

Der Lotsen-Dienst vom 21.11. lief nach Teil B weiter. Der KI-Rechner braucht
den neuen Stand nicht: Am Dienst hat sich nichts geändert.

Läuft er nicht mehr (Rechner war aus), dort starten, in der Umgebung `umg`
aus dem archivierten Auftrag (A0) und mit der Kopie der DDS-Einstellung, die
für den Lauf am 21.11. angelegt wurde. Liegt sie nicht unter dem genannten
Pfad, den Pfad aus dem damaligen Verlauf nehmen oder sie nach dem
archivierten Auftrag, Abschnitt N3, neu anlegen:

```bash
L=~/ki_trockenlauf_ki0/cyclonedds_lotse.xml
umg "export CYCLONEDDS_URI=file://$L; nohup env --default-signal=INT python3 \
     ~/ki_erkundung_ws/ki_erkundung/werkzeuge/lotse_dienst.py --modell qwen3.5:9b \
     > ~/ki_trockenlauf_ki0/lotse_dienst.log 2>&1 < /dev/null & echo \$! > ~/ki_trockenlauf_ki0/lotse_dienst.pid"
sleep 5; tail -3 ~/ki_trockenlauf_ki0/lotse_dienst.log
```

**Nach diesem Auftrag den Dienst beenden** (das ist der offene Schritt A6):

```bash
kill -INT "$(cat ~/ki_trockenlauf_ki0/lotse_dienst.pid)"; sleep 2
tail -20 ~/ki_trockenlauf_ki0/lotse_dienst.log; systemctl is-active amadeus-ki.service
```

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
