"""Selbstheilender Erkundungsbetrieb: reine, ROS-freie Entscheidungslogik.

Konzept: docs/wohnungserkundung/KONZEPT_SELBSTHEILUNG.md (15.10.2026).

Drei Schichten mit klaren Rollen:
  1. Reaktive Sicherheit (collision_monitor mit VL53, Watchdog, Not-Aus) darf
     hart stoppen. Ein Stopp ist ein Pausieren, kein Missionsende.
  2. Nav2 plant (auch durch Unbekanntes) und weicht aus.
  3. Dieser Explorer entscheidet nur WOHIN und heilt Fehlschläge begrenzt.

Eine Mission endet nur bei echten Ausnahmen (``FATAL``), bei erschöpftem
Heilungsbudget bzw. ohne Fortschritt (``HELP``, Teilkarte bleibt nutzbar)
oder wenn die Erkundung abgeschlossen ist. Alles andere wird über die
Heilungsleiter behandelt: warten, neu versuchen, Ziel zurückstellen, sich
umsehen, entlang der eigenen Spur zurücksetzen, um Hilfe bitten.
"""
from dataclasses import dataclass, field
import math
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np
from scipy.ndimage import distance_transform_edt, label

FATAL = 'fatal'
HELP = 'help'
HEAL = 'heal'
WAIT = 'wait'

# Gründe, die sofort und endgültig stoppen. Ein aktiver Motor-Halt sieht wie
# ein Modbus-/Encoderfehler aus (AGENTS.md §2.3); deshalb werden Aktor- und
# Konfigurationsfehler nie automatisch "weggewartet".
_FATAL_EXACT = frozenset({
    'estop_active',
    'second_child_forbidden',
    'child_cancel_failed',
    'child_error',
    'collision_detected',
    'actuator_fault_latched',
    'ros_shutdown',
})
_FATAL_PREFIXES = ('hwt601_', 'hwt_fault', 'encoder_config_fault', 'actuator_')

# Quellen, die kurz fehlen dürfen: warten (H0), danach Hilfe statt Abbruch.
_WAIT_PREFIXES = (
    'estop_missing_stale', 'vl53_status_missing', 'vl53_cloud_missing',
    'lidar_missing', 'localization_missing', 'odometry_missing',
    'map_missing', 'map_stale', 'pose_missing', 'pose_stale',
    'hwt_hold', 'costmap_missing', 'costmap_stale',
)


def classify(reason: Optional[str]) -> str:
    """Ordnet einen Grund einer Behandlung zu: FATAL, WAIT oder HEAL.

    Unbekannte Gründe gelten als heilbar. Die Heilungsleiter ist begrenzt;
    ein dauerhaft wiederkehrender Fehler endet deshalb sicher bei HELP.
    """
    if not reason:
        return HEAL
    text = str(reason)
    if text in _FATAL_EXACT or text.startswith(_FATAL_PREFIXES):
        return FATAL
    if text.startswith(_WAIT_PREFIXES):
        return WAIT
    return HEAL


# Aktionen der Heilungsleiter.
RETRY = 'retry'            # H1: dasselbe Ziel nach kurzer Pause erneut
DEFER = 'defer'            # H2: Ziel zurückstellen, nächstes wählen
LOOK_AROUND = 'look_around'  # H3: Drehung im freien Drehkreis, Sicht gewinnen
TRACK_BACK = 'track_back'  # H4: entlang der eigenen Spur zurücksetzen
REQUEST_HELP = 'help'      # H5: Teilkarte behalten, Hilfe anfordern


@dataclass
class HealingLadder:
    """Begrenzte Eskalation für Fehlschläge ohne Fortschritt.

    ``streak`` zählt aufeinanderfolgende Fehlschläge ohne Fortschritt. Jeder
    echte Fortschritt (Ziel erreicht oder Kartengewinn) setzt die Leiter
    zurück. Das Gesamtbudget ``max_heals`` und ``no_progress_timeout_s``
    begrenzen die Mission unabhängig davon.
    """
    goal_retries: int = 1
    look_around_after: int = 3
    track_back_after: int = 5
    help_after: int = 8
    max_heals: int = 30
    no_progress_timeout_s: float = 600.
    heals: int = 0
    streak: int = 0
    looked_around: bool = False
    tracked_back: bool = False
    last_progress_at: Optional[float] = None
    history: List[dict] = field(default_factory=list)

    def __post_init__(self):
        if not (0 <= self.goal_retries and 1 <= self.look_around_after
                <= self.track_back_after <= self.help_after and self.max_heals >= 1
                and self.no_progress_timeout_s > 0):
            raise ValueError('healing ladder limits are inconsistent')

    def start(self, now: float):
        self.last_progress_at = now

    def progress(self, now: float):
        self.streak = 0
        self.looked_around = self.tracked_back = False
        self.last_progress_at = now

    def stalled(self, now: float) -> bool:
        return (self.last_progress_at is not None
                and now - self.last_progress_at > self.no_progress_timeout_s)

    def failure(self, now: float, reason: str, goal_attempts: int,
                track_back_available: bool, look_around_available: bool) -> str:
        """Nächste Aktion für einen heilbaren Fehlschlag."""
        self.heals += 1
        self.streak += 1
        if self.heals > self.max_heals or self.stalled(now) or self.streak >= self.help_after:
            action = REQUEST_HELP
        elif goal_attempts <= self.goal_retries:
            action = RETRY
        elif (self.streak >= self.look_around_after and not self.looked_around
                and look_around_available):
            self.looked_around = True
            action = LOOK_AROUND
        elif (self.streak >= self.track_back_after and not self.tracked_back
                and track_back_available):
            self.tracked_back = True
            action = TRACK_BACK
        else:
            action = DEFER
        self.history.append(dict(at=now, reason=reason, action=action,
                                 streak=self.streak, heals=self.heals))
        del self.history[:-40]
        return action

    def snapshot(self) -> dict:
        return dict(heals=self.heals, streak=self.streak, max_heals=self.max_heals,
                    looked_around=self.looked_around, tracked_back=self.tracked_back,
                    history=list(self.history))


class TrackRecorder:
    """Selbst gefahrene Spur im odom-Rahmen für die begrenzte Rückfahrt.

    Die Spur ist nachweislich frei befahren worden. Rückwärts wird nur gerade
    entlang des letzten, nahezu geraden Spurabschnitts gefahren, der hinter
    dem Roboter in seiner aktuellen Ausrichtung liegt. Seitliche Abweichung
    und Richtungswechsel begrenzen die zulässige Strecke.
    """
    def __init__(self, spacing_m: float = .02, max_points: int = 400):
        if not spacing_m > 0 or max_points < 2:
            raise ValueError('invalid track recorder limits')
        self.spacing_m = spacing_m
        self.max_points = max_points
        self.points: List[Tuple[float, float, float]] = []

    def clear(self):
        self.points.clear()

    def add(self, pose: Optional[Sequence[float]]):
        if pose is None or len(pose) < 3 or not all(math.isfinite(v) for v in pose[:3]):
            return
        x, y, yaw = (float(v) for v in pose[:3])
        if self.points and math.dist(self.points[-1][:2], (x, y)) < self.spacing_m:
            return
        self.points.append((x, y, yaw))
        del self.points[:-self.max_points]

    def straight_back_distance(self, pose: Sequence[float], max_distance_m: float,
                               lateral_tolerance_m: float = .03,
                               heading_tolerance_rad: float = .35) -> float:
        """Länge, die gerade rückwärts auf der eigenen Spur liegt (0 = keine)."""
        if pose is None or max_distance_m <= 0 or len(self.points) < 2:
            return 0.
        x, y, yaw = (float(v) for v in pose[:3])
        c, s = math.cos(yaw), math.sin(yaw)
        best = 0.
        previous_along = 0.
        for px, py, pyaw in reversed(self.points):
            dx, dy = px-x, py-y
            along = c*dx + s*dy          # >0 vor, <0 hinter dem Roboter
            lateral = -s*dx + c*dy
            heading = math.atan2(math.sin(pyaw-yaw), math.cos(pyaw-yaw))
            if along > 1e-3:
                break                     # Spur liegt vor dem Roboter: kein Rückweg
            if abs(lateral) > lateral_tolerance_m or abs(heading) > heading_tolerance_rad:
                break
            if along > previous_along + 1e-3:
                break                     # Spur kehrt um (z. B. Pendeln)
            previous_along = min(previous_along, along)
            best = max(best, -along)
            if best >= max_distance_m:
                return max_distance_m
        return min(best, max_distance_m)

    def consume(self, distance_m: float):
        """Nach erfolgter Rückfahrt den befahrenen Abschnitt nicht erneut nutzen."""
        if distance_m <= 0 or not self.points:
            return
        last = self.points[-1]
        while len(self.points) > 1 and math.dist(self.points[-1][:2], last[:2]) < distance_m:
            self.points.pop()


@dataclass(frozen=True)
class FrontierGoal:
    x: float
    y: float
    size_cells: int
    distance_m: float
    cost: float
    # Frontier-Zelle, aus der das (ggf. verschobene) Ziel stammt. Zurückgestellt
    # wird diese Stelle, nicht der Fahrpunkt: Mehrere Frontiers können auf
    # denselben geräumigen Punkt rücken.
    frontier_x: Optional[float] = None
    frontier_y: Optional[float] = None

    @property
    def frontier_xy(self) -> Tuple[float, float]:
        return (self.x if self.frontier_x is None else self.frontier_x,
                self.y if self.frontier_y is None else self.frontier_y)


def _coarse_obstacles(occupancy: np.ndarray, resolution: float, occupied_threshold: int,
                      work_resolution_m: float, unknown_blocks: bool = False):
    """Belegung blockweise auf ``work_resolution_m`` und Abstand dazu (Meter)."""
    height, width = occupancy.shape
    k = max(1, int(round(work_resolution_m/resolution)))
    rows, cols = -(-height//k), -(-width//k)
    occupied = np.zeros((rows*k, cols*k), dtype=bool)
    occupied[:height, :width] = (occupancy >= occupied_threshold) | (
        (occupancy < 0) if unknown_blocks else False)
    occupied = occupied.reshape(rows, k, cols, k).any(axis=(1, 3))
    distance = distance_transform_edt(~occupied)*k*resolution if occupied.any() \
        else np.full(occupied.shape, np.inf)
    return occupied, distance, k


def _fine(coarse: np.ndarray, k: int, shape: Tuple[int, int]) -> np.ndarray:
    return np.repeat(np.repeat(coarse, k, axis=0), k, axis=1)[:shape[0], :shape[1]]


def obstacle_clearance(occupancy: np.ndarray, resolution: float, *,
                       occupied_threshold: int = 65,
                       work_resolution_m: float = .05,
                       unknown_blocks: bool = False) -> Optional[np.ndarray]:
    """Abstand jeder Zelle zur nächsten belegten Zelle (Meter, nie zu groß).

    Gerechnet auf ``work_resolution_m`` von Blockmitte zu Blockmitte; ein
    Block gilt als belegt, sobald eine Feinzelle belegt ist. Abgezogen wird
    eine Blockdiagonale, damit der Wert den wahren Abstand nie überschätzt
    (Simulation 22.10.2026: ein überschätzter Abstand legte ein Ziel 0,31 m
    neben einen Pfosten, die Drehung dort streifte ihn). Unterschätzung
    höchstens etwa zwei Blockdiagonalen. Mit ``unknown_blocks`` zählt auch
    Unbekanntes als Hindernis: Ein Zielpunkt soll seinen Drehraum in bekannt
    freiem Raum haben (Simulation 22.10.2026: ein noch ungesehener Wandfuß
    galt als frei, das Ziel lag 6 cm vor der Wand).
    """
    occupancy = np.asarray(occupancy)
    if occupancy.ndim != 2 or occupancy.size == 0 or not resolution > 0:
        return None
    _, distance, k = _coarse_obstacles(occupancy, resolution, occupied_threshold,
                                       work_resolution_m, unknown_blocks)
    return _fine(np.maximum(distance - k*resolution*math.sqrt(2.), 0.), k, occupancy.shape)


def reachable_goal_mask(occupancy: np.ndarray, resolution: float,
                        robot_cell: Tuple[int, int], *, clearance_m: float = .2,
                        escape_m: float = .35, goal_tolerance_m: float = .3,
                        occupied_threshold: int = 65,
                        work_resolution_m: float = .05) -> Optional[np.ndarray]:
    """Zellen, die als Ziel vom Roboter aus erreichbar sein können.

    Grob und bewusst großzügig: Unbekanntes ist passierbar (wie Nav2
    ``allow_unknown``); gesperrt ist nur, was näher als ``clearance_m`` an
    einer belegten Zelle liegt. ``clearance_m`` liegt unter dem Nav2-Radius,
    damit nur eindeutig abgeschnittene Bereiche herausfallen, etwa hinter
    einer geschlossenen Tür (Lücke unter etwa ``2*clearance_m``).

    Im Umkreis ``escape_m`` um den Roboter zählt nur Belegtes selbst. Eine
    Startpose dicht an einem Pfosten gilt damit nicht als „alles
    unerreichbar“; dann heilt weiter die Leiter. Ein Ziel ist zulässig, wenn
    eine erreichbare Zelle höchstens ``goal_tolerance_m`` entfernt liegt
    (Nav2-Plantoleranz). Gerechnet wird auf ``work_resolution_m`` (Zelle
    belegt, wenn eine Feinzelle belegt ist). ``None``: Roboter außerhalb der
    Karte, keine Aussage möglich.
    """
    occupancy = np.asarray(occupancy)
    if occupancy.ndim != 2 or occupancy.size == 0 or not resolution > 0:
        return None
    height, width = occupancy.shape
    row, col = (int(v) for v in robot_cell)
    if not (0 <= row < height and 0 <= col < width):
        return None
    occupied, distance, k = _coarse_obstacles(occupancy, resolution, occupied_threshold,
                                              work_resolution_m)
    coarse_res = k*resolution
    rows, cols = occupied.shape
    r0, c0 = row//k, col//k
    rr, cc = np.mgrid[0:rows, 0:cols]
    escape = np.hypot(rr-r0, cc-c0)*coarse_res <= escape_m
    passable = ~occupied & ((distance >= clearance_m) | escape)
    labels, _ = label(passable, structure=np.ones((3, 3), dtype=bool))
    seeds = np.unique(labels[escape & passable])
    seeds = seeds[seeds > 0]
    reachable = np.isin(labels, seeds)
    if not reachable.any():
        return np.zeros(occupancy.shape, dtype=bool)
    near = distance_transform_edt(~reachable)*coarse_res <= goal_tolerance_m
    return _fine(near, k, (height, width))


def frontier_goals(occupancy: np.ndarray, resolution: float,
                   cell_to_world: Callable[[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]],
                   robot_xy: Sequence[float], *, min_size_cells: int = 5,
                   blacklist: Sequence[Sequence[float]] = (), blacklist_radius_m: float = .5,
                   min_distance_m: float = .3, gain_scale: float = .5,
                   max_goals: int = 20,
                   allowed: Optional[np.ndarray] = None,
                   clearance: Optional[np.ndarray] = None,
                   goal_clearance_m: float = 0.,
                   goal_shift_max_m: float = 0.) -> List[FrontierGoal]:
    """Schnelle Frontier-Auswahl ohne Sichtprognose (anytime, Millisekunden).

    Frontier = freie Zelle mit unbekanntem 4-Nachbarn; Cluster mit
    8-Nachbarschaft. Ziel je Cluster ist seine dem Roboter nächste Zelle.
    Kosten = Entfernung - gain_scale * Clusterlänge. Nav2 plant den Weg und
    darf dabei Unbekanntes queren; ein nicht erreichtes Ziel wird über die
    Heilungsleiter zurückgestellt. ``allowed`` (siehe
    ``reachable_goal_mask``) schließt nur eindeutig abgeschnittene Zellen aus.

    Mit ``clearance`` (siehe ``obstacle_clearance``) wählt jeder Cluster die
    nächste Zelle mit mindestens ``goal_clearance_m`` Abstand zu Belegtem,
    sonst seine Zelle mit dem größten Abstand. Eine Frontier quer über einer
    Türöffnung zielt damit auf die Türmitte statt auf die Pfostenecke; kein
    Cluster fällt dadurch weg. Hat auch die geräumigste Zelle weniger Abstand
    (Frontier nur an einer Wand entlang), rückt das Ziel auf die nächste
    bekannt freie Zelle mit ``goal_clearance_m`` innerhalb
    ``goal_shift_max_m``, gibt es keine, auf die geräumigste bekannt freie
    Zelle dort: Der Roboter soll dort stehen und sich drehen können; der
    LiDAR sieht die Frontier auch von dort.
    """
    occupancy = np.asarray(occupancy)
    if occupancy.ndim != 2 or occupancy.size == 0 or not resolution > 0:
        return []
    free = occupancy == 0
    unknown = occupancy < 0
    adjacent = np.zeros_like(free)
    adjacent[1:, :] |= unknown[:-1, :]
    adjacent[:-1, :] |= unknown[1:, :]
    adjacent[:, 1:] |= unknown[:, :-1]
    adjacent[:, :-1] |= unknown[:, 1:]
    frontier = free & adjacent
    labels, count = label(frontier, structure=np.ones((3, 3), dtype=bool))
    if count == 0:
        return []
    rows, cols = np.nonzero(labels)
    ids = labels[rows, cols]
    wx, wy = cell_to_world(rows, cols)
    wx, wy = np.asarray(wx, dtype=float), np.asarray(wy, dtype=float)
    distance = np.hypot(wx-robot_xy[0], wy-robot_xy[1])
    sizes = np.bincount(ids, minlength=count+1)
    blocked = np.zeros(len(ids), dtype=bool)
    for bx, by in blacklist:
        blocked |= np.hypot(wx-bx, wy-by) <= blacklist_radius_m
    blocked |= distance < min_distance_m
    if allowed is not None:
        blocked |= ~np.asarray(allowed, dtype=bool)[rows, cols]
    spacious = None
    if clearance is not None and goal_clearance_m > 0:
        clearance = np.asarray(clearance)
        spacious = free
    goals = []
    for cluster in range(1, count+1):
        if sizes[cluster] < min_size_cells:
            continue
        members = np.nonzero((ids == cluster) & ~blocked)[0]
        if not len(members):
            continue
        if spacious is not None:
            room = clearance[rows[members], cols[members]]
            wide = room >= goal_clearance_m
            members = members[wide] if wide.any() else members[room >= room.max()]
        best = members[np.argmin(distance[members])]
        gx, gy = float(wx[best]), float(wy[best])
        if spacious is not None and clearance[rows[best], cols[best]] < goal_clearance_m:
            shifted = _nearest_spacious(spacious, clearance, goal_clearance_m, rows[best],
                                        cols[best], resolution, goal_shift_max_m, cell_to_world)
            if shifted is not None:
                gx, gy = shifted
        reach = math.hypot(gx-robot_xy[0], gy-robot_xy[1])
        size = int(sizes[cluster])
        goals.append(FrontierGoal(gx, gy, size, reach,
                                  float(distance[best] - gain_scale*size*resolution),
                                  float(wx[best]), float(wy[best])))
    goals.sort(key=lambda g: (g.cost, g.distance_m))
    return goals[:max_goals]


def _nearest_spacious(free: np.ndarray, clearance: np.ndarray, wanted_m: float, row: int,
                      col: int, resolution: float, max_m: float,
                      cell_to_world) -> Optional[Tuple[float, float]]:
    """Freie Zelle im Umkreis ``max_m`` mit ``wanted_m`` Abstand (die nächste),
    sonst die geräumigste dort (Weltkoordinaten); ``None`` ohne Verbesserung."""
    span = int(math.ceil(max_m/resolution))
    if span <= 0:
        return None
    r0, r1 = max(0, row-span), min(free.shape[0], row+span+1)
    c0, c1 = max(0, col-span), min(free.shape[1], col+span+1)
    rr, cc = np.nonzero(free[r0:r1, c0:c1])
    if not len(rr):
        return None
    d = np.hypot(rr+r0-row, cc+c0-col)*resolution
    room = clearance[rr+r0, cc+c0]
    inside = d <= max_m
    wide = inside & (room >= wanted_m)
    if wide.any():
        i = int(np.argmin(np.where(wide, d, np.inf)))
    else:
        if not inside.any() or room[inside].max() <= clearance[row, col]:
            return None
        best = inside & (room >= room[inside].max())
        i = int(np.argmin(np.where(best, d, np.inf)))
    x, y = cell_to_world(np.array([rr[i]+r0]), np.array([cc[i]+c0]))
    return float(np.asarray(x)[0]), float(np.asarray(y)[0])


def frontier_cells_remaining(occupancy: np.ndarray, min_size_cells: int = 5) -> int:
    """Anzahl der Frontier-Cluster ausreichender Größe (ohne Sperrliste)."""
    occupancy = np.asarray(occupancy)
    if occupancy.ndim != 2 or occupancy.size == 0:
        return 0
    free, unknown = occupancy == 0, occupancy < 0
    adjacent = np.zeros_like(free)
    adjacent[1:, :] |= unknown[:-1, :]
    adjacent[:-1, :] |= unknown[1:, :]
    adjacent[:, 1:] |= unknown[:, :-1]
    adjacent[:, :-1] |= unknown[:, 1:]
    labels, count = label(free & adjacent, structure=np.ones((3, 3), dtype=bool))
    if count == 0:
        return 0
    sizes = np.bincount(labels.ravel(), minlength=count+1)[1:]
    return int(np.count_nonzero(sizes >= min_size_cells))


def rotation_clear(costs: np.ndarray, world_to_cell: Callable[[float, float], Tuple[int, int]],
                   resolution: float, center_xy: Sequence[float], radius_m: float,
                   lethal: int = 100) -> bool:
    """Drehkreis frei von gemessenen Hindernissen? Unbekanntes blockiert nicht.

    Geprüft wird die globale Kostenkarte: nur belegte Zellen (``lethal``)
    innerhalb des Drehradius verbieten die Drehung. Der Kollisionsmonitor mit
    den VL53 bleibt während der Drehung aktiv.
    """
    costs = np.asarray(costs)
    if costs.ndim != 2 or not resolution > 0 or not radius_m > 0:
        return False
    col, row = world_to_cell(center_xy[0], center_xy[1])
    span = int(math.ceil(radius_m/resolution))+1
    r0, r1 = max(0, row-span), min(costs.shape[0], row+span+1)
    c0, c1 = max(0, col-span), min(costs.shape[1], col+span+1)
    if r0 >= r1 or c0 >= c1:
        return True  # außerhalb der Karte: nichts Gemessenes
    rr, cc = np.mgrid[r0:r1, c0:c1]
    inside = np.hypot((rr-row)*resolution, (cc-col)*resolution) <= radius_m
    return not np.any((costs[r0:r1, c0:c1] >= lethal) & inside)


def unknown_ahead_fraction(occupancy: np.ndarray,
                           world_to_cells: Callable[[np.ndarray, np.ndarray], Tuple[np.ndarray, np.ndarray]],
                           resolution: float, pose: Sequence[float], *,
                           start_m: float = 0., lookahead_m: float = 1.,
                           half_width_m: float = .25) -> float:
    """Anteil nicht kartierter Zellen im Korridor vor dem Roboter (0..1).

    Der Korridor liegt in Fahrtrichtung von ``start_m`` bis ``lookahead_m``
    und ist ``2*half_width_m`` breit. Zellen außerhalb der Karte zählen als
    nicht kartiert. Ohne gültige Eingaben gilt der Korridor als unbekannt
    (1.0), damit die Geschwindigkeitsbegrenzung fail-safe greift.
    """
    occupancy = np.asarray(occupancy)
    if (occupancy.ndim != 2 or occupancy.size == 0 or not resolution > 0 or pose is None
            or len(pose) < 3 or not all(math.isfinite(v) for v in pose[:3])
            or not lookahead_m > start_m or not half_width_m > 0):
        return 1.
    step = resolution
    along = np.arange(start_m+step/2, lookahead_m, step)
    across = np.arange(-half_width_m+step/2, half_width_m, step)
    if not len(along) or not len(across):
        return 1.
    a, c = np.meshgrid(along, across, indexing='ij')
    cos, sin = math.cos(pose[2]), math.sin(pose[2])
    wx = pose[0] + cos*a - sin*c
    wy = pose[1] + sin*a + cos*c
    cols, rows = world_to_cells(wx.ravel(), wy.ravel())
    cols, rows = np.asarray(cols, dtype=int), np.asarray(rows, dtype=int)
    inside = (rows >= 0) & (rows < occupancy.shape[0]) & (cols >= 0) & (cols < occupancy.shape[1])
    unknown = ~inside
    unknown[inside] = occupancy[rows[inside], cols[inside]] < 0
    return float(np.count_nonzero(unknown))/len(unknown)
