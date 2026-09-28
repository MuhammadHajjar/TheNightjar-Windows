"""Survey the level data: object types, properties, triggers and messages.

    python tools/level_survey.py            -> build/level_survey.txt

Compares what The Nightjar's 14 levels use against what Papa Sangre 1's levels
use (the same engine binary, and the levels the PS1 port was built and tested
against).  Anything The Nightjar uses that PS1's levels never did is engine code
the PS1 port may never have exercised - each one must be read in the binary.
"""
import collections
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKS = os.path.dirname(ROOT)
NJ = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app', 'Exports', 'The Nightjar')
PS1 = os.path.join(WORKS, 'PapaSangre', 'reference', 'Payload', 'Papa Sangre.app', 'Exports', 'Papa Sangre')
PS2 = os.path.join(WORKS, 'PapaSangre2', 'reference', 'Payload', 'Papa Sangre II.app', 'levels')


def survey(folder, pattern='*.json'):
    s = dict(types=collections.Counter(), props=collections.defaultdict(collections.Counter),
             msgs=collections.Counter(), msg_params=collections.defaultdict(collections.Counter),
             trig=collections.Counter(), layers=collections.Counter(), where=collections.defaultdict(set),
             values=collections.defaultdict(collections.Counter))
    for fp in sorted(glob.glob(os.path.join(folder, pattern))):
        stem = os.path.basename(fp)[:-5]
        d = json.load(open(fp, encoding='utf-8'))
        for k in (d.get('properties') or {}):
            s['props']['(map)'][k] += 1
        for layer in d['layers']:
            s['layers'][layer['name']] += 1
            if layer['name'] == 'ToolBar':
                continue
            for o in layer.get('objects', []):
                t = o.get('type') or '(none)'
                s['types'][t] += 1
                s['where']['type ' + t].add(stem)
                shape = ('polyline' if 'polyline' in o else 'polygon' if 'polygon' in o
                         else 'rect' if (o.get('width') or o.get('height')) else 'point')
                s['props'][t]['<' + shape + '>'] += 1
                for k, v in (o.get('properties') or {}).items():
                    s['props'][t][k] += 1
                    s['where']['prop %s.%s' % (t, k)].add(stem)
                    if not k.startswith('On') and len(str(v)) < 40:
                        s['values']['%s.%s' % (t, k)][str(v)] += 1
                    if k.startswith('On'):
                        s['trig'][k] += 1
                        s['where']['trig ' + k].add(stem)
                        for stmt in str(v).split('|'):
                            stmt = stmt.strip()
                            if not stmt:
                                continue
                            name = stmt.split(':', 1)[0].strip()
                            s['msgs'][name] += 1
                            s['where']['msg ' + name].add(stem)
                            if ':' in stmt:
                                for pair in stmt.split(':', 1)[1].split(';'):
                                    s['msg_params'][name][pair.split('=', 1)[0].strip()] += 1
    return s


def lv(stems):
    nums = [x.replace('nightJar_', '') for x in stems]
    return ','.join(sorted(nums, key=lambda x: int(x) if x.isdigit() else 99))


def main():
    nj, ps1 = survey(NJ), survey(PS1)
    ps2 = survey(PS2) if os.path.isdir(PS2) else None
    out = []
    w = out.append
    w('# Level survey - The Nightjar (14 levels) vs Papa Sangre 1 levels\n')
    w('## Layers\n' + '\n'.join('  %-24s %d' % kv for kv in nj['layers'].most_common()))
    w('\n## Object types (NJ count / PS1 count)')
    for t in sorted(set(nj['types']) | set(ps1['types'])):
        w('  %-20s NJ %4d  PS1 %4d  %s' % (t, nj['types'][t], ps1['types'][t],
                                          'NJ ONLY' if not ps1['types'][t] else ''))
    w('\n## Properties per type used by NJ (PS1 count; NEW = never in PS1 levels)')
    for t in sorted(nj['props']):
        w('  [%s]' % t)
        for k, n in sorted(nj['props'][t].items()):
            p = ps1['props'][t][k]
            vals = nj['values'].get('%s.%s' % (t, k))
            vs = ''
            if vals and len(vals) <= 8:
                vs = '  values: ' + ', '.join('%s x%d' % kv for kv in vals.most_common())
            w('    %-26s NJ %3d  PS1 %4d %s%s  levels: %s' % (
                k, n, p, ' NEW' if not p else '', vs,
                lv(nj['where']['prop %s.%s' % (t, k)])))
    w('\n## Triggers')
    for k, n in sorted(nj['trig'].items()):
        w('  %-20s NJ %3d  PS1 %4d%s' % (k, n, ps1['trig'][k], ' NEW' if not ps1['trig'][k] else ''))
    w('\n## Messages (with parameters)')
    for k, n in sorted(nj['msgs'].items()):
        new = '' if ps1['msgs'][k] else (' NEW (PS2 levels: %d)' % ps2['msgs'][k] if ps2 else ' NEW')
        params = ', '.join('%s x%d' % kv for kv in sorted(nj['msg_params'][k].items()))
        newp = [p for p in nj['msg_params'][k] if not ps1['msg_params'][k][p]]
        w('  %-36s NJ %3d  PS1 %4d%s  params: %s%s' % (k, n, ps1['msgs'][k], new, params,
                                                      ('  NEW PARAMS: ' + ','.join(newp)) if newp and not new else ''))
        w('      levels: ' + lv(nj['where']['msg ' + k]))
    path = os.path.join(ROOT, 'build', 'level_survey.txt')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
