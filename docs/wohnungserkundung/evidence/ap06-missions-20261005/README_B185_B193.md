# AP-06: Umsetzung der Reviewkorrekturen am 07.10.2026

Basis `7934a28`, Produktkorrektur `7fabf80`, MASTERPLAN v1.3 und
Originalszenariomanifest unverändert. Software-/Simulationsarbeit; kein Jetson,
keine Hardware, kein Deployment. Aktueller Gesamtstatus ausschließlich im
[STATUS](../../STATUS.md).

## Gemessene Ursache und Reparatur

B185 erfasst bei 2 cm 553 tatsächliche normalisierte Scans sowie die vollständige
empfangene TF-Folge. Die zusätzliche Explorer-Messung greift in diesem ersten
Diagnosewerkzeug wegen eines falsch angenommenen Prozessaufrufs nicht; dieser
Mangel bleibt sichtbar. Der Lauf endet nach 0,3745 m am ursprünglichen
`geometry_snapshot_retry_budget_exhausted`, mit zwei dokumentierten
`start_motion_wheel_stale_after_processing`-Abbrüchen, null Ankünften/Beobachtungen.

B186 korrigiert ausschließlich den Diagnoseaufruf und misst bei der tatsächlichen
1-cm-Produktkonfiguration die vollständige Eingabeverarbeitung. Unter Last
treten 328–460 ms auf, das vorhandene 180-ms-Quellenfenster wird überschritten.
Der Lauf endet nach 0,0961 m ebenfalls am ursprünglichen Wiederholungsbudget.
Beide Fälle sind ausdrücklich **Diagnose**, keine qualifizierenden Missionen.

B187/B188/B189 verarbeiten identische vier gespeicherte B186-Entscheidungseingänge.
Die Rohkarten-/Kostenkarten-CDR, Pose, Referenz und ursprüngliche physische
Bewegungsbindung werden nicht gegen günstigere Aufzeichnungen ausgetauscht.
Die reine Geometrieprobe verwendet aus der Belegung abgeleitete bekannte Masken;
sie beansprucht keine damalige Livegesundheit oder nachträgliche Fahrfreigabe.

| Variante | Allgemeiner Egress-Pfad auf denselben Zuständen |
|---|---|
| B187, bisherige Einzeloperationen | 186–192 ms |
| B188, Stapeloperationen ohne vorbereiteten Index | 102–107 ms |
| B189, vorbereitete exakte Stapelprädikate | 50–51 ms |

Inventare, projizierte Maskenzahlen, Referenzen und Gültigkeiten sind gleich:
1082 Rohkarten-/13 Kostenkartenzellen, beide Ledgers gültig. Die winzigen echten
TF-Unterschiede bleiben unverändert; sie werden weder gerundet noch re-ankert.
Der allgemeine Projektionspfad erhält seinen unveränderten 1e-9-Pixelflächenvergleich.

`7fabf80` beschleunigt die exakte GEOS-Prüfung durch vorbereitete Geometrie
und Stapeloperationen. Vollständig enthaltene Einheitszellen brauchen keine
zusätzliche Boolean-Schnittfläche; Randzellen behalten die bisherige exakte
Flächenprüfung. Eine skalare vorbereitete Variante erhält Kompatibilität.
Keine neue Unknown-Fläche, Lockerung von Kontur, Quellenfrische oder Historie.

## Tests und Bindung

Elf neue Regressionen vergleichen Stapel-/Skalarentscheidungen mit den bisherigen
Boolean-Flächen, einschließlich Löchern, getrennten Zellen, echten Halbzellen,
numerischer Randtoleranz, leerem Bestand und der tatsächlichen B186-Folge.
Spätere Beobachtung bleibt irreversibler Entzug der Ausnahme.

Der alte Start-Rastertest liest nicht länger die Produktauflösung, um damit
zugleich einen anderen Eingangsdatensatz auszuwählen. Die getrennte kontrollierte
1-cm-Probe und der tatsächliche B172-Negativfall bleiben erhalten; sie behaupten
keinen gemeinsamen historischen Akquisitionsverlauf.

Erster Targetaufruf lud vor dem Build noch die vorige Installation: elf neue
Fälle scheiterten an fehlenden neuen APIs, 25 bestanden. Dieses Log ist erhalten.
Mit expliziter Quellbindung: **36 bestanden**. Anschließend echte V38-Prüfung:

- Zwölfpaketbuild: **7,38 s**, bestanden.
- Direkte Regression: **2242 bestanden**, 155,10 s.
- Registrierte colcon-Tests: **2224, null Fehler/Failures/Skips**, zwölf Pakete,
  2 min 30 s. Testmengen überlappen.
- Bindung B191: `7fabf804ff8a2bcdeb3abc1464ef0227578ec9a5`, 479 Quelldateien,
  137 bytegleiche Installdateien, neun native Artefakte. Originalmanifest,
  MASTERPLAN und native Pluginpins unverändert.

## Tatsächlich gemeinsamer nativer SLAM-Eingang

B190 spielt denselben B186-CDR-Stream durch das gepinnte native SLAM mit 2 und
1 cm ab. Originalscans, Odometrietransformationen und statische Montage-TF
behalten ihre Stempel; `/clock` folgt der aufgezeichneten Empfangsfolge.
Aufgezeichnete Karten und alte `map→odom` werden nicht eingespeist.

Beide Läufe verwenden denselben SHA-256
`71c2e3083a9ea26f46181bac44f3af1d3e1ed3d74ca5872231123809b64094de`,
499 Scans und 1142 Odometrie-TF. Je 50 tatsächlich erzeugte SLAM-Karten,
gleicher finaler Kartenstempel und gleiche finale `map→odom`-Relation.
Rastergrößen unterscheiden sich wie konfiguriert: 142×283 bzw. 283×563.

Das ersetzt den früheren unfairen Eingangsvergleich, beweist aber **nicht**,
dass 1 cm den ursprünglichen B172-Halbzellenfall repariert: Dessen vollständige
Eingangshistorie wurde damals nicht gespeichert. Die nun konkret reparierte
Ursache ist der auf identischen B186-Entscheidungseingaben gemessene
Verarbeitungsaufwand. Die Rastervariante muss weiterhin die Gesamtmatrix bestehen.

## Gesamtprüfung und Rückfall

V37 und V38 bestanden jeweils alle neun historischen nativen Komponenten.
Regulärer B193 auf `7fabf80` bleibt negativ: eine tatsächliche Ankunft, null
qualifizierte Beobachtungen, 0,1619 m; `start_motion_wheel_stale_after_processing`
während der anschließenden Beobachtungsprüfung. Die vollständige Reparatur
ist damit noch nicht nachgewiesen. B194 und folgende Korrekturen werden
im folgenden Nachweis getrennt beschrieben. Keine parallelen Builds,
Regressionen, Profiler oder Archivierung während der Bewegungsprüfung.

Rückfall ausschließlich neuer Produktdiff zu `7934a28`; frühere Fehlerkorrekturen,
ursprüngliche Negativbelege und unveränderte Schutzkette erhalten. Kein 3/3 aus
verschiedenen Kandidaten oder aus diesen Komponentenproben ableiten.

Vollständige synthetische Akquisitionen und CDR-Karten bleiben lokal außerhalb
Git. Kleine sichere JSON/NPZ-Regressionsdaten, Prüfbefehle, Profile und Resultate
liegen hier beziehungsweise in `src/explore/test/data`.
