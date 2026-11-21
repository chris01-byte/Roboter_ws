# Aktueller Agentenauftrag: AT-1b – Antriebsprobe direkt an der Basis (reine Messung, Wiederholung von AT-1)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.11.2026 nach
der Auswertung von AT-1
([Archiv](archive/20261115-at1-ausgewertet/README.md), STATUS Abschnitt
15.11.2026). Der Projektinhaber hat am 15.11.2026 ausdrücklich freigegeben,
dass diese Messfahrt die Basis **direkt** ansteuert, also **ohne die
Nahbereichsbremse** (VL53/Kollisionsmonitor).

**Warum eine Wiederholung:** AT-1 war gestört. Der Auftrag hatte
angenommen, auf `/cmd_vel_smoothed` sende ohne Mission niemand. Tatsächlich
sendet der Glätter dort mit 20 Hz Nullbefehle; die Basis bekam Sollwert und
Halt im Wechsel. Das war ein Fehler im Auftrag. Du hast ihn gefunden und
sauber belegt, danke.

**Was diesmal anders ist:**

- Das Werkzeug sendet auf **`/cmd_vel`**, den Eingang der Basis. Dort stand
  in AT-1 ohne Mission nichts (0 Nachrichten in 8 s und in 5 s).
- Das Werkzeug prüft das jetzt selbst: Es hört vor dem ersten Befehl 2 s auf
  sein Topic und fährt nicht, wenn dort jemand sendet. Tauchen während der
  Fahrt fremde Nachrichten auf, bricht es ab. Kommt an der Basis nicht der
  Sollwert an, lautet das Urteil `gestoert`.
- Du misst die Lage zusätzlich vor der ersten Probe selbst (Schritt 3).

**Hypothese (unverändert, am Antrieb nicht gemessen):** Der Antrieb
übernimmt einen Sollwert nur mit dem Startimpuls beim Anfahren. Spätere
Sollwerte schreibt `base_hardware` seit dem 16.08.2026 ohne Startimpuls; der
Motor fährt dann bis zum nächsten Halt mit dem **ersten** Wert weiter. Unter
Nav2 ist das eine kleine Stufe der Rampe.

Es wird **nichts geändert**: kein Code, kein Parameter, kein Register, keine
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
dauert etwa 3 bis 4 Minuten. **Anders als in AT-1 fährt Amadeus diesmal
voraussichtlich wirklich bis zu 0,55 m weit und zügig.**

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), im STATUS die Arbeitsliste und den Abschnitt
15.11.2026, und den Kopf von `tools/kartierung/antriebsprobe.py`.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 15.11.2026; **Fahrplan §9 Regel 4** (nach einem Fehlschlag zuerst Daten) für das aktive Problem; AGENTS §2.7 (Motorsteuerung getrennt messen) |
| WE-Bezug | Vorarbeit zu WE-M3; keine Abnahme |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `1b7faca`; **kein Build**, es läuft der vorhandene Release `selbstheilung-sh8b-20261114_1643` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_at1b.md`: zwei Proben mit je sechs Phasen, je Phase Soll, Befehl an der Basis, Ist-Tempo, Tempo je Sekunde und Weg; Urteil zur Hypothese |
| Nicht-Ziele | keine Code-, Parameter- oder Registeränderung, keine Mission, kein Nav2-Ziel, kein Build, kein Test anderer Geschwindigkeiten |
| Rückfall | nichts zu tun; es wird nichts geändert |
| Laborrahmen | LAB-1 und die ausdrückliche Freigabe des Projektinhabers vom 15.11.2026 für genau diese Messfahrt **direkt an der Basis ohne Kollisionsmonitor**. Not-Aus-Erreichbarkeit und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden nicht erneut abgefragt |

## Verboten

- keine Code- oder Parameteränderung, kein Commit oder Push, kein Build;
- schreibend nur: der Stackstart und **höchstens dreimal** das Werkzeug
  `antriebsprobe.py --topic /cmd_vel --freigabe AT-1b` (zwei Proben, eine
  Wiederholung nach einem äußeren Abbruch); kein `param set`,
  `lifecycle set`, `service call`, kein `topic pub`, keine Mission, keine
  Nav2-Ziele, kein Modbus-Zugriff neben dem laufenden Treiber;
- das Werkzeug nicht verändern, keine anderen Sollwerte, kein anderes Topic;
- `operator_stationary_confirmed:=true` nur nach Christophers „ja“;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws` (auch nicht die fremden Änderungen dort) und an
  der defekten Codex-Referenz; bestehende Releases und frühere Berichte
  bleiben, wie sie sind;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht.

**Ausdrücklich erlaubt:** rein lesende Zusatzmessungen wie in AT-1
(`ros2 topic info -v`, `topic echo --once`, ein eigener Zählknoten ohne
Publisher). Sie haben in AT-1 die Störung aufgedeckt.

## Sicherheit dieser Messfahrt

- Die Befehle gehen auf `/cmd_vel`, **direkt an die Basis. Der
  Kollisionsmonitor bremst in dieser Probe nicht.** Vor einem Hindernis hält
  Amadeus nicht von selbst an.
- Deshalb gilt: freie Fläche wie in Schritt 2, Christopher steht mit der
  Hand am Not-Aus daneben, und niemand betritt die Fläche.
- Höchstens 0,10 m/s vorwärts, 0,05 m/s rückwärts, 0,25 rad/s.
- Das Werkzeug bricht mit Nullbefehlen ab bei: Not-Aus, veralteter
  Odometrie, mehr als 0,9 m vor oder 0,2 m hinter dem Ausgangspunkt, mehr
  als 0,35 rad Richtungsabweichung beim Geradeausfahren, fremden
  Nachrichten auf `/cmd_vel`, Strg-C.
- Fällt das Werkzeug aus, stoppt die Basis nach 0,25 s von selbst.
- **Rückwärts sieht Amadeus nichts.** Er fährt nur dorthin zurück, wo er
  gerade herkam; trotzdem bleibt der Bereich hinter ihm frei.

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
  git rev-parse HEAD && git merge-base --is-ancestor 1b7faca HEAD && echo "1b7faca enthalten"
mkdir -p "$SH_PR/at1b"
cd "$SH_SRC" && python3 -m pytest -q -p no:cacheprovider tools/kartierung/test_antriebsprobe.py 2>&1 | tail -3
```

Erwartet: `SH_REL` endet auf `selbstheilung-sh8b-20261114_1643`, `12 passed`.
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
Hindernissen.** Er fährt viermal ein Stück vor und wieder zurück (bis etwa
0,55 m, höchstens 0,9 m) und dreht sich zweimal um etwa eine Vierteldrehung
und zurück. Diesmal fährt er voraussichtlich zügig, nicht kriechend. Du
musst nichts abmessen; Weg und Tempo misst die Odometrie.“

## Schritt 3 – Stack scharf starten, Vorprüfung, Topic messen

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/at1b/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/at1b/launch.pid"; cat "$SH_PR/at1b/launch.pid"
date -Iseconds > "$SH_PR/at1b/launch_start.txt"
```

Das ist derselbe Start wie in AT-1 und SH-8b, damit Treiber und Rechenlast
wie im echten Betrieb laufen. **Es wird keine Mission gestartet.** Nach
etwa 60 s (HWT-Einmessung):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/at1b/vorpruefung.json" 2>&1 | tee "$SH_PR/at1b/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
ros2 topic info -v /cmd_vel | tee "$SH_PR/at1b/topic_cmd_vel.txt"
```

Erwartet: Exit 0 wie in AT-1. Bei `FEHL` in „D Quellen“: Stack geordnet
beenden, einmal neu starten. Jeder andere `FEHL`: Stack geordnet beenden
und berichten, keine Probe.

**Dann die Messanordnung selbst messen** (rein lesend, mit deinem
Zählknoten aus AT-1 oder gleichwertig): Nachrichten auf `/cmd_vel` über
mindestens 8 s zählen. Ergebnis wörtlich in den Bericht.

- **0 Nachrichten:** weiter mit Schritt 4.
- **Mehr als 0:** nicht fahren. Festhalten, wer sendet (`topic info -v`),
  mit welcher Rate und welchen Werten; Stack geordnet beenden; berichten.

In `topic info -v` wird als einziger Publisher der `collision_monitor`
erwartet; Abonnenten dürfen mehrere sein (Basis, Mitleser). Ein weiterer
Publisher: nicht fahren, berichten.

## Schritt 4 – Probe 1

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/antriebsprobe.py" --topic /cmd_vel --freigabe AT-1b \
  --json "$SH_PR/at1b/probe1.json" 2>&1 | tee "$SH_PR/at1b/probe1.txt"; echo "exit=${PIPESTATUS[0]}"
```

Der Agent greift nicht ein. Christopher drückt den Not-Aus, wenn Amadeus
sich einem Hindernis nähert oder etwas Unerwartetes tut (das zählt als
Eingriff und beendet den Auftrag). Endet das Werkzeug mit einem Abbruch
(`exit=1`): Grund aus der Ausgabe festhalten.

- Abbruch wegen einer Grenze („mehr als 0,9 m“, „Richtung“) oder wegen
  Not-Aus: Auftrag beendet, berichten.
- Abbruch „sendet schon jemand“ oder „fremder Sender“: **keine weitere
  Probe.** Rein lesend feststellen, wer auf `/cmd_vel` sendet, und
  berichten.
- Nur bei einem äußeren Grund (jemand kommt in den Raum) darf die Probe
  einmal wiederholt werden.

Lautet das Urteil `gestoert`: keine zweite Probe, Schritt 6, berichten
(`an_der_basis` je Abschnitt und die `CMD`-Zeilen zeigen, was ankam).

Danach die Basiszeilen dieser Probe sichern und Christopher fragen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
grep -E "CMD: v=|TIMEOUT-STOP" "$SH_PR/at1b/launch.log" > "$SH_PR/at1b/basis_nach_probe1.txt"; wc -l "$SH_PR/at1b/basis_nach_probe1.txt"
```

1. Hat Amadeus etwas berührt? Musstest du eingreifen?
2. Ist dir aufgefallen, in welchen Phasen er zügig fuhr oder drehte und in
   welchen er kroch? (nur der Eindruck, nichts messen)
3. Steht er wieder etwa am Ausgangspunkt? Falls nicht: bitte zurückstellen.

## Schritt 5 – Probe 2 (Wiederholung, gleicher Standort)

Wie Schritt 4, mit `probe2.json`, `probe2.txt` und `basis_nach_probe2.txt`;
dieselben drei Fragen.

## Schritt 6 – Stack beenden

Stack geordnet beenden (SIGINT nur an die Launch-PID aus
`$SH_PR/at1b/launch.pid`), danach `roboterknoten.py`: „Keine Amadeus-Knoten
aktiv.“

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus; Agent: Stack geordnet beenden)
  bei Berührung, Fahrt auf ein Hindernis zu, ungewöhnlichem Geräusch, Rauch,
  oder wenn Amadeus den freien Bereich verlässt. Danach keine weitere
  Probe in dieser Sitzung; nur berichten.
- Keine Parameter ändern, um eine Probe „durchzubringen“.

## Bewertung (vor der ersten Probe festgelegt)

Das Werkzeug schreibt das Urteil selbst in den Block `urteil`
(`ist_zu_soll` = gemessenes Tempo geteilt durch den Sollwert, jeweils in den
letzten zwei Sekunden eines Abschnitts):

| Urteil | Bedingung |
|---|---|
| `gestoert` | in A, B (zweite Stufe) oder C kam an der Basis nicht der Sollwert an (Abweichung über 15 %); keine Aussage zur Hypothese |
| `bestaetigt` | Sprung (A) mindestens 0,8, Rampe (C) **und** zweite Treppenstufe (B) unter 0,4 |
| `widerlegt` | Rampe (C) **und** zweite Treppenstufe (B) mindestens 0,8 |
| `unklar` | alles andere |

Die Hypothese gilt nur als bestätigt oder widerlegt, wenn **beide Proben
dasselbe Urteil** liefern. Zusätzlich gemessen, ohne Kriterium: Treppe
abwärts (F: bremst der Antrieb auf den kleineren Sollwert ab?), die beiden
Drehphasen und das Tempo je Sekunde (`tempo_je_s`: folgt der Antrieb dem
Sollwert oder bleibt er auf einem Wert stehen, und auf welchem?).

## Bericht: `~/selbstheilung_jetson_bericht_at1b.md`

1. Kopf: Datum, HEAD, Release, Ergebnis der Schritte 0–3 (Werkzeugtest,
   Vorprüfung Exit und Zahl OK/FEHL, `topic info -v /cmd_vel`, **die Zählung
   auf `/cmd_vel` vor der ersten Probe**), Aufbau mit Christophers Antwort
   wörtlich.
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
5. Urteil: bestätigt, widerlegt, unklar oder gestört, mit den Zahlen beider
   Proben.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes.

Am Ende im Chat nur: Pfad; je Probe das Urteil und `ist_zu_soll` für A, B
(zweite Stufe), C, F (zweite Stufe), D und E; Abbrüche, Berührungen oder
Eingriffe.

## Danach

Auswertung in der Cloud-Sitzung. Bei `bestaetigt` folgt eine Korrektur im
Motortreiber als eigener, getrennt geprüfter Schritt (AGENTS §2.7), danach
dieselbe Probe erneut und dann die Stellprobe. Bei `widerlegt` setzt der
Antrieb saubere Befehle um; dann wird als Nächstes bei einer normalen Fahrt
lückenlos mitgelesen, was an der Basis ankommt. Bei `unklar` oder
`gestoert` zuerst die Daten; kein weiterer Versuch ohne neue Auswertung.
