import time
import os
import subprocess
import threading
import shutil
from config import DOWNLOAD_LOCATION
import fileinput

class Session(threading.Thread):
    TR_BINARY_PATH = "../../transmission-2.61/gtk/transmission-gtk"

    def __init__(self, session_name=None, torrent=None, realtime=False):
        self._session_name = session_name
        self._torrent = torrent
        self.realtime = realtime
        name = time.strftime("%y%m%d-%H%M%S")
        if session_name:
            name += "-" + session_name
        self.dir = "sessions/%s" % name
        os.mkdir(self.dir)
        os.mkdir("%s/chunks" % self.dir)
        print "session: %s" % self.dir
        self.logfilename = "%s/session.log" % self.dir
        self._create_tr_config()
        if realtime:
            (log_pipe_reader_fd, log_pipe_writer_fd) = os.pipe()
            self.log_pipe_reader = os.fdopen(log_pipe_reader_fd, "r")
            self.log_pipe_writer = os.fdopen(log_pipe_writer_fd, "w")
        threading.Thread.__init__(self, name="Session")
        self.daemon = True

    def _create_tr_config(self):
        self._temp_config_path = os.path.abspath(".temp-transmission-config")
        shutil.rmtree(self._temp_config_path, ignore_errors=True)
        shutil.copytree("transmission-config", self._temp_config_path)
        self._replace_download_dir_in_tr_config()

    def _replace_download_dir_in_tr_config(self):
        self._replace_line_in_file(
            "%s/settings.json" % self._temp_config_path,
            '"download-dir"',
            '    "download-dir": "%s/%s",' % (DOWNLOAD_LOCATION, self._session_name))
    
    def _replace_line_in_file(self, filename, pattern, replacement):
        for line in fileinput.input(filename, inplace=1):
            if pattern in line:
                print replacement
            else:
                print line,

    def get_log_reader(self):
        return self.log_pipe_reader

    def run(self):
        self.logfile = open(self.logfilename, "w")
        if self.realtime:
            self.run_realtime()
        else:
            self.run_non_realtime()

    def run_realtime(self):
        tr = subprocess.Popen(self._tr_command_line(),
                              cwd=self.dir,
                              shell=True,
                              stderr=subprocess.PIPE)
        while(True):
            line = tr.stderr.readline()
            if line == "":
                return
            self.log_pipe_writer.write(line)
            self.log_pipe_writer.flush()
            self.logfile.write(line)
            self.logfile.flush()

    def run_non_realtime(self):
        tr = subprocess.Popen(self._tr_command_line(),
                              cwd=self.dir,
                              shell=True,
                              stderr=self.logfile)
        tr.wait()

    def _tr_command_line(self):
        command_line = "%s -g %s" % (self.TR_BINARY_PATH, self._temp_config_path)
        if self._torrent:
            command_line += " " + self._torrent
        return command_line
