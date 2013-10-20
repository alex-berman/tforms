from OpenGL.GL import *
import visualizer
import waves
import heat_map
from argparse import ArgumentParser
from smoother import Smoother
from math_tools import sigmoid

class File(waves.File, heat_map.File):
    def add_segment(self, *args):
        waves.File.add_segment(self, *args)
        heat_map.File.add_segment(self, *args)

class Segment(waves.Segment, heat_map.Segment):
    def __init__(self, *args):
        waves.Segment.__init__(self, *args)
        heat_map.Segment.__init__(self, *args)
        self._amp_smoother = Smoother(response_factor=2.5)

    def relative_size(self):
        age = self.age()
        if age > (self.duration - self._fade_time):
            return 1 - sigmoid(1 - (self.duration - age) / self._fade_time)
        else:
            self._amp_smoother.smooth(
                max([abs(value) for value in self.waveform]),
                self.visualizer.time_increment)
            return sigmoid(pow(max(self._amp_smoother.value(), 0), 0.25))

class WavesAndHeatMap(waves.Waves, heat_map.HeatMap):
    def __init__(self, *args):
        waves.Waves.__init__(self, *args)
        heat_map.HeatMap.__init__(self, *args)
        self.file_class = File
        self.segment_class = Segment

    def InitGL(self, *args):
        waves.Waves.InitGL(self, *args)
        heat_map.HeatMap.InitGL(self, *args)

    def resized_window(self):
        waves.Waves.resized_window(self)
        heat_map.HeatMap.resized_window(self)

    def configure_2d_projection(self):
        heat_map.HeatMap.configure_2d_projection(self)

    @staticmethod
    def add_parser_arguments(parser):
        visualizer.Visualizer.add_parser_arguments(parser)
        parser.add_argument("--peer-info", action="store_true")
        parser.add_argument("--disable-title", action="store_true")
        parser.add_argument("--enable-title", action="store_true")
        parser.add_argument("--title-size", type=float, default=30.0)
        parser.add_argument("--test-title", type=str)
        parser.add_argument("--margin-top", type=float, default=0.0)
        parser.add_argument("--margin-bottom", type=float, default=0.0)
        parser.add_argument("--hscope", type=str, default="0:1")
        parser.add_argument("--vscope", type=str, default="0:1")
        parser.add_argument("--continents", action="store_true")
        visualizer.Visualizer.add_margin_argument(parser, "--map-margin")
        visualizer.Visualizer.add_margin_argument(parser, "--waves-margin")

    def reset(self, *args):
        waves.Waves.reset(self, *args)
        heat_map.HeatMap.reset(self, *args)

    def render(self, *args):
        heat_map.HeatMap.render(self, *args)
        self._clear_space_for_waves()
        waves.Waves.render(self, *args)

    def _clear_space_for_waves(self):
        glColor3f(0,0,0)
        glRectf(0, self._waves_top, self.width, self.waves_margin.bottom)

    def _create_title_renderer(self, *args):
        waves.Waves._create_title_renderer(self, *args)

    def _render_title(self, *args):
        waves.Waves._render_title(self, *args)

    def _delete_outdated_segments(self):
        # this is done by Waves.update() and should only be done there
        pass

if __name__ == "__main__":
    parser = ArgumentParser()
    WavesAndHeatMap.add_parser_arguments(parser)
    options = parser.parse_args()
    WavesAndHeatMap(options).run()
