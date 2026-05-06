# Bulk Replace — Phase 3 of the file-replace work

> **Project-rooted backup** of the plan at `~/.claude/plans/ok-lets-discuss-the-cuddly-teapot.md`.
> This file is checked into the repo so the plan survives Claude session resets, plan-file overwrites,
> or `.claude/` directory loss. Last sync: 2026-05-03, after step 3.5 was implemented and the
> deferred user/group scope-tracking refactor was designed.

## Context

The Content Viewer's single Replace File button is now production-ready (Phase 1 + 2 of `curried-prancing-melody.md` shipped: `gui/network.py` with streaming + progress, `gui/file_replace.py` with worker thread + `SingleReplaceProgressDialog` + cancel). The remaining work is **Phase 3: Bulk Replace** — let users point at a local folder of revised documents, match them by filename to the course's existing Canvas documents, and replace them in one orchestrated operation.

This plan refines `curried-prancing-melody.md`'s Phase 3 to reflect what already exists in the codebase, locks in the small open questions, and lays out the 8 implementation steps as concrete file changes.

## What's already in place (Phase 1 + 2)

Helpers and patterns that bulk replace will reuse — verified to exist in the working tree:

- `gui/network.py` — `replace_file_with_progress(course_id, file_id, local_path, on_progress=None, cancel_event=None)`. Streams the upload, fires byte-level callbacks, checks `cancel_event` between Canvas's three stages.
- `gui/file_replace.py`:
  - `perform_replace(...)` — auth bootstrap + delegate to network layer.
  - `mark_row_replaced(current_data, canvas_file_id) -> bool` — pure data mutation.
  - `save_content_json(json_path, current_data)` — disk persistence.
  - `_format_bytes(n)` — "12.4 MB" formatter.
  - `REPLACED_SUFFIX = " - (replaced)"`.
  - `_PROGRESS_THROTTLE_SEC = 0.1`.
  - `SingleReplaceProgressDialog` — reference for modal layout (`transient` + `grab_set`, `WM_DELETE_WINDOW` to cancel handler, Escape binding).
  - `start_single_replace(viewer, row)` — reference for daemon-thread orchestration with throttled `parent.after(0, ...)` updates.
- `gui/content_viewer.py`:
  - `_apply_replaced_to_ui(canvas_file_id)` — viewer-side helper that calls `mark_row_replaced` + `save_content_json` + refreshes the documents table. Bulk will call this once per successful file.
  - `_can_replace`, `_replace_file_btn`, `_check_replace_permission_async` — bulk button reuses the same permission gate.
  - Action button row at lines 417–466. The Bulk Replace button slots in **after `_replace_file_btn`** (line 448) and **before `_open_canvas_btn`** (line 458). Same `pack`/`pack_forget` gating as the Replace File button (visible only when the documents sub-table is active — see content_viewer.py:583–586).
- `gui/table_widget.py`:
  - `ContentTable` — fully reusable inside a `CTkToplevel`. Constructor signature: `ContentTable(parent, columns, on_select=None, placeholder="", status_key=None)`. Public API includes `populate(rows)`, `update_row(idx, row)`, `get_selected()`, `get_selected_index()`, `get_row(idx)`.
  - Color tagging: when `status_key` is set, `_row_tag` looks up `row[status_key]` in module-level `_STATUS_COLORS` (table_widget.py:33) and applies a `status_<value>` tag with the configured background. We extend that dict with bulk-specific values rather than touch the constructor.
- `config/re.yaml` — `document_content_regex` lists 24 extensions: `pdf, docx, ppt, pptx, doc, csv, rtf, pages, rar, xlsx, txt, zip, xls, odt, odp, ods, key, numbers, pub, epub, xps, 7z, srt, vtt`. No existing parser; bulk added one in `gui/file_replace.py`.
- `core/content_scaffolds.py:134–154` — document row schema includes `canvas_file_id` and `file_source` ("Canvas" | "External File") — the gate fields for bulk eligibility.

## Locked design decisions

Mostly inherited from `curried-prancing-melody.md`; flagging the few that needed pinning down after Phase 2 landed:

| Decision | Choice | Rationale |
|---|---|---|
| Match logic | Case-insensitive exact basename match, **extension-strict** | Mirrors the single-replace gate in `replace_file_with_progress` |
| Local folder scan | Flat (no recursion) | One folder = one batch; recursion is a later "if anyone asks" |
| Local extension filter | From `re.yaml` `document_content_regex` | Single source of truth |
| Eligibility gate | `file_source == "Canvas"` AND `canvas_file_id` present AND title doesn't end with `REPLACED_SUFFIX` | Matches single-replace's button-enable rule |
| Ambiguity | Two Canvas docs with the same casefold title → both skipped, status "Ambiguous" — only when there's a local file colliding with that name. Duplicate Canvas titles with no local counterpart bucket as `unmatched_canvas` instead. | Don't guess; don't over-flag |
| Execution | Sequential, one in-flight | Avoids hammering Canvas; matches single-replace UX |
| Bulk button color | Amber `#8a6d00` | Flags destructive scope; same amber used elsewhere for "Needs Review" |
| Bulk button placement | Action button row, between `_replace_file_btn` and `_open_canvas_btn` | Per existing plan |
| Status row colors | Add `Will replace` / `Replacing…` / `Done` / `Failed` / `Skipped` / `No match` / `Already replaced` / `Ambiguous` / `Ignored` to `_STATUS_COLORS` (table_widget.py:33) | No overlap with existing review statuses; avoids refactoring ContentTable |
| Bulk dialog table `status_key` | `"bulk_status"` (separate field, not the review `status`) | Keeps bulk state independent from review state |
| Cancel granularity | Between files, plus the existing between-stage check inside `replace_file_with_progress` | Same trade-off as single replace: a cancel during an upload waits for that upload to finish |
| Modality | Modal (`transient` + `grab_set`) | Prevents accidental other actions during writes |
| Main-window close during a job | Patch `WM_DELETE_WINDOW` on the root to confirm | Per existing plan |
| Per-row Ignore action | Dedicated **Ignore** button in the dialog's action row, acts on the currently-selected row. Toggles `bulk_status` between `"Will replace"` and `"Ignored"`. Mirrors the Content Viewer's Pass/Needs Review/Ignore pattern (button operates on selected row, single-click toggles state, row tag updates). | User wants a way to keep the local file in the folder but exclude it from the run — common when a folder has 30 revised PDFs but two of them shouldn't go up. |
| Folder picker | `tkinter.filedialog.askopenfilename` + `os.path.dirname` derivation. User picks any file in the target folder; we extract the parent directory. | Tk's `askdirectory` is the legacy XP-style tree (no files visible). The native `IFileOpenDialog + FOS_PICKFOLDERS` picker (modern look) shows folders only — files aren't visible inside. The askopenfilename workaround is the only option that gives both modern chrome AND file visibility. The native picker is implemented in `gui/native_dialogs.py` for future reuse where file visibility doesn't matter. |

## Architecture

Two new modules' worth of code, all going into the existing `gui/file_replace.py` (no new files needed for the dialog itself):

- **Pure helpers** (no UI, no threads):
  - `get_document_extensions() -> set[str]` — lazy-load + cache from `re.yaml`.
  - `is_document_file(local_path: str) -> bool`.
  - `match_files_to_documents(folder, documents) -> MatchResult`.
  - `MatchResult` — `@dataclass` with fields `matches: list[tuple[dict, str]]`, `unmatched_local: list[str]`, `unmatched_canvas: list[dict]`, `ambiguous: list[dict]`, `already_replaced: list[dict]`.
- **`BulkReplaceJob`** — owns the worker thread and `cancel_event`. Methods: `start()`, `cancel()`, `is_running()`. Posts per-row updates via `parent.after(0, ...)`.
- **`BulkReplaceDialog`** — `CTkToplevel` containing header / source-folder bar / counter line / `ContentTable` / action buttons (Replace Matched, **Ignore**, Cancel). Owns its `BulkReplaceJob`. Same `transient` + `grab_set` + `protocol("WM_DELETE_WINDOW", ...)` pattern as `SingleReplaceProgressDialog`. Tracks "ignored" via the row's `bulk_status` field — no separate set needed.
- **`start_bulk_replace(viewer)`** — entry point invoked by the new button.

State machine inside `BulkReplaceDialog`: **INIT → MATCHED → RUNNING → DONE**, with the buttons-by-state matrix from the original plan. Cancel button label and behavior swap per state.

Per-row progress in the Status column reuses the same throttle pattern from `start_single_replace` (100ms minimum between marshals, stage changes always emitted), but each in-flight row gets its own throttle state since they're reported sequentially.

## Files to modify

- **`gui/file_replace.py`** — add helpers, `BulkReplaceJob`, `BulkReplaceDialog`, `start_bulk_replace`. ~300 lines added.
- **`gui/content_viewer.py`** — add `_bulk_replace_btn` to the action button row, mirror the documents-only `pack`/`pack_forget` gating from `_replace_file_btn`, mirror the enable-disable logic from the `_can_replace AND data` check. Wire callback to `start_bulk_replace(self)`.
- **`gui/table_widget.py`** — extend `_STATUS_COLORS` with the bulk-specific keys (dark + light values).
- **`gui/native_dialogs.py`** — new file housing the native Windows folder picker (kept dormant; not currently wired into bulk dialog because it shows folders only). See "Native folder picker" below.

No changes to: `network/api.py`, `gui/network.py`, `core/*`, `config/*`.

## Native folder picker (dormant — kept for future use)

### Why a separate module

`tkinter.filedialog.askdirectory` on Windows uses the legacy "Browse for Folder" tree dialog (folders only, XP-era look) — clashes with the rest of the GUI. `askopenfilename` is the modern Windows shell dialog but it's a file picker, not a folder picker. The Vista+ `IFileOpenDialog` COM interface with the `FOS_PICKFOLDERS` flag is a true folder picker that uses the SAME modern shell dialog as `askopenfilename` — but it shows folders ONLY in the content pane (no files visible). For the bulk-replace flow, file visibility for "am I in the right folder?" confirmation is the load-bearing UX requirement, so we reverted to the askopenfilename + os.path.dirname workaround. The native picker module stays in tree for future flows where file visibility doesn't matter (e.g. picking an output folder).

### File: `gui/native_dialogs.py`

Pure stdlib (`ctypes`) — no `comtypes`/`pywin32` dependency for this call (both are in `requirements.txt` already, but `comtypes` is heavy for a single COM call and `pywin32`'s `IFileDialog` wrapper is incomplete).

**Public API:**

```python
def pick_folder(parent=None, initial_dir=None, title=None) -> str | None:
    """Show the native Windows folder picker (Vista+ IFileOpenDialog with
    FOS_PICKFOLDERS). Returns the chosen folder path, or None on cancel.

    Falls back to tkinter.filedialog.askdirectory on non-Windows or any
    failure inside the COM plumbing (logged as a warning, not raised).
    """
```

**Win32 plumbing (ctypes against `ole32.dll`):**

- Constants: `CLSID_FileOpenDialog`, `IID_IFileOpenDialog`, `IID_IShellItem`, `FOS_PICKFOLDERS`, `FOS_FORCEFILESYSTEM`, `FOS_NOCHANGEDIR`, `SIGDN_FILESYSPATH`.
- ole32 functions: `CoInitialize`, `CoUninitialize`, `CoCreateInstance`, `SHCreateItemFromParsingName`.
- Vtable structures via `ctypes.Structure` + function pointer types for `IFileOpenDialog` and `IShellItem`.
- Sequence: `CoInitialize` → `CoCreateInstance(CLSID_FileOpenDialog)` → `SetOptions(FOS_PICKFOLDERS | FOS_FORCEFILESYSTEM | FOS_NOCHANGEDIR)` → optionally `SetFolder(initial_dir as IShellItem)` → optionally `SetTitle` → `Show(parent_hwnd)` → on success: `GetResult` → `IShellItem.GetDisplayName(SIGDN_FILESYSPATH)` → string → release everything → `CoUninitialize` → return path.
- All failures (HRESULT != S_OK except `HRESULT_FROM_WIN32(ERROR_CANCELLED)` which is a clean cancel) → fall back to `askdirectory` and log.

**Fallback** triggered by:
- `sys.platform != "win32"`
- Any exception during the COM calls (with `log.warning(..., exc_info=True)`).

The cancel path (HRESULT 0x800704C7) returns `None` directly, no fallback prompt.

## Implementation steps

Same 8-step structure as `curried-prancing-melody.md`, with concrete file edits per step. Each step is independently verifiable; pause for verification before moving on.

### Step 3.1 — Pure helpers + new color tags ✅ DONE

- `gui/file_replace.py`: `MatchResult` dataclass, `get_document_extensions()`, `is_document_file()`, `match_files_to_documents()`.
- `gui/table_widget.py`: extended `_STATUS_COLORS` with `Will replace`, `Done`, `Failed`, `Skipped`, `No match`, `Already replaced`, `Ambiguous`, `Ignored` (and `Replacing…` later in step 3.5).
- Bug fix during 3.4: ambiguous Canvas-side duplicates only flagged when a local file actually collides with them; otherwise bucketed as `unmatched_canvas`.

### Step 3.2 — Add the Bulk Replace button ✅ DONE

- `gui/content_viewer.py`: new `_bulk_replace_btn` (amber `#8a6d00`, Alt+B), packed after `_replace_file_btn` on the documents sub-table only, mirrors the same show/hide and enable/disable gating.
- `_update_bulk_replace_btn_state()` helper gates on `_can_replace AND _current_data AND not _bulk_dialog`.

### Step 3.3 — Dialog skeleton (INIT state only) ✅ DONE

- `gui/file_replace.py`: `BulkReplaceDialog` class. `CTkToplevel` 720×560, modal, Escape-bound. Header / folder bar / counter line / `ContentTable` (3 columns: Title, Local Match, Status; `status_key="bulk_status"`) / action row (Replace Matched, Ignore, Cancel — Replace Matched + Ignore disabled in INIT).
- Already-replaced rows show `bulk_status="Already replaced"` from the start.
- `start_bulk_replace(viewer)` constructs the dialog; second click brings the existing one to front instead of opening a duplicate.

### Step 3.4 — Folder pick → match → MATCHED state ✅ DONE

- Folder picker uses `filedialog.askopenfilename` + `os.path.dirname` (the workaround for Tk's askdirectory limitations — see "Native folder picker" above for the dormant alternative).
- `_apply_match_result(result)` translates MatchResult buckets into per-row updates via a `canvas_file_id → (status, local_match)` map.
- `_recompute_counts_and_buttons()` updates the counter line:
  - INIT: "Pick any file in your replacement folder to start matching."
  - 0 matched: "0 of {total} matched in this folder. Check filenames or pick a different folder."
  - Otherwise: "{will_replace} of {matched} matched will be replaced ({total} documents total)"
  - Replace Matched enabled iff `will_replace > 0`.
- `_on_row_select(row)`: enables Ignore button only when status is `"Will replace"` or `"Ignored"`. Label flips between `"Ignore"` and `"Don't ignore"` to always describe the click action.
- `_on_ignore_clicked()`: toggles the row's `bulk_status`, refreshes color, recomputes counter + button.
- Re-picking a folder resets all statuses cleanly (the new match result is the source of truth).

### Step 3.5 — Replace Matched → `BulkReplaceJob` (no per-file progress yet) ✅ DONE

- `_on_replace_matched`: snapshots `(canvas_file_id, local_path)` pairs from rows still `"Will replace"`, opens a confirm dialog with `Replace N files in {course_name}? This cannot be undone.`, runs the auth pre-check, snapshots static counts (ignored / already-replaced / not-matched), enters RUNNING (disables Select Folder, Replace Matched, Ignore), spawns a `BulkReplaceJob`.
- `BulkReplaceJob`: owns `cancel_event`, daemon worker thread `name="canvas-bulk-replace"`. Per item, checks cancel_event → marshals `_on_file_starting(cid)` (sets row to amber `"Replacing…"`) → calls `perform_replace(course_id, cid, local_path, cancel_event=...)` → marshals `_on_file_complete(cid, status, apply_replaced)`. Cancel-during-upload counts as `Skipped` (the upload may have completed but wasn't confirmed; the row title intentionally doesn't get the `(replaced)` suffix).
- `_find_row_idx_by_canvas_file_id(cid)` — robust to user-triggered re-sorts during a run.
- `_on_file_complete(cid, status, apply_replaced)`: updates row, calls `viewer._apply_replaced_to_ui(cid)` on success.
- `_update_running_counter()` — live `X / N processed — A replaced, B failed, C skipped`.
- `_on_job_done()` — DONE state, swaps Cancel→Close, prints `"Done — A replaced, B ignored, C already-replaced, D failed, E not matched"` using snapshotted counts.
- `_close()` — during RUNNING calls `_job.cancel()` silently and keeps the dialog open until `_on_job_done` fires.

### Step 3.6 — Per-file progress in the table (NEXT)

- Wire an `on_progress(stage, bytes_read, total)` per file that pumps `bulk_status` updates into the row via the same throttle pattern as `start_single_replace` (100ms minimum, stage change always emits).
- Status text formats:
  - `"Notifying…"` (notifying stage)
  - `"Uploading 12.4 / 47 MB (26%)"` (uploading stage; reuse `_format_bytes`)
  - `"Confirming…"` (confirming stage)
  - `"Done"` (success) / `"Failed: <reason>"` (error)
- Per-stage strings will need either: (a) added to `_STATUS_COLORS` so they map to the amber `Replacing…` color, or (b) split the row's color-tag field from its display field. Approach decided at implementation time.
- **Verify:** Bulk replace a few medium-sized files. Each row ticks live through the stages. UI stays responsive.

### Step 3.7 — Cancel button + window-X confirm

- Cancel button (during RUNNING) → `show_dialog(..., dialog_type="confirm")` with `"Cancel bulk replace? The current upload will finish first."` On Yes: set `cancel_event`. Worker loop checks the event between files; remaining rows transition to `bulk_status="Skipped"` (gray).
- Dialog X (during RUNNING) → same confirm flow via `protocol("WM_DELETE_WINDOW", ...)`.
- **Verify:** Start a 5+ file bulk; Cancel mid-batch. Confirm dialog → on Yes the current file finishes and the rest become Skipped.

### Step 3.8 — Main-window close warning

- `gui/app.py` (or wherever the root's `WM_DELETE_WINDOW` is currently bound):
  - Wrap the existing close handler. If a `BulkReplaceJob` is active (track via `viewer._bulk_dialog._job`), show the same confirm. On Yes: set the cancel event, bounded-wait ~30 seconds, then proceed with normal close.
- **Verify:** Start a bulk run, click the main app's X. Confirm dialog appears; on Yes app closes after current file finishes.

## Edge case: user/group files (scope tracking) — DEFERRED

### The problem

A document linked from a course page can actually be hosted in user or group personal storage rather than the course's file storage:

- `https://{instance}/users/{user_id}/files/{file_id}` — user-owned
- `https://{instance}/groups/{group_id}/files/{file_id}` — group-owned
- `https://{instance}/courses/{course_id}/files/{file_id}` — course-owned

We currently treat all Canvas-hosted documents as course files. The file-replace endpoint (`POST /courses/{course_id}/files`) only works for files actually in the course; user/group files 404 at the notify step. The bulk run shows generic `Failed` for every such row.

### Status

Discussed and design-locked but **deferred for now**. The user paused this thread to work on a side project (diagnostic prints). When this resumes, the chosen design is below.

### Where the scope is lost today

- API path (`resource_nodes/canvasfiles.py`): files iterated via `GET /courses/N/files` are course-scoped by definition, but we never record that fact.
- HTML link path (`resource_nodes/base_node.py` → `core/node_factory.py:get_node_by_a_tag_match`): the `a_tag` URL carries scope (`/users/N/files/M` etc.) but `get_node_by_a_tag_match` only matches the resource type token (`'files'`) and dispatches to `get_content_node`. The scope segment is never inspected.

By the time the document scaffold is built (`core/content_scaffolds.py:document_dict`), the row's `url` field is the proxied download link (`/files/{id}/download?...`) with no scope info, and the scope is irretrievable from the stored data.

### Refactor (~50 lines across 8 files)

Smallest-possible scope plumbing. Follows existing conventions (regex lives in `config/re.yaml` + `sorters/`, scope is propagated through node `__init__` kwargs).

**1. `config/re.yaml`** — one new entry:
```yaml
canvas_file_scope_re: /(courses|users|groups)/(\d+)/files/
```

**2. `sorters/sorters.py`** — compile + expose, mirror of every other URL classifier:
```python
canvas_file_scope_regex = re.compile(expressions["canvas_file_scope_re"])

_FILE_SCOPE_MAP = {"courses": "course", "users": "user", "groups": "group"}

def extract_file_scope(url):
    """Return (scope, scope_id) for a Canvas file URL, or (None, None)."""
    if not url:
        return None, None
    m = canvas_file_scope_regex.search(url)
    if not m:
        return None, None
    return _FILE_SCOPE_MAP[m.group(1).lower()], int(m.group(2))
```
Add `canvas_file_scope_regex` to `reload_patterns()`'s global list and recompile body for env-var substitution support.

**3. `resource_nodes/base_content_node.py`** — accept and store the new attributes:
```python
def __init__(self, parent, root, api_dict=None, url=None, title=None,
             captioned=False, file_scope=None, scope_id=None, **kwargs):
    ...
    self.file_scope = file_scope   # 'course' | 'user' | 'group' | None
    self.scope_id = scope_id        # int or None
```
All existing subclasses (Document, DocumentSite, VideoFile, etc. in `content_nodes.py`) already forward `**kwargs` — no changes needed there.

**4. `resource_nodes/canvasfiles.py`** — set scope when iterating course files:
```python
self.children.append(content_node(
    self, self.parent, file_dict,
    file_scope="course", scope_id=self.course_id,
))
```
`CanvasFolder.get_all_items` similarly passes `file_scope="course"` (scope_id defaults to None unless we plumb course_id through CanvasFolder.__init__ — optional refinement).

**5. `resource_nodes/base_node.py`** — use the sorter helper at both HTML-link instantiation sites:
```python
from sorters.sorters import extract_file_scope
...
# In add_data_api_link_to_children at the data_api_node call:
file_scope, scope_id = extract_file_scope(link[0])
initialized_node = data_api_node(
    self, self.root, api_dict,
    bypass_get_url=True,
    file_scope=file_scope, scope_id=scope_id,
)

# In add_content_nodes_to_children at the ContentNode call:
file_scope, scope_id = extract_file_scope(link[0])
self.children.append(ContentNode(
    self, self.root, None, link[0], link[1],
    file_scope=file_scope, scope_id=scope_id,
))
```

**6. `core/node_factory.py`** — **no change.** Factory stays a pure dispatcher.

**7. `core/content_scaffolds.py`** — emit two new fields in `document_dict`:
```python
"file_scope": getattr(document_node, "file_scope", None),
"scope_id": getattr(document_node, "scope_id", None),
```

**8. `gui/table_widget.py`** — add new `Not in course` status color (gray, dark + light) to `_STATUS_COLORS`.

**9. `gui/file_replace.py`** — split eligibility in `BulkReplaceDialog.__init__`:
```python
self._eligible_docs = []
self._not_in_course_docs = []
for doc in all_docs:
    if doc.get("file_source") != "Canvas" or not doc.get("canvas_file_id"):
        continue
    scope = doc.get("file_scope")
    # None = scanned before scope tracking landed (treat as course — same
    # as today's behavior). 'course' = explicit course file. Both eligible.
    if scope in (None, "course"):
        self._eligible_docs.append(doc)
    else:
        self._not_in_course_docs.append(doc)
```
And in `_build_initial_rows`, give the not-in-course docs the `"Not in course"` status from the start. The existing `_on_row_select` already keeps the Ignore button disabled for any status other than "Will replace" / "Ignored", so non-course rows behave correctly without further changes.

### Backward compatibility

- Old `content.json` files (scanned before this lands) won't have `file_scope`/`scope_id` → `getattr` returns None → docs treated as course-scoped (current behavior). No migration. No regression until the user re-scans.
- After re-scan: bulk dialog correctly tags user/group files as "Not in course" and excludes them from runs.
- CanvasFolder children get `file_scope="course"` but `scope_id=None` — fine because the bulk dialog only checks scope, not scope_id.

### Trade-offs accepted

- **Lifts the "no edits to core/ or resource_nodes/" constraint** for the first time since the OSError fix. The user explicitly approved this as a one-time exception; future scope-tracking-adjacent changes can ride on the same plumbing.
- **Doesn't enable user/group file replace.** Out of scope — would need permission checks per scope and routing through different Canvas API endpoints. The same `file_scope`/`scope_id` fields are reusable if that feature ever ships.
- **No fallback for bare `/files/N` links** with no scope prefix — those default to `file_scope=None`, treated as course (today's behavior). If they turn out to be user/group files at runtime, they fail with the existing generic `Failed` status.

### Verification

1. Re-scan a course that links to a known user file (the SFSU example: `/users/90767/files/9134666`).
2. Inspect the resulting `content.json` — that document row should have `"file_scope": "user"` and `"scope_id": 90767`.
3. Open Bulk Replace on that course → user-file row appears with `"Not in course"` (gray) status from the start, never matchable.
4. Course-owned files still appear normally and can be matched/replaced.
5. Old `content.json` files (no `file_scope` field) still open in Bulk Replace with all Canvas-hosted docs eligible (no regression).

## Edge cases (general)

| Case | Behavior |
|---|---|
| Folder has zero document files | Counter "0 documents found in folder", inline hint to check extensions. |
| Folder has files but none match Canvas titles | Counter "0 of N matched", friendly empty state. |
| Two local files share a casefold name (e.g. `Foo.pdf` and `foo.pdf`) | Pick the first encountered, log warning, mark second as unmatched_local. |
| Two Canvas docs share a casefold title AND a local file collides with that name | Both Canvas docs go to ambiguous (status "Ambiguous"). |
| Two Canvas docs share a casefold title with NO colliding local file | Both go to unmatched_canvas (status "No match") — there's nothing to confuse. |
| Local file exists but extension differs from Canvas doc | Treated as no-match (since match is extension-strict). |
| Network drops mid-batch | Per-file `Failed: <reason>`, batch continues to next file. |
| Permission revoked mid-batch | Per-file `Failed: HTTP 401`, batch continues. |
| `save_content_json` write fails | Log warning; in-memory data still has the suffix (visible until app restart). |
| User clicks Bulk Replace twice | Button disabled while dialog is open (track active dialog on viewer); second click brings existing one to front. |
| User Ignores every matched row | Replace Matched button disables (counter `0 of N`); secondary confirm never appears. |
| Ignore clicked while running | Button is already disabled in RUNNING state; in-flight rows can't be retroactively un-queued. |
| Re-pick folder with previously-Ignored rows still in the table | Ignored state is reset along with all other statuses — the new match result is the source of truth. |
| User-or-group-scoped Canvas file (deferred) | Currently fails generically at runtime. With scope-tracking refactor: marked "Not in course" upfront and excluded from the run. |

## Verification (end-to-end after step 3.8)

1. Open Bulk Replace on a course with multiple Canvas documents — table populates, already-(replaced) rows greyed out from the start.
2. Pick a folder with mixed match types — counter, statuses, and Local Match column update correctly. Re-pick a different folder → re-evaluation works.
3. Select a Will-replace row, click Ignore → row turns gray "Ignored", counter decrements, Ignore button label flips to "Don't ignore". Click again → row returns to green Will-replace; counter re-increments. Select an Already-replaced row → Ignore button stays disabled.
4. Replace Matched → secondary confirm shows the post-Ignore count → execution starts. Rows tick Pending → Notifying → Uploading X/Y MB → Confirming → Done. Counter updates as `X / N completed`. Ignored rows stay gray with no upload activity.
5. Cancel mid-batch → confirm → current file finishes, remaining show Skipped (gray).
6. Try to close the main window during a job → confirm dialog appears.
7. After a clean run: inspect `content.json` — every replaced row has the `(replaced)` suffix; the underlying Content Viewer documents table reflects the changes. After a fresh scan, suffixes clear.
8. Folder with no document extensions (e.g. images only) → counter "0 documents found in folder".
9. Folder with all mismatches → counter "0 of N matched", inline empty-state.
10. Force a 401 mid-batch (revoke token) → remaining rows show `Failed: HTTP 401`, batch continues then ends in DONE.

## Notes for the executor

- **Reuse, don't duplicate.** All the network plumbing, throttling, and progress formatting already exists in `gui/file_replace.py` from Phase 2. The bulk dialog's `on_progress` should look very similar to `start_single_replace`'s.
- **`_apply_replaced_to_ui` is the right call from the bulk worker** — don't re-implement the in-memory mutation + persistence + table refresh; that helper already does all three.
- **Don't touch `core/` or `resource_nodes/`** for the bulk-replace work itself. The user/group scope-tracking refactor (deferred) is the one approved exception, scoped tightly to the files listed in that section.
- **Don't add unsolicited features** — no recursive folder scan, no "preview a file" affordance, no auto-rescan after bulk completes. The plan is the scope.
- **Diagnostic-print mode** is a separate side project the user mentioned. Plan content for that lives in conversation history (not in this file). When that resumes we'll plan it in a separate file rather than overwrite this one.
