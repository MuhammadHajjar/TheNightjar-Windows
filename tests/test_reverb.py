"""The reverb: the recovered Freeverb, the per-sound dry/wet mix, and the
port's OpenAL reverb measured against the original's on the same input."""

import math
import os
import sys

import numpy as np
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.audio import freeverb as FV                         # noqa: E402
from nightjar.audio.engine import Sound, SoundSpec, reverb_params  # noqa: E402
from nightjar.entities.collectible import INTRO_REVERB, LOOP_REVERB  # noqa: E402
from nightjar.entities.monster import ENEMY_REVERB                # noqa: E402

ROOM = (2.1, 5, 1.0)          # -[PGEngine init]: the whole game's one reverb


# ----------------------------------------------------------- the Freeverb
def test_the_fast_model_is_the_recovered_loop_sample_for_sample():
    x = np.zeros(8000)
    x[0] = 1.0
    x[3000] = -0.5
    slow = FV.process(x, *ROOM)
    h = FV.impulse_response(*ROOM)[:8000]
    fast = np.convolve(x, h)[:8000]
    assert np.max(np.abs(slow - fast)) < 1e-12


def test_the_recovered_constants():
    # setRoomSize (NJ 0x1000c3600): size * 0.28 + 0.3; setDampening
    # (0x1000c3694): dampening * 0.01 * 0.4; init (0x1000c29b0): 6 combs,
    # 3 allpasses, input gain 0.015
    assert FV.coefficients(2.1, 5) == pytest.approx((2.1 * 0.28 + 0.3, 5 * 0.004))
    assert FV.coefficients(9.0, 150) == FV.coefficients(2.3, 100)
    assert FV.COMB_TUNING == (1116, 1188, 1277, 1356, 1422, 1491)
    assert FV.ALLPASS_TUNING == (556, 441, 341)
    assert FV.FIXED_GAIN == 0.015


def test_nothing_comes_out_before_the_shortest_comb():
    h = FV.impulse_response(*ROOM)
    assert np.max(np.abs(h[:FV.COMB_TUNING[0]])) < 1e-12
    assert abs(h[FV.COMB_TUNING[0]]) > 1e-4


# ------------------------------------------------------- the EFX mapping
def test_the_efx_decay_follows_the_freeverb():
    p = reverb_params(*ROOM)
    assert p['DECAY_TIME'] == pytest.approx(FV.loop_decay(2.1, 5, 1000))
    assert p['DECAY_HFRATIO'] == pytest.approx(FV.loop_decay(2.1, 5, 5000)
                                               / FV.loop_decay(2.1, 5, 1000))
    assert p['GAINHF'] == 1.0
    assert p['REFLECTIONS_GAIN'] == 0.0


# --------------------------------------------------- the per-sound mix
class StubEngine:
    reverb_slot = 1
    head_position = (0.0, 0.0, 0.0)
    head_orientation = 0.0


def sound(**kw):
    s = Sound(StubEngine(), SoundSpec('s', 'x', spatialized=True), 0, 1.0, 1)
    for k, v in kw.items():
        setattr(s, k, v)
    return s


def test_the_recovered_sends():
    # -[PGECollectible playIntroSound] / startLoop, -[PGEEnemy playSound:looping:]
    assert (INTRO_REVERB['min_distance'], INTRO_REVERB['max_distance'],
            INTRO_REVERB['min_wet_send'], INTRO_REVERB['max_wet_send']) == (1.0, 2.0, 0.1, 0.75)
    assert (LOOP_REVERB['min_distance'], LOOP_REVERB['max_distance'],
            LOOP_REVERB['min_wet_send'], LOOP_REVERB['max_wet_send']) == (1.0, 100.0, 0.05, 0.3)
    assert ENEMY_REVERB == LOOP_REVERB


@pytest.mark.parametrize('d, wet', [(0.5, 0.05), (1.0, 0.05), (50.5, 0.175),
                                    (100.0, 0.3), (400.0, 0.3)])
def test_auto_reverb_mix_follows_the_distance(d, wet):
    s = sound(send_to_reverb=True, dry_gain=1.0, wet_gain=0.5, reverb_mix=dict(LOOP_REVERB))
    s._planar = (d, 0.0, 0.0)
    assert s._auto_mix()
    assert s.wet_gain == pytest.approx(wet)
    assert s.dry_gain == pytest.approx(1.0 - wet)


def test_a_door_opening_is_mostly_reverb_beyond_two_pixels():
    s = sound(send_to_reverb=True, reverb_mix=dict(INTRO_REVERB))
    s._planar = (80.0, 0.0, 0.0)
    s._auto_mix()
    assert (s.wet_gain, s.dry_gain) == pytest.approx((0.75, 0.25))


def test_no_send_means_the_dry_gain_plays_no_part():
    s = sound(gain=0.8, dry_gain=0.3, send_to_reverb=False)
    assert s._mix() == (0.8, 1.0, 0.0)


def test_with_a_send_the_louder_path_rides_on_the_source_gain():
    s = sound(gain=0.5, dry_gain=0.7, wet_gain=0.3, send_to_reverb=True)
    g, direct, send = s._mix()
    assert g == pytest.approx(0.35) and direct == 1.0 and send == pytest.approx(0.3 / 0.7)


# --------------------------------------- measured against the original
def _measure(room, distances, angles):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        'measure_reverb', os.path.join(ROOT, 'tools', 'measure_reverb.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    try:
        return m.measure('t', room, distances, angles)
    except SystemExit:
        pytest.skip('no EFX reverb on this machine')


def test_the_ports_reverb_matches_the_original_in_level_and_decay():
    rows = _measure(ROOM, (50,), (0.0, 45.0, 90.0, 180.0))
    diffs = [r['diff'] for r in rows]
    assert all(abs(x) < 4.5 for x in diffs), diffs                # direction: PORT-SIDE
    assert abs(sum(diffs) / len(diffs)) < 0.5, diffs
    for r in rows:
        assert r['t60_port'] == pytest.approx(r['t60_orig'], rel=0.15)
        assert r['hf_port'] == pytest.approx(r['hf_orig'], rel=0.15)


def test_the_reverb_falls_off_with_distance_exactly_like_the_direct_sound():
    rows = _measure(ROOM, (1, 100, 400), (45.0,))
    offsets = [r['diff'] for r in rows]
    assert max(offsets) - min(offsets) < 0.5, offsets
    assert rows[1]['orig'] - rows[0]['orig'] == pytest.approx(
        20 * math.log10((0.3 / 0.7) / (0.05 / 0.95)), abs=0.1)
