"""Compact, readable dump of every level's objects and triggers.

    python tools/level_dump.py [N ...]      -> build/level_dump.txt (all levels)

Positions are Tiled's (x right, y down); the engine negates y.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app', 'Exports', 'The Nightjar')


def dump(n):
    d = json.load(open(os.path.join(EXPORTS, 'nightJar_%d.json' % n), encoding='utf-8'))
    out = ['=' * 70, 'nightJar_%d' % n]
    for layer in d['layers']:
        for o in layer.get('objects', []):
            p = dict(o.get('properties') or {})
            trig = {k: p.pop(k) for k in list(p) if k.startswith('On')}
            shape = ''
            if o.get('width') or o.get('height'):
                shape = ' rect %gx%g' % (o['width'], o['height'])
            if 'polyline' in o:
                shape = ' polyline ' + ' '.join('(%g,%g)' % (q['x'] + o['x'], q['y'] + o['y']) for q in o['polyline'])
            out.append('%-11s %-28s @(%g,%g)%s' % (o.get('type'), o.get('name') or '-', o['x'], o['y'], shape))
            if p:
                out.append('      ' + '  '.join('%s=%s' % kv for kv in sorted(p.items())))
            for k, v in trig.items():
                for i, stmt in enumerate(str(v).split('|')):
                    out.append('      %-14s %s' % (k if i == 0 else '', stmt))
    return out


def main():
    ns = [int(a) for a in sys.argv[1:]] or list(range(1, 15))
    lines = []
    for n in ns:
        lines += dump(n)
    if not sys.argv[1:]:
        open(os.path.join(ROOT, 'build', 'level_dump.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
