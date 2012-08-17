import copy

MAX_PAUSE_WITHIN_SOUND = 1.0

class Interpreter:
    def interpret(self, chunks, files):
        self._files = files
        sounds = []
        peers = {}
        for chunk in chunks:
            if chunk["peeraddr"] in peers:
                peer_sound_index = peers[chunk["peeraddr"]]
                if self._chunk_appendable_to_sound(chunk, sounds[peer_sound_index]):
                    self._append_chunk_to_sound(chunk, sounds[peer_sound_index])
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
                chunk["filenum"] == sound["filenum"] and
                ((chunk["t"] - (sound["onset"]+sound["duration"])) < MAX_PAUSE_WITHIN_SOUND))

    def _new_sound(self, chunk):
        sound = copy.copy(chunk)
        sound["onset"] = chunk["t"]
        sound["duration"] = self._chunk_duration_with_unadjusted_rate(chunk)
        sound["id"] = chunk["sound_id"] = chunk["id"]
        return sound

    def _append_chunk_to_sound(self, chunk, sound):
        sound["end"] = chunk["end"]
        sound["duration"] = chunk["t"] - sound["onset"]
        chunk["sound_id"] = sound["id"]

    def _chunk_duration_with_unadjusted_rate(self, chunk):
        file_duration = self._files[chunk["filenum"]]["duration"]
        chunk_size = chunk["end"] - chunk["begin"]
        file_size = self._files[chunk["filenum"]]["length"]
        return float(chunk_size) / file_size * file_duration
