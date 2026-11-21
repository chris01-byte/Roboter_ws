# AP-03 – geschlossene Softwareevidenz, 03.10.2026

Basis `875c7c4` (AP-02); Softwarecommit **`c3115ff8ecb28b0828e1de8b8e062c6f0866f55e`**, Branch `fix/nav2-bootstrap-geometry`, Worktree `/workspace/Roboter_ws-ap03`. Originalcheckout, AP-01- und AP-02-Worktree bleiben unverändert. MASTERPLAN v1.3 ist bytegleich zum Nutzeranhang. Kein Hardwarezugriff, Deployment, Push/Merge oder automatischer AP-04-Übergang.

## Ergebnis

| Prüfung | Tatsächliches Ergebnis | Originalbeleg |
|---|---|---|
| Frischer Build auf der AP-02-Testlaufzeit, einschließlich aktueller Repo-/Nav2-Actions | 10 Pakete erfolgreich | [Build](ap03-current-final-build.log) |
| Installierte Produktmodule, Präfixe, echte Nachrichten/Actions | ausschließlich neues `ap03-current-install`; Implementierungen bytegleich zu Quellen | [Bindings](ap03-current-installed-bindings.log), [Codevergleich](ap03-current-installed-source-sha256.txt) |
| Neue Motion- plus bestehende Metric-/Lifecycle-Regressionsdateien gegen Installation | 138 bestanden, davon 22 neue AP-03-Fälle | [Installtests](ap03-current-installed-regressions.log) |
| Alle betroffenen Explorer/Map/State/Base- sowie echte Gate/DDS/Mission/Commandtests | 1.609 bestanden einschließlich aller fünf DDS-Callbackfälle | [Gesamtlauf](ap03-current-affected-tests.log) |
| Registrierte colcon-Tests | 1.577 Tests, 0 Fehler/Fehlschläge/Skipped | [Ergebnis](ap03-current-colcon-results.log), [Lauf](ap03-current-colcon-tests.log) |
| Echter Nav2-Quellbuild für Planung/Controller/NavFn/RPP | 14 Pakete erfolgreich; keine ActionServer-Attrappe | [Nav2-Build](ap03-nav2-final-build.log) |
| Getrennte Produktinstallation im Nav2-Prüfimage | 8 Repo-Pakete; echte installierte Nav2-Plugins/Aktionsbindings | [Build](ap03-product-final-build.log), [Bindings/Codevergleich](ap03-installed-bindings.log) |
| Geschlossene reale Nav2-Komponenten-/Bootstrapmatrix | 8 Fälle bestanden | [Gesamtausgabe](ap03-final-acceptance.log), [Fallverzeichnisse](world/) |
| Neue Regressionen auf unverändertem AP-02-Quellstand | 18 erwartete Fehlschläge, 4 bestandene negative Fälle | [Baseline](ap03-baseline-regressions.log) |
| Tatsächlicher ExploreNode-Kaltstart mit beiden Opt-in-Konfigurationen | Start erfolgreich; Runtime-Modellwechsel schreibgeschützt abgelehnt; kein Auftrag/keine Bewegung | [Kaltstart](ap03-profile-init.log), [Rezept](ap03-profile-init.py) |

Testmengen überlappen und werden nicht summiert. Die Baseline verwendet originale AP-02-Module aus `git archive 875c7c4 src/explore` und nur die neue Testdatei. Vier positive Türfälle scheitern an der bisherigen Hülle; weitere Fehlschläge betreffen fehlende Nav2-Proposals/Live-Pfadpriorität, Vorausrichtung, numerische Endorientierung und nicht geprüfte Response-Parameter. Ein Baseline-Exitcode 1 ist erwartet. Kein Fake-ROS und kein FakeNav2 als Abnahmenachweis.

## Echte Nav2-Matrix

| Fall | Planung/Regelung und Produktprüfung | Maximales Positions-/Headingtracking | Minimaler Abstand des **gepaddeten** Rechtecks |
|---|---|---|---|
| Gerade 68 cm, freier Goal-Bereich dahinter | Beide Actions erfolgreich; bisherige Hülle lehnt ab; Vollrotation im Spalt gesperrt | 1,991 mm / 0,000244 rad | 80,304 mm |
| Gerade 80 cm, freier Goal-Bereich dahinter | Beide Actions erfolgreich; bisherige Hülle lehnt ab | 1,999 mm / 0,000246 rad | 140,225 mm |
| Hindernis, längere Umfahrung | Eigenroute verworfen; tatsächlicher NavFn-Pfad 3,682 m, RPP erfolgreich | 3,485 mm / 0,005011 rad | 200,996 mm |
| Gerade 56 cm, zusätzliche Negativkontrolle | NavFn liefert sogar einen Pfad; Vollchassisprüfung verwirft, **kein FollowPath**, 0 Nichtnullkommandos | keine zugelassene Bewegung | keine Fahrt |
| Drehziel im 68-cm-Spalt | NavFn liefert einen Punktpfad; Goal-Drehhülle verwirft, **kein FollowPath**, 0 Nichtnullkommandos | keine zugelassene Bewegung | keine Fahrt |
| Unbekannter Außenraum hinter der Tür | NavFn bricht ab; eigene bekannte Ziel-/Verbindungsprüfung lehnt ebenfalls ab; 0 Nichtnullkommandos | keine zugelassene Bewegung | keine Fahrt |
| Autonome erste Beobachtung | Tatsächlicher Frontierdetektor/Approach/Policy wählt selbst das Ziel; Scan unzulässig; beide Nav2-Actions erfolgreich | 1,909 mm / 0,000361 rad | 535,299 mm |
| Fehlende initiale Kontur | `wait`, keine Kandidaten; 168 fehlende Zellen je Rohkarte/Costmap konkret benannt; keine Fahrt/Scanwiederholung | keine zugelassene Bewegung | keine Fahrt |

Im Bootstrap entstehen **0,454 m² neue beobachtete Fläche** allein durch die erreichte simulierte Pose und verdeckungsgeprüfte endliche Vorwärtssicht. Der gewählte Zielpunkt ist im Ergebnis protokolliert und nicht vorgegeben. Die anderen positiven Ziele sind ausdrücklich Komponentenziele. Rückwärts-Samples: null in sämtlichen positiven Fällen. Actions enden mit echtem ROS-Status 4; der Unknown-Plan mit Status 6. Negative vollständige Geometrieprüfungen stoppen vor der Controller-Action; es wird nicht behauptet, NavFn könne den orientierten Footprint selbst beweisen.

Jeder Fall besitzt reale Planer-/Controllerlogs, exakte Parameter und Ergebnis-JSON. Positive Fälle enthalten den tatsächlichen Pfad und eine Zeitreihe `monotonic,x,y,yaw,v,w`; bei erforderlicher Vorausrichtung zusätzlich deren gemessene Bewegung. Der Prüflauf liest die 17 Modell-/Geometrieparameter am tatsächlichen Controller. Unabhängige Groundtruth-Kollisionsprüfung: Polygon-Trennachsen und exakte Kantenabstände, nicht die Produkt-Footprintprüfung.

## Umgebungen und Reproduktion

**Aktuelle Produktregression:** AP-02-basierte echte Ubuntu-22.04/Humble-Laufzeit mit Python 3.10.12 und rclpy **3.3.22**. Neues gerätefreies Docker `ap03-current`, `--network none`, Domain 230. [Versionen](ap03-current-environment.txt), [Image-IDs](ap03-local-image-ids.txt), [Isolation](ap03-container-isolation.txt). `nav2_common/nav2_msgs` aus dem unten genannten festgehaltenen Quellstand plus acht Repo-Pakete ergeben den tatsächlich gebauten Zehnpaketausschnitt. [Ausgeführtes Rezept](ap03-current-verify.sh); vorher nur `/opt/ros/humble`, nachher ausschließlich das neue Präfix. Kein AP-01-/AP-02-Overlay-Sourcing im Abschlusslauf. [Install-Codevergleich](ap03-compare-installed.py).

**Echte Nav2-Komponenten:** Nav2 **1.1.20**, kompletter Quellarchivstand `3c3db59d6969d8ecee8e68468693d006397f4a0c`, [Archivhash](ap03-nav2-source-archive-sha256.txt). Offizielles Abhängigkeitsimage `ghcr.io/ros-navigation/navigation2@sha256:48d3727817bdb1582a40c46f3d2caecea509a60a67895b96e6558ed24b040644`; [Manifest](ap03-nav2-manifest-raw.json), [Provenienz](ap03-image-provenance.txt). Dieses Image enthält ROS/Buildabhängigkeiten, noch keine getesteten Nav2-Plugins. Deshalb wurden Planer, Controller und Plugins wirklich aus obigem Quellstand gebaut. Der Build entdeckt alle Quellen, wählt aber ausschließlich `--packages-up-to nav2_planner nav2_controller nav2_regulated_pure_pursuit_controller nav2_navfn_planner` (14 Pakete). Upstream-Unit-Tests sind mit `BUILD_TESTING=OFF` nicht Teil des Nachweises; stattdessen werden die echten Actions geschlossen ausgeführt.

Docker-VFS überschritt beim normalen Schichtimport den verfügbaren Speicher. [Öffentliche OCI-Schichten](ap03-fetch-oci.py) wurden daher mit SHA-256-Prüfung geladen und ohne Quell-/Build-/Logverzeichnisse sowie apt-Caches in ein einzelnes lokales Image überführt. Installierte ROS-/Abhängigkeitsdateien bleiben enthalten; keine ROS-Nachrichtenattrappen oder leeren Paketpräfixe. Lokale Image-ID und ältere rclpy-**3.3.17**-Version sind explizit belegt. Der Komponentencontainer läuft ebenfalls mit `--network none`, ohne Geräte, privilegierten Modus oder Hostnetz.

[Nav2-/Produktrezept](ap03-final-verify.sh) baut getrennte native Nav2- und Repo-Präfixe, prüft deren tatsächliche Auflösung und die installierte Quellenidentität. Für die Welt danach:

```bash
source /opt/ros/humble/setup.bash
source /evidence/ap03-nav2-install/setup.bash
source /evidence/ap03-install/setup.bash
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=228
python3 /repo/tools/simulation/ap03_nav2_closed_loop.py \
  --repo /repo --output /evidence/ap03-final-acceptance
```

Repo unter `/repo`, Source-/Build-/Install-/Logpfade unter `/evidence`. Das Weltwerkzeug erzeugt acht frische Kindprozesse mit Domains 210–217 und beendet ganze Nav2-Prozessgruppen. Dadurch beantwortet ein abgebauter DDS-Service nicht die Readinessprüfung des nächsten gleichnamigen Falls. Es gibt keinen Wiederholungsloop für fehlgeschlagene Welttests.

Die CI ergänzt die 22 Motion-Regressionsfälle und einen separaten echten Nav2-Komponentenjob mit gespeicherten Artefakten. Lokale Rezepte sind ausgeführt; GitHub Actions wurde nicht ausgelöst. CI benutzt distributionsseitige Humble-Pakete; sie ist kein Beleg derselben festgehaltenen nativen Binärdateien.

## Tatsächliche Timinggrenze

Im älteren Nav2-Abhängigkeitsimage scheiterten zwei Sammelläufe an einem unveränderten, zeitkritischen echten Gate-DDS-Test: einmal Rohquellenfrische, einmal dessen 0,35-s-Callback-/0,25-s-Beobachtungsfenster. [Paralleler Lauf](ap03-concurrent-load-affected-tests.log), [Lauf ohne Welt](ap03-sequential-group-timing-failure.log). Auch ein erster Einzelversuch zeigte eine gealterte Wheelprobe; spätere vier frische Einzelprozesse bestanden ([Rezept](ap03-dds-verify.sh), `ap03-dds-*.log`). Somit ist die ältere Prüfumgebung nicht als allgemein stabil unter Last ausgewiesen.

Die bereits für AP-02 verwendete neuere ROS-Laufzeit besteht dagegen alle fünf DDS-Fälle zusammen ([Gegenprobe](ap03-current-rclpy-dds.log)) und anschließend den gesamten neu gebauten **1.609-Fall-Abschlusslauf**. Die Umgebungen unterscheiden sich unter anderem in rclpy/DDS-Versionen; eine alleinige Ursache oder reale Worst-Case-Stabilität wird daraus nicht abgeleitet. Keine Timeout-/Fristlockerung und keine Gate-/HWT-/Encoderänderung, um Ergebnisse grün zu machen. Die Fehllogs bleiben erhalten. Aktive Jetson-/Stopplast bleibt AP-06.

## Grenzen und Rückfall

[Bewegungs-/Geometrievertrag und vorbereitetes Sensorabdeckungspaket](../../BEWEGUNGSVERTRAG.md). Der opt-in Rollout ist nur für Wandzeit-unicycle-Integration mit 100-Hz-Zielrate/25-ms-Schrittkappe und **50-ms** Antwort qualifiziert. Die wirklichen **2000-ms** Motoren, Smoother, Schlupf, Sensor-/TF-Latenzen und Schutz-/Stoppkette sind nicht übertragen. Vorausrichtungsberechnung und autonomer erster Beobachtungsschritt sind Komponentenprüfungen; die vollständige ExploreArea-/BT-/Mission-/Sensor-/Gatekette und Wohnungsvollständigkeit werden hier nicht behauptet. Keine künstlich gesunden HWT-/Encoder-/Schutzzustände in der Simulation.

Das konservative Profil bleibt Standard. Das neue Simulationsprofil wird nicht am Jetson aktiviert. Physische 68-/80-cm-Tür, Startabdeckung, Eigenabschattung und reale Tracking-/Stoppabnahme bleiben offen. AP-04 ist weder begonnen noch durch diesen Abschluss beauftragt. Rückfall: ausschließlich Softwarecommit `c3115ff` und die zugehörige AP-03-Dokumentation gezielt revertieren, AP-01/AP-02 und fremde Arbeit erhalten; keine Rücksetzung von Main/Jetson.

Originalbelege sind in [SHA256SUMS](SHA256SUMS) gebunden.
