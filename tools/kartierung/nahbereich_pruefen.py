#!/usr/bin/env python3
"""Prueft, ob der Nahbereichsschutz wirklich arbeitet. Rueckgabe 0 = ja.

WOZU: Am 14.08.2026 war der Schutz wirkungslos, ohne dass es irgendwo auffiel.
Ein Kernel-Update hatte das Out-of-Tree-Modul ``ch34x_mphsi_master`` verwaist,
``vl53_near_field`` starb daraufhin sofort beim Start - und der
``collision_monitor`` aktivierte sich trotzdem sauber und reichte JEDEN
Fahrbefehl durch. Ein Schutz, der nach einem Kernel-Update stillschweigend zur
Attrappe wird, ist gefaehrlicher als gar keiner, weil man sich auf ihn verlaesst.

Diese Pruefung macht diesen Zustand laut. Sie prueft vier Dinge:

  1. das Kernelmodul ist geladen und ein CH341-I2C-Bus existiert;
  2. der Knoten ``vl53_near_field`` laeuft;
  3. BEIDE Punktwolken-Topics veroeffentlichen tatsaechlich;
  4. der ``collision_monitor`` laeuft.

Punkt 3 ist der wichtige: Ein laufender Knoten allein beweist nichts, und ein
laufender Monitor erst recht nicht.

Was diese Pruefung NICHT leistet: Sie sagt nicht, ob der Monitor auch wirklich
bremst - dafuer braucht es ein Hindernis in der Zone. Und leere Wolken sind
KEIN Fehler: Der Schutz wirkt nur innerhalb von 50 cm (``z_min``/``z_max`` sind
trotz ihres Namens Distanzgrenzen), im freien Raum sind 0 Punkte richtig.

Aufruf:
    python3 tools/kartierung/nahbereich_pruefen.py
    python3 tools/kartierung/nahbereich_pruefen.py --still   # nur Rueckgabewert

Als Tor vor einer Fahrt:
    python3 tools/kartierung/nahbereich_pruefen.py --still || exit 1
"""
import argparse
import glob
import os
import sys
import time

WARTEZEIT_S = 8.0
MINDEST_WOLKEN = 3          # in WARTEZEIT_S; bei ~3 Hz sind das gut 2 Sekunden
TOPICS = ('/near_field/left/points', '/near_field/right/points')


def modul_geladen():
    try:
        with open('/proc/modules', 'r') as f:
            return any(z.startswith('ch34x_mphsi_master') for z in f)
    except OSError:
        return False


def ch341_bus():
    """Nummer des CH341-I2C-Busses oder None."""
    for pfad in sorted(glob.glob('/sys/class/i2c-adapter/i2c-*')):
        try:
            with open(os.path.join(pfad, 'name')) as f:
                if 'ch34' in f.read().lower():
                    return int(os.path.basename(pfad).split('-')[1])
        except (OSError, ValueError):
            continue
    return None


def prozess_laeuft(merkmal):
    """Sucht in /proc statt per ps|grep - das Muster stuende sonst in der
    eigenen Kommandozeile und der Treffer waere die eigene Shell."""
    eigen = {os.getpid(), os.getppid()}
    for eintrag in os.listdir('/proc'):
        if not eintrag.isdigit():
            continue
        pid = int(eintrag)
        if pid in eigen:
            continue
        try:
            with open(f'/proc/{pid}/cmdline', 'rb') as f:
                zeile = f.read().replace(b'\0', b' ').decode('utf-8', 'replace')
        except OSError:
            continue
        if merkmal in zeile:
            return pid
    return None


def wolken_zaehlen(wartezeit):
    """Zaehlt je Topic die eingehenden Wolken. Leere Wolken zaehlen mit -
    entscheidend ist, DASS veroeffentlicht wird."""
    import rclpy
    from rclpy.qos import QoSProfile, QoSReliabilityPolicy
    from sensor_msgs.msg import PointCloud2

    rclpy.init()
    n = rclpy.create_node('nahbereich_pruefen')
    zaehler = {t: 0 for t in TOPICS}
    punkte = {t: None for t in TOPICS}
    qos = QoSProfile(depth=5, reliability=QoSReliabilityPolicy.BEST_EFFORT)

    def mach(t):
        def cb(m):
            zaehler[t] += 1
            punkte[t] = m.width
        return cb

    for t in TOPICS:
        n.create_subscription(PointCloud2, t, mach(t), qos)
    ende = time.monotonic() + wartezeit
    while rclpy.ok() and time.monotonic() < ende:
        rclpy.spin_once(n, timeout_sec=0.1)
    n.destroy_node()
    rclpy.shutdown()
    return zaehler, punkte


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--still', action='store_true',
                   help='nichts ausgeben, nur den Rueckgabewert setzen')
    p.add_argument('--wartezeit', type=float, default=WARTEZEIT_S)
    args = p.parse_args()

    def sag(*a):
        if not args.still:
            print(*a)

    fehler = []

    if not modul_geladen():
        fehler.append('Kernelmodul ch34x_mphsi_master ist nicht geladen. '
                      'Nach einem Kernel-Update neu bauen: '
                      'cd ~/ch34x_mphsi_master_linux/driver && make && '
                      'sudo make install')
        sag('  [FEHLT]  Kernelmodul ch34x_mphsi_master')
    else:
        sag('  [ok]     Kernelmodul ch34x_mphsi_master geladen')

    bus = ch341_bus()
    if bus is None:
        fehler.append('Kein CH341-I2C-Bus vorhanden - der Adapter wird nicht '
                      'bedient.')
        sag('  [FEHLT]  CH341-I2C-Bus')
    else:
        sag(f'  [ok]     CH341-I2C-Bus: i2c-{bus}')

    pid = prozess_laeuft('vl53_near_field/lib')
    if pid is None:
        fehler.append('Der Knoten vl53_near_field laeuft nicht.')
        sag('  [FEHLT]  Knoten vl53_near_field')
    else:
        sag(f'  [ok]     Knoten vl53_near_field laeuft (PID {pid})')

    mon = prozess_laeuft('collision_monitor')
    if mon is None:
        fehler.append('Der collision_monitor laeuft nicht - Fahrbefehle auf '
                      'cmd_vel_smoothed erreichen den Antrieb gar nicht.')
        sag('  [FEHLT]  collision_monitor')
    else:
        sag(f'  [ok]     collision_monitor laeuft (PID {mon})')

    # Der eigentliche Test: Ein laufender Knoten beweist nichts. Es zaehlt, ob
    # tatsaechlich Wolken ankommen.
    if pid is not None:
        try:
            zaehler, punkte = wolken_zaehlen(args.wartezeit)
        except Exception as exc:
            fehler.append(f'Punktwolken nicht pruefbar: {exc}')
            zaehler, punkte = {t: 0 for t in TOPICS}, {t: None for t in TOPICS}
        for t in TOPICS:
            if zaehler[t] < MINDEST_WOLKEN:
                fehler.append(f'{t}: nur {zaehler[t]} Wolken in '
                              f'{args.wartezeit:.0f} s - der Sensor liefert nicht.')
                sag(f'  [FEHLT]  {t}: {zaehler[t]} Wolken')
            else:
                sag(f'  [ok]     {t}: {zaehler[t]} Wolken, '
                    f'zuletzt {punkte[t]} Punkte')

    if fehler:
        sag('')
        sag('NAHBEREICHSSCHUTZ NICHT EINSATZBEREIT:')
        for f in fehler:
            sag(f'  - {f}')
        sag('')
        sag('Keine autonome Fahrt. Fuer eine beaufsichtigte Fahrt muss eine')
        sag('anwesende Person den Not-Aus halten und den Weg im Blick haben.')
        return 1

    sag('')
    sag('Nahbereichsschutz einsatzbereit.')
    sag('Hinweis: Leere Wolken sind im freien Raum korrekt - der Schutz wirkt')
    sag('nur innerhalb von 50 cm. Ob er BREMST, zeigt erst ein Hindernis in')
    sag('der Zone.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
