# Wohnungserkundung – aktueller Status

## 03.10.2026 – MASTERPLAN v1.3 / AP-05 software_geprüft; WE-M7 nativ offen

**AP-05-Kern, Persistenz und ROS-Verbraucherverträge software_geprüft.** Nutzer „gut mache weiter“ beauftragt AP-05 nach dessen konkreter Übergabe. Saubere Basis `2532f1b`, Branch `feature/metric-observation-persistence`, Worktree `/workspace/Roboter_ws-ap05`; Softwarecommit **`090762d93dd4c270478cb31c01c05d07c1da0459`**, Auftragscommit `4a370c0`. MASTERPLAN v1.3 bytegleich; [AP-04-Auftrag archiviert](archive/20261003-ap04/README.md). Keine Hardware, Roboternetzverbindung, Deployment, Push/Merge oder automatische AP-06-Arbeit. Originalcheckout und AP-01–04 bleiben unverändert.

**Fortschritt und Abschluss:** Ankunft allein erledigt kein Ziel. Tatsächlicher Gewinn erfordert neue passende Karte und neuen endlichen Scan, belegte unbekannt→beobachtet-Weltzellen ohne Wand-/Masken-/Reichweiten-/Rasterwiderspruch; nach Verarbeitung Frische und Originaldeadline erneut prüfen. Stationäre Beobachtung höchstens 2 s innerhalb ursprünglicher Goal-/Gesamtfrist; bestehender HWT-HOLD/ACK ohne neues Kind oder Budgetreset. Neue lokale Evidenz erlaubt nach Cooldown dieselbe Aufgabe erneut, höchstens drei Gesamtversuche, keine neue ID durch entfernte Kartenänderung. Gesamterfolg erst nach vorab festem mindestens **3-s-Fenster**, mindestens drei verschiedenen gültigen Scans und kontinuierlich keiner raw-erreichbaren Restaufgabe/ungeklärten zugänglichen Verbindung. Prüfung erfolgt vor Größen-/Geometrie-/Historienfiltern; hinter Wänden unbekannte Zellen verhindern Erfolg nicht pauschal. Letzter Callback-Race wird erneut geprüft. Datenverlust, Filter, Blockade, Versuchs- und Budgetende ergeben keinen Erfolg.

**Ergebnisse und Verbraucher:** `metric_complete`, `usable_partial`, `blocked_help_required`, `error`, `user_canceled` getrennt im versionierten metrischen Statusobjekt. Bestehende ExploreArea-Wirefelder unverändert; nur wirklicher metrischer Abschluss endet SUCCEEDED/true, Cancel terminal CANCELED/false. Bestehender BT-Erfolgspfad bleibt maßgeblich; Missiontelemetrie kann ihn weder beenden noch entsperren. Bestehende App-Modell/UI/Testquelle zeigen die Zustände und Ankunft/Beobachtung/Gewinn getrennt, keine metrische Bodenabdeckungs-Prozentbehauptung. Rohkarte, kumulativer Sichtgewinn, Fahrspur und Semantik bleiben getrennt; weder semantischer Vollabschluss noch unbekannte geschlossene Räume behauptet.

**Bestehende Persistenz:** Schema-1-Checkpoint an exakte gespeicherte Kartenidentität/Fingerprint/Sitzung/Scope gebunden, einschließlich Aufgaben/IDs/Versuchen und Goal-/Fehler-/Gesamtbudgets. Kartenmanager und Sidecar behalten ihre vorhandenen atomaren Einzelverträge; Abbruch zwischen beiden hinterlässt eine Rohkarte ohne Resume-Aufgabenstand, kein vollständiges Backup. Letztes gültiges Paar und gültige ältere Sidecarrevision erhalten. Keine stille Bindung an fremde Karte; Snapshot-Race konkret gemeldet. Laden passiv. Resume nur über explizites Prozessstart-Opt-in, originale Map-ID, neuen gültigen Auftrag, aktuelle Pose/Quellen und **frischen vorhandenen verifizierten globalen Lokalisierungsstatus** derselben Karte. TF/Ready-Bool allein genügt nicht. Ausfallzeit verbraucht Gesamtbudget; keine Versuchs-/Limitreset. Fehlender/ungültiger Resume überschreibt letzte Sicherung nicht.

**Tests/Build/Nachweise:** **65 neue Fälle**, **225 installierte Metriktests**, **1.751 betroffene Tests**, **1.664 registrierte colcon-Tests**, alle bestanden, keine Fehler/Skipped; Mengen überlappen. Frischer echter **Zehnpaketbuild**, anschließend Explorer-Neubuild und vollständiger Wiederholungslauf für letzte Deadline-/HOLD-Korrekturen. Ubuntu 22.04/Humble/Python 3.10.12/rclpy 3.3.22; localhost/Domain 230, network none, keine Geräte. Tatsächliche installierte Produktmodule/Config/Action bytegleich zum Quellcopy/Softwarecommit. Zwei echte DDS-Actionfälle belegen Erfolgs- und Cancel-Wirezustand; synthetische Karten/Scans/Pose und einzelne Nav-Gegenstellen bleiben Komponentenprüfung. Alle ursprünglichen Quellen-/Gate-/Geometrie-/Lifecycleverträge erneut geprüft. [Originalnachweise](evidence/ap05-20261003/README.md) mit Pflichtfallmatrix, roten AP-04-Ankunfts-/AP-05-Deadline-Gegenproben, sämtlichen Zwischenständen, Original-JUnit/Buildkommandos, Install-/Quellhashes und SHA256SUMS. CI-Auswahl ergänzt, Remote-CI nicht ausgeführt.

**Konkreter offener Plattformnachweis WE-M7:** Linux-Workspace ohne `swift`, `xcodebuild`, `xcrun`/Apple-SDK/Simulator. Native iOS-Build/Laufzeit und ergänzte Swift-Tests **nicht ausgeführt**; Python-Rosbridge-/ROS-Verträge sind kein Ersatz. Gemäß MASTERPLAN AP-05 bleibt dies separat offen und sperrt den unabhängigen Kernabschluss nicht.

**Grenzen/Rückfall:** Vollständige Mission/BT/Explorer/Nav2/SLAM-/Sensorkette und physische Start-/Mast-/Tür-/Tracking-/Stopplast weiterhin offen. Historischer synthetischer Graphprüfer nur an neue Resultassertionen angepasst, in AP-05 nicht neu abgenommen. Keine neuen Freiraumannahmen, Geometrie-/Fristlockerung oder Jetson-Profil-/Installänderung; ROBOT_TRANSFER unverändert. Rückfall ausschließlich eigene AP-05-Commits gezielt revertieren; AP-01–04 und fremde Arbeit erhalten.

**Genau nächster vorbereiteter Schritt: AP-06** gemäß MASTERPLAN v1.3 – zunächst vollständige bewegungsabhängige geschlossene Gesamtsoftwareprüfung mit den vorab festgelegten Szenarien/Startposen, anschließend separat technisch begrenzte Zielsystem-/Realabnahme. AP-06 **nicht begonnen**; der AP-05-Auftrag startet keine Robotertests. WE-M7-Nativprüfung bei verfügbarer Apple-Plattform zusätzlich schließen.

## Erhaltene Paketabschlüsse


## 03.10.2026 – MASTERPLAN v1.3 / AP-04 software_geprüft

**AP-04 software_geprüft auf Kandidaten-/Adapterebene.** Nutzer ausdrücklich „gut dann mach mit 04 weiter“. Saubere Basis `495b538`, Branch `feature/frontier-candidate-core`, Worktree `/workspace/Roboter_ws-ap04`; Softwarecommit **`5ee313b47ea2ef7c98554e42a9cae224a8a7d0ca`**. Originalcheckout und AP-01–03 sauber/unverändert. MASTERPLAN v1.3 bytegleich. Keine Hardware, Deployment, Push/Merge oder automatische AP-05-Arbeit. [AP-03-Auftrag bytegleich archiviert](archive/20261003-ap03/README.md).

**Entscheidung nach MASTERPLAN-Alternative:** Gepinnter unveränderter Fremdkern `mertgulerx/frontier_exploration_ros2@418e9717564a895214275e088ea7075b8ac88f64` wirklich gebaut, 134 Unit-Tests bestanden. Sein einziger Ringvorschlag scheitert an der gleichen Fahrzeugprüfung; am langen Rand bietet er unzureichend verteilte Sicht. Deshalb eigene Gewinnung begrenzt korrigiert und erneut verglichen: tatsächliche freie Randpunkte statt Schwerpunkt, mehrere räumlich getrennte Positionen, Annäherung zur bekannten freien Seite, aktuelle echte Scan-/TF-/Scope-/Reichweiten-/Maskenprüfung. Keine externe Runtimeabhängigkeit oder zweiter Navigator. `existing` bleibt Gesamtdefault; read-only `metric_candidate_source` wählt im expliziten metrischen Modus die Korrektur oder `legacy_centroid` als Rückfall. Bestehende Kontur-/Regler-/Quellen-/HOLD-/Kindverträge und Budgets erhalten.

**Abnahmen:** Alle sieben Pflichtfälle auf Kandidatenebene; Wachstum und Wiederbeobachtung über je drei Kartenstände. Unverändertes installiertes Original: Ring → `approach_unavailable` → null Ziele; korrigierte Gewinnung → fünf mit echtem Nav2 zulässige Alternativen. Langer Rand nach tatsächlicher vollständiger Pfadprüfung: **5,9 m** potenziell sichtbarer Rasterrand aus mehreren Eigenpositionen gegenüber **1,9 m** Fremdkern. Gleiche deklarierte endliche synthetische Sicht, Raster, Planung und Schutzbedingungen; kein gemessener Beobachtungsgewinn. **110 echte ComputePathToPose-Pläne**, **74** nach Produktgeometrie zulässig, davon **63** Eigenkorrektur; **36** unzulässige Zielgeometrien ehrlich verworfen. Kein FollowPath oder Motorpublisher. Ursprungrotation korrekt transformiert; Fremdbrücke lehnt sie explizit ab. Neue lokale Kartenevidenz nahe früherem Ziel liefert wieder Vorschläge; missionseigene Erledigung bleibt AP-05.

**Regression/Build:** **27 neue Fälle**. **1.636 betroffene Tests**, **165 gegen installierte Module**, **1.604 registrierte colcon-Tests** bestanden, keine Fehler/Skipped; Mengen überlappen. Frischer aktueller **Zehnpaketbuild**, frischer nativer **Achtpaket-Produktbuild**, unveränderter Fremdkern und CPP-Vergleichsbrücke gebaut. Neue und native installierte Produktmodule bytegleich zum Worktree. Echte Ubuntu-22.04/Humble-/Python-3.10-Laufzeiten, rclpy 3.3.22 bzw. native 3.3.17; keine Nachrichten-/Planerattrappen. Vorhandene AP-03-Nav2-1.1.20-Binärunterlage wiederverwendet, nicht als neuer Nav2-Build gezählt. CI ruft neue pytest-Datei auf; Remote-CI nicht ausgelöst.

**Originalnachweise:** [AP-04-Evidenz](evidence/ap04-20261003/README.md) mit Pflichtfallmatrix, allen nativen Pfaden/Planerlogs, Originalkern-Gegenbeispiel, gemeinsamen Eingaben, konkreten Befehlen, Pin/Lizenz, Image-/Installidentität und SHA256SUMS. Ein korrigierter neuer Minimalreichweiten-Test und erster nativer Prüferabbruch bleiben als Originalbelege erhalten. Keine Frist-/Reserveänderung, um grün zu werden. Historische unabhängige Python-3.12-/DDS-Befunde bleiben in AP-01/AP-03 erhalten.

**Grenzen/Rückfall:** Nur Kandidaten-/Adapter-/Planungssoftware geprüft. Potenzielle Sicht ist keine tatsächlich gemessene Beobachtung; native Plan-SUCCESS ohne volle Geometrie wurde abgelehnt. Mission/BT/Explorer/Nav2/Sensorkette, physische Start-/Mast-/Tracking-/Türabnahme und aktive Jetson-/Stopplast bleiben AP-06; AP-03-Simulationsprofil nicht für Hardware aktiviert. Große Karten oberhalb expliziter Kandidaten-/Sichtkapazität werden konkret blockiert, nicht als abgeschlossen gewertet. Alte missionseigene Erfolgs-Nachbarschaftssperre bleibt für **AP-05** offen. Rückfall nur eigene Software-/Dokumentcommits gezielt revertieren oder `legacy_centroid` beim gestoppten Start auswählen; AP-01–03 und fremde Arbeit erhalten. Kein Jetson-Installwechsel; ROBOT_TRANSFER unverändert.

**Genau nächster vorbereiteter Auftrag: AP-05** – Ankunft/Beobachtung/Erledigung trennen, begrenzte Wiederbeobachtung, ehrlichen Erfolgs-/Teilstandszweig und vorhandene Persistenz-/Verbraucherschnittstellen schließen. Noch nicht begonnen; eigene ausdrückliche Nutzerbeauftragung erforderlich. Vollständige Softwarekette und Hardwarequalifikation bleiben danach AP-06.

## 03.10.2026 – MASTERPLAN v1.3 / AP-03 software_geprüft

**AP-03 software_geprüft für die geschlossene synthetische Komponenten-/Bootstrapprüfung.** Nutzer hat AP-03 ausdrücklich beauftragt. Basis `875c7c4`, Branch `fix/nav2-bootstrap-geometry`, Worktree `/workspace/Roboter_ws-ap03`; Softwarecommit `c3115ff8ecb28b0828e1de8b8e062c6f0866f55e`. Originalcheckout, AP-01-/AP-02-Worktree sauber und unverändert. MASTERPLAN v1.3 bytegleich. Keine Hardware, kein Deployment/Push/Merge oder automatischer AP-04-Übergang. [AP-02-Auftrag bytegleich archiviert](archive/20261003-ap02/README.md).

**Umsetzung:** Ein ungültiger kürzester Eigenpfad schließt ein verbundenes bekanntes Ziel im neuen Opt-in-Profil nicht mehr dauerhaft aus. Er bleibt gekennzeichneter Nav2-Planungsvorschlag; vor jeder Vorausrichtung/Fahrt ist der tatsächliche Nav2-Pfad vollständig zu prüfen. Live/HOLD-Prüfung verwendet diesen tatsächlichen Pfad statt ihn durch eine andere Eigenroute zu verwerfen. Vorhandene NavFn-A*/RPP-Kombination nach Messung erhalten; kein weiterer Navigator oder Frontier-Kern. Numerische Sub-Halbzell-Endstücke erfinden keine Enddrehung.

**Geometrie:** Asymmetrischer Achsbezug, vollständiges Chassis x=−0,11…+0,31/y=±0,23 m und 0,02-m-Padding unverändert; halbe Zelldiagonale, 0,01-m-Interpolationsreserve sowie 0,15-m/±0,40-rad-Goalhülle bleiben geprüft. Neues schreibgeschütztes `rpp_rollout`-Simulationsprofil prüft tatsächliche berechnete Bewegungen einschließlich Drehen mit zusätzlich 0,02-m/±0,05-rad-Trackingband und erfordert aktivierte Vorausrichtung auf das erste tatsächliche Pfadstück innerhalb 0,02 rad. 17 echte Controllerparameter müssen passen. Bestehendes konservatives Profil bleibt Default. [Gemeinsamer Bewegungsvertrag](BEWEGUNGSVERTRAG.md).

**Geschlossene echte Nav2-Abnahme:** Acht Fälle bestanden. 68-/80-cm-Durchfahrt jeweils beide echte Actions erfolgreich, maximal rund 2 mm Tracking und mindestens 80/140 mm Abstand des gepolsterten Footprints. Längere 3,682-m-Umfahrung trotz verworfener Eigenroute erfolgreich, maximal 3,485 mm Positions-/0,005011 rad Headingabweichung und 201 mm Abstand. Vorbestimmte Tür-/Umfahrungsziele sind Komponententests, keine autonome Wohnungserkundung. Unzulässige 56-cm-Durchfahrt und Rotation im 68-cm-Spalt trotz NavFn-Punktpfad vor FollowPath verworfen; unbekannter Außenraum vom tatsächlichen Planer abgelehnt. Keine Nichtnullkommandos in diesen Negativfällen. Rückwärtsanteil sämtlicher positiver Fälle null.

**Autonomer Bootstrap:** Tatsächlicher bestehender Frontierdetektor/Approach/Policy wählt selbst einen ersten Beobachtungspunkt; Vollscan bei unbeobachtetem hinterem Außenraum gesperrt. Echte Nav2-Regelbewegung gewinnt im endlichen verdeckungsgeprüften synthetischen Sichtmodell 0,454 m² neue beobachtete Fläche. Fehlende initiale Kontur ergibt `wait` mit 168 fehlenden Zellen je Quelle, keine identischen Start-/Scanwiederholungen. Eigenkörper-/Egress-Ausnahmen und AP-02-Invalidierung bleiben erhalten. Separates begründetes reales Sensorpositions-/Abdeckungspaket im Bewegungsvertrag nur vorbereitet.

**Tests/Build:** 22 neue aussagekräftige Regressionen; Gegenprobe auf Original-AP-02: 18 erwartete Fehlschläge, 4 negative Fälle bestanden. Aktuelle AP-02-basierte Humble-Laufzeit: 138 Installtests, **1.609 betroffene Tests** einschließlich aller fünf echten DDS-Callbackfälle und **1.577 colcon-Tests** fehlerfrei; echter Zehnpaketbuild mit neuen Repo-/Nav2-Aktionsbindings und geprüfter Install-/Quellenidentität. Zusätzlich echte native Nav2-Planer-/Controller-/Pluginbuilds (14 Pakete) und acht Repo-Pakete in getrennter Installation. Mengen überlappen. CI-Auswahl und echter Nav2-Prüfjob ergänzt; kein GitHub-Lauf. [Vollständige Originalbelege und Reproduktion](evidence/ap03-20261003/README.md).

**Beobachtete Grenze:** Zwei Sammelläufe und ein erster Einzelversuch eines unveränderten engen DDS-Timingtests schwankten im älteren Nav2-Prüfimage (u.a. rclpy 3.3.17). Vier spätere Einzelprozesse dort sowie alle fünf Fälle und der vollständige Abschlusslauf auf AP-02-Laufzeit (rclpy 3.3.22) bestanden. Fehllogs erhalten; keine Ursachengarantie, kein allgemeines Last-Grün und keine Frist-/Schutzlockerung. Aktive Jetson-/Worst-Case-Abnahme bleibt AP-06.

**Offen:** Physische Türen/Startabdeckung und echte Motor-/Tracking-/Stopplast. Simulationsantwort 50 ms und 25-ms-Schrittkappe sind kein Nachweis für die reale 2000-ms-Antriebsrampe, Smoother, Schlupf und Sensor-/TF-Latenzen. Gesamte ExploreArea-/BT-/Mission-/Sensor-/Gatekette und Wohnungsvollständigkeit nicht als abgenommen ausweisen. Das Simulationsprofil ist nicht am Jetson aktiviert.

**Rückfall:** Nur eigene AP-03-Software `c3115ff` und zugehörige Dokumentation gezielt revertieren; AP-01/AP-02, Main/Jetson und fremde Arbeit erhalten.

**Genau nächster Schritt:** AP-04 gemäß MASTERPLAN v1.3 als eigenen begrenzten Softwareauftrag beauftragen. Keine automatische Frontier-Integration, Profilaktivierung oder Fahrt aus diesem Abschluss.

---

## 03.10.2026 – MASTERPLAN v1.3 / AP-02 software_geprüft

**AP-02 software_geprüft.** Nutzer hat AP-02 nach AP-01 ausdrücklich beauftragt.
Keine Hardware, kein Deployment/Push/Merge und kein automatischer AP-03-Übergang.
MASTERPLAN v1.3 bleibt bytegleich; sein ursprünglicher AP-01-Einstieg ist durch
AP-01-Abschluss und den ausdrücklichen Folgeauftrag abgearbeitet.

**Basis/Lieferung:** AP-01-Abschluss `45f268a` auf der bestätigten Integrationsbasis
`08a4b9a`; sauberer eigener Worktree `/workspace/Roboter_ws-ap02`, Branch
`fix/map-lifecycle-source-contract`. Softwarecommit
`96bbd4d8ed6d0b7a3ca6816d7c5fae14c27f45d4`. Originalcheckout und AP-01-Worktree
unverändert. [Aktueller abgeschlossener Auftrag](AGENTENAUFTRAG.md),
[bytegleich archivierter AP-01-Auftrag](archive/20261003-ap01/README.md).

**Konkrete Reparatur:** Raster-/Ursprungs-/Quaternionwechsel verwerfen alte
Egress-/betroffene Body-Evidenz vor Arrayoperationen, ohne Re-Ankern. Normale
passend korrelierte Folgeupdates erhalten neu geprüfte Weltziele. Exakte
Rohkarten-/Statusjoins ersetzen den aktiven Ersatzjoin mit alter Revision;
identischer Inhalt darf eng begrenzt den letzten exakten Snapshot innerhalb
seiner ursprünglichen Fristen erhalten. Verspätete Rohkarten überschreiben
auch den generischen Explorerstand nicht. Sitzungs-/Frame-/Auflösungs- und
beobachtete Rückwechsel sperren alte Arbeit und verspätete Plan-/Kindresultate.
Quellen-, Pose- und Scanfrische wird nach Verarbeitung erneut geprüft.
Der echte Kartenmanager erhält konsistente Beobachtungsrevisionen bei
Duplikaten und verwirft alte positive Stempel ohne Frische-/Revisionserneuerung.

**Gemeinsamer Vertrag:** [Karten-/Quellenbudget](QUELLENVERTRAG.md) ordnet HWT,
Encoder, TF, Gate und Explorer über Empfang, IO, Verarbeitung, DDS, Frische
und Kontinuität zu. Aktiver/passiver Pfad getrennt; bestehende Fristen,
Timingkern und AP-01-Clockvertrag erhalten. Kein allgemeiner Health-/Executor-
Umbau und keine vorgezogene AP-03-/AP-04-Geometrie-/Controller-/Frontierintegration.

**Abnahme:** 55 neue echte Lifecycle-/Produzenten-/Elternschleifenfälle:
100×100 → 100×101, Wachstum mit verschobenem Ursprung, Rohkarte/Costmap,
Auflösungs-/Sitzungs-/Frame-/Quaternionwechsel und Rückwechsel, verspätete
Arbeit, notwendige Quellen verloren, gültige Folgeupdates. Keine Arrayausnahme,
keine falsch gültige alte Maske und keine neue Freiraumannahme. Nav2-`success`
nach Quellenausfall/Kontextwechsel zählt keinen Besuch; gültiges Ziel bei
harmlosem Wachstum bleibt ausführbar.

**Ausgeführte Prüfung:** 1.587 betroffene Pytesttests bestanden, 116 gezielte
Tests gegen das neue Installationspräfix bestanden (einschließlich 55 neuer
Fälle), 1.555 registrierte colcon-Tests ohne Fehler/Fehlschläge/Skipped.
Mengen überlappen. Zehn Pakete mit echten Humble-/Nav2-/robot_interfaces-
Bindungen gebaut; Modul-/Paketauflösung und installierter Code geprüft.
Der Kartenmanager registriert nun tatsächlich seine 53 Map-Core-Tests für
colcon. Gegenprobe auf unverändertem AP-01-Stand: 30 erwartete Fehlschläge,
1 bestandener Fall, 24 abgewählte Fälle. Passende bestehende CI-Trigger und
Pytestauswahl ergänzt; GitHub-Actions nicht gestartet.

**Originalbelege/Reproduktion:** [AP-02-Evidenz](evidence/ap02-20261003/README.md)
mit Build-, Import-, Codehash-, Test-, Baselineausgaben, exaktem Skript,
Umgebung und SHA-256-Manifest. Der anfängliche Voll-`src`-Discoverybuild
scheiterte an nicht gebauten transitiven Launchpaketen; der explizite betroffene
Zehnpaketausschnitt wurde anschließend vollständig gebaut, ohne Dummy-Präfixe.
Dies belegt keinen kompletten Nav2-/BT-/Hardwarelaunch. Der bekannte
Python-3.12-JSON-Baselinefehler aus AP-01 bleibt unverändert außerhalb der
Humble/Python-3.10-Abnahme. Keine pauschale Gesamt-Grünbehauptung.

**Grenzen/Rückfall:** WE-M0 und betroffener metrischer WE-M3-Softwareanteil;
keine vollständige Meilenstein-, Zielsystem-, Start-/Geometrie-, Semantik- oder
Hardwareabnahme. Belastbare aktive Jetson-/Vollstackzeit bleibt AP-06.
Keine Runtimeänderung auf Jetson, deshalb kein neuer ROBOT_TRANSFER-Eintrag.
Nur eigene AP-02-Software-/Dokumentcommits gezielt revertieren; AP-01 erhalten,
keine fremde Arbeit oder pauschalen Altbranch zurücksetzen.

**Genau nächster Schritt:** AP-03 „Bewegung und autonomer Start zusammenführen“ gemäß MASTERPLAN als
separaten Auftrag mit echtem Nav2-Planer-/Controllerpfad und geschlossenem
synthetischem Bootstrap-/Geometrieprüfstand vorbereiten. Hier nicht ausgeführt
oder automatisch aktiviert; keine weitere Code- oder Hardwarearbeit aus AP-02.

## Historie

## 03.10.2026 – MASTERPLAN v1.3 / AP-01 software_geprüft

**AP-01 software_geprüft; Zielsystem, reale Sensor-/Start-/Geometrieabnahme und Wohnungserkundung weiterhin offen.** Kein Hardwarezugriff, Deployment, Push oder Merge. AP-02 ist ausschließlich als Übergabe vorbereitet.

**Basis und Lieferung:** Remote `feature/hwt-hold-recovery-resume` am 03.10.2026 auf `08a4b9ac0b7a128ced2199f20976f3aa92ea55fe` bestätigt. Ursprünglicher lokaler Checkout `work`/main `05439c7` sauber und unverändert belassen; isolierter Worktree `/workspace/Roboter_ws-ap01`, Branch `fix/hwt-clock-correlation`. Keine unbekannten lokalen Änderungen auf der Integrationsbasis. Dokumentübernahme `84abfc6`, geprüfter Softwarecommit `c797442b37994f774df40b6b27d54c27efa3bdc3`. Keine aus einem Branch abgeleitete Jetson-Installationsbehauptung. WE-D0/WE-M0 und betroffener WE-M3-Recoveryanteil.

Kanonisch: [MASTERPLAN v1.3](MASTERPLAN.md), [abgeschlossener AP-01-Auftrag](archive/20261003-ap01/AGENTENAUFTRAG.md), [Meilensteine](MEILENSTEINE.md), [LAB-1](../LABORMODUS.md). Die vier Vorgängerdateien sind mit Commit-/Blob-/SHA-256-Beleg [bytegleich archiviert](archive/20261002-v1.2/README.md); MASTERPLAN entspricht dem Anhang bytegleich. AGENTS/Meilensteine/Gesamtstrategie und PROJECT_MEMORY gezielt synchronisiert, begrenzte AP-04-Erlaubnis ausdrücklich übernommen. ROBOT_TRANSFER unverändert.

### Reparatur und Zeitvertrag

Produktänderungen nur in `hwt601_imu_node.py` und dem privaten `_hwt601_clock.py`. Transport, Guard/Health, Encoder, EKF, Bias, Profile, Mission/Explorer und Recoverycode unverändert. Der echte Transport bleibt vollständiger Hostempfangsbeleg, nicht interner Sensorabtastzeitpunkt. Fehlender/ungültiger Empfangs- oder Transaktionsbeleg wird jetzt hart zurückgewiesen; kein Fallback auf Verarbeitung/Veröffentlichung.

Monotonic rahmt die ROS-Abfrage ein. Präzise Offsetspannen werden geschnitten; ein Bracket von höchstens **1 ms** und höchstens **drei** sofortige Versuche innerhalb derselben echten Transaktionsfrist. Unterer Offsetrand gibt konservativ höchstens 1 ms + 2 ns früheren Empfangsheader; kein Futurefehler durch wechselnden Mittelpunkt. Die Grenze entspricht 1/10 des nominellen Probenabstands und 1/100 der unveränderten Biaskontinuitätsgrenze. Größere Brackets werden verworfen, ohne letzten gültigen Empfang/Header/Samplehistorie zu ändern oder den Transport zu schließen. `clock_correlation` unterscheidet Unsicherheit und Zeitbasisänderung.

Disjunkte Belege bleiben harte Zeitfehler, auch wenn Header noch steigen; keine Neubasierung. Aktive ROS-Time/`use_sim_time`, Clockobjekt-/Typwechsel sowie zwischen Polls aktivierte/deaktivierte ROS-Time werden konservativ gesperrt. Unterstützt: unveränderte Host-SYSTEM_TIME oder inaktive ROSClock mit Hostzeit. Sprünge unter Messunsicherheit sind nicht garantiert erkennbar; der Hostvertrag verlangt denselben laufenden Taktbezug. Siehe [ausführlichen Clockvertrag](../../src/robot_state_estimation/README.md#ap-01-hostempfang-und-clockvertrag-masterplan-v13). Entwicklung bleibt bei harten Fehlern terminal; Legacy-Hard-/Reconnectbehandlung bleibt erhalten.

Unverändert: Entwicklung 50 ms Antwort/Gesamtablauf und 300 ms Rohfrische; Legacy 30/200 ms; Encoder 120/180 ms; Bias-/HOLD-/Recoverygrenzen. Messagebau/Paarungsversuche werden ebenfalls vor Veröffentlichung gegen die Gesamtdeadline geprüft. Wiederholte Unsicherheit führt durch das Alter der letzten echten Probe zur bestehenden Health-HOLD-Reaktion.

### Vorher/Nachher und Pflichtfälle

[Originalmethoden vor Reparatur](evidence/ap01-20261003/ap01-original-method-proof.json): erster Header `1010,000 s`, zweiter echter Empfang `1010,010 s`, nach ROS-Abfrage 20 ms Pause → berechnet `1009,990 s`, terminal `HWT-Messzeit nicht monoton`, Transport geschlossen, nur ein veröffentlichter Wert. [Gewünschter Regressionstest rot](evidence/ap01-20261003/ap01-before.log).

[Reparierte Methoden aus dem Install](evidence/ap01-20261003/ap01-repaired-method-proof.json): zweite Paarung bei monotonic `10,030 s` gültig, Header bleibt exakt Empfang `1010,010 s`; spätere Probe `1010,040 s` ebenfalls veröffentlicht. Drei akzeptierte Werte, null verworfene Werte, kein Terminalfehler, Transport offen. Keine Testnachbildung der Poll-/Fehlerentscheidung.

| Pflichtklasse | Tatsächlicher Nachweis in `test_hwt601_time_correlation.py` |
|---|---|
| Präzise +10 ms, wechselnde kleine Brackets | exakter Empfangsbezug; kontinuierlicher gültiger Strom, zwei konstante Offsets, Fehler ≤1 ms |
| Originalpause, Verzögerung vor/in/nach Paarung, konstant/wechselnd groß | korrekt datiert; erneute präzise Paarung statt Mittelpunktprojektion |
| Unbrauchbar → präzise, wiederholt unbrauchbar | kein Zwischenwert/Reset; letzte gültige Daten altern, nächste echte Probe verarbeitet |
| Transaktions-/Verarbeitungsfrist | 30-/50-ms-Gegenfälle für Verarbeitung, Retry, Dekodierung und Messagebau; keine Publikation |
| Fehlend/NaN/Inf/zukünftig/rückläufig/wiederholt | echte Poll-/Fehlerlogik weist Beleg zurück, kein Ersatzzeitpunkt |
| Unabhängige ROS-Sprünge, kleiner als Probenabstand | ±2/±20 ms bei steigender monotonic erkannt; selbst bei weiter steigenden Headern terminal |
| Tatsächliche Clock-API/Quellenwechsel | echte ROSClock/TimeSource und unabhängige Overrideänderung; Aktivierung/Deaktivierung auch zwischen Polls erkannt |
| Verbundene Verbraucher | echte Guard-/Health-Zeitprüfung akzeptiert erzeugte Header bei 0/0,05/2 ms Zustellung; Future-Gegenfall bleibt hart; echte Alterung bewirkt HOLD |
| Transport/Schutzwirkung | echter serieller Produkttransport + synthetische Gegenstelle, ganz/fragmentiert und verzögerte Dekodierung; CRC/Identität/Timeout bestehend, Sättigung zusätzlich |

### Befehle, Ergebnisse und Auflösung

Vollständige Aufrufe: [ap01-run-final.sh](evidence/ap01-20261003/ap01-run-final.sh). Plattform und Präfixmapping: [Evidenzregister](evidence/ap01-20261003/README.md). Ubuntu 22.04/x86_64, echtes ROS Humble, Python 3.10.12; localhost/Domain 226 für DDS-Tests. Keine Geräte eingebunden.

| Ausführung | Ergebnis | Originalbeleg |
|---|---|---|
| `colcon build --packages-select nav2_common nav2_msgs amadeus_map_identity explore mission_manager robot_state_estimation robot_interfaces base_hardware`, getrennte Build-/Installpräfixe | 8 Pakete bestanden | [Buildlog](evidence/ap01-20261003/ap01-verified-build.log) |
| `pytest` neue Clock-/Rawtests, nur Testpfad plus frisches Install | 58 bestanden, davon 52 neue AP-01-Fälle | [Installtests](evidence/ap01-20261003/ap01-regressions-installed.log) |
| `pytest` vollständige state/base-Tests, Gate-Integration/pending-wheel/source-callbacks, HWT-Recovery/Kindpolitik/Kindvertrag, Mission-HWT und JSON | **443 bestanden** | [Regressionen](evidence/ap01-20261003/ap01-regressions-final.log) |
| `colcon test` state/base und `colcon test-result --verbose` | **381 Tests, 0 Fehler/Failures/Skips** | [Registrierte Ergebnisse](evidence/ap01-20261003/ap01-colcon-results.log) |

Mengen überlappen; nicht addiert. Neue Tests laufen bereits in `.github/workflows/hwt601-we.yml`: PR-Pfadtrigger `src/robot_state_estimation/**` und `python3 -m pytest -q src/robot_state_estimation/test ...`. Kein unzureichender unittest-only-Aufruf; keine CI-Neugestaltung nötig. Colcon hat die neuen 52 Fälle tatsächlich gesammelt. Hosted CI wurde mangels Push nicht neu ausgelöst.

[Importauflösung](evidence/ap01-20261003/ap01-imports-installed.log): Raw/Clockhelper aus `/evidence/ap01-install/robot_state_estimation/lib/python3.10/site-packages`; `robot_interfaces` aus neu gebautem `/evidence/ap01-install/robot_interfaces/local/lib/python3.10/dist-packages`; Standardnachrichten/rclpy aus `/opt/ros/humble`. Weitere Verbraucherprüfungen nutzen aktuellen Worktreecode und diese echten Nachrichtenbindungen. Fünf relevante Quell-/Installmodule [bytegleich mit SHA-256 geprüft](evidence/ap01-20261003/ap01-byte-manifest.json). Container `/evidence` entspricht Host `/workspace/scratch`, `/repo` dem isolierten Worktree; kein alter main-Import. Entwicklungs-/Legacyparameter sind explizit in den Fixtures gesetzt; kein behauptetes geladenes Jetsonprofil.

**Unabhängiger Baselinefehler:** Python 3.12.14 / Missionmanager-JSON-Tiefentest nimmt 2.000 verschachtelte Arrays an. [Vorher](evidence/ap01-20261003/ap01-json-before-python312.log) und [nachher](evidence/ap01-20261003/ap01-json-after-python312.log): je 4 Tests / 1 Fehler, Produkt-/Testbytes unverändert. Unter Humble/Python 3.10 besteht derselbe Test in den 443. Nicht behoben, nicht gelöscht/übersprungen oder als Python-3.12-Erfolg gezählt; außerhalb AP-01 und kein Blocker dieses geprüften Zeitpfads.

### Grenzen, Rückfall und genau ein nächster Schritt

Keine Zielsystem-, aktive Last-, Sensor-/Start-/Geometrie- oder Fahrabnahme. Der historische Roboterabbruch ist nicht abschließend erklärt; nur das konkrete Projektionsgegenbeispiel ist behoben. Keine vollständige EKF-/Robotergrafabnahme behauptet; direkte echte Verbraucherkomponenten erfüllen den begrenzten Zeitvertrag. Keine private Wohnungsevidenz übernommen.

Rückfall: eigenen Softwarecommit `c797442` gezielt revertieren und Paket im getrennten Präfix neu bauen; der dokumentierte Originalfehler kehrt dabei zurück. Keine pauschale Branch-/Installrücksetzung. Dokumentübernahme ist unabhängig prüfbar. Laufende Roboterkopie und ROBOT_TRANSFER unverändert.

**Genau nächster Schritt:** den vorbereiteten begrenzten **AP-02-Auftrag** zu Kartenlebenszyklus/Quellenvertrag gemäß MASTERPLAN v1.3 beauftragen. Konkrete betroffene Pfade und Akzeptanzfälle stehen in der [AP-02-Übergabe am abgeschlossenen Auftrag](AGENTENAUFTRAG.md#ap-02-übergabe-vorbereitet-nicht-ausgeführt). Keine automatische Implementierung oder Fahrt.

Der folgende vollständige STATUS ist ausschließlich Historie bis `08a4b9a`; dortige „aktuelle“ Überschriften, Aufträge und Runtimeangaben gelten für den damaligen Stand.

---

# Wohnungserkundung – aktueller Status und nächster Auftrag

**WE-1 · Stand 01.10.2026 · MASTERPLAN v1.2 · Stufe 3 weiterhin OFFEN**

Maßgeblich: [MASTERPLAN](MASTERPLAN.md), [AGENTENAUFTRAG](AGENTENAUFTRAG.md), [LAB-1](../LABORMODUS.md), [MEILENSTEINE](MEILENSTEINE.md). Dies ist der einzige aktuelle WE-Iststand. Die ausführliche bisherige Statusdatei ist [bytegleich archiviert](archive/20260930-v1.1/STATUS.md); alte Abschnittsnummern und „nächste Schritte“ dort sind historische Referenzen.

**Aktueller Abschluss:** HWT-Entwicklungsvertrag und Start-Egress auf `a6f31bf`
implementiert; 1.564 Regressionen, gerätefreier Drei-Ziel- und HOLD-Produktgraph
bestanden. Kurzer Realstart: HEALTHY nach 36,379 s, terminale Messzeitprüfung
bei 54,880 s; aktuelle Geometrie verwirft alle 22 Kandidaten. Keine reale
Mission. Quellenzeit und konkrete Bewegungsgeometrie blockieren unabhängig.
ROS beendet, Rechner eingeschaltet; Einzelgrenzen im neuen Abschluss unter §4.

**Abschluss des vorigen Pakets 01.10.2026:** Adaptiver metrischer Bootstrap und begrenzte
Encoder-Timing-Recovery auf `fd883fd` softwareseitig geprüft. Gemeinsamer realer
Vorlauf negativ: dritte HWT-Störung erschöpft das Budget; unabhängig davon 33
unbekannte Startkonturzellen / 0,021089 m² Außenanteil, kein zulässiger Startkandidat.
Keine reale Mission. Einzelbelege, voller negativer Dauertest und Grenzen im
neuen Abschluss unter §4 sowie AGENTENAUFTRAG §10. **System bleibt eingeschaltet.**

## 1. Aktuelle Nutzerentscheidung

Normale Erkundung wird metrisch organisiert: beobachten → erreichbare Frontier-/Beobachtungsposition wählen → navigieren → neue Beobachtung und Ergebnis bewerten → nächste Aufgabe. Portal-/Raumsemantik ist keine Pflicht für normale metrisch sichere Ziele. Geometrie, Karte/Pose, Scope, Sensor-/Antriebsgesundheit und Schutzkette bleiben verbindlich.

**GRÜN: METRISCHER ERKUNDUNGSKERN – GERÄTEFREI INTEGRIERT BESTANDEN.** Implementiert als explizites `metric_frontier`-Backend im bestehenden Explorer. Default bleibt `existing`. Beim anschließend beauftragten Realnachweis wurden reale Sensor-/ROS-Prozesse im rein lesenden Vorlauf gestartet; dieser blieb blockiert, keine aktive Fahrt oder Mission, kein dauerhafter Installwechsel. Stufe 3 bleibt **OFFEN**. Konservative Geometrieprüfung bleibt verbindlich; reale Zielerreichung, Türpassage und Robustheit sind nicht aus den Softwaretests abgeleitet.

**Historischer Abschluss des vorigen Pakets (01.10.2026):** Ausgang `cf55cea`,
Funktionskandidat `8f5eeb4`, bestehender Branch/PR #105. 1.469 Regressionen
bestanden; Radübernahme, Uhrzuordnung und ganze Eigenkörperzellen gezielt
korrigiert. **Realer 720-s-Gesamtvorlauf negativ, keine Mission/Fahrt.**
Letzter Fehler nach zwei echten HWT-Recoveries: 120,874 ms verworfenes
Encoderpaar, anschließend 212,127 ms alte letzte zulässige Radprobe am Gate.
Unveränderte 120-/180-ms-Grenzen sperren richtig. Geometrie unabhängig davon:
211 unbekannte Rundblickzellen, 0,188420 m² Außenanteil; bereits Anfangskontur
unzulässig. Genaues Ergebnis und Restumfang im aktuellen Abschluss unter §4,
Auftragsabschluss in AGENTENAUFTRAG §9. Der folgende adaptive Auftrag hat diesen
Restumfang gezielt ersetzt; alte Messungen bleiben unverändert erhalten.

## 2. Belegter Ausgangspunkt

| Stand | Beleg / Grenze |
|---|---|
| Remote-Dokumentbasis vor v1.2 | PR #105, feature/hwt-hold-recovery-resume, `99d21c012dfe4c28d8263f7cd5e16505b07736d6`; keine Aussage über aktuelle lokale Runtime |
| Letzter ausgewerteter realer Kandidat | `492ef20`, Ergebnis `d480243`; vollständiger zweiter Lauf stage3-map-handoff-20260929/real-repeat |
| Historischer Funktionsvergleich | `1d91229dc10ff4bb791938d49aae8e9808a5dfff`; [WE_PARITY_RESET](../WE_PARITY_RESET.md) dokumentiert Frontierfahrten, verbundenen Türübergang und weitere Frontiers danach |
| Erster HWT-Recoveryfall | Gerätefreier aktiver Kindzielvertrag und reale Rundblick-HOLD/Recovery/Fortsetzung im dokumentierten Umfang akzeptiert; kein umfassender Robustheitsnachweis |
| Aktueller Erkundungserfolg | Kein bestandener zusammenhängender A/B/C-/Mehrraumlauf; kein Ziel- oder Türerfolg des letzten Laufs |
| Neues metrisches Backend | Software und Mast-/Encoderkorrekturen auf `8be0709` regressiert; gemeinsamer realer Vorlauf weiter negativ, kein Fahrnachweis |

Aktuelle und historische Modul-/Installpräfixe aus ROBOT_TRANSFER und den erhaltenen Manifesten ermitteln, nicht aus Branch-Namen ableiten. Bestehende Builds und unbekannte lokale Änderungen nicht überschreiben. Die Abnahme eines neu kombinierten Kandidaten wird nicht aus historischen Einzeltests zusammengesetzt.

## 3. Offene Befunde bleiben erhalten

Der letzte vollständige Lauf hielt ein autonomes Frontierkind bis zum Kindtimeout; kein SOURCE_INVALIDATED und kein HWT-first_fault. Keine erledigte Aufgabe, keine Portalquerung, kein Regionwechsel. SlowZone gab 30 % aus; kleine Bewegungen reichten im Offline-Progress-Checker-Replay, nicht für Zielerreichung. Nicht mit externer Bewegungsvermessung gleichsetzen.

Softwareseitig blieb der Portalbestand in 327 Statusmeldungen leer; 296 Gegenproben fanden ebenfalls keinen Kandidaten. Der aktive Analysepfad verwendete 0,20 m statt der separaten historischen Analyse bis 0,40 m. Das ist ein Vergleichsbefund, kein bewiesener alleiniger Auslöser und kein Auftrag, Grenzen blind anzugleichen. Die konkrete physische Tür ist dem Datensatz weiterhin nicht eindeutig zugeordnet.

Die SlowZone-Punkte lagen räumlich auch in den Costmaps. Ein sicherer physischer Ausweg ist damit nicht bewiesen. Warum der reale Timeout zu SYSTEM_FAILURE statt möglicher lokaler Aufgabenrückstellung führte, ist mangels interner Erstentscheidung nicht abschließend rekonstruiert. Positive Offline-Snapshots ersetzen nicht den damaligen Callbackzustand. Abweichungen von Drehsoll/-rückmeldung, Objektidentität und Shutdownfehler bleiben offen, nicht als harmlose Nebeneffekte wegdefiniert.

Originalwerte, Szenarien, Tests und Messgrenzen: [voriger STATUS, Abschnitt 7](archive/20260930-v1.1/STATUS.md#7-nächster-schritt-und-historie). Vollständige lokale Auswertung: `~/.local/share/amadeus/tests/stage3-door-obstacle-offline-20260930/`. Private Rohdaten bleiben lokal.

## 4. Softwareabschluss und Nachweise

Basis: veröffentlichter `1dbbdaa`, unabhängiger Checkout der bestehenden Integrationslinie; kein privater lokaler Bericht als Vorfahr. Änderungen: `explore_node.py`, neue `metric_frontier.py` und `metric_frontier_runtime.py`, explizites Overlay `metric_frontier_params.yaml`, Regression `test_metric_frontier.py` und verbundener Graph `tools/sensorfusion/metric_frontier_product_graph.py`. Modus-/Schnittstellen-/Wiederverwendungszuordnung: [Explore-README](../../src/explore/README.md#explizite-metrische-strategie-masterplan-v12).

Wiederverwendet: tatsächliche Frontiercluster, sichere Annäherungsziele, geodätische Distanz, freie Rastersegmentprüfung und vorhandene Bewertungsgewichte; aktuelle Kartenidentität/Scope, Quellenbeobachter, Nav2-Einzelkind, Scan/Vorausrichtung, HOLD/Stillstand/Gate-ACK. Kein zweiter Navigator und kein semantischer Aufgabenbesitzer im metrischen Modus. Der gepaddete asymmetrische Fahrzeugumriss wird einschließlich Drehungen auf Rohkarte **und** Costmap geprüft. Unbekannte Zellen bleiben gesperrt.

**Build:** sechs Pakete (`explore`, `robot_navigation`, `robot_state_estimation`, `mission_manager`, `robot_map_manager`, `amadeus_map_identity`) isoliert unter `~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/install`, ROS Humble plus dokumentiertem Vollunderlay. BT läuft aus `hwt-child-scope-20260928-retry/install`; Graph protokolliert alle aufgelösten Präfixe. Kein Install in der laufenden Arbeitskopie.

**Regression:** 1.342 pytest-Tests bestanden; zusätzlich registrierte colcon-Tests: 1.242, null Fehler/Failures/Skips. Neue metrische Regression: 21 Tests, unter anderem räumliche Retries, unbekannte/enge Wege, asymmetrischer Footprint, Scope-/Owner-/Budget-Ablehnung, verspätete Actionannahme und alte Karten. Reale ROS-Node-Tests erzwingen localhost und Domain 200–230 vor Initialisierung. Ausführung hier Domain 226, Graph Domain 224; konfigurierte DDS-Peers entfernt.

Ein Neustart der Ausführungsumgebung verlor die temporären `/tmp`-Artefakte und unterbrach den Abschlusslauf. Der Kandidat wurde am dauerhaften lokalen Testpfad erneut gebaut; maßgeblich sind dessen abschließende Logs, nicht verlorene Zwischenläufe.

Ein erster wiederholter HOLD-Reiz vor frischer wiederhergestellter Yaw-Messung endete korrekt an zusätzlicher ungültiger Quelle. Die Fixture wartet jetzt auf gemessene Wiederherstellung vor dem zweiten Rohdatenreiz; Originallauf bleibt unter `graph-hold-before-stable-fixture` erhalten. Produktgrenzen wurden dafür nicht geändert.

Der zusätzliche Rundblickfall legte einen vorzeitigen Abbruch am gemessenen `vl53_triplet_unmatched`-Publikationsfenster offen (`graph-scan-first` und `graph-scan-diagnostic`). Dieses Fenster wird jetzt wie in der Navigation vom echten Gate gesperrt, ohne das gesamte Scanverfahren sofort als Fehler zu beenden; tatsächlich stale/ungültige Quellen bleiben terminal. `scan_route` prüft eine echte Rohkartensperre während des Scans ohne Nav2-Kind.

Der erste korrigierte Scan lief mit einem festen 10-ms-Synthesetakt und 12-s-Testbudget in Timeout (`graph-scan-fixed-tick-model`). Die Fixture integriert jetzt tatsächliche verstrichene Zeit aus den gegateten synthetischen Ausgängen; 0,3-rad-Scanbudget 28 s ausschließlich im Test. Produktprofil weiterhin 360°/280 s. Das ist synthetische Modellbewegung, keine externe Vermessung des Roboters.

**Verbundener Produktgraph (16 Fälle bestanden):** Mission Manager → tatsächlicher BT → Explorer → Nav2-Testgegenstelle; tatsächlicher Kartenmanager, HWT-Shadow und Mission-Gate. Synthetisch sind Raster, physische Eingangsmeldungen und Nav2-Gegenstelle. Kein Zielkandidat, Portal, Region oder Taskgesundheitsadapter wird eingespeist. Lokale Belege `~/.local/share/amadeus/tests/metric-frontier-20260930/software-final/graph-<Fall>/result.json` und Prozesslogs; Szenen sind gerätefrei.

| Pflichtfall aus AGENTENAUFTRAG §4 | Ausgeführter Beleg |
|---|---|
| 1 Ohne Semantik | `chain`: autonome Auswahl ohne Pflichtfeeds; widersprüchlicher optionaler Shadowstatus wirkungslos |
| 2 Beobachtungsschleife/offene Verbindung | `chain`: drei erreichte Aufgaben aus veränderten Rastern im selben Elternauftrag; maximal ein Kind, Verbindung ohne Türlabel |
| 3 Unerreichte Aufgabe/Alternative | `blocked`: tatsächliche erste Policywahl abortiert; terminales Kind, frischer Stillstand und Betriebssnapshot, danach anderes Rasterziel |
| 4 Kriechen/Budget | `budget`: kleine synthetische Drehbewegungen mit tatsächlich publizierten Gyro-/Odomeldungen setzen absolute Aufgabenfrist nicht zurück; gesunder Zustand erlaubt begrenzte Alternative |
| 5 Laufende Karte | `chain` erhält gültiges Kind trotz Updates; `route` storniert bei ungültigem Weg, `scan_route` beendet unzulässigen Scan; Unit-Regression verhindert Übernahme alter Raster/anderer Karte |
| 6 HOLD/Cancel | `hold`: wiederholte kurze Quellenausfälle, unveränderte HOLD-Frist, Bewegung sperrt Resume, Stillstand/Gate-ACK erlauben neues Kind derselben Aufgabe; `late`, `cancel_failed` |
| 7 Harte Gegenfälle | `estop`, `sensor`, `actuator`, `pose`, `map`, Nutzerabbruch, nicht terminales Kind; Scope/Footprint/Budget zusätzlich Regression und `empty`/`filtered` |
| 8 Abschluss/Migration | `empty`: vollständig bekannt nur metrischer Abschlusskandidat/Teilstand; `filtered`: unbekannter Rest ohne Abschlusskandidat; überall keine Speicherfreigabe und kein Gesamt-/Semantikerfolg |

Der abschließende `chain`-Lauf erreichte die ersten drei Aufgaben und nahm vor dem kontrollierten Testende noch ein viertes Kind an; dieses wurde terminal gecancelt. Beispiel der ersten drei Aufgaben (ausschließlich synthetische Koordinaten): `(1.05, 0.05)` → gemessene Zielerreichung/neue Karte → `(2.55, 0.05)` durch rastergeprüfte offene Verbindung → neue Karte → `(4.05, 0.05)`. In `blocked` lautet die erste Entscheidung `task_unreached_cause_unproven`, **kein** erfundenes Hindernis und kein pauschaler Hardwaredefekt; erst nach gesundem terminalem Zustand folgt die andere Aufgabe. Budget über HOLD/Kindwechsel erhalten; Retry erst nach Cooldown, geänderter Kartenevidenz und verbleibenden Versuchen. `scan` prüft begrenzten Initialscan und anschließende Vorausrichtung im verbundenen Pfad; Scan/Vorausrichtung bleiben vorhandene Verfahren mit laufender Konturprüfung.

**Offline-Grenze:** Historischer Erfolgsdatensatz und aktueller Fehllauf wurden lokal nur lesend anhand je drei Raster-/Pose-Snapshots verglichen. Historisch: alte Kandidaten 15/7/11, neue konservativ zulässige 0/4/11; aktueller Fehllauf: 10/13/12 gegenüber 0/0/0. Häufig liegt bereits die tatsächliche Fahrzeugkontur nicht vollständig im bekannten freien Rohkartenraum; zusätzlich Route/Costmap. Der Vergleich verwendet für die reine Kandidatenanalyse einen Rastergrenzen-Scope und beweist weder aktuellen Betreiber-Scope noch Live-Quellengesundheit. Diese Grenze wurde nicht durch Lockerung behoben. Positive Synthetik ist kein Nachweis realer Befahrbarkeit. Private Bags/Karten und Analyseergebnisse bleiben außerhalb Git.

### Realnachweis am 30.09.2026: Vorlauf blockiert, keine Mission

Exakter Kandidat `deb075e3f1a51a46bc00c2235a3068cfbe45d769`, derselbe isolierte Sechspaketinstall, Produktbasisprofil plus lokal vervollständigtes metrisches Overlay über `explore_params_overlay`. Reale Domain 42; kein Aktorschreibprozess. Live-Parameter und 324 Explorer-Statusmeldungen belegen `metric_frontier`; alte WE-Policy/Navigation false. Session/Startkarten-Fingerprint und LAB-1-Scope aus aktueller Karte/Pose zugeordnet; keine historischen Raumkoordinaten oder Dummy-Feeds. Bootstrap-Explorer endete zunächst erwartungsgemäß am ungebundenen Scope; nach Bindung alleiniger metrischer Explorer idle.

**Quellen:** direkte FC03-Startmessung im Stillstand; später passives Gate mit 189,166 ms Radsamplealter > 180 ms. Einmaliger passiver Gate-Neustart nach Sensorstart, tatsächliche kurze Rohquellen-Recovery separat beobachtet. Danach realer Encoderreader terminal verriegelt: `encoderpaar_zeitfenster_ueberschritten`, FC03-Paar 125,870 ms > 120 ms (Einzelreads 91,760/33,809 ms). Ursache der Zeitüberschreitung nicht bewiesen; kein pauschaler Hardwaredefekt. Keine Grenze gelockert und kein Quellenstatus gefälscht.

**Geometrie:** aktuelle Startzelle unbekannt (`-1`); volle gepaddete Kontur in Rohkarte und Costmap unzulässig, bereits erste Scanorientierung verworfen. Snapshotanalyse mit installiertem Kandidaten: 25 reale Frontiercluster, alle `no_known_free_route`, 0 akzeptiert. Kein pauschaler Tür-/Freigabebefund. Darstellung mit Kontur/Scope lokal; keine Fahrspur/Ziel-/Passageereignisse erfunden. Bekannter LAB-1-Rahmen, aktuelles beobachtetes Rasterenvelope; unbekannte Zellen bleiben gesperrt.

| Realnachweiskriterium | Ergebnis und Grenze |
|---|---|
| A: drei autonome Beobachtungen und räumlicher Kartenfortschritt | **nicht bestanden**: 0 Missionen/0 Aufgaben; 1.603 Kartenmanager-Meldungen mit unverändertem Fingerprint |
| B: Zielmisserfolg und sichere Folgeaufgabe | **nicht aufgetreten**: kein Nav2-Kind; passive Quellen-Recovery ist kein Aufgabenfortsetzungsbeleg |
| C: vollständige Passage und Aufgabe dahinter | **nicht bestanden**: keine Fahrt, kein Passagebeleg oder Beobachterzuordnung |

Kein regulärer aktiver Wechsel, weil Vorlauf nicht bestanden; kein zweiter Fahrversuch. Budgets live geladen: 900 s gesamt, 150 s Aufgabe, 6 Versuche/3 Fehler, Initialscan 280 s/0,08 rad/s. Keine Mission begonnen, daher keine Budget-/Timeoutabnahme. Recorder bis Ende aktiv; SQLite erst nach Ende ausgewertet: keine running-Mission, keine Navigate-Statuseinträge, alle aufgezeichneten Befehle null. Geordnete SIGINTs ausschließlich an Launchwurzeln; alle manifestierten Prozesse beendet und Gerätehandles frei. Nach Stackende zwölf frische FC03-Paare, beide Motorpositionen unverändert und 0 rpm. Keine Shutdownfehler im Abschlusslog; Bootstrap-Exit und Laufverriegelung getrennt geführt.

Private Belege ausschließlich `~/.local/share/amadeus/tests/metric-frontier-real-20260930/`: Runtime-Manifest mit Präfixen/Profil-/Modulhashes, Liveparameter/-status, Quellen-/Geometriesnapshots, lokale Darstellung, geschlossene Bag-Auswertung, FC03-Endmessung und Shutdownprüfung. Keine privaten Karten/Bags/Berichts-Vorfahren veröffentlicht. Softwareerfolg bleibt erhalten; kein Stufe-3-Gesamtgrün.

**Damals nächster Schritt, im folgenden Abschnitt ausgeführt:** gezielter Vorlauf-Korrekturauftrag für Startkarten-/Kontur- und FC03-Paarzeitblocker mit getrennten Nachweisen und unveränderten Schutzgrenzen. Aktuelle Voraussetzung ausschließlich im Abschluss vom 01.10.2026.

### Historisch bis cf55cea: Mast-/Eigenkörpervertrag und Encoderzeitpfad

Auftrag vom 30.09. auf veröffentlichtem `0efb7e4`, funktionaler Abschluss
`8be0709` in derselben PR-#105-Linie. **Softwarekorrekturen regressiert;
gemeinsamer realer Vorlauf negativ. Keine Mission und kein Fahrnachweis.**

**Mast:** Betreiberzuordnung OAK-Kameramast verbindlich übernommen. Vorhandene
native Maske 236–304°, NaN-Ausgabe und ROS-CCW bleiben unverändert. Im letzten
Vorlauf: 2.325 Rohscans / 2.287 normierte Scans; im robusten Sektorinneren
57–123° sind sämtliche 924.632 / 905.652 Bins NaN. Die 1° Randreserve dient
nur dieser Auswertung unterschiedlich diskretisierter Scans, verändert keinen
Filter. Tatsächlicher statischer TF aus der Bag: x 0,245, y 0, z 0,660 m,
yaw +1,5708. Manifest belegt Crop=true und tatsächlich gestartete Parameterdatei.
Der native Treiber beantwortete den Parameterdump nicht; deshalb kein erfundener
Live-Parameterbeleg. `/scan` → vorhandene Vereinheitlichung → `/scan_normiert`
→ SLAM/Explorer/HWT-Beobachter/Gate; Costmaps nutzen Rohkarte und ihre vorhandenen
VL53/OAK-Quellen. SLAM-Präfix `~/amadeus_slam_toolbox_ws/install/slam_toolbox`,
Patchparameter live true; installierte `libtoolbox_common.so` enthält den Patch.
Keine neue Drehfahrt oder Kalibrierung daraus ableiten.

**Startkorrektur:** `metric_self_body_enabled` erlaubt privat nur ganze unbekannte
Zellen im ungepaddeten gemessenen Körper x −0,11..0,31 / y ±0,23 m, einschließlich
Zellenecken und Scopeprüfung. Erste korrelierte Pose und Rohkarten-Fingerprint
fixieren den Beleg; er folgt keiner Bewegung und erlischt bei geändertem
Fingerprint. Frische Pose/Scan und passender planarer Montage-TF bleiben Pflicht.
Belegte Zellen, Costmap-Unknown, Außenkeil, Padding und Rasterreserve werden nicht
freigegeben. Rohkarte bleibt bytegleich; volle Kontur x −0,13..0,33 / y ±0,25 m
und ihr Bewegungs-/Drehsweep bleiben geprüft. Keine Garantie für einen Rundblick
allein aus belegtem Eigenkörper.

Der alte Startsnapshot bleibt reproduziert: unbekannte Startzelle, unzulässige
Kontur und 25 `no_known_free_route`. Bei 325 berührten Zellen: 88 ganz im Körper
liegende unbekannte Zellen, 4 Randzellen mit Körperüberschneidung, 16 im Padding,
18 in Rasterreserve; 0 Rohkartenhindernisse. Alte Costmap: 1 unbekannte Zelle in
Rasterreserve, 143 Inflationszellen, 0 Zellen mit Wert ≥100. Rasterkosten beweisen
keine bestimmte physische Objektidentität. Der neue Startsnapshot zeigt 78 ganze
Körperzellen, 16 Körperrand-, 16 Padding- und 18 Reservezellen weiter unbekannt;
Costmap 2 unbekannte Reservezellen, keine Kosten >0 in der berührten Kontur.
Die ganzen Körperzellen werden korrekt getrennt; der unzulässige Außenanteil
bleibt wirksam. Startzentrum nach Clearanceprüfung false, volle Roh-/Costkontur
false, bereits erste Scanorientierung false. 15 reale Cluster, 15
`no_known_free_route`, 0 akzeptiert. Keine freie 360°-Drehung nachgewiesen.

**Encoderkorrektur:** gemeinsame FC03-Blöcke Position/RPM erhalten. Instrumentiert
sind Alias/USB vor/nach Zugriff, Modbus, Antwortprüfung, Paar, Motorversatz,
Pollstart und Publikationsalter. Nur USB-Attributpfadsuche gespeichert; tatsächliche
Identität/tty-Gerätegeneration, Alias und Exklusivität vor/nach jeder Probe sowie
CRC/Antwortprüfung bleiben aktiv. Paarzeit 120 ms und Datenlücke 180 ms unverändert.
Nach ≥20 gesunden Paaren darf ein einzelnes vollständiges Timingpaar bei belegter
Kontinuität verworfen werden: Quelle unbereit, Transport weiter lesend, zwei neue
vollständige plausible Paare. Erstes gültiges Paar integriert sämtliche Zähler
und publiziert weiter unbereit; zweites stellt Readerbereitschaft wieder her.
Passives HWT geht dabei in den vorhandenen HOLD/Validierungsvertrag. Keine
Faultflag-Löschung, Pose-/Baseline-Nullung oder unterschlagene Bewegung.
Anhaltende Verzögerung, lange Lücke, unvollständige Antwort, Portwechsel/-verlust,
unplausible Zähler, Zeitrücklauf und harte Schutzfälle bleiben gesperrt.

Erster Vollstackstart vor der dritten Probe: Pollstart 197,695 ms, Paarzeit
97,920 ms. Terminal, `rebases=0`; keine automatische Heilung einer langen Lücke.
Passiver Readerstart nun 15 s nach den übrigen Starts; vor echten Proben bleibt
Fusion unbereit. Nur Startstaffelung, keine Messzeit-/Grenzverschiebung. Spätere
Verbraucherbeobachtung: frische aufgezeichnete Radprobe vorhanden, während Gate
189,800 ms alte Probe auswertete. Passive HWT-Quellen erhalten aktuelle DDS-Proben
und im Gate eine eigene serielle Callbackgruppe/zweiten Thread; gewöhnliche
Gate-/Not-Aus-/Befehlscallbacks bleiben seriell. Aktiver Basistreiber und aktiver
Gate-Quellenpfad unverändert und separat regressiert.

**Zeitmessung, Millisekunden (Median / p95 / p99 / Maximum):**

| Größe | Allein, 1.200 Paare | Letzter Vollstack, 4.284 Paare |
|---|---:|---:|
| Paar | 13,361 / 15,172 / 16,143 / 18,277 | 18,488 / 37,703 / 52,857 / 87,120 |
| Motorzeitversatz | 6,646 / 7,510 / 8,028 / 9,113 | 9,151 / 18,769 / 25,753 / 43,865 |
| USB/Alias vor Zugriff, je Motor | 0,719 / 1,463 / 1,858 / 4,276 | 1,093 / 4,133 / 10,838 / 33,057 |
| USB/Alias nach Zugriff, je Motor | 0,737 / 1,166 / 1,420 / 3,209 | 1,129 / 4,519 / 10,273 / 45,216 |
| Modbus, je Motor | 4,820 / 5,371 / 5,743 / 9,018 | 6,103 / 13,849 / 20,972 / 36,871 |
| Antwortprüfung, je Motor | 0,019 / 0,034 / 0,046 / 0,365 | 0,035 / 0,047 / 0,203 / 12,365 |
| Pollstartabstand | Standalone-Steuerintervall 50 ms, kein ROS-Publikationsbeleg | 50,000 / 57,173 / 72,622 / 132,552 |
| Publikationsalter ab echtem Paarmittelpunkt | Standalone publiziert nicht | 12,501 / 28,419 / 38,209 / 61,293 |

Je-Motor-Verteilungen haben n=2.400 bzw. 8.568. Null Paarüberschreitungen >120 ms
in beiden Reihen; im letzten Reader null Mittelpunktlücken oder beobachtete
Publikationsalter >180 ms. Keine kausale Last-/Kabelbehauptung aus diesen Maxima.
Voroptimierung ebenfalls 1.200 Alleinpaare: Median 14,020 / p95 16,027 / p99
17,868 / max 21,798 ms. Kein kontrollierter alleiniger Ursachenbeweis.
Zwei erhaltene ältere Vollstackreihen: 12.003 bzw. 3.360 Paare, ebenfalls keine
120-ms-Überschreitung; ihre Gateverriegelungen sind keine Reader-Paarfehler.

**Regression/Build:** acht Projektpakete isoliert, zwei betroffene Pakete nach
Gatekorrektur erneut gebaut; Quelle/Install bytegleich, kein Hauptinstallwechsel.
1.340 abschließende pytest-Tests bestanden, einschließlich aktivem Basistreiber,
passivem Kontinuitäts-/Recoveryvertrag, Not-Aus/Bewegungs-/HOLD-Gegenfällen und
Launch-Besitzprüfung einschließlich verzögertem Reader. Neue echte DDS-Regression
blockiert normalen Callback 350 ms: frische Quellen laufen weiter; tatsächlich
fehlende Radquelle >180 ms bleibt terminal. Ohne eigene Quellengruppe scheitert
die positive Gegenkontrolle erwartungsgemäß an unverändertem Radstempel.
Versetzter LiDAR/Mast, zulässiger Start und Nachbarhindernis/unbekannter
Schwenkraum/falscher TF/ungültige Pose getrennt regressiert. Verbundener
`mast_start`: drei synthetische Aufgaben erreicht, viertes Kind terminal
gecancelt, maximal ein Kind. Das ersetzt keinen realen Bewegungsbeleg.

**Gemeinsames reales Ergebnis:** erster korrigierter Quellenvorlauf 20 s gesund,
später Gate terminal an Radquellenalter; nächste Messung ohne Rendering ebenfalls
nicht durchgängig gesund. Nach gezielter passiver Callbackkorrektur im letzten
Vorlauf reale HWT-Kurzstörung → HOLD → Validierung → HEALTHY, danach weiterhin
terminal `wheel_missing_stale_or_invalid`. Reader selbst bis Ende ready,
4.284 vollständige Paare, keine FC03-Fehler/Reconnects/Recoveryausreißer/Rebases.
Der erste Fehler-Snapshot bleibt die frühere HWT-Störung; er ist kein numerischer
Snapshot der späteren terminalen Radentscheidung. Deren exaktes Verbraucher-
alter/Ursache wird nicht aus dem Bag oder späteren guten Paaren erfunden.
Die Callbackkorrektur behebt den gezielt regressierten seriellen Stau, beweist
aber **keine vollständige Beseitigung realer Verbraucherfrischefehler**.
Geometrie unabhängig davon weiterhin unzulässig. Deshalb kein aktiver Wechsel,
0 Missionen/0 Nav2-Kinder; A/B/C unverändert offen. Budgets 900/150 s, 6/3 live
belegt, nicht als ausgeführte Missionsabnahme gewertet. Alle vier Befehlsströme
null; Encoderpositionen/RPM unverändert null, Odom-v null. Alle manifestierten
Prozesse und Gerätebesitzer beendet; anschließend 12 frische Paare beider Motoren
mit 0 rpm/Position 0. Bootstrap-Scope-Exit getrennt, keine Shutdownfehler.

**Historische Voraussetzung bis cf55cea; durch den folgenden Abschluss konkretisiert:** ein
**gleichzeitig gültiger gemeinsamer Startnachweis**: vollständige gepaddete
Start-/Schwenkgeometrie samt zulässigem Rasterweg sensorisch belegt und tatsächliche
Quellen bis zum Verbraucher innerhalb ihrer unveränderten Frischegrenzen, ohne
terminale Verriegelung. Dieser eine Startvertrag ist aktuell an beiden getrennt
benannten Prädikaten ungültig; die Befunde dürfen nicht zu einem einzigen
angeblich behobenen Fehler zusammengezogen werden. Keine identische Wiederholung
oder erzwungene Bewegung ohne neue Geometrie-/Zeitbezugsevidenz.

Private Messungen/Scans/Karten/Bags/Manifeste ausschließlich unter
`~/.local/share/amadeus/tests/metric-start-encoder-20260930/`, Abschluss in
`common-gatefix/`. Keine Raumdaten oder private Berichts-Vorfahren veröffentlicht.
Rückfall: ohne Mission geordnet beenden, temporäres letztes Overlay weglassen;
Eigenkörperoption abwählen. Bei Kontinuitätsverlust neue belegte stationäre
Initialisierung mit neuem Karten-/Odometriebezug, kein Latch-Reset. Kein Merge,
kein permanenter Installwechsel und kein Stufe-3-Gesamtgrün.

### 01.10.2026 – Entscheider und reale Anfangsgeometrie, begrenztes Paket beendet

**Radpfad:** Eigener atomarer Snapshot je STARTUP-/HOLD-/Terminalübergang mit
Ereigniskennung, Zustand vorher/nachher, Originalnachricht (Header sec/ns,
Frames, Pose/Quaternion, Twist und beide Kovarianzen), tatsächlichem
Consumer-/Callbackeintritt, ROS-/Monotonic-Bracket, Mess-/Empfangsalter,
Grenze, erstem Prädikat und vorheriger erfolgreicher Recovery. Historisches
`first_fault` bleibt erhalten. Fehlend, ungültig und stale getrennt;
ältere Callbackübernahme ersetzt keine neuere Probe. Gate entscheidet einmal
unter dem bestehenden Quellenlock; bounded/latest Diagnose-JSON und DDS-Ausgabe
laufen separat, Stopptimer weiterhin 20 Hz. Ein vor der ROS-Uhrabfrage
präemptierter Callback wird nicht zusätzlich als Messalter gezählt;
Integer-ns-Differenz und konservativer gepaarter Monotonic-Bezug statt alter
Eintrittszeit. Dieser kontrollierte Uhrtest ist kein rückwirkender Beweis
für sämtliche historischen Radfehler.

Zweiter aktueller Realvorlauf: gültige Probe, 215,948 ms Messalter >180 ms,
162,131 ms seit Callback, drei neuere Originalmessungen vor Entscheidung im
Recorder. Reader fehlerfrei, Paarmaximum 93,291 ms. Recorderempfang ist kein
Gatecallback. Separate passive Radgruppe/dritter Thread allein reicht real
nicht: dritter Vorlauf 186,344 ms, neuere Probe mit 69,822 ms Messalter bereits
21,973 ms vorher im Recorder. Danach zusätzlich echte 170,104-ms-Paarverletzung.
Die nachgewiesene Empfangs-/Schedulinglücke wird am vorhandenen Gate geschlossen:
vor passiver Entscheidung nichtblockierender Take aus derselben zuverlässigen
Depth-1-DDS-Subscription unter ihrem Callbackgruppenschutz. Kein zweiter
Subscriber, Quellenpublisher oder Busbesitzer; Originalstempel unverändert.
Eine bereits laufende Subscription wird nicht verdrängt. Receive-Exception
macht die alte Probe ungültig, statt sie gesund weiterzuverwenden. Normaler
Befehl/Not-Aus bleibt seriell; aktive Quellen weiterhin bestehender serieller
Executor/QoS und separat regressiert.

**Reader:** Im ersten aktuellen Start war eine reale 129,184-ms-Paarverletzung
überwiegend in Alias-/USB-Prüfung gemessen (106,350 ms). Voller `/dev`-Pfadwalk
nun nur zur Bindung; beide Aliaslinks, tatsächliche Gerätegenerationen und
alle USB-Identitätswerte weiter vor/nach jeder FC03-Probe prüfen. Weder
120-ms-Paargrenze noch 180-ms-Kontinuität oder Recoverybedingungen gelockert.
1.200 korrigierte Alleinpaare: Median 13,895 / p95 16,593 / p99 19,135 /
Maximum 23,420 ms. Unterschiedliche Lastbedingungen sind kein alleiniger
Kausalvergleich. Die Optimierung garantiert keine reale Echtzeitdeadline.

**Geometrie:** Zellprojektion auf den tatsächlichen Körper durch
res/2·(|cos Δyaw|+|sin Δyaw|) statt immer res/√2. Bei einem erhaltenen aktuellen
Start 78→92 ganze Körperzellen; alle vier Ecken der 14 zusätzlich zugelassenen
Zellen wirklich innerhalb des unveränderten ungepaddeten Körpers. Erste
Anfangsablehnung 50→36 und volle Rundblickablehnung 231→217; körperfremder
Flächenanteil unverändert. Vorheriger C3-Start 78→78, keine rückwirkende Heilung.
Kein Rohkartenwechsel, keine partielle Zellenfreigabe, kein mitbewegter Beleg.
Frischer Scan, der während Kartenarbeit ankommt, wird gegen danach erfasste
Zeit geprüft; echtes Stale/Future/fehlender Scan weiter abgewiesen.

Finale Karte/Pose im selben letzten Vollstack gebunden: 92 unbekannte ganze
Körperzellen privat korrekt behandelt. Anfangskontur weiterhin 36 unbekannte
Zellen: 18 teilweise Körperrand, 1 Padding, 17 Reserve; Außenanteil
0,030920 m². Voller 360°-Sweep: 211 abgewiesene Zellen (18 Rand, 1 Padding,
192 Reserve/zusätzlicher Schwenkraum), Außenanteil **0,188420 m²**.
Dies ist die konservativ benötigte Rasterbeobachtung abzüglich exakter
Körperüberlappung, nicht eine vermeintlich exakte feste Fahrzeug-Sweepfläche.
Costmap: Anfang 2 unbekannte Zellen; volle Drehung 139 unbekannte Zellen /
0,125100 m², vollständig in obiger Rohkartenzellmenge. Flächen nicht addieren.
Keine Rohhindernisse oder Inflationskosten in diesem Beleg. Zentrum nach
Clearance 0,120 m < erforderlichen 0,295 m unzulässig, 0 sichere Kandidaten;
erstes Produktprädikat `initial_scan_footprint_invalid`. Ganze 360°-Kontur,
Vorausrichtungs-/Routenwahl und Costmap werden nicht durch eine freigegebene
Mittelpunktzelle ersetzt. Volle reale Kontur/Padding/Reserve unverändert.

**Regressionen und Grenzen:** Isolierter ursprünglicher Vierpaketbuild plus
abschließendes Zweipaketoverlay bestanden und Quelldateien bytegleich geprüft.
1.469 pytest inklusive A–D, aktiv/passiv, Reihenfolge, wartende echte DDS-Probe,
Receive-Exception, Not-Aus/HOLD/Stillstand/Einzelkind. Gerätefreier verbundener
`mast_start_scan` besteht: versetzter LiDAR/Mast-NaN, volle 360°-Konturzulassung,
bestehender 0,3-rad-Testscan, Vorausrichtung, drei autonome Beobachtungen,
viertes Kind gecancelt, maximal ein Kind. Kein voller physischer Rundblick
behauptet. Zusätzliche vollständige 2π-Dauerprobe nicht bestanden:
`initial_scan_no_progress`, gemessene synthetische Quellengaps bis 460,796 ms.
Diese erhaltene negative Probe wird nicht in die positiven Softwarebelege
umbenannt. Keine entsprechende reale Bewegungsprobe ausgeführt.

**Gemeinsamer Realvorlauf:** Vier klar begrenzte, jeweils nach neuer Evidenz
korrigierte Fenster, jeweils 720 s ab Launchwurzel, kein Gate-/Reader-Neustart
oder Latch-Reset innerhalb eines Fensters. Letzter Kandidat `8f5eeb4`, Sources
zuerst nach 33,328 s bereit; zwei reale HWT-HOLDs mit erfolgreicher Validierung.
Danach etwa 197,9 s: Wheelmessalter 212,127 ms, tatsächlicher Consumerabstand
165,445 ms, gültiger Inhalt, `measurement_age_out_of_bounds`. Historische erste
HWT-Störung und letzte Wheelentscheidung haben eigene Originalsnapshots;
vorherige erfolgreiche Recovery steht im Wheelereignis. Beim Reader:
3.552 akzeptierte Paare (Maximum 99,431 ms); letztes 64,649 ms,
folgendes verworfenes Paar **120,874 ms**,
kein Rebase/Reconnect, keine aktuelle zulässige Ersatzprobe. Geschlossener Bag:
keine neuere Radnachricht um den Entscheid; erster verriegelter Readerstatus
bereits 7,975 ms vor dessen gepaartem ROS-Zeitbezug im Recorder. Das ist ein neuer
echter Transport-/Deadlinegegenfall; keine alte Probe frisch bewerten.
Der spätere Status `ready=false` bleibt erhalten. Gesamtes Fenster negativ,
geometrisch zugleich unzulässig. Kein aktiver Buswechsel, 0 Missionen,
0 Nav2-Kinder; 900/150 s und 6/3 live geladen, keine Budgets gestartet/reset.

**Damals konkreter Restumfang (durch den folgenden Auftrag präzisiert):** Der aktuelle FC03-Pfad muss unter echter Vollstacklast
wieder zulässige Paare innerhalb 120 ms und lückenlos innerhalb 180 ms liefern.
Im letzten Paar sind 71,797 ms Alias/USB-Nachprüfung und 46,840 ms Modbus
beobachtet; aus diesen wall-clock-Phasen allein keine Kabel-/Encoder-/Kernel-
Ursache erfinden. Weitergehende Transport-/Runtime-Latenzabsicherung ist ein
separat zu begrenzender Umsetzungsschritt; dieses Paket startet keine weitere
Reparatur-/Vorlaufserie. Geometrisch genau eine notwendige äußere Handlung:
die private Liste der 211 Außen-/Schwenkzellen mit dem vorhandenen LiDAR von
einer separat hergestellten stationären Beobachtungsposition aufnehmen und
Karte/Pose neu gültig zuordnen. Dafür nötiges manuelles Umsetzen bei deaktivierten
Antrieben durch die anwesende Person liegt außerhalb dieses Softwarepakets.
Stationärer Mast-NaN-Blick und vorhandene OAK/VL53-Vorwärtssicht belegen diesen
gesamten rückwärtigen Bereich nicht. Keine allgemeine Platzfrage, Karten-
freigabe oder autonome Bewegung zur Umgehung.

Alle zugehörigen Wurzeln geordnet einzeln per SIGINT beendet, Gerätehandles frei,
abschließend 12 frische FC03-Paare beider Motoren: Position/RPM null. Elektrische
Motorstromfreiheit wurde daraus nicht behauptet. Befehlsströme und Shutdown-
Details im geschlossenen lokalen Bericht. Ungebundener Bootstrap-Explorer
beendet sich erwartungsgemäß mit Scope-/Sitzungsfehler (Exit 1); anschließend
gebundener Explorer regulär, kein Fehler beim geordneten Shutdown.
Private Messdaten, Zellkoordinaten,
Karten, Bags und Manifeste unter `~/.local/share/amadeus/tests/metric-gate-start-20261001/`,
finaler Lauf `decision-take-common/`, Runtime `final-runtime-env.sh`,
`final-build-identity.json` und `end-state-proof.json`. Keine privaten
Berichts-Vorfahren, Merge, Force-Push oder permanenter Installwechsel.
Rückfall: ohne Mission geordnet stoppen, beide temporären Overlays weglassen,
`active_drive=false`, `enable_auto_explore=false`. **Stufe 3 bleibt offen.**

### Historischer Abschluss: adaptiver Start und begrenzte Encoder-Recovery (01.10.2026)

Ausgang `d9894d268262f7f8e965f2f92aef72021df3245e`, Funktionskandidat
`fd883fdf35e004dff6b209fffff9118c71161cd3`, derselbe Branch/PR #105.
Getrennte Funktionscommits: `a8aa3f3` Encoder/aktive Basis/Fusion/Gate,
`b36d412` adaptiver Start/Controllergeometrie, `fd883fd` typgerechte
Controllerklassen in der Graphfixture. Keine privaten Berichts-Vorfahren.

**Wirksamer Produktvertrag:** `exploration_strategy` bleibt standardmäßig
`existing`; metrisches Profil explizit `metric_frontier`, dessen unveränderlicher
Startparameter `metric_start_strategy=adaptive`. `initial_scan_enabled=true`
bleibt geladen. Ein zulässiger nützlicher Vollrundblick bleibt verfügbar; fehlt
seine Fläche, wird ein echtes Frontier-/Annäherungsziel gesucht. Fehlt schon
die sichere Anfangskontur oder jedes Ziel, folgt ein begründeter Teilstand.
Kein Pflichtscan für eine andere Bewegung, kein festes Fahrziel, kein neuer
Goal-Sender oder Supervisor. Bootstrap/HOLD zählen in 900/150 s und 6/3 hinein.

Vor vorhandener Nav2-Ausführung tatsächlichen `ComputePathToPose`-Plan und
13 Liveparameter von RPP/Goalchecker prüfen: genau `FollowPath`/RPP und
`general_goal_checker`/SimpleGoalChecker; Rotation true, Winkel 0,35 rad,
Lookahead 0,40 m, Geschwindigkeitsskalierung/Rückwärtsfahrt false,
Kollisionsprüfung/Interpolation true, XY-Toleranz 0,15 m/Yaw 0,40 rad.
Vorausrichtung, Controllerkorrektur, interpolierter Carrot/Kurvenraum, gesamte
Route und Zielrotation einschließlich XY-Toleranzdisk reservieren. Ungedeckter
weiter Carrot aus zu dünnem Plan wird verworfen; vorhandene Reserven bleiben.
Die zusätzliche Kurvenreserve ist abgeleitet, kein verkleinerter Footprint.
Startkörperbeleg bleibt im ursprünglichen Raum; harmlose Rasterupdates können
ihn nur verkleinern. Änderungen von Kontext/Raster/Karten-Odometriebezug lassen
ihn verfallen. Keine mitfahrende Freiraumblase, kein Überschreiben von Hindernissen.
Mastmaske, NaN-Semantik und Montage-TF erhalten.

**Encodervertrag:** gemeinsamer Core für passiven Reader und aktive HWT-Basis;
120 ms Paarvalidität und 180 ms Bewegungsfrische/Kontinuität unverändert.
Nach gesundem Vorlauf darf bei intakter Identität begrenzt diagnostisch weiter-
gelesen werden: maximal 2 s / zwei Versuche je Readerlebensdauer. Verworfenes
Paar bleibt unveröffentlicht, Stillstand/HOLD sofort. Neue gültige Paare können
nur bei belegter Kontinuität alle Zählerdifferenzen erhalten; keine Rebase,
Pose-Nullung oder Reconnect-Reparatur. Echte >180-ms-Lücke bleibt unbewiesen,
auch bei späteren 0 RPM/zwei guten Paaren. Verbraucher zusätzlich höchstens
5 s / zwei Wiederherstellungen je Quellenklasse HWT bzw. Rad, ohne Reset durch
Kindwechsel. Gültige Originalstempel, Stillstand, Fusion/Karte/Route, terminales
altes Kind und Gate-ACK vor Resume. Port/Identität/Zähler/Zeit/ESTOP/Cancel
und Aktuatorfehler bleiben hart. Details: [Encodervertrag](../ENCODER_ODOMETRIE_FIX.md)
und [Explore-README](../../src/explore/README.md).

**Alter echter Fehler exakt reproduziert:** native Paardauer 120,874265 ms,
letzte zulässige Radprobe am Gate 212,127149 ms. Erstgrund im ursprünglichen
Reader `encoderpaar_zeitfenster_ueberschritten`; keine wartende zulässige Probe.
Neuer Reader verwirft das Paar; danach >180 ms macht Kontinuität unbewiesen,
2-s-Endgrund `encoder_timing_continuity_unproven`. Historisch nicht aufgezeichnete
verworfene Zähler wurden im Replay mit null gegengetestet: sogar das heilt die
Zeitlücke nicht, beweist aber keinen historischen Stillstand. Kein rückwirkendes
Umdeuten der damaligen Sperre.

**Software und verbundene Nachweise:** 1.493 Regressionen bestanden, isolierter
Fünfpaketbuild erfolgreich. Zehn geänderte Laufzeitartefakte bytegleich mit dem
tatsächlich aufgelösten Install. MM, BT, Explorer, Kartenmanager, HWT-Shadow und
Gate tatsächlich ausgeführt; synthetisch sind Sensor-/Rastereingänge und
Nav2-Gegenstelle. Keine erfundenen Ziele/Gesundheitsadapter. Reale Zeitlücken
bleiben Zeitlücken, kein Fresh-Restamping. Unterschiedliche Graphfälle nicht
zu einer bestandenen durchgehenden Vollrundblickfahrt zusammensetzen.

| Pflichtfall | Ergebnis und Grenze |
|---|---|
| A adaptive Beobachtungsschleife | `adaptive_loop`: drei selbst berechnete Ziele, neue Rasterevidenz, offene Verbindung/weitere Ziele, 60,38 s im selben Elternauftrag, maximal ein Kind. Scanverfügbarkeit in diesem Loop-Test explizit false. Separater Fall unten prüft den tatsächlich eingeschalteten Scan. |
| A/B Scan optional, später zulässig | `adaptive_admission` mit `initial_scan_enabled=true` und voller 2π-Anforderung: rückwärtiger Schatten sperrt Scan; anderes berechnetes Ziel wird ausgeführt; erst neue Karte erlaubt Scan. Danach bewusster Testabbruch, **kein bestandener Vollscan**. Nach letzter Parametertypkorrektur erneut bestanden. |
| C keine sichere Erstbewegung | `adaptive_wait`: null Kinder und ausschließlich Nullbefehle bei unbekannter Startreserve; Vorausrichtung/seitliches Hindernis/Controller-/Zieltoleranz zusätzlich regressiert. |
| D/F Timing-HOLD und HWT davor | `encoder_hold`: tatsächlicher Core verwirft 120,874-ms-Paar bei noch belegter kurzer Kontinuität; HWT-Recovery zuvor separat; neuer gültiger Stillstand/Fusion/ACK, höchstens ein Kind; getrennte Originalereignisse am Explorer und Gate. |
| E echte Lücke | `encoder_gap` und Readerregression: >180 ms, spätere gute Paare/0 RPM ohne Rebase oder Weiterfahrt; begrenzte Diagnose endet gesperrt. |
| G harte Gegenfälle/Budget | `encoder_persistent`, `encoder_no_stop`, `encoder_estop`, `encoder_cancel`, `encoder_budget`, `cancel_failed`, `estop`: keine unerlaubte Fortsetzung; dritter Radfehler nach zwei Recoveries terminal. Aktiver Basisadapter/Identität/Uhrrücklauf/Zähler separat regressiert. |
| H Karten-/Körperbeleg | `route`, `mast_start`, `chain` sowie Körper-/Kontextregression: gültige Updates erhalten Aufgaben; neues Hindernis stoppt; alter Körperbeleg kann weder wandern noch neue Sperren freigeben. |

Sechs geometrie-/Controllerbetroffene Graphfälle nach finaler Kurven- und
Zielreserve erneut bestanden, zusätzlich typgerechte 13-Parameterprüfung und
Budgetfall. Lokales Nachweisregister `metric-adaptive-start-20261001/` mit
`regressions-publish-final.log`, `graph-controller-final-summary.json`,
`graph-suite-summary.json` und einzelnen `result.json`/Prozesslogs.

Nach Veröffentlichung erkannte Offline-CI einen ROS-Import im neuen aktiven
Adaptertest. Nur dessen Sammlung und die ROS-Uhrprüfung bei fehlendem `rclpy`
ausnehmen; vollständige Coretests bleiben offline aktiv. Nachweis in isolierter
Umgebung ohne ROS: 118 bestanden, zwei ROS-Abhängigkeitsskips, 63 Subtests;
zwölf Inbetriebnahmewerkzeugtests bestanden. Dieselben drei ROS-abhängigen
Adapter-/Uhrfälle mit echter ROS-Installation erneut bestanden. Produktbytes
des real geprüften Kandidaten bleiben unverändert, kein neuer Realstart.

**Volle Dauerprobe bleibt negativ:** historische 2π-Probe erhalten. Auch neuer
`graph-adaptive_start-final` nach 259,27 s negativ: Vollscan erst nach tatsächlich
erledigter erster Beobachtung zugelassen, dann Quellenpausen (größte rohe
Publikationslücke 515,70 ms), zwei HWT-Recoveries, absolute 150-s-Scanfrist
erschöpft; anschließend `post_child_state_or_standstill_unconfirmed` mit
`hwt_recovery_attempt_limit`. Gemessene synthetische Gesamt-Yaw 11,825 rad über
Unterbrechungen ist kein belegter abgeschlossener 2π-Scan. Diese Probe entstand
vor der zusätzlichen Kurven-/Zielreserve; die späteren positiven Kurzfälle
ersetzen ihre Laufzeit-/Quellengrenze nicht. Frühere negative Fixture-/Last-/
Geometrieversuche ebenfalls erhalten. Kein Vollrundblick-/Robustheitsgrün.

**Ein gemeinsamer realer Vorlauf:** derselbe isoliert kopiert gebaute Kandidat,
reale Domain 42, `active_drive=false`, passiver FC03-Reader als einziger
Basisbusbesitzer. Vorab FC03-Nullposition/-RPM und freie Handles geprüft.
Ungebundener Bootstrap endet erwartungsgemäß am Scope; im selben Stackfenster
Session/LAB-1-Scope an tatsächliche Karte/Pose gebunden und einziger gebundener
Explorer idle. Laufzeitpräfixe, Prozessbaum, geladene Parameterdateien, Modul-
und native RPP-Bibliothekshashes sowie alle 13 Controllerparameter manifestiert.
Tatsächliches metrisches/adaptives Profil, Scan weiterhin true, 900/150 s und
6/3 live; SLAM `check_min_dist_and_heading_precisely=true`.

Vorab festgelegtes Messfenster **720 s ab Launchwurzel**, gemessen 720,016 s.
Erstmals alle Vorlaufbedingungen außer Bewegungsgeometrie nach 35,858 s.
Am tatsächlichen Gate: HWT-HOLD nach 162,718 s → HEALTHY nach 164,263 s;
zweiter HOLD 401,729 s → HEALTHY 403,212 s. Dritte HWT-Störung nach 583,261 s
terminal `hwt_recovery_attempt_limit`. Eigener Originalzustand: Rawdriver
`ready=false`, `raw_data_ready=false`, `consecutive_errors=1`,
`Zeitueberschreitung nach 0/14 Bytes`; Rawalter dabei erst 37,327 ms.
Also echter Readiness-/Budgetgegenfall, keine erfundene stale-Wheelursache.
First-Fault und zweite erfolgreiche Recovery im späteren Fehler erhalten.
Keine bewiesene Hardware-/Kabel-/Kernelursache daraus ableiten.

Encoder am 720-s-Ende: **13.921 vollständige Paare**, null Timing-Recovery/
Rejects/Rebases/Reconnects, ursprünglicher Baselinezähler eins, Kontinuität
gültig. Größte diagnostizierte Paardauer 108,118 ms, unter 120 ms. Der aktuelle
Realfall ist **kein realer Encoder-Recovery-Nachweis**; dieser ist softwareseitig
verbunden geprüft. Gesundes Rad heilt keine terminale HWT-/Fusionquelle.

Aktuelle frühe und späte Geometrie unabhängig von Quellen negativ:
**33 unbekannte Startkonturzellen**, davon 16 teilweise Körperzellen und
17 Paddingzellen. Ganze Körperzellen privat 79; Außenanteil spät **0,021089 m²**
(früh 0,021069 m²). Eine unbekannte Costmap-Paddingzelle vollständig in dieser
Rohmenge; Flächen nicht addieren. Erster Produktgrund
`initial_contour_unknown_or_occupied`, **null adaptive Kandidaten**. Kein
unbenutzter Vollsweep als Gate: dennoch bleibt die beanspruchte Anfangskontur
unbelegt. Vollsweep nur Diagnose: 220 unbekannte Zellen / 0,189389 m²,
134 Costmap-Zellen vollständig darin. Letzter historischer Referenzfall bleibt
separat 36 Start-/211 Sweepzellen; weder manuelles Umsetzen noch Vorkartieren
wurde als positiver Bootstrap verwendet. Spätaufnahme nutzt aktuelle Daten
im selben laufenden Sensorstack, keine neue Karten-/Quellenfreigabe.

**Reale Mission nicht ausgeführt:** kein aktiver Buswechsel, kein MM-Auftrag,
kein Nav2-Kind. Quellenbudget UND Anfangskontur blockieren technisch; keine
fehlende allgemeine Nutzerfreigabe. Kein weiterer Vorlauf oder Fahrversuch.
Der 720-s-Probe endete automatisch; für abschließenden Snapshot und geordneten
Stopp liefen die rein lesenden Sensorprozesse anschließend noch **185,994 s**.
Dies ist Abschlussnachlauf außerhalb des Messfensters, kein zweites Fenster
und keine 900-s-Mission; eine exakte 720-s-Prozesslaufzeit wird nicht behauptet.
Geschlossene Bag erst nach Recorderende: 0 running-Missionen, 0 Navigate-
Statuseinträge, sämtliche vier aufgezeichneten Befehlsströme null. Radpositionen
durchgehend null; kleine gefilterte IMU-Winkelgeschwindigkeit ist kein Fahrbeleg.
Geschlossener Gesamtdatensatz einschließlich Nachlauf: 17.559 Readerpaare,
keine 120-ms-Verletzung, maximaler Messabstand 124,198 ms. Diese Statistik
nicht mit einem durchgehend gesunden Verbraucherzustand gleichsetzen.
Mast-NaN im robusten Sektorinneren 57–123° vollständig erhalten; Montage-TF
unverändert. Einzelne Raster-/Pose-/Zellbelege bleiben privat.

**Endzustand:** alle manifestierten Prozesse nach einzelnem SIGINT an ihren
Launchwurzeln beendet, beide Gerätealiases ohne Besitzer; anschließend zwölf
frische FC03-Paare je Position 0 / 0 RPM, keine elektrische Sperrstellung
behauptet. Hauptkopie sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`,
kein dauerhafter Install-/Autostartwechsel. System eingeschaltet, kein geplanter
Shutdown. Private Belege ausschließlich
`~/.local/share/amadeus/tests/metric-adaptive-start-20261001/`, insbesondere
`common/passive-window-final.json`, `common/closed-preflight-analysis.json`,
`common/late-geometry-report.json`, `common/fullstack-timing.json`,
`common/scan-mask-proof.json`, `end-state-proof.json` und `end-encoder.json`.

**Belegte Restgrenze:** autonome reale Erkundung erst mit gleichzeitig gültigen
Quellen am Verbraucher innerhalb des unveränderten Recoverybudgets und
sensorisch belegter Anfangskontur/einer zulässigen berechneten Erstbewegung.
Der optionale Rundblick löst weder drei HWT-Störungen noch die 33 Startzellen.
Kein manueller Bootstrap als Ersatz. Weitere gezielte Quellen-/Beobachtungs-
arbeit braucht einen neuen begrenzten Auftrag, keine automatische Neustartserie.
Rückfall: ohne Mission geordnet stoppen und dieses temporäre Fünfpaketoverlay
weglassen; sichere Betriebsparameter `active_drive=false`,
`enable_auto_explore=false`. **Stufe 3 offen.**

### Aktueller Abschluss: HWT-Entwicklungsvertrag und Start-Egress (01.10.2026)

Ausgang `2a0e19d`, bestehender Branch/PR #105. Getrennte Funktionscommits:
`689cba3` (HWT-Vertrag), `acdfbeb` (gebundene Portgeneration), `577013d`
(weiter frisches korrigiertes Original nach verworfener Grenzmessung),
`a6f31bf` (bewegungsgerichteter Egress). Explizites Entwicklungsopt-in:
Antwortfrist 50 ms, Rohoriginalfrische 300 ms, maximal zwei echte HWT-HOLDs
im rollenden 60-s-Fenster. Einzel-Recovery weiterhin absolut 5 s; keine
Rücksetzung durch Aufgaben-/Kind-IDs. Legacy 30/200 ms und Encoder 120/180 ms
erhalten. Kein Restempeln, keine verspätete Antwort nachträglich nutzbar.

**Software:** 1.462 Pflichtregressionen in sieben betroffenen Paketen bestanden
(28,97 s), zusätzlich 102 unveränderte Mission-/BT-/Kartenprüfungen (5,00 s):
zusammen 1.564 Tests in getrennten, nicht überlappenden Testsammlungen.
Pflichtfälle A–F: Polltimeout ohne Budgetverbrauch, wirkliche Rohdatenlücke,
begrenztes Heilen/ACK/Resume, drittes HOLD innerhalb 60 s, drei zeitlich
verteilte Recoveries und harte Port-/Protokoll-/Zeitfehler. G–J: autonome
Vorwärtsausfahrt aus unbekanntem Startbestand, unzulässige Drehung, neues
Hindernis und spätere normale Entscheidung nach echter Beobachtung.
Zusätzlich Wiederbetreten/Annäherung, Kontextentzug und verbleibende
Drehkopplung nach nominalem Verlassen, sowie Not-Aus/Cancel/Einzelkind/
Encoder/Kartenprovenienz regressiert. Verbundener gerätefreier Produktgraph:
drei autonome erreichte Ziele mit neuen Kartenbeobachtungen und Weiterarbeit
über die synthetische Verbindung; maximal ein Nav2-Kind. Separater HOLD-Graph:
150-ms-Lücke ohne HOLD, echte >300-ms-Lücke, Stop/Validierung/ACK innerhalb
5 s und Wiederaufnahme desselben Ziels. Keine reale Recovery daraus ableiten.
Historische negative vollständige 2π-Dauerprobe bleibt unverändert negativ.

**Runtime:** Sechspaket-Copybuild außerhalb Git erfolgreich, letzter Build
von state/explore 8,58 s. 100 Quell-/Install-Dateien bytegleich. Tatsächliche
Prozessargumente, Parameterdateien, Präfixe und Modulhashes privat gesichert;
live Rawreader 50/300 ms, Encoder 120/180 ms und 13 native Controller-/
Goalcheckerparameter gelesen. Die einzelne Live-Explorer-Parameterabfrage
war während dessen verzögerter Initialisierung nicht verfügbar; gebundenes
Launchprofil und vier spätere `metric_frontier`-Statusmeldungen sind erhalten.
Keine vollständige Live-Parameterantwort dieses Nodes behaupten.

**A. Start-Egress:** Fester Ausgangsbestand in beiden Rastern, nur monoton
wegführender voller reservierter RPP-Sweep; Suchmaske ist keine Freigabe.
Aktueller Real-Snapshot: 42 unbekannte Roh-Startkonturzellen (16 teilweise
Körperrand-, 17 Padding-, 9 Reservezellen), 79 ganze Körperzellen privat;
Außenanteil 0,026895 m². Costmap zwei unbekannte Konturzellen. Das ist ein
neuer Snapshot, kein Ersatz des historischen 33-Zellen-Befunds. 22 autonome
Kandidaten, keiner zulässig: zehn nötige Anfangsdrehungen, sieben fehlende
freie Routen, eine ungültige Zielorientierung, vier ungültige Footprint-
Sweeps. Produktgrund `start_egress_no_admissible_motion`; optionaler Vollscan
ebenfalls unzulässig. Alle Zell-/Pose-/Kartenbelege und gerenderte Grafik
privat. Frühere virtuelle Hindernisdiagnose nicht als aktuelle Fahrt ausgeben.

**B. Reale autonome Ziele:** Null; kein aktiver Buswechsel, keine MM-Mission,
kein Nav2-Kind. Keine fehlende allgemeine Nutzerfreigabe: der harte Zeitfehler
und der fehlende zulässige Startkandidat verhindern den konditionierten Start.

**C. Karte:** Aktuelle reale Karte/Pose/Scope gebunden und unverändert
ausgewertet. Kein durch Fahrt erzielter Kartierungsfortschritt und kein
Abdeckungs-/Wohnungsabschluss. Drei neue Beobachtungen nur im Softwaregraph.

**D. HWT:** Erster kurzer Start vor der gemessenen Portprüfung-Optimierung
verbleibt STARTUP: wiederholte >100-ms-Lücken unterbrechen die unveränderte
800-Sample-Kalibrierung. Optimierung gemessen: voller USB-Abgleich im Mittel
1,065 ms, gebundene Geräteprüfung 0,031 ms; voller Ausschluss vor exklusivem
Öffnen, danach Gerätegeneration vor und nach Antwort. Finaler kurzer Start:
60,008-s-Messfenster, HEALTHY bei 36,379 s, terminal bei 54,880 s wegen
`HWT-Messzeit nicht monoton`. Dies betrifft die hostseitige Zuordnung des
Empfangs zu ROS-Zeit; keine bewiesene Sensor-/USB-/Kernelursache. Davor
zwei tatsächliche verworfene Transaktionen: Header 3 Bytes erst nach Frist,
Payload 0; anschließend Header 3/Payload 14 rechtzeitig empfangen, Verarbeitung
nach Frist. Rawdriver meldet dabei `transport_degraded`, letzte gültige
Messung 75,693 bzw. 71,024 ms alt, kein HWT-HOLD. Harte Zeitprüfung umgeht das
Recoverybudget nicht: unmittelbare Sperre, null Recoveryversuche. Keine
natürliche reale HOLD→Resume-Folge in diesem Lauf. Frozen Bias mit 800 Samples
belegt, keine Grenze dafür gelockert. Recorder 3.280 Rohframes gegenüber
Driverzähler 3.287; nicht als verlustfreie Aufzeichnung darstellen.

Encoder am Messfensterende 824 Paare, im geschlossenen Gesamtdatensatz 1.133;
maximal 114,879 ms, null Reject/Timing-Recovery/Rebase/Reconnect, Baseline eins.
Er ist auch hier kein nachgewiesener Blocker. Messfenster und Prozessdauer
getrennt: gesamte Orchestrierung einschließlich Bindung/Manifest/geordnetem
Stopp 83,709 s, Bag-Spanne 76,646 s. Kein 720-s-Vorlauf oder 900-s-Fahrversuch.

**E. Zielmisserfolg/Folgeaufgabe:** Kein reales Ziel gesendet, daher kein
reales Misserfolgs-/Alternativzielereignis. Bestehender Softwarevertrag bleibt
regressiert; die Drei-Ziel-Folge meldet drei `success/observed`, null Fehler.

**F. Passage/Weitererkundung:** Nur synthetisch im Produktgraph belegt;
keine reale Durchfahrt, keine Portal-ID als Voraussetzung eingeführt.

**Endzustand/Rückfall:** Geschlossene Bag mit Integritätsprüfung, null laufende
Missionen/Nav2-Statuseinträge und alle vier Befehlsströme null. Eigene
Launchwurzeln einzeln SIGINT, Recorder danach; sämtliche manifestierten
Prozesse beendet, beide Gerätealiases ohne Handles. Zwölf frische FC03-Paare
Position/RPM null; keine elektrische Motorstromstellung daraus behauptet.
Hauptkopie sauber auf `23928d92f411473ed2644692a04aebdff0ffe803`, kein permanenter
Install-/Autostartwechsel. Rückfall: isoliertes Overlay weglassen oder beide
Opt-ins beim gestoppten Neustart deaktivieren; ohne Mission
`active_drive=false`, `enable_auto_explore=false`. Private Nachweise ausschließlich
`~/.local/share/amadeus/tests/metric-egress-hwt-20261001/`, insbesondere
`runtime-byte-manifest-release.json`, `short-final/geometry-report.json`,
`short-final/passive-window-final.json`, `short-final/timing-analysis.json`,
`short-final/closed-preflight-analysis.json`, `end-state-proof.json` und
`end-encoder.json`. Kein automatischer weiterer Start. Konkrete offene
Grenzen: monotone originale Zeitzuordnung und eine tatsächlich zulässige
autonome erste Trajektorie. **Stufe 3 offen, ROS beendet, Rechner eingeschaltet.**

## 5. Erhaltener Umfang und nächste Meilensteine

Schritt 1/2 nicht neu beginnen; betroffene Wiederverwendung gezielt regressieren. Stufe 3: Softwareabschluss des metrischen Kerns erreicht; reale autonome Beobachtungsfolge, Hindernis-/Befreiungsfälle und vollständige Passage mit Weitererkundung weiterhin offen. Normale Fahrten benötigen keine Portal-ID mehr; physische Durchfahrt und freier Fahrweg bleiben nachzuweisen.

Danach metrischer WE-M4-Rundweg, WE-M5-Persistenz/Wiederaufnahme und WE-M6-Abschluss gemäß v1.2. Semantische Portal-/Regionskriterien werden separat geführt, nicht gelöscht oder rückwirkend erfüllt. Geparkter HWT-Kindziel-Injektionstest, optionale OAK-Türerkennung und zusätzliche Architekturvergleiche sind kein aktueller Parallelauftrag.

## 6. Git, Runtime und Rückfall

Ein Integrationsverantwortlicher, bestehender Branch/PR #105. Kein automatischer Merge, kein permanenter Installwechsel. LAB-1 ohne erneute Standardfreigabeschleifen anwenden. Gerätefreier Auftrag ist keine unbegrenzte Fahrerlaubnis.

Ein lokaler nicht veröffentlichter Berichtscommit mit Raumdaten wurde im Gespräch genannt. Die ausgehende Linie basiert direkt auf dem veröffentlichten Remote-Stand; private Berichtscommits sind keine Vorfahren. Auch bei späteren Pushes Vorfahren prüfen. Lokale Arbeit sichern und getrennt halten, keinen Force-Push oder destruktiven Reset ausführen. Der Funktionscommit basiert ausschließlich auf dem veröffentlichten Remote-Stand.

Rückfall: metrisches Overlay nicht aktivieren, `exploration_strategy: existing` beim geordneten Start ohne Mission; sicherer Betriebsrückfall `enable_auto_explore:=false`, `active_drive:=false`. Kein Branch-Rollback und keine bekannten offenen Befunde ausblenden. Bei Code-Revert auch die gemeinsame Absicherung verspäteter Nav2-Annahme berücksichtigen.

## 7. Historie und Nachweisregister

[Original-STATUS bis 99d21c0](archive/20260930-v1.1/STATUS.md), [Original-Agentenauftrag](archive/20260930-v1.1/AGENTENAUFTRAG.md), [Archivzuordnung und Originalpfade](archive/20260930-v1.1/README.md). Die Dateien sind unverändert erhalten. Maßgeblich für den jetzigen Auftrag sind Abschnitte 1–6 dieser Datei und der aktuelle AGENTENAUFTRAG, nicht ältere Aufträge aus dem Archiv.
