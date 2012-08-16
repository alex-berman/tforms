import wx
import threading
from wx import glcanvas
from OpenGL.GL import *

class GUI(wx.Frame):
    PLAYER_COLOURS = [(255,0,0),
                      (0,255,0),
                      (0,0,255),
                      (255,255,0),
                      (255,0,255),
                      (0,255,255),
                      (100,100,255),
                      (50,50,50)]

    def __init__(self, tr_log, orchestra):
        self.tr_log = tr_log
        self.orchestra = orchestra
        self.score = orchestra.score

        self.width = 800
        self.height = 600
        self.min_byte = min(tr_log.chunks, key=lambda chunk: chunk["begin"])["begin"]
        self.max_byte = max(tr_log.chunks, key=lambda chunk: chunk["end"])["end"]
        self._sounds_being_played = {}
        self._zoom_selection_taking_place = False
        self._playing = False
        self._scrubbing = False
        self._reset_displayed_time()
        self._reset_displayed_bytes()
        self.chunks_and_score_display_list = None
        self.app = wx.App(False)
        self.unplayed_pen = wx.Pen(wx.LIGHT_GREY, width=2)
        self.player_pens = map(self.create_pens_with_colour,
                               self.PLAYER_COLOURS)
        style = wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Frame.__init__(self, None, wx.ID_ANY, "Torrential Forms",
                          size=wx.Size(self.width, self.height), style=style)
        self.Bind(wx.EVT_SIZE, self._OnSize)
        self._vbox = wx.BoxSizer(wx.VERTICAL)
        self._create_control_buttons()
        self._create_clock()
        self._create_peer_buttons()
        self._create_timeline()
        self.SetSizer(self._vbox)
        self.catch_key_events()
        self.Show()
        orchestra.gui = self

    def _create_control_buttons(self):
        self._button_box = wx.BoxSizer(wx.HORIZONTAL)
        self.play_button = wx.Button(self, -1, "Play")
        self.Bind(wx.EVT_BUTTON, self._play_button_clicked, self.play_button)
        self.stop_button = wx.Button(self, -1, "Stop")
        self.Bind(wx.EVT_BUTTON, self._stop_button_clicked, self.stop_button)
        self.stop_button.Disable()
        self.zoom_out_button = wx.Button(self, -1, "Zoom out")
        self.Bind(wx.EVT_BUTTON, self._zoom_out_button_clicked, self.zoom_out_button)
        self._button_box.Add(self.play_button, 1, flag=wx.EXPAND)
        self._button_box.Add(self.stop_button, 1, flag=wx.EXPAND)
        self._button_box.Add(self.zoom_out_button, 1, flag=wx.EXPAND)
        self._vbox.Add(self._button_box)

    def _create_clock(self):
        self.clock = wx.StaticText(self, -1)
        self._button_box.Add(self.clock, 1, flag=wx.EXPAND)
    
    def _create_timeline(self):
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.GLinitialized = False
        self.timeline = glcanvas.GLCanvas(
            self,
            attribList=(glcanvas.WX_GL_RGBA,
                        glcanvas.WX_GL_DOUBLEBUFFER,
                        glcanvas.WX_GL_DEPTH_SIZE, 24))
        self.timeline.Bind(wx.EVT_SIZE, self._on_resize_timeline)
        self.timeline.Bind(wx.EVT_PAINT, self._OnPaint)
        self.timeline.Bind(wx.EVT_KEY_DOWN, self._OnKeyDown)
        self.timeline.Bind(wx.EVT_LEFT_DOWN, self._on_scrub_start)
        self.timeline.Bind(wx.EVT_LEFT_UP, self._on_scrub_stop)
        self.timeline.Bind(wx.EVT_RIGHT_DOWN, self._on_zoom_selection_start)
        self.timeline.Bind(wx.EVT_MOTION, self._on_mouse_moved)
        self.timeline.Bind(wx.EVT_RIGHT_UP, self._on_zoom_selection_stop)
        hbox.Add(self._timeline_button_box)
        hbox.Add(self.timeline, 1, flag=wx.EXPAND)
        self._vbox.Add(hbox, 1, flag=wx.EXPAND)

    def _on_resize_timeline(self, event):
        if self.timeline.GetContext():
            self.Show()
            self.timeline.SetCurrent()
            size = self.timeline.GetClientSize()
            self._reshape_timeline(size.width, size.height)
            self.timeline.Refresh(False)
        event.Skip()

    def _reshape_timeline(self, width, height):
        self.timeline_width = width
        self.timeline_height = height
        glViewport(0, 0, width, height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(0.0, width, height, 0.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW)

    def _create_peer_buttons(self):
        self._timeline_button_box = wx.BoxSizer(wx.VERTICAL)
        self._peer_buttons = []
        for i in range(len(self.tr_log.peers)):
            button = wx.CheckBox(self, i, 'Peer %d' % (i+1))
            button.SetValue(True)
            button.SetForegroundColour(self.PLAYER_COLOURS[i % len(self.PLAYER_COLOURS)])
            button.Bind(wx.EVT_CHECKBOX, self._peer_button_toggled, button)
            self._timeline_button_box.Add(button)
            self._peer_buttons.append(button)

    def _peer_button_toggled(self, event):
        peer_id = event.GetId()
        self.orchestra.players[peer_id].enabled = self._peer_buttons[peer_id].GetValue()
        self.refresh_chunks()
        self.timeline.Refresh()
        self.catch_key_events()

    def main_loop(self):
        self.app.MainLoop()

    def _play_button_clicked(self, event):
        self._orchestra_thread = threading.Thread(target=self.orchestra.play_non_realtime)
        self._orchestra_thread.daemon = True
        self._orchestra_thread.start()
        self.play_button.Disable()
        self.stop_button.Enable()
        self._playing = True
        self.catch_key_events()

    def _stop_button_clicked(self, event):
        self.orchestra.stop()
        self._orchestra_thread.join()
        self.stop_button.Disable()
        self.play_button.Enable()
        self._sounds_being_played = {}
        self._playing = False
        self.catch_key_events()

    def _OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE:
            self._toggle_play(event)
        event.Skip()

    def _toggle_play(self, event):
        if self._playing:
            self._stop_button_clicked(event)
        else:
            self._play_button_clicked(event)

    def _OnPaint(self, event):
        self.timeline.SetCurrent()
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True
            self._on_resize_timeline(event)
        self._draw()
        event.Skip()

    def OnInitGL(self):
        glClearColor(1, 1, 1, 1)

    def _draw(self):
        glClear(GL_COLOR_BUFFER_BIT)
        self.draw_chunks_and_score()
        self.draw_time_cursor()
        self.update_clock()
        if self._zoom_selection_taking_place:
            self._draw_zoom_selection()
        self.timeline.SwapBuffers()

    def _draw_zoom_selection(self):
        self.set_pen(wx.LIGHT_GREY_PEN)
        glLineWidth(1)
        self.draw_rectangle(self._zoom_selection_x1,
                            self._zoom_selection_y1,
                            self._zoom_selection_x2,
                            self._zoom_selection_y2)

    def draw_rectangle(self, x1, y1, x2, y2):
        glBegin(GL_LINE_LOOP)
        glVertex2f(x1, y1)
        glVertex2f(x2, y1)
        glVertex2f(x2, y2)
        glVertex2f(x1, y2)
        glEnd()

    def _OnSize(self, event):
        self.Layout()
        size = self.timeline.GetClientSize()
        self.width = size.width
        self.height = size.height
        self.refresh_chunks()
        self.timeline.Refresh()

    def _reset_displayed_time(self):
        self._displayed_time_begin = 0
        self._displayed_time_end = self.tr_log.lastchunktime()

    def _reset_displayed_bytes(self):
        self._displayed_byte_begin = self.min_byte
        self._displayed_byte_end = self.max_byte

    def _zoom_out_button_clicked(self, event):
        self._reset_displayed_time()
        self._reset_displayed_bytes()
        self.refresh_chunks()
        self.timeline.Refresh()
        self.catch_key_events()

    def _on_scrub_start(self, event):
        self._scrubbing = True
        t = self.px_to_time(event.GetX())
        self.orchestra.set_time_cursor(t)
        self.timeline.Refresh()

    def _on_scrub_stop(self, event):
        self._scrubbing = False

    def _on_zoom_selection_start(self, event):
        self._zoom_selection_x1 = event.GetX()
        self._zoom_selection_y1 = event.GetY()
        self._zoom_selection_x2 = self._zoom_selection_x1
        self._zoom_selection_y2 = self._zoom_selection_y1
        self._zoom_selection_taking_place = True

    def _on_zoom_selection_stop(self, event):
        if self._zoom_selection_taking_place:
            (self._displayed_time_begin,
             self._displayed_time_end) = sorted((
                self.px_to_time(self._zoom_selection_x1),
                self.px_to_time(self._zoom_selection_x2)))

            (self._displayed_byte_begin,
             self._displayed_byte_end) = sorted((
                    self.py_to_byte(self._zoom_selection_y1),
                    self.py_to_byte(self._zoom_selection_y2)))

            self._zoom_selection_taking_place = False
            self.refresh_chunks()
            self.timeline.Refresh()

    def _on_mouse_moved(self, event):
        if self._zoom_selection_taking_place:
            self._zoom_selection_x2 = event.GetX()
            self._zoom_selection_y2 = event.GetY()
            self.timeline.Refresh()
        elif self._scrubbing:
            self._scrub(event)

    def _scrub(self, event):
        t = self.px_to_time(event.GetX())
        if self._playing:
            self.orchestra.set_time_cursor(t)
        else:
            self.orchestra.scrub_to_time(t)
        self.timeline.Refresh()

    def draw_chunks_and_score(self):
        if self.chunks_and_score_display_list:
            glCallList(self.chunks_and_score_display_list)
        else:
            self.render_and_draw_chunks_and_score()
        self.draw_highlighted_sounds()

    def draw_highlighted_sounds(self):
        glLineWidth(2)
        glBegin(GL_LINES)
        for sound_id in self._sounds_being_played.keys():
            sound = self.orchestra.sounds_by_id[sound_id]
            self.draw_sound(sound)
        glEnd()

    def refresh_chunks(self):
        if self.chunks_and_score_display_list:
            glDeleteLists(self.chunks_and_score_display_list, 1)
            self.chunks_and_score_display_list = None

    def render_and_draw_chunks_and_score(self):
        self.chunks_and_score_display_list = glGenLists(1)
        glNewList(self.chunks_and_score_display_list, GL_COMPILE_AND_EXECUTE)

        glBegin(GL_QUADS)
        for chunk in self.tr_log.chunks:
            self.draw_chunk(chunk)
        glEnd()

        glLineWidth(1)
        glBegin(GL_LINES)
        for sound in self.score:
            self.draw_sound(sound)
        glEnd()

        glEndList()

    def draw_chunk(self, chunk, size=0):
        x = self.time_to_px(chunk["t"])
        if 0 <= x < self.timeline_width:
            player_id = self.orchestra.get_player_for_chunk(chunk).id
            if self._peer_buttons[player_id].GetValue() == True:
                pen = self.get_pen_for_player(player_id)
                self.set_pen(pen)
                x1 = x - size
                x2 = x + size + 3
                y1 = self.byte_to_py(chunk["begin"]) + size
                y2 = self.byte_to_py(chunk["end"])   - size - 1
                glVertex2f(x1, y1)
                glVertex2f(x2, y1)
                glVertex2f(x2, y2)
                glVertex2f(x1, y2)

    def draw_sound(self, sound):
        pen = self.get_pen_for_peer(sound["peeraddr"])
        x1 = self.time_to_px(sound["onset"])
        x2 = self.time_to_px(sound["onset"] + sound["duration"].value)
        y1 = self.byte_to_py(sound["begin"])
        y2 = self.byte_to_py(sound["end"])
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)

    def set_pen(self, pen):
        colour = pen.GetColour()
        glColor3f(colour.Red()/255.0, colour.Blue()/255.0, colour.Green()/255.0)

    def draw_line(self, x1, y1, x2, y2):
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glEnd()

    def create_pens_with_colour(self, rgb):
        colour = wx.Colour(*rgb)
        return wx.Pen(colour, width=2)

    def get_pen_for_player(self, player_id):
        pen_id = player_id % len(self.player_pens)
        return self.player_pens[pen_id]

    def get_pen_for_peer(self, peer):
        player = self.orchestra.get_player_for_peer(peer)
        pen_id = player.id % len(self.player_pens)
        return self.player_pens[pen_id]

    def draw_time_cursor(self):
        self.set_pen(wx.LIGHT_GREY_PEN)
        glLineWidth(1)
        x = self.time_to_px(self.orchestra.get_current_log_time())
        y1 = 0
        y2 = self.timeline_height
        self.draw_line(x, y1, x, y2)

    def update_clock(self):
        self.clock.SetLabel('%.2f' % self.orchestra.get_current_log_time())

    def highlight_sound(self, sound):
        self._sounds_being_played[sound["id"]] = True
        wx.CallAfter(self.timeline.Refresh)

    def unhighlight_sound(self, sound):
        if self._sound_is_being_played(sound):
            del self._sounds_being_played[sound["id"]]
            wx.CallAfter(self.timeline.Refresh)

    def _sound_is_being_played(self, sound):
        return sound["id"] in self._sounds_being_played

    def time_to_px(self, t):
        return (t - self._displayed_time_begin) * self.timeline_width / (
            self._displayed_time_end - self._displayed_time_begin)

    def byte_to_py(self, byte):
        return self.timeline_height - \
            (byte - self._displayed_byte_begin) * self.timeline_height / (
            self._displayed_byte_end - self._displayed_byte_begin)

    def px_to_time(self, px):
        return self._displayed_time_begin + px * (
            self._displayed_time_end - self._displayed_time_begin) / self.timeline_width

    def py_to_byte(self, py):
        return self._displayed_byte_begin + (self.timeline_height - py) * (
            self._displayed_byte_end - self._displayed_byte_begin) / self.timeline_height

    def catch_key_events(self):
        self.timeline.SetFocus()
