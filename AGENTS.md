# AGENTS.md — verbindliche Arbeitsanweisung

Dieses Dokument gilt für jeden KI-Agenten und jede Person, die an **Amadeus**
arbeitet. Vor der ersten Änderung lesen: diese Datei, `docs/PROJECT_MEMORY.md`,
`docs/INVENTORY.md`.

**Für Wohnungserkundung zusätzlich zuerst:**
[MASTERPLAN v1.0](docs/wohnungserkundung/MASTERPLAN.md),
[aktueller WE-Status](docs/wohnungserkundung/STATUS.md) und
[aktueller Agentenauftrag](docs/wohnungserkundung/AGENTENAUFTRAG.md).
Der Masterplan legt den Arbeitsrahmen fest; alte Chat-Prompts und archivierte
Aufträge sind keine zweite aktuelle Roadmap. Details in Abschnitt 7.

---

## 1. Was Amadeus ist

Ein realer, fahrender Roboter mit ROS 2 Humble auf einem Jetson. Er hat Motoren,
die anlaufen können, während jemand daneben steht. **Jede Änderung an diesem
Repository kann physische Wirkung haben.**

| | |
|---|---|
| Rechner | Jetson, Ubuntu 22.04.5, ROS 2 Humble |
| Arbeitskopie | `~/roboter_ws` (maßgeblich, getestet) |
| Antrieb | 2× OMC ESS23-RS Closed-Loop-Schrittservo über RS485/Modbus |
| Kamera | OAK-D-S2 auf 1,34 m Höhe, 18,94° nach unten geneigt |
| Nahbereich | 2× VL53L7CX über CH341A-USB-I2C-Adapter |
| SLAM | RTAB-Map (RGB-D), Karten unter `~/.local/share/amadeus/` |

---

## 2. Sicherheitsregeln — nicht verhandelbar

1. **Keine Aktoren ohne ausdrückliche Freigabe.** Motoren, Hubmechanik und
   sonstige Antriebe werden nur nach Zustimmung der anwesenden Person bestromt.
2. **Erst Stillstand, dann Bewegung.** Nach jeder Änderung zuerst ohne
   Motorstrom prüfen (Topics, TF, Logs), erst danach ein begrenzter Fahrtest.
3. **Not-Aus in Reichweite**, bevor irgendetwas fährt. Der Motor-Halt am
   Roboter ist die letzte Rückfallebene — bei aktivem Halt antworten die
   Antriebe nicht auf das Kommandoregister, das sieht wie ein Modbus-Fehler aus.
4. **Keine Geheimnisse ins Repository.** Keine Tokens, Schlüssel, `.env`,
   WLAN-Zugangsdaten. Das gilt auch für Chatverläufe und Commit-Nachrichten.
5. **Keine realen Wohnungsdaten ins Repository.** Karten echter Räume,
   Kamerabilder und ROS-Bags bleiben lokal (siehe `.gitignore`).
6. **Ein Branch je Änderung**, `main` bleibt ein getesteter Stand. Kein
   `git reset --hard`, keine Massenänderungen, kein Überschreiben unbekannter
   Jetson-Dateien.
7. **Sicherheitsrelevante Bereiche** — Kalibrierung, Sensor-Frames,
   Motorsteuerung, `collision_monitor`, Netzwerk — werden separat geändert und
   separat getestet.

---

## 3. Arbeitsweise, die sich hier bewährt hat

### Erst messen, dann erklären

Das ist die teuerste Lektion dieses Projekts. In der Sitzung vom 27./28.07.2026
wurden **sieben** Hypothesen nacheinander durch Messung widerlegt — jede klang
plausibel. Bevor ein Parameter geändert wird: die zugrunde liegende Größe
messen.

### Das Log führt in die Irre

Bei RTAB-Map stehen **Misserfolge im Klartext, Erfolge nicht**. Ein
`grep "Loop closure"` findet fast nur `… rejected!`, obwohl gleichzeitig 167
Wiedererkennungen gelungen sind. Die Wahrheit steht in der Datenbank:

```bash
source /opt/ros/humble/setup.bash && rtabmap-info ~/.local/share/amadeus/rtabmap.db
```

### Eine Kennzahl allein beweist nichts

Während einer Kartierfahrt stieg die Zahl „freier Zellen" munter auf 26,5 m² —
in einem Raum von 18,6 m². 74,6 % davon waren Artefakte. **Zwischendurch
rendern und hinsehen** (`tools/kartierung/karte_ansehen.py`).

### Prozesse sauber beenden

`ros2 launch`-Kinder sind Enkelprozesse. Beim Aufräumen niemals die
**Prozessgruppe** signalisieren — RTAB-Map bekommt SIGINT dann doppelt und
verliert sein Wörterbuch (Details in `tools/kartierung/README.md`). Und:
`pgrep -f "muster"` trifft die eigene Shell, wenn deren Kommandozeile das Muster
enthält. Immer `MY=$$` setzen und die eigene PID ausnehmen.

---

## 4. Branch- und Commit-Konvention

Branch-Namen: `feature/…`, `fix/…`, `docs/…`, `chore/…`

Commit-Muster: `typ: kurze Beschreibung`

Eine Commit-Nachricht beschreibt **warum**, nicht nur was. Bei
sicherheitsrelevanten Änderungen gehört der Rückfallweg hinein. Gute Beispiele
finden sich in der Historie, etwa `f3a9094` (Fahrverhalten) — dort steht die
gemessene Evidenz mit Zahlen.

### Pull-Request-Checkliste

- [ ] Geheimnisse geprüft
- [ ] Build und Test ausgeführt
- [ ] `docs/PROJECT_MEMORY.md` bei Entscheidungen ergänzt
- [ ] `docs/ROBOT_TRANSFER.md` bei Jetson-Wirkung ergänzt
- [ ] Hardwarewirkung beschrieben
- [ ] Rückfallweg beschrieben
- [ ] Keine Aktoren ohne Freigabe aktiviert

---

## 5. Verzeichnisübersicht

| Pfad | Inhalt |
|---|---|
| `src/` | 17 ROS-2-Pakete (siehe `docs/INVENTORY.md`) |
| `src/robot_bringup/launch/` | Startdateien: `robot`, `slam`, `oak`, `teleop_joy`, `server` |
| `tools/kartierung/` | Kartierung, Lokalisierungstests, Kartenauswertung — **mit Fallenbeschreibung im README** |
| `docs/` | Dokumentation, udev-Regeln |
| `ios/` | Xcode-Projekt der App |
| `integration/` | Übergabeprotokolle und Release-Werkzeuge |

---

## 6. Was zuerst zu tun ist

1. `docs/INVENTORY.md` lesen — Komponenten, Startbefehle, Reifegrad.
2. `docs/PROJECT_MEMORY.md` lesen — getroffene Entscheidungen und ihre Gründe.
3. `tools/kartierung/README.md` lesen, falls es um Karten oder Lokalisierung
   geht. Dort stehen drei Fallen, die real Zeit gekostet haben.
4. Bestand prüfen, bevor etwas verändert wird: Läuft schon etwas? Sind die
   Motoren bestromt? Steht der Roboter frei?

---

## 7. Wohnungserkundung: verbindlicher Arbeitsrahmen (WE-1, 27.09.2026)

Bei Arbeiten an Wohnungserkundung, Sensor-/Fahrintegration, Recovery,
Portal-/Raumgedächtnis oder Erkundungsabschluss vor jeder Änderung lesen:

1. [Masterplan: Konsolidierung und robuste Wohnungserkundung](docs/wohnungserkundung/MASTERPLAN.md)
2. [Einziger aktueller WE-Iststand](docs/wohnungserkundung/STATUS.md)
3. [Aktueller Agentenauftrag](docs/wohnungserkundung/AGENTENAUFTRAG.md)
4. [Gesamtstrategie](docs/WOHNUNGSERKUNDUNG_STRATEGIE.md) und betroffene
   [Meilensteine/Abnahmen](docs/wohnungserkundung/MEILENSTEINE.md)

Verbindliche Grundentscheidung: **konsolidieren statt komplett neu schreiben**.
Bestehende Fähigkeiten erhalten, einen reproduzierbaren Kandidaten führen,
Fehler- und Wiederaufnahmeverantwortung gezielt ordnen, dann reale Kernabnahme
und WE-M4/M5/M6. Keine parallele P1–P5-Roadmap, keine neue Navigation und kein
pauschaler Rücksprung auf alte Branches. Ein Integrationsverantwortlicher,
ein aktiver Kandidat und genau ein aktueller Auftrag.

Planversion, WE-Bezug, tatsächliche Istbasis, erwartetes Ergebnis, Nicht-Ziele,
Tests und Rückfall vor jedem Auftrag benennen. Abweichungen nicht stillschweigend
umsetzen. Nach jedem Auftrag Nachweise und genau einen nächsten Schritt im
STATUS fortschreiben. Historische Erfolge bleiben erhalten; sie autorisieren
keinen ungeprüften neuen Install. Neue Grundentscheidungen im Masterplan
versionieren, nicht durch weitere konkurrierende Chat-Prompts ersetzen.

Fachliche WE-Entscheidungen liegen in `docs/wohnungserkundung/STATUS.md`;
übergreifende Projektentscheidungen zusätzlich im PROJECT_MEMORY, tatsächliche
Jetson-Wirkung im ROBOT_TRANSFER. Keine parallelen aktuellen Statuskopien.
Main, HWT-Referenz, lokale Arbeit und ausgeführte Paketpräfixe unterscheiden.
Allgemeine/historische Übersichten oben und im Inventar bestimmen nicht den
aktuell gestarteten SLAM-/Antriebspfad.

Sicher stoppen und einen recoverbaren Auftrag erhalten sind verschiedene
Aufgaben. Recovery nicht durch Weglassen von Schutzprüfungen ersetzen.
Bestehende Sicherheitsregeln bleiben gültig. Dokumentation, Commit, Push und
Merge autorisieren weder Geräteaktivierung noch Fahrt. Auch der Masterplan
ist eine Zielentscheidung, keine Behauptung eines fertigen Kundenprodukts.
