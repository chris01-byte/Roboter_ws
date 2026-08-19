# Integrationsplan: Diagnostik und sichere Selbstbefreiung

**Stand:** 2026-08-19  
**Ausgangsbranch:** `fix/polygon-footprint-wohnung`  
**Status:** Architektur- und Umsetzungsplan; keine neue Fahrfreigabe.

## 1. Ziel

Amadeus soll sich aus normalen Navigationsproblemen kontrolliert erholen koennen, ohne bei Sicherheitsunsicherheit weiterzufahren. Gleichzeitig braucht der Betrieb eine zentrale, lokale Diagnoseschnittstelle fuer Status, Ereignisse und Fehleranalyse.

Die Leitregel lautet:

```text
Sicher stoppen -> Stillstand bestaetigen -> Ursache klassifizieren
-> genau eine begrenzte Recovery oder Mission abbrechen
-> Preflight erneut pruefen -> weiterfahren oder Fehler verriegeln
```

Selbstbefreiung ist keine allgemeine Fahrfreigabe. Sie darf bestehende Grenzen von `cmd_vel_mission_gate`, `velocity_smoother`, `collision_monitor`, `base_hardware`, `/safety/estop` oder die Hardware-Not-Aus-Kette nie umgehen.

## 2. Bestehende Bausteine

| Komponente | Bestehende Aufgabe | Nutzung im Plan |
|---|---|---|
| `base_hardware` | Watchdog, Encoder-/Modbus-Health, Stop, RS485-Reconnect | liefert Antriebszustand; bleibt alleiniger Motorzugriff |
| `cmd_vel_mission_gate` | sperrt Befehle bei fehlender Mission oder stale Sensorik | erhaelt zusaetzliche Health-Sperre |
| `explore` | Frontier, Portal, sichere Drehung, bounded Vorwaertsetappe | bleibt alleinige Quelle automatischer Recovery-Bewegung |
| `mission_manager` | Missionslebenszyklus und Cancel | beendet Missionen bei Health-Fault endgueltig |
| `collision_monitor` | reaktive VL53-Kollisionssicherung | bleibt letzte Softwareinstanz vor `/cmd_vel` |
| `safety_monitor` | `/safety/estop` | nimmt nur irreversible kritische Faults entgegen |
| `robot_bringup` | Onboard Launch | startet die neue Diagnostikschicht |

## 3. Nicht verhandelbare Sicherheitsgrenzen

1. Keine Recovery startet ohne bestaetigten Stillstand: beide Motoren 0 rpm, keine stale Odometrie.
2. Fehlende oder stale Daten von LiDAR, VL53, Odometrie, Karte, TF oder Lokalisierung erlauben nie Bewegung.
3. Not-Aus ist immer verriegelt und darf nur durch einen bewussten menschlichen Reset geloest werden.
4. Die Diagnostik publiziert keine direkte Bewegungsbefehle.
5. Automatische Rueckwaertsfahrt wird nicht eingefuehrt. Eine Rueckzugsbewegung kann nur nach sicherer Drehung als begrenzte Vorwaertsfahrt erfolgen.
6. In einer engen Tuer oder einem Portal darf nicht gedreht werden. Die gepaddete Drehhuelle ist groesser als die gemessene 680-mm-Tuer.
7. Der bestehende Portalpfad bleibt Vorwaerts-/LiDAR-geprueft; seine Bewegungsgrenzen bleiben unveraendert.

## 4. Zielarchitektur

```text
/base_hardware/state_json  /explore/status_json  /mission_manager/status_json
/localization/status_json  /safety/estop  Sensor-/TF-Frische
                   |
                   v
         robot_diagnostics/health_supervisor
                   |
        +----------+-----------+
        |                      |
        v                      v
/robot_health/status_json  /diagnostics + lokale JSONL-Ereignisse
        |
        +--> cmd_vel_mission_gate: frische Health-Freigabe erforderlich
        +--> mission_manager: laufende Mission sicher abbrechen
        +--> safety_monitor: nur kritische, irreversible Faults
```

Die Health-Komponente ist Beobachter und Entscheider fuer den Betriebszustand. Sie besitzt weder einen `/cmd_vel`-Publisher noch eine Nav2-Action.

## 5. Neues Paket `robot_diagnostics`

Neues ROS-2-Paket unter `src/robot_diagnostics/`:

```text
robot_diagnostics/
  config/robot_diagnostics.yaml
  launch/robot_diagnostics.launch.py
  robot_diagnostics/
    event_store.py
    health_model.py
    health_supervisor_node.py
    status_contract.py
  test/
  README.md
```

### Eingaben

- `/base_hardware/state_json`
- `/explore/status_json`
- `/mission_manager/status_json`
- `/localization/status_json` und `/localization/ready`
- `/safety/estop`
- Heartbeats von `/map`, `/scan_normiert`, beiden VL53-Streams und `/odom`
- optional: `collision_monitor_state`, `link_monitor` und Linux-Systemmetriken

### Ausgaben

- `/diagnostics` (`diagnostic_msgs/msg/DiagnosticArray`)
- `/robot_health/status_json` (`std_msgs/msg/String`, reliable, transient-local)
- `/robot_health/events_json` als begrenzter Read-only-Ereignisfeed
- lokale JSONL-Dateien unter `~/.local/share/amadeus/diagnostics/`

### Betriebszustand

```text
BOOTING -> PREFLIGHT -> READY -> RUNNING
                         |         |
                         v         v
                     SAFE_STOP <- RECOVERING
                         |
                         v
                    FAULT_LATCHED

ESTOP_LATCHED ist von jedem Zustand erreichbar.
```

`FAULT_LATCHED` und `ESTOP_LATCHED` werden nicht automatisch zurueckgesetzt.

## 6. Health-Vertrag

`/robot_health/status_json` verwendet `schema_version: 1` und bleibt klein genug fuer App und rosbridge.

```json
{
  "schema_version": 1,
  "state": "READY",
  "motion_permitted": true,
  "fault_latched": false,
  "recovery_allowed": false,
  "reasons": [],
  "freshness": {
    "map": true,
    "scan": true,
    "vl53_left": true,
    "vl53_right": true,
    "odom": true,
    "localization": true
  },
  "sequence": 1842,
  "time": 1787145600.0
}
```

Jede Statusaenderung erzeugt zusaetzlich ein Ereignis:

```json
{
  "sequence": 1842,
  "severity": "error",
  "component": "base_hardware",
  "code": "ENCODER_STALE",
  "message": "Encoderdaten nicht frisch",
  "mission_id": "explore-...",
  "recoverable": true,
  "recovery_action": "safe_stop_then_replan",
  "attempt": 1,
  "snapshot": {"rs485_ready": false, "motor_rpm_left": 0, "motor_rpm_right": 0}
}
```

Keine Zugangsdaten, WLAN-Daten, Kartenbilder, ROS-Bags oder vollständigen Systemlogs in diesen Topics speichern.

## 7. Einbindung in vorhandene Pakete

### `robot_bringup`

- `robot.launch.py` um `robot_diagnostics.launch.py` erweitern.
- `package.xml` um Abhaengigkeit `robot_diagnostics` erweitern.
- Diagnostik startet immer, auch wenn keine autonome Mission aktiv ist.

### `cmd_vel_mission_gate`

- Parameter `health_status_topic`, `health_timeout_s` und `require_robot_health` ergaenzen.
- Bewegung ist nur erlaubt, wenn der Health-Status frisch ist und `motion_permitted=true` meldet.
- Fehlt die Diagnostik oder ist der Status stale, publiziert das Tor sofort null.
- Das Tor bleibt die einzige zusaetzliche Bewegungsfreigabe; die Diagnostik schreibt keinen Twist.

### `mission_manager`

- Health-Status abonnieren.
- Bei `SAFE_STOP`, `FAULT_LATCHED` oder stale Health eine aktive Nav2-/BT-Mission sauber abbrechen.
- Nach einem Health-Fault keine alte Mission automatisch fortsetzen.
- Status additiv um `health_state`, `health_reasons` und `recovery_attempts` erweitern.

### `explore`

Neue pure Datei `explore/recovery_planning.py`:

1. Ziel blacklisten und Karte/Costmap neu bewerten.
2. Normale Frontier- und Portalplanung haben Vorrang.
3. Nur auf freier Flaeche mit bestaetigter Drehhuelle darf ein kontrollierter Scan/Ausrichtungsschritt erfolgen.
4. Nur ein footprintbreiter, frischer Korridor erlaubt eine begrenzte Vorwaertsetappe.
5. Danach stoppen, Karte neu bewerten und nur einmal neu planen.
6. Wiederholtes Scheitern endet in `FAULT_LATCHED` oder Missionsabbruch.

Startgrenzen fuer die erste Abnahme:

```text
max_recovery_attempts_per_mission: 1
max_recovery_forward_m: 0.25
max_recovery_duration_s: 20
allow_reverse: false
allow_rotation_in_portal: false
```

Der bestehende LiDAR-gepruefte Portaluebergang wird nicht ersetzt. Er bleibt die Sonderbehandlung fuer durch Inflation getrennte, physisch verbundene Bereiche.

### `safety_monitor`

- Kritische, nicht wiederherstellbare Fehler duerfen eine `/safety/estop_request` ausloesen.
- `robot_diagnostics` darf diesen Request nie selbst loesen.
- Die GPIO-/Ruhestrom-Anbindung bleibt ein separater Hardware-Sicherheitsblocker.

## 8. Recovery-Matrix

| Befund | Automatische Aktion | Weiterfahrt |
|---|---|---|
| einzelnes Nav2-Ziel fehlgeschlagen | stoppen, Ziel blacklisten, frisch planen | hoechstens einmal |
| Portal blockiert | stoppen, Portal markieren, andere Frontier planen | keine Direktfahrt |
| kurz stale Odometrie/TF | null, begrenzt auf Erholung warten | erst nach Preflight |
| Modbus-Lesefehler | `base_hardware` stoppt und reconnectet | nur nach neuer Encoder-Baseline |
| LiDAR/VL53-Ausfall | `SAFE_STOP`, Fault | nie automatisch |
| Lokalisierung verloren | stoppen; nur vorhandener enger Lokalisierungssuchpfad | nur vor erster Freigabe |
| Wiederholungsgrenze erreicht | `FAULT_LATCHED`, Mission abbrechen | menschliche Entscheidung |
| Not-Aus | `ESTOP_LATCHED` | menschlicher Reset |

## 9. App- und Diagnosezugang

Die iOS-App erhaelt nur Read-only-Informationen:

- Gesamtzustand und Sperrgrund
- Sensorfrische
- RS485-/Encoderzustand
- aktuelle Mission und begrenzte Recovery-Zaehler
- die letzten 50 redigierten Ereignisse
- Exportanforderung fuer ein lokales Diagnosepaket

Kein Knopf in der App darf `FAULT_LATCHED` oder `ESTOP_LATCHED` allein zuruecksetzen. Ein Reset erfordert lokale Bestaetigung und einen vollstaendigen Preflight.

## 10. Systemd-Huelle

Unter `integration/systemd/` werden Vorlagen fuer nicht fahrende Kernprozesse angelegt.

Regeln:

- `Restart=on-failure` nur fuer sichere Onboard-Prozesse.
- jeder Prozessstart erfolgt mit `active_drive=false`.
- ein Prozessneustart stellt niemals eine Fahrfreigabe wieder her.
- Crash-Schleifen werden begrenzt und als `FAULT_LATCHED` erfasst.
- Temperatur, RAM-Druck, freier Speicher und Dienstzustand werden diagnostisch gemeldet.
- kein automatischer Motor-Power-Cycle, kein automatischer Hardware-Not-Aus-Reset.

## 11. Tests und Abnahme

### Stufe A: Offline

- JSON-Grenzen, Schema, Ereignisrotation und Redaction
- Health-Zustandsautomat und Latch-Verhalten
- stale-/fresh-Grenzen fuer alle Quellen
- Recovery-Entscheidung und Drehhullen-Geometrie
- kein Motion- oder Nav2-Zugriff im Diagnostikpaket

### Stufe B: ROS ohne Motorstrom

- `cmd_vel_mission_gate` stoppt bei fehlendem/stale Health-Status
- `mission_manager` cancelt aktive Mission
- Explorer blacklistet ein fehlgeschlagenes Ziel
- `robot_diagnostics`-Neustart erzeugt keine Fahrt
- rosbridge liefert nur den begrenzten Read-only-Vertrag

### Stufe C: Jetson motorlos

- Gesamtlaunch mit `active_drive=false`
- JSONL-Dateien, Event-Rotation und Diagnoseexport pruefen
- simulierte Sensor-/TF-Stale-Ereignisse pruefen
- `systemd`-Neustart pruefen, ohne dass `allow_rs485=true` entsteht

### Stufe D: Beaufsichtigte Fahrt

- ein kontrolliert blockiertes Frontier-Ziel
- sicherer Stopp, dokumentierter Grund und genau ein Replan
- keine Drehung in Tuer/Portal
- nach Recovery entweder neues Ziel oder `FAULT_LATCHED`

### Stufe E: Fehlerinjektion

- VL53-stale
- LiDAR-stale
- Encoder-stale
- Modbus-Reconnect
- Portal ohne Drehfreiraum
- Nav2-Cancel-Timeout

Jede reale Fahrt erfordert die Sicherheitsregeln aus `AGENTS.md`: freie Flaeche, erreichbarer Hardware-Not-Aus, anwesende Person und neue ausdrueckliche Freigabe.

## 12. Branch- und Merge-Reihenfolge

1. `feature/robot-health-diagnostics` - nur Beobachtung, Events, Tests und App-Lesevertrag.
2. `feature/health-gated-missions` - Fahrtor und Mission-Cancel pruefen Health.
3. `feature/bounded-explore-recovery` - Replan, Recovery-Planung und begrenzte Vorwaertsetappe.
4. `ops/safe-systemd-supervision` - motorloser Dienststart und Crash-Grenzen.
5. `feature/resilient-autonomy-integration` - nur nach Einzelabnahmen zusammenfuehren.

Jeder Branch braucht Build, Tests, dokumentierte Hardwarewirkung, Rueckfallweg sowie Aktualisierungen in `docs/PROJECT_MEMORY.md` und `docs/ROBOT_TRANSFER.md`.

## 13. Rollback

- `robot_diagnostics` im Bringup deaktivieren.
- `require_robot_health=false` nur fuer motorlose Fehlersuche zulassen; nie als Produktionsrueckfall fuer autonome Fahrt.
- `max_recovery_attempts_per_mission=0` deaktiviert neue Bewegungs-Recovery vollstaendig.
- `portal_crossing_enabled=false` deaktiviert nur die Portalbruecke; normale Frontier-Navigation bleibt erhalten.
- Bei sicherheitskritischem Verhalten: `/safety/estop_request=true`, Motorstrom trennen und lokale Ereignisdateien sichern.

## 14. Akzeptanzkriterium

Die Erweiterung gilt erst als erfolgreich, wenn ein realer Fehler nicht zu einer unkontrollierten Bewegung, einer Neustartschleife oder einem stillen Missionsende fuehrt. Der Roboter muss entweder kontrolliert neu planen oder mit nachvollziehbarem Ereignis, bestaetigtem Stillstand und gesperrter Weiterfahrt enden.
