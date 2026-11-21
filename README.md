# roboter_ws

ROS 2 Humble workspace fuer die mobile Roboterplattform Amadeus: Fahrbasis, LiDAR-Navigation, Nahbereichsschutz, Missionslogik, semantische Karte, iOS-Bedienung, OAK-Wahrnehmung und die vorbereitete Arm-Integration.

Der Repository-Root ist bewusst knapp gehalten. Der aktuelle Arbeitsstand und die detaillierte Dokumentation liegen unter `PROJEKT_STATUS.md` und `docs/`.

## Einstieg

| Dokument | Zweck |
|---|---|
| [`PROJEKT_STATUS.md`](PROJEKT_STATUS.md) | Aktueller Gesamtstatus, Mainline-Gates und naechster sicherer Schritt. |
| [`docs/README.md`](docs/README.md) | Navigation der aktiven und historischen Dokumentation. |
| [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md) | Entscheidungen mit Evidenz, Teststatus und Rueckfallwegen. |
| [`docs/ROBOT_TRANSFER.md`](docs/ROBOT_TRANSFER.md) | Jetson-/Hardwareuebergabe und Betriebswissen. |
| [`docs/ARM_KONTEXT.md`](docs/ARM_KONTEXT.md) | Einstieg für Agenten: Hardware, vorhandene Software, Quellen und offene Punkte. |
| [`docs/INTEGRATIONSPLAN_ARM_SOFTWARE.md`](docs/INTEGRATIONSPLAN_ARM_SOFTWARE.md) | Stufenplan: zunächst Arm-Inbetriebnahme, später Greifer und OAK-Integration. |
| [`docs/ARM_INBETRIEBNAHME_MESSBLATT.md`](docs/ARM_INBETRIEBNAHME_MESSBLATT.md) | Aufnahme und reale Versuchsprotokolle aller sechs Achsen. |
| [`docs/ARM_BUILDPROTOKOLL.md`](docs/ARM_BUILDPROTOKOLL.md) | Umgesetzte Änderungen, maximal 200 Wörter je Eintrag. |
| [`docs/INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md`](docs/INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md) | Diagnostik, Selbstbefreiung, Ereignisprotokoll und Supervision. |

Historische Pruefplaene und Ergebnisprotokolle liegen unter [`docs/archive/`](docs/archive/). Sie bewahren Nachweise, sind aber keine aktuelle Freigabe.

## Komponenten

```text
Fahrbasis:       base_hardware -> encoder odometry -> cmd_vel mission gate
Navigation:      STL-27L -> scan normalization -> SLAM/Nav2 -> exploration
Nahbereich:      VL53L7CX -> collision monitor
Missionen:       mission_manager -> Behavior Tree -> robot interfaces
Bedienung:       smartphone GUI / iOS app -> rosbridge
Wahrnehmung:     OAK-D-S2 -> semantic perception; frische Greifpose noch zu integrieren
Arm (Build A):   Inventar -> Validierung / Fake / reine ESS17-RS07-Leseprobe
Arm (geplant):   5 ESS17 + 1 NEMA23 -> Controller -> MoveIt 2 -> Arm-Actions
```

## Sicherer Betrieb

- `/safety/estop=true` bedeutet Not-Aus aktiv; softwareseitige Bewegungsfreigaben muessen dann gesperrt bleiben.
- Die hardwired Sicherheitskette ist primaer. Software ersetzt keinen Hardware-Not-Aus.
- Echte Fahrbewegung bleibt ein expliziter, beaufsichtigter Schritt mit der passenden Hardwareabnahme.
- Feinmanipulation soll frische Greifziele in `base_link` verwenden; vorhandene map-Verträge sind vor Integration abzugleichen.
- Registersemantik und Skalierung werden pro Motortyp und Achse bestätigt; der genaue NEMA23-Typ im Arm ist noch offen.

## Bauen und Pruefen

Die konkrete Build- und Abnahmeanweisung richtet sich nach dem bearbeiteten Paket und der Zielmaschine. Massgeblich sind:

1. die Pakettests und GitHub Actions der jeweiligen Aenderung,
2. die aktuelle Jetson-Abnahme in [`docs/ROBOT_TRANSFER.md`](docs/ROBOT_TRANSFER.md),
3. die Eintraege in [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md).

`pruefplan_jetson.sh` bleibt als historische Referenz im Root. Er ist kein pauschaler Freigabebefehl fuer den heutigen Stand, solange seine Stages nicht gegen die aktuelle Paketstruktur und Hardware erneut validiert wurden.

## Branch-Regeln

`main` ist die Zielbasis fuer neue Arbeit, sobald die laufende Mainline-Konsolidierung gemerged ist. Bis dahin werden keine alten gestapelten Feature-/Fix-Branches direkt nach `main` gemerged.

Jede neue Aenderung:

1. startet von dem aktuellen `main`,
2. hat genau ein fachliches Thema,
3. enthaelt Tests und einen klaren Rueckfallweg,
4. wird nach erfolgreichem Merge bereinigt: PR schliessen/mergen, vollstaendig enthaltenen Branch loeschen.

Details zum aktuellen Konsolidierungsstand stehen in [`PROJEKT_STATUS.md`](PROJEKT_STATUS.md).
