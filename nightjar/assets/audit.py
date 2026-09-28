"""Cross-check the game's data against the engine: nothing unexplained.

Used by ``apps/check_content.py`` and the tests.  For all 14 levels:

* every object type and property is one the engine applies (or a known typo);
* every trigger statement parses, and every message name is one the engine
  knows (from its string table) or a known defect in the data;
* every sound a level names resolves through that level's own playlist;
* every agent a trigger addresses exists, and every level loaded exists;
* every playlist declaration resolves to a shipped file.

Each finding is either one of the original's data defects - listed in
``KNOWN`` with the reason, and in GAME_STRUCTURE.md - or it is unexplained.
The check passes when nothing is unexplained.
"""

from __future__ import annotations

import os

from .. import APP_NAME
from . import pack
from .sexp import include_stem, parse_playlist
from .tiled import AGENT_TYPES, level_path, load_level

LEVELS = ['nightJar_%d' % i for i in range(1, 15)]

#: Object types a Nightjar level may contain (the engine's agent types plus
#: the structural ones).
OBJECT_TYPES = set(AGENT_TYPES) | {'Room', 'Surface', 'ActionSurface', 'Path', 'Player'}

#: Properties with a setter somewhere in the engine (class dump + the loader).
SETTABLE = {
    'name', 'active', 'soundList', 'collideRadius', 'shootRange', 'speed',
    'chaseSpeed', 'gain', 'looping', 'spatialized', 'skippable', 'onXrail',
    'onYrail', 'introSound', 'collectSound', 'loopSound', 'nextCollectible',
    'walkingSpeed', 'distractedTime', 'walkingPauseSound', 'awareSound',
    'defaultSound', 'chaseSound', 'notThereSound', 'attackSound',
    'chasingRadius', 'footstepsPrefix', 'surfaceId', 'z', 'tripBPM', 'runBPM',
    'tripSound', 'shuffleSound', 'multipleOnEnter', 'inactivitySounds',
    'inactivityTime', 'isInfinite', 'hitWallSound', 'pixelsPerStep',
    'startAngle', 'shootSound',
}

#: Message names the engine observes, from its string table.
ENGINE_MESSAGES = {
    'PGE_MESSAGE_' + n for n in (
        'ActivateAgentWithName', 'DeactivateAgentWithName', 'AlertAllEnemies',
        'AlertEnemyWithName', 'AlertEnemiesWithinRadius', 'ChangeInactivitySoundList',
        'ChangeInactivityTime', 'ChangeSoundListOnAgentWithName', 'DisableHands',
        'DisableJump', 'DisableRotation', 'DisableSwim', 'DisableWalk', 'EnableHands',
        'EnableJump', 'EnableRotation', 'EnableSwim', 'EnableWalk', 'FollowPathWithName',
        'StopFollowingPath', 'LoadLevelWithName', 'PlaySound', 'PlaySpatialSound',
        'PlaySpatialSoundOnAgentWithName', 'PresentAdiosVC', 'ShutDownLevel',
        'ApplyBpmConstraint', 'ApplyProximityRadiusToPlayer', 'MovePlayerToPosition',
        'MoveObjectToPositionWithName', 'StartFullWheelRotation', 'Log')}

#: Properties whose value names a sound in the level's playlist.
SOUND_PROPS = ('soundList', 'introSound', 'collectSound', 'loopSound', 'tripSound',
               'shuffleSound', 'inactivitySounds', 'awareSound', 'defaultSound',
               'chaseSound', 'notThereSound', 'attackSound', 'walkingPauseSound',
               'shootSound', 'hitWallSound')

#: The original's own data defects, each explained (GAME_STRUCTURE.md).
KNOWN = {
    ('property', 'nightJar_3', 'Room.foostepsPrefix'):
        'typo for footstepsPrefix; no setter matches, so the room has no prefix '
        '(walking is never enabled in level 3)',
    ('message', 'nightJar_4', 'PGE_MESSAGE_easteregg_flies_away'):
        'a sound name written as a message; nothing observes it',
    ('message', 'nightJar_6', 'PGE_MESSAGE_prompt_d_lvl5_i'):
        "the Player's OnTrip names a line as a message; the line never plays "
        '(decision 2 gives it a voice)',
    ('sound', 'nightJar_6', 'prompt_d_lvl6_c'):
        "in level 6's hint list but not its playlist: silent there (decision 2)",
    ('sound', 'nightJar_7', 'prompt_d_lvl7_e_alt'):
        'no such sound (the file is prompt_d_lvl7_e): a silent hint turn (decision 2)',
    ('sound', 'nightJar_9', 'prompt_d_lvl4_e_alt'):
        'no such sound: a silent hint turn',
    ('sound', 'nightJar_9', 'prompt_d_lvl8_e'):
        'declared in no playlist: a silent hint turn (decision 2)',
    ('sound', 'nightJar_10', 'foot_metalsolid_run'):
        "the Room's tripSound; no such sound (the file is trip_metalsolid_run): a silent trip",
    ('sound', 'nightJar_5', 'foot_stone_01_dry_shuffle'):
        "the Room's shuffleSound; no such sound: a silent shuffle",
    ('sound', 'nightJar_12', 'Atmos_CorridorPassage'):
        'the playlist spells it Atmos_corridorpassage and the lookup is '
        'case-sensitive (S3DSound: compare: 0x1000d607c, anySoundWihPrefix: hasPrefix: 0x1000d393c): silent in the original too',
    ('sound', 'nightJar_9', ''):
        "wrigley1's defaultSound is empty",
    ('sound', 'nightJar_2', ''):
        "the LVL2_2E Sound's soundList is empty (in the engine that would be "
        'anySoundWihPrefix:@"" - any sound at all), but nothing activates it: '
        "the line is played as the exit's collectSound",
    ('agent', 'nightJar_2', 'LVL2_1C'):
        'no agent of that name (the line is also a PlaySound, so it is heard)',
    ('agent', 'nightJar_9', 'note1'):
        'no agent of that name; nothing happens',
    ('agent', 'nightJar_12', 'easteregg_mechsweepb_01_dry'):
        'no agent of that name; nothing happens',
    ('agent', 'nightJar_12', 'exit'):
        "note1's nextCollectible; level 12 has no exit agent - its note1 is the door",
    ('trigger', 'nightJar_13', 'Collectible[note2].OnCollect'):
        'OnCollect is not an engine trigger; the hint list never changes after '
        'note 2 (decision 2)',
}


def _read_playlists(bundle: str) -> dict:
    meta = os.path.join(bundle, 'meta', 'S3DPlayListModel')
    out = {}
    for path in pack.glob(os.path.join(meta, '*.sexp')):
        stem = os.path.basename(path).split('.S3DPlayListModel')[0]
        out[stem] = parse_playlist(pack.read_bytes(path).decode('utf-8', 'replace'),
                                   os.path.basename(path))
    return out


def _flatten(pls: dict, stem: str, seen=None) -> dict:
    seen = set() if seen is None else seen
    if stem in seen or stem not in pls:
        return {}
    seen.add(stem)
    out = {s.name: s for s in pls[stem].sounds if s.name}
    for inc in pls[stem].includes:
        for k, v in _flatten(pls, include_stem(inc), seen).items():
            out.setdefault(k, v)
    return out


def run(bundle: str) -> dict:
    """Every finding, split into explained and unexplained."""
    import json
    pls = _read_playlists(bundle)
    findings = []                                   # (kind, level, what, detail)
    counts = {'levels': 0, 'objects': 0, 'triggers': 0, 'sound refs': 0, 'declarations': 0}
    for lv in LEVELS:
        path = level_path(bundle, lv)
        data = load_level(path, lv)
        raw = json.loads(pack.read_bytes(path).decode('utf-8'))
        counts['levels'] += 1
        flat = _flatten(pls, lv)
        names = {o.name for o in data.objects if o.name}
        # raw properties, to catch trigger keys the loader ignores
        for layer in raw.get('layers', []):
            for o in layer.get('objects', []):
                t = o.get('type') or ''
                for k in (o.get('properties') or {}):
                    if k.startswith('On'):
                        from .tiled import TRIGGER_NAMES, _AGENT_TRIGGERS
                        if k not in TRIGGER_NAMES.get(t, _AGENT_TRIGGERS):
                            findings.append(('trigger', lv, f'{t}[{o.get("name")}].{k}', ''))
        for o in [data.room] + data.objects + ([data.player] if data.player else []):
            if o is None:
                continue
            counts['objects'] += 1
            if o.type not in OBJECT_TYPES:
                findings.append(('type', lv, o.type, o.name))
            for k in o.settable:
                if k not in SETTABLE:
                    findings.append(('property', lv, f'{o.type}.{k}', ''))
            for k in SOUND_PROPS:
                v = o.properties.get(k)
                if v is None:
                    continue
                for n in str(v).split('&'):
                    counts['sound refs'] += 1
                    if n not in flat:
                        findings.append(('sound', lv, n, f'{o.type}[{o.name}].{k}'))
            for t in o.triggers:
                counts['triggers'] += 1
                if t.malformed:
                    findings.append(('malformed', lv, t.raw, ''))
                if t.notification_name not in ENGINE_MESSAGES:
                    findings.append(('message', lv, t.notification_name, t.raw))
                    continue
                short = t.notification_name[len('PGE_MESSAGE_'):]
                if 'soundName' in t.parameters:
                    for n in t.parameters['soundName'].split('&'):
                        counts['sound refs'] += 1
                        if n not in flat:
                            findings.append(('sound', lv, n, t.raw))
                if short == 'ChangeInactivitySoundList':
                    for n in t.parameters.get('soundList', '').split('&'):
                        counts['sound refs'] += 1
                        if n not in flat:
                            findings.append(('sound', lv, n, t.raw))
                target = t.parameters.get('agentName', t.parameters.get('name'))
                if short in ('ActivateAgentWithName', 'DeactivateAgentWithName',
                             'PlaySpatialSoundOnAgentWithName', 'AlertEnemyWithName',
                             'ChangeSoundListOnAgentWithName') and target not in names:
                    findings.append(('agent', lv, target, t.raw))
                if short == 'LoadLevelWithName' and not pack.isfile(level_path(bundle, target)):
                    findings.append(('level', lv, target, t.raw))
        for o in data.objects:
            nxt = o.properties.get('nextCollectible')
            if nxt and nxt not in names:
                findings.append(('agent', lv, nxt, f'{o.name}.nextCollectible'))
    # every declaration the Nightjar playlists make resolves to a file
    for lv in LEVELS:
        for name, decl in _flatten(pls, lv).items():
            counts['declarations'] += 1
            if not pack.isfile(os.path.join(bundle, decl.bundle_path)):
                findings.append(('file', lv, decl.bundle_path, name))
    seen = set()
    explained, unexplained = [], []
    for f in findings:
        key = f[:3]
        if key in seen:
            continue
        seen.add(key)
        (explained if key in KNOWN else unexplained).append(f)
    return {'counts': counts, 'explained': explained, 'unexplained': unexplained,
            'app': APP_NAME}
