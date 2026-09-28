# M1 - engine base (2026-09-26)

## What was built

The `nightjar/` package, in the Papa Sangre II port's layout:

| part | from | notes |
|---|---|---|
| audio (OpenAL binding, S3D engine, bank, loader, freeverb, monitor pump, measure) | PS2 port | the S3D layer is the same in both engines (ENGINE_DIFF: S3DSound 99 same + 22 same-refs); constants set from this binary |
| core/messages (the bus) | PS2 port | a superset of PS1's |
| core/triggers, assets/tiled (loader, trigger grammar) | PS1 port | 1_1_020 = this binary |
| world/level, world/surface, entities/agent, player, monster | PS1 port | re-checked against dis/all.txt; changes below |
| entities/sound_agent, entities/collectible | rewritten from this binary | the PS1 versions were simplified readings |
| core/game (loading, win/lose, clock, skip, UI sounds) | new, from this binary | PS2's clock with the carried remainder |
| input (keymap, padmap, gamepad, pygame source), accessibility, util, shell, update, sim | PS2 port | trimmed to this game's actions; renamed |
| save/progress | PS1 port | first level and last playlist default to nightJar_1 |

## Recovered in M1 (with addresses)

* **The level clock**: `-[PGELevel init]` schedules `update` every **0.1 s**
  (0x10002c50c) and `update` passes 0.1 to every agent (0x100032138). The PS1
  port updated agents every frame; this port ticks at 0.1 s on game time.
* **Load order**: agents with `active` are switched on as they are created
  (`setActive:` 0x10002f16c); `loadPlayer:` posts
  `SetControlSettingsToDefault` and `MovePlayerToPosition` (0x10002e678 /
  0x10002e788), which fires the Room's `OnEnter`; then `LevelInited`. The
  Room's hint list arrives as a posted `ChangeInactivitySoundList`
  (0x10002fc34).
* **With VoiceOver** the level loads only after "Wear headphones. Triple tap
  the top half of the screen to pause." has been spoken
  (`loadDataFromJsonFile:previousLevel:` 0x10002cbb0, `update` 0x100031fec).
* **PGESound** (0x1000297d8-0x10002a6bc): the sound starts **0.05 s** after
  activation (`performSelector:afterDelay:` 0x100029910) and `OnActivate` is
  queued first; the soundList is split on `&` keeping empty entries; exact
  lookup then `anySoundWihPrefix:`; a non-looping sound's monitor fires
  `triggerOnSoundEnd` on the main queue; `ShowSkipButton` and skipping both
  need `canSkipSound:` (heard to the end before); skip = `RemoveFullScreenImage`,
  stop, `triggerOnSoundEnd`.
* **PGECollectible** (0x10001b8f8-0x10001cd88): no `OnActivate`; an intro that
  equals the loop goes straight to the loop; intro reverb mix 1-2 px / wet
  0.1-0.75, loop 1-100 px / 0.05-0.3, **no gain set** (the PS1 port's -4 dB
  beacon trim was its own mix choice and is not here); the collect end posts
  `ActivateAgentWithName` directly; a collectible with no collect sound never
  ends (none of Nightjar's needs to).
* **PGEEnemy `playSound:looping:`** (0x10001e844): no `setSpatialized:` - the
  sound keeps its playlist flag; reverb mix 1-100 px / 0.05-0.3.
* **`PlaySpatialSoundOnAgentWithName`** (0x1000219e4, block 0x100021c2c): the
  sound is made spatial and played, **its position never set**. Only level 8
  uses it; to check by ear at M4.
* **The hint timer** (`update` 0x100032028, `playInactivitySound` 0x100033cd4,
  `changeInactivitySoundList:` 0x100033af0): `inactivityTime` starts at
  **+inf** (0x10002c4a8); the clock restarts while a hint plays or there is
  no list; no zero guard; a hint that does not resolve is a silent turn; a
  new list starts again at its first line.
* **Win and lose** (`-[PGEngine loadLevelWithName:]` 0x1000362a4): another
  level = win (complete, unlock, `PresentWinVC`), the same level = lose
  (`PresentLoseVC`).
* **UI sounds** (`playUiSoundWithName:` 0x10003715c): each a new player
  replacing the last; no spacing rule. The splash plays
  `nightjar_sounds/splash/papa_engine_splash.wav`; its accessibility text is
  "Developped by Somethin' Else, published by Playground" (0x10003d858).
* **The reverb** (the C++ CSL Freeverb, not covered by the method diff): the
  same tables (0x100142930 / 0x100142950), 6 combs and 3 allpasses, starting
  values and room/dampening formulas (0x1000c3600 / 0x1000c3694) as the PS2
  model. One room for the game: 2.1 / 5 / 1.
* **Shutdown**: one pass over the agents (0x1000347e4) - the PS1 port's
  repeated sweep was for ps1_23's `OnDeactivate` loops; no Nightjar level has
  an `OnDeactivate`.

## Proved

* 73 tests pass (`tests/`): the recovered constants, the listener transform,
  bit-exact decoding, the HRTF rendered and measured through the loopback
  device, the game's own door and monster heard from their side, flat stereo
  played as on disk, flat mono at 0.5 per ear, the reverb against the
  recovered Freeverb (0.00 dB mean over four directions, decay within 15 %),
  all 14 levels load and start, level 1 end to end (cutscene chain, controls,
  hints at 20 s, the floor triggers, the door, the win), skip gating, the
  collectible and hint rules, win/lose, the clock (13 ms frames = 13 s).
* Content check: 14 levels, 162 objects, 267 triggers, 322 sound references,
  495 declarations; 17 findings, every one an explained data defect; 0
  unexplained (`docs/CONTENT_CHECK.md`).
* `Run\The Nightjar.exe` (folder build, 41 MB, data pack 331 files / 36 MB,
  no credentials file, no Papa Sangre leftovers) self-tested from a clean
  folder: HRTF enabled with the recovered table, NVDA speech, game time 20.0 s
  in 20.0 s, level 1 loaded and its cutscene playing.

## Measured decisions (port-side, logged)

* Default master volume **1.0** (PS2 used 1.4): the Nightjar narration and
  sensors peak at 0 to -1.5 dBFS, so any lift puts 110 of 163 speech and
  sensor files into OpenAL's limiter (measured: the narration's correlation
  with the file fell to 0.997).
* `EFX_ENERGY_MATCH` refitted to this game's one room: 0.9713.
* Level sounds are decoded at load (about 1 s): the original streams on its
  own audio thread; decoding on first play stalled the loop (the self-test
  read 19.8 s in 20 s).

## Left for M2

Main menu, level list, settings, About, the audited win / lose / end screens
(their texts and each button's UI sound, from the `_nj` nibs and handlers),
the menu atmosphere (`preloadMenuAtmos`: the ATMOS sounds of the last
playlist), PC instructions after the lines that name touch controls
(prompt_d_lvl1_a, prompt_d_lvl1_b), the level 1 autopilot, and a play test.
