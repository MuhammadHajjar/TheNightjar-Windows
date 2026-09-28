# M0 - inventory and feasibility (2026-09-26)

Everything here was checked against the extracted bundle and the binary, not
taken from the brief. Tools that produced each fact are named so it can be
re-run.

## The archive

* `nj.ipa` (the decrypted iOS archive), 52,525,294 bytes, SHA-256
  `20998478eeb3420928b07e69e3ec1d95c8dd30a9236db4c089b3e46447bf9365`, 877 zip
  entries. Read only; extracted with Python's zipfile into `reference/`.
* `reference/Nightjar_arm64` is a byte copy of `The Nightjar.app/The Nightjar`
  (3,312,608 bytes) for the tools.

## Section 3 of the brief, checked

| claim | result |
|---|---|
| 52.5 MB, `The Nightjar.app`, display name "The Night Jar", bundle id `com.ernesto.thenightjar`, version 1.0, iOS 7+, SDK 9.2 | **true** (Info.plist). `Info2.plist` / `nightjar-Info.plist` are leftovers of Somethin' Else's own 1.3.498 build (`com.somethinelse.nightjar`) and are not what runs |
| decrypted, thin arm64, 3.3 MB | **true**: `cryptid 0`, cputype arm64, no fat header (machoinfo.py) |
| Papa Engine 1_1_020, same as PS1 | **stronger than that - it is the same program.** See "The binary" below |
| IRCAM LISTEN 1050 HRTF at offset 1322068, byte-identical to PS1's `embedded_hrtf.dat` | **true**: found at file offset 1322068 (vm 0x100142c54), 1,541,427 bytes, equal to both earlier ports' copies |
| 14 levels `nightJar_1..14`, hub list `The Nightjar_hubList.plist` (14 entries) | **true** |
| hub list picked by app name | **true**: `appName` = `displayNameAtPath:(bundlePath)` minus `.app` (`-[PGEGameParameters init]` 0x10002af40), so "The Nightjar" |
| Exports/ also carries PS1 and PS2 prototype maps | **true**: `Exports/Papa Sangre` (27 maps), `Exports/PapaSangreII` (9 maps + a .tmx). Nothing in this app loads them: every `LoadLevelWithName` in the 14 levels names a `nightJar_N`, `getLastPlaylist` / `lastUnlockedLevel` start from `nightJar_1` for this app name, and the level list comes from the Nightjar hub list only |
| 104 playlists | **true** (54 of them are PS1/PS2 leftovers or shared footstep banks) |
| 326 files in nightjar_sounds, 36.7 MB | 326 **entries**: 317 files in 8 folders plus `hitwall.m4a`. 314 m4a, 1 wav, and 2 Sound Forge peak files (.sfk, .sfap0) |
| UI sounds click_button / back_button / start_button / whoosh Med, VO_turnon / VO_turnoff / VO_turnoff_level1 | present. **The three VO_ prompts are never played** (below) |
| `_nj` nibs are this game's | **true**: `getNibName` appends `_nj` when appName is "The Nightjar" (PGEViewController, Win, Lose, Adios, Credits, HubSelector, StepsAndSwipe, MoreGames, GameOver) |
| 5 Gum intro video | present, 8.0 s. **Never played** (below) |
| EIGC_Users.plist holds credentials | a 40-entry dictionary; contents not printed or copied anywhere. In `.gitignore` from day one (tested: excluded even inside a committed folder) |

## The binary

`tools/psdis.py` over the whole binary (dis/all.txt, 2726 methods), then
`bindiff.py`'s normaliser over every method of both binaries, not only PGE/S3D:

* **2718 of 2726 methods are identical** to Papa Sangre 1's binary after
  normalisation. The same method list, in the same order, 16 bytes apart.
* The other 8 differ only by data: the Jenkins build path
  (`workspace/nightjar-app-appstore/nightjar1/...` against
  `.../papasangre-app-appstore/papasangre1/...`) and string-table addresses
  (`S3DEngine quietLog:format:`, SBJson x3, Flurry crash reporter x4).
* String differences: the bundle id and a few Flurry keys. Nothing else.

So The Nightjar and Papa Sangre 1 are **one engine build**, and the game-specific
behaviour is chosen at run time by `appName`. The PS1 port's recovered engine
applies instruction for instruction. Every app-name branch in the binary
(the only code that behaves differently here):

| method | what The Nightjar does |
|---|---|
| `-[PGELevel initSoundEngine]` 0x10002c9c0 | distanceScale **0.015625** (PS1: 0.008) |
| `-[PGEGameProgress lastUnlockedLevel]` / `getLastPlaylist` | first level `nightJar_1` |
| `-[PGEViewController showSplashScreen]` 0x10003d784 | plays `nightjar_sounds/splash/papa_engine_splash.wav` through `playUiSoundWithName:` |
| `-[PGEViewController viewDidLoad]` 0x10003e7d8 | menu background animation, then `preloadMenuAtmos` |
| `getNibName` (9 view controllers) | `_nj` nibs |
| `-[PGEStepsViewController displayHeadphonesImage]` / `displayFullScreenImage:` | NJ artwork only |
| `-[PGEMenuHubViewController viewDidLoad]`, hub `scrollViewDidScroll:` | NJ padlock artwork |
| `-[CreditsViewController viewDidLoad]` 0x100047840 | Cast / About / Credits scroll images; the cast list is set as an accessibility label (text in the binary) |
| `-[AccessibleAllLevelsViewController tableView:cellForRowAtIndexPath:]` | NJ level rows |
| `MoreGamesViewController`, `PSAppDelegate` | cross-promotion and startup, no gameplay |

The menu atmosphere (`-[PGEngine preloadMenuAtmos]` 0x100036c44) is every sound
in the furthest level's playlist whose upper-cased name starts with `ATMOS` -
the same code as PS1, fed Nightjar's playlists.

## Constants the PS1 port has wrong

Re-read with the fixed psdis.py, confirmed from the raw bytes:

* `-[S3DEngine setReverbRoomSize:]` clamps to **[0.01, 2.3]** (0x1002bb334 =
  0.01, 0x1002bb340 = 2.3). The PS1 port's engine.py says [2.2, 2.3] and runs
  room size 2.2; the real value is the 2.1 that `-[PGEngine init]` passes.
* The Surface defaults in `createObjectFromDict:` are runBPM **180**
  (0x100141d1c) and tripBPM **280** (0x100141d24), as the PS1 port has them.
  (The PS2 notes said a PS1 constant read 350 instead of 280; it is not this
  one. M1 re-reads every Surface/Player default before trusting any.)

## Level data (tools/level_survey.py, level_dump.py, audit_ps1port.py)

14 levels, one layer each ("Level Layer", no ToolBar), 162 objects: Sound 68,
Collectible 31, Surface 26, Room 14, Player 14, Monster 8, Path 1; 267 triggers.
Smaller and simpler than PS1's 27 levels (no Dilemma, no NPC).

Everything the Nightjar levels use that **no PS1 level ever used** - engine code
the PS1 port has never been exercised on. Each is in the binary and each needs
reading before it is trusted:

| feature | where | PS1 port |
|---|---|---|
| bare `EnableWalk`, `DisableWalk`, `EnableRotation`, `DisableRotation`, `DisableHands` (PS1 wrote them with the `PGE_MESSAGE_` prefix) | every level | parser prefixes bare names; verify |
| `PlaySpatialSoundOnAgentWithName` | 8 | in agent.py, never run |
| `OnTrip` on the Player | 6 (its statement is broken, below) | wired, never run |
| `OnExit` on a Surface | 8 | wired, never run |
| `OnLoad` on a Sound | 7 | wired for monsters |
| a **Sound** agent with `speed` / `chaseSpeed` following a Path (`FollowPathWithName` from its `OnLoad`) - the "dark matter" that kills on contact | 7 | paths built for monsters |
| `collideRadius` on a Collectible | 9 | KVC, in the settable list |
| `shuffleSound` / `tripBPM` / `tripSound` on the Room | 1, 2, 4-8, 10, 11, 13 | Room is a Surface in the port; verify |
| `OnEnteringShootRange` on Sounds, with only turning enabled | 3 (the listening tutorial) | one PS1 use |
| two endings: two doors, `Outro_A` / `Outro_B_Death_Reigns`, both `PresentAdiosVC` | 14 | PS1 had one |

No object type, property or message is unknown to the engine (audit: 0 unknown
properties), apart from the data defects below.

### Genuine defects in the original level data

To be reproduced as the original behaves (listed in GAME_STRUCTURE.md; the ones
that silence a recorded line are questions for Muhammad when that level's
milestone comes):

1. **nightJar_3** Room: `foostepsPrefix` (typo). No setter matches, so the
   room has no footstep prefix - harmless, walking is never enabled there.
2. **nightJar_4** `note1`'s activation list posts `easteregg_flies_away` as a
   *message* (meant `ActivateAgentWithName:name=easteregg_flies_away`); nothing
   observes it.
3. **nightJar_6** Player `OnTrip`: `prompt_d_lvl5_i` as a message (meant
   `PlaySound:soundName=...`). The line is declared in level 6's playlist and
   never plays.
4. **nightJar_6** Room inactivity list names `prompt_d_lvl6_c`, which level 6's
   playlist does not declare - silent there (it is heard in level 13).
5. **nightJar_7** inactivity list names `prompt_d_lvl7_e_alt` and
   **nightJar_9** names `prompt_d_lvl4_e_alt`: no such files (the real files are
   `prompt_d_lvl7_e` and `prompt_d_lvl4_e`). Silent.
6. **nightJar_9** inactivity lists name `prompt_d_lvl8_e`, declared in no
   playlist. Silent.
7. **nightJar_10** Room `tripSound=foot_metalsolid_run` - no such sound (the
   file is `trip_metalsolid_run`). Silent trip.
8. **nightJar_5** Room `shuffleSound=foot_stone_01_dry_shuffle` - no such sound.
   Silent shuffle.
9. **nightJar_12** `Atmos_CorridorPassage` sound agent's soundList is
   `Atmos_CorridorPassage`; the playlist declares `Atmos_corridorpassage`. The
   engine matches names with `hasPrefix:` (case-sensitive,
   `-[S3DPlayList anySoundWihPrefix:]` 0x1000d3870), so the level's corridor
   atmosphere is **probably silent in the original** (level 9 names the agent
   the same way but spells its soundList correctly). To verify in the lookup
   path before deciding.
10. **nightJar_13** `note2` uses `OnCollect`, which is not a trigger the engine
    knows (its trigger names: OnActivate, OnButtonPressed, OnCollide,
    OnDeactivate, OnDeath, OnEnter, OnEnteringShootRange, OnExit,
    OnExitJumping, OnExitNotJumping, OnLoad, OnPathEnd, OnRun, OnShoot,
    OnShootMissed, OnSoundEnd, OnStart, OnStartToRun, OnStep, OnTrip,
    OnWallCollide, OnWallCollision). The hint list never changes after note 2,
    so `prompt_d_lvl12_a` is never heard.
11. **nightJar_13** `exit` has `nextCollectible=exit` (itself). Effect to check.
12. **nightJar_2** exit activates `LVL2_1C`, **nightJar_9** activates `note1`,
    **nightJar_12** activates `easteregg_mechsweepb_01_dry`: no agents by those
    names; no-ops (LVL2_1C is also played by a PlaySound, so it is heard).
13. **nightJar_9** `wrigley1` has an empty `defaultSound`.

## Sounds (tools/inventory.py)

* Every declaration in the 14 level playlists (and their footstep includes)
  resolves to a shipped file, exactly - no missing files, no case-only matches.
* 36 audio files are declared by no Nightjar level playlist: the UI sounds and
  splash (played by code), `advertisement/AD_Demo.m4a` (the Audio Defence
  advert playlist), 18 alternate `foot_metalhollow_01_dry_*` takes and 2 more
  foot files, `foot_stone_shuffle`, `Atmos_systemsroom_orig`, three
  `easteregg_toysqueak`s, a duplicate `monsters/LVL11Aware`, and speech.
* **Recorded speech the original never plays** (static reading; confirmed per
  level later with an unused-speech tool like PS2's):
  `prompt_d_lvl3_a`, `prompt_d_lvl3_b`, `prompt_d_lvl3_d 2`, `prompt_d_lvl7_e`,
  `prompt_d_lvl8_e`, `prompt_d_lvl5_i`, `prompt_d_lvl12_a`. Transcripts in
  build/transcripts/medium.en.json. Wiring any of them in is Muhammad's call.

## Never played by this binary

Searched the whole binary (strings, CFStrings, selectors), every nib, and every
data file. The only file that names them is `_CodeSignature/CodeResources`:

* `WR118313_5Gum_INTRO_002-H264_16x9.m4v` (8.0 s, the 5 Gum sponsor intro).
  MediaPlayer.framework is not linked, nothing references AVPlayer or
  MPMoviePlayer, and no code or nib names the file. The original never shows
  it.
* `VO_turnon.m4a`, `VO_turnoff.m4a`, `VO_turnoff_level1.m4a` (2.3 s, 4.3 s,
  8.3 s). Also shipped in PS1's bundle; unreferenced in both.

The About page (`NJ_about_scroll.png`, an image with no accessibility text) is
5 Gum's product copy and social links, not information about the game. The
Cast list is real text in the binary; the Credits are an image plus text.

## Screens and controls (tools/nib.py, build/nib_texts.txt)

* Main menu (`PGEViewController_nj`): Begin, Levels, Cast, Credits, About (+ a
  Continue button, and other games).
* Level list (`PGEHubSelector..._nj`, `AccessibleAllLevelsViewController`):
  Previous, Next, Main Menu ("Go back to the main menu").
* In game (`PGEStepsAndSwipeViewController_nj`): Footstep Left, Footstep
  Right, Navigation Wheel, Skip; pause: Continue game, Restart Level, Quit game.
* Win (`PGEWinViewController_nj`): Continue ("Continue to the next level"),
  Play this again, Main menu. Lose: Retry ("Play the level again"), Main Menu.
  End (`PGEAdiosViewController_nj`): Play this again, Main Menu.
* Hands, jump and swim are never enabled by any level (DisableHands in all 14,
  EnableHands 0), so the controls are PS1's: two feet and turning.
* Accessible announcement in the binary: "Wear headphones. Triple tap the top
  half of the screen to pause."

## Transcripts

`tools/transcribe.py` (faster-whisper medium.en, CPU, 2727 s) over everything
that could hold speech: 170 files (all of nightjar_sounds except footsteps, the
VO prompts, the advert, the video). Output with segment times in
build/transcripts/medium.en.json. Non-speech files come back empty or with
whisper's stock hallucinations ("Thanks for watching!"); whisper also mishears
names ("night job" for Nightjar). Check by ear before quoting a line.

* **The 5 Gum video has no audio track** - one h264 video stream, 8.04 s,
  nothing else. There is nothing in it a player could hear.
* The VO prompts are iPhone instructions: "Triple tap home button to turn
  VoiceOver back on", "...to turn VoiceOver off, during level, triple-tap
  screen to pause", and a level-1 version adding "swipe left and right across
  the top half to turn, press the bottom quarters to move your feet".
* `AD_Demo.m4a` is the Audio Defence advert (screams).
* The seven unheard lines:

| file | what it says | where the data meant it |
|---|---|---|
| prompt_d_lvl3_a | "Swipe the top of your screen to turn." | nowhere (level 3 has no hint list) |
| prompt_d_lvl3_b | "I'm not letting you out of here until I can see you can turn." | nowhere |
| prompt_d_lvl3_d 2 | "You need to turn 180 degrees, alright?" | nowhere |
| prompt_d_lvl5_i | "Don't run too fast!" | level 6, when you trip (broken OnTrip) |
| prompt_d_lvl7_e | "Take care when there is dark matter spraying around." | level 7 hint list (named `_alt`) |
| prompt_d_lvl8_e | "We're going to need to torch the hatching eggs. If they hatch, you won't outrun the babies." | level 9 hint lists (never declared) |
| prompt_d_lvl12_a | "Make sure the airlock sensor's directly in front of you and take care." | level 13 hint list after note 2 (broken OnCollect) |

Also silent where named, though heard elsewhere: prompt_d_lvl6_c "When you've
got the sensor, get out of there." (level 6 hint list; heard in level 13).

**Lines that name a touch control** (they get a spoken PC version after them,
as in PS2): prompt_d_lvl1_a "Touch the bottom left-hand side of your screen
now. Step. Touch the bottom right of your screen. Step.", prompt_d_lvl1_b "Walk
with your thumbs on the bottom half of your screen.", prompt_d_lvl4_a and
prompt_d_lvl5_a "Swipe the top of your screen to turn." (and the unused
prompt_d_lvl3_a). The long cutscenes (cutscene_friday3, LVL1_cutscene2c) are
checked line by line in M2.
