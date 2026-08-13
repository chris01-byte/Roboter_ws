# Encoder-Odometrie für den ESS23-RS-Antrieb

**Stand:** 13.08.2026
**Branch:** `fix/encoder-position-odometry`
**Basis:** `c630bbc` (`origin/agent/slam-toolbox-pure-rotation-fix`)
**Status:** Softwareseitig umgesetzt; Hardware-Abnahme am realen Roboter offen

Dieses Dokument beschreibt die Ursache des festen Odometrieversatzes, die
softwareseitige Umstellung auf die Positionsrückmeldung der beiden
ESS23-RS-Antriebe und das verbindliche Abnahmeverfahren am Jetson. Vor Arbeiten
am Roboter zusätzlich `AGENTS.md`, `docs/PROJECT_MEMORY.md`,
`docs/INVENTORY.md` und `docs/ROBOT_TRANSFER.md` vollständig lesen.

> **Keine Fahrfreigabe:** Aus dieser Implementierung und aus bestandenen
> Offline-Tests folgt keine Erlaubnis, Motoren zu bestromen, freizugeben oder zu
> bewegen. Jede Hardwarephase beginnt erst nach ausdrücklicher Freigabe der
> anwesenden Person, mit erreichbarem Not-Aus und dem für die Phase beschriebenen
> mechanischen Sicherheitsaufbau.

---

## 1. Ergebnis in einem Satz

Der neue Odometriepfad integriert die tatsächlichen, kumulierten
Positionsänderungen der Motorencoder aus `0x000A/0x000B`, statt den Fahrweg aus
einzelnen Drehzahlwerten von `0x000C` über die Zeit zu summieren. Der bisherige
Drehzahlpfad bleibt als ausdrücklich wählbarer Rückfallmodus erhalten.

Die Software ist implementiert und offline prüfbar. Die reale Positionseinheit,
Vorzeichen, Wirkung bei manueller Drehung und Verbesserung des festen
Start-/Stoppfehlers sind am konkreten Motorpaar **noch nicht bestätigt**.

---

## 2. Ausgangsproblem und gemessene Evidenz

Der bisher produktive Pfad liest die momentane Ist-Drehzahl aus `0x000C` und
integriert sie zeitlich. Bei gleichmäßiger Fahrt ist das plausibel; an den
Übergängen zwischen Stillstand und Bewegung geht jedoch reproduzierbar Weg
verloren.

Die belastbarste A/B-Messung fuhr dieselbe Gesamtstrecke einmal durchgehend und
einmal in vier Etappen:

| Ablauf | Odometrie | LiDAR-Wandvergleich | Abweichung |
|---|---:|---:|---:|
| `1 x 0,80 m` | 0,8019 m | 0,8305 m | +28,6 mm |
| `4 x 0,20 m` | 0,8215 m | 0,9020 m | +80,5 mm |

Drei zusätzliche Start-/Stoppvorgänge verursachten 51,9 mm zusätzlichen
Fehler, also **17,3 mm je zusätzlicher Etappe**. Die Scan-Streuung von 1,0 bis
3,4 mm ist deutlich kleiner als der Effekt.

Während einer Bremsphase wurde außerdem beobachtet, dass `0x000C` zunächst
`0 rpm` und später wieder `16 rpm` meldete. Eine Erhöhung der Leserate von 10
auf 50 Hz beseitigte den festen Versatz nicht. Auch eine Freigabe der Welle
durch den Stoppbefehl und rein kinetisches Rutschen wurden durch getrennte
Messungen widerlegt. Der interne Mechanismus des Drehzahlwerts bleibt offen.

Unabhängig davon hat der alte Pfad einen klaren Softwaremangel: Nach einem
fehlgeschlagenen Modbus-Read kann die Odometrie auf den kommandierten Sollwert
zurückfallen. Beim Stoppen ist dieser null. Noch stattfindende Bewegung kann so
unbemerkt aus der Odometrie verschwinden.

### Relevanz

- Für `slam_toolbox` sind ungefähr 30 mm meist innerhalb des
  Scanmatching-Suchraums korrigierbar.
- Bei vielen kurzen Nav2-Bewegungen summiert sich der feste Anteil.
- Für Andocken, Feinpositionierung und eine Verschiebung von Hand ist eine
  tatsächlich gezählte Radbewegung wichtig.
- Eine pauschale Korrektur von „17 mm je Start“ wäre technisch falsch: Sie misst
  keine Bewegung und wäre von Last, Rampe, Untergrund und Fahrart abhängig.

---

## 3. Verbindliche Registergrundlage

Quelle ist das offizielle StepperOnline-Dokument **Modbus Series Bus Driver
Function Manual V1.0**. Am realen ESS23-RS wird mit Modbus FC03 gelesen; FC04
wurde geprüft und wird nicht beantwortet. Der Fix schreibt keines der folgenden
Konfigurationsregister.

| Register | Zugriff | Bedeutung für den Fix |
|---|---|---|
| `0x000A` | RO | erstes Wort des aktuellen 32-Bit-Positionswerts |
| `0x000B` | RO | zweites Wort des aktuellen 32-Bit-Positionswerts |
| `0x000C` | RO | aktuelle Motordrehzahl, signed; Vergleichs- und Rückfallpfad |
| `0x0011` | RW/S | Segment-/Subdivision-Einstellung, Bereich 400 bis 51200, Handbuchvorgabe 1000 |
| `0x0019` | RW | 32-Bit-Wortreihenfolge: `0` = High vor Low, `1` = Low vor High |
| `0x0101` | RW/S | Encoderauflösung, viermal Encoder-Linienzahl, Handbuchvorgabe 4000 |

Für einen Closed-Loop-Motor beschreibt das Handbuch `0x000A/0x000B` als
„subdivision equivalent of the encoder feedback value“. Deshalb gilt:

> Weder `0x0011 = 1000` noch `0x0101 = 4000` darf ungeprüft als
> Positionseinheit pro Motorumdrehung übernommen werden. Die wirkliche
> Skalierung von `0x000A/0x000B` muss am konkreten ESS23-RS-Paar ausschließlich
> lesend ermittelt werden.

`0x0011` ist hier eine **Registeradresse**. Nicht verwechseln mit dem Wert
`0x0011`, der in das separate Hilfskommandoregister `0x002D` geschrieben würde,
um einen Motor freizugeben. Dieser Fix löst kein solches Kommando aus.

### Atomare Rückmeldung und Wortreihenfolge

Eine Motorprobe liest mit genau einem FC03-Zugriff ab `0x000A` drei Register:

```text
0x000A  Positionswort 1
0x000B  Positionswort 2
0x000C  Ist-Drehzahl
```

Die beiden Positionswörter dürfen nicht getrennt gelesen werden. Beim Übertrag
des Low-Worts könnte sonst ein nicht existierender Sprung entstehen.

Aus `0x0019` folgt die Dekodierung:

```text
word_order = 0: raw_u32 = (wort_0 << 16) | wort_1
word_order = 1: raw_u32 = (wort_1 << 16) | wort_0
```

Für Diagnoseausgaben wird `raw_u32` als signed int32 im Zweierkomplement
interpretiert. Für überlaufsichere Deltas bleibt die interne Darstellung
uint32.

---

## 4. Softwarearchitektur

### 4.1 Zwei explizite Odometriequellen

`odometry_source` wählt den realen Pfad:

| Wert | Verhalten | Verwendung |
|---|---|---|
| `encoder_position` | Pose direkt aus Deltas von `0x000A/0x000B` | Zielpfad nach Hardware-Abnahme |
| `speed` | bisherige Integration der Ist-Drehzahl aus `0x000C` | Rückfall und A/B-Vergleich |

Es gibt keinen stillen Wechsel von `encoder_position` auf `speed`. Ein
Quellenwechsel während einer Fahrt könnte Bewegung doppelt zählen oder
verlieren. Im Dry-run bleibt die befehlsbasierte Simulation bestehen, weil dort
bewusst keine Modbus-Hardware existiert.

### 4.2 Parametervertrag

| Parameter | Vorgabe | Bedeutung |
|---|---:|---|
| `odometry_source` | `encoder_position` oder `speed` | explizite reale Odometriequelle |
| `encoder_position_register` | `0x000A` | Startadresse des zusammenhängenden Positionswerts |
| `encoder_word_order_register` | `0x0019` | konfigurierte Reihenfolge der beiden 16-Bit-Wörter |
| `encoder_counts_per_motor_revolution` | `0` bis zur Messung | bestätigte Positionseinheiten je Motorumdrehung; `0` sperrt den Positionsmodus |
| `encoder_segment_register` | `0x0011` | nur lesende Diagnose der Segmentierung |
| `encoder_resolution_register` | `0x0101` | nur lesende Diagnose der Encoderauflösung |
| `encoder_expected_segment` | `0` bis H2 | erwarteter gelesener Wert aus `0x0011`; `0` erlaubt nur die read-only Inbetriebnahme |
| `encoder_expected_resolution` | `0` bis H2 | erwarteter gelesener Wert aus `0x0101`; `0` erlaubt nur die read-only Inbetriebnahme |
| `encoder_feedback_period_s` | `0.05` s | Zielabstand zwischen Positionspaaren; bei gültigen neuen Paaren 20 Hz |
| `encoder_stale_timeout_s` | `0.30` s | ab diesem Alter ist eine Rückmeldung stale |
| `encoder_max_recovery_gap_s` | `2.0` s | längste Lücke, deren kumuliertes Delta noch übernommen werden darf |
| `encoder_max_delta_factor` | `1.5` | Reserve über der physikalisch berechneten maximalen Änderung |
| `encoder_failure_stop_count` | `5` | aufeinanderfolgende normale FC03-Transportfehler bis Stopp und Reconnect |
| `modbus_timeout_s` | `0.10` s | Zeitgrenze eines einzelnen Modbus-Versuchs |
| `modbus_retries` | `0` | keine versteckten Pymodbus-Wiederholungen im Stopp-/Fehlerpfad |
| `cmd_timeout_s` | `0.25` s | monotone Echtzeit bis zum Watchdog-Stopp |
| `update_rate_hz` | `50` Hz | Node- und `state_json`-Takt, nicht die Encoder-`/odom`-Rate |
| `use_sim_time` | `false` bei scharfem RS485 | Simulationszeit ist für reale Motorsteuerung verboten |
| `odom_pose_xy_variance` | `0.0025` m² | konservativer Startwert für x/y-Pose |
| `odom_yaw_variance` | `0.0076` rad² | konservativer Startwert für Gierwinkel |
| `odom_twist_linear_variance` | `0.01` (m/s)² | konservativer Startwert für lineare Geschwindigkeit |
| `odom_twist_angular_variance` | `0.03` (rad/s)² | konservativer Startwert für Winkelgeschwindigkeit |

Der wichtigste Inbetriebnahmeschutz ist
`encoder_counts_per_motor_revolution: 0`. Solange die reale Einheit unbekannt
ist, muss `odometry_source: encoder_position` klar gesperrt werden. Ein
geratener Skalierungswert wäre gefährlicher als eine verweigerte
Initialisierung.

Nach H2 werden zusätzlich die auf **beiden** Motoren identisch und read-only
bestätigten Werte aus `0x0011` und `0x0101` als
`encoder_expected_segment` beziehungsweise `encoder_expected_resolution`
größer null eingetragen. Der Wert `0` ist bei diesen beiden Parametern nur für
die Inbetriebnahme gedacht; der reale Modus `encoder_position` bleibt damit
verriegelt.

Die vier Kovarianzen sind ausdrücklich keine bereits gemessenen
Sensorstatistiken. Sie verhindern die falsche Aussage „perfekte Odometrie“ und
werden in H4 aus wiederholten Fahrten gegen eine externe Referenz neu bestimmt.

Die Modbus-Runtime ist über
`src/base_hardware/requirements-modbus.txt` reproduzierbar auf
`pymodbus==3.14.0` und `pyserial==3.5` festgelegt:

```bash
python3 -m pip install -r src/base_hardware/requirements-modbus.txt
```

### 4.3 ROS-unabhängiger Kern

`src/base_hardware/base_hardware/encoder_odometry.py` enthält ausschließlich
Registerdekodierung, Wraparound- und Differentialantriebslogik. Es importiert
weder ROS noch `pymodbus` und kann deshalb offline getestet werden.

Wesentliche Schnittstellen:

- `decode_position_words`: genau zwei Wörter nach `0x0019` dekodieren;
- `u32_to_i32` und `decode_i16`: signed Diagnosewerte;
- `modular_delta_u32`: vorzeichenbehaftetes Delta über den 32-Bit-Überlauf;
- `MotorFeedback`: atomare Position/Drehzahl eines Motors;
- `EncoderUpdate`: Ergebnis eines vollständigen linken/rechten Paars;
- `EncoderOdometry`: Plausibilisierung und exakte
  Differentialantriebsintegration.

Die erste gültige Paarprobe setzt nur die Baseline. Sie erzeugt weder
Roboterbewegung noch einen Sprung in `/odom`.

### 4.4 Wraparound, Reset und Plausibilität

Am signed-32-Bit-Rand kann der Zähler von `2147483647` zu `-2147483648`
wechseln. Das Delta wird modular auf `[-2^31, 2^31-1]` zurückgeführt. Eine
Differenz von exakt `2^31` ist richtungsmehrdeutig und wird abgewiesen.

Ein Motorneustart, eine falsche Wortreihenfolge oder ein Zählerreset kann
ebenfalls einen Sprung erzeugen. Die maximal plausible Änderung folgt aus:

- vergangener Messzeit,
- `max_motor_rpm`,
- bestätigten Counts je Motorumdrehung,
- `encoder_max_delta_factor` und
- einer kleinen Quantisierungsreserve.

Ein unplausibles Paar wird nicht integriert und nie durch den Sollwert ersetzt.
Die Baseline wird kontrolliert neu gesetzt, damit der Fehler nicht beim nächsten
Sample nachläuft.

### 4.5 Radweg und Pose

Nach Bestätigung der Positionseinheit gilt:

```text
Motorumdrehungen = Positionsdelta / encoder_counts_per_motor_revolution
Radumdrehungen   = Motorumdrehungen / gear_ratio
Radweg           = Radumdrehungen * 2 * pi * wheel_radius_m
```

`invert_left` und `invert_right` werden auf die Rückmeldung spiegelbildlich zur
Kommandierung angewendet. Roboter-vorwärts muss anschließend für beide Räder
positiven Radweg ergeben.

```text
ds     = (ds_rechts + ds_links) / 2
dtheta = (ds_rechts - ds_links) / wheel_separation_m
```

Die Pose wird direkt und bogenrichtig aus diesen Wegdeltas fortgeschrieben. Die
Software rechnet nicht erst in eine Geschwindigkeit um, um diese anschließend
erneut im 50-Hz-Node-Takt zu integrieren. Die publizierte Geschwindigkeit ist
nur `Delta / tatsächliches Messintervall`.

### 4.6 Lücken- und Fehlerverhalten

- Ein unvollständiges linkes/rechtes Paar ändert weder Pose noch einzelne
  Motorbaseline und erzeugt keine neue `/odom`-Nachricht.
- Ein einzelner normaler FC03-Fehler behält den offenen Modbus-Client und die
  Baseline. Das nächste gültige Paar kann die zwischenzeitliche Änderung aus
  den kumulierten Counts nachholen, sofern Zeit und Delta plausibel sind.
- `encoder_failure_stop_count` gilt für aufeinanderfolgende normale
  FC03-Transportfehler. An der Schwelle erfolgen bestmöglicher Software-Stopp,
  Busfehlerstatus und Reconnect.
- Ein semantisch ungültiges Encoderpaar, insbesondere ein unplausibles oder
  richtungsmehrdeutiges Delta, sperrt die Fahrt und fordert sofort Stopp an.
  Der Tracker verwirft dieses Paar und setzt seine Baseline kontrolliert neu;
  der bestehende Modbus-Client bleibt bewusst erhalten.
- Eine Abweichung der Treiberkonfiguration von den in H2 bestätigten Werten
  sperrt den Fahrbetrieb ebenfalls sofort. Ein Reconnect wäre hier nutzlos;
  zuerst ist die Konfiguration zu klären oder zu korrigieren.
- Bei `encoder_stale_timeout_s` erfolgen immer Fahrtsperre und Stopp; ein
  Reconnect folgt nur, wenn ein Transportfehler die Stale-Lage verursacht. Es
  wird keine scheinbar frische Bewegung veröffentlicht. Der Software-Stopp
  ersetzt den mechanischen Not-Aus nicht.
- Python-Ausnahmen, eine unbekannte Pymodbus-API und Schreib-/Transportfehler,
  die keinen normalen FC03-Fehlerstatus darstellen, lösen den Stopp- und
  Reconnectpfad sofort aus und warten nicht auf die Fehlerschwelle.
- Jeder tatsächlich neu erzeugte Modbus-Client ist bewusst eine neue
  Zählerepoche: Die alte Baseline wird verworfen, Wortfolge und freigegebene
  Werte aus `0x0011`/`0x0101` werden erneut gelesen, und das erste gültige Paar
  setzt nur eine neue Baseline. So wird ein Controllerreset nicht als Bewegung
  integriert. Bewegung während des Reconnects bleibt unbekannt.
- Eine innerhalb desselben Clients zu lange, aber nicht bereits stale
  Messlücke wird ebenfalls ohne Posesprung neu basiert.

Der reale Positionsmodus verhält sich damit fail-closed: Er erfindet keine
Bewegung. Nur der bewusst hardwarefreie Dry-run integriert Befehle.

Im realen `encoder_position`-Modus wird `/odom` nur zu einem neuen gültigen
Positionspaar publiziert, bei der Zielperiode von 0,05 s also ungefähr mit
20 Hz. `state_json` bleibt davon getrennt und wird weiterhin im 50-Hz-
Node-Update veröffentlicht.

### 4.7 Eingangs- und Watchdog-Sicherheit

- `/cmd_vel` hat QoS-Queue-Tiefe 1. Ein veralteter Befehlsstau wird nicht nach
  einer Blockade nachgefahren; relevant ist der neueste Befehl.
- Nicht-endliche Werte (`NaN`, `+Inf`, `-Inf`) werden verworfen, als ungültiger
  Befehl gezählt und lösen eine Stoppanforderung aus.
- Der Befehls-Watchdog misst ausschließlich mit monotoner Echtzeit und prüft
  den Stopp vor einer möglichen Rückkehr wegen stehender oder rückwärts
  springender ROS-Zeit.
- `use_sim_time: true` ist bei `dry_run: false` und `allow_rs485: true`
  ausdrücklich verboten. Simulationszeit darf keinen realen Motor-Watchdog
  kontrollieren.
- Ob Bewegung angefordert ist, wird erst nach derselben Quantisierung auf den
  tatsächlich schreibbaren signed-RPM-Registerwert entschieden. Quantisieren
  beide Motorwerte zu null, bleibt der Antrieb gestoppt; es wird kein
  Startkommando für eine nicht darstellbare Kleinstbewegung gesendet.

---

## 5. Read-only Inbetriebnahmewerkzeug

Der zugehörige Offline-Test ist `tools/kartierung/test_encoder_position_pruefen.py`.

`tools/kartierung/encoder_position_pruefen.py` ist vom ROS-Node
getrennt und führt ausschließlich FC03-Lesezugriffe aus. Es enthält:

- `MotorConfig`, `PositionSample`, `RevolutionResult`;
- `read_holding_registers_compat` für die Pymodbus-Varianten
  `device_id`, `slave` und `unit`;
- `decode_position`, `signed_i16`, `signed_i32`, `delta_u32`;
- `read_motor_config`, `read_position_sample`;
- `calculate_revolution_result` für definierte Motor- oder Radumdrehungen.

Start je Motor:

1. FC03 `0x0011`, Count 1;
2. FC03 `0x0019`, Count 1;
3. FC03 `0x0101`, Count 1.

Jede laufende Probe ist exakt FC03 ab `0x000A`, Count 3. Es gibt keinen FC06-
oder sonstigen Schreibpfad.

CLI-Vertrag:

- Verbindung: `--port`, `--baudrate`, `--timeout`, `--motor-ids`;
- Protokoll: `--interval`, `--samples`, `--csv`, `--json`;
- zwingende Bestätigung: `--confirm-stack-stopped`;
- Messmodus: entweder `--measure-motor ID` oder `--measure-wheel ID`;
- Messparameter: `--turns`, bei Radmessung zusätzlich `--gear-ratio`.

Das Werkzeug verweigert den Start, wenn der RS485-Port laut `/proc` bereits
von einem Prozess geöffnet ist. `--confirm-stack-stopped` ersetzt diese Prüfung
nicht und ist keine Motor- oder Fahrfreigabe.

Die Ausgabedateien sind Messprotokolle. Falls sie Wohnungsgeometrie,
personenbezogene Angaben oder andere reale Umgebungsdaten enthalten, bleiben
sie lokal und werden nicht committed.

---

## 6. Was der Fix nicht behauptet

- Noch ist nicht bewiesen, wie viele `0x000A/0x000B`-Einheiten eine reale
  Motorumdrehung ergeben.
- Noch ist nicht bewiesen, dass Drehen von Hand am Rad den Zähler im vorgesehenen
  elektrischen Betriebszustand verändert.
- Reifenrutschen, Getriebespiel und mechanische Elastizität bleiben physisch.
- Die Änderung ersetzt weder LiDAR-Scanmatching noch spätere Sensorfusion.
- Sie setzt keinen Positionszähler zurück und verändert keine persistenten
  Motorparameter.
- Die kalibrierten Werte `wheel_radius_m: 0.0624` und
  `wheel_separation_m: 0.3845` werden ohne neue Messreihe nicht geändert.

---

## 7. Offline-Prüfung ohne Hardware

Ein grüner Testlauf ist Softwareevidenz, aber keine Hardwarefreigabe.

### Register- und Mathetests

- High-Low- und Low-High-Dekodierung;
- positive und negative signed 16/32 Bit;
- uint32-Wraparound vorwärts und rückwärts;
- exakt `2^31` als mehrdeutiges Delta;
- unvollständige und ungültige Registerantworten;
- Getriebeumrechnung Motor- und Radumdrehung;
- Handbuchbeispiel eines 32-Bit-Werts von 5000.

### Kinematiktests

- erstes Sample setzt nur Baseline;
- Geradeausfahrt vorwärts/rückwärts;
- Drehung auf der Stelle;
- exakter Kreisbogen;
- Montageinvertierung rechts genau einmal;
- synthetisch eingespeiste Positionsänderung ohne Kommando; dies beweist noch
  kein Handschieben an der Hardware;
- Bewegung während einer Bremsphase;
- derselbe Gesamtcount am Stück und in Etappen ergibt dieselbe Endpose;
- wiederholter Absolutstand wird nicht doppelt gezählt.

### Fehler- und Werkzeugtests

- kurze Lücke wird aus Absolutcounts nachgeholt;
- lange Lücke erzeugt Rebaseline ohne Posesprung;
- unplausibles Delta wird verworfen;
- nicht monotoner Zeitstempel verschiebt die Baseline nicht;
- Pymodbus-Kompatibilität `device_id`/`slave`/`unit`;
- neuer Modbus-Client verwirft die alte Baseline bewusst;
- kurzer normaler FC03-Fehler im selben Client kann Counts erhalten;
- unmittelbarer Ausnahmefehler, Stopp/Reconnect an der Transportfehlerschwelle
  und fail-closed Stopp bei Stale;
- erwartete Segmentierung/Auflösung verriegeln den realen Modus;
- semantisch ungültiges Delta sperrt sofort, rebased und reconnectet nicht;
- abweichende Treiberkonfiguration sperrt sofort ohne Reconnectschleife;
- nicht-endliche `cmd_vel` werden verworfen und fordern Stopp an;
- QoS-Tiefe 1 verhindert eine Befehlswarteschlange;
- der Watchdog nutzt monotone Echtzeit, und scharfes RS485 verbietet Sim-Zeit;
- quantisierte Null-RPM erzeugen keinen Motorstart;
- konservative, endliche positive Odometrie-Kovarianzen werden publiziert;
- Read-only Reihenfolge ausschließlich FC03;
- CSV- und JSONL-Ausgabe;
- `encoder_counts_per_motor_revolution: 0` sperrt den Positionsmodus;
- Dry-run löst keine Hardwaretransaktion aus.

Verbindliche Befehle auf dem Jetson:

```bash
cd ~/roboter_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select base_hardware
source install/local_setup.bash
colcon test --packages-select base_hardware
colcon test-result --verbose
```

Das Ergebnis dieses **Jetson-Laufs** wird erst nach seiner tatsächlichen
Ausführung mit Datum und Commit in `docs/PROJECT_MEMORY.md` ergänzt. Der dort
bereits protokollierte Lauf mit 59 Base-Hardware- plus 12 Werkzeugtests stammt
vom Entwicklungs-Mac und ersetzt die Jetson-Gegenprobe nicht.

Zusätzlich kompiliert und testet
`.github/workflows/encoder-odometry-offline.yml` dieselben Python-Komponenten
unter Ubuntu 22.04/Python 3.10 bei passenden Pushes und Pull Requests. Auch
dieser CI-Lauf ist keine Hardwarefreigabe.

---

## 8. Gestufte Hardware-Abnahme

### H0 - Vorbedingungen, keine Aktoren

- [ ] ausdrückliche Freigabe für die **nächste konkrete Phase** liegt vor;
- [ ] Not-Aus geprüft und erreichbar;
- [ ] Motorstrom für reine Build-/Offlinearbeiten aus;
- [ ] Roboter gegen Wegrollen gesichert, später getestete Räder frei;
- [ ] keine Person und kein Kabel im Bewegungsbereich;
- [ ] genau ein Besitzer von `/dev/ttyUSB_BASE`;
- [ ] Arbeitskopie sauber, Commit notiert;
- [ ] keine echten Karten, ROS-Bags oder Geheimnisse für Git vorgemerkt.

```bash
cd ~/roboter_ws
python3 tools/kartierung/roboterknoten.py
ps -eo pid=,cmd= | grep -E '[b]ase_hardware|[t]tyUSB_BASE'
```

### H1 - ausschließlich lesende Registerprobe

Noch keine Fahrkommandos senden und kein Motorregister schreiben. Je Motor
mehrfach erfassen:

- `0x0011`, `0x0019`, `0x0101`;
- atomar `0x000A` bis `0x000C`;
- Zeitstempel und Modbus-Fehler.

Akzeptanz:

- beide Motoren antworten stabil per FC03;
- `0x0019` ist `0` oder `1`;
- Konfigurationswerte bleiben stabil und werden nicht verändert;
- bei Stillstand bleibt die Position innerhalb erklärbarer Grenzen stabil;
- das Werkzeug protokolliert ausschließlich Reads.

### H2 - Positionseinheit und Vorzeichen bestimmen

Neue ausdrückliche Freigabe erforderlich. Einen aktiv haltenden Motor niemals
mit Gewalt am Rad oder an der Welle drehen. Ob und wie der Motor elektrisch
freigegeben wird, entscheidet die anwesende Person nach dem tatsächlichen
Hardwarezustand; ein Agent sendet kein Freigabekommando.

Für jedes Rad beziehungsweise jeden Motor getrennt:

1. Startposition lesen und mechanische Ausgangsmarke setzen.
2. Mit `--measure-motor ID` eine definierte Zahl Motorumdrehungen oder mit
   `--measure-wheel ID --gear-ratio 10.0` definierte Radumdrehungen erfassen.
3. Endposition lesen und modularen signed Delta-Betrag berechnen.
4. Mindestens dreimal in beiden Richtungen wiederholen.
5. Ergebnisse mit `0x0011` und `0x0101` vergleichen, aber nicht daran
   angleichen.

`encoder_counts_per_motor_revolution` darf erst ungleich null gesetzt werden,
wenn beide Richtungen reproduzierbar denselben Betrag ergeben und beide
Motoren erklärt sind. Kein Mittelwert aus widersprüchlichen Messungen.

Danach werden alle drei Schutzwerte gemeinsam eingetragen:

```yaml
encoder_counts_per_motor_revolution: <bestätigter Wert>
encoder_expected_segment: <bestätigter Wert aus 0x0011, größer 0>
encoder_expected_resolution: <bestätigter Wert aus 0x0101, größer 0>
```

Die beiden Erwartungswerte müssen auf beiden Motoren identisch bestätigt sein.
`0` ist nur für H0 bis H2 zulässig; im realen `encoder_position`-Modus
verriegelt es den Start beziehungsweise Reconnect absichtlich.

Akzeptanz für diese strikt lesende Messung:

- das Werkzeug sendet ausschließlich FC03 und keine Schreibtransaktion;
- `0x0011`, `0x0019` und `0x0101` bleiben über die Messläufe stabil; optional
  erfolgt ein Vorher-/Nachher-Vergleich durch einen zweiten identischen
  read-only Aufruf;
- `0x000A/0x000B` liefern in beiden Richtungen reproduzierbare Deltas;
- die Vorzeichen lassen sich eindeutig den beiden Drehrichtungen zuordnen;
- `0x000C` ist nur zusätzliche Beobachtung, kein Counts-Akzeptanzkriterium.

`0x001D` wird von diesem Werkzeug nicht gelesen und ist für H2 kein Kriterium.
Die Probe schreibt und verändert kein Motorregister.

### H3 - aufgebockter, begrenzter Motorlauf

Neue ausdrückliche Fahrfreigabe erforderlich. Niedrige Drehzahl, kurze Dauer:

- Räder einzeln vorwärts/rückwärts;
- gemeinsam geradeaus;
- entgegengesetzt als Drehung auf der Stelle;
- Encoderposition, Ist-Drehzahl, Sollwert und `/odom` parallel protokollieren;
- ROS-Vorzeichen prüfen;
- Watchdog, stale timeout und Fehlerzähler ohne Bodenfahrt prüfen.

Kein Test darf automatisch vom aufgebockten Zustand in eine Bodenfahrt
übergehen.

### H4 - begrenzte Bodenfahrt

Neue ausdrückliche Fahrfreigabe, freie Strecke, Not-Aus in der Hand und
funktionierender Nahbereichsschutz. Zuerst kurze Gerade, danach die bekannte
A/B-Messung:

```text
1 x 0,80 m
4 x 0,20 m
```

Verglichen werden:

- `odometry_source: encoder_position`;
- `odometry_source: speed`;
- externe Referenz, bevorzugt Lasermessgerät;
- LiDAR nur als zusätzliche Referenz;
- Kursfehler und beide Drehrichtungen.

Aus ausreichend vielen Wiederholungen werden außerdem die Residuen für
x/y-Pose, Gierwinkel sowie lineare und Winkelgeschwindigkeit gegen die externe
Referenz bestimmt. Erst daraus werden die vier `odom_*_variance`-Parameter
kalibriert. Die konservativen Startwerte nicht aufgrund einer einzelnen guten
Fahrt absenken; Messaufbau, Stichprobenzahl und Berechnung im Protokoll
festhalten.

Der Fix ist erst praktisch bestanden, wenn der Zusatzfehler der drei weiteren
Start-/Stoppvorgänge gegenüber den alten 51,9 mm reproduzierbar verschwindet,
ohne Skalen- oder Winkelfehler zu verschlechtern. Die Toleranz wird aus
Messauflösung und Wiederholstreuung **vor** der abschließenden Bewertung
festgelegt und mit Rohwerten dokumentiert.

### H5 - Fehler und Wiederanlauf

Nur unter denselben Sicherheitsbedingungen:

- kontrolliert einen normalen FC03-Lesefehler erzeugen, ohne Leitungen im Lauf
  zu ziehen, und bestätigen, dass kein Sollwert als Bewegung integriert wird;
- bei einer kurzen Fehlprobe prüfen, dass Client und Baseline erhalten bleiben
  und das nächste gültige Paar die kumulierten Counts plausibel übernimmt;
- an `encoder_failure_stop_count` aufeinanderfolgenden normalen FC03-Fehlern
  bestmöglichen Stopp, Busfehlerstatus und Reconnect prüfen;
- bei Stale-Timeout Fahrtsperre und Stopp prüfen; Reconnect nur bei
  zugrunde liegendem Transportfehler erwarten;
- eine Python-Ausnahme oder unbekannte Pymodbus-API separat simulieren und den
  sofortigen Stopp-/Reconnectpfad ohne Warten auf die Schwelle prüfen;
- nach einem tatsächlich neuen Modbus-Client bestätigen, dass die alte
  Baseline bewusst verworfen wird und das erste gültige Paar nur neu basiert;
- eine lange Lücke innerhalb desselben Clients ohne Posesprung neu baselinen;
- kurze Fehlprobe, Fehler-/Stale-Schwelle und echten neuen Client getrennt
  prüfen;
- ein unplausibles Delta einspeisen und sofortige Fahrtsperre/Stopp,
  unveränderte Pose, kontrollierte Rebaseline sowie ausbleibenden Reconnect
  bestätigen;
- eine Abweichung von `encoder_expected_segment` oder
  `encoder_expected_resolution` prüfen: sofort verriegelt, kein Reconnect;
- Controllerneustart nur als eigener ausdrücklich freigegebener Test.

---

## 9. Protokollpflicht

Für jeden realen Lauf festhalten:

- Datum, Branch, vollständiger Commit;
- Motor-Hardware/Firmware und Motor-ID;
- `0x0011`, `0x0019`, `0x0101` je Motor;
- bestätigte Counts pro Motorumdrehung;
- Radradius, Spurweite, Getriebeübersetzung;
- Start-/Endposition und Deltas beider Motoren;
- Messintervalle, stale/ungültige/unplausible Samples;
- RS485-Reconnects und Software-Stopps;
- Sollstrecke, `/odom`, externe Referenz, Kursfehler;
- Sicherheitsaufbau und ausdrückliche Freigabe;
- Rückfalltest.

ROS-Bags, Karten echter Räume und andere Wohnungsdaten bleiben lokal.

---

## 10. Rückfallweg

Bewusst auf den bisherigen Pfad zurückschalten:

```yaml
odometry_source: speed
```

Danach `base_hardware` neu bauen und im Stillstand neu starten. Nicht während
einer Fahrt dynamisch umschalten. Der Rückfall stellt den erprobten
Drehzahlpfad wieder her, einschließlich seines bekannten festen Versatzes.

Soll der ganze Softwarecommit zurückgenommen werden, einen normalen `git revert`
auf einem eigenen Branch benutzen. Kein `git reset --hard`, keine unbekannten
Jetson-Dateien überschreiben und keine persistenten Motorparameter ändern.

---

## 11. Abschlusskriterien

Erst danach darf der Status „am realen Roboter abgenommen“ lauten:

- [ ] Offline-Tests mit Commit und Ergebnis protokolliert;
- [ ] Read-only Werkzeug nachweislich ohne Schreibzugriff;
- [ ] Register und Wortreihenfolge beider Motoren bestätigt;
- [ ] Positionseinheit je Motorumdrehung reproduzierbar gemessen;
- [ ] Vorzeichen für beide Räder und Richtungen bestätigt;
- [ ] Wraparound, Reset und Plausibilisierung geprüft;
- [ ] kein stiller Sollwertfallback im Positionsmodus;
- [ ] stale-/Fehler-Stopp aufgebockt geprüft;
- [ ] A/B-Streckentest mit Wiederholungen bestanden;
- [ ] Drehgenauigkeit mindestens auf dem vorherigen Stand;
- [ ] RS485-Selbstheilung und `speed`-Rückfall geprüft;
- [ ] `docs/PROJECT_MEMORY.md` mit Evidenz, Risiken und Rückfallweg ergänzt;
- [ ] keine Geheimnisse oder realen Wohnungsdaten committed.

Bis dahin bleibt die ehrliche Einordnung: **Softwareseitig umgesetzt,
Hardware-Abnahme offen.**
