#!/usr/bin/python

from session import Session
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-s", "session_name")
parser.add_argument("-t", "torrent")
args = parser.parse_args()

# TODO:
# mkdir ~/Downloads/$session_name
# create configuration as copy of default config, with ~/Downloads/$session_name as download-dir
# automatically add fileLocation=... to torrent init line in log
# start transmission with configuration and torrent as arguments

session = Session()
session.start()
session.join()
