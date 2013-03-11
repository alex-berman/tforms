#!/usr/bin/python

from session import Session
from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument("-s", "--session-name")
parser.add_argument("-t", "--torrent", help="torrent file or URL")
args = parser.parse_args()

session = Session(args.session_name, args.torrent)
session.start()
session.join()
