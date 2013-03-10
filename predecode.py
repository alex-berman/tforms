#!/usr/bin/python

import os
import subprocess
import re
from logger_factory import logger
import tempfile

class mp3_decoder:
    def command(self, source_filename, target_filename, sample_rate=None):
        cmd = 'mpg123'
        if sample_rate:
            cmd += ' -r %d' % sample_rate
        cmd += ' --mono -w "%s" "%s"' % (target_filename, source_filename)
        return cmd

class m4b_decoder:
    def command(self, source_filename, target_filename, sample_rate=None):
        return 'faad -o "%s" "%s"' % (target_filename, source_filename)

class flac_decoder:
    def command(self, source_filename, target_filename, sample_rate=None):
        return 'flac -d "%s" --channels=1 -o "%s"' % (source_filename, target_filename)
        
class Predecoder:
    DECODABLE_FORMATS = ['mp3', 'm4b', 'flac']

    def __init__(self, files, location=None, sample_rate=None):
        self._files = files
        self._location = location
        self._sample_rate = sample_rate
        self._extension_re = re.compile('\.(\w+)$')
        self._decoders = dict([(extension, self._decoder_for_extension(extension))
                               for extension in self.DECODABLE_FORMATS])

    def _decoder_for_extension(self, extension):
        class_name = "%s_decoder" % extension
        return globals()[class_name]()

    def decode(self, force=False):
        for file_info in self._files:
            self._decode_file_unless_already_decoded(file_info, force)

    def _decode_file_unless_already_decoded(self, file_info, force):
        if self._location:
            source_filename = self._location + os.sep + file_info['name']
        else:
            source_filename = file_info['name']
        if self._extension(source_filename) == 'wav':
            file_info["decoded_name"] = source_filename
        elif self._decodable(source_filename):
            logger.debug("decoding %s" % source_filename)
            target_filename = self._target_filename(source_filename)
            file_info["decoded_name"] = target_filename
            if self._already_decoded(target_filename) and not force:
                logger.debug("file already decoded")
            else:
                self._decode_and_process_file(
                    source_filename, target_filename)

    def _decodable(self, filename):
        extension = self._extension(filename)
        return extension in self.DECODABLE_FORMATS

    def _extension(self, filename):
        m = self._extension_re.search(filename)
        if m:
            return m.group(1).lower()

    def _target_filename(self, source_filename):
        return self._extension_re.sub('.wav', source_filename)

    def _already_decoded(self, filename):
        return os.path.exists(filename)

    def _decode_and_process_file(self, source_filename, target_filename):
        if os.path.isfile(source_filename):
            temp = tempfile.NamedTemporaryFile(suffix=".wav")
            self._decode_file(source_filename, temp.name)
            self._process_file(temp.name, target_filename)
            # self._decode_file(source_filename, target_filename)
        else:
            logger.debug("file not downloaded - not decoding")

    def _decode_file(self, source_filename, target_filename):
        extension = self._extension(source_filename)
        decoder = self._decoders[extension]
        cmd = decoder.command(source_filename, target_filename, self._sample_rate)
        logger.debug("decode command: %s" % cmd)
        subprocess.call(cmd, shell=True)

    def _process_file(self, source_filename, target_filename):
        temp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        self._highpass_and_limit(source_filename, temp.name)
        
        dc_offset = self._get_dc_offset(temp.name)
        print "DC offset: %f" % dc_offset
        if dc_offset > 0.01:
            self._dc_shift(temp.name, target_filename, -dc_offset)
            os.unlink(temp.name)
        else:
            os.rename(temp.name, target_filename)

    def _highpass_and_limit(self, source_filename, target_filename):
        subprocess.call(
            'sox "%s" "%s" highpass 200 compand 0,0 9:-15,0,-9' % (source_filename, target_filename),
            shell=True)

    def _get_dc_offset(self, filename):
        p = subprocess.Popen(
            'sox "%s" -n stats' % filename,
            shell=True, stderr=subprocess.PIPE)
        for line in p.stderr:
            m = re.search('DC offset\s+([-0-9.]+)', line)
            if m:
                return float(m.group(1))
        raise Exception("failed to get DC offset")

    def _dc_shift(self, source_filename, target_filename, dc_shift):
        subprocess.call(
            'sox "%s" "%s" dcshift %f' % (source_filename, target_filename, dc_shift),
            shell=True)


if __name__ == "__main__":
    from argparse import ArgumentParser
    from orchestra import Orchestra
    from tr_log_reader import *
    parser = ArgumentParser()
    parser.add_argument("sessiondir", type=str)
    args = parser.parse_args()

    logfilename = "%s/session.log" % args.sessiondir
    log = TrLogReader(logfilename).get_log()
    predecoder = Predecoder(log, Orchestra.SAMPLE_RATE)
    predecoder.decode()
