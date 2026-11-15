# Archiv: Auftrag AT-1 (Antriebsprobe) nach Ausführung und Auswertung

Bytegleicher bisheriger Agentenauftrag aus
`2c3aafb55322ca2ac23805aa523faeb4e2fdf1b2`; Originalblob
`fb2cef05ef5d0f43634d81941caf001258334a53`, SHA256
`ca8333cde923046add966a3e3d51b01f8b7d0500d047d090ad3e9fed8fcb1fd7`.

AT-1 wurde am 15.11.2026 auf dem Jetson ausgeführt: ein scharfer Stackstart
ohne Mission, zwei Proben ohne Abbruch, ohne Berührung und ohne Eingriff.
Ergebnis: **Messung gestört, kein Urteil zur Hypothese.** Der Auftrag
enthielt einen Fehler: Er nahm an, auf `/cmd_vel_smoothed` sende ohne
Mission niemand. Tatsächlich sendet der Glätter dort mit 20 Hz Nullbefehle;
die Basis bekam Sollwert und Halt im Wechsel. Auswertung im STATUS,
Abschnitt 15.11.2026. Der hier archivierte Text ist kein aktueller Auftrag
und darf nicht erneut ausgeführt werden; der aktuelle Stand steht
ausschließlich zwei Ebenen höher in `AGENTENAUFTRAG.md`.
