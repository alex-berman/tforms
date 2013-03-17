import visualizer
import waves
import heat_map
from argparse import ArgumentParser

class File(waves.File, heat_map.File):
    def add_segment(self, *args):
        waves.File.add_segment(self, *args)
        heat_map.File.add_segment(self, *args)

class Segment(waves.Segment, heat_map.Segment):
    def __init__(self, *args):
        waves.Segment.__init__(self, *args)
        heat_map.Segment.__init__(self, *args)

class WavesAndHeatMap(waves.Waves, heat_map.HeatMap):
    def __init__(self, *args):
        waves.Waves.__init__(self, *args)
        heat_map.HeatMap.__init__(self, *args)
        self.file_class = File
        self.segment_class = Segment

    def InitGL(self, *args):
        waves.Waves.InitGL(self, *args)
        heat_map.HeatMap.InitGL(self, *args)

    def ReSizeGLScene(self, *args):
        waves.Waves.ReSizeGLScene(self, *args)
        heat_map.HeatMap.ReSizeGLScene(self, *args)

    def configure_2d_projection(self):
        heat_map.HeatMap.configure_2d_projection(self)

    @staticmethod
    def add_parser_arguments(parser):
        visualizer.Visualizer.add_parser_arguments(parser)
        parser.add_argument("--peer-info", action="store_true")
        parser.add_argument("--disable-title", action="store_true")
        parser.add_argument("--enable-title", action="store_true")
        parser.add_argument("--test-title", type=str)
        parser.add_argument("--margin-top", type=float, default=0.0)
        parser.add_argument("--margin-bottom", type=float, default=0.0)
        parser.add_argument("--hscope", type=str, default="0:1")

    def reset(self, *args):
        waves.Waves.reset(self, *args)
        heat_map.HeatMap.reset(self, *args)

    def render(self, *args):
        waves.Waves.render(self, *args)
        heat_map.HeatMap.render(self, *args)

    def _delete_outdated_segments(self):
        # this is done by Waves.update() and should only be done there
        pass

if __name__ == "__main__":
    parser = ArgumentParser()
    WavesAndHeatMap.add_parser_arguments(parser)
    options = parser.parse_args()
    WavesAndHeatMap(options).run()
