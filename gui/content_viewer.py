import glob
import json
import os
import re
import webbrowser
import customtkinter as ctk

from gui.table_widget import ContentTable
from gui.widgets import _add_focus_ring, _underline_char, Tooltip


# Review status options (add new values here to expand)
_REVIEW_STATUSES = ["Needs Review", "Passed", "Ignore"]
_DEFAULT_STATUS = "-"  # unreviewed — no color
_SHOW_DETAIL_PANEL = False  # Set to True to show the diagnostic detail panel

# Column definitions per content sub-type
_ORDER_COL = {"id": "order", "heading": "Order", "width": 65}

_COLUMNS = {
    "documents": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 150, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 100},
        {"id": "source_page_type", "heading": "Source", "width": 150},
        {"id": "is_hidden", "heading": "Hidden", "width": 100},
        {"id": "downloaded", "heading": "Downloaded", "width": 130},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "document_sites": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "is_hidden", "heading": "Hidden", "width": 90},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "video_sites": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "is_hidden", "heading": "Hidden", "width": 90},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "video_files": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "audio_files": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "audio_sites": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "is_hidden", "heading": "Hidden", "width": 90},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "image_files": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "unsorted": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "url", "heading": "URL", "width": 250, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
}

_DATE_FOLDER_RE = re.compile(r'(?<=[\\/])\d{2}-\d{2}-\d{4}(?=[\\/])')


class ContentViewer:
    """Persistent browser for scanned course content stored in .manifest/ folders."""

    def __init__(self, parent_frame, view):
        self._view = view
        self._parent = parent_frame
        self._course_folders = {}  # display_name -> folder_path
        self._tables = {}         # sub_type key -> ContentTable
        self._selected_row = None
        self._selected_table_key = None  # which table the selection is in
        self._current_data = None  # raw JSON data for re-filtering
        self._review_statuses = {}  # url -> {"status": "Passed"|"Needs Review"|...}
        self._manifest_dir = None   # current course's .manifest/ path

        # Placeholder shown when no data is available
        self._placeholder = ctk.CTkLabel(
            parent_frame,
            text="",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )

        # Main container (hidden until courses are available)
        self._container = ctk.CTkFrame(parent_frame, fg_color="transparent")

        # ── Top bar: dropdown + refresh + open folder ──
        top_bar = ctk.CTkFrame(self._container, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 5))

        ctk.CTkLabel(top_bar, text="Course:", width=60, anchor="w").pack(side="left")
        self._course_var = ctk.StringVar()
        self._dropdown = ctk.CTkOptionMenu(
            top_bar, variable=self._course_var,
            values=["(none)"], command=self._on_course_selected,
            width=400,
        )
        self._dropdown.pack(side="left", fill="x", expand=True, padx=(0, 5))
        Tooltip(self._dropdown, "Select a previously scanned course to browse its content")

        refresh_btn = ctk.CTkButton(top_bar, text="Refresh", width=80,
                                    command=self.refresh_course_list)
        refresh_btn.pack(side="right")
        _add_focus_ring(refresh_btn)
        _underline_char(refresh_btn, 2)  # F → Alt+F
        Tooltip(refresh_btn, "Re-scan the output folder for new or updated course data (Alt+F)")

        self._open_folder_btn = ctk.CTkButton(top_bar, text="Open Folder", width=100,
                                              command=self._open_course_folder, state="disabled")
        self._open_folder_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(self._open_folder_btn)
        _underline_char(self._open_folder_btn, 0)  # O → Alt+O
        Tooltip(self._open_folder_btn, "Open the selected course's folder in File Explorer (Alt+O)")

        # ── Summary banner ──
        self._summary_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        self._summary_frame.pack(fill="x", pady=(0, 5))

        self._course_label = ctk.CTkLabel(
            self._summary_frame, text="",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._course_label.pack(fill="x")

        self._stats_label = ctk.CTkLabel(
            self._summary_frame, text="",
            font=ctk.CTkFont(size=12), text_color="gray", anchor="w",
        )
        self._stats_label.pack(fill="x")

        self._summary_frame.pack_forget()

        # ── Filter bar ──
        filter_bar = ctk.CTkFrame(self._container, fg_color="transparent")
        filter_bar.pack(fill="x", pady=(0, 3))

        ctk.CTkLabel(filter_bar, text="Filters:", font=ctk.CTkFont(size=12, weight="bold"),
                     anchor="w", width=55).pack(side="left")

        self._show_inactive_var = ctk.BooleanVar(value=False)
        cb_inactive = ctk.CTkCheckBox(
            filter_bar, text="Show Inactive Content",
            variable=self._show_inactive_var,
            command=self._on_filter_changed,
        )
        cb_inactive.pack(side="left", padx=(0, 10))
        _add_focus_ring(cb_inactive)
        Tooltip(cb_inactive, "Show content not linked from any active Canvas page")

        # ── Content tabs ──
        self._tabview = ctk.CTkTabview(self._container)
        self._tabview.pack(fill="both", expand=True, pady=(0, 5))

        self._tabview.add("Documents")
        self._tabview.add("Videos")
        self._tabview.add("Audio")
        self._tabview.add("Images")
        self._tabview.add("Unsorted")

        # Documents: nested tabs for documents + document_sites
        self._docs_tabview = ctk.CTkTabview(self._tabview.tab("Documents"))
        self._docs_tabview.pack(fill="both", expand=True)
        self._docs_tabview.add("Documents")
        self._docs_tabview.add("Document Sites")
        self._tables["documents"] = ContentTable(
            self._docs_tabview.tab("Documents"),
            _COLUMNS["documents"], on_select=self._on_row_select,
            placeholder="No Documents Found", status_key="status",
        )
        self._tables["documents"].pack(fill="both", expand=True)
        self._tables["document_sites"] = ContentTable(
            self._docs_tabview.tab("Document Sites"),
            _COLUMNS["document_sites"], on_select=self._on_row_select,
            placeholder="No Document Sites Found", status_key="status",
        )
        self._tables["document_sites"].pack(fill="both", expand=True)

        # Videos: nested tabs
        self._vids_tabview = ctk.CTkTabview(self._tabview.tab("Videos"))
        self._vids_tabview.pack(fill="both", expand=True)
        self._vids_tabview.add("Video Sites")
        self._vids_tabview.add("Video Files")
        self._tables["video_sites"] = ContentTable(
            self._vids_tabview.tab("Video Sites"),
            _COLUMNS["video_sites"], on_select=self._on_row_select,
            placeholder="No Video Sites Found", status_key="status",
        )
        self._tables["video_sites"].pack(fill="both", expand=True)
        self._tables["video_files"] = ContentTable(
            self._vids_tabview.tab("Video Files"),
            _COLUMNS["video_files"], on_select=self._on_row_select,
            placeholder="No Video Files Found", status_key="status",
        )
        self._tables["video_files"].pack(fill="both", expand=True)

        # Audio: nested tabs
        self._audio_tabview = ctk.CTkTabview(self._tabview.tab("Audio"))
        self._audio_tabview.pack(fill="both", expand=True)
        self._audio_tabview.add("Audio Files")
        self._audio_tabview.add("Audio Sites")
        self._tables["audio_files"] = ContentTable(
            self._audio_tabview.tab("Audio Files"),
            _COLUMNS["audio_files"], on_select=self._on_row_select,
            placeholder="No Audio Files Found", status_key="status",
        )
        self._tables["audio_files"].pack(fill="both", expand=True)
        self._tables["audio_sites"] = ContentTable(
            self._audio_tabview.tab("Audio Sites"),
            _COLUMNS["audio_sites"], on_select=self._on_row_select,
            placeholder="No Audio Sites Found", status_key="status",
        )
        self._tables["audio_sites"].pack(fill="both", expand=True)

        # Images: single table
        self._tables["image_files"] = ContentTable(
            self._tabview.tab("Images"),
            _COLUMNS["image_files"], on_select=self._on_row_select,
            placeholder="No Image Files Found", status_key="status",
        )
        self._tables["image_files"].pack(fill="both", expand=True)

        # Unsorted: single table
        self._tables["unsorted"] = ContentTable(
            self._tabview.tab("Unsorted"),
            _COLUMNS["unsorted"], on_select=self._on_row_select,
            placeholder="No Unsorted Content Found", status_key="status",
        )
        self._tables["unsorted"].pack(fill="both", expand=True)

        # ── Detail panel (diagnostic — toggle via _SHOW_DETAIL_PANEL) ──
        if _SHOW_DETAIL_PANEL:
            self._detail = ctk.CTkTextbox(
                self._container, height=120,
                font=ctk.CTkFont(family="Consolas", size=11),
                state="disabled",
            )
            self._detail.pack(fill="x")
            self._detail.tag_config("link", foreground="#3B8ED0", underline=True)
        else:
            self._detail = None

        # ── Action buttons row ──
        btn_row = ctk.CTkFrame(self._container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(5, 0))

        self._open_file_btn = ctk.CTkButton(
            btn_row, text="Open File Location", width=140,
            command=self._open_file_or_site, state="disabled",
        )
        self._open_file_btn.pack(side="left", padx=(0, 5))
        _add_focus_ring(self._open_file_btn)
        _underline_char(self._open_file_btn, 2)  # e in "Open" → Alt+E
        Tooltip(self._open_file_btn, "Open the folder containing the downloaded file, or open the site URL (Alt+E)")

        self._open_source_btn = ctk.CTkButton(
            btn_row, text="Open Source Page", width=140,
            command=self._open_source_page, state="disabled",
        )
        self._open_source_btn.pack(side="left")
        _add_focus_ring(self._open_source_btn)
        _underline_char(self._open_source_btn, 5)  # S in "Source" → Alt+S
        Tooltip(self._open_source_btn, "Open the Canvas page where this content was found (Alt+S)")

        # Status buttons (right-aligned)
        # Underline indices: Needs revieW (11) → Alt+W, PasseD (5) → Alt+D, Ignore (0) → Alt+I
        _status_underline = {"Needs Review": 11, "Passed": 5, "Ignore": 0}
        _status_keys = {"Needs Review": "W", "Passed": "D", "Ignore": "I"}
        self._status_buttons = {}
        for status in reversed(_REVIEW_STATUSES):
            btn = ctk.CTkButton(
                btn_row, text=status, width=110,
                command=lambda s=status: self._on_status_changed(s),
                state="disabled",
            )
            btn.pack(side="right", padx=(3, 0))
            _add_focus_ring(btn)
            _underline_char(btn, _status_underline.get(status, 0))
            Tooltip(btn, f"Mark selected item as '{status}' (Alt+{_status_keys.get(status, '?')})")
            self._status_buttons[status] = btn

        # Keyboard navigation for all tab selectors
        self._setup_tab_keyboard_nav()

        # Show placeholder initially
        self._show_placeholder()

    # ── Public API ──

    def refresh_course_list(self):
        """Scan the output folder for courses with .manifest/ JSON files."""
        output_folder = self._view.var_output_folder.get().strip()
        self._course_folders.clear()

        if not output_folder:
            self._show_placeholder("Set an output folder on the Run tab to browse course content.")
            return

        if not os.path.isdir(output_folder):
            self._show_placeholder(f"Output folder is not accessible:\n{output_folder}")
            return

        for entry in os.listdir(output_folder):
            entry_path = os.path.join(output_folder, entry)
            if not os.path.isdir(entry_path):
                continue
            manifest_dir = os.path.join(entry_path, ".manifest")
            if not os.path.isdir(manifest_dir):
                continue
            # Look for any .json file in .manifest/
            json_files = [f for f in os.listdir(manifest_dir) if f.endswith(".json")]
            if json_files:
                self._course_folders[entry] = entry_path

        if not self._course_folders:
            self._show_placeholder("No scanned courses found. Run a scan to populate this view.")
            return

        names = sorted(self._course_folders.keys())
        self._dropdown.configure(values=names)

        # Preserve the current selection if it still exists
        previous = self._course_var.get()
        if previous in names:
            selected = previous
        else:
            selected = names[0]

        self._course_var.set(selected)
        self._show_container()
        self._on_course_selected(selected)

    def clear(self):
        """Reset all tables and detail panel."""
        for table in self._tables.values():
            table.clear()
        self._set_detail("")
        self._selected_row = None
        self._selected_table_key = None
        self._summary_frame.pack_forget()
        self._open_folder_btn.configure(state="disabled")
        self._open_file_btn.configure(state="disabled")
        self._open_source_btn.configure(state="disabled")
        for btn in self._status_buttons.values():
            btn.configure(state="disabled")

    # ── Internal ──

    def _show_placeholder(self, message="Set an output folder on the Run tab to browse course content."):
        self._container.pack_forget()
        self._placeholder.configure(text=message)
        self._placeholder.pack(expand=True)

    def _show_container(self):
        self._placeholder.pack_forget()
        self._container.pack(fill="both", expand=True)

    def _setup_tab_keyboard_nav(self):
        """Make all content tab selectors navigable with arrows and Enter-to-table."""

        # Nested tabviews: main tab name → (nested tabview, [(sub-tab name, table key), ...])
        nested = {
            "Documents": (self._docs_tabview, [
                ("Documents", "documents"), ("Document Sites", "document_sites"),
            ]),
            "Videos": (self._vids_tabview, [
                ("Video Sites", "video_sites"), ("Video Files", "video_files"),
            ]),
            "Audio": (self._audio_tabview, [
                ("Audio Files", "audio_files"), ("Audio Sites", "audio_sites"),
            ]),
        }
        # Main tabs with no sub-tabs → table key directly
        direct = {"Images": "image_files", "Unsorted": "unsorted"}

        def _focus_table(table_key):
            """Move focus into a table, selecting the first row."""
            table = self._tables.get(table_key)
            if not table:
                return
            tree = table._tree
            children = tree.get_children()
            if children:
                tree.selection_set(children[0])
                tree.focus(children[0])
            tree.focus_set()

        def _add_nav(tabview, tab_names, on_enter=None, on_escape=None):
            """Wire up focus rings, Left/Right arrows, Enter, and Escape on a tabview."""
            try:
                buttons = tabview._segmented_button._buttons_dict
            except AttributeError:
                return
            for name in tab_names:
                btn = buttons.get(name)
                if not btn:
                    continue
                _add_focus_ring(btn)

                def _nav(event, current=name, direction=0):
                    idx = tab_names.index(current) + direction
                    if 0 <= idx < len(tab_names):
                        target = tab_names[idx]
                        tabview.set(target)
                        buttons[target].focus_set()
                    return "break"

                btn.bind("<Left>", lambda e, n=name: _nav(e, n, -1))
                btn.bind("<Right>", lambda e, n=name: _nav(e, n, 1))
                if on_enter:
                    btn.bind("<Return>", lambda e, n=name: on_enter(n))
                if on_escape:
                    btn.bind("<Escape>", lambda e: on_escape())

        def _focus_btn(tabview, tab_name):
            """Focus a specific tab selector button."""
            try:
                btn = tabview._segmented_button._buttons_dict.get(tab_name)
                if btn:
                    btn.focus_set()
            except AttributeError:
                pass

        # ── Main tabview ──
        main_tabs = ["Documents", "Videos", "Audio", "Images", "Unsorted"]

        def _main_enter(tab_name):
            if tab_name in nested:
                ntv, _ = nested[tab_name]
                _focus_btn(ntv, ntv.get())
            elif tab_name in direct:
                _focus_table(direct[tab_name])
            return "break"

        _add_nav(self._tabview, main_tabs, on_enter=_main_enter)

        # ── Nested tabviews ──
        for main_tab, (ntv, sub_tabs) in nested.items():
            sub_names = [s[0] for s in sub_tabs]
            sub_map = dict(sub_tabs)

            def _sub_enter(tab_name, m=sub_map):
                table_key = m.get(tab_name)
                if table_key:
                    _focus_table(table_key)
                return "break"

            def _sub_escape(mt=main_tab):
                _focus_btn(self._tabview, mt)

            _add_nav(ntv, sub_names, on_enter=_sub_enter, on_escape=_sub_escape)

            # Escape from table → back to its sub-tab selector
            for sub_name, table_key in sub_tabs:
                table = self._tables.get(table_key)
                if table:
                    def _esc(e, tv=ntv, sn=sub_name):
                        _focus_btn(tv, sn)
                    table._tree.bind("<Escape>", _esc)

        # ── Direct tables (no sub-tabs): Escape → main tab selector ──
        for main_tab, table_key in direct.items():
            table = self._tables.get(table_key)
            if table:
                def _esc(e, mt=main_tab):
                    _focus_btn(self._tabview, mt)
                table._tree.bind("<Escape>", _esc)

    def _open_course_folder(self):
        """Open the selected course's folder in the file explorer."""
        folder_path = self._course_folders.get(self._course_var.get())
        if folder_path and os.path.isdir(folder_path):
            os.startfile(folder_path)

    def _open_file_or_site(self):
        """Open file location or site URL depending on row type."""
        if not self._selected_row:
            return
        save_path = self._selected_row.get("save_path", "")
        if save_path:
            folder = os.path.dirname(save_path)
            if os.path.isdir(folder):
                os.startfile(folder)
        else:
            url = self._selected_row.get("url", "")
            if url:
                webbrowser.open(url)

    def _open_source_page(self):
        """Open the source_page_url in the default browser."""
        if not self._selected_row:
            return
        url = self._selected_row.get("source_page_url", "")
        if url:
            webbrowser.open(url)

    def _load_review_statuses(self, manifest_dir):
        """Load review_status.json from the manifest directory."""
        path = os.path.join(manifest_dir, "review_status.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def _save_review_statuses(self):
        """Write current review statuses to the manifest directory."""
        if not self._manifest_dir:
            return
        path = os.path.join(self._manifest_dir, "review_status.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._review_statuses, f, indent=2)
        except OSError:
            pass

    def _on_status_changed(self, value):
        """Handle status button click — persist and update table."""
        if not self._selected_row:
            return
        url = self._selected_row.get("url", "")
        if not url:
            return

        self._review_statuses[url] = {"status": value}
        self._save_review_statuses()

        # Update the row data and table display
        self._selected_row["status"] = value
        if self._selected_table_key and self._selected_table_key in self._tables:
            table = self._tables[self._selected_table_key]
            idx = table.get_selected_index()
            if idx >= 0:
                table.update_row(idx, self._selected_row)

    def _on_course_selected(self, choice):
        """Load content JSON and review statuses for the selected course."""
        folder_path = self._course_folders.get(choice)
        if not folder_path:
            self.clear()
            return

        manifest_dir = os.path.join(folder_path, ".manifest")
        json_files = [f for f in os.listdir(manifest_dir)
                      if f.endswith(".json") and f != "review_status.json"]
        if not json_files:
            self.clear()
            return

        json_path = os.path.join(manifest_dir, json_files[0])
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            self.clear()
            return

        self._manifest_dir = manifest_dir
        self._review_statuses = self._load_review_statuses(manifest_dir)
        self._current_data = data
        self._populate_from_data(data)

    def _on_filter_changed(self):
        """Re-populate tables when a filter checkbox changes."""
        if self._current_data:
            self._populate_from_data(self._current_data)

    def _check_downloaded(self, rows):
        """Add a 'downloaded' field with the download date or 'No'."""
        for row in rows:
            save_path = row.get("save_path", "")
            if save_path:
                normalized = os.path.normpath(save_path)
                match_path = None
                if os.path.isfile(normalized):
                    match_path = normalized
                else:
                    # File may exist in a different date folder (downloaded on a previous day)
                    wildcard_path = _DATE_FOLDER_RE.sub('*', normalized, count=1)
                    matches = glob.glob(wildcard_path)
                    if matches:
                        match_path = matches[0]

                if match_path:
                    date_match = _DATE_FOLDER_RE.search(match_path)
                    row["downloaded"] = date_match.group() if date_match else "Yes"
                else:
                    row["downloaded"] = "No"
            else:
                row["downloaded"] = ""
        return rows

    def _populate_from_data(self, data):
        """Fill all tables from a content data dict."""
        content = data.get("content", {})

        # Map JSON keys to table keys
        mapping = {
            "documents": ("documents", "documents"),
            "document_sites": ("documents", "document_sites"),
            "video_sites": ("videos", "video_sites"),
            "video_files": ("videos", "video_files"),
            "audio_files": ("audio", "audio_files"),
            "audio_sites": ("audio", "audio_sites"),
            "image_files": ("images", "image_files"),
            "unsorted": ("unsorted", "unsorted"),
        }

        # Tables that have save_path and need download checking
        downloadable = {"documents", "video_files", "audio_files", "image_files"}
        show_inactive = self._show_inactive_var.get()

        counts = {}
        for table_key, (category, sub_key) in mapping.items():
            rows = content.get(category, {}).get(sub_key, [])
            if not show_inactive:
                rows = [r for r in rows if r.get("source_page_url") and not r.get("is_hidden")]
            if table_key in downloadable:
                rows = self._check_downloaded(rows)
            if table_key == "image_files":
                for row in rows:
                    if not row.get("title"):
                        row["title"] = row.get("file_name", "")
            for row in rows:
                url = row.get("url", "")
                row["status"] = self._review_statuses.get(url, {}).get("status", _DEFAULT_STATUS)
            self._tables[table_key].populate(rows)
            counts[table_key] = len(rows)

        # Update summary
        course_name = data.get("course_name", "")
        course_id = data.get("course_id", "")
        self._course_label.configure(
            text=f"{course_name}  (ID: {course_id})" if course_name else f"Course {course_id}"
        )

        total = sum(counts.values())
        parts = []
        doc_count = counts["documents"] + counts["document_sites"]
        if doc_count:
            parts.append(f"{doc_count} docs")
        vid_count = counts["video_sites"] + counts["video_files"]
        if vid_count:
            parts.append(f"{vid_count} videos")
        aud_count = counts["audio_files"] + counts["audio_sites"]
        if aud_count:
            parts.append(f"{aud_count} audio")
        if counts["image_files"]:
            parts.append(f"{counts['image_files']} images")
        if counts["unsorted"]:
            parts.append(f"{counts['unsorted']} unsorted")

        self._stats_label.configure(text=f"{total} items: {', '.join(parts)}" if parts else "0 items")
        self._summary_frame.pack(fill="x", pady=(0, 5), before=self._tabview)

        self._open_folder_btn.configure(state="normal")
        self._selected_row = None
        self._selected_table_key = None
        self._open_file_btn.configure(state="disabled")
        self._open_source_btn.configure(state="disabled")
        for btn in self._status_buttons.values():
            btn.configure(state="disabled")
        self._set_detail("")

    def _on_row_select(self, row):
        """Show selected row details and enable/disable action buttons."""
        self._selected_row = row

        # Determine which table this selection came from
        for key, table in self._tables.items():
            if table.get_selected() is row:
                self._selected_table_key = key
                break

        # Enable/disable status buttons
        has_url = bool(row.get("url"))
        for btn in self._status_buttons.values():
            btn.configure(state="normal" if has_url else "disabled")

        # Switch button between file location and site URL mode
        save_path = row.get("save_path", "")
        url = row.get("url", "")
        if save_path:
            self._open_file_btn.configure(text="Open File Location")
            if os.path.isdir(os.path.dirname(save_path)):
                self._open_file_btn.configure(state="normal")
            else:
                self._open_file_btn.configure(state="disabled")
        elif url:
            self._open_file_btn.configure(text="Open Site", state="normal")
        else:
            self._open_file_btn.configure(text="Open File Location", state="disabled")

        # Enable Open Source Page if source_page_url exists
        if row.get("source_page_url"):
            self._open_source_btn.configure(state="normal")
        else:
            self._open_source_btn.configure(state="disabled")

        # Populate detail panel
        lines = []
        for key, value in row.items():
            lines.append(f"{key}: {value}")
        self._set_detail("\n".join(lines))

    def _set_detail(self, text):
        if self._detail is None:
            return
        self._detail.configure(state="normal")
        self._detail.delete("1.0", "end")
        if text:
            # Insert text and make URLs clickable
            for line in text.split("\n"):
                if ": http" in line:
                    key, _, url = line.partition(": ")
                    self._detail.insert("end", f"{key}: ")
                    start = self._detail.index("end-1c")
                    self._detail.insert("end", url)
                    end = self._detail.index("end-1c")
                    tag_name = f"link_{start}"
                    self._detail.tag_add(tag_name, start, end)
                    self._detail.tag_config(tag_name, foreground="#3B8ED0", underline=True)
                    self._detail.tag_bind(tag_name, "<Button-1>",
                                          lambda e, u=url: webbrowser.open(u))
                    self._detail.insert("end", "\n")
                else:
                    self._detail.insert("end", line + "\n")
        self._detail.configure(state="disabled")