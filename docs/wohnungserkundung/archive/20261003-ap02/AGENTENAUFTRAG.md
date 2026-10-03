# Aktueller Agentenauftrag: AP-02

Am 03.10.2026 ausdrücklich durch Nutzer „okay erledige AP-02“ beauftragt.
Verbindlich: [MASTERPLAN v1.3](MASTERPLAN.md), [STATUS](STATUS.md), AGENTS,
LAB-1 und die betroffenen WE-Meilensteine. Der abgeschlossene AP-01-Auftrag
samt Übergabe ist [bytegleich archiviert](archive/20261003-ap01/AGENTENAUFTRAG.md).

## Basis und Ziel

Sauberer AP-01-Abschluss `45f268a` auf `08a4b9a`, eigener Branch
`fix/map-lifecycle-source-contract`, Worktree `/workspace/Roboter_ws-ap02`.
WE-D0/WE-M0; betroffene Quellen-, Recovery- und metrische Anteile von WE-M3.
Softwareabschluss ausschließlich AP-02: expliziter Kartenlebenszyklus und
konsistenter Quellenvertrag, echte Regressionen, isolierter ROS-Humble-Build,
aktuelle Paket-/Interfaceauflösung und nachvollziehbare Ergebnisse.

## Begrenzte Umsetzung

Bestehende Explorer-Callbacks, MetricFrontierRuntime und StartEgressEvidence
gezielt reparieren. Kartenidentität/Sitzung/Frame/Geometrie/Revision und
verspätete Karten-/Planerarbeit prüfen. Fingerprint und Kartenmanager
wiederverwenden; nur notwendige Korrekturen dort. Vor Arrayoperationen räumliche
Evidenz invalidieren; niemals eine neue Startausnahme oder Freiraum erfinden.
Normale passend korrelierte Updates erhalten gültige Ziele mit erneuter Prüfung.

Vorhandene HWT-/Encoder-/TF-/Gate-/Explorerbudgets für Empfang, IO,
Verarbeitung, DDS-Verbrauch, Frische und Kontinuität erfassen. Aktiver und
passiver Pfad getrennt; AP-01-Stempelvertrag erhalten. Keine Fristlockerung,
kein allgemeiner Health-, DDS- oder Executorumbau. Betroffene CI-Auswahl
und Trigger bei Bedarf ergänzen.

## Abnahme und Grenzen

100×100 → 100×101 sowie Wachstum mit verschobenem Ursprung;
Auflösungs-/Sitzungs-/Framewechsel; verspätete Arbeit; Verlust notwendiger
Quelle und gültige Folgeupdates. Keine Arrayausnahme, keine falsch gültige
alte Egress-Maske und keine neue Freiraumannahme. Betroffene Tests und Build
mit echten Nachrichtenbindungen; Ergebnis und Rückfall im STATUS dokumentieren.

Keine Hardware, Aktoren, Roboternetzverbindung, Deployment, Push oder Merge.
Keine automatische AP-03-Ausführung und keine vorgezogene AP-03-/AP-04-
Geometrie-/Controller-/Frontierentwicklung. Belastbare aktive Jetson-
Zeitmessung bleibt AP-06. Rückfall: ausschließlich eigene AP-02-Commits
gezielt revertieren, AP-01 erhalten, fremde Arbeit nicht zurücksetzen.

## Softwareabschluss

AP-02 software_geprüft im Softwarecommit `96bbd4d`. Vollständiger Ergebnis-/
Grenz-/Rückfallnachweis ausschließlich im [STATUS](STATUS.md) und dessen
[Originalevidenz](evidence/ap02-20261003/README.md). 55 neue Fälle, 1.587
betroffene Tests, 116 Installtests, 1.555 colcon-Tests und Zehnpaketbuild
bestanden; Mengen überlappen. AP-03 ist nicht automatisch aktiviert.
