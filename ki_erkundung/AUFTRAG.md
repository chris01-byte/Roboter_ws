# Aktueller Auftrag der KI-Linie: KI-F11 – das neue Sehen am Roboter

**Erteilt am 27.11.2026** (Christopher: „Ja los geht es mit KI-F11“). Er
wird aktiv, sobald der Projektinhaber ihn übergibt. Er läuft auf dem
**Jetson**, mit Christopher; auf dem **KI-Rechner** muss das Lotsen-Fenster
(„Amadeus Lotse“) laufen.

**Warum es ihn gibt:** In KI-F9 ist Amadeus einmal nach der Wahl der KI durch
die Labortür gefahren; in Lauf 2 aber wählte die KI ein Fensterrollo, weil
die Vermessung die Tür von einer Scheinlücke verdrängen ließ, zwei Nummern
übereinanderlagen und die KI das Beispiel der Frage abschrieb. Das Sehen ist
seither ohne Roboter repariert (STATUS, „Sehen repariert“), und KI-F9R hat
an den gespeicherten Runden bestätigt: Mit dem neuen Stand hat die Tür in
Lauf 2 eine Nummer, und die KI wählt sie; mit dem alten wiederholte sich der
Fehler. **Jetzt zeigt sich am Roboter, ob das auch im Lauf hält.**

**Neu gegenüber KI-F9 ist genau eines: das neue Sehen** (Plan:
[Bewertung nach KI-F9](BEWERTUNG_KIF9.md) §10, Schritt KI-F11):
- **Vermessung:** keine Lücke mit verkehrten Kanten mehr; fast gleiche Mitten
  bekommen für die KI eine Nummer;
- **Nummern im Bild** verdecken sich nicht mehr;
- **Frage an die KI (Fassung 2):** kein Beispiel zum Abschreiben, erst jede
  Nummer einordnen, dann wählen, Arten „fenster“ und „moebel“, „lieber keine
  Wahl als eine falsche“.

Am Fahren selbst ändert sich nichts: derselbe Erkunder, dieselbe
Schutzkette, kein Build. Das Fahrwerkzeug kann seit Schritt 3 nur
zusätzlich **ablehnen** (durch eine Öffnung mit nur geschätztem zweitem
Pfosten nie direkt), nie zusätzlich fahren. Die Schwächen beim Fahren, die
KI-F9 zeigte (Kostenkarte belegt, Tür nach der Anfahrt nicht
wiedergefunden), sind **nicht** behoben; dafür kommt KI-F10. Deshalb wird
das Sehen (G-1) getrennt vom Fahren (G-2) bewertet. Die Handschritte aus
KI-F9 übernimmt die **Ablaufhilfe** `ki_erkundung/werkzeuge/ki_lauf.py` (in
KI-F9N im Stand erprobt): Sie startet Kamera und Aufnahme, fragt die KI,
baut die Frage an Christopher und fährt nur nach seinem klaren „ja“ zu genau
dieser Wahl.

**Ohne Nahsensoren**, wie vom Projektinhaber am 22.11.2026 entschieden
(`nahsensoren:=false`): Amadeus sieht nichts unter etwa 75 cm Höhe, der
Kollisionsmonitor bremst nicht, und **während einer Etappe sieht er nichts
Neues rechtzeitig, auch nicht in Hüfthöhe** (Bewertung nach KI-F9, §8).
Christopher räumt den Weg frei, bleibt hinter Amadeus und mit einem Schritt
am Not-Aus im Gehäuse.

Die vorigen Aufträge liegen mit Ergebnis im Archiv:
[KI-F9](archiv/20261124-kif9-ki-waehlt/),
[KI-F9N](archiv/20261124-kif9n-im-stand/),
[KI-F9R](archiv/20261127-kif9r-nachrechnen/) (dort auch die Liste aller
früheren).

**Frage dieses Auftrags:** Wählt die KI mit dem neuen Sehen nach dem
Rundblick dreimal von drei Plätzen die Labortür und nie das Fenster, auch
von dem Platz, von dem aus sie in KI-F9 das Fensterrollo wählte? Und wie oft
kommt Amadeus danach in einem Ablauf hindurch?

| | |
|---|---|
| Plan | [Bewertung nach KI-F9](BEWERTUNG_KIF9.md) §10, Schritt KI-F11 („Fenster nie zur Fahrt vorgeschlagen; Tür 3 von 3“), in der mit Christopher am 24.11.2026 vereinbarten Reihenfolge (vor KI-F10); [Konzept](KONZEPT.md) v1.17 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält. **Kein Build:** Release `kif8-20261123_2138` mit `~/roboter_worktrees/kif8.env`, beide unverändert. Unter `src/` hat sich seit `d61453c` nichts geändert; neu sind nur Werkzeuge der KI-Linie (Python, direkt aus der Arbeitskopie) |
| Erwartetes Ergebnis | Bericht `~/ki_erkundung_bericht_kif11.md`: Tests, Vorlauf mit Messen und Belegen, je Lauf Rundblick, Wahl der KI, Frage und Antwort, Fahrt, Meldungen des Erkunders, Kriterien, Christophers Antworten wörtlich |
| Nicht-Ziele | Kein Build; keine eigene Code- oder Parameteränderung; keine Fahrt ohne Christophers Ja zu genau dieser Wahl; keine Fahrt nach Nummer oder Richtung eines Menschen; kein Nav2-Ziel; Kamera nicht während der Fahrt; keine Blattseite (Amadeus steht auf der Seite ohne Türblatt); kein Nachfassen (KI-F10) |
| Rückfall | Nichts Neues am Jetson außer Aufnahmen, Wahl-Dateien, Belegen und Protokollen unter `~/.local/share/amadeus/ki_erkundung/` und `~/ki_trockenlauf_kif11/`. Release und `kif8.env` bleiben unverändert. Der alte Stand des Sehens ist `282ae29` |
| Bereich und Freigabe | Laborraum und, für die Durchfahrt, der Flur unmittelbar hinter der Labortür (vom Projektinhaber am 21.11.2026 verlangt). Ohne Nahsensoren auf Entscheidung des Projektinhabers vom 22.11.2026. Höchstens eine Vorabfrage (LAB-1); dazu je Lauf die Frage nach dem Ja zur Wahl der KI (Entscheidung des Projektinhabers vom 23.11.2026). Christopher ist dabei, mit einem Schritt am Not-Aus. 100 ms Anfahrzeit wie seit dem 15.11. |

## Christophers Platz (gilt in jedem Lauf)

Der Not-Aus sitzt im Gehäuse. Christopher steht deshalb **hinter oder neben
Amadeus auf der Seite, die von der Tür abgewandt ist, gleich außerhalb seines
Drehkreises (etwa 0,5 m vom Gehäuse), so dass er den Not-Aus mit einem
Schritt erreicht; nie zwischen Amadeus und der Tür oder dem Fenster**, nie
neben ihm auf der Türseite, nie vor ihm. **In Lauf 2** (dort liegt das
Fenster hinter Amadeus) steht er **rechts neben ihm, etwa auf Höhe seiner
Mitte**. Dort steht er beim Rundblick (still, solange Amadeus sich dreht) und
schon, bevor er „ja“ schreibt; nach dem Ja folgt er ihm bei der Fahrt von
hinten. Grund: In KI-F9 (2w2) stand etwas in Hüfthöhe 1,9 m neben Amadeus,
lag als belegt in der Kostenkarte und hielt die Fahrt auf; ein Mensch passt
dazu. Der Stopp in der App ist eine zusätzliche Möglichkeit, kein Ersatz für
den Not-Aus.

## Fragen an Christopher – nur diese

Gefragt wird als Text, einzeln, ohne Auswahlfeld; Antworten wörtlich in den
Bericht.

1. **Vorab, genau einmal (F0)**, in Schritt 3, wörtlich:

   > „Heute wählt die KI die Tür mit dem neuen Sehen, dreimal von drei
   > Plätzen. Zuerst ein Vorlauf ohne Motoren: Amadeus steht dabei 1,5 bis
   > 3 m vor der Labortür auf der Seite ohne Türblatt, **mit Blick zur
   > Tür**; die KI wählt im Stand, und ich messe nur. Von diesem Platz aus
   > startet auch Lauf 1. In jedem Lauf dreht sich Amadeus zuerst einmal
   > ganz um sich selbst (etwa anderthalb Minuten), die Kamera nimmt dabei
   > Bilder auf, und die KI auf dem KI-Rechner sagt, welche Öffnung der
   > Ausgang ist. Ich zeige dir ihre Wahl und frage dich, ob er dorthin
   > fahren soll; nur nach deinem ‚ja' fährt er, in einem Ablauf wie
   > zuletzt, und bleibt knapp einen halben Meter hinter der Tür im Flur
   > stehen. **Dein Platz, in jedem Lauf:** hinter oder neben ihm auf der
   > Seite weg von der Tür, gleich außerhalb seines Drehkreises (etwa 0,5 m
   > vom Gehäuse), so dass du den Not-Aus im Gehäuse mit einem Schritt
   > erreichst, aber nie zwischen ihm und der Tür oder dem Fenster (in
   > Lauf 2 sage ich dir den Platz genau); still, solange er sich dreht;
   > dort stehst du auch schon, bevor du ‚ja' schreibst, und bei der Fahrt
   > folgst du ihm von hinten, nie neben ihm auf der Türseite und nie vor
   > ihm. Er fährt **ohne
   > Nahsensoren**: Was niedriger als etwa 75 cm ist (Kisten, Taschen,
   > Kabel, Schuhe, Türstopper), sieht er nicht, und der Kollisionsmonitor
   > bremst nicht. **Auch was höher ist, sieht er während einer Etappe nicht
   > neu: Tritt jemand, auch du, während der Fahrt vor ihn, hält ihn nur der
   > Not-Aus.** Ist alles aufgebaut: auf dem KI-Rechner ‚Amadeus Lotse'
   > geöffnet, die Labortür ganz offen, im Laborraum, in der Tür und im Flur
   > bis gut einen Meter dahinter nichts Niedriges am Boden, nichts auf
   > Amadeus, der Arm in Transportstellung, Amadeus wie oben mit Blick zur
   > Tür, rundherum mindestens 50 cm frei zum Drehen? Wenn du ‚ja'
   > schreibst, starte ich; danach frage ich dich nur noch nach jeder Wahl
   > der KI und nach jedem Lauf.“

   Nur nach „ja“ weiter. Das „ja“ gilt auch als Bestätigung, dass Amadeus
   beim ersten Start stillsteht (`operator_stationary_confirmed:=true`).
2. **Je Lauf die Frage zur Wahl der KI (F-Wahl):** genau der Text, den
   `ki_lauf.py wahl` unter „FRAGE AN CHRISTOPHER (wörtlich weitergeben)“
   ausgibt, mit der Restzeit. Nur sie gibt die Fahrt frei.
3. **Nach jedem Lauf genau eine Nachricht (F-Lauf)**, siehe „Lauf k“,
   Schritt 9. Fehlt in seiner Antwort eine der dort erbetenen Angaben, darf
   **genau einmal** nur nach den fehlenden gefragt werden.
4. **Nur in den Ausnahmen**, die unten ausdrücklich stehen (Lotsen-Dienst
   nicht bereit, im Vorlauf keine Wahl, Motorregler antworten nicht).

Keine weitere Frage, keine Frage nach freien Motoren, keine Bestätigung
unveränderter Laborbedingungen.

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push, **kein
  Build**;
- **jeder Stackstart dieses Auftrags mit `initial_scan_only:=true
  stage_drive_only:=true nahsensoren:=false`**, keiner ohne; **kein
  Stackstart, solange `roboterknoten.py --still` nicht bestanden ist** (die
  Startblöcke prüfen das selbst);
- schreibend nur: die Stackstarts, **je Lauf genau ein** Missionsstart und
  `ki_lauf.py` genau so, wie es hier steht; kein `param set`,
  `lifecycle set`, `service call`, kein weiteres `topic pub`, keine
  Nav2-Ziele, kein Missionsstopp außer genau einem `cancel` unter
  „Abbruch“;
- **kein Missionsstart, wenn `initial_scan_only` oder `stage_drive_only`
  nicht nachweislich `True` ist**, oder bevor `ki_lauf.py start` „Jetzt
  genau einmal die Mission starten“ gemeldet hat;
- **`fahrziel_senden.py` nie direkt aufrufen.** Gefahren wird nur über
  `ki_lauf.py antwort` mit Christophers Wortlaut; `ki_lauf.py messen` nur im
  Vorlauf (es sendet nichts);
- Christophers Antwort wörtlich an `--wortlaut` geben, nie umformuliert
  oder zu „ja“ ergänzt;
- Christopher stellt Amadeus nur zwischen den Läufen um, nie während eines
  Laufs;
- die Kamera läuft nur während des Rundblicks, nie während der Fahrt (die
  Ablaufhilfe prüft das);
- kein Start mit Motorfreigabe (`active_drive:=true`) ohne
  `hwt601_accel_ms:=100`;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws`, nichts an Umgebungsdateien und Releases;
- Signale nur als **genau ein** SIGINT an eine einzelne, geprüfte PID; keine
  Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- kein eigenes Anzeigeprogramm, nichts im Vollbild;
- **keine Bilder, Scans, Karten, Koordinaten oder Adressen im Chat oder im
  Bericht; Wahl-Dateien und Belege nie anzeigen** (sie enthalten
  Koordinaten). Erlaubt sind die Zeilen der Werkzeuge mit Maßen vom Roboter
  aus.

## Vorab festgelegte Kriterien

„Kette“ heißt: `Begin navigating` 0-mal, „Direkter Explore-Befehl verworfen“
0-mal, „Odometrie kurzzeitig nicht frisch“ 0-mal, „process has died“ 0-mal,
„Interner Explorer-Fehler“ 0-mal, „Logger severity“ 0-mal (jeweils in
`zaehler.txt`, also zwischen Stackstart und dem Sichern des Laufs).

**Voraussetzungen** (sonst keine Läufe):

| Kennung | Kriterium |
|---|---|
| T-1 Tests | Tests der KI-Linie unter Humble: `0 failed` (in KI-F9R: 433 bestanden) |
| U-1 Umgebungen | `ki_lauf.py pruefe-umgebung`: „Umgebungen passen.“ |
| V-0 Stillstand belegt | im Vorlauf `vorpruefung.txt`: eine Zeile `[OK  ]` mit „kein Motorschreiber (HWT-Weg ohne active_drive)“ und eine Zeile `[OK  ]` mit „ohne Fahrbefehl“ |
| V-1 Ablaufhilfe im Stand | am letzten Vorlauf (`v2`, falls gelaufen): `start --nur-stand` mit `BEREIT`, `bilder_hz` mindestens 1,8, und „Aufnahme im Stand läuft“; `wahl` ohne „Lage in der Karte fehlt“, „keine Runde“, „Aufnahme abgebrochen“ und ohne `rc=3`, `rc=5`, `rc=6` (also eine Wahl mit Kennung, „Keine Wahl der KI (rc=2)“ oder `rc=4` mit „Keine Öffnung vermessen“); `antwort … nein`: „keine Wahl, zu der eine Antwort passen könnte“; `aufraeumen`: „Alles beendet.“; in `signale.json` genau eine PID. Das Umstellen vor `v2` zählt nicht als Bewegung |

**Vorlauf, ohne die Läufe aufzuhalten:**

| Kennung | Kriterium |
|---|---|
| B-1 Messen und Belege | `wahl`: „Vorlauf im Stand: Wahl der KI mit Kennung …“; `messen`: „Zur Wahl der KI passt Öffnung N“ und „Nur gemessen, nichts gesendet“; danach ein Belege-Ordner mehr als vorher, mit mindestens einer `messung_N.json` (in KI-F9N nicht prüfbar) |

**Je Lauf (k = 1, 2, 3):**

| Kennung | Kriterium |
|---|---|
| N-1 Ohne Nahsensoren | in `schalter.txt`: `vl53_near_field-Knoten: 0`, `require_near_field` `False`, „Testbetrieb im Log“ mindestens 2; in `zaehler.txt` „Robot to slowdown“ und „Robot to approach“ je 0 |
| R-1 Rundblick | in `etappen.txt` „Etappenfahrt: Rundblick vollstaendig, X Grad“ mit X mindestens 355; danach in der Zeile `Aufnahme: ERGEBNIS …` von `wahl` `grund=wartephase` (die Aufnahme setzt das nur, wenn der Erkunder auf das Fahrziel wartet) |
| W-1 Aufnahme | in derselben Zeile `lage=ja` und `verworfen` höchstens ein Zehntel von `aufnahmen`; dazu „Kamera und Aufnahme beendet.“ |
| W-2 Wahl der KI | eine Wahl mit Kennung, die Antwort der KI in höchstens 120 s; die gewählte Nummer ist die Labortür: nach „ja“ ohne weitere Angabe, sonst laut Christophers Angabe in F-Lauf |
| W-3 Übergabe | in `l<k>_fahrt.txt` „Zur Wahl der KI passt Öffnung N (die Mitten liegen X m auseinander)“ mit X höchstens 0,40; „Türachse aus der Wand neben der Tür“; „Entscheidung: Durchfahrt“ oder „Entscheidung: Anfahrt“ |
| T-2 Abschluss | „Durchfahrt abgeschlossen.“ und `LAUF ergebnis=durchfahrt werkzeug_rc=0` in `l<k>_fahrt.txt`; in `etappen.txt` „Etappenfahrt abgeschlossen: … Quelle ki …; kein Nav2-Ziel“ |
| T-3 Ausrichten | in `etappen.txt` je Punkt höchstens drei Zeilen „ausgerichtet um …“; der jeweils letzte „Restfehler“ höchstens 3,5 Grad |
| T-4 Durch die Tür | Christopher (F-Lauf): im Flur ja, berührt nein (auch beim Drehen), eingegriffen nein |
| T-6 Kette | wie oben |
| P-2 Fensterplatz (nur Lauf 2) | Christopher nennt in F-Lauf, welche Nummer im Lotsen-Fenster die Labortür war und ob und mit welcher Nummer das Fenster dort stand, dazu das Rollo; die Zeile der Türnummer in `l2_wahl.txt` liegt in 1,8 bis 2,8 m und 15° bis 50° links. Stand Christopher beim Rundblick in der Linie zum Fenster, ist P-2 (und S-2 für Lauf 2) „nicht beurteilbar“ |

**Gesamt (für W-2 und die Kriterien „je Lauf“ zählen die ersten Versuche der
Läufe 1, 2 und 3; Wiederholungen werden je für sich bewertet und berichtet,
ersetzen aber keinen Lauf; S-2 gilt für alle Versuche):**

| Kennung | Kriterium |
|---|---|
| S-2 Fenster nie gewählt | in keinem Versuch, **auch nicht in einer Wiederholung**, eine Wahl der KI, die Christopher als Fenster nennt. Beurteilt nur aus Christophers Angaben: nach „ja“ war die Wahl die Tür; nach jeder anderen Antwort aus seiner Angabe in F-Lauf, was die gewählte Nummer wirklich war. Fehlt die Angabe: „nicht beurteilbar“ |
| S-1 Einspruch wirkt | nur falls Christopher nicht „ja“ sagt: Amadeus bleibt stehen, `LAUF ergebnis=nicht_gefahren grund=kein_ja` |
| **G-1 Sehen** (Bewertung §10) | in allen drei Läufen R-1, W-1 und W-2, dazu S-2 („Tür 3 von 3, Fenster nie“) |
| **G-2 Fahren** | in allen drei Läufen W-3, T-2, T-3, T-4 und T-6. Für jeden Lauf ohne Durchfahrt wird der Grund aus `l<k>_fahrt.txt` festgehalten (zum Beispiel Wiederfinden, Kostenkarte, Aufstellung, Lot); das geht in KI-F10 ein |

Eine nicht beurteilbare Angabe zählt als „trifft nicht zu“.

---

## Schritt 0 – Bestand

```bash
date -Iseconds
python3 ~/roboter_worktrees/selbstheilung-v2/tools/kartierung/roboterknoten.py; echo "exit=$?"
ls -d ~/.local/share/amadeus/releases/kif8-20261123_2138 ~/roboter_worktrees/kif8.env ~/ki_trockenlauf_ki0/umgebung_we1.bash
ls -d ~/ki_trockenlauf_kif11 2>/dev/null && echo "KIF11-ORDNER GIBT ES SCHON"
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.
Fehlt eines der drei Dinge der `ls`-Zeile: berichten, Ende. Gibt es
`~/ki_trockenlauf_kif11` schon: nicht löschen, berichten, Ende.

## Schritt 1 – Stand holen (kein Build)

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && git rev-parse HEAD
echo "src-Aenderungen: $(git diff --name-only d61453c HEAD -- src/ | wc -l)"
source ~/roboter_worktrees/kif8.env; echo "rc=$?"; echo "$SH_SRC $SH_REL $SH_PR"
mkdir -p "$SH_PR/kif11"
```

Erwartet: `src-Aenderungen: 0`, `rc=0`, `SH_REL` endet auf
`kif8-20261123_2138`. Sonst: nichts starten, berichten. **Jeder ROS-Befehl
der ersten Shell beginnt mit `source ~/roboter_worktrees/kif8.env`.** Die
Ablaufhilfe lädt ihre Umgebungen selbst.

## Schritt 2 – Tests der KI-Linie (unter Humble)

```bash
cd ~/roboter_worktrees/selbstheilung-v2; source ~/roboter_worktrees/kif8.env
( source /opt/ros/humble/setup.bash; env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3 ) | tee "$SH_PR/kif11/tests.txt"
cd ~/roboter_worktrees/selbstheilung-v2; python3 ki_erkundung/werkzeuge/ki_lauf.py pruefe-umgebung 2>&1 | tee "$SH_PR/kif11/umgebung.txt"
```

Erwartung T-1 und U-1. Sonst: nichts starten, berichten, Ende.

## Schritt 3 – die eine Frage (F0)

Christopher F0 stellen (Wortlaut oben). Nur nach „ja“ weiter.

## Schritt 4 – Vorlauf ohne Motorfreigabe, mit Blick zur Tür

Prüft im Stand, nachweislich ohne Motorschreiber (LAB-1 §3), die Kette bis
zur Wahl und dazu `messen` und die Belege. Amadeus bewegt sich nicht.

```bash
source ~/roboter_worktrees/kif8.env
D="$SH_PR/kif11/vorlauf"; mkdir -p "$D"
if python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still; then
  nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
    self_healing:=true start_web_gui:=false \
    use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
    initial_scan_only:=true stage_drive_only:=true nahsensoren:=false \
    > "$D/launch.log" 2>&1 < /dev/null &
  echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds
else
  echo "STACK LAEUFT SCHON - nichts gestartet"
fi
```

Steht „STACK LAEUFT SCHON“: nichts weiter, berichten, Ende. Nach etwa 70 s:

```bash
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif11/vorlauf"; L="$D/launch.log"
{ ros2 param get /explore_node initial_scan_only 2>&1
  ros2 param get /explore_node stage_drive_only 2>&1
  ros2 param get /explore_node stage_drive_target_wait_s 2>&1
  echo "Traceback: $(grep -c Traceback "$L")"; } | tee "$D/pruefung.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 \
  --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"
grep -E "kein Motorschreiber|ohne Fahrbefehl" "$D/vorpruefung.txt"
source ~/ki_trockenlauf_ki0/umgebung_we1.bash; mkdir -p ~/ki_trockenlauf_kif11
timeout 15 ros2 topic echo --once --full-length /ki_erkundung/lotse_status_json > ~/ki_trockenlauf_kif11/lotse_status.txt 2>&1
grep -o '"bereit": [a-z]*' ~/ki_trockenlauf_kif11/lotse_status.txt
```

Erwartet: `True`, `True`, `420.0`, `Traceback: 0`; V-0 (beide Zeilen mit
`[OK  ]`; andere Zeilen des Prüfskripts werden nur berichtet);
`"bereit": true`. **Weicht eine dieser Zeilen ab: Stack beenden (letzter
Block dieses Schritts), berichten, Ende.**

**Lotsen-Dienst nicht bereit (Ausnahme):** Christopher einmal bitten: „Bitte
öffne auf dem KI-Rechner ‚Amadeus Lotse' und schreib ‚fertig'.“ Danach diese
drei Zeilen wiederholen:

```bash
source ~/ki_trockenlauf_ki0/umgebung_we1.bash
timeout 15 ros2 topic echo --once --full-length /ki_erkundung/lotse_status_json > ~/ki_trockenlauf_kif11/lotse_status.txt 2>&1
grep -o '"bereit": [a-z]*' ~/ki_trockenlauf_kif11/lotse_status.txt
```

Ist er dann nicht bereit: Stack beenden, berichten, Ende.

Dann die Ablaufhilfe im Stand:

```bash
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
ls ~/.local/share/amadeus/ki_erkundung/belege/ 2>/dev/null | wc -l > "$O/belege_vorher.txt"
$H start --auftrag kif11 --lauf v1 --nur-stand 2>&1 | tee "$O/v1_start.txt"; echo "rc=${PIPESTATUS[0]}"
$H wahl --auftrag kif11 --lauf v1 2>&1 | grep -v "^Wahl-Datei" | tee "$O/v1_wahl.txt"; echo "rc=${PIPESTATUS[0]}"
```

Gibt `wahl` `rc=10` („Läuft noch“): die `wahl`-Zeile noch einmal (höchstens
dreimal, mit `tee -a`). Hat `wahl` eine Wahl mit Kennung gemeldet (`rc=0`):

```bash
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
$H messen --auftrag kif11 --lauf v1 2>&1 | tee "$O/v1_messen.txt"; echo "rc=${PIPESTATUS[0]}"
echo "Belege-Ordner vorher $(cat "$O/belege_vorher.txt"), nachher $(ls ~/.local/share/amadeus/ki_erkundung/belege/ | wc -l)"
ls "$(ls -td ~/.local/share/amadeus/ki_erkundung/belege/*/ | head -1)"
```

In jedem Fall danach:

```bash
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
K=$(python3 -c "import json; print((json.load(open('$O/laufv1/zustand.json')).get('wahl') or {}).get('kennung') or 'abcdef')")
$H antwort --auftrag kif11 --lauf v1 --kennung "$K" --wortlaut "nein" 2>&1 | tee "$O/v1_antwort.txt"; echo "rc=${PIPESTATUS[0]}"
$H aufraeumen --auftrag kif11 --lauf v1 2>&1 | tee "$O/v1_aufraeumen.txt"
cat "$O/laufv1/signale.json"; tail -5 "$O/laufv1/ablauf.log"
```

`antwort` muss ablehnen, weil ein Vorlauf keine Frage hat; es ruft dabei
nichts auf.

**Im Vorlauf keine Wahl (Ausnahme):** nur, wenn `wahl` „Keine Wahl der KI
(rc=2)“ meldet oder `rc=4` mit „Keine Öffnung vermessen“. Dann Christopher
einmal sagen: „Im Vorlauf hat die KI die Tür nicht gewählt. Stell Amadeus
bitte etwa 2 m genau vor die Labortür, mit Blick zur Tür, und schreib
‚fertig', wenn er still steht.“ Danach **genau einmal** derselbe Vorlauf ab
„Dann die Ablaufhilfe im Stand“ mit `v2` statt `v1` in allen Zeilen und
Dateinamen, im selben Stack. Lauf 1 startet dann an diesem Platz. Bei jeder
anderen Meldung ohne Wahl („Lage in der Karte fehlt“, „keine Runde“,
„Aufnahme abgebrochen“, `rc` 3, 5 oder 6): Stack beenden, berichten, Ende.

Dann den Stack beenden:

```bash
source ~/roboter_worktrees/kif8.env; kill -INT "$(cat "$SH_PR/kif11/vorlauf/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

Fehlt „alles beendet“: kein zweites Signal, nichts mehr starten, berichten,
Ende. **Trifft V-0 oder V-1 nicht zu: keine Läufe, berichten, Ende.** B-1
allein hält die Läufe nicht auf.

---

## Lauf k (k = 1, 2, 3)

Für jeden Lauf dieselben Schritte; Dateien unter `$SH_PR/kif11/lauf$k` und
`~/ki_trockenlauf_kif11/lauf$k`. Lauf 1 startet am Platz des Vorlaufs.
Vor Lauf 2 und 3 hat Christopher „weiter“ geschrieben (Schritt 9). **Die
Nummer des Laufs steht in einer Datei**, weil jeder Block in einer eigenen
Shell läuft; jeder Block liest sie in seiner ersten Zeile.

### 1 – scharfer Start (erste Shell)

```bash
echo 1 > ~/ki_trockenlauf_kif11/aktueller_lauf     # 2, 3 oder 1w … im jeweiligen Lauf
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf); source ~/roboter_worktrees/kif8.env
D="$SH_PR/kif11/lauf$k"; mkdir -p "$D"
if [ -e "$D/launch.pid" ]; then
  echo "LAUF $k HAT SCHON EINEN START - nichts gestartet"
elif python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still; then
  nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
    self_healing:=true start_web_gui:=false \
    use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
    active_drive:=true enable_auto_explore:=true \
    hwt601_accel_ms:=100 \
    initial_scan_only:=true stage_drive_only:=true nahsensoren:=false \
    > "$D/launch.log" 2>&1 < /dev/null &
  echo $! > "$D/launch.pid"; cat "$D/launch.pid"; date -Iseconds > "$D/launch_start.txt"
else
  echo "STACK LAEUFT SCHON - nichts gestartet"
fi
```

Steht „STACK LAEUFT SCHON“ oder „HAT SCHON EINEN START“ (die erste Zeile
nicht angepasst): nichts weiter, berichten, Ende.

### 2 – Prüfungen (nach etwa 70 s, ohne Frage)

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf); source ~/roboter_worktrees/kif8.env
D="$SH_PR/kif11/lauf$k"; L="$D/launch.log"
grep -n "Anfahrverhalten bestaetigt" "$L" | tee "$D/anfahrzeit.txt"
{ ros2 param get /explore_node initial_scan_only 2>&1
  ros2 param get /explore_node stage_drive_only 2>&1
  echo "vl53_near_field-Knoten: $(ros2 node list --no-daemon --spin-time 3 2>/dev/null | grep -c vl53_near_field)"
  ros2 param get /cmd_vel_mission_gate require_near_field 2>&1
  echo "Testbetrieb im Log: $(grep -c 'TESTBETRIEB OHNE NAHSENSOREN' "$L")"; } | tee "$D/schalter.txt"
python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$D/vorpruefung.json" > "$D/vorpruefung.txt" 2>&1; echo "exit=$?"; tail -40 "$D/vorpruefung.txt"
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm`;
`True`, `True`, `vl53_near_field-Knoten: 0`, `False`, `Testbetrieb im Log:`
mindestens `2`; Prüfskript Exit 0 (die Prüfung der Eigenechos entfällt, sie
gilt den Nahsensoren). **Trifft etwas nicht zu (nach einer Wiederholung bei
„erreichbar“, „nicht deklariert“, „Graph unvollständig“): keine Mission,
Stack geordnet beenden (Schritt 8), berichten, Ende.**

**Radsensor beim Start gesperrt (Ausnahme, ohne Frage):** wie in KI-F9: Die
Zeile zur Anfahrzeit ist da, „Modbus-Fehler“ steht 0-mal im Log, und die
Vorprüfung fällt **nur** im Bereich „D Quellen“ durch. Dann:

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf); source ~/roboter_worktrees/kif8.env
D="$SH_PR/kif11/lauf$k"
uptime | tee "$D/last_bei_sperre.txt"
python3 "$SH_SRC/ki_erkundung/werkzeuge/radsensor_zustand.py" 2>&1 | tee "$D/radsensor.txt"
kill -INT "$(cat "$D/launch.pid")"; sleep 15
if python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still; then echo "alles beendet"
  for f in launch.log launch.pid launch_start.txt anfahrzeit.txt schalter.txt vorpruefung.json vorpruefung.txt; do \
    [ -e "$D/$f" ] && mv "$D/$f" "$D/erster_start_$f"; done
fi
```

**Fehlt „alles beendet“: kein zweites Signal, nichts mehr starten,
berichten, Ende.** Sonst Christopher dazu nur sagen (keine Frage): „Der
Radsensor hat sich beim Hochfahren gesperrt; ich starte einmal neu, Amadeus
fährt dabei nicht.“ Mindestens 30 s nach „alles beendet“ **genau ein**
weiterer Start (Schritt 1 ohne die erste Zeile, dann 2). Sperrt er sich
wieder: Schritt 8, berichten, Ende.

**Motorregler antworten nicht (Ausnahme):** Fehlt die Zeile zur Anfahrzeit
und steht im Log „Modbus-Fehler Motor … No response received“: den Block der
Ausnahme „Radsensor“ ab `kill -INT` ausführen (ohne `radsensor_zustand.py`)
und Christopher sagen: „Die Motorregler antworten nicht; so kann ich nicht
starten.“ Sagt er, die Motoren seien frei, ist mindestens 30 s nach „alles
beendet“ **genau ein** weiterer Start erlaubt (Schritt 1 ohne die erste
Zeile, dann 2); sonst berichten, Ende.

### 3 – Kamera und Aufnahme starten (Ablaufhilfe)

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf)
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
$H start --auftrag kif11 --lauf "$k" --tuer "die Labortür" 2>&1 | tee "$O/l${k}_start.txt"; echo "rc=${PIPESTATUS[0]}"
```

Erwartet: `BEREIT … bilder_hz` mindestens 1,8 `… erkunder=ja` und „Aufnahme
läuft und endet von selbst 5 s nach dem Rundblick. Jetzt genau einmal die
Mission starten.“ **Sonst keine Mission:** Schritt 7 und 8, keine weiteren
Läufe, Bericht.

### 4 – Mission starten: erst der Rundblick (erste Shell)

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf); source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif11/lauf$k"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$D/missionsstart.txt"
```

Amadeus dreht sich einmal ganz herum und bleibt stehen; Christopher steht
dabei still an seinem Platz (oben). **Christopher drückt den Not-Aus, bevor
etwas berührt wird:** wenn Amadeus beim Rundblick **fährt** (vor oder
zurück, auch nur ein kurzes Stück), wenn eine Ecke beim Drehen näher als zwei
Finger breit an etwas herankommt, bei ungewöhnlichem Geräusch oder starkem
Schwanken.

### 5 – Wahl der KI abwarten und Christopher fragen (F-Wahl)

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf)
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
$H wahl --auftrag kif11 --lauf "$k" 2>&1 | grep -v "^Wahl-Datei" | tee -a "$O/l${k}_wahl.txt"; echo "rc=${PIPESTATUS[0]}"
```

- **`rc=10` mit „Läuft noch“:** dieselbe Zeile sofort noch einmal, so oft wie
  nötig (die Ablaufhilfe wartet je Aufruf bis 100 s und bricht nach 300 s
  ohne Wartephase selbst ab).
- **`rc=10` mit „Kamera oder Aufnahme laufen noch“:** nach 10 s noch einmal;
  steht das dreimal da: Schritt 7 und 8, nicht fahren, berichten, keine
  weiteren Läufe.
- **„FRAGE AN CHRISTOPHER (wörtlich weitergeben)“:** den Text darunter
  **sofort und wörtlich** an Christopher (ohne Pfade), nichts hinzufügen
  außer der Lauf-Nummer.
- **„noch keine Wartephase“ (`grund=keine_wartephase`, `rc=4`) oder „Die KI
  wird nicht gefragt“ mit einem anderen `grund=` als `wartephase` in der
  Zeile `Aufnahme: ERGEBNIS …` (auch „kein Rundblick bis zur
  Wartephase“):** Der Rundblick ist nicht ordentlich zu Ende gekommen, und
  die Ablaufhilfe hat nichts gesendet. Weiter unter „Abbruch“, zweiter Punkt
  (einmal `cancel`), keine weiteren Läufe.
- **„Keine Wahl der KI“, oder „Die KI wird nicht gefragt“ mit
  `grund=wartephase`:** keine Frage; die Ablaufhilfe hat dem wartenden
  Erkunder das „Ende“ gesagt (Zeilen dazu stehen in der Ausgabe). Weiter mit
  Schritt 7.
- **„Keine Frage an den Menschen“** (zu spät für eine Antwort): keine Frage,
  nichts gesendet; der Erkunder schließt nach seiner Frist selbst, ohne zu
  fahren. Weiter mit Schritt 7.

### 6 – Christophers Antwort eintragen und die Fahrt verfolgen

Christophers Antwort **wörtlich** eintragen; die Kennung steht in der
Ausgabe von `wahl`:

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf)
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
$H antwort --auftrag kif11 --lauf "$k" --kennung KENNUNG --wortlaut "SEINE ANTWORT" 2>&1 | tee -a "$O/l${k}_fahrt.txt"; echo "rc=${PIPESTATUS[0]}"
```

`KENNUNG` und `SEINE ANTWORT` sind Platzhalter. Nur ein klares „ja“ startet
die Fahrt; alles andere sagt dem Erkunder das „Ende“. Gibt `antwort` `rc=10`
(„Die Fahrt läuft noch; weiter mit: verfolgen“):

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf)
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
$H verfolgen --auftrag kif11 --lauf "$k" 2>&1 | tee -a "$O/l${k}_fahrt.txt"; echo "rc=${PIPESTATUS[0]}"
```

so oft wie nötig, bis eine Zeile `LAUF ergebnis=…` kommt. **Kein zweiter
Missionsstart, kein Stopp von Hand.**

**Christopher drückt den Not-Aus (oder den Stopp in der App), bevor etwas
berührt wird,** und sofort, wenn doch etwas Niedriges in den Weg gerät oder
jemand den Weg kreuzt; ohne Nahsensoren hält Amadeus davor nicht von selbst
an. Drehen auf der Stelle, kurzes Stehenbleiben zwischen den Etappen und
vor der Durchfahrt (Neumessung), kleines Nachstellen der Richtung und
langsames Kriechen neben dem Türblatt sind gewollt.

### 7 – aufräumen und sichern (Amadeus steht, der Stack läuft noch)

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf)
cd ~/roboter_worktrees/selbstheilung-v2; H="python3 ki_erkundung/werkzeuge/ki_lauf.py"; O=~/ki_trockenlauf_kif11
$H aufraeumen --auftrag kif11 --lauf "$k" 2>&1 | tee "$O/l${k}_aufraeumen.txt"
source ~/roboter_worktrees/kif8.env; D="$SH_PR/kif11/lauf$k"
date -Iseconds > "$D/ende.txt"
grep -n "Etappenfahrt\|Fahrziel\|Mission beendet" "$D/launch.log" | tee "$D/etappen.txt"
for m in "Begin navigating" "Direkter Explore-Befehl verworfen" "Explore-Rundblickbefehl verworfen" \
  "Odometrie kurzzeitig nicht frisch" "Robot to slowdown" "Robot to approach" "detected collision ahead" \
  "Unabhaengiger LiDAR-Scan kurzzeitig nicht" "LiDAR-Bewegungsmessung nicht eindeutig" "process has died" \
  "Interner Explorer-Fehler" "Logger severity"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
```

Dazu aus den Sekundenzeilen von `base_hardware` zwischen Missionsstart und
Ende: größtes |v| und |w|. Erwartet nach `aufraeumen`: „Alles beendet.“;
sonst kein zweites Signal, Schritt 8, keine weiteren Läufe, Bericht. (Kam die Ablaufhilfe in diesem Lauf
nicht zum Start, meldet `aufraeumen` das; das ist kein Fehler.)

### 8 – Stack geordnet beenden

```bash
k=$(cat ~/ki_trockenlauf_kif11/aktueller_lauf); source ~/roboter_worktrees/kif8.env
kill -INT "$(cat "$SH_PR/kif11/lauf$k/launch.pid")"; sleep 15
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still && echo "alles beendet"
```

**Fehlt „alles beendet“: kein zweites Signal, nichts mehr starten,
berichten, Ende.** Ein weiterer Lauf beginnt nur nach „alles beendet“.

### 9 – eine Nachricht an Christopher (F-Lauf)

Ein Satz zum Ergebnis aus `l${k}_fahrt.txt` (zum Beispiel „Lauf 1:
Rundblick 362°, die KI wählte Nr. 1 (offene Tür), Anfahrt 1,4 m, dann
Durchfahrt 2,1 m, ‚Durchfahrt abgeschlossen'.“), dann **eine** Bitte mit
allen Angaben, die gebraucht werden. Welcher Fall gilt, steht in
`l${k}_fahrt.txt`:

- **Hindurchgefahren** („Durchfahrt abgeschlossen.“): „Bitte antworte in
  einer Nachricht: Steht er ganz im Flur (ja/nein)? Hat er etwas berührt,
  beim Fahren oder Drehen (ja/nein)? Musstest du eingreifen – Not-Aus,
  App-Stopp oder angefasst (ja/nein)? Wo standest du beim Rundblick?“
- **Gefahren, aber nicht hindurch** (eine Zeile „Fahrziel gesendet“, aber
  kein „Durchfahrt abgeschlossen.“): „Er ist ein Stück gefahren, aber nicht
  hindurch. Bitte antworte in einer Nachricht: Hat er etwas berührt, beim
  Fahren oder Drehen (ja/nein)? Musstest du eingreifen (ja/nein)? Wo
  standest du beim Rundblick?“ und, nur bei einem ersten Versuch: „Soll ich
  den Lauf wiederholen? Dann stell ihn bitte zurück an den Platz dieses
  Laufs und schreib ‚wiederholen', wenn er still steht.“
- **Nicht gefahren** (keine Zeile „Fahrziel gesendet“): „Er ist nicht
  gefahren. Bitte antworte in einer Nachricht: Was war die Nummer, die die
  KI gewählt hatte, wirklich (zum Beispiel Tür, Fenster, Regal, Wand,
  Stuhl)? Falls du nicht ‚ja' geschrieben hast: warum? Hat er beim Drehen
  etwas berührt (ja/nein)? Musstest du eingreifen (ja/nein)? Wo standest du
  beim Rundblick?“ und, nur bei einem ersten Versuch: „Soll ich diesen Lauf
  vom selben Platz einmal wiederholen? Dann lass ihn stehen und schreib
  ‚wiederholen'.“ (Hat die KI nichts gewählt, entfällt die Frage nach der
  Nummer.)
- **Nach Lauf 2 (und seiner Wiederholung) zusätzlich:** „Welche Nummer im
  Lotsen-Fenster war die Labortür (oder hatte sie keine)? Hatte das Fenster
  eine Nummer, und welche? Wie stand das Rollo (oben, halb, unten)?“
- **Teil für den nächsten Lauf** (bei einem Lauf ohne Durchfahrt eingeleitet
  mit „Sonst:“):
  - nach Lauf 1: „Stell ihn bitte für Lauf 2 **möglichst an den Platz aus
    KI-F9, Lauf 2**: Von dort lag die Tür etwa 2,3 m entfernt etwa 30° links
    vor ihm und das Fenster mit dem Rollo etwa 2,5 m hinter ihm. Rollo bitte
    so wie damals, wenn du es weißt. Seite ohne Türblatt, rundherum 50 cm
    frei, Tür ganz offen, nichts auf ihm. **Dein Platz in diesem Lauf:**
    rechts neben ihm, etwa auf Höhe seiner Mitte, 0,5 m vom Gehäuse, nicht
    hinter ihm (dort liegt das Fenster). Schreib ‚weiter', wenn er still
    steht.“
  - nach Lauf 2: „Stell ihn bitte für Lauf 3 an einen **dritten** Platz,
    1,5 bis 3 m vor der Tür, höchstens etwa 1 m seitlich der Türmitte,
    Seite ohne Türblatt, rundherum 50 cm frei; dein Platz wieder hinter ihm
    auf der Seite weg von der Tür. Schreib ‚weiter', wenn er still steht.“
  - nach Lauf 3: nichts.

Fehlt in der Antwort eine der erbetenen Angaben: **genau einmal** nur nach
den fehlenden fragen; fehlen sie dann noch: „nicht beurteilbar“.

**Danach:**
- **Berührung oder Eingriff:** keine weiteren Läufe, berichten.
- **„wiederholen“** (nur nach einem ersten Versuch ohne Durchfahrt): genau
  eine Wiederholung mit der Kennung `1w`, `2w` oder `3w` (erste Zeile von
  Schritt 1: `echo 2w > …`), am Platz dieses Laufs. Sein „wiederholen“ gilt
  als Bestätigung, dass Amadeus dort still steht. Nach einer Wiederholung
  wird keine weitere angeboten. Bittet Christopher von sich aus ausdrücklich
  um eine zweite: Kennung `1w2`, `2w2` oder `3w2`, im Bericht als
  Abweichung; eine dritte gibt es nicht.
- **„weiter“:** nächster Lauf (Lauf 1 → 2 → 3). Ein Lauf ohne Durchfahrt
  zählt dann als nicht erfüllt.
- Nach Lauf 3 (oder seiner Wiederholung): Bericht.

## Abbruch

- **Sofort stoppen** bei Berührung, bei einer anderen Bewegung als
  angekündigt, bei ungewöhnlichem Geräusch, starkem Schwanken oder Rauch.
  Christopher: Not-Aus oder App-Stopp. Agent: zuerst **genau einmal**
  `ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String
  "{data: '{\"type\":\"cancel\"}'}"` (in der ersten Shell, nach `source
  ~/roboter_worktrees/kif8.env`), dann Schritt 7 und 8. **Im Vorlauf** statt
  dessen: `ki_lauf.py aufraeumen --auftrag kif11 --lauf v1` (bzw. `v2`) und
  der letzte Block von Schritt 4 (Stack beenden). Danach nichts mehr
  starten; nur berichten.
- Hängt ein Werkzeug (keine neue Zeile über 5 Minuten, Amadeus steht), oder
  endet der Rundblick nicht (Schritt 5, erster Fall „noch keine
  Wartephase“): ebenso einmal `cancel`, dann Schritt 7 und 8, berichten,
  keine weiteren Läufe.
- Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4).
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bericht

Datei `~/ki_erkundung_bericht_kif11.md`, ohne Bilder, Scans, Karten,
Koordinaten und Adressen, ohne den Inhalt der Wahl-Dateien und Belege:

1. Stand (HEAD), die Zeile `src-Aenderungen`, `tests.txt`, `umgebung.txt`.
2. F0 und Christophers Antwort wörtlich.
3. Vorlauf: `pruefung.txt`, aus `vorpruefung.txt` die Zeilen zu
   „Motorschreiber“ und „Fahrbefehl“ und alle Zeilen `[FEHL]`, „bereit“ aus
   `lotse_status.txt`, `v1_start.txt`, `v1_wahl.txt`, `v1_messen.txt` ganz,
   die Zeile zu den Belegen und der Inhalt des neuesten Belege-Ordners (nur
   die Dateinamen), `v1_antwort.txt`, `v1_aufraeumen.txt`, `signale.json`;
   bei der Ausnahme dasselbe für `v2` und Christophers „fertig“.
4. **Je Lauf (und je Wiederholung):** Start, Prüfungen (bei der Ausnahme
   „Radsensor“ der ganze Inhalt von `radsensor.txt` und
   `last_bei_sperre.txt`), `l<k>_start.txt`, **`l<k>_wahl.txt` ganz** (ohne
   Pfade), die Frage F-Wahl, wie sie an Christopher ging, und seine Antwort
   wörtlich, **`l<k>_fahrt.txt` ganz**, `l<k>_aufraeumen.txt`,
   `etappen.txt`, `zaehler.txt`, größtes |v| und |w|, die Nachricht F-Lauf
   und Christophers Antwort wörtlich (mit einer Nachfrage, falls gestellt).
5. Die Tabellen der Kriterien mit dem Gemessenen und „trifft zu“, „trifft
   nicht zu“ oder „nicht beurteilbar“: T-1, U-1, V-0, V-1, B-1; je Lauf N-1,
   R-1, W-1, W-2, W-3, T-2, T-3, T-4, T-6, für Lauf 2 P-2; S-2, S-1 (falls
   Christopher nicht „ja“ sagte), G-1 und G-2. Für jeden Lauf ohne
   Durchfahrt der Grund aus `l<k>_fahrt.txt`.
6. Alles, was nicht lief oder abwich, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Bericht an Christopher.
