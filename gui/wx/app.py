"""wxPython application shell for Canvas Bot.

Builds the main frame with a Notebook (Run / Content / Patterns), applies the
accessible theme, and wires the menu/accelerators. Panels are added as they are
implemented; the app runs with whatever panels are present.
"""

import os
import sys

import wx

from gui.wx import a11y
from gui.wx import theme as theme_mod
from gui.wx.run_panel import RunPanel


APP_TITLE = "Canvas Bot"


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title=APP_TITLE, size=(960, 820))
        self.theme = theme_mod.Theme()

        self._set_icon()

        self.notebook = wx.Notebook(self)
        # Frame + notebook chrome use the grey panel color (not white window_bg),
        # so the area around/behind the tab strip matches the panels instead of
        # showing as an odd white band against the grey content.
        self.theme.apply_panel(self)
        self.theme.apply_panel(self.notebook)

        # Run tab (always present)
        self.run_panel = RunPanel(self.notebook, self.theme)
        self.notebook.AddPage(self._wrap_page(self.run_panel), "Run")

        # Content + Patterns panels are added when their modules are available.
        self.content_panel = None
        self.pattern_panel = None
        self._add_optional_panels()

        self._build_menu()
        self._build_tab_accelerators()

        self.CreateStatusBar()
        self.SetStatusText("Ready")

        # Modern UI font across the whole tree, then Win10/11 window chrome.
        self.theme.apply_font(self)
        self._bold_tabs()
        self._apply_chrome()
        self.Bind(wx.EVT_SHOW, self._on_show)

        self.SetMinSize((760, 660))
        self.Centre()

        # Surface configuration/token state at launch — visibly AND spoken — so
        # a screen-reader user learns about a missing/expired token immediately
        # instead of only when a scan fails.
        self._validate_config_async()

    def _set_status(self, text, speak=True):
        """Update the frame status bar and (optionally) speak it.

        wx's native status bar is not auto-announced by screen readers, so we
        mirror anything important through the Run panel's spoken status line.
        """
        self.SetStatusText(text)
        if speak:
            if self.run_panel is not None:
                self.run_panel.set_status(text, speak=True)
            else:
                a11y.announce(text, interrupt=True)

    def _validate_config_async(self):
        """Check config presence, then validate the token off the UI thread.

        Both outcomes are reported through the spoken status line. Network I/O
        (the /users/self call) runs on a daemon thread inside
        app_service.validate_token_async; results marshal back via wx.CallAfter.
        """
        from gui.core import app_service
        try:
            ok, message = app_service.get_config_status()
        except Exception as exc:
            self._set_status(f"Configuration check failed: {exc}")
            return
        if not ok:
            # e.g. "Not Configured" / "No API Token" — actionable, so speak it.
            self._set_status(message)
            return

        self._set_status("Validating Canvas token…")

        def on_result(valid, msg, info):
            def apply():
                if valid:
                    name = (info or {}).get("name") or "Canvas"
                    self._set_status(f"Ready — connected as {name}")
                else:
                    # Misconfiguration: expired/rejected token, wrong URL, etc.
                    self._set_status(f"Warning — {msg}")
            wx.CallAfter(apply)

        app_service.validate_token_async(on_result)

    def _build_tab_accelerators(self):
        """Give each tab an Alt+digit shortcut.

        wx.Notebook tab labels can't carry '&' mnemonics on Windows, so we wire
        Alt+1 / Alt+2 / Alt+3 (and Ctrl+Tab works natively) to select tabs. The
        digit hint is appended to each tab label so it's discoverable, and the
        accelerator table makes it work from anywhere in the window.
        """
        entries = []
        for i in range(self.notebook.GetPageCount()):
            base = self.notebook.GetPageText(i).split("  (Alt+")[0]
            self.notebook.SetPageText(i, f"{base}  (Alt+{i + 1})")
            ident = wx.NewIdRef()
            self.Bind(wx.EVT_MENU, lambda e, idx=i: self.notebook.SetSelection(idx), id=ident)
            entries.append(wx.AcceleratorEntry(wx.ACCEL_ALT, ord(str(i + 1)), ident))
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

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
        about_item = help_menu.Append(wx.ID_ABOUT, "&Help\tF1", "Open Canvas Bot help")
        welcome_item = help_menu.Append(wx.ID_ANY, "Show &Welcome", "Show the welcome guide")
        self.Bind(wx.EVT_MENU, lambda e: self._about(), about_item)
        self.Bind(wx.EVT_MENU, lambda e: self._welcome(force=True), welcome_item)
        bar.Append(help_menu, "&Help")

        self.SetMenuBar(bar)
        # Best-effort: tint the menu bar to the panel grey so it doesn't sit as a
        # white band above the (now grey) chrome. The native Win32 menu bar is
        # OS-drawn and often ignores this — accepted; we don't owner-draw menus
        # (that would degrade screen-reader support). No-op under High Contrast.
        if self.theme.active:
            try:
                bar.SetBackgroundColour(self.theme.color("panel_bg"))
                bar.SetForegroundColour(self.theme.color("text"))
            except Exception:
                pass

    def _cli(self, flag):
        from gui.core import app_service
        ok, msg = app_service.launch_cli(flag)
        self._set_status(msg)
        # Credential resets change config/token state — re-validate (and speak
        # the new state) shortly after the CLI window has had time to run.
        if flag in ("--reset_canvas_params", "--reset_canvas_studio_params"):
            self._set_status("After finishing the console window, reopen to re-check your token.")

    def _open_log(self):
        from gui.core import app_service
        ok, msg = app_service.open_log_file()
        self._set_status(msg)

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
            self.notebook.AddPage(self._wrap_page(self.content_panel), "Content")
        except Exception:
            pass
        try:
            from gui.wx.pattern_panel import PatternPanel
            self.pattern_panel = PatternPanel(self.notebook, self.theme)
            self.notebook.AddPage(self._wrap_page(self.pattern_panel), "Patterns")
        except Exception:
            pass

    def _bold_tabs(self):
        """Bold the notebook tab labels (native, accessibility-safe).

        On MSW the native tab control renders its labels in the notebook's own
        font, so a bold copy of the base font makes the tab text bold without
        touching page contents (each child keeps the font apply_font gave it).
        Set after the tree-wide font pass and flagged ``_keep_font`` so it isn't
        overwritten. No-op friendly: failures are swallowed.
        """
        try:
            font = wx.Font(self.theme.base_font())
            font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)  # 600 — lighter than full bold
            theme_mod._force_font_quality(font)
            self.notebook._keep_font = True
            self.notebook.SetFont(font)
            # Soften the tab label color ~25% toward neutral grey so the now-bold
            # text reads a touch lighter. Derived from the palette so it tracks
            # light/dark. (Native tab controls may draw their own label color and
            # ignore this — accepted, same as the menu bar.)
            if self.theme.active:
                t = self.theme.color("text")
                grey = wx.Colour(*[round(v + (128 - v) * 0.25)
                                   for v in (t.Red(), t.Green(), t.Blue())])
                self.notebook.SetForegroundColour(grey)
            self.notebook.Refresh()
        except Exception:
            pass

    def _wrap_page(self, panel):
        """Wrap a notebook page so it gets a crisp edge under the tab strip.

        The native tab control butts content straight against the tabs; a thin
        full-width accent rule (plus a little breathing room) gives each tab a
        defined top edge. Done here once so all panels share it without each
        having to alter its own sizer. Skipped visually under High Contrast,
        where we defer to system colors.
        """
        container = wx.Panel(self.notebook)
        self.theme.apply_panel(container)
        sizer = wx.BoxSizer(wx.VERTICAL)
        rule = wx.Panel(container, size=wx.Size(-1, 2))
        if self.theme.active:
            rule.SetBackgroundColour(self.theme.color("accent"))
        sizer.Add(rule, 0, wx.EXPAND)
        sizer.AddSpacer(6)
        panel.Reparent(container)
        sizer.Add(panel, 1, wx.EXPAND)
        container.SetSizer(sizer)
        return container

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

    # Stop the screen-reader speech thread cleanly so its COM object is released
    # before the interpreter tears down.
    try:
        a11y.shutdown()
    except Exception:
        pass
