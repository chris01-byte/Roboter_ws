# Übertragung auf den realen Roboter

## Aktuell: isolierter Korrekturstand, reale Umfahrung noch offen (25.09.2026)

PR #100, Branch `fix/we1-stage3-vl53-regression`. Aktiver
`~/roboter_ws/install` unveraendert. Fuer motorlose Verifikation:
`/opt/ros/humble`, bestehende WE-Overlays,
`we1-stage3-frame-gap-r2/install` (VL53),
`we1-stage3-cancel-latch-r1/install` (Explorer); `robot_navigation`
weiter aus `we1-stage3-health-CVhWvH/install`. Das lokale, nach dem letzten
Odometrie-Endpunkt transformierte Scope-Profil ist
`/home/p/.local/share/amadeus/profiles/stage3-real-20260925-after-r2-scope.yaml`.
Nicht als neue physische Bereichsfreigabe oder als produktiven Install
uebernehmen.

Veraendert wurden nur Frame-Read-/Raster-Plausibilitaet und die
asynchrone Cancel-Ursachenbindung. 971 Tests bestanden; motorlos 44/44
gesunde Sensortripel, TF maximal 0,053 s, null Fahrbefehle, danach
korrekter Einzel-PID-Shutdown 24/24 sauber. Der vorangegangene
Terminal-Gruppenabbruch hatte KeyboardInterrupt-Tracebacks und zaehlt
nicht. Reale Testspur: sechs Quellen-Cancels, nur 0,1445 m Bewegung,
kein Vorbeifahren an der Barriere. `child_navigation_canceled`-Race ist
softwareseitig korrigiert, nicht real belegt. Bei `w=-0,12 rad/s` meldete
die Encoder-Odometrie zeitweise nur `-0,005...-0,04 rad/s` trotz etwa 34
Motor-rpm: Antrieb/Encoder/Schlupf vor weiterer Fahrt gezielt pruefen.
Keine Kalibrier- oder Sicherheitswerte auf Verdacht aendern. Stack aus,
keine offenen Geraetehandles. Evidenz im [WE-STATUS](wohnungserkundung/STATUS.md).
Nach einem rein formatierenden Rebuild des Explorer-Overlays versagte ein
weiterer voller motorloser Start durch VL53-Exit 1 vor ersten Topics;
Ursache nicht gesichert. Zwei isolierte VL53-Starts und ein weiterer voller
Start gelangen, aber kein vollstaendiger Preflight des letzten Builds.
Der genaue Fehler wurde danach im vollen Stack erfasst: rechter
VL53-MCU-Boot-Poll, `VL53L5CXException: 0`. Separates oberstes Overlay
`we1-stage3-vl53-boot-r1/install` wiederholt ausschliesslich diesen
Initialisierungsversuch einmalig und raeumt bei erneutem Fehlschlag auf.
974 Tests; zwei vollstaendige motorlose Preflights des exakten neuen
Installstands (58/58 und 57/57 gesunde Tripel, null Fahrbefehle) und je
24/24 saubere Shutdowns. Die Retry-Verzweigung wurde real nicht getroffen.
**Keine Fahrt**, bis die im vorherigen Realversuch gemessene deutliche
Motor-RPM-/Encoder-Odometrie-Abweichung geklaert und die A/B-Geometrie
erneut passend vorbereitet ist; die Startkorrektur allein ist kein
Umfahrnachweis.

## Aktuell: realer Rundblick wegen VL53-Frame-Health beendet (25.09.2026)

Der Nutzer korrigierte die folgende historische Aussage und bestätigte
Abschaltung und Prüfung vor Ort sowie die Fahrfreigabe. Diese Auskunft ist
kein ferntechnischer Hardwarebeweis. Exakt derselbe isolierte Health-Install
und dasselbe Scope-Profil wurden verwendet; kein aktiver Install und keine
Produktparameter geändert (Repository `3913079`, PR #100).

Vorlauf bestanden: 57 gesunde VL53-Tripel je Seite, TF frisch, alle sechs
Lifecycles aktiv, gemessene RPM null. Ein autonomer Explorerauftrag startete.
Nach 13,267 s im Rundblick beide `frame_healthy=false`, Fahrtor `blocked`,
Wächter-Cancel. Bei 16,082 s gemessene RPM mindestens zwei Sekunden null;
Shutdown 24/24 sauber. Keine Umfahrung und keine Tests C/D. Ursache des
beidseitigen Health-Abfalls noch offen; nicht durch gelockerte Grenzwerte
oder wiederholte Fahrversuche umgehen. Stack bleibt aus. Details/Evidenz:
[WE-STATUS](wohnungserkundung/STATUS.md).

## Historisch: Sicherheitsstopp nach gegenteiliger Nutzeraussage (25.09.2026)

**Keine weitere reale Fahrt oder Motoraktivierung.** Der Nutzer erklärte
nach dem unten dokumentierten Teilversuch, am Roboter existiere überhaupt
kein hardwired Not-Aus und die Motorversorgung könne nicht ausgeschaltet
werden. Die frühere Vor-Ort-Bestätigung eines erreichbaren Not-Aus ist
damit widersprüchlich und darf nicht mehr als Sicherheitsnachweis gelten.
Die 0,18-m-Kurzfahrt bleibt eine technische Beobachtung, **keine gültige
reale Sicherheitsabnahme**. Software-Cancel und ROS-Shutdown sind kein
Ersatz für eine unabhängige Abschaltmöglichkeit. Der Stack ist gestoppt;
kein RS485-Handle ist offen.

Nach dieser Offenlegung nur passive Starts mit `dry_run=true`, RS485 aus,
null Motorsollwerten. Eine neue 0,75 m hohe, 0,55 m breite Barriere etwa
0,55 m vor dem Roboter wurde vom LiDAR frontal ab ca. 0,81 m Achsabstand
gesehen; Nav2 berechnete im geladenen Scope rechts einen Diagnosepfad mit
106 Posen. 59 gesunde VL53-Teilframes je Seite im Preflight, frische
TF-/Karten-/LiDAR-Daten und aktive Safety/Nav2. Das ist **keine** reale
Umfahrung und kein autonomes Explorerziel. Beide Starts endeten mit
24/24 sauberen Kindern. Keine Produkt-/Sicherheitsparameter und kein
aktiver Install wurden geändert. Weitere Fahrt erst nach Herstellung
und Vor-Ort-Nachweis einer unabhängig wirksamen Hardware-Not-Aus- oder
Motorstromtrennung; neue ausdrückliche Freigabe erst danach relevant.
Siehe [WE-STATUS](wohnungserkundung/STATUS.md).

## WE-1 Stufe 3: reale Kurzfahrt A, B ohne Route beendet (25.09.2026)

PR #100, Quellstand `a710fe3`, ausschließlich isolierter Install
`we1-stage3-health-CVhWvH/install`; der aktive Install blieb unverändert.
Vor Ort wurden Not-Aus, menschen-/tierfreier Bereich und Motorstrom
bestätigt. Ein lokales Scope-Profil band die frische Startkarte
(`map`-Pose `(0,0,0)`) an `x=[-0,5;2,6]`, `y=[-0,8;0,8]`. Der
motorisierte Vorlauf hatte 59 frische gesunde VL53-Tripel je Seite,
frische LiDAR-/Karten-/TF-/Odom-Quellen, Nav2 und Collision Monitor aktiv,
Safety frei, RS485 bereit und vor Auftrag 0 Fahr-/Motorwerte.

Test A: Nach autonomer Zielwahl fuhr der Roboter 0,18 m laut Odometrie;
Test-Cancel, Mission `canceled`, beide Motor-RPM 0 für mindestens 2 s.
Test B: 0 m Translation, kein Nav2-Pfad. Die Explorer-Policy hatte nach
Rundblick 10 offene, aber 0 zulässige Aufgaben (`no_current_raw_map_route`
oder auf aktueller Revision nicht beobachtet). Der separate Wächter
meldete später `guard_lost`; der Einzelgrund ist nicht gemessen.
Die reale Barriere war nur 0,40 m hoch und 0,38 m breit, etwa 1 m leicht
links vor der Ausgangspose: unter der 0,66-m-LiDAR-Ebene und damit kein
gültiger Aufbau für den vorgesehenen frühen LiDAR-/Nav2-Umfahrnachweis.
Keine Umfahrung oder Missionsfortsetzung nach Hindernis behaupten.
C/D nicht gestartet. Kein Produktparameter und keine Sicherheitsgrenze
geändert, kein Merge. Logs/Wächterbericht lokal unter
`~/.local/share/amadeus/tests/stage3-real-*`, Scope-Profil unter
`~/.local/share/amadeus/profiles/stage3-real-20260925-scope.yaml`.

Der Stack ist mit SIGINT **nur an Launch-PID** beendet: 24/24 Kinder
sauber, kein Traceback, Prozessrest oder offener I²C-/LiDAR-/RS485-Handle.
**Motorversorgung wird nicht softwareseitig getrennt; nach der späteren
Nutzeraussage ist physisches Ausschalten derzeit nicht möglich.** Erst die
oben genannte Hardware-Sicherheitslücke schließen; danach Route/Policy und Wächtergrund
motorlos diagnostizieren sowie eine mindestens 0,80 m hohe matte
bleibende Barriere mit gemessenen Passagen vorbereiten. Danach erneuter
motorloser Check und separate aktuelle Fahrfreigabe; B vor C/D.
Stufe 3 bleibt GELB. Details im [WE-STATUS](wohnungserkundung/STATUS.md).

## WE-1 Stufe 3: finaler Health-Kandidat motorlos bestanden (25.09.2026)

PR #100, Produktcommit `e18a267`, finaler Gerätefrei-Prüfstand `b692c28`.
Die aktuelle Produktvorgabe trennt technische Framegesundheit von
Target-/Spaltenabdeckung. Die unten beschriebenen früheren
Fahrvertragsblocker sind Historie, nicht der aktuelle Health-Vertrag.
Gesunde vollständige Teilframes sperren nicht global; unbekannte Zonen
bleiben ohne Clearingstrahlen. Reale gültige Nahpunkte, Juli-Filter,
FLIPX, Sensorfrische und sämtliche Fahr-/Kollisionsgrenzen unverändert.

**Ausschließlich isolierter Install, kein aktiver Install überschrieben:**
`/home/p/.local/share/amadeus/releases/we1-stage3-health-CVhWvH/install`.
Enthält gemeinsam neu gebaut `robot_interfaces`, `vl53_near_field`,
`robot_navigation`, `explore`, `safety_monitor`; Quell-/Install-SHA und
VL53-/Nav2-Konfiguration stimmen überein. Statusformat enthält nun
`left_frame_healthy`/`right_frame_healthy`; keine alten Consumer mischen.
Die reale Prozessauflösung bestätigte diese fünf Pakete, Stage-3-complete
für Basis/Manager und Stufe 1 für Bring-up. Vollständige Overlaykette im
maßgeblichen [WE-STATUS](wohnungserkundung/STATUS.md).

Mit unverändert physisch getrennter Motorversorgung zweimal gestartet:

```bash
source /home/p/.local/share/amadeus/releases/we1-stage3-health-CVhWvH/install/setup.bash
export ROS_DOMAIN_ID=217
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export CYCLONEDDS_URI=file:///home/p/.local/share/amadeus/releases/we1-10e1858074e7-r1/cyclonedds-local.xml
unset ROS_LOCALHOST_ONLY
ros2 launch robot_bringup app_mapping.launch.py active_drive:=false enable_auto_explore:=false start_web_gui:=false
```

Keine Action gesendet, kein Nichtnull-Fahrbefehl. Je ca. 15 s: 59/56
stempelgleiche frische VL53-Tripel, beide Health true/PARTIAL/Maske 0;
installierte Health-Prüfung auf realen Daten positiv. Kartenmanager ok,
LiDAR/Karte/Odom/TF frisch (maximales TF-Alter 0,034 s), alle fünf
Nav2-Lifecycles und Collision Monitor active, Safety false. Basis
`dry_run=true`, `allow_rs485=false`, `rs485_ready=false`, alle Sollwerte 0.
Jeweils 24/24 Kinder sauber nach SIGINT **nur an Launch-PID**, kein
Traceback/Restprozess/offener Gerätehandle. Prüfberichte nur lokal unter
`~/.local/share/amadeus/tests/stage3-health-hardware-cycle{1,2}.{json,log}`.

Dieser passive Test ließ Explore-Opt-in und Scope-Verifikation bewusst
aus; der alte R9-Scope ist nach Kartenneustart nicht gültig. Vor Fahrt
vermessenen markierten Bereich/Startpose an aktuelle Karte binden und
gesonderte aktuelle Fahrfreigabe einholen. Konkreter Vorschlag im
WE-STATUS: 4,70 × 2,50 m, hohe unbelebte bleibende Barriere, separate
Stopp-/Wand-/Eckaufstellung, begrenzte Mission und klare Abbruchbedingungen.
Noch **keine reale Umfahr-/Stoppbefreiungsabnahme**, Stufe 3 insgesamt GELB.
Motorloser Check bestanden; weitere Softwareentwicklung hier beendet.
Rückfall: komplettes neues Overlay nicht sourcen; vorheriger Stand sperrt
weiter streng. Das verworfene `we1-stage3-vl53-partial-PiRlgn` nicht nutzen.

## Historie: realer VL53-A/B-Test, passive Zielsystemwiederholung (25.09.2026)

Die echte matte Platte (~1 × 1 m, ~0,40 m vor beiden VL53) ergab links und
rechts je 30/30 vollständige Rohframes mit 64/64 gültigen Targets,
`target_status=5`, `nb_target_detected=1`, kleinen Sigma-Werten und je
64 Original- sowie 8 Costmap-Punkten. Nach Entfernen der Platte lieferten
dieselben Sensoren/Konfigurationen je 30 vollständige Frames, aber nur
2–6 gültige Fernreturns pro Frame in der untersten Sensorzeile, 0 volle
Spalten, `QUALITY_PARTIAL` und leere Nahwolken. Die Hardware ist damit
plausibel; die neue globale 64/64-Forderung ist für freie Szenen nicht
praktikabel und nicht real fahrabgenommen. Einzelne fehlende Targets
bleiben **unbekannt**, niemals pauschal 0,60 m frei. Rohframes und
Auswertung sind nur lokal unter
`/home/p/.local/share/amadeus/tests/we-stage3-vl53-ab-20260925.json`.

Das ausschließlich isolierte Präfix
`/home/p/.local/share/amadeus/releases/we1-stage3-vl53-partial-PiRlgn/install`
enthält eine **verworfene** pauschale `PARTIAL`-Freigabe im Explorer/Fahrtor.
Sie bestand gerätefreie Prozessfälle, besitzt aber keinen positiven
Bewegungsraumbeleg; **nicht für Fahrt oder künftige Freigabe sourcen**.
Der Quellbranch/PR #100 enthält diese Änderung nicht. Sein marking-only-
ObstacleLayer-Fix ist davon unabhängig. Der aktive Roboter-Install und alle
Fahr-/Sensorgrenzen blieben unangetastet.

Mit physisch getrennter Motorversorgung wurden zwei vollständige passive
Starts über das isolierte Präfix geprüft: beide VL53, LiDAR, TF, Rohkarte,
Kartenmanager, Safety, Collision Monitor und Nav2 waren frisch/aktiv;
`active_drive=false`, Explore-Opt-in aus, `dry_run=true`, RS485 aus,
alle Fahr- und Motorsollwerte null. Je Start 24/24 saubere Kinder beim
Einzel-PID-SIGINT, keine Tracebacks, Restprozesse oder Gerätehandles.
Danach bestanden auch **zwei Starts ohne das verworfene Präfix** auf dem
strengen PR-#100-Stand mit Explorer-Shutdown- und marking-only-Overlay:
beide VL53 `PARTIAL`/Maske 0, Safety aus, Collision Monitor/Nav2 aktiv,
acht Fahrbefehlskanäle ohne Nichtnullwert, Basis Dry-run/RS485 aus und
jeweils 24/24 saubere Kinder ohne Rest-Handle. Der normale freie Raum
bleibt mit diesem Stand am Fahrtor gesperrt, wie beabsichtigt.
Der vorhandene R9-Scope ist nach SLAM-Neustart nicht mehr gültig und wurde
deshalb nicht geladen; der Explorer meldete `scope_verified=false`.
Der vollständige motorlose *Fahrbereitschafts*-Nachweis bleibt offen:
Vor Fahrplanung sind aktueller Kartenframe/Startpose/enger Scope und ein
positiver Beleg für den tatsächlich nötigen niedrigen und seitlichen
Fahrraum erforderlich. LiDAR bei 0,66 m und im WE-Launch deaktivierte OAK
ersetzen die unbekannten VL53-Zonen nicht. Keine reale Fahrt ohne gesonderte
Vor-Ort-Fahrfreigabe. Rückfall für das Testpräfix: nicht sourcen.

## WE-1 Stufe 3: VL53-Regression, Teilframe-Markierung (24.09.2026)

Der neue, ausschließlich motorlose Direktlauf las je 20 vollständige
Rohframes aus beiden echten VL53. Derselbe lokale Frame-Satz ergab mit dem
historischen Nahfilter 0 Hindernispunkte im freien Nahbereich; die heutige
Qualitätsauswertung fand je 220 gültige Fern-Zonen, aber 0 volle Spalten.
Eine komplette Rohdatennachricht ist somit nicht gleich 64 gültigen
Target-Returns. Die überwiegend unbeobachteten Zonen dürfen nicht als frei
gelten. Eine große, matte unbelebte Testfläche im Sichtfeld beider Sensoren
wurde noch nicht vermessen; die Hindernis-A/B-Prüfung fehlt.

Ein separater Kandidatenbranch ergänzt die bestehende VL53-Originalwolke
als **marking-only**-Quelle in beiden Nav2-ObstacleLayern. Dadurch kann ein
gültiger Nahpunkt aus einem Teilframe ein Hindernis markieren; er kann keine
unbekannten Zellen räumen. `robot_navigation` liegt nur im isolierten Overlay
`/home/p/.local/share/amadeus/releases/we1-stage3-vl53-mark-bwVxEL/install`;
der aktive Roboter-Install blieb unberührt. 969 Vertragstests und vier
gerätefreie echte Nav2-Stage-3-Prozessfälle bestanden, darunter dauerhafte
Umfahrung mit Explorer-Folgefortschritt und Stopp/Befreiung. Das Fahrtor
bleibt wegen der nicht belegten Bewegungsraumabdeckung gesperrt. Rückfall:
dieses letzte Overlay nicht sourcen. Keine reale Fahrt freigeben, bevor
Sensorabdeckung, aktueller Scope und vollständiger motorloser Preflight
positiv nachgewiesen sind.

## WE-1 Stufe 3: motorloser Zielsystembefund, Fahrt gesperrt (24.09.2026)

Nach ausdrücklicher Vor-Ort-Freigabe wurde der vorhandene Stufe-3-Kandidat
mit realen Sensoren, aber `active_drive=false`, `enable_auto_explore=false`
und physisch getrennter Motorversorgung gestartet. Die Stufe-3-Pakete lösten
aus `we1-stage3-complete-1kI6en` auf, LiDAR-Bring-up und `robot_bringup` aus
Stufe 1. Nach einem nachgewiesenen Explorer-SIGINT-Race wurde **nur** das
separate `explore`-Overlay
`/home/p/.local/share/amadeus/releases/we1-stage3-explorer-shutdown-dnrGyH/install`
zuletzt gesourct (Quellcommit `0fe9245`, gleiche Quell-/Install-SHA). Zwei
vollständige Wiederholungsstarts endeten mit je 24/24 sauberen Kindern,
ohne Restprozess oder Gerätehandle. Der aktive Robot-Install blieb unberührt.

**Fahrblocker:** Beide realen VL53 sind zwar frisch (~3,6 Hz), aber im
aktuellen freien Raum in sämtlichen Stichproben nur `QUALITY_PARTIAL` mit
Spaltenmaske `0/255`. Der separate Rohdatenlauf ergab links 223/1280 und
rechts 233/1280 gültige Zonen, beidseits 0/160 volle Spalten, vorwiegend
Status 255/kein Ziel. Der 64/64-Vertrag und damit das Fahrtor sind nicht
erfüllt; das ist keine Erlaubnis, ihn oder andere Sicherheitsgrenzen zu
lockern. LiDAR, Karte, TF, Kartenmanager und Nav2 waren passiv frisch,
Fahrkanäle und Motor-Sollwerte null. Das geladene R9-Profil trägt noch das
alte `scope_verified=true`, hat aber keine neue physische Bindung an den
aktuellen SLAM-Frame. Kein Realversuch und keine Fahrfreigabe. Für eine
erneute Prüfung eine motorlose, vor Ort kontrollierte VL53-Szene mit
nachgewiesenen Rückgaben beider 8×8-Raster sowie die aktuelle Startpose und
Scope-Grenze im neuen Kartenframe messen; erst danach einen eng begrenzten
Umfahr-/Stoppbefreiungsaufbau festlegen und gesondert zur Fahrt freigeben
lassen. Keine reale Wohnungsgeometrie ins Repository übernehmen.

**Rückfall:** Das neue `explore`-Overlay weglassen, aber das ältere
Kandidatenpräfix wegen seines Egg-Links nicht als eingefrorenen Rollback
ansehen. Der vor `0fe9245` geprüfte Quellstand hatte den dokumentierten
Shutdown-Race; die reale Sensorqualität sperrt beide Varianten für Fahrten.

## WE-1 Stufe 3: neuer isolierter Softwarekandidat, nicht deployt (24.09.2026)

Ausgangsstand PR #99, Branch `feature/we1-stufe3-local-recovery`,
`2914279`; Softwarecommits `785b825`, `e3d7352`, `aa699b0`.
Der neu gebaute Kandidat liegt nur unter
`/home/p/.local/share/amadeus/releases/we1-stage3-complete-1kI6en/install`.
Reihenfolge: `/opt/ros/humble` →
`/home/p/amadeus_slam_toolbox_ws/install` →
`we1-ldlidar-shutdown-overlay` → `we1-10e1858074e7-r1` →
`we1-stage1-5e3fe0a-20260923` → `we1-stage2-6fd36d5-20260923` →
`we1-stage3-bypass-s8QMY8` → diesen Kandidaten. Die neun Pakete
`robot_interfaces`, `vl53_near_field`, `robot_navigation`, `explore`,
`robot_map_manager`, `safety_monitor`, `mission_manager`, `bt_orchestrator`
und `base_hardware` wurden neu gebaut und lösen aus diesem Präfix auf.
Die Python-Pakete `explore` und `robot_navigation` sind in diesem isolierten
Kandidaten per Egg-Link auf den zugehörigen Build gebunden; Source-/Build-
Hashes stimmen überein. Dieses Entwicklungspräfix nicht blind als
unabhängig kopierbares Deployment-Image behandeln.
`bt_orchestrator` benötigte für den Build den vorhandenen separaten
`behaviortree_cpp`-CMake-Underlay unter
`we1-10e1858074e7-r1/underlay/behaviortree_cpp`; der erste Lauf ohne
diesen Pfad scheiterte. Das ist kein Robot-Deployment.

**Jetson-Wirkung bei einer künftigen bewussten Übernahme:** Die additive
`NearFieldStatus`-Schnittstelle verlangt kohärenten Neubau/Start von
Produzent und sämtlichen Verbrauchern. Ein alter Publisher meldet Qualität
0 und sperrt Fahrtor/Explorer; bei aktiviertem optionalem VL53-Safety-Notstopp
bleibt auch dieser gesetzt. Gültige Fernmessung kann eine leere Originalwolke
haben, aber nur mit gemessenem Status 5, Zielanzahl, Sigma, plausiblem
Messwert, Vollabdeckung und gleichem Stempel. Die Costmap bekommt keine
Räumstrahlen aus unbeobachteten Spalten. Safety-Timeout 0,8 s ist neu
streng, nicht gelockert. Nav2 `nav2_params_real.yaml` verfolgt im Kandidaten
0,40 m statt 0,80 m voraus und dreht ab 0,35 rad statt des RPP-Defaults;
Footprint, Padding, Collision Monitor und Geschwindigkeiten sind unverändert.
Das Fahrtor verlangt nun zusätzlich `/safety/estop=false` mit Empfangsalter
höchstens 1,0 s und frisches Basis-/Karten-TF (0,2/0,8 s). Ein allein
gestartetes `nav_real.launch.py` ohne Safety-Publisher bleibt daher bewusst
gesperrt. Der normale `robot.launch.py`- und WE-Mapping-Start enthält den
Safety-Monitor; trotzdem sind tatsächliche TF- und Statusfrequenzen motorlos
zu messen, bevor dieser Kandidat die aktive Hardwarekette ersetzen dürfte.

Der gerätefreie frühe **und** späte dauerhafte Umfahrfall A→B bestanden
auf dem finalen Kandidaten mit echter Nav2-Kette, automatischer Explorerwahl,
nachgewiesenem Kartenfortschritt und weiterlaufender Elternmission. Im
späten Fall wurde ein notwendiger Controller-Stopp vor der unverändert
stehenden Barriere gemessen; die frühere B-Stornierung wurde als Folge von
Frische-/Karten-Duplikat-Races getrennt behoben. Sensor-, Software-Not-Aus-
und TF-Ausfälle endeten gerätefrei hart ohne Wiederanfahrt. Ein Software-
Not-Aus-Diagnoselauf überschritt die anfängliche 25-mm-Prüfergrenze mit
26,3 mm; die nachgelagerte unveränderte Velocity-Smoother-Rampe erklärte
den Restweg. Der korrigierte gerätefreie Prüfer misst Gate-/Ausgangs-
Nullzeit und einen aus der bestehenden Verzögerung abgeleiteten 40-mm-
Diagnoserahmen; er ist **kein** Hardware-Not-Aus- oder Bremswegbeleg.
Die ungeprüfte
reale Sensor-/TF-Verfügbarkeit hält Stufe 3 **insgesamt** offen. Zwei
Einzel-PID-SIGINTs während eines Karten-Saves endeten sauber mit erhaltenen
Dateien; der historische `take_message()`-Zeitpunkt wurde nicht gezielt
getroffen. Kein Zielgerät, kein Gerät, kein Motor und keine echte Karte wurden
hierfür berührt. Details/Evidenzpfade stehen im maßgeblichen WE-STATUS.

**Vor Ort noch erforderlich:** Startpose und aktueller Kartenframe/Scope,
Hinderniskontur, lichte Umfahrbreiten, freier Schwenkraum, Auslauf,
Hardware-Not-Aus, passive VL53-Qualitätsverteilung beider Seiten,
motorloser Gesamtstart/-stopp. Insbesondere die reale VL53-64/64-Qualität
und die `map→odom`-/`odom→base_link`-Publikationsrate gegen die neuen
Gate-Grenzen prüfen. Erst danach und mit neuer konkreter
Vor-Ort-Freigabe ein begrenzter Realversuch. Der frühere enge Scope ohne
Frontierziel darf nicht zum Umfahrtest erweitert oder geraten werden.

**Rückfall:** Dieses Präfix in einer frischen Shell weglassen. Aktiver
Jetson-Install, bisherige Overlays und Wohnungsdaten bleiben unverändert.

## WE-1 Stufe 3: permanente Umfahrung softwaregeprüft, reale Übernahme offen (23.09.2026)

Produktionsquellstand `90379d9`, Prozessprüfer `d13a6c9` auf
`feature/we1-stufe3-local-recovery`, PR #99 weiterhin
offen. Das neue **nur gerätefrei verwendete** Install liegt unter
`/home/p/.local/share/amadeus/releases/we1-stage3-bypass-s8QMY8/install`.
Sourcereihenfolge: ROS Humble → bestätigte Stufe-1-Kette → Stufe 2 → dieses
Präfix. `ros2 pkg prefix explore` und Dateivergleich belegen das neue Paket;
Quell-/Install-SHA von `explore_node.py` jeweils
`485435a0effe6c32efd74da4995a92584d6b01dff255f2010c6e003327fb8fe0`.
Alle übrigen Pakete kommen aus den bisherigen Underlays; Nav2- und
Collision-Monitor-Konfiguration wurden bytegleich mit Stufe 1 verglichen.
Keine Roboterinstallation, kein reales Profil und kein Gerät wurden geändert.

Die echte Nav2-Kette in DDS 219 umfuhr eine stehenbleibende synthetische
Barriere mit automatisch gewähltem Explorerziel. Danach bestätigte eine neue
Rohkarte den Frontierabschluss, ein anderer automatisch gewählter Auftrag
wurde erfolgreich abgearbeitet und dieselbe Elternmission blieb aktiv.
Live-Footprint, geplante/virtuell gefahrene Kontur, Ausgänge der Schutzkette,
maximal ein Kindziel und 0 m Rückwärtsfahrt wurden überprüft. Das ist ein
Softwarebeleg, keine physische Probefahrt. Der unlösbare Gegenfall blieb ohne
Kindziel/Bewegung und endete mit erklärtem Teilstand.

**Vor realer Übernahme weiterhin offen:**

- Notwendiger Stopp mit anschließender Befreiung: frischer NavFn-Umweg
  vorhanden, Regler stoppt aber wegen vorausberechneter Costmap-Kollision.
  Keine Regler-/Sicherheitsgrenze versuchsweise ändern.
- Leere VL53-Originalwolken belegen Empfang, aber keine Messgesundheit.
  Gültige Fernmessung und ungültige Messung sind im heutigen Statusvertrag
  ununterscheidbar. Der Explorer sperrt dann lokale Recovery. Ein eindeutiger
  Sensorstempel-/Gültigkeitsvertrag mit den Verbrauchern ist gesondert nötig;
  insbesondere ist der bisherige Fahrtor-Heartbeat kein Qualitätsnachweis.
- Den bekannten Kartenmanager-SIGINT-Race klären und anschließend einen
  geeigneten motorlosen Gesamtstart/-stopp nachweisen. Dieser Folgeauftrag
  enthält keine Erlaubnis für Hardwarezugriff.
- Aktuelle Startpose/Orientierung, Barrierenkontur, lichte Alternativbreiten,
  freier Schwenkbereich und Auslauf vor Ort messen und an den aktuellen
  Kartenframe/Scope binden. Keine synthetischen Maße als reale Freigabe nutzen.
  Eine reale Fahrt braucht danach die aktuelle ausdrückliche Vor-Ort-Freigabe.

Details, feste Diagnosegeometrie und konkrete Testgrenzen stehen ausschließlich
im laufenden WE-STATUS. **Rückfall:** Neues Präfix weglassen; das vorherige
isolierte Install und der aktive Roboterstand sind unverändert vorhanden.

## WE-1 Stufe 3: neues gerätefreies Nav2-Overlay, nicht auf Antrieb übernehmen (23.09.2026)

Das zusätzliche Stage-3-`explore`-Install
`/home/p/.local/share/amadeus/releases/we1-stage3-routeblock-20260923/install`
liegt **nur isoliert** vor und wurde nicht in den aktiven Roboterstart
übernommen. Quell- und Installdatei `explore_node.py` wurden per SHA-256
verglichen (beide
`be6c8f7da787fa51a57a9bebf87cf0ee1e440a049be57f3eef7af897b6c9c6ef`).
Die Reihenfolge ist ROS Humble → bestätigte Stufe-1-Kette →
Stufe 2 → dieses Stage-3-Overlay; die Nav2-/Collision-Konfiguration kommt
unverändert aus Stufe 1. Der neue Prüfer in DDS-Domain 219 startet keinen
Hardwaretreiber und sendet keine Motorregister. Er belegte zweimal mit
echtem Nav2, Fahrtor und Collision Monitor: Hindernis → Stopp → freie
Sensorstrecke → weitere virtuelle Fahrt → Zielerfolg → Rohkartenfortschritt
→ nächstes Frontierziel. Bei dauerhaftem Hindernis verhinderte die neue
enge Nahkorridor-Klassifikation den zuvor beobachteten sofortigen
`SYSTEM_FAILURE` nach einem zweiten Nav2-Abbruch. Ein echter sicherer
Umweg blieb in zwei synthetischen Positionen aus. Eine zurückgestellte
Aufgabe bleibt bei weiter belegtem Zielkorridor auch nach neuer Costmap
gesperrt; der gerätefreie Gegenlauf blieb nach drei begrenzten Kindzielen
ohne Bewegung stehen und wartete auf eine sichere Alternative.

**Keine reale Fahrt daraus ableiten:** Der letzte motorlose reale WE-Vorlauf
hatte kein gültiges Ziel im engen Scope; das links stehende Hindernis löste
nur Slowdown, keinen Stopp aus. Der einmal beobachtete Kartenmanager-
Shutdown-Race ist weiterhin offen. Vor einem Fahrversuch müssen diese drei
Punkte motorlos geklärt sein; das Fahrtor und die Sicherheitsgrenzen bleiben
unverändert. Rückfallweg: neues Stage-3-Präfix nicht sourcen, stattdessen
das vorherige isolierte Stage-3-Kandidatenpräfix verwenden; kein automatischer
Merge oder Deploy.

## WE-1 Stufe 3: lokale Hindernisbehandlung nur teilweise belegt (23.09.2026)

**Neues physisches Hindernis links (23.09. abends), nur motorlos:** Der linke
VL53 erkannte wiederholt ~0,24–0,25 m, der rechte keinen Nahpunkt. Bei
`dry_run=true`/`allow_rs485=false` ließ der bestehende WE-Collision-Monitor
einen synthetischen Vorwärtswunsch von 0,08 m/s nur mit höchstens 0,024 m/s
durch (SlowZone), nicht mit null. Das Mapping-Profil besitzt eine
bewegungsabhängige Footprint-Approach-Zone; die ältere starre StopZone darf
hier nicht unterstellt werden. Kein Motorstrom, keine reale Bewegung und kein
Recovery-Nachweis. Den aus Dry-run resultierenden Odometrie-/Kartenstand nicht
für eine Fahrt weiterverwenden.

Der anschließende Einzel-SIGINT erzeugte bei `robot_map_manager` einen
`take_message()`-RuntimeError und Exit 1; alle anderen Kinder stoppten sauber,
alle Gerätehandles waren danach frei. Dieser Shutdown ist **nicht** als
Stufe-1-artig sauber abzunehmen. Vor einer realen Fahrt den Race klären,
frischen motorlosen Preflight mit überprüftem Fahrziel durchführen und das
Hindernis nur in einer nachweislich sicheren Testanordnung verwenden. Keine
Schwellen, Footprints oder Fahrtore abschwächen.
Ein unmittelbar folgender motorloser Wiederholungslauf ohne synthetischen
Fahrwunsch sah denselben linken Nahpunkt und stoppte alle 24 Kinder sauber,
ohne Traceback oder offene Gerätehandles. Der erste Race bleibt ungeklärt;
der zweite Lauf beweist nur, dass er nicht bei jedem Stopp auftritt.

**Nachtrag nach Vor-Ort-Freigabe (23.09.):** Auf dem Jetson bestand ein erneuter
passiver WE-Preflight mit Stufe-3-Explorer aus dem isolierten Präfix und allen
anderen WE-Paketen aus der bestätigten Stufe-1/2-Kette. Der Stack lief mit
`active_drive:=false`, realen LiDAR-/VL53-Daten, aktivem Collision Monitor und
Nav2, frischer Rohkarte/TF/Safety und Basiswerten durchgehend null. Ein
einziger SIGINT beendete 24 Kinder sauber; Gerätehandles waren danach frei.
Es wurde kein Fahrbefehl gesendet. Für einen Hindernisversuch sind Startpose,
unbelebte Barriere und sicherer Auslauf noch nicht benannt. Eine gewünschte
freie Kurzfahrt ohne Barriere ist nur ein Basis-/Fahrkettencheck, kein
Stufe-3-Nachweis und braucht eine eigene enge Bewegungsgrenze.
Für den später gewünschten freien Kurztest kam ein weiterer Blocker hinzu:
Das lokale R9-WE-Profil untersagt selbst die Wiederverwendung seiner
Scope-Koordinaten nach SLAM-Neustart. Der passive Vorlauf startete SLAM neu;
Profil-Hashgleichheit ist daher keine gültige physische Scope-Bindung. Vor
einer WE-Fahrt den begrenzten Raum im aktuellen Kartenframe neu messen und
von der anwesenden Person bestätigen lassen. Bis dahin Motoren auslassen;
keine Sicherheitsschwelle ändern oder das Fahrtor umgehen.

Nach Vor-Ort-Bestätigung des einzelnen Raums und geschlossener Ausgänge wurde
ein neues lokales Einmalprofil für einen eng begrenzten, vorwärtsgerichteten
Ein-Ziel-Test im neuen Kartenframe erstellt (Profilpfad und Hash stehen im
WE-Status). Der echte WE-/Nav2-Gesamtprozess wurde damit **nur motorlos**
gestartet: Karte/TF/LiDAR/VL53/Safety waren frisch, Basis `dry_run=true`,
`allow_rs485=false`; der Explorer fand bis zum 75-s-Gesamtbudget kein gültiges
Ziel. Kein Nav2-Fahrkommando, keine Odometriebewegung, danach sauberer Stopp
und freie Gerätehandles. Der Versuch darf nicht scharf wiederholt werden, nur
um ein Ziel zu erzwingen. Erst eine neu vor Ort vermessene Kurzroute und ihr
motorloser Scope-/Nav2-Nachweis erlauben eine reale Probefahrt.

**Ausgangsstand:** bestätigter Stufe-2-Branch bei `3fa3ce6` auf der
Stufe-1-Overlaykette mit Stufe-2-`explore` als letztem Präfix. Der neue
Themenbranch `feature/we1-stufe3-local-recovery` bei Produktionscommit
`d6c6fa9` (Review-PR #99, nicht gemergt) ändert nur Explorer-Code, sein
Profil, Tests und den vorhandenen Prozessprüfer. Der produktive
Roboterstand und die lokale Standardinstallation wurden nicht verändert.
Der einzige neue Build ist das isolierte Präfix
`~/.local/share/amadeus/releases/we1-stage3-candidate-20260923/install`;
es wurde testweise **nach** dem Stage-2-Präfix gesourct.
`ros2 pkg prefix explore`, Python-Import und Quell-/Install-Hash ordneten den
Explorer diesem Präfix zu.

Der Explorer stuft ein terminales Frontier-`ABORTED` nur bei frischer
Costmap-Hindernisevidenz, gestoppter Odometrie, frischem map-TF, LiDAR, beiden
VL53-Streams und freiem Not-Aus als `LOCAL_BLOCKED` ein. Andernfalls bleibt
es ein Systemfehler. Eine blockierte Aufgabe wird begrenzt zurückgestellt;
ein anderes geprüftes Ziel kann übernommen werden, das erste erst nach
frischer, unprojiziert freier Costmap erneut. Nav2-/Collision-Monitor-
Parameter, Footprint, Padding und Scope wurden nicht geändert; Spin und
BackUp bleiben vom Fahrpfad getrennt.

902 Explorer-Pytests und der achtteilige gerätefreie Gesamtprozessprüfer aus
dem Quellbaum sowie gegen das isolierte Install bestanden. Der Prüfer mit
Fake-Nav2 belegt Elternfortsetzung nach lokalem Kindabbruch und kontrolliertes
Warten ohne Ausweg, **nicht** die
sichere Bewegung des realen Controllers. Sein DDS-Bereich ist vom Roboterdomain
getrennt; alle synthetischen Sensoren haben eigene Testtopics. Beim damaligen
Prüflauf war der R9-Befund links (~0,24 m) noch offen; eine Motorfreigabe,
Gerätezugriff oder Fahrbefehl fand dabei nicht statt. Die inzwischen
vorliegende Vor-Ort-Bestätigung und der passive Vorlauf oben ersetzen keinen
produktionsnahen Hindernis-/Collision-Monitor-Nachweis. Bis der begrenzte
Testaufbau festgelegt und motorlos überprüft ist, darf die Stage-3-Installation
nicht als Fahrprofil verwendet werden.

**Rückfall:** Stufe-3-Präfix in einer neuen Shell auslassen; die bestätigte
Stufe-1/2-Kette bleibt unverändert. Es ist nichts auf dem Jetson zu entfernen
oder zurückzukopieren.

---

## WE-1 Stufe 2: gerätefreie Frontierfortsetzung (23.09.2026)

**Basis:** bestätigter Stufe-1-Stand `5e3fe0a` mit dessen unveränderter
Overlaykette. Der Stufe-2-Branch `feature/we1-stufe2-replan-fortsetzung`
ergänzt nur `explore` aus Produktionscommit `6fd36d5`. Isoliertes Install:
`~/.local/share/amadeus/releases/we1-stage2-6fd36d5-20260923/install`.
Es wird **nach** dem Stufe-1-Präfix gesourct; alle anderen Pakete bleiben auf
ihrem in Stufe 1 bestimmten Präfix. `ros2 pkg prefix explore`, Python-Import
und Dateihash bestätigten genau dieses neue Install. Weder die Standardkopie
`/home/p/roboter_ws/install` noch ein aktiver Roboterdienst wurden ersetzt.

Die neue gerätefreie Prozessprüfung hält Ziel A auf einer sicheren neuen
Kartenrevision und auf einem reinen Zeitstempelduplikat aktiv. Wenn A durch
eine echte belegte Zelle ungültig wird, folgt auf bestätigten Kindziel-Cancel
automatisch Ziel B. B wird erfolgreich verarbeitet und seine Frontieraufgabe
auf einer folgenden Karte abgeschlossen. Maximal ein Nav2-Kindziel war aktiv;
`max_frontier_goals=1` im Test beweist, dass der A-Quellenstopp das
Navigationsbudget nicht verbraucht. Ohne neue gültige Quelle erfolgt kein
zweiter Versand und das Elternzeitbudget beendet den Auftrag kontrolliert.
Der bestehende Sechs-Szenarien-Gesamtprozessprüfer bestand sowohl aus der
Quelle als auch gegen das installierte Overlay; 893 Explorer-Pytests bestanden
ebenfalls. Ein erster Install-Gesamtlauf hatte einen einmaligen Timeout im
älteren Wiederaufnahmefall, der isoliert und im vollständigen Wiederholungslauf
bestand. Die Ursache dieser Test-Zeitstreuung ist offen. Alle Prüfungen liefen
ohne Gerätezugriff, Motorfreigabe oder Fahrbefehl.

**Keine Fahrfreigabe:** Das ist kein realer Sensor-, Nav2- oder
Hindernis-Recovery-Test. Der linke VL53-Nahbereichsbefund aus R9 bleibt
ungeklärt. Vor einer neuen Fahrt sind Sichtprüfung oder unbestromtes
Zurücksetzen auf eine vermessene freie Pose, erreichbarer hardwired Not-Aus,
vollständiger neuer Preflight und eine neue ausdrückliche Freigabe nötig.
Weder Scope noch Collision-, Footprint-, Frische- oder Sensorgrenzen wurden
gelockert. Stufe 3 wurde nicht begonnen.

**Rückfall:** Frische Shell öffnen und das Stufe-2-Präfix nicht sourcen.
Stufe 1 bleibt unverändert; keine Geräte- oder Installationsdatei muss
zurückkopiert werden. Den älteren Explorer wegen der dokumentierten
Wiedervergabe eines erreichten Frontierziels nicht als Fahrkandidaten nutzen.

---

## WE-1 Stufe 1: reproduzierbarer motorloser Zielstand (23.09.2026)

**Geprüfter Runtime-Code:**
`5e3fe0a084b9b46809e25715d8bdca4c7bd408a4` aus PR #96 auf dem
Stufe-1-Themenbranch `fix/we1-stufe1-runtimeinventur`; dessen Dokumentation
steht als PR #97 zur Review. Der neue isolierte
Merge-Install liegt unter
`~/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923/install`.
Weder `/home/p/roboter_ws/install` noch die dortige schmutzige Arbeitskopie
wurden verändert oder als gleichwertig behauptet.

Die geprüfte Shell-Reihenfolge ist:

```bash
source /opt/ros/humble/setup.bash
source /home/p/amadeus_slam_toolbox_ws/install/setup.bash
source ~/.local/share/amadeus/releases/we1-ldlidar-shutdown-overlay/install/local_setup.bash
source ~/.local/share/amadeus/releases/we1-10e1858074e7-r1/install/local_setup.bash
source ~/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923/install/local_setup.bash
```

Danach lösen `amadeus_lidar_bringup`, `base_hardware`, `explore`,
`mission_manager`, `robot_bringup`, `robot_map_manager`, `robot_navigation`,
`safety_monitor`, `semantic_map_manager` und `vl53_near_field` aus dem neuen
Stufe-1-Präfix auf. Das sind genau alle unter `src/` seit dem Vollrelease
`10e1858` geänderten Pakete. Unveränderte Projektabhängigkeiten kommen aus dem
commitgebundenen Vollrelease; der LiDAR-Treiber kommt aus dem gepatchten
Close-after-join-Overlay, `slam_toolbox` aus seinem vorhandenen gepatchten
Arbeitspräfix. Das alte `we1-r8-scope-overlay` nicht für Stufe 1 sourcen: Es ist
ein historischer Mischstand und enthält insbesondere kein neu gebautes
`robot_navigation`.

Das verwendete lokale Profil ist
`~/.local/share/amadeus/profiles/we1-two-rooms-hall-r9-20260922.yaml`, SHA-256
`e03495cebfc22dc7d9858cb8893660b83134cf4b6121db64ee49673d0688083f`.
Seine reale Geometrie bleibt lokal. Die beiden Abnahmezyklen wurden mit
`active_drive:=false`, Domain 217 und der Loopback-CycloneDDS-Konfiguration des
Vollreleases gestartet. Keine Missions- oder Navigationsaction wurde gesendet.

Beide Zyklen bestätigten aktive Nav2- und Collision-Lifecycles, vollständige
TF-Ketten, etwa 10 Hz LiDAR, 1 Hz frische Rohkarte, je etwa 4 Hz für beide
VL53, frischen Kartenmanager- und Explorerstatus sowie Safety `false`.
`base_hardware` meldete durchgehend `dry_run=true`, `allow_rs485=false`,
`rs485_ready=false` und null Motorwerte. In den Beobachtungsfenstern gab es
null Nav2-Ziele und null nichtnullige Fahrbefehle. Beide Einzel-SIGINT-Stopps
beendeten alle Prozesse sauber; `/dev/amadeus_lidar`, `/dev/ttyUSB_BASE` und
die sichtbaren I²C-Gerätepfade blieben danach ohne Handle. Die Zykluslogs
enthalten keine Tracebacks oder Prozessabbrüche.

**Keine Fahrfreigabe:** Der frühere reale R9-Befund links vor der Endpose ist
durch diesen motorlosen Lauf weder widerlegt noch beseitigt. Vor jeder späteren
Bewegung sind Sichtprüfung oder unbestromtes Zurücksetzen auf eine vermessene
freie Pose, erreichbarer hardwired Not-Aus, kompletter neuer Preflight und eine
neue ausdrückliche Freigabe erforderlich. Sicherheits- und Frischegrenzen
bleiben unverändert. Nächster erlaubter Schritt ist nur Review des
Stufe-1-PRs; Stufe 2 wurde nicht gestartet.

**Rückfall:** Neue Shell öffnen und das Stufe-1-Präfix nicht sourcen. Es wurde
nichts in die Standardinstallation deployt, daher ist keine Roboterdatei
zurückzukopieren.

---

## WE-1: erster Realversuch sicher beendet, Scope-Fortsetzung gesperrt (21.09.2026)

Christopher bestätigte Not-Aus, freie Türen und zwei Zimmer plus Flur; Treppen,
Außenbereiche, Personen und Tiere waren ausgeschlossen. Der freigegebene Lauf
bewegte Amadeus etwa 0,466 m und endete ohne Safety-, Encoder- oder Busfehler,
aber nur mit einem Teilstand: Kartenrevisionen ersetzten fortlaufend den
Frontierkandidaten und lösten zwölf sichere Cancel/Replans aus. Es wurde kein
Portal überquert und kein natürlicher Mehrraumabschluss erreicht.

Der Explorer hält nun das gesendete Frontierziel fest und prüft genau dieses
Ziel auf jeder neuen Rohkarte erneut gegen Kartenidentität, Pose,
Hindernisabstand, Scope und Erreichbarkeit. Der motorlose Produktionslauf hielt
es von Revision 55 bis 119 aktuell; Basis blieb im Dry-run und alle
Fahrbefehle waren null. Diese Softwareevidenz ist noch keine fahrende Abnahme
der Korrektur.

Amadeus steht nach dem ersten Lauf nicht mehr an der ursprünglichen Startpose.
Ein aus der aufgezeichneten Endpose abgeleitetes lokales Profil lieferte im
motorlosen Exaktkartentest null sicher erreichbare Frontierziele innerhalb des
Scopes, obwohl sechs Ziele ohne Scope erreichbar wären. Beim zweiten aktiven
Vorlauf wurde deshalb kein Auftrag gesendet. Danach wurden alle Prozesse sauber
beendet; `/dev/ttyUSB_BASE` war frei. Der Fahrzustand war null, eine elektrische
Motorstromfreiheit wurde dabei nicht separat gemessen.

Vor dem nächsten Start ist genau eine der folgenden Vor-Ort-Aktionen nötig:

1. Roboter zur ursprünglichen markierten Startpose einschließlich Orientierung
   zurückstellen; oder
2. einen neuen zusammenhängenden Scope ab der aktuellen Pose vermessen und
   dessen Ausschluss von Treppen und Außenbereichen bestätigen.

Das Profil liegt ausschließlich unter
`~/.local/share/amadeus/profiles/we1-first-realtest-20260921.yaml`, der
vollständige Fahrbag unter
`~/.local/share/amadeus/bags/we1-real-full-20260921-2101`. Diese reale Geometrie
nicht committen. Bis zur Vor-Ort-Aktion keine weitere WE-Fahrt auslösen und den
Scope nicht aus bloßem Kartenfreiraum automatisch vergrößern. Der isolierte
Overlaystand ist nicht in die laufende Roboter-Arbeitskopie deployt.

---

## WE-1: motorloser Zielsystemcheck bestanden (21.09.2026)

**Geprüfter Stand:** PR #95, Commit
`10e1858074e738df739077aea27078d6bbef7156`, plus ausschließlich die
Footprint-Test- und Shutdownkorrekturen auf `fix/we1-target-check-blockers`.

Der WE-Releasekandidat wurde auf diesem Jetson ohne Motorfreigabe in getrennten
Installationspräfixen unter
`~/.local/share/amadeus/releases/we1-target-blockers-20260921` gebaut und
geprüft. Die
laufende, lokal geänderte Arbeitskopie `/home/p/roboter_ws` und ihr Install
wurden weder gewechselt noch ersetzt. Das LiDAR-Overlay baut den gepinnten
Vendor-Commit mit der engen seriellen Shutdownkorrektur; der Roboter-Workspace
verwendet weiterhin ein lokales BehaviorTree.CPP-Kompatibilitätspräfix für die
vorhandene ARM64-apt-Bibliothek. Rückfall: eine frische Shell verwenden und die
isolierten Overlays nicht sourcen.

Der gemeinsame Lauf mit LiDAR, beiden VL53, SLAM, Nav2, Explorer,
Kartenmanager, `collision_monitor` und Safety war unter Last stabil. Typische
Raten waren etwa 10 Hz LiDAR, je 4 Hz VL53, 1 Hz Karte, 50 Hz Odometrie und
100 Hz TF. Nav2 und `collision_monitor` waren aktiv, das Laufzeit-Footprint war
das vermessene Polygon über `/local_costmap/published_footprint`.
`base_hardware` lief ausschließlich mit `dry_run=true`; `/dev/ttyUSB_BASE`
blieb frei, Drehzahlen und Geschwindigkeiten blieben null.

Der veraltete VL53-Test prüft nun ausschließlich den bereits real abgenommenen
Polygonvertrag; Produktionskonfiguration und Footprint-Architektur blieben
unverändert. Der gepinnte LiDAR-Treiber schließt seinen seriellen Deskriptor
erst nach dem Empfangsthread-Join. VL53 und Basis behandeln einen bereits durch
SIGINT beendeten rclpy-Kontext idempotent; Fahrtor und Kartenmanager lassen
echte RuntimeErrors weiter sichtbar und ignorieren nur den Humble-
`take_message`-Fehler bei bereits beendetem Kontext.

Der vollständige Build umfasste 23 Pakete. Direkt bestanden 1.206 Tests und
registriert 1.016 Tests, jeweils ohne Fehler, Fehlschlag oder Skip. Der
Produktionsprozessprüfer bestand positiv, Fehlerpfad, Mehrraum-Rückkehr und
Speichern/Neustart/Fortsetzung mit natürlichem Abschluss und jeweils null
Fahrbefehlen.

Der echte Kartenmanager-Save unter `we1_target_recheck_20260921` sowie der
daran gebundene WE-Save bestanden ohne Durability-Warnung. Während 30 Sekunden
gemeinsamer Last entstanden null Nav2-Ziele und null Nichtnull-Befehle. Zwei
aufeinanderfolgende vollständige SIGINT-Stopps endeten danach ohne Traceback
oder Prozessabbruch; LiDAR, beide VL53, Basis und Kartenmanager wurden sauber
freigegeben. `/dev/ttyUSB_BASE`, `/dev/amadeus_lidar` und `/dev/i2c-9` waren
frei.

**MOTORLOSER WE-1-ZIELSYSTEMCHECK: BESTANDEN.** Das lokale Profil
`~/.local/share/amadeus/profiles/we1-first-realtest-20260921.yaml` ist auf
Startraum, bekannte offene Tür und einen begrenzten ersten Flurabschnitt
zugeschnitten. Reale Wohnungsgeometrie und Zustände bleiben ausschließlich
lokal. WE-Navigation, Scope-Freigabe und Portalmonitor stehen weiter auf
`false`, bis Christopher den Ausschluss von Treppen, Außenbereichen und anderen
Gefahren vor Ort bestätigt und ausdrücklich die Fahrt freigibt.

Es wurde kein Deployment vorgenommen. Keine Hardware- oder Fahrfreigabe aus
diesem Abschnitt ableiten; die nächste Aktion ist ausschließlich Christophers
Scope- und Fahrbestätigung bei erreichbarem Not-Aus.

---

## OAK-RGB-D-Transport dauerstabil und selbstheilend (26.08.2026)

**Branch:** `codex/fix-oak-semantic-stream`

Die OAK-Konfiguration liefert nun tatsaechlich 640 x 360 bei 10 Hz
(ISP-Faktor 1/3). `oak.launch.py` startet standardmaessig zwei lokale,
motorunabhaengige Prozesse:

- `oak_rectifier` publiziert `/oak/rgb/image_rect` fuer RTAB-Map ohne
  Exact-Sync zwischen Bild und der stabilen CameraInfo;
- `semantic_stream_relay` publiziert nur 2 Hz JPEG-RGB, verlustfreies
  16UC1-PNG und CameraInfo unter `/oak/semantic/...`.

Der KI-Server muss `compressed_input: true` und ausschliesslich diese drei
Semantiktopics verwenden. Direkte Serverabonnements von
`/oak/rgb/image_raw`, `/oak/rgb/image_rect` oder `/oak/stereo/image_raw` sind
nicht zulaessig. Status:

```bash
ros2 topic echo /oak/rgb/rectifier_status_json --once
ros2 topic echo /oak/semantic/stream_status_json --once
```

`ready` muss wahr sein, Bildformen muessen 640 x 360 zeigen und
`codec_errors`, `stale_rgb`, `stale_depth` muessen null bleiben. Ein Wert in
`subscription_restarts` dokumentiert einen automatisch geheilten lokalen
DDS-Endpunktstillstand und darf nicht verschwiegen werden.

Motorlose Abnahme im isolierten Overlay: OAK 33 min 49 s ohne spaeten USB-
oder Geraetefehler; Relay 17 min 31 s mit 2.068 Paaren und null Codec-/
Altersfehlern; 24 Semantik- und 7 Bring-up-Tests bestanden. Je ein gezielter
2,5-s-Ausfall von Tiefe und RGB wurde durch genau einen Endpoint-Neuaufbau
geheilt. Nach leerem RTX-Objektgedaechtnis lieferte die sichtbare Tasse eine
echte positive 3D-Pose mit Konfidenz 0,694. Keine Motor-, Nav2-, VL53- oder
Missionskomponente lief.

**Produktionsdeployment:** Commit `a2d8ccc` ist auf dem Jetson als normal
kopiertes, nicht vom temporaeren Worktree abhaengiges Colcon-Install aktiv.
Ersetzt wurden ausschliesslich `install/robot_bringup` und
`install/semantic_perception`. Der vorherige vollstaendige Paketstand liegt
lokal unter
`~/.local/share/amadeus/deploy-backups/oak-stream-a2d8ccc-predeploy/`.
Die schmutzige Haupt-Arbeitskopie wurde nicht veraendert.

Auf dem KI-Server wurde derselbe Commit normal unter Python 3.12 gebaut; dort
bestanden 24/24 Tests. Die externe Produktions-YAML nutzt jetzt nur die
komprimierten Semantiktopics. Ihr Vorgänger liegt als
`~/.config/amadeus-server/semantic_perception.yaml.pre-a2d8ccc-20260826` vor.
`amadeus-ki.service` ist aktiv und startet genau einen `llm_planner` sowie
einen `semantic_perception` aus dem Produktions-Install.

Der anschliessende Produktionsstart aus `/home/p/roboter_ws/install` meldete
nach 190 Paaren weiterhin `ready=true`, 0,052 s Publikationsalter, null stale
Frames und null Codecfehler. Der Entzerrer meldete 957/957 Bilder, null Drops
und 640 x 360. Genau ein RTX-Subscriber hing am komprimierten RGB-Topic. Eine
Tassenabfrage blieb ohne laufende Kartenlokalisierung korrekt fail-closed im
`map`-Frame. Aktiv blieben nur OAK, Entzerrer, Relay und beide KI-Server-Nodes;
Motoren, Nav2, VL53 und Missionsausfuehrung waren aus.

Rueckfall: OAK und KI-Dienst stoppen, auf dem Jetson die beiden gesicherten
Paketverzeichnisse zurueckkopieren und auf dem Server die gesicherte YAML
wiederherstellen; alternativ `semantic_relay:=false` oder Commit revertieren.

---

## OAK-Objektpose mit deutschem Servicevertrag — motorlos bestanden (25.08.2026)

**Branch:** `fix/semantic-object-prompts`

Die externe Klasse bleibt deutsch. `GetObjectPose(Tasse)` und spaeter die App
muessen nicht auf englische Begriffe umgestellt werden. Intern setzt
YOLO-World einmalig das validierte Vokabular `cup`, `bottle`,
`remote control`, `tool`, `key`. Eine unvollstaendige, leere oder doppelte
Zuordnung verhindert den Node-Start statt eine falsche Klasse zu liefern.

Die A/B-Messung auf demselben lokalen OAK-Bild ergab fuer die sichtbare Tasse
`cup=0,396`, aber fuer `Tasse=0,029` mit falscher Box. Mit dem Fix erkannte der
Server die Tasse fortlaufend und erreichte ihre gueltige Tiefe. Ohne
Lokalisierung endete die Verarbeitung korrekt am fehlenden `map`-TF. Ein
kurzzeitiger, kuenstlicher Identitaets-TF pruefte ausschliesslich die restliche
3D-Kette und lieferte `found=true`, Konfidenz 0,4048 und
`(1,621; -0,308; 0,555) m` im Testframe. Dabei liefen nur OAK, Bildanzeige,
KI-Server und der Test-TF; keine Motor-, Nav2- oder Missionsknoten. Der TF
wurde danach entfernt und der KI-Dienst neu gestartet. Die Testpose ist nicht
mehr im Gedaechtnis; ohne echten Karten-TF antwortet der Service wieder
`found=false`.

Auf Jetson/Python 3.10 und KI-Server/Python 3.12 bestehen je neun direkte
Tests, Python-Kompilierung und normaler Colcon-Build. Auf dem KI-Server keinen
`--symlink-install`-Wechsel verwenden: Die dortige Setuptools-Version lehnt
die dazu verwendeten Optionen ab. Der normale, isolierte Colcon-Install ist
der bestaetigte Deploymentpfad.

Die Live-Abnahme nutzte 640 x 360. Das bisherige 320-x-180-Nav2-Profil war
fuer Sichtkontrolle und kleine Gegenstaende unnoetig knapp; eine dauerhafte
1920-x-1080-Uebertragung ist aber noch nicht freigegeben. Hochaufloesendes RGB
und ausgerichtete Tiefe erzeugen roh eine hohe WLAN- und GPU-Last. Ein
separates Semantikprofil soll deshalb komprimierte oder bedarfsgesteuerte
Schluesselbilder messen, ohne das schlanke Navigationsprofil zu veraendern.

Wichtig fuer diesen Folgeschritt: Auch der 640-x-360-Lauf war noch kein
Dauertest. Nach 17 min 18 s meldete der Treiber erstmals `No Data` und danach
etwa alle fuenf Sekunden erneut. Am Fehlerbeginn gab es keinen Kernel-USB-
Reset oder Disconnect. Beim Beenden hing der Komponentencontainer ueber
SIGINT und SIGTERM hinaus und wurde erst durch die normale Launch-Eskalation
per SIGKILL beendet; der USB-Disconnect folgte erst dabei. Die Ursache darf
nicht geraten werden. Vor 1080p deshalb mindestens drei motorlose A/B-Laeufe:
Kamera nur lokal, Kamera plus Offboard-Subscriber ohne Inferenz und Kamera plus
Inferenz. Je Lauf Bildrate, Datenluecken, DDS-Transport, Serverlatenz und
Shutdown protokollieren. Erst danach Transport/Kompression oder Aufloesung
festlegen.

Rueckfall: Prompt-Commit revertieren, `semantic_perception` normal neu bauen
und den KI-Dienst neu starten. Ohne reale Lokalisierung keinen statischen
`map -> base_link` stehen lassen; ein solcher TF war nur fuer diesen
motorlosen Projektionstest zulaessig.

---

## Mehrraum-Uebergang — sensorisch und extern bestaetigt (18.08.2026)

**Branch:** `fix/polygon-footprint-wohnung`

Der Explorer besitzt jetzt neben normaler Frontier-Navigation eine
fail-closed Portalbehandlung fuer den real gemessenen Sonderfall, dass Nav2
eine offene Tuer wegen Inflation in zwei freie Costmap-Komponenten trennt.
Normale erreichbare Frontiers bleiben vorrangig. Eine direkte Portalbruecke
ist nur nach frischer vollbreiter LiDAR-Korridorpruefung zulaessig und wird
ueber eingefrorene LiDAR-Geometrie statt ausschliesslich ueber Radencoder
beendet. Wenn neue Scans beide Komponenten waehrend der Anfahrt verbinden,
wechselt der Explorer nun zur regulaeren Nav2-Fahrt hinter die Tuer, statt
faelschlich `portal_geometry_changed` zu melden.

Gemessener Ablauf der Realabnahme:

- erster scharfer Lauf: Portal 0,887 m2, Luecke 0,488 m, Anfahrt 0,454 m;
- nach 0,347 m Anfahrt verschmolzen beide Gebiete zu einer regulaer
  befahrbaren 2,251-m2-Costmap-Komponente; alter Zielpunkt weiterhin Kosten 90;
- nach dem Softwarefix plante Nav2 aus der neuen Startlage ein normales Ziel
  bei `(1,05, 0,05) m` deutlich hinter der Tuer;
- Nav2 meldete Erfolg, Explorer meldete `frontiers_visited=1`;
- Endwerte: Encoderpose `x=1,018 m`, `y=-0,102 m`, `yaw=0,398 rad`, beide
  Motoren 0 rpm, RS485 und Encoder ohne Fehler;
- die Live-Karte wuchs in Fahrtrichtung und die Fahrspurabdeckung erreichte
  23,70 % der aktuellen sicheren Komponente.

Der terminale Missionsstatus dieses begrenzten Laufs war danach absichtlich
`failed`: Ein nur temporaer fuer die Abnahme gesetzter +/-20-Grad-Kegel
verwarf drei seitliche Folgefrontiers. Er kam erst nach dem erfolgreich
erreichten 1,05-m-Ziel zum Tragen und ist kein Tuerfahrfehler. Das normale
Wohnungsprofil bleibt richtungsfrei (`frontier_forward_cone_half_angle_rad:
0.0`). Die temporaere Begrenzung ist nicht Teil des installierten
Produktionsprofils.

Softwareabnahme: Explorer 58/58; gesamter registrierter Bestand 165 Tests,
0 Fehler, 0 Fehlschlaege, 0 Auslassungen. Vor der Fahrt liefen LiDAR mit
10,8 Hz und beide VL53 mit 3,8 Hz; Motoren standen bei 0 rpm. Nach der Fahrt
wurde der gesamte Stack mit genau einem Ctrl-C am Launch-Elternprozess beendet.
Es laufen derzeit keine fuer diese Abnahme absichtlich gestarteten
Amadeus-Knoten. Der anwesende Beobachter bestaetigte nach dem Stillstand, dass
der Roboter die Schwelle vollstaendig verlassen und den Folgeraum real erreicht
hatte. Die aeussere Sichtpruefung stimmt damit mit Sensorik und Nav2 ueberein.

**Naechster Schritt:** Kein weiterer Schwellen-Sondertest. Mit neuer
persoenlicher Fahrfreigabe das normale, richtungsfreie Wohnungsprofil starten
und aus dem Folgeraum mehrere Frontiers bedienen lassen. Erst dieser Lauf
prueft weitere Tueren und den globalen Abschlussvertrag. Echte Karten, Fotos
und ROS-Bags bleiben lokal.

Rueckfall: `portal_crossing_enabled: false` deaktiviert die Portalbruecke,
ohne normale Frontier-Navigation zu entfernen. Vollstaendig motorlos bleibt
`active_drive:=false`.

---

## Polygon-Footprint fuer Tuerdurchgaenge — motorlos verifiziert (18.08.2026)

**Branch:** `fix/polygon-footprint-wohnung`

Der reale lokale Nav2-Footprint ist jetzt die sichere Rechteckhuelle mit den
Rohpunkten `x=-0.11..+0.31 m`, `y=+/-0.23 m` relativ zur mittigen
Antriebsachse und `footprint_padding: 0.02`. Zur Laufzeit werden daraus
`x=-0.13..+0.33 m`, `y=+/-0.25 m`. Das Chassis selbst wurde am 18.08.2026 mit
270 mm vor, 110 mm hinter der Achse und maximal 460 mm Breite gemessen. Die
bekannte VL53-Montage verlaengert die sichere Kontur vorne auf 310 mm. Der
Kartierungs-`collision_monitor` abonniert dieses Polygon auf
`/local_costmap/published_footprint`, sodass lokaler Regler und reaktive
Approach-Pruefung dieselbe Kontur verwenden.

NavFn bleibt vorerst aktiv und plant global mit `robot_radius: 0.28`; die
Explorer-Ziel- und Abdeckungsrechnung verwendet dazu eine kreisfoermige
0,28-m-Maske.
Das ist absichtlich kein Smac-Umbau. Die Entscheidung und der gestufte
Wohnungsplan stehen in `docs/WOHNUNGSERKUNDUNG_STRATEGIE.md`.

Motorlos bestaetigt:

- 33 gezielte Footprint-/Explorer-Tests bestanden;
- registrierter Paketlauf: Explorer 19/19, Navigation 31/31 und Bring-up 3/3,
  insgesamt 53 Tests ohne Fehler/Fehlschlaege/uebersprungene Tests;
- `robot_description`, `explore`, `robot_navigation`, `vl53_near_field`
  gebaut und Xacro validiert;
- vermessener Nav2-Livefootprint exakt `x=-0,13..+0,33 m`, `y=+/-0,25 m`;
- `collision_mapping_approach` identisch im `base_link`-Frame;
- globaler Radius und beide Explorer-Abstaende live jeweils 0,28 m;
- realer NavFn-Stack plante auf einer temporaeren 3-cm-Synthetikkarte einen
  geraden 1,50-m-Pfad durch eine 0,69-m-Tuer (`SUCCEEDED`, ca. 0,7 ms);
- `dry_run=true`, `allow_rs485=false`, 0 rpm;
- nach dem Test keine Amadeus-Knoten aktiv.

Die schmalste Tuer ist mit 680 mm gemessen. Gegenueber der 500 mm breiten,
gepaddingten lokalen Kontur bleiben 90 mm je Seite bei exakt mittiger Fahrt;
das globale 560-mm-Modell laesst 60 mm je Seite. Laufzeit- und NavFn-Tuertest
sind motorlos abgeschlossen. Als naechstes folgt ein einzelner beaufsichtigter
Tuerdurchgang, nicht sofort eine volle Wohnungserkundung. Arm/Greifer muessen
in Transportpose sein. Hard-Not-Aus, freie Tuer und neue persoenliche
Fahrfreigabe bleiben Pflicht.

Begrenztes Profil fuer diese Einzelabnahme:

```bash
cd /home/p/roboter_ws
AMADEUS_FAHRFREIGABE=JA bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=true enable_auto_explore:=true start_web_gui:=false \
  explore_params_overlay:=/home/p/roboter_ws/install/explore/share/explore/config/door_test_params.yaml
```

Der Befehl ist **keine dauerhafte Fahrfreigabe** und darf erst nach neuer
persoenlicher Zustimmung ausgefuehrt werden. Das Profil laesst den Rundblick
und die sichere Vorausrichtung zu, aber hoechstens ein Frontier-Nav2-Ziel,
einen Fehlversuch, keine Coverage-Fahrt und maximal 300 s. Vor dem
Explore-Kommando muessen `max_frontier_goals=1`, `coverage_enabled=false`,
der Polygon-Footprint, beide VL53-Punktwolken und 0 rpm bestaetigt sein.

Ein motorloser Profilstart zeigte einmal einen transienten Fehler beim rechten
VL53 (`VL53L5CXException: 0`). Der sofortige isolierte Wiederholungstest war
erfolgreich; beide Seiten publizierten stabil rund 3,98 Hz. Bei Wiederholung
bleibt die Mission gesperrt und der Sensorstart wird nicht uebergangen.

### Erster begrenzter Realtest und TF-Korrektur (18.08.2026)

Der erste Motorstart blieb vor jedem Auftrag stehen, weil beide Regler bei
aktivem Motor-Halt nicht auf Modbus antworteten. Nach physischem Entriegeln
wurde RS485 vollstaendig bestaetigt. Ein transient fehlgeschlagener linker
VL53-Start wurde nicht uebergangen; der isolierte Neustart lieferte auf beiden
Seiten 3,78 Hz mit maximal 0,44 s Datenluecke bei 0,8 s Fahrtorgrenze.

Der scharfe Ein-Ziel-Lauf absolvierte den Rundblick mit 360,0 Grad und die
Frontier-Vorausrichtung mit 3,0 Grad Kartenrestfehler. Genau ein Nav2-Ziel wurde
angenommen. Es war mit 30,6 Grad zur Startfront jedoch bereits das falsche,
seitliche Ziel und fuehrte nicht zur Tuer; das bestaetigten Beobachter und Log.
Die bisherige `heading_scale` war nur eine weiche Praeferenz. Nach rund 0,28 m
Fahrt brach Nav2 zusaetzlich ab, obwohl Planer, Footprint, Encoder, RS485 und
VL53 fehlerfrei waren. Im Controllerlog steht diese zweite Ursache:
`map->odom` war unter Jetson-Last mindestens 0,95 s alt;
`controller_server.failure_tolerance` betrug nur 0,5 s. Das begrenzte Profil
endete korrekt nach dem ersten Fehlversuch, 0 rpm wurde bestaetigt und alle
Knoten wurden beendet. Dieser Lauf ist **noch kein bestandener Tuerdurchgang**.

Die installierte reale Nav2-Konfiguration verwendet jetzt
`failure_tolerance: 1.5`. `velocity_smoother.velocity_timeout` bleibt 0,5 s,
damit fehlende Reglerausgaben weiterhin frueher ein Nullkommando erzeugen.
Direkt bestanden 15 Vertragspruefungen; der registrierte Paketlauf bestand
31/31 Navigationstests. Ein anschliessender Dry-run bestaetigte live 1,5 s,
0,5 s, `dry_run=true` und 0 rpm. Vor einer Wiederholung Roboter erneut vor der
Tuer ausrichten, beide VL53 pruefen und eine neue persoenliche Fahrfreigabe
einholen.

Das begrenzte Tuerprofil akzeptiert nun zusaetzlich nur Frontier-Anfahrpunkte
innerhalb von +/-20 Grad zur aktuellen Front. Ein Ziel ausserhalb dieses
Korridors kann nicht mehr durch Groesse oder Naehe gewinnen. Fehlt ein sicherer
Kandidat vor der Front, bricht die Mission vor Vorausrichtung und Translation
mit einer eindeutigen Meldung ab. Die normale Wohnungserkundung bleibt mit
Kegelwert null unveraendert. 20/20 Explorer-Tests bestanden. Im installierten
Dry-run waren der Wert `0.3490658503988659`, ein Ziel/ein Fehlversuch,
deaktivierte Coverage, 300 s, `allow_rs485=false`, 0 rpm, beide VL53 mit rund
3,5--3,9 Hz und `/scan_normiert` mit rund 10 Hz aktiv. Danach liefen keine
Amadeus-Knoten mehr.

Rueckfall: lokales/globales `robot_radius: 0.40`, Mapping-Approach-Kreis
`radius: 0.40`, Explorer `coverage_clearance_m: 0.40`, oder ohne Bewegung
`active_drive:=false`. Die TF-Aenderung kann separat mit
`controller_server.failure_tolerance: 0.5` zurueckgenommen werden; nur der
Tuerkegel mit `frontier_forward_cone_half_angle_rad: 0.0`.

---

## Adaptive App-Raumkartierung — real abgenommen (17.08.2026)

**Branch:** `feature/hybrid-erkundung-app`

Die Erkundung hat jetzt drei Phasen:

1. odometrisch kontrollierter 360-Grad-LiDAR-Rundblick;
2. Frontier-Ziele fuer noch unbekannte Kartengrenzen;
3. adaptive Abdeckungsziele in der sicher befahrbaren bekannten Flaeche.

Phase 3 verwendet die gemessene Fahrspur. Standardabschluss sind 85 % der
zusammenhaengenden, radial um 0,28 m von Wand und unbekanntem Raum freigehaltenen
Flaeche innerhalb eines 0,65-m-Korridors um diese Spur. Maximal 14
Abdeckungsziele, 150 s pro Nav2-Ziel und 1200 s Gesamtzeit begrenzen den Lauf.
Eine SLAM-Korrektur ueber 0,35 m wird nicht als gefahrene Verbindung gezaehlt.
Unterhalb des Zielwerts melden Zeitlimit oder fehlendes sicheres Ziel einen
Fehler; die App zeigt dann nicht „Karte kann gespeichert werden".

Erfolgreich bediente Frontier-Anfahrbereiche werden innerhalb 0,60 m fuer den
Rest des Laufs gesperrt. Das verhindert die real beobachtete Folge sofortiger
Nav2-Erfolge ohne Bewegung. Ein zusaetzliches Limit von 20 Frontier-Zielen
bricht eine unerwartete Wiederholung fail-closed ab.

Fuer App, Kartierung und Raumeditor gibt es jetzt genau einen gemeinsamen
Startpfad. Motorlos:

```bash
cd ~/roboter_ws
bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=false enable_auto_explore:=true
```

Beaufsichtigter Realstart, erst nach freiem Raum, erreichtem Hard-Not-Aus und
neuer ausdruecklicher Fahrfreigabe:

```bash
cd ~/roboter_ws
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_app_erkundung.sh \
  active_drive:=true enable_auto_explore:=true
```

Der Launch sendet keinen Auftrag. Sobald die iOS- oder Web-App mit Port 9090
verbunden ist, wird **Erkundung starten** nur bei frischem Missions-,
Not-Aus- und Explorerstatus aktiv. `/explore/status_json` aktualisiert Phase
und reale Abdeckung mit 1 Hz. Erst `map_ready_to_save:true` bestaetigt den
Abschluss der Abdeckungsstrategie; die Karte danach weiterhin visuell
pruefen und bewusst speichern.

Der Starter bricht ab, wenn Einzelstarts von `robot_map_manager`,
`semantic_map_manager`, rosbridge, Missionsmanager oder Explorer noch laufen.
Diese Terminals zuerst sauber mit Strg-C beenden; niemals den neuen
Gesamtlaunch parallel zu `robot.launch.py`, `smartphone_gui.launch.py` oder
`nav_mapping.launch.py` starten. Der Check ist erforderlich, weil passive
Kartenmanager vom allgemeinen Stillstandshelfer absichtlich erlaubt werden.

Motorlos auf dem Jetson bestaetigt: je ein Besitzer aller zentralen Knoten,
`dry_run=True`, 0 rpm, Explorer-Heartbeat, echter rosbridge-Empfang und der
vollstaendige App-Pfad `explore -> running -> cancel -> canceled`.
`map_ready_to_save` blieb beim Abbruch korrekt falsch.

Reale Abnahme am 17.08.2026: Der erste 900-s-Akkulauf erreichte 82,72 % und
lief nur in das Gesamtzeitlimit. Ein Folgelauf deckte danach eine
Frontier-Wiederholung auf und wurde sicher abgebrochen. Mit der 0,60-m-Sperre
fuhr Amadeus den 360-Grad-Rundblick und fuenf verschiedene Frontier-Ziele in
732 s. Die adaptive Zielwahl wechselte bei neu entdeckten Grenzen korrekt
zurueck in die Frontier-Phase. Abschluss: 88,30 % von 5,0706 m2 sicher
erreichbarer Flaeche, 4,4775 m2 abgedeckt, keine Frontiers offen,
`map_ready_to_save=true`, Mission erfolgreich und danach 0 rpm. Beide VL53
und der Kollisionsmonitor waren aktiv. Die lokale Sichtkontrolle zeigte eine
zusammenhaengende 3-cm-Karte ohne offensichtliche Doppelwaende; sie wurde
nicht ins Repository uebernommen.

Rueckfall: `enable_auto_explore:=false`, `active_drive:=false` oder den neuen
App-Launch nicht verwenden. `coverage_enabled:false` in
`explore_params.yaml` stellt das alte Frontier-Ende wieder her.

---

## Automatische LiDAR-Raumkartierung — real abgenommen (16.08.2026)

**Branch:** `feature/automatische-lidar-kartierung`

Der neue Ablauf besitzt zwei klar getrennte Phasen. Zuerst dreht Amadeus mit
0,12 rad/s einmal vollstaendig auf der Stelle. Der erreichte Winkel wird aus
der Encoder-Odometrie ueber den +-Pi-Uebergang akkumuliert; ein Zeitlimit,
Mindestfortschritt, Drehrichtung und der anschliessende Stillstand werden
aktiv ueberwacht. Erst danach wertet der Explorer die neue 3-cm-SLAM-Karte aus
und faehrt sichere Punkte im bekannten Freiraum vor den Grenzen zu noch
unbekannten Bereichen an. Nach jedem Ziel wird neu geplant, bis keine
ausreichend grosse sicher erreichbare Frontier mehr vorhanden oder das
zehnminuetige Gesamtlimit erreicht ist. Nach bereits erzieltem Fortschritt
gilt der erste Fall als `safe_complete`, nicht als Fahrfehler.

Der komplette Ablauf ist motorlos und real getestet. Der Dry-run erreichte
360,4 Grad, bestaetigte den Stopp, fand drei sichere Frontier-Kandidaten und
uebergab genau ein Ziel an Nav2. Der anschliessende Cancel sperrte das Fahrtor,
stornierte das Nav2-Kindziel und endete bei Nullkommando.

Im beaufsichtigten Realtest drehte Amadeus 360,2 Grad, erreichte vier sichere,
jeweils neu geplante Frontier-Ziele und beendete danach wegen der einzigen
verbliebenen, nicht sicher anfahrbaren Frontier. Ein kurz veralteter
`map->odom`-Transform wurde fail-closed gestoppt und ohne Recovery-Bewegung
begrenzt neu versucht. Die Abschlusskarte war zusammenhaengend und frei von
doppelten Waenden oder getrennten Teilkarten (195 x 221 Zellen bei 3 cm,
5,85 x 6,63 m, 16,1 m2 freie Flaeche). Diese reale Karte bleibt lokal.

Voraussetzung fuer das korrekte Verhalten ist das verifizierte LiDAR-Paar
`laser_scan_dir: true` und `tf_yaw: +1.5708`. Vorher liefen Odometrie
(-96,9 Grad) und Kartenwinkel gegeneinander; danach stimmten sie in einem
echten Teilturn mit +99,10 und +98,10 Grad ueberein. Richtung und TF nie
einzeln aendern.

Der sichere Start ist absichtlich nicht automatisch:

```bash
cd ~/roboter_ws
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_automatische_kartierung.sh \
  active_drive:=true enable_auto_explore:=true
```

Erst nach Live-Pruefung von 0 rpm, LiDAR, beiden VL53, Odometrie, SLAM-Karte,
Kollisionsmonitor und freiem Dreh-/Fahrbereich darf genau ein Explore-Auftrag
gesendet werden. Der erste echte Rundblick ist gleichzeitig ein A/B-Test fuer
die Basis: Nach 15 Sekunden muessen im Mittel mindestens 0,01 rad/s erreicht
sein. Zusaetzlich gelten acht Sekunden ohne 0,03 rad Fortschritt, falsche
Drehrichtung, veraltete Odometrie oder 210 Sekunden Gesamtzeit als sicherer
Abbruch. Die niedrige Rate beruecksichtigt die reale 2-s-Motorrampe und die
30-Prozent-SlowZone des Kollisionsmonitors.

Abbruch eines laufenden Auftrags:

```bash
ros2 topic pub --once /mission_manager/command_json std_msgs/msg/String \
  "{data: '{\"type\":\"cancel\"}'}"
```

Danach Nullkommando und 0 rpm bestaetigen und nur den Launch-Prozess einmal
mit Strg-C beenden. Keine Prozessgruppe signalisieren. Die reale Karte erst
nach Sichtkontrolle ueber den Kartenmanager speichern; Wohnungsdaten bleiben
lokal. Rueckfall: `enable_auto_explore:=false` oder `active_drive:=false`.
Ein flaches Stromkabel kann unterhalb der Sensor-Sicht liegen; auch bei
`left=false`, `right=false`, `middle=false` ersetzt das keine Sichtkontrolle.

---

## A* und Zielfahrt mit aktivem VL53-Schutz (16.08.2026)

**Branch:** `fix/nav2-astar-vl53-zieltest`

Der reale Navfn-Planer verwendet jetzt `use_astar: true`. Die Entscheidung ist
gemessen: Dijkstra brach auf der realen 3-cm-Karte trotz zusammenhaengender
begehbarer Zellen ab; A* plante denselben Weg bei unveraendert aktiven linken
und rechten VL53-Obstacle-Layern sofort. Ein Vertragstest verriegelt A*,
`allow_unknown:false` und den erwarteten Navfn-Plugin-Typ.

Der anschliessende beaufsichtigte Realtest bestand. Beide VL53-Datenstroeme,
`collision_monitor`, Lokalisierungs-Gate, Encoder und RS485 waren bereit. Der
Kollisionsmonitor war der einzige `/cmd_vel`-Publisher zur Hardware. Die
Mission `go_to_room Arbeitszimmer` endete mit `success/angekommen`, maximal
0,100 m/s; danach Soll/Ist und beide Motoren 0 rpm, Encoder frisch, keine
Modbus-Lesefehler. Der scharfe Stack ist anschliessend beendet worden.

OAK war bewusst aus: Ihre Live-Punktwolke markierte im A/B-Test den freien
Zielbereich als praktisch unpassierbar und trennte die Costmap. Bis der
Hoehen-/Bodenfilter korrigiert und motorlos abgenommen ist, gilt als
Hinderniskette: zwei VL53 in beiden Costmaps plus zwei VL53 im
`collision_monitor`. Ein absichtlicher Hindernis-Bremstest steht noch aus.

Naechster Meilenstein ist automatische LiDAR-Kartierung. Den vorhandenen
`explore`-Knoten nicht ungeprueft real starten: Er war bislang nicht unter ROS
abgenommen; das alte Python-Erkundungsskript publiziert teilweise direkt und
ist fuer die reale Kollisionskette nicht freigegeben. Erst SLAM, Nav2,
Fahrtor, VL53 und Explorer motorlos als eine fail-closed Kette testen.

---

## Aktueller Abnahmestand: selbst lokalisieren und Raumziel erreichen (16.08.2026)

**Branch:** `feature/globale-lokalisierung`

Der aktuelle Stand erreicht das eigentliche Meilensteinziel: Amadeus startet
ohne gespeicherte oder manuell gesetzte Pose, bestimmt seine Position und
Blickrichtung stationaer aus der gespeicherten LiDAR-Karte und erreicht danach
ein karten- und revisionsgebundenes semantisches Raumziel.

Der Kaltstart verwendet nicht mehr AMCLs nativen Globaldienst. Dieser Dienst
war auf Humble bereits erreichbar, bevor AMCL zwingend eine interne Karte
hatte, und verursachte real einen Segmentation Fault (`exit code -11`). Der
Guard startet stattdessen einen kartenfesten Vollscan-Zyklus. Erst zwei
unabhaengige Treffer innerhalb 0,20 m/8 Grad duerfen `/initialpose` setzen;
AMCL muss die Pose danach bestaetigen. Karte/Basis/LiDAR, AMCL und Guard werden
in 0-/4-/7-Sekunden-Stufen gestartet, weil ein gleichzeitiger Vollstart auf
dem Jetson ausserdem einen Fast-DDS-Lifecycle-Timeout erzeugt hatte.

Reale Abnahme am 16.08.2026:

- drei motorlose Kaltstarts an derselben extern bestaetigten Pose bestanden;
- maximale Streuung 3 cm/1 Grad, zwei konsistente Scans je Start;
- Score `0,9787..0,9789`, Wandtreffer `97,36..97,50 %`, Bestenabstand
  `1,155..1,168`;
- aktiver Start erneut eindeutig: Score `0,980`, 97,22 % Wandtreffer,
  Bestenabstand 1,180; AMCL-Standardabweichung bei Freigabe
  0,140/0,138 m und 4,70 Grad;
- Nav2-Pfad vorab read-only planbar, anschliessende reale Mission
  `go_to_room Arbeitszimmer` erfolgreich;
- Karten-Endfehler 0,133 m/6,28 Grad, damit innerhalb 0,15 m/0,40 rad;
- Encoderweg 1,024 m, Fahrbefehl hoechstens 0,100 m/s;
- terminal `success/angekommen`, danach wiederholt 0 rpm und keine
  Encoder-/Modbusfehler.

Vor dem aktiven Lauf waren RS485, beide Encoder, Motorstillstand, AMCL,
Lokalisierungs-Gate, beide VL53-Datenstroeme und `collision_monitor` korrekt.
VL53 und beide Costmap-Obstacle-Layer wurden auf ausdruecklichen Wunsch nur
fuer diese beaufsichtigte Fahrt zur Laufzeit deaktiviert; OAK war aus. Im
Repository bleibt die Hinderniskette aktiv. Nach der Abnahme wurden
Missions-, Nav2-, AMCL-, LiDAR- und Motorstack beendet. Karten, Raumgeometrie
und Diagnosen liegen weiterhin nur unter `~/.local/share/amadeus/`.

Fuer den naechsten Vorfuehrstart gilt weiterhin: zuerst freie Flaeche und
Not-Aus bestaetigen, motorlos lokalisieren, `/localization/ready=true` und
0 rpm pruefen, erst danach `active_drive:=true` und genau einen frischen
Missionsmanager mit `enable_real_go_to_room:=true` starten. Mehrdeutiger Scan,
falsche Kartenbindung oder fehlendes AMCL sperren fail-closed. Rueckfall:
`enable_real_go_to_room:=false` und den Lokalisierungs-/Real-Launch nicht
starten.

---

## Zwischenstand globaler Vollscan-Gate (16.08.2026)

**Branch:** `feature/globale-lokalisierung`

AMCL hatte eine rund 1,95 m falsche Pose trotz kleiner Kovarianz als
konvergiert gemeldet. Deshalb ist der alte Vertrag ersetzt: Vor der ersten
Freigabe muss jetzt `global_scan_localizer` einen stationaeren Vollscan
eindeutig gegen die Karte abgleichen. Der Treffer ist kryptographisch an den
Kartenfingerabdruck und ueber eine neue zufaellige 128-Bit-ID an genau einen
AMCL-Global-Reset gebunden. Veraltete Statusmeldungen koennen keinen spaeteren
Start freigeben. Danach muss AMCL den Treffer innerhalb 0,30 m/12 Grad
bestaetigen; erst dann prueft der Guard wie bisher Kovarianz und stabiles
`map -> odom`.

Live-A/B am unveraenderten Standort:

- falsches AMCL: `(0,704; 0,379; -123,6 Grad)`, nur 39,6 % Scanpunkte binnen
  15 cm zur Kartenwand, Median 0,190 m;
- globaler Vollscan: bei drei Kaltstarts `x=1,245..1,305 m`, `y=-1,135 m`,
  `yaw=38..39 Grad`, Score `0,970..0,973`, Wandtreffer `97,2..98,75 %`,
  Bestenabstand `1,245..1,267`;
- finale AMCL-Pose `(1,237; -1,147; 39,4 Grad)`, unabhaengig 98,27 % binnen
  15 cm, Median 0,030 m, 90-%-Quantil 0,060 m;
- alle Laeufe motorlos mit `dry_run=true` und 0 rpm.

Normale globale Lokalisierung benoetigt damit keine Drehung und keine
Vorwaertsfahrt mehr. Start weiterhin nur ueber
`tools/kartierung/start_lidar_lokalisierung.sh`; der Matcher setzt
`/initialpose` selbst. Seine Mindestgrenzen sind Score 0,85,
Wandtrefferquote 0,85 und Bestenabstand 1,15. Ein schlechter oder
mehrdeutiger Treffer sperrt fail-closed. Diagnose:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/setup.bash
python3 tools/kartierung/globale_scan_pose.py
python3 tools/kartierung/scan_karten_abgleich.py
ros2 topic echo --full-length /localization/status_json --once
```

22 Pakettests und der Colcon-Build bestehen. Echte Karten und alle Bilder
liegen nur unter `~/.local/share/amadeus/`. Noch offen sind die persoenliche
Bestaetigung der Blickrichtung, zwei weitere deutlich getrennte motorlose
Startpositionen und danach eine beaufsichtigte reale Zielfahrt. Aus diesem
motorlosen Ergebnis folgt noch keine Fahrfreigabe. Der alte
`amcl_lokalisierungsdrehung.py` bleibt nur als Diagnosewerkzeug und ist nicht
mehr der Normalstart.

---

## Übergabestand globale Lokalisierung (15.08.2026)

**Branch:** `feature/globale-lokalisierung`

Der Roboter wurde nach dem letzten Test manuell verschoben. Das war bei
beendeten Motor-/Navigations-Stacks sicher, macht aber jede vorherige globale
Pose ungueltig. Vor der naechsten autonomen Fahrt ist deshalb eine neue
Lokalisierung erforderlich; aus diesem Dokument folgt keine Fahrfreigabe.

### Implementierter Vertrag

- `nav_localized.launch.py` startet die lokale gespeicherte Karte, den
  normalisierten STL-27L-Scan, AMCL, den `localization_guard` und den realen
  Nav2-Pfad mit genau einem dynamischen `map -> odom`-Eigentuemer.
- Der Kartenpfad ist Pflicht. Metrische und semantische Karte muessen denselben
  SHA-256-Fingerabdruck besitzen; echte Karten und Raumdaten bleiben lokal.
- Der Starthelfer prueft PGM und YAML vor ROS. Er bricht ab, wenn
  `free_thresh` die von `map_saver` als 205 geschriebenen unbekannten Zellen
  verschlucken wuerde.
- `/localization/ready` wird erstmalig nur bei hoechstens 0,20 m
  Standardabweichung in x/y, 10 Grad in yaw und hoechstens 0,08 m/5 Grad
  Bewegung von `map -> odom` im Drei-Sekunden-Fenster wahr.
- Nach Freigabe halten getrennte Hysteresen bis 0,30 m/15 Grad Kovarianz und
  0,20 m/12 Grad TF-Bewegung. Die TF-Haltegrenzen stammen aus 640 realen
  Proben mit gemessenen Maxima 0,1601 m/8,32 Grad.
- Das `cmd_vel`-Gate stoppt bei jedem Verlust der Freigabe sofort. Der
  Mission Manager verwirft eine bereits laufende Raumfahrt erst nach 0,8 s
  ununterbrochenem Verlust. Die erste Zielannahme bleibt strikt fail-closed.
- Der Lokalisierungsstatus zeigt die aktuelle TF-Fensterbewegung, die aktive
  Acquire-/Maintain-Grenze und die Gruende eines Sperruebergangs. Der
  Missionsstatus zeigt Verlustalter und Abbruchnachfrist.

### Reale Evidenz und Grenze

Die Ursache der zuvor nicht wiederholbaren Suche wurde nachtraeglich in der
Kartendatei gefunden: Das PGM enthielt 20.543 freie, 3.561 belegte und 29.320
unbekannte Zellen, doch `free_thresh: 0.25` lud alle unbekannten Zellen als
frei. Der so gespeicherte Live-Grid hatte 44,88 m² freie Flaeche statt 18,49
m² und keine unbekannte Region; AMCL suchte damit ausserhalb des realen
Zimmers. Eine lokale, geometrisch identische Version mit
`free_thresh: 0.196` erhaelt die unbekannten Zellen und ist unter dem
Fingerabdruck `528a0b020fe89624da1c55925421aecba948a13f6f27f84087725d0ad79c701f`
gespeichert. Das Overlay `Arbeitszimmer` ist lokal explizit daran gebunden.

Nach freiem Versetzen konvergierte AMCL nach einer vollstaendigen Drehung
einmal auf 0,118/0,135 m und 8,65 Grad Standardabweichung. Die folgende
`go_to_room`-Fahrt erreichte einen Punkt rund 0,03 m vor dem semantischen Ziel.
Eine 0,59-s-TF-Korrektur blieb ohne Missionsverlust; eine spaetere
2,20-s-Instabilitaet brach die Mission korrekt ab und der Motorstillstand
wurde bestaetigt.

Die reine Suchbewegung hinterliess weiterhin mehrere Winkelhypothesen. Der
entscheidende, motorlose Schritt waren standardisierte stationaere
`/request_nomotion_update`-Messungen nach dem Stop: 20 Updates reduzierten die
Streuung auf 0,095/0,118 m und 7,83 Grad und setzten `/localization/ready=true`.
Der Helfer `amcl_lokalisierungsdrehung.py` fuehrt diese Nachmessung nun selbst
aus; die 10-Grad-Grenze bleibt unveraendert. Der reale Nachweis erfolgte nach
einem Stack-Neustart am zuvor um 0,243 m veraenderten Standort mit 180,2 Grad
Drehung. Die nun zusammengefuehrte Ein-Aufruf-Variante muss beim naechsten
versetzten Start noch wiederholt werden.

Der anschliessende reale End-to-End-Test ist bestanden. Die erste Raumfahrt
wurde bei 15,69 Grad Winkelunsicherheit fail-closed abgebrochen und alle
Motorwerte gingen auf null. Nach 20 weiteren stationaeren Messungen
(0,019/0,077 m, 4,50 Grad) erreichte der erneut gesendete Auftrag das
Arbeitszimmer. Missionstatus: `success`, Phase `angekommen`; Abschluss:
0,051/0,078 m, 6,08 Grad und 0 rpm. Der TF-Endpunkt lag rund 0,148 m und
21,7 Grad vom semantischen Ziel entfernt, innerhalb der Nav2-Toleranzen
0,15 m/0,40 rad. Mehrere unabhaengige versetzte Starts fehlen noch fuer eine
statistische Wiederholbarkeitsaussage; ein kompletter versetzter Lauf ist
jedoch real belegt.

### Zustand und naechster Start

- Die Motor-/Nav2-/AMCL-/Missions-Stacks wurden nach dem bestandenen Test beendet; der
  Roboter darf aus einer alten Pose nicht autonom gestartet werden.
- VL53-Zonen und Costmap-Obstacle-Layer waren nur waehrend der beaufsichtigten
  Testlaeufe zur Laufzeit deaktiviert. Keine dauerhafte Abschaltung wurde
  eingecheckt.
- Echte Karte, semantische Daten, Bags und Diagnoserenderings bleiben lokal.
- Vor einem neuen Realtest: freie Fahrbahn und Not-Aus neu bestaetigen,
  motorlosen Preflight ausfuehren, Kartenfingerabdruck pruefen, global neu
  lokalisieren und erst bei `/localization/ready:true` ein Ziel zulassen.
- Rueckfall: `enable_real_go_to_room:=false` verwenden und den
  Lokalisierungs-/Real-Launch nicht starten.

### Abnahmeplan naechste Sitzung: mehrere Startpositionen

Ziel ist nicht ein weiterer Einzel-Erfolg, sondern eine vergleichbare
Wiederholbarkeitsmessung ohne manuell gesetzte Startpose. Drei deutlich
getrennte Startpositionen mit unterschiedlichen Anfangsrichtungen verwenden.
Vor jedem Lauf den vorherigen Launch vollstaendig beenden, den Roboter nur im
Stillstand manuell versetzen und danach denselben korrigierten
Kartenfingerabdruck pruefen.

Je Startposition wird protokolliert:

1. Startbezeichnung und ungefaehre Anfangsrichtung, aber keine Wohnungsgeometrie
   oder Kartendaten im Repository;
2. Ergebnis des motorlosen Preflights und 0-rpm-Nachweis;
3. Ergebnis des zusammengefuehrten Suchlaufs mit `--degrees 360` und
   `--forward-meters 0.25`, Anzahl stationaerer AMCL-Updates und Zeit bis
   `/localization/ready=true`;
4. x-/y-/yaw-Standardabweichung bei Freigabe und Kartenfingerabdruck;
5. terminaler Status von `go_to_room Arbeitszimmer`, eventuelle
   fail-closed-Abbrueche und Zahl notwendiger Neuauftraege;
6. TF-Abstand und Winkelfehler zum Ziel sowie Motor-/Istgeschwindigkeit nach
   dem terminalen Status.

Die Wiederholbarkeitsabnahme besteht, wenn alle drei Starts ohne manuelle
Posevorgabe lokalisieren, alle drei Raumziele innerhalb 0,15 m/0,40 rad
erreichen und nach jedem terminalen Status 0 rpm anliegt. Fuer eine
vorfuehrfertige Ein-Klick-Kette darf kein manueller Stack-Neustart oder
Neuauftrag erforderlich sein. Ein Sicherheitsabbruch ist als korrektes
Fail-closed-Verhalten zu dokumentieren, zaehlt aber nicht als bestandener
Vorführlauf.

Der Vorwaertsteil darf nur an einer Startposition mit mindestens 0,40 m
freier Bahn ausgefuehrt werden. Hardware-/Encoderfehler, falscher
Kartenfingerabdruck, fehlender LiDAR oder eine nicht schliessende Fahrtor-Kette
beenden den jeweiligen Versuch. Eine beaufsichtigte VL53-Deaktivierung bleibt
rein laufzeitbezogen und darf nicht in die persistente Konfiguration gelangen.
ROS-Bags, Karten und Raumgeometrie bleiben lokal; ins Repository kommen nur
aggregierte Messwerte und die Entscheidung bestanden/nicht bestanden.

---

## Abnahmestand reale semantische Raumfahrt (15.08.2026)

**Branch:** `feature/reale-raumfahrt`

Dieser Abschnitt ersetzt fuer neuere Stände die Aussage vom 14.08.,
`go_to_room` sei immer simuliert. Der sichere Standard ist weiterhin
Simulation; nur `enable_real_go_to_room:=true` aktiviert den getrennten
Nav2-Pfad.

### Real bestandener Vertrag

- Ein Karten- und Revisions-gebundenes semantisches Raumziel wird als
  `NavigateToPose` gesendet.
- Der verpflichtende Behavior Tree enthält keine Recovery-Manöver: kein
  automatisches Rueckwaertsfahren und kein selbststaendiges Drehen nach einem
  Fehler.
- Nav2 publiziert auf `/cmd_vel_nav_raw`. Das fail-closed
  `cmd_vel_mission_gate` gibt nur eine frische, laufende `go_to_room`-Mission
  auf `/cmd_vel_nav` frei.
- Der `velocity_smoother` arbeitet `OPEN_LOOP`; danach folgt der
  `collision_monitor`, erst dann `/cmd_vel` und `base_hardware`.
- Der Nav2-Unterzieltimeout ist 2000 ms. Die reale Unterzielannahme benoetigte
  in einem Messlauf rund 590 ms; der alte 20-ms-Wert konnte einen Fehler
  melden, bevor das Unterziel angenommen war.
- Der Fortschrittspruefer ist auf 0,10 m in 20 s gesetzt. Die alte Schwelle
  0,30 m/15 s war mit der bestaetigten 2000-ms-Hardware-Rampe unvereinbar und
  brach freie Fahrt nach rund 0,19 m ab.

Der abschliessende beaufsichtigte Bodenlauf erreichte sein Ziel nach 1,084 m
Encoderweg. Der lange Geradeausabschnitt blieb innerhalb 0,14 Grad, das finale
Einlenken innerhalb 3,28 Grad. Alle vier Stufen der Befehlskette blieben bei
maximal 0,100 m/s und 0,149 rad/s. Nach Erfolg wurden Gate, reale
Istgeschwindigkeit und beide Motoren bei null bestaetigt; es blieb kein
verwaister Nav2-Rohbefehl. Beide VL53-Datenstroeme waren frisch, Encoder und
Modbus fehlerfrei.

### Pruefung vor jeder weiteren Realfahrt

1. Roboterpose nicht aus Kartenkoordinaten raten. Der bislang abgenommene Lauf
   verwendete einen bewusst gesetzten statischen `map -> odom`-Startbezug.
2. Freie Raeder/Fahrbahn und Not-Aus bestaetigen; keine Freigabe aus diesem
   Dokument ableiten.
3. Beide VL53-Punktwolken, aktiven `collision_monitor`, frische Odometrie,
   initialisierte Encoder, RS485-Bereitschaft und 0 rpm pruefen.
4. Laufzeitparameter pruefen: `OPEN_LOOP`, 2000-ms-Nav2-Timeout und
   Fortschrittspruefer 0,10 m/20 s.
5. Während des Laufs Mission, Gate-Ausgang, Encoder-/Modbusstatus und echten
   Motorstillstand auch nach einem Terminalstatus weiter beobachten.

### Offene Grenzen und Rückfall

Die allgemeine Selbstlokalisierung nach freiem Versetzen oder Neustart ist
noch nicht abgenommen. Bis dahin ist reale Raumfahrt nur vom kontrollierten
Startbezug aus zulaessig. Der Recovery-freie Baum bricht absichtlich ab, statt
ein Hindernis autonom zu umfahren. H5 der Encoder-Odometrie und ein echter
VL53-Hindernis-Abbruch in dieser Kette bleiben offen.

Rückfall: `enable_real_go_to_room:=false` verwenden oder weglassen und den
Real-Launch nicht starten. Dann bleibt die semantische Zielaufloesung
read-only/simuliert. Karten- und Raumdaten bleiben lokal ausserhalb des
Repositories.

---

## Auftrag: manuelle semantische Räume in der Amadeus-App (14.08.2026)

**Branch:** `feature/semantic-map-editor`

**Vollständiger Vertrag:** `docs/SEMANTIC_MAP_INTEGRATION.md`

Der neue `semantic_map_manager` ist passiv: Er liest den Status des
`robot_map_manager`, speichert Raum-Polygone außerhalb des Repositories und
publiziert Metadaten. Er besitzt weder Nav2-Action noch `cmd_vel`-Publisher.
Auch `mission_manager` bereitet `go_to_room` ausschließlich als Simulation vor.
Diese Übertragung ist daher **keine Fahrfreigabe**.

### Auf Entwicklungs-Mac und Jetson geprüft

- 51 Semantik-Backend-, 38 Mission-, 15 LLM-Planer-, 51 Kartenmanager-,
  2 Bring-up- und 5 rosbridge-Mocktests: **162/162 Python-Tests bestanden**;
- 39/39 Swift-Tests und vollständiger iOS-Simulator-Build bestanden;
- Python-Kompilierung, Mypy, Flake8 `F/E9`, YAML/XML, Packaging und
  Whitespaceprüfung bestanden;
- der identische Python-Testbestand sowie der Colcon-Build der sechs Pakete
  bestanden am 14.08.2026 auf dem realen Jetson;
- physisches iPhone: signierter Build, Installation, zwei rosbridge-Sockets,
  bewusstes Kartenspeichern, Raum-Upsert auf Revision 1 und App-Neustart
  bestanden;
- Semantikmanager-Neustart stellte Revision 1 identisch wieder her;
  kontrolliertes SIGINT endet nach der gefundenen Shutdown-Korrektur sauber;
- mehr als sechs Sekunden ohne Kartenmanager sperrten den Status mit
  `ok:false`/`editable:false`; der Wiederanlauf derselben Karte stellte
  Revision 1 und den Raum `Test` ohne Datenverlust wieder her;
- ein Update mit `base_revision:0` gegen Revision 1 wurde live abgelehnt und
  ließ `current.json` unverändert;
- `go_to_room` für `Test` ergab live ausschließlich
  `simulation_only_no_navigation`; `/cmd_vel` existierte davor und danach
  nicht;
- während der gesamten Abnahme existierten weder Motor-/Nav2-Knoten noch das
  Topic `/cmd_vel`.

Die Abnahme verwendete ausschließlich die statische `testwohnung`. Eine neue
reale Wohnungskarte und jede Fahrwirkung bleiben eigene spätere Prüfungen.

### Sichere Übernahmereihenfolge

1. Arbeitskopie und Branch prüfen; unbekannte lokale Änderungen nicht
   überschreiben. Den Branch erst übernehmen, nachdem er in das Remote
   veröffentlicht wurde.
2. `AGENTS.md`, dieses Dokument und `docs/SEMANTIC_MAP_INTEGRATION.md` lesen.
3. Ohne aktive Motor-/Navigationsknoten bauen und die Offline-Verträge prüfen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select \
  robot_map_manager semantic_map_manager mission_manager llm_planner \
  semantic_perception robot_bringup
source install/setup.bash

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/semantic_map_manager \
  python3 -m unittest discover -s src/semantic_map_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/mission_manager \
  python3 -m unittest discover -s src/mission_manager/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/llm_planner \
  python3 -m unittest discover -s src/llm_planner/test -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/robot_map_manager \
  python3 -m unittest discover -s src/robot_map_manager/test -v
python3 -m unittest discover -s src/robot_bringup/test -v
python3 -m unittest discover -s ios/Robotersteuerung/Tools \
  -p 'test_mock_rosbridge.py' -v
```

4. Für den ersten ROS-Vertragstest nur die beiden passiven Manager starten;
   dafür sind keine Motoren und keine Fahrt nötig:

```bash
ros2 launch robot_map_manager map_manager.launch.py
ros2 launch semantic_map_manager semantic_map_manager.launch.py
ros2 topic echo /robot_map_manager/status_json
ros2 topic echo /semantic_map/status_json
ros2 topic echo /semantic/catalog_json
```

5. Erst wenn eine echte `/map` sichtbar ist, in der App bewusst **Karte für
   Räume speichern** wählen. Die Erstbindung ist nur nach einem bestätigten
   `save_result` mit identischem SHA-256-Fingerabdruck möglich. Danach einen
   kleinen Test-Raum zeichnen, Zielpunkt strikt innerhalb setzen, speichern,
   App neu verbinden und Persistenz/Revision prüfen.
6. Prüfen, dass die Daten ausschließlich hier liegen und nicht für Git
   vorgemerkt sind:

```text
~/.local/share/amadeus/semantic_maps/<fingerprint>/current.json
~/.local/share/amadeus/semantic_maps/<fingerprint>/revisions/
```

7. Negativtests ohne Fahrt: falsche `base_revision`, Kartenwechsel und mehr als
   sechs Sekunden ausbleibender Kartenmanagerstatus müssen `editable:false`
   ergeben. `go_to_room` darf nur `simulation_only_no_navigation` melden und
   weder Nav2 noch `cmd_vel` auslösen. Ein Replay derselben `request_id` muss
   dabei Karte, Speicher, Pose, Zeit und Zähler aus dem **aktuellen** Zustand
   zeigen und darf keinen historischen Vollstatus zurückspielen.
   Zusätzlich muss der Mission-Cache nach sechs Sekunden ohne neuen
   Semantikstatus verfallen. Ein manuell angelegter Raum, ein Objekt oder ein
   Ablageziel aus einer Topic-Nachricht darf die statischen realen
   `pick_and_place`-Allowlists nicht erweitern.
8. Persistenzgrenzen sichtbar prüfen: 2.048 Revisionen/Karte, 1 GiB
   Repository und 512 MiB Freispeicherreserve sind die defensiven Defaults.
   Eine erreichte Grenze muss die neue Revision ablehnen und die letzte
   gültige Revision unverändert lesbar lassen; nichts automatisch löschen.

### Rückfallweg

- `start_semantic_map_manager:=false` lässt das Paket im Gesamt-Bring-up aus.
- `use_dynamic_catalog:=false` in Missions- und LLM-Konfiguration nutzt wieder
  ausschließlich die statischen Listen.
- Das Verzeichnis `~/.local/share/amadeus/semantic_maps/` vor einer manuellen
  Änderung sichern; der Code löscht keine Revision automatisch.
- Reale Raumfahrt bleibt gesperrt, bis VL53-/Collision-Monitor, Lokalisierung,
  Costmap-Freiraum, Planbarkeit und Abbruchpfade separat abgenommen sind.

## Abnahmestand Encoder-Odometrie (13.08.2026)

**Branch:** `fix/encoder-position-odometry` · **H0 bis H4 bestanden**

- [x] **H0** keine Knoten aktiv, `/dev/ttyUSB_BASE` frei, Worktree sauber
- [x] **H1** beide Motoren stabil per FC03 (~5 ms); `0x0011=1000`, `0x0019=0`,
      `0x0101=4000` beidseitig identisch; Position im Stillstand bitgenau
      konstant über 40 Proben
- [x] **H2** `encoder_counts_per_motor_revolution = 1000`, unabhängig gemessen:
      vorwärts 1000,8/1000,9 und rückwärts 1000,2/1000,3; Richtungsunterschied
      unter 0,07 %; vom Nutzer in beiden Richtungen mit genau 5 Radumdrehungen
      bestätigt. Gegenrechnung über die Motordrehzahl: 999,4–999,5
- [x] **H3** aufgebockt: geradeaus 0,2442 m bei 0,01° Gierwinkel, Drehung auf
      der Stelle 93,33° bei 0,0001 m Translation; null Fehler, `/odom` 16,7 Hz,
      Watchdog greift
- [x] **H4** Bodenfahrt gegen das **Lasermessgerät**: je Fahrt **+0,5 mm**
      statt +17,3 bis +20,1 mm. Zusatzfehler dreier weiterer Start-Stopp-
      Vorgänge von **+51,9 auf +3,9 mm** gesunken (−92 %). Skalenfehler
      +0,23 %, Kursabweichung +0,04° bis +0,27°
- [ ] **H5** Fehler- und Wiederanlaufpfade — offen
- [ ] `odom_*_variance` aus wiederholten Fahrten kalibrieren — offen

### Was dabei zusätzlich gefunden wurde

**Die Anfahrrampe war bis 14.08.2026 nie wirksam.** Der Antrieb weist
`accel_ms: 2500` mit
`ExceptionResponse(function_code=134, exception_code=7)` zurück; die Obergrenze
beider Rampenregister liegt bei **2000**. Ausgelesen stand in `0x001E` auf
beiden Motoren **100**. Sichtbar wurde das erst, weil dieser Branch die
Rückgabewerte der Schreibvorgänge prüft — der alte Code verschluckte den
Fehlschlag.

Die getrennte Änderung ist inzwischen real bestanden: Eingetragen sind jetzt
**2000 ms Beschleunigen**, unverändert 400 ms Bremsen und 5 rpm
Startgeschwindigkeit. Beide Antriebe bestätigten alle drei Werte. Ein
1,0-s-Bodenimpuls mit 0,12 m/s ergab 0,0439 m Encoderweg und 0,000°
Kursänderung; der Nutzer bewertete das Anfahren als „gut sanft“. Die frühere
Annahme, die Rampenzeit werde proportional zu 3000 rpm verkürzt, ist damit
widerlegt. Die anschließende manuelle LiDAR-Runde zeigte keine Verschlechterung
der Wanddicke (37,0 % vorher, 36,7 % nachher). Die offene Zimmertür macht
Fläche und Kartenausdehnung zwischen den beiden Läufen nicht vergleichbar.

**Der Nahbereichsschutz ist funktionslos.** `vl53_near_field` stirbt mit
„Kein CH341/CH34x-I2C-Bus gefunden"; der Adapter `1a86:5512` steckt, das
Kernelmodul `ch34x` fehlt. Der `collision_monitor` aktiviert sich trotzdem und
reicht ohne Sensordaten alles durch. **Vor autonomem Fahren zwingend beheben.**

**Der LiDAR-Wandvergleich taugt nicht als Kalibrierreferenz.** Bei einer Fahrt
lag er 21,5 mm neben dem Laser, bei eigener Streuung von 1,7 mm.

### Fahren mit Nahbereichsschutz

`collision_monitor` hängt als `cmd_vel_smoothed` → `cmd_vel` dazwischen. Wer
direkt auf `/cmd_vel` publiziert, umgeht ihn. Messwerkzeuge nehmen dafür
`--cmd-topic /cmd_vel_smoothed`.

---

## Auftrag: Encoderpositions-Odometrie

**Branch:** `fix/encoder-position-odometry`
**Vollständige Anleitung:** `docs/ENCODER_ODOMETRIE_FIX.md`

Dieser Branch baut auf `agent/slam-toolbox-pure-rotation-fix` auf und enthält
damit den bereits geprüften Humble-Backport und den Scan-Vereinheitlicher. Für
diesen Auftrag später **nicht** auf den Basisbranch zurückschalten.

### Branch auf dem Jetson übernehmen

```bash
cd ~/roboter_ws
git status --short --branch
git fetch origin
git switch fix/encoder-position-odometry 2>/dev/null || \
  git switch --track -c fix/encoder-position-odometry \
  origin/fix/encoder-position-odometry
git pull --ff-only
```

Bei lokalen Änderungen, einem unerwarteten Commit oder einem nicht schnellen
Vorwärtsschritt stoppen und den Zustand klären. Keine unbekannten Jetson-Dateien
überschreiben.

Der Softwarefix ist offline geprüft, aber absichtlich noch nicht fahrbereit:
`encoder_counts_per_motor_revolution: 0.0` blockiert den echten Start. Auf dem
Jetson zuerst alle Roboterknoten beenden und ausschließlich read-only messen:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
python3 tools/kartierung/encoder_position_pruefen.py --confirm-stack-stopped
```

Danach die markierte Motor- oder Radumdrehung gemäß Hilfe des Werkzeugs messen,
Wortfolge, Vorzeichen, `0x0011` und `0x0101` protokollieren und erst den
bestätigten Counts-Wert eintragen. Nach H2 müssen alle drei Schutzwerte gesetzt
sein:

```yaml
encoder_counts_per_motor_revolution: <bestätigter Wert>
encoder_expected_segment: <beidseitig bestätigter Wert aus 0x0011, > 0>
encoder_expected_resolution: <beidseitig bestätigter Wert aus 0x0101, > 0>
```

`0` bei einem dieser Werte ist ausschließlich der read-only
Inbetriebnahmezustand und verriegelt den realen `encoder_position`-Modus. Ein
neuer Modbus-Client liest `0x0011`/`0x0101` erneut und startet bewusst mit einer
neuen Baseline. Anschließend gelten H0 bis H5 aus der vollständigen Anleitung.
Keine Hardwarefreigabe aus diesem Dokument ableiten.

Im laufenden Encoderpositionsmodus behält eine einzelne normale FC03-Fehlprobe
Client und Baseline. An der Transportfehlerschwelle folgen bestmöglicher
Stopp, Busfehlerstatus, Reconnect und eine neue Baseline. Stale Rückmeldung
sperrt und stoppt immer, reconnectet aber nur bei zugrunde liegendem
Transportfehler;
Python-Ausnahmen beziehungsweise unbekannte Pymodbus-API-Fehler gehen sofort in
diesen Pfad. Ein Reconnect darf daher **nicht** als kurze Lücke mit nachzuholenden
Counts bewertet werden.

Ein semantisch ungültiges Encoderpaar oder eine abweichende Treiberkonfiguration
sperrt und stoppt dagegen sofort, ohne den bestehenden Client nutzlos neu zu
verbinden. Ein unplausibles Delta wird verworfen und im Tracker kontrolliert
rebased.

`/odom` wird nur zu einem neuen gültigen Encoderpaar publiziert, mit der
Zielperiode von 0,05 s ungefähr 20 Hz. `state_json` läuft unabhängig davon im
50-Hz-Node-Takt weiter.

Der Befehlsvertrag ist ebenfalls sicherheitsrelevant: `/cmd_vel` hat Queue-Tiefe
1, NaN/Inf werden verworfen und fordern Stopp an, und der Watchdog nutzt
monotone Echtzeit. `use_sim_time: true` ist bei scharfem RS485 verboten. Ein
Motorstart erfolgt nur, wenn nach Quantisierung mindestens ein tatsächlich
schreibbarer RPM-Wert ungleich null ist.

Die vier `odom_*_variance`-Werte sind konservative Startwerte und werden erst
in H4 aus wiederholten extern referenzierten Fahrten kalibriert.

Vor Build und Tests die gepinnten seriellen Abhängigkeiten installieren.
`requirements-modbus.txt` fixiert Pymodbus 3.14.0 und Pyserial 3.5:

```bash
python3 -m pip install -r src/base_hardware/requirements-modbus.txt
```

Lokal auf dem Entwicklungs-Mac bestanden 59 Base-Hardware- und 12
Werkzeugtests. Auf dem Jetson nach dem Checkout erneut ausführen und das dortige
Ergebnis getrennt protokollieren:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src/base_hardware \
  python3 -m unittest discover -s src/base_hardware/test -v
python3 -m unittest discover -s tools/kartierung \
  -p "test_encoder_position_pruefen.py" -v
```

Der CI-Workflow `.github/workflows/encoder-odometry-offline.yml` kompiliert und
prüft dieselben Python-Komponenten zusätzlich unter Ubuntu 22.04/Python 3.10.
Mac- und CI-Ergebnisse ersetzen weder den Jetson-Lauf noch die gestufte
Hardwareabnahme.

---

Der folgende Abschnitt ist nur historischer Kontext des bereits integrierten
Vorläufers. Er ist **keine zweite aktive Übergabe**. Die vollständige alte
Diagnose steht in `docs/SLAM_TOOLBOX_ROTATION_FIX.md`.

## Integrierter Vorläufer: Humble-Fix für reine Drehungen

**Historischer Basisbranch:** `agent/slam-toolbox-pure-rotation-fix`

**Basis:** `feature/stl27l-integration`, Commit `7010058`

**Ziel:** gepinntes `slam_toolbox`-Overlay unter
`~/amadeus_slam_toolbox_ws`; `/opt/ros/humble` bleibt unverändert.

### Voraussetzungen

- [ ] `AGENTS.md`, `docs/PROJECT_MEMORY.md` und
      `docs/SLAM_TOOLBOX_ROTATION_FIX.md` vollständig gelesen
- [ ] Jetson-Arbeitskopie `~/roboter_ws` sauber; unbekannte Änderungen geklärt
- [ ] kein RTAB-Map- oder alter `slam_toolbox`-Prozess aktiv
- [ ] keine Geheimnisse, echten Karten oder ROS-Bags für einen Commit vorgemerkt
- [ ] Motorstrom aus; keine Fahrfreigabe vorausgesetzt

### Einordnung im aktuellen Branch

Der aktuelle Encoderbranch enthält diesen Stand bereits. Nicht auf
`agent/slam-toolbox-pure-rotation-fix` zurückschalten. Das gepinnte Overlay darf
weiterhin nicht ungepinnt aktualisiert und `/opt/ros/humble` nicht verändert
werden.

### Source-Reihenfolge in jedem Testterminal

```bash
source /opt/ros/humble/setup.bash
source ~/amadeus_slam_toolbox_ws/install/setup.bash
source ~/amadeus_lidar_ws/install/local_setup.bash
source ~/roboter_ws/install/local_setup.bash
```

Kontrolle:

```bash
ros2 pkg prefix slam_toolbox
```

Muss auf `~/amadeus_slam_toolbox_ws/install/slam_toolbox` zeigen.

### Abnahmestatus

Stand 12.08.2026, abgenommen auf Commit `4fe5ee3`:

- [x] Patch-Preflight (`git apply --unidiff-zero --check`) bestanden
- [x] Overlay gebaut; `colcon test` liefert allerdings **0 Tests** und ist als
      Evidenz wertlos (Testblock im Upstream auskommentiert). Ersatz: Blob-Hashes,
      Release-Build und `strings`-Gegenprobe am Binärpaket
- [x] Paketpräfix und gepinnter Humble-Commit kontrolliert
- [x] Stillstand: `dry_run=true`, `allow_rs485=false`
- [x] Stillstand: neuer Parameter `true`, keine Knotenflut, `/scan` 9,99 Hz
- [x] Synthetischer Yaw-only-Regressionstest ergänzt:
      `tools/kartierung/test_reine_drehung_synthetisch.py`, A/B 37 gegen 0
- [x] ausdrückliche Fahrfreigabe der anwesenden Person erteilt
- [x] Not-Aus in Reichweite, Fläche frei, Beobachter anwesend
- [x] 360°: mehr als null neue Posegraph-Knoten (1 → 11), Karte sichtbar ergänzt
      (freie Fläche 10,8 → 23,2 m²)
- [x] **versetzt duplizierte Wände: Ursache gefunden und behoben.** Karto
      verwarf jeden Scan mit abweichender Strahlenzahl; der STL-27L schwankt
      über 19 Werte (2145–2176). Abhilfe ist der neue Knoten
      `scan_vereinheitlichen`. A/B bei identischem Ablauf: 31 → 0 verworfene
      Scans, 10 → 41 Knoten, Nebenachse 5,39 → 3,83 m bei real 3,80 m
- [x] 40 cm Translation: weiterhin Kartenupdate (20 neue Knoten), keine
      Doppelwände, Kursabweichung +0,18°
- [ ] langsame geschlossene Runde: **noch offen.** Es ist kein Joystick
      angeschlossen (`/dev/input/js*` fehlt) und weder `collision_monitor` noch
      Nav2 laufen in `slam_lidar.launch.py`. Eine Runde durch die Wohnung darf
      deshalb nicht ferngesteuert-blind gefahren werden — der LiDAR sieht
      Schwellen, Kabel und Tischplatten grundsätzlich nicht
- [x] Testergebnis mit Datum und Commit in `docs/PROJECT_MEMORY.md` ergänzt

Diese damalige Phase-4-Freigabe gilt nicht automatisch für die neue
Encoderänderung. Im aktuellen Branch sind zuerst H0 bis H3 aus
`docs/ENCODER_ODOMETRIE_FIX.md` abzuarbeiten; jede Bewegungsphase braucht eine
neue ausdrückliche Freigabe.

### Zwei Dinge, die beim Fahren beachtet werden müssen

**Vor jedem Versuch prüfen, dass nichts mehr läuft.** `kill -INT` auf die
`ros2 launch`-PID beendet den Elternprozess, die Knoten können weiterlaufen. Am
12.08.2026 liefen dadurch zeitweise **zwei vollständige Stapel gleichzeitig** —
zwei `map->odom`-Publisher und zwei scharfe `base_hardware`-Knoten auf demselben
RS485-Bus. Die betroffene Messung war Unsinn und wurde verworfen. Nach dem
Beenden immer nachsehen, die eigene PID dabei ausnehmen:

```bash
MY=$$
ps -eo pid=,cmd= | grep -E '[l]dlidar|[a]sync_slam_toolbox|[b]ase_hardware|[s]can_vereinheitlichen' \
  | awk -v my="$MY" '$1 != my'
```

**Korrektur vom 16.08.2026:** Die folgende Messung klaerte die
Betragsabweichung, nicht das Vorzeichen. Das Werkzeug spiegelte den
LiDAR-Zuwachs vor der Regression und verdeckte damit die falsche
Treiber-Handedness. Seit dem gekoppelten Paar `laser_scan_dir: true` und
`tf_yaw: +1.5708` stimmen Odometrie (+99,10 Grad) und Kartenwinkel
(+98,10 Grad) in einem echten Teilturn ueberein.

**Die Odometrie-Betragsabweichung liegt bei -1,45 Grad je Umdrehung.** Die früher
gemeldeten −6,3° bis −6,5° waren ein Artefakt von `odometrie_drehtest.py`.
Sauber gemessen mit `tools/kartierung/odometrie_winkel_messen.py` (283
Messpunkte je Richtung, R² = 0,997): Skalenfaktor 0,99628 gegen den und 0,99564
im Uhrzeigersinn — beide Richtungen stimmen überein, also ein echter
Skalenfehler. Kein Handlungsbedarf vor Phase 4.

**Der Radradius ist neu kalibriert:** `wheel_radius_m: 0.0624`,
`wheel_separation_m: 0.3845` (vorher 0.0612 / 0.3755), aus acht Fahrten mit dem
Lasermessgerät. Verifikationsfahrt über 2,00 m innerhalb der Ablesegenauigkeit
getroffen.

**Was dabei zu beachten ist, wenn jemand die Odometrie erneut vermisst:**

1. **Kurze und lange Fahrt kombinieren.** Fester Anfahrversatz und Skalenfehler
   sind nicht trennbar, solange alle Fahrten ähnlich lang sind. 0,30 m gegen
   2,50 m funktioniert; 0,4 bis 1,0 m reicht nicht und liefert je nach
   Auswertung Radien zwischen 0,0621 und 0,0631.
2. **Lasermessgerät, nicht den LiDAR-Wandvergleich.** Der LiDAR lag bei der
   Verifikationsfahrt 24 mm daneben, bei sonst ±5 mm Streuung.
3. **Eine Winkelmessung bestimmt nur r/W**, nie die Spurweite allein. Ein
   Streckenfehler bleibt darin unsichtbar.

**Historischer Befund:** Der feste Versatz war kein Radiusfehler. Die frühere
Vermutung eines verspätet einsetzenden Ist-Drehzahlwerts ist nicht belegt;
50-Hz-Polling widerlegte eine reine Unterabtastung. Der aktuelle Encoderbranch
adressiert den Softwarepfad mit absoluten Positionsdeltas. Ob der Versatz real
verschwindet, entscheidet erst die H4-A/B-Messung.

**Keine Aktoren aktivieren, bevor alle Stillstandsprüfungen oberhalb bestanden
sind.** Ein KI-Agent darf die Fahrfreigabe nicht selbst annehmen.

### Rollback

Launch einmal sauber mit `Ctrl-C` beenden. Dann eine frische Shell verwenden
und das Overlay nicht sourcen:

```bash
source /opt/ros/humble/setup.bash
source ~/roboter_ws/install/local_setup.bash
ros2 pkg prefix slam_toolbox
```

Das Präfix muss wieder `/opt/ros/humble` sein. Der Overlay-Ordner bleibt zur
Analyse erhalten; keine Datenlöschung ist erforderlich.
