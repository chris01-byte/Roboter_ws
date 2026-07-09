# safety_monitor — Onboard-Not-Aus-Wächter (Befund K4)

Publiziert **`/safety/estop`** (`std_msgs/Bool`, latched), das der Behavior-Tree bei
jedem Tick prüft (`IsEstopClear`). Vorher gab es dafür auf dem echten Roboter **keinen
Publisher** — seit Missionen mit K1 wirklich laufen, wäre dadurch jede echte Mission
sofort mit FAILURE gestorben. Dieser Node schließt die Lücke.

## Konvention

| `/safety/estop` | Bedeutung |
|---|---|
| `data: true`  | Not-Aus **aktiv** → BT hält sofort an |
| `data: false` | frei → Roboter darf arbeiten |

## Quellen des Not-Aus (ODER-verknüpft)

1. **Software-Anforderung** `/safety/estop_request` (`Bool`) — z. B. GUI-Button oder
   eine kleine Brücke von einem Hardware-Taster. `true` = ausgelöst.
2. **Nahbereich** (`near_field/status`) — nur wenn `use_near_field_estop: true`
   (Default **aus**). Als harte Notbremse bei extrem naher Distanz; die normale
   reaktive Verlangsamung macht weiter der `collision_monitor`.
3. **Hardware-Taster (GPIO)** — Platzhalter (wie RS485 in `base_hardware`); erst aktiv,
   wenn `Jetson.GPIO` eingebunden ist. Bis dahin über (1) brücken.

## Start

```bash
ros2 launch safety_monitor safety_monitor.launch.py
```
Wird von `robot_bringup/robot.launch.py` automatisch mitgestartet (onboard).

## Not-Aus testen

```bash
ros2 topic echo /safety/estop                                                   # data: false
ros2 topic pub --once /safety/estop_request std_msgs/msg/Bool "{data: true}"    # ausloesen
ros2 topic echo /safety/estop                                                   # data: true
ros2 topic pub --once /safety/estop_request std_msgs/msg/Bool "{data: false}"   # zuruecksetzen
```
Automatisiert in `pruefplan_jetson.sh` als **Stufe SAFE**.

## Sicherheits-Hinweis (Befund S5)

Ein echter Hardware-Not-Aus muss **fail-safe / nach Ruhestromprinzip** verdrahtet sein
(Drahtbruch → ausgelöst). Solange nur die Software-Anforderung genutzt wird, ist das
**nicht** gegeben — der Node meldet das beim Start. Die **hardwired Sicherheitskette
bleibt die primäre Ebene**; dieser Node ist die Firmware-/BT-Sicht darauf.

## Offen / später

- GPIO-Anbindung des physischen Not-Aus-Tasters (`Jetson.GPIO`), fail-safe verdrahtet.
- Optional: Not-Aus-Button in der Smartphone-GUI (publiziert auf `/safety/estop_request`).
- Kopplung an `base_hardware` (Motor-Freigabe), sobald der Antrieb scharf läuft.
