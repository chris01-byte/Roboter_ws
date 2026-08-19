# Amadeus – Robotersteuerung für iPhone

Native SwiftUI-App für `roboter_ws`. Sie ersetzt auf dem iPhone die Bedienung
über Safari/PWA, spricht aber dasselbe rosbridge-Protokoll. Die bisherige
Browser-GUI bleibt als Fallback erhalten.

## Voraussetzungen

- iPhone mit iOS 16 oder neuer
- iPhone und Jetson im selben vertrauenswürdigen WLAN
- Auf dem Jetson läuft `robot_bringup/robot.launch.py` und damit rosbridge auf
  TCP-Port `9090`
- Xcode 26 oder neuer für den aktuellen Projektstand
- Für die Installation auf einem echten iPhone ein in Xcode ausgewähltes
  Apple-Entwicklerteam

Port `8080` wird von der nativen App nicht benötigt. Er gehört nur zur alten
PWA.

## Auf dem eigenen iPhone installieren

1. `Robotersteuerung.xcodeproj` in Xcode öffnen.
2. Target **Robotersteuerung** → **Signing & Capabilities** öffnen.
3. Bei **Team** das eigene Apple-Konto auswählen. Falls Xcode es verlangt, die
   Bundle-ID `de.roboterws.Robotersteuerung` auf eine eigene eindeutige ID
   ändern.
4. iPhone per Kabel oder über Xcode-WLAN-Debugging verbinden, auf dem iPhone
   den Entwicklermodus erlauben und das Gerät als Run Destination wählen.
5. **Run** drücken.
6. Beim ersten Verbindungsversuch den iOS-Dialog für das lokale Netzwerk mit
   **Erlauben** bestätigen.
7. In der App `ws://<JETSON-IP>:9090/` eintragen und den Power-Knopf drücken.

Die zuletzt erfolgreich verwendete Adresse wird ausschließlich lokal in den
App-Einstellungen gespeichert.

## Kostenlose Signierung erneuern

Auf diesem Entwicklungs-Mac liegt
`~/Desktop/Amadeus-App-erneuern.command`. Nach Ablauf des kostenlosen
Sieben-Tage-Profils das iPhone per USB verbinden, entsperren und die Datei
doppelklicken. Sie prüft das bekannte Gerät, baut und signiert die App mit
dem in Xcode ausgewählten Team, installiert sie über die vorhandene App und
startet anschließend Amadeus. Die App nicht vorher vom iPhone löschen, damit
ihre lokalen Einstellungen erhalten bleiben.

## Bedien- und Sicherheitslogik

- Missionen werden erst freigeschaltet, wenn rosbridge verbunden ist und
  sowohl ein frischer Missionsstatus als auch ein frischer
  NOT-AUS-Istzustand empfangen wurden.
- Während eine Mission läuft oder ihr Abbruch noch bestätigt wird, bleiben
  neue Missionsbuttons gesperrt. „Abgebrochen“ erscheint erst nach dem
  terminalen ROS-Action-Ergebnis.
- NOT-AUS wird sofort angefordert. Die App zeigt ihn erst dann als aktiv an,
  wenn `/safety/estop` dies bestätigt.
- Das Freigeben eines aktiven NOT-AUS verlangt eine zweite Bestätigung.
  Unmittelbar vor dem Senden prüft der Controller erneut, ob der bestätigte
  aktive Sicherheitsstatus noch frisch ist.
- Nach WLAN-Abbrüchen verbindet die App mit begrenztem exponentiellem Backoff
  erneut. Nach Rückkehr aus dem Hintergrund wird eine neue Verbindung
  aufgebaut.
- Der Tab **Karte** liest `/map` über eine eigene WebSocket-Verbindung. Große
  OccupancyGrid-Nachrichten können dadurch die Steuer- und
  Sicherheitsverbindung nicht blockieren.
- Im Karten-Tab lassen sich Räume manuell als Polygon deklarieren: Eckpunkte
  antippen, Fläche abschließen, einen Navigationspunkt innerhalb der Fläche
  wählen, Blickrichtung festlegen und speichern. Gespeicherte Räume werden
  farbig überlagert, können ausgewählt und bewusst gelöscht werden.
- Vor der ersten Raumdeklaration bietet die App nur bei eindeutig passender
  Live-Karte **Karte für Räume speichern** an. Danach müssen Live-Karte,
  Kartenmanager und semantischer Snapshot denselben Fingerabdruck und dieselbe
  Geometrie melden. Eine vorhandene persistierte Semantik bleibt nach einem
  Backend-Neustart auch ohne aktuelles `storage.last_saved` bearbeitbar.
- Raumänderungen verwenden `request_id` und `base_revision`. Nach Konflikt,
  unklarer Bestätigung oder zwölf Sekunden ohne Antwort sperrt die App den
  Editor, wiederholt nichts automatisch und verlangt ein Neuladen.
- Die Karte kann per Geste oder über die drei eingeblendeten Tasten vergrößert,
  verschoben und zurückgesetzt werden. Bei einem Verbindungsabbruch bleibt die
  letzte gültige Karte sichtbar und trägt deutlich den Hinweis **NICHT LIVE**.
- iOS führt die WebSocket-Verbindung im gesperrten oder suspendierten Zustand
  nicht zuverlässig weiter. Die App ist deshalb niemals Teil der
  eigentlichen Sicherheitskette.
- Der Software-NOT-AUS ersetzt nicht den verdrahteten Hardware-NOT-AUS.

Die ausführliche, noch umzusetzende Integrationsanweisung für eine live
aktualisierte Roboterposition und Blickrichtung im Karten-Tab steht in
[`docs/APP_LIVE_ROBOTERPOSE_INTEGRATION.md`](../../docs/APP_LIVE_ROBOTERPOSE_INTEGRATION.md).

## Lokal bauen und prüfen

Die Swift-Tests für Protokoll und Sicherheitslogik laufen auch ohne
iOS-Simulator:

```bash
cd /Volumes/64GB/roboter_ws/ios/Robotersteuerung
swift test --scratch-path /tmp/robotersteuerung-swift-tests
python3 -m unittest discover -s Tools -p 'test_mock_rosbridge.py' -v
```

Ein unsigned App-Build funktioniert, sobald in Xcode die iOS-Plattform
installiert ist:

```bash
cd /Volumes/64GB/roboter_ws/ios/Robotersteuerung
xcodebuild \
  -project Robotersteuerung.xcodeproj \
  -scheme Robotersteuerung \
  -configuration Debug \
  -destination 'generic/platform=iOS Simulator' \
  CODE_SIGNING_ALLOWED=NO \
  build
```

Für die Tests innerhalb des iOS-Test-Targets muss zusätzlich eine
iOS-Simulator-Runtime installiert sein. Danach:

```bash
xcodebuild \
  -project Robotersteuerung.xcodeproj \
  -scheme Robotersteuerung \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro,OS=26.5' \
  test
```

## Simulator-Integrationstest ohne Jetson

Der mitgelieferte, abhängigkeitfreie Mock bildet die Steuerungs- und
Sicherheitstopics, `/map`, Kartenmanager und semantische Karte ab. In einem
Terminal starten:

```bash
cd /Volumes/64GB/roboter_ws/ios/Robotersteuerung
python3 Tools/mock_rosbridge.py
```

Danach die App im Simulator öffnen und `ws://127.0.0.1:9090/` eintragen. Der
Mock simuliert Missionsfortschritt, Abbruch, NOT-AUS-Rückmeldung und eine
erkennbare Testwohnung mit 48 × 36 Zellen. Empfangene Frames sind unter
`http://127.0.0.1:9091/events` einsehbar.

Für Fehler- und Wiederanlauftests stehen unter anderem diese lokalen
Steuerendpunkte zur Verfügung:

```text
/pause?stream=status|estop|all&seconds=8
/malformed
/partial
/unknown
/close
/reset
/map-update
/map-reset
/map-disable
/map-enable
/semantic-reset
/semantic-bump
/semantic-bump-silent
```

Der gewünschte erste Flow ist: App öffnen, Karten-Tab wählen, **Karte für
Räume speichern** antippen und anschließend den Raumeditor verwenden.
`/semantic-reset` entfernt den Mock-Snapshot. `/semantic-bump` erzeugt eine
sichtbare konkurrierende Revision; `/semantic-bump-silent` ist für den
Revisionskonflikt ohne vorherigen Status-Push gedacht. Den 12-Sekunden-Timeout
prüfen die Swift-Policytests; der Mock verwirft derzeit keine ACKs. Alle empfangenen rosbridge-
Frames bleiben unter `/events` nachvollziehbar.

Am 26.07.2026 wurden auf einem simulierten iPhone 17 Pro mit iOS 26.5 alle vier
Missionstypen, Picker, Doppel-Taps, Missionsabbruch, NOT-AUS samt
Freigabedialog, veraltete und ungültige Telemetrie, manueller und
automatischer Reconnect sowie Hintergrund/Vordergrund synthetisch bedient.
Zusätzlich wurden die Kartenanzeige, Live-Updates, Zoom, Zurücksetzen,
Subscribe/Unsubscribe, der nicht-live-Zustand und der Wiederanlauf geprüft.
Auch ein erst nach dem Öffnen der App gestarteter `/map`-Publisher wird durch
die automatische Neuregistrierung erkannt.
Am 14.08.2026 bestanden 39 Swift-Tests sowohl per `swift test` als auch im
iOS-Test-Target. Fünf Python-Tests prüfen zusätzlich den zustandsbehafteten
Mock-Flow Save→Bindung, Idempotenz, Upsert/Delete und Revisionskonflikt. Der
Test ersetzt nicht die manuelle Raumeditor-Abnahme und den abschließenden Lauf
mit echtem iPhone und Jetson.

Die Missionsansicht behandelt `rooms` und `pick_and_place_rooms` getrennt:
Selbst gezeichnete Räume erscheinen in der vorbereitenden Raumfahrt, erweitern
aber niemals die bestehende reale Pick-and-Place-Auswahl. Fehlt das additive
Feld bei einem älteren Backend, bleibt die bekannte statische Fallbackliste
aktiv.

Im Karten-Tab genügt eine passende alte Summary nicht: Save, Overlay,
Bearbeitung und Mutationsbestätigung verlangen zusätzlich den aktuellsten
`robot_map_manager`-Status mit `ok:true`. Ein Fehlerstatus sperrt die Bedienung
fail-closed, bis wieder ein gültiger Status eintrifft.

## Netzwerkgrenze

Der aktuelle rosbridge-Server verwendet unverschlüsseltes `ws://` und besitzt
im Repository keine Authentifizierung oder Topic-ACL. Die App erlaubt deshalb
gezielt lokale Verbindungen, aber keine pauschalen Internet-Ausnahmen. Den
Roboter nur in einem vertrauenswürdigen, isolierten WLAN betreiben. Für eine
Verteilung außerhalb des eigenen Netzes ist ein authentifizierter
`wss://`-Gateway mit einer Allowlist der neun benötigten Topics erforderlich.

Die dauerhaft wichtigen Details stehen in
[`GEDAECHTNISPROTOKOLL.md`](GEDAECHTNISPROTOKOLL.md).
