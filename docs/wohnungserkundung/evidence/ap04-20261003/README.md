# AP-04 – Frontiervergleich und Kandidatenabschluss, 03.10.2026

MASTERPLAN **v1.3**, WE-M3; Basis `495b538` (sauberer AP-03-Abschluss), Software **`5ee313b47ea2ef7c98554e42a9cae224a8a7d0ca`**, Branch `feature/frontier-candidate-core`, Worktree `/workspace/Roboter_ws-ap04`. Nutzerauftrag ausschließlich AP-04, gerätefrei. Kein Hardwarezugriff, Deployment, Push/Merge oder automatischer AP-05-Übergang. MASTERPLAN bleibt bytegleich.

## Entscheidung

**Die im Masterplan ausdrücklich erlaubte begrenzte Eigenkorrektur wird übernommen.** Der erste externe Kandidat `mertgulerx/frontier_exploration_ros2` bleibt exakt auf `418e9717564a895214275e088ea7075b8ac88f64`. Er wurde unverändert unter Humble gebaut: **134 gtest-Fälle bestanden**; colcon zählt einschließlich sieben Testlauf-Wrappern **141**, keine Fehler/Skipped. Diese Zahlen sind kein Frontier-/Fahrgesamtnachweis.

Im gemeinsamen Adapter schlägt sein einziger Ringvorschlag an `footprint_sweep_invalid` fehl; es entsteht kein zulässiger Alternativvorschlag. Am langen zusammenhängenden Rand liefert er nur eine Beobachtungsposition: **1,9 m** potenziell sichtbarer Rasterrand gegenüber **5,9 m** aus mehreren tatsächlich mit Nav2 planbaren Eigenvorschlägen. Er müsste seine Clusterrepräsentation um weitere Randpositionen erweitern. Sein `OccupancyGrid2d` ignoriert außerdem die Ursprungsrotation; die Vergleichsbrücke weist sie ausdrücklich zurück. Eine eigene Runtime-Fremdbibliothek samt API-Erweiterung bietet hier keinen belegten Vorteil gegenüber der kleinen Eigenkorrektur. Der Vergleich ist damit beendet; kein anderer Gesamtstack wird gesucht.

Der unveränderte AP-03-Eigenkern wurde vor der Integration aus seinem **installierten Originalmodul** geprüft: Ringfrontier → ein innen liegender Schwerpunkt → `approach_unavailable` → **null Ziele** ([Originalbeleg](ap04-original-baseline.json), [Rezept](ap04-original-baseline.py)). Die neue Gewinnung liefert echte freie Randpunkte in 0,8-m-Rasterbereichen, nähert sich zur bekannten freien Seite und durchläuft weiterhin dieselben vollständigen Karten-/Costmap-/Chassis-/Controller-/Nav2-Prüfungen. Kein Sicherheitsradius, Frischebudget oder unbekannter Außenraum wurde gelockert.

## Pflichtfälle und echte Planung

Alle drei Kerne erhalten dieselben Roh-/Costmapraster, Pose, Scope, Sensorinformationen, Mindestgröße, Annäherungs-/Suchabstände, Footprint, konservative Controllerhülle und Budgets. Historischer Schwerpunktkern, gepinnter Fremdkern und korrigierte Gewinnung unterscheiden sich nur in ihren Randvorschlägen; der gemeinsame Adapter prüft Zulässigkeit und sichtbaren lokalen Rand. Die Fremdbrücke verwendet die vom echten `get_frontier` gelieferte `center_point`-Randzelle mit demselben bekannten Standoff, statt das Fahrzeug auf dessen direkten Grenzgoal zu setzen. Keine Fremdmission, Suppression oder Nav2-Dispatch wird instanziiert.

Die synthetische Vergleichsspezifikation ist ausdrücklich **0,1-m-Raster**, endlicher **0,05–1,2-m-LiDAR**, 360 veröffentlichte Winkelbins, initiale Quellenzeit 100 s mit zugehöriger synthetischer Uhr, frische Empfangsproben, gemessene Fahrzeughülle und vorhandenes **5-s-Kartenbudget**. Beide Kandidatenquellen erhalten dieselbe Sensoransicht, keine versteckte Weltkarte. Das ist keine Messung der Roboterreichweite. Produktion verwendet tatsächliche Scan-/TF-Geometrie einschließlich ungültiger/Mastbins und die kleinere Grenze aus `range_max` und vorhandenem `door_lidar_max_range_m` (Default **4 m**); eigener Test prüft den 4-m-Cap, Montage und Maskierung.

[Vergleich über elf Kartenstände](ap04-final-comparison.json), [gemeinsames Werkzeug](../../../../tools/analysis/frontier_comparison/compare.py), [echte Nav2-Zusammenfassung](native-summary.json):

| Pflichtfall | Zulässige native Pläne: Original / Fremdkern / Korrektur | Beleg / Aussage |
|---|---:|---|
| Freie Insel mit Ringfrontier | 0 / 0 / **5** | Geeignete echte Randpositionen; 10,0 m potenzieller Rand sichtbar |
| Konkave Grenze | 1 / 1 / **9** | Kandidaten auf der tatsächlichen Grenze; 14,5 m statt 1,0/1,1 m Randabdeckung |
| Langer Rand | 0 / 1 / **6** | 5,9 m gegenüber 1,9 m mit derselben endlichen Sicht; mehrere räumlich getrennte Positionen |
| Bester Eigenvorschlag blockiert | 0 / 1 / **4** | Identisches zusätzliches echtes Costmaphindernis für alle Kerne; zulässige Alternative, 4,3 m sichtbarer Rand |
| Karte wächst, Ursprung verschiebt sich | 0 / 1 / **6 → 7 → 8** | Drei Revisionen mit gleichen Weltbezügen, anderen Abmessungen/Ursprüngen; passende Folgeentscheidungen |
| Neue Beobachtung an besuchter Stelle | 0 / 1 / **6 → 3 → 3** | Pose aus vorherigem ausgewähltem Ziel, geänderte lokale Kartenevidenz; Adapter speichert keine Erledigung |
| Optionale Semantik fehlt | 0 / 1 / **6** | Keine Portal-/Regions-/Raumdaten im Adapter; reine Metrik |

Die Zahlen sind **Pläne nach vollständiger Produktprüfung**, keine durchgeführten Fahrten. Der Sichtwert ist deduplizierte zuerst erreichbare unbekannte Rasterrandzellen × Auflösung, ein vergleichbarer konservativer Nutzenwert; keine neue gemessene Freifläche, Wohnungsabnahme oder Gesamterfolg. Alle Angaben gelten für die dokumentierte synthetische Sicht/Rasterung.

Für sämtliche **110** zugelassenen Adaptervorschläge über elf Kartenstände wurde echte `ComputePathToPose`-Planung mit **NavFn A*** ausgeführt. **74** tatsächliche Pfade bestehen die anschließende komplette Produktprüfung, davon **63** aus der Eigenkorrektur. Die übrigen **36** werden wegen unzulässiger Zielanfahr-/Drehgeometrie verworfen; Action-SUCCESS allein wird nicht akzeptiert. Der lange Rand besitzt auch nach dieser tatsächlichen Pfadprüfung mehr als die doppelte Sicht eines einzelnen Vorschlags. Jeder Pflichtfall/Kartenstand hat mindestens eine zulässige Eigenalternative. [Native Ergebnisdateien und alle Pfade](native-plans), Parametrierung und Planerlogs sind pro Fall erhalten. **Kein FollowPath, kein Twist-/Motorpublisher, kein Mission-/HWT-/Encoder-Gesundheitsdummy.**

Gedrehter Ursprung: Eigenvorschläge werden korrekt in Weltkoordinaten transformiert, einschließlich Normalen, Pose, Scope und Sicht; Rotationsäquivalenz am echten Produkt geprüft. Die unmodifizierte Fremdbrücke meldet `unsupported_origin_rotation` ([Beleg](ap04-origin-rotation.json)). Eine native Nav2-Abnahme gedrehter statischer Karten wird damit nicht behauptet.

## Produktänderung und Regressionen

`metric_frontier_candidates.py` ergänzt zustandslose Randgewinnung und LiDAR-Ersttreffersicht; `metric_frontier_runtime.py` trennt `_metric_candidates` von missionseigener `_metric_select`-Historie. Der vorhandene Annäherungshelfer erhält eine optionale kartenseitige Richtung, behält den tatsächlichen Roboter als Reachability-Seed. `metric_candidate_source` ist beim Start read-only: `boundary_samples` im expliziten metrischen Modus, `legacy_centroid` als Vergleich/Rückfall. `existing` bleibt Gesamtdefault. Kein neuer Navigator, kein zweiter Action-/Motorbesitzer.

Karte mit korrelierter Identität, Scope, gültige Pose und bestehende Roh-/Costmapbindung werden erhalten. Sicht endet an Wänden, erster unbekannter Zelle, Raster-/Scopegrenze und blockierten diagonalen Seitenzellen. Eine unbekannte Sensorursprungszelle oder Sicht unterhalb `range_min` wird nicht als Nutzen ausgegeben. NaN, Null, ungültige Strahlen, fehlende Montage oder veraltete/future Empfangs-/Quellzeiten sperren die Kandidaten. Die Rechnung ist begrenzt: 128 Randvorschläge, 4.096 Strahlen, 8.192 radiale Schritte / zwei Mio. Strahlrasterpositionen und vorhandenes Kartenbudget; Überschreitung liefert einen konkreten Fehler, keinen scheinbar erfolgreich leeren Bestand.

**27 neue echte Produktregressionen:** sieben Pflichtfälle, Rotationsäquivalenz, sieben Sensor-/Frische-/TF-Negativfälle, Wand-/Unknown-/Range-/Maskensicht, explizite Kandidatenkapazität, getrennte Historie, neue lokale Sicht nahe früherem Ziel, zwei echte ROS-Node-Read-only-Prüfungen, unbekannter Sensorursprung/Minimalreichweite, Sichtkapazität, Scope, Roh-/Costmapkontur, echter Scan-/4-m-Cap-/Montagevertrag und Verarbeitungsbudget selbst bei leerem Ergebnis. Uhren, Eingangssensoren und Raster sind synthetisch; die geprüfte Kandidaten-, Scope-, Sicht-, Route- und Parameterentscheidung stammt aus echten Produktfunktionen. Die CI führt die neue Datei tatsächlich mit pytest aus; passende Werkzeugtrigger ergänzt. GitHub Actions wurde nicht ausgelöst.

| Abschlussprüfung | Ergebnis | Originalbeleg |
|---|---:|---|
| Frischer aktueller Humble-Build mit echten Repo-/Nav2-Actions | **10 Pakete** | [Build](ap04-current-final-build.log) |
| Vier installierte Metric-/Map-/Motion-Dateien | **165 bestanden**, einschließlich 27 neuer Fälle | [Installtests](ap04-current-installed-regressions.log) |
| Betroffene Explore-/Map-/State-/Base-/Gate-/Missiontests | **1.636 bestanden** | [Gesamtlauf](ap04-current-affected-tests.log) |
| Registrierte colcon-Tests | **1.604**, 0 Fehler/Fehlschläge/Skipped | [Ergebnis](ap04-current-colcon-results.log), [Lauf](ap04-current-colcon-tests.log) |
| Frischer Produktbuild im nativen Nav2-Prüfimage | **8 Pakete** | [Build](ap04-native-product-build.log) |
| Gepinnter unveränderter Fremdkern | **134 gtest / 141 colcon**, 0 Fehler | [Build](ap04-upstream-build.log), [Tests](ap04-upstream-results.log) |
| CPP-Vergleichsbrücke zum wirklichen installierten Fremdkern | erfolgreich | [Build](ap04-probe-build.log) |
| Aktuelle und native Produktmodule | **bytegleich** zum gebauten Worktree | [Installquellen](ap04-installed-source-sha256.txt), [Snapshotvergleich](worktree-build-source-sha256.txt), [aktuelle Bindings](ap04-current-installed-bindings.log), [native Bindings](ap04-native-bindings.log) |

Testmengen überlappen und werden nicht addiert. Der unabhängige historische Python-3.12-JSON-Tiefenbefund bleibt in den AP-01-Belegen erhalten; hier wurde echtes Ubuntu/Humble mit Python **3.10.12** geprüft.

## Reproduktion, Abhängigkeiten und Lizenz

Aktuelle Regression: wiederverwendeter gerätefreier Container `ap03-current`, Ubuntu 22.04.5, rclpy **3.3.22**, NumPy 1.21.5, SciPy 1.8.0, pytest 6.2.5 ([Versionen](ap04-current-environment.txt)). Neues eigenes Build-/Installpräfix `ap04-current-*`, vor Build nur `/opt/ros/humble`, anschließend dessen echte Actions und Paketpräfixe. [Ausgeführtes Rezept](ap04-current-verify.sh).

Native Planung/Fremdkern: Container `ap03-nav2`, Ubuntu 22.04.5, rclpy **3.3.17**, gleiche Python-/NumPy-/SciPy-/pytest-Versionen ([Versionen](ap04-native-environment.txt)). Native Nav2 **1.1.20** aus dem bereits tatsächlich gebauten AP-03-Quellstand `3c3db59d6969d8ecee8e68468693d006397f4a0c`; [dessen vollständige Build-/Imageprovenienz](../ap03-20261003/README.md). **Diese 14 Nav2-Pakete wurden hier wiederverwendet, nicht als neuer AP-04-Build gezählt.** Acht Repo-Pakete dagegen neu in `ap04-native-product-*` gebaut. [Ausgeführtes natives Rezept](ap04-native-verify.sh).

Beide Container: `--network none`, keine Geräte, kein privilegierter Modus/Hostnetz ([Isolation/konkrete Image-IDs](ap04-container-isolation.txt)). Ihr historischer `/repo`-Mount zeigt weiterhin AP-03; AP-04-Befehle verwenden **ausschließlich `/evidence/ap04-repo`**, eine bytegeprüfte eigene Snapshotkopie des AP-04-Worktrees im gemeinsamen Scratch-Mount. Kein älteres Explore-Overlay gewinnt einen Import. Eigene neue Installpräfixe bleiben außerhalb Git. Container- und Vergleichsprozesse sind am Ende geordnet beendet; ältere Checkouts nicht umgeschaltet.

Die CPP-Brücke liegt ausschließlich unter `tools/analysis/frontier_comparison`, linkt den originalen externen Kern und enthält keine ROS-Node/Action-/Nav2-Dispatchlogik. [Upstream-Pin, Archivhash und Herkunft](upstream-provenance.txt), [sämtliche Quellhashes](upstream-source-sha256.txt), [Apache-2.0-Lizenz](upstream-LICENSE.txt), [Build-/Test-/Probe-Befehle](upstream-recipe.sh). Pin unverändert, keine upstream Änderungen, kein externer Code und keine neue FOSS-Bibliotheksabhängigkeit in der Produkt-Runtime. Die kleine eigene Implementierung bleibt unter der Repositorylizenz.

Nach Download/Entpacken der exakt bezeichneten Quellen und Bereitstellung der AP-03-Nav2-Unterlage:

```bash
bash /evidence/ap04-current-verify.sh
bash /evidence/upstream-recipe.sh
source /opt/ros/humble/setup.bash
source /evidence/ap04-current-install/setup.bash
source /evidence/ap04-upstream-install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=230
python3 /evidence/ap04-repo/tools/analysis/frontier_comparison/compare.py \
  --repo /evidence/ap04-repo --probe /evidence/ap04-probe-build/ap04_frontier_probe \
  --output /evidence/ap04-final-comparison.json
# Im nativen Nav2-Abhängigkeitsimage:
bash /evidence/ap04-native-verify.sh
```

Jeder native Fall nutzt einen frischen Prozess/ROS-Domain 220–226. Der Planer wird als tatsächliches ausführbares Programm direkt gestartet und ausschließlich an seiner PID sauber mit SIGINT beendet, ohne Launch-/Prozessgruppensignal. Planerannahme und Ergebnis verwenden zusammen das bestehende 2-s-Planbudget; keine Fristlockerung.

## Erste Prüferfehler und offene Grenzen

Der erste Abschlusslauf bestand 163/164 installierte Fälle; eine neue Minimalreichweiten-Testannahme war falsch: ein 360°-Scan konnte entfernte seitliche Randpunkte trotz zu naher frontaler Grenze sehen. Die Assertion wurde auf den tatsächlich geprüften Vorwärtsstrahl begrenzt; Produkt-Minimalreichweite nicht gelockert. [Originalfehler](ap04-first-installed-regressions.log). Danach besteht der vollständige **165-Fall-Lauf** einschließlich zusätzlichem leerem Verarbeitungsbudget-Gegenfall.

Der erste native Prüfhelfer wartete auf exakte Gleichheit aller Unknown-Zellen. Die echte Inflation kann unknown neben Hindernissen zu gesperrten Kosten machen; das ist keine Freiraumfreigabe. Der Prüfer wartet nun auf aktuelle passende Geometrie, keine verlorene Freiraumbeobachtung und weiterhin gesperrten Unknown/Hindernisbestand. Außerdem wurde sein ros2-run-Wrapper durch den direkten nativen Prozess ersetzt, damit keine eigenen Planerkinder zurückbleiben. Die drei zuvor erzeugten eigenen Planer-PIDs wurden separat beendet. [Originalabbruch](ap04-native-plans.log), [Teilbelege](first-native-harness). Dies sind konkret reparierte Prüferfehler, keine verschwiegene Produktfreigabe. Der finale native Lauf und Prozessabschluss sind vollständig erhalten.

AP-04 belegt **Kandidaten/Adapter und planbare Folgeentscheidungen**, keine tatsächlich erreichten sensorischen Beobachtungen oder Erkundungsmission. Die bisherige missionseigene Erledigung kann erfolgreich bediente Nachbarschaften weiterhin sperren; sie wird bewusst erst in **AP-05** geändert. Die neue Kandidatenebene tut dies nicht, auch bei neuer lokaler Sicht nahe einem früheren Ziel. Historien-/UUID-/Versuchs-/Gesamtbudgets wurden nicht zurückgesetzt.

Reale Start-/Mastabdeckung, tatsächliche Reichweite/TF-/Sensorlatenz, aktive Jetson-/Stopplast, reale Trackingabweichung und Türen bleiben offen. Ein vorhergesagter Sichtgewinn ist kein gemessener Beobachtungsbeleg. Physische Qualifikation und vollständige Mission/BT/Explorer/Nav2/Sensorkette folgen **AP-06**; AP-03-Simulationsprofil wurde hier nicht für Hardware aktiviert. Große Karten oberhalb der expliziten Kapazität bleiben blockiert und dürfen nicht als fertig gelten.

Rückfall: ausschließlich Softwarecommit `5ee313b` und die zugehörige AP-04-Dokumentation gezielt revertieren; AP-01–03 und fremde Arbeit erhalten. Alternativ `metric_candidate_source: legacy_centroid` beim geordnet gestoppten Start wählen. Kein Liveparameter-/Installwechsel am Roboter. **Genau nächster vorbereiteter Auftrag: AP-05**, erst nach eigener Nutzerbeauftragung.

Originaldateien sind mit [SHA256SUMS](SHA256SUMS) gebunden.
