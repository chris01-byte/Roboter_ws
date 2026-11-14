# Wohnungserkundung – verbindlicher Gesamtplan

**Plan:** WE-1 · **Version:** 2026-09-14 · **Projekt:** Amadeus / `chris01-byte/Roboter_ws`

**Geltung:** Vom Nutzer bestätigte Zielarchitektur. Dieses Dokument beschreibt,
was schrittweise entstehen soll, nicht eine bereits implementierte oder für
unbeaufsichtigte Fahrt freigegebene Funktion. Der Dokumentationsauftrag ändert
keine Fahrsoftware, Parameter, Firmware oder Hardware.

| Dokument | Zuständigkeit |
|---|---|
| [Agentenauftrag](wohnungserkundung/AGENTENAUFTRAG.md) | Pflichtkontext, Arbeitsablauf, Grenzen eines Auftrags |
| [Meilensteine](wohnungserkundung/MEILENSTEINE.md) | Reihenfolge, Lieferobjekte, Tests und Abnahmen |
| [Status und Entscheidungen](wohnungserkundung/STATUS.md) | Einziger laufender Fortschrittsstand dieses Vorhabens |
| [Strategiestand 18.08.2026](archive/2026-08/WOHNUNGSERKUNDUNG_STRATEGIE_2026-08-18.md) | Unveränderte historische Referenz, keine neue Fahrfreigabe |

## 1. Ziel und Grenzen

Amadeus soll eine zunächst unbekannte Wohnung schrittweise erschließen,
Raumregionen und ihre Übergänge wiedererkennen, offene Aufgaben systematisch
abarbeiten und über bekannte Verbindungen zurückfinden. Primärer Anwendungsfall:
Zimmer, die über einen gemeinsamen Flur verbunden sind. Der Flur ist eine
Planungspriorität, keine fest programmierte Sternstruktur. Weitere
Zimmerverbindungen, Schleifen und offene Wohnbereiche bleiben zulässig.

Das Kernziel ist erreicht, wenn alle im freigegebenen Umfang aktuell zugänglichen
und sensorisch erschließbaren Bereiche nach einem geprüften Abschlussvertrag
erkundet sind, bekannte Restaufgaben nachvollziehbar ausgewiesen werden und Karte
sowie zugehöriger Erkundungszustand konsistent gespeichert werden können.

Eine von Anfang an geschlossene, unbekannte Tür kann einen nicht beobachteten
Raum verbergen. Ohne Zusatzwissen darf deshalb keine absolute Vollständigkeit
aller tatsächlich existierenden Zimmer behauptet werden. Ein Grundriss oder eine
Nutzerkontrolle darf zur **Abnahme** dienen, aber nicht heimlich als Vorwissen des
angeblich autonomen Explorers verwendet werden.

Nicht Teil des Kernziels: Türöffnen mit dem Arm, Treppenfahrt, automatische
Ladestation, flächendeckendes Reinigen, perfekte architektonische Raumsegmentierung
oder kamerabasierte Benennung jedes Zimmers. Ein Raum darf zunächst `region_002`
heißen. App-Namen sind eine nachgelagerte Ergänzung.

## 2. Belegter Ausgangspunkt und Quellgrenzen

Der Dokumentationsstand beruht auf zwei getrennten Git-Ständen:

| Quelle | Aussage und Einschränkung |
|---|---|
| `main` bei `05439c7a13d7a92e69b9eb4663e3a2a1b44626a1` | Ausgangsbasis dieses Dokumentationszweigs. Nicht identisch mit der jüngsten HWT-Erprobung. |
| `codex/hwt601-encoder-shadow` bei `1d91229dc10ff4bb791938d49aae8e9808a5dfff` | Referenz der jüngsten besprochenen Arbeitszimmer-Flur-Erprobung; keine automatische Merge- oder Deployment-Freigabe. |
| [HWT-Projektprotokoll, Eintrag 11.09.2026](https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/docs/PROJECT_MEMORY.md) | Physischer Übergang in den Flur mit Nutzerbestätigung dokumentiert. Dieselbe Tür wurde bei geänderter Kartengeometrie erneut angeboten. Nachgelagerte Abschlusskorrektur laut Protokoll noch nicht real wiederholt; TF-/Controller-Lastprobleme offen. |
| [HWT-Zwei-Bereich-Profil](https://github.com/chris01-byte/Roboter_ws/blob/1d91229dc10ff4bb791938d49aae8e9808a5dfff/src/explore/config/hwt601_office_hall_params.yaml) | Begrenzter Test mit gefordertem Übergang, nicht der fertige Wohnungsmodus. |
| [Explorer](../src/explore/README.md) | Bestehende Frontier-/Fahrspurabdeckung und Nav2-Anbindung als Integrationsbasis. |
| [Kartenmanager](../src/robot_map_manager/README.md) und [semantischer Kartenmanager](../src/semantic_map_manager/README.md) | Versionierte Kartenablage und manuelle, an Kartenfingerprints gebundene Raum-Overlays existieren bereits. Nicht durch konkurrierende Ablagen ersetzen. |

Die dort genannten 80 Explorer-Tests und der grüne Build sind **berichtete
historische Ergebnisse**, keine im Dokumentationsauftrag neu ausgeführten Tests.
Lokale Bags, Karten und die laufende Jetson-Installation wurden hierbei nicht
unabhängig geprüft. Neuere Repository- oder Hardwareevidenz ist in WE-M0 zu
ermitteln und datiert im Status einzutragen.

Die Strategie vom August verschob einen dauerhaften Raumgraphen bis zum Nachweis
entsprechender Probleme. Mit der dokumentierten Portal-Doppelerkennung und dem
nun bestätigten Nutzerziel wird diese Erweiterung gezielt eingeplant. Das ist
keine Begründung für einen Austausch des gesamten Navigationsstacks.

## 3. Architektur und Verantwortlichkeiten

**Eine gemeinsame metrische Karte, ein ergänzender topologischer Graph, ein
bestehender Ausführungspfad.**

1. SLAM und die bestehende Lokalisierung liefern die metrische Karte und Pose.
2. Der Explorer führt Portalgedächtnis, vorläufige Raumregionen und offene Aufgaben.
3. Eine hierarchische Auswahl bestimmt Region und nächstes Beobachtungs-/Fahrziel.
4. Nav2 und die bereits vorhandenen, begrenzten Explorationsmanöver führen dieses
   Ziel über die bestehende Missions- und Sicherheitskette aus.
5. Kartenmanager und semantischer Kartenmanager bleiben für ihre vorhandenen
   Speicher- und Benennungsverträge zuständig; Änderungen daran sind explizite,
   getestete Schnittstellenerweiterungen.

Es entsteht **kein zweiter Navigator**, kein unabhängiger Motorbusbesitzer und
kein zusätzlicher ungegateter `cmd_vel`-Pfad. Der Graph darf nur Ziele und
Metadaten liefern, niemals Freigaben erzwingen. Normale Durchfahrten bleiben bei
Nav2. Bestehende LiDAR-geprüfte Portalbrücken bleiben Sonderfälle mit unveränderten
Sicherheitsverträgen; das Graphmodell erweitert deren Befugnisse nicht.

Vorgesehene Modulgrenzen im vorhandenen Paket `explore`:

| Vorgeschlagenes Modul | Aufgabe |
|---|---|
| `portal_memory.py` | Identität, Evidenz, Zustände und Durchfahrtsereignisse von Portalen |
| `region_graph.py` | Vorläufige Regionen, Verbindungen und aktuelle Regionszuordnung |
| `exploration_policy.py` | Aufgabenwahl, Hysterese, Rückwege und Abschlussentscheidung |

Diese Dateinamen sind noch kein implementierter Bestand. Nach der Bestandsprüfung
sind vorhandene gleichwertige Funktionen wiederzuverwenden. Reine Logik erhält
Tests ohne ROS, Gerätezugriff oder versteckte Nebenwirkungen. ROS-Anbindung bleibt
in der bestehenden Orchestrierung. Keine umfassende Nebenbei-Refaktorierung.

## 4. Ablauf der Erkundung

### 4.1 Startraum und Flur erschließen

Startraum ausreichend beobachten, eine sichere Verbindung in den Flur entdecken
und den Übergang physisch bestätigen. Nicht erst jede kleine Randlücke im
Startraum mehrfach anfahren. Im Flur schrittweise einen belastbaren Fahrweg und
eine Liste plausibler seitlicher Übergänge aufbauen. Unbekannte Flurfortsetzungen
bleiben eigenständige Erkundungsaufgaben.

### 4.2 Raumweise weiterarbeiten

Einen erreichbaren, noch offenen Bereich auswählen und dessen relevante Frontiers
zusammenhängend bearbeiten. Kleine Änderungen der Zielbewertung dürfen nicht
ständige Raumwechsel auslösen. Hysterese und ein begrenztes Regionsbudget vermeiden
sowohl Pendeln als auch das endlose Festhalten an einer aussichtslosen Region.

Anschließend eine bekannte Verbindung als Transitweg zum nächsten offenen Portal,
Flurabschnitt oder erneut prüfbaren Ziel verwenden. Rückkehr durch eine bekannte
Tür ist zulässig und nötig; sie zählt nicht als neue Tür oder neues Zimmer.

### 4.3 Ziele bewerten, ohne Sicherheit zu verrechnen

Zuerst harte Zulässigkeitsbedingungen prüfen: gültige Lokalisierung, frische
Daten, tatsächlicher Footprint, aktueller Pfad, erlaubter Test-/Missionsbereich,
verbleibende Budgets und alle bestehenden Sicherheitsgates.

Erst danach Informationsgewinn, geplante beziehungsweise geodätische Weglänge,
Regionskontinuität, Wartezeit offener Aufgaben und frühere Fehlversuche bewerten.
Luftlinie allein ist kein Routenmaß durch Wände. Gewichtungen, Einheiten,
Normalisierung und deterministische Gleichstandsregeln sind vor der Abnahme zu
dokumentieren. Informationsgewinn kann niemals eine Sicherheitsbedingung aufheben.

Auch ohne sichere Raumsegmentierung muss der globale Frontier-Bestand sichtbar
bleiben. Der Graph darf nicht der einzige Entdecker sein und einen unsegmentierten
Nachbarbereich unsichtbar machen. Unsicherheit führt zu weiterer Beobachtung oder
einem erklärten Teilabschluss, nicht zur erfundenen Vollständigkeit.

## 5. Portalgedächtnis und Raumgraph

### 5.1 Kandidaten erzeugen und bestätigen

Offene Räume bilden oft eine einzige zusammenhängende Freifläche. Daher sowohl
getrennte Komponenten als auch Engstellen im verbundenen Freiraum berücksichtigen.
Abstandstransformation und ausschließlich analytische Erosion liefern Kandidaten.
Virtuelle Raumtrennlinien dürfen nur die Analyse strukturieren; sie verändern
weder SLAM-Karte noch Nav2-Costmap noch realen Sicherheitsabstand.

Eine Möbelengstelle ist nicht automatisch eine Zimmertür. Plausible Wand-/Rand-
struktur, Richtung, freie Geometrie beiderseits und zeitlich konsistente
Beobachtungen liefern Evidenz. Mehrere Aufrufe auf derselben unveränderten
Kartennachricht zählen nicht als mehrere unabhängige Beobachtungen. Eine
unbestätigte Verbindung bleibt ein Kandidat. Keine pauschale Türbreite erfinden;
Analyseabstand, Komponentenlücke und physische lichte Türbreite nicht verwechseln.

### 5.2 Stabile Identität statt Koordinaten-Gedächtnis

Ein Portal erhält eine beständige ID unabhängig vom Erkennungsdurchlauf, Raster-
index, Raumschwerpunkt oder Blickwinkel. Die Beobachtung von der anderen Seite
muss auf dieselbe ID abgebildet werden. Die Zuordnung verwendet lokale Geometrie,
Richtung mit konsistenter Seitenumkehr, Nachbarschaft und bisherige Evidenz.
Benachbarte ähnliche Türen dürfen dabei nicht verschmolzen werden.

Kartenwachstum, geänderter Ursprung, Auflösung und SLAM-Korrekturen erfordern eine
nachvollziehbare Aktualisierung. Feste `map`-Koordinaten allein sind kein dauerhafter
Anker. Bei großen oder nicht eindeutig zuordenbaren Änderungen Geometrie und
abgeleitete Ziele invalidieren, Identität als unsicher markieren und neu prüfen.
Kein Kamerasystem und kein nicht vorhandener SLAM-Anker werden dafür vorausgesetzt;
die konkret verfügbare Referenz ist in WE-M0/WE-M2 festzulegen.

### 5.3 Getrennte Zustandsachsen

| Objekt | Mindestens zu führen |
|---|---|
| Portal | ID; Geometrie/Revision; Seiten und Nachbarregionen; Kandidat/bestätigt/unsicher; Beobachtungsevidenz; Anfahr-/Auslaufziele pro Seite |
| Durchfahrtsereignis | Portal-ID; Richtung; Zeit-/Kartenbezug; gültige Bewegungsbelege; vollständig überquert oder nicht bestätigt |
| Aktuelle Erreichbarkeit | Offen, vorübergehend blockiert, unklar oder bewusst ausgeschlossen; Grund, Zeit und erneute Prüfbedingung |
| Region | Stabile vorläufige ID; Geometriebezug; gesehen/betreten; Erkundungsstatus; offene Aufgaben; optionale manuelle Namenszuordnung |
| Aufgabe | Frontier/Portal/Beobachtung; Region soweit bekannt; Zustand; letzter Versuch; Sperrgrund; Wiederholungsbudget und Reaktivierung |

Beobachtung, tatsächlicher Eintritt und Erkundungsabschluss sind verschiedene
Dinge. Historisch durchfahren bedeutet nicht aktuell offen. Erfolgreich erkundet
bedeutet nicht für Transit gesperrt. Ein momentan unsichtbares Portal wird nicht
allein deshalb gelöscht. Aufgaben mit Fehlern verschwinden nicht durch Blacklists.

Vorläufige Regionen dürfen später geteilt oder zusammengeführt werden. IDs,
Verbindungen und Restaufgaben müssen dabei kontrolliert zugeordnet werden; keine
Aufgabe darf lautlos verloren gehen. Ein offener Wohn-Essbereich darf eine Region
bleiben. Automatische Regionen und vorhandene manuelle App-Räume sind nicht
zwangsläufig eins zu eins identisch; eine explizite Zuordnung erhält Nutzernamen.

## 6. Physischer Raumwechsel und Rückweg

Eine Karte mit sichtbaren Zellen hinter der Tür beweist keinen Raumwechsel.
Ebenso wenig genügt allein ein erfolgreicher Nav2-Actionstatus, ein Sollbefehl,
eine Radumdrehung auf einer rutschigen Schwelle oder ein Sprung der Kartenpose.

Ein bestätigtes Durchfahrtsereignis verlangt eine zeitlich plausible, frische
Bewegungsfolge von der bekannten Nahseite durch den beobachteten Durchgang bis
zum gültigen Auslauf. Das **gesamte transformierte Chassis-Footprint** muss mit
festgelegter Reserve auf der Gegenseite liegen. Die Prüfung berücksichtigt
Ausrichtung, asymmetrische Kontur, Messunsicherheit und Seitenumkehr. Der reale
Kontur-/Sensorstand kommt aus der jeweiligen abgenommenen Konfiguration, nicht
aus einer neu erfundenen Zahl im Graphen.

Pose-/Sensorausfälle und unplausible Sprünge erzeugen keinen Erfolg. Nach Abbruch
oder Neustart dürfen alte Zwischenstände keine neue Durchfahrt vortäuschen.
Ereignisse werden idempotent verbucht. Anzahl erkannter Portale, Anzahl besuchter
Regionen und Anzahl tatsächlicher Überquerungen sind getrennte Kennzahlen.

Für jeden Rückweg dieselbe aktuelle Geometrie- und Sensorprüfung durchführen wie
für den Hinweg. Ein freier Hinweg garantiert keinen später freien Rückweg. Keine
blinde Rückwärtsfahrt bei unzureichender Sensorabdeckung; bei blockiertem Rückweg
begrenzt neu planen oder sicher stoppen und Hilfe anfordern.

## 7. Abschlussvertrag und ehrliche Statusmeldungen

### 7.1 Abschluss des zugänglichen Umfangs

Ein positiver Abschluss verlangt gemeinsam:

- über ein festgelegtes Zeitfenster mehrere **frische** Neubewertungen ohne
  relevante erreichbare Frontier oder sonstige offene Beobachtungsaufgabe;
- einen vollständigen Aufgabenbestand vor und nach Filterung: kein ungelöstes
  Portal, kein nur durch Blacklist, Fehlziel, fehlende Segmentierung oder
  Planerausfall verschwundenes Ziel;
- nachvollziehbare Zustände aller bekannten Regionen und Verbindungen; beim
  Wohnungsziel einen bestätigten Eintritt in jede dafür vorgesehene erreichbare
  Raumregion, nicht nur Durchsicht aus dem Flur;
- gültige Quellen, plausible Karte und Regionszuordnung, keinen ungelösten
  Lokalisierungs-/Sicherheitsfehler und keine noch laufende Kindnavigation.

Stabile Kartenfläche ist lediglich eine Zusatzprüfung. Keine Daten, eine leere
Karte, eingefrorene Kartennachrichten oder ein nicht verfügbarer Planer bedeuten
nicht, dass die Erkundung fertig ist. Abbruchbudgets sind kein Erfolgskriterium.

### 7.2 Ergebnisse trennen

**Zielschnittstelle, noch nicht implementiert:** Ergebniszustände
`complete_accessible`, `partial`, `aborted`, `canceled`; außerdem separate Angaben
zu `map_saved`, optionalem Rückkehrergebnis, ausgeschlossenen/blockierten
Bereichen und Abschlussgrund. Bestehende Action-/JSON-Verträge erst nach Audit und
mit Kompatibilitätstests erweitern, nicht ungeprüft ersetzen.

`complete_accessible` besagt nur: der explizit ausgewiesene, aktuell zugängliche
Umfang ist abgearbeitet. Bekannte unzugängliche Bereiche bleiben sichtbar und
verhindern die Behauptung einer uneingeschränkt vollständigen Wohnung. Offene
Probleme ohne belastbare Einordnung, erreichte Zeit-/Energiebudgets oder bloß
aufgeschobene Ziele ergeben `partial`. Hardware-/Sensorfehler ergeben einen
Abbruch gemäß bestehender Sicherheit; Nutzerabbruch bleibt `canceled`.

Teilstände dürfen gespeichert werden, sofern Karte und Metadaten gültig sind.
Speichererfolg ist kein Erkundungserfolg. Ein Rückwegfehler darf einen zuvor
beobachteten Kartierungsfortschritt nicht löschen, aber auch keinen insgesamt
erfolgreichen Rückkehrauftrag vortäuschen.

### 7.3 Kartierung ist nicht Fahrspurabdeckung

Die vorhandene Coverage-Kennzahl beschreibt einen Bereich um die gemessene
Fahrspur innerhalb des als erreichbar ermittelten Freiraums. Sie ist nicht der
Anteil der gesamten, noch unbekannten Wohnung. Weder 85 Prozent noch ein anderer
isolierter Wert belegen alle Räume.

Sensorische Beobachtung und gefahrene Fläche getrennt führen. Für Kartierung muss
nicht jeder Quadratmeter überfahren werden; zusätzliche Ziele benötigen einen
begründeten Beobachtungs- oder Missionszweck. Bestehende Coverage-Grenzen und
`map_ready_to_save` bleiben bis zur geprüften Vertragsmigration unverändert. Ein
neues Profil darf alte Werte nicht stillschweigend in eine Vollständigkeitsgarantie
umdeuten oder Schutzprüfungen entfernen.

## 8. Speicherung, Neustart und vorhandene Raumdaten

Den während der Kartierung vorläufigen Graphen einer expliziten Sitzung und
Geometrierevision zuordnen. Beim Speichern an die tatsächliche gespeicherte
Kartenidentität/-version und deren Fingerprint binden. Ein laufend verändertes
OccupancyGrid ist nicht mit einem unveränderten gespeicherten Fingerprint
gleichzusetzen. Die existierenden strikten Bindungsregeln des semantischen
Kartenmanagers werden nicht aufgeweicht, um dieses Problem zu umgehen.

Schema versionieren, atomar speichern, beschädigte oder widersprüchliche Zustände
ablehnen und die letzte gültige Version erhalten. Bestehende Kartenmanager- und
App-Raum-IDs integrieren beziehungsweise explizit zuordnen; keine zweite,
unabhängige Wahrheit über dieselbe gespeicherte Karte erzeugen.

Nach Neustart: Karte/Graph prüfen, gültig lokalisieren, Türen und geplante Wege
frisch bewerten, erst nach einem neuen zulässigen Auftrag und erforderlicher
Fahrfreigabe weiterarbeiten. Laden, Benennen oder Korrigieren eines Raums löst
niemals automatisch Bewegung aus. Reale Karten, Graphgeometrien, Kamerabilder und
Bags bleiben außerhalb des öffentlichen Repositories; nur synthetische Fixtures
und datensparsame Prüfberichte werden eingecheckt.

## 9. Ressourcen, Grenzen und Diagnose

Die aktuelle Referenz nennt TF-Zukunftsextrapolationen und verpasste Controller-
zyklen unter SLAM-Last. Vor Mehrraumerweiterung diese Befunde getrennt messen.
Analyse mit begrenzter Frequenz beziehungsweise relevanten Kartenereignissen,
begrenzten Puffern und kontrollierter Laufzeit ausführen. Keine Vollanalyse in
jedem LiDAR-Callback. Veraltete Analyseergebnisse nicht als frische Planung nutzen.

Diagnose muss aktuelle Region, Ziel und Auswahlgrund, offene Aufgaben vor/nach
Filterung, Portal-IDs, Durchfahrtsbelege, Fehler-/Wiederholungsgründe, Datenalter
sowie Karten-/Graphrevision sichtbar machen. Zunächst genügt eine passive
Status-/Marker-Ausgabe; App-Bedienung folgt separat.

Vor jedem aktiven Test Zeit, Fahrweg, Zielversuche, zulässige Regionen und eine
reale Energie-/Laufzeitreserve festlegen. Fehlt eine validierte Energiequelle,
keinen fiktiven Ladezustand verwenden; zunächst konservativ mit beobachtetem
Akku- und Zeitbudget beaufsichtigt testen. Ein Portallimit allein begrenzt nicht
zwangsläufig alle normalen Nav2-Ziele: auch Ziele und Pfade müssen im ausdrücklich
freigegebenen Bereich bleiben.

## 10. Unveränderliche Leitplanken

| ID | Vertrag |
|---|---|
| WE-01 | Bestehende Frontier-/Nav2- und Sicherheitsarchitektur erhalten; keine konkurrierende Fahrinstanz. |
| WE-02 | Gemeinsame metrische Karte; Graph und analytische Raumgrenzen schreiben keine künstlichen Navigationshindernisse. |
| WE-03 | Stabile Portal-/Regionsidentitäten; Mehrdeutigkeit und Kartenkorrekturen explizit behandeln. |
| WE-04 | Gesehen, betreten und erkundet trennen; ganze Kontur und gültige Bewegung statt Scheinüberquerung. |
| WE-05 | Besuchsstatus sperrt keinen Transit; Rückwege werden frisch sicherheitsgeprüft. |
| WE-06 | Alle offenen Aufgaben nachvollziehbar; Blacklists, Zeitlimits und Fehlziele erzeugen keinen falschen Erfolg. |
| WE-07 | Abschlussumfang, Teilabschluss, Abbruch, Speicherung und Rückkehr getrennt ausweisen. |
| WE-08 | Vorhandene Karten-/Semantikverträge erhalten; Neustart ohne automatische Bewegung. |
| WE-09 | Ressourcen begrenzen und Fehler messen; Sicherheitsabstände oder Frischegrenzen nicht zur Symptombeseitigung lockern. |
| WE-10 | Erst offline/passiv prüfen, dann explizit freigegebene begrenzte Hardwareabnahme. |
| WE-11 | Keine realen Wohnungsdaten, Zugangsdaten oder unkontrollierten Artefakte in Git. |
| WE-12 | Pro Auftrag ein begrenzter Meilensteinschritt, belegter Status und prüfbarer Rückfallweg. |

Abweichungen vom Plan benötigen dokumentierten Befund, Alternativen und eine
bestätigte Planänderung. Ein Agent darf weder das Ziel noch Abnahmekriterien
nachträglich passend zu einem misslungenen Lauf umdefinieren.
