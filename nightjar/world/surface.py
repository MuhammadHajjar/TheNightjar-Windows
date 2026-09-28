"""``PGESurface`` - a patch of floor.

A surface is a rectangle that decides what you are walking on: which footstep
bank plays, how fast you may step before you stumble, and what happens when you
enter, step on, or leave it.

The level itself is a surface (``PGELevel`` derives from ``PGESurface``), which
is how a Room's ``footstepsPrefix`` applies everywhere no individual surface
covers.  Where surfaces overlap, the one with the highest ``z`` wins - that is
the comparison in ``-[PGELevel playerMovedToPosition:]``.
"""

from __future__ import annotations

from ..core.messages import MessageBus
from ..core.triggers import TriggerHost


def _f(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v, default: int = 0) -> int:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _b(v) -> bool:
    return str(v).strip().lower() in ('yes', 'true', '1')


#: What ``-[PGELevel createObjectFromDict:]`` gives a floor when the level data
#: names no value: a **Surface** gets tripBPM **350** (0x100030848) and the
#: **Room** 280 (0x10002fcc4); both get runBPM 180 (0x100030808 / 0x10002fc84).
#: (The Papa Sangre 1 port gave every surface 280 - the 350 was misread.)
#:
#: **This is where falling comes from.**  ``PGEPlayer init`` sets tripBPM to
#: 10000, which no one can reach, but ``playerMovedToPosition:`` copies the
#: floor's value onto the player the moment you stand on one.
DEFAULT_TRIP_BPM = 350.0          # a Surface
ROOM_TRIP_BPM = 280.0             # the Room (the level itself)
DEFAULT_RUN_BPM = 180.0


class Surface(TriggerHost):
    """One floor rectangle in world space."""

    def __init__(self, bus: MessageBus, rect, surface_id: int = 0,
                 z: int = 0, name: str = '') -> None:
        cx = rect[0] + rect[2] / 2.0
        cy = rect[1] + rect[3] / 2.0
        super().__init__(bus, name=name, position=(cx, cy))
        self.rect = tuple(rect)
        self.surface_id = surface_id
        self.z = z
        self.player_is_on_surface = False
        self.multiple_on_enter = False
        #: PGESurface's ``_entered`` / ``_exited``.  Once-only latches; nothing
        #: in the engine ever clears them.
        self.entered = False
        self.exited = False

        self.footsteps_prefix = ''
        self.trip_bpm = DEFAULT_TRIP_BPM
        self.run_bpm = DEFAULT_RUN_BPM
        self.trip_sound = ''
        self.shuffle_sound = ''

    # ------------------------------------------------------------------
    def apply_properties(self, props: dict) -> None:
        for key, raw in props.items():
            if key.startswith('On'):
                continue
            if key == 'footstepsPrefix':
                self.footsteps_prefix = str(raw)
            elif key == 'tripBPM':
                self.trip_bpm = _f(raw)
            elif key == 'runBPM':
                self.run_bpm = _f(raw)
            elif key == 'tripSound':
                self.trip_sound = str(raw)
            elif key == 'shuffleSound':
                self.shuffle_sound = str(raw)
            elif key == 'z':
                self.z = _i(raw)
            elif key == 'multipleOnEnter':
                self.multiple_on_enter = _b(raw)
            elif key == 'surfaceId':
                self.surface_id = _i(raw)
            # anything else has no setter on PGESurface and is ignored

    # ------------------------------------------------------------------
    def contains(self, x: float, y: float) -> bool:
        rx, ry, rw, rh = self.rect
        return rx <= x < rx + rw and ry <= y < ry + rh

    def trigger_on_enter(self) -> None:
        """``-[PGESurface triggerOnEnter]``

        Latched: a surface fires ``OnEnter`` **once in the life of the level**,
        not once per visit, unless it sets ``multipleOnEnter``.  Walk off a
        trigger line and back over it and the second crossing is silent.
        """
        if self.entered and not self.multiple_on_enter:
            return
        self.entered = True
        self.trigger('OnEnter')

    def trigger_on_step(self) -> None:
        self.trigger('OnStep')

    def trigger_on_exit(self) -> None:
        """``-[PGESurface triggerOnExit]`` - latched the same way, on the same
        ``multipleOnEnter`` flag, which governs both directions."""
        if self.exited and not self.multiple_on_enter:
            return
        self.exited = True
        self.trigger('OnExit')

    def trigger_on_exit_jumping(self) -> None:
        """Unlatched, and fired by the level only while the player is jumping."""
        self.trigger('OnExitJumping')

    def trigger_on_exit_not_jumping(self) -> None:
        self.trigger('OnExitNotJumping')

    def __repr__(self) -> str:
        return (f'<Surface id={self.surface_id} z={self.z} '
                f'{self.footsteps_prefix!r} {self.rect}>')
