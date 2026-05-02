"""GUI-side network operations.

Centralizes Canvas API calls where the GUI needs concerns the CLI doesn't —
progress callbacks, cooperative cancellation, tuple timeouts. The shared
network/api.py and network/cred.py stay in place for CLI + back-end use.
"""

import json
import logging
import os
import warnings

import requests
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

from network.api import get_file, _clean_url, _extract_error_message
from network.cred import get_access_token

log = logging.getLogger(__name__)


def replace_file_with_progress(course_id, file_id, local_path,
                               on_progress=None, cancel_event=None):
    """Replace a Canvas file with a streamed multipart upload + progress callbacks.

    Mirrors network.api.replace_file's 3-step flow (notify → upload → confirm)
    but uses requests_toolbelt.MultipartEncoderMonitor so the upload streams
    from disk to socket without buffering the whole file, and so we can report
    byte-level progress to the GUI.

    Parameters
    ----------
    course_id : str | int
    file_id : str | int
    local_path : str
        Path to the local file replacing the Canvas file.
    on_progress : callable(stage, bytes_read, total_bytes) or None
        Fired during execution. `stage` is one of:
            "fetching"    — looking up existing file metadata (step 0)
            "notifying"   — POST to /courses/{id}/files (step 1)
            "uploading"   — multipart upload in flight (step 2; bytes_read/total update)
            "confirming"  — GET to redirect Location (step 3)
            "done"        — success, returning result
        bytes_read and total_bytes are only meaningful during "uploading".
    cancel_event : threading.Event or None
        Checked between stages (NOT mid-upload — the monitor doesn't expose a
        clean abort and Canvas would have a half-uploaded file). When set,
        the function returns None at the next checkpoint.

    Returns
    -------
    dict | None
        The final file metadata dict on success, or None on failure / cancel.
    """

    def _emit(stage, bytes_read=0, total=0):
        if on_progress:
            try:
                on_progress(stage, bytes_read, total)
            except Exception:
                pass  # never let a callback bug kill the upload

    def _cancelled():
        return cancel_event is not None and cancel_event.is_set()

    # Step 0: get existing file metadata for folder_id and display_name
    _emit("fetching")
    if _cancelled():
        return None
    existing = get_file(course_id, file_id)
    if not existing:
        warnings.warn(f"File replace failed: could not retrieve file {file_id}", UserWarning)
        return None

    folder_id = existing.get("folder_id")
    original_name = existing.get("display_name") or existing.get("filename")
    if not folder_id or not original_name:
        warnings.warn("File replace failed: missing folder_id or filename from file metadata", UserWarning)
        return None

    filename = os.path.basename(local_path)
    filesize = os.path.getsize(local_path)

    # Enforce file type match (same gate as network.api.replace_file)
    original_ext = os.path.splitext(original_name)[1].lower()
    local_ext = os.path.splitext(filename)[1].lower()
    if original_ext != local_ext:
        warnings.warn(
            f"File type mismatch: Canvas file is '{original_ext}' but replacement is '{local_ext}'",
            UserWarning,
        )
        return None

    # Step 1: notify Canvas of the upload
    if _cancelled():
        return None
    _emit("notifying")

    notify_url = (f"{os.environ.get('API_PATH')}/courses/{course_id}"
                  f"/files?access_token={get_access_token()}")
    clean_notify = _clean_url(notify_url)
    try:
        resp = requests.post(notify_url, data={
            "name": original_name,
            "size": filesize,
            "parent_folder_id": folder_id,
            "on_duplicate": "overwrite",
        }, verify=True, timeout=(10, 30))
    except RequestsConnectionError as exc:
        log.error(f"Connection error during file replace step 1: {exc}")
        return None

    if resp.status_code != 200:
        log.warning(f"File replace step 1 failed: {clean_notify} | {resp.status_code}")
        try:
            error_message = _extract_error_message(json.loads(resp.content))
        except json.JSONDecodeError:
            error_message = resp.text
        warnings.warn(f"File replace failed (step 1): HTTP {resp.status_code} - {error_message}", UserWarning)
        return None

    upload_info = json.loads(resp.content)
    upload_url = upload_info.get("upload_url")
    upload_params = upload_info.get("upload_params", {})
    if not upload_url:
        log.error("File replace step 1 returned no upload_url")
        return None

    log.info(f"File replace step 1 OK: {clean_notify}")

    # Step 2: streamed multipart upload with progress monitoring
    if _cancelled():
        return None

    try:
        with open(local_path, "rb") as fh:
            fields = dict(upload_params)
            fields["file"] = (original_name, fh, "application/octet-stream")
            encoder = MultipartEncoder(fields=fields)

            def _monitor_callback(monitor):
                _emit("uploading", monitor.bytes_read, monitor.len)

            monitor = MultipartEncoderMonitor(encoder, _monitor_callback)

            resp2 = requests.post(
                upload_url,
                data=monitor,
                headers={"Content-Type": monitor.content_type},
                verify=True,
                allow_redirects=False,
                timeout=(10, 600),
            )
    except (RequestsConnectionError, OSError) as exc:
        log.error(f"Connection error during file replace step 2: {exc}")
        return None

    # Canvas returns 3xx with Location header, or 200/201 with JSON
    if resp2.status_code in (301, 302, 303):
        confirm_url = resp2.headers.get("Location")
    elif resp2.status_code in (200, 201):
        try:
            result = json.loads(resp2.content)
            if result.get("id"):
                _emit("done", filesize, filesize)
                log.info(f"File replace complete (no confirmation needed): {original_name}")
                return result
            confirm_url = result.get("location")
        except json.JSONDecodeError:
            confirm_url = None
    else:
        log.warning(f"File replace step 2 failed: {resp2.status_code}")
        try:
            error_message = _extract_error_message(json.loads(resp2.content))
        except json.JSONDecodeError:
            error_message = resp2.text
        warnings.warn(f"File replace failed (step 2): HTTP {resp2.status_code} - {error_message}", UserWarning)
        return None

    if not confirm_url:
        log.error("File replace step 2 returned no confirmation URL")
        return None

    log.info("File replace step 2 OK, confirming upload")

    # Step 3: confirm the upload (GET to the redirect Location)
    if _cancelled():
        return None
    _emit("confirming", filesize, filesize)

    try:
        separator = "&" if "?" in confirm_url else "?"
        resp3 = requests.get(
            f"{confirm_url}{separator}access_token={get_access_token()}",
            verify=True,
            timeout=(10, 30),
        )
    except RequestsConnectionError as exc:
        log.error(f"Connection error during file replace step 3: {exc}")
        return None

    if resp3.status_code in (200, 201):
        _emit("done", filesize, filesize)
        log.info(f"File replace complete: {original_name}")
        try:
            return json.loads(resp3.content)
        except json.JSONDecodeError:
            return {"status": "ok"}

    log.warning(f"File replace step 3 failed: {resp3.status_code}")
    try:
        error_message = _extract_error_message(json.loads(resp3.content))
    except json.JSONDecodeError:
        error_message = resp3.text
    warnings.warn(f"File replace failed (step 3): HTTP {resp3.status_code} - {error_message}", UserWarning)
    return None
