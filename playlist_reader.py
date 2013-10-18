import importlib
import glob

def read_playlist(module_path):
    playlist_module = importlib.import_module(module_path)
    playlist = playlist_module.playlist
    for item in playlist:
        matches = glob.glob(item["session"])
        if len(matches) == 1:
            item["sessiondir"] = matches[0]
        elif len(matches) == 0:
            raise Exception("no sessions matching %s" % item["session"])
        else:
            raise Exception("more than one session matching %s" % item["session"])
    return playlist
