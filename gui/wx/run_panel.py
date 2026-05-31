"""Run tab: course input, output folder, options, Run button, log view.

Mirrors the old CustomTkinter Run tab but with native wx controls. All scan
logic lives in ``gui.core.app_service``; this panel only collects inputs,
spawns the worker thread, and marshals status/log back to the UI thread.
"""

import os
import sys
import threading

import wx

from gui.core import app_service, settings
from gui.wx import a11y, widgets
from gui.wx.log_panel import LogRedirector, ansi_palette, make_log_ctrl


class RunPanel(wx.Panel):
    def __init__(self, parent, theme):
        super().__init__(parent)
        self._theme = theme
        self._running = False
        self._old_stdout = None
        self._old_stderr = None
        self._build()
        self._load_settings()
        theme.apply_panel(self)

    # ── construction ──

    def _build(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        # Course selection: ID or list file
        course_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Course selection")
        id_sizer, self.course_id = widgets.labeled_text(
            self, "Course &ID:", name="Course ID",
            hint="e.g. 12345",
        )
        course_box.Add(id_sizer, 0, wx.EXPAND | wx.ALL, 4)

        list_row = wx.BoxSizer(wx.HORIZONTAL)
        list_lbl = wx.StaticText(self, label="Course &list:")
        self.course_list = wx.TextCtrl(self)
        widgets.set_name(self.course_list, "Course list file")
        try:
            self.course_list.SetHint("Path to .txt file (one ID per line)")
        except Exception:
            pass
        browse_list = widgets.make_button(
            self, "&Browse…", self._on_browse_list,
            name="Browse for course list", tooltip="Select a .txt file of course IDs",
        )
        list_row.Add(list_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        list_row.Add(self.course_list, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        list_row.Add(browse_list, 0, wx.ALIGN_CENTER_VERTICAL)
        course_box.Add(list_row, 0, wx.EXPAND | wx.ALL, 4)
        outer.Add(course_box, 0, wx.EXPAND | wx.ALL, 8)

        # Output folder
        out_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Output")
        out_row = wx.BoxSizer(wx.HORIZONTAL)
        out_lbl = wx.StaticText(self, label="&Output folder:")
        self.output_folder = wx.TextCtrl(self)
        widgets.set_name(self.output_folder, "Output folder")
        browse_out = widgets.make_button(
            self, "B&rowse…", self._on_browse_output,
            name="Browse for output folder",
            tooltip="Directory where downloads and content data are saved",
        )
        out_row.Add(out_lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
        out_row.Add(self.output_folder, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        out_row.Add(browse_out, 0, wx.ALIGN_CENTER_VERTICAL)
        out_box.Add(out_row, 0, wx.EXPAND | wx.ALL, 4)
        self.cb_download = widgets.make_checkbox(
            self, "&Download files", name="Download files",
            tooltip="Download course documents to the output folder",
        )
        out_box.Add(self.cb_download, 0, wx.ALL, 6)
        outer.Add(out_box, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Options: two grouped columns
        opt_row = wx.BoxSizer(wx.HORIZONTAL)

        dl_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Download options")
        self.cb_video = widgets.make_checkbox(self, "Download &video files", name="Download video files")
        self.cb_audio = widgets.make_checkbox(self, "Download &audio files", name="Download audio files")
        self.cb_image = widgets.make_checkbox(self, "Download i&mage files", name="Download image files")
        self.cb_hidden = widgets.make_checkbox(self, "Include &hidden/locked", name="Include hidden or locked")
        self.cb_inactive = widgets.make_checkbox(self, "Include &unlinked", name="Include unlinked")
        self.cb_flatten = widgets.make_checkbox(self, "&Flatten folder structure", name="Flatten folder structure")
        for cb in (self.cb_video, self.cb_audio, self.cb_image,
                   self.cb_hidden, self.cb_inactive, self.cb_flatten):
            dl_box.Add(cb, 0, wx.ALL, 4)
        opt_row.Add(dl_box, 1, wx.EXPAND | wx.RIGHT, 6)

        disp_box = wx.StaticBoxSizer(wx.VERTICAL, self, "Display options")
        self.cb_content_tree = widgets.make_checkbox(
            self, "Print &content tree", name="Print content tree",
            tooltip="Print course tree showing only resources with content (single course)",
        )
        self.cb_full_tree = widgets.make_checkbox(
            self, "Print full course &tree", name="Print full course tree",
            tooltip="Print the complete course tree (single course)",
        )
        self.cb_content_tree.Bind(wx.EVT_CHECKBOX, self._on_content_tree)
        self.cb_full_tree.Bind(wx.EVT_CHECKBOX, self._on_full_tree)
        disp_box.Add(self.cb_content_tree, 0, wx.ALL, 4)
        disp_box.Add(self.cb_full_tree, 0, wx.ALL, 4)
        opt_row.Add(disp_box, 1, wx.EXPAND)
        outer.Add(opt_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Run button + status
        run_row = wx.BoxSizer(wx.HORIZONTAL)
        self.run_btn = widgets.make_primary_button(
            self, "&Run", self._on_run, theme=self._theme, name="Run",
            tooltip="Start scanning the selected course(s)",
        )
        self.status = widgets.StatusLine(self, label="Status: Ready")
        run_row.Add(self.run_btn, 0, wx.RIGHT, 12)
        run_row.Add(self.status, 1, wx.ALIGN_CENTER_VERTICAL)
        outer.Add(run_row, 0, wx.EXPAND | wx.ALL, 8)

        # Log view
        log_lbl = wx.StaticText(self, label="Output log:")
        outer.Add(log_lbl, 0, wx.LEFT | wx.RIGHT, 8)
        self.log = make_log_ctrl(self, theme=self._theme)
        outer.Add(self.log, 1, wx.EXPAND | wx.ALL, 8)

        self.SetSizer(outer)

    # ── settings ──

    def _load_settings(self):
        s = settings.load()
        self.course_id.SetValue(s["course_id"])
        self.course_list.SetValue(s["course_list"])
        self.output_folder.SetValue(s["output_folder"])
        self.cb_download.SetValue(s["download"])
        self.cb_video.SetValue(s["include_video"])
        self.cb_audio.SetValue(s["include_audio"])
        self.cb_image.SetValue(s["include_image"])
        self.cb_hidden.SetValue(s["include_hidden"])
        self.cb_inactive.SetValue(s["include_inactive"])
        self.cb_flatten.SetValue(s["flatten"])
        self.cb_content_tree.SetValue(s["content_tree"])
        self.cb_full_tree.SetValue(s["full_tree"])

    def _collect_settings(self):
        return {
            "course_id": self.course_id.GetValue(),
            "course_list": self.course_list.GetValue(),
            "output_folder": self.output_folder.GetValue(),
            "download": self.cb_download.GetValue(),
            "include_video": self.cb_video.GetValue(),
            "include_audio": self.cb_audio.GetValue(),
            "include_image": self.cb_image.GetValue(),
            "include_hidden": self.cb_hidden.GetValue(),
            "include_inactive": self.cb_inactive.GetValue(),
            "flatten": self.cb_flatten.GetValue(),
            "content_tree": self.cb_content_tree.GetValue(),
            "full_tree": self.cb_full_tree.GetValue(),
        }

    # ── handlers ──

    def _on_browse_list(self, _evt):
        with wx.FileDialog(
            self, "Select course list", wildcard="Text files (*.txt)|*.txt|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.course_list.SetValue(dlg.GetPath())

    def _on_browse_output(self, _evt):
        with wx.DirDialog(self, "Select output folder", style=wx.DD_DEFAULT_STYLE) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.output_folder.SetValue(dlg.GetPath())

    def _on_content_tree(self, _evt):
        # Mutually exclusive with full tree (matches old behavior).
        if self.cb_content_tree.GetValue():
            self.cb_full_tree.SetValue(False)

    def _on_full_tree(self, _evt):
        if self.cb_full_tree.GetValue():
            self.cb_content_tree.SetValue(False)

    def _on_run(self, _evt):
        if self._running:
            return

        opts = self._collect_settings()
        settings.save(opts)

        ids, messages = app_service.resolve_course_ids(opts["course_id"], opts["course_list"])
        errors = [t for lvl, t in messages if lvl == "error"]
        if errors:
            self.status.set_status("Status: " + errors[0])
            wx.MessageBox(errors[0], "Cannot run", wx.OK | wx.ICON_ERROR, self)
            return

        # Prepare UI for run
        self._running = True
        self.run_btn.Enable(False)
        self.run_btn.SetLabel("Running…")
        self.log.SetValue("")
        self.status.set_status("Status: Initializing…")

        # Redirect stdout/stderr into the log view, rendering ANSI colors with
        # a contrast-checked palette on the log's themed background.
        palette = ansi_palette(self._theme.dark) if self._theme.active else {}
        default_colour = self._theme.color("text") if self._theme.active else None
        self._old_stdout, self._old_stderr = sys.stdout, sys.stderr
        sys.stdout = LogRedirector(self.log, self._old_stdout, palette, default_colour)
        sys.stderr = LogRedirector(self.log, self._old_stderr, palette, default_colour)

        # Surface warnings (non-fatal) into the log
        for lvl, text in messages:
            if lvl == "warning":
                print(f"WARNING: {text}")

        threading.Thread(
            target=self._worker, args=(ids, opts), daemon=True, name="cb-scan",
        ).start()

    def _worker(self, ids, opts):
        def on_status(text):
            wx.CallAfter(self.status.set_status, f"Status: {text}")
        try:
            app_service.run_scan(ids, opts, on_status)
        finally:
            wx.CallAfter(self._finish_run)

    def _finish_run(self):
        sys.stdout = self._old_stdout
        sys.stderr = self._old_stderr
        self._running = False
        self.run_btn.Enable(True)
        self.run_btn.SetLabel("&Run")
        # Notify the main frame so the Content Viewer can refresh.
        top = self.GetTopLevelParent()
        if hasattr(top, "on_scan_complete"):
            top.on_scan_complete()
