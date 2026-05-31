"""Read-only log panel + ANSI-color-aware stdout/stderr redirector (wx).

Replaces the CustomTkinter ``TextRedirector``. The engine prints colored
progress to stdout/stderr during a scan (via colorama, i.e. ANSI SGR escape
codes). We parse those codes and render each run in a real color on a rich
``wx.TextCtrl``, on the UI thread via ``wx.CallAfter``.

Colors are theme-aware and every one is verified at >=7:1 contrast against the
log background (see _ANSI_DARK/_ANSI_LIGHT). Color is purely visual — the text
content appended is unchanged, so screen-reader output is unaffected.

Carriage-return spinner frames (``\r`` without ``\n``) rewrite the current
(last) line instead of appending, so the log doesn't fill with spinner frames.
"""

import re

import wx

# Match a single ANSI SGR sequence, capturing the numeric parameters.
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")

# ANSI foreground code -> palette key. Covers standard (30-37) and bright
# (90-97) foregrounds; backgrounds and styles other than reset are ignored.
_CODE_TO_KEY = {
    30: "gray", 31: "red", 32: "green", 33: "yellow",
    34: "blue", 35: "magenta", 36: "cyan", 37: "white",
    90: "gray", 91: "red", 92: "green", 93: "yellow",
    94: "blue", 95: "magenta", 96: "cyan", 97: "white",
}

# Foreground palettes, verified >=7:1 (mostly >=8:1) on the matching log bg.
_ANSI_DARK = {
    "red": "#FF8A80", "green": "#7CE38B", "yellow": "#FFD24D", "blue": "#6BB4FF",
    "magenta": "#E0A0E0", "cyan": "#6FE0E0", "white": "#F0F0F0", "gray": "#B8B8B8",
}
_ANSI_LIGHT = {
    "red": "#A30016", "green": "#15571A", "yellow": "#6E4700", "blue": "#00407F",
    "magenta": "#7A157A", "cyan": "#005C5C", "white": "#1A1A1A", "gray": "#4D4D4D",
}


def ansi_palette(dark):
    """Return the {key: hex} ANSI foreground palette for the given mode."""
    return dict(_ANSI_DARK if dark else _ANSI_LIGHT)


def parse_ansi(text, start_key):
    """Split *text* into colored runs.

    Returns (runs, end_key) where runs is a list of (segment, key_or_None) and
    end_key is the active color key after the text (so color can span writes).
    A reset (code 0, or an empty ``\x1b[m``) sets key back to None (= default
    foreground). Codes we don't map are ignored, preserving the current key.
    """
    runs = []
    key = start_key
    pos = 0
    for m in _SGR_RE.finditer(text):
        if m.start() > pos:
            runs.append((text[pos:m.start()], key))
        params = m.group(1)
        codes = [int(p) for p in params.split(";") if p != ""] or [0]
        for code in codes:
            if code == 0:
                key = None
            elif code in _CODE_TO_KEY:
                key = _CODE_TO_KEY[code]
            # other codes (bold=1, bg colors, etc.) are ignored
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], key))
    return runs, key


class LogRedirector:
    """File-like object that appends colored writes to a wx.TextCtrl.

    Pass the original stream so output is still echoed there (useful when
    launched from a console). Install by assigning to sys.stdout/sys.stderr;
    restore the originals when the scan finishes.
    """

    def __init__(self, text_ctrl, original=None, palette=None, default_colour=None):
        self._ctrl = text_ctrl
        self._original = original
        self._palette = palette or {}
        self._default = default_colour
        self._key = None  # active ANSI color key across writes
        # Spinner coalescing: the latest \r-frame's runs, and whether a flush
        # is already queued. Multiple frames arriving before the flush runs
        # collapse to the last one (clear + content within a tick -> content).
        self._pending_spinner = None
        self._spinner_flush_queued = False
        # Mimic a real text stream: some code (e.g. tools/canvas_tree.py) probes
        # sys.stdout.encoding to decide whether it can emit unicode.
        self.encoding = getattr(original, "encoding", None) or "utf-8"

    def isatty(self):
        return False

    def write(self, text):
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass

        # A chunk that carries \r but no \n is an in-place "spinner" frame
        # (e.g. "\r<spinner> Resource [time]"). It must be handled as ONE unit:
        # the frame is colorama-colored, so parsing it yields several runs and
        # only the first carries the \r. Dispatching runs individually let the
        # \r run rewrite the line while the rest appended after it — the
        # duplicated, flickering copy. Instead, take the content after the last
        # \r as the new line and coalesce: store it and queue a single flush.
        # Successive frames (and the clear+content pair the engine emits each
        # tick) collapse to the latest, so we repaint the line ~once per event
        # loop pass instead of per write — no jitter, no duplication.
        if "\r" in text and "\n" not in text:
            frame = text.rsplit("\r", 1)[-1]
            self._pending_spinner, _ = parse_ansi(frame, None)
            if not self._spinner_flush_queued:
                self._spinner_flush_queued = True
                wx.CallAfter(self._flush_spinner)
            return

        # Normal text: parse with persistent color state, append each run.
        # (Any pending spinner flush was queued earlier, so FIFO ordering means
        # it settles the spinner line before these appends.)
        runs, self._key = parse_ansi(text, self._key)
        for segment, key in runs:
            if segment:
                wx.CallAfter(self._append, segment, key)

    def _flush_spinner(self):
        self._spinner_flush_queued = False
        runs = self._pending_spinner
        self._pending_spinner = None
        if runs is None:
            return
        # runs may be empty (a pure "\r   \r" clear) -> clears the line.
        self._rewrite_line(runs)

    def _colour_for(self, key):
        if key and key in self._palette:
            return wx.Colour(self._palette[key])
        return self._default

    def _set_colour(self, key):
        try:
            colour = self._colour_for(key)
            if colour is not None:
                self._ctrl.SetDefaultStyle(wx.TextAttr(colour))
        except Exception:
            pass

    def _append(self, text, key):
        if not self._ctrl:
            return
        self._set_colour(key)
        try:
            self._ctrl.AppendText(text)
        except Exception:
            pass

    def _rewrite_line(self, runs):
        """Replace the current (last) line with the given colored runs, atomic."""
        if not self._ctrl:
            return
        try:
            value = self._ctrl.GetValue()
            nl = value.rfind("\n")
            start = nl + 1 if nl >= 0 else 0
            self._ctrl.Freeze()
            try:
                self._ctrl.Remove(start, self._ctrl.GetLastPosition())
                for seg, key in runs:
                    if not seg:
                        continue
                    self._set_colour(key)
                    self._ctrl.AppendText(seg)
            finally:
                self._ctrl.Thaw()
        except Exception:
            pass

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass


def make_log_ctrl(parent, name="Output log", theme=None):
    """Create the read-only multiline rich TextCtrl used as the log view.

    When *theme* is given (and active), the control's background/foreground are
    set from the palette so the ANSI colors render on the intended background.
    """
    ctrl = wx.TextCtrl(
        parent,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.HSCROLL,
    )
    try:
        ctrl.SetName(name)
        font = wx.Font(wx.FontInfo(10).FaceName("Consolas"))
        ctrl.SetFont(font)
    except Exception:
        pass
    if theme is not None and getattr(theme, "active", True):
        try:
            ctrl.SetBackgroundColour(theme.color("window_bg"))
            ctrl.SetForegroundColour(theme.color("text"))
        except Exception:
            pass
    return ctrl
