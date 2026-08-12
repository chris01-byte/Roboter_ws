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
