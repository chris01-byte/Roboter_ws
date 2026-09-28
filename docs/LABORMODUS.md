# LAB-1 – verbindlicher Laborarbeitsmodus für Amadeus

**Version 1.0 · 28.09.2026 · Nutzerentscheidung von Christopher**

Diese Regel dokumentiert die ausdrücklich gewünschte durchgängige Laborfreigabe:
Amadeus befindet sich im dafür vorgesehenen kontrollierten Entwicklungsraum.
Agenten sollen einen beauftragten Laborumfang selbstständig durcharbeiten,
statt für unveränderte Bedingungen wiederholt dieselben Freigaben anzufragen.
Die Regel gilt auch bei Agentenwechsel; sie ist keine neue Roadmap.

## 1. Geltung und bereits erklärte Rahmenbedingungen

Für den jeweils ausdrücklich beauftragten, abgegrenzten Laborumfang gelten
Christophers Angaben als hinterlegte Betreibererklärung: kontrollierter Bereich,
erreichbarer unabhängiger Halt/Not-Aus, keine unbeteiligten Personen oder Tiere
im vorgesehenen Fahrbereich und ausreichender Raum für die festgelegten Versuche.
Diese Angaben nicht bei jedem Preflight, Stackstart oder Agentenwechsel erneut
abfragen. Ihre Quelle ist die Nutzererklärung, nicht eine eigene Messung des Agenten.

Die Laborfreigabe gilt bis Widerruf innerhalb dieses Rahmens. Sie ist keine
unbegrenzte Bewegungsfreigabe: Auftragsgrenzen, freigegebener Laborbereich und
bestehende technische Schutzbedingungen bleiben maßgeblich. Keine automatische
Übertragung auf Kundenwohnungen, neue Räume, Arm-/Hubversuche oder einen
wesentlich veränderten Aufbau. Ein neuer Bereich oder größerer Bewegungsumfang
ist nicht allein durch das Wort „Labor“ freigegeben.

## 2. Durcharbeiten ohne wiederholte Standardfragen

Innerhalb des beauftragten Umfangs sind ohne zusätzliche Erlaubnisrunde erlaubt:

- Repository-/Loganalyse, isolierte Builds, gerätefreie Tests und die beauftragten
  begrenzten Fehlerkorrekturen mit gezielten Regressionen;
- Start und geordneter Stopp der vorgesehenen Sensor-, ROS- und Recorderprozesse,
  Runtime-Manifeste, motorlose Preflights sowie technische Karten-/TF-/Scopebindung;
- regulärer Wechsel in den vorgesehenen aktiven Produktmodus und Ausführung des
  bereits beauftragten begrenzten Fahrtests über die vorhandene Schutzkette;
- technisch begründete Wiederholungen nach einer Korrektur innerhalb des
  festgelegten Versuchs-, Zeit- und Bewegungsbudgets, ohne Endlosschleifen.

Keine wiederholten Fragen wie „Ist der Not-Aus erreichbar?“, „Ist genügend Platz?“,
„Darf ich den Stack/Recorder starten?“, „Darf ich motorlos testen?“ oder
„Darf ich jetzt den bereits beauftragten Fahrtest starten?“, solange der bekannte
Aufbau und der Umfang unverändert sind und kein konkreter Widerspruch vorliegt.
Keine neue Vorlage verlangen, wenn der ausführbare Auftrag bereits vorliegt.

Ein Buildfehler, fehlendes Profil, nicht gebundener Scope, veraltetes Topic oder
fehlendes Ziel ist ein technischer Befund, kein Anlass für eine allgemeine
Freigaberunde. Vorhandene Artefakte selbst suchen, innerhalb des Auftrags
korrigieren und gezielt prüfen. Eine dabei notwendige Bewegungssperre bleibt
wirksam; die gerätefreie Arbeit kann weitergehen. Wiederholte identische
Fehlversuche nicht aneinanderreihen.

## 3. Freigabe und tatsächlicher Hardwarezustand getrennt halten

Eine dauerhafte Erlaubnis bedeutet weder „Motoren sind immer gesperrt“ noch
„Motoren sind immer freigegeben“. Den zuletzt verlässlich bekannten Zustand,
vorhandene Rückmeldungen und tatsächlich ausgeführte Bedienhandlungen verwenden.
Keine Schalterstellung, physische Stillstandsbeobachtung oder Quellenbereitschaft
aus dieser Markdown-Datei erfinden.

Kann eine notwendige physische Umschaltung nicht durch eine freigegebene
Schnittstelle ausgeführt und überprüft werden, genau diese Bedienhandlung einmal
konkret anfordern, statt alle Laborbedingungen erneut abzufragen. Solange ihr
notwendiger Zustand ungeklärt ist, die betroffene Bewegung gesperrt lassen.
Das ist eine konkrete Betriebsanforderung, keine neue pauschale Fahrfreigabe.

Motorlose Prüfung und aktive Ausführung richtig trennen: Unter
`active_drive=false` kein aktives Nav2-Kind als Voraussetzung verlangen.
Der reguläre aktive Modus ist kein Umgehen der Read-only-Sperre. Ein Besitzer
je Gerätebus; nach nötigem Stack-/SLAM-Neustart aktuellen Kartenbezug selbst
prüfen. Bekannte Maße wiederverwenden, aber keine Koordinaten oder Freiräume
für unbekannte Bereiche erfinden.

## 4. Technische Schutzwirkung bleibt bestehen

Preflights, Footprint/Costmaps, Collision Monitor, VL53, HWT-/Encoder-Frische,
Pose-/TF-Gültigkeit, Watchdogs, Stillstands- und Recoverybedingungen bleiben
aktiv. Keinen Sensorzustand, Scope-Nachweis oder Freigabetopic auf „gesund“
fälschen. Keine direkten ungegateten Fahrbefehle und keine pauschale Lockerung
von Grenzen. Not-Aus und Nutzerabbruch nicht automatisch zurücksetzen.

Bei einem konkreten Widerspruch – etwa ausgelöstem Not-Aus, unkontrollierter
Bewegung, tatsächlichem Eintritt einer Person/eines Tiers, nicht ausreichend
geklärtem Quellen-/Posefehler, geändertem Aufbau oder nötiger Überschreitung des
Auftrags – die betroffene Ausführung sicher anhalten. Softwareursache und
Hardwaredefekt nicht gleichsetzen; nicht erst auf einen bewiesenen Kabelbruch
warten. Nur den konkreten Befund, die betroffene Grenze und die tatsächlich
fehlende Handlung/Entscheidung melden. Keine erneute Standardcheckliste.

## 5. Dokumentation und Vorrang bei Freigabeformulierungen

Diese ausdrücklich hinterlegte Nutzerentscheidung erfüllt die organisatorische
Freigabeanforderung für den beschriebenen Laborumfang. Ältere Aufforderungen zu
separaten Freigaben jedes unveränderten Teilschritts sind darin durch LAB-1 ersetzt.
Technische Voraussetzungen, gültige Testgrenzen und historische Nachweise werden
dadurch weder aufgehoben noch rückwirkend als bestanden gewertet.

Vorhandene STATUS-/Auftrags-/Übergabedokumente verwenden, keinen zweiten
Sitzungsmanager und keine neue Freigabe-Software bauen. Ein kurzer Verweis auf
LAB-1 sowie der konkrete Auftragsumfang genügt; diese Angaben selbst führen,
nicht als zusätzliche Benutzercheckliste zurückgeben. Herkunft von
Betreibererklärungen, Messdaten und Außenbeobachtungen getrennt dokumentieren.

Das Einpflegen dieser Regel ist ausschließlich eine Dokumentationsänderung.
Es startet keine Prozesse, aktiviert keine Aktoren, ändert keinen Install und
führt keinen Merge aus. Außerhalb des beschriebenen Laborkontexts gelten die
sonstigen Freigaberegeln unverändert.
