class TitleRenderer:
    def __init__(self, title, size, visualizer):
        if ":" in title:
            author, book = title.split(":")
            title = "%s: %s" % (author.upper(), book)
        self._text_renderer = visualizer.text_renderer(title, size)

    def render(self, x, y):
        self._text_renderer.render(x, y)

    def bounding_box(self, x, y):
        return self._text_renderer.bounding_box(x, y)
