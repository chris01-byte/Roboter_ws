# AP-06: Gesamtkonzept experimentell prüfen

Stand 08.10.2026. Fortsetzung des Nutzerauftrags: eine funktionierende
Gesamtlösung entwickeln, ihre praktische Tragfähigkeit prüfen und vorhandene
Blocker anhand ihrer Wirkung bewerten. Dieser Versuch ist Entwicklungsarbeit;
er ändert weder rückwirkend die ursprüngliche Abnahme noch behauptet er ein
fertiges Kundenprodukt. MASTERPLAN v1.3 und die bisherigen Negativbelege bleiben
erhalten. Der aktuelle Gesamtstatus steht ausschließlich in [STATUS](STATUS.md).

## Fragestellung und erste kontrollierte Veränderung

Der unveränderte Produktkandidat `2e5e1fd` erhält im isolierten Weltmodell einen
endlichen 2160-Strahlen-Laserscan ohne die simulierte Mastabschattung. Dafür
existiert bereits `ap06_closed_product.py --ideal-lidar`. Reichweite, Verdeckung
durch Wände, tatsächliche Bewegung, SLAM, EKF, Mission Manager, BT, Explorer,
Nav2 und die komplette Schutzkette bleiben erhalten. Es wird keine fertige
Karte und kein vorgegebenes Fahrziel in das Produkt eingespeist.

Damit wird eine konkrete fehlende Eingangsbedingung überbrückt: die rückwärtige
Sicht. Das ist im Modell eine Sensorvariante. Der reale Mast verschwindet
dadurch nicht; das Entfernen seiner Filterung am Roboter wäre keine Umsetzung
dieses Versuchs. Ein positiver Versuch würde eine funktionierende Erkundung
unter veränderter Sicht belegen, nicht die Eignung der vorhandenen Montage.

Vor dem ersten Lauf werden Start A, Originalbudgets, Quellhashes und die
geänderte Sensorbedingung gespeichert. Ausgangsbasis sind die drei vorher
festgelegten Startposen; zunächst wird A vollständig ausgeführt. Erst dessen
Befund entscheidet über einen Vergleich mit B/C oder eine andere begründete
Versuchsbedingung. Keine automatische Serie gleicher Fehlstarts.

## Welche Einschränkungen wir wie beurteilen

| Bedingung | Experiment und Entscheidungsgrundlage |
|---|---|
| Startbeobachtung und strenge Anfangsflächenprüfung | Zuerst fehlende Sicht durch endliche Modellmessungen ersetzen. Kommt die Kette damit weiter, ist fehlende Sicht relevant. Das allein beweist weder jede Einzelprüfung notwendig noch eine Hardwareänderung alternativlos. |
| Bereits vor Ankunft nachgewiesene spätere Abfahrt | Zweite Variante nach dem Sichtkontrolllauf: den zusätzlichen Zukunftsnachweis protokollieren und bei vollständig öffentlicher aktueller Kontur zurückstellen. Aktuelle Anfahrt, Zielstopp, Reglervertrag, Beobachtung und Quellen bleiben geprüft. Risiko: sicher ankommen, aber später keinen zulässigen Ausweg finden. Genau das wird im Gesamtversuch untersucht. |
| Zwei-Zentimeter-Abgleich zwischen Encoder und TF | Tatsächliche Messzeiten vergleichen. Der Code liest TF vor umfangreicher Geometrieverarbeitung und bindet danach aktuelle Radmessungen. Ein Zeitversatz muss von räumlicher Inkonsistenz getrennt werden; die Fehlerursache ist mit bisherigen Paarwerten allein nicht bewiesen. |
| Rechen-, Wiederholungs- und Missionsbudgets | Fortschritt, Wartezustände und verbrauchte Zeit getrennt auswerten. Erst eine nachgewiesene nützliche Folgeentscheidung rechtfertigt einen gesonderten Budgetvergleich. Längeres Warten allein ist kein Konzeptnachweis. |
| Hindernisse, verlorene Quellen, Cancel, HOLD und Stillstand | In diesem Versuch vollständig wirksam. Ein Konzept, das nur bei ungültigen Daten oder ohne zuverlässig wirksames Anhalten fährt, liefert keine tragfähige Kundengrundlage. |
| Abschlussbedingungen | Erreichte Position, tatsächliche neue Beobachtung, Passage mit Heck, Restaufgaben und Kartenfehler einzeln berichten. Geänderte Versuche dürfen nicht als ursprüngliche 3/3 gezählt werden. |

## Reproduzierbarer Versuch

Das Werkzeug `tools/simulation/ap06_concept_experiment.py` führt den bestehenden
Gesamtprüfstand aus und bewahrt dessen Originalresultat. Seine Auswertung führt
den experimentellen Befund getrennt von der ursprünglichen Qualifikation.
`original_qualification` bleibt für den Versuch falsch, auch wenn alle
funktionalen Kriterien im veränderten Aufbau erfüllt werden.

Nur im bereits vorbereiteten Humble-Container ohne Geräte und ohne externes
Netzwerk ausführen. Die ursprünglichen Build-/Abhängigkeitsschritte stehen in
[README_AP06](../../tools/simulation/README_AP06.md); ein vorhandenes x86-Binary
ist kein Jetson-Build. Ausgabedaten bleiben außerhalb des Quellbaums.

```bash
export AP06_SIMULATION=1 ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=187
python3 tools/simulation/ap06_concept_experiment.py \
  --repo "$PWD" --output /tmp/ap06-concept-visibility-a \
  --tf-probe /tmp/ap06/tf-probe-build/tf_ownership_probe \
  --profile finite-unmasked --case door68_start_a
```

Der getrennte Vergleich verwendet ein neues Ausgabeverzeichnis und
`--profile finite-unmasked-deferred-departure`. Nur in diesem Profil wird der
zusätzliche Zukunftsnachweis im Explorer-Prozess versuchsweise zurückgestellt.
Die Originalfunktion läuft zuerst. Eine Ablehnung darf nur nach erneut gültigem
unverändertem Reglervertrag, öffentlichem aktuellem Konturbeweis und gültigen
Stopprüfungen überbrückt werden. Jede Entscheidung steht in
`departure_assessments.jsonl`; Quellen-/Fristfehler und Ausnahmen werden nicht
überbrückt. Ein Quellenexport ohne `.git` benötigt zusätzlich
`--source-revision` mit der vollständigen deklarierten SHA; die tatsächlichen
Quelldateien werden unabhängig gehasht. Das behauptet keine geprüfte Identität
aller installierten Binärdateien.

## Übergang zum realen Roboter

Der Nutzer übernimmt die spätere lokale Ausführung auf dem Jetson. Dieser Chat
hat derzeit nur einen Cloud-Ausführungskanal. Der Konzeptversuch enthält keinen
Jetson-Installwechsel und keine autonome reale Fahrt.

Vor der bewegten Wiederholung müssen der konkrete Quellen-/Installstand und
die echten Sensorbedingungen zusammenpassen. Der erste lokale Schritt ist die
rein lesende Erfassung der Startkarte, Kostenkarte, Scans, TF, Encoder-, HWT-
und Schutzstatus. Sie beantwortet, ob die im Modell fehlenden Bereiche am
Roboter wirklich unsichtbar sind und wie groß der tatsächliche Zeitversatz ist.
Reale Karten und Aufnahmen bleiben lokal außerhalb Git.

Für die spätere Erfassung an einem bereits geprüften, passiv laufenden
Produktstack kann derselbe Datensatz wie im Simulator aufgezeichnet werden.
Die folgenden Befehle starten nur den Recorder, keinen Sensor-/Motorstack und
keine Mission. In der Shell müssen vorher Humble und der tatsächlich geprüfte
lokale Produktinstall geladen sein. Der vorhandene
`tools/kartierung/start_app_erkundung.sh` lädt fest `~/roboter_ws/install`;
er ist deshalb kein Nachweis, dass ein separater neuer Kandidat verwendet wird.

```bash
AP06_CAPTURE="${XDG_DATA_HOME:-$HOME/.local/share}/amadeus/diagnostics/ap06-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$AP06_CAPTURE"
git rev-parse HEAD > "$AP06_CAPTURE/source-commit.txt"
git status --short > "$AP06_CAPTURE/source-status.txt"
ros2 node list > "$AP06_CAPTURE/nodes.txt"
ros2 topic list -t > "$AP06_CAPTURE/topics.txt"
timeout --signal=INT 180s ros2 bag record --include-hidden-topics \
  --storage-preset-profile resilient -o "$AP06_CAPTURE/bag" \
  /map /global_costmap/costmap /scan /scan_normiert /tf /tf_static /odom \
  /robot_map_manager/status_json /explore/status_json /mission_manager/status_json \
  /base_hardware/state_json /fusion/hwt601/wheel_odom_raw \
  /shadow/hwt601/wheel_status_json /shadow/hwt601/raw_status_json \
  /shadow/hwt601/status_json /fusion/hwt601/status_json /near_field/status \
  /plan /received_global_plan /explore_area/_action/status \
  /navigate_to_pose/_action/status /safety/estop \
  /cmd_vel_nav_raw /cmd_vel_nav /cmd_vel_smoothed /cmd_vel \
  > "$AP06_CAPTURE/recorder.log" 2>&1
ros2 bag info "$AP06_CAPTURE/bag" > "$AP06_CAPTURE/bag-info.txt"
```

`timeout` liefert bei Ablauf normalerweise Code 124; die abgeschlossene
Bag-Metadatei und tatsächlichen Topic-Zähler entscheiden über die Aufnahme.
Fehlende Topics sind fehlende Messungen. Ein reiner Recorderlauf prüft weder
den Quellenvertrag noch die Anhaltewirkung. Eine laufende Bag-Datenbank wird
nicht parallel ausgewertet. Zusätzlich hält das vorhandene
`hwt_diagnose_manifest.py` mit dem tatsächlich verwendeten Profil und den
geladenen Setup-Dateien die Installpräfixe und Artefakte fest.

Danach folgt im bestehenden LAB-1-Rahmen ein begrenzter aktiver Versuch über
die vorhandene Mission-/Nav2-/Schutzkette: erster selbst gewählter
Beobachtungspunkt, mehrere Folgeaufgaben, ganze Passage, Weiterarbeit und
ehrliches Ende. Änderungen an Sensoraufbau oder Prüfung werden vor diesem
Versuch konkret benannt und separat nachgewiesen. Eine Bedienhilfe oder ein
Eingriff darf einen Entwicklungslauf ermöglichen, wird aber aufgezeichnet und
zählt nicht als autonomer Kundenpositivlauf.

Für eine Lieferentscheidung bleiben anschließend drei vollständige autonome
Softwaremissionen auf demselben Kandidaten sowie die realen, beaufsichtigten
Abnahmen erforderlich. Die endgültige Betriebsgrenze wird anhand dieser
Messungen festgelegt; bisherige Teilfortschritte ersetzen diese Nachweise nicht.

## Rückfall

Die Versuchssteuerung liegt ausschließlich unter `tools/simulation`. Sie wird
nicht in den Produktlaunch installiert. Weglassen des Versuchsaufrufs erhält
den bisherigen Produktpfad. Die Zukunftsnachweis-Variante gilt ausschließlich
für den expliziten isolierten Versuchsprozess; kein dauerhaftes Ändern der
Produktkonfiguration und kein Zurücksetzen fremder Arbeit.

## Aus den Versuchen abgeleitete Integrationskorrektur

Im abgeschlossenen zweiten Lauf scheiterten zwei Ausrichtungen trotz zuvor
positivem originalem Zukunftsnachweis. Jeweils etwa 19,6 s ergaben nur
0,061 beziehungsweise 0,083 rad tatsächliche Encoderrotation. Bei gültigen
Encodern waren über 73 % der Basiskommandos null; die Drehimpulse kamen mit
medianen Abständen von 0,98 beziehungsweise 1,07 s an. Der genaue
untergeordnete Ausrichtungsfehler wurde bisher nicht gespeichert.

Die Drehschleife ruft synchron vor jedem Kommando einen Stopprüfer auf, der
auch die gesamte spätere native Fahrt neu berechnet. Die abgeleitete
Produktkorrektur trennt deshalb die aktuell ausgeführte Drehung von der erst
anschließend ausgeführten Translation. Während externer Vorausrichtung darf
ein frischer vollständiger öffentlicher 360°-Drehraum mit unveränderten
Kontur-/Trackingreserven die spätere Streckenprüfung ersetzen. Fehlt dieser
Nachweis, bleibt der bisherige vollständige Streckenprüfer zuständig.
Unmittelbar vor dem Nav2-Kind und während der Fahrt wird weiterhin die ganze
tatsächliche Strecke geprüft. Quellen-, Pose-, Frist- und Stopprüfungen bleiben
in jeder Phase erhalten. Zusätzlich wird das konkrete Ausrichtungsergebnis
gespeichert, bevor es zum allgemeinen Missionsfehler verdichtet wird.

Die gemessenen Impulse belegen das Ablaufproblem. Die Zuordnung der gesamten
Verzögerung zu einer bestimmten Funktion benötigt den neuen Vergleichslauf;
aus dem Code allein wird keine erreichte Befehlsfrequenz behauptet.


## Befund der geschlossenen Vergleiche vom 08.10.2026

Die endliche Sicht ohne Mastmaske ermöglicht im Modell erste Ankünfte, aber
keine Gesamtmission. Das zusätzliche Überbrücken des Zukunftsnachweises wurde
nur einmal tatsächlich gebraucht; die anschließende Fahrt stoppte nach etwa
6 cm an der weiter wirksamen aktuellen Konturprüfung. Daraus ergibt sich
kein Beleg, diesen Nachweis dauerhaft zu entfernen.

Die Produktkorrektur trennt die aktuelle externe Drehung von der späteren
Fahrt. Eine weitere reproduzierte Korrektur erlaubt die vorhandene öffentliche
Kartenfortsetzung auch bei gültigem, vollständig leerem privatem Startbestand.
Neue Rohdaten dürfen während dieser kurzen vorhandenen Übergangsphase nur
Freiraum entziehen. Im anschließenden `joined-a` trat kein Kartenbindungsstopp
auf; nach zwei Ankünften endete jedoch eine Eingangsprüfung mit
`self_body_scan_stale_after_processing`. Alle Ausrichtungen dieses Laufs waren
reglergeführt; der externe Drehpfad ist dadurch noch nicht praktisch belegt.

Der überprüfbare lokale Einstieg steht in
[JETSON_KONZEPTTEST_AP06](JETSON_KONZEPTTEST_AP06.md). Dazu gehören der echte
Stack mit zurückgestelltem Explorer und ein passives Werkzeug zur aktuellen
Scope-/Quellenbindung. Alle geschlossenen Resultate, auch negative Versuche,
stehen im [Belegbericht](evidence/ap06-concept-20261008/README.md).
Keine der veränderten Sensorvarianten zählt zur ursprünglichen AP-06-Abnahme;
Hardwaremessungen bleiben erforderlich. Die Originalqualifikation ist 0/3.

Der abschließend geprüfte Produktkandidat `c5d2a9c` ergänzt eine begrenzte
Wiederprüfung nach während der Berechnung abgelaufenen Scan-/Posedaten.
Der alte Datensatz bleibt verworfen; Wiederholung verlangt bestätigten Halt,
neue gültige Eingänge und denselben unveränderten Aufgaben-/Missionsrahmen.
Vor Auswahl und bei Beobachtung gilt dieselbe begrenzte Behandlung.
1.808 registrierte Explorer-Tests bestanden nach dem abschließenden Build.

`revalidation-a` erreicht drei Ankünfte mit Beobachtung, endet aber nach dem
5-s-Auswahlbudget ohne ganze Passage. `selection-capture-a` belegt erstmals
eine erfolgreiche Wiederprüfung nach Scanablauf und anschließende Ankunft;
später erschöpft ein Poseablauf das bestehende Aufgabenversuchslimit. Wieder
keine Gesamtmission. Die 23 zusätzlich protokollierten Auswahlaufrufe
überschreiten das Budget nicht; eine Offline-Rekonstruktion der finalen Daten
reproduziert den früheren Auswahlfehler ebenfalls nicht. Sie ersetzt keine
Live-Frischeprüfung. Die genauen Zeiten, Quellbindungen, Grenzen und alle
negativen Resultate stehen im Belegbericht.

Die lokale Übergabe ist damit ein überprüfbarer Entwicklungsstand für den
passiven Jetson-Vorlauf. Die verlangte funktionierende Kundenlösung und
drei erfolgreiche Gesamtmissionen sind noch nicht erreicht.
