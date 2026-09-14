# Wohnungserkundung – laufender Status und Entscheidungen

**Vorhaben WE-1 · Aktualisiert: 2026-09-14**

Dies ist der einzige laufende Fortschrittsstand des Vorhabens. Die
[Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md) beschreibt das Soll,
die [Roadmap](MEILENSTEINE.md) die Abnahmen und der
[Agentenauftrag](AGENTENAUFTRAG.md) den Arbeitsablauf. Historische Logs bleiben
Quellen, aber ersetzen diesen statusbezogenen Einstieg nicht.

## 1. Aktueller nächster Schritt

**WE-M0/A – reine Bestands- und Integrationsprüfung.** Main, HWT-Referenz und
verfügbaren lokalen Installationsstand vergleichen, vorhandene Karten-/Semantik-
verträge prüfen und den kleinsten nächsten Integrations-/Prüfschritt dokumentieren.
Noch keine neue Fahrsoftware, Geräteaktivierung oder funktionale Branchübernahme.

Eine Wiederholung des Arbeitszimmer-Flur-Laufs gehört zu WE-M0/B und benötigt
zusätzlich Zielsystemprüfung, sicheren Aufbau und eine neue ausdrückliche
Freigabe. Das Schreiben oder Veröffentlichen dieses Plans erteilt diese nicht.

## 2. Git- und Evidenzbasis

| Referenz am 14.09.2026 | Nachgewiesener Umfang |
|---|---|
| Main `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1` | Remote gelesen; Elternbasis des Dokumentationszweigs. |
| HWT `1d91229dc10ff4bb791938d49aae8e9808a5dfff` auf `codex/hwt601-encoder-shadow` | Remote-Referenz und eingecheckter Bericht gelesen; nicht pauschal nach Main übernommen. |
| Jetson-Installation und lokale Rohdaten | In diesem Dokumentationsauftrag nicht ausgelesen oder unabhängig verifiziert. |

Der [Bericht vom 11.09.2026](https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/docs/PROJECT_MEMORY.md)
dokumentiert den physischen Übergang vom Arbeitszimmer in den Flur mit
Nutzerbestätigung und anschließendem weiteren Umsehen. Er dokumentiert auch die
erneute Erkennung desselben Portals nach Geometrieänderung. Die abschließende
Softwarekorrektur ist dort mit 80 Explorer-Tests und Build-Erfolg angegeben,
aber ausdrücklich noch nicht erneut real gefahren.

Dies sind historische, im Repository berichtete Nachweise. Der neue Plan
setzt weder diese Tests noch den gesamten Wohnungslauf eigenständig auf bestanden.

## 3. Meilensteinstand

| Stufe | Stand | Fehlender Nachweis / nächste Abgrenzung |
|---|---|---|
| WE-D0 | Dokumentiert; zur Review | Dokumentationszweig/PR ist nicht automatisch Main oder Jetson-Deployment. |
| WE-M0/A | Geplant | Gezielter Code-/Installationsvergleich und bestätigte Integrationsbasis. |
| WE-M0/B | Offen | Neue Baseline-/Lastprüfung und reale Wiederholung der Abschlusskorrektur. |
| WE-M1 | Geplant | Stabile Portalidentität samt Negativtests. |
| WE-M2 | Geplant | Regionsgraph und passive Integration. |
| WE-M3 | Geplant | Hierarchische Policy, Abschlussvertrag und motorlose Abnahme. |
| WE-M4 | Geplant | Arbeitszimmer → Flur → weiteres Zimmer → derselbe Flur. |
| WE-M5 | Geplant | Versionsgebundene Persistenz und sichere Wiederaufnahme. |
| WE-M6 | Geplant | Wiederholbarer Abschluss des zugänglichen Wohnungsumfangs. |
| WE-M7 | Geplant, ergänzend | App-Transparenz und manuelle Benennung. |

## 4. Bekannte offene Punkte

**Codebasis:** Main und HWT-Erprobungszweig unterscheiden sich. Welche Abhängigkeiten
für die nächste Implementierung übernommen werden müssen, ist noch zu prüfen.
Ein Dokumentationsmerge nimmt diese Funktionen nicht mit.

**Baseline:** Die nach dem letzten Realtest geänderte Abschlusslogik ist laut
Referenz noch nicht erneut physisch abgenommen.

**Ressourcen:** Der letzte Bericht nennt TF-Zukunftsextrapolationen und verpasste
Controllerzyklen unter SLAM-Last. Aktuellen Zustand messen, nicht aus alten Werten
als erledigt betrachten.

**Identität und Abschluss:** Ein begrenzter Portalzähler ist noch kein stabiles
Raum-/Türgedächtnis. Die Roadmap legt den allgemeinen Vertrag fest; sie behauptet
nicht, dass das neue Datenmodell bereits im Code existiert.

**Kartenintegration:** Manuelle Raum-Overlays, Fingerprints und Speicherverträge
existieren. Die Zuordnung automatischer Erkundungsregionen und laufender Karten-
revisionen muss diese erhalten; konkrete Schema-/API-Erweiterungen sind noch offen.

**Abnahmegrenzen:** Grenzwerte für Identitätszuordnung, Beobachtungsfenster,
Ressourcenbudgets und Wohnungsumfang müssen vor den jeweiligen Tests begründet
festgelegt werden. Die Dokumentation ist kein Ersatz für diese Messungen.

## 5. Entscheidungslog

### 2026-09-14 – WE-1 als schrittweises Vorhaben festgelegt

**Entscheidung:** Bestehende Frontier-Erkundung um dauerhaftes Portalgedächtnis,
vorläufigen Raumgraphen und Flur-/Raumstrategie ergänzen; Nav2, Sensorfusion und
Sicherheitsausführung bleiben die Basis. Umsetzung in WE-M0 bis WE-M7 statt
Gesamt-Neuentwicklung in einem Agentenlauf.

**Grund / Evidenz:** Nutzer hat diese Strategie bestätigt. Die eingecheckte
HWT-Erprobung belegt einen Raumwechsel und eine spätere Portal-Doppelerkennung.
Das rechtfertigt die gezielte Identitäts-/Rückwegerweiterung, nicht eine bereits
bestandene Vollwohnungserkundung.

**Betroffene Dateien und Hardware:** Nur Strategie, Agentenkontext, Roadmap,
Status und Dokumenteinstiege; alter Strategiestand historisch erhalten.
Keine Geräte, ROS-Prozesse, Parameter, Treiber oder funktionalen Branches geändert.

**Teststatus:** Dieser Eintrag ist eine Planentscheidung. Neue Runtime-, ROS-,
Jetson- und Fahrtests wurden für die Dokumentation nicht ausgeführt. Tatsächliche
Dokumentations-/Remote-Prüfungen werden im zugehörigen PR dokumentiert.

**Offene Risiken:** Integrationsbasis, Baseline-Nachtest, Ressourcenlast und
geplante neue Logik wie oben. Kein universeller Vollständigkeits- oder
Sicherheitsnachweis allein durch diesen Plan.

**Rückfallweg:** Nur den Dokumentationscommit zurücknehmen. Der bisherige
Strategiestand liegt unverändert im Archiv; Roboterlaufzeit bleibt unberührt.

## 6. Pflege nach jedem Arbeitsschritt

Nächsten Schritt, betroffene Statuszeilen und neue Evidenz aktualisieren; keine
vorweggenommenen Gesamthäkchen. Planabweichungen und relevante Entscheidungen hier
mit Datum, Grund, Code-/Dokumentenstand, Tests, offenen Risiken und Rückfallweg
festhalten. Übergreifende Projektentscheidungen zusätzlich mit Verweis in
`docs/PROJECT_MEMORY.md`, echte Betriebsänderungen in `docs/ROBOT_TRANSFER.md`.

Nach Merge/Deployment den nachgewiesenen Stand ausdrücklich eintragen. Ein alter
Commit in dieser Tabelle ist eine Referenz und kein Auftrag, spätere Arbeit auf
diesen Stand zurückzusetzen. Keine privaten Wohnungsgeometrien oder Rohdaten
in diesen Status kopieren.
