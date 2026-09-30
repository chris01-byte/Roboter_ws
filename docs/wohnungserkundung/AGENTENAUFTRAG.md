# Agentenauftrag – metrische Frontiererkundung ohne Portalpflicht

**WE-1 · 30.09.2026 · MASTERPLAN v1.2 · Schritt 3, Softwarepaket**

## 1. Auftrag und verbindlicher Einstieg

Implementiere im bestehenden Amadeus-Produktpfad die Schleife:
**beobachten → erreichbare nützliche Position wählen → Nav2-Auftrag bearbeiten → Messungen/Ergebnis bewerten → nächste Aufgabe.**

Lies AGENTS.md, [LAB-1](../LABORMODUS.md), [MASTERPLAN v1.2](MASTERPLAN.md), [STATUS](STATUS.md) und [Meilensteine](MEILENSTEINE.md). Inventar, Projektgedächtnis, ROBOT_TRANSFER und betroffenen Code gezielt hinzunehmen. Keine Gesamtinventur oder neue Planungsvorlage.

Basis ist der aktuelle veröffentlichte Stand von PR #105 / feature/hwt-hold-recovery-resume. Vor der v1.2-Dokumentation: `99d21c012dfe4c28d8263f7cd5e16505b07736d6`; letzter ausgewerteter funktionaler Kandidat `492ef20`. Historischer Frontier-/Türvergleich `1d91229dc10ff4bb791938d49aae8e9808a5dfff`, zugeordnet in WE_PARITY_RESET. Neuere abgestimmte Korrekturen erhalten, nicht blind zurückrollen.

**Dieser Auftrag ist gerätefreie Implementierung plus integrierter Softwarebeleg.** Keine Hardware-/Sensorprozesse, reale Fahrt, automatische Installation oder Merge. LAB-1 gilt für selbstständiges Durcharbeiten; keine allgemeinen Laborfragen für reine Softwarearbeit.

## 2. Lieferumfang und Nicht-Ziele

Genau ein funktionales Paket: metrische Zielwahl ohne Portal-/Regionspflicht, gekoppelt an die vorhandene Einzelkind-/Mission-/HOLD-Steuerung einschließlich begrenzter Weiterarbeit nach nicht erreichtem Ziel.

Erlaubt sind begrenzte Änderungen in explore, dessen Profilen/Tests und zwingend betroffenen vorhandenen Mission-/BT-/Status-/Launch-Adaptern. Modulgrenze und Migration knapp vor Implementierung benennen. Pure Helfer oder ein klar abgegrenztes Strategiebackend im vorhandenen Paket sind zulässig; kein zweiter Navigator/Goal-Sender und kein Komplettneubau.

Nicht beauftragt: neue SLAM-/OAK-/YOLO-/Arm-/GUI-Pipeline, Austausch von Hardware oder Treibern, pauschale Timeout-/Frische-/Kollisionslockerung, neuer Supervisor, reale HWT-Injektion, automatisches Drehen/Rückwärtsfahren als universelle Befreiung. Portal-/Regionscode nicht löschen. Keine Selbstbefreiung als fertig ausgeben, nur weil ein anderes Ziel auswählbar ist.

## 3. Implementierung

### 3.1 Wiederverwendung und expliziter Modus

Ordne nur die tatsächlich nötigen Bausteine zu: historische Frontiercluster, Bewertung und sichere Annäherungsziele; aktueller Karten-/Scopevertrag; Einzelkind, Cancel, Mission, HWT-HOLD und Schutzkette. Verwende passende vorhandene Helfer, keine Kopie des gesamten alten explore_node.py.

Führe die metrische Strategie explizit und isoliert ein, sinngemäß `metric_frontier`; tatsächlichen Parameternamen und Default dokumentieren. Bestehendes laufendes Produktprofil nicht stillschweigend umschalten. Moduswechsel ausschließlich ohne aktive Mission, gegenseitiger Ausschluss der alten und neuen Aufgabensteuerung.

Normale Ziele benötigen gültige metrische Karte/Sitzung/Frame, aktuelle Pose, Scope, Hinderniskarten, Sensor-/Antriebsgesundheit und Budget. **Keine Portal-ID, Pflicht-Raum-ID, graph.current_region oder frische PortalMemory als zusätzliche Voraussetzung.** Alte Datenklassen bei Bedarf gezielt neutralisieren/entkoppeln; keine Dummy-Portale, künstlichen Regionen oder „immer gesund“-Publisher bauen.

Optionale Semantik darf passiv beobachten, aber nicht versteckt filtern, freigeben, abbrechen oder ein zweites Ziel erzeugen. Notwendige Bewegungs- und Quellenprüfungen werden nicht mit entfernt. Dokumentiere die wirksame Abhängigkeitsgrenze, nicht nur einen ausgeschalteten Parameter.

### 3.2 Echte Frontierziele und laufende Karte

Frontiers aus echten Eingangsrastern berechnen. Sichere erreichbare Annäherungspositionen im bekannten freien Scope bilden; unbekannte Zellen nicht als Fahrweg deklarieren. Keine harte Bindung an eine semantisch aktuelle Region. Erst Zulässigkeit/Erreichbarkeit, dann nachvollziehbarer Nutzen, Weglänge, Anfahrgeometrie und bisherige Fehlversuche. Bestehende Bewertung zuerst wiederverwenden; kein neues Optimierungsforschungsprojekt.

SLAM-Updates werden fortlaufend verarbeitet. Ein gültiges aktives Ziel bleibt bei kleinen Karten-/Rankingänderungen stabil, wird jedoch auf aktuellen metrischen Daten revalidiert. Veraltete Ergebnisse dürfen neue Ablehnungen nicht überschreiben. Kartenwechsel, inkompatible Pose oder unzulässiger Weg sperren. Nicht für jeden unveränderten Weg eine neue semantische Beweiskette verlangen; Quellenfristen und korrekte Kartenprovenienz bleiben wirksam.

Nach Zielerreichung oder sinnvoll beendeter Beobachtungsaufgabe neue Messungen bewerten und das nächste autonome Ziel wählen. Kein Stop nach Scan oder erstem Goal. Keine vollständige Bodenabdeckung des ersten Raums vor erlaubter Weitererkundung voraussetzen.

### 3.3 Ergebnis-, Blockade- und Recoveryvertrag

Übergeordneten Explore-Auftrag von einem einzelnen Nav2-Ergebnis trennen. Genau ein aktives Kind; vor Ersatz muss altes Kind terminal sein, alte Callbacks/Commands bleiben unwirksam.

Nicht erreichtes Ziel bei nachgewiesen gesundem Betriebszustand: kontrolliert stoppen, Stillstand und aktuelle Lage prüfen, den Versuch mit konkretem Grund bewerten und bei sicherer Fortsetzbarkeit Aufgabe befristet zurückstellen. Danach andere tatsächlich erreichbare Aufgabe zulassen. Eine spätere erneute Prüfung benötigt nachvollziehbare Bedingung; keine endlose Neuerzeugung desselben Ziels mit neuer ID.

Kein pauschales `timeout -> LOCAL_BLOCKED` und keine erfundene Hindernisursache. Aufgabenmisserfolg, fehlender Nachweis und echter System-/Aktuatorfehler unterscheiden. Not-Aus, Nutzerabbruch, nicht terminales Kind, ungültige notwendige Quellen oder unsichere Pose dürfen keine automatische Wiederanfahrt erzeugen.

Den bekannten `navigation_timeout -> SYSTEM_FAILURE`-Befund und positive/negative Replays gezielt als Regression verwenden. Fehlenden damaligen Callbackzustand nicht erfinden. Falls für die neue Entscheidung nötig, einen konsistenten Snapshot mit erstem ablehnendem Prädikat/Exception erfassen. Das ist Bestandteil der Implementierung, kein separater Auftrag, der die Entwicklung wieder bis zum Wiederauftreten des historischen Fehlers anhält.

Aufgabenfortschritt von kleinen Drehungen und Odometriesummen unterscheiden. Der neue Kern darf nicht unbegrenzt im SlowZone-Kriechen an derselben Aufgabe festhalten; vorhandene begrenzte Fortschritts-/Versuchsbudgets verwenden und phasenabhängig auswerten. Nötige Drehung/Transit nicht fälschlich als Stillstand werten. Keine realen Grenzwerte auf Verdacht ändern. Gesamtbudgets bleiben über Kindwechsel und HOLD erhalten.

Bestehenden HWT-HOLD-Vertrag erhalten: nach tatsächlicher Wiederherstellung neue Quellen, stabiler Stillstand, aktuelle Pose/Route und nötiges Gate-ACK; dann Fortsetzung derselben noch gültigen Aufgabe oder ausdrücklich begründete Aufgabenentscheidung. Kein Reboot und keine alte Goal-Wiederbelebung.

### 3.4 Engstellen, Abschluss und Ausgabe

Normale Nav2-Durchfahrt durch geometrisch zulässige offene Verbindung ohne Türlabel erlauben. Keine direkte Fahrt durch eine für das reale Fahrzeug unzulässige Costmap-Lücke; besondere Portalbrücken in diesem ersten Modus nicht automatisch aktivieren.

Leere Auswahl durch stale Quellen, Filter, Blockaden oder Budgetende darf nicht als vollständige Wohnungserkundung gelten. Metrischer Abschlusskandidat, Teilstand, Warten, Fehler und Nutzerabbruch getrennt ausweisen. Vorhandene ExploreArea-/Status-/Speicherverbraucher prüfen: keinen semantischen Gesamtabschluss oder `map_ready_to_save` durch leer gewordene Pflichtdaten vortäuschen. Erforderliche neue Modus-/Ergebnisfelder explizit kompatibel oder versioniert anlegen.

Vorhandene Marker/Statusausgabe nutzen: aktives Ziel und Auswahlgrund, aktueller Versuch, Wartungs-/Blockadegrund, echte Aufgabenerledigung und verbleibende Kandidaten. Kartenwachstum nicht aus Meldungsanzahl oder Fahrbefehlintegral behaupten. Keine neue App bauen.

## 4. Gerätefreie Pflichtnachweise

Nutze vorhandene Unit-/Integrationswerkzeuge. ROS-Graph nur isoliert ohne Geräte-/Motorzugriff; synthetische Sensorszenen und Nav2-Gegenstelle sind erlaubt. Die zu prüfende Karten-/Frontier-/Policy-/Kind-/Gate-Logik muss echt laufen. Keine fest eingesetzten Zielkandidaten oder immer gesunden Portal-/Task-Adapter als Integrationsbeleg.

1. **Ohne Semantik:** gültige wachsende Karte und aktuelle technische Quellen, keine Portal-/Regionspublisher; autonomes Ziel entsteht. Auch leerer, verspäteter oder widersprüchlicher optionaler Semantikstatus erzeugt keine metrische Fahrentscheidung.
2. **Beobachtungsschleife:** drei nacheinander aus veränderten Karten abgeleitete Beobachtungsaufgaben im selben Elternauftrag; neue Sicht führt zu erneuter Auswahl, bekannte erledigte Aufgaben werden nicht endlos wiederholt. Eine synthetische offene Verbindung funktioniert ohne Türlabel.
3. **Blockiertes Ziel:** erste reale Policywahl endet erfolglos, altes Kind terminal, erforderlicher Stillstand/Quellen-/Posecheck, begrenzte Zurückstellung, anderes selbst berechnetes zulässiges Ziel. Tür-/Graph-Attrappen bleiben aus.
4. **Kriechen/Progress:** kleine Drehbewegungen ohne Aufgabenfortschritt führen nicht zu endlosen Budgetresets; notwendige Vorausrichtung und sinnvoller Transit bleiben zulässig. Timeout-Entscheidungsgrund und verwendeter Snapshot sind nachvollziehbar.
5. **Kartenübergabe:** häufige harmlose Updates behalten ein weiter gültiges Kind; tatsächliche Hindernis-/Kontextänderung wird wirksam; verspätete alte Arbeit überschreibt keinen neueren Stand.
6. **HOLD/Cancel:** betroffene HWT-, Gate- und Kindverträge einschließlich verspäteter Actionantwort, erneuter Störung, fehlendem Stillstand und zweitem Kind prüfen. Alte reale Belege bleiben historische Teilnachweise, keine aktuelle Simulationserfolgsmeldung.
7. **Harte Gegenfälle:** Not-Aus, Nutzerabbruch, fehlende notwendige Sensor-/TF-/Kartenquelle, unzulässiger Scope/Footprint, erfolgloser Cancel, Aktuatorfehler und ausgeschöpftes Budget verhindern unzulässige Weiterfahrt.
8. **Abschluss/Migration:** nur blockierte oder gefilterte Frontiers, fehlende Daten und unbekannte Restbereiche ergeben keinen Vollabschluss. Bestehende Status-/Speicherkonsumenten verwechseln metrische und semantische Ergebnisse nicht. Alte Strategie bleibt im nicht gewählten Modus unverändert.

Zusätzlich vorhandenen historischen Erfolgsdatensatz und aktuellen Fehllauf für Offline-Kandidaten-/Entscheidungsvergleich nutzen, soweit lokal verfügbar. Ein gespeicherter Bag reagiert nicht auf neue Fahrentscheidungen: Replay ist keine geschlossene physische Erkundungsabnahme. Fehlende private Daten nicht als Zwangsvoraussetzung für synthetische Vertragstests behandeln.

## 5. Arbeiten und veröffentlichen

Ohne Zwischenfreigaben Softwarepaket durcharbeiten. Kleine begründete Reparatur plus gezielte Regression direkt im Paket, keine neue Audit-/Branchkette für jeden Untertest. Bei einem echten Umfangskonflikt genau diesen benennen.

Keine laufende Roboter-Arbeitskopie wechseln, kein dauerhafter Install und keine Fahrt. Ein separates Build-/Testpräfix ist zulässig. Vor ausgehendem Commit/Push lokale Historie prüfen: gemeldete private Berichtscommits nicht als Vorfahren veröffentlichen. Lokale Daten und Änderungen sichern; kein Force-Push oder destruktiver Reset. Remote-Dokumentstand gezielt übernehmen statt unkontrolliert private lokale Historie zu mergen.

In derselben vereinbarten Integrationslinie veröffentlichen. MASTERPLAN nicht erneut umschreiben, sofern keine neue Nutzerentscheidung nötig ist. STATUS, AGENTENAUFTRAG und einschlägiges Projektgedächtnis auf tatsächlich erreichten Stand setzen. Inventar/Topicvertrag nur bei realer Änderung ergänzen.

## 6. Paketabschluss

Liefern: geänderte Dateien und Wiederverwendung, tatsächlicher Modus/Profilpfad, isolierter Build, ausgeführte Tests mit Grenzen, Beispiel der verbundenen Ziel-/Blockade-/Folgezielkette, notwendige Rückfalloption und Commit/PR.

Erfolg: **METRISCHER ERKUNDUNGSKERN – GERÄTEFREI INTEGRIERT BESTANDEN.** Das ist kein Stufe-3-Gesamtgrün und kein physischer Raumwechsel.

Falls nicht erfüllt: konkrete erste fehlgeschlagene Funktion, Originalbeleg und verbleibender Implementierungsschritt; kein Sammelbericht „mehr Diagnose nötig“ ohne Zuordnung.

Genau nächster Schritt nach Softwareerfolg: begrenzter Realnachweis derselben metrischen Beobachtungsschleife im vorhandenen LAB-1-Bereich mit tatsächlicher Hindernisfortsetzung und geometrisch zulässigem Durchgang. Bestehende Profile/Budgets als Ausgangspunkt verwenden, Umfang vor Fahrt konkret festlegen, nicht automatisch aus diesem Softwareauftrag starten.

Die [vorige Auftragsdatei](archive/20260930-v1.1/AGENTENAUFTRAG.md) ist vollständig erhalten, aber kein paralleler aktueller Auftrag.
