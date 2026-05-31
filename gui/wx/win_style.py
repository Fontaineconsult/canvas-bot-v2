"""Native Windows 10/11 window-chrome polish via DWM (ctypes only).

These functions style the *window frame* (title bar, corners, optional backdrop)
through the Desktop Window Manager. They do NOT touch any child control, so the
native MSAA/UIA accessibility of buttons, lists, etc. is completely unaffected —
this is purely cosmetic chrome that makes the app match Win10/11.

All functions are best-effort: on older Windows or any API error they silently
no-op, so the GUI still runs everywhere.
"""

import ctypes
import logging
from ctypes import wintypes

log = logging.getLogger(__name__)

# DWM window attributes (dwmapi.h).
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20          # BOOL: dark title bar
_DWMWA_WINDOW_CORNER_PREFERENCE = 33         # int: corner rounding (Win11)
_DWMWA_SYSTEMBACKDROP_TYPE = 38              # int: Mica/Acrylic (Win11 22H2+)

# DWM_WINDOW_CORNER_PREFERENCE values.
_DWMWCP_DEFAULT = 0
_DWMWCP_ROUND = 2
_DWMWCP_ROUNDSMALL = 3

# DWM_SYSTEMBACKDROP_TYPE values.
_DWMSBT_MAINWINDOW = 2   # Mica
_DWMSBT_TABBEDWINDOW = 4  # Mica Alt


def _hwnd(win):
    """Get the native HWND for a wx.Window, or None."""
    try:
        return int(win.GetHandle())
    except Exception:
        return None


def _set_attr(hwnd, attr, value):
    """Call DwmSetWindowAttribute(hwnd, attr, &value, sizeof(value))."""
    try:
        val = ctypes.c_int(int(value))
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(hwnd), ctypes.c_uint(attr),
            ctypes.byref(val), ctypes.sizeof(val),
        )
        return res == 0
    except Exception as exc:  # dwmapi missing (pre-Vista) or bad attr
        log.debug(f"DwmSetWindowAttribute({attr}) failed: {exc}")
        return False


def set_dark_titlebar(win, dark):
    """Make the window's title bar dark (or light). Win10 2004+ / Win11."""
    hwnd = _hwnd(win)
    if hwnd is None:
        return False
    return _set_attr(hwnd, _DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if dark else 0)


def set_rounded_corners(win, rounded=True, small=False):
    """Round the window corners (Win11 only; silently ignored on Win10)."""
    hwnd = _hwnd(win)
    if hwnd is None:
        return False
    if not rounded:
        pref = _DWMWCP_DEFAULT
    else:
        pref = _DWMWCP_ROUNDSMALL if small else _DWMWCP_ROUND
    return _set_attr(hwnd, _DWMWA_WINDOW_CORNER_PREFERENCE, pref)


def set_mica_backdrop(win, enabled=True):
    """Enable the Win11 Mica backdrop (22H2+). Opt-in: it tints toward the
    desktop and can wash out custom panel colors, so it's not applied by
    default."""
    hwnd = _hwnd(win)
    if hwnd is None:
        return False
    return _set_attr(hwnd, _DWMWA_SYSTEMBACKDROP_TYPE,
                     _DWMSBT_MAINWINDOW if enabled else 0)


def modernize(win, dark, rounded=True):
    """Apply the standard chrome polish to a top-level window.

    Safe to call after the window is created/shown. Matches the title bar to the
    app theme and rounds corners on Win11. No-ops under High Contrast handling
    are the caller's concern (pass dark=False there).
    """
    set_dark_titlebar(win, dark)
    if rounded:
        set_rounded_corners(win, True)


def polish_dialog(dlg, theme):
    """Apply font + theme colors + Win10/11 chrome to a dialog.

    Convenience for the modal dialogs (progress, bulk replace, about) so they
    match the main window. ``theme`` is a gui.wx.theme.Theme. Safe/no-op when
    theme is None or under High Contrast.
    """
    if theme is not None:
        theme.apply_window(dlg)
        theme.apply_font(dlg)
        dark = theme.dark and theme.active
    else:
        dark = False
    modernize(dlg, dark=dark, rounded=True)


def theme_of(win):
    """Best-effort lookup of the Theme attached to the top-level frame."""
    try:
        top = win.GetTopLevelParent()
        return getattr(top, "theme", None)
    except Exception:
        return None
