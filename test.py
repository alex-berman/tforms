import re
file_info_pattern='^TID=1 file=(\d+) offset=(\d+) length=(\d+) firstPiece=(\d+) lastPiece=(\d+) name=(.*)$'
line='TID=1 file=9 offset=51953368 length=8140068 firstPiece=792 lastPiece=916 name=The Art Of The Fugue - Gould - 224 Kbps/10 - The Art of the Fugue, BWV 1080 Contrapunctus I.mp3'
m = re.search(file_info_pattern, line)
print m.groups()

