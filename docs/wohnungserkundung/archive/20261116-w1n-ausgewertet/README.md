# Archiv: Auftrag W-1N (nur lesende Auswertung der Wohnungsfahrten aus W-1) nach Ausführung und Auswertung

Bytegleicher bisheriger Agentenauftrag aus
`fcef2cc3a7d32fb78aa7921de701bd6333434ad8`; Originalblob
`6fb024e695bb5e521aa9f70fd7f0b01fd23cf4e2`, SHA256
`b45948a10090515c6c242168ac31b384e5af8b71f984c172b981530004e88816`.

W-1N wurde am 16.11.2026 auf dem Jetson ausgeführt, nur lesend (kein
Stackstart, keine Fahrt, kein Build). Ergebnis: Die zwei Wohnungsfahrten
scheiterten aus verschiedenen Gründen. Fahrt 1: alle 10 Ziele hinter der
78-cm-Tür gescheitert, Amadeus stand am Ende neben dem 22 cm breiten
Streifen, den der Planer zulässt. Fahrt 2: nie näher als 0,87 m an der Tür;
12 von 14 Abbrüchen durch veraltete Lokalisierung, danach 13-mal derselbe
Anlauf neu. Der Bericht deckte außerdem zwei Fehler der Cloud-Auswertung auf
(„43° schräg“ war nicht gemessen; die lokale Kostenkarte von w1 war
veraltet) und eine Schwäche des Werkzeugs `karte_engstelle.py` an
1-cm-Karten. Auswertung im STATUS, Abschnitt 16.11.2026. Der hier
archivierte Text ist kein aktueller Auftrag und darf nicht erneut ausgeführt
werden; der aktuelle Stand steht ausschließlich zwei Ebenen höher in
`AGENTENAUFTRAG.md`.
