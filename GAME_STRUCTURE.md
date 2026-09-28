# The Nightjar - recovered structure

The engine is Papa Sangre 1's (the same build; see docs/notes/M0_NOTES.md), so
the engine model, movement maths and trigger grammar are those in
`../PapaSangre/GAME_STRUCTURE.md`, with the Nightjar branches below. This file
grows with each milestone.

## Nightjar branches of the engine

| where | Nightjar | PS1 |
|---|---|---|
| distanceScale (`-[PGELevel initSoundEngine]` 0x10002c9c0) | 0.015625 | 0.008 |
| first level (`-[PGEGameProgress lastUnlockedLevel]` 0x10002b784, `getLastPlaylist` 0x10002bc48) | nightJar_1 | ps1_1 |
| splash sound (`-[PGEViewController showSplashScreen]` 0x10003d784) | nightjar_sounds/splash/papa_engine_splash.wav | - |
| nibs (`getNibName`) | `_nj` | plain |
| level list | Exports/The Nightjar_hubList.plist | Papa Sangre_hubList |

## Levels

From the hub list (`altName` is the name the level list shows).

| file | name | playlist includes | objects (besides Player and Room) |
|---|---|---|---|
| nightJar_1 | New Ears | _footsteps_robot | Collectible 1, Sound 6, Surface 3 |
| nightJar_2 | Walk This Way | _footsteps_nightjar_metalhollow | Collectible 1, Sound 5, Surface 4 |
| nightJar_3 | A Brief History of Earth | _footsteps_nightjar_metalhollow | Sound 8 (turning only; OnEnteringShootRange) |
| nightJar_4 | Life Support | _footsteps_nightjar_metalsolid | Collectible 2, Sound 4, Surface 1 |
| nightJar_5 | Behind You | _footsteps_nightjar_metalsmall | Collectible 2, Sound 3, Surface 2 |
| nightJar_6 | Creep | _footsteps_nightjar_metalsolid | Collectible 2, Monster 1, Sound 4 |
| nightJar_7 | Dark Matters | _footsteps_nightjar_metalsolid | Collectible 2, Path 1, Sound 5 (one follows the path and kills), Surface 1 |
| nightJar_8 | Human Waste | _footsteps_nightjar_hotwater, metalsolid | Collectible 3, Monster 1, Sound 4, Surface 8 |
| nightJar_9 | Green Eggs and Slime | _footsteps_nightjar_guts, metalbridge | Collectible 5, Monster 1, Sound 4, Surface 2 |
| nightJar_10 | Trust Nothing | _footsteps_nightjar_metalsolid | Collectible 3, Monster 1, Sound 4 |
| nightJar_11 | Deep Space | _footsteps_nightjar_metalspacewalk | Collectible 4, Monster 1, Sound 5 |
| nightJar_12 | Exit Pursued by an Alien | _footsteps_nightjar_ladder | Collectible 1, Monster 1, Sound 6 |
| nightJar_13 | A Jar of Dark | _footsteps_nightjar_metalspacewalk | Collectible 3, Monster 2, Sound 5, Surface 1 |
| nightJar_14 | Choose Death | _footsteps_nightjar_metalspacewalk | Collectible 2 (the two exits), Sound 5, Surface 4 |

## Defects in the original level data

Reproduced as no-ops or silences, as the original behaves. Evidence in
docs/notes/M0_NOTES.md.

1. nightJar_3 Room `foostepsPrefix` typo - no footstep prefix (walking is never enabled there).
2. nightJar_4 posts `easteregg_flies_away` as a message - nothing observes it.
3. nightJar_6 Player `OnTrip` posts `prompt_d_lvl5_i` as a message - the line never plays.
4. nightJar_6 hint list names `prompt_d_lvl6_c`, not in level 6's playlist - silent.
5. nightJar_7 / nightJar_9 hint lists name `prompt_d_lvl7_e_alt` / `prompt_d_lvl4_e_alt` - no such files.
6. nightJar_9 hint lists name `prompt_d_lvl8_e`, declared in no playlist - silent.
7. nightJar_10 Room `tripSound=foot_metalsolid_run` - no such sound (file is `trip_metalsolid_run`).
8. nightJar_5 Room `shuffleSound=foot_stone_01_dry_shuffle` - no such sound.
9. nightJar_12 `Atmos_CorridorPassage` soundList case differs from the playlist's `Atmos_corridorpassage`; both lookups are case-sensitive (checked at M4), so it is silent in the original too.
10. nightJar_13 `note2` uses `OnCollect`, not an engine trigger - the hint list never changes after note 2.
11. nightJar_13 `exit` names itself as `nextCollectible` - no effect: the exit has no collectSound, so the collect never ends and nothing is activated.
12. nightJar_2 / 9 / 12 activate agents that do not exist (`LVL2_1C`, `note1`, `easteregg_mechsweepb_01_dry`).
13. nightJar_9 `wrigley1` has an empty `defaultSound`.
14. nightJar_2 `LVL2_2E` Sound has an empty `soundList` (which the engine would turn into `anySoundWihPrefix:@""`, any sound at all) - but nothing activates it; the line plays as the exit's `collectSound`.
