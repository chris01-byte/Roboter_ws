# Wohnungserkundung – aktueller Status und nächster Auftrag

**WE-1 · 30.09.2026 · MASTERPLAN v1.2 · Stufe 3 weiterhin OFFEN**

Maßgeblich: [MASTERPLAN](MASTERPLAN.md), [AGENTENAUFTRAG](AGENTENAUFTRAG.md), [LAB-1](../LABORMODUS.md), [MEILENSTEINE](MEILENSTEINE.md). Dies ist der einzige aktuelle WE-Iststand. Die ausführliche bisherige Statusdatei ist [bytegleich archiviert](archive/20260930-v1.1/STATUS.md); alte Abschnittsnummern und „nächste Schritte“ dort sind historische Referenzen.

## 1. Aktuelle Nutzerentscheidung

Normale Erkundung wird metrisch organisiert: beobachten → erreichbare Frontier-/Beobachtungsposition wählen → navigieren → neue Beobachtung und Ergebnis bewerten → nächste Aufgabe. Portal-/Raumsemantik ist keine Pflicht für normale metrisch sichere Ziele. Geometrie, Karte/Pose, Scope, Sensor-/Antriebsgesundheit und Schutzkette bleiben verbindlich.

**Beschlossen, noch nicht umgesetzt.** Keine neue Softwarefunktion, Fahrt, Parameteränderung oder Installation wurde durch diesen Dokumentationsstand ausgeführt. Die spätere Zielwahl ist kein pauschaler Rollback auf den historischen Explorer und kein Umgehen einer unsicheren Durchfahrt.

## 2. Belegter Ausgangspunkt

| Stand | Beleg / Grenze |
|---|---|
| Remote-Dokumentbasis vor v1.2 | PR #105, feature/hwt-hold-recovery-resume, `99d21c012dfe4c28d8263f7cd5e16505b07736d6`; keine Aussage über aktuelle lokale Runtime |
| Letzter ausgewerteter realer Kandidat | `492ef20`, Ergebnis `d480243`; vollständiger zweiter Lauf stage3-map-handoff-20260929/real-repeat |
| Historischer Funktionsvergleich | `1d91229dc10ff4bb791938d49aae8e9808a5dfff`; [WE_PARITY_RESET](../WE_PARITY_RESET.md) dokumentiert Frontierfahrten, verbundenen Türübergang und weitere Frontiers danach |
| Erster HWT-Recoveryfall | Gerätefreier aktiver Kindzielvertrag und reale Rundblick-HOLD/Recovery/Fortsetzung im dokumentierten Umfang akzeptiert; kein umfassender Robustheitsnachweis |
| Aktueller Erkundungserfolg | Kein bestandener zusammenhängender A/B/C-/Mehrraumlauf; kein Ziel- oder Türerfolg des letzten Laufs |
| Neues metrisches Backend | Geplant/beauftragt, kein Build, keine Regression, kein Zielsystem-/Realnachweis vorhanden |

Aktuelle und historische Modul-/Installpräfixe aus ROBOT_TRANSFER und den erhaltenen Manifesten ermitteln, nicht aus Branch-Namen ableiten. Bestehende Builds und unbekannte lokale Änderungen nicht überschreiben. Die Abnahme eines neu kombinierten Kandidaten wird nicht aus historischen Einzeltests zusammengesetzt.

## 3. Offene Befunde bleiben erhalten

Der letzte vollständige Lauf hielt ein autonomes Frontierkind bis zum Kindtimeout; kein SOURCE_INVALIDATED und kein HWT-first_fault. Keine erledigte Aufgabe, keine Portalquerung, kein Regionwechsel. SlowZone gab 30 % aus; kleine Bewegungen reichten im Offline-Progress-Checker-Replay, nicht für Zielerreichung. Nicht mit externer Bewegungsvermessung gleichsetzen.

Softwareseitig blieb der Portalbestand in 327 Statusmeldungen leer; 296 Gegenproben fanden ebenfalls keinen Kandidaten. Der aktive Analysepfad verwendete 0,20 m statt der separaten historischen Analyse bis 0,40 m. Das ist ein Vergleichsbefund, kein bewiesener alleiniger Auslöser und kein Auftrag, Grenzen blind anzugleichen. Die konkrete physische Tür ist dem Datensatz weiterhin nicht eindeutig zugeordnet.

Die SlowZone-Punkte lagen räumlich auch in den Costmaps. Ein sicherer physischer Ausweg ist damit nicht bewiesen. Warum der reale Timeout zu SYSTEM_FAILURE statt möglicher lokaler Aufgabenrückstellung führte, ist mangels interner Erstentscheidung nicht abschließend rekonstruiert. Positive Offline-Snapshots ersetzen nicht den damaligen Callbackzustand. Abweichungen von Drehsoll/-rückmeldung, Objektidentität und Shutdownfehler bleiben offen, nicht als harmlose Nebeneffekte wegdefiniert.

Originalwerte, Szenarien, Tests und Messgrenzen: [voriger STATUS, Abschnitt 7](archive/20260930-v1.1/STATUS.md#7-nächster-schritt-und-historie). Vollständige lokale Auswertung: `~/.local/share/amadeus/tests/stage3-door-obstacle-offline-20260930/`. Private Rohdaten bleiben lokal.

## 4. Genau nächster Auftrag

**Metrische Frontiererkundung ohne Portalpflicht implementieren und gerätefrei durchgängig prüfen.** Ausführbar in AGENTENAUFTRAG.

Eine schmale metrische Aufgabenstrategie im bestehenden Explorer verwenden; aktuelle Mission-/Kind-/HOLD-Verträge erhalten. Kein verpflichtender Portalfeed, keine gefälschte Region als Adapter. Vorhandene echte Frontier-/Annäherungsfunktionen übernehmen, geometrische und technische Prüfungen erhalten. Erstes Ziel bearbeiten → neue Karte bewerten → weiteres Ziel; erfolgloses Einzelziel bei sicherer Fortsetzbarkeit begrenzt zurückstellen und Alternative zulassen.

Der bisherige ausschließliche Timeout-Diagnoseauftrag ist **als eigener aktueller Auftrag abgelöst**. Benötigte Erstentscheidungsdaten gehören in dieses Funktionspaket. Unbekannte historische Einzelwerte müssen nicht erfunden werden und sind kein pauschales Entwicklungs-Gate. Keine vorsorgliche Veränderung der Fahrregler, Sensoren oder SlowZone.

**Paketende:** lauffähiger isolierter Build, echte integrierte Entscheidungsschleife mit synthetischen Sensorszenen/Nav2-Gegenstelle, erforderliche Gegenfälle und genau ein vorbereiteter begrenzter Realnachweis. Keine Geräteprozesse oder Fahrt automatisch anhängen.

## 5. Erhaltener Umfang und nächste Meilensteine

Schritt 1/2 nicht neu beginnen; betroffene Wiederverwendung gezielt regressieren. Stufe 3: zunächst Softwareabschluss des metrischen Kerns, danach reale autonome Beobachtungsfolge, Hindernis-/Befreiungsfälle und vollständige Passage mit Weitererkundung. Normale Fahrten benötigen keine Portal-ID mehr; physische Durchfahrt und freier Fahrweg bleiben nachzuweisen.

Danach metrischer WE-M4-Rundweg, WE-M5-Persistenz/Wiederaufnahme und WE-M6-Abschluss gemäß v1.2. Semantische Portal-/Regionskriterien werden separat geführt, nicht gelöscht oder rückwirkend erfüllt. Geparkter HWT-Kindziel-Injektionstest, optionale OAK-Türerkennung und zusätzliche Architekturvergleiche sind kein aktueller Parallelauftrag.

## 6. Git, Runtime und Rückfall

Ein Integrationsverantwortlicher, bestehender Branch/PR #105. Kein automatischer Merge, kein permanenter Installwechsel. LAB-1 ohne erneute Standardfreigabeschleifen anwenden. Gerätefreier Auftrag ist keine unbegrenzte Fahrerlaubnis.

Ein lokaler nicht veröffentlichter Berichtscommit mit Raumdaten wurde im Gespräch genannt. Vor späterem Push ausgehende Vorfahren prüfen; diese Daten nicht durch Merge/Push mitveröffentlichen. Lokale Arbeit sichern und getrennt halten, keinen Force-Push oder destruktiven Reset ausführen. Der Dokumentationscommit basiert ausschließlich auf dem veröffentlichten Remote-Stand.

Rückfall dieses Planstands: nur die Dokumentationsänderung gezielt zurücknehmen; keine Roboterruntime zurücksetzen. Rückfall der späteren Implementierung: neuen expliziten Modus/Overlay nicht aktivieren, bekannten Stand erhalten und dessen offene Befunde weiter benennen.

## 7. Historie und Nachweisregister

[Original-STATUS bis 99d21c0](archive/20260930-v1.1/STATUS.md), [Original-Agentenauftrag](archive/20260930-v1.1/AGENTENAUFTRAG.md), [Archivzuordnung und Originalpfade](archive/20260930-v1.1/README.md). Die Dateien sind unverändert erhalten. Maßgeblich für den jetzigen Auftrag sind Abschnitte 1–6 dieser Datei und der aktuelle AGENTENAUFTRAG, nicht ältere Aufträge aus dem Archiv.
