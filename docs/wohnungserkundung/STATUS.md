# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus / `chris01-byte/Roboter_ws` · Softwareabschluss: 2026-09-15**

Dies ist der einzige laufende WE-Status. [Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md),
[Meilensteine](MEILENSTEINE.md) und die Sicherheits-/Abnahmereihenfolge bleiben
unverändert. Der vorherige M3/U-Stand ist im
[Archiv](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md) erhalten.

## 1. Geprüfte Basis und Reviewbefund

Der Auftrag lief ausschließlich im separaten Worktree auf
`feature/we-softwareabschluss`, ausgehend von Dokumentationscommit
`56da2e3d93e2050b6178a2db5f770b746cab3512` und dessen funktionalem M3/U-Elternstand
`047455134894f700a115f6cea422479b99c702f6`. `origin/main` stand nach
`git fetch origin` auf `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1`; der getrennte HWT-Nachweis bleibt
`1d91229dc10ff4bb791938d49aae8e9808a5dfff`. Es wurde nichts gemerged.

Die laufende Roboter-Arbeitskopie `/home/p/roboter_ws` blieb auf
`feature/modulare-sensorfusion` (`00f6e521085b6cb0e38a62a029638d28195a544c`)
mit ihren vorhandenen lokalen Änderungen unangetastet. Ihr `install/` enthält
unter anderem Explorer, Kartenmanager und Semantikmanager, besitzt aber keinen
commitgebundenen Installationsnachweis; daraus wird keine Gleichheit mit diesem
WE-Stand behauptet.

Reviewt wurde die gesamte gestapelte WE-Reihe gegen `origin/main`, nicht nur
PR #92. Die Explorer-, Portal-, Regionsgraph-, Kartenmanager-, Semantik- und
Testverträge wurden reproduziert. Zwei funktionskritische Befunde wurden behoben:

- Eine neue Karte stornierte jedes aktive Ziel allein wegen ihrer Revisionsnummer.
  Jetzt darf nur ein auf der neuen exakten Produktionsquelle identitäts- und
  metrisch gleich bestätigtes Ziel weiterlaufen; geänderte, fehlende oder zu lange
  ungeprüfte Evidenz storniert weiterhin.
- Der natürliche Abschluss war nach bestätigter Durchfahrt durch dauerhaft
  `unknown` bleibende Portalseiten blockiert. Ausschließlich eine vollständig
  validierte Chassisdurchfahrt setzt beide Seiten auf `open`; ein Nav2-Erfolg allein
  reicht weiterhin nicht.

Ein kompletter `--packages-up-to`-Build bleibt auf diesem Review-PC durch die von
`/opt/ros/humble` exportierte, lokal fehlende `behaviortree_cpp`-Bibliothek im
Paket `bt_orchestrator` blockiert. Das ist ein Installations-/Underlaybefund,
kein bestandener oder fehlgeschlagener WE-Pakettest. Das geänderte Paket `explore`
wurde im isolierten Präfix erfolgreich gebaut und getestet.

## 2. Meilensteinstand

| Stufe | Nachgewiesener Stand | Verbleibende Grenze |
|---|---|---|
| WE-D0 / WE-M0/A | Strategie, Basisvergleich und Schnittstellenreview abgeschlossen. | Keine Wiederholung ohne neuen Befund. |
| WE-M0/B | Frühere Fahrbasis dokumentiert. | Reproduzierbarer Zielsystem-/Laststand und freigegebener realer Nachtest offen. |
| WE-M1 | Portalgedächtnis und In-Memory-Verträge softwaregeprüft. | Keine Hardwareaussage. |
| WE-M2 | Automatische Rohkarten-, Portal-, Frontier-, Graph- und Aufgabenbildung softwaregeprüft. | Automatische Regionskorrektur bleibt konservativ; reale Karten offen. |
| WE-M3 | **Gerätefreier Softwareumfang abgeschlossen:** automatische Zielwahl, revisionssichere Kindziele, Traversalfortschreibung und natürlicher Elternabschluss nachgewiesen. | Zielprofil, reale Last und Fahrwirkung nicht abgenommen. |
| WE-M4 | Reale Drei-Regionen-Abnahme unverändert offen. | Neue Freigabe, Not-Aus, motorlose Vorprüfung und begrenzte Fahrt erforderlich. |
| WE-M5 | **Gerätefrei abgeschlossen:** versionsgebundener, atomarer WE-Metadatenspeicher und passive Wiederaufnahme über Kartenmanagerstatus. IDs, Graph, Restaufgaben und Blockaden bleiben erhalten; Semantikdaten werden nicht geschrieben. | Zielsystem-Dateisystem und reale Wiederaufnahme offen. |
| WE-M6 | Software-Voraussetzungen zusammenhängend belegt. | Wiederholbarer Abschluss der freigegebenen realen Wohnung bleibt offen. |
| WE-M7 | Nicht begonnen; kein Kernblocker. | App-Transparenz/manuelle Benennung später, ohne Geometrie zu überschreiben. |

## 3. Gerätefreie Gesamtnachweise

Der Prozessprüfer startet den produktiven `ExploreNode` in einer isolierten
ROS-Domain mit synthetischer Karte, TF/Scan und Fake-Nav2. Er publiziert auf den
beobachteten Command-Topics keine Befehle.

| Nachweis | Ergebnis |
|---|---|
| Positiver Portalprozess | Ein automatisch gewähltes Nav2-Ziel, bestätigte Durchfahrt, atomarer Region-/Aufgabenfortschritt und **natürlicher erfolgreicher Elternabschluss**, kein Prüfer-Cancel. |
| Fehlendes passendes TF | Kindziel wird storniert; kein Eintritt, Portalaufgabe offen, erklärter Fehlerabschluss. |
| Unterbrechung/Wiederaufnahme | Expliziter Cancel → erfolgreicher Kartenmanager-Save → atomarer WE-Save → Prozessneustart → passives Laden ohne Ziel → neue Pose/Kartenrevision → neuer ausdrücklicher Auftrag → natürliche erfolgreiche Beendigung. Aufgaben-ID bleibt identisch. |
| Mehrraum/Flurrückkehr | Produktionsdetektor und Traversierungsvalidator bilden Startraum → Flur → weiteres Zimmer; nach Save/Restore führt die Rückrichtung in `region_000002`, also denselben Flur, dessen Eintrittszähler auf zwei steigt. Zwei Portal- und drei Regions-IDs bleiben stabil. |
| Frontierkette | Eine sich entwickelnde Rohkarte erzeugt automatisch einen Frontiercluster, stabile Aufgabe, Policyauswahl und metrischen Kandidaten; Fake-Nav2-Erfolg plus neuere vollständige Karte löst die Aufgabe über den Produktionsresolver. |

Die gemeinsame Regression bestand mit **1000 Tests**. `colcon test` für `explore`
bestand separat mit **848 Tests, 0 Fehlern, 0 Fehlschlägen, 0 Skips**. Der
Prozessprüfer bestand mit den Szenarien `positive`, `fault` und `resume`;
alle meldeten `command_message_count: 0`. Die neuen/geänderten reinen Module,
Tests und der Prüfer bestehen `ament_flake8` ohne Befund. Bestehende historische
Stilfehler im großen `explore_node.py` wurden nicht als funktionale Änderung
vermischt.

## 4. WE-M5-Vertrag und Pflichtfälle

WE-Metadaten liegen separat von unveränderlichen Kartenbytes und getrennt von
`semantic_map_manager`-Raumdaten. Jede Revision bindet Kartenname, Version,
Fingerprint, Breite, Höhe, Auflösung und Frame. Nur ein frischer, exakt zur
aktuellen Karte passender Kartenmanagerstatus wird akzeptiert; Speichern verlangt
zusätzlich ein erfolgreiches `save_result`.

Bestanden sind: Save/Load mit identischen Portal-/Regions-/Aufgaben-IDs,
Fingerprint- und Geometriewiderspruch, veralteter Managerstatus, fremde Karte,
beschädigte/abgebrochene Datei, unbekannte Schemaversion, Rückfall auf eine ältere
gültige Revision, idempotentes doppeltes Save-Ereignis, Neustart ohne Pose,
erhaltene blockierte Portalseite und unveränderte manuelle Semantikdatei. Laden
erzeugt weder Absicht noch Navigationsziel. Fortsetzung erfolgt erst mit neuer
gültiger Pose/Quelle und einem neuen ausdrücklichen `ExploreArea`-Auftrag.

## 5. Verbleibende konkrete Blocker und nächste Abnahme

Der vereinbarte **gerätefreie Softwareabschluss** ist erreicht. Offen sind keine
weiteren allgemeinen WE-Softwareplanungsrunden, sondern getrennte Zielsystem- und
Hardwaregates:

1. Zielsystem-Underlay/Overlay commitgebunden neu bauen; die lokal fehlende
   BehaviorTree.CPP-Bibliothek und die tatsächlich installierten Paketstände
   klären. Keine alte Mischinstallation als Nachweis verwenden.
2. Motorlos auf dem Zielsystem Topics, TF, Kartenmanager-Save/Load-Pfade,
   Dateirechte, Speicherdauer/-grenzen und parallele SLAM-/Nav2-/Sicherheitslast
   prüfen. Die historische 2-s-Quellfrist gegenüber der Statusperiode dort messen.
3. Chassis-/Portalprofil, Kreis-/Polygon-Nahbereichsvertrag und
   Kollisionsüberwachung separat begründen und abnehmen; Softwaretests sind keine
   Hardwarefreigabe.
4. Erst nach ausdrücklicher Freigabe mit Not-Aus in Reichweite WE-M0/B und WE-M4
   begrenzt fahren; anschließend WE-M6 wiederholt für den freigegebenen realen
   Wohnungsumfang abnehmen.

Automatische Regions-Split-/Merge-Entscheidungen bleiben absichtlich konservativ;
ungeklärte Korrekturen dürfen keinen erfundenen Raumabschluss erzeugen. Manuelle
Raumnamen/-daten bleiben Eigentum des Semantikvertrags und werden durch WE-M5 nie
überschrieben.

## 6. Rückfall und Nachweisgrenze

Rückfall: `wohnungserkundung_persistence_enabled: false` lässt den neuen
Dateipfad vollständig unbenutzt; `wohnungserkundung_navigation_enabled: false`
belässt die WE-Kette passiv. Der funktionale Commit kann als Ganzes zurückgenommen
werden, ohne Karten- oder Semantikdateien zu löschen. Sichtbare gültige
WE-Zustandsrevisionen werden nicht automatisch rotiert oder überschrieben.

Alle genannten Ergebnisse sind Softwarebelege mit simulierten Sensoren/Fake-Nav2.
Es wurden keine Geräte aktiviert, keine Fahrt ausgelöst, keine laufende
Roboter-Arbeitskopie gewechselt, kein Deployment ausgeführt und keine reale
Hardwareabnahme behauptet.
