# Aktueller Agentenauftrag: SH-9 – Suchmechanismus EK-1 einschalten; Fahrt durch Labor, Flur und Schlafzimmer

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 16.11.2026 nach
der Auswertung von W-1N
([Archiv](archive/20261116-w1n-ausgewertet/README.md), STATUS Abschnitt
16.11.2026). Dein Bericht zu W-1N hat zwei Fehler der Cloud-Auswertung
aufgedeckt (die veraltete lokale Kostenkarte, die falsche Türmessung des
Werkzeugs); beides ist korrigiert, siehe „Neu, nur mitlesend“.

**Entscheidung des Projektinhabers (16.11.2026):** Der vereinbarte
Suchmechanismus kommt zuerst. Amadeus soll den Raum geordnet erfassen, zu
kleine Lücken auslassen und zügig zum nächsten Raum weiterfahren; 80–85 %
eines Raums genügen, ohne Fortschritt sucht er dort nicht weiter. In W-1 war
dieser Mechanismus ausgeschaltet. Am 08.11. (SH-7) fuhr Amadeus in zwei von
drei Fahrten durch die Labortür, am 15.11. in keiner von zwei.

**Die eine Änderung dieses Auftrags: EK-1 ist eingeschaltet** (`bab7cc7`,
fünf Zeilen im Profil `self_healing_params.yaml`):

- **A Teilschwenk:** Am Start und nach einem erreichten Ziel, das mindestens
  2,5 m von allen früheren Schwenks entfernt liegt, dreht Amadeus sich um
  90° (0,10 rad/s), sofern sein Drehkreis nachweislich frei ist. Der Mast
  verdeckt einen Teil des LiDAR.
- **B Nur Lücken, in die er passt:** Eine Lücke in der Karte zählt nur, wenn
  das Unbekannte dahinter mindestens 0,5 m breit ist. Schmale Schattenkeile
  und Streifen vor Wänden fährt er nicht an; sie halten auch das Ende nicht
  auf. **Am 16.11. korrigiert:** Zwischen Freiem und diesem Unbekannten darf
  ein bis zu 5 cm breiter ausgefranster Rand liegen, außer dicht (8 cm) an
  Wand- und Möbelfronten. Ohne den Rand fiel in der Simulation auch die Tür
  zum Nachbarraum durch den Filter, und die Fahrt endete als „vollständig“
  mit halb erfasstem Flur; ohne den Wandabstand fuhr Amadeus auf die Lücken
  einer Regalfront zu.
- **D Kürzere Fehlversuche:** Kommt er in einem Anlauf 45 s lang nicht
  mindestens 0,25 m von der Stelle, endet der Anlauf als Fehlversuch (bisher
  nach 150 s).

**Unverändert aus W-1:** KM-1 B, KM-2, AW-1, Tempo, Rückfahrt,
Heilungsleiter, 40-Minuten-Budget; jeder Start mit `hwt601_accel_ms:=100`.

**Fahrbereich (vom Projektinhaber am 16.11.2026 für diesen Auftrag
freigegeben): Laborraum, Flur und Schlafzimmer.** Bad, Küche und Wohnzimmer
bleiben zu. Der dritte Raum ist nötig, damit Amadeus den Laborraum wirklich
verlassen muss; einen leeren Flur erfasst er zum großen Teil schon von der
Tür aus.

**Neu, nur mitlesend (keine Wirkung auf die Fahrt):**

- **Nahbild im Fahrtprotokoll** (Schema 3): einmal je Sekunde die tödlichen
  Zellen der lokalen Kostenkarte bis 0,8 m um Amadeus, in
  Roboterkoordinaten, dazu die Breite der Stelle. Damit ist nach der Fahrt
  zu sehen, was der Regler an der Tür „sah“.
- **Lokale Kostenkarte am Ende frisch sichern:** 4 s mitschreiben statt
  `--once`; das Werkzeug liest die letzte vollständige Nachricht und nennt
  ihren Zeitstempel. (Die globale Kostenkarte hat mit dem Explorer einen
  ständigen Leser und ist deshalb auch mit `--once` frisch.)
- **Auswertung gleich am Jetson** (Schritt F7): `selbstheilung_ablauf.py`,
  `selbstheilung_anlaeufe.py` und `karte_engstelle.py` (misst jetzt
  zwischen tragenden Wandgruppen, Einzelzellen getrennt). Ihre Ausgaben
  gehören wörtlich in den Bericht; ein eigener Leseauftrag danach entfällt.

**Was die Fahrt zeigen soll:** ob Amadeus mit EK-1 (1) am Start schwenkt,
(2) im Laborraum nur wenige Ziele anfährt, (3) in wenigen Minuten an der
Labortür ist, (4) hindurch in den Flur und (5) weiter ins Schlafzimmer
fährt und (6) die Fahrt von selbst beendet.

**Ehrliche Erwartung zur Tür:** Die Labortür war am 15.11. das Hindernis
(der Planer lässt in der 78-cm-Tür nur einen Streifen von 22 cm zu; Amadeus
stand daneben). EK-1 ändert daran nichts. Bleibt er dort wieder hängen, ist
das kein Fehler dieses Auftrags; dann zählt, was Nahbild und Kostenkarten an
der Tür zeigen. **Die Tür ist die nächste Korrektur, nicht diese.** Dasselbe gilt für ein
vorzeitiges „vollständig“: Meldet Amadeus die Fahrt als fertig, obwohl ein
offener Raum fehlt, wird das genau so berichtet.

**Stand der Simulation (16.11.2026, Antrieb folgt den Befehlen, drei
Läufe mit diesem Stand):** In zwei Läufen mit drei Räumen fuhr Amadeus durch
beide Türen in alle drei Räume (6½ und 7½ Minuten, 8 Anläufe, 96–97 % der
Fläche; Ende von selbst). In einem Lauf mit zwei Räumen blieb er hinter der
Labortür hängen: Er stand im Flur vor der gegenüberliegenden Wand, setzte
zweimal gerade zurück, **stieß mit dem Heck an den Türpfosten** und rief
nach sieben Planerfehlern Hilfe. Das ist das Bild von W-1 Fahrt 1. In den
beiden anderen Läufen streifte er spät eine niedrige Kiste bzw. einen
Hocker seitlich (bekannte Grenze niedriger Dinge).

**Bekannte Grenzen, die Christopher absichert:**

- **Seiten niedriger Dinge sieht Amadeus nicht** (etwa 15 bis 66 cm hoch:
  Bettkante, Nachttisch, Stuhlbeine). Der LiDAR sitzt in 0,66 m Höhe, die
  VL53 sehen nur nach vorn.
- **Nach hinten sieht er nichts**; er setzt bis 0,4 m zurück. **In und
  hinter einer Tür ist das die gefährlichste Lage:** In der Simulation schob
  eine Rückfahrt das Heck an den Türpfosten (am 14.11. und am 16.11.).
  Christopher steht deshalb an jeder Tür so, dass er das Heck sieht.
- **Flaches unter etwa 5 cm sieht er nicht** (Kabel, Teppichkanten).
- **Der Teilschwenk ist neu:** Am Start dreht er sich um 90°, bevor er
  losfährt.

**Jede Berührung beendet den ganzen Auftrag.** Alle bestehenden Releases
bleiben unverändert.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md`,
`docs/LABORMODUS.md` (LAB-1), `docs/wohnungserkundung/MASTERPLAN.md` §9 mit
dem Nachtrag vom 16.11.2026, im STATUS die Arbeitsliste und den Abschnitt
16.11.2026, im Profil `src/explore/config/self_healing_params.yaml` den
Block „EK-1“, und die Köpfe von
`tools/kartierung/selbstheilung_lauf_protokoll.py` und
`tools/kartierung/karte_engstelle.py`.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 16.11.2026; **Fahrplan §9, Schritt 2 (EK-1), Regel 1** (eine Verhaltensänderung, Messwerkzeuge dürfen mitlesen) |
| WE-Bezug | WE-M3/WE-M4, metrischer Kern; Fahrplan Schritt 2, keine Abnahme |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens `bab7cc7`; neuer Release `selbstheilung-sh9-<STAMP>`. W-1 lief mit `selbstheilung-w1-20261115_1801` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh9.md`: Build, 249 gezielte Tests, bis zu zwei Fahrten mit den Kriterien E1–E6 und K, den Ausgaben der drei Auswertewerkzeuge wörtlich und Christophers Antworten wörtlich |
| Nicht-Ziele | keine eigene Code- oder Parameteränderung, keine Korrektur an der Tür, kein Raum mit Fliesen, keine Tür mit Schwelle, kein Arm, keine Raumziele (`go_to_room`), keine Änderung an Tempo, Rückfahrt, Langsam-Zone, Budget oder Anfahrzeit |
| Rückfall | in der Umgebungsdatei `SH_REL` auf `…/selbstheilung-w1-20261115_1801` (Stand W-1 ohne EK-1) zurückstellen; alle Releases bleiben. Im Code: die fünf EK-1-Zeilen im Profil entfernen |
| Fahrbereich und Freigabe | **Laborraum, Flur und Schlafzimmer, vom Projektinhaber am 16.11.2026 ausdrücklich für diesen Auftrag freigegeben** (LAB-1 gilt für neue Räume nicht von selbst). Bedingungen: Bad, Küche, Wohnzimmer und Wohnungstür zu; keine Stufe und keine Schwelle im offenen Bereich; bewegliche niedrige Dinge weggeräumt; keine weiteren Personen oder Tiere im Fahrbereich; Christopher geht mit der Hand am Not-Aus mit. Not-Aus-Erreichbarkeit ist als Betreibererklärung hinterlegt und wird nicht erneut abgefragt. 100 ms Anfahrzeit ist Standard (15.11.2026) |

## Verboten

- keine eigene Code- oder Parameteränderung, kein Commit oder Push; gebaut
  wird nur in Schritt 3;
- schreibend nur: der Stackstart je Fahrt, falls die App fehlt **genau ein**
  Missionsstart je Fahrt, und **genau ein** Missionsstopp je Fahrt, falls
  sie nach 20 Minuten noch läuft (F5); kein `param set`, `lifecycle set`,
  `service call`, kein weiteres `topic pub`, keine Nav2-Ziele;
- kein Start ohne `hwt601_accel_ms:=100`, kein Lauf von `antriebsprobe.py`;
- `operator_stationary_confirmed:=true` nur nach Christophers „ja“;
- Not-Aus und Nutzerabbruch nie zurücksetzen (LAB-1 §4);
- nichts in `~/roboter_ws` und an der defekten Codex-Referenz; bestehende
  Releases, der v1-Ordner und frühere Berichte bleiben, wie sie sind;
- die Werkzeuge nicht ändern; bei einem Fehler die Meldung wörtlich
  berichten;
- keine Prozessgruppen-Signale, kein `pkill -f`, kein `killall`, kein `kill -9`;
- keine Geheimnisse, IP-Adressen, Karten, Bilder oder Bags im Bericht; keine
  Listen von Zielen oder Wegen mit Koordinaten (die Ausgaben der Werkzeuge
  sind frei davon; Punkt und Blickrichtung für `karte_engstelle.py` bleiben
  in den lokalen Dateien).

## Was Amadeus in diesen Fahrten tut

- **Er kennt keine Räume.** Er wählt jeweils die günstigste Lücke in der
  Karte (nah und groß); die offene Tür ist eine davon. **Neu:** Lücken, hinter
  denen weniger als 0,5 m Unbekanntes liegt, zählen nicht mehr.
- **Neu: Teilschwenk.** Direkt nach dem Missionsstart dreht er sich um 90°
  (etwa 16 s), danach erst wählt er ein Ziel. Später schwenkt er erneut,
  wenn er ein Ziel mindestens 2,5 m vom letzten Schwenk entfernt erreicht
  hat.
- **Neu: 45-Sekunden-Grenze.** Kommt er in einem Anlauf 45 s nicht 0,25 m
  weiter, bricht er ab („Goal canceled“ im Log) und behandelt das wie einen
  Fehlversuch.
- **Vorwärts:** Regler 0,135 m/s, höchstens 0,162 m/s; 0,08 m/s, solange vor
  ihm nicht kartiert ist (also auch beim ersten Durchfahren einer Tür).
- **Drehen:** Regler 0,25 rad/s, höchstens 0,3125 rad/s. Dicht an
  Hindernissen (Langsam-Zone) dreht er sehr langsam, etwa 2,5° je Sekunde.
- **Rückwärts:** entlang der eigenen geraden Spur oder, wenn es keine gibt,
  0,3 m gerade zurück, sofern hinten frei ist; höchstens 0,4 m, 0,05 m/s
  (mit etwas vor ihm 0,015 m/s), einmal je Stillstand. **Nach hinten sieht
  er nichts.**
- **KM-1 B und KM-2 (wie W-1):** Hindernisse dicht an ihm bleiben in seiner
  lokalen Karte stehen; er fährt und dreht nicht in sie hinein, sondern
  meldet einen Fehlschlag und setzt gerade zurück.
- Er heilt Fehlschläge selbst: erneut versuchen, Ziel zurückstellen,
  umsehen, ein Stück zurück, nach acht Fehlschlägen in Folge „Hilfe
  benötigt“.
- Eine Fahrt endet von selbst mit „vollständig“, „Teilkarte“ oder „Hilfe
  benötigt“. **In diesem Auftrag beendet der Agent sie nach 20 Minuten**
  (F5), falls sie dann noch läuft.
- **Kurzes Stehenbleiben ist normal:** Setzen die VL53 einige Sekunden aus
  oder ist die Positionsbestimmung kurz zu alt, sperrt das Fahrtor, und der
  Explorer wartet. Das ist kein Eingriffsgrund. Auch Abbremsen oder kurzes
  Halten in der Tür ist normal.

## Einmal je Sitzung

Jeder ROS-Befehl beginnt mit `source ~/roboter_worktrees/selbstheilung-v2.env`.

### Schritt 0 – Bestand

```bash
date -Iseconds
git -C ~/roboter_ws rev-parse HEAD; git -C ~/roboter_ws status --short | head -5
python3 ~/roboter_ws/tools/kartierung/roboterknoten.py; echo "exit=$?"
```

Läuft ein Robotik-Stack: nichts beenden, Christopher genau einmal fragen.

### Schritt 1 – Klon aktualisieren, neuer Release-Ordner

```bash
STAMP=$(date +%Y%m%d_%H%M); echo "STAMP=$STAMP"
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short && git pull --ff-only && \
  git rev-parse HEAD && git merge-base --is-ancestor bab7cc7 HEAD && echo "bab7cc7 enthalten"
mkdir -p ~/.local/share/amadeus/releases/selbstheilung-sh9-$STAMP/pruefung
```

### Schritt 2 – Umgebungsdatei

In `~/roboter_worktrees/selbstheilung-v2.env` mit dem Datei-Werkzeug nur die
Zeile `export SH_REL=…` auf `$HOME/.local/share/amadeus/releases/selbstheilung-sh9-<STAMP>`
ändern. Die Unterbauzeilen bleiben. Prüfen:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env; echo "rc=$?"; echo "$SH_SRC $SH_REL"
printenv AMENT_PREFIX_PATH | tr ':' '\n' | grep -c "roboter_ws/install"
```

Erwartung: `rc=0`, Zähler `0`.

### Schritt 3 – Build (wie W-1)

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && cd "$SH_SRC" && \
export MAKEFLAGS=-j2 CMAKE_BUILD_PARALLEL_LEVEL=2 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 && \
SECONDS=0 && colcon --log-base "$SH_REL/product-log" build --executor sequential \
  --base-paths src/amadeus_map_identity src/base_hardware src/robot_interfaces \
    src/bt_orchestrator src/mission_manager src/robot_state_estimation src/explore \
    src/robot_navigation src/robot_map_manager src/vl53_near_field \
    src/safety_monitor src/amadeus_lidar_bringup src/robot_bringup src/semantic_map_manager \
  --build-base "$SH_REL/product-build" --install-base "$SH_REL/product-install" \
  --cmake-args \
    -Dbehaviortree_cpp_DIR=/home/p/.local/share/amadeus/releases/ap06-20261010T070231Z/native-install/behaviortree_cpp/share/behaviortree_cpp/cmake \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  2>&1 | tee "$SH_PR/build.log" | tail -25; echo "rc=${PIPESTATUS[0]} dauer_s=$SECONDS"
```

Danach wie in W-1 prüfen: `Found behaviortree_cpp` unter native-install,
alle 14 Präfixe unter `$SH_REL/product-install` (`prefixes.txt`). Dann die
Profilzeilen. **Neu sind nur die EK-1-Zeilen;** alles andere muss wie in
W-1 sein:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  grep -nE "self_healing_scan_rad|self_healing_scan_spacing_m|self_healing_gap_|self_healing_attempt_stall_|self_healing_saturation_" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml" | grep -v "#"; \
  grep -c "def deep_reach_mask" "$SH_REL/product-install/explore/lib/python3.10/site-packages/explore/self_healing.py"; \
  grep -n "minimum_travel" "$SH_REL/product-install/amadeus_lidar_bringup/share/amadeus_lidar_bringup/config/slam_toolbox_self_healing.yaml"; \
  grep -nE "desired_linear_vel|rotate_to_heading_angular_vel|max_velocity|min_velocity|footprint_topic|plugins|inflation_radius|cost_scaling_factor" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml" | grep -v "#"; \
  grep -nE "self_healing_stuck_move_m|overall_timeout_s|self_healing_unknown_speed_mps|initial_scan_angular_speed_radps|self_healing_free_back_m|self_healing_track_back_slow_factor" "$SH_REL/product-install/explore/share/explore/config/self_healing_params.yaml" | grep -v "#"; \
  grep -c "footprint_clearing_enabled: False" "$SH_REL/product-install/robot_navigation/share/robot_navigation/config/nav2_params_self_healing.yaml"; \
  ls "$SH_REL/product-install/robot_navigation/lib/robot_navigation/monitor_kontur" "$SH_REL/product-install/robot_navigation/lib/robot_navigation/rueckfahr_kontur"; \
  grep -n "footprint_topic" "$SH_REL/product-install/vl53_near_field/share/vl53_near_field/config/collision_monitor_self_healing_overlay.yaml"
```

Erwartet:

- **EK-1 (neu), genau diese fünf Zeilen:** `self_healing_scan_rad: 1.5708`,
  `self_healing_scan_spacing_m: 2.5`, `self_healing_gap_depth_m: 0.25`,
  `self_healing_gap_reach_m: 0.05`, `self_healing_attempt_stall_s: 45.0`;
  keine Zeile mit `self_healing_saturation_`; Zähler `deep_reach_mask` `1`
  (liegt die Datei unter einem anderen Python-Pfad, den Pfad mit
  `find "$SH_REL/product-install/explore" -name self_healing.py` suchen und
  dort zählen).
- Wie in W-1: `minimum_travel_distance: 0.25`, `minimum_travel_heading: 0.35`;
  Tempo `0.135`, `0.25`, `[0.162, 0.0, 0.3125]`, `[-0.05, 0.0, -0.3125]`;
  `footprint_topic: rueckfahr_kontur`, `plugins` mit `lidar_layer`, `0.6` /
  `2.5`; Explorer `0.05`, `2400.0`, `0.08`, `0.10`, `0.3`, `0.3`; KM-1 B:
  Zähler `2`; beide Programme vorhanden; im Overlay des Kollisionsmonitors
  `footprint_topic: "kollisionsmonitor_kontur"`.

Jede Abweichung: nicht fahren, berichten. Bei Build-Fehler oder fehlendem
Präfix: nicht fahren, berichten.

### Schritt 4 – gezielte Tests

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && cd "$SH_SRC" && \
env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider \
  src/explore/test/test_self_healing.py \
  src/explore/test/test_self_healing_runtime.py \
  src/explore/test/test_self_healing_gap_depth.py \
  src/explore/test/test_metric_float32_lattice.py \
  src/explore/test/test_metric_selection_retry.py \
  src/explore/test/test_metric_map_lifecycle.py \
  src/robot_navigation/test/test_nav_real_contract.py \
  src/robot_navigation/test/test_monitor_kontur.py \
  src/robot_bringup/test/test_semantic_map_launch_contract.py \
  src/vl53_near_field/test/test_mapping_collision_contract.py \
  tools/kartierung/test_selbstheilung_stillstand_pruefen.py \
  tools/kartierung/test_selbstheilung_lauf_protokoll.py \
  tools/kartierung/test_selbstheilung_ablauf.py \
  tools/kartierung/test_selbstheilung_anlaeufe.py \
  tools/kartierung/test_karte_engstelle.py \
  2>&1 | tee "$SH_PR/tests.log" | tail -40
```

Erwartung: `249 passed` (Cloud, Stand `bab7cc7`). Bei Fehlschlägen
nicht fahren, berichten.

### Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern. Die Antworten **wörtlich**
festhalten, jede Frage als eigene Frage mit freiem Text:

„Bitte bereite Labor, Flur und Schlafzimmer für die Fahrt vor:
1. **Türen:** die Tür zwischen Laborraum und Flur und die Tür zwischen Flur
   und Schlafzimmer ganz öffnen und sichern (Keil oder Türstopper). **Bad,
   Küche, Wohnzimmer und die Wohnungstür bleiben zu.** Balkon- und
   Terrassentüren und Fenster bis zum Boden bleiben zu.
2. **Boden frei:** Kabel, Schuhe, Taschen, lose kleine Teppiche und alles
   Flache unter etwa 15 cm aus den drei Räumen räumen, auch aus den
   Türbereichen.
3. **Bewegliches Niedriges weg:** Mülleimer, Hocker, Körbe, Kisten,
   Wäscheständer und Ähnliches aus dem Weg oder dicht an die Wand. Stühle
   ganz an den Tisch schieben.
4. **Niemand sonst** im Fahrbereich, keine Tiere.
5. **Akku** für mindestens 60 Minuten, Motor-Stop-Schalter freigegeben.
6. Du gehst während jeder Fahrt mit der Hand am Not-Aus mit.“

Dazu diese Fragen:

1. Welche Türen sind offen, welche zu?
2. Wohin öffnen die beiden offenen Türen (in welchen Raum), und wie stehen
   die Türblätter jetzt: ganz an der Wand, oder ragen sie in den Raum oder
   in die Öffnung? Wie breit ist jede Türöffnung an ihrer engsten Stelle
   (mit dem Zollstock gemessen, zwischen Zarge und Zarge oder Türblatt)?
3. Wie breit ist der Flur ungefähr, und was steht dort (Garderobe)?
4. Welche **festen niedrigen Möbel** stehen im Schlafzimmer (Bett,
   Nachttisch, niedrige Regale, Sitzbank)?
5. Gibt es im offenen Bereich **Glasflächen oder Spiegel bis zum Boden**
   oder **größere Teppiche**, die liegen bleiben? Wo?
6. Gibt es im offenen Bereich eine Stufe, eine Schwelle, einen Absatz oder
   Fliesen? (Erwartet: nein. **Bei „ja“: nicht fahren**, bis die Stelle mit
   einer geschlossenen Tür abgetrennt ist.)
7. Steht Amadeus an **demselben Startplatz und in derselben Richtung** wie
   am 15.11. (W-1)?

Ohne eine vollständige Antwort auf Frage 6 keine Fahrt. Geht die Serie an
einem anderen Tag weiter, den Aufbau einmal erneut bestätigen lassen
(„unverändert“ genügt).

## Die Fahrt (höchstens zwei)

Kaltstart mit neuer Karte im Laborraum. In jedem Befehlsblock `RUN=f1`
setzen (zweite Fahrt `RUN=f2`). Laden zwischen den Fahrten ist erlaubt.

### F1. Bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE /dev/amadeus_lidar
mkdir -p "$SH_PR/sh9_run$RUN"
```

Fehlt ein Gerät: nicht fahren, berichten. Christopher einmal fragen: „Steht
Amadeus an seinem Startplatz im **Laborraum** still, mindestens 1 m von der
offenen Tür, mit etwa 0,5 m Platz rundherum (er dreht sich gleich nach dem
Start um 90°), und bleibt er während des Starts (etwa eine Minute)
unberührt?“ Nur nach „ja“ weiter.

### F2. Stack scharf starten (mit 100 ms Anfahrzeit)

`source` steht in einer eigenen Zeile:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  hwt601_accel_ms:=100 \
  > "$SH_PR/sh9_run$RUN/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh9_run$RUN/launch.pid"; cat "$SH_PR/sh9_run$RUN/launch.pid"
date -Iseconds > "$SH_PR/sh9_run$RUN/launch_start.txt"
```

Die PID muss die des `ros2 launch`-Prozesses sein (`ps -o pid,cmd -p <PID>`).
Nach etwa 60 s `nodes.txt` und `lifecycle.txt` erfassen wie in W-1
(`/base_hardware`, `/rueckfahr_kontur` und `/monitor_kontur` vorhanden). Dann:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1
grep -n "Anfahrverhalten bestaetigt" "$SH_PR/sh9_run$RUN/launch.log" | tee "$SH_PR/sh9_run$RUN/anfahrzeit.txt"
grep -n "monitor_kontur" "$SH_PR/sh9_run$RUN/launch.log" | head -3
```

Erwartet: `Beschleunigen 100 ms, Bremsen 400 ms, Startdrehzahl 5 rpm` und
eine Zeile „Kollisionsmonitor-Kontur auf /kollisionsmonitor_kontur: voll …“.
Sonst: keine Mission, Stack geordnet beenden, berichten. Meldet der
LiDAR-Treiber „communication is abnormal“: Stack geordnet beenden,
Christopher einmal bitten, den LiDAR-Stecker zu prüfen, einmal neu starten.

### F3. Vorprüfung direkt vor der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && RUN=f1 && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --eigenecho-s 10 \
  --json "$SH_PR/sh9_run$RUN/vorpruefung.json" 2>&1 | tee "$SH_PR/sh9_run$RUN/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
grep -n "Profilwerte live" "$SH_PR/sh9_run$RUN/vorpruefung.txt"
for n in self_healing_scan_rad self_healing_scan_spacing_m self_healing_gap_depth_m self_healing_gap_reach_m self_healing_attempt_stall_s; do \
  echo "$n: $(ros2 param get /explore_node $n 2>&1)"; done | tee "$SH_PR/sh9_run$RUN/ek1_live.txt"
```

Erwartet: Exit 0 mit denselben Zeilen wie in W-1 (KM-2-Zeilen in Bereich C
OK, Bereich F vier OK-Zeilen). **Neu:** die Zeile „A Explorer: **49**
Profilwerte live gesetzt“ mit OK (in W-1 waren es 44), und die fünf
`param get` liefern `1.5708`, `2.5`, `0.25`, `0.05`, `45.0`. Regeln wie in W-1: bei
`FEHL` in „D Quellen“ Stack geordnet beenden und einmal neu starten; bei
`FEHL` im Bereich F oder in einer KM-2-Zeile nicht fahren, Auftrag beenden
und berichten; jeder andere `FEHL` (nach einer Wiederholung bei
„erreichbar“, „nicht deklariert“ oder „Graph unvollständig“): Stack geordnet
beenden und berichten, keine Fahrt. **Sind die EK-1-Werte nicht live: nicht
fahren, berichten.**

### F4. Fahrtprotokoll und Rechenlast starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh9_run$RUN/protokoll.json" --max-s 1800 \
  > "$SH_PR/sh9_run$RUN/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh9_run$RUN/protokoll.pid"
SLAM_PID=$(pgrep -x async_slam_tool | head -1); echo "SLAM_PID=$SLAM_PID"
echo "$SLAM_PID" > "$SH_PR/sh9_run$RUN/slam.pid"
nohup top -b -d 10 -p "$SLAM_PID" > "$SH_PR/sh9_run$RUN/slam_cpu.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh9_run$RUN/slam_cpu.pid"
sleep 5; grep -n "Messquelle Wackeln" "$SH_PR/sh9_run$RUN/protokoll.txt"
```

Erwartet: `Messquelle Wackeln: OK (/shadow/hwt601/imu/data_raw, 1 Sender)`.
Steht dort `FEHLT`: trotzdem fahren und berichten.

### F5. Mission starten, während der Fahrt, Ende nach 20 Minuten

Christopher drückt in der App „Erkunden“. Steht die App nicht zur Verfügung,
sendet der Agent **genau einmal**:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
date -Iseconds > "$SH_PR/sh9_run$RUN/missionsstart.txt"
```

Startet Christopher über die App, hält der Agent den Zeitpunkt ebenso fest
(`date -Iseconds > "$SH_PR/sh9_run$RUN/missionsstart.txt"`), sobald die
Mission läuft.

**Während der Fahrt** etwa alle zwei Minuten diese Abfrage (nur lesend):

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1; D="$SH_PR/sh9_run$RUN"
START=$(date -d "$(cat "$D/missionsstart.txt")" +%s); echo "seit Missionsstart: $(( $(date +%s) - START )) s"
kill -0 "$(cat "$D/protokoll.pid")" 2>/dev/null && echo "Protokoll läuft noch (Fahrt läuft)" || echo "Protokoll beendet (Fahrt zu Ende)"
```

**Zeigt sie 1200 s oder mehr und läuft das Protokoll noch**, sendet der
Agent **genau einmal** den Stopp, den auch die App sendet, und hält den
Zeitpunkt fest. Endet die Fahrt vorher von selbst, entfällt der Stopp:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1; D="$SH_PR/sh9_run$RUN"
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"cancel\"}'}"
date -Iseconds > "$D/missionsstopp.txt"
```

Das Protokoll beendet sich wenige Sekunden nach dem Missionsende von selbst.

- Der Agent greift sonst nicht ein und sendet keine weiteren Befehle.
- **Christopher geht mit, die Hand am Not-Aus.** Er drückt (App-Stopp oder
  Not-Aus), **bevor** etwas berührt wird:
  - wenn eine Ecke oder Seite beim Drehen näher als etwa zwei Finger breit
    an ein Möbel, einen Türpfosten oder ein Türblatt kommt;
  - wenn Amadeus auf etwas hinter ihm zurücksetzt; **in und hinter einer
    Tür schon, wenn das Heck beim Zurücksetzen einem Pfosten oder dem
    Türblatt näher kommt als eine Handbreit**;
  - wenn er auf Glas, einen Spiegel oder eine geschlossene Tür zufährt und
    nicht abbremst;
  - wenn er über etwas Flaches am Boden fahren würde;
  - wenn er auf eine Tür zufährt, die zu sein sollte.
- Kurzes Stehenbleiben, Abbremsen in Türen und Rückwärtsfahrten nach einem
  Fehlschlag sind normal und kein Eingriffsgrund.
- Christopher merkt sich mit Uhrzeit oder Minuten seit dem Start (ein Zettel
  genügt): **den Schwenk am Start**, wann Amadeus **an der Labortür** ist,
  wann er **ganz im Flur** steht, wann er **an der Schlafzimmertür** ist
  und wann er **im Schlafzimmer** ist; dazu, wie er durch jede Tür fuhr
  (gerade oder schräg, wie nah an Pfosten oder Türblatt).

### F6. Nach der Fahrt sichern (Amadeus steht, der Stack läuft noch)

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1; D="$SH_PR/sh9_run$RUN"
tail -60 "$D/protokoll.txt"
python3 -c "import json,sys; r=json.load(open(sys.argv[1])); [print(k, json.dumps(r.get(k), ensure_ascii=False)) for k in ('schema_version','protokoll_ende','dauer_s','endzustand','suche','heilungsverlauf','abdeckung','nahbild','rueckfahrten','tempo_folge','wackeln','fahrbefehle','vl53_luecken')]" "$D/protokoll.json"
timeout 10 ros2 topic echo --once --full-length /explore/status_json > "$D/explore_status_ende.txt" 2>&1
grep -o 'last_track_back[^}]*}' "$D/explore_status_ende.txt"
for m in "Begin navigating" "Goal succeeded" "Goal failed" "Goal canceled" "Controller patience exceeded" "Running backup" "backup completed successfully" "backup failed" "Canceling backup" "Robot to approach" "detected collision ahead" "failed to create plan" "harte Quellenstoerung" "Transform data too old" "extrapolation into the future" "queue is full" "process has died"; do \
  echo "$m: $(grep -c "$m" "$D/launch.log")"; done | tee "$D/zaehler.txt"
for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
  echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$D/lifecycle_nach.txt"
kill -TERM "$(cat "$D/slam_cpu.pid")"
grep -E "^ *$(cat "$D/slam.pid") " "$D/slam_cpu.txt" | awk '{print $9}' | tr '\n' ' ' | tee "$D/slam_cpu_reihe.txt"
ros2 run nav2_map_server map_saver_cli -f "$D/karte"
timeout 8 ros2 run tf2_ros tf2_echo map base_link > "$D/tf_map_base_link.txt" 2>&1
timeout 8 ros2 run tf2_ros tf2_echo odom base_link > "$D/tf_odom_base_link.txt" 2>&1
date +%s.%N > "$D/kostenkarten_zeit.txt"
timeout 4 ros2 topic echo --full-length /local_costmap/costmap > "$D/lokale_kostenkarte_ende.txt" 2>&1
timeout 20 ros2 topic echo --once --full-length /global_costmap/costmap > "$D/globale_kostenkarte_ende.txt" 2>&1
date +%s.%N >> "$D/kostenkarten_zeit.txt"
ls -la "$D"/karte.yaml "$D"/karte.pgm "$D"/lokale_kostenkarte_ende.txt "$D"/globale_kostenkarte_ende.txt
```

`protokoll.json` muss `schema_version 3` und einen Block `nahbild` haben.
`timeout 4` beendet das Mitschreiben der lokalen Kostenkarte absichtlich;
die Datei enthält mehrere Nachrichten, die letzte kann abgeschnitten sein.
Karten und Kostenkarten bleiben lokal.

Christopher die gespeicherte Karte (`karte.pgm`) als Bild zeigen (oder die
App) und dann fragen. Die Fragen **wörtlich und ohne Hinweis auf
Messwerte**, jede als eigene Frage mit freiem Text:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (App-Stopp, Not-Aus, Umsetzen)? Wenn ja: wo, was
   stand dort, und welche Seite von Amadeus kam zu nah?
3. Hat er sich am Start gedreht, bevor er losfuhr? Ungefähr wie weit?
4. Wann war er an der Labortür, wann ganz im Flur, wann an der
   Schlafzimmertür, wann im Schlafzimmer (Minuten seit dem Start)? Was davon
   hat er nicht erreicht?
5. Wie fuhr er durch die Labortür: gerade oder schräg, mittig oder nah an
   einer Seite? Hat er in der Tür angehalten, zurückgesetzt oder gedreht?
   Wie nah kam er Pfosten oder Türblatt? Dasselbe für die Schlafzimmertür.
6. Wie wirkte die Suche im Laborraum: geordnet oder kreuz und quer? Ist er
   Stellen mehrfach angefahren? Hat er sich oft auf der Stelle gedreht?
7. Wo kam er Dingen sehr nahe, ohne dass du eingreifen musstest? War es beim
   Fahren, beim Drehen oder beim Zurücksetzen?
8. Zur Karte: Ist jeder der drei Räume ganz, größtenteils, nur teilweise
   oder gar nicht zu erkennen? Sind die Wände sauber, besonders an den
   Türen?
9. Nur bei „Hilfe benötigt“ oder einem Halt in einer Tür: Wo stand er, und
   wie stand er zur Tür (gerade, schräg, an welchem Pfosten)?
10. Wie wirkte das Tempo: passend, zu schnell, zu langsam? Ist dir sonst
    etwas aufgefallen?

Danach den Stack geordnet beenden (SIGINT nur an die Launch-PID,
`roboterknoten.py` danach leer). Läuft das Protokoll noch, es vorher per
SIGINT an `protokoll.pid` beenden.

### F7. Auswertung am Jetson (nur lesen, ohne ROS)

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
RUN=f1; D="$SH_PR/sh9_run$RUN"; cd "$SH_SRC/tools/kartierung"
python3 selbstheilung_ablauf.py --log "$D/launch.log" --protokoll "$D/protokoll.json" \
  --json "$D/ablauf.json" > "$D/ablauf.txt" 2>&1; echo "ablauf exit=$?"
python3 selbstheilung_anlaeufe.py "$D/launch.log" --json "$D/anlaeufe.json" > "$D/anlaeufe.txt" 2>&1; echo "anlaeufe exit=$?"
read X Y < <(grep "Translation" "$D/tf_map_base_link.txt" | tail -1 | sed 's/.*\[\(.*\)\].*/\1/' | awk -F, '{print $1+0, $2+0}')
G=$(grep "RPY (degree)" "$D/tf_map_base_link.txt" | tail -1 | sed 's/.*\[\(.*\)\].*/\1/' | awk -F, '{print $3+0}')
GO=$(grep "RPY (degree)" "$D/tf_odom_base_link.txt" | tail -1 | sed 's/.*\[\(.*\)\].*/\1/' | awk -F, '{print $3+0}')
echo "Gier map=$G odom=$GO"; test -n "$X" && test -n "$G" && echo "Pose gelesen"
python3 karte_engstelle.py --karte "$D/karte.yaml" --punkt "$X" "$Y" --gier "$G" \
  --json "$D/engstelle_karte.json" > "$D/engstelle_karte.txt" 2>&1; echo "karte exit=$?"
python3 karte_engstelle.py --kostenkarte "$D/globale_kostenkarte_ende.txt" --punkt "$X" "$Y" --gier "$G" \
  --vergleich "$D/karte.yaml" \
  --json "$D/engstelle_global.json" > "$D/engstelle_global.txt" 2>&1; echo "global exit=$?"
python3 karte_engstelle.py --kostenkarte "$D/lokale_kostenkarte_ende.txt" --mitte --gier "$GO" \
  --json "$D/engstelle_lokal.json" > "$D/engstelle_lokal.txt" 2>&1; echo "lokal exit=$?"
cat "$D/kostenkarten_zeit.txt"; cat "$D"/engstelle_karte.txt "$D"/engstelle_global.txt "$D"/engstelle_lokal.txt
```

- Der Punkt (`$X $Y`) bleibt in den lokalen Dateien und kommt nicht in den
  Bericht; die Ausgaben der Werkzeuge enthalten ihn nicht.
- **Zeitstempel prüfen:** Die „Zeitstempel der Nachricht“ der beiden
  Kostenkarten müssen zwischen den zwei Zeiten in `kostenkarten_zeit.txt`
  liegen oder höchstens 3 s davor. Sonst ist die Karte veraltet: so
  berichten und für die Tür nicht verwenden.
- Steht Amadeus am Ende nicht in oder an einer Tür, zeigt
  `karte_engstelle.py` keine oder eine weite Engstelle; das ist dann
  richtig so und wird nur berichtet.
- Meldet ein Aufruf `FEHLER: …`: die Meldung wörtlich berichten, das
  Werkzeug nicht ändern, mit dem Rest weitermachen.

### F8. Zweite Fahrt und Ende

| Ende der ersten Fahrt | Weiter |
|---|---|
| von selbst („vollständig“, „Teilkarte“), nach 20 Minuten gestoppt, „Hilfe benötigt“ oder vorsorglicher Eingriff, jeweils **ohne Berührung** | Christopher stellt Amadeus an den Startplatz zurück. **Eine** zweite Fahrt `RUN=f2` ab F1, Kaltstart mit neuer Karte |
| Berührung, `outcome=error`, „process has died“ während der Fahrt, Eigenecho, `FEHL` in einer KM-2-Zeile, EK-1-Werte nicht live | **Auftrag beenden**, nur berichten |

Den Not-Aus setzt nur Christopher zurück, nie der Agent (LAB-1 §4). Nach
der zweiten Fahrt ist der Auftrag in jedem Fall beendet. Höchstens vier
Stackstarts insgesamt (Starts, die „D Quellen“ oder ein LiDAR-Startfehler
vor der Mission abfängt, zählen mit).

## Abbruch

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei:
  - Berührung, auch leicht, auch an Türrahmen oder Türblatt;
  - Fahrt oder Drehung auf ein Hindernis ohne rechtzeitiges Abbremsen;
  - Rückfahrt auf etwas zu, das hinter ihm steht;
  - Fahrt durch eine Tür, die zu sein sollte, oder auf eine Stelle zu, die
    Christopher für gefährlich hält;
  - Türblatt bewegt sich oder Tür fällt zu, während Amadeus in der Nähe ist
    (Fahrt ungültig, darf nach erneutem Sichern einmal wiederholt werden);
  - ungewöhnlichem Geräusch, starkem Schwanken des Aufbaus, Rauch.

  Nach einer **Berührung**, einem ungewöhnlichen Geräusch oder Rauch: keine
  weitere Fahrt in dieser Sitzung; nur berichten.
- **Endet eine Fahrt mit `outcome=error`:** anhalten und berichten.
- **Ungültige Fahrt** aus einem äußeren Grund (zum Beispiel kommt jemand in
  den Raum): darf einmal wiederholt werden.
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bewertung

Kriterien, vor der ersten Fahrt festgelegt. Der Agent stellt je Fahrt fest:
erfüllt, nicht erfüllt oder nicht feststellbar, mit Fundstelle. Das Urteil
über EK-1 und die nächste Änderung fällt in der Cloud-Sitzung.

| Nr | Kriterium | Quelle |
|---|---|---|
| E1 | EK-1 ist aktiv: 49 Profilwerte live, die fünf Werte stimmen, und das Protokoll zählt mindestens einen Schwenk (`suche.scans` ≥ 1) | `vorpruefung.txt`, `ek1_live.txt`, `protokoll.json` |
| E2 | Amadeus ist spätestens **5 Minuten** nach dem Missionsstart an der Labortür | Christopher (Frage 4), `ablauf.txt` (erste Engstelle) |
| E3 | Amadeus steht spätestens **10 Minuten** nach dem Missionsstart ganz im Flur | Christopher (Frage 4) |
| E4 | Amadeus fährt ins Schlafzimmer | Christopher (Frage 4) |
| E5 | Die Fahrt endet von selbst („vollständig“ oder „Teilkarte“) in höchstens 20 Minuten, nicht mit „Hilfe benötigt“, **und nicht bevor Amadeus im Schlafzimmer war** | `protokoll.json`, Christopher (Frage 4) |
| E6 | Kein Ziel wird öfter als dreimal angefahren | `ablauf.txt` („häufigstes Ziel“) |
| K | keine Berührung, kein Eingriff, kein `outcome=error`, kein „process has died“ während der Fahrt | Christopher (Fragen 1 und 2), Protokoll, `launch.log` |

Gemessen, aber kein Kriterium: Zahl der Anläufe und ihr Ausgang;
Zeitanteile Vorwärts, Drehen, Stehen (`anlaeufe.txt`); Abbruchgründe und
Wartephasen; `suche.shallow_frontiers` (ausgelassene schmale Lücken);
Abdeckungskurve; Engstellen und Reglerhalte mit Nahbild; Rechenlast
`slam_toolbox`; Zeitfehler; Tempo-Folge; Wackeln.

Zum Vergleich aus W-1 (15.11., ohne EK-1, alle Türen offen): Fahrt 1 an der
Labortür nach etwa 140 s, dort „Hilfe benötigt“ nach 219 s; Fahrt 2 in
20 Minuten 27 Anläufe auf 11 Ziele, eines 8-mal, nie an der Tür.

## Bericht: `~/selbstheilung_jetson_bericht_sh9.md`

1. Kopf: Datum, Release, HEAD, Ergebnis der Schritte 0–4 (Build-Dauer,
   Präfixe, Profilzeilen mit den fünf EK-1-Zeilen wörtlich, Testergebnis),
   Aufbau mit Christophers sieben Antworten wörtlich.
2. **Je Fahrt, Tabelle:** Zeile „Anfahrverhalten bestaetigt“, Vorprüfung
   (Exit, Zahl OK/FEHL, Zeile „Profilwerte live“ und `ek1_live.txt`
   wörtlich), „Messquelle Wackeln“, Ende und Dauer, `endzustand` und
   `suche` wörtlich, Kriterien E1–E6 und K je mit erfüllt / nicht erfüllt /
   nicht feststellbar und Fundstelle.
3. **Je Fahrt wörtlich und vollständig:** `ablauf.txt`; aus `anlaeufe.txt`
   der Block `zusammenfassung` und die Zeilen je Anlauf; `zaehler.txt`;
   die Blöcke `abdeckung`, `nahbild`, `rueckfahrten`, `tempo_folge` und
   `wackeln` aus dem Protokoll; `heilungsverlauf`; `last_track_back`;
   `slam_cpu_reihe.txt`; die Abdeckungskurve als kurze Tabelle alle zwei
   Minuten.
4. **Je Fahrt die Tür:** `engstelle_karte.txt`, `engstelle_global.txt`,
   `engstelle_lokal.txt` wörtlich, die zwei Zeiten aus
   `kostenkarten_zeit.txt` und das Ergebnis der Zeitstempelprüfung; dazu in
   eigenen Worten, wo Amadeus am Ende stand (Raum, an welcher Tür, Abstand
   ungefähr).
5. Christophers zehn Antworten je Fahrt wörtlich.
6. Auffälligkeiten, Abweichungen und nicht Ausgeführtes; Beobachtungen von
   Christopher getrennt von Messwerten. Keine Kartenbilder, keine Listen von
   Zielen mit Koordinaten.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository. Am Ende im Chat nur: Pfad; je Fahrt Ende,
Dauer, Zahl der Anläufe und der verschiedenen Ziele, ob Labortür, Flur und
Schlafzimmer erreicht wurden und wann, Kriterien E1–E6 und K, Kontakte.

## Danach

Auswertung in der Cloud-Sitzung. Bestehen die Fahrten nicht an der Tür,
folgt als nächste Änderung die Korrektur der Türdurchfahrt, mit den Daten
dieser Fahrt; der Rückstand der Positionsbestimmung bei langen Fahrten ist
die Änderung danach. Kein weiterer Versuch ohne neue Auswertung.
