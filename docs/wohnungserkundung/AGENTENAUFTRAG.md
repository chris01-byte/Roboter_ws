# Aktueller Agentenauftrag: AT-1 – Antriebsprobe (reine Messung: Sollwert gegen Encoder-Tempo)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 14.11.2026 nach
der Auswertung von SH-8b und Anhang Z
([Archiv](archive/20261114-sh8b-ausgewertet/README.md)). Der Projektinhaber
hat diese Messfahrt am 14.11.2026 ausdrücklich freigegeben.

**Warum:** In sechs Fahrten kamen an der Basis 6,4–10,1 cm/s an, gefahren
wurden 1,3–1,7 cm/s. In SH-8b legten vier Rückfahrten, bei denen 30 s lang
−1,5 cm/s befohlen waren (das wären 0,45 m), genau 0,151 m (dreimal) und
0,215 m zurück. Das entspricht 8 und 11 U/min am Motor, den ersten Stufen
der Anfahrrampe.

**Hypothese (aus Code und Zahlen, am Antrieb nicht gemessen):** Der Antrieb
übernimmt einen Sollwert nur mit dem Startimpuls beim Anfahren. Spätere
Sollwerte schreibt `base_hardware` seit dem 16.08.2026 ohne Startimpuls; der
Motor fährt dann bis zum nächsten Halt mit dem **ersten** Wert weiter. Unter
Nav2 ist das eine kleine Stufe der Rampe.

**Was diese Probe tut:** Sie fährt auf freier Fläche sechs feste
Sollwertfolgen und misst über `/odom`, was der Antrieb daraus macht. Es wird
**nichts geändert**: kein Code, kein Parameter, kein Register, keine
Mission, kein Nav2-Ziel.

| Phase | Sollwertfolge | erwartet, wenn der Antrieb alles umsetzt | erwartet, wenn die Hypothese stimmt |
|---|---|---|---|
| A | Sprung auf 0,10 m/s, 5 s | etwa 0,45 m | etwa 0,45 m (erster Sollwert ist schon der volle) |
| B | 0,02 m/s 4 s, dann 0,10 m/s 5 s | etwa 0,55 m | etwa 0,18 m (bleibt bei 0,02 m/s) |
| C | Rampe wie Nav2 auf 0,10 m/s, 6 s | etwa 0,5 m | wenige Zentimeter |
| F | 0,10 m/s 3 s, dann 0,03 m/s 4 s | etwa 0,35 m | etwa 0,6 m (bremst nicht ab) |
| D | Sprung auf 0,25 rad/s, 6 s | etwa 80° | etwa 80° |
| E | Rampe auf 0,25 rad/s, 6 s | etwa 75° | wenige Grad |

Nach jeder Phase steht Amadeus 3 s und fährt bzw. dreht dann mit einem
Sprung (−0,05 m/s bzw. 0,25 rad/s) zum Ausgangspunkt zurück. Eine Probe
dauert etwa 3 bis 4 Minuten.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), im STATUS die Arbeitsliste und die Abschnitte
14.11.2026, und den Kopf von `tools/kartierung/antriebsprobe.py`.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 14.11.2026; **Fahrplan §9 Regel 4** (nach einem Fehlschlag zuerst Daten) für das aktive Problem; AGENTS §2.7 (Motorsteuerung getrennt messen) |
| WE-Bezug | Vorarbeit zu WE-M3; keine Abnahme |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `fcf95fc`; **kein Build**, es läuft der vorhandene Release `selbstheilung-sh8b-20261114_1643` (der Motortreiber ist in allen Releases derselbe) |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_at1.md`: zwei Proben mit je sechs Phasen, je Phase Soll, Befehl an der Basis, Ist-Tempo und Weg; Urteil zur Hypothese |
| Nicht-Ziele | keine Code-, Parameter- oder Registeränderung, keine Mission, kein Nav2-Ziel, kein Build, kein Test anderer Geschwindigkeiten |
| Rückfall | nichts zu tun; es wird nichts geändert |
| Laborrahmen | LAB-1 und die ausdrückliche Freigabe des Projektinhabers vom 14.11.2026 für genau diese Messfahrt. Not-Aus-Erreichbarkeit und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden nicht erneut abgefragt |

## Verboten

- keine Code- oder Parameteränderung, kein Commit oder Push, kein Build;
- schreibend nur: der Stackstart und **höchstens dreimal** das Werkzeug
  `antriebsprobe.py --freigabe AT-1` (zwei Proben, eine Wiederholung nach
  einem äußeren Abbruch); kein `param set`, `lifecycle set`, `service call`,
  kein `topic pub`, keine Mission, keine Nav2-Ziele, kein Modbus-Zugriff
  neben dem laufenden Treiber;
- das Werkzeug nicht verändern und keine anderen Sollwerte ausprobieren;
- `operator_stationary_confirmed:=true` nur nach Christophers „ja“;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws` und an der defekten Codex-Referenz; bestehende
  Releases und frühere Berichte bleiben, wie sie sind;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht.

## Sicherheit dieser Messfahrt

- Die Befehle gehen auf `/cmd_vel_smoothed`, also **durch den
  Kollisionsmonitor** (VL53) zur Basis. Umgangen wird nur der Glätter, damit
  die Sollwertfolge unverändert ankommt.
- Höchstens 0,10 m/s vorwärts, 0,05 m/s rückwärts, 0,25 rad/s.
- Das Werkzeug bricht mit Nullbefehlen ab bei: Not-Aus, veralteter
  Odometrie, mehr als 0,9 m vor oder 0,2 m hinter dem Ausgangspunkt, mehr
  als 0,35 rad Richtungsabweichung beim Geradeausfahren, Strg-C.
- Fällt das Werkzeug aus, stoppt die Basis nach 0,25 s von selbst.
- **Rückwärts sieht Amadeus nichts.** Er fährt nur dorthin zurück, wo er
  gerade herkam; trotzdem bleibt der Bereich hinter ihm frei.

## Schritt 0 – Bestand

```bash
date -Iseconds
git -C ~/roboter_ws rev-parse HEAD; git -C ~/roboter_ws status --short | head -5
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

Läuft ein Robotik-Stack (auch der einzelne LiDAR-Treiber aus
`~/roboter_ws/install`, der am 14.11. um 17:55 lief): nichts beenden,
Christopher genau einmal fragen.

## Schritt 1 – Klon aktualisieren, Ordner, Werkzeugtest

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "$SH_SRC $SH_REL"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor fcf95fc HEAD && echo "fcf95fc enthalten"
mkdir -p "$SH_PR/at1"
cd "$SH_SRC" && python3 -m pytest -q -p no:cacheprovider tools/kartierung/test_antriebsprobe.py 2>&1 | tail -3
```

Erwartet: `SH_REL` endet auf `selbstheilung-sh8b-20261114_1643`, `8 passed`.
Sonst nicht fahren, berichten.

## Schritt 2 – Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern und die Antwort wörtlich
festhalten:

„Bitte stelle Amadeus für die Antriebsprobe auf eine freie Fläche:
1. vor seiner Front mindestens 1,5 m frei, seitlich je mindestens 0,6 m,
   hinter ihm mindestens 0,5 m; auch keine niedrigen Dinge am Boden;
2. markiere seinen Standort, zum Beispiel mit einem Stück Klebeband an einem
   Rad, und lege wenn möglich einen Zollstock neben seine Fahrspur;
3. der Motor-Stop-Schalter ist freigegeben, der Akku reicht für 15 Minuten;
4. du stehst während der Proben mit der Hand am Not-Aus daneben.

Er fährt sechsmal ein kurzes Stück vor und wieder zurück (höchstens 0,9 m)
und dreht sich zweimal um etwa eine Vierteldrehung und zurück. Bitte merke
dir grob, wie weit er in jeder der vier Vorwärtsphasen kommt.“

## Schritt 3 – Stack scharf starten und Vorprüfung

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/at1/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/at1/launch.pid"; cat "$SH_PR/at1/launch.pid"
date -Iseconds > "$SH_PR/at1/launch_start.txt"
```

Das ist derselbe Start wie in SH-8b, damit Treiber, Rechenlast und
Kollisionsmonitor wie im echten Betrieb laufen. **Es wird keine Mission
gestartet.** Nach etwa 60 s (HWT-Einmessung):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/at1/vorpruefung.json" 2>&1 | tee "$SH_PR/at1/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
ros2 topic info /cmd_vel_smoothed | tee "$SH_PR/at1/topic_cmd_vel_smoothed.txt"
```

Erwartet: Exit 0 wie in SH-8b; `/cmd_vel_smoothed` mit genau einem
Abonnenten (dem Kollisionsmonitor). Bei `FEHL` in „D Quellen“: Stack
geordnet beenden, einmal neu starten. Jeder andere `FEHL`: Stack geordnet
beenden und berichten, keine Probe.

## Schritt 4 – Probe 1

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/antriebsprobe.py" --freigabe AT-1 \
  --json "$SH_PR/at1/probe1.json" 2>&1 | tee "$SH_PR/at1/probe1.txt"; echo "exit=${PIPESTATUS[0]}"
```

Der Agent greift nicht ein. Christopher drückt den Not-Aus, wenn Amadeus
sich einem Hindernis nähert oder etwas Unerwartetes tut (das zählt als
Eingriff und beendet den Auftrag). Endet das Werkzeug mit einem Abbruch
(`exit=1`): Grund aus der Ausgabe festhalten. Ein Abbruch wegen einer
Grenze („mehr als 0,9 m“, „Richtung“) oder wegen Not-Aus beendet den
Auftrag; nur bei einem äußeren Grund (jemand kommt in den Raum) darf die
Probe einmal wiederholt werden.

Danach die Basiszeilen dieser Probe sichern und Christopher fragen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
grep -E "CMD: v=|TIMEOUT-STOP" "$SH_PR/at1/launch.log" > "$SH_PR/at1/basis_nach_probe1.txt"; wc -l "$SH_PR/at1/basis_nach_probe1.txt"
```

1. Hat Amadeus etwas berührt? Musstest du eingreifen?
2. Wie weit kam er ungefähr in den vier Vorwärtsphasen (erste, zweite,
   dritte, vierte)? In welcher fuhr er zügig, in welcher kroch er?
3. Wie weit drehte er sich in den beiden Drehphasen ungefähr?
4. Steht er wieder etwa am Ausgangspunkt? Falls nicht: bitte zurückstellen.

## Schritt 5 – Probe 2 (Wiederholung, gleicher Standort)

Wie Schritt 4, mit `probe2.json`, `probe2.txt` und `basis_nach_probe2.txt`;
dieselben vier Fragen.

## Schritt 6 – Stack beenden

Stack geordnet beenden (SIGINT nur an die Launch-PID aus
`$SH_PR/at1/launch.pid`), danach `roboterknoten.py`: „Keine Amadeus-Knoten
aktiv.“

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus; Agent: Stack geordnet beenden)
  bei Berührung, Fahrt auf ein Hindernis zu, ungewöhnlichem Geräusch, Rauch,
  oder wenn Amadeus den markierten Bereich verlässt. Danach keine weitere
  Probe in dieser Sitzung; nur berichten.
- Keine Parameter ändern, um eine Probe „durchzubringen“.

## Bewertung (vor der ersten Probe festgelegt)

Das Werkzeug schreibt das Urteil selbst in den Block `urteil`
(`ist_zu_soll` = gemessenes Tempo geteilt durch den Sollwert, jeweils in den
letzten zwei Sekunden eines Abschnitts):

| Urteil | Bedingung |
|---|---|
| `bestaetigt` | Sprung (A) mindestens 0,8, Rampe (C) **und** zweite Treppenstufe (B) unter 0,4 |
| `widerlegt` | Rampe (C) **und** zweite Treppenstufe (B) mindestens 0,8 |
| `unklar` | alles andere |

Die Hypothese gilt nur als bestätigt oder widerlegt, wenn **beide Proben
dasselbe Urteil** liefern. Zusätzlich gemessen, ohne Kriterium: Treppe
abwärts (F: bremst der Antrieb auf den kleineren Sollwert ab?), die beiden
Drehphasen, und ob der Befehl an der Basis dem Sollwert entspricht
(`an_der_basis_…`; weicht er ab, hat der Kollisionsmonitor eingegriffen).

## Bericht: `~/selbstheilung_jetson_bericht_at1.md`

1. Kopf: Datum, HEAD, Release, Ergebnis der Schritte 0–3 (Werkzeugtest,
   Vorprüfung Exit und Zahl OK/FEHL, `topic info`), Aufbau mit Christophers
   Antwort wörtlich.
2. Je Probe: Ausgabe des Werkzeugs wörtlich (`probe<n>.txt`), der Block
   `urteil` und `abbruch` aus `probe<n>.json`, und eine Tabelle über die
   Phasen: Weg bzw. Drehwinkel, je Abschnitt Soll, Befehl an der Basis,
   Ist-Tempo, `ist_zu_soll`; dazu die Rückwege (`rueckwege`).
3. Je Probe aus `basis_nach_probe<n>.txt`: Zahl der `CMD`- und
   `TIMEOUT-STOP`-Zeilen während der Probe und je Phase zwei bis drei
   Beispielzeilen wörtlich (mit den Motor-U/min).
4. Christophers Antworten je Probe wörtlich.
5. Urteil: bestätigt, widerlegt oder unklar, mit den Zahlen beider Proben.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes.

Am Ende im Chat nur: Pfad; je Probe das Urteil und `ist_zu_soll` für A, B
(zweite Stufe), C, F (zweite Stufe), D und E; Abbrüche, Berührungen oder
Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Bei `bestaetigt` folgt eine Korrektur im
Motortreiber als eigener, getrennt geprüfter Schritt (AGENTS §2.7), danach
dieselbe Probe erneut und dann die Stellprobe. Bei `widerlegt` oder
`unklar` zuerst die Daten; kein weiterer Versuch ohne neue Auswertung.
