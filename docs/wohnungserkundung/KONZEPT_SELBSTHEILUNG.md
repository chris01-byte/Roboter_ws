# Amadeus – Konzept „Selbstheilender Erkundungsbetrieb“ (Entwurf)

**Stand:** 15.10.2026 · **Status:** vom Projektinhaber beschlossen; Softwareumsetzung gerätefrei geprüft, keine Realabnahme
**Anlass:** v17 A/B/C 0/3. Die Ursachen liegen überwiegend in Gates, die vorübergehende oder unkritische Zustände als Missionsende behandeln (Auswertung der Original-v17-Rohdaten vom Jetson, 14./15.10.2026).
**Leitsatz des Projektinhabers:** Ein Kundenroboter muss sich selbst heilen und darf den Gesamtprozess nur in Ausnahmen stoppen. Nicht erfasste Kartenzellen dürfen keine Blocker sein. Die VL53 dienen vorrangig dem Ausweichen, nicht dem Blockieren einer Fahrt.

---

## 1. Problem mit dem heutigen Konzept

Der AP06-Pfad verwendet **Beweisführung als Fahrerlaubnis**: Eine Bewegung ist nur erlaubt, wenn jede Zelle der gepolsterten Kontur entlang der ganzen Trajektorie beobachtet frei ist. Außerdem muss jede Quelle frisch sein und Karte, Status, Pose und Scope müssen exakt zusammenpassen. Scheitert ein Beweis, endet sehr oft die Mission.

Folgen, alle durch v17-Daten belegt:

| Mechanismus | Wirkung in v17 |
|---|---|
| Unbekannte Zelle in der Kontur = Verbot | A: Startfreigabe kippt durch eine 1-cm-SLAM-Korrektur (Rundung 0,2 nm); C: `start_egress_approaches_unknown` bei 0,708 m; Mastschatten macht die Zelle unter dem Roboter nie „beobachtet“ |
| Rechenbudget überschritten = Missionsende | B, C: 5,9 / 5,7 s gegen 5 s, Roboter steht dabei |
| Karte und Status nicht exakt gleichzeitig = Versuch verbraucht | HOLD: Status überholt Karte um ≈ 2 ms, nach drei Versuchen Ende |
| 76 verschiedene Abbruch-/Stale-Gründe, 45 `finish`-Ausgänge | Gesamterfolg = Produkt sehr vieler Einzelerfolge |

Kern des Fehlers: **Sicherheit wird in der Planungsebene erzwungen statt in der Reaktionsebene.** Das macht die Planung spröde, ohne die reale Sicherheit zu erhöhen. Was den Roboter tatsächlich vor Kollisionen schützt, sind `collision_monitor`, VL53, LiDAR-Kostenkarte, Watchdog und Not-Aus, nicht die Vollständigkeit der Karte.

## 2. Zielbild: drei Schichten mit klaren Rollen

```text
┌───────────────────────────────────────────────────────────────┐
│ 3. MISSION / EXPLORER   – entscheidet WOHIN                   │
│    weich: warten, neu planen, Ziel zurückstellen, eskalieren  │
│    bricht nur bei Ausnahmen (Abschnitt 4) ab                  │
├───────────────────────────────────────────────────────────────┤
│ 2. NAVIGATION (Nav2)    – entscheidet WIE                     │
│    plant optimistisch auch durch Unbekannt, weicht aus,       │
│    eigene Recovery (warten, neu planen, drehen, Spur zurück)  │
├───────────────────────────────────────────────────────────────┤
│ 1. REAKTIVE SICHERHEIT  – entscheidet OB JETZT                │
│    collision_monitor (VL53 + LiDAR), Watchdog, Frische,       │
│    Not-Aus. Einzige Schicht, die hart stoppen darf.           │
│    Ein Stopp hier ist ein PAUSIEREN, kein Missionsende.        │
└───────────────────────────────────────────────────────────────┘
```

Grundregeln:
1. **Stopp ist sicher, Abbruch ist teuer.** Jede Schicht darf jederzeit anhalten. Nur Schicht 3 darf eine Mission beenden, und nur aus den Ausnahmegründen in Abschnitt 4.
2. **Fehlende Information führt zu Vorsicht, nicht zu Verbot.** Unbekannte Zellen werden langsamer befahren und beobachtet. Sie verbieten die Fahrt nicht.
3. **Fehlende oder alte Sensordaten erlauben nie Bewegung**, beenden aber auch keine Mission: Der Roboter wartet auf frische Daten. Das bestehende Prinzip aus `INTEGRATIONSPLAN_DIAGNOSTIK_UND_SELBSTBEFREIUNG.md` §3.2 bleibt, nur die Folge ändert sich (warten statt beenden).
4. **Jede Heilung ist begrenzt** (Zeit, Anzahl, Weg). Erschöpfte Heilung führt zu „Hilfe benötigt“. Die Mission pausiert dabei und bleibt fortsetzbar.

## 3. Umgang mit unbekannten Zellen

| Ort | Heute | Neu |
|---|---|---|
| Unter dem Roboter am Start (Mastschatten, Eigenkörper) | Muss beobachtet frei sein, sonst `completion_raw_pose_not_observed_free` | Gilt als frei: Der Roboter steht dort. Die feste Startkörpermaske bleibt bis zum ersten Verlassen gültig |
| Hinter dem Roboter (Mastschatten 146–214°) | Muss für jede Drehung beobachtet frei sein | Drehung erlaubt, wenn der Drehkreis in der **Kostenkarte** nicht belegt ist. Unbekannt im Schatten zählt als „nicht belegt, Vorsicht“: langsame Drehung, Monitor aktiv |
| Vor dem Roboter im Fahrkorridor | Muss beobachtet frei sein | Darf befahren werden. Die VL53 sehen genau diesen Bereich (0,30–0,80 m) und lassen über die Kostenkarte ausweichen bzw. über den Monitor bremsen. Solange dieser Korridor nicht kartiert ist, fährt RPP absolut 0,06 m/s (Entscheidung 2) |
| Am Ziel/Frontier | Ziel muss bekannt frei sein | Ziel am Rand des Bekannten, Annäherung bis in Unbekannt erlaubt (klassisches Frontier-Prinzip) |
| Teilzell-/Rundungsdifferenzen | führen zu „neue unbekannte Zelle“ | Toleranz an der float32-Genauigkeit (Nachtrag N1) |

Technisch:
- Nav2-Planer `allow_unknown: true` für Erkundungsziele (`nav2_params_real.yaml:339`, heute `false`).
- Unbekannt in der globalen Kostenkarte erhält erhöhte, aber nicht tödliche Kosten. Bekannte Wege werden bevorzugt, Unbekanntes verbietet nichts.
- Lokale und globale Kostenkarte enthalten die VL53 (und OAK, sofern aktiv) bereits als Hindernisquellen (`nav2_params_real.yaml`, `obstacle_layer`). RPP prüft die volle Kontur gegen die lokale Kostenkarte und weicht damit aus; der Monitor stoppt erst als letzte Instanz. Bei der Umsetzung festgestellt, keine Änderung nötig.

## 4. Echte Ausnahmen: wann die Mission enden darf

Nur diese Gründe beenden die Mission (oder verlangen einen bewussten menschlichen Reset):

| Ausnahme | Verhalten |
|---|---|
| Not-Aus / Motor-Halt | sofort stoppen, verriegelt bis menschlicher Reset (unverändert) |
| Kollision erkannt bzw. unerwarteter Widerstand | stoppen, „Hilfe benötigt“ |
| Dauerhafter Ausfall von LiDAR, beiden VL53 oder Encodern (länger als Heilungsfenster, z. B. 30 s) | stoppen, „Hilfe benötigt“ |
| Aktor- und Modbusfehler, die nach Reconnect nicht verschwinden | stoppen, verriegelt (ein Motor-Halt sieht wie ein Modbusfehler aus, AGENTS §2.3) |
| Lokalisierung verloren und lokale Wiederfindung gescheitert | stoppen, „Hilfe benötigt“ |
| Missionsweites Heilungsbudget erschöpft (z. B. 10 Heilungen ohne Fortschritt oder 10 min ohne neuen Kartengewinn) | Teilkarte speichern, „Hilfe benötigt“ (fortsetzbar) |
| Nutzer bricht ab | `user_canceled` |
| Erkundung vollständig | `success` |

Alles andere (Rechenbudget, Frische nach Verarbeitung, Join-Rennen, Encoderlücke < Heilungsfenster, nicht erreichtes Ziel, abgelehnte Route, unterbrochener Rundblick, HWT-HOLD) ist **heilbar**.

## 5. Heilungsleiter

Jeder heilbare Fehler durchläuft eine begrenzte Eskalation. Jede Stufe beginnt im bestätigten Stillstand (beide Motoren 0 rpm, frische Odometrie).

| Stufe | Maßnahme | Beispiel | Grenze |
|---|---|---|---|
| H0 Warten | Stillstand halten, auf frische bzw. zusammenpassende Daten warten | Join-Rennen, alte Probe, Encoderlücke, HWT-HOLD | ≤ 5 s, dann H1 |
| H1 Neu rechnen | Auswahl oder Route mit aktuellen Daten wiederholen, bei Budgetende bestes bisheriges Ergebnis nehmen | Auswahlbudget, `route_invalidated` | 2× je Aufgabe |
| H2 Ziel zurückstellen | Aufgabe auf „später“ setzen, nächstes Ziel wählen | Ziel ohne Sicht am Stopp, wiederholt unerreichbar | Aufgabe max. 3× zurückgestellt, danach „unerreichbar“ markiert, nicht Missionsende |
| H3 Lokale Befreiung | langsame Drehung im nicht belegten Drehkreis, um Sicht zu gewinnen; kurze Vorwärtsetappe in bekannt freiem Raum | Start im Mastschatten, eingeengte Lage | 2× je Ort |
| H4 Spur zurück | langsam rückwärts **entlang der selbst gefahrenen Spur** (diese war nachweislich frei), max. 0,4 m, 0,05 m/s, nur gerader Spurabschnitt (≤ 3 cm seitlich) | Sackgasse, Engstelle ohne Drehraum | 1× je Stillstandsepisode; **freigegeben vom Projektinhaber am 15.10.2026** |
| H5 Hilfe | Stillstand, Teilkarte speichern, App-Meldung mit Grund und Vorschlag, „Weiter“ per App möglich | Budget erschöpft | – |

Nav2 bringt Teile davon fertig mit: Behavior-Tree-Recovery `Wait`, `ClearCostmap`, `Spin`, `BackUp`, Neuplanung. Heute fehlt im BT ein Retry-Knoten (`bt_orchestrator/bt_xml/explore.xml:19-23`).

## 6. Rolle der VL53

Entsprechend der Vorgabe und dem vorhandenen Aufbau:

| Funktion | Heute | Neu |
|---|---|---|
| Ausweichen | bereits Hindernisschicht beider Kostenkarten (bei Umsetzung festgestellt) | **Hauptrolle** bleibt: RPP plant über die lokale Kostenkarte um das Hindernis |
| Bremsen | `SlowZone` 0,30–0,80 m → 30 % | bleibt |
| Stoppen | `StopZone` 0,30–0,55 m | bleibt als letzte Reaktion; ein Stopp löst **H0 Warten → H1 Neu planen** aus, kein Missionsende |
| Fahrfreigabe des Explorers | `vl53_triplet_unmatched` u. a. sperren die Planung | Explorer prüft nur Frische/Ausfall (Abschnitt 4), keine Einzelzustände; Plausibilität macht der Monitor |
| Ausfall | stoppt | stoppt + wartet; erst nach Heilungsfenster Ausnahme |

## 7. Bessere Alternativen für Teile des Explorers

| Baustein | Heute | Alternative | Bewertung |
|---|---|---|---|
| Frontier-Auswahl | eigener metrischer Kern, Python, 5-s-Budget, Sichtprognose | einfache Frontier-Auswahl (Schwerpunkt/nächstgelegene Frontier, wie `explore_lite`), Auswahl in eigenem Prozess/Thread, Ergebnis „bestes bisher“ | weniger Rechenzeit, robust; Sichtprognose optional als Bewertung, nicht als Gate |
| Fahrfreigabe | Explorer beweist ganze Trajektorie | Nav2 plant, lokale Kostenkarte + Monitor sichern | Standard in ROS-2-Robotern; Explorer schrumpft stark |
| Startphase | private Egress-Inventare, Monotonieregel | Startprozedur: Rundumblick soweit Drehkreis frei, dann normale Navigation mit Vorsicht-Tempo | entfernt Fall A und C-Startgate |
| Karte/Status-Bindung | exakter Join, Versuchsverbrauch | Explorer liest Karte direkt, Status nur für Sitzung/Scope, Abweichung → H0 | entfernt HOLD-Abbruch |
| Rundblick | voller 2π mit Konturprüfung, 150-s-Frist | Teilschwenk über den Mastschatten (≈ 80°) bzw. Drehung bis Sichtgewinn | schneller, weniger Abbrüche |

Empfehlung: **Explorer auf „Wohin“ reduzieren**, Nav2 übernimmt „Wie“ und Recovery, Schicht 1 bleibt unverändert streng. Der vorhandene Code ist dabei nicht verloren. Kartenidentität, Persistenz, Mission-Manager, App, HWT-Fusion, Encoder-Odometrie und LiDAR-Normalisierung bleiben. Ersetzt bzw. entschärft werden vor allem die Gates in `metric_frontier_runtime.py` und `metric_egress_reference.py`.

## 8. Vorgehen (inkrementell, umschaltbar)

1. **Parameter `failure_policy: strict | self_healing`** (Default zunächst `strict`), damit beide Verhalten im selben Prüfstand verglichen werden können.
2. **Schnelle Fixes** (eigener Branch je Fix, roter Gegenfall vorher):
   - N1 float32-Toleranz (Fall A)
   - N2 Status-vor-Karte-Rennen (HOLD)
   - Budgetende im Stillstand → H1 statt Ende (B/C)
3. **Abbruchtaxonomie**: alle 45 `finish`-Ausgänge und die 76 Gründe in die Klassen *Ausnahme* (Abschnitt 4) bzw. *heilbar* (H0–H5) einordnen, als reine getestete Funktion.
4. **Unbekannt als Vorsicht**: `allow_unknown`, Kostenkarten-Kosten, Geschwindigkeitsdeckel; Start- und Abschlussprädikate ohne „beobachtet frei“-Pflicht unter dem Roboter.
5. **VL53 in der lokalen Kostenkarte**: bereits vorhanden, keine Änderung.
6. **Nav2-BT-Recovery** aktivieren (Wait, ClearCostmap, Spin; BackUp nur nach Entscheidung).
7. **Neue Abnahmekriterien** im Prüfstand: Mission erfolgreich trotz injizierter Störungen (Encoderlücke, Join-Rennen, Budget, VL53-Hindernis im Weg). Gemessen werden Zahl der Heilungen, Heilungsdauer und Endzustand.
8. **Reale Abnahmeleiter** wie im Analysebericht (motorlos → aufgebockt → Boden langsam), jede Stufe mit Freigabe und Not-Aus.

Sicherheitsrahmen bleibt unverändert: keine Aktoren ohne Freigabe, erst Stillstand, Not-Aus in Reichweite, Schicht 1 wird nicht gelockert.

## 9. Entscheidungen

| # | Frage | Stand |
|---|---|---|
| 0 | Selbstheilung statt Abbruch als Leitprinzip; Unbekanntes ist kein Blocker; VL53 vorrangig zum Ausweichen | **beschlossen 15.10.2026** |
| 1 | Begrenzte Rückwärtsfahrt entlang der eigenen Spur (H4) | **beschlossen 15.10.2026** |
| 2 | Geschwindigkeit, solange vor dem Roboter noch nicht kartiert ist | **beschlossen 15.10.2026: 0,06 m/s** (Nav2 `speed_limit`, Korridor 1,0 × 0,5 m, > 2 % unbekannt) |
| 3 | Heilungsbudget der Mission (Heilungen, Zeit ohne Kartengewinn) | offen; Startwerte 30 Heilungen / 600 s im Profil |
| 4 | „Hilfe benötigt“ mit „Weiter“ per App als zulässiger Missionsverlauf | offen; technisch: neue Explore-Mission setzt auf der aktuellen Karte fort |
| 5 | Explorer verschlanken oder nur Gates entschärfen | offen; umgesetzt ist beides als Option: neue Strategie `self_healing` und gezielte AP06-Korrekturen |
| 6 | Abnahmekriterien neu fassen (Robustheit vor 95 %-Referenzanteil) | offen |

## 10. Umsetzungsstand 15.10.2026 (Branch `claude/blissful-pasteur-s1eivj`)

Gerätefrei geprüft (ROS 2 Jazzy, Python 3.12, Cloud-Container). Keine Realfahrt,
kein Jetson-Install, keine Aktorwirkung.

| Teil | Umsetzung | Nachweis |
|---|---|---|
| Fall A (Start) | Gitterprüfung toleriert float32-Rundungsrest (1e-4 Zelle = 1 µm) statt Startfreigabe zu verwerfen | `test_metric_float32_lattice.py` (vorher rot) |
| HOLD-Fall | Status vor Rohkarte: laufende Arbeit hält das letzte exakte Paar im 1,25-s-Fenster | `test_metric_map_lifecycle.py` |
| B/C (Rechenzeit) | `metric_selection_budget_retries` (Default 0 = altes Verhalten) | `test_metric_selection_retry.py` |
| Neue Strategie | `exploration_strategy: self_healing` mit Heilungsleiter H0–H5, Spurrückfahrt über Nav2-BackUp | `test_self_healing.py`, `test_self_healing_runtime.py` |
| Nav2-Profil | `nav_mapping.launch.py self_healing:=true`: Planung durch Unbekanntes, leichte BT-Recovery, BackUp über Fahrtor/Glätter/Kollisionsmonitor, Rückwärts nur −0,05 m/s | `test_nav_real_contract.py` |
| VL53 | waren bereits Hindernisquellen beider Kostenkarten (lokales Ausweichen); unverändert | – |
| Tempo im Unbekannten | Explorer publiziert Nav2 `SpeedLimit` absolut 0,06 m/s, solange der Korridor vor dem Roboter (1,0 m, ±0,25 m) zu > 2 % nicht kartiert ist; ohne Karte/Pose fail-safe langsam; Freigabe am Missionsende | `test_self_healing*.py` |

Start im Labor (LAB-1, Not-Aus in Reichweite):

```bash
ros2 launch robot_navigation nav_mapping.launch.py self_healing:=true \
  active_drive:=true enable_auto_explore:=true
```

Rückfallweg: `self_healing:=false` (Default) startet exakt den bisherigen Explorer,
den recovery-freien Nav2-Baum und den abgetrennten Recovery-Ausgang.

Bekannte Grenzen: Die Rückfahrt sieht hinten keine neuen Hindernisse (Mastschatten,
VL53 nur vorn); sie ist deshalb auf die eigene, gerade, kurz zuvor befahrene Spur
begrenzt. Hindernisse unter etwa 12–14 cm sieht keine Sensorkette. Reale Wirkung
der Heilungsleiter ist unbelegt; die nächste Stufe ist eine motorlose Prüfung der
Topics/Parameter auf dem Jetson, danach eine begrenzte Laborfahrt.
