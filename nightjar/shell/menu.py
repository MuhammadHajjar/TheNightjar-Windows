"""The menus, spoken, in The Nightjar's own words.

Every label that exists in the original is the original's - the accessibility
labels in its ``_nj`` nibs, which is what VoiceOver read out - and every UI
sound is the one the button's handler plays (``playUiSoundWithName:``):

====================  ========================================================
main menu             Begin - Continue here (decision 10) -
                      (``continueButtonPressed:``: the furthest level
                      unlocked, click), Levels - named Select Level here
                      (decision 9e) - (click), Credits (click),
                      About (``TriggerOtherGames:``, no sound)
                      (PGEViewController_nj); the Cast button's list is read
                      inside Credits (decision 4)
level list            "Play Level %i: %@" / "Level %i: %@; locked", Main Menu
                      (back) (AccessibleAllLevelsViewController)
Credits               the crew, then the cast under "Cast", then Main Menu
                      (back) (CreditsViewController_nj, types 1 and 2)
About                 the page's texts, then Main Menu (back)
                      (MoreGamesViewController_nj)
pause                 Continue game (click), Restart Level (click), Quit game
                      (back) (PGEStepsAndSwipeViewController_nj); Escape resumes
win                   Continue (click), Play this again (no sound), Main menu
                      (back) (PGEWinViewController_nj)
lose                  Retry (click), Main Menu (back) (PGELoseViewController_nj)
end                   Play this again (click), Main Menu (back)
                      (PGEAdiosViewController_nj)
====================  ========================================================

Added for a PC, each recorded in DIVERGENCES.md: Settings, Quit and (at M7)
Check for updates on the main menu; the click when a level is chosen (house
standard); Settings and Quit to Windows on the pause screen; Select Level and
Quit after a level; the screens' titles (the pictures' words); the version and
a PC note on About.

Nothing is drawn.  A menu is a list you move through with up and down, choose
with Enter or A, and leave with Escape or B; left and right change a setting.
"""

from __future__ import annotations

from ..assets.hublist import load_hub_list
from ..util.settings import MAX_TURN_RATE, MIN_TURN_RATE
from . import texts

CLICK = 'click_button'
BACK = 'back_button'
#: ``MenuItem.sound`` default: decide from the action.
AUTO = 'auto'
#: Actions whose button plays the back sound.
BACK_ACTIONS = ('back', 'main', 'quit')


class MenuItem:
    """One row: what to say, and what choosing it does.

    ``sound`` is the UI sound its button plays: ``CLICK``, ``BACK``, None for
    a button that makes no sound, or AUTO - back for the actions in
    BACK_ACTIONS, click for the rest.
    """

    __slots__ = ('label', 'action', 'value', 'enabled', 'adjust', 'sound')

    def __init__(self, label: str, action: str, value=None,
                 enabled: bool = True, adjust=None, sound=AUTO) -> None:
        self.label = label
        self.action = action
        self.value = value
        self.enabled = enabled
        self.adjust = adjust          # callable(delta) -> new spoken label
        self.sound = sound

    def ui_sound(self) -> str | None:
        if self.sound != AUTO:
            return self.sound
        return BACK if self.action in BACK_ACTIONS else CLICK


class Menu:
    """A spoken list.  ``choose`` returns ``(action, value)`` or None."""

    def __init__(self, title: str, items: list[MenuItem], intro: str = '',
                 cancel: MenuItem | None = None, cancellable: bool = True) -> None:
        self.title = title
        self.items = items
        self.intro = intro            # read once, before the first row
        self.index = 0
        #: What Escape does: the row it stands for (default: a Back with the
        #: back sound), or nothing at all when not ``cancellable``.
        self.cancellable = cancellable
        self.cancel = cancel if cancel is not None else MenuItem('Back', 'back')

    @property
    def current(self) -> MenuItem | None:
        if not self.items:
            return None
        return self.items[self.index % len(self.items)]

    def move(self, delta: int) -> str:
        if not self.items:
            return ''
        self.index = (self.index + delta) % len(self.items)
        return self.speak_current()

    def speak_current(self) -> str:
        item = self.current
        if item is None:
            return f'{self.title}. Empty.'
        return item.label

    def announce(self) -> str:
        """Said on entering the menu: its name, any text, then the row."""
        parts = [self.title]
        if self.intro:
            parts.append(self.intro)
        parts.append(self.speak_current())
        return '. '.join(p.rstrip('.') for p in parts if p) + '.'

    def choose(self):
        item = self.current
        if item is None:
            return None
        if not item.enabled:
            return ('blocked', item)
        if item.adjust is not None and item.action == 'toggle':
            item.label = item.adjust(+1)
            return ('toggled', item)
        return (item.action, item.value)

    def adjust_current(self, delta: float) -> str | None:
        """Left/right on a setting row.  None when the row is not one."""
        item = self.current
        if item is None or item.adjust is None:
            return None
        item.label = item.adjust(delta)
        return item.label


# ---------------------------------------------------------------- builders
def main_menu(progress=None, updates: bool = False) -> Menu:
    """`PGEViewController_nj`.  Escape does nothing: there is nothing behind it."""
    last = progress.last_unlocked_level if progress is not None else 'nightJar_1'
    items = [
        # REQUESTED (decision 10, 2026-09-28): "Continue"; the original's
        # button reads Begin (its handler is continueButtonPressed:).
        MenuItem('Continue', 'continue', last, sound=CLICK),
        # REQUESTED (decision 9e, 2026-09-28): "Select Level", as Papa Sangre
        # II names it; the original's button is Levels (hubSelectorButtonTouched:).
        MenuItem('Select Level', 'levels', sound=CLICK),
        # REQUESTED (decision 4, 2026-09-27): the Cast button's list is read
        # inside Credits, under a "Cast" heading, not from a row of its own.
        MenuItem('Credits', 'credits', sound=CLICK),
        MenuItem('About', 'about', sound=None),          # TriggerOtherGames: plays none
        MenuItem('Settings', 'settings', sound=CLICK),
    ]
    if updates:
        items.append(MenuItem('Check for updates', 'updates', sound=CLICK))
    items.append(MenuItem('Quit', 'quit', sound=BACK))
    return Menu('The Nightjar', items, cancellable=False)


def level_menu(bundle_dir: str, progress=None) -> Menu:
    """`AccessibleAllLevelsViewController`: the hub list, then Main Menu."""
    items = []
    for entry in load_hub_list(bundle_dir):
        # `tableView:didSelectRowAtIndexPath:` posts the launch and plays no
        # sound; the click is the house standard (Papa Sangre II's tester).
        items.append(MenuItem(entry.spoken(progress), 'play', entry.file_name,
                              enabled=entry.is_unlocked(progress), sound=CLICK))
    items.append(MenuItem('Main Menu', 'back', sound=BACK))
    return Menu('Select Level', items, cancel=MenuItem('Main Menu', 'back', sound=BACK))


def text_menu(title: str, rows: list[str], head: list[str] | None = None,
              tail: list[str] | None = None) -> Menu:
    """A screen of text read a row at a time, then Main Menu (back)."""
    items = [MenuItem(r, 'info', sound=None) for r in (head or []) + rows + (tail or [])]
    items.append(MenuItem('Main Menu', 'back', sound=BACK))
    return Menu(title, items, cancel=MenuItem('Main Menu', 'back', sound=BACK))


def credits_menu() -> Menu:
    """The Credits screen's crew list, then (decision 4) the Cast screen's
    list under its own "Cast" heading."""
    return text_menu('Credits', texts.CREDITS + ['Cast'] + texts.CAST[1:])


def about_menu(version: str = '', pc_note: str = '') -> Menu:
    """The About page, with the port's version first and a PC note last."""
    return text_menu('About', texts.ABOUT,
                     head=[f'Version {version}'] if version else None,
                     tail=[pc_note] if pc_note else None)


def _onoff(v: bool) -> str:
    return 'on' if v else 'off'


def settings_menu(settings, engine=None) -> Menu:
    """PORT ADDITION.  Left and right change the row you are on; Enter flips a switch."""

    def volume_label() -> str:
        if engine is None:
            return 'Sound volume, unavailable'
        return f'Sound volume, {engine.master_volume_db:+.0f} decibels'

    def turn_label() -> str:
        return f'Turning speed, {settings.turn_rate:.0f} degrees per second'

    def adjust_volume(delta: float) -> str:
        if engine is None:
            return volume_label()
        before = engine.master_volume_db
        engine.adjust_master_volume(2.0 * delta)
        if abs(engine.master_volume_db - before) < 0.01:
            return volume_label() + (', maximum' if delta > 0 else ', minimum')
        return volume_label()

    def adjust_turn(delta: float) -> str:
        settings.adjust('turnRateDegreesPerSecond', 15.0 * delta)
        if settings.turn_rate <= MIN_TURN_RATE:
            return turn_label() + ', slowest'
        if settings.turn_rate >= MAX_TURN_RATE:
            return turn_label() + ', fastest'
        return turn_label()

    def switch(key: str, label: str):
        def text() -> str:
            return f'{label}, {_onoff(settings.get(key))}'

        def flip(_delta: float) -> str:
            settings.toggle(key)
            return text()
        return text, flip

    pc_t, pc_f = switch('pcInstructions', 'PC instructions')
    up_t, up_f = switch('checkUpdates', 'Check for updates at start')
    return Menu('Settings', [
        MenuItem(volume_label(), 'adjust', adjust=adjust_volume),
        MenuItem(turn_label(), 'adjust', adjust=adjust_turn),
        MenuItem(pc_t(), 'toggle', adjust=pc_f),
        MenuItem(up_t(), 'toggle', adjust=up_f),
        MenuItem('Keys', 'keys'),
        MenuItem('Controller buttons', 'buttons'),
        MenuItem('Back', 'back'),
    ])


#: What the key menu offers, in the order it reads them out.
REBINDABLE = (
    ('foot_left', 'Left foot'),
    ('foot_right', 'Right foot'),
    ('turn_left', 'Turn left'),
    ('turn_right', 'Turn right'),
    ('skip', 'Skip'),
    ('pause', 'Pause'),
    ('confirm', 'Select'),
    ('cancel', 'Back'),
    ('menu_up', 'Menu up'),
    ('menu_down', 'Menu down'),
    ('menu_left', 'Menu left'),
    ('menu_right', 'Menu right'),
    ('volume_up', 'Volume up'),
    ('volume_down', 'Volume down'),
)


def keys_menu(keymap) -> Menu:
    items = []
    for action, label in REBINDABLE:
        keys = keymap.keys_for(action)
        said = ' or '.join(keys) if keys else 'unbound'
        items.append(MenuItem(f'{label}: {said}', 'rebind', action))
    items.append(MenuItem('Restore all keys to their defaults', 'reset_keys'))
    items.append(MenuItem('Back', 'back'))
    return Menu('Keys', items)


#: The pad's list.  Turning is missing on purpose: it is the left stick.
PAD_REBINDABLE = tuple(r for r in REBINDABLE if r[0] not in ('turn_left', 'turn_right'))


def pad_menu(padmap) -> Menu:
    items = []
    for action, label in PAD_REBINDABLE:
        items.append(MenuItem(f'{label}: {padmap.describe(action)}',
                              'rebind_button', action))
    items.append(MenuItem('Restore all buttons to their defaults', 'reset_buttons'))
    items.append(MenuItem('Back', 'back'))
    return Menu('Controller buttons', items)


def pause_menu() -> Menu:
    """The pause screen (`pauseGame` plays nothing); Escape = Continue game."""
    return Menu(texts.PAUSE_TITLE, [
        MenuItem('Continue game', 'resume', sound=CLICK),     # resumeGame:
        MenuItem('Restart Level', 'restart', sound=CLICK),    # playAgainButtonTouched:
        MenuItem('Settings', 'settings', sound=CLICK),
        MenuItem('Quit game', 'main', sound=BACK),            # quitButtonTouched:
        MenuItem('Quit to Windows', 'quit', sound=BACK),
    ], cancel=MenuItem('Continue game', 'resume', sound=CLICK))


def level_complete_menu(next_level: str | None) -> Menu:
    """The win screen.  Escape is Main menu (house standard: Escape backs out)."""
    items = []
    if next_level:
        items.append(MenuItem('Continue', 'next', next_level, sound=CLICK))
    items.append(MenuItem('Play this again', 'replay', sound=None))
    items.append(MenuItem('Select Level', 'levels', sound=CLICK))
    items.append(MenuItem('Main menu', 'main', sound=BACK))
    items.append(MenuItem('Quit', 'quit', sound=BACK))
    return Menu(texts.WIN_TITLE, items, cancel=MenuItem('Main menu', 'main', sound=BACK))


def level_failed_menu() -> Menu:
    """The lose screen."""
    return Menu(texts.LOSE_TITLE, [
        MenuItem('Retry', 'replay', sound=CLICK),
        MenuItem('Select Level', 'levels', sound=CLICK),
        MenuItem('Main Menu', 'main', sound=BACK),
        MenuItem('Quit', 'quit', sound=BACK),
    ], cancel=MenuItem('Main Menu', 'main', sound=BACK))


def adios_menu() -> Menu:
    """`PGEAdiosViewController_nj`: the end of the game.  Play this again
    replays the last level (`reloadCurrentLevel`)."""
    return Menu(texts.END_TITLE, [
        MenuItem('Play this again', 'replay', sound=CLICK),
        MenuItem('Main Menu', 'main', sound=BACK),
        MenuItem('Quit', 'quit', sound=BACK),
    ], cancel=MenuItem('Main Menu', 'main', sound=BACK))


def update_offer_menu(message: str) -> Menu:
    """PORT ADDITION: a newer version is on GitHub.  Two choices and no more:
    Update now downloads it and restarts into it; Not now (and Escape) asks
    again next start."""
    return Menu('Update available', [
        MenuItem('Update now', 'yes'),
        MenuItem('Not now', 'no', sound=BACK),
    ], intro=message, cancel=MenuItem('Not now', 'no'))


def update_ready_menu(message: str) -> Menu:
    """PORT ADDITION: an update downloaded earlier and not yet put in."""
    return Menu('Update ready', [
        MenuItem('Update now', 'restart'),
        MenuItem('Not now', 'later', sound=BACK),
    ], intro=message, cancel=MenuItem('Not now', 'later'))
