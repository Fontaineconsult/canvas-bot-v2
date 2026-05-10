"""ContentUpdateOrchestrator — composes FileReplace + UpdateBody for a
full Canvas link-replace operation.

Usage::

    orch = ContentUpdateOrchestrator(
        course_id="21016",
        replacements=[(9164373, r"C:\\path\\to\\replacement.pdf")],
        body_targets=[("page", "embeded-links")],
        on_event=my_callback,
    )
    orch.run()
    # orch.file_reports, orch.body_reports, orch.mapping, orch.summary

Design:
  - Sync API. Caller threads (GUI worker thread; CLI main thread under a
    SIGINT handler).
  - Lenient on partial file failure: a partial mapping still drives body
    rewrites for the files that did succeed. Bodies whose only refs are
    in failed-replace ids get `skipped` (the unaffected refs in the
    mapping aren't there to rewrite).
  - Scanner is OUT of scope. Caller scans, builds body_targets, hands
    them in. Keeps this class testable without a network mock of every
    Canvas content surface.
  - Cancel is checked between each file and each body. Mid-stage cancel
    inside FileReplace is honored by FileReplace itself.
  - Pre-flight is atomic: every UpdateBody is constructed (does GET) and
    every FileReplace runs preflight() (GET + extension check) BEFORE
    any modification. If anything fails, the whole operation aborts —
    no files touched, no bodies pushed. summary['early'] tells you why.
  - One callback shape: on_event(stage: str, payload: dict). Stages:
        preflight_started        {total_files, total_bodies}
        preflight_body_checked   {resource_type, identifier, ok, status, error}
        preflight_file_checked   {old_file_id, ok, status, error}
        preflight_complete       {failed_files, failed_bodies}
        preflight_failed         {failed_files: [reports], failed_bodies: [reports]}
        file_started             {idx, total, old_file_id, local_path}
        file_progress            {old_file_id, stage, bytes_read, total}
        file_done                {old_file_id, report}
        mapping_built            {mapping}
        body_started             {idx, total, resource_type, identifier}
        body_done                {resource_type, identifier, report}
        complete                 {summary}
"""

import logging
import warnings
from typing import Callable, Dict, List, Optional, Tuple

from core.replace import (
    FileReplace, FileReplaceReport,
    UpdateBodyReport,
    RESOURCE_TYPES,
)
from network.cred import (
    load_config_data_from_appdata,
    set_canvas_api_key_to_environment_variable,
)

log = logging.getLogger(__name__)


class ContentUpdateOrchestrator:
    def __init__(
        self,
        course_id,
        replacements: List[Tuple[int, str]],
        body_targets: Optional[List[Tuple[str, object]]] = None,
        cancel_event=None,
        on_event: Optional[Callable[[str, dict], None]] = None,
    ):
        self.course_id = course_id
        self.replacements = list(replacements)
        self.body_targets = list(body_targets or [])
        self.cancel_event = cancel_event
        self.on_event = on_event

        self.file_reports: List[FileReplaceReport] = []
        self.body_reports: List[UpdateBodyReport] = []
        self.mapping: Dict[int, int] = {}
        self.summary: dict = {}

        # Pre-flight failure accumulators. Populated by _preflight();
        # consumed by _emit_preflight_failed() if non-empty. Kept
        # separate from file_reports / body_reports so the existing
        # replace/update phases (which build their own reports from
        # scratch) stay untouched.
        self._preflight_failed_files: List[FileReplaceReport] = []
        self._preflight_failed_bodies: List[UpdateBodyReport] = []

    # ── public entry ──

    def run(self):
        """Drive the pipeline: pre-flight, replace files, build mapping,
        rewrite bodies, emit complete. Returns self for chaining.

        Pre-flight is atomic: any failure aborts before any modification.
        On pass, the existing replace and body-update phases run
        unchanged — preflight is an additional gate, not a replacement
        for their internal validation.
        """
        self._preflight()
        if self._cancelled():
            self._finalize(early="cancelled_during_preflight")
            return self
        if self._preflight_failed_files or self._preflight_failed_bodies:
            self._emit_preflight_failed()
            self._finalize(early="preflight_failed")
            return self

        self._do_replacements()
        self._build_mapping()
        if self._cancelled():
            self._finalize(early="cancelled_after_files")
            return self
        self._do_body_updates()
        self._finalize()
        return self

    # ── phase 0: pre-flight (no modifications) ──

    def _preflight(self):
        """Validate every body target and every file BEFORE any
        modification. For bodies: construct each UpdateBody (its __init__
        does the GET + revision-id capture); on failure, accumulate the
        report. For files: instantiate a temporary FileReplace and call
        preflight() (GET + extension check); on failure, accumulate.

        Constructed instances are discarded — the existing
        _do_replacements and _do_body_updates phases re-fetch and
        re-construct on their own. This keeps the existing code paths
        untouched at the cost of one extra GET per target on the
        success path. Cheap; the safety guarantee is worth it.
        """
        self._emit("preflight_started",
                   total_files=len(self.replacements),
                   total_bodies=len(self.body_targets))

        for resource_type, identifier in self.body_targets:
            if self._cancelled():
                return
            cls = RESOURCE_TYPES.get(resource_type)
            if cls is None:
                rep = UpdateBodyReport(
                    resource_type=resource_type,
                    course_id=str(self.course_id),
                    identifier=str(identifier),
                    status="unknown_resource_type",
                    error=f"No UpdateBody subclass registered for '{resource_type}'",
                )
                self._preflight_failed_bodies.append(rep)
                self._emit("preflight_body_checked",
                           resource_type=resource_type, identifier=identifier,
                           ok=False, status=rep.status, error=rep.error)
                continue
            try:
                body = cls(self.course_id, identifier)
            except Exception as exc:
                log.exception("%s.__init__ raised in preflight for %s/%s",
                              cls.__name__, resource_type, identifier)
                rep = UpdateBodyReport(
                    resource_type=resource_type,
                    course_id=str(self.course_id),
                    identifier=str(identifier),
                    status="fetch_failed",
                    error=f"Constructor exception: {exc}",
                )
                self._preflight_failed_bodies.append(rep)
                self._emit("preflight_body_checked",
                           resource_type=resource_type, identifier=identifier,
                           ok=False, status=rep.status, error=rep.error)
                continue
            if body.report.status != "not_run":
                # __init__ set status (e.g. fetch_failed). Capture and discard.
                self._preflight_failed_bodies.append(body.report)
                self._emit("preflight_body_checked",
                           resource_type=resource_type, identifier=identifier,
                           ok=False, status=body.report.status,
                           error=body.report.error)
            else:
                self._emit("preflight_body_checked",
                           resource_type=resource_type, identifier=identifier,
                           ok=True, status="not_run", error=None)

        for old_file_id, local_path in self.replacements:
            if self._cancelled():
                return
            fr = FileReplace(self.course_id, old_file_id, local_path)
            try:
                ok = fr.preflight()
            except Exception as exc:
                log.exception("FileReplace.preflight raised for %s", old_file_id)
                fr.report.status = "fetch_failed"
                fr.report.error = f"Preflight exception: {exc}"
                ok = False
            if not ok:
                self._preflight_failed_files.append(fr.report)
                self._emit("preflight_file_checked",
                           old_file_id=int(old_file_id),
                           ok=False, status=fr.report.status, error=fr.report.error)
            else:
                self._emit("preflight_file_checked",
                           old_file_id=int(old_file_id),
                           ok=True, status="not_run", error=None)

        self._emit("preflight_complete",
                   failed_files=len(self._preflight_failed_files),
                   failed_bodies=len(self._preflight_failed_bodies))

    def _emit_preflight_failed(self):
        self._emit("preflight_failed",
                   failed_files=list(self._preflight_failed_files),
                   failed_bodies=list(self._preflight_failed_bodies))

    # ── phase 1 ──

    def _do_replacements(self):
        total = len(self.replacements)
        for idx, (old_file_id, local_path) in enumerate(self.replacements):
            if self._cancelled():
                # Mark every remaining replacement as cancelled and emit
                # so the UI can grey them out.
                for old, path in self.replacements[idx:]:
                    rep = FileReplaceReport(
                        course_id=str(self.course_id),
                        old_file_id=int(old),
                        local_path=path,
                        status="cancelled",
                    )
                    self.file_reports.append(rep)
                    self._emit("file_done", old_file_id=int(old), report=rep)
                return

            self._emit(
                "file_started",
                idx=idx, total=total,
                old_file_id=int(old_file_id), local_path=local_path,
            )

            def _on_progress(stage, bytes_read, total_bytes, _ofid=int(old_file_id)):
                self._emit(
                    "file_progress",
                    old_file_id=_ofid, stage=stage,
                    bytes_read=bytes_read, total=total_bytes,
                )

            fr = FileReplace(
                self.course_id, old_file_id, local_path,
                on_progress=_on_progress, cancel_event=self.cancel_event,
            )
            try:
                fr.run()
            except Exception as exc:
                log.exception("FileReplace raised for old_file_id=%s", old_file_id)
                fr.report.status = "upload_failed"
                fr.report.error = f"Unhandled exception: {exc}"
            self.file_reports.append(fr.report)
            self._emit("file_done", old_file_id=int(old_file_id), report=fr.report)

    # ── phase 2 ──

    def _build_mapping(self):
        for r in self.file_reports:
            if r.status == "replaced" and r.new_file_id:
                self.mapping[r.old_file_id] = r.new_file_id
        self._emit("mapping_built", mapping=dict(self.mapping))

    # ── phase 3 ──

    def _do_body_updates(self):
        total = len(self.body_targets)
        for idx, (resource_type, identifier) in enumerate(self.body_targets):
            if self._cancelled():
                for rt, ident in self.body_targets[idx:]:
                    rep = UpdateBodyReport(
                        resource_type=rt,
                        course_id=str(self.course_id),
                        identifier=str(ident),
                        status="cancelled",
                    )
                    self.body_reports.append(rep)
                    self._emit("body_done",
                               resource_type=rt, identifier=ident, report=rep)
                return

            self._emit(
                "body_started",
                idx=idx, total=total,
                resource_type=resource_type, identifier=str(identifier),
            )

            cls = RESOURCE_TYPES.get(resource_type)
            if cls is None:
                rep = UpdateBodyReport(
                    resource_type=resource_type,
                    course_id=str(self.course_id),
                    identifier=str(identifier),
                    status="unknown_resource_type",
                    error=f"No UpdateBody subclass registered for '{resource_type}'",
                )
                self.body_reports.append(rep)
                self._emit("body_done",
                           resource_type=resource_type, identifier=identifier, report=rep)
                continue

            # Constructor does the initial fetch (and revision-id capture
            # for Page) and may set status='fetch_failed' on its own
            # report. We pass that through; the orchestrator only
            # synthesizes a report when the constructor itself raises.
            try:
                body = cls(self.course_id, identifier)
            except Exception as exc:
                log.exception(
                    "%s.__init__ raised for %s/%s",
                    cls.__name__, resource_type, identifier,
                )
                rep = UpdateBodyReport(
                    resource_type=resource_type,
                    course_id=str(self.course_id),
                    identifier=str(identifier),
                    status="fetch_failed",
                    error=f"Constructor exception: {exc}",
                )
                self.body_reports.append(rep)
                self._emit("body_done",
                           resource_type=resource_type, identifier=identifier, report=rep)
                continue

            try:
                body.run(self.mapping)
            except Exception as exc:
                log.exception(
                    "%s.run raised for %s/%s",
                    cls.__name__, resource_type, identifier,
                )
                body.report.status = "push_failed"
                body.report.error = f"Run exception: {exc}"

            self.body_reports.append(body.report)
            self._emit("body_done",
                       resource_type=resource_type,
                       identifier=identifier,
                       report=body.report)

    # ── completion ──

    def _finalize(self, early=None):
        files_replaced = sum(1 for r in self.file_reports if r.status == "replaced")
        files_cancelled = sum(1 for r in self.file_reports if r.status == "cancelled")
        files_failed = (len(self.file_reports) - files_replaced - files_cancelled)

        bodies_pushed_ok = sum(1 for r in self.body_reports if r.status == "pushed_ok")
        bodies_skipped = sum(1 for r in self.body_reports if r.status == "skipped")
        bodies_stale = sum(1 for r in self.body_reports if r.status == "stale")
        bodies_rolled_back = sum(1 for r in self.body_reports if r.status == "rolled_back")
        bodies_rollback_failed = sum(
            1 for r in self.body_reports if r.status == "rollback_failed"
        )
        bodies_unverified = sum(1 for r in self.body_reports if r.status == "unverified")
        bodies_failed_other = sum(
            1 for r in self.body_reports
            if r.status in ("fetch_failed", "stale_check_failed", "push_failed",
                            "unknown_resource_type", "cancelled")
        )

        # rollback_failed is the worst case — surface those reports at the
        # top level so callers can show the user where to recover. Page
        # reports carry an original_revision_id usable in Canvas's UI;
        # other types carry original_body for paste-back.
        rollback_failed_reports = [
            r for r in self.body_reports if r.status == "rollback_failed"
        ]
        unverified_reports = [
            r for r in self.body_reports if r.status == "unverified"
        ]

        self.summary = {
            "early": early,
            "files_replaced": files_replaced,
            "files_failed": files_failed,
            "files_cancelled": files_cancelled,
            "bodies_pushed_ok": bodies_pushed_ok,
            "bodies_skipped": bodies_skipped,
            "bodies_stale": bodies_stale,
            "bodies_rolled_back": bodies_rolled_back,
            "bodies_rollback_failed": bodies_rollback_failed,
            "bodies_unverified": bodies_unverified,
            "bodies_failed_other": bodies_failed_other,
            "rollback_failed_reports": rollback_failed_reports,
            "unverified_reports": unverified_reports,
            # Pre-flight failures live separately from file_reports /
            # body_reports because the existing replace/update phases
            # never ran when preflight aborted. Surface them so the CLI
            # / GUI can show what was wrong.
            "preflight_failed_files": len(self._preflight_failed_files),
            "preflight_failed_bodies": len(self._preflight_failed_bodies),
            "preflight_failed_file_reports": list(self._preflight_failed_files),
            "preflight_failed_body_reports": list(self._preflight_failed_bodies),
        }
        self._emit("complete", summary=dict(self.summary))

    # ── helpers ──

    def _emit(self, stage, **payload):
        if self.on_event:
            try:
                self.on_event(stage, dict(payload))
            except Exception:
                log.exception("on_event raised for stage %s", stage)

    def _cancelled(self):
        return self.cancel_event is not None and self.cancel_event.is_set()


# ── Single-call entry point ──

def replace_content(
    course_id,
    replacements: Optional[List[Tuple[int, str]]] = None,
    body_targets: Optional[List[Tuple[str, object]]] = None,
    on_event: Optional[Callable[[str, dict], None]] = None,
    cancel_event=None,
    bootstrap_auth: bool = True,
):
    """Run a full Canvas content update (file replacements + body rewrites).

    Thin wrapper around ContentUpdateOrchestrator. The CLI in canvas_bot.py
    drives this; the GUI worker thread will eventually too (with
    bootstrap_auth=False, since the GUI pre-flights auth on the UI thread
    before spawning the worker).

    Args:
        course_id: Canvas course id (string or int).
        replacements: list of (old_file_id, local_path) tuples. May be
            empty for body-only updates.
        body_targets: list of (resource_type, identifier) tuples. May be
            empty for file-only updates (e.g. module files with no
            embedded references).
        on_event: optional callback for progress events. None = silent.
        cancel_event: optional threading.Event for cooperative cancel.
        bootstrap_auth: when True (default), loads credentials from
            appdata and sets the API token. Pass False if the caller
            already did so.

    Returns:
        The populated ContentUpdateOrchestrator instance, or None if
        bootstrap_auth=True and no Canvas API token was found. Inspect
        orch.file_reports / orch.body_reports / orch.mapping / orch.summary
        for results.
    """
    if bootstrap_auth:
        load_config_data_from_appdata()
        if not set_canvas_api_key_to_environment_variable():
            warnings.warn(
                "Canvas API token not found — configure credentials before running",
                UserWarning,
            )
            return None

    orch = ContentUpdateOrchestrator(
        course_id=course_id,
        replacements=replacements or [],
        body_targets=body_targets or [],
        cancel_event=cancel_event,
        on_event=on_event,
    )
    orch.run()
    return orch
