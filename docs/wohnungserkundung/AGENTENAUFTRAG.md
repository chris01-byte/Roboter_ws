# Aktueller Agentenauftrag: SH-5N – Daten zur Mülleimer-Stelle aus SH-5 Fahrt 3 (nur lesend)

**Für den lokalen KI-Agenten auf dem Jetson.** Erteilt am 04.11.2026. SH-5 ist
ausgewertet und [archiviert](archive/20261104-sh5-ausgewertet/README.md). In
Fahrt 3 (`sh5_run3`) blieb Amadeus vor einem etwa 40 cm hohen Mülleimer stehen
und rief nach etwa 10 Minuten „Hilfe benötigt“, obwohl links und hinten Platz
war. Die VL53 haben den Eimer gesehen, der Kollisionsmonitor hat davor
gebremst. Offen ist, **warum er keinen Weg darum herum fand**. Dafür brauchen
wir die vorhandenen Daten dieser Stelle. **Nichts wird gestartet, gefahren
oder gebaut.**

Vorher lesen (Branch `claude/blissful-pasteur-s1eivj`): `AGENTS.md` und im
STATUS den Abschnitt 04.11.2026 (SH-5).

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen bis 04.11.2026 |
| WE-Bezug | WE-M3, Auswertung SH-5 |
| Istbasis | Ordner `/home/p/.local/share/amadeus/releases/selbstheilung-sh5-20261104_1627/pruefung/sh5_run3` |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh5n.md` mit den Auszügen unten |
| Nicht-Ziele | kein Stackstart, kein ROS-Befehl, keine Fahrt, kein Build, keine Änderung an Code, Parametern, Releases oder `~/roboter_ws` |
| Rückfall | nicht nötig (nur lesend) |

## Verboten

- jeder Start von Prozessen außer Lese- und Auswertewerkzeugen (`cat`, `grep`,
  `python3` auf vorhandene Dateien);
- jeder ROS-Befehl (`ros2 …`), jedes Schreiben außerhalb des Berichts und eines
  eigenen Arbeitsordners unter `$SH_PR/werkzeug/`;
- Bilder, ganze Karten, Bags, IP-Adressen oder Geheimnisse im Bericht;
- kein Commit, kein Push.

Hinweis: Nav2 schreibt die geplanten Wege nicht ins Log. Sie sind deshalb
**nicht** gefragt; was fehlt, bitte nicht nachbauen, sondern als „nicht
vorhanden“ melden.

## Was zu liefern ist (aus `sh5_run3`)

1. **Ziele:** aus `launch.log` alle Zeilen „Begin navigating from current
   location (…) to (…)“ ab dem vierten erreichten Ziel bis „Hilfe benötigt“,
   wörtlich, mit Zeitstempel.
2. **Was Amadeus um sich kannte** (wie im SH-5-Bericht vermessen):
   - aus `lokale_kostenkarte_ende.txt`: Kopf (Rahmen, Auflösung, Ursprung,
     Größe, Zeitstempel), Roboterpose im selben Rahmen und alle Zellen mit Wert
     ≥ 99 im Umkreis von 1,0 m als Liste `x_vor y_links wert` **im
     Roboterrahmen** (Meter, zwei Nachkommastellen), sortiert nach Abstand;
   - aus `slam_karte_endstelle.txt`: belegte Zellen (≥ 65) im Umkreis von
     1,5 m, ebenso im Roboterrahmen;
   - geht die Umrechnung nicht sicher: Ausschnitt von höchstens 41 × 41 Zellen
     als Zahlenblock und der Grund.
3. **Wie gebremst wurde, je Anlauf** (vom Start eines Ziels bis zu seinem
   Abbruch, für die **letzten zwei** Anläufe vor „Hilfe benötigt“):
   - alle Zeilen von `collision_monitor` (Aktion, Polygon, Zeit) und von
     `controller_server` außer „detected collision ahead“, dazu deren Anzahl;
   - alle Zeilen von `bt_navigator` und `behavior_server`;
   - falls im Fahrtprotokoll oder Log vorhanden: wie weit sich Amadeus im
     Anlauf bewegt hat.
4. **Explorer-Status am Ende:** `explore_status_ende.txt` vollständig und
   wörtlich.

## Eine Frage an Christopher

Einmal fragen und wörtlich festhalten: „Wie groß ist der Mülleimer aus Fahrt 3
ungefähr (Höhe, Breite, rund oder eckig)? Wo stand er von Amadeus aus gesehen
(vorn, schräg links, schräg rechts) und wie weit weg? Und wo lagen von dort aus
die noch nicht erkundeten Bereiche, also wohin wollte er wohl fahren?“

## Bericht und Chat

Bericht nach `~/selbstheilung_jetson_bericht_sh5n.md`: Punkte 1–4, dann
Christophers Antwort, dann was nicht ging und warum. Am Ende im Chat nur der
Pfad, die nächste Zelle ≥ 99 (Abstand, Richtung) und die Zahl der Anläufe mit
„Failed to make progress“.

## Danach

Auswertung in der Cloud-Sitzung, zusammen mit einem Nachbau der Stelle in der
Simulation. Archivierte Aufträge sind keine aktuellen Aufträge und dürfen nicht
erneut ausgeführt werden.
