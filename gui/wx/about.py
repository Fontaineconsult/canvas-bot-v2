"""About + first-run Welcome dialogs (wx).

Both are simple scrollable read-only text dialogs — accessible by default (a
screen reader reads the text, Tab reaches the close button, Esc closes). Content
mirrors the security/accessibility/getting-started copy from the old GUI, with
the accessibility note updated to reflect the new native/screen-reader support.
"""

import wx

from gui.core import settings

_VERSION = "1.3.0"

_WELCOME_TEXT = """Welcome to Canvas Bot

Canvas Bot is a bridge between Canvas LMS and your desktop. It scans courses to
discover content, downloads files, and lets you review items for accessibility.

SECURITY & API CREDENTIALS
Canvas Bot requires a Canvas API access token, which grants read access to
course content on your behalf.
  1. Never share your API token with anyone.
  2. Generate a dedicated token for Canvas Bot; do not reuse tokens.
  3. Set an expiration date and rotate it periodically.
  4. If compromised, revoke it in Canvas (Account > Settings > Approved
     Integrations).
  5. Your token is stored in the Windows Credential Vault (encrypted, per-user).
     It is never written to plaintext files or logs.

DEPLOYMENT & RESPONSIBILITY
Canvas Bot is provided as-is under the CC-BY-NC-4.0 License. You are responsible
for how this tool is deployed and used within your institution. Ensure your use
complies with your institution's data governance policies and any applicable
regulations (FERPA, GDPR, etc.).

ACCESSIBILITY
This GUI is built with native controls for full screen-reader support (NVDA,
JAWS, SAPI). It provides full keyboard navigation, accessible names on every
control, spoken status and progress, and a color palette verified at 8:1
contrast. When Windows High Contrast is active, the app defers to your system
colors. Color is never the sole means of conveying information.

GETTING STARTED
  1. Use Reset Config to set up your Canvas instance URL and API token.
  2. Enter a course ID, choose an output folder, and check "Download files".
  3. Click Run to start scanning.
"""

_ABOUT_TEXT = f"""Canvas Bot v{_VERSION}

A bridge between Canvas LMS and your desktop: scan courses, download content,
review items for accessibility, and replace files in place.

TABS
  Run       — scan a course (or a list), download files, print content trees.
  Content   — browse scanned content, mark review status, open files and source
              pages, replace files (single or bulk).
  Patterns  — view, add, remove, and test the URL-classification patterns.

KEYBOARD
  Every button has an Alt+letter mnemonic (shown underlined). Tab moves between
  controls; Ctrl+Tab switches tabs. Status, progress, and results are spoken
  through your screen reader.

Licensed under CC-BY-NC-4.0. Provided as-is.
"""


def _text_dialog(parent, title, text, close_label="&Close", size=(620, 600)):
    dlg = wx.Dialog(parent, title=title, size=size,
                    style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    s = wx.BoxSizer(wx.VERTICAL)
    ctrl = wx.TextCtrl(dlg, value=text,
                       style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
    ctrl.SetName(title)
    s.Add(ctrl, 1, wx.EXPAND | wx.ALL, 10)
    btn = wx.Button(dlg, wx.ID_OK, close_label)
    s.Add(btn, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
    dlg.SetSizer(s)
    btn.SetFocus()
    dlg.SetEscapeId(wx.ID_OK)
    return dlg


def show_about(parent):
    dlg = _text_dialog(parent, "About Canvas Bot", _ABOUT_TEXT)
    dlg.ShowModal()
    dlg.Destroy()


def show_welcome_if_first_run(parent):
    """Show the welcome dialog once, then mark first-run complete."""
    if not settings.is_first_run():
        return
    dlg = _text_dialog(parent, "Welcome to Canvas Bot", _WELCOME_TEXT,
                       close_label="&Get Started")
    dlg.ShowModal()
    dlg.Destroy()
    settings.set_first_run_complete()
