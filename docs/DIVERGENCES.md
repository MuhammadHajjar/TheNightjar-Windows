# Divergence register

Every way the Windows port differs from the iOS original, and every place it
reproduces something odd on purpose. The engine is the same build as Papa
Sangre 1's, so entries inherited from that port name the PS1 entry they come
from.

## INVENTED - must stay empty

Nothing.

## MISSING - the original does it, the port does not

Nothing known.  (Re-checked for all 14 levels at M4, 2026-09-27: every level
played to its end by the autopilot, on the simulator and on the built exe.)

## N/A - no meaning on a PC

| what | evidence |
|---|---|
| `WR118313_5Gum_INTRO_002-H264_16x9.m4v`, the sponsor intro | never played by the original (no code, nib or data names it), and it has **no audio track** - 8 s of silent video (M0) |
| `VO_turnon.m4a`, `VO_turnoff.m4a`, `VO_turnoff_level1.m4a` | never played by the original, and they are iPhone VoiceOver instructions ("triple tap home button...") (M0) |
| Flurry telemetry, EIGC networking, the Audio Defence advert, More Games web view | no audio or gameplay consequence |
| Blind intro, Skip ping, Skip explanation, Shake sound (Papa Sangre II's settings) | The Nightjar has no blind_ takes, no skip ping (`showSkipButton` 0x10000fb18 plays nothing) and no shaking |
| `disableReverb` on old hardware (`-[PGEngine init]`) | a phone-age hardware check |
| Hands, jump, swim controls | no Nightjar level enables them (`DisableHands` in all 14, the rest never named) |
| The 5 Gum About page (`launchAbout:`, `NJ_about_scroll`) | wired to no button in the Nightjar nib - the About button opens the More games page instead (M2) |
| The Audio Defence advert after the splash (`checkForAdvertisement`) | an App Store promotion |
| The More games page's live web version (`startWebViewLoad`) | the local page it falls back to is what the port reads |

## PORT-SIDE - the port's own mechanism for an original behaviour

| what | why |
|---|---|
| Reverb: OpenAL EFX fitted to the recovered Freeverb by measurement (`tools/measure_reverb.py`; `EFX_ENERGY_MATCH` 0.9713 for the game's one room) | the original's CSL Freeverb is not available on a PC; level within 0.00 dB mean, decay within 15 %; +-3.5 dB with direction |
| HRTF: the recovered IRCAM 1050 table built to .mhr (makemhr, `-e off`) | OpenAL Soft's HRTF format |
| Positioned sounds folded to mono (the average of the two channels) | OpenAL only spatialises mono, and every Nightjar file is stereo; which channel the original's spatialiser took is not recovered |
| Flat sounds through `AL_DIRECT_CHANNELS_SOFT` with a two-channel buffer (a mono file at 0.5 per ear) | the original's `setupPlain` panner; OpenAL would otherwise put them through the HRTF |
| Level sounds decoded when the level loads | the original streams on its own audio thread; decoding on first play stalled the game clock |
| Game time advances in 10 ms steps carrying the remainder, level tick every 0.1 s | the original's timers, on a clock that keeps pace with the sound |
| Master volume (Page Up / Page Down, on every screen, 2 dB a press), default 1.0 | no counterpart (the phone's own volume); unity because the narration is mastered to 0 dBFS.  Menus too since M4, at Muhammad's request ("like PapaSangre"); the controller's d-pad left/right only navigates in a menu |
| A level's listeners are dropped when it goes (`MessageBus.scope`, `Game.unload`) | the original deallocates the level, its agents and its player, and their `dealloc` removes their observers; without this each old player kept walking in its old map (M3 report: invisible walls, a doubled shuffle) |
| Keyboard, controller, turn rate | the original was a touchscreen |
| Settings (volume, turning speed, PC instructions, check for updates, keys, controller buttons), Quit, Select Level and Quit after a level, Quit to Windows on pause | a PC needs them |
| The Mac build: Quit to the desktop on pause; speech through VoiceOver; progress in `~/Library/Application Support/The Nightjar`; updates are looked for and announced, not installed | a Mac app is signed, and changing its files from inside breaks the signature; a quarantined app may run from a read-only copy |
| Escape on the win, lose and end screens is Main Menu (back sound) | house standard: Escape backs out |
| "That level is locked." when a locked level is chosen | the original's row does nothing, silently |
| The screens' titles spoken ("You're through but you're not safe yet", "0 human life-forms detected", "The End", "Paused") | the original's words, but in pictures VoiceOver could not read |
| About: the version first and a PC note with the keys last; the page's capitals set in ordinary case | house standard; the words are unchanged (a test holds them) |
| Credits read as "role: names" a row at a time | house standard; the original's accessibility value is one long text |
| The PC version of each line that names a touch control, after the line (Settings: PC instructions) | house standard; the recordings describe the phone |

## FAITHFUL BUT ODD - reproduced on purpose

The level data's own defects are listed in GAME_STRUCTURE.md; each is
reproduced as the original behaves unless Muhammad decides otherwise.

| what | evidence |
|---|---|
| An enemy takes an alert while it is switched off, and acts on it once switched on | `alertEnemy:` has no active test (0x10001e0ec); `update:` has (0x10001d0d8).  Level 12's monster is set on you by its own `OnLoad` during the intro.  The PS1 port dropped alerts to inactive enemies |
| Level 8's exit plays its door-opening sound over the start of the ending line | the exit's `collectSound` (Door_pneumatic_collect) follows its `OnCollide` (ShutDownLevel spares the sender); Seth asked for it gone, Muhammad kept it (decision 9) |
| Levels 9, 10 and 11 as designed: level 9's door appears about 16 steps from the last egg, level 10's monster never moves unless you fall, level 11 starts 5 steps from the first clamp | the level data (Seth's beta report asked about each) |
| Level 12's corridor atmosphere is silent | the data says `Atmos_CorridorPassage`, the playlist `Atmos_corridorpassage`; both lookups are case-sensitive (`S3DSound:` compare: 0x1000d607c, `anySoundWihPrefix:` hasPrefix: 0x1000d393c).  Level 9 plays it |
| A monster's sound keeps whatever spatial flag its playlist gives it | `playSound:looping:` has no `setSpatialized:` (0x10001e844) |
| A line can be skipped only once it has been heard to the end | `canSkipSound:` in `createSpatializedSound` and `onDoubleTap` |

## REQUESTED - Muhammad's decisions

| # | date | what | from |
|---|---|---|---|
| 1a | 2026-09-26 | Feet step on key-down (the original steps on release, `footButtonReleased:`) | PS1 port 4c "Feet step on key-down" |
| 1b | 2026-09-26 | `updateBPMCounter` divides by the number of gaps, not stamps (0x100025d74 divides by `[walkTimes count]`) | PS1 port 4c "The tempo reading is your tempo" |
| 1c | 2026-09-26 | An enemy alerted to a noise holds state 4 until its scheduled second has elapsed (0x10001da90), so the snarl is heard | PS1 port 4c "An enemy alerted to a noise snarls for a full second" |
| 1d | 2026-09-26 | A trip's `AlertAllEnemies` always takes the fresh-alert arm, whatever `hasWantedPosition` says | PS1 port 4c "Going down is always heard" |
| 2 | 2026-09-26 | Every recorded line heard: the seven lines behind broken triggers are wired where the data meant them (BUILD_ORDER decision 2); level 3's three to be decided at M3 | PS2 port decision 21 |
| 5 | 2026-09-27 | Level 3 gets a hint list: its three unused lines (prompt_d_lvl3_a, _b, "_d 2"), every 20 s from the end of the hologram speech (the original's level 3 has no hints) | Muhammad, asked at M3 (decision 2) |
| 4 | 2026-09-27 | No Cast button: the cast list is read inside Credits, under a "Cast" heading after the crew (the original has a Cast button, `launchCast:`) | Muhammad, after playing M2 |
| 6 | 2026-09-27 | No shuffle as a level starts: the last foot you used is forgotten when a level loads.  The original keeps it across levels (`PGEMoveInterpretor` belongs to `PGEngine`), so the new level's `SetControlSettingsToDefault` shuffles whenever your last step was 2 to 99 s before (`updateFeetView:` 0x100008154) | Muhammad, after playing M3: "When I start a level I hear the feet shuffling sounds why, remove that" |
| 7 | 2026-09-27 | No announcement as a level starts.  With VoiceOver on, the original says "Wear headphones. Triple tap the top half of the screen to pause." and loads the level once it has been spoken (`loadDataFromJsonFile:previousLevel:` 0x10002cbb0); the port said it with the PC key | Muhammad, after playing M4: "it's unnecessary" |
| 8 | 2026-09-27 | Level 13's footsteps at gain 1.0, 6 dB over the original's 0.5 (`moveForwardOneStep:`); every other level keeps 0.5.  The spacewalk steps peak about 7 dB under the metal floors before them, under level 13's two loudest atmospheres at once | Muhammad, after playing M4: "in level 13 the steps are so quiet they're like don't exist" |
| 9a | 2026-09-28 | Level 8's growl as you first step in the hot water comes from the monster.  `PlaySpatialSoundOnAgentWithName`'s block never sets a position (0x100021c2c), so the original plays it where that sound last was - the middle of the room, ahead of you | Seth's beta report ("a random monster scream plays in the distance in front of you"); Muhammad chose the data's intent |
| 9b | 2026-09-28 | Level 5: the sensor that shuts the door stops the two floor-strip lines the creature lives in (LVL5b, LVL5c), through a port-only `PGE_MESSAGE_PortStopSound`.  The original has no way to stop them and they run on up to 12 s past the door | Seth: "the door sound should cut off everything else" |
| 9c | 2026-09-28 | The click starts at its first audible sample: click_button.wav opens with 116 ms of silence, which the original plays | Seth: "the UI sounds feel delayed" |
| 9d | 2026-09-28 | Hot water footsteps (level 8) at gain 1.0, 6 dB over the original's 0.5 - the quietest steps in the game | Seth: "the water sounds should be louder" |
| 9e | 2026-09-28 | The main menu's Levels is called Select Level (and so is the list), as in Papa Sangre II | Seth |
| 10 | 2026-09-28 | The main menu's Begin is called Continue (it goes to the furthest level unlocked; the original's handler is `continueButtonPressed:`) | Muhammad |
| 3 | 2026-09-27 | Choosing a level in the level list clicks (the original's `didSelectRowAtIndexPath:` is silent) | the brief's house standard, from Papa Sangre II's tester |
