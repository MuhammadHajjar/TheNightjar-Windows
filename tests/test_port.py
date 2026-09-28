"""The port's own housekeeping: content, keys, versions, the save."""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar import APP_NAME, __version__                      # noqa: E402
from nightjar.assets import audit                               # noqa: E402
from nightjar.assets.hublist import load_hub_list               # noqa: E402
from nightjar.input.keymap import Action, DEFAULT_BINDINGS, KeyMap  # noqa: E402
from nightjar.util import paths                                 # noqa: E402


def test_the_content_check_leaves_nothing_unexplained():
    r = audit.run(paths.game_bundle())
    assert r['counts']['levels'] == 14
    assert r['unexplained'] == []


def test_the_level_list_is_the_nightjar_hub_list():
    assert APP_NAME == 'The Nightjar'
    entries = load_hub_list(paths.game_bundle())
    assert [e.file_name for e in entries] == ['nightJar_%d' % i for i in range(1, 15)]
    assert entries[0].alt_name == 'New Ears' and entries[-1].alt_name == 'Choose Death'
    assert entries[0].spoken() == 'Play Level 1: New Ears'
    assert entries[1].spoken() == 'Level 2: Walk This Way; locked'


def test_no_two_gameplay_actions_share_a_key():
    assert KeyMap().conflicts() == {}


def test_nothing_on_the_keyboard_quits():
    assert not any('quit' in a for a in DEFAULT_BINDINGS)
    assert DEFAULT_BINDINGS[Action.PAUSE.value] == ['escape']


def test_the_version_is_the_changelogs_newest_heading():
    text = open(os.path.join(ROOT, 'changelog.txt'), encoding='utf-8').read()
    heads = re.findall(r'^(\d{4}-\d{2}-\d{2}(?: number \d+)?)$', text, re.M)
    assert heads and heads[0] == __version__
    assert open(os.path.join(ROOT, 'VERSION'), encoding='utf-8').read().strip() == __version__
    days = [h.split(' ')[0] for h in heads]
    assert days == sorted(days, reverse=True)


def test_the_credentials_file_is_ignored():
    """EIGC_Users.plist holds a third-party service's user names and passwords."""
    text = open(os.path.join(ROOT, '.gitignore'), encoding='utf-8').read()
    lines = [l.strip() for l in text.splitlines()]
    assert 'EIGC_Users.plist' in lines and '**/EIGC_Users.plist' in lines
    # and it comes after every negation that could bring it back
    last_negation = max(i for i, l in enumerate(lines) if l.startswith('!'))
    assert lines.index('EIGC_Users.plist') > last_negation


def test_a_progress_file_is_written_beside_the_game_and_read_back(tmp_path):
    from nightjar.save.progress import GameProgress
    p = GameProgress(str(tmp_path / 'progress.json'))
    p.player_did_unlock_level('nightJar_2')
    q = GameProgress(str(tmp_path / 'progress.json'))
    assert q.is_level_unlocked('nightJar_2')
    assert q.last_unlocked_level == 'nightJar_2'
