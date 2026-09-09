# HWT601: erste motorische Linksdrehung, 09.09.2026

> **KRITISCH: Die nachstehenden Abnahmen sind zurueckgezogen.** Nutzer bestaetigt
> physisch jeweils nur 45 Grad an Bodenmarkierungen statt gemeldeter 90 Grad.
> Ursache offen, motorisches Testwerkzeug gesperrt. Die folgenden Werte sind
> historische Softwareergebnisse, keine gueltige Hardwareabnahme.
> Aktueller Stand: `docs/HWT601_WINKEL_KRITISCH.md`.

## Nachtrag: freigegebene Gegendrehung rechts bestanden

Auf ausdruecklichen Nutzerwunsch eine Rechtsdrehung mit unveraenderten
Geschwindigkeits-/Zeit-/Feedbackgrenzen ausgefuehrt. Eigener Branch
`feature/hwt601-right-turn-test` ab `ad77217`; Werkzeug erhaelt
`--direction right` (Standard bleibt links). Alle Richtungspruefungen werden
mit dem Sollvorzeichen normiert, Messwerte bleiben vorzeichenbehaftet.

105 Softwaretests bestanden, inklusive Rechtsstopp, falscher Richtung und
Grenzverletzungen. Reales motorloses Rechtskommando -0,10 rad/s mit
anschliessendem Watchdog-Stopp bestanden. Danach echter passiver Preflight,
neue Anfangskalibrierung mit Radruhe und separate Startankuendigung.

| Quelle | Rechtswinkel |
|---|---:|
| HWT601 mit festem Anfangsbias | -90,57797 Grad |
| Unabhaengiger LiDAR | -91,25000 Grad |
| Encoder | -89,80342 Grad |

IMU minus LiDAR +0,67203 Grad. Stillstand bestaetigt; beide groben
Vorzeichen-/Skalenchecks bestanden, keine weitere Bewegung ausgefuehrt.
Die Summe der beiden IMU-Winkel ist +0,35434 Grad. Sie ist nur eine
Plausibilitaetskontrolle: getrennte Biasbestimmung/Referenzinitialisierung,
diskrete LiDAR-Suche und keine durchgehende globale Rueckkehrmessung.
Die exakte urspruengliche Bodenpose ist damit nicht bewiesen.

1.981 IMU-Proben mit Startanker, 19,80035 s inklusive Endruhe,
99,99824 Hz, maximal 18,664 ms Luecke. Alle 990 Encoderzustandsmeldungen
gesund und alle LiDAR-Statusmeldungen im Messfenster gueltig. Maximale
gemeldete lineare Geschwindigkeit 0,00265 m/s. Unabhaengige NumPy-
Nachrechnung aller IMU-Integrale: maximale Abweichung 1,5e-13 Grad.

Lokale Daten: `/home/p/.local/share/amadeus/hwt601/powered-20260909-164111/`
und Bag `right-scans-20260909-164100` im selben Elternverzeichnis.
Alle Testprozesse nach bestaetigtem Stopp beendet; Motorversorgung nicht
physisch abgeschaltet. Keine Produktions-/Kalibrierwerte geaendert.
Wiederholbarkeit, Gesamtfusion und Kartenqualitaet bleiben offen.

## Ergebnis

Nach ausdruecklicher Nutzerfreigabe fuer motorische Drehung und bestaetigtem
freien Schwenkbereich eine langsame Linksdrehung ausgefuehrt. Kein Ruecklauf.

| Quelle | Winkel |
|---|---:|
| HWT601, fest korrigiertes Gyrointegral | +90,93231 Grad |
| Rad-/IMU-unabhaengiger LiDAR-Scanvergleich | +91,25000 Grad |
| Encoder | +89,84432 Grad |

IMU minus LiDAR: -0,31769 Grad. Grober Links-Vorzeichen-/Skalencheck bestanden,
keine Praezisionskalibrierung und keine Fusionsfreigabe. Die LiDAR-Suche ist
diskret; die ausgegebenen Dezimalstellen belegen keine absolute Genauigkeit.
Der Matcher lief direkt auf `/scan`, `base_frame=laser_frame`, ohne IMU-
Scanfilter, Radvorhersage, EKF oder Kartenlokalisierung. Relative Gier ist so
vergleichbar; seine Translation waere die des LiDARs, nicht der Antriebsachse.

1.979 IMU-Proben einschliesslich Startanker, 19,78143 s inklusive Bremsen und
Endruhe, 99,99280 Hz; groesste Luecke 18,081 ms. Alle 989 erfassten
Encoderzustandsmeldungen gesund, alle LiDAR-Statusmeldungen im Messfenster
gueltig. Maximal gemeldete lineare Geschwindigkeit 0,00265 m/s.
Alle drei IMU-Integrale unabhaengig mit NumPy aus JSONL nachgerechnet;
maximale Abweichung 2,8e-13 Grad. Stillstand per Rueckmeldung bestaetigt.

## Ausgefuehrter Ablauf und Hardwarewirkung

Branch `feature/hwt601-powered-turn-test` ab `e972794`. Hauptarbeitskopie
`/home/p/roboter_ws` mit fremden Aenderungen unangetastet.
104 Softwaretests bestanden; realer ROS-Dry-run mit `dry_run=true`,
`allow_rs485=false` pruefte einen 0,10-rad/s-Befehl und anschliessenden
Watchdog-Stopp. Erst danach echter Antrieb, weiterhin ohne Drehvorgabe.
Passiver Preflight bestaetigte IMU, LiDAR, Encoder und Stillstand.

Der unveraenderte Basis-Treiber initialisierte die vorhandenen Motorparameter:
Beschleunigen 2.000 ms, Bremsen 400 ms, Startdrehzahl 5 rpm, Stop und Feedback
bestaetigt. Es wurden also Motorregister angesprochen; keine HWT-
Konfigurationsregister und keine Kalibrier-/Produktionsdateien geaendert.

Neues Werkzeug `tools/sensorfusion/hwt601_motor_drehtest.py`: Standard ist
passiver Preflight ohne Befehlspublisher. Echter Lauf braucht `--execute`,
`AMADEUS_FAHRFREIGABE=JA`, interaktives Terminal und zuletzt `s` + Enter.
Diese Schalter ersetzen keine persoenliche Freigabe. Der Basisprozess wird
separat mit isoliertem Eingang `/hwt_test/cmd_vel`, Zustand
`/hwt_test/base_state`, Odometrie `/hwt_test/encoder_odom`, `publish_tf=false`,
maximal 0,10 rad/s und 0,01 m/s gestartet; das Werkzeug befiehlt nur Drehung.
Der LiDAR-Ausgang ist `/hwt_test/lidar_odom`, Status `/hwt_test/lidar_status`.

Vor Drehung etwa 25 s neue Biasbestimmung mit gemessener Radruhe. Bias waehrend
der Drehung eingefroren. Zielstopp ab 88 Grad LiDAR; reales Ende nach Bremsen
91,25 Grad. Harte Zeitgrenze 24 s, Gegenrichtung, fehlender Fortschritt,
Encoderwinkel >105 Grad, IMU-Winkel >120 Grad, Encodertranslation >12 cm,
Quellenausfall und widerspruechliche Encoder-/LiDAR-Winkel brechen ab.
Basis-Watchdog 0,25 s; Cleanup sendet Nullbefehle. Not-Aus bleibt erforderlich.
Kein `collision_monitor`, keine OAK, keine autonome Navigation; ausschliesslich
isolierter, persoenlich beaufsichtigter Test auf bestaetigt freier Flaeche.

## Lokale Daten und Rueckfall

- Messung: `/home/p/.local/share/amadeus/hwt601/powered-20260909-162248/`
- Scans/ROS: `/home/p/.local/share/amadeus/hwt601/powered-scans-20260909-162330/`
- Vorlauf-Bag `powered-scans-20260909-162300` wurde vor Bewegung beendet;
  der Befehlskanal wird wegen der Exklusivpruefung nicht mitabonniert.

Alle gestarteten Testprozesse wurden nach dem bestaetigten Stopp mit SIGINT
einzeln beendet; keine Prozessgruppensignale. Sensor-/Motorports anschliessend
frei pruefen. Das ist keine physische Stromabschaltung der Motoren.
Rueckfall: Test nicht erneut starten; keine Produktionsstarts umgestellt.

Der vorherige manuelle Lauf `turn-left-20260909-160747` war ein Timeout ohne
beabsichtigte Drehung, keine fehlgeschlagene IMU-Skalenabnahme. Seine Angabe
`motor_power_off=operator_declared_not_measured` war eine nicht verifizierte
Annahme; der Nutzer stellte klar, dass die Raeder blockiert sind. Manuelle
Drehung wurde verworfen, nicht gegen Widerstand erzwungen.

Offen: Gegenrichtung, Wiederholbarkeit, thermische/zeitliche Genauigkeit,
gesamte Sensorfusion und anschliessende Kartenpruefung. Keine automatische
Skalenanpassung aus diesem Einzelversuch.
