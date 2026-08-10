# Hardware-Aktivierungsplan – Stand nach realer Lokalisierung

Der reale Hardwarestand ist weiter als die frühere V1-Planung, aber noch nicht
für Nav2 freigegeben. Vor jeder weiteren Aktivierung ist zuerst der
`UEBERNAHMEPLAN.md` vollständig abzuarbeiten. Solange Commit `390fcec`,
Worktree und Kartenartefakte nicht hashgesichert auf dem USB-Datenträger
liegen, bleibt jede Änderung am Jetson gesperrt.

## Bereits berichtet erreicht

- realer RTAB-Map-`/map`-Publisher,
- gespeicherter Karten-Snapshot,
- RTAB-Datenbank mit 902 Knoten und 271.805 Wörtern,
- 76 bestätigte `/localization_pose`-Meldungen während einer 357-Grad-Drehung,
- zwei Kartierfahrten ohne erneuten RS485-Ausfall nach dem Reconnect-Fix.

Diese Werte sind noch anhand der exportierten Datenbank, Dateien und Logs zu
verifizieren.

## Nächste Freigabestufen

1. Jetson-Code und Laufzeitdaten unverändert sichern.
2. Den exakten Jetson-Diff als neues isoliertes Release übernehmen und
   bewegungsfrei testen.
3. Kartenpose durch eine beaufsichtigte Fahrt über bekannte Distanz metrisch
   prüfen.
4. Direkte `/cmd_vel`-Umgehung des Collision Monitors beseitigen oder als
   separaten, manuell freizugebenden Sonderbetrieb sicherheitstechnisch
   abnehmen.
5. Tiefen- und Höhenverteilung messen.
6. Mit einer neuen Datenbank und erst dann mit geprüftem
   `Grid/RangeMax=4.0` eine flächigere Rasterkarte erzeugen.
7. Rastergeometrie und Wiederlokalisierung abnehmen.
8. Rosbridge-/iPhone-End-to-End-Test durchführen.
9. Nav2 in einem eigenen Release mit `static_map_odom:=false`, eindeutigen
   TF-Autoritäten, realem Footprint, Sensor-Costmaps, Collision Monitor,
   Watchdog und Hardware-NOT-AUS prüfen.

## Harte Abbruchkriterien

- Commit, Worktree oder Hashes weichen von der Sicherungsakte ab.
- RTAB-Datenbank besteht `PRAGMA quick_check` nicht oder enthält null Wörter.
- Mehr als ein Publisher beansprucht `map -> odom`, `odom -> base_footprint`
  oder den finalen `/cmd_vel`.
- `/localization_pose` bleibt bei der metrischen Gegenprobe aus.
- Der Roboter kann ohne Umgehung der Sicherheitskette nicht stoppen,
  rückwärts freigeben oder einen Watchdog-Stopp ausführen.
- Das neue Raster bleibt geometrisch unplausibel oder weist zu viel unbekannte
  beziehungsweise falsch belegte Fläche auf.

Bei einem Abbruch bleiben die funktionierende Datenbank und der bisherige
Snapshot unverändert. Es wird kein automatischer Wiederholungsversuch mit
veränderten Parametern gestartet.
