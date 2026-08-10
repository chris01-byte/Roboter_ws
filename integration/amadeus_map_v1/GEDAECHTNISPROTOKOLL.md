# Gedächtnisprotokoll – Amadeus-Kartenintegration

> **Historischer Stand vom 26.07.2026:** Ein Arbeitsbericht vom 27.07.2026
> bestätigt inzwischen reales RTAB-Map-Mapping und Wiederlokalisierung auf dem
> Jetson. Der dortige, neuere Commit `390fcec` liegt noch nicht auf diesem
> Datenträger. Dieses V1-Protokoll und sein Release bleiben zur
> Nachvollziehbarkeit unverändert maßgeblich für Stufe V1, dürfen aber nicht
> als aktueller Jetson-Stand oder blindes Apply-Ziel verwendet werden.
> Fortsetzung:
> `integration/amadeus_slam_localization_20260727/GEDAECHTNISPROTOKOLL.md`.

**Integrations-ID:** `amadeus-map-v1`  
**Beginn:** 26.07.2026  
**Quell-Workspace:** `/Volumes/64GB/roboter_ws`  
**Ausgangs-Commit:** `39398fcbe283b4486f5c061b13e9b62418a7f550`

Dieses Verzeichnis dokumentiert ausschließlich die neue Kartenintegration
zwischen Robotersoftware und nativer iOS-App. Es ist kein Laufzeitbestandteil
des Roboters. Maßgeblich für eine Übertragung ist das generierte Release unter
`/Volumes/64GB/robot_transfers/`, nicht ein pauschaler Workspace-Abgleich.

## Ergebnis dieser Integrationsstufe

Die Roboterseite besitzt jetzt das neue, fahrbewegungsfreie ROS-2-Paket
`robot_map_manager`. Der zentrale Bringup startet es standardmäßig und über
`start_map_manager:=false` abschaltbar. Es:

- empfängt und validiert `/map` mit zwei kompatiblen QoS-Profilen,
- hält nur den jüngsten gültigen Snapshot im Speicher,
- veröffentlicht eine zeitlich geprüfte Roboterpose im tatsächlichen
  Frame des aktuellen Kartensnapshots,
- speichert ausschließlich auf expliziten Befehl unveränderliche,
  versionierte PGM-/YAML-/Binär-/Metadaten-Artefakte,
- begrenzt Speicherrate, freien Platz, Gesamtgröße, Namen und Versionen,
- löscht oder lädt keine Wohnungskarte und sendet keinerlei Fahrbefehl.

Die native App liest die Live-Karte weiterhin direkt auf `/map`. Das neue
Paket stellt zusätzlich Speicherung, Diagnose und Pose bereit; die App nutzt
die gespeicherte Versionsliste und Pose in dieser Stufe noch nicht.

Der produktive Bringup besitzt weiterhin absichtlich keinen unbestätigten
SLAM-Start. Ohne einen echten `/map`-Publisher wartet die App daher korrekt
auf eine Karte. Diese Grenze ist kein vergessener Codepfad, sondern das
Ergebnis der Sicherheitsprüfung des vorhandenen Stacks.

## Unveränderter Altbestand

Beim Beginn der Arbeit war der Git-Arbeitsbaum bereits nicht sauber. Folgende
Änderungen gehören **nicht** zur Kartenintegration und dürfen nicht
versehentlich in deren Release aufgenommen werden:

```text
 M .gitignore
 M PROJEKT_STATUS.md
 M README.md
 M src/mission_manager/README.md
 M src/mission_manager/mission_manager/mission_manager_node.py
 M src/mission_manager/package.xml
?? ios/
?? src/mission_manager/mission_manager/action_outcome.py
?? src/mission_manager/mission_manager/command_payload.py
?? src/mission_manager/test/
```

Diese Liste ist eine Klassifikation, kein Hinweis darauf, die Dateien
zurückzusetzen oder zu löschen.

## Ausgangsbefund der Kartenkette

Der virtuelle Testpfad `robot_navigation/nav_test.launch.py` veröffentlicht
die statische `testwohnung` über Nav2 `map_server`. Im produktiven
`robot_bringup/robot.launch.py` existierte dagegen noch:

- kein SLAM-Node,
- kein `/map`-Publisher,
- kein produktiver Nav2-Start,
- kein `map -> odom`,
- keine Kartenpersistenz,
- keine veröffentlichte Roboterpose im Kartenframe.

Die native App ist bereits ein rein lesender `/map`-Client. Sobald ein
gültiges `nav_msgs/OccupancyGrid` auf `/map` über das bestehende rosbridge
erreichbar ist, kann sie die Karte darstellen.

## Sicherheitsgrenze

Diese Integrationsstufe darf keine reale Fahrt aktivieren. Die vorhandene
Robotersoftware belegt noch keine geeignete reale Odometrie und die aktuelle
Nav2-/Collision-Monitor-Topickette ist nicht produktionsreif. Deshalb bleiben
RTAB-Map, produktives Nav2 und Motoraktivierung aus, bis auf dem echten
Roboter Sensor-Topics, TF-Autoritäten und die sichere `cmd_vel`-Kette geprüft
sind.

Gespeicherte Wohnungskarten sind geschützte Laufzeitdaten. Sie liegen
außerhalb des Workspace unter:

```text
~/.local/share/amadeus/maps
```

Transfer-, Build- und Rollback-Werkzeuge dürfen diesen Pfad niemals
überschreiben oder löschen.

## Transferregeln

1. Kein pauschales `rsync` definiert den Umfang dieser Änderung.
2. Jede Robot-Zieldatei steht explizit im Release-Manifest.
3. `modify` verlangt den erwarteten Vorher-Hash; `add` verlangt, dass das
   Ziel noch nicht existiert. Abweichung bedeutet Abbruch und Driftbericht.
4. Vor dem Schreiben wird ein Backup der tatsächlich vorhandenen Zieldateien
   angelegt.
5. Dateien werden atomar ersetzt und anschließend erneut gehasht.
6. Ein Rollback entfernt nur unveränderte, durch das Release neu angelegte
   Dateien und restauriert nur Dateien, deren aktueller Hash noch zum Release
   passt.
7. Der Roboter-Stack wird nicht automatisch gestartet, gestoppt oder bewegt.
8. Die iOS-App, bestehende Missionsmanager-Änderungen sowie Build-, Install-,
   Log- und Kartendaten sind nicht Bestandteil dieses Robot-Releases.

## Noch hardwaregebunden

Vor Freigabe von echtem SLAM/Nav2 muss ein späterer Agent auf dem Jetson
mindestens ermitteln:

- JetPack-/Ubuntu-/ROS-Version und installierte RTAB-Map-/OAK-Pakete,
- tatsächliche Kamera-, Depth-, IMU- und Odometrie-Topics samt QoS,
- genau einen Besitzer für `map -> odom`,
  `odom -> base_footprint` und feste Sensor-TFs,
- Nav2-Ausgang auf ein Vorfilter-Topic und den Collision Monitor als einzigen
  Publisher des finalen `/cmd_vel`,
- reale Footprint-Abmessungen und Costmap-Sensorquellen,
- Verfahren für RTAB-Datenbank, Karten-Snapshot und Wiederlokalisierung.

Die Ergebnisse gehören als neues, getrenntes Release beziehungsweise als
Ergänzung dieses Protokolls dokumentiert.

## Fertiges Übergabepaket

```text
Release-ID: amadeus-map-v1-20260726T194942Z
Archiv:     /Volumes/64GB/robot_transfers/amadeus-map-v1-20260726T194942Z.tar.gz
SHA-256:    26db555ed8db674f69a6bb052083a197221e2b821b592079ddb2c26be8ab62ee
Umfang:     15 exakt manifestierte Laufzeitdateien
Pakete:     robot_bringup, robot_map_manager
```

Das Archiv enthält Vorher-/Nachher-Hashes, Dateimodi, Patch, Testplan,
Payload, Preimages sowie portable Apply-/Rollback-/Prüfwerkzeuge. Es wurde
aus einem privaten Snapshot gepackt, direkt auf dem exFAT-Ziel verifiziert,
sicher extrahiert und gegen eine simulierte Jetson-Kopie geprüft.

Bestanden:

- 46/46 ROS-unabhängige Kartenmanager-Tests,
- 24/24 Transfer-, Archiv-, Race- und Rollback-Tests,
- Syntax-, Python-3.8-/3.10-, XML- und JSON-Prüfungen,
- Release-Dry-run, Apply, Nachhashprüfung und vollständiger Rollback,
- erneuter Dry-run aus dem tatsächlich extrahierten Transportarchiv,
- unabhängige Reviews ohne verbleibenden P0/P1/P2-Softwareblocker.

Nicht lokal ausführbar waren `colcon`, echte rclpy-/QoS-/TF-Callbacks und der
ROS-Smoke-Launch, weil auf diesem Mac keine ROS-2-Humble-Laufzeit installiert
ist. Diese Prüfungen bleiben im Archiv-Testplan und im
`HARDWARE_AKTIVIERUNGSPLAN.md` verpflichtend.

`before_mode` und Marker erwarten für die drei bestehenden Bringup-Dateien
den Modus `0700`, wie er beim dokumentierten `rsync -a` vom exFAT-Stick auf
den Jetson entsteht. Zeigt die Zielinventur andere Modi oder Hashes, muss der
Dry-run abbrechen. Dann wird der reale Vorzustand erst geprüft und das
Manifest bewusst neu erzeugt; Modi werden nicht zur Umgehung des Schutzes
blind geändert.
