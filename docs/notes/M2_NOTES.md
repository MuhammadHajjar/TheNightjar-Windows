# M2 - level 1 end to end, with its menus (2026-09-27)

## Recovered (with addresses)

**Main menu** (`PGEViewController_nj.nib`, handlers in PGEViewController):

| label | handler | does | sound |
|---|---|---|---|
| Begin | `continueButtonPressed:` 0x10003cb48 | `InitGameplayEngineAndLaunchLevelWithName` with `lastUnlockedLevel` | click |
| Levels | `hubSelectorButtonTouched:` 0x10003cad0 | `launchHubSelector`: with VoiceOver, `AccessibleAllLevelsViewController` | click |
| Cast | `launchCast:` 0x10003c9dc | CreditsViewController type 2 | click |
| Credits | `launchCredits:` 0x10003c7f4 | CreditsViewController type 1 | click |
| About | `TriggerOtherGames:` 0x10003cd78 | MoreGamesViewController: `html/othergames_nj1.html` | none |

The About button does not open the About screen: `launchAbout:` (type 0,
the 5 Gum image `NJ_about_scroll`) is wired to no button in the Nightjar nib,
so the 5 Gum page is unreachable.  What the About button shows is the page
`othergames_nj1.html` - an About paragraph, More games, Technology.

**Cast and Credits** (`-[CreditsViewController viewDidLoad]` 0x100047840,
`setContent:` 0x100048008): the cast picture's accessibility value is the
cast text (0x100047eec); the credits picture's is the crew text (CFString
0x1002cd970 - psdis printed it as `@"None"`: its CFString reader fails on
long strings, so a "None" in the listing is worth checking).  Main Menu:
`userPressedMainMenu`, back sound.

**Level list** (`AccessibleAllLevelsViewController`): rows "Play Level %i: %@"
/ "Level %i: %@; locked" (altName); choosing an unlocked row posts the launch
and plays no sound, a locked row does nothing; Main Menu plays the back sound.

**Win / lose / end** (`presentWinVC:` 0x10003c484 / `presentLoseVC:` 0x10003c5d4
/ `presentAdiosVC` 0x10003c724, each `playMenuAtmos`):

| screen | buttons |
|---|---|
| win (`PGEWinViewController_nj`) | Continue: `loadLevelWithStringName:` next, click; Play this again: `reloadCurrentLevel`, **no sound**; Main menu: `QuitGameMode`, back |
| lose (`PGELoseViewController_nj`) | Retry: reload, click; Main Menu: back |
| end (`PGEAdiosViewController_nj`) | Play this again: reload (level 14), click; Main Menu: back |

The screens' titles are pictures: "You're through but you're not safe yet"
(NJ_YouMadeItThrough), "0 human life-forms detected" (NJ_YouMetYourEnd), "The
End" (NJ_CompleteGameBG).

**Pause** (`PGEGameplayViewController`): `pauseGame` 0x10000ada0 posts
`PauseGame`, no sound; `resumeGame:` 0x10000af80 click; `playAgainButtonTouched:`
0x10000b24c reload + click; `quitButtonTouched:` 0x10000b10c `QuitGameMode`,
back; `quitLevel` 0x10003d484 brings the menu atmosphere back a second later.

**Menu atmosphere** (`playMenuAtmos` 0x100036e14): the ATMOS sounds of the last
playlist, looping, from gain 0 faded to 1 over 0.5 s (`+[S3DDefaults fadeIn:]`
0x1000cf86c: gain = position / 0.5, then 1 and done); stopped when a level
loads.  After the splash (`removeSplashScreen` - with the Audio Defence advert
check first, N/A), on the three after-level screens, after Quit game.

**PC instructions**: the lines that name touch controls, from the transcripts
(nightjar/tutorial.py): cutscene_friday3's "Use your thumbs. Left, right, left,
right", prompt_d_lvl1_a, prompt_d_lvl1_b, prompt_d_lvl4_a, prompt_d_lvl5_a
(and the unused prompt_d_lvl3_a).

## Proved

* 103 tests: the labels and UI sounds of every screen against the nibs and
  handlers (unit and scripted-key tests through the app's own menu loop), the
  Cast, Credits and About texts word for word against the binary and the
  HTML, the PC lines following the bindings, the menu atmosphere (which
  sounds, the 0.5 s fade, stopped on load, back a second after Quit game), the
  autopilot winning level 1 on five seeds.
* `Run\The Nightjar.exe` (2026-09-27): self-test from a clean folder 20.0 s in
  20.0 s, HRTF on, NVDA; a plain start sits in the main menu with no crash.
  Muhammad's `Run\config` untouched by the build.

## Port additions (logged in DIVERGENCES)

Settings, Quit on the main menu; Settings and Quit to Windows on pause; Select
Level and Quit after a level; Escape on the after-level screens = Main Menu;
the click when a level is chosen; "That level is locked."; the screens' titles
spoken; the version and a PC note on About; the About page's capitals set in
ordinary case (words unchanged).
