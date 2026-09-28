"""The audio layer, checked against the recovered arithmetic and by rendering.

The listener transform is checked against ``-[S3DEngine
normalizeToHeadPosition:]``, and the binaural chain by rendering through
OpenAL Soft's loopback device and measuring the result - so a broken HRTF, a
flipped axis or a lost .mhr fails the suite instead of quietly sounding wrong.
Every sound here is one of The Nightjar's own files.
"""

import math
import os
import struct
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.audio.engine import (                             # noqa: E402
    COINCIDENT_OFFSET, DISTANCE_SCALE, MASTER_GAIN, MAX_SPATIAL_GAIN,
    csl_to_openal, normalize_to_head)
from nightjar.audio.loader import decode                        # noqa: E402

BUNDLE = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app')
# Every Nightjar sound is stereo on disk - even Chase_mono - so the fold to
# mono for the spatialiser is what makes any of it positional.
SPATIAL_STEREO = ('nightjar_sounds', 'collectables', 'Door_pneumatic_living.m4a')  # a door beacon
MONSTER = ('nightjar_sounds', 'monsters', 'Chase_mono.m4a')                         # a monster loop
TRANSIENT = ('nightjar_sounds', 'collectables', 'Door_pneumatic_appear.m4a')        # a door opening
AMBIENCE = ('nightjar_sounds', 'atmos', 'Atmos_cargobay.m4a')                       # flat stereo bed
VOICE = ('nightjar_sounds', 'prompts', 'prompt_d_lvl1_b.m4a')                       # flat narration
HRTF_MHR = os.path.join(ROOT, 'build', 'hrtf', 'papa_ircam_1050.mhr')


# ------------------------------------------------------- recovered constants
def test_recovered_constants():
    # -[PGELevel initSoundEngine] 0x10002ca98 (The Nightjar's branch),
    # -[S3DEngine init] 0x1000d0d98 / 0x1000d111c
    assert DISTANCE_SCALE == 0.015625
    assert MAX_SPATIAL_GAIN == 100.0
    assert MASTER_GAIN == 1.0


# ------------------------------------------------------- listener transform
def test_source_at_head_is_nudged_aside():
    out = normalize_to_head(10.0, 10.0, 0.0, 10.0, 10.0, 0.0, 0.0)
    assert out[1] == COINCIDENT_OFFSET * DISTANCE_SCALE
    assert out[0] == 0.0


def test_forward_is_plus_x_in_csl_space():
    out = normalize_to_head(100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert abs(out[0] - 100.0 * DISTANCE_SCALE) < 1e-9
    assert abs(out[1]) < 1e-9


def test_left_is_plus_y_in_csl_space():
    out = normalize_to_head(0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert abs(out[0]) < 1e-6
    assert abs(out[1] - 100.0 * DISTANCE_SCALE) < 1e-9


def test_turning_rotates_the_world_the_other_way():
    out = normalize_to_head(0.0, 100.0, 0.0, 0.0, 0.0, 0.0, 90.0)
    assert abs(out[0] - 100.0 * DISTANCE_SCALE) < 1e-6
    assert abs(out[1]) < 1e-6


def test_distance_scale_is_applied():
    out = normalize_to_head(128.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    assert abs(out[0] - 2.0) < 1e-9          # 128 px == 2 units at 1/64


def test_axis_mapping_to_openal():
    assert csl_to_openal(1.0, 0.0, 0.0) == (0.0, 0.0, -1.0)
    assert csl_to_openal(0.0, 1.0, 0.0) == (-1.0, 0.0, 0.0)
    assert csl_to_openal(0.0, 0.0, 1.0) == (0.0, 1.0, 0.0)


# ------------------------------------------------------- asset decoding
def test_decoded_audio_matches_the_original_bit_for_bit():
    """The port must not alter the shipped audio in any way."""
    import subprocess
    path = os.path.join(BUNDLE, *SPATIAL_STEREO)
    pcm = decode(path)
    try:
        ref = subprocess.run(
            ['ffmpeg', '-v', 'error', '-i', path, '-f', 's16le', '-acodec',
             'pcm_s16le', '-'], capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return                                   # no ffmpeg on this machine
    got = pcm.samples.reshape(-1)
    exp = np.frombuffer(ref, dtype='<i2')
    assert got.shape == exp.shape
    assert np.array_equal(got, exp)
    assert pcm.sample_rate == 44100


def test_every_positioned_sound_is_folded_to_mono_for_the_spatialiser():
    """A stereo buffer bypasses the HRTF entirely (OpenAL only spatialises
    mono), and every Nightjar file is stereo."""
    for rel in (SPATIAL_STEREO, MONSTER, TRANSIENT):
        path = os.path.join(BUNDLE, *rel)
        assert decode(path).channels == 2, rel
        assert decode(path, mono=True).channels == 1, rel


def test_mono_downmix_preserves_length_and_level():
    path = os.path.join(BUNDLE, *SPATIAL_STEREO)
    stereo = decode(path)
    mono = decode(path, mono=True)
    assert mono.frames == stereo.frames
    a = stereo.samples.astype(np.float64).mean(axis=1)
    b = mono.samples.astype(np.float64).reshape(-1)
    assert np.max(np.abs(a - b)) <= 1.0


# ------------------------------------------------------- rendered output
def test_recovered_hrtf_was_built():
    assert os.path.exists(HRTF_MHR), 'run tools/extract_hrtf.py then makemhr'


def test_rendered_binaural_cues_are_physically_correct():
    """End-to-end through OpenAL: a lost .mhr, a flipped axis, swapped ears or
    a bypassed HRTF all fail here."""
    from nightjar.audio.measure import LoopbackRenderer, check, sweep
    r = LoopbackRenderer()
    try:
        assert r.hrtf_status == 'enabled', f'HRTF status {r.hrtf_status}'
        assert 'papa_ircam_1050' in r.available
        rows = sweep(r)
        failures = check(rows)
        assert not failures, '; '.join(failures)
        lateral = max(abs(itd) for b, itd, _ in rows if b in (90.0, 270.0))
        assert 0.5 < lateral / r.rate * 1000 < 1.0
    finally:
        r.close()


def test_the_games_own_door_and_monster_are_heard_from_where_they_are():
    """The shipped files, folded to mono and placed left and right, must give
    opposite interaural cues - the stereo-buffer bug gave identical ones."""
    from ctypes import c_uint
    from nightjar.audio import openal as OA
    from nightjar.audio.measure import LoopbackRenderer, interaural
    r = LoopbackRenderer()
    try:
        al = r.al
        for rel in (TRANSIENT, MONSTER):
            pcm = decode(os.path.join(BUNDLE, *rel), mono=True)
            buf = (c_uint * 1)()
            al.alGenBuffers(1, buf)
            raw = pcm.tobytes()
            al.alBufferData(buf[0], OA.AL_FORMAT_MONO16, raw, len(raw), pcm.sample_rate)
            got = {}
            for bearing in (90, 270):
                src = (c_uint * 1)()
                al.alGenSources(1, src)
                s = src[0]
                al.alSourcei(s, OA.AL_BUFFER, buf[0])
                al.alSourcei(s, OA.AL_SOURCE_RELATIVE, OA.AL_TRUE)
                al.alSourcef(s, OA.AL_ROLLOFF_FACTOR, 0.0)
                rad = math.radians(bearing)
                c = normalize_to_head(250 * math.cos(rad), 250 * math.sin(rad),
                                      0, 0, 0, 0, 0.0, DISTANCE_SCALE)
                al.alSource3f(s, OA.AL_POSITION, *csl_to_openal(*c))
                al.alSourcePlay(s)
                out = OA.render_samples(al, r.device, 22050, 2)
                data = np.ctypeslib.as_array(out).reshape(-1, 2).copy()
                got[bearing] = interaural(data)
                al.alSourceStop(s)
                al.alDeleteSources(1, src)
            (itd90, ild90), (itd270, ild270) = got[90], got[270]
            assert ild90 > ild270 + 3, f'{rel}: level does not follow direction'
            assert itd90 != itd270, f'{rel}: 90 and 270 degrees render alike'
    finally:
        r.close()


# ------------------------------------- flat sound never meets the HRTF
def _flat_render(path: str, spatialized_in_playlist: bool, seconds: float = 2.0):
    from nightjar.audio.engine import AudioEngine, SoundSpec
    e = AudioEngine(want_reverb=False)
    e.open(loopback=True)
    try:
        s = e.load(SoundSpec('t', path, spatialized=spatialized_in_playlist))
        s.spatialized = False
        s.play()
        out = np.asarray(e.render(int(44100 * seconds))).reshape(-1, 2)
        s.stop()
        return out, decode(path), e.master_gain * e.master_volume
    finally:
        e.close()


def test_a_flat_stereo_file_plays_as_it_is():
    """setupPlain leaves a two-channel file alone: each ear its own channel,
    untouched but for the master volume - the narration and the ambience."""
    for rel in (VOICE, AMBIENCE):
        out, pcm, master = _flat_render(os.path.join(BUNDLE, *rel), False)
        assert pcm.channels == 2
        src = pcm.samples.astype(np.float64) / 32768.0
        n = 60000
        lag = max(range(0, 2000), key=lambda k: float(np.dot(out[k:k + n, 0], src[:n, 0])))
        for ch in (0, 1):
            x, y = out[lag:lag + n, ch], src[:n, ch]
            assert np.corrcoef(x, y)[0, 1] > 0.9999, rel
            gain = np.sqrt(np.mean(x ** 2)) / np.sqrt(np.mean(y ** 2))
            assert abs(20 * math.log10(gain) - 20 * math.log10(master)) < 0.05, rel


def test_a_flat_mono_file_is_half_level_in_each_ear(tmp_path):
    """setupPlain's csl::Panner at its centre gives each ear half of a
    one-channel file.  No Nightjar file is mono, so this uses a made one."""
    path = str(tmp_path / 'mono.wav')
    t = np.arange(44100 * 2) / 44100.0
    sig = (0.3 * np.sin(2 * math.pi * 440 * t) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(sig.tobytes())
    out, pcm, master = _flat_render(path, True)
    L, R = out[:, 0], out[:, 1]
    assert np.allclose(L, R, atol=1e-6)
    n = min(len(L), len(pcm.samples)) - 4000
    ref = pcm.samples[:n, 0].astype(np.float64) / 32768.0
    gain = np.sqrt(np.mean(L[2000:n] ** 2)) / np.sqrt(np.mean(ref[2000:n] ** 2))
    assert abs(20 * math.log10(gain) - 20 * math.log10(0.5 * master)) < 0.2


def test_spatialised_sources_are_not_direct_channelled():
    from ctypes import byref, c_int
    from nightjar.audio import openal as OA
    from nightjar.audio.engine import AudioEngine, SoundSpec
    eng = AudioEngine()
    eng.open()
    try:
        flat = eng.load(SoundSpec('flat', os.path.join(BUNDLE, *AMBIENCE), spatialized=False))
        spatial = eng.load(SoundSpec('spatial', os.path.join(BUNDLE, *SPATIAL_STEREO),
                                     spatialized=True))
        flat.play()
        spatial.play()
        v = c_int(0)
        eng.al.alGetSourcei(flat.source, OA.AL_DIRECT_CHANNELS_SOFT, byref(v))
        assert v.value != OA.AL_FALSE, 'flat sound should bypass the HRTF'
        eng.al.alGetSourcei(spatial.source, OA.AL_DIRECT_CHANNELS_SOFT, byref(v))
        assert v.value == OA.AL_FALSE, 'spatial sound must go through the HRTF'
        flat.stop()
        spatial.stop()
    finally:
        eng.close()


# ------------------------------------------------------- the one reverb
def test_reverb_is_what_pgengine_init_sets():
    """2.1 / 5 / 1 from -[PGEngine init] (0x1000360e0); nothing changes it."""
    from nightjar.audio.engine import (REVERB_DAMPENING, REVERB_ROOM_SIZE,
                                       REVERB_VOLUME, ROOM_SIZE_RANGE)
    assert (REVERB_ROOM_SIZE, REVERB_DAMPENING, REVERB_VOLUME) == (2.1, 5.0, 1.0)
    # setReverbRoomSize: clamps to [0.01, 2.3] (0x1000d2638 / 0x1000d265c),
    # so 2.1 stands - it is not raised to 2.2 as the PS1 port has it
    assert ROOM_SIZE_RANGE == (0.01, 2.3)


def test_reverb_setters_clamp_like_s3dengine():
    from nightjar.audio.engine import reverb_params
    assert reverb_params(9.0, 50, 1) == reverb_params(2.3, 50, 1)
    assert reverb_params(1.5, 150, 1) == reverb_params(1.5, 100, 1)
    assert reverb_params(1.5, 0, 20) == reverb_params(1.5, 0, 8)
    assert reverb_params(1.5, 100, 0)['GAIN'] == 0.0
    assert reverb_params(2.1, 5, 1) != reverb_params(2.2, 5, 1)


def test_9c_trim_lead_removes_the_click_files_silent_start():
    """click_button.wav opens with 116 ms of silence; trimmed, it starts 2 ms
    before its first sample within 40 dB of the peak."""
    import os
    import numpy as np
    from nightjar.audio.engine import trim_lead
    from nightjar.audio.loader import decode
    from nightjar.util import paths
    pcm = decode(os.path.join(paths.game_bundle(), 'click_button.wav'), mono=False)
    cut = trim_lead(pcm)
    lead = (pcm.frames - cut.frames) / pcm.sample_rate
    assert 0.10 < lead < 0.12
    a = np.abs(cut.samples.astype(np.int32)).max(axis=1)
    assert np.argmax(a > a.max() * 0.01) / pcm.sample_rate < 0.003
