"""Help view + first-run Welcome dialog (wx).

The Help view is a tabbed dialog (About / Run / Content / Patterns) ported and
expanded from the old CTk GUI's About dialog. It is built from native, accessible
controls: a wx.Notebook (Ctrl+Tab / arrow keys / Alt+1-4 switch tabs) and a
read-only rich TextCtrl per page that a screen reader reads top to bottom. The
Welcome dialog is the simple first-run text dialog.
"""

import wx
import wx.adv

from gui.core import settings
from gui.wx import win_style

_VERSION = "1.3.0"

# ── content model ───────────────────────────────────────────────────────────
# Each page is a list of items rendered into a rich TextCtrl:
#   ("title", main, subtitle)   big page title + muted subtitle
#   ("h", text)                 bold section heading
#   ("p", text)                 body paragraph
#   ("b", lead[, desc])         bullet: bold lead-in, optional muted description
#   ("note", text)              small italic muted note

_ABOUT_HELP = [
    ("title", "Canvas Bot", f"v{_VERSION}  ·  CC-BY-NC-4.0"),
    ("h", "What is Canvas Bot?"),
    ("p", "Canvas Bot is a bridge between Canvas LMS and your desktop. It connects "
          "to your institution's Canvas, scans courses to discover every embedded "
          "file, link, and media item, and lets you download that content, browse "
          "it by type, and review it for accessibility. It is built for "
          "instructional designers and accessibility specialists who audit courses "
          "at scale."),
    ("h", "Getting Started"),
    ("p", "1.  Open the Config menu and choose “Reset Canvas API Credentials.”"),
    ("p", "2.  Enter your institution identifier (e.g. “sfsu” for "
          "sfsu.instructure.com)."),
    ("p", "3.  Paste your Canvas API access token when prompted."),
    ("p", "4.  On the Run tab, enter a course ID, choose an output folder, and "
          "click Run."),
    ("h", "Configuration"),
    ("p", "Generate an API token in Canvas under Account › Settings › New "
          "Access Token. Use Config › View Config to check your current setup, "
          "and the Reset options to change your instance URL or token. Your token "
          "is stored encrypted in the Windows Credential Vault — never in "
          "plaintext files or logs."),
    ("h", "Accessibility"),
    ("p", "Canvas Bot is built entirely from native controls for full screen-reader "
          "support (NVDA, JAWS, System Access, and more). Every control has an "
          "accessible name and an Alt+letter shortcut, status and progress are "
          "spoken aloud, and the color palette is verified at 8:1 contrast. When "
          "Windows High Contrast is on, the app defers to your system colors. Color "
          "is never the only way information is conveyed."),
    ("h", "Contact — Ideas & Issues"),
    ("p", "Daniel Fontaine"),
]

_RUN_HELP = [
    ("title", "Run", "Scan a course and download its content"),
    ("h", "Course Selection"),
    ("p", "Choose what to scan:"),
    ("b", "Course ID", "the number from your course URL (e.g. canvas.edu/courses/12345)."),
    ("b", "Course List", "a .txt file with one course ID per line, for batch processing."),
    ("note", "Only one input is active at a time — entering a Course ID clears the "
             "Course List and vice versa. The Course ID box takes digits only, up to 10."),
    ("h", "Output"),
    ("p", "Select an output folder, then check “Download files” to enable downloading."),
    ("b", "Downloads are organized into subfolders by module and content type."),
    ("b", "Scanned content is saved automatically so you can browse it on the Content tab."),
    ("note", "Set an output folder and check “Download files” before the Run "
             "button activates."),
    ("h", "Download Options"),
    ("p", "By default only documents (PDF, DOCX, PPTX, etc.) that are visible and "
          "linked from a course page are downloaded."),
    ("b", "Download video / audio / image files", "adds those media types alongside documents."),
    ("b", "Include hidden / locked", "also includes items flagged hidden, unpublished, "
          "locked, or hidden from students."),
    ("b", "Include unlinked", "also includes files that exist in the course but aren't "
          "linked from any active page."),
    ("b", "Flatten folder structure", "saves all files into one directory instead of "
          "preserving the module hierarchy."),
    ("note", "Hidden/locked and Unlinked are independent filters — a file that is "
             "both requires both options checked to download."),
    ("h", "Display Options"),
    ("p", "Single-course mode only:"),
    ("b", "Print content tree", "prints a tree of the resources that contain downloadable content."),
    ("b", "Print full course tree", "prints every resource, including empty modules and pages."),
    ("note", "These two are mutually exclusive and disabled during batch processing."),
    ("h", "Reading the Log"),
    ("p", "Progress streams into the colored log as each content type is imported. "
          "Status and milestones are also spoken through your screen reader, with a "
          "periodic “still importing” reminder during long scans."),
]

_CONTENT_HELP = [
    ("title", "Content", "Browse and review scanned course content"),
    ("h", "Content Viewer"),
    ("p", "Browse content from previously scanned courses. After a scan with an "
          "output folder set, each course's data is saved and appears in the course "
          "dropdown here."),
    ("h", "Course Toolbar"),
    ("b", "Course dropdown", "lists every scanned course found in your output folder."),
    ("b", "Refresh (Alt+E)", "re-scans the output folder for new or updated data."),
    ("b", "Open Folder (Alt+D)", "opens the selected course's folder in File Explorer."),
    ("b", "Open in Canvas (Alt+V)", "opens the course's Files page in Canvas in your browser."),
    ("b", "Delete Course Data (Alt+A)", "permanently deletes the selected course's local "
          "folder and downloads, after a confirmation. This only removes local files — "
          "nothing on Canvas is touched."),
    ("h", "Content Types"),
    ("p", "The “Content type” dropdown switches the table between the categories "
          "Canvas Bot tracks:"),
    ("b", "Documents", "downloadable Canvas files (PDF, DOCX, etc.)."),
    ("b", "Document / Video / Audio Sites", "external links (Google Docs, YouTube, podcasts)."),
    ("b", "Video / Audio / Image Files", "downloadable media files."),
    ("b", "Institution Video, Textbooks, File Storage, Unsorted", "institution video, "
          "digital textbooks, cloud-storage links, and links that matched no known pattern."),
    ("note", "Click any column heading to sort (numeric-aware). The selected row is "
             "announced with its column context."),
    ("h", "Review Status"),
    ("p", "Select a row, then mark it with the status buttons:"),
    ("b", "Mark Passed", "reviewed and acceptable (green)."),
    ("b", "Mark Needs Review", "requires further attention (amber)."),
    ("b", "Mark Ignore", "excluded from review (gray)."),
    ("note", "Status is saved per-course and persists across sessions."),
    ("h", "Filters"),
    ("b", "Show inactive content", "also lists items not linked from any active page or "
          "marked hidden. Off by default."),
    ("h", "Action Buttons"),
    ("b", "Open File Location (Alt+L)", "opens the folder containing a downloaded file. "
          "For link/site rows it becomes “Open Site Link” and opens the URL."),
    ("b", "Open File (Alt+O)", "opens the downloaded file in its default application."),
    ("b", "Open Source Page (Alt+S)", "opens the Canvas page(s) where the item was found."),
    ("b", "Replace File (Alt+R)", "uploads a local file to replace the selected Canvas "
          "document. Enabled only for Canvas-hosted documents when your token has "
          "file-edit permission. After a successful replace the row title is suffixed "
          "“(replaced)” until the next scan."),
    ("b", "Bulk Replace (Alt+B)", "replaces many Canvas documents at once from a local "
          "folder, matched by case-insensitive filename. Enabled only when the course "
          "has replaceable Canvas files; disabled while a non-replaceable External File "
          "row is selected."),
    ("note", "Replace and Bulk Replace appear only on the Documents view, since "
             "replacement applies only to downloadable Canvas files."),
]

_PATTERNS_HELP = [
    ("title", "Patterns", "Classify discovered URLs"),
    ("h", "Pattern Manager"),
    ("p", "Canvas Bot uses regular-expression patterns to classify every URL it "
          "discovers — deciding whether a link is a document, video, audio, image, "
          "or other content type. This tab lets you view, edit, and test those patterns."),
    ("h", "Categories"),
    ("b", "Select a category", "to view its patterns in the table."),
    ("b", "Count", "each category header shows how many patterns it contains."),
    ("note", "Some internal categories are hidden here but still run in the pipeline."),
    ("h", "Editing Patterns"),
    ("b", "Add Pattern", "enter a new regex for the selected category."),
    ("b", "Remove Pattern", "delete the selected pattern."),
    ("b", "Validate", "check a pattern's regex syntax before saving."),
    ("note", "Patterns use Python regex syntax. Changes take effect on the next scan."),
    ("h", "Test URL"),
    ("p", "Enter a URL or filename in the Test box and click Test. The result lists "
          "every category that matches, so you can confirm a URL is classified correctly."),
    ("h", "Reset to Defaults"),
    ("p", "“Reset All to Defaults” restores the original bundled patterns."),
    ("note", "This permanently removes any custom patterns you've added."),
]

_PAGES = [
    ("About", _ABOUT_HELP),
    ("Run", _RUN_HELP),
    ("Content", _CONTENT_HELP),
    ("Patterns", _PATTERNS_HELP),
]


# ── rendering ────────────────────────────────────────────────────────────────

def _make_help_ctrl(parent, name, sections, theme):
    """A read-only rich TextCtrl rendering one help page's sections."""
    ctrl = wx.TextCtrl(
        parent,
        style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.BORDER_NONE,
    )
    ctrl.SetName(f"{name} help")
    # Styled per-run below from the theme font; opt out of the tree-wide
    # apply_font pass so the bold headings / muted notes survive.
    ctrl._keep_font = True

    base = theme.base_font() if theme is not None else \
        wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
    base_px = (base.GetPixelSize().height or 14)

    def font(px_delta=0, bold=False, italic=False):
        f = wx.Font(base)
        if px_delta:
            f.SetPixelSize(wx.Size(0, base_px + px_delta))
        if bold:
            f.SetWeight(wx.FONTWEIGHT_BOLD)
        if italic:
            f.SetStyle(wx.FONTSTYLE_ITALIC)
        return f

    def col(key, fallback):
        try:
            return theme.color(key)
        except Exception:
            return wx.Colour(fallback)

    text_c = col("text", "#1A1A1A")
    muted_c = col("muted_text", "#4D4D4D")
    accent_c = col("accent", "#00407F")
    if theme is not None:
        try:
            ctrl.SetBackgroundColour(theme.color("window_bg"))
        except Exception:
            pass

    def run(s, colour, f):
        ctrl.SetDefaultStyle(wx.TextAttr(colour, wx.NullColour, f))
        ctrl.AppendText(s)

    for item in sections:
        kind = item[0]
        if kind == "title":
            run(item[1] + "\n", accent_c, font(8, bold=True))
            if len(item) > 2 and item[2]:
                run(item[2] + "\n", muted_c, font())
        elif kind == "h":
            run("\n" + item[1] + "\n", text_c, font(4, bold=True))
        elif kind == "p":
            run(item[1] + "\n", text_c, font())
        elif kind == "b":
            run("   •  ", text_c, font())
            run(item[1], text_c, font(bold=True))
            if len(item) > 2 and item[2]:
                run("  —  " + item[2], muted_c, font())
            run("\n", text_c, font())
        elif kind == "note":
            run("   " + item[1] + "\n", muted_c, font(italic=True))

    ctrl.SetInsertionPoint(0)
    return ctrl


def _add_about_links(page, sizer, theme):
    """Clickable email + GitHub links under the About page text."""
    row = wx.BoxSizer(wx.HORIZONTAL)
    lbl = wx.StaticText(page, label="Contact:")
    row.Add(lbl, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    email = wx.adv.HyperlinkCtrl(page, wx.ID_ANY, "fontaine@sfsu.edu",
                                 "mailto:fontaine@sfsu.edu")
    gh = wx.adv.HyperlinkCtrl(page, wx.ID_ANY,
                              "github.com/Fontaineconsult/canvas-bot-v2",
                              "https://github.com/Fontaineconsult/canvas-bot-v2")
    row.Add(email, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 16)
    row.Add(gh, 0, wx.ALIGN_CENTER_VERTICAL)
    sizer.Add(row, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)


def _open_logs():
    try:
        from gui.core import app_service
        app_service.open_log_file()
    except Exception:
        pass


def show_help(parent):
    """Open the tabbed Help dialog (About / Run / Content / Patterns)."""
    theme = win_style.theme_of(parent)
    dlg = wx.Dialog(parent, title="Canvas Bot Help", size=(740, 660),
                    style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dlg.SetMinSize((560, 460))

    nb = wx.Notebook(dlg)
    nb.SetName("Help topics")
    for name, sections in _PAGES:
        page = wx.Panel(nb)
        psz = wx.BoxSizer(wx.VERTICAL)
        psz.Add(_make_help_ctrl(page, name, sections, theme), 1, wx.EXPAND | wx.ALL, 8)
        if name == "About":
            _add_about_links(page, psz, theme)
        page.SetSizer(psz)
        nb.AddPage(page, name)

    outer = wx.BoxSizer(wx.VERTICAL)
    outer.Add(nb, 1, wx.EXPAND | wx.ALL, 8)

    btn_row = wx.BoxSizer(wx.HORIZONTAL)
    logs = wx.Button(dlg, wx.ID_ANY, "&Logs")
    logs.SetToolTip("Open the Canvas Bot log file")
    logs.Bind(wx.EVT_BUTTON, lambda e: _open_logs())
    close = wx.Button(dlg, wx.ID_CANCEL, "&Close")
    btn_row.Add(logs, 0)
    btn_row.AddStretchSpacer(1)
    btn_row.Add(close, 0)
    outer.Add(btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

    dlg.SetSizer(outer)
    dlg.SetEscapeId(wx.ID_CANCEL)

    # Alt+1..4 jump to a tab (Ctrl+Tab and arrow keys work natively too).
    entries = []
    for i in range(len(_PAGES)):
        wid = wx.NewIdRef()
        dlg.Bind(wx.EVT_MENU, lambda e, idx=i: nb.SetSelection(idx), id=wid)
        entries.append(wx.AcceleratorEntry(wx.ACCEL_ALT, ord(str(i + 1)), wid))
    dlg.SetAcceleratorTable(wx.AcceleratorTable(entries))

    if theme is not None:
        try:
            theme.apply_font(dlg)
        except Exception:
            pass
    win_style.polish_dialog(dlg, theme)

    dlg.CentreOnParent()
    nb.SetFocus()
    dlg.ShowModal()
    dlg.Destroy()


# Back-compat: the Help menu's About entry opens the tabbed Help view.
def show_about(parent):
    show_help(parent)


# ── first-run Welcome ────────────────────────────────────────────────────────

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
JAWS, System Access, and more). It provides full keyboard navigation, accessible
names on every control, spoken status and progress, and a color palette verified
at 8:1 contrast. When Windows High Contrast is active, the app defers to your
system colors. Color is never the sole means of conveying information.

GETTING STARTED
  1. Use the Config menu to set up your Canvas instance URL and API token.
  2. Enter a course ID, choose an output folder, and check "Download files".
  3. Click Run to start scanning.

Press F1 any time to open the full Help.
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
    win_style.polish_dialog(dlg, win_style.theme_of(parent))
    return dlg


def show_welcome_if_first_run(parent):
    """Show the welcome dialog once, then mark first-run complete."""
    if not settings.is_first_run():
        return
    dlg = _text_dialog(parent, "Welcome to Canvas Bot", _WELCOME_TEXT,
                       close_label="&Get Started")
    dlg.ShowModal()
    dlg.Destroy()
    settings.set_first_run_complete()
