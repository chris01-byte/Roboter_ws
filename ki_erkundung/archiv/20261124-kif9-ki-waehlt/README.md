# Archiv: Auftrag KI-F9 „die KI wählt die Tür“ – ausgeführt am 24.11.2026 (nachts): einer von zwei

Hier liegt der Auftrag [AUFTRAG.md](AUFTRAG.md) in der Fassung, in der er
ausgeführt wurde (`30e72a4`). Er ist **nicht mehr aktuell**.

Jetson, mit Christopher, 00:04 bis 01:06. **Kein Build:** Release
`kif8-20261123_2138` mit `kif8.env`, beide unverändert; unter `src/` seit
`d61453c` nichts geändert. Tests der KI-Linie 340 bestanden. Eine Frage
vorab (F0), „ja“. Vorlauf ohne Motorfreigabe wie erwartet: Kamera 2,0 Hz,
Aufnahme im Stand mit Lage in der Karte, Antwort der KI in 6,2 s, die Wahl
beim Messen wiedergefunden (Mitten 0,00 m auseinander). Kein Radsensor
gesperrt, keine Motorregler-Ausnahme. Der Bericht liegt nicht im
Repository.

## Was lief

| Lauf | Wahl der KI | Christopher | Ablauf | Ergebnis |
|---|---|---|---|---|
| 1 | Nr. 1 „Durchgang“, 95 % (die Labortür), Antwort 2,2 s | „ja“ | Rundblick 363°, Wahl wiedergefunden (0,04 m), Anfahrt 1,61 m, neu gemessen, Tür wiedergefunden (1,63 m vor der Tür, 0,03 m rechts), Durchfahrt; 9 Etappen, 3,49 m | „Durchfahrt abgeschlossen.“; „erfolgreich, weiter mit lauf 2“ |
| 2 | Nr. 2 „offene Tür“, 90 %, 174° rechts (daneben Nr. 1, 176° rechts, „Lücke an Möbeln“) | „nein es ist ein Fensterrollo“ | `--ende --quelle mensch` | „beendet ohne Fahrziel (Quelle mensch); nichts gefahren“ (S-1 trifft zu) |
| 2w | – | – | Aufnahme beim Beenden mit `kill -INT` abgestürzt (`RuntimeError: Unable to convert call argument to Python object` in `take_message`); keine Blickrunde | `--ende --quelle ki`, nichts gefahren |
| 2w2 | Nr. 1 „offene Tür“, 95 % (die Labortür) | „ja“ | Wahl wiedergefunden (0,04 m), Anfahrt geplant (101° links, 1,35 m, 110° rechts, 0,45 m); „Kostenkarte passt nicht: belegt 1.87 m voraus (Strecke 1)“, Herkunft „Karte (SLAM) frei; Laser sieht dort etwas“, 1,86 m links von Amadeus | keine Fahrt; „da war aber nichts“ |
| 2w3 | Nr. 1 „offene Tür“, 90 % (die Labortür) | „ja“ | Wahl wiedergefunden (0,01 m), Anfahrt 1,57 m (87° und 102° gedreht); danach eine Öffnung 0,77 m, +9,2°, 2,01 m | „Nichts gesendet: Die Tür von vorhin ist nach der Anfahrt nicht wiederzufinden.“; keine Durchfahrt; nichts berührt |

Je Lauf ein Missionsstart; alle Zähler der Kette 0; höchstens 0,050 m/s und
0,100 rad/s. Antworten der KI 1,7 bis 2,4 s, Aufbereiten der Runde auf dem
Jetson 6,7 bis 7,9 s. Christophers Ja oder Nein kam 101 bis 211 s nach
Beginn der Wartezeit (höchstens 420 s).

**G-1 trifft nicht zu: einer von zwei Läufen.** Lauf 2 wurde auf
ausdrückliche Anordnung dreimal wiederholt (der Auftrag erlaubte eine
Wiederholung). Weitere Abweichungen laut Bericht: `ki_tuer_waehlen.py`
einmal ohne die Umgebung der zweiten Shell aufgerufen (`ModuleNotFoundError:
rclpy`), gleich danach mit Umgebung; das Suchmuster für den Status passte
nicht auf das JSON ohne Leerzeichen; nach Lauf 2, 2w und 2w2 blieb die Frage
nach einer Berührung beim Drehen ohne ausdrückliche Antwort.

## Was daraus folgt

Christophers Einschätzung: „Das Grundkonzept funktioniert. Wir hatten
einige erfolgreiche Durchfahrten.“ Drei Dinge müssen robuster werden: die
Wahl der KI (Fensterrollo), die Kostenkarte (belegt, obwohl laut ihm nichts
da war), das Wiederfinden der Tür nach der Anfahrt. Dazu der Absturz der
Aufnahme. Die Bewertung dazu folgt (Stand siehe [STATUS.md](../../STATUS.md)).
