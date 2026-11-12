# Arm — Build- und Integrationsprotokoll

Neue Einträge oben ergänzen, jeweils höchstens **200 Wörter einschließlich
Überschrift**. Jeder Eintrag nennt Änderung, Prüfung, Hardwarewirkung und
nächsten Schritt. Reale Abnahme und Simulation getrennt angeben.

## 2026-11-12 — Dokumentation: Orbbec Gemini 305 zwischen J5 und J6

Der Nutzer hat die Orbbec Gemini 305 gewählt und setzt sie auf das
Handgelenkglied zwischen J5 und J6. Sein Datenblatt V1.0 ist ausgewertet:
passives Farb-Stereo, ideal 7–50 cm, Mindestabstand 40–180 mm je nach
Einstellung, USB-C mit USB 3, höchstens 2 W, Gehäuserückseite bis 60 °C.

Im CAD wurde die Kamera als Quader an vier Seiten des Handgelenkglieds
geprüft. Empfehlung: oben, leicht zur Greiferachse geneigt. Dann liegt sie
in der heutigen Parkpose nur 34 mm vor der Deckschräge, am J1-Anschlag
16 mm (CAD). Ein J5-Winkel von +30 bis +40° statt +20° in der Parkpose
schafft 51–67 mm; Entscheidung beim Nutzer.

Angepasst: Kalibrierkonzept (K4 prüft die Werkskalibrierung, K5 bezieht sich
auf das Handgelenkglied statt den Flansch), ARM_KONTEXT, Integrationsplan,
Messblatt, Projektstatus, Inventar, Kalibrierpaket-README.

Prüfung: nur Dokumentation, Verweise und Wortgrenze geprüft. Herstellerangaben
nicht am Gerät geprüft. Keine Hardwarewirkung.

Nächster Schritt: J5-Parkwinkel und Kameraseite entscheiden, dann
Hall-Sensor J5 setzen. Rückfallweg: Commit zurücknehmen.

## 2026-11-12 — Dokumentation: Kalibrierkonzept neu, Kamera am Handgelenk

Der Nutzer plant eine Kamera am Arm; RGB-D-Kameras für kurze Distanz (Orbbec
Gemini 305, RealSense D405, OAK-D SR) sind ihm für den Prototyp zu teuer.
Eingetragen ist eine günstige Variante nach Herstellerangaben: USB-Farbkamera
mit festem Fokus (rund 40–60 US-$) plus Abstandssensor VL53L7CX (rund
20 US-$) und Lichtschranke im Greifer. Bauraum 42 × 42 × 23 mm und ein
USB-3-fähiger Kabelweg halten den Wechsel zu einer Tiefenkamera offen.

Neu: docs/ARM_KALIBRIERKONZEPT.md. Es ersetzt das Juli-Konzept, das eine
feste OAK als einziges Auge für den Griff voraussetzte. Stufen K1–K7: OAK
grob, Armmodell, Werkzeug und Greifersensoren, Intrinsik und Eye-in-Hand der
Handgelenkkamera, Gesamtprüfung, laufender Abgleich. Grenzwerte folgen aus
dem Fangbereich des Greifers und der Sichtfeldbedingung der Vorposition.

Angepasst: ARM_KONTEXT, Integrationsplan (Abschnitte 6, 8, 10, M7, M8),
Messblatt, Einstiegsseiten, Inventar, Kalibrierpaket-README und der Kopf des
Juli-Konzepts.

Prüfung: nur Dokumentation, Verweise und Wortgrenze geprüft. Keine
Hardwarewirkung.

Nächster Schritt: Kameramodell und Montageort festlegen; danach
Eye-in-Hand-Modus im Löser als eigener, getesteter Build. Rückfallweg: Commit
zurücknehmen.

## 2026-11-12 — Dokumentation: Greifsicht der OAK und Sensor am Handgelenk

Frage des Nutzers: Braucht der Arm eine zusätzliche Kamera mit Blick auf den
Greifer? Die Entscheidung ist offen; eingetragen ist die Evidenz.

Rechnung (Kamerahöhe 1,35 m gemessen, 16:9): Bei der heutigen Neigung von
18,94° liegt eine Tischfläche erst ab 0,59 m vor der Chassisfront im Bild,
eine Arbeitsplatte ab 0,41 m. Couchtisch und Boden sind innerhalb der
Reichweite von 0,81 m nie im Bild. Bei 10° und flacher liegt auch die
Tischfläche außerhalb der Reichweite. Raumsicht und Greifsicht schließen
sich bei fest montierter OAK aus.

Empfohlen ist ein in Greifrichtung schauender Sensor am Handgelenk.
Verglichen sind zwei Montageorte (am Greifer hinter J6, am Handgelenkglied
vor J6) und zwei Kandidaten nach Herstellerangaben (RealSense D405, Luxonis
OAK-D SR).

Prüfung: nur Dokumentation; Verweise und Wortgrenze geprüft.
Herstellerangaben per Websuche, nicht am Gerät geprüft. Keine
Hardwarewirkung.

Nächster Schritt: Entscheidung des Nutzers zu Sensor, Montageort und
Kabelweg vor der Greiferkonstruktion. Rückfallweg: Commit zurücknehmen.

## 2026-11-11 — Dokumentation: Restfragmente zum Arm bereinigt

Auf Nutzerwunsch wurde das ganze Repository nach armbezogenen Begriffen
durchsucht, Code, Konfiguration, App und Prüfskripte eingeschlossen.

Bereinigt: Der Jetson-Prüfplan ließ den überholten Dummy-Arm in RViz als
korrekt bestätigen und verwies für die Kalibrierung auf das historische
Juli-Konzept; jetzt wird der Dummy-Arm ausgenommen und auf Stufe M7
verwiesen. Das Kalibrierpaket erhielt einen Stand-Hinweis: historisches
Konzept, abweichende Kamera-Frames, offenes Flansch-Frame. Ein Satz im
Arm-Kontext widersprach dem neuen Homing-Ablauf.

Bewusst belassen und gekennzeichnet: Dummy-URDF, Ablageposen im
Missionskatalog, Greifer-Platzhalterwerte im Behavior-Tree, historisches
Kalibrierkonzept und Archiv. Der alte CAD-Ordner bleibt bis zur
Nutzerentscheidung.

Prüfung: Shell-Syntax des Prüfplans, Verweise und Wortgrenze geprüft. Nur
Texte geändert, keine Hardwarewirkung.

Nächster Schritt: Arbeitsbranch nach main übernehmen. Rückfallweg: Commit
zurücknehmen.

## 2026-11-11 — Dokumentation: Homing mit Einzelmagnet und Überfahrschutz

Festlegungen des Nutzers: kein Magnetbogen, sondern ein Einzelmagnet je
Achse; J1 erhält einen mechanischen Anschlag; Absolutwertgeber sind
konstruktiv nicht mehr möglich; die Parkposition steht fest.

Der Nutzer stellte das Modbus-Funktionshandbuch und das
ESS17-Hardware-Handbuch bereit. Ausgewertet und mit Seitenangaben
eingetragen: Eingangsfunktionen und Eingangsstatus, Referenzmodi 19–22 und
35, Positionssetzen nach der Referenz, Soft-Limits, Verhalten beim
Überfahren, Schleppfehlergrenze, Strombegrenzung und Alarm Err5.

Konzept: Sensor in der Parkstellung aktiv, Referenz am Fensterende auf der
freien Seite; Start nur bei aktivem Sensor; Suche als Positionsfahrt mit
festem Höchstweg; Übergabe per Referenzmodus 35; danach Soft-Limits. Laut
CAD darf der J1-Anschlag höchstens 1–2° hinter der Parkstellung liegen.

Prüfung: nur Dokumentation, Verweise und Wortgrenze geprüft. Keine
Registerschreibzugriffe, keine Hardwarewirkung; Antriebsfunktionen am Gerät
unbestätigt.

Nächster Schritt: Gelenkbereiche je Achse und Fensterbreite messen.
Rückfallweg: Commit zurücknehmen.

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
