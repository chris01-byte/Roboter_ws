# LAB-Erkundung in Beobachtungs- und Fahrabschnitten

Nutzerauftrag vom 11.10.2026; AP-06 unter [MASTERPLAN v1.5](MASTERPLAN.md).
Den tatsächlichen Prüf- und Installstand ausschließlich im [STATUS](STATUS.md)
nachlesen. Die Strategie gilt für den erklärten kontrollierten Laborbereich.

Der Roboter beginnt mit einer gemessenen 360°-Drehung. Dafür werden weder
freie Kartenpixel noch ein Frontier, eine Tür-ID oder ein schon abgestimmter
Kartenstatus verlangt. Die vorhandene Drehsteuerung misst Encoderfortschritt,
bremst zwischen Segmenten und bestätigt den Halt. Aktuelle Sensoren, Not-Aus,
Antrieb, HWT und die Grenze des freigegebenen Laborbereichs bleiben wirksam.
Ein tatsächlicher Schutzstopp darf auch diesen Rundblick unterbrechen.

Danach arbeitet derselbe Explorer in diesem Rhythmus:

1. Tatsächlichen Stillstand bestätigen und aktuelle Beobachtungen zusammenführen.
2. Ein sinnvolles Erkundungsziel auswählen und seinen echten Nav2-Weg prüfen.
3. Genau ein Nav2-Kind fahren lassen. LiDAR, VL53, Pose, Kartenepoche,
   Datenalter und Schutzkette weiter prüfen.
4. Kindende und tatsächlichen Halt bestätigen; Kartengewinn messen.
5. Im Stillstand wieder beobachten und das nächste Ziel wählen.

Die Sensoren laufen **durchgehend**. Die Slots begrenzen die aufwendige
Kartenauswertung und Zielwahl; sie schalten während der Fahrt keine Sensoren
ab und halten keine alten Hindernisdaten künstlich frisch. Ein normaler
Kartenfortschritt oder noch ausstehender Statusabgleich ersetzt ein laufendes
Ziel nicht. Ein echter Wechsel von Kartenepoche, Bezugssystem oder Auflösung
entzieht dagegen die alte Arbeitsgrundlage.

## Was sich selbst erholen kann

| Auslöser | Reaktion | Was erhalten bleibt |
|---|---|---|
| Kurze Sensor-/Pose-/Kartenlücke | Bewegung stoppen, Quellen und Halt neu prüfen; denselben Auftrag erneut planen | Ursprüngliches Ziel, Versuchszähler und absolute Aufgabenfrist |
| Nav2 verwirft oder erreicht ein Ziel nicht | Nach bestätigtem Halt anderen geprüften Anfahrpunkt suchen | Räumliche Fehlversuchshistorie und gesamte Missionsfrist |
| Kein brauchbares Ziel, aber noch unbekannte erreichbare Fläche | Ein kurzer gemessener Beobachtungsschwenk; danach auf neue Beobachtung oder bestehende Abkühlfrist warten | Keine erfundene Durchfahrt, Beobachtung oder erfolgreiche Kartierung |
| HWT-HOLD | Bestehende Halt-/ACK-Kette verwenden, danach tatsächlichen Weg neu prüfen | HOLD-Ursache, Zähler, Aufgabe und ursprüngliche Fristen |
| Dauerhaft fehlende notwendige Quelle | Nach einem begrenzten ununterbrochenen Prüfzeitraum stehen bleiben und Hilfebedarf melden | Ehrlicher Teilstand und gespeicherte Arbeit; kein Erfolgsabschluss |
| Not-Aus, gelatchter Antriebsfehler, falsche Drehrichtung, ungültiger Controllervertrag, unbekannter Kindzustand | Sicher beenden und tatsächlichen Grund melden | Fehler und Schutzsperren werden niemals gelöscht |

Die Wiederprüfung hat standardmäßig 30 Sekunden, maximal 60 Sekunden. Ein
anderer Fehlername verlängert dieselbe ununterbrochene Datenlücke nicht.
Normale Fahrfehlschläge erreichen im LAB nicht mehr über den globalen
`max_failed_goals`-Zähler allein einen Missionsabbruch. Die Grenzen je räumlicher
Aufgabe, dieselben bereits gescheiterten Ziele, die Gesamtzahl der Aufgaben und
die ursprünglichen absoluten Fristen bleiben bestehen.

Nach einem gewöhnlichen Fehlversuch darf ein anderer Anfahrpunkt ohne neue
Kartenrevision geprüft werden, wenn die beiden Zielankunftsbereiche mit ihren
Trackingreserven getrennt sind. Eine neue Zielposition löscht keine Fehlversuche.
Bereits beobachtete oder teilweise beobachtete Aufgaben behalten ihre bisherigen
Nachweispflichten. Eine hypothetische spätere volle Drehung oder Rückfahrt ist
keine zusätzliche Voraussetzung der aktuellen geprüften Fahrt.

„Reset“ bedeutet hier: den verworfenen Plan vergessen und **aktuelle** Daten
neu prüfen. Es bedeutet weder Not-Aus/HWT/Encoderfehler löschen noch Sensoren,
Busse, Betriebssystem oder Zeitbudgets zurücksetzen. Die Strategie erfindet
auch keine sichere Rückwärtsfahrt aus zwei vorne montierten VL53-Sensoren.
Wenn sich kein tatsächlich passender Weg ergibt, bleibt der Roboter stehen.
Tür- und Raum-IDs können das Gedächtnis ergänzen; die geometrische Erkundung
wartet nicht auf sie. Vollständige Kundenraum-, Boden- und Hardwareabnahmen
werden dadurch nicht behauptet.

## Start und Rückfall

Die gemeinsame Mapping-Kette koppelt diese Auswahl:

```text
unknown_space_policy:=sensor_guarded execution_mode:=lab_slots
```

Das ist die LAB-Voreinstellung der App-/Mapping-Launches. Der private, aktuell
gebundene Scope bleibt `explore_params_overlay`; der reine Vorlauf bleibt mit
`active_drive:=false`, `start_explorer:=false` und ausgeschalteter automatischer
Erkundung verfügbar. Die Änderung schaltet keinen Aktor automatisch ein.

Ein später separat gestarteter Explorer muss dieselbe Moduswahl erhalten.
`metric_scope_vorbereiten.py --execution-mode lab_slots` gibt den passenden
Befehl aus. Es erstellt Parameter und startet keine Bewegung.

Nach bestätigtem Halt und Ende der eigenen Kandidatenprozesse:

- `execution_mode:=continuous unknown_space_policy:=sensor_guarded` erhält
  die bisherigen sensorüberwachten Bewegungsprofile und den alten Ablauf.
- `execution_mode:=continuous unknown_space_policy:=observed_only` stellt
  auch die bisherige Zulassung ausschließlich beobachteter Karte wieder her.

Ein laufender Auftrag darf die Auswahl nicht wechseln. Sie ist beim echten
ROS-Knoten schreibgeschützt. Der alte Ablauf bleibt im selben Paket erhalten.
Keine zweite Navigation, kein neuer Supervisor und kein anderer Motorpfad.

## Prüfen und Belegen

`src/explore/test/test_lab_slots.py` führt den tatsächlichen Elternablauf und
die bestehende Kandidatenauswahl mit ersetztem Bewegungs-/Actiontransport aus.
Das prüft Ablauf, Gegenfälle, Fristen und Zähler; es misst keine reale Drehung.
Die Launch- und ROS-Parameterprüfungen kontrollieren die gemeinsame Modusbindung.

Für die geschlossene Produktprüfung den bestehenden Testdriver mit
`--unknown-space-policy sensor_guarded --execution-mode lab_slots` ausführen.
Die ursprünglichen Welt-, Sensor-, Budget- und Abschlusskriterien bleiben gleich.
Sein Exitcode ist keine Aussage über erfolgreiche Missionen. Präfixe, geladenen
Quellstand, Missionsende, Kartengewinn und Cancel/HOLD getrennt auswerten.
Reale Karten/Bilder/Bags bleiben außerhalb Git. Eine echte LAB-Fahrt verlangt
weiterhin den vorhandenen Quellen-/TF-/Recorder-/Haltvorlauf.
