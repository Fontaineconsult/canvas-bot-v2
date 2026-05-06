import tkinter as tk
from tkinter import ttk
import customtkinter as ctk


# Theme colors for light and dark modes
_THEMES = {
    "dark": {
        "bg": "#2b2b2b",
        "fg": "#dce4ee",
        "heading_bg": "#333333",
        "heading_fg": "#dce4ee",
        "selected_bg": "#1f6aa5",
        "selected_fg": "#ffffff",
        "row_alt": "#323232",
        "border": "#3e3e3e",
        "field_bg": "#343638",
    },
    "light": {
        "bg": "#ffffff",
        "fg": "#1a1a1a",
        "heading_bg": "#e8e8e8",
        "heading_fg": "#1a1a1a",
        "selected_bg": "#3B8ED0",
        "selected_fg": "#ffffff",
        "row_alt": "#f5f5f5",
        "border": "#cccccc",
        "field_bg": "#f9f9f9",
    },
}

# Row background colors keyed by status (review or bulk-replace).
# Bulk-replace status values are name-spaced enough that they don't collide
# with the existing review statuses (Passed / Needs Review / Ignore).
_STATUS_COLORS = {
    "dark": {
        "Passed": "#1a3a1a",
        "Needs Review": "#3a2a0a",
        "Ignore": "#2a2a2a",
        # Bulk replace dialog statuses
        "Will replace":     "#1a3a1a",  # green
        "Replacing…":       "#3a2a0a",  # amber (in flight)
        "Done":             "#1a3a1a",  # green
        "Failed":           "#4a1a1a",  # red
        "Skipped":          "#2a2a2a",  # gray
        "No match":         "#2a2a2a",  # gray
        "Already replaced": "#2a2a2a",  # gray
        "Ambiguous":        "#2a2a2a",  # gray
        "Ignored":          "#2a2a2a",  # gray (matches existing Ignore swatch)
        "User File":        "#2a2a2a",  # gray (lives in user storage — can't be replaced via course endpoint)
        "Group File":       "#2a2a2a",  # gray (lives in group storage — can't be replaced via course endpoint)
    },
    "light": {
        "Passed": "#d4edda",
        "Needs Review": "#fff3cd",
        "Ignore": "#e2e3e5",
        # Bulk replace dialog statuses
        "Will replace":     "#d4edda",  # green
        "Replacing…":       "#fff3cd",  # amber (in flight)
        "Done":             "#d4edda",  # green
        "Failed":           "#f8d7da",  # red
        "Skipped":          "#e2e3e5",  # gray
        "No match":         "#e2e3e5",  # gray
        "Already replaced": "#e2e3e5",  # gray
        "Ambiguous":        "#e2e3e5",  # gray
        "Ignored":          "#e2e3e5",  # gray
        "User File":        "#e2e3e5",  # gray
        "Group File":       "#e2e3e5",  # gray
    },
}


class ContentTable(ctk.CTkFrame):
    """Reusable table widget wrapping ttk.Treeview with scrollbars, sorting, and CTk theming.

    Parameters
    ----------
    parent : widget
        Parent widget.
    columns : list[dict]
        Each dict has keys: id (str), heading (str), width (int), stretch (bool, default False).
    on_select : callable or None
        Called with the selected row dict when a row is clicked.
    """

    def __init__(self, parent, columns, on_select=None, placeholder="", status_key=None, color_key=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._columns = columns
        self._on_select = on_select
        self._sort_col = None
        self._sort_asc = True
        self._rows = []  # mirrors treeview content as list[dict]
        self._status_key = status_key  # row field shown in a column AND used for color
        self._color_key = color_key    # optional separate field used ONLY for color
                                        # (lets display text vary per-row while the
                                        # tag stays stable, e.g. live upload progress)

        # Placeholder shown when table is empty
        self._placeholder = ctk.CTkLabel(
            self, text=placeholder,
            font=ctk.CTkFont(size=14), text_color="gray",
        )

        col_ids = [c["id"] for c in columns]

        # Apply themed style
        self._style = ttk.Style()
        self._apply_theme()

        # Treeview
        self._tree = ttk.Treeview(
            self,
            columns=col_ids,
            show="headings",
            selectmode="browse",
            style="Content.Treeview",
        )

        for col in columns:
            self._tree.heading(
                col["id"],
                text=col["heading"],
                command=lambda c=col["id"]: self._on_heading_click(c),
            )
            self._tree.column(
                col["id"],
                width=col.get("width", 90),
                stretch=col.get("stretch", False),
                anchor=col.get("anchor", "w"),
                minwidth=col.get("minwidth", 50),
            )

        # Scrollbar
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=self._vsb.set)

        # Grid layout
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Proportional column resizing
        self._proportional_cols = {
            c["id"]: c["proportion"] for c in columns if "proportion" in c
        }
        if self._proportional_cols:
            self._tree.bind("<Configure>", self._on_resize)

        # Selection binding
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        # Right-click context menu
        self._ctx_menu = tk.Menu(self._tree, tearoff=0, font=("Segoe UI", 14))
        self._tree.bind("<Button-3>", self._on_right_click)

    # ── Public API ──

    def populate(self, rows):
        """Clear the table and insert *rows* (list of dicts keyed by column id).

        Preserves the active sort column + direction so user-applied sorts survive
        data refreshes (filter toggles, replace operations, course reload).
        """
        self.clear()
        self._rows = list(rows)
        self._sort_rows_in_place()
        if not self._rows and self._placeholder.cget("text"):
            self._tree.grid_remove()
            self._vsb.grid_remove()
            self._placeholder.grid(row=0, column=0, sticky="nsew")
        else:
            self._placeholder.grid_remove()
            self._tree.grid()
            self._vsb.grid()
            for i, row in enumerate(self._rows):
                values = self._values_for_row(row)
                tag = self._row_tag(i, row)
                self._tree.insert("", "end", iid=str(i), values=values, tags=(tag,))
            self._apply_row_tags()

    def clear(self):
        """Remove all rows."""
        self._tree.delete(*self._tree.get_children())
        self._rows.clear()

    def get_selected(self):
        """Return the selected row as a dict, or None."""
        sel = self._tree.selection()
        if not sel:
            return None
        idx = int(sel[0])
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def get_selected_index(self):
        """Return the index of the selected row, or -1."""
        sel = self._tree.selection()
        if not sel:
            return -1
        return int(sel[0])

    def get_row_count(self):
        """Return the number of rows currently displayed."""
        return len(self._rows)

    def get_row(self, idx):
        """Return the row dict at idx, or None if out of range."""
        if 0 <= idx < len(self._rows):
            return self._rows[idx]
        return None

    def update_row(self, idx, row):
        """Update a single row's data and displayed values in place."""
        if 0 <= idx < len(self._rows):
            self._rows[idx] = row
            values = self._values_for_row(row)
            tag = self._row_tag(idx, row)
            self._tree.item(str(idx), values=values, tags=(tag,))

    # ── Display helpers ──

    def _display_value(self, col, value):
        """Truncate value if the column has a max_chars setting."""
        max_chars = col.get("max_chars")
        if max_chars and isinstance(value, str) and len(value) > max_chars:
            return value[:max_chars - 2] + ".."
        return value

    def _values_for_row(self, row):
        """Build the display values tuple for a row, applying truncation."""
        return [self._display_value(c, row.get(c["id"], "")) for c in self._columns]

    def _on_resize(self, event=None):
        """Resize proportional columns to their fraction of the treeview width."""
        total_width = self._tree.winfo_width()
        if total_width < 50:
            return
        for col_id, proportion in self._proportional_cols.items():
            self._tree.column(col_id, width=int(total_width * proportion))

    # ── Sorting ──

    def _sort_rows_in_place(self):
        """Sort self._rows by the current sort column/direction (numeric-aware).

        No-op when no column has been clicked yet. Used by both heading-click
        and populate() so the active sort survives data refreshes.
        """
        if not self._sort_col:
            return
        col_id = self._sort_col

        def _sort_key(r):
            val = r.get(col_id, "")
            s = str(val)
            if s.isdigit():
                return (0, int(s), "")
            return (1, 0, s.lower())

        self._rows.sort(key=_sort_key, reverse=not self._sort_asc)

    def _on_heading_click(self, col_id):
        if self._sort_col == col_id:
            self._sort_asc = not self._sort_asc
        else:
            self._sort_col = col_id
            self._sort_asc = True

        # Update heading indicators
        for col in self._columns:
            suffix = ""
            if col["id"] == self._sort_col:
                suffix = " \u25b2" if self._sort_asc else " \u25bc"
            self._tree.heading(col["id"], text=col["heading"] + suffix)

        self._sort_rows_in_place()
        # Re-render without clearing _rows
        self._tree.delete(*self._tree.get_children())
        for i, row in enumerate(self._rows):
            values = self._values_for_row(row)
            tag = self._row_tag(i, row)
            self._tree.insert("", "end", iid=str(i), values=values, tags=(tag,))
        self._apply_row_tags()

    # ── Selection ──

    def _on_tree_select(self, event=None):
        if self._on_select:
            row = self.get_selected()
            if row is not None:
                self._on_select(row)

    def _on_right_click(self, event):
        """Show context menu with Copy option for the clicked cell."""
        iid = self._tree.identify_row(event.y)
        if not iid:
            return
        self._tree.selection_set(iid)
        self._tree.focus(iid)

        # Identify which column was clicked
        col_id = self._tree.identify_column(event.x)  # e.g. "#1", "#2"
        if not col_id:
            return
        col_idx = int(col_id.replace("#", "")) - 1
        if col_idx < 0 or col_idx >= len(self._columns):
            return

        col = self._columns[col_idx]
        idx = int(iid)
        if idx < 0 or idx >= len(self._rows):
            return

        value = str(self._rows[idx].get(col["id"], ""))
        if not value:
            return

        menu = self._ctx_menu
        menu.delete(0, "end")
        menu.add_command(
            label=f'Copy {col["heading"]}',
            command=lambda: self._copy_to_clipboard(value),
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)

    # ── Theming ──

    def _apply_theme(self):
        mode = ctk.get_appearance_mode().lower()
        t = _THEMES.get(mode, _THEMES["dark"])

        self._style.theme_use("default")
        self._style.configure(
            "Content.Treeview",
            background=t["bg"],
            foreground=t["fg"],
            fieldbackground=t["field_bg"],
            borderwidth=0,
            font=("Consolas", 16),
            rowheight=32,
        )
        self._style.configure(
            "Content.Treeview.Heading",
            background=t["heading_bg"],
            foreground=t["heading_fg"],
            font=("Segoe UI", 16, "bold"),
            borderwidth=1,
            relief="groove",
            bordercolor=t["border"],
        )
        self._style.map(
            "Content.Treeview",
            background=[("selected", t["selected_bg"])],
            foreground=[("selected", t["selected_fg"])],
        )
        self._style.map(
            "Content.Treeview.Heading",
            background=[("active", t["heading_bg"])],
        )

        # Wider scrollbars for easier grabbing
        self._style.configure("Vertical.TScrollbar", width=24, arrowsize=24)

        # Tag colors for alternating rows
        self._tag_colors = t

    def _row_tag(self, idx, row):
        """Return the tag name for a row based on status or alternating index."""
        # color_key (if set) takes priority — lets the displayed status_key
        # text vary (e.g. dynamic upload progress) while the tag stays stable.
        if self._color_key:
            color = row.get(self._color_key, "")
            if color in _STATUS_COLORS.get("dark", {}):
                return f"status_{color}"
        if self._status_key:
            status = row.get(self._status_key, "")
            if status in _STATUS_COLORS.get("dark", {}):
                return f"status_{status}"
        return "odd" if idx % 2 else "even"

    def _apply_row_tags(self):
        t = self._tag_colors
        self._tree.tag_configure("even", background=t["bg"])
        self._tree.tag_configure("odd", background=t["row_alt"])
        # Status-based row colors
        if self._status_key:
            mode = ctk.get_appearance_mode().lower()
            colors = _STATUS_COLORS.get(mode, _STATUS_COLORS["dark"])
            for status, bg in colors.items():
                self._tree.tag_configure(f"status_{status}", background=bg)