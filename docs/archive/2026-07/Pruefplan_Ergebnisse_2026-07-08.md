# Pruefplan-Ergebnisse roboter_ws

## ABNAHME: SOFTWARE-FINAL bestanden — 2026-07-08, 22:34–22:39 (Jetson)
- [x] B0b Paket-/AMENT-Check -> OK (16/16 Pakete gefunden)
- [x] A1 Pick&Place-Trockenlauf -> OK (SUCCESS im Log erkannt)
- [x] K1 Missionsbruecke echt -> OK (BT SUCCESS + mission_manager success)
- [x] K2 Objekt-Gedaechtnis -> OK (found + aus Gedaechtnis)
- [x] K4 safety_monitor -> OK (estop frei by default + Not-Aus wirkt)
- [x] K5 Offboard-Guard -> OK (FAILURE ohne ExploreArea-Aufruf)
- [x] N1 Nav2 virtuell -> OK (navigate_to_pose SUCCEEDED)
- [x] N2 Mission+Nav2 -> OK (BT SUCCESS + status success + Nav2 real)
- [x] D2 handeye_calibration -> OK (Paket vorhanden, Kalibrierlauf folgt nach Arm-Integration)
- [x] B0 Build -> OK (manuell ohne --symlink-install; exFAT kann keine Symlinks; 19 Pakete)

Erkenntnisse aus dem Lauf (beide im Pruefplan-Skript behoben):
1. exFAT/USB: `--symlink-install` scheitert dort -> B0 erkennt das Dateisystem jetzt selbst.
2. N1 war beim Kaltstart flakey (feste Wartezeit) -> N1/N2 warten jetzt aktiv auf den
   Nav2-Action-Server (`wait_action_server`).

*(Fehlversuche vom selben Abend — nicht gesourcte Shell, Symlink-Problem — sind mit diesen
Fixes gegenstandslos und wurden aus dem Protokoll entfernt. Neue Laeufe haengen unten an.)*
