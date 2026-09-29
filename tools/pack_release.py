"""Zip up a release, for the platform doing the packing.

Takes ``Run/`` and makes the one archive that gets handed to someone else:
**the game, and nothing else** - ``The Nightjar.exe``, its ``_internal``
folder and ``changelog.txt`` on Windows, ``The Nightjar.app`` and
``changelog.txt`` on the Mac - inside one folder, "The Nightjar".
Diagnostic tools, config, recordings and save files all stay behind.

The Mac zip is made with ``ditto``, as Finder makes one: a .app is full of
symbolic links and carries a signature over all of it, and Python's zipfile
would store each link as a copy of what it points to, which breaks both.

    python tools/pack_release.py
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.util import host                                   # noqa: E402

RUN = os.path.join(ROOT, 'Run')
DIST = os.path.join(ROOT, 'dist')

GAME = 'The Nightjar.app' if host.MAC else 'The Nightjar.exe'

#: The release, in full.
ALWAYS = (GAME, 'changelog.txt') if host.MAC else (GAME, '_internal', 'changelog.txt')
#: The one folder the zip holds.
TOP = 'The Nightjar'

#: Never shipped: recordings, generated reports, and anybody's save file.
NEVER_SUFFIX = ('.wav', '.log')
NEVER_NAMES = ('progress.json', 'EIGC_Users.plist', 'selftest.txt', 'selftest-update.txt')


def wanted() -> list[tuple[str, str]]:
    """Return ``(absolute path, name inside the zip)`` pairs."""
    out: list[tuple[str, str]] = []
    for name in ALWAYS:
        path = os.path.join(RUN, name)
        if not os.path.exists(path):
            raise SystemExit(f'missing: {path}  (run tools/build_exes.py first)')
        out.append((path, name))
    return out


def check_for_local_paths(files: list[tuple[str, str]]) -> list[str]:
    """Refuse to ship a text file with this machine's paths baked into it.

    The specific thing this exists to catch is ``alsoft.ini``, whose absolute
    ``hrtf-paths`` would send every other machine looking for a directory that
    is not there.  Cheap to run over anything shipped as text.
    """
    home = os.path.expanduser('~')
    needles = [home, ROOT]
    bad = []
    for path, name in files:
        if os.path.splitext(name)[1].lower() not in (
                '.txt', '.ini', '.json', '.cfg', '.md'):
            continue
        try:
            with open(path, encoding='utf-8', errors='replace') as fh:
                body = fh.read()
        except OSError:
            continue
        for needle in needles:
            if needle and needle.lower() in body.lower():
                bad.append(f'{name} contains {needle}')
    return bad


def version() -> str:
    path = os.path.join(ROOT, 'VERSION')
    try:
        with open(path, encoding='utf-8') as fh:
            return fh.read().strip() or '0.0.0'
    except OSError:
        return '0.0.0'


def main(argv: list[str]) -> int:
    files = wanted()

    leaks = check_for_local_paths(files)
    if leaks:
        print('REFUSING to pack - this machine\'s paths are in:')
        for line in leaks:
            print(f'  {line}')
        return 1

    os.makedirs(DIST, exist_ok=True)
    from nightjar.update import updater, version as build_version
    # one name for every release, so .../releases/latest/download/<name> is
    # a link that never changes (the version is in the tag and the changelog)
    out = os.path.join(DIST, updater.ASSET_NAME)
    print(f'version {build_version.text(version())}, tag {build_version.tag(version())}')

    def _tree(root: str):
        """Every file under root, as (absolute, arcname) pairs."""
        for dp, _d, fs in os.walk(root):
            for f in sorted(fs):
                full = os.path.join(dp, f)
                yield full, os.path.relpath(full, RUN)

    if host.MAC:
        return _zip_mac(files, out)

    total = 0
    count = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED,
                         compresslevel=6) as zf:
        for path, name in files:
            members = _tree(path) if os.path.isdir(path) else [(path, name)]
            for full, arcname in members:
                if os.path.splitext(arcname)[1].lower() in NEVER_SUFFIX:
                    continue
                if os.path.basename(arcname) in NEVER_NAMES:
                    continue
                zf.write(full, TOP + '/' + arcname.replace(os.sep, '/'))
                total += os.path.getsize(full)
                count += 1

    return _report(out, count, total)


def _zip_mac(files: list[tuple[str, str]], out: str) -> int:
    """The bundle and the changelog in a "The Nightjar" folder, zipped by ditto."""
    stage = os.path.join(ROOT, 'build', 'release', TOP)
    shutil.rmtree(os.path.dirname(stage), ignore_errors=True)
    os.makedirs(stage)
    for path, name in files:
        if os.path.isdir(path):
            shutil.copytree(path, os.path.join(stage, name), symlinks=True)
        else:
            shutil.copy2(path, os.path.join(stage, name))
    for dp, _d, fs in os.walk(stage):
        for f in fs:
            if (os.path.splitext(f)[1].lower() in NEVER_SUFFIX or f in NEVER_NAMES) \
                    and not os.path.islink(os.path.join(dp, f)):
                raise SystemExit(f'refusing to ship {os.path.join(dp, f)}')
    subprocess.run(['codesign', '--verify', '--deep', '--strict', os.path.join(stage, GAME)],
                   check=True)
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(['ditto', '-c', '-k', '--sequesterRsrc', '--keepParent', stage, out],
                   check=True)
    files_in = [os.path.join(dp, f) for dp, _d, fs in os.walk(stage) for f in fs]
    total = sum(os.lstat(f).st_size for f in files_in)
    return _report(out, len(files_in), total)


def _report(out: str, count: int, total: int) -> int:
    packed = os.path.getsize(out)
    digest = hashlib.sha256(open(out, 'rb').read()).hexdigest()
    print(f'\n{out}')
    print(f'  {count} files, {total / 1e6:.0f} MB in, '
          f'{packed / 1e6:.0f} MB packed')
    print(f'  sha256 {digest}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
