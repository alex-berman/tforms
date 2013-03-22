# -*- coding: utf-8 -*-

playlist = [
    {"session": "sessions/*zlatan-01-10",
     "args": ["--pretend-audio=textival/audio/kallocain1.wav",
              "--title=Karin Boye: Kallocain (del 1)",
              "-z", "0.1"]},

    {"session": "sessions/*zlatan-11-20",
     "args": ["--pretend-audio=textival/audio/kallocain2.wav",
              "--title=Karin Boye: Kallocain (del 2)",
              "-z", "0.5",
              "--max-segment-duration=5.0", "--max-pause-within-segment=2.5"]},

    {"session": "sessions/*roda_rummet1",
     "args": ["--pretend-audio=textival/audio/strindberg_brott_och_brott1.wav",
              "--title=August Strindberg: Brott och brott (del 1)",
              "-z", "1"]},

    {"session": "sessions/*moberg-utvandrarna-01",
     "args": ["--pretend-audio=textival/audio/moberg_utvandrarna1_1.wav",
              "--title=Vilhelm Moberg: Utvandrarna (del 1)",
              "-z", "0.6"]},

    {"session": "sessions/*moberg-utvandrarna-02",
     "args": ["--pretend-audio=textival/audio/moberg_utvandrarna1_2.wav",
              "--title=Vilhelm Moberg: Utvandrarna (del 2)",
              "--max-segment-duration=5.0", "--max-pause-within-segment=2.5",
              "-z", "2.5"]},

    {"session": "sessions/*roda_rummet2",
     "args": ["--pretend-audio=textival/audio/ibsen_ett_dockhem1.wav",
              "--title=Henrik Ibsen: Ett dockhem (del 1)",
              "-z", "4",
              "--max-segment-duration=5.0", "--max-pause-within-segment=2.5"]},

    {"session": "sessions/*astrid-lindgrens-favoriter-bocker",
     "args": ["--pretend-audio=textival/audio/flygare_carlen_nyckfull1.wav",
              u"--title=Emilie Flygare-Carlén: En nyckfull kvinna (del 1)".encode("unicode_escape"),
              "-z", "0.6"]},

    {"session": "sessions/*roda_rummet3",
     "args": ["--pretend-audio=textival/audio/dagerman_sommar1.wav",
              u"--title=Stig Dagerman: Vår lilla sommar (del 1)".encode("unicode_escape"),
              "-z", "4.5",
              "--max-segment-duration=5.0", "--max-pause-within-segment=2.5"]},



    # REMOVED:
    # {"session": "sessions/*zlatan-11-20",
    #  "args": ["--pretend-audio=textival/audio/lagerloef_nils1.wav",
    #           u"--title=Selma Lagerlöf: Nils Holgersson's Adventures (part 1)".encode("unicode_escape"),
    #           "-z", "0.7",
    #           "--max-segment-duration=5.0", "--max-pause-within-segment=2.5"]},
]
