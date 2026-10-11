# AP-06: technische Gegenprüfung vor dem Jetson-Test

Stand: 11.10.2026. Auftrag: Slot-Strategie prüfen, Fehler reproduzieren,
Korrekturen und Alternativen beurteilen, bevor der Kandidat auf dem Jetson
qualifiziert wird. Bezug: MASTERPLAN v1.5, WE-M0/M3/M4/M5/M6; keine WE-M7-Abnahme.

## Urteil

**Der bisherige LAB-Slotkandidat enthält nachweisbare Ablauf- und Routenfehler.
Fünf Fehlergruppen sind gezielt korrigiert; eine weitere Lücke betrifft die
CI-Testauswahl. Die breite Regression und eine autonome Gesamtfahrt sind
weiterhin nicht vollständig bestanden.** Der Quellstand ist ein korrigierter
Softwarekandidat, kein abgenommenes Fahrprodukt.

Für einen Nicht-Informatiker: Der Roboter konnte einen bereits zurückgelegten
Wegteil versehentlich erneut prüfen, als müsse er dort umdrehen. Nach einer
Pause konnte er eine schon erreichte Position vergessen und die Fahrt nochmals
anfordern. Zudem konnte das Aufgabenlimit die Fortsetzung einer bereits
begonnenen Drehung verhindern. Diese Fehler sind behebbar, ohne die Sensoren
oder deren Schutzwirkung abzuschalten.

Daneben gibt es ein **anderes, weiterhin offenes Startproblem**: In den
vorliegenden Gesamtprüfungen wurden die nötigen Rad-/Lagesensor- und Kartendaten
nicht durchgehend rechtzeitig bereitgestellt. Die Mission kam deshalb gar nicht
bis zur autonomen Zielkette. Ein anderer Explorer allein behebt diesen unteren
Datenpfad nicht. Als nächstes muss dessen Ursache im gerätefreien Prüfstand
lokalisiert und behoben werden. Ein weiteres pauschales Lockern der
Explorerregeln ist dafür kein nachgewiesener Lösungsweg.

## 1. Prüfgegenstand und Versionsbindung

| Gegenstand | Exakter Stand / Bedeutung |
|---|---|
| Geprüfte Lieferung | Dokumentation `d2978d4855718bd843b208fa56c2fbaf47f42eef`, Produkt `12de37e89fed2a30d45fa3691919c2cc415560c9` |
| Auditbasis | Separater Worktree, Branch `fix/ap06-slot-audit`; ursprünglicher Worktree/Install erhalten |
| Korrigiertes Produkt | `900ce5d8a3f56dd5f59f6b16462d3a9cb1cc8a53`; Dokumentation/CI folgen separat |
| Historischer Vergleich | `60e894cd6638c2d977b0fca6e352fe7b5aedae44`: 2.976 Regressionen, A/B/C 0/3, Cancel-/HOLD-Stopp 2/2; kein Ergebnis des Slotkandidaten |
| Veröffentlichte ältere Basis | `22a4b76bc4fd23f83227d85b6a5b5b4c303e90f7`; Bundle enthält auch die später entstandenen Slotänderungen |
| Plattform | ROS 2 Humble, Ubuntu 22.04, x86_64, Python 3.10 im isolierten Container; kein Jetson/ARM64-Test |

Vor dem Test waren am Produktcommit keine lokalen Änderungen vorhanden.
Submodulzeiger `src/behaviortree_ros2`:
`6c6aa078ee7bc52fec98984bed4964556abf5beb`, im Worktree nicht ausgecheckt.
Der native Unterbau stammt aus dem zuvor separat gebauten, gepinnten
37-Pakete-Install; in diesem Audit wiederverwendet, nicht komplett neu gebaut.
Die 36 über ament aufgelösten nativen Präfixe sind erneut gebunden; das
37. Paket `rsl` ist ein reiner CMake-Install und separat gehasht
(`native-prefix-bindings.json`). System-ROS und deklarierte Python-Abhängigkeiten
sind ebenfalls Unterbauten.
Keine zweite physische Maschine und kein ARM-Build sind dadurch bewiesen.

Neu gebaut: alle 15 Produktpakete einschließlich `robot_description`, mit
separaten Build-/Install-/Logpfaden. Nachweis: 15 Kandidatenpräfixe,
163 bytegleiche Quelle-/Install-Dateien, 15 tatsächlich importierte Module
inklusive C-Sweep-Erweiterung. Das Host-Worktree-Gitverzeichnis ist im Container
nicht sichtbar. Daher: Commit auf dem Host erfasst, jede erfasste versionierte
Datei im Container per SHA256 nachgeprüft.

Prüfumfang: Anforderungen und Slot-Elternablauf, laufende Routenprüfung,
HOLD/Quellenwiederprüfung, Budgets, Fehlerklassifikation, Launchverträge,
Buildbindung, Regressionen und vorhandene Gesamtlogs. Technische Gegenprüfung
in Auditorrolle, keine personenunabhängige Zertifizierung und keine komplette
Prüfung von iOS, Netzwerksicherheit, Sprachplanung oder Kunden-Raumsemantik.

## 2. Bestätigte Fehler und ausgeführte Korrekturen

F1–F5 betreffen Produkt `12de37e`; Korrektur in `900ce5d`.
Gegenfälle: `src/explore/test/test_lab_slot_audit.py`, ausgeführt gegen die
installierten Produktmodule. Transport/Bewegung und Testzeit sind ersetzt;
die geprüften Elternentscheidungen, Routen- und Beobachtungsfunktionen sind echt.

### F1 – Restweg wegen bereits passierter Punkte verworfen (hoch)

**Quelle:** `lab_slots_runtime.py::live_guard` und
`metric_frontier_runtime.py::_metric_validate_nav_plan` unter `src/explore/explore/`.
Die Liveprüfung berechnete die Bewegung auf dem vollständigen alten Nav2-Pfad
samt vergangener Wegpunkte und nahm externe Vororientierung an. Der laufende
Regler fährt den verbleibenden Weg. So entstand eine nicht verlangte Rückwendung.

**Beleg:** `test_live_remaining_route_does_not_invent_a_turn_towards_passed_waypoints`.
Der echte anfängliche Routenprüfer akzeptiert dieselbe gerade Passage;
die alte Liveprüfung meldet anschließend `lab_route_outside_scope`.
**Korrektur:** Gemeinsame Methode `_metric_nav_plan_route` für bestehenden
Pfadvertrag, Projektion und Abschneiden passierter Punkte; live natives Lenken
ohne zusätzliche externe Vororientierung.
**Abschluss:** Gültiger Restweg akzeptiert, Grenz-/Vertragsverletzungen weiter
abgelehnt. Softwaregeprüft; keine reale Türpassage bewiesen.

### F2 – Livepfad umgeht Teile des Vertrags und die Zieldrehung (hoch)

**Quelle:** ebenfalls `live_guard`. Beim ersetzten Pfad prüfte die alte Fassung
nur den übergeordneten Frame und endliche Positionen. Einzelne Pose-Frames,
Zielorientierung und abschließende Drehung des ganzen Körpers fehlten.
Die aktuelle Körpergrenze blieb überwacht; keine reale Grenzüberschreitung
wird aus diesem Befund behauptet.

**Belege:** `test_live_changed_path_checks_final_heading_against_scope` und
`test_live_replacement_path_keeps_the_native_plan_contract`.
**Korrektur:** Gemeinsamer nativer Pfadvertrag; Körperprüfung der Zieldrehung
am tatsächlich berechneten RPP-Haltepunkt mit unveränderten Reserven.
**Abschluss:** Falscher Einzel-Frame/Zielwinkel und grenzverletzende Zieldrehung
abgelehnt; gültige Fahrt weiter möglich. Die Gesamt-Frame-/NaN-Fälle sind
Kontrollen des bereits vorher vorhandenen Verhaltens.

### F3 – Pause nach Ankunft verliert Beobachtung oder wiederholt Fahrt (hoch)

**Quelle:** `lab_slots_runtime.py::execute_lab_slots`, Kindende → Halt →
Beobachtung. HOLD während der Beobachtung konnte eine erreichte Aufgabe als
unerreicht verbuchen. Verzögerte Haltbestätigung speicherte nur ein nochmals
anzufahrendes Ziel, obwohl das Nav2-Kind bereits erfolgreich beendet war.

**Belege:** `test_hold_after_arrival_preserves_observation_task_and_does_not_navigate_again`
(kurze/lange Pause),
`test_delayed_stop_confirmation_after_arrival_never_resends_the_terminal_child`.
**Korrektur:** Gespeicherte Arbeit enthält terminales Kindresultat und
ursprüngliches Beobachtungsende. Nach Ankunft ausschließlich noch zulässige
Beobachtung fortsetzen; kein zweites Nav2-Ziel. Lange Pause erzeugt weder
Kartengewinn noch neue Frist.
**Abschluss:** Eine Anforderung/ein Versuch, bei rechtzeitigen neuen Kartenzellen
eine Ankunft/eine Beobachtung; HOLD-Ursache erhalten. In-Prozess-Nachweis;
persistierte Wiederaufnahme nach Prozessneustart und ganze reale HOLD-Fortsetzung offen.

### F4 – Aufgabenlimit beendet Fortsetzung des letzten Startscans (mittel)

**Quelle:** Budgetprüfung am Schleifenanfang in `execute_lab_slots`.
Begonnener Scan zählte als Versuch, war aber keine gespeicherte Nav2-Zielaufgabe.
Bei erreichtem Aufgabenlimit brach die nächste Runde ab, selbst wenn nur der
Restwinkel nach HOLD oder kurzer Datenlücke fehlte.
**Beleg:** `test_initial_scan_resumes_even_when_it_uses_last_task_budget`, beide Auslöser.
**Korrektur:** Begonnener Scan läuft mit ursprünglicher Frist und gemessenem
Restwinkel weiter. **Abschluss:** Zwei Teilaufrufe, ein Versuch, zweiter Winkel
`2π − 0,2`; kein neues Zeit-/Aufgabenbudget.

### F5 – Gelatchter Quellenfehler als kurze Datenlücke eingeordnet (mittel)

**Quelle:** `lab_slots_runtime.py::recovery_kind`. Nur
`encoder_config_fault_latched` wurde geprüft. Tatsächliche Meldungen enthalten
bei diesem Wert `false` dennoch `encoder_timing_recovery.fault_latched=true`;
auch `feedback_output_fault_latched` fehlte.
**Beleg:** `test_known_encoder_or_output_latch_is_not_treated_as_a_short_source_gap`;
verschachtelter Encoderzustand zusätzlich in den alten Gesamtlogs belegt.
**Korrektur:** Alle drei expliziten Latches terminal einordnen.
**Abschluss:** Keine Bewegung, kein sinnloses 30-Sekunden-Warten, Fehlerflag
unverändert. Die Schutzkette blockierte bereits; diese Änderung entsperrt sie nicht.

### F6 – CI enthält die neuen LAB-Testdateien nicht (mittel)

**Quelle:** `.github/workflows/hwt601-we.yml`, manuelle pytest-Auswahl im
`contracts`-Job. Trigger auf `src/explore/**` ersetzt keine Testauswahl.
**Korrektur:** `test_lab_slots.py`, `test_lab_slot_audit.py`,
`test_metric_sensor_guarded_start.py` und
`robot_navigation/test/test_sensor_guarded_mapping_launch.py` aufnehmen.
**Abschluss:** YAML/Shell gültig, Pfade vorhanden, lokal ausgeführt/gesammelt.
Remote-GitHub-CI mangels Veröffentlichung nicht ausgeführt; kein Remote-Grün behauptet.

## 3. Prüfergebnisse und Grenzen

| Prüfung | Ergebnis | Aussage |
|---|---|---|
| Finale 13 Gegen-/Kontrollfälle gegen altes Produkt `12de37e` | **11 fehlgeschlagen, 2 bestanden** | F1–F5 reproduzierbar, vorhandene Frame-/NaN-Kontrollen bleiben grün |
| 13 neue und 33 vorhandene Slotfälle gegen `900ce5d` | **46 bestanden** | Gezielte Korrekturen funktionieren im tatsächlichen Elternablauf mit ersetztem Bewegungstransport |
| Breite Regression gegen `900ce5d` | **3.128 bestanden, 5 fehlgeschlagen**, 0 Setupfehler/Skips; 637,51 s | Kein insgesamt grüner Regressionsnachweis |
| Dieselben fünf auffälligen Fälle gezielt gegen `12de37e` | **2 bestanden, 3 fehlgeschlagen** | Quellenzeitprobleme auch im Vorgänger reproduziert |
| Dieselben fünf Fälle gezielt gegen unverändertes `900ce5d` | **5 bestanden** | Schwankendes Ergebnis; kein dazwischen erfolgter Produktfix, ursprünglicher Gesamtlauf bleibt negativ |
| Vier in CI ergänzte Testdateien lokal | **70 bestanden**, YAML-/Shellprüfung positiv | Enthält die 46 oben; keine zusätzlichen 70 unabhängigen Beweise, Remote-CI offen |

### F8 – Regressionsprüfung zeigt nicht stabil reproduziertes Zeitverhalten (hoch, offen)

Die fünf konkreten Fehlschläge im breiten Lauf:

1. `test_metric_public_observation.py::test_public_view_does_not_require_private_ledger_epoch_expiry[ap06_a55_selection]`:
   erwartete bereits bewiesene kurze Beobachtung fehlt; stattdessen Vorschlag,
   der noch einen nativen Plan benötigt.
2. `test_stage3_tf_reception.py::test_current_tf_received_without_executor_and_missing_tf_never_restamped`:
   TF-Freigabe trotz laufendem Testsender nicht rechtzeitig vorhanden.
3. `test_ap06_device_isolation.py::test_original_imu_writer_pause_is_isolated_from_encoder_acquisition[True]`:
   mindestens ein ungültiger Encoderzustand trotz isolierter IMU-Ausgabe.
4. `test_ap06_device_isolation.py::test_real_encoder_source_survives_supervisor_interpreter_pause[False]`:
   gemessene Radquellstempellücke **0,29804 s**, gefordert höchstens **0,18 s**.
5. Derselbe Test mit `[True]`: innerhalb seiner ursprünglichen Startfrist
   nicht genügend echte Radproben empfangen.

Die drei Gerätefälle scheitern auch im gezielten alten Stand; die beiden
anderen Fälle bestehen dort. Im gezielten Kandidatenlauf bestehen danach alle
fünf ohne weitere Produktänderung. Die betroffenen Auswahlfunktionen sind
gegenüber dem Vorgänger AST-gleich, TF-Diagnostik, Basisquelle und Prüftreiber
bytegleich (`unchanged-functions-and-contracts.json`). Daraus folgt keine
bewiesene neue Slotregression, aber auch keine Entwarnung: Reihenfolge,
Rechenzeit und Quellenbereitstellung sind noch nicht ausreichend auseinandergehalten.

**Lösung und Abschluss:** Ersten divergierenden Auswahlschritt samt realem
Auswahlbudget erfassen; DDS/TF-Empfang und Quellzeitfolge bei demselben
Gerätefall korrelieren. Reine Entscheidungstests dürfen kontrollierte Zeit
verwenden, die separaten realen Zeitbedingungen müssen dabei unverändert
geprüft werden. Keine Fristverlängerung, Entfernung des Tests oder Wiederholung
bis zum gewünschten Ergebnis als Fehlerbehebung. Schließung erst nach
nachgewiesener Ursache/Korrektur und bestandenem maßgeblichem Gesamtlauf.

Der breite pytest-Lauf umfasst Produktpakete und Simulationswerkzeuge; er
startet nicht automatisch die langen ursprünglichen Gesamtmissionen. Zahlen
nicht addieren oder als gefahrene Meter/Kartenqualität lesen. Zwischenfehler,
Fixture-Korrekturen und Wiederholungen bleiben im Roharchiv erhalten.
Der erste Restweg-Gegenfall verwendete zu weit auseinanderliegende Punkte
und scheiterte nach der Korrektur zusätzlich am vorhandenen 0,4-m-Pfadvertrag.
Er wurde durch einen dichten nativen Pfad mit aktueller Position ersetzt und
um die echte anfängliche Routenakzeptanz verstärkt; final dieselbe Testdatei
gegen altes und neues Install ausgeführt. Dieser Zwischenfehler ist archiviert.

Build: 15 Produktpakete sowie echte TF-Prüfsonde gebaut. Native 37 Pakete
unverändert wiederverwendet. Keine Änderung an Geschwindigkeiten,
Encoder-/Frischegrenzen, VL53-Schwellen, Kartenstempeln oder Abnahmekriterien.
`ap06_product_scenarios.json`, `ap06_closed_product.py`, `ap06_world.py` und
`ap06_isolation.py` sind gegenüber der Lieferung bytegleich; Hashes im Beleg.

## 4. Offene Ursache der nicht startenden Gesamtmissionen (F7, hoch)

Die vorhandenen finalen Gesamtläufe gehören **zu `12de37e`, nicht `900ce5d`**:
A/C scheitern vor Missionsstart an `SLAM initial actual map`, B an
`real scope and HWT readiness`. Cancel/HOLD ebenfalls vor Bewegung/Injektion:
0/3 positive Gesamtfälle qualifiziert, 0/2 neue Stoppqualifikationen;
kein daraus belegtes Stoppversagen nach Bewegung. Für den Auditkandidaten
liegt noch kein neuer Gesamtmissionsnachweis vor.

Erneute Auswertung originaler Rohjournale:

| Alter Fall | Quellenbefund | Unveränderte Grenze |
|---|---|---|
| A | Frühe Encoderlücke 0,62847 s; danach dauerhaft ungültiger Radzustand | Kontinuität 0,18 s |
| B | Erster zeitlicher Verwerfungsgrund: Lücke 0,82659 s | Kontinuität 0,18 s |
| C | Paarlesung bis 0,26207 s in fehlerhafter Startphase | Paarlesung 0,12 s |
| Cancel | Erste verworfene Lücke 0,18568 s | Kontinuität 0,18 s |
| HOLD | Paarlesung bis 0,32713 s | Paarlesung 0,12 s |

Das äußere `encoder_sample_dt_s` zeigt nach Latch teilweise die letzte akzeptierte
Probe. Für den ersten Auslöser `encoder_timing_recovery.first_timing_rejection`
mitlesen. Einzelne später unauffällige äußere Werte widerlegen die Lücke nicht.
SLAM meldet volle Warteschlangen beziehungsweise Scans vor dem TF-Puffer;
zeitlicher Datenfluss gestört, aber keine alleinige Ursache aller Startfehler
bewiesen. Langsame Executoraufrufe sind belegt; Produzent, Publikationsweg,
Scheduler oder Rechenlast als genaue Ursache noch nicht vollständig zugeordnet.

Die Journale erfassen nicht sämtliche Roh-HWT-, Radodom- und Verbraucherzeiten
lückenlos. „Nur CPU zu langsam“ oder „Modbus defekt“ wäre daher unbelegt.
Feedback- und Sensorausgabe sind bereits teilweise isoliert; pauschal weitere
Prozesse vorzuschlagen ersetzt die fehlende Ursachenmessung nicht.

**Abschluss F7:** Im gleichen gerätefreien Prüfstand bei Nullkommandos zunächst
Erfassungsbeginn/-ende, Quellstempel, Publikation und Empfang entlang Encoder →
Radodom/HWT → Fusion/TF → Scan/SLAM korrelieren. Auch Basisstatus, Roh-HWT,
Shadowstatus, Radodom, `/tf`, `/tf_static`, `/scan_normiert` vor Start durchgehend
aufzeichnen. Ersten Zeitbruch lokalisieren und am verantwortlichen Übergang
korrigieren. Der passive HWT-Recorder hilft, seine bisherige Themenauswahl allein
ersetzt keine vollständige aktive Kettenaufzeichnung. Danach unveränderte
Quellenbedingungen und ursprüngliche Gesamtfälle erfüllen; keine künstliche
Stempelauffrischung oder Fehlerlöschung.

## 5. Weitere Abnahmegrenzen

- **Simulations-/Realprofil unterscheiden sich:** Simulation setzt
  `metric_path_validation: rpp_rollout`, realer Standard bleibt `conservative`.
  Neuer Restweg-Gegenfall bindet ausdrücklich `rpp_rollout`. Die dortige
  Trackingreserve 20 mm/0,05 rad ist kein real gemessener Amadeus-Wert.
  Tatsächliches Zielprofil/Tracking vor Passagenprüfung binden; keine stille
  Übernahme der Simulationskonfiguration oder Verkleinerung der Reserven.
- **HOLD-Stopp ist keine ganze Wiederaufnahme:** Originaldriver setzt
  `hold_resume_qualified=False`. Positiver Stopp beweist keine erneute
  Zielanfahrt, Beobachtung und vollständigen Missionsabschluss.
- **Exitcode ist kein Missionsurteil:** Driver kann mit negativem Ergebnis
  Prozesscode 0 liefern. Kriterien und `passed` in `result.json` prüfen.
- **Slots entlasten die Auswahl, nicht alle Verarbeitung:** Sensoren, SLAM,
  Nav2 und Schutzkette müssen weiterlaufen.
- **Reale Abnahme gesondert:** Keine neue volle Drehung, Türpassage, autonome
  Beobachtungskette oder Kartenqualität auf dem echten Amadeus nachgewiesen.
  Reale Bilder, Karten und Bags liegen weiterhin außerhalb Git.

## 6. Alternativen und Reihenfolge vor dem Jetson-Fahrtest

| Alternative | Bewertung / Bedingung |
|---|---|
| Korrigierte Slots behalten, unteren Start-/Datenpfad zuerst qualifizieren | Empfohlen. Gezielte belegte Korrekturen; F7 durch vollständige Zeitkette schließen. |
| Gemessenen Engpass entkoppeln oder leistungsfähigeren Prüfhost vergleichen | Erst nach Lokalisierung. Bestehende Prozessaufteilung beachten; gleiche Quellenstempel, Grenzen, Welten und Abnahmen. |
| Erst Quellen/SLAM, dann ein gewöhnliches Nav2-Ziel, danach ganze Erkundung | Geeignete Diagnosezerlegung. Einzelnes vorgegebenes Ziel ist Unterbaunachweis, keine autonome Erkundungsabnahme. |
| Schlanken `explore_lite`-Kern wie bei OOMWOO vergleichen | Erst auf gesundem Amadeus-Unterbau aussagekräftig. Ersetzt weder Encoder/HWT/TF noch Schutzkette; ein aktiver Navigationsbesitzer, messbarer Erkundungsabschluss. |
| Vollständiger OOMWOO-Stack oder pauschales Entfernen der Sperren | Kein belegter Kurzweg. Andere Plattform/ROS-/Treiber-/Geometrieverträge; fehlende Positionskontinuität wird dadurch nicht repariert. |

OOMWOO-Verweise aus dem bereits vorhandenen Vergleich:
[`kaiaai/m-explore-ros2` bei `9279196`](https://github.com/kaiaai/m-explore-ros2/tree/9279196223699bf407f5ca7617d411c969aec2d1),
[`makerspet/oomwoo-ros2-tools` bei `d7f937d`](https://github.com/makerspet/oomwoo-ros2-tools/tree/d7f937d1d0fa0c17e9e3035b51446fab7014c7f3).
Keine erneute vollständige OOMWOO-Prüfung in diesem Audit.

1. Offene Regressionen und F7 gerätefrei klären; Quellen, TF und echte
   SLAM-Karte bei Nullkommandos stabil erreichen. Verantwortlichen Zeitübergang
   belegen und gezielt korrigieren.
2. Genau denselben Kandidaten durch unveränderte A/B/C-/Cancel-/HOLD-Fälle
   führen. Ganze HOLD-Fortsetzung zusätzlich prüfen: ein Bewegungsbesitzer,
   terminales altes Kind, ursprüngliche Budgets, erneute Beobachtung.
3. Danach autonome Zielsystemprüfung: separater ARM64-Build, Präfix-/Quellbindung,
   reale Sensorzeiten/Frames/Recorder, begrenzter Rundblick und Slotfahrt im
   bestehenden LAB-1-Auftrag. Früherer rein passiver ARM-Build wäre lediglich
   ein Portierbarkeitscheck.

Keine weitere pauschale Nutzerfreigaberunde nötig. Es fehlt technischer Nachweis,
nicht die bereits erteilte Laborautorisierung.

## 7. Belege, Übergabe und Rückfall

[Maschinenlesbarer Beleg](evidence/ap06-slot-audit-20261011.json).
Vollständige negative Gegenfälle, Zwischenfehler, JUnit, Buildlogs und
Quellbindung separat im Roharchiv. Bundle, Reviewpatch, SHA256-Liste und
Anleitung: `/workspace/slot-audit-results/`. Frühere Lieferung samt vollständigen
Originalgesamtlogs: `/workspace/lab-slot-results/`.

Kein Push/Merge, Jetsontransfer, Autostartwechsel oder reale Aktorbewegung.
Aktueller Iststand und **genau nächster Schritt** ausschließlich im
[STATUS](STATUS.md).

Rückfall nach bestätigtem Halt/Ende eigener Kandidatenprozesse: Auditcommit
im separaten Kandidaten revertieren oder erhaltene Installation verwenden;
Konfiguration erneut binden. Der alte Kandidat enthält die belegten Fehler
und wird durch Rückfall nicht zum abgenommenen Produkt. Fehlerflags,
Quellenzeiten und Budgets bleiben erhalten.
