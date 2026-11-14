# AP-06: Konnektivitätsaufwand und ursprüngliche Abfragelimits

Produktkorrektur `972ef6c`, Basis `8e6cbbe`. B208 liest die vollständige originale
B207-Ereignisfolge mit SHA-/Längenabgleich und den tatsächlich gespeicherten
Checkpoint. Der nachfolgende Fall ist ausdrücklich **terminale öffentliche
Geometrie mit ursprünglicher Historie**, keine exakte frühere Live-Entscheidung
und keine nachträgliche Fahrfreigabe. Kein neuer Gesundheitsnachweis.

B208-Profil scheitert nach **5,110 s** am ursprünglichen Auswahlbudget. Die alte
Python-Vier-Nachbar-Suche kostet 1,437 s in 22 Aufrufen; weitere Zeit verbrauchen
wiederholte skalare Zelltransformationen und eine anschließend überschriebene
Freiraumberechnung. Die neue SciPy-Komponentenmarkierung erhält exakt dieselbe
Vier-Nachbar-Topologie. Vektorisierte Transformationen erhalten Skalar-hypot und
die originale lexikographische Zielreihenfolge. Vorhandene explizite Suchmasken
brauchen keine unbenutzte zusätzliche Erosion.

B209 findet nach **4,252 s** einen Nav2-Prüfvorschlag. Das Profil zeigt weitere
Abfragen trotz noch wirksamer Cooldowns/erschöpfter Nachbarschaftslimits.
`within_limits` ist nun eine geteilte notwendige Bedingung der ursprünglichen
Policy und der Seitenbeobachtungs-Vorprüfung. Sie erlaubt keine Fahrt oder Sicht,
sondern vermeidet nur Abfragen, die auch mit gültiger Sicht verboten blieben.
Evidenz-, Sicht-, Fremdnachbarschafts-, Quellen- und gesamte Bewegungsprüfung
bleiben später vollständig wirksam. Kein Reset von IDs, Versuchen oder Cooldown.

B211: derselbe Vorschlag `(2,734999938867986; -0,42499999050050974; 0)` nach
**2,657 s**. B209/B211 binden explizit denselben gebauten nativen Arithmetikkern;
keine NumPy-Rückfallvariante im Vergleich. Die ursprüngliche Aufgabe 7 bleibt
bei drei Versuchen gesperrt; neue Geometrieabfrage ist kein Missionsreceipt.

24 zusätzliche Tests vergleichen Topologie einschließlich Diagonalkontakt und
nicht zusammenhängender Speicheransicht, exakte Zielreihenfolge bei gedrehtem
Raster, den tatsächlichen B207-Endzustand und die Sperre/Freigabe einer rein
lesenden Abfrage vor/nach dem ursprünglichen Cooldown. **336 betroffene Tests
bestanden**, davor 238 Nachbarfälle. Die kleinen synthetischen Fixturedateien
enthalten CDR/Arrays und JSON, keinen ausführbaren Pickle.

V41 Zwölfpaketbuild **7,33 s**, **2306 direkte Tests** in 150,50 s,
**2288 registrierte Tests**, null Fehler/Failures/Skips. **9/9 native Fälle**.
Regulärer B214 bleibt negativ: zwei Ankünfte/zwei Beobachtungen, 0,9411 m,
60,69 % Referenzboden, kein Rundblick/keine Passage; erneut
`frontier_candidate_processing_budget_exhausted`. Der nachfolgende Nachweis
untersucht den tatsächlichen Entscheidungseingang statt nur den Endzustand. Quellenbindung: 486 Dateien, 137 bytegleiche installierte
Produktdateien und neun native Artefakte. Originalmanifest/Masterplan unverändert.
Gesamtstatus bleibt bis zum tatsächlichen vollständigen Positivnachweis 0/3.
