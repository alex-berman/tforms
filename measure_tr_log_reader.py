import sys
from tr_log_reader import TrLogReader
filename = sys.argv[1]
use_cache = int(sys.argv[2])
tr_log = TrLogReader(filename).get_log(use_cache)
