import os

SESSIONS_PATH = "sessions"

def get_sessions():
    sessions = []
    for name in os.listdir(SESSIONS_PATH):
        session_dir = "%s/%s" % (SESSIONS_PATH, name)
        log_path = "%s/session.log" % session_dir
        if os.path.exists(log_path):
            sessions.append({"name": name,
                             "dir": session_dir})
    return sessions
