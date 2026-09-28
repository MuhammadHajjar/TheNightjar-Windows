"""``PGESound`` - a sound placed in the world.

Does double duty in the shipped levels: the atmosphere loops, the narration, and
the invisible proximity triggers (a Sound with an ``OnCollide`` and no sound to
play) are all this one class.  Recovered from The Nightjar's binary (engine
1_1_020; the same build as Papa Sangre 1's):

* ``init`` (0x1000297d8): gain 1, and every PGESound observes
  ``PGE_INPUT_DoubleTap`` (the skip button) with ``onDoubleTap``;
* ``activate`` (0x1000298e4): schedules ``createSpatializedSound`` **0.05 s**
  later (``performSelector:withObject:afterDelay:``, 0x100029910), *then* runs
  the base activation - so ``OnActivate`` is queued first and the sound starts
  a moment after;
* ``createSpatializedSound`` (0x100029bc8): one of ``sounds`` (the soundList
  split on ``&``) at random; the playlist's sound of exactly that name, else
  ``anySoundWihPrefix:``; spatialised flag, gain, ``play:`` with ``looping``;
  a non-looping sound gets a monitor (block 0x10002a0b4) that, once the
  position reaches the duration, fires ``triggerOnSoundEnd`` on the main queue;
  a skippable, active sound posts ``ShowSkipButton`` - but only when
  ``canSkipSound:`` says it has been heard to the end before;
* ``onDoubleTap`` (0x10002a30c): a skippable, active, playing sound that may
  be skipped posts ``RemoveFullScreenImage``, stops, and ends as if it had
  finished (``triggerOnSoundEnd``);
* ``triggerOnSoundEnd`` (0x10002a194): ``RemoveFullScreenImage``; a skippable
  sound is remembered as heard (``saveSkippableSound:``); ``OnSoundEnd``;
* ``playerMovedToPosition:`` (0x100029980): a railed sound follows the player
  on its axis before the base class runs.
"""

from __future__ import annotations

from ..core.messages import MessageBus, Params
from .agent import GameAgent

#: -[PGESound activate]: createSpatializedSound afterDelay:0.05 (0x100029910)
CREATE_DELAY = 0.05


class SoundAgent(GameAgent):
    def __init__(self, bus: MessageBus, name: str = '',
                 position=(0.0, 0.0), bank=None, level=None) -> None:
        super().__init__(bus, name=name, position=position, bank=bank, level=level)
        self.looping = False
        self.skippable = False
        self.on_x_rail = False
        self.on_y_rail = False
        self.gain = 1.0
        bus.subscribe('PGE_INPUT_DoubleTap', self._on_double_tap)

    # ------------------------------------------------------------------
    def activate(self) -> None:
        """``-[PGESound activate]``: the sound 0.05 s later, OnActivate now."""
        self.bus.call_after(CREATE_DELAY, self.create_spatialized_sound, token=(id(self), 'create'))
        super().activate()

    def deactivate(self) -> None:
        """``-[PGESound deactivate]`` is the base class's (0x100029948)."""
        super().deactivate()

    # ------------------------------------------------------------------
    def create_spatialized_sound(self) -> None:
        """``-[PGESound createSpatializedSound]`` (0x100029bc8)."""
        sounds = self.sounds
        if not sounds or self.bank is None:
            return
        name = sounds[self.level.rand() % len(sounds)] if self.level is not None else sounds[0]
        s = self.bank.sound(name)
        if s is None:
            s = self.bank.any_sound_with_prefix(name)
        self.sound = s
        if s is None:
            return
        s.spatialized = self.spatialized
        if self.spatialized:
            self.update_spatialized_sound()
        s.gain = self.gain
        s.looping = self.looping
        s.play()
        monitors = getattr(self.level, 'monitors', None)
        if not self.looping and monitors is not None:
            monitors.add(s, self._make_monitor(s), self)
        elif self.looping and monitors is not None:
            # PORT-SIDE: a looping hint's PC version follows its first pass
            # (house standard, Papa Sangre II decision 8).
            hook = getattr(self.level, 'on_line_ended', None)
            if hook is not None:
                said = []

                def first_pass(sound=s):
                    if not said and self.sound is sound:
                        said.append(1)
                        hook(sound.name)
                monitors.add_end_callback(s, first_pass, self)
        if self.skippable and self.active and self.level is not None:
            if self.level.can_skip_sound(s.name):
                self.bus.post('PGE_MESSAGE_ShowSkipButton', {})

    def _make_monitor(self, sound):
        """The block at 0x10002a0b4: at the end, OnSoundEnd on the main queue."""
        def monitor(pos, dur):
            if pos >= dur:
                hook = getattr(self.level, 'on_line_ended', None)
                if hook is not None:
                    hook(sound.name)          # PORT-SIDE: PC instructions
                self.bus.dispatch_async(self.trigger_on_sound_end)
                return True
            return False
        return monitor

    def _on_double_tap(self, _name: str, _params: Params) -> None:
        """``-[PGESound onDoubleTap]`` (0x10002a30c) - the skip button."""
        s = self.sound
        if not (self.skippable and self.active and s is not None and s.playing):
            return
        if self.level is None or not self.level.can_skip_sound(s.name):
            return
        self.bus.post('PGE_MESSAGE_RemoveFullScreenImage', {})
        s.stop()
        self.trigger_on_sound_end()

    def skip(self) -> bool:
        """What the skip button does to this sound, for the shell and tests."""
        s = self.sound
        if not (self.skippable and self.active and s is not None and s.playing):
            return False
        if self.level is None or not self.level.can_skip_sound(s.name):
            return False
        self._on_double_tap('PGE_INPUT_DoubleTap', {})
        return True

    def trigger_on_sound_end(self) -> None:
        """``-[PGESound triggerOnSoundEnd]`` (0x10002a194)."""
        self.bus.post('PGE_MESSAGE_RemoveFullScreenImage', {})
        if self.skippable and self.sound is not None and self.level is not None:
            self.level.save_skippable_sound(self.sound.name)
        self.trigger('OnSoundEnd')

    # ------------------------------------------------------------------
    def _on_player_moved(self, name: str, params: Params) -> None:
        """``-[PGESound playerMovedToPosition:]`` - rails, then the base class."""
        pos = params.get('position')
        if isinstance(pos, (tuple, list)) and len(pos) >= 2:
            px, py = float(pos[0]), float(pos[1])
            if self.on_x_rail:
                self.position = (px, self.position[1])
            if self.on_y_rail:
                self.position = (self.position[0], py)
        super()._on_player_moved(name, params)
