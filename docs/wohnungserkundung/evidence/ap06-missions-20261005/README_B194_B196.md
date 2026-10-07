# AP-06: Frische Bindung und konservative Restarbeit, 07.10.2026

Produktbasis `7fabf80`, Korrektur `4497d0c`. Originales Szenariomanifest,
MASTERPLAN v1.3, Controller, Budgets und Sperren unverändert.
Kein Hardwarezugriff. Gesamtstand bleibt bis zur vollständigen Matrix 0/3.

## Tatsächliche Diagnose B194

Der instrumentierte Produktlauf zeichnet die bereits vorliegende echte
Encoderprobe am Ende der unveränderten Eingabeprüfung auf. Er ist ausdrücklich
kein Abnahmelauf. Zwei tatsächliche Entscheidungen unterscheiden die Fälle:

- Alte Probe ca. 247,7 ms, neuere Probe ca. 6,6 ms, aber 21,6 mm von der
  gebundenen TF-Pose entfernt: Die unveränderte 20-mm-Grenze verbietet Neubindung.
- Alte Probe ca. 195,3 ms, neuere Probe ca. 15,6 ms, Positionsunterschied etwa
  0,067 mm: Die alte Implementierung verwirft trotz nutzbarer echter Messung.

Die Korrektur bindet höchstens einmal eine tatsächlich neuere Quellenprobe und
berechnet den vollständigen Egress-/Bewegungsverlauf erneut. Quellstempel müssen
strikt steigen; Empfangszeiten dürfen nicht zurückgehen. Originale Frame-,
TF-, Quellen- und finale Verarbeitungsfristen bleiben wirksam. Ein abgelaufenes
zweites Ergebnis wird weiterhin verworfen; kein Polling oder Inventarreset.
Acht neue Fälle: Originalcode **2 rot/6 grün**; korrigierter gezielter Lauf
zusammen mit betroffenen Nachbarfällen **93 grün**.

B194 endet natürlich nach 0,1632 m an `completion_raw_pose_not_observed_free`.
Ein vorbereiteter Diagnose-Cancel wurde nicht ausgeführt. Der echte Controller
hat den ersten Zielpunkt x=0,3 innerhalb seiner originalen 0,15-m-Toleranz
bereits bei x≈0,163 erreicht. Das ungeklärte Rohkartenfeld am Basiszentrum
beendet die lokale Restarbeitsbewertung, obwohl diese keine Fahrfreigabe ist.

## Offene Arbeit bewahren

`local_small_remainder` liefert bei unbeweisbarer Rohkartenkonnektivität `None`
statt den Elternauftrag mit einer Abschlussausnahme abzubrechen. Der Elterncode
behält die Aufgabe dann explizit als `partially_observed`. Tatsächlicher
Beobachtungsgewinn, ursprüngliche Versuche, Fehler und Historie bleiben erhalten.
Die globale `reachable_remainder`-Abschlussprüfung bleibt unverändert streng.
Unbekannte/belegte/außerhalb liegende Roboterzentren erlauben keinen Abschluss.

Ein Elternfall mit vorgeschobenem Sensor und unbekanntem Basiszentrum prüft die
wirkliche Fortschrittsentscheidung nach einer Beobachtung. Drei negative
Konnektivitätsfälle prüfen zugleich das fortbestehende Abschlussverbot.
Gezielte Prüfung Frische/Restarbeit/Elternablauf: **86 bestanden**, 7,82 s.

## Verbundene Qualifikation

V39 Zwölfpaketbuild **7,02 s**, **2254 direkte Tests** in 151,62 s und
**2236 registrierte Tests**, null Fehler/Failures/Skips. **9/9 native Komponenten
bestanden**. Regulärer B196: eine tatsächliche Ankunft und eine qualifizierte
Beobachtung, 0,1565 m; nächste Auswahl scheitert an unverändertem
`frontier_candidate_processing_budget_exhausted`. Gesamtfall negativ.
Keine parallelen Builds, Tests oder Profiler während der Bewegung. B195 bindet 480 Quelldateien,
137 bytegleiche installierte Produktdateien und neun native Artefakte an
`4497d0c9139481d644715ee613d127fb1db90e23`.
