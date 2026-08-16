# Link Scanner Integration — Bulk Replace Pre-Flight

> **Project-rooted backup** of the plan. Tracks the integration of `gui/link_scanner.py`
> into the existing Bulk Replace flow so users see — *before* they upload — which files
> in their batch are referenced from page bodies (the case Canvas's `on_duplicate=overwrite`
> doesn't auto-rewrite, and which broke 27 links for Mark at CSULB).
>
> **Out of scope for this plan:** single-replace integration, the recovery/audit tool for
> already-broken courses, and any HTML-rewrite logic. Those will get their own plan files
> once this lands.

## Context

`gui/link_scanner.py` (committed) walks a course's syllabus, pages, assignments, discussions,
announcements, quizzes, and quiz questions, returning a `ScanResult` of every place a given
set of `file_id`s is referenced from rich-text HTML. Canvas's overwrite-replace flow leaves
those references stale — the page body still says `<a href="/courses/510/files/{old_id}?wrap=1">`
even though the underlying attachment has been soft-deleted with a `replacement_attachment_id`.
The page-link route doesn't follow the chain by default, so the link returns "Failed getting
file to preview."

This plan threads the scanner into `BulkReplaceDialog` so the user sees, per file, how many
HTML references will break if the replace proceeds. The user can then Ignore risky rows
or proceed informed.

## What's already in place

- `gui/link_scanner.py` — `scan_course_for_file_refs(course_id, file_ids, on_progress, cancel_event, include_quiz_questions)` returns a `ScanResult` with `refs_by_file_id: dict[int, list[FileRef]]`, per-source error tracking, and a `cancelled` flag for partial results. Same `on_progress(stage, done, total)` and `cancel_event` shape as `replace_file_with_progress`.
- `gui/file_replace.py:482 BulkReplaceDialog` — owns the existing INIT → MATCHED → RUNNING → DONE state machine, the `_apply_match_result` translator, the `_recompute_counts_and_buttons` counter line updater, and the `_on_replace_matched` confirm path.
- `gui/file_replace.py:1028 BulkReplaceJob` — daemon-thread orchestration pattern with `cancel_event` and `parent.after(0, ...)` marshalling. Mirror it for `LinkScanJob`.
- `gui/table_widget.py` — `ContentTable` accepts arbitrary `columns` at construction. Adding a fourth column is a constructor-arg change, no widget refactor needed.

## Locked design decisions

| Decision | Choice | Rationale |
|---|---|---|
| When to scan | Automatically on entering MATCHED, not user-initiated | One scan per dialog session feels free; an extra button feels like work |
| Scan scope (which file_ids) | File ids from `result.matches` only (rows that became `bulk_status='Will replace'`). Excludes `already_replaced`, `ambiguous`, `unmatched_canvas`, and user/group docs. | "Matched" is overloaded with `eligible_docs` etc. — this is the unambiguous set |
| State machine | Add a SCANNING substate between MATCHED and "ready" | Keeps INIT/RUNNING/DONE semantics intact; SCANNING is just a guard on Replace Matched |
| Cancel during SCANNING | Cancel scan, return to MATCHED with no link data | User can re-pick folder or close; replace is permitted but unwarned |
| Re-pick folder during SCANNING | Cancel in-flight scan, recompute matches, kick off new scan | Treat the new match result as the source of truth, same pattern as the existing folder re-pick |
| Quiz questions in scan | Included | The bug occurs there too; most expensive bucket, but bulk path can afford it |
| Scan failure (network, 5xx) | Degrade gracefully — log, continue, dialog still functions | A scanner that blocks Replace Matched on transient API failures is worse than no warning |
| New column name | `"Linked from"` | Reads naturally; "References" was ambiguous with regex matches |
| Column content format | `"3 pages, 1 assignment"` (source-type counts, comma-separated) | Concise but specific. Empty string when 0 — no visual noise. |
| Pluralization | Module-scope helper `_pluralize(source_type, n) -> str`. Map: page/pages, assignment/assignments, discussion/discussions, announcement/announcements, quiz/quizzes, quiz question/quiz questions, syllabus/syllabus. | `"1 pages"` is wrong; helper avoids inline ternaries at every call site |
| Confirm dialog addition | One extra line: `"K of N matched files are linked from page bodies and will break."` | Don't itemize in the confirm; the column already shows per-row detail |
| Status color overlay | None for v1 | The "Linked from" column carries the warning visually; a status color change would conflict with the existing "Will replace" green |
| Scope creep guard | Don't add a "scan now" or "rescan" button | Auto-on-enter + auto-on-folder-pick covers every case; manual buttons add states to test |

## Architecture

One new worker class, one new column, one new substate. All edits live in
`gui/file_replace.py` and `gui/table_widget.py`.

- **`LinkScanJob`** — daemon thread, `cancel_event`. Calls `scan_course_for_file_refs` with a per-stage progress callback that marshals to the dialog via `parent.after(0, ...)`. Posts `_on_scan_progress(generation, stage, done, total)` and `_on_scan_done(generation, result)` to the dialog. Each job is stamped with a `generation: int` at construction (passed from the dialog's current `_scan_generation`); marshalled callbacks include the generation so the dialog can reject results from a job that has been superseded by a re-pick.
- **Dialog state additions** — `self._scan_job: LinkScanJob | None`, `self._scan_result: ScanResult | None`, `self._is_scanning: bool`, `self._scan_progress: tuple[str,int,int]` (stage/done/total for the counter line), `self._scan_generation: int` (incremented every time a new scan kicks off; stale callbacks compare against current and early-return), `self._destroyed: bool` (set in `_close`; checked at the top of every scan callback to guard against `update_row` on a torn-down Toplevel — `parent.after` callbacks can queue past dialog destruction). Replace Matched gates on `not self._is_scanning AND will_replace > 0`.
- **Per-row `linked_from` field** — populated from `scan_result.refs_by_file_id[cid]` after scan completes. Each row's display value is built by counting source_types: `Counter(ref.source_type for ref in refs).most_common()` formatted as `"3 pages, 1 assignment"` via `_pluralize`. Plain text only — unlike the existing parallel `bulk_status` (display) / `bulk_color` (tag-key) pattern, `linked_from` has no color tag and no entry in `_STATUS_COLORS`. The column carries the warning visually via its presence, not via row color.
- **Counter line states** — extends the existing matrix:
  - SCANNING: `"Scanning course content for references… {stage}: {done} / {total}"`
  - SCAN_DONE_NO_REFS: existing message + nothing extra
  - SCAN_DONE_WITH_REFS: existing message + ` — {K} will break links` appended

## Files to modify

- **`gui/file_replace.py`** — `LinkScanJob` class, `BulkReplaceDialog` state additions, `_apply_match_result` scan kickoff, `_recompute_counts_and_buttons` counter-line extension, `_on_replace_matched` confirm-text extension, `_close` scan-cancel handling. ~120 lines added.
- **`gui/table_widget.py`** — no code changes; `ContentTable` already accepts arbitrary `columns`. The `BulkReplaceDialog`'s table construction in `__init__` (line 491-ish) gets a fourth column tuple.

No changes to: `gui/link_scanner.py` (already complete), `gui/network.py`, `gui/content_viewer.py`, `core/*`, `network/*`, `config/*`, `resource_nodes/*`.

## Implementation steps

Same step-and-verify cadence as `BULK_REPLACE_PLAN.md`. Pause for verification after each.

### Step 4.1 — Add the `"Linked from"` column

- Edit the module-level `_BULK_COLUMNS` list at `gui/file_replace.py:475-479`. Add a fourth entry: `{"id": "linked_from", "heading": "Linked from", "width": 200, "stretch": False}`. The `ContentTable` constructor at line 580 picks up the new column automatically — no constructor changes.
- `_build_initial_rows` (line 633): include `"linked_from": ""` in each row dict (both `_eligible_docs` and `_not_in_course_docs` branches).
- **Verify:** open Bulk Replace; the new empty column appears at width 200; existing INIT/MATCHED behavior is unchanged.

### Step 4.2 — `LinkScanJob` worker

- New class in `gui/file_replace.py` near `BulkReplaceJob` (line 1028). Constructor takes `(dialog, course_id, file_ids, generation)` and stores `self.generation`. Methods: `start()`, `cancel()`, `is_running()`. Worker calls `scan_course_for_file_refs(...)` with marshalled `on_progress` and the job's own `cancel_event`. On each progress tick the worker marshals `dialog._on_scan_progress(self.generation, stage, done, total)`; on completion or cancel it marshals `dialog._on_scan_done(self.generation, result)`. Marshal via `dialog._parent.after(0, ...)` matching the `BulkReplaceJob` pattern.
- **Verify:** trigger the job manually from a test entry point, confirm `_on_scan_done` fires with a non-empty `ScanResult` and that cancel mid-scan fires the same callback with `result.cancelled=True`. Verify a stale generation is rejected by the dialog (covered properly in 4.5).

### Step 4.3 — Wire scan kickoff in `_on_select_folder`

- At the top of `_on_select_folder` (line 668): if `self._scan_job is not None and self._scan_job.is_running()`, cancel it and set `self._scan_job = None`. (`_apply_match_result` stays pure-data — the kickoff lives at the flow boundary.)
- After the existing `self._recompute_counts_and_buttons()` call (line 697): walk all rows and reset `linked_from=""` so stale data from any previous scan disappears immediately. Then collect file_ids of rows with `bulk_status=='Will replace'`. If the set is non-empty, increment `self._scan_generation`, set `self._is_scanning=True`, construct and start a new `LinkScanJob` stamped with the new generation. Empty set → skip the scan.
- **Verify:** pick a folder that produces matches; confirm scan kicks off (counter line updates) and that re-picking a different folder cancels the in-flight scan, wipes the old `linked_from` data immediately, and starts a new scan.

### Step 4.4 — Counter line + button gating during SCANNING

- Add an early-return branch at the top of `_recompute_counts_and_buttons` (line 757): if `self._is_scanning`, set `_counter_label` to `"Scanning course content for references… {stage}: {done} / {total}"` using `self._scan_progress` (a `(stage, done, total)` tuple updated by `_on_scan_progress`), set Replace Matched to disabled, and return. The existing branches (no folder / 0 matched / has matches) handle post-scan and no-scan cases unchanged.
- `_on_scan_progress(generation, stage, done, total)`: at the top, early-return if `self._destroyed` or `generation != self._scan_generation`. Otherwise store the tuple in `self._scan_progress` and call `_recompute_counts_and_buttons`.
- **Verify:** counter line ticks through stages (`syllabus → pages → assignments → ...`); Replace Matched is greyed out throughout; re-enables when scan completes or is cancelled.

### Step 4.5 — Apply scan result to rows + counter

- `_on_scan_done(generation, result)`: at the top, early-return if `self._destroyed` or `generation != self._scan_generation` (stale callback from a superseded scan). Otherwise store `self._scan_result`, for each row whose `canvas_file_id` is in `result.refs_by_file_id`, format the source-type counts via `_pluralize` and call `update_row` with the new `linked_from` value. Set `self._is_scanning=False`. Recompute counter+buttons.
- Counter line addition (post-scan, with refs): existing message + ` — {K} will break links`, where K = number of rows with non-empty `linked_from`. When K=0, no addition.
- **Verify:** a folder with matches that include a known page-linked file shows `"Linked from: N pages"` in that row's column; counter line shows the breakage tally; row colors stay as they were (green "Will replace" — color overlay not in v1).

### Step 4.6 — Replace Matched confirm dialog

- `_on_replace_matched`: when computing the confirm body, count `K = sum(1 for cid in selected_cids if scan_result and scan_result.has_refs(cid))`. If K > 0, append `"\n\n{K} of these files are linked from page bodies; replacing them will break those links until you fix them."` to the confirm text.
- **Verify:** confirm dialog shows the warning line when K>0; doesn't show it when K=0; user-cancel from confirm leaves dialog in MATCHED state with scan results still visible.

### Step 4.7 — Cancel + close handling

- Modify `_close` (line 985). Branch order: (a) if `self._state == "RUNNING"` and the bulk job is in flight → existing confirm logic unchanged; (b) else if `self._is_scanning` → cancel `self._scan_job` silently (no confirm; scans are cheap to abandon), set `self._destroyed=True`, fall through to default close; (c) default close unchanged. The `_destroyed` flag protects late-firing scan callbacks from acting on a torn-down dialog.
- Folder re-pick during scan: covered in 4.3, but verify the `linked_from` values from the previous scan are wiped during the reset and repopulated by the new scan.
- **Verify:** start a scan, immediately close the dialog → no errors, scan thread exits cleanly. Start a scan, immediately re-pick → previous link data is gone, new scan repopulates. During RUNNING, close still confirms (existing behavior preserved).

## Edge cases

| Case | Behavior |
|---|---|
| Course has no rich content (empty pages list, etc.) | Scan completes instantly with empty `refs_by_file_id`; all `linked_from` cells stay empty; no confirm-dialog warning |
| Scan errors on every source | `result.errors` populated, `refs_by_file_id` empty; confirm dialog shows no breakage warning (we don't have data either way); UI silently degrades to "no link data" |
| Scan errors on some sources | Whatever data was collected is shown; `result.errors` is logged. No banner — partial data is still useful and we don't want to scare the user off |
| File matched in folder is referenced from 0 sources | Empty `linked_from` cell — distinct from "we didn't scan" by virtue of the scan having completed (no UI distinction needed) |
| File referenced from 12 different sources | Display: `"5 pages, 4 assignments, 3 discussions"` — comma-joined, ordered by count desc, no truncation in v1 (column wraps if needed) |
| User clicks Replace Matched with `_scan_result=None` (cancelled) | Existing confirm runs without the breakage line. They're back to v3.5 behavior. |
| Re-pick folder, new match set is a strict subset of old | Old scan data for shared file_ids is wiped along with the rest; we re-scan. Avoids stale results from a different course's worth of refs (impossible here, but principled). |
| User re-picks folder while scan is in flight; old scan completes after the re-pick | Generation stamp on the job — the marshalled `_on_scan_done` checks `generation != self._scan_generation` and returns without touching rows. Same guard on `_on_scan_progress`. |
| User closes dialog while scan is running | `_destroyed=True` set in `_close`; every scan callback checks the flag at the top and returns early. `parent.after` callbacks can queue past destruction; the flag is what makes them safe. |
| Quiz questions endpoint 404s on a quiz | `_paginated_get` logs a warning, scanner skips that quiz; recorded in `result.errors`; rest of scan continues |
| Scan still running when bulk replace would complete (impossible — Replace Matched is gated) | N/A — gated. |

## Verification (end-to-end after step 4.7)

1. Open Bulk Replace on a course with a known page-linked document. Pick a folder containing a replacement for it. After matching, counter line transitions to `"Scanning course content for references…"`. Replace Matched is disabled.
2. Wait for scan to complete. The matched row's `Linked from` column shows `"1 page"` (or similar). Counter line gains the `— 1 will break links` suffix. Replace Matched re-enables.
3. Click Replace Matched → confirm dialog includes the breakage warning line. Cancel from the confirm → dialog returns to MATCHED with link data still visible.
4. Re-pick a different folder → previous link data is wiped, new scan kicks off, populates fresh data.
5. Pick a folder, then click the dialog X mid-scan → dialog closes cleanly, no exceptions, scan thread exits.
6. Disconnect network mid-scan → scan reports errors via the warning channel, Replace Matched re-enables, confirm dialog runs without the breakage warning.
7. Course with no rich-text content of any kind → scan completes immediately, all `Linked from` cells empty, no breakage warning in the confirm.
8. Bulk replace 5 files where 3 are page-linked and 2 are not → confirm shows "3 of these files…", run completes, the 3 risky uploads succeed at Canvas (page links break, as expected — fix is the recovery flow, not in this plan).

## Notes for the executor

- **The scanner is final.** Don't modify `gui/link_scanner.py` for this work. If the scan output isn't shaped right for the dialog, format-translate at the call site.
- **Don't add color tags to the new column.** A separate "Will break N links" status was on the table and we explicitly chose against it for v1 — the column carries the signal.
- **Don't preemptively hide rows with `linked_from` data.** The user already has the Ignore button for opt-out; the warning is informational.
- **Don't add a "Skip risky rows" button.** Same reason — Ignore + the per-row column already enable that workflow without new state.
- **Don't introduce a settings flag for "enable link scan."** Either it works for everyone or we pull it; flagged-off-by-default is worse than not shipping.
- **Don't add a drill-in click on the `Linked from` cell.** Clicking "3 pages" to see *which* pages would be a natural triage affordance, but it requires a sub-dialog and per-source title storage. Out of scope for v1 — the eventual recovery/audit flow is the right home for that view.
