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
EKF-Ausgaben. Nach einem Quellenfehler im bereiten Zustand bleibt das Tor
bis zum Neustart gesperrt; kein Encoder-Gier-Fallback. Der FC03-Vorlauf
autorisiert grundsätzlich keine Fahrbefehle. Frischegrenzen entsprechen
den vorhandenen Quellenprofilen, nicht nachträglich gelockerten Testwerten.

Aktueller Nachweis und Rückfall: `docs/wohnungserkundung/STATUS.md` und
`docs/ROBOT_TRANSFER.md` im Repository. Nur gestoppt auf den bisherigen
Encoderstart zurückfallen; Topic-/TF-Eigentümer vor Neustart prüfen.
