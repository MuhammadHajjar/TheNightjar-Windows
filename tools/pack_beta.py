"""Zip the game for someone else: the private beta in the Drive folder.

Takes ``Run/`` and makes the one archive that gets handed over: **the game,
and nothing else** - ``The Nightjar.exe``, its ``_internal`` folder and
``changelog.txt``, inside one folder, "The Nightjar".  The player's config
(progress, settings, keys), test output and the third-party credentials file
stay behind; the zip is checked for them after it is written.

    python tools/pack_beta.py [destination folder]
"""

from __future__ import annotations

import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

RUN = os.path.join(ROOT, 'Run')
DIST = os.path.join(ROOT, 'dist')
GAME = 'The Nightjar.exe'
ALWAYS = (GAME, '_internal', 'changelog.txt')
TOP = 'The Nightjar'
#: Never shipped, wherever they turn up.
NEVER_NAMES = ('EIGC_Users.plist', 'progress.json', 'progress.json.bak', 'settings.json',
               'keys.json', 'controller.json', 'selftest.txt', 'master_volume.json')
NEVER_DIRS = ('config',)


def files() -> list[tuple[str, str]]:
    out = []
    for name in ALWAYS:
        path = os.path.join(RUN, name)
        if not os.path.exists(path):
            raise SystemExit(f'missing: {path}  (run tools/build_exes.py first)')
        if os.path.isdir(path):
            for dp, _d, fs in os.walk(path):
                for f in fs:
                    p = os.path.join(dp, f)
                    out.append((p, os.path.join(TOP, os.path.relpath(p, RUN))))
        else:
            out.append((path, os.path.join(TOP, name)))
    return out


def main() -> str:
    from nightjar import __version__                             # noqa: PLC0415
    dest = sys.argv[1] if len(sys.argv) > 1 else DIST
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, f'The Nightjar - private beta ({__version__}).zip')
    items = files()
    with zipfile.ZipFile(out + '.part', 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path, arc in items:
            z.write(path, arc)
    with zipfile.ZipFile(out + '.part') as z:
        names = z.namelist()
        bad = [n for n in names
               if os.path.basename(n) in NEVER_NAMES
               or any(part in NEVER_DIRS for part in n.replace(chr(92), '/').split('/')[1:-1])]
        if bad:
            os.remove(out + '.part')
            raise SystemExit(f'refusing: {bad}')
        if z.testzip() is not None:
            raise SystemExit('the zip does not read back')
    os.replace(out + '.part', out)
    print(f'{out}  ({os.path.getsize(out) / 1e6:.0f} MB, {len(names)} files)')
    return out


if __name__ == '__main__':
    main()
