# Gedächtnisprotokoll – reales Mapping und Lokalisierung 27.07.2026

## Einordnung

Diese Akte setzt `integration/amadeus_map_v1` fort. Sie dokumentiert einen
neuen Stand, der laut Arbeitsbericht ausschließlich auf dem Jetson
`p-desktop` unter `~/roboter_ws` und Commit `390fcec` existiert.

Der Bericht wurde auf dem Mac gelesen und mit dem USB-Arbeitsstand verglichen.
Seine Aussagen sind damit **berichtete Hardwarebefunde**, aber noch keine
lokal reproduzierte oder durch Datei-Hashes verifizierte Softwareübernahme.
Eine byteidentische Archivkopie liegt als `QUELLBERICHT_20260727.md` in diesem
Verzeichnis. Original und Kopie besitzen SHA-256:

```text
ab00c2311e9be407ff90a33ea50e5b40ae6d8b8e0326c1181a0da848f702d919
```

Der USB-Workspace steht auf Commit
`8d43cb07ef3ed4a19b61f39e462c6c286a8faaa3`. Commit `390fcec` und
`tools/kartierung/` fehlen dort. Deshalb darf kein Code aus der Beschreibung
nachgebaut und kein Workspace pauschal in eine Richtung synchronisiert werden.

## Erreichter Hardwarestand laut Bericht

- RTAB-Map erzeugte eine reale Karte mit 902 Knoten und 17,54 m erfasster
  Fahrstrecke.
- Die Datenbank enthält 271.805 visuelle Wörter, 100 globale und 67 lokale
  Wiedererkennungen.
- Eine reale 357-Grad-Drehung erzeugte 76 Nachrichten auf
  `/localization_pose`. Das bestätigt visuelle Wiederlokalisierung.
- Der `robot_map_manager` speicherte den Snapshot
  `20260727T165329866919Z-dbdb0d131f39`.
- Nach zwei Kartierfahrten wurden nach dem gemeldeten RS485-Reconnect-Fix
  keine weiteren RS485-Fehler beobachtet.

Damit sind die V1-Annahmen „kein realer `/map`-Publisher“ und „kein produktiver
SLAM-Start“ historisch überholt. Sie bleiben im V1-Protokoll als damaliger
Ausgangsbefund erhalten.

## Berichtete Änderungen, die exakt vom Jetson übernommen werden müssen

1. `src/base_hardware/base_hardware/base_hardware_node.py`
   schließt den alten Modbus-Client vor einem Reconnect. Der USB-Stand besitzt
   diesen Reconnect-Fix noch nicht.
2. Der tatsächliche `slam.launch.py` beziehungsweise seine Aufrufer verwenden
   `sigterm_timeout:=120` und `sigkill_timeout:=180`.
3. Das Stoppen sendet SIGINT nur an den `ros2 launch`-Prozess, nicht an dessen
   gesamte Prozessgruppe. Doppeltes SIGINT kann das Schreiben des visuellen
   Wörterbuchs abbrechen.
4. `tools/kartierung/` enthält Start-, Stopp-, Fahr-, Lokalisierungs- und
   Auswertungswerkzeuge und fehlt vollständig auf dem USB-Stand.
5. Alle real verwendeten RTAB-Map-, Kamera-, TF-, Near-Field- und
   Collision-Monitor-Parameter müssen aus dem Jetson-Stand übernommen werden,
   nicht aus dem Bericht rekonstruiert werden.

Diese Liste ist eine Suchhilfe, kein Dateimanifest. Erst der echte
Jetson-Commit, sein Worktree-Status und Datei-Hashes bestimmen den Umfang eines
späteren Releases.

## Persistente Kartenartefakte auf dem Jetson

```text
~/.local/share/amadeus/rtabmap.db
~/.local/share/amadeus/rtabmap_20260727_backup.db
~/.local/share/amadeus/maps/amadeus/20260727T165329866919Z-dbdb0d131f39/
```

Die RTAB-Datenbank wurde mit ungefähr 270 MB gemeldet. Snapshot und
RTAB-Datenbank erfüllen verschiedene Aufgaben und müssen getrennt erhalten
bleiben. Die funktionierende Datenbank darf bei weiteren Rasterversuchen nicht
überschrieben werden.

## Korrigierte Diagnose- und Abnahmeregeln

- Eine von RTAB-Map beim Start gesetzte `map -> odom`-Transformation beweist
  keine Wiederlokalisierung. Verbindliches Signal ist
  `/localization_pose`.
- `/robot_map_manager/robot_pose` ist derzeit eine aus TF abgeleitete Pose.
  Sie darf weder in der App noch in einem Testbericht als bestätigte
  RTAB-Map-Lokalisierung bezeichnet werden. Eine spätere Integration von
  `/localization_pose` benötigt zuerst Typ- und QoS-Inventur auf dem Jetson.
- Logmeldungen allein sind keine ausreichende Messgrundlage. Wörterzahl,
  Knoten und Wiedererkennungen werden aus der Datenbank beziehungsweise den
  ROS-Ausgaben geprüft.
- Ein geordneter Shutdown ist erst bestätigt, wenn RTAB-Map beendet ist, die
  Datenbank integer ist und die Wörterzahl größer als null bleibt.
- Die visuelle Orientierung funktioniert, aber die metrische Kartenpose bei
  Translation ist noch nicht unabhängig bestätigt.
- Das aktuelle Belegungsraster ist mit 17,7 % frei, 31,3 % belegt und 51 %
  unbekannt noch nicht für Nav2 freigegeben.

## Sicherheitsabweichung mit hoher Priorität

Das Kartierskript publiziert bei einem Fluchtmanöver laut Bericht direkt auf
`/cmd_vel`, weil die StopZone des Collision Monitors auch Dreh- und
Rückwärtsbewegungen sperrt. Damit wird die zuvor verlangte eindeutige
Sicherheitskette umgangen.

Weitere autonome Bodenfahrten und Nav2 bleiben gesperrt, bis entweder:

- die Fluchtbewegung durch eine geprüfte Sicherheitsinstanz mit
  Richtungsfreigabe, Geschwindigkeitsgrenzen, Zeitlimit, Watchdog und
  Hardware-NOT-AUS geführt wird, oder
- ein streng manuell freizugebender Sonderbetrieb dokumentiert und
  abgenommen ist.

Ein erfolgreicher bisheriger Fahrversuch ersetzt diese Freigabe nicht.
Die vorhandenen Near-Field-Sensoren belegen außerdem keinen freien Raum hinter
dem Roboter. Eine zuvor vorwärts gefahrene Strecke ist deshalb allein kein
hinreichender Sicherheitsnachweis für eine spätere Rückwärtsflucht.

## Offene technische Punkte

- Kartenpose bei einer kurzen, metrisch bekannten Translation verifizieren.
- Höhenverteilung der echten Tiefendaten messen, bevor
  `Grid/RangeMax` von 2,5 m auf 4,0 m geändert wird.
- Eine neue Rasterkarte großflächig aufnehmen, ohne die funktionierende
  Datenbank zu überschreiben.
- OAK-Shutdown-Segfault untersuchen.
- TF-Autoritäten und genau einen zulässigen Publisher des finalen
  `/cmd_vel` nachweisen.
- Den lokalen `nav_test.launch.py` nicht auf realer Hardware starten: Er
  publiziert eine statische Test-TF `map -> odom` und verwendet eine virtuelle
  Sollwert-Odometrie. Auch die reale lokale Basis integriert derzeit
  Sollgeschwindigkeit und liefert damit keinen unabhängigen metrischen
  Streckennachweis.
- Rosbridge und iPhone-App mit später Verbindung, `/map`, Frame-ID,
  Auflösung, Kartendarstellung und Roboterpose end-to-end testen.
- Erst danach Nav2 mit `static_map_odom:=false`, echtem Footprint und
  geprüften Costmaps bewerten.

## Releasezustand

Für diese Stufe existiert absichtlich noch kein `release-spec.json` und kein
`RELEASE.json`. Ein Release darf erst erzeugt werden, nachdem der Jetson-Code,
ungecommitete Dateien und Laufzeitdaten gemäß `UEBERNAHMEPLAN.md` gesichert und
auf dem Mac gegen den bisherigen Stand verglichen wurden.
