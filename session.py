import time
import os
import subprocess
import threading

class Session(threading.Thread):
    TR_CMD_LINE = "../../transmission-2.20/gtk/transmission-gtk"

    def __init__(self, realtime=False):
        self.realtime = realtime
        name = time.strftime("%y%m%d-%H%M%S")
        self.dir = "sessions/%s" % name
        os.mkdir(self.dir)
        os.mkdir("%s/chunks" % self.dir)
        self.logfilename = "%s/session.log" % self.dir
        if realtime:
            (log_pipe_reader_fd, log_pipe_writer_fd) = os.pipe()
            self.log_pipe_reader = os.fdopen(log_pipe_reader_fd, "r")
            self.log_pipe_writer = os.fdopen(log_pipe_writer_fd, "w")
        threading.Thread.__init__(self)
        self.daemon = True

    def get_log_reader(self):
        return self.log_pipe_reader

    def run(self):
        self.logfile = open(self.logfilename, "w")
        if self.realtime:
            self.run_realtime()
        else:
            self.run_non_realtime()

    def run_realtime(self):
        tr = subprocess.Popen(self.TR_CMD_LINE,
                              cwd=self.dir,
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
        tr = subprocess.Popen(self.TR_CMD_LINE,
                              cwd=self.dir,
                              stderr=self.logfile)
        tr.wait()
