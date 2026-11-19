# Aktueller Auftrag der KI-Linie: KI-0 – Erstes Sehen (im Stand, ohne Bewegung)

**Erteilt am 19.11.2026.** Er wird aktiv, sobald der Projektinhaber ihn
übergibt. Zwei Teile: **Teil A für den KI-Rechner**, **Teil B für den
Jetson**. Teil A muss vor Teil B laufen.

**Stand 19.11.2026 (spät): Teil A lief bis A5.** Ergebnis und Folgen stehen
in `STATUS.md`. Neu ist der Abschnitt **„A-Nachtrag“** unten; er ersetzt A4
bis A6 für die Fortsetzung. Teil B wurde angepasst (eine Antwort je Frage,
Denken nur nach A-Nachtrag, eine Ansicht zweimal).

**Frage dieses Auftrags:** Erkennt ein Bildmodell auf dem KI-Rechner an
echten Bildern der Kamera von Amadeus, welche vermessene Öffnung die Tür ist,
und wie lange braucht es dafür? Nichts fährt.

| | |
|---|---|
| Konzept | `ki_erkundung/KONZEPT.md` v1.1, Stufe KI-0 |
| Istbasis | Branch `claude/blissful-pasteur-s1eivj`, mindestens der Commit, der diesen Auftrag enthält |
| Erwartetes Ergebnis | Antworten der KI zu einigen Standbildern mit Zeiten; Urteil des Projektinhabers, ob die Tür richtig erkannt wurde; Messwerte zu Kamera, Vermessung und Verbindung |
| Nicht-Ziele | Keine Fahrt, keine Drehung, kein Motor; kein Eingriff in vorhandene Dienste, Pakete, Profile oder `~/roboter_ws`; kein Dauerbetrieb des neuen Dienstes |
| Rückfall | Den gestarteten Lotsen-Dienst, Kamera und LiDAR beenden; `~/ki_erkundung_ws` (KI-Rechner) und die Ausgabeordner dürfen gelöscht werden; das Modell mit `ollama rm` entfernen |

## Regeln

- **Kein Motor, kein Fahr-Stack.** Gestartet werden nur: auf dem KI-Rechner
  der Lotsen-Dienst, auf dem Jetson Kamera und LiDAR.
- **Bilder bleiben im Haus.** Aufnahmen, markierte Fotos und Ergebnisdateien
  liegen nur lokal (Jetson: `~/.local/share/amadeus/ki_erkundung/` und
  `~/ki_trockenlauf_ki0/`; KI-Rechner: `~/ki_trockenlauf_ki0/`). Nichts davon
  in ein Repository, nichts in den Bericht außer Zahlen und Antworttext.
- **Nichts Vorhandenes ändern.** `amadeus-ki.service`, seine Einstellungen
  und `~/roboter_ws` bleiben, wie sie sind.
- **Nichts reparieren.** Läuft ein Schritt nicht, die Meldung wörtlich
  berichten und beim nächsten sinnvollen Schritt weitermachen.
- **Prozesse einzeln beenden:** genau ein SIGINT an die jeweilige PID, nie
  an eine Prozessgruppe (AGENTS §3).

---

## Teil A – KI-Rechner

### A0 – Bestand

```bash
date -Iseconds; hostname
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv
systemctl is-active amadeus-ki.service; systemctl cat amadeus-ki.service
ollama --version; ollama list
```

Aus der Unit ablesen, in welcher Umgebung die vorhandenen KI-Knoten starten
(ROS-Umgebung, `ROS_DOMAIN_ID`, `RMW_IMPLEMENTATION`, `CYCLONEDDS_URI`).
**Diese Umgebung wird im Folgenden unverändert mitbenutzt**; `umg` steht für
den Aufruf eines Befehls darin. Beispiel, an die Unit anpassen und im
Bericht wörtlich nennen (ohne IP-Adressen):

```bash
umg() { pixi run --manifest-path ~/roboter_ws/src/robot_bringup/config/offboard_pixi.toml \
        bash -lc "export ROS_DOMAIN_ID=42 RMW_IMPLEMENTATION=rmw_cyclonedds_cpp; $1"; }
```

### A1 – Stand der KI-Linie holen (eigener Ordner)

```bash
git -C ~/roboter_ws fetch origin claude/blissful-pasteur-s1eivj
C=$(git -C ~/roboter_ws rev-parse FETCH_HEAD); echo "$C"
if [ -d ~/ki_erkundung_ws ]; then git -C ~/ki_erkundung_ws checkout --detach "$C"
else git -C ~/roboter_ws worktree add --detach ~/ki_erkundung_ws "$C"; fi
git -C ~/ki_erkundung_ws rev-parse HEAD; ls ~/ki_erkundung_ws/ki_erkundung
mkdir -p ~/ki_trockenlauf_ki0
```

Die Arbeitskopie `~/roboter_ws` wird dabei nicht verändert. Ist `~/roboter_ws`
dort kein Git-Repository mit Zugriff auf den Branch, das berichten und den
Branch stattdessen frisch nach `~/ki_erkundung_ws` klonen.

### A2 – Tests der Linie

```bash
umg 'cd ~/ki_erkundung_ws && env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
     python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -5'
```

Erwartung: `158 passed` (ohne ROS im Aufruf: `150 passed, 2 skipped`). Fehlt
`pytest` in der Umgebung, das berichten und weitermachen. In der
Pixi-Umgebung des KI-Rechners bricht pytest 9 am Plugin `launch_testing` ab;
dort `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` vor den Aufruf setzen (Befund
19.11.2026).

### A3 – Bildmodell laden

```bash
ollama pull qwen3.5:9b
ollama list
```

Wenn Zeit und Platz reichen, zum Vergleich auch `ollama pull qwen3-vl:8b`.

### A4 – Erste Antwort des echten Modells (künstliches Beispiel, ohne Roboter)

```bash
umg 'cd ~/ki_erkundung_ws && python3 ki_erkundung/werkzeuge/beispielrunde_erzeugen.py \
     --ausgabe ~/ki_trockenlauf_ki0/beispiel'
umg 'cd ~/ki_erkundung_ws && python3 ki_erkundung/werkzeuge/trockenlauf.py \
     --runden ~/ki_trockenlauf_ki0/beispiel --ausgabe ~/ki_trockenlauf_ki0/beispiel_ohne \
     --modell qwen3.5:9b --denken aus --wiederholungen 3'
umg 'cd ~/ki_erkundung_ws && python3 ki_erkundung/werkzeuge/trockenlauf.py \
     --runden ~/ki_trockenlauf_ki0/beispiel --ausgabe ~/ki_trockenlauf_ki0/beispiel_mit \
     --modell qwen3.5:9b --denken an --wiederholungen 2'
nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

Die Ausgabe jeder Zeile (`Wahl …`, `verworfen …` oder `keine Antwort …`,
Sekunden) wörtlich berichten. Das Beispiel ist ein gezeichnetes Zimmer; es
prüft, ob das Modell mit neun Bildern und dem Antwortschema zurechtkommt.
Steht in `ergebnis.json` unter `antworten` irgendwo `"mit_schema": false`
oder `"denken": null` trotz Angabe, das berichten.

### A5 – Lotsen-Dienst starten

```bash
umg 'nohup env --default-signal=INT python3 ~/ki_erkundung_ws/ki_erkundung/werkzeuge/lotse_dienst.py \
     --modell qwen3.5:9b > ~/ki_trockenlauf_ki0/lotse_dienst.log 2>&1 < /dev/null & echo $! > ~/ki_trockenlauf_ki0/lotse_dienst.pid'
sleep 5; cat ~/ki_trockenlauf_ki0/lotse_dienst.pid; tail -3 ~/ki_trockenlauf_ki0/lotse_dienst.log
umg 'timeout 10 ros2 topic echo --once /ki_erkundung/lotse_status_json'
```

Erwartung im Status: `"bereit": true`, das Modell, die Fassung von Ollama.
Die PID muss die des Python-Prozesses sein (`ps -o pid,cmd -p <PID>`). Der
Dienst bleibt für Teil B laufen.

### A6 – nach Teil B: Dienst beenden

```bash
kill -INT "$(cat ~/ki_trockenlauf_ki0/lotse_dienst.pid)"; sleep 2
tail -20 ~/ki_trockenlauf_ki0/lotse_dienst.log
systemctl is-active amadeus-ki.service
```

### A-Nachtrag (19.11.2026, spät) – Fortsetzung nach dem ersten Lauf

Gilt statt A4 bis A6 für die Fortsetzung. Grund: Im ersten Lauf wählte das
Modell dreimal Nummer 1; im Beispielzimmer ist **Nummer 1 die Glastür zum
Balkon**, Nummer 2 die Tür zum Flur. Die Läufe mit Denken endeten ohne
Antwort; die Werkzeuge hatten dabei still mit anderen Einstellungen
wiederholt und den Fehlertext des Dienstes nicht festgehalten. Beides ist
behoben; jetzt wird genau einmal so gefragt wie angegeben, und der Fehlertext
steht in der Ausgabe.

**N1 – neuen Stand holen und Tests:**

```bash
git -C ~/ki_erkundung_ws fetch origin claude/blissful-pasteur-s1eivj
git -C ~/ki_erkundung_ws checkout --detach FETCH_HEAD; git -C ~/ki_erkundung_ws rev-parse HEAD
umg 'cd ~/ki_erkundung_ws && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 env -u CYCLONEDDS_URI \
     ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -3'
```

**N2 – das Beispiel noch einmal, je Einstellung genau eine Frage:**

```bash
B=~/ki_trockenlauf_ki0/beispiel; A=~/ki_trockenlauf_ki0
umg "cd ~/ki_erkundung_ws && python3 ki_erkundung/werkzeuge/trockenlauf.py --runden $B \
     --ausgabe $A/n2_qwen35_ohne --modell qwen3.5:9b --denken aus"
umg "cd ~/ki_erkundung_ws && python3 ki_erkundung/werkzeuge/trockenlauf.py --runden $B \
     --ausgabe $A/n2_qwen3vl --modell qwen3-vl:8b"
umg "cd ~/ki_erkundung_ws && python3 ki_erkundung/werkzeuge/trockenlauf.py --runden $B \
     --ausgabe $A/n2_qwen35_denken --modell qwen3.5:9b --denken an --zeitgrenze 180"
```

Jede Ausgabezeile wörtlich berichten (sie nennt jetzt Wahl, Einordnung jeder
Nummer, Raum, Ladezeit und eingelesene Teile, bei einem Fehler den Text des
Dienstes). Dazu je Lauf aus `ergebnis.json` die `begruendung`. Wechselt das
Modell, enthält die erste Zeile die Ladezeit; das ist erwartet.

**N3 – Lotsen-Dienst über WLAN starten.** Christopher (19.11.2026): Roboter
und KI-Rechner liefen auch im August über WLAN, nicht über Kabel. Die
DDS-Einstellung des vorhandenen Dienstes nennt aber die Kabelbuchse
(`enp4s0`). Deshalb bekommt **nur der Lotsen-Dienst** eine eigene Kopie
dieser Einstellung, in der allein die Netzwerkschnittstelle auf die
WLAN-Schnittstelle zeigt. Nicht ändern: `amadeus-ki.service`, seine
DDS-Datei, Netzwerkeinstellungen des Rechners, Firewall. Rückfall: die Kopie
löschen.

```bash
ip -br addr | grep -v "^lo"          # Name der WLAN-Schnittstelle (Befund: wlo1)
systemctl show amadeus-ki.service -p Environment | tr ' ' '\n' | grep CYCLONEDDS_URI
Q=<Pfad aus CYCLONEDDS_URI ohne file://>; L=~/ki_trockenlauf_ki0/cyclonedds_lotse.xml
cp "$Q" "$L"
```

In `$L` mit dem Datei-Werkzeug genau den Eintrag ändern, der `enp4s0` nennt,
so dass dort die WLAN-Schnittstelle steht; alles andere (Domain, Peers)
bleibt gleich. `diff "$Q" "$L"` muss genau diese eine Änderung zeigen; im
Bericht die Diff-Zeilen ohne IP-Adressen nennen. Steht in der Datei keine
Schnittstelle, sondern eine Adresse, die WLAN-Adresse des Rechners
einsetzen und das berichten. Dann prüfen, ob der Jetson erreichbar ist (die
Adresse steht in den Peers der Datei oder im August-Abschnitt des
ROBOT_TRANSFER; im Bericht ohne Adresse):

```bash
ping -c 3 -W 2 <Jetson-Adresse>
umg "export CYCLONEDDS_URI=file://$L; nohup env --default-signal=INT python3 \
     ~/ki_erkundung_ws/ki_erkundung/werkzeuge/lotse_dienst.py --modell qwen3.5:9b \
     > ~/ki_trockenlauf_ki0/lotse_dienst.log 2>&1 < /dev/null & echo \$! > ~/ki_trockenlauf_ki0/lotse_dienst.pid"
sleep 5; cat ~/ki_trockenlauf_ki0/lotse_dienst.pid; tail -3 ~/ki_trockenlauf_ki0/lotse_dienst.log
umg "export CYCLONEDDS_URI=file://$L; timeout 10 ros2 topic echo --once /ki_erkundung/lotse_status_json"
```

Der Dienst bleibt für Teil B laufen; danach A6. Das Modell im Dienst ist
`qwen3.5:9b`; zeigt N2, dass `qwen3-vl:8b` die Glastür richtig einordnet und
`qwen3.5:9b` nicht, stattdessen `--modell qwen3-vl:8b` nehmen und das
berichten.

### Bericht Teil A

Datei `~/ki_erkundung_bericht_ki0_rechner.md`: Bestand, benutzte Umgebung,
HEAD, Testergebnis, Modelle, die Zeilen aus A4 mit Zeiten, Grafikspeicher,
Status des Dienstes, die Logzeilen des Dienstes zu den Fragen aus Teil B,
alles, was nicht lief.

---

## Teil B – Jetson

Christopher ist dabei. Amadeus steht; niemand muss ihn fahren. Gut ist eine
Stelle, von der die offene Labortür in 2 bis 3 m Entfernung vor ihm liegt.

### B0 – Bestand

```bash
date -Iseconds; MY=$$
pgrep -af "ros2 launch|ldlidar|depthai|base_hardware|slam_toolbox" | grep -v "^$MY " || echo "keine Amadeus-Prozesse"
```

Läuft ein Stack oder ein fremder Test: Christopher einmal fragen, nichts
selbst beenden.

### B1 – Stand holen und Tests

```bash
cd ~/roboter_worktrees/selbstheilung-v2 && git status --short | head -5 && \
  git pull --ff-only && git rev-parse HEAD
source /opt/ros/humble/setup.bash
env -u CYCLONEDDS_URI ROS_DOMAIN_ID=227 ROS_LOCALHOST_ONLY=1 \
  python3 -m pytest -q -p no:cacheprovider ki_erkundung/tests 2>&1 | tail -5
```

### B2 – Umgebung für die Verbindung zum KI-Rechner

Dieselbe Umgebung wie beim Kamerastrom zur Objekterkennung (ROBOT_TRANSFER,
Abschnitt „OAK-RGB-D-Transport …“, 26.08.2026): `/opt/ros/humble`,
`~/roboter_ws/install`, `ROS_DOMAIN_ID=42`,
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` und das lokale `CYCLONEDDS_URI` mit
den festen Gegenstellen. Die gesetzten Werte im Bericht nennen (ohne
IP-Adressen). In jeder neuen Shell zuerst diese Umgebung setzen. Dann:

```bash
KI=~/ki_trockenlauf_ki0; mkdir -p "$KI"
timeout 15 ros2 topic echo --once /ki_erkundung/lotse_status_json
```

Kommt kein Status: Teil A prüfen (läuft der Dienst, gleiche Domain?), sonst
Ende und Bericht.

### B3 – Kamera und LiDAR starten (keine Motoren)

```bash
nohup env --default-signal=INT ros2 launch robot_bringup oak.launch.py pointcloud:=false \
  > "$KI/oak.log" 2>&1 < /dev/null & echo $! > "$KI/oak.pid"
nohup env --default-signal=INT ros2 launch amadeus_lidar_bringup stl27l.launch.py publish_static_tf:=true \
  > "$KI/lidar.log" 2>&1 < /dev/null & echo $! > "$KI/lidar.pid"
sleep 20
timeout 12 ros2 topic hz /oak/semantic/rgb/compressed 2>&1 | tail -2
timeout 8 ros2 topic hz /scan 2>&1 | tail -2
timeout 8 ros2 topic echo --once /oak/semantic/camera_info | grep -A4 -E "^(width|height|k):" | head -14
top -b -n 1 | head -15
```

Erwartung: Bilder etwa 2 Hz, Scans etwa 10 Hz. Aus `k` (fx, Bildbreite) den
waagerechten Öffnungswinkel berechnen: `2 · atan(Breite / (2 · fx))`.

### B4 – eine Ansicht aufnehmen und die KI fragen

Für jede Ansicht `NAME` setzen (kurz, ohne Leerzeichen, zum Beispiel
`labor_tuer_vorn`). Amadeus steht still.

```bash
NAME=labor_tuer_vorn; cd ~/roboter_worktrees/selbstheilung-v2
python3 ki_erkundung/werkzeuge/blickrunde_aufnehmen.py --name "$NAME" --dauer 8 | tee "$KI/${NAME}_aufnahme.txt"
RUNDE=$(ls -d ~/.local/share/amadeus/ki_erkundung/blickrunden/${NAME}_* | tail -1); echo "$RUNDE"
python3 ki_erkundung/werkzeuge/trockenlauf.py --runden "$RUNDE" --ausgabe "$KI/${NAME}_ohne" \
  --ueber-ros --denken aus | tee "$KI/${NAME}_ohne.txt"
```

Nur wenn im A-Nachtrag N2 das Denken eine Antwort in höchstens 180 s
geliefert hat, zusätzlich:

```bash
python3 ki_erkundung/werkzeuge/trockenlauf.py --runden "$RUNDE" --ausgabe "$KI/${NAME}_mit" \
  --ueber-ros --denken an --zeitgrenze 180 | tee "$KI/${NAME}_mit.txt"
```

Mehrfaches Fragen derselben Frage ist entfallen: Die Wiederholungen kamen im
ersten Lauf aus dem Zwischenspeicher (1,3 s statt etwa 17 s) und sagen nichts
über die Wiederholbarkeit.

Danach Christopher das Blatt `$KI/${NAME}_ohne/${NAME}/uebersicht.jpg` zeigen
(das Foto mit den Nummern und die Skizze) und die Antworten der KI aus
`$KI/${NAME}_ohne.txt` nennen. Dann fragen, je einzeln, Antworten wörtlich
notieren:

1. Welche Nummern sind echte, offene Ausgänge, durch die Amadeus fahren könnte?
2. Was ist jede Nummer wirklich (offene Tür, geschlossene Tür, Durchgang, Glas, Spiegel, Lücke an Möbeln, Nische)?
3. War ein Ausgang im Bild zu sehen, der keine Nummer bekommen hat?
4. In welchem Raum steht Amadeus?

Daraus `wahrheit.json` in den Ordner der Runde schreiben (Form:
`{"ausgaenge": [2], "ausgang_sichtbar": true, "arten": {"1": "moebelspalt", "2": "tuer_offen"}, "raum": "…"}`;
erlaubte Arten: `tuer_offen`, `tuer_geschlossen`, `durchgang`, `glas`,
`spiegel`, `moebelspalt`, `nische`, `unklar`) und auswerten:

```bash
python3 ki_erkundung/werkzeuge/trockenlauf_auswerten.py \
  --ergebnis "$KI/${NAME}_ohne/ergebnis.json" --runden "$RUNDE" | tee "$KI/${NAME}_auswertung.txt"
```

### B5 – weitere Ansichten

B4 für bis zu fünf weitere Ansichten wiederholen, wenn Christopher Amadeus
von Hand umstellt oder dreht: zum Beispiel Tür von der Seite, Tür weiter
weg, Blick auf ein Fenster oder einen Spiegel, Blick in eine Zimmerecke ohne
Ausgang. Mindestens eine Ansicht mit der offenen Labortür ist nötig.
Zum Schluss die erste Ansicht noch einmal aufnehmen (Amadeus an dieselbe
Stelle, `NAME` mit Zusatz `_2`): Das ist die Wiederholbarkeit mit neuen
Bildern.

### B6 – beenden

```bash
kill -INT "$(cat "$KI/oak.pid")"; kill -INT "$(cat "$KI/lidar.pid")"; sleep 5; MY=$$
pgrep -af "ros2 launch|ldlidar|depthai" | grep -v "^$MY " || echo "keine Amadeus-Prozesse"
```

Danach Teil A6 auf dem KI-Rechner.

### Bericht Teil B

Datei `~/ki_erkundung_bericht_ki0.md`, ohne Bilder und ohne
Kartenkoordinaten:

1. Stand (HEAD), Testergebnis, benutzte Umgebung, Status des Lotsen-Dienstes.
2. Kamera und LiDAR: Bildrate, Scanrate, Bildgröße, `k`, berechneter
   Öffnungswinkel, die `top`-Zeilen.
3. Je Ansicht: Zeilen des Aufnahmewerkzeugs (Aufnahmen, „ohne Scan
   verworfen“, Montage aus TF oder Vorgabe); aus `ergebnis.json` die
   vermessenen Öffnungen (Nummer, Breite, Entfernung, Richtung, befahrbar);
   je Antwort Wahl, Einordnung jeder Nummer, Raumname, Begründung, gültig
   oder verworfen mit Grund, Sekunden, mit oder ohne Denken; aus
   `einstellungen.umgebung` Modell, Kennung, Fassung von Ollama.
4. Christophers Antworten wörtlich und die Ausgabe der Auswertung.
5. Die vermessene Breite der Labortür neben dem bekannten Maß (laut
   Christopher 850 mm).
6. Alles, was nicht lief, mit Meldung. Keine Deutung.

## Ende

Kein Commit, kein Push. Beide Berichte an Christopher.
