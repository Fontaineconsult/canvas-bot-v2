"""Single + bulk file-replace dialogs (wx).

Both flows drive ``core.orchestrator.replace_content`` (files + body rewrites) on
a worker thread, marshalling its events to the UI with ``wx.CallAfter`` and
speaking milestones through ``a11y``. Source-page rewrite targets are derived
from each row's ``source_page_url`` via ``gui.core.replace_helpers``.
"""

import os
import threading

import wx

from gui.core import replace_helpers as rh
from gui.wx import a11y, widgets, win_style


def _auth_ok():
    """Bootstrap Canvas credentials; returns True when a token is available."""
    try:
        from network.cred import (
            load_config_data_from_appdata,
            set_canvas_api_key_to_environment_variable,
        )
        load_config_data_from_appdata()
        return bool(set_canvas_api_key_to_environment_variable())
    except Exception:
        return False


# ─────────────────────────── single replace ───────────────────────────

def start_single_replace(panel, row):
    """Pick a replacement file for *row* and run the replace with progress."""
    canvas_file_id = row.get("canvas_file_id")
    title = row.get("title", "") or "file"
    if not canvas_file_id:
        wx.MessageBox("This row has no Canvas file id.", "Cannot replace",
                      wx.OK | wx.ICON_ERROR, panel)
        return

    # Initial dir: the file's downloaded folder when available.
    init_dir = ""
    save_path = row.get("save_path", "")
    if save_path and os.path.isdir(os.path.dirname(save_path)):
        init_dir = os.path.dirname(save_path)

    with wx.FileDialog(panel, f"Choose replacement for {title}",
                       defaultDir=init_dir,
                       style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
        if dlg.ShowModal() != wx.ID_OK:
            return
        local_path = dlg.GetPath()

    # Extension-match warning (non-blocking confirm).
    orig_ext = os.path.splitext(title)[1].lower()
    new_ext = os.path.splitext(local_path)[1].lower()
    if orig_ext and new_ext and orig_ext != new_ext:
        if wx.MessageBox(
            f"The replacement is a {new_ext} file but the original is {orig_ext}.\n"
            "Replace anyway?", "Type mismatch",
            wx.YES_NO | wx.ICON_WARNING, panel) != wx.YES:
            return

    if wx.MessageBox(f"Replace '{title}' with '{os.path.basename(local_path)}'?",
                     "Confirm replace", wx.YES_NO | wx.ICON_QUESTION, panel) != wx.YES:
        return

    if not _auth_ok():
        wx.MessageBox("Canvas API token not found. Use Reset Config to set it.",
                      "Not authenticated", wx.OK | wx.ICON_ERROR, panel)
        return

    course_id = panel.get_course_id()
    body_targets = rh.derive_body_targets([row])
    dlg = _ProgressDialog(panel, f"Replacing {title}")
    dlg.run(course_id, [(canvas_file_id, local_path)], body_targets,
            on_success=lambda: panel.apply_replaced(canvas_file_id))
    dlg.ShowModal()
    dlg.Destroy()


class _ProgressDialog(wx.Dialog):
    """Small modal showing replace progress for one or more files."""

    def __init__(self, parent, header):
        super().__init__(parent, title="Replacing", size=(440, 180),
                         style=wx.DEFAULT_DIALOG_STYLE)
        self._cancel = threading.Event()
        self._done = False
        s = wx.BoxSizer(wx.VERTICAL)
        self._header = wx.StaticText(self, label=header)
        self._stage = widgets.StatusLine(self, label="Starting…")
        widgets.set_name(self._stage, "Replace progress")
        self._gauge = wx.Gauge(self, range=100)
        self._btn = widgets.make_button(self, "&Cancel", self._on_cancel, name="Cancel")
        s.Add(self._header, 0, wx.ALL, 10)
        s.Add(self._stage, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)
        s.Add(self._gauge, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 10)
        s.Add(self._btn, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        self.SetSizer(s)
        self.Bind(wx.EVT_CLOSE, lambda e: self._on_cancel(None))
        win_style.polish_dialog(self, win_style.theme_of(parent))

    def run(self, course_id, replace_pairs, body_targets, on_success=None):
        self._on_success = on_success

        def worker():
            from core.orchestrator import replace_content
            replace_content(
                course_id, replace_pairs, body_targets=body_targets,
                on_event=lambda name, **p: wx.CallAfter(self._event, name, p),
                cancel_event=self._cancel,
                progress_callback=lambda stage, b, t: wx.CallAfter(self._progress, stage, b, t),
            )

        threading.Thread(target=worker, daemon=True, name="cb-replace").start()

    def _progress(self, stage, b, t):
        if t:
            self._gauge.SetValue(min(100, int(b * 100 / t)))
        self._stage.SetLabel(f"{stage}… {rh.format_bytes(b)} / {rh.format_bytes(t)}")

    def _event(self, name, payload):
        if name == "preflight_started":
            self._stage.set_status("Pre-flight check…")
        elif name == "file_started":
            i, total = payload.get("index", 0) + 1, payload.get("total", 1)
            self._stage.set_status(f"Uploading file {i} of {total}…")
        elif name == "file_uploaded":
            self._stage.set_status("File uploaded")
        elif name == "file_failed":
            self._stage.set_status(f"File failed: {payload.get('reason', '')}")
        elif name == "body_updated":
            self._stage.set_status(f"Rewrote {payload.get('replaced_count', 0)} link(s) "
                                   f"in {payload.get('resource_type', '')}")
        elif name == "complete":
            self._finish(payload.get("summary", {}))

    def _finish(self, summary):
        self._done = True
        self._gauge.SetValue(100)
        msg = "Replace complete"
        self._stage.set_status(msg)
        a11y.announce(msg, interrupt=True)
        if self._on_success:
            try:
                self._on_success()
            except Exception:
                pass
        self._btn.SetLabel("&Close")

    def _on_cancel(self, _evt):
        if self._done:
            self.EndModal(wx.ID_OK)
            return
        self._cancel.set()
        self._stage.set_status("Cancelling…")
        self._btn.Enable(False)


# ─────────────────────────── bulk replace ───────────────────────────

def start_bulk_replace(panel):
    """Open the bulk replace dialog for the current course's documents."""
    if not _auth_ok():
        wx.MessageBox("Canvas API token not found. Use Reset Config to set it.",
                      "Not authenticated", wx.OK | wx.ICON_ERROR, panel)
        return
    dlg = _BulkDialog(panel)
    dlg.ShowModal()
    dlg.Destroy()


class _BulkDialog(wx.Dialog):
    def __init__(self, panel):
        course = panel.get_course_name()
        super().__init__(panel, title=f"Bulk Replace — {course}", size=(760, 580),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self._panel = panel
        self._documents = panel.get_document_rows()
        self._course_id = panel.get_course_id()
        self._match = None
        self._cancel = threading.Event()
        self._running = False
        self._build()
        win_style.polish_dialog(self, getattr(panel, "_theme", win_style.theme_of(panel)))

    def _build(self):
        s = wx.BoxSizer(wx.VERTICAL)

        folder_row = wx.BoxSizer(wx.HORIZONTAL)
        folder_row.Add(wx.StaticText(self, label="Source folder:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self._folder = wx.TextCtrl(self, style=wx.TE_READONLY)
        widgets.set_name(self._folder, "Source folder")
        folder_row.Add(self._folder, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        folder_row.Add(widgets.make_button(self, "&Pick a File…", self._on_pick,
                                           name="Pick a file in the replacement folder"), 0)
        s.Add(folder_row, 0, wx.EXPAND | wx.ALL, 8)

        self._counter = widgets.StatusLine(self, label="Pick any file in your replacement folder to start matching.")
        s.Add(self._counter, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._table = widgets.AccessibleListCtrl(self, announce_columns=[0, 1, 2])
        self._table.set_columns([("Title", 250), ("Local Match", 250), ("Status", 200)])
        s.Add(self._table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._replace_btn = widgets.make_button(self, "&Replace Matched", self._on_replace, name="Replace matched")
        self._replace_btn.Enable(False)
        self._close_btn = widgets.make_button(self, "&Close", self._on_close_btn, name="Close")
        btns.Add(self._replace_btn, 0, wx.RIGHT, 6)
        btns.Add(self._close_btn, 0)
        s.Add(btns, 0, wx.ALL | wx.ALIGN_RIGHT, 8)
        self.SetSizer(s)

    def _on_pick(self, _evt):
        with wx.FileDialog(self, "Pick any file in your replacement folder",
                           style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            folder = os.path.dirname(dlg.GetPath())
        self._folder.SetValue(folder)
        self._match = rh.match_files_to_documents(folder, self._documents)
        self._populate()

    def _populate(self):
        m = self._match
        rows, data = [], []
        for doc, local in m.matches:
            rows.append([doc.get("title", ""), os.path.basename(local), "Will replace"])
            data.append((doc, local, "Will replace"))
        for doc in m.unmatched_canvas:
            rows.append([doc.get("title", ""), "", "No match"])
            data.append((doc, None, "No match"))
        for doc in m.already_replaced:
            rows.append([doc.get("title", ""), "", "Already replaced"])
            data.append((doc, None, "Already replaced"))
        for doc in m.ambiguous:
            rows.append([doc.get("title", ""), "", "Ambiguous"])
            data.append((doc, None, "Ambiguous"))

        def bg_for(_i, rd):
            return self._panel._theme.status_bg(rd[2]) if rd else None

        self._table.set_rows(rows, row_data=data, bg_for=bg_for)
        n = len(m.matches)
        self._counter.set_status(f"{n} of {len(self._documents)} documents will be replaced.")
        self._replace_btn.Enable(n > 0)

    def _on_replace(self, _evt):
        if self._running or not self._match or not self._match.matches:
            return
        n = len(self._match.matches)
        if wx.MessageBox(f"Replace {n} file(s) in this course? This cannot be undone.",
                         "Confirm bulk replace", wx.YES_NO | wx.ICON_QUESTION, self) != wx.YES:
            return
        self._running = True
        self._replace_btn.Enable(False)
        pairs = [(doc.get("canvas_file_id"), local) for doc, local in self._match.matches]
        rows_for_targets = [doc for doc, _ in self._match.matches]
        body_targets = rh.derive_body_targets(rows_for_targets)

        def worker():
            from core.orchestrator import replace_content
            replace_content(
                self._course_id, pairs, body_targets=body_targets,
                on_event=lambda name, **p: wx.CallAfter(self._event, name, p),
                cancel_event=self._cancel,
            )

        threading.Thread(target=worker, daemon=True, name="cb-bulk").start()

    def _event(self, name, payload):
        if name == "file_started":
            i, total = payload.get("index", 0) + 1, payload.get("total", 1)
            self._counter.set_status(f"Replacing {i} of {total}…")
        elif name == "file_uploaded":
            new_id = payload.get("new_file_id")
            old_id = payload.get("old_file_id")
            # reflect into the underlying viewer
            for doc, _ in (self._match.matches or []):
                if doc.get("canvas_file_id") == old_id:
                    self._panel.apply_replaced(old_id)
                    break
        elif name == "complete":
            self._running = False
            summary = payload.get("summary", {})
            msg = "Bulk replace complete"
            self._counter.set_status(msg)
            a11y.announce(msg, interrupt=True)

    def _on_close_btn(self, _evt):
        if self._running:
            self._cancel.set()
            self._counter.set_status("Cancelling…")
            return
        self.EndModal(wx.ID_OK)
