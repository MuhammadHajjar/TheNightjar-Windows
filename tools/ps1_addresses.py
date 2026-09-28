"""Find Papa Sangre 1 binary addresses left in code carried over from the PS1 port.

The Nightjar binary is the PS1 binary with every function 0x10 later (checked
class by class: the code is instruction-identical once addresses are
normalised).  A comment address copied from the PS1 port therefore points 16
bytes early.  For each address in a file this prints what the Nightjar binary
has at it and at +0x10, and guesses which one the comment means from the words
around it (selectors, strings, ivars, constants).

    python tools/ps1_addresses.py nightjar/entities/monster.py [--fix]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIS = os.path.join(ROOT, 'tools', 'dis', 'all.txt')
SHIFT = 0x10


def load():
    ins, starts = {}, set()
    for line in open(DIS, encoding='utf-8', errors='replace'):
        m = re.match(r'^(0x[0-9a-f]{9})  (.*)$', line)
        if m:
            ins[int(m.group(1), 16)] = m.group(2)
            continue
        m = re.match(r'^===== .*\((0x[0-9a-f]+)\) =====', line)
        if m:
            starts.add(int(m.group(1), 16))
    return ins, starts


def words(text):
    return {w.lower() for w in re.findall(r'[A-Za-z_][A-Za-z0-9_:]{2,}|#?0x[0-9a-f]+|\d+\.\d+', text)}


def main():
    path = sys.argv[1]
    fix = '--fix' in sys.argv
    ins, starts = load()
    src = open(path, encoding='utf-8').read()
    out = []
    changes = {}
    for m in re.finditer(r'0x1000[0-9a-f]{5}', src):
        a = int(m.group(0), 16)
        lo = src.rfind('\n', 0, m.start()) + 1
        hi = src.find('\n', m.end())
        ctx = src[max(0, lo - 200):hi + 200]
        here, there = ins.get(a, ''), ins.get(a + SHIFT, '')
        cw = words(ctx)
        s_here = len(cw & words(here.split(';', 1)[-1])) + (3 if a in starts else 0)
        s_there = len(cw & words(there.split(';', 1)[-1])) + (3 if a + SHIFT in starts else 0)
        verdict = 'nj' if s_here > s_there else 'ps1' if s_there > s_here else '?'
        out.append((m.group(0), verdict, s_here, s_there, here[:60], there[:60]))
        if verdict == 'ps1':
            changes[m.group(0)] = f'0x{a + SHIFT:09x}'
    for row in out:
        print('%s %-3s %d/%d  nj: %-60s | +0x10: %s' % row)
    print(f'{len(out)} addresses: {sum(r[1]=="nj" for r in out)} nj, '
          f'{sum(r[1]=="ps1" for r in out)} ps1, {sum(r[1]=="?" for r in out)} unclear')
    if fix and changes:
        # only whole tokens, and only the ones judged PS1
        new = re.sub(r'0x1000[0-9a-f]{5}',
                     lambda mm: changes.get(mm.group(0), mm.group(0)), src)
        open(path, 'w', encoding='utf-8').write(new)
        print('fixed', len(changes))


if __name__ == '__main__':
    main()
