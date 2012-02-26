import numpy
import math
import struct
import subprocess
import wave

class AudioBuffer:
    BYTES_PER_SAMPLE = 2

    def __init__(self, samplerate, frames=None, duration=None):
        self.samplerate = samplerate
        if frames == None and duration != None:
            self.nframes = self.secs2framecount(duration)
            frames = numpy.zeros( self.nframes )
        elif frames != None:
            self.nframes = frames.size
            duration = self.framecount2secs(self.nframes)
        else:
            raise Exception("AudioBuffer requires frames or duration")
        self.frames = frames
        self.duration = duration

    def getframes(self):
        return self.frames

    def chunk(self, offset, length):
        begin = self.secs2framecount(offset)
        end = self.secs2framecount(offset + length)
        return AudioBuffer(self.samplerate, self.frames[begin:end])

    def mix(self, offset, source):
        begin = self.secs2framecount(offset)
        end = min(begin + source.nframes, self.nframes)
        length = end - begin
        sourceframes = source.getframes()[0:length]
        try:
            self.frames[begin:end] += sourceframes
        except:
            raise Exception("mix failed(begin=%s end=%s self.frames.size=%s sourceframes.size=%s)" % (begin, end, self.frames.size, sourceframes.size))

    def apply_fade(self, fade_time):
        fade_time = min(fade_time, self.duration / 2)
        fade_nframes = self.secs2framecount(fade_time)
        if fade_nframes > 0:
            fade_in_env = self._fade_in_env(fade_nframes / 2)
            fade_out_env = fade_in_env[::-1]
            self.frames[0:fade_in_env.size] *= fade_in_env
            self.frames[-fade_out_env.size:] *= fade_out_env

    def apply_pan_right_to_left(self):
        pan_env = self._pan_env()
        self.frames *= pan_env
        
    def _pan_env(self):
        pan_env_left  = numpy.array(range(0, self.nframes / 2), "float") / (self.nframes / 2)
        pan_env_right = 1 - pan_env_left
        #pan_env_right = pan_env_left
        return numpy.ravel(numpy.asmatrix((pan_env_left, pan_env_right)), order='F')

    def secs2framecount(self, secs):
        return int(math.floor(secs * self.samplerate) * 2)

    def framecount2secs(self, framecount):
        return float(framecount) / self.samplerate / 2

    def __str__(self):
        return "AudioBuffer(frames=%s, frames.size=%s, frames.shape=%s)" % \
            (self.frames, self.frames.size, self.frames.shape)

    def _fade_in_env(self, nframes):
        return numpy.repeat(numpy.array(range(0, nframes), "float") / nframes, 2)

    @staticmethod
    def from_raw_mono_data(raw_data, samplerate):
        num_frames = len(raw_data) / AudioBuffer.BYTES_PER_SAMPLE
        arr = struct.unpack_from("%dh" % num_frames, raw_data)
        frames = numpy.repeat(numpy.array(arr), 2)
        return AudioBuffer(samplerate, frames)

    def to_raw_data(self):
        return "".join((struct.pack('h', item) for item in self.frames))

    def normalize(self):
        self.frames *= 32767 / numpy.max(numpy.abs(self.frames))


class AudioReader:
    def __init__(self, samplerate, nframes, nchannels, samplesize):
        self.samplerate = samplerate
        self.nframes = nframes
        self.nchannels = nchannels
        self.samplesize = samplesize
        self.duration = self.nframes / self.samplerate

    def _frames_from_binary_data(self, binary_data):
        out = struct.unpack_from("%dh" % self.nframes * self.nchannels, binary_data)
        return numpy.array(out)

class WavReader(AudioReader):
    def  __init__(self, filename):
        self.file = wave.open(filename, 'rb')
        AudioReader.__init__(self.file.getframerate(),
                             self.file.getnframes(),
                             self.file.getnchannels(),
                             self.file.getsampwidth())
    
    def get_frames(self):
        print "reading audio file..."
        binary_data = self.file.readframes(self.nframes * self.nchannels)
        print "ok"
        return self._frames_from_binary_data(binary_data)

class AudioCommandReader(AudioReader):
    def __init__(self, command, samplerate, nchannels, samplesize):
        self.binary_data, stderr = subprocess.Popen(
            command, stdout=subprocess.PIPE, shell=True).communicate()
        nframes = len(self.binary_data) / nchannels / samplesize
        AudioReader.__init__(self, samplerate, nframes, nchannels, samplesize)

    def get_frames(self):
        return self._frames_from_binary_data(self.binary_data)


class AudioWriter:
    def  __init__(self, frames, filename, nchannels=2, samplerate=44100, samplesize=2):
        self.frames = frames
        self.filename = filename
        self.file = wave.open(filename, 'wb')
        self.file.setnchannels(nchannels)
        self.file.setframerate(samplerate)
        self.file.setnframes(frames.size)
        self.file.setsampwidth(samplesize)
  
    def write(self):
        print "writing audio to %s..." % self.filename
        bufsize = 1024
        remaining = nframes = self.frames.size
        i1 = 0
        while remaining > 0:
            i2 = min(i1 + bufsize, nframes)
            binarydata = self.numpy2string(self.frames[i1:i2])
            self.file.writeframes(binarydata)
            remaining -= i2 - i1
            i1 = i2
        self.file.close()
        print "ok"

    def numpy2string(self, y):
        """Expects a numpy vector of numbers, outputs a string"""
        signal = "".join((wave.struct.pack('h', item) for item in y))
        # this formats data for wave library, 'h' means data are formatted
        # as short ints
        return signal


