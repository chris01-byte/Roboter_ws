# 2D-SLAM auf Fugen, Schwellen und unebenem Boden

Stand: 24.08.2026

## Nachtrag 10.09.2026: Ursache praktisch reproduziert

Der geplante HWT-/LiDAR-Fugenlauf reproduzierte den entscheidenden Fehler nach
nur 8,5 cm und brach automatisch ab. Encoder meldeten im gemeinsamen
Bewegungsfenster +0,006 Grad, der neue chassisfeste HWT -3,21 Grad. Ein
anschliessender motorloser Lauf des radunabhaengigen LiDAR-Matchers ueber die
aufgezeichneten Scans ergab -3,00 Grad. HWT und LiDAR bestaetigen damit eine
reale Chassisgier, welche die technisch fehlerfreien Motorencoder nicht sehen.

Die fruehere Hypothese "Fuge kann Encoderbewegung verfalschen" ist damit fuer
diesen konkreten Lauf bestaetigt. Gleichzeitig blieb die Scanebene innerhalb
der vorbereiteten Kippgrenzen; das Scan-Gate akzeptierte alle 25 Scans im
Bewegungsfenster. Der unmittelbare Fehler war hier also ebene Gier/Schlupf,
nicht ein unzulaessiger Roll-/Nickstoss. Ein weiterer nackter Encoderlauf ist
nicht noetig. Der naechste Kartenvergleich muss HWT-Gierrate in der lokalen
Odometrie verwenden und den LiDAR-Matcher zunaechst unabhaengig mitfuehren.
SLAM bleibt alleiniger Besitzer von `map -> odom`.

## Anlass

Ein kontrollierter LiDAR-Nachscan in einem gefliesten Bereich erzeugte lokal
faecherfoermig versetzte Konturen. Der neue Kartenstand wurde deshalb
verworfen; der davor gespeicherte Posegraph bleibt der Referenzstand. Echte
Karten, Bilder und ROS-Bags liegen weiterhin nur lokal und gehoeren nicht in
das Repository.

Die anwesende Person beobachtete waehrend der Fahrt ein deutliches Kippeln des
Roboters beim Ueberfahren groesserer Fliesenfugen. Dieser mechanische Befund ist
fuer die Fehleranalyse entscheidend.

## Was gemessen wurde

- Vor der Fahrt stimmten ein globaler LiDAR-Abgleich und die von
  `slam_toolbox` angenommene Startpose bis auf wenige Zentimeter und etwa ein
  Grad ueberein. Eine grob falsche Startlokalisierung ist damit nicht die
  naheliegende Ursache.
- RS485 und absolute Encoderpositionsrueckmeldung blieben waehrend der Fahrt
  fehlerfrei. Es gab keine Konfigurationsstoerung, keine Modbus-Lesefehler und
  keinen einzelnen grossen Sprung im Posegraphen.
- Der fortgesetzte Graph erhielt 238 neue Knoten auf rund 14,8 m Knotenpfad;
  der groesste Abstand aufeinanderfolgender Knoten betrug etwa 0,41 m.
- 33 normierte Scans wurden wegen einer vollen Message-Filter-Warteschlange
  verworfen. Das ist ein Lastsymptom und ein moeglicher Verstaerker, beweist
  fuer sich allein aber keine Ursache.
- Im unauffaelligen Kartenbereich lagen rund 77 % der alten Wandzellen
  innerhalb von 6 cm zu einer Wand des neuen Standes. Im betroffenen Bereich
  lagen nur rund 49 % der neuen Wandzellen so nahe an der vorherigen
  Geometrie. Die lokale Sichtpruefung widerlegte damit eine zunaechst besser
  wirkende globale Wanddicken-Kennzahl.
- Der gespeicherte fehlerhafte Posegraph liess sich motorlos wieder laden und
  reproduzierte die Endpose innerhalb weniger Zentimeter und etwa eines
  Grades. Der Fehler liegt im aufgenommenen Graphen, nicht in einer
  unlesbaren Datei.

## Warum Encoder trotz LiDAR wichtig sind

`slam_toolbox` benutzt `odom -> base_link` als Bewegungsvorhersage und
korrigiert diese anschliessend durch Scan-Matching und Schleifenschluesse.
Gelegentlicher Radschlupf ist deshalb vorgesehen und darf die Karte nicht
sofort zerstoeren. Motorencoder messen jedoch nur die Motorwelle, nicht die
reale Chassisbewegung. Wenn ein Rad an einer Fuge entlastet wird, kurz rutscht
oder anders abrollt, kann die Odometrie trotz technisch perfekter
Encoderrueckmeldung falsch sein.

Gleichzeitig verletzt sichtbares Kippeln eine Grundannahme von 2D-SLAM: Der
LiDAR soll sich in einer festen horizontalen Ebene bewegen. Roll-/Nickbewegung
verschiebt den 0,66 m hoch montierten Sensor, aendert seine Scanebene und kann
statt derselben Wand zeitweise Boden, Sockel, Moebelkanten oder andere Hoehen
treffen. Bewegt oder verwindet sich der Mast, kommt eine nicht im statischen TF
enthaltene Sensorbewegung hinzu.

Der kritische Fall ist daher nicht "Encoder werden verwendet", sondern:
Encoder-Odometrie und LiDAR-Geometrie werden am selben Bodenereignis
gleichzeitig unzuverlaessig. Repetitive oder reflektierende Flaechen und ein
Fahrweg ohne Rueckkehr zu einer eindeutigen Startstelle erschweren danach die
Korrektur. Das beobachtete Auffaechern passt zu fortschreitendem Winkeldrift
ohne belastbaren Schleifenschluss; die genaue Aufteilung zwischen Schlupf,
Kippeln und Scan-Matching muss noch gemessen werden.

## Naechste Messung

Keine SLAM- oder Odometrieparameter auf Verdacht aendern. Der naechste Test ist
eine kurze, begrenzte Messfahrt ueber mehrere Fugen:

1. OAK-D-S2 ohne Aktoren starten und `/oak/imu/data` im Stillstand pruefen.
   Die IMU ist in `oak_params.yaml` bereits aktiviert, aber noch nicht in die
   Odometrie fusioniert.
2. Erst nach neuer persoenlicher Fahrfreigabe eine langsame Gerade ueber den
   gefliesten Abschnitt und zurueck fahren. Hard-Not-Aus und freie Teststrecke
   bleiben Pflicht.
3. IMU, Encoder-Odometrie, LiDAR und TF gemeinsam in einem ausschliesslich
   lokalen ROS-Bag aufzeichnen.
4. Zeitpunkte hoher Roll-/Nick-/Drehrate mit Odometrieabweichung,
   Scan-Matching und verworfenen Scans korrelieren.
5. Erst aus dieser Messung zwischen mechanischer und softwareseitiger Abhilfe
   entscheiden.

## Moegliche Abhilfen nach der Messung

- Mechanik: Rad- und Rollen-Spiel pruefen, groessere oder weichere
  Stuetzrollen bewerten, gleichmaessigen Antriebsradkontakt sicherstellen und
  LiDAR-/Maststeifigkeit messen.
- Zustandsschaetzung: Encoder und IMU mit `robot_localization` fusionieren;
  besonders die Winkelvorhersage darf nicht allein von Raddifferenzen
  abhaengen.
- Scanqualitaet: Scans bei zu grosser Roll-/Nicklage oder Winkelgeschwindigkeit
  markieren beziehungsweise verwerfen, statt falsche Geometrie dauerhaft in
  den Posegraphen einzubauen.
- Kartierablauf: langsamer fahren, Zwischenbilder pruefen und einen lokalen
  Nachscan als geschlossene Runde an derselben eindeutigen Stelle und
  Orientierung beenden.
- Rechenlast: Message-Filter-Drops weiter messen; Scanrate oder
  Verarbeitungslast nur anhand dieser Messung anpassen.

## Nicht tun

- Den verworfenen Nachscan nicht als Navigations- oder Referenzkarte
  veroeffentlichen.
- Radumfang oder Spurweite nicht aus diesem Lauf nachkalibrieren: Schlupf und
  Kippeln sind keine konstante Skala.
- Encoder nicht aus der Kette entfernen und ihre Gewichtung nicht blind
  erhoehen oder senken.
- Echte Wohnungsdaten, Diagnosebilder oder ROS-Bags nicht committen.
