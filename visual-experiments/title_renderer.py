class TitleRenderer:
    def __init__(self, title, size, visualizer):
        print "TitleRenderer"
        if ":" in title:
            author, book = title.split(":")
            title = "%s: %s" % (author.upper(), book)
        self.title = title
        self.size = size
        self.visualizer = visualizer

    def render(self, x, y):
        self.visualizer.draw_text(
            text = self.title,
            x = x,
            y = y,
            size = self.size)
