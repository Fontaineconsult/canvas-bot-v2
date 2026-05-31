"""Read-only log panel + ANSI-color-aware stdout/stderr redirector (wx).

The engine prints colored progress to stdout/stderr during a scan (colorama /
ANSI SGR codes), plus an animation thread that emits a spinner ~12x/sec. On a
large course that is *thousands* of writes in quick succession.

PERFORMANCE / LOCKUP:
The redirector must never touch wx from the worker/animation threads, and must
never do per-write UI work — doing a wx.CallAfter per write floods the UI
event queue and freezes the app ("Not Responding"). Instead:
  * write() (any thread) only appends to an in-memory buffer under a lock —
    no wx calls at all.
  * A wx.Timer on the UI thread calls drain() ~10x/sec, which applies ALL
    buffered text in one batched, frozen update.
  * The current-line position is tracked locally, so we never call GetValue()
    (which would copy the whole growing log on every spinner frame).

Carriage returns (\r) rewrite the current line in place (the spinner); newlines
commit it. Colors are theme-aware, verified >=7:1 on the log background, and the
appended text content is unchanged so screen-reader output is unaffected.
"""

import re
import threading

import wx

# One ANSI SGR escape (e.g. "\x1b[33m").
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")

# ANSI foreground code -> palette key (standard 30-37 + bright 90-97).
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
    end_key is the active color key after the text (so color spans writes). A
    reset (code 0 / empty ``\x1b[m``) sets key to None (default foreground).
    Unmapped codes are ignored, preserving the current key.
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
        pos = m.end()
    if pos < len(text):
        runs.append((text[pos:], key))
    return runs, key


class LogRedirector:
    """Buffering, file-like stdout/stderr sink for the log TextCtrl.

    write() is thread-safe and does no UI work. The owning panel drives drain()
    from a wx.Timer on the UI thread to apply buffered output in batches.
    """

    def __init__(self, text_ctrl, original=None, palette=None, default_colour=None):
        self._ctrl = text_ctrl
        self._original = original
        self._palette = palette or {}
        self._default = default_colour
        self._key = None                  # active ANSI color key across drains
        self._buf = []                    # pending raw text (worker threads append)
        self._lock = threading.Lock()
        self._line_len = 0                # chars on the current unterminated line
        self._rewrite_current = False     # a \r needs to clear the control's tail
        # Mimic a real text stream: tools/canvas_tree.py probes .encoding.
        self.encoding = getattr(original, "encoding", None) or "utf-8"

    # ── file protocol (called from any thread) ──

    def isatty(self):
        return False

    def write(self, text):
        if not text:
            return
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass
        with self._lock:
            self._buf.append(text)

    def flush(self):
        if self._original is not None:
            try:
                self._original.flush()
            except Exception:
                pass

    # ── UI-thread batched apply (called from the panel's timer) ──

    def drain(self):
        """Apply all buffered text to the control in one frozen batch.

        Must run on the UI thread. Cheap when the buffer is empty.
        """
        if self._ctrl is None:
            return
        with self._lock:
            if not self._buf:
                return
            chunk = "".join(self._buf)
            self._buf.clear()

        runs, self._key = parse_ansi(chunk, self._key)
        try:
            self._ctrl.Freeze()
            try:
                for seg, key in runs:
                    if not seg:
                        continue
                    self._set_colour(key)
                    self._emit(seg)
            finally:
                self._ctrl.Thaw()
        except Exception:
            pass

    def _emit(self, seg):
        """Append a colored segment, honoring embedded \r (rewrite) and \n."""
        for tok in _BREAK_RE.split(seg):
            if tok == "":
                continue
            if tok in ("\n", "\r\n"):
                self._ctrl.AppendText("\n")
                self._line_start = self._ctrl.GetLastPosition()
            elif tok == "\r":
                # Carriage return: clear the current (unterminated) line so the
                # next text overwrites it (spinner frames). Remove on a short
                # current line is cheap — no GetValue of the whole control.
                end = self._ctrl.GetLastPosition()
                if end > self._line_start:
                    self._ctrl.Remove(self._line_start, end)
            else:
                self._ctrl.AppendText(tok)

    def _set_colour(self, key):
        try:
            colour = self._palette.get(key) if key else None
            self._ctrl.SetDefaultStyle(
                wx.TextAttr(wx.Colour(colour) if colour else (self._default or wx.NullColour))
            )
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
        ctrl.SetFont(wx.Font(wx.FontInfo(10).FaceName("Consolas")))
    except Exception:
        pass
    if theme is not None and getattr(theme, "active", True):
        try:
            ctrl.SetBackgroundColour(theme.color("window_bg"))
            ctrl.SetForegroundColour(theme.color("text"))
        except Exception:
            pass
    return ctrl
