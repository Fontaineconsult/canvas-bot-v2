# Link-Replace Feature — Session History (reference only)

> This file is a **memory dump** from a design exploration that ended with
> `git reset` discarding the implementation. It is **not** an authoritative
> plan — `claude/LINK_SCANNER_PLAN.md` and `claude/BULK_REPLACE_PLAN.md`
> are the surviving authoritative documents. Use this file to brief a fresh
> session on what was tried, what was decided, what was learned about
> Canvas's API, and what's still open — so the next pass doesn't have to
> re-derive everything.

## What prompted the work

A bulk-replace user (Mark, CSULB) ran our Bulk Replace feature on 27
files. All 27 uploaded successfully but every page-body link to those
files became broken. Two URLs from his report told the story:

- Page link: `https://csulb.instructure.com/courses/510/files/28070361?wrap=1` (old ID, page unchanged)
- Files UI:  `https://csulb.instructure.com/files/31394879/download?download_frd=1` (new ID after upload)

Two distinct file_ids for what should have been one replaced file.

## Canvas behavior — what we verified from source

We read `app/controllers/files_controller.rb` and `app/models/attachment.rb`
on `instructure/canvas-lms` master.

**`on_duplicate=overwrite`** (Attachment#handle_duplicates, lines ~1646-1718):

1. Old attachment is **soft-deleted** — `workflow_state='deleted'`.
2. Old attachment's `replacement_attachment_id` is set to the new attachment's ID.
3. Canvas auto-rewrites **`ContentTag`** references (module items, the legacy assignment-file picker) to point at the new ID.
4. **HTML rich-text content is NOT touched.** Page bodies, assignment descriptions, discussion messages, announcement messages, syllabus_body, quiz descriptions, and quiz question stems still hold the old file_id.

**Replacement chain following** (files_controller.rb, lines ~1056-1114):

- The chain is followed only when the request includes `replacement_chain_context_type` + `replacement_chain_context_id` query params.
- Page-rendered HTML never carries those params, so `/courses/:cid/files/:fid` and `/courses/:cid/files/:fid?wrap=1` and `/files/:fid/download` all return 404 (or "Failed getting file to preview") for a soft-deleted attachment.
- The `FindInContextAssociation` mixin on the model exists but isn't invoked by these controller routes by default.

**Conclusion.** This is the structural cause of Mark's bug. UDOIT, Ally, Pope Tech, and Canvas's own UI all hit the same wall on page-body links — they happen to "work" mostly through `ContentTag`-routed flows (modules) where Canvas does auto-rewrite. Our bulk replace just made the gap visible by hitting 27 page-linked files at once.

## Canvas update endpoint matrix (verified from developer docs)

For the rewrite phase. The notification-suppress column is the kicker.

| Source | Endpoint | Body field | Notify-suppress |
|---|---|---|---|
| Page | `PUT /api/v1/courses/:cid/pages/:url` | `wiki_page[body]` | `wiki_page[notify_of_update]=false` |
| Assignment | `PUT /api/v1/courses/:cid/assignments/:id` | `assignment[description]` | `assignment[notify_of_update]=false` |
| Discussion topic | `PUT /api/v1/courses/:cid/discussion_topics/:id` | `message` | **NONE documented** |
| Announcement | Same as discussion topic (announcements are topics with `is_announcement=true`) | `message` | **NONE** |
| Syllabus | `PUT /api/v1/courses/:id` | `course[syllabus_body]` | **NONE** |
| Quiz | `PUT /api/v1/courses/:cid/quizzes/:id` | `quiz[description]` | `quiz[notify_of_update]=false` (defaults to **true** — must set explicitly) |
| Quiz question | `PUT /api/v1/courses/:cid/quizzes/:qid/questions/:id` | `question[question_text]` | **NONE**. `question[answers]` is an array — partial-PUT semantics undocumented; round-trip the answers to be safe. |

**The notification gap drove the scope decision.** See "Decisions" below.

## Late-discovery: scanner had an N+1 bug

`gui/link_scanner.py:_scan_pages` fetched the pages index, then issued
`get_page(course_id, slug)` per page to retrieve each body. For a 50-page
course, 51 requests. For courses > 100 pages, the existing `get_pages`
helper doesn't paginate — pages past 100 were silently missed.

Canvas's `GET /api/v1/courses/:cid/pages` supports `include[]=body`. From
the docs: *"the page content, in HTML (present when requesting a single
page; **optionally included when listing pages**)"*. With pagination via
`Link: rel="next"` we get every page's body in `ceil(total/100)` requests.

The original scanner plan asserted this wasn't possible and accepted N+1
as "the slow part." That assertion was wrong. Any rebuild of
`_scan_pages` should use `include[]=body&per_page=100` plus the
`_paginated_get` helper that already lives in the scanner module.

The other source types (assignments, discussions, announcements, quizzes)
already get their HTML field from the list endpoints. Quiz questions are
the only legitimate per-resource fetch, and even that paginates per quiz.

## What got built — and discarded

`gui/link_scanner.py` (~360 lines, never committed). Module-level pure
helpers + a `scan_course_for_file_refs(course_id, file_ids, on_progress,
cancel_event, include_quiz_questions)` entry point returning a
`ScanResult` dataclass. Per-source private functions for each of the
seven source types. Internal `_paginated_get` for `Link: rel="next"`
walking. Reused `network.api` helpers (`get_pages`, `get_page`,
`get_assignments`, `get_discussions`, `get_announcements`, `get_quizzes`).

**Phase 4 partial implementation in `gui/file_replace.py`** (also gone):

- New `linked_from` column added to `_BULK_COLUMNS` (width 200, plain text).
- `_pluralize` helper + `_PLURAL_FORMS` map.
- New `LinkScanJob` class mirroring `BulkReplaceJob` — daemon thread, cancel_event, marshalled callbacks.
- Generation stamp passed through every callback so stale results from a superseded scan early-return.
- `_destroyed` flag set in `_close` to guard against `parent.after` callbacks queueing past dialog teardown.
- New dialog state fields: `_scan_job`, `_scan_result`, `_is_scanning`, `_scan_progress`, `_scan_generation`, `_destroyed`.
- `_on_select_folder` cancels in-flight scan, wipes stale `linked_from`, kicks off fresh scan with new generation.
- `_recompute_counts_and_buttons` early-returns scanning text when `_is_scanning`; otherwise appends `— K will break links` to the existing counter when applicable.
- `_on_scan_progress` and `_on_scan_done` with both guards at the top.
- `_on_replace_matched` confirm dialog appended a "K of these files are linked from page bodies; replacing them will break those links until you fix them" warning.
- `_close` branch order: RUNNING confirm (unchanged) / SCANNING silent cancel + `_destroyed=True` / default close.

**Compiled clean. Never run.**

## Plans we wrote during the session

All committed except where noted.

- **`claude/LINK_SCANNER_PLAN.md`** (committed at HEAD, includes the 12-issue read-through fixes). Phase 4 spec for threading the scanner into `BulkReplaceDialog`. Authoritative.
- **`claude/BULK_REPLACE_PLAN.md`** (committed pre-session). Phase 3 spec, fully shipped.
- **`claude/LINK_REWRITER_PLAN.md`** (gone — never committed). Two iterations:
  1. Initial: full 7-source-type rewriter with per-source opt-out checkboxes and "may notify" caveat in the confirm dialog. ~400 lines.
  2. Trimmed: pages-only — single endpoint, silent rewrite. ~150 lines.
  Both covered post-replace integration into the bulk flow and a deferred standalone recovery audit.

## Key design decisions that crystallized (whether or not we kept them)

1. **Scanner is read-only, separate from rewriter.** Different surface, different blast radius. Rebuild this way.
2. **Pre-flight scan (before replace), not post.** Surface breakage to the user up-front, not after the damage.
3. **Auto-on-folder-pick, not user-initiated.** One scan per dialog session feels free; an extra button feels like work.
4. **Scan scope is `result.matches` (Will-replace rows only).** Not all eligible docs. Don't pay for files we won't upload.
5. **Generation-stamped callbacks for stale-result safety.** Re-pick mid-scan must not write old data onto new rows.
6. **`_destroyed` flag for close-during-scan safety.** `parent.after` callbacks can queue past dialog teardown.
7. **Wipe `linked_from` immediately on re-pick.** Don't show stale data while the new scan runs.
8. **`linked_from` column is plain text (not status-colored).** Sidesteps the `bulk_status` / `bulk_color` two-field pattern.
9. **Pluralization helper at module scope.** `"1 pages"` is wrong; per-call ternaries multiply.
10. **Edit-conflict skip via re-fetch + `find_refs_in_html` re-check.** If the body no longer references the old IDs at write time, skip silently — somebody else fixed it.
11. **Always set `notify_of_update=false` on endpoints that support it.** Silent rewrites by default.
12. **Pages-only scope for v1 of the rewriter.** Final user direction. Drop the 6 other source types until proven needed.
13. **Block-replace, not warn-and-allow, when file linked from non-suppress-able source.** Final user direction (proposed but not implemented before reset). Better to leave the file unchanged than to risk notification spam OR broken links from a partial fix.

## Where the Ultraplan handoff was

Session: <https://claude.ai/code/session_01DB9FnwvBE2UdCUdYxENTGi>

Submitted plan: the N+1 fetch fix for `_scan_pages` (use `include[]=body&per_page=100` via `_paginated_get`). The Ultraplan session returned a refined plan; the user reset HEAD before applying it. Worth opening if the next session decides to rebuild the scanner — the refined plan from Ultraplan may already cover the N+1 fix in a more polished form.

## Open decisions / what's not yet settled

- **Should rewriting be coupled to bulk replace, standalone, or both?** Initial design had both — post-replace cleanup as the primary path, recovery audit for already-broken courses as Phase 5.4 deferred. Worth re-deciding before code goes down.
- **Strict block vs. permissive partial fix** when a file is linked from a mix of page (suppress-able) and non-page (no-suppress) sources. Last user direction was strict block, but it wasn't ratified before reset.
- **Single-replace integration.** Phase 4 covered bulk only. Whether single-replace ever gets the same pre-flight scan UX is open.
- **Quiz question `answers` PUT semantics.** Plan to round-trip defensively; never actually tested against Canvas.
- **`replace_file_with_progress`'s 200-with-location branch** may not yield an `id` in the result dict; recovery audit was the planned fallback. If we drop recovery, this becomes a TODO.

## Files of interest

| Path | Status | Why it matters |
|---|---|---|
| `claude/LINK_SCANNER_PLAN.md` | Authoritative spec for Phase 4 | Has the 12 read-through fixes applied. Specifies LinkScanJob shape, generation/destroyed guards, column layout, etc. |
| `claude/BULK_REPLACE_PLAN.md` | Phase 3, shipped | Reference for `BulkReplaceDialog` / `BulkReplaceJob` patterns |
| `gui/file_replace.py` | Bulk-replace dialog and worker | `_BULK_COLUMNS` (line 475), `BulkReplaceDialog.__init__` (line ~491), `_on_select_folder` (line ~668), `_apply_match_result` (line ~721), `_recompute_counts_and_buttons` (line ~756), `_on_replace_matched` (line ~805), `_close` (line ~985), `BulkReplaceJob` (line ~1028) |
| `gui/network.py` | `replace_file_with_progress` | Returns the new file's metadata dict on success — `result["id"]` is the new file_id, needed for any rewriter |
| `network/api.py` | List/show helpers | Reuse rather than re-implement: `get_pages`, `get_page`, `get_assignments`, `get_discussions`, `get_announcements`, `get_quizzes`, `get_file`, `_clean_url`, `_extract_error_message` |
| `core/content_scaffolds.py` line ~134 | Document row schema | `canvas_file_id`, `file_source`, `file_scope` are the eligibility gate fields |
| `config/re.yaml` | `document_content_regex` | Source of truth for replaceable extensions; consumed by `get_document_extensions` |

## Notes for the next session

- **Keep the scanner separate from the rewriter** even when rebuilding. The read/write boundary is load-bearing for code review and for blast-radius reasoning.
- **Use `include[]=body` for the pages list.** Don't recreate the N+1 bug.
- **The `_paginated_get` helper inside the scanner module followed `Link: rel="next"` correctly.** Reuse that shape; the existing `network.api` list helpers don't paginate.
- **`get_file(course_id, file_id)` returns `folder_id` and `display_name`.** Both are needed by `replace_file_with_progress` for the notify step. The bulk path already plumbs this; recovery would too.
- **Don't widen the rewriter scope past pages without revisiting the notification-policy decision.** Discussions/announcements/syllabus/quiz_questions can't suppress notifications; that constraint set the pages-only scope.
- **Test against the `wrap=1` route specifically.** Mark's broken links were on `/courses/510/files/{old_id}?wrap=1`. The chain isn't followed there. Any verification that loads `/files/{new_id}` directly will pass falsely; load via the page link instead.
