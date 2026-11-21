# Archiv: Auftrag KI-0R „Nachrechnen“ – ausgeführt am 21.11.2026

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (Auftrag aus `9df7566`, ausgeführt auf `2579913`). Er ist
**nicht mehr aktuell**; der aktuelle Auftrag der KI-Linie steht in
`ki_erkundung/AUFTRAG.md`.

Ausgeführt auf dem Jetson, 18:55 bis 19:09, mit Christopher für drei
Blätter. Kein Motor, kein Sensor; nur die Werkzeuge dieser Linie und der
Bildbetrachter in einem gewöhnlichen Fenster. Tests am Jetson: 205 bestanden
(erwartet 202; die drei zusätzlichen kamen mit `2579913` vom KI-Rechner).

Der Bericht selbst liegt nicht im Repository.

## Vorab notierte Erwartungen und was gemessen wurde

| Aufnahme | Erwartung | Gemessen | Urteil |
|---|---|---|---|
| `labor_tuer_vorn`, `_vorn_2`, `labor_blatt_90` | Tür 0,78 bis 0,90 m | 0,90 m (aber eine andere Lücke, siehe unten), 0,78 m, 0,77 m | trifft nicht zu |
| `labor_tuer_seite_nah_b` | Tür 0,75 bis 0,95 m, zweite Kante „blatt“ oder „lot“ | 1,30 m, „sprung“, kein Vermerk | **trifft nicht zu** |
| `labor_tuer_weit`, `_weit_seite`, `labor_ecke` | Tür weiter angeboten, 0,75 bis 0,90 m | angeboten in allen drei: 0,72, 0,77 und 0,77 m | Breite bei einer knapp verfehlt |
| `labor_tuer_zu` | nichts angeboten | nichts angeboten | trifft zu |
| alle | an Türpfosten überwiegend kein Vermerk „wand_…“ | 1 von 7 mit „wand_…“ | trifft zu |
| `flur` | keine Erwartung | nichts angeboten; geprüft und verworfen wurde eine einzige Lücke (0,80 m bei −39°, dahinter 0,40 m frei) | – |

## Was das zeigt

- **Eine Verschlechterung durch die eigene Änderung.** Bei `labor_tuer_vorn`
  stand die Nummer jetzt auf der Türzarge: Eine 0,90 m breite Lücke 0,5 m
  vor der Tür hatte die 0,78 m breite Tür verdrängt (Grund im Prüftext:
  „liegt hinter einer näheren Tür“). In KI-0N war dieselbe Aufnahme richtig.
  Die Regel ist in `b3a1acf` zurückgenommen.
- **Die Vermutung „Türblatt“ für `labor_tuer_seite_nah_b` ist widerlegt.**
  Die Wandlinien werden jetzt gefunden, die Tür bleibt trotzdem 1,30 m breit
  und ohne Vermerk. Der Fehler ließ sich im künstlichen Zimmer mit derselben
  Zahl nachstellen, hatte dort aber eine andere Ursache als an der echten
  Tür. Die Ursache an der echten Tür ist offen.
- **Türen werden 8 bis 13 cm zu schmal vermessen** (0,72 bis 0,78 m bei
  wahren 0,85 m), auch ohne Raster. Das ist die vorsichtige Seite.
- **Im Flur sieht der Laser von diesem Standpunkt keine Öffnung.** Die KI
  beschrieb im Foto eine geschlossene Tür. Warum die beiden Türen, die
  Christopher nennt, im Profil nicht erscheinen, ist offen.

## Die KI mit der geänderten Frage

Keine falsche Wahl in elf Ansichten (vorher eine). Stand die Nummer auf der
Schwelle, wurde die Tür gewählt (vier von vier: `labor_blatt_90`,
`labor_tuer_vorn_2`, `labor_tuer_weit`, `labor_tuer_weit_seite`). Stand die
Nummer auf Zarge, Wand oder Mauerwerk, nannte die KI sie „wand“ und wählte
nichts (dreimal; in zwei davon war es die falsch gesetzte Nummer einer
echten Tür). Der Raumname war „unklar“ oder falsch.

Auswertung nach Christophers neuen Angaben zu drei Blättern: K0-1 richtig
8 von 11 (73 %), falsch 0, keine Wahl trotz Ausgang 3. K0-3 0 von 11
verworfen. K0-4 Median 1,5 s. K0-5 ein Paar mit verschiedener Wahl (Folge
der Verschlechterung bei `labor_tuer_vorn`). K0-6 Ausgang angeboten in
7 von 8 (88 %).
