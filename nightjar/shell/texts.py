"""The words the original's screens show, a row at a time.

Each list is the original's own text, word for word, set in ordinary case so a
screen reader does not spell out capitals (the original shows it in capitals);
tests/test_shell.py holds every word against its source.

* ``CREDITS`` - the Credits screen's accessibility value, set on the credits
  picture in ``-[CreditsViewController viewDidLoad]`` (CFString at
  0x1002cd970); each credit read as "role: names" (house standard).
* ``CAST`` - the Cast screen's, on the cast picture (0x100047eec).
* ``ABOUT`` - the About button's page: ``html/othergames_nj1.html``, which
  ``-[MoreGamesViewController viewDidLoad]`` loads (the About button's handler
  is ``TriggerOtherGames:``); its three headings and their paragraphs.
"""

CREDITS = [
    "The Nightjar, created by Somethin' Else and AMV BBDO.",
    'Crew:',
    'Executive producer and director: Paul Bennun',
    'Devised and written: Neil Bennun',
    'Producer: Esther Cunliffe',
    'Creative director: Thiago de Moraes',
    'Creative director: Mark Fairbanks',
    'Development producer: Trevor Klein',
    'Game design consultant: Pete Law',
    'Project manager: Laura Nix',
    "Producer: David O'Donnell",
    'Director of sound and music: Nick Ryan',
    'Game wrangling and voice director: Tassos Stevens',
    'Designer: James Townsend',
    'Interface design and animation: Harry Osborne, Neal Coghlan and Paul Grizzell',
    'Engineer Papa Engine: Dan Jones',
    'Lead developer game engine: Antoine Pastor',
    'Lead engineer Papa Engine: Nigel James Brown',
    'Engineer Papa Engine: Jean Francoise Brouillet',
    'Level rebuilding and testing: Kenny Zhao',
    'Technical project manager Papa Engine: Neville Daniel',
    'Exec producer Papa Engine: Nicky Birch',
    'Producer Papa Engine: Tom Green',
    'Thanks to Sue Cobbledick, Sas Horscroft, Mark Graeme, Gary Grant, Joe Heath, '
    'Charlotte Stone, and Amy Witter.',
]

CAST = [
    'Cast:',
    'Dickie von Kolding: Benedict Cumberbatch',
    'Steig Kjaersgaard: Finlay Robertson',
    'Computer: Melanie Wilson',
    'Captain: Gemma Brockis',
    'Jakob Kullberg: Neil Bennun',
    'Runa Naess: Pia Webley',
    'Adam Pedersen: Dave O-Donnell',
]

ABOUT = [
    'About',
    'The Nightjar uses 3D binaural audio to render its world. You’ll need stereo '
    'headphones to play (any pair will do, make sure left and right are in the '
    'correct ears).',
    'The Nightjar is © 2013 Somethin’ Else',
    'More games',
    'Papa Sangre: the original terrifying 3D audio game. Explore the land of the '
    'dead using only your ears.',
    "Papa Sangre II: Papa's back! But you're dead! If you want to get back to the "
    "world of the living you'll need a ticket to his museum of memory. Sean Bean "
    '(Game of Thrones, The Lord of the Rings), will show you the way.',
    'Technology',
    "These games are made by Somethin' Else, with 3D sound powered by the all new "
    'Papa Engine. Now available for anyone to license to power their game. For '
    'more information see www.papaengine.com',
]

#: The pictures' words, which the screens show and VoiceOver could not read:
#: spoken as each screen's title (PORT-SIDE).
WIN_TITLE = "You're through but you're not safe yet"     # NJ_YouMadeItThrough.png
LOSE_TITLE = '0 human life-forms detected'               # NJ_YouMetYourEnd.png
END_TITLE = 'The End'                                    # NJ_CompleteGameBG.png
PAUSE_TITLE = 'Paused'                                   # NJ_Paused.png
