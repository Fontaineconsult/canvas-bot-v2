"""CLI handler for the --replace_pair / --rewrite_target flow in canvas_bot.py.

Wraps `core.orchestrator.replace_content` with argument validation and a
stdout event formatter matching canvas_bot.py's print convention
([OK] / [!] / [ERROR] prefixes, \\r-throttled upload progress).

The caller (canvas_bot.py) is responsible for auth bootstrap before
invoking `run()`. We pass `bootstrap_auth=False` to replace_content so
the prompt-on-missing-token UX in the CLI's auth helpers is preserved.

Returns an integer exit code:
  0 — file replaced AND all bodies are pushed_ok or skipped
  1 — argument or operation error (file not found, bogus old id,
       any body failure other than skipped/pushed_ok, file replace failed)
  2 — replace_content returned None (auth bootstrap failure path; only
       reachable if the caller passes bootstrap_auth=True, which the
       canvas_bot.py CLI does not — kept for safety).
"""

import os
import sys
import time

import click

from core.orchestrator import replace_content


_PROGRESS_THROTTLE_SEC = 0.1


def _make_event_formatter():
    """Build an on_event callback that prints stdout updates matching
    canvas_bot.py's existing convention. Returns the closure."""
    state = {"last_emit": 0.0, "last_sub": None, "in_upload": False}

    def _emit(stage, payload):
        if stage == "preflight_started":
            tf = payload.get("total_files", 0)
            tb = payload.get("total_bodies", 0)
            print(f"Pre-flight: validating {tf} file(s) and {tb} body target(s)...")

        elif stage == "preflight_body_checked":
            if not payload.get("ok"):
                print(f"  [FAIL] {payload['resource_type']}/{payload['identifier']}: "
                      f"{payload.get('status')} - {payload.get('error')}")

        elif stage == "preflight_file_checked":
            if not payload.get("ok"):
                print(f"  [FAIL] file {payload['old_file_id']}: "
                      f"{payload.get('status')} - {payload.get('error')}")

        elif stage == "preflight_complete":
            ff = payload.get("failed_files", 0)
            fb = payload.get("failed_bodies", 0)
            if ff == 0 and fb == 0:
                print("[OK] Pre-flight passed - all targets reachable.")
            # On failure, the preflight_failed event prints the abort message.

        elif stage == "preflight_failed":
            print("\n[ABORTED] Pre-flight check failed - NO changes were made to Canvas.")
            failed_bodies = payload.get("failed_bodies", [])
            if failed_bodies:
                print("\nBody targets that failed:")
                for r in failed_bodies:
                    msg = r.error or r.status
                    print(f"  - {r.resource_type}/{r.identifier}: {r.status} - {msg}")
            failed_files = payload.get("failed_files", [])
            if failed_files:
                print("\nFiles that failed:")
                for r in failed_files:
                    msg = r.error or r.status
                    print(f"  - {r.old_file_id}: {r.status} - {msg}")
            print()

        elif stage == "file_started":
            print(f"\nReplacing Canvas file {payload['old_file_id']} "
                  f"with {os.path.basename(payload['local_path'])}...")
            state["in_upload"] = False

        elif stage == "file_progress":
            sub = payload.get("stage")
            now = time.monotonic()
            if (sub == state["last_sub"]
                    and sub != "done"
                    and now - state["last_emit"] < _PROGRESS_THROTTLE_SEC):
                return
            state["last_emit"] = now
            state["last_sub"] = sub
            if sub == "uploading" and payload.get("total"):
                pct = int(payload["bytes_read"] * 100 / payload["total"])
                sys.stdout.write(f"\r  uploading {pct}%   ")
                sys.stdout.flush()
                state["in_upload"] = True
            else:
                if state["in_upload"]:
                    sys.stdout.write("\n")
                    state["in_upload"] = False
                print(f"  {sub}")

        elif stage == "file_done":
            if state["in_upload"]:
                sys.stdout.write("\n")
                state["in_upload"] = False
            rep = payload["report"]
            if rep.status == "replaced":
                print(f"[OK] File replaced - new id {rep.new_file_id}")
            elif rep.status == "cancelled":
                print("[!] File replace cancelled")
            else:
                msg = rep.error or rep.status
                print(f"[ERROR] File replace failed ({rep.status}): {msg}")

        elif stage == "mapping_built":
            m = payload["mapping"]
            if m:
                pairs = ", ".join(f"{o}->{n}" for o, n in m.items())
                print(f"[OK] Mapping built: {pairs}")
            else:
                print("[!] No successful replacements - body rewrites will be skipped")

        elif stage == "body_started":
            print(f"\nRewriting {payload['resource_type']}/{payload['identifier']}...")

        elif stage == "body_done":
            rep = payload["report"]
            if rep.status == "pushed_ok":
                print(f"[OK] Rewrote {len(rep.refs_to_replace)} reference(s)")
            elif rep.status == "skipped":
                print("[!] Skipped - no refs in mapping")
            elif rep.status == "stale":
                print("[!] Skipped - resource modified between fetch and push")
            elif rep.status == "rolled_back":
                print(f"[!] Verify failed; rolled back to original ({rep.rollback_path})")
            elif rep.status == "rollback_failed":
                print("[ERROR] Verify AND rollback both failed - manual recovery needed")
                if rep.original_revision_id:
                    print(f"        Recoverable: revert to revision id "
                          f"{rep.original_revision_id} via Canvas UI")
            elif rep.status == "unverified":
                print("[!] Pushed but could not re-fetch to verify")
            else:
                msg = rep.error or rep.status
                print(f"[ERROR] {rep.status}: {msg}")

        elif stage == "complete":
            s = payload["summary"]
            # On preflight abort, skip the per-phase summary lines — they're
            # all zeros (no phases ran) and the preflight_failed event
            # already showed what went wrong.
            if s.get("early") == "preflight_failed":
                return
            print("\n=== Summary ===")
            print(f"  Files:  {s['files_replaced']} replaced, "
                  f"{s['files_failed']} failed, "
                  f"{s['files_cancelled']} cancelled")
            print(f"  Bodies: {s['bodies_pushed_ok']} ok, "
                  f"{s['bodies_skipped']} skipped, "
                  f"{s['bodies_stale']} stale, "
                  f"{s['bodies_rolled_back']} rolled-back, "
                  f"{s['bodies_rollback_failed']} ROLLBACK-FAILED, "
                  f"{s['bodies_unverified']} unverified, "
                  f"{s['bodies_failed_other']} other")

    return _emit


def run(course_id, replace_pair, rewrite_target):
    """Run the orchestrator path. Caller must have already done auth bootstrap.

    Args:
        course_id: Canvas course id (string).
        replace_pair: 2-tuple (OLD_FILE_ID_STR, LOCAL_PATH) from Click.
        rewrite_target: tuple of 2-tuples (RESOURCE_TYPE, IDENTIFIER), possibly empty.

    Returns:
        Exit code (int). See module docstring.
    """
    if not course_id:
        click.echo("Error: --replace_pair requires --course_id.")
        return 1

    old_id_raw, local_path = replace_pair
    try:
        old_file_id = int(old_id_raw)
    except ValueError:
        click.echo(f"Error: --replace_pair OLD_FILE_ID must be an integer "
                   f"(got '{old_id_raw}').")
        return 1
    if not os.path.isfile(local_path):
        click.echo(f"Error: File not found: {local_path}")
        return 1

    orch = replace_content(
        course_id=course_id,
        replacements=[(old_file_id, local_path)],
        body_targets=list(rewrite_target),
        on_event=_make_event_formatter(),
        bootstrap_auth=False,
    )
    if orch is None:
        return 2

    s = orch.summary
    if s.get("early") == "preflight_failed":
        return 1
    ok = (s["files_replaced"] == 1
          and s["files_failed"] == 0
          and s["bodies_rollback_failed"] == 0
          and s["bodies_unverified"] == 0
          and s["bodies_stale"] == 0
          and s["bodies_failed_other"] == 0)
    return 0 if ok else 1
