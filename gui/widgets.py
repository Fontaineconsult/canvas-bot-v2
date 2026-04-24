import os
import re
import sys
import customtkinter as ctk

_ANSI_PARSE_RE = re.compile(r'\x1b\[([0-9;]*)m')

# ANSI code → (tag_name, dark_color, light_color)
_ANSI_COLORS = {
    "30": ("ansi_black",    "#000000", "#000000"),
    "31": ("ansi_red",      "#cc0000", "#a40000"),
    "32": ("ansi_green",    "#4e9a06", "#2e7d06"),
    "33": ("ansi_yellow",   "#c4a000", "#8a7000"),
    "34": ("ansi_blue",     "#3465a4", "#204a87"),
    "35": ("ansi_magenta",  "#75507b", "#5c3566"),
    "36": ("ansi_cyan",     "#06989a", "#04757a"),
    "37": ("ansi_white",    "#d3d7cf", "#555753"),
    "90": ("ansi_gray",     "#555753", "#888a85"),
    "91": ("ansi_lred",     "#ef2929", "#cc0000"),
    "92": ("ansi_lgreen",   "#8ae234", "#4e9a06"),
    "93": ("ansi_lyellow",  "#fce94f", "#c4a000"),
    "94": ("ansi_lblue",    "#729fcf", "#3465a4"),
    "95": ("ansi_lmagenta", "#ad7fa8", "#75507b"),
    "96": ("ansi_lcyan",    "#34e2e2", "#06989a"),
    "97": ("ansi_lwhite",   "#eeeeec", "#2e3436"),
}


def setup_ansi_tags(text_widget):
    """Configure color tags on a CTkTextbox for ANSI color rendering."""
    mode = ctk.get_appearance_mode().lower()
    idx = 1 if mode == "dark" else 2
    for code, entry in _ANSI_COLORS.items():
        text_widget.tag_config(entry[0], foreground=entry[idx])


_FOCUS_COLOR = "#3B8ED0"  # CustomTkinter default blue
_UNFOCUS_COLOR = ("gray75", "gray25")  # Subtle border that blends with background


def _fix_tcl_paths():
    """Set TCL/TK library paths for venvs where they aren't auto-discovered."""
    if os.environ.get('TCL_LIBRARY'):
        return
    candidates = [
        sys.base_prefix,
        os.path.dirname(getattr(sys, '_base_executable', '')),
        os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Python', 'Python312'),
    ]
    for base in candidates:
        tcl_dir = os.path.join(base, 'tcl', 'tcl8.6')
        tk_dir = os.path.join(base, 'tcl', 'tk8.6')
        if os.path.isdir(tcl_dir):
            os.environ['TCL_LIBRARY'] = tcl_dir
            os.environ['TK_LIBRARY'] = tk_dir
            return


def _underline_char(button, index):
    """Underline a character in a CTkButton label via the internal tkinter Label.

    Falls back silently if the internal structure changes in a future CTk version.
    """
    try:
        button._text_label.configure(underline=index)
    except (AttributeError, Exception):
        pass


def _add_focus_ring(widget):
    """Add a visible border when the widget receives keyboard focus, and activate on Enter."""
    widget.configure(border_width=2, border_color=_UNFOCUS_COLOR)
    widget.bind("<FocusIn>", lambda e: widget.configure(border_color=_FOCUS_COLOR))
    widget.bind("<FocusOut>", lambda e: widget.configure(border_color=_UNFOCUS_COLOR))
    if hasattr(widget, 'invoke'):
        widget.bind("<Return>", lambda e: widget.invoke())
    elif hasattr(widget, 'toggle'):
        widget.bind("<Return>", lambda e: widget.toggle())
    elif hasattr(widget, '_command'):
        widget.bind("<Return>", lambda e: widget._command() if widget._command else None)


class Tooltip:
    """Accessible tooltip that appears on hover and focus."""

    def __init__(self, widget, text, delay=3000):
        self.widget = widget
        self.text = text
        self.delay = delay
        self._tip = None
        self._after_id = None
        widget.bind("<Enter>", self._schedule)
        widget.bind("<Leave>", self._hide)
        widget.bind("<FocusIn>", self._schedule)
        widget.bind("<FocusOut>", self._hide)

    def _schedule(self, event=None):
        self._cancel()
        self._after_id = self.widget.after(self.delay, self._show)

    def _cancel(self):
        if self._after_id:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self, event=None):
        self._after_id = None
        if self._tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self._tip = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes("-topmost", True)
        tw.configure(fg_color="white")
        container = ctk.CTkFrame(tw, fg_color="white", corner_radius=8, border_width=1, border_color="gray70")
        container.pack(fill="both", expand=True)
        ctk.CTkLabel(
            container, text=self.text,
            font=ctk.CTkFont(size=12),
            text_color="gray15",
            fg_color="white",
        ).pack(padx=10, pady=6)

    def _hide(self, event=None):
        self._cancel()
        if self._tip:
            self._tip.destroy()
            self._tip = None


def show_dialog(parent, title, message, dialog_type="info", on_confirm=None):
    """Show a CTk-styled dialog. Returns True/False for confirm dialogs.

    dialog_type: "info", "warning", "error", "confirm"
    on_confirm: callback for confirm dialog (called if user clicks Yes)
    """
    result = [False]

    dialog = ctk.CTkToplevel(parent)
    dialog.withdraw()
    dialog.title(title)
    dialog.resizable(False, False)

    # Icon/color per type
    colors = {
        "info":    {"fg": "#2d6a2d", "label": ""},
        "warning": {"fg": "#8a6d00", "label": ""},
        "error":   {"fg": "#b22222", "label": ""},
        "confirm": {"fg": "#3B8ED0", "label": ""},
    }
    style = colors.get(dialog_type, colors["info"])

    # Message
    msg_label = ctk.CTkLabel(
        dialog, text=message, font=ctk.CTkFont(size=13),
        wraplength=380, justify="left",
    )
    msg_label.pack(padx=18, pady=(12, 6), anchor="w")

    # Buttons
    btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
    btn_row.pack(fill="x", padx=18, pady=(0, 10))

    if dialog_type == "confirm":
        def _yes():
            result[0] = True
            dialog.destroy()
            if on_confirm:
                on_confirm()

        no_btn = ctk.CTkButton(btn_row, text="No", width=80, fg_color="gray40",
                               hover_color="gray30", command=dialog.destroy)
        no_btn.pack(side="right", padx=(5, 0))
        _add_focus_ring(no_btn)
        yes_btn = ctk.CTkButton(btn_row, text="Yes", width=80,
                                fg_color=style["fg"], command=_yes)
        yes_btn.pack(side="right")
        _add_focus_ring(yes_btn)
        yes_btn.focus_set()
    else:
        ok_btn = ctk.CTkButton(btn_row, text="OK", width=80,
                               fg_color=style["fg"], command=dialog.destroy)
        ok_btn.pack(side="right")
        _add_focus_ring(ok_btn)
        ok_btn.focus_set()

    dialog.bind("<Escape>", lambda e: dialog.destroy())
    dialog.bind("<Return>", lambda e: (result.__setitem__(0, True), dialog.destroy()) if dialog_type == "confirm" else (None, dialog.destroy()))

    # Size the dialog deterministically — CTkToplevel's reqheight doesn't reflect packed content
    line_count = message.count('\n') + 1
    w = 380
    h = 12 + (line_count * 20) + 6 + 34 + 10  # top pad + lines + mid pad + button row + bottom pad
    dialog.geometry(f"{w}x{h}")

    dialog.deiconify()
    dialog.transient(parent.winfo_toplevel())
    dialog.grab_set()

    dialog.wait_window()
    return result[0]


class TextRedirector:
    """Captures stdout/stderr writes and routes them to the GUI log textbox."""

    def __init__(self, text_widget, root, original_stream):
        self.text_widget = text_widget
        self.root = root
        self.original = original_stream
        self.encoding = getattr(original_stream, 'encoding', 'utf-8')
        self._current_tag = None
        setup_ansi_tags(text_widget)

    def write(self, text):
        if self.original:
            self.original.write(text)
        if text:
            self.root.after(0, self._append, text)

    def _insert_segment(self, segment):
        """Insert a plain-text segment using the current ANSI color tag."""
        if not segment:
            return
        tag = (self._current_tag,) if self._current_tag else ()
        self.text_widget.insert("end", segment, tag)

    def _append(self, text):
        self.text_widget.configure(state="normal")
        # Handle \r — replace the current line (used by spinner animations)
        if '\r' in text:
            cr_parts = text.split('\r')
            for i, cr_part in enumerate(cr_parts):
                if i > 0:
                    self.text_widget.delete("end-1c linestart", "end-1c lineend")
                self._insert_ansi(cr_part)
        else:
            self._insert_ansi(text)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def _insert_ansi(self, text):
        """Parse ANSI escape sequences and insert text with color tags."""
        parts = _ANSI_PARSE_RE.split(text)
        for i, part in enumerate(parts):
            if i % 2 == 0:
                self._insert_segment(part)
            else:
                if part == "0" or part == "":
                    self._current_tag = None
                else:
                    entry = _ANSI_COLORS.get(part)
                    if entry:
                        self._current_tag = entry[0]

    def flush(self):
        if self.original:
            self.original.flush()
