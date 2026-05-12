"""GUI-side file replace orchestration.

Pure helpers (no UI) used by the Content Viewer's single Replace flow and
the upcoming bulk replace feature. UI flows (dialogs, threading, progress
widgets) will land in this module in subsequent steps.
"""

import json
import logging
import os
import re
import threading
import time
import warnings
from dataclasses import dataclass
from tkinter import filedialog
from typing import List, Optional, Tuple

import customtkinter as ctk

from gui.network import replace_file_with_progress
from gui.widgets import Tooltip, _add_focus_ring, show_dialog

log = logging.getLogger(__name__)

REPLACED_SUFFIX = " - (replaced)"

# Minimum time between progress callback marshals to the UI thread.
# MultipartEncoderMonitor fires on every socket write — without this the GUI
# would queue thousands of after(0, ...) calls during a fast upload.
_PROGRESS_THROTTLE_SEC = 0.1


def _format_bytes(n):
    """Render a byte count as a compact human string (e.g. '12.4 MB')."""
    if n is None:
        return "?"
    n = float(n)
    if n < 1024:
        return f"{int(n)} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    if n < 1024 * 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB"
    return f"{n / (1024 * 1024 * 1024):.2f} GB"


# Patterns mapping Canvas URL forms to (resource_type, identifier) tuples.
# resource_type matches keys in core.replace.RESOURCE_TYPES so the parser is
# directly reusable by the orchestrator-driven replace flows. Order matters
# only for /modules#<id>, which is detected via the fragment, so we handle
# it explicitly rather than as a regex.
_SOURCE_URL_PATTERNS = [
    (re.compile(r"/courses/[^/]+/pages/([^/?#]+)"),               "page"),
    (re.compile(r"/courses/[^/]+/discussion_topics/(\d+)"),       "discussion"),
    (re.compile(r"/courses/[^/]+/announcements/(\d+)"),           "discussion"),  # same endpoint as discussion_topics
    (re.compile(r"/courses/[^/]+/assignments/(\d+)"),             "assignment"),
    (re.compile(r"/courses/[^/]+/quizzes/(\d+)"),                 "quiz"),
]


def parse_canvas_source_url(url: str) -> Optional[Tuple[str, str]]:
    """Parse a Canvas source-page URL into (resource_type, identifier).

    Returns None when the URL doesn't correspond to a resource with a
    rewritable body (modules, /files listing, course shell, malformed, etc.).

    Used by:
      - gui.content_viewer for source-row "Multi" dropdown labeling
      - the upcoming derive_body_targets helper that builds the
        orchestrator's body_targets list from source_page_url
    """
    if not isinstance(url, str) or not url:
        return None
    for pattern, resource_type in _SOURCE_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return resource_type, match.group(1)
    return None


def derive_body_targets(rows) -> List[Tuple[str, str]]:
    """Map a set of content rows to the orchestrator's body_targets list.

    For each row, reads source_page_url (accepting list-or-string for
    backward compat with older content.json files) and parses each URL
    via parse_canvas_source_url. URLs that don't correspond to a
    rewritable resource body (modules, /files listings, unknown shapes)
    are dropped — the file is still replaced, but there's nothing to
    rewrite on that side.

    The final list is deduped by (resource_type, identifier) so that
    when N files share a referencing page (common in well-organized
    courses), the orchestrator fetches and rewrites that page once
    rather than N times. Order is preserved (first occurrence wins).

    Used by both start_single_replace ([row]) and BulkReplaceJob (every
    row currently 'Will replace') to populate
    ContentUpdateOrchestrator.body_targets.
    """
    seen = set()
    targets: List[Tuple[str, str]] = []
    for row in rows or []:
        urls = row.get("source_page_url") if isinstance(row, dict) else None
        if urls is None:
            continue
        if isinstance(urls, str):
            urls = [urls]
        elif not isinstance(urls, list):
            continue
        for url in urls:
            parsed = parse_canvas_source_url(url)
            if parsed is None:
                continue
            if parsed in seen:
                continue
            seen.add(parsed)
            targets.append(parsed)
    return targets


def source_url_label(url: str) -> str:
    """Build a short, readable label for a source-page URL.

    Used in the Content Viewer's multi-source dropdown so users can tell
    locations apart without reading raw URLs. Falls back to a truncated
    URL when the path doesn't match a known Canvas resource shape.
    """
    parsed = parse_canvas_source_url(url)
    if parsed:
        resource_type, identifier = parsed
        return f"{resource_type.title()}: {identifier}"
    # Module URLs look like .../modules#<id>; show them readably too.
    if isinstance(url, str) and "/modules" in url:
        frag_match = re.search(r"#(\d+)", url)
        if frag_match:
            return f"Module: {frag_match.group(1)}"
        return "Modules"
    if isinstance(url, str):
        return url if len(url) <= 60 else url[:57] + "..."
    return str(url)


def _course_root_folder(viewer):
    """Return the course's top-level folder (parent of .manifest/) when
    we can locate it, else None.

    Used as a contextual fallback for file pickers when per-row save_path
    data isn't available, has been moved, or doesn't exist on disk in the
    current execution context. Without this, Tk falls back to the cwd —
    which on the PyInstaller bundle is wherever the exe was launched from
    (often Documents), losing all course context.
    """
    manifest_dir = getattr(viewer, "_manifest_dir", None)
    if manifest_dir and os.path.isdir(manifest_dir):
        course_folder = os.path.dirname(manifest_dir)
        if os.path.isdir(course_folder):
            return course_folder
    return None


def perform_replace(course_id, file_id, local_path, on_progress=None, cancel_event=None):
    """Bootstrap Canvas auth, then run the streamed file replace.

    Returns the file metadata dict on success, or None on auth failure or
    any error returned by the network layer. Progress callbacks and the
    cancel event are forwarded to gui.network.replace_file_with_progress.
    """
    from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata
    load_config_data_from_appdata()
    if not set_canvas_api_key_to_environment_variable():
        warnings.warn("Canvas API token not found - cannot replace file", UserWarning)
        return None
    return replace_file_with_progress(
        course_id, file_id, local_path,
        on_progress=on_progress, cancel_event=cancel_event,
    )


def mark_row_replaced(current_data, canvas_file_id):
    """Append REPLACED_SUFFIX to the matching document's title in current_data.

    Idempotent: re-applying to a row already ending in the suffix is a no-op.
    Returns True if a row was matched (whether or not the suffix was already
    present), False if no matching row was found.
    """
    if not current_data or not canvas_file_id:
        return False
    docs = (current_data.get("content", {})
            .get("documents", {})
            .get("documents", []))
    for row in docs:
        if row.get("canvas_file_id") == canvas_file_id:
            title = row.get("title", "") or ""
            if not title.endswith(REPLACED_SUFFIX):
                row["title"] = title + REPLACED_SUFFIX
            return True
    return False


def save_content_json(json_path, current_data):
    """Write current_data back to the course's content.json at json_path."""
    if not json_path or not current_data:
        return
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(current_data, f, indent=4, sort_keys=True, default=str)
    except OSError:
        pass


# ── Bulk Replace pure helpers ──

@dataclass
class MatchResult:
    """Result of matching local files against Canvas documents.

    matches: (canvas_doc_dict, local_path) pairs ready to upload.
    unmatched_local: local files that didn't pair with any Canvas doc.
    unmatched_canvas: eligible Canvas docs with no local match.
    ambiguous: Canvas docs that share a casefold title with another doc.
    already_replaced: Canvas docs whose title ends in REPLACED_SUFFIX.
    """
    matches: List[Tuple[dict, str]]
    unmatched_local: List[str]
    unmatched_canvas: List[dict]
    ambiguous: List[dict]
    already_replaced: List[dict]


_DOCUMENT_EXTENSIONS_CACHE = None


def get_document_extensions():
    """Return the set of document extensions (lowercase, with dot) from re.yaml.

    Cached after first read. Each `document_content_regex` entry looks like
    ".*\\.pdf"; the literal extension is the substring after the last "\\.".
    """
    global _DOCUMENT_EXTENSIONS_CACHE
    if _DOCUMENT_EXTENSIONS_CACHE is not None:
        return _DOCUMENT_EXTENSIONS_CACHE
    try:
        from config.yaml_io import read_re
        data = read_re()
        patterns = data.get("document_content_regex", []) or []
    except Exception:
        log.warning("Could not load document_content_regex from re.yaml", exc_info=True)
        patterns = []
    extensions = set()
    for pattern in patterns:
        if not isinstance(pattern, str):
            continue
        parts = pattern.split("\\.")
        if len(parts) >= 2 and parts[-1]:
            extensions.add("." + parts[-1].lower())
    _DOCUMENT_EXTENSIONS_CACHE = extensions
    return extensions


def is_document_file(local_path):
    """True when local_path's extension is in the document extension set."""
    ext = os.path.splitext(local_path)[1].lower()
    return bool(ext) and ext in get_document_extensions()


def match_files_to_documents(folder, documents):
    """Match local files in `folder` (flat scan) against Canvas `documents`.

    Match logic: case-insensitive exact basename match (including extension).
    Documents whose title already ends in REPLACED_SUFFIX are bucketed into
    `already_replaced` and never matched. When two eligible Canvas documents
    share a casefold title AND a local file with that name exists, both
    Canvas docs are bucketed into `ambiguous` (we can't pick which to
    update). When the duplicate Canvas titles have no local counterpart,
    they're treated as `unmatched_canvas` — there's nothing to confuse.
    Local files outside get_document_extensions() are skipped silently.
    Two local files sharing a casefold name: keep the first, log + bucket
    the rest into `unmatched_local`.
    """
    already_replaced = []
    eligible_docs = []
    for doc in documents:
        title = doc.get("title", "") or ""
        if title.endswith(REPLACED_SUFFIX):
            already_replaced.append(doc)
        else:
            eligible_docs.append(doc)

    docs_by_key = {}
    duplicate_keys = set()
    for doc in eligible_docs:
        key = (doc.get("title", "") or "").casefold()
        if not key:
            continue
        if key in docs_by_key:
            duplicate_keys.add(key)
        docs_by_key.setdefault(key, []).append(doc)

    local_files = []
    seen_local_keys = set()
    unmatched_local = []
    try:
        entries = sorted(os.listdir(folder))
    except OSError as exc:
        log.warning(f"Could not list folder {folder}: {exc}")
        entries = []
    for name in entries:
        full = os.path.join(folder, name)
        if not os.path.isfile(full):
            continue
        if not is_document_file(full):
            continue
        key = name.casefold()
        if key in seen_local_keys:
            log.warning(f"Skipping duplicate local file (casefold collision): {name}")
            unmatched_local.append(full)
            continue
        seen_local_keys.add(key)
        local_files.append((key, full))

    # Only Canvas-side duplicates that ALSO have a local file colliding with
    # them are truly ambiguous. Duplicate Canvas titles with no local
    # counterpart are just unmatched.
    ambiguous_keys = duplicate_keys & seen_local_keys
    ambiguous = []
    for key in ambiguous_keys:
        ambiguous.extend(docs_by_key[key])
    ambiguous_doc_ids = {id(doc) for doc in ambiguous}

    matches = []
    matched_doc_ids = set()
    for key, full in local_files:
        if key in ambiguous_keys:
            unmatched_local.append(full)
            continue
        if key in docs_by_key:
            doc = docs_by_key[key][0]
            matches.append((doc, full))
            matched_doc_ids.add(id(doc))
        else:
            unmatched_local.append(full)

    unmatched_canvas = [
        doc for doc in eligible_docs
        if id(doc) not in matched_doc_ids and id(doc) not in ambiguous_doc_ids
    ]

    return MatchResult(
        matches=matches,
        unmatched_local=unmatched_local,
        unmatched_canvas=unmatched_canvas,
        ambiguous=ambiguous,
        already_replaced=already_replaced,
    )


_STAGE_LABELS = {
    "preflight":  "Pre-flight check…",
    "fetching":   "Fetching file info…",
    "notifying":  "Notifying Canvas…",
    "uploading":  "Uploading…",
    "confirming": "Confirming…",
    "done":       "Done",
}


class SingleReplaceProgressDialog:
    """Tiny modal shown while a single file replace is in flight.

    Two labels: filename and a stage line that updates from the worker via
    update_progress(). During the upload stage the line shows live byte
    counts; during other stages it shows a static label.

    A Cancel button sets the shared cancel_event. The network layer checks
    that event between its three stages (notify / upload / confirm) — it
    does NOT abort mid-stream, so a cancel during the upload waits for the
    current upload to finish before stopping.
    """

    def __init__(self, parent, filename, cancel_event):
        self._parent = parent
        self._cancel_event = cancel_event
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.withdraw()
        self.dialog.title("Replacing file")
        self.dialog.resizable(False, False)

        ctk.CTkLabel(
            self.dialog,
            text=f"Replacing: {filename}",
            font=ctk.CTkFont(size=13),
            wraplength=320,
            justify="left",
        ).pack(padx=18, pady=(12, 4), anchor="w")

        self._stage_label = ctk.CTkLabel(
            self.dialog,
            text="Starting…",
            font=ctk.CTkFont(size=12),
        )
        self._stage_label.pack(padx=18, pady=(0, 8), anchor="w")

        self._cancel_btn = ctk.CTkButton(
            self.dialog, text="Cancel", width=90,
            fg_color="gray40", hover_color="gray30",
            command=self._on_cancel_clicked,
        )
        self._cancel_btn.pack(pady=(0, 12))
        _add_focus_ring(self._cancel_btn)

        self.dialog.geometry("360x130")
        self.dialog.deiconify()
        self.dialog.transient(parent.winfo_toplevel())
        self.dialog.grab_set()
        self._cancel_btn.focus_set()
        # X button and Escape both trigger cancel.
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel_clicked)
        self.dialog.bind("<Escape>", lambda e: self._on_cancel_clicked())

    def _on_cancel_clicked(self):
        if self._cancel_event.is_set():
            return  # already cancelled — ignore repeat clicks
        self._cancel_event.set()
        try:
            self._cancel_btn.configure(text="Cancelling…", state="disabled")
            self._stage_label.configure(text="Cancelling — waiting for current step to finish…")
        except Exception:
            pass

    def update_progress(self, stage, bytes_read=0, total=0):
        """Set the stage line. UI-thread only.

        Suppressed once cancel was clicked so the 'Cancelling…' message
        isn't overwritten by late progress callbacks still in flight.
        """
        if self._cancel_event.is_set():
            return
        if stage == "uploading" and total:
            pct = int(bytes_read * 100 / total) if total else 0
            text = (f"Uploading… {_format_bytes(bytes_read)} / "
                    f"{_format_bytes(total)} · {pct}%")
        else:
            text = _STAGE_LABELS.get(stage, stage)
        try:
            self._stage_label.configure(text=text)
        except Exception:
            pass

    def close(self):
        try:
            self.dialog.grab_release()
        except Exception:
            pass
        try:
            self.dialog.destroy()
        except Exception:
            pass


def start_single_replace(viewer, row):
    """Run the single-file replace UI flow against the given row.

    Pre-flight (file picker, type-mismatch dialog, confirm dialog, auth
    pre-check) runs on the UI thread. The actual upload runs on a daemon
    worker thread so the GUI stays responsive; results are marshalled back
    via parent.after(0, ...).

    `viewer` must expose: _parent, _current_data, _apply_replaced_to_ui().
    `row` is the document row dict (typically viewer._selected_row).
    """
    if not row or not viewer._current_data:
        return
    canvas_file_id = row.get("canvas_file_id")
    course_id = viewer._current_data.get("course_id")
    if not canvas_file_id or not course_id:
        return

    initial_dir = ""
    save_path = row.get("save_path", "")
    if save_path:
        folder = os.path.dirname(save_path)
        if os.path.isdir(folder):
            initial_dir = folder
    if not initial_dir:
        # Fall back to the course's top-level folder so the picker stays
        # contextual instead of dropping to Tk's cwd default (Documents on
        # the bundled exe).
        initial_dir = _course_root_folder(viewer) or ""

    file_path = filedialog.askopenfilename(
        title="Select replacement file",
        initialdir=initial_dir,
    )
    if not file_path:
        return

    original_title = row.get("title", "file")
    # Strip the post-replace marker before extracting the extension —
    # otherwise os.path.splitext("foo.pdf - (replaced)") returns
    # ".pdf - (replaced)" as the "extension" (it just splits at the last
    # dot with no validation), and the mismatch dialog fires for any
    # already-replaced file.
    title_for_ext = original_title
    if title_for_ext.endswith(REPLACED_SUFFIX):
        title_for_ext = title_for_ext[:-len(REPLACED_SUFFIX)]
    original_ext = os.path.splitext(title_for_ext)[1].lower()
    local_ext = os.path.splitext(file_path)[1].lower()
    if original_ext and local_ext and original_ext != local_ext:
        show_dialog(
            viewer._parent, "File Type Mismatch",
            f"Cannot replace '{original_title}' ({original_ext}) "
            f"with a {local_ext} file.\n\nSelect a {original_ext} file instead.",
            dialog_type="warning",
        )
        return

    if not show_dialog(
        viewer._parent, "Replace File",
        f"Replace '{original_title}' in Canvas with:\n\n{os.path.basename(file_path)}",
        dialog_type="confirm",
    ):
        return

    from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata
    load_config_data_from_appdata()
    if not set_canvas_api_key_to_environment_variable():
        show_dialog(viewer._parent, "Authentication Error",
                    "Canvas API token not found. Run a scan first or configure your API token.",
                    dialog_type="error")
        return

    parent = viewer._parent
    cancel_event = threading.Event()
    progress = SingleReplaceProgressDialog(parent, os.path.basename(file_path), cancel_event)

    def _on_done(orch):
        progress.close()
        if cancel_event.is_set():
            log.info(f"File replace cancelled by user: {original_title}")
            return
        if orch is None:
            # bootstrap_auth=False is passed, so this only fires if the
            # worker raised before/within replace_content. Defensive.
            show_dialog(parent, "Replace Failed",
                        f"Failed to replace '{original_title}'. Check the log for details.",
                        dialog_type="error")
            return

        s = orch.summary
        if s.get("early") == "preflight_failed":
            # Pre-flight aborted before any modification. Build a
            # readable failure list and tell the user nothing changed.
            msgs = []
            for r in s.get("preflight_failed_file_reports", []):
                msgs.append(f"File {r.old_file_id}: {r.status} - {r.error or 'no details'}")
            msg_block = "\n".join(msgs) or "Unknown pre-flight failure"
            show_dialog(parent, "Pre-flight Failed",
                        f"Cannot replace '{original_title}':\n\n{msg_block}\n\n"
                        "No changes were made to Canvas.",
                        dialog_type="error")
            return

        rep = orch.file_reports[0] if orch.file_reports else None
        if rep and rep.status == "replaced":
            viewer._apply_replaced_to_ui(canvas_file_id)
            show_dialog(parent, "File Replaced",
                        f"Successfully replaced '{original_title}' with "
                        f"'{os.path.basename(file_path)}'.",
                        dialog_type="info")
        else:
            detail = (rep.error or rep.status) if rep else "no report"
            show_dialog(parent, "Replace Failed",
                        f"Failed to replace '{original_title}': {detail}",
                        dialog_type="error")

    # Throttle state — touched only from the worker thread (single writer).
    throttle = {"last_emit": 0.0, "last_stage": None}

    def _marshal_event(stage, payload):
        """Worker -> UI bridge. Translates orchestrator events into the
        progress dialog's existing stage labels. Outcome handling (the
        success/failure dialogs) lives in _on_done, which inspects the
        orchestrator's summary + reports after run() returns.
        """
        if stage == "preflight_started":
            parent.after(0, progress.update_progress, "preflight", 0, 0)
        elif stage == "file_progress":
            sub = payload.get("stage")
            b = payload.get("bytes_read", 0) or 0
            t = payload.get("total", 0) or 0
            now = time.monotonic()
            if (sub != throttle["last_stage"]
                    or sub == "done"
                    or now - throttle["last_emit"] >= _PROGRESS_THROTTLE_SEC):
                throttle["last_emit"] = now
                throttle["last_stage"] = sub
                parent.after(0, progress.update_progress, sub, b, t)

    body_targets = derive_body_targets([row])

    def _worker():
        try:
            from core.orchestrator import replace_content
            orch = replace_content(
                course_id=course_id,
                replacements=[(int(canvas_file_id), file_path)],
                body_targets=body_targets,
                on_event=_marshal_event,
                cancel_event=cancel_event,
                bootstrap_auth=False,
            )
        except Exception:
            log.exception("Unhandled error in replace worker")
            orch = None
        parent.after(0, _on_done, orch)

    threading.Thread(target=_worker, daemon=True, name="canvas-replace").start()


_BULK_COLUMNS = [
    {"id": "title",        "heading": "Title",       "width": 250, "stretch": True, "max_chars": 70},
    {"id": "local_match",  "heading": "Local Match", "width": 220, "stretch": True, "max_chars": 60},
    {"id": "bulk_status",  "heading": "Status",      "width": 240, "anchor": "center"},
]


class BulkReplaceDialog:
    """Modal dialog for bulk-replacing many Canvas documents from a local folder.

    Step 3.3: INIT state only — table populated with eligible Canvas docs,
    Select Folder picker shows the path but does no matching, Replace and
    Ignore buttons stay disabled, Cancel closes the dialog. Steps 3.4–3.8
    add matching, the worker job, per-file progress, and cancel semantics.
    """

    def __init__(self, viewer):
        from gui.table_widget import ContentTable

        self._viewer = viewer
        self._parent = viewer._parent
        self._folder = None  # set when user picks a folder (step 3.4)
        self._state = "INIT"  # INIT → MATCHED → RUNNING → DONE
        self._job = None      # active BulkReplaceJob during RUNNING / DONE
        # Snapshot of pre-run counts taken at Replace-Matched click time so
        # the final summary line can report ignored / already-replaced /
        # not-matched figures without rescanning the table.
        self._initial_counts = {"ignored": 0, "already_replaced": 0, "not_matched": 0}

        course_data = viewer._current_data or {}
        course_name = course_data.get("course_name", "?")
        course_id = course_data.get("course_id", "?")
        all_docs = (course_data.get("content", {})
                    .get("documents", {})
                    .get("documents", []))
        # Eligibility split:
        #   _eligible_docs        — course files (file_scope == 'courses' or None
        #                           for old scans before scope tracking landed).
        #                           These can actually be replaced.
        #   _not_in_course_docs   — user/group files. Canvas-hosted but live in
        #                           personal/group storage, so the course /files
        #                           endpoint can't replace them. Shown in the
        #                           table with 'Not in course' status so the user
        #                           sees them but can't queue them for replace.
        # Already-replaced rows still appear (greyed out) so the user sees the
        # full picture.
        self._eligible_docs = []
        self._not_in_course_docs = []
        for doc in all_docs:
            if doc.get("file_source") != "Canvas" or not doc.get("canvas_file_id"):
                continue
            if doc.get("file_scope") in ("users", "groups"):
                self._not_in_course_docs.append(doc)
            else:
                self._eligible_docs.append(doc)

        # Build dialog window
        self.dialog = ctk.CTkToplevel(self._parent)
        self.dialog.withdraw()
        self.dialog.title(f"Bulk Replace - {course_name}")
        self.dialog.geometry("720x560")
        self.dialog.minsize(640, 400)

        # Header
        header = ctk.CTkLabel(
            self.dialog,
            text=f"Bulk Replace — {course_name} (ID: {course_id})",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))

        # Folder bar
        folder_bar = ctk.CTkFrame(self.dialog, fg_color="transparent")
        folder_bar.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 6))
        folder_bar.columnconfigure(1, weight=1)
        ctk.CTkLabel(folder_bar, text="Source folder:").grid(row=0, column=0, sticky="w")
        self._folder_entry = ctk.CTkEntry(folder_bar, state="readonly")
        self._folder_entry.grid(row=0, column=1, sticky="ew", padx=(8, 8))
        self._select_folder_btn = ctk.CTkButton(
            folder_bar, text="Pick a File…", width=120,
            command=self._on_select_folder,
        )
        self._select_folder_btn.grid(row=0, column=2)
        _add_focus_ring(self._select_folder_btn)
        Tooltip(
            self._select_folder_btn,
            "Pick any file in the folder of replacement files. "
            "The folder it lives in will be scanned for matches.",
        )

        # Counter line
        self._counter_label = ctk.CTkLabel(
            self.dialog,
            text="Pick any file in your replacement folder to start matching.",
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color="gray",
        )
        self._counter_label.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 6))

        # Table — bulk_status holds the display text (which can be dynamic,
        # e.g. "Uploading 12.4 / 47 MB (26%)" during a run); bulk_color holds
        # the stable tag-color key (one of _STATUS_COLORS' values).
        self._table = ContentTable(
            self.dialog, _BULK_COLUMNS,
            on_select=self._on_row_select,
            placeholder="No Canvas-hosted documents in this course.",
            status_key="bulk_status",
            color_key="bulk_color",
        )
        self._table.grid(row=3, column=0, sticky="nsew", padx=14, pady=(0, 8))

        # Action row
        action_row = ctk.CTkFrame(self.dialog, fg_color="transparent")
        action_row.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 12))
        self._replace_matched_btn = ctk.CTkButton(
            action_row, text="Replace Matched", width=160,
            command=self._on_replace_matched, state="disabled",
        )
        self._replace_matched_btn.pack(side="left")
        _add_focus_ring(self._replace_matched_btn)

        self._ignore_btn = ctk.CTkButton(
            action_row, text="Ignore", width=110,
            fg_color="#555555", hover_color="#444444",
            command=self._on_ignore_clicked, state="disabled",
        )
        self._ignore_btn.pack(side="left", padx=(8, 0))
        _add_focus_ring(self._ignore_btn)

        self._cancel_btn = ctk.CTkButton(
            action_row, text="Cancel", width=110,
            fg_color="gray40", hover_color="gray30",
            command=self._close,
        )
        self._cancel_btn.pack(side="right")
        _add_focus_ring(self._cancel_btn)

        # Grid weights for resizing
        self.dialog.rowconfigure(3, weight=1)
        self.dialog.columnconfigure(0, weight=1)

        # Populate the table
        self._table.populate(self._build_initial_rows())

        # Modal show
        self.dialog.deiconify()
        self.dialog.transient(self._parent.winfo_toplevel())
        self.dialog.grab_set()
        self._select_folder_btn.focus_set()
        self.dialog.protocol("WM_DELETE_WINDOW", self._close)
        self.dialog.bind("<Escape>", lambda e: self._close())

        # Lock the bulk button on the underlying viewer while we're open.
        viewer._bulk_dialog = self
        viewer._update_bulk_replace_btn_state()

    def _build_initial_rows(self):
        """Make per-row dicts for the dialog table — adds bulk_status + local_match.

        Sets both bulk_status (the column display text) and bulk_color (the
        color tag). For static states they're equal; during a run, bulk_status
        will tick through dynamic stage strings while bulk_color stays
        'Replacing…' so the row tag color doesn't flicker.
        """
        rows = []
        for doc in self._eligible_docs:
            row = dict(doc)
            title = row.get("title", "") or ""
            if title.endswith(REPLACED_SUFFIX):
                row["bulk_status"] = "Already replaced"
                row["bulk_color"] = "Already replaced"
            else:
                row["bulk_status"] = ""
                row["bulk_color"] = ""
            row["local_match"] = ""
            rows.append(row)
        for doc in self._not_in_course_docs:
            # User/group files surface in the table so the user sees them, but
            # they're never matchable (folder pick can't move them to 'Will
            # replace') and the Ignore button stays disabled for these statuses.
            row = dict(doc)
            scope = doc.get("file_scope")
            label = "Group File" if scope == "groups" else "User File"
            row["bulk_status"] = label
            row["bulk_color"] = label
            row["local_match"] = ""
            rows.append(row)
        return rows

    # ── Event handlers (stubs filled in by later steps) ──

    def _on_select_folder(self):
        """Pick a folder, run matching, refresh the table + counter + buttons.

        We use askopenfilename + os.path.dirname rather than askdirectory
        (legacy XP-style tree, no files visible) or the native Vista+
        IFileOpenDialog with FOS_PICKFOLDERS (modern chrome but folders-only
        in the content pane). The user needs to see files inside folders
        to confirm they're in the right place. See gui/native_dialogs.py
        for the dormant native picker if a future flow doesn't need files
        visible.
        """
        initial_dir = self._folder or self._guess_initial_dir()
        picked = filedialog.askopenfilename(
            title="Pick any file in the folder of replacement files",
            initialdir=initial_dir,
        )
        if not picked:
            return
        folder = os.path.dirname(picked)
        if not os.path.isdir(folder):
            return
        self._folder = folder
        self._folder_entry.configure(state="normal")
        self._folder_entry.delete(0, "end")
        self._folder_entry.insert(0, folder)
        self._folder_entry.configure(state="readonly")

        result = match_files_to_documents(folder, self._eligible_docs)
        self._apply_match_result(result)
        self._recompute_counts_and_buttons()
        self._state = "MATCHED"
        # Re-evaluate the Ignore button for whatever's selected after re-population.
        sel = self._table.get_selected()
        self._on_row_select(sel)

    def _guess_initial_dir(self):
        """Default the folder picker contextual to the current course.

        Preference order:
        1. Parent dir of the first eligible doc's existing save_path (where
           Canvas Bot put the downloaded copy).
        2. The course's top-level folder (parent of .manifest/) — always
           exists when a course is loaded.
        3. Empty string (Tk falls back to cwd).
        """
        for doc in self._eligible_docs:
            save_path = doc.get("save_path", "")
            if save_path:
                folder = os.path.dirname(save_path)
                if os.path.isdir(folder):
                    return folder
        return _course_root_folder(self._viewer) or ""

    def _apply_match_result(self, result):
        """Translate MatchResult buckets into per-row table updates.

        Every row in the table belongs to exactly one bucket (matches /
        already_replaced / ambiguous / unmatched_canvas), so we build a
        canvas_file_id → (status, local_match) map and then walk the rows.
        Re-applying overrides any prior Ignored state — the new folder pick
        is the source of truth.
        """
        updates = {}
        for doc, local_path in result.matches:
            cid = doc.get("canvas_file_id")
            updates[cid] = ("Will replace", os.path.basename(local_path))
        for doc in result.already_replaced:
            cid = doc.get("canvas_file_id")
            updates[cid] = ("Already replaced", "")
        for doc in result.ambiguous:
            cid = doc.get("canvas_file_id")
            updates[cid] = ("Ambiguous", "")
        for doc in result.unmatched_canvas:
            cid = doc.get("canvas_file_id")
            updates[cid] = ("No match", "")

        for idx in range(self._table.get_row_count()):
            row = self._table.get_row(idx)
            if not row:
                continue
            cid = row.get("canvas_file_id")
            if cid in updates:
                status, local_match = updates[cid]
                row["bulk_status"] = status
                row["bulk_color"] = status   # static state — color follows display
                row["local_match"] = local_match
                self._table.update_row(idx, row)

    def _recompute_counts_and_buttons(self):
        """Update the counter line and the Replace Matched button's enabled state."""
        will_replace = 0
        matched = 0  # rows the matcher matched (Will replace + Ignored)
        total = self._table.get_row_count()
        for idx in range(total):
            row = self._table.get_row(idx)
            if not row:
                continue
            status = row.get("bulk_status", "")
            if status == "Will replace":
                will_replace += 1
                matched += 1
            elif status == "Ignored":
                matched += 1

        if not self._folder:
            self._counter_label.configure(
                text="Pick any file in your replacement folder to start matching.",
            )
        elif matched == 0:
            self._counter_label.configure(
                text=(f"0 of {total} matched in this folder. "
                      "Check filenames or pick a different folder."),
            )
        else:
            self._counter_label.configure(
                text=(f"{will_replace} of {matched} matched will be replaced "
                      f"({total} documents total)"),
            )

        if will_replace > 0:
            self._replace_matched_btn.configure(state="normal")
        else:
            self._replace_matched_btn.configure(state="disabled")

    def _on_row_select(self, row):
        """Enable + relabel the Ignore button based on the selected row's status."""
        if not row:
            self._ignore_btn.configure(state="disabled", text="Ignore")
            return
        status = row.get("bulk_status", "")
        if status == "Will replace":
            self._ignore_btn.configure(state="normal", text="Ignore")
        elif status == "Ignored":
            self._ignore_btn.configure(state="normal", text="Don't ignore")
        else:
            self._ignore_btn.configure(state="disabled", text="Ignore")

    def _on_replace_matched(self):
        """Confirm + spawn the BulkReplaceJob over rows currently 'Will replace'."""
        if self._state != "MATCHED":
            return

        # Snapshot the work — only rows still marked Will replace go in.
        # The row dict travels with each item so the worker can derive
        # body_targets (referencing pages/discussions/etc.) from each
        # row's source_page_url list without re-querying the table.
        items = []
        for idx in range(self._table.get_row_count()):
            row = self._table.get_row(idx)
            if not row or row.get("bulk_status") != "Will replace":
                continue
            cid = row.get("canvas_file_id")
            local_name = row.get("local_match")
            if cid and local_name and self._folder:
                local_path = os.path.join(self._folder, local_name)
                items.append((cid, local_path, row))
        if not items:
            return

        course_name = (self._viewer._current_data or {}).get("course_name", "this course")
        if not show_dialog(
            self.dialog, "Bulk Replace",
            f"Replace {len(items)} files in {course_name}?\n\nThis cannot be undone.",
            dialog_type="confirm",
        ):
            return

        # Auth pre-check (perform_replace also bootstraps but a missing token
        # gives a clearer error here than a row of generic Failed entries).
        from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata
        load_config_data_from_appdata()
        if not set_canvas_api_key_to_environment_variable():
            show_dialog(self.dialog, "Authentication Error",
                        "Canvas API token not found. Run a scan first or configure your API token.",
                        dialog_type="error")
            return

        # Snapshot the static counts that go into the final summary line.
        ignored = already = not_matched = 0
        for idx in range(self._table.get_row_count()):
            row = self._table.get_row(idx) or {}
            status = row.get("bulk_status", "")
            if status == "Ignored":
                ignored += 1
            elif status == "Already replaced":
                already += 1
            elif status in ("No match", "Ambiguous"):
                not_matched += 1
        self._initial_counts = {
            "ignored": ignored,
            "already_replaced": already,
            "not_matched": not_matched,
        }

        # Enter RUNNING — lock the controls that mustn't change mid-run.
        self._state = "RUNNING"
        self._select_folder_btn.configure(state="disabled")
        self._replace_matched_btn.configure(state="disabled")
        self._ignore_btn.configure(state="disabled", text="Ignore")
        self._counter_label.configure(text=f"0 / {len(items)} processed…")

        self._job = BulkReplaceJob(self, self._viewer, items)
        self._job.start()

    def _find_row_idx_by_canvas_file_id(self, cid):
        """Resolve a row's current index — robust against re-sorts during a run."""
        for idx in range(self._table.get_row_count()):
            row = self._table.get_row(idx)
            if row and row.get("canvas_file_id") == cid:
                return idx
        return -1

    def _on_file_starting(self, cid):
        """Worker about to start work on this file. Mark amber 'Replacing…'."""
        idx = self._find_row_idx_by_canvas_file_id(cid)
        if idx < 0:
            return
        row = self._table.get_row(idx)
        if row:
            row["bulk_status"] = "Replacing…"
            row["bulk_color"] = "Replacing…"
            self._table.update_row(idx, row)

    def _on_file_progress(self, cid, stage, bytes_read, total):
        """Worker thread's on_progress callback marshalled here. Updates the
        row's display text per stage; the color tag stays 'Replacing…' so
        the row stays amber throughout."""
        idx = self._find_row_idx_by_canvas_file_id(cid)
        if idx < 0:
            return
        row = self._table.get_row(idx)
        if not row:
            return
        if stage == "uploading" and total:
            pct = int(bytes_read * 100 / total) if total else 0
            text = (f"Uploading {_format_bytes(bytes_read)} / "
                    f"{_format_bytes(total)} ({pct}%)")
        elif stage == "fetching":
            text = "Fetching…"
        elif stage == "notifying":
            text = "Notifying…"
        elif stage == "confirming":
            text = "Confirming…"
        else:
            return  # 'done' is handled by _on_file_complete
        row["bulk_status"] = text
        row["bulk_color"] = "Replacing…"
        self._table.update_row(idx, row)

    def _on_file_complete(self, cid, status, apply_replaced=False):
        """Worker finished a file. status is 'Done' / 'Failed' / 'Skipped'."""
        idx = self._find_row_idx_by_canvas_file_id(cid)
        if idx >= 0:
            row = self._table.get_row(idx)
            if row:
                row["bulk_status"] = status
                row["bulk_color"] = status   # static state — color follows display
                self._table.update_row(idx, row)
        if apply_replaced:
            try:
                self._viewer._apply_replaced_to_ui(cid)
            except Exception:
                log.exception("_apply_replaced_to_ui failed for canvas_file_id=%s", cid)
        self._update_running_counter()

    def _update_running_counter(self):
        """Live counter shown during RUNNING."""
        if not self._job:
            return
        total = len(self._job.items)
        done = (self._job.replaced_count + self._job.failed_count
                + self._job.skipped_count)
        self._counter_label.configure(
            text=(f"{done} / {total} processed — "
                  f"{self._job.replaced_count} replaced, "
                  f"{self._job.failed_count} failed, "
                  f"{self._job.skipped_count} skipped"),
        )

    def _on_preflight_started(self, payload):
        """Orchestrator started pre-flight before any replacement. Show
        the validation state in the counter line — per-row state stays
        at 'Will replace' until a real file_started event fires."""
        total = payload.get("total_files", 0) if isinstance(payload, dict) else 0
        self._counter_label.configure(
            text=f"Pre-flight check: validating {total} file(s)…",
        )

    def _on_preflight_failed(self, payload):
        """Orchestrator aborted before any replacement. Mark each failed
        row with the reason; update the counter to make it clear NO
        changes happened. _on_job_done fires right after and respects
        this state (doesn't overwrite our counter)."""
        failed_files = (payload or {}).get("failed_files", [])
        for r in failed_files:
            cid_int = r.old_file_id
            cid = (self._job._cid_back.get(cid_int, cid_int)
                   if self._job else cid_int)
            idx = self._find_row_idx_by_canvas_file_id(cid)
            if idx < 0:
                continue
            row = self._table.get_row(idx)
            if not row:
                continue
            row["bulk_status"] = f"Pre-flight failed: {r.status}"
            row["bulk_color"] = "Failed"
            self._table.update_row(idx, row)
        self._counter_label.configure(
            text=(f"Pre-flight failed for {len(failed_files)} file(s). "
                  "NO changes were made to Canvas — fix the issues and retry."),
        )

    def _on_job_done(self):
        """Worker thread finished. Enter DONE state and show the summary."""
        self._state = "DONE"
        try:
            # Re-enable the button (it may have been disabled mid-cancel) and
            # rename it to "Close" since there's nothing to cancel anymore.
            self._cancel_btn.configure(text="Close", state="normal")
        except Exception:
            pass
        # Pre-flight aborts already wrote their own counter line via
        # _on_preflight_failed; don't overwrite with the normal summary
        # (which would show all zeros since nothing ran).
        if (self._job and self._job.orch
                and self._job.orch.summary.get("early") == "preflight_failed"):
            return
        a = self._job.replaced_count if self._job else 0
        b = self._initial_counts.get("ignored", 0)
        c = self._initial_counts.get("already_replaced", 0)
        d = self._job.failed_count if self._job else 0
        e = self._initial_counts.get("not_matched", 0)
        self._counter_label.configure(
            text=(f"Done — {a} replaced, {b} ignored, {c} already-replaced, "
                  f"{d} failed, {e} not matched"),
        )

    def _on_ignore_clicked(self):
        """Toggle the selected row's bulk_status between Will replace and Ignored."""
        idx = self._table.get_selected_index()
        if idx < 0:
            return
        row = self._table.get_row(idx)
        if not row:
            return
        status = row.get("bulk_status", "")
        if status == "Will replace":
            row["bulk_status"] = "Ignored"
            row["bulk_color"] = "Ignored"
        elif status == "Ignored":
            row["bulk_status"] = "Will replace"
            row["bulk_color"] = "Will replace"
        else:
            return  # button shouldn't be enabled in other states; defensive no-op
        self._table.update_row(idx, row)
        self._recompute_counts_and_buttons()
        # The selected row's status just changed — refresh the button label.
        self._on_row_select(row)

    def _close(self):
        """Cancel button / X / Escape handler.

        During RUNNING: prompt for confirmation; on Yes signal cancel to the
        worker but keep the dialog open until the in-flight upload finishes
        and _on_job_done fires. Repeat clicks while a cancel is already in
        flight are silent no-ops.
        Otherwise: release the modal grab, destroy the window, re-enable
        the parent button.
        """
        if self._state == "RUNNING" and self._job and self._job.is_running():
            if self._job.cancel_event.is_set():
                return  # cancel already pending; ignore repeat clicks
            confirmed = show_dialog(
                self.dialog, "Cancel Bulk Replace",
                "Cancel bulk replace?\n\nThe current upload will finish first; "
                "remaining files will be skipped.",
                dialog_type="confirm",
            )
            if not confirmed:
                return
            self._job.cancel()
            try:
                self._cancel_btn.configure(text="Cancelling…", state="disabled")
            except Exception:
                pass
            return
        try:
            self.dialog.grab_release()
        except Exception:
            pass
        try:
            self.dialog.destroy()
        except Exception:
            pass
        if getattr(self._viewer, "_bulk_dialog", None) is self:
            self._viewer._bulk_dialog = None
            try:
                self._viewer._update_bulk_replace_btn_state()
            except Exception:
                pass


class BulkReplaceJob:
    """Owns the worker thread that runs ContentUpdateOrchestrator over a
    snapshot of (canvas_file_id, local_path) pairs. The orchestrator
    pre-flights ALL files atomically before any replacement, then runs
    each file replace, emitting per-file events that this class marshals
    to the dialog's row handlers.

    Atomicity: if any file fails pre-flight (e.g. wrong canvas_file_id,
    extension mismatch detected from Canvas metadata), the entire batch
    aborts before any file is touched. The dialog surfaces this via
    _on_preflight_failed.

    Cancel: cancel_event is honored at orchestrator stage boundaries.
    A cancel during an in-flight upload waits for that upload to finish
    (Canvas's notify/upload/confirm is not abortable mid-stream); the
    remaining files in the batch then get 'cancelled' reports, which we
    marshal as 'Skipped' rows.
    """

    def __init__(self, dialog, viewer, items):
        self.dialog = dialog
        self.viewer = viewer
        # items: list[(canvas_file_id, local_path, row)]. The row dict
        # travels with each item so _run can derive body_targets from
        # source_page_url without re-querying the table from a worker
        # thread.
        self.items = list(items)
        self.cancel_event = threading.Event()
        self.thread = None
        self.orch = None  # ContentUpdateOrchestrator after _run completes
        # Outcome tallies — only the worker thread mutates these, and the
        # UI thread only reads them after a marshalled callback fires, so
        # no lock is needed.
        self.replaced_count = 0
        self.failed_count = 0
        self.skipped_count = 0
        # Per-file throttle state — keyed by int canvas_file_id (orchestrator
        # normalizes to int). Single writer (this worker thread).
        self._throttle = {}
        # Reverse map for cid: orchestrator events carry int old_file_id, but
        # dialog rows may store canvas_file_id as int or str (depending on
        # how the scan serialized it). Round-trip via this map so the
        # dialog's _find_row_idx_by_canvas_file_id equality check works.
        self._cid_back = {int(cid): cid for cid, _, _ in self.items}

    def start(self):
        self.thread = threading.Thread(
            target=self._run, daemon=True, name="canvas-bulk-replace",
        )
        self.thread.start()

    def cancel(self):
        self.cancel_event.set()

    def is_running(self):
        return self.thread is not None and self.thread.is_alive()

    def _run(self):
        course_id = (self.viewer._current_data or {}).get("course_id")
        parent = self.viewer._parent
        replacements = [(int(cid), path) for cid, path, _ in self.items]
        body_targets = derive_body_targets([row for _, _, row in self.items])
        try:
            from core.orchestrator import replace_content
            self.orch = replace_content(
                course_id=course_id,
                replacements=replacements,
                body_targets=body_targets,
                on_event=self._marshal,
                cancel_event=self.cancel_event,
                bootstrap_auth=False,
            )
        except Exception:
            log.exception("Unhandled error in bulk replace worker")
        parent.after(0, self.dialog._on_job_done)

    def _marshal(self, stage, payload):
        """Worker -> UI bridge. Translates orchestrator events into the
        dialog's existing per-row handlers and the new pre-flight ones.
        Always runs on the worker thread; all UI updates go through
        parent.after(0, ...).
        """
        parent = self.viewer._parent

        if stage == "preflight_started":
            parent.after(0, self.dialog._on_preflight_started, dict(payload))
            return

        if stage == "preflight_failed":
            parent.after(0, self.dialog._on_preflight_failed, dict(payload))
            return

        if stage == "file_started":
            cid = self._cid_back.get(payload["old_file_id"], payload["old_file_id"])
            parent.after(0, self.dialog._on_file_starting, cid)
            return

        if stage == "file_progress":
            int_cid = payload["old_file_id"]
            cid = self._cid_back.get(int_cid, int_cid)
            sub = payload.get("stage")
            b = payload.get("bytes_read", 0) or 0
            t = payload.get("total", 0) or 0
            tstate = self._throttle.setdefault(
                int_cid, {"last_emit": 0.0, "last_stage": None})
            now = time.monotonic()
            if (sub != tstate["last_stage"]
                    or sub == "done"
                    or now - tstate["last_emit"] >= _PROGRESS_THROTTLE_SEC):
                tstate["last_emit"] = now
                tstate["last_stage"] = sub
                parent.after(0, self.dialog._on_file_progress, cid, sub, b, t)
            return

        if stage == "file_done":
            int_cid = payload["old_file_id"]
            cid = self._cid_back.get(int_cid, int_cid)
            rep = payload["report"]
            if rep.status == "replaced":
                self.replaced_count += 1
                parent.after(0, self.dialog._on_file_complete, cid, "Done", True)
            elif rep.status == "cancelled":
                self.skipped_count += 1
                parent.after(0, self.dialog._on_file_complete, cid, "Skipped", False)
            else:
                self.failed_count += 1
                parent.after(0, self.dialog._on_file_complete, cid, "Failed", False)
            return

        # Other orchestrator events (mapping_built, body_*, complete) are
        # informational for this flow — body_targets is always empty in
        # bulk replace today. _on_job_done reads orch.summary directly.


def start_bulk_replace(viewer):
    """Entry point for the Content Viewer's Bulk Replace button."""
    if not viewer._current_data:
        return
    if getattr(viewer, "_bulk_dialog", None) is not None:
        # Already open — bring it to front instead of opening a second one.
        try:
            viewer._bulk_dialog.dialog.lift()
            viewer._bulk_dialog.dialog.focus_force()
        except Exception:
            pass
        return
    BulkReplaceDialog(viewer)
