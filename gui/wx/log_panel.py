"""Read-only log panel + ANSI-color-aware stdout/stderr redirector (wx).

The engine prints colored progress to stdout/stderr during a scan (colorama /
ANSI SGR codes), plus an animation thread that emits a spinner ~12x/sec. On a
large course that is *thousands* of writes in quick succession.

PERFORMANCE / LOCKUP:
The redirector must never touch wx from the worker/animation threads, and must
never do per-write UI work — a wx.CallAfter per write floods the UI event queue
and freezes the app ("Not Responding"). Instead:
  * write() (any thread) only appends to an in-memory buffer under a lock —
    no wx calls at all.
  * A wx.Timer on the UI thread calls drain() ~10x/sec, which applies ALL
    buffered text in one batched, frozen update.

drain() must also be cheap per call even when a backlog accumulates:
  * Carriage-return (\r) spinner rewrites are resolved in PURE PYTHON first
    (no wx per spinner frame).
  * Text is applied with the minimum number of AppendText calls (one per color
    run; newlines ride inside the text).
  * The control is capped so AppendText on the rich buffer stays O(small) no
    matter how long the scan runs (RICH2 AppendText slows as the buffer grows).

Colors are theme-aware, verified >=7:1 on the log background, and the appended
text content is unchanged so screen-reader output is unaffected.
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

# Cap the on-screen log so AppendText stays fast as a long scan streams output.
_MAX_CHARS = 200_000


def ansi_palette(dark):
    """Return the {key: hex} ANSI foreground palette for the given mode."""
    return dict(_ANSI_DARK if dark else _ANSI_LIGHT)


def parse_ansi(text, start_key):
    """Split *text* into colored runs.

    Returns (runs, end_key) where runs is a list of (segment, key_or_None) and
    end_key is the active color key after the text (so color spans writes). A
    reset (code 0 / empty ``\x1b[m``) sets key to None (default foreground).
    Unmapped codes are ignored, preserving the current key. Carriage returns and
    newlines are left INSIDE the segments; drain() interprets them.
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
        self._rewrite_current = False     # a \r requires clearing the control tail
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

        Must run on the UI thread. Cheap when the buffer is empty. \r spinner
        frames are resolved in Python first, then applied with the minimum
        number of AppendText calls, and the control is capped so it stays fast.
        """
        if self._ctrl is None:
            return
        with self._lock:
            if not self._buf:
                return
            chunk = "".join(self._buf)
            self._buf.clear()

        runs, self._key = parse_ansi(chunk, self._key)
        ops = self._resolve(runs)   # list of (text, key); text has no bare \r
        if not ops:
            return
        try:
            self._ctrl.Freeze()
            try:
                # A leading \r in this batch rewrote a line already on screen:
                # clear that line's remnant before appending the new text.
                if self._rewrite_current and self._line_len > 0:
                    end = self._ctrl.GetLastPosition()
                    self._ctrl.Remove(end - self._line_len, end)
                self._rewrite_current = False
                # Coalesce consecutive same-color ops into one AppendText —
                # AppendText on the rich buffer is the expensive part, so cutting
                # the call count is what matters. The engine wraps each line as
                # "<color>text<reset>\n", which would alternate color/default and
                # defeat merging; since a newline has no glyph, whitespace-only
                # ops are treated as color-neutral and keep the current run going.
                # Result: a batch of N same-color lines becomes ONE AppendText.
                pending_key = None
                parts = []
                for text, key in ops:
                    if not text:
                        continue
                    if not parts:
                        pending_key = key
                    elif text.strip() and key != pending_key:
                        self._set_colour(pending_key)
                        self._ctrl.AppendText("".join(parts))
                        parts = []
                        pending_key = key
                    parts.append(text)
                if parts:
                    self._set_colour(pending_key)
                    self._ctrl.AppendText("".join(parts))
                self._trim()
            finally:
                self._ctrl.Thaw()
        except Exception:
            pass

    def _resolve(self, runs):
        """Turn colored runs (with embedded \r/\n) into appendable (text, key)
        ops, applying carriage-return line rewrites in Python.

        Maintains self._line_len (chars on the current unterminated line) and
        self._rewrite_current (whether a \r requires clearing the control's
        current line tail before the first op is appended).
        """
        ops = []
        for seg, key in runs:
            if not seg:
                continue
            parts = seg.split("\r")   # split on \r only; \n rides inside text
            for pi, part in enumerate(parts):
                if pi > 0:
                    # A \r occurred: discard the in-progress current line. If it
                    # was built entirely within THIS batch, drop it from ops;
                    # otherwise flag the control's current line for clearing.
                    if not self._drop_current_line(ops):
                        self._rewrite_current = True
                    self._line_len = 0
                if part:
                    ops.append((part, key))
                    nl = part.rfind("\n")
                    if nl >= 0:
                        self._line_len = len(part) - nl - 1
                    else:
                        self._line_len += len(part)
        return ops

    def _drop_current_line(self, ops):
        """Remove the current unterminated line's text from pending ops.

        Returns True if the whole current line lived in ops (so nothing in the
        control needs clearing), False if part of it was already committed.
        """
        remaining = self._line_len
        while remaining > 0 and ops:
            text, key = ops[-1]
            nl = text.rfind("\n")
            tail = len(text) - nl - 1
            if tail <= remaining:
                ops.pop()
                remaining -= tail
                if nl >= 0:
                    ops.append((text[:nl + 1], key))   # keep through the newline
                    return True
            else:
                ops[-1] = (text[:len(text) - remaining], key)
                return True
        return remaining <= 0

    def _trim(self):
        """Cap the control length so AppendText stays fast as the log grows."""
        end = self._ctrl.GetLastPosition()
        if end <= _MAX_CHARS:
            return
        cut = end - _MAX_CHARS + _MAX_CHARS // 4   # drop oldest ~25% in one go
        try:
            value = self._ctrl.GetRange(0, cut)
            nl = value.rfind("\n")
            if nl >= 0:
                cut = nl + 1                          # snap to a line boundary
            self._ctrl.Remove(0, cut)
        except Exception:
            pass

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
