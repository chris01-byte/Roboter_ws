# Projektgedächtnis

Fortlaufendes Protokoll getroffener Entscheidungen. Jeder Eintrag nennt die
**beobachtete Evidenz**, nicht nur die Entscheidung. Neue Einträge oben anfügen.

Format:

```text
Datum:
Entscheidung:
Grund / beobachtete Evidenz:
Betroffene Dateien und Hardware:
Teststatus:
Offene Risiken:
Rückfallweg:
```

---

## 2026-08-10 — Import in ein privates GitHub-Repository

**Entscheidung:** Der getestete Jetson-Stand wird nach
`github.com/chris01-byte/Roboter_ws` (privat) übertragen; `ios/` und
`integration/` werden vom USB-Stick ergänzt.

**Grund / Evidenz:** Jetson und Stick waren divergent — der Jetson trug 27
Commits mit der getesteten Robotersoftware, der Stick 4 Commits mit der iOS-App
und den Transferwerkzeugen. `git merge-base --is-ancestor` bestätigte, dass
keiner den anderen enthält. Vor dem Push geprüft: keine Treffer auf Schlüssel-,
Token- oder Passwortmuster; größte Datei 836 KB; keine Provisioning-Profile.
`testwohnung.pgm` ist synthetisch (240×200 Zellen, **null** unbekannte
Bereiche) und damit unbedenklich — eine echte SLAM-Karte hat immer unbekannte
Zonen.

**Betroffen:** gesamtes Repository, `.gitignore`

**Teststatus:** Push erfolgreich, Inhalt auf GitHub gegengeprüft (privat, keine
Token-Funde).

**Offene Risiken:** Ein leeres Repository `amadeus-robot-ws` ist bei der
Einrichtung entstanden und konnte nicht automatisch entfernt werden.

**Rückfallweg:** Repository ist privat und kann gelöscht werden; der lokale
Stand auf dem Jetson bleibt unabhängig davon bestehen.

---

## 2026-07-28 — Anfahrverhalten geglättet (Commit `f3a9094`)

**Entscheidung:** `base_hardware` schreibt Startdrehzahl und Rampen bei jedem
Verbindungsaufbau: `0x0020` = 5 rpm, `0x001E` = 800 ms, `0x001F` = 400 ms.

**Grund / Evidenz:** Der Roboter nickte beim Anfahren sichtbar. Bei einer Kamera
auf 1,34 m verschieben schon 2° Nicken den gemessenen Boden auf 3 m Entfernung
um rund 10 cm — Boden wird dann als Wand kartiert. Auslesen der Register ergab
**Startdrehzahl 30 rpm**, ein Rest aus dem Richtungstest vom 24.07., der
persistent im Motor gespeichert war. Bei Fahrdrehzahlen um 46 rpm setzte der
Antrieb damit sofort mit 65 % der Zielgeschwindigkeit ein. Messung bestätigte:
Solldrehzahl nach ~110 ms zu 90 % erreicht, **trotz** 800-ms-Rampe — die Rampe
war nie das Problem.

**Betroffen:** `base_hardware_node.py`, `base_hardware_params.yaml`; beide
Motoren.

**Teststatus:** Vom Nutzer am Gerät bestätigt („alles passt"). Bremswert von 250
auf 400 ms nachjustiert, weil 250 ms zu ruppig und 800 ms zu weich war
(Nachlaufen).

**Offene Risiken:** 5 rpm Startdrehzahl könnte bei höherer Last zu wenig
Anlaufmoment bieten. Register `0x0021` steht auf 100, Bedeutung unbekannt.

**Rückfallweg:** Werte in `base_hardware_params.yaml` zurücksetzen; der Antrieb
läuft mit jedem Wert, nur weniger sanft.

---

## 2026-07-28 — Lokalisierung ohne Vorwissen nachgewiesen (Commit `e136871`)

**Entscheidung:** Neues Launch-Argument `start_at_origin` und der Test
`lokalisierung_kidnapped.py` als verbindliches Prüfverfahren.

**Grund / Evidenz:** Zwei naheliegende Prüfungen beweisen **nichts**:
(1) „`map→odom` ist nicht die Identität" — RTAB-Map lädt beim Start die zuletzt
gespeicherte Pose, der Roboter steht dann sofort „richtig" da.
(2) „`/localization_pose` wird publiziert" — im Lokalisierungsmodus kommen
Meldungen in **jedem** Verarbeitungstakt (71 Stück bei ~120 s und 1 Hz),
unabhängig vom Erfolg. Belastbar ist nur: ohne Vorwissen starten **und** von
mehreren Standorten prüfen, ob der gemeldete Positionsunterschied dem echten
entspricht.

**Betroffen:** `slam.launch.py`, `tools/kartierung/`

**Teststatus:** Zwei Läufe: 1,25 m ermittelter Abstand gegen 1,4 m von Hand
gemessen (11 % Abweichung). Gegenprobe mit einer schlechteren Karte fiel
korrekt durch (0,000 m Versatz).

**Offene Risiken:** Geometrische Genauigkeit nur handgemessen.

**Rückfallweg:** `start_at_origin:=false` stellt das alte Verhalten her.

---

## 2026-07-28 — Wörterbuch-Verlust: Ursache korrigiert (Commit `390fcec`)

**Entscheidung:** SIGINT geht **nur an den ros2-launch-Prozess**, nie an die
Prozessgruppe; beim Start `sigterm_timeout:=120 sigkill_timeout:=180`.

**Grund / Evidenz:** Die bisherige Projekterklärung lautete, nur `kill -9`
zerstöre das visuelle Wörterbuch. Gemessen: Auch ein SIGINT an die
**Prozessgruppe** tut es — rtabmap bekommt das Signal doppelt (direkt vom Kernel
und weitergereicht von launch), das zweite bricht das Speichern ab. Ergebnis
war eine Datenbank mit 831 Knoten und **0 Wörtern**, rtabmap starb mit
`exit code -2`. Zusätzlich eskaliert launch nach 5 s selbsttätig auf
SIGTERM/SIGKILL, was für große Karten zu knapp ist.

**Betroffen:** `slam.launch.py` (Dokumentation), `tools/kartierung/stop_slam.sh`

**Teststatus:** Mehrfach bestätigt — seither wird das Wörterbuch zuverlässig
geschrieben (bis 271.805 Wörter).

**Rückfallweg:** Entfällt; ohne den Fix ist die Karte unbrauchbar.

---

## 2026-07-28 — RS485-Selbstheilung repariert (Commit `390fcec`)

**Entscheidung:** Der alte Modbus-Client wird vor einem Neuaufbau geschlossen.

**Grund / Evidenz:** Ein einziger Timeout im Startgewitter (OAK, VL53, RTAB-Map
am USB-Bus) legte die Motoren dauerhaft still. Die Selbstheilung legte einen
neuen Client an, ohne den alten zu schließen; dessen exklusives Port-Lock ließ
jeden weiteren Versuch an `[Errno 11] Could not exclusively lock port`
scheitern.

**Betroffen:** `base_hardware_node.py`; RS485-Bus

**Teststatus:** 0 RS485-Fehler über alle folgenden Fahrten.

**Rückfallweg:** Vorheriger Commit; dann ist ein Neustart des Knotens nach
jedem Timeout nötig.

---

## Grundsätzliches (übernommen aus früheren Sitzungen)

- Amadeus nutzt eine **OAK-D-S2** auf hohem Mast; ein Wechsel auf OAK 4 D Pro
  Wide FF ist vorgesehen. Der Treiber erkennt das Modell selbst.
- Für robuste 2D-Navigation ist ein **separater 2D-Lidar** vorgesehen. Kamera
  und Lidar haben unterschiedliche Aufgaben: die Kamera liefert visuelle
  Lokalisierung und Semantik, der Lidar die horizontale Navigationskarte.
- **Maststeifigkeit, Sensor-Frames und Odometrie** sind für die Kartenqualität
  genauso wichtig wie der Sensor selbst — belegt durch den Nick-Befund oben.
- **Spiegel und Glas** erzeugen optische Ausreißer und werden softwareseitig
  gefiltert, nicht als reale Wände interpretiert. Offener Punkt: Die
  Strahlartefakte vom 28.07. (74,6 % der scheinbaren Freifläche) sind
  vermutlich darauf zurückzuführen; `tools/kartierung/karte_bereinigen.py`
  entfernt die Folge, die Ursache ist ungeklärt.
- Die **VL53-Sensoren decken flache Bodenobjekte nicht ab**: Sie sitzen auf
  0,305 m und schauen waagerecht; ihr Kegel trifft den Boden erst bei ~0,53 m,
  jenseits ihrer Reichweite. Kabel und Schwellen sieht kein Sensor.
