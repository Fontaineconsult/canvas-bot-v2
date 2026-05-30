"""Read-only log panel + stdout/stderr redirector for the wx GUI.

Replaces the CustomTkinter ``TextRedirector``. The engine prints progress to
stdout/stderr during a scan; we capture those writes and append them to a
read-only ``wx.TextCtrl`` on the UI thread via ``wx.CallAfter``.

ANSI color escape sequences (the engine uses colorama) are stripped to keep the
text readable — color isn't reproduced (it carries no information a screen
reader needs, and the meaningful status is spoken separately).

Carriage-return spinner frames (``\r`` without ``\n``) are collapsed so the log
doesn't fill with thousands of spinner lines: a lone ``\r`` rewrites the current
(last) line instead of appending.
"""

import re

import wx

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class LogRedirector:
    """File-like object that appends writes to a wx.TextCtrl.

    Pass the original stream so output is still echoed there (useful when
    launched from a console). Install by assigning to sys.stdout/sys.stderr;
    restore the originals when the scan finishes.
    """

    def __init__(self, text_ctrl, original=None):
        self._ctrl = text_ctrl
        self._original = original

    def write(self, text):
        if self._original is not None:
            try:
                self._original.write(text)
            except Exception:
                pass
        clean = _ANSI_RE.sub("", text)
        if not clean:
            return
        wx.CallAfter(self._append, clean)

    def _append(self, text):
        if not self._ctrl:
            return
        # Collapse \r spinner frames: a chunk containing \r but no \n rewrites
        # the last visible line rather than appending a new one.
        if "\r" in text and "\n" not in text:
            last = text.rsplit("\r", 1)[-1]
            self._replace_last_line(last)
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
            self._ctrl.Replace(start, self._ctrl.GetLastPosition(), text)
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


def make_log_ctrl(parent, name="Output log"):
    """Create the read-only multiline TextCtrl used as the log view."""
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
    return ctrl
