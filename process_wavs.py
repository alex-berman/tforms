#!/usr/bin/python

from tr_log_reader import *
from argparse import ArgumentParser
from predecode import Predecoder
from orchestra import Orchestra
import shutil
import subprocess

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
args = parser.parse_args()

logfilename = "%s/session.log" % args.sessiondir
log = TrLogReader(logfilename).get_log()

predecoder = Predecoder(log, Orchestra.SAMPLE_RATE)
predecoder.decode()

def process(filename):
    print filename
    backup_filename = "%s.backup.wav" % filename
    if not os.path.exists(backup_filename):
        shutil.copyfile(filename, backup_filename)

    dc_offset = get_dc_offset(filename)
    print dc_offset

    dc_shift(backup_filename, filename, -dc_offset)

def get_dc_offset(filename):
    p = subprocess.Popen(
        'sox "%s" -n stats' % filename,
        shell=True, stderr=subprocess.PIPE)
    for line in p.stderr:
        m = re.search('DC offset\s+([0-9.]+)', line)
        if m:
            return float(m.group(1))
    raise Exception("failed to get dc offset")

def dc_shift(source_filename, dest_filename, dc_shift):
    subprocess.call('sox "%s" "%s" dcshift %f' % (source_filename, dest_filename, dc_shift),
                    shell=True)

for f in log.files:
    process(f["decoded_name"])
