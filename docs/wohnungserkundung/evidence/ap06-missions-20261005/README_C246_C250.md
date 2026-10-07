# AP-06: Abgelehnte Encoder-/TF-Paare gestoppt und begrenzt neu prüfen

C246 verifiziert zusätzlich die Originalereignisse von C245. Die Beobachter-
Zeitreihe enthält nur die dort protokollierten TF-Samples; das intern tatsächlich
verglichene Encoder-/TF-Paar war nicht gesichert. Unterschiedliche letzte
Beobachterwerte sind **kein** Nachweis eines bestimmten Produkt-Posefehlers.
Deshalb keine erfundene genaue historische Zeitkorrelation oder Filterursache.

Im Elternablauf fehlt unabhängig davon eine sichere Behandlung einer vorüber-
gehend abgelehnten Geometriebindung: `start_motion_wheel_tf_disagreement` wird
nach Child-Stopp sofort endgültig behandelt, während abgelaufene Verarbeitung
bereits eine begrenzte neue Prüfung im Stillstand erlaubt.

`2e5e1fd` nimmt diese Poseabweichung in denselben vorhandenen Ablauf auf:
Child zuerst terminal, vollständiger Stillstand, gültige ursprüngliche Quellen,
neue vollständige Eingaben/Geometrie. Erst ein wieder vollständig gültiges Paar
kann eine neue Planung erlauben. Dieselbe Aufgabe, ursprüngliche Startzeiten,
Versuchs-/Fehlerlimits und Deadlines bleiben bindend. Dauerhafte Abweichung
scheitert weiterhin; Quellenlücke, Cancel und Ablauf werden nicht umklassifiziert.
Die unveränderten 2 cm/0,05 rad werden bei jedem Versuch neu geprüft.

Zusätzlich wird unmittelbar bei Ablehnung das wirklich benutzte Wheel-/TF-
Posepaar samt Referenz, Wheel-Schlüssel, beiden Wheelzeiten und Prüfzeitpunkt
protokolliert. Es wird kein nicht verfügbarer TF-Quellenstempel behauptet und
kein späterer Wert als damaliger Eingang ausgegeben.

Reale Eltern-/Policy-Funktionen mit kontrollierten Action-Peers: Originalcode
**3 rot/9 grün**, korrigiert mit Nachbarfällen **48 grün**. Fälle für vorüber-
gehende und dauerhafte Abweichung, echte Quelllücke, Cancel, Deadline und
erschöpften Retryrahmen. Separate Quellenbindungstests prüfen unveränderte
Ablehnung und exakt protokollierte Eingangswerte.

V46-Build/Gesamttests laufen. Danach native Fälle sowie C248/Cancel249/Gyro250
am gleichen Produktstand; Whole-Ausführung auf vier verfügbaren CPUs bei
vorher verifizierter Vier-CPU-Quote. Keine erneuten identischen A/B-Fehlstarts:
deren fehlender robuster Beobachtungsnachweis ist separat belegt und konstruktiv
vorbereitet. Diese Teilserie darf daher keine vollständige 3/3-Matrix behaupten.

## V46-Endergebnisse

Zwölfpaketbuild, **2371 direkte Tests** (151,41 s), **2353 registrierte Tests**,
null Fehler/Failures/Skips, **9/9 native Komponenten bestanden**. Quellbindung:
494 Dateien, 137 bytegleiche Installdateien, neun gehashte native Artefakte.
Code `2e5e1fd`; ursprüngliches Manifest/Masterplan/externe Plugins unverändert.

C248 führt den neuen Ablauf tatsächlich aus: verworfenes Paar mit **27,0146 mm**
Positions- und 0,0002803 rad Headingabweichung, originale Wheelzeiten gesichert.
Child terminal, Stillstand und `geometry_snapshot_revalidate` im selben Task.
Weitere tatsächliche Native-Vorschläge scheitern jedoch an Geometrie;
`start_egress_new_unknown_or_obstacle` bleibt wirksam. Nach neun Versuchen/einem
Fehler, null Ankünften/Beobachtungen und 0,29878 m endet der Fall regulär an der
**ursprünglichen 900-s-Missionsgrenze** mit `budget_exhausted`. Keine externe
Cancel-Injektion, keine zurückgesetzten Fristen oder Historien.

**Cancel249 bestanden; Gyro-HOLD250 bestanden.** Der Gyro-Fall endet
ordnungsgemäß für die Mission negativ mit `hwt_terminal`; der Schutzfall ist
positiv. Alle drei Fälle: leere terminale Action-Listen, vier Nullbefehlsketten.
C251 verifiziert die vollständigen Originalereignisse: C248 **931.987.524**,
Cancel249 **12.042.067**, Gyro250 **22.465.993** Eingangsbytes gegen die beim
Schreiben erfassten SHA-256-/Bytezahlnachweise. `c251-final-results.json`
enthält Ergebnisse und Hashes; große Gzip-Journale bleiben lokal außerhalb Git.
Die erste Host-Verifikation scheiterte beim Schreiben der Nebenbescheinigung
an Root-Dateirechten; dieselbe Prüfung wurde anschließend erfolgreich im
besitzenden isolierten Container ausgeführt. Kein Originaljournal verändert.

**Keine positive Gesamtmission und keine 3/3-Abnahme.** Softwarekorrekturen
sind überprüfbar; vollständige autonome Erkundung bleibt an den dokumentierten
Start-/Referenz-/Quellengrenzen offen. Abdeckungspaket vorbereitet, keine
Sensor-/Hardwareänderung ausgeführt. Keine erneute identische A/B-Fehlstartserie.
