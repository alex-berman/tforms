import copy

class Interpreter:
    def interpret(self, chunks, files):
        self._files = files
        sounds = []
        peers = {}
        for chunk in chunks:
            if chunk["peeraddr"] in peers:
                peer_sound_index = peers[chunk["peeraddr"]]
                if self._chunk_appendable_to_sound(chunk, sounds[peer_sound_index]):
                    sounds[peer_sound_index] = self._append_chunk_to_sound(
                        chunk, sounds[peer_sound_index])
                else:
                    peers[chunk["peeraddr"]] = len(sounds)
                    sounds.append(self._new_sound(chunk))
            else:
                peers[chunk["peeraddr"]] = len(sounds)
                sounds.append(self._new_sound(chunk))
        return sounds

    def _chunk_appendable_to_sound(self, chunk, sound):
        return (chunk["begin"] == sound["end"] and
                chunk["peeraddr"] == sound["peeraddr"] and
                chunk["filenum"] == sound["filenum"])

    def _new_sound(self, chunk):
        sound = copy.copy(chunk)
        sound["onset"] = chunk["t"]
        sound["duration"] = self._chunk_duration_with_unadjusted_rate(chunk)
        return sound

    def _append_chunk_to_sound(self, chunk, sound):
        sound["end"] = chunk["end"]
        sound["duration"] = chunk["t"] - sound["onset"]
        return sound

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
                "id": first_chunk["id"],
                "peeraddr": first_chunk["peeraddr"],
                "filenum": first_chunk["filenum"]}

    def _chunk_duration_with_unadjusted_rate(self, chunk):
        file_duration = self._files[chunk["filenum"]]["duration"]
        chunk_size = chunk["end"] - chunk["begin"]
        file_size = self._files[chunk["filenum"]]["length"]
        return float(chunk_size) / file_size * file_duration
