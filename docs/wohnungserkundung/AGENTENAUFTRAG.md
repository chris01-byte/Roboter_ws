# Aktueller Agentenauftrag: AP-06

Am 03.10.2026 durch Nutzer „gut dann mache ap-6 fertig“ ausdrücklich beauftragt. Verbindlich: [MASTERPLAN v1.3](MASTERPLAN.md), [STATUS](STATUS.md), AGENTS, LAB-1 und WE-M0/M3/M4/M5/M6/M7. [AP-05-Auftrag bytegleich archiviert](archive/20261003-ap05/README.md).

## Basis und Lieferung

Sauberer AP-05-Abschluss `6a4a7df51c3ed152edb82ffa8b7dce5f1020f8e4`, eigener Branch `feature/ap06-closed-product-validation`, Worktree `/workspace/Roboter_ws-ap06`. Bestehende Mission/BT/Explorer/Nav2/SLAM-Kette vollständig in geschlossener Simulation prüfen, Sensoren aus tatsächlich simulierter Bewegung; danach soweit verfügbar exakten Kandidaten am Zielsystem und im begrenzten bestehenden Laborumfang prüfen. Nachgewiesene Integrationsfehler begrenzt beheben, Regressionen/CI, isolierter echter Build und Originalnachweise. Kein FakeNav2/Replay als Ersatz der Gesamtprüfung, keine versteckten Ziele oder Wahrheitskarte im Explorer.

## Vorab festzuhaltende Abnahme

Synthetische Referenzwelt mit zwei Räumen und Verbindung/Flur, enge Passage (68-/80-cm-Vergleich), Hindernis mit Umweg, blockierter Alternative, beobachtungsbedingtem Kartenwachstum und ehrlichem Abschluss. Mindestens drei verschiedene zulässige Startposen vorher im unveränderlichen Szenariomanifest festlegen; jeder Positivlauf ohne manuelle Nav-Ziele. Geometrie-/Scope-/Kontur-/Quellen-/HOLD-/Einzelkind-/Cancel-/Stillstandsbedingungen und absolute Budgets erhalten. Echte BT-, NavigateToPose-/Plan-/Controller- und SLAM-Instanzen; Welt liefert allein physische Sensormodelle/Odometrie, unabhängiger Prüfer misst volle Passage, Kartentreue, neue Beobachtung und Schutzreaktionen. Teilstände nicht als Positivläufe zählen. Alle fehlgeschlagenen Kriterien und Originalbelege bewahren.

Zielsystem zuerst rein lesender Vorlauf: tatsächliche Basis/Änderungen/Installpräfixe, Gerätebesitzer und gültige Quellen/TF/Stillstand/Schutzkette prüfen. Erst nach bestandenem softwareseitigen und technischen Vorlauf begrenzter realer Ablauf Kaltstart → mindestens drei autonome Beobachtungsaufgaben → ganze Passage/Heck → Weiterarbeit → WE-M4-Rundweg, Hindernis/Halt in passenden getrennten Aufbauten. WE-M6 mindestens zwei beaufsichtigte Positivläufe/andere Startpose; aktuelle echte Verbraucherlast und Gerätebesitzerwechsel, konsistentes Speichern/Wiederaufnahme belegen. Konkrete Laufbudgets und Eingriffs-/Abbruchkriterien vor Start; keine automatischen Neustartserien. LAB-1 enthält bestehende Betreibererklärung, keine erfundene Hardwarestellung. Native iOS-Prüfung separat unter WE-M7 führen.

## Bekannter Zugangsbefund und Grenzen

Bei Beauftragung aktuelle Cloud-Konfiguration revision 39: keine VPN-Konfiguration, keine freigegebenen TCP-Domains/IP-Bereiche, keine bereitgestellten SSH-/Robotercredentials. Nutzer präzisiert: App läuft auf dem Jetson. Darauf erneut geprüft: App kennt lokales Projekt `/home/p/roboter_ws`, Shellwerkzeug liefert x86_64/Debian 13, kein `/etc/nv_tegra_release`, keine Gerätealiases und kein Zugriff auf jenen Projektpfad; Ein Terminal-Anbindungsversuch lieferte ebenfalls Cloud-Kontext; letzte Terminalabfrage keinen zugeordneten lokalen Ausführungskanal. Lokale Ausführung/Anbindung dieses Chats statt unnötiger VPN-Neueinrichtung genügt, sobald tatsächlich verfügbar. Zielsystem-/physische Schritte davon abhängig; keine Umgehung der Netzwerkpolicy. Nutzerklärung zur lokalen Jetson-App erhalten; keine erneute allgemeine Freigabe-/VPN-Frage. Alle unabhängigen Softwarearbeiten weiterführen. Native Apple-Plattform ebenfalls nicht verfügbar. Diese Befunde verhindern kein unabhängiges Simulations-/Softwareergebnis, erlauben aber keine vollständige physische AP-06-Abnahmebehauptung.

Kein Push/Merge, dauerhafter Jetson-Install-/Autostartwechsel. Private reale Karten/Bilder/Bags/Manifeste bleiben lokal außerhalb Git. Bestehende Checkouts/fremde Arbeit bewahren. Rückfall nur eigene AP-06-Commits gezielt revertieren bzw. eigenes temporäres Overlay geordnet abwählen; AP-01–05 und bestehende Schutzkette erhalten. Genau ein aktueller STATUS und nächster Schritt.

## Überprüfbarer Zwischenabschluss 04.10.2026

Software-/Prüfstand `ecb2586`, Zwölfpaketbuild, 1.844 direkte und 1.836 colcon-Tests grün; 135 installierte Produktdateien bytegleich. Echter geschlossener Endpfad enthält Scan-Normalisierung und Safety-Monitor, nativen BT/Nav2/SLAM/EKF und ursprüngliche Schutzkette. Drei Endmissionen fahren erstmals autonom an, scheitern aber vor der ersten Zielankunft an `start_egress_reference_expired`: 0/3 Gesamtpositivfälle. Getrennte Cancel-/HOLD-Stoppfälle bestanden, ACK/Fortsetzung/aktive Wiederaufnahme offen. Aktueller vollständiger Befund ausschließlich im [STATUS](STATUS.md), Originalnachweise im verlinkten Evidenzverzeichnis.

AP-06 bleibt als nächster Auftrag aktiv: Startinventar und tatsächliche SLAM-Raster-/Referenzänderungen mit frischem ganzen Fahrzeugbeweis konsistent verbinden; keine alte Referenz still re-ankern, keine neuen unbekannten Zellen freigeben oder Fristen zurücksetzen. Erst gleiche drei Gesamtmissionen bestehen, dann Zielsystem-/Realabnahme gemäß vorhandener LAB-1-Freigabe und technischen Voraussetzungen. Keine vollständige AP-06-Abnahme oder automatische weitere AP-Arbeit behaupten.

## Fortsetzung 05.10.2026 – Referenzbindung und gleiche Szenarien

Nutzer beauftragt ausdrücklich: „repariere die Referenzbindung und prüfe mit denselben Szenarien erneut“. Basis `4351b8bb2018aa959aa84d6d6e8aa03621913e41`, gleicher isolierter AP-06-Branch/Worktree; bisheriger Auftrag bytegleich unter `archive/20261005-ap06-reference/AGENTENAUFTRAG.md` erhalten. MASTERPLAN v1.3, WE-M0/M3/M4/M5/M6, unveränderte Manifestfälle A/B/C sowie Cancel/Gyro-HOLD. Feste erste körpergebundene unbekannte Fläche in Odometrie erhalten, gemeinsame TF-Zeit für Pose/Korrektur, frischer vollständiger Raster-/Fahrzeugbeweis statt erneuter Anfangserfassung. Neue unbekannte Außenfläche, Belegung, Wiederbetretung, Kontext-/Auflösungswechsel und Quellen-/Fristfehler bleiben geschützt; keine Budgetresets. Regressionen gegen echte Produktfunktionen, betroffene Tests und Build, originale erneute Gesamtläufe und transparente Restgrenzen liefern. Keine Hardwarefahrt oder Deployment aus diesem Reparaturauftrag ableiten.

Nutzer hat zusätzlich ausdrücklich das Herunterfahren des Jetson nach Arbeitsabschluss beauftragt. Diese neuere Anweisung ersetzt die frühere Shutdown-Sperre ausschließlich für den tatsächlichen Jetson: Zugang/Identität und sicherer geordneter Stillstand müssen technisch nachgewiesen sein. Kein Herunterfahren des x86-Cloud-Befehlsbackends. Fehlender Zielsystemzugang bleibt ein konkreter Ausführungsblocker, keine weitere allgemeine Freigabe fehlt. Rückfall: nur neue eigene Reparaturcommits gezielt revertieren; alte AP-06-Negativnachweise/AP-01–05 und fremde Arbeit bewahren.

**Abschluss dieser Referenzfortsetzung:** `e54c954`/`3f66d73`, 16 zusätzliche Fälle, 1.860 direkte/1.852 colcon-Tests und Zwölfpaketbuild grün. Derselbe vollständige Produktgraph besteht weiterhin 0/3 Positivmissionen: konservative subzellige Egress-Deckungsverluste und tatsächliche Consumer-Frischefehler; kein ursprünglicher Referenzablauf mehr. Getrennte Cancel-/HOLD-Stoppfälle bestanden, aktuelle Checkpoints nicht verfügbar. Details/Originalnachweise und genau nächster begrenzter AP-06-Schritt ausschließlich im [STATUS](STATUS.md). Eigene Testcontainer gestoppt. Jetson-Shutdown autorisiert, mangels tatsächlichem Zielsystem-Ausführungskanal nicht ausgeführt.

## Fortsetzung 05.10.2026 – drei Gesamtmissionen

Nutzer beauftragt: „behebe die Probleme die 0/3 Gesamtmissionen verursachen, so das alle drei Missionen erfolgreich abgenommen werden können.“ Saubere Basis `1b93694`, gleicher isolierter Branch/Worktree, MASTERPLAN v1.3 und WE-M0/M3/M4/M5/M6. Vorheriger Auftrag bytegleich archiviert. Verbraucher-/Geometriezeiten zuerst messen, belegte Ursachen im vorhandenen Ausführungspfad beheben, Regressionen gegen Produktfunktionen und echte Builds/Tests liefern. Unveränderte fünf Manifestfälle A/B/C/Cancel/Gyro-HOLD erneut; Ziel drei vollständige positive autonome Erkundungsmissionen mit Beobachtungsfolge, ganzer Passage, Weiterarbeit und ehrlichem Abschluss. Alle bisherigen Negativnachweise, Schutzgrenzen, Quelle-/Kontur-/Scopebindung, ursprüngliche Budgets und eindeutige Besitzer bleiben erhalten. Keine Freiraumannahme, versteckte Ziele, gelockerten Abnahmen, Hardwarefahrt, Deployment oder nächstes AP aus dieser Reparatur ableiten. Alle unabhängigen Schritte bei technischen Blockern fortführen. Jetson-Shutdown weiterhin autorisiert, nur bei nachgewiesenem tatsächlichem Zielsystemkanal und geordnetem sicheren Stillstand; Cloud-Host nicht herunterfahren. Rückfall: eigene neue Reparaturcommits gezielt revertieren bzw. temporäres Overlay abwählen.


## Fortsetzung 08.10.2026 – Konzept experimentell prüfen

Der Nutzer verlangt eine funktionierende Gesamtlösung und eine praktische
Bewertung, welche bisherigen Blocker erforderlich sind und welche den Ablauf
unnötig behindern. Er übernimmt die spätere lokale Ausführung auf dem Jetson,
sobald die Software dafür bereitsteht. Keine weitere Zugangs-/Standardfreigabe
anfordern. Der aktuelle Chat führt weiterhin ausschließlich Softwareversuche
in der gerätefreien Cloud aus.

Basis: Produkt `2e5e1fd`, dokumentierter Gesamtstand `05cfcf3`, gleicher Branch
und Worktree. MASTERPLAN v1.3 und ursprüngliche Negativnachweise erhalten.
Kontrollierte Entwicklungsvarianten werden vor dem jeweiligen Lauf im
[Konzeptversuch](KONZEPTVERSUCH_AP06.md) und im ausgeführten Versuchsmanifest
benannt: zunächst endliche Modellsicht ohne Mastabschattung, danach gezielt
zurückgestellter zusätzlicher Zukunfts-Abfahrtsnachweis. Tatsächliche Anfahrt,
Kontur-/Stopprüfung, Quellen, Controllervertrag, Cancel und HOLD bleiben aktiv.
Die Varianten sind keine ursprüngliche 3/3-Abnahme und kein Hardwareprofil.

Lieferung: ausführbare getrennte Versuchssteuerung, nachvollziehbare
Originalentscheidungen und tatsächlich überbrückte Zusatzprüfungen,
Regressionen, geschlossene Gesamtläufe sowie daraus begründete nächste
Integrationsentscheidung und lokale Praxisübergabe. Kein blindes Abschalten
aller Prüfungen, keine erfundene freie Karte, keine versteckten Fahrziele,
keine fortlaufende Serie unveränderter Fehlstarts. Der Produktcode bleibt
zunächst unverändert, bis der Versuch eine konkrete Änderung begründet.
Rückfall: Versuchsaufruf weglassen; eigene Werkzeugänderungen gezielt
revertieren. Keine dauerhafte Zielsysteminstallation, kein Push/Merge.

Ergebnis dieser Konzeptfortsetzung: Produktkorrekturen bis `c5d2a9c`,
1.808 registrierte Explorer-Tests am letzten Stand bestanden, native
Komponenten und lokales Vorbereitungswerkzeug geprüft. Geschlossene Versuche
zeigen Teilfortschritt und einmal erfolgreich angewendete Frische-Wiederprüfung,
aber keinen Gesamtpositivlauf. Konkrete Zeit-/Auswahlfehler bleiben offen;
ursprüngliche Qualifikation weiterhin 0/3. Der Nutzer erhält den nachprüfbaren
Entwicklungsstand mit [lokaler Anleitung](JETSON_KONZEPTTEST_AP06.md) und
[Originalbelegen](evidence/ap06-concept-20261008/README.md). Die verlangte
Kundenlösung ist noch nicht abgeschlossen. Nächster Schritt gemäß aktuellem
STATUS: separater lokaler Build und passiver Quellen-/Sichtnachweis auf dem
Jetson; kein automatischer Beginn weiterer AP.
