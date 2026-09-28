"""The game around the level: `PGEngine` and the view controllers' audio.

What this owns, each recovered from The Nightjar's binary (engine 1_1_020):

* **loading** (`-[PGEngine loadLevelWithName:]`, 0x1000362a4): controls are
  locked; a `LoadLevelWithName` for **another** level is a win - the level is
  completed, the next one unlocked, `PresentWinVC`; for the **same** level it
  is a loss - `PresentLoseVC`.  The shell answers both with the after-level
  screen.  `actuallyLoadDataFromJsonFile` stops the menu atmosphere and saves
  the level as the last playlist;
* **the clock**: the level's 0.1 s `update` timer (`-[PGELevel init]`
  0x10002c50c) and the S3D monitors every 10 ms, both on game time that keeps
  pace with the wall clock (the remainder of a frame is carried, never
  rounded away);
* **the skip button** (`-[PGEStepsViewController showSkipButton]` 0x10000fb18
  / `skipButtonPressed:` 0x10000f9e4): shown on `ShowSkipButton` - no sooner
  than 6.2 s after the wear-headphones picture went up - hidden by
  `RemoveFullScreenImage`; pressing it posts `PGE_INPUT_DoubleTap` and clicks.
  The picture (`displayHeadphonesImage` 0x10000ed20, which stamps
  `wearHeadphonesDate` at 0x10000f150) is put up by **LoadLevelWithName**
  (observed in `initWithNibName:bundle:` 0x10000eb94): from the menus that is
  the moment you choose the level, so loading counts; after a win or a death
  it is the moment the previous level ended, and the win or lose screen sits
  in between, so after Continue or Retry the wait is usually over.  Nothing in
  this game takes the picture down (`removeFullScreenImage` leaves
  `isWearHeadphonesImage` alone), so the wait always runs from the last one;
* **UI sounds** (`-[PGEngine playUiSoundWithName:]` 0x10003715c): a file in
  the bundle, named with its extension, played by a new AVAudioPlayer that
  replaces (and so stops) the one before; no spacing rule;
* **the menu atmosphere** (`-[PGEngine playMenuAtmos]` 0x100036e14 =
  `preloadMenuAtmos` 0x100036c44 + `startMenuAtmos` 0x100036e48): every sound
  of the last playlist whose name, upper-cased, starts with ``ATMOS``, looping,
  from gain 0 faded in to 1 over 0.5 s (`+[S3DDefaults fadeIn:]` 0x1000cf86c:
  gain = position / 0.5).  Played after the splash, on the win, lose and end
  screens, and a second after Quit game; stopped when a level loads
  (`actuallyLoadDataFromJsonFile` -> `stopMenuAtmos`).
"""

from __future__ import annotations

import random
import time

from ..assets import pack
from ..assets.hublist import load_hub_list
from ..audio.monitor import MonitorPump
from ..assets.tiled import level_path
from ..input.interpreter import MoveInterpretor
from ..world.level import Level, TICK
from .messages import MessageBus, Params

#: showSkipButton: the button waits until 6.2 s after wearHeadphonesDate.
SKIP_BUTTON_DELAY = 6.2
#: skipButtonPressed: clicks (0x10000facc).
SKIP_CLICK = 'click_button'
#: -[PGEViewController showSplashScreen]: The Nightjar's branch (0x10003daf4).
SPLASH_SOUND = 'papa_engine_splash'
#: startMenuAtmos: [S3DDefaults fadeIn:0.5] (0x100036ef0)
ATMOS_FADE_IN = 0.5
#: -[PGEViewController quitLevel]: playMenuAtmos afterDelay:1 (0x10003d4d8)
QUIT_ATMOS_DELAY = 1.0


class Game:
    """One sitting: the persistent bus and controls, and the current level."""

    def __init__(self, bundle: str, progress, settings, bank_factory,
                 menu_bank=None, say=None, rumble=None, engine=None,
                 tutorial_lines=None, rng: random.Random | None = None,
                 wall=time.perf_counter) -> None:
        self.bundle = bundle
        self.progress = progress
        self.settings = settings
        self.bank_factory = bank_factory
        self.menu_bank = menu_bank
        self.say = say or (lambda text: None)
        self.rumble = rumble or (lambda: None)
        self.engine = engine
        self.tutorial_lines = tutorial_lines or {}
        self.rng = rng or random.Random()
        self.bus = MessageBus()
        self.interpreter = MoveInterpretor(self.bus)
        self.level: Level | None = None
        self.bank = None
        self.level_name = ''
        self.hub = {e.file_name: e for e in load_hub_list(bundle)}
        self.outcome = None               # ('win', level, next) | ('lose', level, level) | ('end', level, None)
        self.skip_button = False
        self.now = 0.0
        self._tick_acc = 0.0
        self._clock_acc = 0.0             # wall time not yet spent on a 10 ms step
        #: The wear-headphones picture: when it went up, on the sitting clock.
        self._headphones_at: float | None = None
        #: Wall time spent loading levels, when neither clock runs.
        self._load_wall = 0.0
        self._wall = wall
        self._ui = None
        self.history: list[str] = []
        #: The menu atmosphere and the menu's own clock: its fade-in monitors
        #: and timers run where no game time passes.
        self.atmos: list = []
        self._atmos_bank = None
        self.menu_now = 0.0
        self.menu_monitors = MonitorPump()
        self._menu_timers: list = []
        for name, handler in (
            ('PGE_MESSAGE_LoadLevelWithName', self._load_level_with_name),
            ('PGE_MESSAGE_PresentAdiosVC', self._present_adios),
            ('PGE_MESSAGE_ShowSkipButton', self._show_skip_button),
            ('PGE_MESSAGE_RemoveFullScreenImage', self._remove_skip_button),
        ):
            self.bus.subscribe(name, handler)

    # ------------------------------------------------------------ levels
    def has_level(self, name: str) -> bool:
        return bool(name) and pack.isfile(level_path(self.bundle, name))

    def title(self, name: str) -> str:
        e = self.hub.get(name)
        return e.alt_name if e is not None else name

    def load(self, name: str) -> Level:
        """Load a level and start it."""
        self.unload()
        self.outcome = None
        self.skip_button = False
        self.level_name = name
        self.history.append(name)
        self.stop_menu_atmos()            # actuallyLoadDataFromJsonFile
        self.bank = self.bank_factory(name)
        # The level, its agents and its player are gone with it in the
        # original (their dealloc removes their observers); here everything
        # they subscribe is tagged with the level and dropped by unload().
        # Without this each old player kept walking in its old map - a wall
        # bump with every step, and a second shuffle.
        self._scope_key = key = object()
        with self.bus.scope(key):
            lv = Level(self.bus, self.bank, progress=self.progress, rng=self.rng)
        lv.on_line_ended = self._line_ended
        self.level = lv
        self.interpreter.lock_controls()
        # REQUESTED (decision 6): no shuffle as a level starts.  The original
        # keeps the last foot you used across levels, so the new level's
        # SetControlSettingsToDefault shuffles if you stepped 2-99 s ago.
        self.interpreter.forget_last_foot()
        started = self._wall()
        with self.bus.scope(key):
            lv.load(level_path(self.bundle, name), name)
        # PORT-SIDE: the original streams each sound on its own audio thread,
        # so a first play never holds up the game; here decoding would stall
        # the loop (the 98 s opening cutscene costs about 0.3 s), so the level's
        # sounds - with any the port declares for it - are decoded now, about a
        # second per level, before the first one plays (0.05 s from now).
        preload = getattr(self.bank, 'preload_all', None)
        if preload is not None:
            preload()
        if lv.player is not None:
            lv.player.vibrate_fn = self.rumble
        # actuallyLoadDataFromJsonFile: saveLastPlaylist: (0x10002cfd4)
        self.progress.save_last_playlist(name)
        self._load_wall += max(0.0, self._wall() - started)
        self.bus.update(self.now)
        return lv

    def unload(self) -> None:
        if self.level is not None:
            self.level.shutdown()
            self.level = None
        key = getattr(self, '_scope_key', None)
        if key is not None:
            self.bus.drop_scope(key)
            self._scope_key = None
        if self.bank is not None:
            self.bank.stop_all()
            self.bank = None
        self.bus.clear()

    def _load_level_with_name(self, _n, params: Params) -> None:
        """`-[PGEngine loadLevelWithName:]` (0x1000362a4): win or lose."""
        target = params.get('name')
        current = self.level_name
        self.show_headphones()            # the steps view observes it too
        self.interpreter.lock_controls()
        if not target or self.outcome is not None:
            return
        if target != current:
            self.progress.player_did_complete_level(current)
            self.progress.player_did_unlock_level(target)
            self.outcome = ('win', current, target)
        else:
            self.outcome = ('lose', current, target)

    def _present_adios(self, _n, _p) -> None:
        """`PGE_MESSAGE_PresentAdiosVC`: the end of the game (nightJar_14's
        two exits) - the Adios screen and the menu atmosphere."""
        if self.outcome is None:
            self.outcome = ('end', self.level_name, None)

    # ------------------------------------------------------------ the loop
    def update(self, dt: float) -> None:
        """Advance game time: the 10 ms monitors, the 0.1 s tick, the bus.

        Game time keeps pace with the sound, which runs on the wall clock:
        the part of a 10 ms step a frame did not fill is carried to the next
        frame.  (Rounding each frame to whole steps made Papa Sangre II's port
        run 6 % slow.)
        """
        self._clock_acc += max(0.0, dt)
        steps = int((self._clock_acc + 1e-9) / 0.01)
        self._clock_acc -= steps * 0.01
        for _ in range(steps):
            self.now += 0.01
            self.bus.now = self.now
            lv = self.level
            if lv is not None and not lv.paused:
                lv.monitors.advance(0.01)
                self._tick_acc += 0.01
                while self._tick_acc >= TICK - 1e-9:
                    self._tick_acc -= TICK
                    lv.tick()
            self.bus.update(self.now)
        self.sync_listener()

    def sync_listener(self) -> None:
        if self.engine is None or self.level is None or self.level.player is None:
            return
        p = self.level.player
        self.engine.set_listener(p.position, p.bearing_degrees)
        if self.bank is not None:
            self.engine.update_positions(self.bank.live_sounds())

    @property
    def finished(self) -> bool:
        return self.outcome is not None

    # ------------------------------------------------------------ pausing
    def pause(self) -> None:
        """`-[PGELevel pause:]`: the level's timer stops and its sounds hold."""
        lv = self.level
        if lv is None or lv.paused:
            return
        lv.pause()
        self._paused_sounds = [s for s in self.bank.live_sounds() if s.playing] if self.bank else []
        for s in self._paused_sounds:
            s.pause()

    def resume(self) -> None:
        lv = self.level
        if lv is None or not lv.paused:
            return
        lv.resume(self.now)
        for s in getattr(self, '_paused_sounds', []):
            s.resume()
        self._paused_sounds = []

    # ------------------------------------------------------------ the skip
    @property
    def sitting_now(self) -> float:
        """A clock that runs through play, the menus and loading alike - the
        original's wall clock (`[NSDate date]`), for the skip button."""
        return self.now + self.menu_now + self._load_wall

    def show_headphones(self) -> None:
        """`displayHeadphonesImage` (0x10000ed20): the picture goes up and the
        skip button's 6.2 s start.  The shell calls it when a level is chosen
        from a menu (`initGameplayEngineAndLaunchLevelWithName:` posts
        LoadLevelWithName, 0x10003d2f4); a level's own LoadLevelWithName calls
        it through `_load_level_with_name`."""
        self._headphones_at = self.sitting_now

    def _show_skip_button(self, _n, _p) -> None:
        if self._headphones_at is None:
            wait = 0.0                    # isWearHeadphonesImage NO: at once
        else:
            wait = SKIP_BUTTON_DELAY - (self.sitting_now - self._headphones_at)
        if wait > 0:
            self.bus.call_after(wait, self._skip_shown)
        else:
            self._skip_shown()

    def _skip_shown(self) -> None:
        self.skip_button = True

    def _remove_skip_button(self, _n, _p) -> None:
        self.skip_button = False

    def skip(self) -> bool:
        """`skipButtonPressed:` - only while the button is there to press."""
        if not self.skip_button:
            return False
        self.bus.post('PGE_INPUT_DoubleTap', {})
        self.skip_button = False
        self.play_ui_sound(SKIP_CLICK)
        self.bus.update(self.now)
        return True

    # --------------------------------------------------------- tutorial
    def _line_ended(self, sound_name: str) -> None:
        """House standard: after a tutorial line that names a touch control,
        the same instruction for a PC - unless PC instructions is off."""
        if not self.settings.pc_instructions:
            return
        text = self.tutorial_lines.get(sound_name)
        if text:
            self.say(text() if callable(text) else text)

    # ------------------------------------------------------------ menu audio
    def play_ui_sound(self, name: str) -> None:
        """`-[PGEngine playUiSoundWithName:]` (0x10003715c): flat, and one at
        a time - the new player replaces the old one in `uiAudio`, which stops
        it.  `name` is the file name without its extension."""
        s = self.menu_bank.sound(name) if self.menu_bank is not None else None
        if s is None:
            return
        if self._ui is not None and self._ui is not s:
            self._ui.stop()
        self._ui = s
        s.spatialized = False
        s.gain = 1.0
        s.looping = False
        s.play()

    def play_menu_atmos(self) -> list:
        """`playMenuAtmos`: the last playlist's ATMOS loops, faded in."""
        self.stop_menu_atmos()
        name = self.progress.get_last_playlist()
        bank = self.bank_factory(name) if name else None
        self._atmos_bank = bank
        if bank is None:
            return []
        names = [n for n in getattr(bank, 'specs', {}) if n.upper().startswith('ATMOS')]
        for n in names:
            s = bank.sound(n)
            if s is None:
                continue
            s.gain = 0.0
            s.looping = True
            s.play()

            def fade(pos, _dur, snd=s):
                if ATMOS_FADE_IN > pos:
                    snd.gain = pos / ATMOS_FADE_IN
                    return False
                snd.gain = 1.0
                return True
            self.menu_monitors.add(s, fade, self)
            self.atmos.append(s)
        return self.atmos

    def stop_menu_atmos(self) -> None:
        """`stopMenuAtmos` (0x100037008): stop whatever is playing."""
        for s in self.atmos:
            if s.playing:
                s.stop()
        self.atmos = []
        self.menu_monitors.remove_owner(self)
        self._menu_timers = []

    def call_menu_later(self, delay: float, fn) -> None:
        self._menu_timers.append((self.menu_now + float(delay), fn))

    def menu_update(self, dt: float) -> None:
        """The menu audio's time: its monitors and its timers."""
        self.menu_now += dt
        self.menu_monitors.advance(dt)
        if self._menu_timers:
            due = [t for t in self._menu_timers if t[0] <= self.menu_now]
            if due:
                self._menu_timers = [t for t in self._menu_timers if t[0] > self.menu_now]
                for _when, fn in sorted(due, key=lambda t: t[0]):
                    fn()

    def quit_level(self) -> None:
        """Quit game (`QuitGameMode`): the level goes, and a second later the
        menu atmosphere (`-[PGEViewController quitLevel]`)."""
        self.unload()
        self.call_menu_later(QUIT_ATMOS_DELAY, self.play_menu_atmos)
