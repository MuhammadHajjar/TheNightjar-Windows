"""``PGECollectible`` - the things you walk into: sensors, doors, exits, eggs.

Recovered from The Nightjar's binary (engine 1_1_020):

``activate`` (0x10001ba08)
    fetch the playlist, then ``playIntroSound``.  It does **not** call the
    base ``activate``, so a collectible never fires ``OnActivate``.
``playIntroSound`` (0x10001c208)
    with no intro sound (or one shorter than two characters), or an intro that
    is the loop sound itself, go straight to ``startLoop``; otherwise stop what
    is playing, play the intro spatialised with the distance-driven reverb mix
    (1 to 2 px, wet 0.1 to 0.75), and start the loop when it ends.
``startLoop`` (0x10001c90c)
    play ``loopSound`` spatialised and looping, the reverb mix over 1 to 100 px
    and wet 0.05 to 0.3 - the beacon you home in on.  No gain is set here.
``collidesWithPlayer`` (0x10001b954)
    only while active and not yet collected: fire ``OnCollide``, then
    ``playCollectSound``, then mark it collected.
``playCollectSound`` (0x10001bb44)
    stop the beacon and play ``collectSound`` **unspatialised**; when that
    ends, ``setActive:NO``, post ``ActivateAgentWithName`` for
    ``nextCollectible`` if one is named, and fire ``OnSoundEnd``.  With no
    collect sound to play there is nothing to end, so none of that happens.
``deactivate`` (0x10001bb00)
    clears ``collected`` before the base class.
"""

from __future__ import annotations

from ..core.messages import MessageBus
from .agent import GameAgent

#: -[PGECollectible playIntroSound] (0x10001c4dc-0x10001c570)
INTRO_REVERB = {'auto_mix': True, 'min_distance': 1.0, 'max_distance': 2.0,
                'min_wet_send': 0.1, 'max_wet_send': 0.75}
#: -[PGECollectible startLoop] (0x10001cac4-0x10001cb60)
LOOP_REVERB = {'auto_mix': True, 'min_distance': 1.0, 'max_distance': 100.0,
               'min_wet_send': 0.05, 'max_wet_send': 0.3}


class Collectible(GameAgent):
    def __init__(self, bus: MessageBus, name: str = '',
                 position=(0.0, 0.0), bank=None, level=None) -> None:
        super().__init__(bus, name=name, position=position, bank=bank, level=level)
        self.intro_sound = ''
        self.loop_sound = ''
        self.collect_sound = ''
        self.next_collectible = ''
        #: ``PGECollectible.collected`` - transient: it guards against
        #: re-collecting while the collect sound plays, and ``deactivate``
        #: clears it again.
        self.collected = False
        #: Port-side: a durable record, because ``collected`` is not one.
        self.was_collected = False

    # ------------------------------------------------------------------
    def activate(self) -> None:
        """``-[PGECollectible activate]`` - no ``OnActivate``."""
        self.play_intro_sound()

    def deactivate(self) -> None:
        self.collected = False
        super().deactivate()

    # ------------------------------------------------------------------
    def _spatial(self, sound, reverb: dict) -> None:
        sound.spatialized = True
        sound.reverb_mix = dict(reverb)
        sound.send_to_reverb = True

    def play_intro_sound(self) -> None:
        """``-[PGECollectible playIntroSound]``"""
        if self.bank is None:
            return
        intro = self.intro_sound or ''
        if len(intro) < 2 or intro == self.loop_sound:
            self.start_loop()
            return
        if self.sound is not None and self.sound.playing:
            self.sound.stop()
        sound = self.bank.sound(intro)
        self.sound = sound
        if sound is None:
            return
        self._spatial(sound, INTRO_REVERB)
        sound.looping = False
        sound.play()
        monitors = getattr(self.level, 'monitors', None)
        if monitors is not None:
            def ended(pos, dur):
                if pos >= dur:
                    self.bus.dispatch_async(self.start_loop)
                    return True
                return False
            monitors.add(sound, ended, self)

    def start_loop(self) -> None:
        """``-[PGECollectible startLoop]``"""
        if self.bank is None:
            return
        if self.sound is not None and self.sound.playing:
            self.sound.stop()
        sound = self.bank.sound(self.loop_sound) if self.loop_sound else None
        self.sound = sound
        if sound is None:
            return
        self._spatial(sound, LOOP_REVERB)
        self.update_spatialized_sound()
        sound.looping = True
        sound.play()

    # ------------------------------------------------------------------
    def collides_with_player(self) -> None:
        """``-[PGECollectible collidesWithPlayer]``"""
        if not self.active or self.collected:
            return
        self.trigger('OnCollide')
        self.play_collect_sound()
        # set last, at 0x10001b9b4 (then Flurry's incrementCollectibles)
        self.collected = True
        self.was_collected = True

    def play_collect_sound(self) -> None:
        """``-[PGECollectible playCollectSound]``"""
        if self.sound is not None and self.sound.playing:
            self.sound.stop()
        sound = self.bank.sound(self.collect_sound) if (self.bank and self.collect_sound) else None
        self.sound = sound
        if sound is None:
            return
        sound.spatialized = False
        sound.looping = False
        sound.play()
        monitors = getattr(self.level, 'monitors', None)
        if monitors is not None:
            def ended(pos, dur):
                if pos >= dur:
                    self.bus.dispatch_async(self._finish_collect)
                    return True
                return False
            monitors.add(sound, ended, self)

    def _finish_collect(self) -> None:
        """The block the collect sound's monitor hands the main queue."""
        self.set_active(False)
        if self.next_collectible:
            # posted, not enqueued (postNotificationName:object:)
            self.bus.post('PGE_MESSAGE_ActivateAgentWithName',
                          {'name': self.next_collectible})
        self.trigger('OnSoundEnd')
