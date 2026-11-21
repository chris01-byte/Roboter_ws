# Archiv: Auftrag KI-0 „Erstes Sehen“ – ausgeführt am 19. und 21.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (Stand `14294ec`). Er ist **nicht mehr aktuell**; der
aktuelle Auftrag der KI-Linie steht in `ki_erkundung/AUFTRAG.md`.

| Teil | Wo | Wann | Ergebnis |
|---|---|---|---|
| A (A0–A5) | KI-Rechner | 19.11.2026 | Modelle geladen, Kette mit echtem Modell läuft; im gezeichneten Beispielzimmer dreimal die Glastür gewählt; mit Denken keine Antwort in 60 s; Lotsen-Dienst wegen Netzschnittstelle nicht gestartet |
| A-Nachtrag (N1–N3) | KI-Rechner | vor Teil B (ein eigener Bericht dazu liegt hier nicht vor) | Belegt durch Teil B: Der Lotsen-Dienst war am 21.11.2026 vom Jetson aus über WLAN zu hören und hat geantwortet; mit Denken kam laut Christopher eine Antwort in höchstens 180 s |
| B (B0–B6) | Jetson | 21.11.2026, 10:00–11:29 | sieben Standbilder im Labor aufgenommen und gefragt, sechs gewertet; siehe unten |
| A6 | KI-Rechner | offen | der Lotsen-Dienst lief nach Teil B weiter |

## Ergebnis von Teil B in Zahlen (Bericht des Jetson-Agenten)

Die Berichte selbst liegen nicht im Repository. Bilder, Scans und Karten
blieben auf dem Jetson.

- Tests am Jetson (Python 3.10, ROS 2 Humble): 158 bestanden.
- Verbindung über WLAN: 14 Fragen beantwortet, 0 abgelehnt.
  Modell `qwen3.5:9b`, Ollama 0.32.15.
- Kamera: 320 × 180 (im ROBOT_TRANSFER standen für August 640 × 360),
  waagerecht 63,9°, senkrecht 38,7°, 2,0 Hz. LiDAR 9,9 Hz. Je Aufnahme
  16 Paare aus Bild und Scan, keines verworfen; Montage aus TF.
- Antwortzeit ohne Denken: 1,5 bis 2,7 s, die erste Antwort 4,0 s (davon
  2,4 s Laden). Mit Denken: 8 bis 16 s, einmal 64,6 s ohne brauchbare
  Antwort (verworfen, 25 674 Zeichen Denktext).

| Ansicht | Vermessen | Wahl der KI (ohne Denken) | Christopher |
|---|---|---|---|
| `labor_tuer_vorn` | Nr. 1: 0,74 m, 1,95 m, geradeaus | 1, offene Tür, Raum „Schlafzimmer“ | Nr. 1 ist die offene Tür; Raum Labor |
| `labor_tuer_seite_nah` (nicht gewertet, Tür fast zu) | Nr. 1: 1,02 m bei +128°; Nr. 2: 0,81 m bei −29° | 2, „offene Tür“ | „die tür war fast zu“ |
| `labor_tuer_seite_nah_b` | Nr. 1: 1,98 m bei −77°; Nr. 2: 1,22 m bei −18° | 2, offene Tür, Raum „Flur“ | Nr. 2 ist die Tür, „nur etwas daneben“; bei Nr. 1 ist nichts |
| `labor_tuer_weit` | nur Nr. 1: 2,25 m in 0,81 m | 1, „Durchgang“ (0,95), Raum „Wohnzimmer“ | kein Ausgang, Lücke an Möbeln; die offene Tür in 4–5 m hatte keine Nummer |
| `labor_ecke` | Nr. 1: 1,61 m bei +15°; Nr. 2: 1,74 m bei +57° (nicht im Foto) | keine Wahl | Ausgang ist Nr. 2; im Foto war kein Ausgang |
| `labor_tuer_weit_seite` | Nr. 1: 0,97 m; Nr. 2: 1,55 m; Nr. 3: 1,76 m bei −14° | 3, Raum „Wohnzimmer“ | Nr. 3 ist das Türblatt, der Durchgang liegt etwas weiter links; 1 und 2 Möbel |
| `labor_tuer_vorn_2` (Wiederholung, Standort ungefähr) | Nr. 1: 0,73 m, 2,45 m | 1, „Durchgang“, Raum „Flur“ | Nr. 1 ist die offene Tür |

Bekannte Breite der Labortür laut Christopher: 850 mm. Vermessen: von vorn
0,74 und 0,73 m, von der Seite 1,22 und 1,76 m, aus 4–5 m gar nicht.

## Bewertung (festgehalten in `ki_erkundung/STATUS.md`)

- Die Kette vom Roboter bis zur geprüften Antwort läuft an echten Geräten.
- Wo die Tür eine Nummer hatte und im Foto zu sehen war, hat die KI sie
  gewählt (vier von vier). Sie hat aber auch eine Möbellücke gewählt, wo
  nichts Besseres angeboten war, und eine fast geschlossene Tür „offen“
  genannt. Die Raumnamen waren in allen Ansichten falsch.
- Kein Urteil nach den Kriterien: zu wenige Ansichten (fünf mit angebotenem
  Ausgang, nötig sind zehn), kein Glas und kein Spiegel dabei.
- Das schwache Glied ist die Vermessung der Öffnungen, nicht die KI.

Mit der damaligen Auswertung stand im Bericht „K0-1 richtig 4 von 5“ und
„K0-2 bestanden“. Nachgerechnet mit der korrigierten Auswertung (Commit
`5319b7f`): richtig 4 von 6, K0-2 ohne Urteil.
