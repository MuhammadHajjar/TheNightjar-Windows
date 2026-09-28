"""The shell: the original's labels, each button's UI sound, the screens'
texts word for word, the PC instructions, and the menu atmosphere."""

import os
import random
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.core.game import ATMOS_FADE_IN, QUIT_ATMOS_DELAY, Game   # noqa: E402
from nightjar.input.keymap import Action, KeyMap                       # noqa: E402
from nightjar.save.progress import InMemoryProgress                    # noqa: E402
from nightjar.shell import (about_menu, adios_menu,                    # noqa: E402
                            credits_menu, level_complete_menu, level_failed_menu,
                            level_menu, main_menu, pause_menu)
from nightjar.shell import texts                                       # noqa: E402
from nightjar.sim import FakeBank                                      # noqa: E402
from nightjar.tutorial import pc_lines                                 # noqa: E402
from nightjar.util import paths                                        # noqa: E402

APP = os.path.join(ROOT, 'reference', 'Payload', 'The Nightjar.app')


def sounds(menu):
    return {i.label: i.ui_sound() for i in menu.items}


# ------------------------------------------------------------ labels and sounds
def test_the_main_menu_is_the_nibs():
    m = main_menu(InMemoryProgress())
    labels = [i.label for i in m.items]
    assert labels[:4] == ['Continue', 'Select Level', 'Credits', 'About']
    assert 'Cast' not in labels                          # decision 4: inside Credits
    s = sounds(m)
    # continueButtonPressed: / hubSelectorButtonTouched: / launchCredits:
    # click; TriggerOtherGames: (the About button) plays none
    assert [s[x] for x in ('Continue', 'Select Level', 'Credits')] == ['click_button'] * 3
    assert s['About'] is None
    assert not m.cancellable


def test_begin_goes_to_the_furthest_level_unlocked():
    p = InMemoryProgress()
    assert main_menu(p).items[0].value == 'nightJar_1'
    p.player_did_unlock_level('nightJar_4')
    assert main_menu(p).items[0].value == 'nightJar_4'


def test_the_level_list():
    p = InMemoryProgress()
    m = level_menu(paths.game_bundle(), p)
    assert m.items[0].label == 'Play Level 1: New Ears' and m.items[0].enabled
    assert m.items[1].label == 'Level 2: Walk This Way; locked' and not m.items[1].enabled
    assert m.items[-1].label == 'Main Menu' and m.items[-1].ui_sound() == 'back_button'
    assert m.items[0].ui_sound() == 'click_button'       # house standard


def test_the_pause_screen():
    m = pause_menu()
    s = sounds(m)
    assert s['Continue game'] == s['Restart Level'] == 'click_button'
    assert s['Quit game'] == 'back_button'
    assert m.cancel.action == 'resume'


def test_the_after_level_screens():
    w = sounds(level_complete_menu('nightJar_2'))
    assert w['Continue'] == 'click_button'
    assert w['Play this again'] is None                  # playAgainButtonTouched: plays none
    assert w['Main menu'] == 'back_button'
    lose = sounds(level_failed_menu())
    assert lose['Retry'] == 'click_button' and lose['Main Menu'] == 'back_button'
    end = sounds(adios_menu())
    assert end['Play this again'] == 'click_button' and end['Main Menu'] == 'back_button'
    assert level_complete_menu('x').title == "You're through but you're not safe yet"
    assert level_failed_menu().title == '0 human life-forms detected'
    assert adios_menu().title == 'The End'


# ------------------------------------------------------------ texts, word for word
def _words(s):
    s = s.replace('’', "'").replace('©', '(c)')
    return re.findall(r"[a-z0-9']+", s.lower())


def _binary_string(start: bytes) -> str:
    b = open(os.path.join(ROOT, 'reference', 'Nightjar_arm64'), 'rb').read()
    i = b.find(start)
    return b[i:b.find(b'\0', i)].decode('utf-8')


def test_the_cast_is_the_binarys_word_for_word():
    src = _binary_string(b'CAST:DICKIE')
    assert sorted(_words(' '.join(texts.CAST))) == sorted(_words(src))


def test_the_credits_are_the_binarys_word_for_word():
    src = _binary_string(b'THE NIGHTJAR, CREATED')
    assert sorted(_words(' '.join(texts.CREDITS))) == sorted(_words(src))


def test_the_about_page_is_the_htmls_word_for_word():
    import html
    raw = open(os.path.join(APP, 'html', 'othergames_nj1.html'), encoding='cp1252').read()
    body = raw[raw.find('<body'):]
    body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
    text = html.unescape(re.sub(r'<[^>]+>', ' ', body))
    assert sorted(_words(' '.join(texts.ABOUT))) == sorted(_words(text))


def test_the_cast_is_read_inside_credits_under_its_own_heading():
    rows = [i.label for i in credits_menu().items]
    assert rows[0] == "The Nightjar, created by Somethin' Else and AMV BBDO."
    i = rows.index('Cast')
    assert rows[i + 1] == 'Dickie von Kolding: Benedict Cumberbatch'
    assert rows[-2] == 'Adam Pedersen: Dave O-Donnell' and rows[-1] == 'Main Menu'


def test_the_text_screens_end_with_main_menu():
    for m in (credits_menu(), about_menu('2026-09-27', 'note')):
        assert m.items[-1].label == 'Main Menu' and m.items[-1].ui_sound() == 'back_button'
    a = about_menu('2026-09-27', 'note')
    assert a.items[0].label == 'Version 2026-09-27' and a.items[-2].label == 'note'


# ------------------------------------------------------------ PC instructions
def test_the_pc_lines_name_the_keys_as_they_are_bound():
    km = KeyMap()
    lines = pc_lines(km)
    assert set(lines) >= {'cutscene_friday3', 'prompt_d_lvl1_a', 'prompt_d_lvl1_b',
                          'prompt_d_lvl4_a', 'prompt_d_lvl5_a'}
    assert 'A and D' in lines['cutscene_friday3']()
    km.bind(Action.FOOT_LEFT, ['j'])
    assert 'J and D' in pc_lines(km)['prompt_d_lvl1_b']()


class _Settings:
    pc_instructions = True


def test_a_touch_line_is_followed_by_its_pc_version():
    from nightjar.sim import Sim
    s = Sim('nightJar_1')
    said = []
    lines = pc_lines(KeyMap())
    s.level.on_line_ended = lambda name: said.append((name, lines[name]()) if name in lines else None)
    s.run_until(lambda: s.interpreter.player_can_walk, limit=400)
    s.step(0.1)
    assert any(n == 'cutscene_friday3' for n, _ in filter(None, said))
    # and the hints that name the feet, when they play
    s.run_until(lambda: 'prompt_d_lvl1_b' in s.played(), limit=60)
    s.run_until(lambda: any(x and x[0] == 'prompt_d_lvl1_b' for x in said), limit=10)
    assert any(x and x[0] == 'prompt_d_lvl1_b' for x in said)


# ------------------------------------------------------------ the menu atmosphere
def _game(progress=None):
    bundle = paths.game_bundle()

    class _Clock:
        log = []
        now = 0.0
    clock = _Clock()

    def bank(name):
        return FakeBank(clock, bundle, name, random.Random(1))
    g = Game(bundle, progress or InMemoryProgress(), _Settings(), bank)
    return g, clock


def test_the_menu_atmosphere_is_the_last_levels_atmos_faded_in():
    p = InMemoryProgress()
    p.save_last_playlist('nightJar_4')
    g, clock = _game(p)
    atmos = g.play_menu_atmos()
    assert [s.name for s in atmos] == ['Atmos_systemsroom']
    s = atmos[0]
    assert s.looping and s.gain == 0.0
    clock.now = 0.25
    g.menu_update(0.25)
    assert s.gain == pytest.approx(0.5, abs=0.05)
    clock.now = 0.6
    g.menu_update(0.35)
    assert s.gain == 1.0 and ATMOS_FADE_IN == 0.5


def test_loading_a_level_stops_the_menu_atmosphere():
    g, _ = _game()
    atmos = g.play_menu_atmos()
    assert atmos and atmos[0].playing
    g.load('nightJar_1')
    assert not atmos[0].playing


def test_quit_game_brings_the_atmosphere_back_a_second_later():
    g, clock = _game()
    g.load('nightJar_1')
    g.quit_level()
    assert g.atmos == []
    g.menu_update(QUIT_ATMOS_DELAY - 0.05)
    assert g.atmos == []
    g.menu_update(0.1)
    assert g.atmos and g.atmos[0].name == 'Atmos_cargobay'


def test_the_main_menu_offers_check_for_updates_before_quit():
    from nightjar.shell import main_menu as mm
    labels = [i.label for i in mm(InMemoryProgress(), updates=True).items]
    assert labels[-2:] == ['Check for updates', 'Quit']
    assert 'Check for updates' not in [i.label for i in mm(InMemoryProgress()).items]
