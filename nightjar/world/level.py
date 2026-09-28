"""``PGELevel`` - one playable area, its agents, and the loop that runs them.

Load order is the original's three passes: the ``Room`` first (it defines the
world's origin and the level rectangle), then every agent, then the player.

Per player move, ``-[PGELevel playerMovedToPosition:]``:

1. reset the inactivity clock;
2. start from the level's own ``footstepsPrefix``;
3. find every ``Surface`` whose rectangle contains the player and keep the one
   with the **highest z**;
4. fire ``OnEnter`` if that surface's id differs from the one the player was on,
   otherwise ``OnStep``;
5. copy the surface's ``tripBPM`` / ``runBPM`` / ``tripSound`` onto the player,
   but only where they are greater than zero - a surface that does not specify
   one leaves the previous value alone.

The inactivity nag is the same clock: when nothing has happened for
``inactivityTime`` seconds the level plays the next sound from its list, pushes
the clock forward by that sound's own duration so it cannot retrigger during
playback, and advances to the next sound, wrapping at the end.
"""

from __future__ import annotations

import os
import random

from ..assets.tiled import LevelData, load_level
from ..audio.bank import SoundBank
from ..audio.monitor import MonitorPump
from ..core.messages import MessageBus, Params
from ..core.triggers import TriggerHost
from ..entities.agent import GameAgent
from ..entities.collectible import Collectible
from ..entities.monster import Monster
from ..entities.player import STATE_JUMPING, Player
from ..entities.sound_agent import SoundAgent
from . import requested
from .surface import (DEFAULT_RUN_BPM, DEFAULT_TRIP_BPM, ROOM_TRIP_BPM,
                      Surface, _f, _i)

#: Object types the port creates.  The Nightjar's 14 levels use Sound,
#: Collectible and Monster (plus Room, Surface, Path and Player); the engine's
#: other agent types (Dilemma, NPC, Summoner, ForgetfulMan, ...) belong to Papa
#: Sangre 1, which shares the engine, and no Nightjar level names them.
AGENT_CLASSES = {
    'Sound': SoundAgent,
    'Collectible': Collectible,
    'Monster': Monster,
}

#: What ``playerDidCollideAWall:`` falls back to when ``hitWallSound`` is unset -
#: which is every level in the game.  0x100032eb0.
#: -[PGELevel init]: `update` every 0.1 s (0x10002c50c), passing 0.1 to
#: every agent's update: (0x100032138).
TICK = 0.1

DEFAULT_HIT_WALL_SOUND = 'hitwall'
HIT_WALL_WET_GAIN = 0.5           # fmov s0, #0.5 at 0x100032ef0


class Level(Surface):
    """A loaded level: geometry, agents, player, and the update loop."""

    def __init__(self, bus: MessageBus, bank: SoundBank,
                 progress=None, rng: random.Random | None = None) -> None:
        # PGELevel *is* a PGESurface, and that is not a detail: the level is
        # the floor you are standing on whenever no smaller surface covers you,
        # which is how a room's own tripBPM, footstepsPrefix and shuffleSound
        # reach the player at all.  See _on_player_moved.
        super().__init__(bus, rect=(0.0, 0.0, 0.0, 0.0), surface_id=0,
                         z=0, name='')
        # the Room's own default, not a Surface's (0x10002fcc4)
        self.trip_bpm = ROOM_TRIP_BPM
        self.bank = bank
        self.progress = progress
        self.rng = rng or random.Random()

        self.data: LevelData | None = None
        self.agents: list[GameAgent] = []
        self.floors: list[Surface] = []
        #: PGELevel.pathArray - patrol routes, by name.
        self.paths: dict[str, list[tuple[float, float]]] = {}
        self.player: Player | None = None

        # footsteps_prefix, trip_bpm, run_bpm, trip_sound and shuffle_sound all
        # come from Surface now, with the loader's own defaults.
        self.hit_wall_sound = ''

        #: -[PGELevel init] sets inactivityTime to +inf (0x10002c4a8): no
        #: hints until a level sends ChangeInactivityTime.
        self.inactivity_time = float('inf')
        self.inactivity_sounds: list[str] = []
        self.current_inactivity_sound = 0
        self.last_activity = 0.0
        self._inactivity_sound = None

        #: The S3D sound monitors (`add3DSoundMonitor:`), pumped every 10 ms.
        self.monitors = MonitorPump()
        #: PORT-SIDE hook: called with a sound's name when a line ends (the
        #: spoken PC instructions after a tutorial line).
        self.on_line_ended = None
        self.shutting_down = False
        self.paused = False
        self.next_level: str | None = None
        self.finished = False
        #: nightJar_14's two exits: the game itself is over, not just this level.
        self.game_complete = False

        for msg, handler in (
            ('PGE_INTERNAL_EnemyState', self._on_enemy_state),
            ('PGE_MESSAGE_PlaySpatialSound', self._on_play_spatial_sound),
            ('PGE_MESSAGE_ChangeInactivityTime', self._on_change_inactivity_time),
            ('PGE_MESSAGE_ChangeInactivitySoundList', self._on_change_inactivity_list),
            ('PGE_MESSAGE_LoadLevelWithName', self._on_load_level),
            ('PGE_MESSAGE_ShutDownLevel', self._on_shut_down),
            ('PGE_MESSAGE_PresentAdiosVC', self._on_present_adios),
            ('PGE_MESSAGE_PlayerMovedToPosition', self._on_player_moved),
            ('PGE_MESSAGE_PlayerDidCollideAWall', self._on_wall),
            (requested.STOP_SOUND, self._on_port_stop_sound),
        ):
            bus.subscribe(msg, handler)

    # ------------------------------------------------------------- loading
    def load(self, path: str, name: str | None = None) -> 'Level':
        """``actuallyLoadDataFromJsonFile``'s completion block (0x10002d3bc on):
        ``loadLevelStructure:``, ``loadLevelAgents:``, ``loadPlayer:``, then
        ``PGE_MESSAGE_LevelInited``.

        An agent whose data says ``active`` is switched on as it is created
        (``setActive:`` at 0x10002f16c), so a starting narration is already
        scheduled (``-[PGESound activate]``: 0.05 s later) before the player
        exists.  ``loadPlayer:`` then posts ``SetControlSettingsToDefault`` and
        ``MovePlayerToPosition`` (0x10002e678 / 0x10002e788): the player
        steps onto its start, which is what fires the Room's ``OnEnter``.
        """
        data = load_level(path, name)
        requested.apply(data, self.bank)          # Muhammad's decisions 2 and 5
        self.data = data
        self.name = data.name
        self.rect = data.rect

        # pass 1: the Room
        room = data.room
        if room is not None:
            self.apply_room(room)

        # pass 2: agents and surfaces
        for obj in data.objects:
            if obj.type in ('Surface', 'ActionSurface'):
                s = Surface(self.bus, obj.rect or (obj.x, obj.y, obj.width, obj.height),
                            surface_id=len(self.floors) + 1, name=obj.name)
                s.apply_properties(obj.settable)
                s.add_triggers(obj.triggers)
                self.floors.append(s)
            elif obj.type in AGENT_CLASSES:
                cls = AGENT_CLASSES[obj.type]
                ag = cls(self.bus, name=obj.name, position=(obj.x, obj.y),
                         bank=self.bank, level=self)
                self.agents.append(ag)
                ag.add_triggers(obj.triggers)
                props = dict(obj.settable)
                active = props.pop('active', None)
                ag.apply_properties(props)
                if active is not None:
                    ag.set_active(str(active).strip().lower() in ('yes', 'true', '1'))
            elif obj.type == 'Path':
                self.paths[obj.name] = list(obj.polyline)

        # pass 3: the player
        if data.player is not None:
            p = Player(self.bus, level=self, rng=self.rng)
            p.playlist = self.bank
            p.position = (data.player.x, data.player.y)
            p.pixels_per_step = _f(data.player.properties.get('pixelsPerStep'), 5.0)
            # Only footstepsPrefix comes from the level here: the other four
            # (tripBPM, runBPM, tripSound, shuffleSound) reach the player in
            # playerMovedToPosition:, which starts its search from the level
            # itself - the level *is* the surface you are on when nothing
            # smaller covers you.  That is how the Nightjar Rooms' own tripBPM,
            # tripSound and shuffleSound (levels 1, 2, 4-8, 10, 11, 13) apply.
            p.footsteps_prefix = self.footsteps_prefix
            p.footstep_gain = requested.FOOTSTEP_GAIN.get(self.name, p.footstep_gain)
            p.footstep_gains = dict(requested.FOOTSTEP_GAIN_BY_PREFIX)
            p.add_triggers(data.player.triggers)
            p.set_start_angle(_f(data.player.properties.get('startAngle'), 0.0))
            self.player = p
            self.bus.post('PGE_MESSAGE_SetControlSettingsToDefault', {})
            self.bus.post('PGE_MESSAGE_MovePlayerToPosition', {'position': p.position})

        self.last_activity = self.bus.now
        self.bus.post('PGE_MESSAGE_LevelInited', {'name': self.name})
        return self

    def path_with_name(self, name: str):
        """``-[PGELevel pathWithName:]`` - the route an agent asks to walk."""
        return self.paths.get(name)

    def apply_room(self, room) -> None:
        props = room.settable
        self.apply_properties(props)          # the Room's surface half
        self.hit_wall_sound = str(props.get('hitWallSound', ''))
        if 'inactivityTime' in props:
            self.inactivity_time = _f(props.get('inactivityTime'))
        if 'inactivitySounds' in props:
            # createObjectFromDict: posts the Room's list as a
            # ChangeInactivitySoundList (0x10002fc34).
            self.bus.post('PGE_MESSAGE_ChangeInactivitySoundList',
                          {'soundList': props.get('inactivitySounds')})
        self.add_triggers(room.triggers)

    def set_inactivity_sounds(self, value) -> None:
        """``changeInactivitySoundList:`` (0x100033af0): the list split on
        ``&`` (empty entries kept, as NSString keeps them), index back to 0."""
        self.inactivity_sounds = str(value).split('&') if value is not None else []
        self.current_inactivity_sound = 0

    def rand(self) -> int:
        """The C library's ``rand()``, as the original calls it."""
        return self.rng.randrange(0x7fffffff)

    # ------------------------------------------------------------- running
    def tick(self) -> None:
        """``-[PGELevel update]`` (0x100031fb4), on its 0.1 s NSTimer.

        The hint clock first, then every agent's ``update:`` with 0.1.  (The
        VoiceOver announcement wait at the top belongs to the shell here.)
        """
        if self.paused:
            return
        now = self.bus.now
        self._update_inactivity(now)
        for ag in list(self.agents):
            ag.update(now, TICK)

    # -------------------------------------------------------- inactivity
    def player_was_active(self, now: float) -> None:
        """``-[PGELevel playerWasActive]`` (0x100033904)."""
        self.last_activity = now

    def _update_inactivity(self, now: float) -> None:
        """The hint clock in ``update`` (0x100032028).

        With no hint list, or while a hint is playing, the clock restarts;
        otherwise a hint plays once more than ``inactivityTime`` has passed
        since the last activity.  There is no zero guard: the +inf from
        ``init`` is what keeps it quiet until a level sets a time.
        """
        snd = self._inactivity_sound
        if not self.inactivity_sounds or (snd is not None and snd.playing):
            self.last_activity = now
        if self.inactivity_time < now - self.last_activity:
            self.play_inactivity_sound(now)

    def play_inactivity_sound(self, now: float) -> None:
        """``-[PGELevel playInactivitySound]`` (0x100033cd4).

        Stop the one playing, look the next one up by exact name, play it
        flat, and push the clock past its end (a name that does not resolve
        has no duration, so its slot is silent); then the next index,
        wrapping.
        """
        if not self.inactivity_sounds:
            return
        if self._inactivity_sound is not None and self._inactivity_sound.playing:
            self._inactivity_sound.stop()
        idx = self.current_inactivity_sound
        name = self.inactivity_sounds[idx] if idx < len(self.inactivity_sounds) else ''
        sound = self.bank.sound(name) if name else None
        self._inactivity_sound = sound
        duration = 0.0
        if sound is not None:
            sound.spatialized = False
            sound.looping = False
            sound.play()
            duration = sound.duration
            hook = self.on_line_ended
            if hook is not None:
                # PORT-SIDE: a hint that names a touch control gets its PC
                # version after it (house standard).
                def ended(pos, dur, n=sound.name):
                    if pos >= dur:
                        hook(n)
                        return True
                    return False
                self.monitors.add(sound, ended, self)
        self.last_activity = now + duration
        self.current_inactivity_sound = idx + 1
        if self.current_inactivity_sound >= len(self.inactivity_sounds):
            self.current_inactivity_sound = 0

    # ------------------------------------------------------------ surfaces
    def _on_player_moved(self, _name: str, params: Params) -> None:
        pos = params.get('position')
        if not (isinstance(pos, (tuple, list)) and len(pos) >= 2):
            return
        x, y = float(pos[0]), float(pos[1])
        self.player_was_active(self.bus.now)
        if self.player is None:
            return

        # -[PGELevel playerMovedToPosition:] starts the search with **self**
        # as the current best floor (0x10003231c), because PGELevel is a
        # PGESurface.  A real surface only takes over by containing the player
        # at a higher z.  So there is no "standing on nothing" case: off every
        # surface you are standing on the room, and the room's own tripBPM -
        # 280 by the loader's default - is what lets you fall.  Getting this
        # wrong is why levels with no Surface objects could not trip you.
        best = self
        for s in self.floors:
            if s.contains(x, y) and s.z > best.z:
                best = s

        if best.footsteps_prefix:
            prefix = best.footsteps_prefix
        else:
            prefix = self.footsteps_prefix

        if self.player.current_surface_id != best.surface_id:
            for s in self.floors:
                if s is not best and s.player_is_on_surface:
                    s.player_is_on_surface = False
                    self._exit_surface(s)
            best.player_is_on_surface = True
            self.player.current_surface_id = best.surface_id
            best.trigger_on_enter()
        else:
            best.trigger_on_step()

        if best.trip_bpm > 0:
            self.player.trip_bpm = best.trip_bpm
        if best.run_bpm > 0:
            self.player.run_bpm = best.run_bpm
        # Always assigned, exactly like shuffleSound below.  The original has
        # an else arm here - ``setTripSound:@""`` at 0x1000326c8 - so stepping
        # onto a surface that names no tripSound *clears* the player's and the
        # trip falls back to anySoundContaining:@"trip".  Only ever setting it
        # meant the last trip sound you crossed stuck for the rest of the
        # level: reported as the quicksand trip playing everywhere in ps1_11.
        self.player.trip_sound = best.trip_sound or ''
        # Always assigned, so a surface with no shuffleSound clears it and the
        # player falls back to "<footstepsPrefix>_shuffle".
        self.player.shuffle_sound = best.shuffle_sound or ''

        self.player.footsteps_prefix = prefix

    def _exit_surface(self, s: Surface) -> None:
        """Leaving a surface, in the original's order.

        ``OnExit`` first, then exactly one of the jumping variants depending on
        whether the player is in state 4.  No level uses either variant, and no
        level enables jumping, so only the ``OnExit`` half can ever be observed -
        but the split is what ``playerMovedToPosition:`` does.
        """
        s.trigger_on_exit()
        if self.player is not None and self.player.state == STATE_JUMPING:
            s.trigger_on_exit_jumping()
        else:
            s.trigger_on_exit_not_jumping()

    def _on_port_stop_sound(self, _name: str, params: Params) -> None:
        """Port-only (decision 9b): stop a sound by name, if it is playing."""
        s = self.bank.sound(str(params.get('soundName', ''))) if self.bank else None
        if s is not None and s.playing:
            s.stop()

    def _on_wall(self, _name: str, _params: Params) -> None:
        """``-[PGELevel playerDidCollideAWall:]``, the finite-level branch.

        The fallback name is not a nicety: **no level in the game sets
        ``hitWallSound``**, so ``"hitwall"`` is what you actually hear every
        time you walk into a wall, whenever the level's playlist declares it.

        The original sets only reverb and wet gain - ``spatialized`` is left to
        the playlist, which declares ``hitwall`` unspatialised.
        """
        s = self.bank.sound(self.hit_wall_sound or DEFAULT_HIT_WALL_SOUND)
        if s is None:
            return
        s.send_to_reverb = True
        s.wet_gain = HIT_WALL_WET_GAIN
        s.play()

    # ------------------------------------------------------------ messages
    def _on_play_spatial_sound(self, _name: str, params: Params) -> None:
        name = params.get('soundName', '')
        s = self.bank.sound(name)
        if s is None:
            return
        s.spatialized = True
        pos = params.get('position')
        if isinstance(pos, (tuple, list)) and len(pos) >= 2:
            s.planar = (float(pos[0]), float(pos[1]), 0.0)
        s.play()

    def _on_enemy_state(self, _name: str, params: Params) -> None:
        a = self.agent(params.get('name', ''))
        if isinstance(a, Monster):
            a.change_state_to(int(params.get('state', 1)))

    def _on_change_inactivity_time(self, _name: str, params: Params) -> None:
        self.inactivity_time = _f(params.get('value'))
        self.last_activity = self.bus.now

    def _on_change_inactivity_list(self, _name: str, params: Params) -> None:
        self.set_inactivity_sounds(params.get('soundList'))

    def _on_load_level(self, _name: str, params: Params) -> None:
        self.next_level = params.get('name')
        self.finished = True

    def _on_present_adios(self, _name: str, _params: Params) -> None:
        """``PGE_MESSAGE_PresentAdiosVC`` - the end of the game.

        Observed by ``-[PGEViewController viewDidLoad]``, which presents
        ``PGEAdiosViewController`` and calls ``playMenuAtmos``: the goodbye
        screen with "play this again" and "main menu" on it.  Only nightJar_14
        sends it, from **both** of its doors (Outro_A and Outro_B_Death_Reigns)
        - two endings, and each of them finishes the game.

        There are no view controllers here, so what it means for this port is
        simply: there is no next level, the game is over.
        """
        self.game_complete = True
        self.finished = True
        self.next_level = None

    def _on_shut_down(self, _name: str, params: Params) -> None:
        """``-[PGELevel shutDownLevel:]``

        Every agent **except the one that sent the message** is deactivated, the
        inactivity sound is stopped and its list emptied, and the player is
        frozen.  The sender is spared so the thing you just walked into can
        finish speaking - which is exactly what stops the "are you still there"
        nag from talking over the closing narration.

        One pass over ``agentArray`` (fast enumeration, 0x1000347f4), as the
        original does.  (The Papa Sangre 1 port repeats the sweep because
        ps1_23's ``OnDeactivate`` triggers re-activate agents behind it; no
        Nightjar level has an ``OnDeactivate``, so one pass is the whole story.)
        """
        self.shutting_down = True
        sender = params.get('senderName')
        for a in list(self.agents):
            if a.name != sender:
                a.deactivate()
        if self._inactivity_sound is not None and self._inactivity_sound.playing:
            self._inactivity_sound.stop()
        self.inactivity_sounds = []
        self.inactivity_time = 0.0
        self.bus.post('PGE_MESSAGE_DisableHands', {})
        self.bus.post('PGE_MESSAGE_DisableWalk', {})
        self.bus.post('PGE_MESSAGE_DisableRotation', {})

    # ----------------------------------------------------------- progress
    def can_skip_sound(self, key: str) -> bool:
        return bool(self.progress and self.progress.can_skip_sound(key))

    def save_skippable_sound(self, key: str) -> None:
        if self.progress:
            self.progress.save_skippable_sound(key)

    # ---------------------------------------------------------------- info
    def contains(self, x: float, y: float) -> bool:
        rx, ry, rw, rh = self.rect
        return rx <= x < rx + rw and ry <= y < ry + rh

    def agent(self, name: str) -> GameAgent | None:
        for a in self.agents:
            if a.name == name:
                return a
        return None

    def pause(self) -> None:
        """``-[PGELevel pause:]`` - stop the clock and hold every sound.

        The original invalidates its update timer and pauses each agent; the
        port sets a flag that :meth:`tick` honours, which is the same thing
        without a timer object.
        """
        if self.paused:
            return
        self.paused = True
        if self.player is not None:
            self.player.pause()
        for a in self.agents:
            a.pause()

    def resume(self, now: float) -> None:
        """``-[PGELevel resume:]`` - restart the clock from *now*.

        The original resets its date before rescheduling the timer, so the
        paused interval does not count against the inactivity nag.  The port
        pushes ``last_activity`` forward for the same reason.
        """
        if not self.paused:
            return
        self.paused = False
        if self.player is not None:
            self.player.resume()
        for a in self.agents:
            a.resume()
        self.last_activity = now

    def shutdown(self) -> None:
        """The level going away (``clearLevelData``): every agent silenced
        without firing anything, every sound stopped, nothing left pending."""
        for a in self.agents:
            a.deactivate_no_callback()
        self.monitors.clear()
        self.bank.stop_all()
        self.bus.clear()

    def __repr__(self) -> str:
        return (f'<Level {self.name!r} {len(self.agents)} agents, '
                f'{len(self.floors)} surfaces>')
