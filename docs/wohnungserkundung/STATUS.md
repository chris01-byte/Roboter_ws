# Wohnungserkundung – aktueller Status und Restumfang

**WE-1 · Amadeus / `chris01-byte/Roboter_ws` · Dokumentationsabgleich: 2026-09-15**

Dies ist der einzige laufende WE-Status. [Strategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md)
und [Meilensteine](MEILENSTEINE.md) beschreiben unverändert das Soll;
[Agentenauftrag](AGENTENAUFTRAG.md) beschreibt Arbeitsweise und Folgeauftrag.
Der vollständige vorherige Status einschließlich aller Entscheidungslogs liegt
[unverändert im Archiv](../archive/2026-09/WOHNUNGSERKUNDUNG_STATUS_WE-M3U_0474551.md).
Seine früheren Aussagen über den „aktuellen“ Stand sind historische Snapshots.

## 1. Arbeitspriorität und belastbarer Ausgangspunkt

**Zuerst den vereinbarten Softwareumfang zusammenhängend fertigstellen und
gerätefrei prüfen. Keine vorgezogene Probefahrt, kein Neustart der Entwicklung.**
Raumerkundung und die physische Arbeitszimmer-Flur-Durchfahrt waren bereits vor
WE-1 erprobt; der [HWT-Bericht vom 11.09.2026][hwt] bleibt deren Nachweis.
Die danach korrigierte Abschlusslogik und damalige Lastbefunde sind davon getrennt.

Die WE-Entwicklung hat M3/U erreicht. Die automatische Portal-/Ereigniskette ist
in einem echten Explorer-Prozess mit synthetischen Eingaben geprüft. Das ist mehr
als die früheren Tests mit vorgegebenen Bestätigungsereignissen, aber noch kein
Nachweis der gesamten Wohnung einschließlich Speicherung und Wiederaufnahme.
**Der begrenzte M3/U-Softwareabschluss ist nicht „WE-1 komplett fertig“.**

## 2. Referenzen und Nachweisgrenzen

| Referenz beim Dokumentationsabgleich | Bedeutung |
|---|---|
| [PR #91][pr91], `047455134894f700a115f6cea422479b99c702f6` | Neuester hier geprüfter funktionaler Stand, `feature/we-m3u-process-runtime-evidence`; PR offen, nicht gemerged. |
| `main`: `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1` | Bisherige Main-Basis; die gestapelte WE-Reihe ist nicht automatisch darin enthalten. |
| HWT: `1d91229dc10ff4bb791938d49aae8e9808a5dfff` | Separater erprobter Entwicklungszweig, keine pauschale Übernahmefreigabe. |
| Ursprünglicher Dokumentationscommit `96cebee` | Historischer Planstart, nicht der heutige Fortschrittsstand. |
| Lokale Jetson-Installation | Nur frühere Inventur im Archiv verfügbar; in diesem Dokumentationsauftrag nicht neu geprüft oder verändert. |

Quellen sind der [gepinnte M3/U-Status][oldstatus],
[Projektgedächtnis][memory] und der [Prozessprüfer][smoke]. Die dortigen
Softwaretestresultate sind **berichtete Nachweise**, in diesem
Dokumentationsauftrag nicht erneut ausgeführte ROS-/Build-/Fahrtests.
Bei späteren Änderungen zuerst den neueren Commit und dessen konkrete Evidenz
prüfen; weder diesen Snapshot noch eine höhere PR-Nummer blind als Status benutzen.

## 3. Aktueller Meilensteinstand

| Stufe | Softwarestand | Verbleibende Grenze |
|---|---|---|
| WE-D0 / WE-M0/A | Strategie und Bestandsprüfung dokumentiert. | Kein Deployment-/Hardwarebeleg; keine Wiederholung ohne neuen Befund. |
| WE-M0/B | Historische Fahrbasis vorhanden. | Reproduzierbarer Zielsystemstand, Lastprüfung und gezielter Nachtest der Abschlusskorrektur offen. |
| WE-M1 | Portalgedächtnis und In-Memory-Verträge softwaregeprüft. | Nicht selbst eine Sensor- oder Hardwareabnahme. |
| WE-M2 | Bis AT: Daten-/Struktur-/Frontierzuführung, Graph, Aufgaben und synthetischer Langlauf berichtet. | Neue M3-Monitoranbindung berücksichtigen; Zielsystem-/Gesamtnachweise noch offen. |
| WE-M3 | **A bis U**: hierarchische Auswahl, Ziel-/Kindzielverwaltung, Resultate, Abschlussruntime, Portalmonitor und atomare Fortschreibung im Opt-in-Profil implementiert und im dokumentierten Umfang geprüft. | Vollständiger Mehrraum-Gesamtablauf mit fortlaufenden Kartenänderungen noch gesondert nachzuweisen; Zielprofil und Gesamtsicherheits-/SLAM-Last offen. |
| WE-M4 | Reale Drei-Regionen-Abnahme geplant. | Arbeitszimmer → Flur → weiteres Zimmer → derselbe Flur; nicht durch einen synthetischen Einzelübergang erfüllt. |
| WE-M5 | **WE-Persistenz/Wiederaufnahme noch geplant.** Vorhandene Kartenmanager sind Grundlage, kein fertiger WE-Speicher. | Schema, Kartenbindung, atomarer Save/Load, Restaufgaben und frische Wiederaufnahme gerätefrei umsetzen und prüfen. |
| WE-M6 | Wiederholbarer Wohnungsabschluss nicht abgenommen. | Softwaregesamtkette und anschließend die bestehenden realen Abnahmekriterien erfüllen. |
| WE-M7 | Ergänzende App-Transparenz und manuelle Benennung geplant. | Kein Blocker des geometrischen Kernziels; bestehende App-Verträge erhalten. |

Die alte M3-Tabellenangabe „A bis N“ und „Abschlussruntime fehlt“ ist durch den
neueren M3/U-Bericht überholt. Ebenso gilt „keine Bewegungsbelegquelle angebunden“
nicht mehr pauschal: Im **neuen Opt-in-Profil** ist der synthetisch geprüfte
LiDAR-/TF-Monitor angebunden. Das ist keine Aussage über einen übernommenen
HWT-Gesamtpfad oder die aktuell installierte Hardwarekette.

## 4. Was M3/U konkret belegt – und was nicht

Der Prüfer startet den produktiven `ExploreNode` als eigenen Prozess in einer
isolierten ROS-Domain. Synthetische Karten-/Statusrevisionen erzeugen automatisch
Portalbestätigung, zwei Regionen und eine Portalaufgabe. Synthetische Scans und
exakt zugeordnete TF-Posen laufen durch den konkreten LiDAR-Referenzmatcher.
Die Durchfahrtsbestätigung wird dabei nicht als fertiges Monitorurteil injiziert.

| Berichteter Versuch | Ergebnis |
|---|---|
| Positiver Portalübergang | Ein Nav2-Testziel, ein Eintritt, Portalaufgabe erledigt, null beobachtete Command-Nachrichten. |
| Fehlende zeitlich passende TF-Daten | Ein Ziel, ein Cancel, kein Eintritt, Portalaufgabe offen, erklärter Abbruch, null beobachtete Command-Nachrichten. |
| Quell-/Paketprüfung | 1053 Tests in der gemeinsamen Suite; separater temporärer Drei-Paket-Aufbau mit 875 Tests ohne Fehler, Fehlschläge oder Skips. Die Suiten überlappen und werden nicht addiert. |

**Grenzen:** Nav2, Karte, Kartenmanager, TF und Scans sind simuliert. Der
Prozessversuch verwendet bekannte Raster ohne Frontiers; nach dem positiven
Übergang beendet der Prüfer den Elternauftrag per Cancel. Er belegt daher keinen
natürlichen vollständigen Mehrraumabschluss, keinen Rückweg durch mehrere Räume
und keinen Save/Restart/Resume-Zyklus. Profilwerte sind synthetisch, keine
vermessenen Chassis- oder Sicherheitswerte. Fehlende reale Commandausgabe in
diesem Aufbau ist kein Not-Aus- oder Kollisionsnachweis.

## 5. Endliche Restarbeit innerhalb der bestehenden WE-Meilensteine

Diese Liste bündelt Restanforderungen, sie eröffnet keine Parallelroadmap.

1. **Review und gemeinsame Softwarebasis:** Gestapelte Änderungen bis M3/U und
   diesen Dokumentationsnachtrag prüfen, Abhängigkeiten/Regressionen zuordnen und
   eine exakt bezeichnete isolierte Reviewbasis reproduzieren. Kein automatischer
   Merge nach Main, kein pauschaler HWT-Merge und kein Wechsel der Roboterinstallation.
2. **Mehrraum-Gesamtnachweis:** Vorhandenen Produktionspfad und Prüfer weiterverwenden.
   Synthetische, sich entwickelnde Karten mit Frontiers, mehrere Portale,
   Flurrückkehr und erklärten natürlichen Abschluss zusammen prüfen. Vorhandene
   Einzelbelege zuordnen; nur fehlende Fälle ergänzen. Revisionswechsel während
   aktiver Ziele müssen sowohl korrekte Invalidierung als auch begrenzten
   Fortschritt zeigen. Nicht einfach Karte einfrieren oder Frischeprüfungen lockern.
3. **WE-M5 gerätefrei schließen:** Vorhandene Karten-/Semantikverträge verwenden;
   WE-IDs, Graph und offene Aufgaben passend zur gespeicherten Karte ablegen und
   wiederherstellen. Historie bleibt erhalten, flüchtige Frische/Fahrberechtigungen
   nicht. Laden startet keine Bewegung; Fortsetzung benötigt neue gültige Quellen
   und einen neuen zulässigen Auftrag. Beschädigung, fremde Karte und unvollständige
   Schreibvorgänge dürfen die letzte gültige Sicherung nicht zerstören.
4. **Softwareabschluss zusammen nachweisen:** Den Mehrraumablauf mit Unterbrechung,
   Speicherung, Neustart, erneuter Quellenprüfung und expliziter Fortsetzung
   verbinden. Blockierter Rückweg, fehlende Quellen und Budgetende erzeugen
   nachvollziehbaren Teilstand/Abbruch statt erfundener Vollständigkeit.
5. **Danach Zielsystem und reale Abnahme:** Reproduzierbare Integration mit den
   tatsächlich benötigten HWT-/Sensorfusionsanteilen, begründetes Zielprofil,
   parallele SLAM-/Sicherheitslast, WE-M0/B und WE-M4/6 nach deren Freigaberegeln.
   Offline-WE-M5 muss nicht auf eine vorgezogene Fahrt warten.

Erwartete Szenarioereignisse sind Testorakel, keine Eingaben anstelle der zu
prüfenden Produktionsentscheidung. Eindeutig simulierte Sensoren und Nav2 sind
zulässig. Keine perfekte semantische Wohnungseinteilung, kein neuer Navigator,
kein neues KI-Modell und kein großes zusätzliches Simulationsframework.

## 6. Noch zu prüfende Risiken ohne erfundene Erledigung

- **Kartenrevisionen:** M3/U nennt mögliche laufende Zielabbrüche bei jeder
  inhaltlich neuen Karte. Relevante Änderung, Frische und Fortschritt müssen
  zusammen funktionieren; Zielprofil/Updatefrequenz nicht als gelöst behandeln.
- **Installation und Last:** Gemischte alte Installationsanteile, HWT-Unterlay,
  TF-Zukunftsextrapolationen und verpasste Controllerzyklen sind historische
  Befunde. Keine neue Vor-Ort-Messung in diesem Auftrag; vor Hardwarebetrieb prüfen.
- **Ältere offene Vertragsbefunde:** Die früher dokumentierte 2-s-Quellfrist bei
  2-s-Statusperiode und der Kreis-/Polygon-Widerspruch eines Nahbereichstests
  besitzen hier keinen belegten Abschluss. Im Review gezielt zuordnen: aktuellen
  Fix nachweisen oder als offen führen. Keine Sicherheitskonfiguration passend
  zu einem Test abschwächen.
- **Regionskorrekturen:** Frühere Split-/Merge-Tests injizieren die Entscheidung.
  Im aktuellen Produktionspfad belegen, welche Zuordnungs-/Korrekturfälle automatisch
  behandelt werden und wo konservative Unsicherheit bleibt. Keine perfekte
  Segmentierung fordern, aber auch keine verlorenen globalen Restaufgaben zulassen.

## 7. Fortschrittsschätzung für die Nutzerplanung

**Ungefähr 65 % des WE-1-Kernziels insgesamt; ungefähr 75 % des gesamten
Softwareumfangs.** Dies sind grobe fachliche Planungsschätzungen des
Dokumentationsabgleichs, mit etwa ±10 Prozentpunkten Unsicherheit, keine Messwerte,
keine aus Tests/PRs berechneten Quoten und keine Restzeitzusage. Bewertung: bereits
arbeitende Kernlogik gegenüber offenem Gesamtablauf, Persistenz, Integration und
realer Abnahme. Ein kleiner Rest kann erheblichen Debuggingaufwand verursachen.

100 % Kernziel heißt: alle im vereinbarten Umfang aktuell zugänglichen Bereiche
systematisch erkunden, bekannte Rückwege nutzen, Restaufgaben ehrlich ausweisen,
passend speichern/wiederaufnehmen und die bestehenden WE-M6-Abnahmekriterien
wiederholt real erfüllen. Nicht gemeint: der ganze Roboter einschließlich Arm,
Türöffnen, Ladestation oder optionale App-Komfortfunktionen. Die Prozentzahl ist
kein Anlass, einen Meilenstein ohne dessen Belege abzuhaken.

## 8. Dokumentationsentscheidung und nächster Auftrag

**2026-09-15:** Kopf, Meilensteintabelle und offene Punkte auf die M3/U-Evidenz
abgeglichen. Überholte Gegenwartsaussagen nicht als aktuelle Blocker fortführen.
Der vollständige vorherige Status bleibt als identischer Git-Blob
`6f07e2ae053847293edcce3825fe527f01b0d262` im Archiv; kein historisches Ergebnis
wurde nachträglich auf bestanden gesetzt. Strategie und Abnahmekriterien bleiben
unverändert. Der Auftrag änderte nur Dokumentation, nicht Produktionscode.

Der [Folgeauftrag in Abschnitt 7 des Agentenauftrags](AGENTENAUFTRAG.md#7-folgeauftrag-softwareabschluss-ohne-geräte)
beginnt mit Review der vorhandenen Kette und führt nach einem belegten Reviewgate
zum begrenzten Mehrraum-/Persistenzpaket. Die Nutzerübergabe dieses Auftrags ist
keine Hardware- oder automatische Mergefreigabe. Rückfall: nur diesen
Dokumentationscommit zurücknehmen, nicht die funktionale M3/U-Basis.

[pr91]: https://github.com/chris01-byte/Roboter_ws/pull/91
[oldstatus]: https://github.com/chris01-byte/Roboter_ws/blob/047455134894f700a115f6cea422479b99c702f6/docs/wohnungserkundung/STATUS.md
[memory]: https://github.com/chris01-byte/Roboter_ws/blob/047455134894f700a115f6cea422479b99c702f6/docs/PROJECT_MEMORY.md
[smoke]: https://github.com/chris01-byte/Roboter_ws/blob/047455134894f700a115f6cea422479b99c702f6/tools/kartierung/wohnungserkundung_process_smoke.py
[hwt]: https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/docs/PROJECT_MEMORY.md
