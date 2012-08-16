class Interpretor:
    def interpret(self, chunks, files):
        self._files = files
        groups = self._group_consecutive_chunks(chunks)
        return map(self._interpret_group, groups)

    def _group_consecutive_chunks(self, chunks):
        self._groups = []
        self._current_group = []
        for chunk in chunks:
            if self._chunk_appendable_to_current_group(chunk):
                self._current_group.append(chunk)
            else:
                self._close_current_group()
                self._current_group = [chunk]
        self._close_current_group()
        return self._groups

    def _chunk_appendable_to_current_group(self, chunk):
        if len(self._current_group) > 0:
            return (chunk["begin"] == self._current_group[-1]["end"] and
                    chunk["peeraddr"] == self._current_group[0]["peeraddr"] and
                    chunk["filenum"] == self._current_group[0]["filenum"])

    def _close_current_group(self):
        if len(self._current_group) > 0:
            self._groups.append(self._current_group)

    def _interpret_group(self, group):
        first_chunk = group[0]
        last_chunk = group[-1]
        onset = first_chunk["t"]
        if len(group) == 1:
            duration = self._chunk_duration_with_unadjusted_rate(first_chunk)
        else:
            duration = last_chunk["t"] - onset
        return {"onset": onset,
                "begin": first_chunk["begin"],
                "end": last_chunk["end"],
                "duration": duration,
                "peeraddr": first_chunk["peeraddr"],
                "filenum": first_chunk["filenum"]}

    def _chunk_duration_with_unadjusted_rate(self, chunk):
        file_duration = self._files[chunk["filenum"]]["duration"]
        chunk_size = chunk["end"] - chunk["begin"]
        file_size = self._files[chunk["filenum"]]["length"]
        return float(chunk_size) / file_size * file_duration
