# Arm — Build- und Integrationsprotokoll

Neue Einträge oben ergänzen, jeweils höchstens **200 Wörter einschließlich
Überschrift**. Jeder Eintrag nennt Änderung, Prüfung, Hardwarewirkung und
nächsten Schritt. Reale Abnahme und Simulation getrennt angeben.

## 2026-11-11 — Dokumentation: Parkpose ausgewertet, Homing-Konzept

Ausgewertet wurde der zweite STEP-Export des Nutzers, eine mögliche
Homing-/Parkposition: Hub oben, J1 −180°, J2 −40°, J3 −90°, J4 0°, J5 +20°,
J6 0° gegenüber der gestreckten Nullpose. Das Gelenkmodell gibt den Export
auf 0,4 mm genau wieder.

Rechnerisch hängt der Arm hinter dem Mast: tiefster Punkt real 698 mm, aber
im maskierten LiDAR-Sektor; OAK-Verdeckung 0 % bis etwa 19° Neigung;
Überstand vorn 23 mm, hinten 22 mm. Aus der Parkpose ist für jede Achse die
Richtung nach hinten-oben frei. Die Gegenrichtung ist mit
150-mm-Greifermittellinie nach 8° (J1) bis 44° (J4) blockiert.

Eingetragen als Vorschlag: TLE4905L am Gelenkausgang, Magnetsektor aktiv in
der Parkpose, Referenzkante wenige Grad auf der freien Seite, Einzelachsfolge
mit begrenztem Suchweg; automatisch nur, wenn alle Sensoren aktiv sind.

Prüfung: nur Dokumentation; Kollisionsrechnung aus CAD ohne Kabel und
Greiferform; Verweise und Wortgrenze geprüft. Keine Hardwarewirkung.

Nächster Schritt: Konzept bestätigen, Kantenlage und J1-Parkanschlag
konstruieren, ESS-Homingfunktion im Handbuch prüfen. Rückfallweg: Commit
zurücknehmen.

## 2026-11-11 — Dokumentation: Arm neu konstruiert, Kinematik neu

Der Nutzer hat den Arm neu konstruiert, weil J2 im alten CAD um 90° falsch
eingebaut war. Ausgewertet wurde der STEP-Export in gestreckter Pose mit
OpenCascade; die Bauteile tragen jetzt Gelenknamen.

Neu eingetragen: J1 quer am Hubschlitten, J2 130 mm davor mit senkrechter
Achse, Armachse 94 mm über J1, J3 156 mm vor J2, J5 257 mm vor J3, Flansch
149 mm vor J5, Unterarm 86 mm seitlich versetzt; gestreckt 755 mm ab
Schlitten (Nutzer: 746 mm). J2 schwenkt den Flansch rechnerisch von
y = −422 bis +700 mm.

Überholt und entsprechend markiert: Kinematik, Transportpose, LiDAR-Abstand
und OAK-Studie vom 09./10.11. Simulation neu für den gestreckten Arm: bei
18,94° Neigung 24 % verdeckt mit Hub oben, 4 % mit Hub unten.

Prüfung: nur Dokumentation; Verweise und Wortgrenze geprüft. Keine
Messung, keine Hardwarewirkung.

Nächster Schritt: Homing-Position als STEP auswerten. Rückfallweg: Commit
zurücknehmen.

## 2026-11-10 — Dokumentation: korrigiertes CAD und Messwerte

Der korrigierte STEP-Export vom 09.11.2026 wurde mit OpenCascade ausgewertet:
Die Basis war im ersten Export 105 mm zu niedrig, der Arm ist unverändert.
Eingetragen sind Achslagen und Abstände J1–J6, J2 an der Ecke vorn oben mit
Querachse parallel zu J1 und J3, gestreckt rund 753 mm ab Schlitten (Nutzer:
746 mm), 136 mm Überstand und rund 4 cm Abstand zur LiDAR-Ebene nur bei Hub
ganz oben.

Messungen des Nutzers: LiDAR-Scheibenmitte 705 mm, OAK-Mitte 1350 mm,
Schlittenunterkante 1140 mm. LiDAR- und OAK-Höhe weichen von der laufenden
Konfiguration ab; Korrektur als eigener Sensor-Frame-Schritt.

Simulation der OAK in Transportpose: bei 18,94° rund 20 % verdeckt, armfrei
bis etwa 4°, mit 50 mm höherer Kamera bis etwa 13°.

Prüfung: nur Dokumentation; Verweise und Wortgrenze geprüft. Keine Messung
durch Agenten, keine Hardwarewirkung.

Nächster Schritt: Entscheidungen zu J2 und OAK-Neigung. Rückfallweg: Commit
zurücknehmen.

## 2026-11-08 — Dokumentation: Armaufbau eingetragen, Repo bereinigt

Nutzerangaben vom 08.11.2026 eingearbeitet: Hubachse mit 400 mm Hub plus
sechs Drehgelenke, J4 hinter dem Ellenbogen, neues Greifer-Drehgelenk J6,
J1 mit NEMA23 der ESS-RS-Reihe und 55,25:1, J2–J5 mit 72:1, Schulterhöhe
1106 mm, Reichweite etwa 746 mm plus Greifer bis 150 mm, mindestens 130 mm
Überstand in Transportpose, Nutzlast 1 kg, Not-Aus trennt die gesamte
Versorgung, eigener RS485-Adapter verbaut, Arm in Einzelteilen. Die OAK
dient beim Greifen nur Erkennung und Anfahrdistanz.

Überholte Aussagen gekennzeichnet: iCL-Stepper, sechs ESS17, Arm hinten auf
der Plattform, Ablagehöhen im Missionskatalog, Feinlokalisierung allein mit
der OAK.

Prüfung: Arm-Offline-Tests unverändert grün, interne Verweise und
Wortgrenze geprüft. Nur Dokumentation und Kommentare; keine Werte, kein
Code, keine Hardwarewirkung.

Nächster Schritt: Hubachse, J6-Antrieb, Gewichte und CAD-Export klären;
danach Inventarschema um die Hubachse erweitern (eigener Build), M0, M1A.
Rückfallweg: Commit zurücknehmen.

## 2026-10-10 — Dokumentation: Armplanung rekonstruiert

ARM_KONTEXT, Integrationsplan und das bislang im gesicherten Branch fehlende
Inbetriebnahme-Messblatt wurden aus Nutzerangaben und Repository-Quellen
rekonstruiert. Der ursprüngliche lokale Wortlaut ist nicht zugänglich.

Dokumentiert sind die fünf ESS17 plus ein noch unbekannter NEMA23,
TLE4905L-Eingangsanbindung, Homing-/Nullpunktkonvention, Einzelachsabnahme,
Koordination, XL330-Spindelgreifer mit Endlagen und Widerstandssensoren,
sensorfreie Transportpose und spätere OAK-Kalibrierung.

Der Plan berücksichtigt den bereits vorhandenen Read-only-Build A.
Homing, Bewegung und reale Abnahmen sind ausdrücklich weiterhin offen.
AGENTS, Einstiegsseiten und Projektstatus verlinken die Dokumente.
Das ältere Kalibrierkonzept ist als historische, teilweise überholte
Grundlage gekennzeichnet.

Prüfung: interne Dateiverweise und Markdown-Struktur kontrolliert;
Eintragslänge unter 200 Wörtern. Keine Software-, Konfigurations- oder
Hardwareänderung und kein neuer realer Test. Der frühere CI-Nachweis
für Build A bleibt separat dokumentiert.

Nächster Schritt: Messblatt M0 ausfüllen, anschließend die beaufsichtigte
M1A-Leseprobe. Rückfallweg: diesen reinen Dokumentationscommit zurücknehmen;
laufende Roboterstarts bleiben unverändert.

## 2026-10-10 — Build A: Inbetriebnahme-Grundlage

Ergänzt wurden die ROS-Humble-Pakete arm_hardware, arm_tools und arm_bringup.
Sie enthalten ein unvollständig ausfüllbares Sechs-Achsen-Inventar, strikte
Konfigurationsprüfung, getrennte synthetische Testdaten, einen Fake-Transport
und eine begrenzte ESS17-RS07-Rohdatenprobe.

Die reale Probe verwendet ausschließlich zwei dokumentierte FC03-Leseblöcke.
Sie benötigt explizite Gelenkauswahl, bestätigte Identität, Port, Busparameter
und zwei Vor-Ort-Bestätigungen. Der unbekannte NEMA23 bleibt gesperrt.
Antwortfehler brechen den Lauf ab; Portzugriff ist exklusiv und wird geschlossen.
Eine gemeinsame Zeitgrenze begrenzt auch Störverkehr und blockiertes Schreiben;
nach Verbindungsverlust erfolgt kein automatisches Wiederöffnen.
Es gibt keine Registerschreib-, Homing- oder Bewegungsbefehle.

Ergänzte Prüfungen: Konfigurations- und Fehlerfälle, CLI-Sperren, echte
Modbus-Kommunikation über ein synthetisches Pseudo-Terminal, Paketinstallation
und isolierter ROS-Humble-Build. Ergebnis auf 9e65e4f: alle 32 Tests,
Installation und Humble-Build bestanden ([CI](https://github.com/chris01-byte/Roboter_ws/actions/runs/38070478719)),
einschließlich Dauer-Störverkehr, fehlender Antwort und Verbindungsverlust.
Serielle Abhängigkeiten sind optional deklariert;
ihre Anforderungsliste wird mitinstalliert. Hardwareabnahme bleibt offen.

Hardwarewirkung: keine reale Verbindung oder Bewegung durchgeführt.
Der ausgefallene Entwicklungsrechner wurde durch einen separaten GitHub-Branch
ersetzt; bestehende Roboterstarts sind unverändert.

Nächster Schritt: Typ-/Gelenk-/Adresszuordnung und
Busparameter vor Ort erfassen. Erst anschließend eine beaufsichtigte
M1A-Leseprobe durchführen. Bewegungen folgen in einem getrennten Build.
