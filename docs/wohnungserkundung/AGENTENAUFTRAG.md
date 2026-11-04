# Aktueller Agentenauftrag: SH-4N – Nachlieferung zu den „Hilfe benötigt“-Stellen (nur lesend)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 04.11.2026. SH-4 ist
ausgewertet und [archiviert](archive/20261104-sh4-ausgewertet/README.md):
SL-1 ist am Jetson abgenommen, DR-1 bleibt offen. In Fahrt 2 (`sh4_run2`) und
in der Wiederholung von Fahrt 3 (`sh4_run4`) endete Amadeus neben Gegenständen
mit „Hilfe benötigt“, obwohl laut Christopher Platz zum Ausweichen war. Für
das Arbeitspaket DR-2 brauchen wir die vorhandenen Rohdaten dieser zwei
Stellen. **Nichts wird gestartet, gefahren oder gebaut.**

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md` und im
STATUS den Abschnitt 04.11.2026.

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 04.11.2026 |
| WE-Bezug | WE-M3, Arbeitspaket DR-2 (Drehsperre neben Gegenständen) |
| Istbasis | Ordner `/home/p/.local/share/amadeus/releases/selbstheilung-sh4-20261103_1738/pruefung/sh4_run2` und `…/sh4_run4` aus SH-4 |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh4n.md` mit den Auszügen unten |
| Nicht-Ziele | kein Stackstart, kein ROS-Befehl, keine Fahrt, kein Build, keine Änderung an Code, Parametern, Releases oder `~/roboter_ws` |
| Rückfall | nicht nötig (nur lesend) |

## Verboten

- jeder Start von Prozessen außer Lese- und Auswertewerkzeugen (`cat`, `grep`,
  `python3` auf vorhandene Dateien);
- jeder ROS-Befehl (`ros2 …`), jedes Schreiben außerhalb des Berichts und eines
  eigenen Arbeitsordners unter `$SH_PR/werkzeug/`;
- Bilder, ganze Karten, Bags, IP-Adressen oder Geheimnisse im Bericht;
- kein Commit, kein Push.

## Was zu liefern ist (je für `sh4_run2` und `sh4_run4`)

1. **Explorer-Status am Ende:** Inhalt von `explore_status_ende*.txt`
   vollständig und wörtlich (JSON), insbesondere `ladder`, `last_track_back`,
   `active_goal`.
2. **Lokale Kostenkarte um den Roboter** aus `lokale_kostenkarte_ende.txt`:
   - Kopf: Rahmen, Auflösung, Ursprung, Breite/Höhe, Zeitstempel;
   - Roboterpose zum selben Zeitpunkt im selben Rahmen (x, y, Gierwinkel) und
     woher sie stammt;
   - alle Zellen mit Wert ≥ 99 im Umkreis von 1,0 m um die Robotermitte als
     Liste `x_vor y_links wert` in Metern **im Roboterrahmen** (x nach vorn,
     y nach links, zwei Nachkommastellen), sortiert nach Abstand;
   - geht die Umrechnung nicht sicher, stattdessen den Ausschnitt von
     höchstens 41 × 41 Zellen um den Roboter als Zahlenblock und den Grund.
3. **SLAM-Karte um den Roboter** aus `slam_karte_endstelle.txt` (soweit
   vorhanden): gleich wie Punkt 2, belegte Zellen (≥ 65) im Umkreis von
   1,5 m, im Roboterrahmen.
4. **Log-Auszug** aus `launch.log` vom letzten erreichten Ziel vor der ersten
   Heilung bis „Hilfe benötigt“:
   - alle Zeilen von `explore_node`, `bt_navigator` und `behavior_server`;
   - von `controller_server` alle Zeilen außer „detected collision ahead“,
     dazu deren Anzahl in diesem Zeitraum;
   - von `collision_monitor` nur die Anzahl „Ignoring the source“ und die
     erste und letzte Zeile davon.
5. **Fahrtprotokoll:** die `ereignisse` aus `protokoll.json` im selben
   Zeitraum, wörtlich.

## Eine Frage an Christopher

Einmal fragen und wörtlich festhalten: „Wo standen die Gegenstände, vor denen
Amadeus in Fahrt 2 (Mülleimer) und in der Wiederholung von Fahrt 3 stehen
blieb, von ihm aus gesehen: vorn, links, rechts oder hinten, und wie weit
ungefähr? Wohin hätte er nach deiner Einschätzung ausweichen können?“

## Bericht und Chat

Bericht nach `~/selbstheilung_jetson_bericht_sh4n.md`: je Lauf die Punkte 1–5,
dann Christophers Antwort, dann was nicht ging und warum. Am Ende im Chat nur
der Pfad und je Lauf eine Zeile: nächste Zelle ≥ 99 (Abstand, Richtung),
Zahl der Spurrückfahrten, letzte Heilungsaktion.

## Danach

Auswertung in der Cloud-Sitzung (Arbeitspaket DR-2). Archivierte Aufträge
sind keine aktuellen Aufträge und dürfen nicht erneut ausgeführt werden.
