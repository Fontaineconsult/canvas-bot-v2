"""Reusable accessible wx widgets and helpers.

Keeps the accessibility plumbing in one place so panels stay declarative:
- ``labeled_text`` / ``labeled_choice`` pair a StaticText label with a control
  and set the control's accessible name (NVDA reads a generic role otherwise).
- ``AccessibleListCtrl`` is a report-mode list that announces the selected row
  (with column context) through ``a11y`` — screen readers don't narrate
  multi-column selection well on their own.
- ``StatusLine`` is a StaticText that doubles as a live region: setting its text
  also speaks it.
"""

import wx

from gui.wx import a11y


def set_name(ctrl, name):
    """Set a control's accessible name (and label fallback)."""
    try:
        ctrl.SetName(name)
    except Exception:
        pass
    return ctrl


def labeled_text(parent, label, value="", name=None, password=False,
                 readonly=False, hint=""):
    """A horizontal (StaticText label + wx.TextCtrl) pair.

    Returns (sizer, textctrl). The label uses '&' mnemonic support and the text
    control gets an explicit accessible name so screen readers announce it.
    """
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    lbl = wx.StaticText(parent, label=label)
    style = 0
    if password:
        style |= wx.TE_PASSWORD
    if readonly:
        style |= wx.TE_READONLY
    txt = wx.TextCtrl(parent, value=value, style=style)
    if hint:
        try:
            txt.SetHint(hint)
        except Exception:
            pass
    set_name(txt, name or label.replace("&", "").rstrip(":"))
    sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    sizer.Add(txt, 1, wx.ALIGN_CENTER_VERTICAL)
    return sizer, txt


def labeled_choice(parent, label, choices, name=None):
    """A (StaticText + wx.Choice) pair. Returns (sizer, choice)."""
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    lbl = wx.StaticText(parent, label=label)
    choice = wx.Choice(parent, choices=choices or [])
    set_name(choice, name or label.replace("&", "").rstrip(":"))
    sizer.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    sizer.Add(choice, 1, wx.ALIGN_CENTER_VERTICAL)
    return sizer, choice


def make_button(parent, label, handler, name=None, tooltip=""):
    """Create a wx.Button with '&' mnemonic, handler, accessible name, tooltip."""
    btn = wx.Button(parent, label=label)
    btn.Bind(wx.EVT_BUTTON, handler)
    set_name(btn, name or label.replace("&", ""))
    if tooltip:
        btn.SetToolTip(tooltip)
    return btn


def make_primary_button(parent, label, handler, theme=None, name=None, tooltip=""):
    """A native wx.Button styled as the accent/primary action.

    Still a native button (full MSAA/keyboard support) — we only set its
    background to the theme accent and force a high-contrast foreground. No-op
    styling under High Contrast so the user's system colors win.
    """
    btn = make_button(parent, label, handler, name=name, tooltip=tooltip)
    if theme is not None and getattr(theme, "active", True):
        try:
            accent = theme.color("accent")
            btn.SetBackgroundColour(accent)
            # Pick black/white text for best contrast on the accent.
            r, g, b = accent.Red(), accent.Green(), accent.Blue()
            luma = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
            btn.SetForegroundColour(wx.Colour("#000000") if luma > 0.5 else wx.Colour("#FFFFFF"))
        except Exception:
            pass
    return btn


def make_checkbox(parent, label, name=None, tooltip=""):
    """Create a wx.CheckBox with '&' mnemonic, accessible name, tooltip."""
    cb = wx.CheckBox(parent, label=label)
    set_name(cb, name or label.replace("&", ""))
    if tooltip:
        cb.SetToolTip(tooltip)
    return cb


class StatusLine(wx.StaticText):
    """A status label that also speaks its updates (live region).

    wx has no ARIA live region; explicit speech is the reliable way to surface
    background state changes (scan progress, validation results) to a screen
    reader user whose focus is elsewhere.
    """

    def set_status(self, text, speak=True, interrupt=True):
        self.SetLabel(text)
        if speak:
            a11y.announce(text, interrupt=interrupt)


class AccessibleListCtrl(wx.ListCtrl):
    """Report-mode list that announces row selection with column context.

    Columns are defined via ``set_columns([(heading, width, format), ...])``.
    Rows are plain lists of strings via ``set_rows``. Selecting a row speaks a
    compact "col1: val1, col2: val2" summary so a screen reader user hears the
    whole row, not just the first cell.
    """

    def __init__(self, parent, announce_columns=None, **kw):
        style = kw.pop("style", wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SUNKEN)
        super().__init__(parent, style=style, **kw)
        self._headings = []
        # Indices of columns to include in the spoken summary (default: all).
        self._announce_columns = announce_columns
        self._row_data = []  # parallel list of the original row dicts (optional)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)

    def set_columns(self, columns):
        """columns: list of (heading, width) or (heading, width, wx.LIST_FORMAT_*)."""
        self.ClearAll()
        self._headings = []
        for i, col in enumerate(columns):
            heading = col[0]
            width = col[1] if len(col) > 1 else wx.LIST_AUTOSIZE
            fmt = col[2] if len(col) > 2 else wx.LIST_FORMAT_LEFT
            self.InsertColumn(i, heading, format=fmt, width=width)
            self._headings.append(heading)

    def set_rows(self, rows, row_data=None, bg_for=None):
        """Populate rows.

        rows: list of lists of cell strings.
        row_data: optional parallel list of dicts kept for callers (get_row_data).
        bg_for: optional callable(row_index, row_data) -> wx.Colour or None for
                per-row background (status coloring).
        """
        self.DeleteAllItems()
        self._row_data = list(row_data) if row_data is not None else [None] * len(rows)
        for r, cells in enumerate(rows):
            idx = self.InsertItem(r, str(cells[0]) if cells else "")
            for c in range(1, len(cells)):
                self.SetItem(idx, c, str(cells[c]))
            if bg_for is not None:
                colour = bg_for(r, self._row_data[r])
                if colour is not None:
                    self.SetItemBackgroundColour(idx, colour)

    def get_selected_index(self):
        return self.GetFirstSelected()

    def get_selected_data(self):
        idx = self.GetFirstSelected()
        if idx < 0 or idx >= len(self._row_data):
            return None
        return self._row_data[idx]

    def _row_summary(self, idx):
        parts = []
        cols = range(self.GetColumnCount())
        if self._announce_columns is not None:
            cols = self._announce_columns
        for c in cols:
            if c >= self.GetColumnCount():
                continue
            heading = self._headings[c] if c < len(self._headings) else ""
            text = self.GetItemText(idx, c)
            if text:
                parts.append(f"{heading}: {text}" if heading else text)
        return ", ".join(parts)

    def _on_select(self, event):
        idx = event.GetIndex()
        summary = self._row_summary(idx)
        if summary:
            a11y.announce(summary, interrupt=True)
        event.Skip()
