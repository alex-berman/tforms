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
        waves.Waves.add_parser_arguments(parser)
        heat_map.HeatMap.add_parser_arguments(parser)

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
