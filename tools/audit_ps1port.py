"""Run the Papa Sangre 1 port's content audit over The Nightjar's data (M0 only).

The two games share one engine binary, so the PS1 port's audit - its known
properties, message vocabulary, trigger parser and sound resolution - applies
unchanged.  Only the data paths are swapped.  Nothing is written into the PS1
port's folder: the checklist goes to build/.

    python tools/audit_ps1port.py      -> build/audit_ps1port.txt, build/CONTENT_INVENTORY.md
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS1 = os.path.join(os.path.dirname(ROOT), 'PapaSangre')
sys.path.insert(0, PS1)

from papasangre.assets import audit  # noqa: E402

APP = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app')
audit.BUNDLE = APP
audit.EXPORTS = os.path.join(APP, 'Exports', 'The Nightjar')
audit.META = os.path.join(APP, 'meta', 'S3DPlayListModel')
audit.DOCS = os.path.join(ROOT, 'build')
audit.LEVEL_ORDER = ['nightJar_%d' % i for i in range(1, 15)]
_plist = os.path.join(APP, 'Exports', 'The Nightjar_hubList.plist')


def _hub():
    import plistlib
    with open(_plist, 'rb') as fh:
        return plistlib.load(fh)


audit.hub_list = _hub
# vocabulary: this binary's own string table (the PS1 one is identical, but use ours)
_strings = os.path.join(ROOT, 'build', 'nj_strings.txt')
_orig_known = audit.known_messages


def _known():
    import re
    return set(re.findall(r'PGE_MESSAGE_[A-Za-z]+', open(_strings, encoding='utf-8', errors='replace').read()))


audit.known_messages = _known

if __name__ == '__main__':
    lines = []

    def emit(s=''):
        lines.append(str(s))
        print(s)
    res = audit.run(emit)
    with open(os.path.join(ROOT, 'build', 'audit_ps1port.txt'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
