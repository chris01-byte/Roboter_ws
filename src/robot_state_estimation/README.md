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
