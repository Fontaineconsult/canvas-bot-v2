"""wxPython application shell for Canvas Bot.

Builds the main frame with a Notebook (Run / Content / Patterns), applies the
accessible theme, and wires the menu/accelerators. Panels are added as they are
implemented; the app runs with whatever panels are present.
"""

import os
import sys

import wx

from gui.wx import theme as theme_mod
from gui.wx.run_panel import RunPanel


APP_TITLE = "Canvas Bot"


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title=APP_TITLE, size=(960, 820))
        self.theme = theme_mod.Theme()

        self._set_icon()

        self.notebook = wx.Notebook(self)
        self.theme.apply_window(self)
        self.theme.apply_window(self.notebook)

        # Run tab (always present)
        self.run_panel = RunPanel(self.notebook, self.theme)
        self.notebook.AddPage(self.run_panel, "Run")

        # Content + Patterns panels are added when their modules are available.
        self.content_panel = None
        self.pattern_panel = None
        self._add_optional_panels()

        self.CreateStatusBar()
        self.SetStatusText("Ready")

        self.SetMinSize((760, 660))
        self.Centre()

    def _add_optional_panels(self):
        try:
            from gui.wx.content_panel import ContentPanel
            self.content_panel = ContentPanel(self.notebook, self.theme)
            self.notebook.AddPage(self.content_panel, "Content")
        except Exception:
            pass
        try:
            from gui.wx.pattern_panel import PatternPanel
            self.pattern_panel = PatternPanel(self.notebook, self.theme)
            self.notebook.AddPage(self.pattern_panel, "Patterns")
        except Exception:
            pass

    def _set_icon(self):
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cb.ico")
        if getattr(sys, "frozen", False):
            icon_path = os.path.join(sys._MEIPASS, "cb.ico")
        if os.path.isfile(icon_path):
            try:
                self.SetIcon(wx.Icon(icon_path, wx.BITMAP_TYPE_ICO))
            except Exception:
                pass

    def on_scan_complete(self):
        """Called by the Run panel after a scan; refresh Content Viewer."""
        if self.content_panel is not None and hasattr(self.content_panel, "refresh_courses"):
            self.content_panel.refresh_courses()


def run_wx_gui():
    """Entry point: construct the wx.App and show the main frame."""
    app = wx.App()
    frame = MainFrame()
    frame.Show()

    # First-run welcome (best-effort; module may not exist yet).
    try:
        from gui.core import settings
        from gui.wx.about import show_welcome_if_first_run
        if settings.is_first_run():
            show_welcome_if_first_run(frame)
    except Exception:
        pass

    app.MainLoop()
