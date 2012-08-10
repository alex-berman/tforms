import os, sys, re

filename = sys.argv[1]
backup_filename = filename + ".old"
os.rename(filename, backup_filename)
old = open(backup_filename, "r")
new = open(filename, "w")
for line in old:
    line = re.sub(r' chunkId=[0-9]+', '', line)
    new.write(line)
new.close()
old.close()
