# Meilensteine – vom Flurtest zur vollständigen zugänglichen Wohnung

**Plan WE-1 · Version 2026-09-14**

Maßgeblich sind [Gesamtplan](../WOHNUNGSERKUNDUNG_STRATEGIE.md),
[Agentenauftrag](AGENTENAUFTRAG.md) und der laufende [Status](STATUS.md).
Die folgenden Kriterien sind **vereinbarte Entwicklungsziele**, keine behaupteten
Testergebnisse. WE-Präfixe vermeiden Verwechslungen mit den Arm-/Encoder-Meilensteinen.

## Nachweisstufen und Abhängigkeiten

Jeder Schritt besitzt getrennte Nachweise: `geplant`, `in_arbeit`,
`software_geprüft`, `zielsystem_geprüft`, `physisch_abgenommen`; daneben sind
`blockiert` und `nicht_erforderlich_mit_begründung` zulässig. Ein reiner
Dokumentationsschritt heißt `dokumentiert`, nicht `physisch_abgenommen`.
`Nicht ausgeführt` ist kein bestandenes Gate. Bei neuen Fehlern den betroffenen
Nachweis einschränken oder erneut öffnen und den historischen Erfolg erhalten.

| Stufe | Ergebnis | Voraussetzung |
|---|---|---|
| WE-D0 | Strategie, Agentenvertrag und Roadmap dokumentiert | Nutzerentscheidung und Quellenprüfung |
| WE-M0 | Code-/Betriebsbasis und begrenzte Baseline geklärt | WE-D0 |
| WE-M1 | Stabiles Portalgedächtnis, ohne Fahrwirkung | WE-M0/A; kein Warten auf eine neue Fahrt für reine Unit-Tests nötig |
| WE-M2 | Regionsgraph und passive Zustandsbeobachtung | WE-M1 softwaregeprüft |
| WE-M3 | Hierarchische Auswahl und Abschlussvertrag integriert | WE-M2 softwaregeprüft; geklärte Integrationsbasis |
| WE-M4 | Drei Regionen mit belastbarem Rückweg real nachgewiesen | WE-M0/B sowie WE-M3 zielsystemgeprüft; neue Fahrfreigabe |
| WE-M5 | Kartenbindung, Wiederanlauf und Fortsetzung | WE-M2/M3 für Offline-Arbeit; WE-M4 vor erweitertem realem Fortsetzungstest |
| WE-M6 | Zugängliche Wohnung wiederholbar erkundet | WE-M4 und WE-M5; gültiger Ressourcen-/Betriebsnachweis |
| WE-M7 | App-Transparenz und optionale Raumnamen | Stabile WE-M2/M5-Schnittstellen; kein Blocker der geometrischen Kernfunktion |

Einzelne Meilensteine bei Bedarf in kleine PRs teilen. Die Reihenfolge erlaubt
rein passive Vorarbeit bei noch offener Hardwareabnahme; sie erlaubt nicht, offene
Hardwaregates vor dem nächsten aktiven Lauf zu überspringen.

## WE-D0 – Gemeinsamer Plan und auffindbarer Pflichtkontext

**Lieferung:** Gesamtstrategie, Agentenauftrag, diese Roadmap und ein laufender
Status mit belegtem Ausgangspunkt. Einstieg über Root-AGENTS, Projektstatus und
Dokumentationsindex. Der Strategiestand vom August bleibt historisch erhalten.

**Prüfung:** Nur Dokumentationsdateien geändert; relative Dokumentverweise,
Meilenstein-IDs und Statusbegriffe konsistent; keine realen Geometriedaten oder
Geheimnisse hinzugefügt. Funktionale Branches und der Jetson bleiben unverändert.

**Abnahme:** Commit/Remote-Stand nachvollziehbar; klar bezeichnet, ob Dokumentation
nur auf einem Branch liegt oder bereits in Main verfügbar ist. Keine neue ROS-,
Hardware- oder CI-Abnahme behaupten. **Rückfall:** Nur Dokumentationscommit
zurücknehmen; keine Runtime-Rücksetzung.

## WE-M0 – Ausgangsbasis sichern, bevor Verhalten erweitert wird

### A. Leseanalyse und Integrationsentscheidung

**Ziel:** Eindeutige Zuordnung von Dokumentation, Code, Profil und Betriebsstand.

**Aufgaben:** Aktuelle Remote-Refs und lokale Änderungen erfassen; Unterschiede
zwischen Main und HWT-Referenz gezielt für `explore`, Sensorfusion, Startprofile
und Sicherheitsabhängigkeiten untersuchen. Tatsächlich verwendete Jetson-Pfade
und installierte Versionen nur soweit verfügbar nachweisen, nicht aus Branch-Namen
erraten. Existierende Kartenmanager-/Semantik-IDs und Abschlussverbraucher prüfen.

**Lieferung:** Kurzer Bestandsbericht im Status: vorhandene Funktionen,
fehlende Voraussetzungen, genaue Integrationsbasis, relevante Dateien,
ungeklärte Konflikte, nächster kleiner PR und passende Tests. Noch keine
funktionale Übernahme und keine neue Fahrsoftware.

**Abnahme A:** Kein unbekannter Stand als getestet bezeichnet; keine fehlende
Funktion doppelt erfunden; keine Merge-Abhängigkeit verschwiegen. Bei notwendiger
funktionaler Integration erst deren Umfang bestätigen lassen. **Rückfall:** Keine
Runtime-Wirkung; bei Unklarheit auf diesem Teilschritt stoppen.

### B. Zielsystem-Baseline und Nachtest der Abschlusskorrektur

**Aufgaben:** Auf abgestimmter Codebasis passende bestehende Tests/Builds und einen
wirklich motorlosen Start prüfen. TF-Alter/-Extrapolationen, verpasste Controller-
zyklen und Ressourcenlast messen. Zulässige Last-/Frischekriterien aus dem
bestehenden Betrieb ableiten und vor der Fahrt festlegen; offene Probleme getrennt
beheben, nicht mit größeren Sicherheits-Timeouts verdecken.

Nach neuer Freigabe ausschließlich den bestehenden begrenzten Arbeitszimmer-Flur-
Lauf einschließlich der nachgelagerten Abschlusskorrektur wiederholen. Prüfgebiet
und alle erlaubten Ziele/Pfade vorher festlegen: ein Portallimit allein ist kein
vollständiger räumlicher Schutz gegen weitere normale Nav2-Ziele.

**Abnahme B:** Keine Regression von Sensorfusion, Footprint, Nahbereich, Abbruch
oder Stopp. Physischer Übergang und anschließende Fortsetzung ohne falschen
Doppelportal-Limitabbruch nachvollziehbar. Lastbefunde entweder behoben und
nachgetestet oder begründet so eingegrenzt, dass die nächste Stufe nicht betroffen
ist. **Rückfall:** Bekannte Baseline wiederherstellen, neues Profil nicht aktivieren;
bei Fehlern sicher stoppen. Kein Ganzwohnungslauf in dieser Stufe.

## WE-M1 – Portalidentität und Durchfahrtsgedächtnis als reine Logik

**Ziel:** Dieselbe Tür von beiden Seiten und bei Kartenwachstum wiedererkennen,
ohne Nachbartüren zu verschmelzen. Historie und momentane Erreichbarkeit trennen.

**Lieferung:** Kleines datengetriebenes Modul, stabile IDs, kanonische Seitendefinition,
Geometrie-/Revisionsbezug, Evidenz und idempotente Ereignisse; begründete Grenzen
für Zuordnung, Unsicherheit und Wiederholungen. Speicherung zunächst im Speicher;
das dauerhafte Dateiformat folgt in WE-M5. Keine ROS- oder Motor-Nebenwirkung.

**Pflichttests:** Wiedererkennung von beiden Seiten; wachsende Karte und bewegter
Raumschwerpunkt; geänderter Ursprung und Raster; zwei eng benachbarte Türen;
Möbelengstelle; verlorene Sicht; wiederholte identische Kartennachricht;
blockiert → erneut offen; mehrdeutige Zuordnung; wiederholtes Durchfahrtsereignis.

**Abnahme:** Synthetische Wahrheitszuordnungen bleiben stabil; Ambiguität erzeugt
keine falsche Bestätigung. Besuch/Blacklist verbietet keinen Rückweg. Eindeutige
Ereignisse werden genau einmal gezählt; erkannte Türen und Überquerungen bleiben
verschiedene Größen. **Rückfall:** Modul nicht einbinden; alte Logik unverändert.
**Leitplanken:** WE-03, WE-04, WE-05, WE-11.

## WE-M2 – Vorläufige Regionen und passiver Graph

**Ziel:** Raumregionen und Übergänge verfolgen, ohne von einer perfekt segmentierten
Wohnung oder einer festen Anzahl Zimmer auszugehen.

**Lieferung:** Regionszuordnung und Graph mit nachvollziehbaren Verbindungen,
Seen-/Entered-/Erkundungszuständen, Revisionen und Aufgabenbezug. Bestehende
Portaldetektoren verwenden; Analyse-Erosion strikt von realer Costmap trennen.
Kartenkorrekturen und mögliche Regionsteilungen/-vereinigungen behandeln.
Frühe Status-/Marker-Ausgabe im Schattenmodus, ohne Einfluss auf die Zielwahl.

**Pflichttests:** Startraum-Flur-Zimmer; ein verbundener Freiraum mit offenen Türen;
L-Flur und Schleife; offener Wohnbereich; Möbelunterteilung; Kartenwachstum,
Ursprungsrotation und simulierte Korrektur; Betrachten eines Raums ohne Eintritt;
Rückkehr in denselben Flur; Regionsteilung/-vereinigung ohne verlorene Aufgaben.

**Abnahme:** Derselbe Flur erhält bei Rückkehr keine neue Identität. Unsegmentierte
Frontiers bleiben global sichtbar. Rohkarte und Nav2-Kosten unverändert. Passive
Integration liefert keine Navigationsziele oder Fahrbefehle und meldet veraltete
Daten als solche. Laufzeit/Speicher bei wachsender synthetischer Karte begrenzt.
**Rückfall:** Schattenintegration abschalten. **Leitplanken:** WE-01 bis WE-05, WE-09.

## WE-M3 – Hierarchische Auswahl, Rückwege und Abschlussvertrag

**Ziel:** Flur erschließen, Regionen zusammenhängend untersuchen und bekannte Wege
nutzen; Ende beziehungsweise Teilende aus einem erklärbaren Aufgabenbestand ableiten.

**Lieferung:** Separat aktivierbares Profil und Policy im bestehenden Explorer.
Einziger Eigentümer der Nav2-Ziele bleibt die vorhandene Orchestrierung.
Zielbewertung mit tatsächlicher/geodätischer Weglänge, Informationsgewinn,
Regionshysterese, Aufgabenalter und begrenzten Retries. Bestandsaufnahme aller
Verbraucher von `ExploreArea`, `/explore/status_json`, Coverage und
`map_ready_to_save`; explizite, versionierte oder abwärtskompatible Migration.

Vorab festlegen: Relevanzschwellen, frische Beobachtungsfenster, maximal zulässige
Zuordnungsabweichung, Budgets, Wiederanlaufbedingungen und erwartete Resultate.
Werte begründen und vor den Abnahmeläufen einfrieren. Keine nachträgliche Änderung,
nur damit eine gescheiterte Fahrt als erfolgreich gelten kann.

**Pflichttests:**

- Deterministische Flur-/Raumauswahl ohne Pendeln und ohne Verhungern ferner Ziele;
  transitierbare besuchte Türen; blockiertes Ziel mit späterer erneuter Prüfung.
- Gültiges Portal bereits in verbundener Costmap; reguläre Nav2-Durchfahrt wird
  erkannt, auch wenn keine Sonderbrücke verwendet wurde.
- Nav2-Erfolg vor tatsächlichem Auslauf, Durchsicht, Encoderschlupf, TF-Sprung,
  halbes Chassis im Durchgang und Gegenrichtung erzeugen keinen falschen Eintritt.
- Keine Ziele wegen fehlender Karte, eingefrorener Daten, Planerausfall,
  Blacklist oder unklarer Segmentierung ergibt keinen falschen Vollabschluss.
- Timeout/Energie-/Versuchslimit ergibt einen erklärten Teilstand; Sensorfehler
  oder Not-Aus sichere Unterbrechung; Nutzerabbruch bleibt Abbruch des Auftrags.
- Zielwechsel, Cancel und erneuter Auftrag besitzen nie konkurrierende aktive
  Kindziele. Geänderte Kartenrevision invalidiert veraltete Ziele.
- Begrenztes Testprofil hält **auch normale Nav2-Ziele und Pfade** im freigegebenen
  Bereich. Auftragsscope und Portalzähler werden nicht verwechselt.

**Abnahme:** Offline-Szenarien prüfen konkrete Entscheidungen und Resultate;
Legacy-Verhalten bleibt bei deaktiviertem neuen Profil erhalten. Kein stiller
Rückfall auf einen schwächeren Vollständigkeitsvertrag. Motorlose ROS-/Jetson-
Integration inklusive Abbruch, Status und unveränderter Sicherheitskette bestanden.
**Rückfall:** Neues Profil nicht aktivieren, kompatible Baseline nutzen; Daten nicht
als neuen vollständigen Wohnungsabschluss ausgeben. **Leitplanken:** WE-01 bis WE-10.

## WE-M4 – Erster echter Drei-Regionen-Rundweg

**Versuch:** Arbeitszimmer → Flur → weiteres Zimmer → zurück in denselben Flur.
Das sind drei Bereiche, nicht drei beliebige Zählerinkremente.

**Voraussetzungen:** WE-M0/B und WE-M3 bestanden; neuer beaufsichtigter Auftrag,
freier sicherer Testbereich, erreichbarer Hardware-Not-Aus, definierte Transportpose
und aktuelle Sensor-/Footprint-Abnahme. Kein Mensch oder Tier wird als
Kollisionstest verwendet. Zusätzliche nicht freigegebene Bereiche wirksam ausschließen.

**Lieferung:** Begrenztes Testprofil, vorab festgelegte Kriterien, lokaler Bag/
Status-/Posenbeleg sowie datensparsamer Ergebnisbericht. Keine echten Karten oder
Wohnungskoordinaten in Git.

**Abnahme:** Roboter betritt den dritten Bereich vollständig und kehrt über dessen
bekannte Tür in denselben Flur zurück. Portal- und Regions-IDs bleiben stabil;
Gegenrichtung ist ein neues Ereignis derselben Tür. Durchfahrten durch Messfolge
und äußere Beobachtung bestätigt. Keine manuelle Zielvorgabe als angeblich autonome
Entscheidung verstecken. Alle Schutzfunktionen, begrenzte Abbruchwege und sauberer
Stopp nachgewiesen. Keine Behauptung einer vollständig erkundeten Wohnung.

**Negativversuch:** Blockierten Rückweg zunächst offline testen, real nur nach
separater Freigabe und sicherem Aufbau. Erwartung: kein Erzwingen der Passage,
begrenzte Neuplanung oder sicherer Hilfebedarf.

**Rückfall:** Mission abbrechen, auf vorher abgenommenes Profil zurück; WE-M4 bei
ID-/Stopp-/Rückwegfehlern offen lassen. **Leitplanken:** WE-03 bis WE-07, WE-10.

## WE-M5 – Persistenz, Kartenbindung und Wiederaufnahme

**Ziel:** Erkundungswissen behält Bedeutung über Speicher-/Neustartgrenzen, ohne
falsche Räume an eine andere Karte zu binden oder Bewegung auszulösen.

**Lieferung:** Validiertes Schema und atomare Ablage über beziehungsweise mit den
existierenden Kartenmanager-Verträgen. Laufende Sitzung/Revision von gespeicherter
Kartenidentität und Fingerprint trennen. Manuelle Raum-IDs/Namen explizit zuordnen,
nie durch unbestätigte automatische Segmentierung überschreiben. Teilkarten
speichern und ihren Teilstatus bewahren.

**Pflichttests:** Save/Load-Rundlauf mit identischen IDs; beschädigte/abgebrochene
Schreiboperation; nicht unterstützte Schemaversion; Kartenfingerprint- oder
Geometriewiderspruch; veralteter Managerstatus; Kartenwechsel; Korrektur des
Geometriebezuges; doppelte Events; gültige alte Sicherung; Neustart ohne Pose;
vorher offene, inzwischen blockierte Tür; kein Autostart nach Laden.

**Abnahme:** Fehlerfälle bleiben gesperrt und zerstören keine letzte gültige
Version. Nach Neustart bleiben IDs und Restaufgaben korrekt, aber Fahrt bleibt
bis zu gültiger Lokalisierung und neuem zulässigem Auftrag gesperrt. Reale
Wiederaufnahme zunächst nur im bereits abgenommenen Drei-Regionen-Umfang und mit
neuer Freigabe; bestehende semantische Kartenbindungsregeln nicht lockern.
**Rückfall:** Neue Datenversion nicht aktivieren, gültige alte Karte nutzen oder
explizit neue Erkundung anlegen; niemals fremde Metadaten automatisch übernehmen.
**Leitplanken:** WE-07, WE-08, WE-11.

## WE-M6 – Zugängliche Wohnung und wiederholbarer Gesamtabschluss

**Ziel:** Das vollständige geometrische Kernziel des Gesamtplans erreichen.

**Aufbau:** Erlaubte Wohnung und Zugänglichkeit vorab mit Nutzer definieren;
Treppen, Außenbereiche und nicht abgesicherte Gefahren ausschließen. Ground Truth
für die Abnahme lokal festhalten, nicht dem Explorer als versteckte Zielroute
geben. Mit begrenzten Mehrraumläufen schrittweise auf den Umfang erweitern.
Vor jedem Lauf Zeit-, Fahrweg-, Fehler- und Energie-/Reservevertrag bestätigen.

**Pflichtszenarien:** Alle freigegebenen Türen offen; mindestens eine zunächst
blockierte bekannte Verbindung; spätere erneute Erreichbarkeit; kleine
Kartenkorrekturen; Nutzerabbruch und Wiederaufnahme; andere zulässige Startpose.
Riskante Sensor-/Not-Aus-Fehlerinjektionen zunächst im isolierten Test prüfen;
reale Störungstests benötigen eigenen sicheren Aufbau und Freigabe.

**Abnahme:** Alle im Testumfang erreichbaren Raumregionen physisch betreten und
relevante globale/regionale Aufgaben abgearbeitet. Keine offene Tür übersehen,
keine verlorene Frontier durch Filterung, keine doppelte Regionsidentität.
Resultat, Restliste, Speicherung und gegebenenfalls angeforderte Rückkehr stimmen
mit Messungen und äußerer Prüfung überein. Geschlossene oder ausgeschlossene
Bereiche sind sichtbar benannt, nicht als erkundet gezählt.

Mindestens zwei getrennte beaufsichtigte Positivläufe im vereinbarten Umfang
müssen diese Kriterien ohne manuelle Navigationsübernahme erfüllen; veränderte
Startpose und Unterbrechungs-/Blockadefälle ergänzen den Nachweis. Dies ist ein
Entwicklungs-Abnahmekriterium, keine statistische Sicherheitszertifizierung.
Softwareversion, Profile und Grenzwerte vor den Läufen festlegen.

**Rückfall:** Auf den zuletzt bestandenen kleineren Umfang begrenzen. Fehlerlauf
als Teilstand/Abbruch dokumentieren, nicht durch größere Zählergrenzen nachträglich
umdeuten. **Leitplanken:** WE-01 bis WE-12.

## WE-M7 – App-Transparenz und optionale Benennung

**Ziel:** Der Nutzer sieht die tatsächliche Erkundungsentscheidung und kann
Regionen vorhandenen beziehungsweise neuen manuellen Raumnamen zuordnen.

**Lieferung:** Anzeige von Region, Portal-/Aufgabenstatus, nächstem Ziel und Grund,
Teilabschluss, Speicherung, Blockaden und Rückkehrstatus. Integration in vorhandene
App-/Semantikschnittstellen, keine zweite unabhängige Raumverwaltung.

**Pflichttests:** Neue/unbekannte Felder nach festgelegter Kompatibilitätsstrategie;
veralteter Zustand klar markiert; Kartenwechsel; Raumteilung/-vereinigung;
Nutzername bleibt erhalten; gesperrte Kartenbindung; Benennung ohne Fahrwirkung.

**Abnahme:** Anzeige behauptet weder Fortschritt noch Freigabe, den die
Roboterdaten nicht belegen. Manuelle Änderungen benötigen gültigen Karten-/
Revisionsbezug. Automatische KI-Raumnamen bleiben außerhalb dieser Stufe.
**Rückfall:** Nur neue Darstellung deaktivieren; Kartierung unverändert nutzbar.
**Leitplanken:** WE-07, WE-08, WE-12.

## Einheitlicher Ergebnisnachweis

Bei jeder Teilabnahme mindestens festhalten: Test-ID, Datum, Commit, Profil,
Umgebung, synthetisch/reale Messung, vorab erwartetes Ergebnis, tatsächliches
Ergebnis, relevante Messgrößen, Fehler, lokale Evidenzreferenz, Git-taugliche
Zusammenfassung und Rückfallweg. Durchfahrtsanzahl, eindeutige Portale, betretene
Regionen, offene Aufgaben, Wiederholungen, Laufzeit und Lokalisierungs-/Sensorfehler
getrennt berichten. Nicht verfügbare Metriken als nicht gemessen kennzeichnen.

Fachliche Zusammenfassung in [STATUS.md](STATUS.md); abgeschlossene ausführliche
Prüfberichte bei Bedarf datiert unter `docs/archive/`, reale Rohdaten weiterhin
lokal. Vermeide einen neuen konkurrierenden "aktuellen Status" pro Versuch.
