"""Regenerate the README's wx GUI screenshots automatically.

Launches the real MainFrame, stages presentable demo values, walks the three
tabs on a timer, and captures the window over docs/images/*.png.

Usage (from the repo root):

    python tools/screenshot_readme.py --demo-folder "C:\\path\\to\\scanned courses"

--demo-folder is a folder containing at least one scanned course folder
(with .manifest/content JSON) — it is what the Content tab displays. When
given, settings are patched IN MEMORY only: the user's saved GUI settings
are never modified. Without it, the app's real settings are used as-is.

Requires a display; the window must stay unoccluded during the ~11 seconds
of capture. A neutral full-screen backdrop is placed behind the app so
rounded-corner/DWM edge slop lands on plain grey instead of the desktop.
"""
import argparse
import ctypes
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(REPO, "docs", "images")

os.chdir(REPO)
sys.path.insert(0, REPO)

parser = argparse.ArgumentParser()
parser.add_argument("--demo-folder", default=None,
                    help="Output folder shown in the Content tab (patched in memory)")
parser.add_argument("--course-id", default="12345",
                    help="Course ID displayed on the Run tab")
parser.add_argument("--folder-display", default=r"C:\Canvas Downloads",
                    help="Cosmetic text for the Run tab's output-folder field")
args = parser.parse_args()

if args.demo_folder:
    from gui.core import settings as settings_mod

    _orig_load = settings_mod.load

    def _demo_load():
        s = dict(_orig_load() or {})
        s.update({"course_id": args.course_id, "course_list": "",
                  "output_folder": args.demo_folder})
        return s

    settings_mod.load = _demo_load
    settings_mod.save = lambda *a, **k: None  # demo values must never persist

# Per-monitor DPI awareness BEFORE wx initializes: without it, wx reports
# logical coordinates while ScreenDC blits physical pixels, so the capture
# lands offset and picks up whatever is behind the window.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import wx  # noqa: E402

from gui.wx.app import MainFrame  # noqa: E402

app = wx.App(False)

backdrop = wx.Frame(None, style=wx.BORDER_NONE)
backdrop.SetBackgroundColour(wx.Colour(226, 228, 232))
backdrop.ShowFullScreen(True)

frame = MainFrame()
# Design size scaled to the monitor's DPI so nothing is clipped, clamped to
# the work area so the window can't extend under the taskbar.
size = frame.FromDIP(wx.Size(1000, 860))
area = wx.Display(0).GetClientArea()
frame.SetSize(wx.Size(min(size.width, area.width - 160),
                      min(size.height, area.height - 120)))
frame.SetPosition((area.x + 80, area.y + 50))
frame.Show()
frame.Raise()
frame.run_panel.output_folder.ChangeValue(args.folder_display)

_real_stdout = sys.__stdout__  # GUI log redirects sys.stdout; report around it
shots = []


def _visible_bounds():
    """True on-screen window rect via DWM extended frame bounds.

    wx's GetScreenRect includes the invisible resize/shadow border, which
    blits slivers of whatever is behind the window into the capture.
    """
    import ctypes.wintypes as wt
    r = wt.RECT()
    DWMWA_EXTENDED_FRAME_BOUNDS = 9
    res = ctypes.windll.dwmapi.DwmGetWindowAttribute(
        frame.GetHandle(), DWMWA_EXTENDED_FRAME_BOUNDS,
        ctypes.byref(r), ctypes.sizeof(r))
    if res == 0:
        return r.left, r.top, r.right - r.left, r.bottom - r.top
    rect = frame.GetScreenRect()
    return rect.x, rect.y, rect.width, rect.height


def capture(filename):
    frame.Raise()
    wx.SafeYield()
    x, y, w, h = _visible_bounds()
    dc = wx.ScreenDC()
    bmp = wx.Bitmap(w, h)
    mem = wx.MemoryDC(bmp)
    mem.Blit(0, 0, w, h, dc, x, y)
    mem.SelectObject(wx.NullBitmap)
    ok = bmp.SaveFile(os.path.join(IMAGES, filename), wx.BITMAP_TYPE_PNG)
    shots.append((filename, ok, w, h))


def step_run():
    frame.notebook.SetSelection(0)
    wx.CallLater(800, lambda: capture("screenshot-of-the-run-view.png"))


def step_content():
    frame.notebook.SetSelection(1)
    if frame.content_panel is not None:
        frame.content_panel.refresh_courses()
    # permission check is async — give it time before the shot
    wx.CallLater(2600, lambda: capture("screenshot-of-the-content-view.png"))


def step_patterns():
    frame.notebook.SetSelection(2)
    wx.CallLater(800, lambda: capture("screenshot-of-the-patterns-view.png"))


def finish():
    for name, ok, w, h in shots:
        print(f"{name}: {'saved' if ok else 'SAVE FAILED'} ({w}x{h})",
              file=_real_stdout)
    frame.Close(force=True)
    backdrop.Close(force=True)  # keeping it open would hold MainLoop forever


wx.CallLater(4000, step_run)        # let startup token validation settle
wx.CallLater(5500, step_content)
wx.CallLater(8800, step_patterns)
wx.CallLater(10300, finish)

app.MainLoop()
