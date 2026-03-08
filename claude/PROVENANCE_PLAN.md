# File Stamping & Provenance System for PDF/DOCX

## Context

Canvas Bot downloads documents for accessibility auditing. Users review files and mark them "Passed" in the Content Viewer. Currently this status lives only in `review_status.json` — if the file is lost, moved, or the JSON deleted, the review history is gone.

This feature embeds a provenance stamp (date, SHA-256 hash, marker) directly into PDF and DOCX file metadata when the user clicks "Passed". On subsequent table loads, if `review_status.json` has no entry for a file but the local copy is stamped, the "Passed" status is recovered from the file itself.

## Design

### Stamp Metadata

**PDF** (via `pypdf` — pure Python, 0 deps):
- `/CanvasBot_Stamped`: `"true"`
- `/CanvasBot_StampDate`: ISO 8601 UTC datetime
- `/CanvasBot_ContentHash`: SHA-256 hex (computed before stamping)

**DOCX** (via stdlib `zipfile` + `xml.etree.ElementTree` — no new dep):
- Custom properties in `docProps/custom.xml` with same three keys

### review_status.json Schema (additive, backward compatible)

```json
{
  "https://example.com/file.pdf": {
    "status": "Passed",
    "stamp": {
      "file_hash": "a1b2c3...",
      "stamp_date": "2026-03-01T18:30:00+00:00"
    }
  }
}
```

Recovered entries also get `"recovered": true`.

## Files to Modify

1. **`tools/file_stamp.py`** — NEW: all stamp/read logic (~250 lines)
2. **`gui/content_viewer.py`** — stamp on "Passed" click + provenance recovery in `_check_downloaded`
3. **`requirements.txt`** — add `pypdf`

No changes to `core/` or `resource_nodes/`.

## Implementation Steps

### Step 1: Add `pypdf` to `requirements.txt`

```
pypdf~=5.0
```

Pure Python, ~1MB, no hidden imports for PyInstaller.

### Step 2: Create `tools/file_stamp.py`

**Public API:**
- `stamp_file(file_path) -> StampInfo | None` — hash file, embed metadata, return stamp dict
- `read_stamp(file_path) -> StampInfo | None` — read Canvas Bot metadata from file
- `is_stampable(file_path) -> bool` — extension check (.pdf / .docx)

**Internal — PDF (`pypdf`):**
- `_stamp_pdf(path, stamp)` — `PdfReader` → `PdfWriter.clone_document_from_reader` → `add_metadata({"/CanvasBot_*": ...})` → write to temp file → `os.replace` (atomic)
- `_read_pdf_stamp(path)` — `PdfReader` → read `metadata` dict → check for `/CanvasBot_Stamped`

**Internal — DOCX (stdlib):**
- `_stamp_docx(path, stamp)` — open ZIP, create/update `docProps/custom.xml` with CanvasBot properties, update `[Content_Types].xml` and `_rels/.rels` if custom.xml is new, write to temp file → `os.replace`
- `_read_docx_stamp(path)` — open ZIP, read `docProps/custom.xml`, parse CanvasBot properties

**Internal — shared:**
- `_compute_sha256(path)` — stream file in 8KB chunks, return hex digest

**Error handling:** All functions catch exceptions, log warnings, return `None`/`False`. No errors surface to user. Original file is never corrupted (temp file + atomic rename pattern).

### Step 3: Integrate stamping on "Passed" click (`gui/content_viewer.py`)

In `_on_status_changed(value)`, after saving status to review_status.json:
```python
if value == "Passed":
    self._try_stamp_file(self._selected_row, url)
```

New methods:
- `_try_stamp_file(row, url)` — check save_path exists, is stampable, launch background thread
- `_resolve_file_path(save_path)` — resolve actual path (handles date-folder wildcards, reuses `_DATE_FOLDER_RE` logic)
- `_stamp_worker(file_path, url)` — background thread: calls `stamp_file()`, then schedules main-thread callback via `self._view.root.after(0, ...)`
- `_save_stamp_to_review_status(url, stamp_info)` — main-thread callback: persists stamp info to review_status.json

**Threading:** follows existing `controller.py` pattern — file I/O in daemon thread, GUI updates via `root.after(0, callback)`.

### Step 4: Integrate provenance recovery in `_check_downloaded()` (`gui/content_viewer.py`)

After finding an existing downloaded file, add:
```python
url = row.get("url", "")
if url and url not in self._review_statuses and is_stampable(match_path):
    stamp_info = read_stamp(match_path)
    if stamp_info and stamp_info.get("stamped"):
        self._review_statuses[url] = {
            "status": "Passed",
            "stamp": {"file_hash": ..., "stamp_date": ...},
            "recovered": True,
        }
```

Save recovered statuses at the end if any were found.

**Performance:**
- `is_stampable()` is a string check — zero I/O
- `read_stamp()` reads only metadata (PDF trailer or DOCX custom.xml) — fast even for large files
- Only runs when `url not in self._review_statuses` — cached after first recovery
- For 100 stampable files needing recovery: <1 second total

## Verification

1. Download a course with PDF and DOCX files
2. Mark a PDF as "Passed" → verify stamp in file properties (Adobe Reader or `pypdf` CLI)
3. Mark a DOCX as "Passed" → verify `docProps/custom.xml` contains CanvasBot properties
4. Delete `review_status.json`, reload course → verify "Passed" recovered from file stamps
5. Test edge cases: missing file, locked file, non-PDF/DOCX, already-stamped file
6. Verify no GUI freeze during stamping (background thread)