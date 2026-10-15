# Aktueller Agentenauftrag: SH-1 – motorlose Jetson-Prüfung `self_healing`

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.10.2026 vom
Projektinhaber („schreibe jetzt in die Datei, was der lokale KI-Agent auf dem
Jetson genau machen soll und was er reporten soll“). Ersetzt den bisherigen
AP-06-Auftrag ([bytegleich archiviert](archive/20261015-ap06-eingefroren/README.md)).

Diese Datei liegt auf dem Branch `claude/blissful-pasteur-s1eivj`. Steht
`~/roboter_ws` auf `main`, so lesen, **ohne** den Checkout zu wechseln:

```bash
git -C ~/roboter_ws fetch origin claude/blissful-pasteur-s1eivj
git -C ~/roboter_ws show origin/claude/blissful-pasteur-s1eivj:docs/wohnungserkundung/AGENTENAUFTRAG.md
```

Vorher lesen (vom selben Branch, gleicher `git show`-Weg): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md`
§6, §10, §11 und in `tools/kartierung/README.md` den Abschnitt
„Selbstheilenden Betrieb motorlos prüfen“.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen vom 15.10.2026 (`self_healing` Hauptlinie, AP06 eingefroren, Abnahmeleiter) |
| WE-Bezug | WE-M0 (Zielsystem-Vorlauf) und WE-M3 (metrischer Erkundungskern); Vorbedingung für Abnahmestufe 1 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens Commit `dfc1cbc`; Basis `main` `22a4b76`. Bisher nur in der Cloud geprüft (ROS 2 Jazzy, Python 3.12), **noch nie auf dem Jetson** (Humble, Python 3.10) |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht.md`: Build, gezielte Tests, Prüfskript A–D und VL53-Messreihe auf dem echten Jetson |
| Nicht-Ziele | siehe „Verboten“; keine Fahrt, keine Korrektur, keine Filteränderung |
| Tests | 139 gezielte Tests (in der Cloud grün), Prüfskript `selbstheilung_stillstand_pruefen.py` |
| Rückfall | Overlay nicht mehr sourcen; `~/roboter_ws` und dessen Installation bleiben unverändert |
| Laborrahmen | LAB-1, motorloser Pfad nach §3 (`active_drive=false`); keine Standardfreigabefragen |

## Verboten in diesem Auftrag

- `active_drive:=true`, `enable_auto_explore:=true`, `AMADEUS_FAHRFREIGABE=JA`,
  Missionen, Navigationsziele, App-Erkundung.
- `ros2 topic pub`, `ros2 service call`, `ros2 action send_goal`,
  `ros2 param set`, `ros2 lifecycle set`. Erlaubt sind nur lesende Befehle
  (`node list`, `topic list/info/hz`, `param get`, `lifecycle get`).
- Änderungen in `~/roboter_ws`: kein `checkout`, `pull`, `reset`, `build`,
  kein Schreiben in dessen `install/`. Nur `git fetch` und `git worktree add`.
- Code-, Parameter- oder Filteränderungen, auch „nur zum Testen“. Fehler werden
  berichtet, nicht behoben.
- Commit, Push, Merge, Pull Request.
- Prozessgruppen signalisieren, `pkill -f`/`killall`, `kill -9` auf fremde Prozesse.
- In den Bericht: Geheimnisse, WLAN-Daten, IP-Adressen, Karten, Kamerabilder,
  Bags.

## Ablauf

Shellzustand bleibt zwischen Agentenbefehlen nicht erhalten. Deshalb beginnt
jeder Befehl ab Schritt 3 mit `source ~/roboter_worktrees/selbstheilung.env`.

### Schritt 1 – Bestand nur lesen

```bash
date -Iseconds
cd ~/roboter_ws && git rev-parse HEAD && git branch --show-current && git status --short | head -30
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
printenv ROS_DOMAIN_ID ROS_LOCALHOST_ONLY RMW_IMPLEMENTATION
ls ~/amadeus_slam_toolbox_ws/install/setup.bash ~/amadeus_lidar_ws/install/local_setup.bash ~/roboter_ws/install/local_setup.bash
```

Läuft bereits ein Robotik-Stack: keinen zweiten starten und nichts beenden.
Christopher genau einmal fragen, ob dieser Stack geordnet beendet werden darf.
Fehlt eine der drei Setup-Dateien: abbrechen und berichten, nicht raten.

### Schritt 2 – getrennter Checkout

```bash
mkdir -p ~/roboter_worktrees
git -C ~/roboter_ws fetch origin claude/blissful-pasteur-s1eivj
test -e ~/roboter_worktrees/selbstheilung && echo "EXISTIERT"
git -C ~/roboter_ws worktree add --detach ~/roboter_worktrees/selbstheilung origin/claude/blissful-pasteur-s1eivj
cd ~/roboter_worktrees/selbstheilung && git rev-parse HEAD && git merge-base --is-ancestor dfc1cbc HEAD && echo "dfc1cbc enthalten"
```

Existiert der Ordner schon: nicht überschreiben. Stattdessen
`~/roboter_worktrees/selbstheilung-<JJJJMMTT-HHMM>` verwenden und diesen Pfad in
Schritt 3 als `SH_WT` eintragen.

### Schritt 3 – Umgebung festhalten

```bash
STAMP=$(date +%Y%m%d_%H%M)
cat > ~/roboter_worktrees/selbstheilung.env <<EOF
source /opt/ros/humble/setup.bash
source \$HOME/amadeus_slam_toolbox_ws/install/setup.bash
source \$HOME/amadeus_lidar_ws/install/local_setup.bash
source \$HOME/roboter_ws/install/local_setup.bash
export SH_WT=\$HOME/roboter_worktrees/selbstheilung
export SH_PR=\$HOME/.local/share/amadeus/pruefungen/sh1_$STAMP
[ -f "\$SH_WT/install/local_setup.bash" ] && source "\$SH_WT/install/local_setup.bash"
EOF
source ~/roboter_worktrees/selbstheilung.env && mkdir -p "$SH_PR" && echo "$SH_WT $SH_PR"
```

### Schritt 4 – Build im Checkout

```bash
source ~/roboter_worktrees/selbstheilung.env && cd "$SH_WT" && \
  colcon build --packages-select explore robot_navigation 2>&1 | tee "$SH_PR/build.log" | tail -20
source ~/roboter_worktrees/selbstheilung.env && ros2 pkg prefix explore && ros2 pkg prefix robot_navigation
```

Beide Präfixe müssen unter `$SH_WT/install` liegen. Build-Fehler: Schritte 5–8
entfallen, Schritt 10 (Bericht).

### Schritt 5 – gezielte Tests, isolierte ROS-Domain

Vor dem Stackstart. Die Tests erzeugen synthetische ROS-Daten; deshalb eine
Domain, die nicht die des Roboters ist (227, sonst eine andere freie), und nur
lokal:

```bash
source ~/roboter_worktrees/selbstheilung.env && cd "$SH_WT" && \
ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider \
  src/explore/test/test_self_healing.py \
  src/explore/test/test_self_healing_runtime.py \
  src/explore/test/test_metric_float32_lattice.py \
  src/explore/test/test_metric_selection_retry.py \
  src/explore/test/test_metric_map_lifecycle.py \
  src/robot_navigation/test/test_nav_real_contract.py \
  tools/kartierung/test_selbstheilung_stillstand_pruefen.py \
  2>&1 | tee "$SH_PR/tests.log" | tail -40
```

Erwartung: `139 passed` (Cloud). Fehlschläge nicht beheben; vollständige
Fehlermeldung in den Bericht und mit Schritt 6 weitermachen (motorlos, ohne
Wirkung).

### Schritt 6 – Stack motorlos starten

Normale Roboter-Domain, also **ohne** die Testvariablen aus Schritt 5.

```bash
source ~/roboter_worktrees/selbstheilung.env && \
  python3 ~/roboter_ws/tools/kartierung/roboterknoten.py --still || echo "STACK LAEUFT SCHON - abbrechen"
```

Nur wenn nichts läuft:

```bash
source ~/roboter_worktrees/selbstheilung.env && \
  nohup env --default-signal=INT ros2 launch robot_navigation nav_mapping.launch.py self_healing:=true \
  > "$SH_PR/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/launch.pid"; cat "$SH_PR/launch.pid"
```

`env --default-signal=INT` ist nötig: Ein mit `&` gestarteter Prozess einer
nicht interaktiven Shell ignoriert sonst SIGINT, und der geordnete Stopp aus
Schritt 9 liefe ins Leere (gemessen 15.10.2026). Die gespeicherte PID ist die
des `ros2 launch`-Prozesses.

Nach etwa 30 s lesend erfassen:

```bash
source ~/roboter_worktrees/selbstheilung.env && \
  ros2 node list | sort | tee "$SH_PR/nodes.txt"
source ~/roboter_worktrees/selbstheilung.env && \
  for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
    echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$SH_PR/lifecycle.txt"
grep -nE "ERROR|FATAL|Failed|Managed nodes are active|self_healing|Timed out" "$SH_PR/launch.log" | head -80
```

Ohne `active_drive` integriert die Basis nur Sollwerte (null); TF-Wartemeldungen
sind möglich. Berichten, nicht beheben.

### Schritt 7 – Prüfskript A–D

```bash
source ~/roboter_worktrees/selbstheilung.env && \
  python3 "$SH_WT/tools/kartierung/selbstheilung_stillstand_pruefen.py" \
  --json "$SH_PR/pruefung_AD.json" 2>&1 | tee "$SH_PR/pruefung_AD.txt"; echo "exit=${PIPESTATUS[0]}"
```

Exit 0 = bestanden, 1 = mindestens ein `FEHL`, 2 = Explorer nicht erreichbar.
Bei Exit 2 oder `FEHL` mit „erreichbar“/„nicht deklariert“: einmal nach 30 s
wiederholen (langsamer Lifecycle-Start), beide Ausgaben berichten.

### Schritt 8 – VL53-Messreihe (braucht Christopher)

Christopher legt die Objekte; das ist die einzige Bedienhandlung, die der
Agent anfordert. Je Messung genau einmal ansagen, was wohin gelegt wird, und
auf „liegt“ warten. Danach steht niemand vor dem Roboter (seitlich oder
dahinter, mindestens 1 m Abstand zum Sichtbereich).

Objekt: matt, hell, nicht spiegelnd; mindestens 10 cm breit und 20 cm tief
(Karton, Bücherstapel). Mittig vor dem Roboter. Abstand = Fahrzeugfront bis
Vorderkante des Objekts.

| Nr | Höhe | Abstand ab Front |
|---|---|---|
| 0 | kein Objekt, mindestens 1 m frei | – |
| 1 | 3 cm | 0,30 m |
| 2 | 6 cm | 0,30 m |
| 3 | 10 cm | 0,30 m |
| 4 | 15 cm | 0,30 m |
| 5 | 3 cm | 0,38 m |
| 6 | 6 cm | 0,38 m |
| 7 | 10 cm | 0,38 m |
| 8 | 15 cm | 0,38 m |

Je Messung (Nummer und Notiz anpassen):

```bash
source ~/roboter_worktrees/selbstheilung.env && \
  python3 "$SH_WT/tools/kartierung/selbstheilung_stillstand_pruefen.py" \
  --beobachten-s 1 --vl53-s 10 --notiz "Nr 2: 6 cm, 0,30 m" \
  --json "$SH_PR/vl53_02.json" 2>&1 | tee "$SH_PR/vl53_02.txt"
```

Erwartung aus der Geometrie (zu prüfen, nicht vorwegnehmen): unterste
Sensorzeile bis −30°, Sensor 0,305 m über Boden, gültig nur bis 0,50 m
Messdistanz. Sehr flache Objekte erscheinen vermutlich gar nicht; Treffer
unter etwa 0,14 m über Boden zählt das Skript als `verworfen`. Ist
Christopher nicht verfügbar: Schritt 8 auslassen und das im Bericht vermerken.

### Schritt 9 – Stack geordnet beenden

```bash
source ~/roboter_worktrees/selbstheilung.env && PID=$(cat "$SH_PR/launch.pid") && \
  kill -INT "$PID" && for i in $(seq 1 30); do kill -0 "$PID" 2>/dev/null || break; sleep 1; done; \
  kill -0 "$PID" 2>/dev/null && echo "LAUNCH LAEUFT NOCH" || echo "Launch beendet"
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

SIGINT nur an die Launch-PID, nie an die Gruppe. Läuft der Launch nach 30 s
noch: einmal `kill -TERM` an dieselbe PID, 15 s warten. Danach übrige eigene
Knoten einzeln per PID mit SIGINT beenden und im Bericht auflisten.

### Abbruchregeln

Sofort Schritt 9 und dann Bericht, ohne Wiederholung, bei:

- sichtbarer oder hörbarer Rad-/Motorbewegung;
- `FEHL` in „D Stillstand“ (`dry_run`, `allow_rs485` oder `/cmd_vel` ungleich null);
- ausgelöstem Not-Aus oder einem „Stopp“ von Christopher;
- einem zweiten Robotik-Stack, der während der Prüfung auftaucht.

## Bericht: `~/selbstheilung_jetson_bericht.md`

Markdown, Deutsch, Zahlen und Ausgaben wörtlich. Lange Logs auf die relevanten
Zeilen kürzen und das kenntlich machen. Rohdateien bleiben in `$SH_PR`.

1. **Kopf:** Datum/Uhrzeit Start und Ende, `SH_WT`, `SH_PR`, HEAD des
   Checkouts, Ausgabe „dfc1cbc enthalten“, ROS-Distribution, `python3 --version`.
2. **Bestand vorher:** HEAD, Branch und `git status --short` von `~/roboter_ws`;
   Ausgabe von `roboterknoten.py`; `ROS_DOMAIN_ID`/`ROS_LOCALHOST_ONLY`/`RMW_IMPLEMENTATION`.
3. **Build:** Erfolg ja/nein, Dauer, die zwei `ros2 pkg prefix`-Zeilen; bei
   Fehler die letzten 40 Zeilen von `build.log`.
4. **Tests:** Zusammenfassungszeile (`N passed, M failed …`), Laufzeit; bei
   Fehlern Testname und vollständige Fehlermeldung.
5. **Stackstart:** Startbefehl, Zahl der Knoten, `nodes.txt`, `lifecycle.txt`,
   die `grep`-Zeilen aus `launch.log`.
6. **Prüfung A–D:** vollständige Ausgabe von `pruefung_AD.txt` und Exitcode,
   bei Wiederholung beide.
7. **VL53:** Tabelle je Messung Nr | Notiz | links: Punkte/verworfen/behalten/
   Höhe min–max über Boden/getroffene Zeilen | rechts: dasselbe. Danach der
   `vl53`-Teil jeder JSON-Datei wörtlich. Fehlende Messungen mit Grund.
8. **Beenden:** wie beendet, Wartezeit, Ausgabe von `roboterknoten.py` danach.
9. **Auffälligkeiten:** alles Unerwartete, jede Abweichung von diesem Auftrag
   mit Grund, Beobachtungen von Christopher getrennt von Messwerten.
10. **Nicht ausgeführt:** Schritte, die entfallen sind, und warum.

Am Ende im Chat nur melden: Pfad des Berichts, Ergebnis A–D (bestanden/nicht
bestanden), Zahl der Testfehlschläge, ob die VL53-Reihe vollständig ist.
Christopher lädt den Bericht in die Cloud-Sitzung hoch.

## Danach

Auswertung in der Cloud-Sitzung. Erst bei bestandenem A–D folgt Abnahmestufe 1
(drei begrenzte Laborfahrten nach LAB-1) als eigener Auftrag. Eine Änderung der
VL53-Höhenfilter ist eine getrennte Sicherheitsänderung und nicht Teil von SH-1.
