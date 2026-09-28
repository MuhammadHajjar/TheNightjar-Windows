"""Build the game as a double-clickable exe.

The game is a folder build: ``The Nightjar.exe`` with its libraries in
``_internal`` beside it, so nothing is unpacked to a temporary folder at each
start, and all the game data - levels, playlists, sounds - in one encrypted
pack embedded in the exe as a Windows resource (``nightjar/assets/pack.py``).
It goes into ``Run/`` as the exe and its ``_internal`` folder, next to the
player's ``config``, which is never touched.

Only what this app loads is packed: the 14 Nightjar levels and their hub list,
the playlists those levels use (with their footstep includes), the sounds
those playlists declare, and the UI sounds the buttons and splash play.  The
Papa Sangre maps and playlists the original carries, the artwork, and the
third-party credentials file stay out.

Run:  python tools/build_exes.py
      NJ_DIST=<folder> to build somewhere else while the game in Run is open
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

APPS = os.path.join(ROOT, 'apps')
#: Where the game goes.  NJ_DIST puts it elsewhere - for building while the
#: game in Run is being played (Windows will not replace a running exe).
RUN = os.environ.get('NJ_DIST') or os.path.join(ROOT, 'Run')
WORK = os.path.join(ROOT, 'build', 'pyinstaller')
BUNDLE = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app')
HRTF_DIR = os.path.join(ROOT, 'build', 'hrtf')
HRTF = os.path.join(HRTF_DIR, 'papa_ircam_1050.mhr')
OPENAL = os.path.join(ROOT, 'vendor', 'openal', 'soft_oal.dll')
MAKEMHR = os.path.join(ROOT, 'vendor', 'makemhr', 'makemhr.exe')
NVDA_DIR = os.path.join(ROOT, 'vendor', 'nvda')

GAME_NAME = 'The Nightjar'
PACK = os.path.join(ROOT, 'build', 'gamedata.pak')
GAME_DIST = os.path.join(ROOT, 'build', 'dist_game')
CHANGELOG = os.path.join(ROOT, 'changelog.txt')
#: The files the original's buttons and splash play (playUiSoundWithName:).
UI_FILES = ('click_button.wav', 'back_button.wav', 'start_button.wav', 'whoosh Med.wav')
NEVER = ('EIGC_Users.plist',)


def prepare_hrtf() -> str:
    """The built HRTF, made from the committed ``tools/embedded_hrtf.dat`` (the
    IRCAM 1050 set in the binary) by ``tools/extract_hrtf.py`` and makemhr."""
    if os.path.exists(HRTF):
        return HRTF
    os.makedirs(HRTF_DIR, exist_ok=True)
    print('    building HRTF (first build on this machine)...')
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'extract_hrtf.py')],
                   cwd=ROOT, check=True)
    # -e off: no diffuse-field equalisation - the original convolves the raw
    # IRCAM responses.
    subprocess.run([MAKEMHR, '-i', os.path.join(HRTF_DIR, 'papa_ircam_1050.def'),
                    '-o', HRTF, '-e', 'off'], cwd=HRTF_DIR, check=True)
    if not os.path.exists(HRTF):
        raise SystemExit(f'makemhr did not produce {HRTF}')
    return HRTF


def needed_files() -> list[str]:
    """Bundle-relative paths of everything the game loads."""
    from nightjar.assets.audit import LEVELS, _flatten, _read_playlists  # noqa: PLC0415
    pls = _read_playlists(BUNDLE)
    out = ['Exports/The Nightjar_hubList.plist']
    out += [f'Exports/The Nightjar/{lv}.json' for lv in LEVELS]
    stems = set()
    for lv in LEVELS:
        seen: set = set()
        _flatten(pls, lv, seen)
        stems |= seen
        for decl in _flatten(pls, lv).values():
            out.append(decl.bundle_path)
    meta = os.path.join(BUNDLE, 'meta', 'S3DPlayListModel')
    for f in os.listdir(meta):
        if f.split('.S3DPlayListModel')[0] in stems:
            out.append('meta/S3DPlayListModel/' + f)
    # lines the port declares for a level its playlist does not (decisions 2, 5)
    from nightjar.world.requested import ENSURE, PROMPTS            # noqa: PLC0415
    out += [f'{PROMPTS}/{n}.m4a' for names in ENSURE.values() for n in names]
    out += list(UI_FILES)
    out.append('nightjar_sounds/splash/papa_engine_splash.wav')
    return sorted(set(out))


def prepare_game_data() -> None:
    staging = os.path.join(ROOT, 'build', 'gamedata')
    if os.path.isdir(staging):
        shutil.rmtree(staging)
    for rel in needed_files():
        if os.path.basename(rel) in NEVER:
            raise SystemExit(f'refusing to pack {rel}')
        src = os.path.join(BUNDLE, *rel.split('/'))
        dst = os.path.join(staging, *rel.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    size = sum(os.path.getsize(os.path.join(dp, f))
               for dp, _d, fs in os.walk(staging) for f in fs)
    print(f'    staged the game data, {size / 1e6:.0f} MB')
    from nightjar.assets.pack import write_pack                  # noqa: PLC0415
    n = write_pack(staging, PACK)
    print(f'    packed and encrypted {n} files, {os.path.getsize(PACK) / 1e6:.0f} MB')


def build() -> str:
    prepare_game_data()
    hrtf = prepare_hrtf()
    data: list[tuple[str, str]] = [(hrtf, 'hrtf')]
    for name in ('nvdaControllerClient64.dll', 'nvdaControllerClient32.dll'):
        p = os.path.join(NVDA_DIR, name)
        if os.path.exists(p):
            data.append((p, 'nvda'))
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--noconfirm', '--clean', '--onedir', '--windowed',
        '--name', GAME_NAME,
        '--distpath', GAME_DIST,
        '--workpath', WORK,
        '--specpath', WORK,
        '--add-binary', f'{OPENAL};.',
        '--hidden-import', 'nightjar',
        '--paths', ROOT,
    ]
    for src, dest in data:
        cmd += ['--add-data', f'{src};{dest}']
    from nightjar.assets.pack import RESOURCE_NAME, RESOURCE_TYPE  # noqa: PLC0415
    cmd += ['--resource', f'{PACK},{RESOURCE_TYPE},{RESOURCE_NAME},0']
    cmd.append(os.path.join(APPS, 'play.py'))
    print(f'\n=== building {GAME_NAME}.exe ===', flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout[-4000:])
        sys.stderr.write(proc.stderr[-4000:])
        raise SystemExit('PyInstaller failed')
    shutil.copy2(CHANGELOG, os.path.join(GAME_DIST, GAME_NAME, 'changelog.txt'))
    out = install_game()
    print(f'    {out}  ({os.path.getsize(out) / 1e6:.0f} MB, {time.perf_counter() - t0:.0f}s)')
    return out


def install_game() -> str:
    """Put the folder build into RUN: the exe and its _internal folder, next to
    whatever is there (the player's config stays)."""
    built = os.path.join(GAME_DIST, GAME_NAME)
    exe = os.path.join(RUN, GAME_NAME + '.exe')
    internal = os.path.join(RUN, '_internal')
    os.makedirs(RUN, exist_ok=True)
    try:
        if os.path.exists(exe):
            os.replace(exe, exe + '.old')             # fails at once if it is running
    except OSError:
        raise SystemExit(f'{exe} is running - close the game and build again '
                         f'(or set NJ_DIST to build elsewhere)')
    if os.path.isdir(internal):
        shutil.rmtree(internal)
    shutil.copytree(os.path.join(built, '_internal'), internal)
    shutil.copy2(os.path.join(built, GAME_NAME + '.exe'), exe)
    shutil.copy2(os.path.join(built, 'changelog.txt'), os.path.join(RUN, 'changelog.txt'))
    if os.path.exists(exe + '.old'):
        os.remove(exe + '.old')
    return exe


if __name__ == '__main__':
    build()
