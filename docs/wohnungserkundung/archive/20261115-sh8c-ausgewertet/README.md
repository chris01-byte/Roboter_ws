# Archiv: Auftrag SH-8c (Stellprobe mit 100 ms Anfahrzeit) nach Ausführung und Auswertung

Bytegleicher bisheriger Agentenauftrag aus
`093b31e77081d9a137dbf79a14861da67c8c0869` (Text unverändert seit
`63c2630`); Originalblob `2e0dfea65a5d538c1c22f5d7d4a7cb20ffc9db29`, SHA256
`f21757bc843fe3f8b9ea4072bcf96393c70927377112494e3edfa0846cb57075`.

SH-8c wurde am 15.11.2026 auf dem Jetson ausgeführt (sieben Stackstarts,
vier mit Mission, jeder mit `hwt601_accel_ms:=100`). Ergebnis: **Stellprobe
nicht bestanden.** Ecke zweimal `befreit` (91,6 s und 93,4 s, Rückfahrt
0,307 und 0,308 m in etwa 21 s); Mülleimer `nicht_befreit` mit „Hilfe
benötigt“, weil der Kollisionsmonitor die Rückfahrt 16 s lang auf null hielt
(„approach“, VL53-Punkte im 2-cm-Polsterband); Garderobe bei 5 cm
`nicht_blockiert`, bei 3 cm vor der Mission von Bereich F abgefangen
(LiDAR-Punkte an der Frontkante im Gehäuse), danach Auftragsende. Keine
Berührung, kein Eingriff. Die Messgröße `wackeln` blieb leer (falscher
Topic-Name im Werkzeug). Auswertung im STATUS, Abschnitt 15.11.2026
(abends). Der hier archivierte Text ist kein aktueller Auftrag und darf
nicht erneut ausgeführt werden; der aktuelle Stand steht ausschließlich zwei
Ebenen höher in `AGENTENAUFTRAG.md`.
