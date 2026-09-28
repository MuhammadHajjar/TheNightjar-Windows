# M3 - levels 2 to 5 (2026-09-27)

## What the levels are

| level | name | what it asks | engine paths |
|---|---|---|---|
| nightJar_2 | Walk This Way | a 72-step straight walk (turning stays off) past four voice-line floor strips to the door | Room tripBPM 220 and tripSound; strips OnEnter PlaySound |
| nightJar_3 | A Brief History of Earth | turning only: face the beep behind you, then the sensor | `OnEnteringShootRange` (facing within 11.5 degrees) |
| nightJar_4 | Life Support | the first sensor, then the door | collectible chain, hint list changed on collect |
| nightJar_5 | Behind You | a sensor behind two voice strips, then the door | Room shuffleSound (a missing sound: silent) |

## Recovered in M3

* **A floor strip with no `tripBPM` gets 350**, not 280: the Surface branch of
  `createObjectFromDict:` sets 350 (0x100030848, literal 0x100141d20) and only
  the Room gets 280 (0x10002fcc4); runBPM 180 for both.  The Papa Sangre 1 port
  gives every surface 280 (flagged as a separate task for that port).
* **The facing test** (`updateSpatializedSound` 0x100020c68,
  `setIsInShootingRange:` 0x100020f7c): the dot product of the player's facing
  with the direction to the agent above 0.98 and the distance under
  `shootRange` (infinite); `OnEnteringShootRange` only on the change from out to
  in, only while active.  The same call also sets the S3D head position from
  the agent's copy of the player's position.
* **Only walking resets the hint clock** (`playerWasActive` is called from
  `playerMovedToPosition:` alone), so in a turning-only level hints come round
  whatever you do.

## Decision 5 (2026-09-27)

Level 3's three unused lines are its hints: "Swipe the top of your screen to
turn" (followed by the PC keys), "I'm not letting you out of here until I can
see you can turn", "You need to turn 180 degrees, alright?" - declared for the
level, set as its hint list, starting 20 s after the hologram speech (the time
levels 1 and 2 use).  nightjar/world/requested.py, which also carries decision
2's lines for levels 6, 7, 9 and 13 (tested now, heard at M4/M5).

## Proved

* 135 tests; the autopilot (now turning at 120 degrees a second, like a player)
  wins levels 1 to 5 on five seeds each.
* Level 3's hints play in turn when you do not turn, the first 20 s after the
  speech, and stop when the level shuts down; the beep is behind you until you
  turn; running on level 2 trips you with the room's own sound; level 5's
  shuffle is silent (the data names a sound that does not exist).
* `Run\The Nightjar.exe` (2026-09-27 number 2) self-tested from a clean
  folder on levels 3 and 5: game time 20.0 s in 20.0 s, HRTF on, NVDA; the
  three level 3 lines packed and decoded.
