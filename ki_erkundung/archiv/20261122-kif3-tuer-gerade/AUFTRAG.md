# Aktueller Auftrag der KI-Linie: KI-F3 – durch die Tür: erst von vorn, dann vom Platz im Raum

**Erteilt am 22.11.2026 (abends); zweiter Anlauf „KI-F3b“ seit 22.11.2026
(spät).** Er wird aktiv, sobald der Projektinhaber ihn übergibt. Er läuft
auf dem **Jetson**, mit Christopher. Der KI-Rechner wird nicht gebraucht;
Kamera und KI laufen in diesem Auftrag nicht.

**Erster Anlauf (22.11., 22:03 bis 22:12):** Aufstellen und Messen passten
beim ersten Mal. Im scharfen Stack hatte sich der Radsensor beim Hochfahren
selbst gesperrt (Encoder-Zeitwache `fault_latched`,
`encoder_timing_continuity_unproven`); die Vorprüfung fiel durch, es gab
keine Mission und keine Bewegung. Für diesen bekannten Fall (zuerst SH-4,
04.11.) kannte der Auftrag keinen Weg. Neu ist die Ausnahme „Radsensor beim
Start gesperrt“ unter B1: einmal sichern, was die Zeitwache meldet, dann
genau ein neuer scharfer Start. Prüfdateien jetzt unter `pruefung/kif3b/`,
Bericht `~/ki_erkundung_bericht_kif3b.md`.

**Warum es ihn gibt:** In KI-F2 hielt Amadeus nach 0,35 m an und kam nicht
bis zur Tür. Der Halt war richtig; falsch war der geplante Weg: erst schräg
zu einem Punkt auf der Türachse, dann dort zur Tür drehen. Diese schräge
Strecke führte rechnerisch 1,5 cm an der Spitze des offenen Türblatts
vorbei. **Jetzt fährt Amadeus auf einer geraden Linie von seinem Platz durch
die Türmitte**, und das Werkzeug prüft vorher am Laserbild, dass links und
rechts dieser Linie 0,30 m frei sind.

**Zwei Stufen:** In Stufe 1 stellt Christopher Amadeus vor die Tür, und er
fährt gerade hindurch. In Stufe 2 steht Amadeus irgendwo im Raum, **fährt
selbst vor die Tür** und dann hindurch. Der Projektinhaber hat das
Davorstellen von Hand als Rückschritt gegenüber den früheren Durchfahrten
benannt (22.11.2026); Stufe 2 nimmt es weg. Stufe 2 läuft nur, wenn Stufe 1
alle Kriterien erfüllt hat.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](../20261121-ki0-erstes-sehen/),
[KI-0N](../20261121-ki0n-nachmessen/),
[KI-0R](../20261121-ki0r-nachrechnen/),
[KI-1](../20261121-ki1-blickrunde/),
[KI-F1](../20261122-kif1-erste-etappen/),
[KI-F2](../20261122-kif2-tuerdurchfahrt/).

**Fragen dieses Auftrags:** (1) Kommt Amadeus, mittig vor die offene
Labortür gestellt, auf der geraden Linie durch die Türmitte in einem Zug
hindurch? (2) Findet er von einem Platz im Raum selbst vor die Tür und kommt
dann ohne Hilfe hindurch?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md`, Abschnitt 6a |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. **Kein neuer Build:** Es läuft der Release `kif1-20261122_1515` mit `~/roboter_worktrees/kif1.env`, wie in KI-F1 und KI-F2. Am Erkunder hat sich nichts geändert (Schritt 1 prüft das); geändert ist nur das Werkzeug `fahrziel_senden.py`, und das läuft aus der Arbeitskopie |
| Was neu ist | Keine neue Verhaltensänderung am Roboter: derselbe Schalter `stage_drive_only:=true`. Neu in Stufe 1 ist das Ziel: zwei Punkte auf der geraden Linie vom Standplatz durch die Türmitte (1,2 m vor und 0,45 m hinter der Türlinie), und die Prüfung des Freiraums neben dieser Linie vor dem Senden. Neu in Stufe 2: die **Anfahrt** (`--vor-die-tuer`): zu einem Punkt auf der Türachse, dort zur Tür drehen, ein Stück auf sie zu; danach neu messen und wie in Stufe 1 hindurch. Dafür gibt es in Stufe 2 zum ersten Mal **zwei Missionsstarts in einem Stacklauf** |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif3b.md`: die Messungen im Stand wörtlich, die Fahrt mit den Meldungen des Erkunders und des Werkzeugs, die Kriterien und Christophers Antworten wörtlich |
| Nicht-Ziele | Keine KI, keine Kamera, kein Rundblick, kein Nav2-Ziel; kein Build; keine eigene Code- oder Parameteränderung; je Stufe keine Wiederholung der Fahrt |
| Rückfall | Es wird nichts angelegt außer Prüfdateien unter `pruefung/kif3b/` im vorhandenen Release-Ordner. Ohne das Startargument verhält sich der Stack wie am 19.11. |
| Bereich und Freigabe | Laborraum und, für die Durchfahrt, der Flur unmittelbar hinter der Labortür: vom Projektinhaber am 21.11.2026 ausdrücklich verlangt und mit der Übergabe dieses Auftrags für die Durchfahrten dieses Auftrags freigegeben (eine je Stufe). Christopher ist dabei, die Hand am Not-Aus. 100 ms Anfahrzeit wie seit dem 15.11. |
| Stufe 2 | Läuft nur, wenn der Projektinhaber sie in der Übergabe nennt **und** Stufe 1 die Kriterien T-1 bis T-6 erfüllt hat |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push, kein
  Build;
- schreibend nur: die Stackstarts dieses Auftrags, die Missionsstarts, die
  hier stehen (Stufe 1: **genau einer**; Stufe 2: **genau zwei**, einer für
  die Anfahrt und einer für die Durchfahrt), je Stufe höchstens **ein**
  Missionsstopp und das Werkzeug `fahrziel_senden.py` genau so, wie es hier
  steht; kein `param set`, `lifecycle set`, `service call`, kein weiteres
  `topic pub`, keine Nav2-Ziele;
- **kein Missionsstart, wenn `stage_drive_only` nicht nachweislich `True`
  ist**; keiner für eine Durchfahrt, solange die letzte Messung nicht
  **beides** meldet: „Aufstellung passt.“ und „Weg passt.“; keiner für die
  Anfahrt, solange sie nicht „Anfahrt passt.“ meldet;
- das Werkzeug nie mit `--aufstellung-egal`, `--breite-min`, `--breite-max`
  oder `--vor` aufrufen;
- `initial_scan_only` wird nie gesetzt und muss `False` melden;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`; `operator_stationary_confirmed:=true` nur nach
  Christophers „ja“;
- **jede Fahrt gibt es genau einmal** (Stufe 1: die Durchfahrt; Stufe 2:
  die Anfahrt und die Durchfahrt). Bricht eine ab oder hält sie an, wird
  sie nicht wiederholt, und es folgt keine weitere Fahrt. (Neu aufstellen
  und messen im Stand ist keine Fahrt und darf wiederholt werden.) Einzige
  Ausnahmen stehen unter „Motorregler antworten nicht“, „Radsensor beim
  Start gesperrt“ und „Nichts gesendet“;
- keine Frage vorab, ob die Motoren frei sind, und keine Fragerunde zu
  unveränderten Laborbedingungen (LAB-1). Gefragt wird nur, was in diesem
  Auftrag wörtlich als Frage steht;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an den Umgebungsdateien und an
  bestehenden Releases (außer neuen Prüfdateien unter `pruefung/kif3b/`);
- Amadeus wird nur von Hand umgestellt, wenn kein Stack mit Motorfreigabe
  läuft;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- kein eigenes Anzeigeprogramm, nichts im Vollbild;
- Fragen an Christopher als Text, einzeln, ohne Auswahlfeld; Antworten
  wörtlich;
- keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht.

## Vorab festgelegte Kriterien

„Kette“ heißt: `Begin navigating` 0-mal, „Direkter Explore-Befehl verworfen“
0-mal, „Odometrie kurzzeitig nicht frisch“ 0-mal, „process has died“ 0-mal.

| Kennung | Kriterium |
|---|---|
| T-1 Vermessung | Mittig vor der Tür meldet das Werkzeug eine türbreit vermessene Öffnung (0,65 bis 0,95 m; erwartet 0,72 bis 0,80 m), „Aufstellung passt.“ und „Weg passt.“ mit mindestens 0,30 m frei links und rechts der Fahrlinie |
| T-2 Abschluss | Meldung „Etappenfahrt abgeschlossen: … Quelle mensch; kein Nav2-Ziel“ mit höchstens 10 Etappen |
| T-3 Ausrichten | je Punkt höchstens drei Zeilen „ausgerichtet um …“; der jeweils letzte „Restfehler“ höchstens 3,5 Grad |
| T-4 Durch die Tür | Christopher: Amadeus steht ganz im Flur, auch die Hinterkante ist durch; nichts berührt, kein Eingriff |
| T-5 Abstand | Christopher: an Türpfosten und Türblatt blieb mindestens eine Handbreit |
| T-6 Kette | wie oben |

Für Stufe 2:

| Kennung | Kriterium |
|---|---|
| S-1 Anfahrt gemessen | Von einem Platz, an dem die Aufstellung von Hand nicht passt, meldet das Werkzeug eine türbreit vermessene Öffnung und „Anfahrt passt.“ |
| S-2 Anfahrt gefahren | Meldung „Etappenfahrt abgeschlossen: … Quelle mensch; kein Nav2-Ziel“; Christopher: Amadeus steht vor der Tür mit Blick zur Tür, nichts berührt, kein Eingriff |
| S-3 Danach passt es | Die Messung nach der Anfahrt meldet „Aufstellung passt.“ und „Weg passt.“, ohne dass jemand Amadeus angefasst hat |
| S-4 Durch die Tür | wie T-2 und T-4 |
| S-5 Abstand | wie T-5 |
| S-6 Kette | wie T-6, über den ganzen Stacklauf der Stufe 2 |

Keine Erwartung gibt es zu „Robot to slowdown“ und „Robot to approach“ (der
Kollisionsmonitor darf an Tür und Blatt bremsen). Hält der Erkunder mit
„Nahbereich vor dem Roboter nicht frei“ oder „Streifen vor dem Roboter nicht
frei“ an, ist das ein Befund: berichten, nicht wiederholen. Das Werkzeug
schreibt dann in seine letzte Zeile, was in der Kostenkarte vor dem Roboter
belegt ist; diese Zeile gehört in den Bericht.

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls -d ~/.local/share/amadeus/releases/kif1-20261122_1515 ~/roboter_worktrees/kif1.env
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.
Fehlt der Release oder die Umgebungsdatei: berichten, Ende.

## Schritt 1 – Stand holen und prüfen, dass der Release noch passt

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
git diff --stat baa16b7 HEAD -- src/ | tail -3; echo "zeilen=$(git diff --stat baa16b7 HEAD -- src/ | wc -l)"
source ~/roboter_worktrees/kif1.env; echo "rc=$? $SH_REL"; mkdir -p "$SH_PR/kif3b"
```

Erwartet: `zeilen=0` (am Quelltext der Pakete hat sich seit dem Build des
Release nichts geändert) und `SH_REL` endet auf `kif1-20261122_1515`. Sonst:
nichts starten, berichten. **Jeder ROS-Befehl dieses Auftrags beginnt mit
`source ~/roboter_worktrees/kif1.env`.**

## Schritt 2 – Tests des Werkzeugs

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && ( source /opt/ros/humble/setup.bash; \
  env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3 )
```

Erwartung: `256 passed`. Bei Fehlschlägen nichts starten, berichten.

---

# Stufe 1 – von vorn durch die Tür

## Teil A – Aufstellen und Messen (ohne Motorfreigabe, nichts fährt)

Der Stack startet **ohne** `active_drive` und ohne `enable_auto_explore`;
die Basis wird nicht bestromt (LAB-1 §3). In Teil A wird keine Mission
gesendet. Christopher darf Amadeus zwischen den Messungen umstellen.

### A1 – Aufstellen und Stack ohne Motorfreigabe

Anweisung: „Bitte stelle Amadeus **mittig vor die offene Labortür, etwa 2 m
davor, den Blick gerade durch die Tür**. Die Tür steht so weit offen wie
möglich und ist gesichert. Zwischen Amadeus und der Tür und in der Tür
liegt und steht nichts.“ Frage: „Steht Amadeus so still, und bleibt er
während des Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif1.env
D="$SH_PR/kif3b"; mkdir -p "$D"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  stage_drive_only:=true \
  > "$D/launch_stand.log" 2>&1 < /dev/null &
echo $! > "$D/launch_stand.pid"; cat "$D/launch_stand.pid"; date -Iseconds
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter_stand.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter_stand.txt"
grep -c "Traceback" "$D/launch_stand.log"
```

Erwartet: `True`, `False`, `0`.

### A2 – messen, bis Aufstellung und Weg passen

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"; K=1
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen_$K.txt"
```

Das Werkzeug nennt unter „Türbreit vermessen“ jede passende Öffnung mit
zwei Zeilen: die Lage („Aufstellung passt.“ oder was zu ändern ist) und die
Fahrlinie („Weg passt.“ oder was zu ändern ist).

- **„Aufstellung passt nicht: …“ oder „Weg passt nicht: …“:** Christopher den
  Hinweis wörtlich nennen (zum Beispiel „bitte etwa 15 cm nach rechts
  versetzen“), er stellt um, dann mit `K=2`, `K=3` … erneut messen.
- **„Keine Öffnung ist türbreit vermessen“:** Christopher sagen: „Von hier
  wird die Tür nicht als Tür gemessen. Bitte stelle ihn genauer mittig vor
  die Tür.“ Dann erneut messen.
- Höchstens acht Messungen. Passt es dann nicht: Stack beenden, berichten,
  Ende.

Sobald eine Messung **beides** meldet, „Aufstellung passt.“ und „Weg
passt.“, Christopher einmal fragen: „Ich messe geradeaus eine Öffnung,
**B** m breit und **E** m entfernt. Ist das die Labortür?“ (B und E aus der
Tabelle.) Bei „nein“: wie „passt nicht“ behandeln. Bei „ja“: **Amadeus
bleibt ab jetzt genau so stehen.**

### A3 – Stack beenden

```bash
source ~/roboter_worktrees/kif1.env; kill -INT "$(cat "$SH_PR/kif3b/launch_stand.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

---

## Teil B – die Fahrt durch die Tür

### B1 – Ansage und scharfer Start

Christopher sagen: „Gleich fährt Amadeus in kurzen Etappen **geradeaus auf
die Türmitte zu**, ohne Umweg. Gut einen Meter vor der Tür stellt er die
Richtung nach, wenn nötig, fährt hindurch und bleibt knapp einen halben
Meter dahinter im Flur stehen; das dauert etwa zwei Minuten. Du stehst
seitlich im Laborraum auf der Seite ohne Türblatt, nicht zwischen Amadeus
und der Tür, nicht in der Tür und nicht im Flur vor ihm, mit der Hand am
Not-Aus.“ Frage: „Steht Amadeus unverändert, und bleibt er während des
Starts (etwa eine Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif1.env
D="$SH_PR/kif3b"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  stage_drive_only:=true \
  > "$D/launch.log" 2>&1 < /dev/null &
echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
grep -n "Anfahrverhalten bestaetigt" "$D/launch.log" | tee "$D/anfahrzeit.txt"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung.txt"
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`;
`True` (Etappenfahrt) und `False` (Rundblick); Prüfskript Exit 0 wie in
KI-F2. **Trifft etwas davon nicht zu (nach einer Wiederholung bei
„erreichbar“, „nicht deklariert“, „Graph unvollständig“): keine Mission,
Stack geordnet beenden, berichten.**

**Motorregler antworten nicht (Ausnahme):** Fehlt die Zeile zur Anfahrzeit
und steht im Log „Modbus-Fehler Motor … No response received“, den Stack
geordnet beenden und Christopher den Befund in einem Satz melden: „Die
Motorregler antworten nicht; so kann ich nicht starten.“ Sagt er daraufhin,
die Motoren seien frei, ist **genau ein** weiterer scharfer Start erlaubt.

**Radsensor beim Start gesperrt (Ausnahme):** Die Zeile zur Anfahrzeit ist
da, „Modbus-Fehler“ steht 0-mal im `launch.log`, und die Vorprüfung fällt
**nur** im Bereich „D Quellen“ durch: „Encoder liefern frisch“ und
„Encoder-Zeitwache bereit“ mit `state='fault_latched'`, dazu
gegebenenfalls „HWT-Fusion Quellen bereit“. Dann hat sich der Radsensor
beim Hochfahren selbst gesperrt. Er gibt sich erst bei einem neuen Start
frei; die Selbstheilung löst das nicht (SH-4, 04.11.: 690 s Mission, nie
gefahren). Amadeus hat sich nicht bewegt.

1. Nur lesend sichern, was die Zeitwache meldet, und die Last:

   ```bash
   source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
   uptime | tee "$D/last_bei_sperre_1.txt"
   python3 "$SH_SRC/ki_erkundung/werkzeuge/radsensor_zustand.py" 2>&1 | tee "$D/radsensor_1.txt"
   ```

2. Stack geordnet beenden (wie B5) und Christopher in einem Satz sagen: „Der
   Radsensor hat sich beim Hochfahren selbst gesperrt; ich starte den Stack
   einmal neu, Amadeus fährt dabei nicht.“
3. Die Dateien des ersten Starts beiseitelegen, damit B1 bis B5 mit
   denselben Befehlen weiterlaufen:

   ```bash
   source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
   for f in launch.log launch.pid launch_start.txt anfahrzeit.txt schalter.txt vorpruefung.json vorpruefung.txt; do \
     [ -e "$D/$f" ] && mv "$D/$f" "$D/erster_start_$f"; done; ls "$D"
   ```

4. Mindestens 30 s nach „alles beendet“: **genau ein** weiterer scharfer
   Start, B1 von der Frage an, mit den Befehlen, wie sie dort stehen.
5. Sperrt sich der Radsensor auch beim zweiten Start: Schritt 1 mit
   `_2` statt `_1` in den Dateinamen, Stack beenden, berichten, Ende. Das
   ist dann ein Befund für die Motorsteuerung, nichts für diesen Auftrag.

Stimmt eine der Bedingungen nicht (zum Beispiel „Modbus-Fehler“ im Log oder
eine FEHL-Zeile außerhalb von „D Quellen“), gilt die Ausnahme nicht.

### B2 – noch einmal messen (nichts fährt)

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/messen_scharf.txt"
```

Es muss wieder eine türbreit vermessene Öffnung mit „Aufstellung passt.“
und „Weg passt.“ dastehen. Deren Richtung aus der Tabelle (Zahl mit
Vorzeichen, ohne Gradzeichen) ist `R`. Passt es nicht: keine Mission;
weiter wie unter „Nichts gesendet“.

### B3 – Mission starten und Fahrziel senden

Genau einmal die Mission, dann das Werkzeug; es wartet, bis der Erkunder
wartet, misst, prüft, sendet das Ziel und zeigt dessen Meldungen bis zum
Ende:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --richtung R --richtung-toleranz 10 --hinter 0.45 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/werkzeug.txt"; echo "rc=${PIPESTATUS[0]}"
```

(`--hinter 0.45`, weil im Flur laut Christopher 1,20 m bis zum ersten
Hindernis frei sind.)

**Nichts gesendet (Ausnahme):** Meldet das Werkzeug „Nichts gesendet“ oder
„Der Erkunder wartet nicht“, hat sich Amadeus nicht bewegt. Dann genau
einmal den Stopp senden, den Stack geordnet beenden (B5) und berichten, was
das Werkzeug gesagt hat. **Genau ein** weiterer Durchgang ab Teil A ist
erlaubt.

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
```

**Christopher drückt den Not-Aus (oder den Stopp in der App), bevor etwas
berührt wird:** wenn eine Ecke näher als zwei Finger breit an Pfosten,
Türblatt oder sonst etwas herankommt, wenn Amadeus anders fährt als
angekündigt (rückwärts, im Bogen, deutlich zur Seite, deutlich schneller als
eine Handbreit in der Sekunde), bei ungewöhnlichem Geräusch oder starkem
Schwanken. Kurzes Stehenbleiben zwischen den Etappen, kleines Nachstellen
der Richtung und langsames Kriechen neben dem Türblatt sind gewollt.

### B4 – sichern (Amadeus bleibt stehen, der Stack läuft noch)

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
date -Iseconds > "$D/ende.txt"
grep -n "Etappenfahrt\|Fahrziel" "$D/launch.log" | tee "$D/etappen.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
```

Dazu aus den Sekundenzeilen von `base_hardware` im `launch.log`, wie im
Bericht zu KI-F2: größtes |v| und größtes |w| zwischen Missionsstart und
Ende. Dann Christopher fragen, je einzeln:

1. Steht Amadeus ganz im Flur, auch mit der Hinterkante?
2. Wie viel Platz blieb an den Türpfosten und am Türblatt (etwa in cm, je
   Seite)?
3. Hat er etwas berührt, oder musstest du eingreifen?
4. Ist er gerade auf die Tür zugefahren, und hat er die Richtung
   nachgestellt? Wo?

### B5 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif1.env; kill -INT "$(cat "$SH_PR/kif3b/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Danach stellt Christopher Amadeus von Hand zurück.

---

# Stufe 2 – vom Platz im Raum selbst vor die Tür und hindurch

Nur, wenn der Projektinhaber Stufe 2 in der Übergabe genannt hat und Stufe 1
T-1 bis T-6 erfüllt hat. Sonst: Bericht, Ende.

**Was Amadeus hier tut:** Er misst die Tür von seinem Platz, fährt zu einem
Punkt auf der Türachse gut zwei Meter vor der Tür, dreht sich dort zur Tür
und fährt knapp einen halben Meter auf sie zu. Dann steht er so, wie ihn in
Stufe 1 Christopher hingestellt hat. Von dort misst er neu und fährt wie in
Stufe 1 hindurch. Das sind zwei Missionen in einem Stacklauf.

**Was bekannt nicht geht:** Von der Seite des offenen Türblatts wird die Tür
bisher falsch vermessen (1,25 m statt 0,85 m). Von dort meldet das Werkzeug
„Keine Öffnung ist türbreit vermessen“; dann braucht es einen anderen
Platz. Das ist ein Befund für den Bericht, kein Fehler der Ausführung.

## Teil C – Platz wählen und messen (ohne Motorfreigabe, nichts fährt)

### C1 – Platz und Stack ohne Motorfreigabe

Anweisung: „Bitte stelle Amadeus an einen Platz im Laborraum, **nicht**
mittig vor die Tür: mindestens 2 m von der Tür entfernt und mindestens einen
halben Meter neben der Türmitte, auf der Seite **ohne** Türblatt. Die Tür
liegt vor ihm oder seitlich, nicht in seinem Rücken. Um ihn herum ist eine
Armlänge frei, und zwischen ihm und dem Platz vor der Tür steht nichts.“
Frage: „Steht Amadeus so still, und bleibt er während des Starts (etwa eine
Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif1.env
D="$SH_PR/kif3b"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  stage_drive_only:=true \
  > "$D/launch_stand2.log" 2>&1 < /dev/null &
echo $! > "$D/launch_stand2.pid"; cat "$D/launch_stand2.pid"; date -Iseconds
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter_stand2.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter_stand2.txt"
grep -c "Traceback" "$D/launch_stand2.log"
```

Erwartet: `True`, `False`, `0`.

### C2 – messen, bis die Anfahrt passt

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"; K=1
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --vor-die-tuer --nur-messen 2>&1 | tee "$D/anfahrt_messen_$K.txt"
```

Das Werkzeug nennt unter „Türbreit vermessen“ jede passende Öffnung mit
zwei Zeilen: wie Amadeus zu ihr steht, und die Anfahrt.

- **„Anfahrt: … – Anfahrt passt.“:** weiter unten bei der Frage.
- **„Anfahrt passt nicht: …“:** Christopher den Grund wörtlich nennen und
  sagen: „Bitte stelle ihn an einen anderen Platz.“ Dann mit `K=2`, `K=3` …
  erneut messen.
- **„Anfahrt: nicht nötig, er steht schon passend vor der Tür.“:**
  Christopher sagen: „Er steht schon passend. Bitte stelle ihn weiter zur
  Seite.“ Dann erneut messen.
- **„Keine Öffnung ist türbreit vermessen“:** Christopher sagen: „Von hier
  wird die Tür nicht als Tür gemessen. Bitte stelle ihn an einen anderen
  Platz, von dem er gerader auf die Tür sieht.“ Dann erneut messen.
- Höchstens sechs Messungen. Passt es dann nicht: Stack beenden (C3),
  berichten, Ende.

Sobald eine Messung „Anfahrt passt.“ meldet, Christopher einmal fragen: „Ich
messe eine Öffnung, **B** m breit und **E** m entfernt, **R** Grad **links
oder rechts** von seiner Blickrichtung. Ist das die Labortür?“ (B, E und R
aus der Tabelle; positives R ist links.) Bei „nein“: wie „passt nicht“
behandeln. Bei „ja“: **Amadeus bleibt ab jetzt genau so stehen.**

### C3 – Stack beenden

```bash
source ~/roboter_worktrees/kif1.env; kill -INT "$(cat "$SH_PR/kif3b/launch_stand2.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

## Teil D – Anfahrt und Durchfahrt

### D1 – Ansage und scharfer Start

Christopher die Schritte aus der letzten Zeile „Anfahrt: …“ vorlesen (zum
Beispiel „30 Grad nach links drehen, 1,15 m fahren, 90 Grad nach rechts
drehen, 0,45 m fahren“) und dazu sagen: „Danach steht er etwa eine halbe
Minute, misst neu und fährt wie vorhin gerade durch die Tür. Du stehst so,
dass du weder auf diesem Weg noch zwischen Amadeus und der Tür stehst, nicht
in der Tür und nicht im Flur vor ihm, mit der Hand am Not-Aus.“ Frage:
„Steht Amadeus unverändert, und bleibt er während des Starts (etwa eine
Minute) unberührt?“ Nur nach „ja“:

```bash
source ~/roboter_worktrees/kif1.env
D="$SH_PR/kif3b"
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  stage_drive_only:=true \
  > "$D/launch2.log" 2>&1 < /dev/null &
echo $! > "$D/launch2.pid"; cat "$D/launch2.pid"; date -Iseconds > "$D/launch2_start.txt"
```

Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
grep -n "Anfahrverhalten bestaetigt" "$D/launch2.log" | tee "$D/anfahrzeit2.txt"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter2.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter2.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 --json "$D/vorpruefung2.json" > "$D/vorpruefung2.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung2.txt"
```

Erwartungen und die Ausnahmen „Motorregler antworten nicht“ und
„Radsensor beim Start gesperrt“ wie in B1; die Ausnahme gilt hier noch
einmal, unabhängig von Stufe 1. Dabei in Schritt 1 `_3` (beim zweiten Mal
`_4`) in den Dateinamen und in Schritt 3 statt der dortigen Zeile:

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
for f in launch2.log launch2.pid launch2_start.txt anfahrzeit2.txt schalter2.txt vorpruefung2.json vorpruefung2.txt; do \
  [ -e "$D/$f" ] && mv "$D/$f" "$D/erster_start_$f"; done; ls "$D"
```

Zum Beenden D7 statt B5; der neue Start ist D1 von der Frage an.

### D2 – Anfahrt noch einmal messen (nichts fährt)

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --vor-die-tuer --nur-messen 2>&1 | tee "$D/anfahrt_messen_scharf.txt"
```

Es muss wieder „Anfahrt passt.“ dastehen. Die Richtung dieser Öffnung aus
der Tabelle (Zahl mit Vorzeichen, ohne Gradzeichen) ist `R`. Passt es nicht:
keine Mission; Stack geordnet beenden (D7), berichten.

### D3 – erste Mission: die Anfahrt

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart_anfahrt.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --vor-die-tuer --richtung R --richtung-toleranz 10 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/anfahrt.txt"; echo "rc=${PIPESTATUS[0]}"
```

Erwartet: `rc=0` und „Etappenfahrt abgeschlossen: …“. Meldet das Werkzeug
„Nichts gesendet“ oder „Der Erkunder wartet nicht“: wie in B3 unter „Nichts
gesendet“ (Stopp, Stack beenden, berichten; genau ein weiterer Durchgang ab
Teil C ist erlaubt). Hält der Erkunder an oder scheitert die Anfahrt: keine
zweite Mission; weiter bei D6.

Christopher drückt den Not-Aus wie in B3 beschrieben. Drehen auf der Stelle
um große Winkel und kurzes Stehen zwischen den Schritten sind gewollt.

### D4 – Durchfahrt messen (nichts fährt, niemand fasst Amadeus an)

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --nur-messen --hinter 0.45 2>&1 | tee "$D/durchfahrt_messen.txt"
```

Es muss eine türbreit vermessene Öffnung mit „Aufstellung passt.“ und „Weg
passt.“ dastehen; deren Richtung ist `R2`. **Passt es nicht: keine zweite
Mission.** Das Werkzeug nennt, was fehlt (zum Beispiel „bitte etwa 10 cm
nach rechts versetzen“); das ist der Befund zu S-3. Weiter bei D6.

### D5 – zweite Mission: die Durchfahrt

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart_durchfahrt.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/fahrziel_senden.py" --tuer --richtung R2 --richtung-toleranz 10 --hinter 0.45 --quelle mensch --warten 120 --beobachten 600 2>&1 | tee "$D/werkzeug2.txt"; echo "rc=${PIPESTATUS[0]}"
```

Meldet das Werkzeug „Der Erkunder wartet nicht“ (der zweite Missionsstart
im selben Stacklauf ist am Roboter neu): nichts wiederholen; einmal den
Stopp senden wie in B3, weiter bei D6. Das ist ein Befund.

### D6 – sichern (Amadeus bleibt stehen, der Stack läuft noch)

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3b"
date -Iseconds > "$D/ende2.txt"
grep -n "Etappenfahrt\|Fahrziel\|Mission beendet" "$D/launch2.log" | tee "$D/etappen2.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died"; do \
  echo "$m: $(grep -c "$m" "$D/launch2.log")"; done | tee "$D/zaehler2.txt"
```

Dazu größtes |v| und größtes |w| an der Basis wie in B4. Dann Christopher
fragen, je einzeln:

1. Ist Amadeus selbst vor die Tür gefahren und hat sich zur Tür gedreht?
   Stand er danach mittig davor?
2. Steht er jetzt ganz im Flur, auch mit der Hinterkante?
3. Wie viel Platz blieb an den Türpfosten und am Türblatt (etwa in cm, je
   Seite)?
4. Hat er etwas berührt, oder musstest du eingreifen?

### D7 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/kif1.env; kill -INT "$(cat "$SH_PR/kif3b/launch2.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Danach stellt Christopher Amadeus von Hand zurück.

---

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei Berührung, bei einer anderen Bewegung als
  angekündigt, bei ungewöhnlichem Geräusch, starkem Schwanken oder Rauch.
  Danach nichts mehr starten; nur berichten.
- Endet die Etappenfahrt mit einer Fehlermeldung („Etappenfahrt: …
  fehlgeschlagen“, „… angehalten“, „… nicht frei“, „kein gueltiges
  Fahrziel“): nicht wiederholen, B4 und B5, berichten.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um die Fahrt „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif3b.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen:

1. Stand (HEAD), die Zeile `zeilen=…`, Tests.
2. Teil A: `schalter_stand.txt`; der ganze Inhalt jeder Datei
   `messen_K.txt` mit dem Hinweis, den Christopher bekam, und was er
   geändert hat; seine Antwort auf die Frage nach der Labortür.
3. Teil B: Antwort zum Start; Anfahrzeit, Schalter, Vorprüfung; bei der
   Ausnahme „Radsensor beim Start gesperrt“ der ganze Inhalt von
   `radsensor_K.txt` und `last_bei_sperre_K.txt` und was der zweite Start
   ergab;
   `messen_scharf.txt`; **der ganze Inhalt von `werkzeug.txt`** (mit den
   Zeilen „Fahrlinie …“ und „Kostenkarte …“), `etappen.txt` und
   `zaehler.txt`; größtes |v| und |w| an der Basis; Christophers Antworten
   nach der Fahrt wörtlich.
4. Die Tabelle T-1 bis T-6 mit dem Gemessenen und „trifft zu“ oder „trifft
   nicht zu“.
5. Stufe 2, falls gelaufen: `schalter_stand2.txt`; der ganze Inhalt jeder
   Datei `anfahrt_messen_K.txt` mit dem, was Christopher gesagt bekam und
   geändert hat; seine Antwort auf die Frage nach der Labortür; Anfahrzeit,
   Schalter und Vorprüfung des zweiten scharfen Starts;
   `anfahrt_messen_scharf.txt`; **der ganze Inhalt von `anfahrt.txt`,
   `durchfahrt_messen.txt` und `werkzeug2.txt`**; `etappen2.txt` und
   `zaehler2.txt`; größtes |v| und |w|; Christophers Antworten wörtlich; die
   Tabelle S-1 bis S-6. Falls nicht gelaufen: warum nicht.
6. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
