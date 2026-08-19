# Projektstatus: Roboter_ws

**Stand:** 2026-08-19

**Geltung:** Dieser Status beschreibt die derzeitige Mainline-Konsolidierung. Detaillierte Entscheidungen und Messnachweise stehen in [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md); die Dokumentationsnavigation steht in [`docs/README.md`](docs/README.md).

---

## Kurzfassung

- `main` ist weiterhin der Default-Branch, liegt aber hinter der aktuellen Integrationslinie.
- Der komplette, derzeitige Integrationsstand liegt in `fix/polygon-footprint-wohnung` und den darauf aufbauenden Dokumentationsbranches.
- `chore/repository-mainline-cleanup` bereitet die Uebernahme in `main` vor: aktuelle Dokumentation wird sichtbar gemacht, historische Pruefplaene bleiben archiviert.
- Es werden durch diese Dokumentationsarbeiten keine Motoren, Sensoren oder Sicherheitsparameter bewegt oder konfiguriert.
- Neue Entwicklungsarbeit startet erst nach erfolgreicher Mainline-PR von `main`, nicht mehr auf historischen Feature- oder Fix-Branches.

## Aktuelle Integrationslinie

Die Plattform wurde in aufeinander aufbauenden Branches entwickelt. Die zuletzt aktive fachliche Linie ist:

```text
main
  -> feature/stl27l-integration
  -> agent/slam-toolbox-pure-rotation-fix
  -> fix/encoder-position-odometry
  -> feature/semantic-map-editor
  -> fix/sanfteres-anfahren
  -> feature/reale-raumfahrt
  -> feature/globale-lokalisierung
  -> feature/automatische-lidar-kartierung
  -> feature/hybrid-erkundung-app
  -> fix/polygon-footprint-wohnung
```

Die offenen Pull Requests #2, #4, #5 und #6 sind Teil dieser historischen Stapelstruktur. Sie sind nicht als voneinander unabhaengige Kandidaten fuer einen direkten Merge nach `main` zu behandeln.

## Mainline-Gates

Bevor `main` auf den aktuellen Integrationsstand wechselt, muessen diese Schritte in der Mainline-PR dokumentiert und bestanden sein:

1. Basis der PR ist `main`; Head ist der vollstaendige Aufraeum-/Integrationsbranch.
2. GitHub Actions sind gruen oder ein fehlender Check ist fachlich begruendet.
3. Auf dem Jetson wurden die betroffenen ROS-2-Humble-Pakete gebaut und ihre Tests ausgefuehrt.
4. Keine Konflikte in Dokumentation, Launch-Dateien, Schnittstellen oder Sicherheitsparametern.
5. Die Abnahme bleibt nachvollziehbar: Testumfang, Hardwareumfang und Rueckfallweg werden im PR beschrieben.
6. Erst nach Merge: alte, vollstaendig enthaltene Draft-PRs schliessen und ihre Branches loeschen.

Ein Mainline-Merge ersetzt keine scharfe Hardwareabnahme. Der letzte dokumentierte Teststand ist immer gegen die tatsaechliche Hardware- und Konfigurationsrevision zu bewerten.

## Aktive fachliche Arbeit

| Bereich | Status | Naechster sicherer Schritt |
|---|---|---|
| Fahrbasis und Encoder | ESS23-Encoderpfad, Nav2, LiDAR, VL53 und Mehrraum-Explorer sind auf der Integrationslinie vorhanden. | Mainline-PR bauen und testen; keine alte Teil-PR einzeln nach `main` mergen. |
| Diagnostik und Selbstbefreiung | Plan als PR #7 gegen `fix/polygon-footprint-wohnung`. | Dokumentations-PR in die Integrationslinie uebernehmen, bevor die Mainline-PR erstellt wird. |
| Arm-Integration | Physischer Arm vorhanden; Produktionstreiber, Homing, echtes URDF und ROS-2-Control sind noch nicht integriert. | M0 plus read-only M1 aus `INTEGRATIONSPLAN_ARM_SOFTWARE.md`; keine Mehrachsbewegung vor Achsprotokollen. |
| OAK-Hand-Auge-Kalibrierung | Recorder und Loeser existieren; reale Arm-/TF-Voraussetzungen fehlen noch. | Erst Armmodell, `/joint_states`, TCP und Zeigetest abnehmen; danach kalibrieren. |
| App und semantische Karte | Bestehende passive Funktionen bleiben Bestandteil der Integrationslinie. | Gegen aktuelle Mainline testen, nicht gegen den Juli-Status. |

## Sicherheitsrahmen

- `/safety/estop` mit `true` bedeutet Not-Aus aktiv und blockiert softwareseitige Bewegungsfreigaben.
- Die hardwired Sicherheitskette bleibt primaer; die Software ersetzt sie nicht.
- Reale Basisfahrt und Armfahrt bleiben getrennte, explizit freigegebene Schritte.
- Greifen und Kamera-Feinpose verwenden `base_link`, nicht `map`.
- Keine direkte Bewegungssteuerung ueber historische `JointState`-Command-Topics oder unbestaetigte ESS17-Registerannahmen.

## Dokumentationsstruktur

- Aktuelle Navigation: [`docs/README.md`](docs/README.md)
- Evidenz- und Entscheidungslog: [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md)
- Historische Juli-Unterlagen: [`docs/archive/2026-07/`](docs/archive/2026-07/)
- Der fruehere Root-Pruefplan und seine Ergebnisse bleiben archiviert, sind aber keine heutige Freigabe.
- Der fruehere Status-Snapshot liegt unter [`docs/archive/2026-07/PROJEKT_STATUS_2026-07-09.md`](docs/archive/2026-07/PROJEKT_STATUS_2026-07-09.md).

## Branch-Regeln nach der Konsolidierung

1. `main` ist die einzige Startbasis fuer neue Entwicklungsbranches.
2. Ein Branch hat genau ein Thema und eine klar definierte Zielbasis.
3. Hardwareaenderungen, Dokumentationsaufrraeumungen und Featurearbeit werden getrennt reviewed.
4. Nach Merge werden vollstaendig enthaltene Branches geloescht; offene PRs werden nicht dauerhaft als historische Ablage verwendet.
5. Messdaten und abgeschlossene Pruefprotokolle gehen nach `docs/archive/<jahr-monat>/`, nicht in die Root-Ebene.

## Unmittelbare Reihenfolge

1. Dokumentations-Aufraeumbranch fertigstellen.
2. Diagnostik- und Arm-Dokumentationsbranches in die Integrationslinie aufnehmen.
3. Eine konsolidierte PR von der aktuellen Integrationslinie nach `main` erstellen.
4. CI und Jetson-Abnahme laufen lassen.
5. Nach erfolgreichem Merge `main` als neue Entwicklungsbasis verwenden und ueberholte Draft-PRs/Branches geordnet schliessen.
