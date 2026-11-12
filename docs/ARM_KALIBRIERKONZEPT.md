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

## 1. Was sich gegenüber dem Juli-Konzept geändert hat

| Juli-Konzept | Stand 12.11.2026 |
|---|---|
| Arm hinten auf der Plattform | Arm vorn am Kameramast auf einer Hubachse mit 400 mm Hub, sechs Drehgelenke J1–J6 |
| Die OAK ist das einzige Auge für den Griff (Eye-to-Hand) | Die OAK dient nur Erkennung und Anfahrdistanz (Nutzer, 08.11.2026). Den Griff führt eine Kamera am Handgelenk (Nutzer plant sie, Modell offen) |
| Die lange Kette OAK–Mast–Arm muss auf Millimeter stimmen | Die kurze Kette Handgelenkkamera–Flansch–Greifer trägt den letzten Schritt; davor regelt der Arm nach dem Bild nach |
| Board am Flansch, Kamera fest | Board fest im Raum, Kamera bewegt sich mit dem Arm (Eye-in-Hand) |
| OAK mit Fixfokus angenommen | Die verbaute OAK-D-S2 hat Autofokus; die laufende Konfiguration legt keinen festen Fokus fest |
| Frame `camera_rgb_optical_frame`, die URDF als einzige Quelle | Der OAK-Treiber liefert `oak_rgb_camera_optical_frame`, die OAK-Lage kommt heute aus `oak.launch.py` |
| Feste Millimeter-Zielwerte | Grenzwerte aus dem gemessenen Fangbereich des Greifers ableiten |

Was bleibt, steht in Abschnitt 8.

## 2. Rollen und Ablauf beim Greifen

| Baustein | Aufgabe | Nötige Genauigkeit |
|---|---|---|
| OAK am Mast | Objekt finden, grobe 3D-Lage, Anfahrdistanz für die Basis | Zentimeterbereich |
| Arm mit Modell und Homing | Handgelenkkamera in eine Vorposition bringen, aus der sie das Objekt sieht | Objekt muss im Bild der Handgelenkkamera liegen |
| Handgelenkkamera | Objekt relativ zum Greifer messen, Arm nachführen | trägt den Griff |
| Abstandssensor und Lichtschranke im Greifer, Kraftsensoren | Abstand im letzten Stück, Objekt zwischen den Fingern, Griff bestätigt | Schaltpunkt und Abstand |

Ablauf „Sehen, fahren, nachsehen":

1. Die OAK erkennt das Objekt; die Basis fährt auf Anfahrdistanz und steht.
2. Der Arm fährt in eine Vorposition vor dem Objekt.
3. Die Handgelenkkamera misst das Objekt. Der Arm korrigiert und misst
   erneut, bis die Abweichung im Fangbereich des Greifers liegt.
4. Der Greifer nähert sich entlang seiner Achse, bis Abstandssensor oder
   Lichtschranke das Objekt melden. Dann schließt er, die Kraftsensoren
   bestätigen den Griff.

Folge für die Kalibrierung: Mastbiegung, Kippeln der Basis, Spiel in
Hubachse, J1 und J2 sowie eine verschobene OAK-Lage wirken nur noch darauf,
ob das Objekt in der Vorposition im Bild liegt. Für den Griff zählen die
Intrinsik der Handgelenkkamera, ihre Lage zum Flansch, der Greifpunkt und
der Abstandssensor.

Sichtfeldbedingung für die Vorposition: Bei Abstand d zwischen Kamera und
Objekt und horizontalem Bildwinkel α darf die Grobposition seitlich höchstens
etwa d · tan(α/2) − halbe Objektbreite − Reserve danebenliegen. Diese Größe
bestimmt, wie genau K1 und K2 sein müssen.

## 3. Kalibrierbausteine im Überblick

| Nr. | Baustein | Frage | Verfahren | Arm nötig | Stufe |
|---|---|---|---|---|---|
| K1 | OAK-Lage | Wo sitzt die OAK relativ zu `base_link`? | CAD, gemessene Höhe, Bodenebene | nein | eigener Sensor-Frame-Schritt |
| K2 | Armmodell | Stimmt `base_link` → Flansch? | CAD-Achsen, gemessene Referenzkanten, Drehsinn, Zeigetest | ja | M2 |
| K3 | Werkzeug | Wo liegen Greifpunkt, Abstandssensor und Lichtschranke zum Flansch? | Greifer-CAD, Prüfung mit Zeigespitze und Testobjekt | ja | M5, M6 |
| K4 | Intrinsik der Handgelenkkamera | Wie bildet die Kamera Pixel auf Sehstrahlen ab? | ChArUco-Board am Tisch; bei RGB-D-Kameras Werkskalibrierung prüfen | nein | vor M7 |
| K5 | Handgelenkkamera zum Flansch | Wo sitzt die Kamera am Arm? | Eye-in-Hand: Board fest im Raum, 15–25 Armposen | ja | M7 |
| K6 | Gesamtprüfung | Trifft der Greifer? | Zeigetest und Greiftest an markierten Positionen | ja | M7, M8 |
| K7 | OAK gegen Handgelenkkamera | Passen Grobziel und Feinmessung zusammen? | Dasselbe Objekt mit beiden messen, Abweichung protokollieren | ja | ab M8 laufend |

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

**Ziel:** Die TF-Kette `base_link` → Hubschlitten → J1 … J6 → Flansch stimmt
so gut, dass die Sichtfeldbedingung erfüllt ist.

**Vorgehen:**

1. Arm-URDF aus den CAD-Achsen in ARM_KONTEXT erstellen. Das Gelenkmodell
   gibt zwei STEP-Exporte auf 0,4 mm wieder; real sitzt der Arm rund 10 mm
   tiefer als im CAD.
2. Je Achse Drehsinn (M1B) und Winkel der Referenzkante q_home (M2) messen;
   Hubachse mit Spindelsteigung und Referenz.
3. Zeigetest Arm allein: Zeigespitze am Flansch nacheinander auf markierte
   Punkte einer Prüfplatte mit bekannter Lage fahren und die Abweichung
   messen. Immer aus derselben Richtung anfahren.

**Abnahme:** Abweichung an unabhängigen Punkten dokumentiert und kleiner als
der aus der Sichtfeldbedingung abgeleitete Grenzwert.

### K3 — Werkzeug und Greifersensoren

**Ziel:** Greifpunkt (TCP) sowie Lage und Schaltpunkt von Abstandssensor und
Lichtschranke relativ zum Flansch.

**Vorgehen:** Werte aus dem Greifer-CAD als fester Joint in der Arm-URDF.
Prüfung mit Zeigespitze am TCP und mit einem Testobjekt, das die
Lichtschranke an bekannter Stelle auslöst. Dazu wird der Fangbereich des
Greifers gemessen: seitlicher, axialer und Winkelversatz, bei dem der
Greifer das Referenzobjekt noch sicher fasst (M5).

**Abnahme:** TCP-Prüfung und Fangbereich dokumentiert; aus dem Fangbereich
folgen die Grenzwerte für K5 und K6.

### K4 — Intrinsik der Handgelenkkamera

**Ziel:** Brennweite, Bildmitte und Verzeichnung für genau die
Betriebsauflösung und den Betriebsfokus.

**Vorgehen:**

1. Auflösung festlegen und Fokus fixieren. Bei einem M12-Objektiv den Fokus
   auf die Arbeitsdistanz zwischen Vorposition und Griff stellen und
   sichern. Kein Autofokus im Betrieb.
2. ChArUco-Board des vorhandenen Recorders verwenden (7 × 5 Felder,
   `DICT_5X5_250`); die Feldgröße nachmessen und den gemessenen Wert
   eintragen. Board auf eine steife Platte kleben, matt drucken.
3. 20–40 Bilder über das ganze Bildfeld und mit verschiedenen Neigungen
   aufnehmen und mit OpenCV oder dem ROS-Paket `camera_calibration`
   auswerten.
4. Ergebnis als `camera_info`-Datei mit Datum, Auflösung und Fokusstand
   ablegen.

RGB-D-Kameras wie RealSense D405, Orbbec Gemini 305 oder OAK-D SR bringen
eine Werkskalibrierung mit. Dann wird sie nur geprüft: Reprojektion an einem
Board und Tiefe gegen ein Maß.

**Abnahme:** Reprojektionsfehler dokumentiert und kleiner als ein vorher
festgelegter Wert.

### K5 — Lage der Handgelenkkamera zum Flansch (Eye-in-Hand)

**Ziel:** Feste Transformation Flansch → Kamera.

**Vorgehen:**

1. Board starr im Arbeitsraum befestigen, Basis steht und ist gegen Rollen
   gesichert.
2. 15–25 Armposen anfahren, aus denen die Kamera das Board sieht: im
   späteren Arbeitsabstand zwischen Vorposition und Griff, mit Drehungen um
   mindestens zwei Achsen, keine zwei Posen fast gleich. Jedes Gelenk aus
   derselben Richtung anfahren, vor der Aufnahme Stillstand abwarten,
   mehrere Bilder mitteln.
3. Je Pose das Paar `base_T_tool` (Armpose aus TF) und `camera_T_board`
   (Boardpose aus dem Bild) speichern.
4. Lösen mit `cv2.calibrateHandEye` in der Eye-in-Hand-Form: Die Armposen
   gehen unverändert hinein, das Ergebnis ist `tool_T_camera`.
5. Konsistenz: Für jedes Paar muss `base_T_tool · tool_T_camera ·
   camera_T_board` dieselbe Boardlage im Raum ergeben. Die Streuung zeigt
   die Qualität.
6. Plausibilität: Das Ergebnis muss zur Halterung im CAD passen. Liegt es
   quer, sind fast immer optischer und mechanischer Kamera-Frame vertauscht.

Das Ergebnis wird als fester Joint Flansch → Kamera in die Arm-URDF
eingetragen, mit Datum, Auflösung, Posenzahl und Residuen. Die
Gleichungsform aus Abschnitt 8 des Integrationsplans gilt sinngemäß, mit
fester Boardlage im Raum statt am Flansch.

**Abnahme:** Residuen und unabhängige Prüfpunkte dokumentiert, kleiner als
der aus dem Fangbereich abgeleitete Grenzwert.

### K6 — Gesamtprüfung

1. Zeigetest: Board oder Marker frei im Raum. Die Handgelenkkamera misst aus
   der Vorposition, der TCP fährt auf eine markierte Ecke. Abweichung
   messen, an mindestens fünf Positionen (links, rechts, nah, fern, hoch).
   Zufällige Streuung ist Rauschen; eine gleichbleibende Richtung deutet auf
   K2, K3 oder K5.
2. Greiftest mit dem Referenzobjekt an markierten Positionen nach dem Ablauf
   aus Abschnitt 2 (M8).

**Abnahme:** Restfehler mit Reserve innerhalb des Fangbereichs, vorher
festgelegte Erfolgsquote erreicht, Fehlgriffe werden erkannt.

### K7 — OAK gegen Handgelenkkamera

Bei jedem Griff misst die OAK das Objekt grob und die Handgelenkkamera fein.
Die Abweichung wird protokolliert. Wächst sie, ist K1 neu zu prüfen, bevor
Objekte aus der Vorposition herausfallen.

## 5. Fehlerbudget und Grenzwerte

Grenzwerte werden aus zwei gemessenen Größen abgeleitet:

- **Fangbereich des Greifers** (K3): Was er seitlich, axial und im Winkel
  noch ausgleicht. Daraus folgen die Grenzwerte für K4, K5 und K6.
- **Sichtfeldbedingung der Vorposition** (Abschnitt 2): Daraus folgen die
  Grenzwerte für K1 und K2.

Beiträge zum Griff: Intrinsik (K4), Lage der Kamera zum Flansch (K5),
Greifpunkt (K3), Bildmessung des Objekts, Abstandssensor und die Bewegung
des Arms im letzten, kurzen Stück. Nicht mehr direkt im Griff: OAK-Lage,
Mast, Hubachse, J1 und J2.

## 6. Kameratypen und was sie für die Kalibrierung bedeuten

| Variante | Tiefe | K4 | Abstand im letzten Stück |
|---|---|---|---|
| Günstige USB-Farbkamera (UVC) mit festem Fokus | keine | selbst kalibrieren | Abstandssensor im Greifer (zum Beispiel VL53L7CX) und Lichtschranke |
| RGB-D-Kamera für kurze Distanz (D405, Gemini 305, OAK-D SR) | ja | Werkskalibrierung prüfen | Tiefe der Kamera; Lichtschranke bleibt als Bestätigung |

Beide Varianten nutzen dieselben Stufen. Durchsichtige und glänzende
Flaschen erschweren Stereotiefe und Lichtlaufzeitmessung gleichermaßen; die
Lichtschranke und die Kraftsensoren bestätigen den Griff unabhängig davon.

## 7. Werkzeuge im Repository und nötige Änderungen

| Werkzeug | Stand | Nötig |
|---|---|---|
| `handeye_recorder` | Speichert Paare `base_T_tool` und `camera_T_board` mit ChArUco und Stillstandsprüfung | Für Eye-in-Hand verwendbar: Bild- und Info-Topic auf die Handgelenkkamera, Flansch-Frame der neuen URDF |
| `handeye_solve` | Nur Eye-to-Hand: invertiert die Armposen, gibt die OAK-Lage aus | Eye-in-Hand-Modus (Armposen nicht invertieren, Ergebnis `tool_T_camera`, Konsistenz der Boardlage), Ausgabe für den Kamera-Joint am Flansch, Frame-Namen des laufenden Systems; vorher Test mit synthetischen Daten |
| Intrinsik der Handgelenkkamera | kein Werkzeug im Repo | ROS-Paket `camera_calibration` oder kurzes OpenCV-Skript |
| Arm-URDF | nur die überholte Dummy-URDF | neue URDF aus den CAD-Achsen mit Hubachse, Flansch, Greifer und Kamera-Joint |

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
- Jeder Lauf wird versioniert abgelegt: Datum, Auflösung, Fokus, Posenzahl,
  Residuen, Board-Maß.
- Typische Fallen: optischer und mechanischer Frame vertauscht, Auflösung
  nachträglich geändert, zu ähnliche Posen, Basis rollt während des Laufs.
  Neu: Die Kamerahalterung muss starr am Flansch oder Handgelenk sitzen,
  nie an den Fingern.

## 9. Wann neu kalibriert wird

| Ereignis | Betroffen |
|---|---|
| Halterung, Fokus, Auflösung oder Objektiv der Handgelenkkamera geändert | K4, K5 |
| Greifer umgebaut | K3; K5, wenn die Kamera am Greifer sitzt |
| Gelenk, Kupplung, Homing-Sensor oder Magnet umgebaut | K2 |
| Mast, OAK-Halter oder OAK-Neigung geändert | K1 |
| Kollision oder Sturz | K2 und K5 prüfen |

Schnellprüfung: Eine Prüfmarke fest am Roboter, die die Handgelenkkamera aus
einer festen Armstellung sieht. Die gemessene Lage wird mit dem Sollwert
verglichen und protokolliert, vor Vorführungen und nach Umbauten.
