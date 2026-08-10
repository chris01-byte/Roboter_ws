# Isolierte Roboter-Integrationen

Dieses Verzeichnis trennt neue Roboterfunktionen vom übrigen, möglicherweise
bereits geänderten Arbeitsbaum. Jede Übertragung auf den echten Roboter erhält
eine eigene Integrations-ID und einen eigenen Unterordner.

## Aktueller Stand

- `amadeus_map_v1` ist das abgeschlossene Kartenmanager-Release vom
  26.07.2026. Es bleibt als unveränderlicher historischer Ausgangsstand
  erhalten.
- `amadeus_slam_localization_20260727` dokumentiert den danach ausschließlich
  auf dem Jetson entstandenen realen SLAM-/Lokalisierungsstand. Diese Stufe ist
  noch kein übertragbares Release, weil Commit `390fcec`, die zugehörigen
  Dateien und die Laufzeitdaten noch nicht hashgesichert auf diesem
  Datenträger vorliegen.

Das Release von `amadeus_map_v1` darf nicht blind auf den neueren Jetson-Stand
angewendet werden. Zuerst ist die neue Integrationsakte abzuarbeiten.

## Verbindlicher Aufbau

```text
integration/<integrations-id>/
├── GEDAECHTNISPROTOKOLL.md       Zweck, Entscheidungen und bekannte Grenzen
├── HARDWARE_AKTIVIERUNGSPLAN.md sichere Prüf- und Freigabereihenfolge
├── baseline.json                 dokumentierter Ausgangsstand
├── release-spec.json             ausschließlich erlaubte Robot-Zieldateien
└── RELEASE.json                  Ergebnis, Archiv-Hash und Teststatus
```

`RELEASE.json` entsteht erst nach erfolgreicher Prüfung und Paketerzeugung.
Weitere integrationsspezifische, rein lesende Inventurskripte sind zulässig.

## Übertragungsregel

Maßgeblich ist niemals der gesamte Git-Diff und niemals ein pauschaler
Workspace-Abgleich. Maßgeblich sind nur:

1. die expliziten Einträge in `release-spec.json`,
2. das daraus erzeugte und intern geprüfte Release,
3. dessen separat protokollierter Archiv-SHA-256,
4. ein erfolgreicher Dry-run auf dem tatsächlichen Zielsystem.

Die Werkzeuge liegen unter `tools/robot_transfer`. Sie verändern weder ROS
noch Motorzustände und schützen Build-, Git-, iOS- und Karten-Laufzeitdaten.

## Vorgehen für spätere Agenten

1. Vorhandene Integrationsakten und den aktuellen Arbeitsbaum lesen.
2. Neue Arbeit unter einer neuen Integrations-ID beginnen.
3. Bereits vorher geänderte Dateien als fremden Altbestand klassifizieren.
4. Nur notwendige Laufzeitdateien in die Release-Spezifikation aufnehmen.
5. Tests, offene Hardwareannahmen und Sicherheitsgrenzen dokumentieren.
6. Release auf einem normalen macOS-/Linux-Dateisystem erzeugen und als
   geprüftes Archiv auf den USB-Datenträger packen.
7. Auf dem Roboter zuerst Inventur und Dry-run ausführen; Drift bedeutet
   Abbruch und erneute Prüfung, nicht Überschreiben.
