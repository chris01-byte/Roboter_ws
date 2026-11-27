# Archiv: Auftrag KI-0N „Nachmessen“ – ausgeführt am 21.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (Stand `f28c84a`). Er ist **nicht mehr aktuell**; der
aktuelle Auftrag der KI-Linie steht in `ki_erkundung/AUFTRAG.md`.

Ausgeführt auf dem Jetson, 15:41 bis 17:56, mit Christopher: Teil 1 (N0 bis
N2) und Teil 2 (C1 bis C5). Kein Motor, kein Fahr-Stack; für vier neue
Ansichten liefen Kamera und LiDAR. Der Abschnitt „KI-Rechner –
Lotsen-Fenster einrichten“ gehört zum selben Auftrag; ein Bericht dazu liegt
hier nicht vor.

Der Bericht selbst liegt nicht im Repository. Bilder, Scans und Karten
blieben auf dem Jetson.

## Vorab notierte Erwartungen und was gemessen wurde

| Aufnahme | Vorher (KI-0) | Erwartung | Gemessen | Urteil |
|---|---|---|---|---|
| `labor_tuer_vorn`, `_2` | 0,74 und 0,73 m | etwa 0,75 m, Nummer auf der Schwelle | 0,75 und 0,72 m; Christopher: „Auf der Schwelle“ | trifft zu |
| `labor_tuer_seite_nah_b` | 1,22 m, Nummer neben der Tür | 0,70 bis 0,95 m, zweite Kante „blatt“ oder „lot“ | 1,24 m, „sprung“; Christopher: „die nummer ist zu weit rechts von der Tür auf einer wand“ | **trifft nicht zu** |
| `labor_tuer_weit_seite` | 1,76 m, Nummer auf dem Türblatt | 0,70 bis 0,95 m | 0,77 m in 3,54 m; Christopher: offene Tür, „Auf der Schwelle“ | trifft zu |
| `labor_tuer_weit` | Tür in 4–5 m ohne Nummer | die Tür hat eine Nummer | Nr. 2: 0,70 m in 3,96 m; Christopher: offene Tür, „Auf der Schwelle“ | trifft zu |
| `labor_ecke` | Ausgang 1,74 m breit | 0,70 bis 0,95 m | 0,72 m in 3,66 m, nur in der Skizze | trifft zu bei der Breite |
| alle sieben | 12 Vorschläge, 7 davon an Möbeln | weniger seitlich und hinten | 9 Vorschläge; außerhalb des Fotos 2 statt 5, hinter dem Roboter 0 statt 2; laut Christopher 6 Türen, 2 an Möbeln, 1 Mauerwerk | trifft zu |

## Die elf Ansichten (ohne Denken, `qwen3.5:9b`)

| Ansicht | Vermessen | Wahl der KI | Christopher | Urteil |
|---|---|---|---|---|
| `labor_tuer_vorn` | Nr. 1: 0,75 m | 1, offene Tür | Nr. 1 offene Tür | richtig |
| `labor_tuer_vorn_2` | Nr. 1: 0,72 m | 1, offene Tür | Nr. 1 offene Tür | richtig |
| `labor_tuer_seite_nah_b` | Nr. 1: 1,97 m bei −77°; Nr. 2: 1,24 m | 2, offene Tür | Nr. 2 Tür (Nummer zu weit rechts), Nr. 1 Möbel | richtig |
| `labor_tuer_weit` | Nr. 1: 0,60 m bei −31°; Nr. 2: 0,70 m in 3,96 m | 2, Durchgang | Nr. 2 offene Tür, Nr. 1 Möbel | richtig |
| `labor_tuer_weit_seite` | Nr. 1: 0,77 m | 1, offene Tür | Nr. 1 offene Tür | richtig |
| `labor_blatt_90` (neu) | Nr. 1: 1,40 m bei +86°; Nr. 2: 0,71 m | 2, offene Tür | Nr. 2 „genau mittig in der offnen tür“, Nr. 1 Möbel | richtig |
| `labor_ecke` | Nr. 1: 0,72 m bei +53°, nicht im Foto | keine | Nr. 1 kann die Tür sein, im Foto nicht zu sehen | keine Wahl |
| `labor_tuer_seite_nah` (Tür halb zu) | Nr. 1: 0,82 m | keine | Nr. 1 ist Mauerwerk neben der Tür | richtig (kein Ausgang angeboten) |
| `labor_tuer_zu` (neu) | nichts | keine | keine Nummer, kein Ausgang | richtig |
| `labor_moebelecke` (neu) | Nr. 1: 1,22 m bei +112°, nicht im Foto | keine | Möbel, kein Ausgang | richtig |
| `flur` (neu) | Nr. 1: 0,98 m in 0,56 m | 1, „Durchgang in die Küche“ | Nr. 1 ist die Wand zwischen zwei Türen; die beiden Türen haben keine Nummer | **falsch** |

Auswertung: K0-1 richtig 9 von 11 (82 %), kein Urteil (7 Ansichten mit
angebotenem Ausgang, nötig 10). K0-2 kein Urteil (kein Glas, kein Spiegel).
K0-3: 0 von 11 verworfen. K0-4: Median 1,6 s, längste 2,2 s. K0-5: ein Paar,
gleiche Wahl. K0-6: Ausgang angeboten in 7 von 8 (88 %), nötig 90 %.
Einordnung der Nummern 9 von 13 richtig. Raumname in 1 von 11 richtig.

Hatte die Tür eine Nummer und war sie im Foto, hat die KI sie gewählt: sechs
von sechs.

## Was nicht lief

- **Kein Live-Bild im Auftrag.** Zum Hinstellen wollte Christopher das
  Kamerabild sehen. Der Agent schrieb dafür ein eigenes Anzeigeprogramm
  (nicht im Repository). Die erste Fassung öffnete ein Vollbild, das sich
  nur mit einer Taste schließen ließ; der Hinweis kam bei Christopher nicht
  an. **Er musste den Jetson herunterfahren.** Kamera und LiDAR des ersten
  Starts endeten dadurch ohne SIGINT. Nach dem Neustart waren alle Aufnahmen
  und Dateien erhalten.
- `umgebung_we1.bash` setzt selbst `KI=…/ki_trockenlauf_ki0`; der Auftrag
  setzte `KI` davor. Vier Ausgabedateien landeten im alten Ordner und wurden
  kopiert.
- Der Bildbetrachter `eog` ignorierte SIGINT, wenn er im Hintergrund
  gestartet war; zwei Fenster wurden mit SIGTERM geschlossen.
- `ros2 topic echo --once` kürzt die Statusmeldung (nötig: `--full-length`);
  `ros2 topic hz … | tail` lieferte nichts (nötig: Umleitung in eine Datei);
  `MY=$$` nimmt die Shell des Agenten nicht aus.
- LiDAR-Treiber beim Beenden wieder `buffer overflow detected`.
- Nicht aufgenommen: Glas oder Fenster, Spiegel, anderes Zimmer, eine
  Ansicht zweimal an derselben Stelle.

Folgen daraus stehen in `ki_erkundung/STATUS.md`.
