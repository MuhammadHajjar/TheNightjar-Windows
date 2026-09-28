"""Sound and playlist inventory for The Nightjar (M0).

    python tools/inventory.py        -> build/inventory.txt, build/inventory.json

For each of the 14 levels: the playlist the engine loads for it (the level's
own playlist plus everything it includes), and whether every declaration
resolves to a shipped file (exactly, and ignoring case - iOS devices are
case-sensitive, so a case-only mismatch was silent on a phone).  Then every
audio file in nightjar_sounds/ and the bundle root, with the levels that can
play it, so the unreferenced ones stand out.
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), 'PapaSangre'))
from papasangre.assets.sexp import parse_playlist, include_stem  # noqa: E402

APP = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app')
META = os.path.join(APP, 'meta', 'S3DPlayListModel')
EXPORTS = os.path.join(APP, 'Exports', 'The Nightjar')
LEVELS = ['nightJar_%d' % i for i in range(1, 15)]


def playlists():
    out = {}
    for f in os.listdir(META):
        if f.endswith('.sexp'):
            out[f.split('.S3DPlayListModel')[0]] = parse_playlist(
                open(os.path.join(META, f), encoding='utf-8', errors='replace').read(), f)
    return out


def flatten(pls, stem, seen=None, chain=()):
    seen = set() if seen is None else seen
    if stem in seen or stem not in pls:
        return {}, ([stem] if stem not in pls else [])
    seen.add(stem)
    out, missing = {}, []
    for s in pls[stem].sounds:
        out.setdefault(s.name, (s, stem))
    for inc in pls[stem].includes:
        o, m = flatten(pls, include_stem(inc), seen)
        for k, v in o.items():
            out.setdefault(k, v)
        missing += m
    return out, missing


def files():
    idx = {}
    for dp, _d, fs in os.walk(APP):
        for f in fs:
            if f.lower().endswith(('.m4a', '.wav', '.mp3', '.caf', '.aif', '.aiff', '.m4v')):
                rel = os.path.relpath(os.path.join(dp, f), APP).replace(os.sep, '/')
                idx[rel] = os.path.getsize(os.path.join(dp, f))
    return idx


def duration(path):
    try:
        import av
        with av.open(path) as c:
            return round(float(c.duration or 0) / 1e6, 2)
    except Exception:                                  # noqa: BLE001
        return None


def main():
    pls = playlists()
    idx = files()
    lower = {k.lower(): k for k in idx}
    used_by = collections.defaultdict(set)
    report = []
    w = report.append
    data = {'levels': {}, 'files': {}}
    for lv in LEVELS:
        flat, missing_pl = flatten(pls, lv)
        incs = sorted({src for _s, src in flat.values()} - {lv})
        bad, case = [], []
        for name, (s, src) in sorted(flat.items()):
            rel = s.bundle_path if hasattr(s, 'bundle_path') else '%s/%s.%s' % (s.path, s.name, s.extension)
            if rel in idx:
                used_by[rel].add(lv)
            elif rel.lower() in lower:
                case.append('%s (file is %s)' % (rel, lower[rel.lower()]))
                used_by[lower[rel.lower()]].add(lv + '(case)')
            else:
                bad.append('%s [from %s]' % (rel, src))
        w('%s: %d sounds declared (own %d), includes %s' % (lv, len(flat), len(pls[lv].sounds), ', '.join(incs) or '-'))
        for b in bad:
            w('    MISSING FILE  ' + b)
        for c in case:
            w('    CASE ONLY     ' + c)
        for m in missing_pl:
            w('    MISSING PLAYLIST ' + m)
        data['levels'][lv] = dict(declared=len(flat), includes=incs, missing=bad, case_only=case)
    # every audio file
    w('\n# Files')
    unref = []
    tot = collections.Counter()
    for rel in sorted(idx):
        d = duration(os.path.join(APP, rel))
        users = sorted(used_by.get(rel, ()))
        data['files'][rel] = dict(bytes=idx[rel], seconds=d, levels=users)
        top = rel.split('/')[0] if '/' in rel else '(root)'
        if rel.startswith('nightjar_sounds/'):
            top = '/'.join(rel.split('/')[:2])
        tot[top] += 1
        if not users:
            unref.append('%s  %.1fs' % (rel, d or 0))
    w('files by folder: ' + ', '.join('%s %d' % kv for kv in sorted(tot.items())))
    w('\n# Audio files no Nightjar level playlist declares (%d)' % len(unref))
    report += ['    ' + u for u in unref]
    out = os.path.join(ROOT, 'build', 'inventory.txt')
    open(out, 'w', encoding='utf-8').write('\n'.join(report) + '\n')
    json.dump(data, open(os.path.join(ROOT, 'build', 'inventory.json'), 'w', encoding='utf-8'), indent=1)
    print('\n'.join(report))


if __name__ == '__main__':
    main()
