"""Framework-agnostic helpers for the file-replace flows.

These are the pure functions the original ``gui/file_replace.py`` defined, lifted
here so the wx GUI can use them without importing customtkinter (the old module
imports ctk at top level). The old module keeps its own copies untouched; this
is the canonical home for the new GUI.

Covers: Canvas source-URL parsing, body-target derivation, readable URL labels,
local↔Canvas file matching, the (replaced) title suffix, content.json mutation,
and byte formatting.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

log = logging.getLogger(__name__)

REPLACED_SUFFIX = " - (replaced)"

_DOC_EXT_CACHE = None

# Canvas URL forms → (resource_type matching core.replace.RESOURCE_TYPES).
_SOURCE_URL_PATTERNS = [
    (re.compile(r"/courses/[^/]+/pages/([^/?#]+)"),         "page"),
    (re.compile(r"/courses/[^/]+/discussion_topics/(\d+)"), "discussion"),
    (re.compile(r"/courses/[^/]+/announcements/(\d+)"),     "discussion"),
    (re.compile(r"/courses/[^/]+/assignments/(\d+)"),       "assignment"),
    (re.compile(r"/courses/[^/]+/quizzes/(\d+)"),           "quiz"),
]


def parse_canvas_source_url(url: str) -> Optional[Tuple[str, str]]:
    """Parse a Canvas source-page URL into (resource_type, identifier).

    Returns None for URLs with no rewritable body (modules, /files listing,
    course shell, malformed).
    """
    if not isinstance(url, str) or not url:
        return None
    for pattern, resource_type in _SOURCE_URL_PATTERNS:
        match = pattern.search(url)
        if match:
            return resource_type, match.group(1)
    return None


def derive_body_targets(rows) -> List[Tuple[str, str]]:
    """Map content rows to the orchestrator's deduped body_targets list.

    Reads each row's ``source_page_url`` (list or legacy string), parses each
    URL, drops non-rewritable ones, and dedupes by (resource_type, identifier)
    preserving first-seen order.
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
            if parsed is None or parsed in seen:
                continue
            seen.add(parsed)
            targets.append(parsed)
    return targets


def source_url_label(url: str) -> str:
    """Short readable label for a source-page URL (for menus/announcements)."""
    parsed = parse_canvas_source_url(url)
    if parsed:
        resource_type, identifier = parsed
        return f"{resource_type.title()}: {identifier}"
    if isinstance(url, str) and "/modules" in url:
        frag = re.search(r"#(\d+)", url)
        return f"Module: {frag.group(1)}" if frag else "Modules"
    if isinstance(url, str):
        return url if len(url) <= 60 else url[:57] + "..."
    return str(url)


def _ext_of(path_or_name):
    if not path_or_name:
        return ""
    base = os.path.basename(str(path_or_name))
    dot = base.rfind(".")
    return base[dot + 1:].lower() if dot > 0 else ""


def get_document_extensions():
    """Document-extension set derived from re.yaml (cached)."""
    global _DOC_EXT_CACHE
    if _DOC_EXT_CACHE is not None:
        return _DOC_EXT_CACHE
    exts = set()
    try:
        from config.yaml_io import read_re
        data = read_re(substitute=False)
        for pattern in data.get("document_content_regex", []):
            m = re.search(r"\\\.([a-z0-9]+)", pattern.lower())
            if m:
                exts.add(m.group(1))
    except Exception:
        pass
    if not exts:
        exts = {"pdf", "docx", "doc", "pptx", "ppt", "xlsx", "xls", "txt", "rtf"}
    _DOC_EXT_CACHE = exts
    return exts


def is_document_file(filename):
    return _ext_of(filename) in get_document_extensions()


@dataclass
class MatchResult:
    matches: list
    unmatched_local: list
    unmatched_canvas: list
    ambiguous: list
    already_replaced: list
    not_replaceable: list = field(default_factory=list)  # rows with no Canvas file behind them


def _is_replaceable_doc(doc):
    """True when the row is a Canvas-hosted file that replace can act on.

    External File rows (scraped links) have no canvas_file_id — matching one
    would build a (None, path) replace pair and crash the batch in pre-flight.
    A missing file_source is treated as Canvas for older manifests that predate
    the field (external rows never carry a canvas_file_id anyway).
    """
    return bool(doc.get("canvas_file_id")) and doc.get("file_source", "Canvas") == "Canvas"


def match_files_to_documents(folder, documents):
    """Match local files in *folder* against Canvas document rows.

    Case-insensitive exact basename match, extension-strict. A Canvas-side
    duplicate title is only "ambiguous" when a local file actually collides with
    it; duplicate titles with no local counterpart are just unmatched. Ported
    from the proven gui/file_replace.py logic. Rows that no Canvas file backs
    (External File links) are set aside as not_replaceable before matching so
    they can never produce a replace pair.
    """
    already_replaced = []
    not_replaceable = []
    eligible_docs = []
    for doc in documents:
        title = doc.get("title", "") or ""
        if not _is_replaceable_doc(doc):
            not_replaceable.append(doc)
        elif title.endswith(REPLACED_SUFFIX):
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
    except OSError:
        entries = []
    for name in entries:
        full = os.path.join(folder, name)
        if not os.path.isfile(full) or not is_document_file(full):
            continue
        key = name.casefold()
        if key in seen_local_keys:
            unmatched_local.append(full)
            continue
        seen_local_keys.add(key)
        local_files.append((key, full))

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
    return MatchResult(matches, unmatched_local, unmatched_canvas, ambiguous,
                       already_replaced, not_replaceable)


def _find_document_rows(data):
    return data.get("content", {}).get("documents", {}).get("documents", [])


def mark_row_replaced(data, canvas_file_id):
    """Append the (replaced) suffix to the matching document row. Idempotent."""
    for row in _find_document_rows(data):
        if row.get("canvas_file_id") == canvas_file_id:
            title = row.get("title") or ""
            if REPLACED_SUFFIX.strip() in title:
                return False
            row["title"] = title + REPLACED_SUFFIX
            return True
    return False


def save_content_json(path, data):
    """Write the content.json dict back to disk (pretty-printed)."""
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except OSError as e:
        log.error(f"Failed to save content.json: {e}")
        return False


def format_bytes(n):
    """Compact human byte string (e.g. '12.4 MB')."""
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
