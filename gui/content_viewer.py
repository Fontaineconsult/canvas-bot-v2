import json
import os
import webbrowser
import customtkinter as ctk

from gui.table_widget import ContentTable
from gui.widgets import _add_focus_ring, Tooltip


# Column definitions per content sub-type
_COLUMNS = {
    "documents": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
        {"id": "order", "heading": "Order", "width": 70},
    ],
    "document_sites": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "url", "heading": "URL", "width": 250, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "order", "heading": "Order", "width": 70},
    ],
    "video_sites": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "url", "heading": "URL", "width": 250, "stretch": True},
        {"id": "is_captioned", "heading": "Captioned", "width": 105},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
    ],
    "video_files": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
    ],
    "audio_files": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
    ],
    "audio_sites": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "url", "heading": "URL", "width": 250, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
    ],
    "image_files": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "file_type", "heading": "Type", "width": 80},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
        {"id": "downloaded", "heading": "Downloaded", "width": 110},
    ],
    "unsorted": [
        {"id": "title", "heading": "Title", "width": 175, "stretch": True},
        {"id": "url", "heading": "URL", "width": 250, "stretch": True},
        {"id": "source_page_type", "heading": "Source", "width": 130},
        {"id": "is_hidden", "heading": "Hidden", "width": 80},
    ],
}


class ContentViewer:
    """Persistent browser for scanned course content stored in .manifest/ folders."""

    def __init__(self, parent_frame, view):
        self._view = view
        self._parent = parent_frame
        self._course_folders = {}  # display_name -> folder_path
        self._tables = {}         # sub_type key -> ContentTable
        self._selected_row = None
        self._current_data = None  # raw JSON data for re-filtering

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
        Tooltip(refresh_btn, "Re-scan the output folder for new or updated course data")

        self._open_folder_btn = ctk.CTkButton(top_bar, text="Open Folder", width=100,
                                              command=self._open_course_folder, state="disabled")
        self._open_folder_btn.pack(side="right", padx=(0, 5))
        _add_focus_ring(self._open_folder_btn)
        Tooltip(self._open_folder_btn, "Open the selected course's folder in File Explorer")

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
        )
        self._tables["documents"].pack(fill="both", expand=True)
        self._tables["document_sites"] = ContentTable(
            self._docs_tabview.tab("Document Sites"),
            _COLUMNS["document_sites"], on_select=self._on_row_select,
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
        )
        self._tables["video_sites"].pack(fill="both", expand=True)
        self._tables["video_files"] = ContentTable(
            self._vids_tabview.tab("Video Files"),
            _COLUMNS["video_files"], on_select=self._on_row_select,
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
        )
        self._tables["audio_files"].pack(fill="both", expand=True)
        self._tables["audio_sites"] = ContentTable(
            self._audio_tabview.tab("Audio Sites"),
            _COLUMNS["audio_sites"], on_select=self._on_row_select,
        )
        self._tables["audio_sites"].pack(fill="both", expand=True)

        # Images: single table
        self._tables["image_files"] = ContentTable(
            self._tabview.tab("Images"),
            _COLUMNS["image_files"], on_select=self._on_row_select,
        )
        self._tables["image_files"].pack(fill="both", expand=True)

        # Unsorted: single table
        self._tables["unsorted"] = ContentTable(
            self._tabview.tab("Unsorted"),
            _COLUMNS["unsorted"], on_select=self._on_row_select,
        )
        self._tables["unsorted"].pack(fill="both", expand=True)

        # ── Detail panel ──
        self._detail = ctk.CTkTextbox(
            self._container, height=120,
            font=ctk.CTkFont(family="Consolas", size=11),
            state="disabled",
        )
        self._detail.pack(fill="x")
        self._detail.tag_config("link", foreground="#3B8ED0", underline=True)

        # ── Action buttons row ──
        btn_row = ctk.CTkFrame(self._container, fg_color="transparent")
        btn_row.pack(fill="x", pady=(5, 0))

        self._open_file_btn = ctk.CTkButton(
            btn_row, text="Open File Location", width=140,
            command=self._open_file_or_site, state="disabled",
        )
        self._open_file_btn.pack(side="left", padx=(0, 5))
        _add_focus_ring(self._open_file_btn)
        Tooltip(self._open_file_btn, "Open the folder containing the downloaded file, or open the site URL")

        self._open_source_btn = ctk.CTkButton(
            btn_row, text="Open Source Page", width=140,
            command=self._open_source_page, state="disabled",
        )
        self._open_source_btn.pack(side="left")
        _add_focus_ring(self._open_source_btn)
        Tooltip(self._open_source_btn, "Open the Canvas page where this content was found")

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
        self._course_var.set(names[0])
        self._show_container()
        self._on_course_selected(names[0])

    def clear(self):
        """Reset all tables and detail panel."""
        for table in self._tables.values():
            table.clear()
        self._set_detail("")
        self._selected_row = None
        self._summary_frame.pack_forget()
        self._open_folder_btn.configure(state="disabled")
        self._open_file_btn.configure(state="disabled")
        self._open_source_btn.configure(state="disabled")

    # ── Internal ──

    def _show_placeholder(self, message="Set an output folder on the Run tab to browse course content."):
        self._container.pack_forget()
        self._placeholder.configure(text=message)
        self._placeholder.pack(expand=True)

    def _show_container(self):
        self._placeholder.pack_forget()
        self._container.pack(fill="both", expand=True)

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

    def _on_course_selected(self, choice):
        """Load content JSON for the selected course."""
        folder_path = self._course_folders.get(choice)
        if not folder_path:
            self.clear()
            return

        manifest_dir = os.path.join(folder_path, ".manifest")
        json_files = [f for f in os.listdir(manifest_dir) if f.endswith(".json")]
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

        self._current_data = data
        self._populate_from_data(data)

    def _on_filter_changed(self):
        """Re-populate tables when a filter checkbox changes."""
        if self._current_data:
            self._populate_from_data(self._current_data)

    def _check_downloaded(self, rows):
        """Add a 'downloaded' field to each row based on whether save_path exists."""
        for row in rows:
            save_path = row.get("save_path", "")
            if save_path:
                normalized = os.path.normpath(save_path)
                row["downloaded"] = "Yes" if os.path.isfile(normalized) else "No"
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
                rows = [r for r in rows if r.get("source_page_url")]
            if table_key in downloadable:
                rows = self._check_downloaded(rows)
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
        self._open_file_btn.configure(state="disabled")
        self._open_source_btn.configure(state="disabled")
        self._set_detail("")

    def _on_row_select(self, row):
        """Show selected row details and enable/disable action buttons."""
        self._selected_row = row

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