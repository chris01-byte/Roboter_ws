# AP-06 Referenzreparatur – Originalnachweise 05.10.2026

**Referenzbindung software_geprüft; Gesamt-/Realabnahme weiterhin offen.** Auftrag: „repariere die Referenzbindung und prüfe mit denselben Szenarien erneut“. Ausgang `4351b8bb2018aa959aa84d6d6e8aa03621913e41`, Software `e54c954` → **`3f66d73`**, gleicher AP-06-Branch. [Einziger aktueller STATUS](../../STATUS.md). Keine Hardwarefahrt, Installation, Veröffentlichung oder automatische weitere AP-Arbeit.

## Was sich ändert

`metric_egress_reference.py` hält den einmaligen Anfangsbestand in der ersten Odometriefläche: ursprüngliches Raster/Polygon und committed Flächen-/Abstandshistorie bleiben fest. `metric_frontier_runtime.py` liest echte Pose und `map→odom` zur gemeinsamen tatsächlichen TF-Zeit und hängt den Bezug an jeden Input. Kein Latest-Future-TF als aktueller Messwert, keine frische Quellenstempel-Erfindung.

Kompatibles Wachstum/SLAM-Korrektur erfasst keinen neuen Bestand. Aktuelle ganze unbekannte Rasterzellen müssen vollständig durch erhaltene Anfangszellen gedeckt sein; jede neu beobachtete Teilfläche lässt konservativ die ganze betroffene Anfangszelle entfallen. Danach frischer voller Körper-/Scope-/Rohkarten-/Costmapbeweis und ursprünglicher monotoner Egress-Beweis. Subzellige Rasterung darf kein vorheriges freies Außenstück neu als unbekannte Startausnahme übernehmen. Unbekannte Padding-/Außenfläche, Belegung, Rückkehr, fehlender Bezug sowie Frame-/Sitzungs-/Auflösungswechsel bleiben gesperrt. Ohne belegten Bezug bleibt der strikt invalidierende AP-02-Fallback erhalten.

Reine Projektion darf bei exakt gleichen Geometrie-/Inhaltseingaben wiederverwendet werden. Identische physische Zellgitter nutzen ausschließlich ganzzahlige Indextranslation; andere Gitter brauchen geometrische Ganzzelldeckung. Pose, aktuelle Quellenalter, ganze Bewegungsprüfung und committed Historie werden nicht dadurch gesund gecacht. Bearbeitungszeit ist jetzt auch nach der gesamten Projektion in der ursprünglichen Frischeprüfung enthalten. Keine Frist-/Reserve-/Sensor-/Kalibrierungsänderung; ein Nav-/Missionseigner.

## Rot/Grün, Build und Auflösung

- [Original rot](red.log): 6/10 neue erste Gegenfälle am bisherigen installierten Produkt fehlgeschlagen, 4 bestanden. Ursprungdelta aus dem gesicherten synthetischen C-Befund in rigiden Karten-/Referenztransformationsfällen, Wachstum/Drehung, echte physische Rückkehr und neue Unknown-/Obstaclezellen. Die angenommene rigide Referenztransformation ist eine deklarierte Komponenteneingabe, kein nachträglich gemessener Original-TF-Verlauf.
- Erste Grünprobe: 76 bestanden, zwei Hindernistests noch mit zu enger Ablehnungsgrund-Erwartung (`green-first.log`). Die volle Goalprüfung sperrte schon vor der Trajektorienprüfung; Assertion auf diese Schutzwirkung korrigiert, kein Produktprädikat gelockert.
- Danach 167 / 18 / 169 / 20 ausgewählte Fälle grün, einschließlich echter TF2-Zeitkorrelation. Insgesamt **16 zusätzliche Testfälle** gegen echte Produktfunktionen, CI-Auswahl ergänzt. Quellenverlust, konkurrierender Input, subzellige Deckung, Bearbeitungsfrische und späteres Wachstum nach ungültiger Abfahrt eingeschlossen.
- [Vollständige direkte Auswahl](affected-tests.log): **1.860 bestanden**, 39,94 s. [Reguläre colcon-Auswahl](colcon-results.log): **1.852**, 0 Fehler/Failures/Skipped. Mengen überlappen; keine Upstream-/Remote-CI-Tests behauptet.
- [Inkrementeller Zwölfpaketbuild](final-build.log): **6,65 s**, reale ROS-Produktpakete einschließlich C++-BT; unveränderte native Unterlagen aus vorherigem AP-06 wiederverwendet. Zwischenschritte `build*.log` erhalten.
- [Native](native-identity.json) / [aktuelle Pythonplattform](current-identity.json): **136 installierte Produktdateien bytegleich**, tatsächliche AP-06-Nachrichtenbindings/Modulpräfixe und native Binärhashes. [Quellmanifest](source-manifest.json): **466** Quell-/Test-/Konfigurationsdateien bytegleich zu `3f66d73`; Dokumentationsdateien bewusst nicht als ausführbare Quelle gezählt. MASTERPLAN und alle vier Szenariomanifeste unverändert.

Beide Plattformen Ubuntu 22.04/Humble/amd64/Python 3.10.12. Native Gesamtgraphen: rclpy 3.3.17/rclcpp 16.0.15/rcl 5.3.10; komplette Komponenten-/colcon-Probe: rclpy 3.3.22/rclcpp 16.0.21/rcl 5.3.13. Docker network none, keine Geräte/Privilegedrechte; [Isolierung](container-isolation.log). Kein frischer ARM-/Jetson-Gesamtbuild.

## Dieselben fünf Manifestfälle

[Ergebnisse samt Quellengegenfällen und wirklichen Gate-Zuständen](results.json), [Befehle](commands.json), [Serienausführung](cases.log), [Runner](run_cases.py). Standard `ap06_product_scenarios.json` (2160-Strahl-/Mast-/Nah-/Tiefenprofil) bytegleich SHA256 `54132aaaca7ccee8412d5a5078410f49cb2f388da08c8f18899e5493ab4021da`. Welt, drei Posen, 68-/80-cm-Türen, Hindernis/Umweg/blockierte Alternative, Scope, Konturen, 60-s-Vorlauf, 900-/150-s-Fristen und 20-/3-Aufgaben-/Fehlergrenzen unverändert. Keine manuellen Nav-Ziele, Wahrheitskarte/-TF oder verkleinerten Abnahmen. Originales 720-Profil bytegleich SHA256 `1a1d91e1fc2d5a822fc8956ab1ae3a2860053aca4107d8bcbb7488565ab086f1`; keine neue Abnahme dieses getrennten Lastprofils behauptet.

| Lauf | Ergebnis | Fahrt | Ankunft / Beobachtung |
|---|---|---:|---:|
| `reference-a` – ursprüngliche 68-cm-Pose A | failed / `post_child_state_or_standstill_unconfirmed` | 19,560 cm | 0 / 0 |
| `reference-b` – ursprüngliche 68-cm-Pose B | failed / `post_child_state_or_standstill_unconfirmed` | 18,230 cm | 0 / 0 |
| `reference-c-v2` – ursprüngliche 80-cm-Pose C | failed / `hwt_terminal` | 17,594 cm | 0 / 0 |
| `reference-cancel` | Zusatzfall passed; Mission canceled / `user_canceled` | 3,423 cm | keine Positivmission |
| `reference-gyro-hold` | HOLD/Halt-Zusatzfall passed; Mission failed / `hwt_terminal` | 5,192 cm | keine Positivmission |

**0/3 vollständige positive Missionen.** Der frühere Referenzablauf kommt in den fünf neuen Ereignisprotokollen nullmal vor. Das ist kein Nachweis einer zulässigen subzelligen Gesamt-Abfahrt: deren volle projizierte Deckung geht konservativ verloren (`start_egress_new_unknown_or_obstacle`), ohne Neuverankerung/Whitening. Rigid konsistente positive Komponentenfälle und diese tatsächlichen Raster-/Verbrauchsgegenfälle bleiben getrennt.

Im Explorer erste harte Quellenentscheidung: A Radprobe **2,539 s**, B Raw/Yaw **2,753 s**, Rad **2,788 s**; C Radprobe **298,965 ms**, Raw-/Yawstatus **2,733/2,443 s**. Das wirkliche Fahrtor meldet jeweils **21,5–31,8 ms nach derselben Explorerentscheidung HEALTHY/sources_ready**. Das beweist unterschiedliche Verbraucherzustände, keine erfundene gesunde Quelle und keine bewiesene Scheduling-, Bus- oder Hardwareursache. 180-ms-Radfrische und alle anderen Quellengrenzen bleiben unverändert.

Cancel terminal **0,602 s**, Stillstand **0,301 s ab Injektion**, innerhalb 3/1 s. Im selben Fenster eigener Radfrischefehler (268,357 ms); der Lauf beweist den beendeten Nutzerabbruch mit Halt, nicht alleinige Kausalität des Cancel-Befehls. Tatsächlicher 450-ms-Gyrotransportausfall: HOLD gesehen, Stillstand **0,268 s nach HOLD / 0,594 s nach Injektion**; kein ACK/Fortsetzen/Resume (`hold_resume_qualified:false`).

Alle fünf: tatsächlicher Mission-Manager/C++-BT/Explorer/Nav2/NavFn/RPP/Scan-Normalizer/Safety/Gate/Smoother/Collision/EKF/SLAM-Pfad; Original-HWT-/Encoder-/Sensorproduktmethoden, nur deklarierte Geräte-/Weltmodelle. Höchstens ein Explore-/NavigateToPose-Kind, wirkliche TF-GIDs eindeutig nur SLAM `map→odom` und EKF `odom→base_link`. Terminal keine aktiven Handles, alle vier Cmd-Stufen genau null. Unabhängiger vollständiger gepaddeter Körper kollisionsfrei; kleinstes beobachtetes Konturmaß in C 47,811 cm. Beobachteter Referenzboden A/B/C **55,032 / 57,484 / 58,054 %**, keine ganze Passage/Heckfreigabe/Weitererkundung oder ≥95-%-Abnahme. Fünf echte Rohkartensaves erfolgreich; alle aktuellen exakten Checkpoints `metric_checkpoint_exact_saved_snapshot_unavailable`. Kein konsistentes Resume-Paar oder aktives Wiederaufnehmen behauptet.

`reference-c-v1` auf `e54c954` bleibt ein ursprünglicher negativer Zwischenversuch: keine Fahrt, Consumerstopp. Danach genaue Geometrieprojektion memoisiert/vektorisiert und Bearbeitungsfrische ergänzt (`3f66d73`), C mit neuen Ausgabepfaden technisch begründet wiederholt. Es zählt ausschließlich v2 als aktueller C-Fall. Vorherige AP-06-Fehlläufe/Nachweise nicht überschrieben.

## Archive und Abschluss

[Native Originalarchive](native-runs.tgz): sämtliche sechs rein synthetischen Läufe einschließlich des ersten Negativversuchs, echte Karten-/Costmap-Geometrien, Sensor-/HWT-/Nav2-/SLAM-/TF-/BT-/Safety-/Normalizerlogs, Events, gemessene Modelltrajektorien und gespeicherte Rohkarten. [JUnit](junit.tgz): letzte echte Ergebnisse. `SHA256SUMS` schützt alle Belege; Originalausgabe einschließlich Whitespace erhalten. Reale Raumdaten/Geheimnisse sind nicht enthalten.

Prüfstandreproduktion gemäß [bestehender AP-06-Anleitung](../../../../tools/simulation/README_AP06.md), gleicher gepinnter nativer Unterbau und isolierter Domainbereich. Ausgabeverzeichnis immer neu; CPU-/Callback-Zeitlücken werden nicht durch Neustartserien oder verlängerte Fristen verdeckt. `final-tests.sh`, Identitäts-/Quellmanifest und exakte Befehle ermöglichen Prüfung der getroffenen Aussage.

Eigene ROS-Kinder vor Sicherung beendet; nur Init/Idle in beiden Containern. Danach beide temporären Testcontainer gestoppt ([Originalstopp](containers-stop.log)). Keine Prozessgruppen-Signale, keine Jetson-Wirkung. Nutzer autorisiert Jetson-Shutdown nach Abschluss, aber [tatsächlicher Ausführungsbackend](execution-environment.json) bleibt x86-Cloud ohne Jetson-Projekt/Zugang. Neuer App-Terminal-Leseversuch antwortete nicht und wurde beendet. **Jetson nicht heruntergefahren**; kein Cloud-System-Shutdown.

**Kleinstes nächstes AP-06-Paket:** konkrete Callback-/Quellenalter während frischer Geometrieauswertung messen und begrenzt beheben; subzellige Bestands-/Rastergegenfälle bewahren und dieselben fünf Fälle erneut. Erst drei vollständige Positivmissionen erlauben Zielsystem-/LAB-1-Vorlauf. Alle Real-/aktive Verbraucherlast-/Besitzerwechsel-/HOLD-Fortsetzungs-/WE-M5-Resume-/Apple-WE-M7-Grenzen bleiben offen. Rückfall nur eigene `3f66d73`/`e54c954`-Commits gezielt revertieren bzw. isoliertes Overlay abwählen. AP-01–05/Main/fremde Arbeit und alte Nachweise erhalten; kein Push/Merge/Deployment.
