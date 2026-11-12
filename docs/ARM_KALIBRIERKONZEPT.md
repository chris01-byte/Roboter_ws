# Kalibrierkonzept: Arm, Handgelenkkamera und OAK

**Stand: 12.11.2026.** Dieses Konzept ersetzt das Juli-Konzept
[KONZEPT_KALIBRIERUNG_OAK_ARM.md](../KONZEPT_KALIBRIERUNG_OAK_ARM.md); jenes
bleibt nur als historische Grundlage erhalten. Grundlagen sind
[ARM_KONTEXT](ARM_KONTEXT.md) (Kinematik, Parkpose, Greifsicht der OAK) und
der [Integrationsplan](INTEGRATIONSPLAN_ARM_SOFTWARE.md), Abschnitt 8 sowie
die Stufen M2 und M5–M8. Das Konzept beschreibt Verfahren und Reihenfolge.
Grenzwerte werden erst aus Messungen abgeleitet und im
[Messblatt](ARM_INBETRIEBNAHME_MESSBLATT.md) eingetragen; Zahlen aus dem
Juli-Konzept sind keine Zusage.

**Handgelenkkamera: Orbbec Gemini 305** (Nutzerentscheidung 12.11.2026). Sie
sitzt auf dem Handgelenkglied zwischen J5 und J6, also vor dem Drehgelenk
des Greifers: Sie dreht mit J1–J5, aber nicht mit J6. Kameradaten stammen
aus dem Datenblatt V1.0 vom 06.01.2026, das der Nutzer bereitgestellt hat;
am Gerät sind sie noch nicht geprüft.

## 1. Was sich gegenüber dem Juli-Konzept geändert hat

| Juli-Konzept | Stand 12.11.2026 |
|---|---|
| Arm hinten auf der Plattform | Arm vorn am Kameramast auf einer Hubachse mit 400 mm Hub, sechs Drehgelenke J1–J6 |
| Die OAK ist das einzige Auge für den Griff (Eye-to-Hand) | Die OAK dient nur Erkennung und Anfahrdistanz (Nutzer, 08.11.2026). Den Griff führt die Gemini 305 am Handgelenk |
| Die lange Kette OAK–Mast–Arm muss auf Millimeter stimmen | Die kurze Kette Gemini–Handgelenkglied–Greifer trägt den letzten Schritt; davor regelt der Arm nach dem Bild nach |
| Board am Flansch, Kamera fest | Board fest im Raum, Kamera bewegt sich mit dem Arm (Eye-in-Hand) |
| OAK mit Fixfokus angenommen | Die verbaute OAK-D-S2 hat Autofokus; die laufende Konfiguration legt keinen festen Fokus fest |
| Frame `camera_rgb_optical_frame`, die URDF als einzige Quelle | Der OAK-Treiber liefert `oak_rgb_camera_optical_frame`, die OAK-Lage kommt heute aus `oak.launch.py` |
| Feste Millimeter-Zielwerte | Grenzwerte aus dem gemessenen Fangbereich des Greifers ableiten |

Was bleibt, steht in Abschnitt 8.

## 2. Rollen und Ablauf beim Greifen

| Baustein | Aufgabe | Nötige Genauigkeit |
|---|---|---|
| OAK am Mast | Objekt finden, grobe 3D-Lage, Anfahrdistanz für die Basis | Zentimeterbereich |
| Arm mit Modell und Homing | Gemini in eine Vorposition bringen, aus der sie das Objekt sieht | Objekt muss im Bild der Gemini liegen |
| Gemini 305 am Handgelenk | Objekt mit Farbbild und Tiefe relativ zum Greifer messen, Arm nachführen | trägt den Griff |
| Lichtschranke im Greifer, Kraftsensoren | Objekt zwischen den Fingern, Griff bestätigt | Schaltpunkt |

Ablauf „Sehen, fahren, nachsehen":

1. Die OAK erkennt das Objekt; die Basis fährt auf Anfahrdistanz und steht.
2. Der Arm fährt in eine Vorposition vor dem Objekt.
3. Die Gemini misst das Objekt. Der Arm korrigiert und misst erneut, bis die
   Abweichung im Fangbereich des Greifers liegt.
4. Der Greifer nähert sich entlang seiner Achse; die Tiefe der Gemini führt
   ihn heran, die Lichtschranke meldet das Objekt zwischen den Fingern. Dann
   schließt er, die Kraftsensoren bestätigen den Griff.

Die Lichtschranke bleibt nötig: Die Gemini misst passiv per Farb-Stereo und
braucht laut Hersteller Textur. Glatte oder durchsichtige Flaschen liefern
Tiefenlücken. Ein zusätzlicher Abstandssensor im Greifer ist optional.

Folge für die Kalibrierung: Mastbiegung, Kippeln der Basis, Spiel in
Hubachse, J1 und J2 sowie eine verschobene OAK-Lage wirken nur noch darauf,
ob das Objekt in der Vorposition im Bild liegt. Für den Griff zählen die
Werkskalibrierung der Gemini, ihre Lage zum Handgelenkglied, der Greifpunkt
und die Lichtschranke.

Sichtfeldbedingung für die Vorposition: Bei Abstand d zwischen Kamera und
Objekt und horizontalem Bildwinkel α darf die Grobposition seitlich höchstens
etwa d · tan(α/2) − halbe Objektbreite − Reserve danebenliegen. Diese Größe
bestimmt, wie genau K1 und K2 sein müssen.

## 3. Kalibrierbausteine im Überblick

| Nr. | Baustein | Frage | Verfahren | Arm nötig | Stufe |
|---|---|---|---|---|---|
| K1 | OAK-Lage | Wo sitzt die OAK relativ zu `base_link`? | CAD, gemessene Höhe, Bodenebene | nein | eigener Sensor-Frame-Schritt |
| K2 | Armmodell | Stimmt `base_link` → Handgelenkglied → Flansch? | CAD-Achsen, gemessene Referenzkanten, Drehsinn, Zeigetest | ja | M2 |
| K3 | Werkzeug | Wo liegen Greifpunkt und Lichtschranke zum Flansch, wie groß ist der Fangbereich? | Greifer-CAD, Prüfung mit Zeigespitze und Testobjekt | ja | M5, M6 |
| K4 | Werkskalibrierung der Gemini | Stimmen Farb-Intrinsik, Tiefe und Deckung von Tiefe und Farbe? | Prüfung am Board und gegen ein Maß | nein | vor M7 |
| K5 | Gemini zum Handgelenkglied | Wo sitzt die Kamera am Arm? | Eye-in-Hand mit der Armpose bis J5: Board fest im Raum, 15–25 Armposen | ja | M7 |
| K6 | Gesamtprüfung | Trifft der Greifer? | Zeigetest und Greiftest an markierten Positionen | ja | M7, M8 |
| K7 | OAK gegen Gemini | Passen Grobziel und Feinmessung zusammen? | Dasselbe Objekt mit beiden messen, Abweichung protokollieren | ja | ab M8 laufend |

Reihenfolge: K1 und K4 sind armunabhängig und können jederzeit erfolgen.
Danach K2, dann K3, dann K5. K6 schließt ab, K7 läuft im Betrieb mit. Fehler
früher Stufen lassen sich später nicht herausrechnen.

## 4. Die Stufen im Einzelnen

### K1 — Lage der OAK

**Ziel:** OAK-Lage in `base_link` im Zentimeterbereich.

**Vorgehen:** Höhe gemessen (1350 mm, 10.11.2026), Neigung aus der
Bodenebene wie beim Verfahren vom 27.07.2026, Position vorn und seitlich aus
dem CAD. Gehört in den offenen Sensor-Frame-Schritt, in dem
`oak.launch.py` von 1340 auf 1350 mm korrigiert wird. Der Autofokus der
OAK-D-S2 ist für die Grobrolle zulässig. Wird der Fokus fixiert, wird die
Intrinsik dazu einmal geprüft. Die OAK-Lage hat genau einen Eigentümer:
heute `oak.launch.py`. Ob sie später in die Arm-URDF wandert, wird beim Bau
der URDF entschieden; nie beide gleichzeitig.

**Abnahme:** Bodenebene und Objekte in bekannter Entfernung liegen innerhalb
eines vorher festgelegten Zentimeterwerts.

### K2 — Armmodell

**Ziel:** Die TF-Kette `base_link` → Hubschlitten → J1 … J5 →
Handgelenkglied → J6 → Flansch stimmt so gut, dass die Sichtfeldbedingung
erfüllt ist.

**Vorgehen:**

1. Arm-URDF aus den CAD-Achsen in ARM_KONTEXT erstellen. Das Gelenkmodell
   gibt zwei STEP-Exporte auf 0,4 mm wieder; real sitzt der Arm rund 10 mm
   tiefer als im CAD. Das Handgelenkglied zwischen J5 und J6 bekommt einen
   eigenen Frame, weil die Kamera daran sitzt.
2. Je Achse Drehsinn (M1B) und Winkel der Referenzkante q_home (M2) messen;
   Hubachse mit Spindelsteigung und Referenz.
3. Zeigetest Arm allein: Zeigespitze am Flansch nacheinander auf markierte
   Punkte einer Prüfplatte mit bekannter Lage fahren und die Abweichung
   messen. Immer aus derselben Richtung anfahren.

**Abnahme:** Abweichung an unabhängigen Punkten dokumentiert und kleiner als
der aus der Sichtfeldbedingung abgeleitete Grenzwert.

### K3 — Werkzeug und Greifersensoren

**Ziel:** Greifpunkt (TCP) sowie Lage und Schaltpunkt der Lichtschranke
relativ zum Flansch; Fangbereich des Greifers.

**Vorgehen:** Werte aus dem Greifer-CAD als fester Joint in der Arm-URDF.
Der Greifpunkt liegt auf der J6-Achse. Seine Lage zum Handgelenkglied und
damit zur Kamera hängt deshalb nicht von J6 ab; J6 dreht nur die Finger.
Prüfung mit Zeigespitze am TCP und mit einem Testobjekt, das die
Lichtschranke an bekannter Stelle auslöst. Dazu wird der Fangbereich
gemessen: seitlicher, axialer und Winkelversatz, bei dem der Greifer das
Referenzobjekt noch sicher fasst (M5).

**Abnahme:** TCP-Prüfung und Fangbereich dokumentiert; aus dem Fangbereich
folgen die Grenzwerte für K5 und K6.

### K4 — Werkskalibrierung der Gemini 305 prüfen

**Ziel:** Bestätigen, dass Farb-Intrinsik, Tiefe und die Deckung von Tiefe
und Farbe für die Betriebseinstellung stimmen. Die Gemini ist ab Werk
kalibriert und hat feste Fokusse; eine eigene Intrinsik-Kalibrierung ist nur
nötig, wenn die Prüfung scheitert.

**Vorgehen:**

1. Betriebseinstellung festlegen und notieren: Preset, Auflösung (zum
   Beispiel 848 × 530 für Tiefe und Farbe oder 1280 × 800), Bildrate,
   Disparitätsbereich, Firmwarestand.
2. Reprojektion: ChArUco-Board des vorhandenen Recorders (7 × 5 Felder,
   `DICT_5X5_250`, gemessene Feldgröße) im Farbbild erkennen und mit der
   gelieferten Intrinsik reprojizieren, über das ganze Bild verteilt.
3. Tiefe: ebene, strukturierte Fläche in gemessenen Abständen im späteren
   Arbeitsbereich (Greifpunkt und Vorposition) gegen ein Maß prüfen. Der
   Tiefennullpunkt liegt laut Datenblatt 3,95 mm hinter der Frontscheibe.
4. Deckung: Ränder des Boards im an das Farbbild angeglichenen Tiefenbild
   (D2C) gegen das Farbbild prüfen.

**Abnahme:** Reprojektionsfehler, Tiefenabweichung und Deckung dokumentiert
und kleiner als vorher festgelegte Werte.

### K5 — Lage der Gemini zum Handgelenkglied (Eye-in-Hand)

**Ziel:** Feste Transformation Handgelenkglied → Kamera. Bezug ist bewusst
das Glied hinter J5 und nicht der Flansch, weil die Kamera nicht mit J6
dreht.

**Vorgehen:**

1. Board starr im Arbeitsraum befestigen, Basis steht und ist gegen Rollen
   gesichert. J6 in einer Stellung festhalten, in der die Finger das Board
   nicht verdecken.
2. 15–25 Armposen anfahren, aus denen die Kamera das Board sieht: im
   späteren Arbeitsabstand zwischen Vorposition und Griff, mit Drehungen um
   mindestens zwei Achsen, keine zwei Posen fast gleich. Jedes Gelenk aus
   derselben Richtung anfahren, vor der Aufnahme Stillstand abwarten,
   mehrere Bilder mitteln.
3. Je Pose das Paar `base_T_wrist` (Armpose bis zum Handgelenkglied aus TF)
   und `camera_T_board` (Boardpose aus dem Farbbild) speichern.
4. Lösen mit `cv2.calibrateHandEye` in der Eye-in-Hand-Form: Die Armposen
   gehen unverändert hinein, das Ergebnis ist `wrist_T_camera`.
5. Konsistenz: Für jedes Paar muss `base_T_wrist · wrist_T_camera ·
   camera_T_board` dieselbe Boardlage im Raum ergeben. Die Streuung zeigt
   die Qualität.
6. Plausibilität: Das Ergebnis muss zur Halterung im CAD passen. Liegt es
   quer, sind fast immer optischer und mechanischer Kamera-Frame vertauscht.

Das Ergebnis wird als fester Joint Handgelenkglied → Kamera-Grundframe in
die Arm-URDF eingetragen, mit Datum, Einstellung, Posenzahl und Residuen.
Die Frames innerhalb der Kamera (Grundframe zu optischen Frames von Farbe und
Tiefe) liefert der Kameratreiber aus der Werkskalibrierung; sie werden nicht
ein zweites Mal veröffentlicht. Die Gleichungsform aus Abschnitt 8 des
Integrationsplans gilt sinngemäß, mit fester Boardlage im Raum.

**Abnahme:** Residuen und unabhängige Prüfpunkte dokumentiert, kleiner als
der aus dem Fangbereich abgeleitete Grenzwert.

### K6 — Gesamtprüfung

1. Zeigetest: Board oder Marker frei im Raum. Die Gemini misst aus der
   Vorposition, der TCP fährt auf eine markierte Ecke. Abweichung messen, an
   mindestens fünf Positionen (links, rechts, nah, fern, hoch). Zufällige
   Streuung ist Rauschen; eine gleichbleibende Richtung deutet auf K2, K3
   oder K5.
2. Greiftest mit dem Referenzobjekt an markierten Positionen nach dem Ablauf
   aus Abschnitt 2 (M8), auch mit gedrehtem J6.

**Abnahme:** Restfehler mit Reserve innerhalb des Fangbereichs, vorher
festgelegte Erfolgsquote erreicht, Fehlgriffe werden erkannt.

### K7 — OAK gegen Gemini

Bei jedem Griff misst die OAK das Objekt grob und die Gemini fein. Die
Abweichung wird protokolliert. Wächst sie, ist K1 neu zu prüfen, bevor
Objekte aus der Vorposition herausfallen.

## 5. Fehlerbudget und Grenzwerte

Grenzwerte werden aus zwei gemessenen Größen abgeleitet:

- **Fangbereich des Greifers** (K3): Was er seitlich, axial und im Winkel
  noch ausgleicht. Daraus folgen die Grenzwerte für K4, K5 und K6.
- **Sichtfeldbedingung der Vorposition** (Abschnitt 2): Daraus folgen die
  Grenzwerte für K1 und K2.

Beiträge zum Griff: Werkskalibrierung (K4), Lage der Kamera zum
Handgelenkglied (K5), Greifpunkt (K3), Bild- und Tiefenmessung des Objekts,
Lichtschranke und die Bewegung des Arms im letzten, kurzen Stück. Nicht mehr
direkt im Griff: OAK-Lage, Mast, Hubachse, J1 und J2.

## 6. Die Kamera: Orbbec Gemini 305

Herstellerangaben aus dem Datenblatt V1.0:

| Merkmal | Angabe | Folge für Arm und Kalibrierung |
|---|---|---|
| Messprinzip | passives Farb-Stereo, 18 mm Basis, Global Shutter, fester Fokus, kein Projektor | braucht Textur und Licht; glatte und durchsichtige Flächen liefern Lücken |
| Arbeitsbereich | 4–100 cm, ideal 7–50 cm | Greifpunkt rund 15 cm vor der Kamera liegt im Idealbereich |
| Mindestabstand | 50 mm (1280 × 800) bzw. 40 mm (848 × 530) bei Disparitätsbereich 256, nur im Nahbereichs-Preset; 90 bzw. 60 mm bei 128; 180 bzw. 120 mm bei 64 | 128 genügt für rund 15 cm; 256 senkt die zulässige Umgebungstemperatur auf 40 °C |
| Sichtfeld | Tiefe H 88° × V 65°, Farbe H 94° × V 68° (16:10) | Greifer und Objekt gleichzeitig im Bild |
| Ströme | Tiefe bis 1280 × 800 bei 30 Bildern/s, 848 × 530 bei 60; Farbe 1280 × 800 bei 60; über USB 2.0 nur bis 848 × 530 bei 15 bzw. 640 × 480 bei 30 | USB 3 verwenden |
| Genauigkeit | Tiefe ≤ ±1,8 %, räumliche Präzision ≤ 1 % bei 50 cm auf heller Ebene | in K4 im eigenen Arbeitsbereich prüfen |
| Koordinaten | Ursprung im optischen Zentrum des linken Farbmoduls (Seite mit USB-C); x rechts, y unten, z vorn | passt zur Kameraframe-Konvention des Treibers |
| Anschluss | USB-C mit Schraubverriegelung; 5 V, mindestens 0,7 A; typisch 1,6 W, höchstens 2 W; USB-IF-zertifiziertes Kabel, bis 3 m empfohlen | Kabelweg bis zum Jetson messen |
| Befestigung | unten 1/4-20 UNC und 2 × M3 im Abstand 20 mm, hinten 2 × M3 im Abstand 20 mm; M3 höchstens 4,8 mm tief | Unterseite nach unten montieren, sonst steht das Bild auf dem Kopf |
| Maße, Masse | 42 × 42 × 23 mm, 68 g | rund 0,1 kg mit Halter und Kabel am Handgelenk |
| Temperatur | Umgebung −10 bis 45 °C (40 °C bei Disparität 256); Gehäuserückseite bis 60 °C | Halter nicht aus PLA, sondern zum Beispiel PETG, ASA oder Aluminium |
| Plattform | ARM: Ubuntu 22.04/24.04, Jetson Orin Nano/NX/AGX/Thor, USB 3.0 | Jetson-Modell des Roboters bestätigen |

Montage nach CAD-Rechnung vom 12.11.2026 (Einzelheiten in
[ARM_KONTEXT](ARM_KONTEXT.md#gemini-305-am-handgelenk-12112026)): oben auf dem
Handgelenkglied, Frontscheibe rund 20 mm hinter der Flanschfläche, leicht
nach unten zur Greiferachse geneigt. Der drehende Greifer kann die Kamera so
nicht berühren. J6 dreht die Finger im Bild; die übliche Greifstellung legt
die Finger links und rechts der Bildmitte.

## 7. Werkzeuge im Repository und nötige Änderungen

| Werkzeug | Stand | Nötig |
|---|---|---|
| Kameratreiber | nicht im Repo | Orbbec SDK und ROS-2-Treiber für Humble auf dem Jetson; Unterstützung der Gemini 305 vor dem Kauf weiterer Teile prüfen |
| `handeye_recorder` | Speichert Paare Armpose und `camera_T_board` mit ChArUco und Stillstandsprüfung | Für Eye-in-Hand verwendbar: Farbbild- und Info-Topic der Gemini, Frame des Handgelenkglieds statt Flansch |
| `handeye_solve` | Nur Eye-to-Hand: invertiert die Armposen, gibt die OAK-Lage aus | Eye-in-Hand-Modus (Armposen nicht invertieren, Ergebnis `wrist_T_camera`, Konsistenz der Boardlage), Ausgabe für den Kamera-Joint am Handgelenkglied, Frame-Namen des laufenden Systems; vorher Test mit synthetischen Daten |
| Prüfung der Werkskalibrierung (K4) | kein Werkzeug im Repo | kurzes Skript für Reprojektion, Tiefe gegen Maß und Deckung |
| Arm-URDF | nur die überholte Dummy-URDF | neue URDF aus den CAD-Achsen mit Hubachse, Handgelenkglied, Kamera-Joint, Flansch und Greifer |

Änderungen an Kalibriercode und Sensor-Frames sind sicherheitsrelevant und
werden als eigener, getesteter Schritt umgesetzt.

## 8. Was aus dem Juli-Konzept bleibt

- ChArUco-Board statt Einzelmarker; Feldgröße nachmessen; steife Platte,
  matter Druck.
- Statische Paare mit gleicher Anfahrrichtung, Stillstand und Mittelung über
  mehrere Bilder; Posen gut verteilt.
- Zuerst das Armmodell, dann die Kamera.
- Jeder TF hat genau einen Eigentümer; keine parallelen
  `static_transform_publisher` für dieselben Frames.
- Jeder Lauf wird versioniert abgelegt: Datum, Einstellung, Posenzahl,
  Residuen, Board-Maß.
- Typische Fallen: optischer und mechanischer Frame vertauscht, Auflösung
  oder Preset nachträglich geändert, zu ähnliche Posen, Basis rollt während
  des Laufs. Neu: Die Kamerahalterung muss starr am Handgelenkglied sitzen.

## 9. Wann neu kalibriert wird

| Ereignis | Betroffen |
|---|---|
| Halterung oder Neigung der Gemini geändert | K5 |
| Preset, Auflösung oder Firmware der Gemini geändert | K4 prüfen |
| Greifer umgebaut | K3 (K5 nicht, die Kamera sitzt vor J6) |
| Gelenk, Kupplung, Homing-Sensor oder Magnet umgebaut | K2 |
| Mast, OAK-Halter oder OAK-Neigung geändert | K1 |
| Kollision oder Sturz | K2, K4 und K5 prüfen |

Schnellprüfung: Eine Prüfmarke fest am Roboter, die die Gemini aus einer
festen Armstellung sieht. Die gemessene Lage wird mit dem Sollwert
verglichen und protokolliert, vor Vorführungen und nach Umbauten.
