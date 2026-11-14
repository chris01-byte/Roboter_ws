# Kritische Prüfung des AP-06-Builds v17

Stand 11.10.2026. Produktquelle `60e894cd6638c2d977b0fca6e352fe7b5aedae44`,
beauftragte Implementierungsbasis `d2c6cfe018564b9bc59ff43dd49808e3293169c2`.
STATUS.md bleibt der einzige aktuelle Iststand. Dieser Bericht prüft die
Aussagekraft der Belege; er erweitert weder Freigaben noch Abnahmekriterien.

| Selbst gestellte Frage | Antwort und Grenze |
|---|---|
| Habe ich tatsächlich den korrigierten Stand gebaut? | Ja: sauberer Fixbranch, 14 Pakete separat in 174,559 s. Quellmanifest und Buildmanifest stimmen für alle 3.717 verfolgten Dateien überein; 157 Vergleichseinträge betreffen 155 eindeutige bytegleiche Quelle/Install-Dateien; zwei Dateien wurden doppelt erfasst. Die Auftragsbasis d2c6cfe ist Vorfahr. `source_base=e14ca312` bezeichnet den historischen Ursprung des privaten Checkouts; der gebaute Stand ist 60e894c. |
| Können alte Overlays den Prüflauf unbemerkt verändern? | Alle 14 Produktpräfixe zeigen auf v17. Aufgelöste Produktmodule und ARM64-Nativkern sind mit Pfad/Hash erfasst. ROS Humble, gepinnter Nav2-Unterbau und LiDAR-Unterbau werden ausdrücklich weiterverwendet; ihre Bindung ist dokumentiert. Das ist kein hermetischer Build auf einer zweiten Maschine. |
| Ist die bestehende Installation wirklich erhalten? | Ja: alle 1.048 ursprünglichen Installhashes unverändert, Bestandsmain 23928d9 sauber. Build, Install, Log und Diagnose liegen separat. Keine dauerhafte Installation oder Aktoraktivierung aus diesem Build. |
| Beweisen die gezielten Gegenfälle den tatsächlichen Fehler? | Adaptive Elternauswahl und reale Produktvalidatoren werden ausgeführt. Transport-/Testuhrenersatz ist gekennzeichnet; keine erfolgreiche Entscheidungsattrappe. Wartefolge sowie native Stop-/Anfangsdrehungs-Klassifizierung waren vorher rot. Geometrisch unzulässige Pläne bleiben abgelehnt und werden innerhalb ursprünglicher Grenzen verbucht. |
| Habe ich für den Rechenzeitgewinn Schutzwirkung aufgegeben? | Die ursprünglichen Frische-, Scan-, Aufgaben-, Gesamt- und Versuchslimits bleiben. Pure Inhaltsbindung wird vor Rückgabe vollständig frisch auditiert; fünfzehn Änderungen an Eingaben/Parametern verwerfen die Auswahl. Ausnahme gibt die Bindung frei. Aktuelle Quellen und native Route werden vor Bewegung weiterhin erneut geprüft. Eine 1-ms-Executor-Pause wurde wegen verzögerter Nachrichtenzustellung verworfen. |
| Ist die Beschleunigung für jede Mission bewiesen? | Nein. Drei Paare derselben aufgezeichneten synthetischen B-Auswahl unter 320-Hz-DDS-Last: median 3,909→3,265 s Wandzeit, 2,396→1,997 s Thread-CPU, 1.828→16 Inhaltsreads, gleiches Ziel/90 Punkte/Hash. Das belegt den gemessenen Engpass; es belegt weder allgemeine Worst-Case-Zeiten noch reale Sensorfrische. |
| Habe ich eine gemeinsame Ursache aller Abbrüche bewiesen? | Nein. Erster Trigger, Folgereaktionen und Terminalgrund bleiben getrennt. Scan-Footprint, fehlende Stop-Sicht, gealterte ausgewählte Probe und Auswahlbudget sind verschiedene belegte Ereignisse. Reale Encoder-/Antriebs-Teilprüfungen beweisen keine autonome Gesamtfahrt. |
| Genügt eine grüne Regression für Auslieferung? | Nein. Abnahme verlangt 3/3 unveränderte ganze Originalmissionen mit drei Beobachtungen, voller Passage einschließlich Heck, weiterer Kartierung und sämtlichen Manifestkriterien; anschließend aktuelle reale Abnahme. Der ursprüngliche HOLD-Fall prüft Halt, ausdrücklich keine vollständige Wiederaufnahme. |
| Waren meine eigenen Prüfwerkzeuge fehlerfrei? | Nein. Falsche Testpfade und ein schon angelegter leerer Ergebnisordner verursachten Starts vor Testsammlung. Sie wurden repariert; ursprüngliche Fehlerlogs bleiben erhalten und werden nicht als Produktfehler oder positive Prüfungen gezählt. |
| Ist die veröffentlichte Übergabe aktuell und reproduzierbar? | Die Softwarekorrekturen sind auf dem Featurebranch. Die Jetson-Anleitung nannte noch c5d2a9c als aktuellen Kandidaten; dieser veraltete Verweis wird mit diesem Audit korrigiert. Exakter Commit, Buildskripte, Präfixe und Hashes werden im Auditbeleg veröffentlicht. Lokale Logs und reale Raumdaten bleiben außerhalb Git. |

V17 ist vollständig ausgeführt: **2.976 Regressionen bestanden; ursprüngliche
Missionen 0/3**. A 0,203623 m/keine Beobachtung, erster Egress-Routentrigger,
terminal `completion_raw_pose_not_observed_free`. B 0,354768 m/eine Beobachtung,
zuerst keine ursprüngliche Sicht am nativen Stop, terminal Auswahlbudget
5,889749 s bei 2,257465 s Thread-CPU. C 0,707988 m/eine Beobachtung, Scan
nach 0,192777 rad/4,083774 s geometrisch unterbrochen, danach Auswahlbudget
5,707443 s bei 2,145290 s CPU. Damit löst die gemessene lokale Beschleunigung
die tatsächlich späteren Lastfälle noch nicht. Unterschiedliche Läufe und
Eingaben erlauben keine allgemeine Verschlechterungs-/Verbesserungsaussage.
Ein Exitcode 0 des Matrixdrivers heißt nur, dass alle Fälle ausgeführt wurden;
ihre individuellen Ergebnisse bleiben negativ.

Originale Cancel/HOLD-Stoppfälle: 2/2 bestanden. Vollständige Wiederaufnahme bleibt
offen. Im originalen HOLD-Fall erfolgte nach dem Halt tatsächliche Fortsetzung:
vier Ankünfte, drei Beobachtungen, 1,249039 m; terminal jedoch
`map_status_join_retry_budget_exhausted`. Das ist positiver begrenzter
Fortsetzungsfortschritt, kein gespeicherter Wiederaufnahme- oder Missionsabschluss.
Alle Kinder terminal und vier Kommandoströme null; keine Realfahrt.
[Exakter Build-/Ergebnisbeleg](evidence/ap06-correction-v17-20261011.json).

Die jeweils jüngsten abgeschlossenen Missions- und Regressionsergebnisse stehen
in STATUS.md und im verlinkten Buildbeleg. Ein noch laufender Prüfteil bleibt
als offen gekennzeichnet. Vollständige Wiederaufnahme und reale Folge werden
separat nachgewiesen; ein HOLD-Stopp oder kurzer Fahrweg ersetzt diese Nachweise
nicht.

Rückfall: privaten Kandidaten abwählen; nur eigene begrenzte Korrekturcommits
gezielt revertieren. Bestandsinstall, Main, Schutzprüfungen und ursprüngliche
Manifestfälle bleiben erhalten.
