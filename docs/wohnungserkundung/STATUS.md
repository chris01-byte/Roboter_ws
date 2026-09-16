# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus / `chris01-byte/Roboter_ws` · Gerätefreier Softwareabschluss: 2026-09-16 · nachgewiesen**

Dies ist der einzige laufende WE-Status. [Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md),
[Meilensteine](MEILENSTEINE.md) und die Sicherheits-/Abnahmereihenfolge bleiben
unverändert. Der vorherige M3/U-Stand ist im
[Archiv](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md) erhalten.

## 0. Gerätefreier Abschlusscheck 2026-09-16

Der Check und die Korrektur liefen ausschließlich im separaten Worktree
`feature/we-transit-return`, ausgehend vom Reviewstand
`05d28f0a2ce5e7a6d100f3b52064d8399955102d` (PR #94, gestapelt auf PR #93).
Die Behebung liegt in `5e7ba9ea2dca25a0f51676bf78e884f59e966678`; die laufende
Roboter-Arbeitskopie blieb unverändert. `git fetch origin` hatte keinen neueren
abgestimmten WE-Stand ergeben. Es gab keinen Merge.

Der bisherige Mehrraumblocker ist behoben. Nach einer bestätigten Durchfahrt
schließt der Regionsgraph nur die offene, zur Zielregion passende Portalaufgabe.
Bleibt in der verlassenen Region echte Arbeit offen, erzeugt er eine einmalige
revisionsgebundene `TRANSIT`-Aufgabe für dieselbe Portal-ID. Die Ankunft über
diese Aufgabe schließt genau sie; Transitaufgaben erzeugen keine Ping-Pong-
Rückwege. Mehrdeutige Transitaufgaben bleiben nicht auswählbar. Der vorhandene
Portal-Evidenz- und Traversalpfad ist ihr konkreter Verbraucher: `ExploreNode`
akzeptiert sie nur mit frischer Karten-, Scope-, Portal- und Routen-Evidenz.
Eine Aufgabe kann nicht auf der Revision gewählt werden, auf der sie entstand;
ohne eine neuere Quelle bleibt sie gesperrt. Die Statusprojektion verwendet
außerdem die neueste Portal-/Graphrevision, statt einen frisch fortgeschriebenen
Traversalstand fälschlich als veraltet zu melden.

Der vorhandene isolierte ROS-Prozessprüfer bestand in ROS-Domain 215 mit
synthetischer Karte, TF/Scan und Fake-Nav2. Er belegt die Produktionskette
Startraum → Flur → weiteres Zimmer → Unterbrechung → atomarer Kartenmanager-
und WE-Save → Neustart → passives Laden ohne Ziel → neue Pose/Quelle → neuer
ausdrücklicher Auftrag → derselbe Flur → Frontierabschluss → natürlicher
erklärter Elternabschluss. Die Rückkehraufgabe wurde automatisch gewählt,
behielt ihre ID über den Neustart und wurde erst durch den vorhandenen
Durchfahrtsmonitor bestätigt. Der Prüfer gab keine Fahrbefehle aus
(`command_message_count: 0`). Der bisherige Positiv-, Fehler- und
Einportal-Wiederanlauffall bestehen ebenfalls.

**WE-1 gerätefreier Softwareabschluss: nachgewiesen auf der genannten
Entwicklungsbasis.** Dies ist weder eine Main-Integration noch ein
Installations-, Zielsystem- oder Hardwareabnahmenachweis.

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
| WE-M3 | Automatische Zielwahl, revisionssichere Kindziele, Traversalfortschreibung und natürlicher Mehrraum-Elternabschluss sind gerätefrei geprüft. Der Rückweg entsteht als versionsgebundene Transitaufgabe und wird über den vorhandenen Portalpfad automatisch ausgewählt. | Zielprofil, reale Last und Fahrwirkung sind getrennt offen. |
| WE-M4 | Reale Drei-Regionen-Abnahme unverändert offen. | Neue Freigabe, Not-Aus, motorlose Vorprüfung und begrenzte Fahrt erforderlich. |
| WE-M5 | Versionsgebundener, atomarer WE-Metadatenspeicher und passive Wiederaufnahme über Kartenmanagerstatus sind im vollständigen Mehrraum-Rückweg geprüft. Portal-, Regions- und offene Transit-IDs bleiben erhalten; Semantikdaten werden nicht geschrieben. | Zielsystem-Dateisystem und reale Wiederaufnahme offen. |
| WE-M6 | Die gerätefreie Softwarekette ist zusammenhängend belegt. | Wiederholbarer Abschluss der freigegebenen realen Wohnung bleibt offen. |
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
| Mehrraum/Flurrückkehr/Wiederanlauf | Der produktive `ExploreNode` bildet Startraum → Flur → weiteres Zimmer. Danach: expliziter Cancel, atomarer Save, Prozessneustart ohne Autostart, neue Pose/Karte und neuer Auftrag. Die automatisch gewählte erhaltene Transitaufgabe führt durch dieselbe Portal-ID in den Flur zurück; Eintrittszähler 3, Transit- und Frontieraufgabe abgeschlossen, natürlicher Elternabschluss. |
| Frontierkette | Eine sich entwickelnde Rohkarte erzeugt automatisch einen Frontiercluster, stabile Aufgabe, Policyauswahl und metrischen Kandidaten; Fake-Nav2-Erfolg plus neuere vollständige Karte löst die Aufgabe über den Produktionsresolver. |

Die direkte Paketregression und `colcon test` für `explore` bestanden jeweils mit
**857 Tests, 0 Fehlern, 0 Fehlschlägen, 0 Skips**. Der Prozessprüfer bestand mit
`positive`, `fault`, `multiroom` und `resume`; alle vier Szenarien meldeten
`command_message_count: 0`. Die erweiterten reinen Module, Tests und der Prüfer
bestehen `ament_flake8` ohne Befund. Bestehende historische Stilbefunde im großen
`explore_node.py` wurden nicht als fachliche Änderung vermischt.

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

Im vereinbarten **gerätefreien Softwareumfang besteht kein offener funktionaler
Blocker**. Vor einer Integration oder Hardwarearbeit bleiben getrennte Gates:

1. Den Branch reviewen und nach ausdrücklicher Freigabe nach `main` integrieren;
   kein automatischer Merge.
2. Zielsystem-Underlay/Overlay commitgebunden neu bauen; die lokal fehlende
   BehaviorTree.CPP-Bibliothek und die tatsächlich installierten Paketstände
   klären. Keine alte Mischinstallation als Nachweis verwenden.
3. Motorlos auf dem Zielsystem Topics, TF, Kartenmanager-Save/Load-Pfade,
   Dateirechte, Speicherdauer/-grenzen und parallele SLAM-/Nav2-/Sicherheitslast
   prüfen. Die historische 2-s-Quellfrist gegenüber der Statusperiode dort messen.
4. Chassis-/Portalprofil, Kreis-/Polygon-Nahbereichsvertrag und
   Kollisionsüberwachung separat begründen und abnehmen; Softwaretests sind keine
   Hardwarefreigabe.
5. Erst nach ausdrücklicher Freigabe mit Not-Aus in Reichweite WE-M0/B und WE-M4
   begrenzt fahren; anschließend WE-M6 wiederholt für den freigegebenen realen
   Wohnungsumfang abnehmen.

Automatische Regions-Split-/Merge-Entscheidungen bleiben absichtlich konservativ;
ungeklärte Korrekturen dürfen keinen erfundenen Raumabschluss erzeugen. Manuelle
Raumnamen/-daten bleiben Eigentum des Semantikvertrags und werden durch WE-M5 nie
überschrieben.

## 6. Rückfall und Nachweisgrenze

Rückfall: `wohnungserkundung_persistence_enabled: false` lässt den neuen
Dateipfad vollständig unbenutzt; `wohnungserkundung_navigation_enabled: false`
belässt die WE-Kette passiv. Der funktionale Commit `5e7ba9e` kann als Ganzes
zurückgenommen werden, ohne Karten- oder Semantikdateien zu löschen. Sichtbare gültige
WE-Zustandsrevisionen werden nicht automatisch rotiert oder überschrieben.

Alle genannten Ergebnisse sind Softwarebelege mit simulierten Sensoren/Fake-Nav2.
Es wurden keine Geräte aktiviert, keine Fahrt ausgelöst, keine laufende
Roboter-Arbeitskopie gewechselt, kein Deployment ausgeführt und keine reale
Hardwareabnahme behauptet.
