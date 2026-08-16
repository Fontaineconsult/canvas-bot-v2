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


def card(parent, ctrl, theme, thickness=2):
    """Wrap a control in a border-colored panel so it reads as a raised card.

    Big data surfaces (the log, the content table, the pattern lists) are white/
    near-black insets sitting on the cooler panel canvas; this outline gives them
    a defined edge instead of bleeding into the panel. ``ctrl`` is reparented into
    the returned holder, which should be added to the sizer in ``ctrl``'s place.

    The border is the holder's background showing through even padding on every
    side, so it is uniform on all four edges — unlike a native control border,
    which is a 3D bevel (light top/left, dark bottom/right). For that reason the
    wrapped controls are built with ``wx.BORDER_NONE`` so the two don't double up.
    Under High Contrast we draw no border and defer to system colors.
    """
    holder = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    active = getattr(theme, "active", True)
    if active:
        try:
            holder.SetBackgroundColour(theme.color("border"))
        except Exception:
            active = False
    ctrl.Reparent(holder)
    sizer.Add(ctrl, 1, wx.EXPAND | wx.ALL, thickness if active else 0)
    holder.SetSizer(sizer)
    return holder


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
    """A native wx.Button marked as the default/primary action.

    We use SetDefault() — on Win10/11 the *default* button is drawn by the OS
    with the system accent treatment, which is the native primary-button idiom
    and is guaranteed to meet system contrast in every state (normal, hover,
    pressed, focused). We deliberately do NOT set a custom background: native
    MSW buttons render a custom bg as a washed, low-contrast fill, which is the
    contrast problem we're avoiding. A bold label adds emphasis.
    """
    btn = make_button(parent, label, handler, name=name, tooltip=tooltip)
    try:
        btn.SetDefault()
        font = btn.GetFont()
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        btn.SetFont(font)
        # Opt out of the tree-wide apply_font pass so the bold weight survives.
        btn._keep_font = True
    except Exception:
        pass
    return btn


def make_checkbox(parent, label, name=None, tooltip=""):
    """Create a wx.CheckBox with '&' mnemonic, accessible name, tooltip."""
    cb = wx.CheckBox(parent, label=label)
    set_name(cb, name or label.replace("&", ""))
    if tooltip:
        cb.SetToolTip(tooltip)
    _bind_enter_toggle(cb)
    return cb


def _bind_enter_toggle(cb):
    """Let Enter toggle a checkbox, not just Space.

    Native wx.CheckBox only responds to Space. With a default button set (Run),
    pressing Enter is grabbed by the top-level window for default-button
    activation BEFORE it reaches the focused checkbox as a key-down — so binding
    EVT_KEY_DOWN here never fires. EVT_CHAR_HOOK is delivered to the focused
    control first (ahead of the default-button machinery), so we catch Enter
    there, toggle the value, post the normal EVT_CHECKBOX so dependent handlers
    run, and consume the key so it does not also fire the default button.
    """
    def on_char_hook(event):
        if (event.GetKeyCode() in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER)
                and not event.HasAnyModifiers()):
            cb.SetValue(not cb.GetValue())
            evt = wx.CommandEvent(wx.wxEVT_CHECKBOX, cb.GetId())
            evt.SetInt(1 if cb.GetValue() else 0)
            evt.SetEventObject(cb)
            cb.GetEventHandler().ProcessEvent(evt)
            return  # consume Enter (do not Skip → won't trigger default button)
        event.Skip()

    cb.Bind(wx.EVT_CHAR_HOOK, on_char_hook)


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

    def __init__(self, parent, announce_columns=None, border=True, **kw):
        # LC_HRULES/LC_VRULES draw grid lines: the horizontal rule below the
        # header cleanly separates it from the data rows, and vertical rules
        # divide the columns — native, no custom drawing, accessibility-neutral.
        # ``border=False`` (used when the list is wrapped by ``card()``) drops the
        # native beveled border so it doesn't double up with the card's flat
        # outline — the bevel's light top/left highlight otherwise reads as a
        # white gap inside the card frame.
        edge = wx.BORDER_THEME if border else wx.BORDER_NONE
        style = kw.pop("style", wx.LC_REPORT | wx.LC_SINGLE_SEL
                       | wx.LC_HRULES | wx.LC_VRULES | edge)
        super().__init__(parent, style=style, **kw)
        self._headings = []
        # Indices of columns to include in the spoken summary (default: all).
        self._announce_columns = announce_columns
        self._row_data = []   # parallel list of the original row dicts (optional)
        self._rows = []       # current display rows (list of cell-string lists)
        self._bg_for = None   # row-coloring callback, reused on re-sort
        self._sort_col = None  # column currently sorted by
        self._sort_asc = True  # sort direction
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_select)
        self.Bind(wx.EVT_LIST_COL_CLICK, self._on_col_click)

    def set_columns(self, columns):
        """columns: list of (heading, width) or (heading, width, wx.LIST_FORMAT_*)."""
        self.ClearAll()
        self._headings = []
        self._sort_col = None  # column set changed; drop any prior sort state
        for i, col in enumerate(columns):
            heading = col[0]
            width = col[1] if len(col) > 1 else wx.LIST_AUTOSIZE
            fmt = col[2] if len(col) > 2 else wx.LIST_FORMAT_LEFT
            # Upper-case the visible heading so it reads distinctly from the
            # title-case data rows; keep the original for the spoken summary.
            self.InsertColumn(i, heading.upper(), format=fmt, width=width)
            self._headings.append(heading)

    def set_rows(self, rows, row_data=None, bg_for=None):
        """Populate rows.

        rows: list of lists of cell strings.
        row_data: optional parallel list of dicts kept for callers (get_row_data).
        bg_for: optional callable(row_index, row_data) -> wx.Colour or None for
                per-row background (status coloring).

        Retains the data so header clicks can re-sort; if a sort column is
        already active it is re-applied to the new data.
        """
        self._rows = [list(r) for r in rows]
        self._row_data = list(row_data) if row_data is not None else [None] * len(rows)
        self._bg_for = bg_for
        if self._sort_col is not None:
            self._apply_sort()
        self._render()

    def _render(self):
        """Paint the current self._rows/_row_data into the control."""
        self.DeleteAllItems()
        for r, cells in enumerate(self._rows):
            idx = self.InsertItem(r, str(cells[0]) if cells else "")
            for c in range(1, len(cells)):
                self.SetItem(idx, c, str(cells[c]))
            if self._bg_for is not None:
                colour = self._bg_for(r, self._row_data[r])
                if colour is not None:
                    self.SetItemBackgroundColour(idx, colour)

    @staticmethod
    def _sort_key(value):
        """Numeric-aware key: numbers sort before text, ascending naturally."""
        s = (value or "").strip()
        try:
            return (0, float(s))
        except (TypeError, ValueError):
            return (1, s.casefold())

    def _apply_sort(self):
        """Reorder self._rows and self._row_data by the active sort column."""
        col = self._sort_col
        if col is None or not self._rows:
            return
        paired = list(zip(self._rows, self._row_data))
        paired.sort(
            key=lambda pr: self._sort_key(pr[0][col] if col < len(pr[0]) else ""),
            reverse=not self._sort_asc,
        )
        self._rows = [p[0] for p in paired]
        self._row_data = [p[1] for p in paired]

    def _update_header_arrows(self):
        """Show ▲/▼ on the sorted column heading, plain on the rest."""
        for i, heading in enumerate(self._headings):
            text = heading.upper()
            if i == self._sort_col:
                text += "  " + ("▲" if self._sort_asc else "▼")
            col = self.GetColumn(i)
            col.SetText(text)
            self.SetColumn(i, col)

    def _on_col_click(self, event):
        col = event.GetColumn()
        if col < 0 or col >= len(self._headings):
            return
        if self._sort_col == col:
            self._sort_asc = not self._sort_asc  # toggle direction
        else:
            self._sort_col = col
            self._sort_asc = True
        self._apply_sort()
        self._render()
        self._update_header_arrows()
        direction = "ascending" if self._sort_asc else "descending"
        a11y.announce(f"Sorted by {self._headings[col]}, {direction}", interrupt=True)

    def set_cell(self, row, col, text):
        """Update one cell's text in place (display + retained row data).

        Keeps ``self._rows`` in sync so a later re-sort re-renders the new
        text instead of reverting to the original cell value.
        """
        if 0 <= row < len(self._rows) and 0 <= col < len(self._rows[row]):
            self._rows[row][col] = str(text)
            self.SetItem(row, col, str(text))

    def find_row_index(self, predicate):
        """Index of the first row whose row_data satisfies ``predicate``.

        Row order follows the current (possibly sorted) display order, so the
        returned index is valid for set_cell. Returns -1 when no row matches.
        """
        for i, rd in enumerate(self._row_data):
            try:
                if predicate(rd):
                    return i
            except Exception:
                continue
        return -1

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
