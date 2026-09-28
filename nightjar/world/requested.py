"""The decisions about the level data (BUILD_ORDER), applied as a level loads.

The original data is never edited; each change is made here, to the loaded
copy, and each is logged in docs/DIVERGENCES.md (REQUESTED) with its decision
number in docs/BUILD_ORDER.md.

Decision 2 (2026-09-26): every recorded line is heard - each line the original
leaves unheard goes where the level data shows it was meant to go.
Decision 5 (2026-09-27): level 3's three unused turning lines are its hints.
Decision 8 (2026-09-27): level 13's footsteps are 6 dB louder.
Decision 9 (2026-09-28, Seth's beta report): 9b level 5's door cuts off the
creature; 9d level 8's hot water steps are 6 dB louder.
"""

from __future__ import annotations

from ..assets.tiled import Trigger, parse_trigger_statement

PROMPTS = 'nightjar_sounds/prompts'

#: Lines a level's playlist does not declare, declared for it (flat, as every
#: prompt is declared elsewhere).
ENSURE = {
    'nightJar_3': ['prompt_d_lvl3_a', 'prompt_d_lvl3_b', 'prompt_d_lvl3_d 2'],   # decision 5
    'nightJar_6': ['prompt_d_lvl6_c'],          # in level 6's hint list, not its playlist
    'nightJar_7': ['prompt_d_lvl7_e'],          # the list names prompt_d_lvl7_e_alt
    'nightJar_9': ['prompt_d_lvl8_e'],          # in level 9's hint lists, declared nowhere
}


#: Decision 8: a level's footstep gain where it is not the original's 0.5
#: (-[PGEPlayer moveForwardOneStep:]).  Level 13's spacewalk steps peak about
#: 7 dB under the metal floors before it, under its two loudest atmospheres
#: at once: "the steps are so quiet they're like don't exist".
FOOTSTEP_GAIN = {'nightJar_13': 1.0}
#: Decision 9d: the same by footstep bank, wherever it is walked on.  The hot
#: water steps are the quietest in the game (loudest 100 ms about -33 dBFS).
FOOTSTEP_GAIN_BY_PREFIX = {'foot_hotwater': 1.0}

#: Port-only message for decision 9b: stop a sound by name.  The engine has
#: no such message; nothing in the original data can post it.
STOP_SOUND = 'PGE_MESSAGE_PortStopSound'


def _obj(data, name):
    for o in data.objects:
        if o.name == name:
            return o
    return None


def _level3(data) -> None:
    """Decision 5: the three lines as level 3's hint list, starting 20 s after
    the hologram speech ends (as levels 1 and 2 time theirs)."""
    data.room.properties['inactivitySounds'] = 'prompt_d_lvl3_a&prompt_d_lvl3_b&prompt_d_lvl3_d 2'
    intro = _obj(data, 'LVL3_1A')
    if intro is not None:
        intro.triggers.append(parse_trigger_statement('OnSoundEnd', 'ChangeInactivityTime:value=20'))


def _level5(data) -> None:
    """Decision 9b: the sensor that shuts the door on the creature stops the
    two floor-strip lines it lives in (LVL5b "Hear something?", LVL5c "Get to
    the sensor to close the door on that thing") - in the original they play
    on, up to 12 s past the door."""
    note = _obj(data, 'note1')
    if note is not None:
        for line in ('LVL5b', 'LVL5c'):
            note.triggers.append(parse_trigger_statement(
                'OnCollide', f'{STOP_SOUND}:soundName={line}'))


def _level6(data) -> None:
    """Decision 2: the Player's OnTrip names "Don't run too fast!" as a
    message; it is played as the designer meant."""
    p = data.player
    if p is None:
        return
    p.triggers = [parse_trigger_statement('OnTrip', 'PlaySound:soundName=prompt_d_lvl5_i')
                  if t.trigger_type == 'OnTrip' and t.notification_name == 'PGE_MESSAGE_prompt_d_lvl5_i'
                  else t for t in p.triggers]


def _level7(data) -> None:
    """Decision 2: the hint list's prompt_d_lvl7_e_alt is the file prompt_d_lvl7_e."""
    v = data.room.properties.get('inactivitySounds', '')
    data.room.properties['inactivitySounds'] = v.replace('prompt_d_lvl7_e_alt', 'prompt_d_lvl7_e')


def _level13(data) -> None:
    """Decision 2: note 2's `OnCollect` (not an engine trigger) is its OnCollide,
    so the hint list changes after note 2 and prompt_d_lvl12_a is heard."""
    note = _obj(data, 'note2')
    if note is None or 'OnCollect' not in note.properties:
        return
    for stmt in str(note.properties['OnCollect']).split('|'):
        if stmt.strip():
            note.triggers.append(parse_trigger_statement('OnCollide', stmt.strip()))


CHANGES = {
    'nightJar_3': _level3,
    'nightJar_5': _level5,
    'nightJar_6': _level6,
    'nightJar_7': _level7,
    'nightJar_13': _level13,
}


def apply(data, bank) -> list[str]:
    """Make the requested changes to one loaded level.  Returns the lines
    declared for it."""
    fn = CHANGES.get(data.name)
    if fn is not None:
        fn(data)
    added = []
    ensure = getattr(bank, 'ensure', None)
    for name in ENSURE.get(data.name, ()):
        if ensure is not None and ensure(name, f'{PROMPTS}/{name}.m4a', False):
            added.append(name)
    return added


__all__ = ['apply', 'ENSURE', 'CHANGES', 'FOOTSTEP_GAIN', 'FOOTSTEP_GAIN_BY_PREFIX',
           'STOP_SOUND', 'Trigger']
