# Schritt 2: markierter manueller +/-90-Grad-Drehversuch

**Status:** vorbereitet und synthetisch getestet, noch kein realer Drehversuch.
Branch `feature/hwt601-turn-test`, Grundlage `3205e9a` (bestandener Biastest).
Vorbereitung ist keine Motorfreigabe. OAK/ROS/EKF/Antrieb bleiben aus.

## Bodenmarkierung

Ja: eine **externe Winkelreferenz** vorbereiten. Die genaue Position des
Roboters in der Wohnung und ein perfekt unveraenderter Drehmittelpunkt sind
fuer diesen Gyrotest nicht erforderlich; entscheidend sind die Anfangs- und
Endausrichtung. Der um 84 mm versetzte IMU-Montageort aendert daran nichts.

1. Abloesbares, flach aufgeklebtes Klebeband verwenden. Linie A mit Pfeil
   beschreibt die aktuelle Vorwaertsrichtung des Roboters.
2. Linie B mit Pfeil zeigt exakt 90 Grad **nach links**, von oben gesehen
   gegen den Uhrzeigersinn. Mit grossem Winkel ausrichten. Alternativ ein
   Dreieck mit Seiten 60/80/100 cm abmessen: zwischen den 60- und 80-cm-
   Seiten liegt der rechte Winkel. Die Linien verlaengern, damit sie neben
   dem Roboter sichtbar bleiben. Keine losen Baender als Stolperfalle.
3. Gut sichtbare, feste Chassispunkte als Laengsrichtungsbezug verwenden.
   Ein Punkt unter der Mitte der Antriebsachse hilft beim Wiederpositionieren,
   ist aber optional. Nicht unter den Roboter greifen oder ihn anheben, nur
   um diesen Punkt zu markieren.

Erster Lauf: A -> B, **+90 Grad links**. Zweiter Lauf: B -> A,
**-90 Grad rechts**. Bei einer kleinen Verschiebung die Chassisrichtung
parallel zur entsprechenden Referenz ausrichten; nicht dem alten Bodenpunkt
nachjagen. Die Messreferenz ist immer Klebeband/Winkel, niemals die IMU-Anzeige.
Die Messgenauigkeit ist durch die Markierung und Sichtausrichtung begrenzt.

## Mechanische Voraussetzung

- Motorversorgung wirklich aus; Not-Aus erreichbar. Eine Softwarepause
  bestaetigt keine Stromfreiheit. Sensor/Jetson duerfen separat versorgt bleiben.
- Nur wenn der Roboter ohne Gewalt von Hand bewegbar ist. Nicht gegen
  Haltemoment, Bremse, Getriebe oder blockierte Raeder druecken. Bei Widerstand
  **nicht beginnen**; zuerst eine andere, separat freigegebene Testmethode planen.
- Freien Schwenkbereich aller Anbauten und Kabel sicherstellen, Stolperstellen
  beseitigen, nicht kippen/heben und keine Kabel abziehen, waehrend gemessen wird.
- Niemand im Quetschbereich. Bei schwerem Aufbau Hilfe organisieren. Der Test
  ist keine Aufforderung, einen mechanisch ungeeigneten Roboter zu verdrehen.

## Vorbereitungscheck (jetzt erlaubt, ohne serielles Oeffnen)

```bash
cd /home/p/roboter_worktrees/hwt601-usb-commissioning
python3 tools/sensorfusion/hwt601_drehtest.py
```

Dieser Default liest nur udev-Merkmale des bekannten HWT-Alias. Er startet
keine Kalibrierung und keinen Hardwareprozess. Ein anderer laufender IMU-Leser
muss vor dem spaeteren echten Test beendet sein; der Messport wird exklusiv
geoeffnet. Motor-/LiDAR-Port werden nicht durchsucht oder geoeffnet.

## Echter Test erst nach Absprache und Vorbereitung

In einem interaktiven Terminal, an Linie A ausgerichtet:

```bash
python3 tools/sensorfusion/hwt601_drehtest.py \
  --run --direction left --motor-power-off --stationary-confirmed
```

Die beiden Bestaetigungsflags sind Angaben der anwesenden Person, keine
gemessenen Freigaben. Das Skript steuert **keinen** Motor.

1. Etwa 25 s ruhig halten: 15 s Einlauf und 10 s neuer Anfangsbias aus
   dem bestehenden HWT-Profil. Nicht blind den Bias einer alten Messung laden.
2. Meldung **Bias eingefroren** abwarten. Mit `s` und Enter das Messfenster
   starten; erst nach der Bestaetigung bewegen.
3. Langsam von A nach B drehen, moeglichst in etwa 5–15 Sekunden, und anhand
   der externen Markierung ausrichten. Der Bias bleibt fest; es werden keine
   simulierten Radstillstandswerte eingespeist und kein Bias nachgefuehrt.
4. Roboter ruhig abstellen, `e` und Enter. Drei weitere Sekunden ruhig
   halten, dann erscheinen Ergebnis und Speicherort.
5. Fuer den Rueckweg von B nach A denselben Ablauf mit `--direction right`
   starten. Dabei wird am nun ruhenden Roboter erneut ein Anfangsbias bestimmt.

`q` und Enter oder Ctrl-C brechen den Messlauf ab. Das beendet die Messung,
**nicht** eine von Hand verursachte Bewegung: Roboter selbst sicher abstellen.
Zeitlimits: maximal 90 s fuer Anfangskalibrierung und 120 s je weiterer Phase.
Ein unerwartet geschlossenes Eingabeterminal bricht ebenfalls ab.

## Auswertung und Grenzen

Erwartet werden etwa +90 bzw. -90 Grad um Sensor-Z (= bestaetigte Roboter-Z-
Richtung). Vorlaeufig gilt +/-5 Grad Abweichung je Lauf als grober
Vorzeichen-/Skalencheck. Ausgegeben wird auch gemessen/Referenz als
Skalenverhaeltnis; es wird **kein** Kalibrierfaktor automatisch gespeichert.
Keine laufende Winkelanzeige: sie koennte den unabhaengigen Sollwinkel ersetzen.

Das Ergebnis verlangt ausserdem >=80 Hz, keine Integrationsluecke >0,1 s,
mindestens 100 Proben und zwei Sekunden Messdauer sowie maximal 5 Grad
integrierte Roll-/Nickabweichung. Serialfehler/Saettigung/unplausible
Beschleunigung brechen ab. Eine gueltige Messung bleibt `fusion_ready=false`.
Die Roll-/Nickpruefung ist kein Sicherheitssensor gegen Umkippen.

Beide Richtungen muessen getrennt ausgewertet werden. Die Summe ihrer
Z-Winkel sollte nahe null liegen; dies ist nur eine ergaenzende Kontrolle,
weil zwischen den Laeufen erneut kalibriert und nicht durchgehend gemessen wird.
Ein bestandener grober Test belegt weder 0,1-Grad-Genauigkeit noch Encoder-
Skalierung, Fahrverhalten, USB-Neustartfestigkeit oder die fertige Kartierung.

Rohdaten/JSON bleiben lokal unter
`~/.local/share/amadeus/hwt601/turn-left-.../` bzw. `turn-right-.../`.
Abgebrochene Laeufe werden unvollstaendig/nicht bestanden gespeichert.
Die Auswertung verwendet vorhandene vorlaeufige 4-g-/400-Grad/s-Skalen.
Gegenrichtung/falsche Skala ist ein Untersuchungsergebnis, kein Anlass zum
automatischen Umschreiben der Sensorkonfiguration.

Rueckfall: Test beenden/nicht starten. Kein Produktionsprofil, Sensorregister,
TF, Motorstart oder Systemdienst wird durch diesen Test veraendert.
