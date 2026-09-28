"""The game's own menu loop, driven by scripted key presses: which UI sound
each button asks for, and what Escape does on each screen."""

import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nightjar.input.keymap import Action                          # noqa: E402
from nightjar.save.progress import InMemoryProgress               # noqa: E402
from nightjar.shell import (adios_menu, level_complete_menu,      # noqa: E402
                            level_failed_menu, level_menu, main_menu, pause_menu)
from nightjar.util import paths                                   # noqa: E402

_spec = importlib.util.spec_from_file_location('nj_play', os.path.join(ROOT, 'apps', 'play.py'))
play = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(play)


class Rep:
    def __init__(self):
        self.said = []

    def say(self, text, interrupt=True):
        self.said.append(text)

    def show(self, text):
        pass


class Src:
    quit_requested = False


class StubApp:
    """Just what run_menu touches: speech, input frames, UI sounds."""

    def __init__(self, keys):
        self.rep = Rep()
        self.src = Src()
        self.frames = [[(k.value, 'down', 0.0)] for k in keys]
        self.sounds = []

    def pump(self):
        if not self.frames:
            self.src.quit_requested = True
            return []
        return self.frames.pop(0)

    def ui(self, name):
        self.sounds.append(name)


A = Action


def run(menu, keys):
    app = StubApp(keys)
    return play.run_menu(app, menu), app.sounds, app.rep.said


def test_begin_clicks_and_goes_to_level_1_on_a_fresh_save():
    got, snd, said = run(main_menu(InMemoryProgress()), [A.CONFIRM])
    assert got == ('continue', 'nightJar_1') and snd == ['click_button']
    assert said[0] == 'The Nightjar. Continue.'


def test_about_makes_no_sound():
    got, snd, _ = run(main_menu(InMemoryProgress()), [A.MENU_DOWN] * 3 + [A.CONFIRM])
    assert got == ('about', None) and snd == []


def test_escape_on_the_main_menu_is_ignored():
    got, snd, _ = run(main_menu(InMemoryProgress()), [A.CANCEL, A.MENU_DOWN, A.CONFIRM])
    assert got == ('levels', None) and snd == ['click_button']


def test_quit_on_the_main_menu_plays_back():
    got, snd, _ = run(main_menu(InMemoryProgress()), [A.MENU_UP, A.CONFIRM])
    assert got == ('quit', None) and snd == ['back_button']


def test_a_locked_level_says_so_and_stays():
    m = level_menu(paths.game_bundle(), InMemoryProgress())
    got, snd, said = run(m, [A.MENU_DOWN, A.CONFIRM, A.MENU_UP, A.CONFIRM])
    assert got == ('play', 'nightJar_1') and snd == ['click_button']
    assert 'That level is locked.' in said


def test_escape_in_the_level_list_is_main_menu_with_the_back_sound():
    got, snd, _ = run(level_menu(paths.game_bundle(), InMemoryProgress()), [A.CANCEL])
    assert got == ('back', None) and snd == ['back_button']


def test_escape_in_pause_continues_the_game_with_a_click():
    got, snd, said = run(pause_menu(), [A.CANCEL])
    assert got == ('resume', None) and snd == ['click_button']
    assert said[0] == 'Paused. Continue game.'


def test_the_win_screen_says_its_words_and_continues_with_a_click():
    got, snd, said = run(level_complete_menu('nightJar_2'), [A.CONFIRM])
    assert got == ('next', 'nightJar_2') and snd == ['click_button']
    assert said[0] == "You're through but you're not safe yet. Continue."


def test_play_this_again_after_a_win_is_silent():
    got, snd, _ = run(level_complete_menu('nightJar_2'), [A.MENU_DOWN, A.CONFIRM])
    assert got == ('replay', None) and snd == []


def test_escape_after_a_level_is_main_menu():
    for menu in (level_complete_menu('nightJar_2'), level_failed_menu(), adios_menu()):
        got, snd, _ = run(menu, [A.CANCEL])
        assert got[0] == 'main' and snd == ['back_button']


def test_retry_clicks():
    got, snd, said = run(level_failed_menu(), [A.CONFIRM])
    assert got == ('replay', None) and snd == ['click_button']
    assert said[0] == '0 human life-forms detected. Retry.'


class _Engine:
    def __init__(self):
        self.master_volume_db = 0.0

    def adjust_master_volume(self, db):
        self.master_volume_db = max(-12.0, min(18.0, self.master_volume_db + db))


def test_page_up_and_down_change_the_volume_in_a_menu():
    app = StubApp([A.VOLUME_UP, A.VOLUME_UP, A.VOLUME_DOWN, A.CONFIRM])
    app.engine = _Engine()
    got = play.run_menu(app, main_menu(InMemoryProgress()))
    assert got == ('continue', 'nightJar_1')
    assert app.rep.said[1:4] == ['Volume +2 decibels.', 'Volume +4 decibels.',
                                 'Volume +2 decibels.']
    assert app.engine.master_volume_db == 2.0


def test_the_volume_says_when_it_is_at_the_top():
    app = StubApp([A.VOLUME_UP] * 10 + [A.CONFIRM])
    app.engine = _Engine()
    play.run_menu(app, main_menu(InMemoryProgress()))
    assert app.rep.said[-1] == 'Volume +18 decibels, maximum.'


def test_the_dpad_navigates_a_menu_and_leaves_the_volume_alone():
    app = StubApp([])
    app.engine = _Engine()
    # one d-pad press is both menu_right and volume_up, with one stamp
    app.frames = [[(A.MENU_RIGHT.value, 'down', 1.0), (A.VOLUME_UP.value, 'down', 1.0)],
                  [(A.CONFIRM.value, 'down', 2.0)]]
    play.run_menu(app, main_menu(InMemoryProgress()))
    assert app.engine.master_volume_db == 0.0


def test_decision_7_a_level_starts_without_an_announcement():
    class Game:
        loaded = None
        pictures = 0

        def show_headphones(self):
            self.pictures += 1

        def title(self, name):
            return name

        def load(self, name):
            self.loaded = name
    app = StubApp([])
    app.progress = InMemoryProgress()
    app.game = Game()
    play.start_level(app, 'nightJar_2')
    assert app.game.loaded == 'nightJar_2' and app.rep.said == []
    assert app.game.pictures == 1                  # chosen from a menu
    play.start_level(app, 'nightJar_2', launched=False)
    assert app.game.pictures == 1                  # Continue / Retry
    assert app.progress.is_level_unlocked('nightJar_2')
