"""A level is not done until the autopilot wins it, on several seeds."""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.autopilot import play_level                           # noqa: E402

#: Every level, and where each must lead (nightJar_14 ends the game).
PORTED = {f'nightJar_{i}': f'nightJar_{i + 1}' for i in range(1, 14)}


@pytest.mark.parametrize('seed', [1, 2, 3, 4, 5])
@pytest.mark.parametrize('level', sorted(PORTED))
def test_the_autopilot_wins(level, seed):
    won, s, ap = play_level(level, seed=seed)
    assert won, f'{level} seed {seed}: stuck at {s.player.position}, t={s.now:.0f}'
    assert s.level.next_level == PORTED[level]
    if level != 'nightJar_3':                   # level 3: turning only
        assert ap.steps > 0


@pytest.mark.parametrize('seed', [1, 2, 3])
@pytest.mark.parametrize('door, outro', [('doorA', 'Outro_A'), ('doorB', 'Outro_B_Death_Reigns')])
def test_both_doors_end_the_game(door, outro, seed):
    won, s, ap = play_level('nightJar_14', seed=seed, prefer=door)
    assert won and s.level.game_complete
    assert outro in s.played()
    assert s.sent('PGE_MESSAGE_PresentAdiosVC')
