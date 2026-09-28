# The Nightjar for Windows - build order and journal

The journal of the port: milestone status, every decision with its number and
date, and what was proved. Notes per milestone are in docs/notes/.

## Status

| milestone | status |
|---|---|
| M0 inventory and feasibility | **done 2026-09-26** |
| M1 engine base | **done 2026-09-26** |
| M2 level 1 end to end | **done 2026-09-27** |
| M3 levels 2-5 | **done 2026-09-27** (two bugs reported, fixed in M4) |
| M4+M5 levels 6-14 and the two endings, in one go | **done 2026-09-27** ("everything works great") |
| private beta 1 for Seth | **2026-09-27 number 4** in the Drive folder; report fixed in 2026-09-28 |
| M7 updater, public repo, first release | **released 2026-09-28** |
| M6 the full shell | - |
| M7 folder build, data pack, updater | - |
| beta, release | - |

## M0 - inventory and feasibility (2026-09-26)

Details: docs/notes/M0_NOTES.md.

**Verdict: feasible, and faithfully.** The Nightjar runs the very same engine
build as Papa Sangre 1: 2718 of the binary's 2726 methods are identical to PS1's
after normalisation and the other 8 differ only in build paths and string
addresses. The game is chosen at run time by the app name, and only a dozen
small branches differ (listed in the notes). So:

* the PS1 port's recovered engine is the reference, instruction for
  instruction - nothing has to be recovered twice;
* the PS2 port supplies everything around the engine: audio engine (with the
  flat-sound fix), clock, menus, settings, controller, pack, updater, tests;
* all the game content (14 levels, their playlists and sounds) is data the
  engine already reads.

Nothing found that cannot be done faithfully. The original never plays the 5
Gum video (which has no audio track anyway) or the three VoiceOver prompts
(iPhone instructions); both are N/A. Seven recorded hint lines sit behind
broken triggers and are never heard; whether to hear them is Muhammad's call.

Proved in M0:

* archive hash recorded, ipa untouched, extracted copy in reference/;
* every fact in section 3 of the brief checked (one correction: 317 sound files
  in 326 entries);
* whole-binary disassembly, class dump, strings; method-by-method comparison
  with PS1's binary;
* the HRTF found at the stated offset and byte-identical;
* level survey, PS1-port content audit over this game's data (0 unknown
  properties), sound inventory (every declaration resolves), 13 data defects
  listed;
* EIGC_Users.plist excluded by .gitignore, tested.

Carried forward as work, not decisions:

* the PS1 port's reverb room size is misread (2.2; the binary clamps to
  [0.01, 2.3], so 2.1 stands) - the Nightjar port uses the binary's value;
* engine paths the PS1 levels never exercised and the Nightjar levels do
  (table in the notes) get read in the binary before the PS1 code is trusted.

## M1 - engine base (2026-09-26)

Details: docs/notes/M1_NOTES.md.

**Built.** `nightjar/` = the PS2 port's infrastructure (audio, bus, input,
speech, util, shell, updater, simulator) + the PS1 port's engine (the same
binary), with the sound agent and collectible rewritten from this binary and
the level clock, load order, hint timer, win/lose and UI sounds recovered.
`Run\The Nightjar.exe` opens with the splash and plays level 1.

**Gate proved:** the built exe self-tested from a clean folder - HRTF enabled
with the recovered table, NVDA speech, game time 20.0 s in 20.0 s, level 1
loaded and speaking.  73 tests; content check 0 unexplained of 17 findings.

Found along the way (all logged): the level ticks at 0.1 s, not per frame;
a sound starts 0.05 s after its agent activates; collectibles never fire
`OnActivate`; sensors, doors and monsters re-mix their reverb from their
distance; monster sounds keep their playlist's spatial flag; a sound played
"on" an agent is not moved to it; hints wait for a time to be set and restart
while one plays; skipping needs the line heard before; the PS1 port's reverb
room size (2.2) is wrong; the default volume is unity because this game's
speech is mastered to 0 dBFS.

## M2 - level 1 end to end, with its menus (2026-09-27)

Details: docs/notes/M2_NOTES.md.

**Built.** Main menu (Begin, Levels, Cast, Credits, About, Settings, Quit),
the level list, Cast / Credits / About read a row at a time, Settings with key
and controller rebinding, the pause screen, the win / lose / end screens -
every label from the `_nj` nibs and every UI sound from its button's handler -
the menu atmosphere, and the spoken PC version after the lines that name the
touch screen.  Autopilot wins level 1 on five seeds.  103 tests.

Found: Nightjar's About button opens the More games page (an About
paragraph, More games, Technology), not the 5 Gum About screen, which no
button reaches; the screens' titles exist only as pictures; the menu
atmosphere fades in over 0.5 s to full gain.

## M3 - levels 2 to 5 (2026-09-27)

Details: docs/notes/M3_NOTES.md.

**Built.** Levels 2 to 5 play through; the autopilot wins each on five seeds;
135 tests.  Found: a floor strip with no trip speed gets 350, not 280 (the
Papa Sangre 1 port's misread, fixed here and flagged for that port); only
walking resets the hint clock.

## M4 + M5 - levels 6 to 14, both endings (2026-09-27)

Details: docs/notes/M4_NOTES.md.  Done as one milestone at Muhammad's request
("the game is too short so let's finish it in one go").

**Built.** Every level plays to its end: the autopilot now plans a route
around anything deadly, crosses alarm floors far from the monster and hurries
when something is coming, and wins all 14 levels on five seeds (120 more runs
of levels 6-13 lost none), both endings of level 14 included.  The built exe,
from a clean folder, finishes levels 6-14 and both endings by itself on the
real audio device (`--autoplay`), game time keeping pace with the wall clock.
199 tests.

Fixed from the M3 report: a level's listeners outlived it (old players kept
stepping in their old maps - the wall at level 5's start, and a doubled
shuffle); the shuffle as a level starts is gone (decision 6); Page Up / Page
Down work on every screen.

Found: an enemy takes an alert while switched off (level 12's monster is set on
you by its own OnLoad; the PS1 port dropped it, so the ladder chase never
happened); the Nightjar binary is the PS1 binary moved 0x10 bytes, and 65
addresses carried over from the PS1 port were corrected
(tools/ps1_addresses.py); level 12's corridor atmosphere is silent in the
original too (case-sensitive lookup).

## Milestone plan

Each milestone ends with a Run\ build Muhammad plays, tests, and a go/no-go.

* **M1 - engine base.** New package `nightjar/` in PS2's layout. From PS2:
  core (bus, the 10 ms pump with the carried remainder, triggers), audio
  (OpenAL binding, S3D engine with flat sounds kept out of the HRTF and stereo
  folded to mono for the spatialiser, recovered Freeverb, bank handing out one
  object per name), input, accessibility, util, sim. From PS1 (same binary):
  player, move interpreter, level/surfaces, collectible, sound agent, monster,
  paths - each method checked against dis/all.txt with its address in a
  comment. Nightjar branches (distanceScale 0.015625). Reverb refitted by
  measurement for room size 2.1 / dampening 5. Loopback render tests.
  *Gate: nightJar_1 loads and speaks in Run\.*
* **M2 - level 1 end to end** with the first menus (main menu, pause, win and
  lose screens), autopilot, self-test, Run build.
* **M3 - levels 2-5**: walking, the listening tutorial (level 3 turns only and
  uses shooting range), first sensors and doors, hint lists, room trips.
* **M4 - levels 6-9**: the first monster, the dark matter on a path (7), hot
  water that alerts and a sound played on the monster (8), the eggs (9).
* **M5 - levels 10-14**: the ladder chase, two monsters (13), the two endings
  and the end screen (14).
* **M6 - the full shell**: settings, keys, controller buttons, Cast / Credits /
  About, PC instructions for the tutorial lines, splash and menu atmosphere,
  UI sounds audited against every `playUiSoundWithName:` caller.
* **M7 - folder build, encrypted data pack, privacy scan, self-updater**, each
  proved (verify_updater offline and live).
* **Beta** in the Drive folder for Seth, then **release** only when Muhammad
  says.

## Decisions

**Gate M0 -> M1 (2026-09-26):** go.

**Gate M1 -> M2 (2026-09-27):** go - Muhammad played the M1 build: "absolutely works great".

**Decision 1 (2026-09-26): the four engine changes from Papa Sangre 1 carry
over.** Same engine, same choices (PS1 port DIVERGENCES 4c): feet step on
key-down; the tempo reading divides by the gaps, so a `tripBPM` means real
steps per minute; an enemy alerted to a noise holds state 4 for the second it
scheduled, so the snarl is heard; a trip's alert always takes the fresh-alert
arm (snarl, wind-up, chase). Each is REQUESTED in DIVERGENCES.

**Decision 2 (2026-09-26): every recorded line is heard, as on Papa Sangre II
(its decision 21).** Each line the original leaves unheard goes where the level
data shows it was meant to go: `prompt_d_lvl5_i` on a trip in level 6,
`prompt_d_lvl6_c` in level 6's hint list, `prompt_d_lvl7_e` for level 7's
`_alt`, `prompt_d_lvl8_e` in level 9's hint lists, `prompt_d_lvl12_a` after
level 13's note 2. The three level 3 turning lines (`prompt_d_lvl3_a`, `_b`,
`_d 2`) have no place in the data: ask Muhammad at M3. A test asserts no line
is left unheard.

**Gate M2 -> M3 (2026-09-27):** go.

**Decision 4 (2026-09-27): Cast is read inside Credits.** The main menu has
no Cast row; Credits reads the crew list, then a "Cast" heading and the cast
list.  (The original has a Cast button of its own, `launchCast:`.)

**Decision 5 (2026-09-27): level 3's three unused turning lines are its
hints.** "Swipe the top of your screen to turn", "I'm not letting you out of
here until I can see you can turn", "You need to turn 180 degrees, alright?",
in turn, from 20 s after the hologram speech; the first is followed by the PC
keys.

**Gate M3 -> M4 (2026-09-27):** go, with two bugs to fix first (a shuffle as
each level starts; stuck in a wall at level 5's start), Page Up / Page Down
volume "like PapaSangre", and all the remaining levels in one go.

**Decision 6 (2026-09-27): no shuffle as a level starts.** The original
remembers the last foot you used across levels, so a new level opens with your
feet shuffling whenever your last step was 2 to 99 s earlier.  Muhammad: "When
I start a level I hear the feet shuffling sounds why, remove that."  The port
forgets the last foot when a level loads; the shuffle inside a level is
unchanged.

**Gate M4 -> beta (2026-09-27):** "everything works great", with two changes,
then the beta for Seth.

**Decision 7 (2026-09-27): no announcement as a level starts.** "Wear
headphones. Press Escape to pause." is gone ("it's unnecessary"); the level
loads straight away.  (The original announces it through VoiceOver and waits.)

**Decision 8 (2026-09-27): level 13's footsteps are 6 dB louder** (gain 1.0
where the original has 0.5): "the steps are so quiet they're like don't
exist".  Measured: its spacewalk steps peak about 7 dB under the metal floors
of the levels before, under its two loudest atmospheres together.  Levels 11
and 14 use the same steps and keep the original gain.

## Beta round 1 - Seth's report (2026-09-28)

Details: docs/notes/BETA1_NOTES.md.  Levels 1-4, 6, 7, 12-14 "perfect"; both
endings work.

**Fixed (a port bug):** skipping an intro waited 6.2 s from each level load.
The original starts that wait when the wear-headphones picture goes up - on
the LoadLevelWithName that ends the previous level, or when you choose a level
from a menu - so after the win or lose screen you can usually skip at once,
and from a menu loading counts.  Now the same.

**Decision 9 (2026-09-28): Seth's requests.** Muhammad took (a) level 8's growl
from the monster, (b) level 5's door cutting off the creature, (c) the click
without its 116 ms silent start, (d) hot water steps 6 dB louder, (e) Select
Level for Levels.  Kept as the original: level 8's exit door sound, and the
running sounds - decision 1b stays ("Keep Papa Sangre 1's"), so the fast
footsteps start at 200 real steps a minute.  Levels 9, 10 and 11 are as the
data made them.

**Decision 10 (2026-09-28): the main menu's Begin is called Continue.**

**Decision 10 is followed by the release (2026-09-28): go.** A new changelog
for players (the development history stays in this journal), the updater,
the public repo and the first release.

## M7 + release - the updater and 2026-09-28 (2026-09-28)

**The updater** is the Papa Sangre II port's (`nightjar/update/`), wired into
the shell the same way: a quiet check when the main menu first opens
(Settings, Check for updates at start), Check for updates on the main menu,
and two answers only, Update now or Not now.  Only the files that changed are
downloaded; the hand-off runs after the game closes, never writes `config/`,
and starts the game again.  The release zip is always
`TheNightjar-Windows.zip`, so
https://github.com/MuhammadHajjar/TheNightjar-Windows/releases/latest/download/TheNightjar-Windows.zip
always gives the newest.

**Proved:** `tools/verify_updater.py`, offline through the real PowerShell
hand-off: a normal update, a server without byte ranges, a file locked for
4 s, a file locked for good (rolled back, the old game started); `--frozen`:
a built 2026-09-27 number 5 exe updated itself to 2026-09-28 from a local
release (2 files, 41 MB of 93 MB, save kept, restarted, 7 s); and live, the
same build updated itself from the GitHub release (38 s, save kept,
restarted).  A fresh clone passes all 210 tests once the HRTF is built.

**Released:** https://github.com/MuhammadHajjar/TheNightjar-Windows, public,
MIT; tag `2026-09-28`, asset `TheNightjar-Windows.zip` (93 MB).  The beta zip
was removed from the Drive folder; Seth's note stays.
