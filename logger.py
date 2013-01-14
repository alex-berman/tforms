import logging
import sys
logging.basicConfig(filename="%s.log" % sys.argv[0],
                    level=logging.INFO,
                    filemode="w",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("play")
