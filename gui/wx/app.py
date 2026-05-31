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

        self._build_menu()

        self.CreateStatusBar()
        self.SetStatusText("Ready")

        # Modern UI font across the whole tree, then Win10/11 window chrome.
        self.theme.apply_font(self)
        self._apply_chrome()
        self.Bind(wx.EVT_SHOW, self._on_show)

        self.SetMinSize((760, 660))
        self.Centre()

    def _apply_chrome(self):
        """Match the title bar to the theme and round corners (Win10/11)."""
        from gui.wx import win_style
        # Under High Contrast we defer to the system, so don't force a dark bar.
        dark = self.theme.dark and self.theme.active
        win_style.modernize(self, dark=dark, rounded=True)

    def _on_show(self, event):
        # Some DWM attributes only "take" once the HWND is realized/shown.
        if event.IsShown():
            self._apply_chrome()
        event.Skip()

    def _build_menu(self):
        """Menu bar: File (Exit) + Config + Help. Mnemonics + accelerators give
        keyboard access; native menus are fully screen-reader accessible."""
        bar = wx.MenuBar()

        file_menu = wx.Menu()
        exit_item = file_menu.Append(wx.ID_EXIT, "E&xit\tAlt+F4", "Quit Canvas Bot")
        self.Bind(wx.EVT_MENU, lambda e: self.Close(), exit_item)
        bar.Append(file_menu, "&File")

        cfg_menu = wx.Menu()
        view_cfg = cfg_menu.Append(wx.ID_ANY, "&View Config\tCtrl+Shift+V", "Show configuration status")
        reset_api = cfg_menu.Append(wx.ID_ANY, "Reset Canvas &API Credentials", "Reconfigure token + instance URL")
        reset_studio = cfg_menu.Append(wx.ID_ANY, "Reset Canvas &Studio Credentials", "Reconfigure Canvas Studio OAuth")
        open_log = cfg_menu.Append(wx.ID_ANY, "Open &Log File", "Open the Canvas Bot log")
        self.Bind(wx.EVT_MENU, lambda e: self._cli("--config_status"), view_cfg)
        self.Bind(wx.EVT_MENU, lambda e: self._cli("--reset_canvas_params"), reset_api)
        self.Bind(wx.EVT_MENU, lambda e: self._cli("--reset_canvas_studio_params"), reset_studio)
        self.Bind(wx.EVT_MENU, lambda e: self._open_log(), open_log)
        bar.Append(cfg_menu, "&Config")

        help_menu = wx.Menu()
        about_item = help_menu.Append(wx.ID_ABOUT, "&About\tF1", "About Canvas Bot")
        welcome_item = help_menu.Append(wx.ID_ANY, "Show &Welcome", "Show the welcome guide")
        self.Bind(wx.EVT_MENU, lambda e: self._about(), about_item)
        self.Bind(wx.EVT_MENU, lambda e: self._welcome(force=True), welcome_item)
        bar.Append(help_menu, "&Help")

        self.SetMenuBar(bar)

    def _cli(self, flag):
        from gui.core import app_service
        ok, msg = app_service.launch_cli(flag)
        self.SetStatusText(msg)

    def _open_log(self):
        from gui.core import app_service
        ok, msg = app_service.open_log_file()
        self.SetStatusText(msg)

    def _about(self):
        from gui.wx.about import show_about
        show_about(self)

    def _welcome(self, force=False):
        from gui.core import settings
        from gui.wx import about
        if force:
            # Temporarily clear the flag so the dialog shows on demand.
            data_first = settings.is_first_run()
            if not data_first:
                # show directly without toggling persisted state
                dlg = about._text_dialog(self, "Welcome to Canvas Bot",
                                         about._WELCOME_TEXT, close_label="&Get Started")
                dlg.ShowModal()
                dlg.Destroy()
                return
        about.show_welcome_if_first_run(self)

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
