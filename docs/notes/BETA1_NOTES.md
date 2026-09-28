# Beta round 1 - Seth Gamer's report on 2026-09-27 number 4 (2026-09-28)

Every item was first checked against the original: a port bug is fixed; the
original's own behaviour went to Muhammad (decision 9).

| # | report | finding | outcome |
|---|---|---|---|
| 1 | Level 5: closing the door does not cut the creature off | the creature is inside LVL5b (16.1 s) and LVL5c (21.6 s), played by the floor strips' `PlaySound`; `shutDownLevel:` (0x10003476c) only deactivates agents and the inactivity sound, and the sensor's collect only stops its own beacon - the original plays on | 9b: the sensor's OnCollide stops both (port-only `PGE_MESSAGE_PortStopSound`) |
| 2 | Level 8: a monster scream "in the distance in front of you" on the first step in the water | `PlaySpatialSoundOnAgentWithName` never positions the sound (block 0x100021c2c): Wrigley_aware plays where it last was, the room's middle | 9a: placed on the monster |
| 3 | Level 8: water sounds louder | foot_hotwater is the quietest bank (s1 peak -17 dBFS, loudest 100 ms -33 dBFS; metal floors -10 / -27) | 9d: hot water steps at gain 1.0 (original 0.5) |
| 4 | Level 8: "an unused door open sound" over the ending | the exit's collectSound Door_pneumatic_collect (1.9 s) follows its OnCollide (ShutDownLevel spares the sender) - the original's | kept |
| 5 | Level 9: the door appears too close to the last egg | exit (640,160), egg3 (500,240): 16 steps - the level data | as designed |
| 6 | Level 10: the monster never moves | an enemy moves only when alerted; level 10 alerts only on a fall | as designed |
| 7 | Level 11: you start too close to the first clamp | player (140,430), note1 (110,390): 5 steps - the level data | as designed |
| 8 | Running sounds only near a sprint | decision 1b (tempo = real steps a minute): fast bank at 200, fall at 280; the original's reading is 1.25x high (fast bank at ~160 real, fall at ~224) | kept (Muhammad: "Keep Papa Sangre 1's") |
| 9 | Skipping an intro only works 10-12 s in | **port bug.** The wait is 6.2 s after `wearHeadphonesDate`, stamped by `displayHeadphonesImage` (0x10000f150) on **LoadLevelWithName** (observed at 0x10000eb94): after a win or death that is when the previous level ended (Continue = `loadLevelWithStringName:`, Retry = `reloadCurrentLevel`, neither posts it), from a menu it is the moment of choosing (`initGameplayEngineAndLaunchLevelWithName:` posts it, 0x10003d2f4), so loading counts.  The port timed 6.2 s of game time from each load | fixed: `Game.sitting_now` (game + menu + load time), `show_headphones()`; 4 tests |
| 10 | UI sounds feel delayed | click_button.wav opens with 116 ms of silence (back/start 15 ms, whoosh 34 ms); the original plays it as it is | 9c: the click starts 2 ms before its first sample within 40 dB of its peak |
| 11 | Levels should be Select Level | the original's button is Levels | 9e: Select Level (menu and list) |

The 10-12 s: load time was not counted (1.2-1.9 s here, likely more on
Seth's machine) and every level restarted the wait; frame cost was ruled out
(under 1 ms at worst on the real engine).
