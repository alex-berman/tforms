#!/usr/bin/python

from tr_log_reader import TrLogReader
from argparse import ArgumentParser
import shutil
import os
import glob

parser = ArgumentParser()
parser.add_argument("playlist", type=str)
parser.add_argument("project_target", type=str)
args = parser.parse_args()

def copy_dir(source_dir, target_dir):
    if os.path.exists(target_dir):
        print "skipping existing dir %s" % target_dir
    else:
        print "copying %s to %s" % (source_dir, target_dir)
        shutil.copytree(source_dir, target_dir)

def copy_file(source_path, target_path):
    if os.path.exists(target_path):
        print "skipping existing file %s" % target_path
    else:
        print "copying %s to %s" % (source_path, target_path)
        target_dir = os.path.dirname(target_path)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        shutil.copy(source_path, target_path)


playlist_module = __import__(args.playlist)
playlist = playlist_module.playlist
for item in playlist:
    matches = glob.glob(item["session"])
    if len(matches) == 1:
        sessiondir = matches[0]
    elif len(matches) == 0:
        raise Exception("no sessions matching %s" % item["session"])
    else:
        raise Exception("more than one session matching %s" % item["session"])

    logfilename = "%s/session.log" % sessiondir
    tr_log = TrLogReader(logfilename).get_log()
    copy_dir(sessiondir, "%s/%s" % (args.project_target, sessiondir))
    for f in tr_log.files:
        copy_file("%s/%s" % (tr_log.file_location, f["name"]),
                  "%s/%s/%s" % (args.project_target, tr_log.file_location, f["name"]))
