"""Platform guards: every Windows-specific choice has a Mac equivalent.

Nothing in ``nightjar/`` reaches past :mod:`nightjar.util.host` for a
platform decision, and both platforms' equivalents resolve - the NVDA DLL has
its VoiceOver bridge, ``soft_oal.dll`` its ``libopenal.dylib``, the exe's
embedded pack a ``gamedata.pak`` in the .app, the Windows zip a Mac one.
"""

import ast
import os
import plistlib
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.util import host, paths                           # noqa: E402

VENDOR_OPENAL_WIN = os.path.join(ROOT, 'vendor', 'openal', 'soft_oal.dll')
VENDOR_OPENAL_MAC = os.path.join(ROOT, 'vendor', 'openal-mac', 'libopenal.dylib')
VENDOR_MAKEMHR_WIN = os.path.join(ROOT, 'vendor', 'makemhr', 'makemhr.exe')
VENDOR_MAKEMHR_MAC = os.path.join(ROOT, 'vendor', 'makemhr-mac', 'makemhr')
mac_only = pytest.mark.skipif(not host.MAC, reason='the Mac build')


# ------------------------------------------------------------ the platform
def test_the_platform_is_decided_once():
    assert host.PLATFORM in ('windows', 'mac', 'other')
    assert host.WINDOWS == (sys.platform == 'win32')
    assert host.MAC == (sys.platform == 'darwin')
    assert not (host.WINDOWS and host.MAC)


def test_speech_follows_the_platform():
    from nightjar.accessibility import speech
    backend = speech.create()
    try:
        if host.MAC:
            assert backend.name in ('voiceover', 'null'), backend.name
        elif host.WINDOWS:
            assert backend.name in ('nvda', 'sapi', 'null'), backend.name
    finally:
        backend.close()


def test_the_voiceover_bridge_is_there_on_the_mac_only():
    from nightjar.accessibility import voiceover
    assert voiceover.is_supported() == host.MAC
    if not host.MAC:
        assert voiceover.speak('no-op off the mac') is False


def test_windows_only_imports_never_load_at_import_time():
    """winreg sits behind a platform guard, inside the function that uses it."""
    for rel in ('nightjar/accessibility/speech.py', 'nightjar/util/sysaudio.py',
                'nightjar/util/host.py', 'nightjar/assets/pack.py',
                'nightjar/update/updater.py'):
        tree = ast.parse(open(os.path.join(ROOT, rel), encoding='utf-8').read())
        for node in tree.body:
            if isinstance(node, ast.Import):
                assert all(a.name != 'winreg' for a in node.names), rel
            elif isinstance(node, ast.ImportFrom):
                assert node.module != 'winreg', rel


def test_the_pause_menu_quits_to_the_platforms_desktop():
    from nightjar.shell.menu import pause_menu
    labels = [item.label for item in pause_menu().items]
    assert ('Quit to Windows' in labels) == host.WINDOWS
    assert ('Quit to the desktop' in labels) == (not host.WINDOWS)


# ---------------------------------------------------------------- libraries
def test_both_platforms_libraries_are_vendored():
    """The Mac OpenAL Soft and makemhr are committed beside the Windows ones."""
    for p in (VENDOR_OPENAL_WIN, VENDOR_OPENAL_MAC, VENDOR_MAKEMHR_WIN, VENDOR_MAKEMHR_MAC):
        assert os.path.exists(p), p


def test_the_openal_library_is_the_platforms_own():
    name = os.path.basename(paths.openal_dll())
    assert name == ('libopenal.dylib' if host.MAC else 'soft_oal.dll')
    assert os.path.exists(paths.openal_dll()), paths.openal_dll()


@mac_only
def test_the_mac_binaries_run_here():
    """Mach-O for this machine, and linked only against the system."""
    out = subprocess.run(['file', VENDOR_OPENAL_MAC, VENDOR_MAKEMHR_MAC],
                         capture_output=True, text=True).stdout
    assert out.count('Mach-O') == 2, out
    assert os.uname().machine in out, out
    links = subprocess.run(['otool', '-L', VENDOR_OPENAL_MAC],
                           capture_output=True, text=True).stdout.splitlines()[2:]
    for line in links:
        assert line.strip().startswith(('/usr/lib/', '/System/')), line
    assert os.access(VENDOR_MAKEMHR_MAC, os.X_OK)


# ------------------------------------------------------------ the data pack
def test_a_pack_beside_the_frozen_root_is_mapped_and_served(tmp_path):
    """The Mac's pack: gamedata.pak inside the bundle, not a resource in the exe."""
    from nightjar.assets import pack
    src = tmp_path / 'src'
    (src / 'Exports').mkdir(parents=True)
    (src / 'Exports' / 'level.json').write_bytes(b'{"a": 1}')
    (src / 'click_button.wav').write_bytes(b'RIFF' + bytes(range(256)))
    assert pack.write_pack(str(src), str(tmp_path / pack.FILE_NAME)) == 2
    root = str(tmp_path / 'gamedata')
    try:
        assert pack.auto_mount(root)
        assert pack.read_bytes(os.path.join(root, 'Exports', 'level.json')) == b'{"a": 1}'
        assert pack.read_bytes(os.path.join(root, 'click_button.wav')) == b'RIFF' + bytes(range(256))
        assert pack.isfile(os.path.join(root, 'exports', 'LEVEL.json'))
        assert pack.glob(os.path.join(root, 'Exports', '*.json')) == \
            [os.path.join(root, 'Exports', 'level.json')]
    finally:
        pack.mount(None, None)


# ------------------------------------------------------------------ updates
def _release(*names):
    from nightjar.update.updater import Release
    return Release({'tag_name': '2026-10-01', 'assets': [
        {'name': n, 'browser_download_url': 'https://example.invalid/' + n, 'size': 1}
        for n in names]})


def test_each_platform_downloads_its_own_zip():
    from nightjar.update import updater
    assert updater.ASSET_NAME == ('TheNightjar-Mac.zip' if host.MAC else 'TheNightjar-Windows.zip')
    both = _release('TheNightjar-Windows.zip', 'TheNightjar-Mac.zip')
    assert both.asset_name == updater.ASSET_NAME


def test_a_mac_never_takes_the_windows_zip():
    lone = _release('TheNightjar-Windows.zip')
    assert lone.asset_name == ('' if host.MAC else 'TheNightjar-Windows.zip')


def test_the_mac_looks_for_updates_but_never_installs_one(monkeypatch):
    from nightjar.update import updater
    monkeypatch.setattr(paths, 'FROZEN', True)
    allowed, why = updater.can_update()
    if host.MAC:
        assert not allowed and 'Mac zip' in why
        assert updater.check_only()
    else:
        assert not updater.check_only()
    monkeypatch.setattr(paths, 'FROZEN', False)
    assert not updater.check_only()


# ----------------------------------------------------------------- building
def test_the_build_uses_the_platforms_names():
    import tools.build_exes as be
    import tools.pack_release as pr
    assert be.SEP == (';' if host.WINDOWS else ':')
    assert be.GAME == pr.GAME == ('The Nightjar.app' if host.MAC else 'The Nightjar.exe')
    assert be.OPENAL == (VENDOR_OPENAL_MAC if host.MAC else VENDOR_OPENAL_WIN)
    assert be.MAKEMHR == (VENDOR_MAKEMHR_MAC if host.MAC else VENDOR_MAKEMHR_WIN)


def test_the_bundle_identifier_is_reverse_dns():
    import tools.build_exes as be
    parts = be.BUNDLE_ID.split('.')
    assert len(parts) >= 3 and all(p.isalnum() for p in parts), be.BUNDLE_ID


def test_the_bundle_version_is_the_day_in_dotted_numbers():
    import tools.build_exes as be
    assert be.bundle_version('2026-09-28') == ('2026.9.28', '2026.9.28')
    assert be.bundle_version('2026-09-28 number 2') == ('2026.9.28', '2026.9.28.2')


def test_pyobjc_is_declared_for_the_mac_only():
    toml = open(os.path.join(ROOT, 'pyproject.toml'), encoding='utf-8').read()
    assert "pyobjc-framework-cocoa>=12.2.2; sys_platform == 'darwin'" in toml


@mac_only
def test_finishing_the_bundle_stamps_it_and_leaves_it_signed(tmp_path):
    """PyInstaller signs before the version goes in; the build signs again."""
    import tools.build_exes as be
    bundle = tmp_path / 'The Nightjar.app'
    macos = bundle / 'Contents' / 'MacOS'
    macos.mkdir(parents=True)
    shutil.copy('/usr/bin/true', macos / 'The Nightjar')
    with open(bundle / 'Contents' / 'Info.plist', 'wb') as fh:
        plistlib.dump({'CFBundleExecutable': 'The Nightjar', 'CFBundlePackageType': 'APPL',
                       'CFBundleIdentifier': 'The Nightjar',
                       'CFBundleShortVersionString': '0.0.0'}, fh)
    subprocess.run(['codesign', '--force', '--sign', '-', str(bundle)], check=True,
                   capture_output=True)
    be.finalize_mac_app(str(bundle))
    with open(bundle / 'Contents' / 'Info.plist', 'rb') as fh:
        plist = plistlib.load(fh)
    assert plist['CFBundleIdentifier'] == be.BUNDLE_ID
    assert (plist['CFBundleShortVersionString'], plist['CFBundleVersion']) == be.bundle_version()
    subprocess.run(['codesign', '--verify', '--deep', '--strict', str(bundle)], check=True)
