# v1.2.2 Plan: Content Viewer + Pattern Manager GUI

## Context

Canvas Bot v1.2.1 has a GUI that only exposes the basic run workflow (course ID, output folders, checkboxes, run button). The CLI has much richer capabilities -- viewing discovered content as structured data and full CRUD over the regex pattern system -- that aren't accessible from the GUI. This plan adds two features:

1. **Content Viewer** -- a persistent browser for all scanned courses within the download folder. Each scan saves `content.json` to the course's `.manifest/` folder. A dropdown lists all available courses; selecting one loads its content into organized tables with clickable URLs.
2. **Pattern Manager** -- view, add, remove, validate, and test regex patterns from `re.yaml` without touching the CLI

**Constraint:** No edits to `core/` or `resource_nodes/` files.

### Content Viewer Data Flow

```
Scan completes
    ↓
Save content.json → {download_dir}/{CourseName} - {CourseID}/.manifest/content.json
    ↓
Content tab scans download_dir for all .manifest/content.json files
    ↓
Dropdown populated: "Biology 101 - 12345", "English 114 - 64634", ...
    ↓
User selects course → JSON loaded into tables
```

No download folder set → Content tab shows "Set a download folder on the Run tab to browse course content."

---

## Files Overview

| File | Action | Purpose |
|------|--------|---------|
| `gui/table_widget.py` | **New** | Reusable ttk.Treeview wrapper with scrollbars, sorting, theming |
| `gui/content_viewer.py` | **New** | ContentViewer class: nested tabs + tables for content data |
| `gui/pattern_manager.py` | **New** | PatternManager class: CRUD, validate, test URL |
| `gui/app.py` | **Modify** | Add CTkTabview, wire new components, parent param on builders |
| `gui/controller.py` | **Modify** | Capture content data after scan, schedule viewer update |
| `gui/widgets.py` | Unchanged | |
| `gui/validation.py` | Unchanged | |
| `canvas_bot.py` | Unchanged | `content_extractor.get_all_content()` already exists |

### Key existing functions to reuse (read-only reference, no edits)
- `config/yaml_io.py`: `read_re(substitute=False)`, `write_re(data)`, `reset_re()`
- `core/content_extractor.py`: `get_all_content()` returns the full content dict
- `sorters/sorters.py`: compiled matchers for test-URL feature; reload via `importlib.reload()`
- `canvas_bot.py:400-536`: existing add/remove/validate/test/reset logic (reference for validation rules)

---

## Phase 0: Infrastructure -- Tabbed Layout

### Step 0.1: Create `gui/table_widget.py`

Reusable `ContentTable` class wrapping `tkinter.ttk.Treeview`.

- Accepts: `parent`, `columns` list (each: `{id, heading, width, stretch?}`), `on_select` callback
- Creates ttk.Treeview + vertical scrollbar inside a CTkFrame
- Applies ttk.Style theming matching CTk appearance mode (dark bg/light text or vice versa)
- Public methods:
  - `populate(rows: list[dict])` -- clear + insert
  - `clear()`
  - `get_selected() -> dict | None`
  - `get_row_count() -> int`
- Column heading clicks toggle ascending/descending sort
- Bind `<<TreeviewSelect>>` to fire `on_select(row_dict)` callback

**Verify:** `from gui.table_widget import ContentTable` -- no errors. Quick test window with sample data renders a table.

---

### Step 0.2: Refactor `gui/app.py` -- CTkTabview with "Run" tab + folder consolidation

- After `_build_title_bar()`, create `self.tabview = ctk.CTkTabview(self.root)` and add a `"Run"` tab
- Add `parent` parameter to `_make_section(title, parent=None)` and all `_build_*` methods
- Move all existing build calls to target `self.tabview.tab("Run")` instead of `self.root`
- Increase window to `900x800`, minsize `700x650`

**Folder consolidation:** Replace the 3-folder Output section with a single folder + checkboxes:

- Remove `var_excel_folder`, `var_json_folder` and their entry/browse widgets
- Rename `var_download_folder` → `var_output_folder`
- Replace `_build_output_folders()` with `_build_output_section()`:
  ```
  Output Folder:  [___________________________] [Browse]

  ☐ Download files   ☐ Export to Excel   ☐ Export to JSON
  ```
- Add `var_download` (BooleanVar), `var_excel` (BooleanVar), `var_json` (BooleanVar)
- `content.json` is always saved to `.manifest/` when output folder is set (no checkbox needed)

**Validation:** Run button enabled when:
- Has course (course ID or course list) AND
- (output folder set + at least one of download/excel/json checked) OR (tree display option checked)

**Settings persistence:** Update `save_settings`/`load_settings` to use the new variable names. Old settings with `download_folder`/`excel_folder`/`json_folder` should migrate gracefully (use `download_folder` or first non-empty as `output_folder`).

**Controller changes (`gui/controller.py`):**
- Update `_run_worker()` to use `var_output_folder` for all three outputs:
  - `bot.download_files(output_folder, **params)` when `var_download` is checked
  - `bot.save_content_as_excel(output_folder, **params)` when `var_excel` is checked
  - `bot.save_content_as_json(output_folder, output_folder, **params)` when `var_json` is checked
- Update `validate_run()` with the new validation logic

**Verify:** Launch GUI. One "Run" tab visible. Single output folder with 3 action checkboxes. Run button enables/disables correctly. Existing keyboard shortcuts work. Settings load/save correctly.

---

### Step 0.3: Add empty "Content" and "Patterns" tab placeholders

- `self.tabview.add("Content")` and `self.tabview.add("Patterns")`
- Placeholder labels in each

**Verify:** Three tabs visible. Clicking each shows its content. "Run" tab still functional.

---

## Phase 1: Content Discovery Viewer (sequential, complete before Phase 2)

### Content Viewer Architecture

The Content Viewer is a **persistent browser** for all previously scanned courses. Data is stored on disk, not just in memory.

**Storage:** `{download_dir}/{CourseName} - {CourseID}/.manifest/content.json`

**UI Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ Course: [▼ dropdown of all scanned courses ] [Refresh]  │
│ ENG 114 - 20 WRITING... (ID: 64634)                    │
│ 87 items: 20 docs, 12 doc sites, 5 videos, ...         │
├─────────────────────────────────────────────────────────┤
│ [Documents] [Videos] [Audio] [Images] [Unsorted]        │
│ ┌─────────────────────────────────────────────────────┐ │
│ │  Table rows...                                      │ │
│ │                                                     │ │
│ └─────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│ Detail: title: ...  url: [clickable]  path: ...         │
└─────────────────────────────────────────────────────────┘
```

No download folder set → shows "Set a download folder on the Run tab to browse course content."

---

### Step 1.1: Save content.json after each scan

In `gui/controller.py`:

- In `_run_worker()`, after `bot.start()` and before download/export, if a download folder is set:
  1. Build the course subfolder path: `{download_dir}/{sanitized_course_name} - {course_id}`
  2. Create `.manifest/` subfolder if it doesn't exist (set hidden attribute on Windows)
  3. Call `bot.content_extractor.get_all_content()` and save as `.manifest/content.json`
- Do this for **every course** in the loop (including batch mode), so each course gets its own `content.json`
- After the loop completes, schedule `self.view.root.after(0, self._on_scan_complete)` to notify the Content Viewer to refresh its dropdown

**Reuse:** The course folder naming convention already exists in `content_extractor.py` line ~844 (`sanitize_windows_filename`). We need the same sanitization logic. Import and use `from tools.export_to_excel import sanitize_windows_filename` or replicate the simple char-replacement.

**Verify:** Run a scan with a download folder set. Check that `{download_dir}/{CourseName} - {CourseID}/.manifest/content.json` exists and contains valid JSON matching the content structure.

---

### Step 1.2: Create `gui/content_viewer.py` -- skeleton with course dropdown

`ContentViewer` class taking `parent_frame` and a reference to the view (for reading `var_download_folder`):

- **Top bar:** CTkOptionMenu (dropdown) listing available courses + "Refresh" button
- **Summary banner:** course name label + stats label (hidden until a course is selected)
- **Nested CTkTabview** with sub-tabs: Documents, Videos, Audio, Images, Unsorted
- **Detail panel** at bottom: CTkTextbox (120px height, Consolas, read-only)

Key methods:
- `refresh_course_list()` -- scans `download_folder` for all subdirectories containing `.manifest/content.json`, populates dropdown with folder names
- `load_course(folder_name)` -- reads `content.json` from that course's `.manifest/`, populates tables
- `clear()` -- resets to empty state

Sub-tab structure:
```
Documents tab → nested tabview: "Documents" | "Document Sites"
Videos tab    → nested tabview: "Video Files" | "Video Sites"
Audio tab     → nested tabview: "Audio Files" | "Audio Sites"
Images tab    → single ContentTable
Unsorted tab  → single ContentTable
```

Column definitions:

| Table | Columns |
|-------|---------|
| Documents | title, file_type, source_page_type, is_hidden, order |
| Document Sites | title, url, source_page_type, is_hidden, order |
| Video Sites | title, url, is_captioned, source_page_type, is_hidden |
| Video Files | title, file_type, class, is_captioned, source_page_type |
| Audio Files | title, file_type, source_page_type, is_hidden |
| Audio Sites | title, url, source_page_type, is_hidden |
| Image Files | title, file_type, source_page_type, is_hidden |
| Unsorted | title, url, source_page_type, is_hidden |

**Verify:** `from gui.content_viewer import ContentViewer` -- no errors.

---

### Step 1.3: Integrate ContentViewer into app + controller

In `gui/app.py`:
- Replace Content tab placeholder with `self.content_viewer = ContentViewer(self.tabview.tab("Content"), self)`
- The view reference lets ContentViewer read `self.view.var_download_folder`

In `gui/controller.py`:
- `_on_scan_complete()` calls `self.view.content_viewer.refresh_course_list()` and auto-switches to Content tab
- If only one course was scanned, auto-select it in the dropdown

Wire the download folder variable: when `var_download_folder` changes, call `content_viewer.refresh_course_list()` so the dropdown updates if the user changes folders.

**Verify:** Set a download folder that already has scanned courses (from previous CLI runs with `--output_as_json` or from Step 1.1). The dropdown should populate. Select a course -- tables fill with data.

---

### Step 1.4: Detail panel with clickable URLs

Wire each ContentTable's `on_select` callback to populate the detail panel:

- Show all fields of selected row as `key: value` lines
- For `url`, `source_page_url` fields: render as clickable links
- URL click opens in default browser via `webbrowser.open(url)`

**Verify:** Click a row in any table. Detail panel shows all fields. Click a URL -- browser opens.

---

### Step 1.5: Summary statistics banner

When a course is loaded, compute counts and display:
```
ENG 114 - 20 WRITING THE FIRST YEAR Spring 2026  (ID: 64634)
87 items: 20 docs, 12 doc sites, 5 videos, 0 audio, 3 images, 47 unsorted
```

Also update each sub-tab title with count, e.g. `"Documents (20)"`.

**Verify:** Compare displayed counts against `test_data/64634.json`. Counts match.

---

### Step 1.6: Auto-refresh after scan + Refresh button

- After a scan completes, the dropdown refreshes and auto-selects the most recently scanned course
- "Refresh" button manually re-scans the download folder (in case courses were added by CLI or another session)
- When download folder is empty or not set, show placeholder message

**Verify:** Run scan. Content tab auto-refreshes dropdown with the new course selected. Click Refresh manually -- same result. Clear download folder field -- Content tab shows placeholder.

---

## Phase 2: Pattern Manager (after Phase 1 is complete)

### Step 2.1: Create `gui/pattern_manager.py` -- skeleton with two-column layout

`PatternManager` class taking `parent_frame`:

- **Left column (30%):** scrollable category list (CTkScrollableFrame with CTkButton per category)
- **Right column (70%):** selected category header + pattern table (ContentTable with columns: `#`, `pattern`) + action buttons
- **Bottom row (spanning both columns):** test URL panel
- Use grid geometry for the two-column layout

**Verify:** Launch GUI, click Patterns tab. Two-column layout renders. Left column empty, right column has placeholder.

---

### Step 2.2: Populate category list from `read_re(substitute=False)`

- Load all categories from `config/yaml_io.py: read_re(substitute=False)`
- Display each as a button/label: `category_name (count)`
- Distinguish list-type vs string-type categories visually (e.g. string types dimmed or marked)
- Track `_selected_category`; highlight selected item

**Verify:** All 19 categories appear. Counts match `--patterns-list` CLI output.

---

### Step 2.3: Display patterns for selected category

When category clicked:
- Populate right-column ContentTable with patterns (index + pattern text)
- Update category header label
- For string-type categories, show single row; disable add/remove buttons

**Verify:** Click `document_content_regex` -- see all patterns. Click `resource_node_re` (string type) -- see single row. Counts match re.yaml.

---

### Step 2.4: "Add Pattern" dialog

Button below pattern table. Opens CTkToplevel dialog:
1. Entry field for new pattern
2. **Inline validation** on typing or on submit: `re.compile(pattern)` -- show error in red if invalid
3. Duplicate check: `pattern in self._patterns_data[category]`
4. On success: append to `self._patterns_data[category]`, call `write_re()` (saves to `%APPDATA%\canvas bot\re.yaml`), refresh table + category count
5. Disabled when string-type category or no category selected

**Verify:** Add `.*\.odt` to `document_content_regex`. Table updates. Confirm via CLI: `python canvas_bot.py --patterns-list document_content_regex`. Remove it after testing.

---

### Step 2.5: "Remove Pattern" with confirmation

Button below pattern table:
1. Get selected row from table
2. Confirmation dialog: "Remove `{pattern}` from `{category}`?"
3. On confirm: remove from `self._patterns_data[category]`, call `write_re()`, refresh table + category count
4. Disabled when no pattern selected or string-type category

**Verify:** Add test pattern, then remove it via GUI. Table updates. Confirm via CLI.

---

### Step 2.6: "Validate" button

Button below pattern table:
1. Get selected pattern
2. `re.compile(pattern, re.IGNORECASE)` -- show result in a status label
3. Report: valid/invalid, group count, flags

**Verify:** Select any pattern, click Validate. "Valid regex" with group count shown. Matches `--patterns-validate` CLI output.

---

### Step 2.7: "Test URL" panel (bottom row)

Panel spanning both columns at bottom:
- Entry field + "Test" button + result label
- On test: `importlib.reload(sorters.sorters)` to pick up any edits saved to AppData, then test input against all compiled matchers
- Show matches in green or "No matches (Unsorted)" in orange

Reload flow:
```python
import importlib
import sorters.sorters
importlib.reload(sorters.sorters)
# Now import fresh matchers
from sorters.sorters import document_content_regex, ...
```

**Verify:**
- `myfile.pdf` → MATCH: document_content_regex
- `https://www.youtube.com/watch?v=abc` → MATCH: web_video_resources_regex
- `https://randomsite.com` → No matches (Unsorted)
- Add a new pattern, then test it WITHOUT restarting -- should match after reload

---

### Step 2.8: "Reset All to Defaults" button

Button at bottom of left column:
1. Confirmation dialog warning about losing custom patterns
2. On confirm: `reset_re()` (deletes AppData file; next `read_re()` recreates from bundled default)
3. Reload `self._patterns_data = read_re(substitute=False)`, refresh category list + pattern table

**Verify:** Add test pattern. Reset. Test pattern gone. All categories at original counts.

---

## Phase 3: Integration Polish

### Step 3.1: Integrate PatternManager into app.py

Replace Patterns tab placeholder with `self.pattern_manager = PatternManager(self.tabview.tab("Patterns"))`.

**Verify:** Full Patterns tab functionality works alongside Run and Content tabs.

---

### Step 3.2: Tab keyboard shortcuts

Add `Ctrl+1/2/3` to switch tabs:
```python
self.root.bind("<Control-Key-1>", lambda e: self.tabview.set("Run"))
self.root.bind("<Control-Key-2>", lambda e: self.tabview.set("Content"))
self.root.bind("<Control-Key-3>", lambda e: self.tabview.set("Patterns"))
```

**Verify:** Ctrl+1/2/3 switch tabs correctly.

---

## Dependency Graph

```
Step 0.1 (table_widget.py)
    ↓
Step 0.2 (tabbed layout)
    ↓
Step 0.3 (placeholder tabs)
    ↓
Step 1.1 (save content.json to .manifest/)
    ↓
Step 1.2 (ContentViewer skeleton + course dropdown)
    ↓
Step 1.3 (integrate viewer + wire dropdown to download folder)
    ↓
Step 1.4 (detail panel + clickable URLs)
    ↓
Step 1.5 (summary stats)
    ↓
Step 1.6 (auto-refresh after scan + Refresh button)
    ↓
Step 2.1 (PatternManager skeleton)
    ↓
Step 2.2 (category list)
    ↓
Step 2.3 (pattern display)
    ↓
Step 2.4 (add pattern)
    ↓
Step 2.5 (remove pattern)
    ↓
Step 2.6 (validate)
    ↓
Step 2.7 (test URL with reload)
    ↓
Step 2.8 (reset defaults)
    ↓
Step 3.1 (integrate PatternManager)
    ↓
Step 3.2 (keyboard shortcuts)
```

All steps are sequential. Each step produces a testable result before moving to the next.

---

## Verification Strategy

After each step: launch the GUI, verify the specific behavior described. At the end of each phase:

- **Phase 0:** GUI launches with 3 tabs, "Run" tab works identically to before
- **Phase 1:** Scan course 64634 with a download folder set. Verify `.manifest/content.json` is created. Content tab dropdown lists the course. Select it -- tables match `test_data/64634.json`. Scan a second course -- dropdown shows both. Close and reopen GUI -- both courses still in dropdown (persistent).
- **Phase 2:** All CRUD operations work, verify against CLI `--patterns-*` commands
- **Phase 3:** All tabs work together, shortcuts work, no regressions
