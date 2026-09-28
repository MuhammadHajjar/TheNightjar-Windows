"""The recovered engine (1_1_020): loading, the level clock, sounds, sensors
and doors, the hint timer, and level 1 end to end in the simulator."""

import math
import os
import random
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.assets.tiled import level_path, load_level           # noqa: E402
from nightjar.core.game import Game                                 # noqa: E402
from nightjar.save.progress import InMemoryProgress                 # noqa: E402
from nightjar.sim import FakeBank, Sim                              # noqa: E402
from nightjar.util import paths                                     # noqa: E402
from nightjar.world.level import TICK                               # noqa: E402

LEVELS = ['nightJar_%d' % i for i in range(1, 15)]


# ------------------------------------------------------------ loading
@pytest.mark.parametrize('name', LEVELS)
def test_every_level_loads_and_starts(name):
    s = Sim(name)
    s.step(1.0)
    assert s.player is not None
    assert s.level.rect[2] > 0 and s.level.rect[3] > 0


def test_world_y_is_tiled_y_negated():
    d = load_level(level_path(paths.game_bundle(), 'nightJar_1'), 'nightJar_1')
    exit_ = d.by_name('exit')
    # Room at (10,10) 480x600 -> centre (250, 310); the door at Tiled (244,130)
    assert (exit_.x, exit_.y) == (244 - 250, -(130 - 310))
    assert (d.player.x, d.player.y) == (240 - 250, -(480 - 310))


def test_the_level_ticks_every_tenth_of_a_second():
    assert TICK == 0.1


# ------------------------------------------------------------ the clock
class _Settings:
    pc_instructions = True


def test_game_time_keeps_pace_with_the_wall_clock():
    """13 ms frames must add up to 13 s, not 10 (Papa Sangre II's port ran 6 %
    slow by rounding each frame to whole 10 ms steps)."""
    g = Game(paths.game_bundle(), InMemoryProgress(), _Settings(), lambda n: None)
    for _ in range(1000):
        g.update(0.013)
    assert g.now == pytest.approx(13.0, abs=0.011)


# ------------------------------------------------------------ level 1
def test_level_1_opens_with_its_cutscene_after_the_activation_delay():
    s = Sim('nightJar_1')
    s.step(0.04)
    assert s.played() == []
    s.step(0.02)
    assert s.played() == ['Cutcene1_final']        # -[PGESound activate]: 0.05 s


def test_level_1_locks_the_controls_until_the_third_cutscene_ends():
    s = Sim('nightJar_1')
    s.step(0.2)
    assert not s.interpreter.player_can_walk
    assert not s.interpreter.player_can_rotate
    s.run_until(lambda: s.interpreter.player_can_walk, limit=400)
    order = [n for n in s.played()]
    assert order[:3] == ['Cutcene1_final', 'cutscene_friday2', 'cutscene_friday3']
    # friday3's OnSoundEnd enables walking but not turning (the level's data)
    assert not s.interpreter.player_can_rotate
    assert s.level.inactivity_time == 20.0


def test_level_1_can_be_won():
    s = Sim('nightJar_1')
    s.run_until(lambda: s.interpreter.player_can_walk, limit=400)
    foot = 'L'
    while not s.level.finished and s.now < 700:
        if s.foot(foot):
            foot = 'R' if foot == 'L' else 'L'
        s.step(0.5)
    assert s.level.next_level == 'nightJar_2'
    played = s.played()
    for line in ('easteregg_creakgroana_01_dry', 'LVL1_cutscene2b',
                 'easteregg_shipcreakb_01_dry', 'LVL1_cutscene2c'):
        assert line in played


# ------------------------------------------------------------ win and lose
def _game():
    bundle = paths.game_bundle()
    holder = {}

    def bank(name):
        return FakeBank(holder['sim'], bundle, name, random.Random(1))

    g = Game(bundle, InMemoryProgress(), _Settings(), bank)

    class _Clock:
        @property
        def now(self):
            return g.now
        log = []
    holder['sim'] = _Clock()
    return g


def test_loading_another_level_is_a_win_and_unlocks_it():
    g = _game()
    g.load('nightJar_1')
    g.bus.post('PGE_MESSAGE_LoadLevelWithName', {'name': 'nightJar_2'})
    assert g.outcome == ('win', 'nightJar_1', 'nightJar_2')
    assert g.progress.is_level_completed('nightJar_1')
    assert g.progress.is_level_unlocked('nightJar_2')


def test_loading_the_same_level_is_a_loss():
    g = _game()
    g.load('nightJar_6')
    g.bus.post('PGE_MESSAGE_LoadLevelWithName', {'name': 'nightJar_6'})
    assert g.outcome == ('lose', 'nightJar_6', 'nightJar_6')
    assert not g.progress.is_level_completed('nightJar_6')


def test_the_last_playlist_is_saved_on_load():
    g = _game()
    g.load('nightJar_3')
    assert g.progress.get_last_playlist() == 'nightJar_3'


def test_a_fresh_save_starts_at_level_1():
    p = InMemoryProgress()
    assert p.last_unlocked_level == 'nightJar_1'
    assert p.get_last_playlist() == 'nightJar_1'


# ------------------------------------------------------------ PGESound
def test_a_skippable_line_can_only_be_skipped_once_heard():
    s = Sim('nightJar_3')
    s.step(0.2)
    assert s.sent('PGE_MESSAGE_ShowSkipButton') == []
    s.skip()
    assert 'LVL3_1A' in s.playing()                  # not heard before: no skip
    # heard to the end once, it may be skipped next time
    s.run_until(lambda: 'LVL3_1A' not in s.playing(), limit=200)
    assert s.progress.can_skip_sound('LVL3_1A')
    s2 = Sim('nightJar_3', progress=s.progress)
    s2.step(0.2)
    assert s2.sent('PGE_MESSAGE_ShowSkipButton')
    s2.skip()
    assert 'LVL3_1A' not in s2.playing()
    assert 'Atmos_transcendental' in s2.bank.specs    # and its OnSoundEnd ran:
    s2.step(0.2)
    assert 'Atmos_transcendental' in s2.playing()


# ------------------------------------------------------------ PGECollectible
def test_a_collectible_whose_intro_is_its_loop_goes_straight_to_the_loop():
    s = Sim('nightJar_14')                           # doorA: End_Sensor both
    a = s.level.agent('doorA')
    a.set_active(True)
    s.bus.update(s.now)
    assert a.sound is not None and a.sound.name == 'End_Sensor' and a.sound.looping


def test_a_door_plays_its_intro_then_its_loop():
    s = Sim('nightJar_1')
    a = s.level.agent('exit')
    a.set_active(True)
    s.bus.update(s.now)
    assert a.sound.name == 'Door_pneumatic_appear' and not a.sound.looping
    assert a.sound.reverb_mix['max_distance'] == 2.0
    s.run_until(lambda: a.sound is not None and a.sound.name == 'Door_pneumatic_living', limit=10)
    assert a.sound.looping and a.sound.reverb_mix['max_distance'] == 100.0


def test_a_collectible_never_fires_onactivate():
    s = Sim('nightJar_1')
    a = s.level.agent('exit')
    fired = []
    orig = a.trigger
    a.trigger = lambda t: (fired.append(t), orig(t))[1]
    a.set_active(True)
    assert 'OnActivate' not in fired


# ------------------------------------------------------------ the hint timer
def test_hints_wait_for_a_time_to_be_set():
    s = Sim('nightJar_1')
    assert s.level.inactivity_time == math.inf       # -[PGELevel init]
    s.step(30.0)
    assert not any(n.startswith('prompt_') for n in s.played())


def test_hints_play_in_turn_and_restart_the_clock_while_playing():
    s = Sim('nightJar_1')
    s.run_until(lambda: s.interpreter.player_can_walk, limit=400)
    t0 = s.now
    s.run_until(lambda: 'prompt_d_lvl1_c' in s.played(), limit=40)
    assert s.now - t0 == pytest.approx(20.0, abs=0.25)
    s.run_until(lambda: 'prompt_d_lvl1_b' in s.played(), limit=60)
    first = s.bank.sound('prompt_d_lvl1_c').duration
    # the next one comes 20 s after the first *ended*
    assert s.now - t0 == pytest.approx(20.0 + first + 20.0, abs=0.3)


def test_a_hint_that_does_not_resolve_is_a_silent_turn():
    s = Sim('nightJar_1')
    s.level.set_inactivity_sounds('no_such_line&prompt_d_lvl1_a')
    s.level.inactivity_time = 1.0
    s.level.last_activity = s.now
    s.step(1.2)
    assert s.level.current_inactivity_sound == 1
    assert not s.playing() or 'prompt_d_lvl1_a' not in s.playing()
    s.step(1.2)
    assert 'prompt_d_lvl1_a' in s.playing()


# ------------------------------------------------------------ PlaySpatialSoundOnAgentWithName
def test_a_sound_played_on_an_agent_is_put_on_it():
    """-[PGEGameAgent playSpatialSoundOnAgentWithName:]'s block never sets a
    position (0x100021c2c) - the sound would play where its object last was.
    Decision 9a (Seth's beta report) puts it on the agent."""
    s = Sim('nightJar_8')
    snd = s.bank.sound('Wrigley_aware')
    snd.planar = (12.0, 34.0, 0.0)
    s.bus.post('PGE_MESSAGE_PlaySpatialSoundOnAgentWithName',
               {'agentName': 'wrigley1', 'soundName': 'Wrigley_aware'})
    assert snd.playing and snd.spatialized
    assert snd.planar[:2] == s.level.agent('wrigley1').position


# ------------------------------------------------------------ PGEEnemy
def test_an_enemy_sound_keeps_its_playlist_flag_and_gets_the_distance_mix():
    s = Sim('nightJar_6')
    m = s.level.agent('wrigley1')
    snd = s.bank.sound('Wrigley_eating')
    snd.spatialized = False                          # whatever it was last set to
    m.play_sound('Wrigley_eating')
    assert snd.playing and not snd.spatialized       # no setSpatialized: here
    assert snd.send_to_reverb and snd.reverb_mix['max_wet_send'] == 0.3
