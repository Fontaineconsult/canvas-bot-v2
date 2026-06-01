"""Content Viewer tab (wx).

Browses scanned courses stored under ``<output>/<course>/.manifest/content.json``.
A flat "Content type" choice selects which of the 11 content tables to show in an
accessible report-mode ListCtrl. Rows can be marked Passed / Needs Review /
Ignore (persisted to review_status.json), and action buttons open the file, its
folder, or its source page(s), or launch the replace flows.

Reuses ``gui.core.replace_helpers`` for source-URL parsing and content.json
mutation, and ``network.api.get_course_permissions`` (async) to gate replace.
"""

import glob
import json
import os
import shutil
import threading
import webbrowser

import wx

from gui.core import replace_helpers as rh
from gui.wx import a11y, widgets

# table_key -> (category, sub_key) in content.json
_TABLE_MAP = {
    "documents": ("documents", "documents"),
    "document_sites": ("documents", "document_sites"),
    "video_sites": ("videos", "video_sites"),
    "video_files": ("videos", "video_files"),
    "audio_files": ("audio", "audio_files"),
    "audio_sites": ("audio", "audio_sites"),
    "image_files": ("images", "image_files"),
    "institution_video": ("videos", "institution_video"),
    "digital_textbooks": ("other", "digital_textbooks"),
    "file_storage": ("other", "file_storage"),
    "unsorted": ("unsorted", "unsorted"),
}

# Friendly label -> table_key, in display order (flat, accessible single Choice)
_CONTENT_TYPES = [
    ("Documents", "documents"),
    ("Document Sites", "document_sites"),
    ("Video Sites", "video_sites"),
    ("Video Files", "video_files"),
    ("Institution Video", "institution_video"),
    ("Audio Files", "audio_files"),
    ("Audio Sites", "audio_sites"),
    ("Images", "image_files"),
    ("Textbooks", "digital_textbooks"),
    ("File Storage", "file_storage"),
    ("Unsorted", "unsorted"),
]

# Columns per table_key: list of (heading, field, width). "Order"/"Title"/
# "Status" plus type-specific fields. Mirrors gui/content_viewer._COLUMNS.
_FILE_COLS = lambda: [
    ("Order", "order", 60), ("Title", "title", 280), ("Type", "file_type", 80),
    ("Source", "source_page_type", 110), ("Visibility", "visibility", 110),
    ("Downloaded", "downloaded", 110), ("Status", "status", 120),
]
_SITE_COLS = lambda: [
    ("Order", "order", 60), ("Title", "title", 240), ("URL", "url", 280),
    ("Source", "source_page_type", 110), ("Visibility", "visibility", 110),
    ("Status", "status", 120),
]
_COLUMNS = {
    "documents": [
        ("Order", "order", 60), ("Title", "title", 260), ("Type", "file_type", 70),
        ("File Source", "file_source", 100), ("Source", "source_page_type", 100),
        ("Visibility", "visibility", 100), ("Downloaded", "downloaded", 100),
        ("Status", "status", 120),
    ],
    "document_sites": _SITE_COLS(),
    "video_sites": _SITE_COLS(),
    "video_files": _FILE_COLS(),
    "audio_files": _FILE_COLS(),
    "audio_sites": _SITE_COLS(),
    "image_files": _FILE_COLS(),
    "institution_video": _SITE_COLS(),
    "digital_textbooks": _SITE_COLS(),
    "file_storage": _SITE_COLS(),
    "unsorted": _SITE_COLS(),
}

_SITE_KEYS = {"document_sites", "video_sites", "audio_sites", "institution_video",
              "digital_textbooks", "file_storage", "unsorted"}

_REASON_LABELS = {
    "hidden_for_user": "Hidden", "hidden_from_students": "Hidden",
    "unpublished": "Unpublished", "locked": "Locked", "varies": "Varies",
}

_REVIEW_STATUSES = ["Passed", "Needs Review", "Ignore"]
_DEFAULT_STATUS = "-"
_DATE_FOLDER_RE = __import__("re").compile(r'(?<=[\\/])\d{2}-\d{2}-\d{4}(?=[\\/])')

_BLOCKED_EXT = frozenset({
    ".exe", ".msi", ".com", ".scr", ".bat", ".cmd", ".ps1", ".vbs", ".js",
    ".jar", ".dll", ".sys", ".lnk", ".url", ".reg", ".hta", ".docm", ".xlsm",
    ".pptm",
})


class ContentPanel(wx.Panel):
    def __init__(self, parent, theme):
        super().__init__(parent)
        self._theme = theme
        self._course_folders = {}   # display name -> folder
        self._current_data = None
        self._manifest_dir = None
        self._content_json_path = None
        self._review = {}
        self._table_key = "documents"
        self._can_replace = False
        self._perm_cache = {}
        self._pending_perm_course = None
        self._build()
        theme.apply_panel(self)
        self.refresh_courses()

    # ── construction ──

    def _build(self):
        outer = wx.BoxSizer(wx.VERTICAL)

        # Row 1: course choice + buttons
        top = wx.BoxSizer(wx.HORIZONTAL)
        top.Add(wx.StaticText(self, label="Co&urse:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.course_choice = wx.Choice(self, choices=[])
        widgets.set_name(self.course_choice, "Course")
        self.course_choice.Bind(wx.EVT_CHOICE, self._on_course)
        top.Add(self.course_choice, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        top.Add(widgets.make_button(self, "Refr&esh", self._on_refresh, name="Refresh course list"), 0, wx.RIGHT, 4)
        self.open_folder_btn = widgets.make_button(self, "Open Fol&der", self._on_open_folder, name="Open course folder")
        top.Add(self.open_folder_btn, 0, wx.RIGHT, 4)
        self.canvas_btn = widgets.make_button(self, "Open in Can&vas", self._on_open_canvas, name="Open in Canvas")
        top.Add(self.canvas_btn, 0, wx.RIGHT, 4)
        # Destructive action, set apart at the far right. Native styling (custom
        # button colours render washed/low-contrast on MSW); the danger is
        # conveyed by the label, tooltip, and a warning confirmation dialog.
        self.delete_btn = widgets.make_button(
            self, "Delete Course Dat&a", self._on_delete,
            name="Delete course data",
            tooltip="Permanently delete the selected course's downloaded folder "
                    "and data on this computer (cannot be undone)",
        )
        top.Add(self.delete_btn, 0)
        outer.Add(top, 0, wx.EXPAND | wx.ALL, 8)

        # Row 2: course info + content-type choice + status buttons
        row2 = wx.BoxSizer(wx.HORIZONTAL)
        self.info = wx.StaticText(self, label="No course selected")
        widgets.set_name(self.info, "Course summary")
        row2.Add(self.info, 1, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        row2.Add(wx.StaticText(self, label="Content &type:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.type_choice = wx.Choice(self, choices=[label for label, _ in _CONTENT_TYPES])
        widgets.set_name(self.type_choice, "Content type")
        self.type_choice.SetSelection(0)
        self.type_choice.Bind(wx.EVT_CHOICE, self._on_type)
        row2.Add(self.type_choice, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)

        _mark_labels = {
            "Passed": "Mark &Passed",
            "Needs Review": "Mark &Needs Review",
            "Ignore": "Mark I&gnore",
        }
        for status in _REVIEW_STATUSES:
            b = widgets.make_button(self, _mark_labels.get(status, f"Mark {status}"),
                                    lambda e, s=status: self._on_mark(s),
                                    name=f"Mark {status}")
            setattr(self, f"_mark_{status.replace(' ', '_')}", b)
            row2.Add(b, 0, wx.RIGHT, 4)
        outer.Add(row2, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Row 3: filter
        row3 = wx.BoxSizer(wx.HORIZONTAL)
        self.cb_inactive = widgets.make_checkbox(self, "Show &inactive content", name="Show inactive content")
        self.cb_inactive.Bind(wx.EVT_CHECKBOX, lambda e: self._repopulate())
        row3.Add(self.cb_inactive, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        self.scan_label = wx.StaticText(self, label="")
        row3.Add(self.scan_label, 1, wx.ALIGN_CENTER_VERTICAL)
        outer.Add(row3, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # Row 4: the table
        self.table = widgets.AccessibleListCtrl(self, announce_columns=[1, 6, 4])
        self.table.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_row)
        self.table.Bind(wx.EVT_LIST_ITEM_DESELECTED, lambda e: self._update_actions())
        outer.Add(self.table, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # Row 5: action buttons
        row5 = wx.BoxSizer(wx.HORIZONTAL)
        self.open_loc_btn = widgets.make_button(self, "Open File &Location", self._on_open_location, name="Open file location")
        self.open_file_btn = widgets.make_button(self, "&Open File", self._on_open_file, name="Open file")
        self.open_src_btn = widgets.make_button(self, "Open &Source Page", self._on_open_source, name="Open source page")
        self.replace_btn = widgets.make_button(self, "&Replace File", self._on_replace, name="Replace file")
        self.bulk_btn = widgets.make_button(self, "&Bulk Replace", self._on_bulk, name="Bulk replace")
        for b in (self.open_loc_btn, self.open_file_btn, self.open_src_btn, self.replace_btn, self.bulk_btn):
            row5.Add(b, 0, wx.RIGHT, 4)
        outer.Add(row5, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizer(outer)
        self._update_actions()

    # ── course loading ──

    def refresh_courses(self):
        """Scan settings' output folder for courses with a .manifest/content.json."""
        from gui.core import settings
        out = settings.load().get("output_folder", "")
        self._course_folders = {}
        if out and os.path.isdir(out):
            for entry in sorted(os.listdir(out)):
                folder = os.path.join(out, entry)
                manifest = os.path.join(folder, ".manifest")
                if os.path.isdir(manifest):
                    jsons = [f for f in os.listdir(manifest)
                             if f.endswith(".json") and f != "review_status.json"]
                    if jsons:
                        self._course_folders[entry] = folder
        names = list(self._course_folders.keys())
        self.course_choice.Set(names or ["(none)"])
        if names:
            self.course_choice.SetSelection(0)
            self._on_course(None)
        else:
            self.course_choice.SetSelection(0)
            self._current_data = None
            self.table.DeleteAllItems()
            self.info.SetLabel("No scanned courses found")
            # No course selected — disable the per-course actions (delete, open
            # folder, open in Canvas) that would otherwise stay stale-enabled.
            self._update_actions()

    def _on_refresh(self, _evt):
        self.refresh_courses()
        a11y.announce(f"{len(self._course_folders)} courses", interrupt=True)

    def _on_course(self, _evt):
        name = self.course_choice.GetStringSelection()
        folder = self._course_folders.get(name)
        if not folder:
            return
        manifest = os.path.join(folder, ".manifest")
        jsons = [f for f in os.listdir(manifest)
                 if f.endswith(".json") and f != "review_status.json"]
        if not jsons:
            return
        path = os.path.join(manifest, jsons[0])
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._current_data = json.load(f)
        except (OSError, json.JSONDecodeError):
            self._current_data = None
            return
        self._manifest_dir = manifest
        self._content_json_path = path
        self._review = self._load_review(manifest)
        self._can_replace = False
        self._check_permission_async(self._current_data.get("course_id"))
        self._repopulate()
        self._update_summary()
        # Speak the loaded course + headline count so a screen-reader user knows
        # the selection took effect and how much content there is.
        summary = (self._current_data.get("summary", {}) or {}).get("content", {})
        total = summary.get("total", self.table.GetItemCount())
        a11y.announce(f"Loaded {self._current_data.get('course_name', 'course')}, "
                      f"{total} items", interrupt=True)

    def _update_summary(self):
        d = self._current_data or {}
        name = d.get("course_name", "Untitled")
        summary = d.get("summary", {}).get("content", {})
        total = summary.get("total", 0)
        hidden = summary.get("hidden", 0)
        self.info.SetLabel(f"{name} — {total} items, {hidden} hidden")
        scanned = d.get("scanned_date", "")
        self.scan_label.SetLabel(f"Last scanned: {scanned}" if scanned else "")

    # ── table population ──

    def _rows_for(self, table_key):
        d = self._current_data or {}
        category, sub = _TABLE_MAP[table_key]
        return d.get("content", {}).get(category, {}).get(sub, []) or []

    def _visibility(self, row):
        reason = row.get("hidden_reason", "")
        has_source = bool(row.get("source_page_url"))
        if not reason:
            return "Visible"
        labels = []
        for part in reason.split(", "):
            label = _REASON_LABELS.get(part, part)
            if label == "Hidden" and has_source:
                continue
            labels.append(label)
        seen = set()
        uniq = [l for l in labels if not (l in seen or seen.add(l))]
        return ", ".join(uniq) if uniq else "Visible"

    def _downloaded(self, row):
        save_path = row.get("save_path", "")
        if not save_path:
            return ""
        norm = os.path.normpath(save_path)
        if os.path.isfile(norm):
            m = _DATE_FOLDER_RE.search(norm)
            return m.group() if m else "Yes"
        wildcard = _DATE_FOLDER_RE.sub("*", norm, count=1)
        matches = glob.glob(wildcard)
        if matches:
            m = _DATE_FOLDER_RE.search(matches[0])
            return m.group() if m else "Yes"
        return "No"

    def _on_type(self, _evt):
        idx = self.type_choice.GetSelection()
        if idx < 0:
            return
        self._table_key = _CONTENT_TYPES[idx][1]
        self._repopulate()
        a11y.announce(f"{_CONTENT_TYPES[idx][0]}, {self.table.GetItemCount()} items", interrupt=True)

    def _repopulate(self):
        key = self._table_key
        cols = _COLUMNS[key]
        self.table.set_columns([(h, w) for h, _f, w in cols])

        rows = list(self._rows_for(key))
        show_inactive = self.cb_inactive.GetValue()

        # Enrich + filter
        display_rows = []
        data_rows = []
        for row in rows:
            if not show_inactive and not row.get("source_page_url"):
                continue
            if not show_inactive and row.get("is_hidden"):
                continue
            url = row.get("url", "")
            row["status"] = self._review.get(url, {}).get("status", _DEFAULT_STATUS)
            row["visibility"] = self._visibility(row)
            if key not in _SITE_KEYS:
                row["downloaded"] = self._downloaded(row)
            # Multi source label
            spu = row.get("source_page_url")
            if isinstance(spu, list) and len(spu) > 1:
                row.setdefault("_orig_source_page_type", row.get("source_page_type"))
                row["source_page_type"] = "Multi"
            if key == "image_files" and not row.get("title"):
                row["title"] = row.get("file_name", "")
            cells = []
            for _h, field, _w in cols:
                val = row.get(field, "")
                cells.append("" if val is None else str(val))
            display_rows.append(cells)
            data_rows.append(row)

        def bg_for(_i, rowdata):
            if rowdata is None:
                return None
            return self._theme.status_bg(rowdata.get("status"))

        self.table.set_rows(display_rows, row_data=data_rows, bg_for=bg_for)
        self._update_actions()

    # ── review status ──

    def _load_review(self, manifest_dir):
        path = os.path.join(manifest_dir, "review_status.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_review(self):
        if not self._manifest_dir:
            return
        path = os.path.join(self._manifest_dir, "review_status.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._review, f, indent=2)
        except OSError:
            pass

    def _on_mark(self, status):
        row = self.table.get_selected_data()
        if not row:
            return
        url = row.get("url", "")
        if not url:
            return
        self._review[url] = {"status": status}
        self._save_review()
        row["status"] = status
        idx = self.table.get_selected_index()
        if idx >= 0:
            # update the Status cell + row color
            status_col = len(_COLUMNS[self._table_key]) - 1
            self.table.SetItem(idx, status_col, status)
            colour = self._theme.status_bg(status)
            if colour is not None:
                self.table.SetItemBackgroundColour(idx, colour)
        a11y.announce(f"Marked {status}", interrupt=True)

    # ── action buttons ──

    def _on_row(self, _evt):
        self._update_actions()

    def _resolve_path(self, save_path):
        """Return the file's real on-disk path, or None if not found.

        The path stored in content.json is computed at scan time and embeds a
        date folder; the file may actually live in a different date folder if it
        was downloaded on another day. Try the exact path first, then a glob
        with the date segment wild-carded (same logic as the Downloaded column),
        so Open File / Open File Location work whenever the file exists.
        """
        if not save_path:
            return None
        norm = os.path.normpath(save_path)
        if os.path.isfile(norm):
            return norm
        matches = glob.glob(_DATE_FOLDER_RE.sub("*", norm, count=1))
        return matches[0] if matches else None

    def _update_actions(self):
        row = self.table.get_selected_data()
        has = row is not None
        save_path = (row or {}).get("save_path", "") if has else ""
        url = (row or {}).get("url", "") if has else ""
        spu = (row or {}).get("source_page_url") if has else None
        resolved = self._resolve_path(save_path)

        self.open_loc_btn.Enable(bool(resolved) or bool(url))
        # Same physical button, two modes; keep the mnemonic on 'L' in both so
        # Alt+L is stable and never collides with Open &Source Page (s).
        self.open_loc_btn.SetLabel("Open Site &Link" if (not save_path and url) else "Open File &Location")
        self.open_file_btn.Enable(bool(resolved))
        self.open_src_btn.Enable(bool(spu))
        is_doc = self._table_key == "documents"
        can_replace_row = (self._can_replace and is_doc and has
                           and row.get("canvas_file_id") and row.get("file_source") == "Canvas")
        self.replace_btn.Enable(bool(can_replace_row))
        self.bulk_btn.Enable(bool(self._can_replace and is_doc and self._current_data))
        course_url = (self._current_data or {}).get("course_url")
        self.canvas_btn.Enable(bool(course_url))
        real_course = self.course_choice.GetStringSelection() in self._course_folders
        self.open_folder_btn.Enable(bool(real_course))
        self.delete_btn.Enable(bool(real_course))

    def _on_open_location(self, _evt):
        row = self.table.get_selected_data()
        if not row:
            return
        resolved = self._resolve_path(row.get("save_path", ""))
        if resolved:
            os.startfile(os.path.dirname(resolved))  # noqa: S606
        elif row.get("url"):
            webbrowser.open(row["url"])

    def _on_open_file(self, _evt):
        row = self.table.get_selected_data()
        if not row:
            return
        resolved = self._resolve_path(row.get("save_path", ""))
        if not resolved:
            return
        ext = os.path.splitext(resolved)[1].lower()
        if ext in _BLOCKED_EXT:
            wx.MessageBox(f"Cannot open '{os.path.basename(resolved)}'.\n"
                          f"Files with the '{ext}' extension are blocked for security.",
                          "Blocked file type", wx.OK | wx.ICON_WARNING, self)
            return
        os.startfile(resolved)  # noqa: S606

    def _on_open_source(self, _evt):
        row = self.table.get_selected_data()
        if not row:
            return
        spu = row.get("source_page_url")
        if isinstance(spu, str):
            spu = [spu] if spu else []
        if not spu:
            return
        if len(spu) == 1:
            webbrowser.open(spu[0])
            return
        # Multiple: popup menu of locations
        menu = wx.Menu()
        for url in spu:
            item = menu.Append(wx.ID_ANY, rh.source_url_label(url))
            self.Bind(wx.EVT_MENU, lambda e, u=url: webbrowser.open(u), item)
        self.PopupMenu(menu)
        menu.Destroy()

    def _on_delete(self, _evt):
        """Delete the selected course's local folder (downloads + manifest).

        Mirrors the old CTk Content Viewer's Delete button. Removes only the
        folder under the user's output directory that this app created — never
        anything on Canvas. Gated behind a warning dialog whose default button is
        No, so a stray Enter can't trigger it.
        """
        name = self.course_choice.GetStringSelection()
        folder = self._course_folders.get(name)
        if not folder or not os.path.isdir(folder):
            return
        msg = ("Permanently delete this course's downloaded folder and all its "
               "data on this computer?\n\nThis only removes local files — it does "
               "not affect anything on Canvas. It cannot be undone.\n\n"
               f"{name}\n{folder}")
        dlg = wx.MessageDialog(self, msg, "Delete Course Data",
                               wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING)
        try:
            confirmed = dlg.ShowModal() == wx.ID_YES
        finally:
            dlg.Destroy()
        if not confirmed:
            return
        a11y.announce(f"Deleting {name}", interrupt=True)
        try:
            shutil.rmtree(folder)
        except OSError as exc:
            wx.MessageBox(f"Could not delete folder:\n{folder}\n\n{exc}",
                          "Delete failed", wx.OK | wx.ICON_ERROR, self)
            a11y.announce("Delete failed", interrupt=True)
            return
        self.refresh_courses()
        a11y.announce(
            f"Deleted {name}. {len(self._course_folders)} courses remaining.",
            interrupt=True)

    def _on_open_folder(self, _evt):
        folder = self._course_folders.get(self.course_choice.GetStringSelection())
        if folder and os.path.isdir(folder):
            os.startfile(folder)  # noqa: S606

    def _on_open_canvas(self, _evt):
        course_url = (self._current_data or {}).get("course_url")
        if course_url:
            webbrowser.open(course_url.rstrip("/") + "/files")

    def _on_replace(self, _evt):
        row = self.table.get_selected_data()
        if not row:
            return
        from gui.wx.replace_dialogs import start_single_replace
        start_single_replace(self, row)

    def _on_bulk(self, _evt):
        from gui.wx.replace_dialogs import start_bulk_replace
        start_bulk_replace(self)

    # ── replace support (called back by dialogs) ──

    def apply_replaced(self, canvas_file_id):
        """Mark a row replaced in current_data + persist + refresh (called by dialogs)."""
        if rh.mark_row_replaced(self._current_data, canvas_file_id):
            rh.save_content_json(self._content_json_path, self._current_data)
            self._repopulate()

    def get_document_rows(self):
        return list(self._rows_for("documents"))

    def get_course_id(self):
        return (self._current_data or {}).get("course_id")

    def get_course_name(self):
        return (self._current_data or {}).get("course_name", "")

    # ── async permission ──

    def _check_permission_async(self, course_id):
        if not course_id:
            return
        if course_id in self._perm_cache:
            self._can_replace = self._perm_cache[course_id]
            self._update_actions()
            return
        self._pending_perm_course = course_id

        def worker():
            ok = False
            reached = False  # did we actually query Canvas (creds present)?
            try:
                # Bootstrap credentials here — the permission check can run on
                # the first Content-tab visit, before any scan has loaded them.
                # Without this it would silently fail and (worse) cache False,
                # leaving Replace disabled even after a later scan loads creds.
                from network.cred import (
                    load_config_data_from_appdata,
                    set_canvas_api_key_to_environment_variable,
                )
                load_config_data_from_appdata()
                if set_canvas_api_key_to_environment_variable():
                    from network.api import get_course_permissions
                    perms = get_course_permissions(course_id)
                    ok = bool(perms and perms.get("manage_files_edit"))
                    reached = True
            except Exception:
                ok, reached = False, False
            wx.CallAfter(self._apply_permission, course_id, ok, reached)

        threading.Thread(target=worker, daemon=True, name="cb-perm").start()

    def _apply_permission(self, course_id, ok, reached=True):
        # Only cache a result actually obtained from Canvas; a credential-less
        # failure is "unknown", not "no permission", so don't poison the cache.
        if reached:
            self._perm_cache[course_id] = ok
        # Ignore stale results if the user switched courses
        if (self._current_data or {}).get("course_id") != course_id:
            return
        was = self._can_replace
        self._can_replace = ok
        self._update_actions()
        # Speak the replace-availability result once it's known — it arrives
        # asynchronously after the course loads, so focus is elsewhere; this is
        # exactly the kind of background state a screen reader can't infer.
        if not reached:
            a11y.announce("Could not verify file-edit permission; "
                          "replace is unavailable.", interrupt=False)
        elif ok and not was:
            a11y.announce("File replace available for this course.", interrupt=False)
        elif not ok:
            a11y.announce("You do not have permission to replace files in this course.",
                          interrupt=False)
