# -*- coding: utf-8 -*-

playlist = [
    {"session": "sessions/*roda_rummet1",
     "args": ["--pretend-audio=textival/audio/andersen_swineherd.wav",
              "--title=H.C. Andersen: The Swineherd",
              "-z", "1"]},

    {"session": "sessions/*astrid-lindgrens-favoriter-bocker",
     "args": ["--pretend-audio=textival/audio/flygare_carlen_nyckfull1.wav",
              u"--title=Emilie Flygare-Carlén: En nyckfull kvinna (del 1)".encode("unicode_escape"),
              "-z", "0.6"]},
]
