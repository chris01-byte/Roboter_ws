# Archiv: Auftrag AT-2 (Antriebsprobe mit 100 ms Anfahrzeit) nach Ausführung und Auswertung

Bytegleicher bisheriger Agentenauftrag aus
`487de06ffa2b50f0e6f506085b5567d8c5f05f48`; Originalblob
`d478abb72605e429f0eeb106b12d768a9869bf7f`, SHA256
`55ad8ecebcfaa60cca098c179cf78857e272a4c5b60303dd5984fe43ae6e2050`.

AT-2 wurde am 15.11.2026 auf dem Jetson ausgeführt: ein scharfer Stackstart
mit `hwt601_accel_ms:=100` ohne Mission, zwei Proben direkt auf `/cmd_vel`,
ohne Abbruch, ohne Berührung und ohne Eingriff; die Messung war ungestört.
Ergebnis: **bestanden**, zweimal `antrieb_folgt_rampen: ja`, alle sechs
Abschnitte 0,96–1,03, Stufe 0,99. Christopher sah Ruckeln beim Anfahren
(Probe 1 erste Fahrt, Probe 2 letzte Fahrt). Auswertung im STATUS, Abschnitt
15.11.2026 (nachmittags). Der hier archivierte Text ist kein aktueller
Auftrag und darf nicht erneut ausgeführt werden; der aktuelle Stand steht
ausschließlich zwei Ebenen höher in `AGENTENAUFTRAG.md`.
