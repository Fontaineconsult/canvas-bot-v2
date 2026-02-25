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

    def __init__(self, parent, columns, on_select=None, placeholder="", **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._columns = columns
        self._on_select = on_select
        self._sort_col = None
        self._sort_asc = True
        self._rows = []  # mirrors treeview content as list[dict]

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
                minwidth=50,
            )

        # Scrollbars
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=self._vsb.set, xscrollcommand=self._hsb.set)

        # Grid layout
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")
        self._hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Selection binding
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    # ── Public API ──

    def populate(self, rows):
        """Clear the table and insert *rows* (list of dicts keyed by column id)."""
        self.clear()
        self._rows = list(rows)
        if not self._rows and self._placeholder.cget("text"):
            self._tree.grid_remove()
            self._vsb.grid_remove()
            self._hsb.grid_remove()
            self._placeholder.grid(row=0, column=0, sticky="nsew")
        else:
            self._placeholder.grid_remove()
            self._tree.grid()
            self._vsb.grid()
            self._hsb.grid()
            for i, row in enumerate(self._rows):
                values = [row.get(c["id"], "") for c in self._columns]
                tag = "odd" if i % 2 else "even"
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

    def get_row_count(self):
        """Return the number of rows currently displayed."""
        return len(self._rows)

    # ── Sorting ──

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

        # Sort rows
        self._rows.sort(key=lambda r: str(r.get(col_id, "")).lower(), reverse=not self._sort_asc)
        # Re-populate without clearing _rows
        self._tree.delete(*self._tree.get_children())
        for i, row in enumerate(self._rows):
            values = [row.get(c["id"], "") for c in self._columns]
            tag = "odd" if i % 2 else "even"
            self._tree.insert("", "end", iid=str(i), values=values, tags=(tag,))
        self._apply_row_tags()

    # ── Selection ──

    def _on_tree_select(self, event=None):
        if self._on_select:
            row = self.get_selected()
            if row is not None:
                self._on_select(row)

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
            relief="flat",
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

        # Tag colors for alternating rows
        self._tag_colors = t

    def _apply_row_tags(self):
        t = self._tag_colors
        self._tree.tag_configure("even", background=t["bg"])
        self._tree.tag_configure("odd", background=t["row_alt"])