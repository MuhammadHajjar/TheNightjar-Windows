"""Levels 2 to 5: what the data asks for, as the engine does it, and the
requested changes (decisions 2 and 5)."""

import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.sim import Sim                                        # noqa: E402
from nightjar.world.surface import DEFAULT_TRIP_BPM, ROOM_TRIP_BPM  # noqa: E402


def test_a_floor_strip_without_a_trip_speed_gets_350_and_the_room_280():
    # -[PGELevel createObjectFromDict:]: Surface 350 (0x100030848), Room 280 (0x10002fcc4)
    assert (DEFAULT_TRIP_BPM, ROOM_TRIP_BPM) == (350.0, 280.0)
    s = Sim('nightJar_2')                         # the room says 220, the strips nothing
    assert s.level.trip_bpm == 220.0
    assert all(f.trip_bpm == 350.0 for f in s.level.floors)
    s = Sim('nightJar_3')                         # a room that names no trip speed
    assert s.level.trip_bpm == 280.0


def test_level_2_is_a_straight_walk_with_turning_off():
    s = Sim('nightJar_2')
    s.run_until(lambda: s.interpreter.player_can_walk, limit=60)
    assert not s.interpreter.player_can_rotate


def test_running_too_fast_on_level_2_trips_you_with_its_own_sound():
    s = Sim('nightJar_2')
    s.run_until(lambda: s.interpreter.player_can_walk, limit=60)
    foot = 'L'
    for _ in range(12):                           # 0.2 s a step: 300 steps a minute
        s.foot(foot)
        foot = 'R' if foot == 'L' else 'L'
        s.step(0.2)
    assert 'LVL2trip_mhollow' in s.played()       # the Room's tripSound, exact lookup


def _no_turning(level):
    s = Sim(level)
    s.run_until(lambda: s.interpreter.player_can_rotate, limit=200)
    return s


def test_level_3_turns_and_hears_the_beep_behind_it():
    s = _no_turning('nightJar_3')
    assert not s.interpreter.player_can_walk
    clock = s.level.agent('clock_15sec')
    s.step(0.2)
    assert clock.active and not clock.is_in_shooting_range     # behind you
    s.turn(math.pi)                                            # face it
    s.step(0.2)
    assert s.sent('PGE_MESSAGE_ActivateAgentWithName')[-1]['name'] == 'LVL3_1B'


def test_decision_5_level_3s_three_lines_are_its_hints():
    s = _no_turning('nightJar_3')
    t0 = s.now
    hints = ['prompt_d_lvl3_a', 'prompt_d_lvl3_b', 'prompt_d_lvl3_d 2']
    for h in hints:
        s.run_until(lambda h=h: h in s.played(), limit=40)
        assert h in s.played()
    first = s.log[[n for _, _, n in s.log].index('prompt_d_lvl3_a')][0]
    assert first - t0 == pytest.approx(20.0, abs=0.3)
    # and they stop when the level shuts down (the sensor faced)
    from nightjar.autopilot import Autopilot
    ap = Autopilot(s)
    while not s.level.finished and s.now < t0 + 300:
        ap.tick()
        s.step(0.05)
    assert s.level.finished and s.level.inactivity_sounds == []


def test_the_level_4_sensor_leads_to_the_door_and_changes_the_hints():
    from nightjar.autopilot import Autopilot
    s = Sim('nightJar_4')
    ap = Autopilot(s)
    while not s.level.agent('note1').was_collected and s.now < 200:
        ap.tick()
        s.step(0.05)
    s.step(0.1)
    assert s.level.inactivity_sounds == ['prompt_d_lvl4_e', 'prompt_d_lvl4_f', 'prompt_d_lvl4_a']
    s.run_until(lambda: s.level.agent('exit').active, limit=30)
    assert 'LVL4b' in s.played()


def test_level_5s_shuffle_is_silent_as_in_the_original():
    s = Sim('nightJar_5')
    s.run_until(lambda: s.interpreter.player_can_walk, limit=60)
    s.foot('L')
    s.step(0.5)
    s.foot('R')
    s.step(3.0)                                   # the shuffle falls due two seconds later
    assert s.player.shuffle_sound == 'foot_stone_01_dry_shuffle'
    assert not any('shuffle' in n for n in s.played())


# ------------------------------------------------------------ decision 2, later levels
def test_decision_2_level_6s_trip_line_plays():
    s = Sim('nightJar_6')
    trips = [t for t in s.player.triggers if t.trigger_type == 'OnTrip']
    assert trips and trips[0].notification_name == 'PGE_MESSAGE_PlaySound'
    assert trips[0].parameters['soundName'] == 'prompt_d_lvl5_i'
    assert s.bank.has('prompt_d_lvl6_c')


def test_decision_2_level_7s_hint_is_the_real_file():
    s = Sim('nightJar_7')
    assert 'prompt_d_lvl7_e' in s.level.inactivity_sounds
    assert 'prompt_d_lvl7_e_alt' not in s.level.inactivity_sounds
    assert s.bank.has('prompt_d_lvl7_e')


def test_decision_2_level_9s_egg_line_is_declared():
    assert Sim('nightJar_9').bank.has('prompt_d_lvl8_e')


def test_decision_2_level_13s_note_2_changes_the_hints():
    s = Sim('nightJar_13')
    note = s.level.agent('note2')
    assert any(t.trigger_type == 'OnCollide' and t.notification_name ==
               'PGE_MESSAGE_ChangeInactivitySoundList' for t in note.triggers)
