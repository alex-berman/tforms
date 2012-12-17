from vector import Vector
import math
from math_tools import sigmoid

class CameraScriptInterpreter:
    def __init__(self, script_filename):
        module = __import__(script_filename)
        self._script = self._parse_script(module.script)

    def _parse_script(self, script):
        return [self._parse_keyframe(keyframe) for keyframe in script]

    def _parse_keyframe(self, keyframe):
        t, position, y_orientation, x_orientation = keyframe
        return {"t": float(t),
                "position": Vector(3, position),
                "orientation": Vector(2, (x_orientation, y_orientation))}

    def position_and_orientation(self, t):
        if t < self._script[0]["t"]:
            return (self._script[0]["position"],
                    self._script[0]["orientation"])
        else:
            n1 = self._get_keyframe_index(t)
            if n1 is None:
                return (self._script[-1]["position"],
                        self._script[-1]["orientation"])
            else:
                n2 = n1 + 1
                t1 = self._script[n1]["t"]
                t2 = self._script[n2]["t"]
                opacity2 = sigmoid((t - t1) / (t2 - t1))

                position1 = self._script[n1]["position"]
                position2 = self._script[n2]["position"]
                position = position1 + (position2 - position1) * opacity2

                orientation1 = self._script[n1]["orientation"]
                orientation2 = self._script[n2]["orientation"]
                orientation = orientation1 + (orientation2 - orientation1) * opacity2

                return (position, orientation)

    def _get_keyframe_index(self, t):
        for n1 in range(len(self._script) - 1):
            n2 = n1 + 1
            if self._script[n1]["t"] < t <= self._script[n2]["t"]:
                return n1

    def _sigmoid(self, v):
        return 1.0 / (1.0 + math.exp((-v + .5) * 20))
