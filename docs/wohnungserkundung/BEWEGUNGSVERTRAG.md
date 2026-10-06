# AP-03 – Bewegung und Bootstrap, Softwarevertrag

Verbindlich bleibt MASTERPLAN v1.3. Der [STATUS](STATUS.md) enthält den einzigen aktuellen Abschluss; die [Originalbelege](evidence/ap03-20261003/README.md) begrenzen diesen Vertrag auf das geprüfte synthetische Modell. Keine Fahrfreigabe, kein Deployment und keine Übertragung der Trackingreserve auf reale Motoren.

## Gemeinsame Geometrie

`base_link` liegt an der mittigen Antriebsachse. Gemessene Hardwarehülle einschließlich vorderer Sensorhalter: x = −0,11 … +0,31 m, y = ±0,23 m. Nav2 verwendet dieses asymmetrische Rechteck mit 0,02 m Padding; Explorer prüft dessen effektive Hülle x = −0,13 … +0,33 m, y = ±0,25 m. Keine symmetrische Zentrierung und keine Verkleinerung des Chassis. Arm-Transportpose bleibt reale Voraussetzung.

Der 0,28-m-Kreis des vorhandenen globalen NavFn-Planers ist eine Suchgeometrie. Er beweist weder Drehen noch Durchfahrt des Rechtecks. Rohkarte, Scope und tatsächliche Costmap müssen den ganzen reservierten Footprint zulassen. Unbekannter Außenraum ist niemals Freiraum. Eigenkörpermasken und monotone Start-Egress-Inventare bleiben private, an die AP-02-Raster-/Sitzungsidentität gebundene Evidenz; keine Kartenumschreibung.

**AP-06-Referenzbindung, 05.10.2026:** Die stationäre virtuelle Eigenkörpermaske und das private erste Abfahrtsinventar sind getrennt. Die Eigenkörpermaske enthält nur ursprüngliche ganze Körperzellen im festen Kartenframe, wird nach tatsächlicher Abfahrt entzogen und erweitert sich durch neue Raster nicht. Das einmalig erfasste Abfahrtsinventar umfasst alle ursprünglich unbekannten Zellen unter der reservierten Anfangskontur, auch diejenigen, die die stationäre Eigenkörpermaske vorübergehend zuließ. Es bleibt mit ursprünglichem Raster, Polygon, Zellschlüsseln und monotonen Abfahrtsflächen/-abständen in der ersten Odometriefläche gebunden. Aktuelle Pose und `map→odom` kommen vom selben tatsächlichen TF-Zeitpunkt. Auch bei deckungsgleichem Kartenraster wird der aktuelle physische TF-Bezug für die Projektion dieses Inventars verwendet; eine Lokalisierungskorrektur allein ist keine neue Rasterbeobachtung. Tatsächliche unbekannt→beobachtet-Deltas werden im deklarierten Kartenframe verglichen und als exakt gemessene Teilflächen dauerhaft aus dem körpergebundenen Bestand abgezogen. Kein Re-Ankern, Recapture oder Wiederaufwuchs. Aktuelle ganze unbekannte Zellen benötigen volle Deckung im Restbestand; die frische volle Konturprüfung auf beiden Rastern und der originale monotone Bewegungsbeweis bleiben zwingend. Kontext-/Auflösungswechsel, Belegung, neue unbekannte Außenfläche und verlorener Bezug sperren weiter. Ohne belegten TF-Bezug bleibt der strikt rastergebundene AP-02-Pfad. Verarbeitung verbraucht die ursprünglichen Quellen-/Aufgabenfristen.

**AP-06-Konsolidierung vor erneuter Fahrprüfung, 05.10.2026:** `rpp_rollout` ist weiterhin ausschließlich der bereits qualifizierte, parametergesperrte Simulationspfad. Die 0,15-m-/0,40-rad-Goalcheckergrenzen beschreiben Akzeptanz, keine Befehle zu beliebigen Posen in einer Scheibe. Statt dieser unerreichbaren Posen wird dessen tatsächliche Rollout-Stoppbahn samt möglicher Enddrehung geprüft: unveränderte 20-mm-/0,05-rad-Trackinghülle, Chassis/Padding, Halbzelldiagonale und 10-mm-Interpolationsreserve. Die Zielposition selbst bleibt ebenfalls mit dieser Hülle geprüft; der vollständige Rollout einschließlich frühzeitigem Stopp erhält die volle Hülle. Eine andere gewünschte Endorientierung verlangt die vollständige Drehhülle am tatsächlichen Rollout-Stopp, nicht erst am idealen Zielpunkt. Default `conservative` behält die volle 0,15-m-/0,40-rad-Scheibe. Native zusätzliche Komponentenabnahme: tatsächliches RPP-Anhalten innerhalb einer 68-cm-Passage; eine dortige Vierteldrehung und zu kleine/unbekannte Passagen bleiben negativ. Kein Ziel-/Frist-/Gesamtabnahmekriterium wird verändert; Hardwareübertragbarkeit weiterhin offen.


Bei jeder Rasterprüfung bleiben halbe Zelldiagonale und 0,01 m Interpolationsreserve erhalten. Der RPP-Rollout verwendet höchstens Viertelzellen/5 mm Translation und begrenzt den reservierten Eckweg pro Schritt auf 4 mm. Der konservative Default behält den gesamten 0,15-m-Positionskreis und ±0,40 rad Orientierung einschließlich nötiger Enddrehung bei. Im parametergesperrten qualifizierten Rollout wird die oben beschriebene tatsächlich erreichbare Stopp-/Drehbewegung vollständig geprüft.

## Pfadvorschlag und Bewegungsfreigabe

Der kürzeste eigene Rasterpfad kann am Drehen oder RPP-Carrot scheitern, obwohl Nav2 eine längere Umfahrung findet. Im ausdrücklichen Rollout-Profil bleibt ein verbundenes bekanntes Ziel mit vollständigem Goal-Footprint als `requires_nav2_plan`-Vorschlag erhalten. Diese Erreichbarkeit erteilt keine Bewegungsfreigabe und erfindet keinen alternativen Fahrpfad.

Vor Vorausrichtung und Navigation ist ein tatsächlich erfolgreicher `ComputePathToPose`-Pfad mit passendem Frame, gültigem Endpunkt und Orientierung sowie vollständiger unabhängiger Chassis-/Controllerprüfung notwendig. Live-Validierung und HOLD-Wiederaufnahme prüfen anschließend diesen tatsächlichen Nav2-Pfad; ein anderer kürzester Eigenpfad darf ihn nicht wieder verwerfen. Ungültiger tatsächlicher Pfad bleibt gesperrt. Der vorhandene NavigateToPose-/Explorer-Besitzer, der einzelne Child, Cancel/HOLD und alle Quellenbudgets bleiben erhalten.

Sub-Halbzell-Verbindungen vom letzten Rasterzentrum zum kontinuierlichen Ziel bestimmen keine neue Endorientierung. Sonst würde ein numerischer 0,3-mm-Anschluss eine unnötige Vierteldrehung erzeugen. Die tatsächliche Endorientierung wird weiterhin von Nav2 und dem Goal-Footprint geprüft.

Vor einer qualifizierten Beobachtungsfahrt aus vollständig gewöhnlich bekannter
Kontur wird zusätzlich die Weiterfahrt vom vorhergesagten RPP-Stopp geprüft.
Eine bekannte volle Drehhülle genügt; andernfalls muss der bestehende native
Planer einen vollständig öffentlich geprüften Vorwärtsrückweg oder einen
Vorwärtspfad in einen bekannten Wendebereich liefern. Der Suchhorizont ergibt
sich aus 0,40-m-Carrot, vorderer Körperausdehnung und 0,15-m-Stoppabstand; er
verwendet ausschließlich die aktuellen Roh-/Costmapraster und bleibt innerhalb
der ursprünglichen 5-s-Verarbeitungs-, Aufgaben- und Gesamtfristen. Die einmalige private Abfahrt und die bereits vorhandene begrenzte erste
Beobachtung im Startkorridor bleiben beim vollständigen ursprünglichen
Pfad-/Egress-Beweis; ein Wendebereich muss dafür nicht bereits vor der ersten
Beobachtung sichtbar sein. Eine schmale Passage
mit bekanntem Wendebereich dahinter bleibt zulässig, die aufgezeichnete C33-
Sackgassenpose ohne bewiesene Weiterfahrt wird vor dem Anfahren verworfen.

Diese `ComputePathToPose.use_start`-Anfragen sind ausdrücklich hypothetische,
rein lesende Planung. Sie erzeugen keine Navigation, TF, neue Beobachtung,
private Anfangsfläche oder Frische. Ihr `/plan` wird nicht als aktueller
Fahrpfad übernommen. Nur das ursprüngliche Beobachtungsziel kann anschließend
über denselben einzelnen NavigateToPose-Besitzer fahren; jede spätere Fahrt
braucht erneut einen aktuellen Native-Pfad von der tatsächlich gemessenen Pose.
Verworfene Aufgaben/Versuche und alle ursprünglichen Budgets bleiben erhalten. Die hypothetische Endorientierung folgt der tatsächlichen
RPP-/Goalchecker-Akzeptanz: ein bereits innerhalb 0,4 rad liegender Heading
wird nicht zum idealen Goal-Heading umgedeutet. Bei rein lesenden zukünftigen
Nav2-Pfaden wird zusätzlich derselbe volle öffentliche RPP-Beweis für nominale
Startorientierung und beide Ränder der unveränderten ±0,05-rad-Trackingbandbreite
geführt. Ein Wechsel der anfänglichen Drehrichtung an der π-Grenze ist eine
andere Reglerbahn, nicht bloß eine Konturaufweitung um die ideale Bahn. Die aktuelle lokale Zielsuche
bevorzugt bei gleicher Grenze von 0,3 m einen öffentlich bekannten Wendebereich,
falls dessen vollständige Anfahrt bewiesen ist. Tatsächliche Beobachtungsziele
haben Vorrang vor einem optionalen vollen Startscan.

Eine rein lesende Planungsvorschlagsablehnung ohne jemals gestartetes
NavigateToPose-Kind verbraucht weiterhin den ursprünglichen Gesamt- und
Aufgabenversuch, aber keinen fehlgeschlagenen Fahrzielzähler. Nach einem
wirklichen Kind-Dispatch bleibt die Fahrversuchsbindung auch über Kartenjoin-
Cancellation und erneute Planung erhalten; deren Scheitern zählt weiterhin als
Fahrfehler. Eine gefilterte Restfrontier oder ausgeschöpftes Budget bleibt
unvollständig; daraus wird kein Gesamterfolg. Nach einer rein lesenden
Vorschlagsablehnung darf nach demselben 30-s-Cooldown eine andere Position
außerhalb der ursprünglichen 15-cm-Akzeptanzscheibe als neue geometrische Anfrage
geprüft werden. Die Aufgaben-ID und höchstens drei Gesamtversuche bleiben gleich;
identische Pose, echte Fahrfehler und erledigte Nachbarschaft erhalten dadurch
keine neue Freigabe. Diese Anfrage ist keine neue gemessene Beobachtung.
Die Live-Auswahl beendet zusätzliche Kandidatenarbeit auch bei einem ersten
zulässigen Native-Planungsvorschlag; Bewegung bleibt bis dessen vollständigem
aktuellem Nav2-/Kontur-/Quellenbeweis gesperrt. Die ursprünglichen 5 s gelten.

## Planer und Controller nach Nachweis

Die vorhandene Kombination **NavFn A\* + Regulated Pure Pursuit** bleibt erhalten. Kein weiterer Navigator und kein neuer Frontier-Kern. Grund ist der ausgeführte Nachweis: echte 68-/80-cm-Durchfahrten und eine 3,68-m-Umfahrung, die der eigene kürzeste Pfad ablehnt, bestehen mit positivem unabhängig gemessenem Footprintabstand. NavFn selbst akzeptiert auch den unzulässigen 56-cm- und Drehfall: gerade deshalb bleibt die zusätzliche rechteckige Prüfung vor dem Child unverzichtbar.

Geprüfte RPP-Werte: fester interpolierter 0,40-m-Carrot, Rotate-to-heading ab 0,35 rad, Kollisionsprüfung an, kein Rückwärtsfahren, gewünschte Translation 0,10 m/s, Drehgeschwindigkeit 0,20 rad/s, maximale Winkelbeschleunigung 2,0 rad/s², Controller 20 Hz und SimpleGoalChecker mit obigen Toleranzen. Das Rollout-Profil liest die bisherigen 17 Parameter/Typen und zusätzlich `general_goal_checker.stateful=false` am tatsächlichen Controller und verweigert abweichende Werte. Die Position muss auch bei der Enddrehung innerhalb der unveränderten 15 cm bleiben; ein früheres einmaliges Betreten genügt nicht. Der echte native Plugin-Gegenfall akzeptiert bei `true` eine anschließend 16 cm entfernte Pose und verweigert sie bei `false`. Gemessener Rückwärtsanteil in sämtlichen positiven Fällen: null.

Der bestehende konservative Modus bleibt Node-Standard. `metric_frontier_simulation_params.yaml` lädt nach dem bestehenden metrischen Opt-in-Profil `metric_path_validation: rpp_rollout`. Das schreibgeschützte Profil behält seine vorhandenen Parameter. Im qualifizierten metrischen RPP-Pfad besitzt der native Controller die tatsächliche Abfahrt: sein interpolierter Carrot und seine 0,35-rad-Drehschwelle bestimmen den bewiesenen Rollout. Der Explorer sendet davor keine zusätzliche Drehung im Stand, die insbesondere den festen unbekannten Heckbestand vergrößern könnte. Der konservative Modus verwendet weiterhin die vorhandene Explorer-Vorausrichtung auf den tatsächlichen Carrot.

Der Rollout ersetzt die pauschale ±0,35-rad-Hülle auf jedem geraden Wegpunkt durch die tatsächliche berechnete RPP-Translation und nötige Rotation, zusätzlich mit **0,02 m Positions- und ±0,05 rad Headingband**. Sämtliche Chassis-, Padding-, Raster- und Interpolationsreserven bleiben bestehen; die erreichbare Goal-Stopp-/Drehhülle wird wie oben beschrieben geprüft. Der Winkel eines unbesuchten letzten Rasterknicks erzeugt keine zusätzliche Drehung am idealen Ziel: im qualifizierten Modus werden das sichere Ziel mit angeforderter Heading sowie der tatsächlich erreichbare Stopp mit erforderlicher Drehung geprüft. Diese neue Bandwahl ist durch Messung begründet und ausschließlich für das dokumentierte Modell qualifiziert; sie ist keine allgemeine Garantie für beliebige Anlagen oder Karten.

## Geschlossene Simulation und Grenzen

Bei Nutzung der privaten Abfahrtserlaubnis im qualifizierten RPP-Pfad bindet der Explorer die monotone private
Abfahrtsgeschichte zusätzlich an die bereits vorhandene tatsächliche
Encoder-Odometrie. Ein stationärer EKF-/TF-Korrekturschritt ist dadurch keine
erfundene physische Rückwärtsfahrt. Radprobe und gemeinsamer TF-Bezug bleiben
frisch; die Radprobe muss gültige Frames, endliche planare Pose und höchstens
180 ms Messungs-/Empfangsalter haben. TF und Encoder müssen in Odom innerhalb
der vorhandenen Trackinghülle von 2 cm / 0,05 rad übereinstimmen. Der relative
vorhergesagte Reglerweg wird für die private Geschichte auf diese gemessene
Pose bezogen. Die ganze aktuelle Kontur wird weiterhin gegen beide tatsächlichen
Raster mit ihrer TF-Pose geprüft. Ein echter Encoder-Rückschritt, neue unbekannte
Außenfläche oder verlorene Quelle bleibt unzulässig; kein Egress-Re-Ankern.
Ist die gesamte aktuelle reservierte Kontur auf beiden Rastern regulär bekannt
und frei, wird keine private Erlaubnis genutzt und kein zusätzlicher alter
Encoderstempel als Geometrieeingabe verlangt. Der ursprüngliche Live-Guard
prüft weiter die tatsächliche Quelle. Eine Rückkehr in ungeklärten Raum erhält
dadurch keine Freigabe.

Rundumbeobachtungen im qualifizierten Modus behalten dieselbe 2-cm-
Positionsreserve wie der RPP-Beweis, sowohl bei Auswahl als auch unmittelbar
vor und während der Drehung. Die 127 Headingproben und alle übrigen
Kontur-/Rasterreserven bleiben bestehen. Während der bloßen Planeranfrage
prüft der Explorer das aktuelle Ziel und die bekannte Verbindung; ein alter
eigener Routenvorschlag ist keine Bewegungsautorität. Sobald Nav2 seinen
tatsächlichen Pfad liefert, muss dieser vor jeder Bewegung vollständig bestehen.

Echte aus Humble-Commit `3c3db59d6969d8ecee8e68468693d006397f4a0c` gebaute Nav2-Planer-/Controllerprozesse, reale Actions und GetParameters. Welt und Antrieb sind synthetisch: Wand-/Türgeometrie, 2-cm-Raster, Wandzeit, unicycle-Integration mit 100-Hz-Zielrate/25-ms-Schrittkappe und 50-ms-Antriebsantwort. Die wirkliche 2000-ms-Hardware-Rampe, Smoother, Schlupf, Sensorlatenzen, TF-/HWT-/Gate-/Stoppschutzkette werden hier nicht simulativ gesund gemeldet und nicht als integriert abgenommen.

Der native Komponentenprüfstand verwendet dieselbe metrische Abfahrtentscheidung wie der Explorer. RPP führt seine erforderlichen Drehungen selbst aus; ein vorhandener Explorer-Drehtransport bleibt eine reine Welt-Testanbindung für den konservativen Modus. Die unabhängige Weltprüfung verwendet Polygon-Trennachsen und exakte Kantenabstände statt der Produkt-Footprintfunktion. Tracking ist der Abstand zur berechneten SE(2)-Rollout-Röhre; Goal-Drehung wird gesondert innerhalb der vollständigen Goal-Prüfung berücksichtigt. Rohpfade, Alignments und echte Regelbewegungen sind archiviert.

Tür-/Umfahrungsziele sind vorbestimmte Komponentenziele und belegen keine autonome Wohnungserkundung. Nur der Bootstrap-Fall nimmt sein erstes Ziel aus dem tatsächlichen bestehenden Explorer-Frontierdetektor, Approach, Ranking und Policy. Seine Beobachtungen ändern sich ausschließlich durch die erreichte simulierte Pose und eine ausdrücklich modellierte endliche Vorwärtssicht mit Wandverdeckung; keine unsichtbaren Groundtruth-Zellen fließen in Explorer oder Planer. Vollrotation bei unbeobachtetem hinterem Außenraum wird verworfen. Fehlende initiale Außenkontur ergibt `wait` mit konkreten fehlenden Zellen und ohne Scan-/Fahrtwiederholung.

Die physische Tür-/Startgeometrie und dieses künstliche Sichtmodell sind weiterhin offen. Reale Deckung und eine Tracking-/Stoppqualifikation sind erforderlich, bevor das Rollout-Profil am Roboter verwendet werden kann. Daraus folgt keine AP-04- oder Hardwareaktivierung.

## Separat vorbereitetes Sensorabdeckungspaket

Bei unverändert unbekannter initialer Außenkontur ist der nächste konstruktive Schritt Beobachtung, nicht Reserveabbau oder wiederholtes Starten. Das Paket ist hier nur vorbereitet, nicht beauftragt oder umgesetzt:

- Festgehaltene tatsächliche Startpose, Kartenraster, LiDAR-TF (+0,245 m, 0 m, +90°), OAK-/VL53-TFs und Arm-Transporthülle gemeinsam prüfen. Eigenkörperzellen und äußeren Mastschatten räumlich getrennt darstellen; keine unbekannte äußere Zelle als Körper klassifizieren.
- Für die volle Startrotation äußere Swing-Hülle des asymmetrischen gepolsterten Rechtecks samt Raster-/Trackingreserve beobachten. Falls nur eine gerade erste Beobachtung gewünscht ist, genau deren kontinuierliche Front-, Seiten- und Rear-Egress-Hülle nachweisen. Die LiDAR-Eigenabschattung, seitliche/rückwärtige Sicht und niedrige Hindernisse sind konkrete fehlende Daten, nicht pauschal „mehr Sensoren“.
- Mit dem bestehenden gerätefreien Start-Geometriediagnostikwerkzeug fehlende Zellgruppen und Bewegungsvarianten protokollieren; keine privaten Wohnungskoordinaten in Git. Erst danach eine belegte Montage-/Blickwinkelkorrektur oder einen abgegrenzten zusätzlichen Beobachter vorschlagen. Reichweite allein beseitigt Eigenabschattung nicht.
- Abnahme dieses separaten Pakets: echte äußere Beobachtungen decken die nötige Hülle bei gültigen Fristen; Eigenkörper-/Egress-Ausnahmen bleiben privat und monoton; unbekannte Richtungen löschen keine Hindernisse. Reale Montage, Aktoren und Deployment benötigen einen eigenen ausdrücklichen Auftrag und die einschlägige Hardwareabnahme.

### Native Rückwege in einem öffentlich bekannten Refugium

Eine hypothetische Rückverbindung muss kein gerader Chord sein. Die echte
CPP-NavFn-Vorwärtsverbindung und deren echte CPP-Rückverbindung werden beide
mit vollständigem öffentlichem RPP-Sweep einschließlich Heading-Band geprüft.
Ein Direkt-Rückfilter war in C40/C33 falsch negativ, obwohl die tatsächlichen
Umwege bestehen. Entfernt wird ausschließlich dieser Direktfilter; unbekannter
Außenraum, erste Abfahrt, echtes Neurechnen am gemessenen Istort, ein Kind und
alle ursprünglichen Zeit-/Versuchsgrenzen bleiben maßgeblich.


AP-06-Auswahlreihenfolge: Eine begrenzte nützliche öffentliche Beobachtung
wird vor unbewiesener ferner Approach-Arbeit gesucht; original 0,5 s innerhalb
5 s, tatsächliche finite unbekannte Sichtpunkte und ganzer Eigenweg. Erledigte
identifizierte Aufgaben bleiben ausgeschlossen. Tatsächliche native Hin- und
Abfahrt sind anschließend zwingend; kein erster privater Egress mehr.
Ein terminaler Nav2-SUCCESS außerhalb exakt 0,15 m / 0,4 rad zählt nicht als
Ankunft. Nach bestätigtem Halt und vollständig frischen gültigen Eingaben darf
dieselbe Aufgabe im selben ursprünglichen Deadline-/Try-/Gesamtbudget erneut
über den bestehenden Child-Besitzer vollständig geprüft werden. Kein Reset,
keine Quellenheilung und keine zusätzliche Bewegung bei harter Schutzursache.

Eine öffentliche Beobachtung hängt nicht vom Ablauf der privaten
Startreferenz ab. Ein ungültiger monotoner Bestand kann dieselbe
Karten-/Sitzungsidentität behalten. Der ganz öffentlich bekannte aktuelle
Körper und der vollständig regulär geprüfte Weg sind notwendig; ungültige
private Ausnahmen bleiben ungültig.

Die längere Suche speziell für die erste Abfahrt ist nur bei vorhandener,
aktuell gültiger privater Evidenz zulässig. Ein ungültiger Bestand mit
weiterhin gebundener Identität aktiviert weder diese Suche noch deren
initiales Rankingprivileg. Vollständige öffentliche Folgewege benutzen
weiter die normale native Hin-/Abfahrtsprüfung.


Bei neuer Rohkarte vor dem passenden Status darf ausschließlich ein bereits
aktives vollständig öffentliches RPP-Kind innerhalb des originalen 1,25-s-
Fensters den alten exakten Join behalten. Frische neue Rohzellen entziehen
Freiraum durch unbekannte/belegte/fehlende Deckung; sie erteilen keine neue
Freigabe. Ganzzellige Ausrichtung, gleicher Frame/Auflösung/Orientierung,
alte Originalstempel und aktueller ganzer Körper/Pfad bleiben zwingend.
Gültiger privater Startbestand, neue Ziele und Erfolgsquittungen sind
von diesem Fall ausgeschlossen. Kein zusätzlicher Navigator oder Try-Reset.
## Präzisierung AP-06, 06.10.2026: private Platzierung und öffentliche Abfahrt

Das erste private Platzierungsinventar bleibt historisch an den ersten Anker gebunden. Seine aktuelle Freigabemaske darf ausschließlich monoton schrumpfen: nur ursprüngliche unbekannte Zellen, die weiterhin vollständig unter dem tatsächlichen aktuellen ungepaddeten Körper liegen. Verlassene Zellen werden keine Rückfahrterlaubnis und erhalten bei Rückkehr keine erneute Anfangsfreigabe. Reine TF-Verfeinerung bei unveränderter Körperpose ist keine gemessene Abfahrt. Öffentliche Kandidaten und öffentliche Native-Abfahrtsprüfung verlangen tatsächlich beobachtete freie Rohzellen; die virtuelle Anfangsmaske ist kein Beobachtungsbeleg. Die private Abfahrtsausnahme und ihr Suchseed gelten ausschließlich bei aktueller Roh-Unknown-Berührung der reservierten Kontur und gültigem ursprünglichem gekoppeltem Egress-Beweis. Auch virtuell whitelisted Roh-Unknown erfordert diesen Beweis; vollständig beobachtete aktuelle Kontur verwendet die normale Native-Abfahrtsprüfung.
