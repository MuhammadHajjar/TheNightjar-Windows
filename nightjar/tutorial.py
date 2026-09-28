"""The PC versions of the lines that name a touch control (house standard).

The narration is recorded speech about a touchscreen, and it cannot be
re-recorded.  So each line that tells you *how* to do something with the phone
plays as recorded, and then the screen reader says how to do it here, naming
whatever the keys (and, with one connected, the controller buttons) are bound
to at that moment - a rebound key is spoken as rebound.

Which lines - every speech file was transcribed (build/transcripts/
medium.en.json, faster-whisper medium.en) and only those that describe the
phone get a PC version:

* ``cutscene_friday3`` (level 1) ends "Use your thumbs. Left, right, left,
  right.  Listen to your footsteps";
* ``prompt_d_lvl1_a`` (level 1's and level 2's hints) "Touch the bottom
  left-hand side of your screen now.  Step.  Touch the bottom right of your
  screen.  Step.";
* ``prompt_d_lvl1_b`` "Walk with your thumbs on the bottom half of your
  screen" (level 1's hints);
* ``prompt_d_lvl4_a`` and ``prompt_d_lvl5_a`` "Swipe the top of your screen to
  turn" (levels 4 and 5's hints); ``prompt_d_lvl3_a`` says the same and no
  level plays it (decision 2 leaves it to M3).

Lines that only say *what* to do - "turn left until the sound is in both
ears", "walk five steps", "if you go a little quicker, you can run" - name no
control and get nothing.  A looping line gets its PC version once, after its
first pass; a line that is skipped gets none.
"""

from __future__ import annotations

from .input.keymap import Action
from .input.padmap import button_label

_KEY_NAMES = {
    'return': 'Enter', 'keypad enter': 'keypad Enter', 'escape': 'Escape',
    'backspace': 'Backspace', 'space': 'Space', 'tab': 'Tab',
    'left': 'Left arrow', 'right': 'Right arrow', 'up': 'Up arrow',
    'down': 'Down arrow', 'left ctrl': 'Left Control', 'right ctrl': 'Right Control',
    'left shift': 'Left Shift', 'right shift': 'Right Shift',
    'left alt': 'Left Alt', 'right alt': 'Right Alt',
    'page up': 'Page Up', 'page down': 'Page Down',
}


def key_name(key: str) -> str:
    k = str(key).lower()
    if k in _KEY_NAMES:
        return _KEY_NAMES[k]
    if len(k) == 1:
        return k.upper()
    return k


def keys(keymap, action) -> str:
    ks = keymap.keys_for(action)
    if not ks:
        return 'an unbound key'
    return ' or '.join(key_name(k) for k in ks)


def buttons(padmap, action) -> str:
    bs = padmap.buttons_for(action)
    if not bs:
        return 'an unbound button'
    return ' or '.join(button_label(b) for b in bs)


def pc_lines(keymap, padmap=None, pad_connected=lambda: False) -> dict:
    """Sound name -> a function returning the words to say after it."""
    A = Action

    def k(a):
        return keys(keymap, a)

    def pad(text):
        """The controller's version, only when one is connected."""
        if padmap is None or not pad_connected():
            return ''
        return ' On the controller: ' + (text() if callable(text) else text)

    def b(a):
        return buttons(padmap, a)

    def walking():
        return (f'On this computer, your feet are {k(A.FOOT_LEFT)} and {k(A.FOOT_RIGHT)}. '
                'Press them one after the other to walk.'
                + pad(lambda: f'{b(A.FOOT_LEFT)} and {b(A.FOOT_RIGHT)}, one after the other.'))

    def stepping():
        return (f'On this computer, press {k(A.FOOT_LEFT)} for your left foot, then '
                f'{k(A.FOOT_RIGHT)} for your right.'
                + pad(lambda: f'{b(A.FOOT_LEFT)}, then {b(A.FOOT_RIGHT)}.'))

    def turning():
        return (f'On this computer, turn with {k(A.TURN_LEFT)} and {k(A.TURN_RIGHT)}; '
                'hold one down to keep turning.'
                + pad('push the left stick left or right.'))

    return {
        'cutscene_friday3': walking,
        'prompt_d_lvl1_a': stepping,
        'prompt_d_lvl1_b': walking,
        'prompt_d_lvl3_a': turning,
        'prompt_d_lvl4_a': turning,
        'prompt_d_lvl5_a': turning,
    }


def pc_about(keymap) -> str:
    """After the About page, which says only to wear headphones."""
    A = Action
    return (f'On this computer: walk by pressing your feet, {keys(keymap, A.FOOT_LEFT)} '
            f'and {keys(keymap, A.FOOT_RIGHT)}, one after the other. Turn with '
            f'{keys(keymap, A.TURN_LEFT)} and {keys(keymap, A.TURN_RIGHT)}. '
            f'{keys(keymap, A.SKIP)} skips a line you have heard before, and '
            f'{keys(keymap, A.PAUSE)} pauses. {keys(keymap, A.VOLUME_UP)} and '
            f'{keys(keymap, A.VOLUME_DOWN)} change the volume, anywhere in the game. '
            f'Every key can be changed in Settings.')
