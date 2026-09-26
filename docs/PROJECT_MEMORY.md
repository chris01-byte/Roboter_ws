# Projektgedächtnis

Fortlaufendes Protokoll getroffener Entscheidungen. Jeder Eintrag nennt die
**beobachtete Evidenz**, nicht nur die Entscheidung. Neue Einträge oben anfügen.

Format:

```text
Datum:
Entscheidung:
Grund / beobachtete Evidenz:
Betroffene Dateien und Hardware:
Teststatus:
Offene Risiken:
Rückfallweg:
```

---

## 2026-09-26 — HWT-Zielsystemvorlauf an realer FC03-Latenz gestoppt

**Entscheidung:** Nutzerfreigabe für motorlosen Vorlauf und kurze spätere
Bewegung liegt vor. Bewegung nicht gestartet: Die 50-ms-Grenze des echten
Encoderpaares wurde im vollständigen Stack wiederholt überschritten; Roh-
quellenwächter verriegelte korrekt. Nur tatsächliche Dauer beider FC03-Reads
und abgewiesener Paare diagnostisch ergänzen. Erprobten 45-s-Startaufschub
nach erneutem Fehlschlag zurücknehmen; keine Grenze oder Kalibrierung lockern.

**Evidenz:** Isolierter Reader 1.275 Paare, maximal 31,56 ms; mit HWT/LiDAR
1.015 Paare, maximal 33,89 ms. VL53-Start: 66,976 ms, davon rechter
Read 46,805 ms. Vollstack: erstes Paar einmal 102,890 ms; auch nach
45-s-Aufschub achtes Paar 53,823 ms, davon ein Read 39,240 ms.
Eine CPU-3-Bindung nur des Lesers half ebenfalls nicht: erstes Vollstack-Paar
77,245 ms (Einzelreads 48,993/27,977 ms), Schutz verriegelte. Affinität
anschließend vollständig zurückgenommen; keine Fahr- oder Grenzänderung.
HWT-Bias stabil (805 Samples), beide VL53 gesund, Karte/LiDAR/Safety/Nav2
im ersten Vorlauf frisch, aber FC03 verriegelt und TF anschließend alt.
Null Nichtnull-Fahrbefehle. Aktuelle Vor-Ort-Auskunft: Endstufen unabhängig
gesperrt, Controller lesbar, Hardware-Halt erreichbar. Keine Motoraktivierung.

**Risiko / Rückfall:** Ursache USB/Modbus vs. Scheduling noch unklar;
Startaufschub wirkte nicht. SIGINT nur an Launch-PID hinterließ wiederholt
5-s-SIGTERM-Eskalationen; einmal Nav2-Controller Code -6 beim frühen
Abbruch. Alle Prozesse/Handles danach geschlossen, aber kein sauberer
Shutdown-Nachweis. Aktiven Install nicht umstellen, keine reale Fahrt.
Isolierten PR-#101-Kandidaten gestoppt lassen. Weitere Messwerte und
erforderlicher nächster Schritt im [WE-STATUS](wohnungserkundung/STATUS.md).

## 2026-09-26 — Bewährte HWT-Fusion explizit in WE integriert, noch keine Hardwareabnahme

**Entscheidung:** PR #100 (`113014e`) bleibt Basis. Auf getrenntem Branch
`codex/we1-hwt601-fusion` selektive Übernahme aus HWT-Referenz `1d91229`
(`b3b6370`) und opt-in Integration (`f61e3e7`), kein Blind-Merge. Bestehenden
read-only Treiber, Achsen, eingefrorenen Start-Bias, Encoder-vx/HWT-wz-EKF
und unabhängigen LiDAR-Beobachter erhalten. Kein OAK, keine Kalibrieränderung.
EKF besitzt allein `/odom`/`odom->base_link`, SLAM `/map`/`map->odom`.
Motorlos ersetzt der echte FC03-only Leser die Basis exklusiv; synthetischer
Dry-run gilt nicht als Stillstandsnachweis. HWT-Start braucht eine aktuelle
explizite Stillstandsbestätigung. Alle bisherigen VL53-/Cancel-Fixes bleiben.

**Evidenz:** HWT lag im historischen Install, aber nicht in der geladenen
PR-#100-Kette; kein laufender HWT-Prozess. 14-Paket-Isolat gebaut,
1185 Tests bestanden, Quelle/Install der neuen Absicherung hashgleich.
Echter EKF mit synthetischen Eingängen fusioniert Encoder-vx/HWT-wz korrekt.
Bei fehlendem Roh-HWT bzw. Encoder produziert er noch 14 bzw. 23 Odometrien:
Deshalb sperren Fahrtor/Explorer anhand echter Eingänge und verriegeln einen
Ausfall nach Bereitschaft, statt EKF-Frische als Sensorgesundheit zu werten.
Kein stiller Rückfall auf Encoder-Gier. Zwei Prozessläufe sauber beendet.
WE-Ziel-B-Fortsetzung und echter Nav2-Stopp/Umfahrung mit bleibender
synthetischer Barriere und fortgesetzter Elternmission erneut bestanden.

**Befundgrenze:** Sechs alte Cancels zeitlich rekonstruiert, ihre konkreten
Quellenprädikate nicht lückenlos erhalten. Zwei kurz ungültige Raw-Map-Proben
sind kein Beweis für spätere Cancels. Befehlsunterbrechungen und erhebliche
RPM-/Positionsodom-Differenz sind gemessen; Antrieb/Encoder/Chassis-Ursache
weiter offen. Kein HWT in dieser alten Fahrt, keine erfundenen HWT-Messungen
und keine pauschale Schlupferklärung. Tabelle im [WE-STATUS](wohnungserkundung/STATUS.md).

**CI-Integration:** Folge-PR #101 auf #100. Erster Encoder-Workflow meldete
fehlendes `yaml`/`pytest`; Testumgebung und deklarierte YAML-Testabhängigkeit
gezielt ergänzt, Aufruf auf pytest umgestellt, damit auch die übernommenen
Fälle wirklich laufen. Keine Testabschwächung und keine Laufzeitänderung.

**Hardware / Risiko / Rückfall:** Kein aktueller Gerätezugriff, keine Fahrt,
keine Umstellung des aktiven Installs; fremde lokale Arbeit erhalten.
Motorlose HWT-Zielsystemprüfung und reale Bewegung OFFEN. FC03 erfordert
antwortende Controllerelektronik bei unabhängig gesperrter Motorendstufe.
Aktuelle Freigabe dafür zuerst gebündelt einholen. Rückfall ausschließlich
gestoppt mit frischer Shell/alter PR-#100-Kette und HWT-Opt-in aus; niemals
Topic-/TF-Eigentümer während einer Mission umschalten. Details und konkreter
Prüfablauf in [ROBOT_TRANSFER](ROBOT_TRANSFER.md). Stufe 3 bleibt GELB.

## 2026-09-25 — VL53-Frame-Luecke und Cancel-Race minimal korrigiert

**Entscheidung:** Keine Sicherheitsgrenze lockern und den aktiven Install
nicht umstellen. Ein fehlender VL53-Rohread publiziert kein frisch datiertes
Status-Tripel; 64er-Laengen der konfiguriert benoetigten Qualitaetsraster
werden geprueft. Ein von einer ungueltigen Kartenquelle ausgeloester
Nav2-Cancel behaelt seine Ursache bis zum Kindresultat; unbestaetigter
Cancel bleibt Systemfehler.

**Evidenz:** Echte CH341/VL53-Reads warfen `IndexError`; ein zurueckgegebenes
`nb_target_detected`-Raster hatte 252 Eintraege. Beim begrenzten Realversuch
gab es sechs Source-Replans, 0,1445 m Translation und keinen Umfahrnachweis;
der letzte asynchrone Cancel wurde nach Quellen-Erholung faelschlich zum
terminalen `child_navigation_canceled`. Die Antriebsrueckmeldung zeigte
zeitweise Soll `w=-0,12 rad/s` und rund 34 Motor-rpm, aber Encoder-Odometrie
nur `-0,005...-0,04 rad/s`; Ursache offen.

**Test / Hardware:** 971 gerätefreie Tests; isolierte VL53-/Explorer-Overlays,
motorlos 44/44 gesunde Tripel, frische TF/Karte/LiDAR, sechs Lifecycles,
null Fahrbefehle, korrekt wiederholter Shutdown 24/24 sauber. Der erste
motorlose Shutdown per Terminal-Gruppensignal erzeugte Tracebacks und ist
explizit kein Abnahmenachweis. Keine weitere reale Fahrt nach dem Befund.

**Risiko / Rueckfall:** Nach einem nur formatierenden Rebuild starb der
VL53-Knoten in einem weiteren vollen motorlosen Start nach 26 s (Exit 1,
0 Near-Field-Topics/Qualitaetsproben); genaue Exception nicht gesichert.
Zwei isolierte Sensorstarts und ein weiterer voller Start gelangen, also
kein genereller Hardwareausfall, aber keine reproduzierbare motorlose
Abnahme dieses exakten Builds. Wiederholte Quellen-Replans und
Antriebs-/Odometrie-Abweichung sind ebenfalls offen. Isolierte Overlays
nicht sourcen, bisherigen aktiven Install beibehalten. Stufe 3 GELB, kein
Merge/keine Stufe 4. Details im [WE-STATUS](wohnungserkundung/STATUS.md).

**Nachtrag:** Der Fehler wurde im vollen motorlosen Stack reproduziert:
rechter VL53, `s.init()`/MCU-Boot-Poll, `VL53L5CXException: 0`.
Ein genau einmaliger Retry nur fuer diesen Fehler und Cleanup bei erneutem
Scheitern sind jetzt im separaten VL53-Overlay. 974 Tests, danach zwei
volle motorlose Preflights mit 58/58 und 57/57 gesunden Tripeln,
null Fahrbefehlen und je 24/24 sauberem Shutdown. Kein Fahrtest nach
dieser Aenderung; Antriebsabweichung und Umfahrung weiterhin offen.
Die geraetefreien Gesamtprozessfaelle `frontier_replan`, `local_blocked`,
echter Nav2-`explorer_bypass` und `stopped_bypass` wurden mit dem finalen
Overlay erneut bestanden; die Barriere blieb in den Bypassfaellen stehen
und die Elternmission setzte nach dem Kindziel fort. Reale Umfahrung ist
dadurch nicht ersetzt.

---

## 2026-09-25 — Vor-Ort-Korrektur akzeptiert, Realtest durch Frame-Health gestoppt

Der Nutzer bestätigte nach seiner gegenteiligen Aussage ausdrücklich, dass
die Abschaltung verbaut und geprüft sei; diese Vor-Ort-Auskunft wurde als
Korrektur akzeptiert, nicht als ferntechnischer Hardwarebeweis. Frühere
Teilversuche sind dadurch nicht nachträglich abgenommen. Kandidat/Install
und sämtliche Produktparameter blieben unverändert (`3913079`, PR #100).
Nach bestandenem Vorlauf (57 gesunde Tripel pro VL53, frische TF, aktive
Lifecycles, gemessene RPM null) startete ein automatischer Explorerauftrag.
Nach 13,267 s Rundblick fielen beide `frame_healthy`-Flags ab; Fahrtor
`blocked`, Wächter-Cancel. Bei 16,082 s waren zwei Sekunden gemessener
Stillstand bestätigt, später 24/24 Launch-Kinder sauber beendet.

**Entscheidung / Rest:** Kein weiterer Realtest nach diesem Fehler.
Rohframe-/Treiberursache noch offen, keine Behauptung eines Hardwaredefekts
und keine Grenzwertlockerung. Kein Umfahrnachweis und keine Stufe 4.
Details und private Evidenz im [WE-STATUS](wohnungserkundung/STATUS.md).
Rückfallweg: Stack gestoppt lassen; aktiven Install nicht umstellen.

## 2026-09-25 — Historisch: Sicherheitsvoraussetzung für weitere reale Fahrt widerlegt

**Entscheidung:** Keine weitere Motoraktivierung oder Fahrt. Nach dem
begrenzten Realversuch erklärte der Nutzer, es gebe am selbstgebauten
Roboter überhaupt keinen hardwired Not-Aus und die Motorversorgung könne
nicht ausgeschaltet werden. Das widerspricht der vorherigen ausdrücklichen
Bestätigung eines erreichbaren Hardware-Not-Aus. Die technisch beobachtete
Kurzfahrt ist deshalb **keine gültige Sicherheitsabnahme**. Software-Cancel
und ROS-Shutdown ersetzen keine unabhängig wirksame Abschaltmöglichkeit.

**Beobachtete Evidenz:** Nach der Offenlegung nur passive Starts mit
`dry_run=true`, `allow_rs485=false`, null Motorsollwerten. Neue bleibende
Barriere: etwa 0,55 m vor dem Roboter, 0,55 m breit, 0,75 m hoch. LiDAR
maß frontale Treffer ab etwa 0,81 m Achsabstand; im geladenen Scope
berechnete Nav2 einen Diagnosepfad rechts (106 Posen). Beide VL53,
Karte/TF/Safety/Nav2 waren frisch beziehungsweise aktiv; der Preflight
hatte 59 gesunde Teilframes je Seite. Das beweist keine autonome
Explorer-Umfahrung. Beide passiven Starts: je 24/24 saubere Kinder,
kein RS485-Handle nach Shutdown. Der Stack ist aus.

**Betroffen / Rückfall / Rest:** Keine Produktparameter und kein aktiver
Install geändert; Belege im [WE-STATUS](wohnungserkundung/STATUS.md).
Reale Fahrt erst nach Herstellung und Vor-Ort-Nachweis einer unabhängig
wirksamen Hardware-Not-Aus-/Motorstromtrennung. Bis dahin Softwarestand
isoliert lassen, keine Stufe 4 und kein Merge.

---

## 2026-09-25 — erste reale Stufe-3-Kurzfahrt, Umfahrung noch nicht belegt

**Entscheidung:** Stufe 3 bleibt GELB; nach Test A keinen Stopp-/Wandfall
vorziehen. PR #100/`a710fe3`, isolierter Health-Install, nur ein Stack.

**Beobachtete Evidenz:** Mit vor Ort freigegebenem hardwired Not-Aus und
Motorstrom, 3 m Vorraum, je ca. 1 m seitlich und lokal gebundenem Scope
`x=[-0,5;2,6]`, `y=[-0,8;0,8]` bestanden Sensor-/TF-/Safety-/Nav2-Preflight.
Der autonom vom Explorer gewählte Nav2-Auftrag fuhr 0,18 m laut Odometrie;
expliziter Test-Cancel stoppte beide Motoren mit 0 RPM. Das ist Test A,
**keine** Hindernisumfahrung. Im anschließenden B-Rundblick entstanden
10 offene Aufgaben, aber 0 zulässige: sechs `no_current_raw_map_route`,
vier auf der aktuellen Revision nicht beobachtet; kein Nav2-Pfad und
0 m Translation. Der separate Wächter cancelte nach 128 s zusätzlich mit
`guard_lost`, ohne dass sein konkreter Einzelgrund aufgezeichnet wurde.
Keine unbelegte Sensorursache behaupten. Die 0,40 m hohe, 0,38 m breite
Barriere liegt unter der LiDAR-Höhe 0,66 m und ist kein gültiger Aufbau
für den vorher definierten frühen LiDAR-/Nav2-Umfahrtest mit mindestens
0,80 m Höhe. Sie wurde nicht entfernt. 24/24 Shutdown-Kinder sauber,
keine Tracebacks oder offenen Gerätehandles.

**Betroffene Dateien und Hardware / Rest / Rückfall:** Keine Produktdatei,
kein aktiver Install und keine Sicherheitsgrenze geändert. Nur lokales
Scope-Profil und lokale Wächterlogs unter `~/.local/share/amadeus/`.
Motorversorgung muss der anwesende Nutzer wieder physisch trennen.
Vor weiterer Fahrt Route/Policy im gemessenen Scope und den Wächtergrund
motorlos aufklären, LiDAR-sichtbare matte Barriere und Passagen vermessen,
erneut vor Ort freigeben; dann B vor C/D. Vollständige Evidenz im
[WE-STATUS](wohnungserkundung/STATUS.md). Rückfall: isoliertes Overlay
nicht sourcen, Stack ist bereits gestoppt. Kein Merge und keine Stufe 4.

---

## 2026-09-25 — finaler VL53-Health-Vertrag, motorlos zweimal bestanden

**Entscheidung:** Nach ausdrücklicher Präzisierung der Produktrolle VL53
als Nahhindernis-/Reaktionssensor verwenden, nicht als globale
64/64-Freiraumbescheinigung. `e18a267` ergänzt explizite Frame-Health-
Felder; `b692c28` ist der finale Gerätefrei-Prüfstand auf PR #100.
Health ersetzt im Fahrtor/Explorer/optionalen Nahhalt die komplette
Targetabdeckung. Unbekannte Zonen bleiben unbekannt und räumen nicht;
gültige Teilframe-Nahpunkte bleiben marking-only wirksam. Frische,
Scope, Safety, Footprint, Padding und Geschwindigkeiten unverändert.

**Beobachtete Evidenz:** Reale A/B-Aufnahmen (unten) belegen gesunde
Sensoren mit nur 2–6 Fernreturns. 970 Vertragstests und bestehende
Stufe-3-Prozessfälle bestanden; zusätzliche Teilframe-, Wand- und
Eckfälle belegen bleibende Umfahrung, zwei erfolgreiche Explorerziele,
keinen Rückwärtsweg und weiterlaufenden Elternauftrag. Ein im alten
und neuen Stand gemessener `disappear`-Prüferfehler (22 s verbleibende
Hinderniszelle durch ungleiche synthetische Markierungs-/Clearingstrahlen)
wurde ausschließlich im vorhandenen Prüfer korrigiert. Danach bleibt A
erhalten und die Mission arbeitet weiter; keine Testgrenze gelockert.

**Zielsystem:** Neues isoliertes `we1-stage3-health-CVhWvH/install`,
Quell-/Install-Hashvergleich und echte Prozessauflösung geprüft.
Zwei passive Gesamtstarts: 59 bzw. 56 gesunde PARTIAL-Tripel je Seite,
Health-Prüfung positiv, frische LiDAR/TF/Odom/Karte, Nav2/Collision Monitor
aktiv, keine Nichtnull-Fahr-/Motorwerte, RS485 gesperrt, je 24/24 saubere
Shutdown-Kinder ohne Traceback/Handle. Motorversorgung physisch getrennt.

**Rest / Rückfall:** Softwareentwicklung dieses Abschlussauftrags beendet.
Realen begrenzten Testaufbau zur separaten Freigabe vorgelegt; tatsächliche
Maße und aktuelle Karten-/Scope-Bindung stehen vor Fahrt noch aus.
OAK ist vorhandene, wiederverwendbare Nav2-Quelle, im aktuellen WE-Start
aber nicht aktiviert; keine neue Pipeline. Vollständige Evidenz und
Fahrtestvorschlag nur im [WE-STATUS](wohnungserkundung/STATUS.md).
Aktiver Install unverändert, kein Merge. Rückfall: komplettes neues
Interface-/Verbraucheroverlay weglassen; vorheriger strenger Stand sperrt.
Die frühere pauschale 0,60-m-Freiraumannahme bleibt verboten.

## 2026-09-25 — 64/64 real widerlegt, pauschale PARTIAL-Fahrfreigabe verworfen

**Entscheidung:** Die Juli-Zonenfilterung, vollständige 8×8-Frameprüfung,
gültige Hindernispunkte und die marking-only-Korrektur von PR #100 bleiben
getrennte Grundlagen. Weder 64/64-Targets als globale Sensor-Health noch
`PARTIAL` allein als Fahrfreigabe verwenden. Die experimentelle pauschale
Verbraucheröffnung wurde vor Commit/Push zurückgenommen; das aktive
Fahrtor bleibt fail-closed.

**Grund / beobachtete Evidenz:** Bei derselben realen Sensorik lieferten
je Seite 30/30 vollständige Frames vor einer matten Platte 64 gültige
Targets, Status 5 und kleine Sigma-Werte; nach Entfernen der Platte nur
2–6 Fernreturns je Frame, `QUALITY_PARTIAL`, keine volle Spalte. Hardware
und Treiber sind grundsätzlich plausibel; die global verlangten 64/64
Targets sind in der freien Szene physikalisch nicht verfügbar. Ein
gerätefreier echter Nav2-Test mit pauschaler `PARTIAL`-Freigabe bestand
Umfahrung und Explorer-Fortsetzung, belegte aber **nicht** die
Beobachtung des niedrigen/seitlichen Realraums. LiDAR sitzt bei 0,66 m,
OAK ist im WE-Mapping-Launch aus. Zwei motorlose Gesamtstarts mit diesem
isolierten Testpräfix zeigten frische Quellen, null Fahrbefehle und jeweils
24/24 saubere Shutdown-Kinder. Zwei zusätzliche Starts des strengen
PR-#100-Kandidaten ohne dieses Testpräfix zeigten ebenfalls frische Quellen,
null Fahr-/Motorwerte und je 24/24 saubere Kinder; der Scope war nicht
gebunden.

**Betroffene Dateien und Hardware:** Reale VL53 und ROS-Prozesse nur bei
physisch getrennter Motorversorgung; Rohframes ausschließlich lokal unter
`/home/p/.local/share/amadeus/tests/we-stage3-vl53-ab-20260925.json`.
Kein aktiver Install, kein Produktionsprofil und keine Sicherheitsgrenze
geändert. Dokumentation im maßgeblichen WE-STATUS und ROBOT_TRANSFER.

**Teststatus / offenes Risiko / Rückfall:** A/B und passiver Stack-/Shutdown-
Teil bestanden; vollständige Fahrbereitschaft **nicht**. Für reale Bewegung
fehlen positiver bewegungsbezogener Beobachtungsbeleg, aktuelle Scope-/
Startpose-Bindung und separate Fahrfreigabe. Das experimentelle
`we1-stage3-vl53-partial-PiRlgn` niemals zur Fahrt sourcen; Weglassen des
Overlays erhält das unveränderte fail-closed Tor. Die alte 0,60-m-Annahme
bleibt verboten.

---

## 2026-09-24 — Teilframe-Hindernisse markieren, unbekannten Raum nicht räumen

**Entscheidung:** Die real bewährte VL53-Zonenfilterung und Originalwolke
bleiben Grundlage. Eine vollständige 8×8-Rohnachricht wird getrennt von
gültigen Einzel-Target-Returns beurteilt. Nav2 erhält gültige Nahpunkte aus
Teilframes zusätzlich als marking-only-Quelle. Weder die alte pauschale
0,60-m-Freiräumung bei fehlendem Target noch eine bloße `PARTIAL`-Freigabe
des Fahrtors wird übernommen.

**Grund / beobachtete Evidenz:** Ein neuer motorloser A/B-Lauf auf denselben
je 20 Rohframes fand historisch 0 Nahpunkte, heute je 220 gültige Fern-Zonen,
aber 0 volle Spalten. Eine rechte vollständige Rohnachricht hatte gar keinen
gültigen Target-Return. Der Stage-3-Vollspaltenfilter unterdrückte damit
auch echte Nah-Hindernisse in der Nav2-Costmap, obwohl die Originalwolke sie
dem Collision Monitor liefert. Der 64/64-Vertrag aus `785b825`/`e3d7352`
hat keinen Realnachweis; die zuvor gemessenen 0/160 Vollspalten je Seite
widerlegen seine praktische Verfügbarkeit in der freien Szene.

**Betroffene Dateien und Hardware:** Nur `nav2_params_real.yaml`, der
zugehörige Vertragstest und ein VL53-Punktwolken-Vertragstest wurden für den
Markierungsfix geändert; beide echten VL53 wurden nur motorlos gelesen.
Keine aktive Roboterinstallation oder Sicherheitsgrenze wurde geändert.

**Teststatus:** 969 Vertragstests und die echten, aber gerätefreien
Nav2-Prozessfälle `fixed_bypass`, `explorer_bypass`, `stopped_bypass`,
`blocked` bestanden. Großflächen-Zielreturn, bewegungsspezifischer
Freiraumbeleg, aktueller Karten-Scope und erneuter Gesamtpreflight fehlen;
deshalb weiterhin **keine reale Fahrfreigabe**.

**Offene Risiken / Rückfall:** 2D-Costmap, LiDAR-Höhe und in WE deaktivierte
OAK belegen unbeobachtete VL53-Höhen nicht automatisch. Der Markierungsfix
ist nur im isolierten Overlay `we1-stage3-vl53-mark-bwVxEL`; Rückfall durch
Weglassen dieses Overlays. Das ältere 64/64-Tor bleibt bis zu einem
positiv belegten Ersatz aktiv.

---

## 2026-09-24 — Motorloser Stufe-3-Zielsystemvorlauf bleibt gesperrt

**Entscheidung:** Keine reale Fahrt freigeben und keine VL53-/Collision-
Grenze lockern. Den konkret beobachteten Explorer-SIGINT-Race getrennt
beheben und nur als isoliertes Overlay über den vorhandenen Kandidaten legen.

**Grund / beobachtete Evidenz:** Beide echten VL53 lieferten stempelgleiche,
frische Frames, aber bei je 20 Rohframes nur 223/1280 (links) und 233/1280
(rechts) gültige Zonen; keine der 160 Spalten je Seite war vollständig.
Vorwiegend `target_status=255` und fehlendes Ziel verhinderten den
64/64-Vertrag; leere Wolken sind kein Freiraumbeleg. Beim ersten Gesamt-SIGINT
des ursprünglichen Kandidaten starb nur der Explorer mit invalidiertem
Humble-Wait-Set. Der gezielte Executor-vor-Kontext-Fix `0fe9245` bestand 921
Explorer-Tests und zwei motorlose Gesamtstarts/-stopps mit je 24 sauberen
Kindern und freien Gerätehandles. TF, LiDAR, Rohkarte, Kartenmanager, Safety,
Nav2 und Null-Fahrkanäle waren im 12-s-Fenster frisch; das R9-Scope ist nach
dem letzten SLAM-Neustart nicht neu physisch gebunden. Details im WE-STATUS.

**Betroffene Dateien und Hardware:** `explore_node.py`, zwei Shutdown-
Vertragstests und ein neues isoliertes `explore`-Präfix; reale VL53, LiDAR
und ROS-Prozesse nur motorlos gelesen. Motorversorgung physisch getrennt;
kein aktiver Install/Profilwechsel. **Offene Risiken:** Sensor-64/64-Qualität,
aktuelle Scope-Bindung und reale Umfahrung/Stoppbefreiung. **Rückfallweg:**
Neues `explore`-Overlay weglassen; keine der isolierten Varianten ist zur
Fahrt freigegeben.

## 2026-09-24 — PR #99: Bring-up-Vertrag in passender CI-Umgebung

**Entscheidung:** Den unveränderten Bring-up-Test des Workflows
`semantic-map-offline.yml` in einem ROS-Humble/Jammy-Job mit deklariertem
`python3-opencv` und `ros-humble-cv-bridge` ausführen. Der Mapmanager-Test
erhält den fehlenden Python-Suchpfad zum bestehenden Paket
`amadeus_map_identity`. Keine Robotiktests auslassen oder abschwächen.

**Grund / beobachtete Evidenz:** Der frühere frische Python-Runner brach beim
Import von `cv2` ab, bevor Tests oder der Mapmanager-Schritt laufen konnten.
Lokal liefen sieben Bring-up- und 53 Mapmanager-Tests mit den benötigten
Abhängigkeiten. Beide erneuten GitHub-Läufe für `e4376c4` bestanden
vollständig ([36035275084](https://github.com/chris01-byte/Roboter_ws/actions/runs/36035275084),
[36035281883](https://github.com/chris01-byte/Roboter_ws/actions/runs/36035281883)).

**Betroffene Dateien und Hardware:** Nur CI-Workflow; kein Hardwarezugriff,
kein aktiver Install, keine Motoren. **Offene Risiken:** Motorlose Prüfung des
isolierten Stufe-3-Kandidaten, reale Sensorqualität und Fahrabnahme bleiben
offen. **Rückfallweg:** CI-Commit zurücknehmen; der isolierte Kandidat und
alle aktiven Roboterpräfixe bleiben unverändert.

## 2026-09-24 — Stufe-3-Softwareablauf abgeschlossen; reale Abnahme offen

**Entscheidung:** VL53-Qualität vor dem Nahfilter explizit je Sensor melden
und mit beiden Originalwolken stempelgleich korrelieren. Nur vollständig
gültige, plausible 8×8-Rückgaben dürfen als beobachtete Freiraumstrahlen
in die Costmap gelangen. Explorer, Fahrtor und der optionale Safety-Nahstopp
verlangen positive frische Evidenz; fehlende/ungültige Daten halten an.
Der Kartenmanager verarbeitet SIGINT erst nach laufendem Callback, bevor
Executor, Knoten und Kontext in dieser Reihenfolge schließen. Das Fahrtor
benötigt zusätzlich ein frisches explizites Software-Not-Aus-Freigabesignal
und frische `odom→base_link`-/`map→base_link`-TF, bevor es Missionsbewegung
ausgibt; die Lokalisierungssuche bleibt getrennt begrenzt.

**Grund / beobachtete Evidenz:** Der reale Treiber nennt das Sigmafeld
`range_sigma_mm`; zuvor wurde es unter `sigma_mm` nicht geprüft. Eine
gültige Fernrückgabe und Status 255/ungültig erzeugten identisch leere
Originalwolken. Ein unabhängiger Review fand zusätzlich, dass der neue
UNKNOWN-Status ohne Anpassung des `safety_monitor` einen gesetzten
Nahstopp aufheben konnte; vor der Abnahme korrigiert. Tests decken gültig
nah/fern, partielle/fehlende/malformed/negative/unplausibel große Werte,
stempelgleiche Produktion, leere Fernwolke und ungültige Costmap-Strahlen ab.
Zwei echte SIGINT-Läufe während eines laufenden Karten-Save-Callbacks
bewahrten beide Saves und endeten ohne Traceback oder Restprozess. Der
historische `take_message()`-Race ist strukturell durch den nicht mehr
vorzeitig invalidierten ROS-Kontext adressiert; der exakte Zeitpunkt wurde
im Smoke nicht deterministisch reproduziert.

**Reglerbefund:** Bei altem 0,80-m-Lookahead schneidet RPP den vorhandenen
NavFn-Umweg ab und stoppt korrekt vor einer tödlichen lokalen Costmap-Zelle.
Eine 0,10-rad-Drehschwelle verletzte im gerätefreien späten Gegenversuch
die unabhängige gepaddete Footprint-Geometrie und wurde verworfen. Der
aktuelle 0,40-m-Lookahead/0,35-rad-Stand zeigte nach einem notwendigen
Stopp sichere autonome Umfahrung bis Ziel A. Ein früher A→B-Lauf scheiterte
an einem Odometrie-Snapshot-Race (`age_s=-0.029`) und ein weiterer an
erneutem Cancel durch inhaltlich gleiche Kartenbeobachtung nach bereits
positiver neuer Revalidation. Monotone Frische wird nun nach jeder Aufnahme
gemessen; der letzte positiv revalidierte Kartenfingerprint überlebt
identische Folgebeobachtungen. Echte neue Inhalte benötigen weiterhin
Revalidation. Auf dem finalen gerätefreien Kandidaten gelangen der
notwendige Stopp **und** frühe dauerhafte Umfahrung jeweils bis zu zwei
erfolgreichen automatisch gewählten Zielen bei laufender Elternmission.
Keine Rückwärtsfahrt oder konkurrierende Nav2-Ziele.

**Weitere Sicherheitsbefunde:** Der echte Nav2-Prozessprüfer zeigte, dass
ein Software-Not-Aus ohne Gate-Anbindung noch kurz Bewegung zuließ und ein
TF-Ausfall sogar 0,172 m virtuellen Nachlauf bewirkte. Die explizite
Not-Aus-Prüfung im Gate und getrennte TF-Frische (Basis 0,2 s, gesamte
Kartenkette 0,8 s) reduzieren dies im gleichen Test auf 0,022 bzw.
0,037 m und beenden Kind/Elternauftrag ohne Recovery. Ein Not-Aus-Lauf
mit 0,0263 m verfehlte die anfängliche willkürliche 0,025-m-Diagnosegrenze;
die Spur wies Gate-Null und Nachlauf allein durch den unveränderten
Velocity-Smoother nach. Die neue 0,04-m-**Prüfergrenze** ist aus dessen
0,30-m/s²-Verzögerung und Publikationsphasen hergeleitet und verlangt
zusätzlich Gate-Null binnen 0,15 s und Ausgangs-Null binnen 0,45 s.
Weder Produktgrenze noch Bremskonfiguration wurde gelockert. Die Gate-Suche vor
Lokalisierungsfix behält ihren separaten bereits begrenzten Vertrag. Diese
strengeren Prüfungen sind **kein** Ersatz für hardwired Not-Aus oder reale
TF-/Sensor-Frequenzmessung vor Deployment.

**Betroffene Dateien und Hardware:** Additive `NearFieldStatus`-Felder,
VL53-Produzent, Explorer/Fahrtor/Safety-Verbraucher, bestehende Nav2-
Konfiguration, Kartenmanager und gezielte Tests. Kein Hardwarezugriff,
kein aktiver Roboterinstall, keine Motoren. Neun betroffene Pakete im
isolierten Kandidaten gebaut; der C++-BT-Build benötigte den vorhandenen
lokalen `behaviortree_cpp`-CMake-Underlay.

**Teststatus / offene Risiken:** 1 018 Pytests der fünf betroffenen Pakete;
echte Nav2-Prozessfälle `explorer_bypass`, `stopped_bypass`, `disappear`,
`no_exit`, aktive VL53-/Not-Aus-/TF-Fehler; bestehende Prozessfälle
`local_blocked`, `frontier_replan` und `frontier_no_source`;
zweimaliger Save/SIGINT-Smoke
bestanden. Der Prozessprüfer benötigte eine Korrektur seiner periodischen
Telemetrie und seines asynchronen Cleanup; der erste Replan-Wiederholungslauf
hatte eine `Destroyable`-Aufräummeldung, der danach saubere Lauf ist belegt.
`frontier_no_source` benötigte ebenfalls den periodischen Prüfer-Timer; der
erfolgreiche Wiederholungslauf endete erst am Missionsbudget, ohne zweite
Navigation oder Fahrbefehl.
Reale 64/64-VL53-Verfügbarkeit und TF-Rate, motorloser Zielstack und
Realabnahme bleiben offen. Der exakte historische `take_message()`-SIGINT-
Zeitpunkt ist nicht deterministisch injiziert. Details und lokale Fehlerbelege
stehen im laufenden WE-STATUS.

**Rückfallweg:** Kandidaten-Overlay nicht sourcen; die zuvor getesteten
Präfixe und die aktive Roboter-Arbeitskopie bleiben unverändert. Die
fehlgeschlagenen Versuche wurden nur in lokalen `/tmp`-Evidenzordnern
aufgezeichnet, nicht als Wohnungsdaten committed.

---

## 2026-09-23 — Stufe-3-Umweg belegt; Direktkorridor und VL53-Leere getrennt

**Entscheidung:** Nach `a8710db` die Rückkehr einer blockierten Aufgabe an
einen frischen geodätischen Weg auf der Schnittmenge von exakt gebundener
Rohkarte/Scope und gleichgerasterter Nav2-Costmap binden. Der gerade
Zielkorridor darf blockiert bleiben. Start-/Zielprojektion, fremde Raster,
veraltete Daten und Wege außerhalb des Scopes geben die Aufgabe nicht frei.
Der bestehende Nav2-Ausführungspfad bleibt unverändert.

**Evidenz:** Die alte Wiederfreigabe lehnte einen belegten Umweg ab. Der
gezielte Prozessfall wählt jetzt nach A-Abbruch und B-Fortschritt A erneut,
obwohl sein Direktkorridor ein Hindernis behält. Separat umfuhr der echte
Nav2-Controller eine dauerhaft stehende synthetische Barriere; automatische
Explorerwahl, erster Frontierabschluss, erfolgreicher zweiter Auftrag und
Fortsetzung desselben Elternauftrags sind gegen das neue Install belegt.
Gesamtweg 3,253 m, Folgeziel 0,453 m, maximal ein Kind, keine Rückwärtsfahrt
und keine geplante/gefahrene Polygonverletzung. Ein festes Diagnoseziel
bestand zuvor separat. Nav2-/Collision-Parameter wurden nicht geändert.

**Schnittstellengrenze:** Produktionsmethoden des VL53 erzeugen sowohl bei
gültiger Fernmessung als auch bei ungültiger Messung null Originalpunkte.
Die Test-Nullvektoren waren kein Gesundheitsbeleg. Der Explorer trennt
Empfang, Quellalter, Messgültigkeit und Punktzahl; leere Wolken bleiben
unbekannt und erlauben keine Recovery. Der echte Stoppfall findet einen
geometrisch gültigen Umweg, scheitert aber an der lokalen Kollisionsprüfung
des Reglers und anschließend an diesem fehlenden Sensorgültigkeitsbeleg.
Die nötige Produzenten-/Statusvertragserweiterung und der Reglerbefund sind
im maßgeblichen WE-Status konkret abgegrenzt; keine blinden Manöver ergänzen.

**Dateien / Hardware / Tests:** Nur Explorer, zugehörige Tests und bestehende
gerätefreie Prozessprüfer. 917 Pytests und 917 registrierte Colcon-Tests
grün; gezielte Policy-/Umfahr-/Stillstandsprüfungen. Kein Hardwarezugriff,
kein aktiver Installwechsel. Quelle `90379d9`, Prüfer `d13a6c9`, Präfix und Hash
in `ROBOT_TRANSFER`. Stufe 3 bleibt wegen Stoppbefreiung, Sensorvertrag und
fehlender realer Abnahme GELB. **Rückfall:** Neues Overlay nicht sourcen;
der Ausgangsstand bleibt vorhanden, einschließlich seiner bekannten Fehler.

---

## 2026-09-23 — WE-Stufe 3: Routenblockade nach echtem Nav2-Abbruch getrennt behandeln

**Entscheidung:** Einen bereits terminalen Nav2-Abbruch auch dann als
begrenztes `LOCAL_BLOCKED` behandeln, wenn das metrische Ziel frei bleibt,
aber eine frische globale Costmap eine tödlich belegte Zelle höchstens
0,75 m vor der stillstehenden Basis im zielwärtigen 0,35-m-Korridor zeigt.
Dieselbe Aufgabe wird erst nach neuer Costmap **und** freiem Zielkorridor
wieder wählbar; ein weiterhin freier Zielpunkt allein reicht nicht.
Alle bestehenden Not-Aus-, TF-, Odometrie-, LiDAR-, dualen VL53- und
Costmap-Frischeprüfungen bleiben vorgeschaltet. Die Klassifikation gibt
selbst keinen Fahrbefehl frei und verwendet dieselben Ziel-/Zeitbudgets.

**Grund / beobachtete Evidenz:** Ein gerätefreier Prozessprüfer mit echtem
Nav2, WE-Collision-Monitor, Fahrtor, Smoother und virtueller Basis zeigte
zweimal Hindernis → sicheren Reglerstopp (Poseänderung 2,2–2,5 mm) →
Hindernis verschwindet → weitere 0,534–0,536 m virtuelle Fahrt → A erreicht
→ neue Rohkarte markiert A abgeschlossen → anderes Ziel startet; maximal
ein Kindziel. Bei dauerhaftem Hindernis wurde A als lokale Blockade
zurückgestellt, aber B lag hinter demselben Hindernis. B selbst blieb als
metrischer Punkt frei; der alte Code stufte seinen Controller-Abbruch als
`SYSTEM_FAILURE` ein und beendete den Elternauftrag. Mit der neuen
Korridorprüfung blieb der Auftrag nach zwei echten Nav2-Abbrüchen aktiv,
ohne weiterzufahren oder parallele Kindziele zu starten.

**Betroffene Dateien und Hardware:** `src/explore/explore/explore_node.py`,
Explorer-Vertragstest und ein isolierter Test-Launch/Prozessprüfer unter
`tools/kartierung/`. Kein Hardware- oder Sicherheitsparameter geändert,
kein Motor aktiviert. Neues `explore`-Install in einem getrennten lokalen
Stage-3-Präfix; aktiver Roboter-Install unverändert.

**Teststatus / offene Risiken:** Explorer-Tests 904 grün, bestehender
Acht-Szenarien-Prozessprüfer grün; neuer echter Nav2-Prozessfall
`disappear` zweimal grün. Ein dauerhafter synthetischer Umfahrfall stoppte
an zwei Positionen sicher, erreichte A aber nicht. Nach drei durch das
Testprofil begrenzten Kindzielen blieb der Roboter virtuell stehen und die
Mission wartete auf eine sichere Alternative; keine konkurrierenden Ziele.
Reale Bewegung und
spätere sichere Weiterfahrt nach Zurückstellung fehlen. Das reale enge
WE-Profil bot im letzten motorlosen Lauf kein Frontierziel, und der
Kartenmanager-SIGINT-Race ist noch ungeklärt. Stufe 3 bleibt GELB.

**Rückfallweg:** Das neue Overlay aus der Source-Reihenfolge entfernen und
den vorherigen Stage-3-Kandidaten verwenden; kein automatischer Merge oder
Deploy. Bei irgendeinem Safety-Ausfall bleibt der unveränderte
`SYSTEM_FAILURE`-Pfad aktiv.

---

## 2026-09-23 — WE-Stufe 3: linker Nahpunkt löst nur SlowZone aus; Shutdown-Race offen

**Entscheidung:** Keine reale Fahrt aus dem neuen linken Hindernisaufbau
freigeben. Ein Nahbereichs-Flag allein ist weder ein belegter Vollstopp noch
ein sicherer Recovery-Pfad; der konkrete WE-Mapping-Monitor muss am Ausgang
bewertet werden. Der unerwartete Kartenmanager-Exit beim Stop bleibt offen.

**Grund / beobachtete Evidenz:** Der linke VL53 sah ~0,24–0,25 m, der rechte
keinen Nahpunkt. Bei motorlosem synthetischem 0,08-m/s-Eingang gab der
Collision Monitor höchstens 0,024 m/s aus, passend zur unveränderten
30-%-SlowZone, nicht null. Der Test nutzte `dry_run=true` und
`allow_rs485=false`; keine physische Bewegung. Beim Einzel-SIGINT starb
`robot_map_manager` mit einem Humble-`take_message()`-RuntimeError; danach
waren alle Prozesse und Gerätehandles frei. Der vorhandene RuntimeError-Guard
in Quelle und Install ist bytegleich, deckte diesen Fall aber nicht ab.

**Betroffene Dateien und Hardware:** Nur dokumentierter Testbefund; weder
Sensor-, Collision-, Footprint-, Scope- noch Motorparameter geändert. Die
lokale reale Geometrie und Sensordaten bleiben außerhalb des Repositorys.

**Teststatus / offene Risiken:** Kein realer Stop-/Weiterfahrnachweis. Der
Kartenmanager-Shutdown ist in diesem Vorlauf nicht sauber. Vor erneutem
Realtest Race reproduzieren/klären und den vollständigen motorlosen Preflight
in frischem SLAM-Kontext wiederholen.
Ein unmittelbar folgender passiver Wiederholungszyklus mit gleichem linkem
Nahpunkt und ohne synthetischen Fahrwunsch stoppte alle 24 Kinder sauber;
Gerätehandles waren frei. Der erste Fehler ist damit intermittierend oder
testablaufabhängig, nicht widerlegt.

**Rückfallweg:** Stack aus und Stufe-3-Overlay in einer neuen Shell auslassen;
der aktive Roboter-Install wurde nicht verändert. Das neue Hindernis vor einer
anderen Testanordnung unbestromt entfernen oder repositionieren.

---

## 2026-09-23 — WE-Stufe 3: lokalen Nav2-Abbruch nur mit positivem Beleg zurückstellen

**Entscheidung:** Die vorhandene Explorer-/Nav2-/Task-Policy-Kette unterscheidet
`LOCAL_BLOCKED` von `SOURCE_INVALIDATED`, Nutzerabbruch und Systemfehler.
Nach terminalem Frontier-Abbruch wird nur mit frischer Costmap-Blockade,
Stillstand und gesunden Sicherheitsquellen die Aufgabe revisionsbegrenzt
zurückgestellt. Derselbe Frontier darf nicht durch eine Costmap-Projektion
sofort wieder als neues Ziel erscheinen. Es gibt keine neue Fahrprimitive.

**Grund / beobachtete Evidenz:** Humble `NavigateToPose.Result` besitzt keinen
Fehlercode. Der R9-Lauf endete bei `Controller patience exceeded` nach
LiDAR/VL53-Costmap-Hindernis; ein pauschales `ABORTED` kann daher weder
ungeprüft als Hindernis noch als Freigabe zum Manöver dienen. Der neue
gerätefreie Prozessfall deckte tatsächlich eine sofortige Wiederwahl von A
über eine benachbarte Costmap-Projektion auf. Erst die Sperre bis zum neu
unprojiziert belegten Originalziel ergab A-Abbruch → B-Erfolg → belegten
Frontierfortschritt → spätere Reaktivierung von A.

**Betroffene Dateien und Hardware:** `explore`-Runtime, Verträge, Profil und
bestehender Gesamtprozessprüfer; keine Motor-, VL53-, Nav2- oder
Collision-Monitor-Konfiguration geändert. Kein Gerät geöffnet, kein Motor
freigegeben und kein Fahrbefehl publiziert.

**Teststatus:** 902 Explorer-Pytests und acht gerätefreie Szenarien des
bestehenden Gesamtprozessprüfers aus dem Quellbaum **und** gegen das isoliert
installierte Stage-3-`explore` bestanden. Vor der Stabilisierung traten in
langen Prüfläufen ein
Pose-Sprung-Flake im älteren Portal-Positivfall und ein Timer-Shutdown-Race
auf; beide sind im WE-Status offengelegt. Kein realer Recovery-Test.

**Offene Risiken:** Der Prozessprüfer ersetzt Nav2 durch einen Fake-Action-
Server und beweist keine physische Ausweichfahrt. Aktive harte Fehler während
eines laufenden Kindes und echter gleicher-Ziel-/Umfahrungs-Replan brauchen
weitere Produktionsnähe. Der R9-Nahbereichsbefund bleibt offen. Keine
Stufe-3-Fahrfreigabe.

**Rückfallweg:** Neues Shell-Environment ohne Stufe-3-Präfix; nur bestätigte
Stufe-1/2-Installkette laden. Vor einer realen Fahrt erneut explizite
Vor-Ort-Freigabe einholen.

---

## 2026-09-23 — WE-Stufe 2: Frontier-Replan muss echte Fortsetzung belegen

**Entscheidung:** Die vorhandene WE-Navigation behält ein sicher und
erreichbar gebliebenes metrisches Ziel trotz Kartenrevision oder bloß neuem
Zeitstempel. Nach echter Quelleninvalidierung stoppt sie das Kindziel und
wartet auf eine neue Policywahl. Ein bereits erfolgreich erreichtes
identisches Frontierziel wird bis zur neuen Rohkartenauflösung nicht erneut
als Kindziel versendet; ein anders belegtes Ziel bleibt möglich.

**Grund / beobachtete Evidenz:** Der bisherige `SOURCE_INVALIDATED`-Unit-Test
bewies nur den Replan-Status vor einem Eltern-Cancel. Der erweiterte echte
Explorer-Prozessprüfer zeigt mit synthetischer ROS-Karte und Fake-Nav2 die
vollständige Kette A laufend → A sicher storniert → B automatisch gesendet → B
erfolgreich → B-Aufgabe auf neuer Karte abgeschlossen, während der
Elternauftrag aktiv bleibt. Mit `max_frontier_goals=1` belegt B zugleich, dass
der Quellenstopp keinen Nav2-/Zielversuch verbraucht. Der erste neue Prüflauf
zeigte eine unnötige erneute Vergabe desselben erreichten B-Ziels; die enge
Integrationssperre beseitigte genau diesen Fall. Der Gegenfall ohne frische
Folgequelle sendet kein B und endet am Gesamtzeitbudget.

**Betroffene Dateien und Hardware:** Nur `explore_node.py`, dessen Vertragstest
und der bestehende Prozessprüfer sind funktional betroffen. Der Code wurde
als einzelnes `explore`-Paket in einem eigenen Overlay auf dem bestätigten
Stufe-1-Präfix gebaut. Keine Hardware wurde geöffnet, keine Motorfreigabe
veranlasst und kein reales Wohnungsprofil ins Repository übernommen. Scope-, Sensor-,
Frische-, Footprint- und Collision-Konfigurationen bleiben unverändert.

**Teststatus:** 893 Explorer-Pytests und der gesamte gerätefreie
Sechs-Szenarien-Prozessprüfer aus dem Quellbaum und dem Stufe-2-Install
bestanden. Der installierte Explorer löst aus dem neuen Präfix auf und ist
bytegleich mit der Quelle. Ein erster Install-Gesamtlauf meldete einmal einen
Timeout des älteren Wiederaufnahme-Traversal-Status; dessen isolierte
Wiederholung und der zweite vollständige Install-Gesamtlauf bestanden.

**Offene Risiken:** Die einmalige Zeitstreuung des älteren Prozessfalls hat
keine bestimmte Ursache; bei erneuter Reproduktion ist sie gesondert zu
untersuchen. Es gibt keine reale Fahrabnahme dieser Stufe. Der reale
linke VL53-Nahbereichsbefund aus R9 ist vor jeder späteren Bewegung vor Ort
zu klären; anschließend wären neuer Preflight und ausdrückliche Freigabe
erforderlich. Mehrraumfahrt und Hindernis-Recovery gehören nicht zu Stufe 2.

**Rückfallweg:** Neue Shell ohne das Stufe-2-Overlay öffnen und WE-Navigation
des älteren Stands bis zur erneuten Prüfung nicht für eine Fahrt freigeben.
Stufe-1-Install, lokale Arbeitskopie und Geräte bleiben unverändert.

---

## 2026-09-23 — WE-Stufe 1 an Quellcommit und Laufzeitpräfix gebunden

**Entscheidung:** Der reproduzierbare motorlose WE-Ausgangsstand ist der
Quellbaum `5e3fe0a084b9b46809e25715d8bdca4c7bd408a4` mit einem isolierten
Zehn-Paket-Overlay über dem vollständigen Release `10e1858`, dem gepatchten
STL-27L-Treiber und dem vorhandenen gepatchten `slam_toolbox`. Der historische
R9-Neun-Paket-Mischstand wird nicht als Stufe-1-Ausgangsstand weiterverwendet.

**Grund / beobachtete Evidenz:** R9 hatte gezeigt, dass der vorhandene
Kartenmanager-Fix `5f821b8` im zunächst verwendeten Overlay fehlen konnte.
Der neue Abgleich ergab, dass zwischen Vollrelease und Zielcommit genau zehn
ROS-Pakete geändert wurden; exakt diese zehn lösen über `ros2 pkg prefix` aus
dem neuen Install auf. Laufzeitdateien in Quelle und Install sind identisch.
Alle bestätigten WE-Korrekturen sind Vorfahren des Zielcommits. Zwei
vollständige motorlose Starts lieferten aktive Nav2-/Collision-Lifecycles,
frische Karte, TF, LiDAR und beide VL53 sowie Explorer- und Safety-Status.
RS485 blieb gesperrt, alle Motorwerte und nichtnulligen Fahrbefehle blieben
null. Beide Einzel-SIGINT-Stopps endeten ohne Traceback oder hängen gebliebenen
Gerätehandle.

**Betroffene Dateien und Hardware:** Dokumentiert sind der isolierte Install
`~/.local/share/amadeus/releases/we1-stage1-5e3fe0a-20260923`, die bestehende
Overlaykette und das lokale WE-Profil nur über Pfad und Hash. Es wurden keine
Produktionsinstallation, keine reale Geometrie und keine Sicherheitsgrenze
geändert. LiDAR und VL53 wurden nur lesend betrieben; `base_hardware` lief im
Dry-run mit `allow_rs485=false`.

**Teststatus:** Zehn-Paket-Build bestanden; 1.002 registrierte Colcon-Tests in
den Paketen mit Testregistrierung und 1.155 direkte Pytests bestanden. Zwei
motorlose Gesamtzyklen bestanden mit etwa 10 Hz LiDAR, 1 Hz Karte und je etwa
4 Hz VL53. Sämtliche Prozesse und LiDAR-, RS485- sowie I²C-Handles waren nach
jedem Stopp frei. Zwei frühere, nicht gewertete Vorläufe mit fehlerhafter
DDS-Testkonfiguration sind vollständig erklärt und wurden in der zulässigen
Domain 217 erfolgreich wiederholt.

**Offene Risiken:** Das ist keine Fahr- oder Hardwareabnahme. Der reale
R9-Nahbereichsbefund an der Endpose bleibt vor jeder späteren Bewegung physisch
zu klären; hardwired Not-Aus, freie Umgebung und neue ausdrückliche
Fahrfreigabe bleiben Pflicht. Stufe 2 wurde nicht begonnen.

**Rückfallweg:** Eine frische Shell verwenden und das Stufe-1-Overlay nicht
sourcen. Vollrelease, alte Overlays, lokale Arbeitskopie, Karten und Profile
blieben unverändert; es ist keine Datei zurückzukopieren und kein Gerät neu zu
konfigurieren.

---

## 2026-09-21 — Reale WE-Fortsetzung braucht festes Ziel und zusammenhängenden Scope

**Entscheidung:** Ein einmal gesendetes Frontierziel bleibt bei neueren
Rohkarten metrisch fest und darf nur weiterlaufen, wenn genau dieses Ziel auf
der neuen Quelle erneut sicher, im autorisierten Scope und geodätisch erreichbar
ist. Quellen-Replans verbrauchen nicht das Nav2-Ergebnisbudget. Die nächste
Realfahrt bleibt bis zur Rückstellung an die ursprüngliche Startmarke oder bis
zu einer neuen lokalen Scope-Vermessung gesperrt.

**Grund / beobachtete Evidenz:** Der freigegebene Erstversuch fuhr etwa 0,466 m
ohne Safety-, Encoder- oder Busfehler, wurde aber auf jeder Kartenrevision wegen
eines neu bevorzugten Kandidaten storniert und endete nach zwölf Replans nur mit
Teilstand. Nach der Korrektur blieb dasselbe Ziel motorlos von Revision 55 bis
119 aktuell. Ein Exaktkartentest an der neuen Pose fand sechs Frontiers ohne
Scope, aber null sicher erreichbare innerhalb des lokalen Polygons. Daher wurde
beim zweiten aktiven Vorlauf kein Auftrag gesendet.

**Betroffene Dateien und Hardware:** Explorer-Ziel-/Quellenprüfung,
Frontier-Scope-Evidenz, Kartenrevisionsadapter und Kartenmanagerstatus samt
Tests. Das reale Profil und beide Bags bleiben lokal. Keine
Produktionskonfiguration, Fahrparameter oder Live-Arbeitskopie wurden ersetzt.

**Teststatus:** Pakettests und motorloser Produktionslauf bestanden; sichere
Bewegung und sauberer Stopp des Erstversuchs belegt. Kein natürlicher realer
Mehrraumabschluss, keine reale Wiederaufnahme und keine Hardwareabnahme.

**Offene Risiken:** Der aktuelle lokale Scope ist von der aktuellen Roboterpose
aus nicht zusammenhängend traversierbar. Seine automatische Erweiterung könnte
unbekannte Treppen- oder Außenbereiche freigeben und ist deshalb verboten.

**Rückfallweg:** Die Zielstabilitätskorrektur zurücknehmen und WE-Navigation
deaktiviert lassen; lokale Bags/Profile bleiben unangetastet. Dann gilt der
beobachtete Cancel-/Budgetblocker wieder als offen.

---

## 2026-09-21 — WE-1 motorloser Zielsystemcheck bestanden

**Entscheidung:** Der motorlose WE-1-Zielsystemcheck gilt auf PR #95 plus den
eng begrenzten Zielsystemkorrekturen als bestanden. Es folgt keine weitere
Softwareentwicklung und keine Fahrt ohne neue persönliche Freigabe.

**Grund / beobachtete Evidenz:** Der einzige rote Vertragstest erwartete noch
den historischen Kreis statt des seit 18.08. real abgenommenen dynamischen
Polygons; nur der Test wurde berichtigt. Die LiDAR-Abbruchursache war eine
reproduzierbare Close-Race: Der Vendor-Treiber schloss und invalidierte den
seriellen Deskriptor vor dem Empfangsthread-Join, sodass der Thread noch
`FD_SET(-1)` erreichen konnte. Der separate Patch initialisiert die Atomics und
schließt erst nach dem Join. Python-Knoten behandeln den bereits durch SIGINT
beendeten Humble-Kontext idempotent; echte RuntimeErrors im gültigen Kontext
bleiben sichtbar. Zwei vollständige Wiederholungen beendeten alle 24 Prozesse
sauber und gaben LiDAR, I²C sowie `/dev/ttyUSB_BASE` frei.

**Betroffene Dateien und Hardware:** Ausschließlich Footprint-Vertragstest,
Shutdown-Hüllen von Basis, VL53, Fahrtor und Kartenmanager, reproduzierbarer
Patch/Builder für den gepinnten STL-27L-Treiber sowie Dokumentation. Keine
Fahrparameter, Produktions-Footprints, Live-Installation oder Aktoren geändert.
Ein begrenztes Profil mit realer Wohnungsgeometrie liegt nur lokal und hält alle
Fahr-Opt-ins bis zur Vor-Ort-Bestätigung auf `false`.

**Teststatus:** Vollständiger isolierter 23-Paket-Build; 1.206 direkte und
1.016 registrierte Tests ohne Fehler/Fehlschlag/Skip; vier bestandene
Produktionsprozessszenarien. Reale gemeinsame Sensor-/SLAM-/Nav2-/Explorer-/
Safety-Last mit 0 Nav2-Zielen und 0 Nichtnull-Fahrbefehlen; atomarer
Kartenmanager- und gebundener WE-Save ohne Durability-Warnung; zwei
aufeinanderfolgende saubere SIGINT-Gesamtstopps.

**Offene Risiken:** Dies ist keine Hardware- oder Fahrabnahme. Der lokale Scope
muss vor Ort nachweislich Treppen, Außenbereiche und andere Gefahren
ausschließen. Not-Aus, freie Tür, Transportpose und Christophers ausdrückliche
Fahrfreigabe bleiben Pflicht.

**Rückfallweg:** Isolierte Overlays nicht sourcen beziehungsweise die
Zielsystemkorrekturen zurücknehmen. Dadurch werden weder bestehender Live-
Install noch Karten- oder Semantikdaten verändert.

---

## 2026-09-16 — WE-Releasekandidatencheck: Rückkehrkette noch nicht produktiv

**Entscheidung:** PR #93 wird nach dem vollständigen Gerätefreireview nicht als
WE-1-Software-Releasekandidat eingefroren. Die 1,25-s-Policyübergabe ist
korrigiert, aber die produktive Kette besitzt keine automatisch auswählbare
Transit-/Rückkehr-Aufgabe für die Gegenrichtung eines bereits bestätigten
Portals.

**Grund / beobachtete Evidenz:** Bei fortlaufenden Rohkarten konnte vorher jede
neue Revision den pending-Handoff verlängern. Der neue Intent-gebundene Timer
endet nach höchstens 1,25 s ab erster ungeprüfter Revision; vier gezielte Fälle
belegen Stream ohne Bestätigung, gleiche Neu-Bestätigung, abweichendes Ziel und
dauerhaft hängende Policy. Der isolierte reale Explorer-Prozess bestand erneut
positiven natürlichen Abschluss, Fail-closed-TF-Fehler und Save/Restart/Resume
ohne Command-Nachrichten. Der Codeaudit der gestapelten Mehrraumkette zeigt
jedoch: bestätigte Durchfahrt schließt `task-portal-<id>`; der Policy-/Kandidat-
pfad erstellt danach keine Rückkehr- oder Transitaufgabe. Der bisherige
Mehrraumtest ruft die Gegenrichtung deshalb direkt am Validator auf und ist kein
vollständiger ExploreNode-Prozessnachweis.

**Betroffene Dateien und Hardware:** Eng begrenzte Explorer-Quellenprüfung und
Regressionstests sowie WE-Status. Keine Fahrparameter, Geräte, reale Karten,
Robotinstallation oder Hardwareprofile geändert.

**Teststatus:** Isolierter Drei-Paket-Build bis `explore`; 853 Explorer-
Colcon-Tests; 1005 gemeinsame Quelltests; Prozesssmoke mit positivem,
Fehler- und Wiederaufnahmeszenario. Der vollständige Mehrraumprozess ist nicht
bestanden, sondern durch den beschriebenen fehlenden Produktionsvertrag blockiert.
Der bekannte vollständige Zielgraph-Build bleibt wegen der fehlenden
`behaviortree_cpp`-Underlay-Bibliothek außerhalb des WE-Paketbefunds offen.

**Offene Risiken:** Ein späterer Transitvertrag darf keine Route, Bewegung oder
Türdurchfahrt fingieren. Er braucht frische Karten-/Routen-/Portalquellen,
eigenständige Fail-closed-Negativfälle und Save/Restart-Identität.

**Rückfallweg:** Den neuen Grace-Schutz oder den gesamten Reviewcommit
zurücknehmen; das bestehende WE-Profil bleibt deaktivierbar. Keine Karten- oder
Semantikdaten werden geändert oder gelöscht.

---

## 2026-09-15 — WE-Softwarekette revisionssicher und passiv wiederaufnehmbar

**Entscheidung:** WE-Ziele überleben neue Kartenrevisionen nur, wenn die neue
exakte Produktionsauswertung dasselbe Ziel identitäts- und metrisch gleich erneut
bestätigt. WE-Zustand wird nach einem erfolgreichen, passenden Kartenmanager-Save
als eigene unveränderliche JSON-Revision gespeichert. Laden bleibt wirkungslos;
Fortsetzung braucht frische Karte/Pose und einen neuen `ExploreArea`-Auftrag.

**Grund / beobachtete Evidenz:** Zuvor stornierte jede neue Revisionsnummer ein
aktives Ziel. Außerdem konnte ein grundsätzlich erfolgreicher Prozess nie
natürlich abschließen, weil bestätigte Portale dauerhaft unbekannte Seiten
behielten. Nach der Korrektur endete der echte Explorer-Prozess natürlich;
Unterbrechung, atomarer Save, Neustart, passives Laden und ausdrückliche
Fortsetzung endeten ebenfalls natürlich. Ein Produktionsdetektor-/Validatorfall
behielt in Startraum → Flur → Zimmer → Flur dieselbe Flur-ID über Save/Restore.

**Betroffene Dateien und Hardware:** Explorer-Laufzeit, reine Portal-/Frontier-/
Graphzustände, neuer WE-Metadatenspeicher, Tests und Prozessprüfer. Keine
Fahrparameter, Geräte, reale Karten, laufende Arbeitskopie oder Installation.

**Teststatus:** 1000 gemeinsame Quelltests; 848 Explorer-Colcon-Tests; drei
Prozessszenarien einschließlich natürlichem Abschluss und Wiederaufnahme;
geänderte reine Module/Tests flake8-sauber. Voller Zielgraph-Build auf dem
Review-PC durch fehlende systemweite `behaviortree_cpp`-Bibliothek blockiert.
Keine Hardwareabnahme.

**Offene Risiken:** Zielsystem-Build/Dateisystem, parallele reale Last,
Chassis-/Portalprofil, Nahbereichsgeometrie sowie WE-M0/B, M4 und M6 bleiben
gesonderte Abnahmen.

**Rückfallweg:** Persistenz- und WE-Navigations-Opt-ins deaktivieren oder diesen
funktionalen Commit zurücknehmen. Karten- und manuelle Semantikdaten werden vom
WE-Speicher nicht überschrieben.

---

## 2026-09-14 — WE-Portalfortschritt an echten Prozessbeleg gebunden

**Entscheidung:** Das separat aktivierbare WE-Profil versendet Portalziele nur
mit verifiziertem Scope und vollständig gesetztem, eingefrorenem
LiDAR-Traversierungsmonitor. Erst ein bestätigtes Ereignis darf Region und
Portalaufgabe atomar fortschreiben. Das optionale Scope-Polygon besitzt im
ROS-Knoten ausdrücklich den Typ `DOUBLE_ARRAY`; ein leeres, typmehrdeutiges
Standard-YAML-Array wird nicht gesetzt.

**Grund / beobachtete Evidenz:** Ein isolierter Prozesslauf des echten
`ExploreNode` mit synthetischem Kartenmanagerstatus, Rohkarte, TF/Scan und
Fake-Nav2 fand drei durch Objekt-Fakes verdeckte Nähte: falsche ROS-Array-
Typableitung, fehlende Portalsnapshot-Delegation des Lifecycle-Besitzers und
fehlende monotone Zeit beim Ereignisaufruf. Nach der Korrektur beendete der
Positivlauf die Portalaufgabe und betrat genau eine neue Region. Fehlendes
exaktes TF stornierte das einzige Kindziel, ließ die Portalaufgabe offen und
erzeugte keinen Eintritt. Beide Läufe beobachteten null Command-Nachrichten.

**Betroffene Dateien und Hardware:** Eng begrenzte Explorer-Parameter-,
Lifecycle- und Ereignisnaht, zugehörige Tests sowie gerätefreier Prozessprüfer;
keine Fahrsoftware, Geräte, reale Karten oder Installation verändert.

**Teststatus:** 1053 angrenzende Quelltests; frischer Drei-Paket-Aufbau mit 875
Tests ohne Fehler; positiver und abbrechender Prozesslauf in isolierter
ROS-Domain. Das sind Softwarebelege, keine Chassisvermessung, Fahrt oder
Hardwareabnahme.

**Offene Risiken:** Profilwerte sind synthetisch. Parallele SLAM-/Nav2-/
Sicherheitslast, reale Kartenrevisionsfrequenz und motorlose
Zielprofilintegration bleiben offen.

**Rückfallweg:** Gestapelten WE-M3/U-Commit zurücknehmen oder WE-Navigation und
Portalmonitor deaktiviert lassen. Ohne explizites Scope- und Monitorprofil wird
kein Portalziel versandt.

---

## 2026-09-14 — Kartenfingerprint in azyklisches Blattpaket extrahiert

**Entscheidung:** Die kanonische, ROS-unabhängige Fingerprintberechnung liegt im
neuen Blattpaket `amadeus_map_identity`. `robot_map_manager.MapSnapshot` und der
reine WE-M2-Portalquellenadapter verwenden dieselbe Funktion. Der
`source_stamp_ns` bleibt bewusst getrennt von der Inhaltsidentität.

**Grund / beobachtete Evidenz:** Ein Direktimport von `robot_map_manager` in
`explore` würde den vorhandenen Paketpfad
`robot_map_manager → robot_navigation → explore` zyklisch schließen. Eine
zweite Digestimplementierung könnte unbemerkt von gespeicherten Karten- und
Semantikfingerprints abweichen. Der bekannte Kartenmanagervektor blieb nach der
Extraktion bytegleich; Colcon listet das neue Paket vor beiden Verbrauchern.

**Betroffene Dateien und Hardware:** Neues reines Python-Paket
`amadeus_map_identity`; Fingerprintaufruf und Paketmetadaten in
`robot_map_manager`; reiner Quellenadapter und Paketmetadaten in `explore`;
Inventar und Wohnungserkundungsstatus. Keine ROS-Callbacks, Kartenformate,
Geräte, Navigation oder Fahrsoftware geändert.

**Teststatus:** Bekannte Digestvektoren, vollständige Kartenmanager-/Explorer-
Quelltests, angrenzende Semantikverträge und isolierter Drei-Paket-Build
bestanden. Dies ist kein Jetson-Deployment und keine Hardwareabnahme.

**Offene Risiken:** Der Explorer erzeugt noch keine normalisierte
Rohkartenidentität aus einer ROS-Nachricht. Laufzeit- und Speicherwirkung dieser
späteren opt-in Berechnung sind vor Aktivierung auf dem Zielsystem zu messen.

**Rückfallweg:** Gestapelten WE-M2/X-Commit zurücknehmen. Dadurch verwendet der
Kartenmanager wieder seine vorherige interne, inhaltlich identische
Fingerprintberechnung; Karten-IDs und gespeicherte Artefakte benötigen keine
Migration.

---

## 2026-08-26 — OAK-RGB-D-Dauerstream entkoppelt und selbstheilend

**Entscheidung:** Die OAK-D-S2 liefert im Semantik-/SLAM-Profil real
640 x 360 bei 10 Hz. Die RGB-Entzerrung laeuft ausserhalb des DepthAI-
Komponentencontainers im eigenen `oak_rectifier`; Bild und CameraInfo werden
unabhaengig mit Best-Effort/KEEP_LAST(1) empfangen. CameraInfo ist die stabile
Kalibrierung und wird nicht mehr fuer jedes Bild per Exact-Sync erzwungen.

Der KI-Server darf keine OAK-Rohbilder abonnieren. Ein lokaler
`semantic_stream_relay` waehlt aus begrenzten Puffern nur frische, per
Quellzeitstempel passende RGB-/Tiefenpaare und sendet 2 Hz als JPEG plus
verlustfreies 16UC1-PNG. Server und Relay lehnen Bilder ueber 2 s sowie mehr
als 0,20 s RGB-/Tiefenversatz fail-closed ab. DepthAIs geraeteinterne
Synchronisierung bleibt aus, weil sie im Realtest wiederholt etwa 10 s lange
RGB-Luecken erzeugte. Bleibt ein lokaler CycloneDDS-Bild- oder Tiefenendpunkt
mehr als 3 s still, wird nur diese Best-Effort-Subscription mit 5 s Cooldown
neu aufgebaut; jeder Eingriff steht gezaehlt im Status.

**Grund / beobachtete Evidenz:** `i_width/i_height=640x360` skalierte beim
Humble-Treiber nur Metadaten; `/oak/rgb/image_raw` blieb tatsaechlich
1280 x 720. Erst der explizite ISP-Faktor 1/3 lieferte real 640 x 360. Direkte
Offboard-Rohbildabonnenten drueckten den lokalen RGB-Pfad von rund 30 Hz auf
unter 1 Hz. Im alten gemeinsamen Container fiel RGB nach 17 min 18 s mit
`No Data` aus, ohne zeitgleichen Kernel-USB-Reset.

Ein getrennt gestarteter Standard-`image_proc`-Rectifier verlor in einem
weiteren A/B-Lauf nach rund 8,5 min dauerhaft nur seine Bildseite, waehrend
dasselbe `/oak/rgb/image_raw` nachgemessen mit 10,0 Hz weiterlief. Der eigene
Entzerrer ohne CameraSubscriber-Synchronisierung beseitigt diesen Pfad. Im
anschliessenden langen Lauf blieb die OAK insgesamt 33 min 49 s aktiv; es gab
nach dem absichtlichen USB-Neuaufbau beim Start keinen Reset, Disconnect oder
DepthAI-Fehler. Das Vollbild war symmetrisch, 640 x 360 und enthielt das gesamte
gemessene Sichtfeld. Feste OpenCV-Remap-Tabellen benoetigten im Jetson-Benchmark
4,24 statt 5,38 ms pro Bild (21 % schneller).

Der erste Relay-Endpunkt verlor nach rund 11 min nur Tiefe (`rgb_queue=80`,
`depth_queue=0`), obwohl ein neu gestarteter Subscriber dasselbe Tiefentopic
sofort mit 8--9 Hz empfing. Ein frisch erzeugter Relay lief danach real
17 min 31 s ueber die fruehere Grenze: 2.068 publizierte Paare, 36 verworfene
Timerzyklen, null stale RGB-/Tiefenframes, null Codecfehler, zuletzt 0,077 s
Publikationsalter und `ready=true`. Zwei isolierte Wiederanlauftests pausierten
jeweils Tiefe beziehungsweise RGB fuer 2,5 s. In beiden Faellen wurde exakt
der betroffene Endpoint einmal neu aufgebaut und lieferte danach wieder Daten;
der Endstatus war `ready=true` und ohne Codec-/Bildfehler.

Der RTX-Knoten wurde fuer den Positivtest mit leerem Objektgedaechtnis gestartet.
Die sichtbare Tasse wurde neu mit Konfidenz 0,694 erkannt und im motorlosen
Testframe `base_link` plausibel bei `(1,259; 0,051; 0,831) m` projiziert. Das
ist eine echte RGB-D-/CUDA-/TF-Projektion, keine globale Kartenlokalisierung.

**Betroffene Dateien und Hardware:** OAK-Profile und `oak.launch.py` in
`robot_bringup`; eigener Entzerrer samt Status; komprimierender Relay,
Codec/Pairing und Servereingang in `semantic_perception`; OAK-D-S2, Jetson,
WLAN und RTX 3090. Keine Karte oder Aufnahme liegt im Repository. Motor-,
Nav2-, VL53- und Missionsknoten waren waehrend aller Tests aus.

**Teststatus:** 24 direkte Semantiktests und 7 Bring-up-Tests bestanden,
einschliesslich verlustfreier 16-Bit-Tiefe, Frische-/Skew-Grenzen,
ISP-Vertrag, Aufloesungssperre und Watchdog-Zeitlogik. Beide Pakete bauten im
isolierten Jetson-Overlay. Zusaetzlich bestanden die zwei realen, synthetisch
unterbrochenen ROS-Wiederanlauftests, der 33:49-min-OAK-Lauf, der
17:31-min-Relay-Lauf, Vollbildsichtkontrolle und die frische positive
Tassenpose. Das Abschalten erfolgte per Einzelsignal an die Elternprozesse;
DepthAI endete sauber. Das Produktionsdeployment ist getrennt im
`ROBOT_TRANSFER.md` protokolliert. Dabei wurden beide Pakete als normale
Kopien im Jetson-Produktions-Install und `semantic_perception` auf dem
KI-Server installiert. Der Produktionsdienst und ein weiterer motorloser
OAK-Start bestaetigten dieselben komprimierten Topics, 640 x 360, frische
Statuswerte und den erwarteten fail-closed `map`-Service ohne Lokalisierung.

**Offene Risiken:** 640 x 360 nutzt das volle Sichtfeld, aber nicht die volle
Sensor-Pixelaufloesung. Eine spaetere hoehere Objekterkennungsaufloesung braucht
einen eigenen Bandbreiten-, CPU-, Temperatur- und Dauertest. Ein
`subscription_restarts`-Zaehler groesser null ist ein geheilter Transportfehler,
aber weiterhin eine Diagnose, die beobachtet werden soll. Fuer eine Pose im
`map`-Frame muss die reale Lokalisierung separat bestaetigt sein.

**Rueckfallweg:** Relay mit `semantic_relay:=false` abschalten oder den Commit
revertieren und beide Pakete neu bauen. Der KI-Server bleibt ohne frische
komprimierte Bilder fail-closed. Bei einem Rueckfall auf den alten Rectifier
muss dessen gemessener Spaetausfall einkalkuliert werden; OAK, Server und
Navigation koennen weiterhin getrennt gestoppt werden.

---

## 2026-08-25 — Deutsche Objektanfrage liefert reale OAK-3D-Pose

**Entscheidung:** App, Behavior Tree und Service verwenden weiterhin die
deutschen kanonischen Objektklassen (`Tasse`, `Flasche`, ...). Fuer
YOLO-World/CLIP werden sie positionsgleich auf robuste englische Modell-Prompts
(`cup`, `bottle`, ...) abgebildet. Die Zuordnung muss vollstaendig,
eineindeutig und frei von Leerwerten sein; andernfalls startet der Node nicht.
Die bestehende Konfidenzschwelle 0,35 bleibt unveraendert.

**Grund / beobachtete Evidenz:** Auf demselben lokal gehaltenen 640-x-360-
OAK-Bild war die rosa Tasse auf einem Stuhl klar sichtbar. Ein isolierter
A/B-Lauf auf der RTX 3090 lieferte mit einem gemischten Vokabular fuer `cup`
Konfidenz 0,322, fuer `Tasse` dagegen nur 0,029 und eine falsche, fast
bildgrosse Box. Mit dem exakten englischen Betriebsvokabular stieg derselbe
korrekte `cup`-Treffer auf 0,396. Das Problem war damit der Text-Prompt, nicht
Tassenposition, Kamera, CUDA oder die bestehende Schwelle.

Nach dem Softwarefix meldete der laufende Server wiederholt nur noch den
fehlenden Transform `oak_rgb_camera_optical_frame -> map`. Damit waren
2D-Treffer und gueltiger Tiefenwert bereits belegt. Fuer einen rein motorlosen
Endtest lief kurz ein ausdruecklich kuenstlicher Identitaets-TF
`map -> base_link`; zuvor waren weder Karten-TF noch Motor-, Nav2- oder
Missionsknoten vorhanden. `GetObjectPose(Tasse)` antwortete danach mit
`found=true`, Konfidenz 0,4048 und der Testkoordinate
`(x=1,621; y=-0,308; z=0,555) m`. Hoehe und Entfernung waren fuer die Tasse
auf dem Stuhl plausibel. Diese Pose beweist Projektion und TF-Kette, nicht die
globale Roboterlokalisierung. Der Test-TF wurde sofort beendet und der
KI-Dienst neu gestartet, damit die kuenstliche Pose nicht im Objektgedaechtnis
bleibt. Der abschliessende Serviceaufruf lieferte ohne echten Karten-TF wieder
fail-closed `found=false`.

**Betroffene Dateien und Hardware:** `semantic_perception_node.py`, Parameter,
neun Backend-/Prompt-Vertragstests, Paket-README, Inventar und
Uebergabedokumentation. Real beteiligt waren OAK-D-S2, WLAN und RTX 3090.
Keine Motor-, Navigations- oder Kartenkomponente lief; Kamerabild und
Testkoordinaten wurden nicht als Datei ins Repository aufgenommen.

**Teststatus:** Neun direkte Tests, Python-Kompilierung, YAML- und
Whitespacepruefung sowie Colcon-Build auf Jetson/Python 3.10 bestanden. Auf
dem KI-Server bestanden dieselben neun Tests und der normale Colcon-Build unter
Python 3.12. Ein Symlink-Build ist dort mit der vorhandenen
Setuptools-Kombination nicht kompatibel (`--editable`/`--uninstall`); der
bewaehrte normale Installationsmodus baut das Paket sauber. Der Live-Test
bestaetigte englisches Modellvokabular, echte OAK-Box, Tiefe, Kamera-TF,
positive 3D-Serviceantwort und anschliessenden fail-closed Endzustand.

Der anschliessende Dauerbetrieb deckte getrennt einen offenen Kamerafehler auf:
Die 640-x-360-Pipeline war ab `22:19:39` bereit und meldete nach 17 min 18 s
erstmals `Camera diagnostics error: No Data`. Danach kam die Meldung alle etwa
fuenf Sekunden. Im Kernel-Log steht zum Fehlerbeginn weder USB-Reset noch
Disconnect; der physische USB-Disconnect erschien erst beim spaeteren
erzwungenen Prozessende. Der DepthAI-Komponentencontainer reagierte weder auf
SIGINT noch SIGTERM und wurde vom Launch nach dessen normalen Fristen per
SIGKILL beendet. Damit ist der positive Objekttest gueltig, ein stabiler
640-x-360-Dauerstream aber noch nicht abgenommen. Ob DDS-Rueckstau,
Treiber/Pipeline oder eine andere Lastkopplung die Ursache ist, ist nicht
gemessen entschieden.

**Offene Risiken:** Eine positive Pose im echten `map`-Frame verlangt
gleichzeitig die reale, bestaetigte Lokalisierung. Die 640-x-360-Aufloesung war
fuer die Referenztasse ausreichend, ist nach dem spaeten `No Data` aber noch
nicht dauerstabil. Vor jeder Aufloesungserhoehung muss ein isolierter
Dauer-A/B-Lauf lokalen Kamerabetrieb, Offboard-Subscriber und Inferenzlast
trennen. Ein dauerhaftes semantisches Hochaufloesungsprofil ist noch nicht
vermessen. 1920-x-1080-RGB plus
ausgerichtete Tiefe ungefiltert ueber WLAN wuerden Bandbreite und Inferenzlast
stark erhoehen. Das wird als getrennte Sensorkonfigurationsaenderung mit
komprimierten oder bedarfsgesteuerten Schluesselbildern bewertet, nicht in
diesen Prompt-Fix gemischt. Der Hintergrundscan fuehrt weiterhin eine
Vorhersage je Klasse aus.

**Rueckfallweg:** Den Prompt-Commit revertieren und `semantic_perception` im
normalen Modus neu bauen. Kamera und KI-Dienst koennen getrennt beendet
werden. Ohne echten Karten-TF bleibt die reale Antwort fail-closed; fuer
Trockentests ist weiterhin ausschliesslich `model_backend: stub` zulaessig.

---

## 2026-08-25 — OAK-zu-RTX-Wahrnehmung fail-closed und live verbunden

**Entscheidung:** Ein reales `semantic_perception`-Backend darf bei fehlendem
Bild, Tiefe, CameraInfo, TF, Modell oder einer leeren Detektion niemals auf die
simulierte Stub-Pose zurueckfallen. Der Stub ist nur noch mit dem expliziten
Parameter `model_backend: stub` aktiv. YOLO-World erhaelt die konfigurierten
Klassen genau einmal vor dem ersten CUDA-Lauf; jede Antwort wird danach gegen
die tatsaechliche Box-Klasse gefiltert. Jetson und KI-Server verwenden fuer
Custom-Services dieselbe CycloneDDS-Middleware und feste WLAN-Peers.

**Grund / beobachtete Evidenz:** Der laufende Server war auf `yoloworld`
konfiguriert, meldete aber ohne einen einzigen Kamera-Publisher eine Tasse an
der festen Stub-Pose `(1,0; 0,0; 0,5) m` mit Konfidenz 0,8 und fuehrte alle
fuenf Klassen unter `seen`. Nach dem Fail-closed-Fix ergab dieselbe Anfrage
`found=false`, Konfidenz 0 und `seen=[]`.

Ein zweiter A/B-Test zeigte, dass ein Jetson-Client ueber Fast DDS beim
benutzerdefinierten `GetObjectPose`-Service einen leeren Request am Server
ausloeste und keine Antwort erhielt. Nach Installation von
`rmw_cyclonedds_cpp` und Start mit demselben CycloneDDS-Profil wurde `Tasse`
unveraendert uebertragen und die Antwort empfangen. Standardtopics allein
hatten diesen Interoperabilitaetsfehler zuvor verdeckt.

Im ersten echten OAK-Lauf kamen rektifizierte RGB-Bilder mit etwa 13 bis
20 Hz auf dem Server an. Dabei wurden zunaechst die nicht deklarierte
Ultralytics-CLIP-Abhaengigkeit und danach wiederholtes `set_classes()` als
CPU/CUDA-Mischfehler sichtbar. CLIP ist nun auf Commit `68dce32140994dfcb645a1320c4ebdc034fc19fd`
gepinnt; das gemeinsame Klassenvokabular wird einmalig gesetzt. Der finale
Mehrzyklustest nutzte die RTX 3090 mit rund 2,1 GB VRAM ohne CLIP-,
Auto-Install- oder Device-Fehler. Eine Live-Serviceanfrage antwortete in rund
zwei Sekunden korrekt `found=false`, weil keine bestaetigte Tasse samt
Karten-TF vorlag.

Der getrennte LLM-End-to-End-Test schickte anschliessend die Anweisung
`Erkunde bitte die Wohnung` ueber WLAN an Qwen 2.5/Ollama. Nach rund 2,4 s
publizierte `llm_planner` exakt `{"type":"explore"}` und den Status
`dispatched`. `/mission_manager/command_json` hatte dabei keinen Subscriber;
auf dem Jetson liefen weiterhin keine Roboter- oder Fahrknoten. Damit sind
Sprachmodell, Parser, Validator und DDS-Ausgabe belegt, nicht jedoch eine reale
Missionsausfuehrung durch diesen Test.

**Betroffene Dateien und Hardware:** `semantic_perception_node.py`, sieben
Backend-/Klassenfiltertests, Paket-README, reproduzierbares Pixi-Beispiel im
`robot_bringup` sowie dieses Projektgedaechtnis. Real beteiligt waren die
OAK-D-S2 am Jetson, WLAN und die RTX 3090. Auf dem Jetson wurden das
CycloneDDS-RMW-Paket und ein lokales Peer-Profil installiert; auf dem Server
liegt die gepinnte CLIP-Abhaengigkeit in der Pixi-Konfiguration ausserhalb des
Repositories. Keine Motor-, Karten- oder Navigationskomponente lief.

**Teststatus:** Python-Kompilierung, sieben direkte Unittests, Build und
Colcon-Test auf Jetson/Python 3.10 sowie KI-Server/Python 3.12 bestanden.
Der motorlose Live-Test bestaetigte USB 3, OAK-D-S2, RGB/Depth/CameraInfo,
passende Reliable-QoS, WLAN-Datenrate, CUDA-Modelllauf, fail-closed Service und
sauberes Kamera-Shutdown. Eine frische Jetson-Shell waehlt persistent
CycloneDDS und bestand den Custom-Service-Test; der KI-Dienst blieb aktiv.
Der motorlose LLM-Vertrag bestand zusaetzlich Anweisung, Ollama-Antwort,
Validierung, Auftrags-Topic und Status-Topic ohne Missionsempfaenger.

**Offene Risiken:** Noch nicht abgenommen ist ein positiver Treffer mit real
sichtbarem Referenzobjekt, gueltiger Tiefe und gleichzeitig vorhandenem
`map -> base_link -> camera`-TF. Erst dieser Test darf eine reale 3D-Objektpose
freigeben. Der Hintergrundscan fuehrt derzeit fuer jede der fuenf Klassen eine
eigene Vorhersage aus; eine spaetere Ein-Pass-Auswertung kann die GPU-Last
senken, darf aber den Klassenfilter nicht umgehen. Die realen Peer-IPs und
systemd-/Pixi-Dateien bleiben absichtlich lokale Deploymentkonfiguration.

**Rueckfallweg:** Den Wahrnehmungs-Fix revertieren und den Serverdienst neu
bauen; fuer Trockentests stattdessen bewusst `model_backend: stub` setzen.
Die Jetson-Shellvariablen lassen sich entfernen, ohne ROS-Pakete zu loeschen;
ohne gemeinsames RMW sind benutzerdefinierte WLAN-Services jedoch nicht
freigegeben. Kamera und KI-Server koennen jederzeit getrennt gestoppt werden;
Navigation und Sicherheit laufen davon unabhaengig onboard.

---

## 2026-08-25 — Offboard-Nodes unter CycloneDDS sauber beendet

**Entscheidung:** `llm_planner` und `semantic_perception` behandeln beim
externen Dienststopp neben `KeyboardInterrupt` auch
`ExternalShutdownException`. `rclpy.shutdown()` wird nur noch aufgerufen,
solange der Kontext aktiv ist.

**Grund / beobachtete Evidenz:** Beim kontrollierten Neustart des
KI-Server-Dienstes beendete CycloneDDS den ROS-Kontext vor dem Python-Spin.
Beide Nodes meldeten deshalb erst `ExternalShutdownException` und danach einen
zweiten Fehler fuer `rcl_shutdown already called`, obwohl der Neustart
funktional gelang. Der Guard trennt diesen normalen Dienststopp von echten
Laufzeitfehlern.

**Betroffene Dateien und Hardware:** Einstiegspunkte von `llm_planner` und
`semantic_perception`; keine Roboter-Hardware und keine Bewegungssteuerung.

**Teststatus:** Python-Kompilierung, alle 15 Sprachplaner-Tests, erneuter Build
beider Pakete und ein kontrollierter systemd-Neustart ohne Traceback bestanden.

**Offene Risiken:** Fehler waehrend der eigentlichen Node-Ausfuehrung bleiben
weiterhin sichtbar und fuehren zum Dienstneustart.

**Rueckfallweg:** Diesen Commit revertieren; dadurch kehren nur die
Shutdown-Tracebacks zurueck. ROS-Schnittstellen und Modellparameter bleiben
unveraendert.

---

## 2026-08-25 — LLM-JSON-Tiefenlimit unter Python 3.12 explizit gemacht

**Entscheidung:** Der Offboard-Sprachplaner begrenzt verschachtelte
LLM-JSON-Antworten jetzt unabhaengig von der Python-Laufzeit auf 64 Ebenen.
Der Extraktor beruecksichtigt dabei Strings und Escape-Sequenzen, bevor er das
erste vollstaendige JSON-Objekt an `json.loads` uebergibt.

**Grund / beobachtete Evidenz:** Der vorhandene Negativtest mit 1.500
Verschachtelungsebenen verliess sich indirekt auf `RecursionError`. Python 3.12
akzeptierte dieselbe Struktur, sodass sie bis zur Auftragsvalidierung gelangte.
Eine feste Grenze erhaelt den fail-closed-Vertrag ueber Python-Versionen hinweg.

**Betroffene Dateien und Hardware:** `llm_planner_node.py` und dieser Eintrag.
Nur der asynchrone Offboard-Planer ist betroffen; keine Aktoren oder
Roboter-Hardware wurden angesprochen.

**Teststatus:** Alle 15 direkten `llm_planner`-Tests unter Python 3.12 sowie
Python-Kompilierung bestanden, einschliesslich tiefem JSON, ungueltigem Unicode
und gueltigem JSON mit Praefixtext.

**Offene Risiken:** Der Planer bleibt eine High-Level-Komponente. Jeder neue
Auftragstyp muss weiterhin separat in `_validate()` freigegeben werden.

**Rueckfallweg:** Diesen Parser-Commit revertieren. Dadurch gilt wieder das
laufzeitabhaengige Rekursionsverhalten; Motor-, Navigations- und
Sicherheitskonfigurationen bleiben unveraendert.

---

## 2026-08-18 — Mehrraum-Uebergang erreicht; Portalwechsel robust gemacht

**Entscheidung:** Der Explorer behandelt eine durch Inflation kuenstlich in
zwei Costmap-Komponenten getrennte Tuer als begrenztes Portal. Normale,
unprojizierte Frontier-Ziele bleiben immer vorrangig. Nur wenn alle
Frontier-Ziele auf die aktuelle Komponente zurueckprojiziert werden, darf der
Explorer ein benachbartes, ausreichend grosses Gebiet ueber eine begrenzte
Bruecke anfahren. Vor einer direkten Bruecke sind weiterhin eine frische
vollbreite LiDAR-Korridorpruefung, Missions-Gate, Geschwindigkeitsglaettung und
Kollisionsmonitor vorgeschrieben; der reale Fortschritt wird aus einem
eingefrorenen LiDAR-Referenzscan statt nur aus den auf Schwellen schlupfenden
Radencodern bestimmt. Wird die Tuer waehrend der Nav2-Anfahrt durch neue
Kartenevidenz regulaer verbunden, ist das kein Fehler mehr: Der urspruengliche
Fernseitenpunkt muss nun exakt in der Roboterkomponente liegen, danach
uebernimmt der normale Nav2-Pfad bis mindestens eine halbe Auslaufreserve
hinter diesem Punkt. Ungeklaerte Frontiers oder Portale verhindern weiterhin
`map_ready_to_save=true`.

**Grund / beobachtete Evidenz:** Der erste scharfe Portallauf erkannte vor der
Fahrt genau einen Uebergang: Zielgebiet 0,887 m2, Costmap-Luecke 0,488 m,
Nav2-Anfahrt 0,454 m und begrenzte Bruecke 0,797 m. Nach 0,347 m realer
Anfahrt wuchs die Karte. Die bislang getrennten Gebiete bildeten danach eine
einzige 2,251-m2-Komponente; Roboter, alter Anfahrpunkt und alter Zielpunkt
lagen alle in Label 1. Der alte Zielpunkt bei etwa `(1,001, 0,025) m` hatte
Kosten 90 und war regulaer erreichbar. Die fruehere Prüfung deutete das
Verschwinden des Portalobjekts trotzdem als `portal_geometry_changed` und
stoppte bei 0 rpm. Das war ein falscher Fehlerzustand, nicht eine blockierte
Tuer.

Nach der Korrektur und einem motorlosen Start plante der echte Nav2-Stack aus
der bereits vorgerueckten Position ein normales Frontier-Ziel bei
`(1,05, 0,05) m` im Folgeraum. Im beaufsichtigten Realtest meldete Nav2 dieses
Ziel als erreicht; der Explorer zaehlte eine besuchte Frontier. Die Basis
endete bei Encoderpose `x=1,018 m`, `y=-0,102 m`, `yaw=0,398 rad`, beiden
Motoren 0 rpm, fehlerfreiem RS485 und fehlerfreien Encodern. Die Karte wuchs
waehrend der Fahrt deutlich; zum Stoppzeitpunkt waren 23,70 % der aktuellen
sicheren Komponente durch die Fahrspur abgedeckt. Eine nur fuer diese Abnahme
temporär aktivierte harte Vorwaertsbegrenzung verwarf danach drei seitliche
Frontiers, weshalb die Gesamtmission korrekt als unvollstaendig endete. Diese
Begrenzung gehoert nicht zum Wohnungsprofil und wurde wieder entfernt. Die
sensorische Mehrraumfahrt ist damit nachgewiesen. Der anwesende Beobachter
bestaetigte anschliessend, dass der Roboter die Schwelle vollstaendig verlassen
und den Folgeraum real erreicht hatte. Damit stimmen Nav2-Erfolg, Sensorik und
aeussere Sichtpruefung ueberein.

**Betroffene Dateien und Hardware:** `explore_node.py`, neue Module
`portal_planning.py` und `lidar_motion.py`, Explorer-Parameter und Tests,
Missions-Gate-/Nav2-Vertraege sowie diese Dokumentation. Der Realtest nutzte
STL-27L, beide VL53, SLAM, Nav2, Polygon-Footprint, Kollisionsmonitor,
Encoder-Odometrie und beide ESS23-RS-Antriebe. Karte und Wohnungsgeometrie
blieben ausschliesslich lokal.

**Teststatus:** 58/58 Explorer-Tests bestanden, darunter synthetische
Portalgeometrie, LiDAR-Korridor, eingefrorene Scanbewegung, Nav2-Uebergabe bei
zusammengewachsener Costmap und fail-closed Gegenfaelle. Der gesamte aktuell
registrierte Bestand meldet 165 Tests, 0 Fehler, 0 Fehlschlaege und 0
Auslassungen. Vor der realen Fahrt: `dry_run=false`, `allow_rs485=true`,
`rs485_ready=true`, Encoderfeedback frisch, 0 rpm, LiDAR 10,8 Hz und beide
VL53 3,8 Hz. Nach der Fahrt erneut 0 rpm; der Stack wurde ueber genau ein
Ctrl-C am Launch-Elternprozess beendet.

**Offene Risiken:** Ein einzelner Wechsel beweist noch keine vollstaendige
Wohnungserkundung. Als naechstes muss das unbeschraenkte Wohnungsprofil aus
dem erreichten Folgeraum mehrere Frontiers und weitere Tueren bedienen. Die
Portal-Direktbruecke wurde real noch nicht ausgefuehrt, weil die Live-Karte die
Tuer rechtzeitig regulaer fuer Nav2 verband. Schwellen und Teppiche bleiben
Schlupfquellen; deshalb darf der direkte Portalpfad nicht auf Encoderabschluss
zurueckfallen.

**Rueckfallweg:** `portal_crossing_enabled: false` deaktiviert nur die neue
Portalbruecke; normale Frontier-Navigation bleibt erhalten. Der sicherste
Funktionsrueckfall ist `enable_auto_explore:=false` oder
`active_drive:=false`. Der neue Verbundenheitswechsel kann separat entfernt
werden; dann stoppt ein waehrend der Anfahrt zusammengewachsenes Portal wieder
fail-closed mit `portal_geometry_changed`.

---

## 2026-08-18 — Vermessener, tuergaengiger Polygon-Footprint

**Entscheidung:** Die lokale reale Nav2-Costmap verwendet die am 18.08.2026
relativ zur mittigen Antriebsachse gemessene, asymmetrische Plattformkontur:
Chassis vorn +0,27 m, hinten -0,11 m und seitlich +/-0,23 m. Weil die bekannten
VL53-Frames bei x=+0,29 m liegen und ihr Modell bis +0,305 m reicht, umfasst die
sichere Rechteckhuelle x=-0,11..+0,31 m und y=+/-0,23 m. Dazu kommen 0,02 m
Padding. NavFn bleibt als bewaehrter 2D-Planer vorerst global kreisfoermig;
sein Radius sinkt von 0,40 auf 0,28 m (halbe Breite plus 0,05 m Reserve). Der
Kartierungs-`collision_monitor` uebernimmt dynamisch den lokalen
Polygon-Footprint. Die
Explorer-Ziel- und Abdeckungsmaske wird kreisfoermig statt mit einem
quadratischen Fenster erodiert; die Abdeckungsreserve sinkt passend auf
0,28 m. Die etablierte Frontier-Methode bleibt Grundlage der
Wohnungserkundung; ein Raumgraph oder Smac State Lattice folgt nur nach einem
reproduzierbaren Bedarf.

**Grund / beobachtete Evidenz:** Der Wohnungslauf beendete sich formal mit
86,21 %, obwohl der Roboter den Startraum nicht verlassen hatte. Es lag kein
Motor-, Encoder-, Sensor- oder Nav2-Fehler vor. Die alte 0,40-m-Quadratmaske
trennte die lokale Karte am Tuerbereich und zaehlte nur einen Teil des bereits
kartografisch freien Raums als erreichbar. Auf demselben nur lokal gehaltenen
Kartenschnappschuss vergroesserte die kreisfoermige 0,30-m-Maske die groesste
zusammenhaengende sichere Komponente deutlich und verband zuvor getrennte
Bereiche. Nav2 empfiehlt fuer nicht kreisfoermige Roboter den geometrischen
Footprint; NavFn selbst bleibt jedoch ein 2D-Planer, weshalb lokales Polygon
und globales Breitenmodell getrennt sind. Die nachgemessene schmalste Tuer ist
0,68 m breit. Gegenueber der 0,50-m-gepaddeten Plattformbreite bleiben 0,18 m
Gesamtreserve, gegenueber dem globalen 0,56-m-Kreis 0,12 m.

**Betroffene Dateien und Hardware:** `nav2_params_real.yaml`,
`collision_monitor_mapping_params.yaml`, `explore_node`, Explorer-Parameter
und Tests sowie `docs/WOHNUNGSERKUNDUNG_STRATEGIE.md`. Der motorlose Live-Test
startete STL-27L, beide VL53, SLAM, Nav2 und `collision_monitor`; RS485 und
Antrieb blieben aus. Keine echte Karte wurde ins Repository uebernommen.

**Teststatus:** 33 gezielte Footprint-/Explorer-Tests bestanden. Nachdem die
vorhandenen Tests korrekt in `colcon test` registriert wurden, bestanden
19/19 Explorer-, 31/31 Navigations- und 3/3 Bring-up-Tests, zusammen 53 Tests
ohne Fehler, Fehlschlaege oder Auslassungen. Vier betroffene Pakete bauten erfolgreich;
das Xacro ist gueltig. Im Jetson-Dry-run publizierte Nav2 exakt die gepaddeten
Ecken `x=-0,13..+0,33 m`, `y=+/-0,25 m`; der Kollisionsmonitor publizierte
dieselben vier Punkte im `base_link`-Frame. Globaler Radius sowie Explorer-
Ziel- und Abdeckungsabstand waren zur Laufzeit jeweils 0,28 m.
`base_hardware` meldete durchgehend `dry_run=true` und 0 rpm. Der Stack wurde
danach ueber den Launch-Prozess beendet; danach waren keine Amadeus-Knoten
aktiv. Abschliessend plante der reale NavFn-Stack auf einer temporaeren
3-cm-Synthetikkarte geradlinig von x=-0,75 m nach x=+0,75 m durch eine 23
Zellen beziehungsweise 0,69 m breite Tuer. Die `ComputePathToPose`-Action
endete mit `SUCCEEDED` nach rund 0,7 ms; auch dabei blieb die Basis im Dry-run
bei 0 rpm. Die temporaere Karte wurde danach geloescht.

Der erste begrenzte Realtest am 18.08.2026 bestaetigte den 360,0-Grad-Rundblick,
die Karten-Vorausrichtung mit 3,0 Grad Restfehler und die Uebergabe genau eines
Nav2-Ziels. Die aeussere Beobachtung und das nachtraeglich ausgewertete Log
zeigten jedoch einen bereits davor liegenden Zielwahlfehler: Die gewaehlte
Frontier lag 30,6 Grad seitlich zur Startfront und fuehrte nicht zur Tuer.
`heading_scale: 3.0` bevorzugte die Front nur weich und konnte dieses Ziel
nicht ausschliessen. Amadeus fuhr rund 0,28 m in diese falsche Richtung, bevor
der Controller zusaetzlich abbrach. Diese zweite Ursache war weder Footprint
noch Planung: `map->odom` blieb unter Jetson-Last mindestens 0,95 s hinter der
aktuellen Odometrie zurueck, waehrend der Controller nur 0,5 s Ausfall
tolerierte. Das Ein-Ziel-Profil endete daraufhin wie vorgesehen nach dem ersten
Fehlversuch; die Tuerdurchfahrt gilt damit noch nicht als bestanden. Der
Controller toleriert nun 1,5 s. Der nachgeschaltete
`velocity_smoother` bleibt unveraendert bei 0,5 s und setzt die Geschwindigkeit
damit frueher auf null; ein dauerhaft fehlender TF fuehrt weiterhin zum
Abbruch. 15 direkte und 31 registrierte Navigationstests bestanden. Im
motorlosen Live-Stack waren `failure_tolerance=1.5`, `velocity_timeout=0.5`,
`dry_run=true` und 0 rpm aktiv. Nach beiden Laeufen waren keine
Amadeus-Knoten mehr aktiv.

Nur das Tuerprofil setzt deshalb jetzt einen harten Vorwaertskorridor von
+/-20 Grad (`frontier_forward_cone_half_angle_rad`). Ausserhalb liegende
Frontier-Anfahrpunkte werden vor jeder Vorausrichtung und Translation
verworfen. Gibt es keinen sicheren Kandidaten im Korridor, endet der Test
explizit ohne Translation. Das normale Wohnungsprofil setzt den Wert auf null
und behaelt seine unbeschraenkte Frontier-Auswahl. Der neue Auswahlvertrag
bestand 20/20 Explorer-Tests. Der installierte motorlose Live-Stack bestaetigte
den 20-Grad-Wert, ein Ziel/einen Fehlversuch, deaktivierte Coverage, 300 s,
`dry_run=true`, `allow_rs485=false` und 0 rpm. Beide VL53 liefen mit rund
3,5--3,9 Hz, der normierte LiDAR mit rund 10 Hz.

Fuer die reale Einzelabnahme existiert zusaetzlich das explizite Profil
`door_test_params.yaml`: Rundblick und Vorausrichtung bleiben aktiv, aber es
sind hoechstens ein Frontier-Ziel, ein Fehlversuch, keine Coverage-Fahrt und
300 s Gesamtdauer erlaubt. Der Parameter-Overlay wird von App-, Mapping- und
Explorer-Launch durchgereicht. Im Dry-run waren alle Begrenzungen live aktiv,
`allow_rs485=false` und 0 rpm. Ein VL53-Start schlug einmal rechts mit
`VL53L5CXException: 0` fehl; der isolierte Wiederholungstest initialisierte
anschliessend beide Sensoren und beide Punktwolken liefen stabil mit rund
3,98 Hz. Jeder scharfe Start muss deshalb beide Topics erneut pruefen.

**Offene Risiken:** Die abgeschraegten Vorderecken sind ohne gemessene
Schraegentiefe absichtlich nicht ausgespart; die Rechteckhuelle ist sicherer,
aber beim Drehen konservativer. Die Erkundung ist nur mit eingefahrenem Arm
zulaessig. NavFn garantiert keine global kinematisch gueltige Route fuer
Rechteckroboter; der lokale Polygonpruefer verhindert die Ausfuehrung einer
unpassenden Route, kann aber zu einem Stillstand fuehren. Der Wohnungs-
Abschlussvertrag muss noch um ungeloeste Portale und Kartenstabilitaet
erweitert werden. Die neue TF-Ausfalltoleranz ist motorlos verifiziert; die
reale Tuerdurchfahrt mit Vorwaertskorridor muss nach erneutem Aufstellen und
neuer Fahrfreigabe wiederholt werden.

**Rueckfallweg:** In `nav2_params_real.yaml` lokal/global wieder
`robot_radius: 0.40` setzen, im Mapping-Kollisionsmonitor den 0,40-m-Kreis
wiederherstellen und `coverage_clearance_m: 0.40` verwenden. Sicherer
Funktionsrueckfall bleibt `enable_auto_explore:=false` oder
`active_drive:=false`. Nur die TF-Ausfalltoleranz laesst sich separat durch
`controller_server.failure_tolerance: 0.5` zuruecknehmen. Der Tuerkegel laesst
sich separat mit `frontier_forward_cone_half_angle_rad: 0.0` deaktivieren.

---

## 2026-08-17 — Adaptive Erkundung real bestanden und Frontier-Schleife gesperrt

**Entscheidung:** Erfolgreich angefahrene Frontier-Umfelder werden fuer den
Rest derselben Mission in einem Radius von 0,60 m nicht erneut als Ziel
zugelassen. Zusaetzlich beendet ein hartes Limit von 20 Frontier-Zielen einen
fehlerhaften Lauf fail-closed. Wegen der realen, durch die aktive
VL53-SlowZone bis auf etwa 0,034 m/s reduzierten Fahrt gelten jetzt 150 s pro
Nav2-Ziel und 1200 s fuer den gesamten Rundblick-, Frontier- und
Abdeckungslauf.

**Grund / beobachtete Evidenz:** Der erste Akku-Realtest mit 90 s pro Ziel und
900 s Gesamtzeit endete waehrend Frontier 6 bei 82,72 % statt der geforderten
85 %. Nach der Zeiterhoehung zeigte ein weiterer scharfer Lauf einen anderen
Fehler: Nach zwei echten Frontier-Fahrten meldete Nav2 denselben bereits
erreichten Anfahrbereich wiederholt sofort als Erfolg. Die Abdeckung blieb bei
23,45 %, waehrend der Frontier-Zaehler ohne Bewegung bis 21 stieg. Der Auftrag
wurde abgebrochen und der Roboter bei 0 rpm gestoppt. Ursache war, dass nur
gescheiterte Ziele gesperrt wurden; erfolgreich bediente lokale
Frontier-Umfelder blieben erneut waehlbar.

Der beaufsichtigte Wiederholungslauf mit Sperre bestand in 732 s. Nach dem
360-Grad-Rundblick wurden fuenf verschiedene Frontier-Ziele real bedient. Die
Abdeckung stieg dabei nachvollziehbar von 3,69 ueber 6,47, 20,41, 35,01,
54,01 und 72,81 auf 88,30 %. Die adaptive Phase plante zwischenzeitlich ein
Abdeckungsziel; dessen Fahrt oeffnete neue Frontiers, worauf der Explorer
korrekt zur Frontier-Phase zurueckwechselte. Abschlusswerte:
`reachable_area_m2=5.0706`, `covered_area_m2=4.4775`,
`frontiers_visited=5`, `frontiers_remaining=0` und
`map_ready_to_save=true`.

**Betroffene Dateien und Hardware:** `explore_node`, Explorer-Parameter und
-Tests sowie Kartierungs- und Uebergabedokumentation. Der Realtest lief auf
Akku mit STL-27L, beiden VL53, Encoder-Odometrie, SLAM, Nav2,
`collision_monitor`, Missions-Gate und realem Antrieb. Wohnungsgeometrie und
Kartenbild liegen nur lokal unter `/tmp` und nicht im Repository.

**Teststatus:** 92 Tests aus `explore`, `robot_navigation`,
`mission_manager` und `robot_bringup` bestanden. Die vier Pakete `explore`,
`robot_navigation`, `robot_bringup` und `smartphone_gui` bauten erfolgreich.
Ein motorloser Gesamtstart bestaetigte die neuen Live-Parameter und brach bei
unveraenderter physischer LiDAR-Szene erwartungsgemaess fail-closed ab. Vor
dem scharfen Lauf waren Not-Aus frei, Odometrie 0/0, LiDAR und beide VL53
frisch und `collision_monitor` der einzige `/cmd_vel`-Publisher zur Basis.
Am Ende meldeten Explorer und Mission Erfolg, Odometrie 0/0 und die Basis
wiederholt 0 rpm. Der gerenderte 3-cm-Kartenausschnitt hatte 139 x 236 Zellen
(4,17 x 7,08 m), 16,99 m2 freie Zellen und keine offensichtlichen doppelten
Wandzuege. Danach wurde der gesamte Stack beendet.

**Offene Risiken:** Die Prozentzahl bezieht sich weiterhin auf die um 0,40 m
erodierte, vom Start aus erreichbare Freiflaeche und einen 0,65-m-Korridor um
die reale Fahrspur, nicht auf jede freie Karten- oder Bodenstelle. Die
Kartenansicht muss vor dauerhaftem Speichern durch eine Person bestaetigt
werden. Flache Kabel koennen unterhalb der Sensoren liegen. Die bekannten
Shutdown-Ausnahmen von LiDAR, `base_hardware` und VL53 traten erst nach
Nullkommando beim Strg-C-Beenden auf.

**Rueckfallweg:** `frontier_revisit_radius_m` und `max_frontier_goals` koennen
auf den vorherigen Commit zurueckgesetzt werden; fuer einen sicheren
Funktionsrueckfall `coverage_enabled:false`, `enable_auto_explore:=false`
oder `active_drive:=false` verwenden. Ein laufender Auftrag wird mit
`{"type":"cancel"}` beendet.

---

## 2026-08-16 — Frontier-Erkundung um adaptive Flaechenabdeckung und App-Preflight erweitert

**Entscheidung:** Die reale Raumkartierung besitzt nun drei Phasen: den
odometriegeprueften 360-Grad-Rundblick, die vorhandene Frontier-Erkundung und
anschliessend eine adaptive Abdeckungsfahrt. Die dritte Phase misst nicht den
bekannten Kartenanteil, sondern projiziert die tatsaechlich im Kartenframe
gemessene Fahrspur auf die zusammenhaengende sicher befahrbare Freiflaeche.
Nach Ende der Frontiers wird jeweils der geodaetisch am weitesten entfernte,
noch nicht abgedeckte sichere Punkt angefahren. Damit waechst die Zahl der
Ziele mit Raumgroesse und Grundriss statt mit einer festen Vierer-Liste.

Der Startwert fuer einen erfolgreichen Abschluss ist 85 % Abdeckung bei
0,65 m Besuchsradius, 0,40 m Kartenabstand, mindestens 0,70 m Zielentfernung,
hoechstens 14 Abdeckungszielen und 900 s Gesamtzeit. Abrupte
`map->odom`-Korrekturen ueber 0,35 m werden als neue Messpunkte gespeichert,
aber nicht als vermeintlich gerade gefahrene Strecke interpoliert. Ein
Zeitlimit oder fehlender sicherer Folgekandidat unterhalb 85 % meldet Fehler
und niemals „Karte fertig".

`explore_node` sendet einen 1-Hz-Heartbeat auf `/explore/status_json` mit
Phase, realer Abdeckung, Zielwert, befahrbarer/abgedeckter Flaeche,
Frontier-/Abdeckungszielen und `map_ready_to_save`. iOS- und Web-App schalten
„Erkundung starten" nur frei, wenn Missionsstatus, Not-Aus und Explorerstatus
frisch sind, `explore_execution=bt_explicit_opt_in` gilt und der Explorer
bereit ist. Der neue `robot_bringup/app_mapping.launch.py` startet SLAM,
Nav2, Missionskette, beide Kartenmanager, rosbridge und den optionalen
Web-Fallback genau einmal. `start_app_erkundung.sh` prueft zusaetzlich auf
bereits laufende passive App-Knoten und bricht vor einem Doppelstart ab.

**Grund / beobachtete Evidenz:** Im beaufsichtigten Frontier-Lauf erreichte
der Roboter vier sichere Ziele, befuhr nach Beobachtung aber nur etwa 40 % des
Raums. Das ist kein Fehler der festen Zielzahl — der Explorer hatte keine
Vierer-Liste. Ein LiDAR-Rundblick macht sichtbaren Boden bereits kartografisch
bekannt; die Frontier-Methode sucht danach nur noch Grenzen zwischen bekannt
und unbekannt. „Keine Frontier" beweist deshalb keine physische
Raumabdeckung. Der neue Pfadvertrag trennt beide Groessen.

Der erste Gesamt-Dry-run zeigte ausserdem zwei bereits laufende passive
Kartenmanager aus der vorherigen App-Sitzung. `roboterknoten.py --still`
erlaubt diese absichtlich; der neue Starter erkennt sie nun separat und
verhindert doppelte Knotennamen. In einer isolierten ROS-Domaene liefen
anschliessend genau je ein `/map`-, Explorer-, Missionsmanager-, Kartenmanager-
und rosbridge-Besitzer. `base_hardware` meldete durchgehend `dry_run=True` und
0 rpm. Ein echter WebSocket-Client erhielt den vollstaendigen Explorerstatus,
`explore_execution=bt_explicit_opt_in` und `/safety/estop=false`. Ein ueber
denselben rosbridge-Pfad gesendetes `explore` wurde auf Mission und Explorer
als `running` bestaetigt; `cancel` endete auf beiden Ebenen mit `canceled` und
`map_ready_to_save=false`.

**Betroffene Dateien und Hardware:** `explore`,
`robot_bringup/app_mapping.launch.py`, `tools/kartierung`, native iOS-App,
Web-Fallback und Simulator-Mock. Der Test startete STL-27L und beide VL53;
die Antriebe blieben im Dry-run unbestromt. Keine Wohnungsdaten wurden
eingecheckt.

**Teststatus:** 15 Explorer- und 3 Bringup-Vertragstests, 13 Navigationstests, 45
Missionsmanager-Tests und 6 Simulator-Mock-Tests bestanden. Vier geaenderte
ROS-Pakete bauten erfolgreich. JavaScript-Syntax, Python-Kompilierung,
Launch-Aufloesung, Einzelbesitzer, 1-Hz-Heartbeat und der komplette
rosbridge-Start-/Abbruchpfad wurden auf dem Jetson motorlos geprueft. Swift
und Xcode sind auf dem Jetson nicht installiert; die zwei neuen Swift-
Protokolltests muessen auf dem Mac/Xcode-Lauf noch ausgefuehrt werden.

**Offene Risiken:** Die adaptive Zielwahl ist noch nicht real gefahren. Der
85-%-Wert bezieht sich auf den um 0,40 m erodierten, zusammenhaengenden
Freiraum und einen 0,65-m-Korridor um die gemessene Spur, nicht auf jeden
Quadratzentimeter Boden. Dynamische Kartenexpansion kann den Prozentsatz
voruebergehend senken. Kabel unterhalb der Sensorsicht bleiben ein reales
Risiko. Die bekannten Shutdown-Ausnahmen von LiDAR, `base_hardware` und VL53
traten erneut erst nach Nullkommando beim Beenden auf und gehoeren nicht zu
dieser Aenderung.

**Rueckfallweg:** `coverage_enabled:false` stellt das alte Frontier-Ende
wieder her. Ohne `app_mapping.launch.py` bleibt der bisherige
`start_automatische_kartierung.sh` nutzbar. `enable_auto_explore:=false`
sperrt App-Auftrag und Fahrtor, `active_drive:=false` haelt die Basis im
Dry-run. Ein laufender Auftrag wird mit `{"type":"cancel"}` beendet.

---

## 2026-08-16 — Automatische LiDAR-Kartierung real abgenommen und LiDAR-Handedness korrigiert

**Entscheidung:** Die automatische Kartierung beginnt nicht mehr sofort mit
einem Fahrziel. Der Explorer fuehrt zuerst einen kontrollierten 360-Grad-
Rundblick mit 0,12 rad/s aus und misst den tatsaechlich erreichten Winkel aus
der Encoder-Odometrie. Erst nach bestaetigtem Stillstand werden Frontiers auf
der frisch erweiterten 3-cm-SLAM-Karte gesucht. Sichere Anfahrpunkte bleiben
im bekannten Freiraum, besitzen 0,35 m Abstand zu Wand und unbekanntem Raum
und werden nach Distanz, Groesse und aktueller Blickrichtung bewertet. Vor
jedem groesseren Richtungswechsel richtet ein begrenzter, encodergepruefter
Drehpfad den Roboter aus; das Nav2-Ziel wird erst nach erneuter Messung im
Kartenframe freigegeben.

Der STL-27L wird ROS-konform gegen den Uhrzeigersinn ausgegeben. Der dazu
gehoerende, gemeinsam verifizierte Montagevertrag ist
`laser_scan_dir: true` plus `tf_yaw: +1.5708`. Diese beiden Werte duerfen
nicht unabhaengig voneinander geaendert werden. Wenn nach mindestens einem
erreichten Ziel nur noch Frontiers ohne sicheren Anfahrpunkt im bekannten
Freiraum verbleiben, endet die Mission als `safe_complete` statt als Fehler.

Die reale Erkundung verlangt weiterhin zwei getrennte Opt-ins:
`active_drive:=true` fuer die Basis und `enable_auto_explore:=true` fuer
Missionsmanager und Fahrtor. Der Launch sendet selbst keinen Auftrag. OAK ist
aus dieser Kette entfernt; STL-27L, beide VL53, Odometrie, SLAM-Karte,
`collision_monitor`, Missionsstatus und das dedizierte Fahrtor muessen
fortlaufend vorhanden sein. Nav2-Recovery-Bewegungen sind nicht mit der
Hardware verbunden.

**Grund / beobachtete Evidenz:** Der erste reale Explore-Versuch erzeugte nur
eine kurze, langsame Bewegung und keine systematische Raumabdeckung. Die alte
Logik fuhr unmittelbar eine Frontier an und lieferte damit weder einen
definierten ersten Raumueberblick noch eine getrennte Messung, ob Basis oder
Nav2 die beobachtete Langsamkeit verursachten.

Beim ersten realen Vorausrichtungstest drehte die Encoder-Odometrie um
-96,9 Grad, waehrend der Kartenwinkel mit entgegengesetztem Vorzeichen lief:
Aus einem erwarteten kleinen Restfehler wurden +161,4 Grad; `map->odom` lag
bei etwa -172,7 Grad. Die SLAM-Daten enthielten keine Loop-Closure-Kanten, der
Sprung war daher keine falsche Wiedererkennung. Der Treiberquelltext zeigte
die Ursache: `laser_scan_dir: false` liess die nativen Uhrzeigersinn-Bins
stehen, publizierte aber weiterhin einen positiven `angle_increment`, den
ROS-Verbraucher als Gegen-Uhrzeigersinn interpretieren. Das alte
Winkelmesswerkzeug spiegelte dieses Vorzeichen vor der Betragsregression und
hatte den Fehler dadurch verborgen.

Nach der gekoppelten Korrektur meldete der isolierte Sensortest 2172 Strahlen,
Treibrichtung `Counterclockwise` und einen maskierten Mastbogen von
56,0 bis 123,9 Grad mit Zentrum bei 90 Grad im Sensorframe; durch den
+90-Grad-TF liegt der Mast korrekt hinten. Vorne, links und rechts waren
gueltig. Im echten Drehtest stimmten dann Odometrie (+99,10 Grad) und
Kartenwinkel (+98,10 Grad) in Vorzeichen und Betrag ueberein. Ein motorloser
Fehlertest liess den Kartenrestfehler absichtlich von +21,8 auf +22,5 Grad
steigen; das Fahrtor brach vor jeder Nav2-Translation ab. Damit ist der
Kartenframe-Abgleich nachweislich fail-closed.

Im anschliessenden motorlosen Gesamttest starteten LiDAR, `slam_toolbox`,
Basis im `dry_run`, beide VL53, Kollisionsmonitor, Explorer, Mission, Fahrtor
und Nav2 als eine Kette. Der Explorer kommandierte ausschliesslich eine
Drehung, akkumulierte ueber den +-Pi-Uebergang 360,4 Grad Odometriewinkel,
bestaetigte den Stopp und plante danach frisch. Er fand drei sichere
Frontier-Kandidaten und uebergab genau ein Nav2-Ziel. Ein expliziter Abbruch
stornierte das Kindziel, sperrte das Fahrtor und fuehrte Soll- und
Istkommando auf 0,000 m/s und 0,000 rad/s.

Der Test deckte zwei Startfallen auf. `slam_toolbox` publiziert eine
unveraenderte Karte im Stillstand nicht laufend neu; deshalb darf nur der
dedizierte, streng auf reine Drehung begrenzte Rundblick eine bereits
empfangene, aber nicht mehr frische Karte verwenden. Jede Nav2-Fahrt verlangt
weiterhin eine frische Karte. Ausserdem wurde die
`IsEstopClear`-Subscription erst mit dem Missionsbaum angelegt und konnte beim
allerersten Tick noch leer sein. Eine einsekundige Vorlaufzeit vor dem ersten
BT-Tick behebt dieses Rennen, ohne eine Action vor der Sicherheitspruefung zu
starten; ein fehlendes oder aktives Not-Aus-Signal bleibt danach fail-closed.

Der beaufsichtigte Realtest bestand anschliessend den 360,2-Grad-Rundblick und
erreichte vier nacheinander neu geplante Frontier-Ziele. Die erste
Vorausrichtung endete bei nur -2,5 Grad Kartenrestfehler und -3,5 Grad bei der
Uebergabe. Ein unter Jetson-Last kurz veralteter `map->odom`-Transform brach
ein Ziel sicher ab; der begrenzte Neuversuch richtete erneut aus und setzte
ohne Recovery-Bewegung fort. Am Ende blieb nur eine Frontier ohne sicheren
Anfahrpunkt im bekannten Freiraum. Die daraus gerenderte Karte war ein
zusammenhaengender Grundriss ohne doppelte Waende oder getrennte Teilkarten:
195 x 221 Zellen bei 3 cm, 5,85 x 6,63 m Ausdehnung und 16,1 m2 freie Flaeche.
Karte und Diagnosebild bleiben lokal und werden nicht eingecheckt.

**Betroffene Dateien und Hardware:** `explore`, `robot_navigation`,
`mission_manager`, `bt_orchestrator`, `amadeus_lidar_bringup`, die
Odometrie-Messwerkzeuge sowie
`tools/kartierung/start_automatische_kartierung.sh`; real betroffen waren
STL-27L, beide VL53L7CX und beide ESS23-RS-Antriebe. Wohnungsgeometrie,
ROS-Bags und Diagnosebilder werden nicht eingecheckt.

**Teststatus:** Python-Kompilierung und `git diff --check` bestanden. 156
direkt ausgefuehrte Python-Vertrags-, Algorithmus- und Hardwaretests sowie 72
Colcon-Tests liefen ohne Fehler; der gemeinsame Build aller sieben geaenderten
ROS-Pakete bestand. Motorlos bestanden Rundblick, Neuplanung,
Kartenframe-Gate und Abbruch. Real bestanden Rundblick, Vorausrichtungen, vier
Frontier-Fahrten, ein fail-closed TF-Neuversuch und der abschliessende
Stillstand bei 0 rpm.

**Offene Risiken:** Ein flaches Kabel unterhalb der VL53- und LiDAR-Sicht kann
weiterhin unentdeckt bleiben; die beaufsichtigte freie Fahrflaeche und der
hardwired Not-Aus bleiben notwendig. Unter hoher Jetson-Last kann ein
Karten-Transform kurz veralten; die Kette stoppt dann und versucht nur
begrenzt neu. Die bekannten Shutdown-Ausnahmen des LiDAR-Treibers sowie von
`base_hardware` und `vl53_near_field` treten erst nach bestaetigtem
Nullkommando auf und sind separat zu bereinigen.

**Rückfallweg:** Den neuen Kartierungslaunch nicht starten oder
`enable_auto_explore:=false` belassen; dann nimmt das Fahrtor keine
Explore-Bewegung an. `active_drive:=false` haelt die Basis im Dry-run. Ein
laufender Auftrag wird mit `{"type":"cancel"}` beendet; danach blockiert das
Fahrtor sofort und Nav2 muss sein Kindziel terminal stornieren.
LiDAR-Richtung und Montage-Yaw nur als gekoppeltes Paar zurueckrollen; ein
einseitiger Rueckbau spiegelt den Scan erneut.

---

## 2026-08-16 — A* und aktiver VL53-Schutz fuer reale Raumfahrt abgenommen

**Entscheidung:** Der reale Navfn-Planer verwendet `use_astar: true`. Bei
Zielfahrten bleiben beide VL53-Quellen in lokaler/globaler Costmap und im
`collision_monitor` aktiv. Die OAK-Punktwolke bleibt vorlaeufig aus der
Laufzeit heraus, bis ihre Fehlmarkierungen getrennt korrigiert sind.

**Grund / beobachtete Evidenz:** Auf derselben unveraenderten 3-cm-Karte brach
Dijkstra mit `Failed to create a plan from potential` ab. Der rein lesende
A/B-Test zeigte dennoch eine zusammenhaengende begehbare Zellenmenge. A* fand
bei weiterhin aktiven VL53-Obstacle-Layern sofort einen Pfad. Mit zusaetzlich
aktiver OAK-Punktwolke wurde dagegen selbst das freie Raumziel als Kostenwert
253 markiert und die begehbare Verbindung getrennt; das ist ein Sensorfilter-
und kein Kartenaufloesungsproblem.

Nach einem frischen Build und Neustart lud der Planer A* aus der persistenten
Konfiguration und plante denselben Pfad erneut erfolgreich. Der anschliessende
beaufsichtigte Realtest erreichte das semantische Raumziel mit maximal
0,100 m/s. Missionsstatus war `success/angekommen`; Lokalisierung blieb
freigegeben. Danach meldeten Soll- und Istgeschwindigkeit sowie beide Motoren
0, Encoderfeedback war frisch und fehlerfrei, Modbus-Lesefehler blieben 0.
Beide VL53 lieferten vor der Fahrt fortlaufend Punktwolken; im freien
Nahbereich waren 0 Punkte das erwartete Ergebnis. Der `collision_monitor` war
aktiv und alleiniger Publisher auf den Hardware-Eingang `/cmd_vel`.

**Betroffene Dateien und Hardware:** `robot_navigation`-Planerkonfiguration
und Vertragstest, beide VL53L7CX, STL-27L, Nav2 sowie beide ESS23-RS-Antriebe.
Echte Karte und Raumgeometrie bleiben lokal.

**Teststatus:** 9 gezielte Navigationstests, YAML-Vertragspruefung,
Colcon-Build, motorloser Neustart mit persistentem A*, read-only Pfadplanung
und eine reale Zielfahrt bestanden. Vor dem Realtest waren Vollscan-Score
0,978, Lokalisierung, RS485, Encoder, VL53 und Kollisionskette bereit. Nach
dem Test wurden alle scharfen Prozesse beendet.

**Offene Risiken:** Der Schutz wurde aktiv mitgefuehrt, aber noch nicht durch
ein absichtlich eingebrachtes Hindernis zum Bremsen ausgeloest. Die
OAK-Punktwolke darf bis zur Korrektur des Boden-/Hoehenfilters nicht als
Obstacle-Quelle aktiviert werden. Die bekannten Shutdown-Ausnahmen bleiben
reine Aufraeumfehler nach bestaetigtem 0-rpm-Stillstand.

**Rückfallweg:** `use_astar` auf `false` zuruecksetzen oder den realen
Lokalisierungs-/Navigationslaunch nicht starten. A* veraendert weder
Geschwindigkeitsgrenzen noch die fail-closed Fahrtor- und Kollisionskette.

---

## 2026-08-16 — Globaler Kaltstart und autonome Raumfahrt reproduzierbar abgenommen

**Entscheidung:** Der native Humble-Dienst
`/reinitialize_global_localization` wird im Normalstart nicht mehr aufgerufen.
Stattdessen eroeffnet der `localization_guard` einen eindeutig an Karte,
Generation und 128-Bit-ID gebundenen Vollscan-Zyklus. Zwei separat berechnete
Scans muessen innerhalb 0,20 m und 8 Grad dieselbe Pose liefern; erst dann
setzt `global_scan_localizer` `/initialpose`. AMCL muss diesen Treffer
rueckbestaetigen, bevor das Fahrtor oeffnet. AMCL startet vier Sekunden nach
Karte/Basis/LiDAR, Guard und Matcher nach sieben Sekunden, um den Jetson beim
Lifecycle-Start zu entlasten.

**Grund / beobachtete Evidenz:** Bei einem realen Kaltstart war der AMCL-Dienst
bereits erreichbar, obwohl AMCL intern noch keine Karte verarbeitet hatte.
Der Humble-Callback reicht in diesem Zustand einen Null-Kartenzeiger an
`pf_init_model` weiter; direkt nach dem Dienstaufruf starb AMCL mit
`exit code -11`. Ein weiterer gleichzeitiger Vollstart verlor zudem eine
Fast-DDS-Antwort auf `/amcl/change_state` und liess AMCL inaktiv. Der
kartenfeste Initialpose-Pfad und die zeitliche Staffelung beseitigen beide
beobachteten Startfehler, ohne einen Grenzwert zu lockern.

Drei anschliessende motorlose Kaltstarts an der unveraenderten, vom
Beobachter bestaetigten Pose bestanden. Die Treffer streuten hoechstens
3 cm und 1 Grad; Score `0,9787..0,9789`, Wandtrefferquote
`97,36..97,50 %` und Bestenabstand `1,155..1,168`. Jeder Start benoetigte
genau zwei konsistente Scans, AMCL wurde `active`, `/localization/ready` wurde
`true`, und `base_hardware` blieb `dry_run=true` bei 0 rpm.

Der danach ausdruecklich freigegebene End-to-End-Lauf lokalisierte erneut
motorlos im Stand und fuhr anschliessend das karten- und revisionsgebundene
Ziel `Arbeitszimmer` an. Nav2 meldete `success`, der Missionsmanager
`angekommen`. Der Karten-Endfehler betrug 0,133 m und 6,28 Grad und lag damit
innerhalb der Abnahmegrenzen 0,15 m/0,40 rad. Der Encoderweg betrug 1,024 m;
der Fahrbefehl blieb bei hoechstens 0,100 m/s. Nach dem terminalen Status
wurden wiederholt Soll- und Istgeschwindigkeit sowie beide Motoren mit 0 rpm
bestaetigt. Lokalisierung, Encoder und Modbus blieben fehlerfrei.

**Betroffene Dateien und Hardware:** `robot_navigation` (Startstaffelung,
Guard, Initialisierungsvertrag, Zwei-Scan-Konsens, Tests), STL-27L, Nav2/AMCL
und beide ESS23-RS-Antriebe. Die beiden VL53-Datenstroeme und der aktive
`collision_monitor` wurden vor der Fahrt geprueft, danach auf ausdruecklichen
Wunsch nur fuer diesen beaufsichtigten Lauf zur Laufzeit deaktiviert. Diese
Deaktivierung ist nicht persistent. Echte Karten, Raumgeometrie und
Diagnosebilder bleiben lokal.

**Teststatus:** 30 gezielte Python-Tests, Python-Kompilierung,
`git diff --check`, Colcon-Build und Colcon-Test des Pakets bestanden. Dazu
bestanden drei vollstaendige motorlose Kaltstarts, eine read-only
Nav2-Pfadplanung und die reale semantische Zielfahrt. Vor und nach der Fahrt
gab es genau einen Karten-, Semantik-, Missions-, AMCL- und `cmd_vel`-Pfad;
alle scharfen Knoten wurden anschliessend beendet.

**Offene Risiken:** Die heutige Wiederholung belegt drei Neustarts an einer
extern bestaetigten Position und einen vollstaendigen Ziellauf. Fuer eine
breitere statistische Aussage bleiben weitere deutlich getrennte
Startpositionen und Raumkonfigurationen sinnvoll. VL53 und OAK waren waehrend
des eigentlichen Ziellaufs deaktiviert; Hinderniserkennung ist damit fuer
diesen Lauf nicht abgenommen. Die bekannten Shutdown-Meldungen des
STL-27L-Treibers sowie die doppelte `rclpy.shutdown()`-Exception von
`base_hardware` und `vl53_near_field` bleiben getrennte Aufraeumfehler nach
bestaetigtem Stillstand.

**Rückfallweg:** `nav_localized.launch.py` nicht starten und
`enable_real_go_to_room:=false` verwenden. Dadurch bleiben globale
Lokalisierung und reale semantische Raumfahrt ohne Fahrwirkung. Der alte
AMCL-Globaldienst darf wegen des belegten Null-Kartenfensters nicht wieder in
den automatischen Kaltstart aufgenommen werden.

---

## 2026-08-16 — Selbstsichere AMCL-Fehlpose durch globalen Vollscan-Gate behoben

**Entscheidung:** Eine kleine AMCL-Kovarianz reicht nicht mehr zur ersten
Fahrfreigabe. Der neue `global_scan_localizer` sucht motorlos mit einem
stationaeren Vollscan ueber alle freien Kartenpositionen und Blickrichtungen.
Er bewertet Wandendpunkte und freie Strahlwege und akzeptiert nur einen
absolut guten sowie gegen die zweitbeste getrennte Hypothese eindeutigen
Treffer. Jeder AMCL-Global-Reset erhaelt eine zufaellige 128-Bit-ID. Der
`localization_guard` verlangt einen frischen Treffer fuer exakt
Kartenfingerabdruck, Generation und Reset-ID und prueft anschliessend, dass
AMCL hoechstens 0,30 m/12 Grad von diesem Startwert abweicht. Erst danach
gelten die bisherigen Kovarianz- und TF-Stabilitaetsgrenzen.

**Grund / beobachtete Evidenz:** AMCL meldete nach einer beaufsichtigten
Suchdrehung die Pose `(0,704; 0,379; -123,6 Grad)` mit nur
`0,122/0,123 m` und `9,54 Grad` Standardabweichung. Die vom Beobachter in der
Karte markierte reale Position lag jedoch rund 1,95 m entfernt. Ein
unabhaengiger Scan/Karten-Abgleich widerlegte die scheinbar sichere Pose: nur
39,6 % der Endpunkte lagen innerhalb 15 cm einer Kartenwand, Medianabstand
0,190 m.

Die globale Vollscansuche fand ohne Bewegung konsistent den Bereich
`x=1,245..1,305 m`, `y=-1,135 m`, `yaw=38..39 Grad`. Im ersten Diagnoselauf
erreichte der beste Treffer Score 0,980, 99,17 % Wandtreffer und Faktor 1,283
zur zweitbesten getrennten Hypothese. Drei vollstaendige motorlose Starts
lieferten erneut denselben Bereich. Der finale Kaltstart erreichte Score
0,973, 98,75 % Wandtreffer, Faktor 1,245 und wurde von AMCL bei
`(1,237; -1,147; 39,4 Grad)` bestaetigt. Die unabhaengige Nachpruefung legte
98,27 % der aktuellen Scanpunkte innerhalb 15 cm an Kartenwaende; Median
0,030 m, 90-%-Quantil 0,060 m. Das ist die gemessene A/B-Trennung gegen die
falsche AMCL-Pose, nicht nur eine kleinere Kovarianz.

**Betroffene Dateien und Hardware:** `robot_navigation` (Matcher-Kern,
ROS-Knoten, Launch, Guard und Vertrag), `tools/kartierung` (rein lesende
Diagnose) und STL-27L. Beide ESS23-RS-Antriebe blieben durchgehend im
`dry_run`; keine reale Karte und kein Diagnosebild wird eingecheckt.

**Teststatus:** 22 gezielte `robot_navigation`-Tests, Python-Kompilierung,
`git diff --check` und Colcon-Build bestanden. Der synthetische Test trennt
eine korrekte von einer falschen Pose ueber Wand- und Freistrahlscore. Live
wurden bei drei Neustarts jeweils eine neue Reset-ID, ein Treffer im selben
Positionsbereich, Guard-Verifikation, `ready=true`, `dry_run=true` und
Motorwerte 0 rpm bestaetigt. Ein erwartbarer AMCL-Loghinweis zur wenige
Millisekunden juengeren Initialpose erscheint unmittelbar vor dem dennoch
erfolgreichen `Setting pose`; Rueckdatieren und Nullstempel veraenderten ihn
nicht und wurden deshalb nicht als Scheinloesung uebernommen.

**Offene Risiken:** Die reale Blickrichtung muss noch vom anwesenden
Beobachter bestaetigt werden; die eingezeichnete gruene Pfeilrichtung koennte
auch nur ein Positionszeiger sein. Vorfuehrreife verlangt danach mindestens
zwei weitere motorlose, deutlich getrennte Startpositionen und erst dann eine
beaufsichtigte reale Zielfahrt. Die festen Qualitaetsgrenzen sind mit der
aktuellen Zimmerkarte klar bestanden, aber noch nicht statistisch ueber viele
Raumkonfigurationen validiert. Bei offener Tuer oder starker dynamischer
Verdeckung darf der Matcher korrekt ablehnen; das Fahrtor bleibt dann zu.

**Rückfallweg:** `nav_localized.launch.py` nur motorlos mit
`require_global_scan_match:=false` starten oder auf den vorherigen Commit
zurueckgehen. Eine reale Fahrt ohne den Vollscan-Gate ist nach dem belegten
1,95-m-Fehler nicht freigegeben.

---

## 2026-08-15 — Ursache der nicht wiederholbaren AMCL-Lokalisierung gefunden

**Entscheidung:** Vor jedem LiDAR-/AMCL-Start prueft
`karte_fuer_nav2_pruefen.py` die tatsaechliche Nav2-Trinary-Interpretation von
PGM und YAML. Der Start bricht ab, wenn die von ROS `map_saver` als Grauwert
205 gespeicherten unbekannten Zellen durch den Schwellwert vollstaendig zu
freiem oder belegtem Raum werden. Die echte Karte wurde lokal, verlustfrei
mit `free_thresh: 0.196` neu versioniert; Original und alte Version bleiben
unveraendert. Das semantische Overlay wurde nur wegen identischer
PGM-Geometrie explizit an den neuen Fingerabdruck gebunden.

**Grund / beobachtete Evidenz:** Die bislang verwendete PGM-Datei besitzt
20.543 freie, 3.561 belegte und 29.320 unbekannte Zellen. Ihr altes YAML mit
`free_thresh: 0.25` klassifizierte den Unbekannt-Wert 205 jedoch als frei.
Der live geladene und anschliessend korrekt gespeicherte OccupancyGrid besass
deshalb 49.863 freie Zellen, keine unbekannte Zelle und 44,88 m² scheinbare
Freiflaeche statt 18,49 m². AMCL musste damit in physisch unmoeglichen
Aussenbereichen suchen. Die korrigierte Live-Karte enthaelt wieder exakt
20.543/3.561/29.320 Zellen und den Fingerabdruck
`528a0b020fe89624da1c55925421aecba948a13f6f27f84087725d0ad79c701f`.
Schon im Stillstand sank die globale AMCL-Streuung gegenueber der
verfaelschten Karte von etwa 1,73/2,06 m auf 1,36/1,43 m; eine physische
Beobachtungsfahrt ist fuer die Konvergenz weiterhin erforderlich.

Dabei wurde ein zweiter Vertragsfehler korrigiert: `/amcl_pose` wird im
Stillstand nicht periodisch publiziert. Ein pauschaler Nachrichten-Timeout
haette eine einmal korrekt lokalisierte, stehende Pose wieder gesperrt. Der
Guard verlangt stattdessen eine Pose nach dem kartenbezogenen Global-Reset
und sichert deren Fortbestand ueber den frischen dynamischen `map -> odom`-TF.

**Betroffene Dateien und Hardware:** `tools/kartierung`,
`robot_navigation/localization_guard.py`, STL-27L und lokale Kartenablage.
Keine echte Karte oder semantische Raumgeometrie liegt im Repository.

**Teststatus:** Die Pruefung lehnt die alte reale YAML/PGM-Kombination mit
29.320 verlorenen Zellen ab und akzeptiert die korrigierte Version mit
18,49 m² frei und 26,39 m² unbekannt. Vier synthetische Positiv-/Negativtests
bestehen. Der korrigierte ROS-OccupancyGrid und die neue semantische Bindung
wurden motorlos live bestaetigt.

Der reale End-to-End-Lauf nach freiem Versetzen bestand am selben Tag. Ein
erster Global-Reset mit 360,3 Grad Suchdrehung und 0,243 m begrenzter
Vorwaertsfahrt verbesserte die Streuung auf 0,111/0,152 m und 20,88 Grad. Das
0,35-m-Fahrtorlimit schloss 7 mm vor dem angeforderten Weg. Nach dem deshalb
erforderlichen Stack-Neustart wurde AMCL am veraenderten Standort erneut
global verteilt. Auf 180,2 Grad Beobachtungsdrehung folgten 20 standardisierte
stationaere `/request_nomotion_update`-Messungen; sie trennten die
verbliebenen Winkelhypothesen. Die Freigabe erfolgte bei 0,095/0,118 m und
7,83 Grad Standardabweichung. Die erste
Raumfahrt wurde bei erneut auf 15,69 Grad gestiegener Winkelunsicherheit
korrekt abgebrochen; Fahrtor und Motoren gingen auf null. Nach 20 weiteren
stationaeren Messungen lag AMCL bei 0,019/0,077 m und 4,50 Grad. Der erneute
`go_to_room`-Auftrag meldete `success/angekommen`; Abschlusswerte waren
0,051/0,078 m und 6,08 Grad, korrekter Kartenfingerabdruck und 0 rpm. Die
TF-Zielabweichung betrug rund 0,148 m und 21,7 Grad und lag damit innerhalb
der konfigurierten Nav2-Toleranzen 0,15 m/0,40 rad.

Der Lokalisierungshelfer fordert die stationaeren AMCL-Nachmessungen nun nach
garantiertem Stop selbst an. Dadurch wird nicht die 10-Grad-Grenze gelockert,
sondern es werden im Stillstand weitere LiDAR-Beobachtungen ausgewertet. Die
Einzelschritte sind real belegt; die nun zusammengefuehrte Ein-Aufruf-Variante
bedarf beim naechsten versetzten Start noch eines Wiederholungslaufs.

**Offene Risiken:** Ein realer, frei versetzter End-to-End-Lauf ist bestanden;
mehrere unabhaengige Startpositionen fehlen noch fuer eine statistische
Wiederholbarkeitsaussage. Eine Raumfahrt kann bei voruebergehend steigender
Winkelunsicherheit weiterhin sicher abbrechen und muss erst nach erneuter
Lokalisierungsfreigabe neu beauftragt werden. Die konkrete Schwelle 0.196 gilt
fuer diese map_saver-PGM; andere Karten muessen durch die Pruefung bewertet
und duerfen nicht automatisch umgeschrieben werden.

**Rückfallweg:** Den korrigierten lokalen Kartenstand nicht verwenden und den
Lokalisierungs-Launch motorlos lassen. Das Original ist unveraendert vorhanden;
die Startpruefung kann separat rueckgaengig gemacht werden, ohne Kartendaten
oder Motorparameter anzufassen.

---

## 2026-08-15 — Globale AMCL-Lokalisierung: Sicherheitskette real bewiesen, Wiederholbarkeit noch offen

**Entscheidung:** Reale semantische Raumfahrt wird an eine explizite globale
AMCL-Freigabe gebunden. Der `localization_guard` prueft Kartenfingerabdruck,
Publisher-Eindeutigkeit, eine Pose nach dem Global-Reset, Scan-/TF-Frische,
AMCL-Kovarianz und die Stabilitaet von `map -> odom`. Die erstmalige Freigabe bleibt streng bei
0,20 m Standardabweichung in x/y, 10 Grad in yaw sowie 0,08 m/5 Grad
TF-Bewegung im Drei-Sekunden-Fenster. Nach einer bestaetigten Freigabe gelten
Hysteresen von 0,30 m/15 Grad fuer die Kovarianz und 0,20 m/12 Grad fuer die
TF-Bewegung.

Ein Verlust von `/localization/ready` sperrt das `cmd_vel`-Gate weiterhin
sofort. Nur der irreversible Missionsabbruch hat eine Nachfrist von 0,8 s:
Kurze AMCL-Korrekturen stoppen den Roboter, lassen die laufende Nav2-Action
aber bestehen; anhaltender Verlust bricht sie ab. Die erste Zielannahme hat
keine Nachfrist.

**Grund / beobachtete Evidenz:** Nach freiem Versetzen gelang eine globale
AMCL-Lokalisierung nach einer vollstaendigen Drehung einmal mit
0,118/0,135 m und 8,65 Grad Standardabweichung. Die anschliessende reale
`go_to_room`-Fahrt kam bis auf rund 0,03 m an das semantische Ziel. Eine
0,59 s lange `map -> odom`-Korrektur wurde durch die neue Missionsnachfrist
korrekt ueberstanden. Eine zweite Instabilitaet dauerte 2,20 s; der
Mission Manager brach deshalb wie vorgesehen ab und beide Motoren wurden bei
null bestaetigt. Nav2 selbst meldete dabei keinen Planer- oder Reglerfehler.

Die alte TF-Haltegrenze 0,08 m/5 Grad war fuer normale AMCL-Korrekturen zu
eng. Eine begrenzte langsame Kurvenfahrt mit 0,04 m/s und 0,15 rad/s lieferte
640 TF-Proben; im Drei-Sekunden-Fenster traten maximal 0,1601 m und 8,32 Grad
auf. Daraus wurden die Haltegrenzen 0,20 m/12 Grad mit Messreserve abgeleitet,
waehrend die strengeren Erstfreigabegrenzen unveraendert bleiben.

Nach einem weiteren Neustart und erneutem Versetzen war die globale Pose trotz
vollstaendiger Drehung und begrenzter Suchboegen nicht wieder eindeutig. Der
beste spaetere AMCL-Stand lag unter anderem bei 0,146/0,117 m, aber 11,33 Grad
und bestand den Vertrag absichtlich nicht. Ein Laufzeitversuch mit
2.000 bis 10.000 Partikeln endete bei 0,141/0,113 m und 13,39 Grad; diese
Parameter wurden deshalb nicht uebernommen. Einzelscan-Hypothesen waren wegen
der unvollstaendigen/offenen Karte und Raumsymmetrien mehrdeutig. Eine
zunaechst scheinbar gute Hypothese lag bei korrekter Nav2-Geometrie
(0,40 m Roboterradius) sogar in einer unzulaessigen Zelle. Deshalb wird weder
die 10-Grad-Grenze gelockert noch eine einzelne Scan-Uebereinstimmung als
globale Pose akzeptiert.

**Betroffene Dateien und Hardware:** `robot_navigation` (AMCL-Launch,
Lokalisierungsvertrag und -Guard, Missions-Gate, Realprofil und Starthelfer),
`mission_manager` (Freigabepruefung und 0,8-s-Abbruchnachfrist),
`robot_bringup` (Joystick-Konfliktvermeidung), STL-27L und beide ESS23-RS-
Antriebe. Die echte Karte, semantische Raumdaten, Diagnoserenderings und
Messprotokolle bleiben lokal ausserhalb des Repositories. Die VL53-Zonen und
beide Costmap-Obstacle-Layer wurden auf ausdruecklichen Wunsch nur fuer die
beaufsichtigten Testlaeufe zur Laufzeit deaktiviert; daraus folgt keine
persistente Konfigurationsaenderung.

**Teststatus:** Colcon-Build von `robot_navigation` und `mission_manager`, 60
gemeinsame Tests ohne Fehler, Python-Kompilierung und Whitespacepruefung
bestanden. Der motorlose Preflight bestaetigte `dry_run:true`, gesperrtes
RS485, 0 rpm und die aktiven Acquire-/Maintain-Grenzen. Real bestanden sind
der unmittelbare Gate-Stopp, das Ueberstehen des 0,59-s-Aussetzers, der sichere
Abbruch nach 2,20 s und die lokale Nav2-Annaeherung bis 0,03 m. Nicht bestanden
und damit offen ist eine nach beliebigem Versetzen wiederholbar eindeutige
globale Selbstlokalisierung mit anschliessender vollstaendiger Zielerreichung.

**Offene Risiken:** Die aktuelle Zimmerkarte ist bei offener Tuer und in
symmetrischen Bereichen fuer eine einzelne LiDAR-Beobachtung mehrdeutig.
AMCLs globaler Reset plus einfache Dreh-/Bogensuche garantiert noch keine
Konvergenz zur richtigen Hypothese. Als naechster Schritt ist ein
Mehrbeobachtungs-Initialisierer mit zeitlich getrennter Scanbewertung oder eine
messgestuetzte AMCL-Suchstrategie erforderlich. Vor jeder weiteren Fahrt nach
manuellem Verschieben muss die Pose neu ermittelt werden; eine alte Pose darf
nicht fortgeschrieben werden.

**Rückfallweg:** `nav_localized.launch.py` beziehungsweise den
Lokalisierungshelfer nicht starten und `enable_real_go_to_room:=false`
verwenden. Dann bleibt semantische Raumfahrt ohne reale Fahrwirkung. Fuer den
vorherigen kontrollierten statischen Testbezug kann `nav_real.launch.py` nur
unter den dort dokumentierten engen Testbedingungen verwendet werden; er ist
kein Ersatz fuer globale Lokalisierung.

---

## 2026-08-15 — Reale semantische Raumfahrt fail-closed abgenommen

**Entscheidung:** `go_to_room` darf ein echtes Nav2-Ziel nur nach dem separaten
Opt-in `enable_real_go_to_room:=true` senden. Der Standard bleibt Simulation.
Der reale Pfad verwendet einen Recovery-freien Behavior Tree und diese Kette:

```text
Nav2 -> cmd_vel_mission_gate -> velocity_smoother -> collision_monitor
     -> base_hardware
```

Das Gate gibt nur einen frischen `running`-Status derselben `go_to_room`-
Mission frei. Terminaler, fehlender, veralteter oder ungueltiger Status
erzwingt null. Der Glätter arbeitet `OPEN_LOOP`; die Encoder-Odometrie bleibt
unveraendert die Nav2-Rueckmeldung. Der Fortschrittspruefer verlangt 0,10 m in
20 s.

**Grund / beobachtete Evidenz:** Die Antriebsvorzeichen wurden mit einer
begrenzten Rechtsdrehung isoliert bestaetigt. Der erste Reglerlauf bog trotzdem
ab, weil `CLOSED_LOOP` die bereits vorhandene 2000-ms-Motorrampe ein zweites
Mal nachregelte: Nach drei Sekunden lagen nur 3,5 mm Encoderweg und etwa
0,007 m/s Sollgeschwindigkeit an. `OPEN_LOOP` beseitigte diese Doppelkopplung.

Ein zweiter, sicherheitsrelevanter Befund war Nav2s bisheriger
`default_server_timeout` von 20 ms. Die Unterzielannahme kam real erst nach
rund 590 ms; der Behavior Tree meldete vorher Fehler, waehrend der Controller
das verspaetet angenommene Unterziel weiterfuhr. Der Timeout steht nun auf
2000 ms, und das zusaetzliche Missions-Gate blockiert einen solchen verwaisten
Befehl unabhaengig vom Nav2-Actionzustand. Eine nach erfolgreichem Trockenlauf
absichtlich injizierte Rohgeschwindigkeit bewirkte hinter dem Gate exakt
0,000 m virtuelle Bewegung.

Der erste reale Lauf mit der neuen Kette wurde nach 15 s als festgefahren
abgebrochen: Die sanfte Hardware-Rampe hatte zu diesem Zeitpunkt rund 0,19 m
statt der damals geforderten 0,30 m erreicht. Das war kein Schlupf und kein
Encoderfehler. Mit der daraus gemessenen Schwelle 0,10 m/20 s erreichte der
abschliessende beaufsichtigte Lauf sein semantisches Ziel. Gemessen wurden
1,084 m Encoderweg, maximal 0,14 Grad Abweichung im langen Geradeausabschnitt
und 3,28 Grad beim finalen Einlenken. Roh-, Gate-, Glätter- und Sicherheits-
Ausgang blieben bei hoechstens 0,100 m/s und 0,149 rad/s. Nach dem
Terminalstatus war der maximale verwaiste Rohbefehl 0,000; Gate und beide
Motoren wurden bei null bestaetigt. Beide VL53-Datenstroeme blieben frisch,
Encoder und Modbus meldeten keinen Fehler.

**Betroffene Dateien und Hardware:** `mission_manager` (expliziter Nav2-Pfad,
Recovery-freier Baum, Action-Abbruch), `robot_navigation` (Realprofil,
Missions-Gate, Open-Loop-Glättung, Fortschrittspruefer), beide ESS23-RS-
Antriebe und beide VL53L7CX. Keine Karte, Raumgeometrie oder Zielkoordinate
wurde ins Repository aufgenommen.

**Teststatus:** Colcon-Build von `mission_manager` und `robot_navigation`, 44
gemeinsame Python-Tests, Python-Kompilierung, XML-/YAML-Pruefung und
`git diff --check` bestanden. Gate-Fehlerinjektion bestand fehlenden,
laufenden, terminalen und veralteten Status. Der vollstaendige Trockenlauf und
die verwaiste-Rohbefehl-Injektion bestanden. Der abschliessende reale Lauf
bestand Zielerreichung, Geschwindigkeitsgrenzen, Sensorfrische und gemessenen
Stillstand.

**Offene Risiken:** Dies ist noch keine allgemeine Selbstlokalisierung. Der
abgenommene Lauf verwendete einen bewusst gesetzten statischen `map -> odom`-
Startbezug; nach freiem Versetzen oder Neustart muss die Pose weiterhin
zuverlaessig lokalisiert werden. Der Recovery-freie Baum bricht bei Planungs-
oder Regelfehlern absichtlich ab und umfährt nichts selbstständig. H5 der
Encoder-Odometrie und ein realer VL53-Hindernis-Abbruch waehrend dieser
Raumfahrt bleiben offen. `base_hardware` und `vl53_near_field` melden beim
gemeinsamen SIGINT weiterhin eine bereits bekannte doppelte
`rclpy.shutdown()`-Exception, nachdem der Stillstand erreicht ist; das neue
Gate endet dagegen sauber.

**Rückfallweg:** `enable_real_go_to_room:=false` verwenden oder weglassen;
dann bleibt `go_to_room` ohne Fahrwirkung in der bisherigen Simulation. Den
Real-Launch nicht starten. Motorparameter, Encodergeometrie und semantische
Kartendaten werden durch diesen Rückfall nicht verändert.

---

## 2026-08-14 — Beschleunigungsrampe 2000 ms real abgenommen

**Entscheidung:** `accel_ms` wird von 100 auf **2000** erhöht. Bremsen bleibt
bewusst bei 400 ms, die Startdrehzahl bei 5 rpm. Damit wird normales Anfahren
sanfter, ohne den Bremsweg des Nahbereichs- und Notstopps zu verlängern.

**Grund / Evidenz:** Bei der ersten vollständigen manuellen LiDAR-Runde
wackelte der hohe Aufbau beim Anfahren stark. Die 100-ms-Einstellung war der
Wert, den die Hardware zuvor ohnehin fuhr; sie war ausdrücklich nur der
unveränderte H2/H3-Ausgangspunkt. Beide realen Antriebe akzeptieren und
bestätigen 2000, während 2500 weiterhin mit Modbus Exception 7 abgelehnt wird.
Der Knoten prüft jeden Schreibzugriff und verweigert bei Ablehnung die
Fahrfreigabe.

Ein begrenzter Bodenversuch mit 1,0 s bei 0,12 m/s ergab **0,0439 m** absoluten
Encoderweg und **0,000°** Kursänderung. Der Nutzer bewertete das Anfahren als
„gut sanft“. Das widerlegt die bisherige Dokumentationsannahme, die
Rampenzeit werde gegen 3000 rpm skaliert und wirke bei Kartiergeschwindigkeit
nur rund 0,12 s: Sie wirkt real wesentlich stärker und offenbar weitgehend
direkt auf die Sollwertänderung.

Die anschließende geschlossene manuelle LiDAR-Runde hatte eine offene
Zimmertür und ist deshalb in Fläche und Ausdehnung nicht A/B-vergleichbar. Der
geometrieunabhängigere Wanddickenanteil blieb praktisch gleich (**37,0 % →
36,7 %**); die weichere Rampe verschlechterte die Karte also nicht, ein
messbarer Kartenqualitätsgewinn ist mit diesem einen Lauf aber nicht belegt.
Der Scan-Normalisierer setzte 4467/4467 Scans auf 2160 Strahlen um; keine
Verwerfung wegen wechselnder Strahlenzahl und kein RS485-/Encoderfehler während
der Fahrt. Karte, Posegraph und Laufprotokoll bleiben ausschließlich lokal.

**Betroffene Dateien und Hardware:** `base_hardware_params.yaml`, Defaultwert
im Basis-Node, Vertragsprüfung und Dokumentation; beide ESS23-RS-Antriebe.

**Teststatus:** 60/60 Base-Hardware-Tests, Build, Python-Kompilierung, Flake8
F/E9 und Diff-Check bestanden. Registerprüfung ohne Bewegung, begrenzter
Bodentest und vollständige manuelle Kartenrunde real bestanden. Nach dem
Joystick-Stopp bestätigte der Watchdog fortlaufend 0 rpm. Eine einzelne
Modbus-Fehlermeldung trat erst beim gemeinsamen SIGINT-Herunterfahren auf,
nachdem der Roboter bereits rund eine Minute stillstand.

**Offene Risiken:** Die exakte Rampenfunktion des ESS23-RS ist noch nicht aus
mehreren Impulsdauern identifiziert. Bremsen bleibt absichtlich ruppiger; ein
Komfort-Smoother muss später vor dem `collision_monitor` liegen, damit dessen
Sicherheitsstopp nicht verzögert wird. Ein erneuter externer H4-Laservergleich
war für diese reine Beschleunigungsänderung nicht Teil des Laufs.

**Rückfallweg:** `accel_ms: 100` wiederherstellen und `base_hardware` neu
bauen. Encoderwerte, Geometrie und Bremsrampe sind von diesem Rückfall
unberührt.

---

## 2026-08-14 — DKMS-Aufraeumen: ein "rm" ohne --force haette den Treiber beim naechsten Boot gekillt

**Entscheidung:** Festgehalten als Warnung. Beim Bereinigen der
DKMS-Dopplung entstand kurzzeitig ein Zustand, in dem der Treiber nach dem
naechsten Neustart nicht mehr geladen haette.

**Grund / Evidenz:** `dkms status` meldete
`installed (WARNING! Diff between built and installed module!)` — in
`/lib/modules` lag noch ein handgebautes Modul, DKMS hatte ein eigenes gebaut.
Der Versuch, das mit `rm` der alten Datei plus `dkms install` zu loesen, ging
schief: **DKMS haelt sich laut eigenem Status fuer installiert und ueberspringt
den Einbau.** Ergebnis:

```text
Modul im Speicher : laeuft weiter  -> alles schien in Ordnung
Datei in /lib/modules : FEHLT
modules.dep       : 0 Eintraege
modules.alias     : kein Alias
```

Im laufenden Betrieb war nichts zu merken. Erst ein Neustart haette den
Nahbereichsschutz stillschweigend getoetet — dieselbe Klasse von Fehler, die
den ganzen Tag gekostet hat.

**Behebung:** `dkms uninstall --all` bringt die Buchfuehrung mit der Realitaet
in Einklang, danach installiert `dkms install` wirklich. Ein reines
`dkms install` nach einem `rm` reicht **nicht**.

**Endzustand geprueft:** `installed` ohne Warnung; Modul unter
`/lib/modules/5.15.199-tegra/updates/dkms/` (DKMS-eigenes Verzeichnis, hat
Vorrang); `modules.dep` 1 Eintrag; Alias `usb:v1A86p5512… → ch34x_mphsi_master`
wieder da; installierte Datei identisch mit dem DKMS-Build; Startpruefung
vollstaendig gruen.

**Lehre:** Beim Hantieren an Kernelmodulen sagt der laufende Betrieb **nichts**
ueber die Bootfaehigkeit. Nach jedem Eingriff sind drei Dinge zu pruefen, nicht
nur `lsmod`: die **Datei** in `/lib/modules`, der Eintrag in **`modules.dep`**
und der **Alias** in `modules.alias`. Genau das prueft
`tools/kartierung/nahbereich_pruefen.py` inzwischen mit ab.

**Betroffen:** kein Projektcode.

**Rueckfallweg:** Modul neu bauen ueber
`tools/kartierung/setup_ch34x_treiber.sh`, dann DKMS wie oben.

---

## 2026-08-14 — CH341-Treiberquelle gepinnt und DKMS eingerichtet

**Entscheidung:** Der WCH-Treiber wird wie der STL-27L-Treiber und
`slam_toolbox` als **gepinntes Vendor-Manifest** gefuehrt:
`vendor_ch34x_mphsi.repos`, Commit `f33863f` von
`WCHSoftGroup/ch34x_mphsi_master_linux`. Aufbau ueber
`tools/kartierung/setup_ch34x_treiber.sh`.

**Grund / Evidenz:** Die Quellen lagen unversioniert in `~/`. Waeren sie
verschwunden, haette niemand mehr gewusst, welcher Stand gebaut war — und nach
dem naechsten Kernel-Update waere der Nahbereichsschutz erneut lautlos
ausgefallen. Geprueft: Quellcode gegenueber `f33863f` **unveraendert**, einzige
Ergaenzung ist die `dkms.conf`.

DKMS ist eingerichtet und greift ueber `/etc/kernel/postinst.d/dkms` bei jeder
Kernel-Installation; `AUTOINSTALL="yes"` meldet unser Modul dafuer an. Damit
baut es sich kuenftig selbst neu.

**Betroffen:** `vendor_ch34x_mphsi.repos` (neu),
`tools/kartierung/setup_ch34x_treiber.sh` (neu).

**Teststatus:** Skript erkennt den vorhandenen gepinnten Stand, baut fehlerfrei
gegen 5.15.199-tegra und prueft das `vermagic` gegen den laufenden Kernel. Die
root-Schritte werden bewusst nur ausgegeben, nicht ausgefuehrt.

**Offene Risiken:** `/usr/src/ch34x-mphsi-1.0` ist ein Symlink ins
Home-Verzeichnis. Wird es verschoben, kann DKMS nach einem Kernel-Update nicht
mehr bauen. Das Manifest erlaubt dann aber, den Stand wiederherzustellen.

**Rueckfallweg:** `sudo dkms remove -m ch34x-mphsi -v 1.0 --all`; das Modul fuer
5.15.185 liegt weiterhin unter `/lib/modules/5.15.185-tegra/`.

---

## 2026-08-14 — Startpruefung: der Nahbereichsschutz kann nicht mehr lautlos fehlen

**Entscheidung:** `tools/kartierung/nahbereich_pruefen.py` prueft den
Nahbereichsschutz, und `start_lidar_slam.sh` verweigert den Start mit
`active_drive:=true`, wenn die Pruefung durchfaellt. Bewusst **nicht** in
`base_hardware` eingebaut — dessen Motorcode hat gerade die H0-bis-H4-Abnahme
bestanden, dort kommt jetzt keine neue Abhaengigkeit hinein.

**Grund / Evidenz:** Der Ausfall vom 14.08.2026 war lautlos. `vl53_near_field`
starb beim Start, der `collision_monitor` aktivierte sich trotzdem sauber und
reichte **jeden** Fahrbefehl durch. Kein Fehler beim Booten, keine Warnung —
nur ein Sicherheitssystem, das zur Attrappe geworden war. Aufgefallen ist es
allein, weil zufaellig jemand hinsah.

Die Pruefung prueft vier Dinge, und Punkt 3 ist der entscheidende:

1. Kernelmodul `ch34x_mphsi_master` geladen;
2. CH341-I2C-Bus vorhanden;
3. **beide Punktwolken-Topics veroeffentlichen tatsaechlich** — ein laufender
   Knoten beweist nichts, ein laufender Monitor erst recht nicht;
4. `collision_monitor` laeuft.

**Teststatus:** Alle vier Faelle am Geraet geprueft. Fehlerfall meldet
namentlich, was fehlt, und gibt 1 zurueck. Gutfall gibt 0 zurueck. Der
Startversuch mit `active_drive:=true` bei abgeschaltetem Schutz brach ab, ohne
einen einzigen Knoten zu starten. Ohne `active_drive` greift das Tor nicht —
`dry_run=True, allow_rs485=False` wie zuvor.

**Bewusster Ausweg:** `AMADEUS_OHNE_NAHBEREICH=1` schaltet den Start ohne Schutz
frei — fuer beaufsichtigte Fahrten mit Not-Aus in der Hand, wie sie den ganzen
13. und 14.08. gefahren wurden. Der Weg ist absichtlich umstaendlich und muss
je Aufruf gesetzt werden.

**Was die Pruefung NICHT leistet:** Sie sagt nicht, ob der Monitor auch bremst —
dafuer braucht es ein Hindernis in der Zone. Und leere Wolken sind kein Fehler:
Der Schutz wirkt nur innerhalb von 50 cm.

**Betroffen:** `tools/kartierung/nahbereich_pruefen.py` (neu),
`tools/kartierung/start_lidar_slam.sh`,
`src/vl53_near_field/config/ch34x_dkms.conf.example` (neu). Keine Motoren
bestromt.

**Offene Risiken:** Die Pruefung laeuft beim Start, nicht dauerhaft. Faellt der
Sensor waehrend der Fahrt aus, faengt sie das nicht. Ein laufender Waechter
waere der naechste Schritt.

**Rueckfallweg:** Das Tor greift nur bei `active_drive:=true`; entfernen liesse
es sich durch Loeschen des Blocks in `start_lidar_slam.sh`.

---

## 2026-08-14 — Nahbereichsschutz wieder in Betrieb: Kernel-Update hatte den Treiber verwaist

**Entscheidung:** Das Out-of-Tree-Modul `ch34x_mphsi_master` wurde gegen den
laufenden Kernel neu gebaut und bootfest installiert. Der Nahbereichsschutz ist
wieder nachweislich funktionsfähig.

**Grund / Evidenz:** Am 13.08.2026 war hier notiert, der Schutz sei
„funktionslos" und der WCH-Treiber müsse erst gebaut werden. **Das war eine
Fehldiagnose.** Der Hinweis des Nutzers auf die früheren VL53-Abnahmen
(`1f48b2c`, `6ee8c62`, `6a6b397`) führte zur wahren Ursache:

```text
Modul gebaut fuer : 5.15.185-tegra
laeuft gerade     : 5.15.199-tegra
DKMS              : nicht installiert
```

Ein **Kernel-Update** hat das Modul verwaist. Ohne DKMS wird es nicht neu
gebaut, deshalb lud es seit dem Update nicht mehr. Der Projektcode war nie
kaputt.

Nach `make` gegen die Header von 5.15.199 und `sudo make install`: `i2c-10 —
ch34x-mphsi-i2c` erscheint, der Multiplexer `0x70` antwortet, der Knoten findet
den Bus selbst. Mit einem Objekt in ~20 cm melden **beide Sensoren 64 von 64
Zonen** bei 0,18–0,26 m, `target_status` 5 durchgehend, alle vier Filter
passiert.

**Bremsnachweis ohne Motorstrom** — `collision_monitor` ohne `base_hardware`
betrieben, Fahrbefehl hinein, Ausgang beobachtet:

| Zustand | Ergebnis |
|---|---|
| Objekt in der Zone | **2914 von 2914** auf null gebremst |
| freie Bahn | **133 von 165** unverändert mit 0,100 m/s durchgereicht |

**Drei Fallen, damit sie niemanden erneut kosten:**

1. `z_min`/`z_max` heißen so, sind aber **Distanzgrenzen**. Der Schutz wirkt nur
   innerhalb von 50 cm; „0 Punkte" im freien Raum ist korrekt. Der Boden
   erscheint bei 0,60–0,72 m und wird bewusst weggefiltert.
2. `stop_pub_timeout: 2.0` — nach einem Stopp publiziert der Monitor noch zwei
   Sekunden Nullen und schweigt dann. Ausbleibende Nachrichten heißen „Stopp
   hält an", nicht „Monitor tot".
3. Eigene Diagnosewerkzeuge brauchen zwei Dinge, die der ROS-Knoten schon tut:
   `VL53L5CX_COMMS_CHUNK_SIZE = 32` (sonst `OSError(5)` beim Firmware-Upload,
   der CH341A schafft nur ~32 Byte je Transaktion) und `set_resolution(64)`
   (sonst bleibt der Sensor im 4×4-Modus und nur 16 der 64 Zellen tragen Daten —
   das sah kurz wie ein Projektfehler aus, war aber einer im Prüfwerkzeug).

**Betroffen:** kein Projektcode; `~/ch34x_mphsi_master_linux/driver` neu gebaut
und installiert. Keine Motoren bestromt, keine Bewegung.

**Teststatus:** Treiber geladen, Bus erkannt, beide Sensoren geprüft, Bremsen
und Durchreichen je einzeln nachgewiesen.

**Offene Risiken:** **Ohne DKMS bricht das beim nächsten Kernel-Update erneut.**
Unverändert bestehen die beiden physischen blinden Flecken: maskierter
Mastsektor nach hinten, LiDAR-Scanebene auf 75 cm.

**Rückfallweg:** `sudo make uninstall` im Treiberverzeichnis; das für 5.15.185
gebaute Modul liegt als Sicherung unter
`/tmp/ch34x_mphsi_master_5.15.185.ko.bak`.

---

## 2026-08-14 — Semantische Räume auf Jetson und echtem iPhone abgenommen

**Entscheidung:** Der passive semantische Kartenpfad ist auf dem realen Jetson
und einem physischen iPhone für die nächste Stufe freigegeben. Diese Freigabe
umfasst Kartenanzeige, manuelles Speichern, Raum-Overlay, Revisionen und
Persistenz, aber ausdrücklich keine Raumfahrt.

**Grund / beobachtete Evidenz:** Vor dem Start waren auf dem Jetson keine ROS-,
Motor- oder Navigationsknoten aktiv und der Workspace war sauber. Der Branch
`feature/semantic-map-editor` wurde ohne Überschreiben lokaler Änderungen
übernommen. Der ROS-2-Humble-Build der sechs Pakete `robot_map_manager`,
`semantic_map_manager`, `mission_manager`, `llm_planner`,
`semantic_perception` und `robot_bringup` bestand. Anschließend bestanden alle
**162/162 Python-Vertragstests** auf dem Jetson.

Für den fahrbewegungsfreien End-to-End-Test liefen ausschließlich die statische
`testwohnung`, eine statische TF, `robot_map_manager`, `semantic_map_manager`
und rosbridge. `/cmd_vel` existierte nicht. Die nativ signierte Amadeus-App
wurde auf dem echten iPhone installiert und verband sich über WLAN. Der Nutzer
speicherte die Karte bewusst in der App und zeichnete den Raum `Test` mit vier
Eckpunkten und einem inneren Zielpunkt. Kartenmanager, App und Semantikmanager
verwendeten denselben Fingerabdruck; das Overlay wechselte von Revision 0 auf
1 und erschien im Katalog. Nach einem echten Neustart des Semantikmanagers
wurde Revision 1 aus `~/.local/share/amadeus/semantic_maps/` wiederhergestellt.
Nach Neustart der App verband sie sich ohne erneute URL-Übergabe, womit die
gespeicherte rosbridge-Adresse ebenfalls bestätigt ist.

Die passiven Negativtests wurden anschließend ebenfalls auf dem echten Jetson
ausgeführt. Nach Abschalten von `robot_map_manager` und rosbridge sperrte der
Semantikmanager den unverändert gespeicherten Raum nach mehr als sechs
Sekunden mit `ok:false` und `editable:false`. Nach Wiederanlauf derselben Karte
wurde Revision 1 ohne Datenverlust wieder editierbar. Ein absichtlich mit
`base_revision:0` gesendetes Update gegen Revision 1 wurde als veraltet
abgelehnt; `current.json` blieb auf Revision 1. Ein temporär allein ergänzter
`mission_manager` löste `go_to_room` für `Test` ausschließlich als
`simulation_only_no_navigation` auf. Vor und nach diesem Versuch existierte
kein `/cmd_vel`-Topic.

Der erste Geräte-Start zeigte außerdem, dass der bisherige App-Standard
`roboter.local` im realen WLAN nicht auflösbar war. Der vorhandene Jetson-
Hostname `p-desktop.local` löste dagegen stabil auf und wurde für den Test
einmalig übergeben. Die App verwendet ihn nun als Standard für frische
Installationen; eine bereits vom Nutzer gespeicherte Adresse behält Vorrang.

Beim Neustarttest wurde ein doppelter `rclpy.shutdown()` nach SIGINT sichtbar:
Der Node war bereits beendet, meldete aber fälschlich Exitcode 1. Der Einstieg
fängt `KeyboardInterrupt` nun ab und ruft Shutdown nur bei `rclpy.ok()` auf;
ein Quellvertragstest schützt diesen Pfad.

**Betroffene Dateien und Hardware:**
`semantic_map_manager_node.py`, sein Vertragstest und diese Übergabedokumente;
`RobotController.swift` und das iOS-Gedächtnisprotokoll; Jetson `p-desktop` und
physisches iPhone. Die Testkarte und der Raum liegen nur im lokalen Amadeus-
Datenspeicher und nicht im Repository.

**Teststatus:** Jetson: sechs Pakete gebaut, **162/162 Python-Tests** grün,
ROS-Topics und Persistenz live geprüft. iPhone: Gerätebuild, Installation,
App-/Karten-WebSocket, manuelles Save, Raum-Upsert und App-Neustart bestanden.
Der SIGINT-Fix wurde zusätzlich durch erneuten Build, Test und kontrolliertes
Beenden auf dem Jetson geprüft. Stale-Sperre, Wiederanlauf, veraltete Revision
und simulierte Raumzielauflösung bestanden als reale, fahrbewegungsfreie
Negativtests.

**Offene Risiken:** Getestet wurde bewusst die statische Testkarte, nicht eine
neue reale Wohnungskarte. Ein tatsächlicher Kartenwechsel auf eine andere
Geometrie und der vollständige Editorlauf auf dieser Wohnungskarte bleiben
offen. Rosbridge bleibt im lokalen WLAN unverschlüsselt und unauthentifiziert.
Reale Navigation sowie VL53-/Collision-Schutz sind weiterhin gesperrt.

**Rückfallweg:** Die passiven Testprozesse beenden;
`start_semantic_map_manager:=false` oder `use_dynamic_catalog:=false` setzen.
Die versionierten lokalen Overlay-Dateien nicht löschen; sie sind unabhängig
vom Git-Workspace.

## 2026-08-14 — Manuelle semantische Räume vollständig implementiert

**Entscheidung:** Die erste semantische Ausbaustufe besteht ausschließlich aus
vom Nutzer in der nativen Amadeus-App gezeichneten Räumen. Jeder Raum wird als
Polygon mit ID, Name, Farbe und einem inneren Navigationspunkt gespeichert und
unveränderlich an den SHA-256-Fingerabdruck einer gespeicherten metrischen
Karte gebunden. Gegenstände und automatische Raumsegmentierung bleiben eine
spätere, getrennte Ausbaustufe. `go_to_room` löst den Punkt nur auf und bleibt
hart im Simulationsmodus; es existiert in diesem Stand kein Nav2-/`cmd_vel`-
Pfad für Raumziele.

**Grund / beobachtete Evidenz:** Die vorhandene OccupancyGrid-Karte besitzt
Geometrie, aber keine stabilen Raumnamen. Ein separates Overlay lässt die SLAM-
Karte unverändert und verhindert über Fingerabdruck, Geometrie und Revision,
dass Räume nach einem Kartenwechsel still auf die falsche Wohnung angewendet
werden. App, Backend und Kartenmanager berechnen denselben Fingerabdruck. Ein
Erst-Overlay ist erst nach einem bestätigten manuellen Kartenspeichern erlaubt;
ein vorhandenes Overlay darf bei identischem Fingerabdruck nach Neustart wieder
aktiv werden. Stale Statusdaten, verlorene ACKs, Revisionskonflikte und fremde
Karten sperren Bearbeitung fail-closed.

Während des Cross-Contract-Reviews wurde zusätzlich ein alter Replaypfad im
`robot_map_manager` gefunden: Eine idempotente Wiederholung konnte einen
historischen Vollstatus erneut auf dem globalen Statustopic publizieren. Der
Cache enthält nun nur noch unveränderliche Kommandoergebnisfelder; Karte,
Speicher, Pose, Zeit und Zähler werden bei jedem Replay aus dem aktuellen
Zustand aufgebaut. Dasselbe Prinzip gilt im `semantic_map_manager`.

Das Cross-Contract-Review trennte außerdem manuelle Räume von den bereits
realen Missions-Allowlists: Der dynamische Katalog darf ausschließlich Räume
liefern. Objekte, Ablageziele und `pick_and_place`-Räume bleiben statisch;
ein gezeichnetes Polygon kann deshalb keine reale Behavior-Tree-Mission
freischalten. Semantikstatus müssen `editable:true` sein und verfallen im
Missionsmanager nach sechs monotonic gemessenen Sekunden. Alle JSON-Eingänge
sind gegen Größe, Rekursion und ungültiges Unicode begrenzt.
Da die Prüfung einfacher Polygone Kantenpaare vergleicht, begrenzen Backend,
Mission, App und Mock zusätzlich jeden Raum auf 64 und das Gesamtdokument auf
4.096 Polygonpunkte. So kann ein formal gültiger Extremstatus keine ROS-
Callbackverarbeitung über viele Sekunden blockieren.
Die App verlangt für Save, Overlay, Mutation und ACK zusätzlich einen aktuellen
Kartenmanagerstatus mit `ok:true`; ein Fehlerstatus mit noch passender Summary
kann die Bearbeitung nicht kurzzeitig offenhalten.

**Betroffene Dateien und Hardware:** neues Paket `src/semantic_map_manager/`;
iOS-Raumeditor in `ios/Robotersteuerung/`; read-only Semantikkonsumenten in
`mission_manager` und `llm_planner`; passiver Bring-up-Include; getrennter
Wahrnehmungskatalog; Replay-Härtung im `robot_map_manager`; vollständiger
Vertrag in `docs/SEMANTIC_MAP_INTEGRATION.md`. Keine Hardware wurde bewegt und
keine echten Wohnungsdaten liegen im Repository.

**Teststatus:** Auf dem Entwicklungs-Mac bestanden **162 Python-Vertragstests**
(51 Semantik-Backend, 38 Mission, 15 LLM-Planer, 51 Kartenmanager, 2 Bring-up,
5 zustandsbehafteter rosbridge-Mock) und **39 Swift-Tests**. Mypy, Flake8
`F/E9`, Python-Kompilierung, YAML/XML, fünf isolierte Python-Wheels und
`git diff --check` waren grün. Der vollständige unsigned iOS-Simulator-Build
für arm64/x86_64 bestand mit Swift-/Clang-Warnungen als Fehler; App und Mock
starteten im iPhone-17-Pro-Simulator. Der nachfolgende Jetson-/iPhone-Test ist
im unmittelbar darüberstehenden Eintrag protokolliert.

**Offene Risiken:** Reale Raumfahrt bleibt gesperrt, bis Kartenladen,
Lokalisierung, Costmap-Freiraum, Planbarkeit, Abbruchpfade und insbesondere der
derzeit fehlende VL53-/CH341-Nahbereichsschutz separat bestanden sind. Die
erste Stufe prüft den Zielpunkt geometrisch im Polygon, aber noch nicht gegen
belegte/unbekannte Zellen oder Erreichbarkeit. Polygonüberlappungen sind
erlaubt; Objekte und automatische Segmentierung fehlen bewusst. Rosbridge ist
im aktuellen lokalen Netz weder authentifiziert noch verschlüsselt.

**Rückfallweg:** `start_semantic_map_manager:=false` lässt den passiven Node
beim Bring-up aus. `use_dynamic_catalog:=false` stellt die statischen
Kataloglisten wieder her. Ohne passenden Semantikstatus bleibt der bestehende
Karten-Tab reine Anzeige und sendet keine Raumänderung. Diese Rückfälle
aktivieren keine Fahrt.

## 2026-08-13 — H4 bestanden: der feste Versatz je Fahrt ist weg

**Entscheidung:** Der Encoderpfad (`odometry_source: encoder_position`) bleibt
scharf. Der über Wochen reproduzierte feste Odometrieversatz je Fahrt ist
beseitigt.

**Grund / Evidenz:** Fahrtest mit dem **Lasermessgerät** als externer Referenz,
Positionen auf dem Maßband abgelesen (0,395 → 1,219 → 1,443 → 1,674 → 1,907 m):

| Fahrt | Laser | Odometrie | Abweichung |
|---|---|---|---|
| 1× 0,80 m | 824,0 mm | 825,9 mm | **−1,9 mm** |
| Etappe 1 | 224,0 mm | 223,6 mm | +0,4 mm |
| Etappe 2 | 231,0 mm | 231,7 mm | −0,7 mm |
| Etappe 3 | 233,0 mm | 231,1 mm | +1,9 mm |
| Etappe 4 | 227,0 mm | 226,6 mm | +0,4 mm |
| **4× 0,20 m gesamt** | **915,0 mm** | **913,0 mm** | **+2,0 mm** |

**Das Abnahmekriterium der Übergabe ist damit erfüllt.** Der Zusatzfehler der
drei weiteren Start-Stopp-Vorgänge sank von **+51,9 mm auf +3,9 mm**, also um
92 %. Der Skalenfehler beträgt +0,23 % und die Kursabweichung +0,04° bis
+0,27° — beides unverschlechtert.

**Je Fahrt +0,5 mm statt der bisherigen +17,3 bis +20,1 mm.** Jede einzelne
Fahrt stimmt auf unter 2 mm. Der Skalenfehler beträgt −0,23 % auf 0,824 m, die
Kursabweichung lag bei +0,04° und +0,27° — beides unverschlechtert.

Der Mechanismus ist im Detail sichtbar: Eine kommandierte 0,20-m-Etappe meldet
über den Encoder 0,224 bis 0,233 m, und der Laser bestätigt genau diese Werte.
Der Roboter fährt also tatsächlich weiter als kommandiert, weil er ausrollt —
der Drehzahlpfad verschluckte exakt diesen Weg.

**WICHTIG für künftige Kalibrierungen: Der LiDAR-Wandvergleich taugt dafür
nicht.** Bei Lauf 1 meldete er 0,8025 m gegen 0,8240 m laut Laser, also
**21,5 mm daneben** — bei einer eigenen Streuung von nur 1,7 mm. Über alle
Encoder-Läufe streute er zwischen −23,4 und +5,6 mm, während der Laser
durchweg unter 2 mm blieb. Seine geringe Streuung täuscht eine Genauigkeit vor,
die er nicht hat.

**Betroffene Dateien und Hardware:** keine Codeänderung in diesem Schritt; beide
Motoren, fünf Fahrten von zusammen rund 1,7 m auf dem Boden.

**Teststatus:** H0 bis H4 bestanden. Vier unabhängige Fahrt-für-Fahrt-Vergleiche
gegen das Lasermessgerät.

**Offene Risiken:** Die vier `odom_*_variance`-Werte sind weiterhin konservative
Startwerte; ihre Kalibrierung verlangt laut Übergabe mehr Wiederholungen als
hier gefahren. H5 (Fehler- und Wiederanlaufpfade) steht aus.

**Der Nahbereichsschutz ist derzeit funktionslos.** Der `collision_monitor`
startet und aktiviert sich sauber, aber `vl53_near_field` stirbt beim Start mit
„Kein CH341/CH34x-I2C-Bus gefunden (WCH-Treiber geladen?)". Der USB-Adapter
`1a86:5512` steckt, das Kernelmodul `ch34x` ist nicht geladen. Ein Monitor ohne
Sensordaten reicht alles durch. Für autonomes Fahren muss das zuerst in Ordnung
sein; bei diesem Fahrtest ersetzte die Aufsicht der anwesenden Person ihn.

**Rückfallweg:** `odometry_source: speed` stellt den alten Pfad her — mitsamt
seinem Versatz von rund 18 mm je Fahrt.

---

## 2026-08-13 — H2 und H3 bestanden; Encoderpfad ist scharf

**Entscheidung:** `encoder_counts_per_motor_revolution: 1000.0`,
`encoder_expected_segment: 1000`, `encoder_expected_resolution: 4000`. Der
Encoderpfad ist damit entriegelt und läuft. Zusätzlich `accel_ms: 2500 -> 100`,
weil der Antrieb 2500 zurückweist (siehe unten).

**H2, gemessen am aufgebockten Roboter mit freien Rädern.** Verfahren ohne
Abweichung von der Übergabe: Encoderstand strikt lesend vor und nach einem
befristeten Motorlauf; Lesewerkzeug und `base_hardware` liefen **nie**
gleichzeitig. Bodenreferenz war eine Radmarkierung, vom Nutzer in **beiden**
Richtungen mit genau 5 Radumdrehungen bestätigt.

| Lauf | M1 | M2 | Counts/Motorumdrehung |
|---|---|---|---|
| vorwärts 65,3 s | +50040 | −50045 | 1000,8 / 1000,9 |
| rückwärts 65,3 s | −50009 | +50017 | 1000,2 / 1000,3 |

Richtungsunterschied 0,062 % (M1) und 0,056 % (M2). Ein dritter Lauf über
65,0 s ergab konsistent +49804/−49810. Die Gegenrechnung über die kommandierte
Motordrehzahl (46 rpm) ergab 999,4 bis 999,5 — ein völlig anderer Weg, dasselbe
Ergebnis. Der Wert deckt sich mit `0x0011`, wurde aber **nicht** von dort
übernommen.

**H3, aufgebockt:** `/odom` +0,2442 m bei 8 s × 0,03 m/s (erwartet 0,240) und
dabei nur 0,01° Gierwinkel; rückwärts symmetrisch 0,2443 m; Drehung auf der
Stelle 93,33° bei **0,0001 m** Translation (erwartet 91,7°). Null Fehler, null
verworfene Updates, `/odom` mit 16,7 Hz, Watchdog greift. Vorzeichen und
Montageinvertierung stimmen.

**BEFUND MIT EIGENSTÄNDIGEM GEWICHT — die Anfahrrampe war nie wirksam.** Der
neue Branch verweigerte zunächst jede Fahrt: `Anfahrparameter Motor 1, Reg
0x001E nicht bestaetigt`, danach Dauerreconnect ohne einen einzigen Fahrbefehl.
Ursache: Der Antrieb weist `2500` mit
`ExceptionResponse(function_code=134, exception_code=7)` zurück. Abgetastet
liegt die Obergrenze beider Rampenregister bei **2000**.

Ausgelesen standen in `0x001E` auf beiden Motoren **100** — weder die früher
eingetragenen 800 noch die 2500. `0x001F` (400) und `0x0020` (5) stimmten
dagegen. Schreibzugriffe funktionieren also, nur dieser Wert wurde nie
angenommen.

Sichtbar wurde das erst, weil der Encoder-Branch die **Rückgabewerte** der
Schreibvorgänge prüft. Der vorherige Code rief `_write_register` dreimal ohne
jede Auswertung auf. Das erklärt rückwirkend den Eintrag vom 28.07.2026, die
Solldrehzahl sei „nach ~110 ms zu 90 % erreicht, trotz 800-ms-Rampe" — die
Rampe stand nie auf 800.

Eingetragen sind jetzt 100, also exakt der Wert, den die Hardware ohnehin fährt:
Der Schreibvorgang gelingt, der Knoten startet, das Fahrverhalten ändert sich
nicht. Eine wirklich weichere Rampe wäre mit bis zu 2000 möglich und entspräche
der ursprünglichen Absicht — das ist aber eine echte Verhaltensänderung am
Antrieb und gehört nach AGENTS.md 7 in einen eigenen Schritt.

**Betroffene Dateien und Hardware:** `base_hardware_params.yaml`,
`test_base_hardware_node_contract.py`; ESS23-RS IDs 1/2. Beim Messen drei
Motorläufe zu je 65 s und drei zu je 8 s, Roboter aufgebockt, Räder frei.

**Teststatus:** 59 base_hardware-Tests und 12 Werkzeugtests grün. Der Test
`test_unknown_counts_fail_closed` prüfte wörtlich die Inbetriebnahme-Nullen;
er nagelt jetzt das H2-Ergebnis fest. Die fail-closed-Logik im Node blieb
unverändert — wer wieder 0 einträgt, verriegelt den Pfad erneut.

**Offene Risiken:** Einzelne Räder ließen sich nicht getrennt ansteuern, weil
`cmd_vel` immer beide bedient; H3 deckt diesen Punkt daher nur gemeinsam ab.
Fehler- und Wiederanlaufpfade (H5) wurden nicht provoziert. H4, also die
Bodenfahrt mit A/B gegen die alten 51,9 mm, steht aus. Ob der Encoder
Handschieben erfasst, ist weiterhin unbeantwortet — die Antriebe halten die
Welle auch ohne jeden Master am Bus, ein Handversuch ist damit ausgeschlossen.

**Rückfallweg:** `odometry_source: speed`, oder die drei Encoderwerte wieder
auf 0. `accel_ms` zurück auf 2500 würde den Startfehler erneut auslösen.

---

## 2026-08-13 — Encoder-Fix auf dem Jetson geprüft: Offline-Tests und H1 bestanden

**Entscheidung:** Der Branch `fix/encoder-position-odometry` (`9f7d339`) ist auf
dem Jetson gebaut, offline geprüft und die read-only Registerprobe H1 ist
bestanden. `encoder_counts_per_motor_revolution` bleibt bei `0` — der reale
Positionsmodus ist damit weiterhin verriegelt.

**Grund / Evidenz:** Der geforderte eigene Jetson-Lauf (Mac- und CI-Ergebnisse
zählen dafür ausdrücklich nicht):

- `colcon build --packages-select base_hardware` fehlerfrei;
- 59 base_hardware-Tests bestanden;
- 12 Tests des read-only Inbetriebnahmewerkzeugs bestanden;
- `colcon test-result --verbose`: 59 Tests, 0 Fehler, 0 Fehlschläge.

Die gepinnten Abhängigkeiten waren bereits erfüllt: Pymodbus **3.14.0** und
Pyserial **3.5** sind installiert, exakt wie in `requirements-modbus.txt`
gefordert. Es musste nichts nachinstalliert werden, der laufende Antrieb blieb
also unberührt.

**H0:** keine Amadeus-Knoten aktiv, `/dev/ttyUSB_BASE` von keinem Prozess
gehalten, Arbeitskopie sauber auf `9f7d339`.

**H1, ausschließlich lesend:** Beide Motoren antworten stabil per FC03 mit rund
5 ms je Zugriff. Beidseitig identisch gelesen:

```text
Motor 1: 0x0011=1000, 0x0019=0 (high/low), 0x0101=4000
Motor 2: 0x0011=1000, 0x0019=0 (high/low), 0x0101=4000
```

Ausgangspositionen M1 `+48955`, M2 `−49028`; die gegenläufigen Vorzeichen passen
zur spiegelbildlichen Montage. Über 40 Proben je Motor blieb das Delta **exakt
null** — die Position ist im Stillstand nicht nur „innerhalb erklärbarer
Grenzen" stabil, sondern bitgenau konstant.

**Betroffene Dateien und Hardware:** keine Codeänderung; ESS23-RS IDs 1/2 auf
`/dev/ttyUSB_BASE`, ausschließlich lesend.

**Teststatus:** H0 und H1 bestanden. H2 bis H5 offen.

**Offene Risiken:** `0x0011=1000` und `0x0101=4000` sind exakt die
Handbuchvorgaben. Sie dürfen laut Übergabe **nicht** als Positionseinheit je
Motorumdrehung übernommen werden — das ist genau die Messung, die H2 leistet.

**Praktisches Hindernis für H2:** Die Antriebe halten die Welle mit Moment. Am
13.08.2026 konnte der Nutzer die Räder von Hand nicht drehen, weder nach dem
Stoppbefehl noch bei Solldrehzahl 0. Für eine Handmessung muss der Motor
elektrisch freigegeben werden; ohne Versorgung antwortet er aber nicht mehr auf
Modbus. Wie freigegeben wird, entscheidet laut Übergabe ausdrücklich die
anwesende Person — ein Agent sendet kein Freigabekommando.

**Rückfallweg:** `odometry_source: speed`; für vollständigen Rollback den
Commit `9f7d339` revertieren.

---

## 2026-08-13 — Absolute Encoderposition statt Drehzahlintegration

**Entscheidung:** Die reale Odometrie wird auf die kumulierten ESS-RS-Positionen
`0x000A/0x000B` umgestellt. `0x000C` bleibt Diagnose; bei Lesefehlern wird im
realen Betrieb niemals mehr der Sollwert integriert.

**Grund / Evidenz:** Der reproduzierte feste Fehler betrug 17,3 mm pro
zusätzlichem Stop/Start. 50-Hz-Speed-Polling änderte ihn nicht. Beim Bremsen
meldete `0x000C` zeitweise 0 rpm und später wieder 16 rpm. Die neue Software
erhält jede in `0x000A/0x000B` tatsächlich registrierte Bewegung. Ob diese
Register Handschieben im vorgesehenen Betriebszustand erfassen, ist H2-offen.
Ein einzelner normaler FC03-Fehler behält Client und Baseline; die
Transportfehlerschwelle führt zu Stopp und Reconnect, Ausnahmen/API-Fehler
sofort. Stale Rückmeldung sperrt und stoppt immer, reconnectet aber nur bei
einem zugrunde liegenden Transportfehler.
Ein semantisch ungültiges Paar oder eine Konfigurationsabweichung sperrt und
stoppt dagegen sofort ohne Reconnect. Ein unplausibles Delta wird verworfen und
im Tracker kontrolliert rebased.
Jeder tatsächlich neue Client verwirft die alte Baseline bewusst. Im
Encoderpositionsmodus entsteht `/odom` nur zu einem neuen gültigen Paar
(Ziel etwa 20 Hz), während `state_json` im 50-Hz-Node-Takt weiterläuft.
Der Watchdog nutzt monotone Echtzeit; scharfes RS485 mit `use_sim_time` ist
verboten. `/cmd_vel` hat Queue-Tiefe 1, nicht-endliche Werte fordern Stopp an,
und nur ein nach RPM-Quantisierung darstellbarer Befehl darf starten.

Pymodbus 3.14.0 und Pyserial 3.5 sind in
`src/base_hardware/requirements-modbus.txt` fest gepinnt; interne Modbus-Retries
sind null. Die vier Odometrie-Kovarianzen sind konservative Startwerte und erst
in H4 durch wiederholte externe Referenzmessungen zu kalibrieren.

**Betroffene Dateien/Hardware:** `base_hardware_node.py`,
`encoder_odometry.py`, Parameter, ESS23-RS IDs 1/2 auf `/dev/ttyUSB_BASE`.

**Teststatus:** Auf dem Entwicklungs-Mac bestanden 59
Base-Hardware-Regressionstests und 12 Tests des strikt read-only
Inbetriebnahmewerkzeugs; Syntax geprüft. Keine Motoren aktiviert. Der erneute
Build-/Testlauf auf dem Jetson sowie reale Counts pro Motorumdrehung,
Wortfolge/Vorzeichen und A/B-Fahrt sind offen.
Der Workflow `.github/workflows/encoder-odometry-offline.yml` kompiliert und
testet dieselben Python-Komponenten zusätzlich auf Ubuntu 22.04/Python 3.10;
CI und Mac-Lauf ersetzen die Jetson- und Hardwareabnahme nicht.

**Offene Risiken:** `0x0011` meldet standardmäßig 1000 Unterteilungen,
`0x0101` standardmäßig 4000 Encoder-Counts. Die Einheit der Positionsregister
darf nicht geraten werden. Deshalb blockieren `counts=0` sowie
`encoder_expected_segment=0` oder `encoder_expected_resolution=0` den realen
Positionsmodus. Nach H2 müssen die erwarteten Werte mit den beidseitig
bestätigten read-only Werten aus `0x0011`/`0x0101` verriegelt werden.

**Rückfallweg:** `odometry_source: speed`; auch dort kein Sollwertfallback.
Für vollständigen Code-Rollback diesen Commit revertieren.

---

## 2026-08-12 — Root Cause für fehlende LiDAR-Kartenupdates bei reiner Drehung

**Entscheidung:** Der offizielle `slam_toolbox`-Fix aus PR #808 wird als
minimaler Patch auf einen fest gepinnten Humble-Commit zurückportiert und in
einem separaten Overlay unter `~/amadeus_slam_toolbox_ws` gebaut. Aktiviert wird
er projektspezifisch mit `check_min_dist_and_heading_precisely: true`. Die
apt-Installation unter `/opt/ros/humble` bleibt unverändert.

**Grund / beobachtete Evidenz:** Im selben Lauf veränderte eine 360°-Drehung
**0 von 29.640** Kartenzellen, eine anschließende 40-cm-Translation dagegen
**2.410**. Odometrie/TF drehten korrekt, Mapping-Parameter waren aktiv und
LiDAR, USB sowie Totzonenfilter blieben stabil. Die Humble-Implementierung von
`SlamToolbox::shouldProcessScan()` prüft vor Karto nur
`Pose2::SquaredDistance`, also x/y-Translation. Dadurch erreicht eine reine
Drehung Kartos korrekte Distanz-oder-Winkel-Prüfung nicht. Das entspricht
[Issue #807](https://github.com/SteveMacenski/slam_toolbox/issues/807); der
offizielle Fix wurde in [PR #808](https://github.com/SteveMacenski/slam_toolbox/pull/808)
als Commit `649a50eae698396c40352619c95cd20e2ea1790a` gemergt, fehlt aber im
Humble-Zweig.

**Betroffene Dateien und Hardware:**
`vendor_slam_toolbox_humble.repos`,
`patches/slam_toolbox_humble_pure_rotation.patch`,
`tools/kartierung/build_slam_toolbox_humble_overlay.sh`,
`tools/kartierung/slam_knoten_beobachten.py`,
`tools/kartierung/slam_graph_marker.py`,
`tools/kartierung/test_slam_knoten_beobachten.py`,
`src/amadeus_lidar_bringup/config/slam_toolbox_amadeus.yaml`; Jetson und
STL-27L. Die bestehende Fahrwerkskalibrierung wird nicht verändert.

**Teststatus:** Root Cause durch Quellcode und Messung bestätigt. Backport und
Build-/Stillstandsverfahren sind in `docs/SLAM_TOOLBOX_ROTATION_FIX.md`
dokumentiert. Test am echten Jetson, reine Drehung, Translation und geschlossene
Runde stehen noch aus; keine Aktoren ohne ausdrückliche Freigabe.

**Offene Risiken:** Der LiDAR-Zeitstempel liegt am Ende eines ungefähr 100-ms-
Scans und für diesen Pfad ist kein beamweises Deskew nachgewiesen; schnelle
Drehung kann daher Wände verschmieren, erklärt aber nicht das Null-Update. Im
Odometrie-Drehtest sind Korrekturformel und Korrelationsvorzeichen vor einer
weiteren Kalibrierung für CW und CCW zu verifizieren. Ein synthetischer
Yaw-only-Regressionstest fehlt noch.

**Rückfallweg:** Launch beenden und in einer frischen Shell nur
`/opt/ros/humble/setup.bash` sowie `~/roboter_ws/install/local_setup.bash`
sourcen.
Das separate Overlay wird dadurch ohne Löschung deaktiviert.

---

## 2026-08-13 — Fester Versatz je Fahrt bestätigt, Ursache eingegrenzt

**Entscheidung:** Noch keine. Der Befund wird festgehalten, die Ursache ist
eingegrenzt, aber nicht bewiesen. Es wurde nichts an `base_hardware` geändert.

**Grund / Evidenz:** Der feste Versatz je Fahrt lässt sich **ohne äußeres
Messmittel** nachweisen, indem dieselbe Gesamtstrecke einmal am Stück und
einmal in Etappen gefahren wird — der Skalenanteil ist dann in beiden Fällen
gleich, der feste Anteil fällt einmal beziehungsweise N-mal an:

| | Odometrie | LiDAR | Abweichung |
|---|---|---|---|
| 1× 0,80 m | 0,8019 m | 0,8305 m | +28,6 mm |
| 4× 0,20 m | 0,8215 m | 0,9020 m | +80,5 mm |

Drei zusätzliche Fahrten kosten 51,9 mm, also **17,3 mm je Fahrt**. Die
Wandabstände wurden über 15 Scans gemittelt; ihre Streuung lag bei 1,0 bis
3,4 mm, der Effekt ist also weit außerhalb des Messrauschens.

**Was die Ursache NICHT ist:** Die Odometrie integriert sehr wohl die gemessene
Ist-Drehzahl, nicht den Sollwert — 153 Motor-rpm ergeben rechnerisch
0,09999 m/s, was in der Anzeige als 0,1000 erscheint und einen zunächst in die
Irre führt. Quantisierung (0,65 %) wäre ein Skalenfehler und steckt bereits im
Radradius. Ein reiner Zeitverzug hebt sich über eine Fahrt aus dem Stillstand
mathematisch exakt auf.

**Was auffällt:** Während der Bremsphase ist die Rückmeldung unbrauchbar. Nach
einem Stoppbefehl bei t=3,04 s meldete das Register bei t=3,12 s **null**, bei
t=3,47 s dann wieder **16 rpm** — die Räder drehten also noch. Dazu passt, dass
`feedback_period_s: 0.1` nur 10 Stützstellen je Sekunde liefert, während mit
50 Hz integriert wird; über eine Bremsung bleiben vier Werte.

**Zusätzlicher Codebefund, unabhängig davon:** Schlägt eine Modbus-Leseanfrage
fehl, setzt `_poll_speed_feedback` `feedback_ok = False`, und `_update` fällt
**stillschweigend auf den KOMMANDIERTEN Wert zurück**. Während eines Stopps ist
das Kommando null — ein Lesefehler genau dort lässt die Odometrie also exakt den
Weg verlieren, den der Roboter noch ausrollt, ohne jede Warnung. Das ist
unabhängig vom Hauptbefund ein Mangel.

**Betroffen:** noch nichts geändert. Neue Werkzeuge:
`tools/kartierung/odometrie_versatz_messen.py` und
`tools/kartierung/start_lidar_slam.sh`.

**Teststatus:** Der Versatz ist reproduziert und quantifiziert, die Ursache
nicht bewiesen.

**Nächster Schritt:** `feedback_period_s` von 0.1 auf 0.02 setzen und dieselbe
A/B-Messung wiederholen. Schrumpft der Versatz deutlich, war die Unterabtastung
die Ursache. Dafür muss der Roboter zuvor umgesetzt werden — vor ihm sind nur
noch rund 0,9 m frei, und rückwärts ist er blind.

**Offene Risiken:** Der Versatz wirkt sich bei vielen kurzen Fahrten stärker aus
als bei wenigen langen. Für Nav2 mit häufigen Stopps ist das relevant.

---

## 2026-08-12 — Odometrie neu kalibriert; ein Teil des Fehlers ist kein Radiusfehler

**Entscheidung:** `wheel_radius_m: 0.0624` und `wheel_separation_m: 0.3845`
(vorher 0.0612 / 0.3755). Der verbleibende Fehler von rund 15 mm je Fahrt ist
**kein Kalibrierproblem** und wird nicht über die Radgeometrie ausgeglichen.

**Grund / Evidenz:** Acht Fahrten mit dem Lasermessgerät, jede in Radumdrehung
umgerechnet, weil zwischendurch der Radius verstellt wurde:

```text
echte Strecke = 15 mm + 0.0625 m * Radumdrehung [rad]
                ^^^^^   ^^^^^^^^
                je FAHRT konstant, unabhaengig von der Laenge
```

Ausgleich über alle acht Fahrten (Hebel 5,1 bis 40,4 rad): wirksamer Radius
0,06252 m, fester Versatz 15,1 mm, größte Restabweichung 8,2 mm. Der gesetzte
Wert 0,0624 liegt 0,2 % darunter — unter dem Messrauschen, deshalb belassen.

**Der Weg dorthin ist die eigentliche Lehre.** Aus den ersten vier Fahrten
(alle zwischen 0,41 und 1,01 m) kamen je nach Auswertung Radien zwischen 0,0621
und 0,0631 heraus; eine daraus abgeleitete Vorhersage wurde anschließend
widerlegt. Fester Versatz und Skalenfaktor sind stark korreliert, solange alle
Fahrten ähnlich lang sind. Erst der Hebel aus einer **kurzen und einer langen**
Fahrt (0,30 m gegen 2,50 m) trennt beide: bei 0,30 m macht ein 15-mm-Versatz
5 % aus, bei 2,50 m nur 0,6 %. Zwei unabhängige Auswertungen — der Gesamtausgleich
und der Hebel allein — lagen danach 0,13 % auseinander.

Dass der Versatz **je Fahrt** anfällt, wurde getrennt belegt: zweimal 0,50 m
einzeln gefahren ergab zusammen 1,068 m bei 1,021 m gemeldet, dieselbe Strecke
am Stück nur 1,044 m bei 1,012 m. Vorhergesagt waren 1,072 m für „Versatz je
Fahrt" gegen 1,053 m für „nur einmal". Die abschließende Verifikationsfahrt über
2,00 m sagte 2,021 m voraus, gemessen wurden 2,030 m.

**Historischer Verdacht zum damaligen Messzeitpunkt, nicht bestätigt:** Beim
Anfahren könnten sich die Räder vor einer brauchbaren Ist-Drehzahl-Rückmeldung
drehen. Der spätere 50-Hz-Test widerlegte reine Unterabtastung; der interne
Mechanismus von `0x000C` blieb offen. Der aktuelle, getrennte Encoderpfad steht
im Eintrag vom 13.08.2026 am Dokumentanfang.

**Warum das früher niemand fand:** Eine Winkelmessung bestimmt nur das
Verhältnis r/W, nie die Spurweite allein. Radius und Spurweite waren beide rund
2 % zu klein, aber im fast gleichen Verhältnis — die Drehung stimmte auf 0,4 %,
die Strecke lag 2,5 % daneben. Nur eine Streckenmessung kann das aufdecken.

**Der LiDAR-Wandvergleich taugt nicht als alleinige Referenz.** Bei der
Verifikationsfahrt meldete er 2,006 m gegen 2,030 m per Laser — 24 mm daneben,
bei einer sonstigen Streuung von ±5 mm. Der Roboter endete dort 0,94 m vor der
Wand, deutlich näher als sonst. Für Kalibrierentscheidungen immer das
Lasermessgerät heranziehen.

**Betroffen:** `src/base_hardware/config/base_hardware_params.yaml`. Beim Messen
beide Motoren, acht Fahrten zwischen 0,30 und 2,50 m.

**Teststatus:** Verifikationsfahrt über 2,00 m innerhalb der Ablesegenauigkeit
getroffen. Kursabweichung über alle Fahrten zwischen −0,51° und +0,28°.

**Offene Risiken:** Der feste Versatz von 15 mm je Fahrt bleibt bestehen und
wirkt sich bei vielen kurzen Fahrten stärker aus als bei wenigen langen. Die
wirksame Spurweite liegt 6,5 mm über der abgemessenen — plausibel durch
Aufstandspunkt und Reifenradieren, aber nicht unabhängig bestätigt.

**Rückfallweg:** `wheel_radius_m: 0.0612` und `wheel_separation_m: 0.3755` in
`base_hardware_params.yaml`, dann `colcon build --packages-select base_hardware`.

---

## 2026-08-12 — Winkelfehler war ein Messartefakt; Phase 4a bestanden

**Entscheidung:** Der Winkelfehler der Odometrie wird künftig mit
`tools/kartierung/odometrie_winkel_messen.py` bestimmt, nicht mehr mit
`odometrie_drehtest.py`. Die Kalibrierwerte bleiben unverändert.

**Grund / Evidenz:** Die zuvor über vier Läufe reproduzierten −4,98° bis −6,50°
je Umdrehung waren ein Artefakt des Messverfahrens. `odometrie_drehtest.py`
vergleicht nur Anfangs- und Endscan, liest `/scan` mit schwankender
Strahlenzahl und summiert die Odometrie nicht über die Bremsphase. Der zweite
Punkt wiegt am schwersten: da nur gleich lange Scans vergleichbar sind, blieben
im Versuch **22 von rund 250 Messpunkten** übrig, bei einer Vergleichsgüte von
0,70 m statt 0,03 m — die Verfolgung verlor zwischen den Scans die Spur und
lieferte einen Skalenfaktor von 0,80, also 20 % Fehler. Offensichtlich Unsinn.

Kontinuierlich gemessen auf `/scan_normiert`, je eine volle Umdrehung bei
0,25 rad/s:

| Richtung | Messpunkte | Skalenfaktor | R² |
|---|---|---|---|
| gegen den Uhrzeigersinn | 283 | 0,99628 | 0,9973 |
| im Uhrzeigersinn | 283 | 0,99564 | 0,9974 |

Beide Richtungen stimmen auf 0,00064 überein — das Verhalten eines echten
Skalenfehlers, kein richtungsabhängiger Effekt. **−1,45° je Umdrehung**, also
0,4 %. Der Widerspruch zu den 0,50° aus `9e8c06f` ist damit aufgelöst.

Wichtig für spätere Kalibrierungen: Die Winkelmessung bestimmt nur das
**Verhältnis** von Radradius zu Spurweite, nicht die Spurweite selbst. Der
Streckentest über 0,40 m ergab 0,411 m gemeldet gegen 0,427 m per LiDAR
(+3,9 %). Zusammen mit dem Winkelfaktor folgt daraus eine um 4,3 % größere
Spurweite — nicht die 0,4 %, die der Winkel allein nahelegt. Beide Werte
gehören gemeinsam gesetzt und gemeinsam geprüft.

**Phase 4a bestanden:** 0,40 m Translation erzeugte 20 neue Knoten, die Karte
blieb einwandig, Kursabweichung +0,18°, Nebenachse 3,85 m gegen real 3,80 m.

**Betroffen:** `tools/kartierung/odometrie_winkel_messen.py` (neu),
Dokumentation. Beim Messen beide Motoren, drei volle Umdrehungen und 0,40 m
Fahrt.

**Teststatus:** Zwei Messläufe je Richtung, seitlicher Versatz 0,0–0,1 cm.

**Offene Risiken:** Der Radradius ist ungeprüft; die +3,9 % beruhen auf einer
einzigen LiDAR-Wandmessung und brauchen eine Gegenmessung mit dem
Lasermessgerät. Ein Deskew fehlt weiterhin.

**Nicht gefahren:** die geschlossene Runde aus Phase 4. Es ist kein Joystick
angeschlossen, und weder `collision_monitor` noch Nav2 laufen in dieser
Startdatei. Ohne Hindernisabsicherung und mit einem Sensor, der Schwellen und
Kabel grundsätzlich nicht sieht, wird nicht blind durch die Wohnung gefahren.

**Rückfallweg:** Es wurde nichts an der Kalibrierung geändert; der Stand ist
unverändert fahrbereit.

---

## 2026-08-12 — Duplizierte Wände: Karto verwarf drei Viertel aller Scans

**Entscheidung:** Zwischen Treiber und `slam_toolbox` läuft ab sofort der Knoten
`amadeus_lidar_bringup/scan_vereinheitlichen`. Er setzt jeden Scan auf ein
festes Winkelgitter (2160 Strahlen) um und veröffentlicht ihn als
`/scan_normiert`. Der Launch-Schalter `normalize_scan` steht auf `true`.

**Grund / Evidenz:** Die versetzt duplizierten Wände kamen weder vom fehlenden
Deskew noch vom Odometrie-Winkelfehler — beide Vermutungen waren falsch. Karto
merkt sich die Strahlenzahl des **ersten** verarbeiteten Scans und bricht bei
jedem abweichenden Scan sofort ab: `LaserRangeFinder::Validate` gibt false
zurück, `Mapper::Process` kehrt daraufhin ohne Knoten und ohne Kartenbeitrag
zurück (`lib/karto_sdk/src/Karto.cpp` Zeile 213 ff., `Mapper.cpp` Zeile 2722).
Die Meldung geht auf **stdout**, nicht ins ROS-Log — deshalb war sie so lange
unsichtbar.

Der STL-27L liefert keine feste Strahlenzahl: über 424 Scans am stehenden
Roboter **19 verschiedene Werte zwischen 2145 und 2176**, der häufigste deckt
nur 25,7 % ab. Die Winkel sind dabei korrekt, der Treiber zieht
`angle_increment` mit, sodass `(N-1)·increment` immer 360° ergibt.

Die Rechnung geht auf: etwa 42 winkelgetriggerte Annahmen je Umdrehung mal
25,7 % sind knapp 11 — gemessen wurden 10.

A/B am realen Roboter, identischer Ablauf, nur der Schalter umgelegt:

| | verworfene Scans | neue Knoten | Wand/frei | Nebenachse (real 3,80 m) |
|---|---|---|---|---|
| ohne | 31 | 10 | 0,125 | 5,39 m |
| mit | 0 | 41 | 0,098 | 3,83 m |

**Kennzahlenfalle, die fast zur falschen Entscheidung geführt hätte:** „dicke
Wände" stieg von 3,2 % auf 24,0 % — bei der *besseren* Karte. Die Kennzahl misst
Erosionsüberleben und belohnt dünne Linien. Konsistent aus 41 Richtungen
eingetragene Wände sind bei 3-cm-Zellen zwei bis drei Zellen dick; verschmierte
Karten bestehen aus dünnen Fragmenten an vielen Versätzen und schneiden
scheinbar besser ab. Erst das Rendern entschied.

Zwei weitere Korrekturen: Die Mastmaske funktioniert — der Treiber maskiert mit
**NaN**, nicht mit 0 wie in `stl27l.yaml` behauptet. Eine Prüfung auf `== 0.0`
findet sie nicht; genau das führte kurzzeitig zu der falschen Vermutung, der
Mast sei unmaskiert. Und `amadeus_lidar_bringup` brauchte eine `setup.cfg`, die
console_scripts nach `lib/<paket>` umleitet, sonst findet launch sie nicht.

**Betroffen:** `src/amadeus_lidar_bringup/` (neuer Knoten, `scan_gitter.py`,
Test, `setup.cfg`, `setup.py`, Launch, `stl27l.yaml`), Dokumentation. Beim
Fahrtest beide Motoren.

**Teststatus:** Zwei saubere Durchläufe mit Vorbedingungsprüfung und
verifiziertem Abschalten. Ohne Normalisierer exakt reproduziert (31 Verwürfe,
10 Knoten), mit Normalisierer 0 und 41. Sechs Unittests der Winkelabbildung.

**Offene Risiken:** Der Odometrie-Winkelfehler von −6,3° bis −6,5° je Umdrehung
bleibt ungeklärt und widerspricht den 0,50° aus `9e8c06f`. Ein Deskew fehlt
weiterhin. Beide sind vom Normalisierer unabhängig.

**Betriebsfalle, die real Schaden anrichten kann:** `kill -INT` auf die
`ros2 launch`-PID beendet nur den Elternprozess; die Knoten können weiterlaufen.
Dadurch liefen zeitweise **zwei vollständige Stapel gleichzeitig**, mit zwei
`map->odom`-Publishern und zwei scharfen `base_hardware`-Knoten auf demselben
RS485-Bus. Die betroffene Messung war unbrauchbar und wurde verworfen. Nach dem
Beenden immer die Knotenprozesse nachzählen, die eigene PID ausnehmen.

**Rückfallweg:** `normalize_scan:=false` startet wieder ohne den Knoten; der
Treiberpfad bleibt unverändert. Die Karte ist dann wieder verschmiert, der
Roboter aber fahrbereit.

---

## 2026-08-12 — Backport abgenommen; er legt einen zweiten Fehler frei

**Entscheidung:** Der gepinnte `slam_toolbox`-Backport (Upstream `649a50e`,
PR #808) wird auf dem Jetson als Overlay `~/amadeus_slam_toolbox_ws`
betrieben. Phase 1 bis 3 der Abnahme sind bestanden, **Phase 4 bleibt
gesperrt**, bis die neu sichtbare Wandverschmierung eingegrenzt ist.

**Grund / Evidenz:** Der Kern ist doppelt belegt. Synthetisch, ganz ohne
Hardware (`tools/kartierung/test_reine_drehung_synthetisch.py`): dieselben
Eingangsdaten, nur der Schalter umgelegt, ergaben **37 gegen 0** neue Knoten bei
einer 360°-Drehung — die `false`-Variante reproduziert das Fehlerbild aus #807
exakt, nicht ungefähr. Am realen Roboter: 1 → 11 Knoten, freie Fläche 10,8 →
23,2 m². Vorher waren es null.

Dass wirklich der gepatchte Code läuft, ist über das Binärpaket belegt, nicht
über einen Pfad: `check_min_dist_and_heading_precisely` kommt im Overlay-`.so`
genau einmal vor, im apt-Paket gar nicht — und der Parameter ist am laufenden
Knoten abfragbar.

**Der wichtigere Befund ist der zweite:** Die Nachher-Karte zeigt versetzt
mehrfach eingetragene Wände. Wand/frei stieg von 0,041 auf 0,115 (Richtwerte
0,091 vor und 0,052 nach der Odometrie-Kalibrierung), dicke Wandzellen von
0,0 % auf 3,1 %. Solange reine Drehungen verworfen wurden, konnte eine Drehung
die Karte auch nicht verschmieren — der Backport hat das Problem nicht erzeugt,
sondern sichtbar gemacht. Zwei Kandidaten, **keiner gemessen bestätigt**:
fehlendes Deskew (bei 0,30 rad/s dreht der Roboter je 100-ms-Scan um 1,72°) und
ein Winkelfehler der Odometrie (gemessen −4,98° je Umdrehung gegen die in
`9e8c06f` dokumentierten 0,50°, bei nur 0,1 cm seitlichem Versatz).

Zwei Prüfungen des Übergabeprotokolls erwiesen sich als untauglich:
`colcon test` meldet Rückgabewert 0 bei **0 Tests**, weil der Testblock im
gepinnten Upstream auskommentiert ist. Und `slam_knoten_beobachten.py` las seine
Grundlinie über 30 `spin_once`-Aufrufe ein — die kehren aber zurück, sobald
irgendein Callback lief, und der TransformListener liefert ~50 TF/s. Die
Schleife war nach Sekundenbruchteilen durch, während der Graph nur alle 1 s
publiziert; der Initialknoten wurde dadurch der Bewegung zugerechnet und ein
reiner Stillstandslauf meldete „Die Drehung erzeugt Knoten".

**Betroffen:** `docs/SLAM_TOOLBOX_ROTATION_FIX.md`, `docs/ROBOT_TRANSFER.md`,
`tools/kartierung/slam_knoten_beobachten.py`,
`tools/kartierung/test_reine_drehung_synthetisch.py`; Overlay
`~/amadeus_slam_toolbox_ws`; beim Fahrtest beide Motoren.

**Teststatus:** Phase 0–3 bestanden bis auf das Kriterium „keine versetzt
duplizierten Wände". `/scan` stabil 9,99 Hz, genau ein Publisher für
`map -> odom`, `slam_toolbox` beendet sauber.

**Offene Risiken:** Wandverschmierung ungeklärt. Die Drehung erzeugte nur 10
statt der theoretisch möglichen ~42 Knoten, synthetisch waren es 37 — Ursache
nicht gemessen. Karto verwarf 31 von rund 2100 Scans wegen schwankender
Strahlenzahl (2146–2174 statt fest 2172); klein, aber unerklärt. Der
LiDAR-Treiber stirbt beim Herunterfahren mit Exit −6, `base_hardware` mit
Exit 1 (`rcl_shutdown already called`) — beides auf dem Weg nach unten und
unabhängig vom Backport.

**Nächster Schritt, bewusst eine Messung und keine Parameteränderung:** dieselbe
Drehung bei 0,20 rad/s wiederholen und die Kartenkennzahlen vergleichen. Das
trennt Deskew von Odometrie, ohne eine Hypothese vorwegzunehmen.

**Rückfallweg:** Neue Shell öffnen und das Overlay nicht sourcen; dann gilt
wieder das unveränderte apt-Paket unter `/opt/ros/humble`. Gegengeprüft. Es
werden keine Dateien verändert und nichts gelöscht.

---

## 2026-08-10 — Import in ein privates GitHub-Repository

**Entscheidung:** Der getestete Jetson-Stand wird nach
`github.com/chris01-byte/Roboter_ws` (privat) übertragen; `ios/` und
`integration/` werden vom USB-Stick ergänzt.

**Grund / Evidenz:** Jetson und Stick waren divergent — der Jetson trug 27
Commits mit der getesteten Robotersoftware, der Stick 4 Commits mit der iOS-App
und den Transferwerkzeugen. `git merge-base --is-ancestor` bestätigte, dass
keiner den anderen enthält. Vor dem Push geprüft: keine Treffer auf Schlüssel-,
Token- oder Passwortmuster; größte Datei 836 KB; keine Provisioning-Profile.
`testwohnung.pgm` ist synthetisch (240×200 Zellen, **null** unbekannte
Bereiche) und damit unbedenklich — eine echte SLAM-Karte hat immer unbekannte
Zonen.

**Betroffen:** gesamtes Repository, `.gitignore`

**Teststatus:** Push erfolgreich, Inhalt auf GitHub gegengeprüft (privat, keine
Token-Funde).

**Offene Risiken:** Ein leeres Repository `amadeus-robot-ws` ist bei der
Einrichtung entstanden und konnte nicht automatisch entfernt werden.

**Rückfallweg:** Repository ist privat und kann gelöscht werden; der lokale
Stand auf dem Jetson bleibt unabhängig davon bestehen.

---

## 2026-07-28 — Anfahrverhalten geglättet (Commit `f3a9094`)

**Entscheidung:** `base_hardware` schreibt Startdrehzahl und Rampen bei jedem
Verbindungsaufbau: `0x0020` = 5 rpm, `0x001E` = 800 ms, `0x001F` = 400 ms.

**Grund / Evidenz:** Der Roboter nickte beim Anfahren sichtbar. Bei einer Kamera
auf 1,34 m verschieben schon 2° Nicken den gemessenen Boden auf 3 m Entfernung
um rund 10 cm — Boden wird dann als Wand kartiert. Auslesen der Register ergab
**Startdrehzahl 30 rpm**, ein Rest aus dem Richtungstest vom 24.07., der
persistent im Motor gespeichert war. Bei Fahrdrehzahlen um 46 rpm setzte der
Antrieb damit sofort mit 65 % der Zielgeschwindigkeit ein. Messung bestätigte:
Solldrehzahl nach ~110 ms zu 90 % erreicht, **trotz** 800-ms-Rampe — die Rampe
war nie das Problem.

**Betroffen:** `base_hardware_node.py`, `base_hardware_params.yaml`; beide
Motoren.

**Teststatus:** Vom Nutzer am Gerät bestätigt („alles passt"). Bremswert von 250
auf 400 ms nachjustiert, weil 250 ms zu ruppig und 800 ms zu weich war
(Nachlaufen).

**Offene Risiken:** 5 rpm Startdrehzahl könnte bei höherer Last zu wenig
Anlaufmoment bieten. Register `0x0021` steht auf 100, Bedeutung unbekannt.

**Rückfallweg:** Werte in `base_hardware_params.yaml` zurücksetzen; der Antrieb
läuft mit jedem Wert, nur weniger sanft.

---

## 2026-07-28 — Lokalisierung ohne Vorwissen nachgewiesen (Commit `e136871`)

**Entscheidung:** Neues Launch-Argument `start_at_origin` und der Test
`lokalisierung_kidnapped.py` als verbindliches Prüfverfahren.

**Grund / Evidenz:** Zwei naheliegende Prüfungen beweisen **nichts**:
(1) „`map→odom` ist nicht die Identität" — RTAB-Map lädt beim Start die zuletzt
gespeicherte Pose, der Roboter steht dann sofort „richtig" da.
(2) „`/localization_pose` wird publiziert" — im Lokalisierungsmodus kommen
Meldungen in **jedem** Verarbeitungstakt (71 Stück bei ~120 s und 1 Hz),
unabhängig vom Erfolg. Belastbar ist nur: ohne Vorwissen starten **und** von
mehreren Standorten prüfen, ob der gemeldete Positionsunterschied dem echten
entspricht.

**Betroffen:** `slam.launch.py`, `tools/kartierung/`

**Teststatus:** Zwei Läufe: 1,25 m ermittelter Abstand gegen 1,4 m von Hand
gemessen (11 % Abweichung). Gegenprobe mit einer schlechteren Karte fiel
korrekt durch (0,000 m Versatz).

**Offene Risiken:** Geometrische Genauigkeit nur handgemessen.

**Rückfallweg:** `start_at_origin:=false` stellt das alte Verhalten her.

---

## 2026-07-28 — Wörterbuch-Verlust: Ursache korrigiert (Commit `390fcec`)

**Entscheidung:** SIGINT geht **nur an den ros2-launch-Prozess**, nie an die
Prozessgruppe; beim Start `sigterm_timeout:=120 sigkill_timeout:=180`.

**Grund / Evidenz:** Die bisherige Projekterklärung lautete, nur `kill -9`
zerstöre das visuelle Wörterbuch. Gemessen: Auch ein SIGINT an die
**Prozessgruppe** tut es — rtabmap bekommt das Signal doppelt (direkt vom Kernel
und weitergereicht von launch), das zweite bricht das Speichern ab. Ergebnis
war eine Datenbank mit 831 Knoten und **0 Wörtern**, rtabmap starb mit
`exit code -2`. Zusätzlich eskaliert launch nach 5 s selbsttätig auf
SIGTERM/SIGKILL, was für große Karten zu knapp ist.

**Betroffen:** `slam.launch.py` (Dokumentation), `tools/kartierung/stop_slam.sh`

**Teststatus:** Mehrfach bestätigt — seither wird das Wörterbuch zuverlässig
geschrieben (bis 271.805 Wörter).

**Rückfallweg:** Entfällt; ohne den Fix ist die Karte unbrauchbar.

---

## 2026-07-28 — RS485-Selbstheilung repariert (Commit `390fcec`)

**Entscheidung:** Der alte Modbus-Client wird vor einem Neuaufbau geschlossen.

**Grund / Evidenz:** Ein einziger Timeout im Startgewitter (OAK, VL53, RTAB-Map
am USB-Bus) legte die Motoren dauerhaft still. Die Selbstheilung legte einen
neuen Client an, ohne den alten zu schließen; dessen exklusives Port-Lock ließ
jeden weiteren Versuch an `[Errno 11] Could not exclusively lock port`
scheitern.

**Betroffen:** `base_hardware_node.py`; RS485-Bus

**Teststatus:** 0 RS485-Fehler über alle folgenden Fahrten.

**Rückfallweg:** Vorheriger Commit; dann ist ein Neustart des Knotens nach
jedem Timeout nötig.

---

## Grundsätzliches (übernommen aus früheren Sitzungen)

- Amadeus nutzt eine **OAK-D-S2** auf hohem Mast; ein Wechsel auf OAK 4 D Pro
  Wide FF ist vorgesehen. Der Treiber erkennt das Modell selbst.
- Für robuste 2D-Navigation ist ein **separater 2D-Lidar** vorgesehen. Kamera
  und Lidar haben unterschiedliche Aufgaben: die Kamera liefert visuelle
  Lokalisierung und Semantik, der Lidar die horizontale Navigationskarte.
- **Maststeifigkeit, Sensor-Frames und Odometrie** sind für die Kartenqualität
  genauso wichtig wie der Sensor selbst — belegt durch den Nick-Befund oben.
- **Spiegel und Glas** erzeugen optische Ausreißer und werden softwareseitig
  gefiltert, nicht als reale Wände interpretiert. Offener Punkt: Die
  Strahlartefakte vom 28.07. (74,6 % der scheinbaren Freifläche) sind
  vermutlich darauf zurückzuführen; `tools/kartierung/karte_bereinigen.py`
  entfernt die Folge, die Ursache ist ungeklärt.
- Die **VL53-Sensoren decken flache Bodenobjekte nicht ab**: Sie sitzen auf
  0,305 m und schauen waagerecht; ihr Kegel trifft den Boden erst bei ~0,53 m,
  jenseits ihrer Reichweite. Kabel und Schwellen sieht kein Sensor.
