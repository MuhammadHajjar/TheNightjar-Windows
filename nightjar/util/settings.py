"""Player settings that survive between sittings.

``config/settings.json`` next to the executable, written out on first run the
way ``keys.json`` is so it can be found and edited by hand.

Turn speed is not recovered: the original turned by swiping, and the one
sensitivity slider in the binary belongs to
``PGEStepsWithHeightViewController``, an alternative control scheme The
Nightjar never switches on.  It is here because a keyboard and a thumbstick both need
a rate where a swipe needed none - see DIVERGENCES.md.

**Volume does not live here.**  The audio engine already persists its own
master volume into ``config/audio.json`` and applies it on start; the options
menu drives that rather than keeping a second copy.
"""

from __future__ import annotations

import json
import os

from . import paths

#: Degrees per second while a turn key is held or the stick is pushed fully.
DEFAULT_TURN_RATE = 120.0
MIN_TURN_RATE = 30.0
MAX_TURN_RATE = 400.0

DEFAULTS = {
    'turnRateDegreesPerSecond': DEFAULT_TURN_RATE,
    # The screen reader's PC version of each tutorial line that names a touch
    # control, on by default (the house standard from Papa Sangre II).
    'pcInstructions': True,
    # PORT ADDITION: look for a new version on GitHub when the game starts;
    # the version that ran last (so an update can say it happened).
    'checkUpdates': True,
    'lastVersion': '',
}
# Papa Sangre II's Blind intro, Skip ping, Skip explanation and Shake sound
# switches are not here: The Nightjar has no blind_ takes, no skip ping
# (-[PGEStepsViewController showSkipButton] 0x10000fb18 plays nothing) and no
# shaking.

#: The on/off settings; everything else is a number with a range.
TOGGLES = ('pcInstructions', 'checkUpdates')
#: Settings that are words.
STRINGS = ('lastVersion',)

_RANGES = {
    'turnRateDegreesPerSecond': (MIN_TURN_RATE, MAX_TURN_RATE),
}


def settings_path() -> str:
    d = os.path.join(paths.writable_root(), 'config')
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return os.path.join(d, 'settings.json')


class Settings:
    """Turn speed, clamped and persisted."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or settings_path()
        self.values = dict(DEFAULTS)
        self.load()

    # ------------------------------------------------------------------
    def load(self) -> 'Settings':
        try:
            with open(self.path, encoding='utf-8') as fh:
                stored = json.load(fh)
        except FileNotFoundError:
            self.save()
            return self
        except (OSError, ValueError):
            return self                 # a corrupt file must never stop play
        if isinstance(stored, dict):
            for key in DEFAULTS:
                if key in stored:
                    self.set(key, stored[key], save=False)
        return self

    def save(self) -> None:
        try:
            with open(self.path, 'w', encoding='utf-8') as fh:
                json.dump(self.values, fh, indent=2, sort_keys=True)
        except OSError:
            pass                        # read-only install: still playable

    # ------------------------------------------------------------------
    def set(self, key: str, value, save: bool = True):
        if key in STRINGS:
            v = '' if value is None else str(value)
            self.values[key] = v
            if save:
                self.save()
            return v
        if key in TOGGLES:
            v = value if isinstance(value, bool) else str(value).lower() in ('1', 'true', 'yes', 'on')
            self.values[key] = v
            if save:
                self.save()
            return v
        lo, hi = _RANGES[key]
        try:
            v = float(value)
        except (TypeError, ValueError):
            v = DEFAULTS[key]
        v = max(lo, min(hi, v))
        self.values[key] = v
        if save:
            self.save()
        return v

    def get(self, key: str):
        if key in STRINGS:
            return str(self.values.get(key, DEFAULTS[key]) or '')
        if key in TOGGLES:
            return bool(self.values.get(key, DEFAULTS[key]))
        return float(self.values.get(key, DEFAULTS[key]))

    def toggle(self, key: str) -> bool:
        return self.set(key, not self.get(key))

    def adjust(self, key: str, delta: float) -> float:
        return self.set(key, self.get(key) + delta)

    # ---------------------------------------------------------- shortcuts
    @property
    def turn_rate(self) -> float:
        return self.get('turnRateDegreesPerSecond')

    @turn_rate.setter
    def turn_rate(self, v: float) -> None:
        self.set('turnRateDegreesPerSecond', v)

    @property
    def pc_instructions(self) -> bool:
        return self.get('pcInstructions')

    @property
    def check_updates(self) -> bool:
        return self.get('checkUpdates')

    def __repr__(self) -> str:
        return f'<Settings turn {self.turn_rate:.0f} deg/s>'
