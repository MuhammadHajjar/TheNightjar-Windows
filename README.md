# The Nightjar - Windows port

A faithful port of *The Nightjar* (Somethin' Else, iOS, 2011) to Windows: the
audio-only sci-fi thriller, played entirely by listening. All 14 levels and
both endings; keyboard and controller; screen-reader output; and the
original's own HRTF.

The engine is not a re-imagining. The Nightjar runs the Papa Engine, the same
build as Papa Sangre's (the binary is Papa Sangre 1's, every function 0x10
bytes later), so this port is the original's logic recovered from the arm64
binary and its data: the same maps, the same playlists, the same walking
arithmetic, the same monster state machine. `docs/BUILD_ORDER.md` is the
journal of how each piece was recovered and every decision taken on the way;
`docs/DIVERGENCES.md` lists everything that had to differ and why;
`GAME_STRUCTURE.md` is the recovered structure of the game itself;
`docs/notes/` holds the working notes per milestone.

## Playing

Download the newest release, unzip it anywhere, and run `The Nightjar.exe`
from "The Nightjar" folder. There is no installer. Keep the `_internal` folder
beside the exe: it is the game's libraries. Headphones are a must; the whole
game is binaural.

Your progress and settings are written to a `config` folder next to the exe
(or to `%LOCALAPPDATA%\The Nightjar` when the game cannot write there, for
example when it was started from inside the zip).

The game updates itself. When the main menu opens it looks for a newer
release on GitHub, and the main menu's **Check for updates** asks straight
away. It asks one thing, Update now or Not now. Update now downloads only the
files that changed, then the game closes, puts them in place and starts again
by itself; Not now asks again next time. Your progress is kept. The check at
start can be switched off in Settings.

## Controls

Keyboard, all rebindable in Settings, Keys:

| | |
|---|---|
| A / D | left foot, right foot. Alternate them to walk; a foot you just used waits two seconds |
| Left / Right arrow | turn |
| Enter | select, and skip a scene you have heard before |
| Up / Down arrow | move through a menu; Left / Right change a setting |
| Escape | pause menu, and back out of a menu |
| Page up / Page down | volume, anywhere in the game |

Controller, rebindable in Settings, Controller buttons:

| | |
|---|---|
| Left / Right trigger | left foot, right foot |
| Left stick | turn |
| D-pad up / down | up and down in a menu |
| D-pad left / right | volume. Also left and right in a menu |
| A | select, and skip |
| B, or Back | back |
| Start | pause menu |

Nothing on the keyboard or the pad quits the game: that is Alt+F4, or Quit in
a menu.

## Building

Everything the game runs on is in here: the audio, the Tiled map exports, the
S3D playlists, the level list, the More games page the About screen reads and
the HRTF table. Clone it and build, there is nothing else to find.

    python tools/build_exes.py        the game, into Run\ (exe, _internal, changelog)
    python tools/pack_release.py      the release zip, into dist\

The game is a folder build (PyInstaller one-dir): every sound, level and
playlist travels inside the exe as one encrypted pack, embedded as a Windows
resource, so there are no loose game files. `EIGC_Users.plist`, which the
original bundle carries, is never committed, packed or shipped:
`.gitignore` and `build_exes.py` both refuse it.

The HRTF is not committed in its built form: `build/` is generated. The
committed `tools/embedded_hrtf.dat` is the original IRCAM 1050 set, carved out
of the binary by `tools/extract_hrtf.py`, and `build_exes.py` rebuilds
`build/hrtf/papa_ircam_1050.mhr` from it on a fresh clone with
`vendor/makemhr/makemhr.exe` (from OpenAL Soft's binary release).

The original's arm64 binary is here too, at `reference/Nightjar_arm64`.
Nothing needs it to build or play, but it is the source of truth for the
reverse engineering, and the scripts read it (`capstone` is needed for these):

    python tools/psdis.py . > tools/dis/all.txt    the whole-binary disassembly
    python tools/classdump.py reference/Nightjar_arm64    the classes and ivars
    python tools/fn.py "selector"                  one function out of the disassembly
    python tools/ps1_addresses.py <file>           addresses carried over from the Papa Sangre 1 port

The code cites the disassembly by address throughout. A few of the first
survey tools (`audit_ps1port.py`, `inventory.py`, `level_survey.py`,
`nib.py`) read the Papa Sangre ports' checkouts from beside this one.

## Running from source

Python 3.12+, `pygame-ce`, `numpy`, `av`, and OpenAL Soft (`vendor/openal`).
Speech goes through the NVDA controller client when NVDA is running, SAPI 5
otherwise.

    python apps/play.py                      the game
    python apps/play.py nightJar_8           straight into one level
    python apps/check_content.py             every level's data checked against the playlists
    python -m pytest                         the tests (build once first: the audio tests use the built HRTF)
    python tools/verify_updater.py           the updater, end to end, offline

A built exe checks itself without anyone at the keys:

    "The Nightjar.exe" --selftest nightJar_1       20 s of a level on the real device
    "The Nightjar.exe" --autoplay nightJar_12      the autopilot plays the level to its end
    "The Nightjar.exe" --autoplay nightJar_14 doorB

## Versions

A version is the day it was made, and "number 2", "number 3" when a day has
more than one: `2026-09-28 number 2`. It lives in `nightjar/__init__.py`,
`VERSION` and the newest heading of `changelog.txt`, and a test keeps the
three the same. The release tag is the version without spaces,
`2026-09-28-2`. Every release's zip has the same name,
`TheNightjar-Windows.zip`, so
https://github.com/MuhammadHajjar/TheNightjar-Windows/releases/latest/download/TheNightjar-Windows.zip
always downloads the newest, and it is what the game looks for when it
updates itself. Keep it the only zip on a release. `changelog.txt` ships beside
the exe.

## Layout

    apps/           the game and the content check
    nightjar/
        assets/     playlists, Tiled maps, the level list, the data pack
        audio/      OpenAL binding, the S3D engine equivalent, the reverb, the sound bank
        core/       message bus, the game around the level, triggers
        input/      rebindable key map and controller map, the foot interpreter
        world/      level, surfaces, the requested changes
        entities/   player, sound agent, collectible, enemy
        save/       progress
        shell/      the menus
        update/     the self-updater
        accessibility/  speech
        autopilot.py    a player that finishes every level, for the tests
    tests/          pytest
    tools/          build, packaging, reverse-engineering and audit scripts
    docs/           the journal, the divergences, the notes

## Credits

*The Nightjar* was created by **Somethin' Else**, with the Papa Engine. This
port is not affiliated with them.

Windows port by **Muhammad Hajjar**. Thanks to **Seth Gamer** for testing the
whole game and reporting what differed from the original.

## Licence

The port's own code is MIT, see `LICENSE`. That covers the code in this
repository and nothing else: the original game's audio, maps, script and
trademarks belong to their owners and are here only so the port can be built
and played.
