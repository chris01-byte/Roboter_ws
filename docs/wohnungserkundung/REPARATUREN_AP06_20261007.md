# AP-06: umgesetzte Reparaturen und verbliebene Abnahmeblocker

**Keine Gesamtabnahme: weiterhin keine belegte 3/3-Serie.** Neun lokale
Reparaturcommits auf `feature/ap06-closed-product-validation`, Produktstand
`2e5e1fd`. MASTERPLAN v1.3, ursprüngliches Szenariomanifest, Schutzgrenzen,
Versuchs-/Zeitbudgets und externe Nav2-/SLAM-Pins erhalten. Keine Hardwarefahrt,
kein Deployment, kein Push/Merge und kein nächstes AP.

## Konkrete Änderungen

| Commit | Reparatur und Nachweis |
|---|---|
| `7fabf80` | Exakte Referenz-/Zellgeometrie gebündelt; identische Eingaben von 186–192 auf 50–51 ms |
| `4497d0c` | Höchstens einmal tatsächlich neuere TF-konsistente Wheelprobe vollständig neu beweisen; unbewiesene lokale Restarbeit offen halten |
| `8e6cbbe` | Strikt disjunkte Zellclips auslassen, identische lokale Evidenzprojektion bündeln |
| `972ef6c` | Gleiche Vier-Nachbar-Konnektivität und Zielreihenfolge schneller berechnen; bestehende Limits vor teuren Seitenabfragen prüfen |
| `60e23a8` | Nach wirklicher Beobachtung bereits vollständig öffentlich bewiesenen ausstehenden Rundblick vor weiteren Zielen ausführen |
| `a2180ed` | Exakte Zellabstände im optionalen eigenen nativen Rechenkern; vollständiger NumPy-Oracle bleibt |
| `3c66cbe` | Exaktes Clipping im selben Kern; Kontaktpunkte und ursprüngliche NumPy-Flächensummation erhalten |
| `5612878` | Vorhandenen bewiesenen kurzen privaten Startschritt vor Fernabfragen suchen; tatsächlicher A227-Gegenfall >5 s → 0,964 s bei gleichem Ziel/Task |
| `2e5e1fd` | Vorübergehende Encoder-/TF-Abweichung ausschließlich nach terminalem Child und Stillstand im bestehenden begrenzten Rahmen neu prüfen; tatsächlich abgelehnte Eingaben protokollieren |

Der eigene C-Kern ist reine Arithmetik ohne ROS-/Quellen-/Bewegungsautorität.
Auf einem anderen Zielsystem muss er neu gebaut werden. Unsupported/fehlender
Kern behält den bisherigen vollständigen NumPy-Pfad; keine pauschale
Performancezusage für den Jetson.

## Softwareprüfung

V46: zwölf Pakete gebaut, **2371 direkte Tests**, **2353 registrierte Tests**,
null Fehler/Failures/Skips. Die Testmengen überlappen und werden nicht addiert.
**9/9 native Komponentenfälle** am aktuellen Kandidaten bestanden.
494 Quelldateien gebunden, 137 ausgeführte Installdateien bytegleich; acht
externe native Artefakte und eigener Arithmetic-Kern gehasht.

Neue Fälle prüfen unter anderem reale gespeicherte Geometrie-/Inventare,
Kontakt-/Teilzellen, Rückkehr in verlassenen unbekannten Bereich, Quellenalter,
TF-Abweichung, unveränderte Task-/Nachbarhistorie, Cancel, Deadline und
erschöpfte Neuprüfung. Kausale Rot/Grün-Nachweise sowie negative Zwischenstände
sind erhalten, keine allein selbstbestätigende Konfigurationsprüfung.

## Was die vollständigen Läufe tatsächlich zeigen

Die letzte vollständige Originalmatrix V45 ergibt **0/3 A/B/C**;
Cancel241 und Gyro-HOLD242 bestehen. A238 überwindet den Auswahlabbruch, sperrt
aber eine kleine reale Kurve im festen unbekannten Anfangsbereich. B239 sperrt
neu unbekannte Fläche beim Referenzwechsel. C240 erreicht drei Ankünfte und
Beobachtungen sowie 4,394 m, endet jedoch an einer echten 213-ms-Encoderlücke.
Drei Beobachtungen sind keine positive Gesamtmission.

C245 mit zur Vier-CPU-Quote passender Zuteilung zeigt keine Drosselung, aber
Encoder-/TF-Abweichung. Daraus entstand die begrenzte Pose-Neuprüfung.
Die zusätzliche V46-Serie C248/Cancel249/Gyro250 ist separat zu bewerten und
ersetzt keine vollständige Originalmatrix auf demselben finalen Stand.
Ihr Endergebnis steht im aktuellen [STATUS](STATUS.md).

## Konkrete Grenze und vorbereitete Weiterarbeit

Auf dem erhaltenen A227-Start fehlen für das unveränderte vollständige
Trackingband **138 äußere unbekannte Rohzellen**. Nominal gerade Vorfahrt
besteht, die tatsächlich gemessene kleine Kurve verletzt denselben festen
Anfangsnachweis. Eine neue freie Fläche, größeres Inventar oder kleinere
Reserve wäre keine zulässige Lösung.

Das [separate Startbeobachtungs-/Abdeckungspaket](AP06_STARTBEOBACHTUNG_BLOCKER.md)
benennt die benötigten Zellen, konstruktive Sensoranforderungen und die neue
Abnahme. Es setzt die ausdrückliche MASTERPLAN-AP-03-Regel um, bei fehlender
notwendiger Sicht eine begründete Abdeckungsänderung vorzubereiten statt
identische Fehlstarts zu wiederholen. Keine Sensormontage ist damit ausgeführt
oder freigegeben; nicht alle denkbaren alternativen Beobachtungsbewegungen
wurden mathematisch ausgeschlossen.

Der lange Base-Executor-Aufruf und die HWT-Lücke sind separat offen; die letzte
Poseabweichung wird nun am tatsächlichen Ablehnungspaar dokumentiert.
Keine erfundenen Zeitstempel und keine verlängerte 180-ms-Quellgrenze.

## Reproduzierbare Belege

- [Referenzgeometrie und Quellenbindung](evidence/ap06-missions-20261005/README_B185_B193.md)
- [Frische und lokale Restarbeit](evidence/ap06-missions-20261005/README_B194_B196.md)
- [Auswahlgeometrie](evidence/ap06-missions-20261005/README_B197_B207.md)
- [Konnektivität und bestehende Limits](evidence/ap06-missions-20261005/README_B208_B214.md)
- [Ausstehender öffentlicher Rundblick](evidence/ap06-missions-20261005/README_B215_B225.md)
- [Native exakte Arithmetik und V44-Matrix](evidence/ap06-missions-20261005/README_B227_B235.md)
- [Nahpriorität und V45-Matrix](evidence/ap06-missions-20261005/README_B236_B242.md)
- [Begrenzte Pose-Neuprüfung und V46](evidence/ap06-missions-20261005/README_C246_C250.md)

Rückfall: ausschließlich eigene neue Reparaturcommits gezielt revertieren;
vorherige AP-Korrekturen, Karten, Checkpoints und Negativevidenz erhalten.
Keine gesamthafte Rücksetzung des Branches oder der Nutzerdokumentation.
