# Aktueller Agentenauftrag: AP-03

Am 03.10.2026 ausdrücklich durch Nutzer „Gut, wenn soweit alles io. ist begeinne mit AP-03“ beauftragt. Verbindlich: [MASTERPLAN v1.3](MASTERPLAN.md), [STATUS](STATUS.md), AGENTS, LAB-1 und WE-M3. [AP-02 ist bytegleich archiviert](archive/20261003-ap02/AGENTENAUFTRAG.md).

## Basis und Ziel

Sauberer AP-02-Abschluss `875c7c4`, eigener Branch `fix/nav2-bootstrap-geometry`, Worktree `/workspace/Roboter_ws-ap03`. AP-01-Zeitvertrag und AP-02-Kartenlebenszyklus erhalten. Ausschließlich AP-03: Bewegung und autonomen Start zusammenführen, gezielte vorhandene Explorer-/Nav2-Geometriekorrekturen, Regressionen, echter isolierter Build und nachvollziehbare gerätefreie Ergebnisse.

## Umsetzung und Abnahme

Vorhandene echte Nav2-Planer und Controller mit asymmetrischem Chassis, Achsbezug, Rasterreserve, Drehen, Rückwärtsanteil und gemessener Trackingabweichung gemeinsam prüfen. Ein einzelner ungeeigneter kürzester Eigenpfad darf ein über längeren Weg zulässiges Ziel nicht dauerhaft ausschließen. Keine bloße Reserveentfernung.

Geschlossene synthetische Pflichtfälle: Hindernis mit längerer Umfahrung; gerade 68-cm- und 80-cm-Durchfahrt; unzulässiges Drehen im engen Durchgang; freier Zielbereich hinter der Tür; beobachteter und unbekannter Außenraum. Positive schmale Durchfahrt mit echtem Nav2-Planer und Controller ausführen; Trackingabweichung, Footprintabstände und erreichte beobachtete Fläche messen. Vorbestimmte Ziele sind nur Komponententests, keine autonome Erkundung. Simulationsmodell ist kein Nachweis für reale Hardware.

Bootstrap trennt eigenen bekannten Körper und unbeobachteten Außenraum. Erste Beobachtungsbewegung nachweisen oder konkret fehlende Beobachtung benennen. Vollrotation nur bei zulässiger Geometrie. Fehlende Sensorabdeckung mit begründetem separatem Sensorpositions-/Abdeckungspaket vorbereiten; keine identischen Startwiederholungen.

## Grenzen und Rückfall

Keine Hardware, Roboternetzverbindung, Deployment, Push oder Merge. Kein automatischer AP-04-Übergang, kein neuer Navigator/Supervisor, kein neuer Frontier-Kern. Physische Tür-/Startabnahme bleibt offen. Rückfall ausschließlich eigene AP-03-Commits revertieren; AP-01/AP-02 und fremde Arbeit erhalten. Tatsächliche Blocker konkret dokumentieren und unabhängige Schritte weiterführen.

## Softwareabschluss

AP-03 software_geprüft im Softwarecommit `c3115ff`; Umfang, Originalbelege, beobachtete Timinggrenzen, reale offene Abnahmen und Rückfall ausschließlich im [STATUS](STATUS.md) und der [AP-03-Evidenz](evidence/ap03-20261003/README.md). 22 neue Fälle; 1.609 betroffene, 138 installierte und 1.577 colcon-Tests bestanden; echte Zehnpaket-/native Nav2-Builds und Achtfallmatrix. Simulationsprofil nicht für Hardware qualifiziert oder aktiviert. Kein automatischer AP-04-Übergang.
