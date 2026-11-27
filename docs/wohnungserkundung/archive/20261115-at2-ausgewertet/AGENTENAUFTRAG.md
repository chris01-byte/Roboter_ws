# Aktueller Agentenauftrag: AT-2 – Antriebsprobe mit kurzer Anfahrzeit (100 ms), Sollwerte wie unter Nav2

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.11.2026 nach
der Auswertung von AT-1b
([Archiv](archive/20261115-at1b-ausgewertet/README.md), STATUS Abschnitte
15.11.2026). Der Projektinhaber hat diese Messfahrt am 15.11.2026
ausdrücklich freigegeben: wieder **direkt an der Basis** (ohne
Nahbereichsbremse) und mit **Anfahrzeit 100 ms** im Antrieb.

**Was AT-1b gezeigt hat:** Der Antrieb folgt Sprüngen und Stufen voll,
Rampen in 20-Hz-Schritten aber nur mit 11–22 %. Erklärung (Rechenmodell
`tools/kartierung/antriebsmodell.py`): Er verteilt jede Sollwertänderung auf
seine Anfahrzeit von 2000 ms, gerechnet ab dem vorigen Sollwert. Nach einer
feinen Rampe bestimmt der letzte kleine Schritt die Beschleunigung. Nav2
sendet immer solche Rampen; daher das Kriechtempo und die zu kurzen
Rückfahrten. Deine Messung war sauber und hat das entschieden, danke.

**Was diese Probe prüft:** Folgt der Antrieb den Befehlen, wie Nav2 sie
sendet, wenn seine Anfahrzeit auf 100 ms steht (der Stand bis 14.08.2026)?
Und bleibt der hohe Aufbau dabei ruhig?

**Die einzige Änderung** gegenüber AT-1b ist das Startargument
`hwt601_accel_ms:=100` (seit 10.10.2026 als Laborvergleich 100–2000
vorgesehen). Kein Code, kein Build, keine Parameterdatei, keine Mission.
`base_hardware` schreibt die Anfahrzeit bei jedem Start neu in den Antrieb;
der nächste normale Start setzt wieder 2000 ms.

**Programm AT-2** (das Werkzeug sendet nur Befehlsformen wie unter Nav2;
jede Änderung ist begrenzt wie im Glätter, auch auf den Rückwegen):

| Phase | Sollwertfolge | gemessen bzw. gerechnet bei 2000 ms | Vorhersage des Modells bei 100 ms |
|---|---|---|---|
| C | Rampe auf 0,10 m/s, 6 s | 0,04–0,08 m, Ist/Soll 0,11–0,22 (AT-1b) | etwa 0,49 m, Ist/Soll 1,0 |
| G | Rampe auf 0,10 m/s, ab auf 0,04 m/s, auf 0,08 m/s | etwa 0,2 m, oben 0,05 | etwa 0,56 m, alle drei Abschnitte 1,0 |
| R | langsame Rückfahrt wie in der Langsam-Zone: Rampe auf −0,015 m/s, 8 s | etwa 0,01 m | etwa 0,11 m rückwärts, Ist/Soll 1,0 |
| E | Rampe drehen auf 0,25 rad/s, 6 s | etwa 6°, Ist/Soll 0,11 (AT-1b) | etwa 70°, Ist/Soll 1,0 |
| S | Rampe auf 0,03 m/s, dann **Stufe** auf 0,10 m/s (wie beim Verlassen der Langsam-Zone) | – | etwa 0,49 m; hier kann der Aufbau rucken |

Die Vorhersagen sind eine Rechnung, keine Messung. Weicht die Messung ab,
ist das ein Ergebnis und kein Fehler der Probe.

Nach jeder Phase steht Amadeus 3 s und fährt bzw. dreht mit einer Rampe
zurück. Eine Probe dauert etwa 3 Minuten. Sprünge aus dem Stand (A, B, F,
D) sind mit der Freigabe `AT-2` im Werkzeug gesperrt.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), im STATUS die Arbeitsliste und die Abschnitte
15.11.2026, und den Kopf von `tools/kartierung/antriebsprobe.py`.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 15.11.2026; **Fahrplan §9 Regel 1** (eine Änderung je Realtest) und AGENTS §2.7 (Motorsteuerung getrennt ändern und getrennt prüfen) |
| WE-Bezug | Vorarbeit zu WE-M3; keine Abnahme |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `50b41e4`; **kein Build**, es läuft der vorhandene Release `selbstheilung-sh8b-20261114_1643` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_at2.md`: zwei Proben mit je fünf Phasen bei 100 ms Anfahrzeit; Urteil, ob der Antrieb Rampen folgt; Christophers Beobachtung zum Aufbau |
| Nicht-Ziele | keine Code- oder Dateiänderung, keine Mission, kein Nav2-Ziel, kein Build, keine andere Anfahrzeit als 100 ms, keine Änderung der Bremszeit |
| Rückfall | nichts zu tun: Der nächste Start ohne das Argument schreibt wieder 2000 ms in den Antrieb |
| Laborrahmen | LAB-1 und die ausdrückliche Freigabe des Projektinhabers vom 15.11.2026 für genau diese Messfahrt **direkt an der Basis ohne Kollisionsmonitor mit Anfahrzeit 100 ms**. Not-Aus-Erreichbarkeit und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden nicht erneut abgefragt |

## Verboten

- keine Code- oder Parameteränderung, kein Commit oder Push, kein Build;
- schreibend nur: der Stackstart mit `hwt601_accel_ms:=100` und **höchstens
  dreimal** das Werkzeug `antriebsprobe.py --topic /cmd_vel --freigabe AT-2`
  (zwei Proben, eine Wiederholung nach einem äußeren Abbruch); kein
  `param set`, `lifecycle set`, `service call`, kein `topic pub`, keine
  Mission, keine Nav2-Ziele, kein Modbus-Zugriff neben dem laufenden Treiber;
- das Werkzeug nicht verändern, keine anderen Sollwerte, kein anderes
  Topic, kein anderes Freigabewort, keine andere Anfahrzeit;
- `operator_stationary_confirmed:=true` nur nach Christophers „ja“;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws` (auch nicht die fremden Änderungen dort) und an
  der defekten Codex-Referenz; bestehende Releases und frühere Berichte
  bleiben, wie sie sind;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht.

**Ausdrücklich erlaubt:** rein lesende Zusatzmessungen wie in AT-1 und
AT-1b (`ros2 topic info -v`, `topic echo --once`, ein eigener Zählknoten
ohne Publisher).

## Sicherheit dieser Messfahrt

- Die Befehle gehen auf `/cmd_vel`, **direkt an die Basis. Der
  Kollisionsmonitor bremst in dieser Probe nicht.** Vor einem Hindernis hält
  Amadeus nicht von selbst an.
- Deshalb gilt: freie Fläche wie in Schritt 2, Christopher steht mit der
  Hand am Not-Aus daneben, und niemand betritt die Fläche.
- Höchstens 0,10 m/s vorwärts, 0,05 m/s rückwärts auf den Rückwegen,
  0,015 m/s in der Rückfahrphase, 0,25 rad/s.
- Das Werkzeug bricht mit Nullbefehlen ab bei: Not-Aus, veralteter
  Odometrie, mehr als 0,9 m vor oder 0,2 m hinter dem Ausgangspunkt, mehr
  als 0,35 rad Richtungsabweichung beim Geradeausfahren, fremden
  Nachrichten auf `/cmd_vel`, Strg-C.
- Fällt das Werkzeug aus, stoppt die Basis nach 0,25 s von selbst. Die
  Bremszeit (400 ms) ist unverändert.
- **Rückwärts sieht Amadeus nichts.** In Phase R fährt er etwa 0,11 m
  hinter den Ausgangspunkt; hinter ihm bleiben mindestens 0,5 m frei.

## Schritt 0 – Bestand

```bash
date -Iseconds
git -C ~/roboter_ws rev-parse HEAD; git -C ~/roboter_ws status --short | head -8
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

Läuft ein Robotik-Stack (auch ein einzelner LiDAR-Treiber aus
`~/roboter_ws/install`): nichts beenden, Christopher genau einmal fragen.
Die fremden Änderungen in `~/roboter_ws` nur notieren.

## Schritt 1 – Klon aktualisieren, Ordner, Werkzeugtest

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "$SH_SRC $SH_REL"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor 50b41e4 HEAD && echo "50b41e4 enthalten"
mkdir -p "$SH_PR/at2"
cd "$SH_SRC" && python3 -m pytest -q -p no:cacheprovider \
  tools/kartierung/test_antriebsprobe.py tools/kartierung/test_antriebsmodell.py 2>&1 | tail -3
```

Erwartet: `SH_REL` endet auf `selbstheilung-sh8b-20261114_1643`, `23 passed`.
Sonst nicht fahren, berichten.

## Schritt 2 – Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern und die Antwort wörtlich
festhalten:

„Bitte stelle Amadeus für die Antriebsprobe auf eine freie Fläche:
1. vor seiner Front mindestens 1,5 m frei, seitlich je mindestens 0,6 m,
   hinter ihm mindestens 0,5 m; auch keine niedrigen Dinge am Boden;
2. der Motor-Stop-Schalter ist freigegeben, der Akku reicht für 15 Minuten;
3. du stehst während der Proben mit der Hand am Not-Aus daneben.

**Wichtig: In dieser Probe bremst Amadeus nicht von selbst vor
Hindernissen.** Er fährt dreimal ein Stück vor und wieder zurück (bis etwa
0,6 m, höchstens 0,9 m), einmal langsam etwa 10 cm rückwärts und dreht sich
einmal um etwa eine Vierteldrehung und zurück. Bitte achte diesmal auf den
Aufbau (Mast und Kamera): Wackelt oder ruckt er irgendwann sichtbar?“

## Schritt 3 – Stack scharf starten (Anfahrzeit 100 ms), Vorprüfung, Topic messen

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  > "$SH_PR/at2/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/at2/launch.pid"; cat "$SH_PR/at2/launch.pid"
date -Iseconds > "$SH_PR/at2/launch_start.txt"
```

Derselbe Start wie in AT-1b, nur mit `hwt601_accel_ms:=100`. **Es wird
keine Mission gestartet.** Nach etwa 60 s (HWT-Einmessung):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
grep -n "Anfahrverhalten bestaetigt" "$SH_PR/at2/launch.log" | tee "$SH_PR/at2/anfahrzeit.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/at2/vorpruefung.json" 2>&1 | tee "$SH_PR/at2/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
ros2 topic info -v /cmd_vel | tee "$SH_PR/at2/topic_cmd_vel.txt"
```

Erwartet:

- **`Anfahrverhalten bestaetigt: Beschleunigen 100 ms, Bremsen 400 ms,
  Startdrehzahl 5 rpm.`** Steht dort ein anderer Wert, fehlt die Zeile oder
  steht „nicht bestaetigt“ im Log: **nicht fahren**, Stack geordnet beenden,
  berichten. Bricht schon der Start mit einer Meldung zur Anfahrrampe ab:
  wörtlich berichten, nichts umgehen.
- Vorprüfung Exit 0 wie in AT-1b. Bei `FEHL` in „D Quellen“: Stack geordnet
  beenden, einmal neu starten (wieder mit `hwt601_accel_ms:=100`). Jeder
  andere `FEHL`: Stack geordnet beenden und berichten, keine Probe.
- In `topic info -v` als einziger Publisher der `collision_monitor`.

**Dann die Messanordnung selbst messen** (rein lesend, Zählknoten wie in
AT-1b): Nachrichten auf `/cmd_vel` über mindestens 8 s zählen. Ergebnis
wörtlich in den Bericht. 0 Nachrichten: weiter. Mehr als 0: nicht fahren,
festhalten wer sendet, Stack geordnet beenden, berichten.

## Schritt 4 – Probe 1

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/antriebsprobe.py" --topic /cmd_vel --freigabe AT-2 \
  --json "$SH_PR/at2/probe1.json" 2>&1 | tee "$SH_PR/at2/probe1.txt"; echo "exit=${PIPESTATUS[0]}"
```

Der Agent greift nicht ein. Christopher drückt den Not-Aus, wenn Amadeus
sich einem Hindernis nähert oder etwas Unerwartetes tut (das zählt als
Eingriff und beendet den Auftrag). Endet das Werkzeug mit einem Abbruch
(`exit=1`): Grund aus der Ausgabe festhalten.

- Abbruch wegen einer Grenze („mehr als 0,9 m“, „hinter dem
  Ausgangspunkt“, „Richtung“) oder wegen Not-Aus: Auftrag beendet, berichten.
- Abbruch „sendet schon jemand“ oder „fremder Sender“: keine weitere Probe;
  rein lesend feststellen, wer auf `/cmd_vel` sendet, und berichten.
- Nur bei einem äußeren Grund (jemand kommt in den Raum) darf die Probe
  einmal wiederholt werden.

Lautet das Urteil `gestoert`: keine zweite Probe, Schritt 6, berichten.

Danach die Basiszeilen dieser Probe sichern und Christopher fragen. Die
Fragen **wörtlich und ohne Hinweis auf Messwerte** stellen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
grep -E "CMD: v=|TIMEOUT-STOP" "$SH_PR/at2/launch.log" > "$SH_PR/at2/basis_nach_probe1.txt"; wc -l "$SH_PR/at2/basis_nach_probe1.txt"
```

1. Hat Amadeus etwas berührt? Musstest du eingreifen?
2. Hat der Aufbau (Mast, Kamera) irgendwann sichtbar gewackelt oder
   geruckt? Wenn ja: beim Anfahren, beim Langsamerwerden, beim Anhalten
   oder mitten in der Fahrt, und in welcher der fünf Fahrten ungefähr?
3. Fuhr und drehte er zügig, oder kroch er irgendwo?
4. Steht er wieder etwa am Ausgangspunkt? Falls nicht: bitte zurückstellen.

## Schritt 5 – Probe 2 (Wiederholung, gleicher Standort)

Wie Schritt 4, mit `probe2.json`, `probe2.txt` und `basis_nach_probe2.txt`;
dieselben vier Fragen.

## Schritt 6 – Stack beenden

Stack geordnet beenden (SIGINT nur an die Launch-PID aus
`$SH_PR/at2/launch.pid`), danach `roboterknoten.py`: „Keine Amadeus-Knoten
aktiv.“ Es wird kein weiterer Stack gestartet, um die Anfahrzeit
zurückzustellen; das tut der nächste normale Start von selbst.

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus; Agent: Stack geordnet beenden)
  bei Berührung, Fahrt auf ein Hindernis zu, ungewöhnlichem Geräusch, Rauch,
  starkem Schwanken des Aufbaus, oder wenn Amadeus den freien Bereich
  verlässt. Danach keine weitere Probe in dieser Sitzung; nur berichten.
- Keine Parameter ändern, um eine Probe „durchzubringen“.

## Bewertung (vor der ersten Probe festgelegt)

Das Werkzeug schreibt das Urteil in den Block `urteil`, Schlüssel
`antrieb_folgt_rampen`. Bewertet werden sechs Abschnitte (C Ende; G oben,
unten, wieder; R Ende; E Ende), jeweils `ist_zu_soll` = gemessenes Tempo
geteilt durch den Sollwert:

| Urteil | Bedingung |
|---|---|
| `gestoert` | in einem der sechs Abschnitte kam an der Basis nicht der Sollwert an (Abweichung über 15 %) |
| `ja` | alle sechs Abschnitte zwischen 0,8 und 1,2 |
| `nein` | Vorwärtsrampe (C) und Drehrampe (E) beide unter 0,4, wie in AT-1b |
| `teilweise` | alles andere; die abweichenden Abschnitte stehen in `ausserhalb_0_8_bis_1_2` |

Die Probe gilt als bestanden, wenn **beide Proben `ja`** liefern. Ohne
Kriterium zusätzlich: die Stufe in S (`stufe_langsam_zone_ist_zu_soll`),
das Tempo je Sekunde jeder Phase und Christophers Beobachtung zum Aufbau.
Ob 100 ms als Standard taugt, entscheidet der Projektinhaber nach dem
Bericht; ein `ja` allein ändert nichts am Standard.

## Bericht: `~/selbstheilung_jetson_bericht_at2.md`

1. Kopf: Datum, HEAD, Release, Ergebnis der Schritte 0–3 (Werkzeugtest,
   **die Zeile „Anfahrverhalten bestaetigt“ wörtlich**, Vorprüfung Exit und
   Zahl OK/FEHL, `topic info -v /cmd_vel`, die Zählung auf `/cmd_vel` vor
   der ersten Probe), Aufbau mit Christophers Antwort wörtlich.
2. Je Probe: Ausgabe des Werkzeugs wörtlich (`probe<n>.txt`), der Block
   `urteil`, `abbruch`, `vor_dem_start_fremde_nachrichten` und
   `fremde_nachrichten` aus `probe<n>.json`, und eine Tabelle über die
   Phasen: Weg bzw. Drehwinkel, `tempo_je_s`, je Abschnitt Soll, Befehl an
   der Basis, `gestoert`, Ist-Tempo, `ist_zu_soll`; dazu die Rückwege
   (`rueckwege`).
3. Je Probe aus `basis_nach_probe<n>.txt`: Zahl der `CMD`- und
   `TIMEOUT-STOP`-Zeilen während der Probe und je Phase zwei bis drei
   Beispielzeilen wörtlich (mit den Motor-U/min).
4. Christophers Antworten je Probe wörtlich.
5. Urteil: `ja`, `teilweise`, `nein` oder `gestoert`, mit den Zahlen beider
   Proben; daneben in einer Tabelle die Vorhersage des Modells aus diesem
   Auftrag und der gemessene Wert.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes.

Am Ende im Chat nur: Pfad; je Probe das Urteil und `ist_zu_soll` der sechs
Abschnitte und der Stufe; Christophers Antwort zum Aufbau; Abbrüche,
Berührungen oder Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Bei zweimal `ja` und ruhigem Aufbau
entscheidet der Projektinhaber, ob 100 ms der Standard für den autonomen
Betrieb wird; danach folgt die Stellprobe mit dieser einen Änderung. Bei
`teilweise`, `nein` oder auffälligem Rucken zuerst die Daten; kein weiterer
Versuch ohne neue Auswertung.
