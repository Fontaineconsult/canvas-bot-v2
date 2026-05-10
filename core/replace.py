"""Resource update primitives for Canvas link-replace work.

Two operation classes plus their report dataclasses:

  - FileReplace  — replace a Canvas file's contents with a local file.
                   Canvas's 3-step upload (notify -> bytes -> confirm).
  - UpdateBody   — base class for rewriting `/files/(\\d+)` references in
                   the body field of a Canvas resource. Subclasses bind to
                   each resource type:
                     Page, Discussion, Announcement, Assignment, Quiz.

Both classes are designed to be driven by core/orchestrator.py:
ContentUpdateOrchestrator, which runs file replacements, builds the
{old_id: new_id} mapping, then walks the UpdateBody instances. They can
also be used directly for unit-level testing — each class has its own
__main__ usage demoed at the bottom of this file.

Safety design (UpdateBody):
  __init__         fetches body, captures original_body. For Page, also
                   captures original_revision_id from
                   `GET /pages/:id/revisions/latest`.
  run(mapping)     skips when no refs in mapping; otherwise stale-checks
                   (re-fetch and compare to original_body), pushes the
                   rewritten body, then verifies (re-fetch and confirm
                   no old refs remain). On verify failure, rolls back —
                   Page rolls back via revision-revert (Canvas-native);
                   all other types re-PUT original_body.

Concurrent-edit protection comes from the stale check; Canvas-native
revision history (Page only) is the additional safety net for the
worst case (verify AND rollback both fail).
"""

import os
import re
import warnings
from dataclasses import dataclass, field
from typing import Optional

from network.api import (
    get_assignment, get_discussion, get_file, get_page, get_quiz,
    get_page_revision_latest, revert_page_to_revision,
    update_assignment, update_discussion_topic, update_page, update_quiz,
)
from network.files import notify_file_upload, upload_file_bytes, confirm_file_upload
from network.cred import set_canvas_api_key_to_environment_variable, load_config_data_from_appdata


_FILE_REF_RE = re.compile(r"/files/(\d+)\b")


# ── Reports ──

@dataclass
class FileReplaceReport:
    """Outcome of a FileReplace.run().

    Status state machine:
      not_run -> replaced
              -> fetch_failed
              -> extension_mismatch
              -> notify_failed
              -> upload_failed
              -> confirm_failed
              -> cancelled
    """
    course_id: str
    old_file_id: int
    local_path: str
    status: str = "not_run"
    error: Optional[str] = None
    new_file_id: Optional[int] = None
    original_name: Optional[str] = None


@dataclass
class UpdateBodyReport:
    """Outcome of an UpdateBody.run(mapping).

    Status state machine:
      not_run -> fetch_failed                  (init couldn't fetch)
              -> skipped                       (no refs in mapping)
              -> stale_check_failed            (couldn't re-fetch pre-push)
              -> stale                         (resource edited since init)
              -> push_failed                   (PUT didn't succeed)
              -> unverified                    (pushed, couldn't re-fetch)
              -> pushed_ok                     (pushed and verified)
              -> rolled_back                   (verify failed, rollback ok)
              -> rollback_failed               (verify AND rollback failed)
    """
    resource_type: str
    course_id: str
    identifier: str  # page_url for Page; numeric id (as str) for the others
    status: str = "not_run"
    error: Optional[str] = None
    refs_to_replace: list = field(default_factory=list)   # old ids in original_body
    refs_remaining_after_push: list = field(default_factory=list)  # old ids still there at verify
    original_revision_id: Optional[int] = None            # Page only
    rollback_path: Optional[str] = None                   # 'revision_revert' | 'rewrite_original'
    # Captured for diagnostic / manual recovery in worst-case states.
    # Populated even when not the rollback source so a follow-up can
    # paste it back if rollback_failed leaves the page in an unknown state.
    original_body: Optional[str] = None


# ── FileReplace ──

class FileReplace:
    """Replace a Canvas file's contents with a new local file.

    Construct with (course_id, old_file_id, local_path), call run(), and
    on success self.new_file_id holds the id of the newly-uploaded
    attachment. self.report is populated as the run progresses.

    Optional callbacks:
      on_progress(stage, bytes_read, total) — stage is one of
        'fetching', 'notifying', 'uploading', 'confirming', 'done'.
        bytes_read and total are only meaningful during 'uploading'.
      cancel_event — threading.Event checked between stages (NOT
        mid-upload; a cancel during the upload is honored at the next
        stage boundary).
    """

    def __init__(self, course_id, old_file_id, local_path,
                 on_progress=None, cancel_event=None):
        self.course_id = course_id
        self.old_file_id = old_file_id
        self.local_path = local_path
        self.on_progress = on_progress
        self.cancel_event = cancel_event
        self.new_file_id = None
        self.report = FileReplaceReport(
            course_id=str(course_id),
            old_file_id=int(old_file_id),
            local_path=local_path,
        )

    def preflight(self):
        """Validate inputs without modifying anything: GET the existing
        Canvas file metadata, check folder_id/filename are present, and
        verify the local file extension matches.

        Returns True if every check passes (report.status stays 'not_run').
        On failure, sets report.status to 'fetch_failed' or
        'extension_mismatch' and returns False.

        Called by ContentUpdateOrchestrator's pre-flight phase so the
        whole batch can abort BEFORE any file is replaced. run() will
        re-fetch in its own Step 0; the duplicate GET is a small cost
        for the atomicity guarantee.
        """
        existing = get_file(self.course_id, self.old_file_id)
        if not existing:
            self.report.status = "fetch_failed"
            self.report.error = f"Could not retrieve file {self.old_file_id}"
            return False

        folder_id = existing.get("folder_id")
        original_name = existing.get("display_name") or existing.get("filename")
        self.report.original_name = original_name
        if not folder_id or not original_name:
            self.report.status = "fetch_failed"
            self.report.error = "Missing folder_id or filename"
            return False

        if not self._extensions_match(original_name):
            self.report.status = "extension_mismatch"
            return False

        return True

    def run(self):
        """Run the 3-step Canvas upload. Returns True on success;
        sets self.new_file_id and self.report.status."""
        if self._cancelled():
            self.report.status = "cancelled"
            return False

        # Step 0: existing file metadata.
        self._emit("fetching")
        existing = get_file(self.course_id, self.old_file_id)
        if not existing:
            self.report.status = "fetch_failed"
            self.report.error = f"Could not retrieve file {self.old_file_id}"
            warnings.warn(
                f"File replace failed: {self.report.error}", UserWarning,
            )
            return False

        folder_id = existing.get("folder_id")
        original_name = existing.get("display_name") or existing.get("filename")
        self.report.original_name = original_name
        if not folder_id or not original_name:
            self.report.status = "fetch_failed"
            self.report.error = "Missing folder_id or filename"
            warnings.warn(f"File replace failed: {self.report.error}", UserWarning)
            return False

        if not self._extensions_match(original_name):
            self.report.status = "extension_mismatch"
            return False

        if self._cancelled():
            self.report.status = "cancelled"
            return False

        # Step 1: notify.
        self._emit("notifying")
        notify_result = notify_file_upload(
            self.course_id, original_name, os.path.getsize(self.local_path), folder_id,
        )
        if notify_result is None:
            self.report.status = "notify_failed"
            self.report.error = "Canvas refused the upload notification"
            return False
        upload_url, upload_params = notify_result

        if self._cancelled():
            self.report.status = "cancelled"
            return False

        # Step 2: upload bytes.
        filesize = os.path.getsize(self.local_path)
        self._emit("uploading", 0, filesize)

        def _on_bytes(bytes_read, total):
            self._emit("uploading", bytes_read, total)

        upload_result = upload_file_bytes(
            upload_url, upload_params, self.local_path, original_name,
            on_bytes=_on_bytes,
        )
        if upload_result is None:
            self.report.status = "upload_failed"
            self.report.error = "Bytes upload failed"
            return False

        # Branch: Canvas may short-circuit (dict) or hand back a confirm_url (str).
        if isinstance(upload_result, dict):
            file_dict = upload_result
        else:
            if self._cancelled():
                self.report.status = "cancelled"
                return False
            self._emit("confirming", filesize, filesize)
            file_dict = confirm_file_upload(upload_result)
            if file_dict is None:
                self.report.status = "confirm_failed"
                self.report.error = "Canvas confirm step failed"
                return False

        if not file_dict.get("id"):
            self.report.status = "confirm_failed"
            self.report.error = "Final response had no file id"
            return False

        self.new_file_id = file_dict["id"]
        self.report.new_file_id = self.new_file_id
        self.report.status = "replaced"
        self._emit("done", filesize, filesize)
        return True

    def _extensions_match(self, original_name):
        original_ext = os.path.splitext(original_name)[1].lower()
        local_ext = os.path.splitext(self.local_path)[1].lower()
        if original_ext != local_ext:
            self.report.error = (
                f"File type mismatch: Canvas '{original_ext}' vs local '{local_ext}'"
            )
            warnings.warn(self.report.error, UserWarning)
            return False
        return True

    def _emit(self, stage, bytes_read=0, total=0):
        if self.on_progress:
            try:
                self.on_progress(stage, bytes_read, total)
            except Exception:
                pass

    def _cancelled(self):
        return self.cancel_event is not None and self.cancel_event.is_set()


# ── UpdateBody base + subclasses ──

class UpdateBody:
    """Base class for rewriting `/files/N` references in a Canvas
    resource's body field.

    Subclasses must define:
      RESOURCE_TYPE — short name used in reports and registry lookups
                      ("page", "discussion", "announcement", ...)
      BODY_FIELD    — JSON field on the GET response holding HTML
                      ("body" for pages; "message" for discussions;
                      "description" for assignments and quizzes)
      _fetch()      — return the resource dict from Canvas
      _push(body)   — PUT the new body; return truthy on success

    Subclasses may override:
      _capture_revision_id() — for Page; default no-op
      _rollback()             — default re-PUTs original_body; Page
                                overrides to use revision-revert
    """

    RESOURCE_TYPE = "unknown"
    BODY_FIELD = "body"

    def __init__(self, course_id, identifier):
        self.course_id = course_id
        self.identifier = identifier
        self.original_body = None
        self.original_revision_id = None  # populated by Page._capture_revision_id
        self.report = UpdateBodyReport(
            resource_type=self.RESOURCE_TYPE,
            course_id=str(course_id),
            identifier=str(identifier),
            rollback_path="rewrite_original",  # default; Page overrides
        )

        fetched = self._fetch()
        if not fetched:
            self.report.status = "fetch_failed"
            self.report.error = f"Could not fetch {self.RESOURCE_TYPE} {identifier}"
            return
        self.original_body = fetched.get(self.BODY_FIELD)
        self.report.original_body = self.original_body
        self._capture_revision_id()

    # ── subclass extension points ──

    def _fetch(self):
        raise NotImplementedError

    def _push(self, body):
        raise NotImplementedError

    def _capture_revision_id(self):
        """Page overrides. Default no-op for resources without revision API."""
        pass

    def _rollback(self):
        """Default: re-PUT the original body. Page overrides to revert via
        revision id (Canvas-native, doesn't depend on local HTML round-tripping
        cleanly through the sanitizer).
        """
        if self.original_body is None:
            return False
        return bool(self._push(self.original_body))

    # ── pure helpers ──

    def rewrite(self, mapping):
        """Return a new body string with old file_ids swapped for new ones.

        `mapping` is `{old_file_id: new_file_id}`. Ids not in the mapping
        are left alone. Does not mutate self.original_body.
        """
        if not self.original_body:
            return ""

        def _swap(match):
            old = int(match.group(1))
            return f"/files/{mapping.get(old, old)}"

        return _FILE_REF_RE.sub(_swap, self.original_body)

    def refs_in_mapping(self, mapping):
        """Return the sorted unique list of old file_ids in original_body
        that also appear as keys in `mapping`."""
        if not self.original_body:
            return []
        found = {
            int(m.group(1)) for m in _FILE_REF_RE.finditer(self.original_body)
            if int(m.group(1)) in mapping
        }
        return sorted(found)

    # ── orchestration entry point ──

    def run(self, mapping):
        """Stale-check, push, verify, rollback-if-needed.

        Returns True for `pushed_ok` and `skipped`; False for any state
        that left work undone or required rollback. Caller inspects
        self.report for the precise outcome.
        """
        if self.report.status == "fetch_failed":
            return False

        refs = self.refs_in_mapping(mapping)
        self.report.refs_to_replace = refs
        if not refs:
            self.report.status = "skipped"
            return True

        # Stale-check: re-fetch and compare to original_body. If a user
        # edited the resource since __init__, abort rather than overwrite
        # their work.
        current = self._fetch()
        if not current:
            self.report.status = "stale_check_failed"
            self.report.error = "Could not re-fetch for stale check"
            return False
        current_body = current.get(self.BODY_FIELD)
        if current_body != self.original_body:
            self.report.status = "stale"
            self.report.error = (
                f"{self.RESOURCE_TYPE} was modified between fetch and push; "
                "skipping to preserve concurrent edits"
            )
            return False

        # Push.
        new_body = self.rewrite(mapping)
        if not self._push(new_body):
            self.report.status = "push_failed"
            self.report.error = "PUT failed"
            return False

        # Verify: re-fetch, scan for any old ids from the mapping that
        # remain. We use functional verification rather than strict
        # string equality because Canvas normalizes HTML (whitespace,
        # attribute order, entity encoding) on PUT — a successful push
        # routinely produces a body that's not byte-identical to what
        # we sent.
        verified = self._fetch()
        if not verified:
            self.report.status = "unverified"
            self.report.error = "Could not re-fetch to verify push"
            return False
        verified_body = verified.get(self.BODY_FIELD, "") or ""
        remaining = sorted({
            int(m.group(1)) for m in _FILE_REF_RE.finditer(verified_body)
            if int(m.group(1)) in mapping
        })
        if remaining:
            self.report.refs_remaining_after_push = remaining
            self.report.error = (
                f"Verify failed: old file ids still present after push: {remaining}"
            )
            if self._rollback():
                self.report.status = "rolled_back"
            else:
                self.report.status = "rollback_failed"
            return False

        self.report.status = "pushed_ok"
        return True


class Page(UpdateBody):
    RESOURCE_TYPE = "page"
    BODY_FIELD = "body"

    def _fetch(self):
        return get_page(self.course_id, self.identifier)

    def _push(self, body):
        return bool(update_page(self.course_id, self.identifier, body))

    def _capture_revision_id(self):
        rev = get_page_revision_latest(self.course_id, self.identifier)
        if rev:
            self.original_revision_id = rev.get("revision_id")
            self.report.original_revision_id = self.original_revision_id
        # Mark this instance as using the Canvas-native rollback path.
        self.report.rollback_path = "revision_revert"

    def _rollback(self):
        """Revert to the revision captured at __init__. Stronger than the
        base re-PUT path: Canvas-native, no HTML re-sanitization risk, and
        restores all revisioned fields (title, editing roles) — not just
        body. If the revision wasn't captured (init-time GET failed), fall
        back to the base re-PUT.
        """
        if self.original_revision_id is None:
            return super()._rollback()
        result = revert_page_to_revision(
            self.course_id, self.identifier, self.original_revision_id,
        )
        return bool(result)


class Discussion(UpdateBody):
    RESOURCE_TYPE = "discussion"
    BODY_FIELD = "message"

    def _fetch(self):
        return get_discussion(self.course_id, self.identifier)

    def _push(self, body):
        return bool(update_discussion_topic(self.course_id, self.identifier, body))


class Announcement(Discussion):
    """Announcements are discussion_topics with is_announcement=true; the
    GET and PUT endpoints are identical to discussions. Subclassing
    Discussion (rather than UpdateBody) keeps the fetch/push wiring DRY
    while still giving the orchestrator a distinct resource_type for
    reports."""
    RESOURCE_TYPE = "announcement"


class Assignment(UpdateBody):
    RESOURCE_TYPE = "assignment"
    BODY_FIELD = "description"

    def _fetch(self):
        return get_assignment(self.course_id, self.identifier)

    def _push(self, body):
        return bool(update_assignment(self.course_id, self.identifier, body))


class Quiz(UpdateBody):
    RESOURCE_TYPE = "quiz"
    BODY_FIELD = "description"

    def _fetch(self):
        return get_quiz(self.course_id, self.identifier)

    def _push(self, body):
        return bool(update_quiz(self.course_id, self.identifier, body))


# ── Resource-type registry (used by ContentUpdateOrchestrator) ──

RESOURCE_TYPES = {
    "page":         Page,
    "discussion":   Discussion,
    "announcement": Announcement,
    "assignment":   Assignment,
    "quiz":         Quiz,
}


# ── Manual / live-test harness ──

if __name__ == "__main__":
    set_canvas_api_key_to_environment_variable()
    load_config_data_from_appdata()

    def show(stage, b, t):
        print(f"  {stage}: {b}/{t}" if stage == "uploading" else f"  {stage}")

    # Example 1: replace a file.
    fr = FileReplace("21016", 9164373, r"C:\some\replacement.pdf", on_progress=show)
    ok = fr.run()
    print(f"FileReplace: {fr.report.status} new_id={fr.report.new_file_id}")

    # Example 2: rewrite a page (after a successful FileReplace gives us new_file_id).
    if ok and fr.new_file_id:
        page = Page("21016", "embeded-links")
        page.run({fr.old_file_id: fr.new_file_id})
        print(f"Page: {page.report.status} refs={page.report.refs_to_replace}")
