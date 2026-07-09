# Konzept: Hand-Auge-Kalibrierung Roboterarm <-> zentrale OAK-Kamera

**Stand:** 2026-07-04 · **Betrifft:** `robot_description`, `semantic_perception`, später `arm_action_server`/MoveIt 2
**Variante:** Eye-to-Hand (Kamera fest an der Basis/am Mast, der Arm bewegt sich)

---

## 0. Ziel und Grundidee

**Ziel in einem Satz:** Nach der Kalibrierung kann eine Objektpose aus dem Kamerabild auf wenige
Millimeter genau in Armkoordinaten umgerechnet werden — die Voraussetzung dafür, dass
`ComputeGrasp` / `MoveArmToPose` das Objekt wirklich treffen.

„Kalibrierung" besteht hier aus **drei Bausteinen**, die aufeinander aufbauen:

| # | Baustein | Frage | Status im Projekt |
|---|---|---|---|
| 1 | **Intrinsik** | Wie bildet die Kamera Pixel auf Sehstrahlen ab? (Brennweite, Verzeichnung) | OAK: ab Werk im Gerät gespeichert — wird **geprüft**, nicht neu gemacht |
| 2 | **Hand-Auge-Transformation** (Extrinsik) | **Wo** sitzt die Kamera relativ zum Roboter? `T(base_link -> camera_rgb_optical_frame)` | Platzhalter in der URDF — **Kern dieses Konzepts** |
| 3 | **Werkzeug-Bezug (TCP)** | Wo ist der Greifpunkt relativ zum Flansch? `tool0 -> gripper_tcp` | Dummy-Werte — wird in Stufe A mit vermessen |

**Grundidee der Hand-Auge-Kalibrierung, anschaulich:**
Am Greifer wird ein Kalibrierboard (Schachbrett mit Markern) befestigt. Der Arm **weiß**, wo seine
Hand ist (Gelenkwinkel + Armmodell). Die Kamera **sieht**, wo das Board ist (Markererkennung).
Fährt man viele verschiedene Armstellungen ab, gibt es genau **eine** Kameramontage, die alle
Beobachtungen gleichzeitig erklärt — die rechnet ein fertiger Löser (OpenCV, Gleichungsform
„AX = ZB") aus. Man muss weder die Kameraposition noch die Board-Halterung von Hand vermessen:
**beide fallen als Ergebnis heraus.**

**Warum Eye-to-Hand:** Laut URDF sitzt die Kamera am Mast der Basis (ca. x=0,12 m, z=0,36 m auf
`base_link`), der Arm hinten auf der Plattform. Die Kamera bewegt sich nicht mit dem Arm — das ist
die Eye-to-Hand-Variante (Gegensatz: Eye-in-Hand = Kamera am Handgelenk).

---

## 1. Ausgangslage im Workspace

Was schon da ist / was fehlt:

| Punkt | Zustand |
|---|---|
| Frames `camera_link`, `camera_rgb_optical_frame`, `tool0`, `gripper_tcp` in der URDF | vorhanden, Werte sind `[ANPASSEN]`-Platzhalter |
| Optischer Kamera-Frame korrekt gedreht (z nach vorn, x rechts, y unten) | korrekt vorhanden |
| Kamera-Joint in der URDF | hat **nur `oak_yaw`** als Rotation — das Kalibrierergebnis ist aber 6-DoF: **auf volle rpy erweitern** (Stufe F) |
| Echter Arm | nur Dummy-URDF; kein Treiber, keine `/joint_states` — **Voraussetzung, Stufe A** |
| Kameratreiber (depthai-ros) | noch Platzhalter in `robot.launch.py` — wird in Stufe B integriert |
| `semantic_perception` | erwartet bereits `camera_frame: camera_rgb_optical_frame` — passt, keine Änderung nötig |

**Wichtige Designentscheidung (Fehlerkette kurz halten):**
Für das **Greifen** darf die Karte (`map`) nicht in der Kette liegen — `map -> base_link` enthält
SLAM-Fehler im Zentimeterbereich. Die Manipulationskette muss lauten:
`camera_rgb_optical_frame -> base_link -> Arm`. Praktisch: Die Fein-Detektion am Zielort
(`DetectObjectFine` / `refine_object_pose`) liefert die Greifpose im **`base_link`**, nicht in `map`.
(Deckt sich mit Prüfbericht-Befunden K2/S7 — die grobe Suche darf in `map` bleiben, der Griff nicht.)

---

## 2. Stufenplan im Überblick

```
A  Mechanik fixieren + echtes Armmodell     (der Arm ist das Messgeraet!)
B  Intrinsik der OAK pruefen                (Werkskalibrierung verifizieren)
C  Kalibrierboard bauen + am Flansch montieren
D  15-25 Posen abfahren und Messpaare sammeln
E  Loesung rechnen (OpenCV / easy_handeye2)
F  Ergebnis in die URDF einpflegen          (eine einzige Quelle!)
G  Ende-zu-Ende validieren (Zeigetest, Greiftest)
H  Absichern + Wartungsroutine
```

Jede Stufe hat unten: **Ziel · Vorgehen · Abnahmekriterium**. Erst wenn die Abnahme erfüllt ist,
lohnt die nächste Stufe — Fehler in frühen Stufen lassen sich später nicht herausrechnen.

> **Wichtig:** MoveIt ist **keine** Voraussetzung. Die Kalibrierung braucht nur (1) korrekte
> `/joint_states` mit echtem Armmodell und (2) die Möglichkeit, den Arm in Stellungen zu fahren —
> Teach-/Handbetrieb genügt. Das Konzept ist also **vor** dem `arm_action_server` umsetzbar.

---

## Stufe A — Voraussetzungen: Mechanik fixiert, Armmodell echt

**Ziel:** Die TF-Kette `base_link -> tool0` stimmt auf wenige Millimeter. Der Arm ist bei der
Hand-Auge-Kalibrierung das **Messgerät** — jeder Fehler im Armmodell wandert 1:1 ins Ergebnis.

**Vorgehen:**
1. **Mechanik final montieren:** Kameramast und Armsockel fest verschraubt (keine Klemm-Provisorien).
   Merksatz: *Nach jeder mechanischen Änderung an Mast oder Armsockel ist die Kalibrierung ungültig* (siehe Stufe H).
2. **Arm-URDF real machen:** Gliederlängen, Achsversätze, Nullstellungen und Drehrichtungen vom
   echten Arm übernehmen (Messschieber/Hersteller-CAD). Die Dummy-Werte in
   `mobile_manipulator_dummy.urdf.xacro` ersetzen (oder eigenes `arm.xacro` einbinden).
   Dabei auch `tool0 -> gripper_tcp` real vermessen (Baustein 3).
3. **`/joint_states` live:** Der Armtreiber publiziert die Gelenkwinkel; `robot_state_publisher`
   erzeugt daraus die TF-Kette. (Genau das, was `display_dummy.launch.py` mit den Slidern macht —
   nur mit echten Winkeln.)
4. **Prüfen:**
   - `ros2 run tf2_tools view_frames` — Kette `base_link -> ... -> tool0 -> gripper_tcp` vollständig?
   - **Zeigetest Arm allein:** TCP nacheinander auf 3–4 angezeichnete Punkte auf der Plattform
     fahren; TF-Position (`ros2 run tf2_ros tf2_echo base_link gripper_tcp`) gegen Handmaß vergleichen.

**Abnahme A:** Zeigetest-Abweichung **< ±3 mm** an allen Punkten; TF-Kette live in RViz.

---

## Stufe B — Intrinsik der OAK prüfen (nicht neu erfinden)

**Ziel:** Bestätigen, dass die Werkskalibrierung der OAK (Intrinsik + Verzeichnung, bei der
Wide-Optik wichtig!) für unsere Auflösung stimmt.

**Hintergrund:** OAK-Kameras tragen ihre Kalibrierung ab Werk im Gerät; `depthai-ros` publiziert
sie als `camera_info` passend zur eingestellten Auflösung. Die Wide-FF-Variante hat Fixfokus —
gut für uns: Der Fokus (und damit die Intrinsik) verstellt sich nicht.

**Vorgehen:**
1. depthai-ros-Treiber starten; Topics prüfen: `/oak/rgb/image_raw` + `/oak/rgb/camera_info`.
   **Betriebsauflösung jetzt festlegen** und für Kalibrierung UND Betrieb dieselbe verwenden
   (Auflösungswechsel = andere `camera_info` — dokumentieren!).
2. **Reprojektionstest:** ChArUco-Board (aus Stufe C) vor die Kamera halten, mit OpenCV
   (`cv2.aruco` + `solvePnP`) die Ecken reprojizieren.
3. **Tiefen-Schnelltest** (falls Stereo-Tiefe später fürs Greifen genutzt wird): ebene Wand /
   Board bei gemessenen 0,50 m und 1,00 m — Anzeige gegen Maßband.

**Abnahme B:** Reprojektionsfehler **< 1 px** in Bildmitte, **< 2 px** am Rand (Weitwinkel);
Tiefenfehler **< 2 %** der Distanz. Nur wenn das scheitert: Neukalibrierung mit dem Luxonis-Tool
(Ausnahmefall, im Protokoll begründen).

---

## Stufe C — Kalibrierboard bauen und am Greifer montieren

**Ziel:** Ein starres, präzise bekanntes Ziel, das die Kamera aus jeder Lage eindeutig vermessen kann.

**Warum ein ChArUco-Board (und kein einzelner Marker):** Ein einzelner flacher Marker (AprilTag/
ArUco) hat bei ungünstigem Blickwinkel eine **Pose-Mehrdeutigkeit** (zwei fast gleich gute
Lösungen — die Pose „springt"). Ein ChArUco-Board (Schachbrett + Marker) liefert viele Ecken und
eine stabile, eindeutige Pose.

**Vorgehen:**
1. **Board:** A4, z. B. 7x5 Felder, Feldgröße 30 mm, ArUco-Wörterbuch `DICT_5X5_250`
   (Parameter im Sammel-Skript hinterlegt). Matt drucken (kein Glanzpapier).
2. **Plan drucken, Maß prüfen:** Drucker skalieren gern. Tatsächliche Feldgröße mit dem
   Messschieber messen (über 5 Felder messen, durch 5 teilen) und **den gemessenen Wert** im
   Skript eintragen. `[ANPASSEN: gemessene Feldgroesse]`
3. **Steife Unterlage:** Board vollflächig auf 3-mm-Alu-Dibond oder eine plan gedruckte Platte
   kleben (Bambu-Drucker vorhanden). Wellen/Beulen im Papier = Millimeterfehler.
4. **Halterung am FLANSCH, nicht an den Fingern:** 3D-gedruckter Winkel, der am `tool0`-Flansch
   (oder Greifergrundkörper) verschraubt/verstiftet wird. Die Finger haben Spiel — Board dort zu
   befestigen ruiniert die Messung. Ausrichtung: Board zeigt „aus dem Greifer heraus", sodass es
   in typischen Armstellungen zur Kamera schaut.
5. **Nicht vermessen müssen:** Die Transformation Flansch->Board ist die zweite Unbekannte der
   Gleichung und **fällt aus der Lösung mit heraus**. Halterung trotzdem fotografieren/dokumentieren
   (für spätere Wiederholung).

**Abnahme C:** Board wackelfrei am Flansch (von Hand: kein fühlbares Spiel); Feldmaß gemessen
und notiert.

---

## Stufe D — Messpaare sammeln (der handwerkliche Kern)

**Ziel:** 15–25 saubere Paare aus (Armpose, Boardpose) über den relevanten Arbeitsraum.

**Was ein „Paar" ist:** Bei stehendem Arm gleichzeitig
- `T(base_link -> tool0)` aus TF (kommt aus `/joint_states` + URDF), und
- `T(camera -> board)` aus dem Kamerabild (ChArUco-PnP mit `camera_info`)
festhalten und wegspeichern (YAML/JSON, eine Datei pro Lauf).

**Die Regeln, die über die Qualität entscheiden:**
1. **Vielfalt:** Posen über den ganzen später relevanten Greifraum verteilen
   (Abstand Kamera–Board ca. **0,4–0,9 m** — dort, wo später gegriffen wird). Board-Orientierung
   um mindestens **±30° um zwei verschiedene Achsen** variieren. Keine zwei Posen „fast gleich" —
   sonst ist das Gleichungssystem schlecht konditioniert und die Lösung driftet.
2. **Backlash beherrschen:** Jede Pose aus **derselben Richtung** anfahren (Getriebespiel),
   dann **2 s Stillstand** vor der Aufnahme.
3. **Mitteln:** Pro Pose 5–10 Kamera-Frames erkennen und die Boardpose mitteln.
4. **Basis steht:** Räder blockieren. Alles spielt sich in `base_link` ab — SLAM/Karte sind egal,
   aber die Basis darf während des gesamten Laufs keinen Millimeter rollen.
5. **Licht:** gleichmäßig, keine Spiegelungen auf dem Board, keine Bewegungsunschärfe.

**Werkzeug (zwei Varianten):**
- **Variante 1 — sofort machbar (im Workspace bereits umgesetzt):** Paket
  `handeye_calibration`, Node `handeye_recorder`
  (`ros2 launch handeye_calibration handeye_recorder.launch.py`): Kontrollbild mit
  Board-Erkennung auf `/handeye/debug_image`, ENTER = Paar aufnehmen (mittelt 8 Frames,
  prüft Stillstand von Board und Arm-TF), warnt bei zu ähnlichen Posen, speichert
  absturzsicher als YAML. Der Arm wird von Hand / per Teach gefahren — **kein MoveIt nötig.**
- **Variante 2 — später mit MoveIt:** `easy_handeye2` (ROS-2-Port von easy_handeye) bietet
  GUI, Posenverwaltung und Löser in einem und kann Posen automatisch abfahren.

**Abnahme D:** ≥ 15 gültige Paare; Protokoll zeigt Spannweite der Orientierungen (≥ 30° um zwei
Achsen) und Abstände (nah bis fern).

---

## Stufe E — Lösung rechnen

**Ziel:** Aus den Paaren die feste Transformation `T(base_link -> camera_rgb_optical_frame)` bestimmen.

**Vorgehen** (im Workspace umgesetzt als `handeye_solve <messpaare.yaml>` im Paket
`handeye_calibration` — läuft auch ohne ROS, z. B. am PC):
1. **Löser:** OpenCV bringt beides mit:
   - `cv2.calibrateRobotWorldHandEye(...)` — löst die Zwei-Unbekannten-Form direkt
     (Kameramontage **und** Flansch->Board fallen gemeinsam heraus), oder
   - `cv2.calibrateHandEye(...)` — Klassiker für Eye-in-Hand; für **Eye-to-Hand** füttert man
     ihn mit den **invertierten** Armposen (`T(tool0 -> base_link)` statt `T(base_link -> tool0)`),
     dann ist das Ergebnis `T(camera -> base_link)`.
   `easy_handeye2` (Variante 2) macht intern genau das.
2. **Ausreißer filtern:** Residuum je Paar ansehen; Paare > 3 Standardabweichungen entfernen,
   neu lösen (typisch: eine verwackelte Aufnahme).
3. **Plausibilität mit dem Zollstock:** Das Ergebnis muss grob zur Realität passen
   (Kamera ca. 0,1–0,2 m vor und 0,3–0,4 m über `base_link`, leicht geneigt). Liegt das Ergebnis
   „völlig quer", ist fast immer der optische gegen den mechanischen Frame verwechselt
   (z-nach-vorn vs. x-nach-vorn) — dann Stufe-F-Umrechnung prüfen, nicht neu messen.

**Abnahme E:** Residuen der Lösung: Rotation **< 0,5°**, Translation **< 3–5 mm** (RMS über alle
Paare); Ergebnis + Residuen + Posenzahl im Protokoll.

---

## Stufe F — Ergebnis einpflegen: die URDF ist die einzige Quelle

**Ziel:** Das Kalibrierergebnis landet genau an **einer** Stelle, aus der alle Nodes ihre TF beziehen.

**Vorgehen:**
1. **Umrechnen auf den Kamera-Joint:** Kalibriert wurde `base_link -> camera_rgb_optical_frame`.
   In der URDF ist die Kette `base_link -> camera_link -> camera_rgb_optical_frame`, wobei der
   letzte Schritt die feste optische Drehung ist. Also:
   `T(base->camera_link) = T(base->optical) * T(camera_link->optical)^-1` (kleines Python-Skript,
   Teil des Kalibrierlaufs — `handeye_solve` druckt die fertigen Werte).
2. **URDF erweitern:** Der Kamera-Joint hat heute nur `oak_yaw`. Auf sechs Werte erweitern:
   `oak_x, oak_y, oak_z, oak_roll, oak_pitch, oak_yaw` — und die Marker von `[ANPASSEN]` auf
   `[KALIBRIERT <Datum>]` ändern, damit niemand die Werte „aufräumt".
3. **Keine Parallelquellen:** Keine zusätzlichen `static_transform_publisher` für dieselben Frames
   (Prüfbericht-Befund I7 gilt hier genauso wie bei den VL53-Sensoren): **URDF = einzige Quelle.**
4. **Kalibrierdatei archivieren:** Ergebnis zusätzlich als YAML unter `docs/kalibrierung/`
   (Datum, Auflösung, Posenzahl, Residuen, Board-Feldmaß) — Nachvollziehbarkeit bei Drift.

**Abnahme F:** RViz zeigt die kalibrierte Kamerapose im TF-Baum; `semantic_perception` läuft
unverändert (der Frame-Name bleibt `camera_rgb_optical_frame`).

---

## Stufe G — Ende-zu-Ende validieren

**Ziel:** Beweisen, dass die gesamte Kette Kamera -> TF -> Arm im Greifraum stimmt — nicht nur
die Rechnung.

**Vorgehen:**
1. **G1 Zeigetest (der ehrlichste Test):** Das Board (jetzt NICHT am Arm, sondern frei im
   Arbeitsraum liegend) von der Kamera vermessen lassen, Pose nach `base_link` transformieren,
   den TCP auf eine markierte Board-Ecke fahren. Abweichung messen.
2. **G2 Fehlerkarte:** G1 an 5 Positionen wiederholen (links/rechts/nah/fern/hoch).
   Zufällige Abweichungen = Rauschen (ok); **systematische Richtung** = Restfehler im Armmodell
   (zurück zu Stufe A2) oder in der Kalibrierung.
3. **G3 Greiftest:** Referenzobjekt (Tasse) an bekannte Position, komplette Kette bis zum Griff —
   sobald der Arm-Server existiert über `ComputeGrasp`/`MoveArmToPose`, bis dahin manuell
   kommandiert. Greiferöffnung 80 mm auf ~70-mm-Objekt toleriert etwa ±5 mm Querfehler.

**Abnahme G:** G1 **< 5 mm** an allen 5 Punkten. Wird das knapp verfehlt: dokumentieren und die
Fein-Detektion am Zielort (`DetectObjectFine` in `base_link`, Abschnitt 1) als **Pflichtschritt**
vor jedem Griff festschreiben — genau dafür ist sie im BT vorgesehen.

---

## Stufe H — Absicherung und Wartung

- **Re-Kalibrier-Trigger** (Liste ins Wartungs-README): Sturz/Transport, Arbeiten an Mast oder
  Armsockel, Armtausch, extreme Temperaturwechsel, Prüfroutine > 8 mm.
- **5-Minuten-Prüfroutine `calib_check`:** eine feste Board-Halterung an der Plattform
  (angeschraubt, Position einmalig eingemessen). Skript: Kamera misst das Board, vergleicht mit
  Soll, loggt die Abweichung. Vor Demos / monatlich ausführen — erkennt Drift, bevor Griffe
  danebengehen.
- **Protokolle:** jeder Kalibrierlauf als YAML in `docs/kalibrierung/` (siehe F4).

---

## Fehlerbudget — womit realistisch zu rechnen ist

| Fehlerquelle | typischer Beitrag | Gegenmaßnahme |
|---|---|---|
| Intrinsik (Werkskalibrierung) | ~0,5–1 px | Stufe B prüfen; Auflösung nie stillschweigend wechseln |
| Board-Druckmaß | ±0,2 mm | Feldgröße nachmessen (C2) |
| Board-Posenmessung (PnP) | 0,5–2 mm (steigt mit Abstand) | großes Board, nah messen, Frames mitteln |
| Hand-Auge-Lösung | 2–5 mm | Posenvielfalt, Ausreißerfilter (D/E) |
| Arm-Kinematik (URDF-Maße) | 1–5 mm | Stufe A ernst nehmen; G2-Fehlerkarte |
| Arm-Wiederholgenauigkeit | 1–3 mm (klassenabhängig) | gleiche Anfahrrichtung, Stillstand |
| OAK-Stereotiefe (falls genutzt) | 1–2 % der Distanz | nah greifen; Fein-Detektion am Zielort |

**Summe realistisch: ~5–10 mm** — das passt zur Greifertoleranz (±5 mm bei 80/70 mm), aber ohne
Reserve. Konsequenz: Die Fein-Detektion nahe am Objekt (kurzer Kameraabstand, Pose in `base_link`)
bleibt fester Bestandteil des Griffablaufs; die Kalibrierung macht sie treffsicher, ersetzt sie
aber nicht.

---

## Typische Fallstricke (Kurzliste zum Abhaken)

- Einzelmarker statt Board -> Pose-Mehrdeutigkeit bei flachem Blickwinkel.
- Optischer und mechanischer Kamera-Frame verwechselt -> Ergebnis liegt „auf der Seite" (Stufe F1 prüfen, nicht neu messen).
- Auflösung nach der Kalibrierung geändert, alte `camera_info` weiterverwendet.
- Alle Posen mit ähnlicher Board-Orientierung -> Lösung schlecht konditioniert.
- Board an den Greiffingern statt am Flansch -> Fingerspiel geht voll ins Ergebnis.
- Basis rollt minimal während des Laufs -> Bremse/Keile.
- Papier-Board wellt sich -> auf steife Platte kleben.

---

## Einordnung ins Projekt

- **Machbar vor MoveIt/arm_action_server:** Stufen A–G brauchen nur echte `/joint_states` +
  Handverfahren des Arms. Die Kalibrierung ist damit ein sinnvoller **erster Schritt der
  Arm-Integration**, nicht ihr Abschluss.
- **Direkter Nutzen:** Die `[ANPASSEN]`-Kamerawerte der URDF werden `[KALIBRIERT]`;
  `semantic_perception` (WP-5 B) bekommt eine belastbare TF-Grundlage für die 3D-Projektion;
  die Prüfbericht-Empfehlung „Greifen in `base_link`, Fein-Detektion am Zielort" (K2/S7) wird
  damit erst umsetzbar.
- **Aufwand grob:** A: 0,5–1 Tag (Vermessung Arm) · B: ~1 h · C: 2–3 h (Druck + Halter) ·
  D: 1–2 h · E+F: ~1 h · G: 1–2 h. Reine Wiederholung (nach Umbau): unter 2 h.

---

*Dieses Konzept ist bewusst werkzeugoffen: Sammel-Skript + OpenCV genügen vollständig; easy_handeye2
ist die Komfortvariante, sobald MoveIt läuft. Alle Toleranzangaben sind Zielwerte für die Abnahme
der jeweiligen Stufe und im Protokoll zu dokumentieren.*
