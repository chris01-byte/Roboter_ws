# Aktueller Agentenauftrag: AP-06

Am 03.10.2026 durch Nutzer „gut dann mache ap-6 fertig“ ausdrücklich beauftragt. Verbindlich: [MASTERPLAN v1.3](MASTERPLAN.md), [STATUS](STATUS.md), AGENTS, LAB-1 und WE-M0/M3/M4/M5/M6/M7. [AP-05-Auftrag bytegleich archiviert](archive/20261003-ap05/README.md).

## Basis und Lieferung

Sauberer AP-05-Abschluss `6a4a7df51c3ed152edb82ffa8b7dce5f1020f8e4`, eigener Branch `feature/ap06-closed-product-validation`, Worktree `/workspace/Roboter_ws-ap06`. Bestehende Mission/BT/Explorer/Nav2/SLAM-Kette vollständig in geschlossener Simulation prüfen, Sensoren aus tatsächlich simulierter Bewegung; danach soweit verfügbar exakten Kandidaten am Zielsystem und im begrenzten bestehenden Laborumfang prüfen. Nachgewiesene Integrationsfehler begrenzt beheben, Regressionen/CI, isolierter echter Build und Originalnachweise. Kein FakeNav2/Replay als Ersatz der Gesamtprüfung, keine versteckten Ziele oder Wahrheitskarte im Explorer.

## Vorab festzuhaltende Abnahme

Synthetische Referenzwelt mit zwei Räumen und Verbindung/Flur, enge Passage (68-/80-cm-Vergleich), Hindernis mit Umweg, blockierter Alternative, beobachtungsbedingtem Kartenwachstum und ehrlichem Abschluss. Mindestens drei verschiedene zulässige Startposen vorher im unveränderlichen Szenariomanifest festlegen; jeder Positivlauf ohne manuelle Nav-Ziele. Geometrie-/Scope-/Kontur-/Quellen-/HOLD-/Einzelkind-/Cancel-/Stillstandsbedingungen und absolute Budgets erhalten. Echte BT-, NavigateToPose-/Plan-/Controller- und SLAM-Instanzen; Welt liefert allein physische Sensormodelle/Odometrie, unabhängiger Prüfer misst volle Passage, Kartentreue, neue Beobachtung und Schutzreaktionen. Teilstände nicht als Positivläufe zählen. Alle fehlgeschlagenen Kriterien und Originalbelege bewahren.

Zielsystem zuerst rein lesender Vorlauf: tatsächliche Basis/Änderungen/Installpräfixe, Gerätebesitzer und gültige Quellen/TF/Stillstand/Schutzkette prüfen. Erst nach bestandenem softwareseitigen und technischen Vorlauf begrenzter realer Ablauf Kaltstart → mindestens drei autonome Beobachtungsaufgaben → ganze Passage/Heck → Weiterarbeit → WE-M4-Rundweg, Hindernis/Halt in passenden getrennten Aufbauten. WE-M6 mindestens zwei beaufsichtigte Positivläufe/andere Startpose; aktuelle echte Verbraucherlast und Gerätebesitzerwechsel, konsistentes Speichern/Wiederaufnahme belegen. Konkrete Laufbudgets und Eingriffs-/Abbruchkriterien vor Start; keine automatischen Neustartserien. LAB-1 enthält bestehende Betreibererklärung, keine erfundene Hardwarestellung. Native iOS-Prüfung separat unter WE-M7 führen.

## Bekannter Zugangsbefund und Grenzen

Bei Beauftragung aktuelle Cloud-Konfiguration revision 39: keine VPN-Konfiguration, keine freigegebenen TCP-Domains/IP-Bereiche, keine bereitgestellten SSH-/Robotercredentials. Zielsystem-/physische Schritte davon abhängig; keine Umgehung der Netzwerkpolicy. Zugang konkret angefragt, alle unabhängigen Softwarearbeiten weiterführen. Native Apple-Plattform ebenfalls nicht verfügbar. Diese Befunde verhindern kein unabhängiges Simulations-/Softwareergebnis, erlauben aber keine vollständige physische AP-06-Abnahmebehauptung.

Kein Push/Merge, dauerhafter Jetson-Install-/Autostartwechsel oder Rechner-Shutdown. Private reale Karten/Bilder/Bags/Manifeste bleiben lokal außerhalb Git. Bestehende Checkouts/fremde Arbeit bewahren. Rückfall nur eigene AP-06-Commits gezielt revertieren bzw. eigenes temporäres Overlay geordnet abwählen; AP-01–05 und bestehende Schutzkette erhalten. Genau ein aktueller STATUS und nächster Schritt.
