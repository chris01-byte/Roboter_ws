# AP-06: Ausstehende Beobachtung vor neuer Zielsuche

Basis `972ef6c`, Korrektur `60e23a8`. B215 verifiziert **43.508.246** originale
B214-Ereignisbytes und den gesicherten Checkpoint. Die gespeicherte Endkarte
besitzt bereits eine zulässige vollständige Drehfläche; ein isolierter neuer
Entscheidungslauf wählt den Rundblick in 0,569 s. Das reproduziert ausdrücklich
nicht den früheren Live-Zeitverbrauch.

B216 zeichnet deshalb den tatsächlichen Auswahl-Eintritt nach zwei Ankünften
und zwei Beobachtungen auf, einschließlich gesperrter privater Inventare und
Originalhistorie. Der Diagnosefall endet natürlich nach **5,100 s** am
Auswahlbudget. Keine externe Cancel-Injektion. Im isolierten B217-Replay derselben
Eingaben erreicht die ursprüngliche Software nach **0,528 s** bereits den
belegten Cooldown-Wartefall. Der zeitbegrenzte Hilfssuchpfad nimmt unter Last
somit einen anderen Folgezweig. Kein behaupteter deterministischer 5-s-Replay
und keine Entfernung der Inventare als nachträgliche Freigabe.

Die vorhandene adaptive Startentscheidung berechnet immer zuerst neue Fahrziele,
bevor sie einen noch ausstehenden Rundblick wählen kann. Nach tatsächlich
gewonnener Startbeobachtung kann ein bereits sicher möglicher Rundblick so
hinter einer teuren weiteren Zielsuche verhungern. `60e23a8` priorisiert deshalb
die noch ausstehende einmalige Beobachtung nach gemessenem Fortschritt, wenn
vollständig **öffentlich** beobachtete Roh-/Kostenkarten die gesamte Drehung
beweisen und rohe, zusammenhängend erreichbare Restgrenzen vorliegen.

Anfang ohne Beobachtung, unsichere Drehfläche, virtuelle Eigenkörperfreiheit,
fehlende Restarbeit und bereits erledigter Scan erhalten keine neue Priorität.
Es werden keine Quellenfrische behauptet, Zellen freigegeben, Fristen verlängert,
Versuche/IDs zurückgesetzt oder Beobachtungszähler erhöht. Bestehender Elterncode
prüft weiterhin jede tatsächliche Drehung, HOLD/Cancel, Stillstand und die
verbleibende ursprüngliche Scan-/Missionszeit. Kein zweiter Scanbesitzer.

Sieben neue Fälle verwenden den tatsächlichen B216-Entscheidungseingang.
Originalcode **1 rot/6 grün**, korrigiert mit Nachbarn **168 grün**.
NPZ/JSON speichern synthetische Geometrie, volle Inventare und ursprüngliche
Historie, keinen ausführbaren Pickle. Der positive Fall verbietet eine neue
Zielsuche vor dem bereits bewiesenen Rundblick und prüft unveränderte Karten,
Ledger-Identität und Aufgabenhistorie.

V42-Softwareprüfung, native Fälle, B221, A222, C223, Cancel224 und Gyro225 sind
am gleichen Produktstand vorgesehen. Bindung: **489 Quellen, 137 bytegleiche
Installdateien, neun native Artefakte**; Originalmanifest/Masterplan unverändert.
Noch keine 3/3-Behauptung. Endergebnisse werden unten ergänzt.

## Tatsächlicher Abschluss dieser Serie

V42: zwölf Pakete gebaut, **2313 direkte / 2295 registrierte Tests**, null
Fehler/Failures/Skips; **9/9 native Komponenten**. Alle folgenden Originalfälle
liefen sequenziell am Produktstand `60e23a8`:

| Fall | Ergebnis |
|---|---|
| B221 | Negativ: 3 Ankünfte/3 Beobachtungen, vollständiger Rundblick, 1,4067 m, 74,46 % Boden; tatsächlicher HWT-Terminalfehler |
| A222 | Negativ: initiales Auswahlbudget, keine Bewegung |
| C223 | Negativ: initiales Auswahlbudget, keine Bewegung |
| Cancel224 | Bestanden: tatsächliche Bewegung, originaler Cancel und terminaler Abschluss |
| Gyro225 | Negativ: HWT bereits beim Start nicht bereit, keine Gyro-Injektion |

B226 liest die ursprünglichen Ereignisse: B221 hat eine echte Encoderlücke von
197,336 ms, Gyro225 eine von 329,504 ms; zulässig bleiben 180 ms. Die
Paarlesedauer beträgt nur 0,501 bzw. 0,162 ms. B221 zeigt gleichzeitig eine
~160-ms-Quellprozesspause bei ~6 ms Prozess-CPU. Das ist keine abgelaufene
lokale Bindung, die durch eine neue Probe behoben werden dürfte. Die
Kontinuitätssperre bleibt wirksam. Ursache der Scheduling-Pause noch nicht
abschließend belegt; keine Behauptung einer nachgewiesenen CPU-Drosselung.

A227 zeichnet den ursprünglichen initialen Entscheidungseingang auf und
überwacht den übergeordneten Cgroup-Zähler: null neue Drosselereignisse im
Lauf. Trotzdem identischer Auswahlabbruch. A228 reproduziert auf genau diesen
Eingaben **5,186 s**. Hauptkosten: private Trajektorienprüfung, davon 1,705 s
Zellabstände und 1,424 s Zellclipping. Diese Diagnose begründet die nächste
reine Arithmetikoptimierung, keine Verlängerung der Auswahlfrist.

Der erste Matrix-Launcher mit `set -u` scheiterte am ROS-Setup vor jedem
zusätzlichen Szenario. Nach Korrektur auf `set -o pipefail` wurden A222 bis
Gyro225 regulär ausgeführt. Beigefügt ist der tatsächlich benutzte korrigierte
Launcher. **Gesamtabnahme weiterhin 0/3.**
