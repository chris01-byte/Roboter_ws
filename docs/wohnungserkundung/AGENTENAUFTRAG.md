# Aktueller Agentenauftrag: SH-7N – Daten zu den Hilfe-Stellen aus SH-7 (nur lesend)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 08.11.2026. SH-7 ist
ausgewertet und [archiviert](archive/20261108-sh7-ausgewertet/README.md). Alle
drei Fahrten endeten mit „Hilfe benötigt“ an Stellen, an denen Christopher
einen Ausweg sah. Viele Anläufe brachen nach 7–9 s ab, zwei Rückfahrten
meldeten sofort „Collision Ahead“, und im Flur fehlte zweimal eine Wand.
Entscheidung des Projektinhabers: **erst Daten prüfen, dann lösen.**
**Nichts wird gestartet, gefahren oder gebaut.**

**Arbeitshypothese (zu prüfen, nicht zu bestätigen):** Die lokale
Kostenkarte liegt im `odom`-Rahmen. Der LiDAR markiert dort, räumt aber nie
(Entscheidung X9); räumen können nur die VL53 (vorn, 0,45–0,7 m). Die
Odometrie wich am Ende jeder Fahrt um etwa 0,3 m und 2–6° von der SLAM-Karte
ab (aus den Endposen im SH-7-Bericht). Dann liegen Wände aus früheren
Fahrminuten verschoben in der lokalen Karte, Durchgänge werden dort schmaler,
und Regler und Rückfahrt melden Kollision, wo frei ist. Die Daten unten
zeigen, ob das stimmt oder nicht. Ein „stimmt nicht“ ist ein ebenso gutes
Ergebnis.

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md` und im
STATUS den Abschnitt 08.11.2026 (SH-7).

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 08.11.2026 |
| WE-Bezug | WE-M3, Auswertung SH-7 |
| Istbasis | Ordner `/home/p/.local/share/amadeus/releases/selbstheilung-sh7-20261108_1617/pruefung/sh7_run1`, `sh7_run2`, `sh7_run3` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh7n.md` mit den Punkten 1–6 unten |
| Nicht-Ziele | kein Stackstart, kein ROS-Befehl, keine Fahrt, kein Build, keine Änderung an Code, Parametern, Releases, Umgebungsdatei oder `~/roboter_ws` |
| Rückfall | nicht nötig (nur lesend) |

## Verboten

- jeder Start von Prozessen außer Lese- und Auswertewerkzeugen (`cat`,
  `grep`, `python3` auf vorhandene Dateien);
- jeder ROS-Befehl (`ros2 …`), jedes Schreiben außerhalb des Berichts und
  eines eigenen Arbeitsordners `$SH_PR/werkzeug/`;
- Bilder, ganze Karten, Bags, IP-Adressen oder Geheimnisse im Bericht (ein
  Kartenbild nur lokal für Christopher, wie in SH-7);
- kein Commit, kein Push.

Was in den Dateien fehlt, bitte nicht nachbauen oder schätzen, sondern als
„nicht vorhanden“ melden. Jede Umrechnung mit Formel und Eingangswerten
angeben, damit sie in der Cloud nachgerechnet werden kann.

## Was zu liefern ist

Je Fahrt (`sh7_run1`, `sh7_run2`, `sh7_run3`), Stelle = Pose am Ende, an der
„Hilfe benötigt“ kam:

1. **Odometrie-Abweichung am Ende:** aus den in SH-7 gesicherten
   `tf2_echo`-Ausgaben `map→base_link` und `odom→base_link` (Dateinamen wie
   vorhanden) die Werte wörtlich und daraus `map→odom` (x, y, Gier in Grad),
   berechnet als `T_map_odom = T_map_base · (T_odom_base)⁻¹`.
2. **Hindernisse der lokalen Karte gegen die SLAM-Karte:**
   - Eingang: `lokale_kostenkarte_ende_voll.txt` (Rahmen `odom`, Kopf mit
     Auflösung, Ursprung, Größe) und `karte.yaml`/`karte.pgm` (Rahmen `map`;
     `negate`, `occupied_thresh`, `free_thresh` aus der yaml beachten).
   - Für jede Zelle der lokalen Karte mit Wert ≥ 99 im Umkreis von 1,5 m um
     `base_link`: Lage im Roboterrahmen (`x_vor`, `y_links`, Meter, zwei
     Nachkommastellen), nach `map` umgerechnet mit Punkt 1, dort der Zustand
     der SLAM-Karte (belegt/frei/unbekannt) und der Abstand zur nächsten
     belegten SLAM-Zelle.
   - Zusammenfassung als Tabelle: Zahl der Zellen ≥ 99 gesamt; davon mit
     nächster belegter SLAM-Zelle ≤ 0,10 m, 0,10–0,30 m und > 0,30 m; davon
     wie viele auf in der SLAM-Karte **freien** Zellen liegen.
   - Gesondert: alle Zellen ≥ 99 innerhalb der Roboterkontur plus 0,05 m
     (Kontur aus `footprint` und `footprint_padding` des lokalen Costmaps in
     `nav2_params_real.yaml` des Releases), mit Lage und SLAM-Zustand.
   - Die 20 Zellen ≥ 99, die dem Roboter am nächsten sind, als Liste.
3. **Warum die Anläufe abbrachen:** aus `launch.log`, für Fahrt 1 die
   letzten 3 Anläufe, für Fahrt 2 und 3 die letzten 8 Anläufe vor „Hilfe
   benötigt“, und für Fahrt 3 zusätzlich die Anläufe 19:22:42–19:25:01 und
   19:34:28–19:34:57 (vor der Tür): je Anlauf von „Begin navigating“ bis zu
   seinem Ende alle Zeilen von `bt_navigator`, `planner_server`,
   `controller_server` und `behavior_server` wörtlich. „detected collision
   ahead“ und sich wiederholende gleiche Zeilen nur zählen (erste und letzte
   wörtlich). Dazu je Anlauf die Zahl der `collision_monitor`-Zeilen je
   Aktion.
4. **Die beiden sofortigen „Collision Ahead“ der Rückfahrt** (Fahrt 1
   16:58:13, Fahrt 2 18:13:14): alle Zeilen ±3 s um den Zeitpunkt wörtlich.
   Für Fahrt 1 (Amadeus stand bis zum Ende an derselben Stelle) zusätzlich
   aus Punkt 2: Zellen ≥ 99 hinter dem Roboter (`x_vor` zwischen −0,25 und
   −0,11 m, `y_links` zwischen −0,25 und +0,25 m). Für Fahrt 2 liegt keine
   Kostenkarte von 18:13 vor: „nicht vorhanden“.
5. **Wie lange die Fahrt bis dahin war:** je Fahrt aus dem Protokoll die
   Odometrie-Strecke und die Zahl der Drehungen auf der Stelle, falls
   ableitbar; sonst „nicht vorhanden“.
6. **Christophers Antworten** (siehe unten), wörtlich.

## Fragen an Christopher

Einmal fragen und wörtlich festhalten. Dazu das Kartenbild von Fahrt 1 lokal
zeigen, wie in SH-7:

1. „Im Flur fehlt in der Karte eine Wand. Du hast gesagt, dort ist eine Tür
   oder ein Durchgang. Welche Wand ist es auf dem Bild? Ist es eine Tür (war
   sie bei SH-7 offen oder zu, ist sie aus Glas?) oder ein offener
   Durchgang ohne Tür? Wie breit, und wohin führt er?“
2. „Die Garderobe im Flur: Wie tief ragt sie in den Flur, wie tief hängen
   Jacken oder Taschen herunter (Höhe über dem Boden), und wie breit war der
   freie Weg daneben?“
3. „An den Hilfe-Stellen von Fahrt 2 (Laborraum nahe der Tür) und Fahrt 3
   (Ecke): Lag dort etwas Niedriges unter etwa 15 cm (Kabel, Schuhe,
   Kartons)?“

## Bericht und Chat

Bericht nach `~/selbstheilung_jetson_bericht_sh7n.md`: Punkte 1–6, dann was
nicht ging und warum. Am Ende im Chat nur: Pfad; je Fahrt `map→odom` (x, y,
Gier), die Zahl der Zellen ≥ 99 im Umkreis von 1,5 m und davon auf SLAM-freien
Zellen mehr als 0,10 m von der nächsten SLAM-Wand, die Zahl der Zellen ≥ 99
innerhalb Kontur + 0,05 m; der häufigste Abbruchgrund je Fahrt; Christophers
Antwort zur fehlenden Wand in einem Satz.

## Danach

Auswertung in der Cloud-Sitzung, dann ein gezielter Befreiungsschritt
(Entscheidung des Projektinhabers 08.11.2026). Archivierte Aufträge sind keine
aktuellen Aufträge und dürfen nicht erneut ausgeführt werden.
