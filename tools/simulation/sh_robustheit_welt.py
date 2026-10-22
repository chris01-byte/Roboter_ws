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


class RobustheitsWelt(World):
    def __init__(self, door_m, start):
        super().__init__(door_m, start)
        self.door_m = door_m
        self.niedrig = []                # (Rechteck, Höhe über Boden)
        self.verspaetungen = []          # Timerlücken > 30 ms
        self.verspaetungen_zeit = []     # zugehörige Zeit (s seit Start)
        self.geschlossene_tueren = []
        self.engste_stelle = None        # Pose beim kleinsten Abstand
        self.zeit_s = None               # vom Treiber gesetzt (Sekunden seit Start)
        self.mitte_min = None            # kleinster Abstand der Robotermitte

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
            super().integrate(command, dt/schritte, tau)
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

    def karte_zu_welt(self, punkte):
        """Karten-/Odometrierahmen (Ursprung = Startpose) in Weltkoordinaten."""
        p = np.asarray(punkte, dtype=float).reshape(-1, 2)
        c, s = math.cos(self.start[2]), math.sin(self.start[2])
        return p@np.array([[c, s], [-s, c]]) + self.start[:2]

    # --- Bewertung (Manifest v2) ---------------------------------------------
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
