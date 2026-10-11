# Wohnungserkundung – verbindliche Gesamtstrategie

**WE-1 · LAB-Präzisierung 11.10.2026 · MASTERPLAN v1.5 · Amadeus**

Der aktuelle [LAB-Slotauftrag](wohnungserkundung/LAB_SLOTS.md) behält dieselbe
Mission/BT/Explorer/Nav2-Kette. Fester 360°-Start ohne vorgeschalteten
Kartenpixelbeweis; anschließend Beobachtung und Zielwahl im bestätigten Halt,
ein Fahrziel und erneute Beobachtung nach Kindende/Halt. Aktuelle Sensoren und
Schutzgates laufen weiter. Normale Blockaden führen zu begrenzter Wiederprüfung
oder geprüftem Ausweichziel, ohne Fehler, Zähler oder Fristen zurückzusetzen.
Der sensorüberwachte `continuous`-Ablauf bleibt ausdrücklich als Rückfall erhalten.

Dies ist die vom Nutzer beschlossene Zielausrichtung, kein Implementierungs- oder Fahrnachweis. [Masterplan](wohnungserkundung/MASTERPLAN.md), [STATUS](wohnungserkundung/STATUS.md), [Agentenauftrag](wohnungserkundung/AGENTENAUFTRAG.md) und [Meilensteine](wohnungserkundung/MEILENSTEINE.md) bilden die einzige aktuelle Roadmap.

Die [vollständige Strategie vor v1.2](wohnungserkundung/archive/20260930-v1.1/WOHNUNGSERKUNDUNG_STRATEGIE.md) bleibt bytegleich erhalten. Ihre nicht betroffenen Detailregeln gelten weiter; die nachfolgende ausdrückliche Trennung ersetzt die Pflicht einer hierarchischen Portal-/Raumauswahl vor metrischen Erkundungszielen.

## 1. Produktziel und Grenzen

Amadeus soll eine zunächst unbekannte, freigegebene Umgebung schrittweise autonom erschließen, offene Aufgaben bearbeiten, bekannte Wege für weiteren Fortschritt und angeforderte Rückkehr nutzen sowie Karte und Erkundungszustand konsistent sichern. Zimmer, Flure, Schleifen und offene Wohnbereiche sind zulässig; keine fest programmierte Sternstruktur.

„Vollständig“ bezieht sich ausschließlich auf den vereinbarten aktuell zugänglichen und sensorisch erschließbaren Umfang. Nicht beobachtete Räume hinter unbekannten geschlossenen Türen dürfen nicht als erledigt gelten. Lokaler Grundriss/Beobachter kann Abnahmereferenz sein, aber kein verdecktes Vorwissen der autonomen Zielwahl.

Nicht Teil des nächsten Pakets: Türöffnen mit Arm, Treppenfahrt, Ladestation, Reinigung, perfekte Raumsegmentierung, neue OAK-/KI-Türerkennung. Physische und kartografische Erkundung sind nicht gleich vollständiges Abfahren jeder Bodenfläche.

## 2. Kernarchitektur

**Eine gemeinsame metrische Karte, ein aktiver Explorer, ein vorhandener Ausführungspfad. Ergänzende Semantik ist nicht dessen Startvoraussetzung.**

SLAM/Pose → metrische Frontier-/Beobachtungswahl → Nav2 → neue Messungen/Ergebnis → nächste Auswahl. Mission Manager/BT, Einzelkind, Gate, Collision Monitor und Basis bleiben der vorhandene Produktpfad. Kein zweiter Navigator oder unkontrollierter cmd_vel-Eingang.

Die notwendige Datenbasis besteht aus konsistenter aktueller Karte, Pose/TF, realen Hindernisinformationen, Fahrzeugumriss, Auftragsscope und technischen Schutz-/Budgetbedingungen. Zielkandidaten erschließen weitere Beobachtung. Seit der Nutzeränderung vom 11.10.2026 darf `sensor_guarded` unbekannte Zellen zur Planung innerhalb des gebundenen Scopes verwenden; Rohkarte und Beobachtungsnachweise bleiben unverändert. LiDAR/VL53, aktuelle Quellen und der ganze Fahrzeugumriss sichern die vorhandene Bewegungskette ab. Ein möglicher Rundblick hat vor der Zielsuche Vorrang; die alte beobachtete Zulassung bleibt als Rückfall verfügbar. Erst Zulässigkeit, dann Nutzen/Weglänge/Anfahrgeometrie und Fehlversuche bewerten. Luftlinie ist kein Routenbeleg.

Globale erreichbare Frontiers im Scope bleiben bearbeitbar, auch ohne Raumsegmentierung. Optionale Portal-/Regionsdaten dürfen nicht durch Frischepflicht, künstliche aktuelle Region oder versteckte Filter zum Vor-Gate werden. Ein fehlender notwendiger Sensor ist davon ausdrücklich zu unterscheiden.

## 3. Kontinuierliche Exploration und lokale Misserfolge

Nach regulärem Start und notwendiger Beobachtung eine Aufgabe tatsächlich bearbeiten; nicht nach Rundblick oder Goal-Annahme enden. Karte während der Fahrt fortführen. Gültiges Ziel bei unwesentlichen Bewertungs-/Kartenänderungen erhalten, aktuelle Wegsicherheit weiter prüfen.

Bei nicht erreichtem Einzelziel kontrolliert beenden und aktuelle Fortsetzbarkeit beurteilen. Gesunde Quellen, terminales altes Kind, bestätigter Stillstand und zulässiger neuer Weg können eine begrenzte alternative Aufgabe erlauben. Ungeklärte sicherheitsrelevante Zustände bleiben gesperrt. Weder dauernd denselben Versuch wiederholen noch jeden Timeout mit Hardwaredefekt gleichsetzen.

Aufgabenfortschritt, reiner Bewegungsfortschritt und neue Kartenevidenz getrennt beurteilen. Notwendige Drehung/Transit zulassen, kleine Schleifen aber nicht als unbegrenzten Fortschritt verbuchen. Gesamtbudgets laufen über Kindwechsel weiter. Vorübergehend blockierte Aufgaben bleiben bekannt und erhalten eine erneute Prüfbedingung.

## 4. Durchgänge und spätere Raumsemantik

Eine offene, für das reale Fahrzeug sicher beobachtete und planbare Verbindung ist im metrischen Modus ein normaler Nav2-Weg, auch ohne Türlabel. Fehlende Portalhypothese bedeutet weder gesperrte Frontiererkundung noch automatisch freie Passage.

Vollständige physische Durchfahrt verlangt weiterhin die plausible Bewegung des gesamten Footprints einschließlich Heck auf die Gegenseite und nachfolgende Weiterarbeit. Eine Karte hinter der Tür, Encoderweg oder Action-SUCCESS allein reicht nicht. Gesonderte LiDAR-geprüfte Engstellenmanöver werden erhalten, aber nicht automatisch zum Umgehen unzulässiger Nav2-Wege aktiviert.

Portalgedächtnis und Regionsgraph bleiben ergänzende Fähigkeiten: stabile Identitäten, Seitenumkehr, gesehen/betreten/erkundet, momentane Erreichbarkeit, Rückwege und optionale Namen. Ihre ursprünglichen Detailverträge bleiben als semantische Abnahmen erhalten. Sie dürfen nach bewährtem metrischem Kern integriert werden, ohne ihn zwingend von vollständiger Semantik abhängig zu machen. Bekannte Türen bleiben Transitwege, besuchte Regionen keine pauschalen Sperrflächen.

## 5. Wiederverwendung, Speicherung und Abnahme

Früheren Frontier-/Annäherungskern um `1d91229` als Referenz nutzen; moderne Sensor-/Fusion-/Cancel-/HOLD-/Kartenkorrekturen erhalten. Kein alter Komplettbranch als neue Runtime. Die genaue Auswahl ist ein begrenzter Softwareauftrag, keine dritte Robotersoftware.

Bestehende Kartenmanager-/Semantikschnittstellen verwenden. Metrischer Teilstand, erfolgreiche Erkundung, Fahrspurabdeckung und semantische Vollständigkeit sind unterschiedliche Ergebnisse. Keine Speicher-/App-Freigabe aus einem lediglich leeren Portalbestand ableiten. Kartenwechsel und Neustart benötigen gültige Bindung/Relokalisierung; keine Fahrt allein durch Laden.

Reale Daten lokal halten. Historische Erfolge nicht erneut verlieren, aber nicht als Beleg einer neuen Kombination ausgeben. Reihenfolge und nächste Arbeit ausschließlich aus Masterplan/STATUS. WE-M0–M7 bleiben erhalten, metrische und semantische Nachweise werden ausdrücklich getrennt. MASTERPLAN v1.4 legt AP-01 → AP-06 fest: Zeitbasis, Karten/Quellen, Planung/Bootstrap, Frontiervergleich, Fortschritt/Abschluss, geschlossene Gesamtprüfung und reale Abnahmen. AP-04 erlaubt ausdrücklich die geprüfte Integration eines gepinnten externen Frontier-Kerns als Kandidatenlieferant; die frühere Offline-Beschränkung ist hierfür aufgehoben. Kein kompletter Fremdstack oder zweiter Navigator. Geometrie- und Abschlussvertrag werden nach konkreten Gegenfällen konsolidiert, Schutzwirkung und gültige Daten bleiben Pflicht. Der historische Frontierkern bleibt Vergleichsreferenz; seine Übernahme ist nicht vorentschieden. AP-06 prüft zuerst die gerätefreie geschlossene Gesamtkette und danach den exakt zugeordneten Kandidaten unter gültigem LAB-1-Umfang/technischen Vorbedingungen am Zielsystem. Zugangsblocker und reale Abnahmen ausschließlich im STATUS; keine pauschale Lockerung anderer Abnahmekriterien.
