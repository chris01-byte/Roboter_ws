# HomeMy – lokale semantische Roboternavigation nach dem Mobility-VLA-Prinzip

**Projekt- und Entscheidungsdokumentation**  
**Stand:** 19. November 2026 · **Version:** 1.0 (Konzept/MVP)  
**Ziel:** Lokale KI-gestützte Zielsuche und autonome Navigation; spätere Erweiterung um Objektmanipulation.

> **Kernaussage:** Wir orientieren uns am hierarchischen Grundprinzip von Google DeepMinds *Mobility VLA*, bauen aber keine 1:1-Replik. Ein lokales multimodales Qwen-Modell versteht Sprache und RGB-Bilder, ein räumliches Gedächtnis verwaltet erkannte Orte und Objekte, OAK-D-Tiefenwerte ermöglichen 3D-Lokalisierung, und ROS 2/Nav2 übernimmt die tatsächliche Navigation und die kollisionsbewusste Bewegungsplanung. Die sicherheitskritische Regelung bleibt unabhängig von der KI.

## 1. Projektziel und Abgrenzung

### 1.1 Was HomeMy am Ende können soll

- Natürlichsprachliche Anweisungen interpretieren, etwa: „Fahre zu meiner Tasse auf dem Wohnzimmertisch.“
- Die Wohnung visuell/semantisch verstehen und Gegenstände mit Orten verknüpfen.
- Bekannte Objekte wiederfinden, zu ihnen navigieren und das Ziel vor Ort erneut verifizieren.
- Bei unbekannter oder veralteter Objektposition gezielt suchen, statt eine vermeintlich sichere Position zu erfinden.
- Später erkannte Gegenstände mit dem Roboterarm greifen und transportieren (eigenes Folgeprojekt).
- Ohne Cloud-Inferenz arbeiten; der KI-Rechner kann dabei stationär in der Wohnung stehen.

### 1.2 Bewusste Abgrenzung des ersten MVP

**Im ersten MVP:** Bildanalyse, strukturierte Zielentscheidung und 3D-Objektposition aus RGB-D-Daten; anschließend einfache Nav2-Anbindung. **Noch nicht:** vollautomatische Langzeitsuche in der gesamten Wohnung, vollständiger Open-Vocabulary-3D-Szenengraph, Greifplanung und autonomes Manipulieren, Fine-Tuning eines eigenen VLM.

**Kein direktes VLM-Motorinterface:** Qwen gibt keine PWM-, Radgeschwindigkeits- oder ungültig geprüften Navigationsbefehle aus. Es empfiehlt ein *semantisches Ziel*, das eine deterministische Softwareschicht validiert und in einen erreichbaren Anfahrpunkt übersetzt.

## 2. Status der Erkenntnisse und Entscheidungen

Die Kennzeichnungen verhindern, dass Empfehlungen fälschlich als bereits implementiert gelten.

| Status | Punkt | Begründung / Bemerkung |
|---|---|---|
| **Bestätigte Hardware** | NVIDIA RTX 3090 mit **24 GB VRAM** ist als lokaler KI-Rechner vorhanden. | Ausreichend Spielraum für ein quantisiertes VLM der 8–9B-Klasse; der tatsächliche Bedarf hängt von Kontext, Bildern und Runtime ab. |
| **Bestätigter Stand** | Es ist **noch kein Qwen-Modell installiert**; die Modellauswahl ist offen. | Wahl kann konsequent nach Bildverstehen, VRAM und Latenz erfolgen. |
| **Geplantes Sensorsystem** | OAK-D mit RGB-Kamera und Stereo-Tiefe für HomeMy. | RGB für Semantik; Tiefe für metrische Objektpositionen. |
| **Architekturentscheidung** | **Lokales VLM + klassische Navigation** statt End-to-End-Aktionserzeugung. | Bessere Prüfbarkeit, Austauschbarkeit und Sicherheit. |
| **Architekturentscheidung** | RTX 3090 zunächst **stationär**; Onboard-Rechner bleibt auf HomeMy. | Reduziert Energie-, Kühlungs- und Gewichtsbedarf auf dem fahrenden Roboter. |
| **Empfohlener Modellstart** | **Qwen3.5-9B**, zunächst quantisiert über **Ollama**. | Verfügbares multimodales Modell, praxisgerechte Größe; muss auf realen Wohnungsbildern getestet werden. |
| **Vergleichskandidat** | Qwen3-VL-8B-Instruct. | Sinnvolle Benchmark-Alternative. |
| **Geplante Robotik-Basis** | ROS 2, Nav2, `tf2`, Odometrie und geeignete Lokalisierung/SLAM. | Robuste metrische Navigation unabhängig von Qwen. |
| **Noch offen** | Genauer OAK-D-Typ, ROS-2-Distribution, Odometrie/SLAM, LiDAR-Einbindung, Rechner-/Netzwerkanbindung. | Vor Hardwareintegration festlegen und durchmessen. |
| **Noch offen** | Struktur der Objekt-Datenbank, Zieldefinition, Tests/Schwellenwerte. | Werden im MVP erarbeitet. |

## 3. Was wir von Google Mobility VLA übernehmen

**Referenz:** *Mobility VLA: Multimodal Instruction Navigation with Long-Context VLMs and Topological Graphs* (arXiv:2407.07775; CoRL 2024, Proceedings 2025).

### 3.1 Kernidee der Forschung

1. Eine Umgebung wird vorher visuell erkundet und als räumlich verknüpfte Beobachtungen organisiert.
2. Ein Vision-Language-Modell interpretiert eine multimodale Anweisung und wählt ein passendes semantisches Ziel.
3. Eine **separate** topologische/niedrigstufige Navigation fährt dieses Ziel an.

Die ursprüngliche Arbeit demonstriert, dass eine RGB-basierte Architektur für semantische Zielnavigation genügen kann. Sie ist **kein Nachweis**, dass für HomeMys präzises Greifen oder metrische 3D-Objektlokalisierung ebenfalls RGB allein die beste Wahl wäre.

### 3.2 Was wir bewusst anders machen

| Originalidee | HomeMy-Umsetzung |
|---|---|
| Großes VLM für Zielauswahl (im Paper u. a. Gemini) | Lokales Qwen3.5-9B (erste Wahl; noch zu benchmarken) |
| Langer Erkundungskontext mit vielen Bildern | Selektierte aktuelle Bilder + abrufbares semantisches Gedächtnis |
| Topologische Graphnavigation | Für den MVP ROS 2/Nav2 mit metrischer Karte; ein semantischer Raumgraph kann später ergänzt werden |
| RGB-basierte Zielerkennung | RGB **und** OAK-D-Tiefe, sobald konkrete 3D-Positionen relevant sind |
| Navigation als Demonstrationsziel | Später Navigation **plus** Greifaufgaben in HomeMy |

**Wichtig:** Eine Nav2-Karte ersetzt nicht automatisch das semantische Objektgedächtnis, und ein Objektdetektor ersetzt keine sichere Fahrregelung.

## 4. Zielarchitektur – Komponenten und Datenfluss

```text
Nutzer: Sprache/Text (z. B. „Fahre zur Tasse“)
                   |
                   v
          [Orchestrierung / ROS 2]
                   |
      +------------+-------------------------+
      |                                      |
      v                                      v
[OAK-D RGB-Bild]                      [Objektspeicher]
      |                                - ID / Klasse
      v                                - Ort / Raum
[Qwen3.5-9B, RTX 3090]               - Zeitstempel
 - Sprache + Bild                     - Konfidenz
 - Referenzen/Semantik                      |
 - strukturierte Zielhypothese <------------+
      |
      v
[Validator / Zielauflösung]
 - existiert Ziel? Daten aktuell?
 - Pose in map-Koordinaten?
 - erreichbarer Anfahrpunkt?
      |
      +<--- [OAK-D Tiefe + Kalibrierung + tf2]
      |
      v
[ROS 2 Nav2 / Lokalisierung / Costmaps]
      |
      v
[HomeMy Antrieb + Hindernisvermeidung]
      |
      v
[Ankunft: erneutes RGB-D-Prüfbild / ggf. Suche]
```

### 4.1 Verantwortlichkeiten

| Komponente | Verantwortlich für | Nicht verantwortlich für |
|---|---|---|
| **Qwen (VLM)** | Sprache, Bildinhalt, räumliche Alltagssemantik, Zielhypothesen | präzise 3D-Messwerte, sichere Motorregelung, SLAM |
| **OAK-D/DepthAI** | RGB-Aufnahmen, Stereo-Tiefenkarte, bildsynchronisierte Sensordaten | semantische Langzeitplanung |
| **Detektion/Segmentierung** | Objektauswahl bzw. Bildmaske/Bounding Box; im MVP ggf. manuell/vereinfacht | sichere Roboterbewegung |
| **3D-Lokalisierung + `tf2`** | Tiefenwerte zu Objektpose im Kamera-, Roboter- und Kartenframe umrechnen | semantische Interpretation |
| **Semantischer Speicher** | Objekte, Räume, Positionen, letzte Sichtung, Vertrauensniveau | Hindernisvermeidung |
| **ROS 2/Nav2** | erreichbare Zielpose, Pfadplanung, lokales Ausweichen, Fahrt | Interpretation offener Sprachbefehle |
| **Sicherheitsfunktionen** | Stopp, Geschwindigkeits- und Bewegungsgrenzen, Kommunikationsausfall | generatives Reasoning |

### 4.2 Verteilung über zwei Rechner

- **Stationärer KI-PC (RTX 3090):** Ollama/Qwen, semantische Inferenz, ggf. speicherintensive Detektion/Segmentierung und Objektgedächtnis.
- **HomeMy-Onboard-Rechner:** OAK-D-Anbindung, ROS-2-Sensordaten, Odometrie, Lokalisierung, Nav2 und die lokale sichere Steuerung.
- **LAN:** Bilder/Ergebnisse zwischen Roboter und KI-PC. Bei Verbindungsabbruch muss der Roboter selbstständig sicher anhalten bzw. in einem klar definierten Zustand bleiben. Keine Cloud notwendig; LAN-Latenz und Robustheit testen.

## 5. Warum wir OAK-D-Tiefe verwenden

### 5.1 Antwort auf die zentrale Frage

**Für das reine semantische Erkennen eines Zieles ist Tiefe nicht zwingend erforderlich.** Qwen kann auf RGB-Bildern eine Tasse erkennen und beschreiben. **Für metrische 3D-Objektposition, einen präzisen Anfahrpunkt und späteres Greifen ist Tiefe jedoch sehr nützlich.** Deshalb lautet der Architekturvorschlag: *RGB und Tiefenmessung parallel, aber funktional getrennt verarbeiten.*

| Aufgabe | RGB allein | Zusätzliche Tiefe |
|---|---|---|
| Tasse als solche erkennen | Ja, mit VLM/Detektor | nicht erforderlich |
| „Tasse auf dem Tisch“ semantisch verstehen | Ja | optional |
| Zu bekanntem Raum navigieren | Mit Lokalisierung und Karte möglich | optional |
| Entfernung und 3D-Position bestimmen | nur indirekt/zusätzliche Geometrie | direkt aus kalibrierten Daten näherungsweise messbar |
| Hindernisse räumlich erfassen | begrenzt | hilfreich, aber kein alleiniger Sicherheitsnachweis |
| Greifpose und Reichweite planen | zusätzlicher 3D-Sensor nötig bzw. komplex | stark empfohlen |

### 5.2 Technischer Ablauf einer 3D-Objektmessung

1. Kalibrierte RGB-Aufnahme und **auf RGB ausgerichtete** Tiefenkarte aufnehmen; Zeitstempel prüfen.
2. Objekt detektieren/segmentieren; bevorzugt Tiefenwerte aus einer **Objektmaske** nutzen, nicht blind nur den Mittelpunkt einer Bounding Box.
3. Ungültige Ausreißer und Hintergrundpixel entfernen, robusten Tiefenwert/3D-Punkt oder Punktwolke bestimmen.
4. Für Pixel \((u,v)\), Tiefe \(Z\) und Intrinsics \((f_x,f_y,c_x,c_y)\):

   \[
   X=(u-c_x)Z/f_x,\qquad Y=(v-c_y)Z/f_y,\qquad Z=Z.
   \]

5. Mit extrinsischer Kalibrierung und `tf2` von `camera_frame` nach `base_link` und `map` transformieren; Unsicherheit mitführen.
6. **Nicht direkt auf den Objektmittelpunkt zufahren:** sicheren, erreichbaren Anfahrpunkt vor dem Objekt erzeugen und über Nav2 prüfen.

**Grenzen der Stereotiefe:** reflektierende/transparente Oberflächen, geringe Textur, ungünstiges Licht, Okklusion und Mindestmessabstand. Für eine Tasse kann ein Teil der Messwerte ungültig sein; eine robuste Schätzung aus mehreren Pixeln/Ansichten ist erforderlich. Bei späterer Greifmanipulation ist zusätzliche Nahbereichsverifikation sinnvoll.

## 6. KI-Modell, RTX 3090 und Inferenz

### 6.1 Startmodell

**Empfehlung: Qwen3.5-9B**, quantisiert und über **Ollama** ausgeführt. Die öffentlich verfügbare Ollama-Variante verarbeitet Text und Bilder; die ausgewiesene Modellgröße liegt je nach Variante/Quantisierung ungefähr bei **6,6–7,6 GB als Modellartefakt**. Das ist **nicht** der gesamte GPU-Verbrauch: Kontext/KV-Cache, Bild-Token, Laufzeit und weitere Modelle kommen hinzu.

Alternative zum Vergleich: **Qwen3-VL-8B-Instruct**. Die endgültige Auswahl erst nach Messungen mit Originalbildern aus der Wohnung treffen.

### 6.2 Warum kein größeres Modell von Beginn an?

- 24 GB VRAM sind komfortabel für ein einzelnes quantisiertes 8–9B-VLM, aber **keine Garantie** für beliebige Kontexte, Bildmengen oder parallele Modelle.
- Ein kleineres Modell ermöglicht häufig geringere Antwortlatenz, einfacheres Debugging und reproduzierbare Tests.
- Der begrenzende Faktor ist nicht nur die Semantik, sondern auch Datenqualität, Zielvalidierung, Mapping und Integration.
- Für den ersten Prototyp ist **kein Fine-Tuning** nötig. Erst dokumentierte Fehler rechtfertigen Distillation/Fine-Tuning.

### 6.3 Erste Installation und Prüfung (Ubuntu)

```bash
# NVIDIA-Treiber/GPU prüfen
nvidia-smi

# Ollama installieren (Installationsskript vor Ausführung prüfen)
curl -fsSL https://ollama.com/install.sh | sh

# Multimodales Startmodell
ollama run qwen3.5:9b
```

Die spätere Integration erfolgt über eine lokale API. Für Bilder werden die Eingaben zunächst als Einzelbilder bzw. gezielte Snapshots übergeben; **kein ungefilterter Dauer-Videostream** an Qwen.

### 6.4 Vorgeschlagener strukturierter Rückgabevertrag

```json
{
  "target_label": "Tasse",
  "semantic_location": "Wohnzimmertisch",
  "candidate_object_id": "cup_014",
  "reason": "Letzte Sichtung im Wohnzimmer, Bild passt zum Befehl",
  "needs_visual_confirmation": true
}
```

Dieser Vertrag liefert **nur eine Zielhypothese**. Die tatsächliche Pose, Aktualität, Plausibilität, Erreichbarkeit und Sicherheitsfreigabe muss die deterministische ROS-2-Schicht prüfen. Ein vom Modell generierter `confidence`-Wert ist **nicht automatisch kalibriert**.

## 7. Semantisches Objektgedächtnis und Aktualität

Empfohlener einfacher MVP-Datensatz pro Objekt:

| Feld | Bedeutung |
|---|---|
| `object_id`, `class`, `aliases` | Wiedererkennung und natürliche Sprache |
| `room_id`, `support_surface` | Raum und Trägerobjekt, z. B. „Wohnzimmer“, „Tisch“ |
| `pose_map`, `pose_covariance` | Räumliche Lage plus Unsicherheit |
| `last_seen_at`, `last_seen_pose` | Zeitpunkt und Ort der letzten bestätigten Beobachtung |
| `source_frame`, `observation_id` | Nachvollziehbarkeit der Sensordaten |
| `status` | `confirmed`, `stale`, `unknown`, ggf. `moved` |

Start mit **SQLite + einfachen räumlichen/semantischen Beziehungen**. ConceptGraphs später als Forschungsreferenz prüfen, jedoch nicht von Beginn an vollständig nachbauen.

**Beispiel Veralten:** Wurde eine Tasse zuletzt vor 20 Minuten gesehen und inzwischen möglicherweise weggeräumt, ist die historische Position eine *Suchhypothese*, keine aktuelle Gewissheit. Bei negativer Vor-Ort-Prüfung Position aktualisieren oder Suchroutine einleiten.

## 8. Entwicklungsplan mit prüfbaren Ergebnissen

### M0 – Baseline und Benchmark

- GPU/Treiber/Ollama/Qwen3.5-9B installieren.
- 20–50 repräsentative Wohnungsbilder erfassen (verschiedene Lichtbedingungen, Objekte, Okklusionen).
- Qwen nach Objekten, Orten, Zielreferenzen fragen; Antwort als JSON validieren.
- **Abnahme:** Wiederholbarer Testdatensatz, Fehlerliste, mittlere/p95-Latenz, reproduzierbare Modellkonfiguration.

### M1 – OAK-D RGB-D und 3D-Lokalisierung

- RGB-/Tiefen-Alignment, Kalibrierung und synchronisierte ROS-2-Topics.
- Objektmaske/Bounding Box mit robuster Tiefenaggregation kombinieren.
- `camera -> base_link -> map` sauber dokumentieren.
- **Abnahme:** Objekte mit plausibler Pose und Fehlerabschätzung in definierten Testfällen.

### M2 – Karte, Lokalisierung und Nav2

- Odometriedaten + geeignete 2D-/3D-Lokalisierung/SLAM, Navigationskarte, Costmaps.
- Statische Zielpunkte über `NavigateToPose` sicher anfahren; Hindernis-/Verbindungsabbruch testen.
- **Abnahme:** Wiederholbar stabile Navigation zu manuellen Testzielen ohne VLM.

### M3 – Semantisches Gedächtnis und End-to-End-Zielnavigation

- Objekte/Räume speichern, aktualisieren und mit Zeitstempeln versehen.
- Qwen-Zielhypothesen deterministisch in eine geprüfte Anfahrpose überführen.
- Vor Ort Ziel erneut über RGB-D verifizieren und Erfolg/Fehler protokollieren.
- **Abnahme:** Befehl „Fahre zur Tasse“ funktioniert in mindestens einem kontrollierten Szenario wiederholbar.

### M4 – Umgang mit Ungewissheit und autonome Suche

- Fehlende/veraltete Objekte erkennen; Suchorte priorisieren.
- Literaturansätze aus VLFM/LocalNav sowie mögliche Frontier-Exploration evaluieren.
- Später Arm/Greifer, Greifpose und Objekttransport als eigenes Teilprojekt.
- **Abnahme:** Bei nicht auffindbarer Tasse wird kontrolliert gesucht oder sauber „nicht gefunden“ gemeldet; keine erfundene Erfolgsmeldung.

### Kennzahlen

- **Semantische Trefferquote:** richtige Zielidentifikation / gültige Befehle.
- **3D-Lokalisierungsfehler:** Abstand zur gemessenen Ground Truth; Ausfallrate der Tiefenschätzung.
- **Navigations-Erfolgsquote:** Ziel erreicht und vor Ort bestätigt.
- **Latenz:** Bildaufnahme → Qwen-Antwort → validierte Zielpose (Median/p95).
- **Robustheit:** Verhalten bei Verdeckung, falscher Karte, veralteter Objektposition, fehlendem LAN.
- **Sicherheit:** Stopp und Begrenzungen unabhängig von VLM-Antworten nachweisbar.

## 9. Risiken und Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| Qwen halluziniert einen Zielort oder ein Objekt | Nur strukturierte Hypothesen, ID-/Zeit-/Plausibilitätsprüfung, Wiederaufnahme vor Ort |
| Stereotiefe unzuverlässig | Maske, robuste Pixelaggregation, Messunsicherheit, mehrere Ansichten, Ausfallzustand |
| RTX 3090 überlastet bei vielen Bildern | Bildauswahl, Auflösungsbegrenzung, Quantisierung, Kontextbudget und Inferenz-Benchmark |
| LAN oder stationärer PC fällt aus | Onboard-Failsafe; sichere Navigation/Stopp ohne KI-PC |
| Hindernis oder Mensch wird nicht erkannt | Costmaps/Sensorfusion und unabhängige Schutzmechanismen; kein Sicherheitsversprechen allein durch VLM |
| Historische Objektposition veraltet | Zeitstempel, Status `stale`, Zielbestätigung und aktualisierte Datenbank |
| Komplexität von ConceptGraphs zu hoch | Start mit schlankem SQLite-Speicher; schrittweise Graph-/Embeddings-Erweiterung |

## 10. Noch konkret zu entscheiden

1. **OAK-D-Modell und Firmware/DepthAI-Version:** genauer Kameratyp, RGB-/Depth-Auflösung, Framerate, Mindestabstand.
2. **Onboard-Plattform:** CPU, ROS-2-Distribution, Netzwerkarchitektur, Energieversorgung.
3. **Lokalisierung:** Radodometrie/IMU/LiDAR vorhanden? Welches SLAM-Verfahren und welche Kartenauflösung?
4. **Detektion:** Zunächst Qwen-Bildreferenz, zusätzlicher Detector (z. B. Grounding DINO) oder Segmentierer? Auf der 3090 getrennt benchmarken.
5. **Object-Store:** Datenbankschema, Poseunsicherheit, Aufbewahrungsdauer, Referenzrahmen.
6. **Testbedingungen:** Ground-Truth-Methode, Messstrecken, erlaubte Geschwindigkeiten, Abbruchkriterien.

## 11. Forschungsarbeiten und technische Dokumentation

**Wissenschaftliche Primärquellen**

1. **Mobility VLA – Multimodal Instruction Navigation with Long-Context VLMs and Topological Graphs.** Google DeepMind; arXiv 2024 / CoRL 2024, Proceedings of Machine Learning Research 2025. https://arxiv.org/abs/2407.07775 · HTML: https://arxiv.org/html/2407.07775 · Konferenz: https://proceedings.mlr.press/v270/xu25b.html
2. **LocalNav – Distilling Frontier VLMs and Embodied RL for On-Device Object Goal Navigation.** Baumann et al., 2026. Lokale Objektnavigation mit einem 4B-VLM (im Paper u. a. Qwen3.5-4B). https://arxiv.org/abs/2606.27871
3. **ConceptGraphs – Open-Vocabulary 3D Scene Graphs for Perception and Planning.** 2023/2024. Objektzentrierte 3D-Szenengraphen aus Bildbeobachtungen. https://arxiv.org/abs/2309.16650 · Code: https://github.com/concept-graphs/concept-graphs
4. **VLFM – Vision-Language Frontier Maps for Zero-Shot Semantic Navigation.** 2023/2024. Frontier-Suche mit RGB-Semantik und Depth-basierter Occupancy Map. https://arxiv.org/abs/2312.03275 · Code: https://github.com/rai-opensource/vlfm

**Technische Primärdokumentation**

5. **Ollama – Qwen3.5-9B:** https://ollama.com/library/qwen3.5:9b
6. **Luxonis – Stereo Depth:** https://docs.luxonis.com/hardware/platform/depth/configuring-stereo-depth
7. **Luxonis – RGB/Depth Alignment:** https://docs.luxonis.com/software/depthai/examples/rgb_depth_aligned
8. **ROS 2 Nav2:** https://docs.nav2.org/

---

## 12. Ein-Satz-Projektentscheidung

**HomeMy erhält eine lokale, hierarchische Robotik-KI: Qwen interpretiert Sprache und Bilder auf dem stationären RTX-3090-Rechner; OAK-D liefert RGB-D für reale 3D-Objektpositionen; ein versioniertes semantisches Gedächtnis verwaltet Orte und Unsicherheiten; ROS 2/Nav2 navigiert eigenständig, während sicherheitsrelevante Steuerung unabhängig von Qwen bleibt.**

*Hinweis: Dies ist ein Architektur- und Entwicklungsplan. Die beschriebenen Fähigkeiten sind noch nicht implementiert oder praktisch verifiziert. Genannte Modellgrößen sind keine zugesicherten Laufzeitwerte.*
