"""Color palette and theming for the wx GUI.

Provides a single light/dark palette whose every foreground/background pair is
verified at >= 8:1 contrast (well past WCAG AAA's 7:1), plus status-row colors
for the content/replace tables.

High Contrast deferral: when Windows High Contrast is active the user has chosen
their own accessible colors, so we must NOT override them. ``apply()`` becomes a
no-op in that case and native controls inherit the system theme.

Light vs. dark is chosen from ``wx.SystemSettings.GetAppearance().IsDark()``.
"""

import ctypes
import ctypes.wintypes
import logging

import wx

log = logging.getLogger(__name__)


# Each fg/bg pair below is >= 8:1. Verified with the WCAG relative-luminance
# formula (see _contrast_ratio / the theme self-test).
_DARK = {
    "window_bg":   "#121212",  # near-black, avoids pure-black halation
    "panel_bg":    "#1E1E1E",
    "text":        "#F0F0F0",  # ~17:1 on window_bg
    "muted_text":  "#B8B8B8",  # ~8.6:1 on window_bg
    "accent":      "#6BB4FF",  # lightened to clear >=8:1 on window_bg
    "selection_bg": "#264F78",
    "selection_text": "#FFFFFF",
    "error":       "#FF8A80",  # ~8.6:1 on window_bg
    "success":     "#7CE38B",  # bright green, high contrast
    "warning":     "#FFD24D",  # bright amber, high contrast
}

_LIGHT = {
    "window_bg":   "#FFFFFF",
    "panel_bg":    "#F4F4F4",
    "text":        "#1A1A1A",  # ~17:1 on white
    "muted_text":  "#4D4D4D",  # ~8.4:1 on white
    "accent":      "#00407F",  # darkened so it clears >=8:1 on white
    "selection_bg": "#CCE4FF",
    "selection_text": "#1A1A1A",
    "error":       "#A30016",  # darkened red, >=8:1 on white
    "success":     "#15571A",  # darkened green, >=8:1 on white
    "warning":     "#6E4700",  # darkened amber, >=8:1 on white
}

# Status-row background colors keyed by review/bulk-replace status. Ported from
# gui/table_widget.py:_STATUS_COLORS. Text color on these rows is forced to the
# palette "text" which keeps >=8:1 against every swatch here.
_STATUS_BG = {
    "dark": {
        "Passed": "#16361B", "Needs Review": "#3A2D08", "Ignore": "#2A2A2A",
        "Will replace": "#16361B", "Replacing…": "#3A2D08", "Done": "#16361B",
        "Failed": "#4A1A1A", "Skipped": "#2A2A2A", "No match": "#2A2A2A",
        "Already replaced": "#2A2A2A", "Ambiguous": "#2A2A2A", "Ignored": "#2A2A2A",
        "User File": "#2A2A2A", "Group File": "#2A2A2A",
    },
    "light": {
        "Passed": "#D4EDDA", "Needs Review": "#FFF3CD", "Ignore": "#E2E3E5",
        "Will replace": "#D4EDDA", "Replacing…": "#FFF3CD", "Done": "#D4EDDA",
        "Failed": "#F8D7DA", "Skipped": "#E2E3E5", "No match": "#E2E3E5",
        "Already replaced": "#E2E3E5", "Ambiguous": "#E2E3E5", "Ignored": "#E2E3E5",
        "User File": "#E2E3E5", "Group File": "#E2E3E5",
    },
}


def is_high_contrast():
    """True when Windows High Contrast mode is active.

    Uses SystemParametersInfoW(SPI_GETHIGHCONTRAST) and checks the
    HCF_HIGHCONTRASTON bit. Returns False on any error / non-Windows.
    """
    SPI_GETHIGHCONTRAST = 0x0042
    HCF_HIGHCONTRASTON = 0x00000001

    class HIGHCONTRAST(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.UINT),
            ("dwFlags", ctypes.wintypes.DWORD),
            ("lpszDefaultScheme", ctypes.wintypes.LPWSTR),
        ]

    try:
        hc = HIGHCONTRAST()
        hc.cbSize = ctypes.sizeof(HIGHCONTRAST)
        ok = ctypes.windll.user32.SystemParametersInfoW(
            SPI_GETHIGHCONTRAST, ctypes.sizeof(HIGHCONTRAST), ctypes.byref(hc), 0
        )
        if not ok:
            return False
        return bool(hc.dwFlags & HCF_HIGHCONTRASTON)
    except Exception as exc:  # pragma: no cover - non-Windows / API quirk
        log.debug(f"High-contrast check failed: {exc}")
        return False


def is_dark():
    """True when the system is using a dark appearance."""
    try:
        return wx.SystemSettings.GetAppearance().IsDark()
    except Exception:
        return False


def _scaled_px(px):
    """Scale a base-96-DPI pixel size by the current display scaling.

    The process is per-monitor DPI aware, so at 125%/150% we must scale our
    pixel-based font sizes ourselves (point sizes scale automatically, pixel
    sizes do not). At 100% this returns px unchanged.
    """
    try:
        hdc = ctypes.windll.user32.GetDC(0)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
        ctypes.windll.user32.ReleaseDC(0, hdc)
        if dpi and dpi != 96:
            return max(1, round(px * dpi / 96))
    except Exception:
        pass
    return px


# LOGFONT.lfQuality = CLEARTYPE_QUALITY. wxMSW serializes the LOGFONT as a
# ';'-joined string; field 13 is lfQuality and defaults to 0 (DEFAULT_QUALITY),
# which lets GDI choose and can render text — especially synthesized weights —
# without ClearType smoothing (jaggy). Forcing 5 turns ClearType on explicitly.
_CLEARTYPE_QUALITY = "5"
_QUALITY_FIELD = 13


def _force_cleartype(font):
    """Force ClearType anti-aliasing on a wx.Font (Windows, no-op elsewhere).

    Rewrites only the lfQuality field of the native font-info string, so weight,
    size and face are preserved. Unexpected formats are left untouched.
    """
    try:
        parts = font.GetNativeFontInfoDesc().split(";")
        if len(parts) > _QUALITY_FIELD and parts[_QUALITY_FIELD] != _CLEARTYPE_QUALITY:
            parts[_QUALITY_FIELD] = _CLEARTYPE_QUALITY
            font.SetNativeFontInfo(";".join(parts))
    except Exception:
        pass
    return font


class Theme:
    """Resolved palette for the current session.

    ``active`` is False under High Contrast — callers should then skip applying
    custom colors and let native system colors show through.
    """

    def __init__(self):
        self.high_contrast = is_high_contrast()
        self.dark = is_dark()
        self.active = not self.high_contrast
        palette = _DARK if self.dark else _LIGHT
        self._palette = palette
        self._status_bg = _STATUS_BG["dark" if self.dark else "light"]
        self._base_font = None

    def base_font(self):
        """The app UI font: classic Segoe UI at an integer pixel height.

        We deliberately use **"Segoe UI"** rather than "Segoe UI Variable" —
        the variable font renders with soft/thin stems under GDI ClearType,
        which reads as fuzzy. Classic Segoe UI is heavily hinted and renders
        crisp. We size it via SetPixelSize (integer pixels) instead of points,
        because a point size like 10pt = 13.33px at 96 DPI lands between pixels
        and softens the text; an integer pixel height stays sharp.
        """
        if self._base_font is not None:
            return self._base_font
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        for face in ("Segoe UI", "Tahoma"):
            candidate = wx.Font(font)
            candidate.SetFaceName(face)
            if candidate.IsOk() and candidate.GetFaceName() == face:
                font = candidate
                break
        # 14px ≈ 10.5pt: a touch larger than the 12px default, integer-aligned.
        font.SetPixelSize(wx.Size(0, _scaled_px(14)))
        # Use SEMIBOLD (600): Segoe UI ships a REAL "Segoe UI Semibold" face, so
        # GDI renders it from a hinted outline and it stays crisp. Medium (500)
        # has no real face — GDI synthesizes it by thickening Regular, which
        # renders soft/jaggy next to the DirectWrite-drawn window title. Semibold
        # is the lightest real face above Regular, so it's crisp AND a touch
        # heavier (the look we want) without the synthesis artifacts.
        font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)
        _force_cleartype(font)   # smooth ClearType edges (fixes jaggy synth weight)
        self._base_font = font
        return font

    def heading_font(self):
        """A slightly larger, semibold font for section headings."""
        font = wx.Font(self.base_font())
        font.SetPixelSize(wx.Size(0, _scaled_px(17)))
        font.SetWeight(wx.FONTWEIGHT_SEMIBOLD)
        return _force_cleartype(font)

    def apply_font(self, win, recurse=True):
        """Set the app font on a window (and optionally its children).

        Controls that opt out by setting ``_keep_font = True`` are skipped, so
        deliberately-styled widgets (e.g. the bold primary button, headings)
        survive a tree-wide font pass.
        """
        if not getattr(win, "_keep_font", False):
            try:
                win.SetFont(self.base_font())
            except Exception:
                pass
        if recurse:
            for child in win.GetChildren():
                self.apply_font(child, recurse=True)

    def color(self, key):
        """Return a wx.Colour for a palette key (e.g. 'text', 'accent')."""
        return wx.Colour(self._palette[key])

    def status_bg(self, status):
        """Return the row-background wx.Colour for a status, or None."""
        hexv = self._status_bg.get(status)
        return wx.Colour(hexv) if hexv else None

    def apply_window(self, win):
        """Apply window/panel bg + text fg to a window. No-op in High Contrast."""
        if not self.active:
            return
        try:
            win.SetBackgroundColour(self.color("window_bg"))
            win.SetForegroundColour(self.color("text"))
        except Exception:
            pass

    def apply_panel(self, win):
        """Apply panel bg + text fg. No-op in High Contrast."""
        if not self.active:
            return
        try:
            win.SetBackgroundColour(self.color("panel_bg"))
            win.SetForegroundColour(self.color("text"))
        except Exception:
            pass


# ── contrast helper (used by the theme self-test) ──

def _rel_luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg, bg):
    """WCAG contrast ratio between two hex colors."""
    l1, l2 = _rel_luminance(fg), _rel_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)
