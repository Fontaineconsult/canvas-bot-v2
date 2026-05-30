"""Pattern Manager tab (wx).

View / add / remove / validate the URL-classification regex patterns stored in
``config/re.yaml``, plus a Test box that classifies an arbitrary URL/filename
through the real pipeline. List-valued categories are editable; scalar config
values are shown read-only.

Reuses ``config.yaml_io`` (read_re / write_re / reset_re),
``sorters.sorters.reload_patterns`` and ``core.node_factory.identify_content_url``.
"""

import re

import wx

from config.yaml_io import read_re, write_re, reset_re
from gui.wx import a11y, widgets


class PatternPanel(wx.Panel):
    def __init__(self, parent, theme):
        super().__init__(parent)
        self._theme = theme
        self._data = {}
        self._category = None
        self._build()
        theme.apply_panel(self)
        self._load()

    def _build(self):
        outer = wx.BoxSizer(wx.HORIZONTAL)

        # Left: categories
        left = wx.BoxSizer(wx.VERTICAL)
        left.Add(wx.StaticText(self, label="&Categories:"), 0, wx.BOTTOM, 4)
        self.cat_list = wx.ListBox(self, style=wx.LB_SINGLE)
        widgets.set_name(self.cat_list, "Pattern categories")
        self.cat_list.Bind(wx.EVT_LISTBOX, self._on_cat)
        left.Add(self.cat_list, 1, wx.EXPAND | wx.BOTTOM, 6)
        left.Add(widgets.make_button(self, "Reset All to D&efaults", self._on_reset,
                                     name="Reset all patterns to defaults"), 0, wx.EXPAND)
        outer.Add(left, 0, wx.EXPAND | wx.ALL, 8)

        # Right: patterns + actions + test
        right = wx.BoxSizer(wx.VERTICAL)
        self.cat_header = wx.StaticText(self, label="Select a category")
        right.Add(self.cat_header, 0, wx.BOTTOM, 4)

        self.pat_list = widgets.AccessibleListCtrl(self, announce_columns=[1])
        self.pat_list.set_columns([("#", 50), ("Pattern", 480)])
        self.pat_list.Bind(wx.EVT_LIST_ITEM_SELECTED, lambda e: self._update_buttons())
        self.pat_list.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda e: self._update_buttons())
        right.Add(self.pat_list, 1, wx.EXPAND | wx.BOTTOM, 6)

        self.status = widgets.StatusLine(self, label="")
        right.Add(self.status, 0, wx.BOTTOM, 6)

        act = wx.BoxSizer(wx.HORIZONTAL)
        self.add_btn = widgets.make_button(self, "&Add Pattern", self._on_add, name="Add pattern")
        self.remove_btn = widgets.make_button(self, "Re&move Pattern", self._on_remove, name="Remove pattern")
        self.validate_btn = widgets.make_button(self, "Va&lidate", self._on_validate, name="Validate pattern")
        for b in (self.add_btn, self.remove_btn, self.validate_btn):
            act.Add(b, 0, wx.RIGHT, 4)
        right.Add(act, 0, wx.BOTTOM, 8)

        test_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Test URL / filename")
        trow = wx.BoxSizer(wx.HORIZONTAL)
        self.test_entry = wx.TextCtrl(self, style=wx.TE_PROCESS_ENTER)
        widgets.set_name(self.test_entry, "Test URL or filename")
        self.test_entry.Bind(wx.EVT_TEXT_ENTER, self._on_test)
        trow.Add(self.test_entry, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        trow.Add(widgets.make_button(self, "&Test", self._on_test, name="Test classification"), 0)
        test_box.Add(trow, 0, wx.EXPAND | wx.ALL, 4)
        self.test_result = widgets.StatusLine(self, label="")
        test_box.Add(self.test_result, 0, wx.EXPAND | wx.ALL, 4)
        right.Add(test_box, 0, wx.EXPAND)

        outer.Add(right, 1, wx.EXPAND | wx.ALL, 8)
        self.SetSizer(outer)
        self._update_buttons()

    # ── data ──

    def _load(self):
        self._data = read_re(substitute=False) or {}
        cats = sorted(self._data.keys())
        self.cat_list.Set(cats)
        if cats:
            self.cat_list.SetSelection(0)
            self._category = cats[0]
            self._show_category()

    def _is_list_category(self, cat):
        return isinstance(self._data.get(cat), list)

    def _on_cat(self, _evt):
        self._category = self.cat_list.GetStringSelection()
        self._show_category()

    def _show_category(self):
        cat = self._category
        patterns = self._data.get(cat, [])
        if not isinstance(patterns, list):
            patterns = [str(patterns)]
        rows = [[str(i + 1), p] for i, p in enumerate(patterns)]
        self.pat_list.set_rows(rows)
        editable = " (editable)" if self._is_list_category(cat) else " (read-only)"
        self.cat_header.SetLabel(f"{cat} — {len(patterns)} pattern(s){editable}")
        self.status.SetLabel("")
        self._update_buttons()

    def _update_buttons(self):
        is_list = self._category is not None and self._is_list_category(self._category)
        has_sel = self.pat_list.get_selected_index() >= 0
        self.add_btn.Enable(bool(is_list))
        self.remove_btn.Enable(bool(is_list and has_sel))
        self.validate_btn.Enable(bool(has_sel))

    def _selected_pattern(self):
        idx = self.pat_list.get_selected_index()
        if idx < 0:
            return None
        return self.pat_list.GetItemText(idx, 1)

    # ── actions ──

    def _on_add(self, _evt):
        if not self._is_list_category(self._category):
            return
        dlg = wx.TextEntryDialog(self, f"New pattern for {self._category}:", "Add pattern")
        if dlg.ShowModal() == wx.ID_OK:
            pattern = dlg.GetValue().strip()
            if not pattern:
                dlg.Destroy()
                return
            try:
                re.compile(pattern)
            except re.error as e:
                wx.MessageBox(f"Invalid regex: {e}", "Cannot add", wx.OK | wx.ICON_ERROR, self)
                dlg.Destroy()
                return
            if pattern in self._data[self._category]:
                wx.MessageBox("Pattern already exists in this category.", "Duplicate",
                              wx.OK | wx.ICON_WARNING, self)
                dlg.Destroy()
                return
            self._data[self._category].append(pattern)
            self._persist()
            self._show_category()
            a11y.announce("Pattern added", interrupt=True)
        dlg.Destroy()

    def _on_remove(self, _evt):
        pattern = self._selected_pattern()
        if pattern is None or not self._is_list_category(self._category):
            return
        if wx.MessageBox(f"Remove this pattern?\n\n{pattern}", "Remove pattern",
                         wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        try:
            self._data[self._category].remove(pattern)
        except ValueError:
            return
        self._persist()
        self._show_category()
        a11y.announce("Pattern removed", interrupt=True)

    def _on_validate(self, _evt):
        pattern = self._selected_pattern()
        if pattern is None:
            return
        try:
            compiled = re.compile(pattern)
            msg = f"Valid regex. Groups: {compiled.groups}"
            self.status.set_status(msg)
        except re.error as e:
            self.status.set_status(f"Invalid regex: {e}")

    def _on_reset(self, _evt):
        if wx.MessageBox("Reset all patterns to defaults? Custom patterns will be lost.",
                         "Reset patterns", wx.YES_NO | wx.ICON_WARNING, self) != wx.YES:
            return
        reset_re()
        self._reload_sorters()
        self._load()
        a11y.announce("Patterns reset to defaults", interrupt=True)

    def _on_test(self, _evt):
        text = self.test_entry.GetValue().strip()
        if not text:
            return
        self._reload_sorters()
        try:
            from core.node_factory import identify_content_url
            result = identify_content_url(text)
        except Exception:
            result = None
        if result:
            msg = f"Classified as: {result}"
        else:
            msg = "No match (would be classified as Unsorted)"
        self.test_result.set_status(msg)

    # ── persistence ──

    def _persist(self):
        try:
            write_re(self._data)
            self._reload_sorters()
        except Exception as e:
            wx.MessageBox(f"Could not save patterns: {e}", "Error", wx.OK | wx.ICON_ERROR, self)

    def _reload_sorters(self):
        try:
            from sorters.sorters import reload_patterns
            reload_patterns()
        except Exception:
            pass
