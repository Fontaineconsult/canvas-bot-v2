"""Native Canvas connection configuration dialog (wx).

Replaces the CLI round-trip (``--reset_canvas_params``) for the common case:
entering the Canvas instance and API token from the GUI. All persistence reuses
the framework-agnostic helpers in ``gui.core.app_service`` (which in turn call
the engine's pure setters), so no engine/CLI code is duplicated here.

Scope (v1): Canvas instance URL + API token + Test Connection. Canvas Studio is
still configured via the CLI menu item; a native Studio section can be added
later alongside this.
"""

import wx

from gui.core import app_service
from gui.wx import a11y, widgets, win_style


_INTRO = ("Connect Canvas Bot to your institution's Canvas. Enter your Canvas "
          "identifier (the subdomain in your Canvas web address) and a personal "
          "API access token. Your token is stored in the encrypted Windows "
          "Credential Vault, never in plaintext.")


class ConfigDialog(wx.Dialog):
    def __init__(self, parent, theme=None, on_saved=None):
        super().__init__(parent, title="Configure Canvas Connection",
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._theme = theme
        self._on_saved = on_saved
        self._cfg = app_service.get_canvas_config()
        self._build()
        if theme is not None:
            try:
                theme.apply_font(self)
            except Exception:
                pass
        win_style.polish_dialog(self, theme)
        # polish_dialog paints the dialog with window_bg (white); switch it to the
        # panel grey so it matches the Run/Content/Patterns panels. StaticText /
        # checkbox children are transparent and inherit it; the white input fields
        # keep their own background, exactly like the Run tab.
        if theme is not None and getattr(theme, "active", True):
            theme.apply_panel(self)
        # Size the window to its content (fonts are applied first, since they
        # affect layout) so nothing is clipped, and prevent shrinking below it.
        self.Fit()
        self.SetMinSize(self.GetSize())
        self.CentreOnParent()
        self.domain.SetFocus()

    # ── construction ──

    def _build(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(self, label=_INTRO)
        intro.Wrap(600)
        outer.Add(intro, 0, wx.ALL, 12)

        # ── Canvas instance ──
        inst_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Canvas instance")
        form = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        form.AddGrowableCol(1, 1)

        self.domain = self._add_field(
            form, "Canvas &identifier:", self._cfg["domain"],
            name="Canvas identifier", hint="e.g. sfsu  (from sfsu.instructure.com)")
        self.domain.Bind(wx.EVT_TEXT, self._on_domain)

        # Live preview of the URLs derived from the identifier.
        self.preview = wx.StaticText(self, label="")
        form.Add(wx.StaticText(self, label="Derived URLs:"), 0)
        form.Add(self.preview, 1, wx.EXPAND)
        inst_box.Add(form, 0, wx.EXPAND | wx.ALL, 6)

        # Advanced: edit the four instance values directly.
        self.cb_advanced = widgets.make_checkbox(
            self, "Advanced — edit &URLs directly",
            name="Advanced, edit URLs directly",
            tooltip="Override the auto-derived URLs (for non-standard Canvas hosts)")
        self.cb_advanced.Bind(wx.EVT_CHECKBOX, self._on_advanced)
        inst_box.Add(self.cb_advanced, 0, wx.ALL, 6)

        adv = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
        adv.AddGrowableCol(1, 1)
        self.course_root = self._add_field(
            adv, "Course page root:", self._cfg["course_page_root"], name="Course page root")
        self.api_path = self._add_field(
            adv, "API path:", self._cfg["api_path"], name="API path")
        self.studio_domain = self._add_field(
            adv, "Studio domain:", self._cfg["studio_domain"], name="Canvas Studio domain")
        for _f in (self.course_root, self.api_path, self.studio_domain):
            _f.Bind(wx.EVT_TEXT, self._mark_dirty)
        inst_box.Add(adv, 0, wx.EXPAND | wx.ALL, 6)
        outer.Add(inst_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # ── API token ──
        tok_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Canvas API token")
        state = (f"Current token: set ({self._cfg['token_masked']})"
                 if self._cfg["token_set"] else "Current token: not set")
        self.token_state = wx.StaticText(self, label=state)
        tok_box.Add(self.token_state, 0, wx.ALL, 6)
        tform = wx.FlexGridSizer(cols=2, vgap=8, hgap=8)
        tform.AddGrowableCol(1, 1)
        hint = ("leave blank to keep current" if self._cfg["token_set"]
                else "paste your Canvas access token")
        self.token = self._add_field(tform, "API &token:", "", name="API token",
                                     password=True, hint=hint)
        self.token.Bind(wx.EVT_TEXT, self._mark_dirty)
        tok_box.Add(tform, 0, wx.EXPAND | wx.ALL, 6)
        self.cb_show = widgets.make_checkbox(
            self, "&Show token", name="Show token",
            tooltip="Reveal the token you typed so you can verify it")
        self.cb_show.Bind(wx.EVT_CHECKBOX, self._on_show_token)
        tok_box.Add(self.cb_show, 0, wx.ALL, 6)
        outer.Add(tok_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # ── status line (live region) ──
        self.status = widgets.StatusLine(self, label="")
        outer.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        # ── buttons ──
        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.save_btn = widgets.make_primary_button(
            self, "&Save", self._on_save, theme=self._theme, name="Save configuration")
        self.test_btn = widgets.make_button(
            self, "&Test Connection", self._on_test, name="Test connection",
            tooltip="Save the current values, then contact Canvas to verify them")
        close_btn = wx.Button(self, wx.ID_CANCEL, "&Close")
        btns.Add(self.save_btn, 0, wx.RIGHT, 6)
        btns.Add(self.test_btn, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer(1)
        btns.Add(close_btn, 0)
        outer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)

        self.SetSizer(outer)
        self.SetEscapeId(wx.ID_CANCEL)
        self._refresh_preview()
        self._apply_advanced(False)

    def _add_field(self, grid, label, value, name=None, password=False, hint=""):
        lbl = wx.StaticText(self, label=label)
        style = wx.TE_PASSWORD if password else 0
        txt = wx.TextCtrl(self, value=value, style=style)
        widgets.set_name(txt, name or label.replace("&", "").rstrip(":"))
        if hint:
            try:
                txt.SetHint(hint)
            except Exception:
                pass
        grid.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL)
        grid.Add(txt, 1, wx.EXPAND)
        return txt

    # ── events ──

    def _on_domain(self, _evt):
        self._refresh_preview()
        self._mark_dirty()

    def _refresh_preview(self):
        urls = app_service.derive_canvas_urls(self.domain.GetValue())
        dom = urls["CANVAS_DOMAIN"]
        if dom:
            self.preview.SetLabel(f"{urls['API_PATH']}\n{urls['CANVAS_COURSE_PAGE_ROOT']}")
        else:
            self.preview.SetLabel("(enter an identifier above)")
        # When not in advanced mode, mirror the derived values into the fields so
        # they're correct if the user later flips Advanced on.
        if not self.cb_advanced.GetValue() and dom:
            self.course_root.ChangeValue(urls["CANVAS_COURSE_PAGE_ROOT"])
            self.api_path.ChangeValue(urls["API_PATH"])
            self.studio_domain.ChangeValue(urls["CANVAS_STUDIO_DOMAIN"])

    def _on_advanced(self, _evt):
        self._apply_advanced(self.cb_advanced.GetValue())

    def _apply_advanced(self, on):
        for fld in (self.course_root, self.api_path, self.studio_domain):
            fld.Enable(on)
        self.preview.Enable(not on)

    def _on_show_token(self, _evt):
        # wx.TE_PASSWORD can't be toggled in place on MSW, so swap the control.
        reveal = self.cb_show.GetValue()
        value = self.token.GetValue()
        sizer = self.token.GetContainingSizer()
        name = self.token.GetName()
        old = self.token
        style = 0 if reveal else wx.TE_PASSWORD
        new = wx.TextCtrl(self, value=value, style=style)
        widgets.set_name(new, name)
        if self._theme is not None:
            try:
                self._theme.apply_font(new)
            except Exception:
                pass
        new.Bind(wx.EVT_TEXT, self._mark_dirty)
        sizer.Replace(old, new)
        old.Destroy()
        self.token = new
        sizer.Layout()
        self.token.SetFocus()

    def _gather(self):
        """Return (kwargs for save_canvas_config). Advanced overrides derive."""
        token = self.token.GetValue().strip()
        if self.cb_advanced.GetValue():
            urls = {
                "CANVAS_DOMAIN": self.domain.GetValue().strip().lower(),
                "CANVAS_COURSE_PAGE_ROOT": self.course_root.GetValue().strip(),
                "API_PATH": self.api_path.GetValue().strip(),
                "CANVAS_STUDIO_DOMAIN": self.studio_domain.GetValue().strip(),
            }
            return {"urls": urls, "token": token}
        return {"domain": self.domain.GetValue().strip(), "token": token}

    def _do_save(self):
        """Persist; return (ok, message). Updates the token-state line on success."""
        ok, msg = app_service.save_canvas_config(**self._gather())
        if ok:
            self._cfg = app_service.get_canvas_config()
            self.token_state.SetLabel(
                f"Current token: set ({self._cfg['token_masked']})"
                if self._cfg["token_set"] else "Current token: not set")
            if callable(self._on_saved):
                try:
                    self._on_saved()
                except Exception:
                    pass
        return ok, msg

    def _set_status(self, text, level="info", speak=True):
        """Show a color-coded, spoken status message.

        ``level`` picks the color (success/error/muted/info → text) so the
        outcome is obvious at a glance; the text itself always states the result
        so meaning never depends on color alone. ``speak`` announces it through
        the live region (assertive) for screen-reader users — left off only for
        the passive "unsaved changes" hint so typing isn't chatty.
        """
        if self._theme is not None and getattr(self._theme, "active", True):
            key = {"success": "success", "error": "error",
                   "muted": "muted_text"}.get(level, "text")
            try:
                self.status.SetForegroundColour(self._theme.color(key))
            except Exception:
                pass
        self.status.set_status(text, speak=speak)
        self.status.Refresh()

    def _mark_dirty(self, _evt=None):
        """Note unsaved edits so a prior 'Saved' message can't mislead."""
        self._set_status("Unsaved changes — press Save to apply.", "muted", speak=False)

    def _on_save(self, _evt):
        ok, msg = self._do_save()
        if ok:
            self._set_status("Configuration saved.", "success")
        else:
            self._set_status(f"Not saved — {msg}", "error")

    def _on_test(self, _evt):
        # Test what's on screen: save first so validate_api_token reads it.
        ok, msg = self._do_save()
        if not ok:
            self._set_status(f"Not saved — {msg}", "error")
            return
        self._set_status("Saved. Testing connection…", "info")
        self.save_btn.Enable(False)
        self.test_btn.Enable(False)

        def on_result(valid, message, info):
            def apply():
                self.save_btn.Enable(True)
                self.test_btn.Enable(True)
                if valid:
                    name = (info or {}).get("name") or "Canvas"
                    self._set_status(f"Connected — signed in as {name}", "success")
                else:
                    self._set_status(f"Connection failed — {message}", "error")
            wx.CallAfter(apply)

        app_service.validate_token_async(on_result)


def show_config(parent, theme=None, on_saved=None):
    """Open the Canvas configuration dialog modally."""
    if theme is None:
        theme = win_style.theme_of(parent)
    dlg = ConfigDialog(parent, theme=theme, on_saved=on_saved)
    a11y.announce("Configure Canvas connection", interrupt=True)
    dlg.ShowModal()
    dlg.Destroy()
