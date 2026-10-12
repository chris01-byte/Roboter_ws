# AP-06: Fortsetzung der F7/F8-Korrekturprüfung am 12.10.2026

## Ergebnis und Geltungsbereich

Die vorhandene Encoderlösung wurde in der Historie nachgewiesen und erhalten.
Ein zusätzlicher Verzögerungspfad im Simulationsquellen-Executor ist ursächlich
korrigiert. Die bisherige positive Einzelprüfung reicht ausdrücklich nicht zur
Schließung von F7/F8: Auf demselben Kandidaten sind weitere reale Quellenpausen
und ein zusätzlicher A54-Entscheidungstestfehler belegt. Keine Gesamtfreigabe.

Auftrag: ausschließlich F7/F8, gerätefrei, unter MASTERPLAN v1.5/AP-06.
Keine Jetsonverbindung, Installation, Autostartänderung oder reale Aktorbewegung.
F1–F6, Mission → BT → Explorer → Nav2 → Schutzkette, Slot-Strategie und genau
ein Navigationsbesitzer bleiben erhalten. Keine Zeitgrenze, Welt, Akzeptanz,
Faultflag oder Versuchshistorie verändert; keine Zeitstempel aktualisiert.

## Prüfstand und Quellenbindung

- Ursprüngliche Auftragsbasis: Dokumentation/CI `1b3bc987913d518776f495fdc5b2e0cbabec383c`,
  Produkt `900ce5d8a3f56dd5f59f6b16462d3a9cb1cc8a53`.
- Übernommene F7/F8-Vorkorrekturen: Produkt `cf010a03c96ad981516b52d96f5c21dda78c4369`,
  Dokumentation `6e392503804682d1870e8dff39e66c5deafb04b3`.
- Separater Branch `fix/ap06-source-timing`, Produkt
  `0b71d8f3c4e461ac3274ceb7c4df8af55ff0e0b1`.
- Sauberer Ausgangszustand, Submodulstand und 3.742 produktseitige Dateihashes
  in `baseline-identity.json` und `source-identity.json` dokumentiert.
- Humble/Python 3.10.12/x86_64, Fast DDS, isolierter Container ohne Netzwerk;
  Build/Install/Log separat unter `/audit/source-timing-*`. Alle 15 Produktpakete
  und native TF-Sonde gebaut. 37-Pakete-Unterbau wiederverwendet.
- 15 private Paketpräfixe, 163 bytegleiche Quell-/Install-Dateien und 18 geladene
  Module geprüft. Bestehende Installationen/Worktrees unverändert erhalten.
- Äußere cgroup: fünf sichtbare CPUs, Quota `400000 100000`; innerer Container
  meldet dagegen `max 100000`. Die innere Statistik allein schließt Drosselung
  des Vorfahren nicht aus. Keine automatische Zuschreibung der Quellenfehler
  an diese Quote. Neue zeitgestempelte äußere Messung separat erhalten.

## Die frühere Encoderlösung ist bereits enthalten

Die Umstellung von RPM-Integration auf absolute Zähler 0x000A/0x000B mit
atomaren Paarlesungen stammt aus `9f7d339b2652cf6f18173c1b53787c7532e04236`.
Der H4-Beleg `7eeed4be766c30883c863133f84d40e9809d2748` dokumentierte die
Anfahr-/Stopverbesserung. `encoder_odometry.py` ist zwischen diesem Stand und
dem neuen Kandidaten bytegleich (SHA256
`a49b82dfd937c40259b13bc16b1e42945c0f2a50017a6f7395476b4a972aeb94`).

Die späteren HWT-Anforderungen prüfen zusätzlich zeitliche Kontinuität:
0,18 s Probenabstand und 0,12 s Paarlesung. Absolute Zähler verlieren bei einer
Wartepause nicht automatisch den gesamten Radweg; daraus folgt aber keine
zuverlässig zeitlich zuordenbare Zwischenbewegung für Fusion/TF. Die frühere
2-s-Integrationsgrenze wäre deshalb kein Ersatz für den heutigen Vertrag.

Die reale positive Quelle vom 10.10. benutzte separate Base-/HWT-Prozesse und
CPU-Zuordnung sowie ein ausdrücklich privates Vorlaufprofil. Sie belegt keine
vollständige autonome Mission. Der Simulator betreibt drei Quellenexecutoren
in einem Prozess. Die echten Base-/HWT-Einstiege verwenden bereits normales
`rclpy.spin(node)`; die hier korrigierte positive Timeoutschleife war im
Simulationsadapter zusätzlich eingeführt.

## F7: belegter Unterbefund und kleinste Änderung

### Ursache und Stelle

`tools/simulation/ap06_closed_product.py::device_process` rief je Quellenschritt
`ex.spin_once(timeout_sec=.05)` auf. Humble rclpy 3.3.21 erzeugt dafür in
`executors.py::_wait_for_ready_callbacks` jedes Mal einen zusätzlichen nativen
Timeout-Timer. Die Quellen verfügen bereits über ihre eigenen periodischen
Timer. Die zusätzliche Allokation liegt im zeitkritischen Erfassungsthread.

Im instrumentierten Nullkommando-Start `startup-baseline-native/` wurden sechs
langsame Timerkonstruktionen, maximal 0,472522 s, beobachtet. Der erste ungültige
Base-Update folgte einem nativen Warteabschnitt bis 0,601222 s; seine Paarlesung
selbst brauchte nur 0,000444 s. Das identifiziert native Verzögerungsgrenzen,
beweist jedoch nicht exklusiv einen bestimmten GIL-/OS-Lockmechanismus.
Der 100-Hz-Nativsampler lief hinterher und beeinflusste die Laufzeit; seine
Stacks werden nur als ergänzende Diagnose verwendet.

### Reproduzierbarer Gegenfall

`tools/simulation/test_ap06_source_executor.py` betreibt die echten Base-/HWT-
Nodes am vorhandenen simulierten FC03-Endpunkt. Nur die zusätzliche native
50-ms-Timeout-Timerkonstruktion erhält nach 1,5 s einmal 300 ms tatsächliche
Verzögerung. ROS-/Sensortimer, Originalmesszeiten und Grenzen bleiben real.

Vorher: 4.044 solche Allokationen, gemessene Injektion 0,303045 s, erste
abgelehnte Quellenlücke 0,304389 s bei 0,18 s; Paarlesung 0,000138 s. Der äußere
`encoder_sample_dt_s` zeigte noch 0,059995 s. Maßgeblich ist hier zusätzlich
`encoder_timing_recovery.first_timing_rejection`. Test rot, 25 Radproben.

Nachher: `ex.spin_once()` wartet auf die vorhandenen periodischen Timer.
Der unnötige Allokationspfad entfällt; kein neues Clock-/Sensorverhalten.
Gegenfall einzeln grün mit 70 tatsächlichen Radproben, maximal 0,066570 s Quellstempelabstand, innerhalb der
unveränderten 180 ms und regulärem Prozessende. Es wurden weder die fehlerhafte
Probe zugelassen noch der Test übersprungen. Der spätere gezielte Lauf desselben
Kandidaten wurde trotzdem rot und bleibt ausdrücklich erhalten.

Der erste Versuch des neuen Tests hatte einen getrennten Setupfehler: ein
inline erzeugtes multiprocessing.Value verlor im Elternprozess seine Referenz
vor dem Spawn. Beleg `timeout-setup-error.*`; durch gehaltene Elternreferenz
korrigiert. Dieser Setupfehler ist kein Produktnachweis. Der anschließend rote
Vorherfall und grüne Einzelfall verwenden dieselbe korrigierte Testfassung.

### Verbleibender Fehler, keine Schließung

Im gezielten Lauf `focused-final.*` scheitert derselbe neue echte Quellenfall
ohne Timerinjektion: 20 Radproben, erste Paarlesung 0,994080 s und Probenlücke
0,751707 s; alle Timeout-Allokationen bereits null. Der ursprüngliche äußere
Probenabstand blieb bei 0,060063 s stehen. Das widerlegt einen Gesamtabschluss.

Weitere gebundene Diagnose `startup-candidate-native/`: erster ungültiger
Base-Update bei monoton 81502,964989 s, vorheriger Update über 0,291479 s,
HWT-Poll über 0,419703 s und natives `WaitSet.get_ready_entities` über
0,208504 s. Die letzte Queueübergabe war kurz. Ein anderer 30-s-Quellenlauf war
gesund. Beides zählt; keine Ursache aus dem grünen Lauf ableiten.

Die abschließende erweiterte Nullkommandomessung
`startup-final-native-diagnostic/` verbindet Originalstempel, Queue, DDS und
Empfang: letzte gültige Radprobe nach 0,006681 s ausgeliefert; nächste
abgelehnte Probenlücke 0,678809 s, Paarlesung 0,027836 s. Der erste Bruch liegt
wieder in der Produktion. Vor `_poll_encoder_feedback` vergehen im Base-Update
rund 0,613 s; gleichzeitig liegt ein `Timer.__enter__`-Aufruf über 0,522244 s.
Die gemessenen Queue-Feeder-Threadstarts benötigen höchstens 0,002904 s;
kein entsprechender langer nativer Logaufruf wurde erfasst. Diese Daten
begründen weder eine neue Prozessschicht noch eine pauschale Logging-Abschaltung.

Die äußere cgroup-Drosselung überlappt diesen ersten Fehler: zwischen monoton
82450,959588 und 82451,657614 steigen `nr_throttled` von 7443 auf 7446 und
`throttled_usec` von 603993165 auf 604771663. Die kumulierte Drosselzeit ist
keine direkt dem Quellen-TID zuordenbare Einzelwartezeit. Das schließt den
Verursachernachweis noch nicht ab. Ein erster Zusatzmessversuch mit einem
Python-Loggerwrapper veränderte dessen Callsite-Identität und scheiterte schon
bei der Initialisierung. Er ist als ungültige Diagnose getrennt erhalten;
der abschließende Versuch benutzt diesen Wrapper nicht.

Eine diagnostische Zusammenlegung der vorhandenen Executoren löste den Fehler
auch ohne die zusätzlichen Timeout-Timer nicht (`startup-shared-periodic/`).
Sie wurde nicht in das Produkt übernommen. Kein weiterer Prozess/Navigator.

Ein zusätzlicher Nullkommando-Start beschränkt den Prüfstand ausdrücklich auf
vier CPUs (`taskset -c 0,1,2,4`), bestehende Ausgabeprozesse auf `[0,1,2]` und
Erfassung auf `[4]`. Auch dieser Versuch scheitert vor Missionsstart: erste
Quellenlücke 0,873376 s, Paarlesung 0,051037 s. Gleichzeitig bleibt die
unabhängige äußere 100-ms-Messung zwischen 82972,035990 und 82972,824276 s
für 0,788286 s aus; der äußere Quoten-Zähler registriert in diesem Intervall
nur 0,029967 s zusätzliche kumulierte Drosselzeit. Eine reine Quotenänderung
ist daher keine belegte Lösung. Der gemeinsame Aussetzer spricht für einen
Einfluss außerhalb des einzelnen ROS-Prozesses, beweist aber weder den
exakten Virtualisierungs-/Schedulingmechanismus noch die Abwesenheit weiterer
Softwarefehler. Diese Diagnose verändert kein reales Profil.

## F8 und getrennte Ergebnisse

| Prüfung auf Produkt `0b71d8f` | Ergebnis |
|---|---|
| Gezielter Lauf einschließlich neuem Quellengegenfall | 98 bestanden, 2 fehlgeschlagen, 0 Skips |
| Vollständiger bisheriger Umfang plus neuer Gegenfall | 3.133 bestanden, 4 fehlgeschlagen, 0 Skips, 1 Warnung; 612,26 s |
| Genau die ursprünglichen fünf F8-Fälle | Jeweils 5/5 im gezielten und breiten Lauf; kein Stabilitätsabschluss |
| Unveränderte A/B/C-Gesamtmissionen | 0/3; jeweils `real scope and HWT readiness` vor Start |
| Unveränderte Cancel-/HOLD-Stoppfälle | 0/2; keine der vorgesehenen Injektionen erreicht |
| Vollständige HOLD-Wiederaufnahme | Nicht nachgewiesen; ursprünglicher Fall prüft nur Stopp |
| Reale Abnahme/Jetson/ARM64 | Nicht durchgeführt, außerhalb dieses Auftrags |

Cancel scheitert vor Missionsstart. Der HOLD-Fall erreicht 95,78° Startscan,
null Ankünfte/Beobachtungen, kein Nav2-Fahrziel und endet `hwt_terminal`.
Erster Auslöser ist `pose_missing_stale_or_invalid`, danach Wiederprüfung,
später `hwt_hold` und terminaler Quellenfehler. Die vorhandene Wiederprüfung
bleibt nachweislich aktiv; Gründe sind getrennt erhalten. Simulierter Radnachlauf
von 0,000114 m und eine kurze Drehung sind keine erfolgreiche Erkundungsfahrt.
66,68 % beobachtete Referenzfläche erfüllen die ursprünglichen 95 % nicht.
Null Endkommandos und beendete Kinder ersetzen nicht die fehlende Stoppinjektion.

Die vier breiten Fehlschläge sind separat zu bearbeiten, nicht im Auftrag
stillschweigend abgeschwächt:

- `test_short_departure_cannot_bypass_route_view_or_original_history[no_route]`
- derselbe Test `[no_view]`
- derselbe Test `[cooldown]`
- `test_decision_takes_real_waiting_wheel_without_executor_callback[False-fresh]`

Die ersten drei melden `frontier_candidate_processing_budget_exhausted`.
Der letzte meldet `raw_missing_stale_or_invalid`; ein grüner Empfang der
Radprobe garantiert im Test nicht gleichzeitig frische übrige Quelldaten.
Eine exklusive Ursache wird daraus noch nicht behauptet. Zusätzlich endet ein
Executor-Thread in `test_geometry_lock_waiters_cannot_starve_original_hwt_samples`
mit einer Warnung `AttributeError: 'NoneType' object has no attribute 'handle'`.
Keinen dieser Gegenbelege als bestanden oder als gelöst umdeuten.

Die neue Regression wird durch CI-Commit `664fce9` sowohl bei Änderungen
als auch in der expliziten Testliste ausgewählt. YAML und Erhalt aller vorherigen
Testpfade lokal geprüft; kein entfernter CI-Lauf behauptet. Dieser Commit ändert
keinen getesteten Produktcode.


Der zusätzliche A54-Test
`test_actual_a54_short_view_precedes_unproved_distant_approach_work` scheitert
im gezielten Lauf, weil der unbewiesene Fernanflug erreicht wird. Er gehört
nicht zu den fünf genau beauftragten Tests. Keine bestätigte Ursache aus einem
bloßen Wiederholungslauf; als separater Befund erhalten und nicht stillschweigend
durch kontrollierte Zeit oder weiteren Explorerumbau verändert.

## Reproduktion, Rückfall und Nachweisgrenzen

Rohbelege/Skripte: `/workspace/ap06-audit-results/source-timing-evidence/`.
`build.sh`, `focused-final.sh`, `full-regressions.sh`, `whole-cases.sh` enthalten
die tatsächlichen Aufrufe. Quellenbindung vor den Läufen; Ergebnisdateien und
Kriterien nach den Läufen lesen. Ein Driver-Exitcode 0 allein ist kein Nachweis.

Für den roten Timergegenfall Baseline `6e39250` in separatem Worktree verwenden,
die unveränderte neue Testdatei aus Produkt `0b71d8f` hinzufügen und gegen die
gebundenen vorhandenen ROS-Pakete ausführen. Für den Nachherfall vollständigen
Kandidaten verwenden. `src/` ist zwischen diesen beiden Ständen unverändert.
Build-/Quellbindung und alle roten Zwischenbelege bleiben in der Lieferung.

Korrekturcommit `0b71d8f`: nur zusätzlicher Quellen-Test und Simulator-
Executoraufruf. Rückfall durch Revert dieses Commits im separaten Kandidaten;
Bestandsinstallationen nicht überschreiben. Dies stellt auch den belegten
Allokationspfad wieder her. Kein Anlass für einen pauschalen Rücksprung auf
alte Encoder-/HWT-Zeitgrenzen oder einen ungeprüften Jetsontransfer.

F7-Abschluss verlangt weiterhin eine durchgängig innerhalb der bestehenden
Grenzen arbeitende Quellen-/TF-/Kartenkette und die unveränderten Gesamtfälle.
Für die verbliebene Verzögerung fehlt die eindeutige Aufteilung in tatsächliche
Rechenarbeit, GIL-/Lockwartezeit und äußeren Schedulingentzug. Frühere gesunde
Produktion mit Auslieferungslücke 0,302590 s bleibt ebenfalls ungeklärt.
Aktueller Iststand und genau ein nächster Schritt stehen ausschließlich im STATUS.

Maschinenlesbare Zusammenfassung mit Rohbeleg-Hashes:
[evidence/ap06-source-timing-20261012.json](evidence/ap06-source-timing-20261012.json).
Reproduzierbare lokale Lieferung: `/workspace/source-timing-results/README.md`.
