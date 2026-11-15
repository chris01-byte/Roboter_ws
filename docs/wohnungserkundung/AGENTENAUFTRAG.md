# Aktueller Agentenauftrag: W-1N – nur lesende Auswertung der beiden Wohnungsfahrten aus W-1

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.11.2026 nach
dem Bericht zu W-1 ([Archiv](archive/20261115-w1-ausgewertet/README.md),
STATUS Abschnitt 15.11.2026 spät). **Es wird nichts gestartet und nichts
gefahren.** Gelesen werden nur die vorhandenen Dateien unter `$SH_PR/w1_*`.

**Warum:** Die Stellprobe mit KM-2 war bestanden. Die Wohnungsfahrt kam
zweimal nicht aus dem Laborraum heraus (w1: „Hilfe benötigt“ nach 219 s in
der Tür; w2: nach 19 min 35 s gestoppt, 27 Ziele begonnen, 2 erreicht,
rund 127 rad gedreht, 13 m gefahren). Beobachtung des Projektinhabers zu
w2: Amadeus blieb im Labor, drehte sich unzählige Male im selben Bereich,
fuhr immer wieder dieselben Stellen an, ohne erkennbare Struktur, und kam
nicht aus dem Raum.

Nach MASTERPLAN §9 Regel 4 folgt auf einen nicht bestandenen Realtest
zuerst eine nur lesende Auswertung. Sie soll **messen**, was bisher nur
vermutet ist:

1. Wie viele verschiedene Ziele gab es, wie oft wurde jedes angefahren, und
   lagen die häufigsten an der Tür?
2. Warum endeten Anläufe mit „Goal canceled“ (in w2 14-mal)? Aus dem Code:
   Der Explorer bricht einen Anlauf ab, wenn eine Quelle fehlt oder der
   HWT-Pfad „HOLD“ meldet, wartet, und wählt danach wieder das beste Ziel,
   also meist dasselbe. Ob das hier so war, steht im Fahrtprotokoll.
3. Worauf hat der Explorer gewartet, wie oft und wie lange?
4. Wann häuften sich die Zeitfehler („extrapolation into the future“, 271),
   und was meldeten die Knoten dabei?
5. Was geschah um die zwei starken Wackelspitzen (w1 bei etwa 134 s in der
   Fahrt, w2 bei etwa 667–670 s im Stand)?

Dafür gibt es ein neues Werkzeug, `tools/kartierung/selbstheilung_ablauf.py`
(nur lesend, ohne ROS). Es gibt **keine Koordinaten** aus: Ziele erscheinen
als laufende Nummern mit Abständen, Zahlen in Meldungen als `#`,
Koordinatenpaare in Auszügen als `(…)`.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`, im
STATUS die Arbeitsliste und den Abschnitt 15.11.2026 (spät), und den Kopf
von `tools/kartierung/selbstheilung_ablauf.py`.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 15.11.2026; **Fahrplan §9 Regel 4** (nach einem Fehlschlag zuerst Daten) |
| WE-Bezug | WE-M3/WE-M4, Auswertung; keine Abnahme |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `03a980d`; kein Build, kein Stackstart; Daten aus `selbstheilung-w1-20261115_1801/pruefung` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_w1n.md`: die Ausgaben der zwei Werkzeuge für w1 und w2 wörtlich, dazu Antworten auf die fünf Fragen oben, Messwert und Lesart getrennt |
| Nicht-Ziele | keine Fahrt, kein Stackstart, kein Build, keine Code- oder Parameteränderung, keine Korrekturvorschläge im Code |
| Rückfall | nichts zu tun; es wird nichts geändert |
| Laborrahmen | entfällt, es bewegt sich nichts |

## Verboten

- kein Stackstart, keine Mission, kein `topic pub`, kein `param set`, kein
  `service call`, kein `lifecycle set`, kein Build, kein Commit oder Push;
- keine Änderung an Dateien unter `$SH_PR/w1_*` außer neuen Dateien im
  Ordner `$SH_PR/w1n/`; nichts in `~/roboter_ws`;
- keine Karten, Bilder, Bags oder Listen von Zielen mit Koordinaten im
  Bericht (die Ausgaben der beiden Werkzeuge sind frei davon);
- keine Geheimnisse und keine IP-Adressen im Bericht.

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

Läuft ein Stack, stört das nicht; nichts beenden, nur vermerken.

## Schritt 1 – Klon aktualisieren, Werkzeugtest

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "$SH_SRC $SH_REL $SH_PR"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor 03a980d HEAD && echo "03a980d enthalten"
mkdir -p "$SH_PR/w1n"
cd "$SH_SRC/tools/kartierung" && python3 -m pytest -q -p no:cacheprovider \
  test_selbstheilung_ablauf.py test_selbstheilung_anlaeufe.py 2>&1 | tail -3
ls -la "$SH_PR/w1_runw1/launch.log" "$SH_PR/w1_runw1/protokoll.json" \
       "$SH_PR/w1_runw2/launch.log" "$SH_PR/w1_runw2/protokoll.json"
```

Erwartet: `SH_PR` endet auf `selbstheilung-w1-20261115_1801/pruefung`,
`11 passed`, alle vier Dateien vorhanden. Fehlt eine Datei: berichten, mit
dem Rest weitermachen.

## Schritt 2 – Ablaufauswertung für w1 und w2

Die Tür liegt in der Karte von w1 an der Hilfe-Stelle (`map→base_link`
x = 1,974 m, y = −1,046 m, aus dem Bericht zu W-1). w2 hatte eine eigene
Karte; stand Amadeus beim Start am selben Platz, liegt die Tür dort etwa an
derselben Stelle. Das ist eine Annahme und im Bericht so zu nennen.

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
cd "$SH_SRC/tools/kartierung"
for R in w1 w2; do
  python3 selbstheilung_ablauf.py --log "$SH_PR/w1_run$R/launch.log" \
    --protokoll "$SH_PR/w1_run$R/protokoll.json" --tuer 1.974 -1.046 \
    --json "$SH_PR/w1n/ablauf_$R.json" > "$SH_PR/w1n/ablauf_$R.txt" 2>&1; echo "$R exit=$?"
  python3 selbstheilung_anlaeufe.py "$SH_PR/w1_run$R/launch.log" \
    --json "$SH_PR/w1n/anlaeufe_$R.json" > "$SH_PR/w1n/anlaeufe_$R.txt" 2>&1; echo "$R exit=$?"
  wc -l "$SH_PR/w1n/ablauf_$R.txt" "$SH_PR/w1n/anlaeufe_$R.txt"
done
```

Endet ein Aufruf mit einem Fehler: die Fehlermeldung wörtlich berichten,
das Werkzeug nicht ändern.

## Schritt 3 – drei gezielte Nachfragen an die Logs (nur lesen)

Nur soweit die Werkzeugausgabe sie nicht schon beantwortet:

1. **Wartegründe und HWT:** Zeigt `ablauf_w2.txt` bei „Abbruchgründe“ den
   Eintrag `kein_warten_im_fenster` oder `nicht_zuordenbar` öfter als
   zweimal, dann für drei dieser Abbrüche die Logzeilen von 5 s davor bis
   3 s danach ansehen und sagen, welcher Knoten den Abbruch auslöste.
2. **Fahrtor:** Welche Gründe nennt `cmd_vel_mission_gate` in w2 für
   Sperren, und wie oft je Grund? (Seine Warnungen stehen in der Liste der
   häufigsten Meldungen; falls dort nichts steht:
   `grep -c "cmd_vel_mission_gate" "$SH_PR/w1_runw2/launch.log"` und die
   fünf häufigsten Meldungen dieses Knotens, Zahlen unkenntlich.)
3. **Erste Zeitfehler:** die ersten zehn Zeilen mit „extrapolation into the
   future“ in w2, mit Zeit seit Missionsstart und Knoten; dazu, welche zwei
   Rahmen (`frame`) die Meldung nennt.

Koordinatenpaare in zitierten Zeilen durch `(…)` ersetzen.

## Bericht: `~/selbstheilung_jetson_bericht_w1n.md`

1. Kopf: Datum, HEAD, Ergebnis von Schritt 0 und 1.
2. **w1:** `ablauf_w1.txt` wörtlich und vollständig; aus `anlaeufe_w1.txt`
   der Block `zusammenfassung` wörtlich.
3. **w2:** `ablauf_w2.txt` wörtlich und vollständig; aus `anlaeufe_w2.txt`
   der Block `zusammenfassung` wörtlich und die Zeilen je Anlauf.
4. Antworten auf die fünf Fragen oben, je Frage zuerst der Messwert (mit
   Fundstelle), dann getrennt die eigene Lesart.
5. Ergebnis von Schritt 3.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes.

Am Ende im Chat nur: Pfad; für w2 die Zahl der verschiedenen Ziele, die
Zahl der wiederholten Anläufe, die Abbruchgründe mit Anzahl und die
Wartezeit gesamt.

## Danach

Auswertung in der Cloud-Sitzung. Erst mit diesen Zahlen wird entschieden,
was zuerst geändert wird (Türdurchfahrt, Zielwahl, Rechenlast). Kein
weiterer Fahrversuch vorher.
