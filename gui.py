import wx
import threading

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

        self.width = 800
        self.height = 600
        print 1
        self.min_byte = min(tr_log.chunks, key=lambda chunk: chunk["begin"])["begin"]
        self.max_byte = max(tr_log.chunks, key=lambda chunk: chunk["end"])["end"]
        print 2
        self._chunks_being_played = {}
        self._zoom_selection_taking_place = False
        self._playing = False
        self._scrubbing = False
        self._reset_displayed_time()
        self.app = wx.App(False)
        self.unplayed_pen = wx.Pen(wx.LIGHT_GREY, width=2)
        self.player_pens = map(self.create_pens_with_colour,
                               self.PLAYER_COLOURS)
        wx.Frame.__init__(self, None, wx.ID_ANY, "Torrential Forms",
                          size=wx.Size(self.width, self.height))
        self.Bind(wx.EVT_SIZE, self._OnSize)
        self._vbox = wx.BoxSizer(wx.VERTICAL)
        self._create_control_buttons()
        self._create_clock()
        self._create_peer_buttons()
        self._create_timeline()
        self.SetSizer(self._vbox)
        self.timeline.SetFocus()
        self.Show(True)
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
        self.timeline = wx.Panel(self)
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
        self.timeline.Refresh()

    def main_loop(self):
        self.app.MainLoop()

    def _play_button_clicked(self, event):
        self._orchestra_thread = threading.Thread(target=self.orchestra.play_non_realtime)
        self._orchestra_thread.daemon = True
        self._orchestra_thread.start()
        self.play_button.Disable()
        self.stop_button.Enable()
        self._playing = True

    def _stop_button_clicked(self, event):
        self.orchestra.stop()
        self._orchestra_thread.join()
        self.stop_button.Disable()
        self.play_button.Enable()
        self._chunks_being_played = {}
        self._playing = False

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
        dc = wx.BufferedPaintDC(self.timeline)
        dc.Clear()
        dc.BeginDrawing()
        self.draw_chunks(dc)
        self.draw_time_cursor(dc)
        self.update_clock()
        if self._zoom_selection_taking_place:
            self._draw_zoom_selection(dc)
        dc.EndDrawing()

    def _draw_zoom_selection(self, dc):
        dc.SetPen(wx.LIGHT_GREY_PEN)
        dc.SetBrush(wx.TRANSPARENT_BRUSH)
        dc.DrawRectangle(self._zoom_selection_x1,
                         self._zoom_selection_y1,
                         self._zoom_selection_x2 - self._zoom_selection_x1,
                         self._zoom_selection_y2 - self._zoom_selection_y1)

    def _OnSize(self, event):
        self.Layout()
        size = self.timeline.GetClientSize()
        self.width = size.width
        self.height = size.height
        self.timeline.Refresh()

    def _reset_displayed_time(self):
        self._displayed_time_begin = 0
        self._displayed_time_end = self.tr_log.lastchunktime()

    def _zoom_out_button_clicked(self, event):
        self._reset_displayed_time()
        self.timeline.Refresh()

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
            self._displayed_time_begin = self.px_to_time(self._zoom_selection_x1)
            self._displayed_time_end = self.px_to_time(self._zoom_selection_x2)
            self._zoom_selection_taking_place = False
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

    def draw_chunks(self, dc):
        if self.tr_log.chunks:
            for chunk in self.tr_log.chunks:
                self.draw_chunk(chunk, dc)

    def draw_chunk(self, chunk, dc):
        x = self.time_to_px(chunk["t"])
        if 0 <= x < self.width:
            player_id = self.orchestra.get_player_for_chunk(chunk).id
            if self._peer_buttons[player_id].GetValue() == True:
                pen = self.get_pen_for_player_and_highlight(
                    player_id, self._chunk_is_being_played(chunk))
                dc.SetPen(pen)
                y1 = self.height - self.bytepos_to_py(chunk["begin"])
                y2 = self.height - self.bytepos_to_py(chunk["end"])
                dc.DrawLine(x, y1, x, y2)

    def create_pens_with_colour(self, rgb):
        colour = wx.Colour(*rgb)
        return {False: wx.Pen(colour, width=2),
                True: wx.Pen(colour, width=4)}

    def get_pen_for_player_and_highlight(self, player_id, highlighted):
        pen_id = player_id % len(self.player_pens)
        return self.player_pens[pen_id][highlighted]

    def draw_time_cursor(self, dc):
        dc.SetPen(wx.LIGHT_GREY_PEN)
        x = self.time_to_px(self.orchestra.get_current_log_time())
        y1 = 0
        y2 = self.height
        dc.DrawLine(x, y1, x, y2)

    def update_clock(self):
        self.clock.SetLabel('%.2f' % self.orchestra.get_current_log_time())

    def highlight_chunk(self, chunk):
        self._chunks_being_played[chunk["id"]] = True
        wx.CallAfter(self.timeline.Refresh)
        self._schedule_to_unhighlight(chunk)

    def _schedule_to_unhighlight(self, chunk):
        wx.FutureCall(1000, self._unhighlight_chunk, chunk)

    def _unhighlight_chunk(self, chunk):
        if self._chunk_is_being_played(chunk):
            del self._chunks_being_played[chunk["id"]]
            wx.CallAfter(self.timeline.Refresh)

    def _chunk_is_being_played(self, chunk):
        return chunk["id"] in self._chunks_being_played

    def time_to_px(self, t):
        return (t - self._displayed_time_begin) * self.width / (
            self._displayed_time_end - self._displayed_time_begin)

    def px_to_time(self, px):
        return self._displayed_time_begin + px * (
            self._displayed_time_end - self._displayed_time_begin) / self.width

    def bytepos_to_py(self, pos):
        return (pos - self.min_byte) * self.height / self.max_byte
