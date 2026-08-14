# llm_planner — Sprach-/Aufgabenplaner (WP-5, Baustein C)

Übersetzt **natürliche Sprache** in einen Missionsauftrag im **bestehenden
`command_json`-Format** des `mission_manager` – und schickt ihn dorthin. Der
`mission_manager` bleibt dadurch **unverändert**; der Planer hängt sich davor.

> Läuft **offboard** auf dem KI-Server. **Asynchron/High-Level – nie im Echtzeit-Regelkreis.**

## Ablauf

```
"Bring mir die Tasse aus der Kueche"
        │  /llm_planner/instruction (String)
        ▼
  [ llm_planner ]  ──Ollama──▶  LLM  ──▶  {"type":"pick_and_place","object":"Tasse", ...}
        │  /mission_manager/command_json
        ▼
  [ mission_manager ]  (unverändert)
```

## Schnittstellen

| Rolle | Topic | Typ |
|---|---|---|
| Eingang | `/llm_planner/instruction` | `std_msgs/String` (Klartext) |
| Ausgang | `/mission_manager/command_json` | `std_msgs/String` (JSON-Auftrag) |
| Status | `/llm_planner/status_json` | `std_msgs/String` |

## LLM-Backend (Ollama)

Standard ist ein **lokales LLM über Ollama**. **Empfohlenes Modell: `qwen2.5`**
(stark bei JSON-Ausgabe und Deutsch; Alternativen: `llama3.1`, `mistral`; sparsam: `qwen2.5:3b`).
Auf dem Server einrichten:
```bash
# Ollama installieren (siehe ollama.com), dann Modell holen:
ollama pull qwen2.5
# Ollama-Dienst läuft üblicherweise automatisch auf Port 11434.
```
Ist Ollama nicht erreichbar oder `use_ollama:=false`, nutzt der Node einen
**regelbasierten Fallback** (Schlüsselwörter) – so ist er auch ohne LLM testbar.

## Start & Test

```bash
ros2 launch llm_planner llm_planner.launch.py
```
In einem zweiten Terminal eine Anweisung senden:
```bash
ros2 topic pub --once /llm_planner/instruction std_msgs/msg/String \
  "{data: 'Erkunde bitte die Wohnung'}"

ros2 topic pub --once /llm_planner/instruction std_msgs/msg/String \
  "{data: 'Bring mir die Tasse aus der Kueche auf den Tisch'}"
```
Ergebnis beobachten:
```bash
ros2 topic echo /mission_manager/command_json
ros2 topic echo /llm_planner/status_json
```

## Parameter

Alle in [config/llm_planner_params.yaml](config/llm_planner_params.yaml) (mit Index).
Der statische **Fallback-Katalog** (`rooms`/`targets`/`objects`) muss konsistent
mit `mission_manager/config/mission_catalog.yaml` bleiben. Standardmaessig
abonniert der Planer zusaetzlich `/semantic/catalog_json`: manuell bestaetigte
Raeume aus dem `semantic_map_manager` ersetzen dann nur die Raumliste.
Fehlende, leere, uebergrosse oder ungueltige Meldungen lassen den Fallback
unveraendert. Akzeptiert werden ausschließlich `schema_version:1`,
`source:"semantic_map_manager"`, höchstens 256 Räume mit Namen bis 80 Zeichen
und insgesamt höchstens 512 KiB. `objects` und `targets` bleiben statisch und
können über den offenen Katalog-Topic nicht erweitert werden. Auch
`pick_and_place` wird weiterhin nur gegen die beim Start konfigurierte
statische Raumliste validiert; manuell gezeichnete Räume gelten ausschließlich
für das später separat freizugebende `go_to_room`.

## Grenzen / offen

- In ROS noch nicht kompiliert/getestet; `py_compile` bestanden.
- Der System-Prompt ist auf die aktuellen Befehle zugeschnitten; bei neuen
  Auftragstypen Prompt **und** `_validate()` erweitern.
- Optional: Antwort-Kanal an die GUI (Rückfrage bei unklarer Anweisung).
