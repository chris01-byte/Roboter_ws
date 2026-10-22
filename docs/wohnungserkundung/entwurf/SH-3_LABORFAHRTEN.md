# ENTWURF – SH-3: drei begrenzte Laborfahrten (Abnahmestufe 1)

> **Nicht ausführen.** Dieser Entwurf wird erst nach bestandenem SH-2 in
> `docs/wohnungserkundung/AGENTENAUFTRAG.md` übernommen. Bis dahin gilt
> ausschließlich der dortige aktuelle Auftrag. Vorbereitet am 22.10.2026.

**Für den lokalen KI-Agenten auf dem Jetson.** Drei echte, autonome
Erkundungsfahrten im Selbstheilungsbetrieb im Laborraum, bewertet nach
Abnahmestufe 1 (`KONZEPT_SELBSTHEILUNG.md` §11). Odometrie: HWT601
(Entscheidung 8 vom 22.10.2026, Begründung in §9 des Konzepts).

## Rahmen

| | |
|---|---|
| Planversion | MASTERPLAN v1.3 mit Nutzerentscheidungen vom 15./16./22.10.2026 |
| WE-Bezug | WE-M3 (metrischer Erkundungskern), Abnahmestufe 1 der Hauptlinie `self_healing` |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, Release aus SH-2 (`selbstheilung-sh2-<STAMP>`), SH-2 bestanden einschließlich HWT-Weg |
| Erwartetes Ergebnis | Bericht `~/selbstheilung_jetson_bericht_sh3.md`: drei Fahrten mit Fahrtprotokoll, Christophers Beobachtungen, Gesamturteil Stufe 1 |
| Nicht-Ziele | keine Code- oder Parameteränderung, kein anderer Raum, keine Wohnungsfahrt, kein Arm, keine Fahrt außerhalb des Laborraums |
| Rückfall | Stack geordnet stoppen; `self_healing:=false` bzw. SH-1-/AP06-Releases bleiben unverändert verfügbar |
| Laborrahmen | LAB-1: aktive Fahrt im beauftragten Umfang ohne erneute Standardfreigaben. Not-Aus-Erreichbarkeit, freier Fahrbereich und Abwesenheit Unbeteiligter sind als Betreibererklärung hinterlegt und werden **nicht** erneut abgefragt |

## Was Amadeus in diesen Fahrten tut

- **Vorwärts:** höchstens 0,12 m/s; 0,06 m/s, solange vor ihm nicht kartiert ist.
- **Drehen:** höchstens 0,25 rad/s.
- **Rückwärts:** nur entlang der eigenen Spur, höchstens 0,4 m, 0,05 m/s.
- Er wählt seine Ziele selbst (Frontiers) und heilt Fehlschläge selbst:
  1. erneut versuchen;
  2. Ziel zurückstellen;
  3. umsehen;
  4. ein Stück zurück entlang der Spur;
  5. „Hilfe benötigt“.
- Eine Fahrt endet von selbst mit „vollständig“, „Teilkarte“ oder „Hilfe
  benötigt“, spätestens nach 20 Minuten (Explorer-Gesamtbudget).

## Einmal je Sitzung: Aufbau (Christopher)

Nur diese konkrete Handlung einmal anfordern: „Bitte die Türen des Laborraums
schließen, sodass Amadeus den Raum nicht verlassen kann.“ Der Selbstheilungs-
betrieb kennt keinen Software-Fahrbereich; den Raum begrenzen Wände und
geschlossene Türen. Ohne geschlossenen Raum keine Fahrt.

## Je Fahrt (Nr 1, 2, 3)

Jede Fahrt ist ein Kaltstart mit neuer Karte. `RUN` = 1, 2 oder 3.

### 1. Bereit

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
python3 "$SH_SRC/tools/kartierung/roboterknoten.py" --still || echo "STACK LAEUFT SCHON - abbrechen"
ls -l /dev/ttyUSB_HWT601 /dev/ttyUSB_BASE
mkdir -p "$SH_PR/sh3_run$RUN"
```

Christopher einmal fragen: „Steht Amadeus an seinem Startplatz still, mit etwa
0,5 m Platz rundherum, und bleibt er während des Starts (etwa eine Minute)
unberührt?“ Nur nach „ja“ weiter. Der Startplatz darf je Fahrt wechseln; ihn
im Bericht beschreiben lassen.

### 2. Stack scharf starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
nohup env --default-signal=INT ros2 launch robot_bringup app_mapping.launch.py \
  self_healing:=true start_web_gui:=false \
  use_hwt601_odometry:=true hwt_development_contract:=true operator_stationary_confirmed:=true \
  active_drive:=true enable_auto_explore:=true \
  > "$SH_PR/sh3_run$RUN/launch.log" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh3_run$RUN/launch.pid"; cat "$SH_PR/sh3_run$RUN/launch.pid"
```

Nach etwa 60 s Knoten und Lifecycle wie in SH-2 erfassen.

### 3. Vorprüfung direkt vor der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env && \
  python3 "$SH_SRC/tools/kartierung/selbstheilung_stillstand_pruefen.py" --odometrie hwt601 --aktiv \
  --json "$SH_PR/sh3_run$RUN/vorpruefung.json" 2>&1 | tee "$SH_PR/sh3_run$RUN/vorpruefung.txt"; echo "exit=${PIPESTATUS[0]}"
```

Nur bei Exit 0 weiter. Sonst Stack stoppen (Schritt 7) und berichten; keine
Fahrt.

### 4. Fahrtprotokoll starten

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
nohup env --default-signal=INT python3 "$SH_SRC/tools/kartierung/selbstheilung_lauf_protokoll.py" \
  --json "$SH_PR/sh3_run$RUN/protokoll.json" \
  > "$SH_PR/sh3_run$RUN/protokoll.txt" 2>&1 < /dev/null &
echo $! > "$SH_PR/sh3_run$RUN/protokoll.pid"
```

### 5. Mission starten

Christopher drückt in der App „Erkunden“. Das ist der Produktweg. Steht die App
nicht zur Verfügung, sendet der Agent **genau einmal** denselben Befehl wie die
App. Das ist der einzige erlaubte Schreibbefehl dieses Auftrags:

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String "{data: '{\"type\":\"explore\"}'}"
```

### 6. Während der Fahrt

- Der Agent greift nicht ein und sendet keine weiteren Befehle.
- Christopher beobachtet und darf jederzeit über die App stoppen oder den
  Not-Aus drücken. Das gilt dann als **Eingriff**.
- Die Fahrt endet von selbst; das Protokoll beendet sich wenige Sekunden danach.

### 7. Nach der Fahrt

```bash
source ~/roboter_worktrees/selbstheilung-v2.env
cat "$SH_PR/sh3_run$RUN/protokoll.txt" | tail -60
for n in controller_server planner_server behavior_server bt_navigator velocity_smoother collision_monitor; do \
  echo "$n: $(ros2 lifecycle get /$n 2>&1)"; done | tee "$SH_PR/sh3_run$RUN/lifecycle_nach.txt"
grep -c "process has died" "$SH_PR/sh3_run$RUN/launch.log"
grep -nE "Ignoring the source|TERMINAL_FAULT|ERROR|FATAL" "$SH_PR/sh3_run$RUN/launch.log" | head -40
ros2 run nav2_map_server map_saver_cli -f "$SH_PR/sh3_run$RUN/karte"
```

Christopher dann einmal fragen und die Antworten wörtlich festhalten:

1. Hat Amadeus etwas berührt?
2. Musstest du eingreifen (Stopp, Not-Aus, Umsetzen)?
3. Sieht die Karte in der App sauber aus, ohne doppelte oder verdrehte Wände?

Danach den Stack geordnet beenden (wie SH-2 Schritt 9: SIGINT nur an die
Launch-PID, `roboterknoten.py` danach leer). Läuft das Protokoll noch, sein
Prozess vorher per SIGINT an `protokoll.pid` beenden.

## Abbruch und Wiederholung

- **Sofort stoppen** (Christopher: Not-Aus oder App-Stopp; Agent: Stack
  geordnet beenden) bei:
  - Berührung;
  - Fahrt auf ein Hindernis ohne Abbremsen;
  - Verlassen des Laborraums;
  - ungewöhnlichem Geräusch;
  - Rauch.

  Danach keine weitere Fahrt in dieser Sitzung; nur berichten.
- **Endet eine Fahrt mit `outcome=error`:** die Serie anhalten und berichten.
  Keine identischen Fehlversuche aneinanderreihen.
- **Ungültige Fahrt:** Ist eine Fahrt aus einem äußeren Grund ungültig (zum
  Beispiel kommt jemand in den Raum), darf sie einmal wiederholt werden.
  Höchstens vier Starts je Sitzung.
- Keine Parameter ändern, um eine Fahrt „durchzubringen“.

## Bewertung Abnahmestufe 1

Bestanden, wenn **alle drei** Fahrten erfüllen:
- `automatisch_erfuellt: true` im Fahrtprotokoll: begonnen, beendet,
  mindestens zwei selbst gewählte Ziele erreicht, sauberes Ende
  (`exploration_complete`, `usable_partial` oder `blocked_help_required`),
  kein Not-Aus während der Fahrt;
- kein Kontakt und kein Eingriff (Christopher);
- Nav2 nach der Fahrt in einem klaren Zustand, kein „process has died“.

Die Fahrzeit wird gemessen, ist aber kein Abbruchkriterium.

## Bericht: `~/selbstheilung_jetson_bericht_sh3.md`

1. Kopf: Datum, Release, HEAD, Raum und Türen (Christophers Angabe).
2. Je Fahrt:
   - Startplatz;
   - Vorprüfung (Exit, Bereich C/D);
   - Fahrtprotokoll ohne `ereignisse`, dazu die Ereignisliste gekürzt auf
     Zustandswechsel, HWT, Not-Aus, VL53-Lücken;
   - Lifecycle danach, „process has died“-Zahl, Warnungen;
   - Christophers drei Antworten wörtlich.
3. Tabelle über alle Fahrten: Dauer, Ziele, Heilungen, Umsehen,
   Spurrückfahrten, Endzustand, Strecke, VL53-Lücken, Kontakt, Eingriff.
4. Gesamturteil Stufe 1: bestanden / nicht bestanden, mit Grund.
5. Auffälligkeiten, Abweichungen und nicht Ausgeführtes.

Karten, Bags und Bilder bleiben lokal unter `$SH_PR` und kommen weder in den
Bericht noch ins Repository.
