"""Levels 6 to 14: the monsters, the dark matter, the alarm floors and the
two endings, as the engine does them, and the requested lines (decision 2)."""

import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.entities.monster import (ALERT_PLAYER, ATTACK, CHASE_PLAYER,  # noqa: E402
                                       GO_TO_POSITION, IDLE, Monster)
from nightjar.sim import Sim                                        # noqa: E402


def _walkable(level):
    s = Sim(level)
    assert s.run_until(lambda: s.interpreter.player_can_walk, limit=200)
    return s


def _face(s, point):
    p = s.player.position
    want = math.atan2(point[1] - p[1], point[0] - p[0])
    diff = (want - s.player.player_angle + math.pi) % (2 * math.pi) - math.pi
    s.turn(diff)


def _walk(s, n, gap=0.55):
    foot = 'L'
    for _ in range(n):
        s.foot(foot)
        foot = 'R' if foot == 'L' else 'L'
        s.step(gap)


def test_an_alert_reaches_a_monster_that_is_not_switched_on_yet():
    """alertEnemy: has no active test (0x10001e0ec); update: has
    (0x10001d0d8).  Level 12's monster alerts itself from its OnLoad while the
    intro plays, and comes for you as soon as it is switched on."""
    s = Sim('nightJar_12')
    m = s.level.agent('wrigley1')
    assert not m.active and m.state == ALERT_PLAYER
    s.run_until(lambda: m.active, limit=60)
    s.step(0.2)
    assert 'Wrigley_aware' in s.played()                 # the roar first
    s.step(1.2)
    assert m.state == CHASE_PLAYER and m.speed == 28.3
    assert 'Monster_chase_COMP' in s.played()


def test_level_12_catches_you_if_you_climb_at_a_walk():
    s = _walkable('nightJar_12')
    assert not s.interpreter.player_can_rotate           # a ladder: up only
    _walk(s, 40, gap=0.6)
    s.run_until(lambda: s.level.finished, limit=60)
    assert s.level.next_level == 'nightJar_12'
    assert 'Deathladdernew' in s.played()


def test_the_dark_matter_follows_its_path_from_its_own_onload():
    s = _walkable('nightJar_7')
    dm = s.level.agent('dm1')
    assert dm.active and dm.has_path
    # it starts beside the path and heads for its first point, then walks the
    # line (path1 is vertical, x = 0 in the level's coordinates) and back
    s.step(12.0)
    x0, y0 = dm.position
    s.step(2.0)
    x1, y1 = dm.position
    assert abs(x0) < 1.0 and abs(x1) < 1.0
    assert math.isclose(abs(y1 - y0), 21.3 * 2.0, rel_tol=0.1)


def test_touching_the_dark_matter_kills_you():
    s = _walkable('nightJar_7')
    dm = s.level.agent('dm1')
    s.player.position = dm.position
    s.bus.post('PGE_MESSAGE_PlayerMovedToPosition', s.player.get_state_dictionary())
    s.step(0.2)
    assert 'Death_DarkMatter' in s.played()
    s.run_until(lambda: s.level.finished, limit=60)
    assert s.level.next_level == 'nightJar_7'            # the same level: you lost


def _into_hot_water(s):
    band = next(f for f in s.level.floors if f.footsteps_prefix == 'foot_hotwater'
                and f.rect[3] == 150)
    x, y, w, h = band.rect
    s.player.position = (x + w - 40, y - 5)              # just below it, far from the monster
    _face(s, (x + w - 40, y + h))
    s.step(0.1)
    return band


def test_hot_water_growls_on_the_first_step_and_alerts_on_the_next():
    s = _walkable('nightJar_8')
    m = s.level.agent('wrigley1')
    _into_hot_water(s)
    _walk(s, 1)
    assert 'chase_violinTrill' in s.played() and 'Wrigley_aware' in s.played()
    assert not s.sent('PGE_MESSAGE_AlertAllEnemies')     # OnEnter, not OnStep
    _walk(s, 2)
    assert s.sent('PGE_MESSAGE_AlertAllEnemies')[-1]['to'] == 'position'
    s.step(1.2)
    assert m.state == GO_TO_POSITION and 'Chase_mono' in s.played()


def test_the_last_egg_wakes_the_mother_and_opens_the_door():
    s = _walkable('nightJar_9')
    m, exit_ = s.level.agent('wrigley1'), s.level.agent('exit')
    egg3 = s.level.agent('egg3')
    assert egg3.collide_radius == 25.0
    for name in ('egg0', 'egg1', 'egg2'):
        s.level.agent(name).set_active(False)
    egg3.set_active(True)
    s.player.position = egg3.position
    s.bus.post('PGE_MESSAGE_PlayerMovedToPosition', s.player.get_state_dictionary())
    s.step(0.2)
    assert exit_.active
    assert 'Wrigley_MamaEggAware' in s.played()
    s.step(1.2)
    assert m.state == GO_TO_POSITION


def test_level_13s_second_monster_wakes_half_a_second_after_the_first():
    s = Sim('nightJar_13')
    w1, w2 = s.level.agent('wrigley1'), s.level.agent('wrigley2')
    s.run_until(lambda: w1.active, limit=200)
    t1 = s.now
    assert not w2.active
    s.run_until(lambda: w2.active, limit=5)
    assert math.isclose(s.now - t1, 0.5, abs_tol=0.02)
    assert w1.state == IDLE and w2.state == IDLE          # asleep until disturbed


def test_level_13s_right_hand_floor_sets_both_monsters_on_you():
    s = _walkable('nightJar_13')
    s.step(0.6)
    right = next(f for f in s.level.floors
                 if any(t.notification_name.endswith('AlertAllEnemies') for t in f.triggers))
    x, y, w, h = right.rect
    s.player.position = (x - 5, y + h / 2)
    _face(s, (x + w, y + h / 2))
    _walk(s, 1)
    s.step(0.2)
    assert all(m.state in (ALERT_PLAYER, CHASE_PLAYER)
               for m in s.level.agents if isinstance(m, Monster))


def test_a_monster_goes_quiet_when_it_has_you_and_the_level_is_lost():
    s = _walkable('nightJar_6')
    m = s.level.agent('wrigley1')
    s.player.position = m.position
    s.bus.post('PGE_MESSAGE_PlayerMovedToPosition', s.player.get_state_dictionary())
    s.step(0.3)
    assert m.state == ATTACK and 'death2' in s.played()
    s.run_until(lambda: s.level.finished, limit=60)
    assert s.level.next_level == 'nightJar_6'


def test_level_6_trip_plays_dont_run_too_fast_and_wakes_the_monster():
    """Decision 2: the Player's OnTrip names the line as a message."""
    s = _walkable('nightJar_6')
    m = s.level.agent('wrigley1')
    _walk(s, 8, gap=0.18)                                 # 333 steps a minute: over 280
    assert 'prompt_d_lvl5_i' in s.played()
    assert m.state != IDLE


def _collect(s, name):
    a = s.level.agent(name)
    s.run_until(lambda: a.active, limit=120)
    s.player.position = a.position
    s.bus.post('PGE_MESSAGE_PlayerMovedToPosition', s.player.get_state_dictionary())
    s.step(0.1)
    s.player.position = (s.player.position[0], s.player.position[1] - 30)   # step off it


def test_decision_2s_hint_lines_are_heard_when_you_wait():
    """Standing still long enough plays each line decision 2 put in a hint list."""
    for level, line, before in (('nightJar_6', 'prompt_d_lvl6_c', ()),
                                ('nightJar_7', 'prompt_d_lvl7_e', ()),
                                ('nightJar_9', 'prompt_d_lvl8_e', ('egg0',)),
                                ('nightJar_13', 'prompt_d_lvl12_a', ('note1', 'note2'))):
        s = _walkable(level)
        for name in before:
            _collect(s, name)
        assert s.run_until(lambda: line in s.played(), limit=240), (level, line)
        assert not s.level.finished, (level, 'died waiting')


def test_decision_8_level_13s_footsteps_are_6_db_louder():
    for level, gain in (('nightJar_13', 1.0), ('nightJar_11', 0.5), ('nightJar_14', 0.5)):
        s = _walkable(level)
        assert s.player.footstep_gain == gain
        _walk(s, 2)
        steps = [s.bank.sound(n) for n in set(s.played()) if n.startswith('foot_')]
        assert steps and all(x.gain == gain for x in steps), level


# ------------------------------------------------ Seth's beta report (decision 9)
def test_9a_level_8s_growl_comes_from_the_monster():
    s = _walkable('nightJar_8')
    m = s.level.agent('wrigley1')
    _into_hot_water(s)
    _walk(s, 1)
    growl = s.bank.sound('Wrigley_aware')
    assert growl.spatialized and growl.planar[:2] == m.position


def test_9b_level_5s_door_cuts_off_the_creature():
    s = _walkable('nightJar_5')
    s.bus.post('PGE_MESSAGE_PlaySound', {'soundName': 'LVL5c'})
    s.step(0.5)
    assert 'LVL5c' in s.playing()
    note = s.level.agent('note1')
    s.player.position = note.position
    s.bus.post('PGE_MESSAGE_PlayerMovedToPosition', s.player.get_state_dictionary())
    s.step(0.2)
    assert 'LVL5c' not in s.playing() and 'LVL5d' in s.playing()   # the door


def test_9d_hot_water_steps_are_6_db_louder_and_metal_is_not():
    s = _walkable('nightJar_8')
    _into_hot_water(s)
    _walk(s, 2)
    hot = [s.bank.sound(n) for n in set(s.played()) if n.startswith('foot_hotwater')]
    assert hot and all(x.gain == 1.0 for x in hot)
    s2 = _walkable('nightJar_8')
    _walk(s2, 2)                                          # on the room's metal
    metal = [s2.bank.sound(n) for n in set(s2.played()) if n.startswith('foot_metalsolid')]
    assert metal and all(x.gain == 0.5 for x in metal)
