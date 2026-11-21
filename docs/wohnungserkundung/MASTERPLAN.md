# WE-1 – Integrationsmasterplan für Amadeus

**Version 1.3 · 02.10.2026 · chris01-byte/Roboter_ws**

> **Nutzerentscheidung 15.10.2026 (Planänderung durch den Auftraggeber):**
> Ein Kundenroboter muss sich selbst heilen und darf den Gesamtprozess nur in
> Ausnahmen stoppen. Nicht erfasste Kartenzellen sind kein Blocker; die VL53
> dienen vorrangig dem Ausweichen. Begrenzte Rückwärtsfahrt entlang der eigenen
> Spur ist erlaubt. Umsetzung als zusätzliche, umschaltbare Strategie
> `self_healing` neben dem AP06-Pfad; AP06-Manifestläufe bleiben mit
> Standardparametern vergleichbar. Verbindlich ausgeführt in
> [KONZEPT_SELBSTHEILUNG.md](KONZEPT_SELBSTHEILUNG.md); Sicherheitsregeln aus
> AGENTS.md und LAB-1 gelten unverändert.
>
> **Nutzerentscheidung 15.10.2026, Nachtrag:** `self_healing` ist die
> Hauptlinie der Erkundung. Der AP06-Pfad (`metric_frontier`, AP-01…AP-06)
> wird eingefroren: keine Weiterentwicklung, vollständig erhalten und
> umschaltbar. Bestätigung nach einem realen Kurztest; Kriterien in
> [KONZEPT_SELBSTHEILUNG.md](KONZEPT_SELBSTHEILUNG.md).
>
> **Abnahmeänderung durch den Auftraggeber (15.10.2026):** Für die Hauptlinie
> gilt die dreistufige Abnahmeleiter Labor → Robustheit (Simulation) → echte
> Wohnung aus KONZEPT_SELBSTHEILUNG.md §11. Das bisherige AP06-Kriterium
> (≥ 95 % Referenzfläche, ≤ 0,10 m, beide Türen inklusive Heck in einem Lauf)
> gilt nur noch für den eingefrorenen AP06-Pfad. Schutzforderungen bleiben.
>
> **Nutzerentscheidung 09.11.2026, Nachtrag – Fahrplan (roter Faden):** Für
> die Selbstheilungslinie gelten ab jetzt die Arbeitsregeln und die
> Schrittfolge in **§9 Fahrplan der Selbstheilungslinie**. Kern: auf dem
> Roboter je Realtest genau eine Verhaltensänderung, die nächste Verbesserung
> entsteht parallel in der Simulation, und der STATUS führt oben genau eine
> Arbeitsliste (aktiv, in Simulation, geparkt, erledigt). Jeder Auftrag
> bezieht sich auf einen Schritt dieses Fahrplans.
>
> **Nutzerentscheidung 19.11.2026 – zweite, getrennte Entwicklungslinie
> „KI-Erkundung“:** Eine KI auf dem vorhandenen KI-Rechner soll die Ziel- und
> Suchwahl der Erkundung übernehmen. Das geschieht als komplett neue Linie im
> eigenen Ordner `ki_erkundung/`. Die bisherige Entwicklung bleibt erhalten
> und unbeeinflusst; die Hauptlinie `self_healing` läuft mit §9 weiter.
> Verbindlich in **§10** und in
> [ki_erkundung/KONZEPT.md](../../ki_erkundung/KONZEPT.md).
>
> **Nutzerentscheidung 19.11.2026 (spät) – Hauptlinie geparkt, KI-Erkundung
> ist die aktive Arbeit:** Nach SH-9 (kein Ziel erreicht, Tür nicht
> durchfahren) wird die Hauptlinie `self_healing` geparkt: keine
> Weiterentwicklung, kein Auftrag, alles bleibt erhalten und umschaltbar.
> Der Rückschritt gegenüber dem 08.11. wird vorerst nicht eingegrenzt.
> Gearbeitet wird an der KI-Erkundung (§10). §9 beschreibt den Stand der
> geparkten Linie; seine Arbeitsregeln gelten für Realtests weiter.

**Verbindliche Zielrichtung:** Hardwareanbindung und bewährte ROS-Basis erhalten; die metrische Erkundung vereinfachen; geeignete Open-Source-Komponenten gezielt integrieren. Fortschritt wird durch bestandene Abnahmen belegt. Zusätzliche Sonderfälle ohne nachgewiesenen Nutzen sind keine Integrationsstrategie.

Dieses Dokument ist die vom Nutzer angeforderte Fortschreibung des vorhandenen MASTERPLAN v1.2. Es wird bei der Übernahme unter `docs/wohnungserkundung/MASTERPLAN.md` die einzige aktuelle Architektur- und Reihenfolgevorgabe. Seine Erstellung ist keine Softwareimplementierung oder Realabnahme. Der erste Auftrag ist ausschließlich gerätefreie Softwarearbeit.

## 1. Produktziel und Grenze des Auftrags

Amadeus soll aus einer normalen zulässigen Startposition eine vorher unbekannte, zugängliche Innenraumwohnung autonom metrisch kartieren: selbst Beobachtungspositionen wählen, sie sicher erreichen, neue Messungen auswerten, durch geeignete offene Verbindungen weitererkunden und mit nachvollziehbarem Ergebnis enden. Manuelles Vorkartieren, Umsetzen oder vorgegebene Wegpunkte erfüllen dieses Ziel nicht.

Das Ziel gilt für einen vorab beschriebenen Betriebsbereich: befahrbare Böden, geeignete Durchgänge, konkrete Sensorabdeckung und vereinbarte Hindernisarten. Geschlossene unbekannte Räume und sensorisch nicht erschließbare Bereiche werden als offen oder ausgeschlossen ausgewiesen. Der Umfang darf nach einem Fehllauf nicht verkleinert werden, nur um denselben Lauf als erfolgreich auszugeben.

Kartierung verlangt geeignete Sicht auf die Umgebung, nicht das Überfahren jeder freien Bodenstelle. Raumnamen, Portalidentitäten, Manipulation und Reinigung sind keine Voraussetzung. Zugängliche Folgeräume müssen tatsächlich erschlossen werden; ein Blick durch die Tür ersetzt nicht die notwendige Passage und Beobachtung dahinter.

## 2. Verbindlichkeit und Dokumentführung

`MUSS` bezeichnet eine Abnahmebedingung. `DARF NICHT` bezeichnet eine ausgeschlossene Vorgehensweise. Abweichungen werden vor abhängiger Umsetzung mit Grund, betroffenen Kriterien und Alternative dokumentiert. Routineentscheidungen innerhalb eines Arbeitspakets trifft der Agent selbstständig. Architekturänderungen oder das Herabsetzen zugesagter Abnahmen benötigen eine ausdrückliche Änderung dieses Plans durch den Auftraggeber; keine stillschweigende Umdeutung durch einen Folgeprompt.

| Dokument | Aufgabe |
|---|---|
| `AGENTS.md`, `docs/LABORMODUS.md` | Allgemeine Arbeitsregeln und bestehender auftragsbezogener Laborrahmen |
| `docs/wohnungserkundung/MASTERPLAN.md` | Diese einzige aktuelle Ziel-, Architektur- und Reihenfolgevorgabe |
| `docs/wohnungserkundung/STATUS.md` | Einziger aktueller Iststand, Nachweise, Blocker und genau ein nächster Auftrag |
| `docs/wohnungserkundung/AGENTENAUFTRAG.md` | Vollständiger ausführbarer Auftrag für das aktive Arbeitspaket |
| `docs/wohnungserkundung/MEILENSTEINE.md` | Bestehende WE-D0/WE-M0–WE-M7-Abnahmen mit Verweisen auf diesen Plan |
| `docs/WOHNUNGSERKUNDUNG_STRATEGIE.md` | Produktumfang und Gesamtstrategie, mit dieser Planfassung synchronisiert |
| `docs/PROJECT_MEMORY.md` | Entscheidungsjournal; frühere Aufträge bleiben historische Quellen |
| `docs/ROBOT_TRANSFER.md` | Tatsächliche Installation und Rückfall am Zielsystem; kein Sollzustand |
| `ki_erkundung/KONZEPT.md`, `ki_erkundung/STATUS.md` | Getrennte Linie KI-Erkundung (§10, seit 19.11.2026): eigenes Konzept und eigener Iststand; für die Hauptlinie nicht maßgeblich |

Bei Übernahme werden die bisherigen vier WE-Dokumente bytegleich mit Herkunfts-SHA unter `docs/wohnungserkundung/archive/20261002-v1.2/` archiviert. Der bisherige STATUS bleibt als Historie erhalten; ein klarer aktueller Abschnitt steht vorn. Alte Aufträge dürfen danach nicht erneut ausgeführt werden. Aktuelle Verweise und Aussagen in AGENTS, MEILENSTEINE und Gesamtstrategie werden synchronisiert; historische Entscheidungen bleiben unverändert erhalten. Es gibt keinen zweiten aktuellen Status und keine zusätzliche Meilenstein-Roadmap.

**Ausdrückliche Änderungen gegenüber v1.2:** Die reine Offline-Beschränkung für Fremdcode wird für die in AP-04 beschriebene Frontier-Komponente aufgehoben. Deren geprüfte Integration ist vorgesehen; ein kompletter Fremdstack bleibt außerhalb des Plans. Die frühere Empfehlung, historische Frontierbildung zu übernehmen, ist wegen des nachgewiesenen Schwerpunktfehlers nur noch eine Vergleichsreferenz. Geometrieprüfung und Abschlussvertrag werden fachlich konsolidiert; ihre heutige Implementierung ist nicht unveränderlich. Schutzwirkung, eindeutige Zuständigkeiten, gültige Daten und ehrliche Nachweise bleiben verbindlich.

LAB-1 wird durch diesen Plan weder widerrufen noch erweitert. Gültige bestehende Autorisierungen sind bei späteren konkreten Laboraufträgen zu berücksichtigen; unveränderte Standardfreigaben werden nicht erneut verlangt. Dieser erste Softwareauftrag enthält weder Gerätezugriff noch Deployment oder Fahrt. Technischer Nachweis, Auftragsumfang und tatsächliche Hardwarewirkung bleiben getrennt.

## 3. Ausgangsbasis und bekannte Befunde

Untersuchter Integrationsstand: `08a4b9ac0b7a128ced2199f20976f3aa92ea55fe` auf `feature/hwt-hold-recovery-resume`. Historische Teilfunktionsreferenz: `1d91229dc10ff4bb791938d49aae8e9808a5dfff`. Älteres untersuchtes main: `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1`. Ein Agent MUSS den tatsächlichen aktuellen Stand prüfen; er darf einen neueren Stand weder blind zurücksetzen noch neue Arbeit gegen das alte main entwickeln.

| Befund aus der Gegenprüfung | Einordnung | Zuständiges Paket |
|---|---|---|
| HWT-Zeitkorrelation kann bei Schedulingpause rückläufige Stempel erzeugen | An Originalmethoden reproduziert; genaue historische Schedulerfolge unbekannt | AP-01 |
| Wachsende Karte wird mit alter Egress-Maske verknüpft | Reproduzierter Arrayfehler | AP-02 |
| Unterschiedliche aktive/passive Zeitpfade, unvollständiger gemeinsamer Nachweis | Code- und Integrationsbefund | AP-02, AP-06 |
| Kürzester ungeeigneter Weg führt zum Ausschluss trotz zulässigen Umwegs | An Originalmethoden reproduziert | AP-03 |
| Zusätzliche Bewegungsreserven sperren synthetische 68-cm-Tür | Reproduzierter Vertragskonflikt; kein Realfahrnachweis | AP-03 |
| Startsperre zwischen fehlender Beobachtung und benötigter Bewegung | Dokumentierter Realbefund; mögliche Alternativbewegung offen | AP-03, AP-06 |
| Ringförmige Frontier erzeugt ungeeignetes Schwerpunktziel | Mit vollständiger aktueller Auswahl reproduziert | AP-04 |
| Erfolgspfad fehlt; Ankunft wird mit Beobachtung verwechselt | Expliziter Entwicklungsstand und Policyproblem | AP-05 |

1.718 von 1.719 ausgewählten bestehenden Tests des untersuchten aktuellen Stands bestanden in der Cloud. Der verbleibende JSON-Tiefentest des Missionsmanagers ist separat zu erfassen; er erklärt die Erkundungsfehler nicht. Grüne Testzahlen ersetzen die neuen konkreten Abnahmen nicht. Cloud-Humble/Python 3.12 ist nicht automatisch Jetson-Humble/Python 3.10.

## 4. Zielarchitektur und feste Grenzen

Der vorhandene Ausführungspfad bleibt: Mission Manager → vorhandener BT → ein Explorer → ein aktives Nav2-Kind → bestehende Bewegungs- und Schutzkette → Basis. SLAM arbeitet kontinuierlich; EKF und TF behalten eindeutige Besitzer.

Innerhalb des Explorers werden drei Verantwortlichkeiten klar getrennt: Kandidatengewinnung, Zulässigkeit durch konsistente Planung und Geometrie, sowie Bewertung des Missionsfortschritts. Die externe Frontier-Komponente liefert Vorschläge und Gründe. Sie übernimmt weder Motorzugriff noch Mission, Nav2-Dispatch, globalen Cancel oder Gesamterfolg.

MUSS erhalten bleiben: Hardwareanbindung, bewährte Encoder-/EKF-Funktionen, gültige Quellen-/Karten-/Posebindung, eindeutiger Auftragseigner, bestätigte Kindbeendigung, Stop-/HOLD-Verträge und konsistente Kartenverwaltung. Änderungen daran sind getrennt zu begründen und zu prüfen.

DARF NICHT eingeführt werden: zweiter Navigator oder Supervisor, direkte Motorbefehle zur Umgehung von Nav2, automatische Freiraumblasen, blindes Löschen von Costmaps, erfundene gesunde Quellen, versteckte Pflicht-Raumsemantik oder unbegrenzte Wiederholungen. Unbekannte Außenbereiche werden nicht durch Annahmen zu freiem Raum.

Zeitstempel dürfen nicht durch Klemmen, Wiederveröffentlichen alter Daten oder Umstempeln auf jetzt gesund erscheinen. Eine verworfene Probe ist keine neue Probe. Tatsächliche Mess-/Empfangszeit, Veröffentlichung und Verbrauch sind unterscheidbar zu halten.

Ein zurückgewiesener Punktpfad beweist nicht die Nichterreichbarkeit des orientierten Fahrzeugs. Planung und Zulassung MÜSSEN dieselbe Kontur, Bezugspose und belegte Reglerabweichung berücksichtigen. Unabhängige letzte Kollisions-/Stoppprüfungen bleiben erhalten; sie ersetzen keinen ausführbaren Planer.

## 5. Arbeitsreihenfolge und Übergänge

AP-01 bis AP-06 sind begrenzte Arbeitspakete innerhalb der vorhandenen WE-Meilensteine, keine neuen Produktmeilensteine. Es gibt einen aktiven Implementierungsauftrag. Unabhängige Quellprüfung und Offline-Vergleiche dürfen parallel erfolgen. Sie aktivieren keine spätere Runtime.

**Reihenfolge:** AP-01 → AP-02 → AP-03 → AP-04 → AP-05 → AP-06. Ein bestandenes Softwarepaket erlaubt das nächste Softwarepaket; dafür wird kein unerreichbarer vorgezogener Wohnungsfahrnachweis verlangt. Die gemeinsame reale Basis wird vor Bewegung in AP-06 geprüft. Ein bekannter Hardwareblocker bleibt sichtbar und verhindert dort abhängige Bewegung, nicht jede unabhängige Softwarearbeit.

| Paket | Ergebnis | Bestehender WE-Bezug |
|---|---|---|
| AP-01 | Korrekte HWT-Empfangszeitzuordnung mit Regressionen | WE-M0; Erhalt M3-Recovery |
| AP-02 | Kartenlebenszyklus und Quellenvertrag konsistent | WE-M0, WE-M3 |
| AP-03 | Ausführbare Planung für Umweg, Engstelle und Bootstrap | WE-M3; Voraussetzung WE-M4 |
| AP-04 | Vergleich und begründete Wahl eines schlanken Frontier-Kerns | WE-M3 |
| AP-05 | Beobachtungsfortschritt, Abschluss und Wiederaufnahme | WE-M3, WE-M5; Mindesttransparenz WE-M7 |
| AP-06 | Geschlossene Gesamtprüfung und begrenzte reale Abnahmen | WE-M0/M3/M4/M5/M6; Ergebnisdarstellung WE-M7 |

### AP-01 – HWT-Zeitfehler gezielt reparieren

Ziel ist eine nachvollziehbare Abbildung des hostseitigen Antwortempfangs auf ROS-Zeit. Die zeitversetzten Uhrabfragen dürfen keinen falschen terminalen Rücklauf erzeugen. Physische Sensorabtastzeit wird nicht behauptet.

Lieferung: minimale Reparatur im HWT-Rawpfad, gegebenenfalls kleiner privater Hilfsbaustein, deterministische Regressionen und dokumentierte Unsicherheits-/Sprungbehandlung. Gesunde Daten werden veröffentlicht, echte ungültige Zeitbezüge nicht verdeckt. Fristen, Encoder, EKF, Bias, Mission und allgemeine Recovery bleiben außerhalb des Umbaus.

Abnahme: ursprüngliches Gegenbeispiel vor Änderung nachgewiesen; nach Änderung kein falscher terminaler Fehler, korrekter Zeitbezug und belegte Fortsetzbarkeit bei gültiger Folgeprobe; unabhängige echte ROS-Zeitsprünge, alte/ungültige Empfangszeiten und Fristverletzungen werden erkannt. Bestehende betroffene Positiv-/Negativtests bestehen. Details im ersten Agentenauftrag.

### AP-02 – Karten und gemeinsame Quellen konsistent behandeln

Kartenidentität, Sitzung, Frame, Auflösung, Ursprung, Abmessungen und Revision erhalten explizite Zustandsübergänge. Normales Kartenwachstum darf weder crashen noch alte räumliche Masken ungeprüft wiederverwenden. Harmlose Updates sollen gültige Ziele erhalten; echte Kontextwechsel invalidieren betroffene Arbeit und ignorieren verspätete Ergebnisse.

Für HWT, Encoder, TF, Gate und Explorer wird ein gemeinsames Zeit-/Gültigkeitsbudget aus vorhandenen Verträgen erfasst: Empfang, IO-Dauer, Verarbeitung, DDS-Verbrauch, Frische und Kontinuität. Aktiver und passiver Pfad werden getrennt aufgeführt. Es entsteht keine neue allgemeine Health-State-Machine. Abweichungen werden gezielt in kleinen Änderungen bearbeitet; reine Timeout-Erhöhungen erfüllen das Paket nicht.

Abnahme: 100×100 → 100×101 sowie Wachstum mit verschobenem Ursprung; Auflösungs-/Sitzungswechsel; verspätete Arbeit; verlorene notwendige Quelle; gültige Folgeupdates. Keine Arrayausnahme, keine falsch gültige alte Egress-Maske, keine stillschweigende neue Freiraumannahme. Paket-/Overlay- und Schnittstellenauflösung sind reproduzierbar. Eine belastbare aktive Zeitmessung am Jetson bleibt als ausdrücklich offener AP-06-Nachweis erfasst.

### AP-03 – Bewegung und autonomer Start zusammenführen

Ein geeigneter Nav2-Planer-/Controllerpfad muss tatsächlich ausführbare Routen liefern. Der eigene Vorfilter darf zulässige Ziele nicht aufgrund eines einzelnen ungeeigneten kürzesten Wegs endgültig verwerfen. Kontur, Achsbezug, Drehung, Rückwärtsanteil, Trackingabweichung und Rasterreserve werden gemeinsam begründet. Die Auswahl einer konkreten vorhandenen Planer-/Controllerkombination erfolgt anhand der Fälle, nicht nach Paketname.

Pflichtfälle: Hindernis mit längerem zulässigem Umweg; gerade 68-cm- und 80-cm-Tür als synthetische Vergleichsfälle; Drehung in zu engem Durchgang; freier Zielbereich hinter der Tür; beobachtete und unbekannte Außenbereiche. Die bisherige 1,6-m-Testtür genügt nicht. Für die positive enge Passage muss ein durch Plan und Regler belegter zulässiger Weg entstehen. Falls das mit dem vorgesehenen Fahrmodell nicht erreichbar ist, ist das Ziel blockiert und konstruktiv zu lösen; Reserven einfach zu entfernen zählt nicht.

Der Bootstrap unterscheidet bekannte eigene Körpergeometrie von unbeobachtetem Außenraum. Er muss eine belegbar zulässige erste Beobachtungsbewegung ermöglichen oder die konkret fehlende Beobachtung benennen. Ein voller Rundblick ist nur eine Option bei geeigneter Geometrie. Wenn die Sensoranordnung notwendige Bereiche nicht erfassen kann, wird eine begründete Änderung von Sensorposition/Abdeckung als separates Paket vorbereitet; keine weitere Serie identischer Fehlstarts.

Abnahme: echte Nav2-Planung und Regelung in einer geschlossenen synthetischen Umgebung für positive und negative Fälle, dokumentierte Bahnabweichung und Konturabstände, erreichter Beobachtungsbereich. Vorgegebene Ziele sind für diese Komponententests erlaubt, gelten aber nicht als autonome Erkundung. Die belegte Bahnabweichung gilt für das dokumentierte Simulationsmodell; ihre Übertragbarkeit auf den realen Roboter wird in AP-06 geprüft. Physische Türfähigkeit und realer Start bleiben bis dahin offen.

### AP-04 – Externen Frontier-Kern vergleichen und integrieren

Erster Kandidat ist `mertgulerx/frontier_exploration_ros2`, zunächst gepinnt auf `418e9717564a895214275e088ea7075b8ac88f64`. Der Kern wurde in der Analyse unter Humble gebaut; 134 vorhandene Tests bestanden. Das ist keine Jetson- oder Fahrabnahme. Ein Pinwechsel braucht begründeten Vergleich, reproduzierbare Abhängigkeiten und Lizenz-/Änderungsnachweis.

Verglichen werden derselbe aktuelle eigene Kern und der externe Kandidat, optional `explore_lite` als einfache Referenz. Eingaben, zulässige Sensorinformationen, Planer, Schutzbedingungen und Budgets sind identisch. Der externe Kern darf nicht dadurch gewinnen, dass er weniger Geometrie prüft oder unbekannte Außenfläche als frei behandelt.

Der Adapter erhält Karte mit vollständiger Geometrie/Identität, gültige Pose und Scope; er liefert Kandidaten mit Bezug zur Beobachtungsgrenze und nachvollziehbaren Ablehnungsgründen. Ein dünner C++-Adapter oder reiner Kandidatendienst ist zulässig. Er darf keine eigenen Nav2-Aufträge senden. Bekannte Grenzen werden behandelt: Zielabstand zur unbekannten Fläche, volle Fahrzeugkontur, Kartenursprungsrotation, echte Sensorreichweite/Sicht, Frische und optionale Kartenvorverarbeitung. Gedrehte Origins werden korrekt transformiert oder ausdrücklich als nicht unterstützt zurückgewiesen, niemals still ignoriert.

Abnahmefälle: freie Insel mit ringförmiger Frontier, konkave Grenze, langer Rand mit mehreren geeigneten Beobachtungspositionen, blockierter bester Kandidat mit zulässiger Alternative, wachsende Karte, neue Beobachtungsmöglichkeit an besuchter Stelle, fehlende optionale Semantik. Geprüft wird hier die Kandidaten-/Adapterebene: veränderte Kartenevidenz muss erneut geeignete planbare Vorschläge erlauben, auch an einer früher besuchten Position; mehrere Kartenstände erzeugen passende Folgeentscheidungen. Der Frontierkern darf dies nicht dauerhaft sperren. Die missionseigene Erledigungs-/Wiederbeobachtungspolitik folgt in AP-05, die vollständige autonome Beobachtungskette in AP-06. Die bloße Zahl ausgegebener Punkte ist kein Qualitätsmaß.

**Entscheidungspunkt:** Übernahme, wenn alle Pflichtfälle bestehen, mindestens ein belegter Vorteil gegenüber dem unveränderten eigenen Kern erreicht wird und die Integration nicht einen zweiten Missions-/Navigationsapparat benötigt. Andernfalls genau den Blocker beheben oder die kleine eigene Kandidatengewinnung begrenzt korrigieren und erneut vergleichen. Der Agent darf innerhalb dieser festgelegten Alternative entscheiden und begründen. Ein weiterer Vollstackwechsel ist keine Ersatzhandlung. Die Entscheidung beendet den Vergleich; keine unbefristete Sammlung weiterer Explorer.

### AP-05 – Fortschritt, Abschluss und Persistenz schließen

Ankunft am Ziel, tatsächliche Beobachtung und erledigte Erkundungsaufgabe sind getrennte Ereignisse. Eine Ankunft ohne brauchbare neue Beobachtung darf eine Gegend nicht dauerhaft erledigen. Kartenänderungen können eine begrenzte Neubewertung ermöglichen; neue IDs dürfen keine endlosen Wiederholungen oder Budgetresets erzeugen.

Gesamterfolg bedeutet: innerhalb eines vorab festgelegten gültigen Beobachtungsfensters keine relevante erreichbare Restaufgabe und keine ungeklärte zugängliche Verbindung. Unbekannte Zellen hinter Wänden sind kein pauschales Erfolgshindernis. Fehlende Daten, ausgeschöpfte Versuche, ungeklärte Blockaden, ausschließlich gefilterte Kandidaten oder Budgetende sind kein Gesamterfolg.

Ergebniszustände unterscheiden mindestens metrischen Erfolg, nutzbaren Teilstand, vorläufig blockiert/Hilfebedarf, Fehler und Nutzerabbruch. Konkrete Interfacefelder werden kompatibel oder versioniert eingeführt. Die vorhandene App zeigt diese Zustände korrekt; kosmetischer App-Umbau bleibt nachgelagert. Rohkarte, Beobachtungsgewinn, befahrene Fläche und optionale Semantik werden nicht vermischt.

Karte, Identität/Sitzung, offene Aufgaben, Versuche und Gesamtbudgets werden über vorhandene Speichermechanismen konsistent gesichert. Laden startet keine Fahrt. Beschädigte oder fremde Daten, nicht unterstützte Version, fehlende Pose und unterbrochene Speicherung werden behandelt; die letzte gültige Sicherung bleibt erhalten. Wiederaufnahme erfordert aktuelle Lokalisierung, Quellen und gültigen Auftrag.

Abnahme: positiver tatsächlicher Erfolgszweig mit passendem Actionzustand; alle negativen Abschlussfälle; Ankunft ohne Sichtgewinn; spätere sinnvolle Wiederbeobachtung; terminaler Cancel und verspätete Antworten; Speichern/Laden/Unterbrechung einschließlich Map-ID-Fehler; korrekt angepasste Ergebnisverbraucher und Teilkartenspeicherung. Eine mangels Plattformzugriff offene native iOS-Laufzeitprüfung bleibt unter WE-M7 separat sichtbar und sperrt keine unabhängige Kernprüfung. ROS-Vertragstests allein sind keine App-Laufzeitabnahme. Metrischer Abschluss behauptet keine abgeschlossene Raumsemantik.

### AP-06 – Geschlossene Kette und reale Produktabnahme

Zuerst arbeitet die vollständige Mission/BT/Explorer/Nav2/SLAM-Kette in einer geschlossenen Simulation: Sensordaten und Karte ändern sich als Folge der tatsächlich simulierten Bewegung. Replay und FakeNav2 bleiben ergänzende Tests. Pflicht sind zwei Räume mit Verbindung/Flur, enge Passage, Umweg, blockierte Alternative, Kartenwachstum und Abschluss. Mindestens drei unterschiedliche zulässige Startposen werden vorab festgelegt; alle müssen ohne manuelle Zielvorgabe bestehen.

Anschließend wird der exakt zugeordnete Kandidat am Zielsystem geprüft: reproduzierbarer Build, aktuelle installierte Präfixe, gültige Quellen/TF, Stillstand und Schutzkette. Passiver Erfolg allein beweist den aktiven Pfad nicht. Aktive Last, Wechsel des Gerätebesitzers und Datenankunft am Verbraucher werden innerhalb des konkreten technischen Testauftrags nachgewiesen. Reale Bewegung setzt dessen gültigen Umfang und die technischen Vorbedingungen voraus; der vorliegende Plan startet keine Fahrt.

Die reale Folge lautet: Kaltstart ohne Vorkarte → erste nützliche autonome Beobachtung → mindestens drei selbst gewählte Beobachtungsaufgaben → vollständige Passage samt Heck → Weitererkundung → Drei-Bereich-Rundweg gemäß WE-M4 → konsistentes Ergebnis. Hindernis mit möglichem Umweg und notwendiger Halt mit zulässiger Fortsetzung gehören in geeignete getrennte Aufbauten. Konkrete Fristen, Versuchsbudgets, Eingriffsdefinition und Abbruchkriterien werden vor jedem Lauf festgehalten.

WE-M6 verlangt weiterhin mindestens zwei getrennte beaufsichtigte positive Läufe ohne manuelle Navigationsübernahme, einschließlich anderer zulässiger Startpose. Ein notwendiger Bedien-/Schutzeingriff verhindert den autonomen Positivnachweis dieses Laufs; er wird nicht verschwiegen. Reale Wiederaufnahme ergänzt WE-M5. Gefährliche Fehlerfälle werden zunächst isoliert geprüft, reale Injektionen benötigen einen konkreten begrenzten Auftrag.

Abnahme belegt Bewegung, Karte, neue Beobachtung, verbleibende Aufgaben, Kindzustände und Schutzreaktionen. Eine reine Freizellzunahme kann SLAM-Drift sein und genügt nicht. Der Testumfang wird durch eine getrennte Referenz kontrolliert; diese wird dem Explorer nicht als versteckte Karte oder Wegpunktliste gegeben. Teilstände bleiben erhalten, zählen aber nicht als vollständige Positivläufe. Eine bestandene Wohnung ist noch keine allgemeine Zuverlässigkeitszertifizierung.

## 6. Verbindliche Regressionen und CI

Jeder behobene nachgewiesene Fehler erhält eine Regression gegen echte Produktfunktionen. Synthetische Uhren, Transporte und Weltmodelle sind zulässig; die zu prüfende Entscheidung selbst darf nicht durch eine Attrappe ersetzt werden. Neue Tests prüfen Verhalten, nicht nur interne Implementierungsdetails.

Die CI-Auswahl MUSS die betroffenen echten Tests ausführen. Insbesondere sind Pytest-Funktionen nicht durch einen bloßen `unittest discover`-Erfolg abgedeckt. Änderungen an `robot_interfaces` müssen die betroffenen Verbraucher prüfen. Zu AP-02 werden die fehlenden passenden Workflow-Trigger und Testaufrufe ergänzt; große ungezielte CI-Neubauten sind kein eigenes Vorhaben.

Ein bekannter unabhängiger Baselinefehler darf dokumentiert isoliert werden, nicht unbemerkt gelöscht oder als bestanden gezählt. Neue Regressionen im betroffenen Pfad blockieren das Paket. Plattform, Befehle, tatsächlich gesammelte Fälle und Ergebnis müssen prüfbar sein. Tests des alten main oder importierte alte Nachrichtenbindungen sind keine Abnahme des neuen Kandidaten.

## 7. Paketführung, Blocker und Rückfall

Vor Beginn: tatsächliche SHA und lokale Änderungen, Planversion, WE-Bezug, Ziel/Nichtziele, Akzeptanzfälle und Rückfall festhalten. Bestehende laufende Roboter-Checkouts werden nicht umgeschaltet. Unbekannte Nutzeränderungen bleiben erhalten. Ein isolierter Branch/Worktree und getrennte Buildpräfixe sind zulässig.

Währenddessen: ein aktiver Kandidat, ein Implementierungsauftrag, ein Integrationsverantwortlicher. Begrenzte Reparaturen und ihre Tests ohne neue Erlaubnisrunde erledigen. Fehlende private Bags sind kein Hindernis für synthetische Softwaretests. Eine notwendige nicht fernbedienbare Handlung oder echte offene Umfangsentscheidung wird konkret benannt; sie stoppt nur davon abhängige Arbeit.

Bei einem Blocker sind erstes fehlgeschlagenes Kriterium, Originalbeleg und kleinstes weiteres Arbeitspaket zu nennen. Kein identischer Realversuch ohne neue Evidenz, kein automatischer Stack-/Rechnerneustart als Lösung, kein Wechsel des Explorers bei unverändertem Sensor-/Startfehler. Es wird kein festes Datum oder Erfolgsprozentsatz ohne Nachweis versprochen.

Rückfall bedeutet Rücknahme des eigenen kleinen Diffs auf die dokumentierte Ausgangsbasis, keine pauschale Rückkehr zum alten historischen Branch. Quellen, Profile und installierte Artefakte werden getrennt geführt. Reale Karten, Bilder, Bags und Geheimnisse bleiben außerhalb der veröffentlichten Historie. Dokumentations-/Softwareabschluss autorisiert keinen Merge oder dauerhaften Installwechsel.

## 8. Nachweisformat und aktueller Einstieg

Ein Paketabschluss nennt Planversion/AP/WE-Bezug, Ausgangs- und Ergebnisstand, geänderte Komponenten, ausgeführte Befehle, Ergebnis je Akzeptanzkriterium, Plattform, Evidenzpfade, bekannte Grenzen, Rückfall und genau einen nächsten Schritt. Statusstufen bleiben getrennt: dokumentiert, in_arbeit, software_geprüft, zielsystem_geprüft, physisch_abgenommen sowie offen/blockiert. Eine neue Planversion setzt historische Teilerfolge nicht zurück und färbt offene Realabnahmen nicht grün.

**Aktueller Einstieg für die Hauptlinie `self_healing`:** der aktive Schritt
des Fahrplans in §9 (Arbeitsliste im STATUS). Der folgende Absatz beschreibt
den Einstieg des eingefrorenen AP06-Pfads vom 02.10.2026.

**Historischer Einstieg AP06: AP-01.** MASTERPLAN v1.3 kanonisch übernehmen und den HWT-Zeitfehler gerätefrei reparieren. AP-02 wird nach dessen Softwareabschluss als nächster konkreter Auftrag vorbereitet. Kein automatischer Übergang zur weiteren Implementierung oder zu einem Laborlauf innerhalb des ersten Auftrags.

**Änderungsprotokoll:** 02.10.2026, v1.3: unabhängige Gegenprüfung eingearbeitet; gemeinsame Basis und Bewegungsmodell vor produktiver Explorerübernahme; gepinnter externer Frontier-Kern als zulässige Komponente; sechs begrenzte Arbeitspakete innerhalb unveränderter WE-Meilensteine; konkreter erster Zeitkorrekturauftrag.
09.11.2026, Nachtrag zu v1.3 (Nutzerentscheidung): §9 Fahrplan der
Selbstheilungslinie mit Arbeitsregeln, Schritten und Paketen.
10.11.2026, Nachtrag (Nutzerentscheidung nach Standortbestimmung): §9 Regeln
6 (gezielte Probe vor langer Fahrt) und 7 (ein Problem zur Zeit), Schritt 1
mit Stellprobe.
14.11.2026, Nachtrag: §9 Regel 7 (nächster Schritt darf in der Simulation
vorbereitet werden). 15.11.2026, Nachtrag: Wohnung vorgezogen, zuerst als
Messfahrt W-1.
16.11.2026, Nachtrag (Nutzerentscheidung nach W-1N): zuerst der
Suchmechanismus EK-1 als SH-9, Fahrbereich Labor, Flur und Schlafzimmer;
Produktvorgabe 80–85 % je Raum; Arbeitsregel 8 (nach jeder Änderung eine
ganze Fahrt durch eine Tür).
19.11.2026, Nachtrag (Nutzerentscheidung): §10 zweite, getrennte
Entwicklungslinie „KI-Erkundung“ im Ordner `ki_erkundung/`; Hauptlinie und
§9 unverändert.
19.11.2026 (spät), Nachtrag (Nutzerentscheidung nach SH-9): Hauptlinie
geparkt; die KI-Erkundung (§10) ist die aktive Arbeit.
19.11.2026, zweiter Nachtrag (Klarstellungen des Projektinhabers): §10.2 an
KONZEPT v1.1 angepasst (kein Joystick, Verbindung zum KI-Rechner wie bei der
Objekterkennung, KI-0 „Erstes Sehen“, KI-1 „Blickrunden aus eigener Kraft“,
KI-5 Gegenstände finden).

## 9. Fahrplan der Selbstheilungslinie (Nutzerentscheidung 09.11.2026)

Dieser Abschnitt ist der rote Faden für die Hauptlinie `self_healing`. Er
legt fest, **in welcher Reihenfolge** gearbeitet wird und **wie** ein
Abschnitt als bestanden gilt. Den jeweils aktuellen Stand führt nur die
**Arbeitsliste oben im STATUS**; dieser Abschnitt ändert sich nur durch eine
neue Entscheidung des Projektinhabers.

### 9.1 Arbeitsregeln

1. **Eine Verhaltensänderung je Realtest.** Auf dem Roboter wird in einem
   Test genau ein Paket neu geprüft. Messwerkzeuge, die nur mitlesen und das
   Fahren nicht beeinflussen, dürfen hinzukommen. So bleibt jedes Ergebnis
   eindeutig einer Änderung zuzuordnen.
2. **Kriterien und Rückfall vorab.** Jedes Paket hat eine Kennung, ein Ziel,
   vor dem Test festgelegte Kriterien und einen Rückfallweg. Es geht erst auf
   den Roboter, wenn es in der Simulation besteht, soweit die Simulation den
   Fall abbilden kann; was sie nicht kann, steht im Paket.
3. **Eine Arbeitsliste.** Der STATUS führt oben genau eine Liste: ein
   Realtest **aktiv**, ein Paket **in Simulation**, alles andere **geparkt**
   mit kurzem Grund, dazu **erledigt**. Neue Ideen werden geparkt, nicht
   sofort gebaut.
4. **Scheitern führt zuerst zu Daten.** Besteht ein Realtest nicht, folgt ein
   nur lesender Auswerteauftrag (wie SH-7N), dann eine gezielte Korrektur
   desselben Pakets. Das nächste Paket bleibt so lange in der Simulation;
   nichts wird vermischt.
5. **Bestanden heißt eingefroren.** Ein bestandener Stand wird als Prototyp
   eingefroren; sein Release bleibt unverändert als Rückfall erhalten.
6. **Gezielte Probe vor langer Fahrt** (Nutzerentscheidung 10.11.2026). Ein
   Verhalten, das nur in bestimmten Lagen gebraucht wird (zum Beispiel sich
   an einem Hindernis befreien), wird zuerst mit einer **Stellprobe**
   geprüft: Amadeus wird gezielt in die Lage gestellt, die Mission startet,
   und gemessen wird wenige Minuten lang. Lange Fahrten folgen erst danach
   und prüfen das Ganze. Grund: Fünf Testtage mit langen Fahrten haben
   dasselbe Problem nicht entschieden, weil die Lage darin nur zufällig
   eintritt.
7. **Ein Problem zur Zeit.** Solange das aktive Problem real nicht gelöst
   ist, wird in der Simulation nur dafür gearbeitet; weitere Pakete bleiben
   geparkt (Nutzerentscheidung 10.11.2026, ersetzt für diese Zeit die
   Parallelarbeit aus Regel 1 bis 3).
   **Nachtrag (Nutzerentscheidung 14.11.2026):** Läuft für das aktive Problem
   ein Realtest und ist in der Simulation nichts mehr dafür offen, wird der
   **nächste Schritt des Fahrplans** in der Simulation vorbereitet (jetzt
   Schritt 2, Erkundungstempo und Nachbarraum finden). Auf den Roboter geht
   weiterhin genau ein Paket je Test, und nichts Neues, solange der laufende
   Test nicht ausgewertet ist.

### 9.2 Schritte

| Schritt | Auf dem Roboter | Parallel in der Simulation | Bestanden, wenn |
|---|---|---|---|
| 1 | **SH-8:** Paket AW-1 plus AW-1b „Abstand halten und wegkommen“. Zuerst Stellprobe an drei bekannten Stellen (Mülleimer, Ecke, Garderobe; je zweimal), bei Erfolg volle Zwei-Raum-Fahrten wie SH-7; die Abdeckungskurve läuft nur mitlesend mit | nur Korrekturen für dieses Problem (Kandidat KM-1 B) | Stellprobe bestanden und C1–C5, G1, R1 und R2 in drei vollen Fahrten; dann Prototyp 2 |
| 2 | **SH-9:** Paket EK-1 „Erkundung zielgerichtet, Teil 1“, zuerst ein Raum, dann zwei | Paket EK-2 nur bei Bedarf | ein Raum zu mindestens 90 % in höchstens 10 min (Schwelle wird nach den SH-8-Kurven endgültig festgelegt), keine Verschlechterung bei C1–C5, G1, R1, R2 |
| 3 | Paket EK-2, nur wenn die Kurven noch viel Leerlauf zeigen | – | wie Schritt 2 |
| 4 | **Stufe 3:** Wohnung | – | Umfang und Kriterien legt der Projektinhaber vorher fest |
| 5 | Raumziele: Erkundungskarte speichern, Räume in der App zeichnen und benennen, Raum per `go_to_room` anfahren | – | wird vor dem Schritt festgelegt |

**Nachtrag (Nutzerentscheidung 15.11.2026): Wohnung jetzt, zuerst als
Messfahrt.** Seit dem 15.11. folgt der Antrieb den Befehlen (Anfahrzeit
100 ms); das Tempo war das Ziel der letzten Runden. Der Projektinhaber
zieht deshalb **Schritt 4 (Wohnung) vor**:

- **Nächster Realtest ist W-1:** eine **begleitete Messfahrt durch alle
  Räume**, ohne Bestehen oder Durchfallen. Davor im selben Auftrag die
  Stellprobe für die eine offene Korrektur des Festsitzens (KM-2), nach
  Regel 6. Regel 1 bleibt: KM-2 ist die einzige Verhaltensänderung.
- **Umfang nach Angabe des Projektinhabers:** alle Zimmertüren offen; keine
  Stufe nach unten und keine Türschwelle im offenen Bereich; Fliesen mit
  Fugen sind dabei. Frei stehende niedrige Dinge werden weggeräumt, feste
  Möbel bleiben. Er geht mit der Hand am Not-Aus mit. Diese Freigabe gilt
  für die Messfahrt W-1 und ihre eine Wiederholung, nicht allgemein.
- **Zurückgestellt, nicht gestrichen:** die zwei weiteren vollen
  Zwei-Raum-Fahrten für Prototyp 2 und Schritt 2/3 (EK-1, EK-2). Was davon
  gebraucht wird und in welcher Reihenfolge, entscheidet sich an den Daten
  von W-1 („erst messen“).
- **Die Abnahme der Wohnung bleibt, wie in KONZEPT_SELBSTHEILUNG §11
  festgelegt** (drei Läufe, alle zugänglichen Räume, Karte mindestens 90 %,
  kein Kontakt). W-1 ist dafür keine Wertung.

**Nachtrag (Nutzerentscheidung 16.11.2026): zuerst der Suchmechanismus;
nach jeder Änderung eine ganze Fahrt.** W-1 kam zweimal nicht aus dem
Laborraum (W-1N: in Fahrt 1 scheiterte die Tür, in Fahrt 2 brachen die
Anläufe wegen veralteter Lokalisierung ab und begannen neu). Der
Projektinhaber stellte fest: Am 08.11. gelang die Tür, jetzt nicht mehr; und
der vereinbarte Suchmechanismus war nicht zu sehen. Beides trifft zu; EK-1
war in W-1 ausgeschaltet.

- **Nächster Realtest ist SH-9 = Schritt 2:** EK-1 einschalten (A
  Teilschwenk, B nur Lücken ab 0,5 m, D Abbruch nach 45 s ohne Weggewinn).
  Das ist die eine Verhaltensänderung.
- **Fahrbereich für SH-9, vom Projektinhaber am 16.11.2026 freigegeben:**
  Laborraum, Flur und Schlafzimmer; Bad, Küche und Wohnzimmer zu; begleitet
  mit der Hand am Not-Aus; zwei Fahrten von höchstens 20 Minuten. Der
  dritte Raum ist nötig, damit Amadeus den Laborraum verlassen muss. Die
  Freigabe gilt für SH-9, nicht allgemein.
- **Produktvorgabe des Projektinhabers:** Ein Raum darf bei 80–85 % als
  erfasst gelten. Entsteht kein Fortschritt mehr, sucht Amadeus dort nicht
  weiter und fährt zum nächsten Raum.
- **Arbeitsregel 8 (aus dem Einwand vom 16.11., gilt bis auf Widerruf des
  Projektinhabers): Nach jeder Änderung am Fahr- oder Kartenverhalten folgt
  vor der nächsten Änderung eine ganze Fahrt durch mindestens eine Tür.**
  Eine Stellprobe (Regel 6) prüft eine Lage, nicht das Ganze. Grund:
  Zwischen SH-7 (08.11.) und W-1 (15.11.) kamen AW-1, KM-1 B, KM-2 und die
  Anfahrzeit 100 ms nur mit Stellproben auf den Roboter; der Rückschritt an
  der Tür lässt sich keiner davon zuordnen.
- **Danach, je eine Änderung je Realtest:** die Türdurchfahrt
  (Planungsstreifen von 22 cm in der 78-cm-Tür, Verkeilen, Rückfahrt am
  Pfosten), dann der Rückstand der Positionsbestimmung bei langen Fahrten,
  dann die Wohnung erneut als Messfahrt.

### 9.3 Pakete

- **AW-1 „Abstand halten und wegkommen“** (`19c8cb9`, Entscheidung
  08.11.2026 nach SH-7N): Wege mit mehr Abstand (globale Inflation), eigene
  räumende LiDAR-Ebene in der lokalen Karte, Rückfahrkontur für BackUp,
  Rückfahrt auch ohne gerade eigene Spur (0,3 m, höchstens 0,4 m,
  0,05 m/s, einmal je Stillstand), Zeitgrenze für 30 % Tempo.
- **KM-1 B** (Kandidat, nur Simulation, 09.11.2026): Die lokale Karte löscht
  nichts mehr unter der Roboterkontur; Hindernisse im 2-cm-Polster bleiben
  eingetragen, der Regler dreht nicht hinein, wegkommen über die
  Rückfahrkontur. Vor einem Einsatz am Roboter im Stand zu messen: Eigenechos
  (Mast im LiDAR-Sichtfeld).
- **EK-1 „Erkundung zielgerichtet, Teil 1“** (Ideen A, C, D vom
  09.11.2026, B vom 14.11.2026; **seit 16.11.2026 im Produktprofil
  eingeschaltet als A + B + D**): A Teilschwenk um 90° am Start und nach
  einem erreichten Ziel mindestens 2,5 m vom letzten Schwenk (wegen des
  Masts nötig); B nur Lücken, hinter denen mindestens 0,5 m Unbekanntes
  liegt (schmale Schattenkeile und Streifen vor Wänden zählen nicht und
  halten das Ende nicht auf); D kürzere Fehlversuche (Abbruch nach 45 s
  ohne 0,25 m Weggewinn statt nach 150 s). C („gut genug“-Ende über ein
  Zeitfenster) ist gebaut und bleibt aus; mit B ergibt sich das Ende
  geometrisch.
- **EK-2 „Erkundung zielgerichtet, Teil 2“** (Idee B): Ziele nach erwartetem
  Nutzen (unbekannte Fläche, die von dort sichtbar würde) statt nach Nähe;
  kleine eingeschlossene Lücken ignorieren.

Geparkte Ideen und offene Nebenpunkte stehen mit Grund in der Arbeitsliste
des STATUS (unter anderem E gröberes Raster für die Lückensuche, F Tempo vor
Unbekanntem).

## 10. Zweite Entwicklungslinie „KI-Erkundung“ (Nutzerentscheidung 19.11.2026)

Der Projektinhaber hat am 19.11.2026 entschieden: Neben der Hauptlinie
entsteht eine **komplett neue, getrennte Entwicklungslinie**. In ihr
übernimmt eine KI auf dem vorhandenen KI-Rechner die Ziel- und Suchwahl:
Amadeus nimmt bei einer Drehung Bilder auf, die KI erkennt Türen und
Durchgänge und entscheidet, wohin gefahren und wo gesucht wird. Die
bisherige Entwicklung darf dadurch weder verloren gehen noch beeinflusst
werden. Der Realtest SH-9 der Hauptlinie läuft parallel.

Maßgeblich für Inhalt und Stufen ist
[ki_erkundung/KONZEPT.md](../../ki_erkundung/KONZEPT.md); den Stand führt
nur [ki_erkundung/STATUS.md](../../ki_erkundung/STATUS.md).

### 10.1 Trennung (MUSS)

1. **Eigener Ordner.** Konzept, Stand, Aufträge, Software und Tests der
   KI-Linie liegen ausschließlich in `ki_erkundung/`.
2. **Kein Eingriff in Bestehendes.** Die KI-Linie ändert keine Pakete unter
   `src/`, keine Profile, Startdateien oder Werkzeuge. Braucht sie später
   eine Anschlussstelle in bestehendem Code, ist das eine eigene, vom
   Projektinhaber freigegebene Änderung der Hauptlinie: standardmäßig aus,
   ausgeschaltet verhaltensgleich, getrennt getestet (AGENTS §2.7).
3. **Die Hauptlinie bleibt, wie sie ist.** §9, die Arbeitsliste im STATUS
   und der Auftrag in `AGENTENAUFTRAG.md` gelten unverändert und bleiben für
   den Roboter maßgeblich. **Seit 19.11.2026 (spät) ist sie geparkt:** Sie
   hat keinen Auftrag; ihr Code, ihre Profile und ihre Releases bleiben
   unverändert erhalten.
4. **Ein Auftrag am Roboter.** Zu jeder Zeit läuft am Roboter genau ein
   Auftrag. Ein Auftrag der KI-Linie wird erst durch ausdrückliche Übergabe
   des Projektinhabers aktiv.
5. **Die Grenzen aus §4 gelten auch hier.** Kein zweiter Navigator oder
   Supervisor, keine direkten Motorbefehle, keine versteckte
   Pflicht-Raumsemantik. Die KI liefert Wahl und Gründe; fällt sie aus oder
   antwortet unbrauchbar, entscheidet die vorhandene Regel. Die Schutzkette
   bleibt unverändert, und die KI ist nie die einzige Schutzmaßnahme.
6. **KI-Rechner im Haus.** Ausgewertet wird auf dem vorhandenen KI-Rechner
   des Projektinhabers. Bilder der Wohnung verlassen das Haus nicht und
   kommen nicht ins Repository.
7. **Dieselben Arbeitsregeln.** Für Realtests der KI-Linie gilt §9.1: je
   Realtest eine Verhaltensänderung, Kriterien und Rückfall vorab, zuerst
   Trockenlauf und Simulation.

**Ausdrückliche Änderung gegenüber §2:** Für die KI-Linie gibt es einen
eigenen Iststand (`ki_erkundung/STATUS.md`). Für die Wohnungserkundung der
Hauptlinie bleibt es bei einem STATUS und einer Arbeitsliste; die KI-Linie
führt dort keine Kopie.

### 10.2 Stufen (Kurzfassung)

| Stufe | Inhalt | Wirkung auf das Fahren |
|---|---|---|
| KI-0 | Erstes Sehen: Amadeus steht, Kamera und LiDAR laufen, die Frage geht über die vorhandene Verbindung an den KI-Rechner | keine |
| KI-1 | Blickrunden aus eigener Kraft: Amadeus dreht sich bei Fahrten der Hauptlinie selbst, die KI beantwortet im Hintergrund dieselben Entscheidungen | keine durch die KI; braucht eine freigegebene Anschlussstelle für die volle Drehung |
| KI-2 | Kopplung in der Simulation mit gespielter KI (richtig, falsch, langsam, stumm) | keine am Roboter |
| KI-3 | Die KI wählt real; Regel als Rückfall | eine Verhaltensänderung, Freigabe des Projektinhabers |
| KI-4 | Raumnamen in der App, Hilferuf mit Bild und Grund | keine am Fahrverhalten |
| KI-5 | Gegenstände finden („Fahre zur Tasse“) mit den vorhandenen Bausteinen | wird vor der Stufe festgelegt |

Kriterien je Stufe stehen vorab im Konzept (Trockenlauf KI-0 und KI-1: K0-1
bis K0-7).

**Klarstellungen des Projektinhabers (19.11.2026, abends):** Kein Joystick;
Amadeus dreht sich für die Blickrunde selbst. Der KI-Rechner wird nur
eingeschaltet; die Verbindung baut sich von selbst auf, wie bei der
Objekterkennung (ROS 2 DDS im WLAN, im Repository auf `main`). Der Lotse
bekommt dafür einen eigenen Dienst auf dem KI-Rechner mit drei eigenen
Themen `/ki_erkundung/…`; Fahrbefehle gibt es dort nicht. Ein viertes Thema
(`/ki_erkundung/fahrziel_json`, seit 21.11.2026) gibt es nur auf dem
Roboter: Darauf nennt die KI-Linie dem Erkunder ein Fahrziel; der KI-Rechner
sendet dort nie.

### 10.3 Verhältnis zur Hauptlinie

- Türdurchfahrt, blinde Rückseite und Rückstand der Ortung bleiben Arbeit der
  Hauptlinie (§9.2). Die KI-Linie setzt darauf auf und baut sie nicht
  doppelt.
- Die KI-Linie darf bestehende Funktionen lesend wiederverwenden. Umgekehrt
  hängt die Hauptlinie von nichts in `ki_erkundung/` ab.
- **Erste Anschlussstelle (21.11.2026, vom Projektinhaber freigegeben):**
  Startargument `initial_scan_only` des Erkunders, Vorgabe `false`. Mit
  `true` dreht Amadeus einmal abschnittsweise um 360° und bleibt stehen, ohne
  ein Ziel anzufahren; ohne das Argument ist alles wie zuvor. Sie dient der
  Blickrunde von KI-1. Weitere Anschlussstellen brauchen je eine eigene
  Freigabe.
- **Zweite Anschlussstelle (21.11.2026, vom Projektinhaber freigegeben):**
  Startargument `stage_drive_only` des Erkunders, Vorgabe `false`
  („Etappenfahrt“). Mit `true` wartet ein Erkundungsauftrag stehend auf genau
  ein Fahrziel der KI-Linie (ein bis drei Punkte in der Karte) und fährt es
  **ohne Nav2** an: auf der Stelle ausrichten und kurze gerade, vom Laser
  gemessene Etappen von höchstens 0,5 m bei 0,05 m/s, vor jeder Etappe die
  Prüfung des Streifens in Fahrzeugbreite. Das sind die am 10./11.09.2026
  real bestandenen Bausteine des Erkunders, unverändert; Fahrtor,
  Geschwindigkeitsglätter und Kollisionsmonitor bleiben davor. Ohne gültiges
  Ziel bewegt sich nichts, und der Auftrag meldet das. Zusammen mit
  `initial_scan_only` kommt zuerst der Rundblick. Der Erkunder bleibt der
  einzige Besitzer der Navigation; die KI-Linie liefert nur das Ziel und
  nennt, wer es gewählt hat. Entscheidung des Projektinhabers dazu: erst
  ohne Nav2, vom Einfachen zum Schwierigen; Nav2 kommt nur dazu, wenn das
  nicht reicht.
- **Rückfall der ganzen Linie:** `ki_erkundung/` und die Verweise darauf
  entfernen. Sonst ändert sich nichts.
