#!/usr/bin/python

from argparse import ArgumentParser
import subprocess
import re

import sys, os
sys.path.append(os.path.dirname(__file__)+"/..")
from tr_log_reader import *

parser = ArgumentParser()
parser.add_argument("sessiondir", type=str)
args = parser.parse_args()

logfilename = "%s/session.log" % args.sessiondir
log = TrLogReader(logfilename).get_log()

ip_matcher = re.compile(' (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}) ')

def trace(addr):
    result = []
    p = subprocess.Popen("traceroute -n %s -w 1.0" % addr,
                         shell=True,
                         stdout=subprocess.PIPE)
    for line in p.stdout:
        m = ip_matcher.search(line)
        if m:
            result.append(m.group(1))
    print result

for addr in log.peers:
    trace(addr)
    break #TEMP
