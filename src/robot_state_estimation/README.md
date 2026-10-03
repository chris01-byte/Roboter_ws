# HWT601/Encoder-Fusion im WE-Kandidaten

Gezielte Übernahme aus `1d91229dc10ff4bb791938d49aae8e9808a5dfff`;
keine OAK-IMU und kein neuer Navigator. Protokoll, Achsrotation, feste
Start-Biaskorrektur, EKF-Profil und unabhängiger LiDAR-Beobachter stammen
aus dieser Referenz. Historische Abnahmen gelten nicht als heutige Abnahme.

Opt-in in `robot_bringup/app_mapping.launch.py`:
`use_hwt601_odometry:=true operator_stationary_confirmed:=true`.
Die Stillstandsbestätigung ist eine aktuelle Vor-Ort-Angabe, kein Dry-run-Wert.
Ohne sie bricht der HWT-Launch vor dem Gerätezugriff ab.

Mit `active_drive:=false` ersetzt der historische **FC03-only Encoderleser**
die Basis; er kann trotzdem den Motorbus öffnen und braucht dafür eine
separate Gerätefreigabe und antwortende, sicher gegen Bewegung gesperrte
Controller. Mit `active_drive:=true` besitzt allein `base_hardware` den Bus.
Niemals beide starten. Es wird kein aktiver Install umgeschaltet.

Encoder-vx → `/fusion/hwt601/wheel_odom_raw`, kalibriertes HWT-wz →
`/shadow/hwt601/imu/yaw_rate`, EKF → `/odom` und `odom→base_link`.
SLAM behält `/map` und `map→odom`. Encoder-Gier und Rohzähler bleiben
diagnostisch sichtbar. `use_control=false`; LiDAR ist nur Vergleich.

Das Fahrtor und der Explorer prüfen dieselben Rohquellen unabhängig von
EKF-Ausgaben. Harte Quellenfehler sperren das Tor bis zum Neustart. Begrenzte
HWT-/Encoder-Recovery läuft über den vorhandenen HOLD-Vertrag; kein
Encoder-Gier-Fallback. Der FC03-Vorlauf
autorisiert grundsätzlich keine Fahrbefehle. Frischegrenzen entsprechen
den vorhandenen Quellenprofilen, nicht nachträglich gelockerten Testwerten.

Aktueller Nachweis und Rückfall: `docs/wohnungserkundung/STATUS.md` und
`docs/ROBOT_TRANSFER.md` im Repository. Nur gestoppt auf den bisherigen
Encoderstart zurückfallen; Topic-/TF-Eigentümer vor Neustart prüfen.

Der metrische LAB-/Entwicklungspfad aktiviert ausdrücklich
`hwt_development_contract:=true`. Das zusätzliche Profil
`hwt601_metric_development.yaml` setzt ausschließlich den Rohleser auf
50 ms Antwortfrist und 300 ms nutzbare Originaldatenfrische. Ohne Opt-in
bleiben 30/200 ms erhalten. Ein Antworttimeout bei weiterhin gültigen,
frischen Originaldaten meldet `transport_degraded`, verbraucht aber keinen
HOLD. Späte Antworten werden verworfen, Originalstempel nicht erneuert.
Die Transaktionsdiagnose zählt Header und Payload getrennt und unterscheidet
fehlende, teilweise, verspätete sowie zu spät verarbeitete Antworten.

Der vorhandene gemeinsame Quellenwächter bleibt zuständig: echter
Datenverlust sperrt Bewegung im HOLD; zwei HWT-HOLDs sind innerhalb eines
rollenden 60-s-Fensters zulässig. Jeder Recoveryvorgang behält seine absolute
5-s-Frist, Stabilitätsprüfung, Stillstand und Gate-ACK. Portwechsel,
Protokoll-/Identitätsfehler, ungültige Daten und Zeitbruch bleiben terminal.
Das Encoderprofil und dessen 120/180-ms-Grenzen bleiben unverändert.
Die Werte sind ein dokumentierter Entwicklungsvertrag, keine Serienfreigabe.

Nach einer Eingabelücke verwirft der Yaw-Kern weiterhin die Grenzmessung.
Im Entwicklungsvertrag darf der letzte unveränderte korrigierte Originalwert
innerhalb seiner bestehenden 350-ms-Frische weiter genutzt werden, wenn
gleichzeitig gültige Rohoriginale innerhalb 300 ms vorliegen. Eingefrorene,
stabile Kalibrierung und alle Fehlerprüfungen bleiben Pflicht; die Lücke wird
nicht integriert. Die 100-ms-Kalibrierungsgrenze wird nicht geändert.

## AP-01: Hostempfang und Clockvertrag (MASTERPLAN v1.3)

Der Rawheader bezeichnet ausschließlich den vollständigen hostseitigen Empfang
`last_reply_received_monotonic_s` des echten Transports, keine interne
Sensorabtastzeit. Empfang, Transaktionsstart und Deadline müssen endlich und
konsistent sein; der frühere Fallback auf Verarbeitungszeit entfällt. Gerätefreie
Regressionen koppeln den echten Transport mit einer synthetischen seriellen
Gegenstelle an den echten `_poll()` und verzögern danach die Verarbeitung.

Die ROS-Abfrage wird mit `time.monotonic()` davor/danach eingerahmt. Unter dem
Hostzeitvertrag (gleiche laufende Taktrate, keine Epochenänderung) liegt der
ROS-minus-monotonic-Offset in `[ROS − nachher, ROS − vorher]`. Die Schnittmenge
aller präzisen Belege bleibt erhalten. Der untere Rand dieser gültigen Spanne
projiziert den Empfang konservativ: höchstens **1 ms plus 2 ns Rundungsreserve
zu früh**, niemals durch einen positiven Mittelpunktfehler in die Zukunft.
Kein Klemmen an den vorherigen Stempel und kein Umstempeln auf jetzt.

Ein Bracket darf höchstens **1 ms** breit sein: 1/10 des nominellen 100-Hz-
Probenabstands und 1/100 der unveränderten 100-ms-Biaskontinuitätsgrenze. Dies
ist eine Unsicherheitsgrenze, keine zusätzliche Frische- oder Antwortfrist.
Bis zu **drei** sofortige Paarungsversuche sind erlaubt, ausschließlich innerhalb
der tatsächlichen 30-/50-ms-Transaktionsdeadline; danach wird die Probe verworfen.
Große Brackets dürfen die Offsetspanne weder begründen noch verbreitern.
Wiederholtes Verwerfen lässt die letzte gültige Empfangszeit, den Header und
die Samplehistorie unverändert altern. `clock_correlation.classification`
unterscheidet `clock_pair_valid`, `clock_pair_uncertain` und `clock_basis_changed`.
Die Unsicherheitsbehandlung reconnectet in keinem Profil; Entwicklung behält
bei noch frischen Originaldaten den bestehenden degradierten Datenvertrag,
Legacy meldet nach seinem bestehenden Fehler-/Bereitschaftsvertrag unbereit.

Disjunkte Offsetbelege erkennen Zeitbasisänderung auch bei weiter steigenden
Headern. Ein erkanntes Ereignis wird nicht durch Neubasieren geheilt;
Entwicklung verriegelt nach dem bisherigen harten Fehlervertrag, Legacy behält
seine vorhandene Reconnect-Schwelle. Beliebig kleine Sprünge innerhalb der
Messunsicherheit sind nicht zuverlässig erkennbar. Langfristiger Offsetdrift,
Suspend oder Wallclockänderung außerhalb der gemeinsamen Spanne machen den
Hostzeitvertrag ebenfalls ungültig. Linux CLOCK_MONOTONIC und Hostwallzeit
müssen denselben laufenden Taktbezug liefern.

Unterstützt werden das unveränderte `SYSTEM_TIME`-Clockobjekt und eine inaktive
`ROSClock` mit Hostzeit. **`use_sim_time`/ROS-Time-Override ist für den realen
Rawdriver nicht unterstützt.** Aktivierung/Deaktivierung wird per echtem rclpy-
Jumpcallback dauerhaft vorgemerkt (auch zwischen Polls); aktiver Override,
Objekt-/Clocktypwechsel sperren vor einem weiteren seriellen Read. Rückkehr zur
alten Quelle hebt den Fehler nicht auf. Reale `ROSClock`-/`TimeSource`-Tests
prüfen Quellenwechsel und unabhängige ROS-Änderungen ohne Systemuhränderung.

Die echten Guard-/Health-Verbrauchertests prüfen kurze Zustellverzögerungen,
Future-Gegenfall und HOLD durch tatsächlich gealterte Originaldaten. Alle
50/300-ms-, Legacy-30/200-ms-, Encoder-120/180-ms-, HOLD-, Bias- und
Recoverygrenzen bleiben unverändert. Kein Hardware- oder Deploymentnachweis.
