# Projektgedächtnis

## Historie und aktueller Einstieg

Die vollständige bisherige Datei bis zum veröffentlichten Commit `99d21c012dfe4c28d8263f7cd5e16505b07736d6` ist [hier bytegleich erhalten](wohnungserkundung/archive/20260930-v1.1/PROJECT_MEMORY.md). Sie enthält auch alle anderen Projektbereiche; nichts daraus ist gelöscht. Für ältere Entscheidungen gezielt dort lesen. Relative Links beziehen sich auf den ursprünglichen Pfad docs/PROJECT_MEMORY.md; [Archivzuordnung](wohnungserkundung/archive/20260930-v1.1/README.md).

Aktuelle Wohnungserkundung ausschließlich aus [MASTERPLAN](wohnungserkundung/MASTERPLAN.md), [STATUS](wohnungserkundung/STATUS.md) und [AGENTENAUFTRAG](wohnungserkundung/AGENTENAUFTRAG.md) ableiten. Ältere „nächste Schritte“ sind keine parallelen Aufträge. Inventar und tatsächliche ROBOT_TRANSFER-Historie bleiben erhalten; dieser Eintrag ändert keine Runtime.

## 30.09.2026 – Metrische Erkundung vor verpflichtender Portal-/Raumsemantik

**Nutzerentscheidung:** Christopher beauftragt Masterplan v1.2 und den nächsten Softwareauftrag. Ziel ist die fortlaufende Schleife aus Beobachtung, erreichbarem Frontier-/Beobachtungsziel, realer Navigation, neuen Messungen und erneuter Aufgabenwahl. Keine dritte vollständige Robotersoftware.

**Wiederverwendung:** Historischer Frontier-/Annäherungskern um `1d91229` plus aktuelle Sensor-/HWT601-/Encoder-/EKF-, Mission-/BT-, Einzelkind-/Cancel-/HOLD- und metrische Validierungsbausteine. Ein Navigator, kein zusätzlicher Motor-/Goalbesitzer. Kein pauschaler Altbranch-Rollback.

**Architekturpräzisierung:** Metrische Ziele innerhalb des gültigen Scopes benötigen keine bestätigte Tür, Region oder Pflicht-PortalMemory. Semantik kann passiv beitragen. Geometrische Durchfahrtsprüfung, notwendige aktuelle Quellen/Pose, Schutzkette, bestätigter Stillstand vor Wiederanfahrt und Budgets bleiben verbindlich. Keine Dummy-Portale/Regionen und kein künstlich gesunder Status. Nicht erreichte Aufgabe ist nicht automatisch Hardwaredefekt; unbekannte sicherheitsrelevante Zustände bleiben bewegungssperrend.

**Bekannte Grenzen:** Der letzte ausgewertete reale Lauf auf `492ef20` endete ohne Ziel-/Türerfolg. SlowZone, fehlende Portalhypothese und unaufgeklärte Timeout-Erstentscheidung bleiben echte Befunde. Aus neuem Plan keine historische Ursache oder neue Abnahme ableiten. Der bisherige Diagnoseauftrag wird als eigenständiger nächster Auftrag abgelöst; benötigte Diagnose und Gegenfälle gehen in das funktionale Softwarepaket ein.

**Betroffene Dokumente:** AGENTS-Einstieg, MASTERPLAN, STATUS, AGENTENAUFTRAG, Gesamtstrategie, Meilensteinpräzisierung und dieses Journal. Frühere umfangreiche Plan-/Status-/Auftrags-/Strategie-/Meilenstein-/Journalfassungen wurden unter ihrer Original-Blobidentität archiviert, damit die aktiven Referenzen nur einen aktuellen Auftrag enthalten. Keine Code-, YAML-, Treiber- oder Hardwareänderung.

**Nachweise dieses Eintrags:** Dokumentationsabgleich; keine neuen Softwaretests oder Realversuche. Akzeptierte frühere HWT-Teilnachweise bleiben erhalten. Neues metrisches Backend erst beauftragt, nicht umgesetzt.

**Nächster Auftrag:** metrischen Kern gerätefrei implementieren und im verbundenen Produktgraph ohne Pflicht-Semantik prüfen: mehrere echte Folgeziele, blockierte Aufgabe mit zulässiger Alternative, HOLD/Cancel und harte Gegenfälle, ehrlicher Abschluss. Danach genau einen begrenzten Realnachweis vorbereiten, nicht automatisch starten.

**Git/Privatsphäre:** LAB-1 unverändert. Reale Karten/Bilder/Bags und private lokale Berichtscommits nicht mitpushen, auch nicht als Vorfahren. Nur Remote-Dokumentbasis veröffentlicht; keine lokale Jetson-Arbeitskopie umgeschaltet. Kein Merge und kein dauerhafter Installwechsel. Rückfall: gezieltes Revert der Dokumentationsänderung ohne Roboterruntime-Eingriff.
