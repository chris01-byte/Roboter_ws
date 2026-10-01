# WE-1 – verbindlicher Masterplan für robuste metrische Wohnungserkundung

**Version 1.2 · 30.09.2026 · Amadeus / `chris01-byte/Roboter_ws`**

**Nutzerentscheidung:** Christopher beauftragt die Ausrichtung auf eine schlanke metrische Erkundungsschleife unter Wiederverwendung der beiden vorhandenen Entwicklungsstände. Dies ist eine ausdrücklich beschlossene Architekturpräzisierung, keine bereits implementierte Funktion, Realabnahme oder Auslieferungsfreigabe. [LAB-1](../LABORMODUS.md) bleibt unverändert gültig.

> Beobachtete Umgebung erfassen → erreichbare, nützliche Beobachtungsposition wählen → über Nav2 anfahren → neue Messungen einarbeiten → Ergebnis bewerten und erneut entscheiden.

**Änderung gegenüber v1.1:** Normale metrisch zulässige Erkundungsziele benötigen keine bestätigte Portal-ID, Raum-ID oder verpflichtend laufende Portal-/Regionsgraph-Auswertung. Tür-/Raumverständnis wird ergänzend geführt. Die geometrische Durchfahrtsprüfung, gültige Karte/Pose, Schutzkette und Auftragsgrenzen bleiben notwendig. Keine dritte vollständige Robotersoftware und kein pauschaler Rücksprung auf einen alten Branch.

Die v1.1-Regel zum nicht rekonstruierbaren historischen HWT-Erstwert gilt weiter: Definierte Recoveryverträge dürfen implementiert und getestet werden, ohne eine unbekannte alte Einzelursache zu behaupten. Frühere Dokumente sind [bytegleich archiviert](archive/20260930-v1.1/README.md).

**Präzisierung 01.10.2026 (Schritt 3):** `metric_frontier` startet adaptiv:
voller Rundblick nur bei belegter Geometrie und Beobachtungsnutzen, sonst ein
autonom berechnetes zulässiges Beobachtungsziel, sonst begründetes Warten/Teilstand.
Der unbenutzte 360°-Sweep ist kein allgemeines Startgate. Die konkrete Bewegung
mit Startkontur, Controllerdrehung, Route und Zielorientierung bleibt vollständig
zu prüfen; unbekanntes Padding bleibt gesperrt. `existing` bleibt unverändert.
Encoder: 120-ms-Messgrenze und 180-ms-Kontinuität bleiben unverändert. Begrenzte
Timing-Recovery erhält den Auftrag im bewegungsgesperrten HOLD, benötigt vor
Wiederanfahrt echte gültige Paare, belegte Kontinuität, Stillstand, aktuelle
Lokalisierung/Route und terminales Kind/Gate-ACK. Unbelegte Lücke bedeutet
Hilfebedarf/Teilstand, niemals Rebaseline oder Faultflag-Reset. Manuelles Umsetzen
oder Vorkartieren zählt nicht als autonomer Bootstrap. Historische Fehlversuche
bleiben erhalten.

## 1. Geltung und Dokumentzuständigkeit

Der Masterplan konkretisiert WE-1. Das Produktziel bleibt die autonome Erkundung der freigegebenen, aktuell zugänglichen und sensorisch erschließbaren Umgebung, konsistenter Teil-/Gesamtabschluss und später belastbare Wiederaufnahme. Geschlossene unbekannte Räume oder unbeobachtete Gefahren dürfen nicht als erkundet gelten.

| Dokument | Verbindliche Rolle |
|---|---|
| [AGENTS.md](../../AGENTS.md), [LABORMODUS.md](../LABORMODUS.md) | Allgemeine Arbeits- und Schutzregeln; durchgängiger begrenzter Laborumfang |
| MASTERPLAN.md | Stabile Entscheidungen, Reihenfolge und Änderungsgrenzen |
| [STATUS.md](STATUS.md) | Einziger aktueller Iststand, offene Punkte und genau ein nächstes Paket |
| [AGENTENAUFTRAG.md](AGENTENAUFTRAG.md) | Ausführbarer aktueller Softwareauftrag |
| [Gesamtstrategie](../WOHNUNGSERKUNDUNG_STRATEGIE.md), [MEILENSTEINE.md](MEILENSTEINE.md) | Produktumfang und präzisierte bestehende WE-D0/WE-M0–WE-M7-Abnahmen |
| [PROJECT_MEMORY.md](../PROJECT_MEMORY.md) | Datiertes Entscheidungsjournal mit vollständiger historischer Referenz |
| [ROBOT_TRANSFER.md](../ROBOT_TRANSFER.md) | Tatsächliche Installation, Betrieb und Rückfall; kein Sollstand |

Die expliziten v1.2-Änderungen haben Vorrang vor alten verpflichtenden Portal-/Regionsabhängigkeiten der metrischen Erkundung. Nicht betroffene Schutz- und Nachweisbedingungen bleiben bestehen. Keine Parallelroadmap, keine neuen WE-Meilenstein-IDs, keine Ausführung alter Archivaufträge.

## 2. Architekturentscheidung und Wiederverwendung

### 2.1 Ein Erkundungskern, ein Ausführungspfad

Mission Manager → bestehender BT → ein Explorer mit metrischer Aufgabenwahl → ein Nav2-Kind → bestehende Gate-/Glättungs-/Kollisionskette → Basis.

SLAM kartiert fortlaufend, auch während der Bewegung. Es ist nicht nach jeder Fahrt neu zu starten. Der Explorer wählt erreichbare Positionen im bekannten zulässigen Freiraum, von denen weitere Beobachtung sinnvoll ist. Sicherheit wird vor Nutzen geprüft; Informationsgewinn rechtfertigt keine unsichere Fahrt.

Der Kern betrachtet erreichbare Frontiers im gesamten aktuellen Auftragsscope, nicht nur in einer zuvor benannten Region. Die Wiederverwendung bekannter Wege ist erlaubt. Kein vollständiges Abfahren des Startraums als Voraussetzung für einen offenen Durchgang. Kartierungsfortschritt ist nicht mit Reinigung/Fahrspurabdeckung gleichzusetzen.

### 2.2 Notwendige Eingänge und optionale Semantik trennen

**Notwendig:** aktuelle konsistente Karte samt Sitzung/Frame, Pose/TF, Hinderniskarten und Beobachtungen, tatsächlicher Fahrzeugumriss, gültiger Auftragsscope, Betriebsbereitschaft, Budgets und Schutzbedingungen.

**Nicht notwendig für normale metrische Ziele:** Portalbestand, semantische Raumzuordnung, topologische Aufgabenhierarchie, kamerabasiertes Türlabel. Leere, fehlende oder veraltete optionale Semantik darf den metrischen Kern nicht sperren. Dagegen bleiben fehlende sicherheitsrelevante Quellen oder unzureichende Lokalisierung bewegungssperrend.

Diese Trennung ist im Daten-/Auftragsvertrag herzustellen. Keine erfundenen Portal-/Raum-IDs, kein künstlich frischer Shadowstatus und keine allgemeine Deaktivierung von Validierungen. Ein bestehender Regionsgraph kann passiv mitlaufen, aber weder einen zweiten Navigationsauftrag senden noch metrische Ziele verdeckt filtern. Sein Ausfall darf auch über gemeinsame Ressourcen oder Startbedingungen nicht unbeabsichtigt zum Pflicht-Gate werden.

### 2.3 Wiederverwenden statt zurückrollen

| Herkunft | Zu übernehmen bzw. gezielt zu prüfen |
|---|---|
| Historischer Explorer um `1d91229` | Frontierbildung und Rangfolge, sichere Annäherungsziele, Rundblick/Vorausrichtung, besuchte/fehlgeschlagene Ziele und Folgeauswahl; Referenzdatensatz vom 11.09. |
| Aktuelle Integration | Sensor-/Treiberkorrekturen, HWT601 plus Encoder/EKF, Mission Manager/BT, bestätigter Kind-Cancel, Auftragserhalt, begrenzte Recovery, metrische Karten-/Pose-/Routenprüfung |
| Vorhandene Infrastruktur | Nav2, Gate, VL53/Collision Monitor, Kartenmanager, Recorder, isolierte Builds, Manifeste und passende Regressionen |
| Portal-/Regionsentwicklung | Erhalten als optionale Erweiterung und historische Vergleichsreferenz; keine Pflichtabhängigkeit des metrischen Kerns |

Existenz eines Moduls oder historischer Test ist kein heutiger Integrationsnachweis. Kein Austausch von Treibern, SLAM oder Motorsteuerung allein wegen dieser Richtungsentscheidung. Keine neue OAK-/YOLO-Pipeline und kein zusätzlicher globaler Supervisor. Veröffentlichter Frontiercode kann gezielt als Offline-Vergleich dienen; ein vollständiger Fremdstack ist nicht beauftragt.

### 2.4 Durchfahrt ohne Türlabel bedeutet nicht Durchfahrt ohne Geometrie

Offene, mit realem Fahrzeugumriss und aktueller Beobachtung zulässige Verbindungen dürfen normale Nav2-Wege sein, auch ohne Portal-ID. Physische Passage inklusive Heck und Weiterarbeit dahinter bleiben nachzuweisen.

Eine durch unbekannte, kollidierende oder nicht sicher befahrbare Geometrie getrennte Karte wird nicht durch direkte Motorbefehle überbrückt. Vorhandene besondere LiDAR-geprüfte Engstellenmanöver bleiben separat erhalten und abgesichert; der erste metrische Kern aktiviert sie nicht automatisch. Ein nicht nachweisbar passierbarer Durchgang bleibt eine sichtbare Restaufgabe, kein verdeckter Vollabschluss.

## 3. Arbeitsreihenfolge innerhalb der bestehenden Roadmap

### Schritt 1 – konsolidierte Betriebsbasis erhalten

Vorhandene Quell-/Profil-/Buildzuordnung und Rückfallstände nutzen. Nur betroffene Auflösung erneut prüfen, keine neue Gesamtinventur. Ein Besitzer je Motorbus, produktivem Odometrie-TF und Navigationsauftrag. Keine laufende Roboter-Arbeitskopie umschalten; unbekannte lokale Änderungen sichern.

**Ergebnis:** Reproduzierbarer abgegrenzter Kandidat. Bisherige Fortschritte nicht durch die neue Planung zurücksetzen. Aktueller Belegumfang steht im STATUS.

### Schritt 2 – akzeptierten ersten Recoveryfall erhalten

Gerätefreier HWT-Kindzielvertrag und realer Rundblick-HOLD/Recovery/Fortsetzung bleiben im dokumentierten Umfang erhalten. Nach betroffenen Integrationsänderungen gezielt regressieren, nicht die historische Ursachenjagd neu beginnen. Die zusätzliche reale HWT-Injektion während eines Nav2-Kindes bleibt geparkter Robustheitsrest, kein neues Gate vor metrischer Erkundung.

### Schritt 3 – metrischen Kern softwareseitig schließen und real abnehmen

**Jetzt zuerst ein zusammenhängendes Softwarepaket:** echte Frontier-/Zielwahl von zwingender Portal-/Regionsevidenz entkoppeln; Zielausführung und nachfolgende Aufgabenentscheidung über bestehende Mission/BT/Nav2 verbinden. Ein lokaler Misserfolg darf bei nachgewiesener sicherer Fortsetzbarkeit eine andere zulässige Aufgabe ermöglichen. Der bekannte Timeout-/Kriechfall ist gezielte Regression, kein unendlicher Diagnose-Nebenauftrag.

Der Gerätefrei-Nachweis umfasst wechselnde Karten, mindestens mehrere aufeinanderfolgende Zielentscheidungen, eine blockierte Aufgabe mit Alternative, fehlende optionale Semantik, begrenzte Wiederaufnahme und harte Gegenfälle. Keine stets gesunden Attrappen für die zu prüfende Policy, keine fest eingesetzten Zielkandidaten statt echter Frontierberechnung.

**Danach begrenzter Realnachweis auf demselben Kandidaten:** regulärer Start und Beobachtung, mehrere autonome Beobachtungspositionen, erkennbare neue Kartenevidenz, frühe Umfahrung, notwendiger Nahbereichshalt mit zulässiger Fortsetzung, geometrisch lösbare Wand-/Ecksituation, physische Durchfahrt und Weitererkundung. Fälle dürfen getrennt aufgebaut werden. Hindernisbewältigung ist Teil der Zielbearbeitung, keine Funktion, auf die erst nach einer perfekten Phase A gewartet wird.

Karte, Ziele, Begründungen, echte Fahrspur und verbleibende Aufgaben sichtbar aus vorhandenen Werkzeugen nachweisen. Neue Kartenmeldungen, freie Zellzahl, kurze Drehungen oder Nav2-SUCCESS allein sind kein Gesamterfolg. Kartenkorrektur/Drift von Beobachtungsgewinn trennen. Kriterien und Wiederholungen vor der Abnahme festlegen; keine erfundene Erfolgsquote.

**Ergebnis:** Stufe 3 nur für tatsächlich erfüllte metrische Kern- und Schutz-/Fortsetzungsfälle grün. Automatische Portal-/Regionsidentität ist dabei nicht mehr Voraussetzung, bleibt jedoch als eigener semantischer Rest sichtbar. Danach keine allgemeine Optimierungsrunde.

### Schritt 4 – WE-M4, WE-M5 und WE-M6 mit getrennten Nachweisen

| Meilenstein | Metrischer Nachweis | Ergänzender semantischer Nachweis |
|---|---|---|
| WE-M4 | Zimmer → Flur → weiteres Zimmer → zurück in denselben Flur; wirkliche Passage und weiterer Fortschritt | Stabile Portal-/Regionsidentität, Seitenumkehr und Wiedererkennung bleiben separat offen, bis geprüft |
| WE-M5 | Konsistente Karte plus metrische Aufgaben/Teilstand speichern; gültige Wiederlokalisierung und kontrollierte Fortsetzung | Portal-/Regionsevidenz und manuelle Namen korrekt zuordnen; optionaler Datenteil darf metrische Wiederaufnahme nicht erzwingen |
| WE-M6 | Zugänglichen vereinbarten Umfang wiederholt erschließen; Restaufgaben und Teilabschluss korrekt ausweisen | Semantische Vollständigkeit nur aus geprüften Identitäten ableiten, nicht aus physischer Durchfahrt allein |

Metrische Teile dürfen ohne Abschluss der semantischen Teile fortgeführt werden. Ein gesamter historischer Meilenstein wird dadurch nicht rückwirkend grün. Präzisierungen und fortgeltende Detailkriterien stehen in MEILENSTEINE.md. WE-M1/M2 bleiben erhaltene passive Semantikarbeit; WE-M7 ist weiterhin nachgelagerte App-Transparenz, keine Voraussetzung des geometrischen Kerns.

### Schritt 5 – Kundentauglichkeit gesondert prüfen

Längere Einsätze, wechselnde Aufbauten/Startpositionen, Ressourcen, Wiederanläufe und kontrollierte Ausfälle separat abnehmen. Zielgrößen für Eingriffe, Missionsabschluss, Recoverydauer/-häufigkeit und sichere Fehlerreaktion vorab festlegen. Häufiges Neustarten ist keine Zuverlässigkeit. Offene Bewegungswidersprüche und Shutdown-/Speicherfehler nicht verschwinden lassen. Eine gute Wohnungsfahrt ist keine Auslieferungs- oder Zertifizierungsfreigabe.

## 4. Fehler-, Fortschritts- und Abschlussvertrag

Schutzkette entscheidet über momentane Bewegung; vorhandene Subsysteme über begrenzte Wiederherstellung; Missionssteuerung über Auftragserhalt, Neuplanung und Hilfebedarf.

- **Aufgabe unerledigt:** Timeout oder Nichterreichbarkeit nicht automatisch als Hardwaredefekt bewerten. Kind terminal beenden, Stillstand und aktuelle Betriebs-/Pose-/Routenlage prüfen. Bei nachgewiesener Fortsetzbarkeit Aufgabe begrenzt zurückstellen und andere zulässige Arbeit wählen. Keine Hindernisursache erfinden, nur um LOCAL_BLOCKED zu erzwingen.
- **Unzureichender Fortschritt:** kleine Drehungen oder Odometriesummen dürfen kein unbegrenztes Festhalten rechtfertigen. Aufgabenfortschritt von lokalem Bewegungsfortschritt trennen; geometrisch nötige Drehung/Transit nicht pauschal als Fehler behandeln. Begrenzte Neuplanung und Versuche, kein Stop-and-go-Flattern.
- **Recoverbare Quellenlücke:** notwendiger Halt, Auftrag halten, begrenzt wiederherstellen; stabile neue Messungen, Kalibrierung, Stillstand und aktuelle Situation vor Fortsetzung prüfen. Kein altes Goal/Command wiederbeleben.
- **Ungeklärte notwendige Quellen/Pose, nicht terminales altes Kind, kritischer Aktuatorfehler:** keine Wiederanfahrt aus bloßer Aufgabenpräferenz. Sicherer Teilstand und konkreter Hilfebedarf sind zulässig, auch ohne bewiesenen Kabelbruch.
- **Not-Aus oder Nutzerabbruch:** keine automatische Rücksetzung oder Fortsetzung.

Genau ein aktives Kind. Verspätete Antworten und alte Kartenarbeit dürfen neuere Zustände nicht überschreiben. Gültige Ziele bei normalen Kartenupdates revalidieren statt allein wegen neuer Revision/neu berechneter Rangfolge fortwährend canceln. Echte Kontextwechsel, unzulässige Wege und ungültige notwendige Quellen bleiben sperrend. Keine alten Daten frisch stempeln.

Gesamtzeit-, Versuchs-, Weg- und Energiebudgets werden bei HOLD, Kindwechsel oder neuem Kandidaten nicht zurückgesetzt. Konkrete Werte vor Tests dokumentieren; heutige Schutz-/Frische-/Geschwindigkeitsgrenzen nicht pauschal erhöhen. Kein automatischer Rechner-/Stack-Reboot als Lösung.

**Abschluss:** Keine erreichbare relevante Frontier über ein definiertes gültiges Beobachtungsfenster und keine ungeklärten relevanten Restaufgaben ist ein begründeter metrischer Abschlusskandidat. Fehlende Daten, leere Auswahl durch Filter/Blacklist, blockierte Übergänge oder erschöpfte Budgets bedeuten nicht vollständig erkundet. Erreichbares erkundet, vorläufig blockiert, unbekannt/ungeklärt und ausgeschlossen getrennt ausweisen. Keine absolute Vollständigkeit hinter unbekannten geschlossenen Türen behaupten. Speicherfreigabe, metrischer Abschluss, Flächenabdeckung und semantischer Abschluss sind getrennte Aussagen.

## 5. Regeln gegen Verzetteln und Laborarbeit

Ein Integrationsverantwortlicher, ein Kandidat, ein aktueller Auftrag. Nur betroffene Funktionen ändern; keine pauschale Neuinstallation, neue Navigation oder gleichzeitige OAK-/Arm-/GUI-Baustelle. Neue reine Policy-/Datenadapter innerhalb des vorhandenen Explorers sind für diese Entkopplung erlaubt, kein konkurrierender Navigator.

LAB-1 gilt auftragsbezogen und agentenübergreifend. Unveränderte Not-Aus-/Platz-/Preflight-/Recorder-/Fahrt-Erlaubnisfragen nicht wiederholen. Technische Zustände selbst prüfen, keine physische Stellung erfinden. Nur tatsächlich notwendige, nicht selbst ausführbare Bedienhandlung oder geänderten Umfang konkret klären. Rein lesender Vorlauf ohne Aktor-Schreibprozess bleibt gemäß LAB-1 möglich. Diese Dokumentationsänderung startet keine Hardware; der nächste Softwareauftrag ist ausdrücklich gerätefrei.

Reale Karten/Bilder/Bags lokal halten. Vor Commit/Push auch die ausgehende Historie prüfen: private lokale Berichtscommits nicht als Vorfahren veröffentlichen. Nicht unkoordiniert pullen/mergen, keinen Force-Push oder Datenverlust erzwingen. Eine neue Planversion darf keine ungeprüfte Runtime aktivieren.

## 6. Nachweise und Abschluss eines Pakets

Getrennt führen: dokumentiert, software_geprüft, zielsystem_geprüft, physisch_abgenommen sowie offen/blockiert. Synthetische Daten, Replay und reale Fahrt unterscheiden. Erfolg gilt nur für den genannten Umfang; keine unbelegten Prozentsätze oder Zusage „nur noch ein Fix“.

Jeder Abschluss: Ausgangs-/Ergebnis-SHA, tatsächliche Profil-/Paketauflösung, betroffene Komponenten, Tests mit Ergebnissen, Evidenzpfade, unveränderte Grenzen, Rückfall und genau ein nächster Schritt. Bei einer neuen Implementierung muss das Ergebnis Code plus verbundener Funktionsnachweis sein, nicht allein ein weiterer Messplan.

## 7. Pflege und sofortiger Einstieg

Aktuellen Auftrag in STATUS und AGENTENAUFTRAG führen. Frühere Originale sind unverändert im Archiv verlinkt. Historische Ursachenlücken bleiben offen; sie verhindern keine ausdrücklich beschlossene, separat nachweisbare Funktionsverbesserung.

**Jetzt:** Das gerätefreie Umsetzungspaket „Metrische Frontiererkundung ohne Portalpflicht“ aus AGENTENAUFTRAG ausführen. Noch keine neue Fahrt, kein Merge und kein dauerhafter Installwechsel aus diesem Plan ableiten.

**Änderungsprotokoll:**
- 27.09.2026: v1.0 Konsolidierung, geordnete Recovery, Kernabnahme, WE-M4/M5/M6 und getrennte Produktreife.
- 27.09.2026: v1.1 unbekannter historischer HWT-Erstwert kein Gate für definierten Recoveryfall.
- 28.09.2026: LAB-1 als Arbeitsregel ergänzt.
- 30.09.2026: v1.2 metrischer Erkundungskern vor verpflichtender Semantik; bewährte Bausteine wiederverwenden; Taskfortsetzung und getrennter metrischer/semantischer Abschluss; alter Diagnoseauftrag durch begrenztes Softwarepaket ersetzt. Nur Dokumentation, keine neue Funktionsabnahme.
