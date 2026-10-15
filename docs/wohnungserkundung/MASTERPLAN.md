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

**Aktueller Einstieg: AP-01.** MASTERPLAN v1.3 kanonisch übernehmen und den HWT-Zeitfehler gerätefrei reparieren. AP-02 wird nach dessen Softwareabschluss als nächster konkreter Auftrag vorbereitet. Kein automatischer Übergang zur weiteren Implementierung oder zu einem Laborlauf innerhalb des ersten Auftrags.

**Änderungsprotokoll:** 02.10.2026, v1.3: unabhängige Gegenprüfung eingearbeitet; gemeinsame Basis und Bewegungsmodell vor produktiver Explorerübernahme; gepinnter externer Frontier-Kern als zulässige Komponente; sechs begrenzte Arbeitspakete innerhalb unveränderter WE-Meilensteine; konkreter erster Zeitkorrekturauftrag.
