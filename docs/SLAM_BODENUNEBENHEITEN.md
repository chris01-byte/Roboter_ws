# 2D-SLAM auf Fugen, Schwellen und unebenem Boden

Stand: 28.08.2026

## Anlass

Ein kontrollierter LiDAR-Nachscan in Kueche und Bad erzeugte lokal
faecherfoermig versetzte Konturen. Der neue Kartenstand wurde verworfen; der
davor gespeicherte Posegraph bleibt die Referenz. Echte Karten, Bilder und
ROS-Bags liegen weiterhin nur lokal und gehoeren nicht in das Repository.

Die anwesende Person beobachtete deutliches Kippeln des Roboters beim
Ueberfahren groesserer Fliesenfugen. Dieser mechanische Befund ist fuer die
Fehleranalyse entscheidend.

## Was gemessen wurde

- Vor der Fahrt stimmten globaler LiDAR-Abgleich und die von `slam_toolbox`
  angenommene Startpose bis auf wenige Zentimeter und etwa ein Grad ueberein.
- RS485 und absolute Encoderpositionsrueckmeldung blieben fehlerfrei. Es gab
  keine Konfigurationsstoerung, keine Modbus-Lesefehler und keinen einzelnen
  grossen Sprung im Posegraphen.
- Der fortgesetzte Graph erhielt 238 neue Knoten auf rund 14,8 m Knotenpfad;
  der groesste Abstand aufeinanderfolgender Knoten betrug etwa 0,41 m.
- 33 normierte Scans wurden wegen einer vollen Message-Filter-Warteschlange
  verworfen. Das ist ein Lastsymptom, beweist aber keine Ursache.
- Im unauffaelligen Kartenbereich lagen rund 77 % der alten Wandzellen
  innerhalb von 6 cm zu einer Wand des neuen Standes. Im betroffenen Bereich
  lagen nur rund 49 % der neuen Wandzellen so nahe an der alten Geometrie.
- Der fehlerhafte Posegraph liess sich motorlos wieder laden und reproduzierte
  seine Endpose. Der Fehler liegt im aufgenommenen Graphen, nicht in einer
  unlesbaren Datei.

## Warum Encoder trotz LiDAR wichtig sind

`slam_toolbox` benutzt `odom -> base_link` als Bewegungsvorhersage und
korrigiert diese durch Scan-Matching und Schleifenschluesse. Gelegentlicher
Radschlupf ist vorgesehen. Motorencoder messen aber nur die Motorwelle, nicht
die reale Chassisbewegung. Wenn ein Rad an einer Fuge entlastet wird, rutscht
oder anders abrollt, kann die Odometrie trotz technisch perfekter
Encoderrueckmeldung falsch sein.

Kippeln verletzt gleichzeitig eine Grundannahme von 2D-SLAM: Der LiDAR soll
sich in einer festen horizontalen Ebene bewegen. Roll-/Nickbewegung
verschiebt den 0,66 m hoch montierten Sensor, aendert seine Scanebene und kann
statt derselben Wand Boden, Sockel, Moebelkanten oder andere Hoehen treffen.
Der kritische Fall ist daher, dass Odometrievorhersage und LiDAR-Geometrie am
selben Bodenereignis gleichzeitig unzuverlaessig werden.

## Warum der erste Stop-and-go-Versuch nichts verbessern konnte

Die gesprochenen Positionen P1 bis P21 waren nur menschliche Markierungen.
Technisch abonnierte `slam_toolbox` waehrend der gesamten Fahrt weiterhin
`/scan_normiert`. Es nahm deshalb auch alle Fugen-, Kipp- und Schlupfphasen in
den Graphen auf. Im Stillstand zusaetzlich zu warten entfernt bereits
eingelesene schlechte Scans nicht. Der Versuch war also kein echter
Stillstandsfilter.

## Implementierter einfacher Stillstandsmodus

Der getrennte Launch `stationary_slam_lidar.launch.py` fuehrt jetzt nur
`/scan_stillstand` an `slam_toolbox`. Das fail-closed Gate prueft gleichzeitig:

- frische Encoder-Odometrie mit hoechstens 0,01 m/s und 0,025 rad/s;
- frische OAK-BMI270-Daten mit hoechstens 0,08 rad/s Drehrate;
- einen Beschleunigungsbetrag innerhalb 0,8 m/s2 um die Erdbeschleunigung;
- mindestens 1,2 s durchgehenden Stillstand.

Danach oeffnet es genau zwei Sekunden. Bei Bewegung wird die Aufnahme sofort
abgebrochen. Nach einem vollstaendigen Fenster bleibt es geschlossen, bis
mindestens 8 cm Translation, 0,08 rad Rotation oder bestaetigte
Encoderbewegung vorlag. Erst nach erneutem Stillstand folgt P2, P3 und so
weiter. Das Status-Topic lautet
`/stationary_scan_gate/status_json`.

Dieser Modus ist bewusst **keine IMU-/Encoderfusion** und keine komplizierte
Bodenkorrektur. Die OAK-IMU entscheidet nur, ob gerade aufgenommen werden
darf. Die Posegraph-Schaetzung benutzt weiterhin Odometrie und Scan-Matching.
Eine statische Schraeglage ohne Bewegung kann der aktuelle Rohdatenvertrag
nicht sicher von der festen OAK-Montage unterscheiden; deshalb soll der
Roboter fuer jede Aufnahme sichtbar auf einer ebenen Fliesenflaeche stehen,
nicht mit einem Rad auf einer Fugenkante oder Schwelle.

## Fortsetzen statt Wohnung neu aufnehmen

Nur die Kueche kann nachgescannt werden, wenn drei Bedingungen erfuellt sind:

1. Der unverfaelschte Wohnungs-Posegraph (`.posegraph` und `.data`) wird
   geladen, nicht einer der verworfenen Kuechenstaende.
2. Die reale Startpose wird zuvor motorlos gegen die passende Rasterkarte
   bestimmt und als `map_start_x`, `map_start_y`, `map_start_yaw` uebergeben.
3. Neue Karte und neuer Posegraph werden unter einem neuen lokalen Pfad
   gespeichert; die Referenz wird nie ueberschrieben.

Ein fehlender Graphteil oder eine ungueltige Startpose beendet den neuen
Launch, bevor Hardwareprozesse starten. Start, Diagnoseaufzeichnung und Save
liegen in `tools/kartierung/`.

## Reale Abnahmereihenfolge

1. Roboter ausgeschaltet beziehungsweise motorlos in einen bereits guten,
   LiDAR-eindeutigen Bereich vor der Kueche stellen.
2. OAK-IMU, LiDAR und globale Startpose ohne Aktoren pruefen.
3. Erst danach persoenliche Fahrfreigabe, freien Weg und Hard-Not-Aus erneut
   bestaetigen.
4. Langsam per Controller von ebener Position zu ebener Position fahren. Nach
   jedem Loslassen nichts von Hand ausloesen: Das Gate wartet und nimmt genau
   einmal automatisch auf.
5. Status und Karte zwischendurch ansehen. Bei einer sichtbar falschen Kontur
   abbrechen; nicht bis zum Ende weiterfahren.
6. Rasterkarte und Posegraph mit `save_stationaere_kartierung.sh` unter neuem
   lokalen Pfad speichern und erst nach Sichtvergleich als Kandidat bewerten.

## Nicht tun

- Den verworfenen Nachscan nicht als Navigations- oder Referenzkarte nutzen.
- Radumfang oder Spurweite nicht aus einem Fugenlauf nachkalibrieren.
- Encoder nicht aus der Kette entfernen und ihre Gewichtung nicht blind
  aendern.
- Den normalen `slam_lidar.launch.py` fuer Stop-and-go verwenden: Dort ist
  die Stillstandsfreigabe absichtlich nicht eingebaut.
- Echte Wohnungsdaten, Diagnosebilder oder ROS-Bags committen.
