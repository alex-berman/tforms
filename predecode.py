import os
import subprocess
import re
from logger import logger

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

    def __init__(self, tr_log, sample_rate=None):
        self.tr_log = tr_log
        self.location = tr_log.file_location
        self._sample_rate = sample_rate
        self._extension_re = re.compile('\.(\w+)$')
        self._decoders = dict([(extension, self._decoder_for_extension(extension))
                               for extension in self.DECODABLE_FORMATS])

    def _decoder_for_extension(self, extension):
        class_name = "%s_decoder" % extension
        return globals()[class_name]()

    def decode(self):
        for file_info in self.tr_log.files:
            self._decode_file_unless_already_decoded(file_info)

    def _decode_file_unless_already_decoded(self, file_info):
        source_filename = self.location + os.sep + file_info['name']
        if self._extension(source_filename) == 'wav':
            file_info["decoded_name"] = source_filename
        elif self._decodable(source_filename):
            logger.debug("decoding %s" % source_filename)
            target_filename = self._target_filename(source_filename)
            file_info["decoded_name"] = target_filename
            if self._already_decoded(target_filename):
                logger.debug("file already decoded")
            else:
                self._decode_file(source_filename,
                                  target_filename)

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

    def _decode_file(self, source_filename, target_filename):
        if os.path.isfile(source_filename):
            extension = self._extension(source_filename)
            decoder = self._decoders[extension]
            cmd = decoder.command(source_filename, target_filename, self._sample_rate)
            logger.debug("decode command: %s" % cmd)
            subprocess.call(cmd, shell=True)
        else:
            logger.debug("file not downloaded - not decoding")
