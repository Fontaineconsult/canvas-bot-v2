# Changelog

## v1.2.1

### SOC 2 Remediation — Logging & Security Hardening

#### SSL Certificate Verification (Critical — C1)
- **Enabled SSL verification on all Canvas API calls** — removed `verify=False` and `urllib3.disable_warnings()` from `network/api.py`. All API requests now validate TLS certificates, preventing man-in-the-middle interception of access tokens.
- Files changed: `network/api.py`

#### Studio API URL Cleaning (High — H2)
- **Added `_clean_url()` to Studio API module** — all log and warning messages in `response_handler()` and `post_handler()` now strip sensitive query parameters (email addresses, tokens) before display. Matches the pattern already used in `network/api.py`.
- Files changed: `network/studio_api.py`

#### User/Session Identification in Logs (Medium — M4)
- **Added username and session ID to every log entry** — a `SessionContextFilter` injects the Windows username (via `getpass.getuser()`) and an 8-character session UUID into all log records. Log format is now `%(asctime)s - %(user)s - %(session)s - %(name)s - %(levelname)s - %(message)s`. Session ID is consistent within a run and unique across runs, enabling attribution on shared machines.
- Files changed: `tools/logger.py`

#### Log File Permissions (Medium — M1)
- **Best-effort file permission restriction** — `os.chmod()` is applied to the log file after creation to restrict access. On Windows `os.chmod` has limited effect, but `%APPDATA%` is already per-user protected.
- Files changed: `tools/logger.py`

#### Audit Trail for Content Access (Medium — M2)
- **Added structured audit log entries** at key pipeline stages:
  - `AUDIT: Course scan start` — logs course ID, title, and URL when a course import begins
  - `AUDIT: Course scan complete` — logs course ID and total content item count after import
  - `AUDIT: Download complete` — logs downloaded/skipped/shortcut counts and output directory
  - `AUDIT: JSON export` — logs course ID and output file path
  - `AUDIT: Excel export` — logs course ID and output directory
- Added `logging.getLogger(__name__)` to `core/content_extractor.py` (previously had no logger)
- Files changed: `core/course_root.py`, `core/content_extractor.py`, `core/downloader.py`

#### Unhandled Error Logging (Medium — M3)
- **All unhandled exceptions now logged with full traceback** — added `log.exception()` to the GUI worker thread (`gui/app.py`), GUI entry point (`canvas_bot.py`), and CLI entry point (`canvas_bot.py`). Previously, the GUI worker thread swallowed exceptions without logging.
- **Global exception hook** — added `sys.excepthook` override in `tools/logger.py` as a safety net for truly uncaught exceptions that bypass all `try/except` blocks.
- Added `logging.getLogger(__name__)` to `gui/app.py` (previously had no logger)
- Files changed: `tools/logger.py`, `gui/app.py`, `canvas_bot.py`

### Bug Fixes
- **Fixed COM initialization on GUI worker thread** — `create_windows_shortcut_from_url()` uses `win32com.client.Dispatch` which requires COM initialization per thread. Added `pythoncom.CoInitialize()` at the start of the GUI worker thread and `CoUninitialize()` in the `finally` block. Fixes `pywintypes.com_error: CoInitialize has not been called` when downloading files from the GUI.
- **Added error handling to download manifest operations** — `config/yaml_io.py` now has a logger and handles `FileNotFoundError` in `read_download_manifest()` (exits cleanly) and `create_download_manifest()` (logs warning).
- Files changed: `gui/app.py`, `config/yaml_io.py`

---

## v1.2.0

### GUI Mode
- **Added graphical user interface** — double-clicking the exe (or running `python canvas_bot.py` with no arguments) now launches a CustomTkinter GUI. Passing CLI arguments continues to use the existing command-line interface.
  - Course Selection: single course ID or batch processing via a `.txt` course list file
  - Output Folders: separate folder pickers for Download, Excel, and JSON output
  - Download Options: checkboxes for include video/audio/image files, include hidden content, flatten folder structure
  - Display Options: print content tree or print full course tree (single course only, mutually exclusive)
  - Run button with validation — disabled until a course input and at least one output folder or display option is set
  - Scrollable log output area with real-time progress display
  - Status bar showing current processing state and configuration check on launch
  - Options organized into two-column layout: Download Options (left) and Display Options (right)
- **Console window hidden in GUI mode** — when launching via the exe, the console window is automatically hidden. If an error occurs before the GUI loads, the console is restored with the traceback displayed.
- **Background threading** — course processing runs in a daemon thread so the GUI stays responsive during imports and downloads.
- **stdout/stderr redirect** — `TextRedirector` class captures all print output and routes it to the GUI log textbox. Includes ANSI escape code stripping (colorama) and carriage return handling for spinner animations.
- **Configuration status check** — the GUI status bar checks for a valid config file and API token on launch via `check_config_status()` in `network/cred.py`, displaying actionable messages if setup is incomplete.
- **New dependency**: `customtkinter`
- Files changed: `gui/__init__.py` (new), `gui/app.py` (new), `canvas_bot.py`, `network/cred.py`

### GUI Configuration Management
- **View Config and Reset Config buttons** — replaced the single Settings button with two buttons in the title bar.
  - "View Config" opens a terminal showing current configuration status (`--config_status`)
  - "Reset Config" opens a dialog with options to reset Canvas API or Canvas Studio credentials, each launching the respective CLI flow in a terminal
- Files changed: `gui/app.py`

### GUI Settings Persistence
- **Settings saved across sessions** — all GUI inputs (course ID, folder paths, checkbox states) are saved to `%APPDATA%\canvas bot\gui_settings.json` when Run is clicked and restored on next launch. Missing or malformed settings files are handled gracefully.
- Files changed: `gui/app.py`

### Window Icon
- **Set application icon** — the `cb.ico` icon is now displayed in the GUI window titlebar and taskbar. Bundled as a data file in the PyInstaller build for the compiled exe.
- Files changed: `gui/app.py`, `build.cmd`, `canvas_bot.spec`

### About Dialog
- **Added About button** to the title bar (`Alt+A`) — opens a scrollable dialog with an overview of Canvas Bot, descriptions of every GUI section (Course Selection, Output Folders, Download Options, Display Options, Configuration), a numbered first-time setup guide, and developer contact info.
- Files changed: `gui/app.py`

### Accessibility
- **Keyboard shortcuts** — `Alt+R` to Run, `Alt+V` to View Config, `Alt+C` to Reset Config, `Alt+A` for About. Shortcuts displayed in button labels.
- **Keyboard focus navigation** — Tab key cycles through all interactive elements. Buttons and checkboxes show a blue focus ring when selected. Enter key activates the focused button or toggles the focused checkbox.
- **Tooltips** — every interactive control (entries, buttons, checkboxes) displays a descriptive tooltip on hover or keyboard focus after a 3-second delay. Tooltips have a white background with rounded corners and a subtle border.
- **Descriptive placeholder text** — all entry fields have detailed placeholder text describing expected input (e.g., "Canvas course ID (e.g. 12345)").
- **Screen reader-friendly labels** — all buttons use descriptive text labels. Error messages reference specific button names.
- **Initial focus** — Course ID field receives focus on launch for immediate keyboard input.
- **Escape to close dialogs** — About and Reset Config dialogs can be dismissed with the Escape key.
- Files changed: `gui/app.py`

### Excel Export Robustness
- **Fixed COM automation for VBA insertion** — replaced `EnsureDispatch` / `Dispatch` cycling with `_get_excel()` helper that tries `EnsureDispatch` first and falls back to clearing the corrupted gen_py cache and retrying. Fixes `AttributeError` on `DisplayAlerts` and stale type library errors.
- **COM thread initialization** — `insert_vba()` now calls `pythoncom.CoInitialize()` / `CoUninitialize()` so Excel COM automation works from the GUI's background thread.
- **Graceful VBA error handling** — `insert_vba()` now catches COM errors and generic exceptions, issuing a warning instead of crashing. Specific detection for the "Trust access to the VBA project object model" Trust Center setting with step-by-step enable instructions.
- **Resilient hyperlink insertion** — `insert_hyperlinks()` skips cells with non-string or invalid URL values instead of raising a COM error.
- **Stale file lock detection** — `save_as_excel()` attempts to remove an existing `.xlsm` before writing. If the file is locked (e.g. by a zombie Excel process), a clear error message is raised instead of an opaque `PermissionError`.
- **Path normalization for GUI paths** — all output paths (download, Excel, JSON) are normalized with `os.path.normpath()` to convert forward slashes from the GUI file picker to backslashes, preventing `PermissionError` on mapped network drives.
- Files changed: `tools/vba_to_excel.py`, `tools/export_to_excel.py`, `core/content_extractor.py`

### Bug Fixes
- **Fixed shortcut creation on UNC paths** — `create_windows_shortcut_from_url()` used `.split(".")` to replace the file extension, which truncated the entire path at the first dot in the server name (e.g., `\\server.domain.edu\...` became `\\server.lnk`). Replaced with `os.path.splitext()` which correctly handles dots in directory names.
- Files changed: `core/downloader.py`

### PyInstaller Build
- **Switched to spec-file build** — `build.cmd` now runs `pyinstaller canvas_bot.spec` instead of passing flags on the command line, preventing the spec file from being regenerated and losing manual edits.
- **Bundled Tcl/Tk for tkinter** — spec file uses `_tkinter.__file__` to locate the correct Python install and bundles the `tcl8.6` and `tk8.6` data directories alongside `collect_all('tkinter')` and `collect_data_files('customtkinter')`.
- **Added `cb.ico` as bundled data** for window icon display in the compiled exe.
- Files changed: `build.cmd`, `canvas_bot.spec`

---

## v1.1

### Simplified Initial Configuration Flow
- **Removed optional config prompts** for `BOX_DOMAIN` and `LIBRARY_PROXY_DOMAIN` from the first-run setup. The config now only asks for the Canvas subdomain (e.g., `sfsu`) and auto-generates all URLs. Both optional fields are silently set to empty strings so regex pattern substitution still works.
- **Removed the multi-step wizard** (Step 1 / Step 2 / edit-to-customize) — replaced with a single prompt for the institution identifier, auto-configured URLs, and a confirm.
- **Removed Box/Library Proxy from `--config_status`** display since they are no longer user-configured.
- Files changed: `canvas_bot.py`

### Warning Collector for Animated Spinners
- **Created `tools/warning_collector.py`** — a `WarningCollector` class that intercepts `warnings.warn()` calls during spinner animations. Warnings are buffered in a thread-safe deque and displayed in a single Error Report block after the entire import completes, preventing network error messages from corrupting the animated spinner display.
  - Max 10 warnings shown; older warnings noted as omitted
  - Full URLs displayed without truncation, each on its own indented line
  - Styled report block with red banner header and warning count
- **Modified `tools/animation.py`** — both the `@animate` decorator and `ProgressAnimation` context manager now install the warning collector before animation starts and uninstall it after the thread joins. Warnings accumulate silently across all import steps.
- **Modified `core/course_root.py`** — flushes the warning collector at the end of `_init_modules_root()`, printing the Error Report block just before "Import Complete".
- Files changed: `tools/animation.py`, `tools/warning_collector.py` (new), `core/course_root.py`

### Cleaned Up API Error Messages
- **Modified `network/api.py`** — network error warnings now show a clean human-readable message instead of raw JSON dicts. Access tokens are stripped from URLs before display.
  - Added `_clean_url()` to remove `access_token` query params from URLs
  - Added `_extract_error_message()` to pull readable messages from Canvas API error responses (e.g., `HTTP 401 - user authorization required` instead of `HTTP 401: {'status': 'unauthenticated', 'errors': [...]}`)
- Files changed: `network/api.py`

### Content Location Shortcuts
- **Added "Content Location" shortcuts to download folders** — when downloading files, a `Content Location.lnk` shortcut is created in each content folder pointing to the Canvas page where the content lives. This lets users navigate directly to the source page for inspection or remediation. Shortcuts are skipped for Module-level content and deduplicated so only one shortcut is created per folder.
- Files changed: `core/downloader.py`

### Security: Safe Folder Deletion
- **Safeguarded `clear_folder_contents()`** — the function now verifies the target folder contains a `.manifest/download_manifest.yaml` file before deleting anything. This ensures only folders created by Canvas Bot can be cleared, preventing accidental deletion of unrelated files.
- Files changed: `core/content_extractor.py`

### Bug Fixes
- **Fixed `resource_nodes/pages.py`** — `@animate('Importing Announcements')` was incorrectly labeling the Pages import spinner. Changed to `@animate('Importing Pages')`.
- **Fixed `resource_nodes/announcements.py`** — added missing manifest registration to `Announcement` class, matching the pattern used by all other resource handler classes (Assignment, Discussion, Quiz, Page, CanvasFolder).

### Canvas Tree Improvements
- **Filtered container nodes from stats** — plural container types (`Modules`, `Assignments`, etc.) no longer appear as separate entries in the Content Summary. Only the individual item counts are shown.
- **Pluralized resource labels in stats** — resource type names now display as plurals (e.g., "Assignments 89" instead of "Assignment 89").
- **Deeper indent for content URLs** — content node URLs are now indented further than resource URLs for clearer visual distinction between the two.
- Removed closed-caption icon print since the captioning detection system is not functional.
- Removed URL labels from tree display to reduce clutter.
- Removed call to deleted `_print_url_legend()` method that was causing an `AttributeError`.
- Files changed: `tools/canvas_tree.py`

### Split Tree Display into Two Modes
- **Replaced `--show_content_tree`** with two new flags:
  - `--print_content_tree` — shows only resource nodes that are ancestors of content. Empty branches (modules, pages, etc. with no content children) are hidden entirely.
  - `--print_full_course` — shows the complete course tree including all resources (previous behavior).
- **Added `show_content_only()` method** to `CanvasTree` — builds a filtered tree copy using `build_path()` from `content_scaffolds.py` to walk ancestor chains. Reuses existing `_format_node_display()`, `_print_header()`, and `_print_statistics()` for display.
- Files changed: `tools/canvas_tree.py`, `canvas_bot.py`

### Hardcoded Version
- **Moved version to `canvas_bot.py`** — version is now defined as `__version__ = "1.1.0"` at the top of the main entry point instead of being read from `config/config.yaml` at runtime. Removed `read_config` import from `canvas_bot.py` and removed the `version` key from `config.yaml`.
- Files changed: `canvas_bot.py`, `config/config.yaml`

### Removed CLI Options
- **Removed `--export_course_list`** and `--semester_filter` — removed the CLI entry points for course list CSV export. The underlying `tools/course_extractor.py` module is unchanged.
- **Removed `--check_video_site_caption_status`** — removed the YouTube caption checking CLI flag. The captioning detection system is not functional.
- Files changed: `canvas_bot.py`

### Security: Token Stripped from Log Output
- **Fixed token leaking to log files** — all `log.*()` calls in `network/api.py` now use `_clean_url()` to strip the `access_token` parameter before writing to disk. Previously only the `warnings.warn()` display was cleaned.
- **Removed duplicate log handler** — `api.py` had its own `RotatingFileHandler` with no formatter (no timestamps) writing to the working directory. Removed it so `api.py` inherits the root logger configured in `tools/logger.py` with proper timestamp formatting.
- Files changed: `network/api.py`

### Fixed Caption Upload Error Path
- **Removed blocking `input()` call** — the error message for missing caption parameters previously called `input()` to pause, which caused `EOFError` in non-interactive contexts. Replaced with `sys.exit(1)`.
- Files changed: `canvas_bot.py`

### EXE Test Harness
- **Created `test/exe_test_harness.py`** — automated test harness that runs the compiled `.exe` (or `canvas_bot.py` in dev mode) with every combination of CLI flags. Tracks pass/fail, exit codes, stdout matching, and timing per test.
  - 64 offline tests: help flags, config status, pattern CRUD/validation/matching across all content types, error handling
  - 20 API tests (when `--course_id` provided): course scan, tree display, download variations (documents, video, audio, image, hidden, flatten, flush), JSON/Excel export, combined outputs, batch processing
  - Grouped by feature area with per-group summary reporting
  - Temp directories for all output, auto-cleaned after run
- **Updated `build.cmd`** — now runs the full offline test harness against the freshly built `.exe` after a successful PyInstaller build. Build stops early on failure instead of falling through.
- Files changed: `test/exe_test_harness.py` (new), `build.cmd`
