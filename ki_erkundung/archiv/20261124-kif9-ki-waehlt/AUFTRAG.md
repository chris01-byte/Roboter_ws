# Aktueller Auftrag der KI-Linie: KI-F9 – die KI wählt die Tür

**Erteilt am 23.11.2026.** Er wird aktiv, sobald der Projektinhaber ihn
übergibt. Er läuft auf dem **Jetson**, mit Christopher; auf dem
**KI-Rechner** muss das Lotsen-Fenster („Amadeus Lotse“) laufen.

**Warum es ihn gibt:** In KI-F8 ist Amadeus dreimal von drei in einem Ablauf
selbst durch die Labortür gefahren; die Tür hat dabei Christopher genannt
(Richtung). Danach hat der Projektinhaber entschieden (23.11.2026): **Jetzt
wählt die KI die Tür, zuerst mit Christophers Ja oder Nein vor der Fahrt.**
Gebaut ist dafür (nur Werkzeuge der KI-Linie, **kein Build**):

- Die Aufnahme der Blickrunde hält fest, wo Amadeus am Ende des Rundblicks in
  der Karte steht.
- `ki_tuer_waehlen.py` bereitet die Blickrunde auf, fragt die KI über den
  Lotsen-Dienst und schreibt die geprüfte Wahl mit ihrem Ort in der Karte in
  eine **Wahl-Datei** auf dem Roboter. Es fährt nicht und sendet nichts. Es
  zeigt die Wahl in einem Satz (Art, Breite, Entfernung, Richtung von
  Amadeus aus) mit der Begründung der KI.
- `fahrziel_senden.py --zur-tuer --wahl DATEI` misst neu, nimmt die
  türbreite Öffnung an dem Ort, den die KI gewählt hat, und macht dann
  denselben Ablauf wie in KI-F8 (gleich hindurch, oder erst davor und dann
  hindurch, in einer Mission). `fahrziel_senden.py --ende` schließt die
  wartende Mission ohne Fahrt (nach einem Nein oder ohne gültige Wahl).

**Neu gegenüber KI-F8 ist genau eines:** Die Tür nennt die KI, nicht
Christopher. Der Rundblick mit Kamera davor ist aus KI-1 am Roboter
erprobt (dort ohne Fahrt danach); die Kamera läuft nur während des
Rundblicks.

**Ohne Nahsensoren**, wie vom Projektinhaber am 22.11.2026 entschieden
(`nahsensoren:=false`): Amadeus sieht nichts unter etwa 75 cm Höhe, und der
Kollisionsmonitor bremst nicht. Christopher räumt den Weg frei und hat die
Hand am Not-Aus.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](archiv/20261121-ki0-erstes-sehen/),
[KI-0N](archiv/20261121-ki0n-nachmessen/),
[KI-0R](archiv/20261121-ki0r-nachrechnen/),
[KI-1](archiv/20261121-ki1-blickrunde/),
[KI-F1](archiv/20261122-kif1-erste-etappen/),
[KI-F2](archiv/20261122-kif2-tuerdurchfahrt/),
[KI-F3 und KI-F3b](archiv/20261122-kif3-tuer-gerade/),
[KI-F4](archiv/20261122-kif4-ersetzt/),
[KI-F5](archiv/20261123-kif5-ohne-nahsensoren/),
[KI-F6](archiv/20261123-kif6-anfahrt-gelungen/),
[KI-F7](archiv/20261123-kif7-erste-durchfahrt/),
[KI-F8](archiv/20261123-kif8-dreimal-durch/).

**Frage dieses Auftrags:** Wählt die KI nach dem Rundblick die Labortür, und
fährt Amadeus nach Christophers Ja in einem Ablauf selbst hindurch – zweimal,
von zwei verschiedenen Plätzen?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md`, Abschnitt 6a (v1.16, Schritt 1) |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. **Kein Build:** Release `kif8-20261123_2138` mit `~/roboter_worktrees/kif8.env`, beide unverändert. Unter `src/` hat sich seit dem Build von KI-F8 (`d61453c`) nichts geändert; neu sind nur Werkzeuge der KI-Linie (Python, direkt aus der Arbeitskopie) |
| Was neu ist | `blickrunde_aufnehmen.py` hält die Lage in der Karte am Ende fest; `ki_tuer_waehlen.py`; `fahrziel_senden.py --wahl` und `--ende`. Der Erkunder ist derselbe wie in KI-F8 |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif9.md`: Tests, Vorlauf, je Lauf Rundblick, Aufnahme, die Ausgabe von `ki_tuer_waehlen.py` und `fahrziel_senden.py`, die Meldungen des Erkunders, die Kriterien und Christophers Antworten wörtlich |
| Nicht-Ziele | Kein Build; keine eigene Code- oder Parameteränderung; keine Fahrt ohne Christophers Ja zu genau dieser Wahl; keine Fahrt nach Nummer oder Richtung eines Menschen; kein Nav2-Ziel; Kamera nicht während der Fahrt; keine Blattseite (Amadeus steht auf der Seite ohne Türblatt) |
| Rückfall | Nichts Neues am Jetson außer Aufnahmen, Wahl-Dateien und Protokollen unter `~/.local/share/amadeus/ki_erkundung/`. Release und `kif8.env` bleiben unverändert. Ohne `--wahl` ist `fahrziel_senden.py` wie in KI-F8 |
| Bereich und Freigabe | Laborraum und, für die Durchfahrt, der Flur unmittelbar hinter der Labortür (vom Projektinhaber am 21.11.2026 verlangt). Ohne Nahsensoren auf Entscheidung des Projektinhabers vom 22.11.2026. Höchstens eine Vorabfrage (Wunsch des Projektinhabers vom 23.11.2026, LAB-1); dazu je Lauf die Frage nach dem Ja zur Wahl der KI (Entscheidung des Projektinhabers vom 23.11.2026). Christopher ist dabei, die Hand am Not-Aus. 100 ms Anfahrzeit wie seit dem 15.11. |

## Fragen an Christopher – nur diese

Gefragt wird als Text, einzeln, ohne Auswahlfeld; Antworten wörtlich in den
Bericht.

1. **Vorab, genau einmal (F0)**, in Schritt 3, wörtlich:

   > „Gleich wählt die KI die Tür, zweimal von zwei Plätzen. Jedes Mal dreht
   > sich Amadeus zuerst einmal ganz um sich selbst (etwa anderthalb
   > Minuten), die Kamera nimmt dabei Bilder auf, und die KI auf dem
   > KI-Rechner sagt, welche Öffnung der Ausgang ist. Ich zeige dir ihre Wahl
   > und frage dich, ob er dorthin fahren soll; nur nach deinem ‚ja' fährt
   > er, in einem Ablauf wie zuletzt, und bleibt knapp einen halben Meter
   > hinter der Tür im Flur stehen. Er fährt **ohne Nahsensoren**: Was
   > niedriger als etwa 75 cm ist (Kisten, Taschen, Kabel, Schuhe,
   > Türstopper), sieht er nicht, und der Kollisionsmonitor bremst nicht.
   > Ist alles aufgebaut: auf dem KI-Rechner ‚Amadeus Lotse' geöffnet, die
   > Labortür ganz offen, im Laborraum, in der Tür und im Flur bis gut einen
   > Meter dahinter nichts Niedriges am Boden, nichts auf Amadeus, der Arm in
   > Transportstellung, Amadeus 1,5 bis 3 m vor der Tür auf der Seite ohne
   > Türblatt, rundherum mindestens 50 cm frei zum Drehen, und du stehst
   > seitlich, nicht zwischen ihm und der Tür, mit der Hand am Not-Aus? Wenn
   > du ‚ja' schreibst, starte ich; danach frage ich dich nur noch nach jeder
   > Wahl der KI und nach jedem Lauf.“

   Nur nach „ja“ weiter. Das „ja“ gilt auch als Bestätigung, dass Amadeus
   beim ersten Start stillsteht (`operator_stationary_confirmed:=true`).
2. **Je Lauf die Frage zur Wahl der KI (F-Wahl)**, siehe „Lauf k“, Schritt
   6. Nur sie gibt die Fahrt frei.
3. **Nach jedem Lauf genau eine Nachricht (F-Lauf)**, siehe „Lauf k“,
   Schritt 10. Christophers „weiter“ darin gilt als Bestätigung, dass
   Amadeus für den nächsten Start stillsteht.
4. **Nur in den Ausnahmen**, die unten ausdrücklich stehen (Lotsen-Dienst
   nicht bereit, Motorregler antworten nicht).

Keine weitere Frage, keine Frage nach freien Motoren, keine Bestätigung
unveränderter Laborbedingungen.

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push, **kein
  Build**;
- **jeder Stackstart dieses Auftrags mit `initial_scan_only:=true
  stage_drive_only:=true nahsensoren:=false`**, keiner ohne;
- schreibend nur: die Stackstarts, **je Lauf genau ein** Missionsstart, die
  Kamera und die Aufnahme in der zweiten Shell, `ki_tuer_waehlen.py` und
  `fahrziel_senden.py` genau so, wie es hier steht; kein `param set`,
  `lifecycle set`, `service call`, kein weiteres `topic pub`, keine
  Nav2-Ziele, kein Missionsstopp von Hand außer unter „Abbruch“;
- **kein Missionsstart, wenn `initial_scan_only` oder `stage_drive_only`
  nicht nachweislich `True` ist**;
- **`fahrziel_senden.py` sendet ein Fahrziel nur mit `--wahl` und nur nach
  Christophers „ja“ zu genau dieser Wahl.** Nie mit `--richtung`,
  `--nummer`, `--quelle mensch` zum Fahren, `--aufstellung-egal`,
  `--breite-min`, `--breite-max` oder `--vor`;
- Christopher stellt Amadeus nur zwischen den Läufen um, nie während eines
  Laufs;
- die Kamera läuft nur während des Rundblicks (Schritt 3 bis 5), nie
  während der Fahrt;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an Umgebungsdateien und Releases;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- kein eigenes Anzeigeprogramm, nichts im Vollbild;
- **keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht; die Wahl-Datei nie anzeigen** (sie enthält Koordinaten). Erlaubt
  sind die Zeilen der Werkzeuge mit Maßen vom Roboter aus.

## Vorab festgelegte Kriterien

„Kette“ heißt: `Begin navigating` 0-mal, „Direkter Explore-Befehl verworfen“
0-mal, „Odometrie kurzzeitig nicht frisch“ 0-mal, „process has died“ 0-mal,
„Interner Explorer-Fehler“ 0-mal, „Logger severity“ 0-mal.

Je Lauf:

| Kennung | Kriterium |
|---|---|
| N-1 Ohne Nahsensoren | kein Knoten `vl53_near_field`; `require_near_field` `False`; „TESTBETRIEB OHNE NAHSENSOREN“ im Log; „Robot to slowdown“ und „Robot to approach“ je 0 |
| R-1 Rundblick | „Etappenfahrt: Rundblick vollstaendig, X Grad“ mit X mindestens 355; danach Phase `stage_drive_wait_target` |
| W-1 Aufnahme | „Blickrunde geschrieben“, „ohne Scan verworfen“ höchstens ein Zehntel der Aufnahmen, „Lage in der Karte am Ende: festgehalten.“ |
| W-2 Wahl der KI | `ki_tuer_waehlen.py` `rc=0`; die Antwort kam in höchstens 120 s; Christopher: die gewählte Öffnung ist die Labortür („ja“) |
| W-3 Übergabe | „Zur Wahl der KI passt Öffnung N (die Mitten liegen X m auseinander)“ mit X höchstens 0,40; „Türachse aus der Wand neben der Tür“; Entscheidung „Durchfahrt“ oder „Anfahrt“ |
| T-2 Abschluss | „Durchfahrt abgeschlossen.“ und „Etappenfahrt abgeschlossen: … Quelle ki …; kein Nav2-Ziel“; Werkzeug `rc=0` |
| T-3 Ausrichten | je Punkt höchstens drei Zeilen „ausgerichtet um …“; der jeweils letzte „Restfehler“ höchstens 3,5 Grad |
| T-4 Durch die Tür | Christopher: steht ganz im Flur, nichts berührt, kein Eingriff, auch nicht beim Drehen |
| T-6 Kette | wie oben |

Gesamt: **G-1: zwei von zwei Läufen erfüllen alle Kriterien.** Sagt
Christopher zu einer Wahl „nein“, trifft W-2 für diesen Lauf nicht zu; dass
Amadeus dann stehen bleibt und die Mission mit „beendet ohne Fahrziel“
schließt, wird als **S-1 Einspruch wirkt** festgehalten.

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls -d ~/.local/share/amadeus/releases/kif8-20261123_2138 ~/roboter_worktrees/kif8.env ~/ki_trockenlauf_ki0/umgebung_we1.bash
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.
Fehlt eines der drei: berichten, Ende.

## Schritt 1 – Stand holen (kein Build)

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
git diff --stat d61453c HEAD -- src/ | tail -3; echo "src-Aenderungen: $(git diff --name-only d61453c HEAD -- src/ | wc -l)"
source ~/roboter_worktrees/kif8.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
mkdir -p "$SH_PR/kif9"
```

Erwartet: `src-Aenderungen: 0` (der Erkunder ist derselbe wie in KI-F8),
`rc=0`, `SH_REL` endet auf `kif8-20261123_2138`. Sonst: nichts starten,
berichten. **Jeder ROS-Befehl der ersten Shell beginnt mit `source
~/roboter_worktrees/kif8.env`.**

## Schritt 2 – Tests der KI-Linie

```bash
cd ~/roboter_worktrees/selbstheilung-v2
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3 ) | tee "$SH_PR/kif9/tests.txt"
```

Erwartung: `340 passed` (die 285 vom Stand der Blattseite und 55 neue zur
Wahl der KI). Bei Fehlschlägen nichts starten, berichten.

## Schritt 3 – die eine Frage (F0)

Christopher F0 stellen (Wortlaut oben). Nur nach „ja“ weiter.

## Schritt 4 – Vorlauf ohne Motorfreigabe (einmal, ohne Frage)

Prüft im Stand, ohne Motorsteuerung, ob die Kette bis zur Wahl technisch
läuft (LAB-1 §3). Amadeus bewegt sich nicht.

**Erste Shell:**

```bash
source ~/roboter_worktrees/kif8.env
D="$SH_PR/kif9/vorlauf"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  initial_scan_only:=true stage_drive_only:=true nahsensoren:=false \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/vorlauf"; L="$D/launch.log"
{ ros2 param get /explore_node initial_scan_only 2>&1
  ros2 param get /explore_node stage_drive_only 2>&1
  ros2 param get /explore_node stage_drive_target_wait_s 2>&1
  echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"
  echo "Traceback: $(grep -c Traceback "$L")"; } | tee "$D/pruefung.txt"
```

Erwartet: `True`, `True`, `420.0`, `vl53_near_field-Knoten: 0`, `False`,
`Testbetrieb im Log:` mindestens `2`, `Traceback: 0`.

**Zweite Shell** (die Kamera kommt wie in KI-1 aus der WE-1-Umgebung):

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_kif9; mkdir -p "$KI"; cd ~/roboter_worktrees/selbstheilung-v2
timeout 15 ros2 topic echo --once --full-length /ki_erkundung/lotse_status_json > "$KI/lotse_status.txt" 2>&1; cat "$KI/lotse_status.txt"
nohup env --default-signal=INT ros2 launch robot_bringup oak.launch.py pointcloud:=false \
  > "$KI/oak_vorlauf.log" 2>&1 < /dev/null & echo $! > "$KI/oak.pid"
sleep 25
timeout -s INT 15 ros2 topic hz /oak/semantic/rgb/compressed > "$KI/rate_vorlauf.txt" 2>&1; tail -2 "$KI/rate_vorlauf.txt"
python3 ki_erkundung/werkzeuge/blickrunde_aufnehmen.py --name kif9_vorlauf --dauer 10 > "$KI/vorlauf_aufnahme.txt" 2>&1; cat "$KI/vorlauf_aufnahme.txt"
kill -INT "$(cat "$KI/oak.pid")"; sleep 5
SECONDS=0; python3 ki_erkundung/werkzeuge/ki_tuer_waehlen.py --ueber-ros --name kif9_vorlauf_ > "$KI/vorlauf_wahl.txt" 2>&1; echo "rc=$? dauer_s=$SECONDS" | tee -a "$KI/vorlauf_wahl.txt"; cat "$KI/vorlauf_wahl.txt"
```

**Lotsen-Dienst nicht bereit (Ausnahme):** Steht in `lotse_status.txt`
nicht `"bereit": true`, Christopher einmal bitten: „Bitte öffne auf dem
KI-Rechner ‚Amadeus Lotse' und schreib ‚fertig'.“ Danach die Zeile mit
`lotse_status.txt` wiederholen; ist er dann nicht bereit: Kamera und Stack
beenden, berichten, Ende.

Erwartet: Rate mindestens 1,8 Hz; „Blickrunde geschrieben“ und „Lage in der
Karte am Ende: festgehalten.“; von `ki_tuer_waehlen.py` eine Zeile „Frage 1
an …“ mit einer Antwort (nicht „keine Antwort“) und `rc` 0 oder 2 (im Stand
sieht die Kamera nur eine Richtung; ob die KI dabei eine Öffnung wählt, ist
hier gleich). Ebenso in Ordnung: `rc=4` mit „Keine Öffnung vermessen, die
die KI wählen könnte“ (dann wird die KI im Stand nicht gefragt). War
`rc=0`, in der **ersten Shell** nur messen (sendet nichts):

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/vorlauf"
WAHL=$(ls -t ~/.local/share/amadeus/ki_erkundung/wahl/kif9_vorlauf_*_wahl.json | head -1)
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --wahl "$WAHL" --nur-messen --hinter 0.45 2>&1 | tee "$D/messen.txt"
```

Dann in jedem Fall den Stack beenden:

```bash
source ~/roboter_worktrees/kif8.env; kill -INT "$(cat "$SH_PR/kif9/vorlauf/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Fehlt „Lage in der Karte am Ende: festgehalten.“, meldet
`ki_tuer_waehlen.py` eine fehlende Lage oder Runde (`rc=4` aus diesem Grund),
kommt keine Antwort der KI („keine Antwort“, `rc` 3 oder 5) oder weicht eine
Prüfzeile ab: nichts weiter starten, berichten. Der Vorlauf braucht keine
Wahl der Labortür.

---

## Lauf k (k = 1, 2)

Für jeden Lauf dieselben Schritte; Dateien unter `$SH_PR/kif9/lauf$k` und
`~/ki_trockenlauf_kif9/lauf$k`. Vor Lauf 2 hat Christopher „weiter“
geschrieben (Schritt 10 von Lauf 1).

### 1 – scharfer Start (erste Shell)

```bash
source ~/roboter_worktrees/kif8.env; k=1        # 2 im zweiten Lauf
D="$SH_PR/kif9/lauf$k"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  initial_scan_only:=true stage_drive_only:=true nahsensoren:=false \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
```

### 2 – Prüfungen (nach etwa 70 s, ohne Frage)

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/lauf$k"; L="$D/launch.log"
grep -n "Anfahrverhalten bestaetigt" "$L" | tee "$D/anfahrzeit.txt"
{ ros2 param get /explore_node initial_scan_only 2>&1
  ros2 param get /explore_node stage_drive_only 2>&1
  echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"; } | tee "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung.txt"
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`;
`True`, `True`, `vl53_near_field-Knoten: 0`, `False`, `Testbetrieb im Log:`
mindestens `2`; Prüfskript Exit 0 (die Prüfung der Eigenechos entfällt, sie
gilt den Nahsensoren). **Trifft etwas nicht zu (nach einer Wiederholung bei
„erreichbar“, „nicht deklariert“, „Graph unvollständig“): keine Mission,
Stack geordnet beenden (Schritt 9), berichten, Ende.**

**Radsensor beim Start gesperrt (Ausnahme, ohne Frage):** wie in KI-F8: Die
Zeile zur Anfahrzeit ist da, „Modbus-Fehler“ steht 0-mal im Log, und die
Vorprüfung fällt **nur** im Bereich „D Quellen“ durch. Dann:

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/lauf$k"
uptime | tee "$D/last_bei_sperre.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/radsensor_zustand.py" 2>&1 | tee "$D/radsensor.txt"
kill -INT "$(cat "$D/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
for f in launch.log launch.pid launch_start.txt anfahrzeit.txt schalter.txt vorpruefung.json vorpruefung.txt; do \
  [ -e "$D/$f" ] && mv "$D/$f" "$D/erster_start_$f"; done
```

Christopher dazu nur sagen (keine Frage): „Der Radsensor hat sich beim
Hochfahren gesperrt; ich starte einmal neu, Amadeus fährt dabei nicht.“
Mindestens 30 s nach „alles beendet“ **genau ein** weiterer Start (Schritt
1, dann 2). Sperrt er sich wieder: Stack beenden, berichten, Ende.

**Motorregler antworten nicht (Ausnahme):** Fehlt die Zeile zur Anfahrzeit
und steht im Log „Modbus-Fehler Motor … No response received“: Stack
beenden und Christopher sagen: „Die Motorregler antworten nicht; so kann ich
nicht starten.“ Sagt er, die Motoren seien frei, ist **genau ein** weiterer
Start erlaubt.

### 3 – Kamera und Aufnahme starten (zweite Shell)

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
KI=~/ki_trockenlauf_kif9; k=1; mkdir -p "$KI/lauf$k"; cd ~/roboter_worktrees/selbstheilung-v2
nohup env --default-signal=INT ros2 launch robot_bringup oak.launch.py pointcloud:=false \
  > "$KI/lauf$k/oak.log" 2>&1 < /dev/null & echo $! > "$KI/oak.pid"
sleep 25
timeout -s INT 15 ros2 topic hz /oak/semantic/rgb/compressed > "$KI/lauf$k/rate.txt" 2>&1; tail -2 "$KI/lauf$k/rate.txt"
nohup env --default-signal=INT python3 ki_erkundung/werkzeuge/blickrunde_aufnehmen.py \
  --name kif9_lauf$k --dauer 420 > "$KI/lauf$k/aufnahme.txt" 2>&1 < /dev/null & echo $! > "$KI/aufnahme.pid"
sleep 3; cat "$KI/lauf$k/aufnahme.txt"
```

Kommen keine Bilder (Rate unter 1,8 Hz): keine Mission; Aufnahme, Kamera und
Stack beenden, berichten.

### 4 – Mission starten: erst der Rundblick (erste Shell)

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/lauf$k"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
```

Etwa alle 20 s (nur lesend):

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/lauf$k"
echo "seit Missionsstart: $(( $(date +%s) - $(date -d "$(cat "$D/missionsstart.txt")" +%s) )) s"
timeout 5 ros2 topic echo --once --full-length /explore/status_json 2>&1 | grep -oE '"(state|phase|message)": "[^"]*"' | head -3
```

Amadeus dreht sich einmal ganz herum und bleibt stehen. Sobald die Phase
`stage_drive_wait_target` lautet („Etappenfahrt: warte auf das Fahrziel der
KI-Linie; noch … s. Der Roboter steht.“), **ohne Pause** weiter mit Schritt
5. Ab da wartet der Erkunder höchstens 420 s auf ein Fahrziel und schließt
die Mission danach selbst, ohne zu fahren. Endet die Mission vorher oder
ist sie nach 300 s noch nicht in dieser Phase: Abbruch (unten).

**Christopher drückt den Not-Aus, bevor etwas berührt wird:** wenn Amadeus
beim Rundblick **fährt** (vor oder zurück, auch nur ein kurzes Stück), wenn
eine Ecke beim Drehen näher als zwei Finger breit an etwas herankommt, bei
ungewöhnlichem Geräusch oder starkem Schwanken.

### 5 – Aufnahme beenden, die KI fragen (zweite Shell)

```bash
KI=~/ki_trockenlauf_kif9; cd ~/roboter_worktrees/selbstheilung-v2
kill -INT "$(cat "$KI/aufnahme.pid")"; sleep 4; tail -6 "$KI/lauf$k/aufnahme.txt"
kill -INT "$(cat "$KI/oak.pid")"; sleep 5; echo "Kamera-Fehlerzeilen: $(grep -ciE 'error' "$KI/lauf$k/oak.log")"
SECONDS=0; python3 ki_erkundung/werkzeuge/ki_tuer_waehlen.py --ueber-ros --name kif9_lauf${k}_ > "$KI/lauf$k/wahl.txt" 2>&1; echo "rc=$? dauer_s=$SECONDS" | tee -a "$KI/lauf$k/wahl.txt"; cat "$KI/lauf$k/wahl.txt"
```

Fehlt „Lage in der Karte am Ende: festgehalten.“, meldet
`ki_tuer_waehlen.py` das ebenso (`rc=4`), und die KI wird nicht gefragt.

### 6 – Christophers Ja oder Nein (F-Wahl)

**Nur bei `rc=0`.** Christopher sofort fragen, wörtlich mit den Zeilen aus
`wahl.txt` (ohne die Pfade):

> „Die KI hat gewählt. <die Zeile ‚Die KI wählt Nr. …' wörtlich> <die Zeile
> ‚Begründung der KI: …' wörtlich> Was sie in jeder Nummer sieht: <die
> Zeilen unter ‚Was die KI in den Nummern sieht' wörtlich> Die Bilder mit den
> Nummern zeigt das Lotsen-Fenster auf dem KI-Rechner. Ist die gewählte
> Öffnung die Labortür, und soll Amadeus hindurchfahren? Schreib ‚ja' oder
> ‚nein'. (Der Erkunder wartet noch etwa … Minuten.)“

Die Minuten: 7 minus die Zeit seit der Phase `stage_drive_wait_target`.

**Bei `rc` ≠ 0 keine Frage:** gleich Schritt 7, Fall „kein Ja“.

### 7 – fahren oder beenden (erste Shell)

- **Christopher schreibt „ja“:**

  ```bash
  source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/lauf$k"
  WAHL=$(ls -t ~/.local/share/amadeus/ki_erkundung/wahl/kif9_lauf${k}_*_wahl.json | head -1); echo "$WAHL" > "$D/wahl_pfad.txt"
  python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --zur-tuer --wahl "$WAHL" --hinter 0.45 --warten 60 --beobachten 600 2>&1 | tee "$D/werkzeug.txt"; echo "rc=${PIPESTATUS[0]}"
  ```

  Das Werkzeug misst neu, sucht die gewählte Tür an ihrem Ort, sendet bei
  „Anfahrt“ zuerst die Anfahrt, misst danach im Stand neu und sendet in
  derselben Mission die Durchfahrt. Passt etwas nicht, sendet es dem
  Erkunder „Ende“; die Mission schließt dann von selbst. **Kein zweiter
  Missionsstart, kein Stopp von Hand.**

- **Kein Ja** („nein“, eine andere Antwort, oder `ki_tuer_waehlen.py` mit
  `rc` ≠ 0):

  ```bash
  source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/lauf$k"
  python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --ende --quelle QUELLE --warten 60 2>&1 | tee "$D/werkzeug.txt"; echo "rc=${PIPESTATUS[0]}"
  ```

  `QUELLE` ist `mensch` nach Christophers Nein, sonst `ki`. Amadeus fährt
  nicht; die Mission schließt mit „beendet ohne Fahrziel“.

**Christopher drückt den Not-Aus (oder den Stopp in der App), bevor etwas
berührt wird,** und sofort, wenn doch etwas Niedriges in den Weg gerät oder
jemand den Weg kreuzt; ohne Nahsensoren hält Amadeus davor nicht von selbst
an. Drehen auf der Stelle, kurzes Stehenbleiben zwischen den Etappen und
vor der Durchfahrt (Neumessung), kleines Nachstellen der Richtung und
langsames Kriechen neben dem Türblatt sind gewollt.

### 8 – sichern (Amadeus bleibt stehen, der Stack läuft noch)

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif9/lauf$k"
date -Iseconds > "$D/ende.txt"
grep -n "Etappenfahrt\|Fahrziel\|Mission beendet" "$D/launch.log" | tee "$D/etappen.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died" \
  "Interner Explorer-Fehler" "Logger severity"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
```

Dazu aus den Sekundenzeilen von `base_hardware` zwischen Missionsstart und
Ende: größtes |v| und |w|.

### 9 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif8.env; kill -INT "$(cat "$SH_PR/kif9/lauf$k/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Läuft die Kamera noch (Schritt 5 nicht erreicht): vorher
`kill -INT "$(cat ~/ki_trockenlauf_kif9/oak.pid)"` und die Aufnahme ebenso.

### 10 – eine Nachricht an Christopher (F-Lauf)

Ein Satz zum Ergebnis aus `werkzeug.txt` (zum Beispiel „Lauf 1: Rundblick
362°, die KI wählte Nr. 2 (offene Tür), Anfahrt 1,4 m, dann Durchfahrt
2,1 m, ‚Durchfahrt abgeschlossen'.“), dann:

- nach Lauf 1: „Steht er ganz im Flur, und hat er nichts berührt, auch nicht
  beim Drehen? Dann stell ihn bitte für Lauf 2 an einen **anderen** Platz im
  Laborraum, 1,5 bis 3 m vor der Tür auf der Seite ohne Türblatt, rundherum
  50 cm frei, Tür ganz offen, nichts auf ihm, und schreib ‚weiter', wenn er
  still steht.“
- nach Lauf 2: „Steht er ganz im Flur, und hat er nichts berührt, auch nicht
  beim Drehen?“
- Ist er nicht gefahren (kein Ja oder „Nichts gesendet“): statt „Steht er
  ganz im Flur …“: „Er ist nicht gefahren. Hat er beim Drehen etwas
  berührt?“

**Danach:**
- Antwort mit „weiter“ und ohne Berührung oder Eingriff: nächster Lauf.
- **Berührung oder Eingriff:** keine weiteren Läufe, berichten.
- **Lauf ohne Durchfahrt** (kein Ja, `rc` ≠ 0 oder kein „Durchfahrt
  abgeschlossen.“): Bittet Christopher ausdrücklich darum, wird **dieser
  Lauf genau einmal** wiederholt (`k=1w` oder `k=2w`, auch in den Namen der
  Aufnahme). Sonst: keine weiteren Läufe, berichten.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Kamera,
  Aufnahme und Stack geordnet beenden) bei Berührung, bei einer anderen
  Bewegung als angekündigt, bei ungewöhnlichem Geräusch, starkem Schwanken
  oder Rauch. Danach nichts mehr starten; nur berichten.
- Hängt ein Werkzeug (keine neue Zeile über 5 Minuten, Amadeus steht), oder
  endet der Rundblick nicht (Schritt 4): einmal `ros2 topic pub --once
  /mission_manager/command_json std_msgs/msg/String "{data:
  '{\"type\":\"cancel\"}'}"`, dann Kamera und Aufnahme beenden, Schritt 8
  und 9, berichten, keine weiteren Läufe.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif9.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen, ohne den Inhalt der Wahl-Dateien:

1. Stand (HEAD), die Zeile `src-Aenderungen`, Tests.
2. F0 und Christophers Antwort wörtlich; der Vorlauf (`pruefung.txt`,
   `lotse_status.txt` ohne Adressen, Rate, `vorlauf_aufnahme.txt`,
   `vorlauf_wahl.txt` ganz, `messen.txt` ganz, falls vorhanden).
3. **Je Lauf:** Start, Prüfungen (bei der Ausnahme „Radsensor“ der ganze
   Inhalt von `radsensor.txt` und `last_bei_sperre.txt`), Rate,
   `aufnahme.txt` (letzte Zeilen), **`wahl.txt` ganz** (ohne Pfade), die
   Frage F-Wahl und Christophers Antwort wörtlich, die Minuten, die der
   Erkunder da noch wartete, **`werkzeug.txt` ganz**, `etappen.txt`,
   `zaehler.txt`, größtes |v| und |w|, die Nachricht F-Lauf und Christophers
   Antwort wörtlich.
4. Die Tabelle N-1, R-1, W-1, W-2, W-3, T-2, T-3, T-4, T-6 je Lauf mit dem
   Gemessenen und „trifft zu“ oder „trifft nicht zu“, dazu S-1, falls
   Christopher „nein“ sagte, und G-1.
5. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
