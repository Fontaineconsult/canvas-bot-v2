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
        self._last_spinner = 0.0  # monotonic time of last rendered spinner frame
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
        runs, self._key = parse_ansi(text, self._key)
        for segment, key in runs:
            if segment:
                wx.CallAfter(self._append, segment, key)

    def _colour_for(self, key):
        if key and key in self._palette:
            return wx.Colour(self._palette[key])
        return self._default

    def _append(self, text, key):
        if not self._ctrl:
            return
        colour = self._colour_for(key)
        try:
            if colour is not None:
                self._ctrl.SetDefaultStyle(wx.TextAttr(colour))
        except Exception:
            pass
        # Collapse \r spinner frames: a chunk containing \r but no \n rewrites
        # the last visible line rather than appending. The engine emits these
        # ~12x/sec; rendering every one reflows/scrolls the control (visible
        # "jitter"), so throttle to a few updates per second — the dropped
        # frames carry no information (just a rotating glyph + timer).
        if "\r" in text and "\n" not in text:
            import time
            now = time.monotonic()
            if now - self._last_spinner < 0.15:
                return
            self._last_spinner = now
            self._replace_last_line(text.rsplit("\r", 1)[-1])
            return
        try:
            self._ctrl.AppendText(text)
        except Exception:
            pass

    def _replace_last_line(self, text):
        try:
            value = self._ctrl.GetValue()
            nl = value.rfind("\n")
            start = nl + 1 if nl >= 0 else 0
            # Freeze during the swap so the control repaints once, not mid-edit
            # (removes the flicker of in-place spinner updates).
            self._ctrl.Freeze()
            try:
                self._ctrl.Replace(start, self._ctrl.GetLastPosition(), text)
            finally:
                self._ctrl.Thaw()
        except Exception:
            try:
                self._ctrl.AppendText(text)
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
