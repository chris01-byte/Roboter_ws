# Aktueller Agentenauftrag: W-1N – nur lesende Auswertung der beiden Wohnungsfahrten aus W-1

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 15.11.2026 nach
dem Bericht zu W-1 ([Archiv](archive/20261115-w1-ausgewertet/README.md),
STATUS Abschnitt 15.11.2026 spät). **Es wird nichts gestartet und nichts
gefahren.** Gelesen werden nur die vorhandenen Dateien unter `$SH_PR/w1_*`.

**Warum:** Die Stellprobe mit KM-2 war bestanden. Die Wohnungsfahrt kam
zweimal nicht aus dem Laborraum heraus (w1: „Hilfe benötigt“ nach 219 s in
der Tür; w2: nach 19 min 35 s gestoppt, 27 Ziele begonnen, 2 erreicht,
rund 126 rad gedreht, 13 m gefahren). Beobachtung des Projektinhabers zu
w2: Amadeus blieb im Labor, drehte sich unzählige Male im selben Bereich,
fuhr immer wieder dieselben Stellen an, ohne erkennbare Struktur, und kam
nicht aus dem Raum.

Nach MASTERPLAN §9 Regel 4 folgt auf einen nicht bestandenen Realtest
zuerst eine nur lesende Auswertung. Sie soll **messen**, was bisher nur
vermutet ist:

1. Wie viele verschiedene Ziele gab es, wie oft wurde jedes angefahren, und
   lagen die häufigsten an der Tür?
2. Warum endeten Anläufe mit „Goal canceled“ (in w2 14-mal, davon 13 ohne
   Eintrag in der Heilungsliste)? Aus dem Code: Der Explorer bricht einen
   Anlauf ab, wenn eine Quelle fehlt oder der HWT-Pfad „HOLD“ meldet,
   wartet, und wählt danach wieder das beste Ziel, also meist dasselbe. Ob
   das hier so war, steht im Fahrtprotokoll.
3. Worauf hat der Explorer gewartet, wie oft und wie lange?
4. Wann häuften sich die Zeitfehler („extrapolation into the future“, 271),
   und was meldeten die Knoten dabei?
5. Was geschah um die zwei starken Wackelspitzen (w1 bei etwa 134 s in der
   Fahrt, w2 bei etwa 667–670 s im Stand)?
6. Wo begannen die gescheiterten und die abgebrochenen Anläufe, gemessen an
   der Tür, und lagen ihre Ziele hinter der Tür?
7. Wie breit ist die Tür in der gesicherten Karte von w1, wie viel davon
   war für den globalen Planer frei, und wie stand Amadeus darin? (Der
   globale Planer rechnet mit einem Kreis von 0,28 m Radius; in einer
   80-cm-Tür bleibt rechnerisch ein Streifen von rund 0,25–0,30 m.)
8. Warum brach der Explorer in w1 die zweite Rückfahrt nach 2,9 s ab?
   Danach stand Amadeus an einer Stelle, von der der Planer keinen Weg fand.

Dafür gibt es zwei Werkzeuge (nur lesend, ohne ROS):

- `tools/kartierung/selbstheilung_ablauf.py`: Ziele, Anläufe der Reihe nach
  mit Bezug zur Tür, Abbruchgründe, Warte- und HWT-Phasen, Rückfahrten,
  Verlauf je Minute, häufigste Meldungen, Auszüge.
- `tools/kartierung/karte_engstelle.py`: lichte Weite der Tür, für den
  Planer freier Anteil, Lage des Roboters darin, aus der gesicherten Karte
  und den gesicherten Kostenkarten.

Beide geben **keine Koordinaten der Karte** aus: Ziele erscheinen als
laufende Nummern mit Abständen, Zahlen in Meldungen als `#`,
Koordinatenpaare in Auszügen als `(…)`, Lagen nur relativ zum Roboter.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`, im
STATUS die Arbeitsliste und den Abschnitt 15.11.2026 (spät), und die Köpfe
der beiden Werkzeuge.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 15.11.2026; **Fahrplan §9 Regel 4** (nach einem Fehlschlag zuerst Daten) |
| WE-Bezug | WE-M3/WE-M4, Auswertung; keine Abnahme |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `f1694a2`; kein Build, kein Stackstart; Daten aus `selbstheilung-w1-20261115_1801/pruefung` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_w1n.md`: die Ausgaben der Werkzeuge für w1 und w2 wörtlich, dazu Antworten auf die acht Fragen oben, Messwert und Lesart getrennt |
| Nicht-Ziele | keine Fahrt, kein Stackstart, kein Build, keine Code- oder Parameteränderung, keine Korrekturvorschläge im Code |
| Rückfall | nichts zu tun; es wird nichts geändert |
| Laborrahmen | entfällt, es bewegt sich nichts |

## Verboten

- kein Stackstart, keine Mission, kein `topic pub`, kein `param set`, kein
  `service call`, kein `lifecycle set`, kein Build, kein Commit oder Push;
- keine Änderung an Dateien unter `$SH_PR/w1_*` außer neuen Dateien im
  Ordner `$SH_PR/w1n/`; nichts in `~/roboter_ws`; die Werkzeuge nicht ändern;
- keine Karten, Bilder, Bags oder Listen von Zielen mit Koordinaten im
  Bericht (die Ausgaben der Werkzeuge sind frei davon);
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
  git rev-parse HEAD && git merge-base --is-ancestor f1694a2 HEAD && echo "f1694a2 enthalten"
mkdir -p "$SH_PR/w1n"
cd "$SH_SRC/tools/kartierung" && python3 -m pytest -q -p no:cacheprovider \
  test_selbstheilung_ablauf.py test_selbstheilung_anlaeufe.py test_karte_engstelle.py 2>&1 | tail -3
ls -la "$SH_PR/w1_runw1/launch.log" "$SH_PR/w1_runw1/protokoll.json" \
       "$SH_PR/w1_runw2/launch.log" "$SH_PR/w1_runw2/protokoll.json" \
       "$SH_PR/w1_runw1/karte.yaml" "$SH_PR/w1_runw1/karte.pgm" \
       "$SH_PR/w1_runw1/globale_kostenkarte_ende_voll.txt" \
       "$SH_PR/w1_runw1/lokale_kostenkarte_ende_voll.txt" \
       "$SH_PR/w1_runw1/tf_map_base_link.txt" "$SH_PR/w1_runw1/tf_odom_base_link.txt"
```

Erwartet: `SH_PR` endet auf `selbstheilung-w1-20261115_1801/pruefung`,
`22 passed`, alle Dateien vorhanden. Fehlt eine Datei: berichten, mit dem
Rest weitermachen.

## Schritt 2 – Ablaufauswertung für w1 und w2

Die Tür liegt in der Karte von w1 an der Hilfe-Stelle (`map→base_link`
x = 1,974 m, y = −1,046 m, aus dem Bericht zu W-1). w2 hatte eine eigene
Karte; stand Amadeus beim Start am selben Platz und in derselben Richtung,
liegt die Tür dort etwa an derselben Stelle. Das ist eine Annahme und im
Bericht so zu nennen; dazu sagen, ob Startplatz und Richtung in w2 gleich
waren (soweit bekannt).

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

Lesehilfe zur Ausgabe: In „Anläufe der Reihe nach“ ist der Start eines
Anlaufs die Stelle, an der der vorige endete. „Ziel hinter Tür“ ist eine
Näherung in Richtung Startplatz→Tür (positiv = weiter weg als die Tür).

## Schritt 3 – Tür in Karte und Kostenkarten von w1

Punkt und Blickrichtung sind die der Hilfe-Stelle aus dem Bericht zu W-1
(`map→base_link` x 1,974, y −1,046, Gier 43,3°). Die lokale Kostenkarte
liegt im Rahmen `odom` und ist um den Roboter zentriert; dort gilt die
Mitte als Standort und die Gier `odom→base_link` (43,3° − (−0,35°) =
43,65°).

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
cd "$SH_SRC/tools/kartierung"
P="$SH_PR/w1_runw1"
grep -h "RPY (degree)" "$P/tf_map_base_link.txt" | tail -1
grep -h "RPY (degree)" "$P/tf_odom_base_link.txt" | tail -1
python3 karte_engstelle.py --karte "$P/karte.yaml" --punkt 1.974 -1.046 --gier 43.3 \
  --json "$SH_PR/w1n/engstelle_karte.json" > "$SH_PR/w1n/engstelle_karte.txt" 2>&1; echo "karte exit=$?"
python3 karte_engstelle.py --kostenkarte "$P/globale_kostenkarte_ende_voll.txt" \
  --punkt 1.974 -1.046 --gier 43.3 \
  --json "$SH_PR/w1n/engstelle_global.json" > "$SH_PR/w1n/engstelle_global.txt" 2>&1; echo "global exit=$?"
python3 karte_engstelle.py --kostenkarte "$P/lokale_kostenkarte_ende_voll.txt" \
  --mitte --gier 43.65 \
  --json "$SH_PR/w1n/engstelle_lokal.json" > "$SH_PR/w1n/engstelle_lokal.txt" 2>&1; echo "lokal exit=$?"
cat "$SH_PR/w1n"/engstelle_karte.txt "$SH_PR/w1n"/engstelle_global.txt "$SH_PR/w1n"/engstelle_lokal.txt
```

- Weicht die Gier in einer der beiden TF-Dateien um mehr als 1° von 43,3°
  bzw. 43,65° ab: den Aufruf mit dem Wert aus der Datei wiederholen und
  beide Werte berichten.
- Meldet ein Aufruf `FEHLER: …` (Datei in anderem Format, gekürzt, Punkt
  außerhalb): die Meldung wörtlich berichten und die ersten 25 Zeilen der
  Datei ansehen und beschreiben (Feldnamen, keine Zahlenkolonnen). Das
  Werkzeug nicht ändern.
- Meldet die Karte „keine Engstelle gefunden“: den Aufruf einmal mit
  `--umkreis 1.8` wiederholen.

Für w2 gibt es keine gesicherte Karte; dort entfällt dieser Schritt.

## Schritt 4 – gezielte Nachfragen an die Logs (nur lesen)

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
4. **Zweite Rückfahrt in w1:** Nennt die Liste „Rückfahrten“ in
   `ablauf_w1.txt` für die abgebrochene Rückfahrt `kein_warten_im_zeitraum`
   oder `nicht_zuordenbar`, dann die Logzeilen von 3 s vor ihrem Beginn bis
   3 s nach dem Abbruch ansehen und sagen, welcher Knoten abbrach und was
   er dabei meldete.

Koordinatenpaare in zitierten Zeilen durch `(…)` ersetzen.

## Bericht: `~/selbstheilung_jetson_bericht_w1n.md`

1. Kopf: Datum, HEAD, Ergebnis von Schritt 0 und 1.
2. **w1:** `ablauf_w1.txt` wörtlich und vollständig; aus `anlaeufe_w1.txt`
   der Block `zusammenfassung` wörtlich.
3. **w2:** `ablauf_w2.txt` wörtlich und vollständig; aus `anlaeufe_w2.txt`
   der Block `zusammenfassung` wörtlich und die Zeilen je Anlauf.
4. **Tür (w1):** `engstelle_karte.txt`, `engstelle_global.txt` und
   `engstelle_lokal.txt` wörtlich, dazu die zwei Gier-Zeilen aus den
   TF-Dateien.
5. Antworten auf die acht Fragen oben, je Frage zuerst der Messwert (mit
   Fundstelle), dann getrennt die eigene Lesart.
6. Ergebnis von Schritt 4.
7. Auffälligkeiten, Abweichungen und nicht Ausgeführtes.

Am Ende im Chat nur: Pfad; für w2 die Zahl der verschiedenen Ziele, die
Zahl der wiederholten Anläufe, die Abbruchgründe mit Anzahl und die
Wartezeit gesamt; für w1 die lichte Weite der Tür und den für den Planer
freien Anteil (Karte und globale Kostenkarte).

## Danach

Auswertung in der Cloud-Sitzung. Erst mit diesen Zahlen wird entschieden,
was zuerst geändert wird (Türdurchfahrt, Zielwahl, Rechenlast). Kein
weiterer Fahrversuch vorher.
