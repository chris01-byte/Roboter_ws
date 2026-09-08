# HWT601: zehnminuetiger motorloser Biastest

## Methode

Branch `feature/hwt601-stationary-bias`, Grundlage `517cbbb`. Der Nutzer
hat Schritt 1 (zehn Minuten unberuehrter Stillstand) explizit freigegeben.
Der Test oeffnet nur den durch udev verifizierten HWT-USB-Port, liest FC03
bei 115200 Baud/Adresse 80 und startet weder ROS noch Basis/OAK/EKF.
Es werden keine Sensor-Konfigurationsregister oder Produktionsparameter
geschrieben. Kein Motor-/LiDAR-Port wird geoeffnet.

`tools/sensorfusion/hwt601_bias_stillstand.py` verwendet die vorhandene
`GyroBiasEstimator`-Implementierung und liest die Parameter direkt aus
`amadeus_hwt601.yaml`: 15 s Einlauf, 10 s Anfangskalibrierung (mindestens
800 Proben), anschliessend volle 600 s Auswertung. Verglichen werden:

- unveraenderte Rohdrehrate;
- Korrektur mit dem einmal bestimmten, danach eingefrorenen Anfangsbias;
- dieselbe Anfangskalibrierung mit der vorhandenen 30-s-Biasnachfuehrung.

Der feste Vergleich verhindert, dass ein kleines Ergebnis der adaptiven
Regelung allein als Beleg fuer thermische Stabilitaet des Sensors gilt.
Alle drei Drehraten werden trapezfoermig ueber Host-Monotonzeit integriert.
Die Werte bleiben in Sensorachsen; bei der bestaetigten Montage entspricht
Sensor-Z der Roboter-Z-Achse. Es handelt sich nicht um EKF- oder Kartendrift.

**Wichtige Grenze:** Stillstand beruht in diesem Versuch auf der Zusage der
anwesenden Person, nicht auf verifizierten Radencoderwerten. Es werden auch
keine simulierten Radwerte als angeblicher Messnachweis publiziert. Ein
langsam tatsaechlich gedrehter Roboter koennte durch Biasnachfuehrung falsch
behandelt werden. Der Test ist deshalb keine Bewegungs-/Schlupfabnahme.
Die Gyroskala ist noch nicht durch einen definierten Drehversuch bestaetigt.
Der Sensor ist bereits eingeschaltet; dies ist kein dokumentierter Kaltstart.

Erfasst werden alle Rohproben und der adaptive Bias lokal als CSV, dazu
JSON-Zusammenfassung mit Dauer, Rate, Datenluecken, allen drei Achsen,
End- und Spitzenintegralen sowie Sperrzaehler. Keine Rohdaten ins Repository.
Bei Serialfehler, Saettigung, unplausibler Schwerkraft oder Integrationsluecke
>0,1 s wird abgebrochen und das Teilergebnis als nicht bestanden gespeichert.

Vorlaeufiges Bestehenskriterium: volle 600 s, Rohdatenpruefung bestanden
(mindestens 80 Hz, keine grosse Datenluecke, plausible Schwerkraft), keine
Bias-Sperrprobe und maximaler absoluter adaptiv korrigierter Z-Winkel unter
1 Grad. Der feste Bias wird unabhaengig davon mit ausgewiesen.
Eine bestandene Messung erteilt keine Fusions- oder Fahrfreigabe.

## Wiederholen

Nur nach erneuter Stillstandsabsprache, ohne OAK/Motoren, aus dem Worktree:

```bash
python3 tools/sensorfusion/hwt601_bias_stillstand.py --stationary-confirmed
```

Das Programm benoetigt rund 10 Minuten 25 Sekunden einschliesslich
Anfangskalibrierung. Daten liegen unter
`~/.local/share/amadeus/hwt601/bias-YYYYMMDD-HHMMSS/`.
Abbruch mit Ctrl-C schliesst den Port und bewahrt das als unvollstaendig
markierte Teilergebnis. Kein gespeicherter Produktionsbias wird ersetzt.

## Ergebnis

**08.09.2026, 23:02 Uhr: bestanden im bereits eingeschalteten Zustand.**
Gesamtdauer 625,034 s einschliesslich Anfangskalibrierung; Auswertung
600,008 s. 59.993 gueltige Auswertungsproben bei 99,987 Hz, groesste
Datenluecke 47,719 ms, keine Bias-Sperrung und kein Serialfehler/Abbruch.
Schwerkraftnorm im Mittel 9,88517 m/s² (9,87612..9,89528 m/s²).

| Methode | X-Endwinkel [Grad] | Y-Endwinkel [Grad] | Z-Endwinkel [Grad] | Max. absoluter Z-Winkel [Grad] |
|---|---:|---:|---:|---:|
| Rohdaten | 48,01248 | 228,07737 | 4,65769 | 4,65769 |
| Fester Anfangsbias | -0,71778 | -0,01098 | -0,12022 | 0,12022 |
| Vorhandene Biasnachfuehrung | -0,07185 | -0,05916 | -0,03439 | 0,03985 |

Die grossen rohen X/Y-Integrale sind unkorrigierte Nullpunktabweichungen,
keine nachgewiesene reale Roll-/Nickbewegung. Maximale absolute adaptive
X/Y-Winkel waren 0,07185/0,09003 Grad. Auch der feste Bias haelt Z in diesem
Lauf unter einem Grad: der Erfolg kommt nicht ausschliesslich aus einer
staendig nachgeregelten Nullannahme. Ein laengerer Kaltstart-/Temperaturtest
und ein Bewegungstest werden dadurch nicht ersetzt.

Anfangsbias in Sensorachsen [rad/s]:
`[0.0014175147, 0.0066348628, 0.0001389846]`.
Adaptiver Endbias [rad/s]:
`[0.0013759322, 0.0065997411, 0.0001189358]`.
Diese Werte werden **nicht** als feste Produktionskalibrierung installiert.

Messdaten lokal:
`/home/p/.local/share/amadeus/hwt601/bias-20260908-230201/`.
CSV mit 62.494 Gesamtproben (einschliesslich Einlauf/Kalibrierung),
59.993 Auswertungsproben; `summary.json` meldet `complete=true`, `passed=true`,
`fusion_ready=false`. Unabhaengige Nachrechnung aller drei Integralverlaeufe
und ihrer Spitzen aus CSV mit NumPy stimmt bis deutlich besser als
1e-8 Grad ueberein; Zeitstempel streng steigend, alle Auswertungsproben stabil.
Der abgedeckte Abstand zwischen erster und letzter Auswertungsprobe ist
599,996 s, die restliche Differenz zur Auswertungsdauer liegt am Abtastrand.

71 Softwaretests bestanden. Messprozess beendet, USB-Port wieder geschlossen;
keine Motoren/OAK/ROS-Fusion gestartet. Naechster Schritt ist ein gesondert
abgesprochener definierter Drehversuch, noch keine Fahrfreigabe.
