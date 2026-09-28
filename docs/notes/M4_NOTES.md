# M4 + M5 - levels 6 to 14, both endings (2026-09-27)

One milestone at Muhammad's request.  It opened with his M3 report.

## The M3 report

**A shuffle as each level starts; stuck in a wall at level 5's start.**  One
root cause and one faithful behaviour:

* `Game` keeps one bus for the whole sitting, and nothing dropped a level's
  subscriptions when it went.  Every old Level, Player and agent went on
  answering the bus: an old player took each of your steps in its own old
  map, so going from level 4 to level 5 you walked on level 5 while the level 4
  player walked into level 4's wall - two `hitwall`s a step, "stuck inside a
  wall".  The old players also played their own shuffle.  The original
  deallocates all of it and each `dealloc` removes its observers.  Fixed:
  everything a level subscribes (level, agents, player) is made inside
  `bus.scope(key)` and `Game.unload` drops the scope.  Test: listeners stay
  level across loads; level 4 then 5 in one sitting has no wall.
* Even with that, the original shuffles at a level's start:
  `PGEMoveInterpretor` belongs to `PGEngine` (0x1000361a8), so the last foot
  you used survives the level; `lockControls` keeps it; the new level's
  `SetControlSettingsToDefault` runs `updateFeetView:`, which posts
  `PGE_ACTION_Shuffle` when that foot was used 2 to 99 s ago (0x100008154,
  0x10000824c).  In the port game time stops in the menus, so it happened
  every time.  Muhammad asked for it gone: decision 6, the last foot is
  forgotten on load (`MoveInterpretor.forget_last_foot`).

**Page Up / Page Down "like PapaSangre".**  Both Papa Sangre ports have it in
play only; this port had the same.  Now on every screen, with "maximum" and
"minimum" said at the ends, and on the About page.  The controller's d-pad
left/right is both menu left/right and volume; in a menu it only navigates.

## Recovered in M4

* **The Nightjar binary is the PS1 binary moved 0x10 bytes.**  Every class
  (PGE*, S3D*) has the same functions at +0x10; the engine code is
  instruction-identical once addresses are normalised (PGEEnemy, PGEGameAgent,
  PGEPlayer, PGELevel, PGEMoveInterpretor, PGESurface, PGECollectible,
  PGESound, PGEngine: 0 differing instructions).  So the PS1 port's monster
  logic applies unchanged - but its address comments were PS1's.
  `tools/ps1_addresses.py` shows each comment address against both readings;
  65 were corrected (monster 42, player 17, level 4, interpreter 2).
* **An enemy takes an alert while switched off.**  `alertEnemy:` (0x10001e0ec)
  has no active test; `update:` does (0x10001d0d8); `levelInited:`
  (0x10001f940) fires `OnLoad` for every agent, active or not.  Level 12's
  monster alerts itself to you from its own `OnLoad` during the intro, so it
  wakes roaring and climbs after you the moment it is switched on.  The PS1
  port returned early for inactive enemies and the chase never happened.
* All three alert messages go to `alertEnemy:` (`PGEEnemy init` 0x10001cf7c);
  `activateEnemy:` is only `setActive:YES`.
* Level 12's `Atmos_CorridorPassage` is silent in the original too:
  `S3DSound:` compares with `compare:` (0x1000d607c) and
  `anySoundWihPrefix:` with `hasPrefix:` (0x1000d393c), both case-sensitive.
* Level 13's exit naming itself as `nextCollectible` does nothing: the exit
  has no collect sound, so its collect never ends.
* The end screen (`presentAdiosVC` 0x10003c724) does not record progress;
  Play this again = `reloadCurrentLevel` + click, Quit = QuitGameMode + back.

## The levels

| level | what it asks | engine paths |
|---|---|---|
| 6 Creep | past a feeding monster to a sensor 30 px from it, then the door | monster idle; a trip wakes it (decision 1d) and plays "Don't run too fast!" (decision 2) |
| 7 Dark Matters | a sensor and a door either side of the dark matter's track | a Sound on a path from its own `OnLoad`, speed 21.3, `OnCollide` kills |
| 8 Human Waste | across a band of hot water to two sensors and the door | `OnEnter` violin + `PlaySpatialSoundOnAgentWithName`, `OnStep` alerts to position, `OnExit` line |
| 9 Green Eggs and Slime | four eggs; the last wakes the mother and opens the door in the slime | collectible `collideRadius` 25, alerts from a collectible's `OnCollide` |
| 10 Trust Nothing | a door that locks your feet until it has spoken, a sensor, the door | a collectible's `OnSoundEnd` |
| 11 Deep Space | three beacons round a monster in the middle | walking round an idle monster |
| 12 Exit Pursued by an Alien | a ladder, a monster climbing after you | the inactive alert above; no turning |
| 13 A Jar of Dark | two sleeping monsters, two sensors, a door on a floor that wakes both | `afterDelay` 0.5, `OnEnter` alerts to player |
| 14 Choose Death | two doors, two endings | `PresentAdiosVC`, the end screen |

## The autopilot

It plans on a 10 px grid (A*): anything deadly (an `OnCollide` that shuts
the level down, on anything but a collectible) is kept clear by its radius
plus 14 px, and a moving one by the stretch it will sweep in the next 2.5 s;
inside that margin already, only cells farther away are open, so the way out
is always away.  Alarm floors cost more the nearer a monster is, so it crosses
where they are far.  It steps at about 109 BPM, and as fast as the ground
allows (15 % under its trip speed, at most 230 BPM) when a monster is coming,
on an alarm floor, or near a moving hazard.  Each seed has its own rhythm and
reaction time.  Results: all 14 levels on seeds 1-5, levels 6-13 on seeds
6-20 too, both doors of level 14.  `--autoplay level [door]` runs it inside the
built exe.

## Proved

* 199 tests (the autopilot on all 14 levels, both endings, the M3 report's two
  bugs, the menu volume, one test per level mechanism above, and decision 2's hint lines heard by waiting).
* Content check: 14 levels, 17 oddities, all explained.
* `Run\The Nightjar.exe` 2026-09-27 number 3, copied to a clean folder outside
  %TEMP% (build/cleantest) and run with `--autoplay` through PowerShell
  Start-Process -Wait, HRTF enabled on the real device, every run exit 0:

  | level | outcome | game time / wall time |
  |---|---|---|
  | 6 | win -> 7 | 68.8 / 68.9 s |
  | 7 | win -> 8 | 77.7 / 77.7 s |
  | 8 | win -> 9 | 68.5 / 68.6 s |
  | 9 | win -> 10 | 92.6 / 93.6 s |
  | 10 | win -> 11 | 156.1 / 156.1 s |
  | 11 | win -> 12 | 88.5 / 88.5 s |
  | 12 | win -> 13 | 28.4 / 28.4 s |
  | 13 | win -> 14 | 189.9 / 190.2 s |
  | 14 door A | the end | 96.6 / 96.6 s |
  | 14 door B | the end | 74.0 / 74.0 s |

  The second lost on levels 9 and 13 is the autopilot's own planning, not the
  game: on their alarm floors a route takes up to 226 ms to plan inside the
  frame, and the game caps a frame at 0.1 s (measured: about 1.3 s over level
  9; level 12, cheap to plan, loses nothing).
* Muhammad's Run\config hashed before and after every build: unchanged.
