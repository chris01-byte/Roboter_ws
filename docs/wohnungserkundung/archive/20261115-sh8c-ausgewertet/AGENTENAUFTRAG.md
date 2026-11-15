# Aktueller Agentenauftrag: SH-8c – dieselbe Stellprobe, einzige Änderung: Anfahrzeit des Antriebs 100 ms

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.11.2026 nach
der Auswertung von AT-2
([Archiv](archive/20261115-at2-ausgewertet/README.md), STATUS Abschnitte
15.11.2026). Der Projektinhaber hat am 15.11.2026 entschieden: **100 ms
Anfahrzeit ist der Standard für den selbstheilenden Betrieb**, und als
Nächstes folgt diese Stellprobe.

**Warum:** SH-8b scheiterte an allen drei Stellen, weil die Rückfahrt nur
0,15–0,22 m statt 0,3 m schaffte. AT-1b und AT-2 haben die Ursache gemessen
und die Gegenprobe bestanden: Mit 2000 ms Anfahrzeit folgte der Antrieb den
Rampen von Nav2 nur mit 11–22 %, mit 100 ms folgt er voll (0,96–1,03). In
AT-2 erreichte die langsame Rückfahrt (−0,015 m/s) ihr Tempo nach etwa 1,5 s.

**Prüfling ist genau eine Änderung:** das Startargument
`hwt601_accel_ms:=100`. **Kein Build.** Es läuft der Release von SH-8b
(`selbstheilung-sh8b-20261114_1643`, mit KM-1 B). Kollisionsmonitor, Karten,
Tempo im Profil, Rückfahrt, Budget und Heilungsleiter bleiben wie in SH-8b.

**Dazu zwei reine Messungen im Fahrtprotokoll, keine Verhaltensänderung:**

1. **Tempo-Folge:** befohlener Weg und Drehwinkel gegen gefahrenen Weg und
   Drehwinkel (Block `tempo_folge`). In den Fahrten bis SH-8b lag das
   Verhältnis bei etwa 0,2; erwartet ist jetzt etwa 1.
2. **Wackeln:** Drehrate um die waagerechten Achsen aus dem HWT601 (Block
   `wackeln`), in Ruhe und während der Fahrt, mit den stärksten Sekunden.
   Christopher sah in AT-2 Ruckeln beim Anfahren; hier wird es gemessen.

**Wichtig – Amadeus fährt zum ersten Mal wirklich das befohlene Tempo:**
0,135 m/s vorwärts und 0,25 rad/s beim Drehen (bisher real 1–2 cm/s), in
der Langsam-Zone 30 % davon. Er setzt jetzt wirklich bis 0,3 m (höchstens
0,4 m) zurück. Alles geht etwa fünf- bis zehnmal schneller als in SH-8b.
Christopher steht deshalb **nah daneben mit der Hand am Not-Aus**.

**Erwartetes Verhalten an jeder Stelle:** Der Regler hält vor dem Hindernis
an („detected collision ahead“ ist normal). Amadeus setzt etwa 0,3 m gerade
zurück (in etwa 20 s), wählt ein anderes Ziel und fährt weg. Eine Befreiung
sollte jetzt deutlich unter den bisherigen 3–4 Minuten liegen.

**Jede Berührung beendet den ganzen Auftrag.** Alle bestehenden Releases
bleiben unverändert.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/MASTERPLAN.md` §9, im
STATUS die Arbeitsliste und die Abschnitte 15.11.2026 und 14.11.2026
(SH-8b). Der SH-8b-Auftrag ist
[archiviert](archive/20261114-sh8b-ausgewertet/README.md); Teil A läuft hier
genauso ab, mit den unten genannten Unterschieden. **Es gibt in diesem
Auftrag keinen Teil B** (keine volle Fahrt).

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 15.11.2026; **Fahrplan §9, Schritt 1, Regeln 1, 4 und 6** (eine Änderung, dieselbe Stellprobe, Stellprobe vor langen Fahrten) |
| WE-Bezug | WE-M3, metrischer Kern im Zwei-Raum-Umfang; keine Abnahme |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `e03cac3` (nur für die Werkzeuge unter `tools/kartierung`); **kein Build**, Release `selbstheilung-sh8b-20261114_1643` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh8c.md`: Stellprobe an drei Stellen (je zweimal) mit Urteil je Probe, Rückfahrstrecken, Tempo-Folge, Wackeln und Eigenecho-Zeilen |
| Nicht-Ziele | keine Code- oder Parameteränderung, kein Build, keine volle Fahrt, kein dritter Raum, keine andere Anfahrzeit als 100 ms, keine Änderung an Tempo, Rückfahrt oder Langsam-Zone |
| Rückfall | Start ohne `hwt601_accel_ms:=100` (dann schreibt die Basis wieder 2000 ms in den Antrieb); Releases bleiben |
| Laborrahmen | LAB-1: aktive Fahrt im beauftragten Umfang ohne erneute Standardfreigaben. Not-Aus-Erreichbarkeit und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden **nicht** erneut abgefragt. Wie in SH-8 entschieden (10.11.2026): Amadeus steht beim Start absichtlich 5 cm vor einem Hindernis. Entscheidung des Projektinhabers vom 15.11.2026: 100 ms Anfahrzeit und diese Stellprobe |

## Verboten

- keine Code- oder Parameteränderung, kein Commit oder Push, **kein Build**;
- schreibend nur: der Stackstart je Probe, falls die App fehlt **genau ein**
  Missionsstart je Probe, und **genau ein** Missionsstopp je Probe (derselbe
  Befehl wie der Stopp der App, siehe A5); kein `param set`,
  `lifecycle set`, `service call`, kein weiteres `topic pub`, keine
  Nav2-Ziele, kein Lauf von `antriebsprobe.py`;
- keine andere Anfahrzeit, kein Start ohne `hwt601_accel_ms:=100`;
- `operator_stationary_confirmed:=true` nur nach Christophers „ja“;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws` (auch nicht die fremden Änderungen dort) und an
  der defekten Codex-Referenz; bestehende Releases und frühere Berichte
  bleiben, wie sie sind;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht.

**Ausdrücklich erlaubt:** rein lesende Zusatzmessungen (`ros2 topic info`,
`topic echo --once`, eigene Zählknoten ohne Publisher).

## Was Amadeus in diesen Proben tut

- **Vorwärts:** Regler 0,135 m/s, höchstens 0,162 m/s; 0,08 m/s, solange vor
  ihm nicht kartiert ist. **Diese Werte werden jetzt wirklich gefahren.**
- **Drehen:** Regler 0,25 rad/s, höchstens 0,3125 rad/s.
- **Rückwärts:** entlang der eigenen geraden Spur oder 0,3 m gerade zurück,
  sofern hinten frei ist; höchstens 0,4 m, 0,05 m/s (mit etwas vor ihm
  0,015 m/s), einmal je Stillstand. **Nach hinten sieht er nichts.**
- **KM-1 B (wie SH-8b):** Hindernisse dicht an ihm bleiben in seiner lokalen
  Karte stehen. Er fährt und dreht nicht in sie hinein, sondern meldet einen
  Fehlschlag und setzt zurück.
- Er wählt seine Ziele selbst und heilt Fehlschläge selbst: erneut
  versuchen, Ziel zurückstellen, umsehen, ein Stück zurück, „Hilfe benötigt“.
- **Kurzes Stehenbleiben ist normal** (VL53-Aussetzer, Kollisionsmonitor).
- Beim Verlassen der Langsam-Zone springt der Sollwert von 30 % auf 100 %;
  dabei kann der Aufbau kurz rucken. Das wird gemessen, es ist kein
  Abbruchgrund, solange nichts stark schwankt.

## Einmal je Sitzung

Jeder ROS-Befehl beginnt mit `source ~/roboter_worktrees/selbstheilung-v2.env`.

### Schritt 0 – Bestand

```bash
date -Iseconds
git -C ~/roboter_ws rev-parse HEAD; git -C ~/roboter_ws status --short | head -8
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.

### Schritt 1 – Klon aktualisieren, Release prüfen, Werkzeugtests

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "$SH_SRC $SH_REL"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor e03cac3 HEAD && echo "e03cac3 enthalten"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
grep -c "footprint_clearing_enabled: False" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"
grep -n "hwt601_accel_ms" "$SH_REL/product-install/robot_bringup/share/robot_bringup/launch/app_mapping.launch.py" | head -3
cd "$SH_SRC" && env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider \
  tools/kartierung/test_selbstheilung_stillstand_pruefen.py \
  tools/kartierung/test_selbstheilung_lauf_protokoll.py 2>&1 | tee "$SH_PR/sh8c_tests.log" | tail -3
```

Erwartet: `SH_REL` endet auf `selbstheilung-sh8b-20261114_1643`; Zähler
`roboter_ws/install` `0`; **zwei** Zeilen `footprint_clearing_enabled:
False`; das Startargument `hwt601_accel_ms` im Launch des Releases
vorhanden; `37 passed` (Cloud, Stand `e03cac3`). Jede Abweichung: nicht
fahren, berichten. Die Umgebungsdatei wird nicht geändert.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern und die Antwort wörtlich
festhalten:

„Bitte für SH-8c aufbauen wie in SH-8b:
1. Dieselbe Tür zwischen Laborraum und Flur ganz öffnen, Türblatt gesichert.
2. Alle anderen Türen beider Räume schließen.
3. In beiden Räumen flache Gegenstände unter etwa 15 cm Höhe vom Boden
   räumen, auch im Türbereich. Die Garderobe im Flur bleibt, wie sie ist.
4. Dieselben zwei Mülleimer und den 5-cm-Abstandshalter bereitlegen.

**Neu und wichtig:** Amadeus fährt heute zum ersten Mal wirklich so schnell,
wie er soll, etwa fünf- bis zehnmal schneller als bisher, und er setzt jetzt
wirklich bis zu 40 cm zurück. Bitte bleib bei jeder Probe nah bei ihm mit
der Hand am Not-Aus und achte besonders auf sein Heck beim Zurücksetzen und
auf seine Seiten beim Vorbeifahren.“

Geht die Serie an einem anderen Tag weiter, den Aufbau dann einmal erneut
bestätigen lassen („unverändert“ genügt). Ohne geschlossene übrige Türen
keine Probe.

## Stellprobe (sechs kurze Proben)

Reihenfolge und Kennung `P`: **s3a, s3b** (Mülleimer), **s2a, s2b** (Ecke),
**s1a, s1b** (Garderobe). Jede Probe ist ein Kaltstart mit neuer Karte. `P`
in jedem Befehlsblock setzen.

| Stelle | Wo | Wie Amadeus hingestellt wird |
|---|---|---|
| S3 Mülleimer | Laborraum, freie Fläche | zwei Mülleimer nebeneinander, etwa 10 cm Lücke, quer vor Amadeus; seine Front mittig davor, **5 cm** Abstand; hinter ihm mindestens 1 m frei, seitlich je mindestens 0,5 m |
| S2 Ecke | Laborraum, freie Raumecke | gerade in die Ecke hinein: Front **5 cm** vor der Wand, linke Seite **5 cm** neben der Seitenwand; hinter ihm mindestens 1 m frei, rechts mindestens 0,5 m |
| S1 Garderobe | Flur | Front gerade auf die Jacken zu, **5 cm** davor; hinter ihm **mindestens 0,7 m** frei (in SH-8b 0,5 m; er setzt jetzt wirklich bis 0,4 m zurück) |

Abstände mit dem Abstandshalter einstellen (±2 cm), danach den Abstandshalter
wegnehmen. Möglichst dieselben Stellen wie in SH-8b. Lässt der Flur an S1
hinten keine 0,7 m zu: den größten möglichen Abstand einstellen, den Wert
festhalten und Christopher bitten, bei dieser Probe das Heck zu beobachten.

### A1. Hinstellen und bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
mkdir -p "$SH_PR/sh8c_$P"
```

Fehlt ein Gerät: nicht fahren, berichten. Christopher einmal je Probe bitten
und die Antwort wörtlich festhalten: „Bitte stelle Amadeus für Probe <P> an
die Stelle <Stelle> wie in der Tabelle. Welche Abstände hast du eingestellt
(vorn, seitlich, hinten)? Steht er still und bleibt er während des Starts
(etwa eine Minute) unberührt? Ist der Motor-Stop-Schalter freigegeben,
reicht der Akku? Stehst du mit der Hand am Not-Aus daneben?“ Nur nach „ja“
weiter.

### A2. Stack scharf starten (mit 100 ms Anfahrzeit)

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  > "$SH_PR/sh8c_$P/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8c_$P/launch.pid"; cat "$SH_PR/sh8c_$P/launch.pid"
date -Iseconds > "$SH_PR/sh8c_$P/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s (HWT-Einmessung) `nodes.txt` und `lifecycle.txt` erfassen wie
in SH-8b, dann:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
grep -n "Anfahrverhalten bestaetigt" "$SH_PR/sh8c_$P/launch.log" | tee "$SH_PR/sh8c_$P/anfahrzeit.txt"
```

Erwartet: **`Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`**.
Steht dort ein anderer Wert, fehlt die Zeile oder steht „nicht bestaetigt“
im Log: **keine Mission**, Stack geordnet beenden, berichten. Meldet der
LiDAR-Treiber „communication is abnormal“: Stack geordnet beenden,
Christopher einmal bitten, den LiDAR-Stecker zu prüfen, einmal neu starten
(zählt zur Gesamtzahl der Starts).

### A3. Vorprüfung mit Eigenechos

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && P=s3a && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 \
  --json "$SH_PR/sh8c_$P/vorpruefung.json" 2>&1 | tee "$SH_PR/sh8c_$P/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Erwartet: Exit 0 mit denselben Zeilen wie in SH-8b, einschließlich Bereich
`F Eigenechos` (vier OK-Zeilen). Bei `FEHL` in „D Quellen“: nicht fahren,
Stack geordnet beenden, einmal neu starten. **Bei `FEHL` im Bereich F: nicht
fahren, Stack geordnet beenden, keine Wiederholung, Auftrag beenden und
berichten.** Jeder andere `FEHL` (nach einer Wiederholung nach 30 s bei
„erreichbar“, „nicht deklariert“ oder „Graph unvollständig“): Stack
geordnet beenden und berichten.

### A4. Protokoll mit Stellprobe starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh8c_$P/protokoll.json" \
  --stellprobe-m 0.5 --stellprobe-fenster-s 360 --nachlauf-s 1 --max-s 900 \
  > "$SH_PR/sh8c_$P/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh8c_$P/protokoll.pid"
```

Das Protokoll liest nur mit. Es endet **1 s** (in SH-8b 5 s), nachdem
Amadeus 0,5 m weg ist, weil er jetzt in 5 s gut einen halben Meter weiter
wäre. Neu im Ergebnis: die Blöcke `tempo_folge` und `wackeln`.

### A5. Mission starten und warten

Christopher drückt in der App „Erkunden“. Steht die App nicht zur Verfügung,
sendet der Agent **genau einmal**:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
```

**Direkt nach dem Missionsstart** diesen Block starten. Er wartet, bis das
Protokoll endet (höchstens 8 min), und sendet dann **sofort genau einmal**
den Stopp, den auch die App sendet, sofern die Mission noch läuft:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
PROT=$(cat "$SH_PR/sh8c_$P/protokoll.pid")
for i in $(seq 480); do kill -0 "$PROT" 2>/dev/null || break; sleep 1; done
kill -0 "$PROT" 2>/dev/null && { kill -INT "$PROT"; sleep 3; }
ENDE=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['protokoll_ende'])" "$SH_PR/sh8c_$P/protokoll.json")
echo "protokoll_ende=$ENDE"
if [ "$ENDE" != "missionsende" ]; then
  ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
  date -Iseconds > "$SH_PR/sh8c_$P/missionsstopp.txt"
fi
```

Nach 0,5 m ist die Probe entschieden; jede weitere Fahrt an den Eimern
bringt nichts (niedrige Gegenstände seitlich sieht Amadeus nicht).

Der Agent greift sonst nicht ein. Christopher beobachtet aus der Nähe mit
der Hand am Not-Aus; nähert sich eine Ecke, eine Seite **oder das Heck** von
Amadeus sichtbar einem Hindernis, drückt er (das zählt als Eingriff und
beendet den Auftrag).

### A6. Probe sichern

Zuerst das Ergebnis lesen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
tail -60 "$SH_PR/sh8c_$P/protokoll.txt"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print(r['protokoll_ende'], json.dumps(r['stellprobe'], ensure_ascii=False)); [print(k, json.dumps(r[k], ensure_ascii=False)) for k in ('rueckfahrten','tempo_folge','wackeln','fahrbefehle')]" "$SH_PR/sh8c_$P/protokoll.json"
```

Danach, weiterhin nur lesend:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$SH_PR/sh8c_$P/explore_status_ende.txt" 2>&1
grep -o 'last_track_back[^}]*}' "$SH_PR/sh8c_$P/explore_status_ende.txt"
grep -nE "Begin navigating|Goal succeeded|Goal failed|Goal canceled|Controller patience exceeded|Failed to make progress|Running backup|backup completed successfully|backup failed|Collision Ahead|Exceeded time allowance|\[collision_monitor\].*Robot to" \
  "$SH_PR/sh8c_$P/launch.log" > "$SH_PR/sh8c_$P/ablauf.txt"; wc -l "$SH_PR/sh8c_$P/ablauf.txt"
grep -c "detected collision ahead" "$SH_PR/sh8c_$P/launch.log"
grep -c "Robot to approach" "$SH_PR/sh8c_$P/launch.log"
grep -c "process has died" "$SH_PR/sh8c_$P/launch.log"
grep -E "CMD: v=|TIMEOUT-STOP" "$SH_PR/sh8c_$P/launch.log" > "$SH_PR/sh8c_$P/basis.txt"; wc -l "$SH_PR/sh8c_$P/basis.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 --json "$SH_PR/sh8c_$P/nachpruefung.json" 2>&1 | grep -E "F Eigenechos|ERGEBNIS" | tee "$SH_PR/sh8c_$P/nachpruefung_f.txt"
timeout 15 ros2 topic echo --once --full-length /local_costmap/costmap > "$SH_PR/sh8c_$P/lokale_kostenkarte_ende_voll.txt" 2>&1
```

Liegen nach der Fahrt **LiDAR- oder VL53-Punkte** im Gehäuse (`FEHL` in
einer dieser drei Zeilen): Auftrag nach dieser Probe beenden und berichten.
Tödliche Zellen der Kostenkarte im Gehäuse nach der Fahrt nur berichten.

**Nur bei Urteil `nicht_befreit` oder „Hilfe benötigt“** zusätzlich
(Amadeus steht):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
P=s3a
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$SH_PR/sh8c_$P/tf_map_base_link.txt" 2>&1
timeout 8 ros2 run tf2_ros tf2_echo odom base_link > "$SH_PR/sh8c_$P/tf_odom_base_link.txt" 2>&1
```

Christopher einmal fragen und wörtlich festhalten. Die Fragen **wörtlich
und ohne Hinweis auf Messwerte** stellen:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Was hast du gesehen: zurückgesetzt, gedreht, gestanden? In welcher
   Reihenfolge, und wie nah kam er dem Hindernis dabei (sichtbare Lücke,
   etwa wie viele Zentimeter)? Wie viel Platz blieb hinter ihm beim
   Zurücksetzen?
4. Hat der Aufbau (Mast, Kamera) sichtbar gewackelt oder geruckt? Wenn ja:
   beim Anfahren, beim Anhalten, beim Drehen oder mitten in der Fahrt?
5. Wie wirkte das Tempo auf dich: passend, zu schnell, zu langsam?

Danach den Stack geordnet beenden (SIGINT nur an die Launch-PID,
`roboterknoten.py` danach leer). Läuft das Protokoll noch, es vorher per
SIGINT an `protokoll.pid` beenden.

### A7. Urteil je Probe und wie es weitergeht

| Urteil | Bedeutung | Weiter |
|---|---|---|
| `befreit` | mindestens eine Heilung, danach 0,5 m vom Standort weg, innerhalb von 6 min | nächste Probe |
| `nicht_blockiert` | ohne Heilung weggefahren: Die Stelle hat ihn nicht blockiert, die Probe sagt nichts aus | **einmal** wiederholen mit **3 cm** statt 5 cm (Kennung mit Zusatz `_nah`); bleibt es dabei, als „Stelle blockiert nicht“ berichten und weiter |
| `nicht_befreit` | nach 6 min nicht 0,5 m weg, oder „Hilfe benötigt“ | die zweite Probe **derselben** Stelle entfällt; mit der nächsten Stelle weiter |
| Berührung, Eingriff, `outcome=error`, „process has died“, Eigenecho (A3 oder A6), falsche Anfahrzeit (A2) | | **Auftrag beenden**, nur berichten |

Höchstens zehn Starts mit Mission, höchstens zwölf Starts insgesamt (Starts,
die „D Quellen“ oder ein LiDAR-Startfehler vor der Mission abfängt, zählen
nur zur Gesamtzahl). Laden zwischen den Proben ist erlaubt.

**Stellprobe bestanden**, wenn keine Probe mit `nicht_befreit`, Berührung,
Eingriff oder Eigenecho endete und jede der drei Stellen mindestens einmal
`befreit` ergab. Danach folgt **kein** weiterer Schritt in diesem Auftrag;
die volle Fahrt kommt nach der Auswertung als eigener Auftrag.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei:
  - Berührung, auch leicht, auch an Mülleimer, Jacke, Türrahmen oder Türblatt;
  - Fahrt oder Drehung auf ein Hindernis ohne rechtzeitiges Abbremsen;
  - Rückfahrt auf etwas zu, das hinter ihm steht;
  - starkem Schwanken des Aufbaus;
  - Fahrt in einen dritten Raum oder durch eine Tür, die zu sein sollte;
  - ungewöhnlichem Geräusch;
  - Rauch.

  Danach keine weitere Probe in dieser Sitzung; nur berichten.
- **Endet eine Probe mit `outcome=error`:** anhalten und berichten.
- **Ungültige Probe** aus einem äußeren Grund (zum Beispiel kommt jemand in
  den Raum): darf einmal wiederholt werden.
- Keine Parameter ändern, um eine Probe „durchzubringen“.

## Bewertung

Die Kriterien stehen vor der ersten Probe fest und sind dieselben wie in
SH-8b.

| Nr | Kriterium | Quelle |
|---|---|---|
| P1 | Urteil `befreit` | `protokoll.json`, Block `stellprobe` |
| P2 | keine Berührung, kein Eingriff | Christophers Antworten 1 und 2 |
| P3 | kein „Hilfe benötigt“, kein `outcome=error`, kein „process has died“ | Protokoll, `launch.log` |
| P4 | kein Eigenecho: Bereich F in A3 ohne `FEHL`, in A6 keine LiDAR- oder VL53-Punkte im Gehäuse | `vorpruefung.txt`, `nachpruefung_f.txt` |

Stellprobe bestanden: siehe A7. **Gemessen, aber kein Kriterium:** Zeit bis
0,5 m weg; Zahl, Dauer und Strecke der Rückfahrten; `tempo_folge` (Weg und
Drehung gefahren zu befohlen); `wackeln` (Ruhe, Fahrt, stärkste Sekunden
und ihre Lage); Zahl „approach“ und „detected collision ahead“; wie nah
Amadeus dem Hindernis kam und wie viel Platz hinten blieb (Christopher).

## Bericht: `~/selbstheilung_jetson_bericht_sh8c.md`

1. Kopf: Datum, Release, HEAD, Ergebnis der Schritte 0 und 1 (Zähler,
   Testergebnis), Aufbau mit Christophers Antwort wörtlich.
2. **Tabelle über alle Proben:** Kennung, Stelle, eingestellte Abstände
   (vorn, seitlich, hinten), Zeile „Anfahrverhalten bestaetigt“, Urteil,
   Zeit bis 0,5 m weg, Heilungen und Rückfahrten bis dahin, größte
   Entfernung, `weg_gefahren_zu_befohlen`, `drehung_gedreht_zu_befohlen`,
   größtes Wackeln (rad/s) und seine Lage, Zahl „approach“, Zahl „detected
   collision ahead“, Christophers fünf Antworten wörtlich.
3. **Je Probe der Ablauf** aus `ablauf.txt` (wörtlich, gleiche
   aufeinanderfolgende Zeilen zusammenfassen), dazu: Vorprüfung (Exit, Zahl
   OK/FEHL, die Zeilen des Bereichs F wörtlich), Nachprüfung (Zeilen F
   wörtlich), `heilungsverlauf`, `last_track_back`, die Blöcke
   `rueckfahrten`, `tempo_folge` und `wackeln` wörtlich, und **für jede
   Rückfahrt**: Ergebnis des `behavior_server` (erfolgreich, Zeitgrenze,
   „Collision Ahead“), Strecke laut Protokoll, Zustand des
   Kollisionsmonitors davor und währenddessen, welches Ziel danach kam.
   Aus `basis.txt` je Probe die Zahl der `CMD`- und `TIMEOUT-STOP`-Zeilen
   und fünf Beispielzeilen mit den größten Motordrehzahlen.
4. **Urteil:** Stellprobe bestanden / nicht bestanden, mit Grund. Für jede
   Probe `nicht_befreit` die Daten wie in SH-8b (`map→odom`, Zellen ≥ 99 und
   = 100 im Umkreis von 1,5 m, Zellen an der Kontur; Werkzeug
   `sh8_stelle.py` aus dem SH-8-Prüfordner nach `$SH_PR/werkzeug/` kopieren
   und Pfade anpassen).
5. **Vergleich mit SH-8b** je Stelle in einer Tabelle: Urteil, Zeit bis
   0,5 m weg, Strecke der ersten Rückfahrt.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad; je Probe Kennung,
Urteil, Zeit bis 0,5 m weg, Strecke der ersten Rückfahrt,
`weg_gefahren_zu_befohlen` und größtes Wackeln; Eigenecho-Ergebnis;
Stellprobe bestanden oder nicht; Kontakte oder Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Bestanden: KM-1 B und die Anfahrzeit
100 ms gelten für das aktive Problem als bestätigt; es folgt die volle
Zwei-Raum-Fahrt als eigener Auftrag. Nicht bestanden: zuerst die Daten
(MASTERPLAN §9 Regel 4), kein weiterer Versuch ohne neue Auswertung.
