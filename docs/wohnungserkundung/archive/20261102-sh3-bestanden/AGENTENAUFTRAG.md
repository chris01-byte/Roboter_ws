# Aktueller Agentenauftrag: SH-3 – drei begrenzte Laborfahrten (Abnahmestufe 1)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 02.11.2026 nach
bestandenem SH-2 (Lauf 2). Drei echte, autonome Erkundungsfahrten im
Selbstheilungsbetrieb im Laborraum, bewertet nach Abnahmestufe 1
(`KONZEPT_SELBSTHEILUNG.md` §11). Odometrie: HWT601 (Entscheidung 8 vom
22.10.2026, Begründung in §9 des Konzepts).

SH-2 hat motorlos bestätigt: Der HWT-Weg startet sauber, alle
Selbstheilungs-Overlays sind live, und die VL53 tragen Objekte ab etwa 6,5 cm
Höhe vor dem Roboter in die lokale Kostenkarte ein. Der vorige Auftrag ist
[archiviert](archive/20261102-sh2-bestanden/README.md).

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md`
§6, §9 und §11.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen vom 15./16./22.10.2026 |
| WE-Bezug | WE-M3 (metrischer Erkundungskern), Abnahmestufe 1 der Hauptlinie `self_healing` |
| Istbasis | Release `selbstheilung-sh2-20261102_1107` aus SH-2 Lauf 2 (gebaut aus `3a05e6b`, 168 Tests grün). **Kein neuer Build.** Der Klon darf neuere Dokumentation ziehen; Code in `src/` und `tools/` (ohne `*.md`) muss dem Stand `3a05e6b` entsprechen (Schritt 0) |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh3.md`: drei Fahrten mit Fahrtprotokoll, Christophers Beobachtungen, Gesamturteil Stufe 1 |
| Nicht-Ziele | keine Code- oder Parameteränderung, kein anderer Raum, keine Wohnungsfahrt, kein Arm, keine Fahrt außerhalb des Laborraums |
| Rückfall | Stack geordnet stoppen; `self_healing:=false` bzw. SH-1-/AP06-Releases bleiben unverändert verfügbar |
| Laborrahmen | LAB-1: aktive Fahrt im beauftragten Umfang ohne erneute Standardfreigaben. Not-Aus-Erreichbarkeit, freier Fahrbereich und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden **nicht** erneut abgefragt |

## Verboten

- keine Code- oder Parameteränderung, kein neuer Build, kein Commit oder Push;
- schreibend nur: der Stackstart in Schritt 2 und, falls die App fehlt,
  **genau ein** Missionsstart je Fahrt in Schritt 5; kein `param set`,
  `lifecycle set`, `service call`, kein weiteres `topic pub`, keine Nav2-Ziele;
- `operator_stationary_confirmed:=true` nur nach Christophers „ja“ in Schritt 1;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws` und an der defekten Codex-Referenz; bestehende
  Releases, der v1-Ordner und frühere Berichte bleiben, wie sie sind;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht.

## Was Amadeus in diesen Fahrten tut

- **Vorwärts:** höchstens 0,12 m/s; 0,06 m/s, solange vor ihm nicht kartiert ist.
- **Drehen:** höchstens 0,25 rad/s.
- **Rückwärts:** nur entlang der eigenen Spur, höchstens 0,4 m, 0,05 m/s.
- Er wählt seine Ziele selbst (Frontiers) und heilt Fehlschläge selbst:
  1. erneut versuchen;
  2. Ziel zurückstellen;
  3. umsehen;
  4. ein Stück zurück entlang der Spur;
  5. „Hilfe benötigt“.
- Eine Fahrt endet von selbst mit „vollständig“, „Teilkarte“ oder „Hilfe
  benötigt“, spätestens nach 20 Minuten (Explorer-Gesamtbudget).
- **Kurzes Stehenbleiben ist normal:** Setzen die VL53 einige Sekunden aus
  (in SH-1 und SH-2 je einmal 6–7 s), sperrt das Fahrtor nach 0,8 s, und der
  Explorer wartet bis zu 30 s, bevor er Hilfe ruft. Das ist kein Eingriffsgrund.

## Einmal je Sitzung

### Schritt 0 – Stand und Release prüfen

```bash
date -Iseconds
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor 3a05e6b HEAD && \
  git diff --quiet 3a05e6b HEAD -- src tools ':(exclude)*.md' && echo "src/tools = Release-Stand 3a05e6b"
grep -n "^export SH_REL" ~/roboter_worktrees/selbstheilung-v2.env
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
echo "$SH_REL"; ls "$SH_REL/product-install/local_setup.bash"
```

Erwartet: „src/tools = Release-Stand 3a05e6b“ und `SH_REL` endet auf
`selbstheilung-sh2-20261102_1107`. Sonst nicht fahren, sondern berichten; kein
neuer Build. Läuft schon ein Robotik-Stack: nichts beenden, Christopher genau
einmal fragen.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern: „Bitte die Türen des Laborraums
schließen, sodass Amadeus den Raum nicht verlassen kann.“ Der Selbstheilungs-
betrieb kennt keinen Software-Fahrbereich; den Raum begrenzen Wände und
geschlossene Türen. Ohne geschlossenen Raum keine Fahrt.

Außerdem einmal: „Bitte flache Gegenstände unter etwa 15 cm Höhe (Kabel,
Kartons, Schuhe) vom Boden räumen.“ Grund: Unter etwa 6 cm sehen die VL53
nichts (SH-2), und von höheren niedrigen Gegenständen nur die Vorderkante;
liegt so ein Gegenstand neben dem Roboter, kann die Flanke ihn beim Drehen
berühren (bekannte Grenze, Entscheidung 22.10.2026). Höhere Möbel und Wände
sieht der LiDAR.

## Je Fahrt (Nr 1, 2, 3)

Jede Fahrt ist ein Kaltstart mit neuer Karte. `RUN` = 1, 2 oder 3; in jedem
Befehlsblock setzen (`RUN=1 …`), weil die Blöcke nicht zwingend in derselben
Shell laufen.

### 1. Bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE
mkdir -p "$SH_PR/sh3_run$RUN"
```

Fehlt ein Gerät: nicht fahren, berichten. Christopher einmal fragen: „Steht
Amadeus an seinem Startplatz still, mit etwa 0,5 m Platz rundherum, und bleibt
er während des Starts (etwa eine Minute) unberührt?“ Nur nach „ja“ weiter. Der
Startplatz darf je Fahrt wechseln; ihn im Bericht beschreiben lassen.

### 2. Stack scharf starten

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/sh3_run$RUN/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh3_run$RUN/launch.pid"; cat "$SH_PR/sh3_run$RUN/launch.pid"
date -Iseconds > "$SH_PR/sh3_run$RUN/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s (HWT-Einmessung) wie in SH-2 `nodes.txt`, 10 s später
`nodes_2.txt` und `lifecycle.txt` erfassen. Erwartet: `/base_hardware`
vorhanden, `/hwt601_encoder_shadow_reader` **nicht** (mit `active_drive`
startet der Launch nur den Motortreiber).

### 3. Vorprüfung direkt vor der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && RUN=1 && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/sh3_run$RUN/vorpruefung.json" 2>&1 | tee "$SH_PR/sh3_run$RUN/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0, Bereiche A–C wie in SH-2 Lauf 2; in D `base_hardware scharf
(aktiver Auftrag)` mit `dry_run=False, allow_rs485=True` und `/cmd_vel 3 s
ohne Fahrbefehl`.

Bei `FEHL` mit „erreichbar“, „nicht deklariert“ oder „Graph unvollständig“ das
Skript einmal nach 30 s wiederholen; erst die Wiederholung zählt. Jeder andere
`FEHL` und ein `FEHL` nach der Wiederholung: Stack geordnet beenden (wie
SH-2 Schritt 9: SIGINT nur an die Launch-PID) und berichten; keine Fahrt.

### 4. Fahrtprotokoll starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh3_run$RUN/protokoll.json" \
  > "$SH_PR/sh3_run$RUN/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh3_run$RUN/protokoll.pid"
```

Nur lesend, nebenher die Rechenlast von `slam_toolbox` alle 10 s mitschreiben
(Simulation 23.10.2026: sie stieg mit der Karte von 25 % auf 80 % eines Kerns,
danach kam `map`→`odom` zu spät). `-x` vergleicht den Prozessnamen exakt und
trifft daher nicht die eigene Shell:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
SLAM_PID=$(pgrep -x async_slam_tool | head -1); echo "SLAM_PID=$SLAM_PID"
echo "$SLAM_PID" > "$SH_PR/sh3_run$RUN/slam.pid"
nohup top -b -d 10 -p "$SLAM_PID" > "$SH_PR/sh3_run$RUN/slam_cpu.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh3_run$RUN/slam_cpu.pid"
```

### 5. Mission starten

Christopher drückt in der App „Erkunden“. Das ist der Produktweg. Steht die App
nicht zur Verfügung, sendet der Agent **genau einmal** denselben Befehl wie die
App:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
```

### 6. Während der Fahrt

- Der Agent greift nicht ein und sendet keine weiteren Befehle.
- Christopher beobachtet und darf jederzeit über die App stoppen oder den
  Not-Aus drücken. Das gilt dann als **Eingriff**.
- Kurzes Stehenbleiben ist kein Eingriffsgrund (siehe oben).
- Die Fahrt endet von selbst; das Protokoll beendet sich wenige Sekunden danach.

### 7. Nach der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=1
cat "$SH_PR/sh3_run$RUN/protokoll.txt" | tail -60
for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
  echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$SH_PR/sh3_run$RUN/lifecycle_nach.txt"
grep -c "process has died" "$SH_PR/sh3_run$RUN/launch.log"
grep -nE "Ignoring the source|TERMINAL_FAULT|ERROR|FATAL" "$SH_PR/sh3_run$RUN/launch.log" | head -40
for m in "extrapolation into the future" "Unable to transform robot pose" "missed its desired rate" "detected collision ahead"; do \
  echo "$m: $(grep -c "$m" "$SH_PR/sh3_run$RUN/launch.log")"; done | tee "$SH_PR/sh3_run$RUN/zeitfehler.txt"
kill -TERM "$(cat "$SH_PR/sh3_run$RUN/slam_cpu.pid")"
grep -E "^ *$(cat "$SH_PR/sh3_run$RUN/slam.pid") " "$SH_PR/sh3_run$RUN/slam_cpu.txt" | awk '{print $9}' | tr '\n' ' ' | tee "$SH_PR/sh3_run$RUN/slam_cpu_reihe.txt"
ros2 run nav2_map_server map_saver_cli -f "$SH_PR/sh3_run$RUN/karte"
```

Christopher dann einmal fragen und die Antworten wörtlich festhalten:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Sieht die Karte in der App sauber aus, ohne doppelte oder verdrehte Wände?

Danach den Stack geordnet beenden (wie SH-2 Schritt 9: SIGINT nur an die
Launch-PID, `roboterknoten.py` danach leer). Läuft das Protokoll noch, sein
Prozess vorher per SIGINT an `protokoll.pid` beenden.

## Abbruch und Wiederholung

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei:
  - Berührung;
  - Fahrt auf ein Hindernis ohne Abbremsen;
  - Verlassen des Laborraums;
  - ungewöhnlichem Geräusch;
  - Rauch.

  Danach keine weitere Fahrt in dieser Sitzung; nur berichten.
- **Endet eine Fahrt mit `outcome=error`:** die Serie anhalten und berichten.
  Keine identischen Fehlversuche aneinanderreihen.
- **Ungültige Fahrt:** Ist eine Fahrt aus einem äußeren Grund ungültig (zum
  Beispiel kommt jemand in den Raum), darf sie einmal wiederholt werden.
  Höchstens vier Starts je Sitzung.
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bewertung Abnahmestufe 1

Bestanden, wenn **alle drei** Fahrten erfüllen:
- `automatisch_erfuellt: true` im Fahrtprotokoll: begonnen, beendet,
  mindestens zwei selbst gewählte Ziele erreicht, sauberes Ende
  (`exploration_complete`, `usable_partial` oder `blocked_help_required`),
  kein Not-Aus während der Fahrt;
- kein Kontakt und kein Eingriff (Christopher);
- Nav2 nach der Fahrt in einem klaren Zustand, kein „process has died“.

Die Fahrzeit wird gemessen, ist aber kein Abbruchkriterium.

## Bericht: `~/selbstheilung_jetson_bericht_sh3.md`

1. Kopf: Datum, Release, HEAD, Ergebnis von Schritt 0, Raum und Türen
   (Christophers Angabe).
2. Je Fahrt:
   - Startplatz;
   - Knotenlisten (Zahl, `/base_hardware` ja/nein, Encoder-Shadow ja/nein);
   - Vorprüfung (Exit, Bereich C/D);
   - Fahrtprotokoll ohne `ereignisse`, dazu die Ereignisliste gekürzt auf
     Zustandswechsel, HWT, Not-Aus, VL53-Lücken;
   - Lifecycle danach, „process has died“-Zahl, Warnungen;
   - `zeitfehler.txt` und die SLAM-Lastreihe (`slam_cpu_reihe.txt`, % eines
     Kerns alle 10 s) vollständig;
   - Christophers drei Antworten wörtlich.
3. Tabelle über alle Fahrten: Dauer, Ziele, Heilungen, Umsehen,
   Spurrückfahrten, Endzustand, Strecke, VL53-Lücken, Kontakt, Eingriff.
4. Gesamturteil Stufe 1: bestanden / nicht bestanden, mit Grund.
5. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad, Zahl der Fahrten,
Gesamturteil, Kontakte oder Eingriffe, und ob eine Fahrt abgebrochen wurde.

## Danach

Auswertung in der Cloud-Sitzung. Die Fahrten selbst schalten keine weitere
Stufe frei: Wohnungsfahrten (Stufe 3) und das Paket „Weiter“ entscheidet der
Projektinhaber gesondert.
