# Changelog

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
