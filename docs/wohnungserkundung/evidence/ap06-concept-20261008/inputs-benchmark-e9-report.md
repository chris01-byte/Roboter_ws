# Rechenkosten von `_metric_inputs_locked`, 08.10.2026

20 Aufrufe der unveränderten installierten Implementierung
`e9f4506c596a133de1374ee1388eb1e9f14c457a`: zwei Initialisierungsaufrufe,
zehn ohne Profiler und acht mit cProfile. Humble-Container `ap03-nav2`,
CPU-Affinität `0,1` wie der ursprüngliche Produktgraph, OMP/OpenBLAS jeweils 1.
Während der Messung liefen weder Gesamtmission noch parallele Builds/Tests.

Die unveränderten finalen Rohkarten-/Costmap-CDRs aus `joined-a` enthalten
jeweils 284 × 564 Zellen. TF2 komponierte aus der tatsächlichen aufgezeichneten
TF-Kette die letzte gemeinsame Pose
`[0.7915008905, 0.1715616471, 1.4427990472]` und Referenz
`[0.0002199585, -0.0073911765, 0.0069800000]`.
Die zulässige Scopegeometrie entspricht dem ursprünglichen Harness.

| Unprofilierter Ablauf | Mittel | Median | Maximum |
|---|---:|---:|---:|
| Unveränderte Projektion, bestehende Memo verwendbar | 22,59 ms | 22,52 ms | 23,09 ms |
| Nur Projektionsmemo vor jedem Aufruf verworfen | 23,52 ms | 23,53 ms | 24,55 ms |

Kumulierte cProfile-Zeit pro Aufruf in der ersten Variante:

| Funktion | Zeit | Anteil an Profiler-Gesamtzeit |
|---|---:|---:|
| `known_safe_mask` | 9,58 ms | 39,2 % |
| `rasterize_scope`, beide Aufrufe zusammen | 8,75 ms | 35,8 % |
| `_metric_prepare_egress` | 8,63 ms | 35,3 % |
| `self_body_unknown_mask` | 1,56 ms | 6,4 % |
| `footprint_clear`, beide Aufrufe zusammen | 1,26 ms | 5,2 % |
| `_validated_snapshot`, beide Raster zusammen | 1,02 ms | 4,2 % |
| `map_snapshot_fingerprint`, drei Aufrufe zusammen | 0,73 ms | 3,0 % |

Die kumulierten Kategorien sind verschachtelt und dürfen **nicht addiert**
werden. Insbesondere liegt Scope-Rasterisierung innerhalb anderer aufgeführter
Funktionen. Kalte Projektionsmemos erhöhen den gemessenen Mittelwert nur um
etwa 0,93 ms. Hier dominiert keine langsame Fingerprintvalidierung.

Dieser unbelastete Mikrobenchmark erklärt die im Gesamtlauf abgelaufene
0,5-s-Scanfrist nicht allein. Dafür fehlen im alten Lauf die genaue
Scanempfangszeit beim Auswählen und die Verarbeitungs-/Schedulingverzögerung
des tatsächlich verworfenen Eingangsobjekts. Aus 22–25 ms Rechenkosten folgt
keine Echtzeitgarantie für einen gleichzeitig laufenden ROS-Graphen.

## Grenzen

- Dies ist ausschließlich eine Offline-Kostenmessung, kein Missionsergebnis,
  Quellenfrischebeweis oder Hardwaretest. Keine Nodes, Publisher oder Aktoren
  wurden gestartet; kein Produktcode wurde geändert.
- Das bestehende `body_input_fixture` erzeugt eine Explorerinstanz ohne
  Nodekonstruktor. Die Auswertungsuhren sind ausdrücklich eingefrorene
  Fixturewerte. Die originalen CDR-/TF-Stempel bleiben unverändert.
- Der fehlgeschlagene Eingang selbst wurde nicht serialisiert; verwendet
  werden finale Raster und finale tatsächliche TF-Pose. Das private
  Egressinventar war laut Laufstatus bereits leer. Der Benchmark rekonstruiert
  diese leere Phase und assertiert leere feste, zurückbehaltene und projizierte
  Inventare sowie gültige Nachweise. Historische Egressobjekte werden nicht
  als exakt rekonstruierter Missionszustand ausgegeben.
- Die kalte Variante verwirft nur das Memo des vorhandenen Objekts, verändert
  weder Zellen noch Berechtigung. Sie simuliert keine beliebige neue Karte.
- cProfile hat eigenen Aufwand; für Laufzeitwerte zählen die getrennten
  unprofilierten Messungen. Die gespeicherten `.prof`-Dateien dienen der
  relativen Zuordnung.

## Reproduktion und gebundene Dateien

Bei unverändertem, geprüftem e9-Produktoverlay und ohne konkurrierende Last:

```bash
docker exec ap03-nav2 bash -c '
source /evidence/ap06-missions-20261005/old-whole-setup.sh
export PYTHONDONTWRITEBYTECODE=1 ROS_DOMAIN_ID=194
exec taskset -c 0,1 python3 \
  /evidence/ap06-concept-20261008/benchmark_metric_inputs.py \
  --output /evidence/ap06-concept-20261008/inputs-benchmark-e9-repeat'
```

Jeder neue Lauf benötigt ein neues Ausgabeverzeichnis. Das Skript bindet die
tatsächlich importierten installierten Module und alle verwendeten
Eingabedateien vor der Messung mit SHA-256; ein inzwischen ersetztes Overlay
wäre ein anderer Vergleichskandidat.

`inputs-benchmark-e9/result.json` enthält Einzelzeiten, TF-Pose, Maskengrößen,
Quell-/Rasterhashes, Profileranteile und Grenzen. `steady.prof/.txt` und
`cold_projection.prof/.txt` enthalten die vollständigen Profile.
`inputs-benchmark-e9-sources/` bewahrt alle sieben profilierten
Produkt-Pythonquellen sowie das bestehende Fixture auf; ihre Bytes wurden
gegen den genannten Commit und die tatsächlich gemessenen Installationshashes
geprüft. `inputs-benchmark-e9-SHA256SUMS` bindet Skript, Ergebnis, Log,
Profilerdateien und diese Quellsnapshots.

Die gemessene Runtime hatte SHA-256:
`aa5f18db87891793a749d59e2940542d4336e12b3864727e0059d238332ba8ca`.
