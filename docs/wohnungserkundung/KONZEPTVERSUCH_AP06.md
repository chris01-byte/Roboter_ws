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
