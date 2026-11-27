# AP-06: Fehlender robuster Startbeobachtungsnachweis

Stand 07.10.2026, Softwarekandidat `5612878`. **Kein Hardwareauftrag,
kein Deployment, kein Wechsel des Szenarios oder der Schutzreserven.**

## Belegter Befund

A238 erreicht nach Reparatur der Auswahl sein natives Fahrzielangebot, wird aber
nach 2,1 cm Gesamtfahrt korrekt gestoppt. Schon die gemessene Pose
`(0,0054301801 m; -0,0000002189 m; -0,0001019690 rad)` verletzt den festen
Anfangsnachweis: Zelle `(122,77)` wächst von `0,7071073623` auf
`0,7085175650` Rasterflächen-Einheiten und ist nicht vollständig im ursprünglichen
Polygon enthalten. Die Karte hat 1 cm Auflösung. Die Modellpose bei vergleichbarer
Vorfahrt zeigt ebenfalls eine kleine reale Kurve; bloße Encoderquantisierung
oder eine SLAM-Korrektur sind deshalb keine vollständige Erklärung.

A244 prüft unabhängig das erhaltene ursprüngliche A227-Inventar. Die gerade
Nominalpose gleicher Vorfahrt besteht; die tatsächliche A238-Pose verletzt auch
hier exakt dieselbe Zelle mit denselben Flächen. Das ist ein kontrollierter
Gegenfall auf dem separat aufgezeichneten Inventar, kein Ersatz der A238-Historie.

Das vorhandene allgemeine Trackingmodell verlangt 2 cm Positions- und 0,05 rad
Headingreserve zusätzlich zur unveränderten gepaddeten Kontur und Rasterreserve.
Auf A227 fehlen dafür schon am Anfang folgende Zellen außerhalb des festen
privaten Inventars:

| Raster | zusätzlich unbeobachtete Zellen | belegte Zellen im geprüften Band |
|---|---:|---:|
| Rohkarte | 138 | 0 |
| Kostenkarte | 36 | 0 |

Die Mittelpunkte liegen relativ zur aufgezeichneten Startpose im Streifen
`x = -0,175 … -0,155 m`, `y = -0,275 … +0,285 m`. Die genauen einzelnen
Rasterzellen stehen in `a244-start-coverage.json`; die Boundingbox allein ist
keine Freigabe. Der vollständige vorhandene Trackingprüfer lehnt ab.

**Folgerung:** Eine ideal gerade Nominaltrajektorie ist für diesen Start kein
robuster Ausführungsnachweis. Mehr Rechenleistung löst die fehlende Beobachtung
nicht. Neue unbekannte Fläche freizugeben, das Anfangsinventar neu zu verankern
oder die Trackingreserve zu entfernen wäre keine zulässige Korrektur.
Die Zahlen belegen diesen Startzustand; keine Behauptung, damit seien alle
möglichen autonomen Beobachtungsbewegungen mathematisch ausgeschlossen.

## Separat vorbereitetes Abdeckungspaket

MASTERPLAN v1.3, AP-03 verlangt bei nicht erfassbaren notwendigen Bereichen:
„eine begründete Änderung von Sensorposition/Abdeckung als separates Paket“
und „keine weitere Serie identischer Fehlstarts“.

1. **Anforderung:** Vor dem ersten Fahrbefehl echte aktuelle freie Beobachtung
   des konkret fehlenden rückwärtigen Streifens einschließlich Raster-/TF-
   Unsicherheit gewinnen. Vorhandene erste Körperplatzierung bleibt eine
   einmalige private Ausnahme; äußere Zellen benötigen Messungen.
2. **Konstruktiver Kandidat:** Zusätzliche niedrige rückwärtige/seitliche
   Nahbereichssicht oder nachweislich geeignete veränderte Sensorposition.
   Vorhandene Front-/Not-Haltabdeckung muss vollständig erhalten bleiben.
   Eine konkrete Montagehöhe, Sensorzahl oder Reichweite ist ohne Prüfung von
   Eigenabschattung, Sichtfeld und Boden-/Hinderniserkennung nicht freigegeben.
3. **Softwareeinbindung:** Reale Messung mit gültigem Frame, Kalibrierung,
   Quellenalter und beobachtetem Freiraum in die bestehende Kartenkette binden.
   Kein paralleler Navigator, keine künstliche Costmap-Freiraumblase, keine
   Oracle-/Referenzkarte als Produkteingang.
4. **Vorprüfung:** Auf den erhaltenen A227-Zellen nachweisen, welche davon die
   vorgesehene endliche Sicht tatsächlich erfasst. Nicht erfasste Zellen bleiben
   unbekannt. Blindzone, dünnes Hindernis, belegter Rand, stale Messung und
   verschobene Referenz müssen weiterhin sperren.
5. **Abnahme:** Dieselbe vollständige Kontur-/Trackingprüfung muss vor Bewegung
   bestehen. Danach neue deklarierte Sensorvariante mit A/B/C, Cancel und
   Gyro-HOLD vollständig prüfen. Ergebnisse nicht mit dem ursprünglichen
   Manifest vermischen oder als dessen unveränderte 3/3 ausgeben.

Dieses Paket ist eine konkrete Anforderung samt Gegenfall und Abnahmeweg,
**keine bereits implementierte oder qualifizierte Sensoränderung**. Die
ursprüngliche AP-06-Gesamtabnahme bleibt offen. Alle davon unabhängigen
Softwarekorrekturen, Regressionen und Quell-/Installationsnachweise bleiben
im aktuellen Kandidaten erhalten.

## Nachweise

- [A236–B242](evidence/ap06-missions-20261005/README_B236_B242.md)
- [Originalfehler und verifizierte Trace-Identitäten](evidence/ap06-missions-20261005/b243-original-failure-summary.json)
- [Konkrete fehlende Zellen und kontrollierter Gegenfall](evidence/ap06-missions-20261005/a244-start-coverage.json)
- [Reproduzierbare lesende Prüfung](evidence/ap06-missions-20261005/a244_start_coverage.py)
