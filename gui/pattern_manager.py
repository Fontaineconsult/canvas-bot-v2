import re
import importlib
import customtkinter as ctk

from config.yaml_io import read_re, write_re, reset_re
from network.cred import load_config_data_from_appdata
from gui.table_widget import ContentTable
from gui.widgets import _add_focus_ring, _underline_char, Tooltip

# Maps re.yaml category keys to GUI display labels.
# Set to None to hide from the GUI. Hidden categories still function in the pipeline.
_CATEGORY_LABELS = {
    "resource_node_re": None,
    "resource_node_types_re": None,
    "document_content_regex": "Documents",
    "ignore_links_regex": "Ignored Links",
    "image_content_regex": "Images",
    "canvas_user_file_content_regex": None,
    "canvas_file_content_regex": None,
    "web_video_resources_regex": "Video Sites",
    "institution_video_services_regex": "Institution Video",
    "canvas_studio_embed": "Canvas Studio",
    "canvas_file_embed": "Canvas File Embeds",
    "canvas_media_embed": "Canvas Media Embeds",
    "video_file_resources_regex": "Video Files",
    "web_audio_resources_regex": "Audio Sites",
    "audio_file_resources_regex": "Audio Files",
    "web_document_applications_regex": "Document Sites",
    "digital_text_book_regex": "Digital Textbooks",
    "file_storage_regex": "File Storage",
    "ignore_list_regex": "Ignore List",
    "force_to_shortcut": "Force to Shortcut",
    "canvas_embed_uuid_regex": "Canvas Embed UUIDs",
}


def _label(category):
    """Return the public display label for a category, or the raw key as fallback."""
    return _CATEGORY_LABELS.get(category) or category


class PatternManager:
    """GUI for viewing, adding, removing, validating, and testing regex patterns from re.yaml."""

    def __init__(self, parent_frame):
        self._parent = parent_frame
        self._patterns_data = {}       # full re.yaml dict (unsubstituted, used for writes)
        self._display_data = {}        # substituted copy (used for GUI display)
        self._selected_category = None
        self._category_buttons = {}    # category_name -> CTkButton
        self._category_order = []      # ordered list of category keys for arrow nav

        # ── Main grid container ──
        self._container = ctk.CTkFrame(parent_frame, fg_color="transparent")
        self._container.pack(fill="both", expand=True)
        self._container.grid_columnconfigure(0, weight=0, minsize=250)
        self._container.grid_columnconfigure(1, weight=1)
        self._container.grid_rowconfigure(0, weight=1)
        self._container.grid_rowconfigure(1, weight=0)

        # ── Left column: category list ──
        left_frame = ctk.CTkFrame(self._container)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 5))

        ctk.CTkLabel(
            left_frame, text="Categories",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        self._category_scroll = ctk.CTkScrollableFrame(left_frame, fg_color="transparent")
        self._category_scroll.pack(fill="both", expand=True, padx=5, pady=(0, 5))

        self._reset_btn = ctk.CTkButton(
            left_frame, text="Reset All to Defaults", width=200,
            fg_color="#b22222", hover_color="#8b0000",
            command=self._on_reset,
        )
        self._reset_btn.pack(pady=(0, 8))
        _add_focus_ring(self._reset_btn)
        _underline_char(self._reset_btn, 1)  # e in "Reset" → Alt+E
        Tooltip(self._reset_btn, "Reset all patterns to the bundled defaults (Alt+E)")

        # ── Right column: pattern display + action buttons ──
        right_frame = ctk.CTkFrame(self._container)
        right_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 5))

        self._category_header = ctk.CTkLabel(
            right_frame, text="Select a category",
            font=ctk.CTkFont(size=14, weight="bold"), anchor="w",
        )
        self._category_header.pack(fill="x", padx=10, pady=(8, 4))

        self._pattern_table = ContentTable(
            right_frame,
            columns=[
                {"id": "index", "heading": "#", "width": 50},
                {"id": "pattern", "heading": "Pattern", "width": 500, "stretch": True},
            ],
            on_select=self._on_pattern_select,
        )
        self._pattern_table.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self._pattern_table._tree.bind("<Escape>", lambda e: self._focus_selected_category())

        # Action buttons row
        btn_row = ctk.CTkFrame(right_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=10, pady=(0, 8))

        self._add_btn = ctk.CTkButton(
            btn_row, text="Add Pattern", width=120,
            command=self._on_add, state="disabled",
        )
        self._add_btn.pack(side="left", padx=(0, 5))
        _add_focus_ring(self._add_btn)
        _underline_char(self._add_btn, 1)  # d in "Add" → Alt+D
        Tooltip(self._add_btn, "Add a new regex pattern to the selected category (Alt+D)")

        self._remove_btn = ctk.CTkButton(
            btn_row, text="Remove Pattern", width=130,
            command=self._on_remove, state="disabled",
        )
        self._remove_btn.pack(side="left", padx=(0, 5))
        _add_focus_ring(self._remove_btn)
        _underline_char(self._remove_btn, 2)  # m in "Remove" → Alt+M
        Tooltip(self._remove_btn, "Remove the selected pattern from this category (Alt+M)")

        self._validate_btn = ctk.CTkButton(
            btn_row, text="Validate", width=100,
            command=self._on_validate, state="disabled",
        )
        self._validate_btn.pack(side="left", padx=(0, 10))
        _add_focus_ring(self._validate_btn)
        _underline_char(self._validate_btn, 2)  # l in "Validate" → Alt+L
        Tooltip(self._validate_btn, "Check if the selected pattern is valid regex syntax (Alt+L)")

        self._status_label = ctk.CTkLabel(
            btn_row, text="", font=ctk.CTkFont(size=12), anchor="w",
        )
        self._status_label.pack(side="left", fill="x", expand=True)

        # ── Bottom row: test URL panel ──
        test_frame = ctk.CTkFrame(self._container)
        test_frame.grid(row=1, column=0, columnspan=2, sticky="ew")

        ctk.CTkLabel(
            test_frame, text="Test URL / Filename",
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(fill="x", padx=10, pady=(8, 4))

        test_row = ctk.CTkFrame(test_frame, fg_color="transparent")
        test_row.pack(fill="x", padx=10, pady=(0, 4))

        self._test_entry = ctk.CTkEntry(
            test_row, placeholder_text="Enter a URL or filename to test...",
        )
        self._test_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self._test_entry.bind("<Return>", lambda e: self._on_test())
        _add_focus_ring(self._test_entry)
        Tooltip(self._test_entry, "Enter a URL or filename to see which pattern categories match it")

        self._test_btn = ctk.CTkButton(
            test_row, text="Test", width=80, command=self._on_test,
        )
        self._test_btn.pack(side="right")
        _add_focus_ring(self._test_btn)
        _underline_char(self._test_btn, 0)  # T → Alt+T
        Tooltip(self._test_btn, "Test the entered URL or filename against all compiled pattern matchers (Alt+T)")

        self._test_result = ctk.CTkLabel(
            test_frame, text="", font=ctk.CTkFont(family="Consolas", size=12), anchor="w",
        )
        self._test_result.pack(fill="x", padx=10, pady=(0, 8))

        # ── Load data ──
        self._load_data()

    # ── Data Loading ──

    def _load_data(self):
        """Load patterns from re.yaml and populate the category list."""
        # Ensure CANVAS_DOMAIN and other env vars are set before substitution
        load_config_data_from_appdata()
        self._patterns_data = read_re(substitute=False)
        self._display_data = read_re(substitute=True)
        self._populate_category_list()

    def _populate_category_list(self):
        """Build category buttons in the left column."""
        # Clear existing buttons
        for widget in self._category_scroll.winfo_children():
            widget.destroy()
        self._category_buttons.clear()
        self._category_order.clear()

        for category, value in self._patterns_data.items():
            if _CATEGORY_LABELS.get(category) is None:
                continue
            is_list = isinstance(value, list)
            count = len(value) if is_list else 1

            btn = ctk.CTkButton(
                self._category_scroll,
                text=f"{_label(category)}  ({count})",
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90") if is_list else ("gray50", "gray60"),
                hover_color=("gray85", "gray25"),
                font=ctk.CTkFont(size=12),
                height=30,
                command=lambda c=category: self._on_category_click(c),
            )
            btn.pack(fill="x", pady=1)
            _add_focus_ring(btn)
            btn.bind("<Up>", lambda e, c=category: self._nav_category(c, -1))
            btn.bind("<Down>", lambda e, c=category: self._nav_category(c, 1))
            btn.bind("<Return>", lambda e, c=category: self._focus_pattern_table(c))
            self._category_buttons[category] = btn
            self._category_order.append(category)

    def _focus_selected_category(self):
        """Return focus from the pattern table to the selected category button."""
        if self._selected_category and self._selected_category in self._category_buttons:
            self._category_buttons[self._selected_category].focus_set()

    def _focus_pattern_table(self, category):
        """Select the category (if not already) and move focus to the pattern table."""
        if self._selected_category != category:
            self._on_category_click(category)
        tree = self._pattern_table._tree
        children = tree.get_children()
        if children:
            tree.selection_set(children[0])
            tree.focus(children[0])
        tree.focus_set()
        return "break"

    def _nav_category(self, current, direction):
        """Navigate to the previous/next category button and select it."""
        try:
            idx = self._category_order.index(current)
        except ValueError:
            return
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self._category_order):
            return
        target = self._category_order[new_idx]
        btn = self._category_buttons[target]
        btn.focus_set()
        self._on_category_click(target)

    # ── Category Selection ──

    def _on_category_click(self, category):
        """Handle clicking a category in the left column."""
        self._selected_category = category
        value = self._patterns_data[category]
        display_value = self._display_data.get(category, value)
        is_list = isinstance(value, list)

        # Highlight selected button
        for name, btn in self._category_buttons.items():
            if name == category:
                btn.configure(fg_color=("gray75", "gray30"), hover_color=("gray70", "gray35"))
            else:
                btn.configure(fg_color="transparent", hover_color=("gray85", "gray25"))

        # Update header
        count = len(value) if is_list else 1
        self._category_header.configure(text=f"{_label(category)}  ({count} pattern{'s' if count != 1 else ''})")

        # Populate pattern table with substituted values for display
        if is_list:
            rows = [{"index": str(i + 1), "pattern": p} for i, p in enumerate(display_value)]
        else:
            rows = [{"index": "1", "pattern": str(display_value)}]
        self._pattern_table.populate(rows)

        # Enable/disable action buttons
        if is_list:
            self._add_btn.configure(state="normal")
        else:
            self._add_btn.configure(state="disabled")
        self._remove_btn.configure(state="disabled")
        self._validate_btn.configure(state="disabled")
        self._status_label.configure(text="")

    def _on_pattern_select(self, row):
        """Handle clicking a pattern in the table."""
        is_list = isinstance(self._patterns_data.get(self._selected_category), list)
        if is_list:
            self._remove_btn.configure(state="normal")
        else:
            self._remove_btn.configure(state="disabled")
        self._validate_btn.configure(state="normal")

    # ── Add Pattern ──

    def _on_add(self):
        """Open a dialog to add a new pattern to the selected category."""
        if not self._selected_category:
            return

        dialog = ctk.CTkToplevel(self._parent)
        dialog.title("Add Pattern")
        dialog.geometry("500x180")
        dialog.resizable(False, False)
        dialog.transient(self._parent.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text=f"Add pattern to: {_label(self._selected_category)}",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(padx=15, pady=(15, 5))

        entry = ctk.CTkEntry(dialog, placeholder_text="Enter regex pattern...")
        entry.pack(fill="x", padx=15, pady=(0, 5))
        entry.focus_set()

        error_label = ctk.CTkLabel(dialog, text="", text_color="red", font=ctk.CTkFont(size=11))
        error_label.pack(fill="x", padx=15)

        def validate_and_add():
            pattern = entry.get().strip()
            if not pattern:
                error_label.configure(text="Pattern cannot be empty.")
                entry.focus_set()
                return

            # Validate regex
            try:
                re.compile(pattern)
            except re.error as e:
                error_label.configure(text=f"Invalid regex: {e}")
                entry.focus_set()
                return

            # Duplicate check
            if pattern in self._patterns_data[self._selected_category]:
                error_label.configure(text="Pattern already exists in this category.")
                entry.focus_set()
                return

            # Add and save
            self._patterns_data[self._selected_category].append(pattern)
            write_re(self._patterns_data)
            self._refresh_after_edit()
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(5, 15))

        add_btn = ctk.CTkButton(btn_row, text="Add", width=80, command=validate_and_add)
        add_btn.pack(side="right", padx=(5, 0))
        _add_focus_ring(add_btn)
        _underline_char(add_btn, 0)  # A
        cancel_btn = ctk.CTkButton(btn_row, text="Cancel", width=80, fg_color="gray40", command=dialog.destroy)
        cancel_btn.pack(side="right")
        _add_focus_ring(cancel_btn)
        _underline_char(cancel_btn, 0)  # C

        entry.bind("<Return>", lambda e: validate_and_add())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    # ── Remove Pattern ──

    def _on_remove(self):
        """Remove the selected pattern after confirmation."""
        if not self._selected_category:
            return

        selected = self._pattern_table.get_selected()
        if not selected:
            return

        pattern = selected["pattern"]

        dialog = ctk.CTkToplevel(self._parent)
        dialog.title("Remove Pattern")
        dialog.geometry("500x150")
        dialog.resizable(False, False)
        dialog.transient(self._parent.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text=f"Remove from: {_label(self._selected_category)}",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(padx=15, pady=(15, 5))

        ctk.CTkLabel(
            dialog, text=pattern,
            font=ctk.CTkFont(family="Consolas", size=12),
        ).pack(padx=15, pady=(0, 10))

        def confirm_remove():
            value = self._patterns_data[self._selected_category]
            if isinstance(value, list) and pattern in value:
                value.remove(pattern)
                write_re(self._patterns_data)
                self._refresh_after_edit()
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))

        remove_btn = ctk.CTkButton(btn_row, text="Remove", width=80,
                       fg_color="#b22222", hover_color="#8b0000", command=confirm_remove)
        remove_btn.pack(side="right", padx=(5, 0))
        _add_focus_ring(remove_btn)
        _underline_char(remove_btn, 0)  # R
        cancel_btn = ctk.CTkButton(btn_row, text="Cancel", width=80, fg_color="gray40", command=dialog.destroy)
        cancel_btn.pack(side="right")
        _add_focus_ring(cancel_btn)
        _underline_char(cancel_btn, 0)  # C
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    # ── Validate ──

    def _on_validate(self):
        """Validate the selected pattern's regex syntax."""
        selected = self._pattern_table.get_selected()
        if not selected:
            return

        pattern = selected["pattern"]
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            self._status_label.configure(
                text=f"Valid regex  |  Groups: {compiled.groups}  |  Flags: IGNORECASE",
                text_color="green",
            )
        except re.error as e:
            self._status_label.configure(text=f"Invalid regex: {e}", text_color="red")

    # ── Test URL ──

    def _on_test(self):
        """Test a URL/filename against all compiled matchers."""
        test_string = self._test_entry.get().strip()
        if not test_string:
            self._test_result.configure(text="Enter a URL or filename to test.", text_color="gray")
            return

        # Reload sorters to pick up any saved edits
        import sorters.sorters
        importlib.reload(sorters.sorters)

        from sorters.sorters import (
            document_content_regex, image_content_regex,
            web_video_content_regex, video_file_content_regex,
            web_audio_content_regex, audio_file_content_regex,
            web_document_applications_regex, file_storage_regex,
            canvas_studio_embed, ignore_list_regex,
        )

        matchers = [
            ("document_content_regex", document_content_regex),
            ("image_content_regex", image_content_regex),
            ("web_video_resources_regex", web_video_content_regex),
            ("video_file_resources_regex", video_file_content_regex),
            ("web_audio_resources_regex", web_audio_content_regex),
            ("audio_file_resources_regex", audio_file_content_regex),
            ("web_document_applications_regex", web_document_applications_regex),
            ("file_storage_regex", file_storage_regex),
            ("canvas_studio_embed", canvas_studio_embed),
            ("ignore_list_regex", ignore_list_regex),
        ]

        matches = [_label(name) for name, regex in matchers if regex.match(test_string)]

        if matches:
            self._test_result.configure(
                text=f"MATCH: {', '.join(matches)}",
                text_color="green",
            )
        else:
            self._test_result.configure(
                text="No matches (would be classified as Unsorted)",
                text_color="orange",
            )

    # ── Reset ──

    def _on_reset(self):
        """Reset patterns to bundled defaults after confirmation."""
        dialog = ctk.CTkToplevel(self._parent)
        dialog.title("Reset Patterns")
        dialog.geometry("450x150")
        dialog.resizable(False, False)
        dialog.transient(self._parent.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog, text="Reset all patterns to defaults?",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(padx=15, pady=(15, 5))

        ctk.CTkLabel(
            dialog, text="Any custom patterns you added will be lost.",
            text_color="gray",
        ).pack(padx=15, pady=(0, 10))

        def confirm_reset():
            reset_re()
            # Reload sorters so the pipeline picks up fresh defaults
            import sorters.sorters
            importlib.reload(sorters.sorters)
            # Reload both copies: unsubstituted for writes, substituted for display
            self._patterns_data = read_re(substitute=False)
            self._display_data = read_re(substitute=True)
            self._populate_category_list()
            self._selected_category = None
            self._pattern_table.clear()
            self._category_header.configure(text="Select a category")
            self._add_btn.configure(state="disabled")
            self._remove_btn.configure(state="disabled")
            self._validate_btn.configure(state="disabled")
            self._status_label.configure(text="Patterns reset to defaults.", text_color="green")
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))

        reset_btn = ctk.CTkButton(btn_row, text="Reset", width=80,
                       fg_color="#b22222", hover_color="#8b0000", command=confirm_reset)
        reset_btn.pack(side="right", padx=(5, 0))
        _add_focus_ring(reset_btn)
        _underline_char(reset_btn, 0)  # R
        cancel_btn = ctk.CTkButton(btn_row, text="Cancel", width=80, fg_color="gray40", command=dialog.destroy)
        cancel_btn.pack(side="right")
        _add_focus_ring(cancel_btn)
        _underline_char(cancel_btn, 0)  # C
        dialog.bind("<Escape>", lambda e: dialog.destroy())

    # ── Helpers ──

    def _refresh_after_edit(self):
        """Refresh both the category list and the pattern table after an add/remove."""
        self._display_data = read_re(substitute=True)
        self._populate_category_list()
        if self._selected_category:
            self._on_category_click(self._selected_category)