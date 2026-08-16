"""Single + bulk file-replace dialogs (wx).

Both flows drive ``core.orchestrator.replace_content`` (files + body rewrites) on
a worker thread, marshalling its events to the UI with ``wx.CallAfter`` and
speaking milestones through ``a11y``. Source-page rewrite targets are derived
from each row's ``source_page_url`` via ``gui.core.replace_helpers``.
"""

import logging
import os
import threading
import time

import wx

from gui.core import replace_helpers as rh
from gui.wx import a11y, widgets, win_style

log = logging.getLogger(__name__)


def _make_event_relay(handler):
    """Wrap a dialog's event handler for use as the orchestrator's on_event.

    Runs on the worker thread. Everything is marshalled to the UI thread with
    wx.CallAfter, but the byte-level ``file_progress`` stream (one event per
    upload chunk) is throttled to ~10 updates/sec so a large upload can't
    flood the UI event queue. Stage changes and the final chunk always pass.
    """
    state = {"last": 0.0, "stage": None}

    def relay(name, payload):
        if name == "file_progress":
            now = time.monotonic()
            stage = payload.get("stage")
            final = payload.get("bytes_read") and payload.get("bytes_read") == payload.get("total")
            if stage == state["stage"] and not final and now - state["last"] < 0.1:
                return
            state["last"], state["stage"] = now, stage
        wx.CallAfter(handler, name, payload)

    return relay


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
    # Non-modal (like the tkinter flow): Show() and let the dialog own its own
    # teardown. The worker marshals events back; on complete/error the dialog
    # closes itself and reports. A blocking ShowModal here is fragile with a
    # background worker and was the source of the hang.
    dlg = _ProgressDialog(panel, f"Replacing {title}")
    dlg.run(course_id, [(canvas_file_id, local_path)], body_targets,
            on_success=lambda: panel.apply_replaced(canvas_file_id))
    dlg.Show()


class _ProgressDialog(wx.Dialog):
    """Small non-modal dialog showing replace progress for one or more files.

    Closes itself on completion (showing a result) or on a worker exception
    (showing the error). Cancel before completion signals the cancel event; the
    orchestrator still emits ``complete`` (early=cancelled), which closes us.
    """

    def __init__(self, parent, header):
        super().__init__(parent, title="Replacing", size=(440, 180),
                         style=wx.DEFAULT_DIALOG_STYLE)
        self._cancel = threading.Event()
        self._done = False
        self._file_ok = False  # set when a file_done reports status 'replaced'
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
        self._total_steps = max(1, len(replace_pairs) + len(body_targets))
        self._step = 0
        self._file_label = "Uploading"     # refreshed by each file_started
        self._spoken_milestones = set()    # per-file spoken 25/50/75% marks

        def worker():
            # Any exception here would otherwise kill the thread silently, so
            # 'complete' never fires and the dialog hangs forever. Marshal it
            # back to close the dialog and report (matches the tkinter flow).
            try:
                from core.orchestrator import replace_content
                # orchestrator calls on_event(stage, payload_dict) positionally.
                replace_content(
                    course_id, replacements=replace_pairs, body_targets=body_targets,
                    on_event=_make_event_relay(self._event),
                    cancel_event=self._cancel,
                )
            except Exception as exc:
                log.exception("Replace worker crashed")
                wx.CallAfter(self._error, str(exc))

        threading.Thread(target=worker, daemon=True, name="cb-replace").start()

    def _advance(self):
        self._step = min(self._total_steps, self._step + 1)
        self._gauge.SetValue(int(self._step * 100 / self._total_steps))

    def _event(self, name, payload):
        # Stage names + payload keys match core.orchestrator's on_event contract.
        if name == "preflight_started":
            self._stage.set_status("Pre-flight check")
        elif name == "preflight_failed":
            nf = len(payload.get("failed_files", []))
            nb = len(payload.get("failed_bodies", []))
            self._stage.set_status(f"Pre-flight failed: {nf} file(s), {nb} page(s)")
        elif name == "file_started":
            i = payload.get("idx", 0) + 1
            total = payload.get("total", 1)
            self._file_label = f"Uploading file {i} of {total}"
            self._spoken_milestones = set()
            self._stage.set_status(self._file_label)
        elif name == "file_progress":
            self._on_file_progress(payload)
        elif name == "file_done":
            report = payload.get("report")
            if report is not None and getattr(report, "status", None) == "replaced":
                self._file_ok = True
            self._advance()
        elif name == "body_started":
            i = payload.get("idx", 0) + 1
            total = payload.get("total", 1)
            rt = payload.get("resource_type", "")
            self._stage.set_status(f"Rewriting {rt} {i} of {total}")
        elif name == "body_done":
            self._advance()
        elif name == "complete":
            self._finish(payload.get("summary", {}))

    def _on_file_progress(self, payload):
        """Byte-level upload feedback: smooth gauge + silent status text.

        Every tick updates the label with speak=False — per-chunk speech would
        flood a screen reader — while 25/50/75% milestones are spoken once per
        file (non-interrupting) so progress is audible without chatter.
        """
        stage = payload.get("stage")
        if stage == "confirming":
            self._stage.set_status(f"{self._file_label} — confirming…", speak=False)
            return
        if stage != "uploading":
            return
        done, total = payload.get("bytes_read") or 0, payload.get("total") or 0
        if total <= 0:
            return
        pct = min(100, int(done * 100 / total))
        self._stage.set_status(
            f"{self._file_label} — {rh.format_bytes(done)} of "
            f"{rh.format_bytes(total)} ({pct}%)", speak=False)
        # Gauge: fractional progress inside the current step, so one big file
        # moves the bar continuously instead of jumping at file_done.
        frac = (self._step + done / total) / self._total_steps
        self._gauge.SetValue(min(100, int(frac * 100)))
        crossed = [m for m in (25, 50, 75)
                   if pct >= m and m not in self._spoken_milestones]
        if crossed:
            # Speak only the highest new milestone — a fast upload crossing
            # several at once shouldn't queue three announcements.
            self._spoken_milestones.update(crossed)
            a11y.announce(f"{crossed[-1]} percent", interrupt=False)

    def _finish(self, summary):
        if self._done:
            return
        self._done = True
        early = (summary or {}).get("early")
        if early:
            icon, title = wx.ICON_WARNING, "Replace incomplete"
            msg = f"Replace did not complete ({early})."
        elif self._file_ok:
            icon, title = wx.ICON_INFORMATION, "Replace complete"
            msg = "Replace complete."
        else:
            icon, title = wx.ICON_WARNING, "Replace failed"
            msg = "The replace did not complete. See the log for details."
        a11y.announce(msg, interrupt=True)
        # Only mark the row replaced if a file actually succeeded.
        if self._file_ok and self._on_success:
            try:
                self._on_success()
            except Exception:
                pass
        # Close the progress dialog, then report (same order as tkinter).
        parent = self.GetParent()
        self._close()
        wx.MessageBox(msg, title, wx.OK | icon, parent)

    def _error(self, message):
        if self._done:
            return
        self._done = True
        parent = self.GetParent()
        self._close()
        wx.MessageBox(f"Replace error:\n\n{message}", "Replace error",
                      wx.OK | wx.ICON_ERROR, parent)

    def _close(self):
        try:
            self.Destroy()
        except Exception:
            pass

    def _on_cancel(self, _evt):
        # Cancel button / X / Escape before completion: signal cancel and wait
        # for the orchestrator to emit 'complete' (early=cancelled), which
        # closes us via _finish. Repeat clicks are no-ops.
        if self._done or self._cancel.is_set():
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

        self._cur_file = ""  # "i of total" label of the file now uploading

        def worker():
            # Guard against a silent thread death leaving rows stuck on
            # "Replacing…" — marshal any exception back to reset state + report.
            try:
                from core.orchestrator import replace_content
                # orchestrator calls on_event(stage, payload_dict) positionally.
                replace_content(
                    self._course_id, replacements=pairs, body_targets=body_targets,
                    on_event=_make_event_relay(self._event),
                    cancel_event=self._cancel,
                )
            except Exception as exc:
                log.exception("Bulk replace worker crashed")
                wx.CallAfter(self._error, str(exc))

        threading.Thread(target=worker, daemon=True, name="cb-bulk").start()

    def _error(self, message):
        self._running = False
        self._counter.set_status("Bulk replace failed.")
        self._replace_btn.Enable(True)
        wx.MessageBox(f"Bulk replace error:\n\n{message}", "Bulk replace error",
                      wx.OK | wx.ICON_ERROR, self)

    def _row_for_file(self, old_id):
        """Table row index for the document with this canvas_file_id, or -1.

        Looked up per event (not cached) so a mid-run header re-sort can't
        leave progress text landing on the wrong row.
        """
        return self._table.find_row_index(
            lambda rd: rd and rd[0].get("canvas_file_id") == old_id)

    def _event(self, name, payload):
        # Stage names + payload keys match core.orchestrator's on_event contract.
        if name == "file_started":
            i = payload.get("idx", 0) + 1
            total = payload.get("total", 1)
            self._cur_file = f"{i} of {total}"
            self._counter.set_status(f"Replacing {self._cur_file}")
            row = self._row_for_file(payload.get("old_file_id"))
            if row >= 0:
                self._table.set_cell(row, 2, "Uploading…")
        elif name == "file_progress":
            # Byte-level feedback: silent (speak=False) — per-chunk speech
            # would flood a screen reader; milestones stay per-file spoken
            # events (started/done).
            if payload.get("stage") != "uploading":
                return
            done, total = payload.get("bytes_read") or 0, payload.get("total") or 0
            if total <= 0:
                return
            pct = min(100, int(done * 100 / total))
            self._counter.set_status(
                f"Replacing {self._cur_file} — {rh.format_bytes(done)} of "
                f"{rh.format_bytes(total)} ({pct}%)", speak=False)
            row = self._row_for_file(payload.get("old_file_id"))
            if row >= 0:
                self._table.set_cell(row, 2, f"Uploading {pct}%")
        elif name == "file_done":
            # Reflect a successful replace into the underlying viewer (adds the
            # '(replaced)' suffix + persists). report.status == 'replaced' marks
            # success; the report object carries the outcome.
            report = payload.get("report")
            old_id = payload.get("old_file_id")
            status = getattr(report, "status", None)
            row = self._row_for_file(old_id)
            if row >= 0:
                # Resolve the progress text so no row is left mid-percent.
                label = {"replaced": "Done", "cancelled": "Skipped"}.get(status, "Failed")
                self._table.set_cell(row, 2, label)
            if report is not None and status == "replaced":
                self._panel.apply_replaced(old_id)
        elif name == "complete":
            self._running = False
            msg = "Bulk replace complete"
            self._counter.set_status(msg)
            a11y.announce(msg, interrupt=True)

    def _on_close_btn(self, _evt):
        if self._running:
            self._cancel.set()
            self._counter.set_status("Cancelling…")
            return
        self.EndModal(wx.ID_OK)
