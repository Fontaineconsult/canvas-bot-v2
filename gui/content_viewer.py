import glob
import json
import os
import re
import shutil
import webbrowser
from tkinter import messagebox
import customtkinter as ctk

from gui.table_widget import ContentTable
from gui.widgets import _add_focus_ring, _underline_char, Tooltip


# Review status options (add new values here to expand)
_REVIEW_STATUSES = ["Needs Review", "Passed", "Ignore"]
_DEFAULT_STATUS = "-"  # unreviewed — no color
_SHOW_DETAIL_PANEL = False  # Set to True to show the diagnostic detail panel

# Short display labels for hidden_reason values
_REASON_LABELS = {
    "hidden_for_user": "Hidden",
    "hidden_from_students": "Hidden",
    "unpublished": "Unpublished",
    "locked": "Locked",
}

# Column definitions per content sub-type
_ORDER_COL = {"id": "order", "heading": "Order", "width": 65}

_COLUMNS = {
    "documents": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 150, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 100},
        {"id": "file_source", "heading": "File Source", "width": 120},
        {"id": "source_page_type", "heading": "Source", "width": 150},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "downloaded", "heading": "Downloaded", "width": 130},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "document_sites": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "video_sites": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "video_files": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "audio_files": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "audio_sites": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "image_files": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True, "max_chars": 60},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "institution_video": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "digital_textbooks": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "file_storage": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 165, "stretch": True},
        {"id": "url", "heading": "URL", "width": 235, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 140},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
    "unsorted": [
        _ORDER_COL,
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "url", "heading": "URL", "width": 250, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "visibility", "heading": "Visibility", "width": 120},
        {"id": "status", "heading": "Status", "width": 160, "minwidth": 160, "anchor": "center"},
    ],
}

_DATE_FOLDER_RE = re.compile(r'(?<=[\\/])\d{2}-\d{2}-\d{4}(?=[\\/])')

# Table keys that represent site/link views (no downloadable files)
_SITE_KEYS = {"document_sites", "video_sites", "audio_sites", "institution_video",
              "digital_textbooks", "file_storage", "unsorted"}


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
        top_bar.pack(fill="x", pady=(0, 2))

        ctk.CTkLabel(top_bar, text="Course:", width=60, anchor="w").pack(side="left")
        self._course_var = ctk.StringVar()
        self._dropdown = ctk.CTkOptionMenu(
            top_bar, variable=self._course_var,
            values=["(none)"], command=self._on_course_selected,
            width=400,
        )
        self._dropdown.pack(side="left", fill="x", expand=True, padx=(0, 5))
        # CTkOptionMenu doesn't support border_width/border_color, so use highlight ring
        self._dropdown.configure(button_color=("gray70", "gray30"))
        self._dropdown.bind("<FocusIn>", lambda e: self._dropdown.configure(button_color="#3B8ED0"))
        self._dropdown.bind("<FocusOut>", lambda e: self._dropdown.configure(button_color=("gray70", "gray30")))
        self._dropdown.bind("<Return>", lambda e: self._dropdown._clicked())
        self._dropdown.bind("<space>", lambda e: self._dropdown._clicked())
        Tooltip(self._dropdown, "Select a previously scanned course to browse its content")

        refresh_btn = ctk.CTkButton(top_bar, text="Refresh", width=80,
                                    command=self.refresh_course_list)
        refresh_btn.pack(side="right")
        _add_focus_ring(refresh_btn)
        _underline_char(refresh_btn, 2)  # F → Alt+F
        Tooltip(refresh_btn, "Re-scan the output folder for new or updated course data (Alt+F)")

        self._delete_btn = ctk.CTkButton(
            top_bar, text="Delete", width=80,
            fg_color="#8B0000", hover_color="#A52A2A",
            command=self._delete_selected_course, state="disabled",
        )
        self._delete_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(self._delete_btn)
        Tooltip(self._delete_btn, "Delete the selected course folder and its data")

        self._open_folder_btn = ctk.CTkButton(top_bar, text="Open Folder", width=100,
                                              command=self._open_course_folder, state="disabled")
        self._open_folder_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(self._open_folder_btn)
        _underline_char(self._open_folder_btn, 0)  # O → Alt+O
        Tooltip(self._open_folder_btn, "Open the selected course's folder in File Explorer (Alt+O)")

        # ── Row 2: summary (30%) | selector buttons (40%) | status buttons (30%) ──
        _sep_color = ("gray75", "gray35")  # 1px divider color (light, dark)

        row2 = ctk.CTkFrame(self._container, height=0, fg_color="transparent")
        row2.pack(fill="x", pady=(3, 0))
        row2.grid_propagate(True)
        # 5 grid columns: content | sep | content | sep | content
        row2.grid_columnconfigure(0, weight=3)  # 30%
        row2.grid_columnconfigure(2, weight=4)  # 40%
        row2.grid_columnconfigure(4, weight=3)  # 30%

        # Left column: course summary
        _heading_font = ctk.CTkFont(size=11, weight="bold")
        _heading_color = ("gray40", "gray60")

        self._summary_frame = ctk.CTkFrame(row2, height=0, fg_color="transparent")
        self._summary_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 8))

        ctk.CTkLabel(self._summary_frame, text="Course Info",
                     font=_heading_font, text_color=_heading_color, anchor="w").pack(fill="x")

        self._course_label = ctk.CTkLabel(
            self._summary_frame, text="",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._course_label.pack(fill="x")

        self._stats_label = ctk.CTkLabel(
            self._summary_frame, text="",
            font=ctk.CTkFont(size=12), text_color="gray", anchor="w", justify="left",
        )
        self._stats_label.pack(fill="x")

        # Separator 1
        ctk.CTkFrame(row2, width=1, height=1, fg_color=_sep_color).grid(
            row=0, column=1, sticky="ns", padx=4)

        # Center column: two-row selector — main categories on top, sub-categories below
        # Category definitions: name → list of (sub-label, table_key)
        self._categories = {
            "Documents": [("Documents", "documents"), ("Document Sites", "document_sites")],
            "Videos":    [("Video Sites", "video_sites"), ("Video Files", "video_files"), ("Inst. Video", "institution_video")],
            "Audio":     [("Audio Files", "audio_files"), ("Audio Sites", "audio_sites")],
            "Images":    [("Images", "image_files")],
            "Other":     [("Textbooks", "digital_textbooks"), ("File Storage", "file_storage")],
            "Unsorted":  [("Unsorted", "unsorted")],
        }
        self._category_order = ["Documents", "Videos", "Audio", "Images", "Other", "Unsorted"]
        self._active_category = "Documents"
        self._active_table_key = "documents"  # default active table

        selectors_frame = ctk.CTkFrame(row2, height=0, fg_color="transparent")
        selectors_frame.grid(row=0, column=2, sticky="ns")

        ctk.CTkLabel(selectors_frame, text="Select Content",
                     font=_heading_font, text_color=_heading_color).pack()

        # Top row: main category buttons
        cat_row = ctk.CTkFrame(selectors_frame, fg_color="transparent")
        cat_row.pack()

        # Lighter blue for active/inactive selector buttons (light mode, dark mode)
        _sel_active = ("#7BB8E0", "#2A5F8A")
        _sel_inactive = ("#D0E4F5", "#1A3A55")
        _sel_hover = ("#6AADE0", "#1F5070")

        self._category_buttons = {}  # category_name -> CTkButton
        for cat in self._category_order:
            btn = ctk.CTkButton(
                cat_row, text=cat, width=70, height=28,
                font=ctk.CTkFont(size=12),
                fg_color=_sel_active if cat == self._active_category else _sel_inactive,
                text_color=("gray10", "gray90"),
                hover_color=_sel_hover,
                command=lambda c=cat: self._switch_category(c),
            )
            btn.pack(side="left", padx=(0, 3))
            _add_focus_ring(btn)
            self._category_buttons[cat] = btn

        # Bottom row: sub-category buttons (swapped when main category changes)
        self._sub_row = ctk.CTkFrame(selectors_frame, fg_color="transparent")
        self._sub_row.pack(pady=(3, 0))

        self._selector_buttons = {}  # table_key -> CTkButton (all sub-buttons across all categories)
        self._selector_keys_order = []  # flat list of all table keys in order
        self._sub_frames = {}  # category_name -> frame holding its sub-buttons
        self._sel_active = _sel_active  # store for _switch methods
        self._sel_inactive = _sel_inactive

        for cat in self._category_order:
            frame = ctk.CTkFrame(self._sub_row, fg_color="transparent")
            self._sub_frames[cat] = frame
            for label, key in self._categories[cat]:
                btn = ctk.CTkButton(
                    frame, text=label, width=80, height=26,
                    font=ctk.CTkFont(size=11),
                    fg_color=_sel_active if key == self._active_table_key else _sel_inactive,
                    text_color=("gray10", "gray90"),
                    hover_color=_sel_hover,
                    command=lambda k=key: self._switch_table(k),
                )
                btn.pack(side="left", padx=(0, 3))
                _add_focus_ring(btn)
                self._selector_buttons[key] = btn
                self._selector_keys_order.append(key)

        # Show the default category's sub-buttons
        self._sub_frames[self._active_category].pack()

        # Separator 2
        ctk.CTkFrame(row2, width=1, height=1, fg_color=_sep_color).grid(
            row=0, column=3, sticky="ns", padx=4)

        # Right column: status buttons stacked vertically
        status_frame = ctk.CTkFrame(row2, height=0, fg_color="transparent")
        status_frame.grid(row=0, column=4, sticky="nse", padx=(8, 0))

        ctk.CTkLabel(status_frame, text="Status",
                     font=_heading_font, text_color=_heading_color, anchor="e").pack(fill="x")

        _status_underline = {"Needs Review": 11, "Passed": 5, "Ignore": 0}
        _status_keys = {"Needs Review": "W", "Passed": "D", "Ignore": "I"}
        _status_btn_colors = {
            "Passed":       {"fg": "#2d6a2d", "hover": "#236b23"},
            "Needs Review": {"fg": "#8a6d00", "hover": "#6b5500"},
            "Ignore":       {"fg": "#555555", "hover": "#444444"},
        }
        self._status_buttons = {}
        for status in _REVIEW_STATUSES:
            sc = _status_btn_colors.get(status, {})
            btn = ctk.CTkButton(
                status_frame, text=status, width=130, height=26,
                fg_color=sc.get("fg"), hover_color=sc.get("hover"),
                command=lambda s=status: self._on_status_changed(s),
                state="disabled",
            )
            btn.pack(anchor="e", pady=(0, 2))
            _add_focus_ring(btn)
            _underline_char(btn, _status_underline.get(status, 0))
            Tooltip(btn, f"Mark selected item as '{status}' (Alt+{_status_keys.get(status, '?')})")
            self._status_buttons[status] = btn

        # ── Row 3: filter bar ──
        filter_bar = ctk.CTkFrame(self._container, fg_color="transparent")
        filter_bar.pack(fill="x", pady=(0, 2))

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

        # ── Row 4: table frame (holds all 8 tables, one visible at a time) ──
        self._table_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        self._table_frame.pack(fill="both", expand=True, pady=(0, 2))

        _PLACEHOLDERS = {
            "documents": "No Documents Found",
            "document_sites": "No Document Sites Found",
            "video_sites": "No Video Sites Found",
            "video_files": "No Video Files Found",
            "audio_files": "No Audio Files Found",
            "audio_sites": "No Audio Sites Found",
            "image_files": "No Image Files Found",
            "institution_video": "No Institution Video Found",
            "digital_textbooks": "No Digital Textbooks Found",
            "file_storage": "No File Storage Sites Found",
            "unsorted": "No Unsorted Content Found",
        }
        for key in self._selector_keys_order:
            self._tables[key] = ContentTable(
                self._table_frame,
                _COLUMNS[key], on_select=self._on_row_select,
                placeholder=_PLACEHOLDERS[key], status_key="status",
            )
        # Show only the default active table
        self._tables[self._active_table_key].pack(fill="both", expand=True)

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

        # ── Row 5: action buttons ──
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

        self._open_direct_btn = ctk.CTkButton(
            btn_row, text="Open File", width=100,
            command=self._open_file_direct, state="disabled",
        )
        self._open_direct_btn.pack(side="left", padx=(0, 5))
        _add_focus_ring(self._open_direct_btn)
        _underline_char(self._open_direct_btn, 1)  # P in "oPen" → Alt+P
        Tooltip(self._open_direct_btn, "Open the file in its default application (Alt+P)")

        self._open_source_btn = ctk.CTkButton(
            btn_row, text="Open Source Page", width=140,
            command=self._open_source_page, state="disabled",
        )
        self._open_source_btn.pack(side="left")
        _add_focus_ring(self._open_source_btn)
        _underline_char(self._open_source_btn, 5)  # S in "Source" → Alt+S
        Tooltip(self._open_source_btn, "Open the Canvas page where this content was found (Alt+S)")

        self._open_canvas_btn = ctk.CTkButton(
            btn_row, text="Open Canvas Files", width=150,
            command=self._open_in_canvas, state="disabled",
        )
        self._open_canvas_btn.pack(side="right")
        _add_focus_ring(self._open_canvas_btn)
        _underline_char(self._open_canvas_btn, 5)  # C in "Canvas" → Alt+C
        Tooltip(self._open_canvas_btn, "Open the course Files page in Canvas to manage files (Alt+C)")

        # Keyboard navigation for selector buttons
        self._setup_selector_keyboard_nav()

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
        self._course_label.configure(text="")
        self._stats_label.configure(text="")
        self._open_folder_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")
        self._open_file_btn.configure(state="disabled")
        self._open_direct_btn.configure(state="disabled")
        self._open_source_btn.configure(state="disabled")
        self._open_canvas_btn.configure(state="disabled")
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

    def _switch_category(self, cat):
        """Switch main category — update sub-buttons and show the first sub-table."""
        if cat == self._active_category:
            return
        # Hide old sub-frame, show new
        self._sub_frames[self._active_category].pack_forget()
        self._active_category = cat
        self._sub_frames[cat].pack()
        # Highlight active category button
        for c, btn in self._category_buttons.items():
            btn.configure(fg_color=self._sel_active if c == cat else self._sel_inactive)
        # Switch to the first sub-table of this category
        first_key = self._categories[cat][0][1]
        self._switch_table(first_key)

    def _switch_table(self, key):
        """Show the table for *key* and hide the previously active one."""
        if key == self._active_table_key:
            return
        # Hide current
        if self._active_table_key in self._tables:
            self._tables[self._active_table_key].pack_forget()
        # Show new
        self._active_table_key = key
        self._tables[key].pack(fill="both", expand=True)
        # Highlight active sub-button
        for btn_key, btn in self._selector_buttons.items():
            btn.configure(fg_color=self._sel_active if btn_key == key else self._sel_inactive)
        # Hide "Open File" for site views (no downloadable files)
        if key in _SITE_KEYS:
            self._open_direct_btn.pack_forget()
        else:
            self._open_direct_btn.pack(side="left", padx=(0, 5), after=self._open_file_btn)

    def _setup_selector_keyboard_nav(self):
        """Wire arrow keys on category and sub-category buttons, Enter/Escape for table focus."""
        cat_order = self._category_order

        def _focus_table(table_key):
            table = self._tables.get(table_key)
            if not table:
                return
            tree = table._tree
            children = tree.get_children()
            if children:
                tree.selection_set(children[0])
                tree.focus(children[0])
            tree.focus_set()

        # Main category buttons: Left/Right to navigate, Enter/Down to sub-row
        for ci, cat in enumerate(cat_order):
            btn = self._category_buttons[cat]

            def _cat_nav(event, idx=ci, direction=0):
                target = idx + direction
                if 0 <= target < len(cat_order):
                    target_cat = cat_order[target]
                    self._switch_category(target_cat)
                    self._category_buttons[target_cat].focus_set()
                return "break"

            def _cat_enter(event, c=cat):
                # Focus the first sub-button of this category
                first_key = self._categories[c][0][1]
                self._selector_buttons[first_key].focus_set()
                return "break"

            btn.bind("<Left>", lambda e, idx=ci: _cat_nav(e, idx, -1))
            btn.bind("<Right>", lambda e, idx=ci: _cat_nav(e, idx, 1))
            btn.bind("<Return>", _cat_enter)
            btn.bind("<Down>", _cat_enter)

        # Sub-category buttons: Left/Right within the category, Enter to table, Escape/Up to category
        for cat in cat_order:
            subs = self._categories[cat]
            sub_keys = [s[1] for s in subs]
            for si, (_, key) in enumerate(subs):
                btn = self._selector_buttons[key]

                def _sub_nav(event, idx=si, keys=sub_keys, direction=0):
                    target = idx + direction
                    if 0 <= target < len(keys):
                        target_key = keys[target]
                        self._switch_table(target_key)
                        self._selector_buttons[target_key].focus_set()
                    return "break"

                def _sub_escape(event, c=cat):
                    self._category_buttons[c].focus_set()
                    return "break"

                btn.bind("<Left>", lambda e, idx=si, keys=sub_keys: _sub_nav(e, idx, keys, -1))
                btn.bind("<Right>", lambda e, idx=si, keys=sub_keys: _sub_nav(e, idx, keys, 1))
                btn.bind("<Return>", lambda e, k=key: (_focus_table(k), "break")[-1])
                btn.bind("<Escape>", _sub_escape)
                btn.bind("<Up>", _sub_escape)

        # Escape from any table → focus its sub-category button
        for key in self._selector_keys_order:
            table = self._tables.get(key)
            if table:
                def _esc(e, k=key):
                    self._selector_buttons[k].focus_set()
                table._tree.bind("<Escape>", _esc)

    def _delete_selected_course(self):
        """Delete the selected course folder after confirmation."""
        name = self._course_var.get()
        folder_path = self._course_folders.get(name)
        if not folder_path or not os.path.isdir(folder_path):
            return
        if not messagebox.askyesno(
            "Delete Course",
            f"Permanently delete this course folder?\n\n{name}\n\n{folder_path}",
        ):
            return
        try:
            shutil.rmtree(folder_path)
        except OSError:
            messagebox.showerror("Error", f"Could not delete folder:\n{folder_path}")
            return
        self.clear()
        self.refresh_course_list()

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

    # Executable/dangerous extensions that must never be opened via os.startfile
    _BLOCKED_EXTENSIONS = frozenset({
        # Windows executables & installers
        ".exe", ".msi", ".msp", ".mst", ".com", ".scr", ".pif", ".gadget", ".appref-ms",
        # Scripts
        ".bat", ".cmd", ".ps1", ".psm1", ".psd1", ".ps1xml", ".vbs", ".vbe",
        ".js", ".jse", ".ws", ".wsf", ".wsc", ".wsh",
        # Shell & registry
        ".sh", ".bash", ".reg", ".inf",
        # Compiled/managed code
        ".dll", ".sys", ".drv", ".cpl", ".ocx",
        # Shortcuts & links (can redirect to executables)
        ".lnk", ".url",
        # Java / .NET
        ".jar", ".class",
        # Office macros (macro-enabled formats)
        ".docm", ".xlsm", ".pptm", ".dotm", ".xltm", ".potm",
        # Other dangerous formats
        ".hta", ".crt", ".application", ".appx", ".msix",
    })

    def _open_file_direct(self):
        """Open the downloaded file in its default application."""
        if not self._selected_row:
            return
        save_path = self._selected_row.get("save_path", "")
        if not save_path or not os.path.isfile(save_path):
            return
        ext = os.path.splitext(save_path)[1].lower()
        if ext in self._BLOCKED_EXTENSIONS:
            messagebox.showwarning(
                "Blocked File Type",
                f"Cannot open '{os.path.basename(save_path)}'.\n\n"
                f"Files with the '{ext}' extension are blocked for security.",
            )
            return
        os.startfile(save_path)

    def _open_source_page(self):
        """Open the source_page_url in the default browser."""
        if not self._selected_row:
            return
        url = self._selected_row.get("source_page_url", "")
        if url:
            webbrowser.open(url)

    def _open_in_canvas(self):
        """Open the course Files page in Canvas."""
        if not self._current_data:
            return
        course_url = self._current_data.get("course_url", "")
        if course_url:
            webbrowser.open(f"{course_url}/files")

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
            "institution_video": ("videos", "institution_video"),
            "digital_textbooks": ("other", "digital_textbooks"),
            "file_storage": ("other", "file_storage"),
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
                # Build visibility column from hidden_reason + source_page_url
                reason = row.get("hidden_reason", "")
                has_source = bool(row.get("source_page_url"))
                if reason:
                    labels = []
                    for part in reason.split(", "):
                        label = _REASON_LABELS.get(part, part)
                        # Hidden items linked from a page are visible to students
                        if label == "Hidden" and has_source:
                            continue
                        labels.append(label)
                    seen = set()
                    unique = [l for l in labels if not (l in seen or seen.add(l))]
                    row["visibility"] = ", ".join(unique) if unique else "Visible"
                else:
                    row["visibility"] = "Visible"
            self._tables[table_key].populate(rows)
            counts[table_key] = len(rows)

        # Update summary
        course_name = data.get("course_name", "")
        self._course_label.configure(text=course_name or "Untitled Course")

        # Count hidden and inactive across all unfiltered content
        hidden_count = 0
        inactive_count = 0
        for table_key, (category, sub_key) in mapping.items():
            for row in content.get(category, {}).get(sub_key, []):
                if row.get("is_hidden"):
                    hidden_count += 1
                if not row.get("source_page_url"):
                    inactive_count += 1

        total = sum(counts.values())
        # Line 1: total, hidden, inactive
        line1_parts = [f"{total} items"]
        if hidden_count:
            line1_parts.append(f"Hidden: {hidden_count}")
        if inactive_count:
            line1_parts.append(f"Inactive: {inactive_count}")

        # Line 2+: content type counts (max 3 per line)
        type_parts = []
        doc_count = counts["documents"] + counts["document_sites"]
        if doc_count:
            type_parts.append(f"Docs: {doc_count}")
        vid_count = counts["video_sites"] + counts["video_files"]
        if vid_count:
            type_parts.append(f"Video: {vid_count}")
        if counts.get("institution_video", 0):
            type_parts.append(f"Inst. Video: {counts['institution_video']}")
        aud_count = counts["audio_files"] + counts["audio_sites"]
        if aud_count:
            type_parts.append(f"Audio: {aud_count}")
        if counts["image_files"]:
            type_parts.append(f"Images: {counts['image_files']}")
        other_count = counts.get("digital_textbooks", 0) + counts.get("file_storage", 0)
        if other_count:
            type_parts.append(f"Other: {other_count}")
        if counts["unsorted"]:
            type_parts.append(f"Unsorted: {counts['unsorted']}")

        lines = ["  |  ".join(line1_parts)]
        for i in range(0, len(type_parts), 3):
            lines.append("  |  ".join(type_parts[i:i + 3]))
        self._stats_label.configure(text="\n".join(lines))

        self._open_folder_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")
        self._open_canvas_btn.configure(
            state="normal" if data.get("course_url") else "disabled"
        )
        self._selected_row = None
        self._selected_table_key = None
        self._open_file_btn.configure(state="disabled")
        self._open_direct_btn.configure(state="disabled")
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

        # Enable "Open File" if the downloaded file exists
        self._open_direct_btn.configure(
            state="normal" if save_path and os.path.isfile(save_path) else "disabled"
        )

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