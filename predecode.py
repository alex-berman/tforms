import os
import subprocess
import re

class Predecoder:
    DECODABLE_FORMATS = ['mp3', 'm4b', 'flac']

    def __init__(self, tr_log, location, sample_rate=None):
        self.tr_log = tr_log
        self.location = location
        self._sample_rate = sample_rate
        self._extension_re = re.compile('\.(\w+)$')

    def decode(self):
        for file_info in self.tr_log.files:
            self._decode_file_unless_already_decoded(file_info)

    def _decode_file_unless_already_decoded(self, file_info):
        source_filename = self.location + os.sep + file_info['name']
        if self._extension(source_filename) == 'wav':
            file_info["decoded_name"] = source_filename
        elif self._decodable(source_filename):
            target_filename = self._target_filename(source_filename)
            file_info["decoded_name"] = target_filename
            if not self._already_decoded(target_filename):
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
        extension = self._extension(source_filename)
        if extension == 'mp3':
            cmd = 'mpg123'
            if self._sample_rate:
                cmd += ' -r %d' % self._sample_rate
            cmd += ' -w "%s" "%s"' % (target_filename, source_filename)
        elif extension == 'm4b':
            cmd = 'faad -o "%s" "%s"' % (target_filename, source_filename)
        elif extension == 'flac':
            cmd = 'flac -d "%s" -o "%s"' % (source_filename, target_filename)
        subprocess.call(cmd, shell=True)
