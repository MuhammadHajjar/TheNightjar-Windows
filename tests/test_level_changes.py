"""One sitting, several levels: nothing from a level outlives it.

Muhammad's M3 report (2026-09-27): a shuffle as each level started, and
level 5 opening "stuck inside a wall".  Both came from the level before:
its player was still subscribed, so it kept stepping in its own old map
(a wall bump with every step) and answered the new level's shuffle."""

import os
import random
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.core.game import Game                               # noqa: E402
from nightjar.save.progress import InMemoryProgress               # noqa: E402
from nightjar.sim import FakeBank                                 # noqa: E402
from nightjar.util import paths                                   # noqa: E402


class _Settings:
    pc_instructions = False


class _Clock:
    def __init__(self):
        self.log = []
        self.now = 0.0


def _game():
    bundle = paths.game_bundle()
    clock = _Clock()
    g = Game(bundle, InMemoryProgress(), _Settings(),
             lambda n: FakeBank(clock, bundle, n, random.Random(1)))
    msgs = []
    g.bus.subscribe(None, lambda n, p: msgs.append((g.now, n)))
    return g, clock, msgs


def _run(g, clock, seconds):
    for _ in range(int(round(seconds / 0.01))):
        g.update(0.01)
        clock.now = g.now


def _until_walk(g, clock, limit=400):
    for _ in range(limit):
        if g.interpreter.player_can_walk:
            return True
        _run(g, clock, 1.0)
    return False


def _walk(g, clock, n):
    foot = 'L'
    for _ in range(n):
        mi = g.interpreter
        if mi.foot_pressed(foot):
            mi.foot_released(foot, g.now)
        foot = 'R' if foot == 'L' else 'L'
        _run(g, clock, 0.6)


def _subs(g):
    return sum(len(v) for v in g.bus._subs.values())


def test_a_levels_listeners_go_with_it():
    g, clock, _ = _game()
    g.load('nightJar_1')
    base = _subs(g)
    for name in ('nightJar_2', 'nightJar_5', 'nightJar_1'):
        g.load(name)
    assert _subs(g) == base
    g.unload()
    assert _subs(g) < base


def test_level_5_after_level_4_is_not_inside_a_wall():
    g, clock, msgs = _game()
    g.load('nightJar_4')
    assert _until_walk(g, clock)
    _walk(g, clock, 6)
    g.load('nightJar_5')
    assert _until_walk(g, clock)
    msgs.clear()
    start = g.level.player.position
    _walk(g, clock, 8)
    assert not [n for _, n in msgs if n == 'PGE_MESSAGE_PlayerDidCollideAWall']
    assert g.level.player.position != start
    assert 'hitwall' not in [n for _, w, n in clock.log if w == 'play']


def test_no_shuffle_as_a_level_starts():
    """Decision 6.  The original would shuffle here: it remembers the last
    foot across levels, and the new level's SetControlSettingsToDefault finds
    it 2-99 s old."""
    g, clock, msgs = _game()
    g.load('nightJar_4')
    assert _until_walk(g, clock)
    _walk(g, clock, 3)
    g.interpreter.lock_controls()          # the door: controls go, the foot stays
    _run(g, clock, 5.0)
    msgs.clear()
    clock.log.clear()
    g.load('nightJar_5')
    _run(g, clock, 3.0)
    assert not [n for _, n in msgs if n == 'PGE_ACTION_Shuffle']
    assert not [n for _, w, n in clock.log if w == 'play' and n.endswith('_shuffle')]


def test_the_shuffle_still_plays_inside_a_level():
    g, clock, msgs = _game()
    g.load('nightJar_4')
    assert _until_walk(g, clock)
    _walk(g, clock, 3)
    _run(g, clock, 2.5)
    assert [n for _, n in msgs if n == 'PGE_ACTION_Shuffle']


# ------------------------------------------------ the skip button's 6.2 s
def _skip_game():
    g, clock, msgs = _game()
    g._wall = lambda: 0.0                    # loading takes no time here
    for k in ('LVL2_1A', 'LVL3_1A', 'LVL4a'):
        g.progress.save_skippable_sound(k)
    return g, clock


def _skip_usable_after(g, clock, limit=10.0):
    t0 = g.now
    while g.now - t0 < limit:
        if g.skip_button:
            return g.now - t0
        _run(g, clock, 0.01)
    return None


def test_from_a_menu_the_skip_waits_6_2_s_from_choosing_the_level():
    g, clock = _skip_game()
    g.show_headphones()
    g.load('nightJar_2')
    assert abs(_skip_usable_after(g, clock) - 6.2) < 0.05


def test_loading_counts_towards_the_wait():
    g, clock = _skip_game()
    g._wall = iter([0.0, 2.0] * 10).__next__  # the load takes 2 s of wall time
    g.show_headphones()
    g.load('nightJar_2')
    assert abs(_skip_usable_after(g, clock) - 4.2) < 0.05


def test_after_a_win_screen_the_skip_is_there_at_once():
    """The picture went up when level 2 ended (its LoadLevelWithName); ten
    seconds on the win screen, Continue, and the intro can be skipped."""
    g, clock = _skip_game()
    g.show_headphones()
    g.load('nightJar_2')
    g.bus.post('PGE_MESSAGE_LoadLevelWithName', {'name': 'nightJar_3'})
    assert g.outcome[0] == 'win'
    g.menu_update(10.0)
    g.load('nightJar_3')                     # Continue: no new picture
    assert _skip_usable_after(g, clock) < 0.1


def test_a_short_stay_on_the_win_screen_leaves_the_rest_of_the_wait():
    g, clock = _skip_game()
    g.show_headphones()
    g.load('nightJar_3')
    g.bus.post('PGE_MESSAGE_LoadLevelWithName', {'name': 'nightJar_4'})
    g.menu_update(2.0)
    g.load('nightJar_4')
    assert abs(_skip_usable_after(g, clock) - 4.2) < 0.1
