import logging
logging.basicConfig(filename="play.log", 
                    level=logging.DEBUG, 
                    filemode="w",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("play")
