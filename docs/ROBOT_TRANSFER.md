# Übertragung auf den realen Roboter

## HWT-Raumerkundung: Sensorfusion bestanden, Zeitlimit angepasst (11.09.2026)

Der erste autonome Lauf des geschlossenen Raumprofils absolvierte einen
362,2-Grad-Rundblick und drei Frontier-Ziele. Das vierte Ziel wurde nach dem
festen 600-s-Gesamtlimit sicher abgebrochen: Fahrtor danach `blocked`, Basis
0 rpm, Not-Aus immer frei. Der Explorer meldete korrekt nur 50,302 %
Spurabdeckung und `map_ready_to_save=false`; das ist keine vollstaendige
Raumabnahme.

Die Bewegungsmessung selbst ist belastbar. EKF und Encoder legten
3,823/3,785 m zurueck. Netto-Gier HWT/EKF/LiDAR/Encoder:
`345,721/345,757/344,000/342,090 Grad`. Der LiDAR hatte null verworfene
Matches, die Basis null Modbus-/Encoderfehler. Der Nahbereich erkannte die
Annaeherung an Raumkonturen und der Kollisionsmonitor verlangsamte. Die
gespeicherte 212-x-153-Karte bei 3 cm/Zelle ist zusammenhaengend und zeigt
keine getrennt versetzte oder verdrehte Raumkopie; kurze Doppelkonturen und
unbekannte Raender bleiben.

Weil allein der bewusst langsame Rundblick 146 s benoetigte, wird nur
`overall_timeout_s` im `hwt601_room_only_params.yaml` auf 900 s erhoeht.
Frontier-/Coverage-Grenzen, 120-s-Ziellimit, ausgeschaltete Tuer-/Portalbewegung
und der physisch geschlossene Raum bleiben unveraendert. Vor dem naechsten
Lauf `explore` neu bauen; neue persoenliche Fahrfreigabe erforderlich.

Lokale Evidenz, nicht committen:
`~/.local/share/amadeus/bags/hwt601-room-20260911-135008` und
`~/.local/share/amadeus/maps/hwt601-room-20260911-135008`.
Bag-SHA-256:
`777121ffd858d1235474da88502b15c9c38e37a009458121bf7ff9b3ea51667a`.

Rueckfall: Raumwrapper nicht starten oder das Gesamtlimit wieder auf 600 s
setzen. Keine Testkarte wurde produktiv geladen. Tuerdurchfahrt bleibt eine
eigene, noch neu freizugebende Abnahmestufe.

---

## HWT-Kartentranslation: 0,50 m real bestanden (11.09.2026)

Das neue Profil `hwt601_translation_only_params.yaml` und der Wrapper
`tools/kartierung/start_hwt601_translation.sh` begrenzen die erste Translation
auf genau eine lokal LiDAR-bestaetigte 0,50-m-Etappe bei maximal 0,05 m/s.
Encoder sind nur Gesundheitspruefung und 0,90-m-Radbudget. Rundblick,
Frontiers, Portale und Abdeckung bleiben aus; der Start sendet noch keine
Mission. Der Status nennt diese Betriebsart eindeutig
`bounded_lidar_translation_only`.

Der beaufsichtigte Echtlauf in der freien Kueche bestand. Vorher war der
0,50-m-breite Frontkorridor bis 1,545 m frei. Die Mission stoppte selbst mit
`SUCCESS`, Fahrtor `blocked` und 0 rpm. Am LiDAR-Schaltpunkt: realer Weg
0,500 m, Encoder-Radweg 0,508 m, seitlich -15 mm, Heading -2,5 Grad,
Matchkosten 0,023 m, 88,5 % Stuetzung, null Rejects. Einschliesslich der
400-ms-Bremsrampe:

- EKF: 0,5225 m, -2,502 Grad
- unabhaengiger LiDAR-Beobachter: 0,5200 m, -2,750 Grad
- reine Radodometrie: 0,5224 m, -1,198 Grad
- HWT-Integral: -2,501 Grad

Damit stimmen HWT und LiDAR bis 0,249 Grad ueberein, waehrend die
Encoder-Gier 1,303 Grad abweicht. Genau diese Radgier bleibt aus der
Kartenodometrie ausgeschlossen. Not-Aus und beide Nahbereichsseiten loesten
nie aus; alle Befehle blieben innerhalb 0,05 m/s und 0,04691 rad/s und endeten
bei null. Die finale 166-x-128-Karte bei 3 cm/Zelle besitzt deckungsgleiche,
dichter gewordene Waende ohne Doppelkontur.

Lokale Evidenz, nicht committen:
`~/.local/share/amadeus/bags/hwt601-translation-20260911-131558` und
`~/.local/share/amadeus/maps/hwt601-translation-20260911-131558`.
Bag-SHA-256:
`f692504fca46204be3cc2039ff6abd630483c6813db4dc6aa0411e9390ee0dec`.
Danach waren Domain 158 und alle Ports frei. Die bekannten Shutdownfehler
traten erst beim Beenden auf. Naechste Stufe: begrenzte Hin-/Rueck- oder
Tueretappe mit neuer persoenlicher Freigabe; noch keine Mehrraumfreigabe.

---

## HWT-Scan-only: korrigierter 360-Grad-Lauf bestanden (10.09.2026)

Der beaufsichtigte Wiederholungslauf des korrigierten
`start_hwt601_rundblick.sh` ist real bestanden. Alle acht Segmente liefen ohne
`odom_stale` bis zum selbsttaetigen Missionsstatus `SUCCESS`; danach waren das
Fahrtor gesperrt, beide Befehlstopics bei null und die Basis im Stillstand.
Es wurde zu keinem Zeitpunkt Translation befohlen.

Kumulierte Winkel im Bewegungsfenster:

- HWT: `+362,092 Grad`
- HWT-/Encoder-EKF auf `/odom`: `+362,107 Grad`
- unabhaengiger LiDAR-Beobachter: `+361,750 Grad`
- reine Radodometrie: `+358,028 Grad`

HWT und LiDAR unterscheiden sich nur um 0,342 Grad. Die Encoder-Gier liegt
4,064 Grad unter HWT; der neue Kartenpfad verhindert wie vorgesehen, dass
diese Radgier die Karte fuehrt. Der LiDAR-Matcher hatte 1.527 akzeptierte,
null verworfene Updates. Seine 23 Rebases sind bei einer 15-Grad-Grenze ueber
einen Vollkreis erwartbar. Die von ihm gemessene Netto-Rumpfverschiebung von
16,57 mm gegen 0,11 mm Radodometrie ist auf dem Fugenboden weiterhin relevant.

Die gespeicherte 116-x-249-Karte bei 3 cm/Zelle zeigt in der Sichtpruefung
einen zusammenhaengenden Grundriss ohne gedoppelte oder verdrehte
Raumkonturen. Lokale Evidenz, nicht committen:
`~/.local/share/amadeus/bags/hwt601-rundblick-repeat-20260910-2317` und
`~/.local/share/amadeus/maps/hwt601-rundblick-repeat-20260910-2317`.
Bag-SHA-256:
`5dfb5155615be658c032a556342dd5f82416bd2b91eab193e55cb982a01319a9`.

Nach Ctrl-C waren Domain 157 und HWT-, Basis- und LiDAR-Port frei. Die
bekannten Abschlussmeldungen von LiDAR/Basis/VL53 und die bekannte
HWT-Humble-Take-Race traten erst beim globalen Shutdown auf. Der bestandene
Rundblick gibt noch keine autonome Mehrraumfahrt frei. Als naechste Stufe nur
einen begrenzten Translations-/Tuerabschnitt mit eigener persoenlicher
Fahrfreigabe fahren; HWT bleibt Karten-Gierquelle, LiDAR nur Beobachter.

---

## HWT-Scan-only: erster Lauf deckt Explorer-Zeitrace auf (10.09.2026)

Fuer die erste HWT-Kartenabnahme ist jetzt
`tools/kartierung/start_hwt601_rundblick.sh` vorgesehen. Er erzwingt ein
installiertes `hwt601_scan_only_params.yaml`, HWT-Odometrie, scharfen
Motor-Opt-in und Explore-Freigabe. Das Profil darf nur acht langsame
45-Grad-Drehsegmente mit je einer Sekunde Pause ausfuehren und beendet die
Mission danach, bevor Frontiers oder andere Translationen geplant werden.
`scan_only=false` bleibt der normale Default.

Der erste ausdruecklich freigegebene Lauf stoppte beim dritten Segment sicher:
Explorer-Resultat `odom_stale`, 110,4 Grad erreicht, danach Fahrtor gesperrt
und 0 rpm. Die Bag zeigt, dass kein Sensor ausgefallen war. Maximale Luecken:
HWT 39,229 ms, EKF-`/odom` 45,026 ms, Radodometrie 92,932 ms. Bis zum
Bremsstillstand: HWT/EKF/LiDAR/Encoder
`+115,593/+115,593/+115,250/+115,492` Grad; lineare Befehle immer exakt null.
Der LiDAR beobachtete 18,81 mm reale Fugenverschiebung gegen nur 0,05 mm in der
Radodometrie. Die unvollstaendige 115-Grad-Karte ist sauber, aber kein
360-Grad-Nachweis.

Ursache des falschen `odom_stale`: Der Explorer las seine monotone
Vergleichszeit vor dem parallel gesperrten Odometrie-Snapshot. Ein dazwischen
eingetroffenes neues Paket hatte dadurch kurz eine spaetere Empfangszeit und
wurde sofort als Uhrfehler verworfen. Alle Bewegungshelfer lesen nun zuerst
die Snapshots und danach die Uhr; eine kleine, auf das normale Frischefenster
begrenzte Zukunftstoleranz deckt dieselbe Callback-Race ab. 63 ausgewaehlte
Pakettests bestehen, der vorhandene Build-Testbestand meldet 271/271. Noch
keine reale Wiederholung: Sie braucht neue persoenliche Fahrfreigabe.

Lokale Daten, nicht committen:
`~/.local/share/amadeus/bags/hwt601-rundblick-20260910-2249` und
`~/.local/share/amadeus/maps/hwt601-rundblick-20260910-2249`. Nach dem Lauf
waren Domain und alle drei seriellen Ports frei. Die bekannten
Shutdown-Meldungen von LiDAR, Basis und VL53 traten erst nach bestaetigtem
Stillstand auf.

---

## HWT-Karten-A/B softwareseitig bereit (10.09.2026)

Der neue HWT-Kartenpfad ist ein Opt-in; der bisherige Encoderstart bleibt der
Rueckfall. Im HWT-Pfad besitzt `base_hardware` weder `/odom` noch TF, sondern
publiziert nur gemessene Rad-Odometrie auf
`/fusion/hwt601/wheel_odom_raw`. Der EKF fusioniert daraus ausschliesslich
Vorwaertsgeschwindigkeit und aus `/shadow/hwt601/imu/yaw_rate` ausschliesslich
Giergeschwindigkeit. Er ist der einzige Besitzer von `/odom` und
`odom -> base_link`; `slam_toolbox` bleibt allein fuer `map -> odom`
zustaendig. Der LiDAR-Matcher schreibt nur seine unabhaengige Kontrolle unter
`/shadow/hwt601/` und wird noch nicht fusioniert.

Der sichere Start fuer den spaeteren, neu freizugebenden Kartenversuch lautet:

```bash
cd ~/roboter_ws
AMADEUS_HWT601_STILLSTAND=JA \
AMADEUS_FAHRFREIGABE=JA \
  bash tools/kartierung/start_app_erkundung_hwt601.sh \
    active_drive:=true enable_auto_explore:=true
```

Vor Ausfuehrung muessen Roboter und Bereich frei, Not-Aus erreichbar und alle
alten Robotikstacks beendet sein. Nach dem Start mindestens 30 Sekunden nicht
bewegen. Der Wrapper setzt die HWT-Argumente selbst und verweigert
Gegenueberschreibungen. Das Fahrtor bleibt bis zum stabilen Bias geschlossen
und stoppt bei Fehler sofort beziehungsweise bei Statusverlust nach hoechstens
0,8 Sekunden. Die App sendet den Explore-Auftrag weiterhin separat; der Start
allein loest keine Mission aus.

Motorlos bestanden: vier Pakete gebaut, Launch in Domain 154 mit
`active_drive=false` und ohne Stillstandsfreigabe gestartet. `/odom` hatte
genau den EKF als Publisher, Rad-Rohdaten genau die Basis. HWT blieb korrekt
`ready=false`, die Basis meldete `dry_run=True`, und anschliessend waren alle
Ports frei. Der reale Karten-A/B-Lauf ist noch offen und braucht eine neue
ausdrueckliche Bewegungsfreigabe. Rueckfall: den normalen
`start_app_erkundung.sh` verwenden; dessen HWT-Schalter ist standardmaessig
`false`.

Der anschliessende vollstaendige Stillstands-Preflight in Domain 155 bestand nach
frischer Nutzerbestaetigung ebenfalls. HWT-Status `ready=true`, 998 stabile
Biasproben, null Rejects/Reconnects; Raten HWT/EKF/Scan
`100,009/30,016/10,002 Hz`. Die EKF-Gier driftete in 56 s nur rund
-0,068 Grad bei null Translation. Der unabhaengige LiDAR-Beobachter hatte 616
akzeptierte und null verworfene Updates und blieb numerisch auf der Startpose.
Alle 1495 LiDAR-Scans wurden normiert. `/odom` und `/map` hatten je genau einen
Publisher, beide vorgesehenen dynamischen TFs waren vorhanden. Kein
Motorzugriff. Nach Ctrl-C waren Domain und Ports frei; die bekannte
Basis-Abschlussrace und einmal eine HWT-Humble-Take-Race erschienen nur beim
Herunterfahren, nicht im Messbetrieb.

---

## Fugenbefund: HWT/LiDAR -3 Grad, Encoder praktisch 0 Grad (10.09.2026)

Ein freigegebener, auf 0,75 m geplanter Geradeauslauf wurde nach nur 8,5 cm
fail-closed beendet: HWT -3,21 Grad gegen Encoder +0,006 Grad. Stillstand war
bestaetigt; kein Ruecklauf. Die motorlose Wiederverarbeitung der gleichzeitig
aufgezeichneten LiDAR-Scans ergab -3,00 Grad auf 0,065 m, 435 akzeptierte
Matcherupdates, null Rejects/Rebases, 0,00853 m Kosten und 96,67 % Stuetzung.
Damit bestaetigen HWT und LiDAR eine reale, fuer die Motorencoder unsichtbare
Chassisgier auf der Fuge.

Das Scan-Gate nahm waehrend der Bewegung 25 Scans an und verwarf keinen. Das
ist korrekt: maximale Gravitationsrichtungsanderung 0,01907 rad, rohe
Roll-/Nickrate 0,03910 rad/s und Beschleunigungsnorm 9,837..9,920 m/s² lagen
weit innerhalb der Grenzen. Ebene reale Gier ist kein Kippereignis. OAK,
SLAM, Karte, Navigation und Produktiv-TF waren aus. Lokale Evidenz:
`fugen-20260910-2115`, `dynamic-straight-forward-20260910-211652` und
`fugen-lidar-replay-20260910-2120`. Alle Ports danach frei, Domains 152/153
leer.

Keine Grenze lockern und keinen weiteren reinen Encoder-Fugenlauf starten.
Der oben beschriebene isolierte Karten-A/B-Start setzt diese Konsequenz nun
um: HWT-Gierrate in der lokalen Odometrie, LiDAR-Matcher nur als
unabhaengiger Waechter und SLAM weiterhin alleiniger Besitzer von
`map -> odom`. Die reale Fahrt ist noch offen; Rueckfall bleibt der bisherige
direkte Encoderpfad.

---

## HWT-/Encoder-/EKF-Dreh- und Geradelauf bestanden (10.09.2026)

In isolierter Domain 148 nach ausdruecklicher Fahrfreigabe zwei begrenzte
Drehungen mit 0,08 rad/s: links Encoder/HWT/EKF
`+18,321744/+18,306255/+18,306116` Grad, rechts
`-18,327586/-18,180042/-18,179794` Grad. HWT minus Encoder damit
-0,015489/+0,147544 Grad; Netto nach der Gegenbewegung
-0,005842/+0,126212/+0,126323 Grad. Translation nur 0,011/0,021 mm, null
Modbusfehler, Encoder-Rejects oder Rebases, jeweils abschliessend 0 rpm.

`base_hardware` war einziger Besitzer von `/dev/ttyUSB_BASE`, fuehrte sowohl
Fahrbefehle als auch absolute Positionslesung aus und stellt nun die Dauer der
sequentiellen FC03-Paarabfrage bereit. Bewegungsmaximum 13,092/11,607 ms;
Links-/Rechts-Erstlesung wechselte nahezu 50:50. Der separate read-only
Encoder-Shadow darf in diesem Modus nicht laufen. OAK, LiDAR, SLAM, Karte,
Navigation, produktive Odometrie und TF waren aus; das EKF blieb ohne TF.

Lokale Evidenz: `~/.local/share/amadeus/hwt601/`
`dynamic-left-20260910-181707` und `dynamic-right-20260910-181746`.
Rohdaten-SHA-256 links
`16c0cb3ebc0831014b1c9502036eacf28af9cfa6b4b337c07dae27c3e558c303`,
rechts `8419b93d0dc7236d91547a4118ba2bc0e29eab40ae3a0838da6057fa1bc9e196`.
Beide Ports danach frei, Domain leer. Dies gibt noch keine Kartenintegration
frei: Innovation/Kovarianz ueber weitere Bewegungsarten, Schwellen,
Temperatur und ein absoluter Heading-Anker bleiben offen.
Rueckfall: Teststack aus lassen;
Produktivstarts sind unveraendert.

Die anschliessende Rohachsenwiederholung bestand ebenfalls. Links/rechts lagen
die Beschleunigungsnormen bei 9,874..9,892/9,875..9,892 m/s², maximale
Roll-/Nickrate bei 0,01105/0,00932 rad/s und maximale Aenderung der
Gravitationsrichtung bei 0,003635/0,002689 rad. Damit blieben 1547 Proben weit
innerhalb der Scan-Grenzen; reine Motorvibration auf glattem Boden ist
bestanden. Vier Drehlauf-Plateaus ergeben fuer HWT minus Encoder vorlaeufig
`1,1504e-5 (rad/s)^2` Restvarianz und 0,003393 rad/s RMS. Den produktiven
Encoderwert noch nicht aendern: nur eine Drehgeschwindigkeit und kein
Schwellenfall.

Der danach ausgefuehrte Geradeaus-/Rueckwaertslauf bestand ebenfalls. Bei
0,05 m/s waren die Wege +0,133931/-0,133873 m, Seitversatz nur
+0,0126/-0,0014 mm und Encoderwinkel +0,05842/-0,04090 Grad. HWT minus
Encoder lag bei -0,47398/+0,20282 Grad; netto bleibt damit -0,27076 Grad
HWT-gegen-Encoder-Restwinkel, obwohl der Encoderweg bis auf 0,059 mm schliesst.
Null Bus-/Encoderfehler, beide Vibrationspruefungen bestanden, beide Laeufe
endeten mit 0 rpm. Evidenz: `dynamic-straight-forward-20260910-185828` und
`dynamic-straight-reverse-20260910-185926`. Nach geordnetem Ende waren beide
Ports frei und Domain 151 leer. Die anschliessende Fugenpruefung steht im
neueren Eintrag oben; Temperatur, Heading-Strategie und Karten-A/B bleiben
offen.

---

## HWT-/Encoder-Shadow: reale Stillstandsabnahme bestanden (09.09.2026)

`codex/hwt601-encoder-shadow` fuegt einen vom Fahrknoten getrennten
ESS23-Encoderleser hinzu. Er besitzt nur Modbus-FC03 fuer die bestaetigten
Positions-/Konfigurationsregister, keine Subscription, keine Schreibmethode,
keine Aktorausgabe und kein TF. `/dev/ttyUSB_BASE`, FTDI
`0403:6001/BG03R8RZ`, der getrennte HWT-Alias und der exklusive serielle Socket
werden im Prozess selbst geprueft. Ein verlorener Port darf keinen impliziten
Pymodbus-Reconnect ausloesen, sondern verriegelt bis zum Neustart.

Der direkte Beobachter muss in Domain 145 vor den Quellen laufen. Der
Quellenwrapper akzeptiert exakt diesen einen vorhandenen Node; dadurch kann
die HWT-Biasphase nicht unbemerkt vor der Encoderbeobachtung ablaufen. Ueber
600 s werden HWT-/Encoderwinkel samt Peaks, Translation, Twist, ROS- und
monotone Echtzeit, Statusluecken/-zaehler sowie Node-, Publisher- und
GID-Provenienz geprueft. Alle Statusquellen und die erste Graphpruefung muessen
schon vor den ausgewaehlten Messproben vorliegen. Ein Erfolg verlangt
zusaetzlich von jeder Quelle binnen zwei Sekunden nach der letzten
ausgewerteten Messprobe einen neuen Status.
Vier Quellenlaeufe mit Best-Effort-Topic-Luecken bis 0,159757 s fuehrten zu
`RELIABLE` mit Tiefe 200 fuer isolierten HWT-Ausgang und Beobachter; der
Encoderausgang ist `RELIABLE` mit Tiefe 10. Zwei weitere Anlaeufe brachen
trotzdem bei 0,100037 beziehungsweise 0,120361 s ab. Im letzten Lauf hatte die
fehlerfreie HWT-Quelle 1697 Werte publiziert, der Beobachter aber nur 1032
gespeichert. Dessen wiederholte Vollsuche durch die wachsende Encoder- und
IMU-Historie war die Ursache. Er haelt die IMU-Zeitliste jetzt separat vor und
prueft nur den neuesten moeglichen Fensterendpunkt. Die strenge
0,100-s-Abnahmegrenze gilt wieder fuer Quelle und Beobachter. Der naechste
Lauf zeichnete das volle 600-s-Fenster ohne Laufzeitfehler auf, deckte aber in
der Abschlussintegration eine zweite quadratische Vollsuche auf: Fuer jeden
Encoderwert wurde die IMU-Zeitstempelliste neu aufgebaut. Weil dadurch die
Abschlussstatus veraltet waeren, wurde er beendet. Die Integration baut die
Zeitliste jetzt nur einmal auf. Der formale Wiederholungslauf bestand danach:
`encoder-shadow-20260909-230007` meldete `passed: true` und `faults: []` fuer
600,499827 s, 60046 HWT-Proben bei 99,993329 Hz und 12011 Encoderproben bei
20,000006 Hz. Maximale Zeitstempelluecken waren 0,030666 s beziehungsweise
0,054657 s. Encoderweg, Encoderdrehung, Rejects, Reconnects und Rebases blieben
null; der HWT integrierte 0,968490 Grad. Alle Quellen- und Graphstatus waren
gueltig, der CSV-Hash wurde unabhaengig bestaetigt. Nach genau einem SIGINT
endeten alle Quellen sauber; beide Ports waren frei und Domain 145 leer. Jede
dynamische Freigabe bleibt offen.

Der abgekuehlte Wiederholungslauf `encoder-shadow-cold-20260910-170933`
bestand ebenfalls: 600,495658 s, 99,993605 Hz HWT, 20,000145 Hz Encoder,
maximale Zeitstempelluecken 0,024880 s/0,058095 s, exakt null Encoderbewegung
und -0,393725 Grad HWT-Drift. Der CSV-Hash
`92cd288373c9ecb4db016edec498df5505144da3f67aa11b8e8090f74da9ff6e`
wurde unabhaengig bestaetigt. Gegenueber dem warmen Lauf verschob sich der
eingefrorene Z-Bias um 0,000066043 rad/s; beide Laeufe bestehen, zeigen aber
Temperaturabhaengigkeit und beim warmen Lauf nur 0,032 Grad Driftreserve.
Ein erster Versuch nach dem Ausschalten verriegelte ohne Schreibzugriff, weil
die ESS23 auf FC03 noch nicht antworteten. Vor jedem Start sind deshalb
Motorversorgung und Motor-Halt zu pruefen. EKF und dynamische Nutzung bleiben
offen.

Fuer die naechste motorlose Stufe ist ein eigener 120-s-EKF-Beobachter samt
zweitem Startwrapper vorbereitet. Reihenfolge: Beobachter, die drei strikt
lesenden Quellen, dann der isolierte Filter. Der EKF-Wrapper akzeptiert vor
seinem Start exakt diese vier vorhandenen Nodes. Der Beobachter prueft neben
Rate, Luecken, Translation, Gier und Twist weiterhin alle Quellstatus und
Publisher-GIDs; `/odom`, Karte, TF, Fusion und Fahrbefehle muessen ohne
Publisher bleiben. Der Filter publiziert nur `/shadow/hwt601/odom`, kein TF,
und besitzt keinen Kontrolleingang. 263 Offline-Tests bestehen; reale
120-s-Abnahme offen. `robot_localization` erzeugt intern genau einen
`transform_listener_impl_*`-Node; der Beobachter erlaubt diese abonnierende
Instanz. Der zweite Smoke-Start bewies, dass der Prozess trotz
`publish_tf=false` einen `/tf`-Publisher anlegt. Das isolierte Launch remappt
`/tf` und `/tf_static` auf Shadow-Sinktopics. Der Beobachter verlangt dort
null Nachrichten und auf den produktiven TF-Topics null Publisher.

Der formale Lauf `encoder-shadow-ekf-20260910-175348` bestand danach mit
`passed: true` und `faults: []`: 120,030024 s, 3602 EKF-Proben bei
30,000827 Hz, maximale Zeitstempelluecke 0,050077 s, null Translation und
+0,101303 Grad relative Endgier. Der direkte HWT-Pfad lag bei +0,102181 Grad,
der Encoder bei 0 Grad; HWT minus EKF waren 0,000877 Grad. Quellen,
Abschlussstatus, Graph und Publisher waren gueltig. Produktive TF-Publisher
und Nachrichten auf den beiden isolierten TF-Sinks blieben null. CSV-Hash:
`10db9d350459f1bbf5231fc3ba92e4cf7fc03c116b633c18b59ddfc89fcc9de3`.
Nach Erfolg wurden EKF und Quellen sauber beendet; Ports frei, Domain 145
leer. Diese Abnahme gilt nur fuer das isolierte motorlose Stillstands-EKF.
Messdaten duerfen nur in einen kanonisch geprueften lokalen Ordner ausserhalb
des Repositories geschrieben werden.

Das getrennte EKF-Profil konsumiert nur Encoder-`vx`/`wz` und HWT-`wz`, bleibt
auf `/shadow/hwt601/odom`, ohne TF und ohne Kontrolleingang. Es startet nicht
mit den Quellen und ist nicht freigegeben: die vorlaeufigen Varianzen gewichten
HWT gegen Encoder-wz ungefaehr 60.000:1, und ein absoluter Heading-Anker fehlt.
Ein plausibler EKF-Winkel beweist daher noch keine Kartenloesung.

Offline bestanden: 259 gezielte Python-Tests, Flake8/Python-/Shell-Syntax und
Diffpruefung. Beide ROS-Pakete bauen; Colcon meldet 99 Tests fuer
`base_hardware` und 67 fuer `robot_state_estimation`, jeweils null Fehler. In
dieser Stufe wurden weder Hardware/Ports noch ROS-Knoten gestartet, keine
Register gelesen oder geschrieben und keine System- oder Kartendatei
veraendert.

Die spaetere reale Abnahme braucht eine neue ausdrueckliche Freigabe,
bestaetigten Chassisstillstand, sauber beendeten Basisstack und erreichbaren
Not-Aus. Der Motorbus wird zwar nur gelesen, bereits versorgte Controller
koennen aber Haltemoment haben. Verbindliche Zwei-Terminal-Reihenfolge,
Grenzwerte, Abschluss und Rueckfall stehen in
`docs/HWT601_ENCODER_SHADOW.md`. Rueckfall: beide Shadow-Prozesse nicht starten
oder jeweils sauber beenden; Produktivlaunches und Motorparameter sind
unveraendert.

---

## HWT-Winkelskala geklaert, warmer Schattenpfad bestanden (09.09.2026)

Der Nutzer hat inzwischen ausdruecklich bestaetigt, den extern beobachteten
Test bei visuell etwa 180 Grad gestoppt zu haben. HWT 178,164, LiDAR 178,250,
Encoder 175,616 und freier Raw-Scan-Fit 178,129 Grad verwerfen damit den
Faktor-zwei-Verdacht. Keine Skalenhalbierung. Die aelteren 45-Grad-Beobachtungen
bleiben historisch zurueckgezogen; ihr genauer Referenzfehler ist nachtraeglich
nicht rekonstruierbar. Das Motor-Testwerkzeug bleibt vorsorglich gesperrt.

`feature/hwt601-shadow-fusion` bereitet nun einen rein passiven Start mit
eigenen `/shadow/hwt601/*`-Topics vor: einmaliger, explizit bestaetigter
Startbias, danach fest; nur Gyro-Z im `base_link`-Frame. Kein Motorport,
`cmd_vel`, OAK, LiDAR, `/odom`, TF, SLAM, Navigation oder Kartenpfad.
Warm-Stillstandskovarianz konservativ `5,0e-7 (rad/s)^2`; Temperatur,
Kaltstart und Motorvibration bleiben offen. Der abschliessende 600,009-s-
Realtest lieferte 59.991 Proben bei 99,982 Hz, null Rejects/Reconnects,
30,744 ms Maximalluecke, +0,01323 Grad Endintegral und 0,08574 Grad maximales
Zwischenintegral. Der Bias blieb nach der Startkalibrierung fest bei
`adaptation_samples=0`. Der isolierte Graph hatte nur die zwei HWT-Knoten und
den Messbeobachter, keine Produktiv-Odom-/TF-/Map-/Befehlspublisher; Motorport,
OAK, Basis, SLAM und RTAB-Map blieben aus. Prozesse sauber beendet, beide Ports
und Domain frei, Kartensignatur unveraendert. Details: `docs/HWT601_SHADOW.md`.

## Historie, Abnahme zurueckgezogen: HWT-Gegendrehung rechts (09.09.2026)

`feature/hwt601-right-turn-test`: `--direction right` bei unveraenderten
Grenzen. IMU -90,57797 Grad gegen LiDAR -91,25000 Grad, Differenz +0,67203
Grad. 105 Softwaretests plus negativer motorloser Watchdog-Test bestanden.
Neue Biasbestimmung und persoenlich freigegebener Realtest; Stillstand
bestaetigt, Testprozesse beendet. Keine physische Motorstromabschaltung.
Beide Richtungen grob plausibel, exakte Rueckkehrpose/Gesamtfusion offen.
Details und lokale Daten: `docs/HWT601_MOTOR_DREHTEST.md`.

---

## Historie, Abnahme zurueckgezogen: HWT-Linksdrehung (09.09.2026)

Nach persoenlicher Freigabe: IMU +90,93231 Grad, unabhaengiger LiDAR
+91,25000 Grad, Encoder +89,84432 Grad. Stillstand bestaetigt, Testprozesse
beendet; keine Rueckdrehung. 104 Softwaretests plus Dry-run-Watchdog geprueft.
Basis initialisierte bestehende Motorregister, HWT-Konfiguration unveraendert.
Keine OAK/Fusion/SLAM, kein collision_monitor; isolierter beaufsichtigter Test.
Branch `feature/hwt601-powered-turn-test`, Details/Rueckfall und lokale Daten:
`docs/HWT601_MOTOR_DREHTEST.md`. Gegenrichtung und Fusionsabnahme weiter offen.

---

## HWT-Schritt 2: manueller Drehtest vorbereitet, noch nicht ausgefuehrt

`feature/hwt601-turn-test` ab `3205e9a`: Anleitung in
`docs/HWT601_DREHTEST.md`, Werkzeug `tools/sensorfusion/hwt601_drehtest.py`.
Standardaufruf prueft nur USB-Metadaten, ohne den Port zu oeffnen.
Zwei externe, rechtwinklige Richtungsmarken fuer +90/-90 Grad; fester
Anfangsbias, keine adaptive Korrektur und keine Live-Winkelvorgabe.
91 Softwaretests bestanden, realer Drehtest ausdruecklich noch offen.
Nur bei bestaetigt ausgeschaltetem Motorstrom und leichtgaengiger, sicherer
manueller Drehbarkeit starten; keine Bewegung oder Aktorfreigabe erfolgt.
Produktivprofile/TFs unveraendert. Rueckfall: Test nicht starten/beenden.

---

## HWT-Stillstand/Bias: zehn Minuten bestanden (08.09.2026)

`feature/hwt601-stationary-bias`: vorhandenes Biasprofil unveraendert mit
echter IMU geprueft. Nach 25 s Einlauf/Kalibrierung volle 600 s ausgewertet,
59.993 Proben, rund 100 Hz, maximal 47,72 ms Luecke, keine Sperrung.
Z-Rohintegral +4,65769 Grad; fester Bias -0,12022 Grad; nachgefuehrt
-0,03439 Grad (absoluter Spitzenwert 0,03985 Grad). Unabhaengige CSV-
Nachrechnung bestaetigt Ergebnis. Keine Produktionswerte ersetzt.
71 Softwaretests bestanden. Prozess beendet/Port geschlossen, keine
Motor-/OAK-/Fusionsknoten gestartet. Kein Kaltstart- oder Bewegungsnachweis;
Stillstand durch Nutzerabsprache, nicht Encoder. Details und Wiederholung:
`docs/HWT601_BIAS_STILLSTAND.md`. Keine Fahrfreigabe.

---

## HWT-Montagereferenz separat vorbereitet (08.09.2026)

`feature/hwt601-mount-frame`: Nutzerachsen X rechts/Y vorne/Z oben ergeben
Yaw -90 Grad. Nominale Fussplattenreferenz relativ zum bestehenden
`base_link`: x=0,084, y=0, z=-0,056 m. Unsicherheit der 84 mm nicht bekannt.
Eigener opt-in Launch `robot_state_estimation hwt601_mount.launch.py`,
ausschliesslich `base_link -> hwt601_mount`, ohne Hardware-/Fusionsstart.
Kein erfundener TF zum unbekannten Chipursprung `hwt601_link`.
Paket gebaut, 66 Tests bestanden; Details und Rueckfall: `HWT601_MONTAGE.md`.
Vorhandene Produktivstarts, Basis-, Rad-, OAK- und VL53-Frames unveraendert.

---

## HWT601: USB installiert, reale Rohdaten erfolgreich geprueft (08.09.2026)

Der Nutzer hat die Installation aus dem folgenden historischen Abschnitt
ausgefuehrt. Alias `/dev/ttyUSB_HWT601`, CH341-Treiber und Steckplatzbindung
sind bestaetigt. Der 60-s-Test lieferte 6.000 gueltige Antworten bei rund
100 Hz, null Fehler, maximal 13,85 ms Luecke. Beschleunigungsnorm 9,88344 m/s²,
unkorrigiertes Z-Gyrointegral 0,38760 Grad in dieser Minute. Auch X/Y zeigen
Bias; noch keine Langzeit- oder Fusionsabnahme.

ROS-Rohdatenstart ebenfalls bestanden (822 Nachrichten); alle Testprozesse
sauber beendet. Motor/OAK/EKF und Sensorkonfiguration unangetastet. Montage-
TF, Gyroskala, Drehrichtung und Bias bleiben offen. Details und alle Achsenwerte:
`docs/HWT601_ERSTMESSUNG.md`. Keine erneute Installation erforderlich.

---

## HWT601: USB-Pfad fertig vorbereitet, Root-Installation offen (08.09.2026)

**Branch:** `fix/hwt601-usb-commissioning`, Basis `a326ab0`.
**Worktree:** `/home/p/roboter_worktrees/hwt601-usb-commissioning`.
Die uncommitteten Aenderungen in `/home/p/roboter_ws` sind unveraendert.

Gemessen: angeschlossener CH340 `1a86:7523`, keine Seriennummer, fester
USB-Pfad `1-2.4.4.4`; fehlender serieller CH341-Kerneltreiber und falsche
brltty-Zuordnung verhindern aktuell den IMU-TTY. Der Nutzer nennt HWT601;
eine echte Sensorantwort/Skala/Montage ist noch nicht abgenommen.

Vorbereitet und getestet: passendes Kernelmodul, pruefsummengebundener
Installer mit Rueckfall, Alias am exakten Steckplatz, gezielte brltty-/ModemManager-
Ausnahme, begrenzter Rohdaten-Messlauf und separater ROS-Start ohne OAK,
Basisprozess, EKF oder TF. 55 Tests bestanden, beide ROS-Pakete gebaut.
Standalone-Start mit fehlendem TTY bestaetigte acht Statusnachrichten mit
`ready=false`, `fusion_ready=false`, null erfundene IMU-Nachrichten und
sauberes Ende. Keine Aktoren aktiviert und keine Systemdateien installiert.

Es fehlt einmal die lokale Administratorauthentifizierung:

```bash
sudo python3 /home/p/roboter_worktrees/hwt601-usb-commissioning/tools/sensorfusion/hwt601_usb_setup.py install
```

Passwort ausschliesslich im lokalen Terminal eingeben. Zuvor Motorversorgung
ausschalten, Roboter sichern. Installer stoppt einmal `brltty-udev.service`,
nicht den Desktop-Brailleprozess, und bindet weder Motor noch LiDAR neu.
Kein globales Deaktivieren von Braille-Diensten, kein Aendern des VL53-I2C-
Treibers. Modul ist kernelgebunden; brltty-Regelkopie nach Updates pruefen.
Rohdatenstart, Messfolge, Hardwarewirkung, Wartung und wiederherstellbarer
Rueckfall sind vollstaendig in `docs/HWT601_USB_INBETRIEBNAHME.md` beschrieben.

---

## HWT601-Chassis-IMU — Software vor Lieferung vorbereitet (30.08.2026)

**Branch:** `feature/hwt601-integration`, Basis `2750ad6`

Vorbereitet ist die RS485-Variante `HWT601-AGV-485`. Der neue ROS-Knoten liest
nur AX..GZ per Modbus-Funktion `0x03`, prueft die komplette RTU-Antwort und
publiziert SI-Rohdaten auf `/hwt601/imu/data_raw`. Er kann keine Konfiguration,
Kalibrierung oder Motoraktion schreiben. Diagnose und JSON-Status melden
Verbindung, Frische, Rate und Fehlerzaehler; bei Fehlern oder Saettigung wird
nichts publiziert.

Die IMU erhaelt einen eigenen isolierten USB-RS485-Adapter und den eindeutigen
Alias `/dev/ttyUSB_HWT601`. Der Treiber verweigert den Motoralias
`/dev/ttyUSB_BASE` auch dann, wenn beide Namen auf dasselbe reale Geraet
zeigen. Eine udev-Regel wird erst nach Lieferung aus VID, PID und eindeutiger
Seriennummer erzeugt. Es wurde jetzt keine Regel installiert.

Sicherer Rohdatenstart nach dem Build:

```bash
cd /home/p/roboter_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch robot_state_estimation hwt601.launch.py
```

Der gestufte Integrationsstart lautet:

```bash
ros2 launch robot_bringup state_estimation_hwt601_validation.launch.py
```

Dabei sind Basis-RS485, Bewegung und Basis-TF hart gesperrt
(`dry_run=true`, `allow_rs485=false`, `publish_tf=false`). OAK, Fusionsadapter,
Scan-Gate und EKF sind standardmaessig aus. So kann der HWT allein betrieben
werden, ohne die OAK dauerhaft zu erwaermen. Die OAK wird spaeter nur per
`start_oak:=true` fuer einen begrenzten Vergleich zugeschaltet.

Die HWT-Datenblattskalen und konservativen Kovarianzen sind vorlaeufig. Ebenso
existiert absichtlich noch kein `base_link -> hwt601_link`: Position,
aufgedruckte Achsen und Orientierung muessen nach der tiefen, steifen Montage
am Roboterboden gemessen werden. Ohne bestaetigte Gravitation, Drehrichtung,
Datenrate, Drift und statischen TF bleiben Adapter, Scan-Gate und EKF aus.

Softwaretest: beide Pakete gebaut, 31 Tests ohne Fehler; Standalone-Start ohne
Sensor meldete korrekt `ready=false`, `state=getrennt` und endete sauber. Der
motorlose Bring-up blieb bei 0 m/s und 0 rpm. Keine Hardware-, Motor- oder
Sensorregister wurden veraendert. Vollstaendige Verdrahtungs-, Einbau- und
Abnahmefolge: `docs/HWT601_INTEGRATION.md`.

Rueckfall: HWT-Launch beenden oder nicht starten. Kein vorhandener Produktiv-
oder OAK-Start referenziert den neuen Treiber.

---

## Modulare Sensor-Fusion — motorlos live abgenommen (30.08.2026)

**Ausgangsstand:** `feature/modulare-sensorfusion`, Commit `00f6e52`

**Aktueller Fix-Branch:** `fix/sensorfusion-imu-bias`

Das neue Paket `robot_state_estimation` trennt Hardwareadapter,
Qualitaetsentscheidungen und Zustandsschaetzung. Der lokale
`robot_localization`-EKF ist kuenftig der vorgesehene einzige Besitzer von
`odom->base_link`; SLAM/Lokalisierung behaelt `map->odom`. Das Defaultprofil
nimmt Encoder-Vorwaerts-/Giergeschwindigkeit, die
Differentialantriebs-Seitwaertsbedingung und die OAK-Gierrate. Es verwendet
weder `cmd_vel` noch OAK-Orientierung oder Beschleunigung. Ein neuer Sensor
kann als standardisierte IMU oder Odometriequelle ergaenzt werden, ohne den
portablen Qualitaetskern zu aendern.

Neu vorhanden:

- thermisch verzoegerte Startkalibrierung und langsame Nachfuehrung des
  OAK-Gyrofehlers nur bei encoderbestaetigtem Stillstand;
- fail-closed Sperre der korrigierten IMU bei zu grossem Restoffset;
- Frische-, Frame-, Zeitstempel- und Kovarianzpruefung;
- radunabhaengige Bewegungsreferenz mit hysteretischer Schlupferkennung;
- IMU-gestuetztes, fail-closed Gate von `/scan_normiert` nach
  `/scan_qualitaet` fuer Kipp-/Stossphasen;
- optionale lokale LiDAR-Odometrie ohne Radinput, TF oder Aktorausgabe;
- JSON- und ROS-Diagnose fuer jede Vertrauensentscheidung;
- ein Validierungslaunch, dessen Motorpfad nicht per Argument freigeschaltet
  werden kann.

Ein laengerer Stillstandstest widerlegte die erste feste
2-s-Startkalibrierung: Ueber 615,7 s wanderte die EKF-Gierlage um
`-43,33 Grad`. Ursache war ein weiter driftender OAK-Nullpunkt, kein Encoder-
oder TF-Fehler. Das Amadeus-Profil wartet deshalb jetzt 15 s, misst danach 5 s
und fuehrt den Bias im bestaetigten Stillstand mit 5 s Zeitkonstante nach. Bei
Radbewegung ist die Schätzung eingefroren. Ab `0,001 rad/s` geglaettetem
Restfehler sperrt der Adapter die IMU und degradiert sichtbar.

Der korrigierte echte Motorlos-Lauf dauerte 342,5 s, davon 330,8 s nach der
ersten Freigabe. Die OAK lieferte 85.620 Rohproben; nach Einlaufzeit,
Kalibrierung und Qualitaetsgate wurden 80.171 korrigierte Proben aufgezeichnet.
Bei exakt 0,00 m Positionsaenderung driftete die EKF-Gierlage nur
`-0,090 Grad`; die korrigierte IMU integrierte zu `-0,058 Grad`. Der
Restoffset lag im Median bei `0,000145 rad/s` und im 95-%-Quantil bei
`0,000615 rad/s`. Eine thermische Spitze von `0,001214 rad/s` loeste wie
vorgesehen 3,5 s Sperre plus 2,0 s Erholzeit aus; danach blieb das System bis
Testende nominal. Es gab nur den EKF-Strom fuer `odom->base_link`.
`base_hardware` blieb durchgehend bei `dry_run=true`, `allow_rs485=false`,
`rs485_ready=false`, 0 m/s und 0 rpm. Alle Testknoten sind beendet. Die beiden
Pakete bauten erfolgreich; 24 gezielte Tests liefen ohne Fehler.

Beim Beenden zeigt `base_hardware` weiterhin den bekannten, getrennten
Humble-Shutdownfehler `rcl_shutdown already called`. Zu diesem Zeitpunkt war
der Trockenlauf bereits gestoppt; der Fix-Branch veraendert den Basis-/Motorcode
bewusst nicht.

Sicherer Wiederholungsstart ohne Motorwirkung:

```bash
cd /home/p/roboter_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch robot_bringup state_estimation_validation.launch.py
```

Das ROS-Humble-Paket `robot_localization` ist auf dem Jetson als
Systemabhaengigkeit installiert. Der neue Code veraendert keine
Motorregister, keine Karten und keine Daten ausserhalb des Workspace.

**Noch nicht produktiv umschalten:** Stufe C (Langzeitstillstand) ist bestanden,
aber reale Geradeaus-, Dreh-, Fugen-,
Schwellen- und Dropouttests fehlen. Sie brauchen erneut persoenliche
Fahrfreigabe, freien Weg und Hard-Not-Aus. Erst danach werden
Kartierungs-/Nav-Starts von Basis-TF und `/scan_normiert` auf EKF-TF und
`/scan_qualitaet` umgestellt. Die optionale LiDAR-Odometrie bleibt bis zu
ihrer eigenen Realabnahme standardmaessig aus.

Rueckfall: Fusionslaunch beenden und den bisherigen Basisweg auf `/odom` mit
`publish_tf=true` sowie SLAM direkt auf `/scan_normiert` verwenden. Der volle
Schnittstellen-, Portierungs- und Akzeptanzvertrag steht in
`docs/SENSOR_FUSION_ARCHITEKTUR.md`.

---

## LiDAR-Nachscan auf gefliestem Boden verworfen (24.08.2026)

Ein beaufsichtigter manueller Nachscan erzeugte lokal fächerfoermig versetzte
Konturen und ist **kein freigegebener Kartenstand**. Die davor gespeicherte
Referenz bleibt erhalten; echte Karten, Bilder und ROS-Bags bleiben lokal.

Der Antrieb meldete waehrend der Fahrt fehlerfreie absolute Encoderpositionen,
RS485 und 0 ungueltige Kommandos. Die anwesende Person beobachtete jedoch
deutliches Kippeln an groesseren Fliesenfugen. Encoder koennen Schlupf und
reale Chassisbewegung nicht sehen; gleichzeitig veraendert Kippeln die Ebene
des 0,66 m hoch montierten 2D-LiDARs. Damit koennen Odometrievorhersage und
Scan-Matching am selben Bodenereignis gleichzeitig unzuverlaessig werden.

Vor einer neuen Kartierfahrt ist deshalb keine Parameterkorrektur, sondern
eine Messung vorgesehen: OAK-D-S2-IMU (`/oak/imu/data`), `/odom`, LiDAR und TF
bei einer kurzen langsamen Fugenfahrt gemeinsam lokal aufzeichnen. Jeder
Motorstart braucht erneut freie Strecke, Hard-Not-Aus und ausdrueckliche
persoenliche Freigabe. Danach werden IMU-Fusion, Kipp-Scanfilter und
mechanische Massnahmen bewertet. Details:
`docs/SLAM_BODENUNEBENHEITEN.md`.

Aktueller Zustand nach der Diagnose: keine Amadeus-Knoten aktiv, keine
Motoren bestromt, keine installierte Konfiguration geaendert.

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
