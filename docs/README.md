# Dokumentation: Einstieg und Gueltigkeit

Dieses Verzeichnis trennt aktuelle Betriebs- und Entwicklungsdokumentation von historischen Pruefprotokollen. Dadurch ist klar, welches Dokument eine heutige Entscheidung steuert und welches nur einen vergangenen Nachweis bewahrt.

## Lesereihenfolge

1. [`../PROJEKT_STATUS.md`](../PROJEKT_STATUS.md) - aktueller Gesamtstatus, Integrationslinie und naechster sicherer Schritt.
2. [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) - fortlaufendes Entscheidungsprotokoll mit Evidenz, Teststatus und Rueckfallwegen.
3. Die fachliche Dokumentation zum gerade bearbeiteten System.
4. Vor Hardwarebetrieb die zugehoerige aktuelle Inbetriebnahme- oder Abnahmeanweisung.

`main` ist die Zielbasis fuer neue Arbeit, nachdem die Mainline-PR gruen geprueft und gemerged ist. Kurzlebige Themenbranches beginnen dann von `main` und erhalten genau einen klaren Zweck.

## Aktive Dokumentation

| Bereich | Dokument | Zweck |
|---|---|---|
| Entscheidungen und Evidenz | [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) | Fortlaufendes Projektgedaechtnis; neue, belegte Entscheidungen oben ergaenzen. |
| Hardware- und Betriebsuebergabe | [`ROBOT_TRANSFER.md`](ROBOT_TRANSFER.md) | Wiederholbare Jetson-/Hardwareuebergabe und Rueckfallwege. |
| Fahrbasis / Encoder | [`ENCODER_ODOMETRIE_FIX.md`](ENCODER_ODOMETRIE_FIX.md) | Bestaetigte ESS23-Encoderregeln und Abnahmeschritte. |
| LiDAR-SLAM | [`SLAM_TOOLBOX_ROTATION_FIX.md`](SLAM_TOOLBOX_ROTATION_FIX.md) | Humble-Overlay, reine Drehung und Inbetriebnahmegrenzen. |
| Wohnungserkundung | [`WOHNUNGSERKUNDUNG_STRATEGIE.md`](WOHNUNGSERKUNDUNG_STRATEGIE.md) | Frontier-, Portal- und Abschlussstrategie. |
| Zielkarte und Lokalisierung | [`ZIEL_KARTE_UND_LOKALISIERUNG.md`](ZIEL_KARTE_UND_LOKALISIERUNG.md) | Karten-/Lokalisierungsvertrag und Fail-closed Regeln. |
| Semantische Karte | [`SEMANTIC_MAP_INTEGRATION.md`](SEMANTIC_MAP_INTEGRATION.md) | Manuelle Raumdaten, Persistenz und Schnittstellen. |
| App-Livepose | [`APP_LIVE_ROBOTERPOSE_INTEGRATION.md`](APP_LIVE_ROBOTERPOSE_INTEGRATION.md) | Read-only Pose-/Lokalisierungsintegration fuer die App. |
| LiDAR-Hardware | [`hardware/STL27L_INTEGRATION.md`](hardware/STL27L_INTEGRATION.md) | STL-27L-spezifische Treiber- und Frameinformation. |
| Arm/OAK-Kalibrierung | [`../KONZEPT_KALIBRIERUNG_OAK_ARM.md`](../KONZEPT_KALIBRIERUNG_OAK_ARM.md) | Hand-Auge-Kalibrierung; erst nach echter Arm-/Encoderabnahme ausfuehren. |
| Arm-Software | [`INTEGRATIONSPLAN_ARM_SOFTWARE.md`](INTEGRATIONSPLAN_ARM_SOFTWARE.md) | ESS17-Commissioning, ros2_control, MoveIt 2, Interlocks und Meilensteine. |
| Diagnostik und Selbstbefreiung | [`INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md`](INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md) | Health-Zustaende, Ereignisprotokoll, sichere Selbstbefreiung und Supervision. |

## Dokumentklassen

### Aktuell

Aktuelle Dokumentation beschreibt den vorgesehenen oder nachweislich laufenden Zustand. Jede Anpassung nennt Datum, betroffene Komponenten, Teststatus und Rueckfallweg.

### Entscheidungsprotokoll

`PROJECT_MEMORY.md` enthaelt historische und aktuelle Entscheidungen. Alte Eintraege bleiben dort, weil sie die Begruendung fuer heutige Schutzregeln liefern. Sie sind nicht automatisch aktuelle Arbeitsanweisungen.

### Archiv

`docs/archive/` enthaelt alte Pruefplaene, Ergebnisprotokolle und Statussnapshots. Sie werden nicht geloescht, damit Messnachweise und Git-Historie nachvollziehbar bleiben. Archivdateien duerfen keine Aussage wie "einzig gueltig" oder "Single Source of Truth" mehr fuer den heutigen Betrieb beanspruchen.

## Legacy-Pruefpfad

`../pruefplan_jetson.sh` und die zugehoerigen Juli-Pruefunterlagen bleiben als historische Referenz erhalten, sind aber keine automatische Freigabe fuer den aktuellen Roboterstand. Vor einer erneuten Verwendung muss jeder aufgerufene Stage gegen die aktuelle Paketstruktur, Sicherheitskette und reale Hardware validiert werden.

Ein neuer aktueller Pruefpfad wird erst nach der Mainline-Konsolidierung aus gezielten Pakettests, Jetson-Abnahmen und den jeweils aktuellen Hardware-Checklisten abgeleitet. Er ersetzt die alte Sammelabnahme, nicht deren historische Nachweise.

## Pflege-Regeln

- Keine echten Karten, Raumgeometrien, ROS-Bags, Passwoerter oder Tokens in das Repository aufnehmen.
- Jede hardwarewirksame Aenderung verweist auf die passende Abnahme und auf einen sicheren Rueckfallweg.
- Statusdateien werden ersetzt oder archiviert, nicht parallel als mehrere angebliche Wahrheiten gepflegt.
- Neue Hauptdokumente gehoeren unter `docs/`; Dateien im Repository-Root bleiben nur dort, wenn sie direkt vom Projektwerkzeug erwartet werden.
