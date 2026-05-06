# Changelog

## v1.2.3

### Content Visibility
- **Visibility column** — replaced the boolean "Hidden" column in all Content Viewer tables with a single "Visibility" column that shows context-aware labels: **Visible**, **Hidden**, **Unpublished**, or **Locked**. Items with multiple flags show combined labels (e.g. "Unpublished, Locked").
- **Context-aware hidden detection** — files marked `hidden_for_user` or `hidden_from_students` in Canvas but linked from a published page or module are shown as **Visible**, since students can still access them via the link. Only truly inaccessible items are labeled **Hidden**.
- **`hidden_reason` field in JSON export** — every content item in `.manifest/content.json` now includes a `hidden_reason` string listing the specific Canvas API flags that caused the item to be hidden (e.g. `"hidden_for_user"`, `"unpublished"`, `"locked"`, `"hidden_from_students"`). Empty string when visible.
- **Content Visibility section in README** — added a reference table documenting how Canvas API visibility flags and link context map to the Visibility column labels.
- Files changed: `gui/content_viewer.py`, `core/content_scaffolds.py`, `core/utilities.py` (new), `readme.md`

### File Source Identification
- **`file_source` field for documents** — the documents scaffold now includes a `file_source` field: `"Canvas"` for files hosted in Canvas (with an API dict), `"External File"` for files discovered via URL scraping.
- **File Source column** — added a "File Source" column (width 120) to the documents table in the Content Viewer, showing whether each document is a Canvas-hosted file or an external link.
- **`canvas_file_id` field** — documents now include the Canvas file ID in the JSON export for use by the file replace feature.
- Files changed: `core/content_scaffolds.py`, `gui/content_viewer.py`

### File Replace
- **Replace File button** — the Content Viewer now has a "Replace File" button (Alt+R) that uploads a local file to replace the selected Canvas document. Enabled only for Canvas-hosted documents (`file_source == "Canvas"`). Opens a file picker, confirms with the user, then performs a 3-step Canvas API upload (notify → upload → confirm). Shows success/error feedback via message dialog.
- **`replace_file()` API function** — new function in `network/api.py` that handles the Canvas 3-step file replace process: POST to notify Canvas, POST multipart upload, POST to confirm. Handles redirects, error responses, and connection failures with logging and warnings.
- **CLI `--replace_file` option** — replace a Canvas file from the command line without a full course scan. Usage: `Canvasbot.exe --course_id 12345 --replace_file "C:\new_syllabus.pdf" --canvas_file_id 67890`. Requires all three flags. Authenticates, uploads, and exits.
- **Replace picker opens at downloaded file's folder** — clicking Replace File now opens the file picker at the same location the Open File Location button uses (the parent folder of the selected row's `save_path`). Falls back to the system default when the file hasn't been downloaded yet or the folder no longer exists. Mirrors the `os.path.dirname(save_path)` + `os.path.isdir` guard in `_open_file_or_site()`.
- **About dialog documentation** — Replace File (Alt+R) added to the Action Buttons list in the About → Content tab, documenting availability rules and the `(replaced)` title-suffix behavior.
- Files changed: `network/api.py`, `gui/content_viewer.py`, `gui/controller.py`, `canvas_bot.py`, `readme.md`

### Refactoring
- **`core/utilities.py`** — extracted `build_path()`, `is_hidden()`, and `get_hidden_reasons()` from `content_scaffolds.py` into a shared utility module. These tree-traversal and visibility functions are now reusable by any module without importing from the scaffold layer.
- **Removed `is_hidden()` and `build_path()` from `content_scaffolds.py`** — all callers (`content_scaffolds.py`, `downloader.py`, `canvas_tree.py`, `content_nodes.py`) updated to import from `core.utilities`.
- Files changed: `core/utilities.py` (new), `core/content_scaffolds.py`, `core/downloader.py`, `tools/canvas_tree.py`, `resource_nodes/content_nodes.py`, `resource_nodes/base_content_node.py`

### Counting & Summary Centralization
- **`Manifest.content_summary()` / `Manifest.resource_summary()`** — new methods returning a unified `{total, hidden, by_class}` dict. Single source of truth replacing three independent counting implementations across `core/content_extractor.py`, `tools/canvas_tree.py`, and `gui/content_viewer.py`.
- **`is_container` class attribute** — added to all 9 plural container classes (`Modules`, `Pages`, `Assignments`, `Quizzes`, `Discussions`, `Announcements`, `CanvasFiles`, `CanvasMediaObjects`, `CanvasStudio`) so they can be distinguished from per-item nodes (`Module`, `Page`, etc.) that share the same `Node` base.
- **`Manifest.container_classes()`** — derives the set of container-shell class names from the `is_container` flag. Removes the hardcoded class-name set previously baked into `tools/canvas_tree.py`.
- **`summary` block in `content.json`** — `ContentExtractor.get_all_content()` now embeds `summary.content` and `summary.resources` at the top of the manifest JSON. Downstream consumers (currently the GUI) can read counts directly without re-tallying.
- **Content Viewer reads summary from JSON** — `_populate_from_data` now sources total, hidden, and per-type breakdown from `data["summary"]["content"]`. Falls back to live counting for older manifests without the block. The Show Inactive filter no longer affects the summary header — only what's shown in the tables.
- **CONTENT SUMMARY tree printout uses Manifest** — `tools/canvas_tree.py` `_print_statistics` now consumes `manifest.content_summary()` and `manifest.resource_summary()` instead of its own `_stats` dict. Dead `_stats` accumulation in `add_node` and the unused `get_statistics()` method removed.
- Files changed: `core/manifest.py`, `core/content_extractor.py`, `gui/content_viewer.py`, `tools/canvas_tree.py`, `resource_nodes/modules.py`, `resource_nodes/pages.py`, `resource_nodes/assignments.py`, `resource_nodes/quizzes.py`, `resource_nodes/discussions.py`, `resource_nodes/announcements.py`, `resource_nodes/canvasfiles.py`, `resource_nodes/media_objects.py`, `resource_nodes/canvas_studio.py`

### GUI Responsiveness
- **Async replace-permission check** — `ContentViewer._check_replace_permission` no longer blocks the main thread on Canvas's `/permissions` endpoint. Course selection spawns a daemon thread that posts the result back via `after(0, ...)`; cached results stay synchronous. Stale results from rapid course switching are guarded so the wrong course's permission can't enable the Replace File button.
- **HTTP request timeout** — `network/api.py` `response_handler` now passes `timeout=10` to `requests.get`, preventing zombie threads when Canvas is unresponsive.
- Files changed: `gui/content_viewer.py`, `network/api.py`

### GUI Tweaks
- **Smaller checkbox indicators** — all 11 `CTkCheckBox` widgets (Run tab options + Content Viewer filter) reduced from the default 24×24 to 19×19 (~21% smaller). Label text size unchanged.
- **Clearer Download Options labels** — the media-type checkboxes now read "Download video files" / "Download audio files" / "Download image files" instead of "Include …", reflecting that they affect the download step only (all types are scanned regardless). "Include hidden content" → "Include hidden/locked" to cover all four Canvas flags (`hidden_for_user`, `published=False`, `hide_from_students`, `locked`). "Include inactive content" → "Include unlinked" to match how the filter actually works.
- **About dialog Download Options section updated** — the Run tab in the About dialog uses the new label terminology and adds a note clarifying that Hidden/locked and Unlinked are independent filters — a file that is both hidden and unlinked requires both options checked to download.
- Files changed: `gui/app.py`, `gui/content_viewer.py`, `gui/controller.py`

### Scan Freshness & Replace Tracking
- **`scanned_date` field at JSON root** — `ContentExtractor.get_all_content()` now embeds `"scanned_date": "YYYY-MM-DD HH:MM:SS"` at the top of every manifest, so consumers can see when the data was captured.
- **"Last scanned: …" label in Content Viewer** — right-aligned on the filter row alongside Show Inactive. Updates per course; clears when no course is selected.
- **`(replaced)` title suffix on successful Replace File** — appended in-memory and persisted to `content.json` via new `_save_content_json()` helper. Acts as a "rescan me" nudge so users know the local `canvas_file_id` may be stale (Canvas issues a new ID on overwrite, which causes a 404 on subsequent same-row replaces after restart). Suffix is naturally wiped by the next scan, which writes fresh title + ID + URL data from Canvas.
- **`_mark_row_replaced(canvas_file_id)` helper** — finds the matching document row in `_current_data`, appends the suffix (guarded against double-appending), writes back, and re-renders the document table.
- Files changed: `core/content_extractor.py`, `gui/content_viewer.py`

### Streaming Replace + Progress Dialog
- **`gui/network.py` (new)** — GUI-side network module. `replace_file_with_progress(course_id, file_id, local_path, on_progress=None, cancel_event=None)` mirrors `network/api.replace_file`'s 3-step Canvas flow (notify → upload → confirm) but streams the upload via `requests_toolbelt.MultipartEncoderMonitor` so bytes flow from disk to socket without buffering the whole file in memory. Adds tuple timeouts per stage (notify `(10, 30)`, upload `(10, 600)`, confirm `(10, 30)`), byte-level progress callbacks, and cooperative cancel between stages. The CLI `--replace_file` path keeps using the original `network/api.replace_file()`.
- **`requests-toolbelt~=1.0.0`** — new dependency for the streaming multipart encoder.
- **`gui/file_replace.py` (new)** — orchestration module for the GUI replace flow. `start_single_replace(viewer, row)` is the entry point, replacing the inline `_replace_file()` method on the viewer. Pre-flight UI (file picker, type-mismatch dialog, confirm dialog, auth check) runs on the UI thread; the upload runs on a daemon worker thread (`name="canvas-replace"`) so the main window stays responsive. Pure helpers `perform_replace`, `mark_row_replaced`, `save_content_json`, plus the `REPLACED_SUFFIX = " - (replaced)"` constant, were lifted out of `content_viewer.py`.
- **`SingleReplaceProgressDialog`** — small modal (360×130) shown during the replace. Displays `Replacing: <filename>` plus a stage line that ticks `Fetching file info… → Notifying Canvas… → Uploading… 12.4 MB / 47 MB · 26% → Confirming… → Done`. Byte-progress updates throttled to **100 ms minimum** between marshalled `after(0, …)` updates so a fast upload can't queue thousands of UI calls.
- **Cancel button** — wires to a `threading.Event` shared with the network function, which checks it between Canvas stages. Cancelling mid-upload waits for the current upload step to finish (the multipart encoder doesn't expose a clean mid-stream abort, and aborting mid-upload would leave Canvas in a half-uploaded state). The dialog's X button and Escape both route through the same cancel handler. Cancelled replaces skip the `(replaced)` suffix and write a log entry instead of showing a success/failure dialog.
- **`_apply_replaced_to_ui(canvas_file_id)` on the viewer** — small UI-side helper that calls `mark_row_replaced` on the data, syncs `_selected_row`, persists via `save_content_json`, and refreshes the table. Replaces the previous `_mark_row_replaced` method by separating the pure data mutation (now in `gui/file_replace.py`) from the UI side-effects (kept in the viewer).
- Files changed: `gui/network.py` (new), `gui/file_replace.py` (new), `gui/content_viewer.py`, `requirements.txt`

### Bulk Replace
- **Bulk Replace button** — new amber button (Alt+B, `fg_color="#8a6d00"`) in the Content Viewer's action row, packed immediately after Replace File on the Documents sub-table only. Same `pack`/`pack_forget` show/hide rules as Replace File; same `_can_replace AND _current_data` enable rule, plus a guard against opening a second dialog while one is already open. Disables itself while a dialog is active.
- **`BulkReplaceDialog`** — new `CTkToplevel` (720×560, modal, Escape-bound) in `gui/file_replace.py`. Three columns: Title (250 stretch), Local Match (220 stretch), Status (240 anchor center). Header shows `Bulk Replace — {course_name} (ID: {course_id})`. Source-folder bar with **Pick a File…** button (a workaround — Tk's `askdirectory` shows the legacy XP-style tree with no files visible; `askopenfilename` + `os.path.dirname` derivation gets you the modern Windows shell file picker so you can confirm the folder by selecting any file inside it). Counter line and three action buttons (Replace Matched, Ignore, Cancel) round out the layout.
- **Match logic** — case-insensitive exact basename match, **extension-strict**. Documents iterated via `match_files_to_documents(folder, documents)` (new pure helper in `gui/file_replace.py`) bucket into five lists in a `MatchResult` dataclass: `matches`, `unmatched_local`, `unmatched_canvas`, `ambiguous`, `already_replaced`. Local files with non-document extensions (per `re.yaml` `document_content_regex`) are filtered out via the new `is_document_file()` + lazy-cached `get_document_extensions()` helpers. Two local files with the same casefold name → keep the first, log a warning, mark the rest as unmatched. Two Canvas docs with the same casefold title → only flagged as `Ambiguous` when a local file actually collides with that name; otherwise bucketed as `unmatched_canvas` so we don't over-flag.
- **`_STATUS_COLORS` extended** — added `Will replace` (green), `Replacing…` (amber, in-flight), `Done` (green), `Failed` (red), `Skipped`, `No match`, `Already replaced`, `Ambiguous`, `Ignored`, `User File`, `Group File` (all gray) to `gui/table_widget.py`'s tag color table. No collisions with the existing review-status keys (`Passed` / `Needs Review` / `Ignore`).
- **`color_key` parameter on `ContentTable`** — new optional constructor argument that, when set, makes `_row_tag` look up the row's color in that field instead of `status_key`. Lets the displayed Status text vary (e.g. dynamic byte progress) while the row's tag color stays stable. Bulk dialog uses `status_key="bulk_status"` + `color_key="bulk_color"`.
- **Per-row Ignore action** — selected-row toggle that flips `bulk_status` between `"Will replace"` ↔ `"Ignored"`. The Ignore button label flips to `"Don't ignore"` when an Ignored row is selected so it always describes the action the click will perform. Disabled for any other status. Re-picking a folder resets all statuses cleanly — the new match result is the source of truth.
- **`BulkReplaceJob`** — daemon worker thread (`name="canvas-bulk-replace"`) that owns the `cancel_event` and the snapshotted `(canvas_file_id, local_path)` work list. Sequential execution, one file in flight at a time. Per-file flow: marshals `_on_file_starting(cid)` (sets row to amber `Replacing…`) → calls `perform_replace(course_id, cid, local_path, on_progress=…, cancel_event=…)` → marshals `_on_file_complete(cid, status, apply_replaced)` with the right outcome. Successful files trigger `viewer._apply_replaced_to_ui(cid)` so the underlying viewer's title gets the `(replaced)` suffix and persistence happens.
- **Per-file live progress in the table** — `BulkReplaceJob` passes a throttled `on_progress(stage, bytes_read, total)` callback per file. Same 100ms throttle pattern as `start_single_replace` (stage change always emits, otherwise gated on `_PROGRESS_THROTTLE_SEC`). Per-file throttle state lives in a closure dict so each row's progress is independent. The dialog's `_on_file_progress` writes dynamic text (`Fetching… → Notifying… → Uploading 12.4 / 47 MB (26%) → Confirming…`) into `bulk_status` while keeping `bulk_color="Replacing…"` so the row tag stays amber throughout.
- **Cancel button + window-X confirm** — `_close()` checks state. During RUNNING: shows a confirm dialog (`"Cancel bulk replace? The current upload will finish first; remaining files will be skipped."`); on Yes signals cancel and disables the button as `"Cancelling…"`; the dialog stays open until the worker finishes the current file and `_on_job_done` fires. Repeat clicks while a cancel is pending are silent no-ops. Same handler routes Cancel button, X button, and Escape. `_on_job_done` re-enables the button and renames it to `"Close"` for the post-run state.
- **Main-window close warning** — `gui/app.py` `CanvasBotGUI.__init__` now binds `WM_DELETE_WINDOW` to `_on_root_close`, which checks for an active `BulkReplaceJob` on the content viewer's `_bulk_dialog`. When found, prompts (`"A bulk replace is in progress. Quit anyway? The current file will finish; remaining files will be skipped."`); on Yes signals cancel, joins the worker thread with a 30s bounded timeout, then destroys the root.
- **Final summary line** — at DONE state the counter line shows `"Done — A replaced, B ignored, C already-replaced, D failed, E not matched"` using counts snapshotted at Replace-Matched click time (so ignored / already-replaced / not-matched are honest even after rows mutated during the run).
- **About dialog updated** — Bulk Replace (Alt+B) added to the Action Buttons list in the About → Content tab, documenting the matching rules, the User File / Group File handling, and the per-row Ignore behavior.
- Files changed: `gui/file_replace.py`, `gui/content_viewer.py`, `gui/table_widget.py`, `gui/app.py`, `gui/controller.py`, `readme.md`

### User/Group File Scope Tracking
- **Why this exists** — Canvas's file replace endpoint (`POST /courses/{course_id}/files`) only works for files actually in the course. Documents linked from a course page can also live in user-personal storage (`/users/N/files/M`) or group storage (`/groups/N/files/M`); attempting to replace those returns 404. The bulk dialog needed a way to surface and exclude these upfront.
- **`canvas_file_scope_regex` in `re.yaml`** — new pattern `.*\/(courses|users|groups)\/[0-9]+\/files\/.*` that matches against either the data-api-endpoint URL (e.g. `/api/v1/users/90767/files/9134669`) or the regular href (`/users/90767/files/9134669?wrap=1...`). Capture group 1 is the scope token (`courses` / `users` / `groups`); group 2 is the scope ID. Compiled in `sorters/sorters.py` alongside the other URL classifiers and recompiled in `reload_patterns()`.
- **`file_scope` attribute on `BaseContentNode`** — new optional kwarg in `__init__`, defaults to `None`. Stored as `self.file_scope` alongside `is_canvas_file` and `is_canvas_studio_file`. All existing subclasses (Document, DocumentSite, VideoFile, etc.) already forward `**kwargs` to super, so they pick this up for free.
- **Scope extraction at HTML link discovery** — `resource_nodes/base_node.py:add_data_api_link_to_children` now imports `canvas_file_scope_regex` from sorters, runs it against `link[0]` (the data-api-endpoint URL — canonical scope source), captures the scope token into `file_scope`, and passes that to the resulting node's constructor. Files iterated via `CanvasFiles.get_all_items` (the course `/files` endpoint) leave `file_scope=None` since they're course-scoped by definition.
- **`file_scope` field in JSON output** — `core/content_scaffolds.py:document_dict` now emits `"file_scope": getattr(document_node, "file_scope", None)` right after `file_source`. Old `content.json` files without the field default to None on read → treated as course-scoped → no regression.
- **Bulk dialog eligibility split** — `BulkReplaceDialog.__init__` splits eligible documents into `_eligible_docs` (course or unknown scope, replaceable) and `_not_in_course_docs` (`file_scope` is `"users"` or `"groups"`). `_build_initial_rows` gives the not-in-course rows their scope-specific status (`"User File"` or `"Group File"`) from the moment the dialog opens. They surface in the table for visibility but never become matchable, and the existing `_on_row_select` keeps the Ignore button disabled for those statuses.
- Files changed: `config/re.yaml`, `sorters/sorters.py`, `resource_nodes/base_content_node.py`, `resource_nodes/base_node.py`, `core/content_scaffolds.py`, `gui/file_replace.py`, `gui/table_widget.py`

### API Token Validation & Connection Diagnostics
- **`validate_api_token()` in `network/cred.py`** — hits Canvas `/users/self` directly (its own `requests.get` so it can capture the status code) and returns `(ok, message, info)`. On success `info` is a dict of `name`, `id`, `locale`, and `api_path`. Failure messages carry the HTTP status plus Canvas's own error body when available (e.g. `Token rejected (HTTP 401 — Invalid access token.)`), the exception class for network failures (`Could not reach Canvas (ConnectionError)`), or the full exception type+text for unexpected crashes — so users troubleshooting can tell 401 from 500 from a DNS failure at a glance.
- **GUI status bar — async validation on launch** — `controller.check_config()` keeps its sync fast path; on success it shows `"Status: Ready — validating token..."` and spawns a daemon thread (`_validate_token_worker`) that posts the result back via `after(0, _apply_token_validation, ok, message, info)`. No startup blocking. When the async result arrives, the status label becomes `Status: Ready (Connected User Name)` on success or `Status: WARNING — <message>` (amber) on failure — the account identity is visible at a glance to catch "wrong account" surprises.
- **CLI integration** — `check_if_api_key_exists()` validates immediately after a freshly-pasted token is saved (`[OK] Token validated. Connected as <name>.` / `[WARN] Token saved but Canvas check failed: …`). The `--config_status` command gains a **Connection Diagnostics** section at the bottom (renamed from "Live Token Validation") that reports:
  - `Token validity: [OK] Ready` / `[WARN] Token rejected (HTTP 401 — …)`
  - `Connected as: <name>`
  - `User ID: <id>`
  - `Canvas API URL: <api_path>`
  - `Effective locale: <locale>` (when present)
  So the command actually verifies the stored token and surfaces which Canvas instance + user it authenticated as, not just what's stored locally.
- Files changed: `network/api.py`, `network/cred.py`, `gui/controller.py`, `canvas_bot.py`

### Course Permission Summary
- **`_print_permission_summary()` in `core/course_root.py`** — called from `initialize_course()` right after the "Starting import" line, before scanning kicks off. Calls `get_course_permissions(course_id)` and prints one line surfacing the three perms Canvas Bot actually depends on:
  - **Read** = `read_as_admin OR read_as_member`
  - **View Unpublished** = `view_unpublished_items`
  - **Edit Files** = `manage_files_edit`
- Output uses colorama: green `OK` / red `NO` per capability. Falls back to yellow "could not retrieve" if the API call fails (scan continues — benefit of the doubt).
- Writes a structured `AUDIT: Permissions | course_id=X | read=True | view_unpublished=True | edit_files=True` log entry for diagnostic history.
- **Halts the scan when Read is NO** — if both `read_as_admin` and `read_as_member` are False the function prints `[ERROR] No read access to this course. Scan cannot continue.` and returns `False`, and `initialize_course()` skips `_init_modules_root()` so we don't make a cascade of doomed resource fetches. A `AUDIT: Scan halted | reason=no_read_access` entry is logged. View Unpublished NO and Edit Files NO still allow the scan to proceed.
- Files changed: `core/course_root.py`

### Course Load Error Diagnostics
- **Replaced the bare `Course ID: X does not exist` message** with a status-aware diagnostic block. `initialize_course()` now surfaces the Canvas API URL, the HTTP status code, and a short explanation per failure mode, so users can tell the difference between "course truly missing," "wrong Canvas URL," "token rejected," "no permission," and "network down" without opening the log.
- **`get_course_with_status()` in `network/api.py`** — sibling of `get_course()` that returns `(data, status_code, reason)` instead of only the body on success. Bypasses `response_handler` so the HTTP status isn't lost. The existing `get_course()` is untouched (still used by `test/pipeline_testing/`).
- **JSON vs generic 404 distinction** — on HTTP 404, the response body is inspected. A Canvas-style JSON error (`{"errors":[...]}`) sets reason `course_not_found`, while an HTML/empty body (the domain responds but isn't Canvas, or the API path is wrong) sets reason `api_path_invalid`. The diagnostic block then prints one of:
  - `Course not found at this Canvas URL.`
  - `Canvas didn't recognize this URL. Run --reset_canvas_params to re-enter your Canvas subdomain.`
- **Per-status explanations** for 401 ("API token rejected"), 403 ("Token works, but your account doesn't have permission…"), and network failure ("Could not reach Canvas. Check your network connection.") round out the diagnostic. Every block also logs `AUDIT: Course API: X | status=Y | reason=Z` for later review.
- Files changed: `network/api.py`, `core/course_root.py`

### Long-Path Resilience (Shortcut Format Switch)
- **Bug fixed:** scans with deeply-nested module/page names crashed with `pywintypes.com_error -2147024690` (`ERROR_FILENAME_EXCED_RANGE`) when `WScript.Shell.CreateShortCut` tried to write a "Content Location" shortcut at a path > 260 chars. File downloads worked because they use `\\?\` extended-length paths via `create_long_path_file()`, but the COM shortcut API doesn't support that prefix and is stuck at MAX_PATH.
- **Fix:** `create_windows_shortcut_from_url()` in `core/downloader.py` now writes plain INI-formatted `.url` Internet Shortcut files via standard file I/O. Same Windows-recognized format (browser icon, double-click opens URL in default browser), but supports the `\\?\` prefix so MAX_PATH no longer applies. Returns `None` on `OSError` (with a log warning) instead of raising, so a single bad shortcut can't abort the whole download run.
- **Removed dead `import win32com.client`** — was the only call site.
- **Stats check** at `core/downloader.py:605` recognizes both `.lnk` (legacy on-disk) and `.url` (new) extensions so the `Shortcuts:` count stays accurate during incremental scans.
- Files changed: `core/downloader.py`

---

## v1.2.2

### Content Viewer Layout Rearrangement
- **Replaced nested CTkTabview navigation with flat button-based layout** — the Content Viewer now uses a compact 5-row structure: (1) course dropdown bar, (2) summary / category selectors / status buttons, (3) filter bar, (4) table, (5) action buttons. Removes two levels of tab nesting (main tabs + sub-tabs) in favor of a single row of category buttons with swappable sub-category buttons beneath.
- **Two-level selector buttons** — top row shows 5 main categories (Documents, Videos, Audio, Images, Unsorted); bottom row shows sub-categories that change when the main category is selected (e.g. Documents → "Documents" | "Document Sites"). Only one table is visible at a time.
- **Status buttons moved to Row 2** — Passed, Needs Review, and Ignore buttons are now stacked vertically in a right-aligned column alongside the selectors, separated by 1px vertical dividers.
- **Three-column Row 2 with visual separators** — Row 2 uses a 30/40/30% grid layout with 1px vertical lines between the course summary, selector buttons, and status buttons. Adapts to light/dark mode.
- **Action buttons moved below table** — Open File Location, Open File, and Open Source Page buttons are now in Row 5 beneath the table instead of sharing a row with the status buttons.
- **Keyboard navigation updated** — Left/Right arrows navigate category and sub-category buttons. Down/Enter from a category button focuses its first sub-button. Enter from a sub-button focuses the table. Escape from table returns to the sub-button; Escape/Up from sub-button returns to the category row.
- **Open in Canvas button** — opens the course Files page (`{course_url}/files`) in the default browser for bulk file management. Located in the top bar alongside Open Folder. Alt+C shortcut.
- **Open File button** — opens the selected downloaded file directly in its default application via `os.startfile()`. Enabled only when the file exists on disk. Alt+P shortcut.
- Files changed: `gui/content_viewer.py`, `gui/app.py`

### Table Widget Improvements
- **Wider vertical scrollbars** — scrollbar width and arrow size increased to 24px for easier grabbing.
- **Removed horizontal scrollbars** — bottom scrollbars removed from all content tables.
- **Status button colors match table row colors** — Passed (green #2d6a2d), Needs Review (amber #8a6d00), and Ignore (gray #555555) button colors now correspond to their row highlight colors.
- Files changed: `gui/table_widget.py`, `gui/content_viewer.py`

### GUI Tabbed Layout
- **Reorganized GUI into three tabs** — the main window now uses a `CTkTabview` with **Run**, **Content**, and **Patterns** tabs. All existing controls (course selection, output, options, run button, log area) are under the Run tab. Window enlarged to 900x800 with 700x650 minimum.
- **Consolidated output folders** — replaced three separate folder pickers (Download, Excel, JSON) with a single Output Folder and a Download files checkbox. Old settings are migrated automatically.
- **Removed Excel and JSON export options** — the GUI no longer exposes Export to Excel or Export to JSON checkboxes. The internal `.manifest/content.json` save for the Content Viewer is unaffected. CLI flags (`--output_as_excel`, `--output_as_json`) remain available.
- **Reframed as a bridge** — Canvas Bot is now described as a "bridge between Canvas LMS and your desktop" throughout the GUI (title bar subtitle, About dialog, welcome dialog).
- **Tabbed About dialog** — the About window now has four tabs: About (intro, getting started, contact), Run (course selection, output, options), Content (content viewer guide), and Patterns (pattern manager guide).
- **Compact options layout** — Download Options and Display Options checkboxes now use a 2-column grid within each section (3x2 and 1x2), reducing the options area height and giving the console output more vertical space.
- **Tab keyboard shortcuts** — `Ctrl+1/2/3` switch between Run, Content, and Patterns tabs.

### Content Viewer (Content Tab)
- **Added Content Viewer** — a persistent browser for all previously scanned courses. Scans the output folder for `.manifest/` JSON files and populates a course dropdown.
- **Course dropdown with auto-refresh** — lists all scanned courses by folder name. Automatically refreshes after a scan completes or when the output folder changes. Manual Refresh button available.
- **Organized content tables** — content displayed in nested sub-tabs: Documents (Documents | Document Sites), Videos (Video Sites | Video Files), Audio (Audio Files | Audio Sites), Images, and Unsorted. Each table supports column-header sorting.
- **Summary banner** — shows course name, ID, and item counts (e.g., "87 items: 20 docs, 12 videos, 3 images, 47 unsorted").
- **Detail panel** — clicking a row shows all fields in a read-only panel with clickable URLs that open in the default browser.
- **Downloaded column** — document, video, audio, and image file tables show whether each file exists at its expected download path. Paths are normalized to handle mixed separators.
- **Open Folder button** — opens the selected course's folder in the file explorer.
- **Open File Location button** — opens the folder containing the selected file's download path.
- **Open Source Page button** — opens the Canvas source page URL for the selected item in the default browser.
- **Context-aware placeholder messages** — shows different messages when no output folder is set, when the folder is not accessible (e.g., disconnected network drive), or when no scanned courses are found.
- **Automatic content.json persistence** — every scan saves content data to `{course_folder}/.manifest/{course_id}.json` for later browsing without re-scanning.

### Pattern Manager (Patterns Tab)
- **Added Pattern Manager** — full GUI for managing regex patterns from `re.yaml`. Two-column layout: scrollable category list on the left, pattern table with action buttons on the right, test URL panel spanning the bottom.
- **Category list** — displays all pattern categories from `read_re(substitute=False)` with item counts. String-type categories (e.g., `resource_node_re`) are visually dimmed; list-type categories are fully interactive. Selected category is highlighted.
- **Category visibility filter** — a `_CATEGORY_VISIBILITY` dictionary controls which categories appear in the GUI. Internal categories (`resource_node_re`, `resource_node_types_re`, `canvas_user_file_content_regex`, `canvas_file_content_regex`) are hidden by default. Hidden categories still function in the pipeline.
- **Pattern display** — selecting a category populates a `ContentTable` with numbered patterns. String-type categories show a single read-only row with add/remove disabled. Patterns with `{PLACEHOLDER}` tokens (e.g., `{CANVAS_DOMAIN}`) are displayed with substituted values (e.g., `sfsu`) for readability; writes use the raw tokens.
- **Add Pattern** — opens a dialog with inline regex validation (`re.compile`) and duplicate checking. On success, appends to the category and saves via `write_re()`.
- **Remove Pattern** — confirmation dialog before removing the selected pattern from the category and saving.
- **Validate** — compiles the selected pattern with `re.IGNORECASE` and reports valid/invalid, group count, and flags in a status label.
- **Test URL** — enter a URL or filename and test against all compiled matchers. Uses `importlib.reload(sorters.sorters)` to pick up unsaved edits. Shows matches in green or "No matches (Unsorted)" in orange. Enter key triggers test.
- **Reset All to Defaults** — confirmation dialog, then calls `reset_re()` to delete the user's AppData copy. Next load recreates from the bundled default.

### Expanded Default Patterns
- **Document patterns** — added 9 accessibility-relevant file types to `document_content_regex`: `.odt`, `.odp`, `.ods`, `.key`, `.numbers`, `.pub`, `.epub`, `.xps`, `.7z`.
- **Video site patterns** — added 47 new patterns to `web_video_resources_regex` covering enterprise platforms (Panopto, Kaltura, YuJa, Wistia, Brightcove, Echo360), education streaming (Kanopy, Docuseek, Swank, PBS, Khan Academy), screen recording (ScreenPal, Screencast-O-Matic), collaboration (Flipgrid/Flip, Vidyard, Loom), social media (Twitch, Instagram Reels, LinkedIn Video, Facebook Watch, TikTok), enterprise (Microsoft Stream, Google Drive preview, Bunny Stream CDN), and more (Rumble, Odysee, BitChute, PeerTube, Streamable, C-SPAN).
- **Institution-specific video patterns** — populated `institution_video_services_regex` (previously empty) with 12 `{CANVAS_DOMAIN}`-prefixed patterns for platforms that use institution subdomains: Panopto, Kaltura, YuJa, Echo360, Kanopy, ShareStream, Ensemble, and ScreenPal.

### Active Content Filtering
- **`--include_inactive_content` CLI flag** — by default, downloads now skip files that are not linked from any active Canvas page (i.e., `get_source_page_url()` returns falsy). Pass `--include_inactive_content` to override and download everything. Defaults to active-only to download the least number of files and those most useful.
- **"Include inactive content" GUI checkbox** — added to the Download Options column on the Run tab. Setting is persisted across sessions.
- **Content Viewer filter bar** — added a "Filters" row between the summary banner and content tabs with a "Show Inactive Content" checkbox (default off). When off, rows without a `source_page_url` and rows with `is_hidden: true` are hidden from all tables. Toggling re-populates tables instantly without reloading from disk.
- Files changed: `canvas_bot.py`, `gui/app.py`, `gui/controller.py`, `gui/content_viewer.py`, `core/downloader.py`

### Reusable Table Widget
- **Created `gui/table_widget.py`** — `ContentTable` class wrapping `ttk.Treeview` with vertical and horizontal scrollbars, column-header click sorting with arrow indicators, alternating row colors, and automatic dark/light theme matching via CTk appearance mode.

### Module Anchor URLs
- **Improved source page URLs for Module content** — `get_source_page_url()` in `core/content_scaffolds.py` now constructs `{course_url}/modules#{module_id}` when content lives inside a Module (which has no direct `html_url`). This creates an anchor link that scrolls directly to the correct module on the Canvas modules page, instead of linking to the generic modules listing.
- Files changed: `core/content_scaffolds.py`

### Accessibility & Usability
- **Focus rings and tooltips** — all interactive elements on the Content and Patterns tabs now show a blue focus ring on keyboard navigation and display descriptive tooltips on hover/focus, matching the Run tab's accessibility features.
- **Content tab auto-refresh** — switching to the Content tab automatically refreshes the course list, ensuring the dropdown reflects any new scans without needing to click Refresh manually.

### Content Viewer Improvements
- **Downloaded column shows download date** — the "Downloaded" column in file tables now displays the actual download date (from the date-stamped folder on disk) instead of "Yes". Shows "No" when the file is not found. Uses glob-based search across date folders so files downloaded on previous days are correctly detected.
- **Empty table placeholders** — tables with no content now display a "No {Content Type} Found" message instead of an empty table. Scrollbars are hidden when the placeholder is shown.
- **Image title fallback** — image file rows now display `file_name` in the Title column when `title` is empty.
- **Removed captioning column** — removed the "Captioned" column from the Video Sites table as the captioning detection system is not functional.
- **Review status categorization** — content items can now be marked as "Passed", "Needs Review", or "Ignore" for accessibility auditing workflows. Three status buttons in the action bar (right-aligned). Status is persisted per course in `.manifest/review_status.json`, keyed by URL — all instances of the same URL share one status. Unreviewed items display "-". Easily expandable by adding values to `_REVIEW_STATUSES`.
- **Status-based row coloring** — table rows are colored by review status: light green for Passed, light orange for Needs Review, light grey for Ignore. Unreviewed rows use the default alternating background. Colors adapt to dark and light modes.
- **Column border separators** — subtle groove-style borders between column headings for visual clarity.
- **Title truncation for file tables** — long titles in downloadable content tables (documents, video files, audio files, image files) are truncated with ".." when exceeding 60 characters. Full title remains visible in the detail panel.
- **Order column restored** — all content tables now show an "Order" column (first column, compact width) displaying the item's position (0–100) within the course. Sorting is numeric-aware so 2 sorts between 1 and 12.
- **Course selection persists across tab switches** — switching away from the Content tab and back no longer resets the course dropdown to the first entry; the previous selection is preserved if it still exists.
- Files changed: `gui/content_viewer.py`, `gui/table_widget.py`

### Robust File Type Detection
- **Centralized `get_file_type()` helper** — replaced inconsistent inline `file_type` logic in 4 scaffold functions (`document_dict`, `video_file_dict`, `audio_file_dict`, `image_file_dict`) with a single `get_file_type(node)` function using a 7-step fallback chain: `display_name` extension, `file_name` extension, URL-decoded `filename` extension, `mime_class`, `mime_type` lookup, `title` extension, URL path extension. Previously, some functions only checked `mime_class` or `mime_type`, causing missing or inconsistent `file_type` values in exports.
- Files changed: `core/content_scaffolds.py`

### Stability
- **OSError handler for disconnected drives** — `core/downloader.py` now catches `OSError` during file writes (e.g., network drive disconnected mid-download) and exits cleanly with a message and `SystemExit(1)` instead of an unhandled traceback.
- **Pattern Manager placeholder substitution fix** — `load_config_data_from_appdata()` is now called when the Pattern Manager loads, ensuring `{CANVAS_DOMAIN}` and other placeholder tokens are substituted with actual values (e.g., `sfsu`) in the GUI display. Previously, env vars were only populated during course processing, causing raw `{CANVAS_DOMAIN}` tokens to appear in the Patterns tab.
- **Regex pattern reloading after config load** — added `reload_patterns()` to `sorters/sorters.py` that recompiles all regex patterns with current environment variables. Called automatically before each scan run. Previously, patterns with domain placeholders (`{CANVAS_STUDIO_DOMAIN}`, `{CANVAS_DOMAIN}`, `{BOX_DOMAIN}`) were compiled at module import time before config was loaded, so they contained literal placeholder text and never matched. This caused Canvas Studio embeds, Canvas media embeds, and Box links to be classified as Unsorted.
- **Canvas Studio downloads use correct URL** — the downloader now uses `download_url` (the DRM video stream URL) for Canvas Studio embeds instead of `url` (the Studio page URL). Previously, Studio video downloads would fail or create shortcuts because the page URL is not a direct file download.
- **Fixed `is_hidden()` only checking the first node** — `return False` was indented inside the `for` loop, causing the function to return after checking only the leaf node instead of walking the entire ancestor chain. Content inside a hidden or unpublished module/page now correctly reports `is_hidden: True`.
- Files changed: `core/downloader.py`, `gui/pattern_manager.py`, `sorters/sorters.py`, `core/node_factory.py`, `resource_nodes/content_nodes.py`, `gui/controller.py`, `core/content_scaffolds.py`

### Code Signing
- **Executable is now code-signed** — the PyInstaller `.exe` is signed with an SSL.com Individual Validation (IV) code signing certificate via eSigner cloud signing. Publisher displays as **Daniel Fontaine** in Windows prompts and Properties → Digital Signatures.
- **Timestamped signatures** — signatures include an RFC 3161 timestamp from SSL.com's TSA, so the signature remains valid after the certificate expires.
- **SHA256 checksums** — each release includes a SHA256 hash for download verification (`certutil -hashfile CanvasBot.exe SHA256`).
- **License changed to CC-BY-NC-4.0** — replaced MIT with Creative Commons Attribution-NonCommercial 4.0 International.
- Files changed: `readme.md`, `LICENSE` (new), `gui/controller.py`

### Internal
- **MVC refactor** — GUI split into `gui/app.py` (view), `gui/controller.py` (controller), and `gui/widgets.py` (shared widgets). Controller handles settings persistence, validation, run logic, and about dialog.
- **`create_download_manifest()` now returns the manifest directory path** for reuse by callers.
- Files changed: `gui/app.py`, `gui/controller.py` (new), `gui/widgets.py` (new), `gui/table_widget.py` (new), `gui/content_viewer.py` (new), `gui/pattern_manager.py` (new), `config/re.yaml`, `config/yaml_io.py`, `core/content_scaffolds.py`, `core/downloader.py`

---

## v1.2.1

### SOC 2 Remediation — Logging & Security Hardening

#### Credential Store Migration (High — H1)
- **Moved API tokens from `os.environ` to a private credential store** — `ACCESS_TOKEN`, `CANVAS_STUDIO_TOKEN`, and `CANVAS_STUDIO_RE_AUTH_TOKEN` are now stored in a module-level `_credentials` dict in `network/cred.py` with getter functions (`get_access_token()`, `get_studio_token()`, `get_studio_refresh_token()`). Tokens are no longer visible to child processes, debugging tools, or any code reading `os.environ`.
- Files changed: `network/cred.py`, `network/api.py`, `network/studio_api.py`

#### Shell Injection Prevention (High — H1)
- **Removed `shell=True` from GUI subprocess calls** — `_launch_cli()` in `gui/app.py` now uses an argument list with `subprocess.CREATE_NEW_CONSOLE` instead of `shell=True` with string formatting, preventing shell injection and environment leakage to child processes.
- Files changed: `gui/app.py`

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

#### Course ID Input Validation (Low — L2)
- **Added numeric validation for course IDs** — both CLI (`--course_id`) and GUI validate that course IDs are numeric before making API calls. Batch course list files (`--course_id_list`) skip invalid entries with per-line warnings. Blank lines in course list files are silently ignored.
- Files changed: `canvas_bot.py`, `gui/app.py`, `gui/validation.py` (new)

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
