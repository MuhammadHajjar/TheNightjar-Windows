"""Build the game as a double-clickable program, for the platform it runs on.

=======  =================================================================
Windows  ``The Nightjar.exe`` with its libraries in ``_internal`` beside it,
         and the game data embedded in the exe as a Windows resource.
Mac      ``The Nightjar.app``, a bundle like any other Mac app, with the game
         data inside it as ``gamedata.pak``.  Speech is VoiceOver, part of
         macOS, so there is no NVDA client to carry.
=======  =================================================================

Both are folder builds (PyInstaller one-dir), so nothing is unpacked to a
temporary folder at each start, and all the game data - levels, playlists,
sounds - is one encrypted pack (``nightjar/assets/pack.py``).  It goes into
``Run/`` with ``changelog.txt``, next to the player's ``config``, which is
never touched.

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
import plistlib
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.util import host                                   # noqa: E402

APPS = os.path.join(ROOT, 'apps')
#: Where the game goes.  NJ_DIST puts it elsewhere - for building while the
#: game in Run is being played (Windows will not replace a running exe).
RUN = os.environ.get('NJ_DIST') or os.path.join(ROOT, 'Run')
WORK = os.path.join(ROOT, 'build', 'pyinstaller')
BUNDLE = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app')
HRTF_DIR = os.path.join(ROOT, 'build', 'hrtf')
HRTF = os.path.join(HRTF_DIR, 'papa_ircam_1050.mhr')
NVDA_DIR = os.path.join(ROOT, 'vendor', 'nvda')

#: The same OpenAL Soft on both, built for each platform.
OPENAL = (os.path.join(ROOT, 'vendor', 'openal-mac', 'libopenal.dylib') if host.MAC
          else os.path.join(ROOT, 'vendor', 'openal', 'soft_oal.dll'))
MAKEMHR = (os.path.join(ROOT, 'vendor', 'makemhr-mac', 'makemhr') if host.MAC
           else os.path.join(ROOT, 'vendor', 'makemhr', 'makemhr.exe'))
#: PyInstaller's src;dest separator: ';' on Windows, ':' everywhere else.
SEP = ';' if host.WINDOWS else ':'

GAME_NAME = 'The Nightjar'
#: What the player double-clicks, in Run/ and in the release zip.
GAME = GAME_NAME + ('.app' if host.MAC else '.exe')
#: The Mac bundle's reverse-DNS identity.  PyInstaller's default is the bare
#: app name, space and all; LaunchServices and Spotlight key on this.
BUNDLE_ID = 'com.thenightjar.port'
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
    if not os.path.exists(MAKEMHR):
        raise SystemExit(f'missing makemhr: {MAKEMHR}\n'
                         'Mac: build it with tools/build_openal_mac.sh')
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
    if not os.path.exists(OPENAL):
        raise SystemExit(f'missing OpenAL Soft: {OPENAL}\n'
                         'Mac: build it with tools/build_openal_mac.sh')
    prepare_game_data()
    hrtf = prepare_hrtf()
    data: list[tuple[str, str]] = [(hrtf, 'hrtf')]
    if host.WINDOWS:
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
        '--add-binary', f'{OPENAL}{SEP}.',
        '--hidden-import', 'nightjar',
        '--paths', ROOT,
    ]
    if host.WINDOWS:
        from nightjar.assets.pack import RESOURCE_NAME, RESOURCE_TYPE  # noqa: PLC0415
        cmd += ['--resource', f'{PACK},{RESOURCE_TYPE},{RESOURCE_NAME},0']
    else:
        # No resources in a Mach-O: the pack sits inside the bundle, where
        # pack.auto_mount finds it beside the frozen root.
        data.append((PACK, '.'))
    if host.MAC:
        # pyobjc loads its frameworks lazily enough that the analyser cannot
        # always see them; the VoiceOver bridge needs both in the build.
        cmd += ['--osx-bundle-identifier', BUNDLE_ID,
                '--hidden-import', 'Foundation', '--hidden-import', 'AppKit']
    for src, dest in data:
        cmd += ['--add-data', f'{src}{SEP}{dest}']
    cmd.append(os.path.join(APPS, 'play.py'))
    print(f'\n=== building {GAME} ===', flush=True)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout[-4000:])
        sys.stderr.write(proc.stderr[-4000:])
        raise SystemExit('PyInstaller failed')
    if host.MAC:
        finalize_mac_app(os.path.join(GAME_DIST, GAME))
        out = install_mac_app()
    else:
        shutil.copy2(CHANGELOG, os.path.join(GAME_DIST, GAME_NAME, 'changelog.txt'))
        out = install_game()
    size = (sum(os.lstat(os.path.join(dp, f)).st_size for dp, _d, fs in os.walk(out) for f in fs)
            if os.path.isdir(out) else os.path.getsize(out))
    print(f'    {out}  ({size / 1e6:.0f} MB, {time.perf_counter() - t0:.0f}s)')
    return out


def install_game() -> str:
    """Put the folder build into RUN: the exe and its _internal folder, next to
    whatever is there (the player's config stays)."""
    built = os.path.join(GAME_DIST, GAME_NAME)
    exe = os.path.join(RUN, GAME)
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
    shutil.copy2(os.path.join(built, GAME), exe)
    shutil.copy2(os.path.join(built, 'changelog.txt'), os.path.join(RUN, 'changelog.txt'))
    if os.path.exists(exe + '.old'):
        os.remove(exe + '.old')
    return exe


# ------------------------------------------------------------------ the Mac
def bundle_version(text: str | None = None) -> tuple[str, str]:
    """(CFBundleShortVersionString, CFBundleVersion) for a version.

    The port's version is a day, '2026-09-28 number 2'; a bundle's is dotted
    numbers, so that is '2026.9.28' and '2026.9.28.2'.
    """
    from nightjar.update import version                          # noqa: PLC0415
    parts = version.parse(version.current() if text is None else text) or (0, 0, 0)
    return '.'.join(map(str, parts[:3])), '.'.join(map(str, parts))


def finalize_mac_app(bundle: str) -> None:
    """Stamp the version and the VoiceOver prompt into the bundle and sign it again.

    PyInstaller writes 0.0.0 for the version.  Changing Info.plist after it
    has signed the bundle breaks the signature ('invalid Info.plist'), which
    Apple silicon refuses to run, so the bundle is signed again - ad hoc, as
    PyInstaller signed it.
    """
    info = os.path.join(bundle, 'Contents', 'Info.plist')
    if not os.path.isfile(info):
        raise SystemExit(f'not a .app bundle: {bundle}')
    with open(info, 'rb') as fh:
        plist = plistlib.load(fh)
    short, full = bundle_version()
    plist['CFBundleIdentifier'] = BUNDLE_ID
    plist['CFBundleShortVersionString'] = short
    plist['CFBundleVersion'] = full
    plist['LSApplicationCategoryType'] = 'public.app-category.games'
    # what macOS says when it asks to let the game drive VoiceOver
    plist['NSAppleEventsUsageDescription'] = 'The Nightjar speaks its menus through VoiceOver.'
    with open(info, 'wb') as fh:
        plistlib.dump(plist, fh, sort_keys=True)
    subprocess.run(['codesign', '--force', '--sign', '-', bundle],
                   check=True, capture_output=True)
    subprocess.run(['codesign', '--verify', '--deep', '--strict', bundle],
                   check=True, capture_output=True)


def install_mac_app() -> str:
    """Put the bundle into RUN, replacing the last one, with the changelog
    beside it (the player's config is in Application Support, not here)."""
    app = os.path.join(RUN, GAME)
    os.makedirs(RUN, exist_ok=True)
    if os.path.isdir(app):
        shutil.rmtree(app)
    shutil.copytree(os.path.join(GAME_DIST, GAME), app, symlinks=True)
    shutil.copy2(CHANGELOG, os.path.join(RUN, 'changelog.txt'))
    return app


if __name__ == '__main__':
    build()
