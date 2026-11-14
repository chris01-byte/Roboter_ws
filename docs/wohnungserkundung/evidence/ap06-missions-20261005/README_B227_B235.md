# AP-06: Exakte native Arithmetik für private Trajektorien

A227 erfasst den tatsächlich gescheiterten initialen Auswahlzustand von A:
Originalkarten, Scan, feste Roh-/Kosteninventare, Referenz, physische Messung und
ursprüngliche leere Versuchshistorie. Kein zurückgesetzter späterer Zustand.
A228 reproduziert am Stand `60e23a8` den 5-s-Abbruch nach **5,186 s**.

`a2180ed` ergänzt eine optionale reine C-Abstandsberechnung im bestehenden
eigenen Arithmetic-Modul. Punkt-/Segment-Reihenfolge und IEEE-Rechenoperationen
entsprechen NumPy; keine FMA/fast-math. Unterstützte Eingaben sind private
zusammenhängende Kopien; neue unveränderliche Ergebnisbuffer. Unpassende
Datentypen, degenerierte Geometrie, ungültige Buffer oder fehlendes Modul
verwenden den vollständigen bisherigen NumPy-Pfad. Quellenalter, Inventare,
Belegung, Scope, Konturreserven und Missionspolitik liegen weiter beim Elterncode.

V43: zwölf Pakete gebaut (**7,07 s**), **2337 direkte Tests** (**140,48 s**),
**2319 registrierte Tests**, null Fehler/Failures/Skips. 24 neue Fälle prüfen
exakte Gleichheit gedrehter Rechtecke, Berührungen, große/kleine Koordinaten,
Fallback und ungültige Buffer. Die echten B201-Trajektorien prüfen jetzt auch
native Distanzrechnung gegen den vollständigen NumPy-Referenzpfad samt
Sperr-/Fortschrittshistorie und Wiedereintritt. Bindung: 490 Quelldateien,
137 bytegleiche Installdateien, neun native Artefakte. V43-native Bewegungsfälle
und die vorbereitete Whole-Matrix wurden **nicht gestartet**, da der Offline-
Gegenfall noch nicht gelöst war.

A229: Distanzrechnung allein reicht nicht. Derselbe Originaleingang endet nach
**5,078 s** am unveränderten Budget. Es werden mehr Trajektorien geprüft;
Clipping ist danach der größte Aufwand. Kein behaupteter Gesamtfix.

Die zweite Korrektur überträgt ausschließlich Sutherland-Hodgman-Clipping in
den eigenen Kern. Identische vier Halbräume, Kanten-/Ausgabereihenfolge,
Nullflächen-Kontaktpunkte und originale NumPy-Flächensummation bleiben erhalten.
Der vollständige NumPy-Oracle bleibt separat verfügbar. 23 zusätzliche Fälle;
**75 gezielte Tests grün**, einschließlich der Originaltrajektorien.

A235: exakt derselbe A227-Eingang findet nun den vollständig geprüften begrenzten
Startbeobachtungskandidaten `(0.3, 0, 0)` in **4,195 s**. Keine Friständerung,
keine geringere Such-/Konturreserve, keine künstliche Quellenfrische. Das ist
ein kausaler Softwaregegenfall, noch keine Gesamtmission. V44-Gesamtprüfung und
anschließende Originalmatrix folgen separat.

Die ausführbaren internen Diagnosepickles und Profile bleiben lokal außerhalb
Git; die Skripte lesen ausschließlich selbst aufgezeichnete synthetische Daten.
Die in Git befindlichen Regressionseingaben verwenden JSON/NPZ ohne Pickle.
Originalmatrix-/Masterplan- und externe Native-Plugin-Hashes sind unverändert;
**der eigene native Arithmetic-Kern hat durch diese Änderung einen neuen Hash**,
der für den finalen Kandidaten erneut gebunden wird.

## V44 Originalmatrix, abgeschlossen

Kandidat `3c66cbe`: zwölf Pakete gebaut (6,68 s), **2360 direkte Tests**
(138,49 s), **2342 registrierte Tests**, null Fehler/Failures/Skips.
**9/9 native Fälle**, **Cancel233 und Gyro-HOLD234 bestanden**.
A230 bleibt im Live-Stack am initialen Auswahlbudget negativ (keine Bewegung).
B231: eine Ankunft/Beobachtung, drei Versuche/ein Fehler, 0,3092 m, dann
Auswahlbudget. C232 überwindet den Startabbruch und erreicht eine Ankunft/
Beobachtung, scheitert später ebenfalls am Auswahlbudget (sechs Versuche/ein
Fehler). Somit weiterhin **0/3 Gesamtmissionen**. Keine HWT-Gesamtfehler in
A/B/C dieser Serie; keine Aufweichung der ursprünglichen Kontinuitätssperre.

Die vorbereitete Matrix mit Nummern 230–234 wurde tatsächlich erst am
kombinierten V44-Kandidaten ausgeführt, nicht am V43-Zwischenstand. Nummern
sind Evidenznamen, keine Versions-/Zeitreihenbehauptung.
