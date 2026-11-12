# Projektstatus: Roboter_ws

**Gesamtstatus:** 2026-08-19. **Arm-Ergänzung:** 2026-10-10.

**Geltung:** `main` ist die aktuelle Entwicklungsbasis. Detaillierte Entscheidungen und Messnachweise stehen in [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md); die Dokumentationsnavigation steht in [`docs/README.md`](docs/README.md).

---

## Arm-Ergänzung vom 10.10.2026

Zuerst ausschließlich Arm-Inbetriebnahme. Auf dem Entwicklungsbranch
`feature/arm-commissioning-foundation` ([PR #106](https://github.com/chris01-byte/Roboter_ws/pull/106),
noch nicht in main) sind Inventarprüfung, Fake und reine ESS17-Leseprobe
implementiert. 32 Tests sowie Installation und Humble-Build bestanden auf
9e65e4f; reale Armabnahme steht aus. Keine Bewegung oder Homing implementiert.

[Kontext](docs/ARM_KONTEXT.md), [Stufenplan](docs/INTEGRATIONSPLAN_ARM_SOFTWARE.md)
und [Messblatt](docs/ARM_INBETRIEBNAHME_MESSBLATT.md) wurden aus Gespräch und
Repo rekonstruiert. Fünf ESS17-RS07, ein noch unbestimmter NEMA23, TLE4905L,
XL330-Spindelgreifer und sensorfreie Fahrpose sind berücksichtigt.
Nächster Schritt: M0 vervollständigen, danach beaufsichtigte M1A-Leseprobe.
Die übrige Gesamtstatus-Zusammenfassung bleibt auf ihrem bisherigen Datum.

## Kurzfassung

- PR #10 hat die vollstaendige, zuvor gestapelte Integrationslinie nach `main` gebracht.
- Die automatisierten Mainline-Checks sind gruen: `python-contracts`, `swift-contracts` und `offline-tests` (3/3).
- Historische Juli-Pruefplaene und Statussnapshots liegen nun unter `docs/archive/2026-07/`.
- Historische Draft-PRs und ihre vollstaendig enthaltenen Branches wurden geschlossen bzw. geloescht.
- Die Konsolidierung hat keine Hardwarebewegung oder neue Hardwarefreigabe ausgeloest.

## Aktueller Entwicklungsstand

`main` enthaelt Fahrbasis, Encoder-Odometrie, STL-27L, VL53-Nahbereichsschutz, Navigation, Lokalisierung, Mehrraum-Erkundung, Missionslogik, semantische Karte, iOS-/Web-Bedienung sowie die Dokumentationsplaene fuer Arm und Diagnostik.

Die aktuelle Projektstruktur ist damit wieder einfach:

```text
main
  -> neue, klar abgegrenzte Themenbranches
  -> Pull Request mit Tests und Rueckfallweg
  -> Merge nach main
  -> Branch loeschen
```

## Verbleibende Betriebsabnahme

Die CI beweist den automatisierten Quellvertragsstand, ersetzt aber keine reale Zielsystemabnahme. Vor einer neuen scharfen Hardwarefreigabe sind weiterhin erforderlich:

1. Betroffene ROS-2-Humble-Pakete auf dem Jetson bauen und testen.
2. Launch-, Schnittstellen- und Sicherheitskonfiguration gegen die reale Hardware pruefen.
3. Den jeweils passenden dokumentierten Rueckfallweg bereithalten.
4. Reale Bewegung nur mit ausdruecklicher Freigabe, Aufsicht und hardwired Not-Aus.

Diese Punkte sind Betriebs- und Sicherheitsgates, nicht Hindernisse fuer weitere rein softwareseitige Entwicklungsarbeit auf `main`.

## Aktive fachliche Arbeit

| Bereich | Status | Naechster sicherer Schritt |
|---|---|---|
| Fahrbasis und Navigation | In `main` konsolidiert. | Jetson-Regression der betroffenen Pakete vor der naechsten realen Fahrfreigabe. |
| Diagnostik und Selbstbefreiung | Plan in [`docs/INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md`](docs/INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md). | Separat, read-only und motorlos implementieren. |
| Arm-Integration | Read-only Build A auf PR #106; Montagezustand offen. Bewegungsansteuerung, Homing und echtes Modell fehlen. | M0 und M1A gemäß [`Stufenplan`](docs/INTEGRATIONSPLAN_ARM_SOFTWARE.md); reale Messungen im [`Messblatt`](docs/ARM_INBETRIEBNAHME_MESSBLATT.md). |
| OAK-Hand-Auge-Kalibrierung | Recorder und Loeser existieren; reale Arm-/TF-Voraussetzungen fehlen noch. | Erst Armmodell, `/joint_states`, TCP und Zeigetest abnehmen; danach kalibrieren. |
| App und semantische Karte | Konsolidiert und dokumentiert. | Gegen den aktuellen `main`-Stand weiterentwickeln und testen. |

## Sicherheitsrahmen

- `/safety/estop=true` bedeutet Not-Aus aktiv und blockiert softwareseitige Bewegungsfreigaben.
- Die hardwired Sicherheitskette bleibt primaer; die Software ersetzt sie nicht.
- Reale Basisfahrt und Armfahrt bleiben getrennte, explizit freigegebene Schritte.
- Zielvertrag für Greifen und Kamera-Feinpose ist `base_link`; bestehende map-Verträge müssen vor Umsetzung abgeglichen werden.
- Keine direkte Bewegungssteuerung ueber historische `JointState`-Command-Topics oder unbestaetigte ESS17-Registerannahmen.

## Dokumentationsstruktur

- Aktuelle Navigation: [`docs/README.md`](docs/README.md)
- Evidenz- und Entscheidungslog: [`docs/PROJECT_MEMORY.md`](docs/PROJECT_MEMORY.md)
- Aktive Plaene: Arm-Software und Diagnostik/Selbstbefreiung unter `docs/`
- Historische Juli-Unterlagen: [`docs/archive/2026-07/`](docs/archive/2026-07/)

## Branch-Regeln

1. Neue Arbeit startet von `main`.
2. Ein Branch hat genau ein fachliches Thema und eine klar definierte Zielbasis.
3. Jede Aenderung enthaelt Tests und einen klaren Rueckfallweg.
4. Nach Merge wird der vollstaendig enthaltene Branch geloescht.
5. Messdaten und abgeschlossene Pruefprotokolle gehen nach `docs/archive/<jahr-monat>/`, nicht in die Root-Ebene.

## Naechste Reihenfolge

1. Jetson-Regression fuer die betroffenen Pakete auf dem aktuellen `main`-Stand ausfuehren.
2. Arm-Integration mit M0 und dem read-only Teil von M1 beginnen.
3. Diagnostik- und Selbstbefreiungsplan als separaten motorlosen Schritt umsetzen.
4. Neue Arbeit nur noch auf klar abgegrenzten Branches von `main` starten.
