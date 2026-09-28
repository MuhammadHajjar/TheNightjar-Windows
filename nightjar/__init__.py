"""The Nightjar for Windows."""

#: The version: the day it was made, and "number N" when a day has more than
#: one.  It is the newest heading of changelog.txt (a test holds them together)
#: and the VERSION file.
__version__ = '2026-09-28'

#: What the original's `appName` is (`-[PGEGameParameters init]` 0x10002af40:
#: the bundle's display name without ".app").  The engine is shared with Papa
#: Sangre 1 and picks this game's branches by comparing against it.
APP_NAME = 'The Nightjar'
