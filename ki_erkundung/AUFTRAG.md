# Aktueller Auftrag der KI-Linie: KI-F3 – Türdurchfahrt auf gerader Linie

**Erteilt am 22.11.2026 (abends).** Er wird aktiv, sobald der Projektinhaber
ihn übergibt. Er läuft auf dem **Jetson**, mit Christopher. Der KI-Rechner
wird nicht gebraucht; Kamera und KI laufen in diesem Auftrag nicht.

**Warum es ihn gibt:** In KI-F2 hielt Amadeus nach 0,35 m an und kam nicht
bis zur Tür. Der Halt war richtig; falsch war der geplante Weg: erst schräg
zu einem Punkt auf der Türachse, dann dort zur Tür drehen. Diese schräge
Strecke führte rechnerisch 1,5 cm an der Spitze des offenen Türblatts
vorbei. **Jetzt fährt Amadeus auf einer geraden Linie von seinem Platz durch
die Türmitte**, und das Werkzeug prüft vorher am Laserbild, dass links und
rechts dieser Linie 0,30 m frei sind.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-0](archiv/20261121-ki0-erstes-sehen/),
[KI-0N](archiv/20261121-ki0n-nachmessen/),
[KI-0R](archiv/20261121-ki0r-nachrechnen/),
[KI-1](archiv/20261121-ki1-blickrunde/),
[KI-F1](archiv/20261122-kif1-erste-etappen/),
[KI-F2](archiv/20261122-kif2-tuerdurchfahrt/).

**Frage dieses Auftrags:** Kommt Amadeus, mittig vor die offene Labortür
gestellt, auf der geraden Linie durch die Türmitte in einem Zug hindurch?

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md`, Abschnitt 6a |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. **Kein neuer Build:** Es läuft der Release `kif1-20261122_1515` mit `~/roboter_worktrees/kif1.env`, wie in KI-F1 und KI-F2. Am Erkunder hat sich nichts geändert (Schritt 1 prüft das); geändert ist nur das Werkzeug `fahrziel_senden.py`, und das läuft aus der Arbeitskopie |
| Was neu ist | Keine neue Verhaltensänderung am Roboter: derselbe Schalter `stage_drive_only:=true`. Neu ist das Ziel: zwei Punkte auf der geraden Linie vom Standplatz durch die Türmitte (1,2 m vor und 0,45 m hinter der Türlinie), und die Prüfung des Freiraums neben dieser Linie vor dem Senden |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif3.md`: die Messungen im Stand wörtlich, die Fahrt mit den Meldungen des Erkunders und des Werkzeugs, die Kriterien und Christophers Antworten wörtlich |
| Nicht-Ziele | Keine KI, keine Kamera, kein Rundblick, kein Nav2-Ziel; kein Build; keine eigene Code- oder Parameteränderung; keine zweite Fahrt |
| Rückfall | Es wird nichts angelegt außer Prüfdateien unter `pruefung/kif3/` im vorhandenen Release-Ordner. Ohne das Startargument verhält sich der Stack wie am 19.11. |
| Bereich und Freigabe | Laborraum und, für die Durchfahrt, der Flur unmittelbar hinter der Labortür: vom Projektinhaber am 21.11.2026 ausdrücklich verlangt und mit der Übergabe dieses Auftrags für diese eine Durchfahrt freigegeben. Christopher ist dabei, die Hand am Not-Aus. 100 ms Anfahrzeit wie seit dem 15.11. |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push, kein
  Build;
- schreibend nur: die Stackstarts dieses Auftrags, **genau ein**
  Missionsstart, höchstens **ein** Missionsstopp und das Werkzeug
  `fahrziel_senden.py` genau so, wie es hier steht; kein `param set`,
  `lifecycle set`, `service call`, kein weiteres `topic pub`, keine
  Nav2-Ziele;
- **kein Missionsstart, wenn `stage_drive_only` nicht nachweislich `True`
  ist**, und keiner, solange die letzte Messung nicht **beides** meldet:
  „Aufstellung passt.“ und „Weg passt.“;
- das Werkzeug nie mit `--aufstellung-egal`, `--breite-min`, `--breite-max`
  oder `--vor` aufrufen;
- `initial_scan_only` wird nie gesetzt und muss `False` melden;
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`; `operator_stationary_confirmed:=true` nur nach
  Christophers „ja“;
- **die Fahrt gibt es genau einmal.** Bricht sie ab oder hält sie an, wird
  sie nicht wiederholt. (Neu aufstellen und messen im Stand ist keine Fahrt
  und darf wiederholt werden.) Einzige Ausnahmen stehen unter „Motorregler
  antworten nicht“ und „Nichts gesendet“;
- keine Frage vorab, ob die Motoren frei sind, und keine Fragerunde zu
  unveränderten Laborbedingungen (LAB-1). Gefragt wird nur, was in diesem
  Auftrag wörtlich als Frage steht;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an den Umgebungsdateien und an
  bestehenden Releases (außer neuen Prüfdateien unter `pruefung/kif3/`);
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
source ~/roboter_worktrees/kif1.env; echo "rc=$? $SH_REL"; mkdir -p "$SH_PR/kif3"
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

Erwartung: `242 passed`. Bei Fehlschlägen nichts starten, berichten.

---

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
D="$SH_PR/kif3"; mkdir -p "$D"
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
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3"
ros2 param get /explore_node stage_drive_only 2>&1 | tee "$D/schalter_stand.txt"
ros2 param get /explore_node initial_scan_only 2>&1 | tee -a "$D/schalter_stand.txt"
grep -c "Traceback" "$D/launch_stand.log"
```

Erwartet: `True`, `False`, `0`.

### A2 – messen, bis Aufstellung und Weg passen

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3"; K=1
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
source ~/roboter_worktrees/kif1.env; kill -INT "$(cat "$SH_PR/kif3/launch_stand.pid")"; sleep 15
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
D="$SH_PR/kif3"
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
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3"
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

### B2 – noch einmal messen (nichts fährt)

```bash
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3"
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
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3"
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
source ~/roboter_worktrees/kif1.env; D="$SH_PR/kif3"
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
source ~/roboter_worktrees/kif1.env; kill -INT "$(cat "$SH_PR/kif3/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Danach stellt Christopher Amadeus von Hand zurück.

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

Datei `~/ki_erkundung_bericht_kif3.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen:

1. Stand (HEAD), die Zeile `zeilen=…`, Tests.
2. Teil A: `schalter_stand.txt`; der ganze Inhalt jeder Datei
   `messen_K.txt` mit dem Hinweis, den Christopher bekam, und was er
   geändert hat; seine Antwort auf die Frage nach der Labortür.
3. Teil B: Antwort zum Start; Anfahrzeit, Schalter, Vorprüfung;
   `messen_scharf.txt`; **der ganze Inhalt von `werkzeug.txt`** (mit den
   Zeilen „Fahrlinie …“ und „Kostenkarte …“), `etappen.txt` und
   `zaehler.txt`; größtes |v| und |w| an der Basis; Christophers Antworten
   nach der Fahrt wörtlich.
4. Die Tabelle T-1 bis T-6 mit dem Gemessenen und „trifft zu“ oder „trifft
   nicht zu“.
5. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
