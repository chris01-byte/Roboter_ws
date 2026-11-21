# Arm — Build- und Integrationsprotokoll

Neue Einträge oben ergänzen, jeweils höchstens **200 Wörter einschließlich
Überschrift**. Jeder Eintrag nennt Änderung, Prüfung, Hardwarewirkung und
nächsten Schritt. Reale Abnahme und Simulation getrennt angeben.

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
