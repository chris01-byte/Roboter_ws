# Integrationsplan: ESS17-RS Roboterarm in die Roboterplattform

**Status:** Plan, noch keine Arm-Hardwarebewegung durch diese Integration

**Zielsystem:** ROS 2 Humble auf Jetson / Ubuntu 22.04

**Gueltigkeit:** Dieser Plan integriert den sechsachsigen ESS17-RS-Arm softwareseitig in `Roboter_ws`. Er baut auf den bestehenden Plattformvertraegen, dem vorhandenen Hand-Auge-Kalibrierpaket und den vorhandenen BT-Actions auf.

---

## 1. Ziel und Scope

### Ziel

Der Roboterarm soll als eigenstaendiger, diagnosefaehiger und sicher gekapselter Plattformbaustein arbeiten. Die oeffentliche Schnittstelle fuer Missionen bleibt klein:

- `/move_arm_to_named` fuer die benannten Posen `stowed`, `ready` und spaeter weitere freigegebene Posen.
- `/move_arm_to_pose` fuer kartesische TCP-Ziele.
- `/gripper_controller/gripper_cmd` fuer den Greifer.
- `/joint_states`, TF und Armstatus fuer Visualisierung, Kalibrierung und Diagnose.

Der vorhandene Behavior Tree verwendet diese Vertrage bereits. Die Integration ersetzt daher keine Missionsschnittstelle, sondern implementiert sie belastbar.

### Im Scope

- Sechs ESS17-RS-Antriebe ueber isoliertes RS485 / Modbus RTU.
- Encoder- und Drehrichtungs-Inbetriebnahme pro Achse.
- Homing, Softlimits, Zustandsautomat, Busfehlerbehandlung und zentraler Software-Not-Aus.
- `ros2_control`, MoveIt 2, Action-Server, URDF/SRDF und BT-Interlocks.
- Eye-to-Hand-Kalibrierung mit der fest montierten OAK-D-S2.
- Tests mit Fake-Modbus vor jeder realen Bewegung.

### Nicht im Scope

- Mechanische Konstruktion, Last-/Kippberechnung, Bremsauslegung oder Veraenderung der hardwired Sicherheitskette.
- Unkontrolliertes Uebernehmen der alten Foxy-Bridge oder des lokalen Prototyp-Controllers.
- Automatische Mehrachsbewegung vor abgeschlossener Achs-Inbetriebnahme.

Die hardwired Not-Aus-Kette bleibt die primaere Sicherheitsinstanz. Dieser Plan integriert ihren Softwarezustand in die Armsteuerung.

---

## 2. Verbindliche Ausgangsfakten

| Bereich | Verbindlicher Stand |
|---|---|
| Plattform | ROS 2 Humble, bestehender Workspace `Roboter_ws` |
| Arm | 6x ESS17-RS, gemeinsame RS485/Modbus-RTU-Leitung, Adressen 1 bis 6 im Prototyp |
| Bestehende Plattform-Actions | `MoveArmToNamed.action` und `MoveArmToPose.action` im Paket `robot_interfaces` |
| Bestehender BT | erwartet `stowed` vor Basisfahrt und `ready` vor Manipulation |
| Software-Not-Aus | `/safety/estop` (`std_msgs/Bool`), `true` bedeutet aktiv / Bewegung verboten |
| Kamera | aktuell OAK-D-S2, Treiberframe im Betrieb `oak_rgb_camera_optical_frame` |
| Kalibrierung | Paket `handeye_calibration` mit Recorder und Offline-Loeser vorhanden |
| Alter Armcode | lokale Foxy-Bruecke, direkte `JointState`-Commands, unvollstaendige/teilweise korrupte Controller-Schicht; nur Referenz, keine Produktionsbasis |

### ESS17-Regel

Die fuer die Fahrbasis bestaetigte ESS23-Semantik darf nicht ungeprueft auf die ESS17-Achsen uebertragen werden. Vor produktiver Steuerung werden fuer jede Achse Messwerte dokumentiert:

- korrekte Modbus-Adresse und FC03-Lesbarkeit,
- Register- und 32-Bit-Wortreihenfolge,
- signed/unsigned Dekodierung von Position und Geschwindigkeit,
- Drehrichtung bei kleinem Jog,
- Referenzfahrtmodus und Homing-Richtung,
- physische Softlimits und Encoder-Nullpunkt.

---

## 3. Zielarchitektur

```text
6x ESS17-RS
    |
RS485 / Modbus RTU
    |
arm_hardware (ros2_control SystemInterface)
    |-- atomare Registerreads, Word-Order, signed decoding
    |-- per-axis limits, watchdog, fault handling
    |-- /safety/estop subscriber
    |
controller_manager
    |-- joint_state_broadcaster
    `-- joint_trajectory_controller
            |
        arm_action_server
            |-- /move_arm_to_named
            `-- /move_arm_to_pose
                    |
                 MoveIt 2
                    |
URDF/SRDF <--------- calibrated camera transform -------- handeye_calibration
    |
robot_state_publisher --> TF: base_link -> tool0 -> gripper_tcp
```

### Paketaufteilung

| Paket | Verantwortung | Nicht verantwortlich fuer |
|---|---|---|
| `arm_hardware` | Modbus-Rohzugriff, Encoderwerte, Kommandos, Stop, Diagnose | IK, MoveIt-Planung, BT-Logik |
| `arm_bringup` | Hardware-/Controller-YAML, Udev, Launch, Lifecycle | direkte Bewegungslogik |
| `robot_description` | echtes Xacro/URDF, Gelenkachse, Limits, TCP | zweiter Kamera-TF-Publisher |
| `robot_moveit_config` | SRDF, Planning Group, Collision Matrix, Named Poses | direkte Modbus-Register |
| `arm_action_server` | Actions, Preflight, MoveIt-Ausfuehrung, Result/Feedback | Bus-Protokolldetails |
| `arm_tools` | Read-only Probe, Einachs-Commissioning, Kalibrierhilfen | produktive Missionssteuerung |
| `handeye_calibration` | Messpaare, Loeser, Kalibrierprotokoll | Kamera-TF parallel publizieren |

### Nicht wiederverwenden

Die lokale Foxy-Bruecke veroeffentlicht direkte `JointState`-Kommandos und bindet Host-Code per `sys.path` ein. Sie wird nicht in den Humble-Workspace kopiert. Der lokale `robot_controller.py` ist nicht die Integrationsbasis, da er gemischte/defekte Quellteile enthaelt. Wiederverwendbar sind ausschliesslich verifizierte Fakten aus dessen Konfiguration und klar testbare Einzelalgorithmen.

---

## 4. Kanonische Daten und Koordinaten

### 4.1 Eine Konfiguration pro Gelenk

`arm_bringup/config/arm_hardware.yaml` wird die alleinige Quelle fuer hardwareabhaengige Fakten. Pro Gelenk werden mindestens gespeichert:

```yaml
joints:
  - name: joint1
    modbus_address: 1
    gear_ratio: 50.0
    encoder_word_order: high_low       # erst nach M1 bestaetigen
    direction_sign: 1                  # erst nach M1 bestaetigen
    encoder_zero_pulses: 0             # erst nach Homing setzen
    soft_limit_lower_rad: -2.61799
    soft_limit_upper_rad: 2.61799
    homing_mode: null                  # erst nach M1 bestaetigen
    homing_direction_sign: null        # erst nach M1 bestaetigen
```

Keine Konfigurationsdatei darf einen geratenen Wert als gemessen kennzeichnen. Unbestaetigte Felder bleiben `null` oder tragen klar `TODO`.

### 4.2 Vorzeichen symmetrisch behandeln

Fuer jedes Gelenk gilt nach Homing:

```text
q_ros = direction_sign * (encoder_pulses - encoder_zero_pulses) / pulses_per_rad
encoder_target_pulses = encoder_zero_pulses + direction_sign * q_ros_target * pulses_per_rad
joint_velocity_ros = direction_sign * motor_speed / gear_ratio
```

`direction_sign` wird somit beim Lesen und beim Schreiben angewandt. Eine Invertierung nur auf dem Befehlsweg oder nur in `/joint_states` ist verboten.

### 4.3 Frame-Vertrag

- `base_link -> tool0 -> gripper_tcp` entsteht nur durch URDF plus `/joint_states` und `robot_state_publisher`.
- Der Greifpfad benutzt Posen in `base_link`, nicht in `map`.
- Die reale OAK verwendet ihren vom Treiber publizierten optischen Frame. Der Name wird vor M7 verbindlich festgelegt; aktuell ist dies `oak_rgb_camera_optical_frame`.
- Die kalibrierte Kameramontage darf genau einen TF-Eigentuemer haben. URDF und OAK-Launch lesen dieselbe versionierte Kalibrierdatei oder es wird nur eine der beiden Quellen aktiviert.

---

## 5. Gemeinsamer Zustandsautomat

Der Arm publiziert einen strukturierten `ArmStatus`. Vorgeschlagene Zustaende:

```text
DISCONNECTED -> DISCOVERING -> DISABLED -> UNHOMED -> HOMING -> READY_STOWED
READY_STOWED -> READY_DEPLOYED -> EXECUTING -> READY_DEPLOYED
* -> FAULT
* -> ESTOPPED
```

### Zulassungsregeln

| Aktion | Vorbedingung | Bei Fehler |
|---|---|---|
| Arm aktivieren | Bus erreichbar, kein Alarm, E-Stop frei | `FAULT` oder `ESTOPPED` |
| Homing | `UNHOMED`, reduzierte Geschwindigkeiten, Bedienfreigabe | `FAULT`; kein automatischer Retry |
| Named Pose | `READY_STOWED` oder `READY_DEPLOYED`, kein E-Stop | Action fehlgeschlagen, Stop gesendet |
| TCP Pose | `READY_DEPLOYED`, validierte Planung, Basis still | Action fehlgeschlagen, keine Fahrt |
| Basisfahrt | Armstatus `READY_STOWED` | Basis-Missionsgate lehnt ab |
| E-Stop | jederzeit | alle Achsen stoppen, Controller deaktivieren, Rehoming erforderlich |

`ArmStatus` muss mindestens Zustand, `homed`, `estop_active`, `bus_healthy`, je Achse Alarmcode, letzte Fehlerursache und Zeitstempel enthalten.

---

## 6. Meilensteine und Anleitung

## M0 - Integrationsvertrag und Testgeruest

**Ziel:** Die Paketgrenzen, Benennungen und Tests existieren, ohne Hardware anzusteuern.

**Arbeitsschritte:**

1. Neue Pakete `arm_hardware`, `arm_bringup`, `arm_action_server` und `arm_tools` anlegen.
2. `ArmStatus.msg` im Paket `robot_interfaces` definieren.
3. Benannte Posen und Action-Namen als Vertrage festschreiben.
4. Fake-Modbus-Transport mit aufzeichnbaren Reads/Writes bereitstellen.
5. Keine reale Serienport-Defaultverbindung. Hardwarebetrieb verlangt einen expliziten Launch-Parameter.

**Abnahme:**

- `colcon build --packages-select robot_interfaces arm_hardware arm_bringup arm_action_server` funktioniert.
- Unit-Tests pruefen Actions, Konfigurationsvalidierung und Fake-Modbus.
- Kein Test oeffnet einen realen `/dev/ttyUSB*`-Port.

**Rueckfall:** Pakete bleiben inaktiv; der bestehende Roboterbetrieb bleibt unveraendert.

---

## M1 - ESS17-RS Commissioning je Achse

**Ziel:** Alle Motor-/Encoderannahmen werden gemessen statt geraten.

**Arbeitsschritte:**

1. `ros2 run arm_tools arm_bus_probe --read-only` implementieren.
2. Busantwort, FC03, Alarm, Bewegungsstatus, Istposition und Geschwindigkeit fuer Adressen 1 bis 6 erfassen.
3. Register `0x0019` und die tatsaechliche 32-Bit-Wortreihenfolge nur nach ESS17-Handbuch und Beobachtung festlegen.
4. Mit mechanisch freiem und beobachtetem Arm pro Achse einen kleinen Jog mit reduzierter Geschwindigkeit ausfuehren.
5. Physische Bewegungsrichtung und Encoder-Vorzeichen protokollieren.
6. `direction_sign`, Homing-Richtung, Getriebe und sichere Testschritte in die Hardware-YAML eintragen.

**Pflichtprotokoll pro Achse:**

| Feld | Wert |
|---|---|
| Joint / Modbus-Adresse | gemessen |
| FC03-Antwort | ja/nein |
| Position word order | bestaetigt |
| aktuelle Geschwindigkeit signed | bestaetigt |
| positiver Jog bewegt physisch | dokumentiert |
| `direction_sign` | +1 oder -1 |
| Homing-Sensor / Mode / Richtung | bestaetigt |
| sicherer Bereich | gemessen |

**Abnahme:**

- Sechs vollstaendige Achsprotokolle.
- Positiver ROS-Gelenkwinkel erhoeht nach der Konfigurationsabbildung die `/joint_states`-Position.
- Kein EEPROM-Schreiben, kein `clear_position` und keine Mehrachsbewegung in diesem Meilenstein.

**Stop-Kriterium:** Unklare Wortreihenfolge, unbestaetigtes Homing oder widerspruechliche Encoderwerte blockieren M2.

---

## M2 - Deterministischer Modbus-/Encoder-Kern

**Ziel:** Der Treiber ist testbar und behandelt ESS17-Varianten explizit.

**Arbeitsschritte:**

1. Modbus-Zugriff kapseln: FC03, retries, Zeitbudget, Bus-Lock und Fehlerklassifikation.
2. 32-Bit Lese-/Schreibfunktionen mit konfigurierbarer Wortreihenfolge implementieren.
3. Signed-16 und signed-32 Dekodierung zentralisieren.
4. Positions-, Geschwindigkeits- und Alarm-Read je Achse in konsistente Zustandswerte ueberfuehren.
5. Kommandofolge fuer Position, Geschwindigkeit, Normalstop und Sofortstop gegen Handbuch und M1-Protokoll implementieren.
6. Beim Timeout alle neuen Kommandos sperren und den Zustand `FAULT` melden.

**Abnahme:**

- Unit-Tests decken high/low, low/high, negative Positionen und negative Geschwindigkeit ab.
- Fake-Modbus-Test prueft, dass Zielregister vor Startregister geschrieben werden.
- Busfehler stoppt die Ausfuehrung deterministisch und erzeugt keine Retry-Schleife mit Bewegungsbefehlen.

---

## M3 - ros2_control und Hardware-Status

**Ziel:** Der Arm ist ein normaler ROS-2-Control-Roboter, nicht ein Topic-gesteuertes Spezialgeraet.

**Arbeitsschritte:**

1. `arm_hardware` als `hardware_interface::SystemInterface` implementieren.
2. Pro Gelenk State Interfaces `position`, `velocity` sowie Command Interface `position` bereitstellen.
3. `joint_state_broadcaster` und `joint_trajectory_controller` in `arm_bringup` konfigurieren.
4. `/safety/estop` abonnieren; `true` unterdrueckt neue Kommandos und loest den definierten Stop-Pfad aus.
5. `ArmStatus` und Diagnosen mit fester Aktualisierungsrate publizieren.
6. Erst im Fake-Transport, danach im Hardware-Read-only-Modus starten.

**Abnahme:**

- Controller laden mit Fake-Hardware.
- `/joint_states` enthaelt exakt die sechs kanonischen Gelenknamen in rad.
- E-Stop-Test: Zieltrajektorie wird abgebrochen; anschliessende Ziele werden abgelehnt.
- Busverlust-Test: Controller meldet `FAULT`, kein stillschweigendes Wiederanfahren.

---

## M4 - Echtes Armmodell, Homing und TF

**Ziel:** `base_link -> tool0` ist geometrisch und kinematisch belastbar.

**Arbeitsschritte:**

1. Dummy-Masse im `robot_description` durch gemessene Gliederlaengen, Achsversetze, Joint-Achsen und Grenzen ersetzen.
2. Echte ROS-Gelenknamen in URDF, Hardware-YAML, Controller und SRDF vereinheitlichen.
3. `tool0 -> gripper_tcp` vermessen und im Xacro eintragen.
4. Referenzfahrt als bedienerbewussten Ablauf implementieren; Home-Offsets versioniert speichern.
5. Nach Homing den Arm auf langsame benannte Pruefposen fahren.
6. TF mit RViz und mechanischem Zeigetest pruefen.

**Abnahme:**

- Vollstaendige TF-Kette `base_link -> ... -> tool0 -> gripper_tcp`.
- Zeigetest an mindestens vier Punkten: Abweichung kleiner oder gleich 3 mm.
- Jede Richtung, jeder Nullpunkt und jedes Softlimit ist durch Test abgenommen.

**Stop-Kriterium:** Ein systematischer Zeigefehler ist ein Modell-/Encoderproblem, keine Aufgabe fuer die Kamerakalibrierung.

---

## M5 - MoveIt 2 und Arm-Actions

**Ziel:** Die bestehenden Plattform-Actions steuern den Arm ueber Planung und kontrollierte Ausfuehrung.

**Arbeitsschritte:**

1. `robot_moveit_config` mit Planning Group `arm`, TCP `gripper_tcp`, Joint Limits und Self-Collision-Matrix erstellen.
2. Named Poses mindestens `stowed`, `ready` und `pregrasp` definieren.
3. `arm_action_server` implementieren:
   - `MoveArmToNamed`: Pose pruefen, planen/ausfuehren, Fortschritt publizieren.
   - `MoveArmToPose`: `PoseStamped` zuerst nach `base_link` transformieren, Plausibilitaet und Erreichbarkeit pruefen, planen/ausfuehren.
4. Cancel, Timeout, E-Stop und Controllerfehler als eindeutige Action-Resultate behandeln.
5. Den Greifer erst nach einem eigenen Controller-/Schnittstellenvertrag anbinden.

**Abnahme:**

- `MoveArmToNamed(stowed)` und `MoveArmToNamed(ready)` funktionieren bei Fake- und realem Arm.
- Unerreichbare Posen, unbekannte Named Poses, E-Stop und Cancel liefern `success=false` mit erklaerender Meldung.
- Keine kartesische Zielpose wird direkt als Motorpuls an den Treiber gegeben.

---

## M6 - Basis-Arm-Interlocks

**Ziel:** Mobilitaet und Manipulation koennen sich nicht in einen ungueltigen Betriebszustand bringen.

**Arbeitsschritte:**

1. `arm_action_server` akzeptiert Bewegungen nur bei stillstehender Basis; Stillstand aus einer verbindlichen Basisgeschwindigkeit oder einem zentralen Betriebsstatus bestimmen.
2. Das vorhandene Missions-/Fahrgate akzeptiert Basisfahrt nur bei `READY_STOWED`.
3. Der BT bleibt wie heute strukturiert: vor Navigation `stowed`, vor Greifen `ready`.
4. Bei Armfehler waehrend einer Mission wird die laufende Manipulationsaction fehlgeschlagen und der BT kann keinen neuen Fahrbefehl ohne `stowed` ausgeben.

**Abnahme:**

- Negativtest 1: Basisgeschwindigkeit ungleich null -> Armgoal abgelehnt.
- Negativtest 2: Arm `READY_DEPLOYED` -> Navigationsfreigabe abgelehnt.
- Negativtest 3: E-Stop mitten in der Action -> BT-Action endet fehlgeschlagen, Status `ESTOPPED`.

---

## M7 - OAK-Hand-Auge-Kalibrierung

**Ziel:** Eine Objektpose aus der OAK wird verlässlich als Greifpose in `base_link` nutzbar.

**Vorbedingungen:** M1 bis M4 sind abgenommen. Der Arm darf nicht als Messgeraet dienen, solange Encoder, Modell oder TCP unklar sind.

**Arbeitsschritte:**

1. Recorderparameter auf den realen OAK-Frame und die realen RGB/CameraInfo-Topics ausrichten.
2. OAK-Aufloesung und Fokusverhalten fuer Kalibrierung und Betrieb festlegen; die aktuell verbaute OAK-D-S2 ist kein impliziter Fixfokus-Fall.
3. ChArUco-Board steif an `tool0` oder Greifergrundkoerper befestigen, Feldmass messen.
4. 15 bis 25 Posen ueber den relevanten Arbeitsraum sammeln; Board mindestens 30 Grad um zwei Achsen variieren.
5. Fuer jeden Frame die TF zum Bildzeitstempel lesen, nicht nur den neuesten TF.
6. Loesung, Ausreisser, Residuen, Aufloesung, Fokusmodus und Boardmass als YAML unter `docs/kalibrierung/` archivieren.
7. Genau eine Kamera-TF-Quelle aktivieren.

**Abnahme:**

- Hand-Auge-Residuen: Translation RMS <= 5 mm und Rotation RMS <= 0.5 Grad.
- Zeigetest mit freiem Board an fuenf Positionen: Fehler <= 5 mm.
- `semantic_perception` verarbeitet fuer den Greifpfad eine Zielpose in `base_link`; `map` wird nicht als Feinmanipulationsframe verwendet.

---

## M8 - Ende-zu-Ende Pick-and-Place

**Ziel:** Der bestehende Behavior Tree arbeitet gegen reale, abgesicherte Armservices.

**Arbeitsschritte:**

1. BT-Pfad zunaechst mit Actions im Fake-Modus ausfuehren.
2. Greifercontroller einbinden und `GripperCommand` separat pruefen.
3. `DetectObjectFine -> ComputeGrasp -> pregrasp -> grasp -> retreat` zunaechst mit einem Referenzobjekt testen.
4. Vor jeder Basisbewegung `stowed`; vor Greifen `ready` erzwingen.
5. Fehlerszenarien gezielt pruefen: Objekt weg, IK nicht loesbar, Busfehler, E-Stop, Cancel, ungueltige Kamerapose.

**Abnahme:**

```text
stowed -> navigate -> ready -> detect fine -> pregrasp -> grasp -> retreat -> stowed
```

funktioniert reproduzierbar und jedes Fehlerszenario endet ohne neue Bewegungsfreigabe.

---

## 7. Testmatrix

| Testklasse | Mindesttests |
|---|---|
| Unit | Word-Order, signed decode, direction_sign, limits, state transitions |
| Fake-Modbus | Registerreihenfolge, Timeout, Alarm, Stop, Busverlust |
| ros2_control | Controller load, joint states, trajectory cancel, estop gate |
| TF/URDF | Gelenknamen, Kette, Achsrichtungen, TCP-Transform |
| MoveIt | Named pose, unreachability, collision, cancel, timeout |
| Integration | base-still gate, stowed-for-drive gate, BT failure propagation |
| Calibration | Reprojection, sample diversity, residuals, 5-point pointing test |
| Hardware | pro Achse einzeln, reduziert, beobachtet und protokolliert |

---

## 8. Empfohlene Pull-Request-Schnitte

| PR | Inhalt | Hardwarebewegung erlaubt? |
|---|---|---|
| PR 1 | M0: Paketgeruest, Interfaces, Fake-Modbus, Tests | nein |
| PR 2 | M1/M2: Commissioning-Tools und Modbus-Kern | nur expliziter Einachs-Test |
| PR 3 | M3: ros2_control, Armstatus, E-Stop-Gate | erst Fake, dann Read-only |
| PR 4 | M4: echtes Modell, Homing, TF, Zeigetest | langsame Named-Pruefposen |
| PR 5 | M5/M6: MoveIt, Actions, Basis-Arm-Interlocks | kontrollierte Armbewegungen |
| PR 6 | M7: Kalibrierung und kanonische Kamera-TF | Kalibrierposen |
| PR 7 | M8: realer BT-Pick-and-Place | nach allen Abnahmen |

Jeder PR enthaelt Unit-Tests, eine Aktualisierung der Konfigurationsdokumentation und ein explizites Abnahmekriterium. Kein PR versteckt eine neue reale Motorbewegung hinter einem Default.

---

## 9. Betriebsanleitung nach Integration

### Startreihenfolge

1. Hardwired Sicherheitskette und `/safety/estop` pruefen.
2. RS485-Geraet per Udev als `/dev/arm_rs485` pruefen.
3. `arm_bringup` im Diagnose-/Read-only-Modus starten.
4. `ArmStatus` pruefen: Bus gesund, kein Alarm, `UNHOMED`.
5. Referenzfahrt mit Bedienfreigabe und reduzierter Geschwindigkeit ausfuehren.
6. `READY_STOWED` pruefen.
7. Erst danach Controller, MoveIt und `arm_action_server` freigeben.
8. Vor einer mobilen Mission `stowed` pruefen; vor dem Griff Feinpose in `base_link` anfordern.

### Pflichtchecks vor dem ersten Betriebstag

```bash
ros2 topic echo /safety/estop --once
ros2 topic echo /arm/status --once
ros2 topic echo /joint_states --once
ros2 run tf2_ros tf2_echo base_link gripper_tcp
ros2 action send_goal /move_arm_to_named robot_interfaces/action/MoveArmToNamed "{target_name: stowed}"
```

Die konkreten Paket- und Topicnamen werden erst mit M0 im Workspace erzeugt; die Befehle sind daher Teil der geplanten Betriebsdokumentation und nicht als aktuelle Startanweisung zu verstehen.

---

## 10. Definition of Done

Die Armsoftware ist erst integriert, wenn alle folgenden Aussagen wahr sind:

- Alle sechs ESS17-Achsen haben ein bestaetigtes Commissioning-Protokoll.
- `direction_sign`, Wortreihenfolge, Getriebe, Homing und Softlimits sind versioniert.
- Der reale Arm publiziert korrekte `/joint_states` und TF.
- Der Zeigetest fuer `base_link -> gripper_tcp` erfuellt <= 3 mm.
- E-Stop, Cancel, Alarm und Busverlust stoppen und sperren die Armbewegung deterministisch.
- Basisfahrt ist nur bei `READY_STOWED`, Armfahrt nur bei stillstehender Basis moeglich.
- Beide bestehenden Arm-Actions liefern nachvollziehbare Ergebnisse und Feedbacks.
- Die OAK-Kalibrierung ist versioniert, hat genau eine TF-Quelle und besteht den 5-Punkt-Zeigetest.
- Der Pick-and-Place-BT besteht Erfolgs- und Fehlertests ohne direkte, ungekapselte Motorbefehle.

---

## 11. Erster auszufuehrender Schritt

Der erste Implementierungsschritt ist **M0 plus das Read-only-Teil von M1**: Paketgeruest, Fake-Modbus und ein `arm_bus_probe`, der niemals schreibt. Erst wenn die sechs Achsprotokolle vorliegen, wird entschieden, wie die konkreten ESS17-Register im Produktionsdriver abgebildet werden.
