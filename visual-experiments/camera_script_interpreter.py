from vector import Vector

class CameraScriptInterpreter:
    def __init__(self, script_filename):
        module = __import__(script_filename)
        self._script = self._parse_script(module.script)

    def _parse_script(self, script):
        return [self._parse_keyframe(keyframe) for keyframe in script]

    def _parse_keyframe(self, keyframe):
        t, position, y_orientation, x_orientation = keyframe
        return {"t": t,
                "position": Vector(3, position),
                "y_orientation": y_orientation,
                "x_orientation": x_orientation}

    def position(self, t):
        if t < self._script[0]["t"]:
            return self._script[0]["position"]
        else:
            n1 = self._get_keyframe_index(t)
            if n1 is None:
                return self._script[-1]["position"]
            else:
                n2 = n1 + 1
                t1 = self._script[n1]["t"]
                t2 = self._script[n2]["t"]
                opacity2 = (t - t1) / (t2 - t1)
                position1 = self._script[n1]["position"]
                position2 = self._script[n2]["position"]
                return position1 + (position2 - position1) * opacity2

    def _get_keyframe_index(self, t):
        for n1 in range(len(self._script) - 1):
            n2 = n1 + 1
            if self._script[n1]["t"] < t <= self._script[n2]["t"]:
                return n1
