# Arm — Build- und Integrationsprotokoll

Neue Einträge oben ergänzen, jeweils höchstens **200 Wörter einschließlich
Überschrift**. Jeder Eintrag nennt Änderung, Prüfung, Hardwarewirkung und
nächsten Schritt. Reale Abnahme und Simulation getrennt angeben.

## 2026-10-10 — Build A: Inbetriebnahme-Grundlage

Ergänzt wurden die ROS-Humble-Pakete arm_hardware, arm_tools und arm_bringup.
Sie enthalten ein unvollständig ausfüllbares Sechs-Achsen-Inventar, strikte
Konfigurationsprüfung, getrennte synthetische Testdaten, einen Fake-Transport
und eine begrenzte ESS17-RS07-Rohdatenprobe.

Die reale Probe verwendet ausschließlich zwei dokumentierte FC03-Leseblöcke.
Sie benötigt explizite Gelenkauswahl, bestätigte Identität, Port, Busparameter
und zwei Vor-Ort-Bestätigungen. Der unbekannte NEMA23 bleibt gesperrt.
Antwortfehler brechen den Lauf ab; Portzugriff ist exklusiv und wird geschlossen.
Es gibt keine Registerschreib-, Homing- oder Bewegungsbefehle.

Ergänzte Prüfungen: Konfigurations- und Fehlerfälle, CLI-Sperren, echte
Modbus-Kommunikation über ein synthetisches Pseudo-Terminal, Paketinstallation
und isolierter ROS-Humble-Build. Der CI-Testlauf steht bei Erstellung noch aus.

Hardwarewirkung: keine reale Verbindung oder Bewegung durchgeführt.
Der ausgefallene Entwicklungsrechner wurde durch einen separaten GitHub-Branch
ersetzt; bestehende Roboterstarts sind unverändert.

Nächster Schritt: CI-Ergebnis prüfen, danach Typ-/Gelenk-/Adresszuordnung und
Busparameter vor Ort erfassen. Erst anschließend eine beaufsichtigte
M1A-Leseprobe durchführen. Bewegungen folgen in einem getrennten Build.
