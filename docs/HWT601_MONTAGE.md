# HWT601-Montage, 08.09.2026

Branch `feature/hwt601-mount-frame`, Basis `a31b816`. Sensor-Frames werden
getrennt von USB-Treiber und Bias-Kalibrierung geaendert und getestet.

## Bestaetigte Angaben und Grenzen

Nutzer: X+ rechts, Y+ vorwaerts, Z+ oben; Gehaeusemitte etwa 84 mm vor der
Antriebsachse und seitlich mittig; Sensor-Fussplatte 34 mm ueber Boden.
Die 84 mm sind eine schwer zugaengliche Naeherungsmessung. Es wird keine
erfundene numerische Messunsicherheit eingesetzt (`null` im Profil).

Der existierende ROS-Bezug ist x vorwaerts/y links/z oben. Im bestehenden
Dummy-URDF liegt `base_link` 90 mm ueber `base_footprint`; OAK und VL53
verwenden denselben 90-mm-Abzug. Das ist eine bestehende Modellkonvention,
keine neue Vermessung. Der URDF-Kommentar "in der Antriebsachse" ist fuer die
Hoehe ungenau: die Radmittelpunkte liegen im Modell bei 62,5 mm ueber Boden.
Diese bestehenden Basis-/Kamera-/Rad-Frames werden hier nicht veraendert.

Die Montageorientierung lautet Roll=0, Pitch=0, Yaw=-pi/2.
Ein Vektor (x,y,z) aus dem Sensor wird in Roboterachsen zu (y,-x,z).
Insbesondere bleibt die positive Z-Gierrate positiv. Die OAK-Neigung
18,94 Grad gehoert nicht in diese Transformation.

## Bekannter Montagepunkt ist nicht der interne Messpunkt

`hwt601_mount` bezeichnet die Projektion der angegebenen Gehaeusemitte auf
die vom Nutzer vermessene Fussplatten-Referenzebene. Nominal:

```text
base_link -> hwt601_mount
translation [m]: 0.084, 0.000, 0.034 - 0.090 = -0.056
quaternion xyzw: 0, 0, -0.7071067812, 0.7071067812
```

Das vom Herstellerartikel verlinkte
[HWT601-AGV-Datenblatt](https://drive.google.com/file/d/19kgM1KujoYvYiMd8ZjfDkQanNgEoKHT1/view)
wurde vollstaendig als Text gelesen und die Masszeichnung auf Seite 8
visuell geprueft. Sie zeigt eine Gehaeusehoehe von 23 mm, aber keine
eindeutige interne Messpunktkoordinate. Die halbe Gehaeusehoehe ist deshalb
**kein** bestaetigter Chipversatz. Die PDF liegt lokal ignoriert unter
`build/hwt601_reference/`, nicht als Herstellerkopie im Repository.

Der neue Launch publiziert ausschliesslich `base_link -> hwt601_mount`.
Er publiziert **kein** `hwt601_mount -> hwt601_link` und verbindet damit
absichtlich noch nicht den Rohdatenframe mit dem Roboter-TF-Baum.
`sensor_origin_offset_mount_m: null` und `fusion_approved: false` bleiben
explizit erhalten. Keine automatische Umschaltung von EKF, Scan-Gate, OAK
oder Produktivstarts. Der reine Rohdatenstart ist unveraendert.

## Motorloser Teststart

Im Worktree `/home/p/roboter_worktrees/hwt601-usb-commissioning`:

```bash
source /opt/ros/humble/setup.bash
source install/local_setup.bash
ros2 launch robot_state_estimation hwt601_mount.launch.py
```

Dieser separate Start oeffnet keinen seriellen Port und startet nur einen
statischen TF-Publisher. Kein Basis-/Motor-/Kamera-/Fusionsprozess.
Beenden mit einmal Ctrl-C, keine Prozessgruppe signalisieren.

Tests pruefen alle drei Achsen, Quaternionnorm, Rechtshaendigkeit,
Millimeter/Metereinheiten, NaN, falsche Frames und fehlende Fusionsfreigabe.
Unplausible Profile werden vor dem Publisherstart abgewiesen.

## Naechste getrennte Stufe

Fuer eine reine Gyro-/Gierratenverwendung ist der genaue Hebelarm nicht
erforderlich: Winkelgeschwindigkeit ist bei starrer Montage ortsunabhaengig.
Die noch unbekannte Chipposition darf also nicht als grundsaetzlicher
Blocker fuer motorlose Gyro-/Biaspruefungen behandelt werden. Dennoch wird
hier kein vollstaendiger physischer Sensor-TF erfunden. Vor dessen Freigabe
braucht es eine dokumentierte Messpunktangabe oder eine explizit vereinbarte
nominale Ursprungsdefinition mit benannter Grenze (keine Beschleunigungs-
Hebelarmkorrektur daraus ableiten).

Gyroskala/Drehrichtung sind separat mit einem abgesicherten Drehversuch
zu pruefen; Bias-/Langzeitabnahme bleibt eine eigene Aenderungs-/Teststufe.
Keine weitere schwer zugaengliche Nutzermessung wurde vorausgesetzt.

Rueckfall: den separaten Montage-Launch beenden/nicht starten. Keine
Produktivdatei, bestehender Sensor-TF oder Systemkonfiguration umgestellt.
