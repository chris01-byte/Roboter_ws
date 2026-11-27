# AP-06: Bereits bewiesene Nahbeobachtung vor Fernabfragen

A230 zeigt, dass der isolierte 4,195-s-Arithmetikgewinn im laufenden Stack
noch keine ausreichende Reserve bietet. Der ursprüngliche kurze private
Beobachtungsschritt wurde erst NACH ferneren Kandidaten und öffentlichen
Hilfssuchen bearbeitet. Diese konsumieren das Budget, obwohl derselbe
Startschritt bereits vollständig beweisbar ist.

`5612878` zieht ausschließlich den vorhandenen kurzen Vorwärtssuchblock vor
diese unabhängigen Fernabfragen. Die bisher bevorzugte größere private
Beobachtung bleibt zuerst; erst wenn sie keinen Kandidaten liefert, folgt
jetzt die kurze Suche. Suchentfernungen, Fristen, Originalinventar, Geometrie,
aktuelle endliche Sicht und spätere tatsächliche Nav2-Planprüfung bleiben
unverändert. Der vorgezogene Block prüft zudem ausdrücklich die vorhandene
Task-/Nachbarhistorie, einschließlich Cooldown und ausgeschöpfter Versuche.
Kein Zurücksetzen, keine neue private Fläche, keine gefälschte Beobachtung.

A236 exportiert den A227-Originaleingang als sichere JSON/NPZ-Regression.
Originalsoftware rot vor jeder Nahentscheidung an der Fernabfrage;
korrigierter Produktcode wählt dieselbe Aufgabe `metric-task-7` und dasselbe
Ziel `(0.3,0,0)` in **0,964 s** (A237, ursprüngliche 5-s-Grenze).
**30 betroffene Tests grün**: positiver tatsächlicher Eingang samt Inventar-
und Kartenprüfung sowie Route/Sicht/Cooldown/Versuchskappen-Gegenfälle.

Transparente Zwischenprüfungen bleiben erhalten: der erste Korrekturlauf
importierte noch die alte Installation und blieb erwartungsgemäß rot.
Nach Neubuild war die Verhaltensprüfung grün, aber eine zu strenge zusätzliche
Testannahme zur internen Projektionsgeneration falsch: die vorhandene
Vorbereitung erhöht diese Generation regulär. Diese Annahme wurde durch
Prüfung der unveränderten ursprünglichen Referenz, Inventarflächen und
Historie ersetzt; keine Änderung dieses Produktverhaltens.

V45-Vollprüfung und ursprüngliche native/Whole-Matrix A238/B239/C240/
Cancel241/Gyro242 sind am gleichen Stand vorgesehen. Endergebnisse folgen.

## V45 abgeschlossen, ursprüngliche Gesamtabnahme weiterhin negativ

Kandidat `5612878`: zwölf Pakete gebaut, **2365 direkte Tests** (147,79 s),
**2347 registrierte Tests**, null Fehler/Failures/Skips; **9/9 native Fälle**.
Quellbindung: **494 Dateien, 137 bytegleiche Installdateien, neun native
Artefakte**. Eigener C-Kern wie V44; Masterplan/Originalmanifest/externe Pins
unverändert.

| Originalfall | Ergebnis |
|---|---|
| A238 | Startauswahl repariert, Fahrt begonnen; 0,02126 m, null Ankünfte/Beobachtungen, feste Anfangsfläche durch kleine reale Kurve verletzt |
| B239 | 0,15937 m, null Ankünfte/Beobachtungen; zuerst veraltete Bindung, dann neue unbekannte Fläche bei Referenzänderung gesperrt |
| C240 | Drei Ankünfte/drei Beobachtungen, sieben Versuche/kein Bewegungsfehler, 4,39397 m; echte Encoderlücke → HWT terminal |
| Cancel241 | Bestanden |
| Gyro-HOLD242 | Bestanden |

Alle fünf Fälle enden ohne aktive Explore-/Navigate-Actions und mit vier
Nullbefehlsketten. Keine hardwarequalifizierte Abnahme. **0/3 Gesamtmissionen**,
auch drei Beobachtungen in C240 sind keine positive Gesamtmission.

B243 verifiziert alle Original-Ereignisbytes dieser fünf Fälle gegen deren
beim Schreiben erfasste SHA-256/Bytezahl. Es bewahrt ursprüngliche Fehler,
HWT-Übergänge und tatsächliche A238-NavFn-Pläne. C240: Encoderlücke **213,245 ms**,
Paarlesung nur **0,137 ms**. Gleichzeitig 184,487 ms aggregierte Cgroup-
Drosselzeit im umgebenden Vier-Sekunden-Fenster. Der Base-Executor hat aber auch
**159 ms eigene Thread-CPU** innerhalb einer 185,571-ms-Ausführung; deshalb
nicht pauschal als reine Hostpause klassifizieren. Ein genauer Callstack dieses
langen Aufrufs ist bisher nicht aufgezeichnet. Frischegrenze bleibt 180 ms.

A244 beschreibt den fehlenden robusten Startnachweis anhand tatsächlicher
Geometrie, vollständig separat von neuen Hardware-/Sensorannahmen:
[vorbereitetes Abdeckungspaket](../../AP06_STARTBEOBACHTUNG_BLOCKER.md).

C245 ist eine zusätzliche Ausführungsdiagnose auf demselben Produktstand:
Vier CPUs statt fünf gleichzeitig möglicher CPUs bei gemessener Vier-CPU-Quote.
Null neue Drosselereignisse, aber nach 0,34825 m tatsächlichem Weg negative
Encoder-/TF-Übereinstimmungsprüfung (`start_motion_wheel_tf_disagreement`).
Keine Ankunft/Beobachtung, alle Actions terminal/vier Nullketten.
Kein Nachweis, dass CPU-Zuteilung die vollständige Quellkette repariert; dieser
Zusatzlauf ersetzt keinen Originalmatrixfall. Keine neue Runde identischer
A-Fehlstarts ohne konstruktiven Startnachweis.

Nächste unabhängige Softwarediagnose: Encoder- und TF-Pose samt tatsächlichen
Mess-/Empfangsstempeln am Disagreement sichern, identische Zeitbasis und
Filterverzug getrennt prüfen; Base-Executor bei >100 ms mit Funktionszeit oder
Callstack lokalisieren. Keine Synchronität durch neue Stempel behaupten und
keine Positions-/Frischegrenze erhöhen. Der Sensor-Abdeckungsvorschlag ist ein
separat vorbereitetes Paket gemäß MASTERPLAN AP-03, keine ausgeführte Änderung.
