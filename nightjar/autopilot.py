"""A player that finishes levels on its own, in the simulator.

It plays the way the game is meant to be played by ear, from what the level
makes audible: wait while the controls are locked (the narration), then head
for the collectible that is sounding - a sensor, an egg or a door - turning to
face it when turning is allowed.  It walks at a steady tempo, and when
something is coming for it (a monster alerted or chasing), or it is standing
on a floor that gives it away, it steps as fast as the ground allows without
falling.  A level is not done until this wins it on several seeds
(tests/test_autopilot.py).

The route is planned on a 10 px grid (one step) over the room: it keeps clear
of anything that kills on contact - a monster asleep or awake, the dark
matter - with room to spare for how fast it moves, and it crosses a floor
that alerts the monsters where that floor is farthest from them.  It knows
where the monsters are, which a player knows by listening.
"""

from __future__ import annotations

import heapq
import math
import random

from .entities.collectible import Collectible
from .entities.monster import (ALERT_AGENT, ALERT_PLAYER, ALERT_POSITION,
                               CHASE_PLAYER, GO_TO_POSITION, Monster)
from .sim import Sim

#: A step every 0.55 s is about 109 BPM: under every runBPM (180) and tripBPM
#: (220 at the lowest) in the game.
STEP_GAP = 0.55
#: Stepping when chased: as fast as the ground allows, 15 % under its tripBPM.
FAST_MARGIN = 0.85
#: Never faster than this (about 230 BPM).
FASTEST_GAP = 0.26
#: Close enough to face: the collectible collide radius is 20 px.
FACING_TOLERANCE = math.radians(4.0)
#: Walking while turning: steps are taken once the heading is this close.
WALK_TOLERANCE = math.radians(25.0)
#: How fast it turns: the port's default turning speed, 120 degrees a second.
TURN_RATE = math.radians(120.0)
#: How often it acts (the simulator step it runs at).
TICK = 0.05
#: The planning grid: one step.
CELL = 10.0
#: Room kept between it and anything deadly, beyond that thing's own radius.
HAZARD_MARGIN = 14.0
#: How far ahead a moving hazard is allowed for: the stretch it will sweep
#: in this many seconds is kept clear.
HAZARD_LOOKAHEAD = 2.5
#: Hurry when that stretch is this close.
HAZARD_HURRY = 60.0
#: What a cell of alerting floor costs, and how much more near a monster.
ALERT_COST = 6.0
ALERT_NEAR = 3000.0
#: The goal: a cell this close to the target's centre.
GOAL_REACH = 14.0
#: States in which a monster is coming (or about to).
COMING = (ALERT_PLAYER, CHASE_PLAYER, ALERT_POSITION, GO_TO_POSITION, ALERT_AGENT)
ALERTS = ('PGE_MESSAGE_AlertAllEnemies', 'PGE_MESSAGE_AlertEnemyWithName')


def _deadly(agent) -> bool:
    """Kills on contact: an OnCollide that shuts the level down, on anything
    that is not a collectible (a door's OnCollide is the way out)."""
    if isinstance(agent, Collectible):
        return False
    return any(t.trigger_type == 'OnCollide' and t.notification_name.endswith('ShutDownLevel')
               for t in agent.triggers)


class Autopilot:
    def __init__(self, sim: Sim, prefer: str | None = None, seed: int = 1) -> None:
        self.sim = sim
        #: Each seed is a different player: its own rhythm and reaction time.
        self.rng = random.Random(seed * 7919)
        self._walk_from = None
        #: Where there is a choice of doors (nightJar_14), the one to take.
        self.prefer = prefer
        self.foot = 'L'
        self.next_step = 0.0
        self.steps = 0
        self.route: list[tuple[float, float]] = []
        self._alert_floors = None

    # ------------------------------------------------------------ what it hears
    def target(self):
        """What to head for: the collectible whose beacon is sounding, or (the
        listening tutorial) a sound waiting to be faced - an active agent with
        an OnEnteringShootRange trigger."""
        live = [a for a in self.sim.level.agents
                if isinstance(a, Collectible) and a.active and not a.collected]
        if self.prefer:
            for a in live:
                if a.name == self.prefer:
                    return a
        if live:
            return live[0]
        for a in self.sim.level.agents:
            if a.active and any(t.trigger_type == 'OnEnteringShootRange' for t in a.triggers):
                return a
        return None

    def bearing_to(self, point) -> float:
        p = self.sim.player
        return math.atan2(point[1] - p.position[1], point[0] - p.position[0])

    def monsters(self):
        return [a for a in self.sim.level.agents if isinstance(a, Monster)]

    def hunted(self) -> bool:
        return any(m.active and m.state in COMING for m in self.monsters())

    def alert_floors(self):
        if self._alert_floors is None:
            self._alert_floors = [
                s for s in self.sim.level.floors
                if any(t.notification_name in ALERTS and t.trigger_type in ('OnStep', 'OnEnter')
                       for t in s.triggers)]
        return self._alert_floors

    def on_alert_floor(self, x, y) -> bool:
        lv = self.sim.level
        best = None
        for s in lv.floors:
            if s.contains(x, y) and (best is None or s.z > best.z):
                best = s
        return best is not None and best in self.alert_floors()

    def fast_gap(self) -> float:
        lv = self.sim.level
        trips = [lv.trip_bpm] + [s.trip_bpm for s in lv.floors if s.trip_bpm > 0]
        lowest = min(t for t in trips if t > 0)
        return max(FASTEST_GAP, 60.0 / (lowest * FAST_MARGIN))

    # ------------------------------------------------------------ the route
    def hazards(self):
        """Everything deadly, as (start, end, radius): the stretch a moving
        one will sweep in the next HAZARD_LOOKAHEAD seconds, or a point."""
        out = []
        for a in self.sim.level.agents:
            if not _deadly(a):
                continue
            if not a.active and not isinstance(a, Monster):
                continue
            r = a.collide_radius + HAZARD_MARGIN
            (x, y), (vx, vy) = a.position, a.orientation_vector
            end = (x, y)
            if a.active and (vx or vy) and a.speed > 0:
                end = (x + vx * a.speed * HAZARD_LOOKAHEAD, y + vy * a.speed * HAZARD_LOOKAHEAD)
            out.append(((x, y), end, r))
        return out

    @staticmethod
    def _dist2(pt, a, b) -> float:
        """Squared distance from pt to the segment a-b."""
        ax, ay = a
        dx, dy = b[0] - ax, b[1] - ay
        L = dx * dx + dy * dy
        t = 0.0 if L == 0 else max(0.0, min(1.0, ((pt[0] - ax) * dx + (pt[1] - ay) * dy) / L))
        qx, qy = ax + t * dx - pt[0], ay + t * dy - pt[1]
        return qx * qx + qy * qy

    def near_moving_hazard(self) -> bool:
        p = self.sim.player.position
        for a, b, r in self.hazards():
            if a != b and self._dist2(p, a, b) < (r + HAZARD_HURRY) ** 2:
                return True
        return False

    def plan(self, goal) -> list[tuple[float, float]]:
        """A* over the room, from where it stands to anywhere within reach of
        ``goal``.  Empty when there is no way through right now."""
        lv, p = self.sim.level, self.sim.player
        rx, ry, rw, rh = lv.rect
        nx, ny = int(rw // CELL), int(rh // CELL)
        hz = self.hazards()
        mons = [m.position for m in self.monsters() if m.active or m.state in COMING]
        floors = self.alert_floors()

        def centre(i, j):
            return (rx + (i + 0.5) * CELL, ry + (j + 0.5) * CELL)

        # Inside a hazard's margin already (it moved towards us): cells nearer
        # to it than we are stay shut, the rest open, so the way out is away.
        here = [self._dist2(p.position, a, b) for a, b, _r in hz]

        def blocked(pt):
            for k, (a, b, r) in enumerate(hz):
                d2 = self._dist2(pt, a, b)
                if d2 < r * r and d2 < here[k]:
                    return True
            return False

        def cost(pt):
            c = 1.0
            if floors and any(s.contains(*pt) for s in floors):
                near = min((math.hypot(pt[0] - m[0], pt[1] - m[1]) for m in mons),
                           default=1e9)
                c += ALERT_COST + ALERT_NEAR / (near + 10.0)
            return c

        si = min(max(int((p.position[0] - rx) // CELL), 0), nx - 1)
        sj = min(max(int((p.position[1] - ry) // CELL), 0), ny - 1)
        gx, gy = goal
        reach2 = GOAL_REACH * GOAL_REACH

        def h(i, j):
            c = centre(i, j)
            return max(0.0, math.hypot(c[0] - gx, c[1] - gy) - GOAL_REACH) / CELL

        openq = [(h(si, sj), 0.0, si, sj)]
        came = {(si, sj): None}
        g = {(si, sj): 0.0}
        found = None
        while openq:
            _f, gc, i, j = heapq.heappop(openq)
            if gc > g.get((i, j), 1e18):
                continue
            c = centre(i, j)
            if (c[0] - gx) ** 2 + (c[1] - gy) ** 2 <= reach2:
                found = (i, j)
                break
            for di in (-1, 0, 1):
                for dj in (-1, 0, 1):
                    if not di and not dj:
                        continue
                    ni, nj = i + di, j + dj
                    if not (0 <= ni < nx and 0 <= nj < ny):
                        continue
                    pt = centre(ni, nj)
                    if blocked(pt):
                        continue
                    step = (1.4142 if di and dj else 1.0) * cost(pt)
                    ng = gc + step
                    if ng < g.get((ni, nj), 1e18):
                        g[(ni, nj)] = ng
                        came[(ni, nj)] = (i, j)
                        heapq.heappush(openq, (ng + h(ni, nj), ng, ni, nj))
        if found is None:
            return []
        path = []
        k = found
        while k is not None:
            path.append(centre(*k))
            k = came[k]
        path.reverse()
        path.append((gx, gy))
        return path

    def waypoint(self, route):
        """The point to steer for: two steps along the route."""
        p = self.sim.player.position
        best = route[-1]
        for pt in route[1:]:
            if math.hypot(pt[0] - p[0], pt[1] - p[1]) >= 2 * CELL:
                best = pt
                break
        return best

    # ------------------------------------------------------------ what it does
    def tick(self) -> None:
        s = self.sim
        mi = s.interpreter
        t = self.target()
        if t is None:
            return
        walking = mi.player_can_walk
        if walking and self._walk_from is None:
            # a moment to react once the narration lets go
            self._walk_from = s.now + self.rng.uniform(0.0, 1.5)
        elif not walking:
            self._walk_from = None
        if walking and s.now < self._walk_from:
            walking = False
        if walking:
            if s.now >= self.next_step or not self.route:
                self.route = self.plan(t.position)
            aim = self.waypoint(self.route) if self.route else None
        else:
            aim = t.position
        if aim is not None and mi.player_can_rotate:
            want = self.bearing_to(aim)
            diff = (want - s.player.player_angle + math.pi) % (2 * math.pi) - math.pi
            tolerance = WALK_TOLERANCE if walking else FACING_TOLERANCE
            if abs(diff) > FACING_TOLERANCE:
                step = TURN_RATE * TICK
                s.turn(max(-step, min(step, diff)))
            if abs(diff) > tolerance:
                return
        if walking and aim is not None and s.now >= self.next_step:
            px, py = s.player.position
            fast = self.hunted() or self.on_alert_floor(px, py) or self.near_moving_hazard()
            if s.foot(self.foot):
                self.steps += 1
                self.foot = 'R' if self.foot == 'L' else 'L'
            gap = (self.fast_gap() * self.rng.uniform(1.0, 1.15) if fast
                   else STEP_GAP * self.rng.uniform(0.85, 1.15))
            self.next_step = s.now + gap

    def run(self, limit: float = 900.0) -> bool:
        """Play until the level ends.  True when it was won."""
        s = self.sim
        end = s.now + limit
        while s.now < end and not s.level.finished:
            self.tick()
            s.step(TICK)
        return bool(s.level.finished and s.level.next_level
                    and s.level.next_level != s.level.name) or s.level.game_complete


def play_level(name: str, seed: int = 1, limit: float = 900.0,
               prefer: str | None = None) -> tuple[bool, Sim, Autopilot]:
    s = Sim(name, seed=seed)
    ap = Autopilot(s, prefer=prefer, seed=seed)
    return ap.run(limit), s, ap
