# Aktueller Agentenauftrag: AP-04

Am 03.10.2026 ausdrücklich durch Nutzer „gut dann mach mit 04 weiter“ beauftragt. Verbindlich: [MASTERPLAN v1.3](MASTERPLAN.md), [STATUS](STATUS.md), AGENTS, LAB-1 und WE-M3. [AP-03 bytegleich archiviert](archive/20261003-ap03/README.md).

## Basis und Ergebnis

Sauberer AP-03-Abschluss `495b538`, Branch `feature/frontier-candidate-core`, Worktree `/workspace/Roboter_ws-ap04`. Ausschließlich AP-04: unveränderten eigenen Kern mit `mertgulerx/frontier_exploration_ros2` Pin `418e9717564a895214275e088ea7075b8ac88f64` bei identischen Eingaben, Sensorinformationen, Planung, Geometrie und Budgets vergleichen. Begründete Kandidatenintegration im vorhandenen Explorer, Regressionen, isolierter echter Humble-Build und Originalnachweise.

## Abnahme und Entscheidung

Ringfrontier, konkave Grenze, langer Rand mit mehreren nützlichen Beobachtungspositionen, blockierter bester Kandidat mit Alternative, Kartenwachstum, neue Beobachtung an besuchter Stelle und fehlende optionale Semantik prüfen. Kandidaten müssen an der Beobachtungsgrenze liegen, volle Kartenidentität/-geometrie, Ursprungrotation, Scope, echte Sensorreichweite/Sicht und Frische berücksichtigen. Gemeinsame vorhandene Footprint-/Nav2-Prüfungen erhalten. Mehrere Kartenstände erzeugen geeignete planbare Folgeentscheidungen; Zahl der Punkte allein genügt nicht.

Externen Kern übernehmen, wenn alle Pflichtfälle und mindestens ein belegter Vorteil bestehen, ohne zweiten Navigations-/Missionsapparat. Andernfalls gemäß MASTERPLAN den konkreten Blocker oder die eigene Kandidatengewinnung begrenzt korrigieren und erneut vergleichen. Lizenz und Pin/Änderungen nachvollziehbar dokumentieren.

## Grenzen und Rückfall

Keine Hardware, Roboternetzverbindung, Deployment, Push/Merge oder automatischer AP-05-Übergang. Missionseigene Erledigungs-/Wiederbeobachtungspolitik und Gesamterfolg bleiben AP-05; geschlossene vollständige Missionskette und Realqualifikation AP-06. Keine neuen Freiraumannahmen, gelockerten Reserven oder Quellenfristen. Rückfall nur eigene AP-04-Commits revertieren; AP-01–03 und fremde Arbeit erhalten. Tatsächliche Blocker konkret benennen und unabhängige Schritte weiterführen.

## Softwareabschluss

AP-04 software_geprüft im Softwarecommit `5ee313b`. Der gepinnte Fremdkern wurde unverändert gebaut und verglichen; wegen belegter Ring-/Langrandgrenzen wurde die im Masterplan erlaubte begrenzte Eigenkorrektur gewählt. Alle sieben Pflichtfälle, elf Kartenstände, echte Nav2-Planung, 27 neue Regressionen und frische Builds sind belegt. Ergebnis, Originalbelege, Plattform-/Sensor-/Hardwaregrenzen und Rückfall ausschließlich im [STATUS](STATUS.md) und der [AP-04-Evidenz](evidence/ap04-20261003/README.md). Keine Hardwarewirkung oder automatische AP-05-Implementierung.
