# HWT601: USB-Inbetriebnahme auf dem Jetson

Stand 08.09.2026. Branch `fix/hwt601-usb-commissioning`, Grundlage
`a326ab0` mit bereits vorbereitetem passivem HWT-Treiber.
Arbeitsverzeichnis: `/home/p/roboter_worktrees/hwt601-usb-commissioning`.
Die laufende Arbeitskopie `/home/p/roboter_ws` mit fremden, uncommitteten
Erkundungsaenderungen bleibt unveraendert. **Keine Fahrfreigabe.**

## Gemessener Befund

- Nutzer meldet HWT601 montiert und per USB angeschlossen. Der genannte
  [Herstellerartikel](https://witmotion-sensor.com/products/hwt601-3-axis-imu-inertial-navigation-ros-robot-module-mems-tilt-angle-sensor-built-in-dof-crystal-gyroscope)
  bietet HWT601-AGV-485, WT601-AGV-485 und USB-485-Adapter an. USB-Erkennung
  alleine beweist noch keine Sensorantwort oder korrekte Versorgung.
- CH340 `1a86:7523` am USB-Pfad `1-2.4.4.4` vorhanden; keine individuelle
  Seriennummer. `/dev/ttyUSB_HWT601` und alle `ttyUSB*` fehlen.
- Laufender Kernel `5.15.199-tegra`: `CONFIG_USB_SERIAL_CH341` ist nicht
  aktiviert, `modprobe ch341` findet kein Modul. Passende Header sind vorhanden.
- udev markiert diesen Adapter faelschlich als Braillegeraet. Im Kerneljournal
  beansprucht `brltty` ausserdem FTDI/Motor und CP210x/LiDAR, deren serielle
  Interfaces daraufhin verschwinden. Diese beiden Ports werden hier **nicht**
  neu gebunden oder geoeffnet; ihre Wiederherstellung ist ein separater Test.
- VL53-USB-I2C `1a86:5512` nutzt `mphsi-ch34x`. Dieser Treiber wird nicht
  veraendert; der hier gebaute serielle CH341-Treiber hat keine `5512`-Kennung.
- Keine ROS-/Motorprozesse liefen. Physischer Motorstrom ist softwareseitig
  nicht bestaetigt. Vor Arbeiten Motorversorgung aus, Roboter gegen Rollen
  sichern. Kein Skript ersetzt den Hardware-Not-Aus.

## Bereits vorbereitet

`tools/sensorfusion/hwt601_usb_setup.py prepare` baut den unveraenderten
[Linux-Stable-Treiber v5.15.199](https://github.com/gregkh/linux/blob/v5.15.199/drivers/usb/serial/ch341.c)
gegen die Jetson-Header. Download nur ueber HTTPS, Quelltext-SHA-256:
`f66d070eab6235b8a5c7a06a283d2feecb8fa3d81bc1323c847c2d2cbf7bd410`.
Quelltext, Modul und Manifest liegen ignoriert unter `build/hwt601_usb/`.
Build und passendes `vermagic` sind bestaetigt. Kein neues Modul wurde geladen.

Die Regel fuer `/dev/ttyUSB_HWT601` ist an VID/PID **und den physischen Port**
gebunden: `platform-3610000.usb-usb-0:2.4.4.4:1.0`. Sensoradapter am selben
Steckplatz lassen. Ein Umstecken muss zuerst erneut identifiziert werden;
eine globale Regel fuer alle CH340-Geraete ist absichtlich nicht vorgesehen.
Das ist eine Steckplatzbindung, keine eindeutige Identifikation des Sensors.

## Einmaliger lokaler Installationsschritt

Das lokale Benutzerkonto braucht ein sudo-Passwort; dieses gehoert nur ins
Terminal, niemals in Chat, Skript oder Repository:

```bash
sudo python3 /home/p/roboter_worktrees/hwt601-usb-commissioning/tools/sensorfusion/hwt601_usb_setup.py install
```

Der Installer prueft zuerst Kernel, Adapter, Buildpruefsummen und vorhandene
Dateien. Er bricht bei fremden Zielregeln ab. Er installiert ausschliesslich:

- `/lib/modules/5.15.199-tegra/updates/amadeus-hwt601/ch341.ko`;
- `/etc/udev/rules.d/83-hwt601.rules` (Alias und gezielter ModemManager-Ausschluss);
- `/etc/udev/rules.d/85-brltty.rules` (Kopie der Paketregel mit einer einzigen
  vorgelagerten Ausnahme fuer den vermessenen HWT-Steckplatz);
- Installationsmanifest unter `/var/lib/amadeus/hwt601-usb/`.

Danach laedt er udev-Regeln/Modul, stoppt `brltty-udev.service` **einmal** und
loest nur fuer HWT-USB/TTY neue udev-Ereignisse aus. Der separate Desktop-
Brailleprozess wird nicht gestoppt. Kein Dienst wird maskiert/deinstalliert;
alle anderen Braille-Zuordnungen bleiben erhalten. Das einmalige Stoppen kann
ein aktuell vom Systemdienst bedientes Braillegeraet unterbrechen.
Motor- und LiDAR-Ports werden nicht angefasst. Wenn der Alias noch fehlt:
nur HWT-USB abziehen und am identischen Steckplatz wieder einstecken.
Bei spaeterem Wiederanlaufen von brltty durch andere USB-Geraete ist erneut
zu pruefen, ob der HWT-Port stabil bleibt. Die noch bestehenden Fehlzuordnungen
von Motor/LiDAR sind hier nicht automatisch mit behoben; ein Boot-/Reconnect-
Test ist Teil der ausstehenden Hardwareabnahme.

**Wartung:** Dies ist kein DKMS-Paket. Bei einem Kernelwechsel muss der Treiber
fuer den neuen Kernel separat vorbereitet und getestet werden. Bei einem
brltty-Paketupdate muss die gezielte Regelkopie erneuert werden; der Installer
erkennt eine seit `prepare` geaenderte Paketregel und bricht ab. Die jeweilige
frische `/lib/udev/rules.d/85-brltty.rules` bleibt immer unangetastet.

## Danach: erst messen, dann ROS/Fusion

Die OAK bleibt fuer diese Schritte aus. Versorgung und RS485-Variante nach
Typenschild pruefen (Details `HWT601_INTEGRATION.md`). Kein Geraetescan ueber
alle seriellen Ports, keine Konfigurations-/Kalibrierbefehle.

```bash
cd /home/p/roboter_worktrees/hwt601-usb-commissioning
# Zwei Sekunden nur lauschen, keinerlei Modbus-Anfrage:
python3 tools/sensorfusion/hwt601_messen.py

# Nach RS485-Pruefung: 15 s Einlauf, 30 s Rohdaten, nur FC03:
python3 tools/sensorfusion/hwt601_messen.py --modbus

# Anschliessend ROS-Rohdaten separat starten; Ende mit einmal Ctrl-C:
bash tools/sensorfusion/start_hwt601_rohdaten.sh
```

Der Messlauf prueft den Alias vor dem Oeffnen gegen den gemessenen USB-Port.
Bei unaufgefordert eingehenden Bytes sendet er **keine** Modbus-Anfrage;
zuerst Protokoll klaeren. Im Modbus-Modus werden Norm der Beschleunigung,
Rate, groesste Datenluecke inklusive Anfang/Ende, Fehler, Mittelwerte,
Standardabweichungen und unkorrigiertes Gyrointegral ausgegeben. Rueckgabecode
2 bedeutet Fehler oder noch nicht bestandene Rohdatenpruefung. Es werden weder
Parameter geaendert noch Kalibrierwerte automatisch gespeichert.

`raw_check_passed=true` bestaetigt nur den kurzen Rohdatentest mit vorlaeufigen
Grenzen (mindestens 80 Hz, keine Luecke >0,20 s, keine verworfenen Antworten,
Beschleunigungsnorm 9,3..10,3 m/s²). **Gyroskala, Montage-TF, Temperaturdrift
und Eignung zur Fusion folgen daraus nicht.** `fusion_ready` bleibt false.
Auch die ROS-Diagnose unterscheidet jetzt `raw_data_ready` von `fusion_ready`.
Die Beschleunigungsskala kann die separate Gyroskala nicht bestaetigen.

Erst nach Rohdatenerfolg folgen ein laengerer Stillstandslauf, einzeln
bestaetigte Achsen/Drehrichtung und der vermessene Montage-TF. Kein
Identitaets-TF als Platzhalter. HWT-Montage und 18,94-Grad-OAK-Neigung bleiben
getrennte Transformationen. Keinen manuellen Drehversuch mit aktivem
Biasadapter und simulierten Null-Radwerten machen: dann koennte echte
Handbewegung faelschlich als Bias behandelt werden.

## Rueckfall

Alle HWT-Leser vorher sauber beenden, keine Fahrprogramme starten:

```bash
sudo python3 /home/p/roboter_worktrees/hwt601-usb-commissioning/tools/sensorfusion/hwt601_usb_setup.py rollback
```

Der Rueckfall entlaedt nur `ch341` (ohne Zwang; Abbruch bei Benutzung) und
verschiebt ausschliesslich unveraenderte, manifestgebundene Installationsdateien
in einen Zeitstempelordner unter `/var/lib/amadeus/hwt601-usb/`. Alles bleibt
wiederherstellbar. Fremde/nachtraeglich geaenderte Regeln bleiben unangetastet.
Die urspruenglichen Paketregeln gelten wieder nach Reload/naechstem
USB-Ereignis; ein vorheriger laufender brltty-Prozess wird nicht rekonstruiert.
Der Produktionsstart wurde zu keinem Zeitpunkt umgestellt.
