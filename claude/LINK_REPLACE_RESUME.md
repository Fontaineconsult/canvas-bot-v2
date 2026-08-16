# Link-Replace Feature — Resume Bookmark

> ## STATUS 2026-08-16: COMPLETE — this file is now historical
>
> Everything below describes the world as of the 2026-05-07 pause and
> **predates the orchestrator architecture**. Do not resume work from
> this checklist. The migration finished and was verified live against
> course 21016 (all resource types: page, discussion, assignment, quiz,
> plus module file-only replaces; single, bulk, and CLI flows).
>
> **Current architecture** (what actually exists now):
> - `core/orchestrator.py` — `ContentUpdateOrchestrator` / `replace_content`:
>   atomic pre-flight → file replaces → body rewrites, event callbacks.
> - `core/replace.py` — `FileReplace` + `UpdateBody` subclasses for all 5
>   rewritable resource types (page, discussion, announcement, assignment,
>   quiz), with stale-check / verify / rollback.
> - `network/files.py` — upload primitives (live-tested).
> - `tools/replace_content_cli.py` + `--replace_pair`/`--rewrite_target`
>   in canvas_bot.py — the CLI flow.
> - `gui/wx/replace_dialogs.py` + `gui/core/replace_helpers.py` — wx single
>   and bulk dialogs; `derive_body_targets` builds body targets from the
>   scan manifest's `source_page_url` (list-shaped since 2026-05-30);
>   byte-level upload progress with screen-reader-safe announcements.
>
> **Key live findings** (see project memory for detail): Canvas follows
> file replacement chains itself — after a same-name overwrite, old
> `/files/N` links resolve to the new file and served body HTML arrives
> already rewritten, so body rewrites report `skipped` and that IS the
> success outcome. A byte-identical overwrite dedupes to the SAME file id.
>
> **How the old checklist resolved**: steps 1–2 (live-test FileReplace,
> round-trip) done 2026-05-10 ("cli tested"); step 3 superseded — the wx
> bulk dialog drives `replace_content` directly; step 4 (delete
> `gui/network.py`) deferred — it goes when the legacy Tk GUI is retired
> (deliberately held off for now); step 5 superseded by
> `derive_body_targets`; step 6 resolved — no scanner rebuild, the scan
> manifest is the authoritative source of referencing pages.
>
> **Sibling file:** `claude/LINK_REPLACE_HISTORY.md` is the longer
> backstory (the original session that ended in a `git reset`, the
> Canvas-source findings, the update-endpoint matrix, etc.). Both files
> are now history, kept for context only.

> **Paused 2026-05-07**: Canvas instance offline due to a cyber attack.
> All forward progress requires a live Canvas to round-trip against, so we
> stopped mid-stride. This file is the bookmark for when service is back.

## What's in the working tree right now

Everything below is committed-or-uncommitted on branch `1.2.3` and
compiles. Live-tested pieces are noted explicitly.

### `core/replace.py` — the abstraction layer

Two classes; both are at column 0; module compiles.

- **`Replace`** — page link rewriter. Live-tested end-to-end against
  course 21016, page `embeded-links` (SFSU). Round-trip works: fetch
  body, rewrite file_id digit segments, PUT new body, no notification
  emitted.
  - `__init__(course_id, page_id)` — fetches body via `get_page`.
  - `_fetch_body()` — `get_page` → `body` field.
  - `print_body()` — debug helper.
  - `rewrite(mapping)` — returns new body string, does not mutate. Uses
    module-level `_FILE_REF_RE = re.compile(r"/files/(\d+)\b")`.
  - `push(new_body)` — PUT via `update_page`. Returns bool.

- **`FileReplace`** — file content replacer. **NOT live-tested yet.**
  Canvas went down before we ran it. Compiles; logic mirrors the proven
  `gui/network.py:replace_file_with_progress` flow but split across
  network primitives and class-level orchestration.
  - `__init__(course_id, old_file_id, local_path, on_progress=None, cancel_event=None)`
  - `run()` → True on success; sets `self.new_file_id`. Steps:
    fetch existing → validate extension match → notify → upload bytes
    (with `on_bytes` translated into `on_progress("uploading", ...)`)
    → branch (Canvas short-circuited dict OR confirm_url string) →
    confirm → store new_file_id.
  - `_extensions_match`, `_emit`, `_cancelled` — internals.

### `network/api.py` — generic Canvas helpers

- **Existing GETs unchanged** — `get_file`, `get_page`, etc.
- **Added `update_page(course_id, page_url, body)`** — PUT
  `wiki_page[body]` with `wiki_page[notify_of_update]=false` always.
  Live-tested via `Replace.push`.
- **Added `put_response_handler` + `put_response_decorator`** — generic
  PUT-with-form-body wrapper, mirrors the existing `response_decorator`
  shape but expects the wrapped function to return `(url, data)`.
  Reusable for future PUT endpoints (assignments, discussions, etc.).

### `network/files.py` — file-upload primitives (NEW FILE)

Three primitives extracted from `gui/network.py:replace_file_with_progress`.
**Not live-tested yet.**

- `notify_file_upload(course_id, name, size, parent_folder_id, on_duplicate="overwrite")`
  → `(upload_url, upload_params)` or None.
- `upload_file_bytes(upload_url, upload_params, local_path, original_name, on_bytes=None)`
  → either a dict (Canvas short-circuited with file metadata) or a
  string (confirm_url) or None. The dict-vs-str return is awkward but
  matches Canvas's actual two-branch behavior; see `FileReplace.run`
  for the consumer pattern.
- `confirm_file_upload(confirm_url)` → file dict or None.

### Untouched (intentionally)

- `gui/network.py:replace_file_with_progress` — still exists, still
  used by the bulk replace flow. Leaving it means the existing UI
  doesn't break. **Slated for removal** once `BulkReplaceJob` is
  migrated to use `FileReplace`.
- `gui/file_replace.py` — bulk replace dialog + worker, no changes.
  Still imports `from gui.network import replace_file_with_progress`.

## When you come back, do this in order

### 1. Live-test `FileReplace` (5 minutes)

Pick a known file in a test course. Drop into `core/replace.py`'s
`__main__`:

```python
def show(stage, b, t):
    print(f"  {stage}: {b}/{t}" if stage == "uploading" else f"  {stage}")

fr = FileReplace("21016", 9164373, r"C:\path\to\replacement.pdf", on_progress=show)
ok = fr.run()
print(f"replaced: {ok}, new_id: {fr.new_file_id}")
```

Verify in Canvas: file 9164373's contents are now the replacement;
new file_id appears in the course's Files UI; the old file_id
returns "Failed getting file to preview" when accessed via
`/courses/21016/files/9164373?wrap=1` (this is the bug we're
chaining `Replace.push` to fix — expected at this stage).

### 2. Round-trip with `Replace` to verify the chain works

```python
# After step 1, you have fr.new_file_id.
mapping = {fr.old_file_id: fr.new_file_id}

# Find a page that references the old file_id and rewrite it.
page = Replace("21016", "embeded-links")
page.push(page.rewrite(mapping))
```

Verify the page link now resolves to the new file (not the old).

### 3. Migrate `BulkReplaceJob._run` to use `FileReplace`

In `gui/file_replace.py`, the worker currently calls `perform_replace`
which wraps `gui/network.py:replace_file_with_progress`. Replace that
with a `FileReplace` instance per file. Capture `fr.new_file_id` into
a list of `(old_id, new_id)` pairs on the job — this is the seed for
the post-replace rewrite step.

### 4. Delete `gui/network.py` (and `perform_replace`)

Once nothing imports `replace_file_with_progress` from `gui.network`,
delete the file. `perform_replace` (the auth-bootstrap wrapper) goes
too — its job moves into `FileReplace` or stays in
`_on_replace_matched` where it already runs.

### 5. Wire post-replace rewrite into `_on_job_done`

Build mapping from `replaced_pairs`. For each page that the (rebuilt)
scanner found a ref in, construct `Replace`, call `rewrite + push`.
Show the user a confirm before running ("N pages link to files you
just replaced; rewrite them now? Silent — no student notifications.").

### 6. Decide: rebuild the scanner here?

We never restored `gui/link_scanner.py` after the original reset. The
two paths:

- **Build it back.** Walks all 7 source types so the gate can block
  files referenced from non-page sources (the policy decision the
  original session arrived at). Still uses `include[]=body` for the
  pages walk (the N+1 fix from the Ultraplan iteration).
- **Skip it.** Hardcode the post-replace rewrite to scan only pages
  for refs, accept that files linked from discussions/etc. silently
  break. Simpler, less safe.

Talk through this when you get there. The original `LINK_SCANNER_PLAN.md`
is still in tree as the spec if you go the rebuild route.

## Open design questions still on the table

| Question | Status |
|---|---|
| Naming: `Replace` vs `PageReplace` vs `LinkReplace` | Unresolved. `Replace` and `FileReplace` are sibling classes today — `Replace` is page-only despite the generic name |
| Where the bulk-match helpers (`match_files_to_documents`, `MatchResult`, `is_document_file`, etc.) live | Currently in `gui/file_replace.py`. The "everything replace in `core/`" instinct says move; pragmatic says don't until they have a non-GUI consumer |
| Should `FileReplace` own auth bootstrap, or is it the caller's job? | Currently caller's. `gui/file_replace.py:_on_replace_matched` ensures auth before spawning the worker. |
| Strict block vs warn-and-allow when a file is linked from non-page (no-suppress) source | Last user direction was strict block; not yet enforced anywhere |
| Single-replace integration | Out of scope for now |
| Recovery audit (Mark's CSULB course) | Out of scope for now; engine pieces are reusable when we get there |

## Files to revisit

| Path | Why |
|---|---|
| `claude/LINK_REPLACE_HISTORY.md` | Long-form context: bug origin, Canvas-source findings, update-endpoint matrix |
| `claude/LINK_SCANNER_PLAN.md` | The (still authoritative) spec for the scanner integration if we go that route |
| `claude/BULK_REPLACE_PLAN.md` | Phase 3 reference for the existing bulk dialog and worker patterns |
| `core/replace.py` | The abstraction layer — `Replace` and `FileReplace` |
| `network/files.py` | The new file-upload primitives |
| `network/api.py` | `update_page` and the PUT decorator added this session |
| `gui/file_replace.py` | The bulk dialog, slated for migration to `FileReplace` |
| `gui/network.py` | Slated for deletion once migration is done |