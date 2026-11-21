"""Welt der Robustheitssimulation (Abnahmestufe 2, Selbstheilungsbetrieb).

Erweitert die AP06-Welt (`ap06_world.World`, unverändert) um das, was die
fünf Störfälle brauchen:

- niedrige Hindernisse (Höhe über Boden), die der LiDAR in 0,66 m Höhe nicht
  sieht, die VL53 aber treffen; der Kollisionsprüfer kennt sie trotzdem;
- Türen, die sich während der Fahrt schließen lassen;
- Integration auch nach verspäteten Timern (unter Rechenlast) in höchstens
  10-ms-Schritten, statt abzubrechen. Jede Lücke wird protokolliert;
- Abstand eines Punkts (Robotermitte, Planpose) zum nächsten Hindernis, um
  enge Stellen dem Planer oder dem Regler zuzuordnen.

Die Welt veröffentlicht nichts und liefert dem Produkt keine Karte.
"""
import math

import numpy as np
from scipy.ndimage import label

from ap06_world import World, chassis_clearance, rectangle

BODEN_Z = -0.09          # Boden im base_link-Rahmen (base_link 0,09 m über Boden)
MAX_SCHRITT_S = 0.01
# Echtes Gehäuse ohne das 2-cm-Polster der Kostenkarte (nav2_params_real.yaml).
# Die Prüfkontur der Simulation (ap06_world.chassis) ist die gepolsterte Kontur;
# „Kontakt“ heißt dort: näher als 2 cm am echten Gehäuse (KM-1, 09.11.2026).
KOERPER = ((-.11, -.23), (.31, -.23), (.31, .23), (-.11, .23))


RADABSTAND_M = 0.3845


def antrieb_schritt(geschwindigkeit, soll, dt, tau_auf_s, tau_ab_s):
    """Ein Zeitschritt der Radantriebe mit Anfahr- und Bremsrampe.

    Gemessen am Roboter (base_hardware_params.yaml, 14.08.2026): Mit
    ``accel_ms=2000`` ergab ein 1,0-s-Fahrimpuls mit 0,12 m/s nur 0,0439 m
    Encoderweg; gebremst wird mit 400 ms. Das Modell ist je Rad eine
    Verzögerung erster Ordnung, träge beim Schnellerwerden (``tau_auf_s``),
    zügig beim Langsamerwerden oder Richtungswechsel (``tau_ab_s``). Mit
    1,3 s / 0,15 s trifft es den gemessenen Impuls auf etwa 5 %.
    """
    v, w = float(geschwindigkeit[0]), float(geschwindigkeit[1])
    sv, sw = float(soll[0]), float(soll[1])
    raeder = [v - w*RADABSTAND_M/2, v + w*RADABSTAND_M/2]
    ziele = [sv - sw*RADABSTAND_M/2, sv + sw*RADABSTAND_M/2]
    neu = []
    for ist, ziel in zip(raeder, ziele):
        schneller = abs(ziel) > abs(ist) and (ist*ziel >= 0.)
        tau = tau_auf_s if schneller else tau_ab_s
        neu.append(ist + (ziel-ist)*(1.-math.exp(-dt/tau)))
    return np.array([(neu[0]+neu[1])/2, (neu[1]-neu[0])/RADABSTAND_M])


def koerper(pose):
    x, y, yaw = pose
    c, s = math.cos(yaw), math.sin(yaw)
    return np.array([(x+c*a-s*b, y+s*a+c*b) for a, b in KOERPER])


def koerper_abstand(pose, obstacles):
    """Abstand des echten Gehäuses zum nächsten Hindernis (0 = Berührung)."""
    from ap06_world import polygon_distance
    body = koerper(pose)
    return min((polygon_distance(body, np.asarray(o)) for o in obstacles), default=math.inf)


class RobustheitsWelt(World):
    def __init__(self, door_m, start, zusatz=(), niedrig=()):
        super().__init__(door_m, start)
        # Zusätzliche feste Möbel (nur Experiment-Manifeste), je [x0, x1, y0, y1].
        for x0, x1, y0, y1 in zusatz:
            self.obstacles.append(rectangle(x0, x1, y0, y1))
        self.door_m = door_m
        self.niedrig = []                # (Rechteck, Höhe über Boden)
        # Feste niedrige Möbel ab Start (nur Experiment-Manifeste), je
        # [Mitte x, Mitte y, Kantenlänge, Höhe]: z. B. ein 40-cm-Mülleimer, den der
        # LiDAR in 0,66 m Höhe nicht sieht, die VL53 aber schon (SH-5 Fahrt 3).
        for cx, cy, groesse, hoehe in niedrig:
            self.setze_niedriges_hindernis((cx, cy), groesse, hoehe)
        self.verspaetungen = []          # Timerlücken > 30 ms
        self.verspaetungen_zeit = []     # zugehörige Zeit (s seit Start)
        self.geschlossene_tueren = []
        self.engste_stelle = None        # Pose beim kleinsten Abstand
        self.zeit_s = None               # vom Treiber gesetzt (Sekunden seit Start)
        self.mitte_min = None            # kleinster Abstand der Robotermitte
        self.minimum_koerper = math.inf  # kleinster Abstand des echten Gehäuses
        self.koerper_engste = None       # Pose und Zeit dazu (SH-8b, 13.11.2026)
        self.koerper_verlauf = []        # jede neue Annäherung: (t_s, Abstand)
        # Optionales Antriebsmodell (tau_auf_s, tau_ab_s): siehe ``antrieb_schritt``.
        self.antrieb = None

    # --- Szenarioeingriffe ----------------------------------------------
    def schliesse_tuer(self, seite):
        """Linke Tür bei x=-0,6 oder rechte Tür bei x=+0,6 schließen."""
        x = {'links': -.6, 'rechts': .6}[seite]
        self.obstacles.append(rectangle(x-.04, x+.04, -self.door_m/2, self.door_m/2))
        self.geschlossene_tueren.append(seite)
        self.checked_pose = None

    def setze_niedriges_hindernis(self, mitte, groesse, hoehe):
        x, y = mitte
        half = groesse/2
        box = rectangle(x-half, x+half, y-half, y+half)
        self.niedrig.append((box, float(hoehe)))
        self.checked_pose = None
        return box

    def frei(self, box, abstand=0.05):
        """Kein Überlapp mit Wänden oder dem Roboter (Vorbedingung beim Setzen)."""
        objekte = [o for o in self.obstacles]
        if chassis_clearance(self.pose, [box]) <= abstand:
            return False
        lo, hi = box.min(axis=0), box.max(axis=0)
        for o in objekte:
            olo, ohi = o.min(axis=0), o.max(axis=0)
            if (lo < ohi + abstand).all() and (olo - abstand < hi).all():
                return False
        return True

    def pruefe_koerper(self):
        """Nur nahe an einem Hindernis rechnen (Prüfkontur unter 3 cm)."""
        if self.minimum_clearance >= .03:
            return
        alle = list(self.obstacles) + [b for b, _ in self.niedrig]
        abstand = koerper_abstand(self.pose, alle)
        if abstand < self.minimum_koerper:
            niedrig = [b for b, _ in self.niedrig]
            self.koerper_engste = dict(
                pose=[round(float(v), 3) for v in self.pose],
                geschwindigkeit=[round(float(v), 3) for v in self.velocity],
                abstand_m=round(float(abstand), 4), t_s=self.zeit_s,
                hindernis_niedrig=bool(niedrig) and
                koerper_abstand(self.pose, niedrig) <= abstand + 1e-9)
            self.koerper_verlauf.append((self.zeit_s, round(float(abstand), 4)))
        self.minimum_koerper = min(self.minimum_koerper, abstand)

    # --- Physik -----------------------------------------------------------
    def integrate(self, command, dt, tau=.05):
        if dt <= 0.:
            return
        if dt > .03:
            self.verspaetungen.append(round(dt, 4))
            self.verspaetungen_zeit.append(self.zeit_s)
        schritte = max(1, math.ceil(dt/MAX_SCHRITT_S))
        for _ in range(schritte):
            vorher = self.minimum_clearance
            if self.antrieb is None:
                super().integrate(command, dt/schritte, tau)
            else:
                # Räder folgen dem Sollwert träge (gemessene Motorrampe); die
                # Basisklasse übernimmt die so berechnete Geschwindigkeit sofort.
                ziel = antrieb_schritt(self.velocity, command, dt/schritte, *self.antrieb)
                super().integrate(ziel, dt/schritte, 1e-9)
            if self.niedrig:
                frei = chassis_clearance(self.pose, [b for b, _ in self.niedrig])
                self.minimum_clearance = min(self.minimum_clearance, frei)
                self.collision |= frei <= 0.
            if self.minimum_clearance < vorher:
                self.engste_stelle = dict(
                    pose=[round(float(v), 3) for v in self.pose],
                    geschwindigkeit=[round(float(v), 3) for v in self.velocity],
                    abstand_m=round(float(self.minimum_clearance), 4),
                    mitte_abstand_m=round(self.punkt_abstand(self.pose[:2]), 4),
                    t_s=self.zeit_s)
        mitte = self.punkt_abstand(self.pose[:2])
        if self.mitte_min is None or mitte < self.mitte_min['abstand_m']:
            self.mitte_min = dict(abstand_m=round(mitte, 4),
                                  pose=[round(float(v), 3) for v in self.pose], t_s=self.zeit_s)

    def naechstes_hindernis(self):
        """(Rechteck, niedrig?) mit dem kleinsten Abstand zur Kontur."""
        boxen = [(b, False) for b in self.obstacles] + [(b, True) for b, _ in self.niedrig]
        abstaende = [chassis_clearance(self.pose, [b]) for b, _ in boxen]
        return boxen[int(np.argmin(abstaende))]

    def punkt_abstand(self, punkt):
        """Abstand eines Punkts zum nächsten Hindernis (alle achsparallel)."""
        return float(self.punkte_abstand(np.asarray(punkt, dtype=float)[:2])[0])

    def punkte_abstand(self, punkte):
        boxen = list(self.obstacles) + [b for b, _ in self.niedrig]
        lo = np.array([b.min(axis=0) for b in boxen])[None]
        hi = np.array([b.max(axis=0) for b in boxen])[None]
        p = np.asarray(punkte, dtype=float).reshape(-1, 2)[:, None]
        return np.linalg.norm(np.maximum(np.maximum(lo-p, 0.), p-hi), axis=2).min(axis=1)

    def abstand_niedrig(self, punkte):
        """Kleinster Abstand der Punkte zu den niedrigen Hindernissen (inf ohne)."""
        if not self.niedrig:
            return math.inf
        lo = np.array([b.min(axis=0) for b, _ in self.niedrig])[None]
        hi = np.array([b.max(axis=0) for b, _ in self.niedrig])[None]
        p = np.asarray(punkte, dtype=float).reshape(-1, 2)[:, None]
        if not len(p):
            return math.inf
        return float(np.linalg.norm(np.maximum(np.maximum(lo-p, 0.), p-hi), axis=2).min())

    def karte_zu_welt(self, punkte):
        """Karten-/Odometrierahmen (Ursprung = Startpose) in Weltkoordinaten."""
        p = np.asarray(punkte, dtype=float).reshape(-1, 2)
        c, s = math.cos(self.start[2]), math.sin(self.start[2])
        return p@np.array([[c, s], [-s, c]]) + self.start[:2]

    # --- Bewertung (Manifest v2) ---------------------------------------------
    def kartenfehler_orte(self, occupancy, resolution, origin, schwelle_m=.1, anzahl=12):
        """Diagnose zu ``map_oracle``: wo liegen belegte Zellen weiter als ``schwelle_m`` von Wänden?

        Gleiche Rechnung wie das Abnahmekriterium (belegt = Wert >= 65, Abstand zu
        den Kanten der festen Hindernisse), zusätzlich mit Ort in Weltkoordinaten.
        """
        a = np.asarray(occupancy)
        row, col = np.nonzero(a >= 65)
        lokal = np.stack((origin[0]+(col+.5)*resolution, origin[1]+(row+.5)*resolution), axis=1)
        punkte = self.karte_zu_welt(lokal)
        abstand = np.full(len(punkte), math.inf)
        for o in self.obstacles:
            for start, end in zip(o, np.roll(o, -1, axis=0)):
                v = end-start
                f = np.clip((punkte-start)@v/(v@v), 0., 1.)
                abstand = np.minimum(abstand, np.linalg.norm(punkte-start-f[:, None]*v, axis=1))
        reihenfolge = np.argsort(-abstand)
        ueber = reihenfolge[abstand[reihenfolge] > schwelle_m]
        return {'schwelle_m': schwelle_m, 'belegte_zellen': int(len(punkte)),
                'ueber_schwelle': int(len(ueber)),
                'orte': [[round(float(punkte[i, 0]), 3), round(float(punkte[i, 1]), 3),
                          round(float(abstand[i]), 3)] for i in ueber[:anzahl]]}

    def abdeckung_erreichbar(self, occupancy, resolution, origin):
        """Anteil der vom Start aus erreichbaren Fläche, den die SLAM-Karte frei kennt.

        Erreichbar heißt: freie Zelle der Welt, über freie Zellen mit dem Start
        verbunden (Hindernisse einschließlich geschlossener Türen trennen).
        Fläche hinter einer geschlossenen Tür zählt nicht mit.
        """
        a = np.asarray(occupancy)
        ys, xs = np.mgrid[-1.4:1.4:resolution, -2.8:2.8:resolution]
        cx, cy = xs+resolution/2, ys+resolution/2
        frei = (cx < -.6) | (cx > .6) | (np.abs(cy) < .42)
        for o in list(self.obstacles) + [b for b, _ in self.niedrig]:
            lo, hi = o.min(axis=0), o.max(axis=0)
            frei &= ~((cx >= lo[0]) & (cx <= hi[0]) & (cy >= lo[1]) & (cy <= hi[1]))
        teile, _ = label(frei)
        r = int(np.clip(round((self.start[1]+1.4)/resolution-.5), 0, frei.shape[0]-1))
        c = int(np.clip(round((self.start[0]+2.8)/resolution-.5), 0, frei.shape[1]-1))
        if teile[r, c] == 0:
            return None
        erreichbar = teile == teile[r, c]
        punkte = np.stack((cx[erreichbar], cy[erreichbar]), axis=1)
        idx = np.floor((self.local(punkte)-np.asarray(origin))/resolution).astype(int)
        im = (idx[:, 0] >= 0) & (idx[:, 0] < a.shape[1]) & (idx[:, 1] >= 0) & (idx[:, 1] < a.shape[0])
        gesehen = np.zeros(len(punkte), dtype=bool)
        gesehen[im] = a[idx[im, 1], idx[im, 0]] == 0
        return {'erreichbar_zellen': int(len(punkte)), 'erreichbar_beobachtet': int(gesehen.sum()),
                'erreichbar_anteil': float(gesehen.mean())}

    # --- Sensoren ---------------------------------------------------------
    def cone_returns(self, mount, directions, maximum=4.):
        result = super().cone_returns(mount, directions, maximum)
        if not self.niedrig:
            return result
        directions = np.asarray(directions, dtype=float)
        yaw = self.pose[2]
        c, s = math.cos(yaw), math.sin(yaw)
        origin = np.array([self.pose[0]+c*mount[0]-s*mount[1],
                           self.pose[1]+s*mount[0]+c*mount[1], mount[2]])
        world_dirs = np.column_stack((c*directions[:, 0]-s*directions[:, 1],
                                      s*directions[:, 0]+c*directions[:, 1], directions[:, 2]))
        best = np.full(len(world_dirs), np.inf)
        for box, hoehe in self.niedrig:
            low = np.array([*box.min(axis=0), BODEN_Z])
            high = np.array([*box.max(axis=0), BODEN_Z+hoehe])
            with np.errstate(divide='ignore', invalid='ignore'):
                t0, t1 = (low-origin)/world_dirs, (high-origin)/world_dirs
            parallel = np.abs(world_dirs) < 1e-12
            outside = ((origin < low) | (origin > high)) & parallel
            near = np.where(parallel, -np.inf, np.minimum(t0, t1)).max(axis=1)
            far = np.where(parallel, np.inf, np.maximum(t0, t1)).min(axis=1)
            hit = (far >= np.maximum(0., near)) & ~outside.any(axis=1)
            best = np.minimum(best, np.where(hit, np.maximum(0., near), np.inf))
        best = np.where(best <= maximum, best, np.inf)
        nearest = np.minimum(np.where(np.isnan(result), np.inf, result), best)
        return np.where(np.isfinite(nearest), nearest, np.nan)


def rechteck_minus(rechteck, oeffnung):
    """Achsparalleles Rechteck (x0, x1, y0, y1) ohne die Öffnung; Liste der Reste."""
    x0, x1, y0, y1 = rechteck
    ox0, ox1, oy0, oy1 = oeffnung
    if ox0 >= x1 or ox1 <= x0 or oy0 >= y1 or oy1 <= y0:
        return [tuple(rechteck)]
    reste = [(x0, min(x1, ox0), y0, y1), (max(x0, ox1), x1, y0, y1),
             (max(x0, ox0), min(x1, ox1), y0, min(y1, oy0)),
             (max(x0, ox0), min(x1, ox1), max(y0, oy1), y1)]
    return [r for r in reste if r[1]-r[0] > 1e-9 and r[3]-r[2] > 1e-9]


class GrundrissWelt(RobustheitsWelt):
    """Frei beschriebener Grundriss für Erkundungsversuche (Fahrplan §9 Schritt 2).

    ``raeume``: Name -> Innenfläche [x0, x1, y0, y1]. ``durchgaenge``: freie
    Rechtecke durch die Wände (Türöffnungen). Wände entstehen als Streifen um
    jeden Raum, ohne Räume und Durchgänge. ``moebel`` sind raumhohe Rechtecke
    (LiDAR und VL53 sehen sie), ``niedrig`` Rechtecke [x0, x1, y0, y1, Höhe]
    unter der LiDAR-Ebene (nur die VL53 sehen sie, die SLAM-Karte kennt sie
    nicht). Die Welt liefert dem Produkt weiterhin keine Karte.
    """
    WAND_M = 0.05

    def __init__(self, start, raeume, durchgaenge=(), moebel=(), niedrig=(), antrieb=None):
        super().__init__(.8, start)
        self.raeume = {str(name): tuple(float(v) for v in box) for name, box in raeume.items()}
        self.durchgaenge = [tuple(float(v) for v in d) for d in durchgaenge]
        if not self.raeume:
            raise ValueError('grundriss braucht mindestens einen Raum')
        frei = list(self.raeume.values()) + self.durchgaenge
        t = self.WAND_M
        streifen = []
        for x0, x1, y0, y1 in self.raeume.values():
            streifen += [(x0-t, x0, y0-t, y1+t), (x1, x1+t, y0-t, y1+t),
                         (x0-t, x1+t, y0-t, y0), (x0-t, x1+t, y1, y1+t)]
        for oeffnung in frei:
            streifen = [rest for wand in streifen for rest in rechteck_minus(wand, oeffnung)]
        self.obstacles = [rectangle(*wand) for wand in streifen]
        self.obstacles += [rectangle(*(float(v) for v in m)) for m in moebel]
        for x0, x1, y0, y1, hoehe in niedrig:
            self.niedrig.append((rectangle(float(x0), float(x1), float(y0), float(y1)),
                                 float(hoehe)))
        if antrieb:
            self.antrieb = (float(antrieb['tau_auf_s']), float(antrieb['tau_ab_s']))
            if not (0. < self.antrieb[1] <= self.antrieb[0] <= 10.):
                raise ValueError('antrieb: 0 < tau_ab_s <= tau_auf_s <= 10 erwartet')
        xs = [v for box in frei for v in box[:2]]
        ys = [v for box in frei for v in box[2:]]
        self.grenzen = (min(xs), max(xs), min(ys), max(ys))
        if self.raum_von(self.start[:2]) is None:
            raise ValueError('Startpose liegt in keinem Raum')

    def schliesse_tuer(self, seite):
        raise ValueError('schliesse_tuer gibt es nur in der festen Zwei-Raum-Welt')

    def raum_von(self, punkt):
        """Name des Raums, in dem der Punkt liegt, sonst None (Wand, Durchgang)."""
        x, y = float(punkt[0]), float(punkt[1])
        for name, (x0, x1, y0, y1) in self.raeume.items():
            if x0 <= x <= x1 and y0 <= y <= y1:
                return name
        return None

    def _referenz(self, resolution):
        """Zellmitten der Welt, Maske frei (Räume und Durchgänge ohne Hindernisse)."""
        gx0, gx1, gy0, gy1 = self.grenzen
        ys, xs = np.mgrid[gy0:gy1:resolution, gx0:gx1:resolution]
        cx, cy = xs+resolution/2, ys+resolution/2
        frei = np.zeros(cx.shape, dtype=bool)
        for x0, x1, y0, y1 in list(self.raeume.values()) + self.durchgaenge:
            frei |= (cx >= x0) & (cx <= x1) & (cy >= y0) & (cy <= y1)
        for o in list(self.obstacles) + [b for b, _ in self.niedrig]:
            lo, hi = o.min(axis=0), o.max(axis=0)
            frei &= ~((cx >= lo[0]) & (cx <= hi[0]) & (cy >= lo[1]) & (cy <= hi[1]))
        return cx, cy, frei

    def _erreichbar(self, resolution):
        cx, cy, frei = self._referenz(resolution)
        teile, _ = label(frei)
        gx0, _, gy0, _ = self.grenzen
        r = int(np.clip(math.floor((self.start[1]-gy0)/resolution), 0, frei.shape[0]-1))
        c = int(np.clip(math.floor((self.start[0]-gx0)/resolution), 0, frei.shape[1]-1))
        if teile[r, c] == 0:
            return cx, cy, None
        return cx, cy, teile == teile[r, c]

    def _gesehen(self, punkte, occupancy, resolution, origin):
        a = np.asarray(occupancy)
        idx = np.floor((self.local(punkte)-np.asarray(origin))/resolution).astype(int)
        im = (idx[:, 0] >= 0) & (idx[:, 0] < a.shape[1]) & (idx[:, 1] >= 0) & (idx[:, 1] < a.shape[0])
        gesehen = np.zeros(len(punkte), dtype=bool)
        gesehen[im] = a[idx[im, 1], idx[im, 0]] == 0
        return gesehen

    def abdeckung_erreichbar(self, occupancy, resolution, origin):
        cx, cy, erreichbar = self._erreichbar(resolution)
        if erreichbar is None:
            return None
        punkte = np.stack((cx[erreichbar], cy[erreichbar]), axis=1)
        gesehen = self._gesehen(punkte, occupancy, resolution, origin)
        return {'erreichbar_zellen': int(len(punkte)), 'erreichbar_beobachtet': int(gesehen.sum()),
                'erreichbar_anteil': float(gesehen.mean())}

    def raum_abdeckung(self, occupancy, resolution, origin):
        """Je Raum: Anteil seiner erreichbaren Fläche, den die SLAM-Karte frei kennt."""
        cx, cy, erreichbar = self._erreichbar(resolution)
        if erreichbar is None:
            return {}
        ergebnis = {}
        for name, (x0, x1, y0, y1) in self.raeume.items():
            maske = erreichbar & (cx >= x0) & (cx <= x1) & (cy >= y0) & (cy <= y1)
            if not maske.any():
                ergebnis[name] = None
                continue
            punkte = np.stack((cx[maske], cy[maske]), axis=1)
            ergebnis[name] = round(float(self._gesehen(punkte, occupancy, resolution, origin).mean()), 4)
        return ergebnis

    def map_oracle(self, occupancy, resolution, origin):
        a = np.asarray(occupancy)
        cx, cy, frei = self._referenz(resolution)
        punkte = np.stack((cx[frei], cy[frei]), axis=1)
        gesehen = self._gesehen(punkte, a, resolution, origin)
        fehler = self.kartenfehler_orte(a, resolution, origin, schwelle_m=0., anzahl=1)
        return {'reference_free_cells': int(len(punkte)),
                'reference_observed_cells': int(gesehen.sum()),
                'reference_observed_fraction': float(gesehen.mean()),
                'maximum_occupied_wall_error_m': fehler['orte'][0][2] if fehler['orte'] else 0.}
