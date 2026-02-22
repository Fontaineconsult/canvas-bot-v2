import os
import re
import sys
import customtkinter as ctk

_ANSI_RE = re.compile(r'\x1b\[[0-9;]*m')

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


class TextRedirector:
    """Captures stdout/stderr writes and routes them to the GUI log textbox."""

    def __init__(self, text_widget, root, original_stream):
        self.text_widget = text_widget
        self.root = root
        self.original = original_stream
        self.encoding = getattr(original_stream, 'encoding', 'utf-8')

    def write(self, text):
        if self.original:
            self.original.write(text)
        if text:
            self.root.after(0, self._append, text)

    def _append(self, text):
        text = _ANSI_RE.sub('', text)
        if not text:
            return
        self.text_widget.configure(state="normal")
        # Handle \r — replace the current line (used by spinner animations)
        if '\r' in text:
            parts = text.split('\r')
            for i, part in enumerate(parts):
                if i > 0:
                    self.text_widget.delete("end-1c linestart", "end-1c lineend")
                if part:
                    self.text_widget.insert("end", part)
        else:
            self.text_widget.insert("end", text)
        self.text_widget.see("end")
        self.text_widget.configure(state="disabled")

    def flush(self):
        if self.original:
            self.original.flush()
