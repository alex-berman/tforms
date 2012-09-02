import wx
import threading
from wx import glcanvas
from OpenGL.GL import *
import colors

class GUI(wx.Frame):
    PLAYING, STOPPED, FF = range(3)

    def __init__(self, orchestra):
        self.orchestra = orchestra
        self.score = orchestra.score

        self.width = 800
        self.height = 600
        self.min_byte = min(orchestra.chunks, key=lambda chunk: chunk["begin"])["begin"]
        self.max_byte = max(orchestra.chunks, key=lambda chunk: chunk["end"])["end"]
        self._segments_being_played = {}
        self._zoom_selection_taking_place = False
        self._state = self.STOPPED
        self._reset_displayed_time()
        self._reset_displayed_bytes()
        self.chunks_and_score_display_list = None
        self.app = wx.App(False)
        self.unplayed_pen = wx.Pen(wx.LIGHT_GREY, width=2)
        self.peer_colors = [wx.Colour(r*255, g*255, b*255)
                            for (r,g,b,a) in colors.colors(len(orchestra.tr_log.peers))]
        self.player_pens = [wx.Pen(color, width=2)
                            for color in self.peer_colors]
        style = wx.DEFAULT_FRAME_STYLE | wx.NO_FULL_REPAINT_ON_RESIZE
        wx.Frame.__init__(self, None, wx.ID_ANY, "Torrential Forms",
                          size=wx.Size(self.width, self.height), style=style)
        self.Bind(wx.EVT_SIZE, self._OnSize)
        self.timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER,self._on_timer)
        self._vbox = wx.BoxSizer(wx.VERTICAL)
        self._create_control_buttons()
        self._create_clock()
        self._create_layer_buttons()
        self._create_timeline()
        self.SetSizer(self._vbox)
        self.catch_key_events()
        self.Show()
        orchestra.gui = self

    def _create_control_buttons(self):
        self._control_buttons_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self._play_button = self._create_control_button("Play", self._play_button_clicked)
        self._ff_button = self._create_control_button("Fast-forward", self._ff_button_clicked)
        self._stop_button = self._create_control_button("Stop", self._stop_button_clicked)
        self._zoom_out_button = self._create_control_button(
            "Zoom out", self._zoom_out_button_clicked)
        self._stop_button.Disable()
        self._vbox.Add(self._control_buttons_sizer)

    def _create_control_button(self, label, callback):
        button = wx.Button(self, -1, label)
        self.Bind(wx.EVT_BUTTON, callback, button)
        self._control_buttons_sizer.Add(button, 1, flag=wx.EXPAND)
        return button

    def _create_clock(self):
        self.clock = wx.StaticText(self, -1)
        self._control_buttons_sizer.Add(self.clock, 1, flag=wx.EXPAND)
    
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
        self.timeline.Bind(wx.EVT_LEFT_DOWN, self._set_time_cursor)
        self.timeline.Bind(wx.EVT_RIGHT_DOWN, self._on_zoom_selection_start)
        self.timeline.Bind(wx.EVT_MOTION, self._on_mouse_moved)
        self.timeline.Bind(wx.EVT_RIGHT_UP, self._on_zoom_selection_stop)
        hbox.Add(self._layers_box)
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

    def _create_layer_buttons(self):
        self._layers_box = wx.BoxSizer(wx.VERTICAL)
        self._chunks_button = self._create_layers_checkbox(
            "Chunks", self._layers_modified, default=True)
        self._segments_button = self._create_layers_checkbox(
            "Segments", self._layers_modified, default=True)
        self._create_peer_buttons()
        self._create_layers_button("Select all peers", self._select_all_peers)
        self._create_layers_button("Select no peers", self._select_no_peers)

    def _select_all_peers(self, event):
        self._set_all_peers_enabled(True)

    def _select_no_peers(self, event):
        self._set_all_peers_enabled(False)

    def _set_all_peers_enabled(self, enabled):
        for i in range(len(self._peer_buttons)):
            self._peer_buttons[i].SetValue(enabled)
            self.orchestra.players[i].enabled = enabled
        self._layers_modified()

    def _create_layers_checkbox(self, label, callback, default):
        button = wx.CheckBox(self, label=label)
        button.SetValue(default)
        button.Bind(wx.EVT_CHECKBOX, callback, button)
        self._layers_box.Add(button)
        return button

    def _create_layers_button(self, label, callback):
        button = wx.Button(self, label=label)
        button.Bind(wx.EVT_BUTTON, callback, button)
        self._layers_box.Add(button)
        return button

    def _layers_modified(self, event=None):
        self.refresh_chunks()
        self.catch_key_events()
        
    def _create_peer_buttons(self):
        self._peer_buttons = []
        for i in range(len(self.orchestra.tr_log.peers)):
            button = wx.CheckBox(self, i, 'Peer %d' % (i+1))
            button.SetValue(True)
            button.SetForegroundColour(self.peer_colors[i])
            button.Bind(wx.EVT_CHECKBOX, self._peer_button_toggled, button)
            self._layers_box.Add(button)
            self._peer_buttons.append(button)

    def _peer_button_toggled(self, event):
        peer_id = event.GetId()
        self._set_peer_enabled(peer_id, self._peer_buttons[peer_id].GetValue())
        self._layers_modified()

    def _set_peer_enabled(self, peer_id, enabled):
        self.orchestra.players[peer_id].enabled = enabled

    def main_loop(self):
        self.app.MainLoop()

    def _play_button_clicked(self, event):
        self.orchestra.timefactor = 1
        self.orchestra.playback_enabled = True
        self._orchestra_thread = threading.Thread(target=self.orchestra.play_non_realtime)
        self._orchestra_thread.daemon = True
        self._orchestra_thread.start()
        self._play_button.Disable()
        self._stop_button.Enable()
        self._ff_button.Disable()
        self._state = self.PLAYING
        self.catch_key_events()

    def _ff_button_clicked(self, event):
        self.orchestra.timefactor = 100
        self.orchestra.playback_enabled = False
        self._orchestra_thread = threading.Thread(target=self.orchestra.play_non_realtime)
        self._orchestra_thread.daemon = True
        self._orchestra_thread.start()
        self._play_button.Disable()
        self._stop_button.Enable()
        self._ff_button.Disable()
        self._state = self.FF
        self.catch_key_events()

    def _stop_button_clicked(self, event):
        self.orchestra.stop()
        self._orchestra_thread.join()
        self._stop_button.Disable()
        self._play_button.Enable()
        self._ff_button.Enable()
        self._segments_being_played = {}
        self._state = self.STOPPED
        self.orchestra.set_time_cursor(self.orchestra.log_time_played_from) # this seems required after ff, or else irrelevant playback occurs, don't know why
        self.catch_key_events()

    def _OnKeyDown(self, event):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE:
            self._toggle_play(event)
        elif keycode == wx.WXK_ESCAPE:
            self.Destroy()
        event.Skip()

    def _toggle_play(self, event):
        if self._state == self.PLAYING:
            self._stop_button_clicked(event)
        else:
            self._play_button_clicked(event)

    def _OnPaint(self, event):
        self.timer.Start(100)
        self.timeline.SetCurrent()
        if not self.GLinitialized:
            self.OnInitGL()
            self.GLinitialized = True
            self._on_resize_timeline(event)
        self._draw()
        event.Skip()

    def _on_timer(self, event):
        self.timeline.Refresh()

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

    def _reset_displayed_time(self):
        self._displayed_time_begin = 0
        self._displayed_time_end = self.orchestra.tr_log.lastchunktime()

    def _reset_displayed_bytes(self):
        self._displayed_byte_begin = self.min_byte
        self._displayed_byte_end = self.max_byte

    def _zoom_out_button_clicked(self, event):
        self._reset_displayed_time()
        self._reset_displayed_bytes()
        self.refresh_chunks()
        self.catch_key_events()

    def _set_time_cursor(self, event):
        t = self.px_to_time(event.GetX())
        self.orchestra.set_time_cursor(t)
        self.timeline.Refresh()

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

    def _on_mouse_moved(self, event):
        if self._zoom_selection_taking_place:
            self._zoom_selection_x2 = event.GetX()
            self._zoom_selection_y2 = event.GetY()
            self.timeline.Refresh()

    def draw_chunks_and_score(self):
        if self.chunks_and_score_display_list:
            glCallList(self.chunks_and_score_display_list)
        else:
            self.render_and_draw_chunks_and_score()
        self.draw_highlighted_segments()

    def draw_highlighted_segments(self):
        glLineWidth(4)
        glBegin(GL_LINES)
        for segment_id in self._segments_being_played.keys():
            segment = self.orchestra.segments_by_id[segment_id]
            self.draw_segment(segment, opacity=0.8)
        glEnd()

    def refresh_chunks(self):
        if self.chunks_and_score_display_list:
            glDeleteLists(self.chunks_and_score_display_list, 1)
            self.chunks_and_score_display_list = None
        self.timeline.Refresh()

    def render_and_draw_chunks_and_score(self):
        self.chunks_and_score_display_list = glGenLists(1)
        glNewList(self.chunks_and_score_display_list, GL_COMPILE_AND_EXECUTE)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        if self._chunks_button.GetValue():
            self.draw_chunks()
        if self._segments_button.GetValue():
            self.draw_segments()
        glEndList()

    def draw_chunks(self):
        glBegin(GL_QUADS)
        for chunk in self.orchestra.chunks:
            self.draw_chunk(chunk)
        glEnd()

    def draw_segments(self):
        glLineWidth(1)
        glBegin(GL_LINES)
        for segment in self.score:
            self.draw_segment(segment, opacity=0.3)
        glEnd()

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

    def draw_segment(self, segment, opacity):
        player_id = self.orchestra.get_player_for_segment(segment).id
        if self._peer_buttons[player_id].GetValue() == True:
            pen = self.get_pen_for_player(player_id)
            self.set_pen(pen, opacity)
            x1 = self.time_to_px(segment["onset"])
            x2 = self.time_to_px(segment["onset"] + segment["duration"])
            y1 = self.byte_to_py(segment["begin"])
            y2 = self.byte_to_py(segment["end"])
            glVertex2f(x1, y1)
            glVertex2f(x2, y2)

    def set_pen(self, pen, opacity=1):
        colour = pen.GetColour()
        glColor4f(colour.Red()/255.0, colour.Green()/255.0, colour.Blue()/255.0, opacity)

    def draw_line(self, x1, y1, x2, y2):
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glEnd()

    def get_pen_for_player(self, player_id):
        pen_id = player_id % len(self.player_pens)
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

    def highlight_segment(self, segment):
        self._segments_being_played[segment["id"]] = True
        wx.CallAfter(self.timeline.Refresh)

    def unhighlight_segment(self, segment):
        if self._segment_is_being_played(segment):
            del self._segments_being_played[segment["id"]]
            wx.CallAfter(self.timeline.Refresh)

    def _segment_is_being_played(self, segment):
        return segment["id"] in self._segments_being_played

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
