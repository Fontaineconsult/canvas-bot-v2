"""Read-only log panel + ANSI-color-aware stdout/stderr redirector (wx).

The engine prints colored progress to stdout/stderr during a scan (colorama /
ANSI SGR codes), plus a spinner thread (utils/spinner.py) that rewrites a single
line via carriage returns ~10x/sec: it writes "\r<frame> <label> [<t>s]"
repeatedly, then "\r<symbol> <label> [<t>s] Done\n" when the step finishes. On a
large course that is *thousands* of writes in quick succession, from two threads.

PERFORMANCE / LOCKUP:
The redirector must never touch wx from the worker/spinner threads, and must
never do per-write UI work — a wx.CallAfter per write floods the UI event queue
and freezes the app ("Not Responding"). Instead:
  * write() (any thread) only appends to an in-memory buffer under a lock —
    no wx calls at all.
  * A wx.Timer on the UI thread calls drain() ~10x/sec, applying ALL buffered
    text in one batched, frozen update.

TERMINAL EMULATION (the correctness part):
The producer always rewrites a WHOLE line after a "\r" (spinner frame or the
final "Done" line), so we model "\r" as "discard the current unterminated line
and start fresh", and "\n" as "commit the current line". We keep the current
unterminated line as ``self._pending`` (a list of colored segments) that mirrors
the control's last on-screen line; each drain removes exactly that line from the
control and re-appends the recomputed result. This avoids stale-length bugs that
left spinner remnants (a stray "⠼") and truncated the next line ("Done" -> "D").

Colors are theme-aware, verified >=7:1 on the log background; appended text
content is unchanged so screen-reader output is unaffected.
"""

import re
import threading

import wx

# One ANSI SGR escape (e.g. "\x1b[33m").
_SGR_RE = re.compile(r"\x1b\[([0-9;]*)m")
# Line-control characters, kept as delimiters when splitting a segment.
_BREAK_RE = re.compile(r"(\r|\n)")

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
        # The current unterminated line as colored segments [(text, key), ...],
        # mirroring the control's last on-screen line (no '\r'/'\n' inside).
        self._pending = []
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

        # Treat a "\r\n" pair as a single newline (don't let the '\r' discard the
        # text before it). Bare '\r' (spinner) and bare '\n' are handled below.
        chunk = chunk.replace("\r\n", "\n")
        runs, self._key = parse_ansi(chunk, self._key)

        # Recompute the line state. ``committed`` are colored segments to append
        # (including '\n' terminators); ``pending`` becomes the new unterminated
        # line. ``pending`` starts as the existing on-screen line so text with no
        # leading '\r' continues it, and '\r' discards it (full-line rewrite).
        committed = []
        pending = list(self._pending)
        old_len = sum(len(t) for t, _ in self._pending)
        for seg, key in runs:
            if not seg:
                continue
            for tok in _BREAK_RE.split(seg):
                if tok == "":
                    continue
                if tok == "\r":
                    pending = []                 # discard current line
                elif tok == "\n":
                    committed.extend(pending)    # commit current line + newline
                    committed.append(("\n", key))
                    pending = []
                else:
                    pending.append((tok, key))

        try:
            self._ctrl.Freeze()
            try:
                # Remove the old on-screen unterminated line; everything we append
                # next (committed lines + the new pending line) replaces it.
                if old_len > 0:
                    end = self._ctrl.GetLastPosition()
                    self._ctrl.Remove(max(0, end - old_len), end)
                self._append_ops(committed + pending)
                self._trim()
            finally:
                self._ctrl.Thaw()
        except Exception:
            pass

        self._pending = pending

    def _append_ops(self, ops):
        """Append colored (text, key) segments with the fewest AppendText calls.

        AppendText on the rich buffer is the expensive part, so consecutive ops
        of the same color are merged into one call. A newline has no glyph, so
        whitespace-only ops are color-neutral and keep the current run going —
        turning a batch of same-colored lines into a single AppendText.
        """
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

    def _trim(self):
        """Cap the control length so AppendText stays fast as the log grows.

        Removes from the FRONT only, so the current pending line (at the end) is
        never disturbed.
        """
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
        # BORDER_NONE: the log is wrapped by widgets.card(), whose flat outline is
        # the only edge — a native sunken border would double up (white top-left).
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.HSCROLL | wx.BORDER_NONE,
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
